"""Authenticate a release before extracting regular files to a private directory.

The archive is copied into private storage first. No tar extraction API is used.
Signatures cover the exact manifest bytes; every payload file is length/hash bound.
"""

import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import tarfile
import tempfile
import time

from common import Failure, canonical, decode, protected_file, require, run

NAMESPACE = "hermes-release@ai.lab.local"
SCHEMA = "hermes-release-v2"
MAX_ARCHIVE = 8 * 1024**3
MAX_METADATA = 1024 * 1024
GATES = {"inference", "restore", "credential_revocation", "data_purge", "vm_destroyed",
         "boot", "runtime", "package_replay", "vulnerability_scan"}
FIELDS = {"schema", "release_id", "issued_at", "expires_at", "image", "provider", "model",
          "host", "baseline_sha256", "files", "evidence", "transaction", "boot_artifact"}


def sha(value):
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def safe_name(name):
    require(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_./+^-]+", name), "unsafe-archive-path")
    path = PurePosixPath(name)
    require(not path.is_absolute() and str(path) == name
            and all(part not in (".", "..") for part in path.parts), "unsafe-archive-path")
    require(name.startswith(("payload/", "packages/", "boot/", "evidence/")), "unexpected-archive-path")
    return name


def candidate_fingerprint(manifest):
    """Bind evidence to all tested inputs, excluding only evidence itself and signing timestamps."""
    value = {key: manifest[key] for key in ("release_id", "image", "provider", "model", "host",
                                          "baseline_sha256", "transaction", "boot_artifact")}
    value["files"] = {name: record for name, record in manifest["files"].items() if not name.startswith("evidence/")}
    return hashlib.sha256(canonical(value)).hexdigest()


def validate(manifest, *, now=None, host=None, bound=False):
    require(isinstance(manifest, dict) and set(manifest) == FIELDS, "invalid-release-fields")
    require(manifest["schema"] == SCHEMA, "unsigned-or-legacy-release")
    require(isinstance(manifest["release_id"], str)
            and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,95}", manifest["release_id"]), "invalid-release-id")
    issued, expires = manifest["issued_at"], manifest["expires_at"]
    require(type(issued) is int and type(expires) is int and 0 < expires - issued <= 86400,
            "invalid-release-window")
    now = int(time.time()) if now is None else now
    require(issued <= now and (bound or now <= expires), "expired-or-future-release")
    require(isinstance(manifest["image"], str) and re.fullmatch(
        r"docker.io/nousresearch/hermes-agent@sha256:[a-f0-9]{64}", manifest["image"]), "unpinned-image")
    require(manifest["provider"] == "openai-api", "unattended-provider-unsupported")
    require(isinstance(manifest["model"], str)
            and re.fullmatch(r"[A-Za-z0-9._:/-]+", manifest["model"]), "invalid-model")
    identity = manifest["host"]
    require(isinstance(identity, dict) and set(identity) == {"machine_id_sha256", "ssh_fingerprint"}
            and sha(identity["machine_id_sha256"])
            and isinstance(identity["ssh_fingerprint"], str)
            and re.fullmatch(r"SHA256:[A-Za-z0-9+/]{43}", identity["ssh_fingerprint"]), "invalid-host-binding")
    require(host is None or identity == host, "wrong-host")
    require(sha(manifest["baseline_sha256"]), "invalid-baseline")
    files = manifest["files"]
    require(isinstance(files, dict) and 1 <= len(files) <= 20000, "invalid-file-map")
    total = 0
    for name, record in files.items():
        safe_name(name)
        require(isinstance(record, dict) and set(record) == {"sha256", "size", "mode"}
                and sha(record["sha256"]) and type(record["size"]) is int
                and 0 <= record["size"] <= MAX_ARCHIVE and record["mode"] in (0o600, 0o644, 0o755),
                "invalid-file-record")
        total += record["size"]
    require(total <= MAX_ARCHIVE, "release-too-large")
    require("payload/vulnerability-policy.json" in files, "missing-vulnerability-policy")
    for field, prefix in (("transaction", "packages/"), ("boot_artifact", "boot/")):
        require(isinstance(manifest[field], str) and manifest[field].startswith(prefix)
                and manifest[field] in files, "missing-release-artifact")
    evidence = manifest["evidence"]
    require(isinstance(evidence, dict) and set(evidence) == GATES, "incomplete-certification")
    for gate, name in evidence.items():
        require(isinstance(name, str) and name.startswith("evidence/") and name in files,
                "missing-certification-evidence")
    return manifest


