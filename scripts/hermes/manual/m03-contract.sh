#!/usr/bin/env bash
# M03 step 2 (credential-free): apply and verify the manual-profile
# configuration contract without any provider credential.
#
# Default is inspect-only; re-run with --apply to make changes.
#
# This is the Gate 2 path for the configuration contract. m04-posture.sh only
# INSTALLS the hardening helper; this helper is where the contract is actually
# applied and verified. It needs no credential and makes no provider call, so it
# can run in the credential-free lab. Provider and messaging acceptance stay in
# m03-accept.sh, separately gated by --allow-provider-call.
#
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/m03-contract.sh --apply
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
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m03-contract.out")
RUNTIME_ACCOUNT="${HERMES_RUNTIME:-hermes}"
RUNTIME_HOME="${HERMES_RUNTIME_HOME:-/home/${RUNTIME_ACCOUNT}}"
HERMES_UID=$(id -u "$RUNTIME_ACCOUNT")
GW_UID=10000
GW_GID=10000
GW=hermes-gateway
GW_STATE="$RUNTIME_HOME/gateway-state"
GWSSH="$RUNTIME_HOME/gateway-ssh"
GW_IMAGE=docker.io/nousresearch/hermes-agent@sha256:fca358f12efd65bfaaca05884166f15c0e2788375ca30d77061ac1ebc96452b7

mp_require_apply 'would install the contract helper, apply the reviewed configuration contract, and verify it'
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

# One-shot command in the pinned gateway image, as the runtime identity, with the
# same mounts the service uses. No s6 bootstrap, no provider credential, no egress.
gcone() {
  entry="$1"
  shift
  h podman run --rm --network none --user "$GW_UID:$GW_UID" --workdir /opt/hermes \
    -v "$GW_STATE":/opt/data:z \
    -v "$RUNTIME_HOME/transport:/run/hermes-transport:z" \
    -v "$GWSSH":/opt/hermes/gateway-ssh:ro,Z \
    --entrypoint "$entry" "$GW_IMAGE" "$@"
}

# gw_runtime — whether the gateway container is live. A LIVE gateway is driven
# with `podman exec`, which reuses its existing mounts and relabels nothing; a
# one-shot `podman run` mounts the private SSH tree with `:ro,Z`, and Podman's
# host-side relabel can invalidate the running gateway's own key, trust and shim
# labels even though `ro` prevents container writes. `unknown` refuses, because a
# possibly-live private tree must not be mounted or relabelled.
gw_runtime=$(mp_container_state h "$GW") || true

# gcur — run a command in the pinned image without creating a private mount when
# the container is live. The exec keeps the runtime identity explicit: exec does
# NOT inherit the supervised process's dropped UID, so `--user` and `--workdir`
# are what make the run test the gateway's actual identity. A one-shot run is
# used only when a successful inventory proves the container is not running.
gcur() {
  local st
  st=$(mp_container_state h "$GW") || true
  case "$st" in
    running) h podman exec --user "$GW_UID:$GW_GID" --workdir /opt/hermes "$GW" "$@" ;;
    stopped) gcone "$@" ;;
    *)
      printf 'STOP: cannot determine whether %s is running; refusing to mount private material\n' "$GW" >&2
      return 1
      ;;
  esac
}

# prepare_gateway_state — make the profile state directory usable by the pinned
# container's own UID/GID.
#
# Host account `hermes` maps to namespace UID 0, NOT to container UID 10000, so
# `install -d -o hermes -g hermes -m 0700` locks the selected container user out
# and can undo a previously working mapped ownership on a rerun. The directory is
# therefore created only when absent, then handed to the container UID/GID inside
# the rootless user namespace (where 10000 maps to the subordinate range). An
# existing mapped ownership is preserved; the mode is tightened to 0700 but never
# broadened. Returns non-zero so a caller cannot report success after it failed.
prepare_gateway_state() {
  local ns_uid mode
  if [ ! -d "$GW_STATE" ]; then
    install -d -o "$RUNTIME_ACCOUNT" -g "$RUNTIME_ACCOUNT" -m 0700 "$GW_STATE" || {
      printf 'STOP: cannot create %s\n' "$GW_STATE" >&2
      return 1
    }
  fi
  ns_uid=$(h podman unshare stat -c '%u' -- "$GW_STATE" 2>/dev/null || true)
  if [ "$ns_uid" != "$GW_UID" ]; then
    if ! h podman unshare chown "$GW_UID:$GW_GID" -- "$GW_STATE"; then
      printf 'STOP: cannot hand %s to the container UID/GID %s:%s (namespace uid was %s)\n' \
        "$GW_STATE" "$GW_UID" "$GW_GID" "${ns_uid:-unknown}" >&2
      return 1
    fi
  fi
  mode=$(stat -c '%a' -- "$GW_STATE" 2>/dev/null || true)
  if [ "$((10#${mode:-0}))" != "$((10#700))" ]; then
    chmod 0700 -- "$GW_STATE" || return 1
  fi
  printf 'gateway_state=%s container_uid=%s namespace_owner=%s mode=%s\n' \
    "$GW_STATE" "$GW_UID" "$(h podman unshare stat -c '%u' -- "$GW_STATE" 2>/dev/null || echo unknown)" \
    "$(stat -c '%a' -- "$GW_STATE" 2>/dev/null || echo unknown)"
  return 0
}

