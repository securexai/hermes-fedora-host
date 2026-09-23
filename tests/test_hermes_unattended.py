"""Offline trust-boundary tests. Keys and archives are disposable synthetic fixtures."""

import copy
import hashlib
import io
import json
import os
import shutil
import socket
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/hermes/unattended"))
from common import Failure, canonical, decode, lock  # noqa: E402
from release import GATES, NAMESPACE, SCHEMA, candidate_fingerprint, unpack, validate  # noqa: E402
from credentials import Broker  # noqa: E402
import credentials as credentials_module  # noqa: E402
from policy import maintenance_open, ssh_options  # noqa: E402
from gates import backup_snapshot, check_vulnerabilities, retain_backups, scan_image  # noqa: E402
import host as host_module  # noqa: E402
import controller as controller_module  # noqa: E402
from build_release import build  # noqa: E402
import maintenance  # noqa: E402
import notify  # noqa: E402
import materialize  # noqa: E402
import boot_build  # noqa: E402
import firmware  # noqa: E402
import efi_media  # noqa: E402
import lab_boot  # noqa: E402
import lab_candidate  # noqa: E402
from types import SimpleNamespace
import signer  # noqa: E402
from finalize import finalize, validate_candidate  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))  # noqa: E402
from integration_gate import integration_only  # noqa: E402


class BootPreflightTests(unittest.TestCase):
    def check_tokens(self, tokens):
        def command(args):
            if args[0] == "getenforce":
                return b"Enforcing\n"
            if args[0] == "mokutil":
                return b"SecureBoot enabled\n"
            if args[0] == "cryptsetup":
                return canonical({"tokens": tokens})
            return b""
        with patch.object(Path, "read_text", return_value='ID=fedora\nVERSION_ID=44\n'), \
                patch.object(host_module, "run", side_effect=command), \
                patch.object(host_module.shutil, "disk_usage", return_value=SimpleNamespace(free=30 * 1024**3)):
            host_module.preflight({"luks_device": "/dev/vda3"})

    def test_systemd_signed_pcr_token(self):
        self.check_tokens({"0": self.standard_token()})

    @staticmethod
    def standard_token():
        return {"type": "systemd-tpm2", "tpm2-pcrs": [7], "tpm2_pubkey_pcrs": [11],
                "tpm2-pcr-bank": "sha256", "tpm2_pubkey": "public-test-fixture"}

    def test_pin_pcrlock_and_update_brittle_policy_rejected(self):
        for override in ({"tpm2-pin": True}, {"tpm2-pin": "false"}, {"tpm2_pcrlock": True},
                         {"tpm2_pcrlock_nv": "nv-fixture"}, {"tpm2-pcr-bank": "sha1"},
                         {"tpm2-pcrs": [0, 7]}, {"tpm2-pcrs": [7, 11]}, {"tpm2_pubkey": ""}):
            with self.subTest(override=override), self.assertRaisesRegex(Failure, "tpm-boot-policy-mismatch"):
                self.check_tokens({"0": {**self.standard_token(), **override}})

    def test_new_token_does_not_hide_legacy_automatic_unlock_path(self):
        with self.assertRaisesRegex(Failure, "tpm-boot-policy-mismatch"):
            self.check_tokens({"0": self.standard_token(), "1": {"type": "systemd-tpm2", "tpm2-pcrs": [0, 7]}})

    def test_future_credentials_require_explicit_trusted_boot_binding(self):
        instance = host_module.Host.__new__(host_module.Host)
        instance.state = {"phase": "backup-verified"}
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(host_module, "CREDENTIAL", Path(temporary) / "credential"), \
                patch.object(host_module, "run", return_value=b"encrypted-fixture") as command, \
                patch.object(instance, "save", return_value={}):
            instance.credential({"key": "runtime-canary-never-in-argv"})
            args = command.call_args.args[0]
            self.assertIn("--tpm2-pcrs=7", args)
            self.assertIn("--tpm2-public-key=/etc/systemd/tpm2-pcr-public-key.pem", args)
            self.assertIn("--tpm2-public-key-pcrs=11", args)
            self.assertNotIn("runtime-canary-never-in-argv", " ".join(args))
            self.assertEqual(command.call_args.kwargs["data"], b"runtime-canary-never-in-argv")

    def test_missing_required_pcr_policy_rejected(self):
        for token in (
            {"type": "systemd-tpm2", "tpm2-pcrs": [7]},
            {"type": "systemd-tpm2", "tpm2_pubkey_pcrs": [11]},
            {"type": "systemd-tpm2", "tpm2-pcrs": [7], "tpm2-public-key-pcrs": [11]},
        ):
            with self.subTest(token=token), self.assertRaisesRegex(Failure, "tpm-boot-policy-mismatch"):
                self.check_tokens({"0": token})


class BootCapacityTests(unittest.TestCase):
    def test_boot_install_does_not_select_kernel_before_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "hermes.efi").write_bytes(b"signed-uki-fixture")
            instance = host_module.Host.__new__(host_module.Host)
            instance.directory = root
            instance.manifest = {"boot_artifact": "hermes.efi"}
            instance.release_id = "order-test"
            with patch.object(host_module, "run") as command, \
                    patch.object(host_module, "install_file") as install, \
                    patch.object(host_module.shutil, "disk_usage", return_value=SimpleNamespace(free=1024**3)):
                self.assertEqual(instance.install_boot(), "hermes-order-test.efi")
                install.assert_called_once()
                self.assertFalse(any(c.args[0][0] == "bootctl" for c in command.call_args_list))

    def test_insufficient_esp_space_preserves_existing_boot_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "hermes.efi").write_bytes(b"x" * 4096)
            instance = host_module.Host.__new__(host_module.Host)
            instance.directory = root
            instance.manifest = {"boot_artifact": "hermes.efi"}
            instance.release_id = "space-test"
            with patch.object(host_module, "run") as command, \
                    patch.object(host_module, "install_file") as install, \
                    patch.object(host_module.shutil, "disk_usage", return_value=SimpleNamespace(free=1024)):
                with self.assertRaisesRegex(Failure, "insufficient-esp-space"):
                    instance.install_boot()
                install.assert_not_called()
                self.assertFalse(any(call.args[0][0] == "bootctl" for call in command.call_args_list))


