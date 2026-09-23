"""Package and sign a completed certifier-owned release directory.

This tool does not manufacture acceptance results. The enrollment procedure must
allow its signing identity to read only the trusted certifier's completed evidence.
"""

import argparse
import hashlib
import os
from pathlib import Path
import tarfile
import tempfile

from common import atomic, canonical, decode, digest, protected_file, report, require, run
from release import GATES, MAX_METADATA, NAMESPACE, candidate_fingerprint, safe_name, unpack, validate


def build(source, output, key, signers):
    source, output = Path(source), Path(output)
    require(not output.exists(), "release-output-exists")
    protected_file(key)
    manifest = decode(protected_file(source / "manifest.json").read_bytes())
    # The certifier supplies the digest map; recomputing it here would sign post-test changes.
    validate(manifest)
    expected = set(manifest["files"]) | {"manifest.json"}
    actual = set()
    for path in source.rglob("*"):
        require(not path.is_symlink(), "unsafe-source-link")
        if path.is_dir():
            require(path.stat().st_mode & 0o022 == 0, "writable-source-directory")
            continue
        protected_file(path)
        actual.add(str(path.relative_to(source)))
    require(actual == expected, "source-file-map-mismatch")
    # Reject failed evidence and changed payloads before touching the signing key.
    for name, record in manifest["files"].items():
        path = source / name
        require(path.stat().st_size == record["size"] and digest(path) == record["sha256"],
                "candidate-changed-before-signing")
    for gate, name in manifest["evidence"].items():
        require(manifest["files"][name]["size"] <= MAX_METADATA, "evidence-too-large")
        value = decode((source / name).read_bytes())
        require(isinstance(value, dict) and value.get("gate") == gate and value.get("result") == "PASS"
                and value.get("release_id") == manifest["release_id"]
                and value.get("artifact_fingerprint") == candidate_fingerprint(manifest),
                "certification-gate-incomplete")
        if gate == "vulnerability_scan":
            require(value.get("policy") == "advisory-denylist-v1"
                    and value.get("policy_sha256") == manifest["files"]["payload/vulnerability-policy.json"]["sha256"],
                    "vulnerability-policy-evidence-mismatch")
    # Snapshot first; subsequent verification hashes the exact bytes in the signed archive.
    with tempfile.TemporaryDirectory(prefix=".release-", dir=output.parent) as temporary:
        directory = Path(temporary)
        raw = canonical(manifest)
        record = directory / "manifest.json"
        record.write_bytes(raw)
        run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", NAMESPACE, str(record)])
        archive_path = directory / "release.tar"
        with tarfile.open(archive_path, "w", format=tarfile.USTAR_FORMAT) as archive:
            archive.add(record, arcname="manifest.json", recursive=False)
            archive.add(record.with_suffix(".json.sig"), arcname="manifest.sig", recursive=False)
            for name in sorted(manifest["files"]):
                safe_name(name)
                archive.add(source / name, arcname=name, recursive=False)
        with archive_path.open("rb") as stream:
            unpack(stream, directory / "verified", signers, host=manifest["host"])
        os.chmod(archive_path, 0o600)
        # Exclusive publication avoids replacing a previously selected artifact.
        os.link(archive_path, output)
    return {"ok": True, "release_id": manifest["release_id"], "sha256": digest(output)}


def main():
    parser = argparse.ArgumentParser(description="Sign completed Hermes certification evidence")
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--signing-key", required=True)
    parser.add_argument("--allowed-signers", required=True)
    args = parser.parse_args()
    return build(args.source, args.output, args.signing_key, args.allowed_signers)


if __name__ == "__main__":
    report(main)
