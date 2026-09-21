#!/usr/bin/env bash
# M04 step 1: remove duplicated credential copies, capture the effective runtime
# posture (identity, capabilities, seccomp, SELinux, mounts, limits), and apply
# the parent slice budget.
#
# Default is inspect-only; re-run with --apply to make changes.
#
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/m04-posture.sh --apply
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
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m04-posture.out")
HERMES_UID=$(id -u hermes)
SLICE="user-${HERMES_UID}.slice"
SLICE_DROPIN="/etc/systemd/system/${SLICE}.d/50-hermes-limits.conf"

# Host-appropriate starting budgets; override for a larger host. These are
# emergency containment, not benchmark results.
MEMORY_HIGH="${HERMES_SLICE_MEMORY_HIGH:-6G}"
MEMORY_MAX="${HERMES_SLICE_MEMORY_MAX:-8G}"
TASKS_MAX="${HERMES_SLICE_TASKS_MAX:-1536}"

mp_require_apply 'would remove duplicate credential copies and write the parent slice budget'
mp_require_host_identity
mp_lock_profile
mp_install_trap
mp_require_tools podman systemctl

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
  echo "### M04 step 1: credential cleanup, runtime posture, limits"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  echo "===== credential files in the profile home ====="
  ls -la /home/hermes/gateway-state/.env* 2>&1
  echo
  echo "===== remove duplicated credential copies ====="
  found=0
  for f in /home/hermes/gateway-state/.env.pre-hardening-*; do
    [ -e "$f" ] || continue
    found=1
    echo "removing $(basename "$f") mode=$(stat -c %a "$f") size=$(stat -c %s "$f") sha256=$(mp_sha256 "$f" | cut -c1-16)"
    rm -f "$f"
  done
  [ "$found" -eq 0 ] && echo "(no duplicate copies present)"
  remaining=$(ls /home/hermes/gateway-state/.env.pre-hardening-* 2>/dev/null | wc -l)
  mp_check no_duplicate_credentials "$([ "$remaining" -eq 0 ] && echo PASS || echo FAIL)" "$remaining duplicate file(s) remain"
  echo

  echo "===== reinstall the contract-driven hardening helper (convergent) ====="
  result=$(mp_install_reconcile contract_harden_helper_installed 0644 hermes:hermes \
    "$BUNDLE/config/harden-config.py" /home/hermes/gateway-ssh/manual-harden-config.py) || exit 1
  echo "$result"
  result=$(mp_install_reconcile contract_file_installed 0644 hermes:hermes \
    "$BUNDLE/config/profile-contract.yaml" /home/hermes/gateway-ssh/profile-contract.yaml) || exit 1
  echo "$result"
  mp_check contract_helper_installed "$([ -r /home/hermes/gateway-ssh/manual-harden-config.py ] && echo PASS || echo FAIL)"
  echo

  echo "===== container security posture ====="
  for c in hermes-worker hermes-gateway; do
    echo "-- $c --"
    h podman inspect "$c" \
      --format 'readonly={{.HostConfig.ReadOnly}} memory={{.HostConfig.Memory}} pids={{.HostConfig.PidsLimit}} netmode={{.HostConfig.NetworkMode}} userns={{.HostConfig.UsernsMode}}
