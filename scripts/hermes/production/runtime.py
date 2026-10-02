"""Production adapter over the same profile engine used by the disposable lab."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import pwd
import re
import shutil
import tarfile
import time
from pathlib import Path, PurePosixPath

from . import bundle, receivers, startup
from .primitives import (
    atomic,
    canonical,
    durable_directory,
    durable_tree,
    read_json,
    regular,
    require,
    run,
    sha,
    supervised_run,
)

HOME = Path("/home/hermes")
STATE = Path("/var/lib/hermes-production")
TREES = ("gateway-state", "gateway-ssh", "worker-state")


# The gateway image writes its own key for its built-in API server into the stored
# environment at start. That server stays disabled (API_SERVER_ENABLED=false is enforced)
# and no port is published, so the stored file may carry it; operator documents may not.
CONTAINER_MANAGED = frozenset({"API_SERVER_KEY"})


def credentials(path, *, container_managed=True):
    """Validate a gateway environment file. Operator-supplied files pass False."""
    path = regular(path, private=True)
    require(path.stat().st_size <= 16384, "credential-file-too-large")
    credential_text(path.read_text(), container_managed=container_managed)


def credential_text(text, *, container_managed=False):
    """Validate the gateway environment document; never return or log its values."""
    require(len(text.encode()) <= 16384, "credential-file-too-large")
    values = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        require(
            separator and key not in values and re.fullmatch(r"[A-Z][A-Z0-9_]*", key),
            "invalid-credential-file",
        )
        values[key] = value
    required = {"DEEPSEEK_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_USERS"}
    optional = {
        "API_SERVER_ENABLED": "false",
        "HERMES_DASHBOARD": "0",
        "GATEWAY_ALLOW_ALL_USERS": "false",
        "WEBHOOK_ENABLED": "false",
    }
    managed = CONTAINER_MANAGED if container_managed else frozenset()
    require(
        required <= set(values) <= required | set(optional) | managed,
        "unexpected-credential-fields",
    )
    require(
        all(values[k] and not any(c.isspace() for c in values[k]) for k in required),
        "missing-private-credentials",
    )
    require(
        all(values[k] and not any(c.isspace() for c in values[k]) for k in managed & set(values)),
        "invalid-container-managed-field",
    )
    require(
        re.fullmatch(r"[1-9][0-9]*(?:,[1-9][0-9]*)*", values["TELEGRAM_ALLOWED_USERS"]),
        "explicit-telegram-numeric-allowlist-required",
    )
    require(all(values.get(k, v) == v for k, v in optional.items()), "unsafe-profile-environment")


def validate_snapshot(path):
    """Reject extraction escapes, devices, ambiguous links and duplicate paths."""
    with tarfile.open(path, "r:") as archive:
        members = archive.getmembers()
        require(len(members) <= 1000000, "snapshot-too-many-files")
        names, symlinks = {}, set()
        for member in members:
            name = member.name.rstrip("/")
            p = PurePosixPath(name)
            require(
                not p.is_absolute()
                and ".." not in p.parts
                and p.parts
                and p.parts[0] in TREES
                and str(p) == name
                and name not in names,
                "unsafe-snapshot-path",
            )
            require(
                member.isfile() or member.isdir() or member.issym() or member.islnk(),
                "unsafe-snapshot-type",
            )
            names[name] = member
            if member.issym():
                # Retain relative in-tree application links only.
                target = PurePosixPath(member.linkname)
                require(not target.is_absolute(), "absolute-snapshot-symlink")
                normalized = os.path.normpath(str(p.parent / target))
                require(
                    PurePosixPath(normalized).parts[0] == p.parts[0], "escaping-snapshot-symlink"
                )
                symlinks.add(name)
        for name, member in names.items():
            require(
                not any(str(p) in symlinks for p in PurePosixPath(name).parents),
                "snapshot-symlink-parent",
            )
            if member.islnk():
                require(
                    member.linkname in names and names[member.linkname].isfile(),
                    "unsafe-snapshot-hardlink",
                )


class Backend:
    def __init__(self, config, state=STATE):
        self.config, self.state = config, Path(state)
        self.mode = config["application_mode"]
        self.uid = pwd.getpwnam("hermes").pw_uid
        self.units = Path(f"/etc/containers/systemd/users/{self.uid}")
        self.verified_releases = {}

    def release(self, release):
        require(re.fullmatch(r"[a-f0-9]{64}", release or ""), "invalid-release-identity")
        if release in self.verified_releases:
            return self.verified_releases[release]
        root = self.state / "releases" / release
        manifest = bundle.validate(
            read_json(root / "manifest.json", owner=0),
            production=self.config["kind"] == "production",
        )
        require(bundle.identity(manifest) == release, "release-identity-mismatch")
        require(not any(path.is_symlink() for path in root.rglob("*")), "installed-release-link")
        actual = {str(path.relative_to(root)) for path in root.rglob("*") if not path.is_dir()}
        require(
            actual == set(manifest["files"]) | {"manifest.json", "manifest.sig"},
            "unexpected-installed-release-file",
        )
        run(
            [
                "ssh-keygen",
                "-Y",
                "verify",
                "-f",
                "/etc/hermes-production/allowed_signers",
                "-I",
                bundle.SIGNER,
                "-n",
                bundle.NAMESPACE,
                "-s",
                str(root / "manifest.sig"),
            ],
            data=(root / "manifest.json").read_bytes(),
        )
        for name, record in manifest["files"].items():
            path = regular(root / name, owner=0)
            require(sha(path) == record["sha256"], "installed-release-corrupt")
        # Match every receiver/helper hash against the retained, locally commissioned
        # version required by this release, including when recovering an older release.
        receivers.for_release(manifest)
        self.verified_releases[release] = (root, manifest)
        return root, manifest

    def engine(self, release):
        root, manifest = self.release(release)
        require(receivers.running_matches(manifest), "mixed-receiver-execution-refused")
        spec = importlib.util.spec_from_file_location(
            "production_profile", root / "source/profile-deploy.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.PRODUCTION = True
        module.PROFILE = manifest["profile"]
        module.MODEL = manifest["profile"]["model"]
        module.GATEWAY_ID = manifest["images"]["gateway"]
        module.WORKER_ID = manifest["images"]["worker"]
        return module

    def user(self, *argv, check=True, timeout=600):
        return run(
            [
                "runuser",
                "-u",
                "hermes",
                "--",
                "env",
                "-i",
                "HOME=/home/hermes",
                "PATH=/usr/bin:/bin",
                f"XDG_RUNTIME_DIR=/run/user/{self.uid}",
                f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{self.uid}/bus",
                *argv,
            ],
            check=check,
            timeout=timeout,
            cwd=HOME,
        )

    def initialize_namespace(self):
        # The first rootless Podman command creates a persistent pause process.
        # The user manager must parent it, rather than the writer subreaper.
        # Only this fixed info command runs in the transient service; ordinary
        # application commands retain their existing descendant supervision.
        result = self.user(
            "systemd-run",
            "--user",
            "--wait",
            "--pipe",
            "--quiet",
            "--collect",
            "--unit=hermes-production-namespace",
            "--property=Type=oneshot",
            "--property=TimeoutStartSec=120s",
            "--property=TimeoutStopSec=30s",
            "--property=KillMode=control-group",
            "--property=WorkingDirectory=/home/hermes",
            "--setenv=HOME=/home/hermes",
            "--setenv=PATH=/usr/bin:/bin",
            f"--setenv=XDG_RUNTIME_DIR=/run/user/{self.uid}",
            f"--setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{self.uid}/bus",
            "--expand-environment=no",
            "/usr/bin/podman",
            "info",
            "--format",
            "{{.Host.Security.Rootless}}",
            # The manager owns the unit timeout and cleanup. Never kill its
            # waiter while initialization could still be running in that unit.
            timeout=0,
        )
        require(result.stdout.strip() == b"true", "runtime-namespace-not-rootless")

    def current(self):
        path = self.state / "current.json"
        return read_json(path, owner=0)["release"] if path.exists() else None

    def set_current(self, release):
        _, manifest = self.release(release)
        receiver = receivers.for_release(manifest).name
        # The journal stays unfinished across BOTH durable pointer writes. Recovery
        # restores the old state and both pointers if either write is interrupted.
        receivers.select(receiver)
        atomic(self.state / "current.json", canonical({"release": release, "receiver": receiver}))

    def prepare(self, candidate, previous):
        self.release(candidate)
        if previous:
            self.release(previous)

    def receiver_action(self, release, action):
        _, manifest = self.release(release)
        if receivers.running_matches(manifest):
            return False
        entry = receivers.for_release(manifest) / "productionctl.py"
        run(["/usr/bin/python3", "-I", str(entry), "release-action", action, release], timeout=1800)
        return True

    def stop(self):
        failures = []
        for name in ("gateway", "worker"):
            unit = f"hermes-{name}.service"
            try:
                result = self.user(
                    "systemctl", "--user", "show", "--property=LoadState", "--value", unit
                )
                if result.stdout.strip() == b"not-found":
                    continue
            except BaseException:
                failures.append(name + "-load-state")
            try:
                self.user("systemctl", "--user", "stop", unit)
            except BaseException:
                failures.append(name + "-stop")
        try:
            running = (
                self.user("podman", "ps", "--format", "{{.Names}}").stdout.decode().splitlines()
            )
            if set(running) & {"hermes-worker", "hermes-gateway"}:
                failures.append("writers-still-running")
        except BaseException:
            failures.append("writer-check")
        require(not failures, "service-stop-failed:" + ",".join(failures))

    def snapshot(self, attempt, release):
        _, manifest = self.release(release)
        sizes = (
            run(
                [
                    "du",
                    "--apparent-size",
                    "--block-size=1",
                    "--summarize",
                    "--one-file-system",
                    *[str(HOME / tree) for tree in TREES],
                ]
            )
            .stdout.decode()
            .splitlines()
        )
        require(
            sum(int(line.split()[0]) for line in sizes) <= self.config["state_budget_bytes"],
            "state-exceeds-reserved-capacity",
        )
        target = self.state / "backups" / attempt
        target.mkdir(mode=0o700)
        archive = target / "state.tar"
        run(
            [
                "tar",
                "--xattrs",
                "--acls",
                "--selinux",
                "--numeric-owner",
                "--one-file-system",
                "-cpf",
                str(archive),
                "-C",
                str(HOME),
                *TREES,
            ],
            timeout=1800,
        )
        archive.chmod(0o600)
        require(
            archive.stat().st_size <= self.config["state_budget_bytes"],
            "state-exceeds-reserved-capacity",
        )
        validate_snapshot(archive)
        units = target / "units"
        units.mkdir(mode=0o700)
        for name in ("hermes-worker.container", "hermes-gateway.container"):
            shutil.copyfile(regular(self.units / name, owner=0), units / name)
        metadata = {
            "release": release,
            "receiver": receivers.for_release(manifest).name,
            "state_sha256": sha(archive),
            "uid": self.uid,
            "subordinate": {
                n: [
                    line
                    for line in Path("/etc/" + n).read_text().splitlines()
                    if line.startswith(("hermes:", str(self.uid) + ":"))
                ]
                for n in ("subuid", "subgid")
            },
            "units": {p.name: sha(p) for p in units.iterdir()},
        }
        atomic(target / "snapshot.json", canonical(metadata))
        durable_tree(target)
        return attempt

    def restore(self, snapshot, release):
        require(re.fullmatch(r"[a-f0-9]{32}", snapshot or ""), "invalid-snapshot-id")
        target = self.state / "backups" / snapshot
        info = read_json(target / "snapshot.json", owner=0)
        require(
            info["release"] == release and sha(target / "state.tar") == info["state_sha256"],
            "snapshot-state-artifact-mismatch",
        )
        require(
            info["uid"] == self.uid
            and info["subordinate"]
            == {
                n: [
                    line
                    for line in Path("/etc/" + n).read_text().splitlines()
                    if line.startswith(("hermes:", str(self.uid) + ":"))
                ]
                for n in ("subuid", "subgid")
            },
            "restore-runtime-id-mapping-mismatch",
        )
        _, manifest = self.release(release)
        require(
            info["receiver"] == receivers.for_release(manifest).name, "snapshot-receiver-mismatch"
        )
        validate_snapshot(target / "state.tar")
        # A private directory on the same mounted filesystem enables safe rename.
        import tempfile

        with tempfile.TemporaryDirectory(prefix=".hermes-restore-", dir=HOME) as directory:
            run(
                [
                    "tar",
                    "--xattrs",
                    "--acls",
                    "--selinux",
                    "--numeric-owner",
                    "-xpf",
                    str(target / "state.tar"),
                    "-C",
                    directory,
                ],
                timeout=1800,
            )
            failed = HOME / (".failed-" + str(time.time_ns()))
            failed.mkdir(mode=0o700)
            for tree in TREES:
                if (HOME / tree).exists():
                    os.rename(HOME / tree, failed / tree)
                os.rename(Path(directory) / tree, HOME / tree)
                durable_tree(HOME / tree)
            durable_directory(HOME)
        for name, expected in info["units"].items():
            require(
                name in ("hermes-worker.container", "hermes-gateway.container")
                and sha(target / "units" / name) == expected,
                "snapshot-unit-corrupt",
            )
            atomic(self.units / name, (target / "units" / name).read_bytes(), 0o644)
        run(["restorecon", "-R", str(self.units)])
        self.user("systemctl", "--user", "daemon-reload")

    def import_images(self, release):
        root, manifest = self.release(release)
        for name, image in manifest["images"].items():
            if self.user("podman", "image", "exists", image, check=False).returncode:
                # Do not make the release directory readable by the runtime account.
                # A root-owned staging copy is readable only through an inherited fd.
                path = root / "images" / (name + ".oci")
                import subprocess

                with path.open("rb") as stream:
                    result = supervised_run(
                        [
                            "runuser",
                            "-u",
                            "hermes",
                            "--",
                            "env",
                            "-i",
                            "HOME=/home/hermes",
                            "PATH=/usr/bin:/bin",
                            f"XDG_RUNTIME_DIR=/run/user/{self.uid}",
                            "podman",
                            "load",
                        ],
                        stdin=stream,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=1800,
                        cwd=HOME,
                        env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"},
                    )
                require(result.returncode == 0, "image-import-failed")
            self.user("podman", "image", "exists", image)

    def configure(self, release):
        if self.receiver_action(release, "configure"):
            return
        engine = self.engine(release)
        if self.mode == "production":
            credentials(HOME / "gateway-state/.env")
        with contextlib.redirect_stdout(io.StringIO()):
            engine.prepare()
            uid, gid = engine.ensure_user()
            engine.ensure_instance(uid, gid, self.mode)
            engine.configure(engine.pinned_gateway())
            engine.install_quadlets(uid, self.mode)

    def activate(self, release):
        self.release(release)
        startup.allow_application()
        for name in ("worker", "gateway"):
            self.user("systemctl", "--user", "reset-failed", f"hermes-{name}.service")
            self.user("systemctl", "--user", "start", f"hermes-{name}.service")

    def restart_previous(self, release):
        if release:
            self.activate(release)

    def verify(self, release):
        if self.receiver_action(release, "verify"):
            return
        if self.mode == "production":
            credentials(HOME / "gateway-state/.env")
        engine = self.engine(release)
        with contextlib.redirect_stdout(io.StringIO()):
            deadline = time.monotonic() + 60
            while True:
                try:
                    engine.verify(self.mode)
                    break
                except engine.DeployError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(1)
        for name in ("ssh", "scp", "sftp", "unix-bridge.py"):
            require(
                sha(HOME / "gateway-ssh" / name) == sha(engine.MANUAL / "gateway" / name),
                "transport-source-drift",
            )
        client = HOME / "gateway-ssh/worker_client_ed25519.pub"
        worker = HOME / "worker-state/ssh-host-keys/ssh_host_ed25519_key.pub"
        require(
            (HOME / "gateway-ssh/known_hosts").read_bytes()
            == b"worker " + regular(worker).read_bytes()
            and (HOME / "worker-state/authorized_keys/worker").read_bytes()
            == regular(client).read_bytes(),
            "worker-identity-pin-drift",
        )
        for name in ("gateway", "worker"):
            import json

            item = json.loads(self.user("podman", "inspect", f"hermes-{name}").stdout)[0]
            host = item["HostConfig"]
            require(
                host.get("ReadonlyRootfs") is True
                and host.get("Privileged") is False
                and host.get("SecurityOpt")
                and "no-new-privileges" in host["SecurityOpt"]
                and not host.get("PortBindings")
                and item.get("ProcessLabel", "").startswith("system_u:system_r:container_t:"),
                "runtime-security-drift",
            )
            require(
                not any(
                    m.get("Source", "").endswith(("docker.sock", "podman.sock"))
                    for m in item["Mounts"]
                ),
                "container-engine-mount",
            )
            require(
                self.user(
                    "podman", "info", "--format", "{{.Host.Security.Rootless}}"
                ).stdout.strip()
                == b"true",
                "containers-not-rootless",
            )
        # Inspect real application process ownership, not just OCI Config.User (s6 starts as root).
        output = self.user("podman", "top", "hermes-gateway", "user", "args").stdout.decode()
        require(
            any(
                line.split()[0] in ("10000", "hermes") and "gateway" in line
                for line in output.splitlines()[1:]
                if line.split()
            ),
            "gateway-process-identity",
        )
        worker_uid = self.user(
            "podman",
            "exec",
            "--user",
            "10000:10000",
            "hermes-gateway",
            "/opt/hermes/bin/ssh",
            "worker@worker",
            "id -u",
        ).stdout.strip()
        require(worker_uid == b"1000", "worker-process-identity")
