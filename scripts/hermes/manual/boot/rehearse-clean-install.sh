#!/usr/bin/env bash
# B6 rehearsal: static, read-only checks that the clean-install runbook, the
# boot helpers and the end-to-end deployment guide still agree, and that the
# helpers can run on a FRESH install whose device, mapper, VG and LUKS UUID all
# differ from the reference host.
#
# Safe to run anywhere: it needs no root and never touches a block device or the
# running system. Section 16 creates and removes one temporary directory to
# self-test key provisioning. Run it before starting B6, and again after any edit
# to the runbook, the guide or the helpers.
#
#   bash scripts/hermes/manual/boot/rehearse-clean-install.sh
#
# Exit status: 0 = no FAIL. Advisories do not fail the run.
set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BOOT_DIR=$HERE
REPO_ROOT=$(cd "$HERE/../../../.." && pwd)
RUNBOOK=$REPO_ROOT/docs/HERMES_BOOT_CLEAN_INSTALL.md
AUTOMATION=$REPO_ROOT/docs/HERMES_BOOT_AUTOMATION.md
HANDOFF=$REPO_ROOT/docs/HERMES_MANUAL_HANDOFF.md
MANUAL_DIR=$REPO_ROOT/scripts/hermes/manual
MANUAL_README=$MANUAL_DIR/README.md
GUIDE=$REPO_ROOT/docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md
ENROLL=$BOOT_DIR/tpm-enroll.sh
WIPE=$BOOT_DIR/fallback-wipe.sh
VERIFY=$BOOT_DIR/b4-verify.sh
LIB=$BOOT_DIR/lib-luks-identity.sh

FAILURES=0
ADVISORIES=0

pass() { printf 'PASS     %s\n' "$*"; }
fail() {
  printf 'FAIL     %s\n' "$*"
  FAILURES=$((FAILURES + 1))
}
advise() {
  printf 'ADVISORY %s\n' "$*"
  ADVISORIES=$((ADVISORIES + 1))
}
section() { printf '\n== %s ==\n' "$*"; }

# ---------------------------------------------------------------- 1. inventory
section "1. Artifact inventory (runbook references resolve)"

for f in "$RUNBOOK" "$AUTOMATION" "$HANDOFF" "$ENROLL" "$WIPE" "$VERIFY" "$LIB"; do
  if [ -r "$f" ]; then
    pass "readable: ${f#"$REPO_ROOT"/}"
  else
    fail "missing or unreadable: $f"
  fi
done

# Every scripts/... or docs/... path named in the runbook must exist.
while read -r ref; do
  [ -n "$ref" ] || continue
  if [ -e "$REPO_ROOT/$ref" ]; then
    pass "runbook reference exists: $ref"
  else
    fail "runbook references a path that does not exist: $ref"
  fi
done < <(
  grep -oE '(scripts|docs)/[A-Za-z0-9._/-]+\.(sh|md|json|py)' "$RUNBOOK" | sort -u
)

# ---------------------------------------------------------------- 2. ordering
section "2. Runbook ordering constraints"

step_line() {
  grep -nE "^## Step [0-9]+ — .*$1" "$RUNBOOK" | head -n1 | cut -d: -f1 || true
}

fw_line=$(step_line 'Firmware power-loss')
enroll_line=$(step_line 'TPM2 enrollment')
deploy_line=$(step_line 'Deploy Hermes')
recovery_line=$(step_line 'Recovery material')

if [ -n "$fw_line" ] && [ -n "$enroll_line" ] && [ "$fw_line" -lt "$enroll_line" ]; then
  pass "firmware step precedes enrollment (PCR7 must not move after binding)"
else
  fail "firmware step must precede TPM2 enrollment"
fi

if [ -n "$recovery_line" ] && [ -n "$enroll_line" ] && [ "$recovery_line" -lt "$enroll_line" ]; then
  pass "recovery material recorded before enrollment"
else
  fail "recovery material must be recorded before enrollment"
fi

if [ -n "$deploy_line" ] && [ -n "$enroll_line" ] && [ "$enroll_line" -lt "$deploy_line" ]; then
  pass "boot prerequisites precede application deployment"
else
  fail "application deployment must follow the boot prerequisites"
fi

for test in 'No passphrase prompt' 'Wall-power cycle' 'Passphrase still unlocks' 'Secure Boot remains enabled'; do
  if grep -qF "$test" "$RUNBOOK"; then
    pass "acceptance test present: $test"
  else
    fail "acceptance test missing from the runbook: $test"
  fi
done

# ------------------------------------------------------- 3. CLI flag parity
section "3. tpm-enroll.sh flag parity (docs vs script)"

documented=$(
  grep -h 'tpm-enroll\.sh' "$RUNBOOK" "$AUTOMATION" "$HANDOFF" 2>/dev/null \
    | grep -oE -- '--[a-z-]+' | sort -u || true
)
implemented=$(grep -oE '^[[:space:]]+--[a-z-]+ *\|' "$ENROLL" | grep -oE -- '--[a-z-]+' | sort -u || true)

missing_impl=$(comm -23 <(printf '%s\n' "$documented") <(printf '%s\n' "$implemented"))
if [ -z "$missing_impl" ]; then
  pass "every documented flag exists in the script ($(printf '%s' "$implemented" | tr '\n' ' '))"
else
  fail "documented but not implemented: $(printf '%s' "$missing_impl" | tr '\n' ' ')"
fi

undocumented=$(comm -13 <(printf '%s\n' "$documented") <(printf '%s\n' "$implemented"))
if [ -n "$undocumented" ]; then
  advise "implemented but not documented in the runbook: $(printf '%s' "$undocumented" | tr '\n' ' ')"
