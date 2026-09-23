#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC1091
# Root-owned, no-argument Hermes deployment state engine.
#
# The workstation installs this file as /usr/local/libexec/hermes-deploy-root
# and grants the administrator a temporary sudo rule for the exact path with
# no command arguments. Every operation is selected by a fixed action read
# from stdin; user input is never evaluated as shell code.

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s nullglob

[[ "$EUID" -eq 0 ]] || {
  printf 'ERROR: root privileges are required\n' >&2
  exit 77
}
[[ $# -eq 0 ]] || {
  printf 'ERROR: this helper accepts no command arguments\n' >&2
  exit 64
}

readonly STATE_DIR='/var/lib/hermes-deploy'
readonly STAGE_DIR="$STATE_DIR/stages"
readonly MANIFEST="$STATE_DIR/manifest"
readonly IMAGE_REF='docker.io/nousresearch/hermes-agent@sha256:e0df6adebddf29b91112aefc999d4aaf6846c9eb544faca5672a16a13590ff79'
readonly IMAGE_DIGEST='sha256:e0df6adebddf29b91112aefc999d4aaf6846c9eb544faca5672a16a13590ff79'
readonly DEFAULT_PROVIDER='openai-codex'
readonly DEFAULT_OPENAI_MODEL='gpt-5.6-luna'
readonly DEFAULT_NOUS_MODEL='anthropic/claude-sonnet-4.6'
readonly ACCEPTANCE='/usr/local/libexec/hermes-acceptance'
readonly ROOT_ACCEPTANCE='/usr/local/libexec/hermes-root-acceptance'

if [[ -r /usr/local/libexec/hermes-provider-auth-status ]]; then
  # shellcheck source=/usr/local/libexec/hermes-provider-auth-status
  source /usr/local/libexec/hermes-provider-auth-status
elif [[ -r "${BASH_SOURCE[0]%/*}/provider-auth-status.sh" ]]; then
  # shellcheck source=provider-auth-status.sh
  source "${BASH_SOURCE[0]%/*}/provider-auth-status.sh"
fi
if [[ -r /usr/local/libexec/hermes-fedora-server-host ]]; then
  # shellcheck source=/usr/local/libexec/hermes-fedora-server-host
  source /usr/local/libexec/hermes-fedora-server-host
elif [[ -r "${BASH_SOURCE[0]%/*}/fedora-server-host.sh" ]]; then
  # shellcheck source=fedora-server-host.sh
  source "${BASH_SOURCE[0]%/*}/fedora-server-host.sh"
fi

STOPPED_CONTAINERS=''
RESTORE_DATA=0
BACKUP_INTERACTIVE=0
PROVIDER=''
MODEL=''
ACCEPTANCE_PROVIDER=''
ACCEPTANCE_MODEL=''
ACTIVE_PROVIDER=''

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

ensure_state() {
  install -d -o root -g root -m 0700 "$STATE_DIR" "$STAGE_DIR"
  chmod 0700 "$STATE_DIR" "$STAGE_DIR"
  chown root:root "$STATE_DIR" "$STAGE_DIR"
}

write_state() {
  local name=$1
  local value=$2
  local tmp
  [[ "$name" =~ ^[A-Za-z0-9._-]+$ ]] || die 'invalid state name'
  tmp=$(mktemp "$STATE_DIR/.$name.XXXXXX")
  chmod 0600 "$tmp"
  printf '%s\n' "$value" >"$tmp"
  mv -- "$tmp" "$STATE_DIR/$name"
  chmod 0600 "$STATE_DIR/$name"
}

read_state() {
  local name=$1
  [[ -r "$STATE_DIR/$name" ]] || return 1
  sed -n '1p' "$STATE_DIR/$name"
}

mark_stage() {
  local stage=$1
  local now
  [[ "$stage" =~ ^[a-z0-9-]+$ ]] || die 'invalid stage name'
  now=$(date -u +%s)
  write_state "$stage" "$now"
  write_state current-phase "$stage"
  cp -- "$STATE_DIR/$stage" "$STAGE_DIR/$stage"
  chmod 0600 "$STAGE_DIR/$stage"
}

stage_exists() {
  [[ -r "$STATE_DIR/$1" ]]
}

get_site_value() {
  local key=$1
  local value
  value=$(sed -n "s/^$key=//p" "$STATE_DIR/site.conf" | tail -n 1)
  [[ -n "$value" ]] || die "site value is missing: $key"
  printf '%s' "$value"
}

write_site() {
  local admin_user=$1
  local management_cidr=$2
  local management_interface=$3
  local tmp
  [[ "$admin_user" =~ ^[a-z_][a-z0-9_-]*$ ]] || die 'invalid administrator account'
  [[ "$management_interface" =~ ^[[:alnum:]_.:-]+$ ]] || die 'invalid management interface'
  valid_ipv4_cidr "$management_cidr" || die 'invalid management CIDR'
  tmp=$(mktemp "$STATE_DIR/.site.conf.XXXXXX")
  chmod 0600 "$tmp"
  {
    printf 'admin_user=%s\n' "$admin_user"
    printf 'management_cidr=%s\n' "$management_cidr"
    printf 'management_interface=%s\n' "$management_interface"
  } >"$tmp"
  mv -- "$tmp" "$STATE_DIR/site.conf"
  chmod 0600 "$STATE_DIR/site.conf"
  mark_stage site-configured
  printf 'SITE_CONFIGURED\n'
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

valid_temp_path() {
  [[ "$1" =~ ^/tmp/hermes-deploy\.[A-Za-z0-9]+$ ]]
}

valid_provider() {
  [[ "$1" == openai-codex || "$1" == openai-api || "$1" == nous ]]
}

valid_model() {
  [[ "$1" =~ ^[A-Za-z0-9._:/-]+$ ]]
}

provider_default_model() {
  case "$1" in
    openai-codex | openai-api) printf '%s\n' "$DEFAULT_OPENAI_MODEL" ;;
    nous) printf '%s\n' "$DEFAULT_NOUS_MODEL" ;;
    *) return 1 ;;
  esac
}

state_provider() {
  local provider
  provider=$(read_state provider || true)
  if [[ -z "$provider" ]]; then
    if stage_exists model-configured || stage_exists oauth; then
      provider=$DEFAULT_PROVIDER
    fi
  fi
  printf '%s\n' "$provider"
}

state_model() {
  local model provider
  model=$(read_state model || true)
  if [[ -z "$model" ]]; then
    provider=$(state_provider)
    if [[ -n "$provider" ]]; then
      model=$(provider_default_model "$provider")
    fi
  fi
  printf '%s\n' "$model"
}

auth_status() {
  local provider=$1 output
  valid_provider "$provider" || return 1
  output=$(as_hermes podman exec --user 10000:10000 hermes hermes auth status "$provider" 2>&1 || true)
  provider_auth_status_logged_in "$provider" "$output"
}

