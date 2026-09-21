#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC1091,SC2029
# Workstation-side orchestration for hermes-deploy.sh.

if [[ -n "${_HERMES_DEPLOY_LIB_LOADED-}" ]]; then
  return 0
fi
readonly _HERMES_DEPLOY_LIB_LOADED=1
readonly REPO_ROOT="$SCRIPT_DIR"
readonly REMOTE_DIR="$REPO_ROOT/scripts/hermes"
readonly DEFAULT_TARGET='aicowork@10.0.30.10'
readonly DEFAULT_MANAGEMENT_CIDR='192.168.99.0/24'
readonly DEFAULT_INTERFACE='eno1'
readonly DEFAULT_OPENAI_MODEL='gpt-5.6-luna'
readonly DEFAULT_NOUS_MODEL='anthropic/claude-sonnet-4.6'
readonly POST_CLOSE_STATUS_ATTEMPTS=12
readonly POST_CLOSE_STATUS_INTERVAL_SECONDS=5
readonly EXPECTED_IMAGE='docker.io/nousresearch/hermes-agent@sha256:e0df6adebddf29b91112aefc999d4aaf6846c9eb544faca5672a16a13590ff79'
# shellcheck source=promotion-record.sh
source "$REMOTE_DIR/promotion-record.sh"
# shellcheck source=certification-evidence.sh
source "$REMOTE_DIR/certification-evidence.sh"

COMMAND=deploy
TARGET="$DEFAULT_TARGET"
TARGET_USER=''
MANAGEMENT_CIDR="$DEFAULT_MANAGEMENT_CIDR"
MANAGEMENT_INTERFACE="$DEFAULT_INTERFACE"
IDENTITY_FILE=''
VERBOSE=false
PURGE_FRESH=false
PROVIDER=''
MODEL=''
PROMOTION_RECORD=''
HOST_KEY=''
STATE_ROOT=''
STATE_DIR=''
WORK_DIR=''
CONTROL_SOCKET=''
UPLOADED_PATH=''
TEMP_HELPER_BOOTSTRAPPED=false
declare -a REMOTE_TEMP_PATHS=()
declare -a SSH_OPTIONS=()

if [[ -t 2 && ! -v NO_COLOR ]]; then
  readonly _C_B=$'\x1b[34m' _C_Y=$'\x1b[33m' _C_R=$'\x1b[31m' _C_OFF=$'\x1b[0m'
else
  readonly _C_B='' _C_Y='' _C_R='' _C_OFF=''
fi

log() { printf '%s[INFO]%s  %s\n' "$_C_B" "$_C_OFF" "$*" >&2; }
warn() { printf '%s[WARN]%s  %s\n' "$_C_Y" "$_C_OFF" "$*" >&2; }
error() { printf '%s[ERROR]%s %s\n' "$_C_R" "$_C_OFF" "$*" >&2; }

die() {
  local code=$1
  shift
  error "$*"
  exit "$code"
}

usage_error() {
  local message=$1
  error "$message"
  error 'Usage: ./hermes-deploy.sh [deploy|configure-provider|check|status|rollback|revoke-auth|adopt-host] [options]'
  exit 64
}

debug() {
  $VERBOSE || return 0
  log "$*"
}

show_help() {
  cat <<'EOF'
Hermes one-command deployment controller

Usage:
  ./hermes-deploy.sh [deploy|configure-provider|check|status|rollback|revoke-auth|adopt-host] [options]

Commands:
  deploy       Install, resume, or safely converge the managed service (default).
  configure-provider
               Switch or configure the provider on an existing deployment.
  check        Run local and remote read-only preflight checks.
  status       Report platform, host identity, provider, health, image pin, and drift.
  rollback     Restore Hermes and manifest-tracked host configuration; RPM updates remain.
  revoke-auth  Log out one selected provider without deleting unrelated state.
  adopt-host   Bind a reinstalled host and archive legacy workstation state.

Options:
  --non-interactive --config PATH --release PATH
                                 enrolled signed-release interface; also supports upgrade
                                 see docs/HERMES_UNATTENDED_DEPLOYMENT.md
  --target USER@HOST             default: aicowork@10.0.30.10
  --identity-file PATH           optional OpenSSH identity file
  --management-cidr CIDR         default: 192.168.99.0/24
  --interface NAME               default: eno1
  --provider ID                  openai-codex, openai-api, or nous
  --model ID                     provider model (defaults are provider-specific)
  --promotion-record PATH        fresh VM certification record for deploy/provider changes
  --verbose                      sanitized diagnostics only; credentials are never traced
  --purge-fresh                  rollback only: remove installer-created identity and data
  -h, --help                     show this help

No remote operation is performed and no local deployment state is created by --help.
Production mutation requires an explicit operator invocation after check and
the target-specific gates. Provider OAuth, API-key, and sudo prompts stay in the terminal.
EOF
}

parse_args() {
  local arg
  if [[ $# -gt 0 && "$1" != -* ]]; then
    case "$1" in
      deploy | configure-provider | check | status | rollback | revoke-auth | adopt-host)
        COMMAND=$1
        shift
        ;;
      *) usage_error "unknown command: $1" ;;
    esac
  fi

  while [[ $# -gt 0 ]]; do
    arg=$1
    case "$arg" in
      -h | --help)
        show_help
        exit 0
        ;;
      --target)
        [[ $# -gt 1 ]] || usage_error '--target requires a value'
        TARGET=$2
        shift 2
        ;;
      --target=*)
        TARGET=$(printf '%s' "$arg" | cut -d= -f2-)
        shift
        ;;
      --identity-file)
        [[ $# -gt 1 ]] || usage_error '--identity-file requires a value'
        IDENTITY_FILE=$2
        shift 2
        ;;
      --identity-file=*)
        IDENTITY_FILE=$(printf '%s' "$arg" | cut -d= -f2-)
        shift
        ;;
      --management-cidr)
        [[ $# -gt 1 ]] || usage_error '--management-cidr requires a value'
        MANAGEMENT_CIDR=$2
        shift 2
        ;;
      --management-cidr=*)
        MANAGEMENT_CIDR=$(printf '%s' "$arg" | cut -d= -f2-)
        shift
        ;;
      --interface)
        [[ $# -gt 1 ]] || usage_error '--interface requires a value'
        MANAGEMENT_INTERFACE=$2
        shift 2
        ;;
      --interface=*)
        MANAGEMENT_INTERFACE=$(printf '%s' "$arg" | cut -d= -f2-)
        shift
        ;;
      --provider)
        [[ $# -gt 1 ]] || usage_error '--provider requires a value'
        PROVIDER=$2
        shift 2
        ;;
      --provider=*)
        PROVIDER=$(printf '%s' "$arg" | cut -d= -f2-)
        shift
        ;;
      --model)
        [[ $# -gt 1 ]] || usage_error '--model requires a value'
        MODEL=$2
        shift 2
        ;;
      --model=*)
        MODEL=$(printf '%s' "$arg" | cut -d= -f2-)
        shift
        ;;
      --promotion-record)
        [[ $# -gt 1 ]] || usage_error '--promotion-record requires a value'
        PROMOTION_RECORD=$2
        shift 2
        ;;
      --promotion-record=*)
        PROMOTION_RECORD=$(printf '%s' "$arg" | cut -d= -f2-)
        shift
        ;;
      --verbose)
        VERBOSE=true
        shift
        ;;
      --purge-fresh)
        PURGE_FRESH=true
        shift
        ;;
      *) usage_error "unknown option: $arg" ;;
    esac
  done
}

valid_ipv4_cidr() {
  local address prefix octet
  local -a octets
  IFS=/ read -r address prefix <<<"$1"
  [[ "$address" =~ ^[0-9]+(\.[0-9]+){3}$ && "$prefix" =~ ^[0-9]+$ ]] || return 1
  IFS=. read -r -a octets <<<"$address"
  (("${#octets[@]}" == 4 && prefix <= 32)) || return 1
  for octet in "${octets[@]}"; do
    [[ "$octet" =~ ^[0-9]+$ ]] && ((octet <= 255)) || return 1
  done
}

