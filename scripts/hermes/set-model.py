import os
import pathlib
import re
import tempfile

import yaml

config_path_value = os.environ.get('HERMES_CONFIG_PATH', '/opt/data/config.yaml').strip()
config_path = pathlib.Path(config_path_value)
if not config_path.is_absolute():
    raise SystemExit('HERMES_CONFIG_PATH must be absolute')
data_dir = config_path.parent
config = yaml.safe_load(config_path.read_text(encoding='utf-8')) or {}
if not isinstance(config, dict):
    raise SystemExit('config.yaml root is not a mapping')

provider = os.environ.get('HERMES_PROVIDER', 'nous').strip()
model = os.environ.get('HERMES_MODEL', 'anthropic/claude-sonnet-4.6').strip()
if provider not in {'openai-codex', 'openai-api', 'nous'}:
    raise SystemExit('unsupported Hermes provider')
if not re.fullmatch(r'[A-Za-z0-9._:/-]+', model):
    raise SystemExit('unsupported Hermes model identifier')
model_section = config.get('model')
if not isinstance(model_section, dict):
    model_section = {}
    config['model'] = model_section
model_section['provider'] = provider
model_section['default'] = model
model_section['model'] = model
# Endpoint credentials are managed by Hermes auth storage. Remove stale
# endpoint overrides so a provider switch uses the selected provider's
# built-in transport and never carries an old key or gateway into the new one.
for key in ('api_key', 'base_url', 'api_mode', 'key_env'):
    model_section.pop(key, None)
config['provider'] = provider
config['default_model'] = model

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

print('Hermes provider and model configured; no secret values displayed.')
