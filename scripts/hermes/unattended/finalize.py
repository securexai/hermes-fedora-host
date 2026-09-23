"""Combine frozen inputs and completed trusted certifier evidence for signing."""

import argparse
import copy
from pathlib import Path
import shutil
import time

from build_release import build
from common import atomic, canonical, decode, digest, protected_file, report, require
from release import candidate_fingerprint, GATES, validate


def validate_candidate(manifest):
    """Validate paths and complete schema before opening any candidate-supplied filename."""
    require(isinstance(manifest, dict) and isinstance(manifest.get("files"), dict), "invalid-candidate")
    expected = {gate: "evidence/" + gate + ".json" for gate in GATES}
    require(manifest.get("evidence") == expected, "invalid-candidate-evidence")
    require(not any(name.startswith("evidence/") for name in manifest["files"]), "candidate-contains-evidence")
    checked = copy.deepcopy(manifest)
    for name in expected.values():
        checked["files"][name] = {"sha256": "0" * 64, "size": 0, "mode": 0o600}
    # Candidate age does not grant promotion validity; finalize starts that window only after cleanup.
    validate(checked, bound=True)
    return manifest


def finalize(candidate, evidence, output, signing_key, signers):
    candidate, evidence, output = Path(candidate), Path(evidence), Path(output)
    manifest = decode(protected_file(candidate / "candidate.json").read_bytes())
    validate_candidate(manifest)
    expected = candidate_fingerprint(manifest)
    for name, record in manifest["files"].items():
        require(digest(protected_file(candidate / name)) == record["sha256"], "candidate-changed-after-freeze")
    # Completed is a new directory, so a failed attempt never changes the frozen candidate.
    import tempfile
    with tempfile.TemporaryDirectory(prefix=".completed-", dir=output.parent) as temporary:
        completed = Path(temporary)
        for name in manifest["files"]:
            target = completed / name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            shutil.copyfile(candidate / name, target)
            target.chmod(manifest["files"][name]["mode"])
        for gate, name in manifest["evidence"].items():
            source = protected_file(evidence / (gate + ".json"))
            value = decode(source.read_bytes())
            require(isinstance(value, dict) and value.get("gate") == gate and value.get("result") == "PASS"
                    and value.get("release_id") == manifest["release_id"]
                    and value.get("artifact_fingerprint") == expected, "certification-gate-incomplete")
            target = completed / name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            atomic(target, canonical(value))
            manifest["files"][name] = {"sha256": digest(target), "size": target.stat().st_size, "mode": 0o600}
        # The 24-hour promotion window begins after every gate, including cleanup, has completed.
        manifest["issued_at"] = int(time.time())
        manifest["expires_at"] = manifest["issued_at"] + 86400
        atomic(completed / "manifest.json", canonical(manifest))
        return build(completed, output, signing_key, signers)


def main():
    parser = argparse.ArgumentParser(description="Finalize completed Hermes certification")
    for option in ("candidate", "evidence", "output", "signing-key", "allowed-signers"):
        parser.add_argument("--" + option, required=True)
    args = parser.parse_args()
    return finalize(args.candidate, args.evidence, args.output, args.signing_key, args.allowed_signers)


if __name__ == "__main__":
    report(main)