valid_provider() {
  [[ "$1" == openai-codex || "$1" == openai-api || "$1" == nous ]]
}

valid_model() {
  [[ "$1" =~ ^[A-Za-z0-9._:/-]+$ ]]
}

provider_default_model() {
  case "$1" in
    openai-codex | openai-api) printf '%s\n' "$DEFAULT_OPENAI_MODEL" ;;
    nous) printf '%s\n' "$DEFAULT_NOUS_MODEL" ;;
    *) return 1 ;;
  esac
}

existing_provider() {
  local provider
  provider=$(state_read provider || true)
  if [[ -z "$provider" ]]; then
    if state_has stage-model-configured || state_has stage-oauth; then
      provider=nous
    fi
  fi
  printf '%s\n' "$provider"
}

existing_model() {
  local model provider
  model=$(state_read model || true)
  if [[ -z "$model" ]]; then
    provider=$(existing_provider)
    if [[ -n "$provider" ]]; then
      model=$(provider_default_model "$provider")
    fi
  fi
  printf '%s\n' "$model"
}

prompt_provider() {
  local selection
  [[ -t 0 && -r /dev/tty ]] || die 75 'provider selection requires an interactive operator terminal'
  cat >&2 <<'EOF'
Select the Hermes inference provider:
  1) ChatGPT or Codex Subscription (openai-codex)
  2) OpenAI API key (openai-api; usage-based billing)
  3) Nous Portal (nous)
EOF
  printf 'Selection [1]: ' >&2
  IFS= read -r selection </dev/tty || die 75 'provider selection was cancelled'
  case "${selection:-1}" in
    1) PROVIDER=openai-codex ;;
    2) PROVIDER=openai-api ;;
    3) PROVIDER=nous ;;
    *) die 64 'provider selection must be 1, 2, or 3' ;;
  esac
}

resolve_provider_selection() {
  local prior_provider prior_model
  case "$COMMAND" in
    deploy | configure-provider)
      prior_provider=$(existing_provider)
      prior_model=$(existing_model)
      if [[ -z "$PROVIDER" ]]; then
        if [[ -t 0 && -r /dev/tty ]]; then
          prompt_provider
        elif [[ -n "$prior_provider" && -r "$STATE_DIR/stage-inference-acceptance" ]]; then
          PROVIDER=$prior_provider
        else
          die 75 'provider selection requires an interactive operator terminal or an accepted provider'
        fi
      fi
      valid_provider "$PROVIDER" || die 64 'provider must be openai-codex, openai-api, or nous'
      if [[ -z "$MODEL" ]]; then
        if [[ "$PROVIDER" == "$prior_provider" && -n "$prior_model" ]]; then
          MODEL=$prior_model
        else
          MODEL=$(provider_default_model "$PROVIDER")
        fi
      fi
      valid_model "$MODEL" || die 64 'model contains unsupported characters'
      ;;
    revoke-auth)
      prior_provider=$(existing_provider)
      if [[ -z "$PROVIDER" ]]; then
        PROVIDER=$prior_provider
        [[ -n "$PROVIDER" ]] || PROVIDER=nous
      fi
      valid_provider "$PROVIDER" || die 64 'provider must be openai-codex, openai-api, or nous'
      [[ -z "$MODEL" ]] || die 64 '--model is valid only with deploy or configure-provider'
      ;;
    *)
      [[ -z "$PROVIDER" && -z "$MODEL" ]] || die 64 '--provider and --model are valid only with provider commands'
      ;;
  esac
}

validate_options() {
  local state_home
  [[ "$TARGET" =~ ^[a-z_][a-z0-9_-]*@[A-Za-z0-9_.:-]+$ ]] || die 64 'target must use a shell-safe USER@HOST'
  TARGET_USER=${TARGET%%@*}
  valid_ipv4_cidr "$MANAGEMENT_CIDR" || die 64 'management CIDR must be a valid IPv4 CIDR'
  [[ "$MANAGEMENT_INTERFACE" =~ ^[[:alnum:]_.:-]+$ ]] || die 64 'interface contains unsupported characters'
  if [[ -n "$IDENTITY_FILE" && ! -r "$IDENTITY_FILE" ]]; then
    die 66 "identity file is not readable: $IDENTITY_FILE"
  fi
  if $PURGE_FRESH && [[ "$COMMAND" != rollback ]]; then
    die 64 '--purge-fresh is valid only with rollback'
  fi
  if [[ -n "$PROVIDER" ]]; then
    valid_provider "$PROVIDER" || die 64 'provider must be openai-codex, openai-api, or nous'
  fi
  if [[ -n "$MODEL" ]]; then
    valid_model "$MODEL" || die 64 'model contains unsupported characters'
  fi
  case "$COMMAND" in
    deploy | configure-provider | revoke-auth) ;;
    *)
      [[ -z "$PROVIDER" && -z "$MODEL" && -z "$PROMOTION_RECORD" ]] \
        || die 64 '--provider, --model, and --promotion-record are valid only with deployment/provider commands'
      ;;
  esac
  case "$COMMAND" in
    deploy | configure-provider) ;;
    *) [[ -z "$PROMOTION_RECORD" ]] || die 64 '--promotion-record is valid only with deploy or configure-provider' ;;
  esac

  if [[ "${HERMES_DEPLOY_TRANSPORT-}" == fixture ]]; then
    HOST_KEY=fixture
  else
    HOST_KEY=$(printf '%s' "$TARGET" | tr -c 'A-Za-z0-9_.-' '_')
  fi
  state_home=${XDG_STATE_HOME:-}
  if [[ -z "$state_home" ]]; then
    [[ -n "${HOME:-}" ]] || die 70 'HOME or XDG_STATE_HOME is required'
    state_home=$HOME/.local/state
  fi
  STATE_ROOT="$state_home/hermes-deploy"
  STATE_DIR="$STATE_ROOT/$HOST_KEY"
}

configure_ssh() {
  SSH_OPTIONS=(
    -o ConnectTimeout=15
    -o ServerAliveInterval=15
    -o ServerAliveCountMax=3
    -o PreferredAuthentications=publickey
    -o PasswordAuthentication=no
    -o KbdInteractiveAuthentication=no
    -o StrictHostKeyChecking=yes
    -o ControlMaster=no
    -o ControlPath=none
  )
  if [[ -n "$IDENTITY_FILE" ]]; then
    SSH_OPTIONS+=(-i "$IDENTITY_FILE" -o IdentitiesOnly=yes)
  fi
  if [[ -v HERMES_DEPLOY_KNOWN_HOSTS ]] && [[ -n "$HERMES_DEPLOY_KNOWN_HOSTS" ]]; then
    SSH_OPTIONS+=(-o "UserKnownHostsFile=$HERMES_DEPLOY_KNOWN_HOSTS")
  fi
}

state_write() {
  local name=$1
  local value=$2
  local tmp
  [[ "$name" =~ ^[A-Za-z0-9._-]+$ ]] || die 70 'invalid local state name'
  install -d -m 0700 "$STATE_DIR"
  chmod 0700 "$STATE_DIR"
  tmp=$(mktemp "$STATE_DIR/.$name.XXXXXX")
  chmod 0600 "$tmp"
  printf '%s\n' "$value" >"$tmp"
  mv -- "$tmp" "$STATE_DIR/$name"
  chmod 0600 "$STATE_DIR/$name"
}

state_read() {
  local name=$1
  [[ -r "$STATE_DIR/$name" ]] || return 1
  sed -n '1p' "$STATE_DIR/$name"
}

state_has() { [[ -r "$STATE_DIR/$1" ]]; }

init_state() {
  install -d -m 0700 "$STATE_DIR"
  chmod 0700 "$STATE_DIR"
  state_write target "$TARGET"
  state_write management-cidr "$MANAGEMENT_CIDR"
  state_write interface "$MANAGEMENT_INTERFACE"
}

