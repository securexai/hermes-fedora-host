#!/usr/bin/env bash
# Hypervisor-side lifecycle for the retained, encrypted DeepSeek acceptance VM.
# --check (default) only inspects; --create converges to the one exact VM;
# --verify attests it; --finalize converges active and saved install media.
# There is no destroy, undefine, volume-delete, or force-stop mode. A partial
# disk or domain mismatch is retained for diagnosis and is never overwritten.
set -Eeuo pipefail
export LC_ALL=C

DOMAIN=lab-hermes-deepseek-e2e-r1
UUID=4349a2bc-67b6-42b7-a6ef-5aeee5ee4009
MAC=52:54:00:83:bf:4b
URI=qemu:///system
NETWORK=fvh-nat
VCPUS=2
MEMORY_MIB=12288
DISK_GIB=120
POOL_NAME=${HERMES_LIBVIRT_POOL:-default}
ISO_NAME=Fedora-Server-dvd-x86_64-44-1.7.iso
CHECKSUM_NAME=Fedora-Server-44-1.7-x86_64-CHECKSUM
MIN_FREE_GIB=140
MIN_FREE_INODES=1000000

fail() {
  printf 'STOP: %s\n' "$*" >&2
  exit 1
}
need_root() { [ "$(id -u)" -eq 0 ] || fail 'run on the hypervisor as root through a private authentication prompt'; }
need_tool() { command -v "$1" >/dev/null || fail "missing tool: $1"; }

MODE=${1:---check}
case "$MODE" in --check | --create | --verify | --finalize) ;; *) fail 'use --check, --create, --verify or --finalize' ;; esac
[ "$#" -le 1 ] || fail 'unexpected arguments'
need_root
for tool in virsh virt-install gpgv sha256sum awk df stat ip runuser qemu-img python3 realpath; do need_tool "$tool"; done
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(realpath -e -- "$SCRIPT_DIR/../../../..")
POOL_DIR=$(virsh -c "$URI" pool-dumpxml "$POOL_NAME" | python3 -c '
import sys, xml.etree.ElementTree as ET
path=ET.fromstring(sys.stdin.read()).findtext("./target/path")
if not path or not path.startswith("/"):
    raise SystemExit("libvirt pool has no absolute target path")
print(path)') || fail "cannot discover libvirt pool $POOL_NAME"
GUEST_DIR="$POOL_DIR/$DOMAIN"
DISK="$GUEST_DIR/disk.qcow2"
STAGE_DIR="$GUEST_DIR/install-media"

# Collect all existing definitions. A failed inventory is a hard stop; it is
# never interpreted as an empty host. Compare the candidate identity and disk
# against every definition, including guests that are shut off.
get_domains() { virsh -c "$URI" list --all --name; }
verify_other_collisions() {
  local domains other xml
  domains=$(get_domains) || fail 'cannot list existing domains'
  while IFS= read -r other; do
    [ -n "$other" ] || continue
    [ "$other" != "$DOMAIN" ] || continue
    xml=$(virsh -c "$URI" dumpxml "$other") || fail "cannot inspect domain $other"
    ! grep -Fiq -- "$UUID" <<<"$xml" || fail "UUID collision with $other"
    ! grep -Fiq -- "$MAC" <<<"$xml" || fail "MAC collision with $other"
    ! grep -Fq -- "$DISK" <<<"$xml" || fail "disk collision with $other"
  done <<<"$domains"
}

verify_absent() {
  local links leases
  [ ! -e "$DISK" ] || fail "orphaned target disk exists: $DISK; preserve for diagnosis"
  verify_other_collisions
  links=$(ip -o link) || fail 'cannot inspect host interfaces'
  ! grep -Fiq -- "$MAC" <<<"$links" || fail 'candidate MAC collides with a host interface'
  leases=$(virsh -c "$URI" net-dhcp-leases "$NETWORK") || fail 'cannot inspect network leases'
  ! grep -Fiq -- "$MAC" <<<"$leases" || fail 'candidate MAC already has a network lease'
}

verify_media() {
  local expected actual count
  [ -r "$ISO" ] || fail "ISO missing: $ISO"
  [ -r "$CHECKSUM" ] || fail "signed checksum missing: $CHECKSUM"
  [ -r "$KEYRING" ] || fail "Fedora keyring missing: $KEYRING"
  gpgv --keyring "$KEYRING" "$CHECKSUM" >/dev/null 2>&1 || fail 'Fedora checksum signature failed'
  count=$(awk -F ' = ' -v name="SHA256 ($ISO_NAME)" '$1 == name {n++} END {print n+0}' "$CHECKSUM")
  [ "$count" -eq 1 ] || fail 'expected exactly one ISO hash in signed checksum'
  expected=$(awk -F ' = ' -v name="SHA256 ($ISO_NAME)" '$1 == name {print $2}' "$CHECKSUM")
  actual=$(sha256sum "$ISO" | awk '{print $1}')
  [ "$actual" = "$expected" ] || fail 'Fedora ISO hash mismatch'
  printf 'media_signature=PASS iso_sha256=%s\n' "$actual"
}

verify_capacity() {
  local cpus mem_kib free_gib free_inodes
  cpus=$(getconf _NPROCESSORS_ONLN)
  mem_kib=$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)
  free_gib=$(df -BG --output=avail "$POOL_DIR" | tail -n1 | tr -dc '0-9')
  free_inodes=$(df --output=iavail "$POOL_DIR" | tail -n1 | tr -dc '0-9')
  [ "$cpus" -ge "$VCPUS" ] || fail 'insufficient CPUs'
  [ "$mem_kib" -ge 14680064 ] || fail 'less than 14 GiB MemAvailable'
  [ "${free_gib:-0}" -ge "$MIN_FREE_GIB" ] || fail 'insufficient free storage'
  [ "${free_inodes:-0}" -ge "$MIN_FREE_INODES" ] || fail 'insufficient free inodes'
  printf 'capacity=PASS cpus=%s mem_available_kib=%s pool_free_gib=%s inodes=%s\n' \
    "$cpus" "$mem_kib" "$free_gib" "$free_inodes"
}

