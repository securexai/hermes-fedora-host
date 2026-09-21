#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC1091,SC2034
# Behavioral tests for m04-backup.sh (review finding 3).
#
# A synthetic profile tree is archived and restored with stubbed external
# commands. Fault injection covers: a failed stop command, a sticky active
# writer, archive-creation failure, extraction failure and metadata drift.
# C2: an undeterminable pre-run service state refuses the stop, so no service is
# stranded and no false restoration PASS is emitted. No root, no container, no
# network, no real credential.
#
#   ./tests/test-hermes-manual-backup.sh [-v]

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

readonly BACKUP_HELPER="$REPO_ROOT/scripts/hermes/manual/m04-backup.sh"

VERBOSE=false
[[ "${1:-}" == -v ]] && VERBOSE=true

WORK=$(mktemp -d)
readonly WORK
trap 'rm -rf -- "$WORK"' EXIT

MACHINE_HASH=$(sha256sum /etc/machine-id | cut -d' ' -f1)
readonly MACHINE_HASH
readonly TEST_ADMIN='backup-fixture-admin'

SANDBOX="$WORK/sandbox"
STUB="$SANDBOX/stub"
STATES="$SANDBOX/states"
TMPROOT="$SANDBOX/tmp"
ADMIN_HOME="$SANDBOX/admin-home"
RUNTIME_HOME="$SANDBOX/home/hermes"
QUADLET_DIR="$SANDBOX/quadlets"
mkdir -p "$STUB" "$STATES" "$TMPROOT" "$ADMIN_HOME" \
  "$RUNTIME_HOME/gateway-state" "$RUNTIME_HOME/worker-state/ssh-host-keys" \
  "$RUNTIME_HOME/gateway-ssh" "$QUADLET_DIR"

# --- synthetic profile ------------------------------------------------------
printf 'terminal:\n  backend: ssh\n  ssh_host: worker\n' >"$RUNTIME_HOME/gateway-state/config.yaml"
printf '%s=%s\nUNRELATED=keep\n' 'OPENAI_API_KEY' 'synthetic-not-a-real-key' >"$RUNTIME_HOME/gateway-state/.env"
chmod 0600 "$RUNTIME_HOME/gateway-state/.env"
printf 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA worker\n' \
  >"$RUNTIME_HOME/worker-state/ssh-host-keys/ssh_host_ed25519_key.pub"
printf 'worker ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n' \
  >"$RUNTIME_HOME/gateway-ssh/known_hosts"
printf '# gateway quadlet\n' >"$QUADLET_DIR/hermes-gateway.container"
printf '# worker quadlet\n' >"$QUADLET_DIR/hermes-worker.container"

# --- stubs ------------------------------------------------------------------
write_stub() { # <name> <<'EOF'
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

write_stub systemctl <<'EOF'
#!/usr/bin/env bash
verb="${2:-}"
unit="${3:-}"
case "$verb" in
  is-active)
    # Query-failure and transitional-state injection (R2/R3). The normal path
    # models real systemctl: it prints the state and returns 0 for active, 3 for
    # anything else. STUB_ISACTIVE_RC forces a bare status with no output, which
    # is a genuine query failure. STUB_ISACTIVE_FAIL_UNTIL_STOP models a transient
    # failure that affects ONLY the pre-stop queries (C2).
    if [ "${STUB_ISACTIVE_FAIL_UNTIL_STOP:-0}" = 1 ] && [ ! -e "${STUB_STATES:?}/stopped-once" ]; then
      exit 1
    fi
    if [ -n "${STUB_ISACTIVE_RC:-}" ]; then exit "$STUB_ISACTIVE_RC"; fi
    if [ -n "${STUB_ISACTIVE_STATE:-}" ]; then printf '%s\n' "$STUB_ISACTIVE_STATE"; exit 0; fi
    if [ -f "${STUB_STATES:?}/$unit" ]; then st=$(cat "${STUB_STATES}/$unit"); else st=inactive; fi
    # A state string that looks stopped but arrives with an unexpected status is
    # still a failed query; the helper must not read the text alone.
    if [ -n "${STUB_ISACTIVE_FORCE_RC:-}" ]; then printf '%s\n' "$st"; exit "$STUB_ISACTIVE_FORCE_RC"; fi
    printf '%s\n' "$st"
    case "$st" in active) exit 0 ;; *) exit 3 ;; esac
    ;;
  stop)
    [ "${STUB_STOP_FAIL:-}" = "$unit" ] && exit 1
    [ "${STUB_STICKY:-0}" = 1 ] && exit 0
    : >"${STUB_STATES:?}/stopped-once"
    printf 'inactive\n' >"${STUB_STATES}/$unit"
    ;;
  start)
    [ "${STUB_START_FAIL:-}" = "$unit" ] && exit 1
    printf 'active\n' >"${STUB_STATES}/$unit"
    ;;
  show) printf 'MemoryHigh=6G\n' ;;
