#!/usr/bin/env bash
# shellcheck shell=bash
# Shared safety, accounting and evidence helpers for the Hermes manual profile.
#
# Sourced by the helpers under scripts/hermes/manual/. It performs no I/O at
# source time beyond defining functions and defaults.
#
# Two design points matter:
#
#   * Most helpers build their report inside `{ ... } | tee "$OUT"`, which runs
#     the block in a SUBSHELL. In-memory counters are therefore lost. Check
#     results are printed as `CHECK <name>=<result>` lines and tallied by
#     mp_finalize() from the log file, which survives the subshell boundary.
#   * mp_finalize() returns non-zero for any FAIL and for any UNVERIFIED, so an
#     unmeasurable *required* check can never be reported as success, and a run
#     that asserts nothing at all is a failure rather than a silent pass.
#   * A gate-excluded check is recorded with mp_defer(), not mp_check UNVERIFIED.
#     Deferred checks are reported explicitly as a partial result and do not
#     block, because the gate that owns them has not run. An informational
#     diagnostic (mp_info) is never counted as evidence either way.
#
# Nothing here writes credentials to disk, prints secret values, or uses a
# predictable path under /tmp for executable content.

# Directory holding this library, so tracked sibling helpers (for example
# redact-stream.py) are resolved by path instead of being regenerated in /tmp.
if [ -z "${MP_LIB_DIR:-}" ]; then
  MP_LIB_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
  readonly MP_LIB_DIR
fi

# --------------------------------------------------------------------------
# Logging and failure
# --------------------------------------------------------------------------

mp_die() {
  printf 'STOP: %s\n' "$*" >&2
  exit 1
}

mp_note() {
  printf '%s\n' "$*"
}

# mp_new_log <path> — create the log with restrictive permissions BEFORE any
# content is written, so an aborted run cannot leave group/world-readable
# output. Prints the path.
mp_new_log() {
  local path="$1"
  [ -d "$(dirname -- "$path")" ] || mp_die "log directory does not exist: $(dirname -- "$path")"
  (
    umask 077
    : >"$path"
  ) || mp_die "cannot create $path"
  chmod 0600 -- "$path" || mp_die "cannot set mode on $path"
  printf '%s\n' "$path"
}

# --------------------------------------------------------------------------
# Structured check accounting
# --------------------------------------------------------------------------

# mp_check <name> <PASS|FAIL|UNVERIFIED|NOT_APPLICABLE> [detail]
mp_check() {
  local name="$1" result="$2" detail="${3:-}"
  printf 'CHECK %s=%s\n' "$name" "$result"
  [ -z "$detail" ] || printf 'CHECK_DETAIL %s: %s\n' "$name" "$detail"
}

# mp_expect <name> <expected> <actual> — PASS when the two strings are equal.
mp_expect() {
  local name="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    mp_check "$name" PASS
  else
    mp_check "$name" FAIL "expected '$expected', got '$actual'"
  fi
}

# mp_info <name> <detail> — informational diagnostic. It is printed for the
# operator and the evidence log but is deliberately NOT a CHECK line, so it can
# never be counted as a PASS or a failure. Use it for measurements that are
# informative but not part of the required gate.
mp_info() {
  printf 'CHECK_INFO %s: %s\n' "$1" "${2:-}"
}

# mp_defer <name> <reason> — a required check owned by a LATER gate that this
# run is not authorized or able to perform. It is reported separately and makes
# the result explicitly partial, but it never becomes a PASS and never blocks a
# gate that has been defined to exclude it.
mp_defer() {
  printf 'CHECK_DEFERRED %s: %s\n' "$1" "${2:-}"
}

