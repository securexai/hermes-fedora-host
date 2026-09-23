"""Lab certification boundary tests; no VM, provider or production access."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/hermes/unattended'))
import certify
import certify_guest
from common import Failure, canonical
from release import GATES, SCHEMA


class CandidateBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'; self.source.mkdir()
        files = {}
        for name in ['payload/host.py', 'payload/vulnerability-policy.json', 'packages/transaction.json', 'boot/hermes.efi']:
            path = self.source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'synthetic bytes')
            files[name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'size': path.stat().st_size, 'mode': 0o600}
        now = int(time.time())
        self.manifest = {'schema': SCHEMA, 'release_id': 'synthetic', 'issued_at': now, 'expires_at': now+86400,
                         'image': 'docker.io/nousresearch/hermes-agent@sha256:'+'a'*64,
                         'provider': 'openai-api', 'model': 'synthetic',
                         'host': {'machine_id_sha256': 'b'*64, 'ssh_fingerprint': 'SHA256:'+'A'*43},
                         'baseline_sha256': 'c'*64, 'transaction': 'packages/transaction.json',
                         'boot_artifact': 'boot/hermes.efi', 'files': files,
                         'evidence': {g: 'evidence/'+g+'.json' for g in GATES}}
        self.raw = canonical(self.manifest)
        self.policy = {'candidate_sha256': hashlib.sha256(self.raw).hexdigest(), 'host': self.manifest['host']}
        self.destination = self.root / 'received'; self.destination.mkdir()

    def archive(self, corrupt=False):
        stream = io.BytesIO()
        certify.archive_candidate(self.source, self.raw, self.manifest, stream, corrupt)
        stream.seek(0); return stream

    def test_real_tar_roundtrip_preserves_every_frozen_byte(self):
        result = certify_guest.receive(self.archive(), self.destination, self.policy)
        self.assertEqual(result, self.manifest)
        for name in result['files']:
            self.assertEqual((self.source/name).read_bytes(), (self.destination/name).read_bytes())

    def test_changed_payload_is_rejected_before_installation(self):
        with self.assertRaisesRegex(Failure, 'candidate-member-hash-mismatch'):
            certify_guest.receive(self.archive(True), self.destination, self.policy)

    def test_candidate_host_and_enrolled_hash_are_independent_requirements(self):
        with self.assertRaisesRegex(Failure, 'unenrolled-candidate'):
            certify_guest.validate_raw(self.raw+b' ', self.policy)
        with self.assertRaisesRegex(Failure, 'wrong-lab-candidate-host'):
            certify_guest.validate_raw(self.raw, {**self.policy, 'host': {}})

    def test_enrolled_manifest_cannot_escape_candidate_directory(self):
        changed = copy.deepcopy(self.manifest)
        changed['files']['payload/../../outside'] = changed['files']['payload/host.py']
        raw = canonical(changed)
        with self.assertRaises(Failure):
            certify_guest.validate_raw(raw, {**self.policy, 'candidate_sha256': hashlib.sha256(raw).hexdigest()})
        self.assertFalse((self.root/'outside').exists())

    def test_symlink_tar_member_is_rejected(self):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w', format=tarfile.USTAR_FORMAT) as archive:
            first = tarfile.TarInfo('candidate.json'); first.size = len(self.raw)
            archive.addfile(first, io.BytesIO(self.raw))
            link = tarfile.TarInfo('payload/host.py'); link.type = tarfile.SYMTYPE; link.linkname = '/etc/passwd'
            archive.addfile(link)
        stream.seek(0)
        with self.assertRaisesRegex(Failure, 'unsafe-candidate-member'):
            certify_guest.receive(stream, self.destination, self.policy)

    def test_incomplete_upload_cannot_become_staged(self):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w', format=tarfile.USTAR_FORMAT) as archive:
            first = tarfile.TarInfo('candidate.json'); first.size = len(self.raw)
            archive.addfile(first, io.BytesIO(self.raw))
        stream.seek(0)
        with self.assertRaisesRegex(Failure, 'incomplete-candidate'):
            certify_guest.receive(stream, self.destination, self.policy)


class PolicyBoundaryTests(unittest.TestCase):
    def config(self):
        value = {k: '/private/'+k for k in certify.FIELDS}
        value.update(schema='hermes-certify-v1', certifier_uid=987, domain_uuid=certify.DOMAIN,
                     target='hermes-certify@172.16.99.12', run_id='a'*64, kernel='7.1.13-test',
                     credential_socket='/run/hermes-lab-credentials/broker.sock')
        return value

    def test_only_enrolled_nonroot_identity_and_fixed_lab_are_accepted(self):
        with patch.object(os, 'getuid', return_value=987):
            self.assertEqual(certify.validate_config(self.config()), self.config())
            for changed in [{'target': 'aicowork@10.0.30.10'}, {'domain_uuid': 'other'},
                            {'credential_socket': '/run/hermes-credentials/broker.sock'}, {'certifier_uid': 0}]:
                with self.subTest(changed=changed), self.assertRaises(Failure):
                    certify.validate_config({**self.config(), **changed})

    def test_boot_retries_never_hide_reported_acceptance_failure(self):
        pending = ['reboot-pending']
        self.assertTrue(certify.retryable_boot_error(Failure(69, 'lab-transport-unavailable'), pending))
        self.assertFalse(certify.retryable_boot_error(Failure(69, 'lab-transport-unavailable'), []))
        for reason in ['package-replay-result-mismatch', 'application-rolled-back', 'failed-tpm-service', 'invalid-json']:
            with self.subTest(reason=reason):
                self.assertFalse(certify.retryable_boot_error(Failure(78, reason), pending))

    def exchange_result(self, response, returncode, action='deploy'):
        instance = certify.Certifier.__new__(certify.Certifier)
        instance.config = {}; instance.manifest = {'release_id': 'synthetic'}
        process = subprocess.CompletedProcess(['ssh'], returncode, canonical(response))
        with patch.object(certify, 'ssh_options', return_value=['ssh']), \
                patch.object(certify.subprocess, 'run', return_value=process):
            return instance.exchange({'action': action})

    def test_complete_pending_reply_followed_by_reboot_disconnect_is_retryable(self):
        for stage in ['reboot-pending', 'persistence-reboot']:
            for code in [255, 143]:
                with self.subTest(stage=stage, code=code):
                    response = {'ok': True, 'stage': stage, 'release_id': 'synthetic'}
                    with self.assertRaises(Failure) as caught:
                        self.exchange_result(response, code)
                    self.assertTrue(certify.retryable_boot_error(caught.exception, [stage]))
                    self.assertFalse(certify.retryable_boot_error(caught.exception, []))
                    self.assertEqual(caught.exception.transport, {
                        'ssh_returncode': code, 'action': 'deploy', 'positive_reply': True,
                        'bound_reboot_reply': True})

    def test_disconnect_never_hides_guest_errors_or_unbound_positive_replies(self):
        cases = [
            ({'ok': False, 'error': 'package-replay-result-mismatch'}, 255, 'deploy'),
            ({'ok': True, 'stage': 'closed', 'release_id': 'synthetic'}, 255, 'deploy'),
            ({'ok': True, 'stage': 'reboot-pending', 'release_id': 'other'}, 255, 'deploy'),
            ({'ok': True, 'stage': 'reboot-pending', 'release_id': 'synthetic'}, 78, 'deploy'),
            ({'ok': True, 'stage': 'reboot-pending', 'release_id': 'synthetic'}, 255, 'observe'),
            ({'ok': True, 'stage': 'reboot-pending', 'release_id': 'synthetic',
              'unexpected': 'private-canary-do-not-log'}, 255, 'deploy')]
        for response, code, action in cases:
            with self.subTest(response=response, code=code, action=action):
                with self.assertRaises(Failure) as caught:
                    self.exchange_result(response, code, action)
                self.assertFalse(certify.retryable_boot_error(caught.exception, ['reboot-pending']))
                self.assertNotIn('private-canary', repr(getattr(caught.exception, 'transport', {})))
                if response.get('ok') is False:
                    self.assertEqual(caught.exception.reason, response['error'])

    def test_successful_pending_reply_is_unchanged(self):
        response = {'ok': True, 'stage': 'reboot-pending', 'release_id': 'synthetic'}
        self.assertEqual(self.exchange_result(response, 0), response)

    def test_primary_failure_survives_cleanup_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.json'
            config.write_text('{}')
            with patch('signal.signal'), \
                    patch.object(sys, 'argv', ['certify.py', '--config', str(config)]), \
                    patch.object(certify, 'protected_file', return_value=config), \
                    patch.object(certify, 'Certifier') as constructor:
                instance = constructor.return_value
                instance.state = {'stage': 'snapshot'}
                instance.execute.side_effect = Failure(78, 'original-failure')
                instance.cleanup.side_effect = Failure(69, 'cleanup-failure')
                with self.assertRaisesRegex(Failure, 'original-failure'):
                    certify.main()
                instance.save.assert_called_once_with('failed', failure='original-failure',
                    primary_failure='original-failure', cleanup_failure='cleanup-failure', failure_stage='snapshot')

    def test_failure_stage_keeps_only_fixed_progress_names(self):
        self.assertEqual(certify.failure_stage({'stage': 'snapshot'}), 'snapshot')
        for value in ('private-credential-canary', ['snapshot'], None):
            with self.subTest(value=value):
                self.assertEqual(certify.failure_stage({'stage': value}), 'unavailable')

    def test_primary_transport_diagnostic_survives_cleanup_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.json'; config.write_text('{}')
            original = Failure(255, 'lab-operation-failed')
            original.transport = {'ssh_returncode': 255, 'action': 'deploy',
                                  'positive_reply': True, 'bound_reboot_reply': False}
            with patch('signal.signal'), \
                    patch.object(sys, 'argv', ['certify.py', '--config', str(config)]), \
                    patch.object(certify, 'protected_file', return_value=config), \
                    patch.object(certify, 'Certifier') as constructor:
                instance = constructor.return_value
                instance.state = {'stage': 'reboot-pending'}
                instance.execute.side_effect = original
                instance.cleanup.side_effect = Failure(69, 'cleanup-failure')
                with self.assertRaisesRegex(Failure, 'lab-operation-failed'):
                    certify.main()
                self.assertEqual(instance.save.call_args.kwargs['failure_transport'], original.transport)
                self.assertEqual(instance.save.call_args.kwargs['primary_failure'], original.reason)

    def test_cleanup_attempts_revocation_even_if_guest_is_unreachable(self):
        instance = certify.Certifier.__new__(certify.Certifier)
        instance.config = self.config(); instance.lease_attempted = True; instance.lease = 'a'*32
        with tempfile.TemporaryDirectory() as directory:
            instance.evidence = Path(directory)
            with patch.object(instance, 'request', side_effect=Failure(69, 'unreachable')), \
                    patch.object(instance, 'gate'), \
                    patch.object(certify, 'credential_request', return_value={'ok': True}) as broker:
                with self.assertRaisesRegex(Failure, 'prior-credential-restoration-failed'):
                    instance.cleanup()
                broker.assert_called_once_with(instance.config['credential_socket'], 'revoke', 'test', 'a'*32)

    def test_cleanup_cannot_turn_revocation_failure_into_pass(self):
        instance = certify.Certifier.__new__(certify.Certifier)
        instance.config = self.config(); instance.lease_attempted = True; instance.lease = 'a'*32
        with patch.object(instance, 'request'), patch.object(certify, 'credential_request', side_effect=Failure(69, 'failed')):
            with self.assertRaisesRegex(Failure, 'provider-revocation-failed'): instance.cleanup()


class RevocationReconciliationTests(unittest.TestCase):
    def test_cleanup_recovers_after_transient_revocation_failure(self):
        instance = certify.Certifier.__new__(certify.Certifier)
        instance.config = {'credential_socket': '/test/socket'}
        instance.lease_attempted = True; instance.lease = 'a'*32
        with tempfile.TemporaryDirectory() as directory:
            instance.evidence = Path(directory)
            with patch.object(instance, 'request') as guest, patch.object(instance, 'gate') as gate, \
                    patch.object(certify, 'credential_request', side_effect=[
                        Failure(69, 'credential-broker-rejected'), {'ok': True, 'revoked': True}]) as broker, \
                    patch.object(certify.time, 'sleep'):
                instance.cleanup()
            guest.assert_called_once_with('cleanup-credential')
            self.assertEqual(broker.call_count, 2)
            gate.assert_called_once()
            self.assertEqual(gate.call_args.args[0], 'credential_revocation')
            self.assertEqual([a['result'] for a in gate.call_args.args[1]['attempts']], ['FAIL', 'PASS'])

    def test_cleanup_exhaustion_retains_attempts_without_a_pass(self):
        instance = certify.Certifier.__new__(certify.Certifier)
        instance.config = {'credential_socket': '/test/socket'}
        instance.lease_attempted = True; instance.lease = 'a'*32
        with patch.object(instance, 'request'), patch.object(instance, 'gate') as gate, \
                patch.object(certify, 'credential_request', side_effect=Failure(69, 'credential-broker-rejected')), \
                patch.object(certify.time, 'sleep'):
            with self.assertRaisesRegex(Failure, 'provider-revocation-failed'): instance.cleanup()
        self.assertEqual([a['result'] for a in instance.revocation_attempts], ['FAIL']*3)
        gate.assert_not_called()

    def test_immediate_confirmation_needs_one_request(self):
        with patch.object(certify, 'credential_request', return_value={'ok': True, 'revoked': True}) as request, \
                patch.object(certify.time, 'sleep') as sleep:
            result = certify.revoke_test_credential('/test/socket', 'a'*32)
        request.assert_called_once_with('/test/socket', 'revoke', 'test', 'a'*32)
        sleep.assert_not_called()
        self.assertTrue(result['revoked'])
        self.assertEqual(result['attempts'], [{'attempt': 1, 'result': 'PASS'}])

    def test_retry_reconciles_only_the_same_lease(self):
        for failure in (Failure(69, 'credential-broker-rejected'), TimeoutError('private-canary')):
            with self.subTest(failure=type(failure).__name__), \
                    patch.object(certify, 'credential_request', side_effect=[failure, {'ok': True, 'revoked': True}]) as request, \
                    patch.object(certify.time, 'sleep') as sleep:
                result = certify.revoke_test_credential('/test/socket', 'a'*32)
                self.assertEqual(request.call_count, 2)
                self.assertTrue(all(call.args == ('/test/socket', 'revoke', 'test', 'a'*32)
                                    for call in request.call_args_list))
                sleep.assert_called_once_with(1)
                self.assertEqual([a['result'] for a in result['attempts']], ['FAIL', 'PASS'])
                self.assertNotIn('private-canary', repr(result))

    def test_exhausted_reconciliation_remains_failure(self):
        with patch.object(certify, 'credential_request', side_effect=Failure(69, 'credential-broker-rejected')) as request, \
                patch.object(certify.time, 'sleep') as sleep:
            with self.assertRaises(Failure) as caught:
                certify.revoke_test_credential('/test/socket', 'a'*32)
        self.assertEqual(request.call_count, 3)
        self.assertEqual([call.args for call in sleep.call_args_list], [(1,), (5,)])
        self.assertEqual([a['result'] for a in caught.exception.revocation_attempts], ['FAIL']*3)

    def test_invalid_reply_or_interruption_is_not_retried(self):
        for response in ({'ok': False}, Failure(69, 'certification-interrupted'),
                         Failure(78, 'broker-response-too-large')):
            with self.subTest(response=type(response).__name__), \
                    patch.object(certify, 'credential_request') as request, patch.object(certify.time, 'sleep') as sleep:
                if isinstance(response, Exception): request.side_effect = response
                else: request.return_value = response
                with self.assertRaises(Failure): certify.revoke_test_credential('/test/socket', 'a'*32)
                self.assertEqual(request.call_count, 1)
                sleep.assert_not_called()


if __name__ == '__main__': unittest.main()
