#!/usr/bin/env bash
# Gate B3/B4 helper: enroll a TPM2 keyslot bound to SHA-256 PCR7 so the server
# can unlock its LUKS root without a passphrase, and revert cleanly if needed.
#
# The existing passphrase is NEVER removed: it stays the break-glass recovery
# credential.
#
# Works on a fresh install. The LUKS device, mapper name and root LV are
# discovered from the running system (see lib-luks-identity.sh); nothing about
# the reference host is hardcoded. Override with HERMES_LUKS_DEV / HERMES_ROOT_LV
# if discovery is wrong, and pin the volume with HERMES_EXPECT_UUID=<uuid> to
# make the script refuse to touch anything else.
#
# Stage the whole boot/ directory together, then run as root on the Hermes host,
# interactively (systemd-cryptenroll prompts for the existing passphrase; the
# value is never echoed or logged by this script):
#
#   sudo bash ~/hermes-manual/boot/tpm-enroll.sh                 # read-only preflight (default)
#   sudo bash ~/hermes-manual/boot/tpm-enroll.sh --enroll --apply
#   sudo bash ~/hermes-manual/boot/tpm-enroll.sh --revert --apply
#
# After a successful enrollment the script does NOT reboot: gate B4 requires the
# operator to reboot and observe that no passphrase prompt appears.
set -u
set -o pipefail
export LC_ALL=C

MODE=preflight
for arg in "$@"; do
  case "$arg" in
    --preflight | preflight) MODE=preflight ;;
    --enroll | enroll) MODE=enroll ;;
    --revert | revert) MODE=revert ;;
    --apply | apply) ;; # mutation gate, consumed by mp_parse_mode
    --inspect | --dry-run) MODE=preflight ;;
    *)
      printf 'STOP: unknown mode: %s\nusage: %s [--preflight|--enroll|--revert] [--apply]\n' "$arg" "${0##*/}" >&2
      exit 2
      ;;
  esac
done

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

# `--apply` authorizes a change; the default mode is a read-only preflight.
MP_EXTRA_FLAGS='--preflight --enroll --revert'
mp_parse_mode "$@"

die() {
  printf 'STOP: %s\n' "$*" >&2
  exit 1
}

PCRS=7
RECOVERY=/root/recovery
STAMP=$(date -u +%Y%m%dT%H%M%SZ)

[ "$(id -u)" -eq 0 ] || hermes_identity_die "must run as root"
ADMIN_ACCOUNT=${HERMES_ADMIN:-aicowork}
ADMIN_HOME=$(hermes_admin_account)
STAGE="$ADMIN_HOME/hermes-boot-recovery"
OUT="$ADMIN_HOME/hermes-tpm-enroll.out"