def members(archive):
    result = {}
    for member in archive:
        require(member.isfile() and not member.issparse() and not member.pax_headers,
                "unsafe-archive-member")
        require(member.name not in result and len(result) < 20002, "duplicate-or-excess-archive-member")
        require(0 <= member.size <= MAX_ARCHIVE, "archive-member-too-large")
        require(member.mode in (0o600, 0o644, 0o755), "unsafe-archive-mode")
        result[member.name] = member
    return result


def unpack(source, destination, signers, *, host=None, now=None, bound_digest=None, owner=None):
    """Destination must not exist; caller owns its non-writable parent directory.

    bound_digest is a previously authenticated manifest hash from root-owned state,
    not a caller-controlled flag. It permits resuming an already bound expired release.
    """
    destination = Path(destination)
    require(not destination.exists(), "release-destination-exists")
    protected_file(signers, owner)
    with tempfile.TemporaryDirectory(prefix=".verify-", dir=destination.parent) as work:
        copy = Path(work) / "archive.tar"
        with open(copy, "xb") as output:
            count = 0
            while chunk := source.read(1024 * 1024):
                count += len(chunk)
                require(count <= MAX_ARCHIVE, "archive-too-large")
                output.write(chunk)
        try:
            archive = tarfile.open(copy, "r:")
        except tarfile.TarError:
            raise Failure(64, "invalid-release-archive") from None
        with archive:
            listing = members(archive)
            require({"manifest.json", "manifest.sig"} <= set(listing), "missing-signature")
            for name in ("manifest.json", "manifest.sig"):
                require(listing[name].size <= MAX_METADATA, "metadata-too-large")
            raw = archive.extractfile(listing["manifest.json"]).read()
            signature = archive.extractfile(listing["manifest.sig"]).read()
            sigpath = Path(work) / "signature"
            sigpath.write_bytes(signature)
            run(["ssh-keygen", "-Y", "verify", "-f", str(signers), "-I", "hermes-release",
                 "-n", NAMESPACE, "-s", str(sigpath)], data=raw, timeout=30)
            fingerprint = hashlib.sha256(raw).hexdigest()
            manifest = validate(decode(raw), host=host, now=now, bound=fingerprint == bound_digest)
            require(set(listing) == set(manifest["files"]) | {"manifest.json", "manifest.sig"},
                    "unexpected-or-missing-artifact")
            payload = Path(work) / "verified"
            payload.mkdir(mode=0o700)
            for name, record in manifest["files"].items():
                member = listing[name]
                require(member.size == record["size"] and member.mode == record["mode"], "artifact-metadata-mismatch")
                target = payload / name
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                hasher = hashlib.sha256()
                with archive.extractfile(member) as input_file, open(target, "xb") as output:
                    while chunk := input_file.read(1024 * 1024):
                        hasher.update(chunk)
                        output.write(chunk)
                require(hasher.hexdigest() == record["sha256"], "artifact-hash-mismatch")
                target.chmod(record["mode"])
            for gate, name in manifest["evidence"].items():
                require(manifest["files"][name]["size"] <= MAX_METADATA, "evidence-too-large")
                evidence = decode((payload / name).read_bytes())
                require(isinstance(evidence, dict) and evidence.get("gate") == gate
                        and evidence.get("result") == "PASS"
                        and evidence.get("release_id") == manifest["release_id"]
                        and evidence.get("artifact_fingerprint") == candidate_fingerprint(manifest),
                        "failed-certification-evidence")
                if gate == "vulnerability_scan":
                    require(evidence.get("policy") == "advisory-denylist-v1"
                            and evidence.get("policy_sha256") == manifest["files"]["payload/vulnerability-policy.json"]["sha256"],
                            "vulnerability-policy-evidence-mismatch")
            (payload / "manifest.json").write_bytes(raw)
            (payload / "manifest.sig").write_bytes(signature)
            os.rename(payload, destination)
    return manifest, fingerprint
