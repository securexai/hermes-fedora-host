"""Lifecycle fault/isolation tests. These do not provision VMs or issue credentials."""

from datetime import datetime, timedelta
import io
import os
from pathlib import Path
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/hermes/unattended'))
import lifecycle
import lifecycle_fixture as fixture
import lifecycle_guest as guest
from common import Failure, canonical, decode, lock, protected_file


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy = {'state_dir': str(self.root), 'schema': 'hermes-lifecycle-v1'}
        self.now = datetime(2026, 9, 13, 2, 0, tzinfo=ZoneInfo('America/Bogota'))
        self.driver = Mock()
        self.factory = Mock(return_value=self.driver)
        self.patch('protected_file', side_effect=lambda p, *a: protected_file(p))
        self.patch('owned_path', side_effect=lambda p, *a, **k: Path(p))
        self.window = self.patch('maintenance_open', return_value=True)

    def patch(self, name, **kwargs):
        p = patch('lifecycle.' + name, **kwargs); self.addCleanup(p.stop); return p.start()

    def execute(self, **kwargs):
        return lifecycle.execute(self.policy, self.factory, now=self.now, **kwargs)

    def state(self):
        active = decode((self.root / 'active.json').read_bytes())
        return decode((self.root / active['run_id'] / 'lifecycle.json').read_bytes())

    def grant(self, run='a', **changes):
        import time
        value = {'schema': 'hermes-lifecycle-lab-window-v1', 'binding': lifecycle.identity(self.policy),
                 'run_id': run * 64, 'issued_at': int(time.time()) - 1, 'expires_at': int(time.time()) + 3600}
        value.update(changes)
        path = self.root / ('grant-' + run + '.json')
        path.write_bytes(canonical(value))
        return str(path)

    def test_bound_grant_allows_off_window_and_second_fresh_run(self):
        self.window.return_value = False
        first = self.execute(grant_path=self.grant())['run_id']
        before = (self.root / first / 'lifecycle.json').read_bytes()
        second = self.execute(grant_path=self.grant('b'))['run_id']
        self.assertNotEqual(first, second)
        self.assertEqual((self.root / first / 'lifecycle.json').read_bytes(), before)
        self.assertEqual(self.driver.certify.call_count, 2)
        with self.assertRaisesRegex(Failure, 'already-consumed'):
            self.execute(grant_path=self.grant())

    def test_grant_rerun_is_idempotent(self):
        grant = self.grant()
        self.execute(grant_path=grant)
        self.assertEqual(self.execute(grant_path=grant)['stage'], 'slot-already-finished')
        self.driver.prepare.assert_called_once()

    def test_bad_grants_do_not_allocate_fixture(self):
        import time
        for changes in ({'binding': 'b' * 64}, {'run_id': '../unsafe'}, {'expires_at': int(time.time()) - 2},
                        {'expires_at': int(time.time()) + 14401}, {'issued_at': True}, {'schema': 'other'}):
            with self.subTest(changes=changes), self.assertRaises(Failure):
                self.execute(grant_path=self.grant(**changes))
        self.factory.assert_not_called()

    def test_expiry_during_preparation_cleans_without_certifying(self):
        grant = self.grant()
        def expire():
            value = decode(Path(grant).read_bytes()); value['expires_at'] = value['issued_at']
            Path(grant).write_bytes(canonical(value))
        self.driver.prepare.side_effect = expire
        with self.assertRaisesRegex(Failure, 'failed-and-cleaned'):
            self.execute(grant_path=grant)
        self.driver.certify.assert_not_called()
        self.driver.cleanup.assert_called_once()

    def test_expired_grant_does_not_block_recovery(self):
        grant = self.grant()
        self.driver.prepare.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): self.execute(grant_path=grant)
        Path(grant).unlink()
        with self.assertRaisesRegex(Failure, 'failed-and-cleaned'):
            self.execute(cleanup_only=True, grant_path=grant)
        self.driver.cleanup.assert_called_once()

    def test_failure_context_never_includes_exception_message(self):
        self.driver.prepare.side_effect = ValueError('private-test-credential-canary')
        with self.assertRaises(Failure): self.execute()
        self.assertEqual(self.state()['failure_context']['type'], 'ValueError')
        self.assertNotIn('private-test-credential-canary', str(self.state()))
        self.assertTrue(self.state()['failure_context']['locations'])

    def test_success_orders_prepare_certify_cleanup(self):
        result = self.execute()
        self.assertEqual(result['stage'], 'complete')
        self.assertFalse(result['release_signed'])
        self.assertEqual([c[0] for c in self.driver.method_calls], ['prepare', 'certify', 'cleanup'])
        self.assertTrue(self.state()['certified'])

    def test_installed_images_are_inspected_before_signing(self):
        driver = fixture.Fixture.__new__(fixture.Fixture)
        driver.private = self.root
        calls = Mock()
        with patch.object(fixture.tpm_profile, 'inspect_initrd', calls.inspect), \
                patch.object(fixture.boot_build, 'toolchain', return_value=(None, self.root)), \
                patch.object(fixture.boot_build, 'build', calls.sign):
            calls.inspect.return_value = {'profile': 'standard-tpm2', 'boot_verified': False}
            calls.sign.return_value = {'ok': True}
            result = driver.build(self.root, self.root / 'installed.efi')
            self.assertEqual([call[0] for call in calls.mock_calls], ['inspect', 'sign'])
            self.assertEqual(result['initrd_profile']['profile'], 'standard-tpm2')
            calls.reset_mock()
            calls.inspect.side_effect = Failure(78, 'initrd-standard-mask-missing')
            with self.assertRaisesRegex(Failure, 'standard-mask-missing'):
                driver.build(self.root, self.root / 'updated.efi')
            calls.sign.assert_not_called()

    def test_failed_archive_observation_is_saved_before_cleanup_without_signing(self):
        driver = fixture.Fixture.__new__(fixture.Fixture)
        driver.private = self.root
        driver.save = Mock()
        (self.root / 'initrd').write_bytes(b'isolated-broken-archive')
        def command(args):
            return b'crypt\ntpm2-tss\nsystemd-pcrphase\n' if '-m' in args else b''
        with patch.object(fixture, 'run', side_effect=command), patch.object(fixture.boot_build, 'build') as sign:
            with self.assertRaisesRegex(Failure, 'standard-mask-missing'):
                driver.build(self.root, self.root / 'installed.efi')
        sign.assert_not_called()
        driver.save.assert_called_once()
        saved = driver.save.call_args.kwargs['last_initrd_review']
        self.assertFalse(saved['passed'])
        self.assertTrue(saved['required_modules_present'])
        self.assertEqual(saved['mask_checks'][fixture.tpm_profile.MASKS[0]]['entries'], 0)

    def test_off_window_no_state_or_driver(self):
        self.window.return_value = False
        self.assertEqual(self.execute()['stage'], 'deferred')
        self.factory.assert_not_called()
        self.assertFalse((self.root / 'active.json').exists())

    def test_window_closed_after_preparation_cleans_without_certifying(self):
        self.window.side_effect = [True, False]
        self.assertEqual(self.execute()['stage'], 'deferred-cleaned')
        self.driver.certify.assert_not_called(); self.driver.cleanup.assert_called_once()
        self.assertFalse(self.state()['certified'])

    def test_run_directory_traversable_under_private_service_umask(self):
        old = os.umask(0o077)
        try: run_id = self.execute()['run_id']
        finally: os.umask(old)
        self.assertEqual((self.root / run_id).stat().st_mode & 0o777, 0o711)

    def test_completed_slot_is_idempotent(self):
        self.execute(); original = self.state()
        self.assertEqual(self.execute()['stage'], 'slot-already-finished')
        self.assertEqual(self.state(), original)
        self.driver.prepare.assert_called_once()

    def test_next_week_uses_new_run_retaining_previous_history(self):
        first = self.execute()['run_id']
        old = (self.root / first / 'lifecycle.json').read_bytes()
        self.now += timedelta(days=7)
        second = self.execute()['run_id']
        self.assertNotEqual(first, second)
        self.assertEqual((self.root / first / 'lifecycle.json').read_bytes(), old)
        self.assertEqual(self.driver.prepare.call_count, 2)

    def test_prepare_failure_cleans_without_certification(self):
        self.driver.prepare.side_effect = Failure(69, 'private-canary-must-not-leak')
        with self.assertRaisesRegex(Failure, 'lifecycle-failed-and-cleaned'): self.execute()
        self.driver.certify.assert_not_called(); self.driver.cleanup.assert_called_once()
        self.assertEqual(self.state()['stage'], 'failed-cleaned')
        self.assertNotIn('private-canary', str(self.state()))

    def test_failed_slot_does_not_reissue(self):
        self.driver.certify.side_effect = Failure(69, 'issuance-uncertain')
        with self.assertRaises(Failure): self.execute()
        self.assertEqual(self.execute()['stage'], 'slot-already-finished')
        self.driver.certify.assert_called_once()

    def test_cleanup_failure_retains_primary_error(self):
        self.driver.certify.side_effect = Failure(69, 'bad-certification')
        self.driver.cleanup.side_effect = Failure(69, 'cleanup-broke')
        with self.assertRaisesRegex(Failure, 'lifecycle-cleanup-failed'): self.execute()
        state = self.state()
        self.assertEqual(state['failure'], 'lifecycle-execution-failed')
        self.assertEqual(state['cleanup_failure'], 'lifecycle-cleanup-failed')
        self.assertEqual(state['stage'], 'cleanup-failed')

    def test_no_new_run_after_unfinished_cleanup(self):
        self.driver.cleanup.side_effect = Failure(69, 'failure')
        with self.assertRaises(Failure): self.execute()
        self.now += timedelta(days=7)
        with self.assertRaisesRegex(Failure, 'interrupted-lifecycle-needs-cleanup'): self.execute()
        self.driver.prepare.assert_called_once()

    def test_cleanup_recovery_outside_window_never_recertifies(self):
        self.driver.prepare.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): self.execute()
        self.window.return_value = False
        with self.assertRaisesRegex(Failure, 'lifecycle-failed-and-cleaned'): self.execute(cleanup_only=True)
        self.driver.prepare.assert_called_once(); self.driver.certify.assert_not_called()
        self.assertEqual(self.state()['stage'], 'failed-cleaned')

    def test_retry_failed_cleanup_preserves_acceptance_without_claiming_complete(self):
        self.driver.cleanup.side_effect = Failure(69, 'failure')
        with self.assertRaises(Failure): self.execute()
        self.assertTrue(self.state()['certified'])
        self.driver.cleanup.side_effect = None
        with self.assertRaises(Failure): self.execute(cleanup_only=True)
        self.assertEqual(self.state()['stage'], 'failed-cleaned')
        self.driver.certify.assert_called_once()

    def test_completed_cleanup_does_not_touch_artifacts(self):
        self.execute(); self.driver.reset_mock(); before = self.state()
        self.assertEqual(self.execute(cleanup_only=True)['stage'], 'nothing-to-clean')
        self.assertEqual(before, self.state()); self.driver.cleanup.assert_not_called()

    def test_empty_cleanup_does_not_allocate_run(self):
        self.assertEqual(self.execute(cleanup_only=True)['stage'], 'nothing-to-clean')
        self.factory.assert_not_called(); self.assertFalse((self.root / 'active.json').exists())

    def test_policy_change_blocks_recovery(self):
        self.driver.prepare.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): self.execute()
        self.policy['model'] = 'changed'
        with self.assertRaisesRegex(Failure, 'lifecycle-policy-changed'): self.execute(cleanup_only=True)
        self.driver.cleanup.assert_not_called()

    def test_active_run_path_traversal_rejected(self):
        (self.root / 'active.json').write_bytes(canonical({'run_id': '../other'}))
        with self.assertRaisesRegex(Failure, 'invalid-active-lifecycle'): self.execute()
        self.factory.assert_not_called()

    def test_symlink_journal_rejected(self):
        target = self.root / 'target'; target.write_bytes(b'{}')
        (self.root / 'active.json').symlink_to(target)
        with self.assertRaises(Failure): self.execute()
        self.factory.assert_not_called()

    def test_concurrent_lifecycle_rejected(self):
        with lock(self.root / '.lifecycle.lock'):
            with self.assertRaisesRegex(Failure, 'target-busy'): self.execute()
        self.driver.prepare.assert_not_called()


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def archive(self, members):
        result = io.BytesIO()
        with tarfile.open(fileobj=result, mode='w', format=tarfile.USTAR_FORMAT) as archive:
            for name, kind in members:
                info = tarfile.TarInfo(name); info.type = kind
                if kind == tarfile.REGTYPE:
                    info.size = 3; archive.addfile(info, io.BytesIO(b'abc'))
                else:
                    info.linkname = '/etc/shadow'; archive.addfile(info)
        result.seek(0); return result

    def test_public_files_roundtrip(self):
        fixture.unpack_public(self.archive([('transaction/transaction.json', tarfile.REGTYPE),
                                            ('export/linux', tarfile.REGTYPE)]), self.root)
        self.assertEqual((self.root / 'export/linux').read_bytes(), b'abc')

    def test_real_gnu_tar_accepts_supported_rpm_caret_version(self):
        import subprocess
        source = self.root / 'source'; source.mkdir()
        package = source / 'transaction/packages/passt-0^20260728.gf8df3f1-2.fc44.x86_64.rpm'
        package.parent.mkdir(parents=True); package.write_bytes(b'public RPM fixture')
        (source / 'export').mkdir(); (source / 'export/linux').write_bytes(b'public kernel fixture')
        raw = subprocess.check_output(['tar', '--format=ustar', '-C', str(source), '-cf', '-', 'transaction', 'export'])
        destination = self.root / 'received'; destination.mkdir()
        fixture.unpack_public(io.BytesIO(raw), destination)
        self.assertEqual((destination / package.relative_to(source)).read_bytes(), package.read_bytes())

    def test_traversal_absolute_and_unexpected_roots_rejected(self):
        for name in ('../escape', '/export/linux', 'export/../../escape', 'private/key', 'export//linux'):
            with self.subTest(name=name), self.assertRaises(Failure):
                fixture.unpack_public(self.archive([(name, tarfile.REGTYPE)]), self.root)

    def test_links_and_devices_rejected(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.FIFOTYPE):
            with self.subTest(kind=kind), self.assertRaises(Failure):
                fixture.unpack_public(self.archive([('export/key', kind)]), self.root)

    def test_duplicate_members_rejected(self):
        with self.assertRaisesRegex(Failure, 'unsafe-public-archive'):
            fixture.unpack_public(self.archive([('export/linux', tarfile.REGTYPE)] * 2), self.root)

    def test_existing_symlink_never_followed(self):
        outside = self.root / 'outside'; outside.mkdir()
        (self.root / 'export').symlink_to(outside)
        # Production destination is newly created; still reject a changed receiver tree.
        with self.assertRaises((Failure, OSError)):
            fixture.unpack_public(self.archive([('export/linux', tarfile.REGTYPE)]), self.root)
        self.assertFalse((outside / 'linux').exists())


