#!/usr/bin/env bash
# M05 test support: prepare the states the remaining Telegram tests need.
#
# Read-only subcommands run directly; mutating subcommands require --apply.
#
# Usage (as root on the Hermes host):
#   sudo bash ~/hermes-manual/m05-tests.sh status
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/m05-tests.sh allowlist-swap --apply
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/m05-tests.sh allowlist-restore --apply
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/m05-tests.sh worker-stop --apply
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/m05-tests.sh worker-start --apply
#   sudo bash ~/hermes-manual/m05-tests.sh logs
#
# The allowlist swap saves only the original numeric value (never the token) so
# it can be restored exactly without duplicating credential material.
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
CMD="${MP_ARGS[0]:-status}"
STATE=/home/hermes/gateway-state
SAVED=/root/hermes-m05-allowlist.saved
HERMES_UID=$(id -u hermes)
GW_UID=10000
IMAGE=docker.io/nousresearch/hermes-agent@sha256:9469b3e78b9545b6d576eb8887a95352e9a0ea83730eaf31431cf862ca1010e1

case "$CMD" in
  status | logs) MUTATING=0 ;;
  allowlist-swap | allowlist-restore | worker-stop | worker-start) MUTATING=1 ;;
  *)
    printf 'usage: %s {status|allowlist-swap|allowlist-restore|worker-stop|worker-start|logs} [--apply]\n' "$0" >&2
    exit 2
    ;;
esac

if [ "$MUTATING" -eq 1 ]; then
  mp_require_apply "would change the live test state for the '$CMD' test"
  mp_require_host_identity
  mp_lock_profile
  mp_install_trap
fi
mp_require_tools podman

ADMIN_ACCOUNT=$(mp_admin_account)
ADMIN_HOME=$(mp_admin_home)
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m05-tests-$CMD.out")

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

current_allowlist() {
  grep -m1 '^TELEGRAM_ALLOWED_USERS=' "$STATE/.env" 2>/dev/null | cut -d= -f2-
}

set_allowlist() {
  new_value="$1"
  # Expansion inside the container's script is intended; the outer shell must not expand it.
  # shellcheck disable=SC2016
  printf 'TELEGRAM_ALLOWED_USERS=%s\n' "$new_value" \
    | runuser -u hermes -- env --chdir=/home/hermes HOME=/home/hermes \
      XDG_RUNTIME_DIR="/run/user/$HERMES_UID" \
      podman run --rm -i --user "$GW_UID:$GW_UID" -v "$STATE":/opt/data:z \
      --entrypoint /bin/sh "$IMAGE" -c '
          set -e
          umask 077
          tmp=/opt/data/.env.new
          grep -vE "^TELEGRAM_ALLOWED_USERS=" /opt/data/.env > "$tmp" || true
          cat >> "$tmp"
          chmod 0600 "$tmp"
          mv -f "$tmp" /opt/data/.env
          echo "env_lines=$(wc -l < /opt/data/.env)"
        '
}

# A predictable root path is still a path another process could pre-create.
assert_saved_path_safe() {
  if [ -L "$SAVED" ]; then
    mp_die "$SAVED is a symlink; refusing to use it"
  fi
  if [ -e "$SAVED" ] && [ ! -f "$SAVED" ]; then
    mp_die "$SAVED exists and is not a regular file"
  fi
}

