#!/usr/bin/env bash
# shellcheck shell=bash
#
# SUPERSEDED — DO NOT USE. Kept only as the historical source reviewed and rejected during preparation.
#
# The preparation guide holds this script ("Incorrectly broad crypttab edits, weak readiness inference,
# automatic resealing behavior, and boot-policy scope conflicts"), and the boot-automation design rejects it
# for the same crypttab-rewriting defect. The supported procedure is now
# `boot/tpm-enroll.sh` (PCR 7:sha256, no PIN, single-record crypttab edit, revert path), designed and
# proven under gates B3–B4; see docs/HERMES_BOOT_AUTOMATION.md and docs/HERMES_BOOT_CLEAN_INSTALL.md.
#
# It previously advertised itself as implementing a TPM auto-unlock document that does not exist anywhere
# in this repository; that dangling reference is removed rather than repaired.
#
# Configure TPM 2.0 LUKS Auto-Unlock using systemd-cryptenroll.
#
# Supports standard Fedora / RHEL (dracut) and Fedora Atomic (rpm-ostree).
# Idempotent — safe to run multiple times.
#
# Actions performed:
#   1. Pre-flight verification (TPM2 hardware, LUKS2 version, PCR availability)
#   2. Backup and update /etc/crypttab to append tpm2-device=auto
#   3. Initramfs verification & regeneration (dracut on non-ostree systems)
#   4. Enroll TPM 2.0 token (systemd-cryptenroll with PCRs 0+7 by default)
#   5. Header & token verification via cryptsetup luksDump
#
# Usage:
#   sudo ./configure-tpm2-auto-unlock.sh [OPTIONS]
#   ./configure-tpm2-auto-unlock.sh --help
#   ./configure-tpm2-auto-unlock.sh --check
#   ./configure-tpm2-auto-unlock.sh --dry-run
#
# See --help for all options and examples.

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s nullglob

if ((BASH_VERSINFO[0] < 5 || (BASH_VERSINFO[0] == 5 && BASH_VERSINFO[1] < 2))); then
  printf 'ERROR: This script requires Bash 5.2 or newer. Current: %s\n' "$BASH_VERSION" >&2
  exit 69
fi

# Use color only for an interactive terminal and honor the NO_COLOR convention.
if [[ -t 2 && -z "${NO_COLOR:-}" ]]; then
  readonly RED=$'\033[0;31m'
  readonly GREEN=$'\033[0;32m'
  readonly YELLOW=$'\033[1;33m'
  readonly BLUE=$'\033[0;34m'
  readonly BOLD=$'\033[1m'
  readonly NC=$'\033[0m'
else
  readonly RED=''
  readonly GREEN=''
  readonly YELLOW=''
  readonly BLUE=''
  readonly BOLD=''
  readonly NC=''
fi

log_info() { printf '%s[INFO]%s %s\n' "$GREEN" "$NC" "$1" >&2; }
log_warn() { printf '%s[WARN]%s %s\n' "$YELLOW" "$NC" "$1" >&2; }
log_error() { printf '%s[ERROR]%s %s\n' "$RED" "$NC" "$1" >&2; }
log_step() { printf '\n%s==>%s %s%s%s\n' "$BLUE" "$NC" "$BOLD" "$1" "$NC" >&2; }

report_unhandled_error() {
  local exit_code=$?
  log_error "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}:${BASH_LINENO[0]}: '${BASH_COMMAND}' exited with code $exit_code"
  return "$exit_code"
}
trap report_unhandled_error ERR

# Configuration variables
DEVICE=""
PCRS="0+7"
CHECK_ONLY=false
DRY_RUN=false
FORCE_REENROLL=false
UNLOCK_KEY_FILE=""
CRYPTTAB_PATH="/etc/crypttab"