verify_network() {
  local info
  info=$(virsh -c "$URI" net-info "$NETWORK") || fail "network $NETWORK unavailable"
  grep -Eq '^Active:[[:space:]]+yes$' <<<"$info" || fail "network $NETWORK is not active"
  printf 'network=PASS name=%s\n' "$NETWORK"
}

# An exact, immutable domain definition is built in both check and create modes.
# --dry-run is required: --print-xml alone can allocate storage.
vm_args=(
  --connect "$URI" --name "$DOMAIN" --metadata "uuid=$UUID"
  --memory "$MEMORY_MIB" --vcpus "$VCPUS" --cpu host-passthrough
  --machine q35
  --boot firmware=efi,firmware.feature0.name=secure-boot,firmware.feature0.enabled=yes,firmware.feature1.name=enrolled-keys,firmware.feature1.enabled=yes
  --tpm backend.type=emulator,backend.version=2.0,model=tpm-crb
  --osinfo detect=on,require=off
  --network "network=$NETWORK,model=virtio,mac=$MAC"
  --graphics vnc,listen=127.0.0.1
  --noautoconsole
)

verify_existing() {
  virsh -c "$URI" dumpxml "$DOMAIN" | python3 -c '
import sys, xml.etree.ElementTree as ET
name, uuid, mac, disk, network, memory_mib, vcpus = sys.argv[1:]
r = ET.fromstring(sys.stdin.read())
def check(ok, message):
    if not ok:
        raise SystemExit("domain definition mismatch: " + message)
check(r.findtext("name") == name, "name")
check(r.findtext("uuid") == uuid, "UUID")
mem = r.find("memory")
check(mem is not None and mem.get("unit") == "KiB" and int(mem.text) == int(memory_mib)*1024, "memory")
check(r.findtext("vcpu") == vcpus, "vCPUs")
features = r.findall("./os/firmware/feature")
check(any(x.get("name") == "secure-boot" and x.get("enabled") == "yes" for x in features), "Secure Boot")
check(any(x.get("name") == "enrolled-keys" and x.get("enabled") == "yes" for x in features), "enrolled keys")
loader = r.find("./os/loader")
check(loader is not None and loader.get("secure") == "yes", "secure UEFI loader")
tpm = r.find("./devices/tpm")
check(tpm is not None and tpm.get("model") == "tpm-crb", "TPM model")
backend = tpm.find("backend")
check(backend is not None and backend.get("type") == "emulator" and backend.get("version") == "2.0", "TPM backend")
check(any(x.get("file") == disk for x in r.findall("./devices/disk/source")), "disk")
check(any(i.find("mac") is not None and i.find("mac").get("address", "").lower() == mac.lower()
          and i.find("source") is not None and i.find("source").get("network") == network
          for i in r.findall("./devices/interface")), "MAC/network")
print("existing_identity=PASS domain=%s uuid=%s mac=%s disk=%s" % (name, uuid, mac, disk))' \
    "$DOMAIN" "$UUID" "$MAC" "$DISK" "$NETWORK" "$MEMORY_MIB" "$VCPUS" \
    || fail "domain $DOMAIN failed definition attestation"
}

verify_disk() {
  qemu-img info -U --output=json "$DISK" | python3 -c '
import json,sys
info=json.load(sys.stdin)
assert info["format"] == "qcow2"
assert info["virtual-size"] == 120 * 1024**3
assert info["actual-size"] < info["virtual-size"]
print("sparse_disk=PASS virtual_bytes=%s actual_bytes=%s" % (info["virtual-size"],info["actual-size"]))'
}

