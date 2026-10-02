#!/usr/bin/env python3
"""Owned localhost SFTP/Restic fixture; synthetic data only, never an off-host proof."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import secrets
import shlex
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from production.primitives import Refused, atomic, canonical, read_json, regular, require, sha

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".toolbox/hermes-production-backup"
NAME = "hermes-preproduction-backup"
PORT = 22226
IMAGE = "sha256:4d7b3f8712ed95efeed6e6756ff70859d896ffeb5e7c04da31504b0fe8203e52"
ARCHIVE = ROOT / (
    ".toolbox/hermes-disposable/v2/prepared/"
    "f86703e758b5ac2d680e7a7c2077ead969b8768b5515b8cdf6c45d18451d3eb6/worker.oci"
)
ARCHIVE_SHA = "155c34c95b797f541fd2469ca63338d6fa00106318ec8171845c3a4d8f76c52a"
MIN_FREE = 20 * 1024**3
LABEL = "io.hermes.local-backup-owner"
CONFIG = b"""Port 2222
ListenAddress 0.0.0.0
HostKey /fixture/host_key
PidFile none
UsePAM no
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
AuthorizedKeysFile /fixture/authorized_keys
AllowUsers worker
StrictModes no
DisableForwarding yes
PermitTTY no
PermitUserEnvironment no
LogLevel ERROR
ChrootDirectory /srv
ForceCommand internal-sftp -d /repository
Subsystem sftp internal-sftp
"""
FIXED_FILES = (
    "server/sshd_config",
    "server/host_key",
    "server/host_key.pub",
    "server/authorized_keys",
    "client/key",
    "client/key.pub",
    "client/known_hosts",
    "client/password",
    "client/wrong_key",
    "client/wrong_key.pub",
    "client/wrong_hosts",
    "client/wrong_password",
)


def command(argv, *, check=True, timeout=180):
    """Capture output privately; never echo command output or secret-bearing errors."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("RESTIC_", "SSH_"))}
    env.update(LANG="C.UTF-8", LC_ALL="C.UTF-8")
    try:
        with subprocess.Popen(
            list(map(str, argv)),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            start_new_session=True,
        ) as process:
            try:
                out, err = process.communicate(timeout=timeout)
            except BaseException:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                raise
            result = subprocess.CompletedProcess(argv, process.returncode, out, err)
    except (OSError, subprocess.SubprocessError) as exc:
        raise Refused("command-unavailable-or-timeout") from exc
    if check:
        require(result.returncode == 0, "command-failed:" + Path(argv[0]).name)
    return result


def directory(path, *, private=True):
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid(), "unsafe-directory")
    require(not info.st_mode & (0o077 if private else 0o022), "unsafe-directory-mode")


def parent_check():
    for path in (BASE.parent, *BASE.parent.parents):
        require(stat.S_ISDIR(path.lstat().st_mode), "symlink-or-invalid-parent")
    directory(BASE.parent, private=False)


@contextmanager
def locked():
    parent_check()
    path = BASE.with_suffix(".lock")
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        info = os.fstat(fd)
        require(
            stat.S_ISREG(info.st_mode)
            and info.st_nlink == 1
            and info.st_uid == os.getuid()
            and not info.st_mode & 0o077,
            "unsafe-lock",
        )
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Refused("fixture-operation-in-progress") from exc
        yield
    finally:
        os.close(fd)


def plan(action):
    return {
        "status": "PREVIEW",
        "action": action,
        "container": NAME,
        "state": str(BASE),
        "listen": f"127.0.0.1:{PORT}",
        "memory_bytes": 256 * 1024**2,
        "cpus": 1,
        "pids": 64,
        "image": IMAGE,
        "minimum_free_bytes": MIN_FREE,
        "acceptance": "local synthetic file recovery only; off-host recovery unverified",
        "retention": "test stops the container; keys, encrypted data and reports retained",
    }


def available_port():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", PORT))
    except OSError as exc:
        raise Refused("localhost-port-in-use") from exc


def inspect_container():
    result = command(["podman", "container", "exists", NAME], check=False)
    require(result.returncode in (0, 1), "container-inventory-failed")
    if result.returncode == 1:
        return None
    return json.loads(command(["podman", "inspect", NAME]).stdout)[0]


def inventory(root):
    result = {}
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        require(not path.is_symlink(), "synthetic-tree-symlink")
        if path.is_dir():
            result[str(path.relative_to(root))] = {"directory": True}
        else:
            regular(path, owner=os.getuid())
            result[str(path.relative_to(root))] = {
                "sha256": sha(path),
                "mode": stat.S_IMODE(info.st_mode),
                "bytes": info.st_size,
            }
    return result


