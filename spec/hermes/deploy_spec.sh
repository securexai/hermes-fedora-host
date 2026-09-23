# shellcheck shell=bash
#
# Public-seam examples for the Hermes workstation deployment controller.
# These examples exercise the command-line contract only; remote behavior is
# covered through disposable fixtures and the acceptance script.

run_help_without_ssh() {
  local marker=$1 output
  output=$(HERMES_SPEC_SSH_FIXTURE=1 HERMES_SPEC_SSH_MARKER="$marker" HERMES_SPEC_SSH_SCRATCH="$SPEC_SSH_SCRATCH" \
    PATH="$PROJECT_ROOT/spec/hermes/fixtures:$PATH" "$PROJECT_ROOT/hermes-deploy.sh" --help) || return 1
  [[ ! -e "$marker" ]] || return 1
  printf '%s\n' "$output"
}

run_invalid_target_without_ssh() {
  local marker=$1 output rc
  set +e
  output=$(HERMES_SPEC_SSH_FIXTURE=1 HERMES_SPEC_SSH_MARKER="$marker" HERMES_SPEC_SSH_SCRATCH="$SPEC_SSH_SCRATCH" \
    PATH="$PROJECT_ROOT/spec/hermes/fixtures:$PATH" "$PROJECT_ROOT/hermes-deploy.sh" check --target malformed-target 2>&1)
  rc=$?
  set -e
  [[ "$rc" -eq 64 && ! -e "$marker" ]] || return 1
  printf '%s\n' "$output"
}

# Per-example scratch directory and marker. `Before`/`After` in the fixture
# Describe call these, so a marker can never survive a failed example or leak
# into a concurrent run.
spec_ssh_fixture_setup() {
  SPEC_SSH_SCRATCH=$(mktemp -d "${TMPDIR:-/tmp}/hermes-spec-ssh.XXXXXX")
  SPEC_SSH_MARKER="$SPEC_SSH_SCRATCH/ssh.called"
  export SPEC_SSH_SCRATCH SPEC_SSH_MARKER
}

spec_ssh_fixture_teardown() {
  [[ -n "${SPEC_SSH_SCRATCH:-}" ]] && rm -rf -- "$SPEC_SSH_SCRATCH"
  SPEC_SSH_SCRATCH=''
  SPEC_SSH_MARKER=''
}

# Positive control: invoking the fixture directly must fail closed with 255 and
# record the call in this example's marker.
spec_ssh_positive_control() {
  local rc=0
  HERMES_SPEC_SSH_FIXTURE=1 HERMES_SPEC_SSH_MARKER="$SPEC_SSH_MARKER" HERMES_SPEC_SSH_SCRATCH="$SPEC_SSH_SCRATCH" \
    "$PROJECT_ROOT/spec/hermes/fixtures/ssh" -o BatchMode=yes fixture@example.invalid true 2>&1 || rc=$?
  [[ -f "$SPEC_SSH_MARKER" ]] || { printf 'positive control marker missing\n'; return 1; }
  grep -qF 'FIXTURE_SSH_CALLED' "$SPEC_SSH_MARKER" || return 1
  return "$rc"
}

# Negative control: without the harness opt-in the fixture must refuse instead of
# behaving like a usable `ssh`.
spec_ssh_identity_refusal() {
  local rc=0
  HERMES_SPEC_SSH_MARKER="$SPEC_SSH_MARKER" HERMES_SPEC_SSH_SCRATCH="$SPEC_SSH_SCRATCH" \
    "$PROJECT_ROOT/spec/hermes/fixtures/ssh" -o BatchMode=yes fixture@example.invalid true 2>&1 || rc=$?
  [[ ! -e "$SPEC_SSH_MARKER" ]] || return 1
  return "$rc"
}

run_help_without_state() {
  local state_root=$1 output
  output=$(XDG_STATE_HOME="$state_root" "$PROJECT_ROOT/hermes-deploy.sh" --help) || return 1
  [[ ! -e "$state_root" ]] || return 1
  printf '%s\n' "$output"
}

run_fixture_check_without_state() {
  local state_root=$1 output
  output=$(HERMES_DEPLOY_TRANSPORT=fixture XDG_STATE_HOME="$state_root" "$PROJECT_ROOT/hermes-deploy.sh" check --target lab@fixture) || return 1
  [[ ! -e "$state_root/hermes-deploy" ]] || return 1
  printf '%s\n' "$output"
}

run_fixture_status_without_state() {
  local state_root=$1 output
  output=$(HERMES_DEPLOY_TRANSPORT=fixture XDG_STATE_HOME="$state_root" "$PROJECT_ROOT/hermes-deploy.sh" status --target lab@fixture) || return 1
  [[ ! -e "$state_root/hermes-deploy" ]] || return 1
  printf '%s\n' "$output"
}

run_fixture_deploy_rejected() {
  local state_root=$1 output rc
  set +e
  output=$(HERMES_DEPLOY_TRANSPORT=fixture XDG_STATE_HOME="$state_root" "$PROJECT_ROOT/hermes-deploy.sh" deploy --target lab@fixture 2>&1)
  rc=$?
  set -e
  [[ "$rc" -eq 78 && ! -e "$state_root/hermes-deploy" ]] || return 1
  printf '%s\n' "$output"
}

run_provider_resolution() {
  local state_dir=$1 provider=$2 model=$3
  SCRIPT_DIR="$PROJECT_ROOT" TEST_STATE_DIR="$state_dir" TEST_PROVIDER="$provider" TEST_MODEL="$model" \
    bash -c '
      set -o errexit
      set -o nounset
      set -o pipefail
      source "$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
      COMMAND=deploy
      STATE_DIR="$TEST_STATE_DIR"
      PROVIDER="$TEST_PROVIDER"
      MODEL="$TEST_MODEL"
      resolve_provider_selection
      printf "provider=%s\\nmodel=%s\\n" "$PROVIDER" "$MODEL"
    ' </dev/null
}

run_provider_resolution_without_selection() {
  local state_dir=$1 output rc
  set +e
  output=$(run_provider_resolution "$state_dir" '' '' 2>&1)
  rc=$?
  set -e
  [[ "$rc" -eq 75 ]] || return 1
  printf '%s\n' "$output"
}

write_accepted_provider_state() {
  local state_dir=$1 provider=$2 model=$3
  mkdir -p "$state_dir"
  printf '%s\n' "$provider" >"$state_dir/provider"
  printf '%s\n' "$model" >"$state_dir/model"
  printf '%s\n' 1 >"$state_dir/stage-inference-acceptance"
}

run_accepted_provider_resolution() {
  local state_dir=$1
  write_accepted_provider_state "$state_dir" openai-api gpt-5.6-luna
  run_provider_resolution "$state_dir" '' ''
}

