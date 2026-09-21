#!/usr/bin/env bash
# M04 closeout (b), part 3: correct the probe file label and re-run the
# end-to-end transport probe inside the running gateway.
#
# Default is inspect-only; re-run with --apply to make changes.
#
# Background: a file written into a bind-mounted directory after its container
# started inherits the host default label (user_home_t), so container_t is
# denied read. This relabels it like its mounted siblings and re-runs the probe.
#
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/m04-postboot-probe.sh --apply
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
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m04-postboot-probe.out")
HERMES_UID=$(id -u hermes)
GWSSH=/home/hermes/gateway-ssh
STATE=/home/hermes/gateway-state
PROBE="$GWSSH/m03-probe.py"

mp_require_apply 'would relabel the transport probe and re-run it'
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

run_probe() {
  h podman exec --user 10000:10000 --workdir /opt/hermes hermes-gateway \
    /opt/hermes/.venv/bin/python3 /opt/hermes/gateway-ssh/m03-probe.py 2>&1
}

rc=0
{
  echo "### M04 post-reboot probe correction"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  echo "===== profile config is unchanged (backend must be ssh) ====="
  grep -nA3 '^terminal:' "$STATE/config.yaml" 2>&1 | head -n 8 || true
  backend_lines=$(grep -c '^  backend: ssh' "$STATE/config.yaml" 2>/dev/null || true)
  echo "backend_lines=${backend_lines:-0}"
  mp_check profile_backend_ssh "$([ "${backend_lines:-0}" -ge 1 ] && echo PASS || echo FAIL)"
  echo

  echo "===== labels before ====="
  ls -lZ "$GWSSH" 2>&1
  echo

  echo "===== relabel the probe like its mounted siblings ====="
  chcon --reference="$GWSSH/known_hosts" "$PROBE" 2>&1
  echo "chcon_rc=$?"
  ls -lZ "$PROBE" 2>&1
  echo

  echo "===== probe attempt 1 (in the running gateway) ====="
  out1=$(run_probe)
  rc1=$?
  printf '%s\n' "$out1" | tail -n 8
  echo "probe_rc=$rc1"
  echo

  if [ "$rc1" -ne 0 ]; then
    echo "===== attempt 1 failed: the run stops here rather than restarting a healthy service ====="
    echo "Restarting the gateway would relabel the :Z mount, but it would also hide an"
    echo "unexplained failure. Inspect the labels and the AVC record, then re-run."
    mp_check transport_probe FAIL "probe rc=$rc1 after relabelling"
  else
    mp_check transport_probe PASS
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
