#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC1091,SC2015,SC2016
# Credential-free and provider acceptance for the managed Hermes service.

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s nullglob

readonly EXPECTED_IMAGE='docker.io/nousresearch/hermes-agent@sha256:e0df6adebddf29b91112aefc999d4aaf6846c9eb544faca5672a16a13590ff79'
readonly EXPECTED_CAP_MASK='00000000000000cb'
readonly STATE_DIR='/var/lib/hermes-deploy'

if [[ -r /usr/local/libexec/hermes-provider-auth-status ]]; then
  # shellcheck source=/usr/local/libexec/hermes-provider-auth-status
  source /usr/local/libexec/hermes-provider-auth-status
elif [[ -r "${BASH_SOURCE[0]%/*}/provider-auth-status.sh" ]]; then
  # shellcheck source=provider-auth-status.sh
  source "${BASH_SOURCE[0]%/*}/provider-auth-status.sh"
else
  provider_auth_status_logged_in() {
    local provider=$1 output=$2
    grep -Fqx -- "$provider: logged in" <<<"$output"
  }
fi
if [[ -r /usr/local/libexec/hermes-fedora-server-host ]]; then
  # shellcheck source=/usr/local/libexec/hermes-fedora-server-host
  source /usr/local/libexec/hermes-fedora-server-host
elif [[ -r "${BASH_SOURCE[0]%/*}/fedora-server-host.sh" ]]; then
  # shellcheck source=fedora-server-host.sh
  source "${BASH_SOURCE[0]%/*}/fedora-server-host.sh"
fi

PROVIDER_REQUIRED=false
INFERENCE_REQUIRED=false
EXPECTED_PROVIDER=''
EXPECTED_MODEL=''
FAILURES=0

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  FAILURES=$((FAILURES + 1))
}

pass() { printf 'PASS: %s\n' "$1"; }

version_at_least() {
  local actual=$1
  local required=$2
  local first
  first=$(printf '%s\n%s\n' "$required" "$actual" | sort -V | head -n 1)
  [[ "$first" == "$required" ]]
}

user_exec() {
  (cd /tmp && runuser -u hermes -- env HOME=/home/hermes XDG_RUNTIME_DIR="/run/user/$(id -u hermes)" "$@")
}

check_host() {
  local podman_version
  fedora_server_is_supported && pass 'Fedora Server 44 host' || fail 'supported Fedora Server 44 host'
  getenforce 2>/dev/null | grep -qx 'Enforcing' && pass 'SELinux enforcing' || fail 'SELinux enforcing'
  [[ "$(stat -fc '%T' /sys/fs/cgroup 2>/dev/null || true)" == cgroup2fs ]] \
    && pass 'cgroup v2' || fail 'cgroup v2'
  systemctl is-active --quiet firewalld && pass 'firewalld active' || fail 'firewalld active'
  podman_version=$(podman version --format '{{.Client.Version}}' 2>/dev/null || true)
  if fedora_server_version_at_least "$podman_version" "$HERMES_SERVER_MIN_PODMAN"; then
    pass "Podman $podman_version"
  else
    fail "Podman $HERMES_SERVER_MIN_PODMAN or newer"
  fi
  lsblk -o FSTYPE 2>/dev/null | grep -q 'crypto_LUKS' && pass 'LUKS-backed storage' \
    || fail 'LUKS-backed storage'
  mokutil --sb-state 2>/dev/null | grep -qi 'secureboot enabled' && pass 'Secure Boot enabled' \
    || fail 'Secure Boot enabled'
  [[ -x /usr/lib/systemd/system-generators/podman-system-generator ]] \
    && pass 'Podman Quadlet generator' || fail 'Podman Quadlet generator'
}