esac
exit 0
EOF

write_stub podman <<'EOF'
#!/usr/bin/env bash
case "${1:-}" in
  inspect) printf 'readonly_rootfs=true memory=0 pids=0 netmode=none userns=keep-id privileged=false\nsecurityopt=[]\ncapdrop=[] capadd=[]\nbinds=\n' ;;
  ps)
    [ "${STUB_PODMAN_PS_RC:-0}" = 0 ] || exit "${STUB_PODMAN_PS_RC}"
    [ -n "${STUB_RUNNING:-}" ] && printf '%s\n' "$STUB_RUNNING"
    ;;
esac
exit 0
EOF

# Real tar, with optional injected failures and metadata drift.
write_stub tar <<'EOF'
#!/usr/bin/env bash
args="$*"
if [[ "$args" == *' -cpf '* ]] && [ "${STUB_TAR_CREATE_FAIL:-0}" = 1 ]; then
  printf 'tar: injected create failure\n' >&2
  exit 2
fi
if [[ "$args" == *' -xpf '* ]] && [ "${STUB_TAR_EXTRACT_FAIL:-0}" = 1 ]; then
  printf 'tar: injected extract failure\n' >&2
  exit 2
fi
/usr/bin/tar "$@"
rc=$?
if [ "$rc" -eq 0 ] && [[ "$args" == *' -xpf '* ]] && [ "${STUB_TAR_BREAK_META:-0}" = 1 ]; then
  dest=''
  prev=''
  for a in "$@"; do
    if [ "$prev" = '-C' ]; then dest="$a"; fi
    prev="$a"
  done
  target=''
  if [ -n "$dest" ]; then
    target=$(find "$dest" -path "*${STUB_BREAK_META_PATH:-}" -print -quit 2>/dev/null || true)
  fi
  [ -n "$target" ] && chmod 0777 "$target" || true
fi
exit "$rc"
EOF
unset -f write_stub

