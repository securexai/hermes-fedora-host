"""Signed release entrypoint. Runs one bounded stage per dispatcher request.

This file and its imports must be included under payload/ in the authenticated
release. Enrollment owns the boot chain and privilege policy; this code never
enrolls a TPM, trusts a host key, or changes firmware trust automatically.
"""

import hashlib
import os
from pathlib import Path
import pwd
import shutil
import sys
import tempfile
import time

# -I excludes caller Python paths; add only the root-owned signed payload directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Failure, atomic, canonical, decode, digest, lock, protected_file, report, require, run
from gates import package_baseline, replay_packages
from offline import require_complete
from tpm_profile import services as tpm_services

ROOT = Path("/var/lib/hermes-unattended")
DATA = Path("/home/hermes/data")
POLICY = Path("/etc/hermes-unattended/host.json")
CREDENTIAL = Path("/etc/credstore.encrypted/hermes-openai-api")


def as_hermes(args, **kwargs):
    account = pwd.getpwnam("hermes")
    return run(["runuser", "-u", "hermes", "--", "env", "--chdir=/home/hermes", "HOME=/home/hermes",
                "XDG_RUNTIME_DIR=/run/user/" + str(account.pw_uid), *args], **kwargs)


def service(*args):
    return as_hermes(["systemctl", "--user", *args])


def boot_id():
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip()


def preflight(policy):
    os_release = Path("/etc/os-release").read_text()
    require('VERSION_ID=44' in os_release and ('ID=fedora\n' in os_release), "unsupported-platform")
    require(run(["getenforce"]).strip() == b"Enforcing", "selinux-not-enforcing")
    run(["systemctl", "is-active", "--quiet", "firewalld"])
    require(b"SecureBoot enabled" in run(["mokutil", "--sb-state"]), "secure-boot-disabled")
    run(["systemd-analyze", "has-tpm2"])
    run(["bootctl", "--esp-path=/boot/efi", "is-installed"])
    require(shutil.disk_usage("/var").free >= 20 * 1024**3, "insufficient-var-space")
    luks = decode(run(["cryptsetup", "luksDump", "--dump-json-metadata", policy["luks_device"]]))
    tokens = luks.get("tokens", {}).values()
    tpm = [token for token in tokens if token.get("type") == "systemd-tpm2"]
    require(bool(tpm), "tpm-boot-policy-mismatch")
    # Multiple automatic tokens are alternative unlock paths, not cumulative
    # restrictions. Retain legacy tokens for recovery review; refuse promotion.
    for token in tpm:
        require(token.get("tpm2-pcrs") == [7] and token.get("tpm2_pubkey_pcrs") == [11]
                and token.get("tpm2-pcr-bank") == "sha256"
                and isinstance(token.get("tpm2_pubkey"), str) and bool(token["tpm2_pubkey"])
                and token.get("tpm2-pin", False) is False
                and not any(value for key, value in token.items() if "pcrlock" in key),
                "tpm-boot-policy-mismatch")


def identity():
    try:
        account = pwd.getpwnam("hermes")
    except KeyError:
        run(["useradd", "--create-home", "--home-dir", "/home/hermes", "--shell", "/usr/sbin/nologin", "hermes"])
        account = pwd.getpwnam("hermes")
    require(account.pw_dir == "/home/hermes" and account.pw_uid != 0, "unsafe-hermes-identity")
    require(not Path("/home/hermes").is_symlink() and not DATA.is_symlink(), "unsafe-hermes-home")
    require(not Path("/home/hermes/.ssh/authorized_keys").exists(), "hermes-has-ssh-keys")
    run(["passwd", "-l", "hermes"])
    # Podman requires XDG_RUNTIME_DIR even before the first container exists.
    # Starting the user manager creates that directory for a newly enrolled user.
    run(["loginctl", "enable-linger", "hermes"])
    run(["systemctl", "start", f"user@{account.pw_uid}.service"])
    # The account owns its home and can replace data while setup runs. Perform all
    # path creation and mode changes after dropping root, including on reruns.
    as_hermes(["podman", "unshare", "python3", "-I", "-c", """import os,stat
try:
    os.mkdir('/home/hermes/data',0o700)
except FileExistsError:
    pass
fd=os.open('/home/hermes/data',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
try:
    info=os.fstat(fd)
    os.fchown(fd,os.getuid(),os.getgid())
    os.fchmod(fd,0o700)
finally:
    os.close(fd)
"""])
    # Fedora useradd allocates subordinate IDs; never overlap ranges by guessing a fixed range.
    for path in ("/etc/subuid", "/etc/subgid"):
        require(any(line.startswith("hermes:") for line in Path(path).read_text().splitlines()),
                "missing-hermes-subordinate-ids")
    return account


