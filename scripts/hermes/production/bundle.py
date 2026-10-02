"""Independent production signature namespace and regular-file-only release archives."""

from __future__ import annotations

import os
import re
import shutil
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

from .primitives import (
    canonical,
    decode,
    digest,
    durable_directory,
    durable_tree,
    is_sha,
    read_json,
    regular,
    require,
    run,
    sha,
)

NAMESPACE = "hermes-production-v1"
SIGNER = "hermes-production"
MAX_BYTES = 32 * 1024**3
GATES = {"repository", "installation", "runtime", "repeatability", "restore", "boot", "application"}
ROOT = Path(__file__).resolve().parents[3]


def name_ok(name):
    require(isinstance(name, str), "unsafe-archive-path")
    path = PurePosixPath(name)
    require(
        isinstance(name, str)
        and re.fullmatch(r"[A-Za-z0-9_./-]+", name)
        and not path.is_absolute()
        and str(path) == name
        and all(part not in (".", "..") for part in path.parts),
        "unsafe-archive-path",
    )


def identity(manifest):
    return digest({key: manifest[key] for key in ("schema", "profile", "images", "files")})


def validate(manifest, *, production=False):
    require(
        isinstance(manifest, dict)
        and set(manifest) == {"schema", "profile", "images", "files", "qualification", "stage"},
        "invalid-release-fields",
    )
    require(manifest["schema"] == NAMESPACE, "wrong-release-profile")
    from lab_profile import validate as validate_profile

    validate_profile(manifest["profile"])
    require(manifest["profile"]["model"] == "deepseek-flash", "unqualified-model")
    require(set(manifest["images"]) == {"gateway", "worker"}, "missing-image-identities")
    for value in manifest["images"].values():
        require(
            isinstance(value, str) and re.fullmatch(r"sha256:[a-f0-9]{64}", value),
            "invalid-image-id",
        )
    files = manifest["files"]
    require(isinstance(files, dict) and 4 <= len(files) <= 1000, "invalid-file-map")
    total = 0
    for name, record in files.items():
        name_ok(name)
        require(name.startswith(("source/", "images/", "evidence/")), "unexpected-file")
        require(
            isinstance(record, dict)
            and set(record) == {"sha256", "size", "mode"}
            and is_sha(record["sha256"])
            and type(record["size"]) is int
            and 0 <= record["size"] <= MAX_BYTES
            and record["mode"] in (0o644, 0o755),
            "invalid-file-record",
        )
        total += record["size"]
    require(total <= MAX_BYTES, "release-too-large")
    require(
        {
            "images/gateway.oci",
            "images/worker.oci",
            "source/profile-deploy.py",
            "source/lab_profile.py",
            "source/manual/config/profile-contract.yaml",
            "evidence/packages.json",
        }
        <= set(files),
        "incomplete-release",
    )
    require(manifest["stage"] in ("candidate", "qualified"), "invalid-stage")
    q = manifest["qualification"]
    require(
        isinstance(q, dict) and set(q) == {"artifact_sha256", "gates", "report_sha256", "report"},
        "invalid-qualification",
    )
    require(q["artifact_sha256"] == identity(manifest), "stale-qualification")
    require(
        isinstance(q["gates"], dict)
        and set(q["gates"]) == GATES
        and all(
            value in ("PASS", "FAIL", "BLOCKED", "NOT_RUN", "STALE")
            for value in q["gates"].values()
        ),
        "invalid-qualification-gates",
    )
    require(q["report_sha256"] is None or is_sha(q["report_sha256"]), "invalid-report-hash")
    if q["report"] is not None:
        require(
            digest(q["report"]) == q["report_sha256"]
            and q["report"]["artifact_sha256"] == identity(manifest)
            and q["report"]["gates"] == q["gates"],
            "qualification-report-mismatch",
        )
    if production or manifest["stage"] == "qualified":
        require(
            manifest["stage"] == "qualified"
            and set(q["gates"].values()) == {"PASS"}
            and is_sha(q["report_sha256"])
            and q["report"] is not None,
            "release-not-qualified",
        )
    return manifest


