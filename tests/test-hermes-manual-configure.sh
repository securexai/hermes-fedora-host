#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC1091,SC2034
# Behavioral tests for m03-configure-and-probe.sh (review R10).
#
# The REAL helper is driven with synthetic state and stubbed runtime commands,
# so no root, container, network or credential is involved. It asserts that a
# converged profile stops no service and relabels nothing, that drift is applied
# only after the private mount is no longer live, and that inspect mode touches
# nothing. C3/C4: the live read keeps the explicit runtime identity, and the
# container inventory (not the unit text) decides whether a private mount is
# live — a failed, transitional or divergent *container* state refuses mutation
# and never selects the one-shot relabel path. F2: a failed configuration or
# backend probe never newly activates a gateway that was inactive before the run.
#
#   ./tests/test-hermes-manual-configure.sh [-v]

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s nullglob

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
readonly SCRIPT_DIR
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
readonly REPO_ROOT
# shellcheck source=lib-test-helpers.sh
source "$SCRIPT_DIR/lib-test-helpers.sh"

readonly MANUAL="$REPO_ROOT/scripts/hermes/manual"
readonly CONFIGURE="$MANUAL/m03-configure-and-probe.sh"

VERBOSE=false
[[ "${1:-}" == -v ]] && VERBOSE=true

WORK=$(mktemp -d)
readonly WORK
trap 'rm -rf -- "$WORK"' EXIT

MACHINE_HASH=$(sha256sum /etc/machine-id | cut -d' ' -f1)
readonly MACHINE_HASH
readonly TEST_ADMIN='review-configure-admin'

SANDBOX="$WORK/sandbox"
STUB="$SANDBOX/stub"
STATES="$SANDBOX/states"
RUNTIME_HOME="$SANDBOX/home/hermes"
ADMIN_HOME="$SANDBOX/admin-home"
GW_STATE="$RUNTIME_HOME/gateway-state"
GWSSH="$RUNTIME_HOME/gateway-ssh"
CONFIG_STATE="$SANDBOX/config-state"
CALL_LOG="$SANDBOX/calls.log"
mkdir -p "$STUB" "$STATES" "$RUNTIME_HOME/transport" "$GW_STATE" "$GWSSH" "$ADMIN_HOME" "$SANDBOX/tmp"

write_stub() {
  local name="$1"
  cat >"$STUB/$name"
  chmod 0755 "$STUB/$name"
}

write_stub getent <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = passwd ] && [ "${2:-}" = "${TEST_ADMIN:-}" ]; then
  printf '%s:x:%s:%s::%s:/bin/bash\n' "$2" "$(/usr/bin/id -u)" "$(/usr/bin/id -g)" "${TEST_HOME}"
  exit 0
fi
exec /usr/bin/getent "$@"
EOF

write_stub id <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = -u ] && [ "${2:-}" = hermes ]; then printf '1001\n'; exit 0; fi
exec /usr/bin/id "$@"
EOF

write_stub mountpoint <<'EOF'
#!/usr/bin/env bash
exit 0
EOF

# A clean, readable audit log: ausearch exits non-zero with "<no matches>".
write_stub ausearch <<'EOF'
#!/usr/bin/env bash
printf '<no matches>\n'
exit 1
EOF

write_stub sleep <<'EOF'
#!/usr/bin/env bash
exit 0
EOF

write_stub chown <<'EOF'
#!/usr/bin/env bash
exit 0
EOF

# Translate `sudo -u hermes -- env -i ... <command>` into a plain local command.
write_stub sudo <<'EOF'
#!/usr/bin/env bash
args=("$@")
i=0
while [ "$i" -lt "${#args[@]}" ] && [ "${args[$i]}" != "--" ]; do i=$((i + 1)); done
i=$((i + 1))
while [ "$i" -lt "${#args[@]}" ]; do
  case "${args[$i]}" in
    env | -*) i=$((i + 1)) ;;
    *=*) i=$((i + 1)) ;;
    *) break ;;
  esac
done
exec "${args[@]:$i}"
EOF

