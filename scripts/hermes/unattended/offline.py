"""Strict DNF replay in systemd's offline-update boot, with durable failure state."""

import argparse
import hashlib
import os
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Failure, atomic, canonical, decode, digest, lock, protected_file, report, require, run

ESP = Path('/boot/efi/EFI/Linux')
ROOT = Path('/var/lib/hermes-unattended/offline')
MARKER = Path('/system-update')
OTHER_MARKER = Path('/etc/system-update')
UNIT = Path('/etc/systemd/system/hermes-offline-replay.service')
WANT = UNIT.parent / 'system-update.target.wants' / UNIT.name


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def state_path(directory, baseline):
    return ROOT / (hashlib.sha256((str(directory) + baseline).encode()).hexdigest() + '.json')


def unit_text(directory, baseline):
    source = Path(__file__).resolve()
    for path in (source, directory):
        require(re.fullmatch(r'/[A-Za-z0-9_./-]+', str(path)) and '..' not in Path(path).parts,
                'unsafe-offline-command-path')
    require(re.fullmatch(r'[a-f0-9]{64}', baseline), 'invalid-offline-baseline')
    return f'''[Unit]
Description=Hermes verified offline package replay
DefaultDependencies=no
Requires=sysinit.target dbus.socket
After=sysinit.target systemd-journald.socket system-update-pre.target
Before=poweroff.target reboot.target shutdown.target system-update.target
FailureAction=reboot

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 -I -B {source} execute --directory {directory} --baseline {baseline}
TimeoutStartSec=25min
UMask=0077
PrivateNetwork=yes
LimitCORE=0
'''.encode()


def stage(directory, baseline, boot_entry=None):
    require(os.geteuid() == 0, 'offline-staging-requires-root')
    directory = Path(directory)
    protected_file(directory / 'transaction.json', 0)
    protected_file(Path(__file__).resolve(), 0)
    content = unit_text(directory, baseline)
    boot = None
    if boot_entry is not None:
        require(isinstance(boot_entry, str) and re.fullmatch(r'hermes-[A-Za-z0-9._-]+\.efi', boot_entry),
                'invalid-offline-boot-entry')
        boot = {'entry': boot_entry, 'sha256': digest(protected_file(ESP / boot_entry, 0))}
    require(not ROOT.is_symlink(), 'unsafe-offline-state')
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    with lock(ROOT / 'stage.lock'):
        for path in (MARKER, OTHER_MARKER, UNIT, WANT):
            require(not path.exists() and not path.is_symlink(), 'offline-update-already-staged')
        target = state_path(directory, baseline)
        require(not target.exists(), 'offline-replay-already-attempted')
        state = {'directory': str(directory), 'baseline': baseline,
                 'expected': protected_file(directory / 'installed-after.sha256', 0).read_text().strip(),
                 'status': 'staging', 'boot_before': boot_id(), 'started_at': int(time.time()),
                 'unit_sha256': hashlib.sha256(content).hexdigest()}
        state['boot'] = boot
        atomic(target, canonical(state))
        atomic(UNIT, content)
        UNIT.chmod(0o644)
        # Validate the actual generated unit before enabling its offline boot hook.
        run(['systemd-analyze', 'verify', str(UNIT)])
        WANT.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        WANT.symlink_to(UNIT)
        state['status'] = 'staged'
        atomic(target, canonical(state))
        MARKER.symlink_to(directory)
        run(['sync', '-f', str(MARKER.parent)])
    return {'stage': 'offline-update-staged'}


def cleanup(state):
    # Never remove a service that an operator has changed since staging.
    require(digest(protected_file(UNIT, 0)) == state['unit_sha256'], 'offline-service-changed')
    require(WANT.is_symlink() and WANT.readlink() == UNIT, 'offline-service-link-changed')
    WANT.unlink()
    UNIT.unlink()


def execute(directory, baseline):
    require(os.geteuid() == 0, 'offline-execution-requires-root')
    directory = Path(directory)
    # Other update managers may have services on the same target. Leave their
    # marker alone and exit successfully if this transaction was not selected.
    if not MARKER.is_symlink() or MARKER.readlink() != directory:
        return {'stage': 'offline-update-not-selected'}
    MARKER.unlink()
    run(['sync', '-f', str(MARKER.parent)])
    target = state_path(directory, baseline)
    state = decode(protected_file(target, 0).read_bytes())
    require(state['directory'] == str(directory) and state['baseline'] == baseline
            and state['status'] == 'staged' and state['boot_before'] != boot_id(),
            'offline-stage-or-boot-mismatch')
    state.update(status='running', update_boot=boot_id())
    atomic(target, canonical(state))
    try:
        from gates import package_baseline, verify_packages
        verify_packages(directory, baseline)
        run(['dnf5', '--disable-repo=*', '--assumeyes', 'replay', str(directory)], timeout=900)
        require(package_baseline() == state['expected'], 'package-replay-result-mismatch')
        if state.get('boot') is not None:
            boot = state['boot']
            require(re.fullmatch(r'hermes-[A-Za-z0-9._-]+\.efi', boot['entry'])
                    and digest(protected_file(ESP / boot['entry'], 0)) == boot['sha256'],
                    'offline-boot-artifact-changed')
            # The old kernel must run replay with its installed modules. Select
            # the new signed UKI only once its matching packages are installed.
            run(['bootctl', '--esp-path=/boot/efi', 'set-default', boot['entry']])
        cleanup(state)
        state.update(status='complete', completed_at=int(time.time()))
        atomic(target, canonical(state))
    except (Failure, OSError, ValueError, KeyError) as error:
        state.update(status='failed', error=getattr(error, 'reason', type(error).__name__),
                     completed_at=int(time.time()))
        atomic(target, canonical(state))
        # FailureAction=reboot returns to normal boot without repeating the update.
        raise Failure(75, 'offline-package-recovery-required') from None
    run(['systemctl', '--no-block', 'reboot'])
    return {'stage': 'offline-replay-complete'}


def require_complete(directory, baseline):
    state = decode(protected_file(state_path(Path(directory), baseline), 0).read_bytes())
    require(state['status'] == 'complete' and state['update_boot'] != boot_id(),
            'offline-package-recovery-required', 75)


def main():
    parser = argparse.ArgumentParser(description='Execute only the staged offline package replay')
    parser.add_argument('command', choices=('execute',))
    parser.add_argument('--directory', required=True)
    parser.add_argument('--baseline', required=True)
    args = parser.parse_args()
    return execute(args.directory, args.baseline)


if __name__ == '__main__':
    report(main)
