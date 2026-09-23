"""Independent observations and bounded restore probes for the isolated certifier."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    action, directory, run_id, expected_kernel = sys.argv[1:]
    directory = Path(directory)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(directory / 'payload'))
    import host
    from common import decode, digest, require, run
    manifest = decode((directory / 'manifest.json').read_bytes())
    image = manifest['image']

    def application(script):
        return decode(host.as_hermes(['podman', 'exec', '-i', '--user', '10000:10000',
                                     'hermes', 'python3', '-'], data=script.encode()))

    if action == 'cleanup-credential':
        instance = host.Host(directory)
        records = decode((instance.previous / 'files.json').read_bytes())
        record = next(r for r in records if r['path'] == str(host.CREDENTIAL))
        if record['exists']:
            from common import atomic, protected_file
            source = protected_file(instance.previous / record['index'], 0)
            atomic(host.CREDENTIAL, source.read_bytes())
            host.CREDENTIAL.chmod(record['mode'])
            run(['systemctl', 'restart', 'hermes-runtime-credentials.service'])
            import pwd
            run(['systemctl', 'start', 'user@' + str(pwd.getpwnam('hermes').pw_uid) + '.service'])
            host.service('restart', 'hermes.service')
            host.wait_health(image)
            require(digest(host.CREDENTIAL) == digest(source), 'prior-credential-not-restored')
        else:
            host.service('stop', 'hermes.service')
            host.CREDENTIAL.unlink(missing_ok=True)
        return {'ok': True, 'stage': 'prior-credential-restored'}
    if action in {'seed', 'damage', 'restore-check'}:
        marker = run_id if action != 'damage' else 'deliberately-changed-' + run_id
        code = """import json,pathlib,yaml
from hermes_cli.config import load_config
p=pathlib.Path('/opt/data/config.yaml')
c=yaml.safe_load(p.read_text())
"""
        if action != 'restore-check':
            code += "c['certification_restore_probe']=" + repr(marker) + "\np.write_text(yaml.safe_dump(c,sort_keys=False))\n"
        code += "assert load_config()['certification_restore_probe']==" + repr(marker) + "\n"
        code += "assert load_config()['approvals']['mode']=='manual'\n"
        code += "assert load_config()['security']['allow_private_urls'] is False\n"
        code += "print(json.dumps({'ok':True,'stage':" + repr(action) + ",'application_loaded_state':True}))\n"
        result = application(code)
        if action == 'damage': host.service('stop', 'hermes.service')
        return result
    if action == 'restore':
        host.service('stop', 'hermes.service')
        # This archive's digest was checked by the endpoint against the original snapshot.
        # Extraction has only the rootless user's namespace authority, never host root.
        import pwd
        uid = pwd.getpwnam('hermes').pw_uid
        result = subprocess.run(['runuser', '-u', 'hermes', '--', 'env', '--chdir=/home/hermes',
                                 'HOME=/home/hermes', 'XDG_RUNTIME_DIR=/run/user/' + str(uid),
                                 'podman', 'unshare', 'tar', '-C', '/home/hermes/data', '-xf', '-'],
                                stdin=sys.stdin.buffer, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        require(result.returncode == 0, 'rootless-restore-failed')
        host.service('start', 'hermes.service')
        host.wait_health(image)
        return {'ok': True, 'stage': 'restored', 'runtime_healthy': True}
    require(action in {'observe', 'observe-previous', 'observe-returned'}, 'unknown-observation')
    from lab_previous import retained, modules, PREVIOUS
    lab_policy = decode(Path('/etc/hermes-lab-certifier.json').read_bytes())
    prior = retained(lab_policy)
    updated_kernel = expected_kernel
    if action == 'observe-previous':
        expected_kernel = prior['kernel']
    host.preflight({'luks_device': '/dev/vda3'})
    require(run(['uname', '-r']).decode().strip() == expected_kernel, 'wrong-running-kernel')
    require(host.package_baseline() == (directory / 'packages/installed-after.sha256').read_text().strip(),
            'wrong-result-inventory')
    tpm_observation = host.tpm_services(run)
    entry = PREVIOUS if action == 'observe-previous' else 'hermes-' + manifest['release_id'] + '.efi'
    target = Path('/boot/efi/EFI/Linux') / entry
    expected_hash = prior['uki_sha256'] if action == 'observe-previous' else manifest['files'][manifest['boot_artifact']]['sha256']
    require(digest(target) == expected_hash, 'wrong-installed-uki')
    entries = decode(run(['bootctl', '--esp-path=/boot/efi', '--json=short', 'list']))
    require(any(e.get('id') == target.name and e.get('isSelected') for e in entries), 'wrong-selected-uki')
    host.wait_health(image)
    run(['systemctl', 'is-active', '--quiet', 'hermes-runtime-credentials.service'])
    credential_info = host.CREDENTIAL.stat()
    require(credential_info.st_uid == 0 and not credential_info.st_mode & 0o077, 'unsafe-encrypted-credential-mode')
    expected = run(['systemd-creds', 'decrypt', '--name=openai-api', str(host.CREDENTIAL), '-']).decode().strip()
    check = """import json,pathlib,errno,sys,yaml
