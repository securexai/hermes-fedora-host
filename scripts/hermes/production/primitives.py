"""Production fail-closed primitives; errors never contain subprocess output."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path


class Refused(RuntimeError):
    pass


_LOCKS = ContextVar("production_locks", default=())


def supervised_run(argv, *, timeout=None, **kwargs):
    """Run commands under a lock-owning subreaper when inside a transaction."""
    locks = _LOCKS.get()
    if not locks:
        return subprocess.run(argv, timeout=timeout, **kwargs)
    command = [
        sys.executable,
        "-I",
        str(Path(__file__).with_name("writer_guard.py")),
        str(timeout or 0),
        ",".join(map(str, locks)),
        *argv,
    ]
    data = kwargs.pop("input", None)
    if data is not None:
        kwargs["stdin"] = subprocess.PIPE
    if kwargs.pop("capture_output", False):
        kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    check = kwargs.pop("check", False)
    # No parent-side timeout/kill: killing the guard would drop serialization
    # while a detached writer remains alive. The guard enforces the deadline.
    with subprocess.Popen(command, pass_fds=locks, start_new_session=True, **kwargs) as process:
        try:
            stdout, stderr = process.communicate(data)
        except BaseException:
            process.communicate()  # Drain pipes and wait for descendants after cancellation.
            raise
        result = subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
    if check:
        result.check_returncode()
    return result


def require(condition, reason):
    if not condition:
        raise Refused(reason)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def is_sha(value):
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate-json-field")
            result[key] = value
        return result

    try:
        return json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError) as exc:
        raise Refused("invalid-json") from exc


def regular(path, *, owner=None, private=False):
    path = Path(path)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "unsafe-file-type")
    require(not info.st_mode & (0o077 if private else 0o022), "unsafe-file-mode")
    if owner is not None:
        require(info.st_uid == owner, "unsafe-file-owner")
    for parent in path.absolute().parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode), "unsafe-parent-type")
        if owner == 0:
            require(info.st_uid == 0 and not info.st_mode & 0o022, "unsafe-parent-owner-mode")
    return path


def read_json(path, *, owner=None):
    path = regular(path, owner=owner)
    require(path.stat().st_size <= 1024 * 1024, "metadata-too-large")
    return decode(path.read_bytes())


def run(argv, *, data=None, timeout=120, check=True, env=None, cwd=None):
    clean = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8"}
    if env:
        clean.update(env)
    try:
        result = supervised_run(
            argv, input=data, capture_output=True, timeout=timeout, env=clean, cwd=cwd
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise Refused("command-unavailable-or-timeout") from exc
    if check:
        require(result.returncode == 0, "command-failed:" + Path(argv[0]).name)
    return result


def atomic(path, content, mode=0o600):
    path = Path(path)
    if path.exists() or path.is_symlink():
        regular(path)
        if path.read_bytes() == content and stat.S_IMODE(path.stat().st_mode) == mode:
            return False
    fd, temporary = tempfile.mkstemp(prefix=".hermes-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return True


def protected_directory(path, mode=0o700, *, parents=False, owner=0):
    """Establish exact modes despite umask, without repairing unsafe existing paths."""
    path = Path(path)
    if parents and not path.parent.exists():
        protected_directory(path.parent, mode, parents=True, owner=owner)
    if path.exists() or path.is_symlink():
        info = path.lstat()
        require(
            stat.S_ISDIR(info.st_mode)
            and info.st_uid == owner
            and stat.S_IMODE(info.st_mode) == mode,
            "unsafe-managed-directory",
        )
    else:
        path.mkdir(mode=mode)
        # mkdir's mode is filtered by the private CLI umask. Only our newly
        # created directory gets an explicit public mode; never relax umask.
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            require(os.fstat(fd).st_uid == owner, "unsafe-managed-directory")
            os.fchmod(fd, mode)
            os.fsync(fd)
        finally:
            os.close(fd)
        durable_directory(path.parent)


def public_directory(path, *, owner=0, boundary=Path("/")):
    """Create public code/unit paths and validate every existing ancestor."""
    path = Path(path)
    for parent in path.absolute().parents:
        if not parent.is_relative_to(boundary):
            break
        if not parent.exists() and not parent.is_symlink():
            continue
        info = parent.lstat()
        require(
            stat.S_ISDIR(info.st_mode)
            and info.st_uid == owner
            and not info.st_mode & 0o022
            and info.st_mode & 0o005 == 0o005,
            "unsafe-public-parent",
        )
    protected_directory(path, 0o755, parents=True, owner=owner)


def durable_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def durable_tree(root):
    root = Path(root)
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    for path in sorted(
        (p for p in root.rglob("*") if p.is_dir() and not p.is_symlink()), reverse=True
    ):
        durable_directory(path)
    durable_directory(root)
    durable_directory(root.parent)


@contextmanager
def lock(path):
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        info = os.fstat(fd)
        require(info.st_uid == os.geteuid() and info.st_nlink == 1, "unsafe-lock")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Refused("operation-busy") from exc
        token = _LOCKS.set((*_LOCKS.get(), fd))
        try:
            yield
        finally:
            _LOCKS.reset(token)
    finally:
        os.close(fd)
