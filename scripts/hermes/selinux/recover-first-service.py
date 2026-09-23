#!/usr/bin/env python3
"""Recover evidence from the failed first run; never restart or change policy."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys
import tarfile

ORIGINAL_HASH = "c5eb5fce4a16d65d0ae2618ee5a9ad2ed7e53b85157b1685186d8c982434ca5d"
STAGED = Path("/home/aicowork/hermes-selinux-trial-20260909/run-reviewed-service.py")
DEST = Path("/var/lib/hermes-selinux-trial-20260909/service-first-recovery")
EXPORT = Path("/home/aicowork/hermes-selinux-service-recovery-20260909")


def main():
    if len(sys.argv) != 1 or os.geteuid() != 0:
        raise RuntimeError("Run with operator sudo, without arguments")
    os.umask(0o077)
    os.environ["PATH"] = "/usr/sbin:/usr/bin:/sbin:/bin"
    os.environ["LC_ALL"] = "C"
    source = STAGED.read_bytes()
    if hashlib.sha256(source).hexdigest() != ORIGINAL_HASH:
        raise RuntimeError("Original staged helper changed")
    # Execute only the verified bytes, with the main guard disabled; use snapshot utilities only.
    module = {"__name__": "original_trial"}
    exec(compile(source, str(STAGED), "exec"), module)
    command, snapshot, acceptance = module["command"], module["snapshot"], module["acceptance"]
    if command("hostname", "-s").strip() != b"hermes":
        raise RuntimeError("Unexpected host")
    DEST.mkdir(mode=0o700)
    EXPORT.mkdir(mode=0o700)
    before = json.loads((module["TRIAL"] / "before.json").read_text())
    current = snapshot()
    (DEST / "current.json").write_text(json.dumps(current, indent=2) + "\n")
    # Preserve encrypted post-run anchors before any separately controlled policy rollback.
    for name in current["anchors"]:
        target = DEST / "encrypted-anchors" / name.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copyfile(name, target)
    status = dict(line.split("=", 1) for line in command("systemctl", "show", "-p", "ExecMainStatus",
                  "-p", "Result", "-p", "ActiveState", "-p", "ExecMainStartTimestamp", module["UNIT"]).decode().splitlines())
    # Exact failed-run window; C locale uses a two-digit year for ausearch.
    query = ["ausearch", "-m", "AVC,USER_AVC", "-ts", "09/09/26", "09:43:10",
             "-te", "09/09/26", "09:43:25", "--raw"]
    result = subprocess.run(query, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    combined = (result.stdout + result.stderr).strip()
    query_ok = (result.returncode == 0 and not result.stderr.strip()) or (result.returncode == 1 and combined == b"<no matches>")
    (DEST / "audit-query-stderr.txt").write_bytes(result.stderr)
    lines = [line for line in result.stdout.decode(errors="replace").splitlines()
             if ("type=AVC " in line or "type=USER_AVC " in line)
             and (module["DOMAIN"] in line or 'comm="systemd-tpm2' in line or module["EXE"] in line)]
    (DEST / "scoped-avcs.log").write_text("\n".join(lines) + "\n")
    domains = set()
    denied = []
    for line in lines:
        match = re.search(r"scontext=([^ ]+)", line)
        if match and len(match[1].split(":")) >= 3:
            domains.add(match[1].split(":")[2])
        fields = {}
        for key in ("scontext", "tcontext", "tclass", "permissive"):
            match = re.search(r"\b" + key + r"=([^ ]+)", line)
            if match:
                fields[key] = match[1]
        match = re.search(r"denied\s+\{([^}]+)\}", line)
        if match:
            fields["denied"] = match[1].strip().split()
        denied.append(fields)
    checks = acceptance(before, current, status, domains, lines, False)
    summary = {"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "passed": False, "reason": "First service run failed; this is read-only recovery, not a retry",
               "audit_query_returncode": result.returncode, "audit_query_parsed": query_ok,
               "status_now": status, "current_checks": checks, "scoped_denials": denied,
               "limits": ["Original process polling and audit-before observations were not saved",
                          "Current snapshot is recovery-time state, not original post-run state",
                          "No policy rollback, restart or reboot was performed"]}
    (DEST / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    archive = EXPORT / "recovery.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(DEST, arcname="recovery")
        bundle.add(module["TRIAL"], arcname="original-trial")
    account = pwd.getpwnam("aicowork")
    os.chown(archive, account.pw_uid, account.pw_gid)
    os.chown(EXPORT, account.pw_uid, account.pw_gid)
    print(json.dumps(summary, indent=2))
    print("RECOVERY_SHA256=" + hashlib.sha256(archive.read_bytes()).hexdigest())
    return 0 if query_ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print("STOP: " + str(error) + "; no service restart requested", file=sys.stderr)
        sys.exit(1)
