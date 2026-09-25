#!/usr/bin/env python3
"""Recover the retained DeepSeek VM's forgotten administrator password.

``check`` is offline. ``reset-password`` requires host root and a private
terminal. Only a locally generated yescrypt hash reaches QEMU guest agent.
The raw password is never an argument, environment variable or file.
"""

import argparse
import base64
import getpass
import hashlib
import json
import os
import subprocess
import sys
import types
from pathlib import Path
from typing import NoReturn

import libvirt
import libvirt_qemu

GRANT_SOURCE = Path(__file__).with_name("deepseek-test-grant.py")
GRANT_SOURCE_SHA256 = "e9fffae62535e3714c4d406f3359c41218d9e6d9411e98bc84ad8c82e638fd39"
URI = "qemu:///system"
USER = "aicowork"


def stop(message: str) -> NoReturn:
    raise RuntimeError(message)


def grant_module():
    if GRANT_SOURCE.is_symlink() or not GRANT_SOURCE.is_file():
        stop("reviewed grant source missing")
    source = GRANT_SOURCE.read_bytes()
    if hashlib.sha256(source).hexdigest() != GRANT_SOURCE_SHA256:
        stop("reviewed grant source changed")
    module = types.ModuleType("deepseek_test_grant")
    module.__file__ = str(GRANT_SOURCE)
    exec(compile(source, str(GRANT_SOURCE), "exec"), module.__dict__)
    return module


def bound_guest(grant) -> None:
    if grant.bound_vm() != "running":
        stop("approved VM must be running")
    grant.bound_network()
    grant.guest_identity()
    info = grant.agent({"execute": "guest-info"})
    commands = info.get("supported_commands")
    if not isinstance(commands, list) or not any(
        isinstance(command, dict)
        and command.get("name") == "guest-set-user-password"
        and command.get("enabled") is True
        for command in commands
    ):
        stop("guest-set-user-password is unavailable")


def private_hash() -> str:
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        stop("private interactive terminal required")
    password = getpass.getpass("New aicowork password for the DeepSeek VM: ")
    confirm = getpass.getpass("Retype new DeepSeek VM password: ")
    if password != confirm:
        stop("passwords did not match; no change made")
    if not 16 <= len(password) <= 256 or any(char in password for char in "\x00\r\n"):
        stop("choose 16 to 256 characters without control characters; no change made")
    try:
        hashed = subprocess.run(
            ["/usr/bin/mkpasswd", "-m", "yescrypt", "-s"],
            input=password + "\n",
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        stop("local password hashing failed; no change made")
    del password, confirm
    if not hashed.startswith("$y$") or "\n" in hashed:
        stop("local password hash invalid; no change made")
    return hashed


def apply_hash(grant, hashed: str) -> None:
    bound_guest(grant)
    payload = {
        "execute": "guest-set-user-password",
        "arguments": {
            "username": USER,
            "password": base64.b64encode(hashed.encode()).decode(),
            "crypted": True,
        },
    }
    conn = libvirt.open(URI)
    if conn is None:
        stop("libvirt connection failed; no change made")
    try:
        domain = conn.lookupByName(grant.DOMAIN)
        if domain.UUIDString() != grant.UUID:
            stop("VM UUID changed; no change made")
        try:
            response = json.loads(libvirt_qemu.qemuAgentCommand(domain, json.dumps(payload), 15, 0))
        except libvirt.libvirtError:
            stop("guest agent password change failed; verify old state")
        if "error" in response or "return" not in response:
            stop("guest agent rejected password change; verify old state")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "reset-password"))
    args = parser.parse_args()
    grant = grant_module()
    if args.action == "check":
        grant.check()
        print("RECOVERY_CHECK=PASS fixed_vm=" + grant.DOMAIN)
        return
    if os.geteuid() != 0:
        stop("host root required; use a private terminal sudo prompt")
    bound_guest(grant)
    hashed = private_hash()
    apply_hash(grant, hashed)
    print("VM_PASSWORD_CHANGE_ACCEPTED; verify with fresh guest sudo authentication")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
