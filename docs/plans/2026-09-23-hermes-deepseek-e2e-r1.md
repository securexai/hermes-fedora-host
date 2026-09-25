# Fresh Hermes DeepSeek end-to-end VM

Record state: ACTIVE — C01 checks incomplete; X01 grant active; B01 fallback stopped after failed passphrase check

## Approved baseline — preserve after approval

- Intended outcome: Install Hermes from scratch on a new Fedora Server 44 VM; verify the manual gateway and
  isolated worker with native DeepSeek V4.1 Flash and Telegram; retain the encrypted VM shut down with sanitized
  evidence.
- Approved scope: Preflight, create `lab-hermes-deepseek-e2e-r1` with 2 vCPUs, 12 GiB RAM, 120 GiB sparse disk,
  `fvh-nat`, UEFI Secure Boot and vTPM 2.0; extend the manual profile's model, credential provisioner, checks and
  guide; interactively install Fedora with LUKS and dedicated `/home/hermes`; execute the documented manual
  profile, acceptance, recovery and cold-start checks; revoke dedicated test credentials on a pass.
- Out of scope and constraints: Do not touch `lab-hermes-manual-r1` or production. Preserve the new guest after
  failure. No production deployment, commit or push. Never record credentials or passphrases; enter them only
  through private prompts. Provider probes are bounded, with no load test. A VM boot cannot certify physical
  firmware, TPM, wall power or production behavior. Dependent gates stop on failure.
- Acceptance criteria: Offline, lint, extension, manifest, secret-scan and diff gates pass; fresh Fedora, encrypted
  unattended cold boot, manual profile, DeepSeek reply and worker tool roundtrip, Telegram positive and negative
  cases, isolation, backup/restore, SELinux/systemd and post-reboot recovery pass; shut down and retain the VM;
  revoke dedicated credentials through trusted interfaces.
- Approval reference: User supplied and requested implementation of the fresh Hermes VM end-to-end plan in this
  conversation. The subsequent user message explicitly changes the Hermes version requirement to the latest
  release.
- Authorized actions and boundaries: New VM lifecycle, bounded test credentials/provider calls, test credential
  revocation, and repository implementation/checks are authorized by the plan. External production writes,
  destructive cleanup of existing VMs, commits and pushes are not.

## Tasks and gates

| ID | Task and dependencies | Progress | Gate and expected result | Gate status | Evidence / next action |
| --- | --- | --- | --- | --- | --- |
| H01 | Host/media/repository preflight; none | ✅ DONE | Read-only inventory, Fedora signature/hash, capacity/network/identity absence; all pass | ✅ PASS | Signed media and host inventory below |
| C01 | Latest Hermes/DeepSeek manual profile and VM helper; none | 🔄 IN_PROGRESS | Pinned current release/image supports native DeepSeek; offline/lint/extensions/manifest/scan/diff pass | ❌ FAIL | v0.21.5 resolution and destination tests pass; repository lint fails on pre-existing Gate 2 files, migration manifest is stale, full shared entrypoint not run under Hermes-only boundary |
| V01 | Create fresh retained VM; H01 and helper checks | ✅ DONE | Exact resources, identity collision checks and domain/disk attestation pass | ✅ PASS | Exact identity and idempotent rerun below |
| I01 | Install Fedora interactively; V01 | ✅ DONE | Fedora 44, Secure Boot, LUKS and separate `/home/hermes`, recovery access pass | ✅ PASS | Corrected layout, private passphrase check, key-only SSH; VNC console account login unverified |
| X01 | Temporary no-password test access; I01 | 🔄 IN_PROGRESS | Exact VM binding, root-owned host/guest wrappers, `visudo`, allowed/rejected operations, sanitized logs and teardown pass | ❌ FAIL | Host and guest grants, allow/reject checks and audit passed; final teardown remains |
| B01 | TPM unlock and cold boot; I01 | 🚧 BLOCKED | Recovery first; no-input shutdown and cold start pass | ❌ FAIL | TPM token wiped, but passphrase check failed; keep VM running and recover before any shutdown |
| M01 | Manual profile and provider tests; B01 and C01 | ⬜ TODO | Ordered M01–M05, gateway/worker, exact reply, tool roundtrip and failure cases pass | ⬜ NOT_RUN | Wait for B01/C01 |
| T01 | Telegram and recovery; M01 | ⬜ TODO | Delivery, allowlist/negative cases, backup/restore, SELinux/systemd and post-reboot checks pass | ⬜ NOT_RUN | Wait for M01 |
| F01 | Final state and revocation; T01 | ⬜ TODO | VM shut down and retained; test key/token revocation independently verified | ⬜ NOT_RUN | Wait for T01 |

## Evidence history

- 2026-09-23 22:16 UTC: Baseline recorded before implementation. Destination checkout was clean at
  `ef3fc9c4efe1adbf7631ce96be203871e9c6c75f` on `hermes/hermes-repository-migration`; feature branch
  `codex/hermes-deepseek-e2e-r1` created. Source MikroTik checkout has unrelated dirty work and is not a target.
- 2026-09-23: Official Hermes releases page identifies v0.21.4 (`v2026.9.21`) as Latest. The immutable OCI
  index is `sha256:6bece0644e29a347e5ae17db43c36938c86f171c6f5e0cef18aa2075d331f3a3`, amd64
  child is `sha256:4c06bddbcdc164e7ab019c137326990767be79b0f8c90db73d9bce2f3d3e64aa` and source
  revision label is `d337b736aa1e8ebecfab043842d13e4a2d2f48a3`. The exact pinned image resolved
  `deepseek` / `deepseek-flash`, `DEEPSEEK_API_KEY`, `https://api.deepseek.com/v1` and `chat_completions`
  with a synthetic key and network disabled. No live provider call has run.
- H01: Fedora Server 44 1.7 ISO signed checksum verified with the Fedora keyring and `gpgv`; the ISO SHA-256
  was `85837793bfa36db6bc709b4cecd2ec116951b87d9c53c3d95eb2fac8dcf7cf1f`. Host inventory was 16
  CPUs, about 25 GiB available RAM and 236 GiB free in the default libvirt pool. `fvh-nat` was active; only
  the prior `lab-hermes-manual-r1` domain existed. The user confirmed the documented sudo-password rotation.
- V01: Created only `lab-hermes-deepseek-e2e-r1`, UUID `4349a2bc-67b6-42b7-a6ef-5aeee5ee4009`, MAC
  `52:54:00:83:bf:4b`; the domain has 2 vCPUs, 12288 MiB RAM, 120 GiB sparse qcow2, `fvh-nat`, secure UEFI
  with enrolled keys and emulated TPM 2.0. Initial creation did complete, but the helper's post-create
  `qemu-img info` failed because running QEMU held the write lock. The helper was corrected to inspect the
  active disk with `qemu-img info -U`. Its `--verify` then passed and a `--create` rerun returned
  `create=UNCHANGED` with the exact same identity and disk. The guest is retained and running the installer.
