#!/bin/bash
# Configure standard Fedora Server SSH from its console. See setup-ssh-key-only.md.
set -Eeuo pipefail
shopt -s nullglob inherit_errexit

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}
usage() {
  cat <<'EOF'
Usage: sudo bash setup-ssh-key-only.sh --user USER --public-key-file FILE \
         --interface INTERFACE --zone ZONE [--dry-run]

Fedora Server, Bash 5+, console setup. Install one plain public key, require
key authentication, deny root SSH, allow port 22 in the explicit firewall zone.
Existing non-root account required. Never supply a private key.
--dry-run makes no changes; missing packages/inactive firewall defer live checks.
Keep console access until the separate workstation tests succeed.
EOF
}

parse_args() {
  user='' key_file='' iface='' zone='' dry_run=false
  while (($#)); do
    case "$1" in
      --help | -h)
        usage
        exit 0
        ;;
      --dry-run)
        dry_run=true
        shift
        ;;
      --user | --public-key-file | --interface | --zone)
        (($# >= 2)) && [[ -n $2 && $2 != --* ]] || fail "Missing value for $1"
        case "$1" in
          --user) user=$2 ;;
          --public-key-file) key_file=$2 ;;
          --interface) iface=$2 ;;
          --zone) zone=$2 ;;
        esac
        shift 2
        ;;
      *) fail "Unknown argument: $1" ;;
    esac
  done
  [[ $user =~ ^[a-zA-Z_][a-zA-Z0-9_.-]*\$?$ ]] || fail 'Specify --user'
  [[ -n $key_file ]] || fail 'Specify --public-key-file'
  [[ $iface =~ ^[a-zA-Z0-9_.:-]+$ && $zone =~ ^[a-zA-Z0-9_-]+$ ]] || fail 'Specify valid --interface and --zone'
}

read_key() {
  [[ -f $key_file && -r $key_file ]] || fail 'Public-key file is not readable'
  (($(stat -c %s -- "$key_file") <= 16384)) || fail 'Public-key file is too large'
  key=$(cat -- "$key_file")
  [[ $key != *$'\n'* && $key != *$'\r'* ]] || fail 'Supply exactly one public-key line'
  read -r key_type key_blob _ <<<"$key"
  case "$key_type" in
    ssh-ed25519 | ssh-rsa | ecdsa-sha2-nistp256 | ecdsa-sha2-nistp384 | ecdsa-sha2-nistp521 | sk-ssh-ed25519@openssh.com | sk-ecdsa-sha2-nistp256@openssh.com) ;;
    *) fail 'Expected a plain OpenSSH public key, without options; private keys are forbidden' ;;
  esac
  ssh-keygen -lf <(printf '%s\n' "$key") >/dev/null 2>&1 || fail 'Invalid public key'
}

