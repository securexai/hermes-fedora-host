#!/usr/bin/env python3
"""Disposable Secure Boot + TPM2 qualification VMs installed unattended from built media.

The VM boots the `productionctl.py media --serial-console` ISO from its virtual cdrom
through the firmware's signed shim/GRUB chain, so installer and installed PCR7 match.
No secret is entered: the installer generates and escrows them.
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/hermes"))
from production import kickstart  # noqa: E402
from production.primitives import (  # noqa: E402
    Refused,
    atomic,
    canonical,
    read_json,
    regular,
    require,
    run,
    sha,
)

NAME = "hermes-production-qualification"
BASE = ROOT / ".toolbox/hermes-production-fixture"
FIXTURES = {
    "qualification": (NAME, BASE, 22224),
    "restore": (
        "hermes-production-restore",
        ROOT / ".toolbox/hermes-production-restore",
        22225,
    ),
    # Disposable pipeline VM (vm/hermes-production-qualify.py); never the older guests.
    "qualify": ("hermes-production-qualify", ROOT / ".toolbox/hermes-qualify/vm", 22227),
}
DISK_ID = "/dev/disk/by-id/virtio-HERMES_PROD_TEST"
MEMORY_MIB = 9216
MIN_FREE_BYTES = 20 * 1024**3
SECURE_BOOT = (
    "uefi,firmware.feature0.name=secure-boot,firmware.feature0.enabled=yes,"
    "firmware.feature1.name=enrolled-keys,firmware.feature1.enabled=yes"
)


def session_environment():
    """Keep host libvirt inventory and creation in the user's existing session."""
    value = os.environ.get("XDG_RUNTIME_DIR")
    require(bool(value) and Path(value).is_absolute(), "session-runtime-required")
    runtime = Path(value)
    try:
        info = runtime.lstat()
    except OSError as exc:
        raise Refused("session-runtime-unavailable") from exc
    require(
        stat.S_ISDIR(info.st_mode)
        and info.st_uid == os.getuid()
        and stat.S_IMODE(info.st_mode) == 0o700,
        "unsafe-session-runtime",
    )
    environment = {"HOME": str(Path.home()), "XDG_RUNTIME_DIR": str(runtime)}
    for key in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME"):
        value = os.environ.get(key)
        if value:
            require(Path(value).is_absolute(), "invalid-session-directory")
            environment[key] = value
    return environment