reset_sandbox() { # <label>
  local label="$1"
  rm -rf "$SANDBOX/backups-$label"
  rm -f "$SANDBOX/lock-$label" "$ADMIN_HOME/hermes-m04-backup.out"
  printf 'active\n' >"$STATES/hermes-gateway.service"
  printf 'active\n' >"$STATES/hermes-worker.service"
  rm -f "$STATES/stopped-once"
  rm -rf "$TMPROOT"/* 2>/dev/null || true
}

run_backup() { # <label> ; env overrides come from the caller
  local label="$1"
  local rc=0
  env -i PATH="$STUB:/usr/bin:/bin" HOME="$ADMIN_HOME" \
    TEST_ADMIN="$TEST_ADMIN" TEST_HOME="$ADMIN_HOME" HERMES_ADMIN="$TEST_ADMIN" \
    HERMES_RUNTIME_HOME="$RUNTIME_HOME" HERMES_QUADLET_DIR="$QUADLET_DIR" \
    HERMES_BACKUP_BASE="$SANDBOX/backups-$label" \
    MP_PROFILE_LOCK_PATH="$SANDBOX/lock-$label" MP_HOST_IDENTITY_FILE=/nonexistent \
    HERMES_EXPECT_MACHINE_ID_SHA256="$MACHINE_HASH" \
    STUB_STATES="$STATES" STUB_RUNNING="${STUB_RUNNING:-}" \
    STUB_STOP_FAIL="${STUB_STOP_FAIL:-}" STUB_STICKY="${STUB_STICKY:-0}" \
    STUB_START_FAIL="${STUB_START_FAIL:-}" \
    STUB_ISACTIVE_RC="${STUB_ISACTIVE_RC:-}" STUB_ISACTIVE_STATE="${STUB_ISACTIVE_STATE:-}" \
    STUB_ISACTIVE_FORCE_RC="${STUB_ISACTIVE_FORCE_RC:-}" \
    STUB_ISACTIVE_FAIL_UNTIL_STOP="${STUB_ISACTIVE_FAIL_UNTIL_STOP:-0}" \
    STUB_PODMAN_PS_RC="${STUB_PODMAN_PS_RC:-0}" \
    STUB_TAR_CREATE_FAIL="${STUB_TAR_CREATE_FAIL:-0}" \
    STUB_TAR_EXTRACT_FAIL="${STUB_TAR_EXTRACT_FAIL:-0}" \
    STUB_TAR_BREAK_META="${STUB_TAR_BREAK_META:-0}" \
    STUB_BREAK_META_PATH="${STUB_BREAK_META_PATH:-}" \
    TMPDIR="$TMPROOT" \
    bash "$BACKUP_HELPER" --apply 2>&1 || rc=$?
  return "$rc"
}

# --- happy path -------------------------------------------------------------
section 'm04-backup happy path'
reset_sandbox happy
happy_out=''
happy_rc=0
happy_out=$(run_backup happy) || happy_rc=$?
assert_equals '0' "$happy_rc" 'a consistent stopped-state backup and restore passes'
assert_contains 'CHECK writers_stopped=PASS' "$happy_out" 'all writers are confirmed stopped before archiving'
assert_contains 'hermes-worker_state=inactive (query_rc=3)' "$happy_out" \
  "systemctl's normal nonzero inactive status is accepted as stopped evidence"
assert_contains 'CHECK restore_extract=PASS' "$happy_out" 'the archive extracts cleanly'
assert_contains 'CHECK restore_metadata=PASS' "$happy_out" 'restored metadata matches the source'
archive=$(find "$SANDBOX/backups-happy" -name app-state.tar 2>/dev/null | head -n1 || true)
if [ -n "$archive" ] && [ -s "$archive" ] && tar -tf "$archive" >/dev/null 2>&1; then
  _pass 'the stopped-state archive was created and is readable'
else
  _fail 'the stopped-state archive was created and is readable' "archive='$archive'"
fi
manifest=$(find "$SANDBOX/backups-happy" -name manifest.txt 2>/dev/null | head -n1 || true)
if [ -n "$manifest" ] && grep -q '^created_utc=' "$manifest"; then
  _pass 'the backup manifest records the archive identity'
else
  _fail 'the backup manifest records the archive identity' "manifest='$manifest'"
fi
if [ "$(cat "$STATES/hermes-gateway.service")" = 'active' ] && [ "$(cat "$STATES/hermes-worker.service")" = 'active' ]; then
  _pass 'prior service state is restored after a successful run'
else
  _fail 'prior service state is restored after a successful run'
fi
if [ -z "$(find "$TMPROOT" -mindepth 1 -print -quit)" ]; then
  _pass 'the restored credential copy is removed'
else
  _fail 'the restored credential copy is removed' "$(find "$TMPROOT" -mindepth 1)"
fi

# --- stop command failure ---------------------------------------------------
section 'm04-backup fault injection: stop and writer state'
reset_sandbox stopfail
STUB_STOP_FAIL='hermes-worker.service'
stopfail_out=$(run_backup stopfail) || true
unset STUB_STOP_FAIL
assert_contains 'CHECK writers_stopped=FAIL' "$stopfail_out" 'a failed stop command fails the writer check'
assert_contains 'CHECK backup_archive=FAIL' "$stopfail_out" 'archiving is refused when writers are not stopped'
assert_equals '' "$(find "$SANDBOX/backups-stopfail" -name app-state.tar -print -quit 2>/dev/null || true)" \
  'no archive is created when writers are not stopped'
if [ "$(cat "$STATES/hermes-worker.service")" = 'active' ]; then
  _pass 'service state is restored after an ordinary failure'
else
  _fail 'service state is restored after an ordinary failure'
fi

reset_sandbox sticky
STUB_STICKY=1
sticky_out=$(run_backup sticky) || true
unset STUB_STICKY
assert_contains 'CHECK writers_stopped=FAIL' "$sticky_out" 'a writer still active after stop fails the writer check'

reset_sandbox running
STUB_RUNNING='hermes-gateway'
running_out=$(run_backup running) || true
unset STUB_RUNNING
assert_contains 'CHECK writers_stopped=FAIL' "$running_out" 'a running profile container fails the writer check'

# Strict stopped-writer evidence (R2): a failed query, a transitional state or a
# failed container query must all be inconclusive, never "stopped".
reset_sandbox queryfail
STUB_ISACTIVE_RC=1
queryfail_out=$(run_backup queryfail) || true
unset STUB_ISACTIVE_RC
assert_contains 'CHECK writers_stopped=FAIL' "$queryfail_out" 'a failed service query is not proof the writers stopped'

# A state string that looks stopped but arrives with an unexpected status is still
# a failed query: the strengthened check must reject it rather than trust the text.
reset_sandbox forcedrc
STUB_ISACTIVE_FORCE_RC=1
forcedrc_out=$(run_backup forcedrc) || true
unset STUB_ISACTIVE_FORCE_RC
assert_contains 'CHECK writers_stopped=FAIL' "$forcedrc_out" \
  'an unexpected query status is rejected even when the state text looks stopped'

reset_sandbox transitional
STUB_ISACTIVE_STATE='deactivating'
transitional_out=$(run_backup transitional) || true
unset STUB_ISACTIVE_STATE
assert_contains 'CHECK writers_stopped=FAIL' "$transitional_out" 'a transitional service state is not proof the writers stopped'

reset_sandbox podmanfail
STUB_PODMAN_PS_RC=125
podmanfail_out=$(run_backup podmanfail) || true
unset STUB_PODMAN_PS_RC
assert_contains 'CHECK writers_stopped=FAIL' "$podmanfail_out" 'a failed container query is not proof the writers stopped'

# C2: only the queries BEFORE the first stop fail transiently. The services are
# active and the rest of the run would work, but the helper cannot know its
# restoration obligation, so it must not stop anything. Previously it stopped
# both, archived, and reported a restoration PASS while leaving both inactive.
reset_sandbox priorqueryfail
STUB_ISACTIVE_FAIL_UNTIL_STOP=1
c2_rc=0
c2_out=$(run_backup priorqueryfail) || c2_rc=$?
unset STUB_ISACTIVE_FAIL_UNTIL_STOP
assert_contains 'CHECK prior_service_state=FAIL' "$c2_out" \
  'C2: an undeterminable pre-run service state is a failed required check'
assert_contains 'CHECK writers_stopped=FAIL' "$c2_out" 'C2: writers are not stopped when the prior state is unknown'
assert_contains 'CHECK backup_archive=FAIL' "$c2_out" 'C2: archiving is refused when the prior state is unknown'
assert_equals '' "$(find "$SANDBOX/backups-priorqueryfail" -name app-state.tar -print -quit 2>/dev/null || true)" \
  'C2: no archive is created when the prior state is unknown'
if [ "$(cat "$STATES/hermes-gateway.service")" = 'active' ] && [ "$(cat "$STATES/hermes-worker.service")" = 'active' ]; then
  _pass 'C2: no service is stranded by the refusal'
else
  _fail 'C2: no service is stranded by the refusal' \
    "gateway=$(cat "$STATES/hermes-gateway.service") worker=$(cat "$STATES/hermes-worker.service")"
fi
if [ "$c2_rc" -ne 0 ]; then
  _pass 'C2: the refusal exits nonzero'
else
  _fail 'C2: the refusal exits nonzero' "rc=$c2_rc"
fi
c2_log=$(cat "$ADMIN_HOME/hermes-m04-backup.out" 2>/dev/null || true)
if [[ "$c2_log" == *'CHECK restore_service_state=PASS'* ]]; then
  _fail 'C2: no false restoration PASS is emitted' "$c2_log"
else
  _pass 'C2: no false restoration PASS is emitted'
fi

# R2/C2 control: a service that was CONCLUSIVELY inactive before the run needs no
# restoration, and that must be distinguishable from an unknown state.
reset_sandbox priorinactive
printf 'inactive\n' >"$STATES/hermes-gateway.service"
printf 'inactive\n' >"$STATES/hermes-worker.service"
priorinactive_rc=0
priorinactive_out=$(run_backup priorinactive) || priorinactive_rc=$?
assert_contains 'CHECK prior_service_state=PASS' "$priorinactive_out" \
  'C2: a conclusively inactive prior state is accepted'
assert_equals '0' "$priorinactive_rc" 'C2: a stopped-state backup of inactive services still passes'

# Restoration failure must invalidate an otherwise-successful run (R3).
reset_sandbox restorefail
STUB_START_FAIL='hermes-worker.service'
restorefail_rc=0
restorefail_out=$(run_backup restorefail) || restorefail_rc=$?
unset STUB_START_FAIL
# The restoration CHECK is appended to the helper's own log, not stdout.
restorefail_log=$(cat "$ADMIN_HOME/hermes-m04-backup.out" 2>/dev/null || true)
assert_contains 'CHECK restore_service_state=FAIL' "$restorefail_log" \
  'a failed service restoration is recorded as a FAIL check'
assert_contains 'RESTORE_FAILED' "$restorefail_out" 'a failed restoration is reported to the operator'
assert_equals '1' "$restorefail_rc" 'a failed restoration fails an otherwise-successful run'

# Both the primary run and the restoration fail: the primary failure must be
# preserved (reported first) and the restoration failure must also be visible.
reset_sandbox bothfail
STUB_TAR_CREATE_FAIL=1
STUB_START_FAIL='hermes-worker.service'
bothfail_rc=0
bothfail_out=$(run_backup bothfail) || bothfail_rc=$?
unset STUB_TAR_CREATE_FAIL STUB_START_FAIL
bothfail_log=$(cat "$ADMIN_HOME/hermes-m04-backup.out" 2>/dev/null || true)
assert_contains 'CHECK backup_archive=FAIL' "$bothfail_out" 'the primary archive failure is still reported'
assert_contains 'CHECK restore_service_state=FAIL' "$bothfail_log" \
  'the restoration failure is reported alongside the primary failure'
assert_equals '1' "$bothfail_rc" 'a run with both failures still exits nonzero'

# --- archive creation failure ----------------------------------------------
section 'm04-backup fault injection: archive creation and extraction'
reset_sandbox createfail
STUB_TAR_CREATE_FAIL=1
createfail_out=$(run_backup createfail) || true
unset STUB_TAR_CREATE_FAIL
assert_contains 'CHECK backup_archive=FAIL' "$createfail_out" 'a non-zero tar creation exit fails the archive check'

reset_sandbox extractfail
STUB_TAR_EXTRACT_FAIL=1
extractfail_out=$(run_backup extractfail) || true
unset STUB_TAR_EXTRACT_FAIL
assert_contains 'CHECK restore_extract=FAIL' "$extractfail_out" 'a non-zero tar extraction exit fails the restore check'

reset_sandbox metabreak
STUB_TAR_BREAK_META=1
STUB_BREAK_META_PATH='gateway-state/config.yaml'
metabreak_out=$(run_backup metabreak) || true
unset STUB_TAR_BREAK_META STUB_BREAK_META_PATH
assert_contains 'CHECK restore_metadata=FAIL' "$metabreak_out" 'restored metadata drift fails the metadata check'

# --- credential-free profile (Gate 2 has no .env) ---------------------------
section 'm04-backup credential-free profile'
reset_sandbox noenv
rm -f "$RUNTIME_HOME/gateway-state/.env"
noenv_out=$(run_backup noenv) || true
assert_contains 'CHECK restore_env_mode=PASS' "$noenv_out" \
  'a credential-free profile verifies the preserved absence of .env'
assert_contains 'RESULT=PASS' "$noenv_out" 'a credential-free stopped-state backup and restore passes'

# --- interrupt mechanism is library-level (documented) ----------------------
section 'm04-backup interruption wiring'
assert_grep 'mp_secure_tmpdir_var RESTORE' "$BACKUP_HELPER" \
  'the restore directory is registered in the calling shell'
assert_grep 'mp_on_cleanup restore_service_state' "$BACKUP_HELPER" \
  'service restoration is registered as a trap hook'
assert_grep 'set -u' "$BACKUP_HELPER" 'the helper runs without set -e masking failures'
lib_stub="$REPO_ROOT/scripts/hermes/manual/lib-manual-common.sh"
assert_grep 'SIGKILL cannot be trapped' "$lib_stub" 'the unavoidable SIGKILL limitation is documented'

print_summary