safe_path() {
  local path=$1 current=/ part
  [[ $path == /* && $path != *'/../'* && $path != *'/./'* ]] || fail 'Unsafe destination path'
  local -a parts
  IFS=/ read -ra parts <<<"$path"
  for part in "${parts[@]}"; do
    [[ -n $part ]] || continue
    current=${current%/}/$part
    [[ ! -L $current ]] || fail "Destination symlink refused: $current"
  done
  if [[ -e $path && ! -d $path ]]; then
    [[ -f $path && $(stat -c %h -- "$path") == 1 ]] || fail 'Destination must be a regular, singly linked file'
  fi
}

inspect_crypto_path() {
  local resolved current
  local expected_owner=0
  if [[ ! -L $crypto ]]; then
    safe_path "$crypto"
    return
  fi
  # This input is never modified. Fedora ships DEFAULT policy as this symlink.
  safe_path "${crypto%/*}"
  resolved=$(readlink -e -- "$crypto") || fail 'Unresolvable crypto-policy symlink'
  [[ $resolved == /usr/share/crypto-policies/DEFAULT/opensshserver.txt && $(readlink -- "$crypto") == "$resolved" ]] \
    || fail 'Unreviewed crypto-policy symlink target'
  safe_path "${resolved%/*}"
  [[ -f $resolved && ! -L $resolved ]] || fail 'Crypto-policy target must be a regular file'
  [[ $(stat -c %u -- "$crypto") == "$expected_owner" ]] || fail 'Crypto-policy link must be root-owned'
  for current in "$resolved" "${crypto%/*}"; do
    while :; do
      [[ $(stat -c %u -- "$current") == "$expected_owner" ]] || fail 'Crypto-policy path must be root-owned'
      (((8#$(stat -c %a -- "$current") & 8#022) == 0)) || fail 'Crypto-policy path must not be group/world writable'
      [[ $current != / ]] || break
      current=${current%/*}
      [[ -n $current ]] || current=/
    done
  done
}

inspect_config() {
  local file line directive rest
  [[ -f $config ]] || fail 'Missing standard sshd_config'
  local -a files=("$config" "$confdir"/*.conf)
  if [[ -e $crypto || -L $crypto ]]; then files+=("$crypto"); fi
  for file in "${files[@]}"; do
    if [[ $file == "$crypto" ]]; then inspect_crypto_path; else safe_path "$file"; fi
    while IFS= read -r line || [[ -n $line ]]; do
      line=${line%%#*}
      read -r directive rest <<<"${line/=/ }"
      case "${directive,,}" in
        match) fail 'Conditional Match configuration is unsupported; review manually' ;;
        include)
          [[ $file == "$config" && $rest == "$confdir/*.conf" ]] \
            || [[ ($file == "$confdir/50-redhat.conf" || $file == "$confdir/40-redhat-crypto-policies.conf") && $rest == "$crypto" ]] \
            || fail 'Nonstandard Include requires manual review'
          ;;
      esac
    done <"$file"
  done
}

key_only_settings() {
  cat <<'EOF'
PubkeyAuthentication yes
AuthenticationMethods publickey
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
EOF
}

candidate_config() {
  local line directive rest file
  while IFS= read -r line || [[ -n $line ]]; do
    read -r directive rest <<<"${line/=/ }"
    if [[ ${directive,,} == include && ${rest%%#*} == "$confdir/*.conf" ]]; then
      while IFS= read -r file; do
        if [[ $file == "$dropin" ]]; then
          key_only_settings
        else
          cat -- "$file"
          printf '\n'
        fi
      done < <(printf '%s\n' "$dropin" "$confdir"/*.conf | sort -u)
    else printf '%s\n' "$line"; fi
  done <"$config"
}

effective_check() {
  local values name value
  if [[ ${1:-} == candidate ]]; then
    values=$("$sshd" -T -f /dev/stdin < <(candidate_config))
  else
    "$sshd" -t
    values=$("$sshd" -T)
  fi
  while read -r name value; do
    grep -qxF "$name $value" <<<"$values" || fail "Effective SSH conflict: $name"
  done <<'EOF'
pubkeyauthentication yes
authenticationmethods publickey
passwordauthentication no
kbdinteractiveauthentication no
permitrootlogin no
port 22
EOF
  [[ $(grep -c '^port ' <<<"$values") == 1 ]] || fail 'Only standard port 22 is supported'
  grep -Eq '^authorizedkeysfile (\.ssh/authorized_keys|%h/\.ssh/authorized_keys)( |$)' <<<"$values" \
    || fail 'Nonstandard AuthorizedKeysFile requires manual review'
}

service_snapshot() {
  local svc=$1 enabled active
  enabled=$(systemctl is-enabled "$svc" 2>/dev/null) || :
  active=$(systemctl is-active "$svc" 2>/dev/null) || :
  case "$enabled" in enabled | disabled | not-found | '') ;; *) fail "Unsupported $svc enablement state" ;; esac
  case "$active" in active | inactive | unknown | '') ;; *) fail "Unsupported $svc activity state" ;; esac
  old_enabled[$svc]=$enabled
  old_active[$svc]=$active
}

standard_ipv6_policy() {
  local scope=$1 actual expected
  local -a args=(--policy=allow-host-ipv6)
  [[ $scope != permanent ]] || args+=(--permanent)
  actual=$(firewall-cmd "${args[@]}" --list-all)
  # Ignore presentation (heading and whitespace), compare every effective field.
  actual=$(sed '1d;s/^[[:space:]]*//;s/[[:space:]]*$//;/^disable: no$/d' <<<"$actual" | sort)
  expected=$(
    cat <<'EOF' | sort
priority: -15000
target: CONTINUE
ingress-zones: ANY
egress-zones: HOST
services:
ports:
protocols:
masquerade: no
forward-ports:
source-ports:
icmp-blocks:
rich rules:
rule family="ipv6" icmp-type name="neighbour-advertisement" accept
rule family="ipv6" icmp-type name="neighbour-solicitation" accept
rule family="ipv6" icmp-type name="router-advertisement" accept
rule family="ipv6" icmp-type name="redirect" accept
rule family="ipv6" icmp-type name="mld-listener-done" accept
rule family="ipv6" icmp-type name="mld-listener-query" accept
rule family="ipv6" icmp-type name="mld-listener-report" accept
rule family="ipv6" icmp-type name="mld2-listener-report" accept
EOF
  )
  [[ $actual == "$expected" ]] || fail 'Modified IPv6 policy requires manual review'
}

firewall_check() {
  local scope z sources rules policies ports actual
  for scope in runtime permanent; do
    local -a args=()
    [[ $scope != permanent ]] || args+=(--permanent)
    if [[ $scope == runtime ]]; then
      actual=$(firewall-cmd --get-zone-of-interface="$iface")
      [[ $actual == "$zone" ]] || fail 'Interface/zone mismatch in runtime configuration'
    fi
    # NetworkManager stores the persistent assignment in its connection profile,
    # not necessarily in firewalld's permanent interface list.
    if [[ $scope == permanent ]]; then
      local query_rc=0
      actual=$(firewall-cmd --permanent --get-zone-of-interface="$iface" 2>&1) || query_rc=$?
      if ((query_rc != 0)); then
        [[ ($query_rc == 1 || $query_rc == 2) && $actual == 'no zone' ]] \
          || fail 'Cannot read permanent interface assignment'
      fi
      if [[ -z $actual || $actual == 'no zone' ]]; then
        local connection
        connection=$(nmcli -g GENERAL.CON-UUID device show "$iface")
        [[ -n $connection && $connection != -- ]] || fail 'Cannot verify persistent management connection'
        actual=$(nmcli -g connection.zone connection show "$connection")
        if [[ -z $actual ]]; then actual=$(firewall-cmd --get-default-zone); fi
      fi
      [[ $actual == "$zone" ]] || fail 'Interface/zone mismatch in persistent configuration'
    fi
    # Source zones and custom rules may take precedence over interface assignment.
    for z in $(firewall-cmd "${args[@]}" --get-zones); do
      sources=$(firewall-cmd "${args[@]}" --zone="$z" --list-sources)
      [[ -z $sources ]] || fail 'Source-based zones require manual review'
    done
    rules=$(firewall-cmd "${args[@]}" --zone="$zone" --list-rich-rules)
    ports=$(firewall-cmd "${args[@]}" --zone="$zone" --list-ports)
    [[ -z $rules && -z $ports ]] || fail 'Custom zone rules/ports require manual review'
    rules=$(firewall-cmd "${args[@]}" --direct --get-all-rules)
    [[ -z $rules ]] || fail 'Direct firewall rules require manual review'
    policies=$(firewall-cmd "${args[@]}" --get-policies)
    local policy
    for policy in $policies; do
      case "$policy" in
        allow-host-ipv6) standard_ipv6_policy "$scope" ;;
        gateway-dmz-to-HOST | gateway-lan-to-HOST | gateway-lan-to-work | gateway-lan-to-world | gateway-world-to-HOST)
          # Shipped policy-set templates have no effect while explicitly disabled.
          firewall-cmd "${args[@]}" --policy="$policy" --query-disable >/dev/null \
            || fail 'Enabled or unreadable gateway policy requires manual review'
          ;;
        *) fail 'Firewall policies require manual review' ;;
      esac
    done
    ports=$(firewall-cmd "${args[@]}" --info-service=ssh)
    ports=$(sed '1d;s/^[[:space:]]*//;s/[[:space:]]*$//' <<<"$ports" | sort)
    [[ $ports == $'destination:\nhelpers:\nincludes:\nmodules:\nports: 22/tcp\nprotocols:\nsource-ports:' ]] \
      || fail 'Nonstandard firewalld SSH service'
  done
}

