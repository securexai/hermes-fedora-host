"""Fixed disposable preparation/enrollment operations, outside candidate authority."""

import argparse
import hashlib
import os
from pathlib import Path
import pwd
import re
import secrets
import shutil
import sys
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import atomic, canonical, decode, digest, protected_file, report, require, run

UUID = '4db6369a-2b8b-427f-a47a-a5d83bb40cff'
ROOT = Path('/var/lib/hermes-lifecycle-guest')
CODE = Path('/usr/local/libexec/hermes-lifecycle-guest')
TRANSACTION = ROOT / 'transaction'
EXPORT = ROOT / 'export'
POLICY = ROOT / 'binding.json'


def guard():
    require(os.geteuid() == 0 and Path('/sys/class/dmi/id/product_uuid').read_text().strip() == UUID,
            'not-disposable-lifecycle-guest', 77)
    require(Path('/boot/efi/hermes-tpm-stage').read_text().strip() == 'hermes-disposable-tpm-stage-v1',
            'missing-disposable-stage', 77)
    return decode(protected_file(POLICY, 0).read_bytes())


def check_request(action, message, binding):
    fields = {'run_id'}
    if action == 'bootstrap': fields |= {'model'}
    if action == 'enroll': fields |= {'policy', 'public_key'}
    require(isinstance(message, dict) and set(message) == fields
            and message['run_id'] == binding['run_id'], 'lifecycle-guest-run-mismatch')


def bootstrap(model):
    require(isinstance(model, str) and re.fullmatch(r'[A-Za-z0-9._:/-]+', model), 'invalid-lab-model')
    import host
    host.ROOT.mkdir(mode=0o700, exist_ok=True)
    fixture = host.Host.__new__(host.Host)
    fixture.directory = ROOT
    fixture.release_id = 'lifecycle-canary'
    fixture.manifest = {
        'image': next(line[6:] for line in (ROOT / 'payload/hermes.container').read_text().splitlines()
                      if line.startswith('Image=')), 'model': model}
    fixture.policy = {}
    fixture.previous = ROOT / 'previous'
    fixture.journal = ROOT / 'runtime-state.json'
    fixture.state = {'phase': 'backup-verified'}
    require(not fixture.journal.exists(), 'bootstrap-already-started')
    host.identity()
    fixture.capture_application()
    # This value is deliberately not a provider credential; it never leaves the guest.
    fixture.credential({'key': 'lifecycle-canary-' + secrets.token_hex(24)})
    fixture.install_runtime()
    host.wait_health(fixture.manifest['image'])
    return {'stage': 'canary-runtime-ready'}


def store():
    from transaction import expected_inventory
    from gates import verify_packages, package_baseline
    require(not TRANSACTION.exists(), 'transaction-already-started')
    before = run(['rpm', '-qa', '--qf', '%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\n'])
    before = b''.join(sorted(before.splitlines(keepends=True)))
    baseline = hashlib.sha256(before).hexdigest()
    run(['dnf5', '--assumeyes', '--setopt=gpgcheck=1', 'upgrade', '--store=' + str(TRANSACTION)], timeout=900)
    require(package_baseline() == baseline, 'download-mutated-baseline')
    atomic(TRANSACTION / 'installed-before.txt', before)
    atomic(TRANSACTION / 'installed-before.sha256', (baseline + '\n').encode())
    expected, _ = expected_inventory(decode((TRANSACTION / 'transaction.json').read_bytes()), before)
    atomic(TRANSACTION / 'installed-after.sha256', (hashlib.sha256(expected).hexdigest() + '\n').encode())
    verify_packages(TRANSACTION, baseline)
    return {'stage': 'transaction-verified', 'baseline': baseline}


def replay():
    from gates import replay_packages
    baseline = protected_file(TRANSACTION / 'installed-before.sha256', 0).read_text().strip()
    replay_packages(TRANSACTION, baseline)
    run(['systemd-run', '--unit=hermes-lifecycle-replay-reboot', '--on-active=5s', '/usr/bin/systemctl', 'reboot'])
    return {'stage': 'replay-reboot-pending'}


def replay_status():
    from offline import state_path, boot_id
    baseline = protected_file(TRANSACTION / 'installed-before.sha256', 0).read_text().strip()
    state = decode(protected_file(state_path(TRANSACTION, baseline), 0).read_bytes())
    require(state['status'] in {'staged', 'running', 'complete'}, 'preparation-replay-failed')
    return {'stage': 'preparation-replay-status',
            'complete': state['status'] == 'complete' and state['update_boot'] != boot_id()}