- 2026-09-23: User clarified repository inputs must resolve relative to each script; absolute libvirt
  storage and guest paths may be discovered or supplied at runtime. The VM helper was revised to discover
  the libvirt pool path and resolve relative media against its repository root. The user directed the agent
  to perform the installation and validation; operator interaction is limited to private credential prompts.
- C01: Manual profile now pins the v0.21.4 image throughout gateway scripts and Quadlet, accepts native
  `deepseek` / `deepseek-flash`, provisions `DEEPSEEK_API_KEY` through a hidden prompt and redacts it from
  diagnostic output. The model setter leaves a converged file unchanged. The paid acceptance calls write
  an attempt receipt before either call, skip replay after success and require an explicit force flag to
  retry an incomplete attempt. The VM helper's `--create` rerun returned `UNCHANGED`; a guest credential
  rerun and a paid-probe rerun have not yet been exercised live.
- C01 checks: the first offline run failed only the duplicate model setter identity rehearsal; syncing
  `scripts/hermes/set-model.py` with the manual copy corrected it. The first lint rerun found one long
  guide line, and the later lint rerun found formatting under the repository's exact shfmt flags; both
  were corrected. Final full offline checks passed, including 386 manual-profile assertions, 140
  ShellSpec examples, 486 reviewed Python tests, clean-install rehearsal, full working-tree secret scan
  and source-aware migration manifest verification (363 rows). Check-only lint, extension validation and
  `git diff --check` passed. The manifest payload fingerprint was
  `0fcc7135f1a8f4d84b2a8c9c99221eddd5a952c02d6567fe8277921b419f4031` before this record update.
- I01: Agent-driven Fedora installer selected only the new 120 GiB `vda`. The reviewed pending partition
  summary showed GPT, EFI, `/boot`, LUKS on `vda3`, a dm-crypt mapping and LVM PV inside it. The proposed
  LVs are XFS `/` 35 GiB, XFS `/var` 30 GiB, XFS `/home/hermes` 40 GiB and encrypted swap 8 GiB, with
  about 4.4 GiB free in the VG. The LUKS passphrase was entered twice through private desktop prompts;
  no value was captured in evidence. Root login is disabled and `aicowork` in `wheel` is configured.
  The administrator password was entered and confirmed through private desktop prompts; the installer
  accepted the account and completed the Fedora installation. First boot, mounted layout, LUKS version
  and recovery access remain unverified.

- 2026-09-24 I01 first-boot failure: Fedora 44 booted after private LUKS entry; `aicowork` console login and
  key-only SSH to `192.168.124.5` passed, and the SSH host key matched the console fingerprint
  `SHA256:+AYjgSf8+CHdL96w909wjrG1talAfekFfwf43EfdgcY`. SELinux was Enforcing and `/home/hermes` was a
  separate XFS LV. `lsblk` exposed a second LUKS container on `vda4` for swap and no reserve in the main VG;
  this violates the single-parent encrypted LVM layout required by the manual guide and blocks TPM enrollment.
  No TPM or Hermes deployment was attempted. The VM was gracefully shut down, the failed installation was
  retained in qcow2 snapshot `pre-layout-correction-20260924`, and the signed ISO copy was rechecked against
  SHA-256 `85837793bfa36db6bc709b4cecd2ec116951b87d9c53c3d95eb2fac8dcf7cf1f` before a corrective
  installer boot. The private VNC helper also lacked Shift synthesis for some characters; it was corrected
  before any new passphrase is entered, and recovery credentials must be reverified after reinstall.
- 2026-09-24 VM helper correction: `--finalize` initially failed because the active CD-ROM had the ISO while
  the persistent definition was already empty. It now inspects both states and ejects each independently;
  the live eject passed and an immediate rerun returned `FINALIZE=UNCHANGED`. Repository gates must rerun
  after this helper change.

- 2026-09-24 I01 corrective install: The agent reinstalled Fedora 44 from the verified signed ISO on
  only the new VM disk. The running guest has EFI 600 MiB FAT32, `/boot` 2 GiB XFS, and one LUKS2
  `vda3` (117.4 GiB) containing the `fedora` VG: linear XFS root 35 GiB, `/var` 30 GiB,
  `/home/hermes` 40 GiB, swap 8 GiB, and 4.39 GiB free extents. `findmnt` confirms a distinct
  `/home/hermes` mount; SELinux is Enforcing, cgroup v2 is present, Secure Boot is enabled, and
  `/dev/tpm0` exists. `aicowork` is in `wheel`; pinned host-key, key-only SSH and private sudo
  access pass. The new SSH host fingerprint is
  `SHA256:jJHOZL7RV7Cqw0QI8DpUuXe7Hn/NdCTgv3D2hQBUU5Q`; the new machine-ID SHA-256 is
  `f8c01e74f672760c10bdbc91023d98ff5173bb9652da1d6e3d2c4cba00d00682`. An independent
  `cryptsetup open --test-passphrase` check passed using private dialogs. Its first piped-input
  attempt failed because a trailing newline became part of the key file; the corrected exact-length
  input passed. The installer media was ejected from active and persistent definitions, with a
  subsequent `--finalize` returning `UNCHANGED`. VNC console account login attempts did not pass;
  LUKS boot entry and remote administrator recovery succeeded. Keep this limitation explicit.
- 2026-09-24 B01 recovery prerequisite: Pre-TPM LUKS header, crypttab, and VG metadata were
  archived outside the guest at
  `/var/home/aicloudopspecial/.local/share/hermes-recovery/lab-hermes-deepseek-e2e-r1/pre-tpm-recovery.tar`
  (16,783,360 bytes, SHA-256 `63b0c072fc9fccec110e54fe3f73be0c3fb2e7c4be67cc49fa667b22e9cc9060`).
  The host destination is Btrfs on a LUKS mapper. Its directory is mode 0700 and archive mode 0600.
  This is off-guest encrypted storage, not a removable offline copy. The first failed install remains
  available as the qcow2 snapshot `pre-layout-correction-20260924`.

- 2026-09-24 B01 staging: The full manual bundle was staged under `/home/aicowork/hermes-manual`
  through the pinned SSH host key using checkout-relative `tar -C scripts/hermes/manual`. The guest copies
  of `boot/tpm-enroll.sh` and `lib-manual-common.sh` matched source SHA-256 hashes
  `7e29f6c5bdad8cf78812fd78d5a307f6dfe4c3dfcd908c15e50b3558f129b3fd` and
  `14d78ce4230590c84f0dae64935ce27eb8f3359cfdef6c7ee42e7022ad655d4f`. After the Telegram
  convergence edit, its staged script matched source SHA-256
  `4cd862d14fb5dcd5a1d753d0364a1e6b076552fdfd8504ada94ed1da0b80ba17`. The saved domain
  boot order was restored from temporary `cdrom,hd` to `hd` after reviewing a one-line XML diff;
  `virsh define --validate` and VM identity attestation passed. No guest reboot has yet followed.
