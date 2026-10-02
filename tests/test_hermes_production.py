"""Offline regressions: fake host commands, real temporary signatures/process trees."""

import atexit
import hashlib
import importlib.util
import io
import json
import os
import runpy
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from contextlib import ExitStack, contextmanager, nullcontext, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/hermes"))
from production import (  # noqa: E402
    bundle,
    client,
    commission,
    escrow,
    host,
    install,
    kickstart,
    media,
    operations,
    preflight,
    primitives,
    receivers,
    runtime,
    startup,
)
from production.operations import Transaction  # noqa: E402
from production.primitives import (  # noqa: E402
    Refused,
    atomic,
    canonical,
    decode,
    digest,
    lock,
    run,
    sha,
)

MANIFEST = "c" * 64
_ESCROW = {}


def escrow_material():
    """One throwaway RSA-3072 escrow key/certificate per test run (never a real key)."""
    if not _ESCROW:
        directory = Path(tempfile.mkdtemp(prefix="hermes-escrow-test-"))
        atexit.register(shutil.rmtree, directory, True)
        key, cert = directory / "escrow-key.pem", directory / "escrow-certificate.pem"
        run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:3072",
                "-noenc",
                "-days",
                "2",
                "-subj",
                "/CN=hermes-escrow-test",
                "-keyout",
                str(key),
                "-out",
                str(cert),
            ],
            timeout=300,
        )
        key.chmod(0o600)
        _ESCROW.update(directory=directory, key=key, cert=cert, pem=cert.read_text())
    return _ESCROW


def settings():
    return {
        "disk_id": "/dev/disk/by-id/virtio-HERMES_PROD_TEST",
        "disk_min_mib": 180000,
        "root_mib": 30720,
        "var_mib": 81920,
        "hermes_mib": 61440,
        "hostname": "hermes-test.example",
        "admin": "hermesadmin",
        "admin_public_key": "ssh-ed25519 " + "A" * 68,
        "timezone": "Etc/UTC",
        "kind": "production",
        "application_mode": "production",
        "escrow_certificate": escrow_material()["pem"],
        "deploy_public_key": "ssh-ed25519 " + "B" * 68,
        "deploy_from": "192.0.2.1/32",
        "artifact_budget_bytes": 2 * preflight.GIB,
        "state_budget_bytes": 2 * preflight.GIB,
        "restic_repository": "sftp:backup@backup.example:/backups/hermes",
    }


def config():
    return {
        "schema": 1,
        "kind": "production",
        "application_mode": "production",
        "machine_id": "a" * 32,
        "home_uuid": "12345678-1234-1234-1234-123456789012",
        "luks_uuid": "22345678-1234-1234-1234-123456789012",
        "ssh_host_sha256": "b" * 64,
        "artifact_budget_bytes": 2 * preflight.GIB,
        "state_budget_bytes": 2 * preflight.GIB,
        "restic_repository": "sftp:backup@backup.example:/backups/hermes",
        "restic_password_file": "/etc/hermes-production/restic-password",
        "deploy_public_key": "ssh-ed25519 " + "A" * 68,
        "deploy_from": "192.0.2.1/32",
    }