check_identity() {
  local home mode groups
  id hermes >/dev/null 2>&1 || {
    fail 'hermes identity exists'
    return
  }
  pass 'hermes identity exists'
  passwd -S hermes 2>/dev/null | grep -qE '^hermes L ' && pass 'hermes password locked' \
    || fail 'hermes password locked'
  home=$(getent passwd hermes | cut -d: -f6)
  [[ "$home" == /home/hermes ]] && pass 'hermes managed home path' || fail 'hermes managed home path'
  mode=$(stat -c '%a' "$home" 2>/dev/null || true)
  [[ "$mode" == 700 ]] && pass 'hermes home mode 0700' || fail 'hermes home mode 0700'
  [[ ! -e "$home/.ssh/authorized_keys" && ! -L "$home/.ssh/authorized_keys" ]] \
    && pass 'hermes has no SSH authorized key' \
    || fail 'hermes has no SSH authorized key'
  groups=$(id -nG hermes 2>/dev/null || true)
  for group in wheel sudo adm systemd-journal; do
    [[ " $groups " != *" $group "* ]] || fail "hermes is not in privileged group $group"
  done
  grep -q '^hermes:' /etc/subuid && pass 'hermes subordinate uid range' \
    || fail 'hermes subordinate uid range'
  grep -q '^hermes:' /etc/subgid && pass 'hermes subordinate gid range' \
    || fail 'hermes subordinate gid range'
  [[ -e /var/lib/systemd/linger/hermes ]] && pass 'hermes linger enabled' \
    || fail 'hermes linger enabled'
  [[ -d /home/hermes/data && ! -L /home/hermes/data ]] \
    && pass 'Hermes data directory exists' || fail 'Hermes data directory exists'
  [[ "$(stat -c '%a' /home/hermes/data 2>/dev/null || true)" == 700 ]] \
    && pass 'Hermes data directory mode 0700' || fail 'Hermes data directory mode 0700'
}

check_root_file() {
  local path=$1 expected_mode=$2 label=$3
  [[ -f "$path" && ! -L "$path" ]] \
    && [[ "$(stat -c '%U:%G %a' "$path" 2>/dev/null || true)" == "root:root $expected_mode" ]] \
    && pass "$label" || fail "$label"
}

check_host_files() {
  local uid unit devices mount_count
  uid=$(id -u hermes 2>/dev/null || true)
  unit="/etc/containers/systemd/users/$uid/hermes.container"
  check_root_file "$unit" 644 'root-owned Quadlet'
  check_root_file /etc/systemd/user/hermes.service.d/60-hermes-runtime.conf 644 \
    'root-owned Type=exec drop-in'
  check_root_file /etc/systemd/user/hermes.service.d/70-hermes-volume-label.conf 644 \
    'root-owned volume-label drop-in'
  check_root_file /usr/local/libexec/hermes-acceptance 755 'root-owned acceptance helper'
  check_root_file /usr/local/libexec/hermes-root-acceptance 755 'root-owned root acceptance helper'
  grep -Fxq "Image=$EXPECTED_IMAGE" "$unit" 2>/dev/null \
    && pass 'digest-pinned Quadlet' || fail 'digest-pinned Quadlet'
  grep -Fxq 'Pull=never' "$unit" 2>/dev/null && pass 'Pull=never' || fail 'Pull=never'
  grep -Fxq 'Exec=gateway run' "$unit" 2>/dev/null && pass 'gateway command' || fail 'gateway command'
  grep -Fxq 'AddCapability=CHOWN SETUID SETGID DAC_OVERRIDE FOWNER' "$unit" 2>/dev/null \
    && pass 'exact capability envelope' || fail 'exact capability envelope'
  grep -Fxq 'NoNewPrivileges=true' "$unit" 2>/dev/null && pass 'no-new-privileges' || fail 'no-new-privileges'
  grep -Fxq 'ReadOnly=true' "$unit" 2>/dev/null && pass 'read-only root' || fail 'read-only root'
  grep -Fxq 'PidsLimit=512' "$unit" 2>/dev/null && pass 'container PID limit' || fail 'container PID limit'
  grep -Fxq 'MemoryMax=4G' "$unit" 2>/dev/null && pass 'memory limit' || fail 'memory limit'
  grep -Fxq 'CPUQuota=200%' "$unit" 2>/dev/null && pass 'CPU quota' || fail 'CPU quota'
  grep -Fxq 'TasksMax=512' "$unit" 2>/dev/null && pass 'systemd task limit' || fail 'systemd task limit'
  grep -Fxq 'UMask=0077' "$unit" 2>/dev/null && pass 'private service umask' || fail 'private service umask'
  grep -Fq 'Volume=%h/data:/opt/data:z' "$unit" 2>/dev/null && pass 'shared-label data mount' \
    || fail 'shared-label data mount'
  ! grep -Eq '^PublishPort=' "$unit" 2>/dev/null && pass 'no published ports' || fail 'no published ports'
  ! grep -Eq '^EnvironmentFile=' "$unit" 2>/dev/null && pass 'no host environment file' \
    || fail 'no host environment file'
  [[ ! -e /home/hermes/.config/systemd/user/hermes.service.d/reset-network-dep.conf ]] \
    && pass 'no user-writable service override' || fail 'no user-writable service override'
  ! grep -Eq '^Device=' "$unit" 2>/dev/null && pass 'no device mappings' || fail 'no device mappings'
  devices=$(user_exec podman inspect hermes --format '{{json .HostConfig.Devices}}' 2>/dev/null || true)
  [[ "$devices" == null || "$devices" == '[]' ]] && pass 'no runtime devices' || fail 'no runtime devices'
  mount_count=$(user_exec podman inspect hermes --format '{{len .Mounts}}' 2>/dev/null || true)
  [[ "$mount_count" == 1 ]] && pass 'single persistent data mount' || fail 'single persistent data mount'
}

