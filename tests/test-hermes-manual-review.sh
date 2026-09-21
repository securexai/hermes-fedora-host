#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC1091,SC2034
# Focused behavioral regression tests for the Gate 2 review findings.
#
# These tests run real subprocesses with synthetic state and stubbed external
# commands. They never require root, never start a container, never contact a
# target and never read a credential store.
#
#   ./tests/test-hermes-manual-review.sh [-v]
#
# Covered here:
#   F1  the privileged rebuild wrapper executes no checkout-controlled code
#   F4  cleanup registration, trap hooks and cleanup-failure reporting
#   F5  different helpers contend on one profile lock
#   F6  egress-probe classification (missing tool is not isolation)
#   F7  centralized ausearch interpretation
#   F9  required / informational / deferred check kinds
#   F10 convergence-primitive behaviour
#   C1  required cleanup runs before the result, so post-success cleanup failure
#       is published as FAIL rather than PASS
#   F1  a cleanup failure is authoritative in memory: it fails the run even when
#       the evidence-log append itself fails
#   C2/C4 conclusive service-state and container-state interpretation, and the
#       callers that refuse lifecycle mutation on an undeterminable state
# F2/F8/F10 configuration and verification behavior is exercised in
# tests/test-hermes-manual-backup.sh and tests/test_hermes_manual_hardening.py.

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
readonly LIB="$MANUAL/lib-manual-common.sh"
readonly REBUILD_WRAPPER="$MANUAL/lab/gate2-rebuild-kickstart-iso.sh"

VERBOSE=false
[[ "${1:-}" == -v ]] && VERBOSE=true

WORK=$(mktemp -d)
readonly WORK
trap 'rm -rf -- "$WORK"' EXIT
export LIB

MACHINE_HASH=$(sha256sum /etc/machine-id | cut -d' ' -f1)
readonly MACHINE_HASH

lib_snippet() {
  local code="$1"
  shift
  bash -c "source \"\$LIB\"; $code" _ "$@"
}

# --------------------------------------------------------------- F4 cleanup
section 'F4 cleanup registration and trap hooks'

