"""Enroll the fixed disposable lab's signed boot manager; never certify a release.

The operator stages public artifacts signed by the existing lab authority. No
private signing or recovery key is accepted by this guest-side procedure.
"""

import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import atomic, canonical, decode, digest, protected_file, report, require, run

ESP = Path('/boot/efi')
STATE = Path('/var/lib/hermes-lab-boot-enrollment')
SOURCE = Path('/usr/lib/systemd/boot/efi/systemd-bootx64.efi.signed')
PRODUCT_UUID = Path('/sys/class/dmi/id/product_uuid')
CERTIFICATE = Path('/etc/hermes-unattended/uki.crt')
PREVIOUS = 'hermes-enrollment.efi'


def same_or_absent(path, expected):
    require(not path.is_symlink(), 'unsafe-lab-enrollment-path')
    if path.exists():
        require(protected_file(path, 0).read_bytes() == expected, 'lab-enrollment-file-conflict')


def enroll(directory, expected_uuid):
    require(os.getuid() == 0, 'lab-enrollment-requires-root')
    require(PRODUCT_UUID.read_text().strip() == expected_uuid, 'lab-domain-identity-mismatch')
    require((ESP / 'hermes-tpm-stage').read_text().strip() == 'hermes-disposable-tpm-stage-v1',
            'lab-tpm-stage-marker-missing')
    directory = Path(directory)
    inputs = {name: protected_file(directory / name, 0)
              for name in ('boot-manager.efi', 'previous.efi', 'uki.crt')}
    for name in ('boot-manager.efi', 'previous.efi'):
        run(['sbverify', '--cert', str(inputs['uki.crt']), str(inputs[name])])
    require(run(['mokutil', '--sb-state']).strip() == b'SecureBoot enabled', 'secure-boot-disabled')
    # Keep the working direct-UKI path intact, independently of the fallback path
    # bootctl replaces. Never infer that a distribution shim is a recovery UKI.
    require(digest(protected_file(ESP / 'EFI/fedora/shimx64.efi', 0)) == digest(inputs['previous.efi']),
            'lab-previous-uki-mismatch')
    binding = {name: digest(path) for name, path in inputs.items()}
    binding['domain_uuid'] = expected_uuid
    require(not STATE.is_symlink(), 'unsafe-lab-enrollment-state')
    STATE.mkdir(mode=0o700, exist_ok=True)
    journal = STATE / 'state.json'
    if journal.exists():
        require(decode(protected_file(journal, 0).read_bytes())['binding'] == binding,
                'lab-enrollment-inputs-changed')
    previous = ESP / 'EFI/Linux' / PREVIOUS
    configuration = ESP / 'loader/loader.conf'
    loader_config = ('default ' + PREVIOUS + '\ntimeout 0\neditor no\nauto-entries no\n').encode()
    targets = {SOURCE: inputs['boot-manager.efi'].read_bytes(),
               previous: inputs['previous.efi'].read_bytes(),
               CERTIFICATE: inputs['uki.crt'].read_bytes(), configuration: loader_config}
    for path, raw in targets.items():
        same_or_absent(path, raw)
    atomic(journal, canonical({'binding': binding, 'stage': 'installing', 'certification': 'pending'}))
    for path, raw in targets.items():
        path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        if not path.exists():
            atomic(path, raw)
            path.chmod(0o644)
    run(['bootctl', '--esp-path=' + str(ESP), 'install'])
    # A direct-UKI boot does not expose the boot-loader interface required by
    # set-default. loader.conf selects the recovery UKI on the first manager boot.
    for path in (ESP / 'EFI/systemd/systemd-bootx64.efi', ESP / 'EFI/BOOT/BOOTX64.EFI'):
        require(digest(protected_file(path, 0)) == binding['boot-manager.efi'],
                'lab-installed-boot-manager-mismatch')
    require(digest(previous) == binding['previous.efi'], 'lab-recovery-uki-changed')
    run(['bootctl', '--esp-path=' + str(ESP), 'is-installed'])
    result = {'binding': binding, 'stage': 'installed-awaiting-boot', 'certification': 'pending'}
    atomic(journal, canonical(result))
    return result


def main():
    parser = argparse.ArgumentParser(description='Enroll only the disposable lab signed boot manager')
    parser.add_argument('--directory', required=True)
    parser.add_argument('--domain-uuid', required=True)
    args = parser.parse_args()
    return enroll(args.directory, args.domain_uuid)


if __name__ == '__main__':
    report(main)
