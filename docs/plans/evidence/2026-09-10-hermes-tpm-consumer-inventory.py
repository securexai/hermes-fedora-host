"""Bounded read-only custom-consumer inventory; emit paths/kinds, never contents."""

import argparse
import datetime
import json
import os
from pathlib import Path
import pwd
import re
import shlex
import stat
import subprocess

DIRECTORIES = (
    '/etc/systemd/system', '/run/systemd/system', '/etc/udev/rules.d',
    '/etc/cron.d', '/etc/cron.hourly', '/etc/cron.daily', '/etc/cron.weekly', '/etc/cron.monthly',
    '/var/spool/cron', '/usr/local/bin', '/usr/local/sbin', '/usr/local/libexec', '/opt',
)
PATTERNS = {
    'nvpcr': rb'(?i)nvpcr|0x0?1d1020[01]',
    'pcrlock': rb'(?i)pcrlock',
    'tpm_sealing_or_measurement': rb'tpm2_(?:create|load|unseal|policy|nv|pcrextend)|systemd-(?:creds|cryptenroll|pcrextend)',
    'attestation': rb'(?i)keylime|attest|tpm2_quote|tpm2_checkquote',
}


def collect(root=Path('/'), homes=None, package_output=None, protected_only=False):
    root = Path(root)
    result = {'schema': 'hermes-custom-tpm-inventory-v1',
              'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'effective_uid': os.geteuid(), 'hits': [], 'unreviewed': [], 'scanned_files': 0,
              'scanned_bytes': 0, 'directories': [], 'walked_directories': 0}
    if homes is None:
        homes = sorted({entry.pw_dir for entry in pwd.getpwall()
                        if entry.pw_dir == '/root' or entry.pw_dir.startswith(('/home/', '/var/home/'))})
    directories = list(DIRECTORIES) + [home + suffix for home in homes
                                     for suffix in ('/.config/systemd/user', '/.config/containers/systemd')]
    if protected_only:
        directories = ['/var/spool/cron'] + [name for name in directories
                                            if name.startswith(('/root/', '/home/hermes/', '/var/home/hermes/'))]
        package_output = b''
    result['scope'] = 'protected-consumer-remainder' if protected_only else 'bounded-custom-execution-paths'
    seen = set()

    def unresolved(path, reason):
        result['unreviewed'].append({'path': '/' + str(path.relative_to(root)), 'reason': reason})

    for name in directories:
        directory = root / name.lstrip('/')
        if (name == '/usr/local/sbin' and directory.is_symlink()
                and os.readlink(directory) in {'bin', '/usr/local/bin'}
                and not (root / 'usr/local/bin').is_symlink()):
            result['directories'].append({'path': name, 'state': 'alias-of-scanned-directory',
                                          'target': '/usr/local/bin'})
            continue
        if any(p.is_symlink() for p in (directory, *directory.parents) if p != root):
            unresolved(directory, 'symlink-not-followed')
            continue
        try:
            directory.stat()
        except FileNotFoundError:
            result['directories'].append({'path': name, 'state': 'absent'})
            continue
        except PermissionError:
            unresolved(directory, 'permission-denied')
            continue
        result['directories'].append({'path': name, 'state': 'visited'})
        for parent, dirs, files in os.walk(directory, followlinks=False,
                                           onerror=lambda error: unresolved(Path(error.filename), 'walk-error')):
            result['walked_directories'] += 1
            if result['walked_directories'] > 1000:
                unresolved(Path(parent), 'directory-count-bound')
                result['coverage_complete'] = False
                return result
            for child in list(dirs):
                p = Path(parent) / child
                if p.is_symlink():
                    unresolved(p, 'symlink-not-followed')
                    dirs.remove(child)
            for child in sorted(files):
                p = Path(parent) / child
                if p in seen:
                    continue
                seen.add(p)
                if len(seen) > 5000:
                    unresolved(p, 'file-count-bound')
                    result['coverage_complete'] = False
                    return result
                try:
                    s = p.lstat()
                    if stat.S_ISLNK(s.st_mode):
                        # Packaged unit enablement links are already accounted for by unit metadata.
                        target = os.readlink(p)
                        if target == '/dev/null' or target.startswith('/usr/lib/systemd/system/'):
                            continue
                        unresolved(p, 'symlink-not-followed')
                        continue
                    if not stat.S_ISREG(s.st_mode):
                        unresolved(p, 'nonregular-not-read')
                        continue
                    if not (s.st_mode & 0o111 or p.suffix in {'.service', '.socket', '.timer', '.target', '.path',
                                                           '.conf', '.rules', '.sh', '.py', '.pl', '.container',
                                                           '.volume', '.network', '.pod', '.kube', '.build'} or '/cron' in name):
                        unresolved(p, 'unclassified-file-not-read')
                        continue
                    if s.st_size > 2 * 1024**2 or result['scanned_bytes'] + s.st_size > 32 * 1024**2:
                        unresolved(p, 'size-bound')
                        continue
                    # No FIFO/device following or symlink resolution at the final component.
                    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                    with os.fdopen(fd, 'rb') as stream:
                        current = os.fstat(stream.fileno())
                        if (current.st_dev, current.st_ino, current.st_size) != (s.st_dev, s.st_ino, s.st_size):
                            unresolved(p, 'changed-during-inventory')
                            continue
                        data = stream.read(2 * 1024**2 + 1)
                    result['scanned_bytes'] += len(data)
                    if len(data) > 2 * 1024**2 or b'\0' in data:
                        unresolved(p, 'binary-or-growing-file-not-interpreted')
                        continue
                    result['scanned_files'] += 1
                    kinds = [key for key, pattern in PATTERNS.items() if re.search(pattern, data)]
                    if kinds:
                        result['hits'].append({'file': '/' + str(p.relative_to(root)), 'kinds': kinds})
                except (PermissionError, OSError):
                    unresolved(p, 'unreadable-or-raced')
    if package_output is None:
        proc = subprocess.run(['rpm', '-qa', '--qf', '%{NAME}\n'], stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=60)
        if proc.returncode:
            result['package_query_failed'] = True
            package_output = b''
        else:
            package_output = proc.stdout
    result['relevant_packages'] = sorted({name for name in package_output.decode().splitlines()
                                         if re.search(r'(?i)tpm|tss|keylime|attest|clevis|tang|ima-evm', name)})
    result['coverage_complete'] = not result['unreviewed'] and not result.get('package_query_failed')
    result['consumer_absence_proven'] = False
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protected-only', action='store_true')
    parser.add_argument('--remote', action='store_true', help='Interactive pinned SSH read; no file is staged on Hermes')
    args = parser.parse_args()
    if args.remote:
        command = 'sudo /usr/bin/python3 -I -B -c ' + shlex.quote(Path(__file__).read_text()) + ' --protected-only'
        # Keep authentication on the operator terminal; never capture a password.
        with open('/dev/tty', 'r+b', buffering=0) as terminal:
            subprocess.run(['ssh', '-tt', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'IdentitiesOnly=yes',
                            '-o', 'ConnectTimeout=10', 'aicowork@10.0.30.10', command],
                           stdin=terminal, stdout=terminal, stderr=terminal, timeout=240, check=True)
    else:
        print(json.dumps(collect(protected_only=args.protected_only), indent=2))
