#!/usr/bin/env bash
# Failed-trial policy rollback only. Preserve all encrypted anchors and TPM state.
set -euo pipefail
umask 077
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
base_hash=bf58d5f5ae23502d844f70c153ef5366c31bf16ac9c77f548b94f3cf1aea1949
trial_hash=67d4f87afb2df3137fb8ab81f8f260942c3b43238bb275d16826b6c7a2ede8c0
exe=/usr/lib/systemd/systemd-tpm2-setup
policy=/etc/selinux/targeted/policy/policy.35
backup=/var/lib/hermes-selinux-trial-20260909
fail() {
  printf '%s\n' "$*" >&2
  exit 1
}
hash_is() { [[ $(sha256sum -- "$1" | cut -d ' ' -f 1) == "$2" ]]; }
[[ $# == 1 && $1 == --approved-trial-rollback ]] || {
  printf '%s\n' 'Expected --approved-trial-rollback' >&2
  exit 64
}
[[ $EUID == 0 && $(hostname -s) == hermes ]] || fail 'Operator sudo on Hermes required.'
[[ $(getenforce) == Enforcing ]] || fail 'Enforcing changed; stop for review.'
hash_is "$policy" "$trial_hash" || fail 'Current policy differs or rollback already applied; stop for review.'
hash_is "$backup/policy.before" "$base_hash" || fail 'Original policy backup mismatch.'
[[ $(stat -c %C "$exe") == system_u:object_r:hermes_tpm2_setup_exec_t:s0 ]] || fail 'Executable context drift.'
[[ -s $backup/service-first-recovery/current.json && -s $backup/service-first-recovery/summary.json ]] || fail 'Recovery evidence missing.'
modules=$(semodule -lfull)
[[ $(awk '$2 == "hermes_tpm2_setup" {print $1}' <<<"$modules") == 400 ]] || fail 'Unexpected module priorities.'
for unit in systemd-tpm2-setup.service systemd-tpm2-setup-early.service; do
  state=$(systemctl show -p ActiveState --value "$unit")
  [[ $state == active || $state == inactive || $state == failed ]] || fail 'Setup unit transitioning.'
  [[ $(systemctl show -p MainPID --value "$unit") == 0 ]] || fail 'Setup process running.'
done
mkdir -m 0700 "$backup/policy-rollback"
printf '%s\n' "$modules" >"$backup/policy-rollback/modules.before"
cp -- "$policy" "$backup/policy-rollback/policy.before"
stat -c %C "$exe" >"$backup/policy-rollback/context.before"
semodule -X 400 -r hermes_tpm2_setup
restorecon "$exe"
hash_is "$policy" "$base_hash" || fail 'Restored policy differs; stop for review.'
[[ $(stat -c %C "$exe") == system_u:object_r:init_exec_t:s0 ]] || fail 'Restored label mismatch.'
[[ $(matchpathcon -n "$exe") == system_u:object_r:init_exec_t:s0 ]] || fail 'Restored mapping mismatch.'
[[ $(getenforce) == Enforcing ]] || fail 'Enforcing validation failed.'
modules=$(semodule -lfull)
[[ $modules != *hermes_tpm2_setup* ]] || fail 'Trial module remains installed.'
printf '%s\n' 'POLICY_ROLLBACK_VERIFIED; no service restart, TPM operation or reboot requested.' >"$backup/policy-rollback/result"
cat "$backup/policy-rollback/result"
