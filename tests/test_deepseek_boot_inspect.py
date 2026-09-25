"""Fixed-target, read-only controls for the DeepSeek guest-agent boot inspector."""

import base64
import contextlib
import importlib.util
import io
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/hermes/manual/lab/deepseek-boot-inspect.py"
SPEC = importlib.util.spec_from_file_location("deepseek_boot_inspect", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BootInspectTests(unittest.TestCase):
    def setUp(self):
        self.guest = (
            "guest_user=root\n"
            "guest_hostname=lab-hermes-deepseek-e2e-r1\n"
            f"guest_machine_sha256={MODULE.MACHINE_SHA256}\n"
            "boot_id=test-boot\n"
            "module_systemd-cryptsetup=present\n"
            "module_tpm2-tss=present\n"
        )

    def test_matching_domain_and_guest_reports_boot_metadata(self):
        def virsh(action, _domain):
            return {
                "domuuid": MODULE.UUID,
                "domiflist": f"vnet0 network fvh-nat virtio {MODULE.MAC}",
                "domstate": "running",
            }[action]

        output = io.StringIO()
        with (
            patch.object(MODULE.os, "geteuid", return_value=0),
            patch.object(MODULE, "virsh", side_effect=virsh),
            patch.object(MODULE, "inspect_guest", return_value=self.guest),
            contextlib.redirect_stdout(output),
        ):
            MODULE.main()
        self.assertIn("boot_id=test-boot", output.getvalue())

    def test_wrong_domain_uuid_stops_before_guest_command(self):
        with (
            patch.object(MODULE.os, "geteuid", return_value=0),
            patch.object(MODULE, "virsh", return_value="wrong"),
            patch.object(MODULE, "inspect_guest") as guest,
        ):
            with self.assertRaisesRegex(RuntimeError, "VM UUID mismatch"):
                MODULE.main()
        guest.assert_not_called()

    def test_wrong_guest_identity_does_not_print_boot_metadata(self):
        def virsh(action, _domain):
            return {
                "domuuid": MODULE.UUID,
                "domiflist": f"vnet0 network fvh-nat virtio {MODULE.MAC}",
                "domstate": "running",
            }[action]

        output = io.StringIO()
        with (
            patch.object(MODULE.os, "geteuid", return_value=0),
            patch.object(MODULE, "virsh", side_effect=virsh),
            patch.object(
                MODULE,
                "inspect_guest",
                return_value=self.guest.replace("guest_user=root", "guest_user=other"),
            ),
            contextlib.redirect_stdout(output),
        ):
            with self.assertRaisesRegex(RuntimeError, "guest identity mismatch"):
                MODULE.main()
        self.assertEqual(output.getvalue(), "")

    def test_empty_installer_hostname_is_accepted_with_matching_machine_id(self):
        def virsh(action, _domain):
            return {
                "domuuid": MODULE.UUID,
                "domiflist": f"vnet0 network fvh-nat virtio {MODULE.MAC}",
                "domstate": "running",
            }[action]

        output = io.StringIO()
        with (
            patch.object(MODULE.os, "geteuid", return_value=0),
            patch.object(MODULE, "virsh", side_effect=virsh),
            patch.object(
                MODULE,
                "inspect_guest",
                return_value=self.guest.replace(
                    "guest_hostname=lab-hermes-deepseek-e2e-r1", "guest_hostname="
                ),
            ),
            contextlib.redirect_stdout(output),
        ):
            MODULE.main()
        self.assertIn("boot_id=test-boot", output.getvalue())

    def test_embedded_guest_parser_counts_json_tpm_token(self):
        parser = MODULE.INSPECT.rsplit("python3 -c '\n", 1)[1].split("\n'", 1)[0]
        metadata = {
            "keyslots": {"0": {}, "1": {}},
            "tokens": {
                "0": {
                    "type": "systemd-tpm2",
                    "tpm2-pcrs": [7],
                    "tpm2-pcr-bank": "sha256",
                    "tpm2-salt": None,
                }
            },
        }
        result = subprocess.run(
            ["python3", "-c", parser],
            input=json.dumps(metadata),
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertIn("tpm2_tokens=1", result.stdout)
        self.assertIn("luks2_keyslots=2", result.stdout)
        self.assertIn("tpm2_pcr7_sha256_no_pin=true", result.stdout)

    def test_guest_failure_reports_only_bounded_stderr(self):
        statuses = iter(
            (
                {"pid": 14},
                {
                    "exited": True,
                    "exitcode": 1,
                    "out-data": base64.b64encode(b"private stdout").decode(),
                    "err-data": base64.b64encode(b"diagnostic" * 100).decode(),
                },
            )
        )
        with patch.object(MODULE, "agent", side_effect=lambda _payload: next(statuses)):
            with self.assertRaisesRegex(RuntimeError, "stderr='diagnostic") as caught:
                MODULE.inspect_guest()
        self.assertNotIn("private stdout", str(caught.exception))
        self.assertLess(len(str(caught.exception)), 580)


if __name__ == "__main__":
    unittest.main()