- 2026-09-24 C01 revalidation: Telegram provisioning now preserves an unchanged `.env` on rerun.
  The full offline suite passed again (386 manual-profile assertions, 140 ShellSpec examples, 486
  reviewed Python tests, clean-install rehearsal, full secret scan and source-aware manifest).
  Check-only lint, extension validation and `git diff --check` passed. The latest GitHub release API
  still reported v0.21.4 (`v2026.9.21`). A live Telegram credential rerun has not yet been tested.
- 2026-09-24 B01 access work: Two temporary PTY root-shell wrapper attempts did not reach their ready
  marker; neither stored the sudo password. Credential-free SSH PTY and pipe controls passed. A new
  non-PTY root-shell attempt is waiting on one private KDE dialog. The proven one-command private
  sudo path remains available; no TPM mutation, application deployment or paid provider call occurred.

- 2026-09-24 safe stop: The non-PTY root-session wrapper waited on the private KDE password dialog;
  no password entry completed during this run. The dialog was closed without receiving or storing a
  password. No TPM token enrollment, cold-start certification, Hermes service deployment, provider
  call or Telegram test was attempted. The new VM received a graceful libvirt shutdown and reached
  `shut off`; its saved boot order is `hd`, and both the new and prior VM definitions remain present.
  The encrypted guest disk, failed-install diagnostic snapshot and off-guest recovery archive are
  retained. The host root shell was closed. Resume at B01 with a private guest sudo authentication,
  then run the boot-helper preflight; later gates remain dependent on B01.

- 2026-09-24 B01 resumed: The host archive SHA-256 and restrictive permissions still matched the
  recorded recovery evidence. Only `lab-hermes-deepseek-e2e-r1` was started; its UUID, sparse disk,
  hard-disk boot order and empty CD-ROM were re-attested. The prior VM stayed shut off. The verified
  LUKS passphrase unlocked Fedora through a private KDE prompt, and pinned key-only SSH reached
  Fedora 44 with a separate XFS `/home/hermes` mount. The new boot ID is
  `fdf53f98-e6fb-4f20-8751-a4170f8f741c`; machine-ID SHA-256 remained
  `f8c01e74f672760c10bdbc91023d98ff5173bb9652da1d6e3d2c4cba00d00682`.
  `mcelog.service` alone is failed because the VM's AMD CPU is unsupported by mcelog, a known
  hardware-diagnostic limitation recorded in the canonical ledger. SELinux remains Enforcing.
- 2026-09-24 B01 preflight: With `HERMES_EXPECT_UUID` and the reviewed machine-ID hash pinned, the
  staged `boot/tpm-enroll.sh --preflight` resolved `/dev/vda3`, the expected mapper and root LV;
  reported one LUKS2 passphrase slot, zero TPM tokens, one matching crypttab record, Secure Boot
  enabled and both TPM device nodes. It ended `PREFLIGHT=OK` without enrolling or regenerating an
  initramfs. The helper's prior generic final line had falsely claimed regeneration in preflight;
  it was corrected, and the corrected staged copy (SHA-256
  `7cbab5f0e79fe734cf4b9ca24cf78027dcbebd0ac6d08dab6b3475b8055ab2e0`) passed the same
  live preflight with `RESULT=PASS - preflight only; no TPM or initramfs change`. Enrollment reruns
  now verify an existing PCR7/SHA-256 token, crypttab and current initramfs before returning
  `ENROLL=UNCHANGED`; partial or differing states fail closed. Repository gates are stale after this
  source and guide change and must rerun before enrollment.

- 2026-09-24 B01 first enrollment attempt: After repository offline, lint, extension, manifest,
  secret-scan and diff gates passed for the corrected TPM helper, the pinned `--enroll --apply` run
  used private guest sudo and LUKS dialogs. `systemd-cryptenroll` returned 0, yielding two LUKS2
  keyslots and one TPM2 token. The passphrase slot retested successfully, crypttab gained
  `tpm2-device=auto`, and `dracut -f` returned 0. The required initramfs check found zero
  `tpm2` or `systemd-cryptsetup` entries, so the helper exited 1 with
  `ENROLLMENT_VERDICT=FAIL`. No reboot or application work followed this failed gate.
  The post-enrollment staged header and pre-enrollment crypttab were archived in the encrypted
  hypervisor home as `post-tpm-staged.tar` (16,783,360 bytes, SHA-256
  `0bd7a5bed3fb9dd693f61abd6c9d4cfc46798ed028495d5c33f696e15ac20d7a`), and a second
  copy attempt returned `UNCHANGED`. The guest remains running and unlocked.
- 2026-09-24 B01 diagnosis: The current-kernel initramfs is 41,643,801 bytes (SHA-256
  `189acd91c8d84485445316448b9eca880ca8c1e0599c49daacdf04e519a8b77c`) and `lsinitrd`
  lists the legacy `crypt` module but no `systemd-cryptsetup` or `tpm2` path. The token metadata
  confirms PCR7 from SHA-256 with no PIN. The installed dracut `73tpm2-tss` module requires the
  absent `tpm2` binary; signed Fedora offers `tpm2-tools`. Dracut also has an available
  `11systemd-cryptsetup` module and the guest has the systemd cryptsetup binary, but that module
  was not selected in the host-only image. The guide's Phase 5 lists `tpm2-tools` after the
  Phase 4 TPM gate; its order must be corrected. Verify the package transaction, install only
  the needed signed prerequisite, persist module selection for later kernel builds, rebuild
  and recheck the initramfs before any reboot.
- 2026-09-24 continuation: The operator reported `lab-hermes-deepseek-e2e-r1` shut off. The
  manual deployment guide now gives the existing-token repair path: confirm recovery material,
  install the signed TPM tool prerequisite, persist both dracut modules, rebuild and inspect the
  current-kernel initramfs, and require `ENROLL=UNCHANGED` before boot proof. No guest mutation
  or cold boot has run in this continuation. The operator was asked to start and unlock only this
  VM through a private passphrase prompt. The destination-only manual-profile and guide checks
  passed (395 and 220 assertions); check-only lint failed on three existing Gate 2 lab scripts'
  shfmt formatting and 24 line-length findings in the Gate 2 access record. The combined offline
  entrypoint includes source-checkout provenance, so it was not run under the operator's new
  Hermes-only repository boundary. The full reviewed working-tree secret scan found no secrets,
  and declared extension/profile verification passed (ShellSpec 0.28.1, locked Ruff 0.16.8,
  ty 0.0.82 and yamllint 1.38.0). `git diff --check` passed. These checks are not application
  or VM boot acceptance.
