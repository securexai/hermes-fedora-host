#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC1091,SC2034
# Behavioral tests for m01-host-prepare.sh temporary-state cleanup (review R6).
#
# The REAL helper is executed with stubbed host commands. Its private key
# directory is allocated in the shell that owns the EXIT/INT/TERM traps, so a
# normal end, a failed pipeline and an interruption all remove it. Allocating it
# inside the `{ ... } | tee` reporting subshell lost that registration.
#
# The run is bounded before any host configuration write: the report pipeline is
# cut immediately after the key directory exists, or the helper is signalled while
# it is parked at a stubbed `sshd -t`. No root, no service, no /etc or /home write.
#
#   ./tests/test-hermes-manual-m01-tempdir.sh [-v]

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

readonly M01="$REPO_ROOT/scripts/hermes/manual/m01-host-prepare.sh"

VERBOSE=false
[[ "${1:-}" == -v ]] && VERBOSE=true

WORK=$(mktemp -d)
readonly WORK
trap 'rm -rf -- "$WORK"' EXIT

MACHINE_HASH=$(sha256sum /etc/machine-id | cut -d' ' -f1)
readonly MACHINE_HASH
readonly TEST_ADMIN='m01-fixture-admin'

SANDBOX="$WORK/sandbox"
STUB="$SANDBOX/stub"
STATES="$SANDBOX/states"
TMPROOT="$SANDBOX/tmp"
ADMIN_HOME="$SANDBOX/admin-home"
mkdir -p "$STUB" "$STATES" "$TMPROOT" "$ADMIN_HOME"

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

# Host preparation commands are all no-ops; nothing touches the real host. The
# install stub records its targets so the test can prove the bounded run stopped
# before the first host configuration write (section 5.4 targets /etc).
for name in dnf rpm systemctl hostnamectl useradd passwd loginctl restorecon chown; do
  write_stub "$name" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
done

write_stub install <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"${STUB_INSTALL_LOG:-/dev/null}"
exec /usr/bin/install "$@"
EOF

write_stub ip <<'EOF'
#!/usr/bin/env bash
printf 'default via 10.0.0.1 dev eth0 proto static\n'
EOF

write_stub firewall-cmd <<'EOF'
#!/usr/bin/env bash
case "$*" in
  *--get-zone-of-interface=*) printf 'FedoraServer (default)\n' ;;
  *--get-default-zone*) printf 'FedoraServer\n' ;;
  *--list-services*) printf 'ssh\n' ;;
esac
exit 0
EOF

# `sshd -t` parks (when asked) after the key directory exists and before any host
# configuration write, giving the test a deterministic interruption point.
write_stub sshd <<'EOF'
#!/usr/bin/env bash
case "${1:-}" in
  -t)
    if [ -n "${STUB_SSHD_PARK:-}" ]; then
      : >"${STUB_SSHD_PARK}"
      n=0
      while [ ! -e "${STUB_SSHD_RELEASE:-/nonexistent}" ] && [ "$n" -lt 400 ]; do
        sleep 0.05
        n=$((n + 1))
      done
    fi
    ;;
  -T)
    printf 'pubkeyauthentication yes\npasswordauthentication no\nkbdinteractiveauthentication no\n'
    ;;
esac
exit 0
EOF

write_stub ausearch <<'EOF'
#!/usr/bin/env bash
printf '<no matches>\n'
exit 1
EOF

# The helper resolves `h` lazily; `sudo` never needs to translate here because no
# runtime command is reached in these bounded runs.
write_stub sudo <<'EOF'
#!/usr/bin/env bash
exit 0
EOF

leftover_tmp() { find "$TMPROOT" -mindepth 1 -maxdepth 1 -print 2>/dev/null | wc -l; }

# Start the real helper in its own process group, parked at the stubbed `sshd -t`
# (after the key directory exists, before any host configuration write). Sets the
# global M01_PID to the waitable child.
M01_PID=0
start_parked_m01() { # <label>
  local label="$1"
  local park="$SANDBOX/park.$label"
  local release="$SANDBOX/release.$label"
  rm -f "$park" "$release"
  env -i PATH="$STUB:/usr/bin:/bin" HOME="$ADMIN_HOME" \
    TEST_ADMIN="$TEST_ADMIN" TEST_HOME="$ADMIN_HOME" HERMES_ADMIN="$TEST_ADMIN" \
    MP_PROFILE_LOCK_PATH="$SANDBOX/lock" MP_HOST_IDENTITY_FILE=/nonexistent \
    HERMES_EXPECT_MACHINE_ID_SHA256="$MACHINE_HASH" \
    STUB_STATES="$STATES" TMPDIR="$TMPROOT" \
    STUB_INSTALL_LOG="$SANDBOX/install.$label.log" \
    STUB_SSHD_PARK="$park" STUB_SSHD_RELEASE="$release" \
    setsid bash "$M01" --apply >"$SANDBOX/$label.out" 2>&1 &
  M01_PID=$!
}

wait_for_park() { # <label> <pid>
  local park="$SANDBOX/park.$1"
  for _ in $(seq 1 200); do
    [ -e "$park" ] && return 0
    sleep 0.05
  done
  return 1
}

# The directly-forked report-pipeline element (the `{ ... }` subshell), which is a
# child of the helper but is not `tee`.
pipeline_child() { # <helper-pid>
  local c cmd
  for c in $(pgrep -P "$1" 2>/dev/null || true); do
    cmd=$(tr '\0' ' ' <"/proc/$c/cmdline" 2>/dev/null || true)
    case "$cmd" in *tee*) ;; *)
      printf '%s\n' "$c"
      return 0
      ;;
    esac
  done
  return 1
}