def export():
    from offline import require_complete
    from gates import package_baseline
    baseline = protected_file(TRANSACTION / 'installed-before.sha256', 0).read_text().strip()
    require_complete(TRANSACTION, baseline)
    require(package_baseline() == (TRANSACTION / 'installed-after.sha256').read_text().strip(),
            'replay-inventory-mismatch')
    require(not EXPORT.exists(), 'export-already-started')
    EXPORT.mkdir(mode=0o700)
    versions = run(['rpm', '-q', 'kernel-core', '--qf', '%{VERSION}-%{RELEASE}.%{ARCH}\n'])
    version = run(['sort', '-V'], data=versions).decode().splitlines()[-1]
    require(re.fullmatch(r'[A-Za-z0-9._+-]+', version), 'invalid-kernel-version')
    kernel = Path('/usr/lib/modules') / version / 'vmlinuz'
    require(run(['rpm', '-qf', '--qf', '%{NAME} %{VERSION}-%{RELEASE}.%{ARCH}', str(kernel)]).decode()
            == 'kernel-core ' + version, 'kernel-owner-mismatch')
    run(['dracut', '--force', str(EXPORT / 'initrd'), version], timeout=600)
    shutil.copyfile(kernel, EXPORT / 'linux')
    shutil.copyfile('/etc/os-release', EXPORT / 'osrel')
    command = Path('/proc/cmdline').read_text().strip()
    require(re.fullmatch(r'root=/dev/mapper/vg_root-root ro rd.lvm.lv=vg_root/root rd.luks.uuid=luks-'
                         r'[0-9a-f-]{36} rd.luks.options=tpm2-device=auto', command), 'unexpected-command-line')
    atomic(EXPORT / 'cmdline', (command + '\n').encode())
    records = {}
    for path in EXPORT.iterdir():
        path.chmod(0o600)
        require(0 < path.stat().st_size < 400 * 1024**2, 'oversized-export')
        records[path.name] = {'sha256': digest(path), 'size': path.stat().st_size}
    return {'stage': 'updated-kernel-exported', 'kernel': version, 'files': records}


def observe():
    from gates import package_baseline
    require(run(['mokutil', '--sb-state']).strip() == b'SecureBoot enabled', 'secure-boot-disabled')
    require(run(['getenforce']).strip() == b'Enforcing', 'selinux-disabled')
    from tpm_profile import services
    tpm_observation = services(run)
    entries = decode(run(['bootctl', '--json=short', 'list']))
    require([e['id'] for e in entries if e.get('isSelected')] == ['hermes-enrollment.efi'],
            'wrong-enrollment-boot')
    return {'stage': 'baseline-observed', 'baseline': package_baseline(), 'tpm_profile': tpm_observation,
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}


def enroll(message, binding):
    from release import sha
    policy, key = message['policy'], message['public_key']
    require(isinstance(policy, dict) and set(policy) == {
        'schema', 'domain_uuid', 'host', 'candidate_sha256', 'run_id', 'kernel'
    } and policy['schema'] == 'hermes-lab-certifier-v1' and policy['domain_uuid'] == UUID
        and policy['run_id'] == binding['run_id'] and policy['host'] == binding['host']
        and sha(policy['candidate_sha256']) and isinstance(policy['kernel'], str)
        and re.fullmatch(r'[A-Za-z0-9._-]+', policy['kernel']), 'invalid-guest-enrollment')
    require(isinstance(key, str) and re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]+', key),
            'invalid-certifier-public-key')
    require(digest('/etc/machine-id') == binding['host']['machine_id_sha256'], 'guest-machine-changed')
    fingerprint = run(['ssh-keygen', '-lf', '/etc/ssh/ssh_host_ed25519_key.pub', '-E', 'sha256']).decode().split()[1]
    require(fingerprint == binding['host']['ssh_fingerprint'], 'guest-ssh-changed')
    target = Path('/etc/hermes-lab-certifier.json')
    require(not target.exists() and not target.is_symlink(), 'guest-already-enrolled')
    code = Path('/usr/local/libexec/hermes-lab-certifier')
    require(not code.exists(), 'certifier-code-exists')
    code.mkdir(mode=0o755)
    for source in CODE.iterdir():
        protected_file(source, 0)
        if source.suffix == '.py' or source.name == 'lab-dispatch':
            shutil.copyfile(source, code / source.name)
            (code / source.name).chmod(0o755 if source.name == 'lab-dispatch' else 0o644)
    atomic(target, canonical(policy))
    Path('/var/lib/hermes-lab-certification').mkdir(mode=0o700)
    host_policy = Path('/etc/hermes-unattended/host.json')
    require(not host_policy.exists(), 'host-policy-exists')
    atomic(host_policy, canonical({'schema': 'hermes-host-v1', 'enabled': False, 'boot_certified': False,
           'recovery_verified': False, 'host': policy['host'], 'luks_device': '/dev/vda3',
           'deployment_user': 'hermes-certify'}))
    run(['useradd', '--create-home', '--shell', '/bin/bash', 'hermes-certify'])
    account = pwd.getpwnam('hermes-certify')
    home = Path(account.pw_dir)
    require(str(home) == '/home/hermes-certify' and account.pw_uid > 0, 'wrong-certifier-account')
    home.chmod(0o700)
    ssh = home / '.ssh'; ssh.mkdir(mode=0o700)
    os.chown(ssh, account.pw_uid, account.pw_gid)
    authorized = ssh / 'authorized_keys'
    atomic(authorized, ('restrict,from="172.16.99.1",command="sudo -n '
                       '/usr/local/libexec/hermes-lab-certifier/lab-dispatch" ' + key + '\n').encode())
    os.chown(authorized, account.pw_uid, account.pw_gid)
    sudoers = Path('/etc/sudoers.d/hermes-lab-certifier')
    require(not sudoers.exists(), 'certifier-sudoers-exists')
    atomic(sudoers, b'hermes-certify ALL=(root) NOPASSWD: /usr/local/libexec/hermes-lab-certifier/lab-dispatch ""\n')
    sudoers.chmod(0o440)
    run(['visudo', '-cf', str(sudoers)])
    effective = run(['sshd', '-T']).decode().splitlines()
    allowed = [line.split(None, 1)[1] for line in effective if line.startswith('allowusers ')]
    ssh_config = Path('/etc/ssh/sshd_config.d/98-hermes-lab-certifier.conf')
    require(not ssh_config.exists(), 'certifier-ssh-config-exists')
    if allowed:
        atomic(ssh_config, ('AllowUsers ' + ' '.join(allowed) + ' hermes-certify\n').encode())
    run(['restorecon', '-RF', str(home), str(code)])
    run(['sshd', '-t']); run(['systemctl', 'reload', 'sshd'])
    return {'stage': 'exact-candidate-enrolled', 'run_id': policy['run_id'],
            'candidate_sha256': policy['candidate_sha256'], 'production_enabled': False}