read_key_values() {
  local line key value
  while IFS= read -r line; do
    [[ "$line" == -- ]] && break
    IFS='=' read -r key value <<<"$line"
    [[ -z "$key" ]] && continue
    case "$key" in
      unit_path) UNIT_PATH=$value ;;
      runtime_dropin_path) RUNTIME_DROPIN_PATH=$value ;;
      volume_dropin_path) VOLUME_DROPIN_PATH=$value ;;
      harden_path) HARDEN_PATH=$value ;;
      model_path) MODEL_PATH=$value ;;
      acceptance_path) ACCEPTANCE_PATH=$value ;;
      root_acceptance_path) ROOT_ACCEPTANCE_PATH=$value ;;
      chat_path) CHAT_PATH=$value ;;
      status_path) STATUS_PATH=$value ;;
      logs_path) LOGS_PATH=$value ;;
      mode) ACCEPTANCE_MODE=$value ;;
      management_cidr) MANAGEMENT_CIDR=$value ;;
      management_interface) MANAGEMENT_INTERFACE=$value ;;
      provider) PROVIDER=$value ;;
      model) MODEL=$value ;;
      active_provider) ACTIVE_PROVIDER=$value ;;
      interactive) BACKUP_INTERACTIVE=$value ;;
      allow_update) ALLOW_UPDATE=$value ;;
      purge) PURGE=$value ;;
      restore_data) RESTORE_DATA=$value ;;
      *) die "unsupported helper input: $key" ;;
    esac
  done
}

as_hermes() {
  as_user hermes "$@"
}

as_user() {
  local user=$1 uid home
  shift
  uid=$(id -u "$user")
  home=$(getent passwd "$user" | cut -d: -f6)
  [[ -n "$home" ]] || die "home directory is unavailable for user: $user"
  (cd /tmp && runuser -u "$user" -- env HOME="$home" XDG_RUNTIME_DIR="/run/user/$uid" "$@")
}

container_owner() {
  if id hermes >/dev/null 2>&1; then
    printf 'hermes\n'
  else
    get_site_value admin_user
  fi
}

container_count() {
  local user=$1 container containers mounts count=0
  containers=$(as_user "$user" podman ps -a -q 2>/dev/null || true)
  while IFS= read -r container; do
    [[ -n "$container" ]] || continue
    mounts=$(as_user "$user" podman inspect "$container" \
      --format '{{range .Mounts}}{{.Source}}{{println}}{{end}}' 2>/dev/null || true)
    grep -Fxq /home/hermes/data <<<"$mounts" && count=$((count + 1))
  done <<<"$containers"
  printf '%s\n' "$count"
}

hermes_systemctl() {
  local uid
  uid=$(id -u hermes)
  (cd /tmp && runuser -u hermes -- env HOME=/home/hermes XDG_RUNTIME_DIR="/run/user/$uid" systemctl --user "$@")
}

capture_manifest_path() {
  local path=$1
  local index=$2
  local backup existed digest
  if [[ -e "$path" || -L "$path" ]]; then
    backup="$BACKUP_DIR/file-$index"
    cp -a -- "$path" "$backup"
    existed=1
    digest=$(sha256sum "$path" 2>/dev/null | awk '{print $1}' || true)
    [[ -n "$digest" ]] || digest=directory
  else
    backup=-
    existed=0
    digest=missing
  fi
  printf '%s\t%s\t%s\t%s\n' "$path" "$existed" "$backup" "$digest" >>"$MANIFEST.tmp"
}

capture_manifest() {
  local uid index path admin
  local -a managed_paths
  [[ -s "$MANIFEST" ]] && {
    printf 'MANIFEST_CURRENT\n'
    return
  }
  BACKUP_DIR="$STATE_DIR/backups/$(date -u +%Y%m%dT%H%M%SZ)"
  readonly BACKUP_DIR
  install -d -o root -g root -m 0700 "$BACKUP_DIR"
  install -d -o root -g root -m 0700 "$BACKUP_DIR/files"
  : >"$MANIFEST.tmp"
  chmod 0600 "$MANIFEST.tmp"
  managed_paths=(
    /etc/ssh/sshd_config.d/00-hermes-hardening.conf
    /etc/systemd/resolved.conf.d/60-hermes-hardening.conf
    /etc/dnf/automatic.conf
    /etc/firewalld
    /etc/systemd/user/hermes.service.d/60-hermes-runtime.conf
    /etc/systemd/user/hermes.service.d/70-hermes-volume-label.conf
    /usr/local/libexec/hermes-acceptance
    /usr/local/libexec/hermes-root-acceptance
    /home/hermes/.config/systemd/user/hermes.service.d/reset-network-dep.conf
    /etc/systemd/system/avahi-daemon.service
    /etc/systemd/system/avahi-daemon.socket
    /etc/systemd/system/cups.service
    /etc/systemd/system/cups.socket
    /etc/systemd/system/cups.path
    /etc/systemd/system/passim.service
    /etc/xdg/autostart/org.kde.kdeconnect.daemon.desktop
    /etc/systemd/system/sleep.target
    /etc/systemd/system/suspend.target
    /etc/systemd/system/hibernate.target
    /etc/systemd/system/hybrid-sleep.target
    /etc/systemd/system/cockpit.service
    /etc/systemd/system/cockpit.socket
    /etc/systemd/system/cockpit-motd.service
    /etc/systemd/system/timers.target.wants/dnf5-automatic.timer
    /usr/local/bin/hermes-chat
    /usr/local/bin/hermes-status
    /usr/local/bin/hermes-logs
  )
  admin=$(get_site_value admin_user)
  managed_paths+=(
    "/etc/sudoers.d/$admin-hermes-deploy"
    "/etc/sudoers.d/$admin-hermes-wrappers"
  )
  index=0
  for path in "${managed_paths[@]}"; do
    capture_manifest_path "$path" "$index"
    index=$((index + 1))
  done
  uid=$(id -u hermes 2>/dev/null || true)
  if [[ -n "$uid" ]]; then
    capture_manifest_path "/etc/containers/systemd/users/$uid/hermes.container" "$index"
  else
    printf '%s\t0\t-\tmissing\n' /etc/containers/systemd/users/UNKNOWN/hermes.container >>"$MANIFEST.tmp"
  fi
  write_state manifest-boot-id "$(cat /proc/sys/kernel/random/boot_id)"
  if [[ -n "$uid" ]]; then
    write_state previous-image "$(as_hermes podman inspect hermes --format '{{.ImageName}}' 2>/dev/null || true)"
  else
    write_state previous-image absent
  fi
  if id hermes >/dev/null 2>&1; then
    if hermes_systemctl is-active hermes.service >/dev/null 2>&1; then
      write_state previous-service-state active
    else
      write_state previous-service-state inactive
    fi
  else
    write_state previous-service-state inactive
  fi
  mv -- "$MANIFEST.tmp" "$MANIFEST"
  chmod 0600 "$MANIFEST"
  write_state backup-dir "$BACKUP_DIR"
  mark_stage manifest
  printf 'MANIFEST_CREATED\n'
}

