#!/usr/bin/env bash
# Gate B4 recovery proof, step 1: remove ONLY the TPM token and deliberately keep
# the crypttab asking for TPM unlock. The next boot must then fall back to the
# console passphrase prompt and unlock normally.
#
# This is the honest test of the failure mode: crypttab still requests TPM, but
# the token is gone, so the initramfs cannot unseal and must prompt. Reverting
# the crypttab as well would only prove the trivial case, and is what
# `tpm-enroll.sh --revert` does for the different purpose of abandoning TPM.
#
# The passphrase slot is never touched.
#
# Identity is discovered on the running host (see lib-luks-identity.sh); stage
# the whole boot/ directory next to this script.
#
#   sudo bash ~/hermes-manual/boot/fallback-wipe.sh --apply
set -u
set -o pipefail
export LC_ALL=C

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib-luks-identity.sh
# shellcheck disable=SC1091
. "$HERE/lib-luks-identity.sh" || {
  printf 'STOP: cannot load %s/lib-luks-identity.sh (stage the whole boot/ directory)\n' "$HERE" >&2
  exit 1
}
# shellcheck source=../lib-manual-common.sh
# shellcheck disable=SC1091
. "$HERE/../lib-manual-common.sh" || {
  printf 'STOP: cannot load %s/../lib-manual-common.sh (stage the whole manual/ tree)\n' "$HERE" >&2
  exit 1
}

mp_parse_mode "$@"

die() {
  printf 'STOP: %s\n' "$*" >&2
  exit 1
}

[ "$(id -u)" -eq 0 ] || hermes_identity_die "must run as root"
mp_require_apply 'would wipe the TPM2 token so the next boot must fall back to the passphrase'
mp_require_host_identity
ADMIN_ACCOUNT=${HERMES_ADMIN:-aicowork}
ADMIN_HOME=$(hermes_admin_account)
OUT="$ADMIN_HOME/hermes-fallback-wipe.out"

rc=0
{
  echo "### Gate B4 recovery proof - step 1 (wipe TPM token, keep crypttab)"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo

  echo "===== identity (discovered on this host) ====="
  hermes_resolve_luks_identity
  DEV=$HERMES_LUKS_DEV
  MAPPER=$HERMES_MAPPER
  echo "device=$DEV"
  echo "mapper=$MAPPER"
  echo "luks_uuid=$HERMES_LUKS_UUID"
  echo

  echo "===== state before ====="
  cryptsetup luksDump "$DEV" | grep -E '^  [0-9]+: (luks2|systemd-tpm2)' | sed 's/^/  /'
  echo "keyslots=$(cryptsetup luksDump "$DEV" | grep -cE '^  [0-9]+: luks2' || true)"
  echo "tpm2_tokens=$(cryptsetup luksDump "$DEV" | grep -cE '^  [0-9]+: systemd-tpm2' || true)"
  echo "-- crypttab (must be left asking for tpm2) --"
  grep -E "^${MAPPER}[[:space:]]" /etc/crypttab | sed 's/^/  /'

  tokens=$(cryptsetup luksDump "$DEV" | grep -cE '^  [0-9]+: systemd-tpm2' || true)
  [ "$tokens" -ge 1 ] || die "no systemd-tpm2 token present; nothing to prove (re-enroll first)"

  crypttab_before=$(sha256sum /etc/crypttab | cut -d' ' -f1)
  echo "crypttab_sha256_before=$crypttab_before"
  echo

  echo "===== wipe the TPM token only ====="
  systemd-cryptenroll --wipe-slot=tpm2 "$DEV"
  echo "wipe_rc=$?"
  echo

  echo "===== state after ====="
  cryptsetup luksDump "$DEV" | grep -E '^  [0-9]+: (luks2|systemd-tpm2)' | sed 's/^/  /'
  keyslots_after=$(cryptsetup luksDump "$DEV" | grep -cE '^  [0-9]+: luks2' || true)
  tokens_after=$(cryptsetup luksDump "$DEV" | grep -cE '^  [0-9]+: systemd-tpm2' || true)
  echo "keyslots_after=$keyslots_after tpm2_tokens_after=$tokens_after"
  [ "$keyslots_after" -ge 1 ] || die "passphrase slot disappeared; restore the header backup now"
  [ "$tokens_after" -eq 0 ] || die "token still present after wipe"
  echo

  echo "===== crypttab must be UNCHANGED (still requests tpm2) ====="
  crypttab_after=$(sha256sum /etc/crypttab | cut -d' ' -f1)
  echo "crypttab_sha256_after=$crypttab_after"
  # ENFORCED, not merely printed (C53). A changed crypttab invalidates the whole point of
  # this step: the next boot would prompt because nothing asks for TPM, which is the
  # trivial case rather than the fallback proof. The verdict is emitted as a marker and
  # turned into a non-zero exit AFTER the block, deliberately not by exiting here, so the
  # passphrase check and the NEXT instructions still run and leave the host known.
  if [ "$crypttab_before" = "$crypttab_after" ]; then
    echo "crypttab_unchanged=yes"
  else
    echo "crypttab_unchanged=NO"
    echo "FALLBACK_PROOF=INVALID crypttab changed during the token wipe"
  fi
  grep -E "^${MAPPER}[[:space:]]" /etc/crypttab | sed 's/^/  /'
  echo

  echo "===== passphrase still works ====="
  if cryptsetup open --test-passphrase "$DEV"; then
    echo "passphrase_slot=OK"
  else
    die "passphrase slot failed; restore the pre-enrollment header backup"
  fi
  echo

  echo "WIPE=done"
  echo "NEXT: reboot. The crypttab still asks for TPM, but the token is gone, so the"
  echo "      initramfs MUST fall back to the passphrase prompt."
  echo "      Expected: passphrase prompt appears -> enter the passphrase -> system boots."
  echo "      If it boots without any prompt, that is a FAILURE of the fallback (report it)."
  echo "      After it is up, re-enroll with: sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/boot/tpm-enroll.sh --enroll --apply"
  echo "===== done ====="
} 2>&1 | tee "$OUT" || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 600 "$OUT" 2>/dev/null || true
echo "WROTE=$OUT"
grep -aE '^(keyslots_after|tpm2_tokens_after|crypttab_unchanged|passphrase_slot|WIPE=)' "$OUT" | head || true

# The enforced verdict (C53). Printing crypttab_unchanged was not enough: the rehearsal
# passed on the word appearing, so a NO value could ride through as REHEARSAL=PASS on the
# step the guide calls the difference between a proven and an assumed recovery path.
if grep -qa '^FALLBACK_PROOF=INVALID' "$OUT"; then
  echo "RESULT=FAIL - crypttab changed during the wipe, so the fallback proof is invalid"
  echo "         the next boot would prompt because nothing requests TPM, not because the token is gone"
  exit 1
fi
echo "RESULT=PASS - token wiped, crypttab unchanged, passphrase slot intact (next boot is a real proof)"
exit "$rc"
