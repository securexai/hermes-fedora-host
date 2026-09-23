#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC2016
# Full disposable Fedora Server certification and promotion-record generator.

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s nullglob
umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR
REPO_ROOT=$SCRIPT_DIR
readonly REPO_ROOT
# shellcheck source=vm/lib-vm-common.sh
source "$REPO_ROOT/vm/lib-vm-common.sh"
# shellcheck source=vm/lib-hermes-luks-console.sh
source "$REPO_ROOT/vm/lib-hermes-luks-console.sh"
# shellcheck source=scripts/hermes/promotion-record.sh
source "$REPO_ROOT/scripts/hermes/promotion-record.sh"
# shellcheck source=scripts/hermes/certification-evidence.sh
source "$REPO_ROOT/scripts/hermes/certification-evidence.sh"

readonly VM_NAME='lab-hermes-server'
readonly VM_IP='172.16.99.12'
readonly VM_USER='lab'
readonly VM_MGMT_CIDR='172.16.99.0/24'
readonly VM_STORAGE_POOL='/var/lib/libvirt/images'
readonly VM_DISK_PATH="$VM_STORAGE_POOL/$VM_NAME.qcow2"
readonly VM_OEMDRV_PATH="$VM_STORAGE_POOL/$VM_NAME-oemdrv.iso"
readonly EXPECTED_ISO_NAME='Fedora-Server-dvd-x86_64-44-1.7.iso'
readonly EXPECTED_ISO_SHA256='85837793bfa36db6bc709b4cecd2ec116951b87d9c53c3d95eb2fac8dcf7cf1f'
readonly EXPECTED_IMAGE='docker.io/nousresearch/hermes-agent@sha256:e0df6adebddf29b91112aefc999d4aaf6846c9eb544faca5672a16a13590ff79'
readonly VM_CREATOR="$REPO_ROOT/vm/create-hermes-server-vm.sh"
readonly CONTROLLER="$REPO_ROOT/hermes-deploy.sh"
readonly LUKS_CONSOLE_WATCH_SECONDS=21600
readonly LUKS_CONSOLE_READY_SECONDS=30

ISO_PATH=''
CHECKSUM_PATH=''
FEDORA_KEYRING=''
IDENTITY_FILE=''
PROVIDER='openai-codex'
MODEL='gpt-5.6-luna'
RUN_DIR=''
KNOWN_HOSTS=''
VM_CREATED=false
UNLOCK_MONITOR_PID=''
UNLOCK_MONITOR_LOG=''
UNLOCK_MONITOR_READY=''
UNLOCK_WATCHER_PID=''
INTERFACE=''
CERTIFICATION_LOCK_FD=''

die() {
  local message=$1
  local code=${2:-1}
  printf 'ERROR: %s\n' "$message" >&2
  exit "$code"
}

show_help() {
  cat <<'EOF'
Certify Hermes on a disposable Fedora Server 44 VM and issue a promotion record.

Usage:
  ./hermes-certify-vm.sh \
    --iso PATH --checksum PATH --fedora-keyring PATH \
    --identity-file PATH --provider ID --model MODEL

The ISO and signed checksum must already exist locally. The certifier never
downloads media. It creates lab-hermes-server at 172.16.99.12 with LUKS and
Secure Boot, runs the full deployment/provider/HERMES_OK acceptance, revokes
all supported providers, purges fresh Hermes data, destroys the VM, and only
then prints PROMOTION_RECORD=/absolute/path.
EOF
}

valid_provider() {
  [[ "$1" == openai-codex || "$1" == openai-api || "$1" == nous ]]
}