rc=0
{
  echo "### M03 step 2 (credential-free): configuration contract apply + verify"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  if [ "$gw_runtime" = unknown ]; then
    echo "STOP: cannot determine whether $GW is running; refusing to mount the private SSH tree."
    echo "      A possibly-live :Z mount would invalidate the running gateway's own labels."
    mp_check gateway_container_state FAIL "podman could not prove whether $GW is running"
    mp_check contract_helper_installed FAIL "skipped: the container state is undetermined"
    mp_check profile_contract_applied FAIL "skipped: the container state is undetermined"
    mp_check contract_verified FAIL "skipped: the container state is undetermined"
    mp_audit_avc_check avc_denials recent
    echo "===== done ====="
    exit 1
  fi
  echo "container_state=$gw_runtime"
  echo

  echo "===== install the contract helper and verifier (convergent) ====="
  prepare_gateway_state || exit 1
  for pair in \
    "config/harden-config.py:manual-harden-config.py" \
    "config/verify-contract.py:manual-verify-contract.py" \
    "config/profile-contract.yaml:profile-contract.yaml"; do
    src="$BUNDLE/${pair%%:*}"
    dest="$GWSSH/${pair##*:}"
    result=$(mp_install_reconcile "contract_file_$(basename "$dest")" 0644 "$RUNTIME_ACCOUNT:$RUNTIME_ACCOUNT" "$src" "$dest") || exit 1
    echo "$result"
    if [ "$gw_runtime" = running ]; then
      case "$result" in
        CHANGED*)
          # A file created inside the live :Z mount keeps the host default label
          # and the running gateway cannot read it; give it the sibling label
          # instead of creating a new relabelling mount.
          chcon --reference="$GWSSH/known_hosts" "$dest" 2>/dev/null \
            || chcon -t container_file_t "$dest" 2>/dev/null || true
          ;;
      esac
    fi
  done
  mp_check contract_helper_installed "$([ -r "$GWSSH/manual-harden-config.py" ] && [ -r "$GWSSH/manual-verify-contract.py" ] && echo PASS || echo FAIL)"
  echo

  echo "===== convergence check (informational) ====="
  check_out=$(gcur /opt/hermes/.venv/bin/python3 /opt/hermes/gateway-ssh/manual-harden-config.py --check 2>&1)
  check_rc=$?
  printf '%s\n' "$check_out" | tail -n 5
  mp_info contract_converged "rc=$check_rc; a converged profile needs no write and no backup"
  echo

  echo "===== apply the reviewed configuration contract ====="
  harden_out=$(gcur env "HERMES_PROFILE_CONTRACT=/opt/hermes/gateway-ssh/profile-contract.yaml" \
    /opt/hermes/.venv/bin/python3 /opt/hermes/gateway-ssh/manual-harden-config.py 2>&1)
  harden_rc=$?
  printf '%s\n' "$harden_out"
  mp_check profile_contract_applied "$([ "$harden_rc" -eq 0 ] && echo PASS || echo FAIL)" "harden rc=$harden_rc"
  echo

  echo "===== credential-free contract verification ====="
  verify_out=$(gcur /opt/hermes/.venv/bin/python3 /opt/hermes/gateway-ssh/manual-verify-contract.py \
    --contract /opt/hermes/gateway-ssh/profile-contract.yaml \
    --config /opt/data/config.yaml \
    --env /opt/data/.env 2>&1)
  verify_rc=$?
  printf '%s\n' "$verify_out" | tail -n 30
  mp_check contract_verified "$([[ "$verify_out" == *CONTRACT_VERIFY=PASS* ]] && echo PASS || echo FAIL)" \
    "the profile must match the contract with replacement semantics (rc=$verify_rc)"
  echo

  echo "===== config readback (no secret values) ====="
  gcur /opt/hermes/.venv/bin/python3 -c "
import json, pathlib, yaml
c = yaml.safe_load(pathlib.Path('/opt/data/config.yaml').read_text())
print('hooks=' + str(c.get('hooks')))
print('mcp_servers=' + str(c.get('mcp_servers')))
print('toolsets=' + json.dumps(c.get('toolsets'), sort_keys=True))
print('platform_toolsets=' + json.dumps(c.get('platform_toolsets'), sort_keys=True))
print('approvals=' + json.dumps(c.get('approvals'), sort_keys=True))
print('security=' + json.dumps(c.get('security'), sort_keys=True))
" 2>&1
  echo

  echo "===== deferred to Gate 3 (never counted as PASS here) ====="
  # Gate 2 is credential-free by authorization. These are reported explicitly so
  # a green contract run is not misread as provider acceptance.
  mp_defer provider_credentials "Gate 3 owns credential provisioning; no .env is required and none is read"
  mp_defer inference_exact "Gate 3 owns provider inference acceptance"
  mp_defer worker_tool_roundtrip "Gate 3 owns the authenticated tool round-trip"
  mp_defer gateway_stays_active "Gate 3 owns gateway daemon stability without a credential-free daemon"
  echo

  echo "===== recent AVC denials ====="
  mp_audit_avc_check avc_denials recent
  echo "===== done ====="
} 2>&1 | tee "$OUT" || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
echo "WROTE=$OUT"
mp_finalize "$OUT" "${rc:-0}"