registered=$(lib_snippet 'mp_secure_tmpdir >/dev/null; printf "%s %s" "${#MP_CLEANUP_DIRS[@]}" "$MP_SECURE_TMPDIR"')
registered_count=${registered%% *}
registered_dir=${registered#* }
if [[ "$registered_count" == '1' && -d "$registered_dir" && "$(stat -c %a "$registered_dir")" == '700' ]]; then
  _pass 'mp_secure_tmpdir registers the directory in the calling shell'
else
  _fail 'mp_secure_tmpdir registers the directory in the calling shell' "got '$registered'"
fi
rm -rf -- "$registered_dir"

cleaned=$(lib_snippet 'mp_secure_tmpdir >/dev/null; d=$MP_SECURE_TMPDIR; mp_cleanup_tmpdirs; [ ! -e "$d" ] && printf CLEANED')
assert_equals 'CLEANED' "$cleaned" 'mp_cleanup_tmpdirs removes registered state'

var_ok=$(lib_snippet 'mp_secure_tmpdir_var keydir; [ -d "$keydir" ] && [ "${#MP_CLEANUP_DIRS[@]}" -eq 1 ] && printf VAR_OK; rm -rf -- "$keydir"')
assert_equals 'VAR_OK' "$var_ok" 'mp_secure_tmpdir_var assigns and registers in the caller'

# The command-substitution pitfall is why the API above exists: it must NOT
# register, or a future caller could reintroduce the leak silently.
subshell_count=$(lib_snippet 'x=$(mp_secure_tmpdir); printf "%s" "${#MP_CLEANUP_DIRS[@]}"; rm -rf -- "$x"')
assert_equals '0' "$subshell_count" 'command substitution does not register cleanup (documented pitfall)'

marker="$WORK/hook-exit.marker"
: >"$marker"
lib_snippet 'marker="$1"; hook(){ printf "ran\n" >>"$marker"; }; mp_on_cleanup hook; mp_install_trap; exit 0' "$marker" >/dev/null 2>&1 || true
assert_equals 'ran' "$(cat "$marker")" 'a registered cleanup hook runs on normal exit'

# INT and TERM: a small child script registers the hook, creates private state
# and waits; a short-lived child sends the signal so the trap is delivered
# promptly. `$$` inside `bash -c` from this harness does not reliably name the
# child, hence the script file.
cat >"$WORK/trap-child.sh" <<'EOF'
#!/usr/bin/env bash
source "$LIB"
marker="$1"
dirmarker="$2"
sig="$3"
hook(){ printf 'ran\n' >>"$marker"; }
mp_on_cleanup hook
mp_install_trap
mp_secure_tmpdir >/dev/null
printf '%s' "$MP_SECURE_TMPDIR" >"$dirmarker"
( sleep 0.5; kill -"$sig" $$ ) &
sleep 30 & wait
EOF
chmod 0755 "$WORK/trap-child.sh"
for signal in INT TERM; do
  marker="$WORK/hook-$signal.marker"
  dir_marker="$WORK/hook-$signal.dir"
  : >"$marker"
  child_rc=0
  timeout 15 "$WORK/trap-child.sh" "$marker" "$dir_marker" "$signal" >/dev/null 2>&1 || child_rc=$?
  if [[ "$(cat "$marker")" == 'ran' ]]; then
    _pass "$signal runs the registered cleanup hook"
  else
    _fail "$signal runs the registered cleanup hook"
  fi
  leaked=$(cat "$dir_marker" 2>/dev/null || true)
  if [[ -n "$leaked" && ! -e "$leaked" ]]; then
    _pass "$signal removes the registered private directory"
  else
    _fail "$signal removes the registered private directory" "leaked '$leaked'"
  fi
  expected_rc=130
  [[ "$signal" == TERM ]] && expected_rc=143
  assert_equals "$expected_rc" "$child_rc" "$signal returns the conventional 128+signal status"
done

cleanup_rc=0
cleanup_err=$(bash -c 'source "$LIB"; bad(){ return 1; }; mp_on_cleanup bad; mp_install_trap; exit 7' 2>&1) || cleanup_rc=$?
assert_equals '7' "$cleanup_rc" 'a cleanup-hook failure preserves the primary exit status'
assert_contains 'CLEANUP_FAILED' "$cleanup_err" 'a cleanup-hook failure is reported, not suppressed'

# R3: mp_run_cleanup itself must not report success when a hook failed, so an
# inspecting caller can tell a completed cleanup from a failed one.
cleanup_return=$(lib_snippet 'bad(){ return 1; }; mp_on_cleanup bad; mp_run_cleanup; printf "rc=%s\n" "$?"' 2>/dev/null || true)
assert_contains 'rc=1' "$cleanup_return" 'mp_run_cleanup returns non-zero when a cleanup hook fails'
cleanup_ok=$(lib_snippet 'good(){ return 0; }; mp_on_cleanup good; mp_run_cleanup; printf "rc=%s\n" "$?"' 2>/dev/null || true)
assert_contains 'rc=0' "$cleanup_ok" 'mp_run_cleanup returns zero when cleanup succeeds'

# C1: the FINALIZER path, not just mp_run_cleanup's return value. Successful
# primary work followed by a failed required cleanup must never be published as
# PASS, because the result line is read by an operator as the run's verdict.
c1_log="$WORK/c1-finalize.log"
c1_rc=0
c1_out=$(lib_snippet 'bad(){ return 1; }; mp_on_cleanup bad; mp_install_trap; mp_check primary PASS >"$1"; mp_finalize "$1" 0' \
  "$c1_log" 2>&1) || c1_rc=$?
if [ "$c1_rc" -ne 0 ]; then
  _pass 'C1: a failed required cleanup after successful work exits nonzero'
else
  _fail 'C1: a failed required cleanup after successful work exits nonzero' "rc=$c1_rc out=$c1_out"
fi
if [[ "$c1_out" == *'RESULT=PASS'* ]]; then
  _fail 'C1: failed cleanup is never published as RESULT=PASS' "$c1_out"
else
  _pass 'C1: failed cleanup is never published as RESULT=PASS'
fi
assert_contains 'CHECK cleanup_required=FAIL' "$(cat "$c1_log" 2>/dev/null || true)" \
  'C1: the cleanup failure is recorded in the run log before the result'
assert_contains 'CLEANUP_FAILED' "$c1_out" 'C1: the cleanup failure is reported to the operator'

# A primary failure that already exists must survive a cleanup failure: the
# finalizer reports the primary status first and never turns it into a PASS.
c1p_log="$WORK/c1-primary.log"
c1p_rc=0
c1p_out=$(lib_snippet 'bad(){ return 1; }; mp_on_cleanup bad; mp_install_trap; mp_check primary PASS >"$1"; mp_finalize "$1" 7' \
  "$c1p_log" 2>&1) || c1p_rc=$?
if [ "$c1p_rc" -ne 0 ]; then
  _pass 'C1: an existing primary failure is preserved'
else
  _fail 'C1: an existing primary failure is preserved' "rc=$c1p_rc out=$c1p_out"
fi
assert_contains 'rc=7' "$c1p_out" 'C1: the primary pipeline status is what the finalizer reports'

# The tempdir-removal path is required cleanup too, not only named hooks: a
# registered private directory that cannot be removed must fail the run. The
# read-only parent makes the failure deterministic for an unprivileged test
# run (the suite already assumes non-root for its install-failure case).
c1t_parent="$WORK/c1-readonly-parent"
mkdir -p "$c1t_parent/child"
printf 'credential copy\n' >"$c1t_parent/child/secret"
chmod 0500 "$c1t_parent"
c1t_log="$WORK/c1-tmpdir.log"
c1t_rc=0
c1t_out=$(lib_snippet 'MP_CLEANUP_DIRS+=("$1/child"); mp_install_trap; mp_check primary PASS >"$2"; mp_finalize "$2" 0' \
  "$c1t_parent" "$c1t_log" 2>&1) || c1t_rc=$?
chmod 0700 "$c1t_parent"
if [ "$c1t_rc" -ne 0 ]; then
  _pass 'C1: an unremovable private directory fails the finalized run'
else
  _fail 'C1: an unremovable private directory fails the finalized run' "rc=$c1t_rc out=$c1t_out"
fi
if [[ "$c1t_out" == *'RESULT=PASS'* ]]; then
  _fail 'C1: a leaked private directory is not published as PASS' "$c1t_out"
else
  _pass 'C1: a leaked private directory is not published as PASS'
fi
assert_contains 'CHECK cleanup_required=FAIL' "$(cat "$c1t_log" 2>/dev/null || true)" \
  'C1: temporary-state removal failure is a required failed check'
rm -rf -- "$c1t_parent"

# Control: successful cleanup keeps a normal PASS and a zero status.
c1o_log="$WORK/c1-clean.log"
c1o_rc=0
c1o_out=$(lib_snippet 'good(){ return 0; }; mp_on_cleanup good; mp_install_trap; mp_check primary PASS >"$1"; mp_finalize "$1" 0' \
  "$c1o_log" 2>&1) || c1o_rc=$?
assert_equals '0' "$c1o_rc" 'C1: a clean run still exits zero'
assert_contains 'RESULT=PASS' "$c1o_out" 'C1: a clean run still publishes PASS'

# F1: the in-memory cleanup result must be authoritative even when the evidence
# append itself fails (an I/O error or a full filesystem). The reviewed finalizer
# recorded the failure ONLY by appending `CHECK cleanup_required=FAIL`, so a failed
# append could still publish PASS. A file-permission fixture is deliberately NOT
# used here: root bypasses mode bits and the test would silently pass. Instead the
# append is made to fail deterministically for any UID by shadowing `printf` for
# the cleanup CHECK only; every other write still reaches the log.
f1_log="$WORK/f1-append-fail.log"
printf 'CHECK work=PASS\n' >"$f1_log"
f1_rc=0
f1_out=$(lib_snippet 'printf() {
  case "${1:-}" in
    "CHECK cleanup_required=FAIL"*) return 1 ;;
  esac
  builtin printf "$@"
}
bad(){ return 1; }
mp_on_cleanup bad
mp_install_trap
mp_check work PASS >"$1"
mp_finalize "$1" 0' "$f1_log" 2>&1) || f1_rc=$?
if [ "$f1_rc" -ne 0 ]; then
  _pass 'F1: a cleanup failure fails the run even when its evidence append fails'