resume_stopped_containers() {
  local rc=$?
  local container local_user
  if [[ -n "$STOPPED_CONTAINERS" ]]; then
    while IFS= read -r container; do
      local_user=$(read_state "manual-container-user-$container" || true)
      [[ -n "$local_user" ]] || local_user=hermes
      [[ -n "$container" ]] && as_user "$local_user" podman start "$container" >/dev/null 2>&1 || true
    done <<<"$STOPPED_CONTAINERS"
  fi
  restore_manual_restart_policies
  return "$rc"
}

restore_manual_restart_policies() {
  local record container policy local_user
  for record in "$STATE_DIR"/manual-restart-policy-*; do
    [[ -r "$record" ]] || continue
    container=$(printf '%s\n' "$record" | sed "s#^$STATE_DIR/manual-restart-policy-##")
    policy=$(read_state "manual-restart-policy-$container" || true)
    local_user=$(read_state "manual-container-user-$container" || true)
    [[ -n "$local_user" ]] || local_user=hermes
    [[ -n "$policy" && "$policy" != none ]] \
      && as_user "$local_user" podman update --restart-policy="$policy" "$container" >/dev/null 2>&1 || true
  done
}

restore_manual_containers() {
  local record container local_user
  restore_manual_restart_policies
  for record in "$STATE_DIR"/manual-running-*; do
    [[ -r "$record" ]] || continue
    container=$(printf '%s\n' "$record" | sed "s#^$STATE_DIR/manual-running-##")
    local_user=$(read_state "manual-container-user-$container" || true)
    [[ -n "$local_user" ]] || local_user=hermes
    as_user "$local_user" podman start "$container" >/dev/null 2>&1 || true
  done
}

backup_data() {
  local archive container containers mounts restart_policy owner runtime_state
  local backup_dir manual_count
  backup_dir=$(read_state backup-dir)
  [[ -n "$backup_dir" ]] || die 'manifest backup directory is unavailable'
  owner=$(container_owner)
  manual_count=$(container_count "$owner")
  if id hermes >/dev/null 2>&1; then
    runtime_state=managed
  elif [[ "$manual_count" =~ ^[1-9][0-9]*$ ]]; then
    runtime_state=manual-container
  else
    runtime_state=fresh
  fi
  write_state detected-runtime-state "$runtime_state"
  if [[ ! -d /home/hermes/data ]]; then
    mark_stage data-backup
    printf 'DATA_BACKUP_NOT_NEEDED\n'
    return
  fi
  if [[ -s "$backup_dir/data.tgz.enc" && -s "$backup_dir/data.tgz.enc.sha256" ]]; then
    sha256sum -c -- "$backup_dir/data.tgz.enc.sha256" >/dev/null 2>&1 \
      || die 'existing data backup checksum failed'
    mark_stage data-backup
    printf 'DATA_BACKUP_CURRENT\n'
    return
  fi
  [[ "$BACKUP_INTERACTIVE" == 1 ]] || {
    printf 'BACKUP_PASSPHRASE_REQUIRED\n' >&2
    return 75
  }
  containers=$(as_user "$owner" podman ps -a -q 2>/dev/null || true)
  STOPPED_CONTAINERS=''
  while IFS= read -r container; do
    [[ -n "$container" ]] || continue
    mounts=$(as_user "$owner" podman inspect "$container" \
      --format '{{range .Mounts}}{{.Source}}{{println}}{{end}}' 2>/dev/null || true)
    if grep -Fxq /home/hermes/data <<<"$mounts"; then
      write_state "manual-container-user-$container" "$owner"
      restart_policy=$(as_user "$owner" podman inspect "$container" \
        --format '{{.HostConfig.RestartPolicy.Name}}' 2>/dev/null || true)
      if [[ -n "$restart_policy" && "$restart_policy" != none ]]; then
        write_state "manual-restart-policy-$container" "$restart_policy"
        as_user "$owner" podman update --restart-policy=no "$container" >/dev/null
      fi
      if as_user "$owner" podman inspect "$container" --format '{{.State.Running}}' 2>/dev/null | grep -qx true; then
        write_state "manual-running-$container" 1
        as_user "$owner" podman stop --time 30 "$container" >/dev/null
        STOPPED_CONTAINERS+="$container"$'\n'
      fi
    fi
  done <<<"$containers"
  trap resume_stopped_containers EXIT
  archive="$backup_dir/data.tgz.enc"
  printf 'Enter a new backup passphrase twice; it is never saved by the deployment.\n' >&2
  as_user "$owner" podman unshare tar -C /home/hermes/data -czf - . \
    | openssl enc -aes-256-cbc -salt -pbkdf2 -out "$archive"
  openssl enc -d -aes-256-cbc -pbkdf2 -in "$archive" | tar -tzf - >/dev/null
  sha256sum "$archive" >"$archive.sha256"
  chmod 0600 "$archive" "$archive.sha256"
  trap - EXIT
  mark_stage data-backup
  printf 'DATA_BACKUP_VERIFIED\n'
}

stage_update() {
  fedora_server_prepare_offline_update
  mark_stage update-staged
  printf 'UPDATE_STAGED\n'
}

install_prerequisites() {
  fedora_server_install_prerequisites
  mark_stage prerequisites
  printf 'PREREQUISITES_READY\n'
}

verify_update() {
  fedora_server_verify_offline_update || die 'Fedora Server offline update verification failed'
  mark_stage update-verified
  printf 'UPDATE_VERIFIED\n'
}

