"""Offline configuration and boot-observation boundaries; no host or TPM changes."""

import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/hermes/unattended"))
from common import Failure  # noqa: E402
import tpm_profile as m  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))  # noqa: E402
from integration_gate import integration_only  # noqa: E402


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_render_idempotent_and_unrelated_configuration_preserved(self):
        other = self.root / "etc/dracut.conf.d/98-existing.conf"
        other.parent.mkdir(parents=True)
        other.write_text("hostonly=yes\n")
        self.assertEqual(m.render(self.root)["profile"], "standard-tpm2")
        before = {p: (p.lstat().st_ino, p.lstat().st_mtime_ns) for p in self.root.rglob("*")}
        m.render(self.root)
        self.assertEqual(before, {p: (p.lstat().st_ino, p.lstat().st_mtime_ns) for p in self.root.rglob("*")})
        self.assertEqual(other.read_text(), "hostonly=yes\n")
        self.assertFalse((self.root / "etc/systemd/system/systemd-tpm2-setup.service").exists())

    def test_refuses_live_root(self):
        for root in ("/", "/tmp/..", "/proc/self/root"):
            with self.subTest(root=root), self.assertRaisesRegex(Failure, "offline-staging-root"):
                m.render(root)

    def test_partial_render_resumes_without_replacing_masks(self):
        path = self.root / m.MASKS[0]
        path.parent.mkdir(parents=True)
        path.symlink_to("/dev/null")
        inode = path.lstat().st_ino
        m.render(self.root)
        self.assertEqual(path.lstat().st_ino, inode)

    def test_late_conflict_stops_before_earlier_writes(self):
        path = self.root / m.DRACUT_PATH
        path.parent.mkdir(parents=True)
        path.write_text("operator-configuration\n")
        with self.assertRaisesRegex(Failure, "existing-profile-conflict"):
            m.render(self.root)
        self.assertFalse(os.path.lexists(self.root / m.MASKS[0]))
        self.assertEqual(path.read_text(), "operator-configuration\n")

    def test_symlinked_parent_refused(self):
        (self.root / "etc").symlink_to(self.root)
        with self.assertRaisesRegex(Failure, "symlinked-profile-parent"):
            m.render(self.root)

    def test_partial_profile_is_not_a_service_exemption(self):
        p = self.root / m.MASKS[0]
        p.parent.mkdir(parents=True)
        p.symlink_to("/dev/null")
        with self.assertRaisesRegex(Failure, "partial-standard-tpm2-profile"):
            m.services(lambda args: b"active", self.root)

    def service_fixture(self, *, early_skip=False, exit_status="0", product="masked"):
        for directory in ("run/systemd", "var/lib/systemd"):
            for suffix in ("pem", "tpm2b_public"):
                p = self.root / directory / ("tpm2-srk-public-key." + suffix)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"srk-public-fixture")
        def run(args):
            if "systemd-pcrproduct.service" in args:
                return product.encode()
            early = "systemd-tpm2-setup-early.service" in args
            return ("LoadState=loaded\nActiveState=" + ("inactive" if early and early_skip else "active")
                    + "\nSubState=" + ("dead" if early and early_skip else "exited")
                    + "\nExecMainStatus=" + exit_status
                    + "\nConditionResult=" + ("no" if early and early_skip else "yes")).encode()
        return run

    def test_standard_profile_keeps_successful_setup_and_srk_continuity(self):
        m.render(self.root)
        result = m.services(self.service_fixture(), self.root)
        self.assertEqual(result["profile"], "standard-tpm2")
        self.assertTrue(result["srk_public_files_match"])

    def test_early_initrd_completion_accepted_with_public_srk_continuity(self):
        m.render(self.root)
        result = m.services(self.service_fixture(early_skip=True), self.root)
        self.assertEqual(result["srk_services"]["systemd-tpm2-setup-early.service"], "skipped-existing-srk")

    def test_success_exit_76_is_not_tpm_acceptance(self):
        m.render(self.root)
        with self.assertRaisesRegex(Failure, "failed-tpm-service"):
            m.services(self.service_fixture(exit_status="76"), self.root)

    def test_product_must_be_masked_for_standard_profile(self):
        m.render(self.root)
        with self.assertRaisesRegex(Failure, "unmasked-nvpcr-consumer"):
            m.services(self.service_fixture(product="loaded"), self.root)

    def test_vendor_profile_still_requires_product_service(self):
        self.assertEqual(m.services(self.service_fixture(product="active"), self.root)["profile"], "vendor-nvpcr")
        with self.assertRaisesRegex(Failure, "failed-tpm-service"):
            m.services(self.service_fixture(product="inactive"), self.root)

    def test_mismatched_srk_blocks_early_skip(self):
        m.render(self.root)
        run = self.service_fixture(early_skip=True)
        (self.root / "var/lib/systemd/tpm2-srk-public-key.pem").write_bytes(b"different-srk")
        with self.assertRaisesRegex(Failure, "srk-public-files-mismatch"):
            m.services(run, self.root)

    def test_new_vendor_definition_requires_review(self):
        m.render(self.root)
        path = self.root / "usr/lib/nvpcr/new-consumer.nvpcr"
        path.parent.mkdir(parents=True)
        path.write_text('{}')
        with self.assertRaisesRegex(Failure, "unreviewed-nvpcr-definition"):
            m.profile(self.root)

    def test_masked_setup_is_rejected(self):
        m.render(self.root)
        run = self.service_fixture()
        with self.assertRaisesRegex(Failure, "failed-tpm-service"):
            m.services(lambda args: run(args).replace(b"LoadState=loaded", b"LoadState=masked"), self.root)


class InitrdProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.image = Path(self.temp.name) / 'initrd'
        self.image.write_bytes(b'disposable-archive-fixture')
        self.listing = '\n'.join('lrwxrwxrwx 1 root root 9 Sep 10 12:00 ' + name + ' -> /dev/null'
                                 for name in m.MASKS)
        self.modules = 'crypt\n tpm2-tss \nsystemd-pcrphase\n'

    def run_tool(self, args):
        self.assertEqual(args[0], 'lsinitrd')
        self.assertEqual(args[-1], str(self.image))
        return (self.modules if '-m' in args else self.listing).encode()

    def test_accepts_archive_masks_and_modules_without_claiming_boot(self):
        result = m.inspect_initrd(self.image, self.run_tool)
        self.assertEqual(result['profile'], 'standard-tpm2')
        self.assertFalse(result['boot_verified'])

    def test_absent_regular_wrong_target_and_duplicate_masks_rejected(self):
        original = self.listing
        for changed in ('\n'.join(original.splitlines()[1:]), original.replace('lrwx', '-rwx', 1),
                        original.replace('/dev/null', '/tmp/other', 1), original + '\n' + original.splitlines()[0]):
            with self.subTest(changed=changed), self.assertRaisesRegex(Failure, 'standard-mask-missing'):
                self.listing = changed
                m.inspect_initrd(self.image, self.run_tool)

    def test_unknown_vendor_definition_rejected_even_with_standard_masks(self):
        self.listing += '\n-rw-r--r-- 1 root root 100 Sep 10 12:00 usr/lib/nvpcr/custom.nvpcr'
        with self.assertRaisesRegex(Failure, 'unreviewed-nvpcr-definition'):
            m.inspect_initrd(self.image, self.run_tool)

    def test_missing_pcr11_support_rejected(self):
        self.modules = 'crypt\ntpm2-tss\n'
        with self.assertRaisesRegex(Failure, 'tpm-modules-missing'):
            m.inspect_initrd(self.image, self.run_tool)

    def test_changing_archive_rejected(self):
        def command(args):
            result = self.run_tool(args)
            if '-m' in args:
                self.image.write_bytes(b'changed-during-inspection')
            return result
        with self.assertRaisesRegex(Failure, 'changed-during-review'):
            m.inspect_initrd(self.image, command)

    def relative_listing(self):
        directories = ['etc', 'etc/nvpcr', 'etc/systemd', 'etc/systemd/system', 'dev']
        return '\n'.join('drwxr-xr-x 1 root root 0 Sep 10 12:00 ' + name for name in directories) + '\n' + '\n'.join(
            'lrwxrwxrwx 1 root root 14 Sep 10 12:00 ' + name + ' -> ' +
            ('../../dev/null' if name.endswith('.nvpcr') else '../../../dev/null') for name in m.MASKS)

    def test_relative_null_requires_exact_target_and_unambiguous_directories(self):
        self.listing = original = self.relative_listing()
        self.assertTrue(m.inspect_initrd(self.image, self.run_tool)['passed'])
        for changed in (original.replace('../../dev/null', '../../../dev/null', 1),
                        original.replace('../../dev/null', '../../dev/./null', 1),
                        original.replace('drwxr-xr-x 1 root root 0 Sep 10 12:00 etc/nvpcr',
                                         'lrwxrwxrwx 1 root root 0 Sep 10 12:00 etc/nvpcr -> elsewhere'),
                        original.replace('drwxr-xr-x 1 root root 0 Sep 10 12:00 dev', ''),
                        original + '\ndrwxr-xr-x 1 root root 0 Sep 10 12:00 etc/nvpcr'):
            with self.subTest(changed=changed), self.assertRaisesRegex(Failure, 'standard-mask-missing'):
                self.listing = changed
                m.inspect_initrd(self.image, self.run_tool)

    def test_failed_inspection_retains_only_sanitized_verdicts(self):
        self.listing = self.relative_listing().replace('../../dev/null', '/private-target-canary', 1)
        self.listing += '\n-rw-r--r-- 1 root root 0 Sep 10 12:00 usr/lib/nvpcr/private-name-canary.nvpcr'
        observed = []
        with self.assertRaisesRegex(Failure, 'standard-mask-missing'):
            m.inspect_initrd(self.image, self.run_tool, observed.append)
        self.assertEqual(len(observed), 1)
        self.assertFalse(observed[0]['passed'])
        self.assertFalse(observed[0]['boot_verified'])
        self.assertEqual(observed[0]['unknown_definition_count'], 1)
        self.assertFalse(observed[0]['mask_checks'][m.MASKS[0]]['accepted'])
        self.assertNotIn('canary', json.dumps(observed))

    def test_installer_applies_real_renderer_to_offline_root_and_preserves_conflicts(self):
        repository = Path(__file__).resolve().parents[1]
        kickstart = (repository / 'vm/kickstart/hermes-tpm-enroll.ks').read_text()
        self.assertLess(kickstart.index("<<'TPMPROFILE'"), kickstart.index('dracut --regenerate-all'))
        source = kickstart.split("<<'TPMPROFILE'\n", 1)[1].split('\nTPMPROFILE', 1)[0]
        root = Path(self.temp.name) / 'target'
        root.mkdir()
        # Substitute only the isolated installer paths; run the actual embedded program.
        source = source.replace("'/run/hermes-profile-oem'", repr(str(repository / 'scripts/hermes/unattended')))
        source = source.replace("'/mnt/sysroot'", repr(str(root)))
        exec(compile(source, 'installer-offline-profile', 'exec'), {})
        self.assertEqual(m.profile(root), 'standard-tpm2')
        config = root / m.DRACUT_PATH
        config.write_text('existing-configuration-canary')
        with self.assertRaisesRegex(Failure, 'existing-profile-conflict'):
            exec(compile(source, 'installer-offline-profile', 'exec'), {})
        self.assertEqual(config.read_text(), 'existing-configuration-canary')