rc=0
{
  echo "### TPM2 enrollment ($MODE)"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

  echo
  echo "===== identity (discovered on this host) ====="
  hermes_resolve_luks_identity
  DEV=$HERMES_LUKS_DEV
  MAPPER=$HERMES_MAPPER
  ROOT_LV=$HERMES_ROOT_LV
  HEADER="$RECOVERY/$(basename "$DEV")-tpm-$STAMP.header"
  PRE_HEADER="$RECOVERY/$(basename "$DEV")-pre-tpm-$STAMP.header"
  CRYPTTAB_BAK="$RECOVERY/crypttab-pre-tpm-$STAMP"
  echo "device=$DEV"
  echo "mapper=$MAPPER"
  echo "root_lv=$ROOT_LV"
  echo "luks_uuid=$HERMES_LUKS_UUID"

  echo
  echo "===== preflight ====="
  echo "-- root ancestry --"
  lsblk -s -o NAME,TYPE "$ROOT_LV" | sed 's/^/  /'
  if ! lsblk -s -o NAME "$ROOT_LV" | grep -q "${MAPPER}"; then
    die "root LV does not descend from $MAPPER"
  fi
  [ -e "/dev/mapper/$MAPPER" ] || die "$MAPPER is not active"

  echo "-- TPM --"
  find /dev -maxdepth 1 -name 'tpm*' 2>/dev/null | sort | sed 's/^/  /'
  [ -e /dev/tpmrm0 ] || [ -e /dev/tpm0 ] || die "no TPM device node"

  echo "-- Secure Boot --"
  mokutil --sb-state 2>&1 | sed 's/^/  /'
  mokutil --sb-state 2>&1 | grep -qi 'SecureBoot enabled' \
    || die "Secure Boot is not enabled; PCR7 binding would be meaningless"

  echo "-- existing keyslots / tokens --"
  keyslots=$(cryptsetup luksDump "$DEV" | grep -cE '^  [0-9]+: luks2' || true)
  tokens=$(cryptsetup luksDump "$DEV" | grep -cE '^  [0-9]+: systemd-tpm2' || true)
  echo "keyslots=$keyslots tpm2_tokens=$tokens"

  echo "-- crypttab --"
  [ -f /etc/crypttab ] || die "/etc/crypttab missing"
  matched=$(grep -cE "^${MAPPER}[[:space:]]" /etc/crypttab || true)
  echo "matching_records=$matched"
  grep -nE "^${MAPPER}[[:space:]]" /etc/crypttab | sed 's/^/  /'
  [ "$matched" -eq 1 ] || die "expected exactly one crypttab record for $MAPPER"
  if grep -q 'tpm2-device=auto' /etc/crypttab; then
    echo "note: tpm2-device=auto already present in crypttab"
  fi

  echo "-- space --"
  df -hT /boot / | sed 's/^/  /'

  if [ "$MODE" = "preflight" ]; then
    echo
    echo "PREFLIGHT=OK (no changes made)"
    echo "===== done ====="
  elif [ "$MODE" = "revert" ]; then
    mp_require_apply 'would wipe the TPM2 token and revert the matching crypttab record'
    mp_require_host_identity
    echo
    echo "===== revert ====="
    systemd-cryptenroll --wipe-slot=tpm2 "$DEV"
    echo "wipe_rc=$?"
    newest_ct=$(find "$RECOVERY" -maxdepth 1 -name 'crypttab-pre-tpm-*' -printf '%T@ %p\n' 2>/dev/null \
      | sort -rn | head -n1 | cut -d' ' -f2- || true)
    if [ -n "$newest_ct" ]; then
      cp -a "$newest_ct" /etc/crypttab
      echo "restored crypttab from $newest_ct"
    else
      echo "WARNING: no crypttab backup found; remove tpm2-device=auto by hand"
    fi
    dracut -f
    echo "dracut_rc=$?"
    echo "keyslots_after=$(cryptsetup luksDump "$DEV" | grep -cE '^  [0-9]+: luks2' || true)"
    echo "tpm2_tokens_after=$(cryptsetup luksDump "$DEV" | grep -cE '^  [0-9]+: systemd-tpm2' || true)"
    echo "REVERT=done - reboot and confirm the passphrase prompt returns"
    echo "===== done ====="
  else
    [ "$MODE" = "enroll" ] || die "unknown mode: $MODE"
    # Every mutation needs both the explicit mode and --apply, and is bound to
    # the reviewed host identity.
    mp_require_apply "would enroll a TPM2 keyslot bound to PCR$PCRS on this host"
    mp_require_host_identity
    [ "$tokens" -eq 0 ] || die "a systemd-tpm2 token already exists; refusing to add a duplicate (use --revert first)"

    echo
    echo "===== recovery material before change ====="
    install -d -m 0700 "$RECOVERY"
    cryptsetup luksHeaderBackup "$DEV" --header-backup-file "$PRE_HEADER"
    echo "pre_header=$PRE_HEADER"
    cp -a /etc/crypttab "$CRYPTTAB_BAK"
    echo "crypttab_backup=$CRYPTTAB_BAK"

    echo
    echo "===== enroll TPM2 (PCR$PCRS sha256, no PIN) ====="
    echo "systemd-cryptenroll will prompt for the EXISTING passphrase."
    # PCR bank is a SUFFIX on the PCR entry (man systemd-cryptenroll:
    # "--tpm2-pcrs=7:sha256" = PCR 7 from the SHA256 bank). There is no
    # separate bank option, and an omitted --tpm2-pcrs means NO PCRs at all.
    systemd-cryptenroll --tpm2-device=auto --tpm2-pcrs="${PCRS}:sha256" \
      --tpm2-with-pin=no "$DEV"
    enroll_rc=$?
    echo "enroll_rc=$enroll_rc"
    [ "$enroll_rc" -eq 0 ] || die "systemd-cryptenroll failed (rc=$enroll_rc); no keyslot, crypttab or initramfs change was made"

    echo
    echo "===== verify slots and passphrase ====="
    cryptsetup luksDump "$DEV" | grep -E '^  [0-9]+: (luks2|systemd-tpm2)' | sed 's/^/  /'
    keyslots_after=$(cryptsetup luksDump "$DEV" | grep -cE '^  [0-9]+: luks2' || true)
    tokens_after=$(cryptsetup luksDump "$DEV" | grep -cE '^  [0-9]+: systemd-tpm2' || true)
    echo "keyslots_after=$keyslots_after tpm2_tokens_after=$tokens_after"
    [ "$tokens_after" -ge 1 ] || die "no systemd-tpm2 token after enrollment"

    echo "testing the passphrase slot (prompts; value not logged)..."
    if cryptsetup open --test-passphrase "$DEV"; then
      echo "passphrase_slot=OK"
    else
      die "passphrase slot failed; revert now with --revert"
    fi

    echo
    echo "===== crypttab: edit only the matching record ====="
    CT_NEW="$RECOVERY/crypttab.new"
    awk -v name="$MAPPER" '
      BEGIN { done = 0 }
      /^[[:space:]]*#/ || NF == 0 { print; next }
      {
        if (!done && $1 == name) {
          if ($4 ~ /(^|,)tpm2-device=auto(,|$)/) { print; done = 1; next }
          $4 = $4 ",tpm2-device=auto"
          print; done = 1; next
        }
        print
      }
      END { if (!done) exit 3 }
    ' /etc/crypttab >"$CT_NEW" || die "crypttab rewrite failed to match the record"
    lines_before=$(wc -l </etc/crypttab)
    lines_after=$(wc -l <"$CT_NEW")
    echo "lines_before=$lines_before lines_after=$lines_after"
    [ "$lines_before" -eq "$lines_after" ] || die "crypttab line count changed; refusing to install"
    install -o root -g root -m 0644 "$CT_NEW" /etc/crypttab
    restorecon -v /etc/crypttab 2>&1 | sed 's/^/  /'
    echo "-- resulting record --"
    grep -nE "^${MAPPER}[[:space:]]" /etc/crypttab | sed 's/^/  /'

    echo
    echo "===== regenerate initramfs ====="
    dracut -f
    dracut_rc=$?
    echo "dracut_rc=$dracut_rc"
    INITRD="/boot/initramfs-$(uname -r).img"
    echo "initramfs=$INITRD"
    tpm2_lines=$(lsinitrd "$INITRD" 2>/dev/null | grep -cE 'tpm2|systemd-cryptsetup' || true)
    echo "tpm2_and_cryptsetup_lines=${tpm2_lines:-0}"
    # ENFORCED (C53). Both values were printed and then ignored, so the run reported
    # ENROLL=done even when dracut failed or the initramfs carried no TPM unlock support -
    # precisely the state where the next boot demands the passphrase with the token gone.
    if [ "$dracut_rc" -ne 0 ] || [ "${tpm2_lines:-0}" -eq 0 ]; then
      echo "ENROLLMENT_VERDICT=FAIL dracut_rc=$dracut_rc tpm2_lines=${tpm2_lines:-0}"
    else
      echo "ENROLLMENT_VERDICT=OK"
    fi

    echo
    echo "===== post-change recovery material (stage for off-host copy) ====="
    cryptsetup luksHeaderBackup "$DEV" --header-backup-file "$HEADER"
    echo "post_header=$HEADER"
    sha256sum "$HEADER" "$PRE_HEADER" 2>/dev/null
    rm -rf "$STAGE"
    install -d -m 0700 "$STAGE"
    cp -a "$HEADER" "$STAGE/"
    cp -a "$CRYPTTAB_BAK" "$STAGE/"
    chown -R "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$STAGE"
    chmod 600 "$STAGE"/*
    echo "staged=$STAGE (pull this off-host as $ADMIN_ACCOUNT, then delete it)"
    echo
    echo "ENROLL=done"
    echo "NEXT: reboot and confirm NO passphrase prompt (gate B4)."
    echo "      If anything looks wrong at the console, boot with the passphrase,"
    echo "      then run this script with --revert."
    echo "===== done ====="
  fi
} 2>&1 | tee "$OUT" || rc=$?

chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 600 "$OUT" 2>/dev/null || true
echo "WROTE=$OUT"

# Enforced enrollment verdict (C53).
if grep -qa '^ENROLLMENT_VERDICT=FAIL' "$OUT"; then
  echo "RESULT=FAIL - the initramfs does not carry TPM unlock support; do not reboot expecting it"
  echo "         fix the dracut failure, then re-run; --revert restores the passphrase-only boot"
  exit 1
fi
echo "RESULT=PASS - initramfs regenerated with TPM unlock support"
exit "$rc"