run_model_config_writer() {
  local config_path=$1 output api_key_field=api_key
  mkdir -p -- "$(dirname -- "$config_path")"
  printf '%s\n' \
    'model:' \
    '  provider: openai-codex' \
    '  default: anthropic/claude-opus-4.6' \
    '  model: anthropic/claude-opus-4.6' \
    "  ${api_key_field}: stale-endpoint-override" \
    'provider: openai-codex' \
    'default_model: anthropic/claude-opus-4.6' >"$config_path"
  HERMES_CONFIG_PATH="$config_path" HERMES_PROVIDER=openai-codex HERMES_MODEL=gpt-5.6-luna \
    python3 "$PROJECT_ROOT/scripts/hermes/set-model.py" >/dev/null || return 1
  output=$(
    python3 - "$config_path" <<'PY'
import pathlib
import sys

import yaml

data = yaml.safe_load(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')) or {}
model = data.get('model') or {}
for key in ('provider', 'default', 'model'):
    print(f'model.{key}={model.get(key)}')
print(f'default_model={data.get("default_model")}')
print(f'api_key_present={"api_key" in model}')
PY
  )
  printf '%s\n' "$output"
}

run_runtime_resume_sync() {
  SCRIPT_DIR="$PROJECT_ROOT" TEST_STATE_DIR="$1" bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    source "$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
    STATE_DIR="$TEST_STATE_DIR"
    UPLOAD_COUNT=0
    stage_is_complete() { return 0; }
    upload_file() {
      UPLOAD_COUNT=$((UPLOAD_COUNT + 1))
      UPLOADED_PATH="/tmp/hermes-deploy.Sync$UPLOAD_COUNT"
    }
    root_action() { printf "action=%s\\n" "$1"; }
    cleanup_remote_temps() { :; }
    run_runtime_stage
  '
}

run_hermes_reboot_reconnect_attempts() {
  local certification_mode=$1 target=$2
  SCRIPT_DIR="$PROJECT_ROOT" TEST_CERTIFICATION_MODE="$certification_mode" TEST_TARGET="$target" bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    source "$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
    HERMES_CERTIFICATION_MODE="$TEST_CERTIFICATION_MODE"
    TARGET="$TEST_TARGET"
    hermes_reboot_reconnect_attempts
  '
}

run_reconnect_probe_options() {
  SCRIPT_DIR="$PROJECT_ROOT" bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    source "$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
    TARGET=lab@172.16.99.12
    SSH_OPTIONS=(-o ConnectTimeout=15)
    is_fixture() { return 1; }
    ssh() {
      local argument effective_timeout=unset
      for argument in "$@"; do
        case "$argument" in
          ConnectTimeout=*) effective_timeout=${argument#*=} ;;
        esac
      done
      printf "effective-connect-timeout=%s\n" "$effective_timeout"
    }
    remote_reconnect_probe true
  '
}

run_remote_preflight_failure_contract() {
  SCRIPT_DIR="$PROJECT_ROOT" bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    source "$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
    is_fixture() { return 1; }
    check_repo_artifacts() { :; }
    root_helper_present() { return 1; }
    upload_count=0
    upload_file() {
      upload_count=$((upload_count + 1))
      UPLOADED_PATH="/tmp/hermes-deploy.Mock$upload_count"
    }
    remote_tty() {
      printf "remote-preflight-failed\\n"
      return 7
    }
    remove_remote_temp() { printf "removed=%s\\n" "$1"; }
    run_rc=0
    run_check || run_rc=$?
    printf "run-check-rc=%s\\n" "$run_rc"
    root_helper_present() { return 0; }
    root_helper_matches() { return 0; }
    root_action() {
      printf "root-helper-preflight-failed\\n"
      return 8
    }
    root_run_rc=0
    run_check || root_run_rc=$?
    printf "root-run-check-rc=%s\\n" "$root_run_rc"
  '
}

run_remote_preflight_four_argument_contract() {
  local work_dir=$1 host_module output rc
  mkdir -p "$work_dir"
  host_module="$work_dir/host-module.sh"
  cat >"$host_module" <<'EOF'
check_root_access() { :; }
check_foundation() {
  printf 'allow-update=%s\n' "$ALLOW_UPDATE"
  [[ "$ALLOW_UPDATE" == 1 ]] || fail 'four-argument update mode'
}
check_network() { :; }
check_console_recovery() { :; }
check_identity_state() { :; }
EOF
  chmod 0600 "$host_module"
  set +e
  output=$("$PROJECT_ROOT/scripts/hermes/remote-preflight.sh" \
    192.168.99.0/24 eno1 1 "$host_module" 2>&1)
  rc=$?
  set -e
  printf 'preflight-rc=%s\n%s\n' "$rc" "$output"
}

run_root_helper_bootstrap_sudo_contract() {
  SCRIPT_DIR="$PROJECT_ROOT" bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    source "$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
    TARGET_USER=aicowork
    upload_count=0
    upload_file() {
      upload_count=$((upload_count + 1))
      UPLOADED_PATH="/tmp/hermes-deploy.Mock$upload_count"
    }
    sha256sum() { printf "%064d  %s\n" 0 "$1"; }
    remote_no_stdin() { :; }
    remote_tty() {
      printf "argument-1=%s\n" "${1-}"
      printf "argument-2=%s\n" "${2-}"
      printf "argument-3=%s\n" "${3-}"
      printf "argument-count=%s\n" "$#"
    }
    root_helper_present() { return 0; }
    bootstrap_root_helper
  '
}

run_concurrent_certifier_rejection() {
  local work_dir=$1 state_root lock_root holder output rc restore_nullglob=0
  local -a run_dirs
  state_root="$work_dir/state"
  lock_root="$state_root/hermes-certification"
  mkdir -p "$lock_root"
  : >"$work_dir/iso"
  : >"$work_dir/checksum"
  : >"$work_dir/keyring"
  : >"$work_dir/identity"
  (
    exec 9>"$lock_root/certification.lock"
    flock 9
    : >"$work_dir/lock-ready"
    while [[ ! -e "$work_dir/lock-release" ]]; do
      sleep 0.05
    done
  ) &
  holder=$!
  while [[ ! -e "$work_dir/lock-ready" ]]; do
    sleep 0.05
  done
  set +e
  output=$(XDG_STATE_HOME="$state_root" "$PROJECT_ROOT/hermes-certify-vm.sh" \
    --iso "$work_dir/iso" \
    --checksum "$work_dir/checksum" \
    --fedora-keyring "$work_dir/keyring" \
    --identity-file "$work_dir/identity" \
    --provider openai-codex \
    --model gpt-5.6-luna 2>&1)
  rc=$?
  set -e
  : >"$work_dir/lock-release"
  wait "$holder"
  [[ "$rc" -eq 75 ]] || return 1
  if ! shopt -q nullglob; then
    shopt -s nullglob
    restore_nullglob=1
  fi
  run_dirs=("$lock_root"/run-*)
  if ((restore_nullglob == 1)); then
    shopt -u nullglob
  fi
  ((${#run_dirs[@]} == 0)) || return 1
  printf '%s\n' "$output"
}

run_certifier_interrupt_cleanup() {
  local work_dir=$1 marker child_rc
  mkdir -p "$work_dir"
  marker="$work_dir/cleanup-events"
  set +e
  SCRIPT_DIR="$PROJECT_ROOT" TEST_RUN_DIR="$work_dir" TEST_MARKER="$marker" bash -c '
    set -o nounset
    VM_CREATED=true
    RUN_DIR="$TEST_RUN_DIR"
    VM_CREATOR=/bin/true
    SSH_PUBKEY=""
    stop_unlock_monitor() { printf "unlock-monitor-stopped\n" >>"$TEST_MARKER"; }
    capture_vm_diagnostics() { printf "diagnostics-captured\n" >>"$TEST_MARKER"; }
    cleanup_after_failure() {
      printf "failure-cleanup-used\n" >>"$TEST_MARKER"
      VM_CREATED=false
    }
    source <(sed -n "/^cleanup() {/,/^trap .*TERM/p" "$SCRIPT_DIR/hermes-certify-vm.sh")
    kill -INT $$
  '
  child_rc=$?
  set -e
  printf 'child_rc=%s\n' "$child_rc"
  [[ -f "$marker" ]] && cat "$marker"
}

run_certifier_verified_failure_cleanup() {
  local work_dir=$1 marker vm_creator
  mkdir -p "$work_dir"
  marker="$work_dir/cleanup-events"
  vm_creator="$work_dir/vm-creator"
  cat >"$vm_creator" <<'EOF'
#!/usr/bin/env bash
printf 'vm-creator %s\n' "$*" >>"$TEST_MARKER"
EOF
  chmod 0700 "$vm_creator"
  SCRIPT_DIR="$PROJECT_ROOT" TEST_RUN_DIR="$work_dir" TEST_MARKER="$marker" \
    TEST_VM_CREATOR="$vm_creator" bash -c '
      set -o errexit
      set -o nounset
      set -o pipefail
      VM_CREATED=true
      RUN_DIR="$TEST_RUN_DIR"
      VM_CREATOR="$TEST_VM_CREATOR"
      VM_NAME=lab-hermes-server
      identity_present=true
      stop_unlock_monitor() { printf "unlock-monitor-stopped\n" >>"$TEST_MARKER"; }
      controller_stage_present() { [[ "$1" == identity ]]; }
      ssh_vm() { $identity_present; }
      revoke_all_providers() { printf "providers-revoked\n" >>"$TEST_MARKER"; }
      purge_fresh_data() {
        printf "fresh-data-purged\n" >>"$TEST_MARKER"
        identity_present=false
      }
      remove_fixture_sudo() { printf "fixture-sudo-removed\n" >>"$TEST_MARKER"; }
      verify_vm_destroyed() {
        printf "destroy-verified\n" >>"$TEST_MARKER"
        grep -Fqx "vm-creator --destroy" "$TEST_MARKER"
      }
      virsh() { printf "unexpected-virsh %s\n" "$*" >>"$TEST_MARKER"; }
      source <(sed -n "/^cleanup_after_failure() {/,/^}/p" "$SCRIPT_DIR/hermes-certify-vm.sh")
      cleanup_after_failure
      printf "vm_created=%s\n" "$VM_CREATED" >>"$TEST_MARKER"
    '
  cat "$marker"
}

run_certification_unlock_evidence_contract() {
  local work_dir=$1 scenario=$2 event_log result
  mkdir -p "$work_dir"
  event_log="$work_dir/unlock-events"
  printf '%s\n' \
    '2026-08-31T02:00:00Z luks-console-attached input-submitted=0' \
    '2026-08-31T02:00:01Z luks-prompt-verified input-submitted=1' \
    '2026-08-31T02:00:02Z monitor-started' \
    '2026-08-31T02:00:03Z console-watch-started attempt=1 vm-state=running' \
    '2026-08-31T02:00:04Z luks-console-attached input-submitted=0' \
    '2026-08-31T02:00:05Z monitor-ready' \
    '2026-08-31T02:00:59Z luks-reboot-observed input-submitted=0' \
    '2026-08-31T02:01:00Z luks-boot-boundary-observed input-submitted=0' \
    '2026-08-31T02:01:01Z luks-prompt-verified input-submitted=1' \
    '2026-08-31T02:01:59Z luks-reboot-observed input-submitted=0' \
    '2026-08-31T02:02:00Z luks-boot-boundary-observed input-submitted=0' \
    '2026-08-31T02:02:01Z luks-prompt-verified input-submitted=1' \
    '2026-08-31T02:02:59Z luks-reboot-observed input-submitted=0' \
    '2026-08-31T02:03:00Z luks-boot-boundary-observed input-submitted=0' \
    '2026-08-31T02:03:01Z luks-prompt-verified input-submitted=1' \
    >"$event_log"
  if [[ "$scenario" == duplicate ]]; then
    printf '%s\n' \
      '2026-08-31T02:03:01Z luks-prompt-verified input-submitted=1' \
      >>"$event_log"
  elif [[ "$scenario" == missing-reboot ]]; then
    sed -i '/02:01:59Z luks-reboot-observed/d' "$event_log"
  fi
  # shellcheck source=../../scripts/hermes/certification-evidence.sh
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/scripts/hermes/certification-evidence.sh"
  if certification_unlock_evidence_is_valid "$event_log"; then
    result=valid
  else
    result=invalid
  fi
  printf 'evidence=%s\n' "$result"
}

run_remove_fixture_sudo_contract() {
  SCRIPT_DIR="$PROJECT_ROOT" bash -c '
    set -o nounset
    source <(sed -n "/^remove_fixture_sudo() {/,/^}/p" "$SCRIPT_DIR/hermes-certify-vm.sh")
    ssh_vm() {
      printf "ssh_vm"
      printf " <%s>" "$@"
      printf "\n"
      if [[ "$1" == sudo ]]; then
        IFS= read -r fixture_cleanup_script || true
        printf "stdin <%s>\n" "$fixture_cleanup_script"
      fi
    }
    remove_fixture_sudo
  '
}

run_provider_rollback() {
  SCRIPT_DIR="$PROJECT_ROOT" TEST_STATE_DIR="$1" bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    source "$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
    STATE_DIR="$TEST_STATE_DIR"
    root_action() { printf "root_action=%s %s\\n" "$1" "${*:2}"; }
    rollback_provider_switch nous anthropic/claude-sonnet-4.6 openai-codex /tmp/hermes-deploy.Model123
  '
}

run_fresh_purge_state_reset() {
  SCRIPT_DIR="$PROJECT_ROOT" TEST_STATE_DIR="$1" bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    source "$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
    STATE_DIR="$TEST_STATE_DIR"
    TARGET=aicowork@10.0.30.10
    MANAGEMENT_CIDR=192.168.99.0/24
    MANAGEMENT_INTERFACE=eno1
    PURGE_FRESH=true
    TEMP_HELPER_BOOTSTRAPPED=false
    init_state
    state_write stage-closed previous
    state_write stage-inference-acceptance previous
    state_write provider openai-codex
    state_write model gpt-5.6-luna
    state_write promotion-id old-promotion
    state_write promotion-artifact-fingerprint old-fingerprint
    state_write host-machine-id-sha256 old-machine-id
    state_write host-ssh-fingerprint old-host-key
    start_control_master() { :; }
    ensure_root_helper() { TEMP_HELPER_BOOTSTRAPPED=true; }
    cleanup_remote_temps() { :; }
    root_action() {
      case "$1" in
        backup-present) return 0 ;;
        rollback|remove-helper) return 0 ;;
        *) return 1 ;;
      esac
    }
    printf "PURGE-HERMES-FRESH\\n" | rollback_command 2>/dev/null
    for state_file in \
      stage-closed stage-inference-acceptance provider model promotion-id \
      promotion-artifact-fingerprint host-machine-id-sha256 host-ssh-fingerprint; do
      if state_has "$state_file"; then
        printf "stale=%s\\n" "$state_file"
      fi
    done
    printf "target=%s\\n" "$(state_read target)"
    printf "cidr=%s\\n" "$(state_read management-cidr)"
    printf "interface=%s\\n" "$(state_read interface)"
    printf "phase=%s\\n" "$(state_read current-phase)"
    printf "rollback-marker=%s\\n" "$(state_has stage-rollback && printf present || printf absent)"
  '
}

run_standard_rollback_state_marker() {
  SCRIPT_DIR="$PROJECT_ROOT" TEST_STATE_DIR="$1" bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    source "$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
    STATE_DIR="$TEST_STATE_DIR"
    TARGET=aicowork@10.0.30.10
    MANAGEMENT_CIDR=192.168.99.0/24
    MANAGEMENT_INTERFACE=eno1
    PURGE_FRESH=false
    TEMP_HELPER_BOOTSTRAPPED=false
    init_state
    state_write stage-closed previous
    state_write provider openai-codex
    state_write promotion-id existing-promotion
    start_control_master() { :; }
    ensure_root_helper() { TEMP_HELPER_BOOTSTRAPPED=true; }
    cleanup_remote_temps() { :; }
    root_action() {
      case "$1" in
        backup-present|rollback|remove-helper) return 0 ;;
        *) return 1 ;;
      esac
    }
    rollback_command
    printf "phase=%s\\n" "$(state_read current-phase)"
    printf "closed-marker=%s\\n" "$(state_has stage-closed && printf present || printf absent)"
    printf "provider=%s\\n" "$(state_read provider)"
    printf "promotion=%s\\n" "$(state_read promotion-id)"
  '
}

