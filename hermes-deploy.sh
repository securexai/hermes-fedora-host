#!/usr/bin/env bash
# Hermes one-command workstation deployment controller.

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s nullglob

if ((BASH_VERSINFO[0] < 5 || (BASH_VERSINFO[0] == 5 && BASH_VERSINFO[1] < 3))); then
  printf 'ERROR: This script requires Bash 5.3+. Current: %s\n' "$BASH_VERSION" >&2
  exit 69
fi

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
readonly SCRIPT_DIR
# Keep the legacy interactive transport separate from the enrolled protocol.
# Explicit opt-in is required: the new path must never fall back to a sudo prompt.
for argument in "$@"; do
  if [[ "$argument" == --non-interactive ]]; then
    exec python3 "$SCRIPT_DIR/scripts/hermes/unattended/controller.py" "$@"
  fi
done
readonly DEPLOY_LIBRARY="$SCRIPT_DIR/scripts/hermes/deploy-lib.sh"
[[ -r "$DEPLOY_LIBRARY" ]] || {
  printf 'ERROR: deployment library not readable: %s\n' "$DEPLOY_LIBRARY" >&2
  exit 66
}

# shellcheck disable=SC1090
source "$DEPLOY_LIBRARY"
main "$@"