securityopt={{.HostConfig.SecurityOpt}}
capdrop={{.HostConfig.CapDrop}} capadd={{.HostConfig.CapAdd}}
selinux={{.HostConfig.SelinuxOpts}} privileged={{.HostConfig.Privileged}}
binds={{range .HostConfig.Binds}}{{.}} {{end}}' 2>&1 || true
  done
  worker_net=$(h podman inspect hermes-worker --format '{{.HostConfig.NetworkMode}}' 2>/dev/null || true)
  mp_check worker_network_none "$([ "$worker_net" = none ] && echo PASS || echo FAIL)" "network mode is '$worker_net'"
  worker_uid=$(h podman inspect hermes-worker --format '{{range .Config.User}}{{.}}{{end}}' 2>/dev/null || true)
  echo "worker_config_user=${worker_uid:-<image default>}"
  echo

  echo "===== effective process posture inside the worker ====="
  # Expansion inside the container's script is intended; the outer shell must not expand it.
  # shellcheck disable=SC2016
  posture=$(h podman exec hermes-worker sh -c '
    id
    grep -E "^(NoNewPrivs|Seccomp|CapEff|CapBnd):" /proc/self/status
    echo "mountinfo_lines=$(wc -l < /proc/self/mountinfo)"
    echo "root_write_probe:"
    ( touch /m04-readonly-probe 2>&1 && echo "WRITABLE_UNEXPECTED" && rm -f /m04-readonly-probe ) || echo "READONLY_OK"
    echo "tmp_write_probe:"
    ( touch /tmp/m04-probe 2>&1 && echo "TMP_WRITABLE_OK" && rm -f /tmp/m04-probe ) || echo "TMP_NOT_WRITABLE"
  ' 2>&1)
  printf '%s\n' "$posture"
  mp_check worker_root_readonly "$([[ "$posture" == *READONLY_OK* && "$posture" != *WRITABLE_UNEXPECTED* ]] && echo PASS || echo FAIL)"
  mp_check worker_tmp_writable "$([[ "$posture" == *TMP_WRITABLE_OK* ]] && echo PASS || echo FAIL)"
  mp_check worker_nnp "$([[ "$posture" == *'NoNewPrivs:	1'* || "$posture" == *'NoNewPrivs: 1'* ]] && echo PASS || echo FAIL)"
  echo

  echo "===== SELinux labels on the shared and private mounts ====="
  ls -ldZ /home/hermes/transport /home/hermes/gateway-ssh /home/hermes/worker-state /home/hermes/gateway-state 2>&1
  # ps -eZ is the readable way to show SELinux process labels here.
  # shellcheck disable=SC2009
  ps -eZ 2>/dev/null | grep -m3 container_t || true
  echo

  echo "===== unit resource properties (before) ====="
  for u in hermes-worker.service hermes-gateway.service; do
    echo "-- $u --"
    h systemctl --user show "$u" -p MemoryMax -p MemoryHigh -p TasksMax -p PidsLimit 2>&1 || true
  done
  systemctl show "$SLICE" -p MemoryHigh -p MemoryMax -p TasksMax 2>&1 || true
  echo

  echo "===== persist the parent slice budget (convergent) ====="
  # `systemctl set-property` is runtime-only on this platform (recorded during
  # the clean-install validation), so the durable mechanism is the drop-in.
  install -d -m 0755 "/etc/systemd/system/${SLICE}.d"
  dropin_candidate="${SLICE_DROPIN}.new.$$"
  cat >"$dropin_candidate" <<CONF
[Slice]
MemoryHigh=${MEMORY_HIGH}
MemoryMax=${MEMORY_MAX}
TasksMax=${TASKS_MAX}
CONF
  chmod 0644 "$dropin_candidate"
  if mp_content_differs "$SLICE_DROPIN" "$dropin_candidate"; then
    mv -f -- "$dropin_candidate" "$SLICE_DROPIN"
    systemctl daemon-reload
    echo "daemon_reload_rc=$? (drop-in changed)"
  else
    rm -f -- "$dropin_candidate"
    echo "drop-in unchanged; no rewrite and no daemon-reload"
  fi
  systemctl show "$SLICE" -p MemoryHigh -p MemoryMax -p TasksMax 2>&1 || true
  slice_high=$(systemctl show "$SLICE" -p MemoryHigh --value 2>/dev/null || true)
  mp_check slice_memory_high "$([ -n "$slice_high" ] && [ "$slice_high" != "infinity" ] && echo PASS || echo FAIL)" "MemoryHigh='$slice_high'"
  echo

  echo "===== worker healthy after limits ====="
  sleep 3
  worker_state=$(h systemctl --user is-active hermes-worker.service)
  echo "worker_state=$worker_state"
  mp_check worker_active "$([ "$worker_state" = active ] && echo PASS || echo FAIL)"
  h podman ps --format '{{.Names}} | {{.Status}}' || true
  echo

  echo "===== recent AVC denials ====="
  mp_audit_avc_check avc_denials recent
  echo "===== done ====="
} 2>&1 | tee "$OUT" || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
echo "WROTE=$OUT"
mp_finalize "$OUT" "${rc:-0}"