fi

# ----------------------------------------------------------- 4. PCR policy
section "4. Enrollment policy claims (PCR, bank, PIN)"

# Matching the literal source text, so the shell must not expand it here.
# shellcheck disable=SC2016
if grep -qF -- '--tpm2-pcrs="${PCRS}:sha256"' "$ENROLL"; then
  pass "script binds the PCR bank as a suffix (PCRS:sha256)"
else
  fail "script no longer uses the 'PCR:bank' suffix form"
fi

if grep -qE '^PCRS=[0-9]+$' "$ENROLL" && [ "$(grep -oE '^PCRS=[0-9]+$' "$ENROLL" | cut -d= -f2)" = "7" ]; then
  pass "script binds PCR7"
else
  fail "script no longer binds PCR7"
fi

if grep -qF -- '--tpm2-with-pin=no' "$ENROLL"; then
  pass "script enrolls without a PIN"
else
  fail "script no longer disables the PIN"
fi

if grep -qF -- '--tpm2-pcr-banks' "$ENROLL" "$AUTOMATION"; then
  fail "invented --tpm2-pcr-banks option reappeared (there is no such option)"
else
  pass "no invented --tpm2-pcr-banks option"
fi

if grep -qE 'passphrase|test-passphrase' "$RUNBOOK" && grep -qF -- '--test-passphrase' "$ENROLL"; then
  pass "passphrase usability is asserted in both runbook and script"
else
  fail "runbook/script lost the passphrase usability assertion"
fi

# --------------------------------------------------- 5. fresh-install identity
section "5. Fresh-install portability (no hardcoded host identity)"

for s in "$ENROLL" "$WIPE" "$VERIFY"; do
  name=${s##*/}
  if grep -qE '^[A-Z_]*DEV=/dev/nvme' "$s" || grep -qE '^MAPPER=luks-' "$s"; then
    fail "$name still hardcodes a host-specific device or mapper"
  else
    pass "$name has no hardcoded device/mapper constant"
  fi
  if grep -qF '88846948-bb3c-4f04-98b8-0d72b3d6f9b6' "$s"; then
    fail "$name still hardcodes the reference-host LUKS UUID"
  else
    pass "$name does not hardcode the reference-host LUKS UUID"
  fi
  if grep -qF 'lib-luks-identity.sh' "$s"; then
    pass "$name sources the shared identity resolver"
  else
    fail "$name does not source lib-luks-identity.sh"
  fi
done

if grep -qE '^HERMES_EXPECT_UUID' "$LIB" || grep -qF 'HERMES_EXPECT_UUID' "$LIB"; then
  pass "UUID check is opt-in via HERMES_EXPECT_UUID"
else
  fail "unconditional UUID expectation returned to the resolver"
fi

# Proven with stubs: a fresh host with a different device, VG and UUID resolves.
section "6. Resolver self-test against a simulated fresh install"
STUB=$(mktemp -d)
trap 'rm -rf "$STUB"' EXIT
cat >"$STUB/findmnt" <<'EOF'
#!/usr/bin/env bash
printf '/dev/mapper/fedora_newhost-lv_root\n'
EOF
cat >"$STUB/lsblk" <<'EOF'
#!/usr/bin/env bash
# Faithful minimal lsblk stub. util-linux >= 2.41 (2.41.5 on Fedora 44) draws the
# inverse dependency tree with box-drawing glyphs in the NAME column even when
# piped and even with -n, so NAME arrives as "<glyph>luks-...". Only --raw/-r
# suppresses the tree formatting. The previous stub printed clean output
# unconditionally, which is exactly why the real breakage at
# lib-luks-identity.sh:48 was invisible to this rehearsal: the stub was more
# optimistic than the tool it stood in for.
raw=0
for a in "$@"; do
  case "$a" in
    --raw | -r) raw=1 ;;
  esac
done
tree() {
  if [ "$raw" -eq 1 ]; then
    printf 'fedora_newhost-lv_root lvm\n'
    printf 'luks-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee crypt\n'
    printf 'nvme0n1p3 part\n'
    printf 'nvme0n1 disk\n'
  else
    G=$'\u2514\u2500'
    printf 'fedora_newhost-lv_root lvm\n'
    printf '%s%s crypt\n' "$G" 'luks-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
    printf '  %s%s part\n' "$G" 'nvme0n1p3'
    printf '    %s%s disk\n' "$G" 'nvme0n1'
  fi
}
case "$*" in
  *PKNAME*/dev/mapper/luks-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee*)
    # Faithful, and deliberately unhelpful in the same way the real tool is: the
    # crypt device's OWN PKNAME is EMPTY, because its parent sits above it and is
    # not part of the default forward listing; lsblk then prints the PKNAMEs of
    # its LVM children. A `PKNAME ... | head -n1` therefore yields the empty
    # string, which is exactly how the second version-dependent break showed up on
    # Fedora 44. Reproduced here so a regression back to that call is caught.
    printf '\ndm-0\ndm-0\n'
    ;;
  *-s*/dev/mapper/fedora_newhost-lv_root*)
    tree
    ;;
  *) exit 1 ;;
esac
EOF
cat >"$STUB/cryptsetup" <<'EOF'
#!/usr/bin/env bash
case "$1" in
  isLuks) exit 0 ;;
  luksUUID) printf 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\n' ;;
  *) exit 1 ;;
