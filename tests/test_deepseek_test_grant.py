"""Offline authorization and source-boundary tests for the temporary VM grant."""

import base64
import hashlib
import importlib.util
import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/hermes/manual/lab/deepseek-test-grant.py"
SPEC = importlib.util.spec_from_file_location("deepseek_test_grant", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GrantTests(unittest.TestCase):
    def test_guest_identity_uses_pinned_network_host_key(self):
        key = base64.b64encode(b"test-ed25519-host-key").decode()
        fingerprint = "SHA256:" + base64.b64encode(
            hashlib.sha256(base64.b64decode(key)).digest()
        ).decode().rstrip("=")
        identity = f"guest_user=0\nmachine_sha256={MODULE.MACHINE_SHA256}\n"
        scanned = f"{MODULE.GUEST_IP} ssh-ed25519 {key} guest\n"
        with (
            patch.object(MODULE, "guest_script", return_value=identity),
            patch.object(MODULE, "run", return_value=scanned),
            patch.object(MODULE, "HOST_FINGERPRINT", fingerprint),
        ):
            self.assertEqual(MODULE.guest_identity(), f"{MODULE.GUEST_IP} ssh-ed25519 {key}\n")

    def test_guest_identity_rejects_mismatched_host_key(self):
        identity = f"guest_user=0\nmachine_sha256={MODULE.MACHINE_SHA256}\n"
        key = base64.b64encode(b"wrong-host-key").decode()
        with (
            patch.object(MODULE, "guest_script", return_value=identity),
            patch.object(MODULE, "run", return_value=f"{MODULE.GUEST_IP} ssh-ed25519 {key}"),
        ):
            with self.assertRaisesRegex(RuntimeError, "fingerprint mismatch"):
                MODULE.guest_identity()

    def test_rules_name_only_fixed_installed_operations(self):
        host = MODULE.rule("host").decode()
        guest = MODULE.rule("guest").decode()
        for action in MODULE.HOST_OPS:
            self.assertIn(f"/usr/bin/python3 -I {MODULE.HOST_BASE}/access.py host {action}", host)
        for action in MODULE.GUEST_OPS:
            self.assertIn(
                f"/usr/bin/python3 -I {MODULE.GUEST_BASE}/access.py guest {action}", guest
            )
        self.assertNotIn("NOPASSWD: ALL", host + guest)
        self.assertNotIn("scripts/hermes/manual", host + guest)

    def test_domain_uuid_mismatch_stops_before_network_check(self):
        with patch.object(MODULE, "virsh", return_value="wrong") as virsh:
            with self.assertRaisesRegex(RuntimeError, "VM UUID mismatch"):
                MODULE.bound_vm()
        virsh.assert_called_once_with("domuuid", MODULE.DOMAIN)

    def test_domain_mac_mismatch_stops(self):
        def virsh(action, _domain):
            return {
                "domuuid": MODULE.UUID,
                "domiflist": "vnet0 network fvh-nat virtio 52:54:00:00:00:00",
            }[action]

        with patch.object(MODULE, "virsh", side_effect=virsh):
            with self.assertRaisesRegex(RuntimeError, "network or MAC mismatch"):
                MODULE.bound_vm()

    def test_unknown_guest_action_never_starts_ssh(self):
        with patch.object(MODULE.subprocess, "run") as command:
            with self.assertRaisesRegex(RuntimeError, "guest operation denied"):
                MODULE.run_guest("arbitrary-shell")
        command.assert_not_called()

    def test_network_lease_mismatch_stops_before_key_enrollment(self):
        def virsh(action, *_args):
            return {
                "net-dumpxml": '<network><ip address="192.168.124.1"/></network>',
                "domifaddr": "vnet0 52:54:00:83:bf:4b ipv4 192.168.124.99/24",
            }[action]

        with patch.object(MODULE, "virsh", side_effect=virsh):
            with self.assertRaisesRegex(RuntimeError, "lease address mismatch"):
                MODULE.bound_network()

    def test_archive_stable_and_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "safe.sh").write_text("#!/bin/sh\nexit 0\n")
            (root / "safe.sh").chmod(0o755)
            first = MODULE.archive(root)
            self.assertEqual(first, MODULE.archive(root))
            (root / "link").symlink_to("safe.sh")
            with self.assertRaisesRegex(RuntimeError, "unsupported manual source"):
                MODULE.archive(root)

    def test_archive_excludes_lab_privilege_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "m01.sh").write_text("exit 0\n")
            (root / "lab").mkdir()
            (root / "lab" / "deepseek-test-grant.py").write_text("unneeded\n")
            with tarfile.open(fileobj=io.BytesIO(MODULE.archive(root)), mode="r:") as tar:
                self.assertEqual(tar.getnames(), ["m01.sh"])

    def test_guest_archive_rejects_traversal_links_and_duplicate_names(self):
        names = set()
        safe = tarfile.TarInfo("boot/tpm-enroll.sh")
        safe.type = tarfile.REGTYPE
        self.assertEqual(MODULE.archive_member_path(safe, names), Path("boot/tpm-enroll.sh"))
        with self.assertRaisesRegex(RuntimeError, "unsafe archive path"):
            MODULE.archive_member_path(safe, names)
        traversal = tarfile.TarInfo("../etc/sudoers")
        with self.assertRaisesRegex(RuntimeError, "unsafe archive path"):
            MODULE.archive_member_path(traversal, set())
        link = tarfile.TarInfo("link")
        link.type = tarfile.SYMTYPE
        with self.assertRaisesRegex(RuntimeError, "unsupported archive member"):
            MODULE.archive_member_path(link, set())

    def test_known_partial_host_copy_reconciles_only_when_guest_grants_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "host"
            base.mkdir()
            (base / "access.py").write_bytes(b"old code")
            (base / "boot-inspect.py").write_bytes(b"inspector")
            (base / "bundle.tar").write_bytes(b"old bundle")
            with (
                patch.object(MODULE, "HOST_BASE", base),
                patch.object(MODULE, "HOST_RULE", Path(directory) / "rule"),
                patch.object(MODULE, "PREVIOUS_HOST_CODE_SHA256", MODULE.digest(b"old code")),
                patch.object(MODULE, "PREVIOUS_BUNDLE_SHA256", MODULE.digest(b"old bundle")),
                patch.object(MODULE, "trusted"),
                patch.object(
                    MODULE, "guest_script", return_value="GUEST_GRANT_STATE=ABSENT"
                ) as guest,
            ):
                MODULE.reconcile_previous_host_copy(b"new code", b"inspector", b"new bundle")
                self.assertFalse((base / "access.py").exists())
                self.assertFalse((base / "bundle.tar").exists())
                self.assertEqual((base / "boot-inspect.py").read_bytes(), b"inspector")
                guest.assert_called_once_with(MODULE.GUEST_GRANT_INVENTORY)

    def test_partial_host_copy_is_preserved_when_guest_grant_may_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "host"
            base.mkdir()
            old = base / "bundle.tar"
            old.write_bytes(b"old bundle")
            with (
                patch.object(MODULE, "HOST_BASE", base),
                patch.object(MODULE, "HOST_RULE", Path(directory) / "rule"),
                patch.object(MODULE, "PREVIOUS_BUNDLE_SHA256", MODULE.digest(b"old bundle")),
                patch.object(MODULE, "trusted"),
                patch.object(MODULE, "guest_script", return_value="GUEST_GRANT_STATE=PRESENT"),
            ):
                with self.assertRaisesRegex(RuntimeError, "guest grant state is not absent"):
                    MODULE.reconcile_previous_host_copy(b"code", b"inspector", b"new bundle")
            self.assertEqual(old.read_bytes(), b"old bundle")

    def test_start_install_rejects_wrong_vm_before_start(self):
        with (
            patch.object(MODULE.os, "geteuid", return_value=0),
            patch.dict(os.environ, {"SUDO_USER": MODULE.HOST_USER}),
            patch.object(MODULE, "check"),
            patch.object(MODULE, "bound_vm", side_effect=RuntimeError("VM UUID mismatch")),
            patch.object(MODULE, "virsh") as virsh,
        ):
            with self.assertRaisesRegex(RuntimeError, "VM UUID mismatch"):
                MODULE.start_install()
        virsh.assert_not_called()

    def test_start_install_starts_only_bound_vm_then_installs(self):
        with (
            patch.object(MODULE.os, "geteuid", return_value=0),
            patch.dict(os.environ, {"SUDO_USER": MODULE.HOST_USER}),
            patch.object(MODULE, "check"),
            patch.object(MODULE, "bound_vm", side_effect=["shut off", "running"]),
            patch.object(MODULE, "virsh", return_value="Domain started") as virsh,
            patch.object(MODULE, "bound_network") as network,
            patch.object(MODULE, "guest_identity") as identity,
            patch.object(MODULE, "install") as install,
        ):
            MODULE.start_install()
        virsh.assert_called_once_with("start", MODULE.DOMAIN)
        network.assert_called_once()
        identity.assert_called_once()
        install.assert_called_once()


if __name__ == "__main__":
    unittest.main()
