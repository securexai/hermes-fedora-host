#!/usr/bin/env python3
"""Prompt-gated PTY interaction for the disposable Hermes LUKS fixture."""

from __future__ import annotations

import argparse
import datetime as dt
import errno
import os
import pty
import re
import select
import signal
import time
from pathlib import Path

BUFFER_LIMIT = 4096
FIXTURE_PASSPHRASE = b"hermes-e2e-fixture"
VERIFIED_PROMPT_LINE = re.compile(
    rb"(?:Please enter passphrase for disk |Enter passphrase for disk )"
    rb"[^\r\n:]*[^\s:\r\n][ \t]*:"
)
UTF8_ELLIPSIS = b"\xe2\x80\xa6"
# systemd middle-ellipsizes long escaped unit names on the serial console.
# Require a hexadecimal UUID tail after that ellipsis so arbitrary status text
# cannot rearm the one-submission-per-boot gate.
BOOT_BOUNDARY_LINE = re.compile(
    rb"Starting[ \t]+systemd-cryptsetup@luks"
    rb"(?:\\x2d[A-Za-z0-9]|-[A-Za-z0-9]|\\x"
    + re.escape(UTF8_ELLIPSIS)
    + rb"[0-9A-Fa-f])"
)
REBOOT_MARKER_LINE = re.compile(
    rb"(?:Reached target reboot\.target(?: - System Reboot\.)?"
    rb"|systemd-shutdown\[[0-9]+\]: Rebooting\."
    rb"|reboot: Restarting system)"
)
CONNECTED_BANNER = b"Connected to domain "
ANSI_ESCAPE = re.compile(rb"\x1b\[[0-?]*[ -/]*[@-~]")
STOP_REQUESTED = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Unlock the disposable Hermes VM only after a verified LUKS prompt."
    )
    parser.add_argument("--domain", required=True)
    parser.add_argument("--uri", required=True)
    parser.add_argument("--timeout", required=True, type=int)
    parser.add_argument("--event-log", required=True, type=Path)
    parser.add_argument("--ready-file", type=Path)
    parser.add_argument("--watch", action="store_true")
    return parser.parse_args()


def append_event(event_log: Path, message: str) -> None:
    timestamp = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with event_log.open("a", encoding="utf-8") as stream:
        stream.write(f"{timestamp} {message}\n")


def normalized_console_output(console_output: bytes) -> bytes:
    return ANSI_ESCAPE.sub(b"", console_output)


def prompt_is_verified(console_output: bytes) -> bool:
    return bool(VERIFIED_PROMPT_LINE.search(normalized_console_output(console_output)))


def latest_boot_boundary(console_output: bytes) -> tuple[bytes, int | None]:
    normalized = normalized_console_output(console_output)
    matches = list(BOOT_BOUNDARY_LINE.finditer(normalized))
    if not matches:
        return normalized, None
    return normalized, matches[-1].end()


def latest_reboot_marker(console_output: bytes) -> tuple[bytes, int | None]:
    normalized = normalized_console_output(console_output)
    matches = list(REBOOT_MARKER_LINE.finditer(normalized))
    if not matches:
        return normalized, None
    return normalized, matches[-1].end()


def console_is_attached(console_output: bytes) -> bool:
    return CONNECTED_BANNER in ANSI_ESCAPE.sub(b"", console_output)


def mark_console_ready(ready_file: Path) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_CLOEXEC
    flags |= getattr(os, "O_NOFOLLOW", 0)
    file_descriptor = os.open(ready_file, flags, 0o600)
    os.close(file_descriptor)


def request_stop(_signum: int, _frame: object) -> None:
    global STOP_REQUESTED
    STOP_REQUESTED = True


def submit_fixture(master_fd: int, event_log: Path) -> None:
    payload = FIXTURE_PASSPHRASE + b"\r"
    written = 0
    while written < len(payload):
        written += os.write(master_fd, payload[written:])
    append_event(event_log, "luks-prompt-verified input-submitted=1")


def console_exit_detail(console_output: bytes) -> str:
    text = console_output.decode("utf-8", errors="replace")
    if "Safe console handling requested but not supported" in text:
        return "safe-console-unsupported"
    if "console is already active" in text:
        return "console-already-active"
    if "console connection refused" in text:
        return "console-connection-refused"
    if "Cannot run interactive console without a controlling TTY" in text:
        return "controlling-tty-missing"
    if "Requested operation is not valid" in text:
        return "requested-operation-invalid"
    if "error:" in text:
        return "virsh-error"
    return "console-process-exited"


