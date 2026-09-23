"""Previous-image lab checks. Called only behind the enrolled candidate endpoint."""

import hashlib
import os
from pathlib import Path
import re
import stat

from common import atomic, canonical, decode, digest, protected_file, require, run

ESP = Path('/boot/efi/EFI/Linux')
RECORD = Path('/var/lib/hermes-lab-certification/previous.json')
ENROLLMENT = Path('/var/lib/hermes-lab-boot-enrollment/state.json')
PREVIOUS = 'hermes-enrollment.efi'
MODULES = Path('/usr/lib/modules')


def modules(kernel):
    require(isinstance(kernel, str) and re.fullmatch(r'[A-Za-z0-9._+-]+', kernel), 'invalid-previous-kernel')
    root = MODULES / kernel
    require(root.is_dir() and not root.is_symlink(), 'previous-modules-missing')
    records = {}
    # Hash loadable modules and modules.* metadata, retaining symlink targets without following them.
    # build/source links may legitimately point outside the installed module tree.
    for path in sorted(root.rglob('*')):
        info = path.lstat()
        name = str(path.relative_to(root))
        if stat.S_ISLNK(info.st_mode):
            records[name] = {'link': os.readlink(path)}
        elif stat.S_ISREG(info.st_mode):
            records[name] = {'sha256': digest(path), 'mode': stat.S_IMODE(info.st_mode)}
        else:
            require(stat.S_ISDIR(info.st_mode), 'unexpected-module-file-type')
    require(any('.ko' in name for name in records) and 'modules.dep' in records, 'incomplete-previous-modules')
    return hashlib.sha256(canonical(records)).hexdigest()


def selected():
    entries = decode(run(['bootctl', '--esp-path=/boot/efi', '--json=short', 'list']))
    values = [entry['id'] for entry in entries if entry.get('isSelected')]
    require(len(values) == 1, 'ambiguous-selected-lab-entry')
    return values[0]


def capture(policy):
    if RECORD.exists():
        return retained(policy)
    require(not RECORD.is_symlink(), 'linked-previous-record')
    enrollment = decode(protected_file(ENROLLMENT, 0).read_bytes())
    target = protected_file(ESP / PREVIOUS, 0)
    require(digest(target) == enrollment['binding']['previous.efi'] and selected() == PREVIOUS,
            'previous-baseline-not-selected')
    run(['sbverify', '--cert', '/etc/hermes-unattended/uki.crt', str(target)])
    kernel = run(['uname', '-r']).decode().strip()
    require(kernel != policy['kernel'], 'previous-and-updated-kernel-identical')
    value = {'run_id': policy['run_id'], 'candidate_sha256': policy['candidate_sha256'],
             'entry': PREVIOUS, 'uki_sha256': digest(target), 'kernel': kernel,
             'modules_sha256': modules(kernel)}
    atomic(RECORD, canonical(value))
    return value


def retained(policy):
    value = decode(protected_file(RECORD, 0).read_bytes())
    require(value['run_id'] == policy['run_id'] and value['candidate_sha256'] == policy['candidate_sha256']
            and value['entry'] == PREVIOUS, 'previous-record-binding-mismatch')
    require(digest(protected_file(ESP / PREVIOUS, 0)) == value['uki_sha256'], 'previous-image-changed')
    require(modules(value['kernel']) == value['modules_sha256'], 'previous-modules-changed')
    return value


def select(policy, manifest, previous):
    retained(policy)
    state = decode(protected_file(Path('/var/lib/hermes-unattended') /
                                  (manifest['release_id'] + '.state.json'), 0).read_bytes())
    require(state['phase'] == 'closed', 'previous-test-requires-completed-update')
    new = 'hermes-' + manifest['release_id'] + '.efi'
    require(digest(protected_file(ESP / new, 0)) == manifest['files'][manifest['boot_artifact']]['sha256'],
            'updated-image-changed')
    entries = decode(run(['bootctl', '--esp-path=/boot/efi', '--json=short', 'list']))
    require([entry['id'] for entry in entries if entry.get('isDefault')] == [new], 'updated-default-not-retained')
    entry = PREVIOUS if previous else new
    run(['sbverify', '--cert', '/etc/hermes-unattended/uki.crt', str(ESP / entry)])
    run(['bootctl', '--esp-path=/boot/efi', 'set-oneshot', entry])
    return {'ok': True, 'stage': 'one-shot-selected', 'entry': entry, 'default': new}


def verify_sequence(updated, previous, returned):
    require(len({item['boot_id'] for item in (updated, previous, returned)}) == 3,
            'previous-test-boot-id-reused')
    require(updated['kernel'] == returned['kernel'] and previous['kernel'] != updated['kernel'],
            'previous-test-kernel-sequence-mismatch')
    require(updated['uki_sha256'] == returned['uki_sha256']
            and previous['uki_sha256'] != updated['uki_sha256'], 'previous-test-image-sequence-mismatch')
    for key in ('package_inventory', 'encrypted_credential_sha256', 'previous_modules_sha256',
                'updated_modules_sha256', 'luks_metadata_sha256', 'pcr_public_key_sha256'):
        require(updated[key] == previous[key] == returned[key], 'previous-test-preservation-mismatch')
    for item in (updated, previous, returned):
        require(item['secure_boot'] is True and item['selinux'] == 'Enforcing'
                and item['runtime_healthy'] is True and item['credential_matches'] is True
                and item['overlay_read_only'] is True and item['tpm_services'] is True,
                'previous-test-runtime-failed')
    require(previous['inference'] == returned['inference'] == 'HERMES_OK', 'previous-test-inference-missing')
