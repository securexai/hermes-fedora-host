"""Verified Fedora Server 44 media plus the hash-pinned Hermes payload -> one unattended ISO.

The ISO still boots through the signed shim/GRUB chain, so the installer measures the
same Secure Boot PCR7 state as the installed system (required for install-time TPM
enrollment). mkksiso only adds the Kickstart, the public payload and boot arguments.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from . import kickstart
from .primitives import atomic, canonical, decode, digest, read_json, regular, require, run, sha

SIGNER = "36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6"
FEDORA_KEY = "distribution-gpg-keys/fedora/RPM-GPG-KEY-fedora-44-primary"
KEY_ROOTS = (Path("/usr/share"), Path("/run/host/usr/share"))
INSTALLER_ARGS = "inst.nosave=all_ks inst.text"
# mkksiso runs in a throwaway local image: no host package layering, no Toolbox change.
TOOLS_IMAGE = "localhost/hermes-media-tools:fedora-44"
TOOLS_BASE = "localhost/dev-base:fedora-44"
TOOLS_PACKAGES = ("lorax", "xorriso", "mtools", "isomd5sum")
SERIAL_ARGS = "console=ttyS0,115200n8"


def verify_iso(iso, checksum):
    """Fedora-signed CHECKSUM file and the exact Server DVD hash."""
    iso, checksum = regular(iso), regular(checksum)
    require(
        re.fullmatch(r"Fedora-Server-dvd-x86_64-44-[0-9.]+\.iso", iso.name) is not None,
        "fedora44-server-media-required",
    )
    key = next((root / FEDORA_KEY for root in KEY_ROOTS if (root / FEDORA_KEY).is_file()), None)
    require(key is not None, "fedora44-public-signing-key-unavailable")
    with tempfile.TemporaryDirectory(prefix="hermes-media-") as temporary:
        ring = Path(temporary) / "fedora.gpg"
        run(
            ["gpg", "--homedir", temporary, "--batch", "--dearmor", "--output", str(ring), str(key)]
        )
        signature = run(["gpgv", "--status-fd=1", "--keyring", str(ring), str(checksum)])
        require(
            ("[GNUPG:] VALIDSIG " + SIGNER + " ").encode() in signature.stdout,
            "unexpected-media-signer",
        )
    expected = re.findall(
        r"^SHA256 \(" + re.escape(iso.name) + r"\) = ([a-f0-9]{64})$", checksum.read_text(), re.M
    )
    require(len(expected) == 1 and sha(iso) == expected[0], "media-checksum-mismatch")
    return expected[0]


def arguments(serial_console):
    return INSTALLER_ARGS + (" " + SERIAL_ARGS if serial_console else "")


def stage(directory, payload, files):
    root = Path(directory) / "hermes-installer"
    for path in (root, root / "production"):
        path.mkdir(mode=0o755)
        os.chmod(path, 0o755)
    for name, data in payload.items():
        atomic(root / name, data, 0o644)
    atomic(root / "manifest.json", canonical(files), 0o644)
    return root


def tools(*, apply=False):
    """One-time local image with mkksiso; built from the local Fedora 44 base, no pull."""
    present = run(["podman", "image", "exists", TOOLS_IMAGE], check=False).returncode == 0
    result = {"status": "PRESENT" if present else "PREVIEW", "image": TOOLS_IMAGE}
    if present or not apply:
        return result
    with tempfile.TemporaryDirectory(prefix="hermes-media-tools-") as context:
        recipe = Path(context) / "Containerfile"
        recipe.write_text(
            f"FROM {TOOLS_BASE}\n"
            "RUN dnf -y --setopt=install_weak_deps=False install "
            + " ".join(TOOLS_PACKAGES)
            + " && dnf clean all\n"
        )
        run(
            ["podman", "build", "--pull=never", "-t", TOOLS_IMAGE, "-f", str(recipe), context],
            timeout=1800,
        )
    return result | {"status": "BUILT"}


def container(work, argv, timeout=1800):
    """Run a media tool on a private, relabeled work directory with no network."""
    return run(
        [
            "podman",
            "run",
            "--rm",
            "--network=none",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,size=1g",
            "--cap-drop=all",
            "--security-opt=no-new-privileges",
            "-v",
            f"{work}:/work:Z",
            TOOLS_IMAGE,
            *argv,
        ],
        timeout=timeout,
    )


ESP_TYPE = "C12A7328-F81F-11D2-BA4B-00A0C93EC93B"


def efi_partition(path):
    """Bytes of the image's single GPT EFI System Partition (what USB firmware boots)."""
    table = decode(run(["sfdisk", "--json", str(path)]).stdout)["partitiontable"]
    require(
        table.get("label") == "gpt" and table.get("sectorsize", 512) == 512, "media-gpt-required"
    )
    rows = [row for row in table["partitions"] if row["type"].upper() == ESP_TYPE]
    require(len(rows) == 1, "media-efi-partition-count")
    with Path(path).open("rb") as stream:
        stream.seek(rows[0]["start"] * 512)
        return stream.read(rows[0]["size"] * 512)