allowance() {
  local rc=0
  firewall-cmd "$@" --zone="$zone" --query-service=ssh >/dev/null || rc=$?
  case $rc in 0) printf yes ;; 1) printf no ;; *) fail 'Cannot read firewall allowance' ;; esac
}

install_key() {
  safe_path "$sshdir"
  safe_path "$authorized"
  [[ ! -e $sshdir || -d $sshdir ]] || fail '.ssh is not a directory'
  mkdir -p -- "$sshdir"
  chmod 700 -- "$sshdir"
  chown "$uid:$gid" -- "$sshdir"
  touch -- "$authorized"
  chmod 600 -- "$authorized"
  chown "$uid:$gid" -- "$authorized"
  # Find the key's type/blob pair even after restrictions. Never add an unrestricted
  # copy of a restricted existing key. Comments do not constitute installed keys.
  if ! awk -v type="$key_type" -v blob="$key_blob" '
    /^[[:space:]]*#/ {next}
    {for (i=1; i<NF; i++) if ($i==type && $(i+1)==blob) found=1}
    END {exit !found}' "$authorized"; then
    if [[ -s $authorized && $(tail -c 1 -- "$authorized" | od -An -tu1 | tr -d '[:space:]') != 10 ]]; then
      printf '\n' >>"$authorized"
    fi
    printf '%s\n' "$key" >>"$authorized"
  fi
  restorecon -F -- "$sshdir" "$authorized"
}