class ProductionPolicyTests(unittest.TestCase):
    def test_runtime_account_accepts_explicit_denial_with_supported_exit_statuses(self):
        for status in (0, 1):
            with self.subTest(status=status):
                self.check_runtime_sudo(
                    status, b"User hermes is not allowed to run sudo on hermes-qualification.\n"
                )

    def test_runtime_account_rejects_grants_ambiguous_output_and_errors(self):
        denied = b"User hermes is not allowed to run sudo on hermes-qualification.\n"
        for status, output in [
            (0, b"(ALL) ALL\n"),
            (0, b""),
            (2, denied),
            (1, b"sudo: a password is required\n"),
            (0, denied + b"    (root) /usr/bin/true\n"),
            (1, b"sudo: policy inspection failed; not allowed\n"),
        ]:
            with (
                self.subTest(status=status, output=output),
                self.assertRaisesRegex(Refused, "runtime-sudo"),
            ):
                self.check_runtime_sudo(status, output)

    def check_runtime_sudo(self, status, output):
        user = SimpleNamespace(
            pw_uid=1001, pw_gid=1001, pw_dir="/home/hermes", pw_shell="/usr/sbin/nologin"
        )
        with (
            patch.object(preflight.pwd, "getpwnam", return_value=user),
            patch.object(preflight.grp, "getgrall", return_value=[]),
            patch.object(preflight.grp, "getgrgid", return_value=SimpleNamespace(gr_name="hermes")),
            patch.object(preflight, "text", return_value="hermes LK"),
            patch.object(
                preflight,
                "run",
                return_value=SimpleNamespace(returncode=status, stdout=output, stderr=b""),
            ),
            patch.object(preflight, "subordinate"),
            patch.object(Path, "exists", return_value=False),
        ):
            self.assertIs(preflight.account(required=True), user)

    def test_system_user_manager_guard_runs_as_root_despite_user_template(self):
        with patch.object(host, "public_directory"), patch.object(host, "atomic") as write:
            host.mount_guard(config(), 1234)
        self.assertIn(
            b"ExecStartPre=+/usr/local/libexec/hermes-production/productionctl.py mount-check",
            write.call_args.args[1],
        )
        self.assertIn("user@1234.service.d", str(write.call_args.args[0]))

    def test_systemd259_omitted_no_pin_field_and_boot_drift_identity(self):
        metadata = {
            "keyslots": {"0": {}, "1": {}},
            "tokens": {"0": {"type": "systemd-tpm2", "tpm2-pcrs": [7], "tpm2-pcr-bank": "sha256"}},
        }
        row = "encrypted UUID=" + config()["luks_uuid"] + " none luks,tpm2-device=auto\n"

        def command(*argv):
            if argv[0] == "lsinitrd":
                return "systemd-cryptsetup tpm2-tss"
            if argv[0] == "mokutil":
                return "SecureBoot enabled"
            return "PCR7 measured digest"

        with (
            patch.object(preflight.Path, "read_text", return_value=row),
            patch.object(preflight, "sha", return_value="a" * 64),
            patch.object(preflight, "text", side_effect=command),
        ):
            first = preflight.boot(config(), metadata)
            self.assertEqual(len(first), 64)
            with patch.object(preflight.platform, "release", return_value="updated-kernel"):
                self.assertNotEqual(first, preflight.boot(config(), metadata))
            metadata["tokens"]["0"]["tpm2_pcrlock"] = True
            with self.assertRaisesRegex(Refused, "tpm-policy"):
                preflight.boot(config(), metadata)

    def test_interrupted_journal_blocks_boot_and_dead_lease_blocks_application(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lease, ready, journal = (root / n for n in ("lease", "ready", "journal"))

            def reader(path, **kw):
                return json.loads(path.read_text())

            with (
                patch.multiple(startup, LEASE=lease, READY=ready, JOURNAL=journal),
                patch.object(startup, "read_json", side_effect=reader),
                patch.object(startup, "boot_id", return_value="boot"),
                patch.object(startup, "process_identity", return_value="start"),
                patch.object(startup.os, "geteuid", return_value=0),
            ):
                journal.write_bytes(canonical({"stage": "configuration"}))
                with self.assertRaisesRegex(Refused, "blocks-boot"):
                    startup.guard()
                with startup.operation():
                    startup.guard()  # Recovery user manager may start.
                    with patch.object(startup.os, "geteuid", return_value=1000):
                        with self.assertRaisesRegex(Refused, "transaction"):
                            startup.guard()
                    startup.allow_application()
                    with patch.object(startup.os, "geteuid", return_value=1000):
                        startup.guard()
                self.assertFalse(ready.exists())
                lease.write_bytes(
                    canonical(
                        {
                            "pid": 1,
                            "boot": "older-boot",
                            "start": "start",
                            "allow_application": True,
                        }
                    )
                )
                with self.assertRaisesRegex(Refused, "dead-startup-lease"):
                    startup.guard()

    def test_mount_guard_rejects_missing_mount_or_wrong_uuid_before_storage_probe(self):
        for mounted in (
            {"target": "/", "fstype": "xfs", "uuid": config()["home_uuid"]},
            {"target": "/home/hermes", "fstype": "xfs", "uuid": "wrong"},
        ):
            with (
                patch.object(host, "read_json", return_value=config()),
                patch.object(host.preflight, "mount", return_value=mounted),
                patch.object(host.preflight, "encrypted") as encrypted,
            ):
                with self.assertRaisesRegex(Refused, "mount-absent"):
                    host.check_mount()
                encrypted.assert_not_called()

    def test_pcr_policy_rejects_unbound_sha1_pin_and_missing_recovery_before_commands(self):
        good = {
            "keyslots": {"0": {}, "1": {}},
            "tokens": {
                "1": {
                    "type": "systemd-tpm2",
                    "tpm2-pcrs": [7],
                    "tpm2-pcr-bank": "sha256",
                    "tpm2-pin": False,
                }
            },
        }
        variants = []
        import copy

        for field, value in (
            ("tpm2-pcrs", []),
            ("tpm2-pcrs", [11]),
            ("tpm2-pcr-bank", "sha1"),
            ("tpm2-pin", True),
        ):
            bad = copy.deepcopy(good)
            bad["tokens"]["1"][field] = value
            variants.append(bad)
        variants.append(good | {"keyslots": {"1": {}}})
        with patch.object(preflight, "run") as command:
            for value in variants:
                with self.assertRaises(Refused):
                    preflight.boot(config(), value)
            command.assert_not_called()

    def test_production_cannot_select_synthetic_mode(self):
        with self.assertRaisesRegex(Refused, "application-mode"):
            preflight.configuration(config() | {"application_mode": "synthetic"})
        preflight.configuration(config() | {"kind": "fixture", "application_mode": "synthetic"})

    def test_rendered_kickstart_parses_as_fedora44(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "production.ks"
            path.write_text(kickstart.render(settings(), MANIFEST))
            result = run(
                [str(ROOT / ".venv/bin/ksvalidator"), "--version", "F44", str(path)], check=False
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_kickstart_refuses_reserved_fedora_and_service_administrators(self):
        for name in (
            "root",
            "bin",
            "daemon",
            "adm",
            "lp",
            "sync",
            "shutdown",
            "halt",
            "mail",
            "operator",
            "games",
            "ftp",
            "nobody",
            "hermes",
            "hermes-deploy",
        ):
            with self.subTest(name=name), self.assertRaisesRegex(Refused, "invalid-admin"):
                kickstart.render(settings() | {"admin": name}, MANIFEST)

    def test_kickstart_refuses_existing_installer_account_before_storage(self):
        rendered = kickstart.render(settings(), MANIFEST)
        pre = rendered.split("%pre --interpreter=/bin/bash --erroronfail\n")[1].split("%end")[0]
        guard = pre.split("<<'HERMES_ADMIN_UNUSED'\n")[1].split("\nHERMES_ADMIN_UNUSED")[0]
        with patch("pwd.getpwnam", side_effect=KeyError):
            exec(guard, {})
        with (
            patch("pwd.getpwnam", return_value=object()),
            self.assertRaisesRegex(SystemExit, "already exists"),
        ):
            exec(guard, {})

    def test_kickstart_verifies_human_admin_identity_and_public_key(self):
        rendered = kickstart.render(settings(), MANIFEST)
        guard = rendered.split("<<'HERMES_ADMIN_VERIFY'\n")[1].split("\nHERMES_ADMIN_VERIFY")[0]
        account = dict(
            pw_name="hermesadmin",
            pw_uid=1000,
            pw_gid=1000,
            pw_dir="/home/hermesadmin",
            pw_shell="/bin/bash",
        )
        home = Path(account["pw_dir"])
        paths = {
            Path("/home"): dict(st_uid=0, st_gid=0, st_mode=stat.S_IFDIR | 0o755),
            home: dict(st_uid=1000, st_gid=1000, st_mode=stat.S_IFDIR | 0o700),
            home / ".ssh": dict(st_uid=1000, st_gid=1000, st_mode=stat.S_IFDIR | 0o700),
            home / ".ssh/authorized_keys": dict(
                st_uid=1000, st_gid=1000, st_mode=stat.S_IFREG | 0o600
            ),
        }

        def verify(changes=None, groups=None, files=None, key=None, label_exit=0):
            observed = paths | (files or {})
            with (
                patch("pwd.getpwnam", return_value=SimpleNamespace(**(account | (changes or {})))),
                patch("grp.getgrnam", return_value=SimpleNamespace(gr_gid=10)),
                patch("os.getgrouplist", return_value=[1000, 10] if groups is None else groups),
                patch("pathlib.Path.lstat", lambda path: SimpleNamespace(**observed[path])),
                patch(
                    "pathlib.Path.read_text",
                    return_value=settings()["admin_public_key"] + "\n" if key is None else key,
                ),
                patch("subprocess.run", return_value=SimpleNamespace(returncode=label_exit)),
            ):
                exec(guard, {})

        verify()
        for changes in (
            {"pw_uid": 11},
            {"pw_gid": 0},
            {"pw_dir": "/root"},
            {"pw_shell": "/usr/sbin/nologin"},
        ):
            with self.subTest(changes=changes), self.assertRaises(SystemExit):
                verify(changes=changes)
        for arguments in (
            {"groups": [1000]},
            {"key": "ssh-ed25519 wrong\n"},
            {"label_exit": 1},
            {"files": {home / ".ssh": paths[home / ".ssh"] | {"st_mode": stat.S_IFLNK | 0o777}}},
            {
                "files": {
                    home / ".ssh/authorized_keys": paths[home / ".ssh/authorized_keys"]
                    | {"st_uid": 0}
                }
            },
            {
                "files": {
                    home / ".ssh/authorized_keys": paths[home / ".ssh/authorized_keys"]
                    | {"st_mode": stat.S_IFREG | 0o666}
                }
            },
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                verify(**arguments)

    def test_host_settings_reject_secret_urls_extra_fields_and_unrestricted_sources(self):
        self.assertEqual(preflight.configuration(config()), config())
        for key, value in (
            ("restic_repository", "sftp:password@host:bad"),
            ("deploy_from", "0.0.0.0/0"),
            ("secret", "never-echo-me"),
            ("artifact_budget_bytes", True),
            ("home_uuid", "../etc"),
        ):
            bad = config() | {key: value}
            with self.subTest(key=key), self.assertRaises(Refused) as error:
                preflight.configuration(bad)
            self.assertNotIn("never-echo-me", str(error.exception))

    def test_storage_walk_requires_expected_encrypted_linear_ancestry(self):
        tree = {
            "blockdevices": [
                {
                    "name": "/dev/mapper/vg-home",
                    "type": "lvm",
                    "children": [
                        {
                            "name": "/dev/mapper/crypt",
                            "type": "crypt",
                            "children": [{"name": "/dev/vda3", "type": "part"}],
                        }
                    ],
                }
            ]
        }

        def command(args, **kwargs):
            if args[0] == "lsblk":
                result = tree
            elif args[:2] == ["cryptsetup", "luksDump"]:
                result = {"keyslots": {"0": {"type": "luks2"}}}
            else:
                raise AssertionError(args)
            return SimpleNamespace(stdout=canonical(result))

        with (
            patch.object(preflight, "run", side_effect=command),
            patch.object(preflight, "text", side_effect=["linear", config()["luks_uuid"]]),
        ):
            self.assertEqual(
                preflight.encrypted("/dev/mapper/vg-home", config()["luks_uuid"])[0], "/dev/vda3"
            )
        with (
            patch.object(preflight, "run", side_effect=command),
            patch.object(preflight, "text", return_value="thin"),
        ):
            with self.assertRaisesRegex(Refused, "nonlinear"):
                preflight.encrypted("/dev/mapper/vg-home", config()["luks_uuid"])
        tree["blockdevices"][0] = {"name": "/dev/vda", "type": "disk"}
        with (
            patch.object(preflight, "run", side_effect=command),
            self.assertRaisesRegex(Refused, "unencrypted"),
        ):
            preflight.encrypted("/dev/vda", config()["luks_uuid"])

    def test_subordinate_ids_reject_overlap_small_and_missing_ranges(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "subuid"
            for content in (
                "hermes:100000:65536\nother:120000:65536\n",
                "hermes:100000:10\n",
                "other:100000:65536\n",
            ):
                path.write_text(content)
                with self.assertRaises(Refused):
                    preflight.subordinate(path, 1000)
            path.write_text("hermes:100000:65536\nother:165536:65536\n")
            preflight.subordinate(path, 1000)

    def test_credentials_reject_allow_all_duplicates_extra_providers_and_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "env"
            content = "DEEPSEEK_API_KEY=synthetic\nTELEGRAM_BOT_TOKEN=synthetic\nTELEGRAM_ALLOWED_USERS=12345\n"
            path.write_text(content)
            path.chmod(0o600)
            runtime.credentials(path)
            for suffix in (
                "GATEWAY_ALLOW_ALL_USERS=true\n",
                "DEEPSEEK_API_KEY=duplicate\n",
                "OPENAI_API_KEY=synthetic\n",
            ):
                path.write_text(content + suffix)
                with self.assertRaises(Refused):
                    runtime.credentials(path)
            path.write_text(content.replace("12345", "*"))
            with self.assertRaises(Refused):
                runtime.credentials(path)
            link = Path(temporary) / "link"
            link.symlink_to(path)
            with self.assertRaises(Refused):
                runtime.credentials(link)

    def test_container_managed_api_key_allowed_only_in_the_stored_environment(self):
        base = "DEEPSEEK_API_KEY=k\nTELEGRAM_BOT_TOKEN=1:t\nTELEGRAM_ALLOWED_USERS=42\n"
        stored = base + "API_SERVER_ENABLED=false\nHERMES_DASHBOARD=0\nAPI_SERVER_KEY=generated\n"
        runtime.credential_text(base)
        runtime.credential_text(stored, container_managed=True)
        with self.assertRaisesRegex(Refused, "unexpected-credential-fields"):
            runtime.credential_text(stored)
        with self.assertRaisesRegex(Refused, "unsafe-profile-environment"):
            runtime.credential_text(
                stored.replace("API_SERVER_ENABLED=false", "API_SERVER_ENABLED=true"),
                container_managed=True,
            )
        for bad in ("API_SERVER_KEY=\n", "API_SERVER_KEY=a b\n"):
            with self.subTest(bad=bad), self.assertRaises(Refused):
                runtime.credential_text(base + bad, container_managed=True)
        with self.assertRaisesRegex(Refused, "unexpected-credential-fields"):
            runtime.credential_text(base + "OPENAI_API_KEY=x\n", container_managed=True)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / ".env"
            path.write_text(stored)
            path.chmod(0o600)
            runtime.credentials(path)
            with self.assertRaisesRegex(Refused, "unexpected-credential-fields"):
                runtime.credentials(path, container_managed=False)

    def test_kickstart_targets_only_explicit_disk_and_contains_no_secrets(self):
        rendered = kickstart.render(settings(), MANIFEST)
        disk = settings()["disk_id"]
        self.assertIn("ignoredisk --only-use=" + disk, rendered)
        self.assertIn("clearpart --all --initlabel --disklabel=gpt --drives=" + disk, rendered)
        self.assertIn("--encrypted --luks-version=luks2", rendered)
        self.assertIn("logvol /home/hermes --fstype=xfs", rendered)
        # Only the %pre generator names the option, with a runtime-substituted value.
        self.assertEqual(rendered.count("--passphrase"), 1)
        self.assertIn("--passphrase=%s", rendered)
        for forbidden in (
            "--password",
            "--iscrypted",
            "hermes-e2e-fixture",
            "zerombr",
            "vda",
            "BEGIN CERTIFICATE",
            "PRIVATE KEY",
        ):
            self.assertNotIn(forbidden, rendered)
        self.assertIn(MANIFEST, rendered)
        self.assertIn("%include /dev/shm/hermes-install/part.ks", rendered)
        self.assertNotIn("\ncdrom\n", rendered)
        self.assertIn("firewall --enabled --service=ssh --remove-service=cockpit\n", rendered)
        self.assertIn("services --enabled=sshd,chronyd --disabled=cockpit.socket\n", rendered)
        self.assertTrue(rendered.rstrip().endswith("reboot --eject"))
        for disk in (
            "/dev/vda",
            "/dev/disk/by-id/wwn-*",
            "/dev/disk/by-id/wwn-test-part1",
            "$(id)",
        ):
            with self.assertRaises(Refused):
                kickstart.render(settings() | {"disk_id": disk}, MANIFEST)

    def test_kickstart_requires_final_secret_copy_suppression_before_install(self):
        rendered = kickstart.render(settings(), MANIFEST)
        guard = rendered.split("<<'HERMES_NOSAVE'\n", 1)[1].split("\nHERMES_NOSAVE", 1)[0]
        for value in ("all_ks", "all"):
            with patch("pathlib.Path.read_text", return_value=f"quiet inst.nosave={value}"):
                exec(guard, {})
        for cmdline in (
            "quiet",
            "inst.nosave=output_ks",
            "inst.nosave=logs",
            "inst.nosave=all_ks inst.nosave=input_ks",
            "inst.nosave=all_ks inst.nosave=all_ks",
            "unrelated=inst.nosave=all_ks",
        ):
            with (
                self.subTest(cmdline=cmdline),
                patch("pathlib.Path.read_text", return_value=cmdline),
                self.assertRaises(SystemExit),
            ):
                exec(guard, {})
        self.assertNotIn("rm -f /root/anaconda-ks.cfg", rendered)

    def test_dvd_missing_packages_are_mandatory_and_install_failure_stops_post(self):
        rendered = kickstart.render(settings(), MANIFEST)
        packages = rendered.split("%packages\n", 1)[1].split("%end", 1)[0].splitlines()
        self.assertNotIn("restic", packages)
        self.assertNotIn("tpm2-tools", packages)
        for package in ("dnf5", "fedora-repos", "fedora-gpg-keys"):
            self.assertIn(package, packages)
        header = "%post --nochroot --interpreter=/bin/bash --erroronfail\n"
        script = rendered.split(header, 1)[1].split("%end", 1)[0]
        self.assertNotIn("--ignoremissing", rendered)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # mkdir/cp/chmod would touch the real /mnt/sysroot; they are no-ops here.
            for name in ("mkdir", "cp", "chmod"):
                (root / name).write_text("#!/bin/sh\nexit 0\n")
                (root / name).chmod(0o700)
            chroot = root / "chroot"
            chroot.write_text(
                f"#!{sys.executable}\n"
                "import json, os, sys\n"
                "with open(os.environ['HERMES_TEST_COMMANDS'], 'a') as stream:\n"
                "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "sys.exit(int(os.environ['HERMES_TEST_INSTALL_EXIT']) "
                "if 'dnf5' in sys.argv else 0)\n"
            )
            chroot.chmod(0o700)
            for code in (0, 23):
                log = root / f"commands-{code}.jsonl"
                result = subprocess.run(
                    ["bash", "-c", script],
                    env=os.environ
                    | {
                        "PATH": str(root) + os.pathsep + os.defpath,
                        "HERMES_TEST_COMMANDS": str(log),
                        "HERMES_TEST_INSTALL_EXIT": str(code),
                    },
                    capture_output=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, code)
                calls = [json.loads(line) for line in log.read_text().splitlines()]
                dnf = [
                    "/mnt/sysroot",
                    "timeout",
                    "--signal=TERM",
                    "--kill-after=10s",
                    "1800s",
                    "dnf5",
                    "--releasever=44",
                    "--disable-repo=*",
                    "--enable-repo=fedora",
                    "--enable-repo=updates",
                    "--setopt=fedora.gpgcheck=1",
                    "--setopt=updates.gpgcheck=1",
                    "--assumeyes",
                ]
                self.assertEqual(calls[0], [*dnf, "upgrade", "--exclude=shim-*"])
                if code:
                    self.assertEqual(len(calls), 1)
                else:
                    install = [*dnf[:4], "600s", *dnf[5:]]
                    self.assertEqual(calls[1], [*install, "install", "restic", "tpm2-tools"])
                    self.assertEqual(
                        calls[2], ["/mnt/sysroot", "rpm", "-q", "restic", "tpm2-tools"]
                    )

    def test_installer_environment_sections_avoid_commands_the_image_lacks(self):
        rendered = kickstart.render(settings(), MANIFEST)
        sections = [
            part.split("%end", 1)[0]
            for part in rendered.split("\n%")[1:]
            if part.startswith(("pre ", "post --nochroot"))
        ]
        self.assertEqual(len(sections), 4)
        for section in sections:
            for line in section.splitlines():
                word = line.strip().split(" ", 1)[0].lstrip("(")
                with self.subTest(line=line):
                    self.assertNotIn(word, {"install", "timeout", "clear"})

    def test_dispatch_has_no_shell_path_or_unsigned_script_operation(self):
        with (
            patch.object(host.os, "geteuid", return_value=0),
            patch.object(host, "read_json", return_value=config()),
            patch.object(host.preflight, "enforce") as enforce,
        ):
            for request in (
                {"operation": "exec", "apply": True},
                {"operation": "deploy", "apply": True, "script": "/tmp/payload"},
                {"operation": "rollback", "apply": "yes"},
            ):
                with self.assertRaises(Refused):
                    host.dispatch(io.BytesIO(canonical(request)))
            enforce.assert_not_called()

    def test_preview_never_loads_backend_or_receives_archive(self):
        with (
            patch.object(host.os, "geteuid", return_value=0),
            patch.object(host, "read_json", return_value=config()),
            patch.object(host.preflight, "enforce"),
            patch.object(host, "Backend") as backend,
        ):
            result = host.dispatch(
                io.BytesIO(canonical({"operation": "upgrade", "apply": False}) + b"not-a-tar")
            )
            self.assertEqual(result["status"], "PREVIEW")
            backend.assert_not_called()


class ProductionBundleFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.key = self.root / "signing"
        run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(self.key)])
        self.signers = self.root / "allowed"
        self.signers.write_text(bundle.SIGNER + " " + self.key.with_suffix(".pub").read_text())
        self.sources = self.root / "repo"
        base = self.sources / "scripts/hermes"
        base.mkdir(parents=True)
        for name in (
            "profile-deploy.py",
            "lab_profile.py",
            "productionctl.py",
            "production-launcher.py",
            "manual/manifest.yaml",
            "manual/config/profile-contract.yaml",
            "production/__init__.py",
            "lab-profiles/baseline.json",
        ):
            target = base / name
            target.parent.mkdir(exist_ok=True, parents=True)
            target.write_bytes((ROOT / "scripts/hermes" / name).read_bytes())
        for source in (ROOT / "scripts/hermes/production").glob("*.py"):
            shutil.copyfile(source, base / "production" / source.name)
        docs = self.sources / "docs"
        docs.mkdir()
        (docs / "HERMES_PRODUCTION_DEPLOYMENT.md").write_text("Fixture documentation.\n")
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        for name in ("gateway", "worker"):
            (self.artifacts / (name + ".oci")).write_bytes(b"synthetic-oci")
        profile = json.loads((base / "lab-profiles/baseline.json").read_text())
        metadata = {
            "gateway_ref": profile["gateway_image"],
            "gateway_id": "sha256:" + "a" * 64,
            "worker_id": "sha256:" + "b" * 64,
            "packages": ["podman-test"],
            "files": {
                n + ".oci": sha(self.artifacts / (n + ".oci")) for n in ("gateway", "worker")
            },
        }
        (self.artifacts / "manifest.json").write_bytes(canonical(metadata))
        self.archive = self.root / "release.tar"
        self.root_patch = patch.object(bundle, "ROOT", self.sources)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.result = bundle.build(self.artifacts, self.archive, self.key)

    def unpack(self, path=None, production=False):
        with (path or self.archive).open("rb") as stream:
            return bundle.unpack(stream, self.root / "result", self.signers, production=production)


class ProductionBundleTests(ProductionBundleFixture):
    def test_real_signature_roundtrip_and_candidate_production_refusal(self):
        with self.assertRaisesRegex(Refused, "not-qualified"):
            self.unpack(production=True)
        self.assertFalse((self.root / "result").exists())
        manifest = self.unpack()
        self.assertEqual(bundle.identity(manifest), self.result["artifact_sha256"])
        self.assertEqual(manifest["stage"], "candidate")

    def test_tampered_artifact_and_duplicate_link_paths_rejected(self):
        for kind in ("bytes", "duplicate", "symlink", "escape"):
            corrupt = self.root / (kind + ".tar")
            with tarfile.open(self.archive) as source, tarfile.open(corrupt, "w") as output:
                for member in source:
                    data = source.extractfile(member).read()
                    if kind == "bytes" and member.name == "images/worker.oci":
                        data = b"X" * len(data)
                    output.addfile(member, io.BytesIO(data))
                if kind != "bytes":
                    extra = tarfile.TarInfo(
                        "manifest.json"
                        if kind == "duplicate"
                        else "../escape"
                        if kind == "escape"
                        else "source/link"
                    )
                    if kind == "symlink":
                        extra.type = tarfile.SYMTYPE
                        extra.linkname = "/etc/shadow"
                    output.addfile(extra)
            with self.subTest(kind=kind), self.assertRaises(Refused):
                self.unpack(corrupt)
            self.assertFalse((self.root / "result").exists())

    def test_receiver_budget_bounds_copy_before_extraction(self):
        with self.archive.open("rb") as source, self.assertRaisesRegex(Refused, "too-large"):
            bundle.unpack(source, self.root / "result", self.signers, max_bytes=128)
        self.assertFalse((self.root / "result").exists())

    def test_wrong_trust_and_stale_qualification_rejected(self):
        self.signers.write_text("wrong-identity " + self.key.with_suffix(".pub").read_text())
        with self.assertRaises(Refused):
            self.unpack()
        proof = self.root / "proof.json"
        proof.write_bytes(
            canonical(
                {
                    "artifact_sha256": "c" * 64,
                    "gates": dict.fromkeys(bundle.GATES, "PASS"),
                    "reports": dict.fromkeys(bundle.GATES, "d" * 64),
                }
            )
        )
        with self.assertRaisesRegex(Refused, "stale-qualification"):
            bundle.build(self.artifacts, self.root / "new.tar", self.key, evidence=proof)

    def test_exact_candidate_requires_all_gates_and_retains_report(self):
        proof = self.root / "proof.json"
        report = {
            "artifact_sha256": self.result["artifact_sha256"],
            "gates": dict.fromkeys(bundle.GATES, "PASS"),
            "reports": dict.fromkeys(bundle.GATES, "d" * 64),
        }
        report["gates"]["boot"] = "NOT_RUN"
        proof.write_bytes(canonical(report))
        with self.assertRaisesRegex(Refused, "not-qualified"):
            bundle.build(self.artifacts, self.root / "qualified.tar", self.key, evidence=proof)
        report["gates"]["boot"] = "PASS"
        proof.write_bytes(canonical(report))
        path = self.root / "qualified.tar"
        bundle.build(self.artifacts, path, self.key, evidence=proof)
        self.assertEqual(self.unpack(path, production=True)["qualification"]["report"], report)


class ProductionReceiverTests(ProductionBundleFixture):
    """Real file modes, signed release checks and tar recovery; OS identity/services mocked."""

    def test_namespace_initialization_runs_under_user_manager_and_requires_rootless(self):
        backend = self.backend()
        for output, expected in ((b"true\n", True), (b"false\n", False), (b"", False)):
            with (
                self.subTest(output=output),
                patch.object(
                    backend, "user", return_value=SimpleNamespace(stdout=output, returncode=0)
                ) as user,
            ):
                if expected:
                    backend.initialize_namespace()
                else:
                    with self.assertRaisesRegex(Refused, "runtime-namespace"):
                        backend.initialize_namespace()
                argv = user.call_args.args
                self.assertEqual(argv[0], "systemd-run")
                self.assertIn("--user", argv)
                self.assertIn("--wait", argv)
                self.assertIn("--pipe", argv)
                self.assertIn("--property=Type=oneshot", argv)
                self.assertIn("--property=TimeoutStartSec=120s", argv)
                self.assertIn("--property=KillMode=control-group", argv)
                self.assertEqual(
                    argv[-4:],
                    ("/usr/bin/podman", "info", "--format", "{{.Host.Security.Rootless}}"),
                )
                self.assertEqual(user.call_args.kwargs["timeout"], 0)

    def test_namespace_initialization_failure_precedes_transaction_recovery(self):
        backend = self.backend()
        events = []
        backend.initialize_namespace = lambda: events.append("namespace")
        transaction = SimpleNamespace(
            rollback=lambda: events.append("rollback") or {"status": "PASS"}
        )
        with (
            patch.object(host.os, "geteuid", return_value=0),
            patch.object(host, "STATE", self.state),
            patch.object(host, "lock", side_effect=lambda *a, **kw: nullcontext()),
            patch.object(host, "read_json", return_value=self.cfg),
            patch.object(host.preflight, "configuration", return_value=self.cfg),
            patch.object(host.preflight, "enforce", return_value={"status": "PASS"}),
            patch.object(host.startup, "operation", side_effect=nullcontext),
            patch.object(host, "Backend", return_value=backend),
            patch.object(host, "Transaction", return_value=transaction),
            patch.object(host, "run", side_effect=lambda *a, **kw: events.append("manager")),
        ):
            host.dispatch(io.BytesIO(canonical({"operation": "rollback", "apply": True})))
            self.assertEqual(events, ["manager", "namespace", "rollback"])
            events.clear()
            with patch.object(
                backend, "initialize_namespace", side_effect=Refused("namespace-failed")
            ):
                with self.assertRaisesRegex(Refused, "namespace-failed"):
                    host.dispatch(io.BytesIO(canonical({"operation": "rollback", "apply": True})))
            self.assertEqual(events, ["manager"])

    def setUp(self):
        super().setUp()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.owner = os.getuid()
        self.public_impl = primitives.public_directory
        self.root.chmod(0o755)
        self.install = self.root / "usr/local/libexec/hermes-production"
        self.state = self.root / "var/lib/hermes-production"
        self.home = self.root / "home/hermes"
        for path in (self.state, self.home):
            path.mkdir(parents=True, mode=0o700)
        for name in ("releases", "attempts", "backups"):
            (self.state / name).mkdir(mode=0o700)
        self.stack.enter_context(patch.object(receivers, "INSTALL", self.install))
        self.stack.enter_context(patch.object(runtime, "HOME", self.home))
        self.stack.enter_context(
            patch.object(runtime.pwd, "getpwnam", return_value=SimpleNamespace(pw_uid=self.owner))
        )
        # Only ownership differs in the unprivileged test filesystem. Keep the
        # real regular-file type/mode/ancestor checks and all hashes/signatures.
        for module in (receivers, runtime, host):
            self.stack.enter_context(
                patch.object(
                    module,
                    "regular",
                    side_effect=lambda path, **kw: primitives.regular(
                        path, private=kw.get("private", False)
                    ),
                )
            )
            if hasattr(module, "read_json"):
                self.stack.enter_context(
                    patch.object(
                        module,
                        "read_json",
                        side_effect=lambda path, **kw: primitives.read_json(path),
                    )
                )
        for module in (receivers, host):
            self.stack.enter_context(
                patch.object(module, "public_directory", side_effect=self.public)
            )
        self.stack.enter_context(
            patch.object(
                host,
                "protected_directory",
                side_effect=lambda path, mode=0o700: primitives.protected_directory(
                    path, mode, owner=self.owner
                ),
            )
        )
        self.original_run = runtime.run
        self.stack.enter_context(patch.object(runtime, "run", side_effect=self.command))
        self.stack.enter_context(
            patch.object(
                runtime.Backend,
                "user",
                side_effect=lambda *a, **kw: SimpleNamespace(
                    returncode=0, stdout=b"not-found\n" if "show" in a else b""
                ),
            )
        )
        self.stack.enter_context(patch.object(startup, "allow_application"))
        original_text = Path.read_text
        self.stack.enter_context(
            patch.object(
                Path,
                "read_text",
                autospec=True,
                side_effect=lambda path, *a, **kw: (
                    "hermes:100000:65536\n"
                    if str(path) in ("/etc/subuid", "/etc/subgid")
                    else original_text(path, *a, **kw)
                ),
            )
        )
        self.cfg = config() | {"kind": "fixture", "application_mode": "synthetic"}
        self.child_versions = []
        self.failure = False

    def public(self, path):
        self.public_impl(path, owner=self.owner, boundary=self.root)

    def command(self, argv, **kwargs):
        if argv[0] == "ssh-keygen":
            argv = [
                str(self.signers) if x == "/etc/hermes-production/allowed_signers" else x
                for x in argv
            ]
        if "release-action" in argv:
            entry, action, release = Path(argv[2]), argv[4], argv[5]
            self.child_versions.append(entry.parent.name)
            with self.running_receiver(entry.parent.name):
                getattr(self.backend(), action)(release)
            return SimpleNamespace(returncode=0, stdout=b"")
        if argv[0] == "restorecon":
            return SimpleNamespace(returncode=0, stdout=b"")
        return self.original_run(argv, **kwargs)

    @contextmanager
    def running_receiver(self, identity):
        root = self.install / "receivers" / identity
        old_helper = sys.modules.pop("lab_profile", None)
        original_path = sys.path[:]
        sys.path.insert(0, str(root))
        try:
            with patch.object(receivers, "__file__", str(root / "production/receivers.py")):
                yield
        finally:
            sys.path[:] = original_path
            sys.modules.pop("lab_profile", None)
            if old_helper is not None:
                sys.modules["lab_profile"] = old_helper

    def backend(self):
        backend = runtime.Backend(self.cfg, state=self.state)
        backend.units = self.root / "units"
        backend.units.mkdir(exist_ok=True)
        return backend

    def versions(self):
        """Retain two independently signed releases and locally installed receivers."""
        source = self.sources / "scripts/hermes"
        original_helper = (source / "lab_profile.py").read_text()
        values = []
        for label in ("A", "B"):
            (source / "lab_profile.py").write_text(
                original_helper + f"\nRECEIVER_LABEL = {label!r}\n"
            )
            # Synthetic application only. All receiver/release validation stays real.
            engine = f"""from pathlib import Path
from lab_profile import RECEIVER_LABEL
assert RECEIVER_LABEL == {label!r}, "mixed helper"
MANUAL = Path(__file__).parent / "manual"
class DeployError(RuntimeError):
    pass
def prepare():
    pass
def ensure_user():
    return (1000, 1000)
def ensure_instance(uid, gid, mode):
    pass
def pinned_gateway():
    return "synthetic"
def configure(image):
    for tree in ("gateway-state", "gateway-ssh", "worker-state"):
        path = Path({str(self.home)!r}) / tree
        path.mkdir(exist_ok=True)
        (path / "version").write_text({label!r})
def install_quadlets(uid, mode):
    for name in ("hermes-worker.container", "hermes-gateway.container"):
        (Path({str(self.root / "units")!r}) / name).write_text({label!r})
def verify(mode):
    assert (Path({str(self.home)!r}) / "gateway-state/version").read_text() == {label!r}
"""
            (source / "profile-deploy.py").write_text(engine)
            archive = self.root / (label + ".tar")
            result = bundle.build(self.artifacts, archive, self.key)
            identity = result["artifact_sha256"]
            with archive.open("rb") as stream:
                bundle.unpack(stream, self.state / "releases" / identity, self.signers)
            receiver = receivers.install(source)
            values.append((identity, receiver))
        return values

    def application_checks(self):
        # Preserve the real routing, engine loader and release validation; replace
        # runtime container assertions only with a signed synthetic engine check.
        original_verify = runtime.Backend.verify

        def verify(backend, release):
            if backend.receiver_action(release, "verify"):
                return
            backend.engine(release).verify("synthetic")

        self.stack.enter_context(patch.object(runtime.Backend, "verify", verify))
        self.assertIsNotNone(original_verify)

    def test_fresh_bootstrap_and_unchanged_rerun_with_cli_umask(self):
        self.check_bootstrap_rerun()

    def test_partial_bootstrap_selects_corrected_receiver_without_application(self):
        self.check_bootstrap_rerun(previous=True)

    def test_private_bootstrap_preserves_active_application_receiver(self):
        self.check_bootstrap_rerun(previous=True, active=True)

    def check_bootstrap_rerun(self, previous=False, active=False):
        etc = self.root / "etc/hermes-production"
        ssh = self.root / "etc/ssh"
        systemd = self.root / "etc/systemd/system"
        sudoers = self.root / "etc/sudoers.d/hermes-production"
        for path in (ssh / "sshd_config.d", systemd, sudoers.parent):
            path.mkdir(parents=True, exist_ok=True)
        proposed = self.root / "host.json"
        proposed.write_bytes(canonical(config()))
        installed_config = etc / "host.json"
        runtime_account = SimpleNamespace(pw_uid=self.owner, pw_gid=os.getgid())
        deployment = SimpleNamespace(
            pw_uid=1001, pw_shell="/bin/sh", pw_dir="/var/empty/hermes-deploy"
        )
        created = set()
        source = ROOT / "scripts/hermes"
        old_receiver = None
        if previous:
            source = self.root / "bootstrap-source"
            (source / "production").mkdir(parents=True)
            for name in receivers.file_map(ROOT / "scripts/hermes"):
                shutil.copyfile(ROOT / "scripts/hermes" / name, source / name)
            old_receiver = receivers.install(source)
            changed = source / "production/preflight.py"
            changed.write_text(changed.read_text() + "\n# reviewed private-bootstrap correction\n")
            if active:
                created.update({"hermes", "hermes-deploy"})
                (self.state / "current.json").write_bytes(
                    canonical({"receiver": old_receiver, "release": "a" * 64})
                )
        expected_receiver = primitives.digest(receivers.descriptor(receivers.file_map(source)))

        def command(argv, **kwargs):
            if argv[0] == "useradd":
                created.add(argv[-1])
            lines = [
                "disableforwarding yes",
                "permittty no",
                "passwordauthentication no",
                "authenticationmethods publickey",
                f"forcecommand sudo -n {self.install}/productionctl.py dispatch",
            ]
            return SimpleNamespace(returncode=0, stdout="\n".join(lines).encode())

        def lookup(name):
            if name not in created:
                raise KeyError(name)
            return deployment

        with (
            patch.multiple(
                host,
                INSTALL=self.install,
                ETC=etc,
                STATE=self.state,
                HOME=self.home,
                SSH=ssh,
                SYSTEMD=systemd,
                SUDOERS=sudoers,
                DEPLOY_HOME=self.root / "var/empty/hermes-deploy",
            ),
            patch.object(host, "__file__", str(source / "production/host.py")),
            patch.object(runtime.Backend, "release", return_value=None),
            patch.object(preflight, "CONFIG", installed_config),
            patch.object(preflight, "collect", return_value={"status": "PASS"}),
            patch.object(
                preflight,
                "account",
                side_effect=lambda **kw: runtime_account if "hermes" in created else None,
            ),
            patch.object(host.pwd, "getpwnam", side_effect=lookup),
            patch.object(host, "run", side_effect=command),
            patch.object(host.os, "geteuid", return_value=0),
            patch.object(host.os, "chown"),
            patch.object(host, "lock", side_effect=lambda path: nullcontext()),
            patch.object(startup, "stable", return_value=True),
        ):
            argv = [
                str(ROOT / "scripts/hermes/productionctl.py"),
                "bootstrap",
                "--config",
                str(proposed),
                "--signers",
                str(self.signers),
                "--apply",
            ]
            # Execute the actual __main__ entrypoint, including os.umask(077).
            original_mask = os.umask(0o022)
            try:
                before = None
                for _ in range(2):
                    with (
                        patch.object(sys, "argv", argv),
                        redirect_stdout(io.StringIO()),
                        self.assertRaises(SystemExit) as exit_value,
                    ):
                        runpy.run_path(argv[0], run_name="__main__")
                    self.assertEqual(exit_value.exception.code, 0)
                    self.assertEqual(os.umask(0o077), 0o077)
                    current = {
                        str(p): (p.stat().st_ino, p.stat().st_mtime_ns)
                        for p in self.install.rglob("*")
                    }
                    if before is not None:
                        self.assertEqual(current, before)
                    before = current
                for path in (
                    self.install,
                    self.install.parent,
                    self.install / "receivers",
                    ssh / "hermes-production",
                    systemd / f"user@{self.owner}.service.d",
                    host.DEPLOY_HOME,
                    host.DEPLOY_HOME.parent,
                ):
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o755, str(path))
                for path in self.install.rglob("*"):
                    if path.is_dir():
                        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o755)
                for path in (etc, self.state, self.state / "incoming", self.home):
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE(installed_config.stat().st_mode), 0o600)
                self.assertEqual(created, {"hermes", "hermes-deploy"})
                self.assertEqual(
                    json.loads((self.install / "controller.json").read_text()),
                    {"receiver": old_receiver if active else expected_receiver},
                )
                receivers.validate(expected_receiver)
            finally:
                os.umask(original_mask)

    def test_quadlet_missing_parents_are_public_under_private_umask(self):
        spec = importlib.util.spec_from_file_location(
            "permission_profile", ROOT / "scripts/hermes/profile-deploy.py"
        )
        engine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(engine)
        engine.PRODUCTION = True
        engine.QUADLET_USERS = self.root / "etc/containers/systemd/users"
        ensure = engine.ensure_directory
        with (
            patch.object(primitives, "public_directory", side_effect=self.public),
            patch.object(
                engine,
                "ensure_directory",
                side_effect=lambda path, mode, uid, gid: ensure(
                    path, mode, self.owner, os.getgid()
                ),
            ),
            patch.object(engine.os, "chown"),
            patch.object(engine, "command"),
            patch.object(engine, "user_systemctl"),
        ):
            previous = os.umask(0o077)
            try:
                self.assertTrue(engine.install_quadlets(1234, "synthetic"))
                self.assertFalse(engine.install_quadlets(1234, "synthetic"))
                for path in (
                    engine.QUADLET_USERS / "1234",
                    engine.QUADLET_USERS,
                    engine.QUADLET_USERS.parent,
                    engine.QUADLET_USERS.parent.parent,
                ):
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o755)
            finally:
                os.umask(previous)

    def test_public_directory_rejects_existing_unsafe_paths(self):
        path = self.root / "unsafe"
        path.mkdir(mode=0o700)
        with self.assertRaisesRegex(Refused, "unsafe-managed-directory"):
            self.public(path)
        parent = self.root / "private-parent"
        parent.mkdir(mode=0o700)
        with self.assertRaisesRegex(Refused, "unsafe-public-parent"):
            self.public(parent / "new-child")
        self.assertFalse((parent / "new-child").exists())
        path.rmdir()
        path.symlink_to(self.home, target_is_directory=True)
        with self.assertRaisesRegex(Refused, "unsafe-managed-directory"):
            self.public(path)

    def test_receiver_hash_checks_and_mixed_engine_rejection(self):
        (old, old_receiver), (new, new_receiver) = self.versions()
        backend = self.backend()
        backend.release(old)
        backend.release(new)
        with self.assertRaisesRegex(Refused, "mixed-receiver"):
            backend.engine(old)
        helper = self.install / "receivers" / old_receiver / "lab_profile.py"
        helper.write_text(helper.read_text() + "\n# tampered\n")
        with self.assertRaisesRegex(Refused, "receiver-hash"):
            self.backend().release(old)
        self.backend().release(new)
        shutil.rmtree(self.install / "receivers" / new_receiver)
        with self.assertRaisesRegex(Refused, "private-bootstrap"):
            self.backend().release(new)
        with patch.object(runtime.Backend, "stop") as stop:
            with self.assertRaisesRegex(Refused, "private-bootstrap"):
                Transaction(self.state, self.backend()).deploy(new)
            stop.assert_not_called()

    def test_launcher_selection_retains_and_checks_both_versions(self):
        (old, old_receiver), (_, new_receiver) = self.versions()
        spec = importlib.util.spec_from_file_location(
            "test_production_launcher", ROOT / "scripts/hermes/production-launcher.py"
        )
        launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        # Root ownership is the only unavailable boundary in this user-owned tree.
        with patch.object(
            launcher, "checked", side_effect=lambda path: primitives.regular(path).read_bytes()
        ):
            for identity in (old_receiver, new_receiver, old_receiver):
                receivers.select(identity)
                self.assertEqual(
                    launcher.selected(self.install),
                    self.install / "receivers" / identity / "productionctl.py",
                )
            receiver_file = self.install / "receivers" / old_receiver / "production/runtime.py"
            receiver_file.write_text(receiver_file.read_text() + "\n# tampered\n")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                launcher.selected(self.install)
            with self.assertRaisesRegex(Refused, "receiver-hash"):
                self.backend().release(old)

    def test_two_receiver_upgrade_rollback_and_failed_transition(self):
        self.application_checks()
        (old, old_receiver), (new, new_receiver) = self.versions()
        backend = self.backend()
        tx = Transaction(self.state, backend)
        tx.deploy(old)
        # Staging B did not overwrite A or select B before the application update.
        self.assertEqual(
            primitives.read_json(self.install / "controller.json"), {"receiver": old_receiver}
        )
        for failure in ("configure", "current-pointer"):
            original_configure = runtime.Backend.configure
            original_atomic = runtime.atomic
            failed = False

            def configure(instance, release):
                nonlocal failed
                original_configure(instance, release)
                if release == new and not failed and failure == "configure":
                    failed = True
                    raise RuntimeError("injected-upgrade-failure")

            def write(path, content, *args):
                nonlocal failed
                if (
                    path == self.state / "current.json"
                    and not failed
                    and failure == "current-pointer"
                ):
                    failed = True
                    raise RuntimeError("injected-upgrade-failure")
                return original_atomic(path, content, *args)

            with (
                self.subTest(failure=failure),
                patch.object(runtime.Backend, "configure", configure),
                patch.object(runtime, "atomic", side_effect=write),
            ):
                with self.assertRaisesRegex(RuntimeError, "injected-upgrade-failure"):
                    tx.deploy(new, upgrade=True)
            self.assertEqual(backend.current(), old)
            self.assertEqual((self.home / "gateway-state/version").read_text(), "A")
            self.assertEqual(
                primitives.read_json(self.install / "controller.json"), {"receiver": old_receiver}
            )
        tx.deploy(new, upgrade=True)
        self.assertEqual(
            primitives.read_json(self.state / "current.json"),
            {"release": new, "receiver": new_receiver},
        )
        # A fresh invocation after selection runs B's coordinating receiver.
        with self.running_receiver(new_receiver):
            rollback = Transaction(self.state, self.backend())
            self.assertEqual(rollback.rollback()["status"], "ROLLED_BACK")
            self.assertEqual(rollback.rollback()["status"], "UNCHANGED")
        self.assertEqual(backend.current(), old)
        self.assertEqual((self.home / "gateway-state/version").read_text(), "A")
        self.assertEqual(
            primitives.read_json(self.install / "controller.json"), {"receiver": old_receiver}
        )
        self.assertIn(old_receiver, self.child_versions)
        self.assertIn(new_receiver, self.child_versions)
        self.assertTrue((self.install / "receivers" / old_receiver).is_dir())

    def test_interrupted_cross_receiver_recovery_and_interrupted_rollback(self):
        self.application_checks()
        (old, old_receiver), (new, new_receiver) = self.versions()
        backend = self.backend()
        tx = Transaction(self.state, backend)
        tx.deploy(old)
        original_atomic = runtime.atomic

        def crash(path, content, *args):
            if path == self.state / "current.json":
                raise SystemExit("simulated-power-loss")
            return original_atomic(path, content, *args)

        # Kill the operation after selecting B but before writing application current.
        with patch.object(tx, "recover"), patch.object(runtime, "atomic", side_effect=crash):
            with self.assertRaises(SystemExit):
                tx.deploy(new, upgrade=True)
        self.assertEqual(
            primitives.read_json(self.install / "controller.json"), {"receiver": new_receiver}
        )
        self.assertEqual((self.home / "gateway-state/version").read_text(), "B")
        with self.running_receiver(new_receiver):
            Transaction(self.state, self.backend()).recover()
        self.assertEqual(backend.current(), old)
        self.assertEqual((self.home / "gateway-state/version").read_text(), "A")
        self.assertEqual(
            primitives.read_json(self.install / "controller.json"), {"receiver": old_receiver}
        )
        tx.deploy(new, upgrade=True)
        with patch.object(runtime, "atomic", side_effect=crash):
            with self.assertRaises(SystemExit):
                tx.rollback()
        # Retry with A's selected receiver after the interrupted rollback pointer switch.
        with self.running_receiver(old_receiver):
            Transaction(self.state, self.backend()).recover()
        self.assertEqual(backend.current(), old)
        self.assertEqual((self.home / "gateway-state/version").read_text(), "A")
        self.assertEqual(primitives.read_json(self.state / "journal.json")["stage"], "recovered")

    def test_failed_recovery_stops_both_services_retains_journal_and_retries(self):
        self.application_checks()
        (old, _), (new, _) = self.versions()
        backend = self.backend()
        tx = Transaction(self.state, backend)
        tx.deploy(old)
        tx.deploy(new, upgrade=True)
        pending = primitives.read_json(tx.journal)
        original_atomic = operations.atomic
        for failure in ("activation", "verification", "current-pointer", "attempt", "journal"):
            for stop_failure in (False, True):
                with self.subTest(failure=failure, stop_failure=stop_failure):
                    tx.save(dict(pending), "rollback")
                    before = tx.journal.read_bytes()
                    running, stops = set(), []
                    triggered = False

                    def user(*args, **kwargs):
                        if "show" in args:
                            return SimpleNamespace(stdout=b"loaded\n", returncode=0)
                        if "start" in args:
                            running.add(args[-1])
                            if failure == "activation" and args[-1] == "hermes-gateway.service":
                                inject()
                        if "stop" in args:
                            stops.append(args[-1])
                            if triggered and stop_failure and args[-1] == "hermes-gateway.service":
                                raise Refused("synthetic-stop-failure")
                            running.discard(args[-1])
                        output = "\n".join(
                            unit.removesuffix(".service") for unit in sorted(running)
                        )
                        return SimpleNamespace(
                            stdout=output.encode() if "ps" in args else b"", returncode=0
                        )

                    def inject():
                        nonlocal triggered
                        if not triggered:
                            triggered = True
                            raise RuntimeError("injected-recovery-failure")

                    original_verify = backend.verify
                    original_current = backend.set_current

                    def verify(release):
                        if failure == "verification":
                            inject()
                        original_verify(release)

                    def current(release):
                        original_current(release)
                        if failure == "current-pointer":
                            inject()

                    def write(path, content, *args):
                        terminal = json.loads(content).get("stage") == "recovered"
                        original_atomic(path, content, *args)
                        if terminal and (
                            (failure == "attempt" and path.parent.name == "attempts")
                            or (failure == "journal" and path == tx.journal)
                        ):
                            # Also cover replace succeeding before final fsync raises.
                            inject()

                    with (
                        patch.object(backend, "user", side_effect=user),
                        patch.object(backend, "verify", side_effect=verify),
                        patch.object(backend, "set_current", side_effect=current),
                        patch.object(operations, "atomic", side_effect=write),
                    ):
                        expected = (
                            "service-stop-failed-safety-unconfirmed"
                            if stop_failure
                            else "injected-recovery-failure"
                        )
                        with self.assertRaisesRegex((RuntimeError, Refused), expected):
                            tx.recover()
                    self.assertEqual(
                        stops[-2:], ["hermes-gateway.service", "hermes-worker.service"]
                    )
                    self.assertEqual(tx.journal.read_bytes(), before)
                    failures = list((self.state / "attempts").glob("*.recovery-failed-*.json"))
                    evidence = max(failures, key=lambda path: path.stat().st_mtime_ns)
                    saved = evidence.read_bytes()
                    self.assertEqual(json.loads(saved)["services_stopped"], not stop_failure)
                    self.assertEqual(running, {"hermes-gateway.service"} if stop_failure else set())
                    # A fresh invocation succeeds and preserves the failed-attempt record.
                    Transaction(self.state, self.backend()).recover()
                    self.assertEqual(primitives.read_json(tx.journal)["stage"], "recovered")
                    self.assertEqual((self.home / "gateway-state/version").read_text(), "A")
                    self.assertEqual(backend.current(), old)
                    self.assertEqual(evidence.read_bytes(), saved)

    def test_stop_attempts_worker_even_when_gateway_query_or_stop_fails(self):
        backend = self.backend()
        for failed_command in ("show", "stop"):
            calls = []

            def user(*args, **kwargs):
                calls.append(args)
                if failed_command in args and args[-1] == "hermes-gateway.service":
                    raise Refused("synthetic-failure")
                return SimpleNamespace(stdout=b"loaded\n" if "show" in args else b"", returncode=0)

            with patch.object(backend, "user", side_effect=user):
                with self.assertRaisesRegex(Refused, "service-stop-failed"):
                    backend.stop()
            self.assertEqual(
                [call[-1] for call in calls if "stop" in call],
                ["hermes-gateway.service", "hermes-worker.service"],
            )