configure_host_policy() {
  local admin cidr iface zone rule ssh_file resolved_file kdeconnect_file
  admin=$(get_site_value admin_user)
  cidr=$(get_site_value management_cidr)
  iface=$(get_site_value management_interface)
  ssh_file=/etc/ssh/sshd_config.d/00-hermes-hardening.conf
  resolved_file=/etc/systemd/resolved.conf.d/60-hermes-hardening.conf
  install -d -o root -g root -m 0755 /etc/ssh/sshd_config.d /etc/systemd/resolved.conf.d
  {
    printf 'PasswordAuthentication no\n'
    printf 'KbdInteractiveAuthentication no\n'
    printf 'PubkeyAuthentication yes\n'
    printf 'PermitRootLogin no\n'
    printf 'AllowUsers %s\n' "$admin"
    printf 'AllowTcpForwarding no\n'
    printf 'X11Forwarding no\n'
    printf 'PermitTunnel no\n'
    printf 'GatewayPorts no\n'
  } >"$ssh_file"
  chmod 0644 "$ssh_file"
  sshd -t
  zone=$(firewall-cmd --get-zone-of-interface="$iface" 2>/dev/null || true)
  [[ -n "$zone" ]] || zone=$(firewall-cmd --get-default-zone)
  rule="rule family=\"ipv4\" source address=\"$cidr\" service name=\"ssh\" accept"
  if ! firewall-cmd --permanent --zone="$zone" --query-rich-rule="$rule" >/dev/null 2>&1; then
    firewall-cmd --permanent --zone="$zone" --add-rich-rule="$rule"
  fi
  for service in ssh mdns kdeconnect; do
    firewall-cmd --permanent --zone="$zone" --remove-service="$service" || true
  done
  firewall-cmd --reload
  firewall-cmd --zone="$zone" --query-rich-rule="$rule" >/dev/null
  {
    printf '[Resolve]\n'
    printf 'LLMNR=no\n'
    printf 'MulticastDNS=no\n'
  } >"$resolved_file"
  chmod 0644 "$resolved_file"
  systemctl restart systemd-resolved
  for unit in avahi-daemon.socket avahi-daemon.service cups.socket cups.path cups.service passim.service \
    cockpit.socket cockpit.service cockpit-motd.service; do
    systemctl disable --now "$unit" >/dev/null 2>&1 || true
    systemctl mask "$unit" >/dev/null 2>&1 || true
  done
  kdeconnect_file=/etc/xdg/autostart/org.kde.kdeconnect.daemon.desktop
  if [[ -f "$kdeconnect_file" && ! -L "$kdeconnect_file" ]]; then
    if grep -q '^Hidden=' "$kdeconnect_file"; then
      sed -i 's/^Hidden=.*/Hidden=true/' "$kdeconnect_file"
    else
      printf '\nHidden=true\n' >>"$kdeconnect_file"
    fi
  fi
  pkill -x kdeconnectd >/dev/null 2>&1 || true
  systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
  fedora_server_configure_automatic_updates
  fedora_server_disable_cockpit
  systemctl reload sshd
  mark_stage host-policy
  printf 'HOST_POLICY_APPLIED\n'
}

rollback_host_policy() {
  restore_manifest
  restore_manual_containers
  systemctl daemon-reload || true
  firewall-cmd --reload || true
  systemctl restart systemd-resolved || true
  systemctl reload sshd || true
  printf 'HOST_POLICY_RESTORED\n'
}

ensure_identity() {
  local fresh_identity fresh_data uid
  fresh_identity=0
  fresh_data=0
  id hermes >/dev/null 2>&1 || fresh_identity=1
  [[ -d /home/hermes/data ]] || fresh_data=1
  if ((fresh_identity == 1)); then
    # Pin the logical home explicitly so the managed identity remains stable
    # across reinstall and deployment resume.
    useradd -m -d /home/hermes -U -s /bin/bash hermes
    write_state fresh-identity 1
  fi
  if ((fresh_data == 1)); then
    write_state fresh-data 1
  fi
  [[ "$(getent passwd hermes | cut -d: -f6)" == /home/hermes ]] \
    || die 'Hermes identity does not use the managed /home/hermes home'
  [[ -d /home/hermes && ! -L /home/hermes && ! -L /home/hermes/data ]] \
    || die 'Hermes home or data path is a symlink'
  chmod 0700 /home/hermes
  passwd -l hermes >/dev/null
  [[ ! -e /home/hermes/.ssh/authorized_keys ]] || die 'Hermes identity has an authorized key'
  grep -q '^hermes:' /etc/subuid || usermod --add-subuids 100000-165535 hermes
  grep -q '^hermes:' /etc/subgid || usermod --add-subgids 100000-165535 hermes
  install -d -o hermes -g hermes -m 0700 /home/hermes/data
  loginctl enable-linger hermes
  uid=$(id -u hermes)
  systemctl start "user@$uid.service"
  write_state hermes-uid "$uid"
  mark_stage identity
  printf 'IDENTITY_READY uid=%s\n' "$uid"
}

check_artifact() {
  local path=$1
  valid_temp_path "$path" || die 'artifact path is not a validated temporary path'
  [[ -r "$path" ]] || die "artifact is not readable: $path"
}

wait_for_healthy() {
  local health attempt
  for attempt in {1..36}; do
    : "$attempt"
    health=$(as_hermes podman inspect hermes --format '{{.State.Health.Status}}' 2>/dev/null || true)
    [[ "$health" == healthy ]] && return 0
    sleep 5
  done
  die "Hermes health did not become healthy (last=$health)"
}

install_runtime() {
  local uid unit_path
  check_artifact "$UNIT_PATH"
  check_artifact "$RUNTIME_DROPIN_PATH"
  check_artifact "$VOLUME_DROPIN_PATH"
  grep -Fxq "Image=$IMAGE_REF" "$UNIT_PATH" || die 'Quadlet image pin drifted'
  grep -Fxq 'Pull=never' "$UNIT_PATH" || die 'Quadlet Pull=never drifted'
  uid=$(id -u hermes)
  as_hermes podman pull "$IMAGE_REF"
  [[ "$(as_hermes podman image inspect "$IMAGE_REF" --format '{{.Digest}}')" == "$IMAGE_DIGEST" ]] \
    || die 'pulled image digest does not match the locked digest'
  unit_path="/etc/containers/systemd/users/$uid/hermes.container"
  install -d -o root -g root -m 0755 "/etc/containers/systemd/users/$uid"
  install -o root -g root -m 0644 "$UNIT_PATH" "$unit_path"
  install -d -o root -g root -m 0755 /etc/systemd/user/hermes.service.d
  install -o root -g root -m 0644 "$RUNTIME_DROPIN_PATH" \
    /etc/systemd/user/hermes.service.d/60-hermes-runtime.conf
  install -o root -g root -m 0644 "$VOLUME_DROPIN_PATH" \
    /etc/systemd/user/hermes.service.d/70-hermes-volume-label.conf
  rm -f /home/hermes/.config/systemd/user/hermes.service.d/reset-network-dep.conf
  rmdir /home/hermes/.config/systemd/user/hermes.service.d 2>/dev/null || true
  hermes_systemctl daemon-reload
  hermes_systemctl reset-failed hermes.service || true
  hermes_systemctl restart hermes.service
  wait_for_healthy
  if ! stage_exists first-successful-start; then
    write_state first-successful-start "$(date -u +%s)"
  fi
  mark_stage runtime-credential-free
  printf 'RUNTIME_READY\n'
}

install_runtime_helpers() {
  check_artifact "$ACCEPTANCE_PATH"
  check_artifact "$ROOT_ACCEPTANCE_PATH"
  install -o root -g root -m 0755 "$ACCEPTANCE_PATH" "$ACCEPTANCE"
  install -o root -g root -m 0755 "$ROOT_ACCEPTANCE_PATH" "$ROOT_ACCEPTANCE"
  if [[ -r /usr/local/libexec/hermes-provider-auth-status ]]; then
    chmod 0755 /usr/local/libexec/hermes-provider-auth-status
  fi
  if [[ -r /usr/local/libexec/hermes-fedora-server-host ]]; then
    chmod 0755 /usr/local/libexec/hermes-fedora-server-host
  fi
  printf 'RUNTIME_HELPERS_INSTALLED\n'
}