- 2026-09-24 boot observation: The operator started the exact VM and reported Fedora reached the
  OS without a LUKS prompt. Read-only libvirt `domstate` returned `running`; the `fvh-nat` lease
  for recorded MAC `52:54:00:83:bf:4b` was `192.168.124.5`. An ED25519 host key fetched from
  that address matched the recorded post-reinstall fingerprint
  `SHA256:jJHOZL7RV7Cqw0QI8DpUuXe7Hn/NdCTgv3D2hQBUU5Q`. An available lab SSH key was
  rejected; no guest command ran through SSH. Workstation `sudo -n` required a password, so
  no guest-agent command ran from the agent. A fixed-identity, read-only guest-agent inspector
  was added at `scripts/hermes/manual/lab/deepseek-boot-inspect.py` and is awaiting the
  operator's private workstation sudo run. Its three mocked authorization/identity tests,
  Ruff check and format check passed. The boot observation is encouraging, but B01 remains
  FAIL until the current initramfs, token, fallback path and repeat cold start are verified.
- 2026-09-24 first guest-agent inspection: The operator's private host-sudo run returned
  `STOP: guest identity mismatch`. The inspector did not print or accept boot metadata from
  that run. Its error now reports only the observed guest username, hostname and machine-ID
  hash, bounded to 300 characters; focused mock tests and Ruff checks pass after the edit.
  Await that identity readback before changing a pin or inferring a TPM result.
- 2026-09-24 identity readback: Guest agent ran as root and returned the recorded machine-ID
  SHA-256 `f8c01e74f672760c10bdbc91023d98ff5173bb9652da1d6e3d2c4cba00d00682`, but
  `/etc/hostname` was empty. The inspector now accepts only an empty hostname or the expected
  domain hostname in addition to the unchanged UUID, MAC, root user and machine-ID pins;
  four focused tests and Ruff check pass. A repeat read-only inspection is pending.
- 2026-09-24 read-only boot report: The exact running guest reported boot ID
  `80155c7e-01a8-4f60-abf4-2faacc05ee5a`, kernel `6.19.10-300.fc44.x86_64`, and both
  `systemd-cryptsetup` and `tpm2-tss` in that kernel's initramfs. One crypttab record has
  `tpm2-device=auto`; root is `/dev/mapper/fedora-root`. The report's `tpm2_tokens=0` came
  from a fragile human-readable `cryptsetup luksDump` pattern and conflicts with the earlier
  JSON token evidence; it is not accepted as a token finding. The inspector now parses LUKS
  JSON metadata for token count, keyslot count and PCR7/SHA-256/no-PIN policy. Five focused
  tests, including execution of the embedded guest JSON parser with synthetic metadata,
  Ruff check and format check pass. A corrected read-only token report is pending.
- 2026-09-24 access and new operator constraint: A follow-up JSON-metadata guest-agent probe
  returned exit 1; the inspector now exposes at most 500 characters of stderr from its fixed
  read-only command, and six focused tests plus Ruff checks pass. The operator then required
  installation, deployment and testing without further sudo-password requests. This session's
  `sudo -n -l` and `sudo -n virsh ... guest-ping` both returned `a password is required`;
  direct guest-agent access timed out after eight seconds. No password-free grant exists for
  this DeepSeek VM in the current session. No further privileged guest or lifecycle operation
  has run. The next live root step requires an independently established, narrow privilege
  path; a workstation password will not be stored or requested by this continuation.
- 2026-09-24 final Hermes-only source checks: The inspector's six focused tests, Ruff check
  and format check passed. The active guide and this plan passed focused Markdown lint;
  `git diff --check` passed. The reviewed full working-tree secret scan reported no findings
  across 371 tracked and untracked files. The repository-wide check-only lint still has the
  previously identified Gate 2 script formatting and access-record line-length findings;
  source-aware migration verification was not run under the Hermes-only constraint.
- 2026-09-24 X01 approved access preparation: `scripts/hermes/manual/lab/deepseek-test-grant.py`
  defines five fixed host and 24 fixed guest operation IDs, separate exact-command sudoers
  rules, one private host-root bootstrap, a root-owned installed host/guest copy, a SHA-256
  pinned root-owned manual bundle, and a dedicated temporary SSH key outside the repository.
  The bootstrap binds the domain UUID/MAC/network/lease, guest machine-ID and ED25519 host-key
  fingerprint before installing guest access. The key uses `restrict,pty,from=` so private
  credential prompts can work while forwarding remains disabled. Final teardown removes
  guest access first, shuts off the exact VM, then removes host access and the dedicated key.
  `check` validated both generated sudoers rules with `visudo`, both embedded guest scripts'
  syntax, and the archive path/type constraints. Seven focused grant tests passed; they include
  UUID/MAC/lease and archive rejection. The host bridge's live IPv4 address was
  `192.168.124.1/24`, matching the key's source restriction. No grant has been installed
  and no live positive/negative authorization test has run yet.
- 2026-09-24 X01 source gates before bootstrap: Manual profile 395/0 and guide 220/0 passed;
  the two DeepSeek-focused unittest modules ran 13 tests/0 failures. The grant's `check`
  validated five host and 24 guest operations and a bundle with SHA-256
  `5fff416b344e5289d84e9ebcb6cdd456f9c5910c4c59086759801ae67d95c2af` at that
  source snapshot. Ruff check/format, focused Markdown lint, full reviewed working-tree
  secret scan (373 files, no findings) and `git diff --check` passed. The grant source SHA-256
  before the final SSH-state hardening edit was
  `08ace68c906d2173230307580544755932c122517efca94b6af829f5579f92f5`; rehash and
  rerun `check` before installation. A direct read-only libvirt state call timed out in the
  current session; the installer itself requires the VM to be running and verifies its
  identity and lease before any guest grant write.
- 2026-09-24 X01 final source review: The guest bundle now excludes `lab/` privilege tools;
  staging installs its hash marker before publishing the root-owned tree so an interrupted
  install can converge on rerun. The guest-agent operation wait is 30 seconds, and fixed
  bootstrap, bundle install, helper and cleanup actions log operation IDs without credential
  material. The fixed guest allowlist includes the Telegram allowlist and worker negative-test
  states (29 guest IDs total). Fourteen focused tests passed, including the bundle exclusion.
  Generated host and guest sudoers syntax passed `visudo`; the pinned manual bundle SHA-256 is
  `28f668d12ecf01c198083ec1ae95d84771432898b99b5e580518613beaffec89`.
  Ruff check and format check, focused Markdown lint, full working-tree secret scan
  (373 files, positive control and no findings), and `git diff --check` passed inside the
  Hermes Toolbox. The reviewed installer source SHA-256 is
  `d919b163dfe89367c02ef2d8feec7133431ab8e675b5181f08bd938146fbd54e`.
  No host or guest grant has been installed; positive and rejected live commands,
  idempotent bootstrap, journal entries and final teardown remain unverified.
