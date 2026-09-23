"""Create isolated EFI installer media carrying public enrollment material only."""

import argparse
import os
from pathlib import Path
import tempfile
import shutil

from common import decode, digest, protected_file, report, require, run


def build(uki, certificate, pcr_public_key, kickstart, output):
    uki, certificate, pcr_public_key, kickstart, output = map(Path, (uki, certificate, pcr_public_key, kickstart, output))
    for path in (uki, certificate, pcr_public_key, kickstart):
        protected_file(path)
    require(uki.stat().st_size < 400 * 1024**2 and kickstart.stat().st_size < 1024**2,
            "installer-media-input-too-large")
    require(not output.exists() and not output.is_symlink(), "installer-media-exists")
    with tempfile.TemporaryDirectory(prefix=".efi-media-", dir=output.parent) as temporary:
        frozen = []
        for index, source in enumerate((uki, certificate, pcr_public_key, kickstart)):
            target = Path(temporary) / str(index)
            shutil.copyfile(source, target)
            target.chmod(0o600)
            frozen.append(target)
        uki, certificate, pcr_public_key, kickstart = frozen
        # The TPM installer applies the same reviewed offline renderer to its
        # target root before dracut. Never substitute a second profile template.
        helpers = []
        for name in ("tpm_profile.py", "common.py"):
            source = protected_file(Path(__file__).resolve().parent / name)
            require(source.stat().st_size < 1024**2, "installer-helper-too-large")
            target = Path(temporary) / name
            shutil.copyfile(source, target)
            target.chmod(0o600)
            helpers.append((target, "::/" + name))
        run(["sbverify", "--cert", str(certificate), str(uki)])
        sections = decode(run(["ukify", "--json=short", "inspect", str(uki)]))
        require(sections.get(".pcrpkey", {}).get("sha256") == digest(pcr_public_key), "installer-pcr-key-mismatch")
        command_line = sections.get(".cmdline", {}).get("text", "").split()
        require("inst.stage2=hd:LABEL=Fedora-S-dvd-x86_64-44" in command_line
                and "inst.ks=hd:LABEL=OEMDRV:/ks.cfg" in command_line, "not-a-certified-installer-uki")
        image = Path(temporary) / "oemdrv.img"
        with image.open("xb") as stream:
            stream.truncate(512 * 1024**2)
        image.chmod(0o600)
        run(["mformat", "-i", str(image), "-F", "-v", "OEMDRV", "::"])
        run(["mmd", "-i", str(image), "::/EFI", "::/EFI/BOOT"])
        for source, destination in [(uki, "::/EFI/BOOT/BOOTX64.EFI"), (kickstart, "::/ks.cfg"),
                                    (pcr_public_key, "::/tpm2-pcr-public-key.pem"), *helpers]:
            before = digest(source)
            run(["mcopy", "-i", str(image), str(source), destination])
            restored = Path(temporary) / "readback"
            run(["mcopy", "-i", str(image), destination, str(restored)])
            require(digest(source) == before and digest(restored) == before, "installer-media-copy-mismatch")
            restored.unlink()
        os.link(image, output)
    return {"ok": True, "stage": "installer-media-built", "sha256": digest(output), "boot_verified": False}


def main():
    parser = argparse.ArgumentParser(description="Create a fresh signed EFI installer disk")
    for name in ("uki", "certificate", "pcr-public-key", "kickstart", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    return build(args.uki, args.certificate, args.pcr_public_key, args.kickstart, args.output)


if __name__ == "__main__":
    report(main)
