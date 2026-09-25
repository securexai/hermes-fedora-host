#!/usr/bin/env python3
"""Temporary fixed-operation access for the retained DeepSeek E2E VM.

``check`` is offline. ``install`` is a one-time private host-root bootstrap.
After installation, ``stage`` and ``run`` use a dedicated SSH key and only
root-owned guest code selected by exact sudoers argument rules. No sudo password
or provider secret is stored or passed as an argument.
"""

import argparse
import ast
import base64
import hashlib
import io
import json
import os
import pwd
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from xml.etree import ElementTree

DOMAIN = "lab-hermes-deepseek-e2e-r1"
UUID = "4349a2bc-67b6-42b7-a6ef-5aeee5ee4009"
MAC = "52:54:00:83:bf:4b"
MACHINE_SHA256 = "f8c01e74f672760c10bdbc91023d98ff5173bb9652da1d6e3d2c4cba00d00682"
HOST_FINGERPRINT = "SHA256:jJHOZL7RV7Cqw0QI8DpUuXe7Hn/NdCTgv3D2hQBUU5Q"
HOST_IP = "192.168.124.1"
GUEST_IP = "192.168.124.5"
HOST_USER = "aicloudopspecial"
GUEST_USER = "aicowork"
HOST_BASE = Path("/var/usrlocal/libexec/hermes-deepseek-test")
GUEST_BASE = Path("/usr/local/libexec/hermes-deepseek-test")
HOST_RULE = Path("/etc/sudoers.d/90-hermes-deepseek-test-host")
GUEST_RULE = Path("/etc/sudoers.d/90-hermes-deepseek-test-guest")
GUEST_ARCHIVE = Path("/home/aicowork/hermes-deepseek-bundle.tar")
STATE_DIR = Path("/var/home/aicloudopspecial/.local/state/hermes-deepseek-test")
VIRSH = ("/usr/bin/virsh", "-c", "qemu:///system")
HOST_OPS = ("status", "start", "shutdown", "inspect-boot", "teardown")
# Exact artifacts left by the interrupted 2026-09-24 bootstrap. These are only
# eligible for replacement while both host and guest grant rules are absent.
PREVIOUS_HOST_CODE_SHA256 = "86fd61be24ab08106c236a2d446003b6987c671659aa83529cb0474a555af47f"
PREVIOUS_BUNDLE_SHA256 = "28f668d12ecf01c198083ec1ae95d84771432898b99b5e580518613beaffec89"
GUEST_HELPERS = {
    "boot-preflight": ("boot/tpm-enroll.sh", ("--preflight",)),
    "boot-enroll": ("boot/tpm-enroll.sh", ("--enroll", "--apply")),
    "boot-verify": ("boot/b4-verify.sh", ()),
    "boot-fallback": ("boot/fallback-wipe.sh", ("--apply",)),
    "m00": ("m00-pin-host-identity.sh", ("--apply",)),
    "worker-key": ("provision-worker-client-key.sh", ()),
    "m01": ("m01-host-prepare.sh", ("--apply",)),
    "m02": ("m02-deploy-and-validate.sh", ("--apply",)),
    "m03-activate": ("m03-activate.sh", ("--apply",)),
    "m03-configure": ("m03-configure-and-probe.sh", ("--apply",)),
    "m03-contract": ("m03-contract.sh", ("--apply",)),
    "deepseek-key": ("provision-deepseek-key.sh", ()),
    "m03-accept": ("m03-accept.sh", ("--apply", "--allow-provider-call")),
    "m04-posture": ("m04-posture.sh", ("--apply",)),
    "m04-backup": ("m04-backup.sh", ("--apply",)),
    "telegram": ("provision-telegram.sh", ()),
    "m05": ("m05-telegram.sh", ("--apply",)),
    "m05-tests": ("m05-tests.sh", ("status",)),
    "m05-allowlist-swap": ("m05-tests.sh", ("allowlist-swap", "--apply")),
    "m05-allowlist-restore": ("m05-tests.sh", ("allowlist-restore", "--apply")),
    "m05-worker-stop": ("m05-tests.sh", ("worker-stop", "--apply")),
    "m05-worker-start": ("m05-tests.sh", ("worker-start", "--apply")),
    "m05-logs": ("m05-tests.sh", ("logs",)),
    "m04-readonly": ("m04-readonly-gateway.sh", ("--apply",)),
    "m04-reboot": ("m04-reboot.sh", ("--apply",)),
    "m04-postboot": ("m04-postboot.sh", ("--apply",)),
    "m04-postboot-probe": ("m04-postboot-probe.sh", ("--apply",)),
}
GUEST_OPS = ("status", "install-bundle", *GUEST_HELPERS)


def stop(message: str) -> None:
    raise RuntimeError(message)


