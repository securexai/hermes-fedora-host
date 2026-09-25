#!/usr/bin/env python3
"""Publish only the fixed host grant after the DeepSeek guest grant is proven.

The original guest-agent bootstrap cannot write the guest sudoers path under
its SELinux context. This finalizer checks the separately installed guest
grant and exact interrupted host copy before publishing the host sudoers rule.
"""

import argparse
import hashlib
import os
import subprocess
import sys
import types
from pathlib import Path
from typing import NoReturn

GRANT_SOURCE = Path(__file__).with_name("deepseek-test-grant.py")
GRANT_SOURCE_SHA256 = "e9fffae62535e3714c4d406f3359c41218d9e6d9411e98bc84ad8c82e638fd39"
BUNDLE_SHA256 = "5f50714513b98005a02d6f111db4e074c50f1e640fc6edafd2f2dc69c9aae068"


def stop(message: str) -> NoReturn:
    raise RuntimeError(message)


def grant_module():
    if GRANT_SOURCE.is_symlink() or not GRANT_SOURCE.is_file():
        stop("reviewed grant source missing")
    source = GRANT_SOURCE.read_bytes()
    if hashlib.sha256(source).hexdigest() != GRANT_SOURCE_SHA256:
        stop("reviewed grant source changed")
    module = types.ModuleType("deepseek_test_grant")
    module.__file__ = str(GRANT_SOURCE)
    exec(compile(source, str(GRANT_SOURCE), "exec"), module.__dict__)
    return module


def verify_host_copy(grant, source: Path, inspector: Path, package: bytes) -> None:
    for parent in (Path("/var"), Path("/var/usrlocal"), Path("/var/usrlocal/libexec")):
        grant.trusted(parent)
    grant.trusted(grant.HOST_BASE, 0o755)
    expected = {
        grant.HOST_BASE / "access.py": source.read_bytes(),
        grant.HOST_BASE / "boot-inspect.py": inspector.read_bytes(),
        grant.HOST_BASE / "bundle.tar": package,
    }
    if set(grant.HOST_BASE.iterdir()) != set(expected):
        stop("host access directory differs")
    for path, content in expected.items():
        grant.trusted(path, 0o644)
        if not path.is_file() or path.read_bytes() != content:
            stop(f"installed host file differs: {path}")


def guest_read(grant, *remote: str) -> str:
    return grant.run(*grant.ssh_command(*remote), timeout=25)


def verify_guest_grant(grant) -> None:
    if grant.bound_vm() != "running":
        stop("approved VM must be running")
    grant.bound_network()
    grant.guest_identity()
    grant.verify_client_state()
    status = guest_read(
        grant,
        "sudo",
        "-n",
        "/usr/bin/python3",
        "-I",
        str(grant.GUEST_BASE / "access.py"),
        "guest",
        "status",
    )
    if status != f"guest_machine_sha256={grant.MACHINE_SHA256} bundle_present=True":
        stop("guest fixed status or bundle differs")
    code = grant.GUEST_BASE / "access.py"
    pin = Path("/etc/hermes-deepseek-test/bundle.sha256")
    expected_code_hash = GRANT_SOURCE_SHA256
    for path, expected_hash in (
        (code, expected_code_hash),
        (pin, hashlib.sha256((BUNDLE_SHA256 + "\n").encode()).hexdigest()),
    ):
        output = guest_read(grant, "/usr/bin/sha256sum", str(path))
        if output != f"{expected_hash}  {path}":
            stop(f"guest file hash differs: {path}")
        ownership = guest_read(grant, "/usr/bin/stat", "-c", "%u:%g:%a", str(path))
        if ownership != "0:0:644":
            stop(f"guest file ownership or mode differs: {path}")
    listing = guest_read(grant, "sudo", "-n", "-l")
    observed = [
        line.split("NOPASSWD: ", 1)[1] for line in listing.splitlines() if "NOPASSWD: " in line
    ]
    expected = grant.rule("guest").decode().split("NOPASSWD: ", 1)[1].strip()
    if observed != [expected]:
        stop("guest NOPASSWD listing differs")


def install(grant) -> None:
    if os.geteuid() != 0 or os.environ.get("SUDO_USER") != grant.HOST_USER:
        stop("private workstation administrator bootstrap required")
    grant.check()
    source, inspector, manual = grant.source_files()
    package = grant.archive(manual)
    if grant.digest(package) != BUNDLE_SHA256:
        stop("reviewed manual bundle changed")
    verify_host_copy(grant, source, inspector, package)
    verify_guest_grant(grant)
    content = grant.rule("host")
    grant.check_rule(content)
    if grant.HOST_RULE.exists() or grant.HOST_RULE.is_symlink():
        grant.trusted(grant.HOST_RULE, 0o440)
        if grant.HOST_RULE.read_bytes() != content:
            stop("existing host sudoers rule differs")
        grant.run("/usr/sbin/restorecon", str(grant.HOST_RULE))
        grant.run("/usr/sbin/visudo", "-cf", str(grant.HOST_RULE))
        print("HOST_GRANT_UNCHANGED")
        return
    grant.installed_file(grant.HOST_RULE, content, 0o440)
    grant.run("/usr/sbin/restorecon", str(grant.HOST_RULE))
    grant.run("/usr/sbin/visudo", "-cf", str(grant.HOST_RULE))
    grant.run(
        "/usr/bin/logger", "-t", "hermes-deepseek-test", "host action=bootstrap result=success"
    )
    print("HOST_GRANT_INSTALLED bundle_sha256=" + BUNDLE_SHA256)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "install"))
    args = parser.parse_args()
    grant = grant_module()
    if args.action == "check":
        grant.check()
        print("HOST_FINALIZE_CHECK=PASS fixed_vm=" + grant.DOMAIN)
    else:
        install(grant)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
