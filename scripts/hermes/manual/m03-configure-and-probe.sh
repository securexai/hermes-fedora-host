#!/usr/bin/env bash
# M03 step 2: write the profile terminal backend and probe real routing.
#
# Default is inspect-only; re-run with --apply to make changes.
#
# Precedence, as resolved from the pinned release's own source
# (tools/terminal_scope.py, hermes_cli/config.py):
#   * While a profile terminal scope is bound, terminal policy resolves ONLY from
#     the profile's /opt/data/.env and /opt/data/config.yaml. The Quadlet's
#     TERMINAL_* environment is the authority for unscoped CLI runs only.
#   * config.yaml terminal.* keys are therefore authoritative for the gateway and
#     must stay consistent with the Quadlet values.
# This helper no longer deletes a stale profile: an incompatible config is
# reported and left in place, because asserting a schema version this procedure
# cannot substantiate would be a compatibility claim it has not earned.
#
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/m03-configure-and-probe.sh --apply
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
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m03-configure.out")
RUNTIME_ACCOUNT="${HERMES_RUNTIME:-hermes}"
RUNTIME_HOME="${HERMES_RUNTIME_HOME:-/home/${RUNTIME_ACCOUNT}}"
HERMES_UID=$(id -u "$RUNTIME_ACCOUNT")
GW_UID=10000
GW=hermes-gateway
GW_STATE="$RUNTIME_HOME/gateway-state"
GWSSH="$RUNTIME_HOME/gateway-ssh"
GW_IMAGE=docker.io/nousresearch/hermes-agent@sha256:fca358f12efd65bfaaca05884166f15c0e2788375ca30d77061ac1ebc96452b7
CLIENT_KEY=/opt/hermes/gateway-ssh/worker_client_ed25519
EXPECTED=(terminal.backend=ssh terminal.ssh_host=worker terminal.ssh_user=worker terminal.ssh_port=22 "terminal.ssh_key=$CLIENT_KEY")
PROBE="$GWSSH/m03-probe.py"

mp_require_apply 'would write the profile terminal backend and restart the gateway'
mp_require_host_identity
mp_lock_profile
mp_install_trap
mp_require_tools podman

h() {
  if ! mountpoint -q "$RUNTIME_HOME"; then
    printf 'STOP: %s is not mounted.\n' "$RUNTIME_HOME" >&2
    return 1
  fi
  sudo -u "$RUNTIME_ACCOUNT" -- env -i --chdir="$RUNTIME_HOME" \
    HOME="$RUNTIME_HOME" USER="$RUNTIME_ACCOUNT" LOGNAME="$RUNTIME_ACCOUNT" \
    PATH=/usr/local/bin:/usr/bin:/bin \
    TERM="${TERM:-xterm}" XDG_RUNTIME_DIR="/run/user/$HERMES_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$HERMES_UID/bus" \
    TMPDIR="$RUNTIME_HOME/.cache/podman-tmp" "$@"
}

# One-shot command in the pinned gateway image, as the runtime identity, with
# the same mounts the service uses. No s6 bootstrap, so it is fast and repeatable.
gcone() {
  entry="$1"
  shift
  h podman run --rm --network none --user "$GW_UID:$GW_UID" --workdir /opt/hermes \
    -v "$GW_STATE":/opt/data:z \
    -v "$RUNTIME_HOME/transport:/run/hermes-transport:z" \
    -v "$GWSSH":/opt/hermes/gateway-ssh:ro,Z \
    -v "$GWSSH/ssh":/opt/hermes/bin/ssh:ro,Z \
    -v "$GWSSH/scp":/opt/hermes/bin/scp:ro,Z \
    -v "$GWSSH/sftp":/opt/hermes/bin/sftp:ro,Z \
    --entrypoint "$entry" "$GW_IMAGE" "$@"
}

