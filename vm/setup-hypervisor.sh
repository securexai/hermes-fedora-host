#!/usr/bin/env bash
# shellcheck shell=bash
#
# Hypervisor setup for VM-based testing
#
# Installs libvirt, QEMU-KVM, Cockpit, and cockpit-machines on the host.
# Works on standard Fedora (DNF) and atomic desktops (rpm-ostree/Kinoite).
#
# After setup, the Cockpit GUI is available at https://<host-ip>:9090
#
# Usage:
#   ./vm/setup-hypervisor.sh              # Install everything
#   ./vm/setup-hypervisor.sh --check      # Show installed status
#   ./vm/setup-hypervisor.sh --dry-run    # Preview without changes
#   ./vm/setup-hypervisor.sh --help       # Show help

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s nullglob

[[ "${TRACE:-0}" == "1" ]] && set -o xtrace

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

# shellcheck source=lib-vm-common.sh
# shellcheck disable=SC1091  # resolved from SCRIPT_DIR at runtime
source "$SCRIPT_DIR/lib-vm-common.sh"

# --- Argument parsing -------------------------------------------------------

DRY_RUN=false
CHECK_ONLY=false
readonly STORAGE_POOL_DIR="/var/lib/libvirt/images"

show_help() {
  cat <<'EOF'
Hypervisor setup for VM-based testing

Usage:
  ./vm/setup-hypervisor.sh              Install and configure hypervisor
  ./vm/setup-hypervisor.sh --check      Show installed component status
  ./vm/setup-hypervisor.sh --dry-run    Preview actions without changes
  ./vm/setup-hypervisor.sh --help       Show this help message

Installs:
  - qemu-kvm          KVM/QEMU hypervisor
  - libvirt            VM management daemon
  - virt-install       CLI VM provisioning tool
  - cockpit            Web management console
  - cockpit-machines   VM management GUI plugin

After setup:
  - Cockpit GUI: https://<host-ip>:9090
  - CLI tools:   virsh, virt-install

Works on standard Fedora (DNF) and Fedora Kinoite 44 (rpm-ostree).
EOF
  exit 0
}

for arg in "$@"; do
  case "$arg" in
    --dry-run | -n) DRY_RUN=true ;;
    --check | -c) CHECK_ONLY=true ;;
    --help | -h) show_help ;;
    *)
      log_error "Unknown argument: $arg"
      show_help
      ;;
  esac
done

# --- OS detection -----------------------------------------------------------

is_ostree() {
  [[ -f /run/ostree-booted ]]
}

# --- Check mode -------------------------------------------------------------

