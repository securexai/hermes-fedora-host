"""Run isolated UA-03 acceptance; never issue a release or destruction gate."""

import argparse
import hashlib
import io
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Failure, atomic, canonical, decode, digest, protected_file, report, require, run
from credentials import client as credential_request
from finalize import validate_candidate
from gates import backup_snapshot
from policy import ssh_options
from release import candidate_fingerprint, sha
from scan_candidate import scan
from signer import owned_path

DOMAIN = '4db6369a-2b8b-427f-a47a-a5d83bb40cff'
FIELDS = {'schema', 'certifier_uid', 'domain_uuid', 'target', 'identity_file', 'known_hosts',
          'candidate', 'state_dir', 'evidence_dir', 'credential_socket', 'backup_repository',
          'backup_password_file', 'run_id', 'kernel'}


def validate_config(config):
    require(isinstance(config, dict) and set(config) == FIELDS and config['schema'] == 'hermes-certify-v1',
            'invalid-certifier-policy')
    require(config['domain_uuid'] == DOMAIN and config['target'] == 'hermes-certify@172.16.99.12',
            'certifier-requires-fixed-lab')
    require(type(config['certifier_uid']) is int and config['certifier_uid'] > 0
            and config['certifier_uid'] == os.getuid(), 'wrong-certifier-identity', 77)
    require(config['credential_socket'] == '/run/hermes-lab-credentials/broker.sock', 'non-lab-broker-forbidden')
    require(sha(config['run_id']) and re.fullmatch(r'[A-Za-z0-9._-]+', config['kernel']), 'invalid-certifier-run')
    for key in ('identity_file', 'known_hosts', 'candidate', 'state_dir', 'evidence_dir',
                'backup_repository', 'backup_password_file'):
        require(isinstance(config[key], str) and Path(config[key]).is_absolute(), 'relative-certifier-path')
    return config


def candidate(config):
    directory = owned_path(config['candidate'], config['certifier_uid'], directory=True)
    raw = protected_file(directory / 'candidate.json').read_bytes()
    manifest = validate_candidate(decode(raw))
    actual = {str(p.relative_to(directory)) for p in directory.rglob('*') if not p.is_dir()}
    require(actual == set(manifest['files']) | {'candidate.json'}, 'unexpected-frozen-candidate-files')
    for name, record in manifest['files'].items():
        path = owned_path(directory / name, config['certifier_uid'])
        require(path.stat().st_size == record['size'] and digest(path) == record['sha256'], 'frozen-candidate-changed')
    return manifest, raw


