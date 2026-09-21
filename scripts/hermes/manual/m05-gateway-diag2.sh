#!/usr/bin/env bash
# M05 diagnostic 2 (corrected redaction): capture the actual service logs and the
# output of the gateway subcommands that were previously discarded.
#
# Run as root on the Hermes host:
#   sudo bash /home/aicowork/hermes-m05-gateway-diag2.sh
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
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m05-gateway-diag2.out")
HERMES_UID=$(id -u hermes)
STATE=/home/hermes/gateway-state
GWSSH=/home/hermes/gateway-ssh
GW_IMAGE=docker.io/nousresearch/hermes-agent@sha256:9469b3e78b9545b6d576eb8887a95352e9a0ea83730eaf31431cf862ca1010e1
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

show() {
  label="$1"
  shift
  echo "===== $label ====="
  "$@" 2>&1 | mp_redact_stream "$STATE/.env" | tail -n 70
  echo
}

rc=0
{
  echo "### M05 gateway diagnostic 2"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  echo "===== profile state that could block a second dispatcher ====="
  # A human-readable listing with labels and sizes is the point here.
  # shellcheck disable=SC2012
  ls -la "$STATE" 2>&1 | head -n 25
  find "$STATE" -maxdepth 3 \( -name '*.pid' -o -name '*.lock' -o -name '*gateway*' \) 2>/dev/null | head -n 20
  echo

  show "gateway status (one-shot, output preserved)" \
    h timeout 60 podman run --rm -v "$STATE":/opt/data:z \
    -v /home/hermes/transport:/run/hermes-transport:z \
    -v "$GWSSH":/opt/hermes/gateway-ssh:ro,Z \
    -v "$GWSSH/ssh":/opt/hermes/bin/ssh:ro,Z \
    -v "$GWSSH/scp":/opt/hermes/bin/scp:ro,Z \
    -v "$GWSSH/sftp":/opt/hermes/bin/sftp:ro,Z \
    "$GW_IMAGE" gateway status

  show "gateway run --no-supervise (previously rc 1, output lost)" \
    h timeout 45 podman run --rm -v "$STATE":/opt/data:z \
    -v /home/hermes/transport:/run/hermes-transport:z \
    -v "$GWSSH":/opt/hermes/gateway-ssh:ro,Z \
    -v "$GWSSH/ssh":/opt/hermes/bin/ssh:ro,Z \
    -v "$GWSSH/scp":/opt/hermes/bin/scp:ro,Z \
    -v "$GWSSH/sftp":/opt/hermes/bin/sftp:ro,Z \
    "$GW_IMAGE" gateway run --no-supervise

  echo "===== start the real service and wait 40s ====="
  h systemctl --user reset-failed hermes-gateway.service 2>/dev/null || true
  h systemctl --user start hermes-gateway.service
  echo "start_rc=$?"
  sleep 40
  echo "service_state=$(h systemctl --user is-active hermes-gateway.service)"
  echo

  show "service journal (last 120 lines, container stdout is forwarded here)" \
    h journalctl --user -u hermes-gateway.service -n 120 --no-pager

  echo "===== containers after the attempt ====="
  h podman ps -a --format '{{.Names}} | {{.Status}} | ports=[{{.Ports}}]'
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
