#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC2034
# Private Fedora Server 44 host implementation used by the Hermes seams.

if [[ -n "${_HERMES_FEDORA_SERVER_HOST_LOADED-}" ]]; then
  return 0
fi
readonly _HERMES_FEDORA_SERVER_HOST_LOADED=1

readonly HERMES_SERVER_PLATFORM='fedora-server-44'
readonly HERMES_SERVER_MIN_PODMAN='5.8.4'
readonly HERMES_SERVER_MIN_MEMORY_KIB=8388608
readonly HERMES_SERVER_MIN_VAR_FREE_KIB=20971520
readonly HERMES_SERVER_MIN_POST_UPDATE_VAR_FREE_KIB=16777216
readonly HERMES_SERVER_MIN_POST_IMAGE_VAR_FREE_KIB=8388608

fedora_server_value() {
  local key=$1
  sed -n "s/^${key}=//p" /etc/os-release | sed -n '1p' | tr -d '"'
}

fedora_server_is_supported() {
  local id version variant pretty
  id=$(fedora_server_value ID)
  version=$(fedora_server_value VERSION_ID)
  variant=$(fedora_server_value VARIANT_ID)
  pretty=$(fedora_server_value PRETTY_NAME)
  [[ "$id" == fedora && "$version" == 44 &&
    ("$variant" == server || "$pretty" == *Server*) ]]
}

fedora_server_version() {
  fedora_server_value VERSION_ID
}

fedora_server_podman_version() {
  podman version --format '{{.Client.Version}}' 2>/dev/null || true
}

fedora_server_version_at_least() {
  local actual=$1
  local required=$2
  local first
  first=$(printf '%s\n%s\n' "$required" "$actual" | sort -V | head -n 1)
  [[ "$first" == "$required" ]]
}

fedora_server_install_prerequisites() {
  dnf5 install -y podman curl openssl python3 mokutil firewalld dnf5-plugin-automatic
  systemctl enable --now firewalld sshd
}

fedora_server_package_contract() {
  command -v podman >/dev/null 2>&1 \
    && command -v curl >/dev/null 2>&1 \
    && command -v openssl >/dev/null 2>&1 \
    && command -v python3 >/dev/null 2>&1 \
    && command -v mokutil >/dev/null 2>&1 \
    && command -v firewall-cmd >/dev/null 2>&1 \
    && [[ -f /usr/lib/systemd/system/dnf5-automatic.timer ]]
}

fedora_server_os_state() {
  local boot_id
  boot_id=$(cat /proc/sys/kernel/random/boot_id)
  printf 'platform=%s\n' "$HERMES_SERVER_PLATFORM"
  printf 'fedora_version=%s\n' "$(fedora_server_version)"
  printf 'kernel=%s\n' "$(uname -r)"
  printf 'podman=%s\n' "$(fedora_server_podman_version)"
  printf 'boot_id=%s\n' "$boot_id"
}

fedora_server_configure_automatic_updates() {
  local config=/etc/dnf/automatic.conf
  install -d -o root -g root -m 0755 /etc/dnf
  cat >"$config" <<'EOF'
[commands]
upgrade_type = default
random_sleep = 0
download_updates = True
apply_updates = False
reboot = never
EOF
  chown root:root "$config"
  chmod 0644 "$config"
  systemctl enable --now dnf5-automatic.timer
}

fedora_server_disable_cockpit() {
  local unit
  for unit in cockpit.socket cockpit.service cockpit-motd.service; do
    systemctl disable --now "$unit" >/dev/null 2>&1 || true
    systemctl mask "$unit" >/dev/null 2>&1 || true
  done
  firewall-cmd --permanent --remove-service=cockpit >/dev/null 2>&1 || true
  firewall-cmd --reload >/dev/null 2>&1 || true
}

fedora_server_prepare_offline_update() {
  local before
  before=$(cat /proc/sys/kernel/random/boot_id)
  printf '%s\n' "$before" >/var/lib/hermes-deploy/boot-id-before-update
  chmod 0600 /var/lib/hermes-deploy/boot-id-before-update
  dnf5 upgrade --offline -y
  dnf5 offline status || true
  printf 'UPDATE_STAGED\n'
}

fedora_server_reboot_for_offline_update() {
  # The deployment controller has already performed its production
  # confirmation (and certification runs are explicitly authorized).  Use
  # DNF5's own non-interactive option for this reboot-only prompt; the prompt
  # reads from the controlling terminal, so piping stdin does not answer it.
  dnf5 offline reboot --assumeyes
}

