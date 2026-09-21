#!/usr/bin/env bash
# Gate 2 fixture lifecycle (HYPERVISOR-SIDE).
#
# Authorized by docs/plans/2026-09-20-hermes-manual-gate2-lab-plan.md (record state ACTIVE):
# guest `lab-hermes-manual-r1`, 2 vCPU / 8 GiB / 80 GiB, network `fvh-nat`, fresh identity.
#
# Modes
#   --check     (default, no root needed) verify capacity, media signature/hash, absence of the
#               retired fixture, and that the domain definition is accepted. Creates nothing.
#   --create    (root) create the guest exactly as authorized. Refuses if any check fails.
#   --finalize  (root) after the install: eject the install media and boot from disk.
#
# There is deliberately NO destroy/undefine/volume-delete mode. Retained diagnostics and the
# Gate 3 fixture must not be destroyed without explicit user approval.
#
# This is a hypervisor-side action script, not a guest helper: it does not source the guest
# safety library and it keeps no CHECK accounting. Its contract is: preflight or abort.
set -euo pipefail
export LC_ALL=C

DOMAIN=lab-hermes-manual-r1
RETIRED_MARKERS=(lab-hermes-server lab-vlans 172.16.99)
VCPUS=2
MEMORY_MIB=8192
DISK_GIB=80
NETWORK=fvh-nat
POOL_DIR=/var/lib/libvirt/images
GUEST_DIR="$POOL_DIR/$DOMAIN"
DISK="$GUEST_DIR/disk.qcow2"
MIN_FREE_GIB=120
MIN_FREE_INODES=1000000
# Install media in a user home is usually unreadable by the qemu user: Fedora homes are
# 0700, and QEMU runs as `qemu`, not as root. If the source is not readable by qemu the
# script stages a verified copy here, which is root-owned and qemu-traversable.
ISO_STAGE_DIR="${GATE2_ISO_STAGE_DIR:-/var/lib/libvirt/boot/$DOMAIN}"
URI=qemu:///system
ISO_RELEASE=Fedora-Server-dvd-x86_64-44-1.7.iso
CHECKSUM_RELEASE=Fedora-Server-44-1.7-x86_64-CHECKSUM

die() {
  printf 'STOP: %s\n' "$*" >&2
  exit 1
}
say() { printf '%s\n' "$*"; }

# Can the hypervisor's own user read this path? Only root can answer definitively,
# because switching to the qemu account requires privilege.
qemu_can_read() {
  [ "$(id -u)" -eq 0 ] || return 2
  runuser -u qemu -- test -r "$1" 2>/dev/null
}

# Unprivileged heuristic: every ancestor directory must be traversable by others.
static_access_ok() {
  local path="$1" dir
  dir=$(dirname "$path")
  while [ "$dir" != "/" ]; do
    [ -x "$dir" ] || return 1
    case "$(stat -c %A "$dir")" in
      ?????????x) ;;
      *) return 1 ;;
    esac
    dir=$(dirname "$dir")
  done
  return 0
}

invoking_home() {
  local user="${SUDO_USER:-${USER:-root}}" home
  home=$(getent passwd "$user" | cut -d: -f6)
  [ -n "$home" ] || die "cannot resolve the home directory of $user"
  printf '%s\n' "$home"
}

HOME_DIR=$(invoking_home)
ISO_DIR="${GATE2_ISO_DIR:-$HOME_DIR/Downloads/fedora-server-44-1.7}"
ISO="$ISO_DIR/$ISO_RELEASE"
CHECKSUM="$ISO_DIR/$CHECKSUM_RELEASE"
KEYRING="$ISO_DIR/fedora.gpg"

MODE=--check
case "${1:-}" in
  '' | --check) MODE=--check ;;
  --create) MODE=--create ;;
  --finalize) MODE=--finalize ;;
  *) die "unknown mode: $1 (use --check, --create or --finalize)" ;;
esac