esac
EOF
cat >"$STUB/getent" <<'EOF'
#!/usr/bin/env bash
printf 'operator:x:1000:1000::/home/operator:/bin/bash\n'
EOF
chmod +x "$STUB"/*
PATH="$STUB:$PATH" HERMES_ADMIN=operator HERMES_LUKS_DEV='' HERMES_ROOT_LV='' \
  bash -c '
    set -u
    . "$1"
    read -r d m r u <<<"$(hermes_discover_luks_identity)" || exit 1
    printf "DEV=%s\nMAPPER=%s\nROOT_LV=%s\nUUID=%s\nHOME=%s\n" \
      "$d" "$m" "$r" "$u" "$(hermes_admin_account)"
  ' _ "$LIB" >"$STUB/out" 2>"$STUB/err" || true

expect() {
  if grep -qxF "$1" "$STUB/out"; then
    pass "resolver: $1"
  else
    fail "resolver: expected '$1' (got: $(tr '\n' ' ' <"$STUB/out"))"
  fi
}
expect 'DEV=/dev/nvme0n1p3'
expect 'MAPPER=luks-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
expect 'ROOT_LV=/dev/mapper/fedora_newhost-lv_root'
expect 'UUID=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
expect 'HOME=/home/operator'

# A pinned mismatch must be refused, and a matching pin accepted.
if HERMES_EXPECT_UUID=11111111-2222-3333-4444-555555555555 \
  bash -c 'set -u; . "$1"; hermes_assert_expected_uuid aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee' \
  _ "$LIB" >/dev/null 2>&1; then
  fail "resolver: a mismatched HERMES_EXPECT_UUID was accepted"
else
  pass "resolver: mismatched HERMES_EXPECT_UUID is refused"
fi

if HERMES_EXPECT_UUID=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee \
  bash -c 'set -u; . "$1"; hermes_assert_expected_uuid aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee' \
  _ "$LIB" >/dev/null 2>&1; then
  pass "resolver: matching HERMES_EXPECT_UUID is accepted"
else
  fail "resolver: a matching HERMES_EXPECT_UUID was refused"
fi

# ------------------------------------------------- 7. fallback proof fidelity
section "7. Fallback proof (token wiped, crypttab still requesting TPM)"

if grep -qF 'fallback-wipe.sh' "$RUNBOOK"; then
  pass "runbook names fallback-wipe.sh for the fallback proof"
else
  fail "runbook prescribes --revert for the fallback proof, which also reverts crypttab and proves only the trivial case"
fi

if grep -qF -- '--wipe-slot=tpm2' "$WIPE"; then
  pass "fallback-wipe.sh wipes the TPM token"
else
  fail "fallback-wipe.sh no longer wipes the TPM token"
fi

if grep -qE '^\s*cp .*crypttab.*\s/etc/crypttab' "$WIPE"; then
  fail "fallback-wipe.sh restores crypttab, which would fake the fallback proof"
else
  pass "fallback-wipe.sh leaves crypttab requesting TPM"
fi

# Require an ENFORCED verdict, not the word appearing somewhere (C53). The previous form
# matched the `echo "crypttab_unchanged=..."` line itself, so it passed even though the
# value could only ever be printed and never acted on - a pure form check on the very step
# the guide calls the difference between a proven and an assumed recovery path.
if grep -qF 'FALLBACK_PROOF=INVALID' "$WIPE" && grep -qF 'RESULT=FAIL' "$WIPE"; then
  pass "fallback-wipe.sh enforces crypttab_unchanged with an explicit FAIL verdict"
else
  fail "fallback-wipe.sh only PRINTS crypttab_unchanged; it must enforce it (FALLBACK_PROOF=INVALID + RESULT=FAIL)"
fi

# Exercise the actual final verdict with synthetic logs. A previous live run
# printed RESULT=PASS after the passphrase check had failed and the script had
# already wiped its token.
verdict_tail=$STUB/fallback-verdict.sh
sed -n '/^# The pipeline may have printed successful wipe markers/,$p' "$WIPE" >"$verdict_tail"
verdict_log=$STUB/fallback-verdict.log
if [ -s "$verdict_tail" ]; then
  printf 'crypttab_unchanged=yes\n' >"$verdict_log"
  if verdict_output=$(OUT="$verdict_log" rc=1 bash "$verdict_tail" 2>&1); then
    verdict_status=0
  else
    verdict_status=$?
  fi
  if [ "$verdict_status" -ne 0 ] && grep -qF 'RESULT=FAIL' <<<"$verdict_output" \
    && ! grep -qF 'RESULT=PASS' <<<"$verdict_output"; then
    pass "fallback helper rejects a failed passphrase check after token wipe"
  else
    fail "fallback helper claimed success after a failed passphrase check"
  fi

  if verdict_output=$(OUT="$verdict_log" rc=0 bash "$verdict_tail" 2>&1); then
    verdict_status=0
  else
    verdict_status=$?
  fi
  if [ "$verdict_status" -ne 0 ] && grep -qF 'RESULT=FAIL' <<<"$verdict_output"; then
    pass "fallback helper requires completion markers"
  else
    fail "fallback helper accepted a log without completion markers"
  fi

  printf 'crypttab_unchanged=yes\npassphrase_slot=OK\nWIPE=done\n' >"$verdict_log"
  if verdict_output=$(OUT="$verdict_log" rc=0 bash "$verdict_tail" 2>&1); then
    verdict_status=0
  else
    verdict_status=$?
  fi
  if [ "$verdict_status" -eq 0 ] && grep -qF 'RESULT=PASS' <<<"$verdict_output"; then
    pass "fallback helper accepts a completed proof"
  else
    fail "fallback helper rejected a completed proof"
  fi
else
  fail "fallback helper final verdict was not found for behavior tests"
fi

if grep -qF 'ENROLLMENT_VERDICT=FAIL' "$ENROLL" && grep -qF 'RESULT=FAIL' "$ENROLL"; then
  pass "tpm-enroll.sh enforces the dracut/initramfs verdict"
else
  fail "tpm-enroll.sh only prints dracut_rc and the tpm2 line count; it must enforce them"
fi

if grep -qF -- '--revert' "$AUTOMATION" && grep -qF 'abandon TPM unlock entirely' "$AUTOMATION"; then
  pass "--revert remains documented as the abandon-TPM path"
else
  advise "--revert is no longer clearly documented as the abandon-TPM path"
fi

# ------------------------------------------------- 8. account-name contract
section "8. Administrator account contract"

if grep -qF 'HERMES_ADMIN' "$LIB"; then
  pass "admin account is overridable (HERMES_ADMIN)"
else
  fail "admin account is hardcoded with no override"
fi

for s in "$ENROLL" "$WIPE" "$VERIFY"; do
  name=${s##*/}
  if grep -qE '/home/[a-z]+/' "$s"; then
    adv_note=$(grep -oE '/home/[a-z]+/' "$s" | sort -u | tr '\n' ' ')
    advise "$name still contains literal home paths: $adv_note"
  else
    pass "$name resolves admin home instead of hardcoding it"
  fi