class FakeBackend:
    def __init__(self, failure=None):
        self.release = "old"
        self.data = "old-state"
        self.events = []
        self.failure = failure
        self.saved = {}

    def event(self, stage):
        self.events.append(stage)
        if stage == self.failure:
            self.failure = None
            raise RuntimeError("injected")

    def current(self):
        return self.release

    def prepare(self, candidate, previous):
        pass

    def set_current(self, release):
        self.event("set-current")
        self.release = release

    def stop(self):
        self.event("stop")

    def snapshot(self, attempt, release):
        self.event("snapshot")
        self.saved[attempt] = (release, self.data)
        return attempt

    def restore(self, snapshot, release):
        self.event("restore")
        assert self.saved[snapshot][0] == release
        self.data = self.saved[snapshot][1]

    def import_images(self, release):
        self.event("import")

    def configure(self, release):
        self.data = release + "-state"
        self.event("configure")

    def activate(self, release):
        assert self.data == release + "-state", "old image started on migrated state"
        self.event("activate")

    def verify(self, release):
        assert self.data == release + "-state"
        self.event("verify")

    def restart_previous(self, release):
        if release:
            self.activate(release)


class ProductionTransactionTests(unittest.TestCase):
    def test_dispatcher_sigkill_keeps_receiver_and_detached_writer_serialized(self):
        for detached in (False, True):
            with self.subTest(detached=detached), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                for name in ("attempts", "incoming", "releases/new"):
                    (root / name).mkdir(parents=True)
                (root / "source").write_text(str(ROOT / "scripts/hermes"))
                (root / "data").write_text("old-state")
                if detached:
                    (root / "detached").touch()
                driver = root / "productionctl.py"
                shutil.copyfile(ROOT / "tests/fixtures/production_process_driver.py", driver)
                command = [sys.executable, "-I", str(driver)]

                def wait_for(predicate):
                    deadline = time.monotonic() + 10
                    while not predicate():
                        self.assertLess(
                            time.monotonic(), deadline, "subprocess handshake timed out"
                        )
                        time.sleep(0.02)

                with subprocess.Popen(
                    [*command, "upgrade"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                ) as dispatcher:
                    try:
                        wait_for(lambda: (root / "writer-pid").exists())
                        self.assertTrue((root / "namespace-initialized").exists())
                        journal = (root / "journal.json").read_bytes()
                        self.assertEqual(json.loads(journal)["stage"], "configuration")
                        dispatcher.kill()
                        self.assertEqual(dispatcher.wait(timeout=5), -signal.SIGKILL)
                        for kill_receiver in (False, True) if detached else (False,):
                            if kill_receiver:
                                os.kill(int((root / "receiver-pid").read_text()), signal.SIGKILL)
                            retry = subprocess.run(
                                [*command, "rollback"], capture_output=True, timeout=5
                            )
                            self.assertEqual(retry.returncode, 1, retry.stderr)
                            self.assertIn(b"operation-busy", retry.stderr)
                            self.assertEqual((root / "journal.json").read_bytes(), journal)
                            self.assertFalse((root / "restored").exists())
                            self.assertEqual((root / "data").read_text(), "old-state")
                        (root / "finish").touch()
                        wait_for(lambda: (root / "written").exists())

                        def recovered():
                            result = subprocess.run(
                                [*command, "rollback"], capture_output=True, timeout=5
                            )
                            if b"operation-busy" in result.stderr:
                                return False
                            self.assertEqual(result.returncode, 0, result.stderr)
                            return True

                        wait_for(recovered)
                        self.assertEqual((root / "data").read_text(), "old-state")
                        self.assertEqual(
                            primitives.read_json(root / "journal.json")["stage"], "recovered"
                        )
                        writer = int((root / "writer-pid").read_text())
                        wait_for(lambda: not Path(f"/proc/{writer}").exists())
                        self.assertEqual((root / "data").read_text(), "old-state")
                    finally:
                        (root / "finish").touch()
                        for name in ("receiver-pid", "writer-pid"):
                            if (root / name).exists():
                                try:
                                    os.kill(int((root / name).read_text()), signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                        if dispatcher.poll() is None:
                            dispatcher.kill()
                        dispatcher.wait(timeout=5)

    def test_supervised_timeout_drains_detached_descendant_before_return(self):
        for receiver_exits in (False, True):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                writer = "import time; from pathlib import Path; time.sleep(0.3); Path('written').touch()"
                receiver = (
                    "import subprocess, sys, time; "
                    f"subprocess.Popen([sys.executable, '-c', {writer!r}], "
                    "start_new_session=True, close_fds=True, stdout=subprocess.DEVNULL, "
                    "stderr=subprocess.DEVNULL); "
                    + ("sys.exit(0)" if receiver_exits else "time.sleep(20)")
                )
                with lock(root / "lock"):
                    result = run(
                        [sys.executable, "-c", receiver], timeout=0.15, cwd=root, check=False
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertTrue((root / "written").exists())

    def test_all_failed_update_stages_restore_matching_state_before_restart(self):
        for failure in (
            "stop",
            "snapshot",
            "import",
            "configure",
            "activate",
            "verify",
            "set-current",
        ):
            with self.subTest(stage=failure), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "attempts").mkdir()
                backend = FakeBackend(failure)
                tx = Transaction(root, backend)
                with self.assertRaisesRegex(RuntimeError, "injected"):
                    tx.deploy("new", upgrade=True)
                self.assertEqual((backend.release, backend.data), ("old", "old-state"))
                self.assertTrue(list((root / "attempts").glob("*.failed.json")))

    def test_noop_avoids_stop_backup_import_and_restart(self):
        with tempfile.TemporaryDirectory() as temporary:
            backend = FakeBackend()
            result = Transaction(temporary, backend).deploy("old")
            self.assertEqual(result["status"], "UNCHANGED")
            self.assertEqual(backend.events, ["verify"])

    def test_upgrade_requires_explicit_operation_and_rollback_restores_pair(self):
        with tempfile.TemporaryDirectory() as temporary:
            (Path(temporary) / "attempts").mkdir()
            backend = FakeBackend()
            tx = Transaction(temporary, backend)
            with self.assertRaisesRegex(Refused, "explicit-upgrade"):
                tx.deploy("new")
            tx.deploy("new", upgrade=True)
            self.assertEqual((backend.release, backend.data), ("new", "new-state"))
            tx.rollback()
            self.assertEqual((backend.release, backend.data), ("old", "old-state"))
            backend.events.clear()
            self.assertEqual(tx.rollback()["status"], "UNCHANGED")
            self.assertEqual(backend.events, ["verify"])

    def test_interruption_recovery_and_failed_recovery_never_start_mismatched_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "attempts").mkdir()
            backend = FakeBackend("restore")
            backend.saved["saved"] = ("old", "old-state")
            backend.data = "new-state"
            row = {
                "id": "attempt",
                "previous": "old",
                "candidate": "new",
                "snapshot": "saved",
                "timings": {},
            }
            tx = Transaction(root, backend)
            tx.save(row, "configuration")
            with self.assertRaisesRegex(RuntimeError, "injected"):
                tx.recover()
            self.assertNotIn("activate", backend.events)
            tx.recover()
            self.assertEqual(backend.data, "old-state")

    def test_concurrent_lock_and_unchanged_atomic_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "lock"
            with lock(path), self.assertRaisesRegex(Refused, "busy"), lock(path):
                pass
            data = Path(temporary) / "data"
            atomic(data, b"unchanged")
            before = data.stat().st_mtime_ns
            self.assertFalse(atomic(data, b"unchanged"))
            self.assertEqual(before, data.stat().st_mtime_ns)

    def test_restore_archive_escapes_and_devices_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "backup.tar"
            for name, kind, target in (
                ("../outside", tarfile.REGTYPE, ""),
                ("gateway-state/device", tarfile.CHRTYPE, ""),
                ("gateway-state/link", tarfile.SYMTYPE, "/etc"),
                ("gateway-state/link", tarfile.SYMTYPE, "../../etc"),
                ("gateway-state/hard", tarfile.LNKTYPE, "etc/shadow"),
            ):
                with tarfile.open(path, "w") as archive:
                    member = tarfile.TarInfo(name)
                    member.type, member.linkname = kind, target
                    archive.addfile(member)
                with self.subTest(name=name, target=target), self.assertRaises(Refused):
                    runtime.validate_snapshot(path)


class ProductionFixtureTests(unittest.TestCase):
    """Synthetic fixture setup: no libvirt, network listener or guest is used."""

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.session_runtime = self.root / "session-runtime"
        self.session_runtime.mkdir(mode=0o700)
        self.stack.enter_context(
            patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(self.session_runtime)})
        )
        spec = importlib.util.spec_from_file_location(
            "production_fixture_test", ROOT / "vm/hermes-production-fixture.py"
        )
        self.fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.fixture)
        self.roles = {
            role: (name, self.root / role, port)
            for role, (name, _, port) in self.fixture.FIXTURES.items()
        }
        self.stack.enter_context(patch.object(self.fixture, "FIXTURES", self.roles))
        self.port = self.stack.enter_context(patch.object(self.fixture, "available_port"))
        self.capacity = self.stack.enter_context(
            patch.object(
                self.fixture.shutil, "disk_usage", return_value=SimpleNamespace(free=80 * 1024**3)
            )
        )
        self.domains = b""
        self.definitions = b"fedora43\nfedora42\n"
        self.fail_install = False
        self.commands = []
        self.command_options = []

        def command(argv, **kwargs):
            self.commands.append(argv)
            self.command_options.append(kwargs)
            if argv[0] == "virsh":
                self.assertEqual(
                    argv, ["virsh", "-c", "qemu:///session", "list", "--all", "--name"]
                )
                output = self.domains
            elif argv[:3] == ["virt-install", "--osinfo", "list"]:
                output = self.definitions
            elif argv[0] == "virt-install":
                if self.fail_install:
                    raise Refused("command-failed:virt-install")
                output = b""
            elif argv[0] == "qemu-img":
                output = b""
            else:
                self.fail(f"unexpected command: {argv[0]}")
            return SimpleNamespace(stdout=output, returncode=0)

        self.stack.enter_context(patch.object(self.fixture, "run", side_effect=command))
        self.media = self.root / "hermes-qualification.iso"
        self.media.write_bytes(b"synthetic built media")
        self.settings = self.root / "settings.json"
        self.settings.write_bytes(canonical(settings() | {"kind": "fixture"}))
        for path in (self.media, self.settings):
            path.chmod(0o600)

    def create(self, **kwargs):
        return self.fixture.create(self.media, self.settings, **kwargs)

    def test_preview_selects_installed_metadata_without_creating_resources(self):
        result = self.create()
        self.assertEqual(result["name"], "hermes-production-qualification")
        self.assertEqual(result["guest_definition"], "fedora43")
        self.assertEqual(result["ssh"], {"host": "127.0.0.1", "port": 22224})
        self.assertEqual(result["status"], "PREVIEW")
        self.assertEqual(result["media_sha256"], sha(self.media))
        self.assertIn("UNATTENDED", result["installation"])
        self.assertFalse(self.roles["qualification"][1].exists())
        self.assertFalse(
            any(c[0] == "qemu-img" or "--name" in c for c in self.commands if c[0] != "virsh")
        )
        self.definitions = b"fedora44\nfedora43\n"
        self.assertEqual(self.create()["guest_definition"], "fedora44")

    def test_inventory_and_install_use_the_same_private_session(self):
        with patch.dict(os.environ, {"HERMES_UNRELATED_SECRET": "synthetic-do-not-forward"}):
            self.create(apply=True)
        for command, options in zip(self.commands, self.command_options, strict=True):
            if command[0] not in {"virsh", "virt-install"}:
                continue
            self.assertEqual(
                options.get("env", {}).get("XDG_RUNTIME_DIR"), str(self.session_runtime)
            )
            self.assertEqual(options["env"]["HOME"], str(Path.home()))
            self.assertNotIn("HERMES_UNRELATED_SECRET", options["env"])

    def test_missing_or_unsafe_session_runtime_refuses_before_commands(self):
        with patch.dict(os.environ):
            os.environ.pop("XDG_RUNTIME_DIR", None)
            with self.assertRaisesRegex(Refused, "session-runtime"):
                self.create(apply=True)
        self.session_runtime.chmod(0o755)
        with self.assertRaisesRegex(Refused, "session-runtime"):
            self.create(apply=True)
        self.assertFalse(self.commands)
        self.assertFalse(self.roles["qualification"][1].exists())

    def test_console_directly_hands_terminal_to_safe_attachment_for_each_role(self):
        for role, (name, _, _) in self.roles.items():
            self.create(role=role, apply=True)
            previous = list(self.commands)
            with (
                patch.object(self.fixture.os, "isatty", return_value=True),
                patch.object(self.fixture.os, "execvpe") as execute,
                patch.dict(os.environ, {"HERMES_UNRELATED_SECRET": "synthetic-only"}),
                redirect_stdout(io.StringIO()) as output,
            ):
                self.fixture.console(role)
            program, argv, environment = execute.call_args.args
            self.assertEqual(program, "virsh")
            self.assertEqual(
                argv,
                ["virsh", "-c", "qemu:///session", "--escape", "^q", "console", name, "--safe"],
            )
            self.assertEqual(environment["XDG_RUNTIME_DIR"], str(self.session_runtime))
            self.assertEqual(environment["TERM"], "xterm-256color")
            self.assertNotIn("HERMES_UNRELATED_SECRET", environment)
            self.assertEqual(self.commands, previous)  # No captured command or lifecycle operation.
            self.assertIn("no input is required", output.getvalue())
            self.assertIn("escrowed recovery key", output.getvalue())
            self.assertIn("Ctrl+Q detaches", output.getvalue())

    def test_console_refuses_redirected_streams_and_wrong_ownership(self):
        with patch.object(self.fixture.os, "execvpe") as execute:
            for redirected in (0, 1, 2):
                with patch.object(
                    self.fixture.os, "isatty", side_effect=lambda fd: fd != redirected
                ):
                    with self.assertRaisesRegex(Refused, "private-interactive-terminal-required"):
                        self.fixture.console("qualification")
            self.create(apply=True)
            ownership = self.roles["qualification"][1] / "ownership.json"
            value = json.loads(ownership.read_text())
            value["role"] = "restore"
            ownership.write_bytes(canonical(value))
            with patch.object(self.fixture.os, "isatty", return_value=True):
                with self.assertRaisesRegex(Refused, "fixture-ownership-mismatch"):
                    self.fixture.console("qualification")
            with self.assertRaisesRegex(Refused, "unknown-fixture-role"):
                self.fixture.console("unrelated-domain")
            execute.assert_not_called()

    def test_both_roles_boot_built_media_through_firmware_with_localhost_only_ssh(self):
        for role, (name, base, port) in self.roles.items():
            result = self.create(role=role, apply=True)
            self.assertEqual(result["status"], "CREATED_UNATTENDED_INSTALLATION_RUNNING")
            self.assertEqual(result["name"], name)
            self.assertEqual(sha(base / "unrelated.raw"), result["unrelated_sha256"])
            command = self.commands[-1]
            self.assertEqual(command[command.index("--name") + 1], name)
            # Firmware -> shim -> GRUB from a USB disk, like the production stick; never
            # direct kernel boot, which changes PCR7.
            disks = [command[i + 1] for i, a in enumerate(command) if a == "--disk"]
            self.assertIn(f"path={self.media},format=raw,device=disk,bus=usb,readonly=on", disks)
            self.assertIn("--import", command)
            self.assertEqual(command[command.index("--events") + 1], "on_reboot=destroy")
            for direct in ("--location", "--initrd-inject", "--extra-args", "--cdrom"):
                self.assertNotIn(direct, command)
            boot = command[command.index("--boot") + 1]
            self.assertIn("secure-boot,firmware.feature0.enabled=yes", boot)
            self.assertIn("enrolled-keys,firmware.feature1.enabled=yes", boot)
            self.assertIn("model=tpm-crb", command[command.index("--tpm") + 1])
            self.assertEqual(command[command.index("--memory") + 1], "9216")
            self.assertIn(f"log.file={base / 'serial.log'}", command[command.index("--serial") + 1])
            network = command[command.index("--network") + 1]
            self.assertIn("portForward0.address=127.0.0.1", network)
            self.assertIn(f"portForward0.range0.start={port}", network)
            self.assertNotIn("0.0.0.0", network)
            before = (base / "ownership.json").read_bytes()
            with self.assertRaisesRegex(Refused, "directory-exists"):
                self.create(role=role, apply=True)
            self.assertEqual((base / "ownership.json").read_bytes(), before)

    def test_conflicts_capacity_and_unknown_roles_fail_before_creation(self):
        with self.assertRaisesRegex(Refused, "unknown-fixture-role"):
            self.create(role="arbitrary")
        self.domains = b"hermes-production-restore\n"
        with self.assertRaisesRegex(Refused, "name-conflict"):
            self.create(role="restore", apply=True)
        self.domains = b""
        self.port.side_effect = Refused("fixture-ssh-port-unavailable")
        with self.assertRaisesRegex(Refused, "port-unavailable"):
            self.create(apply=True)
        self.port.side_effect = None
        self.capacity.return_value.free = self.fixture.MIN_FREE_BYTES - 1
        with self.assertRaisesRegex(Refused, "host-space-low"):
            self.create(apply=True)
        self.assertFalse(any(base.exists() for _, base, _ in self.roles.values()))

    def test_dangling_directory_symlink_is_preserved(self):
        base = self.roles["qualification"][1]
        base.symlink_to(self.root / "absent", target_is_directory=True)
        with self.assertRaisesRegex(Refused, "directory-exists"):
            self.create(apply=True)
        self.assertTrue(base.is_symlink())
        self.assertFalse(self.commands)

    def test_metadata_production_settings_wrong_disk_and_non_iso_media_are_refused(self):
        self.definitions = b"fedora42\n"
        with self.assertRaisesRegex(Refused, "guest-definition-unavailable"):
            self.create(apply=True)
        self.definitions = b"fedora43\n"
        for change, reason in (
            ({"kind": "production"}, "fixture-settings-required"),
            ({"disk_id": "/dev/disk/by-id/virtio-OTHER"}, "fixture-disk-id-mismatch"),
        ):
            self.settings.write_bytes(canonical(settings() | {"kind": "fixture"} | change))
            with self.assertRaisesRegex(Refused, reason):
                self.create(apply=True)
        self.settings.write_bytes(canonical(settings() | {"kind": "fixture"}))
        other = self.root / "media.img"
        other.write_bytes(b"x")
        other.chmod(0o600)
        with self.assertRaisesRegex(Refused, "built-installation-media-required"):
            self.fixture.create(other, self.settings, apply=True)
        self.assertFalse(self.roles["qualification"][1].exists())

    def test_partial_installation_retains_ownership_and_refuses_replay(self):
        self.fail_install = True
        with self.assertRaisesRegex(Refused, "command-failed:virt-install"):
            self.create(apply=True)
        base = self.roles["qualification"][1]
        evidence = (base / "ownership.json").read_bytes()
        self.assertTrue((base / "unrelated.raw").is_file())
        with self.assertRaisesRegex(Refused, "directory-exists"):
            self.create(apply=True)
        self.assertEqual((base / "ownership.json").read_bytes(), evidence)