if $CHECK_ONLY; then
  echo ""
  printf '%s=== Hypervisor Status ===%s\n' "$VM_BOLD" "$VM_NC"
  echo ""

  # KVM
  if [[ -e /dev/kvm ]]; then
    printf '  %sOK%s  KVM acceleration available\n' "$VM_GREEN" "$VM_NC"
  else
    printf '  %sMISSING%s  KVM acceleration (/dev/kvm not found)\n' "$VM_RED" "$VM_NC"
  fi

  # OS type
  if is_ostree; then
    printf '  %sOK%s  OS: atomic desktop (ostree)\n' "$VM_GREEN" "$VM_NC"
  else
    printf '  %sOK%s  OS: standard Fedora\n' "$VM_GREEN" "$VM_NC"
  fi

  # Packages / commands
  for cmd in virsh virt-install qemu-img; do
    if command -v "$cmd" &>/dev/null; then
      local_ver=$("$cmd" --version 2>/dev/null | head -1 || echo "installed")
      printf '  %sOK%s  %s (%s)\n' "$VM_GREEN" "$VM_NC" "$cmd" "$local_ver"
    else
      printf '  %sMISSING%s  %s\n' "$VM_RED" "$VM_NC" "$cmd"
    fi
  done

  # libvirtd service
  if systemctl is-active --quiet libvirtd 2>/dev/null; then
    printf '  %sOK%s  libvirtd is active\n' "$VM_GREEN" "$VM_NC"
  elif systemctl is-enabled --quiet libvirtd 2>/dev/null; then
    printf '  %sWARN%s  libvirtd is enabled but not active\n' "$VM_YELLOW" "$VM_NC"
  else
    printf '  %sMISSING%s  libvirtd not enabled\n' "$VM_RED" "$VM_NC"
  fi

  # Cockpit
  if systemctl is-active --quiet cockpit.socket 2>/dev/null; then
    printf '  %sOK%s  Cockpit is active (port 9090)\n' "$VM_GREEN" "$VM_NC"
  elif systemctl is-enabled --quiet cockpit.socket 2>/dev/null; then
    printf '  %sWARN%s  Cockpit is enabled but socket not active\n' "$VM_YELLOW" "$VM_NC"
  else
    printf '  %sMISSING%s  Cockpit not enabled\n' "$VM_RED" "$VM_NC"
  fi

  # cockpit-machines
  if rpm -q cockpit-machines &>/dev/null; then
    printf '  %sOK%s  cockpit-machines plugin installed\n' "$VM_GREEN" "$VM_NC"
  else
    printf '  %sMISSING%s  cockpit-machines plugin\n' "$VM_RED" "$VM_NC"
  fi

  # UEFI firmware (OVMF)
  if [[ -f /usr/share/edk2/ovmf/OVMF_CODE.fd ||
    -f /usr/share/OVMF/OVMF_CODE.fd ||
    -f /usr/share/edk2/ovmf/OVMF_CODE.secboot.fd ]]; then
    printf '  %sOK%s  OVMF UEFI firmware available\n' "$VM_GREEN" "$VM_NC"
  else
    printf '  %sMISSING%s  OVMF UEFI firmware (install edk2-ovmf)\n' \
      "$VM_RED" "$VM_NC"
  fi

  # Default storage pool
  if virsh -c "$VIRSH_URI" pool-info default &>/dev/null 2>&1; then
    printf '  %sOK%s  libvirt default storage pool\n' "$VM_GREEN" "$VM_NC"
  else
    printf '  %sMISSING%s  libvirt default storage pool\n' "$VM_RED" "$VM_NC"
  fi

  # Non-root VM creators need group write access to the system pool path.
  if [[ -d "$STORAGE_POOL_DIR" ]]; then
    pool_group=$(stat -c '%G' "$STORAGE_POOL_DIR")
    pool_mode=$(stat -c '%a' "$STORAGE_POOL_DIR")
    if [[ "$pool_group" == "libvirt" && "$pool_mode" == "775" ]]; then
      printf '  %sOK%s  libvirt storage permissions (%s:%s %s)\n' \
        "$VM_GREEN" "$VM_NC" "root" "$pool_group" "$pool_mode"
    else
      printf '  %sMISSING%s  libvirt storage permissions (%s:%s %s; run setup)\n' \
        "$VM_RED" "$VM_NC" "root" "$pool_group" "$pool_mode"
    fi
  else
    printf '  %sMISSING%s  libvirt storage directory (%s)\n' \
      "$VM_RED" "$VM_NC" "$STORAGE_POOL_DIR"
  fi

  # Lab network
  if virsh -c "$VIRSH_URI" net-info lab-vlans &>/dev/null 2>&1; then
    printf '  %sOK%s  lab-vlans virtual network\n' "$VM_GREEN" "$VM_NC"
  else
    printf '  %sMISSING%s  lab-vlans virtual network\n' "$VM_RED" "$VM_NC"
  fi

  echo ""
  exit 0
fi

# --- Root check -------------------------------------------------------------

if [[ $EUID -ne 0 ]]; then
  log_error "This script must be run as root (sudo)"
  exit 1
fi

# =============================================================================
echo ""
log_info "Setting up hypervisor for VM-based testing..."
echo ""
# =============================================================================

# --- Step 1: Install packages -----------------------------------------------

PACKAGES=(
  qemu-kvm
  libvirt
  libvirt-client
  virt-install
  cockpit
  cockpit-machines
  guestfs-tools
  edk2-ovmf
)

log_info "Installing packages: ${PACKAGES[*]}"

if is_ostree; then
  log_warn "Atomic desktop detected — using rpm-ostree"
  if $DRY_RUN; then
    log_info "[DRY-RUN] Would execute: rpm-ostree install ${PACKAGES[*]}"
  else
    # rpm-ostree install is idempotent — already-installed packages are skipped
    if rpm-ostree install --idempotent --allow-inactive "${PACKAGES[@]}"; then
      log_info "Packages layered successfully"
    else
      log_warn "Some packages may already be in the base image"
    fi

    # After rpm-ostree stages packages, they are not available until reboot.
    # Check if the key commands exist — if not, a reboot is required before
    # we can enable services, create storage pools, or configure networks.
    if ! command -v virsh &>/dev/null; then
      echo ""
      log_warn "Packages are staged but not yet active (ostree requires a reboot)"
      log_warn "Run: systemctl reboot"
      log_warn "Then re-run: sudo ./vm/setup-hypervisor.sh"
      echo ""
      exit 0
    fi
  fi
else
  if $DRY_RUN; then
    log_info "[DRY-RUN] Would execute: dnf install -y ${PACKAGES[*]}"
  else
    dnf install -y --setopt=install_weak_deps=False "${PACKAGES[@]}"
    log_info "Packages installed"
  fi
fi

# --- Nix health check (after ostree reboot) ---------------------------------

# rpm-ostree reboots can break Nix if the nix-directory.service is incompatible
# with composefs. Warn early so the user can fix Nix before proceeding.
if command -v nix &>/dev/null; then
  if nix store ping &>/dev/null 2>&1; then
    log_info "Nix installation verified"
  else
    log_warn "Nix may be broken after rpm-ostree reboot"
    log_warn "Run the workstation setup.sh --check (source repository) to diagnose"
    log_warn "Or reinstall: curl -sSf -L https://install.determinate.systems/nix | sh -s -- install ostree"
  fi
fi

# --- Step 2: Enable services ------------------------------------------------

