"""Per-boot automatic commissioning after an unattended installation.

Runs from `hermes-commission.service` until every required proof passes:

* first boot: generate host.json from the real identities, run the reviewed
  bootstrap, publish SSH fingerprints and a console code, request one reboot;
* every boot: prove the TPM2 token unseals under the installed boot path, track
  unclean shutdowns, rewrite the commissioning record.

Operator attestations arrive through the bounded dispatcher. Each one needs a code
that only the escrow holder (decrypted nonce) or someone at the console
(per-boot code) can know, so a stolen deployment key alone cannot promote a host.
"""

from __future__ import annotations

import hmac
import re
import secrets
import time
from pathlib import Path

from . import host, kickstart, preflight, startup
from .primitives import (
    atomic,
    canonical,
    digest,
    protected_directory,
    read_json,
    regular,
    require,
    run,
    sha,
)

INSTALLER = Path("/usr/local/libexec/hermes-installer")
STATE = Path("/var/lib/hermes-production")
RECEIPT = STATE / "install-receipt.json"
DIRECTORY = STATE / "commission"
COMPLETE = STATE / "commissioned"
ISSUE = Path("/etc/issue.d/hermes-commission.issue")
HOST_KEY = Path("/etc/ssh/ssh_host_ed25519_key.pub")
FALLBACK = re.compile(r"(?i)falling back|failed to unseal|policy does not match")
ATTESTED = {
    "escrow": "encrypted_offhost_recovery",
    "console": "console_access",
    "power": "firmware_power_restoration",
}


def tpm_unseals(luks_uuid):
    """The PCR7 token unseals now, without any passphrase or keyfile."""
    result = run(
        [
            "cryptsetup",
            "open",
            "--test-passphrase",
            "--type",
            "luks2",
            "--tries",
            "1",
            "--token-only",
            "--token-type",
            "systemd-tpm2",
            "/dev/disk/by-uuid/" + luks_uuid,
        ],
        check=False,
        timeout=120,
    )
    return result.returncode == 0


def fallback_logged():
    """systemd-cryptsetup reported a TPM failure or passphrase fallback in this boot."""
    output = run(
        ["journalctl", "-b", "0", "-o", "cat", "--no-pager", "_COMM=systemd-cryptsetup"],
        check=False,
    ).stdout.decode(errors="replace")
    return FALLBACK.search(output) is not None


def identities(receipt):
    home = preflight.mount("/home/hermes")
    return {
        "machine_id": Path("/etc/machine-id").read_text().strip(),
        "home_uuid": home["uuid"],
        "luks_uuid": receipt["luks_uuid"],
        "ssh_host_sha256": sha(HOST_KEY),
    }


def fingerprint():
    output = run(["ssh-keygen", "-lf", str(HOST_KEY)]).stdout.decode().split()
    require(len(output) >= 2 and output[1].startswith("SHA256:"), "host-key-fingerprint")
    return output[1]


def code():
    raw = secrets.token_hex(5).upper()
    return raw[:5] + "-" + raw[5:]


def load(name, default):
    path = DIRECTORY / name
    return read_json(path, owner=0) if path.exists() else default


def save(name, value):
    atomic(DIRECTORY / name, canonical(value), 0o600)


def issue(lines):
    # agetty (root) also reads /etc/issue.d/*.issue; the console is the only reader.
    ISSUE.parent.mkdir(mode=0o755, exist_ok=True)
    atomic(ISSUE, ("\n".join(["Hermes production commissioning", *lines]) + "\n\n").encode(), 0o600)
    run(["agetty", "--reload"], check=False)


def automatic_reboot(boots):
    """A requested reboot followed by a clean, TPM-unsealed boot with no fallback."""
    for first, second in zip(boots, boots[1:]):
        if (
            first["reboot_requested"]
            and first["tpm_unseals"]
            and second["boot_id"] != first["boot_id"]
            and second["tpm_unseals"]
            and not second["fallback_logged"]
            and not second["unclean_previous"]
        ):
            return {"requested": first, "observed": second}
    return None


