# shellcheck shell=bash
# Prompt-gated LUKS console interface for the disposable Hermes VM.

[[ -n "${_HERMES_LUKS_CONSOLE_LOADED:-}" ]] && return 0
readonly _HERMES_LUKS_CONSOLE_LOADED=1

HERMES_LUKS_CONSOLE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
readonly HERMES_LUKS_CONSOLE_DIR
readonly HERMES_LUKS_CONSOLE_HELPER="$HERMES_LUKS_CONSOLE_DIR/hermes-luks-console.py"

_hermes_luks_console_run() {
  local mode=$1
  local vm_name=$2
  local virsh_uri=$3
  local timeout_seconds=$4
  local event_log=$5
  local ready_file=${6:-}
  local -a helper_args=(
    --domain "$vm_name"
    --uri "$virsh_uri"
    --timeout "$timeout_seconds"
    --event-log "$event_log"
  )

  [[ "$timeout_seconds" =~ ^[1-9][0-9]*$ ]] || return 64
  [[ -n "$ready_file" ]] && helper_args+=(--ready-file "$ready_file")
  [[ "$mode" == watch ]] && helper_args+=(--watch)
  python3 "$HERMES_LUKS_CONSOLE_HELPER" "${helper_args[@]}"
}

hermes_luks_console_unlock() {
  _hermes_luks_console_run unlock "$@"
}

hermes_luks_console_watch() {
  _hermes_luks_console_run watch "$@"
}
