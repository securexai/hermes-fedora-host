"""Offline failure ordering for disposable enrollment; not live boot evidence."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/hermes/unattended'))
from common import Failure
import lab_enroll_boot as enrollment


class IsolatedEntrypointTests(unittest.TestCase):
    def test_isolated_cli_can_import_enrolled_modules(self):
        import subprocess
        source = Path(__file__).resolve().parents[1] / 'scripts/hermes/unattended/lab_enroll_boot.py'
        result = subprocess.run([sys.executable, '-I', '-B', str(source), '--help'],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--domain-uuid', result.stdout)


class LabBootEnrollmentTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.inputs = self.root / 'inputs'
        self.inputs.mkdir()
        for name, raw in {'boot-manager.efi': b'manager', 'previous.efi': b'previous', 'uki.crt': b'certificate'}.items():
            (self.inputs / name).write_bytes(raw)
        for name, relative in {'ESP': 'esp', 'STATE': 'state', 'SOURCE': 'signed.efi',
                               'PRODUCT_UUID': 'uuid', 'CERTIFICATE': 'certificate'}.items():
            mock = patch.object(enrollment, name, self.root / relative)
            mock.start()
            self.addCleanup(mock.stop)
        enrollment.PRODUCT_UUID.write_text('fixture-uuid')
        (enrollment.ESP / 'EFI/fedora').mkdir(parents=True)
        (enrollment.ESP / 'EFI/fedora/shimx64.efi').write_bytes(b'previous')
        (enrollment.ESP / 'hermes-tpm-stage').write_text('hermes-disposable-tpm-stage-v1')
        for mock in (patch.object(enrollment.os, 'getuid', return_value=0),
                     patch.object(enrollment, 'protected_file', side_effect=lambda path, owner: Path(path))):
            mock.start()
            self.addCleanup(mock.stop)
        mock = patch.object(enrollment, 'run', side_effect=self.command)
        self.run = mock.start()
        self.addCleanup(mock.stop)

    def command(self, args):
        if args[0] == 'mokutil':
            return b'SecureBoot enabled\n'
        if args[-1] == 'install':
            for relative in ('EFI/systemd/systemd-bootx64.efi', 'EFI/BOOT/BOOTX64.EFI'):
                path = enrollment.ESP / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(enrollment.SOURCE.read_bytes())
        return b''

    def test_wrong_fixture_has_no_side_effects(self):
        with self.assertRaisesRegex(Failure, 'lab-domain-identity-mismatch'):
            enrollment.enroll(self.inputs, 'another-uuid')
        self.run.assert_not_called()
        self.assertFalse(enrollment.STATE.exists())

    def test_failed_signature_precedes_writes(self):
        self.run.side_effect = Failure(69, 'signature-rejected')
        with self.assertRaisesRegex(Failure, 'signature-rejected'):
            enrollment.enroll(self.inputs, 'fixture-uuid')
        self.assertFalse(enrollment.STATE.exists())
        self.assertFalse(enrollment.SOURCE.exists())

    def test_distribution_boot_file_cannot_substitute_for_previous_uki(self):
        (enrollment.ESP / 'EFI/fedora/shimx64.efi').write_bytes(b'distribution-shim')
        with self.assertRaisesRegex(Failure, 'lab-previous-uki-mismatch'):
            enrollment.enroll(self.inputs, 'fixture-uuid')
        self.assertFalse(enrollment.STATE.exists())

    def test_configuration_conflict_prevents_install(self):
        (enrollment.ESP / 'loader').mkdir()
        (enrollment.ESP / 'loader/loader.conf').write_bytes(b'existing-config')
        with self.assertRaisesRegex(Failure, 'lab-enrollment-file-conflict'):
            enrollment.enroll(self.inputs, 'fixture-uuid')
        self.assertFalse(enrollment.SOURCE.exists())
        self.assertFalse(any(call.args[0][-1] == 'install' for call in self.run.call_args_list))

    def test_rerun_preserves_previous_and_never_claims_boot_pass(self):
        first = enrollment.enroll(self.inputs, 'fixture-uuid')
        self.assertEqual(first, enrollment.enroll(self.inputs, 'fixture-uuid'))
        self.assertEqual(first['stage'], 'installed-awaiting-boot')
        self.assertEqual(first['certification'], 'pending')
        self.assertEqual((enrollment.ESP / 'EFI/Linux/hermes-enrollment.efi').read_bytes(), b'previous')
        self.assertEqual((enrollment.ESP / 'EFI/fedora/shimx64.efi').read_bytes(), b'previous')
        self.assertFalse(any('set-default' in call.args[0] for call in self.run.call_args_list))

    def test_changed_input_cannot_resume_enrollment(self):
        enrollment.enroll(self.inputs, 'fixture-uuid')
        (self.inputs / 'boot-manager.efi').write_bytes(b'changed')
        with self.assertRaisesRegex(Failure, 'lab-enrollment-inputs-changed'):
            enrollment.enroll(self.inputs, 'fixture-uuid')


if __name__ == '__main__':
    unittest.main()