fedora_server_offline_update_pending() {
  local status
  status=$(dnf5 offline status 2>&1 || true)
  if grep -Eiq 'no[[:space:]].*offline.*transaction|no[[:space:]].*transaction|nothing[[:space:]]+to[[:space:]]+do' \
    <<<"$status"; then
    printf 'no\n'
  else
    printf 'yes\n'
  fi
}

fedora_server_verify_no_offline_update() {
  local current version first
  version=$(fedora_server_podman_version)
  first=$(printf '%s\n%s\n' "$HERMES_SERVER_MIN_PODMAN" "$version" | sort -V | head -n 1)
  [[ "$first" == "$HERMES_SERVER_MIN_PODMAN" ]] || {
    printf 'ERROR: Podman %s is below %s\n' "$version" "$HERMES_SERVER_MIN_PODMAN" >&2
    return 1
  }
  current=$(cat /proc/sys/kernel/random/boot_id)
  printf '%s\n' "$current" >/var/lib/hermes-deploy/boot-id-after-update
  chmod 0600 /var/lib/hermes-deploy/boot-id-after-update
  printf 'UPDATE_VERIFIED no-update podman=%s fedora=%s\n' "$version" "$(fedora_server_version)"
}

fedora_server_verify_offline_update() {
  local before current version first log_list latest_log
  before=$(sed -n '1p' /var/lib/hermes-deploy/boot-id-before-update 2>/dev/null || true)
  current=$(cat /proc/sys/kernel/random/boot_id)
  [[ -n "$before" && "$before" != "$current" ]] || {
    printf 'ERROR: boot ID did not change after the Fedora Server update\n' >&2
    return 1
  }
  dnf5 offline status >/dev/null 2>&1 || {
    printf 'ERROR: DNF5 offline transaction status is unavailable\n' >&2
    return 1
  }
  # DNF5 documents negative log numbers, but the Fedora 44 package parses the
  # value as an unsigned list index.  Select the newest positive index from
  # the documented log listing instead of passing --number=-1.
  log_list=$(dnf5 offline log 2>&1) || {
    printf 'ERROR: DNF5 offline transaction log list is unavailable\n' >&2
    return 1
  }
  latest_log=$(sed -n 's/^[[:space:]]*\([0-9][0-9]*\)[[:space:]]\+\/.*$/\1/p' <<<"$log_list" | tail -n 1)
  [[ -n "$latest_log" ]] || {
    printf 'ERROR: DNF5 offline transaction log list is empty\n' >&2
    return 1
  }
  dnf5 offline log --number="$latest_log" >/var/lib/hermes-deploy/dnf5-offline-log-after-update 2>&1 || {
    printf 'ERROR: DNF5 offline transaction log is unavailable\n' >&2
    return 1
  }
  [[ -s /var/lib/hermes-deploy/dnf5-offline-log-after-update ]] || {
    printf 'ERROR: DNF5 offline transaction log is empty\n' >&2
    return 1
  }
  chmod 0600 /var/lib/hermes-deploy/dnf5-offline-log-after-update
  version=$(fedora_server_podman_version)
  first=$(printf '%s\n%s\n' "$HERMES_SERVER_MIN_PODMAN" "$version" | sort -V | head -n 1)
  [[ "$first" == "$HERMES_SERVER_MIN_PODMAN" ]] || {
    printf 'ERROR: Podman %s is below %s\n' "$version" "$HERMES_SERVER_MIN_PODMAN" >&2
    return 1
  }
  printf '%s\n' "$current" >/var/lib/hermes-deploy/boot-id-after-update
  chmod 0600 /var/lib/hermes-deploy/boot-id-after-update
  printf 'UPDATE_VERIFIED podman=%s fedora=%s\n' "$version" "$(fedora_server_version)"
}

fedora_server_host_identity() {
  local machine_id ssh_fingerprint
  machine_id=$(sha256sum /etc/machine-id | awk '{print $1}')
  ssh_fingerprint=$(ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub -E sha256 \
    | awk '{for (i = 1; i <= NF; i++) if ($i ~ /^SHA256:/) {print $i; exit}}')
  [[ "$machine_id" =~ ^[[:xdigit:]]{64}$ ]] || return 1
  [[ "$ssh_fingerprint" =~ ^SHA256:[A-Za-z0-9+/]+={0,2}$ ]] || return 1
  printf 'machine_id_sha256=%s\n' "$machine_id"
  printf 'ssh_host_ed25519_fingerprint=%s\n' "$ssh_fingerprint"
}
