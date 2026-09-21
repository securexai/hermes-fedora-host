#!/usr/bin/env bash
# Host-side wrapper installed as /usr/local/libexec/hermes-gate2/ and granted through
# a temporary sudoers drop-in. It takes NO arguments on purpose: the whole point of the
# grant is that its scope cannot be influenced at call time.
#
# It must be IDEMPOTENT and must verify its own preconditions. During the first attempt
# the installer DVD's tray ended up empty in the domain config (the running installer's
# device probing opened it, and an `attach-disk --config` then persisted the empty-tray
# state), so the guest booted to "No bootable option or device was found". This wrapper
# now ensures both optical media are present before restarting, instead of assuming it.
#
# Both opticals are placed on the SATA controller, which is the controller the installer
# demonstrably read during the first boot.
#
# There is deliberately no destroy/undefine/volume-delete here. `detach-disk` is used
# only to move the kickstart ISO to the SATA bus; it removes a device, not data.
set -euo pipefail
export LC_ALL=C

DOMAIN=lab-hermes-manual-r1
URI=qemu:///system
MEDIA_DIR=/var/lib/libvirt/boot/lab-hermes-manual-r1
DVD="$MEDIA_DIR/Fedora-Server-dvd-x86_64-44-1.7.iso"
KS_ISO="$MEDIA_DIR/ks.iso"

die() {
  printf 'STOP: %s\n' "$*" >&2
  exit 1
}
say() { printf '%s\n' "$*"; }

[ "$(id -u)" -eq 0 ] || die "must run as root"

# Media ownership, correctly: libvirt's dynamic_ownership chowns a domain's disk and
# CD files to the qemu user while it runs, so requiring root ownership was wrong and
# blocked the second attempt. What actually matters is (a) qemu can read the file and
# (b) no unprivileged human can replace it, i.e. it is not group/world writable.
for f in "$DVD" "$KS_ISO"; do
  [ -s "$f" ] || die "missing or empty media: $f"
  case "$(stat -c %U "$f")" in
    root | qemu) ;;
    *) die "$f is owned by $(stat -c %U "$f"), which is neither root nor qemu; refusing" ;;
  esac
  if [ -n "$(find "$f" -maxdepth 0 -perm /022 -print -quit)" ]; then
    die "$f is group/world-writable (mode $(stat -c %a "$f")); refusing"
  fi
  runuser -u qemu -- test -r "$f" || die "the qemu user cannot read $f"
done
say "media ownership and readability verified (root or qemu, not group/world-writable, qemu-readable)"

tray_source() { # <target>
  virsh -c "$URI" domblklist "$DOMAIN" --inactive 2>/dev/null | awk -v t="$1" '$1==t {print $2}'
}

# --- ensure the installer DVD occupies the sda tray --------------------------
sda_now=$(tray_source sda)
if [ "$sda_now" = "$DVD" ]; then
  say "installer media already in the sda tray"
else
  if [ -z "$sda_now" ] || [ "$sda_now" = "-" ]; then
    say "sda tray is empty; inserting the installer media"
    virsh -c "$URI" change-media "$DOMAIN" sda "$DVD" --insert --config
  else
    say "sda holds something else; replacing it with the installer media"
    virsh -c "$URI" change-media "$DOMAIN" sda "$DVD" --update --config
  fi
fi
[ "$(tray_source sda)" = "$DVD" ] || die "the installer media could not be placed in sda"

# --- ensure the kickstart ISO is attached on the SATA bus --------------------
xml=$(mktemp /run/gate2-ks-attach.XXXXXX.xml)
trap 'rm -f "$xml"' EXIT
cat >"$xml" <<XML
<disk type='file' device='cdrom'>
  <driver name='qemu' type='raw'/>
  <source file='$KS_ISO'/>
  <target dev='sdb' bus='sata'/>
  <readonly/>
</disk>
XML

ks_now=$(tray_source sdb)
if [ "$ks_now" = "$KS_ISO" ]; then
  bus=$(virsh -c "$URI" dumpxml "$DOMAIN" --inactive 2>/dev/null | awk "/dev='sdb'/{found=1} found&&/bus=/{print; exit}")
  case "$bus" in
    *"bus='sata'"*) say "kickstart media already attached on the sata bus" ;;
    *)
      say "kickstart media is attached on the wrong bus; moving it to sata"
      virsh -c "$URI" detach-disk "$DOMAIN" sdb --config
      virsh -c "$URI" attach-device "$DOMAIN" "$xml" --config
      ;;
  esac
else
  say "attaching the kickstart media on the sata bus"
  [ -n "$ks_now" ] && [ "$ks_now" != "-" ] && virsh -c "$URI" detach-disk "$DOMAIN" sdb --config || true
  virsh -c "$URI" attach-device "$DOMAIN" "$xml" --config
fi

say "-- media after preparation --"
virsh -c "$URI" domblklist "$DOMAIN" --inactive | sed 's/^/   /'
[ "$(tray_source sdb)" = "$KS_ISO" ] || die "the kickstart media is not attached"

# --- restart so the installer boots with both media --------------------------
if virsh -c "$URI" domstate "$DOMAIN" 2>/dev/null | grep -qi running; then
  virsh -c "$URI" destroy "$DOMAIN"
fi
virsh -c "$URI" start "$DOMAIN"
say "installer restarted with verified media; the unattended install should begin"