def available_port(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", port))
    except OSError as exc:
        raise Refused("fixture-ssh-port-unavailable") from exc


def console(role):
    """Hand the real terminal to virsh; never proxy or record input."""
    require(role in FIXTURES, "unknown-fixture-role")
    require(all(os.isatty(fd) for fd in (0, 1, 2)), "private-interactive-terminal-required")
    name, base, _ = FIXTURES[role]
    ownership = read_json(base / "ownership.json")
    require(
        ownership.get("name") == name and ownership.get("role") == role,
        "fixture-ownership-mismatch",
    )
    environment = session_environment() | {
        "PATH": os.defpath,
        "LANG": "C.UTF-8",
        "TERM": "xterm-256color",
    }
    print(
        "Console: " + name + "\n"
        "Installation and commissioning are unattended; no input is required.\n"
        "The login banner shows the SSH host-key fingerprint and console code.\n"
        "Break-glass recovery uses the escrowed recovery key, never a typed guess.\n"
        "Ctrl+Q detaches. This command does not start or reinstall the VM.",
        flush=True,
    )
    os.execvpe(
        "virsh",
        ["virsh", "-c", "qemu:///session", "--escape", "^q", "console", name, "--safe"],
        environment,
    )


def create(media, settings, *, apply=False, role="qualification"):
    require(role in FIXTURES, "unknown-fixture-role")
    name, base, port = FIXTURES[role]
    media = regular(media)
    require(media.suffix == ".iso", "built-installation-media-required")
    settings = kickstart.validate(read_json(settings))
    require(settings["disk_id"] == DISK_ID, "fixture-disk-id-mismatch")
    require(settings["kind"] == "fixture", "fixture-settings-required")
    require(
        not base.exists() and not base.is_symlink(), "fixture-directory-exists-preserve-evidence"
    )
    environment = session_environment()
    domains = (
        run(["virsh", "-c", "qemu:///session", "list", "--all", "--name"], env=environment)
        .stdout.decode()
        .splitlines()
    )
    require(name not in domains, "fixture-name-conflict")
    available_port(port)
    require(shutil.disk_usage(base.parent).free >= MIN_FREE_BYTES, "fixture-host-space-low")
    definitions = run(["virt-install", "--osinfo", "list"], env=environment).stdout.decode().split()
    variant = next((item for item in ("fedora44", "fedora43") if item in definitions), None)
    require(variant is not None, "fedora-guest-definition-unavailable")
    result = {
        "status": "PREVIEW",
        "name": name,
        "role": role,
        "directory": str(base),
        "ssh": {"host": "127.0.0.1", "port": port},
        "guest_definition": variant,
        "media_sha256": sha(media),
        "boot": "UEFI Secure Boot with enrolled keys, TPM2 emulator, USB disk via shim",
        "memory_mb": MEMORY_MIB,
        "vcpus": 2,
        "disk_virtual_mib": settings["disk_min_mib"] + 1024,
        "disk_to_erase": settings["disk_id"],
        "serial_log": str(base / "serial.log"),
        "minimum_host_free_bytes": MIN_FREE_BYTES,
        "installation": "UNATTENDED: installer generates and escrows every secret",
        "console_command": f"python3 -B vm/hermes-production-fixture.py --role {role} --console",
    }
    if not apply:
        return result
    base.mkdir(mode=0o700)
    # A canary disk is attached writable: any accidental broad clearing must be observable.
    canary = base / "unrelated.raw"
    with canary.open("xb") as stream:
        stream.write(os.urandom(1024 * 1024))
        stream.truncate(64 * 1024 * 1024)
    result["unrelated_sha256"] = sha(canary)
    disk = base / "system.qcow2"
    run(
        ["qemu-img", "create", "-f", "qcow2", str(disk), str(settings["disk_min_mib"] + 1024) + "M"]
    )
    atomic(base / "ownership.json", canonical(result))
    run(
        [
            "virt-install",
            "--connect",
            "qemu:///session",
            "--name",
            name,
            "--memory",
            str(MEMORY_MIB),
            "--vcpus",
            "2",
            "--os-variant",
            variant,
            "--machine",
            "q35",
            "--boot",
            SECURE_BOOT,
            "--tpm",
            "backend.type=emulator,backend.version=2.0,model=tpm-crb",
            "--disk",
            f"path={disk},format=qcow2,bus=virtio,serial=HERMES_PROD_TEST",
            "--disk",
            f"path={canary},format=raw,bus=virtio,serial=HERMES_UNRELATED",
            "--network",
            "user,model=virtio,backend.type=passt,portForward0.proto=tcp,"
            f"portForward0.address=127.0.0.1,portForward0.range0.start={port},"
            "portForward0.range0.to=22",
            # Boot the media as a read-only USB disk, exactly like the production stick:
            # the firmware loads shim from the image's GPT EFI System Partition. The
            # domain powers off on the installer's reboot so the stick can be removed.
            "--disk",
            f"path={media},format=raw,device=disk,bus=usb,readonly=on",
            "--import",
            "--events",
            "on_reboot=destroy",
            "--serial",
            f"pty,log.file={base / 'serial.log'},log.append=on",
            "--graphics",
            "none",
            "--noautoconsole",
            "--wait",
            "0",
        ],
        timeout=180,
        env=environment,
    )
    result["status"] = "CREATED_UNATTENDED_INSTALLATION_RUNNING"
    atomic(base / "ownership.json", canonical(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media", help="ISO built by productionctl.py media --serial-console")
    parser.add_argument("--settings")
    parser.add_argument("--role", choices=sorted(FIXTURES), default="qualification")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true")
    action.add_argument("--console", action="store_true", help="Attach from a terminal")
    args = parser.parse_args()
    if args.console:
        if any((args.media, args.settings)):
            parser.error("--console cannot be combined with installation inputs")
    elif not all((args.media, args.settings)):
        parser.error("creation/preview requires --media and --settings")
    try:
        if args.console:
            console(args.role)
            return 0
        print(
            canonical(create(args.media, args.settings, apply=args.apply, role=args.role)).decode(),
            end="",
        )
        return 0
    except Exception as exc:
        print(
            "STOP: " + (str(exc) if isinstance(exc, Refused) else type(exc).__name__),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
