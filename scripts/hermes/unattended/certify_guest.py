"""Fixed lab-only candidate endpoint; never installed by the production dispatcher."""

import hashlib
import os
import re
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import atomic, canonical, decode, digest, lock, protected_file, report, require, run
from finalize import validate_candidate
from release import candidate_fingerprint, sha

POLICY = Path('/etc/hermes-lab-certifier.json')
ROOT = Path('/var/lib/hermes-lab-certification')
DOMAIN = '4db6369a-2b8b-427f-a47a-a5d83bb40cff'
CANDIDATE = ROOT / 'candidate'


def enrollment():
    require(os.geteuid() == 0, 'lab-certifier-requires-root', 77)
    policy = decode(protected_file(POLICY, 0).read_bytes())
    require(set(policy) == {'schema', 'domain_uuid', 'host', 'candidate_sha256', 'run_id', 'kernel'},
            'invalid-lab-certifier-policy')
    require(policy['schema'] == 'hermes-lab-certifier-v1' and policy['domain_uuid'] == DOMAIN
            and Path('/sys/class/dmi/id/product_uuid').read_text().strip() == DOMAIN,
            'not-enrolled-disposable-domain', 77)
    require(Path('/boot/efi/hermes-tpm-stage').read_text().strip() == 'hermes-disposable-tpm-stage-v1',
            'not-disposable-tpm-installation', 77)
    require(sha(policy['run_id']) and sha(policy['candidate_sha256']), 'invalid-lab-binding')
    require(digest('/etc/machine-id') == policy['host']['machine_id_sha256'], 'lab-machine-id-mismatch')
    fingerprint = run(['ssh-keygen', '-lf', '/etc/ssh/ssh_host_ed25519_key.pub', '-E', 'sha256']).decode().split()[1]
    require(fingerprint == policy['host']['ssh_fingerprint'], 'lab-ssh-identity-mismatch')
    require(ROOT.is_dir() and not ROOT.is_symlink() and ROOT.stat().st_uid == 0
            and ROOT.stat().st_mode & 0o077 == 0, 'unsafe-lab-certifier-state')
    return policy


def validate_raw(raw, policy):
    require(len(raw) <= 1024 * 1024 and hashlib.sha256(raw).hexdigest() == policy['candidate_sha256'],
            'unenrolled-candidate')
    manifest = validate_candidate(decode(raw))
    require(manifest['host'] == policy['host'], 'wrong-lab-candidate-host')
    return manifest


def verify_tree(directory, policy, owner=0):
    manifest = validate_raw(protected_file(directory / 'manifest.json', owner).read_bytes(), policy)
    actual = {str(p.relative_to(directory)) for p in directory.rglob('*') if not p.is_dir()}
    require(actual == set(manifest['files']) | {'manifest.json'}, 'unexpected-candidate-files')
    for name, record in manifest['files'].items():
        path = protected_file(directory / name, owner)
        require(path.stat().st_size == record['size'] and digest(path) == record['sha256'], 'candidate-bytes-changed')
    return manifest


def receive(stream, destination, policy):
    # Stream only regular files into a new root-owned directory, never extract a tar as root.
    with tarfile.open(fileobj=stream, mode='r|') as archive:
        iterator = iter(archive)
        first = next(iterator, None)
        require(first is not None and first.name == 'candidate.json' and first.isfile()
                and not first.issparse() and not first.pax_headers and first.size <= 1024 * 1024,
                'invalid-candidate-header')
        raw = archive.extractfile(first).read()
        manifest = validate_raw(raw, policy)
        atomic(destination / 'manifest.json', raw)
        seen = set()
        for member in iterator:
            require(member.name in manifest['files'] and member.name not in seen and member.isfile()
                    and not member.issparse() and not member.pax_headers, 'unsafe-candidate-member')
            record = manifest['files'][member.name]
            require(member.size == record['size'], 'candidate-member-size-mismatch')
            target = destination / member.name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            source = archive.extractfile(member)
            hasher = hashlib.sha256()
            with target.open('xb') as output:
                target.chmod(0o600)
                remaining = member.size
                while remaining:
                    chunk = source.read(min(1024 * 1024, remaining))
                    require(chunk, 'truncated-candidate')
                    output.write(chunk)
                    hasher.update(chunk)
                    remaining -= len(chunk)
                output.flush()
                os.fsync(output.fileno())
            require(hasher.hexdigest() == record['sha256'], 'candidate-member-hash-mismatch')
            seen.add(member.name)
        require(seen == set(manifest['files']), 'incomplete-candidate')
    return manifest


def host_action(action, message=None, timeout=1500):
    import subprocess
    result = subprocess.run(['/usr/bin/python3', '-I', '-B', str(CANDIDATE / 'payload/host.py'), action],
                            input=canonical(message) if message is not None else None,
                            stdin=subprocess.DEVNULL if message is None else None,
                            capture_output=True, timeout=timeout)
    value = decode(result.stdout)
    if result.returncode or value.get('ok') is not True:
        reason = value.get('error', 'candidate-operation-failed')
        require(isinstance(reason, str) and re.fullmatch(r'[a-z0-9-]{1,96}', reason), 'invalid-candidate-error')
        from common import Failure
        raise Failure(result.returncode or 78, reason)
    return value