def build(artifacts, output, key, *, evidence=None):
    """Sign current maintained source + retained images; never include instance state."""
    artifacts, output, key = Path(artifacts), Path(output), regular(key)
    with key.open("rb") as stream:
        public_key = stream.read(12).startswith(b"ssh-ed25519 ")
    if not public_key:
        regular(key, private=True)
    require(not output.exists(), "release-output-exists")
    cached = read_json(artifacts / "manifest.json")
    profile = read_json(ROOT / "scripts/hermes/lab-profiles/baseline.json")
    require(cached["gateway_ref"] == profile["gateway_image"], "candidate-image-mismatch")
    files = {}
    base = ROOT / "scripts/hermes"
    selected = [
        base / "profile-deploy.py",
        base / "lab_profile.py",
        base / "productionctl.py",
        base / "production-launcher.py",
    ]
    selected.extend((base / "production").glob("*.py"))
    for area in ("manual/config", "manual/gateway", "manual/worker", "manual/quadlets"):
        selected.extend(p for p in (base / area).rglob("*") if p.is_file())
    selected.append(base / "manual/manifest.yaml")
    for path in selected:
        require(not path.is_symlink(), "source-symlink")
        files["source/" + str(path.relative_to(base))] = path
    files["source/PRODUCTION_RUNBOOK.md"] = ROOT / "docs/HERMES_PRODUCTION_DEPLOYMENT.md"
    for component in ("gateway", "worker"):
        path = regular(artifacts / (component + ".oci"))
        require(sha(path) == cached["files"][path.name], "retained-image-corrupt")
        files["images/" + path.name] = path
    with tempfile.TemporaryDirectory(prefix="hermes-release-") as temporary:
        temp = Path(temporary)
        packages = temp / "packages.json"
        require(isinstance(cached.get("packages"), (list, dict, str)), "missing-package-inventory")
        packages.write_bytes(canonical(cached["packages"]))
        files["evidence/packages.json"] = packages
        manifest = {
            "schema": NAMESPACE,
            "profile": profile,
            "images": {c: cached[c + "_id"] for c in ("gateway", "worker")},
            "files": {
                name: {
                    "sha256": sha(path),
                    "size": path.stat().st_size,
                    "mode": 0o755 if os.access(path, os.X_OK) else 0o644,
                }
                for name, path in sorted(files.items())
            },
            "stage": "candidate",
            "qualification": {},
        }
        manifest["qualification"] = {
            "artifact_sha256": identity(manifest),
            "gates": dict.fromkeys(sorted(GATES), "NOT_RUN"),
            "report_sha256": None,
            "report": None,
        }
        if evidence:
            report = read_json(evidence)
            require(
                set(report) == {"artifact_sha256", "gates", "reports"}
                and report["artifact_sha256"] == identity(manifest),
                "stale-qualification",
            )
            require(
                isinstance(report["reports"], dict)
                and set(report["reports"]) == GATES
                and all(is_sha(v) for v in report["reports"].values()),
                "missing-gate-reports",
            )
            manifest["qualification"].update(
                gates=report["gates"], report_sha256=digest(report), report=report
            )
            manifest["stage"] = "qualified"
        validate(manifest)
        metadata = temp / "manifest.json"
        metadata.write_bytes(canonical(manifest))
        agent = (
            {"SSH_AUTH_SOCK": os.environ["SSH_AUTH_SOCK"]}
            if os.environ.get("SSH_AUTH_SOCK")
            else None
        )
        run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", NAMESPACE, str(metadata)], env=agent)
        files.update({"manifest.json": metadata, "manifest.sig": temp / "manifest.json.sig"})
        fd, staging = tempfile.mkstemp(prefix=".release-", dir=output.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                    for name, path in sorted(files.items()):
                        record = manifest["files"].get(
                            name, {"mode": 0o644, "size": path.stat().st_size}
                        )
                        item = tarfile.TarInfo(name)
                        item.size, item.mode = record["size"], record["mode"]
                        with path.open("rb") as source:
                            archive.addfile(item, source)
                stream.flush()
                os.fsync(stream.fileno())
            for name, record in manifest["files"].items():
                require(sha(files[name]) == record["sha256"], "source-changed-during-build")
            os.link(staging, output)  # Atomic publication, no overwrite of an existing release.
        finally:
            Path(staging).unlink(missing_ok=True)
    return {
        "stage": manifest["stage"],
        "artifact_sha256": identity(manifest),
        "sha256": sha(output),
    }


def unpack(source, destination, signers, *, production=False, owner=None, max_bytes=MAX_BYTES):
    """Authenticate copied bytes and all members before publishing; reject links/devices."""
    destination = Path(destination)
    require(not destination.exists(), "release-destination-exists")
    regular(signers, owner=owner)
    with tempfile.TemporaryDirectory(prefix=".verify-", dir=destination.parent) as temporary:
        temp = Path(temporary)
        archive_file = temp / "release.tar"
        total = 0
        with archive_file.open("xb") as output:
            while chunk := source.read(1024 * 1024):
                total += len(chunk)
                require(total <= min(MAX_BYTES, max_bytes), "release-too-large")
                output.write(chunk)
        with tarfile.open(archive_file, "r:") as archive:
            members = {}
            for item in archive:
                name_ok(item.name)
                require(
                    item.isfile()
                    and not item.issparse()
                    and not item.pax_headers
                    and item.name not in members
                    and len(members) < 1002
                    and item.mode in (0o644, 0o755)
                    and 0 <= item.size <= MAX_BYTES,
                    "unsafe-archive-member",
                )
                members[item.name] = item
            require({"manifest.json", "manifest.sig"} <= members.keys(), "unsigned-release")
            require(
                all(members[n].size <= 1024 * 1024 for n in ("manifest.json", "manifest.sig")),
                "metadata-too-large",
            )
            raw = archive.extractfile(members["manifest.json"]).read()
            signature = archive.extractfile(members["manifest.sig"]).read()
            (temp / "signature").write_bytes(signature)
            run(
                [
                    "ssh-keygen",
                    "-Y",
                    "verify",
                    "-f",
                    str(signers),
                    "-I",
                    SIGNER,
                    "-n",
                    NAMESPACE,
                    "-s",
                    str(temp / "signature"),
                ],
                data=raw,
            )
            manifest = validate(decode(raw), production=production)
            require(
                set(members) == set(manifest["files"]) | {"manifest.json", "manifest.sig"},
                "unexpected-or-missing-file",
            )
            payload = temp / "payload"
            payload.mkdir(mode=0o700)
            for name, record in manifest["files"].items():
                item = members[name]
                require(
                    item.size == record["size"] and item.mode == record["mode"],
                    "file-metadata-mismatch",
                )
                path = payload / name
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                with path.open("xb") as output, archive.extractfile(item) as stream:
                    shutil.copyfileobj(stream, output, 1024 * 1024)
                require(sha(path) == record["sha256"], "artifact-hash-mismatch")
                path.chmod(record["mode"])
            (payload / "manifest.json").write_bytes(raw)
            (payload / "manifest.sig").write_bytes(signature)
            durable_tree(payload)
            os.rename(payload, destination)
            durable_directory(destination.parent)
    return manifest
