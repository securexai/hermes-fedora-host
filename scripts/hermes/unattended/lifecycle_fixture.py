"""Root-enrolled fixed-fixture driver. Candidate code runs only as the certifier."""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import secrets
import shlex
import shutil
import sys
import subprocess
import tarfile
import tempfile
import time
import xml.etree.ElementTree as ET

import boot_build
import firmware
import lab_boot
import lab_candidate
import prepare
import tpm_profile
from common import Failure, atomic, canonical, decode, digest, lock, protected_file, require, run
from finalize import validate_candidate
from policy import ssh_options
from release import candidate_fingerprint, sha
from signer import open_owned, owned_path

UUID = '4db6369a-2b8b-427f-a47a-a5d83bb40cff'
DOMAIN = 'lab-hermes-server'
POOL = Path('/var/lib/libvirt/images/hermes-tpm-lab')
DISK = POOL / 'lab-hermes-server.qcow2'
NVRAM = Path('/var/lib/libvirt/qemu/nvram/lab-hermes-server_VARS.fd')
TPM = Path('/var/lib/libvirt/swtpm') / UUID
GUEST = '/usr/local/libexec/hermes-lifecycle-guest'
GUEST_STATE = '/var/lib/hermes-lifecycle-guest'
GATES = {'package_replay', 'inference', 'boot', 'runtime', 'restore', 'vulnerability_scan', 'credential_revocation', 'previous_boot'}
POOL_NAMES = {'owner.json', '.hermes-lab-boot.lock', 'code.fd', 'vars.fd', 'baseline.qcow2',
              'prepared.qcow2', 'lab-hermes-server.qcow2', 'lab-hermes-server-oemdrv.iso', 'installer.iso'}


def unpack_public(stream, destination):
    """Receive only a bounded public transaction/export tree; never tar.extract as root."""
    total, seen = 0, set()
    with tarfile.open(fileobj=stream, mode='r|') as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            require(member.name == str(name) and not name.is_absolute() and '..' not in name.parts
                    and len(name.parts) <= 3 and re.fullmatch(r'[A-Za-z0-9._+^:/~-]+', member.name)
                    and member.name not in seen and not member.pax_headers and not member.issparse(),
                    'unsafe-public-archive')
            seen.add(member.name)
            require(member.isfile() or member.isdir(), 'public-archive-links-forbidden')
            require(name.parts[0] in {'transaction', 'export'}, 'unexpected-public-archive-root')
            total += member.size
            require(0 <= member.size <= 1024**3 and total <= 8 * 1024**3, 'oversized-public-archive')
            target = destination.joinpath(*name.parts)
            for parent in [destination, *list(target.parents)[:len(name.parts) - 1]]:
                require(not parent.is_symlink(), 'linked-public-archive-parent')
            require(not target.is_symlink(), 'linked-public-archive-target')
            if member.isdir():
                target.mkdir(mode=0o700, parents=True, exist_ok=True)
            else:
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with target.open('xb') as output:
                    target.chmod(0o600)
                    shutil.copyfileobj(archive.extractfile(member), output)
                require(target.stat().st_size == member.size, 'truncated-public-archive')


def validate_xml(raw, iso, partial=False):
    try: tree = ET.fromstring(raw)
    except ET.ParseError: raise Failure(78, 'invalid-lifecycle-domain-xml') from None
    require(tree.findtext('name') == DOMAIN and tree.findtext('uuid') == UUID, 'wrong-lifecycle-domain')
    loader = tree.find('./os/loader')
    require(loader is not None and loader.text == str(POOL / 'code.fd') and loader.get('secure') == 'yes'
            and loader.get('readonly') == 'yes', 'wrong-lifecycle-firmware')
    nvram = tree.find('./os/nvram')
    require(nvram is not None and (nvram.text or '').strip() == str(NVRAM), 'wrong-lifecycle-nvram')
    tpm = tree.find('./devices/tpm/backend')
    require(tpm is not None and tpm.get('type') == 'emulator' and tpm.get('version') == '2.0'
            and tpm.find('encryption') is None and tpm.find('source') is None, 'wrong-lifecycle-tpm')
    require(all(tree.find('./os/' + key) is None for key in ('kernel', 'initrd', 'cmdline')),
            'unexpected-direct-boot')
    disks = tree.findall('./devices/disk')
    allowed = {str(DISK)} | ({str(POOL / 'lab-hermes-server-oemdrv.iso'), iso} if partial else set())
    sources = []
    for disk in disks:
        source = disk.find('source')
        require(disk.get('type') == 'file' and source is not None and set(source.attrib) == {'file'},
                'unexpected-domain-storage')
        sources.append(source.get('file'))
    require(len(sources) == len(set(sources)) and str(DISK) in sources and set(sources) <= allowed,
            'wrong-lifecycle-disk-set')
    require(not tree.findall('./devices/filesystem') and not tree.findall('./devices/hostdev'),
            'unexpected-shared-domain-resource')
    return tree


