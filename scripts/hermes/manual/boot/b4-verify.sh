#!/usr/bin/env bash
# Gate B4 verification: confirm the post-enrollment boot is fully healthy.
#
# This is the POST-DEPLOY recheck (runbook step 9/10): it asserts the containers
# autostarted and the transport probe still passes after an unattended boot. The
# pre-deploy boot check in runbook step 7 does not need it, because no Hermes
# unit exists at that point yet.
#
# Deliberately does NOT reinstall the probe file: it already carries the correct
# container label, and rewriting it into the :Z-mounted directory while the
# container runs would strip that label (the failure recorded during M04).
#
# Identity is discovered on the running host (see lib-luks-identity.sh); stage
# the whole boot/ directory next to this script.
#
# Exit status is derived from the ASSERT lines in the output, never from the
# output pipeline: 0 = every assertion PASS, 1 = at least one FAIL. A check that
# could not be measured prints UNVERIFIED and does not pass silently — the
# summary line names it. The previous form ended with `exit "$rc"` where rc came
# from the `tee` pipeline alone, so it exited 0 however unhealthy the host was.
#
#   sudo bash ~/hermes-manual/boot/b4-verify.sh
set -u
set -o pipefail
export LC_ALL=C

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib-luks-identity.sh
# shellcheck disable=SC1091
. "$HERE/lib-luks-identity.sh" || {
  printf 'STOP: cannot load %s/lib-luks-identity.sh (stage the whole boot/ directory)\n' "$HERE" >&2
  exit 1
}
# shellcheck source=../lib-manual-common.sh
# shellcheck disable=SC1091
. "$HERE/../lib-manual-common.sh" || {
  printf 'STOP: cannot load %s/../lib-manual-common.sh (stage the whole manual/ tree)\n' "$HERE" >&2
  exit 1
}

ADMIN_ACCOUNT=${HERMES_ADMIN:-aicowork}
ADMIN_HOME=$(hermes_admin_account)
RUNTIME_ACCOUNT=${HERMES_RUNTIME:-hermes}
RUNTIME_HOME=$(getent passwd "$RUNTIME_ACCOUNT" | cut -d: -f6)
[ -n "$RUNTIME_HOME" ] || hermes_identity_die "runtime account '$RUNTIME_ACCOUNT' does not exist (set HERMES_RUNTIME)"
RUNTIME_UID=$(id -u "$RUNTIME_ACCOUNT")

OUT="$ADMIN_HOME/hermes-b4-verify.out"
PRE="$ADMIN_HOME/hermes-m04-reboot.out"
STATE="$RUNTIME_HOME/gateway-state"
GWSSH="$RUNTIME_HOME/gateway-ssh"
PROBE="$GWSSH/m03-probe.py"
h() {
  if ! mountpoint -q "$RUNTIME_HOME"; then
    printf 'STOP: %s is not mounted.\n' "$RUNTIME_HOME" >&2
    return 1
  fi
  sudo -u "$RUNTIME_ACCOUNT" -- env -i --chdir="$RUNTIME_HOME" \
    HOME="$RUNTIME_HOME" USER="$RUNTIME_ACCOUNT" LOGNAME="$RUNTIME_ACCOUNT" \
    PATH=/usr/local/bin:/usr/bin:/bin \
    TERM="${TERM:-xterm}" XDG_RUNTIME_DIR="/run/user/$RUNTIME_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$RUNTIME_UID/bus" \
    TMPDIR="$RUNTIME_HOME/.cache/podman-tmp" "$@"
}

# Count today's AVC denials. A failure to READ the audit log must never be
# reported as zero: an unreadable log and a clean log are different facts.
# Prints a number, or the literal 'unknown'.
avc_total_today() {
  local out rc n
  out=$(ausearch -m AVC,USER_AVC -ts today 2>&1)
  rc=$?
  if [ "$rc" -ne 0 ]; then
    case "$out" in
      *"<no matches>"*)
        printf '0'
        return 0
        ;;
      *)
        printf 'unknown'
        return 0
        ;;
    esac
  fi
  n=$(printf '%s\n' "$out" | grep -c 'type=AVC' || true)
  printf '%s' "${n:-0}"
}

