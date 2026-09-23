"""Freeze a candidate directory before certification; do not issue promotion evidence."""

import argparse
from pathlib import Path
import shutil
import time

from common import atomic, canonical, decode, digest, protected_file, report, require
from release import GATES, SCHEMA, candidate_fingerprint, safe_name
from transaction import validate_bundle


def prepare(repository, destination, transaction, uki, identity, release_id, model, baseline):
    repository, destination, transaction, uki = map(Path, (repository, destination, transaction, uki))
    require(not destination.exists(), "candidate-destination-exists")
    protected_file(uki)
    protected_file(transaction / "transaction.json")
    protected_file(transaction / "installed-after.sha256")
    validate_bundle(transaction, baseline)
    destination.mkdir(mode=0o700)
    payload = destination / "payload"
    payload.mkdir(mode=0o700)
    library = repository / "scripts/hermes"
    for name in ("host.py", "common.py", "gates.py", "materialize.py", "transaction.py", "offline.py", "tpm_profile.py"):
        shutil.copyfile(library / "unattended" / name, payload / name)
    shutil.copyfile(library / "unattended/vulnerability-policy.json", payload / "vulnerability-policy.json")
    for name in ("hermes.container", "60-hermes-runtime.conf", "70-hermes-volume-label.conf",
                 "harden-config.py", "set-model.py"):
        shutil.copyfile(library / name, payload / name)
    shutil.copyfile(library / "unattended/systemd/hermes-runtime-credentials.service",
                    payload / "hermes-runtime-credentials.service")
    (destination / "packages").mkdir(mode=0o700)
    for source in transaction.rglob("*"):
        require(not source.is_symlink(), "unsafe-package-source")
        if source.is_dir():
            continue
        protected_file(source)
        relative = source.relative_to(transaction)
        name = "packages/" + str(relative)
        safe_name(name)
        output = destination / name
        output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copyfile(source, output)
    (destination / "boot").mkdir(mode=0o700)
    shutil.copyfile(uki, destination / "boot/hermes.efi")
    image = next(line.removeprefix("Image=") for line in (payload / "hermes.container").read_text().splitlines()
                 if line.startswith("Image="))
    files = {}
    for path in sorted(destination.rglob("*")):
        if path.is_file():
            path.chmod(0o600)
            files[str(path.relative_to(destination))] = {"size": path.stat().st_size, "mode": 0o600, "sha256": digest(path)}
    now = int(time.time())
    manifest = {"schema": SCHEMA, "release_id": release_id, "issued_at": now, "expires_at": now + 86400,
                "image": image, "provider": "openai-api", "model": model, "host": identity,
                "baseline_sha256": baseline, "transaction": "packages/transaction.json", "boot_artifact": "boot/hermes.efi",
                "files": files, "evidence": {gate: "evidence/" + gate + ".json" for gate in GATES}}
    atomic(destination / "candidate.json", canonical(manifest))
    return {"ok": True, "release_id": release_id, "artifact_fingerprint": candidate_fingerprint(manifest),
            "stage": "candidate-frozen"}


def main():
    parser = argparse.ArgumentParser(description="Freeze Hermes inputs for certification")
    for option in ("repository", "destination", "transaction", "uki", "host-identity", "release-id", "model", "baseline"):
        parser.add_argument("--" + option, required=True)
    args = parser.parse_args()
    return prepare(args.repository, args.destination, args.transaction, args.uki,
                   decode(protected_file(args.host_identity).read_bytes()), args.release_id, args.model, args.baseline)


if __name__ == "__main__":
    report(main)