expected=json.loads(sys.stdin.readline())
p=pathlib.Path('/opt/data/.env')
lines=p.read_text().splitlines()
assert 'OPENAI_API_KEY='+expected in lines
assert 'OPENAI_BASE_URL=https://api.openai.com/v1' in lines
try:
 with p.open('a'): pass
except OSError as error: assert error.errno==errno.EROFS
else: raise AssertionError('credential mount writable')
c=yaml.safe_load(pathlib.Path('/opt/data/config.yaml').read_text())
assert c['approvals']==dict(c['approvals'],mode='manual',cron_mode='deny',single_query_mode='deny')
assert c['security']['allow_private_urls'] is False and c['security']['tirith_fail_open'] is False
assert c['hooks']=={} and c['mcp_servers']=={} and c['cron']['allow_agent_scheduling'] is False
print(json.dumps({'credential_matches':True,'overlay_read_only':True,'security_config':True}))
"""
    result = decode(host.as_hermes(['podman', 'exec', '-i', '--user', '10000:10000', 'hermes',
                                   'python3', '-c', check], data=(json.dumps(expected)+'\n').encode()))
    metadata = host.as_hermes(['podman', 'inspect', 'hermes'])
    import pwd
    uid = pwd.getpwnam('hermes').pw_uid
    logged = subprocess.run(['runuser', '-u', 'hermes', '--', 'env', '--chdir=/home/hermes',
                             'HOME=/home/hermes', 'XDG_RUNTIME_DIR=/run/user/'+str(uid),
                             'podman', 'logs', '--tail', '200', 'hermes'], capture_output=True, timeout=30)
    require(logged.returncode == 0, 'runtime-log-check-failed')
    logs = logged.stdout + logged.stderr
    require(expected.encode() not in metadata and expected.encode() not in logs, 'runtime-credential-leak')
    if action in {'observe-previous', 'observe-returned'}:
        host.Host(directory).acceptance()
        result['inference'] = 'HERMES_OK'
    import hashlib
    result.update(encrypted_credential_sha256=digest(host.CREDENTIAL),
                  previous_modules_sha256=prior['modules_sha256'], updated_modules_sha256=modules(updated_kernel),
                  luks_metadata_sha256=hashlib.sha256(run(['cryptsetup', 'luksDump', '--dump-json-metadata', '/dev/vda3'])).hexdigest(),
                  pcr_public_key_sha256=digest('/etc/systemd/tpm2-pcr-public-key.pem'))
    result.update(ok=True, stage='observed', boot_id=host.boot_id(), kernel=expected_kernel,
                  package_inventory=host.package_baseline(), uki_sha256=digest(target),
                  runtime_healthy=True, secure_boot=True, tpm_services=True, tpm_profile=tpm_observation, selinux='Enforcing',
                  root_read_only=True, no_ports=True, bounded_credential_leak_check=True,
                  completed_at=int(time.time()))
    return result


if __name__ == '__main__':
    # No command or exception output can reproduce provider/configuration contents.
    try:
        print(json.dumps(main(), sort_keys=True))
    except Exception as error:
        print(json.dumps({'ok': False, 'error': getattr(error, 'reason', 'observation-failed')}))
        raise SystemExit(78) from None
