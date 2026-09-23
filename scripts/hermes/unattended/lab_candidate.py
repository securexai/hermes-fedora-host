"""Build and freeze public staged guest inputs; never issue certification evidence."""

import argparse
import os
from pathlib import Path
import re
import tempfile

import boot_build
import lab_boot
import prepare
from common import atomic, canonical, decode, digest, lock, protected_file, report, require

NAMES = ("linux", "initrd", "osrel", "cmdline")
EXPORT = "/hermes-boot-inputs/"


def extract(domain_uuid, pcr_public_key, directory):
    lab_boot.check_domain(domain_uuid)
    require(lab_boot.bounded_cat("/hermes-tpm-stage").strip() == lab_boot.MARKER.encode(),
            "lab-tpm-stage-marker-missing")
    enrolled = directory / "enrolled.pub"
    lab_boot.bounded_download("/hermes-pcr-public-key.pem", enrolled, 65536)
    require(digest(enrolled) == digest(protected_file(pcr_public_key)), "lab-enrolled-pcr-key-mismatch")
    raw = lab_boot.bounded_cat(EXPORT + "SHA256SUMS")
    require(len(raw) < 1024, "invalid-boot-export-manifest")
    records = {}
    require(raw.isascii(), "invalid-boot-export-manifest")
    for line in raw.decode("ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (linux|initrd|osrel|cmdline)", line)
        require(match is not None and match[2] not in records, "invalid-boot-export-manifest")
        records[match[2]] = match[1]
    require(set(records) == set(NAMES), "incomplete-boot-export")
    for name in NAMES:
        target = directory / name
        lab_boot.bounded_download(EXPORT + name, target, 400 * 1024**2 if name in ("linux", "initrd") else 65536)
        require(0 < target.stat().st_size <= (400 * 1024**2 if name in ("linux", "initrd") else 65536),
                "invalid-boot-export-size")
        target.chmod(0o600)
        require(digest(target) == records[name], "boot-export-hash-mismatch")
    command_line = (directory / "cmdline").read_text().strip()
    require(re.fullmatch(
        r"root=/dev/mapper/vg_root-root ro rd.lvm.lv=vg_root/root rd.luks.uuid=luks-"
        r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12} rd.luks.options=tpm2-device=auto",
        command_line), "invalid-exported-command-line")
    lab_boot.check_domain(domain_uuid)
    return {name: directory / name for name in NAMES}


def construct(args, directory):
    # A new candidate path is mandatory; failure never reuses a partially frozen candidate.
    require(not Path(args.destination).exists() and not Path(args.destination).is_symlink(),
            "candidate-destination-exists")
    inputs = extract(args.domain_uuid, args.pcr_public_key, directory)
    inputs["stub"] = protected_file(args.stub)
    uki = directory / "installed.efi"
    built = boot_build.build(inputs, uki, args.secureboot_key, args.certificate,
                             args.pcr_key, args.pcr_public_key)
    lab_boot.verify_uki(uki, args.certificate, args.pcr_public_key)
    candidate = prepare.prepare(args.repository, args.destination, args.transaction, uki,
                                decode(protected_file(args.host_identity).read_bytes()),
                                args.release_id, args.model, args.baseline)
    frozen_uki = Path(args.destination) / "boot/hermes.efi"
    require(digest(frozen_uki) == built["uki_sha256"], "candidate-uki-mismatch")
    injection_dir = directory / "injection"
    injection_dir.mkdir(mode=0o700)
    command_line, sha = lab_boot.inject(args.domain_uuid, frozen_uki, args.certificate,
                                        args.pcr_public_key, injection_dir)
    require(sha == built["uki_sha256"], "injected-candidate-uki-mismatch")
    result = {**candidate, "stage": "candidate-uki-injected", "domain_uuid": args.domain_uuid,
              "uki_sha256": sha, "build": built, "boot_verified": False, "certification": "pending"}
    atomic(Path(args.state_dir) / "lab-candidate.json", canonical(result))
    if args.start:
        result.update(lab_boot.first_boot(args.domain_uuid, command_line, args.identity_file,
                                          args.known_hosts, args.timeout))
        result["stage"] = "candidate-first-boot-observed"
    return result


def main():
    parser = argparse.ArgumentParser(description="Construct the fixed disposable Hermes boot candidate")
    for name in ("domain-uuid", "stub", "secureboot-key", "certificate", "pcr-key", "pcr-public-key",
                 "repository", "destination", "transaction", "host-identity", "release-id", "model",
                 "baseline", "state-dir"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--start", action="store_true")
    parser.add_argument("--identity-file")
    parser.add_argument("--known-hosts")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    state = Path(args.state_dir)
    require(state.is_absolute() and state.is_dir() and not state.is_symlink()
            and state.stat().st_uid == os.getuid() and not state.stat().st_mode & 0o077,
            "private-lab-state-directory-required")
    require(1 <= args.timeout <= 900, "invalid-lab-boot-timeout")
    if args.start:
        require(args.identity_file and args.known_hosts, "pinned-lab-ssh-required")
        protected_file(args.known_hosts)
        require(not protected_file(args.identity_file).stat().st_mode & 0o077, "ssh-identity-not-private")
    with lock(lab_boot.DISK.parent / ".hermes-lab-boot.lock"):
        atomic(state / "lab-candidate.json", canonical({"ok": False, "stage": "candidate-started",
                                                       "boot_verified": False}))
        with tempfile.TemporaryDirectory(prefix="candidate-", dir=state) as temporary:
            result = construct(args, Path(temporary))
        atomic(state / "lab-candidate.json", canonical(result))
        return result


if __name__ == "__main__":
    report(main)
