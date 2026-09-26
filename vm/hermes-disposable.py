#!/usr/bin/env python3
"""Create, exercise, inspect and remove one Fedora Cloud Hermes lab VM.

All guest privileges are confined to the disposable VM. The host uses the
current user's qemu:///session connection and a loopback-only passt SSH port.
The signed Fedora base is shared; each instance gets an unencrypted qcow2
overlay, a NoCloud seed, and fresh SSH client and server identities.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
LAB = ROOT / ".toolbox/hermes-disposable"
CACHE = LAB / "cache"
INSTANCE = LAB / "instances/hermes-disposable-lab"
NAME = "hermes-disposable-lab"
PORT = 22222
IMAGE = "Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2"
CHECKSUM = "Fedora-Cloud-44-1.7-x86_64-CHECKSUM"
BASE_URL = (
    f"https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/x86_64/images/{IMAGE}"
)
CHECKSUM_URL = f"https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/x86_64/images/{CHECKSUM}"
FEDORA_KEY = pathlib.Path("/usr/share/distribution-gpg-keys/fedora/RPM-GPG-KEY-fedora-44-primary")
SIGNER = "36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6"
SOURCE_FILES = (
    "scripts/hermes/profile-deploy.py",
    "scripts/hermes/live-guest.py",
    "scripts/hermes/manual/manifest.yaml",
    "scripts/hermes/manual/config/harden-config.py",
    "scripts/hermes/manual/config/set-model.py",
    "scripts/hermes/manual/config/profile-contract.yaml",
    "scripts/hermes/manual/gateway/ssh",
    "scripts/hermes/manual/gateway/scp",
    "scripts/hermes/manual/gateway/sftp",
    "scripts/hermes/manual/gateway/unix-bridge.py",
    "scripts/hermes/manual/quadlets/hermes-gateway.container",
    "scripts/hermes/manual/quadlets/hermes-worker.container",
    "scripts/hermes/manual/worker/Containerfile",
    "scripts/hermes/manual/worker/sshd_worker_config",
    "scripts/hermes/manual/worker/worker-entrypoint",
    "scripts/hermes/manual/worker/worker-socket-adapter",
    "scripts/hermes/manual/worker/worker-sshd-inetd",
)


class LabError(RuntimeError):
    pass


def run(
    argv: list[str], *, check: bool = True, timeout: int = 600
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=timeout)
    if check and result.returncode:
        raise LabError(
            f"{pathlib.Path(argv[0]).name} failed (exit {result.returncode}): {result.stderr[-500:].strip()}"
        )
    return result


def virsh(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["virsh", "-c", "qemu:///session", *args], check=check, timeout=40)


def domain_exists() -> bool:
    # A failed domuuid query also means the libvirt connection failed. Listing
    # domains with check=True keeps an inaccessible connection from looking
    # like a successfully cleaned-up VM.
    domains = virsh("list", "--all", "--name").stdout.splitlines()
    return NAME in domains


def download(url: str, dest: pathlib.Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(
        ["curl", "-fsSL", "--retry", "2", "--continue-at", "-", "--output", str(dest), url],
        timeout=900,
    )


def verified_base() -> pathlib.Path:
    base = CACHE / IMAGE
    checks = CACHE / CHECKSUM
    if not FEDORA_KEY.is_file():
        raise LabError("Fedora 44 packaged public key is unavailable")
    if not checks.is_file():
        download(CHECKSUM_URL, checks)
    ring = CACHE / "fedora-44.gpg"
    if not ring.is_file():
        run(["gpg", "--dearmor", "--output", str(ring), str(FEDORA_KEY)])
    signature = run(["gpgv", "--keyring", str(ring), str(checks)])
    if SIGNER not in signature.stderr:
        raise LabError("signed checksum has an unexpected Fedora signer")
    match = re.search(
        rf"^SHA256 \({re.escape(IMAGE)}\) = ([a-f0-9]{{64}})$", checks.read_text(), re.M
    )
    if not match:
        raise LabError("signed Fedora checksum lacks the selected Cloud image")
    if not base.is_file():
        download(BASE_URL, base)
    digest = hashlib.sha256()
    with base.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != match.group(1):
        raise LabError("Fedora Cloud image checksum mismatch")
    print(f"BASE=PASS sha256={digest.hexdigest()}")
    return base


def create_key(path: pathlib.Path) -> None:
    if path.exists() or path.with_suffix(path.suffix + ".pub").exists():
        raise LabError(f"SSH identity already exists: {path.name}")
    run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(path)])
    path.chmod(0o600)


def create_seed() -> None:
    client = INSTANCE / "client_ed25519"
    server = INSTANCE / "server_ed25519"
    create_key(client)
    create_key(server)
    user_public = pathlib.Path(str(client) + ".pub").read_text().strip()
    server_public = pathlib.Path(str(server) + ".pub").read_text().strip()
    server_private = server.read_text().strip().replace("\n", "\n    ")
    user_data = f"""#cloud-config
