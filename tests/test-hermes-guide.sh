#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC1091,SC2034
# Offline consistency checks for the Fedora Server Hermes implementation.

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

# Consumed by the sourced output helpers.
VERBOSE=false
[[ "${1:-}" == -v ]] && VERBOSE=true

readonly GUIDE="$REPO_ROOT/hermes-fedora-server-install-guide.html"
readonly DEPLOY="$REPO_ROOT/hermes-deploy.sh"
readonly DEPLOY_LIB="$REPO_ROOT/scripts/hermes/deploy-lib.sh"
readonly CERTIFIER="$REPO_ROOT/hermes-certify-vm.sh"
readonly REMOTE_STATE="$REPO_ROOT/scripts/hermes/remote-state.sh"
readonly REMOTE_PREFLIGHT="$REPO_ROOT/scripts/hermes/remote-preflight.sh"
readonly HOST_MODULE="$REPO_ROOT/scripts/hermes/fedora-server-host.sh"
readonly AUTH_MODULE="$REPO_ROOT/scripts/hermes/provider-auth-status.sh"
readonly CERT_EVIDENCE="$REPO_ROOT/scripts/hermes/certification-evidence.sh"
readonly PROMOTION_MODULE="$REPO_ROOT/scripts/hermes/promotion-record.sh"
readonly ACCEPTANCE="$REPO_ROOT/scripts/hermes/acceptance.sh"
readonly ROOT_ACCEPTANCE="$REPO_ROOT/scripts/hermes/root-acceptance.sh"
readonly STATUS_WRAPPER="$REPO_ROOT/scripts/hermes/wrappers/hermes-status"
readonly VM_CREATOR="$REPO_ROOT/vm/create-hermes-server-vm.sh"
readonly LUKS_CONSOLE="$REPO_ROOT/vm/lib-hermes-luks-console.sh"
readonly LUKS_CONSOLE_HELPER="$REPO_ROOT/vm/hermes-luks-console.py"
readonly KICKSTART="$REPO_ROOT/vm/kickstart/fedora-server.ks"
readonly VM_COMMON="$REPO_ROOT/vm/lib-vm-common.sh"
readonly E2E_VM="$REPO_ROOT/tests/test-hermes-e2e-vm.sh"
readonly LINKS="$REPO_ROOT/tests/test-hermes-links.sh"
readonly PLAN="$REPO_ROOT/docs/HERMES_DEPLOYMENT_PLAN.md"
readonly HANDOFF="$REPO_ROOT/docs/HERMES_ONE_COMMAND_DEPLOYMENT_HANDOFF.md"
readonly VERIFICATION="$REPO_ROOT/docs/HERMES_INSTALLATION_VERIFICATION.md"
readonly SECURITY_PLAN="$REPO_ROOT/secure-hermes-installation-plan.html"
readonly VM_GUIDE="$REPO_ROOT/docs/VM_TESTING_GUIDE.md"
readonly AGENTS_MD="$REPO_ROOT/AGENTS.md"
# The source repository wired its guide checks into Lefthook. Lefthook is retired
# here; the successors are the pre-push hook and the single offline entrypoint it
# runs. These two bindings keep the original intent of the assertion below.
readonly PRECOMMIT="$REPO_ROOT/.pre-commit-config.yaml"
readonly OFFLINE_CHECKS="$REPO_ROOT/toolbox/run-offline-checks.sh"
readonly HOOK_WIRING="$REPO_ROOT/tests/check_hook_wiring.py"

