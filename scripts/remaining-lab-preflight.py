#!/usr/bin/env python3
"""Read-only preparation inventory; never grants, dispatches or certifies a fixture."""
import argparse
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

ARTIFACT = ['artifact_probe.py']
CONTEXT = ['operator_context.py']
CASES = {
    'b4-linux': ARTIFACT, 'b4-initrd': ARTIFACT, 'b4-cmdline': ARTIFACT,
    'b4-pcr11': CONTEXT + ['pcr_prepare.py', 'pcr_boot.py', 'capture_boot.py'],
    'b4-external': CONTEXT + ['external_probe.py'],
    'b4-credential': CONTEXT + ['credential_probe.py'],
    'b7-before-copy': CONTEXT + ['publication_probe.py'],
    'b7-during-copy': CONTEXT + ['publication_probe.py'],
    'b7-before-publish': CONTEXT + ['publication_probe.py'],
    'b7-during-replay': CONTEXT + ['publication_probe.py', 'replay_probe.py'],
    'b7-before-select': CONTEXT + ['publication_probe.py', 'replay_probe.py'],
    'b7-after-select': CONTEXT + ['publication_probe.py', 'replay_probe.py'],
    'b7-notifications': CONTEXT + ['notification_probe.py'],
}
TOOLS = ['python3', 'sudo', 'systemctl', 'ssh', 'virsh', 'guestfish', 'qemu-img',
         'openssl', 'objcopy', 'sbverify', 'sbsign', 'notify-send']
CONTROLS = ['install-controls.py', 'dispatch.py', 'restore-controls.py', 'verify-restoration.py']


def fingerprint(path, syntax=False):
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, os.getuid()) or info.st_mode & 0o022:
        raise ValueError('unsafe-file')
    raw = path.read_bytes()
    if syntax:
        ast.parse(raw, filename=path.name)
    return {'path': str(path.absolute()), 'sha256': hashlib.sha256(raw).hexdigest(),
            'size': len(raw), 'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid}


def tool_fingerprint(path):
    try:
        return fingerprint(path)
    except PermissionError:
        # Some sudo installations deliberately expose an execute-only root-owned wrapper.
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022 or not info.st_mode & 0o111:
            raise ValueError('unsafe-tool')
        digest = subprocess.run(['sudo', '-n', '/usr/bin/sha256sum', '--', str(path)],
                                stdin=subprocess.DEVNULL, capture_output=True, timeout=15)
        value = digest.stdout.split()[0].decode() if digest.returncode == 0 and digest.stdout else ''
        if len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('tool-hash-unavailable')
        return {'path': str(path.absolute()), 'sha256': value, 'size': info.st_size,
                'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid}


def environment():
    memory = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                      if line.startswith('MemAvailable:')))
    def check(command):
        try:
            return subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            return None
    sudo = check(['sudo', '-n', 'true'])
    domains = check(['virsh', '-c', 'qemu:///system', 'list', '--all', '--name'])
    idle = domains is not None and domains.returncode == 0 and not domains.stdout.strip()
    return {'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'available_memory_kib': memory, 'minimum_memory_kib': 9 * 1024**2,
            'sudo_noninteractive': sudo is not None and sudo.returncode == 0,
            'no_libvirt_domains': idle,
            'resource_and_access_ready': memory >= 9 * 1024**2 and idle
                                         and sudo is not None and sudo.returncode == 0,
            'must_repeat_at_L0': True}


