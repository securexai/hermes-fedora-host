#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC1091,SC2001,SC2015
# Read-only remote preflight. It intentionally never creates deployment state.

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s nullglob

readonly EXPECTED_IMAGE='docker.io/nousresearch/hermes-agent@sha256:e0df6adebddf29b91112aefc999d4aaf6846c9eb544faca5672a16a13590ff79'
FAILURES=0
MANAGEMENT_CIDR=''
MANAGEMENT_INTERFACE=''
ALLOW_UPDATE=0
HOST_MODULE='/usr/local/libexec/hermes-fedora-server-host'

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  FAILURES=$((FAILURES + 1))
}

pass() { printf 'PASS: %s\n' "$1"; }

version_at_least() {
  local actual=$1
  local required=$2
  local first
  first=$(printf '%s\n%s\n' "$required" "$actual" | sort -V | head -n 1)
  [[ "$first" == "$required" ]]
}

valid_ipv4_cidr() {
  local address prefix octet a b c d extra=''
  IFS=/ read -r address prefix <<<"$1"
  [[ "$address" =~ ^[0-9]+(\.[0-9]+){3}$ && "$prefix" =~ ^[0-9]+$ ]] || return 1
  IFS=. read -r a b c d extra <<<"$address"
  [[ -n "$a" && -n "$b" && -n "$c" && -n "$d" && -z "$extra" && "$prefix" -le 32 ]] \
    || return 1
  for octet in "$a" "$b" "$c" "$d"; do
    [[ "$octet" -le 255 ]] || return 1
  done
}

root_check() {
  if [[ "$EUID" -eq 0 ]]; then
    "$@" >/dev/null 2>&1
  else
    sudo -n "$@" >/dev/null 2>&1
  fi
}

root_run() {
  if [[ "$EUID" -eq 0 ]]; then
    "$@"
  else
    sudo -n "$@"
  fi
}

check_root_access() {
  if root_check true; then
    pass 'non-interactive administrative inspection available'
    return 0
  fi
  fail 'non-interactive administrative inspection available (run check from an approved sudo session)'
  return 1
}