else
  _fail 'F1: a cleanup failure fails the run even when its evidence append fails' "rc=$f1_rc out=$f1_out"
fi
if [[ "$f1_out" == *'RESULT=PASS'* ]]; then
  _fail 'F1: a failed cleanup append is never published as RESULT=PASS' "$f1_out"
else
  _pass 'F1: a failed cleanup append is never published as RESULT=PASS'
fi
assert_contains 'CLEANUP_FAILED' "$f1_out" 'F1: the unrecorded cleanup failure is reported to the operator'
if grep -q '^CHECK cleanup_required=FAIL' "$f1_log"; then
  _fail 'F1: the fault fixture actually failed the cleanup append' 'the append unexpectedly succeeded'
else
  _pass 'F1: the fault fixture actually failed the cleanup append'
fi

# ------------------------------------------- C2/C4 state-interpretation
section 'C2/C4 state-interpretation primitives'

# mp_capture_service_state: only a conclusive state may authorize a lifecycle
# mutation, and `active` is the value that creates a restoration obligation.
svc() { # <state-output> <status>
  FAKE_OUT="$1" FAKE_RC="$2" lib_snippet \
    'r(){ printf "%s\n" "$FAKE_OUT"; return "$FAKE_RC"; }; out=$(mp_capture_service_state r u); printf "%s rc=%s\n" "$out" "$?"' 2>/dev/null
}
assert_contains 'active rc=0' "$(svc active 0)" 'C2: an active unit is captured (restoration obligation)'
assert_contains 'inactive rc=0' "$(svc inactive 3)" "C2: systemctl's normal inactive status is conclusive"
assert_contains 'dead rc=0' "$(svc dead 3)" 'C2: a dead unit is conclusive'
assert_contains 'failed rc=0' "$(svc failed 3)" 'C2: a failed unit is conclusive (not running)'
assert_contains 'deactivating rc=1' "$(svc deactivating 3)" 'C2: a transitional state is undetermined'
assert_contains ' rc=1' "$(svc '' 1)" 'C2: a failed query is undetermined'
assert_contains 'active rc=1' "$(svc active 1)" 'C2: a plausible state with a failed status is undetermined'

# mp_container_state: a unit that is not known to be active is not proof that
# its container stopped, so the container inventory is the authority.
ctr() { # <ps-status> <names> <inspect-status> <running>
  FAKE_PS_RC="$1" FAKE_NAMES="$2" FAKE_INSPECT_RC="$3" FAKE_RUNNING="$4" lib_snippet \
    'r(){ case "$1 $2" in
       "podman ps") printf "%s\n" "$FAKE_NAMES"; return "$FAKE_PS_RC" ;;
       "podman inspect") printf "%s\n" "$FAKE_RUNNING"; return "$FAKE_INSPECT_RC" ;;
     esac; }; out=$(mp_container_state r hermes-gateway); printf "%s rc=%s\n" "$out" "$?"' 2>/dev/null
}
assert_contains 'running rc=0' "$(ctr 0 hermes-gateway 0 true)" 'C4: a running container is reported'
assert_contains 'stopped rc=1' "$(ctr 0 '' 0 '')" 'C4: an absent container is provably stopped'
assert_contains 'stopped rc=1' "$(ctr 0 hermes-gateway 0 false)" 'C4: a listed but stopped container is stopped'
assert_contains 'unknown rc=2' "$(ctr 125 '' 0 '')" 'C4: a failed inventory is unknown, never stopped'
assert_contains 'unknown rc=2' "$(ctr 0 hermes-gateway 125 '')" 'C4: a failed inspect is unknown'

for helper in m02-deploy-and-validate.sh m03-configure-and-probe.sh; do
  assert_grep 'mp_capture_service_state' "$MANUAL/$helper" \
    "$helper refuses lifecycle mutation when the prior state is undeterminable"
done
assert_grep 'mp_container_state' "$MANUAL/m03-configure-and-probe.sh" \
  'm03-configure uses the container inventory as the live-mount authority'
assert_grep 'mp_container_state' "$MANUAL/m03-contract.sh" \
  'm03-contract uses the container inventory as the live-mount authority'

