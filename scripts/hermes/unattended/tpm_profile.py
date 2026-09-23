"""Standard TPM2 profile preparation and read-only service checks.

Rendering is only for an offline staging tree. Applying it to a host, rebuilding
its initrd and starting services are separate, explicitly approved operations.
"""

import argparse
import os
from pathlib import Path
import re

from common import digest, report, require

MASKS = (
    "etc/nvpcr/hardware.nvpcr",
    "etc/nvpcr/cryptsetup.nvpcr",
    "etc/systemd/system/systemd-pcrproduct.service",
)
DRACUT_PATH = "etc/dracut.conf.d/99-hermes-standard-tpm2.conf"
DRACUT = ('# Preserve TPM unlock and PCR11 phase modules; carry administrative masks into each new initrd.\n'
          'add_dracutmodules+=" tpm2-tss systemd-pcrphase "\n'
          'install_items+=" /etc/nvpcr/hardware.nvpcr /etc/nvpcr/cryptsetup.nvpcr '
          '/etc/systemd/system/systemd-pcrproduct.service "\n')


def masked(path):
    return path.is_symlink() and os.readlink(path) == "/dev/null"


def profile(root=Path("/")):
    root = Path(root)
    present = [os.path.lexists(root / path) for path in (*MASKS, DRACUT_PATH)]
    if not any(present):
        return "vendor-nvpcr"
    require(all(masked(root / path) for path in MASKS), "partial-standard-tpm2-profile")
    config = root / DRACUT_PATH
    require(not config.is_symlink() and config.is_file() and config.read_text() == DRACUT,
            "standard-tpm2-dracut-mismatch")
    # A future vendor definition is a new consumer review, not implicit consent
    # to restart anchoring. Follow the same directory precedence as systemd.
    seen = set()
    for directory in ("etc/nvpcr", "run/nvpcr", "usr/local/lib/nvpcr", "usr/lib/nvpcr"):
        for path in sorted((root / directory).glob("*.nvpcr")):
            if path.name in seen:
                continue
            seen.add(path.name)
            require(masked(path), "unreviewed-nvpcr-definition")
    return "standard-tpm2"


def render(root):
    root = Path(root).absolute()
    require(root.resolve() != Path("/") and root.is_dir(), "offline-staging-root-required")
    require(not any(p.is_symlink() for p in (root, *root.parents)), "symlinked-staging-root")
    require(root.stat().st_uid == os.getuid() and not root.stat().st_mode & 0o022,
            "unsafe-staging-root")
    # Check the entire set before creating anything. A partial prior render can
    # resume, but existing configurations and parent symlinks are never replaced.
    for relative in (*MASKS, DRACUT_PATH):
        path = root / relative
        for parent in path.parents:
            if parent == root:
                break
            require(not parent.is_symlink(), "symlinked-profile-parent")
            require(not parent.exists() or parent.is_dir(), "invalid-profile-parent")
        if os.path.lexists(path):
            require(masked(path) if relative in MASKS else
                    path.is_file() and not path.is_symlink() and path.read_text() == DRACUT,
                    "existing-profile-conflict")
    for relative in MASKS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not os.path.lexists(path):
            path.symlink_to("/dev/null")
    config = root / DRACUT_PATH
    config.parent.mkdir(parents=True, exist_ok=True)
    if not config.exists():
        # Exclusive create, followed by fsync; an interrupted incomplete file is
        # deliberately a conflict on rerun, never silently replaced.
        with config.open("x") as stream:
            stream.write(DRACUT)
            stream.flush()
            os.fsync(stream.fileno())
        config.chmod(0o644)
    return {"ok": True, "profile": profile(root), "scope": "offline-staging-only"}


