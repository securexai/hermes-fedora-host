#!/usr/bin/env bash
# Build the Gate 2 unattended kickstart and its OEMDRV ISO.
#
# The install media, the disk layout and the admin account are fixed by the approved
# plan. This helper prompts for the lab password locally and never prints it, never
# writes it in plaintext, and never passes it on a command line.
#
#   sudo bash gate2-make-kickstart.sh
#
# Then, on the hypervisor (all root, all reversible):
#   sudo virsh attach-disk lab-hermes-manual-r1 <dir>/ks.iso sdb --type cdrom --mode readonly --config
#   sudo virsh destroy lab-hermes-manual-r1     # power off the idle installer
#   sudo virsh start   lab-hermes-manual-r1     # installer re-runs and reads OEMDRV
#
# Anaconda reads a volume labelled OEMDRV automatically, so no kernel arguments need
# editing. Output directory must be readable by the qemu user.
set -euo pipefail
export LC_ALL=C

DOMAIN=lab-hermes-manual-r1
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TEMPLATE="$HERE/gate2-kickstart.ks.in"
OUT_DIR="${GATE2_KS_DIR:-/var/lib/libvirt/boot/$DOMAIN}"

die() {
  printf 'STOP: %s\n' "$*" >&2
  exit 1
}
say() { printf '%s\n' "$*"; }

# --reuse-hash rebuilds the ISO from the stored hash without prompting, so the media can
# be regenerated after a template fix without the operator being present. The hash is
# never printed; only the substituted file's own hash is reported.
MODE=build
case "${1:-}" in
  '' | --build) MODE=build ;;
  --reuse-hash) MODE=--reuse-hash ;;
  *) die "unknown mode: $1 (use --build or --reuse-hash)" ;;
esac

# sudo resets HOME to the target user's home, so $HOME is /root when this runs under
# sudo and the invoking user's key would never be found. Resolve the INVOKING user's
# home through SUDO_USER instead. (A first version of this helper got that wrong and
# refused to build the ISO.)
invoking_home() {
  local user="${SUDO_USER:-${USER:-root}}" home
  home=$(getent passwd "$user" | cut -d: -f6)
  [ -n "$home" ] || die "cannot resolve the home directory of $user"
  printf '%s\n' "$home"
}

INVOKING_HOME=$(invoking_home)
DEFAULT_KEY_FILE="$INVOKING_HOME/.local/state/hermes-manual-lab/id_ed25519.pub"
KEY_FILE="${GATE2_SSH_PUBLIC_KEY_FILE:-$DEFAULT_KEY_FILE}"
SSH_PUBLIC_KEY="${GATE2_SSH_PUBLIC_KEY:-$(cat "$KEY_FILE" 2>/dev/null || true)}"

[ -r "$TEMPLATE" ] || die "kickstart template not found: $TEMPLATE"
[ -n "$SSH_PUBLIC_KEY" ] || die "no SSH public key: nothing readable at $KEY_FILE (invoking user ${SUDO_USER:-${USER:-root}}); set GATE2_SSH_PUBLIC_KEY_FILE or GATE2_SSH_PUBLIC_KEY"
case "$SSH_PUBLIC_KEY" in
  ssh-ed25519\ * | ssh-rsa\ *) ;;
  *) die "the SSH public key does not look like an OpenSSH public key" ;;
esac
command -v genisoimage >/dev/null 2>&1 || die "genisoimage is required"
command -v openssl >/dev/null 2>&1 || die "openssl is required to hash the password"

install -d -m 0711 "$OUT_DIR" 2>/dev/null || true
[ -d "$OUT_DIR" ] || die "cannot create $OUT_DIR"
[ -w "$OUT_DIR" ] || die "$OUT_DIR is not writable; run with sudo or set GATE2_KS_DIR to a writable directory"

