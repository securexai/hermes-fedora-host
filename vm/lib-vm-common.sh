#!/usr/bin/env bash
# shellcheck shell=bash
#
# Shared utility functions for VM management scripts
#
# Sourced by vm/*.sh scripts — not executed directly.

# Include guard — prevent re-execution when sourced by multiple scripts
[[ -n "${_LIB_VM_COMMON_LOADED:-}" ]] && return 0
readonly _LIB_VM_COMMON_LOADED=1

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s nullglob

# ERR trap for diagnostics — inherited by functions via errtrace.
# Capture the status before the source-path guard changes `$?`. Only report
# files in the project tree to avoid noise in test harnesses.
_vm_common_err_trap() {
  local status=$1
  local source_path=$2
  local line_number=$3
  local failed_command=$4

  if [[ "$source_path" == */vm/* ]]; then
    printf 'ERROR: %s:%s: "%s" exited %s\n' \
      "$source_path" "$line_number" "$failed_command" "$status" >&2
  fi
  return "$status"
}
trap '_vm_common_err_trap "$?" "${BASH_SOURCE[0]:-}" "${LINENO}" "${BASH_COMMAND}"' ERR

# Use system libvirt URI explicitly — without this, virsh and virt-install
# default to qemu:///session which cannot see system-level VMs or networks.
readonly VIRSH_URI="qemu:///system"
export LIBVIRT_DEFAULT_URI="qemu:///system"

# Colors for output — disabled when stderr is not a TTY or NO_COLOR is set.
# Color variables are used by sourcing scripts (setup-hypervisor.sh, create-*.sh).
if [[ -t 2 ]] && [[ -z "${NO_COLOR:-}" ]]; then
  # shellcheck disable=SC2034
  readonly VM_RED='\033[0;31m'
  # shellcheck disable=SC2034
  readonly VM_GREEN='\033[0;32m'
  # shellcheck disable=SC2034
  readonly VM_YELLOW='\033[1;33m'
  # shellcheck disable=SC2034
  readonly VM_BOLD='\033[1m'
  # shellcheck disable=SC2034
  readonly VM_NC='\033[0m'
else
  # shellcheck disable=SC2034
  readonly VM_RED=''
  # shellcheck disable=SC2034
  readonly VM_GREEN=''
  # shellcheck disable=SC2034
  readonly VM_YELLOW=''
  # shellcheck disable=SC2034
  readonly VM_BOLD=''
  # shellcheck disable=SC2034
  readonly VM_NC=''
fi

log_info() {
  printf '%s[INFO]%s %s\n' "$VM_GREEN" "$VM_NC" "$1" >&2
}

log_warn() {
  printf '%s[WARN]%s %s\n' "$VM_YELLOW" "$VM_NC" "$1" >&2
}

log_error() {
  printf '%s[ERROR]%s %s\n' "$VM_RED" "$VM_NC" "$1" >&2
}

die() {
  local msg="${1:-}"
  local code="${2:-1}"
  log_error "$msg"
  # Disable ERR trap before exit to prevent spurious diagnostics
  trap - ERR
  exit "$code"
}

# --- Prerequisite checks ---------------------------------------------------

# Verify KVM hardware acceleration is available
check_kvm() {
  if [[ ! -e /dev/kvm ]]; then
    log_error "KVM not available (/dev/kvm missing)"
    log_error "Ensure CPU virtualization is enabled in BIOS/UEFI"
    return 1
  fi
  return 0
}

# Verify libvirtd is running
check_libvirt() {
  if ! systemctl is-active --quiet libvirtd; then
    log_error "libvirtd is not running"
    log_error "Run: sudo systemctl enable --now libvirtd"
    return 1
  fi
  return 0
}

# Verify that the invoking user can create temporary files in a VM storage path.
# VM creators use qemu-img and xorriso as the invoking user, so checking only
# that the system pool exists is insufficient.
check_storage_pool_writable() {
  local storage_path="$1"
  local probe

  if [[ ! -d "$storage_path" ]]; then
    log_error "VM storage directory does not exist: $storage_path"
    log_error "Run: sudo ./vm/setup-hypervisor.sh"
    return 1
  fi

  if ! probe=$(mktemp "$storage_path/.vm-storage-write.XXXXXX" 2>/dev/null); then
    log_error "VM storage directory is not writable by the current user: $storage_path"
    log_error "Run: sudo ./vm/setup-hypervisor.sh"
    return 1
  fi
  rm -f -- "$probe"
}

# Verify the host can run the Hermes Fedora Server certification VM without avoidable
# memory or storage pressure. The 8 GiB guest needs 9 GiB available before
# QEMU starts; reserve 60 GiB for the thin-provisioned Server disk and image
# even though the qcow2 file initially consumes much less space.
check_hermes_server_host_resources() {
  local storage_path="${1:-/var/lib/libvirt/images}"
  local cpu_count mem_available_kib storage_available_kib
  local required_mem_kib=$((HERMES_SERVER_MIN_MEM_AVAILABLE_GIB * 1024 * 1024))
  local required_storage_kib=$((HERMES_SERVER_MIN_STORAGE_GIB * 1024 * 1024))

  if ! cpu_count=$(getconf _NPROCESSORS_ONLN 2>/dev/null) \
    || [[ ! "$cpu_count" =~ ^[0-9]+$ ]] || ((cpu_count < HERMES_SERVER_MIN_CPUS)); then
    log_error "Hermes Server certification needs at least ${HERMES_SERVER_MIN_CPUS} online CPUs"
    log_error "Detected online CPUs: ${cpu_count:-unavailable}"
    return 1
  fi

  mem_available_kib=$(awk '$1 == "MemAvailable:" {print $2; exit}' /proc/meminfo)
  if [[ ! "$mem_available_kib" =~ ^[0-9]+$ ]] || ((mem_available_kib < required_mem_kib)); then
    log_error "Hermes Server certification needs at least ${HERMES_SERVER_MIN_MEM_AVAILABLE_GIB} GiB MemAvailable"
    log_error "Detected MemAvailable: ${mem_available_kib:-unavailable} KiB"
    return 1
  fi

  if [[ ! -d "$storage_path" ]]; then
    log_error "Hermes Server certification storage path does not exist: $storage_path"
    return 1
  fi
  storage_available_kib=$(df -Pk "$storage_path" | awk 'NR == 2 {print $4}')
  if [[ ! "$storage_available_kib" =~ ^[0-9]+$ ]] \
    || ((storage_available_kib < required_storage_kib)); then
    log_error "Hermes Server certification needs at least ${HERMES_SERVER_MIN_STORAGE_GIB} GiB free at $storage_path"
    log_error "Detected free storage: ${storage_available_kib:-unavailable} KiB"
    return 1
  fi

  log_info "Hermes Server host resources passed (${cpu_count} CPUs, ${mem_available_kib} KiB available, ${storage_available_kib} KiB free at $storage_path)"
}

# Verify a command exists
require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" &>/dev/null; then
    log_error "Required command not found: $cmd"
    return 1
  fi
}

# --- VM lifecycle helpers ---------------------------------------------------

# Check if a VM (domain) already exists in libvirt
vm_exists() {
  local name="$1"
  virsh -c "$VIRSH_URI" list --all --name 2>/dev/null | grep -qx "$name"
}

# Wait for a VM to reach "running" state
# Usage: wait_vm_boot "vm-name" 60
wait_vm_boot() {
  local name="$1"
  local timeout="${2:-60}"

  log_info "Waiting for VM '$name' to boot (timeout: ${timeout}s)..."
  local elapsed=0
  while ((elapsed < timeout)); do
    local state
    state=$(virsh -c "$VIRSH_URI" domstate "$name" 2>/dev/null || true)
    if [[ "$state" == "running" ]]; then
      log_info "VM '$name' is running (${elapsed}s)"
      return 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done
  log_error "VM '$name' did not reach 'running' state within ${timeout}s"
  return 1
}

# Wait for SSH to become responsive on a given IP
# Usage: wait_ssh_ready "172.16.10.10" 120
wait_ssh_ready() {
  local ip="$1"
  local timeout="${2:-120}"

  log_info "Waiting for SSH on $ip (timeout: ${timeout}s)..."
  local elapsed=0
  while ((elapsed < timeout)); do
    if timeout 3 bash -c "echo >/dev/tcp/$ip/22" 2>/dev/null; then
      log_info "SSH responsive on $ip (${elapsed}s)"
      return 0
    fi
    sleep 3
    elapsed=$((elapsed + 3))
  done
  log_error "SSH not responsive on $ip within ${timeout}s"
  return 1
}

# Destroy and undefine a VM, optionally removing storage
# Usage: vm_cleanup "vm-name" [--remove-storage]
#
# --remove-storage  removes all libvirt-managed storage AND NVRAM via
#                   virsh undefine --remove-all-storage --nvram.
#                   WARNING: this deletes every attached disk, including
#                   read-only cdroms (e.g. user-provided ISOs). Only use
#                   when all attached disks are VM-specific copies.
#
# Without the flag, the VM is undefined with --nvram (UEFI NVRAM removed)
# but disk images are left on disk for the caller to clean up selectively.
vm_cleanup() {
  local name="$1"
  local remove_storage="${2:-}"

  if ! vm_exists "$name"; then
    log_info "VM '$name' does not exist, nothing to clean up"
    return 0
  fi

  local state
  state=$(virsh -c "$VIRSH_URI" domstate "$name" 2>/dev/null || true)
  if [[ "$state" == "running" ]]; then
    log_info "Stopping VM '$name'..."
    virsh -c "$VIRSH_URI" destroy "$name" >/dev/null 2>&1 || true
  fi

  if [[ "$remove_storage" == "--remove-storage" ]]; then
    log_info "Removing VM '$name' and its storage..."
    virsh -c "$VIRSH_URI" undefine "$name" \
      --remove-all-storage --nvram >/dev/null 2>&1 || true
  else
    log_info "Removing VM '$name' (keeping storage on disk)..."
    virsh -c "$VIRSH_URI" undefine "$name" --nvram >/dev/null 2>&1 || true
  fi

  log_info "VM '$name' cleaned up"
}

# --- Network helpers --------------------------------------------------------

# Define and start a libvirt network from XML if not already active
# Usage: ensure_network "/path/to/network.xml" "network-name"
ensure_network() {
  local xml_path="$1"
  local net_name="$2"

  if [[ "${DRY_RUN:-false}" == "true" ]]; then
    log_info "[DRY-RUN] Would ensure libvirt network '$net_name' from $xml_path"
    return 0
  fi

  if virsh -c "$VIRSH_URI" net-info "$net_name" &>/dev/null; then
    local state
    state=$(virsh -c "$VIRSH_URI" net-info "$net_name" 2>/dev/null | awk '/^Active:/{print $2}')
    if [[ "$state" == "yes" ]]; then
      log_info "Network '$net_name' already active"
      return 0
    fi
    log_info "Starting existing network '$net_name'..."
    virsh -c "$VIRSH_URI" net-start "$net_name" >/dev/null
    return 0
  fi

  log_info "Defining network '$net_name' from $xml_path..."
  virsh -c "$VIRSH_URI" net-define "$xml_path" >/dev/null
  virsh -c "$VIRSH_URI" net-start "$net_name" >/dev/null
  virsh -c "$VIRSH_URI" net-autostart "$net_name" >/dev/null
  log_info "Network '$net_name' defined, started, and set to autostart"
}

# Add a static DHCP host entry to a running libvirt network (idempotent).
# This ensures the VM gets a predictable IP even if the network was created
# from an older XML that lacked the <host> entry.
# Usage: ensure_dhcp_host "lab-vlans" "52:54:00:ab:10:02" "172.16.99.11" "lab-fedora"
ensure_dhcp_host() {
  local net_name="$1" mac="$2" ip="$3" hostname="$4"

  if [[ "${DRY_RUN:-false}" == "true" ]]; then
    log_info "[DRY-RUN] Would add DHCP host: $hostname ($mac → $ip) to network $net_name"
    return 0
  fi

  if virsh -c "$VIRSH_URI" net-update "$net_name" add ip-dhcp-host \
    "<host mac='$mac' ip='$ip' name='$hostname'/>" \
    --live --config 2>/dev/null; then
    log_info "Added DHCP reservation: $hostname ($mac → $ip)"
  else
    log_info "DHCP reservation already exists: $hostname ($mac → $ip)"
  fi
}

# --- Validation helpers -----------------------------------------------------

# Validate an IPv4 address format (dotted-quad, each octet 0-255)
validate_ip() {
  local ip="$1"
  local label="${2:-IP}"

  if [[ ! "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    log_error "Invalid $label format: $ip (expected dotted-quad IPv4)"
    return 1
  fi

  local IFS='.'
  # Intentional word-splitting on IFS='.' to split IPv4 octets
  # shellcheck disable=SC2206
  local octets=($ip)
  for octet in "${octets[@]}"; do
    if ((octet > 255)); then
      log_error "Invalid $label: octet $octet out of range in $ip"
      return 1
    fi
  done

  return 0
}

# --- SSH key resolution -----------------------------------------------------

# Scan ~/.ssh/ for available public keys and prompt user to select if multiple
# are found. Sets the caller's SSH_KEY variable directly.
# Skipped if SSH_KEY is already set (--ssh-key was provided).
# SSH_KEY is used by the sourcing script, not this library
# shellcheck disable=SC2034
resolve_ssh_key() {
  [[ -n "${SSH_KEY:-}" ]] && return 0

  local keys=()
  local search_dirs=("$HOME")
  [[ -n "${SUDO_USER:-}" ]] && search_dirs+=("/home/$SUDO_USER")

  for dir in "${search_dirs[@]}"; do
    # Any .pub file (handles custom key names like wsl.pub, work_ed25519.pub)
    for pub in "$dir"/.ssh/*.pub; do
      [[ -f "$pub" ]] && keys+=("$pub")
    done
    # authorized_keys as fallback (contains remote public keys)
    if [[ -f "$dir/.ssh/authorized_keys" ]]; then
      keys+=("$dir/.ssh/authorized_keys")
    fi
  done

  if [[ ${#keys[@]} -eq 0 ]]; then
    SSH_KEY=""
  elif [[ ${#keys[@]} -eq 1 ]]; then
    SSH_KEY="${keys[0]}"
    log_info "Found SSH key: $SSH_KEY"
  else
    log_info "Multiple SSH keys found:"
    local PS3="Select key to inject (or Skip): "
    select key in "${keys[@]}" "Skip (no SSH key)"; do
      if [[ "$key" == "Skip (no SSH key)" ]]; then
        SSH_KEY=""
        break
      elif [[ -n "$key" ]]; then
        SSH_KEY="$key"
        log_info "Selected: $SSH_KEY"
        break
      else
        log_warn "Invalid selection, try again"
      fi
    done
  fi
}

# --- Dry-run support --------------------------------------------------------

# Helper function to run commands or preview them in dry-run mode
# Requires DRY_RUN to be set by the sourcing script
run_cmd() {
  if [[ "${DRY_RUN:-false}" == "true" ]]; then
    log_info "[DRY-RUN] Would execute: $*"
  else
    "$@"
  fi
}

# --- Default resource constants (used by sourcing scripts) ------------------

# Fedora VM defaults — used by create-fedora-vm.sh
# shellcheck disable=SC2034
readonly FEDORA_DEFAULT_RAM=2048 # MB
# shellcheck disable=SC2034
readonly FEDORA_DEFAULT_VCPUS=2
# shellcheck disable=SC2034
readonly FEDORA_DEFAULT_DISK=20 # GB

# Hermes Server certification VM defaults — used by create-hermes-server-vm.sh
# shellcheck disable=SC2034
readonly HERMES_SERVER_DEFAULT_RAM=8192 # MB — Hermes certification prerequisite
# shellcheck disable=SC2034
readonly HERMES_SERVER_DEFAULT_VCPUS=2
# shellcheck disable=SC2034
readonly HERMES_SERVER_DEFAULT_DISK=40 # GB — Hermes-agent image E2E needs more than 20 GB
# shellcheck disable=SC2034
readonly HERMES_SERVER_MIN_CPUS=2
# shellcheck disable=SC2034
readonly HERMES_SERVER_MIN_MEM_AVAILABLE_GIB=9
# shellcheck disable=SC2034
readonly HERMES_SERVER_MIN_STORAGE_GIB=60

# --- VM network identity (MAC + static DHCP IP on VLAN 99) -------------------
# Each VM gets a fixed MAC so libvirt's DHCP server assigns a predictable IP.
# IPs are in 172.16.99.11-12, below the dynamic pool (.100-.199).
# MACs use libvirt's 52:54:00 OUI with a lab-specific pattern (ab:10:0N).

# Fedora VM network identity — used by create-fedora-vm.sh
# shellcheck disable=SC2034
readonly FEDORA_MAC="52:54:00:ab:10:02"
# shellcheck disable=SC2034
readonly FEDORA_IP="172.16.99.11"

# Hermes Server certification VM network identity — used by create-hermes-server-vm.sh
# shellcheck disable=SC2034
readonly HERMES_SERVER_MAC="52:54:00:ab:10:03"
# shellcheck disable=SC2034
readonly HERMES_SERVER_IP="172.16.99.12"
