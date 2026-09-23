#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC1091,SC2015
# Root-only host acceptance. The container/application checks live in
# acceptance.sh so the same gate is used by deployment and VM verification.

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s nullglob

readonly STATE_DIR='/var/lib/hermes-deploy'
FAILURES=0

if [[ -r /usr/local/libexec/hermes-fedora-server-host ]]; then
  # shellcheck source=/usr/local/libexec/hermes-fedora-server-host
  source /usr/local/libexec/hermes-fedora-server-host
fi

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  FAILURES=$((FAILURES + 1))
}

pass() { printf 'PASS: %s\n' "$1"; }

get_site_value() {
  local key=$1
  sed -n "s/^$key=//p" "$STATE_DIR/site.conf" | tail -n 1
}

check_sshd() {
  local effective admin
  effective=$(sshd -T 2>/dev/null || true)
  admin=$(get_site_value admin_user)
  for setting in \
    'pubkeyauthentication yes' \
    'passwordauthentication no' \
    'kbdinteractiveauthentication no' \
    'permitrootlogin no' \
    "allowusers $admin" \
    'allowtcpforwarding no' \
    'x11forwarding no' \
    'permittunnel no' \
    'gatewayports no'; do
    grep -Fxq "$setting" <<<"$effective" || fail "sshd $setting"
  done
  ((FAILURES == 0)) && pass 'effective sshd policy' || true
}

check_firewall() {
  local iface cidr zone rule
  iface=$(get_site_value management_interface)
  cidr=$(get_site_value management_cidr)
  zone=$(firewall-cmd --get-zone-of-interface="$iface" 2>/dev/null || true)
  [[ -n "$zone" ]] || zone=$(firewall-cmd --get-default-zone)
  rule="rule family=\"ipv4\" source address=\"$cidr\" service name=\"ssh\" accept"
  firewall-cmd --zone="$zone" --query-rich-rule="$rule" >/dev/null \
    && pass 'management-CIDR SSH firewall rule' || fail 'management-CIDR SSH firewall rule'
  for service in ssh mdns kdeconnect; do
    if firewall-cmd --zone="$zone" --query-service="$service" >/dev/null 2>&1; then
      fail "unrestricted firewalld service $service"
    fi
  done
}

check_services() {
  local unit state
  for unit in \
    avahi-daemon.service avahi-daemon.socket \
    cups.service cups.socket cups.path passim.service \
    cockpit.service cockpit.socket cockpit-motd.service \
    sleep.target suspend.target hibernate.target hybrid-sleep.target; do
    state=$(systemctl is-enabled "$unit" 2>/dev/null || true)
    [[ "$state" == masked || "$state" == disabled || "$state" == static || -z "$state" ]] \
      || fail "disabled or masked $unit"
    [[ "$(systemctl is-active "$unit" 2>/dev/null || true)" != active ]] \
      || fail "inactive $unit"
  done
  systemctl is-enabled dnf5-automatic.timer 2>/dev/null | grep -qx enabled \
    && pass 'download-only dnf5-automatic timer enabled' || fail 'download-only dnf5-automatic timer enabled'
  systemctl is-active dnf5-automatic.timer 2>/dev/null | grep -qx active \
    && pass 'download-only dnf5-automatic timer active' || fail 'download-only dnf5-automatic timer active'
  [[ -r /etc/dnf/automatic.conf ]] \
    && grep -Eiq '^apply_updates[[:space:]]*=[[:space:]]*False' /etc/dnf/automatic.conf \
    && grep -Eiq '^reboot[[:space:]]*=[[:space:]]*never' /etc/dnf/automatic.conf \
    && pass 'automatic updates are download-only' || fail 'automatic updates are download-only'
  pgrep -x kdeconnectd >/dev/null 2>&1 \
    && fail 'kdeconnectd inactive' || pass 'kdeconnectd inactive'
}

check_resolver() {
  local resolved_file=/etc/systemd/resolved.conf.d/60-hermes-hardening.conf
  [[ -r "$resolved_file" ]] \
    && grep -Fxq 'LLMNR=no' "$resolved_file" \
    && grep -Fxq 'MulticastDNS=no' "$resolved_file" \
    && pass 'LLMNR and multicast DNS disabled' \
    || fail 'LLMNR and multicast DNS disabled'
  systemctl is-active --quiet systemd-resolved \
    && pass 'systemd-resolved active' || fail 'systemd-resolved active'
}

check_listeners() {
  local listeners unexpected
  listeners=$(ss -H -lntup 2>/dev/null || true)
  unexpected=$(awk '
    function loopback(address) {
      return address ~ /^127\.[0-9.]+([:%]|$)/ ||
        address ~ /^\[::1\]([:%]|$)/ ||
        address ~ /^::1([:%]|$)/
    }
    !loopback($5) && $5 !~ /:22$/ {print $5}
  ' <<<"$listeners")
  [[ -z "$unexpected" ]] && pass 'no unexpected non-loopback host listeners' \
    || fail 'no unexpected non-loopback host listeners'
}

[[ -r "$STATE_DIR/site.conf" ]] && pass 'site configuration readable' || fail 'site configuration readable'
check_sshd
check_firewall
check_services
check_resolver
check_listeners

if ((FAILURES == 0)); then
  printf 'ROOT_ACCEPTANCE_OK\n'
else
  printf 'ROOT_ACCEPTANCE_FAILED count=%d\n' "$FAILURES" >&2
  exit 1
fi