# --- structural guard: allocation must precede the tee pipeline -------------
section 'm01 cleanup ownership is structural, not incidental'
tmp_line=$(grep -n 'mp_secure_tmpdir_var keydir' "$M01" | head -n1 | cut -d: -f1 || true)
rc_line=$(grep -n '^rc=0$' "$M01" | head -n1 | cut -d: -f1 || true)
block_line=0
if [ -n "$rc_line" ]; then
  block_line=$((rc_line + 1)) # the `{` that opens the report pipeline subshell
fi
if [[ -n "$tmp_line" && "$block_line" -gt 1 && "$tmp_line" -lt "$block_line" ]]; then
  _pass 'the private key directory is registered before the tee pipeline starts'
else
  _fail 'the private key directory is registered before the tee pipeline starts' \
    "tmp=${tmp_line:-none} pipeline_block=${block_line:-none}"
fi

# --- non-signal completion: the helper runs its own tail and cleans up ------
# The report pipeline element is killed while the helper is parked, so the
# helper itself is never signalled: it finishes its normal end-of-script path
# (chown/chmod/mp_finalize) and exits, which is when its EXIT trap must remove
# the private directory. No host configuration write is reached.
section 'm01 non-signal completion removes private state'
rm -rf "$TMPROOT"
mkdir -p "$TMPROOT"
: >"$SANDBOX/install.cut.log"
start_parked_m01 cut
cut_pid=$M01_PID
if ! wait_for_park cut "$cut_pid"; then
  _fail 'the report pipeline reaches the park point' 'park marker never appeared'
  : >"$SANDBOX/release.cut"
  kill -KILL -"$cut_pid" 2>/dev/null || true
  wait "$cut_pid" 2>/dev/null || true
else
  _pass 'the report pipeline reaches the park point'
  block_pid=$(pipeline_child "$cut_pid" || true)
  if [ -n "$block_pid" ]; then
    kill -KILL "$block_pid" 2>/dev/null || true
  else
    _fail 'the report pipeline element is identified' 'no non-tee child found'
  fi
  : >"$SANDBOX/release.cut"
  cut_rc=0
  wait "$cut_pid" 2>/dev/null || cut_rc=$?
  if [ "$cut_rc" -ne 0 ] && [ "$cut_rc" -ne 143 ] && [ "$cut_rc" -ne 130 ]; then
    _pass 'the helper itself was not signalled (it completed its own path)'
  else
    _fail 'the helper itself was not signalled (it completed its own path)' "rc=$cut_rc"
  fi
  assert_equals '0' "$(leftover_tmp)" \
    'the parent EXIT trap removes the private directory on the non-signal path'
  if grep -q '/etc/' "$SANDBOX/install.cut.log" 2>/dev/null; then
    _fail 'the non-signal run stops before a host configuration write' \
      "$(grep -m1 '/etc/' "$SANDBOX/install.cut.log")"
  else
    _pass 'the non-signal run stops before a host configuration write'
  fi
fi

# --- interruption: TERM to the real helper's process group -------------------
# INT is exercised by the library-level trap test in
# tests/test-hermes-manual-review.sh; a non-interactive asynchronous job has
# SIGINT ignored on entry, so it cannot carry that path here.
section 'm01 interruption removes private state'
for signal in TERM; do
  rm -rf "$TMPROOT"
  mkdir -p "$TMPROOT"
  install_log="$SANDBOX/install.$signal.log"
  : >"$install_log"
  release="$SANDBOX/release.$signal"
  start_parked_m01 "$signal"
  m01_pid=$M01_PID
  # `$!` is the process `setsid` put into its own process group, so the signal
  # can target the whole group the way a terminal delivers Ctrl-C.
  pgid=$(ps -o pgid= -p "$m01_pid" 2>/dev/null | tr -d ' ' || true)
  if [ "$pgid" != "$m01_pid" ]; then
    _fail "$signal helper runs in its own process group" "pid=$m01_pid pgid=${pgid:-none}"
    : >"$release"
    kill -KILL "$m01_pid" 2>/dev/null || true
    wait "$m01_pid" 2>/dev/null || true
    continue
  fi
  if ! wait_for_park "$signal" "$m01_pid"; then
    _fail "$signal reaches the parked helper after the key directory exists" 'park marker never appeared'
    : >"$release"
    kill -KILL -"$m01_pid" 2>/dev/null || true
    wait "$m01_pid" 2>/dev/null || true
    continue
  fi
  _pass "$signal reaches the parked helper after the key directory exists"
  kill -"$signal" -"$m01_pid" 2>/dev/null || true
  child_rc=0
  wait "$m01_pid" 2>/dev/null || child_rc=$?
  : >"$release"
  expected_rc=143
  [[ "$signal" == INT ]] && expected_rc=130
  assert_equals "$expected_rc" "$child_rc" "$signal returns the conventional 128+signal status"
  assert_equals '0' "$(leftover_tmp)" "$signal removes the private directory"
  if grep -q '/etc/' "$install_log" 2>/dev/null; then
    _fail "$signal did not reach a host configuration write before the signal" \
      "$(grep -m1 '/etc/' "$install_log")"
  else
    _pass "$signal did not reach a host configuration write before the signal"
  fi
done

print_summary