apply_python_patch() {
  local path=$1
  check_artifact "$path"
  as_hermes podman exec -i --user 10000:10000 hermes python3 - <"$path"
  hermes_systemctl restart hermes.service
  wait_for_healthy
}

apply_hardening() {
  apply_python_patch "$HARDEN_PATH"
  mark_stage hardening
  printf 'HARDENING_APPLIED\n'
}

apply_model() {
  valid_provider "$PROVIDER" || die 'provider is invalid'
  valid_model "$MODEL" || die 'model is invalid'
  check_artifact "$MODEL_PATH"
  as_hermes podman exec -i --user 10000:10000 \
    -e "HERMES_PROVIDER=$PROVIDER" -e "HERMES_MODEL=$MODEL" hermes python3 - <"$MODEL_PATH"
  hermes_systemctl restart hermes.service
  wait_for_healthy
  write_state provider "$PROVIDER"
  write_state model "$MODEL"
  mark_stage model-configured
  printf 'MODEL_CONFIGURED\n'
}

reboot_host() {
  local boot_id
  boot_id=$(cat /proc/sys/kernel/random/boot_id)
  write_state boot-id-before-hermes-reboot "$boot_id"
  mark_stage reboot-requested
  systemctl reboot
}

host_identity() {
  fedora_server_host_identity || die 'Fedora Server host identity could not be read'
}

verify_hermes_reboot() {
  local before current
  before=$(read_state boot-id-before-hermes-reboot || true)
  current=$(cat /proc/sys/kernel/random/boot_id)
  [[ -n "$before" && "$before" != "$current" ]] || die 'boot ID did not change after Hermes reboot'
  write_state boot-id-after-hermes-reboot "$current"
  mark_stage reboot-verified
  printf 'HERMES_REBOOT_VERIFIED\n'
}

run_acceptance() {
  local provider model
  wait_for_healthy
  case "$ACCEPTANCE_MODE" in
    credential-free) "$ACCEPTANCE" --credential-free ;;
    provider | inference)
      provider=${ACCEPTANCE_PROVIDER:-$(state_provider)}
      model=${ACCEPTANCE_MODEL:-$(state_model)}
      [[ -n "$provider" && -n "$model" ]] || die 'provider and model are required for acceptance'
      valid_provider "$provider" || die 'provider is invalid for acceptance'
      valid_model "$model" || die 'model is invalid for acceptance'
      if [[ "$ACCEPTANCE_MODE" == provider ]]; then
        "$ACCEPTANCE" --provider "$provider" --model "$model" --provider-required
      else
        "$ACCEPTANCE" --provider "$provider" --model "$model" --provider-required --inference-required
      fi
      ;;
    *) die 'unsupported acceptance mode' ;;
  esac
  mark_stage "$ACCEPTANCE_MODE-acceptance"
  printf 'ACCEPTANCE_VERIFIED mode=%s\n' "$ACCEPTANCE_MODE"
}

run_provider_auth() {
  local auth_type label
  id hermes >/dev/null 2>&1 || die 'Hermes identity is absent'
  valid_provider "$PROVIDER" || die 'provider is invalid'
  case "$PROVIDER" in
    openai-api)
      auth_type=api-key
      label='OpenAI API key'
      ;;
    openai-codex)
      auth_type=oauth
      label='ChatGPT or Codex Subscription'
      ;;
    nous)
      auth_type=oauth
      label='Nous Portal'
      ;;
    *)
      die 'provider is invalid'
      ;;
  esac
  printf 'Starting the interactive %s authentication flow in the operator terminal.\n' "$label"
  if [[ "$auth_type" == api-key ]]; then
    printf 'Hermes will prompt for the API key without displaying or storing it in deployment output.\n' >&2
  fi
  as_hermes podman exec -it --user 10000:10000 hermes hermes auth add "$PROVIDER" --type "$auth_type"
  write_state provider "$PROVIDER"
  mark_stage oauth
  printf 'PROVIDER_AUTH_COMPLETE provider=%s\n' "$PROVIDER"
}

validate_provider_auth() {
  valid_provider "$PROVIDER" || return 1
  auth_status "$PROVIDER"
}

validate_provider() {
  local config provider model
  valid_provider "$PROVIDER" || return 1
  valid_model "$MODEL" || return 1
  config=$(
    as_hermes podman exec -i --user 10000:10000 hermes python3 - <<'PY'
import pathlib
import yaml

data = yaml.safe_load(pathlib.Path('/opt/data/config.yaml').read_text(encoding='utf-8')) or {}
section = data.get('model') if isinstance(data.get('model'), dict) else {}
provider = section.get('provider') or data.get('provider') or ''
model = section.get('default') or section.get('model') or data.get('default_model') or data.get('model_name') or ''
print(f'{provider}\t{model}')
PY
  )
  IFS=$'\t' read -r provider model <<<"$config"
  [[ "$provider" == "$PROVIDER" && "$model" == "$MODEL" ]] || return 1
  validate_provider_auth
}

prune_auth() {
  local provider
  valid_provider "$ACTIVE_PROVIDER" || die 'active provider is invalid'
  for provider in openai-codex openai-api nous; do
    [[ "$provider" == "$ACTIVE_PROVIDER" ]] && continue
    if auth_status "$provider"; then
      as_hermes podman exec --user 10000:10000 hermes hermes auth logout "$provider" >/dev/null 2>&1 || true
      auth_status "$provider" && die "provider credentials remain active: $provider"
    fi
  done
  printf 'AUTH_PRUNED active_provider=%s\n' "$ACTIVE_PROVIDER"
}

install_wrappers() {
  local admin sudoers_tmp
  check_artifact "$CHAT_PATH"
  check_artifact "$STATUS_PATH"
  check_artifact "$LOGS_PATH"
  admin=$(get_site_value admin_user)
  install -o root -g root -m 0755 "$CHAT_PATH" /usr/local/bin/hermes-chat
  install -o root -g root -m 0755 "$STATUS_PATH" /usr/local/bin/hermes-status
  install -o root -g root -m 0755 "$LOGS_PATH" /usr/local/bin/hermes-logs
  sudoers_tmp=$(mktemp /etc/sudoers.d/.hermes-deploy.XXXXXX)
  chmod 0440 "$sudoers_tmp"
  {
    printf '%s ALL=(root) NOPASSWD: /usr/local/bin/hermes-chat ""\n' "$admin"
    printf '%s ALL=(root) NOPASSWD: /usr/local/bin/hermes-status ""\n' "$admin"
    printf '%s ALL=(root) NOPASSWD: /usr/local/bin/hermes-logs ""\n' "$admin"
  } >"$sudoers_tmp"
  chown root:root "$sudoers_tmp"
  visudo -cf "$sudoers_tmp"
  mv -- "$sudoers_tmp" "/etc/sudoers.d/$admin-hermes-wrappers"
  chmod 0440 "/etc/sudoers.d/$admin-hermes-wrappers"
  mark_stage wrappers
  printf 'WRAPPERS_INSTALLED\n'
}

