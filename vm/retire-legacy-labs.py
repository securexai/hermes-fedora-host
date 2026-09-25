#!/usr/bin/env python3
"""Retire only the two approved, identity-pinned obsolete Hermes system VMs.

Run once through a private host authorization channel. Every resource is checked
before deletion. No guest-agent call is needed: destroying the owned disk also
destroys the inaccessible guest test grant within it.
"""

from __future__ import annotations

import hashlib
import os
import pathlib
import pwd
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

TARGETS = {
    "lab-hermes-deepseek-e2e-r1": {
        "uuid": "4349a2bc-67b6-42b7-a6ef-5aeee5ee4009",
        "mac": "52:54:00:83:bf:4b",
        "disk": pathlib.Path("/var/lib/libvirt/images/lab-hermes-deepseek-e2e-r1/disk.qcow2"),
        "media": (),
        "nvram": pathlib.Path("/var/lib/libvirt/qemu/nvram/lab-hermes-deepseek-e2e-r1_VARS.qcow2"),
    },
    "lab-hermes-manual-r1": {
        "uuid": "d39e5ca7-aded-457c-b01d-a1817a4725a8",
        "mac": "52:54:00:94:58:36",
        "disk": pathlib.Path("/var/lib/libvirt/images/lab-hermes-manual-r1/disk.qcow2"),
        "media": (
            pathlib.Path("/var/lib/libvirt/boot/lab-hermes-manual-r1/Fedora-Server-dvd-x86_64-44-1.7.iso"),
            pathlib.Path("/var/lib/libvirt/boot/lab-hermes-manual-r1/ks.iso"),
        ),
        "nvram": pathlib.Path("/var/lib/libvirt/qemu/nvram/lab-hermes-manual-r1_VARS.qcow2"),
    },
}
HOST_RULE = pathlib.Path("/etc/sudoers.d/90-hermes-deepseek-test-host")
HOST_RULE_SHA256 = "83dea424b2e92298c46700fde511e712212177b5879c032d79c194843243b92d"
HOST_BASE = pathlib.Path("/var/usrlocal/libexec/hermes-deepseek-test")
STATE = pathlib.Path("/var/home/aicloudopspecial/.local/state/hermes-deepseek-test")


class Refusal(RuntimeError):
    pass


def command(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, capture_output=True, text=True, timeout=45, check=False)
    if check and result.returncode:
        raise Refusal(f"{pathlib.Path(args[0]).name} failed (exit {result.returncode})")
    return result


