#!/usr/bin/env bash
# Provision the dedicated OpenAI API key for the Hermes gateway profile.
#
# Run interactively as root on the Hermes host:
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/provision-openai-key.sh
#
# The key is read from the terminal WITHOUT echo, written into the profile .env
# by a one-shot container running as the gateway's runtime UID (10000), and is
# never placed in argv, printed, or written to any log. Existing unrelated .env
# entries are preserved: this merges, it never truncates.
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
OUT=$(mp_new_log "$ADMIN_HOME/hermes-provision-openai.out")
STATE=/home/hermes/gateway-state
GW_UID=10000
IMAGE=docker.io/nousresearch/hermes-agent@sha256:9469b3e78b9545b6d576eb8887a95352e9a0ea83730eaf31431cf862ca1010e1
BASE_URL="${OPENAI_BASE_URL:-https://api.openai.com/v1}"

if [ ! -r /dev/tty ]; then
  echo "STOP: this script needs an interactive terminal for hidden input." >&2
  exit 2
fi

[ -d "$STATE" ] || {
  echo "STOP: $STATE is missing" >&2
  exit 2
}

HERMES_UID=$(id -u hermes)

rc=0
{
  echo "### Provision OpenAI API key for the Hermes gateway profile"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  printf 'Paste the dedicated OpenAI API key. Input is hidden and never echoed.\n' >/dev/tty
  printf 'Key: ' >/dev/tty
  IFS= read -r -s KEY </dev/tty
  printf '\nConfirm key: ' >/dev/tty
  IFS= read -r -s KEY2 </dev/tty
  printf '\n' >/dev/tty

  if [ -z "$KEY" ]; then
    mp_check key_input FAIL "empty key"
    exit 1
  fi
  if [ "$KEY" != "$KEY2" ]; then
    mp_check key_input FAIL "the two entries do not match"
    exit 1
  fi
  case "$KEY" in
    *[![:print:]]*)
      mp_check key_input FAIL "key contains non-printable characters"
      exit 1
      ;;
  esac
  mp_check key_input PASS
  case "$KEY" in
    sk-*) : ;;
    *) echo "WARNING: the value does not start with 'sk-'; continuing because only OpenAI can validate it." >&2 ;;
  esac

  before_other=$(grep -vcE '^(OPENAI_BASE_URL|OPENAI_API_KEY)=' "$STATE/.env" 2>/dev/null || echo 0)

  # Feed the value over stdin so it never appears in a process argument list.
  # Expansion inside the container's script is intended; the outer shell must not expand it.
  # shellcheck disable=SC2016
  printf 'OPENAI_BASE_URL=%s\nOPENAI_API_KEY=%s\n' "$BASE_URL" "$KEY" \
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
            # when .env holds ONLY OpenAI keys. Any other non-zero status is a real
            # read failure and must not be swallowed.
            grep -vE "^(OPENAI_BASE_URL|OPENAI_API_KEY)=" /opt/data/.env > "$tmp" || {
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
          mv -f "$tmp" /opt/data/.env
          echo "env_lines=$(wc -l < /opt/data/.env)"
          echo "openai_key_lines=$(grep -c "^OPENAI_API_KEY=" /opt/data/.env || true)"
          echo "preserved_other_keys=$(grep -vcE "^(OPENAI_BASE_URL|OPENAI_API_KEY)=" /opt/data/.env || true)"
        '

  unset KEY KEY2

  key_lines=$(grep -c '^OPENAI_API_KEY=' "$STATE/.env" 2>/dev/null || true)
  after_other=$(grep -vcE '^(OPENAI_BASE_URL|OPENAI_API_KEY)=' "$STATE/.env" 2>/dev/null || true)
  mp_check openai_key_present "$([ "${key_lines:-0}" -ge 1 ] && echo PASS || echo FAIL)"
  mp_check other_env_preserved "$([ "${after_other:-0}" -ge "${before_other:-0}" ] && echo PASS || echo FAIL)" \
    "before=$before_other after=$after_other"
  stat -c 'env_mode=%a owner=%u:%g size=%s' "$STATE/.env" 2>&1
  echo "WROTE=$OUT"
  echo "No key material was displayed."
} 2>&1 | tee "$OUT" || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
mp_finalize "$OUT" "${rc:-0}"
