"""Shared, secret-free protocol and filesystem primitives."""

import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import signal
import tempfile


class Failure(Exception):
    def __init__(self, code, reason):
        super().__init__(reason)
        self.code = code
        self.reason = reason


def require(condition, reason, code=78):
    if not condition:
        raise Failure(code, reason)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate-json-key", 64)
        result[key] = value
    return result


def decode(raw):
    try:
        return json.loads(raw, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError):
        raise Failure(64, "invalid-json") from None


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def digest(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def protected_file(path, owner=None):
    path = Path(path)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode), "unsafe-file-type")
    require(not info.st_mode & 0o022, "writable-trust-file")
    if owner is not None:
        require(info.st_uid == owner, "wrong-file-owner")
        for parent in path.absolute().parents:
            info = parent.lstat()
            require(stat.S_ISDIR(info.st_mode) and info.st_uid == owner
                    and not info.st_mode & 0o022, "unsafe-trust-directory")
    return path


def atomic(path, data):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextlib.contextmanager
def lock(path):
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Failure(75, "target-busy") from None
        yield
    finally:
        os.close(fd)


def run(args, *, data=None, timeout=120, env=None, stdout=None):
    """Never echo command output: provider errors can contain credential material."""
    try:
        process = subprocess.Popen(args, stdin=subprocess.DEVNULL if data is None else subprocess.PIPE,
                                   stdout=stdout if stdout is not None else subprocess.PIPE,
                                   stderr=subprocess.PIPE, env=env, start_new_session=True)
    except OSError:
        raise Failure(69, "required-command-unavailable") from None
    try:
        output, _ = process.communicate(data, timeout=timeout)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
        raise Failure(69, "operation-timeout") from None
    require(process.returncode == 0, "operation-failed", 69)
    return output


def report(function):
    try:
        value = function()
        if value is not None:
            print(canonical(value).decode(), end="")
    except Failure as error:
        print(canonical({"ok": False, "error": error.reason}).decode(), end="")
        raise SystemExit(error.code) from None
    except (OSError, ValueError, KeyError, TypeError):
        print('{"ok":false,"error":"invalid-or-unavailable-input"}')
        raise SystemExit(78) from None
