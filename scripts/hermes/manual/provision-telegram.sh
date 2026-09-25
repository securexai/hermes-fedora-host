#!/usr/bin/env bash
# Provision Telegram settings for the Hermes gateway profile.
#
# The bot token is read with hidden input, travels over stdin only, and never
# enters argv, output, logs or shell history. Authorized user IDs are numeric and
# not secret. Existing unrelated .env entries are preserved.
#
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/provision-telegram.sh
set -euo pipefail
export LC_ALL=C

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib-manual-common.sh
. "$HERE/lib-manual-common.sh" || {
  printf 'STOP: cannot load %s/lib-manual-common.sh (stage the whole manual/ tree)\n' "$HERE" >&2
  exit 1
}

mp_require_host_identity
# Credential and configuration operations share the one profile lock, so a
# provisioning run cannot interleave with a deployment or hardening run.
mp_lock_profile
mp_require_tools podman

ADMIN_ACCOUNT=$(mp_admin_account)
ADMIN_HOME=$(mp_admin_home)
OUT=$(mp_new_log "$ADMIN_HOME/hermes-provision-telegram.out")
STATE=/home/hermes/gateway-state
GW_UID=10000
IMAGE=docker.io/nousresearch/hermes-agent@sha256:fca358f12efd65bfaaca05884166f15c0e2788375ca30d77061ac1ebc96452b7
HERMES_UID=$(id -u hermes)

if [ ! -r /dev/tty ]; then
  echo "STOP: this script needs an interactive terminal for hidden input." >&2
  exit 2
fi

[ -d "$STATE" ] || {
  echo "STOP: $STATE is missing" >&2
  exit 2
}

rc=0
{
  echo "### Provision Telegram settings for the Hermes gateway profile"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  printf 'Telegram bot token (hidden): ' >/dev/tty
  IFS= read -r -s TOKEN </dev/tty
  printf '\nConfirm token (hidden): ' >/dev/tty
  IFS= read -r -s TOKEN2 </dev/tty
  printf '\n' >/dev/tty

  if [ -z "$TOKEN" ]; then
    mp_check token_input FAIL "empty token"
    exit 1
  fi
  if [ "$TOKEN" != "$TOKEN2" ]; then
    mp_check token_input FAIL "tokens do not match"
    exit 1
  fi
  case "$TOKEN" in
    *[![:print:]]*)
      mp_check token_input FAIL "token contains non-printable characters"
      exit 1
      ;;
  esac
  mp_check token_input PASS

  printf 'Authorized numeric Telegram user ID(s), comma-separated: ' >/dev/tty
  IFS= read -r USERS </dev/tty
  case "$USERS" in
    '' | *[!0-9,]*)
      mp_check allowlist_input FAIL "expected comma-separated numeric IDs only"
      exit 1
      ;;
  esac
  mp_check allowlist_input PASS "count=$(printf '%s' "$USERS" | tr ',' '\n' | grep -c . || true)"

  before_other=$(grep -vcE '^(TELEGRAM_BOT_TOKEN|TELEGRAM_ALLOWED_USERS|TELEGRAM_ALLOW_ALL_USERS)=' "$STATE/.env" 2>/dev/null || echo 0)

  # Feed the token over stdin. The container filters any previously stored
  # Telegram keys, appends the new ones, and replaces the file atomically.
  # Expansion inside the container's script is intended; the outer shell must not expand it.
  # shellcheck disable=SC2016
  printf 'TELEGRAM_BOT_TOKEN=%s\nTELEGRAM_ALLOWED_USERS=%s\nTELEGRAM_ALLOW_ALL_USERS=false\n' \
    "$TOKEN" "$USERS" \
    | runuser -u hermes -- env --chdir=/home/hermes HOME=/home/hermes \
      XDG_RUNTIME_DIR="/run/user/$HERMES_UID" \
      podman run --rm -i --user "$GW_UID:$GW_UID" \
      -v "$STATE":/opt/data:z \
      --entrypoint /bin/sh "$IMAGE" -c '
          set -e
          umask 077
          tmp=/opt/data/.env.new
          if [ -f /opt/data/.env ]; then
            # grep -v exits 1 when it selects no lines, which happens legitimately
            # when .env holds ONLY Telegram keys. Any other non-zero status is a
            # real read failure and must not be swallowed.
            grep -vE "^(TELEGRAM_BOT_TOKEN|TELEGRAM_ALLOWED_USERS|TELEGRAM_ALLOW_ALL_USERS)=" /opt/data/.env > "$tmp" || {
              rc=$?
              if [ "$rc" -ne 1 ]; then
                echo "STOP: could not rewrite /opt/data/.env (grep rc=$rc)" >&2
                exit 1
              fi
            }
          else
            : > "$tmp"
          fi
          cat >> "$tmp"
          chmod 0600 "$tmp"
          if [ -f /opt/data/.env ] && cmp -s "$tmp" /opt/data/.env; then
            rm -f "$tmp"
            echo "env_update=UNCHANGED"
          else
            mv -f "$tmp" /opt/data/.env
            echo "env_update=CHANGED"
          fi
          echo "env_lines=$(wc -l < /opt/data/.env)"
        '

  unset TOKEN TOKEN2

  token_lines=$(grep -c '^TELEGRAM_BOT_TOKEN=' "$STATE/.env" 2>/dev/null || true)
  allow_all=$(grep '^TELEGRAM_ALLOW_ALL_USERS=' "$STATE/.env" 2>/dev/null | cut -d= -f2- || true)
  after_other=$(grep -vcE '^(TELEGRAM_BOT_TOKEN|TELEGRAM_ALLOWED_USERS|TELEGRAM_ALLOW_ALL_USERS)=' "$STATE/.env" 2>/dev/null || true)
  mp_check telegram_token_present "$([ "${token_lines:-0}" -ge 1 ] && echo PASS || echo FAIL)"
  mp_check allow_all_disabled "$([ "$allow_all" = "false" ] && echo PASS || echo FAIL)"
  mp_check other_env_preserved "$([ "${after_other:-0}" -ge "${before_other:-0}" ] && echo PASS || echo FAIL)"
  stat -c 'env_mode=%a owner=%u:%g size=%s' "$STATE/.env" 2>&1
  echo "WROTE=$OUT"
  echo "No token material was displayed."
} 2>&1 | tee "$OUT" || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
mp_finalize "$OUT" "${rc:-0}"
