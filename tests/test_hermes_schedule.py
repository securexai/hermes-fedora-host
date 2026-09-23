"""Scheduled lab workflow regressions; no provider, VM or production mutations."""

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/hermes/unattended"))
import schedule
from common import Failure, canonical, decode, lock


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("scheduler", "state", "evidence"):
            (self.root / name).mkdir(mode=0o700)
        self.config = {"candidate": str(self.root / "candidate"), "state_dir": str(self.root / "state"),
                       "evidence_dir": str(self.root / "evidence"), "run_id": "a" * 64}
        identity = self.root / "host.json"; identity.write_bytes(canonical({"synthetic": True}))
        self.policy = {"schema": "hermes-schedule-v1", "certifier_config": str(self.root / "certifier.json"),
                       "state_dir": str(self.root / "scheduler"),
                       "prepare": {"repository": str(self.root / "repo"), "transaction": str(self.root / "rpms"),
                                   "uki": str(self.root / "uki"), "host_identity": str(identity),
                                   "release_id": "synthetic", "model": "synthetic", "baseline": "b" * 64}}
        self.manifest = {"synthetic": True}
        self.fp = "c" * 64
        self.result = {"ok": True, "stage": "ua03-complete", "run_id": "a" * 64,
                       "artifact_fingerprint": self.fp, "release_signed": False}
        self.window = self.mock("maintenance_open", return_value=True)
        self.prepare = self.mock("prepare.prepare", side_effect=self.make_candidate)
        self.mock("certify.candidate", side_effect=lambda _: (self.manifest, canonical(self.manifest)))
        self.mock("candidate_fingerprint", return_value=self.fp)
        self.mock("owned_path", side_effect=lambda path, *args, **kw: Path(path))
        self.child = self.mock("child", return_value=self.result)

    def mock(self, name, **kwargs):
        mocker = patch("schedule." + name, **kwargs)
        value = mocker.start(); self.addCleanup(mocker.stop)
        return value

    def make_candidate(self, *args):
        path = Path(self.config["candidate"]); path.mkdir(mode=0o700)
        (path / "candidate.json").write_bytes(canonical(self.manifest))

    def execute(self, **kwargs):
        return schedule.execute(self.policy, self.config, **kwargs)

    def journal(self):
        return decode((self.root / "scheduler/schedule.json").read_bytes())

    def test_missed_window_does_not_prepare_or_invoke_child(self):
        self.window.return_value = False
        self.assertEqual(self.execute()["stage"], "deferred")
        self.prepare.assert_not_called(); self.child.assert_not_called()

    def grant(self):
        self.config.update(domain_uuid=schedule.certify.DOMAIN, target="hermes-certify@172.16.99.12")
        self.execute(prepare_only=True)
        self.window.return_value = False
        self.mock("time.time", return_value=1000)
        actual = schedule.protected_file
        self.mock("protected_file", side_effect=lambda path, *args: actual(path))
        path = self.root / "grant.json"
        value = {"schema": "hermes-lab-window-v1", "binding": schedule.binding(self.policy, self.config),
                 "run_id": self.config["run_id"], "candidate_sha256": self.journal()["candidate_sha256"],
                 "issued_at": 900, "expires_at": 1100}
        path.write_bytes(canonical(value))
        return path, value

    def test_lab_grant_dispatches_once_and_records_identity(self):
        path, _ = self.grant()
        self.assertEqual(self.execute(grant_path=path)["stage"], "ua03-complete")
        self.assertEqual(self.journal()["lab_window_grant_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(self.execute(grant_path=path)["stage"], "already-certified")
        self.child.assert_called_once()

    def test_lab_grant_rejects_invalid_time_and_bindings(self):
        path, value = self.grant()
        for field, replacement in [("issued_at", 1001), ("expires_at", 1000), ("expires_at", 20000),
                                   ("issued_at", True), ("binding", "0" * 64),
                                   ("run_id", "0" * 64), ("candidate_sha256", "0" * 64),
                                   ("schema", "other")]:
            with self.subTest(field=field, value=replacement):
                path.write_bytes(canonical({**value, field: replacement}))
                with self.assertRaises(Failure): self.execute(grant_path=path)
        self.child.assert_not_called()

    def test_lab_grant_rejects_other_target_and_missing_preparation(self):
        path, _ = self.grant()
        self.config["target"] = "production"
        with self.assertRaisesRegex(Failure, "requires-fixed-lab"): self.execute(grant_path=path)
        self.config["target"] = "hermes-certify@172.16.99.12"
        (self.root / "scheduler/schedule.json").unlink()
        with self.assertRaisesRegex(Failure, "needs-prepared-run"): self.execute(grant_path=path)
        self.child.assert_not_called()

    def test_lab_grant_expiry_rechecked_before_dispatch(self):
        path, _ = self.grant()
        self.mock("time.time", side_effect=[1000, 1100])
        with self.assertRaisesRegex(Failure, "expired-or-invalid"): self.execute(grant_path=path)
        self.child.assert_not_called()
        self.assertEqual(self.journal()["stage"], "prepared")

    def test_lab_grant_does_not_restart_failed_run(self):
        path, _ = self.grant()
        self.child.side_effect = Failure(69, "synthetic")
        with self.assertRaises(Failure): self.execute(grant_path=path)
        with self.assertRaisesRegex(Failure, "schedule-recovery-required"): self.execute(grant_path=path)
        self.child.assert_called_once()

    def test_lab_grant_requires_root_owned_path(self):
        path, _ = self.grant()
        self.mock("owned_path", side_effect=Failure(77, "unsafe-owner"))
        with self.assertRaisesRegex(Failure, "unsafe-owner"): self.execute(grant_path=path)
        self.child.assert_not_called()

    def test_explicit_local_preparation_is_available_outside_window(self):
        self.window.return_value = False
        self.assertEqual(self.execute(prepare_only=True)["stage"], "prepared")
        self.child.assert_not_called()
        self.assertEqual(self.execute()["stage"], "deferred")

    def test_preparation_seam_preserves_exact_candidate_for_enrollment(self):
        result = self.execute(prepare_only=True)
        self.assertEqual(result["stage"], "prepared")
        self.assertEqual(result["candidate_sha256"], hashlib.sha256(canonical(self.manifest)).hexdigest())
        self.child.assert_not_called()
        self.assertEqual(self.execute()["stage"], "ua03-complete")
        self.prepare.assert_called_once()

    def test_closed_completed_run_is_not_repeated(self):
        self.assertEqual(self.execute()["stage"], "ua03-complete")
        self.assertEqual(self.execute()["stage"], "already-certified")
        self.child.assert_called_once()

    def test_changed_policy_requires_new_enrollment(self):
        self.execute(prepare_only=True)
        self.policy["prepare"]["model"] = "different"
        with self.assertRaisesRegex(Failure, "schedule-binding-mismatch"): self.execute()
        self.child.assert_not_called()

    def test_changed_candidate_never_reaches_certifier(self):
        self.execute(prepare_only=True)
        (self.root / "candidate/candidate.json").write_bytes(b"changed")
        with self.assertRaisesRegex(Failure, "scheduled-candidate-changed"): self.execute()
        self.child.assert_not_called()

    def test_partial_preparation_is_not_reused(self):
        self.prepare.side_effect = OSError("CANARY-secret")
        with self.assertRaisesRegex(Failure, "candidate-preparation-failed"): self.execute()
        self.assertNotIn("CANARY", str(self.journal()))
        with self.assertRaisesRegex(Failure, "schedule-recovery-required"): self.execute()

    def test_interrupted_certifier_is_not_automatically_restarted(self):
        self.execute(prepare_only=True)
        path = self.root / "scheduler/schedule.json"
        value = self.journal(); value["stage"] = "certifying"; path.write_bytes(canonical(value))
        with self.assertRaisesRegex(Failure, "schedule-recovery-required"): self.execute()
        self.child.assert_not_called()

    def test_failed_certifier_runs_cleanup_and_retains_failure(self):
        self.execute(prepare_only=True)
        (self.root / "state/state.json").write_bytes(b"{}")
        self.child.side_effect = [Failure(69, "CANARY-secret"),
                                 {"ok": True, "stage": "credential-cleanup-complete"}]
        with self.assertRaisesRegex(Failure, "scheduled-certification-failed"): self.execute()
        self.assertEqual(self.child.call_args.kwargs, {"cleanup": True})
        self.assertEqual(self.journal()["stage"], "failed")
        self.assertNotIn("CANARY", str(self.journal()))

    def test_cleanup_failure_cannot_become_success(self):
        self.execute(prepare_only=True)
        (self.root / "state/state.json").write_bytes(b"{}")
        self.child.side_effect = [self.result, Failure(69, "CANARY-secret")]
        with self.assertRaisesRegex(Failure, "credential-cleanup-failed"): self.execute()
        self.assertEqual(self.journal()["cleanup_failure"], "credential-cleanup-failed")

    def test_timeout_is_failed_and_cleanup_is_attempted(self):
        self.execute(prepare_only=True)
        (self.root / "state/state.json").write_bytes(b"{}")
        self.child.side_effect = [subprocess.TimeoutExpired("synthetic", 1),
                                 {"ok": True, "stage": "credential-cleanup-complete"}]
        with self.assertRaises(Failure): self.execute()
        self.assertEqual(self.child.call_count, 2)

    def test_success_requires_exact_run_fingerprint_and_unsigned_stage(self):
        self.execute(prepare_only=True)
        for key, value in [("stage", "staged"), ("run_id", "d" * 64),
                           ("artifact_fingerprint", "e" * 64), ("release_signed", True)]:
            with self.subTest(key=key):
                journal = self.journal(); journal["stage"] = "prepared"
                (self.root / "scheduler/schedule.json").write_bytes(canonical(journal))
                self.child.return_value = {**self.result, key: value}
                with self.assertRaises(Failure): self.execute()
                self.assertEqual(self.journal()["stage"], "failed")

    def test_window_is_rechecked_after_preparation(self):
        self.window.side_effect = [True, False]
        self.assertEqual(self.execute()["stage"], "deferred")
        self.assertEqual(self.journal()["stage"], "prepared")
        self.child.assert_not_called()

    def test_concurrent_run_cannot_prepare(self):
        with lock(self.root / "scheduler/.schedule.lock"):
            with self.assertRaisesRegex(Failure, "target-busy"): self.execute()
        self.prepare.assert_not_called()

    def test_cleanup_is_available_outside_window(self):
        self.window.return_value = False
        (self.root / "state/state.json").write_bytes(b"{}")
        self.child.return_value = {"ok": True, "stage": "credential-cleanup-complete"}
        self.assertEqual(self.execute(cleanup_only=True)["stage"], "credential-cleanup-complete")
        self.prepare.assert_not_called()

    def test_policy_rejects_extra_fields_before_accessing_certifier(self):
        path = self.root / "policy.json"
        path.write_bytes(canonical({**self.policy, "command": "/bin/sh"}))
        with patch("schedule.protected_file", side_effect=lambda path, *args: Path(path)):
            with self.assertRaisesRegex(Failure, "invalid-schedule-policy"): schedule.load(path)

    def test_policy_rejects_overlapping_state_directories(self):
        path = self.root / "policy.json"; path.write_bytes(canonical(self.policy))
        (self.root / "certifier.json").write_bytes(canonical(self.config))
        with patch("schedule.protected_file", side_effect=lambda path, *args: Path(path)), \
                patch("schedule.certify.validate_config", return_value={**self.config,
                      "state_dir": self.policy["state_dir"]}):
            with self.assertRaisesRegex(Failure, "overlapping-schedule-directories"): schedule.load(path)

    def test_policy_rejects_relative_source_paths(self):
        self.policy["prepare"]["uki"] = "relative.efi"
        path = self.root / "policy.json"; path.write_bytes(canonical(self.policy))
        with patch("schedule.protected_file", side_effect=lambda path, *args: Path(path)):
            with self.assertRaisesRegex(Failure, "invalid-schedule-path"): schedule.load(path)

    def test_no_event_for_deferred_or_duplicate_run(self):
        for stage in ("deferred", "already-certified"):
            with patch.object(sys, "argv", ["schedule.py", "--config", "/synthetic", "--events", "/events"]), \
                    patch("schedule.load", return_value=(self.policy, self.config)), \
                    patch("schedule.execute", return_value={"ok": True, "stage": stage}), \
                    patch("schedule.publish") as publish:
                schedule.main(); publish.assert_not_called()

    def test_certification_completion_notifies_remaining_action(self):
        with patch.object(sys, "argv", ["schedule.py", "--config", "/synthetic", "--events", "/events"]), \
                patch("schedule.load", return_value=(self.policy, self.config)), \
                patch("schedule.execute", return_value=self.result), patch("schedule.publish") as publish:
            schedule.main()
            publish.assert_called_once_with("/events", "action-required", 75, self.config["run_id"])


class ChildTests(unittest.TestCase):
    def test_tool_readiness_ignores_caller_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = root / 'hermes_private_tool_canary'
            command.write_text('#!/bin/sh\nexit 0\n'); command.chmod(0o755)
            with patch.dict(os.environ, PATH=directory), \
                    patch('schedule.__file__', str(root / 'schedule.py')), \
                    patch('schedule.CERTIFIER_TOOLS', (command.name,)):
                with self.assertRaisesRegex(Failure, 'missing-certifier-tool-'):
                    schedule.tool_readiness()

    def test_real_tool_discovery_rejects_missing_and_nonexecutable_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in schedule.CERTIFIER_TOOLS:
                path = root / name; path.write_text('#!/bin/sh\nexit 0\n'); path.chmod(0o755)
            with patch('schedule.child_environment', return_value={'PATH': directory}):
                self.assertEqual(schedule.tool_readiness()['tools'], list(schedule.CERTIFIER_TOOLS))
                (root / 'restic').chmod(0o644)
                with self.assertRaisesRegex(Failure, 'missing-certifier-tool-restic'):
                    schedule.tool_readiness()
                (root / 'restic').chmod(0o755); (root / 'trivy').unlink()
                (root / 'trivy').symlink_to(root / 'absent')
                with self.assertRaisesRegex(Failure, 'missing-certifier-tool-trivy'):
                    schedule.tool_readiness()

    def test_child_closes_input_bounds_runtime_and_consumes_only_final_json(self):
        def invoke(command, **kwargs):
            self.assertIn("-B", command)
            self.assertNotIn("data", kwargs)  # common.run uses DEVNULL without data.
            self.assertEqual(kwargs["timeout"], 6600)
            self.assertEqual(command[-2:], ["--config", "/synthetic/config.json"])
            kwargs["stdout"].write(b'CANARY progress\n{"ok":true,"stage":"ua03-complete"}\n')
        with patch("schedule.run", side_effect=invoke):
            self.assertEqual(schedule.child("/synthetic/config.json")["stage"], "ua03-complete")

    def test_actual_child_process_receives_eof_and_returns_structured_result(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "certify.py"
            script.write_text("import sys, json\nassert sys.stdin.read() == ''\n"
                              "print(json.dumps(dict(ok=True, stage='synthetic-closed-input')))\n")
            with patch("schedule.__file__", str(Path(directory) / "schedule.py")):
                self.assertEqual(schedule.child("/synthetic/config.json")["stage"], "synthetic-closed-input")

    def test_service_local_tools_require_root_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "bin").mkdir()
            with patch("schedule.__file__", str(Path(directory) / "schedule.py")), \
                    patch("schedule.owned_path", side_effect=Failure(78, "untrusted-signing-input")), \
                    patch("schedule.run") as run:
                with self.assertRaisesRegex(Failure, "untrusted-signing-input"):
                    schedule.child("/synthetic/config.json")
                run.assert_not_called()

    def test_service_local_tools_precede_system_path_without_inheriting_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = Path(directory) / "bin"; tools.mkdir()
            def invoke(command, **kwargs):
                self.assertEqual(kwargs["env"], {"PATH": str(tools) + ":/usr/local/bin:/usr/bin:/bin"})
                kwargs["stdout"].write(b'{"ok":true,"stage":"synthetic"}\n')
            with patch("schedule.__file__", str(Path(directory) / "schedule.py")), \
                    patch("schedule.owned_path") as owned, patch("schedule.run", side_effect=invoke):
                schedule.child("/synthetic/config.json")
                owned.assert_called_once_with(tools, 0, directory=True)

    def test_cleanup_has_separate_timeout_and_fixed_argument(self):
        def invoke(command, **kwargs):
            self.assertEqual(command[-1], "--cleanup-only")
            self.assertEqual(kwargs["timeout"], 300)
            kwargs["stdout"].write(b'{"ok":true,"stage":"no-credential-issued"}\n')
        with patch("schedule.run", side_effect=invoke): schedule.child("/synthetic/config.json", cleanup=True)


if __name__ == "__main__":
    unittest.main()
