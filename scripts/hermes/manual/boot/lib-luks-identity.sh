#!/usr/bin/env bash
# Shared LUKS identity resolution for the Hermes boot helpers (gates B3-B5).
#
# The helpers must work on a FRESH install, where the device node, mapper name,
# VG/LV name and LUKS UUID all differ from the reference host (the clean-install
# runbook explicitly says "do not hand-partition to match the previous host").
# Identity is therefore discovered from the running system, and is only
# cross-checked against an expected value when the operator supplies one.
#
# Resolution order:
#   1. explicit overrides: HERMES_LUKS_DEV, HERMES_ROOT_LV
#   2. discovery from the live root filesystem
# Anything ambiguous fails closed.
#
# Sourced by: tpm-enroll.sh, fallback-wipe.sh, b4-verify.sh.
# Not executable on its own; keep it next to the script that sources it.

hermes_identity_die() {
  printf 'STOP: %s\n' "$*" >&2
  exit 1
}

# Administrator account that owns the staged recovery material and helper logs.
# The preparation guide fixes this name, but keep it overridable so a fresh
# install with a differently named administrator fails loudly instead of
# silently leaving files owned by a nonexistent account.
hermes_admin_account() {
  local admin="${HERMES_ADMIN:-aicowork}" home
  home=$(getent passwd "$admin" | cut -d: -f6)
  [ -n "$home" ] || hermes_identity_die "administrator account '$admin' does not exist (set HERMES_ADMIN)"
  printf '%s\n' "$home"
}

# Discovery only: no device is touched and nothing is validated.
# Prints one line: "<luks-device> <mapper-name> <root-source> <uuid>".
# Returns non-zero when the root is not discoverable as LUKS2-backed.
hermes_discover_luks_identity() {
  local root_src mapper dev_name dev uuid

  root_src="${HERMES_ROOT_LV:-}"
  if [ -z "$root_src" ]; then
    root_src=$(findmnt -no SOURCE --target / 2>/dev/null || true)
  fi
  [ -n "$root_src" ] || return 1

  dev="${HERMES_LUKS_DEV:-}"
  if [ -z "$dev" ]; then
    # Resolve the mapper AND its backing device from a SINGLE raw inverse listing.
    # Do not go back to lsblk for PKNAME; two independent, version-dependent
    # behaviours both broke the original two-call form on util-linux 2.41.5
    # (Fedora 44), and both were found by gate B6 on a real host:
    #
    #   1. `lsblk -s` draws the inverse tree with box-drawing glyphs in the NAME
    #      column even when piped and even with -n, so NAME arrives as
    #      "└─luks-<uuid>". A field parse then returned the glyph-prefixed name,
    #      every lookup on /dev/mapper/<name> failed, and the resolver died with
    #      the misleading "is the root encrypted?" message on a host whose root
    #      was perfectly well encrypted. --raw suppresses alignment and tree
    #      formatting, emitting plain "name type" pairs.
    #   2. `lsblk -no PKNAME <crypt-device>` prints the crypt device's OWN PKNAME
    #      first -- empty, because its parent sits above it and is not part of the
    #      default forward listing -- followed by the PKNAMEs of its LVM children.
    #      `head -n1` therefore reliably returned the empty string, so even with
    #      the glyph fix alone discovery still failed.
    #
    # In an inverse listing the entry of type "crypt" is the mapper, and the next
    # line up the chain is the device that holds it. That is exactly what is
    # needed, comes from one call, and does not depend on either behaviour.
    read -r mapper dev_name <<<"$(lsblk --raw -no NAME,TYPE -s "$root_src" 2>/dev/null \
      | awk '$2 == "crypt" { printf "%s ", $1; getline; print $1; exit }')"
    [ -n "$mapper" ] && [ -n "$dev_name" ] || return 1
    dev="/dev/$dev_name"
  fi

  case "$dev" in
    /dev/*) ;;
    *) dev="/dev/$dev" ;;
  esac

  uuid=$(cryptsetup luksUUID "$dev" 2>/dev/null || true)
  [ -n "$uuid" ] || return 1

  printf '%s %s %s %s\n' "$dev" "luks-$uuid" "$root_src" "$uuid"
}

# Refuse to operate on a volume other than the one the operator pinned.
# A no-op unless HERMES_EXPECT_UUID is set: nothing is hardcoded here.
hermes_assert_expected_uuid() {
  local uuid=$1
  if [ -n "${HERMES_EXPECT_UUID:-}" ] && [ "$HERMES_EXPECT_UUID" != "$uuid" ]; then
    hermes_identity_die "unexpected LUKS UUID: got $uuid, expected $HERMES_EXPECT_UUID (refusing to touch an unknown volume)"
  fi
}

# Validating resolution. Sets HERMES_LUKS_DEV, HERMES_MAPPER, HERMES_ROOT_LV
# and HERMES_LUKS_UUID, failing closed on anything unexpected.
hermes_resolve_luks_identity() {
  local discovered
  discovered=$(hermes_discover_luks_identity) \
    || hermes_identity_die "cannot identify a LUKS2 device behind / (is the root encrypted?)"

  read -r HERMES_LUKS_DEV HERMES_MAPPER HERMES_ROOT_LV HERMES_LUKS_UUID <<<"$discovered"

  [ -e "$HERMES_ROOT_LV" ] || hermes_identity_die "$HERMES_ROOT_LV does not exist"
  [ -b "$HERMES_LUKS_DEV" ] || hermes_identity_die "$HERMES_LUKS_DEV is not a block device"
  cryptsetup isLuks --type luks2 "$HERMES_LUKS_DEV" \
    || hermes_identity_die "$HERMES_LUKS_DEV is not LUKS2"
  hermes_assert_expected_uuid "$HERMES_LUKS_UUID"

  export HERMES_MAPPER HERMES_ROOT_LV HERMES_LUKS_UUID
}