mark_local_stage() {
  state_write "stage-$1" "$(date -u +%s)"
  state_write current-phase "$1"
}

is_fixture() {
  [[ "${HERMES_DEPLOY_TRANSPORT-}" == fixture ]]
}

remote() {
  if is_fixture; then
    return 0
  fi
  if [[ -n "$CONTROL_SOCKET" ]]; then
    ssh "${SSH_OPTIONS[@]}" -S "$CONTROL_SOCKET" -o ControlMaster=auto "$TARGET" "$@"
  else
    ssh "${SSH_OPTIONS[@]}" "$TARGET" "$@"
  fi
}

remote_no_stdin() {
  if is_fixture; then
    return 0
  fi
  if [[ -n "$CONTROL_SOCKET" ]]; then
    ssh "${SSH_OPTIONS[@]}" -S "$CONTROL_SOCKET" -o ControlMaster=auto "$TARGET" "$@" </dev/null
  else
    ssh "${SSH_OPTIONS[@]}" "$TARGET" "$@" </dev/null
  fi
}

remote_without_control() {
  if is_fixture; then
    return 0
  fi
  ssh "${SSH_OPTIONS[@]}" -o BatchMode=yes -o ControlMaster=no -o ControlPath=none "$TARGET" "$@" </dev/null
}

remote_reconnect_probe() {
  if is_fixture; then
    return 0
  fi
  # Reconnect budgets are wall-clock deadlines. Keep an individual network
  # probe short so an unreachable host cannot multiply the declared budget by
  # the controller's normal 15-second SSH connection timeout.
  ssh "${SSH_OPTIONS[@]}" -o ConnectTimeout=2 -o ConnectionAttempts=1 \
    -o BatchMode=yes -o ControlMaster=no -o ControlPath=none "$TARGET" "$@" </dev/null
}

remote_tty() {
  if is_fixture; then
    return 0
  fi
  if [[ -n "$CONTROL_SOCKET" ]]; then
    ssh -tt "${SSH_OPTIONS[@]}" -S "$CONTROL_SOCKET" -o ControlMaster=auto "$TARGET" "$@"
  else
    ssh -tt "${SSH_OPTIONS[@]}" "$TARGET" "$@"
  fi
}

remote_tty_from_fifo() {
  local input_fifo=$1
  shift
  [[ -p "$input_fifo" ]] || die 70 'controller input FIFO is unavailable'
  if is_fixture; then
    return 0
  fi
  if [[ -n "$CONTROL_SOCKET" ]]; then
    ssh -tt "${SSH_OPTIONS[@]}" -S "$CONTROL_SOCKET" -o ControlMaster=auto "$TARGET" "$@" <"$input_fifo"
  else
    ssh -tt "${SSH_OPTIONS[@]}" "$TARGET" "$@" <"$input_fifo"
  fi
}

ensure_sudo_session() {
  # NOPASSWD command rules do not satisfy `sudo -v`; probe a command first so
  # disposable fixtures do not block on a password prompt, while production
  # hosts still get the normal interactive sudo credential check.
  if certification_context_is_valid && remote_tty 'sudo -n /usr/bin/bash -c true' </dev/null >/dev/null 2>&1; then
    return 0
  fi
  if remote_tty 'sudo -n true' </dev/null >/dev/null 2>&1; then
    return 0
  fi
  remote_tty 'sudo -v'
}

remote_script() {
  local privilege=$1
  local script=$2
  shift 2
  if [[ "$privilege" == root ]]; then
    ensure_sudo_session
    remote 'sudo -n bash -s' "$@" <"$script"
  else
    remote bash -s -- "$@" <"$script"
  fi
}

run_remote_preflight() {
  local allow_update=$1 host_module_path remote_rc=0 cleanup_rc=0
  upload_file "$REMOTE_DIR/remote-preflight.sh"
  local preflight_path=$UPLOADED_PATH
  upload_file "$REMOTE_DIR/fedora-server-host.sh"
  host_module_path=$UPLOADED_PATH
  # Keep the read-only preflight in the authenticated TTY. Password-backed
  # sudo may be scoped to that terminal, while the preflight itself must run
  # as root so its checks do not depend on a non-interactive sudo ticket.
  remote_tty sudo /usr/bin/bash "$preflight_path" "$MANAGEMENT_CIDR" "$MANAGEMENT_INTERFACE" "$allow_update" \
    "$host_module_path" || remote_rc=$?
  remove_remote_temp "$preflight_path" || cleanup_rc=$?
  remove_remote_temp "$host_module_path" || cleanup_rc=$?
  ((remote_rc == 0)) || return "$remote_rc"
  return "$cleanup_rc"
}

start_control_master() {
  is_fixture && return 0
  WORK_DIR=$(mktemp -d)
  chmod 0700 "$WORK_DIR"
  CONTROL_SOCKET="$WORK_DIR/control.sock"
  ssh "${SSH_OPTIONS[@]}" -M -S "$CONTROL_SOCKET" -o ControlMaster=yes -o ControlPersist=600 -fnNT "$TARGET"
  remote_no_stdin true
}

wait_for_reconnect() {
  local max_seconds=${1:-300}
  local attempt deadline remaining
  [[ "$max_seconds" =~ ^[1-9][0-9]*$ ]] || die 70 'invalid reconnect wait limit'
  deadline=$((SECONDS + max_seconds))
  for attempt in {1..30}; do
    : "$attempt"
    if ! remote_reconnect_probe true >/dev/null 2>&1; then
      break
    fi
    ((SECONDS < deadline)) || return 1
    sleep 2
  done
  while ((SECONDS < deadline)); do
    remote_reconnect_probe true >/dev/null 2>&1 && return 0
    remaining=$((deadline - SECONDS))
    ((remaining > 0)) || break
    if ((remaining < 5)); then
      sleep "$remaining"
    else
      sleep 5
    fi
  done
  return 1
}

remote_temp_path() {
  local path=$1
  [[ "$path" =~ ^/tmp/hermes-deploy\.[A-Za-z0-9]+$ ]] || die 70 'unexpected remote temporary path'
}

upload_file() {
  local local_path=$1
  [[ -r "$local_path" ]] || die 66 "artifact is not readable: $local_path"
  UPLOADED_PATH=$(remote_no_stdin 'mktemp --tmpdir=/tmp hermes-deploy.XXXXXX')
  remote_temp_path "$UPLOADED_PATH"
  remote "cat > '$UPLOADED_PATH'" <"$local_path"
  REMOTE_TEMP_PATHS+=("$UPLOADED_PATH")
}

remove_remote_temp() {
  local path=$1
  remote_temp_path "$path"
  remote_no_stdin "rm -f -- '$path'" || true
}

cleanup_remote_temps() {
  local path
  for path in "${REMOTE_TEMP_PATHS[@]}"; do
    [[ -n "$path" ]] && remove_remote_temp "$path"
  done
  REMOTE_TEMP_PATHS=()
}

root_action_stream() {
  local action=$1 forward_stdin=$2
  shift 2
  printf '%s\n' "$action"
  if (($# > 0)); then
    printf '%s\n' "$@"
  fi
  if [[ "$forward_stdin" == true ]]; then
    printf '%s\n' --
    # Replace the process-substitution shell so the caller can terminate the
    # exact stdin forwarder as soon as the remote TTY command exits.
    exec cat
  fi
}

root_action_tty() {
  local action=$1 forward_stdin=$2
  local input_fifo input_pid input_rc=0 operator_fd remote_rc=0
  shift 2

  [[ -n "$WORK_DIR" && -d "$WORK_DIR" ]] || die 70 'controller work directory is unavailable'
  input_fifo="$WORK_DIR/root-action-input"
  [[ ! -e "$input_fifo" ]] || die 70 'controller input FIFO already exists'
  mkfifo -m 0600 "$input_fifo"
  exec {operator_fd}<&0
  root_action_stream "$action" "$forward_stdin" "$@" <&"$operator_fd" >"$input_fifo" &
  input_pid=$!
  exec {operator_fd}<&-

  (remote_tty_from_fifo "$input_fifo" 'sudo -n /usr/local/libexec/hermes-deploy-root') || remote_rc=$?

  # Reap the independent FIFO producer after the remote command exits. It is
  # deliberately still blocked on the local TTY while forwarding input.
  if kill -0 "$input_pid" 2>/dev/null; then
    kill -TERM "$input_pid" 2>/dev/null || true
  fi
  wait "$input_pid" 2>/dev/null || input_rc=$?
  rm -f -- "$input_fifo"

  ((remote_rc == 0)) || return "$remote_rc"
  case "$input_rc" in
    0 | 141 | 143) return 0 ;;
    *) return "$input_rc" ;;
  esac
}