done

# ------------------------------------------------------- 9. exit-status integrity
section "9. Privileged-script exit status"

for s in "$ENROLL" "$WIPE" "$VERIFY"; do
  name=${s##*/}
  # Shell-metacharacter literals on purpose: we are grepping for the source text.
  # shellcheck disable=SC2016
  if grep -q 'pipefail' "$s" && grep -qE 'exit "[$]rc"|rc=[$][?]' "$s"; then
    pass "$name propagates a failure status through its tee pipeline"
  else
    fail "$name hides failures inside its tee pipeline (add pipefail and an rc capture)"
  fi
done

# ------------------------------------------- 10. runtime UID is not assumed
section "10. Runtime UID is derived, not hardcoded"

# The preparation guide: "A fixed numeric UID is not required; record the actual
# one." So no helper may bake in 1001.
hard=$(grep -lE 'users/1001|user@1001|/run/user/1001' "$MANUAL_DIR"/*.sh 2>/dev/null || true)
if [ -z "$hard" ]; then
  pass "no manual script hardcodes uid 1001"
else
  fail "hardcoded uid 1001 in: $(printf '%s\n' "$hard" | sed "s#$MANUAL_DIR/##g" | tr '\n' ' ')"
fi

for s in m04-backup.sh m04-reboot.sh m04-postboot.sh; do
  # Matching literal source text, including a variable reference, on purpose.
  # shellcheck disable=SC2016
  if grep -qF 'id -u hermes' "$MANUAL_DIR/$s" || grep -qF 'id -u "$RUNTIME_ACCOUNT"' "$MANUAL_DIR/$s"; then
    pass "$s derives the runtime uid from the account"
  else
    fail "$s does not derive the runtime uid"
  fi
done

# --------------------------------- 11. held scripts are marked, refs resolve
section "11. Superseded helpers and their references"

if grep -q 'SUPERSEDED' "$MANUAL_DIR/configure-tpm2-auto-unlock.sh"; then
  pass "configure-tpm2-auto-unlock.sh is marked SUPERSEDED"
else
  fail "configure-tpm2-auto-unlock.sh is held by the prep guide but not marked as superseded"
fi

if grep -q 'tpm2-luks-auto-unlock.md' "$MANUAL_DIR/configure-tpm2-auto-unlock.sh"; then
  fail "configure-tpm2-auto-unlock.sh still references docs/tpm2-luks-auto-unlock.md (does not exist)"
else
  pass "no dangling docs/tpm2-luks-auto-unlock.md reference"
fi

dangling=""
for s in "$MANUAL_DIR"/*.sh; do
  while read -r ref; do
    [ -n "$ref" ] || continue
    case "$ref" in
      docs/*) [ -e "$REPO_ROOT/$ref" ] || dangling="$dangling ${s##*/}:$ref" ;;
    esac
  done < <(grep -ohE 'docs/[A-Za-z0-9._/-]+\.md' "$s" 2>/dev/null | sort -u || true)
done
if [ -z "$dangling" ]; then
  pass "every docs/*.md path named inside a manual script exists"
else
  fail "dangling documentation references:$dangling"
fi

# ------------------------------- 12. cross-document status consistency
section "12. Status claims agree across documents"

if grep -q 'B1–B5 ✅ PASS' "$AUTOMATION"; then
  stale=""
  for claim in '❌ not enrolled' '❌ unverified on this SER3' 'No TPM token is enrolled' \
    'this SER3'"'"'s exact menu is unverified' 'firmware power-loss option is unverified'; do
    if grep -qF "$claim" "$AUTOMATION" "$HANDOFF" "$MANUAL_README" 2>/dev/null; then
      stale="$stale [$claim]"
    fi
  done
  if [ -z "$stale" ]; then
    pass "no pre-Regime-B status claim survives in the current docs"
  else
    fail "stale status claim(s) contradicting B1–B5 PASS:$stale"
  fi
fi

if grep -q 'M03–M06 remain open' "$MANUAL_README"; then
  fail "manual/README.md still says M03–M06 remain open"
else
  pass "manual/README.md no longer claims M03–M06 are open"
fi

if grep -q 'leave TPM enrollment alone\|leave TPM enrollment' \
  "$REPO_ROOT/docs/plans/2026-09-12-fedora-44-hermes-preparation-guide.md"; then
  if grep -q 'HERMES_BOOT_AUTOMATION.md' "$REPO_ROOT/docs/plans/2026-09-12-fedora-44-hermes-preparation-guide.md"; then
    pass "prep guide's TPM hold carries a forward pointer to the boot automation"
  else
    fail "prep guide still excludes TPM with no pointer to the adopted Regime B work"
  fi
fi

# ------------------------------------- 13. bundle artifacts are all present
section "13. Bundle artifacts referenced by the staged scripts exist"

# Every artifact a staged script installs from the bundle must be in the repo,
# or deployment stops partway. This caught a config helper that existed only on
# the reference host, making M03 acceptance unreproducible.
bundle_missing=""
bundle_checked=0
for s in "$MANUAL_DIR"/*.sh; do
  while read -r ref; do
    [ -n "$ref" ] || continue
    bundle_checked=$((bundle_checked + 1))
    [ -e "$MANUAL_DIR/$ref" ] || bundle_missing="$bundle_missing ${s##*/}:$ref"
  done < <(grep -ohE '[$]BUNDLE/[A-Za-z0-9._/-]+' "$s" 2>/dev/null \
    | sed 's#^[$]BUNDLE/##' | sort -u || true)
