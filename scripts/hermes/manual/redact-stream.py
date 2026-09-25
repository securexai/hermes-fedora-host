#!/usr/bin/env python3
"""Filter stdin, replacing values of known secret keys read from an env file.

Used by the manual helpers to sanitize command output before it reaches a log or
a terminal. It is a tracked, reviewed helper rather than a generated temporary
file, and it never prints or stores a secret value.

    command 2>&1 | python3 redact-stream.py /opt/data/.env

Short values are left alone: a one-character setting is not a credential, and
replacing it would corrupt unrelated output.
"""

from __future__ import annotations

import sys

SECRET_KEYS = (
    "TELEGRAM_BOT_TOKEN=",
    "TELEGRAM_ALLOWED_USERS=",
    "OPENAI_API_KEY=",
    "DEEPSEEK_API_KEY=",
    "OPENROUTER_API_KEY=",
    "API_SERVER_KEY=",
    "SUDO_PASSWORD=",
)
MIN_SECRET_LENGTH = 8
PLACEHOLDER = "[REDACTED]"


def collect_secrets(path: str) -> list[str]:
    secrets: list[str] = []
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                for key in SECRET_KEYS:
                    if line.startswith(key):
                        value = line.split("=", 1)[1].strip()
                        if len(value) >= MIN_SECRET_LENGTH:
                            secrets.append(value)
    except OSError:
        # A missing or unreadable env file is not fatal: output simply passes
        # through unredacted, which is why callers must not treat this as a
        # security control for arbitrary text.
        pass
    return secrets


def main(argv: list[str]) -> int:
    env_path = argv[1] if len(argv) > 1 else ""
    secrets = collect_secrets(env_path) if env_path else []
    data = sys.stdin.read()
    for value in sorted(secrets, key=len, reverse=True):
        data = data.replace(value, PLACEHOLDER)
    sys.stdout.write(data)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
