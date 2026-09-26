"""Offline checks for the disposable VM runner's domain discovery boundary."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import pathlib
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "vm/hermes-disposable.py"
SPEC = importlib.util.spec_from_file_location("hermes_disposable", SOURCE)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DomainDiscoveryTests(unittest.TestCase):
    def test_defined_domain_is_present(self) -> None:
        result = subprocess.CompletedProcess([], 0, f"other\n{MODULE.NAME}\n", "")
        with patch.object(MODULE, "virsh", return_value=result) as virsh:
            self.assertTrue(MODULE.domain_exists())
        virsh.assert_called_once_with("list", "--all", "--name")

    def test_empty_successful_list_means_absent(self) -> None:
        result = subprocess.CompletedProcess([], 0, "", "")
        with patch.object(MODULE, "virsh", return_value=result):
            self.assertFalse(MODULE.domain_exists())

    def test_connection_failure_does_not_claim_absence_or_clean_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            instance = pathlib.Path(temp) / "instance"
            instance.mkdir()
            (instance / "identity.json").write_text("marker\n")
            output = io.StringIO()
            with (
                patch.object(MODULE, "INSTANCE", instance),
                patch.object(MODULE, "virsh", side_effect=MODULE.LabError("libvirt unavailable")),
                contextlib.redirect_stdout(output),
            ):
                with self.assertRaisesRegex(MODULE.LabError, "libvirt unavailable"):
                    MODULE.status()
                with self.assertRaisesRegex(MODULE.LabError, "libvirt unavailable"):
                    MODULE.clean()
            self.assertEqual(output.getvalue(), "")
            self.assertTrue((instance / "identity.json").is_file())

    def test_marked_instance_with_unexpected_file_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            instance = pathlib.Path(temp) / "instance"
            instance.mkdir()
            (instance / "identity.json").write_text(
                json.dumps({"name": MODULE.NAME, "disk": str(instance / "disk.qcow2")})
            )
            (instance / "unrelated.txt").write_text("keep\n")
            with (
                patch.object(MODULE, "INSTANCE", instance),
                patch.object(MODULE, "domain_exists", return_value=False),
            ):
                with self.assertRaisesRegex(MODULE.LabError, "unexpected path"):
                    MODULE.clean()
            self.assertEqual((instance / "unrelated.txt").read_text(), "keep\n")


class LiveIntegrationGuardsTests(unittest.TestCase):
    def test_pending_bot_update_prevents_private_guest_payload(self) -> None:
        values = {
            "deepseek": "dedicated-test-key",
            "telegram": "123:dedicated-test-bot",
            "user": "12345",
            "chat": "12345",
            "cap": "unavailable",
        }
        source = types.SimpleNamespace(
            FILES=values,
            Refusal=RuntimeError,
            private_directory=lambda: None,
            read_private=values.__getitem__,
            post_json=lambda url, payload: (
                {"ok": True, "result": {"url": ""}}
                if url.endswith("getWebhookInfo")
                else {"ok": True, "result": [{"update_id": 17}]}
            ),
        )
        with patch.object(MODULE, "live_source", return_value=source):
            with self.assertRaisesRegex(MODULE.LabError, "pending updates"):
                MODULE.live_values()

    def test_guest_transfer_failure_does_not_print_secret_or_remote_error(self) -> None:
        result = subprocess.CompletedProcess([], 1, b"", b"123:dedicated-test-bot")
        with (
            patch.object(MODULE, "ssh_base", return_value=["ssh"]),
            patch.object(MODULE.subprocess, "run", return_value=result),
        ):
            with self.assertRaises(MODULE.LabError) as failure:
                MODULE.live_guest("inject", b"123:dedicated-test-bot")
        self.assertNotIn("dedicated-test-bot", str(failure.exception))

    def test_guest_transfer_reports_only_an_allowlisted_reason(self) -> None:
        result = subprocess.CompletedProcess(
            [], 1, b"", b"STOP: private live environment contains an invalid value\n"
        )
        with (
            patch.object(MODULE, "ssh_base", return_value=["ssh"]),
            patch.object(MODULE.subprocess, "run", return_value=result),
        ):
            with self.assertRaisesRegex(MODULE.LabError, "invalid value"):
                MODULE.live_guest("inject", b"123:dedicated-test-bot")

    def test_live_deploy_reason_redacts_private_values(self) -> None:
        result = subprocess.CompletedProcess([], 1, "", "STOP: failed for 123:dedicated-test-bot\n")
        reason = MODULE.live_deploy_error(
            result, b"TELEGRAM_BOT_TOKEN=123:dedicated-test-bot\nTELEGRAM_ALLOWED_USERS=12345\n"
        )
        self.assertIn("[redacted]", reason)
        self.assertNotIn("dedicated-test-bot", reason)


if __name__ == "__main__":
    unittest.main()