done
if [ -z "$bundle_missing" ]; then
  pass "all $bundle_checked bundle references resolve to repo files"
else
  fail "staged scripts install artifacts missing from the repo:$bundle_missing"
fi

# ------------------------------- 14. deployment guide references resolve
section "14. End-to-end deployment guide"

if [ -r "$GUIDE" ]; then
  pass "readable: docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md"

  fs_missing=""
  fs_checked=0
  # Boot helpers may live in subdirectories; mNN-/provision- helpers are
  # top-level. The `/`-free alternatives stop `~/hermes-m02-bundle/provision-*.sh`
  # from being read as a manual helper named `m02-bundle/provision-*.sh`.
  while read -r ref; do
    [ -n "$ref" ] || continue
    fs_checked=$((fs_checked + 1))
    [ -e "$MANUAL_DIR/$ref" ] || fs_missing="$fs_missing $ref"
  done < <(grep -ohE '(boot/[A-Za-z0-9._/-]+|m0[0-9]-[A-Za-z0-9._-]+|provision-[A-Za-z0-9._-]+)\.sh' "$GUIDE" \
    | sort -u || true)
  if [ -z "$fs_missing" ]; then
    pass "all $fs_checked helper references in the guide exist"
  else
    fail "deployment guide names scripts that do not exist:$fs_missing"
  fi

  while read -r path; do
    [ -n "$path" ] || continue
    if [ -e "$REPO_ROOT/$path" ]; then
      pass "guide path exists: $path"
    else
      fail "deployment guide names a path that does not exist: $path"
    fi
  done < <(grep -ohE 'scripts/[A-Za-z0-9._/-]+\.(sh|py)' "$GUIDE" | sort -u || true)
else
  fail "docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md is missing (the end-user procedure)"
fi

# ----------------------------------- 15. guide completeness and gate order
section "15. Deployment guide completeness"

if [ -r "$GUIDE" ]; then
  # Every M02-M05 deployment helper must be named by the guide.
  unlisted=""
  for s in "$MANUAL_DIR"/m0[2-5]-*.sh "$MANUAL_DIR"/provision-*.sh; do
    [ -e "$s" ] || continue
    grep -qF "${s##*/}" "$GUIDE" || unlisted="$unlisted ${s##*/}"
  done
  if [ -z "$unlisted" ]; then
    pass "every deployment helper is named in the guide"
  else
    fail "helpers missing from the guide:$unlisted"
  fi

  # Boot gates must be documented before the application deployment, because
  # firmware feeds PCR7 and the binding must not move underneath it afterwards.
  boot_line=$(grep -nE '^## Phase 4' "$GUIDE" | head -n1 | cut -d: -f1 || true)
  app_line=$(grep -nE '^## Phase 6' "$GUIDE" | head -n1 | cut -d: -f1 || true)
  if [ -n "$boot_line" ] && [ -n "$app_line" ] && [ "$boot_line" -lt "$app_line" ]; then
    pass "boot prerequisites precede application deployment in the guide"
  else
    fail "the guide must present boot prerequisites before application deployment"
  fi

  # The two safety-critical commands must be the right ones.
  if grep -qF 'fallback-wipe.sh' "$GUIDE"; then
    pass "guide uses the honest fallback proof (fallback-wipe.sh)"
  else
    fail "guide does not name fallback-wipe.sh for the fallback proof"
  fi
  if grep -qF 'rehearse-clean-install.sh' "$GUIDE"; then
    pass "guide tells the operator to rehearse first"
  else
    fail "guide does not reference the rehearsal precondition"
  fi

  # The user-manager guard asserts /home/hermes is a mount point, so the guide
  # must also require that separate filesystem. Without it the guard fails and
  # the deployment breaks at the application phase.
  if grep -qF 'AssertPathIsMountPoint=/home/hermes' "$GUIDE"; then
    if grep -qiE 'own filesystem|separate mount|separate filesystem' "$GUIDE"; then
      pass "guide requires the separate /home/hermes filesystem its guard asserts"
    else
      fail "guide asserts /home/hermes is a mount point but never requires that filesystem"
    fi
  else
    fail "guide no longer carries the /home/hermes mount assertion"
  fi

  # The accepted storage layout must be documented, with the data LV sized.
  if grep -qF '250 GiB' "$GUIDE" && grep -qF 'fedora_hermes' "$GUIDE"; then
    pass "guide documents the accepted storage layout and data LV size"
  else
    fail "guide does not document the accepted storage layout"
  fi
