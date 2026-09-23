#!/usr/bin/env python3
"""One guarded invocation after two verified preflight-only failures; preserve both attempts."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from types import ModuleType

BACKUP = Path("/var/lib/hermes-selinux-trial-20260909-v2")
SECOND = BACKUP / "service-continuation-1"
CONTINUATION = BACKUP / "service-continuation-2"
PREVIOUS = BACKUP / "continue-reviewed-service-v2.py"
PREVIOUS_HASH = "fd2546742abdba2d7d568a4af31d481a96084dbcea5829cfbc832430bb5e7ab1"
AUDIT_PACKAGES = "audit-4.2.1-1.fc44.x86_64\naudit-libs-4.2.1-1.fc44.x86_64"
AUDIT_BASELINE = {"enabled": "1", "pid": "1182", "lost": "0", "backlog": "0"}
SECOND_SUMMARY = {
    "passed": False, "service_requested": False, "checks": {},
    "errors": [{"phase": "preflight", "type": "RuntimeError"}],
    "timestamp": "2026-09-09T23:39:18.235067+00:00",
}
SECOND_FILES = {"prior-attempt.json", "before.json", "audit-before.json", "audit-preflight.json",
                "audit-preflight.log", "diagnostic-query_audit.json", "summary.json"}


def private_directory(path):
    info = path.stat()
    if (any(p.is_symlink() for p in (path, *path.parents)) or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700):
        raise RuntimeError("Expected root-private evidence directory")


def private_bytes(path, allow_empty=False):
    info = path.stat()
    if (any(p.is_symlink() for p in (path, *path.parents)) or not stat.S_ISREG(info.st_mode)
            or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
            or info.st_size > 2 * 1024 * 1024 or (not allow_empty and info.st_size == 0)):
        raise RuntimeError("Expected bounded root-private evidence file without links")
    return path.read_bytes()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_previous():
    private_directory(BACKUP)
    data = private_bytes(PREVIOUS)
    if sha(data) != PREVIOUS_HASH:
        raise RuntimeError("Previous continuation wrapper identity changed")
    previous = ModuleType("preserved_v2_continuation")
    exec(compile(data, str(PREVIOUS), "exec"), previous.__dict__)
    return previous


def exact(value, expected):
    return json.dumps(value, sort_keys=True) == json.dumps(expected, sort_keys=True)


def read_prior(previous, read_first):
    first = read_first()
    private_directory(SECOND)
    if {p.name for p in SECOND.iterdir()} != SECOND_FILES:
        raise RuntimeError("Second attempt has missing/extra files or possible request evidence")
    data = {name: private_bytes(SECOND / name, allow_empty=name == "audit-preflight.log")
            for name in SECOND_FILES}
    records = {name: json.loads(value, object_pairs_hook=previous.unique_object)
               for name, value in data.items() if name.endswith(".json")}
    if not exact(records["summary.json"], SECOND_SUMMARY):
        raise RuntimeError("Second summary is not the exact preflight-only failure")
    if records["before.json"] != first["before"]:
        raise RuntimeError("Saved snapshots differ between failed attempts")
    if not exact(records["audit-preflight.json"], {
            "returncode": 1, "stderr": "", "timestamp_arguments": ["09/09/26", "18:39:18"]}):
        raise RuntimeError("Prior query metadata differs from reviewed empty raw result")
    if data["audit-preflight.log"] != b"":
        raise RuntimeError("Prior query stdout was not empty")
    if not exact(records["diagnostic-query_audit.json"], {"operation": "query_audit",
            "type": "RuntimeError", "reason": "Audit query failed; absence of denials is unverified"}):
        raise RuntimeError("Prior failed operation was not the reviewed audit query")
    if any(records["audit-before.json"].get(key) != value for key, value in AUDIT_BASELINE.items()):
        raise RuntimeError("Prior audit health differs from operator observation")
    if not exact(records["prior-attempt.json"], {"hashes": first["hashes"],
            "summary": previous.EXPECTED_SUMMARY, "corrected_helper_sha256": previous.CORRECTED_HASH}):
        raise RuntimeError("Prior attempt chain does not match original evidence")
    wrapper = private_bytes(PREVIOUS)
    core = private_bytes(previous.CORRECTED)
    if sha(wrapper) != PREVIOUS_HASH or sha(core) != previous.CORRECTED_HASH:
        raise RuntimeError("Preserved wrapper/core identity changed")
    hashes = {"first/" + name: value for name, value in first["hashes"].items()}
    hashes.update({"second/" + name: sha(value) for name, value in data.items()})
    hashes.update({"previous_wrapper": sha(wrapper), "preserved_core": sha(core)})
    return {"before": first["before"], "hashes": hashes}


def query_audit(core, timestamp, name):
    if core.command("rpm", "-q", "audit", "audit-libs").decode().strip() != AUDIT_PACKAGES:
        raise RuntimeError("Unreviewed audit package version")
    # Force configured logs even when the caller's stdin is a pipe, heredoc or closed descriptor.
    common = ["ausearch", "--input-logs", "-m", "AVC,USER_AVC", "-ts", *timestamp]

    def query(suffix, options):
        argv = common + options
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=60)
        core.save(name + suffix + ".json", {"timestamp_arguments": timestamp, "argv": argv,
                  "returncode": result.returncode, "stderr": result.stderr.decode(errors="replace"),
                  "stdout_bytes": len(result.stdout)})
        (core.TRIAL / (name + suffix + ".log")).write_bytes(result.stdout)
        return result

    raw = query("", ["--raw"])
    if raw.returncode == 0 and not raw.stderr and raw.stdout.strip():
        return raw.stdout.decode()
    if raw.returncode == 1 and raw.stdout == b"" and raw.stderr == b"":
        # v4.2.1 suppresses the no-match marker in raw mode. Require an unambiguous default-format check.
        confirm = query("-confirmation", ["--format", "default"])
        if (confirm.returncode == 1 and confirm.stdout == b""
                and confirm.stderr.strip() == b"<no matches>"):
            return ""
        raise RuntimeError("Empty raw query lacks a clean no-match confirmation")
    raise RuntimeError("Audit query error or unexpected output; absence of denials is unverified")


def configure_core(core, previous, prior, read_first):
    original_audit_status = core.audit_status

    def audit_status():
        value = original_audit_status()
        if any(value.get(key) != expected for key, expected in AUDIT_BASELINE.items()):
            raise RuntimeError("Audit daemon/counters differ from reviewed baseline")
        return value

    core.audit_status = audit_status
    core.query_audit = lambda timestamp, name: query_audit(core, timestamp, name)
    previous.read_prior = lambda: read_prior(previous, read_first)
    previous.CONTINUATION = CONTINUATION
    # Reuse original snapshot/evidence guards, private diagnostics and acceptance preservation check.
    previous.configure_core(core, prior)


def main():
    if sys.argv[1:] != ["--approved-v2-audit-continuation"] or os.geteuid() != 0:
        raise RuntimeError("Explicit audit-continuation scope and operator sudo required")
    os.umask(0o077)
    os.environ.update(PATH="/usr/sbin:/usr/bin:/sbin:/bin", LC_ALL="C")
    previous = load_previous()
    read_first = previous.read_prior
    if previous.BACKUP != BACKUP:
        raise RuntimeError("Unexpected backup path")
    prior = read_prior(previous, read_first)
    core = previous.load_core()
    if core.BACKUP != BACKUP or core.command("hostname", "-s").strip() != b"hermes":
        raise RuntimeError("Unexpected audit-continuation host or core")
    CONTINUATION.mkdir(mode=0o700)  # Third and final named reservation in this reviewed scope; never reuse.
    configure_core(core, previous, prior, read_first)
    core.save("prior-attempts.json", {"hashes": prior["hashes"], "audit_packages": AUDIT_PACKAGES,
                                    "second_summary": SECOND_SUMMARY})
    return core.trial()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print("STOP: " + type(error).__name__ + "; preserve all attempts; do not repeat or reboot", file=sys.stderr)
        sys.exit(1)