- 2026-09-24 X01 first live bootstrap: The operator's first command split the filename at
  `deepseek-test-`, so no installer ran. A corrected invocation passed offline `check` but
  stopped in the read-only guest identity step when guest-agent Python failed while reading
  `/etc/ssh/ssh_host_ed25519_key.pub`; the bounded traceback did not include the final OS
  error. This step precedes all grant writes, and the host rule remained absent. A direct
  read-only `ssh-keyscan` of `192.168.124.5` returned the previously pinned ED25519
  fingerprint `SHA256:jJHOZL7RV7Cqw0QI8DpUuXe7Hn/NdCTgv3D2hQBUU5Q`. The installer now
  checks guest root and machine ID with QGA, and independently verifies the network SSH
  host key against that fingerprint before installing any grant. Sixteen focused tests,
  generated sudoers validation, Ruff check/format, full working-tree secret scan
  (373 files, positive control and no findings) and `git diff --check` passed. The pinned
  manual bundle hash remains
  `28f668d12ecf01c198083ec1ae95d84771432898b99b5e580518613beaffec89`; current
  installer source SHA-256 is
  `86fd61be24ab08106c236a2d446003b6987c671659aa83529cb0474a555af47f`.
  Rerun only the corrected private bootstrap; no VM test gate has advanced.
- 2026-09-25 continuation, America/Bogota: Official GitHub latest-release API now identifies
  v0.21.5 (`v2026.9.24`), published 2026-09-24 UTC, superseding the C01 image pin. Public
  registry metadata resolves the tag to OCI index
  `sha256:fca358f12efd65bfaaca05884166f15c0e2788375ca30d77061ac1ebc96452b7`,
  amd64 manifest `sha256:2fd023efbb8d3d2b0ce1a73d028b07370cff34f567cfe0e999553e8c327ea283`,
  and revision label `f97608f178d1ffeca59860195ab7da295f7c8e5f`, matching the release
  description. This is metadata corroboration, not signature verification or runtime acceptance.
  A read-only `virsh domstate` reports the exact VM `shut off`. The previous bootstrap left
  root-owned host helper, inspector and bundle files matching the reviewed source and previous
  bundle hash, but `sudo -n` for its fixed status operation still requires a password.
  Root access is unavailable without a password request, which the operator prohibited.
  The X01 positive/negative tests and guest grant state remain unverified. Continue C01
  independently; do not infer B01 from the earlier no-prompt observation.
- 2026-09-25 C01 refresh, America/Bogota: The manual profile scripts, Quadlet, manifest and
  current guide now pin v0.21.5 by the verified OCI index above. The release's provider guide
  still names native `deepseek` and `DEEPSEEK_API_KEY`. The exact index pulled into the user
  image store and reported packaged version 0.21.5. A network-disabled Podman run with only
  the synthetic `DEEPSEEK_API_KEY=synthetic-resolution-only` resolved `deepseek-flash` to
  provider `deepseek`, base URL `https://api.deepseek.com/v1` and `chat_completions` mode;
  `native_deepseek_resolution=PASS`. No real provider credential or call was used. Recheck the
  latest release and immutable digest immediately before M01 deployment.
- 2026-09-25 C01 destination checks, America/Bogota: In `dev-infra-hermes`, manual-profile
  assertions passed 395/0, guide assertions 220/0, DeepSeek-focused Python tests 16/0,
  ShellSpec 140/0, and reviewed offline Python suites 486/0. The remaining offline manual
  review, backup, configure, contract, M01 temporary-state and clean-install rehearsal
  commands all exited 0; the rehearsal ended `REHEARSAL=PASS`. Declared extensions passed
  (ShellSpec 0.28.1, locked Ruff 0.16.8, ty 0.0.82, yamllint 1.38.0). Focused Ruff and
  Markdown checks passed. The full working-tree secret scan covered 373 files and found no
  secrets; `git diff --check` passed. These checks cover the current dirty and untracked
  destination tree, not guest deployment or provider behavior.
- 2026-09-25 C01 remaining checks: Repository check-only lint failed solely on the three
  pre-existing Gate 2 lab scripts' shfmt differences and 24 line-length findings in the
  separate Gate 2 access plan. Source-aware migration verification was not run because the
  recorded operator boundary is Hermes-only. Destination-only `--verify` failed because
  `docs/migration-manifest.txt` predates several untracked DeepSeek files and current edits;
  its payload and inventory identities are stale. The combined `toolbox/run-offline-checks.sh`
  was therefore not run. Direct generic yamllint also reported existing long digest/comment
  lines in `manifest.yaml`; the repository's `check-yaml` hook passed. The partial root-owned
  host copy contains bundle SHA-256
  `28f668d12ecf01c198083ec1ae95d84771432898b99b5e580518613beaffec89`, while the
  refreshed source bundle's offline `check` passes with SHA-256
  `5f50714513b98005a02d6f111db4e074c50f1e640fc6edafd2f2dc69c9aae068`.
  Its dedicated state lacks `known_hosts`; guest-side grant
  state is unknown. Do not rerun `install` against that partial state without exact-VM
  privileged inspection and reconciliation.
- 2026-09-25 X01 retry preparation: The operator allowed one private workstation bootstrap
  prompt and retained the Hermes-only cross-repository boundary. `start-install` now verifies
  the pinned domain before starting it and waits for the pinned lease, guest machine-ID and
  SSH host key. Its known-partial recovery accepts only the exact previously recorded
  root-owned host helper and bundle bytes, requires the guest grant inventory to be absent,
  and otherwise fails closed. Fourteen focused grant tests, generated sudoers validation,
  Python syntax, Ruff check/format, focused guide Markdown lint and `git diff --check`
  passed before the live retry. This source change does not alter the pinned guest bundle.
- 2026-09-25 X01 one-prompt live retry: KDE `ksshaskpass` supplied the workstation password
  directly to `sudo -A`; no value entered chat, argv or repository files. The script
  attested the exact domain, started only `lab-hermes-deepseek-e2e-r1`, and passed the pinned
  network, root guest machine-ID and SSH host-key checks. A read-only guest inventory found
  no guest grant artifacts, so the exact old host copy was reconciled. The host now holds
  root-owned `access.py` SHA-256
  `e9fffae62535e3714c4d406f3359c41218d9e6d9411e98bc84ad8c82e638fd39` and
  bundle SHA-256 `5f50714513b98005a02d6f111db4e074c50f1e640fc6edafd2f2dc69c9aae068`.
  Guest-agent Python then ran as root but failed with `PermissionError` creating
  `/usr/local/libexec/hermes-deepseek-test` at the first guest wrapper directory step.
  The cause is unverified; diagnose DAC, filesystem state and SELinux AVCs before changing
  a path or policy. The guest sudoers rule and dedicated SSH authorization were not reached;
  host sudoers publication was not reached. `sudo -n` for the fixed host status operation
  still requires a password and the dedicated `known_hosts` file is absent. A direct,
  authorized graceful libvirt shutdown completed; read-only `domstate` confirmed `shut off`.
  No TPM, application, provider or Telegram gate ran. The one private prompt is consumed;
  no further password prompt is authorized by this reply.