run_revocation_metadata_stream() {
  SCRIPT_DIR="$PROJECT_ROOT" bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    source "$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
    is_fixture() { return 1; }
    remote() { cat; }
    remote_tty() { return 99; }
    root_action revoke-auth provider=openai-codex
  '
}

run_provider_auth_operator_readiness() {
  local unlock_log
  mkdir -p "$1"
  unlock_log="$1/unlock-events"
  printf '%s\n' \
    '2026-08-31T02:00:00Z luks-prompt-verified input-submitted=1' \
    '2026-08-31T02:00:01Z monitor-ready' \
    '2026-08-31T02:00:59Z luks-reboot-observed input-submitted=0' \
    '2026-08-31T02:01:00Z luks-boot-boundary-observed input-submitted=0' \
    '2026-08-31T02:01:01Z luks-prompt-verified input-submitted=1' \
    '2026-08-31T02:01:59Z luks-reboot-observed input-submitted=0' \
    '2026-08-31T02:02:00Z luks-boot-boundary-observed input-submitted=0' \
    '2026-08-31T02:02:01Z luks-prompt-verified input-submitted=1' \
    '2026-08-31T02:02:59Z luks-reboot-observed input-submitted=0' \
    '2026-08-31T02:03:00Z luks-boot-boundary-observed input-submitted=0' \
    '2026-08-31T02:03:01Z luks-prompt-verified input-submitted=1' \
    >"$unlock_log"
  SCRIPT_DIR="$PROJECT_ROOT" TEST_STATE_DIR="$1" \
    HERMES_CERTIFICATION_UNLOCK_LOG="$unlock_log" python3 - <<'PY'
import errno
import os
import pty
import select
import signal
import sys
import time

child_script = r'''
set -o nounset
set -o pipefail
source "$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
HERMES_CERTIFICATION_MODE=1
TARGET=lab@172.16.99.12
PROVIDER=openai-codex
MODEL=gpt-5.6-luna
STATE_DIR="$TEST_STATE_DIR"
existing_provider() { printf '\n'; }
existing_model() { printf '\n'; }
provider_configuration_is_current() { return 1; }
rollback_provider_switch() { :; }
root_action() {
    case "$1" in
        validate-provider-auth) return 1 ;;
        provider-auth)
            printf 'provider-auth-invoked\n'
            return 79
            ;;
        *) return 0 ;;
    esac
}
run_provider_stage
'''

pid, master_fd = pty.fork()
if pid == 0:
    os.execvpe("bash", ["bash", "-c", child_script], os.environ.copy())

captured = bytearray()
status = None


def collect_until(deadline):
    global status
    while time.monotonic() < deadline:
        ready, _, _ = select.select([master_fd], [], [], 0.05)
        if ready:
            try:
                captured.extend(os.read(master_fd, 4096))
            except OSError as exc:
                if exc.errno != errno.EIO:
                    raise
        waited_pid, waited_status = os.waitpid(pid, os.WNOHANG)
        if waited_pid == pid:
            status = waited_status
            return


def stop_child():
    global status
    if status is not None:
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    _, status = os.waitpid(pid, 0)


collect_until(time.monotonic() + 0.4)
if (
    b"not a Bash command" not in captured
    or b"same certification terminal" not in captured
):
    stop_child()
    print("provider-auth-readiness-instructions-ambiguous")
    sys.exit(1)
print("provider-auth-readiness-instructions-clear")
if b"provider-auth-invoked" in captured:
    stop_child()
    print("provider-auth-started-before-operator-ready")
    sys.exit(1)
if status is not None:
    print("provider-stage-exited-before-operator-ready")
    sys.exit(1)

print("provider-auth-waited-for-operator")
os.write(master_fd, b"NOT-YET\n")
collect_until(time.monotonic() + 0.2)
if b"provider-auth-invoked" in captured:
    stop_child()
    print("provider-auth-started-after-invalid-confirmation")
    sys.exit(1)

print("provider-auth-rejected-invalid-confirmation")
os.write(master_fd, b"START-AUTH\n")
collect_until(time.monotonic() + 2.0)
stop_child()
os.close(master_fd)

if b"provider-auth-invoked" not in captured:
    print("provider-auth-did-not-start-after-operator-ready")
    sys.exit(1)

print("provider-auth-started-after-operator-ready")
PY
}

