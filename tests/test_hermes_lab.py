"""Synthetic failure and convergence tests; no VM, root or network operations."""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/hermes"))
import lab  # noqa: E402
import lab_profile as profile  # noqa: E402
import lab_runtime as runtime  # noqa: E402


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.profile = profile.load(lab.PROFILES / "baseline.json")

    def test_baseline_matches_reviewed_manifest(self):
        self.assertIn(
            "ref: " + self.profile["gateway_image"],
            (ROOT / "scripts/hermes/manual/manifest.yaml").read_text(),
        )

    def test_invalid_fields_and_secret_values_are_not_echoed(self):
        for key, value in (
            ("api_key", "PRIVATE_SENTINEL"),
            ("model", "PRIVATE_SENTINEL"),
            ("gateway_image", "latest"),
            ("version", True),
        ):
            candidate = copy.deepcopy(self.profile)
            candidate[key] = value
            with self.assertRaises(profile.ProfileError) as failure:
                profile.validate(candidate)
            self.assertNotIn("PRIVATE_SENTINEL", str(failure.exception))

    def test_limits_reject_bool_negative_and_oversized(self):
        for value in (True, -1, 100000, "2048"):
            candidate = copy.deepcopy(self.profile)
            candidate["gateway"]["memory_mb"] = value
            with self.assertRaises(profile.ProfileError):
                profile.validate(candidate)

    def test_render_preserves_security_and_locks_worker(self):
        text = (ROOT / "scripts/hermes/manual/quadlets/hermes-worker.container").read_text()
        rendered = profile.render_unit(text, "worker", self.profile, "sha256:" + "a" * 64)
        self.assertIn("Network=none", rendered)
        self.assertIn("NoNewPrivileges=true", rendered)
        self.assertIn("ReadOnly=true", rendered)
        self.assertIn("Image=sha256:" + "a" * 64, rendered)
        self.assertIn("Memory=2048m", rendered)
        with self.assertRaises(profile.ProfileError):
            profile.render_unit(text, "worker", self.profile, "latest")

    def test_profile_cannot_override_contract(self):
        self.profile["security"] = {"allow_all_users": True}
        with self.assertRaises(profile.ProfileError):
            profile.validate(self.profile)


class LabTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = pathlib.Path(self.temp.name) / "state"
        self.addCleanup(patch.stopall)
        patch.object(runtime, "STATE", self.state).start()
        patch.object(lab, "STATE", self.state).start()
        self.profile = profile.load(lab.PROFILES / "candidate.json")

    def test_all_mutations_preview_without_state_or_commands(self):
        with (
            patch.object(subprocess, "run", side_effect=AssertionError("external command")),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            for action in ("prepare", "up", "deploy", "clean"):
                self.assertEqual(lab.main([action]), 0)
            self.assertEqual(lab.main(["test", "--suite", "vm"]), 0)
            self.assertEqual(lab.main(["test", "--suite", "candidate"]), 0)
        self.assertFalse(self.state.exists())

    def test_invalid_instance_never_traverses_paths(self):
        for name in ("../outside", "UPPER", "x/../../y", "-unsafe", "x" * 33):
            with self.assertRaises(runtime.LabError):
                runtime.Instance(name, self.profile)

    def test_duplicate_operation_is_refused(self):
        with runtime.lock("instance-dev"):
            with self.assertRaisesRegex(runtime.LabError, "lock"):
                with runtime.lock("instance-dev"):
                    self.fail("second lock was acquired")

    def test_symlink_instance_is_refused(self):
        self.state.mkdir()
        (self.state / "instances").symlink_to(self.temp.name)
        with self.assertRaisesRegex(runtime.LabError, "symlink"):
            runtime.Instance("dev", self.profile)

    def make_cache(self):
        key = runtime.cache_key(self.profile)
        cache = self.state / "prepared" / key
        cache.mkdir(parents=True)
        for name in ("base.qcow2", "gateway.oci", "worker.oci"):
            (cache / name).write_bytes(b"synthetic")
        data = {
            "key": key,
            "gateway_ref": self.profile["gateway_image"],
            "gateway_id": "sha256:" + "a" * 64,
            "worker_id": "sha256:" + "b" * 64,
            "files": {
                name: profile.file_hash(cache / name)
                for name in ("base.qcow2", "gateway.oci", "worker.oci")
            },
        }
        (cache / "manifest.json").write_text(json.dumps(data))
        return cache, data

    def test_cache_checks_content_identity_and_completeness(self):
        cache, _ = self.make_cache()
        self.assertEqual(runtime.read_cache(self.profile)[0], cache)
        (cache / "worker.oci").write_bytes(b"corrupt")
        with self.assertRaisesRegex(runtime.LabError, "checksum"):
            runtime.read_cache(self.profile)
        (cache / "extra").touch()
        with self.assertRaisesRegex(runtime.LabError, "unexpected"):
            runtime.read_cache(self.profile)

    def test_configuration_change_reuses_cache_but_release_change_does_not(self):
        changed = copy.deepcopy(self.profile)
        changed["model"] = "deepseek-reasoner"
        changed["gateway"]["pids_limit"] += 1
        self.assertEqual(runtime.cache_key(self.profile), runtime.cache_key(changed))
        changed["gateway_image"] = "docker.io/nousresearch/hermes-agent@sha256:" + "c" * 64
        self.assertNotEqual(runtime.cache_key(self.profile), runtime.cache_key(changed))

    def test_interrupted_creation_keeps_ownership_marker(self):
        instance = runtime.Instance("dev", self.profile)
        instance.path.parent.mkdir(parents=True)
        instance.vm.PORT = 22223

        def command(argv, **kwargs):
            if argv[0] == "virt-install":
                raise instance.vm.LabError("injected create failure")
            return subprocess.CompletedProcess(argv, 0, "", "")

        with (
            patch.object(instance.vm, "domain_exists", return_value=False),
            patch.object(instance.vm, "create_seed"),
            patch.object(instance.vm, "run", side_effect=command),
        ):
            with self.assertRaises(instance.vm.LabError):
                instance.vm.fresh_run(pathlib.Path("/synthetic-base"), deploy_now=False)
        marker = json.loads((instance.path / "identity.json").read_text())
        self.assertEqual(marker["port"], 22223)
        self.assertEqual(marker["name"], "hermes-lab-dev")
        self.assertTrue(marker["uuid"])

    def test_changed_uuid_blocks_guest_commands(self):
        instance = runtime.Instance("dev", self.profile)
        instance.path.mkdir(parents=True)
        (instance.path / "identity.json").write_text(
            json.dumps(
                {
                    "name": instance.vm.NAME,
                    "uuid": "old",
                    "disk": str(instance.path / "disk.qcow2"),
                    "seed": str(instance.path / "seed.iso"),
                }
            )
        )
        with (
            patch.object(
                instance.vm,
                "virsh",
                return_value=subprocess.CompletedProcess([], 0, "different", ""),
            ),
            patch.object(instance.vm, "run") as command,
        ):
            with self.assertRaises(instance.vm.LabError):
                instance.vm.guest("true")
            command.assert_not_called()

    def test_report_records_failed_step_without_raw_error(self):
        with patch.object(lab, "source_identity", return_value={}):
            report = lab.Report(self.profile, "test")
        with self.assertRaises(RuntimeError), contextlib.redirect_stdout(io.StringIO()):
            report.step(
                "synthetic-failure", lambda: (_ for _ in ()).throw(RuntimeError("PRIVATE_SENTINEL"))
            )
        data = (report.path / "report.json").read_text()
        self.assertIn('"status": "FAIL"', data)
        self.assertNotIn("PRIVATE_SENTINEL", data)

    def test_backup_checksum_failure_never_contacts_guest(self):
        archive = pathlib.Path(self.temp.name) / "backup.tar"
        archive.write_bytes(b"changed")
        instance = runtime.Instance("dev", self.profile)
        with patch.object(instance, "copy_to") as transfer:
            with self.assertRaisesRegex(runtime.LabError, "checksum"):
                lab.restore_backup(instance, archive, {"archive_sha256": "bad"})
            transfer.assert_not_called()

    def test_cleanup_preflights_unknown_files_before_stopping_domain(self):
        instance = runtime.Instance("dev", self.profile)
        instance.path.mkdir(parents=True)
        (instance.path / "unrelated").write_text("preserve")
        with patch.object(instance.vm, "clean") as clean:
            with self.assertRaisesRegex(runtime.LabError, "unexpected"):
                instance.clean()
            clean.assert_not_called()

    def test_no_free_port_does_not_create_a_vm(self):
        instance = runtime.Instance("dev", self.profile)
        with (
            patch.object(instance, "exists", return_value=False),
            patch.object(runtime.socket, "socket") as socket,
            patch.object(instance.vm, "fresh_run") as create,
        ):
            socket.return_value.__enter__.return_value.bind.side_effect = OSError("in use")
            with self.assertRaisesRegex(runtime.LabError, "free"):
                instance.boot(pathlib.Path("/synthetic-base"))
            create.assert_not_called()

    def test_unsafe_guest_state_prevents_artifact_transfer(self):
        instance = runtime.Instance("dev", self.profile)
        with (
            patch.object(
                instance.vm, "guest", return_value=subprocess.CompletedProcess([], 1, "", "")
            ) as guest,
            patch.object(instance, "artifacts") as artifacts,
        ):
            with self.assertRaisesRegex(runtime.LabError, "unsafe"):
                instance.install_artifacts(pathlib.Path("/unused"), {})
            artifacts.assert_not_called()
            self.assertTrue(guest.call_args.args[0].startswith("sudo -n python3"))

    def test_guest_diagnostics_only_export_known_reasons(self):
        instance = runtime.Instance("dev", self.profile)
        error = instance.vm.LabError("untrusted failure PRIVATE_SENTINEL")
        for stderr in ("PRIVATE_SENTINEL", "STOP: unknown PRIVATE_SENTINEL"):
            with patch.object(
                instance.vm, "guest", return_value=subprocess.CompletedProcess([], 1, "", stderr)
            ):
                self.assertEqual(lab.failure_reason(error, instance), "LabError")
        with patch.object(
            instance.vm,
            "guest",
            return_value=subprocess.CompletedProcess(
                [],
                1,
                "",
                "STOP: effective Hermes configuration differs from the requested profile\n",
            ),
        ):
            self.assertIn("configuration differs", lab.failure_reason(error, instance))


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            "profile_deploy_test", ROOT / "scripts/hermes/profile-deploy.py"
        )
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_oci_exports_do_not_retain_incompatible_registry_digest_names(self):
        import lab_guest as g

        raw_id = "a" * 64
        saves = []

        def podman(*args):
            if args[0] == "save":
                saves.append(args)
                pathlib.Path(args[4]).touch()
            return subprocess.CompletedProcess([], 0, raw_id + "\n", "")

        with (
            tempfile.TemporaryDirectory() as temp,
            patch.object(g, "EXPORT", pathlib.Path(temp) / "export"),
            patch.object(g.deploy, "require_host"),
            patch.object(g.deploy, "ensure_user", return_value=(0, 0)),
            patch.object(g.deploy, "pinned_gateway", return_value="registry@sha256:" + "b" * 64),
            patch.object(g, "inventory", return_value={}),
            patch.object(g.os, "chown"),
            patch.object(g.deploy, "podman", side_effect=podman),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            g.export_images()
        self.assertEqual(len(saves), 2)
        self.assertTrue(all(args[-1] == raw_id for args in saves))
        self.assertEqual(json.loads(output.getvalue())["gateway_id"], "sha256:" + raw_id)

    def test_model_verifier_uses_selected_model(self):
        self.module.MODEL = "deepseek-reasoner"
        with patch.object(
            self.module, "podman", return_value=subprocess.CompletedProcess([], 0, "", "")
        ) as podman:
            self.assertTrue(self.module.model_check())
        code = podman.call_args.args[-1]
        self.assertIn("deepseek-reasoner", code)
        self.assertNotIn("deepseek-flash", code)

    def test_failed_apply_does_not_report_success(self):
        d = self.module
        with (
            patch.object(d, "prepare", return_value=False),
            patch.object(d, "ensure_user", return_value=(1001, 1001)),
            patch.object(d, "active", return_value=True),
            patch.object(d, "ensure_instance", return_value=False),
            patch.object(d, "config_current", return_value=True),
            patch.object(d, "install_quadlets", side_effect=d.DeployError("injected failure")),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            with self.assertRaises(d.DeployError):
                d.apply("synthetic")
        self.assertNotIn("DEPLOY=", output.getvalue())

    def test_upstream_initialization_precedes_final_hardening(self):
        d = self.module
        with patch.object(d, "podman") as podman:
            d.configure("synthetic-image")
        self.assertIn("load_config()", podman.call_args_list[-2].args[-1])
        self.assertEqual(
            podman.call_args_list[-1].args[-1], "/opt/hermes/gateway-ssh/harden-config.py"
        )

    def test_runtime_hooks_equivalence_is_narrow(self):
        spec = importlib.util.spec_from_file_location(
            "contract", ROOT / "scripts/hermes/manual/config/harden-config.py"
        )
        contract = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(contract)
        canonical = {"hooks": {}, "security": {"redact_secrets": True}}
        self.assertEqual(
            contract.runtime_effective({"hooks": None, "security": {"redact_secrets": True}}),
            canonical,
        )
        self.assertNotEqual(contract.effective({"hooks": None}), {"hooks": {}})
        for hooks in ({"on_start": ["malicious"]}, [], "{}"):
            self.assertNotEqual(contract.runtime_effective({"hooks": hooks}), {"hooks": {}})
        self.assertEqual(contract.runtime_effective({}), {"hooks": {}})
        self.assertNotEqual(
            contract.runtime_effective({"hooks": None, "security": {"redact_secrets": False}}),
            canonical,
        )


class RestoreTests(unittest.TestCase):
    def setUp(self):
        import lab_guest

        self.guest = lab_guest
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = pathlib.Path(self.temp.name) / "home"
        self.home.mkdir()
        for tree in self.guest.TREES:
            (self.home / tree).mkdir()
            (self.home / tree / "marker").write_text("original")
        self.archive = pathlib.Path(self.temp.name) / "backup.tar"
        import tarfile

        with tarfile.open(self.archive, "w") as tar:
            for tree in self.guest.TREES:
                tar.add(self.home / tree, arcname=tree)
        self.addCleanup(patch.stopall)
        patch.object(self.guest, "HOME", self.home).start()
        patch.object(self.guest, "RESTORE_ARCHIVE", self.archive).start()
        patch.object(self.guest, "synthetic").start()
        patch.object(self.guest.deploy, "locked", side_effect=contextlib.nullcontext).start()

    def test_failed_extraction_preserves_state_and_does_not_stop_services(self):
        g = self.guest
        with (
            patch.object(g, "cmd", side_effect=g.deploy.DeployError("extract failed")),
            patch.object(g, "stop_writers") as stop,
        ):
            with self.assertRaises(g.deploy.DeployError):
                g.restore(g.state_manifest())
            stop.assert_not_called()
        self.assertEqual((self.home / "gateway-state/marker").read_text(), "original")

    def test_partial_swap_rolls_back_before_restarting(self):
        g = self.guest
        actual_replace = g.os.replace
        failed = False

        def replace(source, target):
            nonlocal failed
            if (
                not failed
                and pathlib.Path(source).parent.name == "new"
                and pathlib.Path(source).name == "gateway-ssh"
            ):
                failed = True
                raise OSError("injected swap failure")
            return actual_replace(source, target)

        def extract(*args):
            subprocess.run(args, check=True, capture_output=True)

        with (
            patch.object(g, "cmd", side_effect=extract),
            patch.object(g, "stop_writers", return_value=["gateway"]),
            patch.object(g, "restart") as restart,
            patch.object(g.os, "replace", side_effect=replace),
        ):
            with self.assertRaises(OSError):
                g.restore(g.state_manifest())
            restart.assert_called_once_with(["gateway"])
        for tree in g.TREES:
            self.assertEqual((self.home / tree / "marker").read_text(), "original")

    def test_archive_traversal_refused(self):
        import tarfile

        with tarfile.open(self.archive, "w") as tar:
            tar.addfile(tarfile.TarInfo("gateway-state/../../outside"))
        with self.assertRaises(self.guest.deploy.DeployError):
            self.guest.validate_archive(self.archive)


if __name__ == "__main__":
    unittest.main()
