"""Offline replay ordering and failure recovery; not live update evidence."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/hermes/unattended'))
from common import Failure
import offline
import gates


class OfflineReplayTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.directory = self.root / 'transaction'
        self.directory.mkdir()
        (self.directory / 'transaction.json').write_text('{}')
        (self.directory / 'installed-after.sha256').write_text('b' * 64)
        self.baseline = 'a' * 64
        for name, relative in {'ROOT': 'state', 'MARKER': 'system-update', 'OTHER_MARKER': 'other-update',
                               'UNIT': 'hermes.service', 'WANT': 'wants/hermes.service'}.items():
            mock = patch.object(offline, name, self.root / relative)
            mock.start()
            self.addCleanup(mock.stop)
        for mock in (patch.object(offline.os, 'geteuid', return_value=0),
                     patch.object(offline, 'protected_file', side_effect=lambda path, owner: Path(path))):
            mock.start()
            self.addCleanup(mock.stop)
        for name, value in [('run', b''), ('boot_id', 'before')]:
            mock = patch.object(offline, name, return_value=value)
            setattr(self, name, mock.start())
            self.addCleanup(mock.stop)

    def state(self):
        return json.loads(offline.state_path(self.directory, self.baseline).read_text())

    def stage(self):
        offline.stage(self.directory, self.baseline)
        self.boot_id.return_value = 'update'

    def test_foreign_update_exits_without_touching_it(self):
        offline.MARKER.symlink_to('/another/updater')
        self.assertEqual(offline.execute(self.directory, self.baseline)['stage'], 'offline-update-not-selected')
        self.assertEqual(offline.MARKER.readlink(), Path('/another/updater'))
        self.run.assert_not_called()

    def test_stage_rejects_other_updater_before_enabling(self):
        offline.OTHER_MARKER.symlink_to('/another/updater')
        with self.assertRaisesRegex(Failure, 'offline-update-already-staged'):
            offline.stage(self.directory, self.baseline)
        self.assertFalse(offline.UNIT.exists())
        self.assertFalse(offline.MARKER.is_symlink())

    def test_unit_validation_failure_never_schedules_boot(self):
        self.run.side_effect = Failure(69, 'invalid-unit')
        with self.assertRaisesRegex(Failure, 'invalid-unit'):
            offline.stage(self.directory, self.baseline)
        self.assertFalse(offline.MARKER.is_symlink())
        self.assertFalse(offline.WANT.is_symlink())
        self.assertEqual(self.state()['status'], 'staging')

    def test_success_requires_a_subsequent_normal_boot(self):
        self.stage()
        def verify(*args):
            self.assertFalse(offline.MARKER.is_symlink())
        with patch.object(gates, 'verify_packages', side_effect=verify), \
                patch.object(gates, 'package_baseline', return_value='b' * 64):
            offline.execute(self.directory, self.baseline)
        self.assertEqual(self.state()['status'], 'complete')
        self.assertFalse(offline.UNIT.exists())
        self.assertFalse(offline.WANT.is_symlink())
        with self.assertRaisesRegex(Failure, 'offline-package-recovery-required'):
            offline.require_complete(self.directory, self.baseline)
        self.boot_id.return_value = 'normal'
        offline.require_complete(self.directory, self.baseline)

    def test_signature_failure_records_failure_without_replay_or_reboot_loop(self):
        self.stage()
        self.run.reset_mock()
        with patch.object(gates, 'verify_packages', side_effect=Failure(78, 'rpm-signature-unverified')):
            with self.assertRaisesRegex(Failure, 'offline-package-recovery-required'):
                offline.execute(self.directory, self.baseline)
        self.assertFalse(offline.MARKER.is_symlink())
        self.assertEqual(self.state()['status'], 'failed')
        self.assertEqual(self.state()['error'], 'rpm-signature-unverified')
        self.assertFalse(any(call.args[0][0] == 'dnf5' for call in self.run.call_args_list))

    def test_wrong_inventory_never_reports_success(self):
        self.stage()
        with patch.object(gates, 'verify_packages'), patch.object(gates, 'package_baseline', return_value='c' * 64):
            with self.assertRaises(Failure):
                offline.execute(self.directory, self.baseline)
        self.assertEqual(self.state()['error'], 'package-replay-result-mismatch')
        self.boot_id.return_value = 'normal'
        with self.assertRaises(Failure):
            offline.require_complete(self.directory, self.baseline)

    def test_completion_is_not_published_before_service_cleanup(self):
        self.stage()
        def interrupted_cleanup(state):
            self.assertEqual(self.state()['status'], 'running')
            raise Failure(69, 'cleanup-interrupted')
        with patch.object(gates, 'verify_packages'), \
                patch.object(gates, 'package_baseline', return_value='b' * 64), \
                patch.object(offline, 'cleanup', side_effect=interrupted_cleanup):
            with self.assertRaises(Failure):
                offline.execute(self.directory, self.baseline)
        self.assertEqual(self.state()['status'], 'failed')

    def test_new_kernel_selected_only_after_verified_package_replay(self):
        uki = self.root / 'hermes-test.efi'
        uki.write_bytes(b'signed-uki-fixture')
        with patch.object(offline, 'ESP', self.root):
            offline.stage(self.directory, self.baseline, boot_entry=uki.name)
            self.assertFalse(any(c.args[0][0] == 'bootctl' for c in self.run.call_args_list))
            self.boot_id.return_value = 'update'
            seen = []
            def command(args, **kwargs):
                seen.append(args[0])
                if args[0] == 'bootctl':
                    self.assertIn('dnf5', seen)
                    self.assertEqual(self.state()['status'], 'running')
                return b''
            self.run.side_effect = command
            with patch.object(gates, 'verify_packages'), \
                    patch.object(gates, 'package_baseline', return_value='b' * 64):
                offline.execute(self.directory, self.baseline)
            self.assertLess(seen.index('dnf5'), seen.index('bootctl'))
            self.assertLess(seen.index('bootctl'), seen.index('systemctl'))

    def test_failed_replay_preserves_previous_kernel_selection(self):
        uki = self.root / 'hermes-test.efi'
        uki.write_bytes(b'signed-uki-fixture')
        with patch.object(offline, 'ESP', self.root):
            offline.stage(self.directory, self.baseline, boot_entry=uki.name)
            self.boot_id.return_value = 'update'
            self.run.reset_mock()
            with patch.object(gates, 'verify_packages'), \
                    patch.object(gates, 'package_baseline', return_value='c' * 64):
                with self.assertRaises(Failure):
                    offline.execute(self.directory, self.baseline)
            self.assertFalse(any(c.args[0][0] == 'bootctl' for c in self.run.call_args_list))

    def test_changed_uki_cannot_be_selected_after_replay(self):
        uki = self.root / 'hermes-test.efi'
        uki.write_bytes(b'signed-uki-fixture')
        with patch.object(offline, 'ESP', self.root):
            offline.stage(self.directory, self.baseline, boot_entry=uki.name)
            uki.write_bytes(b'changed-after-staging')
            self.boot_id.return_value = 'update'
            self.run.reset_mock()
            with patch.object(gates, 'verify_packages'), \
                    patch.object(gates, 'package_baseline', return_value='b' * 64):
                with self.assertRaises(Failure):
                    offline.execute(self.directory, self.baseline)
            self.assertEqual(self.state()['error'], 'offline-boot-artifact-changed')
            self.assertFalse(any(c.args[0][0] == 'bootctl' for c in self.run.call_args_list))

    def test_offline_unit_cannot_add_bytecode_to_frozen_candidate(self):
        content = offline.unit_text(self.directory, self.baseline).decode()
        self.assertIn('ExecStart=/usr/bin/python3 -I -B ', content)

    def test_unit_argument_injection_rejected(self):
        with self.assertRaisesRegex(Failure, 'unsafe-offline-command-path'):
            offline.unit_text('/var/lib/package%name', self.baseline)


if __name__ == '__main__':
    unittest.main()