check_foundation() {
  local architecture version secure_boot listeners unexpected memory_kib var_free_kib
  local memory_limit_kib memory_label var_free_limit_kib var_free_label
  architecture=$(uname -m)
  [[ "$architecture" == x86_64 ]] && pass 'x86_64 architecture' || fail 'x86_64 architecture'
  fedora_server_is_supported && pass 'Fedora Server 44 host' || fail 'Fedora Server 44 host'
  stat -fc '%T' /sys/fs/cgroup 2>/dev/null | grep -qx cgroup2fs && pass 'cgroup v2' || fail 'cgroup v2'
  version=$(fedora_server_podman_version)
  if fedora_server_version_at_least "$version" "$HERMES_SERVER_MIN_PODMAN"; then
    pass "Podman $version"
  elif [[ "$ALLOW_UPDATE" == 1 ]]; then
    pass "Podman ${version:-unavailable} (Fedora Server update required before Hermes runtime)"
  else
    fail "Podman $HERMES_SERVER_MIN_PODMAN or newer"
  fi
  for requirement in curl openssl python3 dnf5 mokutil firewall-cmd; do
    if command -v "$requirement" >/dev/null 2>&1; then
      pass "$requirement available"
    elif [[ "$ALLOW_UPDATE" == 1 ]]; then
      pass "$requirement will be installed by the Fedora Server package contract"
    else
      fail "$requirement available"
    fi
  done
  if root_check systemctl list-unit-files dnf5-automatic.timer >/dev/null 2>&1; then
    pass 'dnf5-automatic timer available'
  elif [[ "$ALLOW_UPDATE" == 1 ]]; then
    pass 'dnf5-automatic timer will be installed by the Fedora Server package contract'
  else
    fail 'dnf5-automatic timer available'
  fi
  [[ -x /usr/lib/systemd/system-generators/podman-system-generator ]] \
    && pass 'Podman Quadlet generator present' || fail 'Podman Quadlet generator present'
  [[ -e /sys/firmware/efi ]] && pass 'UEFI firmware interface present' || fail 'UEFI firmware interface present'
  secure_boot=$(mokutil --sb-state 2>/dev/null || true)
  grep -qi 'secureboot enabled' <<<"$secure_boot" && pass 'Secure Boot enabled' \
    || fail 'Secure Boot enabled'
  root_check getenforce && [[ "$(root_run getenforce)" == Enforcing ]] \
    && pass 'SELinux enforcing' || fail 'SELinux enforcing'
  root_check systemctl is-active --quiet firewalld && pass 'firewalld active' || fail 'firewalld active'
  root_check lsblk -o FSTYPE && root_run lsblk -o FSTYPE | grep -q crypto_LUKS \
    && pass 'LUKS-backed storage' || fail 'LUKS-backed storage'
  memory_kib=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
  if systemd-detect-virt --vm --quiet 2>/dev/null; then
    # An 8 GiB libvirt allocation exposes slightly less MemTotal after the
    # guest firmware and PCI address space reserve their memory. Keep the
    # physical-host requirement at 8 GiB while allowing that deterministic
    # reservation in the exact 8192 MiB certification VM.
    memory_limit_kib=$((HERMES_SERVER_MIN_MEMORY_KIB - 524288))
    memory_label='at least 7.5 GiB usable memory for an 8 GiB VM allocation'
  else
    memory_limit_kib=$HERMES_SERVER_MIN_MEMORY_KIB
    memory_label='at least 8 GiB memory'
  fi
  [[ "$memory_kib" =~ ^[0-9]+$ && "$memory_kib" -ge "$memory_limit_kib" ]] \
    && pass "$memory_label" || fail "$memory_label"
  var_free_limit_kib=$HERMES_SERVER_MIN_VAR_FREE_KIB
  var_free_label='at least 20 GiB free under /var'
  if image_is_available; then
    var_free_limit_kib=$HERMES_SERVER_MIN_POST_IMAGE_VAR_FREE_KIB
    var_free_label='at least 8 GiB free under /var after the locked image pull'
  elif [[ "$ALLOW_UPDATE" == 1 ]] && root_check test -r /var/lib/hermes-deploy/boot-id-after-update; then
    # The immutable OS deployment consumes space before the locked container
    # image is pulled. Keep the fresh-host contract at 20 GiB, but use the
    # measured post-update floor when resuming the same certified deployment.
    var_free_limit_kib=$HERMES_SERVER_MIN_POST_UPDATE_VAR_FREE_KIB
    var_free_label='at least 16 GiB free under /var after the staged update'
  fi
  var_free_kib=$(df -Pk /var | awk 'NR == 2 {print $4}')
  [[ "$var_free_kib" =~ ^[0-9]+$ && "$var_free_kib" -ge "$var_free_limit_kib" ]] \
    && pass "$var_free_label" || fail "$var_free_label"
  listeners=$(root_run ss -H -lntup 2>/dev/null || true)
  unexpected=$(awk '
    function loopback(address) {
      return address ~ /^127\.[0-9.]+([:%]|$)/ ||
        address ~ /^\[::1\]([:%]|$)/ ||
        address ~ /^::1([:%]|$)/
    }
    # ss -H -lntup fields are: netid state recv-q send-q local peer.
    !loopback($5) && $5 !~ /:22$/ {print $5}
  ' <<<"$listeners")
  [[ -z "$unexpected" ]] && pass 'no unexpected non-loopback host listeners' \
    || fail 'no unexpected non-loopback host listeners'
}

check_network() {
  local addresses interface source_address
  interface=$(ip -o -4 route show default 2>/dev/null | awk '{print $5; exit}')
  [[ "$interface" == "$MANAGEMENT_INTERFACE" ]] && pass 'management interface matches' \
    || fail 'management interface matches'
  addresses=$(ip -o -4 addr show dev "$MANAGEMENT_INTERFACE" 2>/dev/null | awk '{print $4}')
  [[ -n "$addresses" ]] && pass 'management interface has IPv4 address' \
    || fail 'management interface has IPv4 address'
  valid_ipv4_cidr "$MANAGEMENT_CIDR" \
    && pass 'management CIDR is syntactically valid' || fail 'management CIDR is syntactically valid'
  source_address=$(ip -o -4 route get 1.1.1.1 2>/dev/null | awk '
    {for (i = 1; i <= NF; i++) if ($i == "src") {print $(i + 1); exit}}
  ')
  if [[ -n "$source_address" ]] && grep -Fxq "$source_address" <(sed 's#/.*##' <<<"$addresses"); then
    pass 'management route uses the interface address'
  else
    fail 'management route uses the interface address'
  fi
}

check_console_recovery() {
  if [[ -e /dev/tty0 || -e /dev/hvc0 || -e /dev/ttyS0 || -e /dev/ttyAMA0 ]]; then
    pass 'local console recovery device present'
  else
    fail 'local console recovery device present'
  fi
}

image_is_available() {
  if id hermes >/dev/null 2>&1; then
    if [[ "$EUID" -eq 0 ]]; then
      (cd /tmp && runuser -u hermes -- env HOME=/home/hermes XDG_RUNTIME_DIR="/run/user/$(id -u hermes)" \
        podman image inspect "$EXPECTED_IMAGE" >/dev/null 2>&1)
    else
      (cd /tmp && sudo -n -u hermes env HOME=/home/hermes XDG_RUNTIME_DIR="/run/user/$(id -u hermes)" \
        podman image inspect "$EXPECTED_IMAGE" >/dev/null 2>&1)
    fi
  else
    podman image inspect "$EXPECTED_IMAGE" >/dev/null 2>&1
  fi
}

installer_created_identity() {
  root_check test -r /var/lib/hermes-deploy/fresh-identity || return 1
  [[ "$(root_run sed -n '1p' /var/lib/hermes-deploy/fresh-identity 2>/dev/null || true)" == 1 ]]
}

manual_container_count() {
  local container containers mounts count=0
  containers=$(podman ps -a -q 2>/dev/null || true)
  while IFS= read -r container; do
    [[ -n "$container" ]] || continue
    mounts=$(podman inspect "$container" --format '{{range .Mounts}}{{.Source}}{{println}}{{end}}' 2>/dev/null || true)
    grep -Fxq /home/hermes/data <<<"$mounts" && count=$((count + 1))
  done <<<"$containers"
  printf '%s\n' "$count"
}

check_identity_state() {
  local hermes_state manual_count
  if id hermes >/dev/null 2>&1; then
    if installer_created_identity; then
      hermes_state='managed-fresh'
      pass 'resumable installer-created Hermes identity discovered'
    else
      hermes_state='managed'
      pass 'Hermes identity discovered'
    fi
  else
    manual_count=$(manual_container_count)
    if [[ "$manual_count" =~ ^[1-9][0-9]*$ ]]; then
      hermes_state='manual-container'
      pass "manual Hermes container state discovered (count=$manual_count)"
    else
      hermes_state='fresh'
      pass 'fresh Hermes identity state'
    fi
  fi
  if image_is_available; then
    pass 'local Hermes image matches the locked digest'
  elif [[ "$hermes_state" == fresh || "$hermes_state" == manual-container ||
    "$hermes_state" == managed-fresh ]]; then
    pass "locked image not pulled ($hermes_state migration state)"
  else
    fail 'existing Hermes state has the locked image available'
  fi
  printf 'STATE: hermes_identity=%s image=%s\n' "$hermes_state" "$EXPECTED_IMAGE"
}

[[ $# -ge 2 && $# -le 4 ]] || {
  printf 'ERROR: usage: remote-preflight.sh MANAGEMENT_CIDR MANAGEMENT_INTERFACE [ALLOW_UPDATE] [HOST_MODULE]\n' >&2
  exit 64
}
MANAGEMENT_CIDR=$1
MANAGEMENT_INTERFACE=$2
if [[ $# -ge 3 ]]; then
  ALLOW_UPDATE=$3
fi
if [[ $# -eq 4 ]]; then
  HOST_MODULE=$4
fi
[[ "$MANAGEMENT_INTERFACE" =~ ^[[:alnum:]_.:-]+$ ]] || {
  printf 'ERROR: invalid management interface\n' >&2
  exit 64
}
[[ "$ALLOW_UPDATE" == 0 || "$ALLOW_UPDATE" == 1 ]] || {
  printf 'ERROR: invalid preflight update mode\n' >&2
  exit 64
}
[[ -r "$HOST_MODULE" ]] || {
  printf 'ERROR: Fedora Server host module is missing\n' >&2
  exit 66
}
# shellcheck source=/usr/local/libexec/hermes-fedora-server-host
source "$HOST_MODULE"

check_root_access || true
check_foundation
check_network
check_console_recovery
check_identity_state

if ((FAILURES == 0)); then
  printf 'PREFLIGHT_OK\n'
else
  printf 'PREFLIGHT_FAILED count=%d\n' "$FAILURES" >&2
  exit 1
fi