- 2026-09-25 X01 read-only diagnosis prepared: The fixed
  `scripts/hermes/manual/lab/deepseek-guest-permission-inspect.py` pins the reviewed grant
  source hash and checks the running VM UUID, MAC, lease, guest machine-ID and SSH host key
  before reading only the guest-agent process context, path ownership/modes/SELinux labels
  and read-only mount flags. Its offline `check`, locked Ruff check/format and
  `git diff --check` pass. It has not run against the guest; the VM remains shut off.
- 2026-09-25 post-failure destination checks: The affected guide passed 220/0 assertions;
  focused Markdown lint and locked Ruff check/format passed for the current guide and
  inspector. The DeepSeek-focused tests passed 20/0 after the bootstrap correction.
  The full working-tree secret scan covered 374 files with no findings before this
  evidence-line update; `git diff --check` passed. The repository-wide Gate 2 lint
  failures and stale migration manifest remain open.
- 2026-09-25 X01 read-only diagnosis, America/Bogota: The operator approved one more private
  workstation administrator prompt solely for permission inspection. A direct user-level
  `virsh start` timed out without a result, so the reviewed inspector was extended to
  attest, start, inspect and gracefully shut down only the exact VM within one authenticated
  command. Three focused lifecycle tests cover success, read failure and start timeout;
  locked Ruff and offline pin checks passed. The private KDE prompt succeeded. The script
  started `lab-hermes-deepseek-e2e-r1`, rechecked the pinned UUID/MAC/network, guest machine-ID
  and SSH host key, then reported guest-agent `euid=0` in SELinux context
  `system_u:system_r:virt_qemu_ga_t:s0`. `/usr`, `/usr/local` and
  `/usr/local/libexec` were root-owned mode 0755, labeled `usr_t`, and on a writable mount;
  `/usr/local/libexec/hermes-deepseek-test` was absent. The guest grant directory and rule
  under `/etc` were absent. The script requested graceful shutdown and reported
  `VM_FINAL_STATE=shut off`. These facts make a SELinux denial the leading explanation for
  the earlier `PermissionError`; a matching AVC has not been collected, so the cause is
  not confirmed. No SELinux policy, guest grant, TPM or application state was changed.
  The approved diagnostic prompt is consumed. A small offline inspector correction strips
  NUL terminators from SELinux context strings; this was not rerun live. After that edit,
  the affected guide passed 220/0 assertions, the inspector's three lifecycle tests and
  locked Ruff check/format passed, focused Markdown lint passed, and the full working-tree
  secret scan covered 375 files with no findings before this evidence-line update.
  `git diff --check` passed. The repository-wide Gate 2 lint findings and destination-only
  stale migration manifest remain open under the operator's Hermes-only boundary.
- 2026-09-25 X01 guest administrator access check, America/Bogota: The operator approved
  one private guest administrator prompt. No prompt has been used. Sandbox-level libvirt
  access returned `Operation not permitted`; a host-session read-only `virsh domuuid`
  timed out after ten seconds. Host-session `sudo -n` still requires a password, and
  `ssh-add -l` reports no agent identities. The only configured SSH identity is for
  GitHub; the available Hermes lab key was already rejected by this guest. The VM's
  live state could not be rechecked in this session; the last confirmed state was
  `shut off`. No guest command or VM lifecycle operation ran. The operator has been
  asked to start only this VM in virt-manager and provide the path to the private SSH
  key that previously reached `aicowork@192.168.124.5` after reinstall, or report
  that no working key is available. A path is sufficient; do not send key contents.
- 2026-09-25 X01 operator CLI handoff: The operator asked how to start the VM with
  `sudo` and CLI. The handoff provides fixed-domain `virsh domuuid`, `domstate`,
  `start` and final `domstate` commands, with the expected UUID and an instruction
  to start only from `shut off`. No output or completion has been received. The
  approved guest administrator prompt remains unused.
- 2026-09-25 X01 operator boot report, America/Bogota: The operator reported the
  exact VM `running` after the CLI handoff. A fresh public ED25519 SSH key scan
  of `192.168.124.5` matched the recorded post-reinstall host-key
  fingerprint `SHA256:jJHOZL7RV7Cqw0QI8DpUuXe7Hn/NdCTgv3D2hQBUU5Q`.
  The operator's libvirt UUID/state output has not been inspected by the agent;
  SSH login still awaits the working private key path. No guest command or
  private administrator prompt has run in this continuation.
- 2026-09-25 X01 SSH route and failed guest authentication, America/Bogota:
  The existing `~/.ssh/github-securexai` key reached `aicowork@192.168.124.5`
  with public-key-only login after the recorded ED25519 host fingerprint matched.
  Read-only guest checks found uid 1000, the pinned machine-ID hash, Enforcing
  SELinux, `aicowork` in `wheel`, an unconfined login context and no guest grant
  artifacts. Unprivileged `ausearch` could not read the audit log. The reviewed
  installer still passed its offline `check` with source SHA-256
  `e9fffae62535e3714c4d406f3359c41218d9e6d9411e98bc84ad8c82e638fd39`
  and bundle SHA-256
  `5f50714513b98005a02d6f111db4e074c50f1e640fc6edafd2f2dc69c9aae068`.
  The operator's one approved private guest prompt was used for a fingerprint-pinned
  SSH `sudo -S` invocation. Guest sudo rejected the entered password before the
  audit or bootstrap Python ran (`1 incorrect password attempt`). No password was
  printed or persisted by the orchestrator. A subsequent read-only guest inventory
  confirmed the guest wrapper directory, bundle pin, sudoers rule, staged archive
  and dedicated-key marker are still absent. No further guest prompt is authorized
  by that approval. A new guest authentication route is needed; the VM remains
  reachable by SSH and was not shut down by this attempt.