def run(*argv: str, timeout: int = 30, input_text: str | None = None) -> str:
    result = subprocess.run(
        argv, input=input_text, capture_output=True, text=True, timeout=timeout, check=True
    )
    return result.stdout.strip()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def trusted(path: Path, mode: int | None = None) -> None:
    for item in (path, *path.parents):
        if item == Path("/"):
            break
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            stop(f"untrusted path: {item}")
    if mode is not None and stat.S_IMODE(path.stat().st_mode) != mode:
        stop(f"wrong mode: {path}")


def installed_file(path: Path, content: bytes, mode: int) -> None:
    if path.exists() or path.is_symlink():
        trusted(path, mode)
        if not path.is_file() or path.read_bytes() != content:
            stop(f"installed file differs: {path}")
        return
    trusted(path.parent)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(path, mode)
    trusted(path, mode)


def rule(kind: str) -> bytes:
    if kind == "host":
        base, user, side, operations = HOST_BASE, HOST_USER, "host", HOST_OPS
    else:
        base, user, side, operations = GUEST_BASE, GUEST_USER, "guest", GUEST_OPS
    commands = ", ".join(
        f"/usr/bin/python3 -I {base}/access.py {side} {operation}" for operation in operations
    )
    return (
        f"# Temporary exact-VM Hermes DeepSeek test access.\n{user} ALL=(root) NOPASSWD: {commands}\n"
    ).encode()


def check_rule(content: bytes) -> None:
    with tempfile.NamedTemporaryFile(prefix="hermes-sudoers-", delete=False) as stream:
        path = Path(stream.name)
        stream.write(content)
    try:
        run("/usr/sbin/visudo", "-cf", str(path))
    finally:
        path.unlink()


def source_files() -> tuple[Path, Path, Path]:
    here = Path(__file__).resolve().parent
    manual = here.parent
    inspector = here / "deepseek-boot-inspect.py"
    if not inspector.is_file() or not (manual / "m02-deploy-and-validate.sh").is_file():
        stop("Hermes manual source bundle is incomplete")
    for helper, _ in GUEST_HELPERS.values():
        if not (manual / helper).is_file():
            stop(f"required helper absent: {helper}")
    return here / "deepseek-test-grant.py", inspector, manual


def archive(manual: Path) -> bytes:
    output = io.BytesIO()
    total = 0
    with tarfile.open(fileobj=output, mode="w") as tar:
        for path in sorted(manual.rglob("*")):
            if path.relative_to(manual).parts[0] == "lab":
                continue
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            if path.is_symlink() or not (path.is_file() or path.is_dir()):
                stop(f"unsupported manual source: {path}")
            relative = path.relative_to(manual).as_posix()
            info = tarfile.TarInfo(relative)
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ""
            if path.is_dir():
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)
            else:
                content = path.read_bytes()
                total += len(content)
                if total > 10_000_000:
                    stop("manual bundle exceeds 10 MB")
                info.size = len(content)
                info.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                tar.addfile(info, io.BytesIO(content))
    return output.getvalue()


def check() -> None:
    source, inspector, manual = source_files()
    check_rule(rule("host"))
    check_rule(rule("guest"))
    ast.parse(source.read_text())
    ast.parse(inspector.read_text())
    ast.parse(GUEST_GRANT_INVENTORY)
    ast.parse(GUEST_BOOTSTRAP.replace("PAYLOAD", "'AA=='"))
    ast.parse(GUEST_CLEANUP.replace("PAYLOAD", "'AA=='"))
    package = archive(manual)
    with tarfile.open(fileobj=io.BytesIO(package), mode="r:") as tar:
        names: set[str] = set()
        for member in tar:
            archive_member_path(member, names)
    print(
        f"CHECK=PASS host_ops={len(HOST_OPS)} guest_ops={len(GUEST_OPS)} bundle_sha256={digest(package)}"
    )


def virsh(*args: str) -> str:
    return run(*VIRSH, *args)


def bound_vm() -> str:
    if virsh("domuuid", DOMAIN) != UUID:
        stop("VM UUID mismatch")
    interfaces = virsh("domiflist", DOMAIN)
    if not any(
        len(parts := line.split()) >= 5
        and parts[1] == "network"
        and parts[2] == "fvh-nat"
        and parts[4] == MAC
        for line in interfaces.splitlines()
    ):
        stop("VM network or MAC mismatch")
    return virsh("domstate", DOMAIN)


def bound_network() -> None:
    network = ElementTree.fromstring(virsh("net-dumpxml", "fvh-nat"))
    if network.find("./ip") is None or network.find("./ip").get("address") != HOST_IP:
        stop("fvh-nat gateway address mismatch")
    leases = virsh("domifaddr", DOMAIN, "--source", "lease")
    if not any(
        len(parts := line.split()) >= 4
        and parts[1] == MAC
        and parts[2] == "ipv4"
        and parts[3].split("/", 1)[0] == GUEST_IP
        for line in leases.splitlines()
    ):
        stop("VM lease address mismatch")


