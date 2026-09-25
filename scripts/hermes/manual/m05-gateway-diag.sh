#!/usr/bin/env bash
# M05 diagnostic: find why `hermes gateway run` exits instead of staying up.
#
# Runs disposable foreground probes in the pinned image with the service's real
# mounts and egress, capturing output with a timeout. Every probe's output is
# filtered so no credential value is printed.
#
# Run as root on the Hermes host:
#   sudo bash /home/aicowork/hermes-m05-gateway-diag.sh
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

ADMIN_ACCOUNT=$(mp_admin_account)
ADMIN_HOME=$(mp_admin_home)
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m05-gateway-diag.out")
HERMES_UID=$(id -u hermes)
STATE=/home/hermes/gateway-state
GWSSH=/home/hermes/gateway-ssh
GW_IMAGE=docker.io/nousresearch/hermes-agent@sha256:fca358f12efd65bfaaca05884166f15c0e2788375ca30d77061ac1ebc96452b7

redact() {
  mp_redact_stream "$STATE/.env"
}

h() {
  if ! mountpoint -q /home/hermes; then
    printf 'STOP: /home/hermes is not mounted.\n' >&2
    return 1
  fi
  sudo -u hermes -- env -i --chdir=/home/hermes \
    HOME=/home/hermes USER=hermes LOGNAME=hermes PATH=/usr/local/bin:/usr/bin:/bin \
    TERM="${TERM:-xterm}" XDG_RUNTIME_DIR="/run/user/$HERMES_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$HERMES_UID/bus" \
    TMPDIR=/home/hermes/.cache/podman-tmp "$@"
}

probe() {
  label="$1"
  shift
  echo "===== $label ====="
  out=$(h timeout 50 podman run --rm \
    -v "$STATE":/opt/data:z \
    -v /home/hermes/transport:/run/hermes-transport:z \
    -v "$GWSSH":/opt/hermes/gateway-ssh:ro,Z \
    -v "$GWSSH/ssh":/opt/hermes/bin/ssh:ro,Z \
    -v "$GWSSH/scp":/opt/hermes/bin/scp:ro,Z \
    -v "$GWSSH/sftp":/opt/hermes/bin/sftp:ro,Z \
    "$GW_IMAGE" "$@" 2>&1)
  rc=$?
  printf '%s\n' "$out" | redact | tail -n 60
  case "$rc" in
    124) echo "probe_rc=124 (still running at timeout - this variant STAYS UP)" ;;
    *) echo "probe_rc=$rc (exited on its own)" ;;
  esac
  echo
}

rc=0
{
  echo "### M05 gateway diagnostic"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  probe "gateway status" gateway status
  probe "gateway run (default/supervised)" gateway run
  probe "gateway run --no-supervise" gateway run --no-supervise
  probe "gateway run --force" gateway run --force
  echo "===== service unit state ====="
  h systemctl --user status hermes-gateway.service --no-pager 2>&1 | head -n 18
  echo
  echo "===== recent AVC denials ====="
  ausearch -m AVC,USER_AVC -ts recent 2>&1 | tail -n 20
  echo
  echo "===== done ====="
} 2>&1 | tee "$OUT" >/dev/null || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null
chmod 600 "$OUT"
echo "WROTE=$OUT"
echo "diagnostic_rc=${rc:-0}"