for required in "$GUIDE" "$DEPLOY" "$DEPLOY_LIB" "$CERTIFIER" "$REMOTE_STATE" \
  "$REMOTE_PREFLIGHT" "$HOST_MODULE" "$AUTH_MODULE" "$CERT_EVIDENCE" "$PROMOTION_MODULE" "$ACCEPTANCE" \
  "$ROOT_ACCEPTANCE" "$STATUS_WRAPPER" "$VM_CREATOR" "$LUKS_CONSOLE" "$LUKS_CONSOLE_HELPER" \
  "$KICKSTART" "$VM_COMMON" \
  "$E2E_VM" "$LINKS" "$PLAN" "$HANDOFF" "$VERIFICATION" "$SECURITY_PLAN" "$VM_GUIDE" \
  "$AGENTS_MD" "$PRECOMMIT" "$OFFLINE_CHECKS" "$HOOK_WIRING"; do
  if [[ -f "$required" ]]; then
    _pass "required artifact exists: $(basename "$required")"
  else
    _fail "required artifact exists: $required"
  fi
done

section 'Fedora Server source of truth'
assert_grep '^<!doctype html>' "$GUIDE" 'Server guide begins with doctype'
assert_grep 'Fedora Server 44' "$GUIDE" 'Guide names Fedora Server 44'
assert_grep 'Fedora-Server-dvd-x86_64-44-1.7.iso' "$GUIDE" 'Guide names Server DVD'
assert_grep '85837793bfa36db6bc709b4cecd2ec116951b87d9c53c3d95eb2fac8dcf7cf1f' "$GUIDE" \
  'Guide pins the official Server DVD checksum'
assert_grep 'gpgv' "$CERTIFIER" 'Certifier verifies the signed checksum locally'
assert_grep 'HERMES_PROMOTION_WINDOW_SECONDS' "$PROMOTION_MODULE" 'Promotion window is code-defined'
assert_grep '86400' "$PROMOTION_MODULE" 'Promotion window is 24 hours'
assert_grep 'dnf5 upgrade --offline' "$HOST_MODULE" 'Host module uses DNF5 offline update'
assert_grep 'dnf5 offline reboot' "$HOST_MODULE" 'Host module starts the offline transaction reboot'
assert_grep 'dnf5 offline log' "$HOST_MODULE" 'Host module verifies the offline transaction log'
assert_grep 'fedora_server_offline_update_pending' "$HOST_MODULE" 'Host module handles no-update transactions'
assert_grep 'download_updates = True' "$HOST_MODULE" 'Host module enables update downloads'
assert_grep 'apply_updates = False' "$HOST_MODULE" 'Host module disables automatic application'
assert_grep 'reboot = never' "$HOST_MODULE" 'Host module disables automatic reboot'

section 'Public controller contract'
assert_grep 'deploy\|configure-provider\|check\|status\|rollback\|revoke-auth\|adopt-host' "$DEPLOY_LIB" \
  'Controller exposes the Server command grammar'
assert_grep '--promotion-record PATH' "$DEPLOY_LIB" 'Controller documents promotion records'
assert_grep 'adopt_host_command' "$DEPLOY_LIB" 'Controller implements adopt-host'
assert_grep 'ADOPT-HERMES-HOST' "$DEPLOY_LIB" 'Host adoption has typed confirmation'
assert_grep 'CONFIRM-HERMES-PRODUCTION' "$DEPLOY_LIB" 'Production mutation has typed confirmation'
assert_grep 'XDG_STATE_HOME' "$DEPLOY_LIB" 'Controller supports XDG state'
assert_grep '\.local/state' "$DEPLOY_LIB" 'Controller defaults state below .local/state'
assert_grep 'PROMOTION_BOUND' "$DEPLOY_LIB" 'Controller binds the first production host'
assert_grep 'promotion record is expired before first production use' "$DEPLOY_LIB" \
  'Controller rejects an expired first-use record'
assert_grep 'same production host' "$DEPLOY_LIB" 'Controller permits same-host recertification/resume'
assert_no_grep 'renew-risk|--days|risk|trivy|kinoite|rpm-ostree' "$DEPLOY_LIB" \
  'Controller has no retired risk or Kinoite interface'

