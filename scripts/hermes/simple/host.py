"""Bounded application-only installer. Never modifies boot, TPM, or OS update policy."""
import base64
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import platform
import pwd
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import time

ROOT = Path('/var/lib/hermes-simple')
LIB = Path('/usr/local/libexec/hermes-simple')
STATE = ROOT / 'state.json'
KEY = Path('/etc/credstore.encrypted/hermes-simple-openai')
SSH_CONFIG = Path('/etc/ssh/sshd_config.d/00-hermes-simple.conf')
PACKAGES = ['podman', 'curl', 'openssl', 'python3', 'mokutil', 'firewalld', 'restic', 'shadow-utils']
PAYLOAD = {'host.py', 'data.py', 'materialize.py', 'hermes.container', '60-hermes-runtime.conf',
           '70-hermes-volume-label.conf', 'harden-config.py', 'set-model.py'}


class Failure(Exception):
    pass


def require(value, reason):
    if not value:
        raise Failure(reason)


def run(args, data=None, timeout=120, allow=False, **kwargs):
    result = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=timeout, **kwargs)
    if result.returncode and not allow:
        raise Failure('command-failed:' + Path(args[0]).name)
    return result


def out(args, **kwargs):
    return run(args, **kwargs).stdout


def protected(path):
    for parent in (path, *path.parents):
        if parent.exists() or parent.is_symlink():
            info = parent.lstat()
            require(not stat.S_ISLNK(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
                    'unsafe-managed-path')


def atomic(path, data, mode=0o600):
    protected(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        os.replace(name, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def save(state, phase=None):
    if phase:
        state['phase'] = phase
    state['updated_at'] = int(time.time())
    atomic(STATE, json.dumps(state, sort_keys=True).encode())


def user(args, **kwargs):
    account = pwd.getpwnam('hermes')
    return out(['runuser', '-u', 'hermes', '--', 'env', '--chdir=/home/hermes',
                'HOME=/home/hermes', 'XDG_RUNTIME_DIR=/run/user/' + str(account.pw_uid), *args], **kwargs)


def service(*args, **kwargs):
    return user(['systemctl', '--user', *args], **kwargs)


def crypt_backed(path):
    device = out(['findmnt', '-n', '-o', 'SOURCE', '-T', path]).decode().strip().split('[')[0]
    require(device.startswith('/dev/'), 'application-storage-not-block-backed')
    devices = json.loads(out(['lsblk', '-s', '-J', '-o', 'TYPE', device]))['blockdevices']
    def encrypted(nodes):
        return any(n.get('type') == 'crypt' or encrypted(n.get('children', [])) for n in nodes)
    require(encrypted(devices), 'application-storage-not-luks-backed')


def preflight(config):
    require(os.geteuid() == 0, 'administrator-required')
    values = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    require(values.get('ID', '').strip('"') == 'fedora' and values.get('VERSION_ID', '').strip('"') == '44'
            and values.get('VARIANT_ID', '').strip('"') == 'server' and platform.machine() == 'x86_64',
            'fedora-server-44-x86_64-required')
    require(out(['getenforce']).strip() == b'Enforcing', 'selinux-enforcing-required')
    flags = list(Path('/sys/firmware/efi/efivars').glob('SecureBoot-*'))
    require(len(flags) == 1 and flags[0].read_bytes()[4:] == b'\x01', 'secure-boot-required')
    crypt_backed('/home/hermes' if Path('/home/hermes').exists() else '/home')
    crypt_backed('/var/lib')
    require(shutil.disk_usage('/var').free >= 20 * 1024 ** 3, '20-gib-var-space-required')
    require(int(re.search(r'MemTotal:\s+(\d+)', Path('/proc/meminfo').read_text())[1]) >= 8388608,
            '8-gib-memory-required')
    require(Path('/sys/fs/cgroup/cgroup.controllers').exists(), 'cgroup-v2-required')
    require(re.fullmatch(r'[a-z_][a-z0-9_-]*@[A-Za-z0-9.-]+', config['target']), 'target-invalid')
    admin = config['target'].split('@')[0]
    require(admin != 'root' and pwd.getpwnam(admin).pw_uid != 0, 'nonroot-administrator-required')
    require(re.fullmatch(r'[A-Za-z0-9_.:-]{1,15}', config['management_interface']), 'interface-invalid')
    network = ipaddress.ip_network(config['management_cidr'], strict=True)
    require(network.version == 4 and network.prefixlen > 0, 'management-network-invalid')
    require(Path('/sys/class/net', config['management_interface']).exists(), 'interface-not-found')
    # The current transport must come from the allowlisted management network.
    connection = os.environ.get('SSH_CONNECTION', '').split()
    # sudo commonly removes SSH_CONNECTION. Query the administrator session's
    # source through an explicit bootstrap transport field instead (set by wrapper).
    require(connection and ipaddress.ip_address(connection[0]) in network, 'management-source-required')
    require(re.fullmatch(r'docker.io/nousresearch/hermes-agent@sha256:[0-9a-f]{64}', config['image']),
            'official-image-digest-required')
    require(config['provider'] == 'openai-api' and
            re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}', config['model']), 'provider-model-invalid')
    require(shutil.which('dnf5') and shutil.which('systemd-creds'), 'bootstrap-tools-missing')
    require(not Path('/etc/systemd/system/hermes-runtime-credentials.service').exists(),
            'advanced-profile-already-enrolled')
    return {'ok': True, 'bootstrap': 'ready', 'phase': 'checked'}


def config_fingerprint(config, files):
    semantic = {k: v for k, v in config.items() if k not in ('identity_file', 'known_hosts_file')}
    return hashlib.sha256(json.dumps([semantic, files], sort_keys=True).encode()).hexdigest()


def install_payload(files):
    require(set(files) == PAYLOAD, 'payload-files-invalid')
    protected(LIB)
    LIB.mkdir(parents=True, exist_ok=True)
    for name, encoded in files.items():
        raw = base64.b64decode(encoded, validate=True)
        require(len(raw) < 512 * 1024, 'payload-too-large')
        atomic(LIB / name, raw, 0o644)


def track(state, path):
    protected(path)
    name = str(path)
    if name not in state['files']:
        state['files'][name] = {'data': base64.b64encode(path.read_bytes()).decode(),
                               'mode': stat.S_IMODE(path.stat().st_mode)} if path.exists() else None
        save(state)


def write(state, path, data):
    track(state, path)
    atomic(path, data, 0o644)


def arm(state, seconds):
    # A persistent boot recovery unit covers power loss; a transient monotonic
    # timer covers controller/SSH loss without requiring a reboot.
    guard = 'hermes-simple-recovery-' + state['token'][:16]
    state['guard'] = guard
    save(state)
    run(['systemd-run', '--quiet', '--unit=' + guard, '--on-active=' + str(seconds) + 's',
         '/usr/bin/python3', '-I', str(LIB / 'host.py'), 'recover'])


def disarm(state):
    if state.get('guard'):
        run(['systemctl', 'stop', state['guard'] + '.timer'], allow=True)


def setup_recovery():
    atomic(Path('/etc/systemd/system/hermes-simple-recovery.service'), b'''[Unit]
Description=Reconcile interrupted Hermes application deployment
After=local-fs.target network-online.target
Before=hermes-simple-credentials.service
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 -I /usr/local/libexec/hermes-simple/host.py recover
TimeoutStartSec=600
StandardOutput=null
StandardError=null
[Install]
WantedBy=multi-user.target
''', 0o644)
    run(['systemctl', 'daemon-reload'])
    run(['systemctl', 'enable', 'hermes-simple-recovery.service'])


def configure_access(state):
    config = state['config']
    admin = config['target'].split('@')[0]
    iface = config['management_interface']
    zone = out(['firewall-cmd', '--get-zone-of-interface=' + iface]).decode().strip()
    if not zone or zone == 'no zone':
        zone = out(['firewall-cmd', '--get-default-zone']).decode().strip()
    require(re.fullmatch(r'[A-Za-z0-9_-]+', zone), 'firewall-zone-invalid')
    path = Path('/etc/firewalld/zones') / (zone + '.xml')
    track(state, path)
    # Preserve both runtime and permanent rules; refuse to overwrite unrelated
    # runtime-only changes in this first version.
    args = ['firewall-cmd', '--zone=' + zone, '--list-all']
    runtime = out(args).decode().replace(' (active)', '')
    permanent = out(args + ['--permanent']).decode().replace(' (active)', '')
    require(runtime == permanent, 'firewall-runtime-permanent-drift')
    write(state, SSH_CONFIG, (f'PasswordAuthentication no\nKbdInteractiveAuthentication no\n'
          f'PubkeyAuthentication yes\nPermitRootLogin no\nAllowUsers {admin}\n'
          'AllowTcpForwarding no\nX11Forwarding no\nPermitTunnel no\nGatewayPorts no\n').encode())
    run(['/usr/sbin/sshd', '-t'])
    rule = f'rule family="ipv4" source address="{config["management_cidr"]}" service name="ssh" accept'
    run(['firewall-cmd', '--permanent', '--zone=' + zone, '--add-rich-rule=' + rule])
    for name in ('ssh', 'cockpit', 'mdns'):
        run(['firewall-cmd', '--permanent', '--zone=' + zone, '--remove-service=' + name])
    # Reject alternate open ports/rich rules; do not destroy unrelated policies.
    require(not out(['firewall-cmd', '--permanent', '--zone=' + zone, '--list-ports']).strip(),
            'unmanaged-firewall-ports')
    state['access_changed'] = True
    save(state)
    run(['firewall-cmd', '--reload'])
    run(['systemctl', 'reload', 'sshd'])


def identity(state):
    try:
        account = pwd.getpwnam('hermes')
    except KeyError:
        state['created_account'] = True
        save(state)
        run(['useradd', '--create-home', '--home-dir', '/home/hermes', '--user-group',
             '--shell', '/usr/sbin/nologin', 'hermes'])
        account = pwd.getpwnam('hermes')
    require(account.pw_dir == '/home/hermes' and account.pw_uid >= 1000, 'unsafe-hermes-account')
    require(not Path('/home/hermes').is_symlink() and not Path('/home/hermes/data').is_symlink(),
            'unsafe-hermes-home')
    require(not Path('/home/hermes/.ssh/authorized_keys').exists(), 'hermes-has-ssh-keys')
    require(not set(out(['id', '-nG', 'hermes']).decode().split()) & {'wheel', 'sudo', 'adm', 'systemd-journal'},
            'privileged-hermes-account')
    for file in ('/etc/subuid', '/etc/subgid'):
        require(any(line.startswith('hermes:') for line in Path(file).read_text().splitlines()),
                'missing-subordinate-ids')
    run(['passwd', '-l', 'hermes'])
    run(['loginctl', 'enable-linger', 'hermes'])
    run(['systemctl', 'start', f'user@{account.pw_uid}.service'])
    user(['chmod', '0700', '/home/hermes'])
    user(['mkdir', '-p', '-m', '0700', '/home/hermes/data'])
    state['uid'] = account.pw_uid
    save(state)
    return account


def encrypt(path, name, value):
    data = out(['systemd-creds', 'encrypt', '--with-key=host', '--name=' + name, '-', '-'], data=value)
    atomic(path, data)


def backup_args():
    return ['restic', '--no-cache', '--repo', str(ROOT / 'backups'), '--password-command',
            '/usr/bin/systemd-creds decrypt --name=backup /var/lib/hermes-simple/backup.cred -']


def snapshot(state):
    if not (ROOT / 'backup.cred').exists():
        encrypt(ROOT / 'backup.cred', 'backup', secrets.token_hex(32).encode())
    if not (ROOT / 'backups/config').exists():
        run(backup_args() + ['init'])
    archive = user(['podman', 'unshare', 'python3', '-I', str(LIB / 'data.py'), 'snapshot'], timeout=180)
    records = out(backup_args() + ['backup', '--stdin', '--stdin-filename', 'application.tar', '--json'],
                  data=archive, timeout=300).splitlines()
    summary = next(json.loads(line) for line in reversed(records) if json.loads(line).get('snapshot_id'))
    snapshot_id = summary['snapshot_id']
    restored = out(backup_args() + ['dump', snapshot_id, 'application.tar'], timeout=300)
    require(hashlib.sha256(restored).digest() == hashlib.sha256(archive).digest(), 'backup-readback-mismatch')
    state['backup'] = snapshot_id
    state['backup_sha256'] = hashlib.sha256(archive).hexdigest()
    save(state, 'backup-verified')


def credentials(state, key):
    if key:
        require(len(key) <= 8192 and not any(c.isspace() for c in key) and '\x00' not in key, 'invalid-key')
        require(not KEY.exists(), 'credential-rotation-requires-separate-provisioning')
        state['created_credential'] = True
        save(state)
        encrypt(KEY, 'openai-api', key.encode())
    require(KEY.exists(), 'one-time-api-key-required')


def healthy(config, inference=False):
    value = json.loads(user(['podman', 'inspect', 'hermes']))[0]
    require(value.get('State', {}).get('Health', {}).get('Status') == 'healthy', 'runtime-unhealthy')
    require(value.get('ImageName') == config['image'], 'runtime-image-mismatch')
    host = value['HostConfig']
    require(host.get('ReadonlyRootfs') and not host.get('Privileged') and not host.get('Devices')
            and not value.get('NetworkSettings', {}).get('Ports') and host.get('PidsLimit') == 512,
            'runtime-isolation-mismatch')
    require(any('no-new-privileges' in option for option in host.get('SecurityOpt', [])), 'privilege-escalation-enabled')
    mounts = {m['Destination']: m for m in value.get('Mounts', [])}
    require(set(mounts) == {'/opt/data', '/opt/data/.env'} and not mounts['/opt/data/.env']['RW'],
            'runtime-mounts-mismatch')
    if inference:
        response = user(['podman', 'exec', '-i', '--user', '10000:10000', 'hermes', 'hermes', '--safe-mode',
                         '--provider', config['provider'], '--model', config['model'], '--toolsets', 'context_engine',
                         '-z', 'Return exactly HERMES_OK. The complete response must be HERMES_OK and nothing else.'],
                        timeout=180)
        require(response.rstrip(b'\n') == b'HERMES_OK', 'inference-not-exact')


def wait_health(config):
    for _ in range(36):
        try:
            healthy(config)
            return
        except Failure:
            time.sleep(5)
    raise Failure('runtime-health-timeout')


def runtime(state):
    config, uid = state['config'], state['uid']
    # Configure through a networkless, credential-free one-shot container before
    # the gateway can process traffic or channel events.
    user(['podman', 'unshare', 'chown', '10000:10000', '/home/hermes/data'])
    user(['podman', 'unshare', 'chcon', '-R', 'system_u:object_r:container_file_t:s0', '/home/hermes/data'])
    init = b"from pathlib import Path\np=Path('/opt/data/config.yaml')\nif not p.exists(): p.write_text('{}\\n')\n"
    harden = (LIB / 'harden-config.py').read_bytes()
    # The credential-bearing .env stays read-only. Do not run the legacy .env
    # backup/rewrite portion; enforce its flags in the volatile materializer.
    harden = harden.split(b'if env_path.exists():')[0]
    setup = init + harden + b'\n' + (LIB / 'set-model.py').read_bytes()
    user(['podman', 'run', '--rm', '-i', '--pull=never', '--network=none', '--read-only',
          '--cap-drop=all', '--security-opt=no-new-privileges', '--user=10000:10000',
          '--tmpfs=/tmp:rw,size=64m', '-v', '/home/hermes/data:/opt/data:z',
          '-e', 'HERMES_PROVIDER=' + config['provider'], '-e', 'HERMES_MODEL=' + config['model'],
          '--entrypoint=python3', config['image'], '-'], data=setup, timeout=120)
    materializer = (LIB / 'materialize.py').read_text().replace('/run/hermes-secrets', '/run/hermes-simple-secrets')
    materializer = materializer.replace('lines.append("OPENAI_API_KEY=" + key)',
        'lines = [line for line in lines if line.split("=", 1)[0].strip() not in '
        '("API_SERVER_ENABLED", "HERMES_DASHBOARD", "GATEWAY_ALLOW_ALL_USERS", "WEBHOOK_ENABLED")]\n'
        '    lines.extend(["API_SERVER_ENABLED=false", "HERMES_DASHBOARD=0", '
        '"GATEWAY_ALLOW_ALL_USERS=false", "WEBHOOK_ENABLED=false"])\n'
        '    lines.append("OPENAI_API_KEY=" + key)')
    write(state, LIB / 'runtime-materialize.py', materializer.encode())
    credential_unit = (f'[Unit]\nRequires=user-runtime-dir@{uid}.service\nAfter=user-runtime-dir@{uid}.service\n'
        '[Service]\nType=oneshot\nRemainAfterExit=true\n'
        f'LoadCredentialEncrypted=openai-api:{KEY}\n'
        f'ExecStart=/usr/bin/python3 -I {LIB}/runtime-materialize.py\n'
        'UMask=0077\nLimitCORE=0\nStandardOutput=null\nStandardError=null\n')
    write(state, Path('/etc/systemd/system/hermes-simple-credentials.service'), credential_unit.encode())
    write(state, Path(f'/etc/systemd/system/user@{uid}.service.d/80-hermes-simple.conf'),
          b'[Unit]\nRequires=hermes-simple-credentials.service\nAfter=hermes-simple-credentials.service\n')
    unit = re.sub(r'^Image=.*$', 'Image=' + config['image'], (LIB / 'hermes.container').read_text(), flags=re.M)
    unit = unit.replace('[Container]\n', '[Container]\nVolume=/run/hermes-simple-secrets/provider.env:/opt/data/.env:ro,z\n')
    write(state, Path(f'/etc/containers/systemd/users/{uid}/hermes.container'), unit.encode())
    for name in ('60-hermes-runtime.conf', '70-hermes-volume-label.conf'):
        write(state, Path('/etc/systemd/user/hermes.service.d') / name, (LIB / name).read_bytes())
    run(['systemctl', 'daemon-reload'])
    run(['systemctl', 'restart', 'hermes-simple-credentials.service'])
    run(['systemctl', 'start', f'user@{uid}.service'])
    service('daemon-reload')
    service('restart', 'hermes.service')
    wait_health(config)
    healthy(config, inference=True)


def recover(state):
    if state.get('phase') in ('closed', 'rolled-back'):
        return
    if state.get('uid'):
        service('stop', 'hermes.service', allow=True)
    if state.get('backup'):
        archive = out(backup_args() + ['dump', state['backup'], 'application.tar'], timeout=300)
        require(hashlib.sha256(archive).hexdigest() == state['backup_sha256'], 'rollback-backup-mismatch')
        user(['podman', 'unshare', 'python3', '-I', str(LIB / 'data.py'), 'restore'], data=archive, timeout=180)
    for name, record in reversed(list(state.get('files', {}).items())):
        path = Path(name)
        protected(path)
        if record is None:
            path.unlink(missing_ok=True)
        else:
            atomic(path, base64.b64decode(record['data']), record['mode'])
    run(['systemctl', 'daemon-reload'])
    run(['firewall-cmd', '--reload'], allow=True)
    run(['/usr/sbin/sshd', '-t'])
    run(['systemctl', 'reload', 'sshd'])
    if state.get('previous'):
        if Path('/etc/systemd/system/hermes-simple-credentials.service').exists():
            run(['systemctl', 'restart', 'hermes-simple-credentials.service'])
        run(['systemctl', 'start', f'user@{state["uid"]}.service'])
        service('daemon-reload')
        service('start', 'hermes.service')
        wait_health(state['previous']['config'])
        healthy(state['previous']['config'], inference=True)
    elif state.get('created_account'):
        service('stop', 'hermes.service', allow=True)
        user(['podman', 'rm', '-f', 'hermes'], allow=True)
        run(['loginctl', 'disable-linger', 'hermes'])
        run(['systemctl', 'stop', f'user@{state["uid"]}.service'], allow=True)
        run(['userdel', '--remove', 'hermes'])
        if state.get('created_credential'):
            KEY.unlink(missing_ok=True)
        Path('/run/hermes-simple-secrets/provider.env').unlink(missing_ok=True)
    disarm(state)
    save(state, 'rolled-back')


def dispatch(request):
    action = request['action']
    config = request.get('config')
    if action == 'check':
        return preflight(config)
    protected(ROOT)
    if action == 'status':
        require(STATE.exists(), 'not-installed')
        state = json.loads(STATE.read_text())
        require(state['phase'] == 'closed', 'deployment-not-closed')
        healthy(state['config'])
        return {'ok': True, 'phase': 'closed', 'image': state['config']['image']}
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (ROOT / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = json.loads(STATE.read_text()) if STATE.exists() else {}
        if action == 'recover':
            recover(state)
            return {'ok': True, 'phase': 'rolled-back'}
        if action == 'rollback':
            require(state.get('phase') == 'closed' and state.get('previous'), 'no-previous-deployment')
            save(state, 'rolling-back')
            arm(state, 600)
            recover(state)
            return {'ok': True, 'phase': 'rolled-back'}
        if action == 'prepare':
            preflight(config)
            if state and state.get('phase') not in ('closed', 'rolled-back'):
                recover(state)
            fingerprint = config_fingerprint(config, request['files'])
            if state.get('phase') == 'closed' and state.get('fingerprint') == fingerprint and not request.get('key'):
                healthy(config, inference=True)
                return {'ok': True, 'phase': 'closed', 'unchanged': True}
            previous = state if state.get('phase') == 'closed' else state.get('previous')
            # Adoption of an unrelated installation needs an explicit migration;
            # never overwrite unknown user units or credentials on an existing host.
            if not previous:
                require(not Path('/home/hermes/data').exists(), 'unmanaged-existing-hermes-data')
            require(request.get('key') or KEY.exists(), 'one-time-api-key-required')
            if KEY.exists() and request.get('key'):
                raise Failure('credential-already-provisioned')
            install_payload(request['files'])
            state = {'phase': 'preparing', 'config': config, 'fingerprint': fingerprint,
                     'token': secrets.token_hex(32), 'files': {}, 'previous': previous,
                     'machine_id': Path('/etc/machine-id').read_text().strip()}
            save(state)
            setup_recovery()
            arm(state, 1200)
            try:
                run(['dnf5', 'install', '-y', *PACKAGES], timeout=600)
                state['firewall_was_active'] = run(['systemctl', 'is-active', '--quiet', 'firewalld'], allow=True).returncode == 0
                save(state)
                run(['systemctl', 'enable', '--now', 'firewalld', 'sshd'])
                identity(state)
                credentials(state, request.get('key'))
                user(['podman', 'pull', config['image']], timeout=600)
                require(user(['podman', 'image', 'inspect', config['image'], '--format', '{{.Digest}}']).strip().decode()
                        == config['image'].split('@')[1], 'pulled-digest-mismatch')
                if previous:
                    service('stop', 'hermes.service')
                    snapshot(state)
                configure_access(state)
                save(state, 'awaiting-access')
                disarm(state)
                arm(state, 120)
                return {'ok': True, 'token': state['token'], 'phase': 'awaiting-access'}
            except Exception:
                recover(state)
                raise
        require(state.get('token') == request.get('token') and state.get('config') == config,
                'transaction-binding-mismatch')
        if action == 'confirm-access':
            require(state['phase'] == 'awaiting-access', 'access-phase-mismatch')
            preflight(config)
            save(state, 'access-confirmed')
            disarm(state)
            arm(state, 600)
            return {'ok': True, 'phase': 'access-confirmed'}
        if action == 'deploy':
            require(state['phase'] == 'access-confirmed', 'deployment-phase-mismatch')
            try:
                save(state, 'installing')
                runtime(state)
                save(state, 'closed')
                disarm(state)
                return {'ok': True, 'phase': 'closed', 'image': config['image']}
            except Exception:
                recover(state)
                raise
        raise Failure('unsupported-action')


def main(request):
    os.umask(0o077)
    try:
        result = dispatch(request)
    except (Failure, OSError, KeyError, ValueError, subprocess.SubprocessError) as error:
        # No command output or exception text from subprocesses/provider tools.
        reason = str(error) if isinstance(error, Failure) else type(error).__name__
        print(json.dumps({'ok': False, 'reason': reason}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(globals().get('REQUEST', {'action': sys.argv[1] if len(sys.argv) == 2 else 'invalid'})))