check_service() {
  local uid service_state health inspect_output inspect_prefix cap_eff listeners mounts env_values
  uid=$(id -u hermes 2>/dev/null || true)
  service_state=$(user_exec env XDG_RUNTIME_DIR="/run/user/$uid" systemctl --user is-active hermes.service 2>/dev/null || true)
  [[ "$service_state" == active ]] && pass 'Hermes systemd service active' || fail 'Hermes systemd service active'
  health=$(user_exec podman inspect hermes --format '{{.State.Health.Status}}' 2>/dev/null || true)
  [[ "$health" == healthy ]] && pass 'Hermes health check healthy' || fail 'Hermes health check healthy'
  inspect_output=$(user_exec podman inspect hermes --format '{{.ImageName}}|{{json .Config.Cmd}}|{{.HostConfig.ReadonlyRootfs}}|{{.HostConfig.Privileged}}|{{json .HostConfig.SecurityOpt}}|{{json .NetworkSettings.Ports}}|{{.HostConfig.PidsLimit}}|{{.HostConfig.LogConfig.Type}}' 2>/dev/null || true)
  inspect_prefix="$EXPECTED_IMAGE|[\"gateway\",\"run\"]|true|false|"
  [[ "$inspect_output" == "$inspect_prefix"* ]] \
    && pass 'runtime image, command, and rootfs boundary' || fail 'runtime image, command, and rootfs boundary'
  [[ "$inspect_output" == *'null|512|journald' || "$inspect_output" == *'{}|512|journald' ]] \
    && pass 'runtime ports, PID limit, and journald' || fail 'runtime ports, PID limit, and journald'
  cap_eff=$(user_exec podman exec hermes awk -F: '/^CapEff:/ {gsub(/[[:space:]]/, "", $2); print $2}' /proc/1/status 2>/dev/null || true)
  [[ "$cap_eff" == "$EXPECTED_CAP_MASK" ]] && pass 'effective capabilities 0xcb' \
    || fail 'effective capabilities 0xcb'
  user_exec podman exec hermes grep -q '^NoNewPrivs:[[:space:]]*1$' /proc/1/status 2>/dev/null \
    && pass 'NoNewPrivs runtime bit' || fail 'NoNewPrivs runtime bit'
  user_exec podman exec hermes sh -c 'test ! -w /etc && test ! -e /run/podman/podman.sock && test ! -e /var/run/docker.sock' \
    && pass 'read-only etc and no runtime sockets' || fail 'read-only etc and no runtime sockets'
  mounts=$(user_exec podman inspect hermes --format '{{range .Mounts}}{{.Destination}}={{.RW}} {{end}}' 2>/dev/null || true)
  [[ "$mounts" == *'/opt/data=true'* && "$mounts" != *'/home='* ]] \
    && pass 'restricted data mount' || fail 'restricted data mount'
  user_exec podman exec hermes sh -c \
    'test "$HERMES_HOME" = /opt/data && test "$HERMES_WRITE_SAFE_ROOT" = /opt/data' \
    && pass 'Hermes write boundary is /opt/data' || fail 'Hermes write boundary is /opt/data'
  env_values=$(user_exec podman inspect hermes --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null || true)
  ! grep -Eq '^(API_SERVER_KEY|.*TOKEN|.*PASSWORD|.*SECRET)=' <<<"$env_values" \
    && pass 'runtime environment has no credential injection' \
    || fail 'runtime environment has no credential injection'
  listeners=$(user_exec podman exec hermes python3 -c 'import pathlib; print(sum(1 for line in pathlib.Path("/proc/net/tcp").read_text().splitlines()[1:] if line.split()[3] == "0A" and not line.split()[1].startswith("0100007F:")))' 2>/dev/null || true)
  [[ "$listeners" == 0 ]] && pass 'no non-loopback container listener' || fail 'no non-loopback container listener'
}