class PrivilegedBoundaryReviewTests(unittest.TestCase):
    def setUp(self):
        # Workstation checkout ancestors may be group-writable. Only emulate the
        # enrollment ancestor permissions; exercise actual descriptor traversal.
        real_fstat = os.fstat
        ancestors = set(Path(__file__).resolve().parents)
        def enrolled_stat(fd):
            info = real_fstat(fd)
            if Path("/proc/self/fd/" + str(fd)).resolve() in ancestors:
                values = list(info)
                values[0] &= ~0o022
                values[4] = os.getuid()
                return os.stat_result(values)
            return info
        fixture = patch("signer.os.fstat", side_effect=enrolled_stat)
        fixture.start()
        self.addCleanup(fixture.stop)

    def test_signer_rejects_symlink_parent_and_oversize(self):
        # A trusted-parent tree is required: /tmp itself is intentionally rejected.
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as name:
            root = Path(name)
            private = root / "private"
            private.mkdir(mode=0o700)
            (private / "proof").write_bytes(b"canary")
            (root / "link").symlink_to(private, target_is_directory=True)
            with self.assertRaises(OSError):
                signer.read_owned(root / "link/proof", os.getuid(), 100)
            with self.assertRaisesRegex(Failure, "untrusted-signing-input"):
                signer.read_owned(private / "proof", os.getuid(), 2)
            self.assertEqual(signer.read_owned(private / "proof", os.getuid(), 100), b"canary")

    def test_signer_parent_replacement_cannot_redirect_held_descriptor(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as name:
            root = Path(name)
            original = root / "candidate"
            original.mkdir(mode=0o700)
            (original / "proof").write_bytes(b"original")
            other = root / "other"
            other.mkdir(mode=0o700)
            (other / "proof").write_bytes(b"redirected")
            real_open = os.open
            def swap(path, flags, *args, **kwargs):
                fd = real_open(path, flags, *args, **kwargs)
                if path == "candidate":
                    original.rename(root / "held")
                    original.symlink_to(other, target_is_directory=True)
                return fd
            with patch("signer.os.open", side_effect=swap):
                self.assertEqual(signer.read_owned(original / "proof", os.getuid(), 100), b"original")

    def test_identity_data_setup_drops_root_before_user_path_mutation(self):
        account = SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid(), pw_dir="/home/hermes")
        with patch("host.pwd.getpwnam", return_value=account), patch("host.run"), \
                patch("host.as_hermes") as child, patch("host.Path.is_symlink", return_value=False), \
                patch("host.Path.exists", return_value=False), \
                patch("host.Path.read_text", return_value="hermes:100000:65536\n"), \
                patch("host.os.chown") as chown:
            host_module.identity()
        chown.assert_not_called()
        script = child.call_args.args[0][-1]
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name)
            target = directory / "target"
            target.mkdir(mode=0o755)
            (directory / "data").symlink_to(target, target_is_directory=True)
            result = subprocess.run([sys.executable, "-I", "-c", script.replace("/home/hermes/data", str(directory / "data"))],
                                    capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(target.stat().st_mode & 0o777, 0o755)


class FreshRuntimeIdentityTests(unittest.TestCase):
    def test_first_podman_call_has_started_user_runtime(self):
        account = SimpleNamespace(pw_uid=1001, pw_gid=1001, pw_dir="/home/hermes")
        runtime_ready = False

        def command(args, **kwargs):
            nonlocal runtime_ready
            if args == ["systemctl", "start", "user@1001.service"]:
                runtime_ready = True
            return b""

        def podman(args, **kwargs):
            self.assertTrue(runtime_ready, "fresh Podman requires the user runtime directory")
            return b""

        with patch("host.pwd.getpwnam", return_value=account), patch("host.run", side_effect=command), \
                patch("host.as_hermes", side_effect=podman), patch("host.Path.is_symlink", return_value=False), \
                patch("host.Path.exists", return_value=False), \
                patch("host.Path.read_text", return_value="hermes:100000:65536\n"):
            host_module.identity()

    def test_user_command_leaves_operator_working_directory(self):
        account = SimpleNamespace(pw_uid=1001)
        with patch("host.pwd.getpwnam", return_value=account), patch("host.run", return_value=b"ok") as command:
            self.assertEqual(host_module.as_hermes(["podman", "unshare", "id"]), b"ok")
        args = command.call_args.args[0]
        self.assertEqual(args[:6], ["runuser", "-u", "hermes", "--", "env", "--chdir=/home/hermes"])


@integration_only("real ukify/sbverify/dracut UKI build against a host kernel")
class BootBuildIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="hermes-uki-test-")
        cls.root = Path(cls.temporary.name)
        kernels = list(Path("/usr/lib/modules").glob("*/vmlinuz"))
        if not kernels:
            cls.temporary.cleanup()
            raise unittest.SkipTest("A readable test kernel is required for UKI integration")
        cls.kernel = kernels[0]
        def command(args):
            subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        command(["openssl", "req", "-new", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                 "-subj", "/CN=Hermes synthetic UKI test/", "-keyout", str(cls.root / "sb.key"),
                 "-out", str(cls.root / "sb.crt")])
        command(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048",
                 "-out", str(cls.root / "pcr.key")])
        command(["openssl", "pkey", "-in", str(cls.root / "pcr.key"), "-pubout", "-out", str(cls.root / "pcr.pub")])
        for name in ("sb.key", "pcr.key"):
            (cls.root / name).chmod(0o600)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(self.work.cleanup)
        self.directory = Path(self.work.name)
        (self.directory / "initrd").write_bytes(b"SYNTHETIC NONBOOTABLE INITRD")
        (self.directory / "osrel").write_text("ID=fedora\nVERSION_ID=44\n")
        (self.directory / "cmdline").write_text("root=/dev/mapper/test rd.luks.uuid=test rd.luks.options=tpm2-device=auto")
        _, library = boot_build.toolchain()
        self.inputs = {"linux": self.kernel, "stub": library / "boot/efi/linuxx64.efi.stub",
                       **{name: self.directory / name for name in ("initrd", "osrel", "cmdline")}}

    def build(self):
        return boot_build.build(self.inputs, self.directory / "test.efi", self.root / "sb.key", self.root / "sb.crt",
                                self.root / "pcr.key", self.root / "pcr.pub")

    def test_real_installed_uki_handoff_verifies_signature_and_pcr_key(self):
        (self.directory / "cmdline").write_text(
            "root=/dev/mapper/vg_root-root rd.luks.uuid=test rd.luks.options=tpm2-device=auto")
        self.build()
        command_line = lab_boot.verify_uki(self.directory / "test.efi", self.root / "sb.crt", self.root / "pcr.pub")
        self.assertEqual(command_line, (self.directory / "cmdline").read_text())
        data = bytearray((self.directory / "test.efi").read_bytes())
        data[0x100] ^= 1
        (self.directory / "test.efi").write_bytes(data)
        with self.assertRaises(Failure):
            lab_boot.verify_uki(self.directory / "test.efi", self.root / "sb.crt", self.root / "pcr.pub")

    def test_real_uki_contains_signed_pcr_policy_without_claiming_boot(self):
        result = self.build()
        self.assertEqual(result["stage"], "uki-built")
        self.assertFalse(result["boot_verified"])
        self.assertEqual(result["signed_pcr"], 11)
        image = self.directory / "test.efi"
        data = bytearray(image.read_bytes())
        data[0x100] ^= 1
        image.write_bytes(data)
        check = subprocess.run(["sbverify", "--cert", str(self.root / "sb.crt"), str(image)], capture_output=True)
        self.assertNotEqual(check.returncode, 0)

    def test_installed_uki_signs_distinct_initrd_and_host_boot_policies(self):
        self.build()
        inspected = json.loads(subprocess.run(
            ["ukify", "--json=short", "inspect", str(self.directory / "test.efi")],
            capture_output=True, check=True).stdout)
        signatures = json.loads(inspected[".pcrsig"]["text"])["sha256"]
        # Disk unlock and the later TPM anchor services need separate measured states.
        self.assertEqual(len({entry["pol"] for entry in signatures}), 4)
        self.assertTrue(all(entry["pcrs"] == [11] for entry in signatures))
        self.assertEqual(len({entry["pkfp"] for entry in signatures}), 1)

    def test_kernel_command_line_cannot_disable_selinux(self):
        with (self.directory / "cmdline").open("a") as stream:
            stream.write(" selinux=0")
        with self.assertRaisesRegex(Failure, "unsafe-uki-command-line"):
            self.build()
        self.assertFalse((self.directory / "test.efi").exists())

    def test_firmware_contains_public_certificate_and_never_overwrites_template(self):
        template = Path("/usr/share/edk2/ovmf/OVMF_VARS.fd")
        if not template.exists():
            self.skipTest("OVMF fixture template is required")
        before = hashlib.sha256(template.read_bytes()).hexdigest()
        output = self.directory / "vars.fd"
        result = firmware.prepare(template, self.root / "sb.crt", output)
        self.assertEqual(result["stage"], "firmware-prepared")
        self.assertFalse(result["boot_verified"])
        self.assertEqual(hashlib.sha256(template.read_bytes()).hexdigest(), before)
        with self.assertRaisesRegex(Failure, "firmware-output-exists"):
            firmware.prepare(template, self.root / "sb.crt", output)

    def test_signed_installer_media_round_trip(self):
        (self.directory / "cmdline").write_text(
            "inst.stage2=hd:LABEL=Fedora-S-dvd-x86_64-44 inst.ks=hd:LABEL=OEMDRV:/ks.cfg console=ttyS0,115200n8")
        uki = self.directory / "installer.efi"
        boot_build.build(self.inputs, uki, self.root / "sb.key", self.root / "sb.crt",
                         self.root / "pcr.key", self.root / "pcr.pub", purpose="installer")
        kickstart = self.directory / "ks.cfg"
        kickstart.write_text("# synthetic, not a deployable installer\n")
        result = efi_media.build(uki, self.root / "sb.crt", self.root / "pcr.pub", kickstart, self.directory / "oemdrv.img")
        self.assertEqual(result["stage"], "installer-media-built")
        self.assertFalse(result["boot_verified"])
        for name in ('tpm_profile.py', 'common.py'):
            readback = self.directory / ('readback-' + name)
            subprocess.run(['mcopy', '-i', str(self.directory / 'oemdrv.img'), '::/' + name, str(readback)], check=True)
            source = Path(__file__).resolve().parents[1] / 'scripts/hermes/unattended' / name
            self.assertEqual(readback.read_bytes(), source.read_bytes())


class TpmStagingBoundaryTests(unittest.TestCase):
    def test_unmeasured_pcrs_fail_before_enrollment(self):
        text = (Path(__file__).resolve().parents[1] / "vm/kickstart/hermes-tpm-enroll.ks").read_text()
        script = text.split("python3 - <<'PCRCHECK'\n", 1)[1].split("\nPCRCHECK", 1)[0]
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            script = script.replace("/sys/class/tpm/tpm0/pcr-sha256", name)
            for value in ("0" * 64, "f" * 64, "invalid"):
                (root / "7").write_text("a" * 64)
                (root / "11").write_text(value)
                result = subprocess.run([sys.executable, "-c", script], capture_output=True)
                self.assertNotEqual(result.returncode, 0)
            (root / "11").write_text("b" * 64)
            subprocess.run([sys.executable, "-c", script], check=True)

    def test_tpm_stage_requires_all_enrollment_inputs_before_hypervisor_access(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "installer.iso").write_bytes(b"synthetic")
            (root / "ssh.pub").write_text("ssh-ed25519 AAAA synthetic\n")
            script = Path(__file__).resolve().parents[1] / "vm/create-hermes-server-vm.sh"
            result = subprocess.run([str(script), "--iso", str(root / "installer.iso"), "--ssh-key",
                                     str(root / "ssh.pub"), "--tpm-stage"], stdin=subprocess.DEVNULL,
                                    capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 66)
            self.assertIn(b"TPM staging needs", result.stderr)

    def test_firmware_inputs_cannot_silently_change_legacy_mode(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "installer.iso").write_bytes(b"synthetic")
            (root / "ssh.pub").write_text("ssh-ed25519 AAAA synthetic\n")
            script = Path(__file__).resolve().parents[1] / "vm/create-hermes-server-vm.sh"
            result = subprocess.run([str(script), "--iso", str(root / "installer.iso"), "--ssh-key",
                                     str(root / "ssh.pub"), "--firmware-vars", str(root / "vars.fd")],
                                    stdin=subprocess.DEVNULL, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 64)
            self.assertIn(b"require --tpm-stage", result.stderr)


class MaterializerBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / ".env"

    def read_fixture(self):
        actual_run = subprocess.run
        def child(args, **kwargs):
            self.assertIn("--reuid=10000", args)
            self.assertIn("--clear-groups", args)
            self.assertLess(args.index("--chdir=/home/hermes/data"), args.index("setpriv"))
            script = args[-1].replace("'.env'", repr(str(self.path)))
            return actual_run([sys.executable, "-c", script], **kwargs)
        with patch("materialize.subprocess.run", side_effect=child):
            return materialize.channel_environment(type("Account", (), {"pw_uid": 1001})())

    def test_channel_values_are_read_without_root_authority(self):
        self.path.write_text("CHANNEL_TOKEN=synthetic-channel-canary\n")
        self.assertEqual(self.read_fixture(), ["CHANNEL_TOKEN=synthetic-channel-canary"])

    def test_symlink_is_rejected_by_actual_reader(self):
        target = self.path.parent / "private"
        target.write_text("synthetic-private-canary")
        self.path.symlink_to(target)
        with self.assertRaises(subprocess.CalledProcessError):
            self.read_fixture()

    def test_oversized_file_is_rejected_by_actual_reader(self):
        self.path.write_bytes(b"a" * 131073)
        with self.assertRaises(subprocess.CalledProcessError):
            self.read_fixture()


