#!/usr/bin/env bash
# Rebuild the kickstart ISO from the ROOT-OWNED installed generator without
# prompting for the guest password (the hash is read from the root-owned hash
# file written by the first build).
#
# Installed as /usr/local/libexec/hermes-gate2/ and granted through the temporary
# sudoers drop-in. It takes NO arguments, so the grant's scope cannot be
# influenced at call time.
#
# Hardening note (review finding 1). An earlier version read a repository path
# from /etc/hermes-gate2/repo-path and ran `bash "$REPO/.../gate2-make-kickstart.sh"`
# as root. Root ownership of this wrapper did not protect that transitive
# dependency: anyone able to write the user's checkout could edit the generator
# and obtain root code execution through the granted wrapper. This version
# executes only root-owned files in this directory; the checkout is never
# consulted. Reinstall the grant after editing this file.
#
# It does not touch the domain: restarting the installer is the boot wrapper's
# job, so a rebuild is inert until it is deliberately used.
set -euo pipefail
export LC_ALL=C

LIBEXEC="${HERMES_GATE2_LIBEXEC:-/usr/local/libexec/hermes-gate2}"
GENERATOR="$LIBEXEC/gate2-make-kickstart.sh"
TEMPLATE="$LIBEXEC/gate2-kickstart.ks.in"
KS_DIR=/var/lib/libvirt/boot/lab-hermes-manual-r1

die() {
  printf 'STOP: %s\n' "$*" >&2
  exit 1
}

[ "$(id -u)" -eq 0 ] || die "must run as root"
[ "$#" -eq 0 ] || die "this wrapper takes no arguments (got $#)"

# The directory and every dependency must be root-owned regular files that no
# unprivileged account can replace, and must not be symlinks. This is the control
# that keeps a writable checkout from becoming root code execution.
[ -d "$LIBEXEC" ] || die "missing root-owned directory: $LIBEXEC"
[ ! -L "$LIBEXEC" ] || die "refusing symlinked libexec directory: $LIBEXEC"
[ "$(stat -c %U "$LIBEXEC")" = root ] || die "$LIBEXEC is not root-owned"
[ -z "$(find "$LIBEXEC" -maxdepth 0 -perm /022 -print -quit)" ] || die "$LIBEXEC is group/world-writable"

validate_root_file() {
  local path="$1" owner
  [ -f "$path" ] || die "missing dependency: $path"
  [ ! -L "$path" ] || die "refusing symlinked dependency: $path"
  owner=$(stat -c %U "$path")
  [ "$owner" = root ] || die "$path is owned by $owner, not root; reinstall the grant"
  [ -z "$(find "$path" -maxdepth 0 -perm /022 -print -quit)" ] || die "$path is group/world-writable"
  case "$path" in
    "$LIBEXEC"/*) ;;
    *) die "dependency escapes $LIBEXEC: $path" ;;
  esac
}
validate_root_file "$GENERATOR"
validate_root_file "$TEMPLATE"

# The invoking user supplies only the (public) lab key. Everything executable is
# root-owned, and the scrubbed environment stops a caller variable from
# redirecting the output directory, the template, the key file or the locale.
invoking_user="${SUDO_USER:-root}"
invoking_home=$(getent passwd "$invoking_user" | cut -d: -f6)
[ -n "$invoking_home" ] || die "cannot resolve the home directory of $invoking_user"
key_file="$invoking_home/.local/state/hermes-manual-lab/id_ed25519.pub"
[ -r "$key_file" ] || die "no readable lab public key at $key_file (build the media once without --reuse-hash first)"

printf 'rebuilding the kickstart media from the root-owned generator %s\n' "$GENERATOR"
exec env -i \
  PATH=/usr/sbin:/usr/bin:/sbin:/bin \
  HOME=/root LC_ALL=C \
  GATE2_KS_DIR="$KS_DIR" \
  GATE2_SSH_PUBLIC_KEY_FILE="$key_file" \
  /usr/bin/bash "$GENERATOR" --reuse-hash
