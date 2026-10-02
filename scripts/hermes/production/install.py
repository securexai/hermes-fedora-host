"""Installer %post commissioning inside the target chroot. Runs once per installation.

Replaces the random temporary LUKS passphrase with an escrowed recovery key plus a
SHA256 PCR7 TPM2 token, sets an escrowed break-glass administrator password, and
installs the per-boot commissioning unit. Plaintext secrets exist only in the
installer's private tmpfs and in the operator-encrypted escrow.
"""

from __future__ import annotations

import os
import pwd
import re
import secrets
import stat
from pathlib import Path

from . import escrow, preflight
from .primitives import (
    atomic,
    canonical,
    decode,
    digest,
    protected_directory,
    read_json,
    regular,
    require,
    run,
    sha,
)

INSTALLER = Path("/usr/local/libexec/hermes-installer")
WORK = Path("/var/lib/hermes-install")
STATE = Path("/var/lib/hermes-production")
RECEIPT = STATE / "install-receipt.json"
CRYPTTAB = Path("/etc/crypttab")
BOOT = Path("/boot")
DRACUT = Path("/etc/dracut.conf.d/60-hermes-tpm.conf")
DRACUT_BYTES = b'add_dracutmodules+=" systemd-cryptsetup tpm2-tss "\n'
RESTIC_PASSWORD = Path("/etc/hermes-production/restic-password")
UNIT = preflight.COMMISSION_UNIT
LABEL = "hermes-production"
FILE_CONTEXTS = "/etc/selinux/targeted/contexts/files/file_contexts"
UNIT_BYTES = preflight.COMMISSION_UNIT_BYTES


def luks_uuid(raw):
    """The single Anaconda-written crypttab row for the encrypted PV."""
    rows = []
    for line in raw.decode().splitlines():
        fields = line.split("#", 1)[0].split()
        if fields:
            rows.append(fields)
    require(len(rows) == 1 and len(rows[0]) in (3, 4), "crypttab-target-row-count")
    match = re.fullmatch(r"UUID=([a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12})", rows[0][1])
    require(
        match is not None and rows[0][2] in ("none", "-"), "crypttab-layout-or-keyfile-conflict"
    )
    return match.group(1)


def crypttab_tpm(raw, uuid, *, embedded=False):
    """Add tpm2-device=auto to exactly the target row; refuse any other TPM option.

    dracut's embedded copy names the device by path instead of UUID=.
    """
    identities = {"UUID=" + uuid} | ({"/dev/disk/by-uuid/" + uuid} if embedded else set())
    lines = raw.decode().splitlines(keepends=True)
    matched = 0
    for index, line in enumerate(lines):
        content = line.split("#", 1)[0]
        fields = list(re.finditer(r"\S+", content))
        if len(fields) < 2 or fields[1].group() not in identities:
            continue
        matched += 1
        require(len(fields) in (3, 4) and fields[2].group() in ("none", "-"), "crypttab-conflict")
        options = fields[3].group().split(",") if len(fields) == 4 else []
        options = [] if options == ["-"] else options
        tpm = [option for option in options if option.startswith("tpm2-")]
        require(tpm in ([], ["tpm2-device=auto"]), "crypttab-tpm-options-conflict")
        if not tpm:
            options.append("tpm2-device=auto")
            end = fields[3].end() if len(fields) == 4 else fields[2].end()
            start = fields[3].start() if len(fields) == 4 else end
            prefix = line[:start] if len(fields) == 4 else line[:end] + " "
            lines[index] = prefix + ",".join(options) + line[end:]
    require(matched == 1, "crypttab-target-row-count")
    return "".join(lines).encode()


def metadata(device):
    return decode(run(["cryptsetup", "luksDump", "--dump-json-metadata", device]).stdout)