rc=0
{
  echo "### M05 test support: $CMD"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  case "$CMD" in
    status)
      echo "allowlist=$(current_allowlist)"
      echo "allow_all=$(grep -m1 '^TELEGRAM_ALLOW_ALL_USERS=' "$STATE/.env" 2>/dev/null | cut -d= -f2- || true)"
      echo "token_lines=$(grep -c '^TELEGRAM_BOT_TOKEN=' "$STATE/.env" 2>/dev/null || true)"
      stat -c 'env_mode=%a owner=%u:%g size=%s' "$STATE/.env" 2>&1
      gateway_state=$(h systemctl --user is-active hermes-gateway.service)
      worker_state=$(h systemctl --user is-active hermes-worker.service)
      echo "gateway=$gateway_state"
      echo "worker=$worker_state"
      mp_check gateway_active "$([ "$gateway_state" = active ] && echo PASS || echo FAIL)"
      mp_check worker_active "$([ "$worker_state" = active ] && echo PASS || echo FAIL)"
      h podman ps -a --format '{{.Names}} | {{.Status}} | ports=[{{.Ports}}]' || true
      echo "saved_allowlist=$([ -f "$SAVED" ] && echo present || echo none)"
      mp_check no_pending_swap "$([ ! -f "$SAVED" ] && echo PASS || echo FAIL)" "an outstanding allowlist swap is pending restore"
      ;;
    allowlist-swap)
      assert_saved_path_safe
      if [ -f "$SAVED" ]; then
        mp_check swap_precondition FAIL "$SAVED already exists; run allowlist-restore first"
      else
        original=$(current_allowlist)
        if [ -z "$original" ]; then
          mp_check swap_precondition FAIL "no allowlist is currently set"
        else
          mp_check swap_precondition PASS
          (
            umask 077
            printf '%s\n' "$original" >"$SAVED"
          )
          chmod 0600 "$SAVED"
          echo "saved_original_configured=yes"
          set_allowlist "1"
          h systemctl --user restart hermes-gateway.service
          sleep 20
          echo "gateway=$(h systemctl --user is-active hermes-gateway.service)"
          echo "allowlist_now=1"
          mp_check allowlist_swapped "$([ "$(current_allowlist)" = "1" ] && echo PASS || echo FAIL)"
          echo "-> Your normal account is now UNAUTHORIZED. Send the bot a message; expect NO reply."
        fi
      fi
      ;;
    allowlist-restore)
      assert_saved_path_safe
      if [ ! -f "$SAVED" ]; then
        mp_check restore_precondition FAIL "nothing saved at $SAVED"
      else
        original=$(cat "$SAVED")
        mp_check restore_precondition PASS
        set_allowlist "$original"
        rm -f "$SAVED"
        h systemctl --user restart hermes-gateway.service
        sleep 20
        echo "gateway=$(h systemctl --user is-active hermes-gateway.service)"
        echo "expected_configured=yes"
        mp_check allowlist_restored "$([ "$(current_allowlist)" = "$original" ] && echo PASS || echo FAIL)" \
          "restored value must match the saved value exactly"
        mp_check saved_file_removed "$([ ! -f "$SAVED" ] && echo PASS || echo FAIL)"
      fi
      ;;
    worker-stop)
      h systemctl --user stop hermes-worker.service
      worker_state=$(h systemctl --user is-active hermes-worker.service)
      echo "worker=$worker_state"
      mp_check worker_stopped "$([ "$worker_state" != active ] && echo PASS || echo FAIL)"
      echo "-> Worker stopped. Send the bot a command request; expect a tool error and NO local execution."
      echo "   Run 'worker-start --apply' afterwards to restore normal operation."
      ;;
    worker-start)
      h systemctl --user start hermes-worker.service
      sleep 4
      worker_state=$(h systemctl --user is-active hermes-worker.service)
      echo "worker=$worker_state"
      mp_check worker_started "$([ "$worker_state" = active ] && echo PASS || echo FAIL)"
      ls -lZ /home/hermes/transport/worker.sock 2>&1
      ;;
    logs)
      h journalctl --user -u hermes-gateway.service -n 60 --no-pager 2>&1 | mp_redact_stream "$STATE/.env" | tail -n 60
      mp_check logs_readable PASS
      ;;
  esac
  echo "===== done ====="
} 2>&1 | tee "$OUT" || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
echo "WROTE=$OUT"
mp_finalize "$OUT" "${rc:-0}"