# ------------------------------------------------- F5 cross-helper profile lock
section 'F5 different helpers contend on one profile lock'

STUB="$WORK/stub"
mkdir -p "$STUB"
TEST_ADMIN='review-fixture-admin'
TEST_HOME="$WORK/admin-home"
mkdir -p "$TEST_HOME"

cat >"$STUB/getent" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = passwd ] && [ "${2:-}" = "${TEST_ADMIN:-}" ]; then
  printf '%s:x:%s:%s::%s:/bin/bash\n' "$2" "$(/usr/bin/id -u)" "$(/usr/bin/id -g)" "${TEST_HOME}"
  exit 0
fi
exec /usr/bin/getent "$@"
EOF
cat >"$STUB/id" <<'EOF'
#!/usr/bin/env bash
# `id -u` with no account is the root check; `id -u hermes` is the runtime UID.
if [ "${1:-}" = -u ]; then
  if [ "${2:-}" = hermes ]; then printf '1001\n'; exit 0; fi
  if [ -z "${2:-}" ]; then printf '0\n'; exit 0; fi
fi
exec /usr/bin/id "$@"
EOF
chmod 0755 "$STUB/getent" "$STUB/id"

PROFILE_LOCK="$WORK/profile.lock"
run_helper_under_lock() { # <helper> [args...]
  local helper="$1"
  shift
  local rc=0
  env -i PATH="$STUB:/usr/bin:/bin" HOME="$WORK" \
    TEST_ADMIN="$TEST_ADMIN" TEST_HOME="$TEST_HOME" HERMES_ADMIN="$TEST_ADMIN" \
    MP_PROFILE_LOCK_PATH="$PROFILE_LOCK" MP_HOST_IDENTITY_FILE=/nonexistent \
    HERMES_EXPECT_MACHINE_ID_SHA256="$MACHINE_HASH" \
    bash "$MANUAL/$helper" --apply "$@" 2>&1 || rc=$?
  return "$rc"
}

env -i PATH="$STUB:/usr/bin:/bin" MP_PROFILE_LOCK_PATH="$PROFILE_LOCK" LIB="$LIB" \
  bash -c 'source "$LIB"; mp_lock_profile; printf "HELD\n" >"$1"; while [ ! -e "$2" ]; do sleep 0.2; done' \
  _ "$WORK/holder-ready" "$WORK/holder-release" >/dev/null 2>&1 &
holder=$!
for _ in $(seq 1 50); do
  [ -s "$WORK/holder-ready" ] && break
  sleep 0.1
done
if [ ! -s "$WORK/holder-ready" ]; then
  _fail 'the F5 lock holder acquired the profile lock' 'holder never became ready'
fi

contending_helpers=(
  m01-host-prepare.sh
  m02-deploy-and-validate.sh
  m03-activate.sh
  m03-configure-and-probe.sh
  m03-accept.sh
  m03-contract.sh
  m04-posture.sh
  m04-backup.sh
  provision-worker-client-key.sh
  provision-openai-key.sh
  provision-telegram.sh
)
for helper in "${contending_helpers[@]}"; do
  out=''
  out=$(run_helper_under_lock "$helper" 2>&1) || true
  assert_contains 'another Hermes manual operation holds' "$out" "$helper is refused while another helper holds the profile lock"
done
# Mutation exclusion (R5): a refused provisioning run must not reach its
# mutation function, even though it would otherwise print a success marker.
mut_out=$(run_helper_under_lock provision-worker-client-key.sh 2>&1) || true
assert_contains 'another Hermes manual operation holds' "$mut_out" \
  'the worker-key helper is refused at the lock'
if [[ "$mut_out" == *'worker client key ready'* ]]; then
  _fail 'the refused worker-key helper reaches no mutation' "$mut_out"
else
  _pass 'the refused worker-key helper reaches no mutation'
fi
: >"$WORK/holder-release"
wait "$holder" 2>/dev/null || true

