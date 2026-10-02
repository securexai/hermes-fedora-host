"""Locally commissioned immutable receivers; releases never install executable policy."""

from pathlib import Path

from .primitives import (
    atomic,
    canonical,
    digest,
    durable_tree,
    is_sha,
    public_directory,
    read_json,
    regular,
    require,
    sha,
)

INSTALL = Path("/usr/local/libexec/hermes-production")
PROTOCOL = 1
TOP = {"productionctl.py", "production-launcher.py", "lab_profile.py"}


def file_map(source):
    source = Path(source)
    names = TOP | {str(p.relative_to(source)) for p in (source / "production").glob("*.py")}
    return {name: sha(regular(source / name)) for name in sorted(names)}


def descriptor(files):
    return {"protocol": PROTOCOL, "files": files}


def expected(manifest):
    files = {
        name.removeprefix("source/"): row["sha256"]
        for name, row in manifest["files"].items()
        if name.removeprefix("source/") in TOP
        or (name.startswith("source/production/") and name.endswith(".py"))
    }
    require(TOP <= files.keys() and "production/receivers.py" in files, "missing-receiver-files")
    return descriptor(files)


def validate(identity, wanted=None, *, install=None):
    require(is_sha(identity), "invalid-receiver-identity")
    root = (INSTALL if install is None else Path(install)) / "receivers" / identity
    info = read_json(root / "receiver.json", owner=0)
    require(
        set(info) == {"protocol", "files"}
        and info["protocol"] == PROTOCOL
        and digest(info) == identity
        and (wanted is None or info == wanted),
        "receiver-descriptor-mismatch",
    )
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if not p.is_dir()}
    require(
        actual == set(info["files"]) | {"receiver.json"}
        and not any(p.is_symlink() for p in root.rglob("*")),
        "unexpected-receiver-file",
    )
    for name, checksum in info["files"].items():
        require(sha(regular(root / name, owner=0)) == checksum, "receiver-hash-mismatch")
    return root


def for_release(manifest):
    info = expected(manifest)
    identity = digest(info)
    require(
        (INSTALL / "receivers" / identity).exists(), "receiver-version-requires-private-bootstrap"
    )
    return validate(identity, info)


def install(source):
    """Private bootstrap stages a new receiver without replacing an active version."""
    source = Path(source)
    info = descriptor(file_map(source))
    identity = digest(info)
    public_directory(INSTALL)
    public_directory(INSTALL / "receivers")
    launcher = INSTALL / "productionctl.py"
    content = regular(source / "production-launcher.py").read_bytes()
    if launcher.exists():
        require(
            regular(launcher, owner=0).read_bytes() == content,
            "launcher-protocol-change-requires-migration",
        )
    else:
        atomic(launcher, content, 0o755)
    target = INSTALL / "receivers" / identity
    if target.exists():
        validate(identity, info)
    else:
        import os
        import tempfile

        with tempfile.TemporaryDirectory(prefix=".stage-", dir=INSTALL / "receivers") as temporary:
            os.chmod(temporary, 0o755)  # Only public, non-secret receiver source is staged here.
            stage = Path(temporary) / "receiver"
            public_directory(stage)
            public_directory(stage / "production")
            for name in info["files"]:
                atomic(
                    stage / name,
                    regular(source / name).read_bytes(),
                    0o755 if name in TOP - {"lab_profile.py"} else 0o644,
                )
            atomic(stage / "receiver.json", canonical(info), 0o644)
            require(file_map(stage) == info["files"], "receiver-source-changed-during-bootstrap")
            durable_tree(stage)
            os.rename(stage, target)
            from .primitives import durable_directory

            durable_directory(target.parent)
    # Initialization only. Application transactions own all subsequent selection.
    if not (INSTALL / "controller.json").exists():
        select(identity)
    return identity


def select(identity):
    validate(identity)
    atomic(INSTALL / "controller.json", canonical({"receiver": identity}), 0o644)


def running_matches(manifest):
    source = Path(__file__).resolve().parents[1]
    return descriptor(file_map(source)) == expected(manifest)
