"""Offline subprocess tests; no host configuration or daemons are changed."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integration_gate import integration_only  # noqa: E402


REPO = Path(__file__).resolve().parents[1]
REAL_KEYGEN = shutil.which("ssh-keygen")

MOCK = r'''#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys
root = pathlib.Path(os.environ['FIXTURE'])
state_path = root / 'state.json'
s = json.loads(state_path.read_text())
name, a = pathlib.Path(sys.argv[0]).name, sys.argv[1:]
mutation = False
code, output, error_output = 0, '', ''
if name == 'selinuxenabled':
    code = 1
elif name == 'getent':
    output = f'tester:x:{os.getuid()}:{os.getgid()}::{root}/home/tester:/bin/bash'
elif name == 'ip':
    code = int(a[-1] != 'eth0')
elif name == 'nmcli':
    output = 'test-connection' if 'GENERAL.CON-UUID' in a else s.get('nm_zone', '')
elif name == 'chown' or name == 'restorecon':
    mutation = True
elif name == 'dnf':
    mutation = True
elif name == 'ssh-keygen':
    if a == ['-A']:
        mutation = True
    else:
        # Pass the process-substitution FD through to the real validator.
        fds = tuple(int(x.rsplit('/', 1)[1]) for x in a if x.startswith('/dev/fd/'))
        sys.exit(subprocess.call([os.environ['REAL_KEYGEN'], *a], pass_fds=fds))
elif name == 'systemctl':
    verb, svc = a[0], a[-1]
    if verb == 'show':
        output = s.get('override', '') if '--property=DropInPaths' in a else '/usr/lib/systemd/system/sshd.service'
    elif verb == 'is-active':
        output = s.get(svc + '_active', 'inactive')
        code = 0 if output == 'active' else 3
    elif verb == 'is-enabled':
        output = s.get(svc + '_enabled', 'disabled')
        code = 0 if output == 'enabled' else 1
    else:
        mutation = True
        if verb in ('enable', 'disable'): s[svc + '_enabled'] = 'enabled' if verb == 'enable' else 'disabled'
        if verb in ('start', 'stop') or '--now' in a: s[svc + '_active'] = 'inactive' if verb == 'stop' else 'active'
elif name == 'firewall-cmd':
    permanent = '--permanent' in a
    scope = 'permanent' if permanent else 'runtime'
    if any(x.startswith('--get-zone-of-interface') for x in a):
        output = s.get('zone_' + scope, 'FedoraServer')
        code = s.get('zone_rc_' + scope, 0)
        if code:
            error_output, output = output, ''
    elif '--get-zones' in a: output = 'FedoraServer public'
    elif '--list-sources' in a: output = s.get('sources', '')
    elif '--list-rich-rules' in a: output = s.get('rich_rules', '')
    elif '--list-ports' in a: output = ''
    elif '--get-all-rules' in a: output = ''
    elif '--get-policies' in a: output = s.get('policies', '')
    elif '--query-disable' in a:
        code = s.get('disable_rc_' + scope, 0)
    elif '--get-default-zone' in a: output = s.get('default_zone', 'FedoraServer')
    elif '--info-service=ssh' in a:
        output = 'ssh\n  ports: ' + s.get('ssh_ports', '22/tcp') + '\n  protocols: \n  source-ports: \n  modules: \n  destination: \n  includes: \n  helpers: '
    elif '--list-all' in a and '--policy=allow-host-ipv6' in a:
        output = """allow-host-ipv6 (active)
  disable: no
  priority: -15000
  target: CONTINUE
  ingress-zones: ANY
  egress-zones: HOST
  services:
  ports:
  protocols:
  masquerade: no
  forward-ports:
  source-ports:
  icmp-blocks:
  rich rules:
