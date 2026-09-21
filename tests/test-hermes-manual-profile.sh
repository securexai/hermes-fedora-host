#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC1091,SC2034
# Offline checks for the Hermes manual profile (two rootless Podman containers,
# a pinned upstream gateway and an offline worker).
#
# These checks never run as root, never start a container, never contact a
# target, and never read a credential store. They assert that the repository
# artifacts encode the approved posture and that the helpers fail closed.
#
#   ./tests/test-hermes-manual-profile.sh [-v]

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
readonly CONTRACT="$MANUAL/config/profile-contract.yaml"
readonly HARDEN="$MANUAL/config/harden-config.py"
readonly MANIFEST="$MANUAL/manifest.yaml"
readonly PLAN="$REPO_ROOT/docs/plans/2026-09-20-hermes-manual-profile-improvement.md"
readonly CONTRACT_DOC="$REPO_ROOT/docs/HERMES_MANUAL_PROFILE_CONTRACT.md"
readonly CONTRIBUTING="$REPO_ROOT/docs/CONTRIBUTING.md"
readonly README="$REPO_ROOT/README.md"

VERBOSE=false
[[ "${1:-}" == -v ]] && VERBOSE=true

export LIB

# Helpers that must default to inspection and require --apply to change a host.
readonly INSPECT_HELPERS=(
  m00-pin-host-identity.sh
  m01-host-prepare.sh
  m02-deploy-and-validate.sh
  m03-activate.sh
  m03-configure-and-probe.sh
  m03-contract.sh
  m04-posture.sh
  m04-backup.sh
  m04-readonly-gateway.sh
  m04-reboot.sh
  m05-fix-and-activate.sh
  m05-telegram.sh
  m05-tests.sh
  boot/tpm-enroll.sh
  boot/fallback-wipe.sh
)

# Helpers that must be bound to the reviewed host before they change anything.
readonly IDENTITY_HELPERS=(
  m01-host-prepare.sh
  m02-deploy-and-validate.sh
  m03-activate.sh
  m03-configure-and-probe.sh
  m03-contract.sh
  m04-posture.sh
  m04-backup.sh
  m04-readonly-gateway.sh
  m04-reboot.sh
  m05-fix-and-activate.sh
  m05-telegram.sh
  m05-tests.sh
  provision-openai-key.sh
  provision-telegram.sh
  provision-worker-client-key.sh
  boot/tpm-enroll.sh
  boot/fallback-wipe.sh
)

