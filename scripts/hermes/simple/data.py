"""Application archive operations, executed ONLY in the rootless user namespace."""
import io
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile

LIMIT = 512 * 1024 * 1024


def private(name):
    # Provider/channel credentials stay in place on restore, outside snapshots.
    return any(part.startswith((".env", "auth.json", "credentials")) for part in PurePosixPath(name).parts)


def members(archive):
    records = archive.getmembers()
    total = 0
    seen = set()
    for entry in records:
        path = PurePosixPath(entry.name)
        if path.is_absolute() or ".." in path.parts or private(entry.name):
            raise ValueError("unsafe-archive-path")
        if not (entry.isdir() or entry.isfile()) or entry.name in seen:
            raise ValueError("unsafe-archive-type")
        seen.add(entry.name)
        total += entry.size
        if total > LIMIT:
            raise ValueError("archive-too-large")
    return records


def snapshot(root):
    # Explicitly refuse links/special files, rather than following data-controlled
    # paths or generating an archive the restore path cannot safely consume.
    with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as archive:
        total = 0
        for path in sorted(root.rglob("*")):
            name = path.relative_to(root).as_posix()
            if private(name):
                continue
            if path.is_symlink() or not (path.is_dir() or path.is_file()):
                raise ValueError("unsupported-application-file")
            if path.is_file():
                total += path.stat().st_size
            if total > LIMIT:
                raise ValueError("backup-too-large")
            archive.add(path, arcname=name, recursive=False)


def restore(root, raw):
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        entries = members(archive)  # Validate all entries before deleting anything.
        # Credential locations are protected recursively, including nested files.
        for path in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            relative = path.relative_to(root).as_posix()
            if private(relative):
                continue
            if path.is_dir() and not path.is_symlink():
                try:
                    path.rmdir()
                except OSError:
                    pass
            else:
                path.unlink()
        for entry in entries:
            destination = root / entry.name
            if any(p.is_symlink() for p in (destination, *destination.parents)):
                raise ValueError("restore-symlink")
            destination.parent.mkdir(parents=True, exist_ok=True)
            if entry.isdir():
                destination.mkdir(exist_ok=True)
            else:
                with archive.extractfile(entry) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)
            os.chmod(destination, entry.mode & 0o700)
            os.chown(destination, 10000, 10000)


def main():
    root = Path("/home/hermes/data")
    if root.is_symlink() or not root.is_dir():
        raise ValueError("invalid-data-root")
    if sys.argv[1] == "snapshot":
        snapshot(root)
    elif sys.argv[1] == "restore":
        raw = sys.stdin.buffer.read(LIMIT + 16 * 1024 * 1024 + 1)
        if len(raw) > LIMIT + 16 * 1024 * 1024:
            raise ValueError("archive-too-large")
        restore(root, raw)
    else:
        raise ValueError("unsupported-action")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, tarfile.TarError):
        raise SystemExit(78) from None