class Fixture:
    def __init__(self, policy, directory, state, save):
        self.policy, self.directory, self.state, self.save = policy, directory, state, save
        self.repository = Path(policy['repository'])
        self.code = self.repository / 'scripts/hermes/unattended'
        self.private = directory / 'private'
        self.work = directory / 'work'
        self.account = pwd.getpwnam(policy['certifier_user'])

    def virsh(self, *args):
        return run(['virsh', '-c', 'qemu:///system', *args], env={**os.environ, 'LC_ALL': 'C'}, timeout=90)

    def source_identity(self):
        files = list(self.code.glob('*.py')) + [self.code / 'lab-dispatch']
        files += list((self.repository / 'scripts/hermes').glob('*'))
        files += list((self.code / 'systemd').glob('*.service')) + list((self.code / 'systemd').glob('*.timer'))
        files += [self.code / 'systemd/hermes-runtime-credentials.service',
                  self.code / 'vulnerability-policy.json']
        files += [self.repository / 'vm' / name for name in (
            'create-hermes-server-vm.sh', 'lib-vm-common.sh', 'lib-hermes-luks-console.sh',
            'kickstart/fedora-server.ks', 'kickstart/hermes-tpm-enroll.ks', 'networks/lab-vlans.xml')]
        result = {}
        for source in files:
            require(not source.is_symlink(), 'linked-lifecycle-source')
            if source.is_dir(): continue
            protected_file(source, 0)
            result[str(source.relative_to(self.repository))] = digest(source)
        require(result, 'missing-lifecycle-source')
        return hashlib.sha256(canonical(result)).hexdigest()

    def check_resources(self, checkpoint):
        memory = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
        record = {'available_memory_kib': int(memory['MemAvailable'].split()[0]),
                  'minimum_memory_kib': 9 * 1024**2,
                  'free_disk_bytes': shutil.disk_usage(POOL.parent).free,
                  'minimum_disk_bytes': 60 * 1024**3,
                  'cpus': os.cpu_count() or 0, 'minimum_cpus': 2}
        self.save(resource_checks={**self.state.get('resource_checks', {}), checkpoint: record})
        require(record['free_disk_bytes'] >= record['minimum_disk_bytes'], 'insufficient-lifecycle-disk')
        require(record['available_memory_kib'] >= record['minimum_memory_kib']
                and record['cpus'] >= record['minimum_cpus'], 'insufficient-lifecycle-resources')

    def preflight(self):
        source = self.source_identity()
        self.save(source_sha256=source)
        names = self.virsh('list', '--all', '--name').decode().splitlines()
        uuids = self.virsh('list', '--all', '--uuid').decode().splitlines()
        require(DOMAIN not in names and UUID not in uuids, 'lifecycle-domain-already-exists')
        for path in (POOL, NVRAM, TPM):
            require(not path.exists() and not path.is_symlink(), 'lifecycle-resource-already-exists')
        self.check_resources('preflight')
        self.check_certifier_tools()
        self.check_broker()
        self.private.mkdir(mode=0o700)
        self.work.mkdir(mode=0o711)
        self.work.chmod(0o711)
        # Only a public, hash-bound source identity enters the journal.
        self.save(inputs_started=True)

    def check_certifier_tools(self):
        from schedule import CERTIFIER_TOOLS
        script = ("import sys; sys.path.insert(0, sys.argv[1]); "
                  "from common import canonical; from schedule import tool_readiness; "
                  "print(canonical(tool_readiness()).decode(), end='')")
        response = decode(run(['runuser', '-u', self.account.pw_name, '--', 'env', '-i',
                               sys.executable, '-B', '-E', '-s', '-c', script, str(self.code)], timeout=30))
        require(response == {'ok': True, 'stage': 'certifier-tools-ready', 'tools': list(CERTIFIER_TOOLS)},
                'certifier-tools-not-ready', 69)
        self.save(certifier_tools_ready=True)

    def check_broker(self):
        # Read-only readiness under the actual certifier UID, before allocating a VM or keys.
        script = ("import sys; sys.path.insert(0, sys.argv[1]); "
                  "from common import canonical; from credentials import client; "
                  "print(canonical(client('/run/hermes-lab-credentials/broker.sock', "
                  "'check', 'test', sys.argv[2])).decode(), end='')")
        response = decode(run(['runuser', '-u', self.account.pw_name, '--', 'env', '-i',
                               'PATH=' + os.environ['PATH'], sys.executable, '-B', '-E', '-s', '-c',
                               script, str(self.code), self.state['run_id'][:32]], timeout=150))
        require(response == {'ok': True, 'role': 'test'}, 'isolated-test-broker-unavailable')

    def inputs(self):
        p, cfg = self.private, self.policy
        status = run(['gpgv', '--status-fd=1', '--keyring', cfg['keyring'], cfg['checksum']])
        fingerprints = [line.split()[2] for line in status.decode().splitlines()
                        if line.startswith('[GNUPG:] VALIDSIG ')]
        require(cfg['fedora_fingerprint'] in fingerprints, 'wrong-fedora-signature')
        entry = 'SHA256 (' + Path(cfg['iso']).name + ') = ' + cfg['iso_sha256']
        require(entry in Path(cfg['checksum']).read_text().splitlines()
                and digest(cfg['iso']) == cfg['iso_sha256'], 'wrong-fedora-media')
        for name in ('sb.key', 'pcr.key'):
            run(['openssl', 'genpkey', '-algorithm', 'RSA', '-pkeyopt', 'rsa_keygen_bits:3072', '-out', str(p / name)])
            (p / name).chmod(0o600)
        run(['openssl', 'req', '-new', '-x509', '-key', str(p / 'sb.key'), '-out', str(p / 'sb.crt'),
             '-days', '30', '-subj', '/CN=Hermes disposable lifecycle/'])
        run(['openssl', 'pkey', '-in', str(p / 'pcr.key'), '-pubout', '-out', str(p / 'pcr.pub')])
        for name in ('operator', 'guest-host'):
            run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'hermes-disposable', '-f', str(p / name)])
        atomic(p / 'recovery.key', secrets.token_hex(32).encode())
        inputs = p / 'installer'; inputs.mkdir(mode=0o700)
        for name, source in [('linux', '/images/pxeboot/vmlinuz'), ('initrd', '/images/pxeboot/initrd.img')]:
            run(['xorriso', '-osirrox', 'on', '-indev', cfg['iso'], '-extract', source, str(inputs / name)], timeout=180)
            (inputs / name).chmod(0o600)
        atomic(inputs / 'osrel', b'ID=fedora\nVERSION_ID=44\n')
        atomic(inputs / 'cmdline', b'inst.stage2=hd:LABEL=Fedora-S-dvd-x86_64-44 '
               b'inst.ks=hd:LABEL=OEMDRV:/ks.cfg console=tty0 console=ttyS0,115200n8\n')
        self.build(inputs, p / 'installer.efi', purpose='installer')
        POOL.mkdir(mode=0o711)
        POOL.chmod(0o711)
        atomic(POOL / 'owner.json', canonical({'run_id': self.state['run_id'], 'binding': self.state['binding']}))
        info = POOL.stat()
        self.save(pool_owned=True, pool_identity=[info.st_dev, info.st_ino])
        self.copy_media()
        for key, name in [('firmware_code', 'code.fd'), ('firmware_vars', 'template.fd')]:
            output = POOL / name if name == 'code.fd' else p / name
            run(['qemu-img', 'convert', '-f', 'qcow2', '-O', 'raw', cfg[key], str(output)])
            output.chmod(0o644 if name == 'code.fd' else 0o600)
            require(output.stat().st_size == (3653632 if name == 'code.fd' else 540672),
                    'four-mib-firmware-pair-required')
        firmware.prepare(p / 'template.fd', p / 'sb.crt', POOL / 'vars.fd')
        run(['restorecon', '-RF', str(POOL)])

    def copy_media(self):
        # libvirt may chown attached media. Never attach the reusable root trust input itself.
        source = protected_file(self.policy['iso'], 0)
        target = POOL / 'installer.iso'
        with source.open('rb') as incoming, target.open('xb') as outgoing:
            target.chmod(0o644)
            shutil.copyfileobj(incoming, outgoing)
        require(digest(target) == self.policy['iso_sha256'], 'copied-installer-media-mismatch')


    def build(self, directory, output, purpose='installed'):
        reviewed = (tpm_profile.inspect_initrd(directory / 'initrd', run,
                    observe=lambda value: self.save(last_initrd_review=value)) if purpose == 'installed' else None)
        _, library = boot_build.toolchain()
        result = boot_build.build({**{name: directory / name for name in ('linux', 'initrd', 'osrel', 'cmdline')},
                                 'stub': library / 'boot/efi/linuxx64.efi.stub'}, output, self.private / 'sb.key',
                                 self.private / 'sb.crt', self.private / 'pcr.key', self.private / 'pcr.pub', purpose)
        if reviewed is not None:
            result['initrd_profile'] = reviewed
        return result

    def check_owned(self, partial=False):
        owner = decode(protected_file(POOL / 'owner.json', 0).read_bytes())
        require(owner == {'run_id': self.state['run_id'], 'binding': self.state['binding']}, 'fixture-owner-mismatch')
        require({p.name for p in POOL.iterdir()} <= POOL_NAMES, 'unexpected-fixture-storage')
        require(all(not p.is_symlink() and p.is_file() for p in POOL.iterdir()), 'unsafe-fixture-storage')
        names = self.virsh('list', '--all', '--name').decode().splitlines()
        for name in names:
            if not name: continue
            raw = self.virsh('dumpxml', name, '--inactive')
            if name == DOMAIN:
                validate_xml(raw, str(POOL / 'installer.iso'), partial)
            else:
                require(all(value.encode() not in raw for value in (str(POOL), str(NVRAM), str(TPM), UUID)),
                        'shared-fixture-resource')
        return DOMAIN in names

    def guestfish(self, commands, writable=False):
        lab_boot.check_domain(UUID)
        data = ''.join(command[0] + ' ' + ' '.join(json.dumps(str(a)) for a in command[1:])
                       + '\n' for command in commands).encode()
        result = run(['guestfish', '--rw' if writable else '--ro', '--format=qcow2', '-a', str(DISK),
                      '--key', 'all:file:' + str(self.private / 'recovery.key'), '--keys-from-stdin', '-i'],
                     data=data, timeout=600)
        lab_boot.check_domain(UUID)
        return result

    def offline_enrollment(self):
        p = self.private
        self.guestfish([('upload', p / 'guest-host', '/etc/ssh/ssh_host_ed25519_key'),
                       ('upload', p / 'guest-host.pub', '/etc/ssh/ssh_host_ed25519_key.pub'),
                       ('chmod', '0600', '/etc/ssh/ssh_host_ed25519_key'),
                       ('chmod', '0644', '/etc/ssh/ssh_host_ed25519_key.pub'),
                       ('chown', '0', '0', '/etc/ssh/ssh_host_ed25519_key'),
                       ('chown', '0', '0', '/etc/ssh/ssh_host_ed25519_key.pub'),
                       ('selinux-relabel', '/etc/selinux/targeted/contexts/files/file_contexts', '/etc/ssh', 'force:true'),
                       ('sync',)], True)
        self.guestfish([('download', '/etc/ssh/ssh_host_ed25519_key.pub', p / 'readback.pub'),
                       ('download', '/etc/machine-id', p / 'machine-id'),
                       ('download', '/root/.hermes-tpm-stage', p / 'stage')])
        require((p / 'stage').read_text().strip() == 'tpm-enrolled-awaiting-signed-uki'
                and (p / 'readback.pub').read_bytes() == (p / 'guest-host.pub').read_bytes(), 'recovery-readback-failed')
        key = ' '.join((p / 'readback.pub').read_text().split()[:2])
        require(re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]+', key), 'invalid-guest-host-public-key')
        atomic(p / 'known_hosts', ('172.16.99.12 ' + key + '\n').encode())
        host = {'machine_id_sha256': digest(p / 'machine-id'),
                'ssh_fingerprint': run(['ssh-keygen', '-lf', str(p / 'readback.pub'), '-E', 'sha256']).decode().split()[1]}
        atomic(p / 'host.json', canonical(host))
        atomic(p / 'binding.json', canonical({'run_id': self.state['run_id'], 'host': host}))
        commands = [('mkdir-p', GUEST), ('mkdir-p', GUEST_STATE + '/payload'),
                    ('chmod', '0700', GUEST_STATE), ('upload', p / 'binding.json', GUEST_STATE + '/binding.json')]
        sources = {source.name: source for source in self.code.glob('*.py')}
        sources['lab-dispatch'] = self.code / 'lab-dispatch'
        for name, source in sources.items():
            commands += [('upload', source, GUEST + '/' + name), ('chmod', '0644', GUEST + '/' + name)]
        for name in ('host.py', 'common.py', 'gates.py', 'materialize.py', 'transaction.py', 'offline.py'):
            commands.append(('upload', self.code / name, GUEST_STATE + '/payload/' + name))
        for name in ('hermes.container', '60-hermes-runtime.conf', '70-hermes-volume-label.conf', 'harden-config.py', 'set-model.py'):
            commands.append(('upload', self.repository / 'scripts/hermes' / name, GUEST_STATE + '/payload/' + name))
        commands += [('upload', self.code / 'systemd/hermes-runtime-credentials.service',
                      GUEST_STATE + '/payload/hermes-runtime-credentials.service'), ('sync',)]
        self.guestfish(commands, True)
        self.save(guest_identity=host, recovery_readback=True)

    def ssh(self):
        return ssh_options({'target': 'lab@172.16.99.12', 'identity_file': str(self.private / 'operator'),
                            'known_hosts': str(self.private / 'known_hosts')})

    def guest(self, action, **message):
        require(action in {'bootstrap', 'store', 'replay', 'replay-status', 'export', 'observe', 'enroll', 'purge'}, 'invalid-guest-action')
        command = self.ssh() + ["sudo -n /usr/bin/bash -c " + shlex.quote(
            'exec /usr/bin/python3 -I -B ' + GUEST + '/lifecycle_guest.py ' + action)]
        try:
            process = subprocess.run(command, input=canonical({'run_id': self.state['run_id'], **message}),
                                     capture_output=True, timeout=1500)
        except subprocess.TimeoutExpired:
            raise Failure(69, 'lifecycle-guest-timeout') from None
        if process.returncode == 255 and not process.stdout:
            raise Failure(69, 'lifecycle-transport-unavailable')
        require(len(process.stdout) <= 65536, 'oversized-guest-result')
        result = decode(process.stdout)
        require(process.returncode == 0 and result.get('ok') is True, 'lifecycle-guest-operation-failed')
        return result

    def wait_ssh(self, previous=None, timeout=600):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                boot = run(self.ssh() + ['cat /proc/sys/kernel/random/boot_id'], timeout=20).decode().strip()
                require(re.fullmatch(r'[0-9a-f-]{36}', boot), 'invalid-guest-boot-id')
                if previous is None or boot != previous: return boot
            except Failure: pass
            time.sleep(3)
        raise Failure(69, 'lifecycle-ssh-timeout')

    def poweroff(self):
        self.check_owned()
        if self.virsh('domstate', DOMAIN).strip() == b'shut off': return
        self.virsh('shutdown', DOMAIN)
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if self.virsh('domstate', DOMAIN).strip() == b'shut off': return
            time.sleep(3)
        raise Failure(69, 'lifecycle-shutdown-timeout')

    def boot_manager(self):
        run(self.ssh() + ["sudo -n /usr/bin/bash -c 'dnf5 --assumeyes --setopt=install_weak_deps=False "
                          "install sbsigntools systemd-boot-unsigned'"], timeout=900)
        p = self.private
        unsigned = run(self.ssh() + ['cat /usr/lib/systemd/boot/efi/systemd-bootx64.efi'])
        require(0 < len(unsigned) < 4 * 1024**2, 'oversized-boot-manager')
        atomic(p / 'manager-unsigned.efi', unsigned)
        run(['sbsign', '--key', str(p / 'sb.key'), '--cert', str(p / 'sb.crt'),
             '--output', str(p / 'manager.efi'), str(p / 'manager-unsigned.efi')])
        run(['sbverify', '--cert', str(p / 'sb.crt'), str(p / 'manager.efi')])
        self.poweroff()
        self.guestfish([('mkdir-p', GUEST_STATE + '/boot'),
                       ('upload', p / 'manager.efi', GUEST_STATE + '/boot/boot-manager.efi'),
                       ('upload', p / 'installed.efi', GUEST_STATE + '/boot/previous.efi'),
                       ('upload', p / 'sb.crt', GUEST_STATE + '/boot/uki.crt'), ('sync',)], True)
        self.virsh('start', DOMAIN); boot = self.wait_ssh()
        run(self.ssh() + ["sudo -n /usr/bin/bash -c " + shlex.quote(
            'exec /usr/bin/python3 -I -B ' + GUEST + '/lab_enroll_boot.py --directory ' + GUEST_STATE
            + '/boot --domain-uuid ' + UUID)], timeout=180)
        run(self.ssh() + ["sudo -n /usr/bin/bash -c 'systemd-run --unit=hermes-lifecycle-boot-reboot "
                          "--on-active=5s /usr/bin/systemctl reboot'"])
        self.wait_ssh(boot)
        self.guest('observe')

    def prepare(self):
        self.preflight(); self.inputs()
        self.check_resources('before-installer')
        p = self.private
        self.save(install_started=True)
        run([str(self.repository / 'vm/create-hermes-server-vm.sh'), '--iso', str(POOL / 'installer.iso'),
             '--ssh-key', str(p / 'operator.pub'), '--tpm-stage', '--tpm-public-key', str(p / 'pcr.pub'),
             '--firmware-code', str(POOL / 'code.fd'), '--firmware-vars', str(POOL / 'vars.fd'),
             '--installer-uki', str(p / 'installer.efi'), '--boot-certificate', str(p / 'sb.crt'),
             '--recovery-key-file', str(p / 'recovery.key')], timeout=2100)
        self.check_owned()
        with lock(POOL / '.hermes-lab-boot.lock'):
            self.offline_enrollment()
            inputs = p / 'installed'; inputs.mkdir(mode=0o700)
            lab_candidate.extract(UUID, p / 'pcr.pub', inputs)
            built = self.build(inputs, p / 'installed.efi')
            self.save(baseline_initrd_review=built['initrd_profile'])
            with tempfile.TemporaryDirectory(dir=p) as directory:
                command, _ = lab_boot.inject(UUID, p / 'installed.efi', p / 'sb.crt', p / 'pcr.pub', Path(directory))
            lab_boot.first_boot(UUID, command, p / 'operator', p / 'known_hosts', 600)
        self.save(guest_ready=True)
        self.boot_manager()
        self.guest('bootstrap', model=self.policy['model'])
        stored = self.guest('store'); self.save(baseline=stored['baseline'])
        self.poweroff()
        lab_boot.check_domain(UUID)
        run(['qemu-img', 'convert', '-f', 'qcow2', '-O', 'qcow2', str(DISK), str(POOL / 'baseline.qcow2')], timeout=600)
        run(['qemu-img', 'check', str(POOL / 'baseline.qcow2')], timeout=120)
        run(['qemu-img', 'compare', str(DISK), str(POOL / 'baseline.qcow2')], timeout=600)
        self.save(baseline_saved=True)
        self.virsh('start', DOMAIN); boot = self.wait_ssh()
        self.guest('replay')
        self.wait_ssh(boot, 1800)
        # The offline replay reboots twice; poll its durable completion, not SSH availability alone.
        deadline = time.monotonic() + 1800
        while True:
            try:
                if self.guest('replay-status')['complete']: break
            except Failure as error:
                if error.reason != 'lifecycle-transport-unavailable': raise
            require(time.monotonic() < deadline, 'preparation-replay-incomplete')
            time.sleep(10)
        exported = self.guest('export')
        download = p / 'download'; download.mkdir(mode=0o700)
        with tempfile.TemporaryFile(dir=p) as archive:
            run(self.ssh() + ["sudo -n /usr/bin/bash -c 'exec tar --format=ustar -C " + GUEST_STATE
                              + " -cf - transaction export'"], stdout=archive, timeout=600)
            require(archive.tell() < 8 * 1024**3, 'oversized-public-download')
            archive.seek(0); unpack_public(archive, download)
        for name, record in exported['files'].items():
            require(name in {'linux', 'initrd', 'osrel', 'cmdline'}, 'unknown-boot-export')
            path = download / 'export' / name
            require(digest(path) == record['sha256'] and path.stat().st_size == record['size'], 'boot-download-mismatch')
        built = self.build(download / 'export', p / 'updated.efi')
        self.save(updated_initrd_review=built['initrd_profile'])
        self.poweroff(); lab_boot.check_domain(UUID)
        run(['qemu-img', 'check', str(POOL / 'baseline.qcow2')], timeout=120)
        DISK.rename(POOL / 'prepared.qcow2')
        run(['qemu-img', 'convert', '-f', 'qcow2', '-O', 'qcow2', str(POOL / 'baseline.qcow2'), str(DISK)], timeout=600)
        run(['qemu-img', 'compare', str(DISK), str(POOL / 'baseline.qcow2')], timeout=600)
        run(['restorecon', '-RF', str(POOL)])
        self.virsh('start', DOMAIN); self.wait_ssh()
        require(self.guest('observe')['baseline'] == self.state['baseline'], 'restored-baseline-mismatch')
        self.save(kernel=exported['kernel'])
        self.enroll_candidate()

    def as_certifier(self, *arguments, timeout=7000):
        with tempfile.TemporaryFile() as output:
            run(['runuser', '-u', self.account.pw_name, '--', 'env', '-i',
                 'PATH=' + os.environ['PATH'], sys.executable, '-B', '-E', '-s',
                 str(self.code / 'schedule.py'), '--config', str(self.directory / 'schedule.json'),
                 '--events', str(self.work / 'events'), *arguments], stdout=output, timeout=timeout)
            require(output.tell() <= 65536, 'oversized-scheduler-output')
            output.seek(0); lines = output.read().splitlines()
        require(lines, 'missing-scheduler-output')
        result = decode(lines[-1])
        require(result.get('ok') is True, 'scheduler-failed')
        return result

    def initialize_backup(self, backup, password):
        run(['runuser', '-u', self.account.pw_name, '--', 'env', '-i',
             'PATH=' + os.environ['PATH'], 'restic', '--no-cache', '--repo', str(backup),
             '--password-file', str(password), 'init'], timeout=120)


    def enroll_candidate(self):
        uid, gid = self.account.pw_uid, self.account.pw_gid
        for name in ('state', 'evidence', 'schedule', 'events', 'candidates'):
            path = self.work / name; path.mkdir(mode=0o700); os.chown(path, uid, gid)
        inputs = self.private / 'certifier-inputs'
        inputs.mkdir(mode=0o700)
        shutil.copytree(self.private / 'download/transaction', inputs / 'transaction')
        shutil.copyfile(self.private / 'updated.efi', inputs / 'updated.efi')
        shutil.copyfile(self.private / 'host.json', inputs / 'host.json')
        run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'hermes-certifier', '-f', str(inputs / 'ssh-key')])
        shutil.copyfile(self.private / 'known_hosts', inputs / 'known_hosts')
        atomic(inputs / 'backup-password', secrets.token_hex(32).encode())
        for path in inputs.rglob('*'):
            require(not path.is_symlink(), 'linked-certifier-input')
            os.chown(path, uid, gid); path.chmod(0o700 if path.is_dir() else 0o600)
        os.chown(inputs, uid, gid)
        inputs.rename(self.work / 'inputs')
        inputs = self.work / 'inputs'
        backup = self.work / 'backup'
        backup.mkdir(mode=0o700); os.chown(backup, uid, gid)
        self.initialize_backup(backup, inputs / 'backup-password')
        config = {'schema': 'hermes-certify-v1', 'certifier_uid': uid, 'domain_uuid': UUID,
                  'target': 'hermes-certify@172.16.99.12', 'identity_file': str(inputs / 'ssh-key'),
                  'known_hosts': str(inputs / 'known_hosts'), 'candidate': str(self.work / 'candidates/candidate'),
                  'state_dir': str(self.work / 'state'), 'evidence_dir': str(self.work / 'evidence'),
                  'credential_socket': '/run/hermes-lab-credentials/broker.sock',
                  'backup_repository': str(self.work / 'backup'), 'backup_password_file': str(inputs / 'backup-password'),
                  'run_id': self.state['run_id'], 'kernel': self.state['kernel']}
        atomic(self.directory / 'certifier.json', canonical(config)); (self.directory / 'certifier.json').chmod(0o644)
        recipe = {'repository': str(self.repository), 'transaction': str(inputs / 'transaction'),
                  'uki': str(inputs / 'updated.efi'), 'host_identity': str(inputs / 'host.json'),
                  'release_id': 'lifecycle-' + self.state['run_id'][:24], 'model': self.policy['model'],
                  'baseline': self.state['baseline']}
        atomic(self.directory / 'schedule.json', canonical({'schema': 'hermes-schedule-v1',
               'certifier_config': str(self.directory / 'certifier.json'), 'state_dir': str(self.work / 'schedule'),
               'prepare': recipe})); (self.directory / 'schedule.json').chmod(0o644)
        self.save(scheduler_ready=True)
        require(self.as_certifier('--prepare-only', timeout=900)['stage'] == 'prepared', 'candidate-not-prepared')
        manifest, raw = self.read_candidate()
        require(manifest['host'] == self.state['guest_identity'] and manifest['baseline_sha256'] == self.state['baseline'],
                'wrong-prepared-host')
        self.approve_candidate(manifest)
        atomic(self.directory / 'frozen.json', raw)
        self.save(candidate_sha256=hashlib.sha256(raw).hexdigest(), artifact_fingerprint=candidate_fingerprint(manifest),
                  release_id=manifest['release_id'])
        with open_owned(inputs / 'ssh-key.pub', uid) as stream:
            key = ' '.join(stream.read(1024).decode().split()[:2])
        result = self.guest('enroll', policy={'schema': 'hermes-lab-certifier-v1', 'domain_uuid': UUID,
                            'host': manifest['host'], 'candidate_sha256': self.state['candidate_sha256'],
                            'run_id': self.state['run_id'], 'kernel': self.state['kernel']}, public_key=key)
        require(result.get('candidate_sha256') == self.state['candidate_sha256']
                and result.get('run_id') == self.state['run_id'] and result.get('production_enabled') is False,
                'guest-enrollment-not-confirmed')
        self.save(candidate_enrolled=True)

    def approve_candidate(self, manifest):
        # The certifier may report evidence, but cannot select code for guest-root execution.
        # Reconstruct the selected candidate from root-owned preparation inputs independently.
        require(self.source_identity() == self.state['source_sha256'], 'lifecycle-source-changed')
        reference = self.private / 'approved-candidate'
        prepare.prepare(self.repository, reference, self.private / 'download/transaction',
                        self.private / 'updated.efi', self.state['guest_identity'],
                        'lifecycle-' + self.state['run_id'][:24], self.policy['model'], self.state['baseline'])
        approved = validate_candidate(decode(protected_file(reference / 'candidate.json', 0).read_bytes()))
        require(candidate_fingerprint(manifest) == candidate_fingerprint(approved),
                'certifier-selected-unapproved-candidate')
        atomic(self.directory / 'approved.json', canonical(approved))
        shutil.rmtree(reference)

    def read_candidate(self):
        root, uid = self.work / 'candidates/candidate', self.account.pw_uid
        with open_owned(root / 'candidate.json', uid) as stream: raw = stream.read(1024**2 + 1)
        require(len(raw) <= 1024**2, 'oversized-candidate-manifest')
        manifest = validate_candidate(decode(raw))
        for name, record in manifest['files'].items():
            with open_owned(root / name, uid) as stream:
                require(os.fstat(stream.fileno()).st_size == record['size']
                        and hashlib.file_digest(stream, 'sha256').hexdigest() == record['sha256'], 'candidate-file-changed')
        return manifest, raw

    def evidence(self, name):
        with open_owned(self.work / 'evidence' / (name + '.json'), self.account.pw_uid) as source:
            raw = source.read(1024**2 + 1)
        require(len(raw) <= 1024**2, 'oversized-lifecycle-evidence')
        value = decode(raw)
        require(value['gate'] == name and value['result'] == 'PASS' and value['run_id'] == self.state['run_id']
                and value['artifact_fingerprint'] == self.state['artifact_fingerprint']
                and value['release_id'] == self.state['release_id'] and type(value['completed_at']) is int,
                'mixed-lifecycle-evidence')
        return value

    def certify(self):
        require(self.source_identity() == self.state['source_sha256'], 'lifecycle-source-changed')
        arguments = []
        if 'lab_window' in self.state:
            from lifecycle import identity
            from schedule import binding
            grant = self.state['lab_window']
            require(grant['binding'] == identity(self.policy) and grant['run_id'] == self.state['run_id']
                    and grant['issued_at'] <= int(time.time()) < grant['expires_at'],
                    'expired-lifecycle-certification-window')
            policy = decode(protected_file(self.directory / 'schedule.json', 0).read_bytes())
            config = decode(protected_file(self.directory / 'certifier.json', 0).read_bytes())
            path = self.directory / 'candidate-window.json'
            atomic(path, canonical({'schema': 'hermes-lab-window-v1', 'binding': binding(policy, config),
                   'run_id': self.state['run_id'], 'candidate_sha256': self.state['candidate_sha256'],
                   'issued_at': grant['issued_at'], 'expires_at': grant['expires_at']}))
            path.chmod(0o644)
            arguments = ['--lab-window-grant', str(path)]
        result = self.as_certifier(*arguments)
        require(result['stage'] == 'ua03-complete' and result.get('release_signed') is False, 'lifecycle-certification-incomplete')
        _, raw = self.read_candidate()
        require(hashlib.sha256(raw).hexdigest() == self.state['candidate_sha256'], 'lifecycle-candidate-changed')
        evidence = {name: self.evidence(name) for name in GATES}
        atomic(self.directory / 'acceptance.json', canonical(evidence))

    def verify_destroyed_domain(self):
        require(DOMAIN not in self.virsh('list', '--all', '--name').decode().splitlines()
                and UUID not in self.virsh('list', '--all', '--uuid').decode().splitlines(),
                'domain-destruction-incomplete')
        require(all(not path.exists() and not path.is_symlink() for path in (NVRAM, TPM)),
                'firmware-or-tpm-remains')
        processes = run(['ps', '-eo', 'args=']).decode().splitlines()
        require(not any(('qemu-system' in line or 'swtpm socket' in line)
                        and any(name in line for name in (UUID, 'guest=' + DOMAIN, str(POOL))) for line in processes),
                'fixture-process-remains')

    def purge_storage(self):
        # Keep an inode-bound deletion checkpoint across interruption after undefine or unlink.
        require(self.state.get('domain_destroyed'), 'domain-must-be-destroyed-first')
        if POOL.exists() or POOL.is_symlink():
            owned_path(POOL, 0, directory=True)
            info = POOL.stat()
            require([info.st_dev, info.st_ino] == self.state['pool_identity'], 'fixture-pool-replaced')
            cookie = POOL / 'owner.json'
            if cookie.exists():
                require(not self.check_owned(partial=True), 'domain-reappeared-before-storage-purge')
                self.save(storage_purge_started=True)
                for path in POOL.iterdir():
                    if path.name != 'owner.json': path.unlink()
                cookie.unlink()
            else:
                require(self.state.get('storage_purge_started') and not list(POOL.iterdir()),
                        'fixture-owner-missing')
            POOL.rmdir()
        else:
            require(self.state.get('storage_purge_started'), 'fixture-pool-disappeared')
        self.save(vm_destroyed=True)

    def cleanup(self):
        # Credential reconciliation must succeed before removing recovery paths or the VM.
        if self.state.get('scheduler_ready') and not self.state.get('credentials_cleaned'):
            result = self.as_certifier('--cleanup-only', timeout=400)
            require(result['stage'] in {'credential-cleanup-complete', 'no-certifier-state'}, 'credential-cleanup-incomplete')
            self.save(credentials_cleaned=True)
        if self.state.get('domain_destroyed') and not self.state.get('vm_destroyed'):
            self.verify_destroyed_domain()
            self.purge_storage()
        if self.state.get('pool_owned') and not self.state.get('vm_destroyed'):
            exists = self.check_owned(partial=True)
            if self.state.get('guest_ready') and not self.state.get('guest_purged'):
                if exists and self.virsh('domstate', DOMAIN).strip() == b'shut off':
                    self.virsh('start', DOMAIN); self.wait_ssh()
                require(exists, 'guest-disappeared-before-purge')
                require(self.guest('purge')['stage'] == 'guest-data-purged', 'guest-purge-incomplete')
                self.save(guest_purged=True)
            # Retain public candidate and evidence. Delete only this run's disposable secrets/backups.
            if not self.state.get('certifier_secrets_purged'):
                for path in (self.work / 'backup', self.work / 'inputs'):
                    require(not path.is_symlink(), 'linked-certifier-purge-root')
                    if path.exists(): shutil.rmtree(path)
                self.save(certifier_secrets_purged=True)
            self.check_owned(partial=True)
            if exists:
                if self.virsh('domstate', DOMAIN).strip() != b'shut off': self.virsh('destroy', DOMAIN)
                self.virsh('undefine', DOMAIN, '--nvram', '--tpm')
            self.verify_destroyed_domain()
            self.save(domain_destroyed=True)
            self.purge_storage()
        if self.private.exists():
            require(not self.private.is_symlink(), 'linked-private-purge-root')
            shutil.rmtree(self.private)
        require(not self.private.exists() and not self.private.is_symlink(), 'private-fixture-state-remains')
        self.save(private_purged=True)
        # This record is a lifecycle observation, not a signer request or synthetic promotion evidence.
        atomic(self.directory / 'cleanup.json', canonical({'schema': 'hermes-lifecycle-cleanup-v1',
               'run_id': self.state['run_id'], 'candidate_sha256': self.state.get('candidate_sha256'),
               'credentials_reconciled': self.state.get('credentials_cleaned', False),
               'guest_purged': self.state.get('guest_purged', False),
               'domain_absent': self.state.get('vm_destroyed', False),
               'private_material_absent': True, 'logical_deletion': True, 'release_signed': False,
               'completed_at': int(time.time())}))