class SignerEvidenceTests(unittest.TestCase):
    def records(self):
        return {gate: {"completed_at": 100000, "run_id": "a" * 64} for gate in GATES}

    def test_current_single_run_is_eligible(self):
        signer.validate_evidence(self.records(), 100010)

    def test_stale_evidence_cannot_receive_a_new_expiry(self):
        with self.assertRaisesRegex(Failure, "stale-certification-evidence"):
            signer.validate_evidence(self.records(), 200000)

    def test_evidence_from_different_runs_is_rejected(self):
        records = self.records()
        records["boot"]["run_id"] = "b" * 64
        with self.assertRaisesRegex(Failure, "certification-order-mismatch"):
            signer.validate_evidence(records, 100010)

    def test_destruction_cannot_precede_runtime_checks(self):
        records = self.records()
        records["vm_destroyed"]["completed_at"] -= 1
        with self.assertRaisesRegex(Failure, "certification-order-mismatch"):
            signer.validate_evidence(records, 100010)

    def test_revocation_cannot_precede_inference(self):
        records = self.records()
        records["credential_revocation"]["completed_at"] -= 1
        with self.assertRaisesRegex(Failure, "certification-order-mismatch"):
            signer.validate_evidence(records, 100010)


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.release = self.directory / "selected.tar"
        self.release.write_bytes(b"synthetic release")

    def test_missed_window_does_not_load_credentials_or_deploy(self):
        with patch("maintenance.maintenance_open", return_value=False), patch("maintenance.controller.main") as invoke:
            self.assertEqual(maintenance.execute("missing", self.release, self.directory)["stage"], "deferred")
        invoke.assert_not_called()
        self.assertFalse((self.directory / "latest.json").exists())

    def test_missing_release_reports_action_without_invocation(self):
        with patch("maintenance.maintenance_open", return_value=True), patch("maintenance.controller.main") as invoke:
            with self.assertRaisesRegex(Failure, "certified-release-unavailable"):
                maintenance.execute("missing", self.directory / "absent", self.directory)
        invoke.assert_not_called()
        self.assertEqual(decode((self.directory / "latest.json").read_bytes())["outcome"], "action-required")

    def test_controller_failure_cannot_leak_canary_to_event(self):
        with patch("maintenance.maintenance_open", return_value=True), \
                patch("maintenance.controller.main", side_effect=Failure(78, "CANARY_PRIVATE_KEY")):
            with self.assertRaisesRegex(Failure, "maintenance-needs-attention"):
                maintenance.execute("config", self.release, self.directory)
        self.assertNotIn(b"CANARY", (self.directory / "latest.json").read_bytes())

    def test_nonclosed_result_is_not_completion(self):
        with patch("maintenance.maintenance_open", return_value=True), \
                patch("maintenance.controller.main", return_value={"ok": True, "stage": "reboot-pending"}):
            with self.assertRaises(Failure):
                maintenance.execute("config", self.release, self.directory)
        self.assertEqual(decode((self.directory / "latest.json").read_bytes())["outcome"], "action-required")

    def test_unchanged_completion_is_quiet_and_next_release_notifies(self):
        events = self.directory / "latest.json"
        state = self.directory / "desktop"
        with patch("notify.run") as send:
            maintenance.publish(self.directory, "completed", 0, "first")
            self.assertTrue(notify.deliver(events, state)["notified"])
            maintenance.publish(self.directory, "completed", 0, "first")
            self.assertFalse(notify.deliver(events, state)["notified"])
            maintenance.publish(self.directory, "completed", 0, "second")
            self.assertTrue(notify.deliver(events, state)["notified"])
            self.assertEqual(send.call_count, 2)

    def test_failed_desktop_delivery_retries_without_marking_seen(self):
        maintenance.publish(self.directory, "failed", 69)
        with patch("notify.run", side_effect=Failure(69, "operation-failed")):
            with self.assertRaises(Failure):
                notify.deliver(self.directory / "latest.json", self.directory / "desktop")
        self.assertFalse((self.directory / "desktop/seen").exists())

    def test_injected_notification_text_is_rejected(self):
        value = maintenance.publish(self.directory, "failed", 69)
        value["message"] = "CANARY_PRIVATE_KEY"
        (self.directory / "latest.json").write_bytes(canonical(value))
        with patch("notify.run") as send:
            with self.assertRaisesRegex(Failure, "invalid-notification"):
                notify.deliver(self.directory / "latest.json", self.directory / "desktop")
            send.assert_not_called()


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.key = cls.root / "key"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(cls.key)], check=True)
        cls.signers = cls.root / "signers"
        cls.signers.write_text("hermes-release " + cls.key.with_suffix(".pub").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(self.work.cleanup)
        self.directory = Path(self.work.name)
        self.files = {"payload/host.py": b"# synthetic fixture\n", "packages/transaction.json": b"{}",
                      "boot/hermes.efi": b"synthetic-uki"}
        self.files["payload/vulnerability-policy.json"] = canonical({"schema": "advisory-denylist-v1", "denylist": []})
        self.evidence = {}
        for gate in GATES:
            name = f"evidence/{gate}.json"
            self.evidence[gate] = name
            self.files[name] = canonical({"gate": gate, "result": "PASS", "release_id": "test-1"})
        self.manifest = {"schema": SCHEMA, "release_id": "test-1", "issued_at": 100,
                         "expires_at": 200, "image": "docker.io/nousresearch/hermes-agent@sha256:" + "a" * 64,
                         "provider": "openai-api", "model": "test-model", "baseline_sha256": "b" * 64,
                         "host": {"machine_id_sha256": "c" * 64, "ssh_fingerprint": "SHA256:" + "d" * 43},
                         "transaction": "packages/transaction.json", "boot_artifact": "boot/hermes.efi",
                         "evidence": self.evidence, "files": {}}

    def test_candidate_traversal_is_rejected_before_packaging(self):
        candidate = copy.deepcopy(self.manifest)
        candidate["files"] = {name: {"size": len(raw), "mode": 0o600,
                                     "sha256": hashlib.sha256(raw).hexdigest()}
                              for name, raw in self.files.items() if not name.startswith("evidence/")}
        candidate["files"]["payload/../../private-key"] = {"size": 1, "mode": 0o600, "sha256": "0" * 64}
        with self.assertRaisesRegex(Failure, "unsafe-archive-path"):
            validate_candidate(candidate)

    def test_candidate_cannot_relabel_evidence_paths(self):
        candidate = copy.deepcopy(self.manifest)
        candidate["evidence"]["boot"] = "payload/host.py"
        with self.assertRaisesRegex(Failure, "invalid-candidate-evidence"):
            validate_candidate(candidate)

    def archive(self, *, modify=None, manifest_modify=None, signed=True, duplicate=False, member_type=None):
        manifest = copy.deepcopy(self.manifest)
        manifest["files"] = {name: {"size": len(data), "mode": 0o600,
                                    "sha256": hashlib.sha256(data).hexdigest()}
                             for name, data in self.files.items()}
        if manifest_modify:
            manifest_modify(manifest)
        fingerprint = candidate_fingerprint(manifest)
        for name in self.evidence.values():
            evidence = decode(self.files[name])
            evidence["artifact_fingerprint"] = fingerprint
            if evidence["gate"] == "vulnerability_scan":
                evidence["policy"] = "advisory-denylist-v1"
                evidence["policy_sha256"] = manifest["files"]["payload/vulnerability-policy.json"]["sha256"]
            self.files[name] = canonical(evidence)
            manifest["files"][name] = {"size": len(self.files[name]), "mode": 0o600,
                                       "sha256": hashlib.sha256(self.files[name]).hexdigest()}
        raw = canonical(manifest)
        record = self.directory / "record"
        record.write_bytes(raw)
        record.with_suffix(".sig").unlink(missing_ok=True)
        subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(self.key), "-n", NAMESPACE, str(record)],
                       check=True, capture_output=True)
        files = dict(self.files)
        if modify:
            modify(files)
        files["manifest.json"] = raw
        if signed:
            files["manifest.sig"] = record.with_suffix(".sig").read_bytes()
        result = io.BytesIO()
        with tarfile.open(fileobj=result, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for name, data in files.items():
                entry = tarfile.TarInfo(name)
                entry.mode = 0o600
                entry.size = len(data)
                if member_type and name == "payload/host.py":
                    entry.type = member_type
                    entry.linkname = "/etc/sudoers"
                    entry.size = 0
                archive.addfile(entry, io.BytesIO(data))
            if duplicate:
                archive.addfile(entry, io.BytesIO(data))
        result.seek(0)
        return result, hashlib.sha256(raw).hexdigest()

    def verify(self, archive, **kwargs):
        return unpack(archive, self.directory / "output", self.signers, now=150, **kwargs)

    def test_valid_release(self):
        archive, fingerprint = self.archive()
        result, actual = self.verify(archive, host=self.manifest["host"])
        self.assertEqual(actual, fingerprint)
        self.assertEqual(result["release_id"], "test-1")
        self.assertEqual((self.directory / "output/payload/host.py").read_bytes(), self.files["payload/host.py"])

    def test_tamper_rejected_without_destination(self):
        archive, _ = self.archive(modify=lambda files: files.update({"payload/host.py": b"MALICIOUS CONTENT!!\n"}))
        with self.assertRaises(Failure):
            self.verify(archive)
        self.assertFalse((self.directory / "output").exists())

    def test_missing_signature(self):
        archive, _ = self.archive(signed=False)
        with self.assertRaisesRegex(Failure, "missing-signature"):
            self.verify(archive)

    def test_wrong_signer(self):
        archive, _ = self.archive()
        other = self.directory / "signers"
        other.write_text("another-identity " + self.key.with_suffix(".pub").read_text())
        with self.assertRaises(Failure):
            unpack(archive, self.directory / "output", other, now=150)

    def test_wrong_host(self):
        archive, _ = self.archive()
        with self.assertRaisesRegex(Failure, "wrong-host"):
            self.verify(archive, host={})

    def test_expired_first_use(self):
        archive, _ = self.archive(manifest_modify=lambda value: value.update(expires_at=149))
        with self.assertRaisesRegex(Failure, "expired-or-future-release"):
            self.verify(archive)

    def test_exact_bound_release_can_resume_after_expiry(self):
        archive, fingerprint = self.archive(manifest_modify=lambda value: value.update(expires_at=149))
        self.verify(archive, bound_digest=fingerprint)

    def test_changed_expired_release_cannot_resume(self):
        archive, _ = self.archive(manifest_modify=lambda value: value.update(expires_at=149))
        with self.assertRaises(Failure):
            self.verify(archive, bound_digest="a" * 64)

    def test_future_release(self):
        archive, _ = self.archive(manifest_modify=lambda value: value.update(issued_at=151))
        with self.assertRaises(Failure):
            self.verify(archive)

    def test_legacy_schema(self):
        archive, _ = self.archive(manifest_modify=lambda value: value.update(schema="hermes-promotion-v1"))
        with self.assertRaisesRegex(Failure, "unsigned-or-legacy-release"):
            self.verify(archive)

    def test_unknown_manifest_field(self):
        archive, _ = self.archive(manifest_modify=lambda value: value.update(command="arbitrary"))
        with self.assertRaises(Failure):
            self.verify(archive)

    def test_extra_artifact(self):
        archive, _ = self.archive(modify=lambda files: files.update({"payload/extra": b"extra"}))
        with self.assertRaises(Failure):
            self.verify(archive)

    def test_missing_artifact(self):
        archive, _ = self.archive(modify=lambda files: files.pop("payload/host.py"))
        with self.assertRaises(Failure):
            self.verify(archive)

    def test_signed_traversal(self):
        self.files["payload/../../escape"] = b"escape"
        archive, _ = self.archive()
        with self.assertRaisesRegex(Failure, "unsafe-archive-path"):
            self.verify(archive)
        self.assertFalse((self.directory / "escape").exists())

    def test_signed_absolute_path(self):
        self.files["/etc/sudoers"] = b"escape"
        archive, _ = self.archive()
        with self.assertRaises(Failure):
            self.verify(archive)

    def test_duplicate_archive_entry(self):
        archive, _ = self.archive(duplicate=True)
        with self.assertRaises(Failure):
            self.verify(archive)

    def test_symlink(self):
        archive, _ = self.archive(member_type=tarfile.SYMTYPE)
        with self.assertRaises(Failure):
            self.verify(archive)

    def test_hardlink(self):
        archive, _ = self.archive(member_type=tarfile.LNKTYPE)
        with self.assertRaises(Failure):
            self.verify(archive)

    def test_device(self):
        archive, _ = self.archive(member_type=tarfile.CHRTYPE)
        with self.assertRaises(Failure):
            self.verify(archive)

    def test_failed_evidence(self):
        self.files["evidence/boot.json"] = canonical({"gate": "boot", "result": "FAIL", "release_id": "test-1"})
        archive, _ = self.archive()
        with self.assertRaisesRegex(Failure, "failed-certification-evidence"):
            self.verify(archive)

    def test_missing_gate(self):
        archive, _ = self.archive(manifest_modify=lambda value: value["evidence"].pop("restore"))
        with self.assertRaisesRegex(Failure, "incomplete-certification"):
            self.verify(archive)

    def test_duplicate_json_key(self):
        with self.assertRaises(Failure):
            decode(b'{"a":1,"a":2}')

    def test_target_lock(self):
        with lock(self.directory / "lock"):
            with self.assertRaisesRegex(Failure, "target-busy"):
                with lock(self.directory / "lock"):
                    self.fail("concurrent operation acquired lock")

    def test_symlink_lock(self):
        (self.directory / "lock").symlink_to(self.directory / "other")
        with self.assertRaises(OSError):
            with lock(self.directory / "lock"):
                    self.fail("followed symlink")

    def test_real_builder_signs_and_verifies_complete_release(self):
        now = int(time.time())
        self.archive(manifest_modify=lambda value: value.update(issued_at=now, expires_at=now + 3600))
        manifest = decode((self.directory / "record").read_bytes())
        source = self.directory / "source"
        source.mkdir(mode=0o700)
        for name, data in self.files.items():
            target = source / name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(0o600)
        (source / "manifest.json").write_bytes(canonical(manifest))
        output = self.directory / "built.tar"
        result = build(source, output, self.key, self.signers)
        self.assertTrue(result["ok"])
        with output.open("rb") as stream:
            verified, _ = unpack(stream, self.directory / "rebuilt", self.signers)
        self.assertEqual(verified["release_id"], "test-1")
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_changed_payload_is_rejected_before_signing_command(self):
        now = int(time.time())
        self.archive(manifest_modify=lambda value: value.update(issued_at=now, expires_at=now + 3600))
        source = self.directory / "source"
        source.mkdir(mode=0o700)
        for name, data in self.files.items():
            target = source / name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(0o600)
        (source / "manifest.json").write_bytes((self.directory / "record").read_bytes())
        (source / "payload/host.py").write_bytes(b"altered")
        with patch("build_release.run") as signing:
            with self.assertRaisesRegex(Failure, "candidate-changed-before-signing"):
                build(source, self.directory / "bad.tar", self.key, self.signers)
            signing.assert_not_called()
        self.assertFalse((self.directory / "bad.tar").exists())

    def test_real_finalizer_binds_completed_evidence_and_starts_expiry(self):
        archive, _ = self.archive()
        manifest = self.verify(archive)[0]
        candidate = self.directory / "candidate"
        evidence = self.directory / "completed-evidence"
        candidate.mkdir(mode=0o700)
        evidence.mkdir(mode=0o700)
        for name, raw in self.files.items():
            if name.startswith("evidence/"):
                (evidence / Path(name).name).write_bytes(raw)
                manifest["files"].pop(name)
            else:
                target = candidate / name
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                target.write_bytes(raw)
        (candidate / "candidate.json").write_bytes(canonical(manifest))
        output = self.directory / "finalized.tar"
        finalize(candidate, evidence, output, self.key, self.signers)
        with output.open("rb") as stream:
            verified, _ = unpack(stream, self.directory / "finalized", self.signers)
        self.assertGreater(verified["issued_at"], manifest["issued_at"])
        self.assertEqual(verified["expires_at"] - verified["issued_at"], 86400)
        self.assertEqual(candidate_fingerprint(verified), candidate_fingerprint(manifest))


class BrokerTests(unittest.TestCase):
    def test_activation_requires_exact_listening_unix_socket(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "broker.sock")
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                listener.bind(path)
                environment = {"LISTEN_PID": str(os.getpid()), "LISTEN_FDS": "1"}
                with patch.dict(os.environ, environment), patch.object(credentials_module.socket, "socket", return_value=listener):
                    with self.assertRaisesRegex(Failure, "broker-socket-mismatch"):
                        credentials_module.activated_socket(path)
                    listener.listen(1)
                    self.assertIs(credentials_module.activated_socket(path), listener)
                    with self.assertRaisesRegex(Failure, "broker-socket-mismatch"):
                        credentials_module.activated_socket(path + "-other")
                with patch.dict(os.environ, {"LISTEN_PID": "0", "LISTEN_FDS": "1"}):
                    with self.assertRaisesRegex(Failure, "socket-activation-required"):
                        credentials_module.activated_socket(path)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.calls = []
        self.reject_revoked = True
        self.fail_create = False
        self.policy = {"test_project": "proj_test", "production_project": "proj_prod",
                       "test_uid": 1001, "production_uid": 1002}
        self.broker = Broker(self.policy, self, self.temp.name)
        self.keys = {}
        self.broker.secret = self.secret
        self.lease = "a" * 32

    def secret(self, lease, value=None):
        if value:
            self.keys[lease] = value
        return self.keys[lease]

    def call(self, method, path, body=None, token=None):
        self.calls.append((method, path, body, token))
        if method == "POST":
            if self.fail_create:
                raise Failure(69, "network-failed")
            return {"id": "svc_test", "api_key": {"value": "CANARY_NEVER_LOG_THIS"}}
        if method == "DELETE":
            return {"deleted": True}
        return {"unauthorized": self.reject_revoked}

    def request(self, operation, uid=1001, role="test"):
        return self.broker.handle(uid, {"operation": operation, "role": role, "lease": self.lease})

    def test_peer_identity_rejected_before_api(self):
        with self.assertRaises(Failure):
            self.request("issue", uid=1002)
        self.assertEqual(self.calls, [])

    def test_disabled_production_rejected_before_api_for_every_peer(self):
        self.policy.update(production_project=None, production_uid=None)
        self.broker = Broker(self.policy, self, self.temp.name)
        self.broker.secret = self.secret
        for uid in (0, 1001, 1002):
            with self.subTest(uid=uid), self.assertRaisesRegex(Failure, "broker-role-disabled"):
                self.request("issue", uid=uid, role="production")
        self.assertEqual(self.calls, [])
        self.request("issue")
        self.assertEqual(self.calls[0][1], "organization/projects/proj_test/service_accounts")

    def test_incomplete_disabled_policy_and_privileged_peers_rejected(self):
        for changes in ({"production_project": None}, {"production_uid": None},
                        {"test_uid": 0}, {"production_uid": 0}, {"test_uid": True},
                        {"production_uid": 1001}):
            with self.subTest(changes=changes), self.assertRaises(Failure):
                Broker({**self.policy, **changes}, self, self.temp.name)

    def test_only_fixed_project_is_used(self):
        self.request("issue")
        self.assertEqual(self.calls[0][1], "organization/projects/proj_test/service_accounts")

    def test_repeated_issue_does_not_create_another_account(self):
        first = self.request("issue")
        second = self.request("issue")
        self.assertEqual(first, second)
        self.assertEqual(len(self.calls), 1)

    def test_uncertain_issue_not_retried(self):
        self.fail_create = True
        with self.assertRaises(Failure):
            self.request("issue")
        self.fail_create = False
        with self.assertRaisesRegex(Failure, "lease-needs-reconciliation"):
            self.request("issue")
        self.assertEqual(len(self.calls), 1)

    def test_revocation_checks_actual_key_rejection(self):
        self.request("issue")
        result = self.request("revoke")
        self.assertTrue(result["revoked"])
        self.assertEqual(self.calls[-2][0:2], ("DELETE", "organization/projects/proj_test/service_accounts/svc_test"))
        self.assertEqual(self.calls[-1][0:2], ("GET", "models"))

    def test_revocation_failure_does_not_claim_success(self):
        self.request("issue")
        self.reject_revoked = False
        with self.assertRaisesRegex(Failure, "credential-revocation-unverified"):
            self.request("revoke")
        state = decode((Path(self.temp.name) / (self.lease + ".json")).read_bytes())
        self.assertEqual(state["state"], "deleted")
        self.reject_revoked = True
        self.assertTrue(self.request("revoke")["revoked"])
        self.assertEqual(sum(call[0] == "DELETE" for call in self.calls), 1)

    def test_no_secret_in_lease_state(self):
        self.request("issue")
        raw = (Path(self.temp.name) / (self.lease + ".json")).read_text()
        self.assertNotIn("CANARY", raw)

    def test_cross_role_lease_rejected(self):
        self.request("issue")
        with self.assertRaises(Failure):
            self.request("read", uid=1002, role="production")

    def test_arbitrary_project_injection(self):
        with self.assertRaises(Failure):
            self.broker.handle(1001, {"operation": "issue", "role": "test", "lease": self.lease,
                                      "project": "proj_other"})
        self.assertEqual(self.calls, [])

    def test_unrecognized_operation(self):
        with self.assertRaises(Failure):
            self.request("delete-project")


class PolicyTests(unittest.TestCase):
    def test_maintenance_boundary(self):
        zone = ZoneInfo("America/Bogota")
        self.assertFalse(maintenance_open(datetime(2026, 9, 6, 1, 59, tzinfo=zone)))
        self.assertTrue(maintenance_open(datetime(2026, 9, 6, 2, 0, tzinfo=zone)))
        self.assertTrue(maintenance_open(datetime(2026, 9, 6, 3, 30, tzinfo=zone)))
        self.assertFalse(maintenance_open(datetime(2026, 9, 6, 3, 31, tzinfo=zone)))
        self.assertFalse(maintenance_open(datetime(2026, 9, 7, 2, 0, tzinfo=zone)))

    def test_ssh_has_no_interactive_or_forwarding_fallback(self):
        args = ssh_options({"target": "deploy@10.0.30.10", "identity_file": "/keys/deploy",
                            "known_hosts": "/keys/hosts"})
        for expected in ("BatchMode=yes", "StrictHostKeyChecking=yes", "ClearAllForwardings=yes", "-T"):
            self.assertIn(expected, args)
        self.assertNotIn("-tt", args)
        self.assertEqual(args[-1], "deploy@10.0.30.10")

    def test_missing_config_fails_without_ssh_or_state(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(["bash", str(root / "hermes-deploy.sh"), "upgrade", "--non-interactive",
                                 "--config", "/nonexistent/config.json"], stdin=subprocess.DEVNULL,
                                capture_output=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'"ok":false', result.stdout)
        self.assertNotIn(b"sudo", result.stderr)


class HostStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.host = host_module.Host.__new__(host_module.Host)
        self.host.directory = root
        self.host.release_id = "test-1"
        self.host.manifest = {"image": "image", "baseline_sha256": "baseline", "transaction": "packages/transaction.json"}
        self.host.policy = {}
        self.host.journal = root / "state.json"
        self.host.snapshot = root / "snapshot.tar"
        self.host.state = {"phase": "new"}
        for name in ("preflight", "run", "healthy", "boot_id", "package_baseline", "replay_packages", "require_complete", "wait_health"):
            patcher = patch.object(host_module, name)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)
        self.boot_id.return_value = "boot-1"
        self.package_baseline.return_value = "baseline"
        for name in ("install_boot", "install_runtime", "acceptance", "rollback"):
            patcher = patch.object(self.host, name)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def test_no_packages_before_backup_and_credential(self):
        with self.assertRaises(Failure):
            self.host.advance()
        self.replay_packages.assert_not_called()
        self.install_runtime.assert_not_called()

    def test_baseline_mismatch_prevents_boot_and_package_mutation(self):
        self.host.state["phase"] = "credential-ready"
        self.package_baseline.return_value = "different"
        with self.assertRaisesRegex(Failure, "package-baseline-mismatch"):
            self.host.advance()
        self.install_boot.assert_not_called()
        self.replay_packages.assert_not_called()

    def test_offline_reboot_journal_before_reboot(self):
        self.host.state["phase"] = "credential-ready"
        result = self.host.advance()
        self.assertEqual(result["stage"], "reboot-pending")
        self.assertEqual(decode(self.host.journal.read_bytes())["boot_before"], "boot-1")
        self.replay_packages.assert_called_once()
        self.install_runtime.assert_not_called()

    def test_same_boot_does_not_skip_update_gate(self):
        self.host.state = {"phase": "reboot-pending", "boot_before": "boot-1"}
        self.assertEqual(self.host.advance()["stage"], "reboot-pending")
        self.install_runtime.assert_not_called()
        self.replay_packages.assert_not_called()

    def test_changed_boot_with_wrong_packages_fails(self):
        self.host.state = {"phase": "reboot-pending", "boot_before": "old-boot"}
        (self.host.directory / "packages").mkdir()
        (self.host.directory / "packages/installed-after.sha256").write_text("different")
        with self.assertRaisesRegex(Failure, "package-replay-result-mismatch"):
            self.host.advance()
        self.install_runtime.assert_not_called()

    def test_interrupted_package_staging_never_blindly_replays(self):
        self.host.state["phase"] = "package-staging"
        with self.assertRaisesRegex(Failure, "release-needs-recovery"):
            self.host.advance()
        self.replay_packages.assert_not_called()

    def test_matching_packages_without_offline_completion_cannot_install_runtime(self):
        self.host.state = {"phase": "reboot-pending", "boot_before": "old-boot"}
        (self.host.directory / "packages").mkdir()
        (self.host.directory / "packages/installed-after.sha256").write_text("baseline")
        self.require_complete.side_effect = Failure(75, "offline-package-recovery-required")
        with self.assertRaisesRegex(Failure, "offline-package-recovery-required"):
            self.host.advance()
        self.install_runtime.assert_not_called()

    def test_application_failure_rolls_back(self):
        self.host.state["phase"] = "runtime-pending"
        self.acceptance.side_effect = Failure(69, "bad-inference")
        with self.assertRaisesRegex(Failure, "application-rolled-back"):
            self.host.advance()
        self.rollback.assert_called_once()

    def test_pending_persistence_reboot_does_not_test_stopping_runtime(self):
        self.host.state = {"phase": "persistence-reboot", "runtime_boot_before": "boot-1"}
        self.acceptance.side_effect = Failure(69, "runtime-is-stopping")
        self.assertEqual(self.host.advance()["stage"], "persistence-reboot")
        self.acceptance.assert_not_called()
        self.rollback.assert_not_called()

    def test_success_requires_persistence_reboot(self):
        self.host.state["phase"] = "runtime-pending"
        self.assertEqual(self.host.advance()["stage"], "persistence-reboot")
        self.assertEqual(self.host.advance()["stage"], "persistence-reboot")
        self.boot_id.return_value = "boot-2"
        self.assertEqual(self.host.advance()["stage"], "closed")
        self.install_runtime.assert_called_once()
        self.wait_health.assert_called_once_with("image")

    def test_closed_rerun_checks_health_without_mutation(self):
        self.host.state["phase"] = "closed"
        self.assertEqual(self.host.advance()["stage"], "closed")
        self.healthy.assert_called_once()
        self.install_runtime.assert_not_called()
        self.replay_packages.assert_not_called()


class RollbackPrivilegeTests(unittest.TestCase):
    def test_config_backup_drops_root_authority(self):
        with patch("host.as_hermes", return_value=b"synthetic config") as execute:
            self.assertEqual(host_module.read_application_file(host_module.DATA / "config.yaml"), b"synthetic config")
            self.assertIn("--reuid=10000", execute.call_args.args[0])
            self.assertIn("--clear-groups", execute.call_args.args[0])

    def test_config_restore_drops_root_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path(directory)
            (previous / "complete").write_bytes(b"complete\n")
            (previous / "0").write_bytes(b"synthetic configuration\n")
            (previous / "files.json").write_text(json.dumps([
                {"path": str(previous / "data/config.yaml"), "exists": True, "index": "0",
                 "mode": 0o600, "uid": 1234, "gid": 1234}]))
            host = object.__new__(host_module.Host)
            host.previous = previous
            host.state = {"phase": "runtime-pending", "previous_active": False}
            with patch.object(host, "save", return_value={"stage": "rolled-back"}), \
                    patch("host.DATA", previous / "data"), \
                    patch("host.CREDENTIAL", previous / "absent-credential"), \
                    patch("host.service"), patch("host.run"), patch("host.as_hermes") as execute, \
                    patch("host.atomic") as root_write:
                self.assertEqual(host.rollback()["stage"], "rolled-back")
                root_write.assert_not_called()
                self.assertIn("--reuid=10000", execute.call_args.args[0])
                self.assertIn("--clear-groups", execute.call_args.args[0])
                self.assertEqual(execute.call_args.kwargs["data"], b"synthetic configuration\n")
                script = execute.call_args.args[0][-1]
            # A container UID can use the entered directory even when its host-home
            # ancestors cannot be traversed. Do not resolve paths through getcwd.
            prefix = "import os\ndef inaccessible(): raise PermissionError('private parent')\nos.getcwd=inaccessible\n"
            subprocess.run([sys.executable, "-c", prefix + script], cwd=previous,
                           input=b"restored configuration\n", check=True, capture_output=True)
            self.assertEqual((previous / "config.yaml").read_bytes(), b"restored configuration\n")
            self.assertEqual((previous / "config.yaml").stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(previous.glob(".rollback-*")), [])


class VulnerabilityTests(unittest.TestCase):
    def test_scan_accepts_canonical_docker_hub_name_and_isolates_registry(self):
        image = "docker.io/nousresearch/hermes-agent@sha256:" + "a" * 64
        report = {"Metadata": {"RepoDigests": [image.removeprefix("docker.io/")]},
                  "Results": [{"Vulnerabilities": []}]}
        with patch("gates.run", return_value=json.dumps(report).encode()) as execute:
            self.assertEqual(scan_image(image, [])["result"], "PASS")
        args = execute.call_args.args[0]
        self.assertIn("--cache-dir", args)
        self.assertIn("DOCKER_CONFIG", execute.call_args.kwargs["env"])

    def test_scan_rejects_same_digest_in_another_repository(self):
        image = "docker.io/nousresearch/hermes-agent@sha256:" + "a" * 64
        report = {"Metadata": {"RepoDigests": ["attacker/image@sha256:" + "a" * 64]},
                  "Results": [{"Vulnerabilities": []}]}
        with patch("gates.run", return_value=json.dumps(report).encode()):
            with self.assertRaisesRegex(Failure, "scan-image-mismatch"):
                scan_image(image, [])

    def setUp(self):
        self.image = "image@sha256:" + "a" * 64
        self.report = {"Results": [{"Vulnerabilities": [{"VulnerabilityID": "CVE-TEST", "Severity": "HIGH",
                                                        "PkgName": "test", "InstalledVersion": "1"}]}]}
        self.denial = {"id": "CVE-TEST", "package": "test", "assessed_at": "2026-01-01",
                       "reason": "synthetic unacceptable risk", "owner": "test"}

    def test_high_is_advisory(self):
        result = check_vulnerabilities(self.report, [], self.image)
        self.assertEqual(result["result"], "PASS")
        self.assertTrue(result["advisory"])
        self.assertEqual(result["findings"]["HIGH"], 1)

    def test_explicit_denylist_match_blocks(self):
        with self.assertRaisesRegex(Failure, "denied-vulnerability"):
            check_vulnerabilities(self.report, [self.denial], self.image)

    def test_critical_and_unknown_are_advisory(self):
        for severity in ("CRITICAL", "UNKNOWN"):
            self.report["Results"][0]["Vulnerabilities"][0]["Severity"] = severity
            self.assertEqual(check_vulnerabilities(self.report, [], self.image)["result"], "PASS")

    def test_denylist_applies_across_image_and_package_versions(self):
        self.report["Results"][0]["Vulnerabilities"][0]["InstalledVersion"] = "2"
        with self.assertRaisesRegex(Failure, "denied-vulnerability"):
            check_vulnerabilities(self.report, [self.denial], "new-image")

    def test_unrelated_package_is_not_denied(self):
        self.denial["package"] = "different"
        self.assertEqual(check_vulnerabilities(self.report, [self.denial], self.image)["result"], "PASS")

    def test_wildcard_package_denial(self):
        self.denial["package"] = "*"
        with self.assertRaisesRegex(Failure, "denied-vulnerability"):
            check_vulnerabilities(self.report, [self.denial], self.image)

    def test_old_disposition_schema_is_not_silently_accepted(self):
        self.denial["expires"] = "2099-01-01"
        with self.assertRaisesRegex(Failure, "invalid-denylist-entry"):
            check_vulnerabilities(self.report, [self.denial], self.image)

    def test_empty_scan_is_not_a_pass(self):
        with self.assertRaises(Failure):
            check_vulnerabilities({}, [], self.image)


class ControllerFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state_path = Path(self.temp.name) / "state.json"
        self.events = []
        self.phase = "new"
        self.advances = 0
        self.sha = hashlib.sha256(b"synthetic snapshot").hexdigest()
        for name in ("request", "fetch_backup", "backup_snapshot", "credential_request", "retain_backups"):
            patcher = patch.object(controller_module, name)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)
        patcher = patch.object(controller_module.time, "sleep")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.request.side_effect = self.remote
        self.fetch_backup.side_effect = lambda config, path, **kwargs: path.write_bytes(b"synthetic snapshot")
        self.backup_snapshot.return_value = {"snapshot": "a" * 64, "sha256": self.sha, "restore_verified": True}
        self.credential_request.return_value = {"key": "CANARY_PROVIDER_KEY"}
        self.retain_backups.side_effect = lambda history, snapshot, config: history

    def remote(self, config, action, **values):
        self.events.append(action)
        if action == "snapshot":
            self.phase = "snapshot-ready"
            return {"snapshot_sha256": self.sha}
        if action == "backup-verified":
            self.phase = "backup-verified"
        if action == "credential":
            self.phase = "credential-ready"
        if action == "upgrade":
            self.advances += 1
            self.phase = "reboot-pending" if self.advances == 1 else "closed"
        return {"ok": True, "stage": self.phase, "release_id": "test-1"}

    def test_full_no_input_flow_orders_backup_before_credentials(self):
        state = {"fingerprint": "f" * 64}
        result = controller_module.converge({"credential_socket": "/socket"}, {"release_id": "test-1"},
                                            "f" * 64, self.state_path, "upgrade", state)
        self.assertEqual(result["stage"], "closed")
        self.assertLess(self.events.index("backup-verified"), self.events.index("credential"))
        self.assertNotIn("CANARY", self.state_path.read_text())
        self.credential_request.assert_called_once()

    def test_resume_does_not_replace_credential(self):
        self.phase = "credential-ready"
        controller_module.converge({"credential_socket": "/socket"}, {"release_id": "test-1"},
                                   "f" * 64, self.state_path, "upgrade", {"lease": "a" * 32})
        self.credential_request.assert_not_called()
        self.backup_snapshot.assert_not_called()

    def test_failed_backup_never_delivers_key_or_replays_packages(self):
        self.backup_snapshot.side_effect = Failure(69, "backup-failed")
        with self.assertRaises(Failure):
            controller_module.converge({"credential_socket": "/socket"}, {"release_id": "test-1"},
                                       "f" * 64, self.state_path, "upgrade", {})
        self.credential_request.assert_not_called()
        self.assertNotIn("upgrade", self.events)

    def test_retire_previous_key_only_after_acceptance(self):
        state = {"previous_lease": "b" * 32}
        controller_module.converge({"credential_socket": "/socket"}, {"release_id": "test-1"},
                                   "f" * 64, self.state_path, "upgrade", state)
        self.assertEqual(self.credential_request.call_args.args[1], "revoke")
        self.assertNotIn("previous_lease", state)


