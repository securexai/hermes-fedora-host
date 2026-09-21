# Hermes boot automation (Regime B: unattended cold start)

**Target:** `aicowork@10.0.30.10` (`hermes.ai.lab.local`), Fedora 44 Server, AWZ SER3
**Branch:** `codex/hermes-manual-guide-plan`
**Requirement adopted:** the server must recover from power loss and reboot with **no human present** —
no passphrase, no power-button press.
**Status:** **B1–B5 ✅ PASS, plus the explicit fallback proof ✅, on 2026-09-13** — the server powers itself
on after AC restoration and boots with no passphrase and no keyboard input, and the recovery path was
demonstrated by removing the TPM token and confirming the console passphrase prompt returns and unlocks.
**B6 (clean-install validation) ✅ PASS, 2026-09-14** — executed end to end on a fresh Fedora 44 Server
install; the record is [the B6 handoff](HERMES_B6_CLEAN_INSTALL_HANDOFF.md). Evidence:
[boot B1–B5](plans/evidence/2026-09-13-hermes-boot-b1-b5.json),
[B6 change ledger](plans/evidence/2026-09-14-hermes-b6-change-ledger.md),
[B6 evidence record](plans/evidence/2026-09-14-hermes-b6-baseline.json).
**Secret policy:** no passphrase, recovery key, or credential value appears in this document, the
execution record, the evidence files, or Git.

## 1. Why this is now a prerequisite

The original manual-profile baseline excluded it on purpose: the guide says *"TPM auto-unlock is an
optional later decision, not baseline hardening"*, the simple-profile amendment excludes *"TPM enrollment
or firmware changes"*, and the boot expectation was *"expect a reboot to require the disk-unlock
passphrase at the console."* That baseline delivered **Regime A** — unattended application, supervised
boot — and M01 passed its controlled-reboot gate with an operator at the console.

Regime B is a stricter requirement, so it becomes a **prerequisite of the readiness definition**, not a
post-deployment nicety. Three independent layers must hold:

| # | Prerequisite | Layer | Status |
| --- | --- | --- | --- |
| 1 | Firmware powers on when AC returns | Firmware | ✅ option present and set (B1); wall-power cycle self-powered (B5) |
| 2 | TPM2 releases the LUKS key with no input | Linux / initramfs | ✅ enrolled against `PCR 7:sha256` and proven (B3–B4) |
| 3 | Services autostart and linger | systemd user manager | ✅ validated (M04 reboot test) |

Failure 1 leaves the box dark. Failure 2 leaves it powered on and waiting forever. They are independent
and must be gated and evidenced separately.

## 2. Design decision: simple path first

**Chosen:** keep Fedora's existing trusted chain (Microsoft-signed shim → Fedora-signed GRUB 2.12 →
signed kernel + dracut initramfs). Add one TPM2 keyslot bound to **SHA-256 PCR7**, one crypttab option,
and one initramfs rebuild.

| | Simple (chosen) | UKI + signed PCR11 (deferred) |
| --- | --- | --- |
| Boot chain | unchanged | new systemd-boot + own Secure Boot key enrollment |
| Binds | Secure Boot state/policy (PCR7) | exact kernel + initramfs + cmdline |
| Kernel updates | re-enroll only if PCR7 moves | pre-sign a new policy; smoother |
| New tooling on host | none (`systemd-cryptenroll` already present) | `systemd-boot`, `ukify`, `sbsign`, ESP headroom |
| Lockout triggers | firmware/Secure-Boot key changes | every UKI byte/phase change |

**Explicitly rejected for this phase:** PCR12 binding (firmware-defined semantics, a second uncontrolled
lockout trigger with no demonstrated benefit), PCR11 without a UKI, clevis/tang, an initramfs keyfile
(the key would sit beside the ciphertext), automatic resealing after a mismatch, and the held
`configure-tpm2-auto-unlock.sh` (its crypttab rewriting is defective).

**PCR policy is always stated explicitly on the command line.** No reliance on any tool default; systemd
259's default is to bind no PCRs at all.

## 3. Gate B1 — prerequisites and firmware ordering

The firmware setting is a **firmware configuration change** and firmware configuration feeds PCR
measurements, including PCR7. Changing it *after* enrollment can move the value the token is bound to,
and the first power restoration after an outage is the worst possible moment to discover that.

1. Confirm console access and that the LUKS passphrase is known and usable.
2. In firmware setup, set the power-loss behaviour to **power on**. This SER3's option exists and is set
   (recorded during B1); other hardware may name it *Restore AC Power Loss*, *AC Back*, *After Power
   Failure*, or *State After Power Loss*.
   If the firmware exposes no such setting, record that and continue — gate B5 then cannot pass, but B2–B4
   still deliver "no passphrase", leaving only a power-button press.
