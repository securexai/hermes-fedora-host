"""Offline guards for the guest's temporary live profile payload."""

from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest
from unittest.mock import call, patch

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "scripts/hermes/live-guest.py"
SPEC = importlib.util.spec_from_file_location("hermes_live_guest", SOURCE)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GuestPayloadTests(unittest.TestCase):
    def test_exact_private_payload_is_accepted_without_external_calls(self) -> None:
        MODULE.validate_payload(
            b"DEEPSEEK_API_KEY=dedicated-test-key\n"
            b"TELEGRAM_BOT_TOKEN=123:dedicated-test-bot\n"
            b"TELEGRAM_ALLOWED_USERS=12345\n"
            b"TELEGRAM_ALLOW_ALL_USERS=false\n"
        )

    def test_synthetic_key_or_extra_entry_is_refused(self) -> None:
        base = (
            b"DEEPSEEK_API_KEY=dedicated-test-key\n"
            b"TELEGRAM_BOT_TOKEN=123:dedicated-test-bot\n"
            b"TELEGRAM_ALLOWED_USERS=12345\n"
            b"TELEGRAM_ALLOW_ALL_USERS=false\n"
        )
        for payload in (
            base.replace(b"dedicated-test-key", b"synthetic-hermes-lab-only"),
            base + b"UNREVIEWED_SETTING=1\n",
            base.replace(b"TELEGRAM_ALLOWED_USERS=12345", b"TELEGRAM_ALLOWED_USERS=*"),
            base.replace(b"TELEGRAM_ALLOW_ALL_USERS=false", b"TELEGRAM_ALLOW_ALL_USERS=true"),
        ):
            with self.subTest(payload=payload[:24]):
                with self.assertRaises(MODULE.Refusal):
                    MODULE.validate_payload(payload)

    def test_only_the_observed_guest_zram_swap_may_be_disabled(self) -> None:
        with (
            patch.object(MODULE, "active_swap", side_effect=[["/dev/zram0"], []]),
            patch.object(MODULE, "command") as command,
        ):
            MODULE.disable_exact_zram_swap()
        self.assertEqual(command.call_args_list, [call("/usr/sbin/swapoff", "/dev/zram0")])
        with (
            patch.object(MODULE, "active_swap", return_value=["/dev/vda2"]),
            patch.object(MODULE, "command") as command,
        ):
            with self.assertRaises(MODULE.Refusal):
                MODULE.disable_exact_zram_swap()
        command.assert_not_called()

    def test_underlying_synthetic_profile_rejects_a_bot_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / ".env"
            path.write_text(
                "DEEPSEEK_API_KEY=synthetic-hermes-lab-only\n"
                "API_SERVER_ENABLED=false\n"
                "HERMES_DASHBOARD=0\n"
                "GATEWAY_ALLOW_ALL_USERS=false\n"
                "WEBHOOK_ENABLED=false\n"
                "API_SERVER_KEY=synthetic-test-only\n"
            )
            path.chmod(0o600)
            with patch.object(MODULE, "ENV", path):
                self.assertTrue(MODULE.exact_synthetic_profile())
                with path.open("a") as stream:
                    stream.write("TELEGRAM_BOT_TOKEN=synthetic-test-only\n")
                self.assertFalse(MODULE.exact_synthetic_profile())

    def test_gateway_id_maps_to_the_pinned_subordinate_range(self) -> None:
        self.assertEqual(MODULE.mapped_host_id("0 1001 1\n1 100000 65536\n"), 109999)
        with self.assertRaises(MODULE.Refusal):
            MODULE.mapped_host_id("0 1001 1\n")


if __name__ == "__main__":
    unittest.main()