# --------------------------------------------------------------------- finalize
# Acts on an EXISTING domain. It must not run the create-oriented preflight (capacity,
# media verification, media staging) and must not apply the create guard. The previous
# version refused to run, which is the bug this branch fixes.
if [ "$MODE" = "--finalize" ]; then
  say "=== Gate 2 fixture finalize ==="
  say "domain=$DOMAIN mode=$MODE"
  for marker in "${RETIRED_MARKERS[@]}"; do
    if virsh -c "$URI" list --all --name 2>/dev/null | grep -qi -- "$marker"; then
      die "a retired identifier '$marker' still exists as a domain; refusing to proceed"
    fi
  done
  virsh -c "$URI" dominfo "$DOMAIN" >/dev/null 2>&1 || die "domain $DOMAIN does not exist"
  [ "$(id -u)" -eq 0 ] || die "mode --finalize requires root (this account has no passwordless sudo)"
  virsh -c "$URI" domblklist "$DOMAIN" | sed 's/^/  /'
  media=$(virsh -c "$URI" domblklist "$DOMAIN" | awk '$2 ~ /cdrom|sr0/ {print $1}' | head -n1)
  [ -n "$media" ] || die "could not identify the install media target"
  virsh -c "$URI" change-media "$DOMAIN" "$media" --eject --config || true
  virsh -c "$URI" dumpxml "$DOMAIN" >"/root/$DOMAIN.postinstall.xml"
  say "install media ejected on $media; XML saved to /root/$DOMAIN.postinstall.xml"
  say "next: verify the guest boots from disk, not from the installer."
  exit 0
fi

# --------------------------------------------------------------------- preflight
say "=== Gate 2 fixture preflight ==="
say "domain=$DOMAIN mode=$MODE"

for marker in "${RETIRED_MARKERS[@]}"; do
  if virsh -c "$URI" list --all --name 2>/dev/null | grep -qi -- "$marker"; then
    die "a retired identifier '$marker' still exists as a domain; refusing to proceed"
  fi
  if virsh -c "$URI" net-list --all --name 2>/dev/null | grep -qi -- "$marker"; then
    die "retired network '$marker' is present; refusing to proceed"
  fi
done
virsh -c "$URI" net-list --all --name 2>/dev/null | grep -qx "$NETWORK" \
  || die "network $NETWORK does not exist"
say "no retired identifier present; network $NETWORK exists"

avail_gib=$(df -BG --output=avail "$POOL_DIR" | tail -1 | tr -dc '0-9')
free_inodes=$(df --output=iavail "$POOL_DIR" | tail -1 | tr -dc '0-9')
say "pool available=${avail_gib}GiB free_inodes=${free_inodes} (floors ${MIN_FREE_GIB}GiB / ${MIN_FREE_INODES})"
[ "${avail_gib:-0}" -ge "$MIN_FREE_GIB" ] || die "insufficient pool capacity; not creating the fixture"
[ "${free_inodes:-0}" -ge "$MIN_FREE_INODES" ] || die "insufficient inodes; not creating the fixture"

[ -r "$ISO" ] || die "install ISO not found: $ISO (set GATE2_ISO_DIR)"
[ -r "$CHECKSUM" ] || die "signed CHECKSUM not found: $CHECKSUM"
[ -r "$KEYRING" ] || die "Fedora keyring not found: $KEYRING"
gpgv --keyring "$KEYRING" "$CHECKSUM" >/dev/null 2>&1 \
  || die "the CHECKSUM file's signature does not verify against $KEYRING"
expected=$(grep -oE '[0-9a-f]{64}' "$CHECKSUM" | head -n1)
[ -n "$expected" ] || die "could not read the expected SHA-256 from the signed CHECKSUM"
actual=$(sha256sum "$ISO" | cut -d' ' -f1)
[ "$expected" = "$actual" ] || die "ISO hash mismatch: expected $expected, got $actual"
say "media verified: signature OK, sha256=$actual"

# Determine the usable media path before anything is allocated.
ISO_USE="$ISO"
if qemu_can_read "$ISO"; then
  say "media is readable by the qemu user at its current location"
elif [ "$(id -u)" -eq 0 ]; then
  say "media is NOT readable by the qemu user at $ISO"
  say "staging a verified copy under $ISO_STAGE_DIR"
  install -d -m 0711 "$ISO_STAGE_DIR"
  cp -f --reflink=auto "$ISO" "$ISO_STAGE_DIR/$ISO_RELEASE"
  cp -f "$CHECKSUM" "$ISO_STAGE_DIR/$CHECKSUM_RELEASE"
  cp -f "$KEYRING" "$ISO_STAGE_DIR/fedora.gpg"
  staged="$ISO_STAGE_DIR/$ISO_RELEASE"
  gpgv --keyring "$ISO_STAGE_DIR/fedora.gpg" "$ISO_STAGE_DIR/$CHECKSUM_RELEASE" >/dev/null 2>&1 \
    || die "the staged CHECKSUM copy does not verify"
  staged_actual=$(sha256sum "$staged" | cut -d' ' -f1)
  [ "$staged_actual" = "$expected" ] || die "staged copy hash mismatch: $staged_actual"
  ISO_USE="$staged"
  say "staged copy verified: sha256=$staged_actual"
