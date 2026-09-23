"""Offline single-service boundaries using synthetic state; never contact Hermes or a TPM."""
from contextlib import ExitStack
import copy
import getopt
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/hermes/selinux/run-reviewed-service-v2.py"


class TrialTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("service_v2", SCRIPT)
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)
        self.tmp = tempfile.TemporaryDirectory(prefix="hermes-service-v2-test-")
        self.addCleanup(self.tmp.cleanup)
        self.m.TRIAL = Path(self.tmp.name) / "trial"
        self.m.TRIAL.mkdir(mode=0o700)
        self.before = self.fixture()
        self.after = copy.deepcopy(self.before)
        self.after["anchors"]["/efi/loader/credentials/nvpcr-anchor.fixture.cred"] = self.anchor_hash
        self.after["units"][self.m.UNIT].update({
            "ActiveState": "active", "SubState": "exited", "Result": "success", "ExecMainStatus": "0",
            "ExecMainStartTimestamp": "Wed 2026-09-09 16:00:00 -05", "InvocationID": "2" * 32,
        })
        self.audit = {"enabled": "1", "pid": "10", "lost": "0", "backlog": "0"}
        self.observation = {"restart_returncode": 0, "observed_domains": [self.m.DOMAIN], "timed_out": False}

    def fixture(self):
        m = self.m
        self.anchor_hash = m.BACKUP_HASHES[m.ANCHORS[0].lstrip("/")]
        state = {name: "" for name in m.PROPERTIES}
        state.update({name: "none" for name in ("FailureAction", "SuccessAction", "StartLimitAction", "JobTimeoutAction")})
        state.update({"LoadState": "loaded", "ActiveState": "failed", "SubState": "failed", "MainPID": "0",
                      "ControlPID": "0", "Result": "exit-code", "ExecMainCode": "1", "ExecMainStatus": "1",
                      "InvocationID": "1" * 32, "ConditionResult": "yes", "AssertResult": "yes", "Type": "oneshot",
                      "Restart": "no", "ExecStart": "{ path=" + m.EXE + " ; argv[]=" + m.EXE
                      + " --graceful ; ignore_errors=no ; start_time=[Wed] ; stop_time=[Wed] ; pid=42 ; code=exited ; status=1 }"})
        units = {unit: {**state, "ExecMainStartTimestamp": start} for unit, start in m.STARTS.items()}
        units[m.EARLY].update({"ActiveState": "active", "SubState": "exited", "Result": "success", "ExecMainStatus": "0"})
        return {"srk": {"public-fixture": "srk"}, "anchors": {path: self.anchor_hash for path in m.ANCHORS},
                "boot_paths": {"esp": "/efi", "boot": "/boot"}, "luks_metadata": "fixture-luks",
                "firmware": m.BACKUP_HASHES["firmware.before"], "boot_status": "fixture-boot", "boot_id": "fixture-id",
                "cmdline": "fixture-cmdline", "loaded_policy": m.LOADED_HASH, "disk_policy": m.DISK_HASH,
                "label": m.LABEL, "mapping": m.LABEL, "enforcing": "Enforcing", "packages": m.PACKAGES, "units": units}

    def checks(self, **overrides):
        args = dict(before=self.before, after=self.after, observation=self.observation, avcs=[],
                    audit_before=self.audit, audit_after=self.audit)
        args.update(overrides)
        return self.m.acceptance(**args)

    def preflight(self, **kwargs):
        with patch.object(self.m, "file_hash", side_effect=lambda p: self.m.BACKUP_HASHES[str(p.relative_to(self.m.BACKUP))]), \
                patch.object(self.m, "command", return_value=b""):
            return self.m.preflight(kwargs.get("before", self.before))

    def test_pins_match_verified_installation_record(self):
        record = json.loads((SCRIPT.parents[3] / "docs/plans/evidence/2026-09-09-hermes-selinux-v2-installed.json").read_text())
        self.assertEqual(self.m.LOADED_HASH, record["loaded_policy_sha256"])
        self.assertEqual(self.m.DISK_HASH, record["expected_disk_policy_sha256"])
        for name, value in self.m.BACKUP_HASHES.items():
            self.assertEqual(value, record["archive_validation"]["backup_payload_hashes"][name])

    def test_unit_show_requests_empty_properties_and_rejects_missing_fields(self):
        state = self.before["units"][self.m.UNIT]
        with patch.object(self.m, "command", return_value="\n".join(key + "=" + value for key, value in state.items()).encode()) as command:
            self.assertEqual(self.m.unit_state(self.m.UNIT), state)
            self.assertIn("--all", command.call_args.args)
        with patch.object(self.m, "command", side_effect=[b"MainPID=0\n", b"a(sasbttttuii) 0\n" * len(self.m.HOOKS)]):
            with self.assertRaisesRegex(RuntimeError, "Incomplete"):
                self.m.unit_state(self.m.UNIT)

    def test_omitted_command_arrays_require_typed_empty_bus_values(self):
        state = self.before["units"][self.m.UNIT]
        shown = "\n".join(key + "=" + value for key, value in state.items() if key not in self.m.HOOKS).encode()
        with patch.object(self.m, "command", side_effect=[shown, b"a(sasbttttuii) 0\n" * len(self.m.HOOKS)]) as command:
            self.assertEqual(self.m.unit_state(self.m.UNIT), state)
            self.assertEqual(command.call_args.args[3], "/org/freedesktop/systemd1/unit/systemd_2dtpm2_2dsetup_2eservice")
        for reply in (b"", b"a(sasbttttuii) 1 unexpected-command", b"s unknown"):
            with patch.object(self.m, "command", side_effect=[shown, reply]):
                with self.assertRaisesRegex(RuntimeError, "verified empty"):
                    self.m.unit_state(self.m.UNIT)

    def test_multiple_execstart_rows_cannot_hide_an_extra_command(self):
        state = self.before["units"][self.m.UNIT]
        shown = "ExecStart={ path=/bin/unapproved ; argv[]=/bin/unapproved ; ignore_errors=no ; }\n"
        shown += "\n".join(key + "=" + value for key, value in state.items())
        with patch.object(self.m, "command", return_value=shown.encode()):
            with self.assertRaisesRegex(RuntimeError, "multiple commands"):
                self.m.unit_state(self.m.UNIT)

    def test_good_preflight_and_acceptance(self):
        self.preflight()
        self.assertTrue(all(self.checks().values()))

    def test_policy_package_label_firmware_and_anchor_drift_rejected(self):
        for key in ("loaded_policy", "disk_policy", "enforcing", "label", "mapping", "packages", "firmware"):
            with self.subTest(key=key):
                before = copy.deepcopy(self.before)
                before[key] = "drift"
                with self.assertRaises(RuntimeError):
                    self.preflight(before=before)
        for changed in ({}, {**self.before["anchors"], "/efi/loader/credentials/nvpcr-anchor.new.cred": self.anchor_hash},
                        {path: "drift" for path in self.m.ANCHORS}):
            before = {**self.before, "anchors": changed}
            with self.assertRaises(RuntimeError):
                self.preflight(before=before)

    def test_backup_hash_drift_rejected(self):
        with patch.object(self.m, "file_hash", return_value="drift"):
            with self.assertRaisesRegex(RuntimeError, "backup drift"):
                self.m.preflight(self.before)

    def test_busy_early_or_late_and_previous_invocation_drift_rejected(self):
        for unit in (self.m.UNIT, self.m.EARLY):
            for key, value in (("MainPID", "23"), ("ControlPID", "42"), ("ActiveState", "activating"),
                               ("ExecMainStartTimestamp", "new start"), ("LoadState", "not-found")):
                with self.subTest(unit=unit, key=key):
                    before = copy.deepcopy(self.before)
                    before["units"][unit][key] = value
                    with self.assertRaisesRegex(RuntimeError, "busy or invocation drift"):
                        self.preflight(before=before)

    def test_extra_commands_hooks_and_restarts_rejected(self):
        for key, value in (("Type", "simple"), ("Restart", "always"), ("ExecStart", "/bin/false"),
                           ("ExecStart", self.before["units"][self.m.UNIT]["ExecStart"] * 2),
                           *((name, "unexpected") for name in ("ExecCondition", "ExecStartPre", "ExecStartPost", "ExecStop",
                                                                "ExecStopPost", "OnFailure", "OnSuccess",
                                                                "ConsistsOf", "BoundBy", "PropagatesStopTo", "Upholds")),
                           *((name, "reboot") for name in ("FailureAction", "SuccessAction", "StartLimitAction",
                                                           "JobTimeoutAction"))):
            with self.subTest(key=key):
                before = copy.deepcopy(self.before)
                before["units"][self.m.UNIT][key] = value
                with self.assertRaisesRegex(RuntimeError, "execution contract"):
                    self.preflight(before=before)

    def test_pending_jobs_and_dependency_activation_rejected(self):
        with patch.object(self.m, "file_hash", side_effect=lambda p: self.m.BACKUP_HASHES[str(p.relative_to(self.m.BACKUP))]), \
                patch.object(self.m, "command", return_value=b"42 queued job"):
            with self.assertRaisesRegex(RuntimeError, "Pending"):
                self.m.preflight(self.before)
        for prop, active in (("Requires", b"inactive"), ("Wants", b"failed"), ("Conflicts", b"active")):
            with self.subTest(prop=prop):
                before = copy.deepcopy(self.before)
                before["units"][self.m.UNIT][prop] = "fixture.service"
                with patch.object(self.m, "file_hash", side_effect=lambda p: self.m.BACKUP_HASHES[str(p.relative_to(self.m.BACKUP))]), \
                        patch.object(self.m, "command", side_effect=[b"", active]):
                    with self.assertRaisesRegex(RuntimeError, "dependency"):
                        self.m.preflight(before)

    def test_root_mount_dependency_parses_as_unit_and_still_requires_active(self):
        before = copy.deepcopy(self.before)
        before["units"][self.m.UNIT]["Requires"] = "system.slice -.mount"
        before["units"][self.m.UNIT]["Conflicts"] = "shutdown.target"
        root_state = b"active"

        def systemctl(args, **kwargs):
            # GNU option parsing reproduces the real CLI failure for a leading-dash unit.
            options, operands = getopt.gnu_getopt(list(args[1:]), "p:", ["no-legend", "no-pager", "value"])
            if operands == ["list-jobs"]:
                output = b""
            else:
                self.assertEqual(operands[0], "show")
                output = {"system.slice": b"active", "-.mount": root_state,
                          "shutdown.target": b"inactive"}[operands[1]]
            return subprocess.CompletedProcess(args, 0, output, b"")

        with patch.object(self.m, "file_hash", side_effect=lambda p: self.m.BACKUP_HASHES[str(p.relative_to(self.m.BACKUP))]), \
                patch.object(self.m.subprocess, "run", side_effect=systemctl):
            self.m.preflight(before)
            root_state = b"inactive"
            with self.assertRaisesRegex(RuntimeError, "dependency not quiescent"):
                self.m.preflight(before)

    def test_exit_76_skipped_stale_or_busy_service_never_passes(self):
        for key, value in (("ExecMainStatus", "76"), ("ExecMainCode", "2"), ("ConditionResult", "no"),
                           ("AssertResult", "no"), ("InvocationID", "1" * 32), ("InvocationID", "0" * 32),
                           ("MainPID", "23"), ("ControlPID", "42"), ("ActiveState", "failed"),
                           ("Result", "exit-code"), ("SubState", "running"),
                           ("ExecMainStartTimestamp", self.m.STARTS[self.m.UNIT])):
            with self.subTest(key=key):
                after = copy.deepcopy(self.after)
                after["units"][self.m.UNIT][key] = value
                self.assertFalse(all(self.checks(after=after).values()))

    def test_missing_or_wrong_domain_and_restart_failure_never_pass(self):
        for domains in ([], ["init_t"], [self.m.DOMAIN, "init_t"]):
            self.assertFalse(self.checks(observation={**self.observation, "observed_domains": domains})["actual_domain_observed"])
        for change in ({"timed_out": True}, {"restart_returncode": 1}, {"restart_returncode": None}):
            self.assertFalse(self.checks(observation={**self.observation, **change})["restart_command_zero"])

    def test_every_preservation_invariant_is_required(self):
        for key in ("srk", "luks_metadata", "firmware", "boot_status", "boot_id", "cmdline", "loaded_policy",
                    "disk_policy", "label", "mapping", "packages", "enforcing"):
            with self.subTest(key=key):
                after = {**self.after, key: "drift"}
                self.assertFalse(all(self.checks(after=after).values()))
        after = copy.deepcopy(self.after)
        after["units"][self.m.EARLY]["InvocationID"] = "changed"
        self.assertFalse(self.checks(after=after)["early_unit_preserved"])

    def test_boot_partition_anchor_does_not_substitute_for_esp(self):
        after = copy.deepcopy(self.after)
        del after["anchors"]["/efi/loader/credentials/nvpcr-anchor.fixture.cred"]
        after["anchors"]["/boot/loader/credentials/nvpcr-anchor.fixture.cred"] = self.anchor_hash
        self.assertFalse(self.checks(after=after)["esp_anchor_present"])

    def test_anchor_replacement_missing_copy_and_mismatch_rejected(self):
        for anchors in ({path: "changed" for path in self.after["anchors"]},
                        {"/efi/loader/credentials/nvpcr-anchor.fixture.cred": self.anchor_hash},
                        {**self.after["anchors"], self.m.ANCHORS[0]: "changed"}):
            self.assertFalse(all(self.checks(after={**self.after, "anchors": anchors}).values()))

    def test_audit_loss_daemon_restart_disabled_backlog_and_avc_fail(self):
        for key, value in (("lost", "1"), ("lost", ""), ("pid", "11"), ("pid", "0"), ("pid", "unknown"),
                           ("enabled", "0"), ("enabled", "2"), ("backlog", "1")):
            with self.subTest(key=key):
                self.assertFalse(self.checks(audit_after={**self.audit, key: value})["audit_collection_intact"])
        self.assertFalse(self.checks(avcs=["synthetic denial"])["no_scoped_avcs"])

    def test_audit_date_and_no_matches_or_errors(self):
        self.assertRegex(self.m.audit_timestamp()[0], r"^\d{2}/\d{2}/\d{2}$")
        for stdout, stderr in ((b"", b"<no matches>\n"), (b"<no matches>\n", b"")):
            with patch.object(self.m.subprocess, "run", return_value=SimpleNamespace(returncode=1, stdout=stdout, stderr=stderr)):
                self.assertEqual(self.m.query_audit(["09/09/26", "16:00:00"], "test-query"), "")
        for rc, stdout, stderr in ((1, b"", b"bad date"), (0, b"", b""), (0, b"record", b"warning"), (2, b"", b"error")):
            with patch.object(self.m.subprocess, "run", return_value=SimpleNamespace(returncode=rc, stdout=stdout, stderr=stderr)):
                with self.assertRaisesRegex(RuntimeError, "Audit query"):
                    self.m.query_audit(["09/09/26", "16:00:00"], "test-query")
                self.assertTrue((self.m.TRIAL / "test-query.json").exists())

    def test_symlink_parent_empty_file_and_directory_inputs_rejected(self):
        root = Path(self.tmp.name)
        (root / "plain").mkdir()
        (root / "plain/value").write_bytes(b"fixture")
        (root / "link").symlink_to(root / "plain", target_is_directory=True)
        (root / "file-link").symlink_to(root / "plain/value")
        (root / "empty").touch()
        for path in (root / "link/value", root / "file-link", root / "empty", root / "plain"):
            with self.assertRaises(RuntimeError):
                self.m.file_hash(path)

    def test_encrypted_backup_exclusive_private_and_drift_checked(self):
        anchor = Path(self.tmp.name) / "fixture.cred"
        anchor.write_bytes(b"synthetic encrypted credential")
        before = {"anchors": {str(anchor): self.m.file_hash(anchor)}}
        previous = os.umask(0o077)
        try:
            self.m.preserve_anchors(before, "before")
        finally:
            os.umask(previous)
        output = self.m.TRIAL / "anchors-before/0.cred"
        self.assertEqual(output.read_bytes(), anchor.read_bytes())
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        with self.assertRaises(FileExistsError):
            self.m.preserve_anchors(before, "before")
        anchor.write_bytes(b"changed")
        with self.assertRaisesRegex(RuntimeError, "changed"):
            self.m.preserve_anchors(before, "after")

    def run_trial(self, snapshots=None, queries=None, audits=None):
        m = self.m
        process = Mock(returncode=0)
        process.poll.return_value = 0
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(m, "snapshot", side_effect=snapshots or [self.before, self.before, self.after]))
        stack.enter_context(patch.object(m, "file_hash", side_effect=lambda p: m.BACKUP_HASHES[str(p.relative_to(m.BACKUP))]))
        stack.enter_context(patch.object(m, "command", return_value=b""))
        stack.enter_context(patch.object(m, "audit_status", side_effect=audits or [self.audit, self.audit, self.audit]))
        stack.enter_context(patch.object(m, "query_audit", side_effect=queries or ["", ""]))
        stack.enter_context(patch.object(m, "journal_cursor", return_value="fixture-cursor"))
        stack.enter_context(patch.object(m, "collect_journal", return_value={"collected": True}))
        stack.enter_context(patch.object(m, "unit_state", side_effect=lambda unit: self.after["units"][unit]))
        stack.enter_context(patch.object(m, "preserve_anchors"))
        stack.enter_context(patch.object(m, "sample_domains", return_value={m.DOMAIN}))
        stack.enter_context(patch.object(m.time, "sleep"))
        self.popen = stack.enter_context(patch.object(m.subprocess, "Popen", return_value=process))
        self.printed = stack.enter_context(patch("sys.stdout", new_callable=io.StringIO))
        result = m.trial()
        return result, json.loads((m.TRIAL / "summary.json").read_text())

    def test_complete_trial_requests_only_one_late_restart(self):
        result, summary = self.run_trial()
        self.assertEqual(result, 0)
        self.assertTrue(summary["passed"])
        self.popen.assert_called_once()
        self.assertEqual(self.popen.call_args.args[0], ["systemctl", "--job-mode=fail", "restart", self.m.UNIT])
        self.assertTrue((self.m.TRIAL / "process-observation.json").exists())
        self.assertNotIn(self.anchor_hash, self.printed.getvalue())
        self.assertNotIn("fixture-luks", self.printed.getvalue())

    def test_bad_preflight_never_starts_service(self):
        before = {**self.before, "loaded_policy": "old policy"}
        result, summary = self.run_trial(snapshots=[before])
        self.assertEqual(result, 1)
        self.assertFalse(summary["service_requested"])
        self.popen.assert_not_called()

    def test_audit_parser_failure_before_run_never_starts_service(self):
        result, summary = self.run_trial(queries=[RuntimeError("synthetic secret canary")])
        self.assertEqual(result, 1)
        self.assertFalse(summary["service_requested"])
        self.popen.assert_not_called()
        self.assertNotIn("synthetic secret canary", self.printed.getvalue())

    def test_drift_during_recovery_copy_never_starts_service(self):
        result, _ = self.run_trial(snapshots=[self.before, {**self.before, "boot_id": "changed"}])
        self.assertEqual(result, 1)
        self.popen.assert_not_called()

    def test_audit_drift_immediately_before_request_never_starts_service(self):
        result, summary = self.run_trial(audits=[self.audit, {**self.audit, "lost": "1"}])
        self.assertEqual(result, 1)
        self.assertFalse(summary["service_requested"])
        self.popen.assert_not_called()

    def test_audit_failure_after_run_retains_prior_evidence_and_never_retries(self):
        result, summary = self.run_trial(queries=["", RuntimeError("query failed")])
        self.assertEqual(result, 1)
        self.assertFalse(summary["passed"])
        self.popen.assert_called_once()
        for name in ("before", "after", "audit-before", "audit-after", "process-observation", "service-status"):
            self.assertTrue((self.m.TRIAL / (name + ".json")).is_file())
        self.assertIn("audit-query", [error["phase"] for error in summary["errors"]])

    def test_snapshot_failure_after_run_still_collects_service_and_audit(self):
        result, summary = self.run_trial(snapshots=[self.before, self.before, RuntimeError("anchor missing")])
        self.assertEqual(result, 1)
        self.assertFalse(summary["passed"])
        self.popen.assert_called_once()
        self.assertTrue((self.m.TRIAL / "service-status.json").is_file())
        self.assertTrue((self.m.TRIAL / "audit-after.json").is_file())

    def test_scoped_avc_causes_failure_without_exposing_raw_record(self):
        raw = 'type=AVC msg=audit(1:1): denied scontext=system_u:system_r:' + self.m.DOMAIN + ':s0 private-fixture'
        result, summary = self.run_trial(queries=["", raw])
        self.assertEqual(result, 1)
        self.assertEqual(summary["scoped_avc_count"], 1)
        self.assertNotIn("private-fixture", self.printed.getvalue())

    def test_timeout_terminates_only_waiting_client_and_saves_observation(self):
        process = Mock(returncode=-15)
        process.poll.return_value = None
        with patch.object(self.m.subprocess, "Popen", return_value=process) as popen, \
                patch.object(self.m, "sample_domains", return_value={self.m.DOMAIN}), \
                patch.object(self.m.time, "monotonic", side_effect=[0, 121]):
            observation = self.m.observe_service()
        self.assertTrue(observation["timed_out"])
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=5)
        popen.assert_called_once()
        self.assertEqual(json.loads((self.m.TRIAL / "process-observation.json").read_text()), observation)

    def test_stuck_client_killed_without_a_second_service_command(self):
        process = Mock(returncode=-9)
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("systemctl", 5), 0]
        with patch.object(self.m.subprocess, "Popen", return_value=process) as popen, \
                patch.object(self.m, "sample_domains", return_value=set()), \
                patch.object(self.m.time, "monotonic", side_effect=[0, 121]):
            self.assertTrue(self.m.observe_service()["timed_out"])
        process.kill.assert_called_once()
        popen.assert_called_once()

    def test_process_observer_exception_preserves_sample(self):
        process = Mock(returncode=-15)
        process.poll.return_value = None
        with patch.object(self.m.subprocess, "Popen", return_value=process), \
                patch.object(self.m, "sample_domains", side_effect=[{self.m.DOMAIN}, OSError("fixture")]), \
                patch.object(self.m.time, "sleep"):
            with self.assertRaises(OSError):
                self.m.observe_service()
        self.assertEqual(json.loads((self.m.TRIAL / "process-observation.json").read_text())["observed_domains"], [self.m.DOMAIN])
        process.terminate.assert_called_once()

    def test_domain_sampling_is_tied_to_late_unit_cgroup(self):
        entries = []
        for index, cgroup in enumerate((self.m.UNIT, self.m.EARLY, "unrelated.service")):
            directory = Path(self.tmp.name) / str(index)
            (directory / "attr").mkdir(parents=True)
            (directory / "exe").symlink_to(self.m.EXE)
            (directory / "cgroup").write_text("0::/system.slice/" + cgroup + "\n")
            (directory / "attr/current").write_text("system_u:system_r:" + (self.m.DOMAIN if index == 0 else "init_t") + ":s0\x00")
            entries.append(directory)
        with patch.object(Path, "glob", return_value=entries):
            self.assertEqual(self.m.sample_domains(), {self.m.DOMAIN})

    def test_explicit_argument_root_private_backup_and_exclusive_reservation(self):
        with patch.object(sys, "argv", ["trial"]), patch.object(self.m.subprocess, "Popen") as popen:
            with self.assertRaisesRegex(RuntimeError, "approved-v2"):
                self.m.main()
            popen.assert_not_called()
        with patch.object(sys, "argv", ["trial", "--approved-v2-first-run"]), \
                patch.object(self.m.os, "geteuid", return_value=1000):
            with self.assertRaisesRegex(RuntimeError, "sudo"):
                self.m.main()
        backup = Mock(parents=())
        backup.is_symlink.return_value = False
        backup.stat.return_value = SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=0)
        with patch.object(sys, "argv", ["trial", "--approved-v2-first-run"]), \
                patch.object(self.m.os, "geteuid", return_value=0), patch.object(self.m.os, "umask"), \
                patch.dict(os.environ), patch.object(self.m, "command", return_value=b"hermes\n"), \
                patch.object(self.m, "BACKUP", backup), patch.object(self.m, "trial") as trial:
            with self.assertRaises(FileExistsError):
                self.m.main()
            trial.assert_not_called()
            backup.stat.return_value.st_uid = 1000
            with self.assertRaisesRegex(RuntimeError, "root-private"):
                self.m.main()
            backup.stat.return_value.st_uid = 0
            backup.stat.return_value.st_mode = stat.S_IFDIR | 0o755
            with self.assertRaisesRegex(RuntimeError, "root-private"):
                self.m.main()


if __name__ == "__main__":
    unittest.main()