- 2026-09-25 X01 second private guest authentication, America/Bogota: The
  operator approved one more private guest administrator prompt. The reviewed
  source and bundle hashes, pinned SSH host key, guest machine-ID, Enforcing
  SELinux and absent guest grant were rechecked before the prompt. The KDE
  prompt explicitly named the `aicowork` password from the corrected Fedora
  install. Guest `sudo -S` again reported one incorrect password attempt and
  exited before the audit or bootstrap Python ran. This approval is consumed.
  After two rejected attempts, the agent stopped repeating the GUI-to-SSH
  method. A fingerprint-verified ED25519 host key was installed at the planned
  dedicated `~/.local/state/hermes-deepseek-test/known_hosts` path, mode 0600.
  A fresh pinned SSH inventory confirmed the guest wrapper, sudoers rule,
  bundle pin, staged archive and dedicated-key marker remain absent. The
  next diagnostic is a direct, private terminal `sudo` check inside the guest
  to distinguish a credential problem from the GUI-to-SSH handoff; it requires
  a separate operator decision because both approved prompts were consumed.
- 2026-09-25 X01 forgotten guest password, America/Bogota: During the direct
  terminal credential check, the operator reported they do not remember the
  `aicowork` sudo password. The agent directed them to cancel the prompt and
  avoid further guesses. No direct-terminal authentication result was reported.
  The existing Gate 2 helper and record show a separate retained test VM
  successfully used QEMU guest agent `guest-set-user-password` with a locally
  generated yescrypt hash; those prior results do not prove this VM can do so.
  The new fixed-VM
  `scripts/hermes/manual/lab/deepseek-guest-password-recovery.py` pins the
  reviewed grant source, VM UUID/MAC/network/lease, guest machine-ID and SSH
  host key, checks guest-agent command availability, and requires a private
  host-root terminal to enter a new password twice. Only the yescrypt hash is
  sent through the in-process libvirt API; no raw password is placed in argv,
  environment or files. Its offline `check` passed with the existing grant
  bundle SHA-256
  `5f50714513b98005a02d6f111db4e074c50f1e640fc6edafd2f2dc69c9aae068`.
  Seven focused safety tests, locked Ruff check/format, guide 220/0, focused
  Markdown lint and `git diff --check` passed. Recovery helper SHA-256 is
  `0709839eab59616d82125ba983f35448f550da93b50034355ff9f5e0435b04bc`.
  No password reset or further guest mutation has run; obtain explicit approval
  before rotating this guest credential. A successful guest-agent response
  will still require a fresh guest sudo authentication check.
- 2026-09-25 X01 password recovery approval and final preflight: The operator
  explicitly approved resetting only the retained DeepSeek VM's forgotten
  `aicowork` password through the prepared helper. The check-only recovery
  command, seven focused tests, locked Ruff check/format, guide 220/0 and
  Markdown lint passed. The full Hermes working-tree secret scan covered 377
  tracked and untracked files, its synthetic positive control passed, and it
  reported no findings. The live reset has not yet run; the operator will
  enter workstation sudo and the new guest password privately in a terminal.
- 2026-09-25 X01 password recovery operator result: The operator reported
  `VM_PASSWORD_CHANGE_ACCEPTED; verify with fresh guest sudo authentication`
  from the approved fixed-VM helper. This confirms the helper's QEMU guest-agent
  password command returned success; a fresh sudo authentication has not yet
  independently passed. No raw password or hash was received in chat. Continue
  with a single private authentication attempt and stop on rejection.
- 2026-09-25 X01 guest grant recovery and validation: The new password passed
  a fresh fingerprint-pinned SSH `sudo` call. The administrator process reported
  `unconfined_u:unconfined_r:unconfined_t:s0-s0:c0.c1023`; a same-day audit
  search reported no matching QGA AVC, so the earlier denial remains
  unconfirmed. The reviewed guest bootstrap printed `GUEST_GRANT_INSTALLED`.
  An independent dedicated-key `sudo -n` fixed `status` returned the pinned
  machine hash, and unrelated `true`, an extra argument and an unknown action
  were rejected after clearing the sudo cache. Guest `access.py` was root-owned
  mode 0644 with the reviewed SHA-256; the bundle pin was root-owned mode 0644.
  `sudo -n -l` showed only the generated fixed guest NOPASSWD command list.
  Guest journal entries for bootstrap and status contained only action/result
  fields. The pinned manual bundle staged with `BUNDLE=INSTALLED`; an immediate
  rerun returned `BUNDLE=UNCHANGED`. The host rule is still absent; X01 remains
  failed until host publication, host positive/negative checks and teardown.
- 2026-09-25 X01 host finalizer prepared: The new fixed-VM
  `scripts/hermes/manual/lab/deepseek-host-grant-finalize.py` pins the reviewed
  grant source and bundle hash, verifies exact libvirt and guest identity, the
  installed guest code/pin ownership and hashes, fixed status and sudo listing,
  and the exact root-owned interrupted host copy before publishing only the
  host sudoers rule. It avoids repeating the denied QGA guest write. Its
  offline `check`, six focused tests and locked Ruff check/format passed.
  Read-only guest-side finalizer checks passed over the dedicated SSH key with
  privileged host libvirt binding deferred; the root-owned host copy matched
  outside the sandbox. The exact host `sudo -n` status operation still requires
  a password. Helper SHA-256 is
  `18986feade4d24a5981aea832451f868f0a470a48d8deb729b784e63a3406dd8`.
  No host sudoers rule was written by this preparation. A new private
  workstation administrator prompt is needed for live host finalization.
- 2026-09-25 X01 host finalizer source gates: The updated manual guide passed
  220/0 assertions, the guide and execution record passed focused Markdown
  lint, and the full working-tree secret scan covered 379 tracked and
  untracked files with a passing synthetic positive control and no findings
  before this evidence-line update. `git diff --check` passed. These checks do
  not establish live host sudoers installation or VM boot acceptance.
- 2026-09-25 X01 live host finalization: The operator allowed one private
  workstation administrator prompt for the reviewed finalizer. It returned
  `HOST_GRANT_INSTALLED` with bundle SHA-256
  `5f50714513b98005a02d6f111db4e074c50f1e640fc6edafd2f2dc69c9aae068`.
  The finalizer verified the exact VM and guest identity, guest grant and bundle,
  root-owned installed host copy, host sudoers mode/content and `visudo` before
  publishing the rule. Fresh `sudo -n` host `status` returned the exact domain
  `running`. After `sudo -k`, unrelated `true`, an extra argument and an unknown
  action each exited 1 with `a password is required`; `sudo -n -l` listed only
  the five fixed host NOPASSWD commands in addition to the user's existing
  password-required general sudo access. The journal tag showed sanitized
  bootstrap and status entries. Direct unprivileged `stat` of the sudoers rule
  was denied by filesystem permissions, so its mode and `visudo` result are
  evidenced by the successful root finalizer, not an independent readback.