def services(run, root=Path("/")):
    selected = profile(root)
    observations = {}
    for unit in ("systemd-tpm2-setup-early.service", "systemd-tpm2-setup.service"):
        raw = run(["systemctl", "show", unit, "-p", "LoadState", "-p", "ActiveState",
                   "-p", "SubState", "-p", "ExecMainStatus", "-p", "ConditionResult"]).decode()
        fields = dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)
        require(fields.get("LoadState") == "loaded" and fields.get("ExecMainStatus") == "0",
                "failed-tpm-service")
        active = fields.get("ActiveState") == "active" and fields.get("SubState") == "exited"
        # The early unit may have completed in initrd: its real-root condition
        # skips when the SRK public file already exists. Never accept late skips.
        skipped = (unit.endswith("-early.service") and fields.get("ActiveState") == "inactive"
                   and fields.get("ConditionResult") == "no")
        require(active or skipped, "failed-tpm-service")
        observations[unit] = "passed" if active else "skipped-existing-srk"
    # Public files provide continuity evidence only, not proof of unsealing.
    for suffix in ("pem", "tpm2b_public"):
        early = Path(root) / ("run/systemd/tpm2-srk-public-key." + suffix)
        late = Path(root) / ("var/lib/systemd/tpm2-srk-public-key." + suffix)
        require(early.is_file() and late.is_file() and not early.is_symlink() and not late.is_symlink(),
                "srk-public-files-missing")
        require(0 < early.stat().st_size <= 65536 and 0 < late.stat().st_size <= 65536,
                "srk-public-files-invalid")
        require(early.read_bytes() == late.read_bytes(), "srk-public-files-mismatch")
    if selected == "vendor-nvpcr":
        require(run(["systemctl", "is-active", "systemd-pcrproduct.service"]).strip() == b"active",
                "failed-tpm-service")
    else:
        require(run(["systemctl", "show", "systemd-pcrproduct.service", "-p", "LoadState", "--value"])
                .strip() == b"masked", "unmasked-nvpcr-consumer")
    return {"profile": selected, "srk_services": observations, "srk_public_files_match": True}


def inspect_initrd(image, run, observe=None):
    """Check an archive and retain only bounded, secret-free inspection verdicts."""
    image = Path(image)
    require(image.is_file() and not image.is_symlink(), "invalid-profile-initrd")
    before = digest(image)
    listing = run(["lsinitrd", str(image)]).decode().splitlines()
    modules = {line.strip() for line in run(["lsinitrd", "-m", str(image)]).decode().splitlines()}

    def entries(relative):
        matches = [(line, re.search(r"\s(?:\./)?" + re.escape(relative)
                                   + r"(?: -> (.*))?$", line)) for line in listing]
        return [(line, match.group(1)) for line, match in matches if match]

    def directory(relative):
        matches = entries(relative)
        return len(matches) == 1 and matches[0][0].startswith("d") and matches[0][1] is None

    checks = {}
    for relative in MASKS:
        matches = entries(relative)
        link = len(matches) == 1 and matches[0][0].startswith("l")
        target = matches[0][1] if link else None
        # dracut-install deliberately converts absolute symlinks to relative ones.
        # Accept only this exact spelling, with actual archive directories along
        # its path. Never resolve a target through the controller's filesystem.
        parents = relative.split("/")[:-1]
        relative_null = "../" * len(parents) + "dev/null"
        directories = all(directory("/".join(parents[:i + 1])) for i in range(len(parents)))
        directories = directories and directory("dev")
        kind = "absolute-null" if target == "/dev/null" else "relative-null" if target == relative_null else "other"
        accepted = link and (kind == "absolute-null" or kind == "relative-null" and directories)
        checks[relative] = {"entries": len(matches), "symbolic_link": link, "target_kind": kind,
                            "directory_chain_verified": directories, "accepted": accepted}
    unknown = 0
    for line in listing:
        match = re.search(r"\s(?:\./)?(?:etc|run|usr/local/lib|usr/lib)/nvpcr/([^\s]+\.nvpcr)(?: -> .*)?$", line)
        unknown += bool(match and match.group(1) not in {"hardware.nvpcr", "cryptsetup.nvpcr"})
    supported = {"crypt", "tpm2-tss", "systemd-pcrphase"} <= modules
    unchanged = digest(image) == before
    review = {"profile": "standard-tpm2", "sha256": before, "masks": list(MASKS),
              "required_modules_present": supported, "mask_checks": checks,
              "unknown_definition_count": unknown, "archive_unchanged": unchanged, "boot_verified": False,
              "passed": supported and all(c["accepted"] for c in checks.values()) and unknown == 0 and unchanged}
    if observe is not None:
        observe(review)
    require(supported, "initrd-tpm-modules-missing")
    require(all(c["accepted"] for c in checks.values()), "initrd-standard-mask-missing")
    require(unknown == 0, "initrd-unreviewed-nvpcr-definition")
    require(unchanged, "initrd-changed-during-review")
    return review


def main():
    parser = argparse.ArgumentParser(description="Render a Hermes TPM2 profile into an offline staging tree")
    parser.add_argument("--root", required=True)
    return render(parser.parse_args().root)


if __name__ == "__main__":
    report(main)