def child_exit_code(pid: int) -> int | None:
    try:
        waited_pid, status = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        return 0
    if waited_pid == 0:
        return None
    return os.waitstatus_to_exitcode(status)


def stop_child(pid: int, exit_code: int | None) -> None:
    if exit_code is not None:
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        if child_exit_code(pid) is not None:
            return
        time.sleep(0.05)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    try:
        os.waitpid(pid, 0)
    except ChildProcessError:
        pass


def run_console(
    domain: str,
    uri: str,
    timeout: int,
    event_log: Path,
    ready_file: Path | None = None,
    watch: bool = False,
) -> int:
    global STOP_REQUESTED
    if timeout <= 0:
        return 64
    STOP_REQUESTED = False
    if ready_file is not None:
        ready_file.unlink(missing_ok=True)

    pid, master_fd = pty.fork()
    if pid == 0:
        try:
            os.execvp("virsh", ["virsh", "-c", uri, "console", domain, "--safe"])
        except OSError:
            os._exit(127)

    console_output = b""
    exit_code: int | None = None
    deadline = time.monotonic() + timeout
    console_attached = False
    unlock_count = 0
    # A one-shot attachment is created specifically for the installer boot and
    # may accept its first verified prompt immediately.  The persistent watcher
    # attaches to an already-running guest, so it must observe an explicit
    # shutdown/reboot marker and then the per-boot encrypted-root cryptsetup
    # start before accepting each reboot-time prompt.  Requiring both prevents a
    # same-boot redraw of the cryptsetup status from pre-arming the next boot.
    prompt_armed = not watch
    reboot_observed = False
    previous_handlers = {
        sig: signal.signal(sig, request_stop) for sig in (signal.SIGINT, signal.SIGTERM)
    }
    try:
        while time.monotonic() < deadline and not STOP_REQUESTED:
            readable, _, _ = select.select([master_fd], [], [], 0.1)
            if readable:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    chunk = b""
                if chunk:
                    console_output = (console_output + chunk)[-BUFFER_LIMIT:]
                    if not console_attached and console_is_attached(console_output):
                        console_attached = True
                        if ready_file is not None:
                            mark_console_ready(ready_file)
                        append_event(event_log, "luks-console-attached input-submitted=0")
                    if watch and not prompt_armed and not reboot_observed:
                        normalized, reboot_end = latest_reboot_marker(console_output)
                        if reboot_end is not None:
                            reboot_observed = True
                            console_output = normalized[reboot_end:]
                            append_event(
                                event_log,
                                "luks-reboot-observed input-submitted=0",
                            )
                    if not prompt_armed and (not watch or reboot_observed):
                        normalized, boundary_end = latest_boot_boundary(console_output)
                        if boundary_end is not None:
                            prompt_armed = True
                            reboot_observed = False
                            console_output = normalized[boundary_end:]
                            append_event(
                                event_log,
                                "luks-boot-boundary-observed input-submitted=0",
                            )
                    if prompt_armed and prompt_is_verified(console_output):
                        submit_fixture(master_fd, event_log)
                        unlock_count += 1
                        prompt_armed = False
                        if not watch:
                            time.sleep(1)
                            return 0
                        console_output = b""
                        time.sleep(0.1)
                        continue
            exit_code = child_exit_code(pid)
            if exit_code is not None:
                break

        if exit_code is not None:
            detail = console_exit_detail(console_output)
            append_event(
                event_log,
                f"luks-console-exited input-submitted=0 detail={detail} exit-code={exit_code}",
            )
        elif watch:
            detail = "stopped" if STOP_REQUESTED else "timeout"
            append_event(
                event_log,
                "luks-console-watch-ended input-submitted=0 "
                f"unlocks={unlock_count} detail={detail}",
            )
        else:
            append_event(event_log, "luks-prompt-not-observed input-submitted=0")
        return 1
    finally:
        stop_child(pid, exit_code)
        os.close(master_fd)
        for sig, previous_handler in previous_handlers.items():
            signal.signal(sig, previous_handler)


def main() -> int:
    args = parse_args()
    return run_console(
        args.domain,
        args.uri,
        args.timeout,
        args.event_log,
        args.ready_file,
        args.watch,
    )


if __name__ == "__main__":
    raise SystemExit(main())
