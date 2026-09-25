"""Guardrails for publishing the host half of the DeepSeek test grant."""

import importlib.util
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts/hermes/manual/lab/deepseek-host-grant-finalize.py"
)
SPEC = importlib.util.spec_from_file_location("deepseek_host_grant_finalize", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FinalizeTests(unittest.TestCase):
    def test_changed_grant_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "deepseek-test-grant.py"
            source.write_text("changed\n")
            with patch.object(MODULE, "GRANT_SOURCE", source):
                with self.assertRaisesRegex(RuntimeError, "reviewed grant source changed"):
                    MODULE.grant_module()

    def test_unexpected_host_artifact_stops_before_rule_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / "installed"
            base.mkdir()
            (base / "access.py").write_bytes(b"access")
            (base / "boot-inspect.py").write_bytes(b"inspect")
            (base / "bundle.tar").write_bytes(b"bundle")
            (base / "surprise").write_bytes(b"unexpected")
            source = root / "source.py"
            inspector = root / "inspector.py"
            source.write_bytes(b"access")
            inspector.write_bytes(b"inspect")
            grant = Mock(HOST_BASE=base)
            with self.assertRaisesRegex(RuntimeError, "host access directory differs"):
                MODULE.verify_host_copy(grant, source, inspector, b"bundle")

    def test_wrong_vm_stops_before_guest_ssh(self):
        grant = Mock()
        grant.bound_vm.return_value = "shut off"
        with patch.object(MODULE, "guest_read") as read:
            with self.assertRaisesRegex(RuntimeError, "must be running"):
                MODULE.verify_guest_grant(grant)
        grant.bound_network.assert_not_called()
        read.assert_not_called()

    def test_guest_listing_mismatch_stops_host_publication(self):
        grant = Mock()
        grant.bound_vm.return_value = "running"
        grant.GUEST_BASE = Path("/usr/local/libexec/hermes-deepseek-test")
        grant.MACHINE_SHA256 = "pinned-machine"
        grant.rule.return_value = b"aicowork ALL=(root) NOPASSWD: allowed-command\n"
        pin_hash = MODULE.hashlib.sha256((MODULE.BUNDLE_SHA256 + "\n").encode()).hexdigest()
        grant_run = [
            "guest_machine_sha256=pinned-machine bundle_present=True",
            f"{MODULE.GRANT_SOURCE_SHA256}  {grant.GUEST_BASE / 'access.py'}",
            "0:0:644",
            f"{pin_hash}  /etc/hermes-deepseek-test/bundle.sha256",
            "0:0:644",
            "(root) NOPASSWD: broader-command",
        ]
        with patch.object(MODULE, "guest_read", side_effect=grant_run):
            with self.assertRaisesRegex(RuntimeError, "NOPASSWD listing differs"):
                MODULE.verify_guest_grant(grant)

    def test_exact_install_publishes_only_host_rule(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "access.py"
            inspector = root / "boot-inspect.py"
            manual = root / "manual"
            source.write_bytes(b"source")
            inspector.write_bytes(b"inspector")
            manual.mkdir()
            grant = Mock()
            grant.HOST_USER = "aicloudopspecial"
            grant.HOST_RULE = root / "host-rule"
            grant.source_files.return_value = (source, inspector, manual)
            grant.archive.return_value = b"bundle"
            grant.digest.return_value = MODULE.BUNDLE_SHA256
            grant.rule.return_value = b"fixed-host-rule\n"
            with (
                patch.object(MODULE.os, "geteuid", return_value=0),
                patch.dict(os.environ, {"SUDO_USER": grant.HOST_USER}),
                patch.object(MODULE, "verify_host_copy"),
                patch.object(MODULE, "verify_guest_grant") as guest,
                patch("sys.stdout", new_callable=io.StringIO),
            ):
                MODULE.install(grant)
            guest.assert_called_once_with(grant)
            grant.installed_file.assert_called_once_with(
                grant.HOST_RULE, b"fixed-host-rule\n", 0o440
            )
            grant.run.assert_any_call("/usr/sbin/visudo", "-cf", str(grant.HOST_RULE))

    def test_exact_rerun_restores_label_and_rechecks_visudo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "access.py"
            inspector = root / "boot-inspect.py"
            manual = root / "manual"
            source.write_bytes(b"source")
            inspector.write_bytes(b"inspector")
            manual.mkdir()
            rule = root / "host-rule"
            rule.write_bytes(b"fixed-host-rule\n")
            grant = Mock()
            grant.HOST_USER = "aicloudopspecial"
            grant.HOST_RULE = rule
            grant.source_files.return_value = (source, inspector, manual)
            grant.archive.return_value = b"bundle"
            grant.digest.return_value = MODULE.BUNDLE_SHA256
            grant.rule.return_value = b"fixed-host-rule\n"
            with (
                patch.object(MODULE.os, "geteuid", return_value=0),
                patch.dict(os.environ, {"SUDO_USER": grant.HOST_USER}),
                patch.object(MODULE, "verify_host_copy"),
                patch.object(MODULE, "verify_guest_grant"),
                patch("sys.stdout", new_callable=io.StringIO),
            ):
                MODULE.install(grant)
            grant.installed_file.assert_not_called()
            grant.run.assert_any_call("/usr/sbin/restorecon", str(rule))
            grant.run.assert_any_call("/usr/sbin/visudo", "-cf", str(rule))


if __name__ == "__main__":
    unittest.main()
