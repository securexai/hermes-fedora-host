"""Noninteractive public seam; the enrolled remote dispatcher owns mutation authority."""

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import time
import uuid

from common import Failure, atomic, canonical, decode, digest, lock, protected_file, report, require, run
from policy import load_config, maintenance_open, ssh_options
from release import unpack
from credentials import client as credential_request
from gates import backup_snapshot, retain_backups


def request(config, action, **values):
    response = decode(run(ssh_options(config), data=canonical({"schema": "hermes-dispatch-v1",
                                                              "action": action, **values}), timeout=1560))
    require(isinstance(response, dict) and response.get("ok") is True, "remote-operation-rejected")
    require(response.get("host") == config["host"], "wrong-host")
    return response


def fetch_backup(config, destination, release_id, fingerprint):
    with open(destination, "xb") as output:
        os.chmod(destination, 0o600)
        run(ssh_options(config), data=canonical({"schema": "hermes-dispatch-v1", "action": "backup",
                                               "release_id": release_id, "fingerprint": fingerprint}),
            stdout=output, timeout=900)


def converge(config, manifest, fingerprint, state_path, operation, state):
    release_id = manifest["release_id"]
    binding = {"release_id": release_id, "fingerprint": fingerprint}
    remote = request(config, "bound", **binding)
    phase = remote["stage"]
    if operation == "rollback":
        result = request(config, "rollback", **binding)
        atomic(state_path, canonical({**state, **result}))
        return result
    if phase == "closed":
        result = request(config, operation, **binding)
        return finish(config, state, state_path, result)
    if phase in ("new", "snapshot-ready"):
        snapshot = request(config, "snapshot", **binding)
        # Volatile scratch avoids persisting a plaintext copy on the workstation.
        with tempfile.TemporaryDirectory(prefix="hermes-backup-", dir="/dev/shm") as temporary:
            source = Path(temporary) / "hermes.tar"
            fetch_backup(config, source, **binding)
            require(digest(source) == snapshot["snapshot_sha256"],
                    "snapshot-transport-mismatch")
            receipt = backup_snapshot(source, config, release_id)
        state["backup"] = receipt
        atomic(state_path, canonical(state))
        request(config, "backup-verified", **binding, backup_snapshot=receipt["snapshot"],
                snapshot_sha256=receipt["sha256"])
        phase = "backup-verified"
    if phase == "backup-verified":
        if "lease" not in state:
            state["lease"] = uuid.uuid4().hex
            atomic(state_path, canonical(state))
        secret = credential_request(config["credential_socket"], "issue", "production", state["lease"])
        request(config, "credential", **binding, key=secret["key"])
        del secret
    deadline = time.monotonic() + 3000
    while time.monotonic() < deadline:
        try:
            result = request(config, operation, **binding)
        except Failure:
            # Reconnect only while an independently recorded reboot is pending.
            if state.get("stage") not in ("reboot-pending", "persistence-reboot"):
                raise
            time.sleep(10)
            continue
        state.update(result)
        atomic(state_path, canonical(state))
        if result["stage"] == "closed":
            return finish(config, state, state_path, result)
        require(result["stage"] in ("reboot-pending", "persistence-reboot"), "release-needs-recovery", 75)
        time.sleep(10)
    raise Failure(69, "reboot-recovery-required")


def finish(config, state, state_path, result):
    previous = state.get("previous_lease")
    if previous and previous != state.get("lease"):
        credential_request(config["credential_socket"], "revoke", "production", previous)
        state.pop("previous_lease")
        atomic(state_path, canonical(state))
    if state.get("backup"):
        history = state.setdefault("backup_history", [])
        snapshot = state["backup"]["snapshot"]
        if snapshot not in history:
            history.append(snapshot)
        state["backup_history"] = retain_backups(history, snapshot, config)
        atomic(state_path, canonical(state))
    return result


