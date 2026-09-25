"""Offline guardrails for the explicitly selected live API smoke path."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import pathlib
import tempfile
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


if __name__ == "__main__":
    unittest.main()