"""
        for kind in ('neighbour-advertisement', 'neighbour-solicitation', 'router-advertisement', 'redirect',
                     'mld-listener-done', 'mld-listener-query', 'mld-listener-report', 'mld2-listener-report'):
            output += f'    rule family="ipv6" icmp-type name="{kind}" accept\n'
        output += s.get('extra_policy_rule', '')
    elif '--query-service=ssh' in a:
        code = 0 if s[scope] else 1
    elif '--add-service=ssh' in a or '--remove-service=ssh' in a:
        mutation = True
        s[scope] = '--add-service=ssh' in a
    else: raise RuntimeError(a)
elif name == 'sshd':
    if '-T' in a:
        main = pathlib.Path(a[a.index('-f') + 1]) if '-f' in a else root / 'etc/ssh/sshd_config'
        lines = []
        for line in main.read_text().splitlines():
            if line.lower().startswith('include '):
                for f in sorted((root / 'etc/ssh/sshd_config.d').glob('*.conf')):
                    lines.extend(f.read_text().splitlines())
            else: lines.append(line)
        values = {}
        for line in lines:
            if line and not line.startswith('#'):
                key, value = line.split(None, 1)
                values.setdefault(key.lower(), value)
        defaults = {'port':'22', 'authorizedkeysfile':'.ssh/authorized_keys .ssh/authorized_keys2'}
        for key, value in defaults.items(): values.setdefault(key, value)
        output = '\n'.join(k + ' ' + v for k, v in values.items())
else: raise RuntimeError(name)
command = name + ' ' + ' '.join(a)
if mutation:
    with (root / 'mutations').open('a') as f: f.write(command + '\n')
failure = s.get('fail', '')
if failure and failure in command and not s.get('failed'):
    s['failed'] = True
    code = 42
if s.get('rollback_fail') and s.get('failed') and '--remove-service=ssh' in a:
    code = 42
state_path.write_text(json.dumps(s))
if '--quiet' not in a and output: print(output)
if error_output: print(error_output, file=sys.stderr)
sys.exit(code)
'''


class KeyOnlyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="key-only-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ("etc/ssh/sshd_config.d", "home/tester", "bin", "var/tmp", "run"):
            (self.root / directory).mkdir(parents=True)
        (self.root / "etc/fedora-release").write_text("Fedora release 44\n")
        self.home = self.root / "home/tester"
        self.sshdir = self.home / ".ssh"
        self.authorized = self.sshdir / "authorized_keys"
        self.dropin = self.root / "etc/ssh/sshd_config.d/00-local-key-only.conf"
        self.config = self.root / "etc/ssh/sshd_config"
        self.config.write_text(f"Include {self.dropin.parent}/*.conf\nX11Forwarding yes\n")
        self.state = {"runtime": False, "permanent": False,
                      "sshd_active": "active", "sshd_enabled": "disabled",
                      "firewalld_active": "active", "firewalld_enabled": "enabled"}
        self.write_state()
        mock = self.root / "bin/mock"
        mock.write_text(MOCK)
        mock.chmod(0o755)
        for name in ("dnf", "systemctl", "firewall-cmd", "ip", "getent", "chown", "restorecon", "ssh-keygen", "sshd", "selinuxenabled", "nmcli"):
            (self.root / "bin" / name).symlink_to(mock)
        # Redirect only OS paths and privilege/environment preconditions in a copy.
        # The production file exposes no test-root or command override interface.
        source = (REPO / "setup-ssh-key-only.sh").read_text()
        source = source.replace("[[ $EUID == 0 ]]", "true")
        source = source.replace("export PATH=/usr/sbin:/usr/bin:/sbin:/bin LC_ALL=C", "export LC_ALL=C")
        source = source.replace("/usr/sbin/sshd", str(self.root / "bin/sshd"))
        for prefix in ("/etc/", "/var/tmp/", "/run/", "/usr/lib/systemd/system/service.d/", "/usr/share/crypto-policies/"):
            source = source.replace(prefix, str(self.root) + prefix)
        # Model root ownership within the isolated fixture; never traverse host /tmp.
        source = source.replace('local expected_owner=0', f'local expected_owner={os.getuid()}')
        source = source.replace('[[ $current != / ]]', f'[[ $current != {self.root} ]]')
        self.script = self.root / "setup.sh"
        self.script.write_text(source)
        self.env = dict(os.environ, FIXTURE=str(self.root), REAL_KEYGEN=REAL_KEYGEN,
                        PATH=str(self.root / "bin") + ":" + os.environ["PATH"])
        self.env.pop("SSH_CONNECTION", None)
        self.env.pop("SSH_TTY", None)
        self.key = self.root / "fixture-key"
        subprocess.run([REAL_KEYGEN, "-q", "-t", "ed25519", "-N", "", "-f", str(self.key)], check=True)
        self.pub = Path(str(self.key) + ".pub")

    def write_state(self):
        (self.root / "state.json").write_text(json.dumps(self.state))

    def run_script(self, *extra, key=None, ok=True):
        result = subprocess.run(["bash", str(self.script), "--user", "tester", "--public-key-file",
                                 str(key or self.pub), "--interface", "eth0", "--zone", "FedoraServer", *extra],
                                env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def existing(self):
        self.sshdir.mkdir()
        self.sshdir.chmod(0o750)
        self.authorized.write_text('# preserved comment without newline')
        self.authorized.chmod(0o640)
        self.dropin.write_text('PasswordAuthentication yes\n')
        self.dropin.chmod(0o600)

    def test_apply_preserves_entries_and_is_idempotent(self):
        self.existing()
        environment = self.service_environment('OPTIONS=""\n')
        before = self.config.read_bytes()
        self.run_script()
        expected = b'# preserved comment without newline\n' + self.pub.read_bytes()
        self.assertEqual(self.authorized.read_bytes(), expected)
        self.assertEqual(self.authorized.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.sshdir.stat().st_mode & 0o777, 0o700)
        self.run_script()
        self.assertEqual(self.authorized.read_bytes(), expected)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertEqual(environment.read_text(), 'OPTIONS=""\n')
        self.assertEqual(list((self.root / 'var/tmp').iterdir()), [])

    def test_restricted_duplicate_is_not_broadened(self):
        self.sshdir.mkdir()
        key_fields = ' '.join(self.pub.read_text().split()[:2])
        content = f'from="192.0.2.1",restrict {key_fields} original comment\n'
        self.authorized.write_text(content)
        self.run_script()
        self.assertEqual(self.authorized.read_text(), content)

    def timeout_override(self, content):
        path = self.root / 'usr/lib/systemd/system/service.d/10-timeout-abort.conf'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        self.state['override'] = str(path)
        self.write_state()
        return path

    def test_reviewed_timeout_override_dry_run(self):
        path = self.timeout_override('# Fedora timeout policy\n\n[Service]\nTimeoutStopFailureMode=abort\n')
        before = path.read_bytes()
        result = self.run_script('--dry-run')
        self.assertIn('DRY RUN: no changes made', result.stdout)
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.root / 'mutations').exists())

    def test_changed_timeout_override_rejected(self):
        for content in ('[Service]\nTimeoutStopFailureMode=kill\n',
                        '[Service]\nTimeoutStopFailureMode=abort\nExecStart=/custom/sshd\n',
                        '[Unit]\nTimeoutStopFailureMode=abort\n', ''):
            with self.subTest(content=content):
                self.timeout_override(content)
                self.run_script('--dry-run', ok=False)
                self.assertFalse((self.root / 'mutations').exists())

    def test_missing_extra_and_unknown_overrides_rejected(self):
        path = self.timeout_override('[Service]\nTimeoutStopFailureMode=abort\n')
        path.unlink()
        for overrides in (str(path), '/etc/systemd/system/sshd.service.d/custom.conf',
                          str(path) + ' /etc/systemd/system/sshd.service.d/custom.conf'):
            with self.subTest(overrides=overrides):
                self.state['override'] = overrides
                self.write_state()
                self.run_script('--dry-run', ok=False)
                self.assertFalse((self.root / 'mutations').exists())

    def test_override_query_failure_rejected(self):
        self.state['fail'] = 'systemctl show sshd --property=DropInPaths'
        self.write_state()
        result = self.run_script('--dry-run', ok=False)
        self.assertIn('Cannot inspect sshd service overrides', result.stderr)
        self.assertFalse((self.root / 'mutations').exists())

    def test_invalid_private_and_multiple_keys(self):
        for value in (self.key.read_text(), 'ssh-ed25519 INVALID', self.pub.read_text() * 2):
            with self.subTest(value_type=value.split()[0]):
                bad = self.root / 'bad'
                bad.write_text(value)
                self.run_script(key=bad, ok=False)
                self.assertFalse((self.root / 'mutations').exists())

    def service_environment(self, content):
        path = self.root / 'etc/sysconfig/sshd'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_empty_service_options_dry_run(self):
        for content in ('OPTIONS=""\n', "OPTIONS=''\n", 'OPTIONS=\n',
                        '# comment\n\n; comment\n  OPTIONS=""  \n'):
            with self.subTest(content=content):
                path = self.service_environment(content)
                self.run_script('--dry-run')
                self.assertEqual(path.read_text(), content)
                self.assertFalse((self.root / 'mutations').exists())

    def test_active_service_environment_rejected_without_evaluation(self):
        marker = self.root / 'must-not-exist'
        for content in ('OPTIONS="-oPasswordAuthentication=yes"\n',
                        'OPTIONS=""\nOTHER=""\n',
                        'OPTIONS="-p 2222"\nOPTIONS=""\n',
                        f'OPTIONS="$(touch {marker})"\n',
                        'OPTIONS=""; exit 0\n',
                        'OPTIONS=""\\\n-oPasswordAuthentication=yes\n'):
            with self.subTest(content=content):
                path = self.service_environment(content)
                result = self.run_script('--dry-run', ok=False)
                self.assertIn('settings require manual review', result.stderr)
                self.assertEqual(path.read_text(), content)
                self.assertFalse(marker.exists())
                self.assertFalse((self.root / 'mutations').exists())

    def test_nonregular_service_environment_rejected(self):
        path = self.service_environment('OPTIONS=""\n')
        path.unlink()
        path.symlink_to(self.root / 'absent')
        self.run_script('--dry-run', ok=False)
        path.unlink()
        path.mkdir()
        self.run_script('--dry-run', ok=False)
        self.assertFalse((self.root / 'mutations').exists())

    def test_wrong_runtime_and_permanent_zone(self):
        for scope in ('runtime', 'permanent'):
            self.state['zone_' + scope] = 'public'
            self.write_state()
            self.run_script(ok=False)
            self.assertFalse((self.root / 'mutations').exists())
            del self.state['zone_' + scope]

    def test_conditional_and_unknown_include(self):
        for content in ('Match User tester\n', 'Include /custom/config\n'):
            self.config.write_text(content)
            self.run_script(ok=False)
            self.assertFalse((self.root / 'mutations').exists())

    def test_effective_conflict_rolls_back(self):
        self.config.write_text('PasswordAuthentication yes\n' + self.config.read_text())
        result = self.run_script(ok=False)
        self.assertIn('Effective SSH conflict', result.stderr)
        self.assertFalse(self.sshdir.exists())
        self.assertFalse(self.dropin.exists())

    def test_dry_run_conflict_is_read_only(self):
        self.config.write_text('PasswordAuthentication yes\n' + self.config.read_text())
        self.run_script('--dry-run', ok=False)
        self.assertFalse((self.root / 'mutations').exists())

    def test_networkmanager_persistent_zone(self):
        self.state.update(zone_permanent='no zone', zone_rc_permanent=2, nm_zone='FedoraServer')
        self.write_state()
        self.run_script('--dry-run')
        self.state['nm_zone'] = ''
        self.write_state()
        self.run_script('--dry-run')
        self.state['default_zone'] = 'public'
        self.write_state()
        self.run_script('--dry-run', ok=False)

    def test_zone_query_errors_do_not_trigger_fallback(self):
        for rc, message in ((2, 'invalid option'), (253, 'no zone'), (1, ''), (2, 'no zone\nextra diagnostic')):
            with self.subTest(rc=rc, message=message):
                self.state.update(zone_permanent=message, zone_rc_permanent=rc)
                self.write_state()
                result = self.run_script('--dry-run', ok=False)
                self.assertIn('Cannot read permanent interface assignment', result.stderr)
                self.assertFalse((self.root / 'mutations').exists())

    def test_fedora_crypto_include_paths(self):
        crypto = self.root / 'etc/crypto-policies/back-ends/opensshserver.config'
        crypto.parent.mkdir(parents=True)
        crypto.write_text('# crypto policy fixture\n')
        for name in ('50-redhat.conf', '40-redhat-crypto-policies.conf', '90-custom.conf'):
            with self.subTest(name=name):
                path = self.dropin.parent / name
                path.write_text(f'Include {crypto}\n')
                self.run_script('--dry-run', ok=name != '90-custom.conf')
                path.unlink()
        self.assertFalse((self.root / 'mutations').exists())

    def test_gateway_policy_set_must_be_disabled_in_both_scopes(self):
        self.state['policies'] = ('allow-host-ipv6 gateway-dmz-to-HOST gateway-lan-to-HOST '
                                  'gateway-lan-to-work gateway-lan-to-world gateway-world-to-HOST')
        self.write_state()
        self.run_script('--dry-run')
        for scope in ('runtime', 'permanent'):
            for rc in (1, 253):
                with self.subTest(scope=scope, rc=rc):
                    self.state['disable_rc_' + scope] = rc
                    self.write_state()
                    result = self.run_script('--dry-run', ok=False)
                    self.assertIn('gateway policy requires manual review', result.stderr)
                    self.assertFalse((self.root / 'mutations').exists())
            del self.state['disable_rc_' + scope]

    def crypto_symlink(self):
        crypto = self.root / 'etc/crypto-policies/back-ends/opensshserver.config'
        target = self.root / 'usr/share/crypto-policies/DEFAULT/opensshserver.txt'
        crypto.parent.mkdir(parents=True)
        target.parent.mkdir(parents=True)
        target.write_text('# DEFAULT policy fixture\n')
        crypto.symlink_to(target)
        (self.dropin.parent / '40-redhat-crypto-policies.conf').write_text(f'Include {crypto}\n')
        return crypto, target

    def test_reviewed_crypto_symlink_is_preserved(self):
        crypto, target = self.crypto_symlink()
        alias = target.with_name('packaged-alias.txt')
        os.link(target, alias)
        self.run_script('--dry-run')
        self.assertTrue(crypto.is_symlink())
        self.assertEqual(crypto.resolve(), target)
        self.assertEqual(target.read_text(), '# DEFAULT policy fixture\n')
        self.assertEqual(alias.read_text(), target.read_text())
        self.assertEqual(target.stat().st_nlink, 2)
        self.assertFalse((self.root / 'mutations').exists())

    def test_crypto_symlink_rejects_unknown_missing_and_writable_targets(self):
        crypto, target = self.crypto_symlink()
        for path in (target, target.parent, crypto.parent):
            mode = path.stat().st_mode & 0o777
            path.chmod(mode | 0o020)
            result = self.run_script('--dry-run', ok=False)
            self.assertIn('must not be group/world writable', result.stderr)
            path.chmod(mode)
        crypto.unlink()
        crypto.symlink_to(self.pub)
        result = self.run_script('--dry-run', ok=False)
        self.assertIn('Unreviewed crypto-policy symlink target', result.stderr)
        alias = self.root / 'policy-alias'
        alias.symlink_to(target)
        crypto.unlink()
        crypto.symlink_to(alias)
        result = self.run_script('--dry-run', ok=False)
        self.assertIn('Unreviewed crypto-policy symlink target', result.stderr)
        crypto.unlink()
        crypto.symlink_to(target)
        target.unlink()
        result = self.run_script('--dry-run', ok=False)
        self.assertIn('Unresolvable crypto-policy symlink', result.stderr)
        self.assertFalse((self.root / 'mutations').exists())

    def test_crypto_symlink_requires_expected_owner(self):
        self.crypto_symlink()
        source = self.script.read_text().replace(f'local expected_owner={os.getuid()}',
                                               f'local expected_owner={os.getuid() + 1}')
        self.script.write_text(source)
        result = self.run_script('--dry-run', ok=False)
        self.assertIn('must be root-owned', result.stderr)
        self.assertFalse((self.root / 'mutations').exists())

    def test_standard_ipv6_policy_and_modified_policy(self):
        self.state['policies'] = 'allow-host-ipv6'
        self.write_state()
        self.run_script('--dry-run')
        self.state['extra_policy_rule'] = '    rule service name="ssh" reject\n'
        self.write_state()
        self.run_script('--dry-run', ok=False)

    def test_symlink_and_hardlink_refused(self):
        self.sshdir.mkdir()
        self.authorized.symlink_to(self.pub)
        self.run_script(ok=False)
        self.authorized.unlink()
        os.link(self.pub, self.authorized)
        self.run_script(ok=False)
        self.assertFalse((self.root / 'mutations').exists())

    def test_dry_run_does_not_mutate(self):
        self.existing()
        before = {p: (p.read_bytes(), p.stat().st_mode) for p in (self.authorized, self.dropin, self.config)}
        self.run_script('--dry-run')
        for p, expected in before.items():
            self.assertEqual((p.read_bytes(), p.stat().st_mode), expected)
        self.assertFalse((self.root / 'mutations').exists())
        self.assertEqual(list((self.root / 'var/tmp').iterdir()), [])

    def test_firewall_customization_refused(self):
        for field in ('sources', 'rich_rules', 'policies', 'ssh_ports'):
            self.state[field] = 'custom'
            self.write_state()
            self.run_script(ok=False)
            self.assertFalse((self.root / 'mutations').exists())
            del self.state[field]

    def test_failures_restore_files_modes_services_and_firewall(self):
        self.existing()
        for failure in ('sshd -t', '--add-service=ssh', '--permanent --zone=FedoraServer --add-service=ssh',
                        'systemctl reload sshd', 'systemctl enable sshd'):
            with self.subTest(failure=failure):
                self.state['fail'] = failure
                self.write_state()
                before = {p: (p.read_bytes(), p.stat().st_mode) for p in (self.authorized, self.dropin)}
                result = self.run_script(ok=False)
                self.assertIn('Recovery files retained', result.stderr)
                self.assertNotIn('Restoration incomplete', result.stderr)
                for p, expected in before.items():
                    self.assertEqual((p.read_bytes(), p.stat().st_mode), expected)
                self.assertEqual(self.sshdir.stat().st_mode & 0o777, 0o750)
                actual = json.loads((self.root / 'state.json').read_text())
                for field in ('runtime', 'permanent', 'sshd_active', 'sshd_enabled', 'firewalld_active', 'firewalld_enabled'):
                    self.assertEqual(actual[field], self.state[field], field)

    def test_failed_restoration_is_reported(self):
        self.state.update(fail='systemctl reload sshd', rollback_fail=True)
        self.write_state()
        result = self.run_script(ok=False)
        self.assertIn('Restoration incomplete', result.stderr)

    def test_preserves_preexisting_allowance_on_failure(self):
        self.state.update(runtime=True, permanent=True, fail='systemctl reload sshd')
        self.write_state()
        self.run_script(ok=False)
        actual = json.loads((self.root / 'state.json').read_text())
        self.assertTrue(actual['runtime'] and actual['permanent'])

    def test_initially_inactive_services_restored(self):
        self.state.update(sshd_active='inactive', firewalld_active='inactive',
                          firewalld_enabled='disabled', fail='systemctl start sshd')
        self.write_state()
        self.run_script(ok=False)
        actual = json.loads((self.root / 'state.json').read_text())
        self.assertEqual(actual['sshd_active'], 'inactive')
        self.assertEqual(actual['firewalld_active'], 'inactive')
        self.assertEqual(actual['firewalld_enabled'], 'disabled')

    @integration_only("real /usr/sbin/sshd candidate validation")
    @unittest.skipUnless(Path('/usr/sbin/sshd').is_file(), 'Real sshd is unavailable')
    def test_real_sshd_candidate_and_first_value_conflict(self):
        self.config.write_text(f'HostKey {self.key}\n' + self.config.read_text())
        self.dropin.write_text('PasswordAuthentication yes\n')
        invocation = ['bash', '-c',
                      'source "$1"; config=$2; confdir=$3; dropin=$4; sshd=/usr/sbin/sshd; effective_check candidate',
                      'test', str(REPO / 'setup-ssh-key-only.sh'), str(self.config),
                      str(self.dropin.parent), str(self.dropin)]
        result = subprocess.run(invocation, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.config.write_text('PasswordAuthentication yes\n' + self.config.read_text())
        result = subprocess.run(invocation, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Effective SSH conflict: passwordauthentication', result.stderr)
        self.assertEqual(self.dropin.read_text(), 'PasswordAuthentication yes\n')


if __name__ == '__main__':
    unittest.main()
