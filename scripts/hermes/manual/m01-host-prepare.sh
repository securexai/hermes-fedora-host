#!/usr/bin/env bash
# M01 step 2: prepare the host for the manual profile (guide Phase 5.1-5.8).
#
# Default is inspect-only; re-run with --apply to make changes.
# This helper never reboots. Reboots are explicit, separately observed steps.
#
#   sudo bash ~/hermes-manual/m01-host-prepare.sh --apply
set -u
set -o pipefail
export LC_ALL=C

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib-manual-common.sh
. "$HERE/lib-manual-common.sh" || {
  printf 'STOP: cannot load %s/lib-manual-common.sh (stage the whole manual/ tree)\n' "$HERE" >&2
  exit 1
}

mp_parse_mode "$@"
mapfile -t MP_ARGS < <(mp_positionals "$@")
BUNDLE="${MP_ARGS[0]:-$HERE}"
ADMIN_ACCOUNT=$(mp_admin_account)
ADMIN_HOME=$(mp_admin_home)
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m01-host-prepare.out")
RUNTIME_ACCOUNT="${HERMES_RUNTIME:-hermes}"
RUNTIME_HOME=/home/hermes
HOSTNAME_TARGET="${HERMES_HOSTNAME:-lab-hermes-manual-r1}"

# Guide 5.1. tpm2-tools is non-optional per the guide (the boot gates read PCR 7);
# cryptsetup stays even though this fixture is unencrypted (D-01), so the package
# set matches the documented procedure.
PACKAGES="podman container-selinux passt shadow-utils shadow-utils-subid \
openssh-server openssh-clients firewalld policycoreutils policycoreutils-python-utils \
audit chrony cryptsetup lvm2 xfsprogs tpm2-tools git jq skopeo tar rsync \
dnf5-plugin-automatic dnf5-plugins mokutil smartmontools sysstat"

mp_require_apply 'would install packages, harden SSH, bound the journal, set the update policy, create the runtime account and enable rootless containers'
mp_require_host_identity
mp_lock_profile
mp_install_trap
mp_require_tools dnf systemctl

h() {
  if ! mountpoint -q "$RUNTIME_HOME"; then
    printf 'STOP: %s is not mounted.\n' "$RUNTIME_HOME" >&2
    return 1
  fi
  sudo -u "$RUNTIME_ACCOUNT" -- env -i --chdir="$RUNTIME_HOME" \
    HOME="$RUNTIME_HOME" USER="$RUNTIME_ACCOUNT" LOGNAME="$RUNTIME_ACCOUNT" \
    PATH=/usr/local/bin:/usr/bin:/bin TERM="${TERM:-xterm}" \
    XDG_RUNTIME_DIR="/run/user/$RUNTIME_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$RUNTIME_UID/bus" \
    TMPDIR="$RUNTIME_HOME/.cache/podman-tmp" "$@"
}

RUNTIME_UID=$(id -u "$RUNTIME_ACCOUNT" 2>/dev/null || true)

# 5.2 resolves the lab public key HERE, in the shell that owns the EXIT/INT/TERM
# traps installed above. Allocating this directory inside the `{ ... } | tee`
# reporting pipeline ran it in a subshell and silently lost the cleanup
# registration, so an ordinary exit, a failure or an interruption left the
# private directory behind. `keydir=$(mp_secure_tmpdir)` would lose it the same
# way; mp_secure_tmpdir_var registers in the calling shell.
keyfile="${HERMES_LAB_PUBLIC_KEY_FILE:-}"
if [ -z "$keyfile" ]; then
  mp_secure_tmpdir_var keydir
  keyfile="$keydir/lab-public-key.pub"
  grep -m1 '^ssh-ed25519 ' "$ADMIN_HOME/.ssh/authorized_keys" 2>/dev/null >"$keyfile" || true
  [ -s "$keyfile" ] || keyfile=""
fi