disable_root: true
ssh_pwauth: false
ssh_deletekeys: true
ssh_genkeytypes: [ed25519]
ssh_keys:
  ed25519_private: |
    {server_private}
  ed25519_public: {json.dumps(server_public)}
users:
  - name: labadmin
    groups: [wheel]
    sudo: 'ALL=(ALL) NOPASSWD:ALL'
    lock_passwd: true
    shell: /bin/bash
    ssh_authorized_keys: [{json.dumps(user_public)}]
write_files:
  - path: /etc/ssh/sshd_config.d/50-hermes-lab-key-only.conf
    permissions: '0644'
    content: |
      PasswordAuthentication no
      KbdInteractiveAuthentication no
      PermitRootLogin no
runcmd:
  - [systemctl, restart, sshd]
"""
    (INSTANCE / "user-data").write_text(user_data)
    (INSTANCE / "meta-data").write_text(f"instance-id: {uuid.uuid4()}\n")
    # genisoimage resolves input paths from cwd, so use absolute inputs.
    run(
        [
            "genisoimage",
            "-quiet",
            "-output",
            str(INSTANCE / "seed.iso"),
            "-volid",
            "cidata",
            "-joliet",
            "-rock",
            str(INSTANCE / "user-data"),
            str(INSTANCE / "meta-data"),
        ],
        timeout=60,
    )
    parts = server_public.split()
    (INSTANCE / "known_hosts").write_text(f"[127.0.0.1]:{PORT} {parts[0]} {parts[1]}\n")


def ssh_base() -> list[str]:
    return [
        "ssh",
        "-i",
        str(INSTANCE / "client_ed25519"),
        "-p",
        str(PORT),
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        f"UserKnownHostsFile={INSTANCE / 'known_hosts'}",
        "-o",
        "ConnectTimeout=5",
        "labadmin@127.0.0.1",
    ]


def guest(
    command: str, *, check: bool = True, timeout: int = 600
) -> subprocess.CompletedProcess[str]:
    result = run([*ssh_base(), command], check=False, timeout=timeout)
    if check and result.returncode:
        raise LabError(f"guest command failed (exit {result.returncode})")
    return result


def wait_ssh(timeout: int = 360) -> None:
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if guest("true", check=False, timeout=12).returncode == 0:
            return
        time.sleep(3)
    raise LabError("guest key-only SSH did not become available")


def source_archive() -> pathlib.Path:
    target = INSTANCE / "deploy-source.tar"
    with tarfile.open(target, "w") as archive:
        for relative in SOURCE_FILES:
            source = ROOT / relative
            if not source.is_file() or source.is_symlink():
                raise LabError(f"missing or unsafe deployment source: {relative}")
            info = archive.gettarinfo(str(source), arcname=relative)
            # The repository's preserved files may be owner-only on the host.
            # This allowlisted, credential-free source must be readable by the
            # guest's unprivileged image builder after root takes ownership.
            info.mode = 0o644
            with source.open("rb") as stream:
                archive.addfile(info, stream)
    return target


def transfer_source() -> None:
    archive = source_archive()
    args = ssh_base()
    scp = ["scp", "-i", args[2], "-P", str(PORT), *args[5:-1]]
    run([*scp, str(archive), "labadmin@127.0.0.1:/tmp/hermes-deploy-source.tar"])
    guest(
        "sudo -n install -d -m 0755 /opt/hermes-deploy && sudo -n tar -C /opt/hermes-deploy -xf /tmp/hermes-deploy-source.tar && sudo -n chown -R root:root /opt/hermes-deploy && rm -f /tmp/hermes-deploy-source.tar"
    )
    archive.unlink()


def deploy() -> None:
    if not domain_exists():
        raise LabError("the disposable lab domain is absent; run 'run' first")
    wait_ssh()
    guest(
        "cloud-init status --wait >/dev/null && test $(getenforce) = Enforcing && sudo -n true",
        timeout=600,
    )
    guest(
        "test $(sudo -n sshd -T | sed -n 's/^passwordauthentication //p' | head -1) = no && test $(sudo -n sshd -T | sed -n 's/^kbdinteractiveauthentication //p' | head -1) = no"
    )
    denied = run(
        [
            "ssh",
            "-p",
            str(PORT),
            "-o",
            "BatchMode=yes",
            "-o",
            "PreferredAuthentications=none",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            f"UserKnownHostsFile={INSTANCE / 'known_hosts'}",
            "-o",
            "ConnectTimeout=5",
            "labadmin@127.0.0.1",
            "true",
        ],
        check=False,
        timeout=12,
    )
    if denied.returncode == 0:
        raise LabError("guest accepted an SSH login without the generated key")
    transfer_source()
    result = guest(
        "sudo -n python3 /opt/hermes-deploy/scripts/hermes/profile-deploy.py apply --mode synthetic",
        timeout=1800,
    )
    print(result.stdout.strip())


def fresh_run() -> None:
    if domain_exists() or INSTANCE.exists():
        raise LabError("disposable lab already exists; inspect or clean the exact instance first")
    start = time.monotonic()
    base = verified_base()
    INSTANCE.mkdir(parents=True, mode=0o700)
    create_seed()
    overlay = INSTANCE / "disk.qcow2"
    run(["qemu-img", "create", "-f", "qcow2", "-F", "qcow2", "-b", str(base), str(overlay), "20G"])
    command = [
        "virt-install",
        "--connect",
        "qemu:///session",
        "--name",
        NAME,
        "--memory",
        "4096",
        "--vcpus",
        "2",
        "--os-variant",
        "fedora43",
        "--disk",
        f"path={overlay},format=qcow2,bus=virtio",
        "--disk",
        f"path={INSTANCE / 'seed.iso'},device=cdrom",
        "--network",
        f"user,backend.type=passt,portForward0.proto=tcp,portForward0.address=127.0.0.1,portForward0.range0.start={PORT},portForward0.range0.to=22",
        "--import",
        "--graphics",
        "none",
        "--noautoconsole",
        "--wait",
        "0",
    ]
    run(command, timeout=120)
    vm_uuid = virsh("domuuid", NAME).stdout.strip()
    (INSTANCE / "identity.json").write_text(
        json.dumps(
            {
                "name": NAME,
                "uuid": vm_uuid,
                "disk": str(overlay),
                "seed": str(INSTANCE / "seed.iso"),
            }
        )
        + "\n"
    )
    wait_ssh()
    print(f"BOOT_SECONDS={time.monotonic() - start:.2f}")
    deploy_start = time.monotonic()
    deploy()
    print(f"DEPLOY_SECONDS={time.monotonic() - deploy_start:.2f}")


def status() -> None:
    if not domain_exists():
        print("DOMAIN=ABSENT")
        return
    print(f"DOMAIN={virsh('domstate', NAME).stdout.strip()}")
    if not (INSTANCE / "known_hosts").is_file():
        raise LabError("domain exists without its pinned SSH host key")
    filesystem = guest(
        "sudo -n findmnt -n -o FSTYPE --target /home/hermes/gateway-state", check=False, timeout=30
    )
    mode = (
        "live"
        if filesystem.returncode == 0 and filesystem.stdout.strip() == "tmpfs"
        else "synthetic"
    )
    result = guest(
        f"sudo -n python3 /opt/hermes-deploy/scripts/hermes/profile-deploy.py status --mode {mode}",
        check=False,
        timeout=30,
    )
    print(result.stdout.strip() if result.returncode == 0 else "GUEST_STATUS=UNAVAILABLE")


def reboot() -> None:
    before = guest("cat /proc/sys/kernel/random/boot_id").stdout.strip()
    virsh("reboot", NAME)
    until = time.monotonic() + 360
    while time.monotonic() < until:
        result = guest("cat /proc/sys/kernel/random/boot_id", check=False, timeout=12)
        if result.returncode == 0 and result.stdout.strip() != before:
            status()
            return
        time.sleep(3)
    raise LabError("guest did not return with a new boot ID")


def fault_test() -> None:
    if not domain_exists():
        raise LabError("the disposable lab domain is absent")
    guest(
        "sudo -n sh -c 'cd /home/hermes && runuser -u hermes -- env -i "
        "HOME=/home/hermes USER=hermes LOGNAME=hermes PATH=/usr/bin:/bin "
        "XDG_RUNTIME_DIR=/run/user/$(id -u hermes) "
        "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u hermes)/bus "
        "systemctl --user stop hermes-worker.service'"
    )
    deploy()
    print("RECOVERY=PASS stopped worker service restored by unattended deploy rerun")


def live_source():
    source = ROOT / "scripts/hermes/live-smoke.py"
    spec = importlib.util.spec_from_file_location("hermes_live_smoke", source)
    if spec is None or spec.loader is None:
        raise LabError("private live source helper is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def live_values() -> tuple[bytes, str]:
    source = live_source()
    try:
        source.private_directory()
        values = {name: source.read_private(name) for name in source.FILES}
    except source.Refusal as exc:
        raise LabError(f"private host setup is incomplete: {exc}") from None
    if values["user"] != values["chat"] or not values["user"].isdigit():
        raise LabError("live integration requires one authorized private Telegram chat")
    if values["cap"] not in {"verified", "unavailable"}:
        raise LabError("provider cap status is unrecognized")
    for name in ("deepseek", "telegram"):
        value = values[name]
        if not value.isascii() or any(ord(char) < 33 or ord(char) > 126 for char in value):
            raise LabError(
                f"private {name} value cannot be represented safely in the guest profile"
            )
    bot = values["telegram"]
    try:
        webhook = source.post_json(f"https://api.telegram.org/bot{bot}/getWebhookInfo", {})
        updates = source.post_json(
            f"https://api.telegram.org/bot{bot}/getUpdates",
            {"limit": 1, "timeout": 0, "allowed_updates": ["message"]},
        )
    except source.Refusal as exc:
        raise LabError(f"dedicated Telegram bot preflight failed: {exc}") from None
    if webhook.get("ok") is not True or (webhook.get("result") or {}).get("url"):
        raise LabError("dedicated Telegram bot has an active or unverified webhook")
    if updates.get("ok") is not True or updates.get("result") != []:
        raise LabError(
            "dedicated Telegram bot has pending updates; clear them privately before live start"
        )
    payload = (
        f"DEEPSEEK_API_KEY={values['deepseek']}\n"
        f"TELEGRAM_BOT_TOKEN={bot}\n"
        f"TELEGRAM_ALLOWED_USERS={values['user']}\n"
        "TELEGRAM_ALLOW_ALL_USERS=false\n"
    ).encode("ascii")
    return payload, values["cap"]


def live_guest(action: str, payload: bytes | None = None) -> None:
    remote = f"sudo -n python3 /opt/hermes-deploy/scripts/hermes/live-guest.py {action}"
    if payload is None:
        result = guest(remote, check=False, timeout=60)
    else:
        try:
            result = subprocess.run(
                [*ssh_base(), remote], input=payload, capture_output=True, check=False, timeout=60
            )
        except subprocess.TimeoutExpired:
            raise LabError("guest live credential transfer timed out") from None
    if result.returncode:
        # SSH and guest stderr can include application output. Never copy them
        # into the host terminal once a private payload is involved.
        stderr = (
            result.stderr.decode("utf-8", "replace")
            if isinstance(result.stderr, bytes)
            else result.stderr
        )
        safe_reasons = {
            "STOP: live tmpfs must be empty before private provisioning",
            "STOP: private live environment has an invalid size or shape",
            "STOP: private live environment is not ASCII",
            "STOP: private live environment contains an invalid value",
            "STOP: private live environment has unexpected keys",
            "STOP: synthetic key is not valid in live mode",
            "STOP: Telegram private allowlist is invalid",
            "STOP: cannot inspect rootless Podman ID mapping",
            "STOP: rootless Podman ID map lacks gateway UID",
            "STOP: guest swap must be disabled before private provisioning",
        }
        if stderr.strip() in safe_reasons:
            raise LabError(f"guest live {action} failed: {stderr.strip()}")
        raise LabError(f"guest live {action} failed (exit {result.returncode})")


def live_deploy_error(result: subprocess.CompletedProcess[str], payload: bytes) -> str:
    """Return only a short, redacted guest deployer STOP reason."""
    reason = result.stderr.strip()
    if not reason.startswith("STOP: ") or "\n" in reason or len(reason) > 240:
        return "live Hermes deployment failed"
    for line in payload.decode("ascii").splitlines():
        if "=" in line:
            value = line.split("=", 1)[1]
            if len(value) >= 4:
                reason = reason.replace(value, "[redacted]")
    if "http:" in reason or "https:" in reason:
        return "live Hermes deployment failed"
    return f"live Hermes deployment failed: {reason}"


def live_start() -> None:
    if not domain_exists() or not (INSTANCE / "identity.json").is_file():
        raise LabError("owned disposable VM is absent; run 'run' first")
    identity = json.loads((INSTANCE / "identity.json").read_text())
    if identity.get("name") != NAME or virsh("domuuid", NAME).stdout.strip() != identity.get(
        "uuid"
    ):
        raise LabError("disposable VM identity changed")
    if (
        guest("sudo -n findmnt -n -o FSTYPE --target /home/hermes/gateway-state").stdout.strip()
        == "tmpfs"
    ):
        print("LIVE=UNCHANGED guest tmpfs profile already active")
        return
    payload, cap = live_values()
    preflight = guest(
        "sudo -n python3 /opt/hermes-deploy/scripts/hermes/profile-deploy.py status --mode synthetic",
        check=False,
    )
    if preflight.returncode:
        raise LabError("synthetic VM baseline is not healthy")
    transfer_source()
    try:
        live_guest("prepare")
        live_guest("inject", payload)
        result = guest(
            "sudo -n python3 /opt/hermes-deploy/scripts/hermes/profile-deploy.py apply --mode live",
            check=False,
            timeout=1800,
        )
        if result.returncode:
            raise LabError(live_deploy_error(result, payload))
        print(result.stdout.strip())
    except Exception:
        try:
            live_guest("clear")
            guest(
                "sudo -n python3 /opt/hermes-deploy/scripts/hermes/profile-deploy.py apply --mode synthetic",
                check=False,
                timeout=1800,
            )
        except Exception:
            raise LabError(
                "live startup failed; inspect and clean the exact VM immediately"
            ) from None
        raise
    print(f"LIVE=READY dedicated private bot, tmpfs-only guest profile; provider_cap={cap}")


def live_status() -> None:
    if not domain_exists():
        print("LIVE=ABSENT disposable VM is absent")
        return
    filesystem = guest(
        "sudo -n findmnt -n -o FSTYPE --target /home/hermes/gateway-state", check=False, timeout=30
    )
    if filesystem.returncode or filesystem.stdout.strip() != "tmpfs":
        print("LIVE=INACTIVE no guest tmpfs profile")
        return
    result = guest(
        "sudo -n python3 /opt/hermes-deploy/scripts/hermes/profile-deploy.py status --mode live",
        check=False,
        timeout=30,
    )
    if result.returncode:
        raise LabError("live guest profile is mounted but Hermes status failed")
    print("LIVE=READY " + result.stdout.strip())


def live_stop() -> None:
    if not domain_exists():
        print("LIVE=ABSENT disposable VM is absent")
        return
    filesystem = guest(
        "sudo -n findmnt -n -o FSTYPE --target /home/hermes/gateway-state", check=False, timeout=30
    )
    if filesystem.returncode or filesystem.stdout.strip() != "tmpfs":
        print("LIVE=ALREADY_STOPPED guest tmpfs profile absent")
        return
    live_guest("clear")
    result = guest(
        "sudo -n python3 /opt/hermes-deploy/scripts/hermes/profile-deploy.py apply --mode synthetic",
        check=False,
        timeout=1800,
    )
    if result.returncode:
        raise LabError("guest live credentials cleared but synthetic service restoration failed")
    print("LIVE=STOPPED guest tmpfs cleared; synthetic profile restored")


def clean() -> None:
    marker = INSTANCE / "identity.json"
    if domain_exists():
        if not marker.is_file():
            raise LabError("domain exists without the instance ownership marker")
        identity = json.loads(marker.read_text())
        if identity.get("name") != NAME or virsh("domuuid", NAME).stdout.strip() != identity.get(
            "uuid"
        ):
            raise LabError("domain identity differs from the owned instance")
        devices = virsh("domblklist", NAME, "--details").stdout
        for path in re.findall(r"/\S+", devices):
            if path not in {identity["disk"], identity["seed"]}:
                raise LabError("domain has an unrecognized attached disk")
        if virsh("domstate", NAME).stdout.strip() != "shut off":
            virsh("destroy", NAME)
        virsh("undefine", NAME)
    if INSTANCE.exists():
        if INSTANCE.is_symlink():
            raise LabError("instance directory is a symlink")
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
        }
        if marker.is_file():
            identity = json.loads(marker.read_text())
            if identity.get("name") != NAME or identity.get("disk") != str(INSTANCE / "disk.qcow2"):
                raise LabError("instance ownership marker differs from expected paths")
            allowed.add("identity.json")
        if any(
            p.name not in allowed or p.is_symlink() or not p.is_file() for p in INSTANCE.iterdir()
        ):
            raise LabError("instance contains an unexpected path")
        shutil.rmtree(INSTANCE)
    print("CLEAN=PASS exact disposable VM and instance state absent; verified base retained")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "run",
            "deploy",
            "status",
            "reboot",
            "fault-test",
            "clean",
            "verify-base",
            "live-start",
            "live-status",
            "live-stop",
        ),
    )
    args = parser.parse_args()
    try:
        if args.action == "run":
            fresh_run()
        elif args.action == "deploy":
            deploy()
        elif args.action == "status":
            status()
        elif args.action == "reboot":
            reboot()
        elif args.action == "fault-test":
            fault_test()
        elif args.action == "clean":
            clean()
        elif args.action == "live-start":
            live_start()
        elif args.action == "live-status":
            live_status()
        elif args.action == "live-stop":
            live_stop()
        else:
            verified_base()
    except (LabError, subprocess.TimeoutExpired) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