SIGNERS = b'hermes-production namespaces="hermes-production-v1" ssh-ed25519 ' + b"C" * 68 + b"\n"
LUKS = "33345678-1234-1234-1234-123456789012"
ENV_DOC = (
    b"DEEPSEEK_API_KEY=sk-synthetic\nTELEGRAM_BOT_TOKEN=1:synthetic\nTELEGRAM_ALLOWED_USERS=42\n"
)


def heredoc(rendered, marker):
    return rendered.split(f"<<'{marker}'\n", 1)[1].split(f"\n{marker}", 1)[0]


class ProductionUnattendedTests(unittest.TestCase):
    """Installer-generated secrets, escrow, automatic commissioning and media; all synthetic."""

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.signers = self.root / "allowed_signers"
        self.signers.write_bytes(SIGNERS)

    def test_escrow_roundtrip_tamper_and_strict_members(self):
        material = escrow_material()
        password = escrow.password()
        content = {
            "recovery-key": escrow.recovery_key().encode(),
            "admin-password": password.encode(),
            "receipt.json": canonical({"schema": 1}),
        }
        sealed = self.root / "escrow.cms"
        sealed.write_bytes(escrow.seal(material["cert"], content))
        self.assertNotIn(password.encode(), sealed.read_bytes())
        self.assertEqual(escrow.unseal(sealed, material["key"]), content)
        damaged = bytearray(sealed.read_bytes())
        damaged[-20] ^= 0xFF
        sealed.write_bytes(bytes(damaged))
        with self.assertRaises(Refused):
            escrow.unseal(sealed, material["key"])
        with self.assertRaisesRegex(Refused, "unexpected-escrow-member"):
            escrow.archive({"other": b"x"})
        with self.assertRaisesRegex(Refused, "incomplete-escrow"):
            escrow.members(escrow.archive({"recovery-key": b"k"}))
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            link = tarfile.TarInfo("recovery-key")
            link.type, link.linkname = tarfile.SYMTYPE, "/etc/shadow"
            tar.addfile(link)
        with self.assertRaisesRegex(Refused, "unexpected-escrow-member"):
            escrow.members(buffer.getvalue())
        keys = {escrow.recovery_key() for _ in range(20)}
        self.assertEqual(len(keys), 20)
        for key in keys:
            self.assertRegex(key, r"^(?:[cbdefghijklnrtuv]{8}-){7}[cbdefghijklnrtuv]{8}$")

    def test_escrow_certificate_requires_rsa_3072_or_larger(self):
        self.assertRegex(escrow.certificate(escrow_material()["pem"]), r"^[a-f0-9]{64}$")
        key, cert = self.root / "small.key", self.root / "small.pem"
        run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-noenc",
                "-days",
                "1",
                "-subj",
                "/CN=small",
                "-keyout",
                str(key),
                "-out",
                str(cert),
            ],
            timeout=120,
        )
        with self.assertRaisesRegex(Refused, "rsa-3072"):
            escrow.certificate(cert.read_text())
        for value in ("", "-----BEGIN CERTIFICATE-----\nAAAA\n-----END CERTIFICATE-----\n", 7):
            with self.assertRaises(Refused):
                escrow.certificate(value)

    def test_renderer_validates_unattended_fields_and_pins_manifest(self):
        kickstart.validate(settings())
        for change, reason in (
            ({"deploy_public_key": settings()["admin_public_key"]}, "keys-must-differ"),
            ({"deploy_from": "0.0.0.0/0"}, "unrestricted"),
            ({"restic_repository": "sftp:backup:pw@host:/x"}, "offhost-sftp"),
            ({"artifact_budget_bytes": 20 * preflight.GIB}, "layout-too-small"),
            ({"kind": "lab"}, "host-schema"),
            ({"kind": "production", "application_mode": "synthetic"}, "application-mode"),
            ({"escrow_certificate": "not a certificate"}, "escrow-certificate"),
        ):
            with self.subTest(change=change), self.assertRaisesRegex(Refused, reason):
                kickstart.validate(settings() | change)
        with self.assertRaisesRegex(Refused, "installation-fields"):
            kickstart.validate(settings() | {"admin_password": "never"})
        with self.assertRaisesRegex(Refused, "invalid-manifest"):
            kickstart.render(settings(), "not-a-hash")
        payload, files = kickstart.manifest(settings(), self.signers)
        self.assertEqual(
            set(payload),
            set(kickstart.controller_files()) | {"install.json", "allowed_signers"},
        )
        self.assertIn("production/install.py", payload)
        self.assertIn("production/commission.py", payload)
        installed = decode(payload["install.json"])
        self.assertEqual(set(installed), set(kickstart.INSTALL_FIELDS))
        self.assertNotIn("disk_id", installed)
        for name, data in payload.items():
            self.assertEqual(files["files"][name], hashlib.sha256(data).hexdigest())
        self.signers.write_bytes(b"unrelated ssh-ed25519 AAAA\n")
        with self.assertRaisesRegex(Refused, "signer-identity"):
            kickstart.manifest(settings(), self.signers)
        self.signers.write_bytes(SIGNERS)
        source = self.root / "install.json"
        source.write_bytes(canonical(settings()))
        output = self.root / "production.ks"
        preview = kickstart.write(source, output, signers=self.signers)
        self.assertEqual(preview["status"], "PREVIEW")
        self.assertFalse(output.exists())
        rendered = kickstart.write(source, output, signers=self.signers, apply=True)
        self.assertEqual(rendered["status"], "RENDERED")
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        self.assertIn(rendered["manifest_sha256"], output.read_text())
        with self.assertRaisesRegex(Refused, "output-exists"):
            kickstart.write(source, output, signers=self.signers, apply=True)

    def test_pre_generates_random_temporary_passphrase_in_installer_ram(self):
        script = heredoc(kickstart.render(settings(), MANIFEST), "HERMES_TEMPORARY_KEY")
        keys = []
        for name in ("first", "second"):
            target = self.root / name
            target.mkdir(mode=0o700)
            exec(script.replace('"/dev/shm/hermes-install"', repr(str(target))), {})
            key = (target / "luks-temporary").read_text()
            part = (target / "part.ks").read_text()
            for path in (target / "luks-temporary", target / "part.ks"):
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertGreaterEqual(len(key), 64)
            self.assertTrue(part.endswith(f" --passphrase={key}\n"))
            self.assertIn("--ondisk=" + settings()["disk_id"], part)
            self.assertIn("--encrypted --luks-version=luks2", part)
            keys.append(key)
            with self.assertRaises(FileExistsError):
                exec(script.replace('"/dev/shm/hermes-install"', repr(str(target))), {})
        self.assertNotEqual(*keys)

    def test_reinstall_guard_refuses_existing_hermes_disk_without_explicit_flag(self):
        guard = heredoc(kickstart.render(settings(), MANIFEST), "HERMES_REINSTALL_GUARD")

        def check(labels, cmdline):
            with (
                patch("subprocess.run", return_value=SimpleNamespace(stdout=labels)),
                patch("pathlib.Path.read_text", return_value=cmdline),
            ):
                exec(guard, {})

        check("\n\n", "quiet inst.nosave=all_ks")
        check("hermes-production\n", "inst.nosave=all_ks hermes.reinstall=yes")
        with self.assertRaisesRegex(SystemExit, "already holds Hermes"):
            check("\nhermes-production\n", "inst.nosave=all_ks")
        with self.assertRaises(SystemExit):
            check("hermes-production\n", "inst.nosave=all_ks hermes.reinstall=yes2")

    def test_controller_copy_accepts_only_the_pinned_payload(self):
        payload, files = kickstart.manifest(settings(), self.signers)
        pinned = digest(files)

        def attempt(name, rendered_pin=pinned, tamper=None):
            base = self.root / name
            (base / "media/repo").mkdir(parents=True)
            media.stage(base / "media/repo", payload, files)
            if tamper:
                (base / "media/repo/hermes-installer" / tamper).write_bytes(b"tampered")
            (base / "sysroot/usr/local/libexec").mkdir(parents=True)
            script = heredoc(kickstart.render(settings(), rendered_pin), "HERMES_CONTROLLER_COPY")
            script = script.replace("/run/install", str(base / "media"))
            exec(script.replace("/mnt/sysroot", str(base / "sysroot")), {})
            return base / "sysroot/usr/local/libexec/hermes-installer"

        target = attempt("good")
        for name, data in payload.items():
            self.assertEqual((target / name).read_bytes(), data)
            expected = 0o755 if name in ("productionctl.py", "production-launcher.py") else 0o644
            self.assertEqual(stat.S_IMODE((target / name).stat().st_mode), expected)
        self.assertEqual((target / "manifest.json").read_bytes(), canonical(files))
        # The same media mounted twice (dracut and Anaconda) is accepted.
        twice = self.root / "twice"
        (twice / "media/sources/mount-0000-hdd-device").mkdir(parents=True)
        media.stage(twice / "media/sources/mount-0000-hdd-device", payload, files)
        target = attempt("twice")
        self.assertEqual((target / "manifest.json").read_bytes(), canonical(files))
        with self.assertRaisesRegex(SystemExit, "hash mismatch"):
            attempt("tampered", tamper="production/install.py")
        with self.assertRaisesRegex(SystemExit, "not found"):
            attempt("other-media", rendered_pin="e" * 64)

    def test_install_crypttab_and_keyslot_layout_helpers(self):
        row = f"luks-{LUKS} UUID={LUKS} none discard\n".encode()
        self.assertEqual(install.luks_uuid(b"# comment\n" + row), LUKS)
        for raw in (row + row, f"luks UUID={LUKS} /root/key discard\n".encode(), b""):
            with self.assertRaises(Refused):
                install.luks_uuid(raw)
        changed = install.crypttab_tpm(b"# keep\n" + row, LUKS)
        self.assertEqual(
            changed, f"# keep\nluks-{LUKS} UUID={LUKS} none discard,tpm2-device=auto\n".encode()
        )
        self.assertEqual(install.crypttab_tpm(changed, LUKS), changed)
        embedded = (
            f"luks-{LUKS} /dev/disk/by-uuid/{LUKS} none discard,x-initrd.attach,tpm2-device=auto\n"
        ).encode()
        self.assertEqual(install.crypttab_tpm(embedded, LUKS, embedded=True), embedded)
        with self.assertRaisesRegex(Refused, "row-count"):
            install.crypttab_tpm(embedded, LUKS)
        self.assertEqual(
            install.crypttab_tpm(f"x UUID={LUKS} none\n".encode(), LUKS),
            f"x UUID={LUKS} none tpm2-device=auto\n".encode(),
        )
        for raw, uuid in (
            (f"x UUID={LUKS} none tpm2-pcrs=7\n".encode(), LUKS),
            (row, "43345678-1234-1234-1234-123456789012"),
            (f"x UUID={LUKS} /key discard\n".encode(), LUKS),
        ):
            with self.assertRaises(Refused):
                install.crypttab_tpm(raw, uuid)
        token = {
            "type": "systemd-tpm2",
            "keyslots": ["2"],
            "tpm2-pcrs": [7],
            "tpm2-pcr-bank": "sha256",
        }
        good = {"keyslots": {"1": {}, "2": {}}, "tokens": {"0": token}}
        self.assertEqual(install.token_layout(good, "1"), "2")
        for change in (
            {"tpm2-pin": True},
            {"tpm2-salt": "x"},
            {"tpm2-pcrs": [7, 11]},
            {"tpm2-pcr-bank": "sha1"},
            {"keyslots": ["1"]},
        ):
            with self.subTest(change=change), self.assertRaises(Refused):
                install.token_layout(good | {"tokens": {"0": token | change}}, "1")
        with self.assertRaises(Refused):
            install.token_layout(good | {"keyslots": {"0": {}, "1": {}, "2": {}}}, "1")
        with self.assertRaises(Refused):
            install.token_layout(good | {"tokens": {"0": token, "1": token}}, "1")

    def install_environment(self, initial_slots=("0",)):
        work = self.root / "work"
        work.mkdir(mode=0o700)
        home = self.root / "home/hermesadmin"
        home.mkdir(parents=True)
        boot = self.root / "boot"
        boot.mkdir()
        (boot / "initramfs-6.19.10-300.fc44.x86_64.img").write_bytes(b"image")
        (boot / "initramfs-0-rescue-abc.img").write_bytes(b"rescue")
        crypttab = self.root / "crypttab"
        crypttab.write_bytes(f"luks-{LUKS} UUID={LUKS} none discard\n".encode())
        temporary = "temporary-" + "t" * 60
        (work / "luks-temporary").write_text(temporary)
        state = {"keyslots": {slot: {} for slot in initial_slots}, "tokens": {}}
        calls, sealed = [], {}
        settings_ = kickstart.install_settings(settings())

        def fake(argv, *, data=None, timeout=120, check=True, **kwargs):
            calls.append((list(argv), data))
            out = b""
            if argv[:2] == ["cryptsetup", "luksDump"]:
                out = canonical(state)
            elif argv[:2] == ["cryptsetup", "luksAddKey"]:
                self.assertEqual(Path(argv[3]).read_text(), temporary)
                self.assertEqual(stat.S_IMODE(Path(argv[5]).stat().st_mode), 0o600)
                state["keyslots"]["1"] = {}
            elif argv[0] == "systemd-cryptenroll":
                state["keyslots"]["2"] = {}
                state["tokens"]["0"] = {
                    "type": "systemd-tpm2",
                    "keyslots": ["2"],
                    "tpm2-pcrs": [7],
                    "tpm2-pcr-bank": "sha256",
                }
            elif argv[:2] == ["cryptsetup", "luksRemoveKey"]:
                state["keyslots"].pop("0")
            elif argv[:2] == ["lsinitrd", "-m"]:
                out = b"crypt\nsystemd-cryptsetup\ntpm2-tss\n"
            elif argv[:2] == ["lsinitrd", "-f"]:
                out = crypttab.read_bytes().replace(b"UUID=", b"/dev/disk/by-uuid/")
            elif argv[:2] == ["cryptsetup", "luksHeaderBackup"]:
                Path(argv[-1]).write_bytes(b"HEADER")
            elif argv[0] == "tpm2_pcrread":
                out = b"sha256:\n  7 : 0xAB\n"
            return SimpleNamespace(stdout=out, returncode=0)

        def seal(certificate, content):
            sealed.update(content)
            return b"CIPHERTEXT"

        constants = {
            "WORK": work,
            "STATE": self.root / "state",
            "RECEIPT": self.root / "state/install-receipt.json",
            "CRYPTTAB": crypttab,
            "BOOT": boot,
            "DRACUT": self.root / "60-hermes-tpm.conf",
            "RESTIC_PASSWORD": self.root / "etc/restic-password",
            "UNIT": self.root / "hermes-commission.service",
        }
        for name, value in constants.items():
            self.stack.enter_context(patch.object(install, name, value))
        (self.root / "etc").mkdir()
        account = SimpleNamespace(pw_dir=str(home), pw_uid=os.getuid(), pw_gid=os.getgid())
        for target, value in (
            ("run", fake),
            ("read_json", lambda path, owner=None: settings_),
            ("regular", lambda path, **kwargs: Path(path)),
            ("protected_directory", lambda path, *a, **k: Path(path).mkdir(exist_ok=True)),
            ("check_work", lambda: None),
            ("packages", lambda: None),
        ):
            self.stack.enter_context(patch.object(install, target, value))
        self.stack.enter_context(patch.object(install.os, "geteuid", return_value=0))
        self.stack.enter_context(patch.object(install.os, "chown"))
        self.stack.enter_context(patch.object(install.pwd, "getpwnam", return_value=account))
        self.stack.enter_context(patch.object(install.escrow, "certificate", return_value="f" * 64))
        self.stack.enter_context(patch.object(install.escrow, "seal", side_effect=seal))
        return SimpleNamespace(
            work=work,
            home=home,
            calls=calls,
            sealed=sealed,
            temporary=temporary,
            crypttab=crypttab,
            constants=constants,
        )

    def test_install_commission_orders_keyslots_and_keeps_secrets_out_of_argv(self):
        env = self.install_environment()
        result = install.commission()
        self.assertEqual(result["keyslots"], ["1", "2"])
        argv = [call[0] for call in env.calls]

        def index(prefix):
            return next(i for i, a in enumerate(argv) if a[: len(prefix)] == prefix)

        self.assertLess(index(["cryptsetup", "luksAddKey"]), index(["systemd-cryptenroll"]))
        recovery_test = next(
            i for i, a in enumerate(argv) if "--test-passphrase" in a and "--key-slot" in a
        )
        token_test = next(i for i, a in enumerate(argv) if "--token-only" in a)
        self.assertLess(index(["systemd-cryptenroll"]), recovery_test)
        self.assertLess(recovery_test, token_test)
        self.assertLess(token_test, index(["cryptsetup", "luksRemoveKey"]))
        enroll = argv[index(["systemd-cryptenroll"])]
        for option in ("--tpm2-pcrs=7:sha256", "--tpm2-with-pin=no", "--tpm2-pcrlock="):
            self.assertIn(option, enroll)
        secrets_ = [
            env.temporary,
            env.sealed["recovery-key"].decode(),
            env.sealed["admin-password"].decode(),
            env.sealed["restic-password"].decode(),
        ]
        flat = " ".join(" ".join(a) for a in argv)
        for secret in secrets_:
            self.assertNotIn(secret, flat)
        chpasswd = next(data for a, data in env.calls if a == ["chpasswd"])
        self.assertEqual(chpasswd, f"hermesadmin:{secrets_[2]}\n".encode())
        self.assertEqual(
            (self.root / "etc/restic-password").read_text(), env.sealed["restic-password"].decode()
        )
        self.assertEqual(env.sealed["luks-header.img"], b"HEADER")
        inside = decode(env.sealed["receipt.json"])
        receipt = decode(env.constants["RECEIPT"].read_bytes())
        self.assertEqual(
            receipt["enrollment_nonce_sha256"], digest({"nonce": inside["enrollment_nonce"]})
        )
        self.assertNotIn(inside["enrollment_nonce"], env.constants["RECEIPT"].read_text())
        self.assertTrue(receipt["temporary_slot_removed"])
        self.assertEqual((receipt["recovery_slot"], receipt["tpm_slot"]), ("1", "2"))
        for name in ("recovery-key", "luks-header.img", "escrow-certificate.pem"):
            self.assertFalse((env.work / name).exists())
        escrow_file = env.home / "hermes-escrow.cms"
        self.assertEqual(escrow_file.read_bytes(), b"CIPHERTEXT")
        self.assertEqual(stat.S_IMODE(escrow_file.stat().st_mode), 0o600)
        self.assertIn(b"tpm2-device=auto", env.crypttab.read_bytes())
        self.assertIn(b"commission-boot", env.constants["UNIT"].read_bytes())
        images = [a[-1] for a in argv if a[:2] == ["lsinitrd", "-m"]]
        self.assertEqual([Path(i).name for i in images], ["initramfs-6.19.10-300.fc44.x86_64.img"])
        with self.assertRaisesRegex(Refused, "never-replay"):
            install.commission()

    def test_install_commission_refuses_unexpected_initial_keyslots_before_changes(self):
        env = self.install_environment(initial_slots=("0", "1"))
        with self.assertRaisesRegex(Refused, "unexpected-initial-luks"):
            install.commission()
        self.assertFalse(any(a[0][:2] == ["cryptsetup", "luksAddKey"] for a in env.calls))
        self.assertFalse(env.constants["RECEIPT"].exists())

    def commission_environment(self, kind="fixture"):
        state = self.root / "state"
        directory = state / "commission"
        directory.mkdir(parents=True)
        nonce = "n" * 64
        receipt = {
            "luks_uuid": LUKS,
            "recovery_test": "PASS",
            "installer_tpm_unseal": "PASS",
            "temporary_slot_removed": True,
            "enrollment_nonce_sha256": digest({"nonce": nonce}),
        }
        (state / "install-receipt.json").write_bytes(canonical(receipt))
        boots = [
            {
                "boot_id": "boot-a",
                "tpm_unseals": True,
                "fallback_logged": False,
                "unclean_previous": False,
                "reboot_requested": True,
            },
            {
                "boot_id": "boot-b",
                "tpm_unseals": True,
                "fallback_logged": False,
                "unclean_previous": False,
                "reboot_requested": False,
            },
        ]
        (directory / "boots.json").write_bytes(canonical(boots))
        (directory / "codes.json").write_bytes(
            canonical(
                {"boot_id": "boot-b", "console": digest({"code": "ABCDE-12345"}), "power": None}
            )
        )
        record = self.root / "commissioning.json"
        identity = {"host_sha256": "a" * 64, "boot_sha256": "b" * 64, "packages_sha256": "c" * 64}
        for target, value in (
            ("STATE", state),
            ("RECEIPT", state / "install-receipt.json"),
            ("DIRECTORY", directory),
            ("COMPLETE", state / "commissioned"),
            ("read_json", lambda path, owner=None: decode(Path(path).read_bytes())),
        ):
            self.stack.enter_context(patch.object(commission, target, value))
        self.stack.enter_context(patch.object(commission.preflight, "COMMISSION", record))
        self.stack.enter_context(
            patch.object(
                commission.preflight,
                "collect",
                return_value={"status": "PASS", "commissioning_identity": identity},
            )
        )
        self.boot = self.stack.enter_context(
            patch.object(commission.startup, "boot_id", return_value="boot-b")
        )
        self.issue = self.stack.enter_context(patch.object(commission, "issue"))
        self.stack.enter_context(
            patch.object(commission, "fingerprint", return_value="SHA256:" + "A" * 43)
        )
        cfg = config() | {
            "kind": kind,
            "application_mode": "synthetic" if kind == "fixture" else "production",
        }
        return SimpleNamespace(nonce=nonce, record=record, state=state, config=cfg, boots=boots)

    def test_requested_reboot_clears_the_running_marker_before_rebooting(self):
        env = self.commission_environment()
        (env.state / "commission/boots.json").write_bytes(canonical([]))
        (env.state / "commission/host.json").write_bytes(canonical(env.config))
        (env.state / "bootstrap.json").write_bytes(canonical({"host_sha256": digest(env.config)}))
        installer = self.root / "installer"
        installer.mkdir()
        (installer / "install.json").write_bytes(canonical({}))
        calls = []
        self.boot.return_value = "boot-a"
        with (
            patch.object(commission, "INSTALLER", installer),
            patch.object(commission, "protected_directory"),
            patch.object(commission, "tpm_unseals", return_value=True),
            patch.object(commission, "fallback_logged", return_value=False),
            patch.object(commission, "fingerprint", return_value="SHA256:" + "A" * 43),
            patch.object(commission, "issue"),
            patch.object(commission, "refresh", return_value={"status": "PENDING", "missing": []}),
            patch.object(commission.host, "bootstrap") as bootstrap,
            patch.object(commission, "run", side_effect=lambda argv, **k: calls.append(argv)),
        ):
            result = commission.boot()
        bootstrap.assert_not_called()
        self.assertTrue(result["reboot_requested"])
        self.assertEqual(calls, [["systemctl", "--no-block", "reboot"]])
        self.assertFalse((env.state / "commission/running").exists())
        boots = decode((env.state / "commission/boots.json").read_bytes())
        self.assertEqual([b["reboot_requested"] for b in boots], [True])

    def test_automatic_reboot_requires_requested_clean_tpm_unsealed_successor(self):
        _, second = self.commission_environment().boots
        first = dict(_)
        self.assertIsNotNone(commission.automatic_reboot([first, second]))
        for change in (
            {"unclean_previous": True},
            {"fallback_logged": True},
            {"tpm_unseals": False},
            {"boot_id": "boot-a"},
        ):
            with self.subTest(change=change):
                self.assertIsNone(commission.automatic_reboot([first, second | change]))
        self.assertIsNone(
            commission.automatic_reboot([first | {"reboot_requested": False}, second])
        )

    def test_fixture_commissioning_completes_only_with_decrypted_escrow_nonce(self):
        env = self.commission_environment()
        self.assertEqual(
            commission.refresh(env.config),
            {"status": "PENDING", "missing": ["encrypted_offhost_recovery"]},
        )
        record = decode(env.record.read_bytes())
        self.assertEqual(set(record["gates"]), preflight.PROOFS)
        self.assertTrue(all(len(v) == 64 for v in record["evidence"].values()))
        self.assertEqual(record["gates"]["recovery_unlock"], "PASS")
        self.assertEqual(record["gates"]["automatic_reboot"], "PASS")
        for body, reason in (
            ({"proof": "escrow", "code": "x" * 64}, "code-mismatch"),
            ({"proof": "escrow"}, "invalid-attestation"),
            ({"proof": "root", "code": "x" * 64}, "invalid-attestation"),
            ({"proof": "escrow", "code": "bad code!"}, "invalid-attestation"),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(Refused, reason):
                commission.attest(env.config, body)
        self.assertFalse((env.state / "commissioned").exists())
        self.issue.assert_not_called()
        result = commission.attest(env.config, {"proof": "escrow", "code": env.nonce})
        self.assertEqual(result["status"], "COMMISSIONED")
        self.assertTrue((env.state / "commissioned").exists())
        banner = self.issue.call_args.args[0]
        self.assertIn("  Commissioning complete", banner)
        self.assertFalse(any("code" in line.lower() for line in banner))

    def test_production_also_requires_console_and_power_codes_from_this_boot(self):
        env = self.commission_environment(kind="production")
        commission.attest(env.config, {"proof": "escrow", "code": env.nonce})
        self.assertEqual(
            commission.refresh(env.config)["missing"],
            ["console_access", "firmware_power_restoration"],
        )
        with self.assertRaisesRegex(Refused, "code-mismatch"):
            commission.attest(env.config, {"proof": "power", "code": "ABCDE-12345"})
        self.boot.return_value = "boot-c"
        with self.assertRaisesRegex(Refused, "code-expired"):
            commission.attest(env.config, {"proof": "console", "code": "ABCDE-12345"})
        self.boot.return_value = "boot-b"
        result = commission.attest(env.config, {"proof": "console", "code": "abcde-12345"})
        self.assertEqual(result["missing"], ["firmware_power_restoration"])
        self.assertFalse((env.state / "commissioned").exists())
        self.assertEqual(preflight.required_proofs(env.config), preflight.PROOFS)
        self.assertEqual(
            preflight.required_proofs(env.config | {"kind": "fixture"}), preflight.HOST_PROOFS
        )

    def test_only_the_exact_installer_commissioning_unit_is_not_a_conflict(self):
        root = self.root / "systemd"
        wants = root / "multi-user.target.wants"
        wants.mkdir(parents=True)
        unit = root / "hermes-commission.service"
        with (
            patch.object(preflight, "COMMISSION_UNIT", unit),
            patch.object(preflight.os, "readlink", side_effect=os.readlink),
        ):
            unit.write_bytes(preflight.COMMISSION_UNIT_BYTES)
            unit.chmod(0o644)
            with patch(
                "pathlib.Path.lstat",
                lambda p: SimpleNamespace(st_mode=stat.S_IFREG | 0o644, st_uid=0),
            ):
                self.assertTrue(preflight.commissioning_unit(unit))
            (wants / unit.name).symlink_to("../" + unit.name)
            self.assertTrue(preflight.commissioning_unit(wants / unit.name))
            unit.write_bytes(preflight.COMMISSION_UNIT_BYTES + b"ExecStartPost=/bin/sh\n")
            with patch(
                "pathlib.Path.lstat",
                lambda p: SimpleNamespace(st_mode=stat.S_IFREG | 0o644, st_uid=0),
            ):
                self.assertFalse(preflight.commissioning_unit(unit))
            other = root / "hermes-gateway.service"
            other.write_text("[Service]\n")
            self.assertFalse(preflight.commissioning_unit(other))
            (wants / "hermes-other.service").symlink_to("../hermes-other.service")
            self.assertFalse(preflight.commissioning_unit(wants / "hermes-other.service"))
        self.assertEqual(install.UNIT_BYTES, preflight.COMMISSION_UNIT_BYTES)

    def test_explicit_no_backup_repository_is_accepted_and_backup_refuses(self):
        self.assertEqual(
            preflight.configuration(config() | {"restic_repository": "none"})["restic_repository"],
            "none",
        )
        kickstart.validate(settings() | {"restic_repository": "none"})
        for value in ("None", "local:/srv/backup", "", "sftp:backup@host:relative"):
            with self.subTest(value=value), self.assertRaisesRegex(Refused, "offhost-sftp"):
                preflight.configuration(config() | {"restic_repository": value})
        with (
            patch.object(host.os, "geteuid", return_value=0),
            patch.object(host, "read_json", return_value=config() | {"restic_repository": "none"}),
            patch.object(host.preflight, "enforce") as enforce,
            self.assertRaisesRegex(Refused, "backup-not-configured"),
        ):
            host.dispatch(io.BytesIO(canonical({"operation": "backup", "apply": True})))
        enforce.assert_not_called()

    def test_dispatcher_attestation_and_credential_bounds(self):
        production = config()
        synthetic = config() | {"kind": "fixture", "application_mode": "synthetic"}

        def dispatch(cfg, request, body=b""):
            with (
                patch.object(host.os, "geteuid", return_value=0),
                patch.object(host, "read_json", return_value=cfg),
                patch.object(host.preflight, "enforce") as enforce,
            ):
                result = host.dispatch(io.BytesIO(canonical(request) + body))
                enforce.assert_not_called()
                return result

        with self.assertRaisesRegex(Refused, "attestation-requires-apply"):
            dispatch(production, {"operation": "attest", "apply": False})
        with self.assertRaisesRegex(Refused, "invalid-request-body"):
            dispatch(production, {"operation": "attest", "apply": True}, b"x" * 5000)
        with self.assertRaisesRegex(Refused, "production-mode"):
            dispatch(synthetic, {"operation": "credentials", "apply": False}, ENV_DOC)
        preview = dispatch(production, {"operation": "credentials", "apply": False}, ENV_DOC)
        self.assertEqual(
            preview, {"status": "PREVIEW", "operation": "credentials", "document": "VALID"}
        )
        self.assertNotIn("synthetic", canonical(preview).decode())
        for body, reason in (
            (ENV_DOC + b"OPENAI_API_KEY=x\n", "unexpected-credential-fields"),
            (b"x" * 16385, "too-large"),
            (b"\xff\xfe", "invalid-credential-file"),
        ):
            with self.subTest(reason=reason), self.assertRaisesRegex(Refused, reason):
                dispatch(production, {"operation": "credentials", "apply": False}, body)
        backend = SimpleNamespace(current=lambda: None)
        with (
            patch.object(host.preflight, "collect", return_value={"status": "PASS"}),
            patch.object(host, "Backend", return_value=backend),
            patch.object(host, "lock", return_value=nullcontext()),
            patch.object(host, "store_credentials") as store,
        ):
            stored = dispatch(production, {"operation": "credentials", "apply": True}, ENV_DOC)
        store.assert_called_once_with(ENV_DOC)
        self.assertEqual(stored, {"status": "STORED", "restarted": False})

    def test_operator_setup_creates_keys_trust_and_valid_production_settings(self):
        server = {
            k: settings()[k]
            for k in (
                "disk_id",
                "disk_min_mib",
                "root_mib",
                "var_mib",
                "hermes_mib",
                "hostname",
                "timezone",
                "deploy_from",
                "artifact_budget_bytes",
                "state_budget_bytes",
            )
        } | {"restic_repository": "none"}
        real_run, real_generate = client.run, escrow.generate

        def keygen(argv, **kwargs):
            # The real command prompts on the terminal; tests supply an empty passphrase.
            if argv[0] == "ssh-keygen" and "-N" not in argv:
                argv = [*argv, "-N", ""]
            return real_run(argv, **kwargs)

        out = self.root / "operator"
        with (
            patch.object(client, "run", side_effect=keygen),
            patch.object(
                client.escrow,
                "generate",
                side_effect=lambda d, encrypt, apply: real_generate(d, encrypt=False, apply=apply),
            ),
        ):
            self.assertEqual(client.operator_setup(out, server)["status"], "PREVIEW")
            self.assertFalse(out.exists())
            result = client.operator_setup(out, server, apply=True)
        self.assertEqual(result["status"], "CREATED")
        self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o700)
        installed = json.loads((out / "install.json").read_text())
        kickstart.validate(installed)
        self.assertEqual(installed["kind"], "production")
        self.assertEqual(installed["restic_repository"], "none")
        self.assertNotEqual(installed["admin_public_key"], installed["deploy_public_key"])
        for key in ("admin_ed25519", "deploy_ed25519", "signing_ed25519", "install.json"):
            self.assertEqual(stat.S_IMODE((out / key).stat().st_mode), 0o600, key)
        self.assertTrue(
            (out / "allowed_signers").read_text().startswith('hermes-production namespaces="')
        )
        payload, _ = kickstart.manifest(installed, out / "allowed_signers")
        self.assertIn("allowed_signers", payload)
        with self.assertRaisesRegex(Refused, "operator-directory-exists"):
            client.operator_setup(out, server, apply=True)

    def test_credentials_reapply_contract_before_restart_and_restore_on_failure(self):
        state_dir = self.root / "gateway-state"
        state_dir.mkdir(mode=0o700)
        stored = state_dir / ".env"
        stored.write_bytes(b"OLD\n")
        stored.chmod(0o600)
        calls = []

        class Backend:
            uid = os.getuid()

            def __init__(self, config, fail=False):
                self.fail = fail

            def current(self):
                return "release-a"

            def initialize_namespace(self):
                calls.append("namespace")

            def stop(self):
                calls.append("stop")

            def configure(self, release):
                calls.append(("configure", stored.read_bytes()))
                if self.fail:
                    raise Refused("configure-failed")

            def restart_previous(self, release):
                calls.append(("restart", stored.read_bytes()))

            def verify(self, release):
                calls.append("verify")

        def store(data):
            atomic(stored, data, 0o600)

        def provision(fail):
            calls.clear()
            with (
                patch.object(host, "HOME", self.root),
                patch.object(host.preflight, "collect", return_value={"status": "PASS"}),
                patch.object(host, "Backend", lambda config: Backend(config, fail)),
                patch.object(host, "lock", return_value=nullcontext()),
                patch.object(host.startup, "operation", return_value=nullcontext()),
                patch.object(host, "run"),
                patch.object(host, "Transaction"),
                patch.object(host, "store_credentials", side_effect=store),
            ):
                return host.provision_credentials(config(), io.BytesIO(ENV_DOC), apply=True)

        result = provision(fail=False)
        self.assertEqual(result["status"], "STORED")
        self.assertEqual(
            calls,
            ["namespace", "stop", ("configure", ENV_DOC), ("restart", ENV_DOC), "verify"],
        )
        stored.write_bytes(b"OLD\n")
        with self.assertRaisesRegex(Refused, "configure-failed"):
            provision(fail=True)
        self.assertEqual(calls[-1], ("restart", b"OLD\n"))
        self.assertNotIn("verify", calls)
        self.assertEqual(stored.read_bytes(), b"OLD\n")

    def test_remote_client_waits_for_the_server_result_after_it_stops_reading(self):
        spec = importlib.util.spec_from_file_location(
            "productionctl_remote_test", ROOT / "scripts/hermes/productionctl.py"
        )
        ctl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ctl)
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "ssh"
        fake.write_text(
            f"#!{sys.executable}\n"
            "import os, sys\n"
            "sys.stdin.buffer.readline()  # request header only; never read the archive\n"
            "mode = os.environ['HERMES_FAKE_SSH']\n"
            "if mode == 'result': print('{\"status\":\"CHANGED\"}'); sys.exit(0)\n"
            "if mode == 'stop': print('STOP: operation-busy', file=sys.stderr); sys.exit(1)\n"
            'if mode == \'report\': print(\'{"status":"FAIL","checks":{}}\'); sys.exit(1)\n'
            "print('Traceback (most recent call last): secret=leak', file=sys.stderr); sys.exit(1)\n"
        )
        fake.chmod(0o700)
        known, identity, archive = (self.root / n for n in ("known", "identity", "release.tar"))
        known.write_text("x\n")
        identity.write_text("x\n")
        identity.chmod(0o600)
        archive.write_bytes(os.urandom(8 * 1024 * 1024))  # far larger than any pipe buffer
        args = SimpleNamespace(
            host="10.0.30.10",
            port=22,
            known_hosts=known,
            identity=identity,
            operation="deploy",
            apply=True,
            bundle=archive,
        )

        def remote(mode):
            path = str(bin_dir) + os.pathsep + os.environ["PATH"]
            with patch.dict(os.environ, {"PATH": path, "HERMES_FAKE_SSH": mode}):
                return ctl.remote(args)

        self.assertEqual(remote("result"), {"status": "CHANGED"})
        with self.assertRaisesRegex(Refused, "^remote:operation-busy$"):
            remote("stop")
        self.assertEqual(remote("report"), {"status": "FAIL", "checks": {}})
        with self.assertRaisesRegex(Refused, "^remote-operation-failed$"):
            remote("silent")

    def test_pin_host_requires_the_console_fingerprint(self):
        key = self.root / "host_key"
        run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)])
        public = (self.root / "host_key.pub").read_text().split()
        line = f"[127.0.0.1]:22224 {public[0]} {public[1]}\n"
        expected = run(["ssh-keygen", "-lf", str(key) + ".pub"]).stdout.split()[1].decode()
        real = client.run

        def fake(argv, **kwargs):
            if argv[0] == "ssh-keyscan":
                return SimpleNamespace(stdout=("# banner\n" + line).encode(), returncode=0)
            return real(argv, **kwargs)

        known = self.root / "known_hosts"
        with patch.object(client, "run", side_effect=fake):
            with self.assertRaisesRegex(Refused, "fingerprint-mismatch"):
                client.pin_host("127.0.0.1", 22224, "SHA256:" + "A" * 43, known, apply=True)
            self.assertFalse(known.exists())
            with self.assertRaisesRegex(Refused, "invalid-console-fingerprint"):
                client.pin_host("127.0.0.1", 22224, "MD5:aa", known, apply=True)
            self.assertEqual(
                client.pin_host("127.0.0.1", 22224, expected, known, apply=True)["status"], "PINNED"
            )
            self.assertEqual(known.read_text(), line)
            self.assertEqual(stat.S_IMODE(known.stat().st_mode), 0o600)
            client.pin_host("127.0.0.1", 22224, expected, known, apply=True)
            known.write_text("[127.0.0.1]:22224 ssh-ed25519 AAAAother\n")
            with self.assertRaisesRegex(Refused, "other-key"):
                client.pin_host("127.0.0.1", 22224, expected, known, apply=True)

    def test_media_build_verifies_embedded_payload_and_firmware_boot_arguments(self):
        source = self.root / "settings.json"
        source.write_bytes(
            canonical(settings() | {"kind": "fixture", "application_mode": "synthetic"})
        )
        iso = self.root / "Fedora-Server-dvd-x86_64-44-1.7.iso"
        iso.write_bytes(b"media")
        calls, state = [], {"corrupt": False, "image": True}

        EFIBOOT = b"efiboot".ljust(512, b"\0")

        def fake(argv, **kwargs):
            calls.append(argv)
            if argv[:3] == ["podman", "image", "exists"]:
                return SimpleNamespace(stdout=b"", returncode=0 if state["image"] else 1)
            if argv[:2] == ["sfdisk", "--json"]:
                partitions = [
                    {"start": 0, "size": 1, "type": "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7"},
                    {"start": 1, "size": 1, "type": "C12A7328-F81F-11D2-BA4B-00A0C93EC93B"},
                ]
                table = {"label": "gpt", "sectorsize": 512, "partitions": partitions}
                return SimpleNamespace(stdout=canonical({"partitiontable": table}), returncode=0)
            if argv[0] == "cp":
                shutil.copyfile(argv[-2], argv[-1])
            elif argv[:2] == ["podman", "run"]:
                self.assertIn("--network=none", argv)
                self.assertIn("--cap-drop=all", argv)
                host_dir = argv[argv.index("-v") + 1].rsplit(":/work:Z", 1)[0]
                inner = argv[argv.index(media.TOOLS_IMAGE) + 1 :]

                def local(path):
                    return Path(path.replace("/work", host_dir, 1))

                if inner[0] == "mkksiso":
                    self.assertIn("--skip-mkefiboot", inner)
                    ks = local(inner[inner.index("--ks") + 1])
                    staged = local(inner[inner.index("--add") + 1]) / "manifest.json"
                    state["staged"] = (ks.read_bytes(), staged.read_bytes())
                    state["mkksiso"] = inner
                    args = inner[inner.index("-c") + 1]
                    if state.get("strip"):
                        args = args.replace("inst.nosave=all_ks ", "")
                    state["grub"] = (
                        'set default="0"\nmenuentry x {\n\tlinux /vmlinuz quiet '
                        f"{args} inst.ks=hd:LABEL=X:/hermes-production.ks\n}}\n"
                    )
                    local(inner[-1]).write_bytes(b"stage iso")
                elif inner[0] == "xorriso" and "-pvd_info" in inner:
                    return SimpleNamespace(
                        stdout=b"Volume Set Id: x\nVolume Id    : Fedora-S-dvd-x86_64-44\n",
                        returncode=0,
                    )
                elif inner[0] == "xorriso" and "-extract" in inner:
                    for i, word in enumerate(inner):
                        if word != "-extract":
                            continue
                        inside, target = inner[i + 1], local(inner[i + 2])
                        if inside.endswith("manifest.json"):
                            data = b"{}" if state["corrupt"] else state["staged"][1]
                        elif inside.endswith(".ks"):
                            data = state["staged"][0]
                        elif inside.endswith("grub.cfg"):
                            data = state["grub"].encode()
                        else:
                            data = EFIBOOT
                        target.write_bytes(data)
                elif inner[0] == "xorriso":
                    self.assertEqual(inner[inner.index("-boot_image") + 1 :][:2], ["any", "replay"])
                    append = inner.index("-append_partition")
                    self.assertEqual(
                        inner[append + 1 : append + 4], ["2", "0xef", "/work/efiboot.img"]
                    )
                    # Sector 0 is padding; sector 1 is the USB EFI System Partition.
                    esp = b"stale-dvd-esp".ljust(512, b"\0") if state.get("stale") else EFIBOOT
                    local(inner[inner.index("-outdev") + 1]).write_bytes(b"\0" * 512 + esp)
                elif inner[0] == "mcopy":
                    state.setdefault("mcopy", []).append(inner[-1])
                elif inner[0] == "mtype":
                    return SimpleNamespace(stdout=state["grub"].encode(), returncode=0)
            return SimpleNamespace(stdout=b"", returncode=0)

        output = self.root / "out/hermes.iso"
        output.parent.mkdir()
        with (
            patch.object(media, "verify_iso", return_value=sha(iso)),
            patch.object(media, "run", side_effect=fake),
        ):
            preview = media.build(source, self.signers, iso, iso, output, serial_console=True)
            self.assertEqual(preview["status"], "PREVIEW")
            self.assertEqual(
                preview["boot_arguments"], "inst.nosave=all_ks inst.text console=ttyS0,115200n8"
            )
            self.assertFalse(calls)
            built = media.build(
                source, self.signers, iso, iso, output, serial_console=True, apply=True
            )
            self.assertEqual(built["status"], "BUILT")
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            inner = state["mkksiso"]
            self.assertEqual(
                inner[inner.index("-c") + 1],
                preview["boot_arguments"] + " inst.repo=hd:LABEL=Fedora-S-dvd-x86_64-44",
            )
            self.assertEqual(
                built["installation_source"], "inst.repo=hd:LABEL=Fedora-S-dvd-x86_64-44"
            )
            self.assertEqual(inner[-2:], ["/work/dvd.iso", "/work/stage.iso"])
            self.assertEqual(state["mcopy"], ["::/EFI/BOOT/grub.cfg", "::/EFI/BOOT/BOOT.conf"])
            self.assertEqual(
                decode(state["staged"][1]),
                kickstart.manifest(decode(source.read_bytes()), self.signers)[1],
            )
            with self.assertRaisesRegex(Refused, "media-output-exists"):
                media.build(source, self.signers, iso, iso, output, apply=True)
            other = self.root / "out/corrupt.iso"
            state["corrupt"] = True
            with self.assertRaisesRegex(Refused, "iso-payload-mismatch"):
                media.build(source, self.signers, iso, iso, other, apply=True)
            self.assertFalse(other.exists())
            state["corrupt"], state["stale"] = False, True
            stale = self.root / "out/stale-esp.iso"
            with self.assertRaisesRegex(Refused, "usb-efi-partition-not-updated"):
                media.build(source, self.signers, iso, iso, stale, apply=True)
            self.assertFalse(stale.exists())
            state["stale"], state["strip"] = False, True
            third = self.root / "out/no-args.iso"
            with self.assertRaisesRegex(Refused, "uefi-boot-arguments-missing"):
                media.build(source, self.signers, iso, iso, third, apply=True)
            self.assertFalse(third.exists())
            state["image"] = False
            with self.assertRaisesRegex(Refused, "media-tools-image-missing"):
                media.build(source, self.signers, iso, iso, other, apply=True)
            self.assertEqual(sorted(p.name for p in output.parent.iterdir()), ["hermes.iso"])


