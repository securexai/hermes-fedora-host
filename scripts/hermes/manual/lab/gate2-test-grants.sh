#!/usr/bin/env bash
# Temporary, separate hypervisor/guest grants for the credential-free Gate 2 VM.
# Run --host-* on the hypervisor and --guest-* inside lab-hermes-manual-r1.
# The installed wrappers and guest bundle are copied to root-owned paths; sudo
# never runs a file from this writable checkout. Passwords are never inputs here.
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin LC_ALL=C

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
MANUAL=$(cd "$HERE/.." && pwd)
HOST_BASE=/var/usrlocal/libexec/hermes-gate2-test
GUEST_BASE=/usr/local/libexec/hermes-gate2-test
HOST_RULE=/etc/sudoers.d/90-hermes-gate2-test-host
GUEST_RULE=/etc/sudoers.d/90-hermes-gate2-test-guest
GUEST_PIN_DIR=/etc/hermes-gate2-test
LEGACY_HOST_RULE=/etc/sudoers.d/90-hermes-gate2-lab
LEGACY_GUEST_RULE=/etc/sudoers.d/90-hermes-manual-lab
die() { printf 'STOP: %s\n' "$*" >&2; exit 1; }

host_rule() {
  cat <<EOF
# Temporary Gate 2 host access. All three operations bind UUID, network and MAC.
aicloudopspecial ALL=(root) NOPASSWD: $HOST_BASE/gate2-test-host.sh status, $HOST_BASE/gate2-test-host.sh start, $HOST_BASE/gate2-test-host.sh shutdown
EOF
}
guest_rule() {
  cat <<EOF
# Temporary credential-free Gate 2 guest access; no arbitrary helper path or arguments.
aicowork ALL=(root) NOPASSWD: $GUEST_BASE/gate2-test-guest.sh worker-key, $GUEST_BASE/gate2-test-guest.sh m02, $GUEST_BASE/gate2-test-guest.sh m03-activate, $GUEST_BASE/gate2-test-guest.sh m03-configure, $GUEST_BASE/gate2-test-guest.sh m03-contract, $GUEST_BASE/gate2-test-guest.sh m04-posture, $GUEST_BASE/gate2-test-guest.sh m04-backup
EOF
}
validate_source() {
  [[ -f $HERE/gate2-test-host.sh && -f $HERE/gate2-test-guest.sh ]] || die 'wrapper sources missing'
  [[ -z $(find "$MANUAL" -type l -print -quit) ]] || die 'source bundle contains symlinks'
  [[ -z $(find "$MANUAL" ! -type f ! -type d -print -quit) ]] || die 'source bundle contains special files'
  bash -n "$HERE/gate2-test-host.sh"
  bash -n "$HERE/gate2-test-guest.sh"
  local tmp
  tmp=$(mktemp)
  trap 'rm -f "$tmp"' RETURN
  host_rule >"$tmp"
  visudo -cf "$tmp" >/dev/null || die 'host sudoers syntax invalid'
  guest_rule >"$tmp"
  visudo -cf "$tmp" >/dev/null || die 'guest sudoers syntax invalid'
  rm -f "$tmp"
  trap - RETURN
}
secure_base() {
  local base=$1 parent
  local -a parents
  if [[ $base == "$HOST_BASE" ]]; then
    parents=(/var /var/usrlocal /var/usrlocal/libexec)
  elif [[ $base == "$GUEST_BASE" ]]; then
    parents=(/usr /usr/local /usr/local/libexec)
  else
    die 'unknown libexec base'
  fi
  for parent in "${parents[@]}"; do
    [[ -d $parent && ! -L $parent && $(stat -c %U "$parent") == root ]] || die "untrusted parent $parent"
    [[ -z $(find "$parent" -maxdepth 0 -perm /022 -print -quit) ]] || die "writable parent $parent"
  done
  [[ ! -L $base ]] || die 'libexec path is a symlink'
  install -d -o root -g root -m 0755 "$base"
  [[ $(stat -c %U "$base") == root ]] || die 'libexec path is not root-owned'
  [[ -z $(find "$base" -maxdepth 0 -perm /022 -print -quit) ]] || die 'libexec path is writable'
}
trusted_file() {
  local file=$1
  [[ -f $file && ! -L $file && $(stat -c %U "$file") == root ]] || die "untrusted file $file"
  [[ -z $(find "$file" -maxdepth 0 -perm /022 -print -quit) ]] || die "writable file $file"
}
install_rule() {
  local kind=$1 dest=$2 tmp
  [[ ! -L $dest ]] || die 'sudoers path is a symlink'
  tmp=$(mktemp /etc/sudoers.d/.hermes-gate2-test.XXXXXX)
  if [[ $kind == host ]]; then host_rule >"$tmp"; else guest_rule >"$tmp"; fi
  chown root:root "$tmp"
  chmod 0440 "$tmp"
  if ! visudo -cf "$tmp" >/dev/null; then rm -f "$tmp"; die 'sudoers validation failed'; fi
  if [[ -e $dest ]] && cmp -s "$tmp" "$dest"; then
    rm -f "$tmp"
  else
    mv -f "$tmp" "$dest"
  fi
  visudo -cf "$dest" >/dev/null || die 'installed sudoers validation failed'
}
check_host_fixture() {
  [[ $(/usr/bin/virsh -c qemu:///system domuuid lab-hermes-manual-r1) == d39e5ca7-aded-457c-b01d-a1817a4725a8 ]] || die 'wrong host fixture'
  /usr/bin/virsh -c qemu:///system domiflist lab-hermes-manual-r1 | /usr/bin/awk \
    '$2 == "network" && $3 == "fvh-nat" && $5 == "52:54:00:94:58:36" {ok=1} END {exit !ok}' \
    || die 'wrong host fixture network or MAC'
}
check_guest_fixture() {
  [[ $(cat /etc/hostname) == lab-hermes-manual-r1 ]] || die 'wrong guest hostname'
  [[ $(sha256sum /etc/machine-id | awk '{print $1}') == 5026447dd72b4e67b089b93692dc6e10a0fe5c7996765f6cdbf6a1d2752d6588 ]] || die 'wrong guest machine-id'
}
install_host() {
  [[ $# == 0 ]] || die 'host install takes no arguments'
  validate_source
  check_host_fixture
  secure_base "$HOST_BASE"
  [[ ! -L ${HOST_BASE}/gate2-test-host.sh ]] || die 'host wrapper path is a symlink'
  if [[ -e ${HOST_BASE}/gate2-test-host.sh ]] && ! cmp -s "$HERE/gate2-test-host.sh" "${HOST_BASE}/gate2-test-host.sh"; then
    die 'installed host wrapper differs; remove grant before replacement'
  fi
  if [[ ! -e ${HOST_BASE}/gate2-test-host.sh ]]; then
    install -o root -g root -m 0755 "$HERE/gate2-test-host.sh" "${HOST_BASE}/gate2-test-host.sh"
  fi
  trusted_file "${HOST_BASE}/gate2-test-host.sh"
  install_rule host "$HOST_RULE"
  # The older boot/rebuild grant is unnecessary and was installed for a prior phase.
  rm -f "$LEGACY_HOST_RULE"
  /usr/bin/logger -t hermes-gate2-test -- 'host grant installed; legacy host rule removed'
}
install_guest() {
  [[ $# == 1 && $1 =~ ^[[:xdigit:]]{64}$ ]] || die 'guest install needs one reviewed machine-id SHA256'
  local want=$1 got tmp pin_tmp
  got=$(sha256sum /etc/machine-id | awk '{print $1}')
  [[ $want == "$got" ]] || die 'guest identity does not match reviewed hash'
  check_guest_fixture
  validate_source
  secure_base "$GUEST_BASE"
  [[ ! -L ${GUEST_BASE}/gate2-test-guest.sh && ! -L ${GUEST_BASE}/bundle ]] || die 'guest install path is a symlink'
  if [[ -e ${GUEST_BASE}/gate2-test-guest.sh ]] && ! cmp -s "$HERE/gate2-test-guest.sh" "${GUEST_BASE}/gate2-test-guest.sh"; then
    die 'installed guest wrapper differs; remove grant before replacement'
  fi
  if [[ ! -d ${GUEST_BASE}/bundle ]]; then
    tmp=$(mktemp -d "${GUEST_BASE}/.bundle.XXXXXX")
    cp -a "$MANUAL/." "$tmp/"
    # Python bytecode in the staging tree is local cache, not reviewed source.
    find "$tmp" -type d -name __pycache__ -prune -exec rm -rf -- {} +
    chown -R root:root "$tmp"
    chmod -R go-w "$tmp"
    [[ -z $(find "$tmp" -type l -print -quit) ]] || die 'copied bundle contains symlink'
    mv "$tmp" "${GUEST_BASE}/bundle"
  else
    [[ -z $(find "${GUEST_BASE}/bundle" -type l -print -quit) ]] || die 'installed bundle contains symlink'
    [[ -z $(find "${GUEST_BASE}/bundle" ! -user root -print -quit) ]] || die 'installed bundle is not root-owned'
    [[ -z $(find "${GUEST_BASE}/bundle" -perm /022 -print -quit) ]] || die 'installed bundle is writable'
    diff -qr --exclude=__pycache__ --exclude='*.pyc' "$MANUAL" "${GUEST_BASE}/bundle" >/dev/null \
      || die 'installed bundle differs; remove grant before replacement'
  fi
  if [[ ! -e ${GUEST_BASE}/gate2-test-guest.sh ]]; then
    install -o root -g root -m 0755 "$HERE/gate2-test-guest.sh" "${GUEST_BASE}/gate2-test-guest.sh"
  fi
  trusted_file "${GUEST_BASE}/gate2-test-guest.sh"
  [[ ! -L $GUEST_PIN_DIR ]] || die 'pin directory is a symlink'
  install -d -o root -g root -m 0755 "$GUEST_PIN_DIR"
  [[ ! -L $GUEST_PIN_DIR/machine-id.sha256 ]] || die 'pin path is a symlink'
  if [[ -e $GUEST_PIN_DIR/machine-id.sha256 ]]; then
    [[ $(cat "$GUEST_PIN_DIR/machine-id.sha256") == "$want" ]] || die 'existing identity pin differs'
  else
    pin_tmp=$(mktemp)
    printf '%s\n' "$want" >"$pin_tmp"
    install -o root -g root -m 0644 "$pin_tmp" "$GUEST_PIN_DIR/machine-id.sha256"
    rm -f "$pin_tmp"
  fi
  trusted_file "$GUEST_PIN_DIR/machine-id.sha256"
  install_rule guest "$GUEST_RULE"
  rm -f "$LEGACY_GUEST_RULE"
  /usr/bin/logger -t hermes-gate2-test -- 'guest grant installed; legacy broad rule removed'
}
remove_host() {
  [[ $# == 0 ]] || die 'host remove takes no arguments'
  check_host_fixture
  [[ $(/usr/bin/virsh -c qemu:///system domstate lab-hermes-manual-r1) == 'shut off' ]] || die 'fixture must be shut off before host removal'
  rm -f "$HOST_RULE" "$LEGACY_HOST_RULE" "${HOST_BASE}/gate2-test-host.sh"
  /usr/bin/logger -t hermes-gate2-test -- 'host grants removed after VM shutdown'
}
remove_guest() {
  [[ $# == 0 ]] || die 'guest remove takes no arguments'
  check_guest_fixture
  rm -f "$GUEST_RULE" "$LEGACY_GUEST_RULE" "${GUEST_BASE}/gate2-test-guest.sh" "$GUEST_PIN_DIR/machine-id.sha256"
  rmdir "$GUEST_PIN_DIR" 2>/dev/null || true
  if [[ -d ${GUEST_BASE}/bundle && ! -L ${GUEST_BASE}/bundle && $(stat -c %U "${GUEST_BASE}/bundle") == root ]]; then
    rm -rf -- "${GUEST_BASE}/bundle"
  fi
  /usr/bin/logger -t hermes-gate2-test -- 'guest grants removed before VM shutdown'
}

case "${1:-}" in
  --check) [[ $# == 1 ]] || die '--check takes no arguments'; validate_source; printf 'source and sudoers syntax valid\n' ;;
  --host-install|--host-remove|--guest-install|--guest-remove)
    action=$1; shift
    [[ $(id -u) == 0 ]] || die 'installation and removal require root'
    case "$action" in
      --host-install) install_host "$@" ;;
      --host-remove) remove_host "$@" ;;
      --guest-install) install_guest "$@" ;;
      --guest-remove) remove_guest "$@" ;;
    esac
    ;;
  *) die 'usage: gate2-test-grants.sh --check|--host-install|--host-remove|--guest-install HASH|--guest-remove' ;;
esac
