"""Offline lifecycle checks for the fixed read-only guest permission inspector."""

import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts/hermes/manual/lab/deepseek-guest-permission-inspect.py"
)
SPEC = importlib.util.spec_from_file_location("deepseek_guest_permission_inspect", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PermissionInspectorTests(unittest.TestCase):
    def guest(self):
        guest = Mock()
        guest.DOMAIN = "lab-hermes-deepseek-e2e-r1"
        guest.bound_vm.side_effect = ["shut off", "running", "running", "shut off"]
        guest.virsh.side_effect = ["started", "shutdown requested"]
        guest.guest_script.return_value = "guest_euid=0\n"
        return guest

    def test_starts_pinned_vm_reads_then_shuts_down(self):
        guest = self.guest()
        with patch.object(MODULE.time, "monotonic", return_value=0):
            MODULE.inspect_and_shutdown(guest)
        self.assertEqual(
            guest.virsh.call_args_list,
            [call("start", guest.DOMAIN), call("shutdown", guest.DOMAIN)],
        )
        guest.guest_script.assert_called_once_with(MODULE.GUEST_INSPECT)
        guest.bound_network.assert_called_once()
        guest.guest_identity.assert_called_once()

    def test_guest_inspection_failure_still_requests_shutdown(self):
        guest = self.guest()
        guest.guest_script.side_effect = RuntimeError("guest read failed")
        with patch.object(MODULE.time, "monotonic", return_value=0):
            with self.assertRaisesRegex(RuntimeError, "guest read failed"):
                MODULE.inspect_and_shutdown(guest)
        self.assertEqual(guest.virsh.call_args_list[-1], call("shutdown", guest.DOMAIN))

    def test_start_timeout_still_checks_and_requests_shutdown(self):
        guest = self.guest()
        guest.bound_vm.side_effect = ["shut off", "running", "shut off"]
        guest.virsh.side_effect = [
            subprocess.TimeoutExpired("virsh start", 30),
            "shutdown requested",
        ]
        with self.assertRaises(subprocess.TimeoutExpired):
            MODULE.inspect_and_shutdown(guest)
        self.assertEqual(guest.virsh.call_args_list[-1], call("shutdown", guest.DOMAIN))


if __name__ == "__main__":
    unittest.main()
