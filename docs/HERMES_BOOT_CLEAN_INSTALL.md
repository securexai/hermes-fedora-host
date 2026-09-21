# Hermes clean-install runbook — fully automatic server

**Purpose:** produce a server that survives a wall-power cycle with **no keyboard input** and answers on
Telegram, starting from a fresh Fedora 44 Server install. This is gate **B6** of
[boot automation](HERMES_BOOT_AUTOMATION.md) and the acceptance test for the whole procedure.

**Why a clean install:** the current host was built in Regime A (supervised boot) and then amended. A
fresh install proves the documented order actually produces Regime B, instead of depending on
hand-tuned history. The critical difference from the original run: **the boot prerequisites come before
application deployment**, so the readiness definition can no longer omit them.

**Status:** ✅ **executed end to end and PASSED on 2026-09-14** on a fresh Fedora 44 Server install
(`hermes.ai.lab.local`). M02–M05, M04 steps 7–14 and the Phase 7 wall-power acceptance all passed. The
record — including twelve limitations the run did not clear, and the one gate it could not close without a
firmware-setup visit — is [the B6 clean-install handoff](HERMES_B6_CLEAN_INSTALL_HANDOFF.md).

**Scope:** this runbook is the ordering authority. Individual command detail lives in the referenced
artifacts; do not duplicate it here.

---

## Acceptance (all must pass)

1. No passphrase prompt on any boot, warm or cold.
2. Wall-power cycle → server powers on, unlocks, both Hermes containers autostart, Telegram replies —
   with no keyboard input at any point.
3. Passphrase still unlocks at the console when the TPM token is absent (proven explicitly).
4. Secure Boot remains enabled and SELinux enforcing throughout.

---

## Before you start

Start from [the end-to-end deployment guide](HERMES_MANUAL_DEPLOYMENT_GUIDE.md) if you want the whole build
as a single procedure; this runbook is the ordering authority that guide defers to for the boot gates.

Two preconditions, both checkable off-host:

1. **Rehearse the runbook.** On the workstation run
   `bash scripts/hermes/manual/boot/rehearse-clean-install.sh`. It is read-only: it checks that every
   path the runbook names exists, that the ordering constraints below still hold, that the enrollment
   policy matches what the script actually executes, that the helpers carry no reference-host identity,
   and it self-tests LUKS discovery against a simulated fresh install. `REHEARSAL=PASS` is the
   precondition; a `FAIL` means the runbook and the helpers have drifted apart.
2. **Stage the whole manual tree together.** Copy `scripts/hermes/manual/` to the host
   (`scp -r scripts/hermes/manual ~/hermes-manual`). The boot helpers live in
   `~/hermes-manual/boot/`, share `lib-luks-identity.sh` there, and source the shared
   `lib-manual-common.sh` one level up; they fail closed if either library is missing. Staging only
   `boot/` no longer works.
3. **One ordering constraint is load-bearing, and only one.** Step 2 (firmware power-loss behaviour) must
   precede Step 6 (TPM2 enrollment), because the firmware change can alter PCR 7 and the keyslot is sealed
   against the measurements the machine produces *at enrollment time*. Enrolling first would seal the keyslot
   against a PCR value the machine stops producing, and the next boot would demand the passphrase. Steps 3–5
   are independent of Step 2 and may be done before it; one validation run did exactly that and passed. Do not
   treat the step numbers as a required sequence beyond this constraint — but do not reorder Step 2 after
   Step 6 for any reason.

## Step 0 — Install Fedora 44 Server

Standard Server install. Choose **encrypted** storage (LUKS2) covering the root LVM; keep Secure Boot
enabled. Do not hand-partition to match the previous host — record what you actually get and use it.

## Step 1 — Baseline inventory (read-only)

