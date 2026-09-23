#!/usr/bin/env bash
# Policy installation only; operator approval and repair-guide preflight are required.
set -euo pipefail
umask 077
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
module_hash=1ce86147143ac668910e5136e89e54f69a9f1d62a55073a0c5d1b37406372a5a
base_hash=bf58d5f5ae23502d844f70c153ef5366c31bf16ac9c77f548b94f3cf1aea1949
merged_hash=67d4f87afb2df3137fb8ab81f8f260942c3b43238bb275d16826b6c7a2ede8c0
exe=/usr/lib/systemd/systemd-tpm2-setup
policy=/etc/selinux/targeted/policy/policy.35
backup=/var/lib/hermes-selinux-trial-20260909
fail() {
  printf '%s\n' "$*" >&2
  exit 1
}
hash_is() { [[ $(sha256sum -- "$1" | cut -d ' ' -f 1) == "$2" ]]; }
[[ $# == 2 && $1 == --approved-policy-install ]] || {
  printf '%s\n' 'Usage: bash install-reviewed-candidate.sh --approved-policy-install /absolute/candidate.pp' >&2
  exit 64
}
[[ $2 == /* && -f $2 && ! -L $2 ]] || fail 'Expected an absolute regular module path.'
hash_is "$2" "$module_hash" || fail 'Module hash mismatch; no changes made.'
[[ $EUID == 0 ]] || fail 'Operator sudo required after explicit approval and guide preflight.'
[[ $(hostname -s) == hermes ]] || fail 'Unexpected host.'
[[ $(getenforce) == Enforcing ]] || fail 'SELinux must be Enforcing.'
[[ $(rpm -q --qf '%{VERSION}-%{RELEASE}' selinux-policy-targeted) == 44.8-1.fc44 ]] || fail 'Policy package drift.'
[[ $(rpm -q --qf '%{VERSION}-%{RELEASE}' selinux-policy) == 44.8-1.fc44 ]] || fail 'Policy package drift.'
[[ $(rpm -q --qf '%{VERSION}-%{RELEASE}' systemd) == 259.8-1.fc44 ]] || fail 'systemd package drift.'
hash_is "$policy" "$base_hash" || fail 'Policy baseline drift or already installed; stop for review.'
[[ $(stat -c %C "$exe") == system_u:object_r:init_exec_t:s0 ]] || fail 'Executable label drift.'
[[ $(matchpathcon -n "$exe") == system_u:object_r:init_exec_t:s0 ]] || fail 'Executable mapping drift.'
modules=$(semodule -lfull)
if [[ $modules == *hermes_tpm2_setup* ]]; then fail 'Candidate module already exists; stop for review.'; fi
for unit in systemd-tpm2-setup.service systemd-tpm2-setup-early.service; do
  state=$(systemctl show -p ActiveState --value "$unit")
  [[ $state == inactive || $state == failed || $state == active ]] || fail 'Setup service is transitioning.'
  [[ $(systemctl show -p MainPID --value "$unit") == 0 ]] || fail 'Setup process is running.'
done
# Exclusive root-private backup; never overwrite an earlier trial.
mkdir -m 0700 "$backup"
printf '%s\n' "$modules" >"$backup/modules.before"
tar -C /var/lib/selinux -czf "$backup/targeted-active.tar.gz" targeted/active
cp --preserve=mode -- "$policy" "$backup/policy.before"
stat -c %C "$exe" >"$backup/executable-context.before"
bootctl status >"$backup/boot.before"
efibootmgr -v >"$backup/firmware.before"
journalctl -n 0 --show-cursor >"$backup/journal-cursor.before"
# Copy encrypted anchors without printing their contents; preserve absent ESP copies.
shopt -s nullglob
anchors=(/run/systemd/nvpcr/nvpcr-anchor.cred /var/lib/systemd/nvpcr/nvpcr-anchor.cred)
for anchor in "${anchors[@]}"; do [[ -s $anchor && ! -L $anchor ]] || fail 'Required anchor missing or symlinked.'; done
esp=$(bootctl --print-esp-path)
boot=$(bootctl --print-boot-path)
anchors+=("$esp"/loader/credentials/nvpcr-anchor.*.cred)
if [[ $boot != "$esp" ]]; then anchors+=("$boot"/loader/credentials/nvpcr-anchor.*.cred); fi
for anchor in "${anchors[@]}"; do
  [[ -f $anchor && ! -L $anchor ]] || fail 'Unexpected anchor file type.'
  cp --parents --preserve=mode -- "$anchor" "$backup"
done
# Install a root-owned verified snapshot, not the operator-writable original.
install -m 0600 -- "$2" "$backup/candidate.pp"
hash_is "$backup/candidate.pp" "$module_hash" || fail 'Copied module hash mismatch.'
hash_is "$policy" "$base_hash" || fail 'Policy changed during preflight.'
printf '%s\n' 'Installation started; retain this directory for manual recovery.' >"$backup/installation-started"
semodule -X 400 -i "$backup/candidate.pp"
restorecon "$exe"
hash_is "$policy" "$merged_hash" || fail 'Installed policy differs; stop before service execution.'
[[ $(stat -c %C "$exe") == system_u:object_r:hermes_tpm2_setup_exec_t:s0 ]] || fail 'Label validation failed.'
[[ $(getenforce) == Enforcing ]] || fail 'Enforcing validation failed.'
printf '%s\n' 'POLICY_INSTALL_VERIFIED; no service was restarted. Follow the approved acceptance procedure.'