3. Reboot, then re-record the baseline: Secure Boot state, PCR7, boot ID.
4. Verify: the host is reachable, Secure Boot is still `enabled`, and no boot measurement changed
   unexpectedly. Any unexplained mismatch stops the work.

**Absence of the firmware option blocks only B5**, never B2–B4.

## 4. Gate B2 — recovery material before any change

1. Keep the existing passphrase in keyslot 0. **It is the break-glass recovery credential**; this phase
   never removes it.
2. Prove it: `cryptsetup open --test-passphrase` on the LUKS device must succeed.
3. Take a fresh LUKS header backup and move it off-host to encrypted storage. Record its keyslot
   identity, so it is later unambiguous which unlock methods a given header contains.
4. Back up `/etc/crypttab` and record its exact expected edit.
5. Record the LVM metadata (`vgcfgbackup`) again if the previous copy is stale.

A header backup taken *before* enrollment contains only the passphrase slot; one taken *after* contains
the passphrase slot plus the TPM token. Label them, and never let the older one silently replace the
newer during a recovery.

## 5. Gate B3 — enrollment and crypttab edit

Performed by `scripts/hermes/manual/boot/tpm-enroll.sh` (operator-run, interactive; `--enroll` is the
default mode, with `--preflight` and `--revert` as the other two). It shares `lib-luks-identity.sh` with
the other boot helpers, so stage the whole `boot/` directory.

1. **Resolve identity, then preflight, fail closed:** discover the LUKS2 device, mapper name and root LV
   from the running host — nothing about the reference host is hardcoded, so this works unchanged on a
   fresh install. Optionally refuse any other volume with `HERMES_EXPECT_UUID=<uuid>`. Then verify the
   target by root-device ancestry; confirm a TPM2 device; confirm Secure Boot state; inventory existing
   keyslots and tokens; assert the crypttab has exactly one matching record; confirm free space for the
   new initramfs.
2. `systemd-cryptenroll --tpm2-device=auto --tpm2-pcrs=7:sha256 <device>` — adds a keyslot and a
   `systemd-tpm2` token; the passphrase stays.

   **Syntax note, verified against the installed man page:** the PCR bank is a *suffix on the PCR entry*
   (`--tpm2-pcrs=7:sha256`), there is no separate bank option, and an omitted `--tpm2-pcrs` binds to
   **no PCRs at all** — that is the documented systemd 259 default. Stating the policy explicitly is
   therefore mandatory, not stylistic.
3. Verify: `luksDump` shows the new keyslot + token, and `--test-passphrase` still succeeds.
4. Edit **only** the matching crypttab record, preserving `discard,x-initrd.attach`, appending
   `tpm2-device=auto`. The script rewrites one line and asserts the file is otherwise unchanged.
5. Regenerate the initramfs for the running kernel; verify the image now contains the TPM2 and
   `systemd-cryptsetup` content.
6. Take a post-enrollment header backup off-host and record the new keyslot identity.

## 6. Gate B4 — unattended boot verification

1. Reboot and observe **no passphrase prompt**; confirm Secure Boot enabled and a new boot ID.
2. Confirm the measured state still satisfies the token. On the reference host this step also checks that
   the gateway and worker containers autostarted and re-runs the transport probe; on the clean-install
   runbook no application exists yet at this point, so those checks move to Step 9/10 and are performed
   by `scripts/hermes/manual/boot/b4-verify.sh`.
3. **Prove the fallback** with `scripts/hermes/manual/boot/fallback-wipe.sh`: it wipes the TPM token but
   deliberately leaves crypttab still requesting TPM, so the next boot must fall back to the console
   prompt. Reboot, confirm the prompt reappears and the passphrase unlocks, then re-enroll. This is the
   only honest proof that a failed unseal degrades to a recoverable state rather than a dead box.
   `tpm-enroll.sh --revert` also reverts crypttab, so it proves only the trivial case and does not
   substitute for this step.
4. Confirm no AVC denials and no unexpected failed units.

## 7. Gate B5 — power restoration

Only with the firmware setting from B1 present:

1. Orderly shutdown, then disconnect AC at the wall.
2. Restore AC. The server must power on by itself, unlock without input, and reach the running state
   with both containers and Telegram connected.
3. Record the observed sequence and timings.

## 8. Gate B6 — clean-install validation (fresh OS)

