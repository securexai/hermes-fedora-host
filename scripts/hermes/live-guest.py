#!/usr/bin/env python3
"""Short-lived, tmpfs-only live credentials for the disposable Hermes guest.

The host sends the private profile environment on SSH stdin. This helper never
prints its input, and the guest's unencrypted disk receives no live secret file.
"""

from __future__ import annotations

import os
import pathlib
import pwd
import stat
import subprocess
import sys

STATE = pathlib.Path("/home/hermes/gateway-state")
ENV = STATE / ".env"
KEYS = {
    "DEEPSEEK_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ALLOWED_USERS",
    "TELEGRAM_ALLOW_ALL_USERS",
}
SYNTHETIC_KEYS = {
    "DEEPSEEK_API_KEY",
    "API_SERVER_ENABLED",
    "HERMES_DASHBOARD",
    "GATEWAY_ALLOW_ALL_USERS",
    "WEBHOOK_ENABLED",
    "API_SERVER_KEY",
}


class Refusal(RuntimeError):
    pass


def command(*argv: str) -> None:
    result = subprocess.run(argv, capture_output=True, check=False, timeout=45, cwd=STATE.parent)
    if result.returncode:
        raise Refusal(f"{pathlib.Path(argv[0]).name} failed (exit {result.returncode})")


def check_host() -> None:
    if os.geteuid() != 0 or not STATE.is_dir() or STATE.is_symlink():
        raise Refusal("expected disposable guest root and gateway state directory")
    result = subprocess.run(("/usr/sbin/getenforce",), capture_output=True, check=False)
    if result.returncode or result.stdout.strip() != b"Enforcing":
        raise Refusal("SELinux must be Enforcing")


def active_swap() -> list[str]:
    result = subprocess.run(
        ("/usr/sbin/swapon", "--noheadings", "--raw", "--show=NAME"),
        capture_output=True, check=False,
    )
    if result.returncode:
        raise Refusal("cannot inspect guest swap")
    return result.stdout.decode("ascii").splitlines()


def disable_exact_zram_swap() -> None:
    names = active_swap()
    if names == ["/dev/zram0"]:
        command("/usr/sbin/swapoff", "/dev/zram0")
    elif names:
        raise Refusal("unexpected guest swap device; refuse live credentials")
    if active_swap():
        raise Refusal("guest swap remains active")


def stop_gateway() -> None:
    uid = pwd.getpwnam("hermes").pw_uid
    command(
        "/usr/sbin/runuser", "-u", "hermes", "--", "/usr/bin/env", "-i",
        "HOME=/home/hermes", "USER=hermes", "LOGNAME=hermes", "PATH=/usr/bin:/bin",
        f"XDG_RUNTIME_DIR=/run/user/{uid}",
        f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus",
        "/usr/bin/systemctl", "--user", "stop", "hermes-gateway.service",
    )


def mapped_host_id(mapping: str, container_id: int = 10000) -> int:
    for line in mapping.splitlines():
        try:
            inside, outside, length = (int(part) for part in line.split())
        except ValueError as exc:
            raise Refusal("rootless Podman ID map is malformed") from exc
        if inside <= container_id < inside + length:
            return outside + container_id - inside
    raise Refusal("rootless Podman ID map lacks gateway UID")


def gateway_host_ids() -> tuple[int, int]:
    uid = pwd.getpwnam("hermes").pw_uid
    prefix = (
        "/usr/sbin/runuser", "-u", "hermes", "--", "/usr/bin/env", "-i",
        "HOME=/home/hermes", "USER=hermes", "LOGNAME=hermes", "PATH=/usr/bin:/bin",
        f"XDG_RUNTIME_DIR=/run/user/{uid}",
        f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus",
        "/usr/bin/podman", "unshare", "/usr/bin/cat",
    )
    mapped = []
    for kind in ("uid", "gid"):
        result = subprocess.run(
            (*prefix, f"/proc/self/{kind}_map"), capture_output=True, check=False,
            cwd=STATE.parent, timeout=45,
        )
        if result.returncode:
            raise Refusal("cannot inspect rootless Podman ID mapping")
        mapped.append(mapped_host_id(result.stdout.decode("ascii")))
    return mapped[0], mapped[1]


