"""Synthetic paired-audit and two-failure admission tests; no real services or audit logs."""
from contextlib import ExitStack
import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

import test_hermes_selinux_continuation_v2 as previous_tests

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/hermes/selinux/continue-reviewed-service-v2-audit.py"


def reply(code, out=b"", err=b""):
    return subprocess.CompletedProcess([], code, out, err)


class AuditContinuationTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("audit_continuation", SCRIPT)
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)
        self.fixture = previous_tests.ContinuationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.previous = self.fixture.m
        self.core = self.fixture.core
        self.before = self.fixture.before
        self.after = self.fixture.after
        self.m.BACKUP = self.previous.BACKUP
        self.m.SECOND = self.previous.CONTINUATION
        self.m.CONTINUATION = self.m.BACKUP / "service-continuation-2"
        self.m.PREVIOUS = self.m.BACKUP / "continue-reviewed-service-v2.py"
        self.write(self.m.PREVIOUS, SCRIPT.with_name("continue-reviewed-service-v2.py").read_bytes())
        self.m.SECOND.mkdir(mode=0o700)
        first = self.previous.read_prior()
        self.records = {
            "summary.json": self.m.SECOND_SUMMARY,
            "before.json": self.before,
            "audit-before.json": self.m.AUDIT_BASELINE,
            "audit-preflight.json": {"returncode": 1, "stderr": "", "timestamp_arguments": ["09/09/26", "18:39:18"]},
            "diagnostic-query_audit.json": {"operation": "query_audit", "type": "RuntimeError",
                "reason": "Audit query failed; absence of denials is unverified"},
            "prior-attempt.json": {"hashes": first["hashes"], "summary": self.previous.EXPECTED_SUMMARY,
                                   "corrected_helper_sha256": self.previous.CORRECTED_HASH},
        }
        for name, value in self.records.items():
            self.write(self.m.SECOND / name, json.dumps(value).encode())
        self.write(self.m.SECOND / "audit-preflight.log", b"")
        self.core.TRIAL = self.m.BACKUP / "query-fixture"
        self.core.TRIAL.mkdir(mode=0o700)

    @staticmethod
    def write(path, data):
        path.write_bytes(data)
        path.chmod(0o600)

    def prior(self):
        return self.m.read_prior(self.previous, self.previous.read_prior)

    def query(self, replies):
        with patch.object(self.core, "command", return_value=self.m.AUDIT_PACKAGES.encode()), \
                patch.object(self.m.subprocess, "run", side_effect=replies) as run:
            value = self.m.query_audit(self.core, ["09/09/26", "18:39:18"], "probe")
            return value, run.call_args_list

    def test_silent_raw_result_requires_exact_confirmation_and_log_input(self):
        value, calls = self.query([reply(1), reply(1, err=b"<no matches>\n")])
        self.assertEqual(value, "")
        self.assertEqual(len(calls), 2)
        for call in calls:
            self.assertIn("--input-logs", call.args[0])
            self.assertEqual(call.kwargs["stdin"], subprocess.DEVNULL)
            self.assertEqual(call.kwargs["timeout"], 60)
        self.assertEqual(calls[0].args[0][-1], "--raw")
        self.assertEqual(calls[1].args[0][-2:], ["--format", "default"])
        self.assertTrue((self.core.TRIAL / "probe-confirmation.json").is_file())

    def test_matching_raw_record_is_retained_without_second_query(self):
        record = b'type=AVC msg=audit(1.1:1): synthetic-denial\n'
        value, calls = self.query([reply(0, record)])
        self.assertEqual(value.encode(), record)
        self.assertEqual(len(calls), 1)
        self.assertEqual((self.core.TRIAL / "probe.log").read_bytes(), record)

    def test_raw_errors_and_unexpected_output_never_become_no_matches(self):
        for outcome in (reply(0), reply(0, b" \n"), reply(0, b"record", b"warning"),
                        reply(1, b"record"), reply(1, err=b"<no matches>\n"),
                        reply(1, err=b"permission denied"), reply(2), reply(-15)):
            with self.subTest(outcome=outcome):
                with self.assertRaisesRegex(RuntimeError, "Audit query error"):
                    self.query([outcome])

    def test_confirmation_errors_silence_records_and_warning_marker_rejected(self):
        for confirmation in (reply(1), reply(0, b"new event"), reply(1, b"unexpected", b"<no matches>"),
                             reply(1, err=b"warning\n<no matches>"), reply(2, err=b"error")):
            with self.subTest(confirmation=confirmation):
                with self.assertRaisesRegex(RuntimeError, "clean no-match confirmation"):
                    self.query([reply(1), confirmation])

    def test_package_drift_rejected_before_query(self):
        with patch.object(self.core, "command", return_value=b"audit-new-version"), \
                patch.object(self.m.subprocess, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "package version"):
                self.m.query_audit(self.core, ["09/09/26", "18:39:18"], "probe")
            run.assert_not_called()

    def test_prior_chain_and_frozen_wrapper_load(self):
        prior = self.prior()
        self.assertEqual(prior["before"], self.before)
        self.assertIn("second/audit-preflight.log", prior["hashes"])
        self.assertTrue(callable(self.m.load_previous().read_prior))
        self.assertFalse(self.m.CONTINUATION.exists())

    def test_frozen_wrapper_or_core_drift_rejected(self):
        self.write(self.m.PREVIOUS, b"unreviewed source")
        with self.assertRaisesRegex(RuntimeError, "wrapper identity"):
            self.m.load_previous()
        self.write(self.m.PREVIOUS, SCRIPT.with_name("continue-reviewed-service-v2.py").read_bytes())
        self.write(self.previous.CORRECTED, b"unreviewed core")
        with self.assertRaisesRegex(RuntimeError, "wrapper/core identity"):
            self.prior()

    def test_either_attempt_request_marker_blocks_admission(self):
        for directory in (self.previous.PRIOR, self.m.SECOND):
            for name in ("restart.log", "process-observation.json", "audit-ready.json"):
                with self.subTest(directory=directory, name=name):
                    p = directory / name
                    self.write(p, b"marker")
                    with self.assertRaises(RuntimeError):
                        self.prior()
                    p.unlink()

    def test_missing_second_file_or_nonempty_raw_output_rejected(self):
        p = self.m.SECOND / "audit-preflight.log"
        p.unlink()
        with self.assertRaisesRegex(RuntimeError, "missing/extra"):
            self.prior()
        self.write(p, b" ")
        with self.assertRaisesRegex(RuntimeError, "stdout was not empty"):
            self.prior()

    def test_changed_summary_metadata_health_diagnostic_or_chain_rejected(self):
        changes = {
            "summary.json": {**self.m.SECOND_SUMMARY, "service_requested": True},
            "audit-preflight.json": {**self.records["audit-preflight.json"], "stderr": "error"},
            "audit-before.json": {**self.m.AUDIT_BASELINE, "lost": "1"},
            "diagnostic-query_audit.json": {**self.records["diagnostic-query_audit.json"], "operation": "snapshot"},
            "prior-attempt.json": {**self.records["prior-attempt.json"], "hashes": {}},
            "before.json": {**self.before, "boot_id": "different"},
        }
        for name, value in changes.items():
            with self.subTest(name=name):
                p = self.m.SECOND / name
                self.write(p, json.dumps(value).encode())
                with self.assertRaises(RuntimeError):
                    self.prior()
                self.write(p, json.dumps(self.records[name]).encode())

    def test_duplicate_summary_and_numeric_false_rejected(self):
        p = self.m.SECOND / "summary.json"
        self.write(p, b'{"passed":true,' + p.read_bytes()[1:])
        with self.assertRaisesRegex(RuntimeError, "Duplicate JSON"):
            self.prior()
        self.write(p, json.dumps({**self.m.SECOND_SUMMARY, "passed": 0}).encode())
        with self.assertRaisesRegex(RuntimeError, "exact preflight-only"):
            self.prior()

    def test_empty_raw_file_still_requires_private_regular_file_without_links(self):
        p = self.m.SECOND / "audit-preflight.log"
        p.chmod(0o644)
        with self.assertRaisesRegex(RuntimeError, "root-private evidence file"):
            self.prior()
        p.unlink()
        target = self.m.BACKUP / "empty"
        self.write(target, b"")
        p.symlink_to(target)
        with self.assertRaisesRegex(RuntimeError, "root-private evidence file"):
            self.prior()

    def run_trial(self, replies=None, audit=None, during_after=None, drift=False, during_before=None):
        core = self.core
        values = iter([{**self.before, "boot_id": "different"}] if drift else [self.before, self.before, self.after])
        def snapshot():
            value = next(values)
            if value is self.before and during_before:
                during_before()
            if value is self.after and during_after:
                during_after()
            return value
        def command(*args):
            if args[0] == "hostname":
                return b"hermes"
            if args[0] == "rpm":
                return self.m.AUDIT_PACKAGES.encode()
            if args[1] == "list-jobs":
                return b""
            return b"inactive" if args[-1] == "shutdown.target" else b"active"
        process = Mock(returncode=0)
        process.poll.return_value = 0
        outcomes = replies or [reply(1), reply(1, err=b"<no matches>\n"), reply(1), reply(1, err=b"<no matches>\n")]
        with ExitStack() as stack:
            for obj, name, kwargs in (
                (self.m, "load_previous", {"return_value": self.previous}),
                (self.previous, "load_core", {"return_value": core}),
                (core, "snapshot", {"side_effect": snapshot}),
                (core, "command", {"side_effect": command}),
                (core, "file_hash", {"side_effect": lambda p: core.BACKUP_HASHES[str(p.relative_to(core.BACKUP))]}),
                (core, "audit_status", {"return_value": audit or self.m.AUDIT_BASELINE}),
                (core, "journal_cursor", {"return_value": "fixture-cursor"}),
                (core, "collect_journal", {"return_value": {"collected": True}}),
                (core, "unit_state", {"side_effect": lambda unit: self.after["units"][unit]}),
                (core, "preserve_anchors", {}),
                (core, "sample_domains", {"return_value": {core.DOMAIN}}),
                (core.time, "sleep", {}),
                (self.m.os, "geteuid", {"return_value": 0}),
                (self.m.subprocess, "run", {"side_effect": outcomes}),
                (sys, "argv", {"new": ["helper", "--approved-v2-audit-continuation"]}),
            ):
                stack.enter_context(patch.object(obj, name, **kwargs))
            self.popen = stack.enter_context(patch.object(core.subprocess, "Popen", return_value=process))
            self.output = stack.enter_context(patch("sys.stdout", new_callable=io.StringIO))
            status = self.m.main()
        return status, json.loads((self.m.CONTINUATION / "summary.json").read_text())

    def test_complete_trial_preserves_both_attempts_and_requests_once(self):
        prior = self.prior()
        status, summary = self.run_trial()
        self.assertEqual(status, 0)
        self.assertTrue(summary["passed"])
        # Original read_first is needed after the wrapper's in-memory guard composition.
        original_first = self.previous.read_prior
        self.assertTrue(summary["checks"]["prior_attempt_preserved"])
        self.assertEqual(original_first(), prior)
        self.popen.assert_called_once_with(["systemctl", "--job-mode=fail", "restart", self.core.UNIT],
                                          stdout=unittest.mock.ANY, stderr=unittest.mock.ANY)
        self.assertTrue((self.m.CONTINUATION / "audit-preflight-confirmation.json").is_file())

    def test_failed_confirmation_never_requests_service_and_keeps_private_detail(self):
        status, summary = self.run_trial(replies=[reply(1), reply(1, err=b"private-fixture-error")])
        self.assertEqual(status, 1)
        self.assertFalse(summary["service_requested"])
        self.popen.assert_not_called()
        self.assertNotIn("private-fixture-error", self.output.getvalue())
        self.assertIn("private-fixture-error", (self.m.CONTINUATION / "audit-preflight-confirmation.json").read_text())

    def test_audit_baseline_drift_and_snapshot_drift_block_before_request(self):
        status, summary = self.run_trial(audit={**self.m.AUDIT_BASELINE, "pid": "9999"})
        self.assertEqual(status, 1)
        self.assertFalse(summary["service_requested"])
        self.popen.assert_not_called()

    def test_snapshot_drift_still_blocks_before_request(self):
        status, summary = self.run_trial(drift=True)
        self.assertEqual(status, 1)
        self.assertFalse(summary["service_requested"])
        self.popen.assert_not_called()

    def test_post_audit_error_keeps_service_evidence_and_never_retries(self):
        status, summary = self.run_trial(replies=[reply(1), reply(1, err=b"<no matches>\n"), reply(2, err=b"error")])
        self.assertEqual(status, 1)
        self.assertTrue(summary["service_requested"])
        self.popen.assert_called_once()
        self.assertTrue((self.m.CONTINUATION / "process-observation.json").exists())
        self.assertTrue((self.m.CONTINUATION / "after.json").exists())

    def test_second_attempt_bytes_changed_after_admission_block_before_request(self):
        def rewrite_metadata():
            self.write(self.m.SECOND / "audit-preflight.json",
                       json.dumps(self.records["audit-preflight.json"], indent=2).encode())
        status, summary = self.run_trial(during_before=rewrite_metadata)
        self.assertEqual(status, 1)
        self.assertFalse(summary["service_requested"])
        self.popen.assert_not_called()

    def test_wrong_host_does_not_reserve_or_request(self):
        with patch.object(sys, "argv", ["helper", "--approved-v2-audit-continuation"]), \
                patch.object(self.m.os, "geteuid", return_value=0), \
                patch.object(self.m, "load_previous", return_value=self.previous), \
                patch.object(self.previous, "load_core", return_value=self.core), \
                patch.object(self.core, "command", return_value=b"other-host"), \
                patch.object(self.core, "trial") as trial:
            with self.assertRaisesRegex(RuntimeError, "Unexpected audit-continuation host"):
                self.m.main()
            trial.assert_not_called()
        self.assertFalse(self.m.CONTINUATION.exists())

    def test_both_prior_attempts_are_checked_after_observation(self):
        status, summary = self.run_trial(during_after=lambda: self.write(self.m.SECOND / "extra", b"changed"))
        self.assertEqual(status, 1)
        self.assertFalse(summary["checks"]["prior_attempt_preserved"])

    def test_existing_reservation_blocks_even_before_another_preflight(self):
        self.m.CONTINUATION.mkdir(mode=0o700)
        with patch.object(sys, "argv", ["helper", "--approved-v2-audit-continuation"]), \
                patch.object(self.m.os, "geteuid", return_value=0), \
                patch.object(self.m, "load_previous", return_value=self.previous), \
                patch.object(self.previous, "load_core", return_value=self.core), \
                patch.object(self.core, "command", return_value=b"hermes"), \
                patch.object(self.core, "trial") as trial:
            with self.assertRaises(FileExistsError):
                self.m.main()
            trial.assert_not_called()

    def test_explicit_scope_and_root_required(self):
        for args, uid in ((["helper"], 0), (["helper", "--approved-v2-audit-continuation"], 1000)):
            with patch.object(sys, "argv", args), patch.object(self.m.os, "geteuid", return_value=uid), \
                    patch.object(self.m, "load_previous") as load:
                with self.assertRaisesRegex(RuntimeError, "scope and operator sudo"):
                    self.m.main()
                load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