domains=$(get_domains) || fail 'cannot list existing domains'
if grep -Fxq -- "$DOMAIN" <<<"$domains"; then
  verify_other_collisions
  verify_existing
  verify_disk
  if [ "$MODE" = --verify ]; then
    printf 'VERIFY=PASS retained_domain=%s\n' "$DOMAIN"
    exit 0
  fi
  if [ "$MODE" = --finalize ]; then
    # A running installer can retain an active ISO even when virt-install left
    # the persistent CD-ROM empty. Inspect and converge both views separately.
    active=$(virsh -c "$URI" domblklist "$DOMAIN" --details) || fail 'cannot inspect active block devices'
    saved=$(virsh -c "$URI" domblklist "$DOMAIN" --details --inactive) || fail 'cannot inspect saved block devices'
    parse_cdrom() {
      awk '$2 == "cdrom" {n++; target=$3; source=$4} END {if (n != 1) exit 1; print target, source}'
    }
    active_cdrom=$(parse_cdrom <<<"$active") || fail 'expected one active CD-ROM'
    saved_cdrom=$(parse_cdrom <<<"$saved") || fail 'expected one saved CD-ROM'
    read -r active_target active_source <<<"$active_cdrom"
    read -r saved_target saved_source <<<"$saved_cdrom"
    [ "$active_target" = "$saved_target" ] || fail 'active and saved CD-ROM targets differ'
    for source in "$active_source" "$saved_source"; do
      [ "$source" = '-' ] || [ "${source##*/}" = "$ISO_NAME" ] \
        || fail 'unexpected install media source; preserve definition'
    done
    changed=0
    if [ "$saved_source" != '-' ]; then
      virsh -c "$URI" change-media "$DOMAIN" "$saved_target" --eject --config \
        || fail 'could not eject install media from persistent definition'
      changed=1
    fi
    if [ "$active_source" != '-' ]; then
      virsh -c "$URI" change-media "$DOMAIN" "$active_target" --eject --live \
        || fail 'could not eject install media from active domain; retry after graceful shutdown'
      changed=1
    fi
    if [ "$changed" -eq 0 ]; then
      printf 'FINALIZE=UNCHANGED media_target=%s retained_domain=%s\n' "$active_target" "$DOMAIN"
    else
      printf 'FINALIZE=CHANGED media_target=%s retained_domain=%s\n' "$active_target" "$DOMAIN"
    fi
    exit 0
  fi
  printf '%s=UNCHANGED retained_domain=%s\n' "${MODE#--}" "$DOMAIN"
  exit 0
fi
[ "$MODE" != --verify ] && [ "$MODE" != --finalize ] || fail "domain $DOMAIN does not exist"

[ -n "${HERMES_MEDIA_DIR:-}" ] || fail 'set HERMES_MEDIA_DIR to the verified Fedora media directory'
case "$HERMES_MEDIA_DIR" in
  /*) MEDIA_DIR=$(realpath -e -- "$HERMES_MEDIA_DIR") ;;
  *) MEDIA_DIR=$(realpath -e -- "$REPO_ROOT/$HERMES_MEDIA_DIR") ;;
esac
ISO="$MEDIA_DIR/$ISO_NAME"
CHECKSUM="$MEDIA_DIR/$CHECKSUM_NAME"
KEYRING="$MEDIA_DIR/fedora.gpg"
verify_absent
verify_capacity
verify_network
verify_media

if [ "$MODE" = --check ]; then
  virt-install "${vm_args[@]}" --dry-run --print-xml \
    --disk "path=$POOL_DIR/$DOMAIN.check.qcow2,size=$DISK_GIB,format=qcow2,bus=virtio,discard=unmap" \
    --cdrom "$ISO" >/dev/null || fail 'virt-install rejected the proposed UEFI/vTPM definition'
  printf 'PREFLIGHT=PASS domain=%s uuid=%s mac=%s memory_mib=%s disk_gib=%s\n' \
    "$DOMAIN" "$UUID" "$MAC" "$MEMORY_MIB" "$DISK_GIB"
  exit 0
fi

# The target disk is absent. A retry may safely complete a media-only partial
# setup; it never overwrites an orphaned disk or mismatched domain.
install -d -m 0711 "$GUEST_DIR" "$STAGE_DIR"
media_tmp="$STAGE_DIR/.$ISO_NAME.tmp.$$"
trap 'rm -f -- "$media_tmp"' EXIT
cp --reflink=auto -- "$ISO" "$media_tmp"
chmod 0644 "$media_tmp"
staged_sha=$(sha256sum "$media_tmp" | awk '{print $1}')
expected_sha=$(sha256sum "$ISO" | awk '{print $1}')
[ "$staged_sha" = "$expected_sha" ] || fail 'staged ISO hash mismatch'
if [ -f "$STAGE_DIR/$ISO_NAME" ] && cmp -s "$media_tmp" "$STAGE_DIR/$ISO_NAME"; then
  rm -f -- "$media_tmp"
else
  mv -f -- "$media_tmp" "$STAGE_DIR/$ISO_NAME"
fi
trap - EXIT
runuser -u qemu -- test -r "$STAGE_DIR/$ISO_NAME" || fail 'qemu cannot read staged ISO'
virt-install "${vm_args[@]}" \
  --disk "path=$DISK,size=$DISK_GIB,format=qcow2,bus=virtio,discard=unmap" \
  --cdrom "$STAGE_DIR/$ISO_NAME" || fail 'virt-install failed; preserve guest artifacts for diagnosis'
verify_existing
verify_disk
printf 'CREATE=PASS retained_domain=%s; install Fedora interactively using the private console\n' "$DOMAIN"
