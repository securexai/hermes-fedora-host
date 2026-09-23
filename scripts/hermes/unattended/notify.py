"""Desktop delivery of fixed Hermes maintenance messages; no external messaging service."""

import argparse
import hashlib
import os
from pathlib import Path
import re

from common import atomic, canonical, decode, lock, protected_file, report, require, run
from maintenance import EVENT_FIELDS, OUTCOMES

MESSAGES = {
    "completed": "Hermes certified maintenance completed.",
    "failed": "Hermes maintenance failed. Review the local deployment status.",
    "action-required": "Hermes maintenance needs operator attention. Review the local deployment status.",
}


def deliver(event_path, state_directory):
    event_path, state_directory = Path(event_path), Path(state_directory)
    if not event_path.exists():
        return {"ok": True, "notified": False}
    require(event_path.stat().st_size <= 4096, "oversized-notification")
    value = decode(protected_file(event_path).read_bytes())
    require(isinstance(value, dict) and set(value) == EVENT_FIELDS and value["schema"] == "hermes-event-v1"
            and value["outcome"] in OUTCOMES and type(value["code"]) is int and 0 <= value["code"] <= 255
            and type(value["timestamp"]) is int and value["timestamp"] > 0
            and (value["release"] is None or isinstance(value["release"], str)
                 and re.fullmatch(r"[a-f0-9]{64}", value["release"]))
            and isinstance(value["event_id"], str) and re.fullmatch(r"[a-f0-9]{64}", value["event_id"]),
            "invalid-notification")
    expected = hashlib.sha256(canonical({key: item for key, item in value.items() if key != "event_id"})).hexdigest()
    require(value["event_id"] == expected, "notification-integrity-mismatch")
    state_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    require(not state_directory.is_symlink() and state_directory.stat().st_uid == os.getuid()
            and not state_directory.stat().st_mode & 0o077, "unsafe-notification-state")
    with lock(state_directory / "notify.lock"):
        seen = state_directory / "seen"
        if seen.exists() and protected_file(seen).read_text() == value["event_id"]:
            return {"ok": True, "notified": False}
        if value["outcome"] in MESSAGES:
            run(["notify-send", "--app-name=Hermes", "--urgency=normal", "--",
                 "Hermes maintenance", MESSAGES[value["outcome"]]], timeout=15)
        atomic(seen, value["event_id"].encode())
        return {"ok": True, "notified": value["outcome"] in MESSAGES}


def main():
    parser = argparse.ArgumentParser(description="Deliver secret-free local Hermes notifications")
    parser.add_argument("--event", required=True)
    parser.add_argument("--state", required=True)
    args = parser.parse_args()
    return deliver(args.event, args.state)


if __name__ == "__main__":
    report(main)
