"""Materialize the provider .env overlay without placing its secret in argv or logs."""

import os
from pathlib import Path
import pwd
import subprocess
import tempfile


def channel_environment(account):
    # User-controlled paths must never be read with root authority. O_NOFOLLOW and
    # a regular-file/size check also reject symlinks, FIFOs and oversized files.
    script = """import os,stat,sys
try:
    fd=os.open('.env',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
except FileNotFoundError:
    raise SystemExit(0)
with os.fdopen(fd,'rb') as stream:
    info=os.fstat(stream.fileno())
    if not stat.S_ISREG(info.st_mode) or info.st_size>131072: raise SystemExit(78)
    raw=stream.read(131073)
    if len(raw)>131072: raise SystemExit(78)
    sys.stdout.buffer.write(raw)
"""
    result = subprocess.run(["runuser", "-u", "hermes", "--", "env", "HOME=/home/hermes",
                             "XDG_RUNTIME_DIR=/run/user/" + str(account.pw_uid),
                             "podman", "unshare", "--", "env", "--chdir=/home/hermes/data",
                             "setpriv", "--reuid=10000", "--regid=10000",
                             "--clear-groups", "python3", "-c", script],
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            check=True, timeout=30)
    return result.stdout.decode().splitlines()


def main():
    if os.geteuid() != 0:
        return 77
    credential = Path(os.environ["CREDENTIALS_DIRECTORY"]) / "openai-api"
    key = credential.read_text().strip()
    if not key or any(c in key for c in "\n\r\x00"):
        return 78
    # Preserve channel settings; never copy the previous provider key into the new overlay.
    account = pwd.getpwnam("hermes")
    lines = channel_environment(account)
    lines = [line for line in lines if line.split("=", 1)[0].strip() not in ("OPENAI_API_KEY", "OPENAI_BASE_URL")]
    lines.append("OPENAI_API_KEY=" + key)
    lines.append("OPENAI_BASE_URL=https://api.openai.com/v1")
    destination = Path("/run/hermes-secrets")
    if destination.is_symlink():
        return 78
    destination.mkdir(mode=0o711, exist_ok=True)
    os.chmod(destination, 0o711)
    fd, name = tempfile.mkstemp(dir=destination, prefix=".provider-")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write("\n".join(lines) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(name, account.pw_uid, account.pw_gid)
        for command in (["runuser", "-u", "hermes", "--", "podman", "unshare", "chown", "10000:10000", name],
                        ["chcon", "system_u:object_r:container_file_t:s0", name]):
            subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=True, timeout=30)
        os.replace(name, destination / "provider.env")
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        raise SystemExit(78) from None