restore_service() {
  local svc=$1
  if [[ ${old_active[$svc]} == active ]]; then
    systemctl start "$svc" || return
    [[ $svc != sshd ]] || systemctl reload sshd || return
  else
    systemctl stop "$svc" || return
  fi
  if [[ ${old_enabled[$svc]} == enabled ]]; then
    systemctl enable "$svc"
  else
    systemctl disable "$svc"
  fi
}

rollback() {
  local rc=$? failed=false scope
  trap - EXIT INT TERM HUP
  set +e
  if [[ $rc != 0 ]]; then
    printf 'Configuration failed; restoring managed state.\n' >&2
    if $files_touched; then
      if [[ -f $backup/dropin ]]; then
        cp -a -- "$backup/dropin" "$dropin" || failed=true
      else rm -f -- "$dropin" || failed=true; fi
      if [[ -f $backup/authorized ]]; then
        cp -a -- "$backup/authorized" "$authorized" || failed=true
      else rm -f -- "$authorized" || failed=true; fi
      if $had_sshdir; then
        chmod "$dir_mode" -- "$sshdir" || failed=true
        chown "$dir_owner" -- "$sshdir" || failed=true
        if [[ $dir_context != '?' ]]; then chcon "$dir_context" -- "$sshdir" || failed=true; fi
      else rmdir -- "$sshdir" || failed=true; fi
    fi
    if $firewall_touched; then
      for scope in runtime permanent; do
        local -a args=()
        [[ $scope != permanent ]] || args+=(--permanent)
        if [[ ${old_allow[$scope]} == no ]]; then
          firewall-cmd "${args[@]}" --zone="$zone" --remove-service=ssh >/dev/null || failed=true
        fi
      done
    fi
    if $services_touched; then
      restore_service sshd || failed=true
      restore_service firewalld || failed=true
    fi
    printf 'Package installations and any newly generated host keys remain.\n' >&2
    printf 'Recovery files retained outside sshd includes: %s\n' "$backup" >&2
    $failed && printf 'ERROR: Restoration incomplete; use the console and recovery files.\n' >&2
  else
    rm -rf -- "$backup"
  fi
  exit "$rc"
}