# mp_finalize <log-file> <pipeline-rc> — run REQUIRED cleanup, then tally and exit.
#
# Required cleanup (the registered restoration hooks and the removal of private
# temporary state) runs BEFORE the result is published. A run whose primary work
# succeeded but whose restoration or temporary-state removal failed must not
# print an unqualified PASS: the failure is recorded as the required check
# `cleanup_required=FAIL`, which the tally below turns into a non-zero exit. An
# existing non-zero primary status is still reported first, and an interruption
# status is preserved by the trap, so a cleanup failure never masks the real
# cause of a failed run.
#
# The in-memory cleanup result is authoritative: if the evidence log cannot be
# appended to (an I/O error or a full filesystem), the FAIL line is lost but the
# run still fails, because publishing PASS here is what an operator would read as
# a successful run.
mp_finalize() {
  local out="$1" rc="${2:-0}" cleanup_failed=0 total fails unverified deferred
  if ! mp_run_cleanup; then
    cleanup_failed=1
  fi
  if [ "$cleanup_failed" -eq 1 ]; then
    # The once-only guard in mp_run_cleanup means the EXIT trap will not repeat
    # this, so appending after the pipeline has closed is the single record. The
    # append is best-effort: a failed write must not clear the in-memory failure.
    if [ -s "$out" ]; then
      if ! printf 'CHECK cleanup_required=FAIL "required cleanup (state restoration or temporary-state removal) failed"\n' >>"$out"; then
        printf 'CLEANUP_FAILED the cleanup failure could not be recorded in %s\n' "$out" >&2
      fi
    fi
    printf 'CLEANUP_FAILED required cleanup failed; the run is not reported as a pass\n' >&2
  fi
  if [ ! -s "$out" ]; then
    printf 'RESULT=FAIL (missing or empty output log: %s)\n' "$out"
    exit 1
  fi
  total=$(grep -acE '^CHECK [A-Za-z0-9_.-]+=' "$out" || true)
  fails=$(grep -acE '^CHECK [A-Za-z0-9_.-]+=FAIL' "$out" || true)
  unverified=$(grep -acE '^CHECK [A-Za-z0-9_.-]+=UNVERIFIED' "$out" || true)
  deferred=$(grep -acE '^CHECK_DEFERRED [A-Za-z0-9_.-]+:' "$out" || true)
  printf 'check_total=%s check_fail=%s check_unverified=%s check_deferred=%s\n' \
    "${total:-0}" "${fails:-0}" "${unverified:-0}" "${deferred:-0}"
  if [ "${total:-0}" -eq 0 ]; then
    printf 'RESULT=FAIL (no CHECK lines were produced; the run asserted nothing)\n'
    exit 1
  fi
  if [ "$rc" -ne 0 ]; then
    printf 'RESULT=FAIL (the output pipeline failed; rc=%s; %s may be incomplete)\n' "$rc" "$out"
    exit 1
  fi
  # The in-memory result, not the log, decides this: the FAIL append above may
  # itself have failed, and a failed cleanup must never be published as a PASS.
  if [ "$cleanup_failed" -eq 1 ]; then
    printf 'RESULT=FAIL (required cleanup failed; the run is not reported as a pass)\n'
    exit 1
  fi
  if [ "${fails:-0}" -gt 0 ]; then
    printf 'RESULT=FAIL (%s failed check(s); see the CHECK lines above)\n' "$fails"
    exit 1
  fi
  if [ "${unverified:-0}" -gt 0 ]; then
    printf 'RESULT=INCOMPLETE (%s unverified check(s); a PASS is not claimed)\n' "$unverified"
    exit 3
  fi
  if [ "${deferred:-0}" -gt 0 ]; then
    printf 'RESULT=PASS (PARTIAL: %s check(s) deferred to a later gate; no required check failed)\n' "$deferred"
    exit 0
  fi
  printf 'RESULT=PASS\n'
  exit 0
}

# --------------------------------------------------------------------------
# Mode selection: inspection is the default, mutation needs --apply
# --------------------------------------------------------------------------

MP_APPLY=0

