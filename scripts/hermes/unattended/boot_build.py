"""Build a signed UKI on the workstation; never copy private signing keys into a guest."""

import argparse
import os
from pathlib import Path
import shutil
import tempfile

from common import atomic, canonical, digest, protected_file, report, require, run


def toolchain():
    ukify = shutil.which("ukify")
    require(ukify and shutil.which("sbsign") and shutil.which("sbverify"), "missing-uki-tools", 69)
    # systemd-measure is deliberately installed in libexec rather than PATH.
    systemctl = shutil.which("systemctl")
    require(systemctl, "missing-systemd-tools", 69)
    library = Path(systemctl).resolve().parent.parent / "lib/systemd"
    require((library / "systemd-measure").is_file(), "missing-systemd-measure", 69)
    return ukify, library


def build(inputs, output, secureboot_key, secureboot_certificate, pcr_key, pcr_public_key, purpose="installed"):
    require(purpose in ("installed", "installer"), "invalid-uki-purpose")
    require(set(inputs) == {"linux", "initrd", "osrel", "cmdline", "stub"}, "invalid-uki-inputs")
    paths = {name: protected_file(path) for name, path in inputs.items()}
    for key in (secureboot_key, pcr_key):
        path = protected_file(key)
        require(path.stat().st_uid == os.getuid() and not path.stat().st_mode & 0o077,
                "boot-signing-key-not-private")
    require(Path(secureboot_key).resolve() != Path(pcr_key).resolve(), "boot-signing-roles-not-separated")
    protected_file(secureboot_certificate)
    protected_file(pcr_public_key)
    run(["openssl", "rsa", "-pubin", "-in", str(pcr_public_key), "-noout"])
    pcr_public = run(["openssl", "pkey", "-in", str(pcr_key), "-pubout", "-outform", "DER"])
    require(pcr_public == run(["openssl", "pkey", "-pubin", "-in", str(pcr_public_key), "-outform", "DER"]),
            "pcr-signing-key-mismatch")
    require(pcr_public != run(["openssl", "pkey", "-in", str(secureboot_key), "-pubout", "-outform", "DER"]),
            "boot-signing-roles-not-separated")
    output = Path(output)
    require(not output.exists() and not output.is_symlink(), "uki-output-exists")
    ukify, library = toolchain()
    with tempfile.TemporaryDirectory(prefix=".uki-", dir=output.parent) as temporary:
        directory = Path(temporary)
        frozen = {}
        for name, source in paths.items():
            target = directory / name
            shutil.copyfile(source, target)
            target.chmod(0o600)
            frozen[name] = target
        command_line = frozen["cmdline"].read_text().strip()
        require(command_line and not any(c in command_line for c in "\n\r\x00"), "invalid-uki-command-line")
        options = command_line.split()
        if purpose == "installed":
            require(any(option.startswith("root=") for option in options)
                    and any(option.startswith("rd.luks.uuid=") for option in options)
                    and "rd.luks.options=tpm2-device=auto" in options, "missing-uki-encrypted-root-policy")
        else:
            require("inst.stage2=hd:LABEL=Fedora-S-dvd-x86_64-44" in options
                    and "inst.ks=hd:LABEL=OEMDRV:/ks.cfg" in options, "invalid-installer-command-line")
        require(not any(option in ("selinux=0", "enforcing=0", "rd.luks=0", "rd.break")
                        or option.startswith(("init=", "rdinit=", "rd.break=")) for option in options),
                "unsafe-uki-command-line")
        atomic(frozen["cmdline"], command_line.encode())
        unsigned_inputs = {name: digest(path) for name, path in frozen.items()}
        # Disk unlock runs in initrd; TPM anchor services also unseal after
        # leave-initrd and sysinit. Sign each normal state with the same PCR11 key.
        # Anaconda omits initrd phase services and measures sysinit then ready.
        phases = ("enter-initrd enter-initrd:leave-initrd "
                  "enter-initrd:leave-initrd:sysinit enter-initrd:leave-initrd:sysinit:ready"
                  if purpose == "installed" else "sysinit sysinit:ready")
        result = directory / "hermes.efi"
        run([ukify, "build", "--config=/dev/null", "--efi-arch=x64", "--no-sign-kernel",
             "--linux=" + str(frozen["linux"]), "--initrd=" + str(frozen["initrd"]),
             "--os-release=@" + str(frozen["osrel"]), "--cmdline=@" + str(frozen["cmdline"]),
             "--stub=" + str(frozen["stub"]), "--tools=" + str(library),
             "--signtool=sbsign", "--secureboot-private-key=" + str(secureboot_key),
             "--secureboot-certificate=" + str(secureboot_certificate),
             "--pcr-private-key=" + str(pcr_key), "--pcr-public-key=" + str(pcr_public_key),
             "--pcr-banks=sha256", "--phases=" + phases, "--output=" + str(result)], timeout=300)
        run(["sbverify", "--cert", str(secureboot_certificate), str(result)])
        # Verify required embedded sections independently of ukify's exit status.
        info = run([ukify, "--json=short", "inspect", str(result)])
        from common import decode
        sections = decode(info)
        require(all(name in sections for name in (".linux", ".initrd", ".cmdline", ".osrel", ".pcrpkey", ".pcrsig")),
                "incomplete-signed-uki")
        result.chmod(0o600)
        os.link(result, output)
    return {"ok": True, "stage": "uki-built", "uki_sha256": digest(output), "inputs": unsigned_inputs,
            "secureboot_certificate_sha256": digest(secureboot_certificate),
            "pcr_public_key_sha256": digest(pcr_public_key), "pcr_bank": "sha256",
            "signed_pcr": 11, "phases": phases.split(), "purpose": purpose, "boot_verified": False}


def main():
    parser = argparse.ArgumentParser(description="Build a workstation-signed Hermes UKI")
    parser.add_argument("--purpose", choices=("installed", "installer"), default="installed")
    for name in ("linux", "initrd", "osrel", "cmdline", "stub", "output", "secureboot-key",
                 "secureboot-certificate", "pcr-key", "pcr-public-key"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    return build({name: getattr(args, name) for name in ("linux", "initrd", "osrel", "cmdline", "stub")},
                 args.output, args.secureboot_key, args.secureboot_certificate, args.pcr_key, args.pcr_public_key, args.purpose)


if __name__ == "__main__":
    report(main)