apply_config() {
  backup=$(mktemp -d /var/tmp/ssh-key-only.XXXXXXXX)
  chmod 700 "$backup"
  files_touched=false firewall_touched=false services_touched=false
  trap rollback EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  trap 'exit 129' HUP
  declare -p old_enabled old_active >"$backup/state"
  # Package and host-key creation are deliberately not reversed.
  services_touched=true
  dnf install -y openssh-server openssh-clients firewalld policycoreutils
  inspect_config
  systemctl enable --now firewalld
  firewall_check
  old_allow[runtime]=$(allowance)
  old_allow[permanent]=$(allowance --permanent)
  declare -p old_allow >>"$backup/state"
  safe_path "$dropin"
  [[ ! -d $dropin ]] || fail 'Drop-in destination is a directory'
  [[ ! -e $dropin ]] || cp -a -- "$dropin" "$backup/dropin"
  [[ ! -e $authorized ]] || cp -a -- "$authorized" "$backup/authorized"
  had_sshdir=false
  if [[ -d $sshdir ]]; then
    had_sshdir=true
    dir_mode=$(stat -c %a -- "$sshdir")
    dir_owner=$(stat -c %u:%g -- "$sshdir")
    dir_context='?'
    if selinuxenabled; then dir_context=$(stat -c %C -- "$sshdir"); fi
    declare -p dir_mode dir_owner dir_context >>"$backup/state"
  fi
  files_touched=true
  install_key
  key_only_settings >"$dropin"
  chown root:root "$dropin"
  chmod 644 "$dropin"
  restorecon -F "$dropin"
  ssh-keygen -A
  effective_check
  firewall_touched=true
  firewall-cmd --zone="$zone" --add-service=ssh >/dev/null
  firewall-cmd --permanent --zone="$zone" --add-service=ssh >/dev/null
  [[ $(allowance) == yes && $(allowance --permanent) == yes ]] || fail 'Firewall verification failed'
  systemctl enable sshd
  if [[ ${old_active[sshd]} == active ]]; then
    systemctl reload sshd
  else systemctl start sshd; fi
  systemctl is-active --quiet sshd
  systemctl is-enabled --quiet sshd
  printf 'Local configuration validation passed. Remote access remains UNVERIFIED.\n'
  printf 'Console host identity: ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub\n'
  printf 'Workstation (replace SERVER_IP and key path):\n'
  printf 'ssh -o ControlPath=none -o IdentitiesOnly=yes -o PreferredAuthentications=publickey -i ~/.ssh/id_ed25519_fedora %s@SERVER_IP\n' "$user"
  printf 'ssh -o ControlPath=none -o PubkeyAuthentication=no -o PreferredAuthentications=password,keyboard-interactive %s@SERVER_IP\n' "$user"
}