# A helper with its own mode flags sets MP_EXTRA_FLAGS (space-separated) before
# calling mp_parse_mode, so a typo in an unrecognized option still fails closed.
# mp_parse_mode [args...] — sets MP_APPLY. Unknown options fail closed so a
# typo cannot silently grade as inspect-only or, worse, as apply.
mp_parse_mode() {
  MP_APPLY=0
  local arg
  for arg in "$@"; do
    case "$arg" in
      --apply) MP_APPLY=1 ;;
      --inspect | --dry-run) MP_APPLY=0 ;;
      --) ;;
      -*) case " ${MP_EXTRA_FLAGS:-} " in
        *" $arg "*) ;;
        *) mp_die "unknown option: $arg" ;;
      esac ;;

      *) ;; # positional paths are handled by the caller
    esac
  done
  export MP_APPLY
}

# mp_positionals [args...] — print each non-option argument on its own line.
# Lets a helper accept `--apply` in any position without confusing it for a path.
mp_positionals() {
  local arg
  for arg in "$@"; do
    case "$arg" in
      --apply | --inspect | --dry-run | --) ;;
      -*) ;;
      *) printf '%s\n' "$arg" ;;
    esac
  done
}

# mp_require_apply [message] — stop cleanly when the caller is only inspecting.
mp_require_apply() {
  local message="${1:-re-run with --apply to make this change}"
  if [ "$MP_APPLY" -eq 1 ]; then
    return 0
  fi
  printf 'INSPECT ONLY: no change made. %s\n' "$message"
  exit 0
}

# --------------------------------------------------------------------------
# Identity binding
# --------------------------------------------------------------------------

# mp_admin_account — print the administrator account NAME that owns staged
# recovery material and helper logs. Configurable through HERMES_ADMIN; a
# default here, not a Fedora requirement. Fails closed when it does not exist.
#
# mp_admin_home is the separate accessor for its home directory. Keeping the two
# apart matters: feeding a home path to `getent passwd` yields an empty string,
# which silently produced a root-level log path and an invalid chown target.
mp_admin_account() {
  local admin="${HERMES_ADMIN:-aicowork}"
  getent passwd "$admin" >/dev/null 2>&1 \
    || mp_die "administrator account '$admin' does not exist (set HERMES_ADMIN)"
  printf '%s\n' "$admin"
}

mp_admin_home() {
  local admin home
  admin=$(mp_admin_account)
  home=$(getent passwd "$admin" | cut -d: -f6)
  [ -n "$home" ] || mp_die "administrator account '$admin' has no home directory"
  printf '%s\n' "$home"
}

# mp_host_identity_sha256 — stable, non-secret host fingerprint.
mp_host_identity_sha256() {
  sha256sum /etc/machine-id 2>/dev/null | cut -d' ' -f1
}

# Root-owned pin file, used when the environment cannot carry the binding. This is
# required for sudo-driven runs: sudo resets the environment by default, so an
# env-var-only pin cannot survive `sudo bash helper.sh`. The hash of /etc/machine-id
# is not a secret, so the file is 0644 but root-owned and therefore not tamperable.
MP_HOST_IDENTITY_FILE="${MP_HOST_IDENTITY_FILE:-/etc/hermes-manual/host-identity.sha256}"

# mp_require_host_identity — mutating helpers must be bound to the reviewed
# host. Unset or mismatched means refuse; there is no "best effort" path.
mp_require_host_identity() {
  local want="${HERMES_EXPECT_MACHINE_ID_SHA256:-}" got src="environment"
  got=$(mp_host_identity_sha256)
  [ -n "$got" ] || mp_die "cannot read /etc/machine-id"
  if [ -z "$want" ] && [ -r "$MP_HOST_IDENTITY_FILE" ]; then
    want=$(tr -d '[:space:]' <"$MP_HOST_IDENTITY_FILE")
    src="$MP_HOST_IDENTITY_FILE"
  fi
  if [ -z "$want" ]; then
    mp_die "bind this run to this host first: set HERMES_EXPECT_MACHINE_ID_SHA256=$got, or have root write $got to $MP_HOST_IDENTITY_FILE"
  fi
  [ "$want" = "$got" ] || mp_die "host identity mismatch: this host is $got, the reviewed value is $want (from $src)"
  mp_check host_identity PASS "pinned via $src"
}