def agent(payload: dict) -> dict:
    response = json.loads(virsh("qemu-agent-command", DOMAIN, json.dumps(payload)))
    if "error" in response or "return" not in response:
        stop("guest agent rejected fixed operation")
    return response["return"]


def guest_script(script: str) -> str:
    pid = agent(
        {
            "execute": "guest-exec",
            "arguments": {
                "path": "/usr/bin/python3",
                "arg": ["-I", "-"],
                "input-data": base64.b64encode(script.encode()).decode(),
                "capture-output": True,
            },
        }
    )["pid"]
    for _ in range(300):
        status = agent({"execute": "guest-exec-status", "arguments": {"pid": pid}})
        if status["exited"]:
            output = base64.b64decode(status.get("out-data", "")).decode(errors="replace")
            if status.get("exitcode") != 0:
                error = base64.b64decode(status.get("err-data", "")).decode(errors="replace")
                stop(f"guest operation failed exit={status.get('exitcode')} stderr={error[:300]!r}")
            if len(output) > 4000:
                stop("guest output exceeded bound")
            return output
        time.sleep(0.1)
    stop("guest operation timed out")


GUEST_IDENTITY = r"""
import hashlib
from pathlib import Path
import os
print('guest_user=' + str(os.geteuid()))
print('machine_sha256=' + hashlib.sha256(Path('/etc/machine-id').read_bytes()).hexdigest())
"""


def guest_identity() -> str:
    output = guest_script(GUEST_IDENTITY)
    lines = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    if lines.get("guest_user") != "0" or lines.get("machine_sha256") != MACHINE_SHA256:
        stop("guest identity mismatch")
    scanned = run("/usr/bin/ssh-keyscan", "-T", "5", "-t", "ed25519", GUEST_IP, timeout=10)
    keys = [line.split() for line in scanned.splitlines() if line and not line.startswith("#")]
    if len(keys) != 1 or len(keys[0]) < 3 or keys[0][:2] != [GUEST_IP, "ssh-ed25519"]:
        stop("guest SSH host key scan ambiguous")
    key = keys[0]
    fingerprint = (
        base64.b64encode(hashlib.sha256(base64.b64decode(key[2], validate=True)).digest())
        .decode()
        .rstrip("=")
    )
    if "SHA256:" + fingerprint != HOST_FINGERPRINT:
        stop("guest SSH host key fingerprint mismatch")
    return f"{GUEST_IP} {key[1]} {key[2]}\n"


GUEST_GRANT_INVENTORY = r"""
from pathlib import Path
base = Path('/usr/local/libexec/hermes-deepseek-test')
keys = Path('/home/aicowork/.ssh/authorized_keys')
paths = (
    Path('/etc/sudoers.d/90-hermes-deepseek-test-guest'),
    Path('/etc/hermes-deepseek-test/bundle.sha256'),
    base,
    Path('/home/aicowork/hermes-deepseek-bundle.tar'),
)
marker = keys.exists() and any(
    line.endswith(' hermes-deepseek-test') for line in keys.read_text().splitlines()
)
print('GUEST_GRANT_STATE=' + ('PRESENT' if marker or any(p.exists() or p.is_symlink() for p in paths) else 'ABSENT'))
"""


def reconcile_previous_host_copy(source: bytes, inspector: bytes, package: bytes) -> None:
    """Converge only the known interrupted host copy before publishing a new pin."""
    if not HOST_BASE.exists() and not HOST_BASE.is_symlink():
        return
    trusted(HOST_BASE, 0o755)
    files = {
        HOST_BASE / "access.py": (source, PREVIOUS_HOST_CODE_SHA256),
        HOST_BASE / "boot-inspect.py": (inspector, None),
        HOST_BASE / "bundle.tar": (package, PREVIOUS_BUNDLE_SHA256),
    }
    if set(HOST_BASE.iterdir()) - set(files):
        stop("unexpected host access artifact")
    stale = []
    for path, (current, previous_hash) in files.items():
        if not path.exists() and not path.is_symlink():
            continue
        trusted(path, 0o644)
        content = path.read_bytes()
        if content == current:
            continue
        if previous_hash is None or digest(content) != previous_hash:
            stop(f"unrecognized host access artifact: {path}")
        stale.append(path)
    if not stale:
        return
    if HOST_RULE.exists() or HOST_RULE.is_symlink():
        stop("host grant exists; refusing bundle replacement")
    if guest_script(GUEST_GRANT_INVENTORY).strip() != "GUEST_GRANT_STATE=ABSENT":
        stop("guest grant state is not absent; refusing bundle replacement")
    for path in stale:
        path.unlink()
    print("PARTIAL_HOST_COPY=RECONCILED")


