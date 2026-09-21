#!/usr/bin/env bash
# M04 closeout (a): validate a read-only gateway root filesystem.
#
# Default is inspect-only; re-run with --apply to make changes.
#
# Adds ReadOnly=true plus tmpfs-backed /run and /tmp to the gateway Quadlet,
# restarts, and verifies the gateway returns with a NEW Telegram connection made
# after the restart. If it does not, the previously installed unit is restored
# automatically and the run fails.
#
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/m04-readonly-gateway.sh --apply
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
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m04-readonly.out")
HERMES_UID=$(id -u hermes)
QUADLET_DIR=/etc/containers/systemd/users/$HERMES_UID
GW=hermes-gateway
STATE=/home/hermes/gateway-state
TS=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="/root/hermes-gateway.container.pre-readonly-$TS"

mp_require_apply 'would switch the gateway to a read-only root and restart it'
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

# Telegram connections made since a given epoch, scoped to this boot AND this
# restart, so a line from an earlier run can never satisfy the check.
telegram_since() {
  h journalctl --user -u hermes-gateway.service -b --since "@$1" --no-pager 2>/dev/null \
    | grep -c 'Connected to Telegram' || true
}

rc=0
{
  echo "### M04 closeout: read-only gateway root"
  echo "### generated: $TS"
  echo

  echo "===== current unit (before) ====="
  grep -nE '^(ReadOnly|Tmpfs|Exec)=' "$QUADLET_DIR/hermes-gateway.container" || echo "(no ReadOnly/Tmpfs present)"
  cp -a "$QUADLET_DIR/hermes-gateway.container" "$BACKUP"
  chmod 600 "$BACKUP"
  echo "backup=$BACKUP"
  mp_check unit_backed_up "$([ -s "$BACKUP" ] && echo PASS || echo FAIL)"
  echo

  echo "===== install the read-only variant ====="
  install -o root -g root -m 0644 "$BUNDLE/quadlets/hermes-gateway.container" \
    "$QUADLET_DIR/hermes-gateway.container"
  restorecon -v "$QUADLET_DIR/hermes-gateway.container" 2>&1
  echo "-- after --"
  grep -nE '^(ReadOnly|Tmpfs|Exec)=' "$QUADLET_DIR/hermes-gateway.container" || echo "(none)"
  mp_check readonly_unit_installed "$(grep -qE '^ReadOnly=true' "$QUADLET_DIR/hermes-gateway.container" && echo PASS || echo FAIL)"
  echo

  echo "===== reload and restart ====="
  start_epoch=$(date +%s)
  h systemctl --user daemon-reload
  h systemctl --user reset-failed hermes-gateway.service 2>/dev/null || true
  h systemctl --user restart hermes-gateway.service
  echo "restart_rc=$?"
  sleep 45
  gw_state=$(h systemctl --user is-active hermes-gateway.service)
  echo "gateway_state_after_45s=$gw_state"
  h podman ps -a --format '{{.Names}} | {{.Status}} | ports=[{{.Ports}}]' || true
  echo

  tg_lines=$(telegram_since "$start_epoch")
  echo "telegram_connected_lines_since_restart=$tg_lines"
  if [ "$gw_state" = "active" ] && [ "${tg_lines:-0}" -eq 0 ]; then
    waited=0
    while [ "$waited" -lt 60 ]; do
      sleep 10
      waited=$((waited + 10))
      tg_lines=$(telegram_since "$start_epoch")
      if [ "${tg_lines:-0}" -gt 0 ]; then break; fi
    done
    echo "telegram_reconnect_wait_seconds=$waited telegram_connected_lines=$tg_lines"
  fi
  mp_check telegram_reconnected_after_restart "$([ "${tg_lines:-0}" -gt 0 ] && echo PASS || echo FAIL)" \
    "a new Telegram connection is required, not one inherited from an earlier start"
  echo

  if [ "$gw_state" = "active" ] && [ "${tg_lines:-0}" -gt 0 ]; then
    echo "===== read-only probe inside the gateway ====="
    probe=$(h podman exec "$GW" sh -c '
      echo "root_write_probe:"
      ( touch /m04-readonly-probe 2>&1 && echo "WRITABLE_UNEXPECTED" && rm -f /m04-readonly-probe ) || echo "READONLY_OK"
      echo "run_write_probe:"
      ( touch /run/m04-probe 2>&1 && echo "RUN_WRITABLE_OK" && rm -f /run/m04-probe ) || echo "RUN_NOT_WRITABLE"
      echo "data_write_probe:"
      ( touch /opt/data/.m04-probe 2>&1 && echo "DATA_WRITABLE_OK" && rm -f /opt/data/.m04-probe ) || echo "DATA_NOT_WRITABLE"
    ' 2>&1)
    printf '%s\n' "$probe"
    mp_check gateway_root_readonly "$([[ "$probe" == *READONLY_OK* && "$probe" != *WRITABLE_UNEXPECTED* ]] && echo PASS || echo FAIL)"
    mp_check gateway_run_tmpfs_writable "$([[ "$probe" == *RUN_WRITABLE_OK* ]] && echo PASS || echo FAIL)"
    mp_check gateway_data_volume_writable "$([[ "$probe" == *DATA_WRITABLE_OK* ]] && echo PASS || echo FAIL)"
    echo
    echo "===== gateway journal tail ====="
    h journalctl --user -u hermes-gateway.service -n 30 --no-pager 2>&1 \
      | mp_redact_stream "$STATE/.env" | tail -n 30
    echo
    mp_check readonly_variant_accepted PASS
  else
    echo "===== gateway unhealthy (is-active=$gw_state telegram_lines=${tg_lines:-0}): reverting ====="
    install -o root -g root -m 0644 "$BACKUP" "$QUADLET_DIR/hermes-gateway.container"
    restorecon -v "$QUADLET_DIR/hermes-gateway.container" 2>&1
    h systemctl --user daemon-reload
    h systemctl --user reset-failed hermes-gateway.service 2>/dev/null || true
    h systemctl --user restart hermes-gateway.service
    sleep 40
    reverted=$(h systemctl --user is-active hermes-gateway.service)
    echo "reverted_gateway_state=$reverted"
    mp_check readonly_variant_accepted FAIL "the gateway did not return under the read-only root"
    mp_check unit_reverted "$([ "$reverted" = active ] && echo PASS || echo FAIL)" "the previous unit was restored"
    h podman ps -a --format '{{.Names}} | {{.Status}}' || true
    echo "-- failure journal --"
    h journalctl --user -u hermes-gateway.service -n 40 --no-pager 2>&1 \
      | mp_redact_stream "$STATE/.env" | tail -n 40
  fi
  echo

  echo "===== recent AVC denials ====="
  mp_audit_avc_check avc_denials recent
  echo "===== done ====="
} 2>&1 | tee "$OUT" || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
echo "WROTE=$OUT"
mp_finalize "$OUT" "${rc:-0}"
