"""Disposable shutoff-VM UKI injection and first boot; never promotion evidence."""

import argparse
import json
import os
from pathlib import Path
import shutil
import re
import tempfile
import time
import xml.etree.ElementTree as ET

from common import Failure, atomic, canonical, decode, digest, lock, protected_file, report, require, run
from policy import ssh_options

DOMAIN = "lab-hermes-server"
DISK = Path("/var/lib/libvirt/images/hermes-tpm-lab/lab-hermes-server.qcow2")
EFI_PATHS = ("/EFI/fedora/shimx64.efi", "/EFI/BOOT/BOOTX64.EFI")
MARKER = "hermes-disposable-tpm-stage-v1"


def virsh(*args):
    return run(["virsh", "-c", "qemu:///system", *args],
               env={**os.environ, "LC_ALL": "C"}, timeout=30)


def check_domain(expected_uuid):
    require(re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", expected_uuid),
            "invalid-lab-domain-uuid")
    require(virsh("domstate", DOMAIN).strip() == b"shut off", "lab-domain-not-shut-off")
    try:
        root = ET.fromstring(virsh("dumpxml", DOMAIN, "--inactive"))
    except ET.ParseError:
        raise Failure(78, "invalid-lab-domain-xml") from None
    require(root.findtext("name") == DOMAIN and root.findtext("uuid") == expected_uuid,
            "lab-domain-identity-mismatch")
    disks = root.findall("./devices/disk")
    require(len(disks) == 1, "lab-install-media-or-extra-disk-present")
    disk = disks[0]
    require(all(disk.find(name) is not None for name in ("driver", "source", "target")),
            "incomplete-lab-disk-definition")
    require(disk.get("type") == "file" and disk.get("device") == "disk"
            and disk.find("driver").get("type") == "qcow2"
            and disk.find("source").get("file") == str(DISK)
            and disk.find("target").get("dev") == "vda", "unexpected-lab-disk")
    loader = root.find("./os/loader")
    require(loader is not None and loader.get("secure") == "yes"
            and loader.get("readonly") == "yes", "lab-secure-firmware-required")
    tpm = root.find("./devices/tpm/backend")
    require(tpm is not None and tpm.get("type") == "emulator" and tpm.get("version") == "2.0",
            "lab-tpm2-required")
    require(root.find("./os/kernel") is None and root.find("./os/initrd") is None
            and root.find("./os/cmdline") is None, "lab-direct-kernel-boot-forbidden")
    protected_file(DISK)
    info = decode(run(["qemu-img", "info", "--output=json", str(DISK)]))
    require(info.get("format") == "qcow2" and not info.get("backing-filename")
            and not info.get("snapshots"), "lab-disk-overlay-or-snapshot")
    details = virsh("dominfo", DOMAIN).decode().splitlines()
    fields = dict(line.split(":", 1) for line in details if ":" in line)
    require(fields.get("Managed save", "").strip() == "no", "lab-managed-save-present")
    require(fields.get("Autostart", "").strip() == "disable", "lab-autostart-must-be-disabled")


def guestfish(commands, writable=False):
    # A separate appliance accesses only the fixed lab image, never host block devices.
    # All arguments are quoted for guestfish's command parser; no shell commands are used.
    if writable:
        require(virsh("domstate", DOMAIN).strip() == b"shut off", "lab-domain-not-shut-off")
    allowed = {"cat", "filesize", "download", "is-file", "cp", "sync", "upload", "mv"}
    require(all(command and command[0] in allowed for command in commands), "invalid-guestfish-command")
    script = "\n".join(command[0] + " " + " ".join(json.dumps(str(arg)) for arg in command[1:])
                       for command in commands) + "\n"
    return run(["guestfish", "--rw" if writable else "--ro", "--format=qcow2", "-a", str(DISK),
                "-m", "/dev/sda1"], data=script.encode(), timeout=300)


