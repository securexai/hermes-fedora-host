#!/usr/bin/python3 -I
"""Fixed protocol-1 launcher. Private bootstrap cannot overwrite this trust boundary."""

import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path


def checked(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid or info.st_mode & 0o022:
        raise ValueError("unsafe receiver file")
    for parent in path.absolute().parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid or info.st_mode & 0o022:
            raise ValueError("unsafe receiver parent")
    return path.read_bytes()


def selected(install):
    selection = json.loads(checked(install / "controller.json"))
    if set(selection) != {"receiver"} or not re.fullmatch(r"[a-f0-9]{64}", selection["receiver"]):
        raise ValueError("invalid selection")
    root = install / "receivers" / selection["receiver"]
    info = json.loads(checked(root / "receiver.json"))
    encoded = (json.dumps(info, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if (
        set(info) != {"protocol", "files"}
        or info["protocol"] != 1
        or hashlib.sha256(encoded).hexdigest() != selection["receiver"]
        or "productionctl.py" not in info["files"]
    ):
        raise ValueError("invalid descriptor")
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if not p.is_dir()}
    if actual != set(info["files"]) | {"receiver.json"} or any(
        p.is_symlink() for p in root.rglob("*")
    ):
        raise ValueError("unexpected receiver file")
    for name, checksum in info["files"].items():
        if name.startswith("/") or ".." in Path(name).parts:
            raise ValueError("invalid receiver path")
        if hashlib.sha256(checked(root / name)).hexdigest() != checksum:
            raise ValueError("receiver hash mismatch")
    return root / "productionctl.py"


if __name__ == "__main__":
    os.umask(0o077)
    try:
        entry = selected(Path(__file__).absolute().parent)
        os.execv("/usr/bin/python3", ["/usr/bin/python3", "-I", str(entry), *sys.argv[1:]])
    except Exception:
        sys.exit("STOP: invalid-installed-receiver")