# The lock file itself is the shared constant; no phase-specific path remains.
phase_locks=0
for script in "$MANUAL"/*.sh; do
  if grep -qE '/run/lock/hermes-manual-(m0[0-9]|phase)' "$script"; then
    phase_locks=$((phase_locks + 1))
  fi
done
assert_equals '0' "$phase_locks" 'no helper keeps a phase-specific lock path'

# ------------------------------------------------------------- F6 egress probe
section 'F6 egress-probe classification'

classify() { lib_snippet 'mp_classify_egress "$1" "$2"' "$1" "$2"; }
assert_equals 'EGRESS_SUCCESS' "$(classify 0 '')" 'a completed probe is egress success'
assert_equals 'EGRESS_DENIED' "$(classify 7 'curl: (7) Failed to connect to 198.51.100.1 port 80: Network is unreachable')" \
  'a refused/unreachable network is denial'
assert_equals 'DNS_FAILURE' "$(classify 6 'curl: (6) Could not resolve host: example.com')" 'rc 6 is a DNS failure'
assert_equals 'PROBE_TIMEOUT' "$(classify 28 '')" 'rc 28 is a probe timeout'
assert_equals 'PROBE_UNAVAILABLE' "$(classify 127 'sh: 1: curl: not found')" 'a missing tool is unavailable, never denial'
assert_equals 'PROBE_UNAVAILABLE' "$(classify 1 'curl: command not found')" 'command-not-found text is unavailable'
assert_equals 'PROBE_ERROR' "$(classify 2 'unexpected local failure')" 'an unclassifiable probe is an error, not isolation'

assert_no_grep 'EGRESS_YES|EGRESS_NO' "$MANUAL/m02-deploy-and-validate.sh" \
  'm02 no longer treats any probe failure as denied egress'
assert_grep 'PROBE_TOOLS_PRESENT' "$MANUAL/m02-deploy-and-validate.sh" \
  'm02 proves the probe tools exist before probing'
assert_grep 'mp_classify_egress' "$MANUAL/m02-deploy-and-validate.sh" \
  'm02 uses the shared classifier'
assert_grep 'ipv6' "$MANUAL/m02-deploy-and-validate.sh" 'm02 covers IPv6 as well as IPv4'

# R7: a missing resolver or a timed-out query must not be graded as isolation.
classify_dns() { lib_snippet 'mp_classify_dns "$1" "$2"' "$1" "$2"; }
assert_equals 'DNS_RESOLVED' "$(classify_dns 0 '93.184.216.34  example.com')" \
  'a resolved name is a real isolation failure'
assert_equals 'DNS_UNRESOLVED' "$(classify_dns 2 '')" \
  'a definitive not-found is the expected denied case'
assert_equals 'DNS_TIMEOUT' "$(classify_dns 124 '')" \
  'a timed-out query is inconclusive, not isolation'
assert_equals 'PROBE_UNAVAILABLE' "$(classify_dns 127 'getent: not found')" \
  'a missing resolver command is unavailable, never isolation'
assert_equals 'PROBE_ERROR' "$(classify_dns 1 'unexpected local failure')" \
  'an execution failure is inconclusive'
assert_grep 'mp_classify_dns' "$MANUAL/m02-deploy-and-validate.sh" \
  'm02 uses the shared DNS classifier'
assert_grep 'command -v getent' "$MANUAL/m02-deploy-and-validate.sh" \
  'm02 proves the resolver command exists before probing'

# R7 behavioral: execute the REAL m02 DNS block (extracted between its markers)
# with a mocked `h`, so the probe → status-capture → grading wiring is exercised,
# not just the classifier. Only a definitive unresolved result may PASS.
DNS_BLOCK=$(sed -n '/^  # MP-DNS-GRADING-BEGIN/,/^  # MP-DNS-GRADING-END/p' \
  "$MANUAL/m02-deploy-and-validate.sh")
if [ -z "$DNS_BLOCK" ]; then
  _fail 'the m02 DNS grading block is extractable' 'markers not found'
else
  _pass 'the m02 DNS grading block is extractable'
fi
DNS_RUNNER="$WORK/dns-runner.sh"
{
  printf '#!/usr/bin/env bash\nsource "$LIB"\n'
  printf 'h() { printf "%%s\\n" "${STUB_DNS_RAW:-}"; }\n'
  printf 'resolver_tools="${STUB_RESOLVER_TOOLS:-RESOLVER_PRESENT}"\n'
  printf 'WORKER_NAME=hermes-worker\n'
  printf '%s\n' "$DNS_BLOCK"
} >"$DNS_RUNNER"
run_dns_block() { # <resolver-tools> <raw>
  STUB_RESOLVER_TOOLS="$1" STUB_DNS_RAW="$2" bash "$DNS_RUNNER" 2>&1
}
assert_contains 'mp_classify_dns' "$(cat "$DNS_RUNNER")" 'the executed block is the real classifier wiring'
assert_contains 'worker_dns_isolation=FAIL' \
  "$(run_dns_block RESOLVER_PRESENT '93.184.216.34  example.com
rc=0')" \
  'a resolved name fails DNS isolation'
assert_contains 'worker_dns_isolation=PASS' \
  "$(run_dns_block RESOLVER_PRESENT 'rc=2')" \
  'only a definitive unresolved result passes DNS isolation'
assert_contains 'worker_dns_isolation=UNVERIFIED' \
  "$(run_dns_block RESOLVER_PRESENT 'rc=124')" \
  'a timed-out query is UNVERIFIED, never isolation'
assert_contains 'worker_dns_isolation=UNVERIFIED' \
  "$(run_dns_block RESOLVER_PRESENT "timeout: failed to run command 'getent': No such file or directory
rc=127")" \
  'a missing resolver command inside the probe is UNVERIFIED'
assert_contains 'worker_dns_isolation=UNVERIFIED' \
  "$(run_dns_block RESOLVER_PRESENT 'Error: no such container: hermes-worker')" \
  'a probe execution error is UNVERIFIED'
assert_contains 'worker_dns_isolation=UNVERIFIED' \
  "$(run_dns_block RESOLVER_ABSENT 'rc=2')" \
  'an absent resolver is UNVERIFIED before any probe'
if [[ "$(run_dns_block RESOLVER_PRESENT 'rc=2')" == *'rc=2'* && "$(run_dns_block RESOLVER_PRESENT 'rc=2')" == *'class=DNS_UNRESOLVED'* ]]; then
  _pass 'the block reports the captured resolver status and class'
else
  _fail 'the block reports the captured resolver status and class'
fi

# ------------------------------------------------------------- F7 audit result
section 'F7 centralized audit-result interpretation'

AUDIT_STUB="$WORK/audit"
mkdir -p "$AUDIT_STUB"
make_ausearch() { # <mode>
  cat >"$AUDIT_STUB/ausearch" <<EOF
#!/usr/bin/env bash
printf '%s\n' "\${AUSEARCH_STUB_OUTPUT:-}"
exit "\${AUSEARCH_STUB_RC:-0}"
EOF
  chmod 0755 "$AUDIT_STUB/ausearch"
}

run_audit() { # <rc> <output>
  local rc="$1" output="$2"
  AUSEARCH_STUB_RC="$rc" AUSEARCH_STUB_OUTPUT="$output" \
    PATH="$AUDIT_STUB:/usr/bin:/bin" bash -c 'source "$LIB"; mp_audit_avc_check avc_denials recent' 2>&1
}

make_ausearch
assert_contains 'CHECK avc_denials=PASS' "$(run_audit 1 '<no matches>')" \
  'a clean log (non-zero rc, "<no matches>") is a PASS'
assert_contains 'CHECK avc_denials=FAIL' "$(run_audit 0 'type=AVC msg=audit(1.2:3): avc: denied { read }')" \
  'actual denials are a FAIL'
assert_contains 'CHECK avc_denials=UNVERIFIED' "$(run_audit 2 'Error opening config file /etc/audit/auditd.conf')" \
  'an audit-read error is UNVERIFIED'
assert_contains 'CHECK avc_denials=PASS' "$(run_audit 0 '')" 'an empty clean result is a PASS'

# Absent tool: a PATH with coreutils but no ausearch. Invoke bash by absolute
# path because the restricted PATH deliberately has no bash.
STUB_ONLY="$WORK/stub-only"
mkdir -p "$STUB_ONLY"
for tool in grep tail; do ln -sf "/usr/bin/$tool" "$STUB_ONLY/$tool"; done
absent_out=$(PATH="$STUB_ONLY" /usr/bin/bash -c 'source "$LIB"; mp_audit_avc_check avc_denials recent' 2>&1) || true
assert_contains 'CHECK avc_denials=UNVERIFIED' "$absent_out" 'an absent ausearch is UNVERIFIED'

# Every helper that GRADES an ausearch result uses the shared function; helpers
# that merely print the audit view (diagnostics) are not graded.
audit_users=0
old_pattern=0
unguarded=0
for script in "$MANUAL"/*.sh; do
  if grep -q 'mp_audit_avc_check' "$script"; then
    audit_users=$((audit_users + 1))
  fi
  if grep -q 'mp_check avc_denials' "$script"; then
    old_pattern=$((old_pattern + 1))
  fi
  if grep -q 'ausearch -m AVC,USER_AVC' "$script" && grep -q 'mp_check' "$script" \
    && ! grep -q 'mp_audit_avc_check' "$script"; then
    unguarded=$((unguarded + 1))
    _fail "$(basename "$script") grades ausearch without the shared classifier"
  fi
done
assert_min_count 8 "$audit_users" 'helpers using the centralized audit check were enumerated'
assert_equals '0' "$old_pattern" 'no helper keeps the old ad-hoc avc_denials interpretation'
assert_equals '0' "$unguarded" 'no helper grades an ausearch result outside the shared classifier'

# ------------------------------------------- F9 required / info / deferred
section 'F9 check kinds and partial acceptance'

log_deferred="$WORK/deferred.log"
lib_snippet 'mp_check required_ok PASS; mp_defer provider_acceptance "Gate 3 owns it"' >"$log_deferred"
deferred_rc=0
deferred_out=$(bash -c 'source "$LIB"; mp_finalize "$1" 0' _ "$log_deferred" 2>&1) || deferred_rc=$?
assert_equals '0' "$deferred_rc" 'a deferred check does not block a gate that excludes it'
assert_contains 'PARTIAL' "$deferred_out" 'a deferred check is reported as a partial result'
assert_contains 'check_deferred=1' "$deferred_out" 'the deferred count is reported'

log_unverified="$WORK/unverified2.log"
lib_snippet 'mp_check required_ok PASS; mp_check required_bad UNVERIFIED "no data"' >"$log_unverified"
unverified_rc=0
bash -c 'source "$LIB"; mp_finalize "$1" 0' _ "$log_unverified" >/dev/null 2>&1 || unverified_rc=$?
assert_equals '3' "$unverified_rc" 'an UNVERIFIED required check still blocks'

log_info="$WORK/info.log"
lib_snippet 'mp_info diagnostic "just a measurement"; mp_check required_ok PASS' >"$log_info"
info_total=$(bash -c 'source "$LIB"; mp_finalize "$1" 0' _ "$log_info" 2>&1 | sed -n 's/^check_total=\([0-9]*\).*/\1/p')
assert_equals '1' "$info_total" 'informational output is not counted as a check'