def bounded_download(source, destination, limit=400 * 1024**2):
    # The domain is offline under exclusive operator control. Check the appliance
    # file size before copying, not only after consuming workstation storage.
    size = guestfish([("filesize", source)]).strip()
    require(size.isdigit() and 0 < int(size) <= limit, "lab-export-too-large")
    guestfish([("download", source, destination)])
    require(Path(destination).stat().st_size == int(size), "lab-export-size-changed")


def bounded_cat(source, limit=1024):
    size = guestfish([("filesize", source)]).strip()
    require(size.isdigit() and 0 < int(size) <= limit, "lab-export-too-large")
    raw = guestfish([("cat", source)])
    length = int(size)
    # guestfish's interactive printer appends one newline to cat output.
    # Preserve file bytes, including their own trailing newline, exactly.
    require(len(raw) == length or len(raw) == length + 1 and raw.endswith(b"\n"),
            "lab-export-size-changed")
    return raw[:length]


def verify_uki(uki, certificate, pcr_public_key):
    run(["sbverify", "--cert", str(certificate), str(uki)])
    sections = decode(run(["ukify", "--json=short", "inspect", str(uki)]))
    require(all(name in sections for name in (".linux", ".initrd", ".osrel", ".cmdline", ".pcrsig", ".pcrpkey")),
            "incomplete-installed-uki")
    require(sections[".pcrpkey"].get("sha256") == digest(pcr_public_key), "installed-pcr-key-mismatch")
    command_line = sections[".cmdline"].get("text", "").strip()
    require(command_line and not any(c in command_line for c in "\n\r\x00"), "invalid-installed-command-line")
    options = command_line.split()
    require("root=/dev/mapper/vg_root-root" in options
            and sum(option.startswith("root=") for option in options) == 1
            and sum(option.startswith("rd.luks.uuid=") for option in options) == 1
            and "rd.luks.options=tpm2-device=auto" in options,
            "installed-encrypted-root-policy-required")
    require(not any(option.startswith(("inst.", "init=", "rdinit=", "rd.break", "rd.luks.key=",
                                       "rd.luks.options=")) and option != "rd.luks.options=tpm2-device=auto"
                    or option in ("selinux=0", "enforcing=0", "rd.luks=0") for option in options),
            "unsafe-installed-command-line")
    return command_line


def inject(expected_uuid, uki, certificate, pcr_public_key, directory):
    frozen = []
    for index, source in enumerate((uki, certificate, pcr_public_key)):
        source = protected_file(source)
        require(source.stat().st_size <= 400 * 1024**2, "lab-input-too-large")
        target = directory / str(index)
        shutil.copyfile(source, target)
        target.chmod(0o600)
        frozen.append(target)
    uki, certificate, pcr_public_key = frozen
    command_line = verify_uki(uki, certificate, pcr_public_key)
    check_domain(expected_uuid)
    require(bounded_cat("/hermes-tpm-stage").strip() == MARKER.encode(),
            "lab-tpm-stage-marker-missing")
    # Bind the supplied public key to the one actually installed during TPM enrollment.
    enrolled_key = directory / "enrolled.pub"
    bounded_download("/hermes-pcr-public-key.pem", enrolled_key, 65536)
    require(digest(enrolled_key) == digest(pcr_public_key), "lab-enrolled-pcr-key-mismatch")
    for index, destination in enumerate(EFI_PATHS):
        current = directory / ("current-" + str(index))
        bounded_download(destination, current)
        if digest(current) == digest(uki):
            continue
        backup = destination + ".hermes-original"
        exists = guestfish([("is-file", backup)]).strip()
        require(exists in (b"true", b"false"), "invalid-efi-backup-state")
        check_domain(expected_uuid)
        if exists == b"false":
            guestfish([("cp", destination, backup), ("sync",)], writable=True)
        restored = directory / ("backup-" + str(index))
        bounded_download(backup, restored)
        # Only initial injection or a same-input interrupted retry is supported.
        # Never proceed past a failed earlier backup or replace a different release.
        require(digest(restored) == digest(current), "efi-backup-copy-mismatch")
        # Upload to a temporary sibling and verify it before replacing the boot path.
        pending = destination + ".hermes-pending"
        guestfish([("upload", uki, pending), ("sync",)], writable=True)
        readback = directory / ("pending-" + str(index))
        bounded_download(pending, readback)
        require(digest(readback) == digest(uki), "efi-upload-copy-mismatch")
        check_domain(expected_uuid)
        guestfish([("mv", pending, destination), ("sync",)], writable=True)
    for index, destination in enumerate(EFI_PATHS):
        readback = directory / ("final-" + str(index))
        bounded_download(destination, readback)
        require(digest(readback) == digest(uki), "efi-final-copy-mismatch")
    check_domain(expected_uuid)
    return command_line, digest(uki)


