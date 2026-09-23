"""Produce a real scan gate bound to the frozen candidate and its explicit image policy."""

import argparse
import time
from pathlib import Path

from common import atomic, canonical, decode, digest, protected_file, report, require
from finalize import validate_candidate
from gates import scan_image
from release import candidate_fingerprint, sha

POLICY_PATH = "payload/vulnerability-policy.json"


def scan(candidate, output, run_id):
    require(sha(run_id), "invalid-certification-run")
    candidate = Path(candidate)
    raw = protected_file(candidate / "candidate.json").read_bytes()
    manifest = validate_candidate(decode(raw))
    require(POLICY_PATH in manifest["files"], "missing-vulnerability-policy")
    policy_path = protected_file(candidate / POLICY_PATH)
    expected = manifest["files"][POLICY_PATH]["sha256"]
    require(digest(policy_path) == expected, "vulnerability-policy-changed")
    policy = decode(policy_path.read_bytes())
    require(isinstance(policy, dict) and set(policy) == {"schema", "denylist"}
            and policy["schema"] == "advisory-denylist-v1", "invalid-vulnerability-policy")
    result = scan_image(manifest["image"], policy["denylist"])
    require((candidate / "candidate.json").read_bytes() == raw and digest(policy_path) == expected,
            "candidate-changed-during-scan")
    result.update(release_id=manifest["release_id"], artifact_fingerprint=candidate_fingerprint(manifest),
                  run_id=run_id, completed_at=int(time.time()), policy_sha256=expected)
    require(not Path(output).exists(), "scan-evidence-already-exists")
    atomic(output, canonical(result))
    return result


def main():
    parser = argparse.ArgumentParser(description="Scan an official Hermes candidate using its frozen policy")
    for name in ("candidate", "output", "run-id"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    return scan(args.candidate, args.output, args.run_id)


if __name__ == "__main__":
    report(main)
