#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC1091,SC2034
# Behavioral tests for m03-contract.sh state-directory ownership (review R1).
#
# The REAL helper is executed with synthetic state and stubbed runtime commands.
# The pinned gateway container selects UID/GID 10000, while host `hermes` maps to
# namespace UID 0, so the helper must hand the profile state directory to the
# container's own UID inside the rootless user namespace instead of resetting it
# to host `hermes`. The tests observe the real shell ownership path (the command
# the helper issues), not merely file ownership created by Python. C5: a live
# gateway is driven through `podman exec`, so contract application and
# verification never mount or relabel its private SSH tree; an undeterminable
# container state refuses.
#
#   ./tests/test-hermes-manual-contract.sh [-v]

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

readonly CONTRACT="$REPO_ROOT/scripts/hermes/manual/m03-contract.sh"

VERBOSE=false
[[ "${1:-}" == -v ]] && VERBOSE=true

WORK=$(mktemp -d)
readonly WORK
trap 'rm -rf -- "$WORK"' EXIT

MACHINE_HASH=$(sha256sum /etc/machine-id | cut -d' ' -f1)
readonly MACHINE_HASH
readonly TEST_ADMIN='contract-fixture-admin'

SANDBOX="$WORK/sandbox"
STUB="$SANDBOX/stub"
CALL_LOG="$SANDBOX/calls.log"
ADMIN_HOME="$SANDBOX/admin-home"
RUNTIME_HOME="$SANDBOX/home/hermes"
GW_STATE="$RUNTIME_HOME/gateway-state"
GWSSH="$RUNTIME_HOME/gateway-ssh"
mkdir -p "$STUB" "$ADMIN_HOME" "$RUNTIME_HOME/transport" "$GWSSH" "$SANDBOX/tmp"

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

write_stub chown <<'EOF'
#!/usr/bin/env bash
exit 0
EOF

write_stub ausearch <<'EOF'
#!/usr/bin/env bash
printf '<no matches>\n'
exit 1
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

# The podman seam. `unshare stat` reports the namespace UID of the current owner
# (this is how the helper decides whether the mapping is already valid), and
# `unshare chown` is the ownership path the helper must use for fresh state. The
# `ps`/`inspect` pair models the container inventory that decides whether the
# private SSH tree may be mounted at all (C5).
write_stub podman <<'EOF'
#!/usr/bin/env bash
printf 'podman %s\n' "$*" >>"${STUB_CALL_LOG:?}"

container_state_name() {
  if [ -n "${STUB_CONTAINER_STATE:-}" ]; then printf '%s\n' "$STUB_CONTAINER_STATE"; return 0; fi
  printf 'stopped\n'
}

image_dispatch() { # emulate the pinned image commands
  case "$*" in
    *harden-config.py*)
      case "$*" in *--check*) printf 'PROFILE_CONTRACT_CHECK=PASS\n' ;; *) printf 'PROFILE_CONTRACT_APPLIED\n' ;; esac
      ;;
    *verify-contract.py*) printf 'CONTRACT_VERIFY=PASS\n' ;;
    *python3*) printf 'hooks={} mcp_servers={}\n' ;;
  esac
  exit 0
}

