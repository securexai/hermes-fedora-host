#!/usr/bin/env bash
# shellcheck shell=bash
# Compatibility entrypoint. The deployment controller is the single state engine
# for fresh installs, managed resumes, and manual-container cutovers.

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

if [[ $# -gt 0 && ("$1" == -h || "$1" == --help) ]]; then
  exec "$SCRIPT_DIR/hermes-deploy.sh" --help
fi

if [[ -z "${HERMES_SSH_TARGET-}" && -z "${HERMES_SSH_KEY-}" &&
  -z "${HERMES_MGMT_SUBNET-}" && -z "${HERMES_IFACE-}" && -z "${HERMES_ADMIN_USER-}" ]]; then
  exec "$SCRIPT_DIR/hermes-deploy.sh" deploy "$@"
fi

declare -a COMPAT_ARGS=()
if [[ -n "${HERMES_SSH_TARGET-}" ]]; then
  COMPAT_ARGS+=(--target "$HERMES_SSH_TARGET")
fi
if [[ -n "${HERMES_SSH_KEY-}" ]]; then
  COMPAT_ARGS+=(--identity-file "$HERMES_SSH_KEY")
fi
if [[ -n "${HERMES_MGMT_SUBNET-}" ]]; then
  COMPAT_ARGS+=(--management-cidr "$HERMES_MGMT_SUBNET")
fi
if [[ -n "${HERMES_IFACE-}" ]]; then
  COMPAT_ARGS+=(--interface "$HERMES_IFACE")
fi
if [[ -n "${HERMES_ADMIN_USER-}" ]]; then
  compat_target=${HERMES_SSH_TARGET:-aicowork@10.0.30.10}
  [[ "${compat_target%%@*}" == "$HERMES_ADMIN_USER" ]] || {
    printf 'ERROR: HERMES_ADMIN_USER must match the USER portion of HERMES_SSH_TARGET\n' >&2
    exit 64
  }
fi

exec "$SCRIPT_DIR/hermes-deploy.sh" deploy "${COMPAT_ARGS[@]}" "$@"
