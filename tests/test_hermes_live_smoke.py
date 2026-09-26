"""Offline guardrails for the explicitly selected live API smoke path."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import pathlib
import tempfile
import types
import unittest
from unittest.mock import patch

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "scripts/hermes/live-smoke.py"
SPEC = importlib.util.spec_from_file_location("hermes_live_smoke", SOURCE)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LiveSmokeBoundsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.private = pathlib.Path(self.temp.name) / "private"
        self.private.mkdir(mode=0o700)
        self.original = MODULE.PRIVATE
        MODULE.PRIVATE = self.private
        self.addCleanup(setattr, MODULE, "PRIVATE", self.original)
        for name, value in {
            "deepseek": "dedicated-test-key",
            "telegram": "dedicated-test-bot-token",
            "user": "12345",
            "chat": "12345",
            "cap": "unavailable",
        }.items():
            path = self.private / MODULE.FILES[name]
            path.write_text(value + "\n")
            path.chmod(0o600)

    def test_at_most_one_post_to_each_service_and_no_secret_output(self) -> None:
        calls = []

        def fake_post(url, payload, authorization=None):
            calls.append((url, payload, authorization))
            return (
                {"choices": [{}], "usage": {"total_tokens": 2}} if authorization else {"ok": True}
            )

        output = io.StringIO()
        with (
            patch.object(MODULE, "post_json", side_effect=fake_post),
            contextlib.redirect_stdout(output),
        ):
            MODULE.smoke()
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][2], "dedicated-test-key")
        self.assertIn("sendMessage", calls[1][0])
        self.assertNotIn("dedicated-test-key", output.getvalue())
        self.assertNotIn("dedicated-test-bot-token", output.getvalue())
        self.assertNotIn("12345", output.getvalue())

    def test_mismatched_user_and_chat_prevent_all_calls(self) -> None:
        (self.private / MODULE.FILES["chat"]).write_text("67890\n")
        with patch.object(MODULE, "post_json") as request:
            with self.assertRaises(MODULE.Refusal):
                MODULE.smoke()
        request.assert_not_called()

    def test_wrong_file_mode_prevents_all_calls(self) -> None:
        (self.private / MODULE.FILES["deepseek"]).chmod(0o644)
        with patch.object(MODULE, "post_json") as request:
            with self.assertRaises(MODULE.Refusal):
                MODULE.smoke()
        request.assert_not_called()

    def test_discovers_one_private_start_and_acknowledges_it(self) -> None:
        updates = {
            "ok": True,
            "result": [
                {
                    "update_id": 17,
                    "message": {
                        "text": "/start",
                        "from": {"id": 12345},
                        "chat": {"id": 12345, "type": "private"},
                    },
                }
            ],
        }
        with patch.object(MODULE, "post_json", side_effect=[updates, {"ok": True, "result": []}]) as request:
            self.assertEqual(MODULE.discover_private_chat("dedicated-test-bot-token"), ("12345", "12345"))
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args_list[1].args[1]["offset"], 18)

    def test_ambiguous_private_senders_do_not_acknowledge_updates(self) -> None:
        updates = {
            "ok": True,
            "result": [
                {"update_id": i, "message": {"text": "/start", "from": {"id": i}, "chat": {"id": i, "type": "private"}}}
                for i in (17, 18)
            ],
        }
        with patch.object(MODULE, "post_json", return_value=updates) as request:
            with self.assertRaises(MODULE.Refusal):
                MODULE.discover_private_chat("dedicated-test-bot-token")
        self.assertEqual(request.call_count, 1)

    def test_replaces_only_deepseek_key_without_exposing_values(self) -> None:
        output = io.StringIO()
        with (
            patch.object(MODULE.sys, "stdin", types.SimpleNamespace(isatty=lambda: True)),
            patch("builtins.input", return_value="yes"),
            patch.object(MODULE.getpass, "getpass", return_value="replacement-key"),
            contextlib.redirect_stdout(output),
        ):
            MODULE.replace_deepseek()
            MODULE.replace_deepseek()
        self.assertEqual(MODULE.read_private("deepseek"), "replacement-key")
        self.assertEqual((self.private / MODULE.FILES["deepseek"]).stat().st_mode & 0o777, 0o600)
        self.assertEqual(MODULE.read_private("telegram"), "dedicated-test-bot-token")
        self.assertEqual(MODULE.read_private("cap"), "unavailable")
        self.assertIn("KEY=REPLACED", output.getvalue())
        self.assertIn("KEY=UNCHANGED", output.getvalue())
        self.assertNotIn("replacement-key", output.getvalue())

    def test_replacement_refuses_changed_account_or_unsafe_key(self) -> None:
        old = MODULE.read_private("deepseek")
        with (
            patch.object(MODULE.sys, "stdin", types.SimpleNamespace(isatty=lambda: True)),
            patch("builtins.input", return_value="no"),
            patch.object(MODULE.getpass, "getpass") as prompt,
        ):
            with self.assertRaises(MODULE.Refusal):
                MODULE.replace_deepseek()
        prompt.assert_not_called()
        with (
            patch.object(MODULE.sys, "stdin", types.SimpleNamespace(isatty=lambda: True)),
            patch("builtins.input", return_value="yes"),
            patch.object(MODULE.getpass, "getpass", return_value="bad\nkey"),
        ):
            with self.assertRaises(MODULE.Refusal):
                MODULE.replace_deepseek()
        self.assertEqual(MODULE.read_private("deepseek"), old)

    def test_replacement_refuses_unsafe_existing_file(self) -> None:
        (self.private / MODULE.FILES["deepseek"]).chmod(0o644)
        with (
            patch.object(MODULE.sys, "stdin", types.SimpleNamespace(isatty=lambda: True)),
            patch("builtins.input") as prompt,
        ):
            with self.assertRaises(MODULE.Refusal):
                MODULE.replace_deepseek()
        prompt.assert_not_called()


if __name__ == "__main__":
    unittest.main()