# ------------------------------------------- F10 convergence primitives
section 'F10 convergence primitives'

same="$WORK/same.txt"
printf 'content\n' >"$same"
lib_snippet 'mp_content_differs "$1" "$1"' "$same" >/dev/null 2>&1 && differs=0 || differs=$?
assert_equals '1' "$differs" 'identical content reports no difference'
printf 'other\n' >"$WORK/other.txt"
lib_snippet 'mp_content_differs "$1" "$2"' "$same" "$WORK/other.txt" >/dev/null 2>&1 && differs=0 || differs=$?
assert_equals '0' "$differs" 'different content reports a difference'
lib_snippet 'mp_content_differs "$1" "$2"' "$WORK/missing.txt" "$same" >/dev/null 2>&1 && differs=0 || differs=$?
assert_equals '0' "$differs" 'a missing destination reports a difference'

stamp="$WORK/stamp"
lib_snippet 'mp_write_stamp "$1" abc123' "$stamp" >/dev/null
lib_snippet 'mp_stamp_matches "$1" abc123' "$stamp" && matched=0 || matched=$?
assert_equals '0' "$matched" 'a matching stamp is recognised'
lib_snippet 'mp_stamp_matches "$1" other' "$stamp" >/dev/null 2>&1 && matched=0 || matched=$?
assert_equals '1' "$matched" 'a mismatched stamp is not recognised'

