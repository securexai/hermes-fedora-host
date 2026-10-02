"""Render a nonsecret, explicitly disk-bound, unattended Fedora Server installation profile.

The installer generates every secret itself (see `install.py`) and seals it to the
operator's escrow certificate, so the rendered Kickstart and media contain public
material only.
"""

import hashlib
import re
from pathlib import Path

from . import escrow, preflight
from .primitives import atomic, canonical, digest, read_json, require, sha

ROOT = Path(__file__).resolve().parents[3]
CONTROLLER = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "vm/kickstart/fedora-server-production.ks.in"
# Fedora 44 setup RPM accounts, plus this profile's service identities. The
# installer also checks its live account database before storage changes.
RESERVED_ADMINS = frozenset(
    "root bin daemon adm lp sync shutdown halt mail operator games ftp nobody "
    "hermes hermes-deploy".split()
)
FIELDS = frozenset(
    {
        "disk_id",
        "disk_min_mib",
        "root_mib",
        "var_mib",
        "hermes_mib",
        "hostname",
        "admin",
        "admin_public_key",
        "timezone",
        "kind",
        "application_mode",
        "escrow_certificate",
        "deploy_public_key",
        "deploy_from",
        "artifact_budget_bytes",
        "state_budget_bytes",
        "restic_repository",
    }
)
# Values the installed system needs; everything else only shapes the Kickstart text.
INSTALL_FIELDS = (
    "admin",
    "kind",
    "application_mode",
    "escrow_certificate",
    "deploy_public_key",
    "deploy_from",
    "artifact_budget_bytes",
    "state_budget_bytes",
    "restic_repository",
)
# Placeholders substituted into the Kickstart text.
TEXT_FIELDS = (
    "disk_id",
    "disk_min_mib",
    "root_mib",
    "var_mib",
    "hermes_mib",
    "hostname",
    "admin",
    "admin_public_key",
    "timezone",
)


def validate(settings):
    require(isinstance(settings, dict) and set(settings) == FIELDS, "invalid-installation-fields")
    disk = settings["disk_id"]
    require(
        re.fullmatch(
            r"/dev/disk/by-id/(?:wwn-|nvme-|ata-|scsi-|virtio-)[A-Za-z0-9_.:-]+", disk or ""
        )
        and not re.search(r"-part[0-9]+$", disk),
        "explicit-whole-disk-id-required",
    )
    for key, minimum in (
        ("root_mib", 30720),
        ("var_mib", 40960),
        ("hermes_mib", 40960),
        ("disk_min_mib", 120000),
    ):
        require(
            type(settings[key]) is int and minimum <= settings[key] < 2**31,
            "invalid-storage-sizing",
        )
    require(
        settings["disk_min_mib"]
        >= sum(settings[k] for k in ("root_mib", "var_mib", "hermes_mib")) + 4096,
        "disk-too-small-for-layout",
    )
    require(
        re.fullmatch(r"[a-z][a-z0-9-]{0,62}(?:\.[a-z0-9-]{1,63})*", settings["hostname"] or ""),
        "invalid-hostname",
    )
    require(
        re.fullmatch(r"[a-z][a-z0-9_]{0,30}", settings["admin"] or "")
        and settings["admin"] not in RESERVED_ADMINS,
        "invalid-admin-account",
    )
    require(
        re.fullmatch(
            r"ssh-ed25519 [A-Za-z0-9+/]{60,100}={0,2}", settings["admin_public_key"] or ""
        ),
        "invalid-admin-public-key",
    )
    require(
        re.fullmatch(r"[A-Za-z_]+(?:/[A-Za-z_+-]+)+", settings["timezone"] or ""),
        "invalid-timezone",
    )
    require(
        settings["deploy_public_key"] != settings["admin_public_key"],
        "deployment-and-admin-keys-must-differ",
    )
    # Reuse the installed host contract for every value that reaches host.json.
    preflight.configuration(host_template(settings))
    escrow.certificate(settings["escrow_certificate"])
    # Budgets must fit the requested layout, or firstboot preflight would refuse.
    mib = 1024**2
    require(
        settings["var_mib"] * mib
        >= 20 * preflight.GIB
        + 3 * settings["artifact_budget_bytes"]
        + 2 * settings["state_budget_bytes"]
        and settings["hermes_mib"] * mib
        >= settings["artifact_budget_bytes"] + settings["state_budget_bytes"],
        "layout-too-small-for-capacity-budgets",
    )
    return settings