# mp_pin_host_identity — write the root-owned pin file. Bootstrap step, run once.
mp_pin_host_identity() {
  local got dir
  got=$(mp_host_identity_sha256)
  [ -n "$got" ] || mp_die "cannot read /etc/machine-id"
  dir=$(dirname -- "$MP_HOST_IDENTITY_FILE")
  install -d -m 0755 -- "$dir" || mp_die "cannot create $dir"
  printf '%s\n' "$got" >"$MP_HOST_IDENTITY_FILE" || mp_die "cannot write $MP_HOST_IDENTITY_FILE"
  chmod 0644 -- "$MP_HOST_IDENTITY_FILE"
  printf 'pinned host identity %s in %s\n' "$got" "$MP_HOST_IDENTITY_FILE"
}

# mp_volume_identity_ok <luks-uuid> — optional volume pin, used where a device
# path alone is ambiguous.
mp_volume_identity_ok() {
  local uuid="$1" want="${HERMES_EXPECT_UUID:-}"
  [ -n "$uuid" ] || return 1
  if [ -n "$want" ] && [ "$want" != "$uuid" ]; then
    mp_check volume_identity FAIL "got $uuid, expected $want"
    return 1
  fi
  mp_check volume_identity "${want:+PASS}${want:-UNVERIFIED}" \
    "${want:+pinned}${want:-HERMES_EXPECT_UUID is unset}"
  [ -n "$want" ]
}

# mp_require_tools <tool...> — fail before doing work when a prerequisite is
# missing, instead of misreading "tool absent" as "check failed".
mp_require_tools() {
  local missing=() tool
  for tool in "$@"; do
    command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    mp_die "missing prerequisite tool(s): ${missing[*]}"
  fi
}

# --------------------------------------------------------------------------
# Service-state interpretation
# --------------------------------------------------------------------------

# mp_capture_service_state <runner-fn> <unit> — print the unit's CONCLUSIVE state
# and return 0; print the raw value (possibly empty) and return 1 when the state
# cannot be determined. `active` is the only value that creates a restoration
# obligation; `inactive`, `dead` and `failed` are conclusively not running. A
# failed query, a transitional value (`activating`/`deactivating`/`reloading`) or
# an unexpected status is undetermined: the caller must refuse any lifecycle
# mutation rather than stop a service it may not be able to restore.
#
# The state text alone is not enough — systemctl prints a plausible value for a
# failed query too — so the normal statuses (0 for active, 3 for the rest) are
# required as well.
mp_capture_service_state() {
  local runner="$1" unit="$2" state rc=0
  state=$("$runner" systemctl --user is-active "$unit" 2>/dev/null) || rc=$?
  case "$rc" in
    0 | 3) ;;
    *)
      printf '%s\n' "${state:-}"
      return 1
      ;;
  esac
  case "$state" in
    active | inactive | dead | failed)
      printf '%s\n' "$state"
      return 0
      ;;
    *)
      printf '%s\n' "${state:-}"
      return 1
      ;;
  esac
}

# mp_container_state <runner-fn> <container> — print `running`, `stopped` or
# `unknown` and return 0/1/2. This is the authority for whether a private mount
# is live, because a unit that is not known to be active is NOT proof that its
# container has stopped.
#
#   running -> a successful `podman inspect` reports State.Running true
#   stopped -> a successful `podman ps -a` inventory does not list it, or lists
#              it with State.Running false; either way it is provably not running
#   unknown -> the inventory or the inspect failed, or reported no boolean; a
#              failed query proves nothing, so the caller must not create a
#              `:z`/`:Z` mount against a possibly-live path
mp_container_state() {
  local runner="$1" name="$2" names rc=0 running rrc=0
  names=$("$runner" podman ps -a --format '{{.Names}}' 2>/dev/null) || rc=$?
  if [ "$rc" -ne 0 ]; then
    printf 'unknown\n'
    return 2
  fi
  if ! printf '%s\n' "$names" | grep -qx -- "$name"; then
    printf 'stopped\n'
    return 1
  fi
  running=$("$runner" podman inspect --format '{{.State.Running}}' "$name" 2>/dev/null) || rrc=$?
  if [ "$rrc" -ne 0 ]; then
    printf 'unknown\n'
    return 2
  fi
  case "$running" in
    true)
      printf 'running\n'
      return 0
      ;;
    false)
      printf 'stopped\n'
      return 1
      ;;
    *)
      printf 'unknown\n'
      return 2
      ;;
  esac
}

