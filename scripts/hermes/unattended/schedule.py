"""Freeze an enrolled candidate and schedule isolated UA-03; never sign or deploy."""

import argparse
import shutil
import os
from pathlib import Path
import sys
import tempfile
import time

import certify
import prepare
from maintenance import publish
from common import Failure, atomic, canonical, decode, digest, lock, protected_file, report, require, run
from policy import maintenance_open
from release import candidate_fingerprint, sha
from signer import owned_path

FIELDS = {"schema", "certifier_config", "state_dir", "prepare"}
PREPARE_FIELDS = {"repository", "transaction", "uki", "host_identity", "release_id", "model", "baseline"}
STAGES = {"preparing", "prepared", "certifying", "ua03-complete", "failed"}


def load(path):
    policy = decode(protected_file(path, 0).read_bytes())
    require(isinstance(policy, dict) and set(policy) == FIELDS
            and policy["schema"] == "hermes-schedule-v1", "invalid-schedule-policy")
    recipe = policy["prepare"]
    require(isinstance(recipe, dict) and set(recipe) == PREPARE_FIELDS
            and all(isinstance(value, str) and value for value in recipe.values())
            and sha(recipe["baseline"]), "invalid-schedule-recipe")
    for value in [policy["certifier_config"], policy["state_dir"],
                  *(recipe[key] for key in ("repository", "transaction", "uki", "host_identity"))]:
        require(isinstance(value, str) and Path(value).is_absolute() and ".." not in Path(value).parts
                and not any(char in value for char in "\r\n\x00"), "invalid-schedule-path")
    config = certify.validate_config(decode(protected_file(policy["certifier_config"], 0).read_bytes()))
    owned_path(policy["state_dir"], os.getuid(), directory=True)
    require(not Path(policy["state_dir"]).stat().st_mode & 0o077, "schedule-state-not-private")
    # The journal cannot overlap certifier evidence, candidate or state paths.
    directories = [Path(policy["state_dir"]), *(Path(config[key]) for key in
                   ("state_dir", "candidate", "evidence_dir"))]
    require(all(a != b and a not in b.parents and b not in a.parents
                for index, a in enumerate(directories) for b in directories[index + 1:]),
            "overlapping-schedule-directories")
    return policy, config


def binding(policy, config):
    import hashlib
    return hashlib.sha256(canonical({"policy": policy, "certifier": config})).hexdigest()


CERTIFIER_TOOLS = ("ssh", "sudo", "restic", "trivy")


def child_environment():
    search_path = "/usr/local/bin:/usr/bin:/bin"
    tools = Path(__file__).resolve().parent / "bin"
    if tools.exists() or tools.is_symlink():
        # Service-local tooling is enrolled by root, never inherited from the caller.
        owned_path(tools, 0, directory=True)
        search_path = str(tools) + ":" + search_path
    return {"PATH": search_path}


def tool_readiness():
    """Check the child's actual search path under the caller's certifier identity."""
    environment = child_environment()
    for name in CERTIFIER_TOOLS:
        require(shutil.which(name, path=environment["PATH"]) is not None,
                "missing-certifier-tool-" + name, 69)
    return {"ok": True, "stage": "certifier-tools-ready", "tools": list(CERTIFIER_TOOLS)}


def child(config_path, cleanup=False):
    command = [sys.executable, "-B", "-E", "-s", str(Path(__file__).with_name("certify.py")),
               "--config", str(config_path)]
    if cleanup:
        command.append("--cleanup-only")
    environment = child_environment()
    # Progress and accidental output never reach notifications or the scheduler journal.
    with tempfile.TemporaryFile() as output:
        run(command, timeout=300 if cleanup else 6600, stdout=output,
            env=environment)
        require(output.tell() <= 65536, "oversized-certifier-result")
        output.seek(0)
        lines = output.read().splitlines()
    require(lines, "missing-certifier-result")
    result = decode(lines[-1])
    require(isinstance(result, dict) and result.get("ok") is True, "invalid-certifier-result")
    return result


def cleanup(policy, config):
    state = Path(config["state_dir"]) / "state.json"
    if not state.exists():
        require(not state.is_symlink(), "unsafe-certifier-state")
        return {"ok": True, "stage": "no-certifier-state"}
    result = child(policy["certifier_config"], cleanup=True)
    require(result.get("stage") in ("no-credential-issued", "credential-cleanup-complete"),
            "incomplete-certifier-cleanup")
    return {"ok": True, "stage": "credential-cleanup-complete"}


def frozen(config, journal):
    manifest, raw = certify.candidate(config)
    require(digest(Path(config["candidate"]) / "candidate.json") == journal["candidate_sha256"]
            and candidate_fingerprint(manifest) == journal["artifact_fingerprint"],
            "scheduled-candidate-changed")
    return manifest


