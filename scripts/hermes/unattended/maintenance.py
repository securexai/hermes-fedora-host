"""Run an enrolled deployment in its window and publish fixed, secret-free local events."""

import argparse
import contextlib
import hashlib
import io
import os
from pathlib import Path
import sys
import time

import controller
from common import Failure, atomic, canonical, decode, lock, protected_file, report, require
from policy import maintenance_open

OUTCOMES = {"completed", "failed", "action-required", "deferred"}
EVENT_FIELDS = {"schema", "outcome", "code", "timestamp", "event_id", "release"}


def publish(directory, outcome, code, release_id=None):
    """Never include exception text, provider responses, config values or child output."""
    require(outcome in OUTCOMES and type(code) is int and 0 <= code <= 255, "invalid-event", 64)
    directory = Path(directory)
    require(directory.is_dir() and not directory.is_symlink()
            and directory.stat().st_uid == os.getuid()
            and not directory.stat().st_mode & 0o022, "unsafe-event-directory")
    path = directory / "latest.json"
    with lock(directory / ".event.lock"):
        previous = decode(protected_file(path).read_bytes()) if path.exists() else {}
        require(isinstance(previous, dict), "invalid-event-state")
        release = hashlib.sha256(str(release_id).encode()).hexdigest() if release_id is not None else None
        if previous.get("outcome") == outcome and previous.get("code") == code and previous.get("release") == release:
            return previous
        value = {"schema": "hermes-event-v1", "outcome": outcome, "code": code,
                 "timestamp": int(time.time()), "release": release}
        value["event_id"] = hashlib.sha256(canonical(value)).hexdigest()
        atomic(path, canonical(value))
        # No secret fields exist in this schema. A separate desktop user can read it.
        path.chmod(0o644)
        return value


def execute(config, release, events):
    if not maintenance_open():
        # Missed windows are normal; no action and no desktop notification.
        return {"ok": True, "stage": "deferred"}
    if not Path(release).is_file():
        publish(events, "action-required", 66)
        raise Failure(66, "certified-release-unavailable")
    previous = sys.argv
    try:
        sys.argv = ["controller.py", "upgrade", "--non-interactive", "--config", str(config),
                    "--release", str(release)]
        # Only the controller's structured result is consumed. Suppress any accidental output.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = controller.main()
        require(isinstance(result, dict) and result.get("ok") is True and result.get("stage") == "closed",
                "maintenance-incomplete", 75)
    except Failure as error:
        publish(events, "action-required" if error.code in (66, 75, 77, 78) else "failed", error.code)
        raise Failure(error.code, "maintenance-needs-attention") from None
    except (OSError, ValueError, KeyError, TypeError):
        publish(events, "failed", 78)
        raise Failure(78, "maintenance-needs-attention") from None
    finally:
        sys.argv = previous
    publish(events, "completed", 0, result.get("release_id"))
    return {"ok": True, "stage": "closed"}


def main():
    parser = argparse.ArgumentParser(description="Run certified Hermes maintenance with local events")
    parser.add_argument("--config")
    parser.add_argument("--release")
    parser.add_argument("--events", required=True)
    parser.add_argument("--service-failed", action="store_true")
    args = parser.parse_args()
    if args.service_failed:
        path = Path(args.events) / "latest.json"
        if path.exists():
            previous = decode(protected_file(path).read_bytes())
            require(isinstance(previous, dict), "invalid-event-state")
            if previous.get("outcome") in ("failed", "action-required") and 0 <= time.time() - previous.get("timestamp", 0) <= 120:
                return previous
        return publish(args.events, "action-required", 69)
    require(args.config and args.release, "maintenance-input-required", 64)
    return execute(args.config, args.release, args.events)


if __name__ == "__main__":
    report(main)