case "${1:-}" in
  unshare)
    shift
    case "${1:-}" in
      stat)
        printf '%s\n' "${STUB_NS_UID:-0}"
        exit 0
        ;;
      chown)
        printf 'PODMAN_CHOWN_NS %s\n' "$*" >>"${STUB_CALL_LOG}"
        [ "${STUB_CHOWN_FAIL:-0}" = 1 ] && exit 1
        exit 0
        ;;
    esac
    ;;
  ps)
    printf 'podman-container-inventory %s\n' "$(container_state_name)" >>"${STUB_CALL_LOG}"
    case "$(container_state_name)" in
      unknown) printf 'Error: unable to connect to Podman socket\n' >&2; exit 125 ;;
      running | exited) printf 'hermes-gateway\n' ;;
    esac
    ;;
  inspect)
    printf 'podman-container-inspect %s\n' "$(container_state_name)" >>"${STUB_CALL_LOG}"
    case "$(container_state_name)" in
      running) printf 'true\n' ;;
      exited | stopped) printf 'false\n' ;;
      *) printf 'Error: no such container\n' >&2; exit 125 ;;
    esac
    ;;
  exec)
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
    image_dispatch "$@"
    ;;
  run)
    entry=""; after_image=0; cmd=(); prev=""
    for a in "$@"; do
      [ "$prev" = "--entrypoint" ] && entry="$a"
      if [ "$after_image" = 1 ]; then cmd+=("$a"); fi
      case "$a" in docker.io/*) after_image=1 ;; esac
      prev="$a"
    done
    image_dispatch "${entry:-/bin/true}" "${cmd[@]:-}"
    ;;
esac
exit 0
EOF

write_stub chcon <<'EOF'
#!/usr/bin/env bash
printf 'chcon %s\n' "$*" >>"${STUB_CALL_LOG:?}"
exit 0
EOF

reset_calls() { : >"$CALL_LOG"; }

seed_state_dir() { # <mode>
  rm -rf "$GW_STATE"
  install -d -m "$1" "$GW_STATE"
}

run_contract() {
  local rc=0
  env -i PATH="$STUB:/usr/bin:/bin" HOME="$ADMIN_HOME" \
    TEST_ADMIN="$TEST_ADMIN" TEST_HOME="$ADMIN_HOME" HERMES_ADMIN="$TEST_ADMIN" \
    HERMES_RUNTIME_HOME="$RUNTIME_HOME" \
    MP_PROFILE_LOCK_PATH="$SANDBOX/lock" MP_HOST_IDENTITY_FILE=/nonexistent \
    HERMES_EXPECT_MACHINE_ID_SHA256="$MACHINE_HASH" \
    STUB_CALL_LOG="$CALL_LOG" STUB_NS_UID="${STUB_NS_UID:-0}" STUB_CHOWN_FAIL="${STUB_CHOWN_FAIL:-0}" \
    STUB_CONTAINER_STATE="${STUB_CONTAINER_STATE:-}" \
    TMPDIR="$SANDBOX/tmp" \
    bash "$CONTRACT" --apply 2>&1 || rc=$?
  return "$rc"
}

# --- fresh state must be handed to the container UID ------------------------
section 'm03-contract fresh state ownership'
reset_calls
rm -rf "$GW_STATE"
fresh_rc=0
fresh_out=$(run_contract) || fresh_rc=$?
assert_equals '0' "$fresh_rc" 'a fresh state directory converges and passes'
assert_contains 'CHECK contract_verified=PASS' "$fresh_out" 'the contract is applied and verified'
if [ -d "$GW_STATE" ]; then
  _pass 'the helper creates the profile state directory'
else
  _fail 'the helper creates the profile state directory'
fi
assert_equals '700' "$(stat -c %a "$GW_STATE" 2>/dev/null || echo missing)" \
  'fresh state keeps mode 0700 (nothing is broadened)'
if grep -q 'PODMAN_CHOWN_NS' "$CALL_LOG"; then
  _pass 'fresh state is handed to the container UID through the user namespace'
else
  _fail 'fresh state is handed to the container UID through the user namespace' "$(cat "$CALL_LOG")"
fi
if grep -q 'PODMAN_CHOWN_NS chown 10000:10000' "$CALL_LOG"; then
  _pass 'the mapped ownership uses container UID/GID 10000, not host hermes'
else
  _fail 'the mapped ownership uses container UID/GID 10000, not host hermes' "$(grep PODMAN_CHOWN_NS "$CALL_LOG" || true)"
fi

# --- already-mapped ownership must be preserved ----------------------------
section 'm03-contract preserved mapped ownership'
seed_state_dir 0700
reset_calls
STUB_NS_UID=10000
mapped_rc=0
mapped_out=$(run_contract) || mapped_rc=$?
unset STUB_NS_UID
assert_equals '0' "$mapped_rc" 'an already-mapped state directory passes'
if grep -q 'PODMAN_CHOWN_NS' "$CALL_LOG"; then
  _fail 'valid mapped ownership is preserved without a needless chown' "$(grep PODMAN_CHOWN_NS "$CALL_LOG")"
else
  _pass 'valid mapped ownership is preserved without a needless chown'
fi

# --- legacy host ownership must be corrected --------------------------------
section 'm03-contract legacy ownership repair'
seed_state_dir 0700
reset_calls
STUB_NS_UID=0
legacy_rc=0
legacy_out=$(run_contract) || legacy_rc=$?
unset STUB_NS_UID
assert_equals '0' "$legacy_rc" 'legacy host ownership is repaired'
if grep -q 'PODMAN_CHOWN_NS chown 10000:10000' "$CALL_LOG"; then
  _pass 'legacy host-hermes ownership is remapped to container UID 10000'
else
  _fail 'legacy host-hermes ownership is remapped to container UID 10000' "$(cat "$CALL_LOG")"
fi

# --- a broad mode is narrowed, not broadened --------------------------------
section 'm03-contract mode reconciliation'
seed_state_dir 0755
reset_calls
STUB_NS_UID=10000
mode_rc=0
mode_out=$(run_contract) || mode_rc=$?
unset STUB_NS_UID
assert_equals '0' "$mode_rc" 'a broadened state mode is corrected'
assert_equals '700' "$(stat -c %a "$GW_STATE")" 'a broadened state mode is narrowed to 0700'
if grep -q 'PODMAN_CHOWN_NS' "$CALL_LOG"; then
  _fail 'a valid mapping does not force a chown while fixing the mode' "$(grep PODMAN_CHOWN_NS "$CALL_LOG")"
else
  _pass 'a valid mapping does not force a chown while fixing the mode'
fi

# --- an ownership failure must not report success ---------------------------
section 'm03-contract ownership failure propagation'
seed_state_dir 0700
reset_calls
STUB_NS_UID=0
STUB_CHOWN_FAIL=1
fail_rc=0
fail_out=$(run_contract) || fail_rc=$?
unset STUB_NS_UID STUB_CHOWN_FAIL
if [ "$fail_rc" -ne 0 ]; then
  _pass 'a failed ownership mapping exits nonzero'
else
  _fail 'a failed ownership mapping exits nonzero'
fi
assert_contains 'cannot hand' "$fail_out" 'the ownership failure is reported'

# --- C5: a live gateway is used through exec, never a private :Z relabel -----
section 'm03-contract live gateway private-mount safety'
seed_state_dir 0700
# Remove the helpers a previous section installed so this run genuinely writes
# them into the live mount and must give the new files their sibling label.
rm -f "$GWSSH/manual-harden-config.py" "$GWSSH/manual-verify-contract.py" "$GWSSH/profile-contract.yaml"
reset_calls
STUB_NS_UID=10000
STUB_CONTAINER_STATE=running
live_rc=0
live_out=$(run_contract) || live_rc=$?
unset STUB_CONTAINER_STATE
assert_equals '0' "$live_rc" 'C5: contract apply passes against a live gateway'
assert_contains 'CHECK contract_verified=PASS' "$live_out" 'C5: the contract is verified against the live container'
assert_no_grep 'podman run .*gateway-ssh:/opt/hermes/gateway-ssh:ro,Z' "$CALL_LOG" \
  'C5: no one-shot run mounts the live private SSH tree'
assert_no_grep 'systemctl --user stop' "$CALL_LOG" 'C5: a healthy live gateway is not stopped'
assert_contains 'podman exec --user 10000:10000 --workdir /opt/hermes hermes-gateway' "$(cat "$CALL_LOG")" \
  'C5/C3: the live helper and verifier run as the container runtime identity'
if grep -q '^chcon ' "$CALL_LOG"; then
  _pass 'C5: a file written into the live mount is given its sibling label'
else
  _fail 'C5: a file written into the live mount is given its sibling label'
fi

# Contract after an active configure, run again: every rerun must stay
# convergent and equally free of private mounts.
for run_no in 2 3; do
  reset_calls
  STUB_NS_UID=10000
  STUB_CONTAINER_STATE=running
  repeat_rc=0
  repeat_out=$(run_contract) || repeat_rc=$?
  unset STUB_CONTAINER_STATE
  assert_equals '0' "$repeat_rc" "C5: live contract run $run_no still passes"
  assert_no_grep 'podman run .*gateway-ssh:/opt/hermes/gateway-ssh:ro,Z' "$CALL_LOG" \
    "C5: live contract run $run_no mounts no private SSH tree"
  assert_no_grep '^chcon ' "$CALL_LOG" "C5: live contract run $run_no relabels nothing (converged)"
done

# --- C5: an undeterminable container state refuses before any mount ----------
section 'm03-contract unknown container state'
seed_state_dir 0700
reset_calls
STUB_NS_UID=10000
STUB_CONTAINER_STATE=unknown
unknown_rc=0
unknown_out=$(run_contract) || unknown_rc=$?
unset STUB_CONTAINER_STATE
if [ "$unknown_rc" -ne 0 ]; then
  _pass 'C5: an undeterminable container state fails the run'
else
  _fail 'C5: an undeterminable container state fails the run'
fi
assert_contains 'CHECK gateway_container_state=FAIL' "$unknown_out" \
  'C5: the container-state refusal is recorded'
assert_no_grep 'podman run ' "$CALL_LOG" 'C5: no one-shot container runs when the state is unknown'

print_summary