GUEST_BOOTSTRAP = r"""
import base64, hashlib, json, os, pathlib, pwd, stat, subprocess, tempfile
data = json.loads(base64.b64decode(PAYLOAD))
assert os.geteuid() == 0
assert hashlib.sha256(pathlib.Path('/etc/machine-id').read_bytes()).hexdigest() == data['machine']
base = pathlib.Path('/usr/local/libexec/hermes-deepseek-test')
rule = pathlib.Path('/etc/sudoers.d/90-hermes-deepseek-test-guest')
pin = pathlib.Path('/etc/hermes-deepseek-test/bundle.sha256')
for parent in (pathlib.Path('/usr'), pathlib.Path('/usr/local'), pathlib.Path('/etc'),
               pathlib.Path('/etc/sudoers.d')):
    s = parent.lstat()
    assert stat.S_ISDIR(s.st_mode) and s.st_uid == 0 and not s.st_mode & 0o022
libexec = pathlib.Path('/usr/local/libexec')
if not libexec.exists(): libexec.mkdir(mode=0o755)
s = libexec.lstat()
assert stat.S_ISDIR(s.st_mode) and s.st_uid == 0 and not s.st_mode & 0o022
for directory in (base, pin.parent):
    if not directory.exists():
        directory.mkdir(mode=0o755)
    s = directory.lstat()
    assert stat.S_ISDIR(s.st_mode) and s.st_uid == 0 and not s.st_mode & 0o022
def put(path, content, mode):
    if path.exists() or path.is_symlink():
        s = path.lstat()
        assert stat.S_ISREG(s.st_mode) and s.st_uid == 0 and stat.S_IMODE(s.st_mode) == mode
        assert path.read_bytes() == content
    else:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, mode)
put(base / 'access.py', base64.b64decode(data['code']), 0o644)
put(pin, (data['bundle_hash'] + '\n').encode(), 0o644)
with tempfile.NamedTemporaryFile(dir='/etc/sudoers.d', prefix='.hermes-check-', delete=False) as stream:
    temporary = pathlib.Path(stream.name)
    stream.write(base64.b64decode(data['rule']))
os.chmod(temporary, 0o440)
try:
    subprocess.run(['/usr/sbin/visudo', '-cf', str(temporary)], check=True, capture_output=True)
finally:
    temporary.unlink()
user = pwd.getpwnam('aicowork')
ssh_dir = pathlib.Path(user.pw_dir) / '.ssh'
if not ssh_dir.exists():
    ssh_dir.mkdir(mode=0o700)
    os.chown(ssh_dir, user.pw_uid, user.pw_gid)
s = ssh_dir.lstat()
assert stat.S_ISDIR(s.st_mode) and s.st_uid == user.pw_uid and not s.st_mode & 0o077
authorized = ssh_dir / 'authorized_keys'
assert not authorized.is_symlink()
if authorized.exists():
    s = authorized.lstat()
    assert stat.S_ISREG(s.st_mode) and s.st_uid == user.pw_uid and not s.st_mode & 0o077
    existing = authorized.read_text()
else:
    existing = ''
entry = data['authorized_entry']
assert entry.startswith('restrict,pty,from="192.168.124.1" ssh-ed25519 ')
matches = [line for line in existing.splitlines() if line.endswith(' hermes-deepseek-test')]
assert not matches or matches == [entry]
if entry not in existing.splitlines():
    fd = os.open(authorized, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a') as stream:
        if existing and not existing.endswith('\n'):
            stream.write('\n')
        stream.write(entry + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.chown(authorized, user.pw_uid, user.pw_gid)
    os.chmod(authorized, 0o600)
subprocess.run(['/usr/sbin/restorecon', str(ssh_dir), str(authorized)], check=True, capture_output=True)
put(rule, base64.b64decode(data['rule']), 0o440)
subprocess.run(['/usr/sbin/visudo', '-cf', str(rule)], check=True, capture_output=True)
subprocess.run(['/usr/sbin/restorecon', '-R', str(base), str(pin.parent), str(rule)], check=True, capture_output=True)
subprocess.run(['/usr/bin/logger', '-t', 'hermes-deepseek-test', 'guest action=bootstrap result=success'], check=True)
print('GUEST_GRANT_INSTALLED')
"""

