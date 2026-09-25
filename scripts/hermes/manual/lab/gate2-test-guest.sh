#!/usr/bin/env bash
# Installed root-owned under /usr/local/libexec/hermes-gate2-test in the guest.
# Every invoked helper and its transitive bundle are root-owned at the same path.
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin LC_ALL=C

BASE=/usr/local/libexec/hermes-gate2-test
PIN=/etc/hermes-gate2-test/machine-id.sha256
die() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
[[ $# == 1 ]] || die 'exactly one operation is required'
case "$1" in
  worker-key) helper=provision-worker-client-key.sh; args=() ;;
  m02) helper=m02-deploy-and-validate.sh; args=(--apply) ;;
  m03-activate) helper=m03-activate.sh; args=(--apply) ;;
  m03-configure) helper=m03-configure-and-probe.sh; args=(--apply) ;;
  m03-contract) helper=m03-contract.sh; args=(--apply) ;;
  m04-posture) helper=m04-posture.sh; args=(--apply) ;;
  m04-backup) helper=m04-backup.sh; args=(--apply) ;;
  *) die 'operation denied' ;;
esac
[[ $(id -u) == 0 && ${SUDO_USER:-} == aicowork ]] || die 'wrong invoking identity'
[[ -f $PIN && ! -L $PIN && $(stat -c %U "$PIN") == root ]] || die 'identity pin is not trusted'
[[ -z $(find "$PIN" -maxdepth 0 -perm /022 -print -quit) ]] || die 'identity pin is writable'
want=$(cat "$PIN")
[[ $want =~ ^[[:xdigit:]]{64}$ ]] || die 'invalid identity pin'
got=$(sha256sum /etc/machine-id | awk '{print $1}')
[[ $want == "$got" ]] || die 'guest identity mismatch'
[[ -d $BASE/bundle && ! -L $BASE/bundle && $(stat -c %U "$BASE/bundle") == root ]] || die 'bundle is not trusted'
[[ -z $(find "$BASE/bundle" -perm /022 -print -quit) ]] || die 'bundle is writable'
[[ -z $(find "$BASE/bundle" -type l -print -quit) ]] || die 'bundle contains a symlink'
[[ -z $(find "$BASE/bundle" ! -user root -print -quit) ]] || die 'bundle is not root-owned'
[[ -f $BASE/bundle/$helper && ! -L $BASE/bundle/$helper ]] || die 'helper is missing'

/usr/bin/logger -t hermes-gate2-test -- "guest action=$1 result=start"
if /usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root LC_ALL=C TERM=xterm \
  HERMES_EXPECT_MACHINE_ID_SHA256="$want" \
  /usr/bin/bash "$BASE/bundle/$helper" "${args[@]}"; then
  /usr/bin/logger -t hermes-gate2-test -- "guest action=$1 result=success"
else
  rc=$?
  /usr/bin/logger -t hermes-gate2-test -- "guest action=$1 result=failed rc=$rc"
  exit "$rc"
fi