def healthy(image):
    result = decode(as_hermes(["podman", "inspect", "hermes"]))[0]
    require(result.get("State", {}).get("Health", {}).get("Status") == "healthy", "runtime-unhealthy")
    require(result.get("ImageName") == image, "runtime-image-mismatch")
    require(result.get("HostConfig", {}).get("ReadonlyRootfs") is True, "runtime-root-writable")
    require(not result.get("NetworkSettings", {}).get("Ports"), "runtime-published-ports")
    require(not result.get("HostConfig", {}).get("Privileged"), "privileged-runtime")


def wait_health(image):
    for _ in range(36):
        try:
            healthy(image)
            return
        except Failure:
            time.sleep(5)
    raise Failure(69, "runtime-health-timeout")


def install_file(source, destination, mode):
    destination = Path(destination)
    require(not destination.is_symlink(), "unsafe-install-destination")
    destination.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    atomic(destination, Path(source).read_bytes())
    destination.chmod(mode)


def read_application_file(path):
    if path != DATA / "config.yaml":
        return protected_file(path, 0).read_bytes()
    script = """import os,stat,sys
fd=os.open('config.yaml',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
with os.fdopen(fd,'rb') as stream:
    info=os.fstat(stream.fileno())
    if not stat.S_ISREG(info.st_mode) or info.st_size>4194304: raise SystemExit(78)
    raw=stream.read(4194305)
    if len(raw)>4194304: raise SystemExit(78)
    sys.stdout.buffer.write(raw)
"""
    return as_hermes(["podman", "unshare", "--", "env", "--chdir=/home/hermes/data",
                      "setpriv", "--reuid=10000", "--regid=10000",
                      "--clear-groups", "python3", "-c", script])


