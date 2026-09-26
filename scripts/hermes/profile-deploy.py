#!/usr/bin/env python3
"""Converge the rootless Hermes gateway and isolated worker on a Fedora guest.

``prepare`` installs the ordinary Fedora runtime packages and caches the pinned
gateway and credential-free worker images. It is safe to run before capturing a
reusable Cloud image. ``apply`` adds per-instance SSH identities, applies the
reviewed profile contract, and starts the Quadlets. Synthetic mode is the
default and gives the gateway no network. Live mode requires a separately
provisioned, tmpfs-backed profile environment; this program never receives a
provider or bot credential as an argument or environment variable.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import pathlib
import pwd
import stat
import subprocess
import sys
import tempfile
from contextlib import contextmanager

HERE = pathlib.Path(__file__).resolve().parent
MANUAL = HERE / "manual"
HOME = pathlib.Path("/home/hermes")
GATEWAY_STATE = HOME / "gateway-state"
GATEWAY_SSH = HOME / "gateway-ssh"
WORKER_STATE = HOME / "worker-state"
TRANSPORT = HOME / "transport"
WORKER_IMAGE = "localhost/hermes-worker:1"
PACKAGES = ("podman", "container-selinux", "passt", "openssh-clients", "policycoreutils")
SYNTHETIC_KEY = "synthetic-hermes-lab-only"


class DeployError(RuntimeError):
    pass


def command(
    argv: list[str], *, user: bool = False, check: bool = True
) -> subprocess.CompletedProcess[str]:
    operation = pathlib.Path(argv[0]).name
    if operation == "podman" and len(argv) > 1:
        operation += f" {argv[1]}"
    if user:
        uid = pwd.getpwnam("hermes").pw_uid
        argv = [
            "/usr/sbin/runuser",
            "-u",
            "hermes",
            "--",
            "/usr/bin/env",
            "-i",
            f"HOME={HOME}",
            "USER=hermes",
            "LOGNAME=hermes",
            "PATH=/usr/local/bin:/usr/bin:/bin",
            f"XDG_RUNTIME_DIR=/run/user/{uid}",
            f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus",
            *argv,
        ]
    result = subprocess.run(
        argv, capture_output=True, text=True, check=False, cwd=HOME if user else None
    )
    if check and result.returncode:
        # Command output can include application data. Do not copy it into the
        # terminal, journal, or a report while credentials may be provisioned.
        raise DeployError(f"{operation} failed (exit {result.returncode})")
    return result


def podman(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return command(["/usr/bin/podman", *args], user=True, check=check)


def user_systemctl(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return command(["/usr/bin/systemctl", "--user", *args], user=True, check=check)


def active(unit: str) -> bool:
    result = user_systemctl("is-active", unit, check=False)
    return result.returncode == 0 and result.stdout.strip() == "active"


@contextmanager
def locked():
    path = pathlib.Path("/run/lock/hermes-profile-deploy.lock")
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_CLOEXEC, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(fd)
        raise DeployError("another profile deployment is running") from exc
    try:
        yield
    finally:
        os.close(fd)


def require_host():
    if os.geteuid() != 0:
        raise DeployError("run as root inside the reviewed guest")
    if command(["/usr/sbin/getenforce"]).stdout.strip() != "Enforcing":
        raise DeployError("SELinux must be Enforcing")
    for path in (
        MANUAL / "manifest.yaml",
        MANUAL / "worker/Containerfile",
        MANUAL / "quadlets/hermes-gateway.container",
    ):
        if not path.is_file():
            raise DeployError(f"deployment source is incomplete: {path.name}")


def pinned_gateway() -> str:
    unit = (MANUAL / "quadlets/hermes-gateway.container").read_text()
    refs = [
        line.split("=", 1)[1].strip() for line in unit.splitlines() if line.startswith("Image=")
    ]
    if len(refs) != 1 or not refs[0].startswith("docker.io/nousresearch/hermes-agent@sha256:"):
        raise DeployError("gateway Quadlet must name one immutable Hermes digest")
    digest = refs[0].rsplit(":", 1)[1]
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise DeployError("gateway image digest is malformed")
    manifest = (MANUAL / "manifest.yaml").read_text()
    if f"ref: {refs[0]}" not in manifest:
        raise DeployError("gateway Quadlet does not match the release manifest")
    return refs[0]


def ensure_directory(path: pathlib.Path, mode: int, uid: int, gid: int) -> bool:
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise DeployError(f"unexpected path type: {path}")
    created = not path.exists()
    if created:
        path.mkdir(parents=True, mode=mode)
        os.chown(path, uid, gid)
    current = path.stat()
    if stat.S_IMODE(current.st_mode) != mode:
        os.chmod(path, mode)
    if not created and current.st_uid not in (uid, 0):
        mapped = {GATEWAY_STATE: "10000", WORKER_STATE / "home": "1000"}.get(path)
        if (
            mapped is None
            or podman("unshare", "stat", "-c", "%u", str(path)).stdout.strip() != mapped
        ):
            raise DeployError(f"unexpected directory owner: {path}")
    return created


def write_file(path: pathlib.Path, data: bytes, mode: int, uid: int, gid: int) -> bool:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise DeployError(f"unexpected file type: {path}")
    if path.exists() and path.read_bytes() == data:
        current = path.stat()
        if stat.S_IMODE(current.st_mode) != mode:
            os.chmod(path, mode)
        if current.st_uid != uid or current.st_gid != gid:
            os.chown(path, uid, gid)
        return False
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, mode)
        os.chown(tmp, uid, gid)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return True


def worker_source_hash() -> str:
    h = hashlib.sha256()
    for path in sorted((MANUAL / "worker").iterdir()):
        if not path.is_file():
            continue
        h.update(path.name.encode() + b"\0")
        h.update(path.read_bytes())
    return h.hexdigest()


def ensure_user() -> tuple[int, int]:
    try:
        account = pwd.getpwnam("hermes")
    except KeyError:
        command(
            [
                "/usr/sbin/useradd",
                "--create-home",
                "--user-group",
                "--home-dir",
                str(HOME),
                "--shell",
                "/bin/bash",
                "hermes",
            ]
        )
        account = pwd.getpwnam("hermes")
    if account.pw_dir != str(HOME) or account.pw_uid == 0:
        raise DeployError("unexpected Hermes runtime identity")
    wheel = command(["/usr/bin/id", "-nG", "hermes"]).stdout.split()
    if "wheel" in wheel:
        raise DeployError("Hermes runtime user must not have administrative access")
    command(["/usr/bin/loginctl", "enable-linger", "hermes"])
    command(["/usr/bin/systemctl", "start", f"user@{account.pw_uid}.service"])
    return account.pw_uid, account.pw_gid


def prepare() -> bool:
    missing = [
        name for name in PACKAGES if command(["/usr/bin/rpm", "-q", name], check=False).returncode
    ]
    if missing:
        command(["/usr/bin/dnf", "-y", "install", *missing])
    uid, gid = ensure_user()
    ensure_directory(HOME / ".cache", 0o700, uid, gid)
    gateway = pinned_gateway()
    changed = bool(missing)
    if podman("image", "exists", gateway, check=False).returncode:
        podman("pull", gateway)
        changed = True
    stamp = HOME / ".cache/hermes-worker-build.sha256"
    want = worker_source_hash()
    have = stamp.read_text().strip() if stamp.exists() else ""
    image_present = podman("image", "exists", WORKER_IMAGE, check=False).returncode == 0
    if have != want or not image_present:
        podman(
            "build",
            "--tag",
            WORKER_IMAGE,
            "--file",
            str(MANUAL / "worker/Containerfile"),
            str(MANUAL / "worker"),
        )
        write_file(stamp, (want + "\n").encode(), 0o600, uid, gid)
        changed = True
    print(
        f"PREPARE={'CHANGED' if changed else 'UNCHANGED'} gateway_digest={gateway.rsplit(':', 1)[1]} worker_source_sha256={want}"
    )
    return changed


def keypair(path: pathlib.Path) -> bool:
    public = pathlib.Path(str(path) + ".pub")
    if path.exists() != public.exists():
        raise DeployError(f"incomplete SSH keypair: {path.name}")
    if path.exists():
        if path.is_symlink() or public.is_symlink():
            raise DeployError("SSH identity is a symlink")
        return False
    command(["/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(path)], user=True)
    os.chmod(path, 0o600)
    os.chmod(public, 0o644)
    return True


def map_gateway_uid(path: pathlib.Path):
    current = podman("unshare", "stat", "-c", "%u", str(path)).stdout.strip()
    if current != "10000":
        podman("unshare", "chown", "10000:10000", str(path))


def ensure_instance(uid: int, gid: int, mode: str) -> bool:
    changed = False
    for path, permissions in (
        (GATEWAY_STATE, 0o700),
        (GATEWAY_SSH, 0o711),
        (TRANSPORT, 0o711),
        (WORKER_STATE, 0o700),
        (WORKER_STATE / "home", 0o700),
        (WORKER_STATE / "ssh-host-keys", 0o700),
        (WORKER_STATE / "authorized_keys", 0o755),
    ):
        changed |= ensure_directory(path, permissions, uid, gid)
    client = GATEWAY_SSH / "worker_client_ed25519"
    host = WORKER_STATE / "ssh-host-keys/ssh_host_ed25519_key"
    changed |= keypair(client)
    changed |= keypair(host)
    client_public = pathlib.Path(str(client) + ".pub").read_bytes()
    host_public = pathlib.Path(str(host) + ".pub").read_bytes()
    authorized = WORKER_STATE / "authorized_keys/worker"
    known = GATEWAY_SSH / "known_hosts"
    if authorized.exists() and authorized.read_bytes() != client_public:
        raise DeployError("worker authorization key changed; rotate deliberately")
    if known.exists() and known.read_bytes() != b"worker " + host_public:
        raise DeployError("worker SSH host pin changed; rotate deliberately")
    changed |= write_file(authorized, client_public, 0o644, uid, gid)
    changed |= write_file(known, b"worker " + host_public, 0o644, uid, gid)
    for name in ("ssh", "scp", "sftp", "unix-bridge.py"):
        changed |= write_file(
            GATEWAY_SSH / name, (MANUAL / "gateway" / name).read_bytes(), 0o755, uid, gid
        )
    for source, target in (
        ("harden-config.py", "harden-config.py"),
        ("set-model.py", "set-model.py"),
        ("profile-contract.yaml", "profile-contract.yaml"),
    ):
        changed |= write_file(
            GATEWAY_SSH / target, (MANUAL / "config" / source).read_bytes(), 0o644, uid, gid
        )
    map_gateway_uid(client)
    map_gateway_uid(GATEWAY_STATE)
    if mode == "synthetic":
        env_file = GATEWAY_STATE / ".env"
        if env_file.exists():
            lines = env_file.read_text().splitlines()
            if f"DEEPSEEK_API_KEY={SYNTHETIC_KEY}" not in lines or any(
                line.startswith(("TELEGRAM_BOT_TOKEN=", "TELEGRAM_ALLOWED_USERS="))
                for line in lines
            ):
                raise DeployError("synthetic mode refuses an existing live profile environment")
        else:
            changed |= write_file(
                env_file, f"DEEPSEEK_API_KEY={SYNTHETIC_KEY}\n".encode(), 0o600, uid, gid
            )
            map_gateway_uid(env_file)
    else:
        filesystem = command(
            ["/usr/bin/findmnt", "-n", "-o", "FSTYPE", "--target", str(GATEWAY_STATE)]
        ).stdout.strip()
        if filesystem != "tmpfs":
            raise DeployError("live profile state must be mounted on tmpfs")
        if command(["/usr/sbin/swapon", "--noheadings"]).stdout.strip():
            raise DeployError("disable guest swap before provisioning live credentials")
        env_file = GATEWAY_STATE / ".env"
        if not env_file.is_file() or stat.S_IMODE(env_file.stat().st_mode) != 0o600:
            raise DeployError("private live profile environment is missing or has wrong mode")
        keys = {line.split("=", 1)[0] for line in env_file.read_text().splitlines() if "=" in line}
        if not {"DEEPSEEK_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_USERS"} <= keys:
            raise DeployError("private live profile environment lacks required entries")
        map_gateway_uid(env_file)
    return changed


def model_check() -> bool:
    code = (
        "import pathlib,yaml; c=yaml.safe_load(pathlib.Path('/opt/data/config.yaml').read_text()); "
        "m=c.get('model') or {}; assert c.get('provider') in (None,'deepseek') and "
        "c.get('default_model')=='deepseek-flash' and m.get('provider')=='deepseek' "
        "and m.get('default')=='deepseek-flash' and 'base_url' not in m; "
        "from hermes_cli.runtime_provider import resolve_runtime_provider; "
        "r=resolve_runtime_provider(target_model='deepseek-flash'); "
        "assert r.get('provider')=='deepseek' and r.get('base_url')=='https://api.deepseek.com/v1'"
    )
    result = podman(
        "exec",
        "--user",
        "10000:10000",
        "hermes-gateway",
        "/opt/hermes/.venv/bin/python3",
        "-c",
        code,
        check=False,
    )
    return result.returncode == 0


def config_current() -> bool:
    if not active("hermes-gateway.service"):
        return False
    checked = podman(
        "exec",
        "--user",
        "10000:10000",
        "hermes-gateway",
        "/opt/hermes/.venv/bin/python3",
        "/opt/hermes/gateway-ssh/harden-config.py",
        "--check",
        check=False,
    )
    return checked.returncode == 0 and model_check()


def configure(gateway: str):
    mounts = (
        "--volume",
        f"{GATEWAY_STATE}:/opt/data:z",
        "--volume",
        f"{GATEWAY_SSH}:/opt/hermes/gateway-ssh:ro,z",
    )
    prefix = (
        "run",
        "--rm",
        "--network",
        "none",
        "--user",
        "10000:10000",
        *mounts,
        "--entrypoint",
        "/opt/hermes/.venv/bin/python3",
    )
    podman(*prefix, gateway, "/opt/hermes/gateway-ssh/harden-config.py")
    podman(
        "run",
        "--rm",
        "--network",
        "none",
        "--user",
        "10000:10000",
        *mounts,
        "--env",
        "HERMES_PROVIDER=deepseek",
        "--env",
        "HERMES_MODEL=deepseek-flash",
        "--entrypoint",
        "/opt/hermes/.venv/bin/python3",
        gateway,
        "/opt/hermes/gateway-ssh/set-model.py",
    )


def install_quadlets(uid: int, mode: str) -> bool:
    target = pathlib.Path(f"/etc/containers/systemd/users/{uid}")
    ensure_directory(target, 0o755, 0, 0)
    changed = False
    for name in ("hermes-worker.container", "hermes-gateway.container"):
        content = (MANUAL / "quadlets" / name).read_text()
        if name == "hermes-gateway.container" and mode == "synthetic":
            content = content.replace("[Container]\n", "[Container]\nNetwork=none\n", 1)
        changed |= write_file(target / name, content.encode(), 0o644, 0, 0)
    if changed:
        command(["/usr/sbin/restorecon", "-R", str(target)])
    user_systemctl("daemon-reload")
    return changed


def verify(mode: str):
    if not active("hermes-worker.service") or not active("hermes-gateway.service"):
        raise DeployError("Hermes services are not both active")
    for container, expected in (
        ("hermes-worker", "none"),
        ("hermes-gateway", "none" if mode == "synthetic" else ""),
    ):
        network = podman(
            "inspect", "--format", "{{.HostConfig.NetworkMode}}", container
        ).stdout.strip()
        if expected and network != expected:
            raise DeployError(f"{container} has unexpected network mode")
    worker = json.loads(podman("inspect", "hermes-worker").stdout)[0]
    env_names = {entry.split("=", 1)[0] for entry in worker.get("Config", {}).get("Env", [])}
    if env_names & {"DEEPSEEK_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_USERS"}:
        raise DeployError("provider or bot configuration reached the offline worker")
    mount_sources = {item.get("Source") for item in worker.get("Mounts", [])}
    if str(GATEWAY_STATE) in mount_sources or str(GATEWAY_SSH) in mount_sources:
        raise DeployError("gateway private state is mounted into the offline worker")
    result = podman(
        "exec",
        "--user",
        "10000:10000",
        "hermes-gateway",
        "/opt/hermes/bin/ssh",
        "-o",
        "BatchMode=yes",
        "worker@worker",
        "printf HERMES_WORKER_OK",
    )
    if result.stdout.strip() != "HERMES_WORKER_OK":
        raise DeployError("gateway-to-worker SSH round trip failed")
    print("STATUS=PASS worker=active gateway=active worker_network=none")


def apply(mode: str):
    prepared = prepare()
    uid, gid = ensure_user()
    was_active = active("hermes-gateway.service")
    worker_was_active = active("hermes-worker.service")
    instance_changed = ensure_instance(uid, gid, mode)
    current = config_current() if was_active and not instance_changed else False
    gateway = pinned_gateway()
    if was_active and not current:
        user_systemctl("stop", "hermes-gateway.service")
    worker_restart = False
    gateway_restart = False
    try:
        if not current:
            configure(gateway)
        units_changed = install_quadlets(uid, mode)
        worker_restart = (
            prepared
            or instance_changed
            or units_changed
            or not worker_was_active
            or not active("hermes-worker.service")
        )
        if worker_restart:
            user_systemctl("restart", "hermes-worker.service")
        gateway_restart = (
            prepared
            or instance_changed
            or units_changed
            or not current
            or not active("hermes-gateway.service")
        )
        if gateway_restart:
            user_systemctl("restart", "hermes-gateway.service")
        verify(mode)
    except Exception:
        if was_active and not active("hermes-gateway.service"):
            user_systemctl("start", "hermes-gateway.service", check=False)
        raise
    changed = prepared or instance_changed or units_changed or worker_restart or gateway_restart
    print(f"DEPLOY={'CHANGED' if changed else 'UNCHANGED'} mode={mode}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "apply", "status"))
    parser.add_argument("--mode", choices=("synthetic", "live"), default="synthetic")
    args = parser.parse_args(argv)
    try:
        require_host()
        with locked():
            if args.action == "prepare":
                prepare()
            elif args.action == "apply":
                apply(args.mode)
            else:
                verify(args.mode)
    except DeployError as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
