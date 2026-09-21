#!/usr/bin/env bash
# M04 closeout (b), part 1: enable gateway autostart, record the pre-reboot
# state, and (only after every prerequisite check passes and the operator types
# the confirmation) reboot for the persistence test.
#
# Default is inspect-only; re-run with --apply to make changes.
#
# With TPM2 enrollment in place the host unlocks itself, so no passphrase is
# needed and this step can be driven remotely. The passphrase is still required
# at the console if the TPM token has been removed or PCR 7 has changed.
#
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/m04-reboot.sh --apply
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
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m04-reboot.out")
HERMES_UID=$(id -u hermes)
QUADLET_DIR=/etc/containers/systemd/users/$HERMES_UID

mp_require_apply 'would install the autostart gateway unit and reboot this host'
mp_require_host_identity
mp_lock_profile
mp_install_trap

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
  echo "### M04 closeout (b), part 1: reboot persistence preparation"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  echo "===== install the autostart gateway Quadlet ====="
  install -o root -g root -m 0644 "$BUNDLE/quadlets/hermes-gateway.container" \
    "$QUADLET_DIR/hermes-gateway.container"
  restorecon -v "$QUADLET_DIR/hermes-gateway.container" 2>&1
  grep -nE '^\[Install\]|^WantedBy=|^ReadOnly=|^Exec=' "$QUADLET_DIR/hermes-gateway.container" || true
  mp_check autostart_wantedby "$(grep -qE '^WantedBy=default.target' "$QUADLET_DIR/hermes-gateway.container" && echo PASS || echo FAIL)"
  echo

  echo "===== reload user manager ====="
  h systemctl --user daemon-reload
  echo "daemon_reload_rc=$?"
  echo "gateway_enable_state=$(h systemctl --user is-enabled hermes-gateway.service 2>&1)"
  echo "worker_enable_state=$(h systemctl --user is-enabled hermes-worker.service 2>&1)"
  echo

  echo "===== pre-reboot state ====="
  echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)"
  echo "uptime=$(uptime -p)"
  echo "user_manager=$(systemctl is-active "user@$HERMES_UID.service" 2>/dev/null || true)"
  echo "linger=$(ls /var/lib/systemd/linger/ 2>&1)"
  gateway_state=$(h systemctl --user is-active hermes-gateway.service)
  worker_state=$(h systemctl --user is-active hermes-worker.service)
  echo "gateway=$gateway_state"
  echo "worker=$worker_state"
  mp_check services_active_before_reboot "$([ "$gateway_state" = active ] && [ "$worker_state" = active ] && echo PASS || echo FAIL)"
  h podman ps -a --format '{{.Names}} | {{.Status}} | ports=[{{.Ports}}]' || true
  h podman inspect hermes-worker --format 'worker_started={{.State.StartedAt}}' 2>/dev/null || true
  h podman inspect hermes-gateway --format 'gateway_started={{.State.StartedAt}}' 2>/dev/null || true
  echo "===== done with preparation ====="
} 2>&1 | tee "$OUT" || rc=$?

# Reboot only when the preparation actually passed; otherwise report and stop so
# a broken configuration is never carried across a reboot.
if [ "${rc:-0}" -ne 0 ] || grep -qaE '^CHECK [A-Za-z0-9_.-]+=FAIL' "$OUT"; then
  chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
  chmod 0600 "$OUT"
  echo "WROTE=$OUT"
  mp_finalize "$OUT" "${rc:-0}"
fi

echo "With TPM2 unlock enrolled no console input is needed. If the token was"
echo "removed or firmware changed PCR 7, the passphrase prompt returns and needs"
echo "someone physically at the console."
printf 'Type exactly REBOOT to proceed, anything else to abort: '
read -r answer
if [ "$answer" != "REBOOT" ]; then
  echo "ABORTED - no reboot performed" | tee -a "$OUT"
  chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
  chmod 0600 "$OUT"
  echo "WROTE=$OUT"
  echo "RESULT=ABORTED (no reboot performed; preparation checks passed)"
  exit 0
fi

echo "reboot_issued_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$OUT"
chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
echo "WROTE=$OUT"
sync
systemctl reboot