run_provider_auth_invalid_unlock_evidence() {
  local work_dir=$1 event_log output rc
  mkdir -p "$work_dir"
  event_log="$work_dir/unlock-events"
  printf '%s\n' \
    '2026-08-31T02:00:00Z luks-prompt-verified input-submitted=1' \
    '2026-08-31T02:00:01Z monitor-ready' \
    '2026-08-31T02:01:00Z luks-boot-boundary-observed input-submitted=0' \
    '2026-08-31T02:01:01Z luks-prompt-verified input-submitted=1' \
    '2026-08-31T02:01:01Z luks-prompt-verified input-submitted=1' \
    >"$event_log"
  set +e
  output=$(SCRIPT_DIR="$PROJECT_ROOT" TEST_STATE_DIR="$work_dir" \
    HERMES_CERTIFICATION_UNLOCK_LOG="$event_log" bash -c '
      set -o nounset
      set -o pipefail
      source "$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
      HERMES_CERTIFICATION_MODE=1
      TARGET=lab@172.16.99.12
      PROVIDER=openai-codex
      MODEL=gpt-5.6-luna
      STATE_DIR="$TEST_STATE_DIR"
      existing_provider() { printf "\n"; }
      existing_model() { printf "\n"; }
      provider_configuration_is_current() { return 1; }
      root_action() {
        if [[ "$1" == validate-provider-auth ]]; then
          return 1
        fi
        printf "provider-auth-invoked\n"
      }
      run_provider_stage
    ' 2>&1)
  rc=$?
  set -e
  printf 'rc=%s\n%s\n' "$rc" "$output"
}

run_provider_auth_remote_exit_with_open_tty() {
  SCRIPT_DIR="$PROJECT_ROOT" python3 - <<'PY'
import errno
import fcntl
import os
import pty
import select
import signal
import sys
import time

child_script = r'''
set -o nounset
set -o pipefail
source "$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
is_fixture() { return 1; }
WORK_DIR=$(mktemp -d)
remote_tty_from_fifo() {
    local input_fifo=$1 operator_input received_action received_provider separator
    {
        IFS= read -r received_action
        IFS= read -r received_provider
        IFS= read -r separator
    } <"$input_fifo"
    if [[ "$received_action" != provider-auth ||
          "$received_provider" != provider=openai-codex ||
          "$separator" != -- ]]; then
        printf 'provider-auth-test-invalid-protocol\n'
        return 78
    fi
    printf 'provider-auth-test-awaiting-input\n'
    IFS= read -r operator_input <"$input_fifo"
    if [[ "$operator_input" != operator-input ]]; then
        printf 'provider-auth-test-invalid-operator-input\n'
        return 77
    fi
    printf 'provider-auth-test-remote-exited\n'
    return 79
}
printf 'provider-auth-test-ready\n'
if root_action provider-auth provider=openai-codex; then
    rc=0
else
    rc=$?
fi
printf 'root_action_rc=%s\n' "$rc"
'''

pid, master_fd = pty.fork()
if pid == 0:
    os.execvpe("bash", ["bash", "-c", child_script], os.environ.copy())

captured = bytearray()
status = None


def collect_once(deadline):
    global status
    timeout = max(0.0, min(0.05, deadline - time.monotonic()))
    ready, _, _ = select.select([master_fd], [], [], timeout)
    if ready:
        try:
            captured.extend(os.read(master_fd, 4096))
        except OSError as exc:
            if exc.errno != errno.EIO:
                raise
    waited_pid, waited_status = os.waitpid(pid, os.WNOHANG)
    if waited_pid == pid:
        status = waited_status


def process_group_snapshot(group_id):
    snapshots = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            stat_text = open(f"/proc/{entry}/stat", encoding="utf-8").read()
            comm_end = stat_text.rfind(")")
            comm = stat_text[stat_text.find("(") + 1 : comm_end]
            fields = stat_text[comm_end + 2 :].split()
            if int(fields[2]) != group_id:
                continue
            wchan = open(f"/proc/{entry}/wchan", encoding="utf-8").read().strip()
            status_fields = {}
            for line in open(f"/proc/{entry}/status", encoding="utf-8"):
                key, _, value = line.partition(":")
                if key in ("SigPnd", "ShdPnd", "SigBlk", "SigIgn", "SigCgt"):
                    status_fields[key] = value.strip()
            snapshots.append(
                f"pid={entry},comm={comm},state={fields[0]},wchan={wchan},"
                f"sigpnd={status_fields.get('SigPnd', '?')},"
                f"shdpnd={status_fields.get('ShdPnd', '?')},"
                f"sigblk={status_fields.get('SigBlk', '?')},"
                f"sigign={status_fields.get('SigIgn', '?')},"
                f"sigcgt={status_fields.get('SigCgt', '?')}"
            )
        except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError):
            continue
    return ";".join(sorted(snapshots)) or "process-group-empty"


ready_marker = b"provider-auth-test-ready"
startup_deadline = time.monotonic() + 5.0
while ready_marker not in captured and status is None and time.monotonic() < startup_deadline:
    collect_once(startup_deadline)

if ready_marker not in captured:
    if status is None:
        os.killpg(pid, signal.SIGTERM)
        os.waitpid(pid, 0)
    print("provider-auth-test-startup-timeout")
    sys.exit(1)

input_ready_marker = b"provider-auth-test-awaiting-input"
input_ready_deadline = time.monotonic() + 5.0
while input_ready_marker not in captured and status is None and time.monotonic() < input_ready_deadline:
    collect_once(input_ready_deadline)

if input_ready_marker not in captured:
    if status is None:
        os.killpg(pid, signal.SIGTERM)
        os.waitpid(pid, 0)
    print("provider-auth-test-input-ready-timeout")
    sys.exit(1)

os.write(master_fd, b"operator-input\n")

remote_exit_marker = b"provider-auth-test-remote-exited"
remote_exit_deadline = time.monotonic() + 5.0
while remote_exit_marker not in captured and status is None and time.monotonic() < remote_exit_deadline:
    collect_once(remote_exit_deadline)

if remote_exit_marker not in captured:
    if status is None:
        os.killpg(pid, signal.SIGTERM)
        os.waitpid(pid, 0)
    print("provider-auth-test-remote-exit-timeout")
    sys.exit(1)

behavior_deadline = time.monotonic() + 1.0
while status is None and time.monotonic() < behavior_deadline:
    collect_once(behavior_deadline)

if status is None:
    snapshot = process_group_snapshot(pid)
    captured_text = captured.decode("utf-8", errors="replace").replace("\r", "").replace("\n", "|")
    os.killpg(pid, signal.SIGTERM)
    os.waitpid(pid, 0)
    print(f"provider-auth-hung-after-remote-exit {snapshot} captured={captured_text}")
    sys.exit(1)

try:
    os.killpg(pid, 0)
except ProcessLookupError:
    pass
else:
    os.killpg(pid, signal.SIGTERM)
    print("provider-auth-left-stdin-forwarder-running")
    sys.exit(1)

fcntl.fcntl(master_fd, fcntl.F_SETFL, os.O_NONBLOCK)
try:
    while True:
        captured.extend(os.read(master_fd, 4096))
except OSError as exc:
    if exc.errno not in (errno.EAGAIN, errno.EIO):
        raise
finally:
    os.close(master_fd)

sys.stdout.write(captured.decode("utf-8", errors="replace").replace("\r", ""))
sys.exit(os.waitstatus_to_exitcode(status))
PY
}

