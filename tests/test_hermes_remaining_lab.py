"""Offline acceptance of remaining-lab probes; no hypervisor, credentials or boot."""

import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace

CODE = Path(__file__).resolve().parents[1] / 'scripts/hermes/unattended'
sys.path.insert(0, str(CODE))
import lab_faults
import lab_previous
from common import Failure


class PreviousTests(unittest.TestCase):
    def observations(self):
        updated = dict(boot_id='boot-1', kernel='new', uki_sha256='a'*64,
                       package_inventory='b'*64, encrypted_credential_sha256='c'*64,
                       previous_modules_sha256='d'*64, updated_modules_sha256='e'*64,
                       luks_metadata_sha256='f'*64, pcr_public_key_sha256='0'*64,
                       secure_boot=True, selinux='Enforcing', runtime_healthy=True,
                       credential_matches=True, overlay_read_only=True, tpm_services=True)
        previous = {**updated, 'boot_id': 'boot-2', 'kernel': 'old', 'uki_sha256': '1'*64, 'inference': 'HERMES_OK'}
        returned = {**updated, 'boot_id': 'boot-3', 'inference': 'HERMES_OK'}
        return updated, previous, returned

    def test_complete_roundtrip(self):
        lab_previous.verify_sequence(*self.observations())

    def test_reused_boot_same_image_reseal_token_change_and_removed_modules_fail(self):
        changes = {'boot_id': 'boot-1', 'kernel': 'new', 'uki_sha256': 'a'*64,
                   'package_inventory': 'changed', 'encrypted_credential_sha256': 'resealed',
                   'previous_modules_sha256': 'removed', 'updated_modules_sha256': 'removed',
                   'luks_metadata_sha256': 'reenrolled', 'pcr_public_key_sha256': 'replaced',
                   'secure_boot': False, 'selinux': 'Permissive', 'runtime_healthy': False,
                   'credential_matches': False, 'overlay_read_only': False, 'tpm_services': False,
                   'inference': 'not-HERMES_OK'}
        for field, value in changes.items():
            with self.subTest(field=field), self.assertRaises(Failure):
                updated, previous, returned = self.observations()
                previous[field] = value
                lab_previous.verify_sequence(updated, previous, returned)

    def test_return_boot_must_reuse_updated_image_and_credential(self):
        for field in ('uki_sha256', 'encrypted_credential_sha256', 'kernel', 'inference'):
            with self.subTest(field=field), self.assertRaises(Failure):
                items = self.observations(); items[2][field] = 'wrong'
                lab_previous.verify_sequence(*items)

    def test_modules_hash_records_actual_content_and_links(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); tree = root / 'old'; tree.mkdir()
            (tree / 'module.ko').write_bytes(b'first module')
            (tree / 'modules.dep').write_text('module.ko:\n')
            (tree / 'build').symlink_to('/not-followed')
            with patch.object(lab_previous, 'MODULES', root):
                first = lab_previous.modules('old')
                (tree / 'module.ko').write_bytes(b'changed module')
                self.assertNotEqual(first, lab_previous.modules('old'))
                (tree / 'module.ko').unlink()
                with self.assertRaisesRegex(Failure, 'incomplete-previous-modules'):
                    lab_previous.modules('old')

    def test_module_path_traversal_and_symlink_root_rejected(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(lab_previous, 'MODULES', Path(temp)):
            (Path(temp) / 'old').symlink_to('/usr')
            for kernel in ('../other', 'old'):
                with self.subTest(kernel=kernel), self.assertRaises(Failure): lab_previous.modules(kernel)

    def test_previous_selection_requires_closed_update_and_keeps_new_default(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / 'state.json'; state.write_text('{"phase":"reboot-pending"}')
            with patch.object(lab_previous, 'retained'), patch.object(lab_previous, 'protected_file', return_value=state):
                with self.assertRaisesRegex(Failure, 'previous-test-requires-completed-update'):
                    lab_previous.select({}, {'release_id': 'test'}, True)


class TamperTests(unittest.TestCase):
    def image(self):
        data = bytearray(2048); data[:2] = b'MZ'
        struct.pack_into('<I', data, 0x3c, 128); data[128:132] = b'PE\0\0'
        struct.pack_into('<H', data, 134, 3); struct.pack_into('<H', data, 148, 0)
        for index, section in enumerate(('.linux', '.initrd', '.cmdline')):
            offset = 152 + index * 40
            data[offset:offset + len(section)] = section.encode()
            struct.pack_into('<II', data, offset + 16, 128, 512 + index * 128)
        return data

    def test_each_section_changes_one_byte_and_preserves_control(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / 'control.efi'; source.write_bytes(self.image())
            for index, section in enumerate(('.linux', '.initrd', '.cmdline')):
                target = root / (str(index) + '.efi')
                result = lab_faults.mutate(source, target, section)
                changed = [i for i, (a, b) in enumerate(zip(source.read_bytes(), target.read_bytes())) if a != b]
                self.assertEqual(changed, [512 + index * 128])
                self.assertFalse(result['resigned'])
            self.assertEqual(source.read_bytes(), self.image())

    def test_existing_output_link_and_malformed_input_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / 'control'; source.write_bytes(self.image())
            target = root / 'copy'; target.symlink_to(source)
            with self.assertRaises(FileExistsError): lab_faults.mutate(source, target, '.linux')
            target.unlink(); source.write_bytes(b'not PE')
            with self.assertRaises(Failure): lab_faults.mutate(source, target, '.linux')
            self.assertFalse(target.exists())


class FaultTests(unittest.TestCase):
    def test_real_process_death_leaves_no_published_partial_image(self):
        # Actual os._exit bypasses finally: these are interrupted writes, not exception mocks.
        for point in ('before-copy', 'during-copy', 'before-publish'):
            with self.subTest(point=point), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); esp = root / 'esp'; esp.mkdir(); records = root / 'records'; records.mkdir()
                source = root / 'input.efi'; source.write_bytes(b'x' * (2 * 1024 * 1024))
                previous = esp / 'previous.efi'; previous.write_bytes(b'approved previous')
                target = esp / 'new.efi'; evidence = records / 'fault.json'
                script = ('import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); '
                          'from lab_faults import interrupted_copy; interrupted_copy(*sys.argv[2:])')
                result = subprocess.run([sys.executable, '-B', '-c', script, str(CODE), str(source), str(target),
                                         point, str(evidence)], capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 137, result.stderr)
                self.assertFalse(target.exists())
                self.assertEqual(previous.read_bytes(), b'approved previous')
                record = json.loads(evidence.read_text()); self.assertEqual(record['point'], point)
                pending = list(esp.glob('.pending-*'))
                self.assertEqual(len(pending), 0 if point == 'before-copy' else 1)
                if point == 'during-copy': self.assertLess(pending[0].stat().st_size, source.stat().st_size)
                if point == 'before-publish': self.assertEqual(pending[0].read_bytes(), source.read_bytes())

    def test_completed_replay_cannot_be_reported_as_interrupted(self):
        import offline, gates
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'packages').mkdir()
            (root / 'packages/installed-after.sha256').write_text('final')
            instance = SimpleNamespace(directory=root)
            manifest = {'baseline_sha256': 'initial', 'transaction': 'packages/transaction.json'}
            child = Mock(pid=12345, returncode=0)
            child.poll.side_effect = [None, 0, 0]
            with patch.object(lab_faults, 'enrolled', return_value=({}, manifest, instance, None)), \
                    patch.object(offline, 'execute', side_effect=lambda *args: offline.run(['dnf5', '--disable-repo=*'])), \
                    patch.object(gates, 'package_baseline', return_value='final'), \
                    patch.object(lab_faults.subprocess, 'Popen', return_value=child), \
                    patch.object(lab_faults.time, 'sleep'), patch.object(lab_faults.os, 'killpg') as kill, \
                    patch.object(lab_faults, 'checkpoint') as witness:
                with self.assertRaisesRegex(Failure, 'replay-mutation-checkpoint-not-observed'):
                    lab_faults.replay_fault('a'*64, 'during-replay', root / 'evidence')
                kill.assert_not_called(); witness.assert_not_called()

    def test_replay_checkpoint_requires_live_kill_and_intermediate_inventory(self):
        import offline, gates
        class Stopped(BaseException): pass
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'packages').mkdir()
            (root / 'packages/installed-after.sha256').write_text('final')
            instance = SimpleNamespace(directory=root)
            manifest = {'baseline_sha256': 'initial', 'transaction': 'packages/transaction.json'}
            child = Mock(pid=12345, returncode=-9); child.poll.return_value = None
            with patch.object(lab_faults, 'enrolled', return_value=({}, manifest, instance, None)), \
                    patch.object(offline, 'execute', side_effect=lambda *args: offline.run(['dnf5', '--disable-repo=*'])), \
                    patch.object(gates, 'package_baseline', return_value='intermediate'), \
                    patch.object(lab_faults.subprocess, 'Popen', return_value=child), \
                    patch.object(lab_faults.os, 'killpg') as kill, \
                    patch.object(lab_faults, 'checkpoint', side_effect=Stopped) as witness:
                with self.assertRaises(Stopped): lab_faults.replay_fault('a'*64, 'during-replay', root / 'evidence')
                kill.assert_called_once_with(12345, 9)
                self.assertTrue(witness.call_args.kwargs['inventory_incomplete'])
                self.assertTrue(witness.call_args.kwargs['child_killed'])

    def test_replayed_fault_record_refuses_another_interruption(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); evidence = root / 'fault.json'; evidence.write_text('{}')
            with self.assertRaisesRegex(Failure, 'fault-already-attempted'):
                lab_faults.interrupted_copy(root / 'unused', root / 'new', 'before-copy', evidence)


if __name__ == '__main__': unittest.main()
