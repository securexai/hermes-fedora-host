#!/usr/bin/env python3
"""Fixed synthetic-only operations inside an owned disposable lab guest."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import sys
import tarfile
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("profile_deploy", HERE / "profile-deploy.py")
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)
HOME = pathlib.Path("/home/hermes")
EXPORT = pathlib.Path("/var/tmp/hermes-lab-export")
RESTORE_ARCHIVE = pathlib.Path("/var/tmp/hermes-lab-restore.tar")
TREES = ("gateway-state", "gateway-ssh", "worker-state")


def cmd(*args: str):
    return deploy.command(list(args))


def synthetic() -> None:
    deploy.require_host()
    env = HOME / "gateway-state/.env"
    if env.is_symlink() or not env.is_file() or os.path.ismount(HOME / "gateway-state"):
        raise deploy.DeployError("synthetic on-disk state is required")
    values = dict(line.split("=", 1) for line in env.read_text().splitlines() if "=" in line)
    if values.get("DEEPSEEK_API_KEY") != deploy.SYNTHETIC_KEY or any(
        name.startswith("TELEGRAM_") for name in values
    ):
        raise deploy.DeployError("backup and restore refuse live state")


def identities() -> dict:
    paths = {
        "machine": pathlib.Path("/etc/machine-id"),
        "sshd": pathlib.Path("/etc/ssh/ssh_host_ed25519_key.pub"),
        "worker": HOME / "worker-state/ssh-host-keys/ssh_host_ed25519_key.pub",
        "client": HOME / "gateway-ssh/worker_client_ed25519.pub",
    }
    return {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in paths.items()}


def inventory() -> dict:
    deploy.require_host()
    return {
        "packages": cmd(
            "/usr/bin/rpm", "-qa", "--qf", "%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\n"
        ).stdout.splitlines(),
        "selinux": "Enforcing",
    }


def export_images() -> None:
    deploy.require_host()
    if EXPORT.exists():
        raise deploy.DeployError("export directory already exists")
    EXPORT.mkdir(mode=0o755)
    uid, gid = deploy.ensure_user()
    os.chown(EXPORT, uid, gid)
    gateway = deploy.pinned_gateway()
    result = inventory()
    for name, image in (("gateway", gateway), ("worker", deploy.WORKER_IMAGE)):
        image_id = deploy.podman("image", "inspect", image, "--format", "{{.Id}}").stdout.strip()
        # Export by image ID: converting a registry manifest to OCI changes its
        # manifest digest. Retaining the registry digest as a name makes Podman
        # reject the archive on import. The separate manifest keeps provenance.
        deploy.podman(
            "save", "--format", "oci-archive", "--output", str(EXPORT / f"{name}.oci"), image_id
        )
        os.chmod(EXPORT / f"{name}.oci", 0o644)
        result[name + "_id"] = "sha256:" + image_id.removeprefix("sha256:")
    print(json.dumps(result, sort_keys=True))


def state_manifest(base=None) -> str:
    """Fingerprint bytes, types, numeric ownership, modes and link targets."""
    base = base or HOME
    rows = []
    for tree in TREES:
        root = base / tree
        for path in [root, *sorted(root.rglob("*"))]:
            st = path.lstat()
            payload = (
                os.readlink(path)
                if path.is_symlink()
                else (
                    hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "directory"
                )
            )
            rows.append((str(path.relative_to(base)), st.st_mode, st.st_uid, st.st_gid, payload))
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def stop_writers() -> list[str]:
    prior = []
    for unit in ("hermes-gateway.service", "hermes-worker.service"):
        result = deploy.user_systemctl("is-active", unit, check=False)
        if (result.returncode, result.stdout.strip()) not in (
            (0, "active"),
            (3, "inactive"),
            (3, "failed"),
        ):
            raise deploy.DeployError("cannot conclusively inspect service state")
        if result.returncode == 0:
            prior.append(unit)
    try:
        for unit in ("hermes-gateway.service", "hermes-worker.service"):
            deploy.user_systemctl("stop", unit)
        running = deploy.podman("ps", "--format", "{{.Names}}").stdout.splitlines()
        if set(running) & {"hermes-gateway", "hermes-worker"}:
            raise deploy.DeployError("application writers did not stop")
    except Exception:
        restart(prior)
        raise
    return prior


def restart(prior: list[str]) -> None:
    for unit in reversed(prior):
        deploy.user_systemctl("start", unit)


def backup() -> None:
    synthetic()
    with deploy.locked():
        prior = stop_writers()
        try:
            archive = pathlib.Path("/var/tmp/hermes-lab-state.tar")
            if archive.exists():
                raise deploy.DeployError("backup already exists")
            cmd(
                "/usr/bin/tar",
                "--xattrs",
                "--acls",
                "--numeric-owner",
                "-cpf",
                str(archive),
                "-C",
                str(HOME),
                *TREES,
            )
            os.chmod(archive, 0o600)
            os.chown(archive, __import__("pwd").getpwnam("labadmin").pw_uid, -1)
            print(json.dumps({"state_sha256": state_manifest()}))
        finally:
            restart(prior)


def validate_archive(archive):
    with tarfile.open(archive) as tar:
        for member in tar:
            parts = pathlib.PurePosixPath(member.name).parts
            if not parts or parts[0] not in TREES or ".." in parts or member.name.startswith("/"):
                raise deploy.DeployError("restore archive contains an unowned path")
            if not (member.isdir() or member.isfile() or member.issym()) or member.islnk():
                raise deploy.DeployError("restore archive contains an unsupported entry")
            if len(parts) == 1 and not member.isdir():
                raise deploy.DeployError("restore root must be a directory")
            if member.issym() and (
                member.linkname.startswith("/")
                or ".." in pathlib.PurePosixPath(member.linkname).parts
            ):
                raise deploy.DeployError("restore archive contains an unsafe symlink")


def restore(expected: str) -> None:
    synthetic()
    if not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise deploy.DeployError("expected state fingerprint is invalid")
    archive = RESTORE_ARCHIVE
    validate_archive(archive)
    with deploy.locked():
        stage = pathlib.Path(tempfile.mkdtemp(prefix=".lab-restore-", dir=HOME))
        fresh, old = stage / "new", stage / "old"
        fresh.mkdir()
        old.mkdir()
        prior = []
        moved = []
        restart_safe = False
        cleanup_safe = True
        try:
            # Extraction and metadata verification precede any service or state mutation.
            cmd(
                "/usr/bin/tar",
                "--xattrs",
                "--acls",
                "--numeric-owner",
                "-xpf",
                str(archive),
                "-C",
                str(fresh),
            )
            if state_manifest(fresh) != expected:
                raise deploy.DeployError("staged restore content or metadata differs from backup")
            if any((HOME / tree).is_symlink() or not (HOME / tree).is_dir() for tree in TREES):
                raise deploy.DeployError("restore targets are not ordinary directories")
            prior = stop_writers()
            cleanup_safe = False
            try:
                for tree in TREES:
                    os.replace(HOME / tree, old / tree)
                    moved.append(tree)
                    os.replace(fresh / tree, HOME / tree)
            except Exception:
                # Writers remain stopped during the complete rollback. If rollback
                # itself fails, retain the stage and do not restart partial state.
                for tree in reversed(moved):
                    if (HOME / tree).exists():
                        shutil.rmtree(HOME / tree)
                    os.replace(old / tree, HOME / tree)
                restart_safe = True
                cleanup_safe = True
                raise
            restart_safe = True
            cleanup_safe = True
            print(json.dumps({"state_sha256": state_manifest()}))
        finally:
            if restart_safe:
                restart(prior)
            if cleanup_safe:
                shutil.rmtree(stage)
                archive.unlink(missing_ok=True)


def sanitize() -> None:
    deploy.require_host()
    if any((HOME / name).exists() for name in TREES):
        raise deploy.DeployError("a deployed VM cannot become a reusable base")
    if not pathlib.Path("/var/lib/hermes-lab-builder").is_file():
        raise deploy.DeployError("dedicated builder marker is absent")
    # Run from a root transient system service, never the bootstrap SSH session.
    # The SSH command that scheduled this service may already have exited.
    # A missing logind user is acceptable only if no account process remains.
    deploy.command(["/usr/bin/loginctl", "terminate-user", "labadmin"], check=False)
    remaining = deploy.command(["/usr/bin/pgrep", "-u", "labadmin"], check=False)
    if remaining.returncode != 1:
        raise deploy.DeployError("bootstrap account processes remain or cannot be inspected")
    cmd("/usr/sbin/userdel", "--remove", "labadmin")
    pathlib.Path("/etc/sudoers.d/90-cloud-init-users").unlink(missing_ok=True)
    for path in pathlib.Path("/etc/ssh").glob("ssh_host_*"):
        path.unlink()
    for path in (pathlib.Path("/root/.ssh"), pathlib.Path("/var/log/journal"), EXPORT):
        if path.exists():
            shutil.rmtree(path)
    pathlib.Path("/var/lib/systemd/random-seed").unlink(missing_ok=True)
    cmd("/usr/bin/cloud-init", "clean", "--logs", "--machine-id", "--seed")
    pathlib.Path("/var/lib/hermes-lab-builder").unlink()
    pathlib.Path("/var/lib/hermes-lab-prepared").write_text("sanitized-v1\n")
    cmd("/usr/bin/sync")
    cmd("/usr/bin/systemctl", "poweroff")


def audit_base() -> None:
    deploy.require_host()
    if pathlib.Path("/var/lib/hermes-lab-prepared").read_text() != "sanitized-v1\n":
        raise deploy.DeployError("base sanitization marker is absent")
    if any((HOME / name).exists() for name in TREES):
        raise deploy.DeployError("prepared base contains application state")
    uid = __import__("pwd").getpwnam("hermes").pw_uid
    if pathlib.Path(f"/etc/containers/systemd/users/{uid}").exists():
        raise deploy.DeployError("prepared base contains application units")
    print("BASE_AUDIT=PASS no application state or units")


def fixture() -> None:
    synthetic()
    deploy.podman(
        "exec",
        "--user",
        "1000:1000",
        "hermes-worker",
        "sh",
        "-c",
        "umask 077; printf HERMES_RESTORE_OK > /home/worker/lab-marker.txt",
    )


def verify_fixture() -> None:
    synthetic()
    if (
        deploy.podman(
            "exec", "--user", "1000:1000", "hermes-worker", "cat", "/home/worker/lab-marker.txt"
        ).stdout
        != "HERMES_RESTORE_OK"
    ):
        raise deploy.DeployError("restored application fixture is missing")


def main() -> int:
    actions = {
        "fixture": fixture,
        "verify-fixture": verify_fixture,
        "stop": lambda: (synthetic(), stop_writers()),
        "export-images": export_images,
        "sanitize": sanitize,
        "audit-base": audit_base,
        "backup": backup,
        "restore": lambda: restore(sys.argv[2]),
        "identities": lambda: print(json.dumps(identities())),
        "inventory": lambda: print(json.dumps(inventory())),
    }
    try:
        if (
            len(sys.argv) not in (2, 3)
            or sys.argv[1] not in actions
            or (len(sys.argv) == 3) != (sys.argv[1] == "restore")
        ):
            raise deploy.DeployError("unknown lab guest operation")
        deploy.configure_profile()
        actions[sys.argv[1]]()
    except Exception as exc:
        # Guest output can contain application data. Only a fixed failure is exported.
        print(
            "STOP: "
            + (
                str(exc)
                if isinstance(exc, deploy.DeployError)
                else "synthetic lab guest operation failed (" + type(exc).__name__ + ")"
            ),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