run_inference_failure_diagnostics() {
  SCRIPT_DIR="$PROJECT_ROOT" bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    source <(sed "/^while \[\[ \$# -gt 0 \]\]; do/,\$d" "$SCRIPT_DIR/scripts/hermes/acceptance.sh")
    user_exec() {
      printf "%s\n" "Error: selected model is unavailable for this account" >&2
      return 1
    }
    check_inference
    printf "failures=%s\n" "$FAILURES"
  '
}

run_isolated_inference_contract() {
  local work_dir=$1 marker
  mkdir -p "$work_dir"
  marker="$work_dir/inference-argv"
  SCRIPT_DIR="$PROJECT_ROOT" TEST_MARKER="$marker" bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    source <(sed "/^while \[\[ \$# -gt 0 \]\]; do/,\$d" "$SCRIPT_DIR/scripts/hermes/acceptance.sh")
    EXPECTED_PROVIDER=openai-codex
    EXPECTED_MODEL=gpt-5.6-luna
    user_exec() {
      printf "%s\n" "$*" >"$TEST_MARKER"
      if [[ " $* " == *" hermes --safe-mode --provider openai-codex --model gpt-5.6-luna "* &&
        " $* " == *" --toolsets context_engine "* && " $* " == *" -z "* ]]; then
        printf "HERMES_OK\n"
      else
        printf "%119s" unexpected
      fi
    }
    if run_inference_probe; then
      printf "probe=passed\n"
    else
      printf "probe=failed\n"
    fi
    printf "argv=%s\n" "$(<"$TEST_MARKER")"
  '
}

run_remote_auth_status_contract() {
  SCRIPT_DIR="$PROJECT_ROOT" TEST_AUTH_STATUS=$1 bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    source "$SCRIPT_DIR/scripts/hermes/provider-auth-status.sh"
    eval "$(sed -n "/^valid_provider()/,/^}/p; /^auth_status()/,/^}/p" "$SCRIPT_DIR/scripts/hermes/remote-state.sh")"
    as_hermes() { printf "%s\n" "$TEST_AUTH_STATUS"; }
    if auth_status openai-codex; then
      printf "authenticated\n"
    else
      printf "unauthenticated\n"
    fi
  '
}

run_acceptance_auth_status_contract() {
  SCRIPT_DIR="$PROJECT_ROOT" TEST_AUTH_STATUS=$1 bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    source "$SCRIPT_DIR/scripts/hermes/provider-auth-status.sh"
    source <(sed "/^while \[\[ \$# -gt 0 \]\]; do/,\$d" "$SCRIPT_DIR/scripts/hermes/acceptance.sh")
    EXPECTED_PROVIDER=openai-codex
    EXPECTED_MODEL=gpt-5.6-luna
    user_exec() {
      if [[ " $* " == *" hermes auth status "* ]]; then
        printf "%s\n" "$TEST_AUTH_STATUS"
      else
        printf "provider=openai-codex\nmodel=gpt-5.6-luna\n"
      fi
    }
    check_provider
    printf "failures=%s\n" "$FAILURES"
  '
}

run_post_close_status_convergence_contract() {
  local work_dir=$1
  mkdir -p "$work_dir"
  SCRIPT_DIR="$PROJECT_ROOT" TEST_STATE_DIR="$work_dir/state" \
    TEST_COUNTER="$work_dir/status-attempts" bash -c '
      set -o errexit
      set -o nounset
      set -o pipefail
      source "$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
      STATE_DIR="$TEST_STATE_DIR"
      TARGET=lab@172.16.99.12
      PROVIDER=openai-codex
      MODEL=gpt-5.6-luna
      printf "0\n" >"$TEST_COUNTER"
      check_repo_artifacts() { :; }
      state_has() { return 1; }
      is_fixture() { return 1; }
      start_control_master() { :; }
      root_helper_present() { return 0; }
      run_check() { :; }
      resolve_provider_selection() { :; }
      init_state() { mkdir -p "$STATE_DIR"; }
      ensure_root_helper() { :; }
      run_promotion_gate() { :; }
      confirm_production_mutation() { :; }
      run_simple_stage() { :; }
      run_data_backup_stage() { :; }
      run_host_policy_stage() { :; }
      run_update_stage() { :; }
      run_runtime_stage() { :; }
      run_hardening_stage() { :; }
      run_acceptance_stage() { :; }
      run_hermes_reboot_stage() { :; }
      run_provider_stage() { :; }
      run_close_stage() { printf "close-complete\n"; }
      cleanup_remote_temps() { :; }
      status_command() {
        local attempt
        attempt=$(<"$TEST_COUNTER")
        attempt=$((attempt + 1))
        printf "%s\n" "$attempt" >"$TEST_COUNTER"
        if ((attempt < 3)); then
          printf "phase=closed\ndrift=detected\ndrift_reasons=health\n"
          return 78
        fi
        printf "phase=closed\ndrift=none\ndrift_reasons=none\n"
      }
      sleep() { printf "retry-delay=%s\n" "$1"; }
      deploy_command
      printf "status-attempts=%s\n" "$(<"$TEST_COUNTER")"
  '
}

run_post_close_status_diagnostic_contract() {
  local work_dir=$1
  mkdir -p "$work_dir/state"
  printf 'closed\n' >"$work_dir/state/current-phase"
  SCRIPT_DIR="$PROJECT_ROOT" TEST_STATE_DIR="$work_dir/state" bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    source "$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
    STATE_DIR="$TEST_STATE_DIR"
    TARGET=lab@172.16.99.12
    root_helper_present() { return 1; }
    remote_tty() {
      printf "%s\n" \
        "platform=fedora-server-44 health=starting drift=detected drift_reasons=health"
      printf "oauth-device-code=must-not-be-retained\n" >&2
      return 78
    }
    status_rc=0
    status_command || status_rc=$?
    printf "status-rc=%s\n" "$status_rc"
  '
}

