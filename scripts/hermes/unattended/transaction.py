"""Validate a stored DNF5 transaction and predict its exact RPM inventory.

The prediction is an expectation, not package-replay evidence. Certification
must compare it with the real inventory after the offline update.
"""

import hashlib
from pathlib import Path, PurePosixPath
import re

from common import decode, protected_file, require

INCOMING = {'Install', 'Upgrade', 'Downgrade', 'Reinstall'}
OUTGOING = {'Remove', 'Replaced'}


def normalize(nevra):
    require(isinstance(nevra, str) and (re.fullmatch(r'[A-Za-z0-9+_.:~^%-]+', nevra)
            or re.fullmatch(r'gpg-pubkey-[a-f0-9:]+-[a-f0-9]+\.\(none\)', nevra)), 'invalid-package-nevra')
    parts = nevra.rsplit('-', 2)
    require(len(parts) == 3 and all(parts), 'invalid-package-nevra')
    name, version, release_arch = parts
    release, separator, arch = release_arch.rpartition('.')
    require(separator and release and arch, 'invalid-package-nevra')
    if ':' not in version:
        version = '0:' + version
    epoch, _, value = version.partition(':')
    require(epoch.isdigit() and value and ':' not in value, 'invalid-package-nevra')
    return name + '-' + str(int(epoch)) + ':' + value + '-' + release + '.' + arch


def expected_inventory(transaction, before):
    require(isinstance(transaction, dict) and set(transaction) == {'version', 'rpms'}
            and transaction['version'] == '1.0' and isinstance(transaction['rpms'], list)
            and transaction['rpms'], 'unsupported-stored-transaction')
    require(isinstance(before, bytes) and before and before.endswith(b'\n'), 'invalid-package-inventory')
    names = [normalize(line) for line in before.decode('ascii').splitlines()]
    require(len(names) == len(set(names)), 'duplicate-installed-package')
    installed = set(names)
    removed, added, reinstalled = set(), set(), set()
    paths = {}
    for record in transaction['rpms']:
        require(isinstance(record, dict), 'invalid-transaction-package')
        action = record.get('action')
        require(action in INCOMING | OUTGOING, 'unsupported-transaction-action')
        name = normalize(record.get('nevra'))
        target = removed if action in OUTGOING else reinstalled if action == 'Reinstall' else added
        require(name not in target, 'duplicate-transaction-package')
        target.add(name)
        if action in INCOMING:
            raw = record.get('package_path')
            require(isinstance(raw, str) and raw, 'missing-stored-package-path')
            relative = PurePosixPath(raw)
            require(not relative.is_absolute() and '..' not in relative.parts
                    and relative.parts[0] == 'packages' and len(relative.parts) == 2
                    and relative.suffix == '.rpm' and '\\' not in raw, 'unsafe-stored-package-path')
            require(str(relative) not in paths, 'duplicate-stored-package-path')
            paths[str(relative)] = name
        else:
            require('package_path' not in record, 'unexpected-outgoing-package-path')
    require(removed <= installed and reinstalled <= installed, 'transaction-baseline-mismatch')
    require(not (added & (installed - removed)) and not (reinstalled & (added | removed)),
            'transaction-package-conflict')
    expected = (installed - removed) | added
    return ''.join(name + '\n' for name in sorted(expected)).encode(), paths


def validate_bundle(directory, baseline):
    directory = Path(directory)
    before = protected_file(directory / 'installed-before.txt').read_bytes()
    require(hashlib.sha256(before).hexdigest() == baseline, 'stored-transaction-baseline-mismatch')
    transaction = decode(protected_file(directory / 'transaction.json').read_bytes())
    expected, paths = expected_inventory(transaction, before)
    for name in paths:
        path = directory / name
        require(not path.parent.is_symlink(), 'unsafe-stored-package-directory')
        protected_file(path)
    require({str(path.relative_to(directory)) for path in directory.rglob('*.rpm')} == set(paths),
            'stored-package-set-mismatch')
    expected_hash = hashlib.sha256(expected).hexdigest()
    require(protected_file(directory / 'installed-after.sha256').read_text().strip() == expected_hash,
            'stored-transaction-result-mismatch')
    return paths