close_deployment() {
  local admin sudoers_file
  admin=$(get_site_value admin_user)
  sudoers_file="/etc/sudoers.d/$admin-hermes-deploy"
  rm -f "$sudoers_file"
  rm -f /usr/local/libexec/hermes-deploy-root /usr/local/libexec/hermes-preflight
  mark_stage closed
  printf 'DEPLOYMENT_CLOSED\n'
}

remove_helper() {
  local admin sudoers_file
  admin=$(get_site_value admin_user)
  sudoers_file="/etc/sudoers.d/$admin-hermes-deploy"
  rm -f "$sudoers_file" /usr/local/libexec/hermes-deploy-root /usr/local/libexec/hermes-preflight
  printf 'TEMPORARY_HELPER_REMOVED\n'
}

restore_manifest() {
  local path existed backup expected uid
  [[ -r "$MANIFEST" ]] || die 'deployment manifest is missing'
  while IFS=$'\t' read -r path existed backup expected; do
    : "$expected"
    [[ -n "$path" ]] || continue
    if [[ "$path" == */users/UNKNOWN/hermes.container ]]; then
      uid=$(id -u hermes 2>/dev/null || true)
      [[ -n "$uid" ]] || continue
      path="/etc/containers/systemd/users/$uid/hermes.container"
    fi
    if [[ "$existed" == 1 ]]; then
      [[ -e "$backup" || -L "$backup" ]] || die "manifest backup missing: $path"
      if [[ "$expected" != directory && "$expected" != missing ]]; then
        [[ "$(sha256sum "$backup" 2>/dev/null | awk '{print $1}')" == "$expected" ]] \
          || die "manifest backup checksum failed: $path"
      fi
      rm -rf -- "$path"
      install -d -o root -g root -m 0755 "$(dirname "$path")"
      cp -a -- "$backup" "$path"
    else
      rm -rf -- "$path"
    fi
  done <"$MANIFEST"
}

restore_data_backup() {
  local backup_dir archive restore_dir old_data
  backup_dir=$(read_state backup-dir || true)
  [[ "$backup_dir" == "$STATE_DIR/backups/"* ]] || die 'data backup directory is invalid'
  archive="$backup_dir/data.tgz.enc"
  [[ -s "$archive" && -s "$archive.sha256" ]] || die 'verified data backup is missing'
  sha256sum -c -- "$archive.sha256" >/dev/null 2>&1 || die 'data backup checksum failed'
  restore_dir=$(mktemp -d /home/hermes/.hermes-restore.XXXXXX)
  chown hermes:hermes "$restore_dir"
  chmod 0700 "$restore_dir"
  if ! openssl enc -d -aes-256-cbc -pbkdf2 -in "$archive" 2>/dev/null \
    | as_hermes podman unshare tar -C "$restore_dir" -xzf -; then
    rm -rf -- "$restore_dir"
    die 'encrypted data backup could not be decrypted and extracted'
  fi
  old_data="$backup_dir/.data-before-rollback"
  rm -rf -- "$old_data"
  mv -- /home/hermes/data "$old_data"
  if ! mv -- "$restore_dir" /home/hermes/data; then
    mv -- "$old_data" /home/hermes/data
    rm -rf -- "$restore_dir"
    die 'restored data directory could not be installed'
  fi
  chown hermes:hermes /home/hermes/data
  chmod 0700 /home/hermes/data
  rm -rf -- "$old_data"
  printf 'DATA_RESTORED\n'
}

rollback_deployment() {
  local purge uid
  purge=$PURGE
  [[ "$purge" == 0 || "$purge" == 1 ]] || die 'invalid purge selection'
  [[ "$RESTORE_DATA" == 0 || "$RESTORE_DATA" == 1 ]] || die 'invalid data restore selection'
  if id hermes >/dev/null 2>&1; then
    hermes_systemctl stop hermes.service || true
    as_hermes podman stop --time 30 hermes >/dev/null 2>&1 || true
  fi
  restore_manifest
  restore_manual_restart_policies
  if [[ "$RESTORE_DATA" == 1 ]]; then
    restore_data_backup
  fi
  systemctl daemon-reload || true
  firewall-cmd --reload || true
  systemctl restart systemd-resolved || true
  sshd -t && systemctl reload sshd || true
  if [[ "$(read_state previous-service-state || true)" == active ]] && id hermes >/dev/null 2>&1; then
    hermes_systemctl daemon-reload || true
    hermes_systemctl start hermes.service || true
  elif id hermes >/dev/null 2>&1; then
    restore_manual_containers
  fi
  if [[ "$purge" == 1 ]]; then
    [[ "$(read_state fresh-identity || true)" == 1 ]] || die 'purge refused: identity was not created by this installer'
    [[ "$(read_state fresh-data || true)" == 1 ]] || die 'purge refused: data was not created by this installer'
    loginctl disable-linger hermes || true
    loginctl terminate-user hermes || true
    uid=$(id -u hermes 2>/dev/null || true)
    [[ -n "$uid" ]] && systemctl stop "user@$uid.service" || true
    rm -rf -- /home/hermes/data
    userdel --remove hermes
  fi
  write_state rollback-purge "$purge"
  mark_stage rolled-back
  printf 'ROLLBACK_COMPLETE purge=%s\n' "$purge"
}

revoke_auth() {
  valid_provider "$PROVIDER" || die 'provider is invalid'
  id hermes >/dev/null 2>&1 || die 'Hermes identity is absent'
  as_hermes podman exec --user 10000:10000 hermes hermes auth logout "$PROVIDER" >/dev/null 2>&1 || true
  auth_status "$PROVIDER" && die "provider credentials remain active: $PROVIDER"
  mark_stage auth-revoked
  printf 'AUTH_REVOKED provider=%s\n' "$PROVIDER"
}