# Gateway runtime state is the authority for whether a private mount is live. The
# unit text is NOT: a unit that is not known to be active may still have a
# running container holding the mount. `unknown` refuses everything, because
# mounting the private tree with `:z`/`:Z` while it may be live would invalidate
# the running gateway's own labels.
gw_container=$(mp_container_state h "$GW") || true
gw_prior_known=1
gw_prior=$(mp_capture_service_state h hermes-gateway.service) || gw_prior_known=0

# A restoration obligation exists whenever the gateway was conclusively active OR
# its container is provably running: either way, a stop by this run must be
# undone. When neither is known, this helper must not stop anything.
gw_restore_obligation=0
if [ "$gw_prior" = active ] || [ "$gw_container" = running ]; then
  gw_restore_obligation=1
fi
prior_ok=1
if [ "$gw_prior_known" -eq 0 ] && [ "$gw_container" != running ]; then
  prior_ok=0
fi

# gcur — run a command against the profile WITHOUT creating a new container mount
# while the gateway container is running. `podman run -v ...:z` makes Podman
# relabel the host path, and doing that while the container holds the same
# private state is the churn this helper must avoid; `podman exec` reuses the
# live container's mount and relabels nothing. The exec keeps the runtime
# identity explicit: exec does NOT inherit the supervised process's dropped UID,
# so `--user 10000:10000 --workdir /opt/hermes` is required for the read or probe
# to exercise the gateway's actual identity. A one-shot `podman run` is used ONLY
# when a successful inventory proves the container is not running.
gcur() {
  local st
  st=$(mp_container_state h "$GW") || true
  case "$st" in
    running) h podman exec --user "$GW_UID:$GW_UID" --workdir /opt/hermes "$GW" "$@" ;;
    stopped) gcone "$@" ;;
    *)
      printf 'STOP: cannot determine whether %s is running; refusing to create a private mount\n' "$GW" >&2
      return 1
      ;;
  esac
}

# Trap-registered so an early failure or an interrupt still restores a gateway
# this helper stopped. Idempotent: acts only when the state differs.
restore_gateway_state() {
  local now container_now rc=0
  now=$(h systemctl --user is-active hermes-gateway.service 2>/dev/null || true)
  if [ "$gw_restore_obligation" -eq 1 ] && [ "$now" != "active" ]; then
    # Only start when the container is not still running: an unreadable unit
    # query with a live container is not a stopped gateway.
    container_now=$(mp_container_state h "$GW") || true
    if [ "$container_now" = running ]; then
      printf 'gateway container is still running; no start needed\n'
    else
      printf 'restoring gateway service state (prior=%s, now=%s)\n' "${gw_prior:-unknown}" "${now:-unknown}"
      if ! h systemctl --user start hermes-gateway.service; then
        printf 'RESTORE_FAILED gateway service was active before this run and could not be restarted\n' >&2
        rc=1
      fi
    fi
  fi
  printf 'gateway_state_at_exit=%s\n' "$(h systemctl --user is-active hermes-gateway.service 2>/dev/null || true)"
  return "$rc"
}
mp_on_cleanup restore_gateway_state