Record a sanitized baseline with a UTC timestamp: release, kernel, CPU/RAM, `lsblk`, `findmnt`, VG/LV
layout, LUKS version and **keyslot inventory**, `cryptsetup luksDump` summary, `getenforce`, cgroup
version, firewalld zones, listening sockets, `mokutil --sb-state`, TPM presence, and the LUKS UUID.

Two facts must be unambiguous before continuing: the LUKS device identity, **and** that only the
passphrase slot exists.

## Step 2 — Firmware power-loss behaviour, **before** enrollment

Changing this setting is a firmware configuration change and firmware configuration feeds PCR7. Do it
first, so nothing moves underneath the binding afterwards.

1. At the console, enter firmware setup and set the power-loss behaviour to **power on** (menus name it
   *Restore AC Power Loss*, *AC Back*, *After Power Failure*, or *State After Power Loss*).
2. Record whether the option existed and what it was set to.
3. Reboot, then re-verify: Secure Boot still enabled, host reachable, no unexplained measurement change.

**If no such setting exists**, record that, continue, and mark acceptance test 2 as unachievable on this
hardware. Everything else still applies.

## Step 3 — Recovery material

1. Confirm the LUKS passphrase is known and **usable**: `cryptsetup open --test-passphrase`.
2. Store the passphrase somewhere durable and offline. It is the break-glass credential.
3. Take a LUKS header backup and move it **off-host** to encrypted storage, labelled with its keyslot
   identity (this one contains only the passphrase slot).
4. Back up `/etc/crypttab`; note its exact expected edit.
5. `vgcfgbackup`.

## Step 4 — Host preparation

Apply the preparation guide's sections in order: controlled update and host tools, LUKS/LVM recovery
metadata, key-only SSH, firewall review (drop Cockpit if unused), bounded journal, download-only update
policy, time synchronisation. Record the same evidence as M01.

## Step 5 — Runtime account

Create the unprivileged `hermes` account (no login shell, no sudo, valid subordinate IDs), lay out
`/home/hermes`, enable lingering, and confirm rootless Podman reports `rootless=true cgroups=v2` with a
graphroot under `/home/hermes`. **Do not start any application yet** — the boot prerequisite comes next.

> **Mutation gating.** `tpm-enroll.sh` defaults to a read-only preflight. Enrollment and revert
> each require both an explicit mode and `--apply`, plus `HERMES_EXPECT_MACHINE_ID_SHA256`
> matching the reviewed host. `tpm-enroll.sh --inspect` states the read-only intent explicitly, and
> `fallback-wipe.sh` also requires `--apply`.

## Step 6 — TPM2 enrollment (gate B3)

The helpers discover the LUKS device, mapper name and root LV from the running system, so a fresh
install needs no editing. They fail closed on anything ambiguous, and nothing about the reference
host is hardcoded. Overrides, only if discovery is wrong:

| Variable | Effect |
| --- | --- |
| `HERMES_EXPECT_UUID=<uuid>` | refuse to touch any other volume (recommended: pin the Step 1 UUID) |
| `HERMES_LUKS_DEV=/dev/nvmeXnY` | pin the LUKS container device |
| `HERMES_ROOT_LV=/dev/mapper/...` | pin the root LV |
| `HERMES_ADMIN=<account>` | account that owns staged material and helper logs (default `aicowork`) |

1. Run `sudo bash ~/hermes-manual/boot/tpm-enroll.sh --preflight` and read every line. Preflight is also the default with no flag. Record the discovered
   `device`, `mapper` and `luks_uuid` it prints. Stop on any mismatch.
2. Run it without arguments; it takes a fresh header backup, enrolls
   `--tpm2-pcrs=7` with SHA-256 and no PIN, verifies the passphrase slot still works, edits **only** the
   matching crypttab record, regenerates the initramfs, and stages post-change recovery material for an
   off-host copy.
3. Move the staged pre/post header backups and the crypttab backup off-host, then delete the staging
   directory.

## Step 7 — Unattended boot and fallback (gate B4)

