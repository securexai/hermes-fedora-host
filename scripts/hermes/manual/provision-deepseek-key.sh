#!/usr/bin/env bash
# Provision a dedicated native DeepSeek API key for the manual Hermes gateway.
# Run interactively on the reviewed guest as root. The key is read from /dev/tty
# without echo, crosses into the pinned image only on stdin, and never appears
# in argv or logs. Unrelated profile environment entries are preserved.
set -euo pipefail
export LC_ALL=C

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib-manual-common.sh
. "$HERE/lib-manual-common.sh" || {
  printf 'STOP: cannot load %s/lib-manual-common.sh (stage the whole manual/ tree)\n' "$HERE" >&2
  exit 1
}

mp_require_host_identity
mp_lock_profile
mp_require_tools podman

ADMIN_ACCOUNT=$(mp_admin_account)
ADMIN_HOME=$(mp_admin_home)
OUT=$(mp_new_log "$ADMIN_HOME/hermes-provision-deepseek.out")
STATE=/home/hermes/gateway-state
GW_UID=10000
IMAGE=docker.io/nousresearch/hermes-agent@sha256:fca358f12efd65bfaaca05884166f15c0e2788375ca30d77061ac1ebc96452b7

[ -r /dev/tty ] || {
  echo 'STOP: an interactive terminal is required for hidden input' >&2
  exit 2
}
[ -d "$STATE" ] || {
  echo "STOP: $STATE is missing" >&2
  exit 2
}
HERMES_UID=$(id -u hermes)

rc=0
{
  echo "### Provision native DeepSeek API key for the Hermes gateway"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'Dedicated DeepSeek API key (hidden): ' >/dev/tty
  IFS= read -r -s KEY </dev/tty
  printf '\nConfirm key (hidden): ' >/dev/tty
  IFS= read -r -s KEY2 </dev/tty
  printf '\n' >/dev/tty

  if [ -z "$KEY" ] || [ "$KEY" != "$KEY2" ]; then
    mp_check key_input FAIL 'empty or mismatched entries'
    exit 1
  fi
  case "$KEY" in
    *[![:print:]]*)
      mp_check key_input FAIL 'non-printable character'
      exit 1
      ;;
  esac
  mp_check key_input PASS

  before_other=$(grep -vcE '^DEEPSEEK_API_KEY=' "$STATE/.env" 2>/dev/null || true)
  before_other=${before_other:-0}
  # The inner script receives only stdin. It compares before replacing, so a
  # rerun with the same key leaves the .env file unchanged.
  # shellcheck disable=SC2016
  printf 'DEEPSEEK_API_KEY=%s\n' "$KEY" \
    | runuser -u hermes -- env --chdir=/home/hermes HOME=/home/hermes \
      XDG_RUNTIME_DIR="/run/user/$HERMES_UID" \
      podman run --rm -i --user "$GW_UID:$GW_UID" \
      -v "$STATE":/opt/data:z \
      --entrypoint /bin/sh "$IMAGE" -c '
        set -e
        umask 077
        tmp=/opt/data/.env.new
        if [ -f /opt/data/.env ]; then
          grep -vE "^DEEPSEEK_API_KEY=" /opt/data/.env > "$tmp" || {
            rc=$?
            [ "$rc" -eq 1 ] || { echo "STOP: env read failed (rc=$rc)" >&2; exit 1; }
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
        echo "deepseek_key_lines=$(grep -c "^DEEPSEEK_API_KEY=" /opt/data/.env || true)"
      '
  unset KEY KEY2

  key_lines=$(grep -c '^DEEPSEEK_API_KEY=' "$STATE/.env" 2>/dev/null || true)
  after_other=$(grep -vcE '^DEEPSEEK_API_KEY=' "$STATE/.env" 2>/dev/null || true)
  mp_check deepseek_key_present "$([ "${key_lines:-0}" -eq 1 ] && echo PASS || echo FAIL)"
  mp_check other_env_preserved "$([ "${after_other:-0}" -ge "$before_other" ] && echo PASS || echo FAIL)" \
    "before=$before_other after=$after_other"
  stat -c 'env_mode=%a owner=%u:%g size=%s' "$STATE/.env" 2>&1
  echo "WROTE=$OUT"
  echo 'No key material was displayed.'
} 2>&1 | tee "$OUT" || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
mp_finalize "$OUT" "${rc:-0}"