fi

# ------------------------- 16. worker client key provisioning (guide + helper)
section "16. Worker client key provisioning (guide and helper)"

KEY_HELPER=$MANUAL_DIR/provision-worker-client-key.sh
KEY_TMP=''
STUB_DIR=''
OWN_TMP=''
section_cleanup() {
  for d in "$KEY_TMP" "$STUB_DIR" "$OWN_TMP"; do
    if [ -n "$d" ]; then
      rm -rf "$d"
    fi
  done
}
trap section_cleanup EXIT

if [ -r "$KEY_HELPER" ]; then
  pass "worker client key helper exists: ${KEY_HELPER##*/}"
else
  fail "worker client key helper is missing: ${KEY_HELPER##*/}"
fi

if [ -r "$KEY_HELPER" ]; then
  # M02 only migrates a key from transport/keys and otherwise stops, so the
  # helper must generate one and must not regress on ownership or modes.
  if grep -qF 'podman unshare chown' "$KEY_HELPER"; then
    pass "key helper maps the private key to the gateway UID"
  else
    fail "key helper does not chown the private key through podman unshare"
  fi
  # Matching literal source text, including the variable references, on purpose.
  # shellcheck disable=SC2016
  if grep -qF 'chmod 0600 "$key"' "$KEY_HELPER" && grep -qF 'chmod 0644 "$pub"' "$KEY_HELPER"; then
    pass "key helper pins 0600 private / 0644 public modes"
  else
    fail "key helper does not pin the private/public key modes"
  fi
fi

if [ -r "$GUIDE" ]; then
  if grep -qF 'provision-worker-client-key.sh' "$GUIDE"; then
    pass "guide documents worker client key provisioning"
  else
    fail "guide never provisions worker_client_ed25519 before M02"
  fi

  key_line=$(grep -nF 'provision-worker-client-key.sh' "$GUIDE" | head -n1 | cut -d: -f1 || true)
  m02_line=$(grep -nF 'm02-deploy-and-validate.sh' "$GUIDE" | head -n1 | cut -d: -f1 || true)
  if [ -n "$key_line" ] && [ -n "$m02_line" ] && [ "$key_line" -lt "$m02_line" ]; then
    pass "key provisioning precedes the first M02 reference in the guide"
  else
    fail "key provisioning must precede M02 in the guide"
  fi

  if grep -qF '/home/hermes/gateway-ssh/worker_client_ed25519' "$GUIDE"; then
    pass "guide names the key location M02 expects"
  else
    fail "guide does not name /home/hermes/gateway-ssh/worker_client_ed25519"
  fi

  # Without a remote host operand, scp copies into the workstation's home and
  # the server-side sudo commands below never find their scripts.
  scp_count=$(grep -cE '^[[:space:]]*scp ' "$GUIDE" || true)
  bad_scp=''
  while IFS= read -r line; do
    case "$line" in
      *@*:*) ;;
      *) bad_scp="$bad_scp [$line]" ;;
    esac
  done < <(grep -E '^[[:space:]]*scp ' "$GUIDE" || true)
  if [ "$scp_count" -ge 1 ] && [ -z "$bad_scp" ]; then
    pass "every guide scp names a remote destination"
  else
    fail "guide scp without a remote host (copies locally):$bad_scp"
  fi

  # The M02-M05 helpers hardcode /home/aicowork, so the account is not a free
  # choice and HERMES_ADMIN must not be advertised as general portability.
  if grep -qF 'requires the administrator account' "$GUIDE" && grep -qF 'aicowork' "$GUIDE"; then
    pass "guide requires aicowork for the M02-M05 bundle"
  else
    fail "guide does not require aicowork for the M02-M05 bundle"
  fi

  if grep -qF '<ADMIN>' "$GUIDE"; then
    fail "guide still offers the <ADMIN> placeholder for an account the helpers require to be aicowork"
  else
    pass "guide uses the required aicowork account consistently"
  fi

  admin_bad=''
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    case "$line" in
      *boot* | *Boot* | *Phase\ 4*) ;;
      *) admin_bad="$admin_bad [$line]" ;;
    esac
  done < <(grep -F 'HERMES_ADMIN' "$GUIDE" || true)
  if [ -z "$admin_bad" ]; then
    pass "every HERMES_ADMIN mention is scoped to the boot helpers"
  else
    fail "HERMES_ADMIN is advertised beyond the boot helpers:$admin_bad"
  fi

  # F3: sudo resets the environment, so an exported variable cannot bind an
  # application helper. The guide must show the reviewed machine-id hash on the
  # sudo command line, or document the authorized root-owned pin bootstrap — and
  # must forbid blindly deriving the expected identity on the target.
  phase6_line=$(grep -nE '^## Phase 6' "$GUIDE" | head -n1 | cut -d: -f1 || true)
  phase7_line=$(grep -nE '^## Phase 7' "$GUIDE" | head -n1 | cut -d: -f1 || true)
  phase6=''
  if [ -n "$phase6_line" ] && [ -n "$phase7_line" ] && [ "$phase6_line" -lt "$phase7_line" ]; then
    phase6=$(sed -n "${phase6_line},$((phase7_line - 1))p" "$GUIDE")
  fi
  if grep -qF 'HERMES_EXPECT_MACHINE_ID_SHA256=<reviewed hash>' <<<"$phase6" \
    && grep -qF 'm00-pin-host-identity.sh' <<<"$phase6"; then
    pass "guide binds the application sequence to the reviewed host identity"
  else
    fail "the application phase does not establish the host identity its helpers require"
  fi
  if grep -qF 'never be used to discover' <<<"$phase6"; then
    pass "guide forbids blindly deriving the expected identity on the target"
  else
    fail "guide does not forbid blindly deriving the expected identity on the target"
  fi
