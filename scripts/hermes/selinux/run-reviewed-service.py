#!/usr/bin/env python3
"""One approved late-service trial. Never retry, reboot, or alter policy."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

UNIT = "systemd-tpm2-setup.service"
EXE = "/usr/lib/systemd/systemd-tpm2-setup"
DOMAIN = "hermes_tpm2_setup_t"
LOADED_HASH = "1055f582b19e650040870d799e8ab3cc44ccc56b9c59d6207ddadd969450c34a"
TRIAL = Path("/var/lib/hermes-selinux-trial-20260909/service-first")


def command(*args, allowed=(0,)):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    if result.returncode not in allowed:
        raise RuntimeError("Command failed: " + args[0])
    return result.stdout


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    p = Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size == 0:
        raise RuntimeError("Missing or unexpected recovery file: " + str(p))
    return digest(p.read_bytes())


def snapshot():
    srk = {}
    for directory in ("/run/systemd", "/var/lib/systemd"):
        for suffix in ("pem", "tpm2b_public"):
            path = directory + "/tpm2-srk-public-key." + suffix
            srk[path] = file_hash(path)
    anchors = {}
    for path in ("/run/systemd/nvpcr/nvpcr-anchor.cred", "/var/lib/systemd/nvpcr/nvpcr-anchor.cred"):
        anchors[path] = file_hash(path)
    boot_paths = {command("bootctl", arg).decode().strip()
                  for arg in ("--print-esp-path", "--print-boot-path")}
    for boot in boot_paths:
        directory = Path(boot) / "loader/credentials"
        if directory.is_dir():
            for path in directory.iterdir():
                name = path.name.lower()
                if name.startswith("nvpcr-anchor.") and name.endswith(".cred"):
                    anchors[str(path)] = file_hash(path)
    metadata = json.loads(command("cryptsetup", "luksDump", "--dump-json-metadata", "/dev/nvme0n1p3"))
    return {"srk": srk, "anchors": anchors,
            "luks_metadata": digest(json.dumps(metadata, sort_keys=True).encode()),
            "firmware": digest(command("efibootmgr", "-v")),
            "loaded_policy": digest(Path("/sys/fs/selinux/policy").read_bytes()),
            "label": command("stat", "-c", "%C", EXE).decode().strip(),
            "enforcing": command("getenforce").decode().strip()}


def acceptance(before, after, status, domains, avcs, audit_ok):
    anchors = after["anchors"]
    return {"service_exit_zero": status.get("ExecMainStatus") == "0" and status.get("Result") == "success",
            "actual_domain_observed": DOMAIN in domains,
            "no_scoped_avcs": not avcs,
            "audit_collection_intact": audit_ok,
            "esp_anchor_present": any(p.startswith(("/boot/", "/efi/")) for p in anchors),
            "anchor_copies_match": bool(anchors) and len(set(anchors.values())) == 1,
            "prior_anchors_preserved": all(anchors.get(p) == h for p, h in before["anchors"].items()),
            **{name + "_preserved": before[name] == after[name]
               for name in ("srk", "luks_metadata", "firmware", "loaded_policy", "label")},
            "enforcing": after["enforcing"] == "Enforcing"}


def audit_status():
    return dict(line.split(None, 1) for line in command("auditctl", "-s").decode().splitlines() if " " in line)


def query_audit(timestamp, destination):
    result = subprocess.run(["ausearch", "-m", "AVC,USER_AVC", "-ts", *timestamp, "--raw"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    (destination / "audit-query.json").write_text(json.dumps({
        "timestamp_arguments": timestamp, "returncode": result.returncode,
        "stderr": result.stderr.decode(errors="replace")}, indent=2) + "\n")
    if result.returncode == 1:
        if (result.stdout + result.stderr).strip() != b"<no matches>":
            raise RuntimeError("Audit query failed; absence of denials is unverified")
    elif result.returncode != 0 or result.stderr.strip():
        raise RuntimeError("Audit query failed; absence of denials is unverified")
    return result.stdout.decode()


def main():
    if sys.argv[1:] != ["--approved-first-run"]:
        raise RuntimeError("Usage: run-reviewed-service.py --approved-first-run")
    if os.geteuid() != 0:
        raise RuntimeError("Operator sudo required")
    os.umask(0o077)
    os.environ["PATH"] = "/usr/sbin:/usr/bin:/sbin:/bin"
    os.environ["LC_ALL"] = "C"
    if command("hostname", "-s").strip() != b"hermes":
        raise RuntimeError("Unexpected host")
    TRIAL.mkdir(mode=0o700)
    before = snapshot()
    if before["loaded_policy"] != LOADED_HASH or before["enforcing"] != "Enforcing":
        raise RuntimeError("Loaded policy or enforcing drift; service not run")
    if before["label"] != "system_u:object_r:hermes_tpm2_setup_exec_t:s0":
        raise RuntimeError("Executable context drift; service not run")
    backup = Path("/var/lib/hermes-selinux-trial-20260909")
    if before["firmware"] != file_hash(backup / "firmware.before"):
        raise RuntimeError("Firmware differs from installation backup; service not run")
    for name in ("/run/systemd/nvpcr/nvpcr-anchor.cred", "/var/lib/systemd/nvpcr/nvpcr-anchor.cred"):
        if before["anchors"][name] != file_hash(backup / name.lstrip("/")):
            raise RuntimeError("Anchor differs from installation backup; service not run")
    audit_before = audit_status()
    if audit_before.get("enabled") not in ("1", "2") or audit_before.get("pid", "0") == "0" or not audit_before.get("lost", "").isdigit():
        raise RuntimeError("Audit collection unavailable; service not run")
    if command("systemctl", "show", "-p", "MainPID", "--value", UNIT).strip() != b"0":
        raise RuntimeError("Service already running")
    (TRIAL / "before.json").write_text(json.dumps(before, indent=2) + "\n")
    (TRIAL / "audit-before.json").write_text(json.dumps(audit_before, indent=2) + "\n")
    start = time.time()
    timestamp = datetime.datetime.fromtimestamp(start).strftime("%m/%d/%y %H:%M:%S").split()
    domains = set()
    with (TRIAL / "restart.log").open("wb") as log:
        process = subprocess.Popen(["systemctl", "restart", UNIT], stdout=log, stderr=log)
        while process.poll() is None:
            for directory in Path("/proc").glob("[0-9]*"):
                try:
                    if os.readlink(directory / "exe") == EXE:
                        context = (directory / "attr/current").read_text().strip().strip("\x00")
                        domains.add(context.split(":")[2])
                except (OSError, IndexError):
                    pass
            if time.time() - start > 120:
                process.terminate()
                process.wait(timeout=10)
                raise RuntimeError("Observation timeout; inspect service manually, do not retry")
            time.sleep(0.002)
    (TRIAL / "process-observation.json").write_text(json.dumps({
        "start_epoch": start, "restart_returncode": process.returncode,
        "observed_domains": sorted(domains)}, indent=2) + "\n")
    after = snapshot()
    (TRIAL / "after.json").write_text(json.dumps(after, indent=2) + "\n")
    status = dict(line.split("=", 1) for line in command("systemctl", "show", "-p", "ExecMainStatus",
                  "-p", "Result", "-p", "ActiveState", UNIT).decode().splitlines())
    (TRIAL / "service-status.json").write_text(json.dumps(status, indent=2) + "\n")
    time.sleep(2)
    raw = query_audit(timestamp, TRIAL)
    avcs = []
    for line in raw.splitlines():
        if ("type=AVC " in line or "type=USER_AVC " in line) and (
                DOMAIN in line or 'comm="systemd-tpm2' in line or EXE in line):
            avcs.append(line)
    audit_after = audit_status()
    audit_ok = (audit_before.get("lost") == audit_after.get("lost")
                and audit_after.get("enabled") in ("1", "2") and audit_after.get("pid", "0") != "0"
                and audit_after.get("backlog") == "0")
    checks = acceptance(before, after, status, domains, avcs, audit_ok)
    checks["restart_command_zero"] = process.returncode == 0
    summary = {"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "checks": checks, "passed": all(checks.values()), "status": status,
               "observed_domains": sorted(domains), "scoped_avc_count": len(avcs)}
    (TRIAL / "after.json").write_text(json.dumps(after, indent=2) + "\n")
    (TRIAL / "scoped-avcs.log").write_text("\n".join(avcs) + "\n")
    (TRIAL / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print("STOP: " + str(error) + "; preserve trial evidence; do not repeat or reboot", file=sys.stderr)
        sys.exit(1)