class ResticIntegrationTests(unittest.TestCase):
    def test_encrypted_backup_roundtrip_and_owned_retention(self):
        # Real Restic with a disposable repository and synthetic data, never production credentials.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            password = root / "password"
            password.write_text("synthetic-test-password-only\n")
            password.chmod(0o600)
            repository = root / "repository"
            config = {"backup_repository": str(repository), "backup_password_file": str(password)}
            base = ["restic", "--no-cache", "--repo", str(repository), "--password-file", str(password)]
            subprocess.run(base + ["init"], stdin=subprocess.DEVNULL, capture_output=True, check=True)
            source = root / "hermes.tar"
            source.write_bytes(b"synthetic recovery canary\n")
            source.chmod(0o600)
            result = backup_snapshot(source, config, "test-1")
            self.assertTrue(result["restore_verified"])
            self.assertEqual(result["sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(retain_backups([result["snapshot"]], result["snapshot"], config), [result["snapshot"]])
            wrong = root / "wrong-password"
            wrong.write_text("wrong-password\n")
            wrong.chmod(0o600)
            denied = subprocess.run(["restic", "--no-cache", "--repo", str(repository), "--password-file", str(wrong), "snapshots"],
                                    stdin=subprocess.DEVNULL, capture_output=True)
            self.assertNotEqual(denied.returncode, 0)

    def test_retention_keeps_current_even_when_old(self):
        history = [f"{index:064x}" for index in range(12)]
        with patch("gates.run") as command:
            retained = retain_backups(history, history[0], {"backup_repository": "/repo", "backup_password_file": "/password"})
        self.assertIn(history[0], retained)
        self.assertEqual(retained[1:], history[-8:])
        forgotten = command.call_args.args[0]
        self.assertNotIn(history[0], forgotten)
        self.assertNotIn("--prune", forgotten)


class LabBootTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.directory = Path(self.work.name)
        self.uki = self.directory / "input.efi"
        self.uki.write_bytes(b"verified-uki")
        self.cert = self.directory / "input.crt"
        self.cert.write_bytes(b"certificate")
        self.key = self.directory / "input.pub"
        self.key.write_bytes(b"public-key")
        self.command_line = "root=/dev/mapper/vg_root-root rd.luks.uuid=123 rd.luks.options=tpm2-device=auto"
        self.files = {path: b"original-efi" for path in lab_boot.EFI_PATHS}
        self.files.update({"/hermes-tpm-stage": lab_boot.MARKER.encode(),
                           "/hermes-pcr-public-key.pem": self.key.read_bytes()})
        self.writes = []

    def fish(self, commands, writable=False):
        result = b""
        if writable:
            self.writes.extend(commands)
        for command in commands:
            operation, *args = command
            if operation == "filesize":
                result = str(len(self.files[args[0]])).encode()
            elif operation == "cat":
                result = self.files[args[0]]
            elif operation == "download":
                Path(args[1]).write_bytes(self.files[args[0]])
            elif operation == "is-file":
                result = b"true" if args[0] in self.files else b"false"
            elif operation == "upload":
                self.files[args[1]] = Path(args[0]).read_bytes()
            elif operation == "cp":
                self.files[args[1]] = self.files[args[0]]
            elif operation == "mv":
                self.files[args[1]] = self.files.pop(args[0])
            elif operation != "sync":
                self.fail("unexpected guestfish operation")
        return result

    def inject(self):
        with patch.object(lab_boot, "check_domain"), patch.object(lab_boot, "verify_uki", return_value=self.command_line):
            with patch.object(lab_boot, "guestfish", side_effect=self.fish):
                return lab_boot.inject("uuid", self.uki, self.cert, self.key, self.directory)

    def test_oversized_guest_file_is_rejected_before_download(self):
        with patch.object(lab_boot, "guestfish", return_value=b"999999999999") as fish:
            with self.assertRaisesRegex(Failure, "lab-export-too-large"):
                lab_boot.bounded_download("/oversized", self.directory / "output")
        self.assertEqual(fish.call_count, 1)
        self.assertFalse((self.directory / "output").exists())

    def test_cat_preserves_file_newline_without_guestfish_printer_newline(self):
        for content in (b"manifest", b"manifest\n"):
            with self.subTest(content=content), patch.object(
                    lab_boot, "guestfish", side_effect=[str(len(content)).encode(), content + b"\n"]):
                self.assertEqual(lab_boot.bounded_cat("/manifest"), content)
        for changed in (b"short", b"manifest\nX", b"manifest\n\n"):
            with self.subTest(changed=changed), patch.object(
                    lab_boot, "guestfish", side_effect=[b"8", changed]):
                with self.assertRaisesRegex(Failure, "lab-export-size-changed"):
                    lab_boot.bounded_cat("/manifest")

    def test_injection_verifies_copies_and_rerun_preserves_originals(self):
        command_line, sha = self.inject()
        self.assertEqual(command_line, self.command_line)
        self.assertEqual(sha, hashlib.sha256(self.uki.read_bytes()).hexdigest())
        for path in lab_boot.EFI_PATHS:
            self.assertEqual(self.files[path], self.uki.read_bytes())
            self.assertEqual(self.files[path + ".hermes-original"], b"original-efi")
        self.writes.clear()
        self.inject()
        self.assertEqual(self.writes, [])

    def test_corrupt_existing_backup_blocks_retry_before_replacement(self):
        self.files[lab_boot.EFI_PATHS[0] + ".hermes-original"] = b"partial-backup"
        with self.assertRaisesRegex(Failure, "efi-backup-copy-mismatch"):
            self.inject()
        self.assertEqual(self.writes, [])

    def test_wrong_enrolled_key_prevents_all_writes(self):
        self.files["/hermes-pcr-public-key.pem"] = b"different-enrollment"
        with self.assertRaisesRegex(Failure, "lab-enrolled-pcr-key-mismatch"):
            self.inject()
        self.assertEqual(self.writes, [])

    def test_missing_stage_marker_prevents_all_writes(self):
        self.files["/hermes-tpm-stage"] = b"legacy-fixture"
        with self.assertRaisesRegex(Failure, "lab-tpm-stage-marker-missing"):
            self.inject()
        self.assertEqual(self.writes, [])

    def test_failed_copy_preserves_boot_path_and_original_on_retry(self):
        normal = self.fish
        def corrupt(commands, writable=False):
            result = normal(commands, writable)
            for command in commands:
                if command[0] == "upload":
                    self.files[command[2]] = b"truncated"
            return result
        self.fish = corrupt
        with self.assertRaisesRegex(Failure, "efi-upload-copy-mismatch"):
            self.inject()
        self.assertEqual(self.files[lab_boot.EFI_PATHS[0]], b"original-efi")
        self.fish = normal
        self.inject()
        self.assertEqual(self.files[lab_boot.EFI_PATHS[0] + ".hermes-original"], b"original-efi")

    def test_running_domain_rejected_before_disk_access(self):
        with patch.object(lab_boot, "virsh", return_value=b"running"), patch.object(lab_boot, "run") as command:
            with self.assertRaisesRegex(Failure, "lab-domain-not-shut-off"):
                lab_boot.check_domain("11111111-1111-1111-1111-111111111111")
        command.assert_not_called()

    def test_wrong_domain_uuid_rejected(self):
        with patch.object(lab_boot, "virsh", side_effect=[b"shut off", b"<domain><name>lab-hermes-server</name><uuid>other</uuid></domain>"]):
            with self.assertRaisesRegex(Failure, "lab-domain-identity-mismatch"):
                lab_boot.check_domain("11111111-1111-1111-1111-111111111111")

    def test_domain_gate_accepts_only_isolated_enrolled_disk(self):
        uuid = "11111111-1111-1111-1111-111111111111"
        xml = (f'<domain><name>lab-hermes-server</name><uuid>{uuid}</uuid>'
               '<os><loader secure="yes" readonly="yes"/></os><devices>'
               '<disk type="file" device="disk"><driver type="qcow2"/>'
               f'<source file="{self.uki}"/><target dev="vda"/></disk>'
               '<tpm><backend type="emulator" version="2.0"/></tpm></devices></domain>')
        cases = [(xml, b"Managed save: no\nAutostart: disable\n", {"format": "qcow2"}, None),
                 (xml.replace('secure="yes"', 'secure="no"'), b"", {}, "lab-secure-firmware-required"),
                 (xml.replace('version="2.0"', 'version="1.2"'), b"", {}, "lab-tpm2-required"),
                 (xml, b"", {"format": "qcow2", "backing-filename": "other"}, "lab-disk-overlay-or-snapshot"),
                 (xml, b"Managed save: yes\nAutostart: disable\n", {"format": "qcow2"}, "lab-managed-save-present"),
                 (xml, b"Managed save: no\nAutostart: enable\n", {"format": "qcow2"}, "lab-autostart-must-be-disabled")]
        for document, details, info, error in cases:
            with self.subTest(error=error):
                def virsh(operation, *args):
                    return {"domstate": b"shut off", "dumpxml": document.encode(), "dominfo": details}[operation]
                with patch.object(lab_boot, "DISK", self.uki), patch.object(lab_boot, "virsh", side_effect=virsh):
                    with patch.object(lab_boot, "run", return_value=canonical(info)):
                        if error:
                            with self.assertRaisesRegex(Failure, error):
                                lab_boot.check_domain(uuid)
                        else:
                            lab_boot.check_domain(uuid)

    def test_guestfish_uses_stdin_and_unquoted_command_name(self):
        """Mocked command construction; runs with or without libguestfs installed."""
        with patch.object(lab_boot, "run", return_value=b"true") as command:
            lab_boot.guestfish([("is-file", "/EFI/BOOT/BOOTX64.EFI")])
        args = command.call_args.args[0]
        self.assertNotIn("-f", args)
        script = command.call_args.kwargs["data"]
        self.assertEqual(script, b'is-file "/EFI/BOOT/BOOTX64.EFI"\n')

    def test_write_rechecks_shutdown(self):
        with patch.object(lab_boot, "virsh", return_value=b"running"), patch.object(lab_boot, "run") as command:
            with self.assertRaisesRegex(Failure, "lab-domain-not-shut-off"):
                lab_boot.guestfish([("sync",)], writable=True)
        command.assert_not_called()

    def test_first_boot_requires_exact_command_line_and_secure_boot(self):
        self.uki.chmod(0o600)
        with patch.object(lab_boot, "check_domain"), patch.object(lab_boot, "virsh") as virsh:
            with patch.object(lab_boot, "run", side_effect=[self.command_line.encode(), b"SecureBoot enabled"]) as command:
                result = lab_boot.first_boot("uuid", self.command_line, self.uki, self.key, 1)
        self.assertTrue(result["first_boot_observed"])
        self.assertFalse(result["boot_verified"])
        virsh.assert_called_once_with("start", lab_boot.DOMAIN)
        for call in command.call_args_list:
            self.assertIn("StrictHostKeyChecking=yes", call.args[0])
            self.assertIn("BatchMode=yes", call.args[0])
            self.assertNotIn("console", call.args[0])

    def test_wrong_boot_never_reports_observation(self):
        self.uki.chmod(0o600)
        with patch.object(lab_boot, "check_domain"), patch.object(lab_boot, "virsh"):
            with patch.object(lab_boot, "run", return_value=b"wrong command line"):
                with self.assertRaisesRegex(Failure, "booted-command-line-mismatch"):
                    lab_boot.first_boot("uuid", self.command_line, self.uki, self.key, 1)

    def test_boot_timeout_is_bounded_and_does_not_force_stop_guest(self):
        self.uki.chmod(0o600)
        with patch.object(lab_boot, "check_domain"), patch.object(lab_boot, "virsh") as virsh:
            with patch.object(lab_boot.time, "monotonic", side_effect=[0, 2]):
                with self.assertRaisesRegex(Failure, "lab-first-boot-timeout"):
                    lab_boot.first_boot("uuid", self.command_line, self.uki, self.key, 1)
        virsh.assert_called_once_with("start", lab_boot.DOMAIN)

    def test_installer_and_wrong_pcr_keys_are_rejected(self):
        sections = {name: {} for name in (".linux", ".initrd", ".osrel", ".cmdline", ".pcrsig", ".pcrpkey")}
        sections[".pcrpkey"]["sha256"] = hashlib.sha256(self.key.read_bytes()).hexdigest()
        sections[".cmdline"]["text"] = "inst.ks=hd:LABEL=OEMDRV:/ks.cfg"
        with patch.object(lab_boot, "run", side_effect=[b"", canonical(sections)]):
            with self.assertRaisesRegex(Failure, "installed-encrypted-root-policy-required"):
                lab_boot.verify_uki(self.uki, self.cert, self.key)
        sections[".cmdline"]["text"] = self.command_line
        sections[".pcrpkey"]["sha256"] = "wrong"
        with patch.object(lab_boot, "run", side_effect=[b"", canonical(sections)]):
            with self.assertRaisesRegex(Failure, "installed-pcr-key-mismatch"):
                lab_boot.verify_uki(self.uki, self.cert, self.key)


if __name__ == "__main__":
    unittest.main()


class InstalledGuestfishParserTests(unittest.TestCase):
    """Optional probe of the installed guestfish parser; opt-in integration only.

    Kept separate from LabBootTests so the reviewed mocked command-construction
    assertion in the offline allowlist is never suppressed by a missing binary.
    """

    @integration_only("installed guestfish stdin parser probe")
    @unittest.skipUnless(shutil.which("guestfish"), "guestfish is not installed")
    def test_installed_guestfish_parses_stdin_commands(self):
        # Exercise the installed parser without starting an appliance or accessing a disk.
        probe = subprocess.run(["guestfish"], input=b"version\n", capture_output=True)
        self.assertEqual(probe.returncode, 0, "guestfish stdin parser unavailable")


class LabCandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.key = self.root / "pcr.pub"
        self.key.write_bytes(b"public")
        self.contents = {"linux": b"kernel", "initrd": b"initrd", "osrel": b"ID=fedora",
                         "cmdline": b"root=/dev/mapper/vg_root-root ro rd.lvm.lv=vg_root/root "
                         b"rd.luks.uuid=luks-11111111-1111-1111-1111-111111111111 rd.luks.options=tpm2-device=auto"}
        self.manifest = "".join(hashlib.sha256(raw).hexdigest() + "  " + name + "\n"
                                for name, raw in self.contents.items()).encode()

    def fish(self, commands):
        operation, path, *destination = commands[0]
        if operation == "cat":
            return lab_boot.MARKER.encode() if path == "/hermes-tpm-stage" else self.manifest
        raw = (lab_boot.MARKER.encode() if path == "/hermes-tpm-stage" else self.manifest
               if path.endswith("SHA256SUMS") else b"public" if path == "/hermes-pcr-public-key.pem"
               else self.contents[Path(path).name])
        if operation == "filesize":
            return str(len(raw)).encode()
        Path(destination[0]).write_bytes(raw)
        return b""

    def extract(self):
        with patch.object(lab_boot, "check_domain"), patch.object(lab_boot, "guestfish", side_effect=self.fish):
            return lab_candidate.extract("uuid", self.key, self.root)

    def test_extract_exact_public_inputs(self):
        result = self.extract()
        self.assertEqual(set(result), set(lab_candidate.NAMES))
        self.assertEqual(result["linux"].read_bytes(), b"kernel")

    def test_tampered_export(self):
        self.contents["initrd"] = b"tampered"
        with self.assertRaisesRegex(Failure, "boot-export-hash-mismatch"):
            self.extract()

    def test_missing_duplicate_and_traversal_records(self):
        original = self.manifest
        for manifest in (original.splitlines()[0] + b"\n", original + original.splitlines()[0] + b"\n",
                         original.replace(b"linux", b"../linux")):
            self.manifest = manifest
            with self.assertRaises(Failure):
                self.extract()

    def test_wrong_enrolled_key(self):
        self.key.write_bytes(b"other")
        with self.assertRaisesRegex(Failure, "lab-enrolled-pcr-key-mismatch"):
            self.extract()

    def test_construct_freezes_before_injection_and_keeps_certification_pending(self):
        destination = self.root / "candidate"
        identity = self.root / "identity.json"
        identity.write_text('{}')
        args = SimpleNamespace(destination=str(destination), domain_uuid="uuid", pcr_public_key=self.key,
                               stub=self.key, secureboot_key=self.key, certificate=self.key, pcr_key=self.key,
                               repository=self.root, transaction=self.root, host_identity=identity,
                               release_id="test", model="test", baseline="0" * 64, state_dir=self.root, start=False)
        sha = hashlib.sha256(b"uki").hexdigest()
        def build(inputs, output, *keys):
            output.write_bytes(b"uki")
            return {"uki_sha256": sha, "boot_verified": False}
        def prepare(*values):
            (destination / "boot").mkdir(parents=True)
            (destination / "boot/hermes.efi").write_bytes(values[3].read_bytes())
            return {"ok": True, "artifact_fingerprint": "bound"}
        with patch.object(lab_candidate, "extract", return_value={}), patch.object(boot_build, "build", side_effect=build):
            with patch.object(lab_boot, "verify_uki"), patch.object(lab_candidate.prepare, "prepare", side_effect=prepare):
                with patch.object(lab_boot, "inject", return_value=("cmdline", sha)) as inject:
                    result = lab_candidate.construct(args, self.root)
                    self.assertEqual(inject.call_args.args[1], destination / "boot/hermes.efi")
        self.assertFalse(result["boot_verified"])
        self.assertEqual(result["certification"], "pending")
        with patch.object(lab_candidate, "extract") as extract:
            with self.assertRaisesRegex(Failure, "candidate-destination-exists"):
                lab_candidate.construct(args, self.root)
            extract.assert_not_called()
