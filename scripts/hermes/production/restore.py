"""Isolated encrypted off-host restore rehearsal; never starts a restored live gateway."""

import re
import tempfile
from pathlib import Path

from . import preflight, receivers
from .primitives import atomic, canonical, lock, read_json, regular, require, run, sha
from .runtime import STATE, validate_snapshot


def rehearse(snapshot_id, *, apply=False):
    require(re.fullmatch(r"[a-f0-9]{64}", snapshot_id or ""), "full-restic-snapshot-id-required")
    config = preflight.configuration(read_json(preflight.CONFIG, owner=0))
    require(
        config["kind"] == "fixture" and config["application_mode"] == "synthetic",
        "isolated-synthetic-fixture-required",
    )
    require(config["restic_repository"] != "none", "backup-not-configured")
    preflight.enforce(config, installed=True)
    require(not (STATE / "current.json").exists(), "restore-rehearsal-requires-empty-fixture")
    if not apply:
        return {"status": "PREVIEW", "operation": "restore-rehearsal", "snapshot": snapshot_id}
    password = regular(config["restic_password_file"], owner=0, private=True)
    env = {
        "RESTIC_REPOSITORY": config["restic_repository"],
        "RESTIC_PASSWORD_FILE": str(password),
        "HOME": "/root",
    }
    with (
        lock(STATE / "operation.lock"),
        tempfile.TemporaryDirectory(prefix="restore-rehearsal-", dir=STATE) as temporary,
    ):
        destination = Path(temporary)
        run(
            [
                "restic",
                "-o",
                "sftp.args=-oBatchMode=yes -oStrictHostKeyChecking=yes",
                "restore",
                snapshot_id,
                "--target",
                str(destination),
                "--verify",
            ],
            env=env,
            timeout=7200,
        )
        require(
            not any(p.is_symlink() for p in destination.rglob("*")), "unexpected-backup-tree-link"
        )
        restored = destination / str(STATE).lstrip("/")
        snapshots = list((restored / "backups").glob("*/snapshot.json"))
        require(len(snapshots) == 1, "ambiguous-restic-state-snapshot")
        info = read_json(snapshots[0], owner=0)
        archive = snapshots[0].parent / "state.tar"
        require(sha(archive) == info["state_sha256"], "restored-state-corrupt")
        validate_snapshot(archive)
        # Check the signed source/image pair with the same release verifier. Do not
        # configure or activate it: restored secrets stay confined to encrypted staging.
        from .runtime import Backend

        backend = Backend(config, state=restored)
        _, manifest = backend.release(info["release"])
        require(
            info["receiver"] == receivers.for_release(manifest).name,
            "restored-receiver-release-mismatch",
        )
        receivers.validate(
            info["receiver"],
            receivers.expected(manifest),
            install=destination / str(receivers.INSTALL).lstrip("/"),
        )
        target = destination / "isolated-state"
        target.mkdir(mode=0o700)
        run(
            [
                "tar",
                "--xattrs",
                "--acls",
                "--selinux",
                "--numeric-owner",
                "-xpf",
                str(archive),
                "-C",
                str(target),
            ],
            timeout=1800,
        )
        run(["tar", "--compare", "--file", str(archive), "--directory", str(target)], timeout=1800)
        result = {
            "status": "PASS",
            "scope": "isolated-offhost-file-restore-no-application-start",
            "snapshot": snapshot_id,
            "release": info["release"],
            "state_sha256": info["state_sha256"],
        }
        atomic(STATE / "restore-rehearsal.json", canonical(result))
        return result