def on_tmpfs() -> bool:
    if not os.path.ismount(STATE):
        return False
    result = subprocess.run(
        ("/usr/bin/findmnt", "-n", "-o", "FSTYPE", "--target", str(STATE)),
        capture_output=True, check=False,
    )
    if result.returncode or result.stdout.strip() != b"tmpfs":
        raise Refusal("gateway state is mounted on an unexpected filesystem")
    return True


def exact_synthetic_profile() -> bool:
    if ENV.is_symlink() or not ENV.is_file() or stat.S_IMODE(ENV.stat().st_mode) != 0o600:
        return False
    try:
        entries = [line.split("=", 1) for line in ENV.read_text().splitlines()]
    except UnicodeError:
        return False
    if any(len(entry) != 2 for entry in entries):
        return False
    values = dict(entries)
    return (
        len(entries) == len(SYNTHETIC_KEYS)
        and set(values) == SYNTHETIC_KEYS
        and values["DEEPSEEK_API_KEY"] == "synthetic-hermes-lab-only"
        and values["GATEWAY_ALLOW_ALL_USERS"] == "false"
    )


def prepare() -> None:
    check_host()
    if on_tmpfs():
        raise Refusal("live tmpfs already exists; inspect status or clear it")
    if not exact_synthetic_profile():
        raise Refusal("underlying guest profile is not the exact synthetic fixture")
    mapped_uid, mapped_gid = gateway_host_ids()
    disable_exact_zram_swap()
    stop_gateway()
    command(
        "/usr/bin/mount", "-t", "tmpfs", "-o", "size=128m,mode=0700,nosuid,nodev",
        "tmpfs", str(STATE),
    )
    os.chown(STATE, mapped_uid, mapped_gid)
    if not on_tmpfs():
        raise Refusal("live profile tmpfs mount was not established")
    print("LIVE_PREPARE=PASS guest state on tmpfs; swap disabled")


def validate_payload(data: bytes) -> None:
    if not data or len(data) > 8192 or not data.endswith(b"\n"):
        raise Refusal("private live environment has an invalid size or shape")
    try:
        lines = data.decode("ascii").splitlines()
        entries = [line.split("=", 1) for line in lines]
    except UnicodeError as exc:
        raise Refusal("private live environment is not ASCII") from exc
    if any(len(entry) != 2 or not entry[1] or any(ord(c) < 33 or ord(c) > 126 for c in entry[1]) for entry in entries):
        raise Refusal("private live environment contains an invalid value")
    if {entry[0] for entry in entries} != KEYS or len(entries) != len(KEYS):
        raise Refusal("private live environment has unexpected keys")
    values = dict(entries)
    if values["DEEPSEEK_API_KEY"] == "synthetic-hermes-lab-only":
        raise Refusal("synthetic key is not valid in live mode")
    if not values["TELEGRAM_ALLOWED_USERS"].isdigit() or values["TELEGRAM_ALLOW_ALL_USERS"] != "false":
        raise Refusal("Telegram private allowlist is invalid")


def inject() -> None:
    check_host()
    if active_swap():
        raise Refusal("guest swap must be disabled before private provisioning")
    if not on_tmpfs() or list(STATE.iterdir()):
        raise Refusal("live tmpfs must be empty before private provisioning")
    data = sys.stdin.buffer.read(8193)
    validate_payload(data)
    fd = os.open(ENV, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        mapped_uid, mapped_gid = gateway_host_ids()
        os.chown(ENV, mapped_uid, mapped_gid)
        os.chmod(ENV, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        ENV.unlink(missing_ok=True)
        raise
    print("LIVE_INJECT=PASS one restricted tmpfs profile; values not displayed")


def clear() -> None:
    check_host()
    stop_gateway()
    if on_tmpfs():
        command("/usr/bin/umount", str(STATE))
    if on_tmpfs():
        raise Refusal("live tmpfs remains mounted")
    print("LIVE_CLEAR=PASS guest tmpfs profile absent")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("prepare", "inject", "clear"):
        print("Usage: live-guest.py prepare|inject|clear", file=sys.stderr)
        return 2
    try:
        {"prepare": prepare, "inject": inject, "clear": clear}[sys.argv[1]]()
    except (Refusal, OSError, subprocess.TimeoutExpired) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