check_policy() {
  local policy
  policy=$(
    user_exec podman exec -i --user 10000:10000 hermes python3 - <<'PY' 2>/dev/null || true
import pathlib
import yaml

data = yaml.safe_load(pathlib.Path('/opt/data/config.yaml').read_text(encoding='utf-8')) or {}
checks = {
    'approvals_mode': data.get('approvals', {}).get('mode'),
    'cron_mode': data.get('approvals', {}).get('cron_mode'),
    'single_query_mode': data.get('approvals', {}).get('single_query_mode'),
    'hard_stop_enabled': data.get('tool_loop_guardrails', {}).get('hard_stop_enabled'),
    'tirith_fail_open': data.get('security', {}).get('tirith_fail_open'),
    'allow_private_urls': data.get('security', {}).get('allow_private_urls'),
    'allow_lazy_installs': data.get('security', {}).get('allow_lazy_installs'),
    'hooks_auto_accept': data.get('hooks_auto_accept'),
    'mcp_servers': data.get('mcp_servers'),
    'hooks': data.get('hooks'),
    'plugins_enabled': data.get('plugins', {}).get('enabled'),
    'plugins_disabled': data.get('plugins', {}).get('disabled'),
    'skills_external_dirs': data.get('skills', {}).get('external_dirs'),
    'skills_trusted_project_dirs': data.get('skills', {}).get('trusted_project_dirs'),
    'skills_project_discovery': data.get('skills', {}).get('project_discovery'),
    'memory_provider': data.get('memory', {}).get('provider'),
    'web_keyless_fallback': data.get('web', {}).get('keyless_fallback'),
    'web_keyless_rescue': data.get('web', {}).get('keyless_rescue'),
    'cli_toolset': data.get('platform_toolsets', {}).get('cli'),
}
for key, value in checks.items():
    print(f'{key}={value}')
PY
  )
  grep -Fxq 'approvals_mode=manual' <<<"$policy" && pass 'manual approvals' || fail 'manual approvals'
  grep -Fxq 'cron_mode=deny' <<<"$policy" && pass 'cron scheduling denied' || fail 'cron scheduling denied'
  grep -Fxq 'single_query_mode=deny' <<<"$policy" && pass 'one-shot approval denied' || fail 'one-shot approval denied'
  grep -Fxq 'hard_stop_enabled=True' <<<"$policy" && pass 'tool-loop hard stops' || fail 'tool-loop hard stops'
  grep -Fxq 'tirith_fail_open=False' <<<"$policy" && pass 'Tirith fail-closed' || fail 'Tirith fail-closed'
  grep -Fxq 'allow_private_urls=False' <<<"$policy" && pass 'private URLs denied' || fail 'private URLs denied'
  grep -Fxq 'allow_lazy_installs=False' <<<"$policy" && pass 'lazy installs denied' || fail 'lazy installs denied'
  grep -Fxq 'hooks_auto_accept=False' <<<"$policy" && pass 'hook auto-accept disabled' || fail 'hook auto-accept disabled'
  grep -Fxq 'mcp_servers={}' <<<"$policy" && pass 'MCP inventory empty' || fail 'MCP inventory empty'
  grep -Fxq 'hooks={}' <<<"$policy" && pass 'hook inventory empty' || fail 'hook inventory empty'
  grep -Fxq 'plugins_enabled=[]' <<<"$policy" && pass 'plugin enablement empty' || fail 'plugin enablement empty'
  grep -Fxq 'plugins_disabled=[]' <<<"$policy" && pass 'plugin disablement empty' || fail 'plugin disablement empty'
  grep -Fxq 'skills_external_dirs=[]' <<<"$policy" && pass 'external skills empty' || fail 'external skills empty'
  grep -Fxq 'skills_trusted_project_dirs=[]' <<<"$policy" \
    && pass 'trusted project skill dirs empty' || fail 'trusted project skill dirs empty'
  grep -Fxq 'skills_project_discovery=False' <<<"$policy" \
    && pass 'project skill discovery disabled' || fail 'project skill discovery disabled'
  grep -Fxq 'memory_provider=' <<<"$policy" && pass 'external memory provider empty' \
    || fail 'external memory provider empty'
  grep -Fxq 'web_keyless_fallback=False' <<<"$policy" && pass 'keyless web fallback disabled' || fail 'keyless web fallback disabled'
  grep -Fxq 'web_keyless_rescue=False' <<<"$policy" && pass 'keyless web rescue disabled' || fail 'keyless web rescue disabled'
  grep -Fxq "cli_toolset=['hermes-cli']" <<<"$policy" && pass 'CLI toolset locked' || fail 'CLI toolset locked'
}