# Record the ordering of stop vs relabel across the whole run, and provide
# failure injection for the stop path (R10/R3).
write_stub systemctl <<'EOF'
#!/usr/bin/env bash
printf 'systemctl %s\n' "$*" >>"${STUB_CALL_LOG:?}"
verb="${2:-}"
unit="${3:-}"
case "$verb" in
  is-active)
    # A bare forced status with no output is a genuine query failure (C4); a
    # forced state string models a transitional/undetermined value.
    if [ -n "${STUB_ISACTIVE_RC:-}" ]; then
      printf 'Failed to connect to user bus\n' >&2
      exit "$STUB_ISACTIVE_RC"
    fi
    if [ -n "${STUB_ISACTIVE_STATE:-}" ]; then printf '%s\n' "$STUB_ISACTIVE_STATE"; exit 3; fi
    if [ -f "${STUB_STATES:?}/$unit" ]; then cat "${STUB_STATES}/$unit"; else printf 'inactive\n'; fi
    ;;
  stop) [ "${STUB_STOP_FAIL:-}" = "$unit" ] && exit 0; printf 'inactive\n' >"${STUB_STATES}/$unit" ;;
  start) [ "${STUB_START_FAIL:-}" = "$unit" ] && exit 1; printf 'active\n' >"${STUB_STATES}/$unit" ;;
esac
exit 0
EOF

write_stub chcon <<'EOF'
#!/usr/bin/env bash
printf 'chcon %s\n' "$*" >>"${STUB_CALL_LOG:?}"
exit 0
EOF

# Drop the container owner/group so the sandbox can install as the test user.
write_stub install <<'EOF'
#!/usr/bin/env bash
args=()
skip=0
for a in "$@"; do
  if [ "$skip" = 1 ]; then skip=0; continue; fi
  case "$a" in
    -o | -g) skip=1 ;;
    *) args+=("$a") ;;
  esac
done
exec /usr/bin/install "${args[@]}"
EOF

# Emulate the pinned image commands the helper uses, for BOTH `podman run` (no
# live mount) and `podman exec` (the live container). Every run that would mount
# the gateway-state path records whether the gateway was ACTIVE at that moment,
# so the test can assert that Podman's implicit `:z` relabel is never applied to
# a live private mount.
write_stub podman <<'EOF'
#!/usr/bin/env bash
kind="${1:-}"
printf 'podman %s\n' "$*" >>"${STUB_CALL_LOG:?}"

# The container inventory is the authority for whether a private mount is live.
# `STUB_CONTAINER_STATE` models a container that diverges from its unit; without
# it the state follows the unit file, as a healthy system would.
container_state_name() {
  if [ -n "${STUB_CONTAINER_STATE:-}" ]; then printf '%s\n' "$STUB_CONTAINER_STATE"; return 0; fi
  if [ -f "${STUB_STATES:?}/hermes-gateway.service" ] \
     && [ "$(cat "${STUB_STATES}/hermes-gateway.service")" = active ]; then
    printf 'running\n'
  else
    printf 'stopped\n'
  fi
}

dispatch() { # <program> <args...>
  local prog="$1"; shift
  case "$prog" in
    */bin/hermes)
      if [ "${1:-}" = config ]; then
        local sub="${2:-}" key="${3:-}" value="${4:-}" state="${STUB_CONFIG_STATE:?}"
        case "$sub" in
          get)
            if line=$(grep -m1 "^${key}=" "$state" 2>/dev/null); then
              printf '%s\n' "${line#*=}"
            else
              printf 'not set\n'
              exit 1
            fi
            ;;
          set)
            if [ "${STUB_CONFIG_SET_FAIL:-0}" = 1 ]; then
              printf 'error: injected config set failure\n' >&2
              exit 1
            fi
            grep -v "^${key}=" "$state" >"$state.tmp" 2>/dev/null || true
            printf '%s=%s\n' "$key" "$value" >>"$state.tmp"
            mv "$state.tmp" "$state"
            ;;
        esac
      fi
      ;;
    *python3)
      if [ "${STUB_PROBE_FAIL:-0}" = 1 ]; then printf 'RESULT=FAIL\n'; exit 1; fi
      printf 'RESULT=PASS\n' ;;
  esac
  exit 0
}