def upload(config, release):
    # Stream the archive after a bounded JSON header; neither shell quoting nor SCP is involved.
    with open(release, "rb") as source, tempfile.TemporaryFile() as outgoing:
        outgoing.write(canonical({"schema": "hermes-dispatch-v1", "action": "stage"}))
        while chunk := source.read(1024 * 1024):
            outgoing.write(chunk)
        outgoing.seek(0)
        try:
            result = subprocess.run(ssh_options(config), stdin=outgoing, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, timeout=900, check=False)
        except subprocess.TimeoutExpired:
            raise Failure(69, "release-upload-timeout") from None
        require(result.returncode == 0, "release-upload-failed", 69)
        response = decode(result.stdout)
        require(response.get("ok") is True and response.get("host") == config["host"], "release-upload-rejected")
        return response


def main():
    parser = argparse.ArgumentParser(description="Enrolled, signed Hermes release controller")
    parser.add_argument("command", choices=("deploy", "upgrade", "check", "status", "rollback"))
    parser.add_argument("--non-interactive", action="store_true", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--release")
    parser.add_argument("--json", action="store_true", help="structured output (always enabled for this interface)")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.command in ("check", "status"):
        require(args.release is None, "release-not-valid-for-read-only-command", 64)
        return request(config, args.command)
    require(args.release is not None, "release-required", 64)
    for command in ("ssh", "ssh-keygen", "restic"):
        require(shutil.which(command) is not None, "missing-controller-dependency", 69)
    if args.command != "rollback":
        password = protected_file(config["backup_password_file"])
        require(password.stat().st_mode & 0o077 == 0, "backup-password-not-private")
        credential_request(config["credential_socket"], "check", "production", "0" * 32)
        run(["restic", "--no-cache", "--repo", config["backup_repository"], "--password-file", config["backup_password_file"],
             "snapshots", "--json", "--no-lock"])
    state = Path(config["state_dir"])
    target = hashlib.sha256(config["target"].encode()).hexdigest()
    state_path = state / (target + ".json")
    prior = decode(state_path.read_bytes()) if state_path.exists() else {}
    # Verification creates disposable local files only, before any SSH mutation or persistent state.
    with tempfile.TemporaryDirectory(prefix="hermes-release-") as temporary:
        verified = Path(temporary) / "verified"
        with open(args.release, "rb") as stream:
            manifest, fingerprint = unpack(stream, verified, config["allowed_signers"], host=config["host"],
                                           bound_digest=prior.get("fingerprint"))
        require(manifest["provider"] == config["provider"] and manifest["model"] == config["model"],
                "provider-model-mismatch")
        require(args.command == "rollback" or maintenance_open(), "outside-maintenance-window", 75)
        state.mkdir(mode=0o700, parents=True, exist_ok=True)
        require(not state.is_symlink() and state.stat().st_uid == os.getuid()
                and state.stat().st_mode & 0o077 == 0, "unsafe-controller-state")
        with lock(state / (target + ".lock")):
            prior = decode(protected_file(state_path).read_bytes()) if state_path.exists() else {}
            status = request(config, "check")
            require(status.get("enrolled") is True, "host-not-enrolled")
            if prior.get("fingerprint") != fingerprint:
                upload(config, args.release)
                prior = {"fingerprint": fingerprint, "release_id": manifest["release_id"],
                         "previous_lease": prior.get("lease"), "backup_history": prior.get("backup_history", [])}
                atomic(state_path, canonical(prior))
            try:
                return converge(config, manifest, fingerprint, state_path, args.command, prior)
            except Failure:
                # Restore service after a failed pre-change backup or provider setup. Once package
                # staging starts, retain state and require OS recovery instead of guessing rollback.
                try:
                    binding = {"release_id": manifest["release_id"], "fingerprint": fingerprint}
                    phase = request(config, "bound", **binding)["stage"]
                    if phase in ("new", "snapshot-creating", "snapshot-ready", "backup-verified", "credential-ready", "rolled-back"):
                        recovery = request(config, "rollback", **binding)
                        if recovery["stage"] == "rolled-back" and prior.get("lease"):
                            credential_request(config["credential_socket"], "revoke", "production", prior["lease"])
                        prior.update(recovery)
                    else:
                        prior["recovery"] = "operator-required"
                    atomic(state_path, canonical(prior))
                except Failure:
                    pass
                raise


if __name__ == "__main__":
    report(main)