section 'Remote Server lifecycle'
assert_grep 'Fedora Server 44 host' "$REMOTE_PREFLIGHT" 'Preflight detects Fedora Server'
assert_grep 'HERMES_SERVER_MIN_PODMAN' "$REMOTE_PREFLIGHT" 'Preflight uses Server package contract'
assert_grep 'fedora_server_install_prerequisites' "$REMOTE_STATE" 'Remote state installs prerequisites through host module'
assert_grep 'fedora_server_configure_automatic_updates' "$REMOTE_STATE" 'Remote state converges automatic update policy'
assert_grep 'fedora_server_disable_cockpit' "$REMOTE_STATE" 'Remote state disables Cockpit'
assert_grep 'dnf5-automatic.timer' "$REMOTE_STATE" 'Remote state manages DNF5 automatic timer'
assert_grep 'host-identity' "$REMOTE_STATE" 'Remote state exposes host identity'
assert_no_grep 'risk|trivy|kinoite|rpm-ostree' "$REMOTE_STATE" 'Remote state has no retired machinery'
assert_no_grep 'risk|trivy|kinoite|rpm-ostree' "$REMOTE_PREFLIGHT" 'Preflight has no retired machinery'
assert_no_grep 'risk|trivy|kinoite|rpm-ostree' "$ACCEPTANCE" 'Acceptance has no retired machinery'
assert_no_grep 'risk|trivy|kinoite|rpm-ostree' "$ROOT_ACCEPTANCE" 'Root acceptance has no retired machinery'
assert_grep 'Fedora Server 44' "$ACCEPTANCE" 'Application acceptance names Server platform'
assert_grep 'download-only dnf5-automatic timer enabled' "$ROOT_ACCEPTANCE" 'Root acceptance checks update policy'

section 'Authentication and provider safety'
assert_grep 'grep -Fqx' "$AUTH_MODULE" 'Auth status parser anchors the exact line'
assert_grep 'provider_auth_status_logged_in' "$REMOTE_STATE" 'Remote state uses shared auth parser'
assert_grep 'provider_auth_status_logged_in' "$ACCEPTANCE" 'Acceptance uses shared auth parser'
for provider in openai-codex openai-api nous; do
  assert_grep "$provider" "$DEPLOY_LIB" "Controller supports $provider"
done
assert_grep 'auth_type=api-key' "$REMOTE_STATE" 'API provider uses Hermes masked prompt'
assert_no_grep 'api-key.*=' "$DEPLOY_LIB" 'Controller has no API-key argument'
assert_no_grep 'auth add.*--api-key' "$REMOTE_STATE" 'Remote state has no API-key argument'
assert_grep 'provider credentials remain active' "$REMOTE_STATE" 'Credential cleanup verifies logout'
assert_grep 'inference_result=HERMES_OK' "$CERTIFIER" 'Certifier requires exact HERMES_OK record value'
assert_grep 'AUTHENTICATION_READY provider=' "$DEPLOY_LIB" \
  'Certification exposes a secret-free provider readiness marker'
assert_grep 'START-AUTH' "$DEPLOY_LIB" \
  'Certification waits for typed operator readiness before provider authentication'
assert_order 'verify_certification_unlock_evidence' 'AUTHENTICATION_READY provider=' "$DEPLOY_LIB" \
  'Certification validates encrypted boots before exposing the authentication gate'
assert_no_grep 'DEBUG-hermes-inference' "$ACCEPTANCE" 'Temporary inference instrumentation is removed'

section 'VM certification and cleanup'
assert_grep "VM_NAME='lab-hermes-server'" "$VM_CREATOR" 'Server VM name is canonical'
assert_grep 'HERMES_SERVER_DEFAULT_RAM' "$VM_CREATOR" 'Server VM uses 8 GiB contract'
assert_grep 'HERMES_SERVER_DEFAULT_VCPUS' "$VM_CREATOR" 'Server VM uses 2 vCPU contract'
assert_grep 'qemu-img create.*40G' "$VM_CREATOR" 'Server VM creates a 40 GiB disk'
assert_grep '172.16.99.12' "$VM_CREATOR" 'Server VM uses the static lab IP'
assert_grep 'secure-boot' "$VM_CREATOR" 'Server VM enables Secure Boot'
assert_grep '--location.*ISO_PATH' "$VM_CREATOR" \
  'Server VM boots the verified installer image directly'