validate_stage() {
  local stage=$1 uid unit health first backup_dir archive provider model
  case "$stage" in
    site-configured)
      [[ -r "$STATE_DIR/site.conf" ]]
      ;;
    manifest)
      [[ -s "$MANIFEST" ]]
      ;;
    prerequisites)
      fedora_server_package_contract
      ;;
    update-verified)
      [[ -r "$STATE_DIR/boot-id-after-update" ]] || return 1
      fedora_server_is_supported || return 1
      first=$(printf '%s\n%s\n' "$HERMES_SERVER_MIN_PODMAN" \
        "$(fedora_server_podman_version)" | sort -V | head -n 1)
      [[ "$first" == "$HERMES_SERVER_MIN_PODMAN" ]]
      ;;
    update-staged)
      stage_exists update-staged && dnf5 offline status >/dev/null 2>&1
      ;;
    host-policy)
      [[ -r /etc/ssh/sshd_config.d/00-hermes-hardening.conf ]] \
        && [[ -r /etc/systemd/resolved.conf.d/60-hermes-hardening.conf ]] \
        && [[ -r /etc/dnf/automatic.conf ]] \
        && grep -Eiq '^apply_updates[[:space:]]*=[[:space:]]*False' /etc/dnf/automatic.conf \
        && grep -Eiq '^reboot[[:space:]]*=[[:space:]]*never' /etc/dnf/automatic.conf \
        && systemctl is-enabled dnf5-automatic.timer >/dev/null 2>&1 \
        && [[ "$(systemctl is-active cockpit.socket 2>/dev/null || true)" != active ]]
      ;;
    identity)
      id hermes >/dev/null 2>&1 && [[ -e /var/lib/systemd/linger/hermes ]] \
        && grep -q '^hermes:' /etc/subuid && grep -q '^hermes:' /etc/subgid
      ;;
    runtime-credential-free)
      uid=$(id -u hermes 2>/dev/null || true)
      unit="/etc/containers/systemd/users/$uid/hermes.container"
      [[ -r "$unit" ]] && grep -Fxq "Image=$IMAGE_REF" "$unit" \
        && [[ "$(hermes_systemctl is-active hermes.service 2>/dev/null || true)" == active ]] \
        && health=$(as_hermes podman inspect hermes --format '{{.State.Health.Status}}' 2>/dev/null || true) \
        && [[ "$health" == healthy ]]
      ;;
    data-backup)
      stage_exists data-backup || return 1
      [[ "$(read_state fresh-data || true)" == 1 ]] && return 0
      [[ -d /home/hermes/data ]] || return 0
      backup_dir=$(read_state backup-dir || true)
      archive="$backup_dir/data.tgz.enc"
      [[ -n "$backup_dir" && -s "$archive" && -s "$archive.sha256" ]] || return 1
      sha256sum -c -- "$archive.sha256" >/dev/null 2>&1 || return 1
      return 0
      ;;
    root-acceptance)
      stage_exists root-acceptance && [[ -x "$ROOT_ACCEPTANCE" ]] && "$ROOT_ACCEPTANCE" >/dev/null
      ;;
    oauth)
      stage_exists oauth && auth_status "$(state_provider)"
      ;;
    hardening | post-auth-hardening)
      stage_exists "$stage" && as_hermes podman exec --user 10000:10000 hermes python3 -c '
import pathlib
import yaml
data = yaml.safe_load(pathlib.Path("/opt/data/config.yaml").read_text(encoding="utf-8")) or {}
skills = data.get("skills", {})
memory = data.get("memory", {})
plugins = data.get("plugins", {})
valid = (
    data.get("hooks_auto_accept") is False
    and data.get("mcp_servers") == {}
    and data.get("hooks") == {}
    and plugins.get("enabled") == []
    and plugins.get("disabled") == []
    and skills.get("external_dirs") == []
    and skills.get("trusted_project_dirs") == []
    and skills.get("project_discovery") is False
    and memory.get("provider") == ""
    and memory.get("write_approval") is True
    and data.get("platform_toolsets", {}).get("cli") == ["hermes-cli"]
)
raise SystemExit(0 if valid else 1)
'
      ;;
    model-configured)
      stage_exists model-configured && {
        PROVIDER=$(state_provider)
        MODEL=$(state_model)
        valid_provider "$PROVIDER" && valid_model "$MODEL"
      } && as_hermes podman exec --user 10000:10000 hermes python3 -c '
import pathlib
import sys
import yaml
data = yaml.safe_load(pathlib.Path("/opt/data/config.yaml").read_text(encoding="utf-8")) or {}
section = data.get("model") if isinstance(data.get("model"), dict) else {}
provider = section.get("provider") or data.get("provider") or ""
model = section.get("default") or section.get("model") or data.get("default_model") or data.get("model_name") or ""
raise SystemExit(0 if provider == sys.argv[1] and model == sys.argv[2] else 1)
' _ "$PROVIDER" "$MODEL"
      ;;
    credential-free-acceptance | post-reboot-credential-free)
      stage_exists "$stage" && "$ACCEPTANCE" --credential-free >/dev/null
      ;;
    provider-acceptance)
      provider=$(state_provider)
      model=$(state_model)
      stage_exists provider-acceptance \
        && "$ACCEPTANCE" --provider "$provider" --model "$model" --provider-required >/dev/null
      ;;
    inference-acceptance)
      provider=$(state_provider)
      model=$(state_model)
      stage_exists inference-acceptance \
        && "$ACCEPTANCE" --provider "$provider" --model "$model" \
          --provider-required --inference-required >/dev/null
      ;;
    reboot-verified)
      [[ -r "$STATE_DIR/boot-id-after-hermes-reboot" ]]
      ;;
    wrappers)
      [[ -x /usr/local/bin/hermes-chat && -x /usr/local/bin/hermes-status && -x /usr/local/bin/hermes-logs ]]
      ;;
    closed)
      [[ ! -e /usr/local/libexec/hermes-deploy-root && ! -e /usr/local/libexec/hermes-preflight ]] \
        && stage_exists wrappers
      ;;
    *) return 1 ;;
  esac
}

config_provider_model() {
  as_hermes podman exec -i --user 10000:10000 hermes python3 - <<'PY'
import pathlib
import yaml

data = yaml.safe_load(pathlib.Path('/opt/data/config.yaml').read_text(encoding='utf-8')) or {}
section = data.get('model') if isinstance(data.get('model'), dict) else {}
provider = section.get('provider') or data.get('provider') or ''
model = section.get('default') or section.get('model') or data.get('default_model') or data.get('model_name') or ''
print(f'provider={provider}')
print(f'model={model}')
PY
}

