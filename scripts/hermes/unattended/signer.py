"""Fixed signing service: only the enrolled certifier's handoff can reach the signing key."""

import argparse
import contextlib
import os
from pathlib import Path
import stat
import tempfile
import time

from common import atomic, decode, digest, lock, protected_file, report, require
from finalize import finalize, validate_candidate
from release import GATES, candidate_fingerprint

FIELDS = {"schema", "signer_uid", "certifier_uid", "candidate", "evidence", "output_dir",
          "signing_key", "allowed_signers"}


def owned_path(path, owner, directory=False):
    path = Path(path)
    require(path.is_absolute(), "relative-signing-path")
    info = path.lstat()
    require((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            and info.st_uid == owner and not info.st_mode & 0o022, "untrusted-signing-input")
    for parent in path.parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0, owner)
                and not info.st_mode & 0o022, "untrusted-signing-parent")
    return path


@contextlib.contextmanager
def open_owned(path, owner):
    """Walk with held directory descriptors so a certifier rename cannot redirect reads."""
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts, "relative-signing-path")
    directory = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
            info = os.fstat(directory)
            require(info.st_uid in (0, owner) and not info.st_mode & 0o022, "untrusted-signing-parent")
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, "rb") as source:
            info = os.fstat(source.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_uid == owner
                    and not info.st_mode & 0o022, "untrusted-signing-input")
            yield source
    finally:
        os.close(directory)


def read_owned(path, owner, limit):
    with open_owned(path, owner) as source:
        require(os.fstat(source.fileno()).st_size <= limit, "untrusted-signing-input")
        raw = source.read(limit + 1)
        require(len(raw) <= limit, "oversized-signing-input")
        return raw


def copy_owned(path, destination, owner, limit):
    with open_owned(path, owner) as source, open(destination, "xb") as target:
        os.chmod(destination, 0o600)
        require(os.fstat(source.fileno()).st_size == limit, "untrusted-signing-input")
        total = 0
        while chunk := source.read(1024 * 1024):
            total += len(chunk)
            require(total <= limit, "oversized-signing-input")
            target.write(chunk)
        require(total == limit, "truncated-signing-input")
        target.flush()
        os.fsync(target.fileno())


def validate_evidence(records, now):
    require(isinstance(records, dict) and set(records) == GATES
            and all(isinstance(value, dict) for value in records.values()), "invalid-certification-evidence")
    times = {}
    run_ids = set()
    for gate, value in records.items():
        completed = value.get("completed_at")
        require(type(completed) is int and now - 86400 <= completed <= now, "stale-certification-evidence")
        run_id = value.get("run_id")
        require(isinstance(run_id, str) and len(run_id) == 64
                and all(c in "0123456789abcdef" for c in run_id), "invalid-certification-run")
        times[gate] = completed
        run_ids.add(run_id)
    require(len(run_ids) == 1 and times["vm_destroyed"] == max(times.values())
            and times["credential_revocation"] >= times["inference"], "certification-order-mismatch")


def sign(config):
    require(isinstance(config, dict) and set(config) == FIELDS
            and config["schema"] == "hermes-signer-v1", "invalid-signer-policy")
    signer, certifier = config["signer_uid"], config["certifier_uid"]
    require(type(signer) is int and type(certifier) is int and signer > 0 and certifier > 0
            and signer != certifier and signer == os.getuid(), "signer-role-mismatch")
    candidate = owned_path(config["candidate"], certifier, directory=True)
    evidence = owned_path(config["evidence"], certifier, directory=True)
    output = owned_path(config["output_dir"], signer, directory=True)
    key = owned_path(config["signing_key"], signer)
    require(key.stat().st_mode & 0o077 == 0, "signing-key-not-private")
    signers = protected_file(config["allowed_signers"], 0)
    candidate_raw = read_owned(candidate / "candidate.json", certifier, 1024 * 1024)
    manifest = decode(candidate_raw)
    validate_candidate(manifest)
    evidence_raw = {gate: read_owned(evidence / (gate + ".json"), certifier, 1024 * 1024)
                    for gate in manifest["evidence"]}
    now = int(time.time())
    validate_evidence({gate: decode(raw) for gate, raw in evidence_raw.items()}, now)
    fingerprint = candidate_fingerprint(manifest)
    with lock(output / ".signer.lock"):
        target = output / (fingerprint + ".tar")
        # Never renew an old certification by re-signing it with a later expiry.
        require(not target.exists(), "candidate-already-signed")
        with tempfile.TemporaryDirectory(prefix=".handoff-", dir=output) as temporary:
            # Freeze the checked handoff under signer ownership before calling the packaging API.
            frozen = Path(temporary) / "candidate"
            frozen.mkdir(mode=0o700)
            proof = Path(temporary) / "evidence"
            proof.mkdir(mode=0o700)
            atomic(frozen / "candidate.json", candidate_raw)
            for name, record in manifest["files"].items():
                destination = frozen / name
                destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                copy_owned(candidate / name, destination, certifier, record["size"])
            for gate, raw in evidence_raw.items():
                atomic(proof / (gate + ".json"), raw)
            finalize(frozen, proof, target, key, signers)
        target.chmod(0o644)
        # Only this identity can publish. Deployment sees a complete archive via atomic rename.
        pending = output / ".selected.pending"
        require(not pending.exists() and not pending.is_symlink(), "pending-publication-needs-recovery")
        os.link(target, pending)
        os.replace(pending, output / "selected.tar")
        fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    return {"ok": True, "stage": "signed", "artifact_fingerprint": fingerprint,
            "archive_sha256": digest(target)}


def main():
    parser = argparse.ArgumentParser(description="Sign only enrolled certifier handoffs")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    return sign(decode(protected_file(args.config, 0).read_bytes()))


if __name__ == "__main__":
    report(main)