The fresh install is the real acceptance: it proves the procedure produces a fully automatic server
without relying on hand-tuned history. The ordered runbook is
[the clean-install procedure](HERMES_BOOT_CLEAN_INSTALL.md). It must be executed end to end on a fresh
Fedora 44 Server install, and it must place the boot prerequisites **before** application deployment, so
the readiness definition can no longer omit them.

A clean install passes only when, after the final step, the machine survives a wall-power cycle with no
keyboard input and Hermes answers on Telegram.

**Status: ✅ PASS, 2026-09-14.** Executed on the spare bare-metal host (`hermes.ai.lab.local`); M02–M05,
M04 steps 7–14 and Phase 7 (the wall-power acceptance) all passed, and the record names every change made
along the way. See [the B6 handoff](HERMES_B6_CLEAN_INSTALL_HANDOFF.md) — including its section 8, which
lists the twelve limitations the run did not clear.

## 9. Acceptance tests (all required, in order)

- Preflight rejects a mismatched device, an unexpected keyslot/token set, or an ambiguous crypttab.
- Enrollment leaves the passphrase working; `--test-passphrase` succeeds before and after.
- A reboot unlocks with no keyboard input; Secure Boot remains enabled.
- Wiping the token restores the passphrase prompt, and the passphrase unlocks.
- Cold start after AC restoration powers on and unlocks with no input (B5 only).
- Both Hermes containers autostart on every boot; the transport probe passes after each.
- Telegram reconnects after each boot without operator action.
- An interrupted enrollment (`--revert`) leaves the passphrase path intact and the host bootable.
- Firmware power-loss change is recorded and PCR7 is re-verified after it.

## 10. Recovery and rollback

| Situation | Action |
| --- | --- |
| TPM unseal fails at boot | Console passphrase prompt; unlock, then re-enroll or clear the token |
| PCR7 moved (firmware/db/MOK change) | Console unlock; re-enroll with the new measurements, then record why |
| Bad crypttab edit | Restore the saved crypttab, regenerate the initramfs |
| Unbootable after change | Console + the recorded passphrase; restore the header backup only if slots were lost |
| Need to abandon TPM unlock entirely | `systemd-cryptenroll --wipe-slot=tpm2 <device>`, restore crypttab, regenerate initramfs |

`--revert` in the enrollment script performs exactly that last row.

## 11. Limitations

- **A stolen intact server boots itself**, and the provider/bot credentials live on that volume. Accepted
  for this host; mitigate by keeping the OpenAI key restricted and revoking on doubt. **Disk-only theft
  remains protected**: the TPM is on the motherboard, so the keyslot cannot be unsealed on another
  machine.
- **PCR7 binds Secure Boot *policy state*, not the boot contents.** Two concrete consequences, both
  unmitigated at this phase:
  1. `/boot` and the ESP are unencrypted and PCR7 does not measure them, so an attacker who can boot a
     *signed* live environment (Secure Boot still enabled, therefore PCR7 unchanged) can replace the
     initramfs with one that exfiltrates the LUKS key, then reboot and have the TPM release it.
  2. Fedora's GRUB permits editing a boot entry at the menu unless a superuser password is set, so
     `rd.break`/`init=/bin/bash` can yield a root shell on the already-unlocked volume with no passphrase
     — again with PCR7 unchanged.
  Cheapest meaningful mitigations, in order: set a GRUB superuser password (`grub2-setpassword`), protect
  firmware settings and removable boot, and treat clevis/tang or the UKI/signed-PCR11 phase as the real
  fixes.
- Automatically unlocking the disk means the running system holds the dm-crypt key in RAM, so physical
  attacks on a running or suspended machine (cold boot, DMA) become relevant where they were not before.
- PCR7 moves on firmware updates and Secure Boot key/database/MOK changes, so a firmware update can
  require supervised re-enrollment before the box will come back unattended.
- The SER3 uses a firmware TPM (MSFT0101), which is weaker than a discrete TPM.
- Binding is to Secure Boot state, **not** to the specific kernel/initramfs. An attacker able to boot an
  older still-trusted image boots an approved state; only the UKI/PCR11 phase would narrow that.
- `discard` remains in the crypttab options; this work does not change that pre-existing tradeoff.
- The firmware AC-back setting **exists on this SER3 and is set**, but it is firmware state: a firmware
  update, a CMOS/NVRAM clear, or a dead CMOS battery can silently revert it to "stay off". Nothing in this
  procedure detects that until the next real outage, and there is no out-of-band power control, so a lost
  setting means the box stays dark until a human arrives.
