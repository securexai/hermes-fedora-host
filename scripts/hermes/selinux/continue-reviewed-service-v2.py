#!/usr/bin/env python3
"""Continue the approved single invocation only after the exact v2 preflight-only failure."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from types import ModuleType

BACKUP = Path("/var/lib/hermes-selinux-trial-20260909-v2")
PRIOR = BACKUP / "service-first"
CONTINUATION = BACKUP / "service-continuation-1"
ORIGINAL = BACKUP / "run-reviewed-service-v2.py"
CORRECTED = BACKUP / "run-reviewed-service-v2-corrected.py"
ORIGINAL_HASH = "3ed9e2e9d8c751b1cb6281648cef4f1691b81fb480442da247b301578af51500"
CORRECTED_HASH = "6fd1a7c96efc3729173d321398ce0b111f2d5f0cea46df6b0c2d9c2605f3ec07"
EXPECTED_SUMMARY = {
    "passed": False, "service_requested": False, "checks": {},
    "errors": [{"phase": "preflight", "type": "RuntimeError"}],
    "timestamp": "2026-09-09T23:10:56.604573+00:00",
}
INVOCATIONS = {
    "systemd-tpm2-setup.service": "4cce6a53c01c4dff8c480b530fd16661",
    "systemd-tpm2-setup-early.service": "856199b7545e421e84cec252c2106124",
}


def private_directory(path):
    info = path.stat()
    if (any(p.is_symlink() for p in (path, *path.parents)) or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700):
        raise RuntimeError("Expected root-private directory without symlinks")


def private_bytes(path):
    info = path.stat()
    if (any(p.is_symlink() for p in (path, *path.parents)) or not stat.S_ISREG(info.st_mode)
            or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
            or not 0 < info.st_size <= 2 * 1024 * 1024):
        raise RuntimeError("Expected bounded root-private regular file without links")
    return path.read_bytes()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeError("Duplicate JSON property in prior evidence")
        result[key] = value
    return result


def read_prior():
    private_directory(BACKUP)
    private_directory(PRIOR)
    if {p.name for p in PRIOR.iterdir()} != {"before.json", "summary.json"}:
        raise RuntimeError("Prior attempt has unexpected files or request/observation evidence")
    original = private_bytes(ORIGINAL)
    if sha(original) != ORIGINAL_HASH:
        raise RuntimeError("Original helper identity changed")
    before_data = private_bytes(PRIOR / "before.json")
    summary_data = private_bytes(PRIOR / "summary.json")
    summary = json.loads(summary_data, object_pairs_hook=unique_object)
    # Canonical JSON distinguishes false from numeric zero; require the exact known failed attempt.
    if json.dumps(summary, sort_keys=True) != json.dumps(EXPECTED_SUMMARY, sort_keys=True):
        raise RuntimeError("Prior summary is not the exact preflight-only failure")
    before = json.loads(before_data, object_pairs_hook=unique_object)
    if (not isinstance(before, dict) or set(before.get("units", {})) != set(INVOCATIONS)
            or any(before["units"][unit].get("InvocationID") != value for unit, value in INVOCATIONS.items())
            or "-.mount" not in before["units"]["systemd-tpm2-setup.service"].get("Requires", "").split()):
        raise RuntimeError("Prior snapshot does not identify the reviewed dependency failure")
    return {"before": before, "hashes": {"original_helper": sha(original),
            "before.json": sha(before_data), "summary.json": sha(summary_data)}}


def load_core():
    data = private_bytes(CORRECTED)
    if sha(data) != CORRECTED_HASH:
        raise RuntimeError("Corrected helper identity changed")
    core = ModuleType("reviewed_v2_core")
    exec(compile(data, str(CORRECTED), "exec"), core.__dict__)
    return core


def configure_core(core, prior):
    core.TRIAL = CONTINUATION
    original_preflight = core.preflight
    original_acceptance = core.acceptance
    original_command = core.command

    def preflight(before):
        current_prior = read_prior()
        if current_prior != prior:
            raise RuntimeError("Prior evidence changed during continuation")
        if before != prior["before"]:
            raise RuntimeError("Current snapshot differs from failed-attempt baseline")
        original_preflight(before)

    def acceptance(*args, **kwargs):
        checks = original_acceptance(*args, **kwargs)
        try:
            checks["prior_attempt_preserved"] = read_prior() == prior
        except Exception:
            checks["prior_attempt_preserved"] = False
        return checks

    def command(*args):
        try:
            return original_command(*args)
        except Exception as error:
            core.save("command-failure.json", {"argv": list(args), "type": type(error).__name__,
                                                "reason": str(error)})
            raise

    def monitored(name, operation):
        def call(*args, **kwargs):
            try:
                return operation(*args, **kwargs)
            except Exception as error:
                core.save("diagnostic-" + name + ".json", {"operation": name,
                          "type": type(error).__name__, "reason": str(error)})
                raise
        return call

    core.preflight = preflight
    core.acceptance = acceptance
    core.command = command
    for name in ("snapshot", "preflight", "audit_status", "query_audit", "journal_cursor", "preserve_anchors"):
        setattr(core, name, monitored(name, getattr(core, name)))


def main():
    if sys.argv[1:] != ["--approved-v2-continuation"] or os.geteuid() != 0:
        raise RuntimeError("Explicit continuation scope and operator sudo required")
    os.umask(0o077)
    os.environ.update(PATH="/usr/sbin:/usr/bin:/sbin:/bin", LC_ALL="C")
    prior = read_prior()
    core = load_core()
    if core.BACKUP != BACKUP or core.command("hostname", "-s").strip() != b"hermes":
        raise RuntimeError("Unexpected continuation host or backup path")
    CONTINUATION.mkdir(mode=0o700)  # Exclusive reservation; never reuse, delete or rename either attempt.
    configure_core(core, prior)
    core.save("prior-attempt.json", {"hashes": prior["hashes"], "summary": EXPECTED_SUMMARY,
                                   "corrected_helper_sha256": CORRECTED_HASH})
    return core.trial()  # Same single-request/audit/acceptance logic; never call the original main().


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print("STOP: " + type(error).__name__ + "; preserve both attempts; do not repeat or reboot", file=sys.stderr)
        sys.exit(1)