show_status() {
  local phase uid health image drift provider model provider_model config_provider config_model provider_auth
  local promotion_id machine_id host_fingerprint update_policy
  phase=$(read_state current-phase || true)
  uid=$(id -u hermes 2>/dev/null || true)
  health=$(as_hermes podman inspect hermes --format '{{.State.Health.Status}}' 2>/dev/null || true)
  image=$(as_hermes podman inspect hermes --format '{{.ImageName}}' 2>/dev/null || true)
  [[ -n "$phase" ]] || phase=not-started
  [[ -n "$uid" ]] || uid=absent
  [[ -n "$health" ]] || health=inactive
  [[ -n "$image" ]] || image=absent
  provider=$(state_provider)
  model=$(state_model)
  provider_model=$(config_provider_model 2>/dev/null || true)
  if [[ -n "$provider_model" ]]; then
    config_provider=$(sed -n 's/^provider=//p' <<<"$provider_model" | tail -n 1)
    config_model=$(sed -n 's/^model=//p' <<<"$provider_model" | tail -n 1)
    [[ -n "$config_provider" ]] && provider=$config_provider
    [[ -n "$config_model" ]] && model=$config_model
  fi
  if [[ -n "$provider" ]] && auth_status "$provider"; then
    provider_auth=ready
  else
    provider_auth=missing
  fi
  [[ -n "$provider" ]] || provider=unconfigured
  [[ -n "$model" ]] || model=unconfigured
  promotion_id=$(read_state promotion-id || true)
  [[ -n "$promotion_id" ]] || promotion_id=unconfigured
  machine_id=$(read_state host-machine-id-sha256 || true)
  [[ -n "$machine_id" ]] || machine_id=unbound
  host_fingerprint=$(read_state host-ssh-fingerprint || true)
  [[ -n "$host_fingerprint" ]] || host_fingerprint=unbound
  update_policy=download-only
  drift=none
  validate_stage runtime-credential-free || drift=detected
  if stage_exists inference-acceptance && [[ "$provider_auth" != ready ]]; then
    drift=detected
  fi
  printf 'phase=%s\n' "$phase"
  printf 'platform=%s\n' "${HERMES_SERVER_PLATFORM:-fedora-server-44}"
  printf 'host_machine_id_sha256=%s\n' "$machine_id"
  printf 'host_ssh_ed25519_fingerprint=%s\n' "$host_fingerprint"
  printf 'update_policy=%s\n' "$update_policy"
  printf 'promotion_id=%s\n' "$promotion_id"
  printf 'hermes_uid=%s\n' "$uid"
  printf 'service_health=%s\n' "$health"
  printf 'provider=%s\n' "$provider"
  printf 'model=%s\n' "$model"
  printf 'provider_auth=%s\n' "$provider_auth"
  printf 'image=%s\n' "$image"
  printf 'image_pin=%s\n' "$IMAGE_REF"
  printf 'drift=%s\n' "$drift"
  [[ "$drift" == none ]]
}

read -r ACTION || die 'missing helper action'
case "$ACTION" in
  status | validate | preflight | backup-present | host-identity) ;;
  *) ensure_state ;;
esac
case "$ACTION" in
  configure-site)
    IFS= read -r admin || die 'missing administrator account'
    IFS= read -r cidr || die 'missing management CIDR'
    IFS= read -r iface || die 'missing management interface'
    write_site "$admin" "$cidr" "$iface"
    ;;
  create-manifest) capture_manifest ;;
  backup-data)
    read_key_values
    backup_data
    ;;
  install-prerequisites) install_prerequisites ;;
  stage-update) stage_update ;;
  offline-pending) fedora_server_offline_update_pending ;;
  offline-reboot) fedora_server_reboot_for_offline_update ;;
  verify-no-update) fedora_server_verify_no_offline_update ;;
  verify-update) verify_update ;;
  host-policy) configure_host_policy ;;
  rollback-host) rollback_host_policy ;;
  identity) ensure_identity ;;
  install-runtime)
    UNIT_PATH=''
    RUNTIME_DROPIN_PATH=''
    VOLUME_DROPIN_PATH=''
    read_key_values
    install_runtime
    ;;
  install-runtime-helpers)
    ACCEPTANCE_PATH=''
    ROOT_ACCEPTANCE_PATH=''
    read_key_values
    install_runtime_helpers
    ;;
  apply-hardening)
    HARDEN_PATH=''
    read_key_values
    apply_hardening
    ;;
  set-model)
    MODEL_PATH=''
    PROVIDER=''
    MODEL=''
    read_key_values
    apply_model
    ;;
  preflight)
    MANAGEMENT_CIDR=''
    MANAGEMENT_INTERFACE=''
    ALLOW_UPDATE=0
    read_key_values
    [[ -x /usr/local/libexec/hermes-preflight ]] || die 'temporary preflight helper is missing'
    /usr/local/libexec/hermes-preflight "$MANAGEMENT_CIDR" "$MANAGEMENT_INTERFACE" "$ALLOW_UPDATE"
    ;;
  backup-present)
    backup_dir=$(read_state backup-dir || true)
    if [[ "$backup_dir" == "$STATE_DIR/backups/"* &&
      -s "$backup_dir/data.tgz.enc" && -s "$backup_dir/data.tgz.enc.sha256" ]]; then
      printf 'BACKUP_PRESENT\n'
    else
      printf 'BACKUP_ABSENT\n'
    fi
    ;;
  host-identity) host_identity ;;
  provider-auth)
    PROVIDER=''
    read_key_values
    run_provider_auth
    ;;
  validate-provider-auth)
    PROVIDER=''
    read_key_values
    validate_provider_auth
    printf 'VALID provider-auth provider=%s\n' "$PROVIDER"
    ;;
  validate-provider)
    PROVIDER=''
    MODEL=''
    read_key_values
    validate_provider
    printf 'VALID provider=%s model=%s\n' "$PROVIDER" "$MODEL"
    ;;
  reboot) reboot_host ;;
  verify-reboot) verify_hermes_reboot ;;
  acceptance)
    ACCEPTANCE_MODE=''
    ACCEPTANCE_PROVIDER=''
    ACCEPTANCE_MODEL=''
    read_key_values
    run_acceptance
    ;;
  root-acceptance)
    ROOT_ACCEPTANCE_PATH=''
    read_key_values
    if [[ -n "$ROOT_ACCEPTANCE_PATH" ]]; then
      check_artifact "$ROOT_ACCEPTANCE_PATH"
      "$ROOT_ACCEPTANCE_PATH"
    else
      "$ROOT_ACCEPTANCE"
    fi
    mark_stage root-acceptance
    ;;
  install-wrappers)
    CHAT_PATH=''
    STATUS_PATH=''
    LOGS_PATH=''
    read_key_values
    install_wrappers
    ;;
  close) close_deployment ;;
  prune-auth)
    ACTIVE_PROVIDER=''
    read_key_values
    prune_auth
    ;;
  remove-helper) remove_helper ;;
  rollback)
    PURGE=0
    RESTORE_DATA=0
    read_key_values
    rollback_deployment
    ;;
  revoke-auth)
    PROVIDER=''
    read_key_values
    revoke_auth
    ;;
  validate)
    IFS= read -r stage || die 'missing stage to validate'
    if validate_stage "$stage"; then
      printf 'VALID %s\n' "$stage"
    else
      printf 'DRIFT %s\n' "$stage" >&2
      exit 1
    fi
    ;;
  status) show_status ;;
  *)
    die 'unknown helper action'
    ;;
esac
