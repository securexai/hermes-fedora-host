"""Safety checks for the exact-VM guest password recovery path."""

import base64
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts/hermes/manual/lab/deepseek-guest-password-recovery.py"
)
SPEC = importlib.util.spec_from_file_location("deepseek_guest_password_recovery", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RecoveryTests(unittest.TestCase):
    def test_changed_grant_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "deepseek-test-grant.py"
            source.write_text("changed\n")
            with patch.object(MODULE, "GRANT_SOURCE", source):
                with self.assertRaisesRegex(RuntimeError, "reviewed grant source changed"):
                    MODULE.grant_module()

    def test_wrong_vm_stops_before_guest_or_network_checks(self):
        grant = Mock()
        grant.bound_vm.return_value = "shut off"
        with self.assertRaisesRegex(RuntimeError, "must be running"):
            MODULE.bound_guest(grant)
        grant.bound_network.assert_not_called()
        grant.guest_identity.assert_not_called()
        grant.agent.assert_not_called()

    def test_disabled_password_command_stops_before_prompt(self):
        grant = Mock()
        grant.bound_vm.return_value = "running"
        grant.agent.return_value = {
            "supported_commands": [{"name": "guest-set-user-password", "enabled": False}]
        }
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            MODULE.bound_guest(grant)
        grant.bound_network.assert_called_once()
        grant.guest_identity.assert_called_once()

    def test_guest_agent_receives_only_yescrypt_hash_for_exact_vm(self):
        grant = Mock()
        grant.DOMAIN = "lab-hermes-deepseek-e2e-r1"
        grant.UUID = "4349a2bc-67b6-42b7-a6ef-5aeee5ee4009"
        domain = Mock()
        domain.UUIDString.return_value = grant.UUID
        conn = Mock()
        conn.lookupByName.return_value = domain
        with (
            patch.object(MODULE, "bound_guest") as bound,
            patch.object(MODULE.libvirt, "open", return_value=conn),
            patch.object(
                MODULE.libvirt_qemu, "qemuAgentCommand", return_value='{"return":{}}'
            ) as command,
        ):
            MODULE.apply_hash(grant, "$y$reviewed-yescrypt-hash")
        bound.assert_called_once_with(grant)
        conn.lookupByName.assert_called_once_with(grant.DOMAIN)
        payload = json.loads(command.call_args.args[1])
        self.assertEqual(payload["execute"], "guest-set-user-password")
        self.assertEqual(payload["arguments"]["username"], "aicowork")
        self.assertIs(payload["arguments"]["crypted"], True)
        self.assertEqual(
            base64.b64decode(payload["arguments"]["password"]),
            b"$y$reviewed-yescrypt-hash",
        )
        self.assertEqual(command.call_args.args[2:], (15, 0))
        conn.close.assert_called_once()

    def test_uuid_change_stops_before_password_command(self):
        grant = Mock()
        grant.DOMAIN = "lab-hermes-deepseek-e2e-r1"
        grant.UUID = "4349a2bc-67b6-42b7-a6ef-5aeee5ee4009"
        domain = Mock()
        domain.UUIDString.return_value = "wrong"
        conn = Mock()
        conn.lookupByName.return_value = domain
        with (
            patch.object(MODULE, "bound_guest"),
            patch.object(MODULE.libvirt, "open", return_value=conn),
            patch.object(MODULE.libvirt_qemu, "qemuAgentCommand") as command,
        ):
            with self.assertRaisesRegex(RuntimeError, "UUID changed"):
                MODULE.apply_hash(grant, "$y$reviewed-yescrypt-hash")
        command.assert_not_called()
        conn.close.assert_called_once()

    def test_mismatched_private_entry_never_hashes_password(self):
        with (
            patch.object(MODULE.sys.stdin, "isatty", return_value=True),
            patch.object(MODULE.sys.stderr, "isatty", return_value=True),
            patch.object(
                MODULE.getpass, "getpass", side_effect=["first-password", "other-password"]
            ),
            patch.object(MODULE.subprocess, "run") as run,
        ):
            with self.assertRaisesRegex(RuntimeError, "did not match"):
                MODULE.private_hash()
        run.assert_not_called()

    def test_private_hash_uses_stdin_not_command_arguments(self):
        completed = Mock(stdout="$y$test-hash\n")
        with (
            patch.object(MODULE.sys.stdin, "isatty", return_value=True),
            patch.object(MODULE.sys.stderr, "isatty", return_value=True),
            patch.object(
                MODULE.getpass,
                "getpass",
                side_effect=["synthetic-long-password", "synthetic-long-password"],
            ),
            patch.object(MODULE.subprocess, "run", return_value=completed) as run,
        ):
            self.assertEqual(MODULE.private_hash(), "$y$test-hash")
        self.assertEqual(run.call_args.args[0], ["/usr/bin/mkpasswd", "-m", "yescrypt", "-s"])
        self.assertEqual(run.call_args.kwargs["input"], "synthetic-long-password\n")


if __name__ == "__main__":
    unittest.main()
