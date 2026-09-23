"""Root-owned forced-command entrypoint. Only authenticated release code can run as root."""

import hashlib
import os
from pathlib import Path
import re
import sys
import tempfile

from common import atomic, canonical, decode, digest, lock, protected_file, report, require, run
from policy import maintenance_open
from release import NAMESPACE, validate, unpack
from host import preflight

ROOT = Path("/var/lib/hermes-unattended")
POLICY = Path("/etc/hermes-unattended/host.json")
SIGNERS = Path("/etc/hermes-unattended/allowed_signers")


def identity():
    fingerprint = run(["ssh-keygen", "-lf", "/etc/ssh/ssh_host_ed25519_key.pub", "-E", "sha256"]).decode().split()[1]
    return {"machine_id_sha256": digest("/etc/machine-id"), "ssh_fingerprint": fingerprint}


def enrollment():
    require(os.geteuid() == 0, "root-dispatcher-required", 77)
    policy = decode(protected_file(POLICY, 0).read_bytes())
    require(isinstance(policy, dict) and policy.get("schema") == "hermes-host-v1"
            and policy.get("host") == identity(), "host-enrollment-mismatch")
    require(policy.get("enabled") is True, "host-not-enrolled")
    require(policy.get("boot_certified") is True and policy.get("recovery_verified") is True,
            "boot-enrollment-incomplete")
    protected_file(SIGNERS, 0)
    require(ROOT.is_dir() and not ROOT.is_symlink() and ROOT.stat().st_uid == 0
            and ROOT.stat().st_mode & 0o077 == 0, "unsafe-dispatcher-state")
    return policy


def verify_tree(directory, host, fingerprint):
    raw = protected_file(directory / "manifest.json", 0).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == fingerprint, "bound-release-changed")
    run(["ssh-keygen", "-Y", "verify", "-f", str(SIGNERS), "-I", "hermes-release", "-n", NAMESPACE,
         "-s", str(protected_file(directory / "manifest.sig", 0))], data=raw, timeout=30)
    manifest = validate(decode(raw), host=host, bound=True)
    for name, record in manifest["files"].items():
        path = protected_file(directory / name, 0)
        require(path.stat().st_size == record["size"] and digest(path) == record["sha256"], "staged-artifact-changed")
    return manifest


def dispatch(stream):
    policy = enrollment()
    header = stream.readline(65537)
    require(len(header) <= 65536 and header.endswith(b"\n"), "invalid-dispatch-frame", 64)
    message = decode(header)
    require(isinstance(message, dict) and message.get("schema") == "hermes-dispatch-v1", "invalid-dispatch-schema", 64)
    action = message.get("action")
    require(action in ("status", "check", "stage", "bound", "snapshot", "backup", "backup-verified",
                       "credential", "deploy", "upgrade", "rollback"), "unauthorized-operation", 77)
    fields = {"schema", "action"} if action in ("status", "check", "stage") else {
        "schema", "action", "release_id", "fingerprint"}
    if action == "credential":
        fields |= {"key"}
    if action == "backup-verified":
        fields |= {"backup_snapshot", "snapshot_sha256"}
    require(set(message) == fields, "unexpected-dispatch-fields", 64)
    if action == "backup-verified":
        require(isinstance(message["backup_snapshot"], str)
                and re.fullmatch(r"[a-f0-9]{8,64}", message["backup_snapshot"])
                and isinstance(message["snapshot_sha256"], str)
                and re.fullmatch(r"[a-f0-9]{64}", message["snapshot_sha256"]), "invalid-backup-receipt", 64)
    response = {"ok": True, "host": policy["host"], "enrolled": True}
    if action in ("status", "check"):
        preflight(policy)
        state = decode((ROOT / "status.json").read_bytes()) if (ROOT / "status.json").exists() else {"stage": "enrolled"}
        if state.get("release_id"):
            active = state["release_id"]
            require(isinstance(active, str) and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,95}", active), "invalid-active-release")
            directory = ROOT / "releases" / active
            binding = decode(protected_file(ROOT / (active + ".binding"), 0).read_bytes())
            verify_tree(directory, policy["host"], binding["fingerprint"])
            state = decode(run(["/usr/bin/python3", "-I", str(directory / "payload/host.py"), action], timeout=180))
            require(isinstance(state, dict) and set(state) <= {"ok", "stage", "release_id"}, "unsafe-status-response")
        return {**response, **state}
    if action not in ("bound", "rollback", "backup"):
        require(maintenance_open(minimum_seconds=0 if action in ("deploy", "upgrade") else 1800),
                "outside-maintenance-window", 75)
    with lock(ROOT / "target.lock"):
        if action == "stage":
            with tempfile.TemporaryDirectory(prefix=".incoming-", dir=ROOT) as temporary:
                incoming = Path(temporary) / "release"
                manifest, fingerprint = unpack(stream, incoming, SIGNERS, host=policy["host"], owner=0)
                require("payload/host.py" in manifest["files"], "missing-host-entrypoint")
                release_id = manifest["release_id"]
                releases = ROOT / "releases"
                releases.mkdir(mode=0o700, exist_ok=True)
                destination = releases / release_id
                if destination.exists():
                    existing = digest(destination / "manifest.json")
                    require(existing == fingerprint, "release-id-reused")
                else:
                    os.rename(incoming, destination)
                atomic(ROOT / (release_id + ".binding"), canonical({"fingerprint": fingerprint}))
                return {**response, "release_id": release_id, "fingerprint": fingerprint, "stage": "staged"}
        release_id = message["release_id"]
        require(isinstance(release_id, str) and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,95}", release_id),
                "invalid-release-id", 64)
        directory = ROOT / "releases" / release_id
        binding = decode(protected_file(ROOT / (release_id + ".binding"), 0).read_bytes())
        require(message["fingerprint"] == binding["fingerprint"], "release-binding-mismatch")
        verify_tree(directory, policy["host"], binding["fingerprint"])
        if action == "bound":
            state_path = ROOT / (release_id + ".state.json")
            state = decode(state_path.read_bytes()) if state_path.exists() else {"phase": "new"}
            return {**response, "release_id": release_id, "fingerprint": binding["fingerprint"], "stage": state["phase"]}
        if action == "backup":
            source = protected_file(ROOT / (release_id + ".snapshot.tar"), 0)
            with source.open("rb") as snapshot:
                while chunk := snapshot.read(1024 * 1024):
                    sys.stdout.buffer.write(chunk)
            return None
        # This entrypoint is explicitly inside the signed release's root trust boundary.
        # It receives fixed action names, no caller-supplied commands, environment, or file paths.
        env = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8", "HOME": "/root"}
        sensitive_input = canonical(message) if action in ("credential", "backup-verified") else None
        result = decode(run(["/usr/bin/python3", "-I", str(directory / "payload/host.py"), action],
                            data=sensitive_input, timeout=1500, env=env))
        require(isinstance(result, dict) and result.get("ok") is True, "release-operation-failed")
        require(set(result) <= {"ok", "stage", "release_id", "recovery", "snapshot_sha256"}, "unsafe-release-response")
        atomic(ROOT / "status.json", canonical(result))
        return {**response, **result}


if __name__ == "__main__":
    require(len(sys.argv) == 1, "dispatcher-takes-no-arguments", 64)
    report(lambda: dispatch(sys.stdin.buffer))
