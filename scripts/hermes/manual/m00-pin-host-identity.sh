#!/usr/bin/env bash
# Bootstrap: write the root-owned host identity pin used by every later helper.
#
# This exists because sudo resets the environment: a sudo-invoked helper cannot see
# HERMES_EXPECT_MACHINE_ID_SHA256, so the binding must live in a root-owned file.
# It is the one deliberate bootstrap exception: it records the host it runs on.
#
# Default is inspect-only; run with --apply once, as root:
#   sudo bash ~/hermes-manual/m00-pin-host-identity.sh --apply
set -u
set -o pipefail
export LC_ALL=C

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib-manual-common.sh
. "$HERE/lib-manual-common.sh" || {
  printf 'STOP: cannot load %s/lib-manual-common.sh (stage the whole manual/ tree)\n' "$HERE" >&2
  exit 1
}

mp_parse_mode "$@"
mp_require_apply 'would record this host identity in the root-owned pin file'
[ "$(id -u)" -eq 0 ] || mp_die "run with sudo: the pin file must be root-owned"
mp_install_trap

ADMIN_ACCOUNT=$(mp_admin_account)
[ "$(id -u "$ADMIN_ACCOUNT")" -ne 0 ] || mp_die "the administrator account must not be root"

current=$(mp_host_identity_sha256)
echo "host_identity_sha256=$current"
if [ -r "$MP_HOST_IDENTITY_FILE" ]; then
  echo "existing pin=$(tr -d '[:space:]' <"$MP_HOST_IDENTITY_FILE")"
else
  echo "existing pin=none"
fi
mp_pin_host_identity
echo "verified_pin=$(tr -d '[:space:]' <"$MP_HOST_IDENTITY_FILE")"
[ "$(tr -d '[:space:]' <"$MP_HOST_IDENTITY_FILE")" = "$current" ] \
  || mp_die "the pin file does not match this host after writing"
echo "RESULT=PASS host identity pinned; later helpers can be run through sudo"