def keygen(path):
    command(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "fixture", "-f", path])
    path.chmod(0o600)
    path.with_suffix(".pub").chmod(0o600)


def initialize():
    require(not BASE.exists() and not BASE.is_symlink(), "unknown-state-preserved")
    BASE.mkdir(mode=0o700)
    for name in ("server", "client", "repository", "source", "restores", "reports"):
        (BASE / name).mkdir(mode=0o700)
    keygen(BASE / "server/host_key")
    keygen(BASE / "client/key")
    keygen(BASE / "client/wrong_key")
    atomic(BASE / "server/sshd_config", CONFIG)
    atomic(BASE / "server/authorized_keys", (BASE / "client/key.pub").read_bytes())
    for dest, source in (
        ("known_hosts", "server/host_key.pub"),
        ("wrong_hosts", "client/wrong_key.pub"),
    ):
        public = " ".join((BASE / source).read_text().split()[:2])
        atomic(BASE / "client" / dest, f"[127.0.0.1]:{PORT} {public}\n".encode())
    for name in ("password", "wrong_password"):
        atomic(BASE / "client" / name, (secrets.token_hex(32) + "\n").encode())
    (BASE / "source/nested").mkdir(mode=0o700)
    atomic(
        BASE / "source/marker.txt", ("Hermes synthetic backup " + secrets.token_hex(32)).encode()
    )
    atomic(BASE / "source/nested/binary.dat", bytes(range(256)) * 32)
    atomic(BASE / "source/empty", b"")
    atomic(BASE / "source/executable", b"#!/bin/sh\nexit 0\n", mode=0o700)
    state = {
        "schema": 1,
        "uid": os.getuid(),
        "base": str(BASE),
        "image": IMAGE,
        "owner": secrets.token_hex(16),
        "files": {p: sha(BASE / p) for p in FIXED_FILES},
        "source": inventory(BASE / "source"),
    }
    atomic(BASE / "ownership.json", canonical(state))
    return state


def read_state():
    directory(BASE)
    state = read_json(BASE / "ownership.json", owner=os.getuid())
    require(
        state["schema"] == 1
        and state["uid"] == os.getuid()
        and state["base"] == str(BASE)
        and state["image"] == IMAGE,
        "state-identity-drift",
    )
    require(
        len(state["owner"]) == 32 and all(c in "0123456789abcdef" for c in state["owner"]),
        "invalid-owner-token",
    )
    for name in ("server", "client", "repository", "source", "restores", "reports"):
        directory(BASE / name)
    require(set(state["files"]) == set(FIXED_FILES), "private-file-set-drift")
    for path, expected in state["files"].items():
        require(
            sha(regular(BASE / path, owner=os.getuid(), private=True)) == expected,
            "fixture-key-or-configuration-drift",
        )
    require((BASE / "server/sshd_config").read_bytes() == CONFIG, "sshd-policy-drift")
    require(inventory(BASE / "source") == state["source"], "synthetic-source-drift")
    return state