def refresh(config):
    """Rewrite the commissioning record from retained observations; report completion."""
    receipt = read_json(RECEIPT, owner=0)
    boots = load("boots.json", [])
    current = startup.boot_id()
    report = preflight.collect(config, commissioned=False, installed=True, capacity=False)
    require(report["status"] == "PASS", "commissioning-preflight-failed")
    gates, evidence = {}, {}
    for gate in preflight.PROOFS:
        gates[gate], evidence[gate] = "NOT_RUN", digest({"gate": gate, "status": "NOT_RUN"})
    if (
        receipt["recovery_test"] == "PASS"
        and receipt["installer_tpm_unseal"] == "PASS"
        and receipt["temporary_slot_removed"] is True
    ):
        gates["recovery_unlock"], evidence["recovery_unlock"] = "PASS", sha(RECEIPT)
    proof = automatic_reboot(boots)
    this_boot = [b for b in boots if b["boot_id"] == current]
    if proof and this_boot and this_boot[-1]["tpm_unseals"]:
        gates["automatic_reboot"], evidence["automatic_reboot"] = "PASS", digest(proof)
    for gate, row in load("attestations.json", {}).items():
        require(gate in ATTESTED.values() and row["status"] == "PASS", "invalid-attestation")
        gates[gate], evidence[gate] = "PASS", digest(row)
    identity = report["commissioning_identity"]
    record = {
        "host_sha256": identity["host_sha256"],
        "boot_sha256": identity["boot_sha256"],
        "packages_sha256": identity["packages_sha256"],
        "gates": gates,
        "evidence": evidence,
    }
    atomic(preflight.COMMISSION, canonical(record), 0o600)
    missing = sorted(g for g in preflight.required_proofs(config) if gates[g] != "PASS")
    if not missing:
        atomic(COMPLETE, canonical({"host_sha256": identity["host_sha256"]}), 0o600)
        # Codes are no longer accepted; the banner keeps only the pinned host key.
        issue([f"  SSH host key: {fingerprint()} (ED25519)", "  Commissioning complete"])
    return {"status": "COMMISSIONED" if not missing else "PENDING", "missing": missing}


def boot():
    """Per-boot service entry point (root, local)."""
    require(Path("/proc/self").exists(), "procfs-required")
    receipt = read_json(RECEIPT, owner=0)
    settings = read_json(INSTALLER / "install.json", owner=0)
    protected_directory(DIRECTORY)
    current = startup.boot_id()
    marker = DIRECTORY / "running"
    unclean = marker.exists() and regular(marker, owner=0).read_text().strip() != current
    atomic(marker, current.encode(), 0o600)
    record = {
        "boot_id": current,
        "observed_at": int(time.time()),
        "tpm_unseals": tpm_unseals(receipt["luks_uuid"]),
        "fallback_logged": fallback_logged(),
        "unclean_previous": unclean,
        "reboot_requested": False,
    }
    path = DIRECTORY / "host.json"
    if not path.exists():
        config = kickstart.host_template(settings, identities(receipt))
        atomic(path, canonical(preflight.configuration(config)), 0o600)
    config = preflight.configuration(read_json(path, owner=0))
    bootstrapped = STATE / "bootstrap.json"
    if not (
        bootstrapped.exists()
        and read_json(bootstrapped, owner=0) == {"host_sha256": digest(config)}
    ):
        host.bootstrap(path, INSTALLER / "allowed_signers", apply=True)
    console = code()
    power = code() if unclean and record["tpm_unseals"] and not record["fallback_logged"] else None
    save(
        "codes.json",
        {
            "boot_id": current,
            "console": digest({"code": console}),
            "power": digest({"code": power}) if power else None,
        },
    )
    boots = load("boots.json", [])
    if (
        not any(b["reboot_requested"] for b in boots)
        and record["tpm_unseals"]
        and not record["fallback_logged"]
    ):
        record["reboot_requested"] = True
    save("boots.json", [*boots, record])
    result = refresh(config)
    lines = [f"  SSH host key: {fingerprint()} (ED25519)"]
    if result["status"] != "COMMISSIONED":
        lines.append(f"  Console code: {console}")
        if power:
            lines.append(f"  Power-restoration code: {power}")
        lines.append("  Pending: " + ", ".join(result["missing"]))
    issue(lines)
    if record["reboot_requested"]:
        # This reboot is clean by construction. The shutdown stops this unit while it
        # is still activating, so ExecStop would not clear the marker in time.
        marker.unlink()
        run(["systemctl", "--no-block", "reboot"])
    return result | {
        "tpm_unseals": record["tpm_unseals"],
        "reboot_requested": record["reboot_requested"],
    }


def clean_shutdown():
    marker = DIRECTORY / "running"
    if marker.exists() and regular(marker, owner=0).read_text().strip() == startup.boot_id():
        marker.unlink()
    return {"status": "CLEAN_SHUTDOWN_RECORDED"}


def attest(config, body):
    """Dispatcher attestation: proof kind plus a code from the escrow or the console."""
    require(
        isinstance(body, dict)
        and set(body) == {"proof", "code"}
        and body["proof"] in ATTESTED
        and isinstance(body["code"], str)
        and re.fullmatch(r"[A-Za-z0-9-]{8,128}", body["code"]) is not None,
        "invalid-attestation-request",
    )
    receipt = read_json(RECEIPT, owner=0)
    current = startup.boot_id()
    if body["proof"] == "escrow":
        expected = receipt["enrollment_nonce_sha256"]
        observed = digest({"nonce": body["code"]})
    else:
        codes = load("codes.json", {})
        require(codes.get("boot_id") == current, "attestation-code-expired")
        expected = codes.get(body["proof"]) or ""
        observed = digest({"code": body["code"].upper()})
    require(bool(expected) and hmac.compare_digest(expected, observed), "attestation-code-mismatch")
    gate = ATTESTED[body["proof"]]
    attestations = load("attestations.json", {})
    attestations[gate] = {"status": "PASS", "boot_id": current, "recorded_at": int(time.time())}
    save("attestations.json", attestations)
    return refresh(config) | {"attested": gate}