show_help() {
  cat <<'HELP_EOF'
Usage:
  sudo ./configure-tpm2-auto-unlock.sh [OPTIONS]

Options:
  -d, --device PATH        Target LUKS block device (e.g. /dev/nvme0n1p3).
                           Auto-detected if not specified.
  -p, --pcrs LIST          PCR registers to bind (default: 0+7).
  -k, --unlock-key-file F  Path to keyfile to unlock LUKS for enrollment non-interactively.
  -f, --force-reenroll     Wipe existing TPM2 keyslot before enrolling a new one.
  -c, --check              Verify prerequisites and current TPM2 LUKS status without making changes.
  -n, --dry-run            Simulate operations without modifying crypttab, initramfs, or LUKS tokens.
  -h, --help               Display this help message and exit.

Environment Variables:
  PASSWORD                 Current LUKS passphrase (enables non-interactive enrollment).

Examples:
  # Check system compatibility and status:
  ./configure-tpm2-auto-unlock.sh --check

  # Interactive enrollment:
  sudo ./configure-tpm2-auto-unlock.sh

  # Non-interactive enrollment using PASSWORD env var:
  sudo PASSWORD="MySecretPassphrase" ./configure-tpm2-auto-unlock.sh

  # Explicit device and re-enrollment:
  sudo ./configure-tpm2-auto-unlock.sh --device /dev/nvme0n1p3 --force-reenroll
HELP_EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -d | --device)
        [[ -n "${2:-}" ]] || {
          log_error "Option '$1' requires an argument."
          exit 2
        }
        DEVICE="$2"
        shift 2
        ;;
      -p | --pcrs)
        [[ -n "${2:-}" ]] || {
          log_error "Option '$1' requires an argument."
          exit 2
        }
        PCRS="$2"
        shift 2
        ;;
      -k | --unlock-key-file)
        [[ -n "${2:-}" ]] || {
          log_error "Option '$1' requires an argument."
          exit 2
        }
        UNLOCK_KEY_FILE="$2"
        shift 2
        ;;
      -f | --force-reenroll)
        FORCE_REENROLL=true
        shift
        ;;
      -c | --check)
        CHECK_ONLY=true
        shift
        ;;
      -n | --dry-run)
        DRY_RUN=true
        shift
        ;;
      -h | --help)
        show_help
        exit 0
        ;;
      *)
        log_error "Unknown option: $1"
        show_help
        exit 2
        ;;
    esac
  done
}