HASH_FILE="$OUT_DIR/guest-password.hash"
if [ "$MODE" = "--reuse-hash" ]; then
  [ -r "$HASH_FILE" ] || die "no stored password hash at $HASH_FILE; run once without --reuse-hash to create it"
  HASH=$(tr -d '[:space:]' <"$HASH_FILE")
  case "$HASH" in
    \$6\$*) ;;
    *) die "the stored hash at $HASH_FILE is not SHA-512 crypt; refusing" ;;
  esac
  say "reusing the stored password hash (not displayed)"
else
  # Password is read hidden from stdin; a pipe works too, which is how the helper's own
  # self-test exercises it. The plaintext is never persisted.
  if [ ! -t 0 ]; then
    say "reading the password from standard input (hidden input expected on a terminal)"
  fi
  printf 'Password for the guest administrator account: ' >&2
  IFS= read -r -s PW1
  printf '\nConfirm again: ' >&2
  IFS= read -r -s PW2
  printf '\n' >&2
  [ -n "$PW1" ] || die "empty password"
  [ "$PW1" = "$PW2" ] || die "the two entries do not match"
  HASH=$(printf '%s' "$PW1" | openssl passwd -6 -stdin)
  unset PW1 PW2
  [ -n "$HASH" ] || die "password hashing failed"
  (
    umask 077
    printf '%s\n' "$HASH" >"$HASH_FILE"
  )
  chmod 0600 "$HASH_FILE"
  say "stored the password hash at $HASH_FILE (0600 root) so the media can be rebuilt unattended"
fi

KS="$OUT_DIR/ks.cfg"
ISO="$OUT_DIR/ks.iso"

# Assembled as a single line with the '=' option form, which is what the successful
# install used. The hash is only ever written into the generated ks.cfg (0600, root).
USER_DIRECTIVE="user --name=aicowork --groups=wheel --homedir=/home/aicowork --shell=/bin/bash --password=$HASH --iscrypted"

python3 - "$TEMPLATE" "$KS" "$HASH" "$SSH_PUBLIC_KEY" "$USER_DIRECTIVE" <<'PY'
import hashlib, pathlib, sys
template, out, pw_hash, key, user_directive = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
text = pathlib.Path(template).read_text(encoding="utf-8")
for placeholder, value in (("@@ADMIN_USER_DIRECTIVE@@", user_directive), ("@@SSH_PUBLIC_KEY@@", key)):
    if placeholder not in text:
        raise SystemExit(f"STOP: template is missing {placeholder}")
    text = text.replace(placeholder, value)
text = text.replace("@@KS_SHA256@@", hashlib.sha256(text.encode()).hexdigest())
pathlib.Path(out).write_text(text, encoding="utf-8")
PY
unset HASH
chmod 0600 "$KS"
if grep -q '@@' "$KS"; then
  die "unsubstituted placeholder remains in $KS"
fi

rm -f "$ISO"
genisoimage -quiet -o "$ISO" -V OEMDRV -J -R "$KS" >/dev/null 2>&1 || die "could not build $ISO"
chmod 0640 "$ISO"
chgrp qemu "$ISO" 2>/dev/null || true
[ -s "$ISO" ] || die "the kickstart ISO is empty"

say ""
say "kickstart ready:"
say "  ks.cfg : $KS (0600 root; contains the password hash)"
say "  ks.iso : $ISO (0640 root:qemu, volume label OEMDRV)"
say "  layout : /boot/efi 1G, /boot 2G, then LVM vg_hermes:"
say "           / 20G, /var 15G, /home/hermes 30G (required), swap 4G"
say "  encryption: none (deviation D-01); rootpw locked; aicowork in wheel; Secure Boot untouched"
say ""
say "Next, on the hypervisor:"
say "  sudo virsh attach-disk $DOMAIN $ISO sdb --type cdrom --mode readonly --config"
say "  sudo virsh destroy $DOMAIN   # power off the idle installer (no data on the disk yet)"
say "  sudo virsh start $DOMAIN     # installer re-runs and reads the OEMDRV volume"
