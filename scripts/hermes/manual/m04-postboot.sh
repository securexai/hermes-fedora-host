#!/usr/bin/env bash
# M04 closeout (b), part 2: verify Quadlet autostart and gateway function after
# the reboot. Run this once the host is unlocked and reachable again.
#
# Default is inspect-only. It installs the transport probe, so re-run with
# --apply to actually perform the post-reboot verification.
#
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/m04-postboot.sh --apply
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
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m04-postboot.out")
PRE="$ADMIN_HOME/hermes-m04-reboot.out"
HERMES_UID=$(id -u hermes)
STATE=/home/hermes/gateway-state

mp_require_apply 'would install the transport probe and run the post-reboot verification'
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
  echo "### M04 closeout (b), part 2: post-reboot verification"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  echo "===== boot identity ====="
  pre_boot=$(grep -m1 '^boot_id=' "$PRE" 2>/dev/null | cut -d= -f2- || true)
  now_boot=$(cat /proc/sys/kernel/random/boot_id)
  echo "boot_id_before=${pre_boot:-unknown}"
  echo "boot_id_after=$now_boot"
  mp_check boot_changed "$([ -n "${pre_boot:-}" ] && [ "$pre_boot" != "$now_boot" ] && echo PASS || echo UNVERIFIED)" \
    "without the pre-reboot record the boot change cannot be established"
  echo "uptime=$(uptime -p)"
  echo

  echo "===== autostart results (no manual start performed) ====="
  echo "user_manager=$(systemctl is-active "user@$HERMES_UID.service")"
  echo "linger=$(ls /var/lib/systemd/linger/ 2>&1)"
  gateway_state=$(h systemctl --user is-active hermes-gateway.service)
  worker_state=$(h systemctl --user is-active hermes-worker.service)
  echo "gateway=$gateway_state"
  echo "worker=$worker_state"
  mp_check services_autostarted "$([ "$gateway_state" = active ] && [ "$worker_state" = active ] && echo PASS || echo FAIL)"
  h podman ps -a --format '{{.Names}} | {{.Status}} | ports=[{{.Ports}}]' || true
  h podman inspect hermes-worker --format 'worker_started={{.State.StartedAt}}' 2>/dev/null || true
  h podman inspect hermes-gateway --format 'gateway_started={{.State.StartedAt}}' 2>/dev/null || true
  echo "worker_socket=$(ls -lZ /home/hermes/transport/worker.sock 2>&1)"
  echo

  echo "===== gateway function after reboot ====="
  tg_lines=$(h journalctl --user -u hermes-gateway.service -b --no-pager 2>/dev/null | grep -c 'Connected to Telegram' || true)
  echo "telegram_connected_this_boot=$tg_lines"
  h journalctl --user -u hermes-gateway.service -b -n 25 --no-pager 2>&1 \
    | mp_redact_stream "$STATE/.env" | tail -n 25
  mp_check telegram_this_boot "$([ "${tg_lines:-0}" -gt 0 ] && echo PASS || echo FAIL)" \
    "a connection logged in an earlier boot does not count"
  echo

  echo "===== end-to-end transport probe (real production code path) ====="
  install -o hermes -g hermes -m 0644 "$BUNDLE/gateway/m03-probe.py" /home/hermes/gateway-ssh/m03-probe.py
  # A file created inside a :Z mount after the container started keeps the host
  # default label and the gateway cannot read it; give it the sibling label.
  chcon --reference=/home/hermes/gateway-ssh/known_hosts /home/hermes/gateway-ssh/m03-probe.py 2>/dev/null \
    || chcon -t container_file_t /home/hermes/gateway-ssh/m03-probe.py 2>/dev/null || true
  echo "probe_context=$(stat -c %C /home/hermes/gateway-ssh/m03-probe.py 2>&1)"
  probe_out=$(h podman exec --user 10000:10000 --workdir /opt/hermes hermes-gateway \
    /opt/hermes/.venv/bin/python3 /opt/hermes/gateway-ssh/m03-probe.py 2>&1)
  probe_rc=$?
  printf '%s\n' "$probe_out" | tail -n 8
  echo "probe_rc=$probe_rc"
  mp_check transport_probe "$([ "$probe_rc" -eq 0 ] && [[ "$probe_out" == *RESULT=PASS* ]] && echo PASS || echo FAIL)"
  echo

  echo "===== exposure and health ====="
  h podman port hermes-gateway 2>&1 || true
  ss -lntp 2>/dev/null | grep -E '0\.0\.0\.0|\[::\]' | grep -vE '127\.0\.0\.|\[::1\]' || true
  echo "failed_units:"
  systemctl --failed --no-pager | tail -n +2 | head -n 3 || true
  failed=$(systemctl --failed --no-pager --plain 2>/dev/null | tail -n +2 | grep -c . || true)
  mp_check no_failed_units "$([ "${failed:-0}" -eq 0 ] && echo PASS || echo FAIL)" "$failed failed unit(s)"
  echo

  echo "===== recent AVC denials ====="
  mp_audit_avc_check avc_denials recent
  echo "===== done ====="
} 2>&1 | tee "$OUT" || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
echo "WROTE=$OUT"
mp_finalize "$OUT" "${rc:-0}"