def host_template(settings, identities=None):
    """host.json for this installation; firstboot supplies the real identities."""
    identities = identities or {
        "machine_id": "0" * 32,
        "home_uuid": "00000000-0000-0000-0000-000000000000",
        "luks_uuid": "00000000-0000-0000-0000-000000000000",
        "ssh_host_sha256": "0" * 64,
    }
    return {
        "schema": 1,
        "kind": settings["kind"],
        "application_mode": settings["application_mode"],
        **identities,
        "artifact_budget_bytes": settings["artifact_budget_bytes"],
        "state_budget_bytes": settings["state_budget_bytes"],
        "restic_repository": settings["restic_repository"],
        "restic_password_file": "/etc/hermes-production/restic-password",
        "deploy_public_key": settings["deploy_public_key"],
        "deploy_from": settings["deploy_from"],
    }


def install_settings(settings):
    return {key: validate(settings)[key] for key in INSTALL_FIELDS}


def controller_files():
    """The receiver source the installer stages; identical to a bootstrap's file map."""
    names = {"productionctl.py", "production-launcher.py", "lab_profile.py"}
    names |= {"production/" + p.name for p in (CONTROLLER / "production").glob("*.py")}
    return {name: CONTROLLER / name for name in sorted(names)}


def manifest(settings, signers):
    """Public payload copied from the media; the Kickstart pins its manifest hash."""
    signer_data = Path(signers).read_bytes()
    require(
        len(signer_data) <= 16384 and b"hermes-production " in signer_data,
        "production-signer-identity-required",
    )
    payload = {name: path.read_bytes() for name, path in controller_files().items()}
    payload["install.json"] = canonical(install_settings(settings))
    payload["allowed_signers"] = signer_data
    files = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(payload.items())}
    return payload, {"schema": 1, "files": files}


def render(settings, manifest_sha256):
    validate(settings)
    require(re.fullmatch(r"[a-f0-9]{64}", manifest_sha256 or "") is not None, "invalid-manifest")
    template = TEMPLATE.read_text()
    for key in TEXT_FIELDS:
        template = template.replace("@@" + key.upper() + "@@", str(settings[key]))
    template = template.replace("@@MANIFEST_SHA256@@", manifest_sha256)
    # Disposable fixtures expose the console on serial for unattended observation.
    append = "audit=1" + (
        " console=tty0 console=ttyS0,115200n8" if settings["kind"] == "fixture" else ""
    )
    template = template.replace("@@BOOT_APPEND@@", append)
    require("@@" not in template, "unresolved-kickstart-placeholder")
    # Only the %pre generator may name the passphrase option, and only with a
    # runtime-substituted value. No password, hash or passphrase value is rendered.
    require(
        template.count("--passphrase") == 1
        and "--passphrase=%s" in template
        and "--password" not in template
        and "--iscrypted" not in template
        and "rootpw --plaintext" not in template,
        "secret-in-kickstart",
    )
    return template


def write(settings_file, output, *, signers, apply=False):
    settings = validate(read_json(settings_file))
    _, files = manifest(settings, signers)
    content = render(settings, digest(files))
    result = {
        "status": "PREVIEW",
        "disk_to_erase": settings["disk_id"],
        "settings_sha256": digest(settings),
        "manifest_sha256": digest(files),
        "escrow_certificate_sha256": escrow.certificate(settings["escrow_certificate"]),
        "private_console": "NONE: secrets are generated by the installer and escrowed",
    }
    if apply:
        output = Path(output)
        require(not output.exists(), "installation-output-exists")
        atomic(output, content.encode(), 0o600)
        result["status"] = "RENDERED"
        result["kickstart_sha256"] = sha(output)
    return result