class Host:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.manifest = decode((self.directory / "manifest.json").read_bytes())
        self.release_id = self.manifest["release_id"]
        self.policy = decode(protected_file(POLICY, 0).read_bytes())
        self.journal = ROOT / (self.release_id + ".state.json")
        self.state = decode(self.journal.read_bytes()) if self.journal.exists() else {"phase": "new"}
        self.snapshot = ROOT / (self.release_id + ".snapshot.tar")
        self.previous = ROOT / (self.release_id + ".previous")

    def save(self, phase, **values):
        self.state.update(values, phase=phase)
        atomic(self.journal, canonical(self.state))
        return {"ok": True, "stage": phase, "release_id": self.release_id}

    def capture_application(self):
        if self.previous.exists():
            require((self.previous / "complete").exists(), "incomplete-application-backup")
            return
        self.previous.mkdir(mode=0o700)
        paths = [CREDENTIAL, DATA / "config.yaml"]
        try:
            uid = pwd.getpwnam("hermes").pw_uid
            paths += [Path(f"/etc/containers/systemd/users/{uid}/hermes.container")]
        except KeyError:
            pass
        paths += [Path("/etc/systemd/user/hermes.service.d/80-hermes-credential.conf")]
        records = []
        for index, path in enumerate(paths):
            require(not path.is_symlink(), "unsafe-application-backup-path")
            record = {"path": str(path), "exists": path.exists(), "index": str(index)}
            if path.exists():
                info = path.stat()
                record.update(uid=info.st_uid, gid=info.st_gid, mode=info.st_mode & 0o777)
                atomic(self.previous / str(index), read_application_file(path))
            records.append(record)
        atomic(self.previous / "files.json", canonical(records))
        atomic(self.previous / "complete", b"complete\n")

    def track(self, path):
        """Remember each installer-owned file once, including absent files on a fresh host."""
        path = Path(path)
        records = decode((self.previous / "files.json").read_bytes())
        if any(record["path"] == str(path) for record in records):
            return
        require(not path.is_symlink(), "unsafe-tracked-path")
        record = {"path": str(path), "exists": path.exists(), "index": str(len(records))}
        if path.exists():
            info = path.stat()
            record.update(uid=info.st_uid, gid=info.st_gid, mode=info.st_mode & 0o777)
            atomic(self.previous / record["index"], read_application_file(path))
        records.append(record)
        atomic(self.previous / "files.json", canonical(records))

    def snapshot_data(self):
        if self.state["phase"] != "new":
            require(self.snapshot.exists(), "snapshot-unavailable")
            return {"ok": True, "stage": self.state["phase"], "release_id": self.release_id,
                    "snapshot_sha256": digest(self.snapshot)}
        preflight(self.policy)
        self.capture_application()
        try:
            active = service("is-active", "hermes.service").strip() == b"active"
        except (Failure, KeyError):
            active = False
        self.state["previous_active"] = active
        self.save("snapshot-creating")
        guard = "hermes-backup-guard-" + hashlib.sha256(self.release_id.encode()).hexdigest()[:16]
        run(["systemd-run", "--unit=" + guard, "--on-active=20min", "/usr/bin/python3", "-I", "-B",
             str(self.directory / "payload/host.py"), "backup-guard"])
        if DATA.exists():
            try:
                service("stop", "hermes.service")
            except Failure:
                # A missing/inactive service is acceptable only if there is no running container.
                require(not as_hermes(["podman", "ps", "-q"]).strip(), "cannot-quiesce-runtime")
            with open(self.snapshot, "xb") as output:
                os.chmod(self.snapshot, 0o600)
                as_hermes(["podman", "unshare", "tar", "-C", str(DATA), "-cf", "-", "."], stdout=output, timeout=900)
        else:
            with open(self.snapshot, "xb") as output:
                os.chmod(self.snapshot, 0o600)
                run(["tar", "-cf", "-", "--files-from=/dev/null"], stdout=output)
        value = digest(self.snapshot)
        self.save("snapshot-ready", snapshot_sha256=value)
        return {"ok": True, "stage": "snapshot-ready", "release_id": self.release_id, "snapshot_sha256": value}

    def acknowledge_backup(self, message):
        require(self.state["phase"] in ("snapshot-ready", "backup-verified"), "backup-stage-mismatch")
        require(message.get("snapshot_sha256") == self.state["snapshot_sha256"], "backup-digest-mismatch")
        return self.save("backup-verified", backup_snapshot=message["backup_snapshot"])

    def credential(self, message):
        require(self.state["phase"] in ("backup-verified", "credential-ready"), "credential-stage-mismatch")
        value = message.get("key")
        require(isinstance(value, str) and 1 <= len(value) <= 4096
                and not any(c in value for c in "\n\r\x00"), "invalid-runtime-key")
        encrypted = run(["systemd-creds", "encrypt", "--name=openai-api", "--with-key=host+tpm2",
                         "--tpm2-pcrs=7", "--tpm2-public-key=/etc/systemd/tpm2-pcr-public-key.pem",
                         "--tpm2-public-key-pcrs=11", "-", "-"],
                        data=value.encode())
        CREDENTIAL.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        atomic(CREDENTIAL, encrypted)
        return self.save("credential-ready")

    def install_boot(self):
        uki = self.directory / self.manifest["boot_artifact"]
        run(["sbverify", "--cert", "/etc/hermes-unattended/uki.crt", str(uki)])
        target = Path("/boot/efi/EFI/Linux") / ("hermes-" + self.release_id + ".efi")
        # Atomic replacement needs a full temporary image beside preserved boot entries.
        require(shutil.disk_usage("/boot/efi").free >= uki.stat().st_size + 1024 * 1024,
                "insufficient-esp-space")
        install_file(uki, target, 0o644)
        # Offline replay selects this entry after its kernel modules are installed.
        return target.name

    def advance(self):
        phase = self.state["phase"]
        if phase == "closed":
            healthy(self.manifest["image"])
            return self.save("closed")
        if phase == "credential-ready":
            preflight(self.policy)
            require(package_baseline() == self.manifest["baseline_sha256"], "package-baseline-mismatch")
            boot_entry = self.install_boot()
            self.save("package-staging", boot_before=boot_id())
            replay_packages((self.directory / self.manifest["transaction"]).parent, self.manifest["baseline_sha256"],
                            boot_entry=boot_entry)
            self.save("reboot-pending")
            run(["systemd-run", "--unit=hermes-offline-reboot", "--on-active=5s", "/usr/bin/systemctl", "reboot"])
            return {"ok": True, "stage": "reboot-pending", "release_id": self.release_id}
        if phase == "reboot-pending":
            if boot_id() == self.state["boot_before"]:
                return {"ok": True, "stage": "reboot-pending", "release_id": self.release_id}
            # A changed boot ID alone does not prove RPM transaction success.
            expected = (self.directory / "packages/installed-after.sha256").read_text().strip()
            require(package_baseline() == expected, "package-replay-result-mismatch")
            require_complete((self.directory / self.manifest["transaction"]).parent, self.manifest["baseline_sha256"])
            preflight(self.policy)
            self.save("runtime-pending")
            phase = "runtime-pending"
        require(phase in ("runtime-pending", "runtime-installed", "persistence-reboot"), "release-needs-recovery", 75)
        if phase == "persistence-reboot" and boot_id() == self.state["runtime_boot_before"]:
            return {"ok": True, "stage": "persistence-reboot", "release_id": self.release_id}
        try:
            if phase == "persistence-reboot":
                wait_health(self.manifest["image"])
            if phase == "runtime-pending":
                self.install_runtime()
                self.save("runtime-installed")
            self.acceptance()
            if phase != "persistence-reboot":
                self.save("persistence-reboot", runtime_boot_before=boot_id())
                run(["systemd-run", "--unit=hermes-persistence-reboot", "--on-active=5s", "/usr/bin/systemctl", "reboot"])
                return {"ok": True, "stage": "persistence-reboot", "release_id": self.release_id}
            preflight(self.policy)
        except Failure:
            self.rollback()
            raise Failure(69, "application-rolled-back") from None
        self.snapshot.unlink(missing_ok=True)
        return self.save("closed")

    def install_runtime(self):
        account = identity()
        payload = self.directory / "payload"
        unit = payload / "hermes.container"
        require("Image=" + self.manifest["image"] in unit.read_text().splitlines(), "quadlet-image-mismatch")
        as_hermes(["podman", "pull", self.manifest["image"]], timeout=900)
        unit_target = f"/etc/containers/systemd/users/{account.pw_uid}/hermes.container"
        self.track(unit_target)
        install_file(unit, unit_target, 0o644)
        for name in ("60-hermes-runtime.conf", "70-hermes-volume-label.conf"):
            self.track("/etc/systemd/user/hermes.service.d/" + name)
            install_file(payload / name, "/etc/systemd/user/hermes.service.d/" + name, 0o644)
        overlay = Path("/etc/systemd/user/hermes.service.d/80-hermes-credential.conf")
        overlay.unlink(missing_ok=True)
        container_dropin = Path(f"/etc/containers/systemd/users/{account.pw_uid}/hermes.container.d/80-credentials.conf")
        self.track(container_dropin)
        container_dropin.unlink(missing_ok=True)
        service("daemon-reload")
        service("restart", "hermes.service")
        wait_health(self.manifest["image"])
        for name in ("harden-config.py", "set-model.py"):
            command = ["podman", "exec", "-i", "--user", "10000:10000"]
            if name == "set-model.py":
                command += ["-e", "HERMES_PROVIDER=openai-api", "-e", "HERMES_MODEL=" + self.manifest["model"]]
            as_hermes(command + ["hermes", "python3", "-"], data=(payload / name).read_bytes())
        self.track("/usr/local/libexec/hermes-unattended/materialize.py")
        self.track("/etc/systemd/system/hermes-runtime-credentials.service")
        install_file(payload / "materialize.py", "/usr/local/libexec/hermes-unattended/materialize.py", 0o755)
        install_file(payload / "hermes-runtime-credentials.service", "/etc/systemd/system/hermes-runtime-credentials.service", 0o644)
        runtime_order = Path("/etc/systemd/system/hermes-runtime-credentials.service.d/80-runtime-directory.conf")
        self.track(runtime_order)
        runtime_order.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        atomic(runtime_order, ("[Unit]\nRequires=user-runtime-dir@" + str(account.pw_uid)
                               + ".service\nAfter=user-runtime-dir@" + str(account.pw_uid) + ".service\n").encode())
        runtime_order.chmod(0o644)
        manager = Path(f"/etc/systemd/system/user@{account.pw_uid}.service.d/80-hermes-credentials.conf")
        self.track(manager)
        manager.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        atomic(manager, b"[Unit]\nRequires=hermes-runtime-credentials.service\nAfter=hermes-runtime-credentials.service\n")
        manager.chmod(0o644)
        run(["systemctl", "daemon-reload"])
        run(["systemctl", "restart", "hermes-runtime-credentials.service"])
        # Requires= propagates the credential restart to the dependent user manager.
        # Bring it back before issuing any user-bus commands.
        run(["systemctl", "start", f"user@{account.pw_uid}.service"])
        # Quadlet container options belong in a .container.d drop-in, not the generated service.
        container_dropin.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        atomic(container_dropin, b"[Container]\nVolume=/run/hermes-secrets/provider.env:/opt/data/.env:ro,z\n")
        container_dropin.chmod(0o644)
        service("daemon-reload")
        service("restart", "hermes.service")
        wait_health(self.manifest["image"])

    def acceptance(self):
        healthy(self.manifest["image"])
        script = b'''import pathlib, yaml
c=yaml.safe_load(pathlib.Path('/opt/data/config.yaml').read_text())
assert c['approvals']['mode']=='manual'
assert c['approvals']['cron_mode']=='deny'
assert c['approvals']['single_query_mode']=='deny'
assert c['security']['allow_private_urls'] is False
assert c['security']['tirith_fail_open'] is False
assert c['hooks']=={} and c['mcp_servers']=={}
assert c['cron']['allow_agent_scheduling'] is False
'''
        as_hermes(["podman", "exec", "-i", "--user", "10000:10000", "hermes", "python3", "-"], data=script)
        output = as_hermes(["podman", "exec", "--user", "10000:10000", "hermes", "hermes", "--safe-mode",
                            "--provider", "openai-api", "--model", self.manifest["model"], "--toolsets", "context_engine",
                            "-z", "Return exactly HERMES_OK and nothing else."], timeout=120)
        require(output in (b"HERMES_OK", b"HERMES_OK\n"), "inference-acceptance-failed")

    def rollback(self):
        require((self.previous / "complete").exists(), "application-backup-unavailable")
        try:
            service("stop", "hermes.service")
        except (Failure, KeyError):
            pass
        for record in decode((self.previous / "files.json").read_bytes()):
            path = Path(record["path"])
            if path == CREDENTIAL and self.state["phase"] == "closed":
                # Successful rotation retires the old provider identity. Keep the accepted key
                # during later application rollback rather than restoring a revoked credential.
                continue
            require(not path.is_symlink(), "unsafe-rollback-destination")
            if path == DATA / "config.yaml":
                # Hermes owns this directory and can replace its entries. Restore with
                # the same container UID, never root authority in a user-controlled path.
                if record["exists"]:
                    script = """import os,secrets,sys
directory=os.open('.',os.O_RDONLY|os.O_DIRECTORY)
name='.rollback-'+secrets.token_hex(16)
fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600,dir_fd=directory)
try:
    with os.fdopen(fd,'wb') as stream:
        stream.write(sys.stdin.buffer.read())
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(name,'config.yaml',src_dir_fd=directory,dst_dir_fd=directory)
    os.fsync(directory)
finally:
    try: os.unlink(name,dir_fd=directory)
    except FileNotFoundError: pass
    os.close(directory)
"""
                    as_hermes(["podman", "unshare", "--", "env", "--chdir=/home/hermes/data",
                               "setpriv", "--reuid=10000", "--regid=10000",
                               "--clear-groups", "python3", "-c", script],
                              data=(self.previous / record["index"]).read_bytes())
                else:
                    as_hermes(["podman", "unshare", "--", "env", "--chdir=/home/hermes/data",
                               "setpriv", "--reuid=10000", "--regid=10000",
                               "--clear-groups", "rm", "-f", "--", "config.yaml"])
                continue
            if record["exists"]:
                atomic(path, (self.previous / record["index"]).read_bytes())
                path.chmod(record["mode"])
                os.chown(path, record["uid"], record["gid"])
            else:
                path.unlink(missing_ok=True)
        try:
            run(["systemctl", "daemon-reload"])
            if CREDENTIAL.exists() and Path("/etc/systemd/system/hermes-runtime-credentials.service").exists():
                run(["systemctl", "restart", "hermes-runtime-credentials.service"])
                uid = pwd.getpwnam("hermes").pw_uid
                run(["systemctl", "start", f"user@{uid}.service"])
            service("daemon-reload")
            if self.state.get("previous_active"):
                service("restart", "hermes.service")
                # Verify the restored image, not the candidate image which failed acceptance.
                uid = pwd.getpwnam("hermes").pw_uid
                unit = Path(f"/etc/containers/systemd/users/{uid}/hermes.container").read_text()
                previous_image = next(line.removeprefix("Image=") for line in unit.splitlines() if line.startswith("Image="))
                wait_health(previous_image)
        except (Failure, KeyError):
            return self.save("recovery-required")
        return self.save("rolled-back")


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 2, "invalid-host-invocation", 77)
    host = Host(Path(__file__).resolve().parent.parent)
    action = sys.argv[1]
    if action == "backup-guard":
        with lock(ROOT / "target.lock"):
            if host.state["phase"] in ("snapshot-creating", "snapshot-ready", "backup-verified", "credential-ready"):
                return host.rollback()
            return {"ok": True, "stage": host.state["phase"], "release_id": host.release_id}
    if action == "snapshot":
        return host.snapshot_data()
    if action in ("backup-verified", "credential"):
        message = decode(sys.stdin.buffer.read(65537))
        return host.acknowledge_backup(message) if action == "backup-verified" else host.credential(message)
    if action == "rollback":
        return host.rollback()
    if action in ("check", "status"):
        preflight(host.policy)
        if host.state["phase"] == "closed":
            healthy(host.manifest["image"])
        return {"ok": True, "stage": host.state["phase"], "release_id": host.release_id}
    require(action in ("deploy", "upgrade"), "unknown-host-action", 64)
    return host.advance()


if __name__ == "__main__":
    report(main)
