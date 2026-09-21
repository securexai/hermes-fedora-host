#!/usr/bin/env bash
# M01: read-only baseline and precondition inventory for the manual profile.
#
# This helper never mutates anything and takes no --apply. Its purpose is to record
# what the host actually is before any deployment, and to fail when a precondition
# the profile depends on is absent.
#
# Run as root on the Hermes host:
#   sudo bash ~/hermes-manual/m01-baseline.sh
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
ADMIN_ACCOUNT=$(mp_admin_account)
ADMIN_HOME=$(mp_admin_home)
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m01-baseline.out")
BASELINE="$ADMIN_HOME/hermes-m01-baseline.json"
RUNTIME_ACCOUNT="${HERMES_RUNTIME:-hermes}"
RUNTIME_HOME=$(getent passwd "$RUNTIME_ACCOUNT" 2>/dev/null | cut -d: -f6)

rc=0
{
  echo "### M01 baseline inventory (read-only)"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  echo "===== platform ====="
  os_id=$( (. /etc/os-release && printf '%s' "$ID"))
  os_ver=$( (. /etc/os-release && printf '%s' "$VERSION_ID"))
  os_pretty=$( (. /etc/os-release && printf '%s' "$PRETTY_NAME"))
  arch=$(uname -m)
  kernel=$(uname -r)
  echo "BASELINE os_id=$os_id"
  echo "BASELINE os_version=$os_ver"
  echo "BASELINE os_pretty=$os_pretty"
  echo "BASELINE arch=$arch"
  echo "BASELINE kernel=$kernel"
  echo "BASELINE machine_id_sha256=$(mp_host_identity_sha256)"
  echo "BASELINE hostname=$(hostnamectl --static 2>/dev/null || hostname)"
  mp_check fedora_44 "$([ "$os_id" = fedora ] && [ "$os_ver" = 44 ] && echo PASS || echo FAIL)"
  mp_check arch_x86_64 "$([ "$arch" = x86_64 ] && echo PASS || echo FAIL)"
  echo

  echo "===== kernel and cgroup ====="
  cgroup_fs=$(stat -fc %T /sys/fs/cgroup 2>/dev/null || echo unknown)
  echo "BASELINE cgroup_fs=$cgroup_fs"
  mp_check cgroup_v2 "$([ "$cgroup_fs" = cgroup2fs ] && echo PASS || echo FAIL)"
  echo

  echo "===== security posture ====="
  selinux=$(getenforce 2>/dev/null || echo unknown)
  echo "BASELINE selinux=$selinux"
  mp_check selinux_enforcing "$([ "$selinux" = Enforcing ] && echo PASS || echo FAIL)"
  if command -v mokutil >/dev/null 2>&1; then
    sb=$(mokutil --sb-state 2>&1 || true)
    echo "BASELINE secureboot=$sb"
    if [[ "$sb" == *"SecureBoot enabled"* ]]; then
      mp_check secure_boot PASS
    else
      mp_check secure_boot FAIL "$sb"
    fi
  else
    echo "BASELINE secureboot=mokutil-absent"
    mp_check secure_boot UNVERIFIED "mokutil is not installed"
  fi
  echo

  echo "===== storage and the required dedicated filesystem ====="
  findmnt --mountpoint /home/hermes >/dev/null 2>&1 \
    && mp_check home_hermes_is_mount PASS \
    || mp_check home_hermes_is_mount FAIL "every manual helper aborts unless /home/hermes is its own mount"
  findmnt -no SOURCE,FSTYPE,SIZE,OPTIONS --target /home/hermes 2>/dev/null | sed 's/^/  home_hermes: /' || echo "  home_hermes: not mounted"
  echo "BASELINE root_source=$(findmnt -no SOURCE --target /)"
  echo "BASELINE root_fstype=$(findmnt -no FSTYPE --target /)"
  root_avail_gib=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
  echo "BASELINE root_avail_gib=$root_avail_gib"
  mp_check root_free_space "$([ "${root_avail_gib:-0}" -ge 5 ] && echo PASS || echo FAIL)" "${root_avail_gib}GiB available (floor 5GiB)"

  # Encryption is deliberately absent on this fixture (plan deviation D-01). A missing
  # LUKS layer is the authorized state here, so it is NOT_APPLICABLE rather than FAIL.
  if lsblk -s -o NAME,TYPE "$(findmnt -no SOURCE --target /)" 2>/dev/null | grep -q crypt; then
    echo "BASELINE encryption=luks"
    if command -v cryptsetup >/dev/null 2>&1; then
      luks_dev=$(lsblk --raw -no NAME,TYPE -s "$(findmnt -no SOURCE --target /)" 2>/dev/null | awk '$2=="crypt" {print "/dev/"$1; exit}')
      echo "BASELINE luks_device=$luks_dev"
      echo "  keyslots=$(cryptsetup luksDump "$luks_dev" 2>/dev/null | grep -cE '^  [0-9]+: luks2' || true)"
      mp_check encryption_state PASS "LUKS present"
    else
      mp_check encryption_state UNVERIFIED "LUKS present but cryptsetup is not installed"
    fi
  else
    echo "BASELINE encryption=none"
    mp_check encryption_state NOT_APPLICABLE "plan deviation D-01: this fixture is deliberately unencrypted"
  fi
  echo

  echo "===== time synchronization ====="
  ntp=$(timedatectl show -p NTPSynchronized --value 2>/dev/null || echo unknown)
  echo "BASELINE ntp_synchronized=$ntp"
  mp_check time_synchronized "$([ "$ntp" = yes ] && echo PASS || echo FAIL)"
  echo

  echo "===== administrator account ====="
  if id -u "$ADMIN_ACCOUNT" >/dev/null 2>&1; then
    echo "BASELINE admin_account=$ADMIN_ACCOUNT"
    echo "BASELINE admin_home=$ADMIN_HOME"
    echo "  groups=$(id -nG "$ADMIN_ACCOUNT" | tr ' ' ',')"
    mp_check admin_in_wheel "$(id -nG "$ADMIN_ACCOUNT" | tr ' ' '\n' | grep -qx wheel && echo PASS || echo FAIL)"
  else
    mp_check admin_account FAIL "$ADMIN_ACCOUNT does not exist"
  fi
  echo

  echo "===== runtime account (created later by m01-host-prepare) ====="
  if id -u "$RUNTIME_ACCOUNT" >/dev/null 2>&1; then
    echo "BASELINE runtime_account=$RUNTIME_ACCOUNT uid=$(id -u "$RUNTIME_ACCOUNT")"
    echo "BASELINE runtime_shell=$(getent passwd "$RUNTIME_ACCOUNT" | cut -d: -f7)"
    echo "BASELINE runtime_home=$RUNTIME_HOME"
    echo "  subuid=$(grep "^${RUNTIME_ACCOUNT}:" /etc/subuid 2>/dev/null | cut -d: -f2- || echo none)"
    echo "  subgid=$(grep "^${RUNTIME_ACCOUNT}:" /etc/subgid 2>/dev/null | cut -d: -f2- || echo none)"
  else
    echo "BASELINE runtime_account=absent (expected before host preparation)"
  fi
  echo

  echo "===== networking and firewall ====="
  iface=$(ip -o -4 route show default 2>/dev/null | awk '{print $5}' | head -n1)
  addr=$(ip -o -4 addr show "${iface:-lo}" 2>/dev/null | awk '{print $4}' | head -n1)
  echo "BASELINE primary_interface=${iface:-none}"
  echo "BASELINE primary_address=${addr:-none}"
  if command -v firewall-cmd >/dev/null 2>&1; then
    zone=$(firewall-cmd --get-zone-of-interface="${iface:-link}" 2>/dev/null | head -n1)
    [ -n "$zone" ] || zone=$(firewall-cmd --get-default-zone 2>/dev/null | head -n1)
    zone=${zone%% *}
    echo "BASELINE firewalld_active=$(firewall-cmd --state 2>/dev/null || echo unknown)"
    echo "BASELINE firewall_zone=${zone:-none}"
    mp_check firewalld_active "$([ "$(firewall-cmd --state 2>/dev/null || echo down)" = running ] && echo PASS || echo FAIL)"
  else
    mp_check firewalld_active FAIL "firewall-cmd is not installed"
  fi
  echo

  echo "===== tooling presence (installed by m01-host-prepare) ====="
  for tool in podman skopeo sshd restorecon ausearch; do
    printf '  %-10s %s\n' "$tool" "$(command -v "$tool" >/dev/null 2>&1 && echo present || echo absent)"
  done
  echo "===== done ====="
} 2>&1 | tee "$OUT" || rc=$?

# Sanitized machine-readable extract; no secrets are involved in this inventory.
python3 - "$OUT" "$BASELINE" <<'PY' || true
import json, re, sys
log, out = sys.argv[1], sys.argv[2]
data = {}
for line in open(log, encoding="utf-8", errors="replace"):
    m = re.match(r"^BASELINE ([a-z0-9_]+)=(.*)$", line.strip())
    if m:
        data[m.group(1)] = m.group(2)
data["checks"] = re.findall(r"^CHECK ([A-Za-z0-9_.-]+)=(\S+)", open(log, encoding="utf-8", errors="replace").read(), re.M)
with open(out, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, sort_keys=True)
print(f"wrote {out}", file=sys.stderr)
PY
chmod 0644 "$BASELINE" 2>/dev/null || true
chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
echo "WROTE=$OUT"
echo "BASELINE_JSON=$BASELINE"
mp_finalize "$OUT" "${rc:-0}"