lib_snippet 'mp_should_rebuild "$1" abc123 1' "$stamp" >/dev/null 2>&1 && rebuild=0 || rebuild=$?
assert_equals '1' "$rebuild" 'a matching stamp with an existing image skips the rebuild'
lib_snippet 'mp_should_rebuild "$1" abc123 0' "$stamp" && rebuild=0 || rebuild=$?
assert_equals '0' "$rebuild" 'a missing image forces the rebuild'
lib_snippet 'mp_should_rebuild "$1" different 1' "$stamp" && rebuild=0 || rebuild=$?
assert_equals '0' "$rebuild" 'changed inputs force the rebuild'

# ------------------------------------------- R4 install reconcile / propagation
section 'R4 installation failure propagation and mode reconciliation'

src="$WORK/install-src"
printf 'installed content\n' >"$src"
chmod 0644 "$src"
dest="$WORK/install-dest"
printf 'installed content\n' >"$dest"
chmod 0777 "$dest"
install_out=$(lib_snippet 'mp_install_if_changed 0640 - "$1" "$2"' "$src" "$dest")
assert_equals '640' "$(stat -c %a "$dest")" 'an unchanged destination still has its mode reconciled'
assert_contains 'UNCHANGED' "$install_out" 'unchanged content is reported as unchanged'
chmod 0644 "$src"
printf 'different content\n' >"$WORK/install-other"
install_out=$(lib_snippet 'mp_install_if_changed 0640 - "$1" "$2"' "$WORK/install-other" "$dest")
assert_equals '640' "$(stat -c %a "$dest")" 'changed content is installed with the required mode'
assert_contains 'CHANGED' "$install_out" 'changed content is reported as changed'

readonly_dir="$WORK/readonly-dir"
mkdir -p "$readonly_dir"
chmod 0500 "$readonly_dir"
install_rc=0
lib_snippet 'mp_install_if_changed 0644 - "$1" "$2"' "$src" "$readonly_dir/new-file" >/dev/null 2>&1 || install_rc=$?
assert_equals '1' "$install_rc" 'an install failure is propagated, not swallowed'

reconcile_out=$(lib_snippet 'mp_install_reconcile probe 0644 - "$1" "$2"; echo "rc=$?"' "$src" "$dest") || true
assert_contains 'CHECK probe=PASS' "$reconcile_out" 'a reconciled install records a PASS check'
reconcile_missing=$(lib_snippet 'mp_install_reconcile probe 0644 - "$1" "$2"; echo "rc=$?"' "$src" "$readonly_dir/new-file") || true
assert_contains 'CHECK probe=FAIL' "$reconcile_missing" 'a failed install records a FAIL check and returns nonzero'
chmod 0700 "$readonly_dir"

# A fully converged install must not churn metadata: a second identical call
# leaves the status-change time untouched, while a drifted mode is repaired.
chmod 0640 "$dest"
lib_snippet 'mp_install_if_changed 0640 - "$1" "$2"' "$WORK/install-other" "$dest" >/dev/null
ctime_before=$(stat -c '%z' "$dest")
lib_snippet 'mp_install_if_changed 0640 - "$1" "$2"' "$WORK/install-other" "$dest" >/dev/null
assert_equals "$ctime_before" "$(stat -c '%z' "$dest")" \
  'a converged install does not rewrite already-correct metadata'
chmod 0666 "$dest"
lib_snippet 'mp_install_if_changed 0640 - "$1" "$2"' "$WORK/install-other" "$dest" >/dev/null
assert_equals '640' "$(stat -c %a "$dest")" 'drifted metadata is still repaired on the unchanged-content path'

# No caller may hide an installation failure.
for caller in m02-deploy-and-validate.sh m03-activate.sh m03-contract.sh \
  m03-configure-and-probe.sh m04-posture.sh; do
  assert_grep 'mp_install_reconcile' "$MANUAL/$caller" "$caller uses the reconciling installer"
  assert_grep '\|\| exit 1' "$MANUAL/$caller" "$caller propagates an installation failure"
done

# R3 wiring: every helper that stops a service appends a required restoration
# CHECK before mp_finalize, so a failed restoration fails an otherwise-green run.
for helper in m02-deploy-and-validate.sh m03-configure-and-probe.sh m04-backup.sh; do
  restore_line=$(grep -nE 'CHECK restore_[a-z_]+=(PASS|FAIL)' "$MANUAL/$helper" | tail -n1 | cut -d: -f1 || true)
  finalize_line=$(grep -n 'mp_finalize' "$MANUAL/$helper" | tail -n1 | cut -d: -f1 || true)
  if [[ -n "$restore_line" && -n "$finalize_line" && "$restore_line" -lt "$finalize_line" ]]; then
    _pass "$helper records restoration before publishing the final result"
  else
    _fail "$helper records restoration before publishing the final result" \
      "restore=${restore_line:-none} finalize=${finalize_line:-none}"
  fi
done

# ------------------------------------------- F8 credential-free contract path
section 'F8 credential-free contract application path'

readonly CONTRACT_HELPER="$MANUAL/m03-contract.sh"
readonly GATE2_PLAN="$REPO_ROOT/docs/plans/2026-09-20-hermes-manual-gate2-lab-plan.md"
if [ -x "$CONTRACT_HELPER" ] || [ -f "$CONTRACT_HELPER" ]; then
  _pass 'the credential-free contract helper exists'
else
  _fail 'the credential-free contract helper exists'
