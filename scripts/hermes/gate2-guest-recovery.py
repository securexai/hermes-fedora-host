#!/usr/bin/env python3
"""Bounded QEMU guest-agent recovery for the retained Hermes Gate 2 VM.

Run as host root after reviewing this file. A private reset prompt is available;
only a yescrypt hash reaches the guest agent, with no password in argv or files.
"""

import argparse
import base64
import getpass
import json
import os
import subprocess
import sys
import time

import libvirt
import libvirt_qemu

DOMAIN = "lab-hermes-manual-r1"
UUID = "d39e5ca7-aded-457c-b01d-a1817a4725a8"
MAC = "52:54:00:94:58:36"
MACHINE_SHA256 = "5026447dd72b4e67b089b93692dc6e10a0fe5c7996765f6cdbf6a1d2752d6588"
URI = "qemu:///system"
VIRSH = ("/usr/bin/virsh", "-c", URI)

INSPECT = r"""
set -euo pipefail
printf 'guest_user=%s\n' "$(id -un)"
printf 'guest_hostname=%s\n' "$(cat /etc/hostname)"
printf 'guest_machine_sha256=%s\n' "$(sha256sum /etc/machine-id | awk '{print $1}')"
for path in /etc/sudoers.d/90-hermes-manual-lab \
            /etc/sudoers.d/90-hermes-gate2-test-guest \
            /etc/sudoers.d/90-hermes-gate2-password-once \
            /usr/local/libexec/hermes-gate2-test/gate2-test-guest.sh \
            /usr/local/libexec/hermes-gate2-test/gate2-reset-password-once.sh; do
  if [ -e "$path" ]; then
    stat -c 'file=%n owner=%U mode=%a type=%F' "$path"
    case "$path" in /etc/sudoers.d/*) visudo -cf "$path" >/dev/null && echo "syntax=PASS path=$path" ;; esac
  else
    printf 'absent=%s\n' "$path"
  fi
done
for path in /etc/sudoers.d/90-hermes-manual-lab /etc/sudoers.d/90-hermes-gate2-test-guest; do
  if [ -f "$path" ]; then
    printf 'rule=%s\n' "$path"
    sed -n '/^[[:space:]]*[^#[:space:]]/p' "$path"
  fi
done
"""

def virsh(*args: str) -> str:
    result = subprocess.run(
        [*VIRSH, *args], check=True, capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip()


def agent(payload: dict) -> dict:
    response = json.loads(virsh("qemu-agent-command", DOMAIN, json.dumps(payload)))
    if "error" in response:
        raise RuntimeError(response["error"])
    return response["return"]


def guest_script(script: str) -> str:
    payload = {
        "execute": "guest-exec",
        "arguments": {
            "path": "/usr/bin/bash",
            "arg": ["-s"],
            "input-data": base64.b64encode(script.encode()).decode(),
            "capture-output": True,
        },
    }
    pid = agent(payload)["pid"]
    for _ in range(100):
        status = agent({"execute": "guest-exec-status", "arguments": {"pid": pid}})
        if status["exited"]:
            out = base64.b64decode(status.get("out-data", "")).decode(errors="replace")
            err = base64.b64decode(status.get("err-data", "")).decode(errors="replace")
            if err:
                print(err[:4000], file=sys.stderr, end="")
            if status.get("exitcode") != 0:
                raise RuntimeError(f"guest command failed: exit={status.get('exitcode')} output={out[:2000]}")
            return out
        time.sleep(0.1)
    raise RuntimeError("guest command did not finish within 10 seconds")


def reset_password() -> None:
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        raise RuntimeError("private interactive terminal required")
    password = getpass.getpass("New VM password for aicowork: ")
    confirm = getpass.getpass("Retype new VM password: ")
    if password != confirm:
        raise RuntimeError("passwords did not match; no change made")
    if not 16 <= len(password) <= 256 or "\x00" in password:
        raise RuntimeError("choose 16 to 256 characters; no change made")
    try:
        hashed = subprocess.run(
            ["/usr/bin/mkpasswd", "-m", "yescrypt", "-s"],
            input=password + "\n", capture_output=True, text=True, check=True,
            timeout=30,
        ).stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("local password hashing failed; no change made") from exc
    del password, confirm
    if not hashed.startswith("$y$") or "\n" in hashed:
        raise RuntimeError("local password hash invalid; no change made")
    payload = {
        "execute": "guest-set-user-password",
        "arguments": {
            "username": "aicowork",
            "password": base64.b64encode(hashed.encode()).decode(),
            "crypted": True,
        },
    }
    conn = libvirt.open(URI)
    if conn is None:
        raise RuntimeError("libvirt connection failed; no change made")
    try:
        domain = conn.lookupByName(DOMAIN)
        if domain.UUIDString() != UUID:
            raise RuntimeError("VM UUID changed; no change made")
        try:
            response = json.loads(libvirt_qemu.qemuAgentCommand(domain, json.dumps(payload), 15, 0))
        except libvirt.libvirtError as exc:
            raise RuntimeError("guest agent password change failed; verify old state") from exc
        if "error" in response or "return" not in response:
            raise RuntimeError("guest agent rejected password change; verify old state")
    finally:
        conn.close()
    print("VM_PASSWORD_CHANGE_ACCEPTED; verify with fresh sudo authentication")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inspect", "reset-password"))
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("run as host root with a private sudo prompt")
    if virsh("domuuid", DOMAIN) != UUID:
        raise RuntimeError("VM UUID mismatch")
    interfaces = virsh("domiflist", DOMAIN)
    if not any(
        len(parts := line.split()) >= 5
        and parts[1] == "network"
        and parts[2] == "fvh-nat"
        and parts[4] == MAC
        for line in interfaces.splitlines()
    ):
        raise RuntimeError("VM MAC or network mismatch")
    if virsh("domstate", DOMAIN) != "running":
        raise RuntimeError("VM is not running")
    guest = guest_script(INSPECT)
    if "guest_user=root" not in guest or "guest_hostname=lab-hermes-manual-r1" not in guest:
        observed = ", ".join(
            line for line in guest.splitlines() if line.startswith(("guest_user=", "guest_hostname="))
        )
        raise RuntimeError(f"guest identity mismatch ({observed})")
    if f"guest_machine_sha256={MACHINE_SHA256}" not in guest:
        raise RuntimeError("guest machine-id mismatch")
    if args.action == "inspect":
        print(guest, end="")
    else:
        reset_password()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
