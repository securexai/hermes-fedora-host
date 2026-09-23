"""Serialize fresh disposable certification lifecycles; never sign or deploy."""

import argparse
from datetime import datetime
import hashlib
import os
from pathlib import Path
import pwd
import re
import secrets
import signal
import time
from zoneinfo import ZoneInfo

from common import Failure, atomic, canonical, decode, lock, protected_file, report, require
from maintenance import publish
from policy import maintenance_open
from release import sha
from signer import owned_path

FIELDS = {'schema', 'repository', 'state_dir', 'events_dir', 'certifier_user', 'model',
          'iso', 'iso_sha256', 'checksum', 'keyring', 'fedora_fingerprint', 'firmware_code', 'firmware_vars'}
TERMINAL = {'complete', 'failed-cleaned', 'deferred-cleaned'}


def load(path):
    require(os.geteuid() == 0, 'lifecycle-requires-root-enrollment', 77)
    value = decode(protected_file(path, 0).read_bytes())
    require(isinstance(value, dict) and set(value) == FIELDS and value['schema'] == 'hermes-lifecycle-v1',
            'invalid-lifecycle-policy')
    require(value['certifier_user'] == 'hermes-certification', 'wrong-lifecycle-certifier')
    account = pwd.getpwnam(value['certifier_user'])
    require(account.pw_uid > 0, 'root-certifier-forbidden')
    require(sha(value['iso_sha256']) and isinstance(value['fedora_fingerprint'], str)
            and re.fullmatch(r'[A-F0-9]{40}', value['fedora_fingerprint']), 'invalid-media-binding')
    require(isinstance(value['model'], str) and re.fullmatch(r'[A-Za-z0-9._:/-]+', value['model']),
            'invalid-lifecycle-model')
    for key in ('repository', 'state_dir', 'events_dir', 'iso', 'checksum', 'keyring', 'firmware_code', 'firmware_vars'):
        name = value[key]
        require(isinstance(name, str) and re.fullmatch(r'/[A-Za-z0-9_./-]+', name)
                and '..' not in Path(name).parts, 'unsafe-lifecycle-path')
        if key in ('repository', 'state_dir', 'events_dir'):
            owned_path(name, 0, directory=True)
        else:
            protected_file(name, 0)
    paths = [Path(value[k]) for k in ('repository', 'state_dir', 'events_dir')]
    require(all(a != b and a not in b.parents and b not in a.parents
                for i, a in enumerate(paths) for b in paths[i + 1:]), 'overlapping-lifecycle-paths')
    # Run directories must be searchable for the certifier, but writable only by root.
    require(Path(value['state_dir']).stat().st_mode & 0o077 == 0o011, 'lifecycle-state-mode-must-be-0711')
    return value


def identity(policy):
    return hashlib.sha256(canonical(policy)).hexdigest()


def failure_context(error):
    # Only code locations and an allowlisted exception class; never messages, locals or child output.
    locations = []
    trace = error.__traceback__
    while trace is not None:
        code = trace.tb_frame.f_code
        path = Path(code.co_filename)
        if path.parent == Path(__file__).resolve().parent and re.fullmatch(r'[a-z_]+\.py', path.name):
            locations.append({'file': path.name, 'function': code.co_name, 'line': trace.tb_lineno})
        trace = trace.tb_next
    kind = type(error).__name__
    return {'type': kind if kind in {'Failure', 'OSError', 'ValueError', 'KeyError', 'TypeError',
                                    'AttributeError', 'TimeoutExpired', 'ModuleNotFoundError'} else 'Exception',
            'locations': locations[-8:]}


def lab_window(policy, path):
    grant = decode(protected_file(owned_path(path, 0), 0).read_bytes())
    require(isinstance(grant, dict) and set(grant) == {
        'schema', 'binding', 'run_id', 'issued_at', 'expires_at'
    } and grant['schema'] == 'hermes-lifecycle-lab-window-v1', 'invalid-lifecycle-lab-grant')
    require(grant['binding'] == identity(policy) and sha(grant['run_id']), 'lifecycle-lab-binding-mismatch')
    now = int(time.time())
    require(type(grant['issued_at']) is int and type(grant['expires_at']) is int
            and grant['issued_at'] <= now < grant['expires_at']
            and 0 < grant['expires_at'] - grant['issued_at'] <= 4 * 3600,
            'expired-or-invalid-lifecycle-lab-window')
    return grant


