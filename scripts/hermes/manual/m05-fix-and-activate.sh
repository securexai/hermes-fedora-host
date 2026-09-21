#!/usr/bin/env bash
# M05 fix: reinstall the current Quadlets and prove the gateway stays up as a
# supervised daemon.
#
# Default is inspect-only; re-run with --apply to make changes.
#
# Background this preserves: an installed hermes-gateway.container that predates
# the `Exec=gateway run` line runs bare `hermes`, prints the interactive banner,
# and exits immediately because there is no TTY. The unit therefore looks
# "failed" rather than "misconfigured".
#
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/m05-fix-and-activate.sh --apply
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
mapfile -t MP_ARGS < <(mp_positionals "$@")
BUNDLE="${MP_ARGS[0]:-$HERE}"
ADMIN_ACCOUNT=$(mp_admin_account)
ADMIN_HOME=$(mp_admin_home)
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m05-fix.out")
HERMES_UID=$(id -u hermes)
QUADLET_DIR=/etc/containers/systemd/users/$HERMES_UID
GW=hermes-gateway
STATE=/home/hermes/gateway-state

mp_require_apply 'would reinstall the Quadlets and restart the gateway'
mp_require_host_identity
mp_lock_profile
mp_install_trap
mp_require_tools podman

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
  "$@" 2>&1 | mp_redact_stream "$STATE/.env" | tail -n 50
  echo
}

rc=0
{
  echo "### M05 fix and activation"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  echo "===== bundled vs installed gateway Quadlet ====="
  echo "-- bundled Exec/Install lines --"
  grep -nE '^Exec=|^\[Install\]|^WantedBy=' "$BUNDLE/quadlets/hermes-gateway.container" || true
  echo "-- installed (before) --"
  grep -nE '^Exec=|^\[Install\]|^WantedBy=' "$QUADLET_DIR/hermes-gateway.container" || echo "(no Exec= and no [Install] present)"
  echo

  echo "===== reinstall Quadlets from the bundle ====="
  install -o root -g root -m 0644 "$BUNDLE/quadlets/hermes-worker.container" "$QUADLET_DIR/hermes-worker.container"
  install -o root -g root -m 0644 "$BUNDLE/quadlets/hermes-gateway.container" "$QUADLET_DIR/hermes-gateway.container"
  restorecon -Rv "$QUADLET_DIR" 2>&1 | tail -n 3
  echo "-- installed (after) --"
  grep -nE '^Exec=|^\[Install\]|^WantedBy=' "$QUADLET_DIR/hermes-gateway.container" || echo "(none)"
  mp_check exec_line_present "$(grep -qE '^Exec=gateway run' "$QUADLET_DIR/hermes-gateway.container" && echo PASS || echo FAIL)"
  echo

  echo "===== reload and restart ====="
  h systemctl --user daemon-reload
  h systemctl --user reset-failed hermes-gateway.service 2>/dev/null || true
  h systemctl --user restart hermes-gateway.service
  echo "restart_rc=$?"
  sleep 30
  gw_state=$(h systemctl --user is-active hermes-gateway.service)
  echo "gateway_state_after_30s=$gw_state"
  h podman ps -a --format '{{.Names}} | {{.Status}} | ports=[{{.Ports}}]' || true
  echo

  echo "===== stability: re-check after a further 60s ====="
  sleep 60
  gw_state_late=$(h systemctl --user is-active hermes-gateway.service)
  echo "gateway_state_after_90s=$gw_state_late"
  mp_check gateway_supervised "$([ "$gw_state" = active ] && [ "$gw_state_late" = active ] && echo PASS || echo FAIL)" \
    "the unit must stay active across both observations"
  h podman ps -a --format '{{.Names}} | {{.Status}}' || true
  echo

  echo "===== no published ports ====="
  port_out=$(h podman port "$GW" 2>&1)
  echo "podman_port=${port_out:-<empty>}"
  mp_check no_published_ports "$([ -z "$port_out" ] && echo PASS || echo FAIL)"
  ss -lntp 2>/dev/null | grep -E '0\.0\.0\.0|\[::\]' | grep -v '127.0.0.1' | head || true
  echo

  show "gateway journal tail" h journalctl --user -u hermes-gateway.service -n 40 --no-pager
  echo "===== done ====="
} 2>&1 | tee "$OUT" || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
echo "WROTE=$OUT"
mp_finalize "$OUT" "${rc:-0}"
