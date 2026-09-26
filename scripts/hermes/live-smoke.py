#!/usr/bin/env python3
"""Private, bounded DeepSeek/Telegram API connectivity smoke on the host.

This does not test an inbound Telegram user or Hermes gateway routing. It makes
at most one paid DeepSeek POST and one outbound Telegram POST per invocation.
No retry is performed. It never prints response bodies, tokens, IDs or URLs.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import pathlib
import stat
import sys
import tempfile
import urllib.error
import urllib.request

PRIVATE = pathlib.Path.home() / ".local/share/hermes-disposable/private"
FILES = {
    "deepseek": "deepseek.key",
    "telegram": "telegram.token",
    "chat": "telegram.chat-id",
    "user": "telegram.user-id",
    "cap": "deepseek-cap-status",
}


class Refusal(RuntimeError):
    pass


def private_directory(create: bool = False) -> None:
    if PRIVATE.is_symlink():
        raise Refusal("private directory is a symlink")
    if create:
        PRIVATE.mkdir(parents=True, mode=0o700, exist_ok=True)
    if not PRIVATE.is_dir():
        raise Refusal("private host setup has not been completed")
    info = PRIVATE.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise Refusal("private host directory has wrong owner or mode")


def read_private(name: str) -> str:
    path = PRIVATE / FILES[name]
    if path.is_symlink() or not path.is_file():
        raise Refusal(f"private {name} file is missing or unsafe")
    info = path.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise Refusal(f"private {name} file has wrong owner or mode")
    value = path.read_text().strip()
    if not value or "\n" in value or "\r" in value:
        raise Refusal(f"private {name} value is empty or malformed")
    return value


def atomic_private(name: str, value: str) -> None:
    path = PRIVATE / FILES[name]
    if path.exists() or path.is_symlink():
        raise Refusal(f"private {name} file exists; revoke or replace it deliberately")
    fd, temp = tempfile.mkstemp(prefix=".setup-", dir=PRIVATE)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(value + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def discover_private_chat(bot: str) -> tuple[str, str]:
    """Find one pending private /start and acknowledge it before gateway startup."""
    url = f"https://api.telegram.org/bot{bot}/getUpdates"
    response = post_json(url, {"limit": 100, "timeout": 0, "allowed_updates": ["message"]})
    updates = response.get("result")
    if response.get("ok") is not True or not isinstance(updates, list):
        raise Refusal("Telegram did not return an update list")
    if len(updates) == 100:
        raise Refusal("too many pending Telegram updates for safe private discovery")
    candidates: list[tuple[int, int]] = []
    for item in updates:
        if not isinstance(item, dict) or type(item.get("update_id")) is not int:
            raise Refusal("unexpected pending Telegram update; enter IDs manually")
        message = item.get("message")
        if not isinstance(message, dict) or message.get("text") != "/start":
            raise Refusal("unexpected pending Telegram message; enter IDs manually")
        sender = message.get("from")
        chat = message.get("chat")
        if not isinstance(sender, dict) or not isinstance(chat, dict):
            raise Refusal("unexpected pending Telegram sender; enter IDs manually")
        user_id, chat_id = sender.get("id"), chat.get("id")
        if not (
            chat.get("type") == "private"
            and type(user_id) is int
            and type(chat_id) is int
            and user_id == chat_id
        ):
            raise Refusal("pending Telegram update is not one private account")
        candidates.append((item["update_id"], user_id))
    if not candidates:
        raise Refusal("send /start from the authorized account to the dedicated bot, then retry")
    if len({user_id for _, user_id in candidates}) != 1:
        raise Refusal("multiple private /start senders are pending; enter IDs manually")
    update_id, user_id = max(candidates)
    acknowledged = post_json(url, {"offset": update_id + 1, "limit": 1, "timeout": 0})
    if acknowledged.get("ok") is not True or acknowledged.get("result") != []:
        raise Refusal("Telegram discovery saw new pending updates; retry with a quiet dedicated bot")
    return str(user_id), str(user_id)


def setup() -> None:
    if not sys.stdin.isatty():
        raise Refusal("run setup in a private interactive host terminal")
    private_directory(create=True)
    if any((PRIVATE / value).exists() for value in FILES.values()):
        raise Refusal("private setup already exists; use status or revoke-local")
    values = {
        "deepseek": getpass.getpass("Dedicated test DeepSeek API key: "),
        "telegram": getpass.getpass("Dedicated test Telegram bot token: "),
    }
    if any(not value or value != value.strip() for value in values.values()):
        raise Refusal("a private value is empty or malformed")
    user = getpass.getpass("Authorized private Telegram user ID (Enter to discover /start): ")
    if user:
        chat = getpass.getpass("Dedicated private Telegram chat ID: ")
    else:
        user, chat = discover_private_chat(values["telegram"])
        print("CHAT_DISCOVERY=PASS one private /start consumed; numeric ID kept private")
    values.update(user=user, chat=chat)
    cap = input("$1 DeepSeek provider-side cap status [verified/unavailable]: ").strip()
    if cap not in {"verified", "unavailable"}:
        raise Refusal("cap status must be verified or unavailable")
    if any(
        not value or value != value.strip() or "\n" in value or "\r" in value
        for value in values.values()
    ):
        raise Refusal("a private value is empty or malformed")
    if not values["user"].lstrip("-").isdigit() or not values["chat"].lstrip("-").isdigit():
        raise Refusal("Telegram user and chat IDs must be numeric")
    if values["deepseek"] == "synthetic-hermes-lab-only":
        raise Refusal("a synthetic provider key cannot be used for live smoke")
    for name, value in (*values.items(), ("cap", cap)):
        atomic_private(name, value)
    print("SETUP=PASS five restricted host-only files; no value displayed")


def replace_deepseek() -> None:
    """Replace only the DeepSeek key after its account cap is reconfirmed."""
    if not sys.stdin.isatty():
        raise Refusal("run key replacement in a private interactive host terminal")
    private_directory()
    for name in FILES:
        read_private(name)
    confirmation = input("Existing provider-side cap status applies to the new key [yes/no]: ").strip()
    if confirmation != "yes":
        raise Refusal("use revoke-local and setup if the replacement key uses another account")
    value = getpass.getpass("Replacement dedicated test DeepSeek API key: ")
    if (
        not value
        or value != value.strip()
        or not value.isascii()
        or any(ord(char) < 33 or ord(char) > 126 for char in value)
        or value == "synthetic-hermes-lab-only"
    ):
        raise Refusal("replacement DeepSeek key is empty or malformed")
    old = read_private("deepseek")
    if value == old:
        print("KEY=UNCHANGED restricted host-only DeepSeek key already matches")
        return
    path = PRIVATE / FILES["deepseek"]
    fd, temp = tempfile.mkstemp(prefix=".replace-", dir=PRIVATE)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(value + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    print("KEY=REPLACED restricted host-only DeepSeek key; no value displayed")


def status() -> None:
    private_directory()
    for name in FILES:
        read_private(name)
    print("PRIVATE_SOURCE=READY restricted host-only files present")


def post_json(url: str, payload: dict, authorization: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if authorization:
        headers["Authorization"] = f"Bearer {authorization}"
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    try:
        # Ignore ambient proxy variables so a bot token in the Telegram URL is
        # sent only over TLS to the intended API endpoint.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=30) as response:
            if response.status != 200:
                raise Refusal(f"live endpoint returned HTTP {response.status}")
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise Refusal(f"live endpoint returned HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError):
        # Telegram places its token in the request URL; never print exceptions.
        raise Refusal("live endpoint connection failed") from None
    except json.JSONDecodeError:
        raise Refusal("live endpoint returned invalid JSON") from None


def smoke() -> None:
    private_directory()
    deepseek = read_private("deepseek")
    bot = read_private("telegram")
    user = read_private("user")
    chat = read_private("chat")
    cap = read_private("cap")
    if cap not in {"verified", "unavailable"}:
        raise Refusal("unknown provider-side spending cap status")
    if user != chat:
        raise Refusal("live smoke requires a dedicated private chat with the authorized user")
    print(f"LIMITS=1 DeepSeek POST, 1 outbound Telegram POST, no retries; provider_cap={cap}")
    result = post_json(
        "https://api.deepseek.com/chat/completions",
        {
            "model": "deepseek-flash",
            "messages": [{"role": "user", "content": "Reply OK."}],
            "max_tokens": 16,
            "stream": False,
        },
        deepseek,
    )
    if not result.get("choices") or not isinstance(result.get("usage"), dict):
        raise Refusal("DeepSeek response lacked completion or usage fields")
    print("DEEPSEEK=PASS authenticated bounded response")
    result = post_json(
        f"https://api.telegram.org/bot{bot}/sendMessage",
        {"chat_id": chat, "text": "Hermes disposable lab: bounded outbound test."},
    )
    if result.get("ok") is not True:
        raise Refusal("Telegram response did not confirm outbound delivery")
    print("TELEGRAM=PASS one outbound API message; inbound authorization NOT RUN")


def revoke_local() -> None:
    private_directory()
    for name in FILES:
        path = PRIVATE / FILES[name]
        if path.is_symlink():
            raise Refusal("private file is a symlink; refuse local deletion")
        if path.exists():
            path.unlink()
    PRIVATE.rmdir()
    print("LOCAL_FILES=ABSENT; revoke both credentials at their providers separately")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("setup", "replace-deepseek", "status", "smoke", "revoke-local")
    )
    args = parser.parse_args()
    try:
        {
            "setup": setup,
            "replace-deepseek": replace_deepseek,
            "status": status,
            "smoke": smoke,
            "revoke-local": revoke_local,
        }[args.action]()
    except (Refusal, OSError, ValueError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
