"""Install-generated secrets sealed to the operator's public RSA certificate.

OpenSSL CMS AuthEnvelopedData: AES-256-GCM content key wrapped with RSA-OAEP-SHA256.
Nobody types or memorizes these secrets; break-glass decrypts the escrow off-host.
"""

from __future__ import annotations

import io
import os
import re
import secrets
import tarfile
from pathlib import Path

from .primitives import require, run

MODHEX = "cbdefghijklnrtuv"
MEMBERS = frozenset(
    {"recovery-key", "admin-password", "restic-password", "luks-header.img", "receipt.json"}
)
MAX_BYTES = 64 * 1024 * 1024
CERTIFICATE = re.compile(
    r"-----BEGIN CERTIFICATE-----\n[A-Za-z0-9+/=\n]{200,12000}-----END CERTIFICATE-----\n?"
)


def recovery_key():
    """systemd recovery-key format: 256 random bits as eight dash-separated modhex groups."""
    text = "".join(MODHEX[b >> 4] + MODHEX[b & 15] for b in secrets.token_bytes(32))
    return "-".join(text[i : i + 8] for i in range(0, 64, 8))


def password():
    return secrets.token_urlsafe(24)


def certificate(pem):
    """Validate the public escrow certificate; return its SHA256 fingerprint."""
    require(
        isinstance(pem, str) and CERTIFICATE.fullmatch(pem) is not None,
        "invalid-escrow-certificate",
    )
    text = run(["openssl", "x509", "-noout", "-text"], data=pem.encode()).stdout.decode()
    match = re.search(r"Public Key Algorithm: rsaEncryption\s+Public-Key: \((\d+) bit\)", text)
    require(match is not None and int(match.group(1)) >= 3072, "escrow-requires-rsa-3072-or-larger")
    output = run(
        ["openssl", "x509", "-noout", "-fingerprint", "-sha256"], data=pem.encode()
    ).stdout.decode()
    fingerprint = output.strip().rpartition("=")[2].replace(":", "").lower()
    require(
        re.fullmatch(r"[a-f0-9]{64}", fingerprint) is not None, "escrow-fingerprint-unavailable"
    )
    return fingerprint


def generate(directory, *, encrypt=True, apply=False):
    """Operator RSA-4096 escrow key (passphrase-protected unless a test key) and certificate."""
    directory = Path(directory)
    require(not directory.exists() and not directory.is_symlink(), "escrow-directory-exists")
    result = {
        "status": "PREVIEW",
        "directory": str(directory),
        "key_protection": ("OPENSSL_PASSPHRASE_PROMPT" if encrypt else "UNENCRYPTED_TEST_KEY"),
    }
    if not apply:
        return result
    directory.mkdir(mode=0o700)
    key, cert = directory / "escrow-key.pem", directory / "escrow-certificate.pem"
    argv = [
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:4096",
        "-sha256",
        "-days",
        "3650",
        "-subj",
        "/CN=hermes-production-escrow",
        "-keyout",
        str(key),
        "-out",
        str(cert),
    ]
    # OpenSSL reads the key passphrase from the controlling terminal, never argv.
    run(argv if encrypt else [*argv, "-noenc"], timeout=600)
    os.chmod(key, 0o600)
    os.chmod(cert, 0o644)
    result.update(
        status="CREATED",
        certificate=str(cert),
        certificate_sha256=certificate(cert.read_text()),
    )
    return result


def archive(members):
    require(set(members) <= MEMBERS and members, "unexpected-escrow-member")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for name in sorted(members):
            data = members[name]
            require(isinstance(data, bytes), "escrow-member-not-bytes")
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o600, 0
            tar.addfile(info, io.BytesIO(data))
    require(buffer.tell() <= MAX_BYTES, "escrow-too-large")
    return buffer.getvalue()


def members(raw):
    """Strictly parse a decrypted escrow: unique regular files with known names only."""
    require(len(raw) <= MAX_BYTES, "escrow-too-large")
    result = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tar:
        for info in tar.getmembers():
            require(
                info.isfile() and info.name in MEMBERS and info.name not in result,
                "unexpected-escrow-member",
            )
            result[info.name] = tar.extractfile(info).read()
    require({"recovery-key", "admin-password", "receipt.json"} <= set(result), "incomplete-escrow")
    return result


def seal(certificate_path, content):
    """Encrypt to the recipient certificate. Plaintext only travels over pipes."""
    return run(
        [
            "openssl",
            "cms",
            "-encrypt",
            "-binary",
            "-aes-256-gcm",
            "-recip",
            str(certificate_path),
            "-keyopt",
            "rsa_padding_mode:oaep",
            "-keyopt",
            "rsa_oaep_md:sha256",
            "-outform",
            "DER",
        ],
        data=archive(content),
        timeout=300,
    ).stdout


def unseal(ciphertext_path, key_path):
    """Decrypt with the operator key. OpenSSL may prompt for its passphrase on the terminal."""
    result = run(
        [
            "openssl",
            "cms",
            "-decrypt",
            "-binary",
            "-inform",
            "DER",
            "-in",
            str(ciphertext_path),
            "-inkey",
            str(key_path),
        ],
        timeout=300,
    )
    return members(result.stdout)