detect_target_device() {
  if [[ -n "$DEVICE" ]]; then
    if [[ ! -b "$DEVICE" ]]; then
      log_error "Specified device '$DEVICE' does not exist or is not a block device."
      exit 1
    fi
    return 0
  fi

  # 1. Search for root filesystem underlying LUKS device
  local root_dev
  root_dev=$(findmnt -n -o SOURCE / 2>/dev/null || true)
  if [[ -n "$root_dev" ]]; then
    local dm_name
    dm_name=$(basename "$root_dev")

    local candidates=()
    while IFS= read -r dev; do
      [[ -n "$dev" ]] && candidates+=("$dev")
    done < <(lsblk -rn -o PATH,FSTYPE | awk '$2=="crypto_LUKS" {print $1}')

    if [[ ${#candidates[@]} -eq 1 ]]; then
      DEVICE="${candidates[0]}"
      log_info "Auto-detected encrypted partition: $DEVICE"
      return 0
    elif [[ ${#candidates[@]} -gt 1 ]]; then
      for cand in "${candidates[@]}"; do
        if lsblk -rn -o PATH "$cand" 2>/dev/null | grep -qw "$dm_name"; then
          DEVICE="$cand"
          log_info "Auto-detected root encrypted partition: $DEVICE"
          return 0
        fi
      done
      log_error "Multiple crypto_LUKS devices found: ${candidates[*]}. Please specify with --device."
      exit 1
    fi
  fi

  # Fallback: check /etc/crypttab if readable
  if [[ -r "$CRYPTTAB_PATH" ]]; then
    local crypt_src
    crypt_src=$(awk '!/^#/ && NF>=2 {print $2; exit}' "$CRYPTTAB_PATH" || true)
    if [[ -n "$crypt_src" ]]; then
      if [[ "$crypt_src" =~ ^UUID= ]]; then
        local uuid="${crypt_src#UUID=}"
        local dev_by_uuid
        dev_by_uuid=$(blkid -t "UUID=$uuid" -o device 2>/dev/null || true)
        if [[ -n "$dev_by_uuid" && -b "$dev_by_uuid" ]]; then
          DEVICE="$dev_by_uuid"
          log_info "Auto-detected device from crypttab UUID: $DEVICE"
          return 0
        fi
      elif [[ -b "$crypt_src" ]]; then
        DEVICE="$crypt_src"
        log_info "Auto-detected device from crypttab path: $DEVICE"
        return 0
      fi
    fi
  fi

  log_error "Could not auto-detect target LUKS partition. Please specify with --device <path>."
  exit 1
}

preflight_checks() {
  log_step "1. Running Pre-Flight Verification"

  # Check required tools
  local missing_tools=()
  for tool in systemd-cryptenroll lsblk; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      missing_tools+=("$tool")
    fi
  done
  if [[ ${#missing_tools[@]} -gt 0 ]]; then
    log_error "Missing required utilities: ${missing_tools[*]}"
    exit 1
  fi

  # Check TPM 2.0 device
  if [[ ! -e "/dev/tpmrm0" && ! -e "/dev/tpm0" ]]; then
    log_error "No TPM device found at /dev/tpmrm0 or /dev/tpm0. Verify TPM 2.0 is enabled in BIOS/UEFI."
    exit 1
  fi

  local tpm_list
  tpm_list=$(systemd-cryptenroll --tpm2-device=list 2>&1 || true)
  if [[ "$tpm_list" != *"/dev/tpmrm0"* && "$tpm_list" != *"/dev/tpm0"* ]]; then
    log_error "systemd-cryptenroll did not detect a supported TPM 2.0 device."
    printf '%s\n' "$tpm_list" >&2
    exit 1
  fi
  log_info "TPM 2.0 hardware confirmed (/dev/tpmrm0)."

  # Detect target device
  detect_target_device

  # Check LUKS version (supports non-root check via lsblk and root check via cryptsetup)
  local is_luks2=false
  local lsblk_ver
  lsblk_ver=$(lsblk -rn -o PATH,FSTYPE,FSVER "$DEVICE" 2>/dev/null | awk '$1=="'"$DEVICE"'" {print $3}' || true)
  if [[ "$lsblk_ver" == "2" ]]; then
    is_luks2=true
  elif command -v cryptsetup >/dev/null 2>&1 && [[ $EUID -eq 0 ]]; then
    if cryptsetup isLuks --type luks2 "$DEVICE" 2>/dev/null; then
      is_luks2=true
    fi
  fi

  if ! "$is_luks2"; then
    log_error "Device '$DEVICE' is not recognized as a LUKS2 partition. systemd-cryptenroll requires LUKS2 format."
    exit 1
  fi
  log_info "Partition '$DEVICE' is verified LUKS2."

  # Check PCR registers
  if command -v systemd-analyze >/dev/null 2>&1; then
    local pcrs_active
    pcrs_active=$(systemd-analyze pcrs 2>&1 || true)
    if [[ -n "$pcrs_active" ]]; then
      log_info "TPM PCR registers are active (Binding target: $PCRS)."
    fi
  fi
}

check_tpm_token_status() {
  log_step "2. Checking Current LUKS Tokens and Keyslots"

  local has_tpm=false
  local checked_header=false
  local tpm_valid=false
  local tpm_tested=false

  if [[ $EUID -eq 0 ]] && command -v cryptsetup >/dev/null 2>&1; then
    local dump_output
    dump_output=$(cryptsetup luksDump "$DEVICE" 2>&1 || true)
    checked_header=true
    if [[ "$dump_output" =~ systemd-tpm2 ]]; then
      has_tpm=true
      log_info "TPM 2.0 token already present in LUKS header for $DEVICE."

      # Live unseal test against current active PCR measurements
      tpm_tested=true
      local test_output
      if test_output=$(cryptsetup --test-passphrase open "$DEVICE" </dev/null 2>&1); then
        tpm_valid=true
        log_info "TPM 2.0 unseal test: PASSED (active system PCR state matches token policy)."
      else
        tpm_valid=false
        if [[ "$test_output" =~ "TPM policy does not match" ]]; then
          log_warn "TPM 2.0 token policy MISMATCH: system firmware/UEFI or Secure Boot state changed."
          log_warn "Disk cannot auto-unlock with current token and will prompt for passphrase on boot."
        else
          log_warn "TPM 2.0 unseal test FAILED."
        fi
      fi
    else
      log_info "No TPM 2.0 token found yet in LUKS header."
    fi
  else
    log_warn "LUKS header inspection and live token testing require root privileges (sudo)."
  fi

  local crypttab_ok=false
  if [[ -r "$CRYPTTAB_PATH" ]]; then
    if grep -E "tpm2-device=" "$CRYPTTAB_PATH" >/dev/null 2>&1; then
      crypttab_ok=true
      log_info "tpm2-device option already present in $CRYPTTAB_PATH."
    else
      log_warn "tpm2-device option NOT present in $CRYPTTAB_PATH."
    fi
  else
    log_warn "Cannot read $CRYPTTAB_PATH without root privileges."
  fi

  if "$CHECK_ONLY"; then
    printf '\n%s--- Status Summary ---%s\n' "$BOLD" "$NC"
    printf 'Device:             %s\n' "$DEVICE"
    printf 'LUKS Version:       LUKS2 (Valid)\n'
    printf 'TPM Device:         /dev/tpmrm0 (Available)\n'
    if "$checked_header"; then
      if "$has_tpm"; then
        if "$tpm_tested"; then
          if "$tpm_valid"; then
            printf 'TPM Token Enrolled: true (Policy: VALID)\n'
          else
            printf 'TPM Token Enrolled: true (Policy: MISMATCH / OUT-OF-DATE)\n'
          fi
        else
          printf 'TPM Token Enrolled: true\n'
        fi
      else
        printf 'TPM Token Enrolled: false\n'
      fi
    else
      printf 'TPM Token Enrolled: (Requires sudo to inspect)\n'
    fi
    if [[ -r "$CRYPTTAB_PATH" ]]; then
      printf 'Crypttab Config:    %s\n' "$crypttab_ok"
    else
      printf 'Crypttab Config:    (Requires sudo to inspect)\n'
    fi

    if "$checked_header" && "$has_tpm" && "$crypttab_ok"; then
      if "$tpm_tested" && ! "$tpm_valid"; then
        printf '%sStatus: RE-ENROLLMENT REQUIRED (Run with sudo --force-reenroll)%s\n\n' "$RED" "$NC"
      else
        printf '%sStatus: AUTO-UNLOCK READY%s\n\n' "$GREEN" "$NC"
      fi
    else
      printf '%sStatus: READY FOR ENROLLMENT (Run with sudo)%s\n\n' "$YELLOW" "$NC"
    fi
  fi
}

configure_crypttab() {
  log_step "3. Configuring /etc/crypttab"

  if [[ ! -f "$CRYPTTAB_PATH" ]]; then
    log_error "File $CRYPTTAB_PATH not found."
    exit 1
  fi

  if grep -q "tpm2-device=" "$CRYPTTAB_PATH"; then
    log_info "tpm2-device option already configured in $CRYPTTAB_PATH. No changes needed."
    return 0
  fi

  log_info "Adding tpm2-device=auto to $CRYPTTAB_PATH..."
  if "$DRY_RUN"; then
    log_info "[DRY-RUN] Would backup $CRYPTTAB_PATH and append ',tpm2-device=auto'."
    return 0
  fi

  local backup_file
  backup_file="${CRYPTTAB_PATH}.bak.$(date +%Y%m%d%H%M%S)"
  cp -p "$CRYPTTAB_PATH" "$backup_file"
  log_info "Created backup: $backup_file"

  # Safely append tpm2-device=auto to non-comment lines
  sed -i '/^#/! { /tpm2-device/!s/$/,tpm2-device=auto/ }' "$CRYPTTAB_PATH"
  log_info "Updated $CRYPTTAB_PATH successfully."
}

configure_initramfs() {
  log_step "4. Checking and Regenerating Initramfs"

  # Check if rpm-ostree (Fedora Silverblue/Kinoite/CoreOS)
  if command -v rpm-ostree >/dev/null 2>&1 && [[ -d /sysroot/ostree ]]; then
    log_info "Fedora Atomic/OSTree system detected: initramfs regeneration is handled dynamically on boot."
    return 0
  fi

  if ! command -v dracut >/dev/null 2>&1; then
    log_warn "dracut not found; skipping initramfs regeneration."
    return 0
  fi

  log_info "Verifying dracut modules (tpm2-tss, systemd-cryptsetup)..."
  local dracut_mods
  dracut_mods=$(dracut --list-modules 2>&1 || true)
  if [[ "$dracut_mods" != *"tpm2-tss"* ]]; then
    log_warn "dracut module 'tpm2-tss' not listed. Ensure tpm2-tss is installed."
  fi
  if [[ "$dracut_mods" != *"systemd-cryptsetup"* ]]; then
    log_warn "dracut module 'systemd-cryptsetup' not listed."
  fi

  if "$DRY_RUN"; then
    log_info "[DRY-RUN] Would run: dracut --force --regenerate-all"
    return 0
  fi

  log_info "Regenerating initramfs with dracut..."
  dracut --force --regenerate-all
  log_info "Initramfs regeneration complete."
}

enroll_tpm() {
  log_step "5. Enrolling TPM 2.0 Token into LUKS Header"

  local dump_output
  dump_output=$(cryptsetup luksDump "$DEVICE" 2>&1 || true)
  local is_enrolled=false
  if [[ "$dump_output" =~ systemd-tpm2 ]]; then
    is_enrolled=true
  fi

  local current_unseal_ok=false
  if "$is_enrolled"; then
    if cryptsetup --test-passphrase open "$DEVICE" </dev/null >/dev/null 2>&1; then
      current_unseal_ok=true
    fi
  fi

  if "$is_enrolled" && ! "$FORCE_REENROLL"; then
    if "$current_unseal_ok"; then
      log_info "TPM 2.0 token is already enrolled and matches current PCR state. Use --force-reenroll to replace it."
      return 0
    else
      log_warn "Existing TPM 2.0 token is enrolled, but live unseal test failed (policy mismatch from firmware/kernel updates)."
      log_warn "Automatic re-enrollment enabled to seal to current PCR measurements."
      FORCE_REENROLL=true
    fi
  fi

  if "$DRY_RUN"; then
    if "$FORCE_REENROLL" && "$is_enrolled"; then
      log_info "[DRY-RUN] Would re-enroll TPM2 token (atomic wipe of previous token): systemd-cryptenroll --wipe-slot=tpm2 --tpm2-device=auto --tpm2-pcrs=$PCRS $DEVICE"
    else
      log_info "[DRY-RUN] Would enroll TPM2 token: systemd-cryptenroll --tpm2-device=auto --tpm2-pcrs=$PCRS $DEVICE"
    fi
    return 0
  fi

  local enroll_cmd=("systemd-cryptenroll")
  if "$FORCE_REENROLL" && "$is_enrolled"; then
    log_info "Replacing existing TPM 2.0 token (atomic wipe of previous slot and enrollment of new token)..."
    enroll_cmd+=("--wipe-slot=tpm2")
  fi
  enroll_cmd+=("--tpm2-device=auto" "--tpm2-pcrs=$PCRS")

  if [[ -n "$UNLOCK_KEY_FILE" ]]; then
    enroll_cmd+=("--unlock-key-file=$UNLOCK_KEY_FILE")
  fi
  enroll_cmd+=("$DEVICE")

  log_info "Executing systemd-cryptenroll (PCRs: $PCRS, Device: $DEVICE)..."
  if [[ -n "${PASSWORD:-}" ]]; then
    PASSWORD="$PASSWORD" "${enroll_cmd[@]}"
  else
    "${enroll_cmd[@]}"
  fi

  log_info "TPM 2.0 token successfully enrolled."
}

verify_configuration() {
  log_step "6. Final Verification"

  if "$DRY_RUN"; then
    log_info "[DRY-RUN] Verification step skipped."
    return 0
  fi

  local dump_output
  dump_output=$(cryptsetup luksDump "$DEVICE" 2>&1 || true)

  if [[ "$dump_output" =~ systemd-tpm2 ]]; then
    log_info "Verified: systemd-tpm2 token is active in LUKS header."
  else
    log_error "Verification FAILED: systemd-tpm2 token not found in LUKS header."
    exit 1
  fi

  if grep -q "tpm2-device=" "$CRYPTTAB_PATH"; then
    log_info "Verified: tpm2-device=auto is configured in $CRYPTTAB_PATH."
  else
    log_warn "Warning: tpm2-device option missing from $CRYPTTAB_PATH."
  fi

  # Live unseal validation: ensures systemd-cryptsetup will succeed at boot
  local test_out
  if test_out=$(cryptsetup --test-passphrase open "$DEVICE" </dev/null 2>&1); then
    log_info "Verified: TPM 2.0 live unseal test succeeded against current system PCRs."
  else
    log_error "Verification FAILED: TPM 2.0 token failed live unseal test!"
    printf '%s\n' "$test_out" >&2
    exit 1
  fi

  printf '\n%s=======================================================%s\n' "$GREEN" "$NC"
  printf '%s  TPM 2.0 LUKS Auto-Unlock Successfully Configured!   %s\n' "$BOLD" "$NC"
  printf '%s=======================================================%s\n\n' "$GREEN" "$NC"
  printf 'Target Device: %s\n' "$DEVICE"
  printf 'Bound PCRs:    %s\n' "$PCRS"
  printf 'Crypttab:      %s\n' "$CRYPTTAB_PATH"
  printf 'Live Unseal:   VERIFIED (PCR policy matches)\n\n'
  printf 'Note: Your original manual passphrase in Keyslot 0 is preserved as fallback.\n'
}

main() {
  parse_args "$@"

  preflight_checks
  check_tpm_token_status

  if "$CHECK_ONLY"; then
    exit 0
  fi

  # Mutation requires root
  if [[ $EUID -ne 0 ]]; then
    log_error "Configuring TPM2 auto-unlock requires root privileges. Please re-run with sudo."
    exit 1
  fi

  configure_crypttab
  configure_initramfs
  enroll_tpm
  verify_configuration
}

main "$@"
