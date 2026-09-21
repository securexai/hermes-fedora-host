#!/usr/bin/env bash
# M03 acceptance: model + hardening, authenticated HERMES_OK, a harmless tool
# round-trip that must land in the offline worker, and bounded leak checks.
#
# Default is inspect-only. Two independent opt-ins are required before this
# helper spends money or changes the profile:
#   --apply                perform the profile changes and checks
#   --allow-provider-call  run the authenticated inference and tool round trip
#
# Requires the profile .env to have been provisioned already.
#
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> \
#     bash ~/hermes-manual/m03-accept.sh --apply --allow-provider-call
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
ALLOW_PROVIDER_CALL=0
for arg in "$@"; do
  [ "$arg" = "--allow-provider-call" ] && ALLOW_PROVIDER_CALL=1
done
mapfile -t MP_ARGS < <(mp_positionals "$@")
BUNDLE="${MP_ARGS[0]:-$HERE}"
ADMIN_ACCOUNT=$(mp_admin_account)
ADMIN_HOME=$(mp_admin_home)
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m03-accept.out")
HERMES_UID=$(id -u hermes)
GW_UID=10000
GW_STATE=/home/hermes/gateway-state
GWSSH=/home/hermes/gateway-ssh
GW_IMAGE=docker.io/nousresearch/hermes-agent@sha256:9469b3e78b9545b6d576eb8887a95352e9a0ea83730eaf31431cf862ca1010e1
MODEL="${HERMES_MODEL:-gpt-5.6-luna}"
PROVIDER="${HERMES_PROVIDER:-openai-api}"

mp_require_apply 'would apply the profile hardening and run the acceptance checks'
mp_require_host_identity
mp_lock_profile
mp_install_trap
mp_require_tools podman

h() {
  if ! mountpoint -q /home/hermes; then
    printf 'STOP: /home/hermes is not mounted.\n' >&2
    return 1
  fi
  sudo -u hermes -- env -i --chdir=/home/hermes \
    HOME=/home/hermes USER=hermes LOGNAME=hermes PATH=/usr/local/bin:/usr/bin:/bin \
    TERM="${TERM:-xterm}" XDG_RUNTIME_DIR="/run/user/$HERMES_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$HERMES_UID/bus" \
    TMPDIR=/home/hermes/.cache/podman-tmp "$@"
}

# One-shot container in the pinned image as the runtime identity, WITH egress
# (needed only when a provider call is explicitly authorized).
gconet() {
  entry="$1"
  shift
  h timeout 240 podman run --rm --user "$GW_UID:$GW_UID" --workdir /opt/hermes \
    -v "$GW_STATE":/opt/data:z \
    -v /home/hermes/transport:/run/hermes-transport:z \
    -v "$GWSSH":/opt/hermes/gateway-ssh:ro,Z \
    -v "$GWSSH/ssh":/opt/hermes/bin/ssh:ro,Z \
    -v "$GWSSH/scp":/opt/hermes/bin/scp:ro,Z \
    -v "$GWSSH/sftp":/opt/hermes/bin/sftp:ro,Z \
    --entrypoint "$entry" "$GW_IMAGE" "$@"
}