assert_grep 'inst\.ks=hd:LABEL=OEMDRV:/ks\.cfg' "$VM_CREATOR" \
  'Server VM passes the kickstart location explicitly'
assert_no_grep 'send-key.*KEY_(UP|ENTER)' "$VM_CREATOR" \
  'Server VM installation does not depend on timed boot-menu input'
assert_grep '--encrypted' "$KICKSTART" 'Server kickstart enables LUKS'
assert_grep '^bootloader --append="rd.auto=1 console=tty0 console=ttyS0,115200n8"$' "$KICKSTART" \
  'Server kickstart persists encrypted-root discovery for future kernels'
assert_grep 'def prompt_is_verified' "$LUKS_CONSOLE_HELPER" \
  'LUKS console input requires an exact prompt classifier'
assert_grep 'pty\.fork' "$LUKS_CONSOLE_HELPER" \
  'LUKS console helper allocates a controlling PTY'
assert_grep '--ready-file' "$LUKS_CONSOLE_HELPER" \
  'LUKS console helper exposes a confirmed-attachment handshake'
assert_grep 'luks-console-attached input-submitted=0' "$LUKS_CONSOLE_HELPER" \
  'LUKS console helper records its attachment without submitting input'
assert_grep 'prompt_armed' "$LUKS_CONSOLE_HELPER" \
  'LUKS console helper tracks whether a reboot-time prompt is armed'
assert_grep 'BOOT_BOUNDARY_LINE' "$LUKS_CONSOLE_HELPER" \
  'LUKS console helper rearms only at an explicit per-boot boundary'
assert_grep 'Starting.*systemd-cryptsetup@luks' "$LUKS_CONSOLE_HELPER" \
  'LUKS console helper rearms on the encrypted-root cryptsetup start despite terminal repaint prefixes'
assert_no_grep 'Reached target paths\\.target - Path Units\\.' "$LUKS_CONSOLE_HELPER" \
  'LUKS console helper ignores the duplicated path-units progress marker'
assert_grep 'luks-boot-boundary-observed input-submitted=0' "$LUKS_CONSOLE_HELPER" \
  'LUKS console helper records each trusted reboot boundary'
assert_grep 'certification_unlock_evidence_is_valid' "$CERT_EVIDENCE" \
  'Certification evidence rejects missing or duplicate reboot submissions'
assert_grep 'require_cmd python3' "$VM_CREATOR" \
  'Server VM creator checks the PTY helper runtime'
assert_grep 'hermes_luks_console_unlock' "$VM_CREATOR" \
  'Initial VM boot uses prompt-gated LUKS input'
assert_grep 'hermes_luks_console_watch' "$CERTIFIER" \
  'Certification reboots share one persistent prompt-gated LUKS watcher'
assert_grep 'monitor-ready' "$CERTIFIER" \
  'Certification confirms a persistent console attachment before deployment'
assert_no_grep "sleep 30" "$CERTIFIER" \
  'Certification does not delay console attachment until after the reboot prompt'
assert_grep '--unlock-log.*UNLOCK_MONITOR_LOG' "$CERTIFIER" \
  'Initial boot retains classified LUKS console events'
assert_no_grep 'LUKS_KEYCODES|KEY_H KEY_E KEY_R' "$VM_CREATOR" \
  'VM creation has no blind LUKS keyboard sequence'
assert_no_grep 'KEY_H KEY_E KEY_R' "$CERTIFIER" \
  'Certification monitoring has no blind LUKS keyboard sequence'