class DomainTests(unittest.TestCase):
    def xml(self, **changes):
        values = {'uuid': fixture.UUID, 'disk': str(fixture.DISK), 'loader': str(fixture.POOL / 'code.fd'),
                  'nvram': str(fixture.NVRAM), 'extra': '', 'secure': 'yes'}
        values.update(changes)
        return '''<domain><name>lab-hermes-server</name><uuid>{uuid}</uuid><os>
<loader secure="{secure}" readonly="yes">{loader}</loader><nvram>{nvram}</nvram></os><devices>
<disk type="file" device="disk"><source file="{disk}"/></disk>
<tpm><backend type="emulator" version="2.0"/></tpm>{extra}</devices></domain>'''.format(**values).encode()

    def test_exact_fixture_accepted(self):
        fixture.validate_xml(self.xml(), '/media/fedora.iso')

    def test_other_uuid_disk_firmware_or_nvram_rejected(self):
        for key in ('uuid', 'disk', 'loader', 'nvram', 'secure'):
            with self.subTest(key=key), self.assertRaises(Failure):
                fixture.validate_xml(self.xml(**{key: 'wrong'}), '/media/fedora.iso')

    def test_shared_filesystem_and_host_device_rejected(self):
        for extra in ('<filesystem/>', '<hostdev/>'):
            with self.subTest(extra=extra), self.assertRaises(Failure):
                fixture.validate_xml(self.xml(extra=extra), '/media/fedora.iso')

    def test_extra_disk_rejected_even_during_partial_cleanup(self):
        extra = '<disk type="file"><source file="/production/disk.qcow2"/></disk>'
        with self.assertRaises(Failure): fixture.validate_xml(self.xml(extra=extra), '/media/fedora.iso', True)

    def test_installer_media_only_allowed_for_partial_cleanup(self):
        extra = '<disk type="file"><source file="/media/fedora.iso"/></disk>'
        fixture.validate_xml(self.xml(extra=extra), '/media/fedora.iso', True)
        with self.assertRaises(Failure): fixture.validate_xml(self.xml(extra=extra), '/media/fedora.iso')


