#!/usr/bin/env bash
# shellcheck shell=bash
#
# Create a Fedora VM for testing the workstation `setup.sh` with real
# ostree/reboot support.
#
# SCOPE NOTE: `setup.sh` is part of the unrelated workstation stack that stays in
# the source repository and was deliberately NOT migrated here. This script is
# retained for reference only; the "then test: ./setup.sh" step below cannot run
# in this repository. See docs/ENVIRONMENT.md for the scope boundary.
#
# Uses a Fedora Cloud qcow2 image with cloud-init for provisioning.
# The repo is shared into the VM via virtio-fs or 9p for testing.
#
# Usage:
#   ./vm/create-fedora-vm.sh --image /path/to/Fedora-Cloud-Base-43.qcow2
#   ./vm/create-fedora-vm.sh --destroy         # Remove VM and storage
#   ./vm/create-fedora-vm.sh --dry-run         # Preview without changes
#   ./vm/create-fedora-vm.sh --help            # Show help
#
# Prerequisites:
#   - setup-hypervisor.sh completed
#   - Fedora Cloud Base qcow2 image downloaded

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s nullglob

[[ "${TRACE:-0}" == "1" ]] && set -o xtrace

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
readonly REPO_ROOT

# shellcheck source=lib-vm-common.sh
# shellcheck disable=SC1091  # resolved from SCRIPT_DIR at runtime
source "$SCRIPT_DIR/lib-vm-common.sh"

# --- Constants --------------------------------------------------------------

readonly VM_NAME="lab-fedora"
readonly STORAGE_POOL="/var/lib/libvirt/images"
readonly DISK_PATH="$STORAGE_POOL/${VM_NAME}.qcow2"
readonly CIDATA_PATH="$STORAGE_POOL/${VM_NAME}-cidata.iso"
readonly NETWORK="lab-vlans"
readonly CLOUD_INIT_DIR="$SCRIPT_DIR/cloud-init"

# --- Argument parsing -------------------------------------------------------

DRY_RUN=false
DESTROY=false
IMAGE_PATH=""
SSH_KEY=""