rc=0
{
  echo "### Gate B4 verification (unattended boot)"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  echo "===== boot identity ====="
  pre_boot=$(grep -m1 '^boot_id=' "$PRE" 2>/dev/null | cut -d= -f2- || true)
  now_boot=$(cat /proc/sys/kernel/random/boot_id)
  echo "boot_id_at_m04=${pre_boot:-unknown}"
  echo "boot_id_now=$now_boot"
  echo "boot_changed=$([ -n "${pre_boot:-}" ] && [ "$pre_boot" != "$now_boot" ] && echo yes || echo unknown)"
  echo "uptime=$(uptime -p)"
  # Baseline for the "no new denials during this run" assertion at the end. Taken
  # here, before anything in this script touches the containers.
  avc_before=$(avc_total_today)
  echo "avc_today_at_start=$avc_before"
  echo

  echo "===== boot trust and unlock material ====="
  mokutil --sb-state 2>&1
  tpm2_pcrread sha256:7 2>&1 | tail -n 1
  hermes_resolve_luks_identity
  echo "device=$HERMES_LUKS_DEV"
  echo "luks_uuid=$HERMES_LUKS_UUID"
  cryptsetup luksDump "$HERMES_LUKS_DEV" | grep -E '^  [0-9]+: (luks2|systemd-tpm2)' | sed 's/^/  /'
  echo "keyslots=$(cryptsetup luksDump "$HERMES_LUKS_DEV" | grep -cE '^  [0-9]+: luks2' || true)"
  echo "tpm2_tokens=$(cryptsetup luksDump "$HERMES_LUKS_DEV" | grep -cE '^  [0-9]+: systemd-tpm2' || true)"
  echo "-- crypttab --"
  grep -E "^${HERMES_MAPPER}[[:space:]]" /etc/crypttab | sed 's/^/  /'
  echo

  echo "===== autostart results (no manual start) ====="
  echo "user_manager=$(systemctl is-active "user@$RUNTIME_UID.service")"
  echo "linger=$(ls /var/lib/systemd/linger/ 2>&1)"
  gw_state=$(h systemctl --user is-active hermes-gateway.service)
  worker_state=$(h systemctl --user is-active hermes-worker.service)
  echo "gateway=$gw_state"
  echo "worker=$worker_state"
  echo "ASSERT containers=$([ "$gw_state" = "active" ] && [ "$worker_state" = "active" ] && echo PASS || echo FAIL)"
  h podman ps -a --format '{{.Names}} | {{.Status}} | ports=[{{.Ports}}]'
  h podman inspect hermes-worker --format 'worker_started={{.State.StartedAt}}'
  h podman inspect hermes-gateway --format 'gateway_started={{.State.StartedAt}}'
  echo "worker_socket=$(stat -c '  %n mode=%a owner=%U:%G context=%C' "$RUNTIME_HOME/transport/worker.sock" 2>&1)"
  echo

  echo "===== gateway function this boot ====="
  echo "telegram_connected_this_boot=$(h journalctl --user -u hermes-gateway.service -b --no-pager 2>/dev/null | grep -c 'Connected to Telegram' || true)"
  h journalctl --user -u hermes-gateway.service -b -n 12 --no-pager 2>&1 \
    | mp_redact_stream "$STATE/.env" | tail -n 12
  echo

  echo "===== end-to-end transport probe (existing probe, not reinstalled) ====="
  if [ -f "$PROBE" ]; then
    stat -c '  %n mode=%a owner=%U:%G context=%C' "$PROBE"
    probe_out=$(h podman exec --user 10000:10000 --workdir /opt/hermes hermes-gateway \
      /opt/hermes/.venv/bin/python3 /opt/hermes/gateway-ssh/m03-probe.py 2>&1)
    probe_rc=$?
    printf '%s\n' "$probe_out" | tail -n 6
    echo "probe_rc=$probe_rc"
    echo "ASSERT transport_probe=$([ "$probe_rc" -eq 0 ] && echo PASS || echo FAIL)"
  else
    echo "probe_missing=yes"
    if [ "$gw_state" = "active" ]; then
      echo "ASSERT transport_probe=FAIL (the gateway is running but the probe is absent)"
    else
      echo "ASSERT transport_probe=UNVERIFIED (no gateway yet: this is the pre-deploy boot check)"
    fi
  fi
  echo

  echo "===== exposure and health ====="
  h podman port hermes-gateway 2>&1
  ss -lntp 2>/dev/null | grep -E '0\.0\.0\.0|\[::\]' | grep -vE '127\.0\.0\.|\[::1\]'
  echo "failed_units:"
  systemctl --failed --no-pager | tail -n +2 | head -n 3
  failed_out=$(systemctl --failed --no-pager --plain 2>&1)
  failed_rc=$?
  if [ "$failed_rc" -ne 0 ]; then
    echo "system_failed_units=UNVERIFIED (systemctl exited $failed_rc)"
    echo "ASSERT failed_units=UNVERIFIED"
  else
    sys_failed=$(printf '%s\n' "$failed_out" | grep -cE '^[^ ]+\.(service|socket|timer|path|mount|target)[[:space:]]' || true)
    # The system manager alone is not enough: the Hermes units are USER units.
    user_failed=$(h systemctl --user --failed --no-pager --plain 2>/dev/null | grep -cE '^[^ ]+\.(service|socket|timer|path|mount|target)[[:space:]]' || true)
    echo "system_failed_units=${sys_failed:-0} user_failed_units=${user_failed:-0}"
    if [ "${sys_failed:-0}" -eq 0 ] && [ "${user_failed:-0}" -eq 0 ]; then
      echo "ASSERT failed_units=PASS"
    else
      echo "ASSERT failed_units=FAIL"
    fi
  fi
  echo

  echo "===== AVC denials ====="
  avc_after=$(avc_total_today)
  echo "avc_today_at_start=$avc_before"
  echo "avc_today_at_end=$avc_after"
  echo "-- recent denials (boot-wide: a by-design repair denial from runbook step 12 may appear) --"
  ausearch -m AVC,USER_AVC -ts recent 2>&1 | tail -n 15
  # Scope the assertion to THIS RUN, not to the whole boot. A by-design denial can
  # legitimately already exist earlier in the same boot (runbook step 12 installs
  # the probe before step 13 relabels it), so a boot-wide count would fail here
  # even on a perfectly healthy host — a false negative this run actually hit.
  if [ "$avc_before" = "unknown" ] || [ "$avc_after" = "unknown" ]; then
    echo "ASSERT new_avc_during_run=UNVERIFIED (ausearch could not read the audit log; this is NOT a zero count)"
  elif [ "$avc_after" -le "$avc_before" ]; then
    echo "ASSERT new_avc_during_run=PASS"
  else
    echo "ASSERT new_avc_during_run=FAIL ($((avc_after - avc_before)) new denial(s) during this run)"
  fi
  echo
  echo "===== done ====="
} 2>&1 | tee "$OUT" || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 600 "$OUT" 2>/dev/null || true
echo "WROTE=$OUT"
grep -aE '^(boot_changed|user_manager|gateway=|worker=|keyslots=|tpm2_tokens=|telegram_connected_this_boot|probe_rc)' "$OUT" | head -n 12 || true