check_provider() {
  local provider_model
  valid_provider "$EXPECTED_PROVIDER" || {
    fail 'selected provider is supported'
    return
  }
  valid_model "$EXPECTED_MODEL" || {
    fail 'selected model is valid'
    return
  }
  local auth_output
  auth_output=$(user_exec podman exec --user 10000:10000 hermes hermes auth status "$EXPECTED_PROVIDER" 2>&1 || true)
  provider_auth_status_logged_in "$EXPECTED_PROVIDER" "$auth_output" \
    && pass "${EXPECTED_PROVIDER} auth status is logged in" \
    || fail "${EXPECTED_PROVIDER} auth status is logged in"
  provider_model=$(
    user_exec podman exec -i --user 10000:10000 hermes python3 - <<'PY' 2>/dev/null || true
import pathlib
import yaml

data = yaml.safe_load(pathlib.Path('/opt/data/config.yaml').read_text(encoding='utf-8')) or {}
section = data.get('model') if isinstance(data.get('model'), dict) else {}
provider = section.get('provider') or data.get('provider')
model = section.get('default') or section.get('model') or data.get('default_model') or data.get('model_name')
print(f'provider={provider}')
print(f'model={model}')
PY
  )
  grep -Fxq "provider=$EXPECTED_PROVIDER" <<<"$provider_model" \
    && pass "provider $EXPECTED_PROVIDER" || fail "provider $EXPECTED_PROVIDER"
  grep -Fxq "model=$EXPECTED_MODEL" <<<"$provider_model" && pass 'selected model' || fail 'selected model'
}

valid_provider() {
  [[ "$1" == openai-codex || "$1" == openai-api || "$1" == nous ]]
}

valid_model() {
  [[ "$1" =~ ^[A-Za-z0-9._:/-]+$ ]]
}

classify_inference_stderr() {
  local stderr_file=$1

  if [[ ! -s "$stderr_file" ]]; then
    printf 'none\n'
  elif grep -Eqi 'billing|credits?|quota|rate[ _-]?limit|subscription|account balance|usage limit|exhausted' "$stderr_file"; then
    printf 'billing-or-quota\n'
  elif grep -Eqi 'unauthori[sz]ed|forbidden|authentication|credentials?|oauth|access token|refresh token|log[ -]?in|sign[ -]?in|(^|[^0-9])(401|403)([^0-9]|$)' "$stderr_file"; then
    printf 'authentication\n'
  elif grep -Eqi 'model[^[:cntrl:]]*(not found|does not exist|unsupported|unavailable|not available|access|requires)|invalid[ _-]*model|unknown[ _-]*model' "$stderr_file"; then
    printf 'model-access\n'
  elif grep -Eqi 'timed out|timeout' "$stderr_file"; then
    printf 'timeout\n'
  elif grep -Eqi 'name or service not known|temporary failure in name resolution|could not resolve|connection (refused|reset)|network is unreachable|dns' "$stderr_file"; then
    printf 'network\n'
  elif grep -Eqi 'config(uration)?|yaml|migration|version' "$stderr_file"; then
    printf 'configuration\n'
  else
    printf 'other\n'
  fi
}

