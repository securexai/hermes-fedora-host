"""Explicit operator-run lab probes; never included in the signed host payload.

These helpers do not allocate fixtures or issue grants. The runbook specifies the
fresh fixture, caller identity, watchdog and control boots required around them.
"""

import argparse
import hashlib
import os
from pathlib import Path
import signal
import stat
import struct
import subprocess
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Failure, atomic, canonical, decode, digest, protected_file, report, require, run, lock

SECTIONS = {'.linux', '.initrd', '.cmdline'}


def mutate(source, destination, section):
    """Change exactly one byte inside a raw PE section without touching its signature."""
    source, destination = Path(source), Path(destination)
    require(section in SECTIONS, 'unsupported-tamper-section')
    require(source.stat().st_size <= 512 * 1024**2, 'oversized-uki')
    data = bytearray(protected_file(source).read_bytes())
    require(len(data) >= 64 and data[:2] == b'MZ', 'invalid-pe-header')
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    require(pe + 24 <= len(data) and data[pe:pe + 4] == b'PE\0\0', 'invalid-pe-header')
    count, optional = struct.unpack_from('<H', data, pe + 6)[0], struct.unpack_from('<H', data, pe + 20)[0]
    table = pe + 24 + optional
    require(1 <= count <= 96 and table + count * 40 <= len(data), 'invalid-pe-sections')
    matches, ranges = [], []
    for index in range(count):
        offset = table + index * 40
        name = bytes(data[offset:offset + 8]).rstrip(b'\0')
        size, start = struct.unpack_from('<II', data, offset + 16)
        require(start + size <= len(data), 'invalid-pe-section-range')
        if size:
            require(start >= table + count * 40, 'pe-section-overlaps-header')
            require(all(start + size <= a or start >= b for a, b in ranges), 'overlapping-pe-sections')
            ranges.append((start, start + size))
        if name == section.encode(): matches.append((start, size))
    require(len(matches) == 1 and matches[0][1] > 0, 'missing-or-duplicate-tamper-section')
    start, size = matches[0]
    before = hashlib.sha256(data).hexdigest()
    data[start] ^= 1
    # Exclusive creation also refuses links and the approved input path.
    with destination.open('xb') as output:
        destination.chmod(0o600)
        output.write(data)
        output.flush(); os.fsync(output.fileno())
    return {'source_sha256': before, 'tested_sha256': digest(destination), 'section': section,
            'changed_offset': start, 'changed_bytes': 1, 'resigned': False}


def checkpoint(path, point, **values):
    atomic(path, canonical({'schema': 'hermes-lab-fault-v1', 'point': point,
                           'timestamp': int(time.time()), **values}))
    os._exit(137)


def interrupted_copy(source, target, point, evidence):
    """Exercise common.atomic itself, interrupting only this exact target write."""
    require(point in {'before-copy', 'during-copy', 'before-publish'}, 'unknown-publication-fault')
    source, target, evidence = map(Path, (source, target, evidence))
    require(not evidence.exists() and not evidence.is_symlink(), 'fault-already-attempted')
    raw = source.read_bytes()
    info = {'source_sha256': hashlib.sha256(raw).hexdigest(), 'target': str(target)}
    if point == 'before-copy': checkpoint(evidence, point, **info)
    original_fdopen, original_replace = os.fdopen, os.replace

    class PartialWriter:
        def __init__(self, stream): self.stream = stream
        def __enter__(self): return self
        def __exit__(self, *args): return self.stream.__exit__(*args)
        def write(self, data):
            count = min(1024 * 1024, len(data) // 2)
            require(count > 0, 'image-too-small-for-partial-copy')
            self.stream.write(data[:count]); self.stream.flush(); os.fsync(self.stream.fileno())
            checkpoint(evidence, point, bytes_written=count, expected_size=len(data), **info)
        def __getattr__(self, name): return getattr(self.stream, name)

    def fdopen(fd, *args, **kwargs):
        stream = original_fdopen(fd, *args, **kwargs)
        name = Path(os.readlink('/proc/self/fd/' + str(fd)))
        if point == 'during-copy' and name.parent == target.parent and name.name.startswith('.pending-'):
            return PartialWriter(stream)
        return stream

    def replace(source_name, destination, *args, **kwargs):
        if point == 'before-publish' and Path(destination) == target:
            require(digest(source_name) == info['source_sha256'], 'incomplete-prepublication-file')
            checkpoint(evidence, point, temporary=str(source_name), **info)
        return original_replace(source_name, destination, *args, **kwargs)

    with patch.object(os, 'fdopen', fdopen), patch.object(os, 'replace', replace):
        atomic(target, raw)
    raise Failure(78, 'publication-fault-not-reached')


def enrolled(run_id):
    import certify_guest
    policy = certify_guest.enrollment()
    require(policy['run_id'] == run_id, 'wrong-fault-run')
    manifest = certify_guest.verify_tree(certify_guest.CANDIDATE, policy)
    # Prefer the frozen candidate's implementation, never a caller-supplied path.
    sys.path.insert(0, str(certify_guest.CANDIDATE / 'payload'))
    import host
    return policy, manifest, host.Host(certify_guest.CANDIDATE), host


def snapshot(run_id):
    policy, manifest, instance, host = enrolled(run_id)
    from lab_previous import retained, modules
    try:
        prior = retained(policy)
    except Failure as error:
        prior = {'preservation_error': error.reason}
    paths = ['/etc/crypttab', '/etc/fstab', '/etc/systemd/tpm2-pcr-public-key.pem',
             '/var/lib/systemd/tpm2-srk-public-key.tpm2b_public',
             '/etc/ssh/ssh_host_ed25519_key.pub', '/etc/machine-id',
             '/etc/dracut.conf.d/99-hermes-standard-tpm2.conf',
             '/etc/nvpcr/hardware.nvpcr', '/etc/nvpcr/cryptsetup.nvpcr',
             '/etc/systemd/system/systemd-pcrproduct.service',
             '/boot/efi/loader/loader.conf', '/etc/hermes-unattended/host.json',
             str(host.CREDENTIAL), '/home/hermes/data/config.yaml']
    files = {}
    for name in paths:
        path = Path(name)
        if path.is_symlink(): files[name] = {'link': os.readlink(path)}; continue
        if not path.exists(): files[name] = {'absent': True}; continue
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode), 'unexpected-preservation-file')
        raw = host.read_application_file(path) if name.endswith('/config.yaml') else path.read_bytes()
        files[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'mode': stat.S_IMODE(info.st_mode),
                       'uid': info.st_uid, 'gid': info.st_gid,
                       'xattrs_sha256': hashlib.sha256(canonical({key: os.getxattr(path, key).hex()
                                        for key in sorted(os.listxattr(path))})).hexdigest()}
    esp = Path('/boot/efi/EFI/Linux')
    artifacts = {p.name: {'size': p.stat().st_size, 'sha256': digest(p)} for p in sorted(esp.iterdir()) if p.is_file()}
    state = instance.state
    from offline import state_path
    journal = state_path((instance.directory / manifest['transaction']).parent, manifest['baseline_sha256'])
    replay = decode(journal.read_bytes()) if journal.exists() else None
    return {'run_id': run_id, 'candidate_sha256': policy['candidate_sha256'],
            'boot_id': host.boot_id(), 'inventory': host.package_baseline(), 'files': files,
            'esp': artifacts, 'entries': decode(run(['bootctl', '--esp-path=/boot/efi', '--json=short', 'list'])),
            'previous': prior, 'host_phase': state['phase'], 'replay': replay,
            'luks_metadata_sha256': hashlib.sha256(run(['cryptsetup', 'luksDump', '--dump-json-metadata', '/dev/vda3'])).hexdigest(),
            'selinux': run(['getenforce']).decode().strip(), 'timestamp': int(time.time())}