fi
assert_grep 'manual-harden-config\.py' "$CONTRACT_HELPER" 'the contract helper applies the contract'
assert_grep 'manual-verify-contract\.py' "$CONTRACT_HELPER" 'the contract helper verifies the contract'
assert_grep 'mp_defer' "$CONTRACT_HELPER" 'provider acceptance is deferred, not required, in the credential-free path'
assert_grep 'm03-contract\.sh' "$GATE2_PLAN" 'the Gate 2 plan sequences the contract-application step'

# ------------------------------------------- F1 privileged-wrapper dependency
section 'F1 the privileged wrapper executes no checkout code'

F1_LIBEXEC="$WORK/f1/libexec"
F1_CHECKOUT="$WORK/f1/checkout"
mkdir -p "$F1_LIBEXEC" "$F1_CHECKOUT" "$WORK/f1/home/.local/state/hermes-manual-lab"
printf 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA review@test\n' \
  >"$WORK/f1/home/.local/state/hermes-manual-lab/id_ed25519.pub"
printf 'root-owned template\n' >"$F1_LIBEXEC/gate2-kickstart.ks.in"

cat >"$F1_LIBEXEC/gate2-make-kickstart.sh" <<'EOF'
#!/usr/bin/env bash
# Stand-in for the root-owned generator: records that it ran and the scope it saw.
printf 'libexec-ran KS_DIR=%s\n' "${GATE2_KS_DIR:-unset}" >>"$(dirname "$0")/executed.marker"
exit 0
EOF
cat >"$F1_CHECKOUT/gate2-make-kickstart.sh" <<'EOF'
#!/usr/bin/env bash
printf 'checkout-ran\n' >>"$(dirname "$0")/executed.marker"
exit 0
EOF
chmod 0755 "$F1_LIBEXEC/gate2-make-kickstart.sh" "$F1_CHECKOUT/gate2-make-kickstart.sh"

# Stub identity and ownership only; the wrapper's checks are what is under test.
cat >"$STUB/id" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = -u ]; then printf '0\n'; exit 0; fi
exec /usr/bin/id "$@"
EOF
cat >"$STUB/getent" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = passwd ]; then
  printf '%s:x:0:0::%s:/bin/bash\n' "${2:-root}" "${F1_HOME}"
  exit 0
fi
exec /usr/bin/getent "$@"
EOF
cat >"$STUB/stat" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = -c ] && [ "${2:-}" = %U ]; then
  case "${3:-}" in "$F1_LIBEXEC" | "$F1_LIBEXEC"/*) printf 'root\n'; exit 0 ;; esac
fi
exec /usr/bin/stat "$@"
EOF
chmod 0755 "$STUB/id" "$STUB/getent" "$STUB/stat"

run_rebuild() { # [args...]
  local rc=0
  env -i PATH="$STUB:/usr/bin:/bin" HOME="$WORK" SUDO_USER=reviewer \
    F1_HOME="$WORK/f1/home" F1_LIBEXEC="$F1_LIBEXEC" \
    GATE2_KS_DIR=/evil/should-be-ignored \
    HERMES_GATE2_LIBEXEC="$F1_LIBEXEC" \
    bash "$REBUILD_WRAPPER" "$@" 2>&1 || rc=$?
  return "$rc"
}

run_rebuild >"$WORK/f1/out" 2>&1 || true
if [ -s "$F1_LIBEXEC/executed.marker" ] && [ ! -e "$F1_CHECKOUT/executed.marker" ]; then
  _pass 'the wrapper executes the root-owned generator, not a checkout copy'
else
  _fail 'the wrapper executes the root-owned generator, not a checkout copy' "$(cat "$WORK/f1/out")"
fi
assert_contains 'KS_DIR=/var/lib/libvirt/boot/lab-hermes-manual-r1' \
  "$(cat "$F1_LIBEXEC/executed.marker" 2>/dev/null || true)" \
  'the wrapper fixes the output scope and scrubs the caller environment'
rebuild_code=$(grep -vE '^[[:space:]]*#' "$REBUILD_WRAPPER" || true)
if grep -q 'repo-path' <<<"$rebuild_code"; then
  _fail 'the wrapper does not read a checkout path' 'executable code references repo-path'
else
  _pass 'the wrapper does not read a checkout path'
fi

# A symlinked or group/world-writable dependency is refused before execution.
rm -f "$F1_LIBEXEC/executed.marker"
mv "$F1_LIBEXEC/gate2-make-kickstart.sh" "$F1_LIBEXEC/generator.real"
ln -s "$F1_CHECKOUT/gate2-make-kickstart.sh" "$F1_LIBEXEC/gate2-make-kickstart.sh"
symlink_out=$(run_rebuild 2>&1) || true
assert_contains 'symlinked dependency' "$symlink_out" 'a symlinked generator is refused'
rm -f "$F1_LIBEXEC/gate2-make-kickstart.sh"
mv "$F1_LIBEXEC/generator.real" "$F1_LIBEXEC/gate2-make-kickstart.sh"

rm -f "$F1_LIBEXEC/executed.marker"
chmod 0777 "$F1_LIBEXEC/gate2-make-kickstart.sh"
writable_out=$(run_rebuild 2>&1) || true
assert_contains 'group/world-writable' "$writable_out" 'a group/world-writable generator is refused'
assert_equals '' "$(cat "$F1_LIBEXEC/executed.marker" 2>/dev/null || true)" 'a refused generator never runs'
chmod 0755 "$F1_LIBEXEC/gate2-make-kickstart.sh"

arg_out=$(run_rebuild --extra 2>&1) || true
assert_contains 'takes no arguments' "$arg_out" 'the wrapper refuses call-time arguments'

print_summary