assert_grep '^hostonly_cmdline="yes"$' "$KICKSTART" \
  'Server initramfs embeds its discovered encrypted-root command line'
assert_grep 'dnf5-plugin-automatic' "$HOST_MODULE" 'Server host module installs update plugin'
assert_grep 'revoke_all_providers' "$CERTIFIER" 'Certifier revokes all providers'
assert_grep 'purge_fresh_data' "$CERTIFIER" 'Certifier purges fresh data'
assert_grep 'remove_fixture_sudo' "$CERTIFIER" 'Certifier removes fixture bootstrap privilege'
assert_grep 'ssh_vm sudo -n /usr/bin/bash -s' "$CERTIFIER" \
  'Fixture cleanup uses the exact command authorized by the disposable sudo rule'
assert_grep 'VM_CREATED=false' "$CERTIFIER" 'Certifier tracks destruction before record issuance'
assert_grep 'unlock-monitor.log' "$CERTIFIER" 'Certifier records encrypted reboot unlock attempts'
assert_grep 'HERMES_CERTIFICATION_UNLOCK_LOG' "$CERTIFIER" \
  'Certifier shares its secret-free unlock evidence with the controller gate'
assert_order '^run_certification_controller_deploy$' '^verify_unlock_evidence$' "$CERTIFIER" \
  'Certifier revalidates encrypted-boot evidence before promotion work'
assert_grep 'capture_vm_diagnostics' "$CERTIFIER" 'Certifier captures VM state before failure cleanup'
assert_grep 'flock -n' "$CERTIFIER" 'Certifier rejects concurrent certification runs'
assert_grep 'another Hermes certification is already active' "$CERTIFIER" \
  'Concurrent certification failure is explicit'
assert_grep 'controller_stage_present identity' "$CERTIFIER" \
  'Failure cleanup uses durable controller identity state'
assert_grep 'hermes_reboot_reconnect_attempts' "$DEPLOY_LIB" \
  'Encrypted certification reboot has an explicit reconnect budget'
assert_grep 'ConnectTimeout=2' "$DEPLOY_LIB" \
  'Reconnect probes cannot exceed the declared reboot deadline'
assert_order 'VM_CREATED=true' 'vm-create.log' "$CERTIFIER" \
  'Certifier arms cleanup before VM creation'
assert_order 'vm-destroy.log' 'PROMOTION_RECORD_PATH=' "$CERTIFIER" \
  'Promotion record is generated after VM destruction'
assert_order 'verify_vm_destroyed' 'VM_DESTROYED_VERIFIED' "$CERTIFIER" \
  'Promotion record requires verified VM destruction'
assert_no_grep 'with-trivy|risk|kinoite|ostree' "$CERTIFIER" 'Certifier has no retired options'
if [[ ! -e "$REPO_ROOT/vm/create-kinoite-vm.sh" ]]; then
  _pass 'obsolete Kinoite creator removed'
else
  _fail 'obsolete Kinoite creator removed'
fi
if [[ ! -e "$REPO_ROOT/vm/kickstart/kinoite.ks" ]]; then
  _pass 'obsolete Kinoite kickstart removed'
else
  _fail 'obsolete Kinoite kickstart removed'
fi
if [[ ! -e "$REPO_ROOT/hermes-kinoite-install-guide.html" ]]; then
  _pass 'obsolete Kinoite guide removed'
else
  _fail 'obsolete Kinoite guide removed'
fi

