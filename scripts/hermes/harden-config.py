import datetime
import os
import pathlib
import shutil
import tempfile

import yaml

data_dir = pathlib.Path('/opt/data')
config_path = data_dir / 'config.yaml'
env_path = data_dir / '.env'
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')

config = yaml.safe_load(config_path.read_text(encoding='utf-8')) or {}
if not isinstance(config, dict):
    raise SystemExit('config.yaml root is not a mapping')

def section(name):
    value = config.get(name)
    if not isinstance(value, dict):
        value = {}
        config[name] = value
    return value

section('approvals').update({
    'mode': 'manual',
    'timeout': 300,
    'cron_mode': 'deny',
    'single_query_mode': 'deny',
    'mcp_reload_confirm': True,
    'destructive_slash_confirm': True,
})
section('security').update({
    'allow_private_urls': False,
    'redact_secrets': True,
    'protected_instruction_files': True,
    'tirith_enabled': True,
    'tirith_fail_open': False,
    'allow_lazy_installs': False,
})
config['hooks_auto_accept'] = False
config['hooks'] = {}
config['mcp_servers'] = {}
section('plugins').update({'enabled': [], 'disabled': []})
section('cron')['allow_agent_scheduling'] = False
section('checkpoints')['enabled'] = True
section('tool_loop_guardrails').update({
    'hard_stop_enabled': True,
    'hard_stop_after': {
        'exact_failure': 5,
        'idempotent_no_progress': 5,
        'same_tool_failure': 8,
    },
})
section('skills').update({
    'external_dirs': [],
    'trusted_project_dirs': [],
    'project_discovery': False,
    'guard_agent_created': True,
    'write_approval': True,
})
section('memory').update({'provider': '', 'write_approval': True})
section('web').update({'keyless_fallback': False, 'keyless_rescue': False})
section('terminal').update({'backend': 'local', 'docker_mount_cwd_to_workspace': False})
section('platform_toolsets')['cli'] = ['hermes-cli']

shutil.copy2(config_path, data_dir / f'config.yaml.pre-hardening-{stamp}')
fd, tmp_name = tempfile.mkstemp(prefix='.config.yaml.', dir=data_dir)
try:
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        yaml.safe_dump(config, handle, sort_keys=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(tmp_name, 0o600)
    os.replace(tmp_name, config_path)
finally:
    if os.path.exists(tmp_name):
        os.unlink(tmp_name)

if env_path.exists():
    shutil.copy2(env_path, data_dir / f'.env.pre-hardening-{stamp}')
    updates = {
        'API_SERVER_ENABLED': 'false',
        'HERMES_DASHBOARD': '0',
        'GATEWAY_ALLOW_ALL_USERS': 'false',
        'WEBHOOK_ENABLED': 'false',
    }
    lines = env_path.read_text(encoding='utf-8').splitlines()
    output = []
    seen = set()
    for line in lines:
        key = line.split('=', 1)[0].strip() if '=' in line and not line.lstrip().startswith('#') else ''
        if key in updates:
            output.append(f'{key}={updates[key]}')
            seen.add(key)
        else:
            output.append(line)
    for key, value in updates.items():
        if key not in seen:
            output.append(f'{key}={value}')
    fd, tmp_name = tempfile.mkstemp(prefix='.env.', dir=data_dir)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write('\n'.join(output) + '\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, env_path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)

print('Hermes configuration hardened; no secret values displayed.')