manual_shell_artifacts() {
  printf '%s\n' \
    "$MANUAL"/*.sh \
    "$MANUAL"/boot/*.sh \
    "$MANUAL"/lab/*.sh \
    "$MANUAL"/gateway/ssh \
    "$MANUAL"/gateway/scp \
    "$MANUAL"/gateway/sftp \
    "$MANUAL"/worker/worker-entrypoint \
    "$MANUAL"/worker/worker-socket-adapter \
    "$MANUAL"/worker/worker-sshd-inetd
}

# Run a snippet with the library sourced. Snippets must not touch the network.
lib_snippet() {
  local code="$1"
  shift
  bash -c "source \"\$LIB\"; $code" _ "$@"
}

run_finalize() { # <log> <rc> -> prints the exit status
  local status=0
  lib_snippet 'mp_finalize "$1" "$2"' "$1" "$2" >/dev/null 2>&1 || status=$?
  printf '%s\n' "$status"
}

TMPDIR_TEST=$(mktemp -d)
readonly TMPDIR_TEST
trap 'rm -rf -- "$TMPDIR_TEST"' EXIT

# ---------------------------------------------------------------- inventory
section 'Manual-profile artifacts'

readonly REDACT_HELPER="$MANUAL/redact-stream.py"

for required in "$LIB" "$REDACT_HELPER" "$CONTRACT" "$HARDEN" "$MANIFEST" "$PLAN" "$CONTRACT_DOC"; do
  if [[ -f "$required" ]]; then
    _pass "artifact exists: ${required#"$REPO_ROOT"/}"
  else
    _fail "artifact exists: ${required#"$REPO_ROOT"/}"
  fi
done

# ------------------------------------------------------------------- syntax
section 'Shell and Python syntax'

shell_count=0
while IFS= read -r script; do
  shell_count=$((shell_count + 1))
  if bash -n "$script" 2>/dev/null; then
    _pass "bash syntax: ${script#"$MANUAL"/}"
  else
    _fail "bash syntax: ${script#"$MANUAL"/}" "$(bash -n "$script" 2>&1 | head -n 1)"
  fi
done < <(manual_shell_artifacts)
assert_min_count 25 "$shell_count" 'manual shell artifacts were enumerated'

python_count=0
for source in "$MANUAL"/*.py "$MANUAL"/config/*.py "$MANUAL"/gateway/*.py; do
  python_count=$((python_count + 1))
  if python3 -c 'import ast, sys; ast.parse(open(sys.argv[1], encoding="utf-8").read())' "$source" 2>/dev/null; then
    _pass "python syntax: ${source#"$MANUAL"/}"
  else
    _fail "python syntax: ${source#"$MANUAL"/}"
  fi
done
assert_min_count 5 "$python_count" 'manual Python artifacts were enumerated'

# ------------------------------------------------------------ safety library
section 'Shared safety library behaviour'

log_pass="$TMPDIR_TEST/pass.log"
{
  lib_snippet 'mp_check a PASS; mp_check b PASS' >"$log_pass"
} 2>/dev/null || true
assert_equals '0' "$(run_finalize "$log_pass" 0)" 'all-PASS log finalizes successfully'

log_fail="$TMPDIR_TEST/fail.log"
lib_snippet 'mp_check a PASS; mp_check b FAIL "boom"' >"$log_fail"
assert_equals '1' "$(run_finalize "$log_fail" 0)" 'a FAIL check blocks the run'

log_unverified="$TMPDIR_TEST/unverified.log"
lib_snippet 'mp_check a PASS; mp_check b UNVERIFIED "not measurable"' >"$log_unverified"
assert_equals '3' "$(run_finalize "$log_unverified" 0)" 'an UNVERIFIED check is never a pass'

log_empty="$TMPDIR_TEST/empty.log"
printf 'no assertions here\n' >"$log_empty"
assert_equals '1' "$(run_finalize "$log_empty" 0)" 'a run that asserts nothing fails'

log_rc="$TMPDIR_TEST/rc.log"
lib_snippet 'mp_check a PASS' >"$log_rc"
assert_equals '1' "$(run_finalize "$log_rc" 7)" 'a failed output pipeline fails the run'

assert_equals '1' "$(run_finalize "$TMPDIR_TEST/missing.log" 0)" 'a missing log file fails the run'

# mp_secure_tmpdir: private directory, cleaned up by the caller.
secure_dir=$(lib_snippet 'mp_secure_tmpdir')
if [[ -d "$secure_dir" && "$(stat -c %a "$secure_dir")" == '700' ]]; then
  _pass 'mp_secure_tmpdir creates a 0700 directory'
else
  _fail 'mp_secure_tmpdir creates a 0700 directory' "got '$secure_dir' mode '$(stat -c %a "$secure_dir" 2>/dev/null)'"
fi
rm -rf -- "$secure_dir"

# mp_parse_mode: inspection is the default, --apply is explicit, typos fail closed.
assert_equals '0' "$(lib_snippet 'mp_parse_mode; printf "%s" "$MP_APPLY"')" \
  'mutating mode defaults to inspection'
assert_equals '1' "$(lib_snippet 'mp_parse_mode --apply; printf "%s" "$MP_APPLY"')" \
  '--apply selects mutation'
if lib_snippet 'mp_parse_mode --aply' >/dev/null 2>&1; then
  _fail 'an unknown option is refused'
else
  _pass 'an unknown option is refused'
fi

# mp_require_apply: stops cleanly while inspecting.
inspect_status=0
lib_snippet 'mp_require_apply' >/dev/null 2>&1 || inspect_status=$?
assert_equals '0' "$inspect_status" 'inspection exits successfully without mutating'
apply_status=0
lib_snippet 'MP_APPLY=1; mp_require_apply; printf ok' >/dev/null 2>&1 || apply_status=$?
assert_equals '0' "$apply_status" 'apply mode proceeds past the inspect guard'

# Host identity binding.
expected_hash=$(sha256sum /etc/machine-id | cut -d' ' -f1)
assert_contains "$expected_hash" "$(lib_snippet 'mp_host_identity_sha256')" 'host fingerprint is the machine-id hash'
# Hermetic: point the pin-file fallback at a non-existent path so the env-var
# assertion does not depend on whether this host has a pin file.
if MP_HOST_IDENTITY_FILE=/nonexistent/hermes-identity lib_snippet 'mp_require_host_identity' >/dev/null 2>&1; then
  _fail 'an unbound host identity is refused'
else
  _pass 'an unbound host identity is refused'
fi
pin_file="$TMPDIR_TEST/host-identity.sha256"
printf '%s\n' "$expected_hash" >"$pin_file"
if MP_HOST_IDENTITY_FILE="$pin_file" lib_snippet 'mp_require_host_identity' >/dev/null 2>&1; then
  _pass 'a root-owned pin file satisfies the host binding without environment variables'
else
  _fail 'a root-owned pin file satisfies the host binding without environment variables'
fi
printf '%s\n' 0000000000000000000000000000000000000000000000000000000000000000 >"$pin_file"
if MP_HOST_IDENTITY_FILE="$pin_file" lib_snippet 'mp_require_host_identity' >/dev/null 2>&1; then
  _fail 'a wrong pin file is refused'
else
  _pass 'a wrong pin file is refused'
fi
if HERMES_EXPECT_MACHINE_ID_SHA256="$expected_hash" lib_snippet 'mp_require_host_identity' >/dev/null 2>&1; then
  _pass 'a matching host identity is accepted'
else
  _fail 'a matching host identity is accepted'
fi
if HERMES_EXPECT_MACHINE_ID_SHA256=0000000000000000000000000000000000000000000000000000000000000000 \
  lib_snippet 'mp_require_host_identity' >/dev/null 2>&1; then
  _fail 'a mismatched host identity is refused'
else
  _pass 'a mismatched host identity is refused'
fi

# Administrator account resolution is configurable, not hardcoded.
assert_equals 'root' "$(HERMES_ADMIN=root lib_snippet 'mp_admin_account')" \
  'HERMES_ADMIN selects the administrator account name'
assert_equals '/root' "$(HERMES_ADMIN=root lib_snippet 'mp_admin_home')" \
  'mp_admin_home resolves the configured account home'
if [ "$(HERMES_ADMIN=root lib_snippet 'mp_admin_account')" = "$(HERMES_ADMIN=root lib_snippet 'mp_admin_home')" ]; then
  _fail 'the account name and its home are distinct values'
else
  _pass 'the account name and its home are distinct values'
fi
if lib_snippet 'HERMES_ADMIN=hermes-manual-no-such-account mp_admin_account' >/dev/null 2>&1; then
  _fail 'a missing administrator account is refused'
else
  _pass 'a missing administrator account is refused'
fi

# Secret-safe redaction: no helper file, long values replaced, noise untouched.
# The fake credential is assembled at runtime rather than written as a literal, so this
# test does not itself look like a leaked key to the repository's secret scanner.
env_fixture="$TMPDIR_TEST/redact.env"
fake_key="sk-$(printf 'a%.0s' $(seq 1 24))"
{
  printf 'OPENAI_API_KEY=%s\n' "$fake_key"
  printf 'SHORT=x\n'
} >"$env_fixture"
redacted=$(printf 'key=%s short=x\n' "$fake_key" | lib_snippet 'mp_redact_stream "$1"' "$env_fixture")
assert_contains '[REDACTED]' "$redacted" 'redaction replaces a known secret value'
assert_contains 'short=x' "$redacted" 'redaction leaves short non-secret values intact'
if printf 'key=%s\n' "$fake_key" | lib_snippet 'mp_redact_stream "$1"' "$env_fixture" | grep -qF "$fake_key"; then
  _fail 'redaction output contains no raw secret'
else
  _pass 'redaction output contains no raw secret'
fi

# Operation lock: a second writer is refused while the first holds the lock.
lock_path="$TMPDIR_TEST/operation.lock"
lib_snippet 'mp_lock "$1"; sleep 3' "$lock_path" &
lock_holder=$!
sleep 0.5
if lib_snippet 'mp_lock "$1"' "$lock_path" >/dev/null 2>&1; then
  _fail 'a concurrent operation is refused'
else
  _pass 'a concurrent operation is refused'
fi
kill "$lock_holder" 2>/dev/null || true
wait "$lock_holder" 2>/dev/null || true

# ------------------------------------------------- temporary-file discipline
section 'No predictable temporary executables'

for script in $(manual_shell_artifacts); do
  name=${script#"$MANUAL"/}
  assert_no_grep 'cat[[:space:]]*>[[:space:]]*/tmp/' "$script" "$name writes no predictable /tmp helper"
  assert_no_grep '/tmp/[A-Za-z0-9_.-]+\.py' "$script" "$name executes no /tmp Python helper"
done

# Standalone and library artifacts are deliberately not required to source the
# shared library: the libraries themselves, the SSH helper the guide copies on
# its own, the workstation-side static rehearsal, and the legacy TPM helper the
# preparation guide excludes from use.
readonly LIB_EXEMPT='lib-manual-common.sh boot/lib-luks-identity.sh setup-ssh-key-only.sh configure-tpm2-auto-unlock.sh boot/rehearse-clean-install.sh lab/gate2-create-fixture.sh'

for script in "$MANUAL"/*.sh "$MANUAL"/boot/*.sh; do
  name=${script#"$MANUAL"/}
  exempt=false
  for allowed in $LIB_EXEMPT; do
    [[ "$name" == "$allowed" ]] && exempt=true
  done
  $exempt && continue
  assert_grep 'source .*lib-manual-common\.sh|\. .*lib-manual-common\.sh' "$script" \
    "$name sources the shared safety library"
done

# ------------------------------------------------------- failure propagation
section 'Failure propagation through tee'

tee_scripts=0
for script in "$MANUAL"/*.sh "$MANUAL"/boot/*.sh; do
  code=$(grep -vE '^[[:space:]]*#' "$script" || true)
  grep -qE '\|[[:space:]]*tee' <<<"$code" || continue
  tee_scripts=$((tee_scripts + 1))
  name=${script#"$MANUAL"/}
  assert_grep 'pipefail' "$script" "$name uses pipefail with tee"
  if grep -qE 'tee[^|]*\|\|[[:space:]]*rc=' <<<"$code" || grep -q 'mp_finalize' "$script"; then
    _pass "$name captures the pipeline status"
  else
    _fail "$name captures the pipeline status" 'tee masks the block exit status'
  fi
done
assert_min_count 8 "$tee_scripts" 'tee-using helpers were enumerated'

# --------------------------------------------------------- inspect by default
section 'Mutation is explicit'

for name in "${INSPECT_HELPERS[@]}"; do
  script="$MANUAL/$name"
  assert_grep 'mp_parse_mode' "$script" "$name parses an explicit mode"
  assert_grep 'mp_require_apply' "$script" "$name refuses to mutate while inspecting"
done

for name in "${IDENTITY_HELPERS[@]}"; do
  script="$MANUAL/$name"
  assert_grep 'mp_require_host_identity' "$script" "$name is bound to the reviewed host"
done

# ------------------------------------------------------------ configuration
section 'Configuration contract'

contract_data="$TMPDIR_TEST/contract"
mkdir -p "$contract_data"
cat >"$contract_data/config.yaml" <<'YAML'
agent:
  custom_operator_key: keep-me
_config_version: 11
terminal:
  backend: local
YAML
printf 'OPENAI_API_KEY=sk-synthetic-not-a-real-key\nUNRELATED_SETTING=keep\n' >"$contract_data/.env"

HERMES_DATA_DIR="$contract_data" python3 "$HARDEN" >/dev/null

if python3 - "$CONTRACT" "$contract_data/config.yaml" <<'PY'; then
import sys
import yaml

contract = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
produced = yaml.safe_load(open(sys.argv[2], encoding="utf-8"))
problems = []


def compare(path, want, got):
    if isinstance(want, dict):
        if not isinstance(got, dict):
            problems.append(f"{path}: expected a mapping, got {type(got).__name__}")
            return
        for key, value in want.items():
            if key not in got:
                problems.append(f"{path}.{key}: missing")
            else:
                compare(f"{path}.{key}", value, got[key])
    elif want != got:
        problems.append(f"{path}: expected {want!r}, got {got!r}")


compare("config", contract["config"], produced)
if produced.get("agent", {}).get("custom_operator_key") != "keep-me":
    problems.append("config.agent.custom_operator_key was not preserved")
if produced.get("_config_version") != 11:
    problems.append("config._config_version was modified instead of preserved")
if produced.get("manual_profile", {}).get("contract_version") != 1:
    problems.append("config.manual_profile.contract_version is missing")
if "tools" in produced:
    problems.append("config.tools is not a real Hermes key; the allowlist must be written as toolsets/platform_toolsets")
narrow = ["terminal", "file", "memory", "clarify"]
if produced.get("toolsets") != narrow:
    problems.append(f"config.toolsets is {produced.get('toolsets')!r}, expected {narrow!r}")
for platform in ("cli", "telegram"):
    if (produced.get("platform_toolsets") or {}).get(platform) != narrow:
        problems.append(f"config.platform_toolsets.{platform} is not the narrow allowlist")
for line in problems:
    print(f"MISMATCH {line}")
sys.exit(1 if problems else 0)
PY
  _pass 'the contract is applied without losing operator keys'
else
  _fail 'the contract is applied without losing operator keys' 'see MISMATCH lines above'
fi

for key in API_SERVER_ENABLED HERMES_DASHBOARD GATEWAY_ALLOW_ALL_USERS WEBHOOK_ENABLED; do
  assert_grep "^${key}=" "$contract_data/.env" "env allowlist sets $key"
done
assert_grep '^UNRELATED_SETTING=keep' "$contract_data/.env" 'unrelated env entries are preserved'
assert_grep '^OPENAI_API_KEY=sk-synthetic-not-a-real-key' "$contract_data/.env" \
  'existing secret values are not rewritten'

fresh_data="$TMPDIR_TEST/fresh"
mkdir -p "$fresh_data"
HERMES_DATA_DIR="$fresh_data" python3 "$HARDEN" >/dev/null
assert_no_grep '^_config_version:' "$fresh_data/config.yaml" 'no schema version is invented'

cp "$contract_data/config.yaml" "$TMPDIR_TEST/first-run.yaml"
HERMES_DATA_DIR="$contract_data" python3 "$HARDEN" >/dev/null
if python3 - "$TMPDIR_TEST/first-run.yaml" "$contract_data/config.yaml" <<'PY'; then
import sys
import yaml

first = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
second = yaml.safe_load(open(sys.argv[2], encoding="utf-8"))
for doc in (first, second):
    doc.get("manual_profile", {}).pop("applied_utc", None)
sys.exit(0 if first == second else 1)
PY
  _pass 'reapplying the contract is idempotent'
else
  _fail 'reapplying the contract is idempotent'
fi

bad_data="$TMPDIR_TEST/bad"
mkdir -p "$bad_data"
printf 'model: [unclosed\n' >"$bad_data/config.yaml"
if HERMES_DATA_DIR="$bad_data" python3 "$HARDEN" >/dev/null 2>&1; then
  _fail 'a malformed config.yaml is refused'
else
  _pass 'a malformed config.yaml is refused'
fi
assert_equals 'model: [unclosed' "$(cat "$bad_data/config.yaml")" 'a malformed config is left untouched'

# ------------------------------------------------------------ release identity
section 'Release identity'

gateway_ref=$(python3 -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))["images"]["gateway"]["ref"])' "$MANIFEST")
worker_ref=$(python3 -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))["images"]["worker"]["ref"])' "$MANIFEST")
worker_base=$(python3 -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))["images"]["worker"]["base"])' "$MANIFEST")

assert_contains '@sha256:' "$gateway_ref" 'the gateway pin is digest-qualified'
assert_equals "$gateway_ref" \
  "$(grep -m1 '^Image=' "$MANUAL/quadlets/hermes-gateway.container" | cut -d= -f2-)" \
  'the gateway Quadlet uses the manifested digest'
assert_equals "$worker_ref" \
  "$(grep -m1 '^Image=' "$MANUAL/quadlets/hermes-worker.container" | cut -d= -f2-)" \
  'the worker Quadlet uses the manifested artifact'
assert_equals "$worker_base" \
  "$(grep -m1 '^FROM ' "$MANUAL/worker/Containerfile" | awk '{print $2}')" \
  'the worker build pins the manifested base digest'
assert_no_grep ':latest' "$MANUAL/quadlets/hermes-gateway.container" 'the gateway Quadlet has no floating tag'
assert_no_grep ':latest' "$MANUAL/quadlets/hermes-worker.container" 'the worker Quadlet has no floating tag'
assert_grep 'tag_signed: false' "$MANIFEST" 'the manifest records that the upstream tag is unsigned'

# ------------------------------------------------------------- transport trust
section 'Transport trust policy'

for shim in "$MANUAL"/gateway/ssh "$MANUAL"/gateway/scp "$MANUAL"/gateway/sftp; do
  name=${shim#"$MANUAL"/}
  assert_grep 'StrictHostKeyChecking=yes' "$shim" "$name pins the worker host key"
  assert_grep 'IdentitiesOnly=yes' "$shim" "$name selects only the pinned identity"
  assert_grep 'GlobalKnownHostsFile=/dev/null' "$shim" "$name ignores ambient known_hosts"
  assert_grep 'HERMES_GATEWAY_SSH_DIR' "$shim" "$name allows a disposable base directory"
  assert_no_grep '/tmp/' "$shim" "$name uses no predictable temporary path"
done

assert_no_grep '^[[:space:]]*AcceptEnv' "$MANUAL/worker/sshd_worker_config" \
  'the worker sshd accepts no client environment'
assert_grep 'AuthenticationMethods publickey' "$MANUAL/worker/sshd_worker_config" \
  'the worker sshd requires public-key authentication'
# Comment-insensitive: the shim's own header explains the backend flag it defeats.
shim_code=$(grep -vE '^[[:space:]]*#' "$MANUAL/gateway/ssh" || true)
if grep -q 'StrictHostKeyChecking=accept-new' <<<"$shim_code"; then
  _fail 'the shim never accepts an unknown host key'
else
  _pass 'the shim never accepts an unknown host key'
fi

# --------------------------------------------- inspection needs no privileges
section 'Inspection is privilege-free'

# Static greps cannot catch a wrong log path or a leaked temporary directory, so
# one helper is actually run in inspect mode as the current user. This is the
# only check in this suite that executes a helper; it needs no root, starts no
# container and contacts nothing. The administrator account is synthetic and
# resolves to a temporary home, so the run never writes into a real home.
inspect_tmp="$TMPDIR_TEST/inspect"
mkdir -p "$inspect_tmp"
inspect_home="$TMPDIR_TEST/inspect-home"
mkdir -p "$inspect_home"
inspect_stub="$TMPDIR_TEST/inspect-stub"
mkdir -p "$inspect_stub"
cat >"$inspect_stub/getent" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = passwd ] && [ "${2:-}" = review-inspect-admin ]; then
  printf 'review-inspect-admin:x:%s:%s::%s:/bin/bash\n' "$(/usr/bin/id -u)" "$(/usr/bin/id -g)" "${INSPECT_HOME}"
  exit 0
fi
exec /usr/bin/getent "$@"
EOF
chmod 0755 "$inspect_stub/getent"
inspect_log="$inspect_home/hermes-m04-posture.out"
rm -f "$inspect_log"

inspect_out=$(PATH="$inspect_stub:$PATH" TMPDIR="$inspect_tmp" INSPECT_HOME="$inspect_home" \
  HERMES_ADMIN=review-inspect-admin bash "$MANUAL/m04-posture.sh" 2>&1) && inspect_rc=0 || inspect_rc=$?
assert_equals '0' "$inspect_rc" 'inspection exits successfully without privileges'
assert_contains 'INSPECT ONLY' "$inspect_out" 'inspection states that nothing was changed'
if [ -f "$inspect_log" ] && [ "$(stat -c %a "$inspect_log")" = '600' ]; then
  _pass 'inspection writes its log to the configured administrator home at mode 0600'
else
  _fail 'inspection writes its log to the configured administrator home at mode 0600' "expected $inspect_log"
fi
assert_equals '0' "$(find "$inspect_tmp" -mindepth 1 | wc -l)" \
  'inspection leaves no private temporary state behind'

# ------------------------------------------------------------- gate ordering
section 'Gate ordering'

# Inspection must be cheap: the apply gate has to precede taking the operation
# lock, or merely looking at the host needs root and a free lock.
first_line() {
  grep -nE -- "$2" "$1" 2>/dev/null | head -n1 | cut -d: -f1 || true
}

ordering_checked=0
for script in "$MANUAL"/*.sh "$MANUAL"/boot/*.sh; do
  name=${script#"$MANUAL"/}
  case "$name" in lib-* | boot/lib-*) continue ;; esac
  apply_line=$(first_line "$script" 'mp_require_apply' || true)
  lock_line=$(first_line "$script" 'mp_lock_profile|mp_lock ' || true)
  tmp_line=$(first_line "$script" 'mp_secure_tmpdir' || true)
  trap_line=$(first_line "$script" 'mp_install_trap' || true)

  if [ -n "$apply_line" ] && [ -n "$lock_line" ]; then
    ordering_checked=$((ordering_checked + 1))
    if [ "$apply_line" -lt "$lock_line" ]; then
      _pass "$name gates inspection before taking the lock"
    else
      _fail "$name gates inspection before taking the lock" \
        "mp_lock at line $lock_line precedes mp_require_apply at line $apply_line"
    fi
  fi
  if [ -n "$tmp_line" ]; then
    ordering_checked=$((ordering_checked + 1))
    if [ -n "$trap_line" ] && [ "$trap_line" -lt "$tmp_line" ]; then
      _pass "$name installs cleanup before creating private state"
    else
      _fail "$name installs cleanup before creating private state" \
        "mp_secure_tmpdir at line $tmp_line is not preceded by mp_install_trap"
    fi
  fi
done
assert_min_count 10 "$ordering_checked" 'gate ordering invariants were exercised'

# ------------------------------------------- no automated destruction of lab assets
section 'Destructive lab operations are not automated'

# The Gate 2 authorization forbids destroying retained diagnostic and Gate 3 assets
# without explicit approval, so the fixture helper must not grow a destroy mode.
# Comment-insensitive: the script explains the omission in its header.
readonly LAB_FIXTURE="$MANUAL/lab/gate2-create-fixture.sh"
assert_grep 'requires root' "$LAB_FIXTURE" 'the fixture helper states its privilege requirement'
assert_grep 'PREFLIGHT=PASS' "$LAB_FIXTURE" 'the fixture helper has a non-mutating check mode'
assert_grep '\-\-dry-run' "$LAB_FIXTURE" 'the fixture check uses --dry-run so it cannot create storage'
assert_grep 'MIN_FREE_GIB' "$LAB_FIXTURE" 'the fixture helper enforces a capacity floor'
assert_grep 'lab-hermes-server' "$LAB_FIXTURE" 'the fixture helper refuses the retired fixture'
assert_grep '172.16.99' "$LAB_FIXTURE" 'the fixture helper refuses the retired network'

lab_code=$(grep -vE '^[[:space:]]*#' "$LAB_FIXTURE" || true)
destructive=$(grep -nE '\b(destroy|undefine|vol-delete|vol-wipe)\b' <<<"$lab_code" || true)
if [ -z "$destructive" ]; then
  _pass 'no destructive verb appears in fixture helper executable code'
else
  _fail 'no destructive verb appears in fixture helper executable code' "$destructive"
fi

# -------------------------------------------------------------- documentation
section 'Documentation parity'

assert_grep 'profile-contract.yaml' "$CONTRACT_DOC" 'the contract document names the contract file'
assert_grep 'terminal' "$CONTRACT_DOC" 'the contract document states the tool allowlist'
assert_grep 'test-hermes-manual-profile' "$CONTRIBUTING" 'the contributor guide lists the manual-profile check'
assert_grep 'test-hermes-manual-profile' "$README" 'the root README lists the manual-profile check'
assert_grep '2026-09-20-hermes-manual-profile-improvement' "$MANUAL/README.md" \
  'the manual README links the execution record'
assert_grep 'hermes-cli' "$CONTRACT_DOC" 'the contract document explains why the broad composite is not used'

print_summary