log_info "Enabling services..."

run_cmd systemctl enable --now libvirtd
if [[ "$DRY_RUN" == "false" ]]; then
  log_info "libvirtd enabled and started"
else
  log_info "[DRY-RUN] Would enable and start libvirtd"
fi

run_cmd systemctl enable --now cockpit.socket
if [[ "$DRY_RUN" == "false" ]]; then
  log_info "Cockpit socket enabled and started"
else
  log_info "[DRY-RUN] Would enable and start cockpit.socket"
fi

# --- Step 3: Configure default storage pool ---------------------------------

if ! virsh -c "$VIRSH_URI" pool-info default &>/dev/null 2>&1; then
  log_info "Creating default storage pool..."
  run_cmd virsh -c "$VIRSH_URI" pool-define-as default dir --target "$STORAGE_POOL_DIR"
  run_cmd virsh -c "$VIRSH_URI" pool-build default
  run_cmd virsh -c "$VIRSH_URI" pool-start default
  run_cmd virsh -c "$VIRSH_URI" pool-autostart default
  log_info "Default storage pool created at $STORAGE_POOL_DIR"
else
  log_info "Default storage pool already exists"
fi

# Ensure storage pool directory is writable by the libvirt group so that
# non-root users in the libvirt group can create and convert disk images.
if [[ -d "$STORAGE_POOL_DIR" ]]; then
  current_group=$(stat -c '%G' "$STORAGE_POOL_DIR")
  current_perms=$(stat -c '%a' "$STORAGE_POOL_DIR")
  if [[ "$current_group" != "libvirt" || "$current_perms" != "775" ]]; then
    log_info "Fixing storage pool permissions ($current_group/$current_perms → libvirt/775)..."
    run_cmd chgrp libvirt "$STORAGE_POOL_DIR"
    run_cmd chmod 0775 "$STORAGE_POOL_DIR"
    log_info "Storage pool permissions set"
  else
    log_info "Storage pool permissions already correct"
  fi
fi

# --- Step 4: Configure lab network ------------------------------------------

NETWORK_XML="$SCRIPT_DIR/networks/lab-vlans.xml"
if [[ -f "$NETWORK_XML" ]]; then
  if ! virsh -c "$VIRSH_URI" net-info lab-vlans &>/dev/null 2>&1; then
    log_info "Defining lab-vlans network..."
    run_cmd virsh -c "$VIRSH_URI" net-define "$NETWORK_XML"
    run_cmd virsh -c "$VIRSH_URI" net-start lab-vlans
    run_cmd virsh -c "$VIRSH_URI" net-autostart lab-vlans
    log_info "lab-vlans network created and started"
  else
    log_info "lab-vlans network already defined"
  fi
else
  log_warn "Network XML not found at $NETWORK_XML — skipping"
fi

# --- Step 5: Firewall -------------------------------------------------------

if command -v firewall-cmd &>/dev/null; then
  if ! firewall-cmd --query-service=cockpit --permanent &>/dev/null 2>&1; then
    log_info "Opening firewall for Cockpit (port 9090)..."
    run_cmd firewall-cmd --permanent --add-service=cockpit
    run_cmd firewall-cmd --reload
    log_info "Firewall updated"
  else
    log_info "Firewall already allows Cockpit"
  fi
fi

# --- Step 6: Add current user to libvirt group if not root session ----------

if [[ -n "${SUDO_USER:-}" ]]; then
  if id -nG "$SUDO_USER" 2>/dev/null | grep -qw libvirt; then
    log_info "User '$SUDO_USER' already in libvirt group"
  elif getent group libvirt 2>/dev/null | grep -qw "$SUDO_USER"; then
    log_info "User '$SUDO_USER' already in libvirt group (pending login)"
  else
    log_info "Adding user '$SUDO_USER' to libvirt group..."
    # On ostree, groups from the base image live in /usr/lib/group (read-only).
    # gpasswd/usermod require the group in /etc/group, so mirror it there first.
    if is_ostree && ! grep -q '^libvirt:' /etc/group 2>/dev/null; then
      grep '^libvirt:' /usr/lib/group >>/etc/group
    fi
    run_cmd gpasswd -a "$SUDO_USER" libvirt
    log_info "User added — log out and back in for group membership to take effect"
  fi
fi

# =============================================================================
echo ""
log_info "Hypervisor setup complete!"
echo ""
printf '%s=== Next Steps ===%s\n' "$VM_BOLD" "$VM_NC"
echo ""
echo "  1. Cockpit GUI:  https://$(hostname -I | awk '{print $1}'):9090"
echo "  2. Create VMs:   ./vm/create-fedora-vm.sh"
echo "                   ./vm/create-hermes-server-vm.sh --iso <server-iso> --ssh-key <public-key>"
echo "  3. Check status: ./vm/setup-hypervisor.sh --check"
echo ""
if is_ostree; then
  printf '%s  NOTE: Reboot required if packages were newly layered.%s\n' "$VM_YELLOW" "$VM_NC"
  echo ""
fi