class GuestBoundaryTests(unittest.TestCase):
    def test_request_cannot_change_run_or_add_fields(self):
        binding = {'run_id': 'a' * 64}
        for message in ({'run_id': 'b' * 64}, {'run_id': 'a' * 64, 'command': 'arbitrary'}):
            with self.assertRaises(Failure): guest.check_request('purge', message, binding)

    def test_guest_production_domain_rejected(self):
        with patch.object(guest.os, 'geteuid', return_value=1000):
            with self.assertRaisesRegex(Failure, 'not-disposable-lifecycle-guest'): guest.guard()

    def test_enrollment_rejects_wrong_candidate_and_unsafe_key_before_writes(self):
        host = {'machine_id_sha256': 'a' * 64, 'ssh_fingerprint': 'SHA256:' + 'a' * 43}
        binding = {'run_id': 'a' * 64, 'host': host}
        policy = {'schema': 'hermes-lab-certifier-v1', 'domain_uuid': guest.UUID, 'host': host,
                  'candidate_sha256': 'b' * 64, 'run_id': binding['run_id'], 'kernel': 'test-kernel'}
        for change in ({'domain_uuid': 'production'}, {'host': {}}, {'run_id': 'b' * 64},
                       {'candidate_sha256': '../escape'}, {'kernel': 'bad;command'}):
            with self.subTest(change=change), self.assertRaises(Failure):
                guest.enroll({'policy': {**policy, **change}, 'public_key': 'ssh-ed25519 AAA'}, binding)
        with self.assertRaisesRegex(Failure, 'invalid-certifier-public-key'):
            guest.enroll({'policy': policy, 'public_key': 'ssh-ed25519 AAA\ncommand="anything"'}, binding)

    def test_partial_bootstrap_missing_unit_is_safe_to_clean(self):
        with patch.object(guest.subprocess, 'run', return_value=SimpleNamespace(returncode=1, stdout=b'not-found')):
            with patch.object(guest, 'run') as command:
                guest.stop_unit_if_present('hermes-runtime-credentials.service')
                command.assert_not_called()

    def test_unit_query_failure_cannot_be_treated_as_absence(self):
        with patch.object(guest.subprocess, 'run', return_value=SimpleNamespace(returncode=1, stdout=b'')):
            with self.assertRaises(Failure): guest.stop_unit_if_present('hermes-runtime-credentials.service')


class FixtureCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = {'run_id': 'a' * 64, 'binding': 'b' * 64}
        account = SimpleNamespace(pw_name='hermes-certification', pw_uid=os.getuid(), pw_gid=os.getgid())
        with patch.object(fixture.pwd, 'getpwnam', return_value=account):
            self.driver = fixture.Fixture({'repository': str(self.root), 'certifier_user': account.pw_name},
                                          self.root, self.state, lambda **values: self.state.update(values))
        self.driver.private.mkdir(mode=0o700)
        self.driver.work.mkdir(mode=0o700)

    def test_tool_readiness_runs_under_certifier_identity_with_empty_environment(self):
        import schedule
        result = {'ok': True, 'stage': 'certifier-tools-ready', 'tools': list(schedule.CERTIFIER_TOOLS)}
        with patch.object(fixture, 'run', return_value=canonical(result)) as command:
            self.driver.check_certifier_tools()
        args = command.call_args.args[0]
        self.assertEqual(args[:5], ['runuser', '-u', 'hermes-certification', '--', 'env'])
        self.assertEqual(args[5], '-i')
        self.assertFalse(any(a.startswith('PATH=') for a in args))
        self.assertIn('tool_readiness()', args[args.index('-c') + 1])
        self.assertTrue(self.state['certifier_tools_ready'])

    def test_missing_tools_stop_before_broker_keys_or_vm_allocation(self):
        self.driver.private.rmdir(); self.driver.work.rmdir()
        self.driver.source_identity = Mock(return_value='c' * 64)
        self.driver.virsh = Mock(return_value=b'')
        self.driver.check_certifier_tools = Mock(side_effect=Failure(69, 'missing-certifier-tool-restic'))
        self.driver.check_broker = Mock(); self.driver.inputs = Mock()
        with patch.object(fixture, 'POOL', self.root / 'pool'), \
                patch.object(fixture, 'NVRAM', self.root / 'vars'), \
                patch.object(fixture, 'TPM', self.root / 'tpm'), \
                patch.object(fixture.shutil, 'disk_usage', return_value=SimpleNamespace(free=61 * 1024**3)), \
                patch.object(fixture.os, 'cpu_count', return_value=2), \
                patch.object(Path, 'read_text', return_value='MemAvailable: 20000000 kB\n'):
            with self.assertRaisesRegex(Failure, 'missing-certifier-tool-restic'):
                self.driver.prepare()
        self.driver.check_broker.assert_not_called(); self.driver.inputs.assert_not_called()
        self.assertFalse(self.driver.private.exists()); self.assertFalse(self.driver.work.exists())
        self.assertTrue(all(c.args[0] == 'list' for c in self.driver.virsh.call_args_list))

    def test_memory_drop_after_inputs_stops_before_installer(self):
        available = [10 * 1024**2]
        self.driver.preflight = Mock(side_effect=lambda: self.driver.check_resources('preflight'))
        self.driver.inputs = Mock(side_effect=lambda: available.__setitem__(0, 8 * 1024**2))
        with patch.object(fixture.shutil, 'disk_usage', return_value=SimpleNamespace(free=61 * 1024**3)), \
                patch.object(fixture.os, 'cpu_count', return_value=2), \
                patch.object(Path, 'read_text', side_effect=lambda: 'MemAvailable: %d kB\n' % available[0]), \
                patch.object(fixture, 'run') as command:
            with self.assertRaisesRegex(Failure, 'insufficient-lifecycle-resources'):
                self.driver.prepare()
        self.driver.inputs.assert_called_once()
        command.assert_not_called()
        self.assertNotIn('install_started', self.state)
        self.assertEqual(self.state['resource_checks']['preflight']['available_memory_kib'], 10 * 1024**2)
        self.assertEqual(self.state['resource_checks']['before-installer']['available_memory_kib'], 8 * 1024**2)
        self.assertEqual(self.state['resource_checks']['before-installer']['minimum_memory_kib'], 9 * 1024**2)

    def test_unexpected_tool_readiness_response_rejected(self):
        with patch.object(fixture, 'run', return_value=canonical({'ok': True, 'tools': []})):
            with self.assertRaisesRegex(Failure, 'certifier-tools-not-ready'):
                self.driver.check_certifier_tools()
        self.assertNotIn('certifier_tools_ready', self.state)

    def test_broker_readiness_uses_certifier_identity_and_readonly_check(self):
        with patch.object(fixture, 'run', return_value=canonical({'ok': True, 'role': 'test'})) as command:
            self.driver.check_broker()
            args = command.call_args.args[0]
            self.assertEqual(args[:3], ['runuser', '-u', 'hermes-certification'])
            script = args[args.index('-c') + 1]
            self.assertIn("'check', 'test'", script)
            self.assertNotIn("'issue'", script)

    def test_other_broker_role_rejected(self):
        with patch.object(fixture, 'run', return_value=canonical({'ok': True, 'role': 'production'})):
            with self.assertRaisesRegex(Failure, 'isolated-test-broker-unavailable'): self.driver.check_broker()

    def test_revocation_failure_stops_purge_and_destruction(self):
        self.state.update(scheduler_ready=True, pool_owned=True, guest_ready=True)
        self.driver.as_certifier = Mock(side_effect=Failure(69, 'uncertain-issuance'))
        self.driver.check_owned = Mock()
        (self.driver.private / 'recovery.key').write_bytes(b'synthetic-canary')
        with self.assertRaises(Failure): self.driver.cleanup()
        self.driver.check_owned.assert_not_called()
        self.assertTrue((self.driver.private / 'recovery.key').exists())
        self.assertNotIn('credentials_cleaned', self.state)

    def test_guest_purge_failure_retains_local_keys_and_vm(self):
        self.state.update(pool_owned=True, guest_ready=True, credentials_cleaned=True)
        self.driver.check_owned = Mock(return_value=True)
        self.driver.virsh = Mock(return_value=b'running')
        self.driver.guest = Mock(side_effect=Failure(69, 'guest-unreachable'))
        with self.assertRaises(Failure): self.driver.cleanup()
        self.assertTrue(self.driver.private.exists())
        self.assertNotIn('certifier_secrets_purged', self.state)
        self.assertFalse(any(c.args[0] in ('destroy', 'undefine') for c in self.driver.virsh.call_args_list))

    def test_no_fixture_failure_purges_only_run_private_directory(self):
        sibling = self.root / 'unrelated'; sibling.mkdir(); (sibling / 'keep').write_bytes(b'keep')
        self.driver.cleanup()
        self.assertFalse(self.driver.private.exists())
        self.assertEqual((sibling / 'keep').read_bytes(), b'keep')
        self.assertFalse(decode((self.root / 'cleanup.json').read_bytes())['release_signed'])

    def test_private_symlink_refused(self):
        self.driver.private.rmdir()
        outside = self.root / 'outside'; outside.mkdir(); (outside / 'keep').write_bytes(b'keep')
        self.driver.private.symlink_to(outside)
        with self.assertRaises(Failure): self.driver.cleanup()
        self.assertTrue((outside / 'keep').exists())


class StorageRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pool = self.root / 'pool'; self.pool.mkdir()
        info = self.pool.stat()
        self.state = {'run_id': 'a' * 64, 'binding': 'b' * 64, 'domain_destroyed': True,
                      'pool_identity': [info.st_dev, info.st_ino]}
        self.driver = fixture.Fixture.__new__(fixture.Fixture)
        self.driver.state = self.state
        self.driver.save = lambda **values: self.state.update(values)
        self.driver.check_owned = Mock(return_value=False)
        for name, value in [('POOL', self.pool), ('owned_path', lambda p, *a, **kw: Path(p))]:
            mocker = patch.object(fixture, name, value); mocker.start(); self.addCleanup(mocker.stop)

    def test_success_removes_only_exact_pool_and_records_checkpoint(self):
        (self.pool / 'owner.json').write_bytes(canonical({'run_id': self.state['run_id']}))
        (self.pool / 'disk').write_bytes(b'synthetic')
        self.driver.purge_storage()
        self.assertFalse(self.pool.exists())
        self.assertTrue(self.state['storage_purge_started']); self.assertTrue(self.state['vm_destroyed'])

    def test_recreated_domain_blocks_storage_deletion(self):
        (self.pool / 'owner.json').write_bytes(b'{}')
        self.driver.check_owned.return_value = True
        with self.assertRaisesRegex(Failure, 'domain-reappeared-before-storage-purge'):
            self.driver.purge_storage()
        self.assertTrue((self.pool / 'owner.json').exists())

    def test_interruption_after_last_unlink_recovers(self):
        self.state['storage_purge_started'] = True
        self.driver.purge_storage()
        self.assertFalse(self.pool.exists()); self.assertTrue(self.state['vm_destroyed'])

    def test_interruption_after_rmdir_recovers(self):
        self.pool.rmdir(); self.state['storage_purge_started'] = True
        self.driver.purge_storage()
        self.assertTrue(self.state['vm_destroyed'])

    def test_missing_pool_without_deletion_checkpoint_rejected(self):
        self.pool.rmdir()
        with self.assertRaisesRegex(Failure, 'fixture-pool-disappeared'): self.driver.purge_storage()

    def test_replaced_pool_or_missing_owner_rejected(self):
        self.state['pool_identity'][1] += 1
        with self.assertRaisesRegex(Failure, 'fixture-pool-replaced'): self.driver.purge_storage()
        self.state['pool_identity'][1] -= 1
        with self.assertRaisesRegex(Failure, 'fixture-owner-missing'): self.driver.purge_storage()

    def test_live_domain_cannot_be_skipped(self):
        self.state['domain_destroyed'] = False
        with self.assertRaisesRegex(Failure, 'domain-must-be-destroyed-first'): self.driver.purge_storage()


