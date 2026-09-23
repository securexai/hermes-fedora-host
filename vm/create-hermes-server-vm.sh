#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC1091,SC2054
# Create the disposable Fedora Server 44 Hermes certification VM.

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s nullglob
umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR
# shellcheck source=lib-vm-common.sh
source "$SCRIPT_DIR/lib-vm-common.sh"
# shellcheck source=lib-hermes-luks-console.sh
source "$SCRIPT_DIR/lib-hermes-luks-console.sh"

readonly VM_NAME='lab-hermes-server'
readonly VM_IP='172.16.99.12'
readonly VM_MAC='52:54:00:ab:10:03'
readonly NETWORK='lab-vlans'
readonly KICKSTART_FILE="$SCRIPT_DIR/kickstart/fedora-server.ks"
readonly INSTALL_KERNEL_ARGS='inst.stage2=hd:LABEL=Fedora-S-dvd-x86_64-44 inst.ks=hd:LABEL=OEMDRV:/ks.cfg console=tty0 console=ttyS0,115200n8'
readonly LUKS_PROMPT_TIMEOUT_SECONDS=180
readonly LUKS_PROMPT_PROBE_SECONDS=30

DRY_RUN=false
DESTROY=false
ISO_PATH=''
SSH_KEY=''
UNLOCK_EVENT_LOG=/dev/null
TPM_STAGE=false
TPM_PUBLIC_KEY=''
FIRMWARE_VARS=''
FIRMWARE_CODE=''
INSTALLER_UKI=''
BOOT_CERTIFICATE=''
RECOVERY_KEY_FILE=''

show_help() {
  cat <<'EOF'
Create the disposable Fedora Server 44 Hermes certification VM

Usage:
  ./vm/create-hermes-server-vm.sh --iso PATH --ssh-key PATH [--unlock-log PATH]
  ./vm/create-hermes-server-vm.sh --destroy
  ./vm/create-hermes-server-vm.sh --dry-run --iso PATH
  ./vm/create-hermes-server-vm.sh --iso PATH --ssh-key PATH --tpm-stage \
    --tpm-public-key PATH --firmware-code PATH --firmware-vars PATH \
    --installer-uki PATH --boot-certificate PATH --recovery-key-file PATH

The VM is intentionally disposable: Fedora Server 44 DVD, 8 GiB RAM, 2 vCPUs,
40 GiB encrypted disk, UEFI Secure Boot, and 172.16.99.12 on lab-vlans.
The creator never downloads or trusts installer media; hermes-certify-vm.sh
verifies the ISO and signed checksum before invoking it.

--tpm-stage enrolls the disposable TPM during installation and leaves the VM
powered off for workstation UKI injection. It never invokes the console unlocker.
Firmware variables must already trust the workstation's public boot certificate.
The installer UKI must use that same certificate and the enrolled PCR public key.
EOF
}

unlock_server_fixture() {
  local deadline remaining probe_seconds
  log_info 'Waiting for the verified Fedora LUKS prompt on the VM serial console...'
  deadline=$((SECONDS + LUKS_PROMPT_TIMEOUT_SECONDS))
  while ((SECONDS < deadline)); do
    remaining=$((deadline - SECONDS))
    probe_seconds=$LUKS_PROMPT_PROBE_SECONDS
    ((remaining < probe_seconds)) && probe_seconds=$remaining
    if hermes_luks_console_unlock "$VM_NAME" "$VIRSH_URI" "$probe_seconds" "$UNLOCK_EVENT_LOG"; then
      log_info 'Verified Fedora LUKS prompt received the disposable fixture input'
      return 0
    fi
    sleep 2
  done
  die 'verified Fedora LUKS prompt was not observed; no unlock input was sent' 69
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --iso)
      [[ $# -gt 1 ]] || die '--iso requires a path' 64
      ISO_PATH=$2
      shift 2
      ;;
    --ssh-key)
      [[ $# -gt 1 ]] || die '--ssh-key requires a path' 64
      SSH_KEY=$2
      shift 2
      ;;
    --unlock-log)
      [[ $# -gt 1 ]] || die '--unlock-log requires a path' 64
      UNLOCK_EVENT_LOG=$2
      shift 2
      ;;
    --tpm-stage)
      TPM_STAGE=true
      shift
      ;;
    --tpm-public-key | --firmware-code | --firmware-vars | --installer-uki | --boot-certificate | --recovery-key-file)
      [[ $# -gt 1 ]] || die "$1 requires a path" 64
      case "$1" in
        --tpm-public-key) TPM_PUBLIC_KEY=$2 ;;
        --firmware-code) FIRMWARE_CODE=$2 ;;
        --firmware-vars) FIRMWARE_VARS=$2 ;;
        --installer-uki) INSTALLER_UKI=$2 ;;
        --boot-certificate) BOOT_CERTIFICATE=$2 ;;
        --recovery-key-file) RECOVERY_KEY_FILE=$2 ;;
      esac
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
    --help | -h)
      show_help
      exit 0
      ;;
    *)
      die "unknown argument: $1" 64
      ;;
  esac