- 2026-09-25 B01 resumed: The installed host `inspect-boot` action failed before
  returning a report because QEMU guest-agent supplied a PATH that omitted
  `cryptsetup`; its embedded command used a bare executable name. The source
  inspector now calls `/usr/bin/cryptsetup`, but the pinned root-owned host
  copy remains the earlier bytes and has not been replaced. The fixed guest
  `boot-preflight` then reported `/dev/vda3`, two LUKS keyslots, one TPM2 token,
  one matching crypttab record with `tpm2-device=auto`, Secure Boot enabled and
  `PREFLIGHT=OK`. With that one-token state established, fixed `boot-enroll`
  took its existing-token convergence branch and returned
  `existing_tpm_policy=PASS`, both `systemd-cryptsetup` and `tpm2-tss` in the
  current-kernel initramfs, and `ENROLL=UNCHANGED`. The fallback wipe, private
  passphrase boot and repeat no-input cold start are still pending.
- 2026-09-25 source follow-up: The inspector's one-line absolute-path fix passed
  six focused tests and locked Ruff check/format; the corrected source SHA-256 is
  `50f2415182dfc3320c7f074d9bad484621b1e107958c418fb41e9531b81a0344`.
  The host finalizer's offline
  check still passed with the unchanged grant source and bundle. The updated
  guide passed 220/0 assertions, manual-profile checks passed 395/0, focused
  Markdown lint passed, and the full Hermes-only working-tree secret scan
  covered 379 tracked/untracked files with a passing positive control and no
  findings. These source checks do not refresh the installed inspector copy or
  complete the fallback boot gate.
- 2026-09-25 B01 fallback interruption: The operator ran the fixed guest
  `boot-fallback` action in a private terminal. It reported one remaining
  keyslot, zero TPM tokens and `crypttab_unchanged=yes`, but no
  `passphrase_slot=OK` or `WIPE=done`. The command exited 1. A bounded read of
  its guest-owned log found three `No key available with this passphrase`
  messages and `STOP: passphrase slot failed; restore the pre-enrollment header
  backup`. Its final `RESULT=PASS` was a source bug: the trailing verdict ignored
  the nonzero pipeline status. The exact VM remains running. Do not shut it
  down, reboot, or treat the printed PASS as proof of recovery access.
- 2026-09-25 B01 recovery inventory: Both encrypted-host recovery archives
  still exist with mode 0600 and match their recorded SHA-256 values:
  `pre-tpm-recovery.tar` and `post-tpm-staged.tar`. Only member names were listed;
  no LUKS header contents or credential values were read into the record. The
  repository `fallback-wipe.sh` now reports failure when its pipeline fails or
  completion markers are absent, and directs the operator to keep the guest
  running after a failed passphrase check. A focused rehearsal now executes
  the actual final verdict with synthetic failed-passphrase, missing-marker and
  completed-proof logs; all three cases passed, and the full clean-install
  rehearsal returned `REHEARSAL=PASS` with zero failures/advisories. Focused
  ShellCheck, shfmt, `bash -n` and `git diff --check` passed. A repeat fixed
  guest preflight still reported one keyslot, zero TPM tokens, one matching
  crypttab record with `tpm2-device=auto`, Secure Boot and a running guest.
  The installed root-owned bundle remains the earlier pinned copy; it has not
  been replaced. The local source bundle digest changed to
  `c863d6152ce6b56b7c35bd90badab229273e4bf1feeee754c5c0407eb5a5e752`,
  so source gates must be refreshed before any new bundle installation.

## Decisions and approved scope changes

| Date and timezone | Decision and reason | Approval reference | Affected tasks |
| --- | --- | --- | --- |
| 2026-09-23 UTC | Use the latest Hermes release at deployment time rather than the plan's pinned v2026.9.11; verify compatibility and immutable image identity before credentials | User: `install the latest hermes version` | C01, M01 |
| 2026-09-24 America/Bogota | Perform further test and deployment work without asking for a sudo password; retain private handling for other required credentials | User: `make all testing, deployment installation etc unattended without asking me sudo password` | B01, M01, T01, F01 |
| 2026-09-24 America/Bogota | Prepare one-time, exact-VM temporary access with separate host and guest grants, fixed root-owned operations, validation and shutdown cleanup | User approved the immediately preceding recommendation with `approved` | X01, B01, M01, T01, F01 |
| 2026-09-25 America/Bogota | Allow one private workstation bootstrap prompt; retain the Hermes-only boundary, so cross-repository provenance remains unverified | User response to two continuation questions | C01, X01 |
| 2026-09-25 America/Bogota | Allow one additional private prompt for the prepared read-only guest permission diagnostic | User response to continuation question | X01 |
| 2026-09-25 America/Bogota | Allow one private guest administrator prompt; guest login route must be established first | User: `Allow one private guest administrator prompt` | X01 |
| 2026-09-25 America/Bogota | Allow one more private guest administrator prompt after the first sudo rejection | User: `one more private guest administrator prompt` | X01 |
| 2026-09-25 America/Bogota | Reset only this retained VM's forgotten `aicowork` password using private workstation sudo and new-password terminal prompts | User: `Approve this VM password reset` | X01 |
| 2026-09-25 America/Bogota | Allow one private workstation administrator prompt for the reviewed fixed-VM host finalizer | User: `Allow one private host prompt` | X01, B01 |

## Handoff / closure

- Current outcome: Signed media, host preflight, retained VM creation, corrected Fedora install
  and private recovery check passed. The current v0.21.5 image passed credential-free DeepSeek
  resolution and destination offline tests, while repository lint and manifest gates remain open.
  The operator reported the exact encrypted VM running, and the pinned SSH host
  key and machine identity were reached after that report. The host and guest
  grants and pinned bundle now pass focused live allow/reject checks. The guest
  helper verified the existing TPM token's PCR7/SHA-256/no-PIN policy, crypttab
  and current initramfs; fallback and repeat cold-start proof remain unresolved.
- Remaining gates and blockers: C01, X01, B01, M01, T01 and F01 are pending. No raw credential values have
  been received in chat or printed by this workflow. Fixed password-free host
  and guest operations are active for the exact VM. The one newly approved
  private host prompt was consumed by successful finalization. The installed
  boot inspector remains the earlier bytes with the bare `cryptsetup` defect;
  use the verified guest helper for B01 until teardown or an authorized refresh.
  No application deployment, paid provider call or Telegram test has run. Later gates depend
  on B01 and C01.
- Material limitations: Historical passes belong to older artifacts and environments.
- Exact next action: Confirm which credential the operator entered at the
  `cryptsetup` prompt, without collecting its value. Keep the exact VM running.
  Establish a valid LUKS recovery passphrase through a private, identity-pinned
  path before any shutdown. If the passphrase is unavailable, review the
  matching post-enrollment header recovery route before a write. Resume the
  fallback boot only after recovery access is independently verified.
- Final state: ACTIVE — C01 lint/manifest gates failed; X01 final teardown pending; B01 recovery blocked