run_post_close_status_exhaustion_contract() {
  local work_dir=$1
  mkdir -p "$work_dir"
  SCRIPT_DIR="$PROJECT_ROOT" TEST_COUNTER="$work_dir/status-attempts" bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    source "$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
    printf "0\n" >"$TEST_COUNTER"
    status_command() {
      local attempt
      attempt=$(<"$TEST_COUNTER")
      attempt=$((attempt + 1))
      printf "%s\n" "$attempt" >"$TEST_COUNTER"
      printf "phase=closed\ndrift=detected\ndrift_reasons=health\n"
      return 78
    }
    sleep() { :; }
    status_rc=0
    wait_for_post_close_status || status_rc=$?
    printf "status-rc=%s\n" "$status_rc"
    printf "status-attempts=%s\n" "$(<"$TEST_COUNTER")"
  '
}

run_hermes_status_drift_reason_contract() {
  local work_dir=$1 mock_bin
  mock_bin="$work_dir/bin"
  mkdir -p "$mock_bin"
  cat >"$mock_bin/id" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == '-u hermes' ]]; then
  printf '10000\n'
else
  exec /usr/bin/id "$@"
fi
EOF
  cat >"$mock_bin/runuser" <<'EOF'
#!/usr/bin/env bash
case " $* " in
  *' podman inspect hermes --format '*)
    printf '%s\n' 'docker.io/nousresearch/hermes-agent@sha256:e0df6adebddf29b91112aefc999d4aaf6846c9eb544faca5672a16a13590ff79|starting|true|null'
    ;;
  *' podman exec -i --user 10000:10000 hermes python3 '*)
    cat >/dev/null
    printf 'openai-codex|gpt-5.6-luna\n'
    ;;
  *' systemctl --user is-active hermes.service '*)
    printf 'active\n'
    ;;
  *' hermes auth status openai-codex '*)
    printf 'openai-codex: logged in\n'
    ;;
  *)
    printf 'unexpected runuser invocation: %s\n' "$*" >&2
    exit 97
    ;;
esac
EOF
  cat >"$mock_bin/systemctl" <<'EOF'
#!/usr/bin/env bash
case "$*" in
  'is-enabled dnf5-automatic.timer') printf 'enabled\n' ;;
  'is-active cockpit.socket') printf 'inactive\n' ;;
  *)
    printf 'unexpected systemctl invocation: %s\n' "$*" >&2
    exit 97
    ;;
esac
EOF
  cat >"$mock_bin/sed" <<'EOF'
#!/usr/bin/env bash
if [[ "${*: -1}" == /etc/os-release ]]; then
  case "$*" in
    *'^ID='*) printf 'fedora\n' ;;
    *'^VERSION_ID='*) printf '44\n' ;;
    *'^VARIANT_ID='*) printf 'server\n' ;;
    *'^PRETTY_NAME='*) printf 'Fedora Server 44\n' ;;
    *) exit 97 ;;
  esac
else
  exec /usr/bin/sed "$@"
fi
EOF
  chmod 0700 "$mock_bin/id" "$mock_bin/runuser" "$mock_bin/systemctl" "$mock_bin/sed"
  PATH="$mock_bin:/usr/bin:/bin" "$PROJECT_ROOT/scripts/hermes/wrappers/hermes-status"
}

run_certifier_status_failure_capture_contract() {
  local work_dir=$1
  mkdir -p "$work_dir"
  SCRIPT_DIR="$PROJECT_ROOT" TEST_RUN_DIR="$work_dir" bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    RUN_DIR="$TEST_RUN_DIR"
    PROVIDER=openai-codex
    MODEL=gpt-5.6-luna
    controller() {
      case "$1" in
        deploy) return 78 ;;
        status)
          printf "phase=closed\ndrift=detected\ndrift_reasons=health\n"
          return 78
          ;;
        *) return 97 ;;
      esac
    }
    source <(sed -n "/^run_certification_controller_deploy() {/,/^}/p" \
      "$SCRIPT_DIR/hermes-certify-vm.sh")
    deploy_rc=0
    run_certification_controller_deploy || deploy_rc=$?
    printf "deploy-rc=%s\n" "$deploy_rc"
    printf "diagnostic-mode=%s\n" "$(stat -c %a "$RUN_DIR/status-failure.log")"
    cat "$RUN_DIR/status-failure.log"
  '
}

run_promotion_record_contract() {
  local state_dir=$1 mode=$2
  SCRIPT_DIR="$PROJECT_ROOT" TEST_STATE_DIR="$state_dir" TEST_PROMOTION_MODE="$mode" bash -c '
    set -o errexit
    set -o nounset
    set -o pipefail
    source "$SCRIPT_DIR/scripts/hermes/promotion-record.sh"
    mkdir -p "$TEST_STATE_DIR"
    record="$TEST_STATE_DIR/promotion.record"
    fingerprint=$(promotion_record_fingerprint "$SCRIPT_DIR")
    now=$(date -u +%s)
    issued=$((now - 60))
    expires=$((now + 3600))
    provider=openai-codex
    model=gpt-5.6-luna
    if [[ "$TEST_PROMOTION_MODE" == expired ]]; then
      expires=$((now - 1))
    elif [[ "$TEST_PROMOTION_MODE" == mismatch ]]; then
      provider=openai-api
    fi
    printf "%s\n" \
      "schema=$HERMES_PROMOTION_SCHEMA" \
      "certification_id=certification-test" \
      "promotion_id=promotion-test" \
      "issued_at=$issued" \
      "expires_at=$expires" \
      "artifact_fingerprint=$fingerprint" \
      "iso_sha256=85837793bfa36db6bc709b4cecd2ec116951b87d9c53c3d95eb2fac8dcf7cf1f" \
      "iso_signature=verified" \
      "fedora_version=44" \
      "kernel=6.10.0-100.fc44.x86_64" \
      "podman=5.8.4" \
      "hermes_image=docker.io/nousresearch/hermes-agent@sha256:e0df6adebddf29b91112aefc999d4aaf6846c9eb544faca5672a16a13590ff79" \
      "provider=$provider" \
      "model=$model" \
      "inference_result=HERMES_OK" \
      "credentials_revoked=true" \
      "data_purged=true" \
      "vm_destroyed=true" >"$record"
    chmod 0600 "$record"
    set +e
    promotion_record_validate "$record" openai-codex gpt-5.6-luna \
      docker.io/nousresearch/hermes-agent@sha256:e0df6adebddf29b91112aefc999d4aaf6846c9eb544faca5672a16a13590ff79 \
      "$fingerprint"
    rc=$?
    set -e
    case "$rc" in
      0) printf "validation=valid\n" ;;
      1) printf "validation=mismatch\n" ;;
      2) printf "validation=expired\n" ;;
      *) return "$rc" ;;
    esac
  '
}

Describe "hermes-deploy.sh public CLI"
Before 'spec_ssh_fixture_setup'
After 'spec_ssh_fixture_teardown'

It "fixture ssh records a call and fails closed (positive control)"
When call spec_ssh_positive_control
The status should equal 255
The output should include "FIXTURE_SSH_CALLED"
End

It "fixture ssh refuses to act without the harness opt-in (negative control)"
When call spec_ssh_identity_refusal
The status should equal 90
The output should include "FIXTURE_SSH_REFUSED"
End

It "shows the complete command grammar without contacting a host"
When call run_help_without_ssh "$SPEC_SSH_MARKER"
The status should be success
The output should include "./hermes-deploy.sh [deploy|configure-provider|check|status|rollback|revoke-auth|adopt-host] [options]"
The output should include "--target USER@HOST"
The output should include "--management-cidr CIDR"
The output should include "--identity-file PATH"
The output should include "--provider ID"
The output should include "--model ID"
The output should include "--verbose"
The output should include "No remote operation is performed"
End