def replay_fault(run_id, point, evidence):
    policy, manifest, instance, host = enrolled(run_id)
    require(point in {'during-replay', 'before-select', 'after-select'}, 'unknown-replay-fault')
    import offline
    from gates import package_baseline
    original = offline.run
    baseline = manifest['baseline_sha256']
    directory = (instance.directory / manifest['transaction']).parent
    require(not evidence.exists() and not evidence.is_symlink(), 'fault-already-attempted')

    def invoke(args, **kwargs):
        if args[:2] == ['dnf5', '--disable-repo=*'] and point == 'during-replay':
            child = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, start_new_session=True)
            changed = False
            killed = False
            expected = (directory / 'installed-after.sha256').read_text().strip()
            try:
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline and child.poll() is None:
                    inventory = package_baseline()
                    changed = inventory not in {baseline, expected}
                    if changed and child.poll() is None: break
                    time.sleep(1)
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGKILL)
                    killed = True
                child.wait(timeout=10)
            require(changed and killed and child.returncode == -signal.SIGKILL,
                    'replay-mutation-checkpoint-not-observed')
            checkpoint(evidence, point, run_id=run_id, inventory_changed=True,
                       inventory_incomplete=True, child_killed=True)
        selecting = args[:3] == ['bootctl', '--esp-path=/boot/efi', 'set-default']
        if selecting and point == 'before-select': checkpoint(evidence, point, run_id=run_id)
        result = original(args, **kwargs)
        if selecting and point == 'after-select': checkpoint(evidence, point, run_id=run_id)
        return result

    with patch.object(offline, 'run', invoke):
        offline.execute(directory, baseline)
    raise Failure(78, 'replay-fault-not-reached')


def main():
    parser = argparse.ArgumentParser(description='Bounded primitives for the remaining operator-run lab cases')
    sub = parser.add_subparsers(dest='action', required=True)
    tamper = sub.add_parser('mutate')
    tamper.add_argument('--source', required=True); tamper.add_argument('--destination', required=True)
    tamper.add_argument('--section', required=True, choices=sorted(SECTIONS))
    observe = sub.add_parser('snapshot'); observe.add_argument('--run-id', required=True)
    for name in ('publish-fault', 'replay-fault'):
        item = sub.add_parser(name); item.add_argument('--run-id', required=True)
        item.add_argument('--point', required=True); item.add_argument('--evidence', required=True)
    args = parser.parse_args()
    if args.action == 'mutate': return mutate(args.source, args.destination, args.section)
    if args.action == 'snapshot': return snapshot(args.run_id)
    policy, manifest, instance, host = enrolled(args.run_id)
    evidence = Path(args.evidence)
    # Checkpoint records are secret-free; fixed guest-private directory only.
    require(evidence.parent == Path('/var/lib/hermes-lab-certification')
            and evidence.name == 'fault-' + args.point + '.json', 'wrong-fault-evidence-path')
    if args.action == 'replay-fault': return replay_fault(args.run_id, args.point, evidence)
    require(host.package_baseline() == manifest['baseline_sha256'], 'publication-needs-unchanged-baseline')
    from lab_previous import retained
    retained(policy)
    target = Path('/boot/efi/EFI/Linux') / ('hermes-' + manifest['release_id'] + '.efi')
    require(not target.exists() and not target.is_symlink(), 'publication-target-already-exists')
    with lock(host.ROOT / 'target.lock'):
        state = decode(protected_file(instance.journal, 0).read_bytes())
        require(state['phase'] == 'credential-ready', 'publication-staging-no-longer-ready')
        return interrupted_copy(instance.directory / manifest['boot_artifact'], target, args.point, evidence)


if __name__ == '__main__':
    report(main)