rc=0
{
  echo "### M03 acceptance"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "### allow_provider_call=$ALLOW_PROVIDER_CALL provider=$PROVIDER model=$MODEL"
  echo

  echo "===== preconditions ====="
  if [ -s "$GW_STATE/.env" ]; then
    echo "env_present=yes"
    stat -c 'env_mode=%a owner=%u:%g size=%s' "$GW_STATE/.env"
    mp_check profile_credentials PASS
  elif [ "$ALLOW_PROVIDER_CALL" -eq 1 ]; then
    echo "env_present=NO - a provider call was authorized but no credential is provisioned"
    mp_check profile_credentials FAIL "profile .env is missing or empty but --allow-provider-call was given"
  else
    echo "env_present=NO - deferred: no provider call is authorized in this run"
    # Required only for provider acceptance, which Gate 3 owns. Without
    # --allow-provider-call this run is credential-free, so it is deferred
    # rather than failed, and never recorded as a PASS.
    mp_defer profile_credentials "Gate 3 owns credential provisioning; no provider call was authorized"
  fi
  echo "worker_state=$(h systemctl --user is-active hermes-worker.service)"
  echo "gateway_state=$(h systemctl --user is-active hermes-gateway.service)"
  echo

  echo "===== install config helpers ====="
  install -o hermes -g hermes -m 0644 "$BUNDLE/config/set-model.py" "$GWSSH/set-model.py"
  install -o hermes -g hermes -m 0644 "$BUNDLE/config/harden-config.py" "$GWSSH/manual-harden-config.py"
  install -o hermes -g hermes -m 0644 "$BUNDLE/config/profile-contract.yaml" "$GWSSH/profile-contract.yaml"
  chcon --reference="$GWSSH/known_hosts" "$GWSSH/set-model.py" "$GWSSH/manual-harden-config.py" "$GWSSH/profile-contract.yaml" 2>/dev/null \
    || chcon -t container_file_t "$GWSSH/set-model.py" "$GWSSH/manual-harden-config.py" "$GWSSH/profile-contract.yaml" 2>/dev/null || true
  echo

  echo "===== set provider and model ====="
  model_out=$(gconet env "HERMES_PROVIDER=$PROVIDER" "HERMES_MODEL=$MODEL" \
    /opt/hermes/.venv/bin/python3 /opt/hermes/gateway-ssh/set-model.py 2>&1)
  model_rc=$?
  printf '%s\n' "$model_out"
  echo "set_model_rc=$model_rc"
  mp_check provider_model_set "$([ "$model_rc" -eq 0 ] && echo PASS || echo FAIL)"
  echo

  echo "===== apply the manual-profile configuration contract ====="
  harden_out=$(gconet env "HERMES_PROFILE_CONTRACT=/opt/hermes/gateway-ssh/profile-contract.yaml" \
    /opt/hermes/.venv/bin/python3 /opt/hermes/gateway-ssh/manual-harden-config.py 2>&1)
  harden_rc=$?
  printf '%s\n' "$harden_out"
  echo "harden_rc=$harden_rc"
  mp_check profile_contract_applied "$([ "$harden_rc" -eq 0 ] && echo PASS || echo FAIL)"
  echo

  echo "===== config readback (no secret values) ====="
  gconet /opt/hermes/.venv/bin/python3 -c "
import json, pathlib, yaml
c = yaml.safe_load(pathlib.Path('/opt/data/config.yaml').read_text())
print('model_section=' + json.dumps(c.get('model'), sort_keys=True))
print('provider=' + str(c.get('provider')) + ' default_model=' + str(c.get('default_model')))
print('terminal=' + json.dumps(c.get('terminal'), sort_keys=True))
print('approvals=' + json.dumps(c.get('approvals'), sort_keys=True))
print('security=' + json.dumps(c.get('security'), sort_keys=True))
print('toolsets=' + json.dumps(c.get('toolsets'), sort_keys=True))
print('platform_toolsets=' + json.dumps(c.get('platform_toolsets'), sort_keys=True))
print('hooks=' + str(c.get('hooks')) + ' mcp_servers=' + str(c.get('mcp_servers')))
print('cron_scheduling=' + str((c.get('cron') or {}).get('allow_agent_scheduling')))
" 2>&1
  echo

  if [ "$ALLOW_PROVIDER_CALL" -eq 1 ]; then
    echo "===== authenticated inference (expect exactly HERMES_OK) ====="
    inf_out=$(gconet /opt/hermes/bin/hermes --safe-mode --provider "$PROVIDER" --model "$MODEL" \
      --toolsets context_engine -z 'Return exactly HERMES_OK and nothing else.' 2>&1)
    inf_rc=$?
    printf 'inference_output=%s\n' "$inf_out"
    echo "inference_rc=$inf_rc"
    mp_check inference_exact "$([ "$(printf '%s' "$inf_out" | tr -d '\r' | sed -e 's/[[:space:]]*$//')" = "HERMES_OK" ] && echo PASS || echo FAIL)"
    echo

    echo "===== harmless tool round-trip (must execute in the worker) ====="
    tool_out=$(gconet /opt/hermes/bin/hermes --provider "$PROVIDER" --model "$MODEL" \
      --toolsets terminal -z 'Run the shell command: echo HERMES_WORKER_TOOL_OK; head -1 /etc/fedora-release   Then reply only with the command output.' 2>&1)
    tool_rc=$?
    printf 'tool_output=%s\n' "$tool_out"
    echo "tool_rc=$tool_rc"
    mp_check worker_tool_roundtrip "$([[ "$tool_out" == *HERMES_WORKER_TOOL_OK* ]] && echo PASS || echo FAIL)"
    echo
  else
    echo "===== provider calls skipped (--allow-provider-call not given) ====="
    # Gate 3 owns provider and messaging acceptance. These are deferred, not
    # unverified, so the credential-free part of the run can still complete
    # without ever claiming a provider result.
    mp_defer inference_exact "Gate 3 owns provider acceptance; no provider call authorized in this run"
    mp_defer worker_tool_roundtrip "Gate 3 owns provider acceptance; no provider call authorized in this run"
    echo
  fi

  echo "===== bounded credential-leak checks (values never printed) ====="
  # A synthetic canary is planted in the profile .env first, so the checks prove
  # the mechanism works even when no real provider key is present.
  CANARY="canary-$RANDOM$RANDOM$RANDOM$RANDOM"
  printf 'HERMES_LEAK_CANARY=%s\n' "$CANARY" >>"$GW_STATE/.env"
  chmod 0600 "$GW_STATE/.env"
  if grep -qF -- "$CANARY" "$GW_STATE/.env"; then
    mp_check canary_planted PASS
  else
    mp_check canary_planted FAIL "could not plant the synthetic canary"
  fi
  for target in "$GW_STATE/config.yaml" /home/hermes/transport; do
    if grep -rIlF -- "$CANARY" "$target" >/dev/null 2>&1; then
      mp_check "canary_absent_$(basename "$target")" FAIL "canary reached $target"
    else
      mp_check "canary_absent_$(basename "$target")" PASS
    fi
  done
  if grep -rIlF -- "$CANARY" /home/hermes/worker-state >/dev/null 2>&1; then
    mp_check canary_absent_worker_state FAIL "canary reached the worker state"
  else
    mp_check canary_absent_worker_state PASS
  fi
  # Remove the canary again; the profile must not keep test material. grep -v
  # exits 1 when it selects no lines (the .env held only the canary), which is a
  # legitimate empty result, not a failure to rewrite.
  grep -v '^HERMES_LEAK_CANARY=' "$GW_STATE/.env" >"$GW_STATE/.env.tmp" || true
  chmod 0600 "$GW_STATE/.env.tmp"
  mv -f "$GW_STATE/.env.tmp" "$GW_STATE/.env"
  if grep -qF -- "$CANARY" "$GW_STATE/.env"; then
    mp_check canary_removed FAIL "the canary is still in the profile .env"
  else
    mp_check canary_removed PASS
  fi
  echo

  echo "===== recent AVC denials ====="
  mp_audit_avc_check avc_denials recent
  echo "===== done ====="
} 2>&1 | tee "$OUT" || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
echo "WROTE=$OUT"
mp_finalize "$OUT" "${rc:-0}"
