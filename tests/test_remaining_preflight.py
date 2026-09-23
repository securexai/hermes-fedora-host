"""Preparation inventory tests; no VM, privilege or credential operation."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / 'scripts/remaining-lab-preflight.py'
spec = importlib.util.spec_from_file_location('remaining_preflight', path)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.operators = self.root / 'operators'; self.operators.mkdir()
        self.templates = self.root / 'templates'; self.templates.mkdir()
        self.manifest = self.root / 'sources.json'; self.manifest.write_text('{}')
        (self.root / 'docs').mkdir()
        (self.root / 'docs/HERMES_REMAINING_LAB_TESTS.md').write_text('public procedure')
        for names in preflight.CASES.values():
            for name in names:
                (self.operators / name).write_text('value = 1\n')
        for case in preflight.CASES:
            block = self.templates / 'blocks' / case; block.mkdir(parents=True)
            for name in preflight.CONTROLS:
                (block / name).write_text('value = 1\n')
            (block / 'fixture.service').write_text('TimeoutStartSec=170min\nTimeoutStopSec=50min\nKillMode=control-group\n')

    def inventory(self):
        with patch.object(preflight, 'TOOLS', []), patch.object(preflight, 'environment', return_value={}):
            return preflight.prepare(self.operators, self.templates, self.manifest, self.root, '')

    def test_missing_operator_blocks_only_dependent_cases(self):
        (self.operators / 'notification_probe.py').unlink()
        report = self.inventory()
        self.assertEqual(report['cases']['b7-notifications']['static_preparation'], 'BLOCKED')
        self.assertTrue(all(v['static_preparation'] == 'PASS' for n,v in report['cases'].items()
                            if n != 'b7-notifications'))

    def test_unrelated_case_drift_does_not_invalidate_selected_preparation(self):
        report = self.inventory()
        (self.operators / 'notification_probe.py').write_text('value = 2\n')
        self.assertTrue(preflight.verify(report, 'b4-linux')['unchanged_inputs'])
        self.assertFalse(preflight.verify(report, 'b7-notifications')['unchanged_inputs'])

    def test_changed_bytes_and_permissions_invalidate_snapshot(self):
        report = self.inventory()
        self.assertTrue(preflight.verify(report)['unchanged_inputs'])
        (self.operators / 'artifact_probe.py').write_text('value = 2\n')
        (self.operators / 'replay_probe.py').chmod(0o666)
        result = preflight.verify(report)
        self.assertFalse(result['unchanged_inputs'])
        self.assertEqual(len(result['drift']), 2)
        self.assertFalse(result['live_gates_reusable'])
        self.assertFalse(result['grants_reusable'])

    def test_symlink_and_bad_syntax_rejected_without_execution(self):
        p = self.operators / 'artifact_probe.py'; p.unlink(); p.symlink_to(self.manifest)
        (self.operators / 'replay_probe.py').write_text('this is not valid python !')
        report = self.inventory()
        self.assertEqual(report['cases']['b4-linux']['static_preparation'], 'BLOCKED')
        self.assertEqual(report['cases']['b7-during-replay']['static_preparation'], 'BLOCKED')
        self.assertEqual(report['cases']['b4-external']['static_preparation'], 'PASS')

    def test_missing_cleanup_or_changed_time_limit_blocks_case(self):
        (self.templates / 'blocks/b4-linux/restore-controls.py').unlink()
        (self.templates / 'blocks/b4-initrd/fixture.service').write_text('TimeoutStartSec=infinity\n')
        report = self.inventory()
        self.assertEqual(report['cases']['b4-linux']['static_preparation'], 'BLOCKED')
        self.assertEqual(report['cases']['b4-initrd']['static_preparation'], 'BLOCKED')


if __name__ == '__main__':
    unittest.main()