def virsh(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return command("/usr/bin/virsh", "-c", "qemu:///system", *args, check=check)


def exact_file(path: pathlib.Path, owner: int, mode: int | None = None) -> None:
    if path.is_symlink() or not path.is_file():
        raise Refusal(f"missing or unsafe exact file: {path}")
    info = path.stat()
    if info.st_uid != owner or (mode is not None and stat.S_IMODE(info.st_mode) != mode):
        raise Refusal(f"unexpected owner or mode: {path}")


def exact_directory(path: pathlib.Path, owner: int, children: set[str]) -> None:
    if path.is_symlink() or not path.is_dir() or path.stat().st_uid != owner:
        raise Refusal(f"missing or unsafe exact directory: {path}")
    if {item.name for item in path.iterdir()} != children:
        raise Refusal(f"unexpected exact directory contents: {path}")
    if any(item.is_symlink() for item in path.iterdir()):
        raise Refusal(f"symlink in exact directory: {path}")


def domains() -> dict[str, ET.Element]:
    found: dict[str, ET.Element] = {}
    target_paths = {
        str(path)
        for expected in TARGETS.values()
        for path in (expected["disk"], *expected["media"])
    }
    for other in virsh("list", "--all", "--name").stdout.splitlines():
        if not other or other in TARGETS:
            continue
        root = ET.fromstring(virsh("dumpxml", other).stdout)
        attached = {
            item.get("file") for item in root.findall("./devices/disk/source") if item.get("file")
        }
        if attached & target_paths:
            raise Refusal(f"another domain shares legacy lab storage: {other}")
    for name, expected in TARGETS.items():
        xml = virsh("dumpxml", name).stdout
        root = ET.fromstring(xml)
        if root.findtext("uuid") != expected["uuid"] or root.findtext("name") != name:
            raise Refusal(f"unexpected domain identity: {name}")
        macs = {item.get("address") for item in root.findall("./devices/interface/mac")}
        if macs != {expected["mac"]}:
            raise Refusal(f"unexpected domain MAC: {name}")
        nets = {item.get("network") for item in root.findall("./devices/interface/source")}
        if nets != {"fvh-nat"}:
            raise Refusal(f"unexpected domain network: {name}")
        disks = {item.get("file") for item in root.findall("./devices/disk/source") if item.get("file")}
        allowed = {str(expected["disk"]), *(str(p) for p in expected["media"])}
        if disks != allowed:
            raise Refusal(f"unexpected domain storage attachments: {name}")
        if root.findtext("./os/nvram") != str(expected["nvram"]):
            raise Refusal(f"unexpected domain NVRAM: {name}")
        if root.find("./devices/tpm[@model='tpm-crb']/backend[@type='emulator']") is None:
            raise Refusal(f"unexpected domain TPM: {name}")
        if virsh("domstate", name).stdout.strip() != "shut off":
            raise Refusal(f"domain must be shut off before retirement: {name}")
        if virsh("snapshot-list", name, "--name").stdout.strip():
            raise Refusal(f"domain has snapshots: {name}")
        found[name] = root
    return found


def preflight() -> None:
    if os.geteuid() != 0:
        raise Refusal("private host root authorization is required")
    account = pwd.getpwnam("aicloudopspecial")
    qemu = pwd.getpwnam("qemu")
    domains()
    for name, expected in TARGETS.items():
        disk = expected["disk"]
        exact_directory(disk.parent, 0, {disk.name})
        exact_file(disk, 0)
        if expected["media"]:
            exact_directory(expected["media"][0].parent, 0, {p.name for p in expected["media"]})
            for media in expected["media"]:
                exact_file(media, qemu.pw_uid)
        exact_file(expected["nvram"], qemu.pw_uid, 0o600)
    exact_file(HOST_RULE, 0, 0o440)
    if hashlib.sha256(HOST_RULE.read_bytes()).hexdigest() != HOST_RULE_SHA256:
        raise Refusal("DeepSeek host sudoers rule differs from the reviewed grant")
    command("/usr/sbin/visudo", "-cf", str(HOST_RULE))
    exact_directory(HOST_BASE, 0, {"access.py", "boot-inspect.py", "bundle.tar"})
    for item in HOST_BASE.iterdir():
        exact_file(item, 0, 0o644)
    exact_directory(STATE, account.pw_uid, {"id_ed25519", "id_ed25519.pub", "known_hosts"})
    exact_file(STATE / "id_ed25519", account.pw_uid, 0o600)
    exact_file(STATE / "known_hosts", account.pw_uid, 0o600)
    print("PREFLIGHT=PASS two shut-off UUID-pinned domains, exact disks/media/NVRAM/TPM and DeepSeek grant")


def already_absent() -> bool:
    if os.geteuid() != 0:
        raise Refusal("private host root authorization is required")
    listed = set(virsh("list", "--all", "--name").stdout.splitlines())
    paths = [HOST_RULE, HOST_BASE, STATE]
    for expected in TARGETS.values():
        paths.extend((expected["disk"], expected["disk"].parent, expected["nvram"]))
        paths.extend(expected["media"])
        if expected["media"]:
            paths.append(expected["media"][0].parent)
    return not (listed & TARGETS.keys()) and all(not path.exists() and not path.is_symlink() for path in paths)


def apply() -> None:
    if already_absent():
        print("RETIRE=PASS exact obsolete resources already absent")
        return
    preflight()
    # Recheck after preflight, then change only the named domains.
    for name in TARGETS:
        virsh("undefine", name, "--nvram", "--tpm")
    for expected in TARGETS.values():
        disk = expected["disk"]
        disk.unlink()
        disk.parent.rmdir()
        for media in expected["media"]:
            media.unlink()
        if expected["media"]:
            expected["media"][0].parent.rmdir()
    HOST_RULE.unlink()
    for item in HOST_BASE.iterdir():
        item.unlink()
    HOST_BASE.rmdir()
    for item in STATE.iterdir():
        item.unlink()
    STATE.rmdir()
    for name in TARGETS:
        if virsh("domuuid", name, check=False).returncode == 0:
            raise Refusal(f"domain still defined after cleanup: {name}")
    if any(expected["nvram"].exists() for expected in TARGETS.values()):
        raise Refusal("an obsolete VM NVRAM file remains after cleanup")
    if HOST_RULE.exists() or HOST_BASE.exists() or STATE.exists():
        raise Refusal("temporary DeepSeek host grant remains after cleanup")
    print("RETIRE=PASS both exact obsolete domains, owned files, and temporary host grant absent")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("Usage: retire-legacy-labs.py --check|--apply", file=sys.stderr)
        return 2
    try:
        if sys.argv[1] == "--check":
            if already_absent():
                print("PREFLIGHT=PASS exact obsolete resources already absent")
            else:
                preflight()
        else:
            apply()
    except (Refusal, OSError, ET.ParseError, subprocess.TimeoutExpired) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
