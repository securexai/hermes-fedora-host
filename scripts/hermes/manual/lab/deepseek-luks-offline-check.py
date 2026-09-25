#!/usr/bin/env python3
"""Check a privately entered LUKS passphrase against this VM's header backups.

The archived headers are read into anonymous memory. The passphrase is entered
once through KDE, sent to cryptsetup on stdin with its terminal newline removed,
and never written to a file, argument, environment variable or log.
"""

import argparse
import hashlib
import os
import pwd
import stat
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import NoReturn

ACCOUNT = "aicloudopspecial"
BASE = Path("/var/home/aicloudopspecial/.local/share/hermes-recovery/lab-hermes-deepseek-e2e-r1")
ARCHIVES = (
    (
        "PRE",
        "pre-tpm-recovery.tar",
        "63b0c072fc9fccec110e54fe3f73be0c3fb2e7c4be67cc49fa667b22e9cc9060",
        "vda3-pre-tpm-e2e.header",
    ),
    (
        "POST",
        "post-tpm-staged.tar",
        "0bd7a5bed3fb9dd693f61abd6c9d4cfc46798ed028495d5c33f696e15ac20d7a",
        "./vda3-tpm-20260924T024955Z.header",
    ),
)
HEADER_SIZE = 16_777_216


def stop(message: str) -> NoReturn:
    raise RuntimeError(message)


def header_from_archive(name: str, expected_hash: str, member_name: str) -> bytes:
    path = BASE / name
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            stop(f"untrusted recovery archive: {name}")
        if stat.S_IMODE(info.st_mode) != 0o600 or info.st_size != 16_783_360:
            stop(f"recovery archive mode or size differs: {name}")
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected_hash:
            stop(f"recovery archive hash differs: {name}")
        stream.seek(0)
        with tarfile.open(fileobj=stream, mode="r:") as archive:
            member = archive.getmember(member_name)
            if not member.isfile() or member.size != HEADER_SIZE:
                stop(f"recovery header member differs: {name}")
            source = archive.extractfile(member)
            if source is None:
                stop(f"recovery header unreadable: {name}")
            header = source.read(HEADER_SIZE + 1)
            if len(header) != HEADER_SIZE:
                stop(f"recovery header length differs: {name}")
            return header


def test_header(header: bytes, key: bytes) -> bool:
    fd = os.memfd_create("hermes-luks-header", os.MFD_CLOEXEC)
    try:
        view = memoryview(header)
        offset = 0
        while offset < len(header):
            written = os.write(fd, view[offset:])
            if written <= 0:
                stop("cannot load recovery header into memory")
            offset += written
        result = subprocess.run(
            [
                "/usr/bin/cryptsetup",
                "open",
                "--test-passphrase",
                "--tries=1",
                "--key-file=-",
                f"/proc/self/fd/{fd}",
            ],
            input=key,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            pass_fds=(fd,),
            timeout=30,
            check=False,
        )
        if result.returncode not in (0, 2):
            stop("cryptsetup could not evaluate the backup header")
        return result.returncode == 0
    finally:
        os.close(fd)


def askpass() -> bytearray:
    result = subprocess.run(
        ["/usr/bin/ksshaskpass", "LUKS recovery passphrase for lab-hermes-deepseek-e2e-r1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        stop("private LUKS prompt canceled or failed")
    value = bytearray(result.stdout)
    if value.endswith(b"\n"):
        del value[-1:]
    if not value or len(value) > 4096 or b"\n" in value or b"\x00" in value:
        stop("private LUKS input length or form is invalid")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "check"))
    args = parser.parse_args()
    if os.geteuid() != pwd.getpwnam(ACCOUNT).pw_uid:
        stop("run as the workstation owner without sudo")
    headers = [
        (label, header_from_archive(name, digest, member))
        for label, name, digest, member in ARCHIVES
    ]
    for label, header in headers:
        if test_header(header, b"known-invalid-synthetic-key"):
            stop(f"synthetic wrong-key control unexpectedly passed: {label}")
    print("OFFLINE_HEADER_PREFLIGHT=PASS archives=2 synthetic_wrong_key=rejected")
    if args.action == "preflight":
        return
    key = askpass()
    try:
        for label, header in headers:
            print(
                f"{label}_HEADER_PASSPHRASE_MATCH="
                + ("PASS" if test_header(header, bytes(key)) else "FAIL")
            )
    finally:
        key[:] = b"\x00" * len(key)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired, tarfile.TarError, KeyError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
