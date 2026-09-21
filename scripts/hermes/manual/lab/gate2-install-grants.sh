#!/usr/bin/env bash
# Install the temporary, scoped privilege grants used to drive Gate 2.
#
# Run once, as root, on the HOST:
#   sudo bash gate2-install-grants.sh --install
#   sudo bash gate2-install-grants.sh --status
#   sudo bash gate2-install-grants.sh --remove
#
# What is granted, and why it is scoped this way:
#   * HOST: three argument-free wrappers - boot the installer, rebuild the kickstart media,
#     and collect an observation bundle. No wildcards, no general virsh authority.
#   * The rebuild wrapper needs a generator and the kickstart template. Those are installed
#     here as ROOT-OWNED files in the same libexec directory, so the granted wrapper never
#     executes anything from the user-writable checkout (review finding 1). A wrapper that
#     ran `bash "$REPO/.../generator.sh"` as root let anyone who can write the checkout
#     obtain root through the grant; the checkout path is no longer recorded or read.
#   * GUEST: installed by the kickstart, not here. It is scoped to the staged helper
#     directory but is ROOT-EQUIVALENT IN PRACTICE, because the helpers run arbitrary
#     commands as root. That is deviation D-03 and is acceptable only because the guest
#     is disposable and holds no real credentials during Gate 2.
#
# Removal is one command and needs no reboot.
set -euo pipefail
export LC_ALL=C

ADMIN_USER="${HERMES_LAB_ADMIN_USER:-aicloudopspecial}"
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
WRAPPER_SRC="$HERE/gate2-boot-kickstart.sh"
REBUILD_SRC="$HERE/gate2-rebuild-kickstart-iso.sh"
OBSERVE_SRC="$HERE/gate2-observe.sh"
GENERATOR_SRC="$HERE/gate2-make-kickstart.sh"
TEMPLATE_SRC="$HERE/gate2-kickstart.ks.in"
LIBEXEC=/usr/local/libexec/hermes-gate2
SUDOERS_HOST=/etc/sudoers.d/90-hermes-gate2-lab

die() {
  printf 'STOP: %s\n' "$*" >&2
  exit 1
}

case "${1:-}" in
  --install | --status | --remove) MODE="$1" ;;
  *) die "usage: $0 {--install|--status|--remove}" ;;
esac

[ "$(id -u)" -eq 0 ] || die "must run as root"
id -u "$ADMIN_USER" >/dev/null 2>&1 || die "account $ADMIN_USER does not exist"

status() {
  printf 'boot wrapper:     %s\n' "$([ -x "$LIBEXEC/gate2-boot-kickstart.sh" ] && echo installed || echo absent)"
  printf 'rebuild wrapper:  %s\n' "$([ -x "$LIBEXEC/gate2-rebuild-kickstart-iso.sh" ] && echo installed || echo absent)"
  printf 'observe wrapper:  %s\n' "$([ -x "$LIBEXEC/gate2-observe.sh" ] && echo installed || echo absent)"
  printf 'root generator:   %s\n' "$([ -x "$LIBEXEC/gate2-make-kickstart.sh" ] && echo installed || echo absent)"
  printf 'root template:    %s\n' "$([ -r "$LIBEXEC/gate2-kickstart.ks.in" ] && echo installed || echo absent)"
  printf 'host sudoers:     %s\n' "$([ -f "$SUDOERS_HOST" ] && echo installed || echo absent)"
  if [ -f "$SUDOERS_HOST" ]; then
    printf 'grant:\n'
    grep -vE '^\s*#|^\s*$' "$SUDOERS_HOST" | sed 's/^/  /'
  fi
}