def first_boot(expected_uuid, command_line, identity, known_hosts, timeout):
    require(1 <= timeout <= 900, "invalid-lab-boot-timeout")
    for source in (identity, known_hosts):
        protected_file(source)
    require(not Path(identity).stat().st_mode & 0o077, "ssh-identity-not-private")
    check_domain(expected_uuid)
    virsh("start", DOMAIN)
    config = {"identity_file": str(identity), "known_hosts": str(known_hosts), "target": "lab@172.16.99.12"}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            output = run(ssh_options(config) + ["cat /proc/cmdline"],
                         timeout=max(1, min(20, deadline - time.monotonic())))
        except Failure:
            time.sleep(min(2, max(0, deadline - time.monotonic())))
            continue
        require(output.decode().strip() == command_line, "booted-command-line-mismatch")
        output = run(ssh_options(config) + ["mokutil --sb-state"], timeout=20)
        require(output.strip() == b"SecureBoot enabled", "boot-secure-boot-not-enabled")
        return {"first_boot_observed": True, "boot_verified": False, "certification": "pending"}
    raise Failure(69, "lab-first-boot-timeout-use-offline-recovery")


def main():
    parser = argparse.ArgumentParser(description="Inject a signed UKI into the fixed disposable Hermes VM")
    for name in ("domain-uuid", "uki", "certificate", "pcr-public-key", "state-dir"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--start", action="store_true")
    parser.add_argument("--identity-file")
    parser.add_argument("--known-hosts")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    directory = Path(args.state_dir)
    require(directory.is_absolute() and not directory.is_symlink() and directory.is_dir()
            and directory.stat().st_uid == os.getuid() and not directory.stat().st_mode & 0o077,
            "private-lab-state-directory-required")
    require(not args.start or (args.identity_file and args.known_hosts), "pinned-lab-ssh-required")
    require(1 <= args.timeout <= 900, "invalid-lab-boot-timeout")
    if args.start:
        for source in (args.identity_file, args.known_hosts):
            protected_file(source)
        require(not Path(args.identity_file).stat().st_mode & 0o077, "ssh-identity-not-private")
    # Serialize all instances independently of caller-selected evidence directories.
    with lock(DISK.parent / ".hermes-lab-boot.lock"):
        atomic(directory / "lab-boot.json", canonical({"ok": False, "stage": "injection-started",
                                                       "domain_uuid": args.domain_uuid, "boot_verified": False}))
        with tempfile.TemporaryDirectory(prefix="uki-injection-", dir=directory) as temporary:
            command_line, sha = inject(args.domain_uuid, args.uki, args.certificate, args.pcr_public_key, Path(temporary))
        result = {"ok": True, "stage": "lab-uki-injected", "domain_uuid": args.domain_uuid,
                  "uki_sha256": sha, "boot_verified": False}
        atomic(directory / "lab-boot.json", canonical(result))
        if args.start:
            result.update(first_boot(args.domain_uuid, command_line, args.identity_file, args.known_hosts, args.timeout))
            result["stage"] = "lab-first-boot-observed"
        atomic(directory / "lab-boot.json", canonical(result))
        return result


if __name__ == "__main__":
    report(main)