def window_open(policy, config, grant_path=None):
    if grant_path is None:
        return maintenance_open()
    grant = decode(protected_file(owned_path(grant_path, 0), 0).read_bytes())
    require(isinstance(grant, dict) and set(grant) == {
        "schema", "binding", "run_id", "candidate_sha256", "issued_at", "expires_at"
    } and grant["schema"] == "hermes-lab-window-v1", "invalid-lab-window-grant")
    require(config.get("domain_uuid") == certify.DOMAIN
            and config.get("target") == "hermes-certify@172.16.99.12",
            "window-grant-requires-fixed-lab")
    now = int(time.time())
    require(type(grant["issued_at"]) is int and type(grant["expires_at"]) is int
            and grant["issued_at"] <= now < grant["expires_at"]
            and 0 < grant["expires_at"] - grant["issued_at"] <= 4 * 3600,
            "expired-or-invalid-lab-window")
    require(grant["binding"] == binding(policy, config) and grant["run_id"] == config["run_id"]
            and sha(grant["candidate_sha256"])
            and grant["candidate_sha256"] == digest(Path(config["candidate"]) / "candidate.json"),
            "lab-window-binding-mismatch")
    # A grant can only dispatch an already frozen candidate, never authorize preparation.
    require((Path(policy["state_dir"]) / "schedule.json").is_file(), "lab-window-needs-prepared-run")
    return True


def execute(policy, config, prepare_only=False, cleanup_only=False, grant_path=None):
    root = Path(policy["state_dir"])
    with lock(root / ".schedule.lock"):
        if cleanup_only:
            # Recovery remains available outside the maintenance window and after failure.
            return cleanup(policy, config)
        if not prepare_only and not window_open(policy, config, grant_path):
            return {"ok": True, "stage": "deferred"}
        path = root / "schedule.json"
        identity = binding(policy, config)
        if path.exists():
            journal = decode(protected_file(path).read_bytes())
            require(isinstance(journal, dict) and journal.get("binding") == identity
                    and journal.get("stage") in STAGES, "schedule-binding-mismatch")
            require(journal["stage"] in ("prepared", "ua03-complete"), "schedule-recovery-required", 75)
            frozen(config, journal)
            if journal["stage"] == "ua03-complete":
                return {"ok": True, "stage": "already-certified", "release_signed": False}
        else:
            require(not path.is_symlink(), "unsafe-schedule-state")
            require(not Path(config["candidate"]).exists() and not Path(config["candidate"]).is_symlink(),
                    "candidate-destination-exists")
            require(not (Path(config["state_dir"]) / "state.json").exists(), "certification-run-already-started")
            owned_path(Path(config["candidate"]).parent, os.getuid(), directory=True)
            journal = {"schema": "hermes-schedule-state-v1", "binding": identity, "stage": "preparing"}
            atomic(path, canonical(journal))
            recipe = policy["prepare"]
            try:
                prepare.prepare(recipe["repository"], config["candidate"], recipe["transaction"], recipe["uki"],
                                decode(protected_file(recipe["host_identity"]).read_bytes()), recipe["release_id"],
                                recipe["model"], recipe["baseline"])
                manifest, raw = certify.candidate(config)
                journal.update(stage="prepared", candidate_sha256=digest(Path(config["candidate"]) / "candidate.json"),
                               artifact_fingerprint=candidate_fingerprint(manifest))
                atomic(path, canonical(journal))
            except Exception:
                journal.update(stage="failed", failure="candidate-preparation-failed")
                atomic(path, canonical(journal))
                raise Failure(78, "candidate-preparation-failed") from None
        if prepare_only:
            return {"ok": True, "stage": "prepared", "candidate_sha256": journal["candidate_sha256"],
                    "release_signed": False}
        if not window_open(policy, config, grant_path):
            return {"ok": True, "stage": "deferred"}
        if grant_path is not None:
            journal["lab_window_grant_sha256"] = digest(grant_path)
        journal.update(stage="certifying")
        atomic(path, canonical(journal))
        failure = None
        try:
            result = child(policy["certifier_config"])
            require(result.get("stage") == "ua03-complete" and result.get("run_id") == config["run_id"]
                    and result.get("artifact_fingerprint") == journal["artifact_fingerprint"]
                    and result.get("release_signed") is False, "incomplete-scheduled-certification")
            frozen(config, journal)
        except Exception:
            failure = "scheduled-certification-failed"
        try:
            cleanup(policy, config)
        except Exception:
            journal["cleanup_failure"] = "credential-cleanup-failed"
            failure = failure or "credential-cleanup-failed"
        if failure:
            journal.update(stage="failed", failure=failure)
            atomic(path, canonical(journal))
            raise Failure(69, failure)
        journal.update(stage="ua03-complete")
        atomic(path, canonical(journal))
        return {"ok": True, "stage": "ua03-complete", "release_signed": False}


def main():
    parser = argparse.ArgumentParser(description="Schedule an enrolled disposable Hermes candidate")
    parser.add_argument("--config", required=True)
    parser.add_argument("--events", required=True)
    parser.add_argument("--lab-window-grant")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--cleanup-only", action="store_true")
    args = parser.parse_args()
    try:
        policy, config = load(args.config)
        result = execute(policy, config, args.prepare_only, args.cleanup_only, args.lab_window_grant)
    except (Failure, OSError, ValueError, KeyError, TypeError) as error:
        publish(args.events, "action-required", error.code if isinstance(error, Failure) else 78)
        raise
    if result["stage"] in ("prepared", "ua03-complete"):
        # UA-03 completion still needs UA-04 cleanup; it is not deployment completion.
        publish(args.events, "action-required", 75, config["run_id"])
    return result


if __name__ == "__main__":
    report(main)