root_action() {
  local action=$1
  local forward_stdin=false
  local use_tty=false
  shift
  is_fixture && return 0
  case "$action" in
    backup-data)
      for argument in "$@"; do
        if [[ "$argument" == interactive=1 ]]; then
          forward_stdin=true
          use_tty=true
        fi
      done
      ;;
    rollback)
      for argument in "$@"; do
        if [[ "$argument" == restore_data=1 ]]; then
          forward_stdin=true
          use_tty=true
        fi
      done
      ;;
    provider-auth)
      forward_stdin=true
      use_tty=true
      [[ -t 0 ]] || die 75 "$action requires an interactive operator terminal"
      ;;
  esac
  if $use_tty; then
    root_action_tty "$action" "$forward_stdin" "$@"
  else
    root_action_stream "$action" "$forward_stdin" "$@" \
      | remote 'sudo -n /usr/local/libexec/hermes-deploy-root'
  fi
}

root_helper_present() {
  is_fixture && return 0
  remote_no_stdin 'test -x /usr/local/libexec/hermes-deploy-root'
}

root_helper_matches() {
  local expected_helper expected_preflight expected_auth expected_host
  local actual_helper actual_preflight actual_auth actual_host
  is_fixture && return 0
  expected_helper=$(sha256sum "$REMOTE_DIR/remote-state.sh" | awk '{print $1}')
  expected_preflight=$(sha256sum "$REMOTE_DIR/remote-preflight.sh" | awk '{print $1}')
  expected_auth=$(sha256sum "$REMOTE_DIR/provider-auth-status.sh" | awk '{print $1}')
  expected_host=$(sha256sum "$REMOTE_DIR/fedora-server-host.sh" | awk '{print $1}')
  actual_helper=$(remote_no_stdin 'sha256sum /usr/local/libexec/hermes-deploy-root' 2>/dev/null \
    | awk '{print $1}' || true)
  actual_preflight=$(remote_no_stdin 'sha256sum /usr/local/libexec/hermes-preflight' 2>/dev/null \
    | awk '{print $1}' || true)
  actual_auth=$(remote_no_stdin 'sha256sum /usr/local/libexec/hermes-provider-auth-status' 2>/dev/null \
    | awk '{print $1}' || true)
  actual_host=$(remote_no_stdin 'sha256sum /usr/local/libexec/hermes-fedora-server-host' 2>/dev/null \
    | awk '{print $1}' || true)
  [[ "$actual_helper" == "$expected_helper" && "$actual_preflight" == "$expected_preflight" &&
    "$actual_auth" == "$expected_auth" && "$actual_host" == "$expected_host" ]]
}

bootstrap_root_helper() {
  local bootstrap_command helper_digest helper_path preflight_digest preflight_path quoted_bootstrap
  local auth_digest auth_path host_digest host_path
  upload_file "$REMOTE_DIR/remote-state.sh"
  helper_path=$UPLOADED_PATH
  helper_digest=$(sha256sum "$REMOTE_DIR/remote-state.sh" | awk '{print $1}')
  remote_no_stdin "printf '%s  %s\n' '$helper_digest' '$helper_path' | sha256sum -c -"
  upload_file "$REMOTE_DIR/remote-preflight.sh"
  preflight_path=$UPLOADED_PATH
  preflight_digest=$(sha256sum "$REMOTE_DIR/remote-preflight.sh" | awk '{print $1}')
  remote_no_stdin "printf '%s  %s\n' '$preflight_digest' '$preflight_path' | sha256sum -c -"
  upload_file "$REMOTE_DIR/provider-auth-status.sh"
  auth_path=$UPLOADED_PATH
  auth_digest=$(sha256sum "$REMOTE_DIR/provider-auth-status.sh" | awk '{print $1}')
  remote_no_stdin "printf '%s  %s\n' '$auth_digest' '$auth_path' | sha256sum -c -"
  upload_file "$REMOTE_DIR/fedora-server-host.sh"
  host_path=$UPLOADED_PATH
  host_digest=$(sha256sum "$REMOTE_DIR/fedora-server-host.sh" | awk '{print $1}')
  remote_no_stdin "printf '%s  %s\n' '$host_digest' '$host_path' | sha256sum -c -"
  bootstrap_command=$(
    cat <<BOOTSTRAP
set -o errexit
set -o nounset
set -o pipefail
install -d -o root -g root -m 0755 /usr/local/libexec /var/lib/hermes-deploy /etc/sudoers.d
install -o root -g root -m 0755 '$helper_path' /usr/local/libexec/hermes-deploy-root
install -o root -g root -m 0755 '$preflight_path' /usr/local/libexec/hermes-preflight
install -o root -g root -m 0755 '$auth_path' /usr/local/libexec/hermes-provider-auth-status
install -o root -g root -m 0755 '$host_path' /usr/local/libexec/hermes-fedora-server-host
sudoers_file=/etc/sudoers.d/$TARGET_USER-hermes-deploy
printf '%s ALL=(root) NOPASSWD: /usr/local/libexec/hermes-deploy-root ""\n' '$TARGET_USER' >"\$sudoers_file"
chown root:root "\$sudoers_file"
chmod 0440 "\$sudoers_file"
visudo -cf "\$sudoers_file"
rm -f -- '$helper_path'
rm -f -- '$preflight_path'
rm -f -- '$auth_path'
rm -f -- '$host_path'
BOOTSTRAP
  )
  # Run the complete bootstrap under one interactive sudo invocation. This
  # supports hosts whose sudo timestamp is scoped to the active terminal.
  printf -v quoted_bootstrap '%q' "$bootstrap_command"
  remote_tty sudo /usr/bin/bash -c "$quoted_bootstrap"
  root_helper_present || die 70 'temporary root helper was not installed'
}

check_repo_artifacts() {
  local artifact
  local -a artifacts=(
    "$REPO_ROOT/hermes-deploy.sh"
    "$REPO_ROOT/scripts/hermes/deploy-lib.sh"
    "$REMOTE_DIR/remote-state.sh"
    "$REMOTE_DIR/remote-preflight.sh"
    "$REMOTE_DIR/fedora-server-host.sh"
    "$REMOTE_DIR/provider-auth-status.sh"
    "$REMOTE_DIR/certification-evidence.sh"
    "$REMOTE_DIR/promotion-record.sh"
    "$REMOTE_DIR/hermes.container"
    "$REMOTE_DIR/60-hermes-runtime.conf"
    "$REMOTE_DIR/70-hermes-volume-label.conf"
    "$REMOTE_DIR/harden-config.py"
    "$REMOTE_DIR/set-model.py"
    "$REMOTE_DIR/acceptance.sh"
    "$REMOTE_DIR/root-acceptance.sh"
    "$REMOTE_DIR/wrappers/hermes-chat"
    "$REMOTE_DIR/wrappers/hermes-status"
    "$REMOTE_DIR/wrappers/hermes-logs"
  )
  for artifact in "${artifacts[@]}"; do
    [[ -r "$artifact" ]] || {
      error "required artifact is missing: $artifact"
      return 1
    }
  done
  grep -Fxq "Image=$EXPECTED_IMAGE" "$REMOTE_DIR/hermes.container" || {
    error 'canonical Quadlet image pin is not the locked digest'
    return 1
  }
  grep -Fxq 'Pull=never' "$REMOTE_DIR/hermes.container" || {
    error 'canonical Quadlet does not set Pull=never'
    return 1
  }
  ! grep -Eq '(^|[[:space:]])(sk-|ghp_|AKIA[0-9A-Z]{16})' "${artifacts[@]}" || {
    error 'credential-looking literal found in deployment artifacts'
    return 1
  }
  ! grep -R -Eq 'NOPASSWD:[[:space:]]+ALL' "$REMOTE_DIR" || {
    error 'arbitrary sudo access found in Hermes deployment artifacts'
    return 1
  }
}