class PackagedDracutIntegrationTests(unittest.TestCase):
    """Real packaged dracut-install/cpio/lsinitrd archive readback; opt-in only.

    Kept out of tests/offline_allowlist.txt: an installed dracut package must not
    pull real archive construction into the pre-push gate.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.image = Path(self.temp.name) / 'initrd'
        self.image.write_bytes(b'disposable-archive-fixture')

    @integration_only("real packaged dracut-install/cpio/lsinitrd readback")
    @unittest.skipUnless(Path('/usr/lib/dracut/dracut-install').is_file() and shutil.which('cpio')
                         and shutil.which('lsinitrd'),
                         'requires packaged dracut-install, cpio and lsinitrd')
    def test_packaged_dracut_relative_masks_survive_actual_archive_readback(self):
        source, destination = (Path(self.temp.name) / name for name in ('source', 'destination'))
        source.mkdir(); destination.mkdir()
        m.render(source)
        (source / 'dev').mkdir()
        # No privileged device creation or host configuration input is needed to
        # reproduce dracut's link conversion; use an empty isolated target file.
        (source / 'dev/null').write_bytes(b'')
        subprocess.run(['/usr/lib/dracut/dracut-install', '-r', str(source), '-D', str(destination),
                        '-a', *['/' + name for name in m.MASKS]], check=True, capture_output=True)
        for name in m.MASKS:
            self.assertNotEqual(os.readlink(destination / name), '/dev/null')
        modules = destination / 'usr/lib/dracut/modules.txt'
        modules.parent.mkdir(parents=True)
        modules.write_text('crypt\ntpm2-tss\nsystemd-pcrphase\n')
        names = ['.'] + sorted(str(p.relative_to(destination)) for p in destination.rglob('*'))
        archive = subprocess.run(['cpio', '--null', '-o', '-H', 'newc'], cwd=destination,
                                 input=('\0'.join(names) + '\0').encode(), capture_output=True, check=True)
        self.image.write_bytes(gzip.compress(archive.stdout))
        result = m.inspect_initrd(self.image, lambda args: subprocess.check_output(args, stderr=subprocess.PIPE))
        self.assertTrue(result['passed'])
        self.assertTrue(all(c['target_kind'] == 'relative-null' and c['directory_chain_verified']
                            for c in result['mask_checks'].values()))
        self.assertFalse(result['boot_verified'])


if __name__ == "__main__":
    unittest.main()
