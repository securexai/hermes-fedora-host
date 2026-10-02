"""Workstation-side helpers: pinned SSH, console-verified host pinning, escrow enrollment."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from . import escrow
from .primitives import atomic, decode, regular, require, run, sha

HOST = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]*")


def ssh(host, port, user, identity, known_hosts, command=None):
    require(HOST.fullmatch(host or "") is not None, "invalid-ssh-host")
    require(1 <= port <= 65535, "invalid-ssh-port")
    regular(known_hosts)
    regular(identity, private=True)
    argv = ["ssh", "-p", str(port), "-F", "/dev/null", "-T"]
    for option in (
        "BatchMode=yes",
        "IdentitiesOnly=yes",
        "IdentityAgent=none",
        "StrictHostKeyChecking=yes",
        "ClearAllForwardings=yes",
        "ConnectTimeout=10",
        "UserKnownHostsFile=" + str(Path(known_hosts).absolute()),
        "GlobalKnownHostsFile=/dev/null",
    ):
        argv += ["-o", option]
    argv += ["-i", str(Path(identity).absolute()), f"{user}@{host}"]
    return argv + ([command] if command else [])


def pin_host(host, port, fingerprint, known_hosts, *, apply=False):
    """Accept the scanned key only if it matches the fingerprint read at the console."""
    require(HOST.fullmatch(host or "") is not None and 1 <= port <= 65535, "invalid-ssh-target")
    require(
        re.fullmatch(r"SHA256:[A-Za-z0-9+/]{43}", fingerprint or "") is not None,
        "invalid-console-fingerprint",
    )
    scanned = run(["ssh-keyscan", "-T", "10", "-p", str(port), "-t", "ed25519", host], timeout=30)
    lines = [line for line in scanned.stdout.decode().splitlines() if line and line[0] != "#"]
    require(len(lines) == 1 and lines[0].split()[1] == "ssh-ed25519", "unexpected-host-key-scan")
    observed = run(["ssh-keygen", "-lf", "-"], data=(lines[0] + "\n").encode()).stdout.split()
    require(
        len(observed) >= 2 and observed[1].decode() == fingerprint, "host-key-fingerprint-mismatch"
    )
    content = (lines[0] + "\n").encode()
    result = {"status": "PREVIEW", "host": host, "port": port, "fingerprint": fingerprint}
    if apply:
        target = Path(known_hosts)
        if target.exists() or target.is_symlink():
            require(regular(target).read_bytes() == content, "known-hosts-exists-with-other-key")
        else:
            atomic(target, content, 0o600)
        result["status"] = "PINNED"
    return result


def enroll(target, admin, admin_identity, escrow_key, escrow_out, attest, *, apply=False):
    """Fetch, store and decrypt-verify the escrow, prove it to the host, delete the server copy.

    `target` is (host, port, known_hosts); `attest(code)` sends the escrow proof through
    the bounded deployment dispatcher. Secrets are never printed.
    """
    host, port, known_hosts = target
    require(re.fullmatch(r"[a-z][a-z0-9_]{0,30}", admin or "") is not None, "invalid-admin-account")
    regular(escrow_key, private=True)
    out = Path(escrow_out)
    require(not out.exists() and not out.is_symlink(), "escrow-output-exists")
    base = ssh(host, port, admin, admin_identity, known_hosts)
    result = {"status": "PREVIEW", "host": host, "escrow_output": str(out)}
    if not apply:
        return result
    fetched = run([*base, "cat -- hermes-escrow.cms"], timeout=300)
    require(0 < len(fetched.stdout) <= escrow.MAX_BYTES, "escrow-unavailable-on-host")
    atomic(out, fetched.stdout, 0o600)
    content = escrow.unseal(out, escrow_key)
    receipt = decode(content["receipt.json"])
    require(
        set(receipt)
        == {
            "schema",
            "luks_uuid",
            "recovery_slot",
            "tpm_slot",
            "enrollment_nonce",
            "escrow_certificate_sha256",
        },
        "invalid-escrow-receipt",
    )
    commissioning = attest(receipt["enrollment_nonce"])
    run([*base, "rm -- hermes-escrow.cms"], timeout=60)
    os.sync()
    return {
        "status": "ENROLLED",
        "host": host,
        "escrow_output": str(out),
        "escrow_sha256": sha(out),
        "luks_uuid": receipt["luks_uuid"],
        "members": sorted(content),
        "commissioning": commissioning,
    }


def operator_setup(output, server, *, apply=False):
    """Create the operator's production material in one owner-only directory.

    Admin and deployment keys are unencrypted but owner-only: the deployment key only
    reaches the bounded dispatcher, and the admin key alone cannot gain root (sudo needs
    the escrowed password). The release-signing and escrow keys are passphrase-protected;
    OpenSSH and OpenSSL read those passphrases from the terminal, never from arguments.
    """
    from . import kickstart

    output = Path(output)
    require(not output.exists() and not output.is_symlink(), "operator-directory-exists")
    files = {
        "admin_ed25519": "SSH key for the hermesadmin break-glass account (enroll)",
        "deploy_ed25519": "SSH key for the bounded deployment dispatcher",
        "signing_ed25519": "release-signing key (passphrase)",
        "allowed_signers": "public signer trust copied onto the server",
        "escrow/escrow-key.pem": "escrow private key (passphrase); keep it safe",
        "install.json": "non-secret installation settings",
    }
    result = {"status": "PREVIEW", "directory": str(output), "files": files, "server": server}
    if not apply:
        return result
    output.mkdir(mode=0o700, parents=False)
    for name, comment, passphrase in (
        ("admin_ed25519", "hermesadmin", False),
        ("deploy_ed25519", "hermes-deploy", False),
        ("signing_ed25519", "hermes-production-signing", True),
    ):
        argv = ["ssh-keygen", "-q", "-t", "ed25519", "-C", comment, "-f", str(output / name)]
        run(argv if passphrase else [*argv, "-N", ""], timeout=600)
    signer = (output / "signing_ed25519.pub").read_text().split()
    atomic(
        output / "allowed_signers",
        f'hermes-production namespaces="hermes-production-v1" {signer[0]} {signer[1]}\n'.encode(),
        0o644,
    )
    escrow.generate(output / "escrow", encrypt=True, apply=True)

    def public(name):
        return " ".join((output / (name + ".pub")).read_text().split()[:2])

    settings = server | {
        "admin": "hermesadmin",
        "admin_public_key": public("admin_ed25519"),
        "deploy_public_key": public("deploy_ed25519"),
        "escrow_certificate": (output / "escrow/escrow-certificate.pem").read_text(),
        "kind": "production",
        "application_mode": "production",
    }
    kickstart.validate(settings)
    atomic(output / "install.json", (json.dumps(settings, indent=2) + "\n").encode(), 0o600)
    result.update(
        status="CREATED",
        escrow_certificate_sha256=escrow.certificate(settings["escrow_certificate"]),
    )
    return result