rc=0
{
  echo "### M01 step 2: host preparation (guide Phase 5)"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  # ---------------------------------------------------------------- 5.1 tools
  echo "===== 5.1 controlled update and host tools ====="
  dnf --refresh -y upgrade
  upgrade_rc=$?
  echo "dnf_upgrade_rc=$upgrade_rc"
  mp_check dnf_upgrade "$([ "$upgrade_rc" -eq 0 ] && echo PASS || echo FAIL)"
  dnf -y install $PACKAGES
  install_rc=$?
  echo "dnf_install_rc=$install_rc"
  missing=""
  for pkg in $PACKAGES; do
    rpm -q "$pkg" >/dev/null 2>&1 || missing="$missing $pkg"
  done
  if [ -z "$missing" ]; then
    mp_check packages_installed PASS
  else
    mp_check packages_installed FAIL "not installed:$missing"
  fi
  systemctl enable --now chronyd >/dev/null 2>&1 || true
  mp_check chronyd_active "$(systemctl is-active chronyd >/dev/null 2>&1 && echo PASS || echo FAIL)"
  echo

  # ------------------------------------------------------------------ 5.2 SSH
  echo "===== 5.2 key-only SSH ====="
  iface=$(ip -o -4 route show default 2>/dev/null | awk '{print $5}' | head -n1)
  # firewalld annotates the default zone in this output ("FedoraServer (default)"),
  # and passing that whole string as a zone name makes the SSH helper reject it.
  # Resolve the interface's own zone and strip any annotation.
  zone=$(firewall-cmd --get-zone-of-interface="${iface:-link}" 2>/dev/null | head -n1)
  [ -n "$zone" ] || zone=$(firewall-cmd --get-default-zone 2>/dev/null | head -n1)
  zone=${zone%% *}
  echo "interface=${iface:-none} zone=${zone:-none}"
  echo "lab_public_key=${keyfile:-<none>}"
  if [ -n "$iface" ] && [ -n "$zone" ] && [ -n "$keyfile" ]; then
    bash "$BUNDLE/setup-ssh-key-only.sh" --user "$ADMIN_ACCOUNT" \
      --public-key-file "$keyfile" --interface "$iface" --zone "$zone"
    ssh_helper_rc=$?
    echo "ssh_helper_rc=$ssh_helper_rc"
    mp_check ssh_helper_rc "$([ "$ssh_helper_rc" -eq 0 ] && echo PASS || echo FAIL)"
  else
    mp_check ssh_helper_rc FAIL "missing interface, zone or public key (set HERMES_LAB_PUBLIC_KEY_FILE)"
  fi
  if sshd -t 2>/dev/null; then
    mp_check sshd_config_valid PASS
  else
    mp_check sshd_config_valid FAIL "$(sshd -t 2>&1 | head -n1)"
  fi
  eff=$(sshd -T 2>/dev/null | grep -E '^(pubkeyauthentication|passwordauthentication|kbdinteractiveauthentication|permitrootlogin) ' || true)
  printf '%s\n' "$eff"
  if [[ "$eff" == *"pubkeyauthentication yes"* && "$eff" == *"passwordauthentication no"* &&
    "$eff" == *"kbdinteractiveauthentication no"* ]]; then
    mp_check ssh_key_only PASS
  else
    mp_check ssh_key_only FAIL "effective sshd policy is not key-only"
  fi
  echo

  # ------------------------------------------------- 5.3 firewall and cockpit
  echo "===== 5.3 firewall and Cockpit ====="
  if systemctl list-unit-files cockpit.socket >/dev/null 2>&1; then
    systemctl disable --now cockpit.socket >/dev/null 2>&1 || true
  fi
  mp_check cockpit_socket_disabled "$(systemctl is-enabled cockpit.socket >/dev/null 2>&1 && echo FAIL || echo PASS)"
  if [ -n "$zone" ] && firewall-cmd --zone="$zone" --list-services 2>/dev/null | grep -qw cockpit; then
    firewall-cmd --permanent --zone="$zone" --remove-service=cockpit >/dev/null
    firewall-cmd --reload >/dev/null
  fi
  if [ -n "$zone" ]; then
    services=$(firewall-cmd --zone="$zone" --list-services 2>/dev/null || true)
    echo "zone_services=${services:-none}"
    if [[ " $services " == *" ssh "* && " $services " != *" cockpit "* ]]; then
      mp_check firewall_policy PASS
    else
      mp_check firewall_policy FAIL "ssh missing or cockpit still enabled in $zone"
    fi
  else
    mp_check firewall_policy FAIL "no active firewalld zone"
  fi
  echo

  # ----------------------------------------- 5.4 journal and update policy
  echo "===== 5.4 bounded journal and download-only updates ====="
  install -d -m 0755 /etc/systemd/journald.conf.d
  cat >/etc/systemd/journald.conf.d/60-hermes-host.conf <<'CONF'
[Journal]
Storage=persistent
SystemMaxUse=1G
SystemKeepFree=2G
MaxRetentionSec=14day
CONF
  chmod 0644 /etc/systemd/journald.conf.d/60-hermes-host.conf
  systemctl restart systemd-journald
  mp_check journal_bounded "$(grep -q '^SystemMaxUse=1G' /etc/systemd/journald.conf.d/60-hermes-host.conf && echo PASS || echo FAIL)"
  install -d -m 0755 /etc/dnf
  cat >/etc/dnf/automatic.conf <<'CONF'
[commands]
upgrade_type = default
download_updates = yes
apply_updates = no
reboot = never

[emitters]
emit_via = stdio
CONF
  chmod 0644 /etc/dnf/automatic.conf
  systemctl enable --now dnf5-automatic.timer >/dev/null 2>&1 || true
  mp_check dnf_timer_active "$(systemctl is-active dnf5-automatic.timer >/dev/null 2>&1 && echo PASS || echo FAIL)"
  if grep -q '^download_updates = yes' /etc/dnf/automatic.conf && grep -q '^apply_updates = no' /etc/dnf/automatic.conf; then
    mp_check dnf_download_only PASS
  else
    mp_check dnf_download_only FAIL "automatic.conf does not stage-only"
  fi
  echo

  # ------------------------------------------------------------- 5.5 hostname
  echo "===== 5.5 static hostname ====="
  hostnamectl set-hostname "$HOSTNAME_TARGET"
  mp_expect hostname_static "$HOSTNAME_TARGET" "$(hostnamectl --static 2>/dev/null || echo unknown)"
  echo

  # ------------------------------------------------------- 5.6 runtime account
  echo "===== 5.6 runtime account ====="
  if ! id -u "$RUNTIME_ACCOUNT" >/dev/null 2>&1; then
    useradd --user-group --no-create-home --home-dir "$RUNTIME_HOME" --shell /usr/sbin/nologin "$RUNTIME_ACCOUNT"
    echo "created $RUNTIME_ACCOUNT"
  else
    echo "$RUNTIME_ACCOUNT already exists; preserved"
  fi
  passwd --lock "$RUNTIME_ACCOUNT" >/dev/null 2>&1 || true
  RUNTIME_UID=$(id -u "$RUNTIME_ACCOUNT")
  echo "runtime_uid=$RUNTIME_UID"
  if ! mountpoint -q "$RUNTIME_HOME"; then
    mp_check runtime_home_mount FAIL "$RUNTIME_HOME is not its own filesystem; refusing to continue"
    exit 1
  fi
  mp_check runtime_home_mount PASS
  chown "$RUNTIME_ACCOUNT:$RUNTIME_ACCOUNT" "$RUNTIME_HOME"
  chmod 0700 "$RUNTIME_HOME"
  restorecon -v "$RUNTIME_HOME" >/dev/null 2>&1 || true
  mp_expect runtime_shell /usr/sbin/nologin "$(getent passwd "$RUNTIME_ACCOUNT" | cut -d: -f7)"
  mp_expect runtime_locked L "$(passwd -S "$RUNTIME_ACCOUNT" | awk '{print $2}')"
  if sudo -l -U "$RUNTIME_ACCOUNT" 2>&1 | grep -qi 'not allowed to run sudo'; then
    mp_check runtime_no_sudo PASS
  else
    mp_check runtime_no_sudo FAIL "$RUNTIME_ACCOUNT appears to hold sudo authority"
  fi
  subuid_count=$(grep "^${RUNTIME_ACCOUNT}:" /etc/subuid 2>/dev/null | cut -d: -f3 | head -n1)
  subgid_count=$(grep "^${RUNTIME_ACCOUNT}:" /etc/subgid 2>/dev/null | cut -d: -f3 | head -n1)
  echo "subuid_count=${subuid_count:-0} subgid_count=${subgid_count:-0}"
  if [ "${subuid_count:-0}" -ge 65536 ] && [ "${subgid_count:-0}" -ge 65536 ]; then
    mp_check subordinate_ids PASS
  else
    mp_check subordinate_ids FAIL "need at least 65536 of each"
  fi
  echo

  # --------------------------------- 5.7 directories and the user manager
  echo "===== 5.7 directories and persistent user manager ====="
  install -d -o "$RUNTIME_ACCOUNT" -g "$RUNTIME_ACCOUNT" -m 0700 \
    "$RUNTIME_HOME/.config" "$RUNTIME_HOME/.local" "$RUNTIME_HOME/.cache/podman-tmp" \
    "$RUNTIME_HOME/gateway-state" "$RUNTIME_HOME/workspace" \
    "$RUNTIME_HOME/worker-state" "$RUNTIME_HOME/transport"
  restorecon -Rv "$RUNTIME_HOME" >/dev/null 2>&1 || true
  mp_check runtime_dirs "$([ -d "$RUNTIME_HOME/gateway-state" ] && [ -d "$RUNTIME_HOME/transport" ] && echo PASS || echo FAIL)"

  install -d -m 0755 "/etc/systemd/system/user@${RUNTIME_UID}.service.d"
  cat >"/etc/systemd/system/user@${RUNTIME_UID}.service.d/20-hermes-data.conf" <<'CONF'
[Unit]
RequiresMountsFor=/home/hermes
AssertPathIsMountPoint=/home/hermes
CONF
  chmod 0644 "/etc/systemd/system/user@${RUNTIME_UID}.service.d/20-hermes-data.conf"
  systemctl daemon-reload
  mp_check mount_assertion "$(grep -q '^AssertPathIsMountPoint=/home/hermes' "/etc/systemd/system/user@${RUNTIME_UID}.service.d/20-hermes-data.conf" && echo PASS || echo FAIL)"
  loginctl enable-linger "$RUNTIME_ACCOUNT"
  systemctl start "user@${RUNTIME_UID}.service" >/dev/null 2>&1 || true
  mp_expect linger_enabled yes "$(loginctl show-user "$RUNTIME_ACCOUNT" -p Linger --value 2>/dev/null || echo unknown)"
  mp_check user_manager_active "$(systemctl is-active "user@${RUNTIME_UID}.service" >/dev/null 2>&1 && echo PASS || echo FAIL)"
  echo

  # ------------------------------------------------------- 5.8 rootless check
  echo "===== 5.8 rootless container verification ====="
  info=$(h podman info --format \
    'rootless={{.Host.Security.Rootless}} cgroups={{.Host.CgroupsVersion}} manager={{.Host.CgroupManager}} driver={{.Store.GraphDriverName}} graphroot={{.Store.GraphRoot}}' 2>&1)
  printf '%s\n' "$info"
  if [[ "$info" == *"rootless=true"* ]]; then
    mp_check podman_rootless PASS
  else
    mp_check podman_rootless FAIL "$info"
  fi
  if [[ "$info" == *"graphroot=$RUNTIME_HOME"* ]]; then
    mp_check graphroot_on_data_mount PASS
  else
    mp_check graphroot_on_data_mount FAIL "container store is not on $RUNTIME_HOME"
  fi
  idmap=$(h podman unshare cat /proc/self/uid_map 2>&1 | tr '\n' ';')
  echo "uid_map=${idmap:-unavailable}"
  if [ -n "${idmap:-}" ] && [ "$idmap" != "unavailable" ]; then
    mp_check rootless_userns PASS
  else
    mp_check rootless_userns FAIL "cannot enter the rootless user namespace"
  fi
  echo

  echo "===== recent AVC denials ====="
  # Centralized: ausearch exits non-zero for a clean log ("<no matches>"), so the
  # return code alone must never be read as "unmeasurable".
  mp_audit_avc_check avc_denials recent
  echo "===== done ====="
} 2>&1 | tee "$OUT" || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
echo "WROTE=$OUT"
mp_finalize "$OUT" "${rc:-0}"