fi

if [ -r "$KEY_HELPER" ]; then
  if command -v ssh-keygen >/dev/null 2>&1; then
    # shellcheck disable=SC1091
    # shellcheck source=../provision-worker-client-key.sh
    . "$KEY_HELPER"

    KEY_TMP=$(mktemp -d)
    KEY_PRIV=$KEY_TMP/worker_client_ed25519

    # Fresh creation.
    if provision_worker_client_key "$KEY_TMP" >/dev/null 2>&1; then
      pass "key helper provisions a fresh keypair"
    else
      fail "key helper failed on a fresh directory"
    fi
    if [ -s "$KEY_PRIV" ] && [ -s "$KEY_PRIV.pub" ]; then
      pass "fresh run created the private and public key files"
    else
      fail "fresh run did not create both key files"
    fi
    priv_mode=$(stat -c %a "$KEY_PRIV" 2>/dev/null || true)
    pub_mode=$(stat -c %a "$KEY_PRIV.pub" 2>/dev/null || true)
    if [ "$priv_mode" = 600 ] && [ "$pub_mode" = 644 ]; then
      pass "fresh key modes are 0600 private / 0644 public"
    else
      fail "unexpected key modes: private=${priv_mode:-none} public=${pub_mode:-none}"
    fi

    # Rerun preservation.
    priv_before=$(sha256sum "$KEY_PRIV" | cut -d' ' -f1)
    pub_before=$(sha256sum "$KEY_PRIV.pub" | cut -d' ' -f1)
    rerun_out=''
    if rerun_out=$(provision_worker_client_key "$KEY_TMP" 2>&1); then
      pass "key helper re-runs cleanly"
    else
      fail "key helper failed on a rerun"
    fi
    priv_after=$(sha256sum "$KEY_PRIV" | cut -d' ' -f1)
    pub_after=$(sha256sum "$KEY_PRIV.pub" | cut -d' ' -f1)
    if [ "$priv_before" = "$priv_after" ]; then
      pass "rerun preserves the existing private key"
    else
      fail "rerun replaced the existing private key"
    fi
    if [ "$pub_before" = "$pub_after" ]; then
      pass "rerun preserves the existing public key"
    else
      fail "rerun replaced the existing public key"
    fi

    # Recovery of a missing public key.
    rm -f "$KEY_PRIV.pub"
    recover_out=''
    if recover_out=$(provision_worker_client_key "$KEY_TMP" 2>&1); then
      pass "key helper recovers a missing public key"
    else
      fail "key helper failed to recover a missing public key"
    fi
    if [ -s "$KEY_PRIV.pub" ]; then
      derived_blob=$(ssh-keygen -y -f "$KEY_PRIV" | awk '{print $2}')
      rebuilt_blob=$(awk '{print $2}' "$KEY_PRIV.pub")
      if [ -n "$derived_blob" ] && [ "$derived_blob" = "$rebuilt_blob" ]; then
        pass "rebuilt public key matches the preserved private key"
      else
        fail "rebuilt public key does not match the private key"
      fi
    else
      fail "public key was not rebuilt"
    fi
    priv_recovered=$(sha256sum "$KEY_PRIV" | cut -d' ' -f1)
    if [ "$priv_before" = "$priv_recovered" ]; then
      pass "public key recovery leaves the private key untouched"
    else
      fail "public key recovery rewrote the private key"
    fi

    # Never print private key material.
    if printf '%s\n%s\n' "$rerun_out" "$recover_out" | grep -q 'PRIVATE KEY'; then
      fail "key helper printed private key material"
    else
      pass "key helper prints no private key material"
    fi
  else
    advise "ssh-keygen not found; key helper self-test skipped"
  fi
fi

# main()'s ownership sequence. ssh-keygen runs as root, so the private key starts
# root-owned, and rootless Podman cannot chown a root-owned inode from inside the
# runtime account's user namespace. The helper must therefore hand the private key
# to that account BEFORE the mapped-UID chown. Stub the privileged commands, run
# main() unprivileged, and assert the order of the ownership calls.
if [ -r "$KEY_HELPER" ] && command -v ssh-keygen >/dev/null 2>&1; then
  STUB_DIR=$(mktemp -d)
  OWN_TMP=$(mktemp -d)
  OWN_LOG=$STUB_DIR/calls.log
  : >"$OWN_LOG"

  cat >"$STUB_DIR/id" <<'STUB'
#!/usr/bin/env bash
if [ "${1:-}" = -u ]; then
  printf '0\n'
  exit 0
fi
exit 1
STUB

  cat >"$STUB_DIR/mountpoint" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB

  cat >"$STUB_DIR/chown" <<'STUB'
#!/usr/bin/env bash
printf 'chown %s\n' "$*" >>"$OWN_LOG"
exit 0
STUB

  cat >"$STUB_DIR/sudo" <<'STUB'
#!/usr/bin/env bash
printf 'sudo %s\n' "$*" >>"$OWN_LOG"
shift
shift
if [ "${1:-}" = -- ]; then
  shift
fi
exec "$@"
STUB

  cat >"$STUB_DIR/env" <<'STUB'
#!/usr/bin/env bash
printf 'env %s\n' "$*" >>"$OWN_LOG"
while [ "$#" -gt 0 ]; do
  case "$1" in
    -i | --chdir=* | *=*) shift ;;
    *) break ;;
  esac
done
exec "$@"
STUB

  cat >"$STUB_DIR/podman" <<'STUB'