run_check() {
  local allow_update=${1:-0}
  [[ "$allow_update" == 0 || "$allow_update" == 1 ]] || die 70 'invalid preflight mode'
  check_repo_artifacts || return 1
  if is_fixture; then
    printf 'Preflight passed (fixture transport; no state written)\n'
    return 0
  fi
  debug "running read-only preflight on $TARGET"
  if root_helper_present && root_helper_matches; then
    if root_action preflight "management_cidr=$MANAGEMENT_CIDR" "management_interface=$MANAGEMENT_INTERFACE" \
      "allow_update=$allow_update"; then
      printf 'Preflight passed for %s\n' "$TARGET"
      return 0
    fi
    warn "preflight failed for $TARGET; no deployment state was written"
    return 1
  fi
  if run_remote_preflight "$allow_update"; then
    printf 'Preflight passed for %s\n' "$TARGET"
    return 0
  fi
  warn "preflight failed for $TARGET; no deployment state was written"
  return 1
}

certification_context_is_valid() {
  [[ "${HERMES_CERTIFICATION_MODE-0}" == 1 && "$TARGET" == lab@172.16.99.12 ]]
}

verify_certification_unlock_evidence() {
  local event_log summary
  certification_context_is_valid || return 0
  event_log=${HERMES_CERTIFICATION_UNLOCK_LOG-}
  [[ "$event_log" == /* && -r "$event_log" ]] \
    || die 78 'VM encrypted-boot evidence is missing before provider authentication'
  if ! certification_unlock_evidence_is_valid "$event_log"; then
    summary=$(certification_unlock_evidence_summary "$event_log" || true)
    die 78 "VM encrypted-boot evidence failed closed ($summary)"
  fi
  printf 'ENCRYPTED_REBOOT_EVIDENCE_OK watched_boots=%s\n' \
    "$HERMES_CERTIFICATION_EXPECTED_WATCHED_BOOTS" >&2
}

hermes_reboot_reconnect_attempts() {
  if certification_context_is_valid; then
    # The encrypted certification VM requires a console unlock before SSH can
    # return. Allow ten minutes so the independent unlock monitor can retry.
    printf '600\n'
  else
    printf '300\n'
  fi
}

confirm_production_mutation() {
  certification_context_is_valid && return 0
  if stage_is_complete update update-verified && stage_is_complete hermes-reboot reboot-verified; then
    return 0
  fi
  [[ -t 0 && -r /dev/tty ]] || die 75 'production package mutation requires a typed terminal confirmation'
  local reply
  printf 'This will mutate the production host and perform planned reboots. Type CONFIRM-HERMES-PRODUCTION: ' >&2
  IFS= read -r reply </dev/tty || die 75 'production confirmation was cancelled'
  [[ "$reply" == CONFIRM-HERMES-PRODUCTION ]] || die 75 'production confirmation did not match'
}

confirm_provider_auth_ready() {
  local reply
  certification_context_is_valid || return 0
  verify_certification_unlock_evidence
  [[ -t 0 && -r /dev/tty ]] \
    || die 75 'VM certification provider authentication requires an interactive operator terminal'

  printf 'AUTHENTICATION_READY provider=%s\n' "$PROVIDER" >&2
  if [[ "$PROVIDER" == openai-codex ]]; then
    printf '%s\n' 'The Hermes device login allows 15 minutes after authentication starts.' >&2
  fi
  printf '%s\n' \
    'START-AUTH is a readiness response for this running certification; it is not a Bash command.' >&2
  while true; do
    printf '%s' 'In this same certification terminal, type START-AUTH when you are ready: ' >&2
    IFS= read -r reply </dev/tty \
      || die 75 'provider authentication readiness confirmation was cancelled'
    if [[ "$reply" == START-AUTH ]]; then
      printf 'AUTHENTICATION_OPERATOR_READY provider=%s\n' "$PROVIDER" >&2
      return 0
    fi
    warn 'provider authentication has not started; in this same certification terminal, type START-AUTH exactly when ready'
  done
}

read_host_identity() {
  local output=$1
  PROMOTION_HOST_MACHINE_ID=$(sed -n 's/^machine_id_sha256=//p' <<<"$output" | tail -n 1)
  PROMOTION_HOST_SSH_FINGERPRINT=$(sed -n 's/^ssh_host_ed25519_fingerprint=//p' <<<"$output" | tail -n 1)
  [[ "$PROMOTION_HOST_MACHINE_ID" =~ ^[[:xdigit:]]{64}$ ]] || return 1
  [[ "$PROMOTION_HOST_SSH_FINGERPRINT" =~ ^SHA256:[A-Za-z0-9+/]+={0,2}$ ]]
}

run_promotion_gate() {
  local artifact_fingerprint record_rc host_identity bound_provider bound_model
  local bound_id bound_fingerprint
  certification_context_is_valid && {
    log 'VM certification context: promotion record will be generated after acceptance and cleanup'
    return 0
  }
  [[ -n "$PROMOTION_RECORD" ]] || die 75 'deploy/provider configuration requires --promotion-record'
  [[ "$PROMOTION_RECORD" = /* ]] || die 64 '--promotion-record must be an absolute path'
  artifact_fingerprint=$(promotion_record_fingerprint "$REPO_ROOT") \
    || die 66 'promotion artifact fingerprint cannot be computed'
  set +e
  promotion_record_validate "$PROMOTION_RECORD" "$PROVIDER" "$MODEL" "$EXPECTED_IMAGE" \
    "$artifact_fingerprint"
  record_rc=$?
  set -e
  bound_provider=$(state_read promotion-provider || true)
  bound_model=$(state_read promotion-model || true)
  bound_id=$(state_read promotion-id || true)
  bound_fingerprint=$(state_read promotion-artifact-fingerprint || true)
  host_identity=$(root_action host-identity 2>/dev/null || true)
  read_host_identity "$host_identity" || die 78 'production host identity could not be verified'
  if [[ -n "$bound_id" ]]; then
    [[ "$(state_read host-machine-id-sha256 || true)" == "$PROMOTION_HOST_MACHINE_ID" &&
    "$(state_read host-ssh-fingerprint || true)" == "$PROMOTION_HOST_SSH_FINGERPRINT" ]] \
      || die 78 'promotion record cannot be reused on a different production host'
    if [[ "$bound_provider" == "$PROVIDER" && "$bound_model" == "$MODEL" ]]; then
      [[ "$PROMOTION_ID" == "$bound_id" && "$PROMOTION_ARTIFACT_FINGERPRINT" == "$bound_fingerprint" ]] \
        || die 78 'promotion record does not match the bound deployment'
      if [[ "$record_rc" -ne 0 ]]; then
        [[ "$record_rc" -eq 2 ]] || die 78 'promotion record no longer matches the deployment artifacts'
        log 'resuming the bound deployment with its previously validated promotion record'
        return 0
      fi
    else
      [[ "$record_rc" -eq 0 ]] || die 75 'provider/model change requires a fresh unexpired promotion record'
      log 'binding a recertified provider/model on the same production host'
    fi
  else
    [[ "$record_rc" -eq 0 ]] || {
      [[ "$record_rc" -eq 2 ]] && die 75 'promotion record is expired before first production use'
      die 78 'promotion record does not match the selected deployment inputs'
    }
  fi
  state_write promotion-record "$PROMOTION_RECORD"
  state_write promotion-id "$PROMOTION_ID"
  state_write promotion-provider "$PROMOTION_PROVIDER"
  state_write promotion-model "$PROMOTION_MODEL"
  state_write promotion-artifact-fingerprint "$PROMOTION_ARTIFACT_FINGERPRINT"
  state_write host-machine-id-sha256 "$PROMOTION_HOST_MACHINE_ID"
  state_write host-ssh-fingerprint "$PROMOTION_HOST_SSH_FINGERPRINT"
  state_write promotion-bound-at "$(date -u +%s)"
  printf 'PROMOTION_BOUND id=%s\n' "$PROMOTION_ID"
}
remote_stage_valid() {
  local stage=$1
  root_action validate "$stage"
}

stage_is_complete() {
  local local_stage=$1
  local remote_stage=$2
  if remote_stage_valid "$remote_stage"; then
    if ! state_has "stage-$local_stage"; then
      mark_local_stage "$local_stage"
      log "recovered completed stage marker: $local_stage"
    fi
    log "stage already complete: $local_stage"
    return 0
  fi
  warn "stage drift detected; converging: $local_stage"
  return 1
}

run_simple_stage() {
  local local_stage=$1
  local remote_stage=$2
  local action=$3
  shift 3
  stage_is_complete "$local_stage" "$remote_stage" && return 0
  root_action "$action" "$@"
  mark_local_stage "$local_stage"
  if [[ -v HERMES_DEPLOY_STOP_AFTER_STAGE && "$HERMES_DEPLOY_STOP_AFTER_STAGE" == "$local_stage" ]]; then
    die 75 "deployment paused after stage: $local_stage"
  fi
}

run_data_backup_stage() {
  local backup_rc
  stage_is_complete data-backup data-backup && return 0
  if root_action backup-data; then
    mark_local_stage data-backup
    return 0
  fi
  backup_rc=$?
  [[ "$backup_rc" -eq 75 ]] || die "$backup_rc" 'data backup preparation failed'
  root_action backup-data interactive=1
  mark_local_stage data-backup
}

run_update_stage() {
  stage_is_complete update update-verified && return 0
  if ! stage_is_complete update-staged update-staged; then
    root_action stage-update
    mark_local_stage update-staged
  fi
  if stage_is_complete update update-verified; then
    return 0
  fi
  if [[ "$(root_action offline-pending 2>/dev/null || true)" == no ]]; then
    root_action verify-no-update
    mark_local_stage update
    return 0
  fi
  warn 'The host will reboot to apply the prepared Fedora Server DNF5 offline transaction.'
  warn 'Rollback restores Hermes and tracked configuration only; RPM and kernel updates are not reversed.'
  root_action offline-reboot || true
  # A fresh Server VM can spend several minutes applying hundreds of RPMs in
  # the offline environment before SSH is available again.  Keep the normal
  # reboot wait bounded at five minutes, but allow the planned Fedora update
  # reboot fifteen minutes to complete before declaring it failed.
  wait_for_reconnect 900 || die 69 'host did not return after the Fedora Server update reboot'
  root_action verify-update
  mark_local_stage update
}

run_host_policy_stage() {
  local canary_rc=0
  stage_is_complete host-policy host-policy && return 0
  if ! root_action host-policy; then
    warn 'Host policy application failed; restoring the manifest through the original control connection.'
    root_action rollback-host || true
    die 69 'host policy application failed; host policy was restored'
  fi
  if [[ -v HERMES_DEPLOY_FORCE_CANARY_FAILURE && "$HERMES_DEPLOY_FORCE_CANARY_FAILURE" == 1 ]]; then
    canary_rc=1
  elif remote_without_control true >/dev/null 2>&1; then
    canary_rc=0
  else
    canary_rc=1
  fi
  if ((canary_rc == 0)); then
    mark_local_stage host-policy
    return 0
  fi
  warn 'The SSH canary failed; restoring the manifest through the original control connection.'
  root_action rollback-host || true
  die 69 'SSH canary failed after host policy; host policy was restored'
}

sync_runtime_helpers() {
  local acceptance_path root_acceptance_path
  upload_file "$REMOTE_DIR/acceptance.sh"
  acceptance_path=$UPLOADED_PATH
  upload_file "$REMOTE_DIR/root-acceptance.sh"
  root_acceptance_path=$UPLOADED_PATH

  root_action install-runtime-helpers "acceptance_path=$acceptance_path" \
    "root_acceptance_path=$root_acceptance_path"
  cleanup_remote_temps
}

run_runtime_stage() {
  local unit_path runtime_path volume_path
  sync_runtime_helpers
  stage_is_complete runtime runtime-credential-free && return 0

  upload_file "$REMOTE_DIR/hermes.container"
  unit_path=$UPLOADED_PATH
  upload_file "$REMOTE_DIR/60-hermes-runtime.conf"
  runtime_path=$UPLOADED_PATH
  upload_file "$REMOTE_DIR/70-hermes-volume-label.conf"
  volume_path=$UPLOADED_PATH

  root_action install-runtime "unit_path=$unit_path" "runtime_dropin_path=$runtime_path" \
    "volume_dropin_path=$volume_path"
  cleanup_remote_temps
  mark_local_stage runtime
}

run_hardening_stage() {
  local harden_path
  stage_is_complete hardening hardening && return 0
  upload_file "$REMOTE_DIR/harden-config.py"
  harden_path=$UPLOADED_PATH
  root_action apply-hardening "harden_path=$harden_path"
  remove_remote_temp "$harden_path"
  mark_local_stage hardening
}

run_acceptance_stage() {
  local mode=$1
  local acceptance_stage=$2
  stage_is_complete "$acceptance_stage" "$acceptance_stage" && return 0
  root_action acceptance "mode=$mode"
  root_action root-acceptance
  mark_local_stage "$acceptance_stage"
}

provider_configuration_is_current() {
  root_action validate-provider "provider=$PROVIDER" "model=$MODEL" >/dev/null 2>&1 || return 1
  stage_is_complete inference-acceptance inference-acceptance
}

rollback_provider_switch() {
  local previous_provider=$1
  local previous_model=$2
  local candidate_provider=$3
  local model_path=${4:-}

  warn "provider acceptance failed for $candidate_provider; restoring the previous provider configuration"
  if [[ -n "$previous_provider" && -n "$previous_model" ]]; then
    if [[ -n "$model_path" ]]; then
      root_action set-model "model_path=$model_path" "provider=$previous_provider" "model=$previous_model" || true
    fi
    root_action acceptance "mode=provider" "provider=$previous_provider" "model=$previous_model" >/dev/null 2>&1 || true
    state_write provider "$previous_provider"
    state_write model "$previous_model"
    if [[ "$candidate_provider" != "$previous_provider" ]]; then
      root_action revoke-auth "provider=$candidate_provider" || true
    fi
  else
    root_action revoke-auth "provider=$candidate_provider" || true
  fi
}

run_hermes_reboot_stage() {
  local reconnect_seconds
  if stage_is_complete hermes-reboot reboot-verified; then
    run_acceptance_stage credential-free post-reboot-credential-free
    return 0
  fi
  reconnect_seconds=$(hermes_reboot_reconnect_attempts)
  root_action reboot || true
  wait_for_reconnect "$reconnect_seconds" \
    || die 69 'host did not return after the credential-free Hermes reboot'
  root_action verify-reboot
  mark_local_stage hermes-reboot
  run_acceptance_stage credential-free post-reboot-credential-free
}

run_provider_stage() {
  local harden_path model_path previous_provider previous_model
  previous_provider=$(existing_provider)
  previous_model=$(existing_model)
  if provider_configuration_is_current; then
    if ! root_action prune-auth "active_provider=$PROVIDER"; then
      die 78 'provider credential cleanup failed; deployment was not finalized'
    fi
    state_write provider "$PROVIDER"
    state_write model "$MODEL"
    return 0
  fi

  if ! root_action validate-provider-auth "provider=$PROVIDER" >/dev/null 2>&1; then
    confirm_provider_auth_ready
    if ! root_action provider-auth "provider=$PROVIDER"; then
      rollback_provider_switch "$previous_provider" "$previous_model" "$PROVIDER"
      die 78 'provider authentication failed; previous provider configuration was restored'
    fi
  fi
  mark_local_stage oauth

  upload_file "$REMOTE_DIR/harden-config.py"
  harden_path=$UPLOADED_PATH
  if ! root_action apply-hardening "harden_path=$harden_path"; then
    rollback_provider_switch "$previous_provider" "$previous_model" "$PROVIDER"
    die 78 'post-auth hardening failed; previous provider configuration was restored'
  fi
  remove_remote_temp "$harden_path"
  mark_local_stage post-auth-hardening

  upload_file "$REMOTE_DIR/set-model.py"
  model_path=$UPLOADED_PATH
  if ! root_action set-model "model_path=$model_path" "provider=$PROVIDER" "model=$MODEL"; then
    rollback_provider_switch "$previous_provider" "$previous_model" "$PROVIDER" "$model_path"
    die 78 'provider model configuration failed; previous provider configuration was restored'
  fi
  mark_local_stage model-configured

  if ! root_action acceptance "mode=provider" "provider=$PROVIDER" "model=$MODEL"; then
    rollback_provider_switch "$previous_provider" "$previous_model" "$PROVIDER" "$model_path"
    die 78 'provider acceptance failed; previous provider configuration was restored'
  fi
  root_action root-acceptance || {
    rollback_provider_switch "$previous_provider" "$previous_model" "$PROVIDER" "$model_path"
    die 78 'root acceptance failed after provider configuration; previous provider configuration was restored'
  }
  if ! root_action acceptance "mode=inference" "provider=$PROVIDER" "model=$MODEL"; then
    rollback_provider_switch "$previous_provider" "$previous_model" "$PROVIDER" "$model_path"
    die 78 'authenticated inference failed; previous provider configuration was restored'
  fi
  mark_local_stage provider-acceptance
  mark_local_stage inference-acceptance
  if ! root_action prune-auth "active_provider=$PROVIDER"; then
    rollback_provider_switch "$previous_provider" "$previous_model" "$PROVIDER" "$model_path"
    die 78 'provider credential cleanup failed; previous provider configuration was restored'
  fi
  state_write provider "$PROVIDER"
  state_write model "$MODEL"
}

run_close_stage() {
  local chat_path status_path logs_path force=${1:-0}
  if [[ "$force" == 0 ]] && stage_is_complete closed closed; then
    return 0
  fi

  upload_file "$REMOTE_DIR/wrappers/hermes-chat"
  chat_path=$UPLOADED_PATH
  upload_file "$REMOTE_DIR/wrappers/hermes-status"
  status_path=$UPLOADED_PATH
  upload_file "$REMOTE_DIR/wrappers/hermes-logs"
  logs_path=$UPLOADED_PATH
  root_action install-wrappers "chat_path=$chat_path" "status_path=$status_path" "logs_path=$logs_path"
  cleanup_remote_temps
  mark_local_stage wrappers
  root_action close
  mark_local_stage closed
  TEMP_HELPER_BOOTSTRAPPED=false
}

status_drift_reasons() {
  local status_output=$1 reasons
  reasons=$(sed -n 's/.*drift_reasons=\([^[:space:]]*\).*/\1/p' <<<"$status_output" | tail -n 1)
  if [[ "$reasons" == none ||
    "$reasons" =~ ^[a-z][a-z0-9-]*(,[a-z][a-z0-9-]*)*$ ]]; then
    printf '%s\n' "$reasons"
  else
    printf 'unknown\n'
  fi
}

status_command() {
  local failure_reasons phase target_line remote_status status_file status_rc
  phase=$(state_read current-phase || true)
  target_line=$(state_read target || true)
  [[ -n "$phase" ]] || phase=not-started
  [[ -n "$target_line" ]] || target_line=$TARGET
  printf 'phase=%s\n' "$phase"
  printf 'target=%s\n' "$target_line"

  if is_fixture; then
    printf 'service_health=fixture-healthy\n'
    printf 'platform=fedora-server-44\n'
    printf 'host_identity=unbound\n'
    printf 'update_policy=download-only\n'
    printf 'promotion_id=unconfigured\n'
    printf 'provider=unconfigured\n'
    printf 'model=unconfigured\n'
    printf 'provider_auth=unconfigured\n'
    printf 'image_pin=%s\n' "$EXPECTED_IMAGE"
    printf 'drift=none\n'
    return 0
  fi

  if root_helper_present; then
    root_action status
    return
  fi

  status_file=$(mktemp)
  chmod 0600 "$status_file"
  remote_tty 'sudo -n /usr/local/bin/hermes-status' </dev/null >"$status_file" 2>/dev/null || status_rc=$?
  status_rc=${status_rc:-0}
  remote_status=$(sed -n '1,20p' "$status_file")
  rm -f -- "$status_file"
  if [[ -n "$remote_status" ]]; then
    printf '%s\n' "$remote_status"
  fi
  [[ "$status_rc" -eq 0 ]] && return 0
  failure_reasons=$(status_drift_reasons "$remote_status")
  printf 'STATUS_FAILED exit_code=%d drift_reasons=%s\n' "$status_rc" "$failure_reasons" >&2
  return "$status_rc"
}

wait_for_post_close_status() {
  local attempt failure_reasons status_output status_rc
  for ((attempt = 1; attempt <= POST_CLOSE_STATUS_ATTEMPTS; attempt++)); do
    status_rc=0
    status_output=$(status_command 2>/dev/null) || status_rc=$?
    if ((status_rc == 0)); then
      printf '%s\n' "$status_output"
      return 0
    fi
    if ((attempt < POST_CLOSE_STATUS_ATTEMPTS)); then
      sleep "$POST_CLOSE_STATUS_INTERVAL_SECONDS"
    fi
  done
  [[ -z "$status_output" ]] || printf '%s\n' "$status_output"
  failure_reasons=$(status_drift_reasons "$status_output")
  warn "post-close status did not converge after $POST_CLOSE_STATUS_ATTEMPTS attempts (last exit=$status_rc drift_reasons=$failure_reasons)"
  return "$status_rc"
}

ensure_root_helper() {
  if root_helper_present && root_helper_matches; then
    TEMP_HELPER_BOOTSTRAPPED=true
    return 0
  fi
  root_helper_present && warn 'remote deployment helper drifted; replacing it from the checked-in artifact'
  bootstrap_root_helper
  TEMP_HELPER_BOOTSTRAPPED=true
}

remove_temporary_root_helper() {
  $TEMP_HELPER_BOOTSTRAPPED || return 0
  root_action remove-helper || true
  TEMP_HELPER_BOOTSTRAPPED=false
}

deploy_command() {
  check_repo_artifacts || die 66 'local deployment artifacts are incomplete'
  if state_has stage-closed && ! is_fixture && [[ -z "$PROVIDER" && -z "$MODEL" ]]; then
    if status_command >/dev/null 2>&1; then
      log 'deployment is already closed and healthy; no changes required'
      return 0
    fi
  fi
  is_fixture && die 78 'fixture transport is read-only and cannot execute deploy'

  if state_has stage-closed; then
    configure_provider_command
    return
  fi

  start_control_master
  if ! root_helper_present; then
    ensure_sudo_session
  fi
  run_check 1 || die 78 'read-only preflight failed; no deployment mutation was started'
  resolve_provider_selection
  init_state
  ensure_root_helper
  run_promotion_gate
  confirm_production_mutation
  run_simple_stage site-configured site-configured configure-site "$TARGET_USER" "$MANAGEMENT_CIDR" "$MANAGEMENT_INTERFACE"
  run_simple_stage manifest manifest create-manifest
  run_data_backup_stage
  run_simple_stage prerequisites prerequisites install-prerequisites
  run_host_policy_stage
  run_update_stage
  run_simple_stage identity identity identity
  run_runtime_stage
  run_hardening_stage
  run_acceptance_stage credential-free credential-free-acceptance
  run_hermes_reboot_stage
  run_provider_stage
  run_close_stage
  cleanup_remote_temps
  wait_for_post_close_status
}

configure_provider_command() {
  check_repo_artifacts || die 66 'local deployment artifacts are incomplete'
  [[ -d "$STATE_DIR" ]] || die 66 'no local deployment state exists for this target'
  is_fixture && die 78 'fixture transport is read-only and cannot configure a provider'

  start_control_master
  run_check 1 || die 78 'read-only preflight failed; no provider mutation was started'
  resolve_provider_selection
  ensure_root_helper
  run_promotion_gate
  sync_runtime_helpers
  stage_is_complete runtime runtime-credential-free || die 78 'managed Hermes runtime is not ready for provider configuration'
  run_provider_stage
  run_close_stage 1
  cleanup_remote_temps
  wait_for_post_close_status
}

revoke_auth_command() {
  [[ -d "$STATE_DIR" ]] || die 66 'no local deployment state exists for this target'
  is_fixture && die 78 'fixture transport cannot revoke auth'
  start_control_master
  ensure_root_helper
  resolve_provider_selection
  root_action revoke-auth "provider=$PROVIDER"
  mark_local_stage auth-revoked
  remove_temporary_root_helper
  cleanup_remote_temps
  printf '%s authentication revoked; Hermes data was retained.\n' "$PROVIDER"
}

rollback_command() {
  local purge_value=0 restore_data=0 backup_status
  [[ -d "$STATE_DIR" ]] || die 66 'no local deployment state exists for this target'
  is_fixture && die 78 'fixture transport cannot rollback'
  if $PURGE_FRESH; then
    printf 'Type PURGE-HERMES-FRESH to remove only installer-created identity/data: ' >&2
    IFS= read -r purge_value
    [[ "$purge_value" == PURGE-HERMES-FRESH ]] || die 75 'fresh purge cancelled'
    purge_value=1
  fi
  start_control_master
  ensure_root_helper
  backup_status=$(root_action backup-present 2>/dev/null || true)
  if [[ "$backup_status" == *BACKUP_PRESENT* ]]; then
    [[ -t 0 ]] || die 75 'rollback needs an interactive terminal to restore the encrypted data backup'
    restore_data=1
  fi
  root_action rollback "purge=$purge_value" "restore_data=$restore_data"
  if ((purge_value)); then
    reset_local_state_after_rollback
  else
    mark_local_stage rollback
  fi
  remove_temporary_root_helper
  cleanup_remote_temps
  printf 'Rollback complete. Hermes data was retained unless --purge-fresh was explicitly selected; RPM and kernel updates were not reversed.\n'
}

reset_local_state_after_rollback() {
  local state_file
  local -a stale_state=(
    current-phase
    provider
    model
    promotion-record
    promotion-id
    promotion-provider
    promotion-model
    promotion-artifact-fingerprint
    promotion-bound-at
    host-machine-id-sha256
    host-ssh-fingerprint
  )

  for state_file in "${STATE_DIR}"/stage-*; do
    rm -f -- "$state_file"
  done
  for state_file in "${stale_state[@]}"; do
    rm -f -- "${STATE_DIR}/${state_file}"
  done
  init_state
  mark_local_stage rollback
}

adopt_host_command() {
  local host_identity archive legacy_root reply
  is_fixture && die 78 'fixture transport cannot adopt a host'
  [[ -t 0 && -r /dev/tty ]] || die 75 'adopt-host requires a typed confirmation terminal'
  host_identity=$(remote_without_control \
    'cd /tmp && sha256sum /etc/machine-id && ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub -E sha256') \
    || die 69 'could not read the reinstalled host identity'
  PROMOTION_HOST_MACHINE_ID=$(awk 'NR == 1 {print $1}' <<<"$host_identity")
  PROMOTION_HOST_SSH_FINGERPRINT=$(awk 'NR == 2 {for (i = 1; i <= NF; i++) if ($i ~ /^SHA256:/) {print $i; exit}}' \
    <<<"$host_identity")
  [[ "$PROMOTION_HOST_MACHINE_ID" =~ ^[[:xdigit:]]{64}$ ]] || die 78 'host machine-id hash is invalid'
  [[ "$PROMOTION_HOST_SSH_FINGERPRINT" =~ ^SHA256:[A-Za-z0-9+/]+={0,2}$ ]] \
    || die 78 'host SSH ED25519 fingerprint is invalid'
  printf 'Verified host identity: machine-id-sha256=%s ssh-ed25519=%s\n' \
    "$PROMOTION_HOST_MACHINE_ID" "$PROMOTION_HOST_SSH_FINGERPRINT" >&2
  printf 'Confirm this is the reinstalled production host. Type ADOPT-HERMES-HOST: ' >&2
  IFS= read -r reply </dev/tty || die 75 'host adoption was cancelled'
  [[ "$reply" == ADOPT-HERMES-HOST ]] || die 75 'host adoption confirmation did not match'
  legacy_root="${HOME:-}/hermes-deploy"
  if [[ -d "$legacy_root" && "$legacy_root" != "$STATE_ROOT" ]]; then
    archive="${legacy_root}.archive-$(date -u +%Y%m%dT%H%M%SZ)"
    mv -- "$legacy_root" "$archive"
    log "archived legacy deployment state at $archive"
  fi
  if [[ -d "$STATE_DIR" ]]; then
    [[ "$(state_read host-machine-id-sha256 || true)" == "$PROMOTION_HOST_MACHINE_ID" &&
    "$(state_read host-ssh-fingerprint || true)" == "$PROMOTION_HOST_SSH_FINGERPRINT" ]] \
      || die 78 'existing XDG deployment state belongs to another host'
  fi
  init_state
  state_write host-machine-id-sha256 "$PROMOTION_HOST_MACHINE_ID"
  state_write host-ssh-fingerprint "$PROMOTION_HOST_SSH_FINGERPRINT"
  state_write platform fedora-server-44
  state_write adopted-at "$(date -u +%s)"
  printf 'HOST_ADOPTED target=%s\n' "$TARGET"
}

cleanup() {
  local rc=$?
  if $TEMP_HELPER_BOOTSTRAPPED; then
    root_action remove-helper >/dev/null 2>&1 || true
    TEMP_HELPER_BOOTSTRAPPED=false
  fi
  cleanup_remote_temps >/dev/null 2>&1 || true
  if [[ -n "$CONTROL_SOCKET" && -S "$CONTROL_SOCKET" ]]; then
    ssh "${SSH_OPTIONS[@]}" -S "$CONTROL_SOCKET" -O exit "$TARGET" >/dev/null 2>&1 || true
  fi
  if [[ -n "$WORK_DIR" && -d "$WORK_DIR" ]]; then
    rm -rf -- "$WORK_DIR"
  fi
  return "$rc"
}

trap cleanup EXIT
trap 'trap - INT EXIT; cleanup; kill -INT $$' INT
trap 'trap - TERM EXIT; cleanup; kill -TERM $$' TERM
trap 'printf "ERROR: %s:%d: %q exited %d\n" "$BASH_SOURCE" "$LINENO" "$BASH_COMMAND" "$?" >&2' ERR

main() {
  parse_args "$@"
  validate_options
  configure_ssh
  case "$COMMAND" in
    check)
      if ! is_fixture; then
        start_control_master
      fi
      run_check 0
      ;;
    status) status_command ;;
    deploy) deploy_command ;;
    configure-provider) configure_provider_command ;;
    revoke-auth) revoke_auth_command ;;
    rollback) rollback_command ;;
    adopt-host) adopt_host_command ;;
    *) die 64 "unsupported command: $COMMAND" ;;
  esac
}