def token_layout(data, recovery):
    """Exactly the recovery slot plus one PCR7-only, no-PIN TPM2 token slot."""
    tokens = list(data.get("tokens", {}).values())
    require(len(tokens) == 1, "unexpected-token-count")
    token = tokens[0]
    require(
        token.get("type") == "systemd-tpm2"
        and token.get("tpm2-pcrs") == [7]
        and token.get("tpm2-pcr-bank") == "sha256"
        and token.get("tpm2-pin", False) is False
        and not token.get("tpm2-salt")
        and not token.get("tpm2_pcrlock")
        and not token.get("tpm2_pubkey_pcrs")
        and not token.get("tpm2-public-key-pcrs"),
        "unexpected-tpm-policy",
    )
    enrolled = token.get("keyslots", [])
    require(
        len(enrolled) == 1
        and enrolled[0] != recovery
        and set(data.get("keyslots", {})) == {recovery, enrolled[0]},
        "unexpected-keyslot-layout",
    )
    return enrolled[0]


def private_file(path, content):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)


def shred(path):
    path = Path(path)
    if path.exists():
        size = path.stat().st_size
        with path.open("r+b") as stream:
            stream.write(b"\0" * size)
            stream.flush()
            os.fsync(stream.fileno())
        path.unlink()


def check_work():
    info = WORK.lstat()
    require(
        stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o700,
        "installer-private-tmpfs-required",
    )
    filesystem = run(["findmnt", "-n", "-o", "FSTYPE", "--target", str(WORK)]).stdout.strip()
    require(filesystem == b"tmpfs", "installer-private-tmpfs-required")


def packages():
    run(["rpm", "-q", *preflight.PACKAGES, "lvm2", "openssl"])
    version = run(["podman", "--version"]).stdout.decode().split()[-1]
    require(tuple(map(int, version.split(".")[:3])) >= (5, 8, 4), "podman-at-least-5.8.4-required")