else
  if static_access_ok "$ISO"; then
    say "WARNING: cannot confirm qemu readability without root; the create step will verify it"
  else
    say "media is not traversable by other users; create mode will stage a verified copy under $ISO_STAGE_DIR"
  fi
fi

if virsh -c "$URI" dominfo "$DOMAIN" >/dev/null 2>&1; then
  if [ "$MODE" = "--create" ]; then
    die "domain $DOMAIN already exists; refusing to recreate it"
  fi
  say "NOTE: domain $DOMAIN already exists (--check only reports this)"
fi

if [ "$MODE" = "--check" ]; then
  say ""
  # --dry-run is REQUIRED: bare --print-xml still performs storage creation, and an
  # explicit step number means "print that install phase", not "print only". Both
  # mistakes were made and caught during planning; the domain count, volume count and
  # absence of the guest directory were re-verified after the check.
  #
  # The disk path here sits directly in the pool root because virt-install resolves the
  # parent directory during volume allocation, and the per-guest directory does not exist
  # until --create makes it. Only the path differs; every other option is identical.
  say "=== domain definition (no mutation; --dry-run --print-xml) ==="
  virt-install --connect "$URI" --dry-run --print-xml \
    --name "$DOMAIN" \
    --memory "$MEMORY_MIB" --vcpus "$VCPUS" --cpu host-passthrough \
    --machine q35 \
    --boot firmware=efi,firmware.feature0.name=secure-boot,firmware.feature0.enabled=yes,firmware.feature1.name=enrolled-keys,firmware.feature1.enabled=yes \
    --osinfo detect=on,require=off \
    --disk "path=$POOL_DIR/$DOMAIN.check.qcow2,size=$DISK_GIB,format=qcow2,bus=virtio,discard=unmap" \
    --network "network=$NETWORK,model=virtio" \
    --graphics "vnc,listen=127.0.0.1" \
    --cdrom "$ISO_USE" \
    --noautoconsole || die "the domain definition was rejected by virt-install"
  say ""
  say "PREFLIGHT=PASS (nothing created)"
  exit 0
fi

[ "$(id -u)" -eq 0 ] || die "mode $MODE requires root (this account has no passwordless sudo)"

# Fail closed BEFORE allocating a disk: the first attempt at this fixture failed here.
if ! qemu_can_read "$ISO_USE"; then
  die "the install media at $ISO_USE is still not readable by the qemu user; refusing to allocate a disk"
fi
say "media confirmed readable by the qemu user: $ISO_USE"

say ""
say "=== creating $DOMAIN ==="
install -d -m 0711 "$GUEST_DIR"
virt-install --connect "$URI" \
  --name "$DOMAIN" \
  --memory "$MEMORY_MIB" --vcpus "$VCPUS" --cpu host-passthrough \
  --machine q35 \
  --boot firmware=efi,firmware.feature0.name=secure-boot,firmware.feature0.enabled=yes,firmware.feature1.name=enrolled-keys,firmware.feature1.enabled=yes \
  --osinfo detect=on,require=off \
  --disk "path=$DISK,size=$DISK_GIB,format=qcow2,bus=virtio,discard=unmap" \
  --network "network=$NETWORK,model=virtio" \
  --graphics "vnc,listen=127.0.0.1" \
  --cdrom "$ISO_USE" \
  --noautoconsole

say ""
say "=== created ==="
virsh -c "$URI" dominfo "$DOMAIN" | sed 's/^/  /'
say "-- interfaces (fresh MAC required) --"
virsh -c "$URI" domiflist "$DOMAIN" | sed 's/^/  /'
say "-- VNC endpoint (loopback only) --"
virsh -c "$URI" domdisplay "$DOMAIN" | sed 's/^/  /'
say "-- disk --"
ls -l "$DISK" | sed 's/^/  /'
say ""
say "NEXT: connect to the loopback VNC endpoint and install Fedora Server 44 with encrypted"
say "storage and a dedicated /home/hermes filesystem. Do not type the LUKS passphrase anywhere"
say "except the guest console."