It "uses deploy when no subcommand is supplied"
When call run_help_without_ssh "$SPEC_SSH_MARKER"
The status should be success
The output should include "Commands:"
End

It "rejects an unknown subcommand with a usage error"
When run "$PROJECT_ROOT/hermes-deploy.sh" unsupported-command
The status should equal 64
The stderr should include "unknown command"
The stderr should include "Usage:"
End

It "rejects an option without its value"
When run "$PROJECT_ROOT/hermes-deploy.sh" check --target
The status should equal 64
The stderr should include "requires a value"
End

It "rejects an unsupported provider before contacting a host"
When run "$PROJECT_ROOT/hermes-deploy.sh" check --provider unsupported
The status should equal 64
The stderr should include "provider must be openai-codex, openai-api, or nous"
End

It "rejects an unsafe model identifier before contacting a host"
When run "$PROJECT_ROOT/hermes-deploy.sh" check --model "gpt model"
The status should equal 64
The stderr should include "model contains unsupported characters"
End

It "rejects a malformed target before contacting a host"
When call run_invalid_target_without_ssh "$SPEC_SSH_MARKER"
The status should be success
The output should include "USER@HOST"
End
End

Describe "Hermes provider selection"
It "uses gpt-5.6-luna for openai-codex by default"
When call run_provider_resolution "$SHELLSPEC_WORKDIR/codex-state" openai-codex ""
The status should be success
The output should include "provider=openai-codex"
The output should include "model=gpt-5.6-luna"
End

It "uses gpt-5.6-luna for openai-api by default"
When call run_provider_resolution "$SHELLSPEC_WORKDIR/api-state" openai-api ""
The status should be success
The output should include "provider=openai-api"
The output should include "model=gpt-5.6-luna"
End

It "uses the Claude Sonnet default for Nous"
When call run_provider_resolution "$SHELLSPEC_WORKDIR/nous-state" nous ""
The status should be success
The output should include "provider=nous"
The output should include "model=anthropic/claude-sonnet-4.6"
End

It "preserves an explicit model override"
When call run_provider_resolution "$SHELLSPEC_WORKDIR/override-state" openai-codex gpt-5.6-sol
The status should be success
The output should include "provider=openai-codex"
The output should include "model=gpt-5.6-sol"
End

It "replaces a stale gateway default model with the selected model"
When call run_model_config_writer "$SHELLSPEC_WORKDIR/model-config/config.yaml"
The status should be success
The output should include "model.provider=openai-codex"
The output should include "model.default=gpt-5.6-luna"
The output should include "model.model=gpt-5.6-luna"
The output should include "default_model=gpt-5.6-luna"
The output should include "api_key_present=False"
End

It "reuses an accepted provider and model without an interactive menu"
When call run_accepted_provider_resolution "$SHELLSPEC_WORKDIR/accepted-state"
The status should be success
The output should include "provider=openai-api"
The output should include "model=gpt-5.6-luna"
End

It "requires an explicit provider for a fresh non-interactive run"
When call run_provider_resolution_without_selection "$SHELLSPEC_WORKDIR/fresh-state"
The status should be success
The output should include "provider selection requires an interactive operator terminal"
End
End

Describe "Hermes provider resume safety"
It "refreshes provider-facing helpers even when the runtime stage is already valid"
When call run_runtime_resume_sync "$SHELLSPEC_WORKDIR/runtime-resume-state"
The status should be success
The output should include "action=install-runtime-helpers"
End

It "restores the prior provider with the canonical model artifact"
When call run_provider_rollback "$SHELLSPEC_WORKDIR/provider-rollback-state"
The status should be success
The output should include "root_action=set-model model_path=/tmp/hermes-deploy.Model123 provider=nous model=anthropic/claude-sonnet-4.6"
The output should include "root_action=revoke-auth provider=openai-codex"
The stderr should include "restoring the previous provider configuration"
End

It "resets stale completion and promotion state after a fresh-data rollback"
When call run_fresh_purge_state_reset "$SHELLSPEC_WORKDIR/fresh-purge-state"
The status should be success
The output should include "Rollback complete. Hermes data was retained unless --purge-fresh was explicitly selected; RPM and kernel updates were not reversed."
The output should include "target=aicowork@10.0.30.10"
The output should include "cidr=192.168.99.0/24"
The output should include "interface=eno1"
The output should include "phase=rollback"
The output should include "rollback-marker=present"
The output should not include "stale="
End

It "retains deployment state after a standard rollback"
When call run_standard_rollback_state_marker "$SHELLSPEC_WORKDIR/standard-rollback-state"
The status should be success
The output should include "phase=rollback"
The output should include "closed-marker=present"
The output should include "provider=openai-codex"
The output should include "promotion=existing-promotion"
End

It "uses a finite non-TTY stream for non-interactive credential revocation"
When call run_revocation_metadata_stream
The status should be success
The output should include "revoke-auth"
The output should include "provider=openai-codex"
End

It "waits for the certification operator before starting provider authentication"
When call run_provider_auth_operator_readiness "$SHELLSPEC_WORKDIR/provider-auth-readiness"
The status should be success
The output should include "provider-auth-readiness-instructions-clear"
The output should include "provider-auth-waited-for-operator"
The output should include "provider-auth-rejected-invalid-confirmation"
The output should include "provider-auth-started-after-operator-ready"
The output should not include "provider-auth-started-before-operator-ready"
The output should not include "provider-auth-started-after-invalid-confirmation"
End

It "fails closed before OAuth when encrypted-boot evidence is invalid"
When call run_provider_auth_invalid_unlock_evidence "$SHELLSPEC_WORKDIR/provider-invalid-unlock"
The status should be success
The output should include "rc=78"
The output should include "VM encrypted-boot evidence failed closed"
The output should not include "AUTHENTICATION_READY"
The output should not include "provider-auth-invoked"
End

It "stops forwarding an open operator TTY when provider authentication exits"
When call run_provider_auth_remote_exit_with_open_tty
The status should be success
The output should include "root_action_rc=79"
The output should not include "provider-auth-test-invalid-protocol"
The output should not include "provider-auth-test-invalid-operator-input"
The output should not include "provider-auth-test-startup-timeout"
The output should not include "provider-auth-test-input-ready-timeout"
The output should not include "provider-auth-test-remote-exit-timeout"
The output should not include "provider-auth-hung-after-remote-exit"
End
End

Describe "Hermes reboot reconnect policy"
It "allows the encrypted certification VM ten minutes to unlock and reconnect"
When call run_hermes_reboot_reconnect_attempts 1 lab@172.16.99.12
The status should be success
The output should equal "600"
End

It "keeps the production reboot reconnect wait at five minutes"
When call run_hermes_reboot_reconnect_attempts 0 aicowork@10.0.30.10
The status should be success
The output should equal "300"
End

It "caps each SSH probe below the overall reconnect deadline"
When call run_reconnect_probe_options
The status should be success
The output should equal "effective-connect-timeout=2"
End
End

Describe "Hermes certification concurrency"
It "rejects a second certifier before creating a run or VM"
When call run_concurrent_certifier_rejection "$SHELLSPEC_WORKDIR/concurrent-certifier"
The status should be success
The stderr should equal ""
The output should include "another Hermes certification is already active"
End
End

Describe "Hermes certification failure cleanup"
It "uses diagnostic and credential cleanup when interrupted"
When call run_certifier_interrupt_cleanup "$SHELLSPEC_WORKDIR/interrupted-certifier"
The status should be success
The output should include "child_rc=130"
The output should include "diagnostics-captured"
The output should include "failure-cleanup-used"
End

It "streams the cleanup script through the fixture's authorized sudo command"
When call run_remove_fixture_sudo_contract
The status should be success
The output should equal "ssh_vm <sudo> <-n> </usr/bin/bash> <-s>
stdin <rm -f -- /etc/sudoers.d/lab-hermes-fixture>
ssh_vm <test> <!> <-e> </etc/sudoers.d/lab-hermes-fixture>"
End

