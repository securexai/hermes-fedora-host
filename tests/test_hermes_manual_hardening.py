"""Behavioral tests for the manual-profile configuration contract.

Runs ``harden-config.py`` and ``verify-contract.py`` as subprocesses against
synthetic profiles. Covers review findings 2 (empty mappings must replace, not
merge), 8 (credential-free verification path) and 10 (convergent re-application:
no write, no backup, stable hash/mode/owner).
"""

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
MANUAL = REPO_ROOT / 'scripts/hermes/manual'
HARDEN = MANUAL / 'config/harden-config.py'
VERIFY = MANUAL / 'config/verify-contract.py'
CONTRACT = MANUAL / 'config/profile-contract.yaml'

NARROW = ['terminal', 'file', 'memory', 'clarify']
# Assembled at runtime and never a real credential; also avoids writing a
# scanner-friendly `KEY=value` literal into the repository.
ENV_KEY = 'OPENAI_API_KEY'
SYNTHETIC = 'sk-' + ('a' * 24)


def run(script, *args, data_dir, env=None):
    environment = dict(os.environ)
    environment['HERMES_DATA_DIR'] = str(data_dir)
    if env:
        environment.update(env)
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True, text=True, env=environment, check=False,
    )


def backups(data_dir):
    return sorted(p.name for p in data_dir.glob('config.yaml.pre-contract-*'))


class HardenConfigTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.data = Path(temporary.name)

    def write_config(self, text, mode=0o600):
        path = self.data / 'config.yaml'
        path.write_text(text, encoding='utf-8')
        path.chmod(mode)
        return path

    def populate(self):
        return self.write_config(
            'agent:\n'
            '  custom_operator_key: keep-me\n'
            '_config_version: 11\n'
            'terminal:\n'
            '  backend: local\n'
            'hooks:\n'
            '  on_start:\n'
            '    - command: /usr/local/bin/legacy-hook\n'
            'mcp_servers:\n'
            '  legacy:\n'
            '    command: /usr/local/bin/legacy-mcp\n'
            'toolsets:\n'
            '  - hermes-cli\n'
            'plugins:\n'
            '  enabled:\n'
            '    - legacy-plugin\n'
        )

    def test_populated_security_collections_are_replaced(self):
        self.populate()
        result = run(HARDEN, data_dir=self.data)
        self.assertEqual(result.returncode, 0, result.stderr)
        import yaml
        config = yaml.safe_load((self.data / 'config.yaml').read_text())
        self.assertEqual(config.get('hooks'), {})
        self.assertEqual(config.get('mcp_servers'), {})
        self.assertEqual(config.get('plugins', {}).get('enabled'), [])
        self.assertEqual(config.get('toolsets'), NARROW)
        self.assertEqual(config['agent']['custom_operator_key'], 'keep-me')
        self.assertEqual(config['_config_version'], 11)

    def test_convergence_is_a_noop_on_second_and_third_application(self):
        self.populate()
        first = run(HARDEN, data_dir=self.data)
        self.assertEqual(first.returncode, 0, first.stderr)
        path = self.data / 'config.yaml'
        snapshot = (hashlib.sha256(path.read_bytes()).hexdigest(),
                    path.stat().st_mtime_ns, path.stat().st_mode, path.stat().st_uid, path.stat().st_gid,
                    len(backups(self.data)))
        second = run(HARDEN, data_dir=self.data)
        third = run(HARDEN, data_dir=self.data)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(third.returncode, 0, third.stderr)
        self.assertIn('PROFILE_CONTRACT_UNCHANGED', second.stdout)
        after = (hashlib.sha256(path.read_bytes()).hexdigest(),
                 path.stat().st_mtime_ns, path.stat().st_mode, path.stat().st_uid, path.stat().st_gid,
                 len(backups(self.data)))
        self.assertEqual(snapshot, after)
        self.assertEqual(len(backups(self.data)), 1)

    def test_change_creates_exactly_one_backup(self):
        self.write_config('agent:\n  custom_operator_key: keep-me\n')
        run(HARDEN, data_dir=self.data)
        self.assertEqual(len(backups(self.data)), 1)
        run(HARDEN, data_dir=self.data)
        self.assertEqual(len(backups(self.data)), 1)
        # An explicit upgrade is the only path that backs up a converged profile.
        upgrade = run(HARDEN, '--upgrade', data_dir=self.data)
        self.assertEqual(upgrade.returncode, 0, upgrade.stderr)
        self.assertEqual(len(backups(self.data)), 2)

    def test_check_mode_verifies_without_writing(self):
        self.populate()
        path = self.data / 'config.yaml'
        before = path.read_bytes()
        stale = run(HARDEN, '--check', data_dir=self.data)
        self.assertNotEqual(stale.returncode, 0, 'a stale profile must fail the check')
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(backups(self.data), [])
        run(HARDEN, data_dir=self.data)
        fresh = run(HARDEN, '--check', data_dir=self.data)
        self.assertEqual(fresh.returncode, 0, fresh.stdout + fresh.stderr)
        self.assertIn('PROFILE_CONTRACT_CHECK=PASS', fresh.stdout)

    def test_mode_and_owner_are_preserved_when_changed(self):
        path = self.populate()
        path.chmod(0o640)
        stat_before = path.stat()
        result = run(HARDEN, data_dir=self.data)
        self.assertEqual(result.returncode, 0, result.stderr)
        stat_after = path.stat()
        self.assertEqual(stat_before.st_mode, stat_after.st_mode)
        self.assertEqual(stat_before.st_uid, stat_after.st_uid)
        self.assertEqual(stat_before.st_gid, stat_after.st_gid)

    def test_malformed_config_is_refused_and_untouched(self):
        path = self.write_config('model: [unclosed\n')
        result = run(HARDEN, data_dir=self.data)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(path.read_text(), 'model: [unclosed\n')

    def test_check_mode_verifies_environment_policy_without_writing(self):
        self.write_config('agent:\n  custom_operator_key: keep-me\n')
        env = self.data / '.env'
        env.write_text('API_SERVER_ENABLED=true\n', encoding='utf-8')
        env.chmod(0o600)
        # Config is not applied either, so the check must fail without writing.
        before_config = (self.data / 'config.yaml').read_bytes()
        before_env = env.read_bytes()
        result = run(HARDEN, '--check', data_dir=self.data)
        self.assertNotEqual(result.returncode, 0, 'a drifted environment must fail the check')
        self.assertEqual((self.data / 'config.yaml').read_bytes(), before_config)
        self.assertEqual(env.read_bytes(), before_env)
        self.assertEqual(backups(self.data), [])
        run(HARDEN, data_dir=self.data)
        fresh = run(HARDEN, '--check', data_dir=self.data)
        self.assertEqual(fresh.returncode, 0, fresh.stdout + fresh.stderr)
        self.assertIn('PROFILE_CONTRACT_CHECK=PASS', fresh.stdout)

    def test_check_mode_fails_and_writes_nothing_when_policy_env_is_missing(self):
        self.write_config('agent:\n  custom_operator_key: keep-me\n')
        run(HARDEN, data_dir=self.data)
        env = self.data / '.env'
        self.assertTrue(env.exists(), 'apply must create the policy .env')
        before_backups = backups(self.data)
        env.unlink()
        before_config = (self.data / 'config.yaml').read_bytes()
        result = run(HARDEN, '--check', data_dir=self.data)
        self.assertNotEqual(result.returncode, 0, 'a missing policy file must fail the check')
        self.assertFalse(env.exists(), 'check mode must not recreate the policy file')
        self.assertEqual((self.data / 'config.yaml').read_bytes(), before_config)
        self.assertEqual(backups(self.data), before_backups, 'check mode must not add a backup')

    def test_converged_rerun_does_not_touch_the_environment_file(self):
        self.write_config('agent:\n  custom_operator_key: keep-me\n')
        run(HARDEN, data_dir=self.data)
        env = self.data / '.env'
        stamp = env.stat().st_mtime_ns
        settled = env.read_bytes()
        second = run(HARDEN, data_dir=self.data)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(env.read_bytes(), settled)
        self.assertEqual(env.stat().st_mtime_ns, stamp, 'a converged .env must not be rewritten')

    def test_security_controlled_mappings_are_replaced_exactly(self):
        self.write_config(
            'security:\n'
            '  allow_private_urls: true\n'
            '  operator_extra_control: keep-me-not\n'
            'approvals:\n'
            '  mode: always\n'
            '  operator_extra_approval: true\n'
            'agent:\n'
            '  custom_operator_key: keep-me\n'
        )
        result = run(HARDEN, data_dir=self.data)
        self.assertEqual(result.returncode, 0, result.stderr)
        import yaml
        config = yaml.safe_load((self.data / 'config.yaml').read_text())
        self.assertEqual(config['security']['allow_private_urls'], False)
        self.assertNotIn('operator_extra_control', config['security'])
        self.assertEqual(config['approvals']['mode'], 'manual')
        self.assertNotIn('operator_extra_approval', config['approvals'])
        self.assertEqual(config['agent']['custom_operator_key'], 'keep-me')

    def test_fresh_state_is_owned_by_the_invoking_process(self):
        # The contract is applied inside the container as the mapped runtime UID;
        # a fresh file must belong to that process at mode 0600, never to root.
        result = run(HARDEN, data_dir=self.data)
        self.assertEqual(result.returncode, 0, result.stderr)
        stat = (self.data / 'config.yaml').stat()
        self.assertEqual(stat.st_mode & 0o777, 0o600)
        self.assertEqual(stat.st_uid, os.getuid())
        self.assertEqual(stat.st_gid, os.getgid())

    def test_env_allowlist_preserves_secrets_and_unrelated_keys(self):
        env = self.data / '.env'
        env.write_text(f'{ENV_KEY}={SYNTHETIC}\nUNRELATED_SETTING=keep\n', encoding='utf-8')
        env.chmod(0o600)
        self.write_config('agent:\n  custom_operator_key: keep-me\n')
        result = run(HARDEN, data_dir=self.data)
        self.assertEqual(result.returncode, 0, result.stderr)
        text = env.read_text()
        self.assertIn(f'{ENV_KEY}={SYNTHETIC}', text)
        self.assertIn('UNRELATED_SETTING=keep', text)
        for key in ('API_SERVER_ENABLED=false', 'HERMES_DASHBOARD=0',
                    'GATEWAY_ALLOW_ALL_USERS=false', 'WEBHOOK_ENABLED=false'):
            self.assertIn(key, text)
        settled = env.read_bytes()
        run(HARDEN, data_dir=self.data)
        self.assertEqual(env.read_bytes(), settled)


class VerifyContractTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.data = Path(temporary.name)

    def conforming(self):
        path = self.data / 'config.yaml'
        path.write_text(
            'hooks: {}\n'
            'mcp_servers: {}\n'
            'toolsets: [terminal, file, memory, clarify]\n'
            'platform_toolsets:\n'
            '  cli: [terminal, file, memory, clarify]\n'
            '  telegram: [terminal, file, memory, clarify]\n'
            'approvals:\n'
            '  mode: manual\n'
            '  timeout: 300\n'
            '  cron_mode: deny\n'
            '  single_query_mode: deny\n'
            '  unattended_mode: deny\n'
            '  mcp_reload_confirm: true\n'
            '  destructive_slash_confirm: true\n'
            'security:\n'
            '  allow_private_urls: false\n'
            '  redact_secrets: true\n'
            '  protected_instruction_files: true\n'
            '  tirith_enabled: true\n'
            '  tirith_fail_open: false\n'
            '  allow_lazy_installs: false\n'
            'hooks_auto_accept: false\n'
            'plugins: {enabled: [], disabled: []}\n'
            'cron: {allow_agent_scheduling: false}\n'
            'checkpoints: {enabled: true}\n'
            'tool_loop_guardrails:\n'
            '  hard_stop_enabled: true\n'
            '  hard_stop_after: {exact_failure: 5, idempotent_no_progress: 5, same_tool_failure: 8}\n'
            'skills:\n'
            '  external_dirs: []\n'
            '  trusted_project_dirs: []\n'
            '  project_discovery: false\n'
            '  guard_agent_created: true\n'
            '  write_approval: true\n'
            'memory: {provider: "", write_approval: true}\n'
            'web: {keyless_fallback: false, keyless_rescue: false}\n'
            'terminal:\n'
            '  backend: ssh\n'
            '  ssh_host: worker\n'
            '  ssh_user: worker\n'
            '  ssh_port: 22\n'
            '  ssh_key: /opt/hermes/gateway-ssh/worker_client_ed25519\n'
            '  docker_mount_cwd_to_workspace: false\n',
            encoding='utf-8')
        return path

    def verify(self, env=None):
        args = ['--contract', str(CONTRACT), '--config', str(self.data / 'config.yaml')]
        if env:
            args += ['--env', str(env)]
        return run(VERIFY, *args, data_dir=self.data)

    def test_conforming_profile_passes(self):
        self.conforming()
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('CONTRACT_VERIFY=PASS', result.stdout)

    def test_absent_security_collections_are_equivalent_to_empty(self):
        path = self.conforming()
        text = path.read_text().replace('hooks: {}\n', '').replace('mcp_servers: {}\n', '')
        path.write_text(text)
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_populated_hooks_fail(self):
        path = self.conforming()
        path.write_text(path.read_text().replace('hooks: {}', 'hooks:\n  on_start: [legacy]'))
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('CONTRACT_VERIFY=FAIL', result.stdout)

    def test_extra_security_control_fails_exact_replacement(self):
        path = self.conforming()
        path.write_text(path.read_text().replace(
            'security:\n  allow_private_urls: false\n',
            'security:\n  allow_private_urls: false\n  operator_extra_control: true\n'))
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('replace.security', result.stdout)

    def test_extra_platform_toolset_fails_exact_replacement(self):
        # The review's exact counterexample: a broad per-platform override added
        # back after apply must fail verification, not be silently tolerated.
        path = self.conforming()
        path.write_text(path.read_text().replace(
            '  telegram: [terminal, file, memory, clarify]\n',
            '  telegram: [terminal, file, memory, clarify]\n  discord: [hermes-cli]\n'))
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('replace.platform_toolsets', result.stdout)

    def test_extra_platform_toolset_is_removed_by_apply(self):
        path = self.conforming()
        path.write_text(path.read_text().replace(
            '  telegram: [terminal, file, memory, clarify]\n',
            '  telegram: [terminal, file, memory, clarify]\n  discord: [hermes-cli]\n'))
        import yaml
        applied = run(HARDEN, data_dir=self.data)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        config = yaml.safe_load(path.read_text())
        self.assertNotIn('discord', config['platform_toolsets'])
        self.assertEqual(sorted(config['platform_toolsets']), ['cli', 'telegram'])
        self.assertEqual(self.verify().returncode, 0)

    def test_unmanaged_keys_outside_replacement_paths_are_preserved(self):
        path = self.conforming()
        path.write_text('agent:\n  custom_operator_key: keep-me\n' + path.read_text())
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        applied = run(HARDEN, data_dir=self.data)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        import yaml
        config = yaml.safe_load(path.read_text())
        self.assertEqual(config['agent']['custom_operator_key'], 'keep-me')

    def test_wrong_toolsets_fail(self):
        path = self.conforming()
        path.write_text(path.read_text().replace('[terminal, file, memory, clarify]', '[hermes-cli]'))
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)

    def test_env_allowlist_is_checked(self):
        self.conforming()
        env = self.data / '.env'
        env.write_text('API_SERVER_ENABLED=true\n', encoding='utf-8')
        result = self.verify(env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('env.API_SERVER_ENABLED', result.stdout)


if __name__ == '__main__':
    unittest.main()
