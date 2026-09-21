#!/usr/bin/env bash
# M03 step 1: activate the gateway and validate the SSH terminal backend.
#
# Default is inspect-only; re-run with --apply to make changes. No provider
# credential is loaded in this step: it proves that the gateway starts under the
# manual profile, resolves the enforcement shims, and publishes no ports.
#
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/m03-activate.sh --apply
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
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m03-activate.out")
HERMES_UID=$(id -u hermes)
QUADLET_DIR=/etc/containers/systemd/users/$HERMES_UID
GW=hermes-gateway

mp_require_apply 'would reinstall the Quadlets, restart the gateway, and probe the SSH backend'
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
  echo "### M03 step 1: gateway activation + SSH backend validation"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  echo "===== reinstall rootless Quadlets (convergent) ====="
  install -d -o root -g root -m 0755 "$QUADLET_DIR"
  quadlets_changed=0
  for unit in hermes-worker.container hermes-gateway.container; do
    result=$(mp_install_reconcile "quadlet_${unit%.container}" 0644 root:root "$BUNDLE/quadlets/$unit" "$QUADLET_DIR/$unit") || exit 1
    echo "$result"
    [[ "$result" == CHANGED* ]] && quadlets_changed=1
  done
  [ "$quadlets_changed" -eq 1 ] && restorecon -Rv "$QUADLET_DIR" 2>&1 | tail -n 3 || echo "quadlet labels unchanged"
  mp_check quadlets_installed "$([ -r "$QUADLET_DIR/hermes-gateway.container" ] && [ -r "$QUADLET_DIR/hermes-worker.container" ] && echo PASS || echo FAIL)"
  if [ "$quadlets_changed" -eq 1 ]; then
    h systemctl --user daemon-reload
    echo "daemon_reload_rc=$?"
  else
    echo "quadlets unchanged; daemon-reload skipped"
  fi
  echo

  echo "===== state before activation ====="
  echo "worker_state=$(h systemctl --user is-active hermes-worker.service)"
  echo "gateway_state=$(h systemctl --user is-active hermes-gateway.service)"
  echo "gateway_enable_state=$(h systemctl --user is-enabled hermes-gateway.service 2>&1)"
  echo "worker_socket=$(ls -l /home/hermes/transport/worker.sock 2>&1)"
  echo

  echo "===== start gateway (convergent: skip when already active) ====="
  gateway_now=$(h systemctl --user is-active hermes-gateway.service 2>/dev/null || true)
  if [ "$gateway_now" = "active" ] && [ "$quadlets_changed" -eq 0 ]; then
    echo "gateway already active with unchanged Quadlets; start skipped"
  else
    h systemctl --user start hermes-gateway.service
    echo "gateway_start_rc=$?"
  fi
  sleep 12
  gateway_state=$(h systemctl --user is-active hermes-gateway.service)
  echo "gateway_state=$gateway_state"
  mp_check gateway_active "$([ "$gateway_state" = active ] && echo PASS || echo FAIL)"
  h systemctl --user status hermes-gateway.service --no-pager 2>&1 | head -n 14
  echo

  echo "===== containers and published ports ====="
  h podman ps -a --format '{{.Names}} | {{.Status}} | {{.Image}} | ports=[{{.Ports}}]'
  port_out=$(h podman port "$GW" 2>&1)
  echo "-- explicit port query: ${port_out:-<empty>} --"
  mp_check no_published_ports "$([ -z "$port_out" ] && echo PASS || echo FAIL)" "$port_out"
  echo

  echo "===== no gateway process listening on the host ====="
  ss -lntp 2>/dev/null | grep -vE '127\.0\.0|\[::1\]' | head || true
  echo

  echo "===== container identity and shim resolution ====="
  # Expansion inside the container's script is intended; the outer shell must not expand it.
  # shellcheck disable=SC2016
  shim_out=$(h podman exec "$GW" sh -c 'id; echo "which ssh: $(command -v ssh)"; echo "which scp: $(command -v scp)"; ls -l /opt/hermes/bin/ssh /opt/hermes/bin/scp' 2>&1)
  printf '%s\n' "$shim_out"
  if [[ "$shim_out" == *"which ssh: /opt/hermes/bin/ssh"* ]]; then
    mp_check shim_resolution PASS
  else
    mp_check shim_resolution FAIL "the image is resolving another ssh binary"
  fi
  echo

  echo "===== HERMES terminal environment ====="
  h podman exec "$GW" sh -c 'env | grep -E "^TERMINAL_" | sort' 2>&1 || true
  echo

  echo "===== hermes doctor (informational only) ====="
  # The handoff records that `hermes doctor` forces terminal_env=local inside a
  # container, so it cannot validate this profile. It is an INFORMATIONAL
  # diagnostic: it is reported but is not a required check, so it can neither
  # pass nor block the gate.
  doctor_out=$(h timeout 180 podman exec "$GW" hermes doctor 2>&1)
  doctor_rc=$?
  printf '%s\n' "$doctor_out" | tail -n 40
  mp_info doctor "rc=$doctor_rc; hermes doctor forces the local backend in a container and cannot validate the SSH profile"
  echo

  echo "===== gateway logs ====="
  h podman logs --tail 50 "$GW" 2>&1 | mp_redact_stream /home/hermes/gateway-state/.env | tail -n 50
  echo

  echo "===== recent AVC denials ====="
  mp_audit_avc_check avc_denials recent
  echo "===== done ====="
} 2>&1 | tee "$OUT" || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
echo "WROTE=$OUT"
mp_finalize "$OUT" "${rc:-0}"
