"""Offline recovery-export safety checks; never access a live host."""
import importlib.util
import os
from pathlib import Path
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class ExportTests(unittest.TestCase):
    def test_export_and_rejection_boundaries(self):
        script = Path(__file__).resolve().parents[1] / "scripts/hermes/selinux/export-reviewed-policy-v2.py"
        spec = importlib.util.spec_from_file_location("export_v2", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(prefix="hermes-export-v2-test-") as tmp:
            directory = Path(tmp)
            module.BACKUP = directory / "backup"
            module.EXPORT = directory / "export"
            module.POLICY = directory / "disk"
            module.LOADED = directory / "loaded"
            module.POLICY.write_bytes(b"fixture disk")
            module.LOADED.write_bytes(b"fixture loaded")
            module.EXPECTED = module.digest(module.POLICY)
            names = ["modules.before", "targeted-active.tar.gz", "policy.before", "executable-context.before",
                     "boot.before", "firmware.before", "journal-cursor.before", "candidate.pp", "installation-started",
                     "run/systemd/nvpcr/nvpcr-anchor.cred", "var/lib/systemd/nvpcr/nvpcr-anchor.cred"]
            for name in names:
                path = module.BACKUP / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"fixture data")
            (module.BACKUP / "unrelated-private-data").write_bytes(b"excluded fixture")
            module.MODULE = module.digest(module.BACKUP / "candidate.pp")
            module.BASE = module.digest(module.BACKUP / "policy.before")

            def command(*args):
                if args[0] == "hostname":
                    return b"hermes\n"
                if args[0] == "getenforce":
                    return b"Enforcing\n"
                if args[0] in ("stat", "matchpathcon"):
                    return b"system_u:object_r:hermes_tpm2_setup_exec_t:s0\n"
                if args[0] == "systemctl":
                    return b"MainPID=0\n"
                self.fail(str(args))

            with patch.object(module.os, "geteuid", return_value=0), \
                    patch.object(module.os, "chown"), patch.object(module.os, "umask"), \
                    patch.dict(os.environ), patch.object(module, "command", side_effect=command), \
                    patch.object(module.pwd, "getpwnam", return_value=SimpleNamespace(pw_uid=1000, pw_gid=1000)), \
                    patch.object(sys, "argv", ["export", "--approved-policy-export"]), patch("builtins.print"):
                module.main()
                with tarfile.open(module.EXPORT / "recovery.tar.gz") as archive:
                    self.assertEqual(set(archive.getnames()), set(names))
                self.assertEqual((module.EXPORT / "loaded-policy.35").read_bytes(), b"fixture loaded")
                self.assertEqual(module.EXPORT.stat().st_mode & 0o777, 0o700)
                self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in module.EXPORT.iterdir()))
                with self.assertRaises(FileExistsError):
                    module.main()
                module.EXPORT = directory / "other-export"
                module.EXPECTED = "invalid"
                with self.assertRaisesRegex(RuntimeError, "policy/enforcing"):
                    module.main()
                module.EXPECTED = module.digest(module.POLICY)
                anchor = module.BACKUP / names[-1]
                anchor.unlink()
                anchor.symlink_to(module.LOADED)
                with self.assertRaisesRegex(RuntimeError, "unsafe"):
                    module.main()
                self.assertFalse(module.EXPORT.exists())
            with patch.object(sys, "argv", ["export"]):
                with self.assertRaisesRegex(RuntimeError, "Expected"):
                    module.main()


if __name__ == "__main__":
    unittest.main()
