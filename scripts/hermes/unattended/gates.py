"""Release preparation gates; none of these functions certify a VM by themselves."""

from datetime import date
import hashlib
import os
from pathlib import Path
import re
import selectors
import subprocess
import tempfile
import time

from common import Failure, decode, digest, protected_file, require, run
from transaction import normalize, validate_bundle


def check_vulnerabilities(report, denylist, image, today=None):
    """Severity is advisory; explicitly assessed ID/package matches block all image versions."""
    today = date.today() if today is None else today
    require(isinstance(report, dict) and isinstance(report.get("Results"), list)
            and report["Results"], "missing-vulnerability-results")
    require(isinstance(denylist, list), "invalid-denylist")
    denied = set()
    for item in denylist:
        require(isinstance(item, dict) and set(item) == {"id", "package", "reason", "owner", "assessed_at"},
                "invalid-denylist-entry")
        require(all(isinstance(item[key], str) and item[key].strip() for key in item), "invalid-denylist-entry")
        try:
            assessed = date.fromisoformat(item["assessed_at"])
        except (ValueError, TypeError):
            raise Failure(78, "invalid-denylist-date") from None
        require(assessed <= today, "future-denylist-assessment")
        denied.add((item["id"], item["package"]))
    counts = {severity: 0 for severity in ("UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL")}
    for result in report["Results"]:
        require(isinstance(result, dict), "invalid-vulnerability-result")
        findings = result.get("Vulnerabilities")
        require(findings is None or isinstance(findings, list), "invalid-vulnerability-list")
        for vulnerability in findings or []:
            require(isinstance(vulnerability, dict), "invalid-vulnerability-finding")
            severity = vulnerability.get("Severity")
            require(severity in counts, "invalid-vulnerability-severity")
            identifier, package = vulnerability.get("VulnerabilityID"), vulnerability.get("PkgName")
            require(isinstance(identifier, str) and identifier and isinstance(package, str) and package,
                    "invalid-vulnerability-finding")
            counts[severity] += 1
            require((identifier, package) not in denied and (identifier, "*") not in denied,
                    "denied-vulnerability")
    return {"result": "PASS", "gate": "vulnerability_scan", "policy": "advisory-denylist-v1",
            "findings": counts, "advisory": any(counts.values())}


def scan_image(image, denylist):
    require(re.fullmatch(r"docker.io/nousresearch/hermes-agent@sha256:[a-f0-9]{64}", image), "unpinned-image")
    environment = {key: value for key, value in os.environ.items() if not key.startswith("TRIVY_")}
    # Use private scratch space and no personal registry credentials or ambient cache.
    with tempfile.TemporaryDirectory(prefix="hermes-scan-") as scratch:
        registry = Path(scratch) / "registry"
        registry.mkdir(mode=0o700)
        environment["DOCKER_CONFIG"] = str(registry)
        raw = run(["trivy", "image", "--quiet", "--format", "json", "--scanners", "vuln",
                   "--cache-dir", str(Path(scratch) / "cache"),
                   "--config", "/dev/null", "--image-src", "remote", "--ignore-unfixed=false",
                   "--ignorefile", "/dev/null", "--timeout", "15m", image], timeout=960, env=environment)
    report = decode(raw)
    # Trivy reports Docker Hub names without the registry prefix. Accept only that
    # exact equivalent, never a digest belonging to a different repository.
    names = report.get("Metadata", {}).get("RepoDigests", [])
    require(image in names or image.removeprefix("docker.io/") in names, "scan-image-mismatch")
    return check_vulnerabilities(report, denylist, image)


def package_baseline():
    raw = run(["rpm", "-qa", "--qf", "%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\n"])
    return hashlib.sha256(b"".join(sorted(raw.splitlines(keepends=True)))).hexdigest()


def verify_packages(directory, expected_baseline):
    directory = Path(directory)
    require(package_baseline() == expected_baseline, "package-baseline-mismatch")
    expected_packages = validate_bundle(directory, expected_baseline)
    protected_file(directory / "transaction.json", 0)
    packages = sorted(directory.rglob("*.rpm"))
    require(packages, "missing-certified-rpms")
    for package in packages:
        protected_file(package, 0)
        result = run(["rpmkeys", "--checksig", str(package)])
        require(b"signatures OK" in result and b"NOT OK" not in result, "rpm-signature-unverified")
        identity = run(["rpm", "-qp", "--qf", "%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}", str(package)])
        require(normalize(identity.decode()) == expected_packages[str(package.relative_to(directory))],
                "stored-rpm-identity-mismatch")
    return {"stage": "stored-packages-verified", "rpm_count": len(packages)}


def replay_packages(directory, expected_baseline, boot_entry=None):
    verify_packages(directory, expected_baseline)
    # DNF5 replay has no --offline option. Use systemd's offline-update target
    # to run strict replay, with signatures rechecked before any RPM scriptlet.
    from offline import stage
    return stage(directory, expected_baseline, boot_entry=boot_entry)


def command_digest(args, timeout=900):
    """Hash restored plaintext in memory without logging or persisting it."""
    process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    hasher = hashlib.sha256()
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                require(remaining > 0, "restore-timeout", 69)
                require(selector.select(remaining), "restore-timeout", 69)
                chunk = os.read(process.stdout.fileno(), 1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)
        require(process.wait(timeout=max(1, deadline - time.monotonic())) == 0, "restore-failed", 69)
        return hasher.hexdigest()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()


def backup_snapshot(source, config, release_id):
    """Encrypt a quiesced snapshot, then prove a byte-identical restore before use.

    Caller must keep the application quiesced and source immutable until this returns.
    Archive ownership and semantic restoration are separately checked in the VM gate.
    """
    source = protected_file(source)
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", release_id), "invalid-release-id")
    protected_file(config["backup_password_file"])
    base = ["restic", "--no-cache", "--repo", config["backup_repository"], "--password-file", config["backup_password_file"]]
    before = digest(source)
    raw = run(base + ["backup", "--json", "--tag", "pre-change",
                      "--tag", "release:" + release_id, "--", str(source)], timeout=900)
    summaries = [decode(line) for line in raw.splitlines() if line.strip()]
    snapshots = [item.get("snapshot_id") for item in summaries if item.get("message_type") == "summary"]
    require(len(snapshots) == 1 and isinstance(snapshots[0], str)
            and re.fullmatch(r"[a-f0-9]{8,64}", snapshots[0]), "missing-backup-snapshot")
    require(digest(source) == before, "backup-source-changed")
    restored = command_digest(base + ["dump", snapshots[0], str(source.absolute())])
    require(restored == before, "backup-restore-mismatch")
    return {"snapshot": snapshots[0], "sha256": before, "restore_verified": True, "release_id": release_id}


def retain_backups(history, current, config):
    """Forget only owned successful snapshot IDs; never infer ownership from arbitrary repository tags."""
    require(isinstance(history, list) and all(isinstance(item, str) and re.fullmatch(r"[a-f0-9]{8,64}", item)
                                            for item in history), "invalid-backup-history")
    require(current in history, "rollback-snapshot-not-in-history")
    history = list(dict.fromkeys(history))
    keep = set(history[-8:]) | {current}
    expired = [item for item in history if item not in keep]
    if expired:
        run(["restic", "--no-cache", "--repo", config["backup_repository"], "--password-file", config["backup_password_file"],
             "forget", "--", *expired], timeout=900)
    return [item for item in history if item in keep]
