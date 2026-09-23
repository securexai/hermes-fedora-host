"""Create a disposable OVMF variable store; never modify workstation firmware variables."""

import argparse
import os
from pathlib import Path
import tempfile

from common import decode, digest, protected_file, report, require, run


def prepare(template, certificate, output):
    template, certificate, output = Path(template), Path(certificate), Path(output)
    protected_file(template)
    protected_file(certificate)
    require(not output.exists() and not output.is_symlink(), "firmware-output-exists")
    certificate_der = run(["openssl", "x509", "-in", str(certificate), "-outform", "DER"])
    with tempfile.TemporaryDirectory(prefix=".firmware-", dir=output.parent) as temporary:
        directory = Path(temporary)
        image, record = directory / "vars.fd", directory / "vars.json"
        run(["virt-fw-vars", "--input", str(template), "--output", str(image),
             "--enroll-cert", str(certificate), "--microsoft-db=uefi11", "--microsoft-kek=all",
             "--add-db", "e9a063fd-54b5-4b71-9d0d-3a346a55f826", str(certificate),
             "--distro-keys=fedora", "--sb", "--output-json", str(record)])
        variables = {item["name"]: bytes.fromhex(item["data"])
                     for item in decode(record.read_bytes())["variables"]}
        require(variables.get("SecureBootEnable") == b"\x01" and variables.get("CustomMode") == b"\x00"
                and certificate_der in variables.get("PK", b"") and certificate_der in variables.get("db", b""),
                "firmware-enrollment-verification-failed")
        image.chmod(0o600)
        os.link(image, output)
    return {"ok": True, "stage": "firmware-prepared", "firmware_sha256": digest(output),
            "certificate_sha256": digest(certificate), "boot_verified": False}


def main():
    parser = argparse.ArgumentParser(description="Prepare a fresh disposable Secure Boot variable store")
    for option in ("template", "certificate", "output"):
        parser.add_argument("--" + option, required=True)
    args = parser.parse_args()
    return prepare(args.template, args.certificate, args.output)


if __name__ == "__main__":
    report(main)