inspect_service_overrides() {
  local paths content
  paths=$(systemctl show sshd --property=DropInPaths --value) || fail 'Cannot inspect sshd service overrides'
  [[ -n $paths ]] || return 0
  # Fedora's inherited timeout policy does not change SSH startup or authentication.
  # Accept the reviewed contents, not merely a familiar filename.
  [[ $paths == /usr/lib/systemd/system/service.d/10-timeout-abort.conf ]] || fail 'sshd service overrides require manual review'
  [[ -f $paths && -r $paths && ! -L $paths ]] || fail 'sshd timeout override requires manual review'
  content=$(awk '
    /^[[:space:]]*([#;]|$)/ { next }
    { sub(/^[[:space:]]+/, ""); sub(/[[:space:]]+$/, ""); print }
  ' "$paths") || fail 'Cannot read sshd timeout override'
  [[ $content == $'[Service]\nTimeoutStopFailureMode=abort' ]] || fail 'sshd timeout override requires manual review'
}

inspect_service_environment() {
  local file=/etc/sysconfig/sshd
  [[ -e $file || -L $file ]] || return 0
  [[ -f $file && -r $file && ! -L $file ]] || fail 'sshd environment file requires manual review'
  # Parse a narrow set of inert assignments; never source an environment file.
  awk -v quote="'" '
    /^[[:space:]]*([#;]|$)/ { next }
    { sub(/^[[:space:]]+/, ""); sub(/[[:space:]]+$/, "") }
    $0 == "OPTIONS=" || $0 == "OPTIONS=\"\"" || $0 == "OPTIONS=" quote quote { next }
    { exit 1 }
  ' "$file" || fail 'Active /etc/sysconfig/sshd settings require manual review'
}

main() {
  ((BASH_VERSINFO[0] >= 5)) || fail 'Bash 5+ required'
  parse_args "$@"
  [[ $EUID == 0 ]] || fail 'Run from the server console with sudo'
  export PATH=/usr/sbin:/usr/bin:/sbin:/bin LC_ALL=C
  umask 077
  [[ -f /etc/fedora-release && ! -e /run/ostree-booted ]] || fail 'Standard Fedora Server with DNF required'
  [[ -z ${SSH_CONNECTION:-}${SSH_TTY:-} ]] || fail 'Use the server console for initial configuration'
  config=/etc/ssh/sshd_config confdir=/etc/ssh/sshd_config.d
  crypto=/etc/crypto-policies/back-ends/opensshserver.config
  dropin=$confdir/00-local-key-only.conf sshd=/usr/sbin/sshd
  local account shell
  account=$(getent passwd "$user") || fail 'Account does not exist'
  IFS=: read -r _ _ uid gid _ home shell <<<"$account"
  [[ $uid != 0 && -d $home && -x $shell && $shell != */nologin && $shell != */false ]] || fail 'Require a non-root login account'
  [[ $(stat -c %u "$home") == "$uid" ]] || fail 'Home must belong to the selected account'
  (((8#$(stat -c %a "$home") & 8#022) == 0)) || fail 'Home must not be group/world writable'
  sshdir=$home/.ssh authorized=$home/.ssh/authorized_keys
  safe_path "$authorized"
  [[ ! -d $authorized ]] || fail 'authorized_keys is a directory'
  command -v ssh-keygen >/dev/null || fail 'Install openssh-clients at the console to validate the public key first'
  read_key
  ip link show dev "$iface" >/dev/null || fail 'Interface does not exist'
  declare -gA old_enabled=() old_active=() old_allow=()
  service_snapshot sshd
  service_snapshot firewalld
  if systemctl is-active --quiet sshd.socket || systemctl is-enabled --quiet sshd.socket 2>/dev/null; then
    fail 'Socket-activated SSH requires manual review'
  fi
  inspect_service_overrides
  local fragment
  fragment=$(systemctl show sshd --property=FragmentPath --value)
  [[ -z $fragment || $fragment == /usr/lib/systemd/system/sshd.service ]] || fail 'Nonstandard sshd service requires manual review'
  inspect_service_environment
  [[ ! -e $config ]] || inspect_config
  if [[ ${old_active[firewalld]} == active ]]; then firewall_check; fi
  if $dry_run; then
    if [[ -x $sshd && -f $config ]]; then effective_check candidate; fi
    printf 'DRY RUN: no changes made. Would install packages/key/drop-in, validate, allow SSH in %s on %s, and enable/reload sshd.\n' "$zone" "$iface"
    printf 'Missing-package and inactive-firewall checks are deferred to apply. Remote access is UNVERIFIED.\n'
    return
  fi
  apply_config
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main "$@"; fi
