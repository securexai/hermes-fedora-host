#!/usr/bin/env python3
"""Exercise the pinned Hermes image's provider selection and Telegram gate offline."""

from __future__ import annotations

import json
import os
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch

from hermes_cli import runtime_provider
from openai import OpenAI
from plugins.platforms.telegram import adapter as telegram


class MockServices(BaseHTTPRequestHandler):
    requests: list[tuple[str, dict, str]] = []

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.requests.append((self.path, body, self.headers.get("Authorization", "")))
        if self.path == "/v1/chat/completions":
            response = {
                "id": "synthetic-1",
                "object": "chat.completion",
                "created": 1,
                "model": "deepseek-flash",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "OK"},
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        elif self.path == "/botsynthetic-token/sendMessage":
            response = {"ok": True, "result": {"message_id": 1}}
        else:
            self.send_error(404)
            return
        data = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, _format: str, *_args: object) -> None:
        pass


def provider_checks(port: int) -> None:
    profile = SimpleNamespace(api_key_env_vars=("DEEPSEEK_API_KEY",))
    model = {
        "provider": "deepseek",
        "default": "deepseek-flash",
        "base_url": f"http://127.0.0.1:{port}/v1",
    }
    synthetic = {
        "api_key": "synthetic-hermes-lab-only",
        "base_url": "https://api.deepseek.com",
        "source": "env",
    }
    with patch.object(
        runtime_provider, "resolve_api_key_provider_credentials", return_value=synthetic
    ):
        resolved = runtime_provider._api_key_provider_runtime(
            "deepseek", profile, "deepseek", model, "deepseek-flash"
        )
    assert resolved["provider"] == "deepseek"
    assert resolved["api_mode"] == "chat_completions"
    assert resolved["base_url"] == model["base_url"]
    assert resolved["api_key"] == synthetic["api_key"]
    client = OpenAI(
        api_key=resolved["api_key"],
        base_url=resolved["base_url"],
        max_retries=0,
        timeout=5,
    )
    answer = client.chat.completions.create(
        model="deepseek-flash",
        messages=[{"role": "user", "content": "Reply OK."}],
        max_tokens=8,
    )
    assert answer.choices[0].message.content == "OK"
    with patch.object(
        runtime_provider,
        "resolve_api_key_provider_credentials",
        return_value={"api_key": "", "base_url": "https://api.deepseek.com"},
    ):
        try:
            runtime_provider._api_key_provider_runtime(
                "deepseek", profile, "deepseek", model, "deepseek-flash"
            )
        except runtime_provider.AuthError:
            pass
        else:
            raise AssertionError("missing DeepSeek credential did not fail closed")


def telegram_checks(port: int) -> None:
    instance = object.__new__(telegram.TelegramAdapter)
    with patch.object(
        telegram,
        "_scoped_gate_env",
        side_effect=lambda key: {
            "TELEGRAM_ALLOWED_USERS": "12345",
            "GATEWAY_ALLOW_ALL_USERS": "false",
        }.get(key, ""),
    ):
        assert instance._is_callback_user_authorized("12345", chat_type="private")
        assert not instance._is_callback_user_authorized("67890", chat_type="private")
        assert not instance._is_callback_user_authorized("", chat_type="private")
        if instance._is_callback_user_authorized("12345", chat_type="private"):
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/botsynthetic-token/sendMessage",
                data=json.dumps({"chat_id": "12345", "text": "synthetic"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                assert json.load(response)["ok"] is True
    with patch.object(telegram, "_scoped_gate_env", return_value=""):
        assert not instance._is_callback_user_authorized("12345", chat_type="private")


def main() -> None:
    assert not os.environ.get("DEEPSEEK_API_KEY")
    assert not os.environ.get("TELEGRAM_BOT_TOKEN")
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    MockServices.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), MockServices)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        provider_checks(server.server_port)
        telegram_checks(server.server_port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert [path for path, _, _ in MockServices.requests] == [
        "/v1/chat/completions",
        "/botsynthetic-token/sendMessage",
    ]
    assert MockServices.requests[0][2] == "Bearer synthetic-hermes-lab-only"
    print("PASS: pinned-image DeepSeek/Telegram mock HTTP, allow/reject (synthetic, offline)")


if __name__ == "__main__":
    main()