# --------------------------------------------------------------------------
# Private temporary state
# --------------------------------------------------------------------------

MP_CLEANUP_DIRS=()
MP_SECURE_TMPDIR=""

# mp_secure_tmpdir — 0700 directory for this run. Predictable shared paths are
# never used for anything the run later executes or trusts.
#
# IMPORTANT: this registers the directory for trap-based removal, so it must run
# in the calling shell. `x=$(mp_secure_tmpdir)` runs it in a SUBSHELL and silently
# loses that registration, leaving credential copies behind when the run is
# interrupted. Call it directly and read "$MP_SECURE_TMPDIR", or use
# mp_secure_tmpdir_var, which assigns in the caller.
mp_secure_tmpdir() {
  local dir
  dir=$(mktemp -d "${TMPDIR:-/tmp}/hermes-manual.XXXXXXXX") \
    || mp_die "cannot create a private temporary directory"
  chmod 0700 -- "$dir"
  MP_CLEANUP_DIRS+=("$dir")
  MP_SECURE_TMPDIR="$dir"
  printf '%s\n' "$dir"
}

# mp_secure_tmpdir_var <varname> — create a private directory, register it for
# trap-based removal in the CALLING shell, and assign its path to <varname>.
mp_secure_tmpdir_var() {
  local __mp_name="${1:-}"
  [ -n "$__mp_name" ] || mp_die "mp_secure_tmpdir_var needs a destination variable name"
  mp_secure_tmpdir >/dev/null
  printf -v "$__mp_name" '%s' "$MP_SECURE_TMPDIR"
}

# mp_cleanup_tmpdirs — remove every registered directory. Returns non-zero when
# any removal failed, so the caller can report it instead of hiding it.
mp_cleanup_tmpdirs() {
  local dir failed=0
  for dir in "${MP_CLEANUP_DIRS[@]:-}"; do
    [ -n "$dir" ] || continue
    rm -rf -- "$dir" || failed=$((failed + 1))
  done
  MP_CLEANUP_DIRS=()
  return "$failed"
}

MP_CLEANUP_HOOKS=()
MP_CLEANUP_FAILURES=0
MP_CLEANUP_RAN=0

# mp_on_cleanup <function> — register a restoration/cleanup hook, run on EXIT,
# INT and TERM. Hooks must be idempotent (they may run once explicitly and again
# from the trap), must not call exit, and should return non-zero when
# restoration fails so the failure is reported. Restoring prior service state is
# a hook, not an after-the-pipeline statement, precisely so an early `exit`,
# an INT, or a TERM still reaches it.
mp_on_cleanup() {
  [ -n "${1:-}" ] || mp_die "mp_on_cleanup needs a function name"
  MP_CLEANUP_HOOKS+=("$1")
}

# mp_run_cleanup — run registered hooks, then remove private directories, and
# report any failure. Returns non-zero when a hook or a directory removal failed,
# so a caller that inspects the status can see it; mp_install_trap still preserves
# the run's primary exit status. It runs at most once per shell: a TERM trap that
# calls exit re-enters through the EXIT trap, and hooks must not run twice.
mp_run_cleanup() {
  local hook
  [ "${MP_CLEANUP_RAN:-0}" -eq 1 ] && return 0
  MP_CLEANUP_RAN=1
  for hook in "${MP_CLEANUP_HOOKS[@]:-}"; do
    [ -n "$hook" ] || continue
    if ! "$hook"; then
      printf 'CLEANUP_FAILED hook=%s (the primary status is preserved)\n' "$hook" >&2
      MP_CLEANUP_FAILURES=$((MP_CLEANUP_FAILURES + 1))
    fi
  done
  if ! mp_cleanup_tmpdirs; then
    printf 'CLEANUP_FAILED private temporary state could not be fully removed\n' >&2
    MP_CLEANUP_FAILURES=$((MP_CLEANUP_FAILURES + 1))
  fi
  [ "$MP_CLEANUP_FAILURES" -eq 0 ] || return 1
  return 0
}