section 'Documentation and secret hygiene'
assert_grep 'hermes-certify-vm.sh' "$HANDOFF" 'Handoff documents the certifier'
assert_grep 'adopt-host' "$HANDOFF" 'Handoff documents host adoption'
assert_grep 'promotion-record' "$HANDOFF" 'Handoff documents promotion records'
assert_grep 'Fedora Server 44' "$SECURITY_PLAN" 'Security plan names Fedora Server'
assert_no_grep 'trivy|kinoite|rpm-ostree|risk' "$SECURITY_PLAN" 'Security plan has no retired promotion machinery'
assert_grep 'hermes-certify-vm.sh' "$VM_GUIDE" 'VM guide documents Server certification'
assert_grep 'START-AUTH' "$GUIDE" 'Server guide documents provider readiness confirmation'
assert_grep 'START-AUTH' "$HANDOFF" 'Handoff documents provider readiness confirmation'
assert_grep 'START-AUTH' "$VM_GUIDE" 'VM guide documents provider readiness confirmation'
assert_grep 'ENCRYPTED_REBOOT_EVIDENCE_OK watched_boots=3' "$GUIDE" \
  'Server guide documents the fail-closed encrypted-boot gate'
assert_grep 'cryptsetup start is the per-boot boundary' "$VM_GUIDE" \
  'VM guide documents trusted watcher re-arming'
assert_grep 'run-20260831T054115Z' "$VERIFICATION" \
  'Verification record identifies the latest failed certification run'
assert_grep 'initial=1 watched=3 boundaries=3 monitor_ready=1' "$VERIFICATION" \
  'Verification record documents the exact unlock-evidence contract'
assert_no_grep 'independent console-unlock monitor|retries the unlock every 30 seconds' "$VM_GUIDE" \
  'VM guide describes the persistent watcher contract'
assert_no_grep 're-arms after meaningful console progress' "$VM_GUIDE" \
  'VM guide does not document the unsafe progress-based re-arm rule'
assert_no_grep 'trivy|kinoite|rpm-ostree|risk' "$VM_GUIDE" 'VM guide has no retired promotion machinery'
assert_grep 'hermes-fedora-server-install-guide.html' "$AGENTS_MD" 'Repository guidance names Server guide'

# Structural wiring, not string presence: a comment cannot satisfy these, and
# removed or wrong hook wiring is rejected. The --self-test run additionally
# proves the checker rejects each known mutation (removed hook, wrong entry,
# wrong stage, wrong always_run/pass_filenames, duplicate id, commented-out guide
# invocation, unittest discovery instead of the reviewed allowlist).
if python3 "$HOOK_WIRING" --quiet; then
  _pass 'pre-push hook structurally runs the offline entrypoint and the guide gate'
else
  _fail 'pre-push hook structurally runs the offline entrypoint and the guide gate'
fi
if python3 "$HOOK_WIRING" --self-test --quiet; then
  _pass 'hook-wiring negative controls reject removed or wrong wiring'
else
  _fail 'hook-wiring negative controls reject removed or wrong wiring'
fi
assert_grep 'test-hermes-e2e-vm' "$E2E_VM" 'VM E2E names its own runner'
for file in "$GUIDE" "$DEPLOY" "$DEPLOY_LIB" "$CERTIFIER" "$REMOTE_STATE" "$REMOTE_PREFLIGHT" \
  "$HOST_MODULE" "$AUTH_MODULE" "$CERT_EVIDENCE" "$PROMOTION_MODULE" "$ACCEPTANCE" "$ROOT_ACCEPTANCE" \
  "$STATUS_WRAPPER" "$VM_CREATOR" "$LUKS_CONSOLE" "$LUKS_CONSOLE_HELPER" "$KICKSTART" \
  "$HANDOFF" "$PLAN" "$VERIFICATION" \
  "$SECURITY_PLAN" "$VM_GUIDE"; do
  filename=$(basename "$file")
  assert_no_grep 'sk-[A-Za-z0-9_-]{20,}|sk-or-v1-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}' "$file" \
    "$filename has no common API/token literal"
  assert_no_grep 'BEGIN [A-Z ]*PRIVATE KEY' "$file" "$filename has no private key"
  assert_no_grep 'NOPASSWD:[[:space:]]+ALL' "$file" "$filename has no arbitrary sudo grant"
done

print_summary