class ProductionQualifyPipelineTests(ProductionBundleFixture):
    """Pipeline logic only: real temporary signed bundles; no VM, libvirt or network."""

    def setUp(self):
        super().setUp()
        spec = importlib.util.spec_from_file_location(
            "production_qualify_test", ROOT / "vm/hermes-production-qualify.py"
        )
        self.qualify = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.qualify)

    def test_derived_upgrade_is_signed_and_corrupt_variant_is_refused(self):
        directory = self.root / "run"
        directory.mkdir()
        shutil.copyfile(self.archive, directory / "candidate.tar")
        shutil.copyfile(self.key, directory / "signing_ed25519")
        (directory / "signing_ed25519").chmod(0o600)
        identities = self.qualify.derive_candidates(directory)

        def unpack(name):
            with (directory / name).open("rb") as stream:
                return bundle.unpack(stream, self.root / ("out-" + name), self.signers)

        baseline = unpack("candidate.tar")
        self.assertEqual(identities["candidate"], bundle.identity(baseline))
        upgraded = unpack("upgrade.tar")
        self.assertEqual(identities["upgrade"], bundle.identity(upgraded))
        self.assertNotEqual(identities["upgrade"], identities["candidate"])
        self.assertEqual(receivers.expected(upgraded), receivers.expected(baseline))
        with self.assertRaisesRegex(Refused, "artifact-hash-mismatch"):
            unpack("corrupt.tar")

    def test_gates_never_overstate_a_local_run(self):
        args = SimpleNamespace(no_offhost_backup=False, live_env=None)
        run_ = self.qualify.Run(args)
        everything = {name for stages in self.qualify.GATE_STAGES.values() for name in stages}
        self.assertLessEqual(everything, set(self.qualify.STAGES))
        self.assertEqual(set(self.qualify.GATE_STAGES), bundle.GATES)
        run_.stages = [
            {"stage": name, "status": "PASS"}
            for name in self.qualify.STAGES
            if name not in self.qualify.LIVE_ONLY
        ]
        gates = run_.gates()
        for gate in ("repository", "installation", "runtime", "repeatability", "boot"):
            self.assertEqual(gates[gate], "PASS", gate)
        self.assertEqual(gates["restore"], "BLOCKED")
        self.assertEqual(gates["application"], "BLOCKED")
        self.assertEqual(run_.waivers(), {})
        args.no_offhost_backup = True
        self.assertEqual(run_.gates()["restore"], "PASS")
        self.assertIn("no off-host backup", run_.waivers()["restore"])
        args.live_env = "gateway.env"
        self.assertEqual(run_.gates()["application"], "NOT_RUN")
        run_.stages.append({"stage": "application", "status": "PASS"})
        self.assertEqual(set(run_.gates().values()), {"PASS"})
        run_.stages[-1]["status"] = "FAIL"
        self.assertEqual(run_.gates()["application"], "FAIL")
        interrupted = next(r for r in run_.stages if r["stage"] == "interrupted_upgrade")
        interrupted["status"] = "FAIL"
        self.assertEqual(run_.gates()["repeatability"], "FAIL")
        self.assertEqual(run_.gates()["restore"], "FAIL")

    def test_every_stage_has_a_method_and_live_questions_cover_approval(self):
        missing = [
            name
            for name in self.qualify.STAGES
            if not callable(getattr(self.qualify.Run, name, None))
        ]
        self.assertEqual(missing, [])
        self.assertTrue(callable(getattr(self.qualify.Run, "evidence", None)))
        source = Path(self.qualify.__file__).read_text()
        self.assertIn("rm -rf /tmp/hermes-approval-check", source)
        self.assertIn("DENY it", source)

    def test_previous_vm_removal_requires_pipeline_ownership(self):
        vm = self.root / "vm"
        vm.mkdir()
        (vm / "ownership.json").write_bytes(canonical({"role": "qualification"}))
        with (
            patch.object(self.qualify, "VM_DIR", vm),
            patch.object(
                self.qualify, "virsh", return_value=SimpleNamespace(stdout=b"", returncode=0)
            ) as virsh,
        ):
            with self.assertRaisesRegex(Refused, "unowned-qualification-resources"):
                self.qualify.replace_previous()
            self.assertTrue(vm.exists())
            (vm / "ownership.json").write_bytes(canonical({"role": "qualify"}))
            self.assertEqual(self.qualify.replace_previous(), "REMOVED")
            self.assertFalse(vm.exists())
            self.assertFalse(any(c.args[0] == "undefine" for c in virsh.call_args_list))


if __name__ == "__main__":
    unittest.main()