#!/usr/bin/env bash
printf 'podman %s\n' "$*" >>"$OWN_LOG"
exit 0
STUB

  chmod +x "$STUB_DIR"/*

  OWN_KEY=$OWN_TMP/keys/worker_client_ed25519
  # The key helper now refuses to run unbound from the reviewed host, so the
  # fixture supplies this machine's fingerprint. That strengthens the fixture's
  # contract rather than bypassing it.
  fixture_host_hash=$(sha256sum /etc/machine-id 2>/dev/null | cut -d' ' -f1)
  if PATH="$STUB_DIR:$PATH" OWN_LOG="$OWN_LOG" \
    HERMES_EXPECT_MACHINE_ID_SHA256="$fixture_host_hash" \
    MP_PROFILE_LOCK_PATH="$OWN_TMP/profile.lock" \
    HERMES_GATEWAY_SSH_DIR="$OWN_TMP/keys" bash "$KEY_HELPER" >/dev/null 2>&1; then
    pass "key helper runs its privileged ownership sequence"
  else
    fail "key helper failed its privileged ownership sequence"
  fi

  owner_line=''
  mapped_line=''
  owner_is_account=false
  lineno=0
  while IFS= read -r line; do
    lineno=$((lineno + 1))
    read -r -a fields <<<"$line"
    for f in "${fields[@]}"; do
      if [ "$f" = "$OWN_KEY" ]; then
        case "${fields[0]:-}" in
          chown)
            [ -n "$owner_line" ] || owner_line=$lineno
            if [ "${fields[1]:-}" = 'hermes:hermes' ]; then
              owner_is_account=true
            fi
            ;;
          podman)
            [ -n "$mapped_line" ] || mapped_line=$lineno
            ;;
        esac
      fi
    done
  done <"$OWN_LOG"

  if [ -n "$owner_line" ]; then
    pass "helper hands the private key to the runtime account"
  else
    fail "helper never chowns the private key to the runtime account"
  fi
  if [ -n "$mapped_line" ]; then
    pass "helper maps the private key to the gateway UID"
  else
    fail "helper never maps the private key to the gateway UID"
  fi
  if [ -n "$owner_line" ] && [ -n "$mapped_line" ] && [ "$owner_line" -lt "$mapped_line" ]; then
    pass "runtime-account ownership precedes the rootless mapped chown"
  else
    fail "rootless mapped chown must run after the runtime account owns the private key"
  fi
  if [ "$owner_is_account" = true ]; then
    pass "private key is chowned to the runtime account before mapping"
  else
    fail "private key transfer does not target the runtime account"
  fi
fi

# ------------------------------------------------- 17. duplicate helper identity
section "17. Duplicate helper identity (no silently divergent copy)"
# Every other check in this rehearsal tests FORM - that a path exists, that a string
# appears. That is how C52 happened: scripts/hermes/manual/setup-ssh-key-only.sh was a
# stale, WEAKER copy of a second file at the repository root, and this rehearsal reported
# PASS throughout, because the shipped helper existed and the guide named it. Identity is
# the check that was missing. Any helper that exists in more than one place must be
# byte-identical, or be listed here as an intentional variant with a reason.
# Basename collisions that are NOT stale copies. The check is name-based, so it cannot tell
# "one artifact, two copies" from "two different programs that share a name"; this list is
# where that judgement is recorded, with the reason. Removing a name from this list makes the
# rehearsal fail until the pair is either reconciled or byte-identical.
#   harden-config.py  unattended forces terminal.backend=local; the manual variant keeps SSH.
#   host.py           944 differing lines. scripts/hermes/simple/ is the bounded
#                     application-only installer; scripts/hermes/unattended/ is the signed
#                     release entrypoint. Different programs that share a name.
#   controller.py     285 differing lines. scripts/hermes/simple/ is the provisioned SSH
#                     controller; scripts/hermes/unattended/ is the noninteractive dispatcher
#                     seam. Different programs that share a name.
DIVERGENT_ALLOWED="harden-config.py host.py controller.py"
dupes=$(
  {
    find "$REPO_ROOT/scripts" -type f \( -name '*.sh' -o -name '*.py' \) -print
    find "$REPO_ROOT" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \) -print
  } 2>/dev/null | awk -F/ '{ print $NF "\t" $0 }' | sort | awk -F'\t' '
    { c[$1] = c[$1] " " $2 }
    END { for (b in c) { n = split(c[b], a, " "); if (n > 1) print b "\t" c[b] } }
  ' || true
)
if [ -z "$dupes" ]; then
  pass "no duplicate shell or Python helper basenames found"
else
  while IFS=$'\t' read -r base paths; do
    [ -n "$base" ] || continue
    case " $DIVERGENT_ALLOWED " in
      *" $base "*)
        pass "duplicate helper is a documented intentional variant: $base"
        continue
        ;;
    esac
    identical=true
    first=''
    for p in $paths; do
      if [ -z "$first" ]; then
        first=$p
        continue
      fi
      cmp -s "$first" "$p" || identical=false
    done
    if [ "$identical" = true ]; then
      pass "duplicate helper is byte-identical: $base"
    else
      fail "duplicate helper has SILENTLY DIVERGED and needs reconciliation: $base ($paths)"
    fi
  done <<EOF
$dupes
EOF
fi

# ------------------------------------------------------------------- summary
printf '\n== Summary ==\n'
printf 'failures=%d advisories=%d\n' "$FAILURES" "$ADVISORIES"
if [ "$FAILURES" -eq 0 ]; then
  printf 'REHEARSAL=PASS\n'
else
  printf 'REHEARSAL=FAIL\n'
  exit 1
fi