valid_model() {
  [[ "$1" =~ ^[A-Za-z0-9._:/-]+$ ]]
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --iso)
      [[ $# -gt 1 ]] || die '--iso requires a path' 64
      ISO_PATH=$2
      shift 2
      ;;
    --checksum)
      [[ $# -gt 1 ]] || die '--checksum requires a path' 64
      CHECKSUM_PATH=$2
      shift 2
      ;;
    --fedora-keyring)
      [[ $# -gt 1 ]] || die '--fedora-keyring requires a path' 64
      FEDORA_KEYRING=$2
      shift 2
      ;;
    --identity-file)
      [[ $# -gt 1 ]] || die '--identity-file requires a path' 64
      IDENTITY_FILE=$2
      shift 2
      ;;
    --provider)
      [[ $# -gt 1 ]] || die '--provider requires a value' 64
      PROVIDER=$2
      shift 2
      ;;
    --model)
      [[ $# -gt 1 ]] || die '--model requires a value' 64
      MODEL=$2
      shift 2
      ;;
    --help | -h)
      show_help
      exit 0
      ;;
    *)
      die "unknown argument: $1" 64
      ;;
  esac
done

[[ -r "$ISO_PATH" ]] || die "ISO is not readable: $ISO_PATH" 66
[[ -r "$CHECKSUM_PATH" ]] || die "signed checksum is not readable: $CHECKSUM_PATH" 66
[[ -r "$FEDORA_KEYRING" ]] || die "Fedora keyring is not readable: $FEDORA_KEYRING" 66
[[ -r "$IDENTITY_FILE" ]] || die "SSH identity file is not readable: $IDENTITY_FILE" 66
valid_provider "$PROVIDER" || die 'provider must be openai-codex, openai-api, or nous' 64
valid_model "$MODEL" || die 'model contains unsupported characters' 64
SSH_PUBKEY="${IDENTITY_FILE}.pub"

RUN_STAMP=$(date -u +%Y%m%dT%H%M%SZ)
STATE_HOME=${XDG_STATE_HOME:-}
if [[ -z "$STATE_HOME" ]]; then
  [[ -n "${HOME:-}" ]] || die 'HOME or XDG_STATE_HOME is required' 70
  STATE_HOME=$HOME/.local/state
fi
CERTIFICATION_ROOT="$STATE_HOME/hermes-certification"
install -d -m 0700 "$CERTIFICATION_ROOT"
require_cmd flock
CERTIFICATION_LOCK="$CERTIFICATION_ROOT/certification.lock"
exec {CERTIFICATION_LOCK_FD}>"$CERTIFICATION_LOCK"
chmod 0600 "$CERTIFICATION_LOCK"
flock -n "$CERTIFICATION_LOCK_FD" \
  || die 'another Hermes certification is already active; finish or stop it before retrying' 75

RUN_DIR="$CERTIFICATION_ROOT/run-$RUN_STAMP"
install -d -m 0700 "$RUN_DIR"
KNOWN_HOSTS="$RUN_DIR/known_hosts"
UNLOCK_MONITOR_LOG="$RUN_DIR/unlock-monitor.log"
UNLOCK_MONITOR_READY="$RUN_DIR/unlock-monitor.ready"
install -m 0600 /dev/null "$UNLOCK_MONITOR_LOG"
if [[ ! -r "$SSH_PUBKEY" ]]; then
  SSH_PUBKEY=$(mktemp "$RUN_DIR/ssh-key.XXXXXX")
  chmod 0600 "$SSH_PUBKEY"
  ssh-keygen -y -f "$IDENTITY_FILE" >"$SSH_PUBKEY" || die 'could not derive the SSH public key' 66
fi

verify_media() {
  local verified_checksum actual signature checksum_payload clear_signed=false
  verified_checksum=$(mktemp "$RUN_DIR/verified-checksum.XXXXXX")
  chmod 0600 "$verified_checksum"
  checksum_payload=$CHECKSUM_PATH
  signature=''
  if grep -Fq -- '-----BEGIN PGP SIGNED MESSAGE-----' "$CHECKSUM_PATH" 2>/dev/null; then
    clear_signed=true
  else
    case "$CHECKSUM_PATH" in
      *.gpg)
        checksum_payload=${CHECKSUM_PATH%.gpg}
        signature=$CHECKSUM_PATH
        ;;
      *.asc)
        checksum_payload=${CHECKSUM_PATH%.asc}
        signature=$CHECKSUM_PATH
        ;;
      *)
        for candidate in "$CHECKSUM_PATH.gpg" "$CHECKSUM_PATH.asc"; do
          if [[ -r "$candidate" ]]; then
            signature=$candidate
            break
          fi
        done
        ;;
    esac
  fi
  [[ -r "$checksum_payload" ]] || die "checksum payload is not readable: $checksum_payload" 66
  if [[ -n "$signature" ]]; then
    gpgv --keyring "$FEDORA_KEYRING" --output "$verified_checksum" "$signature" "$checksum_payload" \
      >"$RUN_DIR/checksum-signature.log" 2>&1 \
      || die 'Fedora checksum signature verification failed' 77
  elif $clear_signed; then
    gpgv --keyring "$FEDORA_KEYRING" "$checksum_payload" >"$RUN_DIR/checksum-signature.log" 2>&1 \
      || die 'Fedora clear-signed checksum verification failed' 77
    install -d -m 0700 "$RUN_DIR/gnupg"
    GNUPGHOME="$RUN_DIR/gnupg" gpg --batch --no-options --no-default-keyring \
      --keyring "$FEDORA_KEYRING" --output - --decrypt "$checksum_payload" \
      >"$verified_checksum" 2>>"$RUN_DIR/checksum-signature.log" \
      || die 'Fedora clear-signed checksum extraction failed' 77
  else
    die 'detached Fedora checksum signature is missing; expected .gpg or .asc beside the checksum' 77
  fi
  awk -v expected="$EXPECTED_ISO_SHA256" -v iso_name="$EXPECTED_ISO_NAME" \
    'index($0, expected) && index($0, iso_name) {found=1} END {exit(found ? 0 : 1)}' \
    "$verified_checksum" \
    || die 'verified checksum file does not contain the expected Fedora Server 44 DVD hash' 77
  actual=$(sha256sum "$ISO_PATH" | awk '{print $1}')
  [[ "$actual" == "$EXPECTED_ISO_SHA256" ]] \
    || die "Fedora Server ISO SHA-256 mismatch: $actual" 77
  printf 'ISO_SIGNATURE=verified\nISO_SHA256=%s\n' "$actual" >"$RUN_DIR/media-verification"
  chmod 0600 "$RUN_DIR/media-verification"
}

run_offline_tests() (
  cd "$REPO_ROOT"
  exec </dev/null
  # Check-only gate inside the dev-toolbox `infra` container. Host runtime
  # operations (virsh, virt-install, qemu-img, xorriso) stay on the host; every
  # repository check runs in the container through an explicit Toolbox
  # invocation. The two scripts are:
  #   run-offline-checks.sh   reviewed offline suites + full-tree secret scan
  #                           (toolbox/scan-secrets.sh, with a positive control)
  #   run-check-only-lint.sh  check-only lint over the tracked AND untracked tree
  # Neither rewrites the working tree, and neither runs the real integration
  # suites (those are opt-in via toolbox/run-integration-checks.sh).
  command -v toolbox >/dev/null 2>&1 || die 'toolbox is required to run the repository check gate' 69
  setsid --wait toolbox run --container dev-infra-hermes bash -c \
    "cd $(printf '%q' "$REPO_ROOT") && bash toolbox/run-offline-checks.sh && bash toolbox/run-check-only-lint.sh"
  python3 vm/hermes-luks-console.py --help >/dev/null
)

ssh_vm() {
  ssh -i "$IDENTITY_FILE" \
    -o IdentitiesOnly=yes \
    -o PreferredAuthentications=publickey \
    -o PasswordAuthentication=no \
    -o KbdInteractiveAuthentication=no \
    -o StrictHostKeyChecking=accept-new \
    -o UserKnownHostsFile="$KNOWN_HOSTS" \
    -o ConnectTimeout=15 \
    "$VM_USER@$VM_IP" "$@"
}

wait_ssh() {
  local deadline=$((SECONDS + 600))
  while ((SECONDS < deadline)); do
    ssh_vm true >/dev/null 2>&1 && return 0
    sleep 5
  done
  return 1
}

unlock_fixture() {
  hermes_luks_console_watch "$VM_NAME" qemu:///system \
    "$LUKS_CONSOLE_WATCH_SECONDS" "$UNLOCK_MONITOR_LOG" "$UNLOCK_MONITOR_READY"
}

unlock_monitor_log() {
  printf '%s %s\n' "$(date -u +%FT%TZ)" "$*" >>"$UNLOCK_MONITOR_LOG"
}

vm_domain_state() {
  local state
  state=$(virsh -c qemu:///system domstate "$VM_NAME" 2>/dev/null || true)
  [[ -n "$state" ]] && printf '%s\n' "$state" || printf 'unavailable\n'
}

unlock_monitor() {
  local attempts=0 state watch_rc
  trap 'stop_unlock_watcher; exit 0' INT TERM
  trap stop_unlock_watcher EXIT
  unlock_monitor_log 'monitor-started'
  while :; do
    state=$(vm_domain_state)
    if [[ "$state" != running ]]; then
      unlock_monitor_log "waiting vm-state=$state"
      sleep 5
      continue
    fi
    rm -f -- "$UNLOCK_MONITOR_READY"
    attempts=$((attempts + 1))
    unlock_monitor_log "console-watch-started attempt=$attempts vm-state=$state"
    unlock_fixture &
    UNLOCK_WATCHER_PID=$!
    if wait "$UNLOCK_WATCHER_PID"; then
      watch_rc=0
    else
      watch_rc=$?
    fi
    UNLOCK_WATCHER_PID=''
    unlock_monitor_log "console-watch-ended attempt=$attempts exit-code=$watch_rc"
    sleep 2
  done
}

start_unlock_monitor() {
  local deadline
  rm -f -- "$UNLOCK_MONITOR_READY"
  unlock_monitor &
  UNLOCK_MONITOR_PID=$!
  deadline=$((SECONDS + LUKS_CONSOLE_READY_SECONDS))
  while ((SECONDS < deadline)); do
    if [[ -f "$UNLOCK_MONITOR_READY" ]]; then
      unlock_monitor_log 'monitor-ready'
      return 0
    fi
    kill -0 "$UNLOCK_MONITOR_PID" 2>/dev/null || break
    sleep 1
  done
  stop_unlock_monitor
  die 'encrypted-console monitor could not attach before certification reboots' 69
}

stop_unlock_watcher() {
  if [[ -n "$UNLOCK_WATCHER_PID" ]] && kill -0 "$UNLOCK_WATCHER_PID" 2>/dev/null; then
    kill "$UNLOCK_WATCHER_PID" 2>/dev/null || true
    wait "$UNLOCK_WATCHER_PID" 2>/dev/null || true
  fi
  UNLOCK_WATCHER_PID=''
}

stop_unlock_monitor() {
  if [[ -n "$UNLOCK_MONITOR_PID" ]] && kill -0 "$UNLOCK_MONITOR_PID" 2>/dev/null; then
    kill "$UNLOCK_MONITOR_PID" 2>/dev/null || true
    wait "$UNLOCK_MONITOR_PID" 2>/dev/null || true
  fi
  UNLOCK_MONITOR_PID=''
}

controller() {
  local command=$1
  shift
  HERMES_CERTIFICATION_MODE=1 \
    HERMES_CERTIFICATION_UNLOCK_LOG="$UNLOCK_MONITOR_LOG" \
    HERMES_DEPLOY_KNOWN_HOSTS="$KNOWN_HOSTS" \
    XDG_STATE_HOME="$RUN_DIR/controller-state" \
    "$CONTROLLER" "$command" \
    --target "$VM_USER@$VM_IP" \
    --identity-file "$IDENTITY_FILE" \
    --management-cidr "$VM_MGMT_CIDR" \
    --interface "$INTERFACE" "$@"
}

run_certification_controller_deploy() {
  local deploy_rc=0 diagnostic diagnostic_tmp status_rc=0 status_tmp
  controller deploy --provider "$PROVIDER" --model "$MODEL" || deploy_rc=$?
  ((deploy_rc != 0)) || return 0

  diagnostic="$RUN_DIR/status-failure.log"
  status_tmp=$(mktemp "$RUN_DIR/.status-failure.XXXXXX")
  diagnostic_tmp=$(mktemp "$RUN_DIR/.status-failure-final.XXXXXX")
  chmod 0600 "$status_tmp" "$diagnostic_tmp"
  controller status >"$status_tmp" 2>&1 || status_rc=$?
  {
    printf 'controller_deploy_exit=%d\n' "$deploy_rc"
    printf 'controller_status_exit=%d\n' "$status_rc"
    cat -- "$status_tmp"
  } >"$diagnostic_tmp"
  mv -- "$diagnostic_tmp" "$diagnostic"
  rm -f -- "$status_tmp"
  printf 'Sanitized controller status retained at %s\n' "$diagnostic" >&2
  return "$deploy_rc"
}

guest_facts() {
  ssh_vm bash -s -- "$EXPECTED_IMAGE" <<'REMOTE_FACTS'
source /etc/os-release
printf 'fedora_version=%s\n' "$VERSION_ID"
printf 'kernel=%s\n' "$(uname -r)"
podman_version=$(podman version --format '{{.Client.Version}}' 2>/dev/null || true)
printf 'podman=%s\n' "$podman_version"
printf 'image=%s\n' "$1"
REMOTE_FACTS
}

revoke_all_providers() {
  local provider rc=0
  for provider in openai-codex openai-api nous; do
    set +e
    controller revoke-auth --provider "$provider"
    local provider_rc=$?
    set -e
    ((provider_rc == 0)) || rc=1
  done
  return "$rc"
}

purge_fresh_data() {
  ssh_vm id hermes >/dev/null 2>&1 || return 0
  printf 'PURGE-HERMES-FRESH\n' | controller rollback --purge-fresh
}

remove_fixture_sudo() {
  printf '%s\n' 'rm -f -- /etc/sudoers.d/lab-hermes-fixture' \
    | ssh_vm sudo -n /usr/bin/bash -s
  ssh_vm test '!' -e /etc/sudoers.d/lab-hermes-fixture
}

verify_unlock_evidence() {
  local summary
  if certification_unlock_evidence_is_valid "$UNLOCK_MONITOR_LOG"; then
    return 0
  fi
  summary=$(certification_unlock_evidence_summary "$UNLOCK_MONITOR_LOG" || true)
  die "encrypted-boot evidence failed closed ($summary)" 78
}

verify_vm_destroyed() {
  ! vm_exists "$VM_NAME" && [[ ! -e "$VM_DISK_PATH" && ! -e "$VM_OEMDRV_PATH" ]]
}

controller_stage_present() {
  local stage=$1
  local state_dir="$RUN_DIR/controller-state/hermes-deploy/lab_172.16.99.12"
  [[ -f "$state_dir/stage-$stage" ]]
}

capture_vm_diagnostics() {
  local diagnostics="$RUN_DIR/vm-failure.log"
  local screenshot="$RUN_DIR/vm-failure-screen.ppm"
  {
    printf 'captured_at=%s\n' "$(date -u +%FT%TZ)"
    printf 'domain_state=%s\n' "$(vm_domain_state)"
    virsh -c qemu:///system dominfo "$VM_NAME"
    virsh -c qemu:///system domblklist "$VM_NAME" --details
    virsh -c qemu:///system domifaddr "$VM_NAME" --source lease
  } >"$diagnostics" 2>&1 || true
  chmod 0600 "$diagnostics"
  if virsh -c qemu:///system screenshot "$VM_NAME" "$screenshot" >/dev/null 2>&1; then
    chmod 0600 "$screenshot"
  else
    rm -f -- "$screenshot"
  fi
  printf 'Certification failure diagnostics retained at %s\n' "$RUN_DIR" >&2
}

cleanup_after_failure() {
  local cleanup_ok=true
  local identity_present=false
  stop_unlock_monitor
  if controller_stage_present identity || ssh_vm id hermes >/dev/null 2>&1; then
    identity_present=true
  fi
  if ! $identity_present && $VM_CREATED; then
    "$VM_CREATOR" --destroy >/dev/null 2>&1 || true
    if verify_vm_destroyed; then
      printf 'Certification failed before Hermes identity creation; VM destruction verified.\n' >&2
      VM_CREATED=false
    else
      cleanup_ok=false
    fi
  elif $identity_present && $VM_CREATED; then
    revoke_all_providers || cleanup_ok=false
    purge_fresh_data || cleanup_ok=false
    remove_fixture_sudo || cleanup_ok=false
    if $cleanup_ok && ssh_vm id hermes >/dev/null 2>&1; then
      cleanup_ok=false
    fi
    if $cleanup_ok; then
      "$VM_CREATOR" --destroy >/dev/null 2>&1 || true
      if verify_vm_destroyed; then
        printf 'Certification failed after credential use; cleanup and VM destruction verified.\n' >&2
        VM_CREATED=false
      else
        cleanup_ok=false
      fi
    fi
  fi
  if $VM_CREATED; then
    "$VM_CREATOR" --destroy >/dev/null 2>&1 || true
    if verify_vm_destroyed; then
      printf 'Certification cleanup was not verifiable before forced VM destruction; destruction verified.\n' >&2
      VM_CREATED=false
    else
      printf 'ERROR: certification cleanup and VM destruction could not be verified.\n' >&2
    fi
  fi
}

cleanup() {
  local rc=$?
  if (($# > 0)); then
    rc=$1
  fi
  if ((rc != 0)) && $VM_CREATED; then
    capture_vm_diagnostics
  fi
  stop_unlock_monitor
  if ((rc == 0)) && $VM_CREATED; then
    "$VM_CREATOR" --destroy >/dev/null 2>&1 || true
  elif ((rc != 0)) && $VM_CREATED; then
    cleanup_after_failure
  fi
  if [[ -n "${SSH_PUBKEY:-}" && "$SSH_PUBKEY" == "$RUN_DIR"/* ]]; then
    rm -f -- "$SSH_PUBKEY"
  fi
  return "$rc"
}
trap cleanup EXIT
trap 'trap - INT EXIT; cleanup 130 || true; kill -INT $$' INT
trap 'trap - TERM EXIT; cleanup 143 || true; kill -TERM $$' TERM

require_cmd python3
require_cmd virsh
require_cmd virt-install
require_cmd qemu-img
require_cmd xorriso
check_kvm
check_libvirt
check_storage_pool_writable /var/lib/libvirt/images
check_hermes_server_host_resources /var/lib/libvirt/images
verify_media
run_offline_tests
check_hermes_server_host_resources /var/lib/libvirt/images

vm_exists "$VM_NAME" && die "certification VM '$VM_NAME' already exists; destroy it before retrying" 73
[[ ! -e "$VM_DISK_PATH" && ! -e "$VM_OEMDRV_PATH" ]] \
  || die 'certification VM storage already exists; destroy it before retrying' 73
VM_CREATED=true
"$VM_CREATOR" --iso "$ISO_PATH" --ssh-key "$SSH_PUBKEY" \
  --unlock-log "$UNLOCK_MONITOR_LOG" >"$RUN_DIR/vm-create.log" 2>&1
start_unlock_monitor
wait_ssh || die 'certification VM did not become reachable over SSH' 69
INTERFACE=$(ssh_vm ip -o -4 route show default | awk '{print $5; exit}')
[[ -n "$INTERFACE" ]] || die 'certification VM management interface was not discovered' 69

printf 'Starting full Hermes provider certification for %s/%s. Credentials remain in the terminal only.\n' \
  "$PROVIDER" "$MODEL" >&2
run_certification_controller_deploy
verify_unlock_evidence
controller status >"$RUN_DIR/status.log"
guest_facts >"$RUN_DIR/guest-facts"
revoke_all_providers
purge_fresh_data
remove_fixture_sudo || die 'temporary VM bootstrap privilege could not be removed' 78
if ssh_vm id hermes >/dev/null 2>&1; then
  die 'fresh Hermes identity remained after certification purge' 78
fi
stop_unlock_monitor
"$VM_CREATOR" --destroy >"$RUN_DIR/vm-destroy.log" 2>&1
verify_vm_destroyed || die 'certification VM or its dedicated storage still exists' 78
printf 'VM_DESTROYED_VERIFIED\n' >&2
VM_CREATED=false

issued_at=$(date -u +%s)
expires_at=$((issued_at + HERMES_PROMOTION_WINDOW_SECONDS))
promotion_id="promotion-$RUN_STAMP"
certification_id="certification-$RUN_STAMP"
artifact_fingerprint=$(promotion_record_fingerprint "$REPO_ROOT") \
  || die 'could not calculate the certification artifact fingerprint' 70
fedora_version=$(sed -n 's/^fedora_version=//p' "$RUN_DIR/guest-facts" | tail -n 1)
kernel=$(sed -n 's/^kernel=//p' "$RUN_DIR/guest-facts" | tail -n 1)
podman=$(sed -n 's/^podman=//p' "$RUN_DIR/guest-facts" | tail -n 1)
[[ "$fedora_version" == 44 && "$kernel" =~ ^[A-Za-z0-9._:+/-]+$ &&
  "$podman" =~ ^[0-9]+\.[0-9]+\.[0-9]+ ]] || die 'guest facts are incomplete for a promotion record' 78

PROMOTION_RECORD_PATH="$STATE_HOME/hermes-certification/$promotion_id.record"
install -d -m 0700 "$(dirname "$PROMOTION_RECORD_PATH")"
umask 077
cat >"$PROMOTION_RECORD_PATH" <<EOF
schema=$HERMES_PROMOTION_SCHEMA
certification_id=$certification_id
promotion_id=$promotion_id
issued_at=$issued_at
expires_at=$expires_at
artifact_fingerprint=$artifact_fingerprint
iso_sha256=$EXPECTED_ISO_SHA256
iso_signature=verified
fedora_version=$fedora_version
kernel=$kernel
podman=$podman
hermes_image=$EXPECTED_IMAGE
provider=$PROVIDER
model=$MODEL
inference_result=HERMES_OK
credentials_revoked=true
data_purged=true
vm_destroyed=true
EOF
chmod 0600 "$PROMOTION_RECORD_PATH"
promotion_record_validate "$PROMOTION_RECORD_PATH" "$PROVIDER" "$MODEL" "$EXPECTED_IMAGE" \
  "$artifact_fingerprint" || die 'generated promotion record failed strict validation' 70
printf 'PROMOTION_RECORD=%s\n' "$(realpath "$PROMOTION_RECORD_PATH")"
