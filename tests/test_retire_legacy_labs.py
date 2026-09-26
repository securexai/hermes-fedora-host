"""Offline guards for the exact manual-VM boot directory retirement."""

from __future__ import annotations

import importlib.util
import os
import pathlib
import tempfile
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "vm/retire-legacy-labs.py"
SPEC = importlib.util.spec_from_file_location("retire_legacy_labs", SOURCE)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

SIX_FILES = {
    "Fedora-Server-dvd-x86_64-44-1.7.iso": 0o644,
    "Fedora-Server-44-1.7-x86_64-CHECKSUM": 0o644,
    "fedora.gpg": 0o644,
    "ks.cfg": 0o600,
    "guest-password.hash": 0o600,
    "ks.iso": 0o640,
}


class BootDirectoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.boot = pathlib.Path(self.temp.name) / "boot"
        self.boot.mkdir()
        self.boot.chmod(0o711)
        specification = MODULE.TARGETS["lab-hermes-manual-r1"]
        self.media = {self.boot / path.name: mode for path, mode in specification["media"].items()}
        self.auxiliary = {
            self.boot / path.name: mode for path, mode in specification["auxiliary"].items()
        }
        for name, mode in SIX_FILES.items():
            path = self.boot / name
            path.write_bytes(b"synthetic offline fixture\n")
            path.chmod(mode)

    def check_boot(self) -> None:
        uid = os.getuid()
        MODULE.exact_boot_files(self.media, self.auxiliary, uid, uid)

    def test_six_owned_files_pass_and_unrelated_file_refuses(self) -> None:
        self.check_boot()
        extra = self.boot / "unrelated.txt"
        extra.write_text("preserve\n")
        with self.assertRaisesRegex(MODULE.Refusal, "unexpected exact directory contents"):
            self.check_boot()
        self.assertEqual(extra.read_text(), "preserve\n")

    def test_sensitive_hash_must_keep_owner_only_mode(self) -> None:
        (self.boot / "guest-password.hash").chmod(0o644)
        with self.assertRaisesRegex(MODULE.Refusal, "unexpected owner or mode"):
            self.check_boot()

    def test_boot_directory_must_keep_exact_mode(self) -> None:
        self.boot.chmod(0o777)
        with self.assertRaisesRegex(MODULE.Refusal, "unsafe exact directory"):
            self.check_boot()


if __name__ == "__main__":
    unittest.main()