done

if $TPM_STAGE; then
  readonly STORAGE_POOL='/var/lib/libvirt/images/hermes-tpm-lab'
else
  readonly STORAGE_POOL='/var/lib/libvirt/images'
fi
readonly DISK_PATH="$STORAGE_POOL/${VM_NAME}.qcow2"
readonly OEMDRV_PATH="$STORAGE_POOL/${VM_NAME}-oemdrv.iso"

if $DESTROY; then
  vm_cleanup "$VM_NAME"
  for path in "$DISK_PATH" "$OEMDRV_PATH"; do
    [[ -e "$path" ]] && run_cmd rm -f -- "$path"
  done
  exit 0
fi

[[ -r "$ISO_PATH" ]] || die "Fedora Server ISO is not readable: $ISO_PATH" 66
[[ -r "$KICKSTART_FILE" ]] || die "Fedora Server kickstart is not readable: $KICKSTART_FILE" 66
[[ -r "$SSH_KEY" ]] || die "SSH public key is not readable: $SSH_KEY" 66
if $TPM_STAGE; then
  for path in "$TPM_PUBLIC_KEY" "$FIRMWARE_CODE" "$FIRMWARE_VARS" "$INSTALLER_UKI" "$BOOT_CERTIFICATE"; do
    [[ "$path" == /* && "$path" != *,* && -f "$path" && ! -L "$path" && -r "$path" ]] \
      || die 'TPM staging needs regular absolute public-key and matching firmware paths without commas' 66
  done
  # Only a private, caller-owned random hex recovery file is accepted. Never print it.
  python3 - "$RECOVERY_KEY_FILE" <<'PYRECOVERY'
import os, re, stat, sys
fd = os.open(sys.argv[1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
with os.fdopen(fd, "rb") as source:
    info = os.fstat(source.fileno())
    if not (stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
            and not info.st_mode & 0o077 and re.fullmatch(rb"[a-f0-9]{64}\n?", source.read(66))):
        raise SystemExit(78)
PYRECOVERY
  openssl rsa -pubin -in "$TPM_PUBLIC_KEY" -noout >/dev/null 2>&1 \
    || die 'TPM staging needs a valid public key' 78
elif [[ -n "$TPM_PUBLIC_KEY$FIRMWARE_CODE$FIRMWARE_VARS$INSTALLER_UKI$BOOT_CERTIFICATE$RECOVERY_KEY_FILE" ]]; then
  die 'TPM/firmware inputs require --tpm-stage' 64
fi
if [[ "$UNLOCK_EVENT_LOG" != /dev/null ]]; then
  [[ -f "$UNLOCK_EVENT_LOG" && -w "$UNLOCK_EVENT_LOG" ]] \
    || die "unlock event log is not writable: $UNLOCK_EVENT_LOG" 66
fi
require_cmd virsh
require_cmd virt-install
require_cmd qemu-img
require_cmd xorriso
require_cmd python3
check_libvirt
check_storage_pool_writable "$STORAGE_POOL"
check_hermes_server_host_resources "$STORAGE_POOL"
vm_exists "$VM_NAME" && die "VM '$VM_NAME' already exists; destroy it before retrying" 73
for path in "$DISK_PATH" "$OEMDRV_PATH"; do
  [[ ! -e "$path" && ! -L "$path" ]] || die 'dedicated lab storage already exists; inspect recovery state before retrying' 73
done

SSH_KEY_CONTENT=$(awk '/^ssh-(ed25519|rsa|ecdsa)[[:space:]]+[A-Za-z0-9+\/=]+([[:space:]]|$)/ {print $1 " " $2; exit}' "$SSH_KEY")
[[ -n "$SSH_KEY_CONTENT" ]] || die 'SSH key file does not contain a supported public key' 66

detach_install_media() {
  local target
  log_info 'Removing installer media before booting the installed Server guest...'
  while IFS= read -r target; do
    [[ -n "$target" ]] || continue
    virsh -c "$VIRSH_URI" detach-disk "$VM_NAME" "$target" --config >/dev/null
  done < <(virsh -c "$VIRSH_URI" domblklist "$VM_NAME" --details | awk '$2 == "cdrom" {print $3}')
}

wait_for_install_shutdown() {
  local elapsed=0 state
  log_info 'Waiting for the unattended Fedora Server installation to finish...'
  while ((elapsed < 1800)); do
    state=$(virsh -c "$VIRSH_URI" domstate "$VM_NAME" 2>/dev/null || true)
    case "$state" in
      'shut off')
        log_info "Fedora Server installation powered off the VM (${elapsed}s)"
        return 0
        ;;
      crashed | pmsuspended)
        log_error "Fedora Server installation ended in VM state: $state"
        return 1
        ;;
    esac
    sleep 5
    elapsed=$((elapsed + 5))
  done
  log_error 'Fedora Server installation did not finish within 1800s'
  return 1
}

KS_TMPDIR=$(mktemp -d)
cleanup() {
  rm -rf -- "${KS_TMPDIR:-}"
}
trap cleanup EXIT
trap 'trap - INT EXIT; cleanup; kill -INT $$' INT
trap 'trap - TERM EXIT; cleanup; kill -TERM $$' TERM

cp -- "$KICKSTART_FILE" "$KS_TMPDIR/ks.cfg"
if $TPM_STAGE; then
  cp -- "$TPM_PUBLIC_KEY" "$KS_TMPDIR/tpm2-pcr-public-key.pem"
  cat "$SCRIPT_DIR/kickstart/hermes-tpm-enroll.ks" >>"$KS_TMPDIR/ks.cfg"
  python3 - "$RECOVERY_KEY_FILE" "$KS_TMPDIR/ks.cfg" <<'PYRECOVERY'
import os, re, stat, sys
from pathlib import Path
fd = os.open(sys.argv[1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
with os.fdopen(fd, "rb") as stream:
    info = os.fstat(stream.fileno())
    raw = stream.read(66)
    if not (stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
            and not info.st_mode & 0o077 and re.fullmatch(rb"[a-f0-9]{64}\n?", raw)):
        raise SystemExit(78)
path = Path(sys.argv[2])
path.write_text(path.read_text().replace("hermes-e2e-fixture", raw.decode().strip()))
PYRECOVERY
fi
sed -i "s|^# HERMES_SSH_KEY_PLACEHOLDER$|install -d -o lab -g lab -m 0700 /home/lab/.ssh\\nprintf '%s\\n' '$SSH_KEY_CONTENT' > /home/lab/.ssh/authorized_keys\\nchmod 0600 /home/lab/.ssh/authorized_keys\\nchown lab:lab /home/lab/.ssh/authorized_keys|" \
  "$KS_TMPDIR/ks.cfg"

if $TPM_STAGE; then
  run_cmd python3 "$SCRIPT_DIR/../scripts/hermes/unattended/efi_media.py" \
    --uki "$INSTALLER_UKI" --certificate "$BOOT_CERTIFICATE" --pcr-public-key "$TPM_PUBLIC_KEY" \
    --kickstart "$KS_TMPDIR/ks.cfg" --output "$OEMDRV_PATH"
else
  run_cmd xorriso -as mkisofs -quiet -V OEMDRV -o "$OEMDRV_PATH" "$KS_TMPDIR"
fi

NETWORK_XML="$SCRIPT_DIR/networks/lab-vlans.xml"
ensure_network "$NETWORK_XML" "$NETWORK"
ensure_dhcp_host "$NETWORK" "$VM_MAC" "$VM_IP" "$VM_NAME"
run_cmd qemu-img create -f qcow2 "$DISK_PATH" 40G
run_cmd chmod 0600 "$DISK_PATH"

BOOT_SPEC='uefi,firmware.feature0.name=secure-boot,firmware.feature0.enabled=yes,firmware.feature1.name=enrolled-keys,firmware.feature1.enabled=yes'
if $TPM_STAGE; then
  BOOT_SPEC="loader=$FIRMWARE_CODE,loader.readonly=yes,loader.type=pflash,loader.secure=yes,nvram.template=$FIRMWARE_VARS,nvram.templateFormat=raw"
fi
VIRT_INSTALL_ARGS=(
  --name "$VM_NAME"
  --memory "$HERMES_SERVER_DEFAULT_RAM"
  --vcpus "$HERMES_SERVER_DEFAULT_VCPUS"
  --disk "path=$DISK_PATH,format=qcow2,bus=virtio,boot.order=2"
  --network "network=$NETWORK,model=virtio,mac=$VM_MAC"
  --os-variant fedora-unknown
  --graphics vnc,listen=127.0.0.1
  --boot "$BOOT_SPEC"
  --serial pty
  --console pty,target_type=serial
  --noautoconsole
  --wait 0
)
if $TPM_STAGE; then
  # Match the dedicated domain accepted by the lab certifier and power helper.
  VIRT_INSTALL_ARGS+=(--uuid 4db6369a-2b8b-427f-a47a-a5d83bb40cff
    --machine q35 --features smm=on --tpm model=tpm-crb,backend.type=emulator,backend.version=2.0
    --disk "path=$OEMDRV_PATH,format=raw,bus=virtio,readonly=on,boot.order=1"
    --disk "path=$ISO_PATH,device=cdrom,bus=sata,readonly=on,boot.order=3" --import)
else
  VIRT_INSTALL_ARGS+=(--disk "path=$OEMDRV_PATH,device=cdrom,bus=sata,readonly=on,boot.order=3"
    --location "$ISO_PATH" --extra-args "$INSTALL_KERNEL_ARGS")
fi
run_cmd virt-install "${VIRT_INSTALL_ARGS[@]}"

if ! $DRY_RUN; then
  wait_for_install_shutdown
  detach_install_media
  if $TPM_STAGE; then
    media_target=$(virsh -c "$VIRSH_URI" domblklist "$VM_NAME" --details | awk -v source="$OEMDRV_PATH" '$4 == source {print $3}')
    [[ "$media_target" =~ ^vd[a-z]+$ ]] || die 'cannot identify the dedicated EFI installer disk for removal' 78
    virsh -c "$VIRSH_URI" detach-disk "$VM_NAME" "$media_target" --config >/dev/null
    log_info 'TPM installer stopped before first encrypted boot; signed UKI injection and boot verification are required'
    exit 0
  fi
  virsh -c "$VIRSH_URI" start "$VM_NAME" >/dev/null 2>&1 || true
  wait_vm_boot "$VM_NAME" 180
  unlock_server_fixture
  wait_ssh_ready "$VM_IP" 300 || {
    unlock_server_fixture
    wait_ssh_ready "$VM_IP" 180
  }
fi

if $TPM_STAGE; then
  log_info 'TPM staging commands prepared; first encrypted boot requires signed UKI injection'
else
  log_info "Fedora Server certification VM '$VM_NAME' is ready at $VM_IP"
fi