def stop_unit_if_present(unit):
    observed = subprocess.run(['systemctl', 'show', unit, '--property=LoadState', '--value'],
                              capture_output=True, timeout=30)
    state = observed.stdout.strip()
    require(state in (b'loaded', b'masked', b'not-found') and (observed.returncode == 0 or state == b'not-found'),
            'cannot-query-runtime-unit')
    if state != b'not-found': run(['systemctl', 'stop', unit])


def purge():
    # Idempotent after partial bootstrap/enrollment. Preserve the operator until VM destruction.
    try: account = pwd.getpwnam('hermes')
    except KeyError: account = None
    if account is not None:
        require(account.pw_dir == '/home/hermes' and account.pw_uid > 0, 'wrong-hermes-account')
        run(['loginctl', 'disable-linger', 'hermes'])
        stop_unit_if_present('user@' + str(account.pw_uid) + '.service')
        stop_unit_if_present('hermes-runtime-credentials.service')
        processes = run(['ps', '-eo', 'uid=']).decode().split()
        require(str(account.pw_uid) not in processes, 'runtime-processes-remain')
    mounts = run(['findmnt', '-rn', '-o', 'TARGET']).decode().splitlines()
    require(not any(p == '/home/hermes' or p.startswith('/home/hermes/') for p in mounts), 'runtime-mounts-remain')
    paths = [Path('/home/hermes'), Path('/var/spool/mail/hermes'), Path('/etc/credstore.encrypted/hermes-openai-api'),
             Path('/var/lib/hermes-unattended'), Path('/var/lib/hermes-lab-certification'),
             Path('/etc/hermes-lab-certifier.json'), Path('/etc/hermes-unattended'),
             Path('/usr/local/libexec/hermes-lab-certifier'), Path('/etc/sudoers.d/hermes-lab-certifier'),
             Path('/etc/ssh/sshd_config.d/98-hermes-lab-certifier.conf'),
             Path('/run/hermes-credentials'), Path('/run/hermes-runtime-credentials')]
    for path in paths:
        require(not path.is_symlink(), 'unsafe-guest-purge-path')
        if path.is_dir(): shutil.rmtree(path)
        else: path.unlink(missing_ok=True)
    if account is not None: run(['userdel', 'hermes'])
    try: certifier = pwd.getpwnam('hermes-certify')
    except KeyError: certifier = None
    if certifier is not None:
        require(certifier.pw_dir == '/home/hermes-certify' and certifier.pw_uid > 0, 'wrong-certifier-account')
        run(['userdel', '--remove', 'hermes-certify'])
    # ROOT contains the canary capture and package preparation state; binding stays until retry finishes.
    for name in ('previous', 'payload', 'transaction', 'export'):
        path = ROOT / name
        require(not path.is_symlink(), 'unsafe-bootstrap-purge-path')
        if path.exists(): shutil.rmtree(path)
    run(['sshd', '-t']); run(['systemctl', 'reload', 'sshd'])
    require(all(not p.exists() and not p.is_symlink() for p in paths), 'guest-purge-incomplete')
    return {'stage': 'guest-data-purged', 'logical_deletion': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('bootstrap', 'store', 'replay', 'replay-status', 'export', 'observe', 'enroll', 'purge'))
    action = parser.parse_args().action
    binding = guard()
    raw = sys.stdin.buffer.read(65537)
    require(len(raw) <= 65536, 'oversized-lifecycle-request')
    message = decode(raw)
    check_request(action, message, binding)
    if action == 'bootstrap': result = bootstrap(message['model'])
    elif action == 'enroll': result = enroll(message, binding)
    elif action == 'replay-status': result = replay_status()
    else: result = globals()[action]()
    return {'ok': True, **result}


if __name__ == '__main__':
    report(main)