def validate_container(item, state):
    require(
        item["Name"].lstrip("/") == NAME
        and item["Image"].removeprefix("sha256:") == IMAGE.removeprefix("sha256:")
        and item["Config"]["Labels"].get(LABEL) == state["owner"],
        "container-owner-drift",
    )
    if "container_id" in state:
        require(item["Id"] == state["container_id"], "container-id-drift")
    config = item["HostConfig"]
    require(
        config["Memory"] == 256 * 1024**2
        and config["PidsLimit"] == 64
        and config["NanoCpus"] == 10**9,
        "container-resource-drift",
    )
    require(
        config["ReadonlyRootfs"]
        and not config["Privileged"]
        and "no-new-privileges" in config["SecurityOpt"],
        "container-security-drift",
    )
    require(
        config["PortBindings"] == {"2222/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(PORT)}]},
        "container-port-drift",
    )
    require(
        config["UsernsMode"] == "private"
        and item["Config"]["User"] == "0:0"
        and all(
            config["IDMappings"][kind][:2] == ["0:1:1000", "1000:0:1"]
            for kind in ("UidMap", "GidMap")
        ),
        "container-userns-drift",
    )
    require(
        item["Config"]["Cmd"] == ["/usr/sbin/sshd", "-D", "-e", "-f", "/fixture/sshd_config"],
        "container-command-drift",
    )
    binds = {
        m["Destination"]: (m["Source"], m["RW"]) for m in item["Mounts"] if m["Type"] == "bind"
    }
    require(
        len(item["Mounts"]) == 2
        and binds
        == {
            "/fixture": (str(BASE / "server"), False),
            "/srv/repository": (str(BASE / "repository"), True),
        },
        "container-mount-drift",
    )
    caps = {c.removeprefix("CAP_") for c in item["EffectiveCaps"]}
    require(
        caps == {"DAC_OVERRIDE", "SETUID", "SETGID", "SYS_CHROOT"}, "container-capability-drift"
    )


def ensure_up():
    require(
        command(["podman", "info", "--format", "{{.Host.Security.Rootless}}"]).stdout.strip()
        == b"true",
        "rootless-podman-required",
    )
    item = inspect_container()
    if BASE.exists() or BASE.is_symlink():
        state = read_state()
        if item is not None:
            validate_container(item, state)
        else:
            require("container_id" not in state, "owned-container-missing-preserve-state")
    else:
        require(item is None, "container-name-conflict")
        state = None
    if item is not None and item["State"]["Running"]:
        return state, item
    require(shutil.disk_usage(BASE.parent).free >= MIN_FREE, "host-free-space-low")
    available_port()
    if state is None:
        state = initialize()
    if item is None:
        exists = command(["podman", "image", "exists", IMAGE], check=False)
        require(exists.returncode in (0, 1), "image-inventory-failed")
        if exists.returncode == 1:
            require(
                sha(regular(ARCHIVE, owner=os.getuid())) == ARCHIVE_SHA, "image-archive-mismatch"
            )
            command(["podman", "load", "--input", ARCHIVE], timeout=300)
        command(["podman", "image", "exists", IMAGE])
        command(
            [
                "podman",
                "create",
                "--name",
                NAME,
                "--label",
                f"{LABEL}={state['owner']}",
                "--pull=never",
                "--memory=256m",
                "--cpus=1",
                "--pids-limit=64",
                "--userns=keep-id:uid=1000,gid=1000",
                "--user=0:0",
                "--read-only",
                "--read-only-tmpfs=false",
                "--tmpfs=/run/sshd:rw,nosuid,nodev,noexec,mode=0755",
                "--security-opt=no-new-privileges",
                "--cap-drop=ALL",
                "--cap-add=DAC_OVERRIDE,SETUID,SETGID,SYS_CHROOT",
                "--publish",
                f"127.0.0.1:{PORT}:2222/tcp",
                "--volume",
                f"{BASE / 'server'}:/fixture:ro,Z",
                "--volume",
                f"{BASE / 'repository'}:/srv/repository:rw,Z",
                IMAGE,
                "/usr/sbin/sshd",
                "-D",
                "-e",
                "-f",
                "/fixture/sshd_config",
            ]
        )
        item = inspect_container()
        validate_container(item, state)
    state["container_id"] = item["Id"]
    atomic(BASE / "ownership.json", canonical(state))
    command(["podman", "start", item["Id"]])
    item = inspect_container()
    validate_container(item, state)
    require(item["State"]["Running"], "container-not-running")
    return state, item


def stop_owned():
    item = inspect_container()
    if not BASE.exists() and not BASE.is_symlink():
        require(item is None, "container-name-conflict")
        return "absent"
    state = read_state()
    if item is None:
        require("container_id" not in state, "owned-container-missing-preserve-state")
        return "not-created"
    validate_container(item, state)
    if not item["State"]["Running"]:
        return "already-stopped"
    command(["podman", "stop", "--time", "10", item["Id"]])
    item = inspect_container()
    validate_container(item, state)
    require(not item["State"]["Running"], "container-stop-failed")
    return "stopped"


def ssh_args(*, wrong_key=False, wrong_host=False):
    return [
        "ssh",
        "-F",
        "/dev/null",
        "-p",
        str(PORT),
        "-i",
        str(BASE / "client" / ("wrong_key" if wrong_key else "key")),
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "IdentityAgent=none",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "UserKnownHostsFile="
        + str(BASE / "client" / ("wrong_hosts" if wrong_host else "known_hosts")),
        "-o",
        "GlobalKnownHostsFile=/dev/null",
        "-o",
        "ClearAllForwardings=yes",
        "-o",
        "ConnectTimeout=5",
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=2",
        "-T",
        "-s",
        "worker@127.0.0.1",
        "sftp",
    ]


def restic(*args, wrong_password=False, wrong_key=False, wrong_host=False, check=True):
    return command(
        [
            "toolbox",
            "run",
            "--container",
            "dev-infra-hermes",
            "env",
            "--chdir=" + str(BASE / "source"),
            "restic",
            "--no-cache",
            "--repo",
            "sftp:worker@127.0.0.1:/repository",
            "--password-file",
            BASE / "client" / ("wrong_password" if wrong_password else "password"),
            "-o",
            "sftp.connections=1",
            "-o",
            "sftp.command=" + shlex.join(ssh_args(wrong_key=wrong_key, wrong_host=wrong_host)),
            *args,
        ],
        check=check,
        timeout=300,
    )


def wait_ready():
    # A real pinned-key SFTP handshake, never a successful TCP-only readiness claim.
    for _ in range(10):
        result = command(ssh_args(), check=False, timeout=10)
        if result.returncode == 0:
            return
        time.sleep(0.5)
    raise Refused("pinned-sftp-not-ready")


def snapshots():
    return json.loads(restic("snapshots", "--json").stdout)


def exercise(state, item):
    wait_ready()
    for args in ({"wrong_key": True}, {"wrong_host": True}):
        require(command(ssh_args(**args), check=False).returncode == 255, "ssh-negative-accepted")
    config = BASE / "repository/config"
    if not config.exists():
        require(not any((BASE / "repository").iterdir()), "partial-repository-preserved")
        restic("init")
    require(
        restic("snapshots", wrong_password=True, check=False).returncode == 12,
        "wrong-restic-password-not-rejected",
    )
    before = snapshots()
    require(
        len(before) <= 1
        and all(
            row["hostname"] == NAME
            and row["tags"] == [state["owner"]]
            and row["paths"] == [str(BASE / "source")]
            for row in before
        ),
        "unexpected-repository-snapshots",
    )
    restic(
        "backup",
        "--json",
        "--skip-if-unchanged",
        "--host",
        NAME,
        "--tag",
        state["owner"],
        ".",
    )
    after = snapshots()
    require(
        len(after) == 1 and (not before or after[0]["id"] == before[0]["id"]),
        "snapshot-rerun-duplicated",
    )
    restic("check", "--read-data")
    attempt = BASE / "restores" / secrets.token_hex(8)
    attempt.mkdir(mode=0o700)
    restic("restore", after[0]["id"], "--target", attempt, "--verify")
    require(inventory(attempt) == state["source"], "restored-content-or-mode-mismatch")
    marker = (BASE / "source/marker.txt").read_bytes()
    for path in (BASE / "repository").rglob("*"):
        if path.is_file():
            require(marker not in path.read_bytes(), "plaintext-marker-in-repository")
    validate_container(inspect_container(), state)
    return {
        "status": "PASS",
        "scope": "local synthetic files only",
        "container_id": item["Id"],
        "snapshot_id": after[0]["id"],
        "snapshot_count": 1,
        "unchanged_rerun": bool(before),
        "checks": [
            "pinned SFTP",
            "wrong SSH key rejected",
            "wrong host key rejected",
            "wrong Restic password rejected",
            "Restic read-data integrity",
            "restored content and file modes",
            "no plaintext marker in repository",
            "container identity, binding, resources, mounts and security",
        ],
        "source_files": state["source"],
        "restore": str(attempt.relative_to(BASE)),
        "offhost_recovery": "NOT_VERIFIED",
        "application_recovery": "NOT_RUN",
    }


def test_fixture():
    report = {"status": "FAIL", "scope": "local synthetic files only"}
    started = False
    try:
        state, item = ensure_up()
        started = True
        report = exercise(state, item)
    except (Refused, OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        report["error"] = str(exc) if isinstance(exc, Refused) else type(exc).__name__
    finally:
        # Also inspect matching partial creations if startup raised after podman create/start.
        if started or (BASE / "ownership.json").is_file():
            try:
                report["stop"] = stop_owned()
            except (Refused, OSError, ValueError, KeyError, TypeError, IndexError):
                report.update(status="FAIL", stop="FAILED_REVIEW_REQUIRED")
    if (BASE / "ownership.json").is_file():
        read_state()
        atomic(BASE / "reports" / (secrets.token_hex(8) + ".json"), canonical(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("up", "test", "stop", "status"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        if args.action != "status" and not args.apply:
            result = plan(args.action)
        else:
            with locked():
                if args.action == "test":
                    result = test_fixture()
                elif args.action == "stop":
                    result = {"status": "PASS", "container": stop_owned()}
                elif args.action == "up":
                    _, item = ensure_up()
                    result = {"status": "PASS", "container_id": item["Id"], "running": True}
                elif not BASE.exists() and not BASE.is_symlink():
                    require(inspect_container() is None, "container-name-conflict")
                    result = {"status": "ABSENT"}
                else:
                    state = read_state()
                    item = inspect_container()
                    require(item is not None, "owned-container-missing-preserve-state")
                    validate_container(item, state)
                    result = {
                        "status": "PRESENT",
                        "container_id": item["Id"],
                        "running": item["State"]["Running"],
                        "state": str(BASE),
                    }
        print(json.dumps(result, sort_keys=True, indent=2))
        return int(result["status"] == "FAIL")
    except (Refused, OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print(
            json.dumps(
                {
                    "status": "REFUSED",
                    "reason": str(exc) if isinstance(exc, Refused) else type(exc).__name__,
                }
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
