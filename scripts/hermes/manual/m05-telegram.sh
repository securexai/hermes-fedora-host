#!/usr/bin/env bash
# M05 step 1: start the gateway with Telegram configured and verify it becomes a
# stable supervised daemon with no public listener.
#
# Default is inspect-only; re-run with --apply to make changes.
#
# The authorized/unauthorized message tests are performed by the operator from
# Telegram; this helper prepares the state and reports it. It never prints the
# bot token.
#
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/m05-telegram.sh --apply
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
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m05-telegram.out")
HERMES_UID=$(id -u hermes)
GW=hermes-gateway
STATE=/home/hermes/gateway-state

mp_require_apply 'would restart the gateway and measure Telegram daemon stability'
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

rc=0
{
  echo "### M05 step 1: Telegram activation and daemon stability"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  echo "===== Telegram settings present? ====="
  if [ -s "$STATE/.env" ]; then
    echo "telegram_token_lines=$(grep -c '^TELEGRAM_BOT_TOKEN=' "$STATE/.env" 2>/dev/null || true)"
    echo "authorized_users_configured=$(grep -c '^TELEGRAM_ALLOWED_USERS=' "$STATE/.env" 2>/dev/null || true)"
    echo "allow_all_users=$(grep '^TELEGRAM_ALLOW_ALL_USERS=' "$STATE/.env" 2>/dev/null | cut -d= -f2- || true)"
    stat -c 'env_mode=%a owner=%u:%g size=%s' "$STATE/.env"
    token_lines=$(grep -c '^TELEGRAM_BOT_TOKEN=' "$STATE/.env" 2>/dev/null || true)
    allow_all=$(grep '^TELEGRAM_ALLOW_ALL_USERS=' "$STATE/.env" 2>/dev/null | cut -d= -f2- || true)
    mp_check telegram_credentials "$([ "${token_lines:-0}" -ge 1 ] && echo PASS || echo FAIL)"
    mp_check allow_all_disabled "$([ "$allow_all" = "false" ] && echo PASS || echo FAIL)" "TELEGRAM_ALLOW_ALL_USERS=$allow_all"
  else
    echo "env_missing=yes - provision Telegram first"
    mp_check telegram_credentials FAIL "profile .env is missing or empty"
    mp_check allow_all_disabled FAIL "cannot evaluate without a profile .env"
  fi
  echo

  echo "===== start gateway ====="
  start_epoch=$(date +%s)
  h systemctl --user restart hermes-gateway.service
  echo "restart_rc=$?"
  sleep 25
  gw_state=$(h systemctl --user is-active hermes-gateway.service)
  echo "gateway_state_after_25s=$gw_state"
  h podman ps -a --format '{{.Names}} | {{.Status}} | ports=[{{.Ports}}]' || true
  echo

  echo "===== no public listener ====="
  port_out=$(h podman port "$GW" 2>&1)
  echo "podman_port=${port_out:-<empty>}"
  mp_check no_published_ports "$([ -z "$port_out" ] && echo PASS || echo FAIL)"
  ss -lntp 2>/dev/null | grep -E '0\.0\.0\.0|\[::\]' | grep -v '127.0.0.1' | head || true
  echo

  echo "===== gateway log tail (credentials redacted) ====="
  h podman logs --tail 120 "$GW" 2>&1 | mp_redact_stream "$STATE/.env" | tail -n 120
  echo

  echo "===== daemon stability over 60s ====="
  sleep 60
  gw_state_late=$(h systemctl --user is-active hermes-gateway.service)
  echo "gateway_state_after_85s=$gw_state_late"
  mp_check gateway_stable "$([ "$gw_state" = active ] && [ "$gw_state_late" = active ] && echo PASS || echo FAIL)"
  h podman ps -a --format '{{.Names}} | {{.Status}} | ports=[{{.Ports}}]' || true
  echo

  tg_lines=$(h journalctl --user -u hermes-gateway.service -b --since "@$start_epoch" --no-pager 2>/dev/null | grep -c 'Connected to Telegram' || true)
  echo "telegram_connected_lines_since_restart=$tg_lines"
  mp_check telegram_connected "$([ "${tg_lines:-0}" -gt 0 ] && echo PASS || echo FAIL)" \
    "a connection must be logged after this restart"
  echo

  echo "===== recent AVC denials ====="
  mp_audit_avc_check avc_denials recent

  echo "===== operator message tests to perform ====="
  echo "1. From an AUTHORIZED Telegram account, send the bot a simple message and confirm a reply."
  echo "2. From an UNAUTHORIZED account, send a message and confirm it is rejected/ignored."
  echo "3. Trigger an approval-gated action: first verify the verdict with"
  echo "   'hermes approvals test' (0 = allow, 2 = ask, 3 = deny), then use a command that"
  echo "   actually reaches that verdict. A benign command proves nothing."
  echo "4. Approve and reject an exact memory ID with /memory pending, then confirm recall"
  echo "   in a NEW session."
  echo "5. Record the observed outcomes for M05 evidence."
  echo
  echo "===== done ====="
} 2>&1 | tee "$OUT" || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
echo "WROTE=$OUT"
mp_finalize "$OUT" "${rc:-0}"