def execute(policy, factory, cleanup_only=False, now=None, grant_path=None):
    root = Path(policy['state_dir'])
    now = datetime.now(ZoneInfo('America/Bogota')) if now is None else now.astimezone(ZoneInfo('America/Bogota'))
    slot = now.date().isoformat()
    pointer = root / 'active.json'
    with lock(root / '.lifecycle.lock'):
        state = None
        if pointer.exists():
            active = decode(protected_file(pointer, 0).read_bytes())
            require(isinstance(active, dict) and set(active) == {'run_id'} and sha(active['run_id']),
                    'invalid-active-lifecycle')
            directory = owned_path(root / active['run_id'], 0, directory=True)
            state = decode(protected_file(directory / 'lifecycle.json', 0).read_bytes())
            require(state['run_id'] == active['run_id'] and state['binding'] == identity(policy),
                    'lifecycle-policy-changed')
        if state is not None and state['stage'] not in TERMINAL and not cleanup_only:
            raise Failure(75, 'interrupted-lifecycle-needs-cleanup')
        if cleanup_only:
            if state is None or state['stage'] in TERMINAL:
                return {'ok': True, 'stage': 'nothing-to-clean'}
        else:
            grant = lab_window(policy, grant_path) if grant_path is not None else None
            if grant is None and not maintenance_open(now):
                return {'ok': True, 'stage': 'deferred'}
            if state is not None and (state['run_id'] == grant['run_id'] if grant else state['slot'] == slot):
                return {'ok': True, 'stage': 'slot-already-finished'}
            run_id = grant['run_id'] if grant else secrets.token_hex(32)
            directory = root / run_id
            require(not directory.exists() and not directory.is_symlink(), 'lifecycle-lab-run-already-consumed')
            directory.mkdir(mode=0o711)
            directory.chmod(0o711)
            state = {'schema': 'hermes-lifecycle-state-v1', 'run_id': run_id,
                     'binding': identity(policy), 'slot': slot, 'stage': 'starting', 'certified': False}
            if grant is not None:
                state['lab_window'] = grant
            atomic(directory / 'lifecycle.json', canonical(state))
            atomic(pointer, canonical({'run_id': run_id}))

        def save(**values):
            state.update(values)
            atomic(directory / 'lifecycle.json', canonical(state))

        driver = factory(policy, directory, state, save)
        failed = state.get('failure')
        deferred = False
        if not cleanup_only:
            try:
                save(stage='provisioning')
                driver.prepare()
                save(stage='enrolled')
                # Preparation can use most of the window. Do not start late certification.
                if not (lab_window(policy, grant_path) == state['lab_window'] if grant_path else maintenance_open()):
                    deferred = True
                else:
                    save(stage='certifying')
                    driver.certify()
                    save(certified=True)
            except Exception as error:
                failed = 'lifecycle-execution-failed'
                save(failure=failed, failure_context=failure_context(error))
        else:
            failed = failed or 'interrupted-lifecycle'
            save(failure=failed)
        save(stage='cleaning')
        try:
            driver.cleanup()
        except Exception as error:
            save(stage='cleanup-failed', cleanup_failure='lifecycle-cleanup-failed',
                 cleanup_context=failure_context(error))
            raise Failure(69, 'lifecycle-cleanup-failed') from None
        stage = 'failed-cleaned' if failed else 'deferred-cleaned' if deferred else 'complete'
        # A cleanup-only recovery never upgrades interrupted acceptance into a pass.
        require(stage != 'complete' or state['certified'], 'missing-lifecycle-certification')
        save(stage=stage, cleanup_failure=None)
        if failed:
            raise Failure(69, 'lifecycle-failed-and-cleaned') from None
        return {'ok': True, 'stage': stage, 'run_id': state['run_id'], 'release_signed': False}


def main():
    parser = argparse.ArgumentParser(description='Run the root-enrolled disposable Hermes lifecycle')
    parser.add_argument('--config', required=True)
    parser.add_argument('--cleanup-only', action='store_true')
    parser.add_argument('--lab-window-grant')
    args = parser.parse_args()
    policy = load(args.config)
    from lifecycle_fixture import Fixture
    def interrupted(signum, frame):
        raise Failure(69, 'lifecycle-interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        result = execute(policy, Fixture, args.cleanup_only, grant_path=args.lab_window_grant)
    except Exception:
        publish(policy['events_dir'], 'action-required', 69)
        raise Failure(69, 'lifecycle-needs-attention') from None
    if result['stage'] == 'complete':
        publish(policy['events_dir'], 'completed', 0, result['run_id'])
    return result


if __name__ == '__main__':
    report(main)