# mp_install_trap — run cleanup on exit and on the usual interruption signals,
# preserving the original exit status for a normal exit and returning the
# conventional 128+signal status (130 for INT, 143 for TERM) for an interruption,
# so a wrapper or CI step can tell an interrupted run from a successful one.
# SIGKILL cannot be trapped: a killed run can leave its 0700 temporary directory
# (and any restored credential copy in it) on disk. That is an unavoidable
# limitation; the directory is private to the run, and the next helper run
# creates a fresh one.
mp_install_trap() {
  trap 'rc=$?; mp_run_cleanup; exit "$rc"' EXIT
  trap 'mp_run_cleanup; exit 130' INT
  trap 'mp_run_cleanup; exit 143' TERM
}

# --------------------------------------------------------------------------
# Single-writer operation lock
# --------------------------------------------------------------------------

MP_LOCK_FD=""

# Every helper that mutates the same profile takes THIS lock. Phase-specific lock
# files (m02-, m03-, m04-) did not serialize the profile: m02 and m03 could run at
# the same time and interleave Quadlet, trust-material and service changes. The
# path is overridable only so tests can point it at a sandbox.
MP_PROFILE_LOCK_PATH="${MP_PROFILE_LOCK_PATH:-/run/lock/hermes-manual-profile.lock}"

# mp_lock <path> [wait-seconds] — refuse concurrent mutation of the same profile.
mp_lock() {
  local path="$1" wait_seconds="${2:-0}"
  install -d -m 0755 -- "$(dirname -- "$path")"
  exec {MP_LOCK_FD}>>"$path" || mp_die "cannot open lock $path"
  if [ "$wait_seconds" -gt 0 ]; then
    flock -w "$wait_seconds" "$MP_LOCK_FD" \
      || mp_die "another Hermes manual operation holds $path"
  else
    flock -n "$MP_LOCK_FD" \
      || mp_die "another Hermes manual operation holds $path (concurrent execution refused)"
  fi
}

# mp_lock_profile [wait-seconds] — the one lock every profile-mutating helper
# uses, including credential and configuration operations, so two different
# helpers can never mutate the same profile concurrently.
mp_lock_profile() {
  mp_lock "$MP_PROFILE_LOCK_PATH" "${1:-0}"
}

# --------------------------------------------------------------------------
# Audit-log interpretation (SELinux AVC denials)
# --------------------------------------------------------------------------