def commission():
    require(os.geteuid() == 0, "installer-root-required")
    require(not RECEIPT.exists(), "installation-already-commissioned-never-replay")
    settings = read_json(INSTALLER / "install.json", owner=0)
    certificate = WORK / "escrow-certificate.pem"
    check_work()
    private_file(certificate, settings["escrow_certificate"].encode())
    certificate_sha256 = escrow.certificate(settings["escrow_certificate"])
    account = pwd.getpwnam(settings["admin"])
    packages()
    for prefix in ("/etc/systemd", "/usr/lib/systemd"):
        for name in ("tpm2-pcr-public-key.pem", "tpm2-pcr-signature.json"):
            require(not (Path(prefix) / name).exists(), "additional-tpm-policy-needs-review")
    uuid = luks_uuid(CRYPTTAB.read_bytes())
    device = "/dev/disk/by-uuid/" + uuid
    temporary = regular(WORK / "luks-temporary", owner=0, private=True)
    before = metadata(device)
    require(len(before["keyslots"]) == 1 and not before.get("tokens"), "unexpected-initial-luks")
    (temporary_slot,) = before["keyslots"]
    recovery_file = WORK / "recovery-key"
    private_file(recovery_file, escrow.recovery_key().encode())
    run(["cryptsetup", "luksAddKey", "--key-file", str(temporary), device, str(recovery_file)])
    added = set(metadata(device)["keyslots"]) - {temporary_slot}
    require(len(added) == 1, "recovery-slot-not-added")
    (recovery_slot,) = added
    run(
        [
            "systemd-cryptenroll",
            "--unlock-key-file=" + str(temporary),
            "--tpm2-device=auto",
            "--tpm2-pcrs=7:sha256",
            "--tpm2-with-pin=no",
            "--tpm2-pcrlock=",
            device,
        ],
        timeout=300,
    )
    test = ["cryptsetup", "open", "--test-passphrase", "--type", "luks2", "--tries", "1"]
    run(
        [
            *test,
            "--disable-external-tokens",
            "--key-slot",
            recovery_slot,
            "--key-file",
            str(recovery_file),
            device,
        ]
    )
    # The TPM must unseal under the installer's PCR7; firstboot repeats this check
    # after the real boot path to prove installer and installed PCR7 agree.
    run([*test, "--token-only", "--token-type", "systemd-tpm2", device], timeout=120)
    run(["cryptsetup", "luksRemoveKey", "--key-file", str(temporary), device])
    final = metadata(device)
    tpm_slot = token_layout(final, recovery_slot)
    run(["cryptsetup", "config", device, "--label", LABEL])
    atomic(
        CRYPTTAB, crypttab_tpm(CRYPTTAB.read_bytes(), uuid), stat.S_IMODE(CRYPTTAB.stat().st_mode)
    )
    atomic(DRACUT, DRACUT_BYTES, 0o644)
    run(["dracut", "--regenerate-all", "--force"], timeout=1800)
    for image in sorted(BOOT.glob("initramfs-*.img")):
        if "rescue" in image.name:
            continue
        modules = set(run(["lsinitrd", "-m", str(image)]).stdout.decode().split())
        require({"systemd-cryptsetup", "tpm2-tss"} <= modules, "initramfs-tpm-modules-missing")
        embedded = run(["lsinitrd", "-f", "etc/crypttab", str(image)]).stdout
        require(
            crypttab_tpm(embedded, uuid, embedded=True) == embedded, "initramfs-crypttab-mismatch"
        )
    header = WORK / "luks-header.img"
    run(["cryptsetup", "luksHeaderBackup", device, "--header-backup-file", str(header)])
    admin_password = escrow.password()
    run(["chpasswd"], data=f"{settings['admin']}:{admin_password}\n".encode())
    run(["passwd", "--lock", "root"])
    protected_directory(RESTIC_PASSWORD.parent)
    protected_directory(STATE)
    restic_password = escrow.password()
    atomic(RESTIC_PASSWORD, restic_password.encode(), 0o600)
    nonce = secrets.token_hex(32)
    pcr7 = run(["tpm2_pcrread", "sha256:7"]).stdout
    inside = {
        "schema": 1,
        "luks_uuid": uuid,
        "recovery_slot": recovery_slot,
        "tpm_slot": tpm_slot,
        "enrollment_nonce": nonce,
        "escrow_certificate_sha256": certificate_sha256,
    }
    sealed = escrow.seal(
        certificate,
        {
            "recovery-key": recovery_file.read_bytes(),
            "admin-password": admin_password.encode(),
            "restic-password": restic_password.encode(),
            "luks-header.img": header.read_bytes(),
            "receipt.json": canonical(inside),
        },
    )
    del admin_password, restic_password
    target = Path(account.pw_dir) / "hermes-escrow.cms"
    atomic(target, sealed, 0o600)
    os.chown(target, account.pw_uid, account.pw_gid)
    for path in (recovery_file, header, certificate):
        shred(path)
    atomic(UNIT, UNIT_BYTES, 0o644)
    run(["systemctl", "enable", UNIT.name])
    receipt = {
        "schema": 1,
        "luks_uuid": uuid,
        "recovery_slot": recovery_slot,
        "tpm_slot": tpm_slot,
        "recovery_test": "PASS",
        "installer_tpm_unseal": "PASS",
        "temporary_slot_removed": temporary_slot not in final["keyslots"],
        "escrow_sha256": sha(target),
        "escrow_certificate_sha256": certificate_sha256,
        "enrollment_nonce_sha256": digest({"nonce": nonce}),
        "installer_pcr7_sha256": digest({"pcr7": pcr7.decode()}),
        "admin": settings["admin"],
    }
    require(receipt["temporary_slot_removed"], "temporary-slot-remains")
    atomic(RECEIPT, canonical(receipt), 0o600)
    # The installer may run without a loaded policy; label exactly what we created.
    run(
        [
            "setfiles",
            "-F",
            FILE_CONTEXTS,
            "/etc/shadow",
            str(CRYPTTAB),
            str(DRACUT),
            str(UNIT),
            "/etc/hermes-production",
            str(STATE),
            str(INSTALLER),
            str(target),
        ],
        timeout=300,
    )
    return {
        "status": "INSTALLED_COMMISSIONING_PENDING",
        "luks_uuid": uuid,
        "keyslots": sorted(final["keyslots"]),
        "escrow_sha256": receipt["escrow_sha256"],
    }