1. Reboot. **Expect no passphrase prompt.** Confirm Secure Boot enabled and a new boot ID.
2. Confirm both Hermes units are not yet installed (expected at this stage) and no failed units exist.
3. **Prove the fallback** with `sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/boot/fallback-wipe.sh --apply`. It removes the TPM token but
   deliberately leaves crypttab still requesting TPM unlock, so the next boot must fall back to the
   console prompt. Reboot, confirm the prompt returns and the passphrase unlocks, then re-enroll with
   `tpm-enroll.sh`.

   This distinction matters: `tpm-enroll.sh --revert` also reverts crypttab, so it only exercises the
   case where nothing asks for TPM and proves nothing about a failed unseal. `--revert` is for
   abandoning TPM unlock entirely, not for this proof.

## Step 8 — Power restoration (gate B5)

Orderly shutdown, pull AC at the wall, restore AC. The server must power on by itself and reach a login
prompt with no input. Record timings. Skip only if Step 2 found no firmware option.

## Step 9 — Deploy Hermes

Now deploy the application on top of a host that already boots unattended. This is the M02–M06 sequence in
`scripts/hermes/manual/`, applied in order: worker image and transport (`m02-deploy-and-validate.sh`),
credentials, CLI and terminal scope (`m03-*.sh`, `provision-*.sh`), hardening, posture and the
stopped-state backup with isolated restore (`m04-*.sh`), then Telegram (`m05-*.sh`). Both Quadlets must
carry the gateway `[Install]` section from the start.

Account prerequisites, both fixed by the Step 4 preparation and **not** free choices:

- administrator `aicowork` — the helpers stage material and write logs in its home (override with
  `HERMES_ADMIN`);
- runtime `hermes` with no login shell, no sudo and valid subordinate IDs. Its **numeric UID is whatever
  the install produced**; do not assume 1001. The helpers derive it with `id -u hermes`, so record the
  actual value in the Step 1 baseline and use it wherever a path needs it
  (`/etc/containers/systemd/users/<uid>/`, `/run/user/<uid>`).

After the containers are up, `sudo bash ~/hermes-manual/boot/b4-verify.sh` re-asserts the boot properties with
the application present (autostart, secure boot, keyslot/token inventory, no AVCs, transport probe). It is
a post-deploy recheck only: at Step 7 the Hermes units do not exist yet, so it cannot replace the console
observations there.

## Step 10 — Final acceptance

Orderly shutdown → pull AC → restore AC → **no keyboard input at any point** → confirm:

- both containers are running,
- the end-to-end transport probe returns the worker's Fedora identity,
- Telegram replies,
- no published ports beyond `sshd` and `systemd-resolved`,
- no failed units and no new AVC denials.

## Evidence to record

Per step: UTC timestamp, exact command, expected vs actual result, artifact identities (image digests,
header-backup hashes, keyslot/token inventory before and after, PCR set and banks, initramfs identity),
and an explicit statement of what remains unverified. Record the firmware setting and the boot sequence
observed after the power cycle. Record the `rehearse-clean-install.sh` output (and its commit or file
hashes) that was the precondition for starting.

## Recovery if the clean install goes wrong

The passphrase slot is never removed, and a pre-enrollment header backup exists off-host. At the console,
boot with the passphrase and run `~/hermes-manual/boot/tpm-enroll.sh --revert --apply` to remove the TPM token, or restore
the saved crypttab and regenerate the initramfs. Never restore a header backup unless slots were actually
lost — restoring the pre-enrollment header silently deletes the TPM token and any later recovery slot.

## Limitations to carry into the handoff

- PCR7 binding tracks Secure Boot state, not the specific kernel/initramfs.
- A firmware update or Secure Boot key change can require supervised re-enrollment.
- A stolen intact server boots itself, with credentials on the volume.
- The firmware TPM on this hardware class is weaker than a discrete TPM.