class PolicyTests(unittest.TestCase):
    def test_nonroot_lifecycle_rejected_before_reading_policy(self):
        with patch.object(lifecycle.os, 'geteuid', return_value=1000):
            with self.assertRaisesRegex(Failure, 'lifecycle-requires-root-enrollment'):
                lifecycle.load('/must-not-be-read')

    def test_example_is_deliberately_unenrolled(self):
        path = Path(__file__).resolve().parents[1] / 'scripts/hermes/unattended/examples/lifecycle.json'
        value = decode(path.read_bytes())
        self.assertEqual(set(value), lifecycle.FIELDS)
        self.assertFalse(lifecycle.sha(value['iso_sha256']))
        self.assertNotIn('production', value['certifier_user'])

    def test_no_unbounded_clock_exception_switch(self):
        source = Path(lifecycle.__file__).read_text()
        self.assertIn("add_argument('--lab-window-grant'", source)
        self.assertNotIn("add_argument('--force'", source)

    def test_service_uses_separate_root_lifecycle_and_existing_certifier_seam(self):
        units = Path(lifecycle.__file__).parent / 'systemd'
        source = (units / 'hermes-lifecycle.service').read_text()
        self.assertIn('User=root', source)
        self.assertIn('--cleanup-only', source)
        self.assertIn('KillMode=control-group', source)
        self.assertIn('Persistent=false', (units / 'hermes-lifecycle.timer').read_text())



