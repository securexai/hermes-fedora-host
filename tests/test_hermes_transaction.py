"""Exact stored-transaction expectations and package-boundary failures."""

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/hermes/unattended'))
from common import Failure
from transaction import expected_inventory, normalize, validate_bundle
import gates
from release import safe_name


class StoredTransactionTests(unittest.TestCase):
    def setUp(self):
        self.before = b'base-0:1-1.x86_64\nkeep-2:1-1.noarch\n'
        self.transaction = {'version': '1.0', 'rpms': [
            {'action': 'Upgrade', 'nevra': 'base-2-1.x86_64', 'package_path': './packages/base.rpm'},
            {'action': 'Replaced', 'nevra': 'base-1-1.x86_64'},
            {'action': 'Install', 'nevra': 'new-1-1.noarch', 'package_path': './packages/new.rpm'},
        ]}

    def test_prediction_preserves_unrelated_and_epoch_packages(self):
        inventory, paths = expected_inventory(self.transaction, self.before)
        self.assertEqual(inventory, b'base-0:2-1.x86_64\nkeep-2:1-1.noarch\nnew-0:1-1.noarch\n')
        self.assertEqual(set(paths), {'packages/base.rpm', 'packages/new.rpm'})
        self.assertEqual(normalize('hyphenated-package-1:2.3-4.fc44.x86_64'),
                         'hyphenated-package-1:2.3-4.fc44.x86_64')

    def test_real_rpm_filename_characters_preserve_archive_boundary(self):
        for name in ('packages/packages/libstdc++-16.2.1-2.fc44.x86_64.rpm',
                     'packages/packages/passt-0^20260728.gf8df3f1-2.fc44.x86_64.rpm'):
            self.assertEqual(safe_name(name), name)
        for name in ('packages/../escape', 'packages/$(command).rpm', 'packages/file;command.rpm'):
            with self.assertRaises(Failure):
                safe_name(name)

    def test_reinstall_does_not_duplicate_inventory(self):
        transaction = {'version': '1.0', 'rpms': [
            {'action': 'Reinstall', 'nevra': 'base-1-1.x86_64', 'package_path': './packages/base.rpm'}]}
        self.assertEqual(expected_inventory(transaction, self.before)[0], self.before)

    def test_rpm_signing_key_pseudopackage_is_preserved(self):
        key = b'gpg-pubkey-0:abcd1234-6786af3b.(none)\n'
        inventory, _ = expected_inventory(self.transaction, self.before + key)
        self.assertIn(key, inventory)

    def test_unknown_actions_and_versions_fail_closed(self):
        for change in ('action', 'version'):
            with self.subTest(change=change):
                transaction = copy.deepcopy(self.transaction)
                if change == 'action':
                    transaction['rpms'][0]['action'] = 'Reason Change'
                else:
                    transaction['version'] = '2.0'
                with self.assertRaises(Failure):
                    expected_inventory(transaction, self.before)

    def test_external_and_traversal_paths_are_rejected(self):
        for name in ('/etc/package.rpm', './packages/../../elsewhere.rpm',
                     'https://example.invalid/package.rpm', './packages/dir/file.rpm'):
            with self.subTest(name=name):
                transaction = copy.deepcopy(self.transaction)
                transaction['rpms'][0]['package_path'] = name
                with self.assertRaisesRegex(Failure, 'unsafe-stored-package-path'):
                    expected_inventory(transaction, self.before)

    def test_missing_replaced_package_rejects_wrong_baseline(self):
        with self.assertRaisesRegex(Failure, 'transaction-baseline-mismatch'):
            expected_inventory(self.transaction, b'base-0:0-1.x86_64\n')

    def test_duplicate_package_rejected(self):
        self.transaction['rpms'].append(self.transaction['rpms'][0])
        with self.assertRaisesRegex(Failure, 'duplicate-transaction-package'):
            expected_inventory(self.transaction, self.before)

    def test_bundle_requires_complete_local_rpms_and_exact_result(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / 'packages').mkdir()
            (root / 'installed-before.txt').write_bytes(self.before)
            (root / 'transaction.json').write_text(json.dumps(self.transaction))
            expected, paths = expected_inventory(self.transaction, self.before)
            (root / 'installed-after.sha256').write_text(hashlib.sha256(expected).hexdigest() + '\n')
            for path in paths:
                (root / path).write_bytes(b'fixture-rpm')
            baseline = hashlib.sha256(self.before).hexdigest()
            self.assertEqual(validate_bundle(root, baseline), paths)
            (root / 'packages/extra.rpm').write_bytes(b'extra')
            with self.assertRaisesRegex(Failure, 'stored-package-set-mismatch'):
                validate_bundle(root, baseline)
            (root / 'packages/extra.rpm').unlink()
            (root / 'installed-after.sha256').write_text('0' * 64)
            with self.assertRaisesRegex(Failure, 'stored-transaction-result-mismatch'):
                validate_bundle(root, baseline)

    def test_valid_signature_on_wrong_rpm_never_stages_update(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / 'base.rpm').write_bytes(b'fixture')
            with patch.object(gates, 'package_baseline', return_value='baseline'), \
                    patch.object(gates, 'validate_bundle', return_value={'base.rpm': 'base-0:2-1.x86_64'}), \
                    patch.object(gates, 'protected_file', side_effect=lambda path, owner: path), \
                    patch.object(gates, 'run', side_effect=[b'digests signatures OK', b'wrong-0:2-1.x86_64']) as run:
                with self.assertRaisesRegex(Failure, 'stored-rpm-identity-mismatch'):
                    gates.replay_packages(root, 'baseline')
                self.assertFalse(any(call.args[0][0] == 'dnf5' for call in run.call_args_list))


if __name__ == '__main__':
    unittest.main()