case "$kind" in
  run)
    case "$*" in
      *gateway-state*)
        gw='unknown'
        [ -f "${STUB_STATES:?}/hermes-gateway.service" ] && gw=$(cat "${STUB_STATES}/hermes-gateway.service")
        printf 'podman-run-state-mount gateway_active=%s\n' \
          "$([ "$gw" = active ] && echo yes || echo no)" >>"${STUB_CALL_LOG}"
        ;;
    esac
    entry=""; after_image=0; cmd=(); prev=""
    for a in "$@"; do
      [ "$prev" = "--entrypoint" ] && entry="$a"
      if [ "$after_image" = 1 ]; then cmd+=("$a"); fi
      case "$a" in docker.io/*) after_image=1 ;; esac
      prev="$a"
    done
    dispatch "${entry:-/bin/true}" "${cmd[@]:-}"
    ;;
  ps)
    # `podman ps -a --format '{{.Names}}'`: a successful inventory that lists the
    # container is what lets the helper inspect it; failure is unknown.
    cstate=$(container_state_name)
    printf 'podman-container-inventory %s\n' "$cstate" >>"${STUB_CALL_LOG}"
    case "$cstate" in
      unknown) printf 'Error: unable to connect to Podman socket\n' >&2; exit 125 ;;
      running | exited) printf 'hermes-gateway\n' ;;
    esac
    ;;
  inspect)
    # `podman inspect --format '{{.State.Running}}' hermes-gateway`
    printf 'podman-container-inspect %s\n' "$(container_state_name)" >>"${STUB_CALL_LOG}"
    case "$(container_state_name)" in
      running) printf 'true\n' ;;
      exited | stopped) printf 'false\n' ;;
      *) printf 'Error: no such container\n' >&2; exit 125 ;;
    esac
    ;;
  exec)
    # Record the exact live invocation so identity and mount arguments are
    # observable, then skip the exec options to reach the container and command.
    shift
    printf 'podman-exec %s\n' "$*" >>"${STUB_CALL_LOG}"
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --user | --workdir | -u | -w | -e | --env) shift 2 ;;
        -*) shift ;;
        *) break ;;
      esac
    done
    [ "${1:-}" = hermes-gateway ] && shift
    dispatch "$@"
    ;;
esac
exit 0
EOF

seed_converged() {
  printf 'terminal.backend=ssh\nterminal.ssh_host=worker\nterminal.ssh_user=worker\n' >"$CONFIG_STATE"
  printf 'terminal.ssh_port=22\nterminal.ssh_key=/opt/hermes/gateway-ssh/worker_client_ed25519\n' >>"$CONFIG_STATE"
  install -m 0644 "$MANUAL/gateway/m03-probe.py" "$GWSSH/m03-probe.py"
  printf 'worker ssh-ed25519 AAAA review\n' >"$GWSSH/known_hosts"
  printf 'terminal:\n  backend: ssh\n' >"$GW_STATE/config.yaml"
  printf 'active\n' >"$STATES/hermes-gateway.service"
  : >"$CALL_LOG"
}

seed_converged_inactive() {
  seed_converged
  printf 'inactive\n' >"$STATES/hermes-gateway.service"
}

seed_drifted() {
  seed_converged
  printf 'terminal.backend=local\nterminal.ssh_host=worker\nterminal.ssh_user=worker\n' >"$CONFIG_STATE"
  printf 'terminal.ssh_port=22\nterminal.ssh_key=/opt/hermes/gateway-ssh/worker_client_ed25519\n' >>"$CONFIG_STATE"
}

# No `podman run` may mount the gateway-state path while the gateway is active:
# that is the implicit `:z` relabel the review requires this helper to avoid.
assert_no_live_state_mount() { # <name>
  local name="$1" bad
  bad=$(grep '^podman-run-state-mount gateway_active=yes' "$CALL_LOG" || true)
  if [ -z "$bad" ]; then
    _pass "$name"
  else
    _fail "$name" "$bad"
  fi
}

run_configure() { # [--inspect]
  local rc=0
  env -i PATH="$STUB:/usr/bin:/bin" HOME="$ADMIN_HOME" \
    TEST_ADMIN="$TEST_ADMIN" TEST_HOME="$ADMIN_HOME" HERMES_ADMIN="$TEST_ADMIN" \
    HERMES_RUNTIME_HOME="$RUNTIME_HOME" \
    MP_PROFILE_LOCK_PATH="$SANDBOX/lock" MP_HOST_IDENTITY_FILE=/nonexistent \
    HERMES_EXPECT_MACHINE_ID_SHA256="$MACHINE_HASH" \
    STUB_STATES="$STATES" STUB_CALL_LOG="$CALL_LOG" STUB_CONFIG_STATE="$CONFIG_STATE" \
    STUB_STOP_FAIL="${STUB_STOP_FAIL:-}" STUB_START_FAIL="${STUB_START_FAIL:-}" \
    STUB_ISACTIVE_RC="${STUB_ISACTIVE_RC:-}" STUB_ISACTIVE_STATE="${STUB_ISACTIVE_STATE:-}" \
    STUB_CONTAINER_STATE="${STUB_CONTAINER_STATE:-}" \
    STUB_CONFIG_SET_FAIL="${STUB_CONFIG_SET_FAIL:-0}" \
    STUB_PROBE_FAIL="${STUB_PROBE_FAIL:-0}" \
    TMPDIR="$SANDBOX/tmp" \
    bash "$CONFIGURE" "$@" 2>&1 || rc=$?
  return "$rc"
}

# --- converged --------------------------------------------------------------
section 'm03-configure converged profile'
seed_converged
converged_rc=0
converged_out=$(run_configure --apply) || converged_rc=$?
assert_equals '0' "$converged_rc" 'a converged profile passes without changes'
assert_contains 'already converged; no service stop and no relabel' "$converged_out" \
  'the helper reports the converged path'
assert_contains 'CHECK readback_terminal_backend=PASS' "$converged_out" 'the readback still verifies the backend'
if grep -q 'systemctl --user stop' "$CALL_LOG"; then
  _fail 'a converged profile does not stop the gateway' "$(grep 'systemctl --user stop' "$CALL_LOG")"
else
  _pass 'a converged profile does not stop the gateway'
fi
if grep -q '^chcon ' "$CALL_LOG"; then
  _fail 'a converged profile does not relabel the live private mount' "$(grep '^chcon ' "$CALL_LOG")"
else
  _pass 'a converged profile does not relabel the live private mount'
fi
if grep -q 'systemctl --user start' "$CALL_LOG"; then
  _fail 'a converged profile does not restart an active gateway' "$(grep 'systemctl --user start' "$CALL_LOG")"
else
  _pass 'a converged profile does not restart an active gateway'
fi
assert_no_live_state_mount 'a converged active gateway is never queried through a new state mount'
# C3: a live read must keep the container runtime identity. `podman exec` does
# not inherit the supervised process's dropped UID, so the explicit user and
# workdir are required for the probe to mean anything.
assert_contains 'podman exec --user 10000:10000 --workdir /opt/hermes hermes-gateway' "$(cat "$CALL_LOG")" \
  'the live read runs as UID/GID 10000 in the required working directory'

# --- converged while the unit is already inactive ---------------------------
section 'm03-configure converged with an inactive gateway'
seed_converged_inactive
inactive_rc=0
inactive_out=$(run_configure --apply) || inactive_rc=$?
assert_equals '0' "$inactive_rc" 'a converged profile passes even when the unit is inactive'
assert_contains 'already converged; no service stop and no relabel' "$inactive_out" \
  'the inactive converged path is reported'
if grep -qE 'systemctl --user (stop|start)' "$CALL_LOG"; then
  _fail 'a converged inactive profile makes no lifecycle change' "$(grep -E 'systemctl --user (stop|start)' "$CALL_LOG")"
else
  _pass 'a converged inactive profile makes no lifecycle change'
fi
assert_no_live_state_mount 'an inactive converged run never mounts a live state path'
assert_equals 'inactive' "$(cat "$STATES/hermes-gateway.service")" \
  'the converged inactive run leaves the unit inactive'

# --- failed stop must not mutate a live mount (R3/R10) ----------------------
section 'm03-configure failed stop'
seed_drifted
STUB_STOP_FAIL='hermes-gateway.service'
stopfail_rc=0
stopfail_out=$(run_configure --apply) || stopfail_rc=$?
unset STUB_STOP_FAIL
assert_contains 'CHECK gateway_stopped=FAIL' "$stopfail_out" 'a failed stop is recorded as a failed check'
assert_contains 'CHECK gateway_configured=FAIL' "$stopfail_out" 'the run refuses to write while the mount is live'
assert_equals '1' "$stopfail_rc" 'a failed stop fails the run'
assert_no_live_state_mount 'a failed stop never creates a new mount against the live state'

# --- failed config application ---------------------------------------------
section 'm03-configure failed application'
seed_drifted
STUB_CONFIG_SET_FAIL=1
setfail_rc=0
setfail_out=$(run_configure --apply) || setfail_rc=$?
unset STUB_CONFIG_SET_FAIL
assert_contains 'CHECK gateway_configured=FAIL' "$setfail_out" 'a failed config set is recorded as a failed check'
assert_equals '1' "$setfail_rc" 'a failed config application fails the run'

# --- F2: a failed application must not activate an inactive gateway ---------
# `apply_ok` only means the STOP succeeded. The reviewed startup block treated it
# as configuration success, so an inactive gateway with drifted config and a
# failed `config set` was started with known-bad terminal configuration and no
# restoration obligation to undo it.
section 'm03-configure failed application leaves an inactive gateway inactive'
seed_drifted
printf 'inactive\n' >"$STATES/hermes-gateway.service"
STUB_CONFIG_SET_FAIL=1
f2_rc=0
f2_out=$(run_configure --apply) || f2_rc=$?
unset STUB_CONFIG_SET_FAIL
assert_contains 'CHECK gateway_configured=FAIL' "$f2_out" \
  'F2: a failed config set is recorded as a failed check'
assert_contains 'CHECK readback_terminal_backend=FAIL' "$f2_out" \
  'F2: the readback failure is recorded when the write failed'
assert_equals '1' "$f2_rc" 'F2: a failed config application fails the run'
if grep -q 'systemctl --user start' "$CALL_LOG"; then
  _fail 'F2: a failed configuration never activates the gateway' "$(grep 'systemctl --user start' "$CALL_LOG")"
else
  _pass 'F2: a failed configuration never activates the gateway'
fi
assert_equals 'inactive' "$(cat "$STATES/hermes-gateway.service")" \
  'F2: the previously inactive gateway is left inactive after a failed apply'

# --- F2: a failed backend probe must not activate the gateway ---------------
section 'm03-configure failed probe leaves the gateway inactive'
seed_drifted
printf 'inactive\n' >"$STATES/hermes-gateway.service"
STUB_PROBE_FAIL=1
f2p_rc=0
f2p_out=$(run_configure --apply) || f2p_rc=$?
unset STUB_PROBE_FAIL
assert_contains 'CHECK gateway_configured=PASS' "$f2p_out" \
  'F2: configuration succeeded before the probe failure'
assert_contains 'CHECK terminal_backend_probe=FAIL' "$f2p_out" \
  'F2: a failed backend probe is recorded'
assert_equals '1' "$f2p_rc" 'F2: a failed backend probe fails the run'
if grep -q 'systemctl --user start' "$CALL_LOG"; then
  _fail 'F2: a failed backend probe never activates the gateway' "$(grep 'systemctl --user start' "$CALL_LOG")"
else
  _pass 'F2: a failed backend probe never activates the gateway'
fi
assert_equals 'inactive' "$(cat "$STATES/hermes-gateway.service")" \
  'F2: the gateway stays inactive after a failed backend probe'

# --- F2: an initially active gateway keeps its restoration obligation --------
# The new activation gate must not remove the existing restoration guarantee: a
# gateway that was active before the run is brought back by the cleanup hook even
# when the configuration failed, because the operator's prior state is owed back.
section 'm03-configure failed application restores an initially active gateway'
seed_drifted
STUB_CONFIG_SET_FAIL=1
f2r_rc=0
f2r_out=$(run_configure --apply) || f2r_rc=$?
unset STUB_CONFIG_SET_FAIL
assert_contains 'CHECK gateway_configured=FAIL' "$f2r_out" 'F2: the failed apply is recorded'
assert_equals '1' "$f2r_rc" 'F2: the failed apply fails the run'
if grep -q 'systemctl --user start' "$CALL_LOG"; then
  _pass 'F2: an initially active gateway is restored despite the failed apply'
else
  _fail 'F2: an initially active gateway is restored despite the failed apply'
fi
assert_equals 'active' "$(cat "$STATES/hermes-gateway.service")" \
  'F2: the initially active gateway is active again after the failed apply'

# --- failed restoration of a stopped active gateway ------------------------
section 'm03-configure failed restoration'
seed_drifted
STUB_START_FAIL='hermes-gateway.service'
restore_rc=0
restore_out=$(run_configure --apply) || restore_rc=$?
unset STUB_START_FAIL
restore_log=$(cat "$ADMIN_HOME/hermes-m03-configure.out" 2>/dev/null || true)
assert_contains 'CHECK restore_gateway_state=FAIL' "$restore_log" \
  'a failed restoration is recorded as a required failed check'
assert_contains 'RESTORE_FAILED' "$restore_out" 'a failed restoration is reported to the operator'
assert_equals '1' "$restore_rc" 'a failed restoration fails an otherwise-successful run'

# --- configuration drift ----------------------------------------------------
section 'm03-configure configuration drift'
seed_drifted
drift_rc=0
drift_out=$(run_configure --apply) || drift_rc=$?
assert_equals '0' "$drift_rc" 'a drifted backend is applied successfully'
assert_contains 'CHECK readback_terminal_backend=PASS' "$drift_out" 'the drifted backend is corrected and read back'
assert_contains 'terminal.backend=ssh' "$(cat "$CONFIG_STATE")" 'the corrected value is written'
assert_contains 'systemctl --user stop' "$(cat "$CALL_LOG")" 'drift stops the gateway before writing'
assert_contains 'systemctl --user start' "$(cat "$CALL_LOG")" \
  'a successfully configured drifted gateway is activated again'
assert_equals 'active' "$(cat "$STATES/hermes-gateway.service")" \
  'a successful configure and probe leaves the gateway active'
if grep -q '^chcon ' "$CALL_LOG"; then
  _fail 'an unchanged probe is not relabelled when only config drifts' "$(grep '^chcon ' "$CALL_LOG")"
else
  _pass 'an unchanged probe is not relabelled when only config drifts'
fi

# --- changed probe must be installed after the mount is no longer live ------
section 'm03-configure probe change ordering'
seed_converged
printf 'stale probe\n' >"$GWSSH/m03-probe.py"
: >"$CALL_LOG"
probe_rc=0
probe_out=$(run_configure --apply) || probe_rc=$?
assert_equals '0' "$probe_rc" 'a changed probe is installed successfully'
if grep -q '^chcon ' "$CALL_LOG"; then
  _pass 'a changed probe is relabelled'
else
  _fail 'a changed probe is relabelled'
fi
stop_line=$(grep -n 'systemctl --user stop' "$CALL_LOG" | head -n1 | cut -d: -f1 || true)
chcon_line=$(grep -n '^chcon ' "$CALL_LOG" | head -n1 | cut -d: -f1 || true)
if [[ -n "$stop_line" && -n "$chcon_line" && "$stop_line" -lt "$chcon_line" ]]; then
  _pass 'the gateway is stopped before the live private mount is relabelled'
else
  _fail 'the gateway is stopped before the live private mount is relabelled' "stop=$stop_line chcon=$chcon_line"
fi

# --- C4: a failed unit query must not select the one-shot relabel path -------
section 'm03-configure unknown unit state with a live container'
seed_converged
STUB_ISACTIVE_RC=1
STUB_CONTAINER_STATE=running
c4a_rc=0
c4a_out=$(run_configure --apply) || c4a_rc=$?
unset STUB_ISACTIVE_RC STUB_CONTAINER_STATE
assert_equals '0' "$c4a_rc" 'C4: a converged run with unreadable unit state still passes through the live container'
assert_no_live_state_mount 'C4: a failed unit query never selects the one-shot state mount'
if grep -q 'systemctl --user stop' "$CALL_LOG"; then
  _fail 'C4: a failed unit query causes no service stop' "$(grep 'systemctl --user stop' "$CALL_LOG")"
else
  _pass 'C4: a failed unit query causes no service stop'
fi
assert_contains 'podman exec --user 10000:10000 --workdir /opt/hermes hermes-gateway' "$(cat "$CALL_LOG")" \
  'C4: a live container is read with exec even when its unit state is unreadable'

# --- C4: a running container behind a non-active unit blocks mutation --------
section 'm03-configure running container behind an inactive unit'
seed_drifted
printf 'inactive\n' >"$STATES/hermes-gateway.service"
STUB_CONTAINER_STATE=running
c4b_rc=0
c4b_out=$(run_configure --apply) || c4b_rc=$?
unset STUB_CONTAINER_STATE
assert_contains 'CHECK gateway_stopped=FAIL' "$c4b_out" 'C4: the stop gate requires proven container quiescence'
assert_contains 'CHECK gateway_configured=FAIL' "$c4b_out" 'C4: config is not written while a live container holds the mount'
assert_equals '1' "$c4b_rc" 'C4: a live container behind a non-active unit fails the run'
assert_no_live_state_mount 'C4: a live container is read with exec even when its unit is not active'
if grep -q '^chcon ' "$CALL_LOG"; then
  _fail 'C4: no relabel happens while the container is live' "$(grep '^chcon ' "$CALL_LOG")"
else
  _pass 'C4: no relabel happens while the container is live'
fi

# --- C4: an undeterminable prior state refuses the lifecycle mutation --------
section 'm03-configure undeterminable prior state'
seed_drifted
STUB_ISACTIVE_STATE='deactivating'
STUB_CONTAINER_STATE=stopped
c4c_rc=0
c4c_out=$(run_configure --apply) || c4c_rc=$?
unset STUB_ISACTIVE_STATE STUB_CONTAINER_STATE
assert_contains 'CHECK gateway_stopped=FAIL' "$c4c_out" 'C4: an undeterminable prior state refuses the stop'
assert_equals '1' "$c4c_rc" 'C4: an undeterminable prior state fails the run instead of stranding the unit'
if grep -q 'systemctl --user stop' "$CALL_LOG"; then
  _fail 'C4: nothing is stopped when its prior state is undetermined' "$(grep 'systemctl --user stop' "$CALL_LOG")"
else
  _pass 'C4: nothing is stopped when its prior state is undetermined'
fi

# --- C4: a failed container inventory refuses to mount anything -------------
section 'm03-configure unknown container state'
seed_drifted
STUB_CONTAINER_STATE=unknown
c4d_rc=0
c4d_out=$(run_configure --apply) || c4d_rc=$?
unset STUB_CONTAINER_STATE
assert_contains 'CHECK gateway_container_state=FAIL' "$c4d_out" \
  'C4: an undeterminable container state is a failed check'
assert_equals '1' "$c4d_rc" 'C4: an undeterminable container state fails the run'
if grep -qE '^podman (run|exec) ' "$CALL_LOG"; then
  _fail 'C4: no container command runs when the state is unknown' "$(grep -E '^podman (run|exec) ' "$CALL_LOG")"
else
  _pass 'C4: no container command runs when the state is unknown'
fi

# --- inspection must touch nothing -----------------------------------------
section 'm03-configure inspection'
seed_converged
inspect_rc=0
inspect_out=$(run_configure) || inspect_rc=$?
assert_equals '0' "$inspect_rc" 'inspection exits successfully'
assert_contains 'INSPECT ONLY' "$inspect_out" 'inspection states that nothing was changed'
if [ -s "$CALL_LOG" ]; then
  _fail 'inspection touches no runtime command' "$(cat "$CALL_LOG")"
else
  _pass 'inspection touches no runtime command'
fi

print_summary
