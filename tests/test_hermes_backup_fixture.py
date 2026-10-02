"""Offline localhost-backup safety regressions; every external command is mocked."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/hermes"))
spec = importlib.util.spec_from_file_location(
    "backup_fixture", ROOT / "scripts/hermes/backup-fixture.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class LocalBackupFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name) / "backup"
        self.patch = patch.object(fixture, "BASE", self.base)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.commands = patch.object(fixture, "command")
        self.command = self.commands.start()
        self.addCleanup(self.commands.stop)

    def initialized(self):
        def key(path):
            fixture.atomic(path, b"synthetic private key")
            fixture.atomic(path.with_suffix(".pub"), b"ssh-ed25519 synthetic-public-key")

        with patch.object(fixture, "keygen", side_effect=key):
            return fixture.initialize()

    def container(self, state):
        return {
            "Name": fixture.NAME,
            "Image": fixture.IMAGE,
            "Id": "a" * 64,
            "Config": {
                "Labels": {fixture.LABEL: state["owner"]},
                "User": "0:0",
                "Cmd": ["/usr/sbin/sshd", "-D", "-e", "-f", "/fixture/sshd_config"],
            },
            "HostConfig": {
                "Memory": 256 * 1024**2,
                "PidsLimit": 64,
                "NanoCpus": 10**9,
                "ReadonlyRootfs": True,
                "Privileged": False,
                "SecurityOpt": ["no-new-privileges"],
                "UsernsMode": "private",
                "IDMappings": {
                    "UidMap": ["0:1:1000", "1000:0:1", "1001:1001:64536"],
                    "GidMap": ["0:1:1000", "1000:0:1", "1001:1001:64536"],
                },
                "PortBindings": {"2222/tcp": [{"HostIp": "127.0.0.1", "HostPort": "22226"}]},
            },
            "Mounts": [
                {
                    "Type": "bind",
                    "Destination": "/fixture",
                    "Source": str(self.base / "server"),
                    "RW": False,
                },
                {
                    "Type": "bind",
                    "Destination": "/srv/repository",
                    "Source": str(self.base / "repository"),
                    "RW": True,
                },
            ],
            "EffectiveCaps": ["CAP_DAC_OVERRIDE", "CAP_SETUID", "CAP_SETGID", "CAP_SYS_CHROOT"],
            "State": {"Running": True},
        }

    def test_preview_does_not_create_files_or_run_commands(self):
        self.assertEqual(fixture.plan("test")["status"], "PREVIEW")
        self.assertFalse(self.base.exists())
        self.command.assert_not_called()

    def test_name_conflict_refused_before_state_creation(self):
        self.command.return_value = SimpleNamespace(stdout=b"true", returncode=0)
        with patch.object(fixture, "inspect_container", return_value={"foreign": True}):
            with self.assertRaisesRegex(fixture.Refused, "name-conflict"):
                fixture.ensure_up()
        self.assertFalse(self.base.exists())

    def test_inventory_error_is_not_absence(self):
        self.command.return_value = SimpleNamespace(returncode=125)
        with self.assertRaisesRegex(fixture.Refused, "inventory-failed"):
            fixture.inspect_container()

    def test_symlink_unknown_state_and_lock_contention_refused(self):
        self.base.symlink_to(self.base.parent / "missing")
        with self.assertRaisesRegex(fixture.Refused, "unknown-state"):
            fixture.initialize()
        self.base.unlink()
        with fixture.locked():
            with self.assertRaisesRegex(fixture.Refused, "operation-in-progress"):
                with fixture.locked():
                    pass
        self.base.with_suffix(".lock").unlink()
        self.base.with_suffix(".lock").symlink_to(self.base.parent / "missing")
        with self.assertRaises(OSError):
            with fixture.locked():
                pass

    def test_private_identity_and_source_drift_refused(self):
        state = self.initialized()
        self.assertEqual(fixture.read_state(), state)
        path = self.base / "client/password"
        path.chmod(0o644)
        with self.assertRaisesRegex(fixture.Refused, "unsafe-file-mode"):
            fixture.read_state()
        path.chmod(0o600)
        fixture.atomic(self.base / "source/empty", b"changed")
        with self.assertRaisesRegex(fixture.Refused, "source-drift"):
            fixture.read_state()

    def test_port_and_space_fail_before_writes(self):
        self.command.return_value = SimpleNamespace(stdout=b"true", returncode=0)
        with patch.object(fixture, "inspect_container", return_value=None):
            with patch.object(fixture.shutil, "disk_usage", return_value=SimpleNamespace(free=0)):
                with self.assertRaisesRegex(fixture.Refused, "free-space-low"):
                    fixture.ensure_up()
            with patch.object(
                fixture.shutil, "disk_usage", return_value=SimpleNamespace(free=fixture.MIN_FREE)
            ):
                with patch.object(
                    fixture, "available_port", side_effect=fixture.Refused("port-in-use")
                ):
                    with self.assertRaisesRegex(fixture.Refused, "port-in-use"):
                        fixture.ensure_up()
        self.assertFalse(self.base.exists())

    def test_container_drift_refused_before_stop(self):
        state = self.initialized()
        item = self.container(state)
        mutations = [
            ("Config", "Labels", {fixture.LABEL: "foreign"}),
            ("HostConfig", "Memory", 0),
            ("HostConfig", "Privileged", True),
            (
                "HostConfig",
                "PortBindings",
                {"2222/tcp": [{"HostIp": "0.0.0.0", "HostPort": "22226"}]},
            ),
            ("HostConfig", "UsernsMode", "host"),
            ("Config", "Cmd", ["/bin/bash"]),
        ]
        for group, field, value in mutations:
            with self.subTest(field=field):
                changed = copy.deepcopy(item)
                changed[group][field] = value
                with patch.object(fixture, "inspect_container", return_value=changed):
                    with self.assertRaises(fixture.Refused):
                        fixture.stop_owned()
        self.command.assert_not_called()

    def test_running_rerun_preserves_keys_container_and_avoids_mutations(self):
        state = self.initialized()
        item = self.container(state)
        self.command.return_value = SimpleNamespace(stdout=b"true", returncode=0)
        with patch.object(fixture, "inspect_container", return_value=item):
            found_state, found_item = fixture.ensure_up()
        self.assertEqual(found_state, state)
        self.assertEqual(found_item, item)
        self.assertEqual(self.command.call_count, 1)  # rootless info only

    def test_podman_digest_normalization_and_keep_id_maps(self):
        state = self.initialized()
        item = self.container(state)
        item["Image"] = fixture.IMAGE.removeprefix("sha256:")
        fixture.validate_container(item, state)
        item["HostConfig"]["IDMappings"]["UidMap"] = ["0:0:1", "1:1:65536"]
        with self.assertRaisesRegex(fixture.Refused, "userns-drift"):
            fixture.validate_container(item, state)

    def test_unexpected_volume_and_missing_owned_container_refused(self):
        state = self.initialized()
        item = self.container(state)
        item["Mounts"].append({"Type": "volume", "Destination": "/extra"})
        with self.assertRaisesRegex(fixture.Refused, "mount-drift"):
            fixture.validate_container(item, state)
        state["container_id"] = item["Id"]
        fixture.atomic(self.base / "ownership.json", fixture.canonical(state))
        with patch.object(fixture, "inspect_container", return_value=None):
            with self.assertRaisesRegex(fixture.Refused, "owned-container-missing"):
                fixture.stop_owned()

    def test_stop_rerun_and_failed_stop_are_honest(self):
        state = self.initialized()
        running = self.container(state)
        stopped = copy.deepcopy(running)
        stopped["State"]["Running"] = False
        with patch.object(fixture, "inspect_container", side_effect=[running, stopped, stopped]):
            self.assertEqual(fixture.stop_owned(), "stopped")
            self.assertEqual(fixture.stop_owned(), "already-stopped")
        self.assertEqual(self.command.call_count, 1)
        self.command.side_effect = fixture.Refused("command-failed:podman")
        with patch.object(fixture, "inspect_container", return_value=running):
            with self.assertRaisesRegex(fixture.Refused, "command-failed"):
                fixture.stop_owned()

    def test_test_failure_stops_service_and_preserves_sanitized_report(self):
        state = self.initialized()
        with patch.object(fixture, "ensure_up", return_value=(state, self.container(state))):
            with patch.object(fixture, "exercise", side_effect=fixture.Refused("restore-mismatch")):
                with patch.object(fixture, "stop_owned", return_value="stopped") as stop:
                    result = fixture.test_fixture()
        stop.assert_called_once()
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["stop"], "stopped")
        self.assertEqual(json.loads(next((self.base / "reports").iterdir()).read_text()), result)

    def test_cleanup_failure_overrides_success(self):
        state = self.initialized()
        with patch.object(fixture, "ensure_up", return_value=(state, self.container(state))):
            with patch.object(fixture, "exercise", return_value={"status": "PASS"}):
                with patch.object(
                    fixture, "stop_owned", side_effect=fixture.Refused("stop-failed")
                ):
                    result = fixture.test_fixture()
        self.assertEqual(result, {"status": "FAIL", "stop": "FAILED_REVIEW_REQUIRED"})

    def test_wrong_password_failure_requires_specific_authentication_exit(self):
        state = self.initialized()
        fixture.atomic(self.base / "repository/config", b"synthetic")
        self.command.return_value = SimpleNamespace(returncode=255)
        with patch.object(fixture, "wait_ready"):
            with patch.object(fixture, "restic", return_value=SimpleNamespace(returncode=1)):
                with self.assertRaisesRegex(fixture.Refused, "wrong-restic-password-not-rejected"):
                    fixture.exercise(state, self.container(state))

    def test_client_uses_pinned_trust_and_file_password_without_environment_fallback(self):
        fixture.restic("snapshots")
        argv = self.command.call_args.args[0]
        self.assertIn("--password-file", argv)
        self.assertIn("--chdir=" + str(self.base / "source"), argv)
        ssh_command = next(
            arg for arg in argv if isinstance(arg, str) and arg.startswith("sftp.command=")
        )
        for option in (
            "StrictHostKeyChecking=yes",
            "IdentityAgent=none",
            "IdentitiesOnly=yes",
            "GlobalKnownHostsFile=/dev/null",
        ):
            self.assertIn(option, ssh_command)

    def test_backup_uses_relative_tree_and_detects_duplicate_snapshots(self):
        state = self.initialized()
        fixture.atomic(self.base / "repository/config", b"synthetic")
        self.command.return_value = SimpleNamespace(returncode=255)
        snapshot = {
            "id": "a" * 64,
            "hostname": fixture.NAME,
            "tags": [state["owner"]],
            "paths": [str(self.base / "source")],
        }
        with patch.object(fixture, "wait_ready"), patch.object(fixture, "restic") as restic:
            restic.return_value = SimpleNamespace(returncode=12)
            with patch.object(fixture, "snapshots", side_effect=[[snapshot], [snapshot, snapshot]]):
                with self.assertRaisesRegex(fixture.Refused, "snapshot-rerun-duplicated"):
                    fixture.exercise(state, self.container(state))
            backup = next(call for call in restic.call_args_list if call.args[0] == "backup")
            self.assertEqual(backup.args[-1], ".")
            self.assertIn("--skip-if-unchanged", backup.args)

    def test_command_failure_does_not_expose_output(self):
        self.commands.stop()
        with patch.object(fixture.subprocess, "Popen") as popen:
            process = popen.return_value.__enter__.return_value
            process.communicate.return_value = (b"sensitive", b"sensitive")
            process.returncode = 2
            with self.assertRaisesRegex(fixture.Refused, "^command-failed:fake$"):
                fixture.command(["fake"])
            self.assertEqual(popen.call_args.kwargs["stdin"], subprocess.DEVNULL)
            self.assertFalse(any(k.startswith("RESTIC_") for k in popen.call_args.kwargs["env"]))
        self.commands.start()


if __name__ == "__main__":
    unittest.main()