def observe(action, policy, stream=None, message=None):
    command = ['/usr/bin/python3', '-I', '-B', str(Path(__file__).with_name('certify_observe.py')),
               action, str(CANDIDATE), policy['run_id'], policy['kernel']]
    if action == 'restore':
        # Accept only the exact archive captured by the candidate's snapshot stage.
        receipt = decode(protected_file(ROOT / 'snapshot.json', 0).read_bytes())
        require(message['sha256'] == receipt['snapshot_sha256'] and type(message['size']) is int
                and 0 < message['size'] <= 1024**3, 'invalid-restore-frame')
        with tempfile.TemporaryFile(dir='/run') as temporary:
            hasher = hashlib.sha256()
            remaining = message['size']
            while remaining:
                chunk = stream.read(min(remaining, 1024 * 1024))
                require(chunk, 'truncated-restore')
                temporary.write(chunk); hasher.update(chunk); remaining -= len(chunk)
            require(hasher.hexdigest() == receipt['snapshot_sha256'], 'restore-digest-mismatch')
            temporary.seek(0)
            import subprocess
            result = subprocess.run(command, stdin=temporary, capture_output=True, timeout=300)
            require(result.returncode == 0, 'semantic-restore-failed', 69)
            return decode(result.stdout)
    return decode(run(command, timeout=300))


def dispatch(stream):
    policy = enrollment()
    raw = stream.readline(65537)
    require(len(raw) <= 65536 and raw.endswith(b'\n'), 'invalid-lab-frame')
    message = decode(raw)
    require(isinstance(message, dict) and message.get('schema') == 'hermes-lab-candidate-v1'
            and message.get('run_id') == policy['run_id'], 'invalid-lab-run')
    action = message.get('action')
    fields = {'schema', 'run_id', 'action'}
    if action == 'credential': fields |= {'key'}
    if action == 'backup-verified': fields |= {'backup_snapshot', 'snapshot_sha256'}
    if action == 'restore': fields |= {'size', 'sha256'}
    require(set(message) == fields, 'unexpected-lab-fields')
    require(action in {'stage', 'status', 'snapshot', 'backup', 'backup-verified', 'credential',
                       'deploy', 'upgrade', 'rollback', 'observe', 'seed', 'damage', 'restore', 'restore-check', 'cleanup-credential', 'lock-probe', 'observe-previous', 'observe-returned',
                       'select-previous', 'select-updated'},
            'unauthorized-lab-operation', 77)
    with lock(ROOT / 'endpoint.lock'):
        if action == 'stage':
            from lab_previous import capture
            capture(policy)
            with tempfile.TemporaryDirectory(prefix='.incoming-', dir=ROOT) as temporary:
                incoming = Path(temporary) / 'candidate'; incoming.mkdir(mode=0o700)
                manifest = receive(stream, incoming, policy)
                if CANDIDATE.exists():
                    verify_tree(CANDIDATE, policy)
                else:
                    os.rename(incoming, CANDIDATE)
            return {'ok': True, 'stage': 'staged', 'artifact_fingerprint': candidate_fingerprint(manifest)}
        manifest = verify_tree(CANDIDATE, policy)
        if action in {'select-previous', 'select-updated'}:
            from lab_previous import select
            with lock(Path('/var/lib/hermes-unattended/target.lock')):
                return select(policy, manifest, action == 'select-previous')
        if action == 'lock-probe':
            import subprocess
            probe = subprocess.run(['/usr/bin/python3', '-I', str(Path(__file__).resolve())],
                input=canonical({'schema': 'hermes-lab-candidate-v1', 'run_id': policy['run_id'], 'action': 'status'}),
                capture_output=True, timeout=30)
            require(probe.returncode == 75 and decode(probe.stdout).get('error') == 'target-busy',
                    'concurrent-operation-not-rejected')
            return {'ok': True, 'stage': 'lock-rejected'}
        if action in {'observe', 'observe-previous', 'observe-returned', 'seed', 'damage', 'restore', 'restore-check', 'cleanup-credential'}:
            return observe(action, policy, stream, message)
        if action == 'backup':
            receipt = decode(protected_file(ROOT / 'snapshot.json', 0).read_bytes())
            path = Path('/var/lib/hermes-unattended') / (manifest['release_id'] + '.snapshot.tar')
            require(digest(protected_file(path, 0)) == receipt['snapshot_sha256'], 'snapshot-changed')
            with path.open('rb') as source: shutil.copyfileobj(source, sys.stdout.buffer)
            return None
        # Match the production target lock as well as serializing lab fixture operations.
        with lock(Path('/var/lib/hermes-unattended/target.lock')):
            result = host_action(action, message if action in {'credential', 'backup-verified'} else None)
        if action == 'snapshot': atomic(ROOT / 'snapshot.json', canonical(result))
        return result


if __name__ == '__main__':
    require(len(sys.argv) == 1, 'lab-endpoint-takes-no-arguments')
    report(lambda: dispatch(sys.stdin.buffer))