# mp_audit_avc_check <check-name> [since] — one interpretation of ausearch for
# every helper, so a clean host is never reported UNVERIFIED and a read error is
# never reported as clean.
#
#   ausearch absent                     -> UNVERIFIED (tool missing)
#   "<no matches>" in the output        -> PASS, clean readable log; ausearch
#                                          exits NON-ZERO for this, which is why
#                                          the rc alone must never be trusted
#   rc 0 with AVC/USER_AVC records      -> FAIL, denials were recorded
#   rc 0 with no denial records         -> PASS, nothing to report
#   any other non-zero rc               -> UNVERIFIED, the log could not be read
mp_audit_avc_check() {
  local name="${1:-avc_denials}" since="${2:-recent}" out rc
  if ! command -v ausearch >/dev/null 2>&1; then
    mp_check "$name" UNVERIFIED "ausearch is not installed"
    return 0
  fi
  out=$(ausearch -m AVC,USER_AVC -ts "$since" 2>&1)
  rc=$?
  printf '%s\n' "$out" | tail -n 20
  if printf '%s' "$out" | grep -qF -- '<no matches>'; then
    mp_check "$name" PASS "clean readable audit log: no AVC or USER_AVC denials recorded"
  elif [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -qE 'type=(AVC|USER_AVC)'; then
    mp_check "$name" FAIL "AVC or USER_AVC denials were recorded during this run"
  elif [ "$rc" -eq 0 ]; then
    mp_check "$name" PASS "ausearch returned no denial records"
  else
    mp_check "$name" UNVERIFIED "ausearch could not read the audit log (rc=$rc)"
  fi
}

# --------------------------------------------------------------------------
# Egress-probe interpretation
# --------------------------------------------------------------------------

# mp_classify_egress <rc> <output> — turn one bounded probe into a single
# verdict, so a missing tool is never mistaken for isolation:
#
#   EGRESS_SUCCESS    the probe completed and reached the network  -> isolation broken
#   EGRESS_DENIED     the network refused/unreachable              -> expected for a network-less worker
#   DNS_FAILURE       host name could not be resolved
#   PROBE_TIMEOUT     the probe was killed by its own bound        -> inconclusive
#   PROBE_UNAVAILABLE the probe command does not exist             -> inconclusive
#   PROBE_ERROR       anything else                                -> inconclusive
mp_classify_egress() {
  local rc="${1:-1}" out="${2:-}"
  case "$out" in
    *"command not found"* | *"not found"* | *"executable file not found"* | *"No such file or directory"*)
      printf 'PROBE_UNAVAILABLE\n'
      return 0
      ;;
  esac
  case "$rc" in
    0) printf 'EGRESS_SUCCESS\n' ;;
    6) printf 'DNS_FAILURE\n' ;;
    28) printf 'PROBE_TIMEOUT\n' ;;
    7 | 101 | 113)
      case "$out" in
        *"Could not resolve"*) printf 'DNS_FAILURE\n' ;;
        *) printf 'EGRESS_DENIED\n' ;;
      esac
      ;;
    127) printf 'PROBE_UNAVAILABLE\n' ;;
    *)
      case "$out" in
        *"Network is unreachable"* | *"Network unreachable"* | *"Connection refused"* | \
          *"Failed to connect"* | *"Could not resolve"* | *"No route to host"*)
          printf 'EGRESS_DENIED\n'
          ;;
        *"timed out"* | *"Timeout"* | *"timeout"*) printf 'PROBE_TIMEOUT\n' ;;
        *) printf 'PROBE_ERROR\n' ;;
      esac
      ;;
  esac
}

# mp_classify_dns <rc> <output> — interpret one bounded name-resolution probe, so
# a missing resolver or a timed-out query is never graded as isolation:
#
#   DNS_RESOLVED      a name resolved (isolation is broken)
#   DNS_UNRESOLVED    definitive "not found" (the expected denied case)
#   DNS_TIMEOUT       the query was killed by its bound (inconclusive)
#   PROBE_UNAVAILABLE the resolver command does not exist (inconclusive)
#   PROBE_ERROR       the query failed for another reason (inconclusive)
mp_classify_dns() {
  local rc="${1:-1}" out="${2:-}"
  case "$out" in
    *"command not found"* | *"not found"* | *"No such file or directory"*)
      printf 'PROBE_UNAVAILABLE\n'
      return 0
      ;;
  esac
  case "$rc" in
    0) printf 'DNS_RESOLVED\n' ;;
    2) printf 'DNS_UNRESOLVED\n' ;;
    124 | 137) printf 'DNS_TIMEOUT\n' ;;
    127) printf 'PROBE_UNAVAILABLE\n' ;;
    *) printf 'PROBE_ERROR\n' ;;
  esac
}

# --------------------------------------------------------------------------
# Convergence helpers (avoid needless writes, rebuilds and restarts)
# --------------------------------------------------------------------------

# mp_content_differs <dest> <candidate> — true (0) when dest is missing or its
# bytes differ from candidate. Used to skip an install/write that would only
# change timestamps.
mp_content_differs() {
  local dest="$1" candidate="$2"
  [ -f "$dest" ] || return 0
  cmp -s -- "$dest" "$candidate" && return 1
  return 0
}