def archive_candidate(directory, raw, manifest, output, corrupt=False):
    with tarfile.open(fileobj=output, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        first = tarfile.TarInfo('candidate.json'); first.mode = 0o600; first.size = len(raw)
        archive.addfile(first, io.BytesIO(raw))
        names = sorted(manifest['files'], key=lambda name: (not name.startswith('payload/'), name))
        for name in names:
            info = tarfile.TarInfo(name); info.mode = 0o600; info.size = manifest['files'][name]['size']
            if corrupt:
                value = bytearray((directory / name).read_bytes())
                require(value, 'empty-corruption-fixture'); value[0] ^= 1
                archive.addfile(info, io.BytesIO(value))
                break
            with (directory / name).open('rb') as source: archive.addfile(info, source)


def retryable_boot_error(error, stages):
    return bool(stages and stages[-1] in ('reboot-pending', 'persistence-reboot')) and (
        isinstance(error, subprocess.TimeoutExpired)
        or isinstance(error, Failure) and error.reason == 'lab-transport-unavailable')


def failure_stage(state):
    value = state.get('stage')
    allowed = {'new', 'staging', 'snapshot', 'issuing-test-credential', 'deploying', 'reboot-pending',
               'persistence-reboot', 'closed', 'cold-boot', 'semantic-restore', 'scanning', 'ua03-acceptance-passed', 'previous-boot', 'return-updated-boot'}
    return value if isinstance(value, str) and value in allowed else 'unavailable'


def revoke_test_credential(path, lease):
    # Reconcile only an existing lease. The broker retains confirmed deletion and
    # requires actual HTTP 401 rejection before reporting successful revocation.
    # Retain the client's 120-second socket timeout and the outer cleanup limit;
    # at most three requests add only six seconds of backoff.
    attempts = []
    for attempt, delay in enumerate((0, 1, 5), 1):
        if delay: time.sleep(delay)
        try:
            result = credential_request(path, 'revoke', 'test', lease)
            require(result.get('ok') is True, 'credential-revocation-failed')
        except Exception as error:
            rejected = isinstance(error, Failure) and error.reason == 'credential-broker-rejected'
            transport = isinstance(error, (TimeoutError, ConnectionError))
            attempts.append({'attempt': attempt, 'result': 'FAIL',
                             'reason': 'broker-rejected' if rejected else
                                       'transport-unavailable' if transport else 'nonretryable'})
            if not (rejected or transport) or attempt == 3:
                error.revocation_attempts = attempts
                raise
        else:
            attempts.append({'attempt': attempt, 'result': 'PASS'})
            return {**result, 'attempts': attempts}


class Certifier:
    def __init__(self, config):
        self.config = validate_config(config)
        self.manifest, self.raw = candidate(config)
        self.fingerprint = candidate_fingerprint(self.manifest)
        self.state_dir = owned_path(config['state_dir'], os.getuid(), directory=True)
        self.evidence = owned_path(config['evidence_dir'], os.getuid(), directory=True)
        require(not (self.state_dir / 'state.json').exists(), 'certification-run-already-started')
        self.state = {'run_id': config['run_id'], 'artifact_fingerprint': self.fingerprint, 'stage': 'new'}
        self.lease = config['run_id'][:32]
        self.lease_attempted = False
        self.save('new')

    def save(self, stage, **values):
        self.state.update(values, stage=stage, updated_at=int(time.time()))
        atomic(self.state_dir / 'state.json', canonical(self.state))
        print(canonical({'stage': stage, 'run_id': self.config['run_id']}).decode(), end='', flush=True)

    def frame(self, action, **values):
        return {'schema': 'hermes-lab-candidate-v1', 'run_id': self.config['run_id'], 'action': action, **values}

    def exchange(self, message, body=None, output=None, timeout=1560):
        if body is None:
            process = subprocess.run(ssh_options(self.config), input=canonical(message),
                                     stdout=output if output is not None else subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, timeout=timeout)
        else:
            # Restore archives contain application state and must stay in volatile storage.
            scratch = '/dev/shm' if message['action'] == 'restore' else None
            with tempfile.TemporaryFile(dir=scratch) as request:
                request.write(canonical(message))
                body.seek(0)
                import shutil
                shutil.copyfileobj(body, request)
                request.seek(0)
                process = subprocess.run(ssh_options(self.config), stdin=request,
                                         stdout=output if output is not None else subprocess.PIPE,
                                         stderr=subprocess.DEVNULL, timeout=timeout)
        if output is not None:
            require(process.returncode == 0, 'snapshot-transfer-failed', 69)
            return None
        if process.returncode == 255 and not process.stdout:
            raise Failure(69, 'lab-transport-unavailable')
        response = decode(process.stdout)
        if process.returncode or response.get('ok') is not True:
            reason = response.get('error', 'lab-operation-failed')
            require(isinstance(reason, str) and re.fullmatch(r'[a-z0-9-]{1,96}', reason), 'invalid-lab-error')
            stage = response.get('stage')
            release_id = getattr(self, 'manifest', {}).get('release_id')
            bound_reboot = (message.get('action') == 'deploy' and isinstance(release_id, str)
                            and stage in ('reboot-pending', 'persistence-reboot')
                            and response == {'ok': True, 'stage': stage, 'release_id': release_id})
            # The remote reply can arrive before sshd exits during a scheduled reboot. Do not
            # accept it as success: the caller still requires an acknowledged boot stage and
            # its existing deadline before retrying. Reported guest failures stay terminal.
            if process.returncode in (255, 143) and bound_reboot:
                reason = 'lab-transport-unavailable'
            failure = Failure(process.returncode or 78, reason)
            failure.transport = {'ssh_returncode': process.returncode,
                                 'action': 'deploy' if message.get('action') == 'deploy' else 'other',
                                 'positive_reply': response.get('ok') is True,
                                 'bound_reboot_reply': bound_reboot}
            raise failure
        return response

    def request(self, action, **values):
        return self.exchange(self.frame(action, **values))

    def rejection(self, message, expected, body=None):
        try: self.exchange(message, body)
        except Failure as error:
            require(error.reason == expected, 'wrong-negative-test-failure')
            return True
        raise Failure(78, 'negative-test-accepted')

    def gate(self, name, result):
        record = {**result, 'gate': name, 'result': 'PASS', 'release_id': self.manifest['release_id'],
                  'artifact_fingerprint': self.fingerprint, 'run_id': self.config['run_id'],
                  'completed_at': int(time.time())}
        target = self.evidence / (name + '.json')
        require(not target.exists(), 'gate-evidence-already-exists')
        atomic(target, canonical(record))

    def cold_boot(self, observation='observe'):
        def power(action):
            return decode(run(['sudo', '-n', '/usr/local/libexec/hermes-lab-power/lab-power'],
                              data=canonical({'action': action}), timeout=40))
        power('shutdown')
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if power('state')['state'] == 'shut off': break
            time.sleep(3)
        else: raise Failure(69, 'cold-shutdown-timeout')
        power('start')
        return self.wait_observation(observation)

    def wait_observation(self, action='observe'):
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            try: return self.exchange(self.frame(action), timeout=max(1, deadline - time.monotonic()))
            except (Failure, subprocess.TimeoutExpired) as error:
                if not retryable_boot_error(error, ['reboot-pending']): raise
                time.sleep(5)
        raise Failure(69, 'boot-observation-timeout')

    def execute(self):
        config = self.config
        self.save('staging')
        negative = {}
        negative['wrong_run'] = self.rejection({**self.frame('status'), 'run_id': '0'*64}, 'invalid-lab-run')
        negative['extra_fields'] = self.rejection(self.frame('status', command='forbidden'), 'unexpected-lab-fields')
        with tempfile.TemporaryFile() as archive:
            archive_candidate(Path(config['candidate']), self.raw, self.manifest, archive, corrupt=True)
            negative['changed_payload'] = self.rejection(self.frame('stage'), 'candidate-member-hash-mismatch', archive)
        with tempfile.TemporaryFile() as archive:
            archive_candidate(Path(config['candidate']), self.raw, self.manifest, archive)
            staged = self.exchange(self.frame('stage'), archive)
        require(staged['artifact_fingerprint'] == self.fingerprint, 'staged-candidate-mismatch')
        require(self.request('status')['stage'] == 'new', 'non-clean-candidate-state')
        negative['credential_before_backup'] = self.rejection(self.frame('credential', key='synthetic-not-a-key'),
                                                              'credential-stage-mismatch')
        negative['deploy_before_backup'] = self.rejection(self.frame('deploy'), 'release-needs-recovery')
        negative['target_lock'] = self.request('lock-probe')['stage'] == 'lock-rejected'
        self.request('seed')
        self.save('snapshot')
        receipt = self.request('snapshot')
        negative['wrong_backup_receipt'] = self.rejection(self.frame('backup-verified', backup_snapshot='0'*64,
                                                                    snapshot_sha256='0'*64), 'backup-digest-mismatch')
        with tempfile.TemporaryDirectory(prefix='hermes-certifier-', dir='/dev/shm') as scratch:
            source = Path(scratch) / 'snapshot.tar'
            with source.open('xb') as output:
                source.chmod(0o600); self.exchange(self.frame('backup'), output=output)
            require(digest(source) == receipt['snapshot_sha256'], 'snapshot-hash-mismatch')
            backup = backup_snapshot(source, config, self.manifest['release_id'])
            backup['source_path'] = str(source)
            atomic(self.state_dir / 'backup.json', canonical(backup))
        self.request('backup-verified', backup_snapshot=backup['snapshot'], snapshot_sha256=backup['sha256'])
        self.save('issuing-test-credential', lease=self.lease)
        self.lease_attempted = True
        secret = credential_request(config['credential_socket'], 'issue', 'test', self.lease)
        self.request('credential', key=secret['key'])
        del secret
        self.save('deploying')
        deadline = time.monotonic() + 3600
        stages = []
        while time.monotonic() < deadline:
            try: result = self.request('deploy')
            except (Failure, subprocess.TimeoutExpired) as error:
                if not retryable_boot_error(error, stages): raise
                time.sleep(10); continue
            stage = result['stage']
            if not stages or stages[-1] != stage:
                stages.append(stage); self.save(stage, stages=stages)
            if stage == 'closed': break
            require(stage in ('reboot-pending', 'persistence-reboot'), 'unexpected-deployment-stage')
            time.sleep(10)
        else: raise Failure(69, 'candidate-deployment-timeout')
        require(stages == ['reboot-pending', 'persistence-reboot', 'closed'], 'missing-deployment-boot-stage')
        warm = self.request('observe')
        self.gate('package_replay', {'inventory_sha256': warm['package_inventory'], 'ordered_stages': stages})
        self.gate('inference', {'exact_output': 'HERMES_OK', 'source': 'candidate Host.acceptance before and after persistence reboot'})
        self.save('cold-boot')
        cold = self.cold_boot()
        require(cold['boot_id'] != warm['boot_id'], 'cold-boot-id-unchanged')
        self.gate('boot', {'warm': warm, 'cold': cold})
        self.gate('runtime', cold)
        # This is after actual update completion, before credential revocation or semantic restore.
        self.save('previous-boot')
        self.request('select-previous')
        previous = self.cold_boot('observe-previous')
        self.save('return-updated-boot')
        self.request('select-updated')
        returned = self.cold_boot('observe-returned')
        from lab_previous import verify_sequence
        verify_sequence(cold, previous, returned)
        self.gate('previous_boot', {'updated': cold, 'previous': previous, 'returned': returned,
                                  'post_update': True, 'reenrollment': False})
        before = self.request('observe')
        require(self.request('deploy')['stage'] == 'closed' and self.request('upgrade')['stage'] == 'closed',
                'closed-rerun-failed')
        after = self.request('observe')
        require(before['boot_id'] == after['boot_id'] and before['package_inventory'] == after['package_inventory'],
                'rerun-mutated-boot-or-packages')
        negative['closed_deploy_upgrade_rerun'] = True
        self.save('semantic-restore')
        self.request('damage')
        negative['wrong_restore_receipt'] = self.rejection(self.frame('restore', size=1, sha256='0'*64), 'invalid-restore-frame')
        with tempfile.TemporaryFile(dir='/dev/shm') as restored:
            run(['restic', '--no-cache', '--repo', config['backup_repository'], '--password-file', config['backup_password_file'],
                 'dump', backup['snapshot'], backup['source_path']], stdout=restored, timeout=300)
            size = restored.tell(); restored.seek(0)
            require(hashlib.file_digest(restored, 'sha256').hexdigest() == backup['sha256'], 'restore-transport-changed')
            self.exchange(self.frame('restore', size=size, sha256=backup['sha256']), restored)
        restored_state = self.request('restore-check')
        self.gate('restore', {**restored_state, 'snapshot': backup['snapshot'], 'encrypted_roundtrip': True})
        require(all(negative.values()), 'negative-matrix-incomplete')
        atomic(self.state_dir / 'negative-matrix.json', canonical({'result': 'PASS', 'checks': negative,
               'run_id': config['run_id'], 'artifact_fingerprint': self.fingerprint}))
        self.save('scanning')
        scan(config['candidate'], self.evidence / 'vulnerability_scan.json', config['run_id'])
        require(candidate(config)[1] == self.raw, 'candidate-changed-during-certification')
        self.save('ua03-acceptance-passed')

    def cleanup(self):
        if not self.lease_attempted: return
        errors = []
        try: self.request('cleanup-credential')
        except Exception: errors.append('prior-credential-restoration-failed')
        try:
            result = revoke_test_credential(self.config['credential_socket'], self.lease)
            self.revocation_attempts = result['attempts']
            if not (self.evidence / 'credential_revocation.json').exists(): self.gate('credential_revocation', result)
        except Exception as error:
            self.revocation_attempts = getattr(error, 'revocation_attempts', [])
            errors.append('provider-revocation-failed')
        require(not errors, '-and-'.join(errors), 69)


def main():
    parser = argparse.ArgumentParser(description='Certify one enrolled disposable candidate through UA-03')
    parser.add_argument('--config', required=True)
    parser.add_argument('--cleanup-only', action='store_true')
    args = parser.parse_args()
    config = decode(protected_file(args.config, 0).read_bytes())
    if args.cleanup_only:
        validate_config(config)
        manifest, raw = candidate(config)
        state_path = Path(config['state_dir']) / 'state.json'
        if not state_path.exists(): return {'ok': True, 'stage': 'no-credential-issued'}
        state = decode(protected_file(state_path).read_bytes())
        require(state['run_id'] == config['run_id'] and state['artifact_fingerprint'] == candidate_fingerprint(manifest),
                'cleanup-run-binding-mismatch')
        if 'lease' not in state: return {'ok': True, 'stage': 'no-credential-issued'}
        certifier = Certifier.__new__(Certifier)
        certifier.config = config; certifier.manifest = manifest; certifier.raw = raw
        certifier.fingerprint = candidate_fingerprint(manifest); certifier.evidence = Path(config['evidence_dir'])
        certifier.lease = state['lease']; certifier.lease_attempted = True
        require(certifier.lease == config['run_id'][:32], 'cleanup-lease-mismatch')
        certifier.cleanup()
        return {'ok': True, 'stage': 'credential-cleanup-complete'}
    certifier = Certifier(config)
    import signal
    def interrupted(signum, frame):
        raise Failure(69, 'certification-interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    failed = None
    failed_stage = None
    failed_transport = None
    try: certifier.execute()
    except Exception as error:
        failed = getattr(error, 'reason', 'certification-command-failed')
        failed_stage = failure_stage(certifier.state)
        failed_transport = getattr(error, 'transport', None)
    cleanup_failed = None
    try: certifier.cleanup()
    except Exception as error: cleanup_failed = getattr(error, 'reason', 'certification-cleanup-failed')
    if failed or cleanup_failed:
        diagnostic = {'failure_transport': failed_transport} if failed_transport is not None else {}
        attempts = getattr(certifier, 'revocation_attempts', None)
        if isinstance(attempts, list): diagnostic['revocation_attempts'] = attempts
        certifier.save('failed', failure=failed or cleanup_failed, primary_failure=failed,
                        cleanup_failure=cleanup_failed,
                        failure_stage=failed_stage or failure_stage(certifier.state), **diagnostic)
        failed = failed or cleanup_failed
        raise Failure(69, failed)
    certifier.save('ua03-complete')
    return {'ok': True, 'stage': 'ua03-complete', 'run_id': config['run_id'],
            'artifact_fingerprint': certifier.fingerprint, 'release_signed': False}


if __name__ == '__main__':
    report(main)