GUEST_CLEANUP = r"""
import base64, hashlib, json, os, pathlib, pwd, shutil, stat, subprocess, tempfile
data = json.loads(base64.b64decode(PAYLOAD))
assert os.geteuid() == 0
assert hashlib.sha256(pathlib.Path('/etc/machine-id').read_bytes()).hexdigest() == data['machine']
base = pathlib.Path('/usr/local/libexec/hermes-deepseek-test')
rule = pathlib.Path('/etc/sudoers.d/90-hermes-deepseek-test-guest')
pin = pathlib.Path('/etc/hermes-deepseek-test/bundle.sha256')
expected_rule = base64.b64decode(data['rule'])
expected_code = base64.b64decode(data['code'])
def root_file(path, content, mode):
    if path.exists() or path.is_symlink():
        s = path.lstat()
        assert stat.S_ISREG(s.st_mode) and s.st_uid == 0 and stat.S_IMODE(s.st_mode) == mode
        assert path.read_bytes() == content
for directory in (base, pin.parent):
    if directory.exists() or directory.is_symlink():
        s = directory.lstat()
        assert stat.S_ISDIR(s.st_mode) and s.st_uid == 0 and not s.st_mode & 0o022
root_file(rule, expected_rule, 0o440)
root_file(base / 'access.py', expected_code, 0o644)
root_file(pin, (data['bundle_hash'] + '\n').encode(), 0o644)
root_file(base / 'bundle.sha256', (data['bundle_hash'] + '\n').encode(), 0o644)
bundle = base / 'bundle'
if bundle.exists() or bundle.is_symlink():
    assert bundle.is_dir() and not bundle.is_symlink()
    for item in (bundle, *bundle.rglob('*')):
        s = item.lstat()
        assert s.st_uid == 0 and not s.st_mode & 0o022
        assert stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode)
user = pwd.getpwnam('aicowork')
authorized = pathlib.Path(user.pw_dir) / '.ssh/authorized_keys'
entry = data['authorized_entry']
if authorized.exists() or authorized.is_symlink():
    s = authorized.lstat()
    assert stat.S_ISREG(s.st_mode) and s.st_uid == user.pw_uid and not s.st_mode & 0o077
    lines = authorized.read_text().splitlines()
    matches = [line for line in lines if line.endswith(' hermes-deepseek-test')]
    assert not matches or matches == [entry]
else:
    lines = []
if rule.exists(): rule.unlink()
if entry in lines:
    remaining = [line for line in lines if line != entry]
    with tempfile.NamedTemporaryFile(dir=authorized.parent, prefix='.hermes-keys-', delete=False, mode='w') as stream:
        temporary = pathlib.Path(stream.name)
        stream.write(''.join(line + '\n' for line in remaining))
        stream.flush()
        os.fsync(stream.fileno())
    os.chown(temporary, user.pw_uid, user.pw_gid)
    os.chmod(temporary, 0o600)
    os.replace(temporary, authorized)
    subprocess.run(['/usr/sbin/restorecon', str(authorized)], check=True, capture_output=True)
if bundle.exists(): shutil.rmtree(bundle)
for file in (base / 'bundle.sha256', base / 'access.py', pin):
    if file.exists(): file.unlink()
if base.exists(): base.rmdir()
if pin.parent.exists(): pin.parent.rmdir()
subprocess.run(['/usr/bin/logger', '-t', 'hermes-deepseek-test', 'guest action=cleanup result=success'], check=True)
print('GUEST_GRANTS_ABSENT')
"""


def user_state() -> tuple[Path, str]:
    account = pwd.getpwnam(HOST_USER)
    if os.geteuid() != 0 and os.geteuid() != account.pw_uid:
        stop("wrong workstation account")
    for parent in (
        Path(account.pw_dir),
        Path(account.pw_dir) / ".local",
        Path(account.pw_dir) / ".local/state",
    ):
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != account.pw_uid or info.st_mode & 0o022:
            stop(f"untrusted SSH state parent: {parent}")
    return STATE_DIR, str(account.pw_uid)


def keypair() -> str:
    state, uid_text = user_state()
    uid = int(uid_text)
    gid = pwd.getpwnam(HOST_USER).pw_gid
    if not state.exists():
        state.mkdir(parents=True, mode=0o700)
        os.chown(state, uid, gid)
    if (
        state.is_symlink()
        or state.stat().st_uid != uid
        or stat.S_IMODE(state.stat().st_mode) != 0o700
    ):
        stop("untrusted SSH state directory")
    private = state / "id_ed25519"
    public = state / "id_ed25519.pub"
    if private.is_symlink() or public.is_symlink():
        stop("dedicated SSH keypair path is a symlink")
    if not private.exists() and not public.exists():
        command = [
            "/usr/bin/ssh-keygen",
            "-q",
            "-t",
            "ed25519",
            "-N",
            "",
            "-C",
            "hermes-deepseek-test",
            "-f",
            str(private),
        ]
        if os.geteuid() == 0:
            run("/usr/sbin/runuser", "-u", HOST_USER, "--", *command)
        else:
            run(*command)
    if not private.is_file() or not public.is_file() or private.is_symlink() or public.is_symlink():
        stop("dedicated SSH keypair incomplete")
    if private.stat().st_uid != uid or stat.S_IMODE(private.stat().st_mode) != 0o600:
        stop("dedicated SSH private key permissions changed")
    if public.stat().st_uid != uid or public.stat().st_mode & 0o022:
        stop("dedicated SSH public key ownership or mode changed")
    publine = public.read_text().strip()
    if not publine.startswith("ssh-ed25519 "):
        stop("dedicated SSH public key invalid")
    derived = run("/usr/bin/ssh-keygen", "-y", "-P", "", "-f", str(private))
    if derived.split()[:2] != publine.split()[:2]:
        stop("dedicated SSH keypair differs")
    return publine