case "$MODE" in
  --status)
    status
    exit 0
    ;;
  --remove)
    rm -f "$SUDOERS_HOST"
    rm -f "$LIBEXEC/gate2-boot-kickstart.sh" "$LIBEXEC/gate2-rebuild-kickstart-iso.sh" \
      "$LIBEXEC/gate2-observe.sh" "$LIBEXEC/gate2-make-kickstart.sh" "$LIBEXEC/gate2-kickstart.ks.in"
    rmdir "$LIBEXEC" 2>/dev/null || true
    # Remove the obsolete checkout path file if a previous version installed it.
    rm -f /etc/hermes-gate2/repo-path
    rmdir /etc/hermes-gate2 2>/dev/null || true
    printf 'grants removed; no reboot required\n'
    status
    exit 0
    ;;
esac

install -d -m 0755 "$LIBEXEC"
install -o root -g root -m 0755 "$WRAPPER_SRC" "$LIBEXEC/gate2-boot-kickstart.sh"
install -o root -g root -m 0755 "$REBUILD_SRC" "$LIBEXEC/gate2-rebuild-kickstart-iso.sh"
install -o root -g root -m 0755 "$OBSERVE_SRC" "$LIBEXEC/gate2-observe.sh"
# The rebuild wrapper's transitive executable dependencies, installed root-owned
# here so the granted wrapper never reads code from the writable checkout.
install -o root -g root -m 0755 "$GENERATOR_SRC" "$LIBEXEC/gate2-make-kickstart.sh"
install -o root -g root -m 0644 "$TEMPLATE_SRC" "$LIBEXEC/gate2-kickstart.ks.in"
cat >"$SUDOERS_HOST" <<CONF
# Temporary Gate 2 lab grant. Three argument-free wrappers; see
# docs/plans/2026-09-20-hermes-manual-gate2-lab-plan.md. Remove with --remove.
Cmnd_Alias HERMES_GATE2_BOOT = $LIBEXEC/gate2-boot-kickstart.sh
Cmnd_Alias HERMES_GATE2_REBUILD = $LIBEXEC/gate2-rebuild-kickstart-iso.sh
Cmnd_Alias HERMES_GATE2_OBSERVE = $LIBEXEC/gate2-observe.sh
$ADMIN_USER ALL=(root) NOPASSWD: HERMES_GATE2_BOOT, HERMES_GATE2_REBUILD, HERMES_GATE2_OBSERVE
CONF
chmod 0440 "$SUDOERS_HOST"
chown root:root "$SUDOERS_HOST"

# A malformed sudoers file can break sudo entirely, so validate and roll back on failure.
if ! visudo -cf "$SUDOERS_HOST" >/dev/null 2>&1; then
  rm -f "$SUDOERS_HOST"
  die "the generated sudoers file failed validation and was removed"
fi

# Every executable the grant can reach must be root-owned and not group/world
# writable, including the transitive generator. A writable dependency would make
# the scope of the grant meaningless.
for w in "$LIBEXEC/gate2-boot-kickstart.sh" "$LIBEXEC/gate2-rebuild-kickstart-iso.sh" \
  "$LIBEXEC/gate2-observe.sh" "$LIBEXEC/gate2-make-kickstart.sh"; do
  [ "$(stat -c %U "$w")" = root ] || die "$w is not root-owned; refusing"
  [ ! -L "$w" ] || die "$w is a symlink; refusing"
done
for w in "$LIBEXEC/gate2-boot-kickstart.sh" "$LIBEXEC/gate2-rebuild-kickstart-iso.sh" \
  "$LIBEXEC/gate2-observe.sh" "$LIBEXEC/gate2-make-kickstart.sh" "$LIBEXEC/gate2-kickstart.ks.in"; do
  [ -z "$(find "$w" -maxdepth 0 -perm /022 -print -quit)" ] || die "$w is group/world-writable; refusing"
done
[ -z "$(find "$LIBEXEC" -perm /022 -print -quit)" ] || die "wrapper directory is group/world-writable"

printf 'installed\n'
status
printf '\nverify the grant as the target account:\n  sudo -n -l -U %s | tail -n 5\n' "$ADMIN_USER"