class BackupInitializationTests(unittest.TestCase):
    def test_real_repository_initialization_enables_encrypted_roundtrip(self):
        import pwd
        import secrets
        from gates import backup_snapshot
        from common import run
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); backup = root / 'backup'; backup.mkdir()
            password = root / 'password'; password.write_text(secrets.token_hex(32)); password.chmod(0o600)
            source = root / 'source'; source.write_bytes(b'public lifecycle backup fixture')
            driver = fixture.Fixture.__new__(fixture.Fixture)
            driver.account = pwd.getpwuid(os.getuid())
            config = {'backup_repository': str(backup), 'backup_password_file': str(password)}
            with self.assertRaises(Failure): backup_snapshot(source, config, 'lifecycle-test')
            def as_current_test_identity(args, **kwargs):
                self.assertEqual(args[:6], ['runuser', '-u', driver.account.pw_name, '--', 'env', '-i'])
                return run(args[7:], **kwargs)
            with patch.object(fixture, 'run', side_effect=as_current_test_identity):
                driver.initialize_backup(backup, password)
                result = backup_snapshot(source, config, 'lifecycle-test')
                self.assertTrue(result['restore_verified'])
                with self.assertRaises(Failure): driver.initialize_backup(backup, password)
            self.assertTrue((backup / 'config').is_file())