# mp_stamp_matches <stamp-file> <value> — true when the recorded value already
# equals the current one, so an expensive rebuild can be skipped.
mp_stamp_matches() {
  local stamp_file="$1" value="$2"
  [ -f "$stamp_file" ] || return 1
  [ "$(tr -d '[:space:]' <"$stamp_file" 2>/dev/null)" = "$value" ]
}

# mp_write_stamp <stamp-file> <value> — record a convergence stamp atomically.
mp_write_stamp() {
  local stamp_file="$1" value="$2" tmp
  tmp="${stamp_file}.new.$$"
  printf '%s\n' "$value" >"$tmp" && mv -f -- "$tmp" "$stamp_file"
}

# mp_should_rebuild <stamp-file> <input-hash> <image-exists 0|1> — true (0) when
# an image build is actually needed. A matching stamp with an existing image is
# convergent: an ordinary re-run must not rebuild.
mp_should_rebuild() {
  local stamp_file="$1" value="$2" image_exists="${3:-0}"
  [ "$image_exists" = "1" ] || return 0
  mp_stamp_matches "$stamp_file" "$value" && return 1
  return 0
}

# mp_install_if_changed <mode> <owner:group|-> <src> <dest> — install a file only
# when its content differs, and ALWAYS reconcile the required mode and ownership,
# so a drifted permission cannot survive a converged re-run. Returns non-zero
# when the install or the reconcile fails, so the caller can propagate it.
# Prints "CHANGED <dest>" or "UNCHANGED <dest>".
mp_install_if_changed() {
  local mode="$1" owner="$2" src="$3" dest="$4" changed=0 current current_mode
  if [ ! -f "$dest" ] || ! cmp -s -- "$src" "$dest"; then
    if [ "$owner" = "-" ]; then
      install -m "$mode" "$src" "$dest" || return 1
    else
      install -o "${owner%%:*}" -g "${owner##*:}" -m "$mode" "$src" "$dest" || return 1
    fi
    changed=1
  else
    # Reconcile metadata only when it genuinely differs, so a fully converged
    # re-run does not churn ctime on a file whose mode and owner are correct.
    current_mode=$(stat -c '%a' -- "$dest" 2>/dev/null || true)
    if [ "$((10#${current_mode:-0}))" != "$((10#$mode))" ]; then
      chmod "$mode" -- "$dest" || return 1
    fi
    if [ "$owner" != "-" ]; then
      current=$(stat -c '%U:%G' -- "$dest" 2>/dev/null || true)
      if [ "$current" != "$owner" ]; then
        chown "${owner%%:*}:${owner##*:}" -- "$dest" || return 1
      fi
    fi
  fi
  if [ "$changed" -eq 1 ]; then
    printf 'CHANGED %s\n' "$dest"
  else
    printf 'UNCHANGED %s\n' "$dest"
  fi
  return 0
}

# mp_install_reconcile <check-name> <mode> <owner:group|-> <src> <dest> —
# mp_install_if_changed plus a CHECK line, returning the install status so a
# caller can fail the run instead of reporting a converged profile that is not.
mp_install_reconcile() {
  local name="$1" mode="$2" owner="$3" src="$4" dest="$5" out rc
  out=$(mp_install_if_changed "$mode" "$owner" "$src" "$dest")
  rc=$?
  [ -n "$out" ] && printf '%s\n' "$out"
  if [ "$rc" -eq 0 ]; then
    mp_check "$name" PASS "$out"
  else
    mp_check "$name" FAIL "install or ownership/mode reconcile failed for $dest"
  fi
  return "$rc"
}

# --------------------------------------------------------------------------
# Secret-safe output
# --------------------------------------------------------------------------

# mp_redact_stream <env-file> — filter stdin through the tracked
# redact-stream.py helper. No temporary executable is created, and a missing
# env file degrades to pass-through rather than failing the pipeline.
mp_redact_stream() {
  python3 "$MP_LIB_DIR/redact-stream.py" "${1:-}"
}

# mp_sha256 <path> — short, stable identity string for evidence.
mp_sha256() {
  sha256sum -- "$1" 2>/dev/null | cut -d' ' -f1
}