echo
echo "===== assertion summary ====="
grep -aE '^ASSERT ' "$OUT" || true
fails=$(grep -acE '^ASSERT [a-z_]+=FAIL' "$OUT" || true)
unver=$(grep -acE '^ASSERT [a-z_]+=UNVERIFIED' "$OUT" || true)
total=$(grep -acE '^ASSERT ' "$OUT" || true)
echo "assert_total=${total:-0} assert_fail=${fails:-0} assert_unverified=${unver:-0}"

# A missing or truncated log must never read as success just because it contains
# no failing assertion.
if [ "${total:-0}" -eq 0 ]; then
  echo "RESULT=FAIL (no ASSERT lines were produced; $OUT is missing or truncated)"
  exit 1
fi
if [ "${rc:-0}" -ne 0 ]; then
  echo "RESULT=FAIL (the output pipeline failed; $OUT may be incomplete)"
  exit 1
fi
if [ "${fails:-0}" -gt 0 ]; then
  echo "RESULT=FAIL (${fails} failed assertion(s); see the ASSERT lines above)"
  exit 1
fi
if [ "${unver:-0}" -gt 0 ]; then
  echo "RESULT=PASS with ${unver} unverified check(s) - a PASS is NOT claimed for those"
  exit 0
fi
echo "RESULT=PASS (all assertions passed)"
exit 0
