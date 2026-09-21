"""Offline collector gate tests; all subprocesses and host config reads are mocked."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("collector", HERE / "2026-09-12-hermes-ssh-preflight.py")
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class CollectorTests(unittest.TestCase):
    def collect(self, blocked=False):
        commands = []

        def execute(command, **kwargs):
            commands.append(command)
            code = int(blocked and command[0] == 'bash' and command[-1].endswith('inspect_config'))
            output = ''
            if '--get-policies' in command:
                output = 'allow-host-ipv6 gateway-lan-to-HOST'
            if '--get-zones' in command:
                output = 'FedoraServer'
            return subprocess.CompletedProcess(command, code, output, '')

        sink = io.StringIO()
        with patch.object(collector, 'HELPER', HERE.parents[2] / 'setup-ssh-key-only.sh'), \
                patch.object(collector.os, 'geteuid', return_value=0), \
                patch.object(collector.subprocess, 'run', side_effect=execute), \
                patch.object(Path, 'read_text', return_value=''), \
                patch.object(Path, 'glob', return_value=[]), contextlib.redirect_stdout(sink):
            collector.main()
        return json.loads(sink.getvalue()), commands

    def test_success_gates_full_dry_run_and_collects_policies(self):
        report, commands = self.collect()
        self.assertEqual(report['checks'][-1]['name'], 'complete_read_only_dry_run')
        self.assertEqual(report['checks'][-1]['rc'], 0)
        main_calls = [c[-1] for c in commands if c[0] == 'bash' and '\nmain ' in c[-1]]
        self.assertEqual(len(main_calls), 1)
        self.assertTrue(main_calls[0].endswith('--dry-run'))
        self.assertTrue(any('--policy=gateway-lan-to-HOST' in c for c in commands))
        self.assertFalse(any('apply_config' in c[-1] for c in commands))

    def test_failed_config_blocks_candidate_and_dry_run_but_collects_diagnostics(self):
        report, commands = self.collect(blocked=True)
        checks = {item['name']: item for item in report['checks']}
        self.assertIn('blocked', checks['candidate_key_only_configuration'])
        self.assertIn('blocked', checks['complete_read_only_dry_run'])
        self.assertTrue(any('--policy=gateway-lan-to-HOST' in c for c in commands))
        self.assertFalse(any(c[0] == 'bash' and '\nmain ' in c[-1] for c in commands))


if __name__ == '__main__':
    unittest.main()