It "destroys the disposable VM after credential cleanup is verified"
When call run_certifier_verified_failure_cleanup "$SHELLSPEC_WORKDIR/verified-failure-cleanup"
The status should be success
The output should include "providers-revoked"
The output should include "fresh-data-purged"
The output should include "fixture-sudo-removed"
The output should include "vm-creator --destroy"
The output should include "destroy-verified"
The output should include "vm_created=false"
The output should not include "unexpected-virsh"
The stderr should include "cleanup and VM destruction verified"
End
End

Describe "Hermes certification encrypted-boot evidence"
It "accepts exactly one initial unlock and one unlock per three watched boots"
When call run_certification_unlock_evidence_contract "$SHELLSPEC_WORKDIR/unlock-valid" valid
The status should be success
The output should equal "evidence=valid"
End

It "rejects a duplicate same-boot submission"
When call run_certification_unlock_evidence_contract "$SHELLSPEC_WORKDIR/unlock-duplicate" duplicate
The status should be success
The output should equal "evidence=invalid"
End

It "rejects a cryptsetup boundary without a fresh reboot marker"
When call run_certification_unlock_evidence_contract "$SHELLSPEC_WORKDIR/unlock-missing-reboot" missing-reboot
The status should be success
The output should equal "evidence=invalid"
End
End

Describe "Hermes inference diagnostics"
It "uses an isolated one-shot with the certified provider and model"
When call run_isolated_inference_contract "$SHELLSPEC_WORKDIR/isolated-inference"
The status should be success
The output should include "probe=passed"
The output should include "hermes --safe-mode --provider openai-codex --model gpt-5.6-luna"
The output should include "--toolsets context_engine"
The stderr should equal ""
End

It "preserves a sanitized provider failure signal without exposing provider text"
When call run_inference_failure_diagnostics
The status should be success
The stderr should include "INFERENCE_FAILED"
The stderr should include "exit_code=1"
The stderr should include "stdout=empty"
The stderr should include "stderr=model-access"
The output should not include "selected model is unavailable"
The stderr should not include "selected model is unavailable"
The output should include "failures=1"
End
End

Describe "Hermes provider authentication status"
It "rejects Hermes logged-out output even when the command exits zero"
When call run_remote_auth_status_contract "openai-codex: logged out (No credentials stored.)"
The status should be success
The output should equal "unauthenticated"
End

It "accepts the exact Hermes logged-in status line"
When call run_remote_auth_status_contract "openai-codex: logged in"
The status should be success
The output should equal "authenticated"
End

It "makes provider acceptance reject logged-out output"
When call run_acceptance_auth_status_contract "openai-codex: logged out (No credentials stored.)"
The status should be success
The stderr should include "auth status is logged in"
The output should include "failures=1"
End

It "makes provider acceptance accept logged-in output"
When call run_acceptance_auth_status_contract "openai-codex: logged in"
The status should be success
The output should include "failures=0"
End
End

Describe "Hermes post-close status convergence"
It "waits for a newly closed deployment to become healthy"
When call run_post_close_status_convergence_contract "$SHELLSPEC_WORKDIR/post-close-convergence"
The status should be success
The output should include "close-complete"
The output should include "retry-delay=5"
The output should include "status-attempts=3"
The output should include "drift=none"
End

It "reports the allowlisted reason without retaining remote stderr"
When call run_post_close_status_diagnostic_contract "$SHELLSPEC_WORKDIR/post-close-diagnostic"
The status should be success
The output should include "status-rc=78"
The output should include "drift_reasons=health"
The stderr should include "STATUS_FAILED exit_code=78 drift_reasons=health"
The output should not include "must-not-be-retained"
The stderr should not include "must-not-be-retained"
End

It "fails after the bounded retry budget with the final safe reason"
When call run_post_close_status_exhaustion_contract "$SHELLSPEC_WORKDIR/post-close-exhaustion"
The status should be success
The output should include "status-rc=78"
The output should include "status-attempts=12"
The output should include "drift_reasons=health"
The stderr should include "post-close status did not converge after 12 attempts"
The stderr should include "drift_reasons=health"
End

It "identifies the exact drifted wrapper check"
When call run_hermes_status_drift_reason_contract "$SHELLSPEC_WORKDIR/hermes-status-drift"
The status should equal 1
The output should include "drift=detected"
The output should include "drift_reasons=health"
The output should include "host_machine_id_sha256=unbound"
The output should include "promotion_id=unconfigured"
The output should not include "unexpected runuser invocation"
The output should not include "unexpected systemctl invocation"
End

It "retains a mode-0600 status artifact when controller deployment fails"
When call run_certifier_status_failure_capture_contract "$SHELLSPEC_WORKDIR/certifier-status-failure"
The status should be success
The output should include "deploy-rc=78"
The output should include "diagnostic-mode=600"
The output should include "controller_deploy_exit=78"
The output should include "controller_status_exit=78"
The output should include "drift_reasons=health"
The stderr should include "Sanitized controller status retained at"
End
End

Describe "hermes-deploy.sh state contract"
It "does not create deployment state for help"
When call run_help_without_state "$SHELLSPEC_WORKDIR/state"
The status should be success
The output should include "No remote operation is performed"
End

It "has a side-effect-free check mode in fixture transport"
When call run_fixture_check_without_state "$SHELLSPEC_WORKDIR/state"
The status should be success
The output should include "Preflight passed"
End

It "reports fixture status without creating state"
When call run_fixture_status_without_state "$SHELLSPEC_WORKDIR/state"
The status should be success
The output should include "phase=not-started"
The output should include "service_health=fixture-healthy"
The output should include "provider=unconfigured"
The output should include "model=unconfigured"
The output should include "provider_auth=unconfigured"
The output should include "drift=none"
End

It "rejects fixture deployment before creating state"
When call run_fixture_deploy_rejected "$SHELLSPEC_WORKDIR/state"
The status should be success
The output should include "fixture transport is read-only"
End

It "rejects malformed site options before contacting a host"
When run "$PROJECT_ROOT/hermes-deploy.sh" check --management-cidr 192.168.99.0/33
The status should equal 64
The stderr should include "valid IPv4 CIDR"
End

It "rejects the removed days option"
When run "$PROJECT_ROOT/hermes-deploy.sh" check --days 8
The status should equal 64
The stderr should include "unknown option: --days"
End
End

Describe "Hermes preflight status propagation"
It "preserves a failed remote preflight status after temporary-file cleanup"
When call run_remote_preflight_failure_contract
The status should be success
The output should include "remote-preflight-failed"
The output should include "removed=/tmp/hermes-deploy.Mock1"
The output should include "removed=/tmp/hermes-deploy.Mock2"
The output should include "run-check-rc=1"
The output should include "root-helper-preflight-failed"
The output should include "root-run-check-rc=1"
The output should not include "Preflight passed for"
The stderr should include "preflight failed"
End

It "preserves update mode when the host module is the fourth argument"
When call run_remote_preflight_four_argument_contract "$SHELLSPEC_WORKDIR/preflight-four-arguments"
The status should be success
The output should include "preflight-rc=0"
The output should include "allow-update=1"
The output should include "PREFLIGHT_OK"
The output should not include "four-argument update mode"
End
End

Describe "Hermes root helper bootstrap"
It "allows the bootstrap sudo prompt in the same remote TTY"
When call run_root_helper_bootstrap_sudo_contract
The status should be success
The output should include "argument-1=sudo"
The output should include "argument-2=/usr/bin/bash"
The output should include "argument-3=-c"
The output should include "argument-count=4"
The output should not include "argument-2=-n"
End
End

Describe "Hermes promotion records"
It "accepts a fresh record with matching provider and artifacts"
When call run_promotion_record_contract "$SHELLSPEC_WORKDIR/promotion-valid" valid
The status should be success
The output should equal "validation=valid"
End

It "classifies an expired record separately from a mismatched record"
When call run_promotion_record_contract "$SHELLSPEC_WORKDIR/promotion-expired" expired
The status should be success
The output should equal "validation=expired"
End

It "rejects a record for a different provider"
When call run_promotion_record_contract "$SHELLSPEC_WORKDIR/promotion-mismatch" mismatch
The status should be success
The output should equal "validation=mismatch"
End
End