class CopiedMediaTests(unittest.TestCase):
    def test_verified_copy_is_disposable_and_reusable_input_is_unchanged(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); pool = root / 'pool'; pool.mkdir()
            source = root / 'verified.iso'; source.write_bytes(b'verified signed installer')
            before = source.stat()
            driver = fixture.Fixture.__new__(fixture.Fixture)
            driver.policy = {'iso': str(source), 'iso_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
            with patch.object(fixture, 'POOL', pool), patch.object(fixture, 'protected_file', side_effect=lambda p, *a: Path(p)):
                driver.copy_media()
                copied = pool / 'installer.iso'
                self.assertEqual(copied.read_bytes(), source.read_bytes())
                self.assertNotEqual(copied.stat().st_ino, source.stat().st_ino)
                self.assertEqual(source.stat().st_uid, before.st_uid)
                self.assertIn(copied.name, fixture.POOL_NAMES)
                with self.assertRaises(FileExistsError): driver.copy_media()
                copied.unlink(); driver.policy['iso_sha256'] = '0' * 64
                with self.assertRaisesRegex(Failure, 'copied-installer-media-mismatch'): driver.copy_media()


class CandidateWindowTests(unittest.TestCase):
    def test_derived_grant_preserves_exact_candidate_and_expiry(self):
        import time
        import hashlib
        import schedule
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            policy = {'state_dir': str(root)}
            grant = {'schema': 'hermes-lifecycle-lab-window-v1', 'binding': lifecycle.identity(policy),
                     'run_id': 'a' * 64, 'issued_at': int(time.time()) - 1, 'expires_at': int(time.time()) + 100}
            driver = fixture.Fixture.__new__(fixture.Fixture)
            driver.directory, driver.policy = root, policy
            raw = b'candidate'
            driver.state = {'lab_window': grant, 'run_id': grant['run_id'], 'source_sha256': 'source',
                            'candidate_sha256': hashlib.sha256(raw).hexdigest()}
            for name in ('schedule.json', 'certifier.json'):
                (root / name).write_bytes(canonical({'test': name}))
            driver.source_identity = Mock(return_value='source')
            driver.as_certifier = Mock(return_value={'stage': 'ua03-complete', 'release_signed': False})
            driver.read_candidate = Mock(return_value=({}, raw))
            driver.evidence = Mock(return_value={'result': 'PASS'})
            with patch.object(fixture, 'protected_file', side_effect=lambda p, *a: Path(p)):
                driver.certify()
            derived = decode((root / 'candidate-window.json').read_bytes())
            self.assertEqual(derived['expires_at'], grant['expires_at'])
            self.assertEqual(derived['issued_at'], grant['issued_at'])
            self.assertEqual(derived['run_id'], grant['run_id'])
            self.assertEqual(derived['candidate_sha256'], driver.state['candidate_sha256'])
            self.assertEqual(derived['binding'], schedule.binding({'test': 'schedule.json'}, {'test': 'certifier.json'}))
            driver.as_certifier.assert_called_once_with('--lab-window-grant', str(root / 'candidate-window.json'))
            driver.as_certifier.reset_mock()
            driver.state['lab_window']['expires_at'] = int(time.time()) - 1
            with self.assertRaisesRegex(Failure, 'expired-lifecycle-certification-window'):
                driver.certify()
            driver.as_certifier.assert_not_called()


class CandidateApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.driver = fixture.Fixture.__new__(fixture.Fixture)
        self.driver.private = root / 'private'; self.driver.private.mkdir()
        self.driver.directory = root
        self.driver.repository = root / 'repository'
        self.driver.state = {'source_sha256': 'source', 'guest_identity': {'machine_id_sha256': 'a' * 64},
                             'run_id': 'a' * 64, 'baseline': 'b' * 64}
        self.driver.policy = {'model': 'approved-model'}
        self.driver.source_identity = Mock(return_value='source')
        self.approved = {'release_id': 'lifecycle-' + 'a' * 24, 'image': 'approved-image', 'provider': 'openai-api',
                         'model': 'approved-model', 'host': self.driver.state['guest_identity'],
                         'baseline_sha256': 'b' * 64, 'transaction': 'packages/transaction.json',
                         'boot_artifact': 'boot/hermes.efi',
                         'files': {'payload/host.py': {'sha256': 'c' * 64, 'size': 10, 'mode': 384}}}
        def prepare(*args):
            destination = Path(args[1]); destination.mkdir()
            (destination / 'candidate.json').write_bytes(canonical(self.approved))
        for name, value in [('prepare.prepare', prepare), ('validate_candidate', lambda x: x),
                            ('protected_file', lambda p, *a: protected_file(p))]:
            mocker = patch('lifecycle_fixture.' + name, value); mocker.start(); self.addCleanup(mocker.stop)

    def test_exact_root_selected_inputs_accepted(self):
        self.driver.approve_candidate(self.approved)
        self.assertEqual(decode((self.driver.directory / 'approved.json').read_bytes()), self.approved)
        self.assertFalse((self.driver.private / 'approved-candidate').exists())

    def test_certifier_substituted_payload_rejected(self):
        changed = {**self.approved, 'files': {'payload/host.py': {'sha256': 'd' * 64, 'size': 10, 'mode': 384}}}
        with self.assertRaisesRegex(Failure, 'certifier-selected-unapproved-candidate'):
            self.driver.approve_candidate(changed)
        self.assertFalse((self.driver.directory / 'approved.json').exists())

    def test_certifier_cannot_choose_model(self):
        with self.assertRaisesRegex(Failure, 'certifier-selected-unapproved-candidate'):
            self.driver.approve_candidate({**self.approved, 'model': 'unapproved-model'})

    def test_changed_root_source_blocks_enrollment(self):
        self.driver.source_identity.return_value = 'changed'
        with self.assertRaisesRegex(Failure, 'lifecycle-source-changed'):
            self.driver.approve_candidate(self.approved)



if __name__ == '__main__':
    unittest.main()
