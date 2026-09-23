#!/usr/bin/env python3
"""Export the approved v2 installed policy and encrypted installation backups only."""
import hashlib
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys
import tarfile

BACKUP = Path("/var/lib/hermes-selinux-trial-20260909-v2")
EXPORT = Path("/home/aicowork/hermes-selinux-export-20260909-v2")
LOADED = Path("/sys/fs/selinux/policy")
POLICY = Path("/etc/selinux/targeted/policy/policy.35")
EXPECTED = "84e62bca8dbd0439593c7fbf44f795a9f1a3d5b461f5a174baf35c9346678360"
MODULE = "37643c3428ee847e82643056142d1ff5702d7249ed8046e71326c1e01b00a6b8"
BASE = "bf58d5f5ae23502d844f70c153ef5366c31bf16ac9c77f548b94f3cf1aea1949"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, timeout=60).stdout


def main():
    if sys.argv[1:] != ["--approved-policy-export"]:
        raise RuntimeError("Expected --approved-policy-export")
    if os.geteuid() != 0:
        raise RuntimeError("Operator sudo required")
    os.umask(0o077)
    os.environ["PATH"] = "/usr/sbin:/usr/bin:/sbin:/bin"
    os.environ["LC_ALL"] = "C"
    if command("hostname", "-s").strip() != b"hermes":
        raise RuntimeError("Unexpected host")
    if digest(POLICY) != EXPECTED or command("getenforce").strip() != b"Enforcing":
        raise RuntimeError("Installed policy/enforcing mismatch")
    label = b"system_u:object_r:hermes_tpm2_setup_exec_t:s0"
    exe = "/usr/lib/systemd/systemd-tpm2-setup"
    if command("stat", "-c", "%C", exe).strip() != label or command("matchpathcon", "-n", exe).strip() != label:
        raise RuntimeError("Executable context mismatch")
    # Exact installation metadata and encrypted anchors; never export arbitrary state directories.
    names = ["modules.before", "targeted-active.tar.gz", "policy.before", "executable-context.before",
             "boot.before", "firmware.before", "journal-cursor.before", "candidate.pp", "installation-started",
             "run/systemd/nvpcr/nvpcr-anchor.cred", "var/lib/systemd/nvpcr/nvpcr-anchor.cred"]
    files = {BACKUP / name for name in names}
    files.update(BACKUP.glob("boot/**/nvpcr-anchor.*.cred"))
    files.update(BACKUP.glob("efi/**/nvpcr-anchor.*.cred"))
    for path in files:
        if not path.is_file() or path.stat().st_size == 0 or any(p.is_symlink() for p in [path, *path.parents]):
            raise RuntimeError("Missing or unsafe installation backup")
    if digest(BACKUP / "candidate.pp") != MODULE or digest(BACKUP / "policy.before") != BASE:
        raise RuntimeError("Installation backup mismatch")
    account = pwd.getpwnam("aicowork")
    EXPORT.mkdir(mode=0o700)  # Exclusive; preserve previous results on rerun.
    loaded = EXPORT / "loaded-policy.35"
    loaded.write_bytes(LOADED.read_bytes())
    archive = EXPORT / "recovery.tar.gz"
    with tarfile.open(archive, "w:gz", dereference=True) as output:
        for path in sorted(files):
            output.add(path, arcname=str(path.relative_to(BACKUP)), recursive=False)
    status = command("systemctl", "show", "-p", "ActiveState", "-p", "MainPID", "-p", "ExecMainStatus",
                     "-p", "ExecMainStartTimestamp", "systemd-tpm2-setup.service", "systemd-tpm2-setup-early.service")
    (EXPORT / "service-state.txt").write_bytes(status)
    result = {"loaded_policy_sha256": digest(loaded), "recovery_sha256": digest(archive),
              "backup_file_count": len(files), "export_directory": str(EXPORT),
              "scope": "export only; loaded-policy semantic verification remains required"}
    (EXPORT / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    for path in EXPORT.iterdir():
        os.chmod(path, 0o600)
        os.chown(path, account.pw_uid, account.pw_gid)
    os.chown(EXPORT, account.pw_uid, account.pw_gid)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("STOP: " + str(error) + "; preserve results; no service restart or reboot", file=sys.stderr)
        sys.exit(1)
