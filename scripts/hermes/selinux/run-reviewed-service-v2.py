#!/usr/bin/env python3
"""One separately approved v2 late-service trial; preserve evidence and never recover automatically."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

UNIT = "systemd-tpm2-setup.service"
EARLY = "systemd-tpm2-setup-early.service"
EXE = "/usr/lib/systemd/systemd-tpm2-setup"
DOMAIN = "hermes_tpm2_setup_t"
LABEL = "system_u:object_r:hermes_tpm2_setup_exec_t:s0"
BACKUP = Path("/var/lib/hermes-selinux-trial-20260909-v2")
TRIAL = BACKUP / "service-first"
LOADED_HASH = "28f3153377e6b7065dcf0e235936ffa360b1f1fdf1e68896f5fda681e020487e"
DISK_HASH = "84e62bca8dbd0439593c7fbf44f795a9f1a3d5b461f5a174baf35c9346678360"
# Public hashes from the independently verified v2 recovery export; no credential contents.
BACKUP_HASHES = {
    "candidate.pp": "37643c3428ee847e82643056142d1ff5702d7249ed8046e71326c1e01b00a6b8",
    "policy.before": "bf58d5f5ae23502d844f70c153ef5366c31bf16ac9c77f548b94f3cf1aea1949",
    "targeted-active.tar.gz": "1623077e2f24d57ff9cfd3f85ea71f445849e589cec1135e53fedc7af2532879",
    "firmware.before": "93788cd5e4d64661356d6a152c1faf86bc69023f717e532c14d0b20909786f89",
    "run/systemd/nvpcr/nvpcr-anchor.cred": "62ebf942a151100b883fcb8c41eaf37ad98e2a1f33b820ff4e0386d462064dd7",
    "var/lib/systemd/nvpcr/nvpcr-anchor.cred": "62ebf942a151100b883fcb8c41eaf37ad98e2a1f33b820ff4e0386d462064dd7",
}
ANCHORS = ("/run/systemd/nvpcr/nvpcr-anchor.cred", "/var/lib/systemd/nvpcr/nvpcr-anchor.cred")
PACKAGES = "selinux-policy-44.8-1.fc44.noarch\nselinux-policy-targeted-44.8-1.fc44.noarch\nsystemd-259.8-1.fc44.x86_64"
STARTS = {UNIT: "Wed 2026-09-09 09:43:14 -05", EARLY: "Tue 2026-09-08 22:19:12 -05"}
HOOKS = ("ExecCondition", "ExecStartPre", "ExecStartPost", "ExecStop", "ExecStopPost")
PROPERTIES = (
    "LoadState", "ActiveState", "SubState", "MainPID", "ControlPID", "Result", "ExecMainCode",
    "ExecMainStatus", "ExecMainStartTimestamp", "InvocationID", "ConditionResult", "AssertResult",
    "Type", "Restart", "ExecStart", *HOOKS,
    "Requires", "Wants", "Requisite", "BindsTo", "Conflicts", "OnFailure", "OnSuccess",
    "FailureAction", "SuccessAction", "StartLimitAction", "JobTimeoutAction",
    "ConsistsOf", "BoundBy", "PropagatesStopTo", "Upholds",
)


def command(*args):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    if result.returncode:
        raise RuntimeError("Command failed: " + args[0])
    return result.stdout


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_file(path):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise RuntimeError("Symlink in evidence input")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size == 0:
        raise RuntimeError("Missing or unexpected evidence input")
    return path


def file_hash(path):
    return digest(safe_file(path).read_bytes())


def save(name, value):
    # TRIAL is created exclusively beneath the checked root-private installation backup.
    with (TRIAL / name).open("w", encoding="utf-8") as output:
        json.dump(value, output, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())


def unit_state(unit):
    args = ["systemctl", "show", "--all", unit]
    for prop in PROPERTIES:
        args.extend(("-p", prop))
    pairs = [line.split("=", 1) for line in command(*args).decode().splitlines()]
    result = dict(pairs)
    if len(pairs) != len(result):
        raise RuntimeError("Repeated unit property; multiple commands are not approved")
    # Even --all omits empty Exec* arrays. Verify their typed D-Bus values instead of assuming empty.
    missing_hooks = [name for name in HOOKS if name not in result]
    if missing_hooks:
        encoded = "".join(char if char.isascii() and char.isalnum() else f"_{ord(char):02x}" for char in unit)
        values = command("busctl", "get-property", "org.freedesktop.systemd1",
                         "/org/freedesktop/systemd1/unit/" + encoded,
                         "org.freedesktop.systemd1.Service", *missing_hooks).decode().splitlines()
        if values != ["a(sasbttttuii) 0"] * len(missing_hooks):
            raise RuntimeError("Missing command property is not a verified empty array")
        result.update({name: "" for name in missing_hooks})
    if any(prop not in result for prop in PROPERTIES):
        raise RuntimeError("Incomplete unit observation")
    return result


def snapshot():
    srk = {f"{directory}/tpm2-srk-public-key.{suffix}":
           file_hash(f"{directory}/tpm2-srk-public-key.{suffix}")
           for directory in ("/run/systemd", "/var/lib/systemd") for suffix in ("pem", "tpm2b_public")}
    boot_paths = {key: command("bootctl", option).decode().strip() for key, option in
                  (("esp", "--print-esp-path"), ("boot", "--print-boot-path"))}
    anchors = {path: file_hash(path) for path in ANCHORS}
    for boot in set(boot_paths.values()):
        if boot not in ("/boot", "/boot/efi", "/efi"):
            raise RuntimeError("Unreviewed boot mount path")
        directory = Path(boot) / "loader/credentials"
        if any(p.is_symlink() for p in (directory, *directory.parents)):
            raise RuntimeError("Symlink in boot credential path")
        if directory.is_dir():
            for path in sorted(directory.iterdir()):
                if path.name.lower().startswith("nvpcr-anchor.") and path.name.lower().endswith(".cred"):
                    anchors[str(path)] = file_hash(path)
    metadata = json.loads(command("cryptsetup", "luksDump", "--dump-json-metadata", "/dev/nvme0n1p3"))
    return {
        "srk": srk, "anchors": anchors, "boot_paths": boot_paths,
        "luks_metadata": digest(json.dumps(metadata, sort_keys=True).encode()),
        "firmware": digest(command("efibootmgr", "-v")),
        "boot_status": digest(command("bootctl", "status")),
        "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "cmdline": digest(Path("/proc/cmdline").read_bytes()),
        "loaded_policy": digest(Path("/sys/fs/selinux/policy").read_bytes()),
        "disk_policy": file_hash("/etc/selinux/targeted/policy/policy.35"),
        "label": command("stat", "-c", "%C", EXE).decode().strip(),
        "mapping": command("matchpathcon", "-n", EXE).decode().strip(),
        "enforcing": command("getenforce").decode().strip(),
        "packages": command("rpm", "-q", "selinux-policy", "selinux-policy-targeted", "systemd").decode().strip(),
        "units": {unit: unit_state(unit) for unit in (UNIT, EARLY)},
    }


def audit_status():
    return dict(line.split(None, 1) for line in command("auditctl", "-s").decode().splitlines() if " " in line)


def audit_healthy(value):
    return (value.get("enabled") in ("1", "2") and value.get("pid", "0").isdigit()
            and int(value.get("pid", "0")) > 0 and value.get("lost", "").isdigit()
            and value.get("backlog") == "0")


def audit_timestamp():
    # Verified host parser uses a two-digit year under LC_ALL=C.
    return datetime.datetime.now().strftime("%m/%d/%y %H:%M:%S").split()


def query_audit(timestamp, name):
    result = subprocess.run(["ausearch", "-m", "AVC,USER_AVC", "-ts", *timestamp, "--raw"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    save(name + ".json", {"timestamp_arguments": timestamp, "returncode": result.returncode,
                         "stderr": result.stderr.decode(errors="replace")})
    (TRIAL / (name + ".log")).write_bytes(result.stdout)
    if result.returncode == 1 and (result.stdout + result.stderr).strip() == b"<no matches>":
        return ""
    if result.returncode != 0 or result.stderr.strip() or not result.stdout.strip():
        raise RuntimeError("Audit query failed; absence of denials is unverified")
    return result.stdout.decode()


def preflight(before):
    if (before["loaded_policy"] != LOADED_HASH or before["disk_policy"] != DISK_HASH
            or before["enforcing"] != "Enforcing" or before["label"] != LABEL
            or before["mapping"] != LABEL or before["packages"] != PACKAGES):
        raise RuntimeError("Policy, label or package drift")
    for name, expected in BACKUP_HASHES.items():
        if file_hash(BACKUP / name) != expected:
            raise RuntimeError("Installation backup drift")
    if before["firmware"] != BACKUP_HASHES["firmware.before"]:
        raise RuntimeError("Firmware drift")
    for path in ANCHORS:
        if before["anchors"].get(path) != BACKUP_HASHES[path.lstrip("/")]:
            raise RuntimeError("Anchor drift")
    if set(before["anchors"]) != set(ANCHORS):
        raise RuntimeError("Boot anchor presence differs from verified v2 export")
    for unit, state in before["units"].items():
        if (state["LoadState"] != "loaded" or state["ActiveState"] not in ("active", "inactive", "failed")
                or state["MainPID"] != "0" or state["ControlPID"] != "0"
                or state["ExecMainStartTimestamp"] != STARTS[unit]):
            raise RuntimeError("Setup unit busy or invocation drift")
    # Check effective commands and hooks before making a single-unit request. Do not run a shell.
    state = before["units"][UNIT]
    if (state["Type"] != "oneshot" or state["Restart"] != "no"
            or any(state[name] for name in (*HOOKS, "OnFailure", "OnSuccess", "ConsistsOf", "BoundBy",
                                           "PropagatesStopTo", "Upholds"))
            or any(state[name] != "none" for name in ("FailureAction", "SuccessAction", "StartLimitAction",
                                                       "JobTimeoutAction"))
            or not re.fullmatch(r"\{ path=" + re.escape(EXE) + r" ; argv\[\]=" + re.escape(EXE)
                                + r" --graceful ; ignore_errors=no ;[^{}]*\}", state["ExecStart"])):
        raise RuntimeError("Unreviewed service execution contract")
    # No queued jobs or inactive required units that a normal restart would pull into the transaction.
    if command("systemctl", "list-jobs", "--no-legend", "--no-pager").strip():
        raise RuntimeError("Pending systemd jobs")
    for name in ("Requires", "Wants", "Requisite", "BindsTo", "Conflicts"):
        for unit in state[name].split():
            active = command("systemctl", "show", "-p", "ActiveState", "--value", "--", unit).strip()
            if active not in ((b"inactive", b"failed") if name == "Conflicts" else (b"active",)):
                raise RuntimeError("Service dependency not quiescent")


def preserve_anchors(before, name):
    directory = TRIAL / ("anchors-" + name)
    directory.mkdir(mode=0o700)
    for index, (path, expected) in enumerate(sorted(before["anchors"].items())):
        data = safe_file(path).read_bytes()
        if digest(data) != expected:
            raise RuntimeError("Anchor changed during recovery copy")
        with (directory / f"{index}.cred").open("xb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    save("anchor-backup-map-" + name + ".json", list(sorted(before["anchors"])))


def journal_cursor():
    output = command("journalctl", "-n", "0", "--show-cursor", "--no-pager").decode()
    match = re.search(r"^-- cursor: (\S+)$", output, re.MULTILINE)
    if not match:
        raise RuntimeError("Journal cursor unavailable")
    save("journal-before.json", {"cursor": match[1]})
    return match[1]


def collect_journal(cursor):
    output = command("journalctl", "-u", UNIT, "--after-cursor=" + cursor, "--no-pager", "-o", "short-iso")
    (TRIAL / "service-journal.log").write_bytes(output)
    return {"collected": True}


def sample_domains():
    observations = set()
    for directory in Path("/proc").glob("[0-9]*"):
        try:
            if os.readlink(directory / "exe") != EXE:
                continue
            cgroups = (directory / "cgroup").read_text().splitlines()
            if not any(line.split(":", 2)[-1] == "/system.slice/" + UNIT for line in cgroups):
                continue
            observations.add((directory / "attr/current").read_text().strip().strip("\x00").split(":")[2])
        except (OSError, IndexError):
            continue  # Short-lived process disappeared; absence cannot pass actual-domain acceptance.
    return observations


def observe_service():
    observation = {"request_recorded": True, "restart_returncode": None,
                   "observed_domains": [], "timed_out": False}
    save("process-observation.json", observation)  # Durable intent before the only restart call.
    with (TRIAL / "restart.log").open("xb") as log:
        process = subprocess.Popen(["systemctl", "--job-mode=fail", "restart", UNIT], stdout=log, stderr=log)
        try:
            started = time.monotonic()
            domains = set()
            while True:
                new = sample_domains()
                if new - domains:
                    domains.update(new)
                    observation["observed_domains"] = sorted(domains)
                    save("process-observation.json", observation)
                if process.poll() is not None:
                    break
                if time.monotonic() - started > 120:
                    observation["timed_out"] = True
                    break
                time.sleep(0.002)
        finally:
            # This only terminates our waiting systemctl client; the unit may still be running.
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            observation["restart_returncode"] = process.returncode
            save("process-observation.json", observation)
    return observation


def acceptance(before, after, observation, avcs, audit_before, audit_after):
    state = after["units"][UNIT]
    esp_prefix = after["boot_paths"]["esp"] + "/loader/credentials/"
    anchors = after["anchors"]
    invariant_names = ("srk", "luks_metadata", "firmware", "boot_status", "boot_id", "cmdline", "boot_paths",
                       "loaded_policy", "disk_policy", "label", "mapping", "packages")
    checks = {name + "_preserved": before[name] == after[name] for name in invariant_names}
    checks.update({
        "restart_command_zero": observation["restart_returncode"] == 0 and not observation["timed_out"],
        "service_exit_zero": state["ExecMainCode"] == "1" and state["ExecMainStatus"] == "0"
        and state["Result"] == "success" and state["ActiveState"] == "active" and state["SubState"] == "exited"
        and state["MainPID"] == "0" and state["ControlPID"] == "0",
        "fresh_invocation": bool(re.fullmatch(r"[0-9a-f]{32}", state["InvocationID"]))
        and state["InvocationID"] != "0" * 32
        and state["InvocationID"] != before["units"][UNIT]["InvocationID"]
        and state["ExecMainStartTimestamp"] != before["units"][UNIT]["ExecMainStartTimestamp"]
        and state["ConditionResult"] == "yes" and state["AssertResult"] == "yes",
        "actual_domain_observed": observation["observed_domains"] == [DOMAIN],
        "early_unit_preserved": before["units"][EARLY] == after["units"][EARLY],
        "no_scoped_avcs": not avcs,
        "audit_collection_intact": audit_healthy(audit_before) and audit_healthy(audit_after)
        and all(audit_before.get(key) == audit_after.get(key) for key in ("lost", "pid", "enabled")),
        "esp_anchor_present": any(path.startswith(esp_prefix) for path in anchors),
        "anchor_copies_match": bool(anchors) and len(set(anchors.values())) == 1,
        "prior_anchors_preserved": all(anchors.get(path) == value for path, value in before["anchors"].items()),
        "enforcing": after["enforcing"] == "Enforcing",
    })
    return checks


def trial():
    summary = {"passed": False, "service_requested": False, "checks": {}, "errors": []}
    phase = "preflight"
    try:
        before = snapshot()
        save("before.json", before)
        preflight(before)
        audit_before = audit_status()
        save("audit-before.json", audit_before)
        if not audit_healthy(audit_before):
            raise RuntimeError("Audit collection unavailable")
        timestamp = audit_timestamp()
        query_audit(timestamp, "audit-preflight")  # Verify the host parser before requesting service execution.
        cursor = journal_cursor()
        preserve_anchors(before, "before")
        refreshed = snapshot()
        if refreshed != before:
            raise RuntimeError("State changed during preflight")
        preflight(refreshed)
        refreshed_audit = audit_status()
        save("audit-ready.json", refreshed_audit)
        if (not audit_healthy(refreshed_audit)
                or any(refreshed_audit.get(key) != audit_before.get(key) for key in ("lost", "pid", "enabled"))):
            raise RuntimeError("Audit state changed during preflight")
        phase = "service-observation"
        # A durable request marker is conservative: it cannot prove the unit actually executed.
        summary["service_requested"] = True
        save("summary.json", summary)
        observation = None
        try:
            observation = observe_service()
        except Exception as error:
            summary["errors"].append({"phase": phase, "type": type(error).__name__})
        # Independent collection: an audit/snapshot failure must not discard earlier observations.
        phase = "post-observation"
        collected = {}
        collectors = (("service-status", lambda: {unit: unit_state(unit) for unit in (UNIT, EARLY)}),
                      ("after", snapshot), ("audit-after", audit_status),
                      ("audit-query", lambda: query_audit(timestamp, "audit-query")),
                      ("service-journal", lambda: collect_journal(cursor)))
        time.sleep(2)
        for name, collect in collectors:
            try:
                collected[name] = collect()
                if name != "audit-query":
                    save(name + ".json", collected[name])
            except Exception as error:
                summary["errors"].append({"phase": name, "type": type(error).__name__})
        if "after" in collected:
            try:
                preserve_anchors(collected["after"], "after")
            except Exception as error:
                summary["errors"].append({"phase": "anchor-backup-after", "type": type(error).__name__})
        if observation is not None and len(collected) == len(collectors):
            avcs = [line for line in collected["audit-query"].splitlines()
                    if ("type=AVC " in line or "type=USER_AVC " in line)
                    and (DOMAIN in line or 'comm="systemd-tpm2' in line or EXE in line)]
            (TRIAL / "scoped-avcs.log").write_text("\n".join(avcs) + "\n")
            summary["scoped_avc_count"] = len(avcs)
            summary["observed_domains"] = observation["observed_domains"]
            summary["checks"] = acceptance(before, collected["after"], observation, avcs,
                                            audit_before, collected["audit-after"])
            summary["passed"] = all(summary["checks"].values()) and not summary["errors"]
    except Exception as error:
        summary["errors"].append({"phase": phase, "type": type(error).__name__})
    finally:
        summary["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save("summary.json", summary)
    # Raw journal/audit/TPM data and exception messages stay out of operator-facing output.
    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1


def main():
    if sys.argv[1:] != ["--approved-v2-first-run"]:
        raise RuntimeError("Expected --approved-v2-first-run")
    if os.geteuid() != 0:
        raise RuntimeError("Operator sudo required")
    os.umask(0o077)
    os.environ["PATH"] = "/usr/sbin:/usr/bin:/sbin:/bin"
    os.environ["LC_ALL"] = "C"
    if command("hostname", "-s").strip() != b"hermes":
        raise RuntimeError("Unexpected host")
    info = BACKUP.stat()
    if (any(path.is_symlink() for path in (BACKUP, *BACKUP.parents)) or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700):
        raise RuntimeError("Expected root-private v2 backup directory")
    TRIAL.mkdir(mode=0o700)  # Atomic exclusive reservation blocks repeats, including failed preflights.
    return trial()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print("STOP: " + type(error).__name__ + "; preserve evidence; do not repeat or reboot", file=sys.stderr)
        sys.exit(1)