rc=0
{
  echo "### M03 step 2: profile terminal config + backend probe"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  if [ "$gw_container" = unknown ]; then
    echo "STOP: cannot determine whether $GW is running (the container inventory query failed)."
    echo "      Refusing to read or relabel any private mount: a possibly-live :Z mount"
    echo "      would invalidate the running gateway's own labels."
    mp_check gateway_container_state FAIL "podman could not prove whether $GW is running"
    mp_check config_schema_version NOT_APPLICABLE "skipped: the container state is undetermined"
    mp_check readback_terminal_backend FAIL "skipped: the container state is undetermined"
    mp_check readback_terminal_ssh_host FAIL "skipped: the container state is undetermined"
    mp_check readback_terminal_ssh_user FAIL "skipped: the container state is undetermined"
    mp_check readback_terminal_ssh_port FAIL "skipped: the container state is undetermined"
    mp_check readback_terminal_ssh_key FAIL "skipped: the container state is undetermined"
    mp_check terminal_backend_probe FAIL "skipped: the container state is undetermined"
    mp_audit_avc_check avc_denials recent
    echo "===== done ====="
    exit 1
  fi
  echo "container_state=$gw_container prior=$gw_prior prior_ok=$prior_ok"
  echo

  echo "===== profile terminal drift check (before touching any service) ====="
  # Read the current values FIRST, through gcur so a running gateway is queried
  # with `podman exec` and its live private mount is never relabelled. A converged
  # profile must not stop a healthy gateway, and a live mount must not be touched.
  drift=0
  for pair in "${EXPECTED[@]}"; do
    key=${pair%%=*}
    value=${pair#*=}
    current=$(gcur /opt/hermes/bin/hermes config get "$key" 2>&1 | tail -n 1)
    if [ "$current" = "$value" ]; then
      echo "state[$key]=$current (matches)"
    else
      echo "state[$key]=${current:-<unset>} (expected $value)"
      drift=1
    fi
  done
  probe_differs=0
  mp_content_differs "$PROBE" "$BUNDLE/gateway/m03-probe.py" && probe_differs=1
  echo "config_drift=$drift probe_differs=$probe_differs"
  if [ "$drift" -eq 0 ] && [ "$probe_differs" -eq 0 ]; then
    echo "profile terminal config and probe already converged; no service stop and no relabel"
    mp_info config_converged "no drift; the service is left running and the live mount is untouched"
    need_stop=0
  else
    mp_info config_converged "drift or a changed probe; applying before probing"
    need_stop=1
  fi
  echo

  apply_ok=0
  config_ok=0
  readback_ok=0
  probe_ok=0
  if [ "$need_stop" -ne 1 ]; then
    echo "===== no config change needed; the service was never stopped ====="
    echo
  elif [ "$prior_ok" -ne 1 ]; then
    echo "===== the pre-run gateway state is undeterminable; refusing to stop it ====="
    # Stopping a unit whose prior state cannot be read risks stranding it: the
    # restoration hook cannot know whether it must be started again.
    mp_check gateway_stopped FAIL "the pre-run service state is undetermined, so no safe restoration could be guaranteed"
    mp_check gateway_configured FAIL "skipped because the pre-run service state could not be determined"
    echo
  else
    echo "===== stop the gateway while configuring (its private mount is live) ====="
    stop_rc=0
    h systemctl --user stop hermes-gateway.service 2>/dev/null || stop_rc=$?
    gw_now=$(h systemctl --user is-active hermes-gateway.service 2>/dev/null || true)
    # The unit text alone is not proof the private mount is dead: a container can
    # outlive a unit that reports inactive. The successful inventory is required.
    gw_container_now=$(mp_container_state h "$GW") || true
    echo "gateway_state=${gw_now:-<no output>} container_state=$gw_container_now (stop_rc=$stop_rc)"
    if [ "$stop_rc" -eq 0 ] \
      && { [ "$gw_now" = inactive ] || [ "$gw_now" = dead ]; } \
      && [ "$gw_container_now" = stopped ]; then
      mp_check gateway_stopped PASS "the unit is stopped and no container holds the private mount"
      apply_ok=1
    else
      # Mutating while the container may still hold the live mount is exactly the
      # relabel churn this helper avoids, so fail instead of proceeding.
      mp_check gateway_stopped FAIL "the gateway is not conclusively quiescent (state=${gw_now:-unknown} container=${gw_container_now:-unknown} stop_rc=$stop_rc); refusing to touch its live mount"
      mp_check gateway_configured FAIL "skipped because the gateway could not be stopped"
    fi
    echo

    if [ "$apply_ok" -eq 1 ]; then
      if [ "$probe_differs" -eq 1 ]; then
        echo "===== install probe (only after the mount is no longer live) ====="
        mp_install_reconcile gateway_probe_installed 0644 hermes:hermes \
          "$BUNDLE/gateway/m03-probe.py" "$PROBE" || exit 1
        # A file created inside a :Z mount while its container runs keeps the host
        # default label; give it the same label as its mounted siblings.
        chcon --reference="$GWSSH/known_hosts" "$PROBE" 2>/dev/null \
          || chcon -t container_file_t "$PROBE" 2>/dev/null || true
        stat -c 'probe_mode=%a owner=%U:%G context=%C' "$PROBE"
        echo
      else
        echo "probe already current; no relabel of the private mount"
        echo
      fi

      echo "===== write the SSH terminal backend ====="
      set_fail=0
      for pair in "${EXPECTED[@]}"; do
        key=${pair%%=*}
        value=${pair#*=}
        current=$(gcur /opt/hermes/bin/hermes config get "$key" 2>&1 | tail -n 1)
        if [ "$current" = "$value" ]; then
          echo "set[$key] skipped: already '$value' (convergent, no config rewrite)"
          continue
        fi
        out=$(gcur /opt/hermes/bin/hermes config set "$key" "$value" 2>&1)
        rc_set=$?
        printf '%s\n' "$out" | tail -n 4
        echo "set[$key]_rc=$rc_set"
        [ "$rc_set" -eq 0 ] || set_fail=1
      done
      if [ "$set_fail" -eq 0 ]; then
        mp_check gateway_configured PASS "the terminal backend was written or already correct"
        config_ok=1
      else
        mp_check gateway_configured FAIL "at least one terminal config set failed"
      fi
      echo
    fi
  fi

  echo "===== existing profile config (report only, never deleted) ====="
  if [ -f "$GW_STATE/config.yaml" ]; then
    stat -c 'size=%s owner=%U:%G mode=%a sha256=' "$GW_STATE/config.yaml"
    mp_sha256 "$GW_STATE/config.yaml"
    echo "-- config schema version --"
    on_disk=$(grep -E '^_config_version:' "$GW_STATE/config.yaml" | head -n1 | awk '{print $2}')
    echo "on_disk_version=${on_disk:-absent}"
    if [ -z "${on_disk:-}" ]; then
      echo "NOTE: an absent _config_version cannot be evaluated against the upstream"
      echo "      migration floor. The value is left untouched; this helper does not"
      echo "      invent a schema version. It is informational, not a pass."
      mp_info config_schema_version "no _config_version on disk to evaluate (left untouched by design)"
    else
      mp_check config_schema_version PASS "on_disk_version=$on_disk (left in place)"
    fi
  else
    echo "(config.yaml absent; the pinned image will generate one)"
    mp_check config_schema_version NOT_APPLICABLE "no profile config yet"
  fi
  echo

  echo "===== resolved config readback ====="
  # gcur again: an active gateway is read with `podman exec`, never with a new
  # mount, so the converged path stays free of live-mount relabels.
  readback_fail=0
  for pair in "${EXPECTED[@]}"; do
    key=${pair%%=*}
    expected=${pair#*=}
    actual=$(gcur /opt/hermes/bin/hermes config get "$key" 2>&1 | tail -n 1)
    printf '%s=%s\n' "$key" "$actual"
    if [ "$actual" = "$expected" ]; then
      mp_check "readback_${key//./_}" PASS "expected '$expected', got '$actual'"
    else
      mp_check "readback_${key//./_}" FAIL "expected '$expected', got '$actual'"
      readback_fail=1
    fi
  done
  if [ "$readback_fail" -eq 0 ]; then
    readback_ok=1
  fi
  echo

  echo "===== real backend probe as UID 10000 ====="
  probe_out=$(gcur /opt/hermes/.venv/bin/python3 /opt/hermes/gateway-ssh/m03-probe.py 2>&1)
  probe_rc=$?
  printf '%s\n' "$probe_out"
  echo "probe_rc=$probe_rc"
  if [ "$probe_rc" -eq 0 ] && [[ "$probe_out" == *RESULT=PASS* ]]; then
    mp_check terminal_backend_probe PASS
    probe_ok=1
  else
    mp_check terminal_backend_probe FAIL "the SSH backend did not reach the worker (rc=$probe_rc)"
  fi
  echo

  echo "===== gateway unit state (Gate 3 owns daemon stability) ====="
  # A converged run makes NO lifecycle change: it neither stops nor starts the
  # unit. Only a run that stopped the gateway to reconfigure it brings it back.
  # The 20-second stability observation is a deliberate daemon probe that only
  # runs after a real change, and it is deferred to Gate 3 either way.
  gw_state=$(h systemctl --user is-active hermes-gateway.service 2>/dev/null || true)
  # A run that stopped the gateway may start it again ONLY when every required
  # configuration check passed. `apply_ok` means the STOP succeeded, not that the
  # configuration was written or read back correctly: starting on a failed apply
  # would leave a previously inactive gateway running with known-bad terminal
  # configuration and no restoration obligation to undo that start. A gateway that
  # was active before this run is restored by the cleanup hook regardless.
  activate_ok=0
  if [ "$need_stop" -eq 1 ] && [ "$apply_ok" -eq 1 ] \
    && [ "$config_ok" -eq 1 ] && [ "$readback_ok" -eq 1 ] && [ "$probe_ok" -eq 1 ]; then
    activate_ok=1
  fi
  if [ "$activate_ok" -eq 1 ]; then
    if [ "$gw_state" = active ]; then
      echo "gateway already active after configuration; start skipped (convergent)"
    else
      h systemctl --user start hermes-gateway.service
      echo "start_rc=$?"
    fi
    sleep 20
    gw_state=$(h systemctl --user is-active hermes-gateway.service)
    echo "gateway_state_after_20s=$gw_state"
    if [ "$gw_state" != "active" ]; then
      echo "gateway did not stay active (deferred to Gate 3); stopping it to avoid a restart loop"
      h systemctl --user stop hermes-gateway.service 2>/dev/null || true
    fi
  elif [ "$need_stop" -eq 1 ] && [ "$apply_ok" -eq 1 ]; then
    echo "gateway left stopped: required configuration/readback/probe did not pass (config_ok=$config_ok readback_ok=$readback_ok probe_ok=$probe_ok)"
  else
    echo "no lifecycle change this run; gateway_state=$gw_state"
  fi
  # Gate 2 explicitly excludes a stable long-running gateway: without a provider
  # credential the gateway is not expected to stay up. This is DEFERRED, not a
  # required check, and it is never recorded as a PASS.
  mp_defer gateway_stays_active \
    "Gate 3 owns gateway daemon stability; credential-free gateway is not a stable daemon (state=$gw_state)"
  h podman ps -a --format '{{.Names}} | {{.Status}} | ports=[{{.Ports}}]'
  h podman logs --tail 25 "$GW" 2>&1 | mp_redact_stream "$GW_STATE/.env" | tail -n 25
  echo

  echo "===== recent AVC denials ====="
  mp_audit_avc_check avc_denials recent
  echo "===== done ====="
} 2>&1 | tee "$OUT" || rc=$?

restore_rc=0
restore_gateway_state >>"$OUT" 2>&1 || restore_rc=$?
if [ "$restore_rc" -eq 0 ]; then
  printf 'CHECK restore_gateway_state=PASS\n' >>"$OUT"
else
  printf 'CHECK restore_gateway_state=FAIL "prior gateway state could not be restored"\n' >>"$OUT"
  printf 'RESTORE_FAILED gateway state restoration failed (see %s)\n' "$OUT" >&2
fi
chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
echo "WROTE=$OUT"
mp_finalize "$OUT" "${rc:-0}"