def prepare(operators, templates, source_manifest, repository, tool_path):
    files, cases, tools = {}, {}, {}
    def inspect(path, syntax=True):
        key = str(path.absolute())
        if key not in files:
            try:
                files[key] = {'result': 'PASS', **fingerprint(path, syntax)}
            except (OSError, ValueError, SyntaxError) as error:
                files[key] = {'path': key, 'result': 'BLOCKED', 'reason': type(error).__name__}
        return files[key]['result'] == 'PASS'
    for name in TOOLS:
        found = shutil.which(name, path=tool_path)
        try:
            if not found:
                raise FileNotFoundError(name)
            tools[name] = {'result': 'PASS', **tool_fingerprint(Path(found).resolve())}
        except (OSError, ValueError) as error:
            tools[name] = {'result': 'BLOCKED', 'reason': type(error).__name__}
    predecessor = 'b3'
    for case, names in CASES.items():
        required = [operators / name for name in names]
        required += [templates / 'blocks' / case / name for name in CONTROLS]
        checks = [inspect(p) for p in required]
        units = list((templates / 'blocks' / case).glob('*.service'))
        experiment_units = [u for u in units if not u.name.endswith('-failed.service')]
        bounded = len(experiment_units) == 1
        for unit in units:
            checks.append(inspect(unit, False))
        if bounded:
            text = experiment_units[0].read_text()
            bounded = all(value in text for value in
                          ('TimeoutStartSec=170min', 'TimeoutStopSec=50min', 'KillMode=control-group'))
        checks.append(bounded)
        required.extend(units)
        checks.extend(v['result'] == 'PASS' for n, v in tools.items()
                      if n != 'notify-send' or case == 'b7-notifications')
        cases[case] = {'predecessor': predecessor,
                       'static_preparation': 'PASS' if all(checks) else 'BLOCKED',
                       'required_files': [str(p.absolute()) for p in required],
                       'live_acceptance': 'NOT_RUN', 'maximum_total_seconds': 14400}
        predecessor = case
    manifest = json.loads(source_manifest.read_bytes())
    inspect(source_manifest, False)
    for name in manifest:
        p = repository / name
        # Bundled binaries have their own root-owned tool readiness checks in L0.
        if name.startswith('scripts/hermes/unattended/bin/'):
            continue
        inspect(p, name.endswith('.py'))
    inspect(repository / 'docs/HERMES_REMAINING_LAB_TESTS.md', False)
    inspect(Path(__file__).resolve())
    return {'schema': 'hermes-preparation-inventory-v1',
            'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'files': files, 'tools': tools, 'cases': cases,
            'dispatch_environment': environment(),
            'limitations': ['Syntax and file checks do not prove operator semantics or guest permissions.',
                            'Live L0, predecessor acceptance, independent L2 and fresh grants remain mandatory.',
                            'Notification visibility requires actual receipt; no desktop message is sent.',
                            'No fixture, credential, grant or host control is modified.']}


def verify(snapshot, case=None):
    drift = []
    selected = None
    if case is not None:
        all_case_files = {p for c in snapshot['cases'].values() for p in c['required_files']}
        shared = set(snapshot['files']) - all_case_files
        selected = shared | set(snapshot['cases'][case]['required_files'])
    for group in ('files', 'tools'):
        for name, old in snapshot[group].items():
            if group == 'files' and selected is not None and name not in selected:
                continue
            if group == 'tools' and case is not None and case != 'b7-notifications' and name == 'notify-send':
                continue
            if old['result'] != 'PASS':
                drift.append({'input': name, 'reason': 'previously-blocked'})
                continue
            try:
                current = tool_fingerprint(Path(old['path'])) if group == 'tools' else fingerprint(old['path'])
                if any(current[k] != old[k] for k in ('sha256', 'mode', 'uid', 'size')):
                    drift.append({'input': name, 'reason': 'changed'})
            except (OSError, ValueError):
                drift.append({'input': name, 'reason': 'unavailable-or-unsafe'})
    return {'unchanged_inputs': not drift, 'drift': drift,
            'live_gates_reusable': False, 'grants_reusable': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--operators', type=Path)
    p.add_argument('--templates', type=Path)
    p.add_argument('--source-manifest', type=Path)
    p.add_argument('--repository', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--output', type=Path)
    p.add_argument('--verify', type=Path)
    p.add_argument('--case', choices=list(CASES))
    args = p.parse_args()
    if args.verify:
        result = verify(json.loads(args.verify.read_bytes()), args.case)
    else:
        if not all((args.operators, args.templates, args.source_manifest, args.output)):
            p.error('operators, templates, source-manifest and exclusive output are required')
        tool_path = '/var/lib/hermes-lifecycle-source/bin:' + os.environ.get('PATH', '')
        result = prepare(args.operators, args.templates, args.source_manifest, args.repository, tool_path)
        with args.output.open('x') as stream:
            os.chmod(args.output, 0o600)
            json.dump(result, stream, indent=2)
            stream.write('\n')
        result = {'report': str(args.output), 'cases': {n:v['static_preparation'] for n,v in result['cases'].items()},
                  'blocked_tools': [n for n,v in result['tools'].items() if v['result'] != 'PASS'],
                  'dispatch_environment': result['dispatch_environment']}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
