"""Synthetic continuation boundaries; no Hermes, TPM, sudo or real service calls."""
from contextlib import ExitStack
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import test_hermes_selinux_service_v2 as service_tests

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/hermes/selinux/continue-reviewed-service-v2.py"


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("continuation_v2", SCRIPT)
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)
        self.fixture = service_tests.TrialTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.core = self.fixture.m
        self.tmp = tempfile.TemporaryDirectory(prefix="hermes-continuation-test-")
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        previous_umask = os.umask(0o077)
        self.addCleanup(os.umask, previous_umask)
        self.m.BACKUP = root
        self.m.PRIOR = root / "service-first"
        self.m.PRIOR.mkdir(mode=0o700)
        self.m.CONTINUATION = root / "service-continuation-1"
        self.m.ORIGINAL = root / "run-reviewed-service-v2.py"
        self.m.CORRECTED = root / "run-reviewed-service-v2-corrected.py"
        self.core.BACKUP = root
        self.write(self.m.ORIGINAL, b"synthetic original helper")
        self.m.ORIGINAL_HASH = self.m.sha(self.m.ORIGINAL.read_bytes())
        self.write(self.m.CORRECTED, SCRIPT.with_name("run-reviewed-service-v2.py").read_bytes())
        self.before = self.fixture.before
        for unit, invocation in self.m.INVOCATIONS.items():
            self.before["units"][unit]["InvocationID"] = invocation
        self.before["units"][self.core.UNIT]["Requires"] = "system.slice -.mount"
        self.before["units"][self.core.UNIT]["Conflicts"] = "shutdown.target"
        self.after = copy.deepcopy(self.before)
        self.after["anchors"]["/efi/loader/credentials/nvpcr-anchor.fixture.cred"] = self.fixture.anchor_hash
        self.after["units"][self.core.UNIT].update({"ActiveState": "active", "SubState": "exited",
            "Result": "success", "ExecMainStatus": "0", "InvocationID": "2" * 32,
            "ExecMainStartTimestamp": "Wed 2026-09-09 19:00:00 -05"})
        self.write(self.m.PRIOR / "before.json", json.dumps(self.before).encode())
        self.write(self.m.PRIOR / "summary.json", json.dumps(self.m.EXPECTED_SUMMARY).encode())
        # Represent root ownership only within this disposable fixture, retaining real type/mode/link checks.
        real_stat = Path.stat
        def fixture_stat(path, *args, **kwargs):
            value = real_stat(path, *args, **kwargs)
            if path.is_relative_to(root):
                fields = list(value)
                fields[4] = 0
                return os.stat_result(fields)
            return value
        stat_patch = patch.object(Path, "stat", fixture_stat)
        stat_patch.start()
        self.addCleanup(stat_patch.stop)

    @staticmethod
    def write(path, data):
        path.write_bytes(data)
        path.chmod(0o600)

    def test_exact_prior_and_hash_pinned_core_load_without_main(self):
        prior = self.m.read_prior()
        self.assertEqual(prior["before"], self.before)
        self.assertEqual(set(prior["hashes"]), {"original_helper", "before.json", "summary.json"})
        self.assertTrue(callable(self.m.load_core().trial))
        self.assertFalse(self.m.CONTINUATION.exists())

    def test_original_and_corrected_code_drift_rejected(self):
        self.write(self.m.ORIGINAL, b"changed original")
        with self.assertRaisesRegex(RuntimeError, "Original helper"):
            self.m.read_prior()
        self.write(self.m.CORRECTED, b"raise AssertionError('must never execute')")
        with self.assertRaisesRegex(RuntimeError, "Corrected helper"):
            self.m.load_core()

    def test_request_markers_and_any_extra_prior_file_rejected(self):
        for name in ("process-observation.json", "restart.log", "audit-before.json", "unexpected"):
            with self.subTest(name=name):
                path = self.m.PRIOR / name
                self.write(path, b"fixture")
                with self.assertRaisesRegex(RuntimeError, "unexpected files"):
                    self.m.read_prior()
                path.unlink()

    def test_missing_prior_file_rejected(self):
        (self.m.PRIOR / "before.json").unlink()
        with self.assertRaisesRegex(RuntimeError, "unexpected files"):
            self.m.read_prior()

    def test_requested_passed_wrong_time_numeric_false_and_extra_summary_rejected(self):
        for changes in ({"service_requested": True}, {"passed": True}, {"timestamp": "different"},
                        {"service_requested": 0}, {"checks": {"extra": True}}, {"extra": "field"}):
            with self.subTest(changes=changes):
                self.write(self.m.PRIOR / "summary.json", json.dumps({**self.m.EXPECTED_SUMMARY, **changes}).encode())
                with self.assertRaisesRegex(RuntimeError, "exact preflight-only"):
                    self.m.read_prior()

    def test_duplicate_json_property_rejected(self):
        p = self.m.PRIOR / "summary.json"
        self.write(p, b'{"passed":true,' + p.read_bytes()[1:])
        with self.assertRaisesRegex(RuntimeError, "Duplicate JSON"):
            self.m.read_prior()

    def test_prior_unit_identity_and_root_dependency_required(self):
        for mutation in ("invocation", "dependency", "extra-unit"):
            before = copy.deepcopy(self.before)
            if mutation == "invocation":
                before["units"][self.core.UNIT]["InvocationID"] = "different"
            elif mutation == "dependency":
                before["units"][self.core.UNIT]["Requires"] = "system.slice"
            else:
                before["units"]["unreviewed.service"] = {}
            self.write(self.m.PRIOR / "before.json", json.dumps(before).encode())
            with self.assertRaisesRegex(RuntimeError, "reviewed dependency"):
                self.m.read_prior()

    def test_symlink_hardlink_and_nonprivate_modes_rejected(self):
        p = self.m.PRIOR / "summary.json"
        original = p.read_bytes()
        p.chmod(0o644)
        with self.assertRaisesRegex(RuntimeError, "root-private regular"):
            self.m.read_prior()
        p.unlink()
        target = self.m.BACKUP / "summary-copy.json"
        self.write(target, original)
        p.symlink_to(target)
        with self.assertRaisesRegex(RuntimeError, "root-private regular"):
            self.m.read_prior()
        p.unlink()
        os.link(target, p)
        with self.assertRaisesRegex(RuntimeError, "root-private regular"):
            self.m.read_prior()
        p.unlink()
        self.write(p, original)
        self.m.PRIOR.chmod(0o755)
        with self.assertRaisesRegex(RuntimeError, "root-private directory"):
            self.m.read_prior()

    def test_empty_or_nonroot_input_rejected(self):
        self.write(self.m.PRIOR / "summary.json", b"")
        with self.assertRaisesRegex(RuntimeError, "root-private regular"):
            self.m.read_prior()
        fake = Mock(parents=(), is_symlink=Mock(return_value=False))
        fake.stat.return_value = Mock(st_mode=stat.S_IFREG | 0o600, st_uid=1000, st_nlink=1, st_size=100)
        with self.assertRaisesRegex(RuntimeError, "root-private regular"):
            self.m.private_bytes(fake)

    def test_scope_and_root_required_before_core_load(self):
        for argv, uid in ((["helper"], 0), (["helper", "--approved-v2-continuation"], 1000)):
            with patch.object(sys, "argv", argv), patch.object(self.m.os, "geteuid", return_value=uid), \
                    patch.object(self.m, "load_core") as load:
                with self.assertRaisesRegex(RuntimeError, "scope and operator sudo"):
                    self.m.main()
                load.assert_not_called()
        self.assertFalse(self.m.CONTINUATION.exists())

    def run_continuation(self, snapshots=None, queries=None, during_after=None, during_before=None):
        m = self.core
        snapshots = iter(snapshots or [self.before, self.before, self.after])
        def snapshot():
            value = next(snapshots)
            if value is self.before and during_before:
                during_before()
            if value is self.after and during_after:
                during_after()
            return value
        def command(*args):
            if args[0] == "hostname":
                return b"hermes\n"
            if args[1] == "list-jobs":
                return b""
            self.assertIn("--", args)
            return b"inactive" if args[-1] == "shutdown.target" else b"active"
        process = Mock(returncode=0)
        process.poll.return_value = 0
        with ExitStack() as stack:
            for obj, name, kwargs in (
                (self.m, "load_core", {"return_value": m}),
                (m, "snapshot", {"side_effect": snapshot}),
                (m, "file_hash", {"side_effect": lambda p: m.BACKUP_HASHES[str(p.relative_to(m.BACKUP))]}),
                (m, "command", {"side_effect": command}),
                (m, "audit_status", {"return_value": self.fixture.audit}),
                (m, "query_audit", {"side_effect": queries or ["", ""]}),
                (m, "journal_cursor", {"return_value": "fixture-cursor"}),
                (m, "collect_journal", {"return_value": {"collected": True}}),
                (m, "unit_state", {"side_effect": lambda unit: self.after["units"][unit]}),
                (m, "preserve_anchors", {}),
                (m, "sample_domains", {"return_value": {m.DOMAIN}}),
                (m.time, "sleep", {}),
                (self.m.os, "geteuid", {"return_value": 0}),
                (sys, "argv", {"new": ["helper", "--approved-v2-continuation"]}),
            ):
                stack.enter_context(patch.object(obj, name, **kwargs))
            self.popen = stack.enter_context(patch.object(m.subprocess, "Popen", return_value=process))
            self.output = stack.enter_context(patch("sys.stdout", new_callable=io.StringIO))
            result = self.m.main()
        return result, json.loads((self.m.CONTINUATION / "summary.json").read_text())

    def test_complete_continuation_preserves_old_attempt_and_requests_once(self):
        prior = self.m.read_prior()
        result, summary = self.run_continuation()
        self.assertEqual(result, 0)
        self.assertTrue(summary["passed"])
        self.assertTrue(summary["checks"]["prior_attempt_preserved"])
        self.assertEqual(self.m.read_prior(), prior)
        self.popen.assert_called_once()
        self.assertEqual(self.popen.call_args.args[0], ["systemctl", "--job-mode=fail", "restart", self.core.UNIT])
        self.assertTrue((self.m.CONTINUATION / "prior-attempt.json").is_file())
        self.assertEqual(stat.S_IMODE((self.m.CONTINUATION / "summary.json").stat().st_mode), 0o600)

    def test_current_snapshot_drift_blocks_before_request_and_records_private_reason(self):
        result, summary = self.run_continuation(snapshots=[{**self.before, "boot_id": "different"}])
        self.assertEqual(result, 1)
        self.assertFalse(summary["service_requested"])
        self.popen.assert_not_called()
        diagnostic = json.loads((self.m.CONTINUATION / "diagnostic-preflight.json").read_text())
        self.assertIn("differs", diagnostic["reason"])

    def test_second_snapshot_drift_blocks_before_request(self):
        result, summary = self.run_continuation(snapshots=[self.before, {**self.before, "boot_id": "different"}])
        self.assertEqual(result, 1)
        self.assertFalse(summary["service_requested"])
        self.popen.assert_not_called()

    def test_prior_bytes_changed_before_request_fail_even_if_json_is_equivalent(self):
        def rewrite_summary():
            self.write(self.m.PRIOR / "summary.json", json.dumps(self.m.EXPECTED_SUMMARY, indent=2).encode())
        result, summary = self.run_continuation(during_before=rewrite_summary)
        self.assertEqual(result, 1)
        self.assertFalse(summary["service_requested"])
        self.popen.assert_not_called()
        diagnostic = json.loads((self.m.CONTINUATION / "diagnostic-preflight.json").read_text())
        self.assertIn("Prior evidence changed", diagnostic["reason"])

    def test_prior_evidence_change_during_observation_cannot_pass(self):
        result, summary = self.run_continuation(during_after=lambda: self.write(self.m.PRIOR / "extra", b"changed"))
        self.assertEqual(result, 1)
        self.assertFalse(summary["checks"]["prior_attempt_preserved"])

    def test_audit_error_is_private_and_never_requests_service(self):
        result, summary = self.run_continuation(queries=[RuntimeError("private-canary")])
        self.assertEqual(result, 1)
        self.assertFalse(summary["service_requested"])
        self.popen.assert_not_called()
        self.assertNotIn("private-canary", self.output.getvalue())
        self.assertIn("private-canary", (self.m.CONTINUATION / "diagnostic-query_audit.json").read_text())

    def test_continuation_reservation_blocks_reuse_after_preflight_failure(self):
        self.run_continuation(snapshots=[{**self.before, "boot_id": "different"}])
        with patch.object(sys, "argv", ["helper", "--approved-v2-continuation"]), \
                patch.object(self.m.os, "geteuid", return_value=0), \
                patch.object(self.m, "load_core", return_value=self.core), \
                patch.object(self.core, "command", return_value=b"hermes"), \
                patch.object(self.core, "trial") as trial:
            with self.assertRaises(FileExistsError):
                self.m.main()
            trial.assert_not_called()

    def test_wrong_host_never_reserves_continuation(self):
        with patch.object(sys, "argv", ["helper", "--approved-v2-continuation"]), \
                patch.object(self.m.os, "geteuid", return_value=0), \
                patch.object(self.m, "load_core", return_value=self.core), \
                patch.object(self.core, "command", return_value=b"not-hermes"):
            with self.assertRaisesRegex(RuntimeError, "Unexpected continuation host"):
                self.m.main()
        self.assertFalse(self.m.CONTINUATION.exists())

    def test_command_failure_retains_private_argv(self):
        prior = self.m.read_prior()
        self.m.CONTINUATION.mkdir(mode=0o700)
        with patch.object(self.core, "command", side_effect=RuntimeError("fixture command failure")):
            self.m.configure_core(self.core, prior)
            with self.assertRaises(RuntimeError):
                self.core.command("systemctl", "show", "-p", "ActiveState", "--value", "--", "-.mount")
        diagnostic = json.loads((self.m.CONTINUATION / "command-failure.json").read_text())
        self.assertEqual(diagnostic["argv"][-2:], ["--", "-.mount"])


if __name__ == "__main__":
    unittest.main()