def build(settings_file, signers, iso, checksum, output, *, serial_console=False, apply=False):
    settings = kickstart.validate(read_json(settings_file))
    payload, files = kickstart.manifest(settings, signers)
    pinned = digest(files)
    content = kickstart.render(settings, pinned)
    output = Path(output)
    verified = verify_iso(iso, checksum)
    result = {
        "status": "PREVIEW",
        "disk_to_erase": settings["disk_id"],
        "kind": settings["kind"],
        "media_sha256": verified,
        "manifest_sha256": pinned,
        "kickstart_sha256": digest({"kickstart": content}),
        "boot_arguments": arguments(serial_console),
        "output": str(output),
    }
    if not apply:
        return result
    require(not output.exists() and not output.is_symlink(), "media-output-exists")
    require(
        run(["podman", "image", "exists", TOOLS_IMAGE], check=False).returncode == 0,
        "media-tools-image-missing-run-media-tools",
    )
    with tempfile.TemporaryDirectory(prefix=".hermes-media-", dir=output.parent) as temporary:
        work = Path(temporary)
        # A reflink copy is a new inode: relabeling it never touches the operator's ISO.
        run(["cp", "--reflink=auto", str(iso), str(work / "dvd.iso")], timeout=1800)
        require(sha(work / "dvd.iso") == verified, "media-copy-mismatch")
        stage(work, payload, files)
        atomic(work / "hermes-production.ks", content.encode(), 0o644)
        # The installation source is the boot media's own label (USB disk or CD-ROM).
        info = container(work, ["xorriso", "-indev", "/work/dvd.iso", "-pvd_info"], timeout=120)
        labels = re.findall(r"^Volume Id\s*:\s*(\S+)\s*$", info.stdout.decode(), re.M)
        require(
            len(labels) == 1 and re.fullmatch(r"[A-Za-z0-9._-]{1,32}", labels[0]) is not None,
            "media-volume-id-unavailable",
        )
        repository = "inst.repo=hd:LABEL=" + labels[0]
        result["installation_source"] = repository
        # Rootless containers have no loop devices, so mkefiboot is skipped and the
        # UEFI boot image's grub.cfg is replaced with mtools instead (below).
        container(
            work,
            [
                "mkksiso",
                "--skip-mkefiboot",
                "--ks",
                "/work/hermes-production.ks",
                "--add",
                "/work/hermes-installer",
                "-c",
                arguments(serial_console) + " " + repository,
                *("-R", 'set default="1"', 'set default="0"'),
                *("-R", "set timeout=60", "set timeout=5"),
                "/work/dvd.iso",
                "/work/stage.iso",
            ],
        )
        container(
            work,
            [
                "xorriso",
                "-osirrox",
                "on",
                "-indev",
                "/work/stage.iso",
                "-extract",
                "/EFI/BOOT/grub.cfg",
                "/work/grub.cfg",
                "-extract",
                "/images/efiboot.img",
                "/work/efiboot.img",
            ],
            timeout=300,
        )
        for path in (work / "grub.cfg", work / "efiboot.img"):
            os.chmod(path, 0o644)
        for name in ("grub.cfg", "BOOT.conf"):
            container(
                work,
                ["mcopy", "-o", "-i", "/work/efiboot.img", "/work/grub.cfg", "::/EFI/BOOT/" + name],
                timeout=120,
            )
        container(
            work,
            [
                "xorriso",
                "-indev",
                "/work/stage.iso",
                "-outdev",
                "/work/hermes.iso",
                "-boot_image",
                "any",
                "replay",
                # Replay re-appends the DVD's original EFI partition, which UEFI firmware
                # boots from a USB stick. Replace it with the updated boot image.
                "-append_partition",
                "2",
                "0xef",
                "/work/efiboot.img",
                "-update",
                "/work/efiboot.img",
                "/images/efiboot.img",
            ],
        )
        container(work, ["implantisomd5", "--force", "/work/hermes.iso"])
        (work / "check").mkdir()
        container(
            work,
            [
                "xorriso",
                "-osirrox",
                "on",
                "-indev",
                "/work/hermes.iso",
                "-extract",
                "/hermes-installer/manifest.json",
                "/work/check/manifest.json",
                "-extract",
                "/hermes-production.ks",
                "/work/check/kickstart.ks",
                "-extract",
                "/images/efiboot.img",
                "/work/check/efiboot.img",
            ],
            timeout=300,
        )
        require(
            (work / "check/manifest.json").read_bytes() == canonical(files), "iso-payload-mismatch"
        )
        require((work / "check/kickstart.ks").read_text() == content, "iso-kickstart-mismatch")
        # A virtual CD boots the El Torito image file; a USB stick boots the GPT EFI
        # System Partition. Both must carry the same automatic-install menu.
        image = (work / "check/efiboot.img").read_bytes()
        esp = efi_partition(work / "hermes.iso")
        require(esp[: len(image)] == image, "usb-efi-partition-not-updated")
        atomic(work / "check/esp.img", esp, 0o644)
        for source in ("/work/check/efiboot.img", "/work/check/esp.img"):
            efi = container(
                work, ["mtype", "-i", source, "::/EFI/BOOT/grub.cfg"], timeout=120
            ).stdout.decode()
            install = [line for line in efi.splitlines() if line.strip().startswith("linux ")][:1]
            require(
                'set default="0"' in efi
                and install
                and arguments(serial_console) in install[0]
                and repository in install[0].split()
                and ":/hermes-production.ks" in install[0],
                "uefi-boot-arguments-missing",
            )
        os.chmod(work / "hermes.iso", 0o600)
        os.rename(work / "hermes.iso", output)
    result["status"] = "BUILT"
    result["iso_sha256"] = sha(output)
    return result