run_inference_probe() (
  local probe_dir stdout_file stderr_file response stdout_class stderr_class
  local stdout_bytes stderr_bytes inference_rc=0

  probe_dir=$(mktemp -d)
  stdout_file="$probe_dir/stdout"
  stderr_file="$probe_dir/stderr"
  : >"$stdout_file"
  : >"$stderr_file"
  chmod 0600 "$stdout_file" "$stderr_file"
  trap 'rm -f -- "$stdout_file" "$stderr_file"; rmdir -- "$probe_dir"' EXIT

  if user_exec podman exec -i --user 10000:10000 hermes hermes \
    --safe-mode \
    --provider "$EXPECTED_PROVIDER" \
    --model "$EXPECTED_MODEL" \
    --toolsets context_engine \
    -z 'Return exactly HERMES_OK. The complete response must be the nine ASCII characters HERMES_OK and nothing else.' \
    >"$stdout_file" 2>"$stderr_file"; then
    inference_rc=0
  else
    inference_rc=$?
  fi

  response=$(<"$stdout_file")
  if [[ "$response" == HERMES_OK ]]; then
    stdout_class=exact
  elif [[ -z "$response" ]]; then
    stdout_class=empty
  elif [[ "$response" == *HERMES_OK* ]]; then
    stdout_class=contains-expected
  else
    stdout_class=unexpected
  fi
  stderr_class=$(classify_inference_stderr "$stderr_file")
  stdout_bytes=$(stat -c '%s' "$stdout_file")
  stderr_bytes=$(stat -c '%s' "$stderr_file")

  if ((inference_rc == 0)) && [[ "$stdout_class" == exact ]]; then
    return 0
  fi

  printf 'INFERENCE_FAILED exit_code=%d stdout=%s stdout_bytes=%s stderr=%s stderr_bytes=%s\n' \
    "$inference_rc" "$stdout_class" "$stdout_bytes" "$stderr_class" "$stderr_bytes" >&2
  return 1
)

check_inference() {
  if run_inference_probe; then
    pass 'harmless inference returned HERMES_OK'
  else
    fail 'harmless inference returned HERMES_OK'
  fi
}

while [[ $# -gt 0 ]]; do
  option=$1
  shift
  case "$option" in
    --provider)
      [[ $# -gt 0 ]] || {
        printf 'ERROR: --provider requires a value\n' >&2
        exit 64
      }
      EXPECTED_PROVIDER=$1
      shift
      ;;
    --model)
      [[ $# -gt 0 ]] || {
        printf 'ERROR: --model requires a value\n' >&2
        exit 64
      }
      EXPECTED_MODEL=$1
      shift
      ;;
    --provider-required) PROVIDER_REQUIRED=true ;;
    --inference-required) INFERENCE_REQUIRED=true ;;
    --credential-free)
      PROVIDER_REQUIRED=false
      INFERENCE_REQUIRED=false
      ;;
    *)
      printf 'ERROR: unknown acceptance option: %s\n' "$option" >&2
      exit 64
      ;;
  esac
done

if $PROVIDER_REQUIRED; then
  [[ -n "$EXPECTED_PROVIDER" ]] || EXPECTED_PROVIDER=$(sed -n '1p' "$STATE_DIR/provider" 2>/dev/null || true)
  [[ -n "$EXPECTED_MODEL" ]] || EXPECTED_MODEL=$(sed -n '1p' "$STATE_DIR/model" 2>/dev/null || true)
  [[ -n "$EXPECTED_PROVIDER" ]] || EXPECTED_PROVIDER=nous
  [[ -n "$EXPECTED_MODEL" ]] || EXPECTED_MODEL=anthropic/claude-sonnet-4.6
fi

[[ -r "$STATE_DIR/site.conf" ]] && pass 'site configuration is present' || fail 'site configuration is present'
check_host
check_identity
check_host_files
check_service
check_policy
if $PROVIDER_REQUIRED; then
  check_provider
fi
if $INFERENCE_REQUIRED; then
  check_inference
fi

if ((FAILURES == 0)); then
  printf 'ACCEPTANCE_OK\n'
else
  printf 'ACCEPTANCE_FAILED count=%d\n' "$FAILURES" >&2
  exit 1
fi