def install() -> None:
    if os.geteuid() != 0 or os.environ.get("SUDO_USER") != HOST_USER:
        stop("private host administrator bootstrap required")
    check()
    if bound_vm() != "running":
        stop("approved VM must be running for guest grant installation")
    bound_network()
    known = guest_identity()
    source, inspector, manual = source_files()
    public = keypair()
    package = archive(manual)
    for parent in (Path("/var"), Path("/var/usrlocal"), Path("/var/usrlocal/libexec")):
        trusted(parent)
    reconcile_previous_host_copy(source.read_bytes(), inspector.read_bytes(), package)
    if HOST_RULE.exists() or HOST_RULE.is_symlink():
        trusted(HOST_RULE, 0o440)
        if HOST_RULE.read_bytes() != rule("host"):
            stop("existing host sudoers rule differs")
    if not HOST_BASE.exists():
        HOST_BASE.mkdir(mode=0o755)
    trusted(HOST_BASE, 0o755)
    installed_file(HOST_BASE / "access.py", source.read_bytes(), 0o644)
    installed_file(HOST_BASE / "boot-inspect.py", inspector.read_bytes(), 0o644)
    installed_file(HOST_BASE / "bundle.tar", package, 0o644)
    run("/usr/sbin/restorecon", "-R", str(HOST_BASE))
    payload = {
        "machine": MACHINE_SHA256,
        "code": base64.b64encode(source.read_bytes()).decode(),
        "rule": base64.b64encode(rule("guest")).decode(),
        "bundle_hash": digest(package),
        "authorized_entry": f'restrict,pty,from="{HOST_IP}" {public}',
    }
    script = GUEST_BOOTSTRAP.replace(
        "PAYLOAD", repr(base64.b64encode(json.dumps(payload).encode()).decode())
    )
    if "GUEST_GRANT_INSTALLED" not in guest_script(script):
        stop("guest grant did not report success")
    state, _ = user_state()
    known_path = state / "known_hosts"
    if known_path.is_symlink():
        stop("dedicated known_hosts is a symlink")
    if known_path.exists():
        if (
            known_path.stat().st_uid != pwd.getpwnam(HOST_USER).pw_uid
            or stat.S_IMODE(known_path.stat().st_mode) != 0o600
            or known_path.read_text() != known
        ):
            stop("dedicated known_hosts differs")
    else:
        fd = os.open(known_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(known)
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(known_path, pwd.getpwnam(HOST_USER).pw_uid, pwd.getpwnam(HOST_USER).pw_gid)
        known_path.chmod(0o600)
    check_rule(rule("host"))
    installed_file(HOST_RULE, rule("host"), 0o440)
    run("/usr/sbin/restorecon", str(HOST_RULE))
    run("/usr/sbin/visudo", "-cf", str(HOST_RULE))
    run("/usr/bin/logger", "-t", "hermes-deepseek-test", "host action=bootstrap result=success")
    print(f"HOST_GRANT_INSTALLED bundle_sha256={digest(package)}")


def start_install() -> None:
    if os.geteuid() != 0 or os.environ.get("SUDO_USER") != HOST_USER:
        stop("private host administrator bootstrap required")
    check()
    state = bound_vm()
    if state == "shut off":
        print(virsh("start", DOMAIN))
    elif state != "running":
        stop(f"cannot bootstrap from state {state}")
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        if bound_vm() != "running":
            stop("exact VM stopped during bootstrap")
        try:
            bound_network()
            guest_identity()
            break
        except (OSError, RuntimeError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            time.sleep(2)
    else:
        stop("exact VM did not reach pinned network and guest identity; no grant installed")
    install()


def host(action: str) -> None:
    if os.geteuid() != 0 or os.environ.get("SUDO_USER") != HOST_USER:
        stop("wrong host invoking identity")
    trusted(HOST_BASE / "access.py", 0o644)
    state = bound_vm()
    run("/usr/bin/logger", "-t", "hermes-deepseek-test", f"host action={action} state={state}")
    if action == "status":
        print(f"domain={DOMAIN} state={state}")
    elif action == "start":
        if state == "shut off":
            print(virsh("start", DOMAIN))
        elif state != "running":
            stop(f"cannot start from state {state}")
    elif action == "shutdown":
        if state == "running":
            print(virsh("shutdown", DOMAIN))
        elif state != "shut off":
            stop(f"cannot shut down from state {state}")
    elif action == "inspect-boot":
        if state != "running":
            stop("VM is not running")
        subprocess.run(["/usr/bin/python3", "-I", str(HOST_BASE / "boot-inspect.py")], check=True)
    elif action == "teardown":
        if state != "running":
            stop("VM must be running to remove guest grants before final shutdown")
        source = HOST_BASE / "access.py"
        package = HOST_BASE / "bundle.tar"
        payload = {
            "machine": MACHINE_SHA256,
            "rule": base64.b64encode(rule("guest")).decode(),
            "code": base64.b64encode(source.read_bytes()).decode(),
            "bundle_hash": digest(package.read_bytes()),
            "authorized_entry": f'restrict,pty,from="{HOST_IP}" {STATE_DIR.joinpath("id_ed25519.pub").read_text().strip()}',
        }
        script = GUEST_CLEANUP.replace(
            "PAYLOAD", repr(base64.b64encode(json.dumps(payload).encode()).decode())
        )
        if "GUEST_GRANTS_ABSENT" not in guest_script(script):
            stop("guest grant cleanup unverified; VM remains running")
        virsh("shutdown", DOMAIN)
        for _ in range(60):
            if bound_vm() == "shut off":
                break
            time.sleep(2)
        if bound_vm() != "shut off":
            stop("guest grants removed but VM did not shut off; host grant retained")
        if HOST_RULE.read_bytes() != rule("host"):
            stop("VM off and guest grants absent, but host rule differs; preserve for review")
        HOST_RULE.unlink()
        for item in (
            HOST_BASE / "bundle.tar",
            HOST_BASE / "boot-inspect.py",
            HOST_BASE / "access.py",
        ):
            trusted(item, 0o644)
            item.unlink()
        HOST_BASE.rmdir()
        known = STATE_DIR / "known_hosts"
        private = STATE_DIR / "id_ed25519"
        public = STATE_DIR / "id_ed25519.pub"
        for item in (known, private, public):
            if item.exists():
                if item.is_symlink() or item.stat().st_uid != pwd.getpwnam(HOST_USER).pw_uid:
                    stop(f"temporary SSH state differs: {item}")
                item.unlink()
        if any(STATE_DIR.iterdir()):
            print(f"state_dir_retained={STATE_DIR} (unrelated files preserved)")
        else:
            STATE_DIR.rmdir()
        print(f"domain={DOMAIN} state=shut off grants=absent")
    else:
        stop("host operation denied")
    run("/usr/bin/logger", "-t", "hermes-deepseek-test", f"host action={action} result=success")


def guest(action: str) -> None:
    if os.geteuid() != 0 or os.environ.get("SUDO_USER") != GUEST_USER:
        stop("wrong guest invoking identity")
    trusted(GUEST_BASE / "access.py", 0o644)
    if digest(Path("/etc/machine-id").read_bytes()) != MACHINE_SHA256:
        stop("guest machine identity mismatch")
    if action == "status":
        run("/usr/bin/logger", "-t", "hermes-deepseek-test", "guest action=status result=success")
        print(
            f"guest_machine_sha256={MACHINE_SHA256} bundle_present={(GUEST_BASE / 'bundle').is_dir()}"
        )
        return
    if action == "install-bundle":
        run(
            "/usr/bin/logger",
            "-t",
            "hermes-deepseek-test",
            "guest action=install-bundle result=start",
        )
        install_bundle()
        run(
            "/usr/bin/logger",
            "-t",
            "hermes-deepseek-test",
            "guest action=install-bundle result=success",
        )
        return
    if action not in GUEST_HELPERS:
        stop("guest operation denied")
    bundle = GUEST_BASE / "bundle"
    trusted(bundle)
    helper, args = GUEST_HELPERS[action]
    path = bundle / helper
    trusted(path)
    env = {
        "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
        "HOME": "/root",
        "LC_ALL": "C",
        "TERM": "xterm",
        "HERMES_EXPECT_MACHINE_ID_SHA256": MACHINE_SHA256,
        "HERMES_PROVIDER": "deepseek",
        "HERMES_MODEL": "deepseek-flash",
    }
    run("/usr/bin/logger", "-t", "hermes-deepseek-test", f"guest action={action} result=start")
    status = subprocess.run(["/usr/bin/bash", str(path), *args], env=env).returncode
    run("/usr/bin/logger", "-t", "hermes-deepseek-test", f"guest action={action} result={status}")
    if status:
        raise SystemExit(status)


def archive_member_path(member: tarfile.TarInfo, names: set[str]) -> Path:
    path = Path(member.name)
    canonical = path.as_posix()
    if (
        path.is_absolute()
        or ".." in path.parts
        or canonical in ("", ".")
        or member.name.rstrip("/") != canonical
        or canonical in names
    ):
        stop("unsafe archive path")
    if not (member.isfile() or member.isdir()):
        stop("unsupported archive member")
    names.add(canonical)
    return path


def install_bundle() -> None:
    expected = Path("/etc/hermes-deepseek-test/bundle.sha256").read_text().strip()
    if len(expected) != 64 or not all(c in "0123456789abcdef" for c in expected):
        stop("invalid bundle pin")
    file = GUEST_ARCHIVE
    account = pwd.getpwnam(GUEST_USER)
    if not file.is_file() or file.is_symlink() or file.stat().st_uid != account.pw_uid:
        stop("staged bundle absent or untrusted")
    if file.stat().st_mode & 0o022 or file.stat().st_size > 12_000_000:
        stop("staged bundle writable or oversized")
    if digest(file.read_bytes()) != expected:
        stop("staged bundle hash mismatch")
    destination = GUEST_BASE / "bundle"
    marker = GUEST_BASE / "bundle.sha256"
    if destination.exists():
        trusted(destination)
        if marker.read_text().strip() != expected:
            stop("installed bundle differs")
        print("BUNDLE=UNCHANGED")
        return
    temporary = Path(tempfile.mkdtemp(prefix=".bundle-", dir=GUEST_BASE))
    try:
        with tarfile.open(file, mode="r:") as tar:
            names = set()
            unpacked = 0
            for member in tar:
                path = archive_member_path(member, names)
                unpacked += member.size
                if unpacked > 10_000_000:
                    stop("bundle content exceeds limit")
                target = temporary / path
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with tar.extractfile(member) as source, target.open("xb") as output:
                        shutil.copyfileobj(source, output)
                    target.chmod(0o755 if member.mode & 0o111 else 0o644)
        installed_file(marker, (expected + "\n").encode(), 0o644)
        os.rename(temporary, destination)
        print("BUNDLE=INSTALLED")
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def ssh_command(*remote: str, tty: bool = False) -> list[str]:
    verify_client_state()
    return [
        "/usr/bin/ssh",
        *(["-tt"] if tty else []),
        "-i",
        str(STATE_DIR / "id_ed25519"),
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        f"UserKnownHostsFile={STATE_DIR / 'known_hosts'}",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
        f"{GUEST_USER}@{GUEST_IP}",
        *remote,
    ]


def verify_client_state() -> None:
    state, uid_text = user_state()
    uid = int(uid_text)
    if state.is_symlink() or not state.is_dir() or state.stat().st_uid != uid:
        stop("dedicated SSH state directory missing or changed")
    if stat.S_IMODE(state.stat().st_mode) != 0o700:
        stop("dedicated SSH state directory mode changed")
    for path, mode in ((state / "id_ed25519", 0o600), (state / "known_hosts", 0o600)):
        if path.is_symlink() or not path.is_file() or path.stat().st_uid != uid:
            stop(f"dedicated SSH file missing or changed: {path}")
        if stat.S_IMODE(path.stat().st_mode) != mode:
            stop(f"dedicated SSH file mode changed: {path}")
    if not (state / "id_ed25519.pub").is_file():
        stop("dedicated SSH public key missing")
    keypair()
    parts = (state / "known_hosts").read_text().strip().split()
    if len(parts) != 3 or parts[:2] != [GUEST_IP, "ssh-ed25519"]:
        stop("dedicated known_hosts format changed")
    fingerprint = (
        base64.b64encode(hashlib.sha256(base64.b64decode(parts[2])).digest()).decode().rstrip("=")
    )
    if "SHA256:" + fingerprint != HOST_FINGERPRINT:
        stop("dedicated known_hosts fingerprint mismatch")


def stage() -> None:
    verify_client_state()
    package = HOST_BASE / "bundle.tar"
    trusted(package, 0o644)
    command = [
        "/usr/bin/scp",
        "-i",
        str(STATE_DIR / "id_ed25519"),
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        f"UserKnownHostsFile={STATE_DIR / 'known_hosts'}",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "BatchMode=yes",
        str(package),
        f"{GUEST_USER}@{GUEST_IP}:{GUEST_ARCHIVE}",
    ]
    subprocess.run(command, check=True)
    subprocess.run(
        ssh_command(
            "sudo",
            "-n",
            "/usr/bin/python3",
            "-I",
            str(GUEST_BASE / "access.py"),
            "guest",
            "install-bundle",
        ),
        check=True,
    )


def run_guest(action: str) -> None:
    if action not in GUEST_OPS:
        stop("guest operation denied")
    private_prompt = action in ("boot-enroll", "boot-fallback", "deepseek-key", "telegram")
    subprocess.run(
        ssh_command(
            "sudo",
            "-n",
            "/usr/bin/python3",
            "-I",
            str(GUEST_BASE / "access.py"),
            "guest",
            action,
            tty=private_prompt,
        ),
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("check", "install", "start-install", "host", "guest", "stage", "run")
    )
    parser.add_argument("action", nargs="?")
    args = parser.parse_args()
    if args.mode in ("host", "guest", "run"):
        if args.action not in (HOST_OPS if args.mode == "host" else GUEST_OPS):
            parser.error("unknown or missing fixed operation")
    elif args.action is not None:
        parser.error("this mode takes no operation")
    if args.mode == "check":
        check()
    elif args.mode == "install":
        install()
    elif args.mode == "start-install":
        start_install()
    elif args.mode == "host":
        host(args.action)
    elif args.mode == "guest":
        guest(args.action)
    elif args.mode == "stage":
        stage()
    else:
        run_guest(args.action)


if __name__ == "__main__":
    try:
        main()
    except (
        OSError,
        RuntimeError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        ValueError,
        ElementTree.ParseError,
    ) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
