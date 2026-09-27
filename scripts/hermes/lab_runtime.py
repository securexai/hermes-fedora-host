"""Owned local instances and immutable prepared caches for the Hermes lab."""

from __future__ import annotations

import copy
import fcntl
import importlib.util
import json
import os
import pathlib
import re
import socket
import subprocess
import time
from contextlib import contextmanager

from lab_profile import digest, file_hash, validate

ROOT = pathlib.Path(__file__).resolve().parents[2]
STATE = ROOT / ".toolbox/hermes-disposable/v2"
GUEST = "sudo -n python3 /opt/hermes-deploy/scripts/hermes/lab_guest.py "


class LabError(RuntimeError):
    pass


def vm_module():
    spec = importlib.util.spec_from_file_location("disposable", ROOT / "vm/hermes-disposable.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checked(argv, timeout=1800):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise LabError(
            f"{pathlib.Path(argv[0]).name} failed (exit {result.returncode}; output suppressed)"
        )
    return result


def safe_path(path: pathlib.Path) -> None:
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise LabError("lab path contains a symlink")
        if parent == ROOT:
            break


def directory(path: pathlib.Path):
    safe_path(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.stat().st_uid != os.getuid():
        raise LabError("lab directory ownership changed")
    path.chmod(0o700)


def write_json(path: pathlib.Path, value):
    safe_path(path)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("x") as stream:
        os.chmod(temp, 0o600)
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


@contextmanager
def lock(name):
    directory(STATE / "locks")
    path = STATE / "locks" / (name + ".lock")
    safe_path(path)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise LabError("another operation owns this lab lock") from None
        yield
    finally:
        os.close(fd)


def source_identity():
    files = (
        *vm_module().SOURCE_FILES,
        "vm/hermes-disposable.py",
        "scripts/hermes/lab.py",
        "scripts/hermes/lab_runtime.py",
        "tests/hermes-synthetic-smoke.py",
        "tests/test_hermes_lab.py",
        "tests/test_hermes_disposable.py",
        "tests/offline_allowlist.txt",
        "scripts/hermes/lab-profiles/baseline.json",
        "scripts/hermes/lab-profiles/candidate.json",
        "docs/HERMES_DISPOSABLE_LAB.md",
    )
    return {name: file_hash(ROOT / name) for name in sorted(set(files))}


def cache_key(profile):
    files = [
        "scripts/hermes/profile-deploy.py",
        "scripts/hermes/lab_guest.py",
        "scripts/hermes/lab_profile.py",
        "scripts/hermes/lab_runtime.py",
        "vm/hermes-disposable.py",
    ]
    files += [
        str(p.relative_to(ROOT))
        for p in (ROOT / "scripts/hermes/manual/worker").iterdir()
        if p.is_file()
    ]
    module = vm_module()
    return digest(
        {
            "format": 1,
            "preparation_revision": profile["preparation_revision"],
            "fedora": module.IMAGE,
            "fedora_sha256": module.BASE_SHA256,
            "signer": module.SIGNER,
            "gateway": profile["gateway_image"],
            "inputs": {name: file_hash(ROOT / name) for name in sorted(files)},
        }
    )


def read_cache(profile):
    key = cache_key(profile)
    path = STATE / "prepared" / key
    safe_path(path)
    if not path.is_dir():
        raise LabError("prepared cache missing; run prepare --apply")
    if {p.name for p in path.iterdir()} != {
        "base.qcow2",
        "gateway.oci",
        "worker.oci",
        "manifest.json",
    }:
        raise LabError("prepared cache is incomplete or has unexpected files")
    if any(
        p.is_symlink() or not p.is_file() or p.stat().st_uid != os.getuid() for p in path.iterdir()
    ):
        raise LabError("prepared cache has unsafe files")
    manifest = json.loads((path / "manifest.json").read_text())
    if manifest.get("key") != key or manifest.get("gateway_ref") != profile["gateway_image"]:
        raise LabError("prepared cache identity mismatch")
    for name in ("gateway_id", "worker_id"):
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", manifest.get(name, "")):
            raise LabError("prepared cache image identity is invalid")
    for name in ("base.qcow2", "gateway.oci", "worker.oci"):
        target = path / name
        if target.is_symlink() or file_hash(target) != manifest["files"].get(name):
            raise LabError("prepared cache checksum mismatch")
    return path, manifest


class Instance:
    def __init__(self, name: str, profile: dict):
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", name):
            raise LabError("instance name must be 1-32 lowercase letters, digits or hyphens")
        self.name = name
        self.profile = validate(profile)
        self.path = STATE / "instances" / name
        safe_path(self.path)
        self.vm = vm_module()
        self.vm.INSTANCE = self.path
        self.vm.NAME = "hermes-lab-" + name
        self.vm.PROFILE = self.profile
        self.vm.GUARDED = True
        marker = self.path / "identity.json"
        if marker.exists():
            safe_path(marker)
            port = json.loads(marker.read_text()).get("port")
            if type(port) is not int or not 22000 <= port <= 22999:
                raise LabError("instance port identity is invalid")
            self.vm.PORT = port

    def exists(self):
        return self.vm.domain_exists() or self.path.exists()

    def artifacts(self, manifest):
        self.vm.WORKER_ID = manifest["worker_id"]
        self.vm.GATEWAY_ID = manifest["gateway_id"]

    def copy_from(self, remote, target):
        self.vm.assert_identity()
        args = self.vm.ssh_base()
        checked(
            [
                "scp",
                "-i",
                args[2],
                "-P",
                str(self.vm.PORT),
                *args[5:-1],
                "labadmin@127.0.0.1:" + remote,
                str(target),
            ]
        )

    def copy_to(self, source, remote):
        self.vm.assert_identity()
        args = self.vm.ssh_base()
        checked(
            [
                "scp",
                "-i",
                args[2],
                "-P",
                str(self.vm.PORT),
                *args[5:-1],
                str(source),
                "labadmin@127.0.0.1:" + remote,
            ]
        )

    def boot(self, base):
        with lock("ports"):
            if self.exists():
                raise LabError("instance already exists; inspect or clean it explicitly")
            reserved = set()
            for path in (STATE / "instances").glob("*/identity.json"):
                safe_path(path)
                reserved.add(json.loads(path.read_text()).get("port"))
            for port in range(22222, 23000):
                if port in reserved:
                    continue
                with socket.socket() as sock:
                    try:
                        sock.bind(("127.0.0.1", port))
                    except OSError:
                        continue
                    self.vm.PORT = port
                    break
            else:
                raise LabError("no free lab loopback SSH port")
            # virt-install detects any external race for the selected port.
            self.vm.fresh_run(base, deploy_now=False)
        self.vm.guest(
            "cloud-init status --wait >/dev/null && test $(getenforce) = Enforcing", timeout=600
        )

    def require_synthetic(self):
        # The bootstrap account cannot traverse the runtime's private home.
        # Inspect as guest root, and permit the absent home of a stock image.
        result = self.vm.guest(
            "sudo -n python3 -c \"import pathlib,os; p=pathlib.Path('/home/hermes/gateway-state'); assert not p.is_symlink() and not os.path.ismount(p)\"",
            check=False,
        )
        if result.returncode:
            raise LabError(
                "synthetic operation refuses an unsafe or mounted gateway state; use live-stop first"
            )

    def install_artifacts(self, cache, manifest):
        self.require_synthetic()
        self.artifacts(manifest)
        self.vm.transfer_source()
        # Prepare the unprivileged account without pulling or building images.
        self.vm.guest(
            "rpm -q podman container-selinux passt openssh-clients policycoreutils >/dev/null || sudo -n dnf -y install podman container-selinux passt openssh-clients policycoreutils >/dev/null",
            timeout=1200,
        )
        self.vm.guest(
            "sudo -n python3 -c \"import sys;sys.path.insert(0,'/opt/hermes-deploy/scripts/hermes');import lab_guest;lab_guest.deploy.ensure_user()\""
        )
        uid = self.vm.guest("id -u hermes").stdout.strip()
        if not uid.isdigit():
            raise LabError("guest runtime UID is invalid")
        for name in ("gateway", "worker"):
            self.copy_to(cache / f"{name}.oci", f"/tmp/hermes-lab-{name}.oci")
            self.vm.guest(
                f"sudo -n chmod 644 /tmp/hermes-lab-{name}.oci && sudo -n runuser -u hermes -- env --chdir=/home/hermes HOME=/home/hermes XDG_RUNTIME_DIR=/run/user/{uid} podman load -i /tmp/hermes-lab-{name}.oci >/dev/null && rm /tmp/hermes-lab-{name}.oci",
                timeout=600,
            )

    def deploy(self, manifest):
        self.vm.assert_identity()
        self.require_synthetic()
        existing = self.path / "profile.json"
        if existing.exists() and json.loads(existing.read_text())["vm"] != self.profile["vm"]:
            raise LabError("VM sizing changed; use a fresh instance")
        self.artifacts(manifest)
        self.vm.deploy()
        write_json(existing, self.profile)
        write_json(self.path / "artifact.json", manifest)

    def up(self, cache, manifest, *, stock=False):
        start = time.monotonic()
        self.artifacts(manifest)
        base = self.vm.verified_base() if stock else cache / "base.qcow2"
        self.boot(base)
        if stock:
            self.install_artifacts(cache, manifest)
        else:
            self.vm.transfer_source()
            self.vm.guest(GUEST + "audit-base")
        self.deploy(manifest)
        return time.monotonic() - start

    def clean(self):
        safe_path(self.path)
        if self.path.exists():
            allowed = {
                "client_ed25519",
                "client_ed25519.pub",
                "server_ed25519",
                "server_ed25519.pub",
                "user-data",
                "meta-data",
                "seed.iso",
                "known_hosts",
                "disk.qcow2",
                "deploy-source.tar",
                "identity.json",
                "profile.json",
                "artifact.json",
            }
            if any(
                p.name not in allowed or p.is_symlink() or not p.is_file()
                for p in self.path.iterdir()
            ):
                raise LabError("unexpected instance path; cleanup refused before domain mutation")
        if self.vm.domain_exists():
            self.vm.assert_identity()
        self.vm.clean()

    def identities(self):
        return json.loads(self.vm.guest(GUEST + "identities").stdout)

    def reboot(self):
        self.vm.reboot()
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            result = self.vm.guest(
                "sudo -n python3 /opt/hermes-deploy/scripts/hermes/profile-deploy.py status --mode synthetic",
                check=False,
                timeout=30,
            )
            if result.returncode == 0:
                return
            time.sleep(3)
        raise LabError("Hermes did not recover after reboot")


def prepare(profile):
    builder_profile = copy.deepcopy(profile)
    builder_profile["vm"] = {"memory_mb": 4096, "vcpus": 2, "disk_gb": 20}
    # Preparation only builds images; it does not run the requested application.
    for component in ("gateway", "worker"):
        builder_profile[component]["memory_mb"] = min(builder_profile[component]["memory_mb"], 4096)
    validate(builder_profile)
    key = cache_key(profile)
    with lock("cache-" + key):
        destination = STATE / "prepared" / key
        if destination.exists():
            return read_cache(profile)
        directory(destination.parent)
        stage = destination.with_name(key + ".building")
        if stage.exists():
            raise LabError(
                "interrupted cache build retained; inspect the .building directory before recovery"
            )
        directory(stage)
        builder = Instance("build-" + key[:16], builder_profile)
        with lock("instance-" + builder.name):
            base = builder.vm.verified_base()
            base_sha = file_hash(base)
            builder.boot(base)
            builder.vm.transfer_source()
            builder_machine = builder.vm.guest("sha256sum /etc/machine-id").stdout.split()[0]
            builder.vm.guest(
                "sudo -n touch /var/lib/hermes-lab-builder && sudo -n python3 /opt/hermes-deploy/scripts/hermes/profile-deploy.py prepare",
                timeout=1800,
            )
            manifest = json.loads(builder.vm.guest(GUEST + "export-images", timeout=600).stdout)
            for name in ("gateway", "worker"):
                builder.copy_from(f"/var/tmp/hermes-lab-export/{name}.oci", stage / f"{name}.oci")
            # Stop user-manager processes before sanitization; root transient
            # service survives removal of the bootstrap account/session.
            builder.vm.guest(
                "sudo -n systemd-run --unit=hermes-lab-sanitize --on-active=2s /usr/bin/python3 /opt/hermes-deploy/scripts/hermes/lab_guest.py sanitize"
            )
            deadline = time.monotonic() + 90
            while builder.vm.virsh("domstate", builder.vm.NAME).stdout.strip() != "shut off":
                if time.monotonic() > deadline:
                    raise LabError(
                        "builder did not shut down after sanitization; retained for inspection"
                    )
                time.sleep(2)
            builder.vm.assert_identity()
            checked(
                [
                    "qemu-img",
                    "convert",
                    "-f",
                    "qcow2",
                    "-O",
                    "qcow2",
                    str(builder.path / "disk.qcow2"),
                    str(stage / "base.qcow2"),
                ]
            )
            checked(["qemu-img", "check", str(stage / "base.qcow2")])
            manifest.update(
                {
                    "key": key,
                    "gateway_ref": profile["gateway_image"],
                    "fedora_sha256": base_sha,
                    "files": {
                        name: file_hash(stage / name)
                        for name in ("base.qcow2", "gateway.oci", "worker.oci")
                    },
                }
            )
            # Prove first-boot cleanup using a throwaway clone BEFORE publication.
            probe = Instance("audit-" + key[:16], builder_profile)
            with lock("instance-" + probe.name):
                probe.boot(stage / "base.qcow2")
                probe.vm.transfer_source()
                probe.vm.guest(GUEST + "audit-base")
                machine = probe.vm.guest("sha256sum /etc/machine-id").stdout.split()[0]
                expected_key = (probe.path / "client_ed25519.pub").read_text().strip()
                actual_key = probe.vm.guest(
                    "cat /home/labadmin/.ssh/authorized_keys"
                ).stdout.strip()
                if machine == builder_machine or actual_key != expected_key:
                    raise LabError("prepared clone reused builder identity or access")
                probe.clean()
            manifest["clone_audit"] = "PASS"
            write_json(stage / "manifest.json", manifest)
            if cache_key(profile) != key:
                raise LabError(
                    "preparation inputs changed; unpublished build retained for inspection"
                )
            for path in stage.iterdir():
                path.chmod(0o400)
            stage.chmod(0o500)
            os.rename(stage, destination)
            builder.clean()
        return read_cache(profile)
