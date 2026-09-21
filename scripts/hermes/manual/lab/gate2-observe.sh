#!/usr/bin/env bash
# Collect an observation bundle for the Gate 2 fixture, as root.
#
# Exists because unprivileged libvirt access on this host is intermittently denied by
# polkit (measured: 2 failures in 10 attempts over 30 s, with an active seat0 session and
# healthy virtqemud). Diagnosis therefore runs as root through the temporary grant, which
# does not involve polkit at all, instead of retrying an unreliable path.
#
# Installed as /usr/local/libexec/hermes-gate2/ and granted through the temporary sudoers
# drop-in. Takes NO arguments. Writes world-readable output so the agent can read it
# without any privilege.
set -euo pipefail
export LC_ALL=C

DOMAIN=lab-hermes-manual-r1
URI=qemu:///system
OUTDIR=/var/lib/hermes-gate2/observe
KEEP=20

[ "$(id -u)" -eq 0 ] || {
  printf 'STOP: must run as root\n' >&2
  exit 1
}
install -d -m 0755 "$OUTDIR"
ts=$(date -u +%Y%m%dT%H%M%SZ)
bundle="$OUTDIR/observe-$ts.txt"
png="$OUTDIR/console-$ts.png"

guest_ip() {
  virsh -c "$URI" net-dhcp-leases fvh-nat 2>/dev/null | awk '/ipv4/ {print $5}' | cut -d/ -f1 | head -n1
}

{
  echo "observed_utc=$ts"
  echo
  echo "--- domains ---"
  virsh -c "$URI" list --all 2>&1
  echo
  echo "--- domain info ---"
  virsh -c "$URI" dominfo "$DOMAIN" 2>&1 | grep -E 'Name|State|CPU\(s\)|Max memory|CPU time|Autostart' || true
  echo
  echo "--- optical and disk media ---"
  virsh -c "$URI" domblklist "$DOMAIN" 2>&1
  echo
  echo "--- vda allocation (install progress) ---"
  virsh -c "$URI" domblkinfo "$DOMAIN" vda 2>&1 | grep -E 'Capacity|Allocation' || true
  echo
  echo "--- dhcp lease ---"
  virsh -c "$URI" net-dhcp-leases fvh-nat 2>&1
  ip=$(guest_ip || true)
  echo "guest_ip=${ip:-none}"
  if [ -n "${ip:-}" ]; then
    if timeout 5 bash -c "exec 3<>/dev/tcp/$ip/22" 2>/dev/null; then
      echo "ssh_port=open"
    else
      echo "ssh_port=closed_or_filtered"
    fi
  fi
} >"$bundle" 2>&1

virsh -c "$URI" screenshot "$DOMAIN" "$png" >>"$bundle" 2>&1 || true
chmod 0644 "$bundle" 2>/dev/null || true
[ -e "$png" ] && chmod 0644 "$png" 2>/dev/null || true

# Prune this wrapper's own old outputs only.
ls -1t "$OUTDIR"/observe-*.txt 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f
ls -1t "$OUTDIR"/console-*.png 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f

printf 'bundle=%s\npng=%s\n' "$bundle" "$png"