show_help() {
  cat <<'EOF'
Create a Fedora VM for testing setup.sh

Usage:
  ./vm/create-fedora-vm.sh --image <path>           Create VM from Fedora Cloud image
  ./vm/create-fedora-vm.sh --image <path> --ssh-key <path>  With SSH key injection
  ./vm/create-fedora-vm.sh --destroy                Remove VM and its storage
  ./vm/create-fedora-vm.sh --dry-run                Preview actions without changes
  ./vm/create-fedora-vm.sh --help                   Show this help message

Arguments:
  --image <path>     Path to Fedora Cloud Base qcow2 image
  --ssh-key <path>   Path to SSH public key to inject (optional)
                     Default: auto-detected from ~/.ssh/*.pub

Examples:
  ./vm/create-fedora-vm.sh --image ~/Downloads/Fedora-Cloud-Base-43-1.1.x86_64.qcow2
  ./vm/create-fedora-vm.sh --image ~/Downloads/Fedora-Cloud-Base-43.qcow2 --ssh-key ~/.ssh/id_ed25519.pub
  ./vm/create-fedora-vm.sh --destroy

VM resources: 2GB RAM, 2 vCPUs, 20GB disk
Network: lab-vlans (NAT virtual network)
Console: Cockpit → Machines → lab-fedora → Console tab
Login: lab / lab (or via SSH key)
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --image)
      IMAGE_PATH="${2:-}"
      if [[ -z "$IMAGE_PATH" ]]; then
        log_error "--image requires a file path argument"
        exit 1
      fi
      shift 2
      ;;
    --ssh-key)
      SSH_KEY="${2:-}"
      if [[ -z "$SSH_KEY" ]]; then
        log_error "--ssh-key requires a file path argument"
        exit 1
      fi
      shift 2
      ;;
    --destroy)
      DESTROY=true
      shift
      ;;
    --dry-run | -n)
      DRY_RUN=true
      shift
      ;;
    --help | -h) show_help ;;
    *)
      log_error "Unknown argument: $1"
      show_help
      ;;
  esac
done

# --- Destroy mode -----------------------------------------------------------

if $DESTROY; then
  log_info "Destroying VM '$VM_NAME'..."
  vm_cleanup "$VM_NAME" --remove-storage
  for f in "$DISK_PATH" "$CIDATA_PATH"; do
    if [[ -f "$f" ]]; then
      run_cmd rm -f "$f"
    fi
  done
  log_info "Done"
  exit 0
fi

# --- Validation -------------------------------------------------------------

if [[ -z "$IMAGE_PATH" ]]; then
  log_error "Fedora Cloud image path required. Use --image <path>"
  log_error "Download from: fedoraproject.org → Cloud → Cloud Base images"
  exit 1
fi

if [[ ! -f "$IMAGE_PATH" ]]; then
  log_error "Image file not found: $IMAGE_PATH"
  exit 1
fi

require_cmd virsh
require_cmd virt-install
require_cmd qemu-img
if ! command -v genisoimage &>/dev/null && ! command -v mkisofs &>/dev/null; then
  log_error "Neither genisoimage nor mkisofs found — install: sudo dnf install genisoimage"
  exit 1
fi
check_libvirt
check_storage_pool_writable "$STORAGE_POOL"

if vm_exists "$VM_NAME"; then
  log_error "VM '$VM_NAME' already exists"
  log_error "Run with --destroy first, or manage via Cockpit"
  exit 1
fi

# --- Resolve SSH key --------------------------------------------------------

resolve_ssh_key

# =============================================================================
log_info "Creating Fedora VM '$VM_NAME'..."
echo ""
# =============================================================================

# --- Step 1: Prepare disk ---------------------------------------------------

log_info "Preparing disk image (${FEDORA_DEFAULT_DISK}GB)..."
run_cmd cp "$IMAGE_PATH" "$DISK_PATH"

if [[ "$DRY_RUN" == "false" ]]; then
  run_cmd qemu-img resize "$DISK_PATH" "${FEDORA_DEFAULT_DISK}G"
  log_info "Disk resized to ${FEDORA_DEFAULT_DISK}GB"
fi

# --- Step 2: Build cloud-init ISO -------------------------------------------

log_info "Building cloud-init data..."

CIDATA_TMPDIR=$(mktemp -d)
cleanup() {
  rm -rf "${CIDATA_TMPDIR:-}"
}
trap 'cleanup' EXIT
trap 'trap - INT EXIT; cleanup; kill -INT $$' INT
trap 'trap - TERM EXIT; cleanup; kill -TERM $$' TERM

# Copy user-data, inject SSH key if available
cp "$CLOUD_INIT_DIR/fedora-user-data.yaml" "$CIDATA_TMPDIR/user-data"

if [[ -n "$SSH_KEY" && -f "$SSH_KEY" ]]; then
  SSH_KEY_CONTENT=$(grep -m1 '^ssh-' "$SSH_KEY" || true)
  if [[ -z "$SSH_KEY_CONTENT" ]]; then
    log_warn "No ssh-* key line found in $SSH_KEY — skipping SSH key injection"
  else
    log_info "Injecting SSH key: $SSH_KEY"
    sed -i "/^  - name: lab$/a\\    ssh_authorized_keys:\\n      - $SSH_KEY_CONTENT" \
      "$CIDATA_TMPDIR/user-data"
  fi
fi

# Create meta-data
cat >"$CIDATA_TMPDIR/meta-data" <<EOF
instance-id: $VM_NAME
local-hostname: $VM_NAME
EOF

if command -v genisoimage &>/dev/null; then
  ISO_CMD=genisoimage
elif command -v mkisofs &>/dev/null; then
  ISO_CMD=mkisofs
else
  log_error "Neither genisoimage nor mkisofs found — cannot build cloud-init ISO"
  log_error "Install: sudo dnf install genisoimage"
  exit 1
fi

run_cmd "$ISO_CMD" -output "$CIDATA_PATH" -volid cidata -joliet -rock \
  "$CIDATA_TMPDIR/user-data" "$CIDATA_TMPDIR/meta-data"

log_info "Cloud-init ISO created: $CIDATA_PATH"

# --- Step 3: Ensure network exists ------------------------------------------

NETWORK_XML="$SCRIPT_DIR/networks/lab-vlans.xml"
ensure_network "$NETWORK_XML" "$NETWORK"
ensure_dhcp_host "$NETWORK" "$FEDORA_MAC" "$FEDORA_IP" "$VM_NAME"

# --- Step 4: Create VM ------------------------------------------------------

log_info "Creating VM with virt-install..."

# Commas are virt-install key=value syntax, not array separators
# shellcheck disable=SC2054
VIRT_INSTALL_ARGS=(
  --name "$VM_NAME"
  --memory "$FEDORA_DEFAULT_RAM"
  --vcpus "$FEDORA_DEFAULT_VCPUS"
  --disk "path=$DISK_PATH,format=qcow2,bus=virtio"
  --disk "path=$CIDATA_PATH,device=cdrom"
  --network "network=$NETWORK,model=virtio,mac=$FEDORA_MAC"
  --os-variant fedora-unknown
  --graphics vnc,listen=127.0.0.1
  --boot uefi,hd
  --noautoconsole
  --import
)

# Share the repo into the VM via filesystem passthrough
VIRT_INSTALL_ARGS+=(
  --filesystem "source=$REPO_ROOT,target=workspace,accessmode=mapped"
  --security type=none
)

run_cmd virt-install "${VIRT_INSTALL_ARGS[@]}"

# --- Step 5: Wait for boot --------------------------------------------------

if [[ "$DRY_RUN" == "false" ]]; then
  wait_vm_boot "$VM_NAME" 60
  log_info "Waiting for cloud-init to complete..."
  wait_ssh_ready "$FEDORA_IP" 180 || log_warn "SSH not ready — cloud-init may still be running"
fi

# =============================================================================
echo ""
log_info "Fedora VM '$VM_NAME' created successfully!"
echo ""
printf '%s=== Access ===%s\n' "$VM_BOLD" "$VM_NC"
echo ""
echo "  VM IP:        $FEDORA_IP"
echo ""
echo "  Cockpit GUI:  https://$(hostname -I | awk '{print $1}'):9090"
echo "                → Machines → $VM_NAME → Console"
echo ""
echo "  Console login: lab / lab"
echo "  SSH:           ssh lab@$FEDORA_IP"
echo ""
echo "  Mount workspace inside VM:"
echo "    sudo mount -t 9p -o trans=virtio,version=9p2000.L workspace /workspace"
echo ""
echo "  Then test (workstation setup.sh; absent from this repository):"
echo "    cd /workspace && ./setup.sh"
echo ""
echo "  To destroy:   ./vm/create-fedora-vm.sh --destroy"
echo ""
