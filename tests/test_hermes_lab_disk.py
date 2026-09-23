"""Explicit disposable libguestfs disk integration; no libvirt domain is started."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/hermes/unattended"))
import lab_boot  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integration_gate import integration_only  # noqa: E402


class LabDiskIntegrationTests(unittest.TestCase):
    """Real libguestfs disk creation/conversion/injection; opt-in integration only.

    This is deliberately absent from tests/offline_allowlist.txt: installing
    guestfish/qemu-img must not activate appliance and disk work in the normal
    pre-push gate. Run it with toolbox/run-integration-checks.sh.
    """

    @integration_only("real guestfish appliance and qemu-img disk work")
    @unittest.skipUnless(
        shutil.which("guestfish") and shutil.which("qemu-img"),
        "the real disk test requires guestfish and qemu-img",
    )
    def test_real_fat_disk_injection_and_idempotent_readback(self):
        with tempfile.TemporaryDirectory(prefix="hermes-lab-disk-") as temporary:
            work = Path(temporary)
            environment = {**os.environ, "LIBGUESTFS_BACKEND": "direct", "TMPDIR": temporary,
                           "LIBGUESTFS_TMPDIR": temporary, "LIBGUESTFS_CACHEDIR": temporary,
                           "XDG_RUNTIME_DIR": temporary}
            inputs = work / "inputs"
            inputs.mkdir()
            for name, data in (("uki", b"synthetic-uki"), ("cert", b"synthetic-cert"),
                               ("key", b"synthetic-key"), ("original", b"original-efi"),
                               ("marker", lab_boot.MARKER.encode())):
                (inputs / name).write_bytes(data)
            # This fixture deliberately tests disk I/O only. Signature validation has
            # independent real-UKI tests; no synthetic boot evidence is produced here.
            script = (f'mkdir /EFI\nmkdir /EFI/fedora\nmkdir /EFI/BOOT\n'
                      f'upload {inputs}/original /EFI/fedora/shimx64.efi\n'
                      f'upload {inputs}/original /EFI/BOOT/BOOTX64.EFI\n'
                      f'upload {inputs}/marker /hermes-tpm-stage\n'
                      f'upload {inputs}/key /hermes-pcr-public-key.pem\nsync\n')
            subprocess.run(["guestfish", "-N", str(work / "fixture.raw") + "=fs:vfat:32M",
                            "-m", "/dev/sda1"], input=script.encode(), env=environment,
                           check=True, stdout=subprocess.DEVNULL, timeout=180)
            disk = work / "fixture.qcow2"
            subprocess.run(["qemu-img", "convert", "-f", "raw", "-O", "qcow2",
                            str(work / "fixture.raw"), str(disk)], check=True, timeout=30)
            with patch.dict(os.environ, environment), patch.object(lab_boot, "DISK", disk):
                with patch.object(lab_boot, "check_domain"), patch.object(lab_boot, "virsh", return_value=b"shut off"):
                    with patch.object(lab_boot, "verify_uki", return_value="synthetic-command-line"):
                        for attempt in range(2):
                            stage = work / str(attempt)
                            stage.mkdir()
                            lab_boot.inject("synthetic-uuid", inputs / "uki", inputs / "cert", inputs / "key", stage)
                    for index, destination in enumerate(lab_boot.EFI_PATHS):
                        restored = work / ("original-" + str(index))
                        lab_boot.guestfish([("download", destination + ".hermes-original", restored)])
                        self.assertEqual(restored.read_bytes(), b"original-efi")


if __name__ == "__main__":
    unittest.main()
