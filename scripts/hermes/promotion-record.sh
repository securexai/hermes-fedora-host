#!/usr/bin/env bash
# shellcheck shell=bash
# Strict, secret-free promotion record implementation.

if [[ -n "${_HERMES_PROMOTION_RECORD_LOADED-}" ]]; then
  return 0
fi
readonly _HERMES_PROMOTION_RECORD_LOADED=1
readonly HERMES_PROMOTION_SCHEMA='hermes-promotion-v1'
readonly HERMES_PROMOTION_WINDOW_SECONDS=86400

promotion_record_fingerprint() {
  local root=$1 file
  local -a files=(
    "$root/hermes-deploy.sh"
    "$root/hermes-certify-vm.sh"
    "$root/scripts/hermes/deploy-lib.sh"
    "$root/scripts/hermes/remote-state.sh"
    "$root/scripts/hermes/remote-preflight.sh"
    "$root/scripts/hermes/fedora-server-host.sh"
    "$root/scripts/hermes/provider-auth-status.sh"
    "$root/scripts/hermes/certification-evidence.sh"
    "$root/scripts/hermes/promotion-record.sh"
    "$root/scripts/hermes/hermes.container"
    "$root/scripts/hermes/60-hermes-runtime.conf"
    "$root/scripts/hermes/70-hermes-volume-label.conf"
    "$root/scripts/hermes/harden-config.py"
    "$root/scripts/hermes/set-model.py"
    "$root/scripts/hermes/acceptance.sh"
    "$root/scripts/hermes/root-acceptance.sh"
    "$root/scripts/hermes/wrappers/hermes-chat"
    "$root/scripts/hermes/wrappers/hermes-status"
    "$root/scripts/hermes/wrappers/hermes-logs"
    "$root/vm/create-hermes-server-vm.sh"
    "$root/vm/hermes-luks-console.py"
    "$root/vm/kickstart/fedora-server.ks"
    "$root/vm/lib-hermes-luks-console.sh"
    "$root/vm/lib-vm-common.sh"
    "$root/vm/networks/lab-vlans.xml"
    "$root/hermes-remediation-wizard.sh"
    "$root/tests/test-hermes-e2e-vm.sh"
    "$root/tests/test-hermes-guide.sh"
    "$root/spec/hermes/deploy_spec.sh"
    "$root/spec/vm/luks_console_spec.sh"
    "$root/tests/test_hermes_unattended.py"
    "$root/tests/test_hermes_lab_disk.py"
    "$root/scripts/hermes/unattended/dispatch"
    "$root/scripts/hermes/unattended/vulnerability-policy.json"
    "$root/vm/kickstart/hermes-tpm-enroll.ks"
  )
  # The new public seam depends on these modules. Changes must also invalidate
  # legacy certification records; exclude interpreter cache/build artifacts.
  for file in "$root"/scripts/hermes/unattended/*.py "$root"/scripts/hermes/unattended/systemd/*; do
    [[ -f "$file" ]] && files+=("$file")
  done
  for file in "${files[@]}"; do
    [[ -r "$file" ]] || return 1
  done
  for file in "${files[@]}"; do
    printf '%s  %s\n' "${file#"$root"/}" "$(sha256sum "$file" | awk '{print $1}')"
  done | sha256sum | awk '{print $1}'
}

promotion_record_value() {
  local record=$1 key=$2
  sed -n "s/^${key}=//p" "$record" | sed -n '1p'
}

promotion_record_load() {
  local record=$1 line key value
  declare -A seen=()
  [[ -f "$record" && -r "$record" && ! -L "$record" ]] || return 1
  [[ "$(stat -c '%a' "$record" 2>/dev/null || true)" == 600 ]] || return 1
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^([a-z][a-z0-9_]*)=([^[:space:]]+)$ ]] || return 1
    key=${BASH_REMATCH[1]}
    value=${BASH_REMATCH[2]}
    [[ -z "${seen[$key]-}" ]] || return 1
    seen[$key]=1
    case "$key" in
      schema) PROMOTION_SCHEMA_VALUE=$value ;;
      certification_id) PROMOTION_CERTIFICATION_ID=$value ;;
      promotion_id) PROMOTION_ID=$value ;;
      issued_at) PROMOTION_ISSUED_AT=$value ;;
      expires_at) PROMOTION_EXPIRES_AT=$value ;;
      artifact_fingerprint) PROMOTION_ARTIFACT_FINGERPRINT=$value ;;
      iso_sha256) PROMOTION_ISO_SHA256=$value ;;
      iso_signature) PROMOTION_ISO_SIGNATURE=$value ;;
      fedora_version) PROMOTION_FEDORA_VERSION=$value ;;
      kernel) PROMOTION_KERNEL=$value ;;
      podman) PROMOTION_PODMAN=$value ;;
      hermes_image) PROMOTION_HERMES_IMAGE=$value ;;
      provider) PROMOTION_PROVIDER=$value ;;
      model) PROMOTION_MODEL=$value ;;
      inference_result) PROMOTION_INFERENCE_RESULT=$value ;;
      credentials_revoked) PROMOTION_CREDENTIALS_REVOKED=$value ;;
      data_purged) PROMOTION_DATA_PURGED=$value ;;
      vm_destroyed) PROMOTION_VM_DESTROYED=$value ;;
      *) return 1 ;;
    esac
  done <"$record"
  for key in schema certification_id promotion_id issued_at expires_at artifact_fingerprint \
    iso_sha256 iso_signature fedora_version kernel podman hermes_image provider model \
    inference_result credentials_revoked data_purged vm_destroyed; do
    [[ -n "${seen[$key]-}" ]] || return 1
  done
  [[ "$PROMOTION_SCHEMA_VALUE" == "$HERMES_PROMOTION_SCHEMA" ]] || return 1
  [[ "$PROMOTION_CERTIFICATION_ID" =~ ^[A-Za-z0-9._-]+$ ]] || return 1
  [[ "$PROMOTION_ID" =~ ^[A-Za-z0-9._-]+$ ]] || return 1
  [[ "$PROMOTION_ISSUED_AT" =~ ^[0-9]+$ && "$PROMOTION_EXPIRES_AT" =~ ^[0-9]+$ ]] || return 1
  ((PROMOTION_EXPIRES_AT > PROMOTION_ISSUED_AT)) || return 1
  ((PROMOTION_EXPIRES_AT - PROMOTION_ISSUED_AT <= HERMES_PROMOTION_WINDOW_SECONDS)) || return 1
  [[ "$PROMOTION_ARTIFACT_FINGERPRINT" =~ ^[[:xdigit:]]{64}$ ]] || return 1
  [[ "$PROMOTION_ISO_SHA256" =~ ^[[:xdigit:]]{64}$ ]] || return 1
  [[ "$PROMOTION_ISO_SIGNATURE" == verified ]] || return 1
  [[ "$PROMOTION_FEDORA_VERSION" == 44 ]] || return 1
  [[ "$PROMOTION_KERNEL" =~ ^[A-Za-z0-9._:+/-]+$ ]] || return 1
  [[ "$PROMOTION_PODMAN" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][A-Za-z0-9]+)*$ ]] || return 1
  [[ "$PROMOTION_HERMES_IMAGE" == docker.io/nousresearch/hermes-agent@sha256:* ]] || return 1
  [[ "$PROMOTION_PROVIDER" == openai-codex || "$PROMOTION_PROVIDER" == openai-api || "$PROMOTION_PROVIDER" == nous ]] || return 1
  [[ "$PROMOTION_MODEL" =~ ^[A-Za-z0-9._:/-]+$ ]] || return 1
  [[ "$PROMOTION_INFERENCE_RESULT" == HERMES_OK ]] || return 1
  [[ "$PROMOTION_CREDENTIALS_REVOKED" == true && "$PROMOTION_DATA_PURGED" == true &&
    "$PROMOTION_VM_DESTROYED" == true ]] || return 1
}

promotion_record_validate() {
  local record=$1 provider=$2 model=$3 expected_image=$4 artifact_fingerprint=$5 now
  promotion_record_load "$record" || return 1
  [[ "$PROMOTION_PROVIDER" == "$provider" && "$PROMOTION_MODEL" == "$model" ]] || return 1
  [[ "$PROMOTION_HERMES_IMAGE" == "$expected_image" ]] || return 1
  [[ "$PROMOTION_ARTIFACT_FINGERPRINT" == "$artifact_fingerprint" ]] || return 1
  now=$(date -u +%s)
  [[ "$now" =~ ^[0-9]+$ ]] || return 1
  ((PROMOTION_ISSUED_AT <= now)) || return 1
  ((now <= PROMOTION_EXPIRES_AT)) || return 2
}
