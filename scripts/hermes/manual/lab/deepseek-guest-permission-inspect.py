#!/usr/bin/env python3
"""Read-only, fixed-identity inspection of the failed DeepSeek guest grant path."""

import ast
import hashlib
import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path

HOST_USER = "aicloudopspecial"
GRANT_PATH = Path(__file__).with_name("deepseek-test-grant.py")
GRANT_SHA256 = "e9fffae62535e3714c4d406f3359c41218d9e6d9411e98bc84ad8c82e638fd39"

GUEST_INSPECT = r"""
import os
import stat
from pathlib import Path

print('guest_euid=' + str(os.geteuid()))
print('process_context=' + Path('/proc/self/attr/current').read_text().rstrip('\x00\n'))
for name in ('/usr', '/usr/local', '/usr/local/libexec',
             '/usr/local/libexec/hermes-deepseek-test',
             '/etc', '/etc/hermes-deepseek-test',
             '/etc/sudoers.d/90-hermes-deepseek-test-guest'):
    path = Path(name)
    try:
        info = path.lstat()
    except FileNotFoundError:
        print(name + ' absent')
        continue
    try:
        label = os.getxattr(path, 'security.selinux').decode(errors='replace').rstrip('\x00')
    except OSError as exc:
        label = 'unavailable_errno_' + str(exc.errno)
    flags = os.statvfs(path).f_flag
    print(name + ' uid=' + str(info.st_uid) + ' mode=' + oct(stat.S_IMODE(info.st_mode))
          + ' label=' + label + ' readonly=' + str(bool(flags & os.ST_RDONLY)))
"""


def main() -> None:
    if hashlib.sha256(GRANT_PATH.read_bytes()).hexdigest() != GRANT_SHA256:
        raise RuntimeError("grant source differs from reviewed pin")
    ast.parse(GUEST_INSPECT)
    if sys.argv[1:] == ["check"]:
        print("CHECK=PASS fixed guest permission inspector")
        return
    if sys.argv[1:] != ["inspect"]:
        raise RuntimeError("expected check or inspect")
    if os.geteuid() != 0 or os.environ.get("SUDO_USER") != HOST_USER:
        raise RuntimeError("private workstation administrator authentication required")
    spec = importlib.util.spec_from_file_location("deepseek_grant", GRANT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load reviewed grant")
    grant = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grant)
    inspect_and_shutdown(grant)


def inspect_and_shutdown(grant) -> None:
    state = grant.bound_vm()
    if state not in ("shut off", "running"):
        raise RuntimeError(f"cannot inspect exact VM from state {state}")
    try:
        if state == "shut off":
            print(grant.virsh("start", grant.DOMAIN))
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if grant.bound_vm() != "running":
                raise RuntimeError("exact VM stopped before inspection")
            try:
                grant.bound_network()
                grant.guest_identity()
                break
            except (
                OSError,
                RuntimeError,
                subprocess.CalledProcessError,
                subprocess.TimeoutExpired,
            ):
                time.sleep(2)
        else:
            raise RuntimeError("exact VM did not reach pinned guest identity")
        print(grant.guest_script(GUEST_INSPECT), end="")
    finally:
        if grant.bound_vm() == "running":
            print(grant.virsh("shutdown", grant.DOMAIN))
        for _ in range(60):
            if grant.bound_vm() == "shut off":
                print("VM_FINAL_STATE=shut off")
                break
            time.sleep(2)
        else:
            raise RuntimeError("exact VM shutdown unverified")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
