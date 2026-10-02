# Portable Hermes production deployment on Fedora 44

<!-- markdownlint-disable MD013 -->

Record state: IN_PROGRESS — the unattended production path is implemented and proven in disposable Secure Boot + TPM2 VMs (runs r7/r8: install → commissioned → deployed in about 9.5 minutes, every local stage PASS, no secret typed). Off-host restore, real-credential application tests, fault automation, physical attestation and the production canary remain open; see [Approved scope change — unattended production path](#approved-scope-change--unattended-production-path-2026-10-01). Prior pet-VM qualification work (G03–G05) is STALE/superseded history; no production acceptance is claimed.

## Approved baseline — preserve after approval

- **Outcome:** Signed portable production deployment bundle using rootless Podman Quadlet, with a separate production Kickstart for fresh machines; the existing-server and fresh-server paths deploy the same qualified gateway/offline-worker artifacts and security contract.
- **Scope:** x86-64 Fedora Server 44, cgroup v2, SELinux enforcing, LUKS2-encrypted storage, dedicated XFS `/home/hermes`, UEFI Secure Boot and explicit SHA256 PCR7 TPM2 no-PIN automatic unlock. Keep DeepSeek/Telegram, terminal/file/memory/clarify only, manual approvals, strict transport identities, no worker network, no published ports or engine sockets, locked non-login non-administrative runtime account, subordinate IDs, read-only roots and resource limits. Do not imply protection against an intact stolen server or a compromised gateway/shared kernel.
- **Release:** Retained official gateway and worker OCI archives, exact source/config/image/package identities, OpenSSH-signed manifest under a distinct production identity, safe extraction before execution, local pinned signer trust, per-machine identities. Resolve the release at preparation; no floating tags or worker builds on production. Project signing is not upstream signature verification.
- **Host behavior:** Read-only preflight; require 8 GiB RAM, 20 GiB free `/var`, artifact/rollback/backup capacity, compatible packages/storage/boot/access and no conflicting resources. Preserve unrelated configuration/services/update policy; incompatible machines get a preparation report, never automatic repartitioning or encryption conversion. Production Kickstart uses verified Fedora media, explicit stable disk identity/sizing, encrypted linear LVM and private console secrets; the existing public-password lab Kickstart remains lab-only.
- **Commissioning:** One private phase may contain several interactions for firmware power restoration, known-good recovery passphrase, encrypted off-host recovery material, host fingerprint/machine binding, additive PCR7 enrollment, matching crypttab/initramfs modules, reboot/cold boot/recovery proof, application credentials and backup access. Thereafter a dedicated SSH forced-command/root-owned named-operation dispatcher provides unattended application operations without a general root shell. Credentials stay in the owner-only gateway profile on encrypted storage; no secrets in arguments, reports, releases, media or Git.
- **Interface/recovery:** preflight/bootstrap/deploy/status/verify/backup/upgrade/rollback, non-secret config, preview unless `--apply`, no interactive fallback, serialization, durable stages, unchanged reruns preserving identities/no unnecessary restarts, stopped-state backups, matching state/config/image rollback, retained failure evidence, encrypted off-host Restic and isolated restore rehearsal. Health checks are credential-free and do not make paid calls.
- **Acceptance:** Repository Toolbox offline/lint/link/secret/provenance checks; fresh install with unrelated disk preservation and no retained secrets; existing-host positive/negative preflight; actual config/process/SELinux/mount/network/SSH/canary parity; no-op/interruption/concurrency/corruption/missing-mount cases; update rollback and isolated backup restore; TPM/reboot/cold/recovery/re-enrollment proof; exact-candidate DeepSeek tool round trip, Telegram allow/reject and approvals; per-physical-target console/power recovery. Record stage timings and PASS/FAIL/BLOCKED/NOT_RUN/STALE without substituting synthetic evidence for runtime acceptance.
- **Delivery:** Save this record first; shared engine and production interface; guarded Kickstart/encrypted fixture; qualification; canonical operations runbook; then one specifically authorized production canary. Maintain patch/requalification and Fedora lifecycle guidance. Keep historical evidence/entrypoints intact. No automatic promotion, bootloader migration, additional providers or expanded tools.
- **Approval evidence:** User pasted the complete researched plan with “PLEASE IMPLEMENT THIS PLAN”, then “continue” after interruption. The selected choices were bundle + Kickstart, tested PCR7, current DeepSeek + Telegram, and private commissioning.
- **Authority:** Repository implementation and plan-scoped synthetic/encrypted qualification work are approved. No concrete production target or private credentials have been supplied; physical canary commissioning and real credential/provider operations remain gated. No commit, push, merge or PR change requested. Do not delegate without the user's explicit request under the supplied global agreement.
- **Initial provenance:** clean `main` at `3debb5ae22f91eb47c61daa30f1543d20456fec2`; required branch `codex/hermes-production-bundle` created. Initial sandbox branch creation was denied by filesystem access; the reviewed escalation succeeded. No implementation existed at interruption.
- **Record owner:** This file is the single execution record for this approved change. Older records remain historical.

## Tasks and gates

Review correction R2 baseline (user request, 2026-09-27): preserve serialization
while receiver children or mutating descendants survive dispatcher death, stop
both services after failed recovery and report stop failures, add real temporary
subprocess SIGKILL and recovery-retry regressions, rerun canonical Toolbox offline
and check-only lint gates, and refresh provenance/bundle evidence. This remains
repository review delivery only: no target contact, operational credentials or
Git delivery. G01/G02/G07, T01/T04 completion, and the R1 repository/bundle passes
below are STALE for these changes. Earlier evidence files remain immutable.
R2 is IN_PROGRESS; expected gates are focused real-process tests, both canonical
gates, a fresh retained-OCI package roundtrip, and preserved-evidence/provenance
verification. Exact next action: implement process-tree serialization and failed
recovery cleanup, then execute these checks with local temporary fixtures.

| Task | Outcome / dependencies | Progress | Gates | Exact next action |
| --- | --- | --- | --- | --- |
| T01 | Shared application engine, signed releases, production preflight and named-operation interface; none | ✅ DONE | G01/G02 | Namespace correction verified in repository scope; replacement candidate prepared. Actual runtime remains G04 |
| T02 | Guarded production Kickstart and encrypted qualification fixture; T01 | 🚧 BLOCKED | G03 | Restore full private hygiene validated PASS; qualification hygiene remains separately bound and pending |
| T03 | Transactions, backup/restore, boot/runtime/application qualification; T01/T02 | 🚧 BLOCKED | G04/G05/G06 | Recover the forgotten qualification administrator password privately after failed-prompt cancellation; then revalidate boot/runtime and prepare a watcher bound to that new boot before the one-attempt fault/recovery harness |
| T04 | Canonical runbook and complete repository verification; T01/T02 | ✅ DONE | G07 | Candidate executable checks remain current; private-receipt blocker and locally tested interruption-watcher evidence publication PASS within repository scope |
| T05 | One production canary; T01–T04 | 🚧 BLOCKED | G08 | Selected server 10.0.30.10/aicowork: approved physical boot/recovery commissioning complete; application canary awaits qualified artifact and explicit deployment authority |

| Gate | Method / expected result | Status | Latest evidence |
| --- | --- | --- | --- |
| G01 | Synthetic preflight/release/privilege/config tests reject invalid inputs before mutation and preserve secrets | ✅ PASS | 57 focused, 623 canonical Python and real SIGKILL/detached-writer regressions PASS; 11 private-bootstrap and 13 R2 interruption guards PASS; eight R1 guards retained |
| G02 | Shared lab parity and signed bundle roundtrip/tamper/replay/no-op regressions | ✅ PASS | Candidate `579403970f8225aea05866752e82e8800b3bac3f5abcf2cd892ffc9f52944295` signature/extraction and unqualified-production rejection PASS |
| G03 | Fedora44 Kickstart validation plus encrypted fixture installation, unrelated disk preservation, secret hygiene | 🚧 BLOCKED | Restore full hygiene receipt at 2026-09-30T14:48:46Z independently validated: all 12 files reviewed, known-value comparison PASS, saved Kickstarts absent; qualification fixture hygiene remains open |
| G04 | Real gateway/worker deployment, rerun, reboot, failed update, rollback and isolated Restic restore | 🚧 BLOCKED | Actual replacement runtime/rerun, seven fresh dispatcher rejection cases, signature corruption and failed-update recovery PASS; successful-update explicit rollback and application warm/cold boot PASS; current-candidate interruption/missing-mount and isolated restore require private setup; restore private dispatcher and actual named preflight/empty-state status PASS; isolated application restore remains NOT_RUN |
| G05 | Secure Boot/TPM PCR7/initramfs, automatic cold start and private recovery proof | 🚧 BLOCKED | Physical and qualification VM basic boot/recovery sequences PASS; restore TPM setup, automatic warm/cold boots, private recovery, cleanup and subsequent automatic boot PASS; TPM re-enrollment remains NOT_RUN |
| G06 | Exact-candidate DeepSeek/Telegram/approvals/canaries using private dedicated credentials | 🚧 BLOCKED | No private credentials or selected live-smoke inputs supplied |
| G07 | Toolbox offline gate, check-only lint, changed links, full secret scan, source-aware manifest and exact diff | ✅ PASS | Unchanged final-candidate executable inputs retain 623 canonical Python/140 ShellSpec; nine hygiene, eleven snapshot-watcher and fifteen restore-dispatcher guard tests PASS; fresh private-receipt/watcher source/evidence/archive/link checks, Markdown lint, full-tree secret scan and source-aware provenance PASS within scope |
| G08 | Explicitly selected physical target, console/recovery and wall-power restoration | ✅ PASS | 10.0.30.10/aicowork: encrypted header copy, automatic reboot, clean shutdown/cold start with AC restoration, physical passphrase recovery, exact temporary-entry cleanup and subsequent automatic boot PASS; physical commissioning scope only, no application deployment |

## Evidence history

- Planning inspection: current manual/lab engine and candidate bundle inspected; existing lab paths intentionally use unencrypted disks and temporary live secrets. Production adapter must enforce additional prerequisites. Historical passes are not new execution evidence.
- Implemented `scripts/hermes/productionctl.py`, production policy/signature/transaction/startup/backup/restore modules, shared-engine production branches, guarded production Kickstart/fixture, locked pykickstart dependency and canonical [runbook](../HERMES_PRODUCTION_DEPLOYMENT.md). Existing lab behavior and historical evidence were preserved. No production host was contacted or changed; no commit/push/PR action occurred.
- Initial focused suite: 17 PASS, expanded to 25 PASS. Corrections included lint findings, journal recovery/startup authorization, durable archive writes, systemd 259's omitted no-PIN token field, explicit root execution of the user-manager guard, and read-only SSH/PAM compatibility. The no-PIN format was checked against [systemd v259 source](https://github.com/systemd/systemd/blob/v259/src/shared/tpm2-util.c).
- Initial full offline gate: FAIL only for duplicate `common.py`/`transaction.py` helper basenames; renamed the new modules to `primitives.py`/`operations.py`. Initial check-only lint: FAIL only for two ordered-list numbers in the new runbook; corrected. Original failed logs are preserved under [this evidence directory](evidence/2026-09-27-hermes-production/).
- Subsequent full Toolbox offline gate: PASS, 574 Python tests, 140 ShellSpec examples and all shell/manual/guide checks; full-tree secret scan PASS, source-aware migration manifest PASS. Check-only lint PASS. These passes precede the last SSH/PAM/client-port edits, so final-source status is temporarily STALE rather than silently reusing them.
- Retained OCI archives (1,148,489,216 bytes combined) were packaged, signed with an ephemeral test-only key, verified and safely unpacked; an unqualified candidate was rejected under production policy. Initial artifact `e162118e30c77c782e8b33bdb9ace1952da2df8c4dd5052f06e9023f476d5c4c` is now STALE after source edits. No production signing key was created or installed; test keys and archives were removed automatically. Timings are packaging-only, not deployment benchmarks.
- Fedora Server DVD downloaded to ignored `.toolbox/hermes-production-validation/media/`, SHA256 `85837793bfa36db6bc709b4cecd2ec116951b87d9c53c3d95eb2fac8dcf7cf1f`, 3,913,023,488 bytes. GPG verified signer `36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6`. Fixture preview passed against local libvirt name inventory with an ephemeral public test key. No domain, disk, installer, container or guest session was created by that preview.
- Private-console availability was requested asynchronously; no answer or private input has been received. Do not infer consent to provision real credentials or a concrete production target from elapsed time.
- Final frozen implementation: full Toolbox offline gate PASS (574 Python tests including 25 new production tests, 140 ShellSpec examples, all manual/shell/guide checks); check-only lint PASS; secret scan PASS; Python syntax and exact diff checks PASS. [Verification index](evidence/2026-09-27-hermes-production/verification.json) binds every retained log/report by SHA256. Later edits only close this record and add immutable result files; documentation, secret scan and manifest checks are refreshed for those edits.
- Final retained-OCI packaging roundtrip PASS: artifact `8f0fa9ad305f1ad01e0534ec657f2da3bfaedc1e43b03649f3b6bd11e19ad5ed`, archive SHA256 `0cfb64c50f28c6939ed65d680d817a97d02d57c255b51eaccccd759400e803ff`, 1,148,723,200 bytes, candidate rejection under production policy PASS. Test-only build/sign took 2.931 seconds and verify/hash/extraction reporting 2.396 seconds on cached local inputs. These are not deployment measurements. Earlier source identities remain retained as STALE.

- Review correction resumed: user authorized directory-permission and cross-version receiver recovery fixes, real-function regressions, Toolbox gates and fresh evidence only. G01/G02/G07 and the prior `bundle-final.json` artifact are STALE for the changed implementation. Prior evidence remains byte-for-byte retained. No deployment contact, credentials, Git delivery or live qualification is authorized by this correction.

## Decisions and approved scope changes

- The initial compatibility contract intentionally rejects swap and ambiguous/thin/RAID ancestry; it requires one identified LUKS device for encrypted system/runtime storage. This narrows supported preparation rather than altering unrelated storage.
- A fixture may use network-disabled synthetic application mode and retain NOT_RUN for physical power restoration/initial off-host restore while its other boot commissioning proofs pass. Production cannot select that mode; release qualification and each physical target retain their separate gates.
- Original controller/helper policy (superseded by the review correction below): updates require private bootstrap and cannot silently mix versions. Ordinary qualified image/configuration updates remain unattended. The independent off-host restore command validates files in encrypted isolated staging and never starts a restored live gateway; application recovery acceptance is still required.

- Review correction: private bootstrap now retains immutable receiver versions without switching the active selection. Each release must still match every receiver/helper hash. Protocol-1 transactions coordinate controller and application selection; the prior receiver is retained for failed upgrades, explicit rollback and interrupted recovery. A fixed launcher refuses unsupported protocol changes; legacy flat installations need separate private migration. Public directory creation establishes exact modes under umask `077` and rejects unsafe existing ancestors before creating children.

## Handoff or closure — historical repository-delivery snapshot

- Current outcome: repository implementation and canonical runbook delivered with passing final-source offline, lint, signature/archive and syntax validation. No qualified production release has been signed or deployed.
- Remaining gates: private G03–G06 and target-specific G08. The overall plan is not complete.
- Material limitations: no current-source encrypted installation/runtime/Restic/boot/provider/Telegram/physical certification; production qualification remains open.
- Original next action after repository delivery: obtain private-console availability and create the new fixture using `.toolbox/hermes-production-validation/media/Fedora-Server-dvd-x86_64-44-1.7.iso`, its adjacent signed checksum, and an operator-controlled commissioning public key; render/review its explicit-disk settings, then invoke `vm/hermes-production-fixture.py --apply` and complete the private installation/recovery sequence in the runbook. Do not reuse a disposable preview key or claim production timings from package tests.
- Previous final state: BLOCKED on private encrypted-fixture commissioning, protected backup/live application inputs and an explicitly identified production canary. Repository changes remain uncommitted on `codex/hermes-production-bundle`.

- Review correction progress: six new real-function regressions passed with the original 25 tests (31 total before the added launcher regression). Initial focused attempts exposed test-fixture syntax, simulated-root lock ownership and stale helper-import isolation issues; these were corrected. Root ownership/host services and the process boundary remain mocked; real mode setting, signed release verification, engine loading, receiver selection, snapshots and tar restoration are exercised. That check sequence is superseded by the completed review validation below. Live gates remain pending; no target contact, credential provisioning, commit or push is permitted.

## Review correction validation and handoff

- **Scope completed:** both authorized review findings are fixed. Seven added regressions use real directory/parent mode establishment, actual CLI umask, signature and receiver hash validation, matching helper/engine loading, controller selection, stopped-state tar snapshots and restoration. OS identity/account/service commands, container behavior and the child-process boundary are synthetic; this does not establish root-owned Fedora runtime acceptance.
- **Checks:** `python3 -B -m unittest discover -s tests -p test_hermes_production.py` PASS (32 tests); selected maintained Python Ruff check/format PASS. Canonical `toolbox/run-offline-checks.sh` PASS (581 Python cases, 140 ShellSpec examples, all manual/shell/guide checks, full-tree secret scan and source-aware provenance). Canonical `toolbox/run-check-only-lint.sh` PASS. Both commands ran from this repository in `dev-infra-hermes`; see [offline log](evidence/2026-09-27-hermes-production/offline-review-r1.log) and [lint log](evidence/2026-09-27-hermes-production/lint-review-r1.log).
- **Bundle evidence:** [review package report](evidence/2026-09-27-hermes-production/bundle-review-r1.json) records artifact `26a1bcca3b2673b901114b99f1bc9862e66fc515b41e12b693be26a4fde2532d`, archive `0503dd14c0a34933af4ca8db41a1b66452369ebd61d7e8b298d222cdc500db29`, 1,148,743,680 bytes, protocol-1 receiver `472886bf21cdd0cdb07e007f6eddb7e1cfd6b9d2d66310b7091013bcecc0d06b`. Retained OCI inputs are unchanged. Test-only packaging/signing took 2.964 seconds and verification/extraction 1.799 seconds; these are not deployment timings. Temporary test keys/archive were removed. Production candidate rejection PASS; no qualified release was produced.
- **Superseded results:** `bundle-final.json`, `offline-final.log`, `lint-final.log` and the repository/bundle portions of `verification.json` are STALE for the corrected source. They remain unchanged, as do all earlier evidence files; their SHA256 values were checked against the prior verification index. Media verification and the historical fixture preview remain scoped to their original inputs and are not new runtime evidence.
- **Reproducibility:** [review verification index](evidence/2026-09-27-hermes-production/verification-review-r1.json) records checked source and evidence hashes, branch/base, exact commands and limitations. The canonical record and migration manifest are refreshed after evidence publication; the final documentation/secret/provenance/diff checks cover those closure edits.
- **Remaining gates:** G03–G06 and G08 remain BLOCKED/NOT_RUN in their existing scopes. A launcher/protocol change or a legacy flat receiver installation needs a separately reviewed migration. Live controller transitions, encrypted installation, boot recovery, Restic application restore and provider/Telegram behavior are not qualified by these tests.
- **Exact next action:** review these uncommitted fixes on `codex/hermes-production-bundle`. Any future live qualification requires a separately authorized private commissioning session and its protected inputs. No targets were contacted, operational credentials provisioned, or commits/pushes made during this correction.

## Review correction R2 progress

- Implementation now retains the operation lock in a Linux subreaper until the
  command and all adopted descendants exit. Production primitives, shared-engine
  commands and OCI import use it; cross-version receivers remain inside the same
  supervised tree. Parent cleanup is not the serialization mechanism.
- Recovery now stops both services on activation, verification, pointer or
  finalization failure; a failed gateway stop does not skip the worker. The
  unfinished journal is restored, unique sanitized failure records survive a
  successful retry, and stop/persistence failures are reported explicitly.
- Initial focused Toolbox suite PASS (36 tests). Four added tests cover real
  dispatcher SIGKILL with both a receiver and a detached, descriptor-closing
  descendant; command timeout with a detached writer; ten recovery failure/stop
  combinations with retry; and gateway query/stop failure still attempting worker
  shutdown. The initial selected Ruff check found one import-order issue; it was
  corrected, changed files formatted, and selected Ruff check PASS. Prior R1
  evidence remains STALE for changed source and is preserved unchanged.
- Source-aware provenance refreshed and verified. Next action: run canonical
  offline/check-only lint gates and retained-OCI package roundtrip, then record
  immutable evidence hashes and final documentation/provenance checks.
- First R2 canonical offline and check-only lint gates PASS, and the retained-OCI
  roundtrip PASS (`915d98d2eb298df38f2ceed266c241691e451ce81c381b461fe16211c00e2402`).
  Final inspection then tightened timeout handling to avoid signaling a reaped
  receiver's potentially reused process-group ID; the real-process timeout test
  now covers both a living receiver and one that has already exited. These first
  R2 gate/package results are retained as STALE; final-source focused tests still
  PASS (36). All evidence indexed by R1 was checked and remains byte-identical.
  Exact next action: rerun the affected canonical gates and package roundtrip
  against this final source, then refresh closure evidence and provenance.

## Review correction R2 validation and handoff (superseded)

- **Scope complete:** orphan writer serialization, failed-recovery service cleanup,
  and the requested regressions are implemented. A separate lock-owning Linux
  subreaper survives dispatcher death and waits for receiver descendants. This
  includes detached writers that close inherited descriptors. Timeouts do not
  permit recovery while writers live, or signal a reaped leader's stale group ID.
- **Recovery:** activation, verification, current-pointer and finalization faults
  attempt both stops, retain the unfinished journal and unique sanitized failure
  evidence, and support retry. Stop failure is explicitly reported as safety
  unconfirmed; persistence failure is also reported. The runbook documents busy
  writers, private diagnosis and the retry procedure. Deliberately killing the
  lock-owning guard or removing its lock is outside this mechanism's guarantees.
- **Final checks:** 36 focused production tests PASS; selected Ruff check/format
  PASS. Canonical Toolbox offline PASS (585 reviewed Python cases, 140 ShellSpec
  examples, manual/shell/guide gates, full-tree secret scan and source-aware
  provenance). Canonical check-only lint PASS. See the
  [offline log](evidence/2026-09-27-hermes-production/offline-review-r2-final.log),
  [lint log](evidence/2026-09-27-hermes-production/lint-review-r2-final.log) and
  [verification index](evidence/2026-09-27-hermes-production/verification-review-r2.json).
  Actual process lifetimes, flock contention and SIGKILL are tested locally;
  account, service and container behavior remains synthetic. Signed release,
  snapshot and tar restoration tests also remain offline.
- **Fresh bundle evidence:** the
  [final R2 report](evidence/2026-09-27-hermes-production/bundle-review-r2-final.json)
  binds artifact `9299238f053dcabc03f1017dc631ac557713a57d7d8fd1edc9f1a8929af0470b`,
  archive SHA256 `a213a6e0a2114172e9d0e7646d6fb5337dd55383fa7193ca19e6801cb17a91e2`
  (1,148,753,920 bytes) and protocol-1 receiver
  `243d6db51984625138f02c8740352a3510ce37c3518568c6849e2fdc70f180a4`.
  Packaging/signing took 2.992 seconds and verification/extraction 1.725 seconds
  using retained local OCI inputs. These are package timings, not deployment
  timings. Candidate rejection under production policy PASS. Temporary test keys
  and archives were automatically removed; no operational credentials were made.
- **Preservation:** R1 indexed evidence remains byte-for-byte unchanged. R1 and
  initial R2 repository/bundle results are STALE for the final source; earlier
  evidence is retained and bound in the new index. Historical media/fixture
  observations retain their original scope. The canonical record and migration
  manifest are refreshed after evidence publication; closure checks cover these
  documentation/evidence additions without claiming a new live qualification.
- **Remaining gates:** G03–G06 and G08 remain BLOCKED/NOT_RUN. Overall production
  qualification is incomplete. No deployment targets were contacted, operational
  credentials provisioned, or commit/push/PR changes made.
- **Exact next action:** review the uncommitted R2 changes and linked evidence on
  `codex/hermes-production-bundle`. Live qualification or Git delivery requires
  separate explicit authorization; no operational action is queued by this record.

- Closure correction: the expanded selected Ruff format check caught one shared
  engine call newly short enough for a single line (`profile-deploy.py`). Earlier
  formatting runs covered the new modules/tests but omitted that shared file;
  the format PASS wording above was too broad. This line is now corrected.
  R2 final repository/package passes and `verification-review-r2.json` are STALE
  for that source-byte change, with all files retained. The independent canonical
  lint gate had passed. Exact next action: verify all selected Python formatting,
  refresh bundle/source hashes and rerun canonical gates for accepted R2 evidence.

## R2 completed repository delivery

- **Final outcome:** all four requested correction outcomes are complete within
  offline review scope. T01/T04 and G01/G02/G07 are current again. The source,
  tests, runbook and provenance include both fixes and the final formatting
  correction. No deployment or production qualification is implied.
- **Checks PASS:** 36 focused tests; canonical Toolbox offline (585 Python tests,
  140 ShellSpec examples and all shell/manual/guide checks); canonical check-only
  lint; selected Ruff check and format check over all 15 selected Python files;
  full-tree secret scan and source-aware manifest verification. The final
  [focused log](evidence/2026-09-27-hermes-production/focused-review-r2-accepted.log),
  [offline log](evidence/2026-09-27-hermes-production/offline-review-r2-accepted.log),
  [lint log](evidence/2026-09-27-hermes-production/lint-review-r2-accepted.log) and
  [verification index](evidence/2026-09-27-hermes-production/verification-review-r2-accepted.json)
  supersede the earlier R2 results. Closure documentation, links, secrets and
  provenance are checked after this record/evidence publication.
- **Bundle PASS:** the
  [accepted R2 report](evidence/2026-09-27-hermes-production/bundle-review-r2-accepted.json)
  records artifact `f43a98ade04eb94cbc927d9c69d79241c216e2c4eb65b7194e68ee4ca424f0a0`
  and archive `beef60eebcd163914d86d198be1e55668490d5947493c0588aa3c02a328fd206`.
  The receiver identity and archive size remain as recorded above; the shared
  engine's final formatting changes the complete artifact identity. All packaged
  source hashes match current files. Test-only build/sign took 2.868 seconds and
  verify/extraction 1.719 seconds; production candidate rejection PASS. No
  qualified production release or operational key was produced.
- **Preservation and limits:** every earlier indexed evidence file remains
  unchanged. Superseded R1 and earlier R2 results remain STALE and available.
  Actual SIGKILL, descriptor closure, detached descendants and flock lifetime are
  exercised with temporary local subprocesses; service/container/host behavior
  is synthetic. G03–G06/G08 remain BLOCKED/NOT_RUN. Production targets were not
  contacted; no operational credentials, commits, pushes or PR changes occurred.
- **Exact next action:** review this uncommitted repository delivery and the
  accepted R2 index. No further action is authorized or queued for deployment or
  Git delivery; the broader plan remains blocked on separate private qualification.

## Preproduction goal resumption — 2026-09-27

- **Current authority:** the user activated the goal to complete preproduction
  changes and qualification and confirmed "start that goal". Repository edits,
  documentation, offline Toolbox checks and necessary in-scope corrections are
  authorized. This supersedes the prior repository-only handoff as an instruction
  to continue; it does not authorize a concrete live resource or operational
  credential use. Before VM lifecycle, privileged operations, deployment or live
  external tests, obtain one explicit authorization naming resources, operations,
  cleanup and provider/Telegram limits. No Git delivery or production changes.
- **Acceptance boundary:** complete T01–T04 and G01–G07 for the exact candidate;
  T05/G08 remain required for the broader production plan and are outside this
  preproduction goal. Preserve all mandatory encrypted-fixture, runtime, restore,
  boot and live-application requirements. An offline pass cannot close G03–G06.
- **Resumption inspection:** existing dirty feature branch
  `codex/hermes-production-bundle`, base
  `3debb5ae22f91eb47c61daa30f1543d20456fec2`, retained without reset. All 20 source
  hashes and 29 evidence hashes in the accepted R2 index match current files.
  Source-aware manifest verification PASS in `dev-infra-hermes` with 461 rows.
  The sandbox could not access Toolbox; the authorized host-access retry passed.
  This record append invalidates only whole-tree provenance until regeneration;
  the unchanged implementation and retained package evidence keep their scope.
- **Environment observations:** the retained Fedora Server 44 ISO and signed
  checksum exist; the fixture directory does not. Toolbox has Python 3.14.7 and
  KVM access but lacks `virsh`, `virt-install` and `qemu-img`; host-side virtualization
  tools must be inspected separately. These observations are not installation or
  guest readiness. No target or credential file was contacted or inspected.
- **Current work:** refresh repository checks and inspect qualification tooling
  and inputs. Expected result: canonical offline/lint gates pass, immutable
  evidence remains intact, and a concrete live qualification authorization and
  private setup handoff are ready. G03–G06 remain BLOCKED pending those inputs.
- **Exact next action:** inspect local session-domain inventory without guest
  contact, refresh the manifest, then run the canonical Toolbox offline and
  check-only lint commands with new evidence paths; prepare the bounded live
  authorization while independent repository validation continues.

- **First resumption checks:** check-only lint PASS. Read-only host-side fixture
  preview PASS, with current Fedora signed-media verification, an empty local
  session-domain inventory and a temporary nonoperational key; no VM was created.
  The proposed fixture has 8 GiB RAM, two vCPUs, a 181024 MiB sparse system disk
  and a 64 MiB unrelated-disk canary under the previously specified fixture path.
- **Failed attempt retained:** the initial canonical offline command ran under
  an overbroad log-wrapper `umask 077`; 583/585 Python tests passed and two fixture
  assertions failed (`test_identity_data_setup_drops_root_before_user_path_mutation`
  and `test_fresh_bootstrap_and_unchanged_rerun_with_cli_umask`). Both fixtures
  create prerequisite directories before exercising the behavior under test;
  their expected public modes assume the Toolbox default `022`, confirmed live.
  Lint, shell suites, secret scan and provenance passed. Preserve the log and
  correct the invocation, not the application permission requirements. The
  failed run does not replace accepted R2 evidence as a passing result.
- **Private prerequisite request:** requested only non-secret public-key paths,
  backup endpoint/credential paths, live-smoke credential paths/test identities,
  spend/message limits and console availability. No values or authorization have
  been received. Exact next action: rerun the canonical offline command under
  the Toolbox default umask while retaining logs inside the private validation
  directory, then publish fresh evidence and prepare the live-operation handoff.

### Resumption result and live qualification handoff

- **Repository result:** canonical offline PASS under the normal Toolbox `022`
  umask: 585 Python tests, 140 ShellSpec examples and all remaining offline gates.
  Check-only lint, full-tree secret scan and source-aware provenance PASS. Local
  file-link validation checked 52 targets before this closure append; it did not
  fetch remote URLs or validate fragments. No application or test edits were
  needed. The failed `077` invocation remains retained, not relabeled as PASS.
- **Candidate continuity:** all 38 package entries, executable modes, retained
  OCI bytes, package inventory, current profile and image identities reproduce
  artifact `f43a98ade04eb94cbc927d9c69d79241c216e2c4eb65b7194e68ee4ca424f0a0`.
  The prior roundtrip archive used a temporary test key and was removed; this
  identity check is not a new signed or qualified release. Accepted R2 evidence
  remains valid within its package/offline scope and unchanged byte-for-byte.
- **Evidence:** [resumption index](evidence/2026-09-27-hermes-production/verification-goal-resumption.json),
  [passing offline log](evidence/2026-09-27-hermes-production/offline-goal-default-umask.log),
  [failed invocation](evidence/2026-09-27-hermes-production/offline-goal-initial.log),
  [lint](evidence/2026-09-27-hermes-production/lint-goal.log),
  [fresh fixture preview](evidence/2026-09-27-hermes-production/fixture-preview-goal.json)
  and [candidate identity](evidence/2026-09-27-hermes-production/candidate-identity-goal.json).
  This index excludes the mutable execution record and manifest. Final check-only
  lint, links, secrets and provenance cover the subsequent evidence/record additions.
- **Prepared resource proposal, not authorization:** create only
  `qemu:///session` domain `hermes-production-qualification`, using the retained
  signed Fedora 44 media, 8 GiB RAM, two vCPUs and the two new disks under
  `.toolbox/hermes-production-fixture/`. Installation may erase only its new
  `virtio-HERMES_PROD_TEST` system disk; preserve and verify the unrelated-disk
  canary. Proposed operations are private installation/commissioning, candidate
  deployment, negative/rerun/interruption tests, upgrade/rollback, reboot/cold
  start/recovery and evidence capture. Preserve failed fixtures and evidence;
  no automatic deletion, retained-fixture access or production operations.
- **Still required before a single live authorization:** an operator-controlled
  commissioning public key and console availability; explicit isolated restore
  target and off-host Restic endpoint with private access; dedicated live-smoke
  credential paths, authorized/rejected test identities and provider/message
  limits. The existing fixture helper creates only the named primary fixture;
  a concrete isolated restore target/procedure must be reviewed before its use.
  Any operational signing/deployment keys belong to private setup, not the
  ephemeral preview. Requests are for paths/identifiers only, never raw secrets.
- **Gate audit:** T01/T04 and G01/G02/G07 retain passing repository evidence;
  G03 has parser/media/preview coverage only. G03–G06 remain BLOCKED because
  encrypted installation, actual runtime, isolated off-host application restore,
  TPM/recovery and exact-candidate provider/Telegram proof have not run. T05/G08
  remain outside this preproduction goal without being waived for production.
- **Exact next action:** obtain the non-secret private-setup details requested
  in this task, then finalize one exact-resource/operation/cleanup/spend
  authorization and conduct private commissioning. No dependent live action is
  queued or approved by this handoff; the preproduction goal is incomplete.

## Concrete preproduction setup preparation

- **Authority:** the user requested "Proceed" after the offer to prepare one
  concrete test-environment proposal and a private-setup checklist. Preparation
  is authorized; no live operations follow from that reply. The existing goal
  also authorizes repository corrections needed for qualification. Preserve the
  approved baseline and the current dirty feature branch.
- **Inspected facts:** host guest definitions include `fedora43` but not
  `fedora44`; the current fixture hardcodes the unavailable definition. It also
  has only one fixed VM name and lacks localhost SSH forwarding. Local session
  inventory is empty, both proposed fixture directories are absent, and the
  workspace has 84.5 GiB available. Existing disposable-lab private files are
  owned by the current user, with directory mode 0700 and five file modes 0600.
  Only metadata was inspected; credential validity, permission to reuse them and
  provider cap enforcement have not been established.
- **Repository correction:** retain the existing default qualification fixture
  and add exactly one isolated restore role; use installed Fedora44 metadata
  when available and Fedora43 metadata otherwise while requiring the same signed
  Fedora44 media; expose guest SSH only on distinct localhost ports. Reject name,
  directory and port conflicts and insufficient host free space before creation.
  Keep creation deliberately create-only: reruns preserve existing resources and
  fail rather than replace them. No unrestricted domain or directory selection.
- **Expected validation:** unit tests mock every virtualization/signature command
  and cover role isolation, metadata selection, preview, conflict/capacity refusal
  and preserved partial failures. Then canonical offline/lint/secret/provenance
  checks and a fresh retained-OCI bundle roundtrip cover the final documentation.
  G02/G07 and T04 become STALE once the packaged runbook changes; accepted evidence
  stays immutable. G03–G06 remain BLOCKED pending live commissioning.
- **Exact next action:** implement and validate this fixture correction, save
  the exact two-VM proposal and private checklist here, then request approval
  only for the fully prepared live scope. A separate-machine SFTP destination
  has been requested as the remaining non-discoverable resource input.

### Proposal awaiting live-operation approval

The user's "Proceed" authorizes preparing this proposal, not creating its VMs.
The following scope is ready for review; the SFTP destination must still be
identified before external backup operations can be included in the approval.

| Resource | Proposed use and limit |
| --- | --- |
| `qemu:///session` / `hermes-production-qualification` | Fresh encrypted Fedora44 installation; localhost SSH `127.0.0.1:22224`; files only in `.toolbox/hermes-production-fixture/` |
| `qemu:///session` / `hermes-production-restore` | Independent encrypted restore target; localhost SSH `127.0.0.1:22225`; files only in `.toolbox/hermes-production-restore/` |
| Each new VM | 8 GiB RAM, two vCPUs, 181024 MiB sparse system disk and 64 MiB unrelated-disk canary; run one VM at a time by default |
| Disk layout | Only the new disk identified as `/dev/disk/by-id/virtio-HERMES_PROD_TEST` is erased: root 30720 MiB, `/var` 81920 MiB, Hermes 61440 MiB, plus boot/LVM overhead |
| Workstation private setup | Dedicated test signing, commissioning and forced-command deployment keys under owner-only `~/.local/share/hermes-production-qualification/`; no general host sudo grant |
| Backup service | A separate-machine SFTP account and a dedicated test directory supplied by the operator; pinned host identity, encrypted Restic data and a private repository password |
| Existing private live inputs | Potential reuse of the five restricted files under `~/.local/share/hermes-disposable/private/`, only after the operator confirms dedicated test ownership and reuse for this candidate |

The host free-space requirement is 20 GiB before creation and each later large
write. The sparse disks are not preallocated and this is not a filesystem quota;
if the reserve cannot be maintained, stop rather than grow the experiment.
No host package installation, network/bridge/firewall alteration, existing-VM
access or physical production operation is included.

**Operations proposed:** create/install/commission the two named VMs, pin their
identities, stage a test-signed candidate and matching receivers, deploy/rerun,
verify isolation and rejection cases, exercise controlled interruption and failed
upgrade/rollback, create encrypted backup snapshots at the selected endpoint,
restore matching state into the isolated target, reboot/cold-start, and verify
private recovery followed by automatic TPM unlock. Bootloader, crypttab and
initramfs changes are confined to the new guests. Recovery failure keeps the
affected guest running for private diagnosis; never wipe keyslots or restore
headers automatically. Record each acceptance gate independently.

**Proposed live limits:** maximum USD 1 total provider spend for this qualification
attempt, with an independently verified enforceable account limit before gateway
activation; the historical text file saying "verified" is insufficient. Schedule
at most six authorized operator test messages and one rejected-user probe, using
the dedicated test bot and operator-selected test accounts only. The existing
harness cannot cap gateway-internal retries or bot replies; do not describe these
operator-message limits as a hard API-request limit. If enforceable spend control
cannot be established, hold live activation and propose a bounded alternative
before making any request. Stop on authentication failure; no repeated paid
retries or unattended replacement of credentials. Close the live window after
the required tool/approval/allow/reject observations and check actual usage.

**Cleanup proposed:** stop both gateways and normally leave the two owned VMs
shut down after verification. Retain disks, ownership data, encrypted backup
snapshots and sanitized failure evidence. Revoke temporary guest commissioning
access when safe; keep recovery access if a gate failed. Do not delete the five
existing private source files, revoke provider credentials, prune a remote
repository, remove disks or touch other resources without separate instruction.

### Consolidated private setup checklist

1. After approval, generate dedicated test keys in the private workstation
   directory and render the two non-secret installation settings. The operator
   does not need to locate or disclose an existing personal SSH key.
2. Install each new VM using its private console. The operator enters encryption
   and administrator secrets and retains recovery material outside chat/logs.
   Follow the canonical [commissioning procedure](../HERMES_PRODUCTION_DEPLOYMENT.md#existing-server-preparation-and-private-commissioning)
   for recovery verification, additive PCR7 enrollment, initramfs checks and
   reboot/cold/recovery proofs. This phase can require several private prompts.
3. Privately provision the selected SFTP destination, its pinned identity and
   test-only access, plus the Restic password. Record only non-secret endpoint
   identities and evidence hashes. Commission the restore guest independently;
   never clone its TPM, machine or SSH identity from the primary guest.
4. Install the reviewed bounded guest dispatcher and validate its permitted and
   rejected operations. Finish synthetic runtime, repeatability and restore
   checks before enabling real credentials. Retain no live gateway credentials
   in reusable media, image caches or fixture snapshots.
5. Confirm reuse or replacement of the existing private test files, current
   account ownership, the spend control and a quiet dedicated test bot. Enter
   any replacement values privately. The operator supplies the allowed-user
   messages, approval/denial interactions and rejected-user probe during the
   live window; a bot token alone cannot generate authentic messages from those
   users. These manual acceptance interactions prevent a promise of zero human
   intervention even after installation.
6. Finish evidence and usage review; apply only the cleanup above. The agent
   continues all authorized automatic checks and in-scope corrections between
   private interactions. No commit, push, PR modification or production canary.

**Current preparation status:** six new synthetic fixture tests PASS (42 total
focused production tests). Both actual read-only role previews and canonical
repository/bundle checks PASS within their recorded scopes. The precise remaining input is the
backup host/account/test directory, followed by approval of this bounded scope;
secrets and test interactions are handled privately afterward.

### Setup preparation verification and handoff

- **Changes complete:** fixture metadata selection, fixed restore role, localhost
  SSH forwarding, pre-creation capacity/port/name/directory checks and symlink
  refusal. Existing fixture defaults remain compatible. Six offline tests cover
  both roles, preview without creation, refusal and preservation of partial work.
  Canonical runbook and this concrete proposal/private checklist are updated.
- **Checks PASS:** 42 focused tests, selected Ruff check/format, canonical Toolbox
  offline (591 Python tests, 140 ShellSpec examples), check-only lint, full-tree
  secrets, source-aware manifest and diff whitespace. Both read-only role previews
  verify retained signed Fedora44 media and select this host's `fedora43` metadata.
  Ports 22224/22225 were available at preview time; availability is rechecked on
  creation. No guest, disk, operational key or provider request was created.
- **Fresh candidate:** artifact
  `834adb288d5ebdec3a700426fdd054801be3dfa10010534731b8e32939851df8`, archive
  `9dfb2e3123a3aebcb9ca229c132906421e54e506a94c2207606979808989f10a`,
  1,148,753,920 bytes. Test-only retained-OCI build/sign took 2.984 seconds and
  verification/extraction 1.788 seconds; unqualified production rejection PASS.
  Temporary signing keys/archives were removed. These are package measurements,
  not live qualification or installation timing.
- **Evidence:** [setup verification index](evidence/2026-09-27-hermes-production/verification-fixture-setup.json)
  binds the new [offline log](evidence/2026-09-27-hermes-production/offline-fixture-setup.log),
  [focused tests](evidence/2026-09-27-hermes-production/focused-fixture-setup.log),
  [lint](evidence/2026-09-27-hermes-production/lint-fixture-setup.log),
  [previews](evidence/2026-09-27-hermes-production/fixture-setup-previews.json)
  and [package roundtrip](evidence/2026-09-27-hermes-production/bundle-fixture-setup.json).
  Accepted R2 and initial goal-resumption evidence remain byte-identical; their
  previous whole-tree/candidate passes are STALE for this updated runbook/fixture.
  Final documentation, links, secrets and manifest checks cover this publication.
- **Outcome:** repository preparation is complete; G03–G06 and the overall
  preproduction goal remain incomplete. This proposal does not approve itself.
  No production resource, retained recovery fixture or Git delivery was touched.
- **Exact next action:** obtain the separate backup host/account/test directory,
  then approve the named resources, test operations, private input use and limits
  above in one live scope. Begin the private commissioning checklist only after
  that approval. If no separate backup host is available, record that limitation
  and propose a separately bounded backup resource; do not substitute a local
  copy for required off-host recovery evidence.

## No backup host available — alternative awaiting direction

- **User input:** the operator answered "No backup" to the request for a backup
  host. Treat this as no existing backup destination, not authorization to waive
  recovery acceptance or provision an external service. The earlier request to
  supply an existing host is resolved and must not be repeated unchanged.
- **Current contract:** `production/preflight.py` requires
  `encrypted_offhost_recovery` to be PASS even for a fixture. Only isolated
  restore and physical firmware power-restoration proofs may initially remain
  unperformed on a fixture. Keep this guard unchanged. A repository URL with
  SFTP syntax is not proof of an independent recovery copy.
- **Recommended bounded extension for review:** a rootless local SFTP test
  container named `hermes-preproduction-backup`, bound only to
  `127.0.0.1:22226`, with task-owned state under the ignored
  `.toolbox/hermes-production-backup/` and a 256 MiB memory / one-CPU / 64-PID
  limit. Reuse the retained pinned worker OCI archive's OpenSSH implementation
  with a separate SFTP-only configuration and test keys; do not alter the
  application worker profile, enable host SSH, publish a LAN port, or change
  host firewall policy. Proposed data is synthetic test content encrypted by
  Restic. No provider credentials, paid APIs or external messages are needed.
- **What it could prove:** real SFTP transport, encrypted Restic backup and
  isolated file restoration with matching test content. A future reviewed
  fixture runner would enforce ownership/port/path checks, preview/apply,
  rerun behavior, failure retention and the host free-space reserve. This is a
  concrete resource proposal, not an implemented or exercised service.
- **Acceptance limit:** that container shares the workstation's storage and
  failure domain with both VMs. It cannot establish independent off-host
  recovery, close the complete G04 restore gate, or authorize a false
  commissioning attestation. Do not bypass preflight to run dependent tests.
  Full qualification remains incomplete until compliant recovery storage exists
  or the user explicitly approves a change to the original acceptance scope.
- **Retention:** if later approved, stop only the owned test container after
  checks and retain its encrypted test repository and sanitized evidence.
  Removal, pruning or provider credential revocation is not included. Existing
  VM, production and recovery resources remain outside this extension.
- **Alternative:** retain backup/restore as BLOCKED until independent storage
  is available, without adding the local fixture. Installation-only preparation
  can be considered separately, but no VM lifecycle is yet authorized here.
- **Exact next action:** receive the operator's direction on preparing the
  local test fixture versus deferring backup tests, then finalize the applicable
  scope extension and live-resource approval before dependent implementation
  or operations. No VM, container, key, backup or external service was created.

## Approved temporary local backup extension

- **Approval evidence:** the operator selected "Temporary local backup" after
  the proposed local SFTP fixture and its acceptance limits were presented.
  This authorizes implementing and exercising the named local fixture within
  those limits. It does not authorize VM creation, production changes, provider
  calls, Telegram messages or waiving independent off-host recovery.
- **Frozen extension scope:** rootless container `hermes-preproduction-backup`,
  localhost `127.0.0.1:22226`, state only under ignored
  `.toolbox/hermes-production-backup/` with an adjacent task lock; 256 MiB memory,
  one CPU and 64 PIDs. Use the retained worker OCI archive with SHA256
  `155c34c95b797f541fd2469ca63338d6fa00106318ec8171845c3a4d8f76c52a`
  and image `sha256:4d7b3f8712ed95efeed6e6756ff70859d896ffeb5e7c04da31504b0fe8203e52`.
  No image pulls or builds, host SSH/firewall changes, or unrelated mounts.
  Generate only fixture-specific test keys and a Restic test password locally;
  keep them private and out of reports, argv values, images and Git.
- **Observed prerequisites:** host Podman reports rootless operation. The owned
  fixture directory is absent. Restic 0.19.1 and SSH are already installed in
  `dev-infra-hermes`; no host packages or Toolbox installations are needed.
- **Task LB01 — IN_PROGRESS:** implement preview/apply/status/stop and a real
  synthetic-data backup/restore test with ownership checks, serialization,
  unchanged rerun behavior, partial-failure retention and isolated restoration.
  Stop the owned container after tests while retaining state/evidence.
- **Gate LB-U — NOT_RUN:** offline tests mock Podman/Restic/network operations;
  expect rejection of conflicts, unsafe paths, changed identity and failed
  commands, plus rerun and failure-cleanup behavior. Add only those unit tests
  to the reviewed offline allowlist; do not widen integration discovery.
- **Gate LB-L — NOT_RUN:** run the authorized local fixture, encrypt synthetic
  data through real Restic/SFTP, restore into fresh isolated staging and compare
  file content/modes; reject wrong SSH trust/key and wrong Restic password;
  check localhost binding, rootless/resource/mount/security configuration;
  rerun unchanged without replacing keys/container or duplicating snapshots;
  stop twice and preserve all task data. No live application secrets are inputs.
- **Gate LB-R — NOT_RUN:** canonical offline/lint/secret/provenance checks,
  affected documentation/links and exact changed artifact evidence. Preserve
  previous evidence and mark affected repository/package passes STALE.
- **Acceptance boundary:** LB-L is actual local transport/encryption/file-restore
  evidence. It cannot close the whole G04 gate, satisfy
  `encrypted_offhost_recovery`, or establish application recovery or physical
  fault independence. Existing production preflight remains unchanged.
- **Exact next action:** implement the bounded fixture and offline regressions,
  run LB-U before starting its service, then perform LB-L and LB-R and retain the
  stopped fixture plus a precise handoff for the remaining original gates.

### Local backup implementation and live correction record

- **LB01 implementation:** added the bounded host runner
  `scripts/hermes/backup-fixture.py` and its canonical
  [operating guide](../HERMES_LOCAL_BACKUP_FIXTURE.md). Existing production
  preflight, application profiles, VM fixtures and private application inputs
  remain unchanged.
- **LB-U — PASS:** 17 mocked safety regressions cover preview, serialization,
  path/name/port/capacity conflicts, identity/mount/map drift, command failures,
  stop convergence and failure cleanup. External commands are mocked in the
  explicitly allowlisted class; no live test entered the offline gate.
- **First live correction:** Podman reports its image digest without the
  `sha256:` prefix and keep-id as private namespace plus explicit UID/GID maps.
  The first validation failed before service startup. Inspected the stopped
  matching container, corrected normalization/map validation and added a
  regression. No ownership or security guard was removed.
- **Second live correction:** an absolute Restic source path archived changing
  ancestor-directory metadata. The first unchanged rerun created a second
  snapshot even though all four files were unchanged. Preserved that failed
  repository as `.toolbox/hermes-production-backup/repository-attempt-absolute-path/`
  while the owned container was stopped; no data was deleted. Backups now run
  from inside the fixed synthetic source directory and archive `.`.
- **LB-L — PASS within local scope:** the corrected initial test and unchanged
  rerun used one active snapshot with ID
  `9946c64289cd0db03cfd711e91809c51cb009e3f04208d980d87445b78ed2d62`.
  Both restored matching content and file modes, checked all encrypted data,
  rejected incorrect SSH identity/trust and Restic passwords, checked resource
  limits/mounts/localhost binding and stopped successfully. Keys and container
  identity were retained. Failed attempts remain evidence, not current passes.
- **LB-R — IN_PROGRESS:** run canonical offline and check-only lint gates,
  source-aware provenance, documentation links and secret checks; publish the
  sanitized local result and immutable verification index, then validate the
  publication. Prior whole-tree passes are STALE for these added sources.
  Packaged production sources are unchanged; verify their hashes before
  reusing the existing candidate roundtrip evidence.
- **Remaining boundary:** local success still does not satisfy
  `encrypted_offhost_recovery`, application restore, the complete G04 gate or
  full preproduction qualification. No VM or production lifecycle was run.

### Local backup repository acceptance and publication

- **LB01 — DONE; LB-U/LB-L — PASS within their stated scopes.** Two additional
  stop operations both returned `already-stopped`; the container remained
  stopped and `127.0.0.1:22226` was available afterward. The active repository
  occupies 24 KiB; the retained failed repository occupies 40 KiB. These sizes
  describe this synthetic test only, not a production capacity estimate.
- **LB-R repository gates — PASS:** 608 reviewed Python cases, 140 ShellSpec
  examples and the complete canonical offline gate; check-only lint, full-tree
  secret scanning, Ruff check/format, 59 local documentation targets before
  publication and source-aware migration verification. No dependency sync,
  image pull/build, production operation or Git delivery was performed.
- **Package reuse — VERIFIED:** all 38 package entries and modes plus the
  current profile reconstruct artifact
  `834adb288d5ebdec3a700426fdd054801be3dfa10010534731b8e32939851df8`.
  No packaged source changed, so the prior retained-image signature roundtrip
  remains applicable. All five earlier verification indices and their bound
  evidence still match their recorded hashes. Only prior whole-tree passes
  are superseded for this new fixture code/docs/tests.
- **Immutable evidence:** [verification index](evidence/2026-09-27-hermes-production/verification-local-backup.json),
  [live runs and failures](evidence/2026-09-27-hermes-production/live-local-backup.json),
  [focused regressions](evidence/2026-09-27-hermes-production/focused-local-backup.log),
  [offline gate](evidence/2026-09-27-hermes-production/offline-local-backup.log),
  [check-only lint](evidence/2026-09-27-hermes-production/lint-local-backup.log),
  [package input recheck](evidence/2026-09-27-hermes-production/package-inputs-local-backup.json)
  and [pre-publication link check](evidence/2026-09-27-hermes-production/links-local-backup.json).
  Raw private credentials and encrypted/restored test data remain ignored.
- **Publication closure — PASS; LB-R — PASS:** the updated record passed
  Markdown lint; all 66 local link targets exist; all six source hashes and
  six bound evidence files match the new index. Full-tree secret scanning
  passed and the regenerated manifest verified in source-aware mode with
  484 rows. Refresh and verify provenance after this final status update.
  The approved temporary local extension is complete within its tested scope;
  the original preproduction goal remains incomplete.
- **Exact next action after closure:** retain the stopped fixture. Resume
  broader commissioning only when the original named-resource/private-setup
  approval is complete and independent recovery storage is available, or a
  separately approved acceptance-scope revision defines a narrower goal.
  Local backup is implemented and tested; it must not be turned into a false
  `encrypted_offhost_recovery` attestation.

## Fresh-server intake — corrected account

- **User input:** fresh server installed at `10.0.30.10`; the operator corrected
  the login from `aicorowk` to **`aicowork`**. Use only the corrected account.
  The 500 GB SSD and fresh installation are user-reported; OS, partition layout,
  encryption and installed services have not yet been inspected remotely.
- **SI01 — IN_PROGRESS:** establish trusted SSH access for read-only readiness
  inspection. This intake does not qualify the release or attest commissioning,
  and does not authorize disk changes or provision production credentials.
- **SI-NET — PASS, 2026-09-28 04:16 UTC:** host TCP port 22 accepted a bounded
  connection and returned `SSH-2.0-OpenSSH_10.2`. Public-only `ssh-keyscan -T 5
  -t ed25519 10.0.30.10` succeeded. The observed, **unverified** fingerprint is
  `SHA256:CO3LNHAD0V3xvhZlQfSZK3phrdJ9TuENjSKxyvz/sd8`.
  No authentication was attempted and no scanned key was saved as trusted.
- **SI-TRUST/ACCESS — BLOCKED:** no matching entry was found in the standard
  user/system known-host files; no standard private identity or usable agent
  identity was observed. Default `ssh -G` also refused the existing local SSH
  configuration with an owner/permissions diagnostic. Preserve that unrelated
  configuration; use an isolated SSH configuration for this target when its
  identity and intended login method are established.
- **Exact next action:** obtain console confirmation of the public Ed25519
  fingerprint and the intended local SSH-key path, or confirmation that access
  uses a private password login. The operator can read the fingerprint with
  `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` on the server console.
  Never request the password in chat. Then perform authenticated read-only
  inventory and prepare one concrete commissioning scope from its findings.
- **Remaining qualification:** G03–G06 and physical G08 are still unperformed
  in their live scopes. The completed localhost backup fixture remains test
  evidence; independent off-host recovery is still unresolved.

### SSH key access preparation — user-requested

- **Updated input:** login currently uses a password. The operator asked how
  to allow SSH key access. Prepare a dedicated local Ed25519 key and an
  interactive `ssh-copy-id` command for the corrected `aicowork@10.0.30.10`
  account. Password input stays in the operator's terminal; no password is
  requested in chat, stored or embedded in commands.
- **Scope:** keep the key under ignored, owner-only
  `.toolbox/hermes-production-access/`; never replace an existing identity.
  The operator installs only its public key into their account. Use an
  isolated client configuration and dedicated known-host file. The observed
  host fingerprint still requires console comparison before trust is accepted.
  No sudo policy, server SSH settings, storage or production deployment changes
  are included in preparing account access.
- **SI-KEY — PASS locally:** generated
  `.toolbox/hermes-production-access/aicowork-10.0.30.10` and its `.pub` file.
  The directory is mode 0700; the private key and public file are mode 0600,
  current-user-owned, regular single-link files. Derived and stored public
  identities match. The public access-key fingerprint is
  `SHA256:yJ6yCyJwS5lA+iMva739rMHdWuldNahkNYTHFPzZc1U`.
  This is the client access key, distinct from the server host fingerprint.
- **Exact next action:** the operator compares the server's console fingerprint
  with the observed host fingerprint above, then runs interactive `ssh-copy-id`
  with the dedicated `.pub`, `-F /dev/null`, and a dedicated `known_hosts` file
  in the same ignored directory. Normal duplicate checking remains enabled;
  do not use force mode. Enter the server password only in the terminal.
  After the operator confirms completion, verify batch key authentication and
  collect read-only readiness evidence. Remote installation/login is NOT_RUN
  until that private step completes.

## Authenticated server inventory and approved prerequisite fixes

- **SI01/SI-TRUST/ACCESS — PASS for key login:** after the operator reported
  `done`, the dedicated known-host file contained the expected Ed25519 key and
  batch public-key login succeeded as `aicowork`. Console comparison remains
  operator-reported through completion of the supplied instructions; it was
  not independently observed by the agent.
- **Read-only inventory:** [server report](evidence/2026-09-27-hermes-production/server-intake-10-0-30-10.json)
  records Fedora Server 44/x86-64, approximately 13 GiB available-to-kernel RAM,
  cgroup v2, SELinux enforcing, Secure Boot enabled, TPM resource manager and
  Podman 5.8.7. Root/var/Hermes are XFS logical volumes below crypto_LUKS:
  30 GiB `/`, 60 GiB `/var`, 80 GiB `/home/hermes`. The latter sizes reverse the
  example but satisfy its 4 GiB artifact / 8 GiB state capacity budgets.
  `/boot` is 2 GiB ext4 and EFI approximately 1 GiB; ext4 `/boot` is not rejected
  by production preflight. No repartitioning is indicated by this inventory.
  The separate exFAT/removable-looking `sda` is outside the change scope.
- **Observed gaps:** Restic is the only missing enumerated runtime package;
  an 8 GiB zram swap device is active. The `hermes` runtime account does not
  exist yet, which is normal before bootstrap. Root-only LVM/LUKS/boot policy
  and recovery proofs remain unverified.
- **Approval evidence:** after these two gaps were reported, the operator
  instructed `continue with pending tasks`. This authorizes installing Restic
  with required dependencies and disabling the identified default zram swap,
  plus bounded read-only commissioning inspection. Preserve storage, unrelated
  services, credentials and the existing sudo policy; do not reboot or enroll
  TPM keys as part of these prerequisite fixes.
- **SP01 — IN_PROGRESS:** prepare a target-bound, preview/apply prerequisite
  script. Refuse conflicting zram configuration, ensure sufficient available
  RAM before swapoff, install Restic only if absent, mask the vendor zram
  configuration with `/etc/systemd/zram-generator.conf -> /dev/null`, stop only
  zram0 swap/setup, reload generators and verify no active swap or regenerated
  zram0 swap unit. Save a sanitized root inspection report, preserving partial
  changes on failure for a checked rerun.
- **SP-ACCESS — BLOCKED:** `sudo -n true` returned `sudo: a password is required`.
  Prepare the reviewed script and private interactive sudo command before
  handing off that unavoidable password step. Never request/store the password
  or install a broad passwordless sudo grant.
- **SP-PREP — PASS:** the target-bound
  [reviewable script](evidence/2026-09-27-hermes-production/server-prerequisites-script.txt)
  is placed at
  `/home/aicowork/hermes-prerequisites-be66c2b6f902dc44.py`, owner-only, on the
  selected server. Its unprivileged preview passed and reported exactly the
  two intended changes. Local syntax, Ruff and mocked wrong-target/preview/root
  checks passed; kernel swap parsing additionally covers empty/malformed input
  and KiB-to-byte conversion. See the immutable
  [preparation receipt](evidence/2026-09-27-hermes-production/server-prerequisites-preparation.json)
  for the exact source SHA256 and preview.
- **Preserved preview failures:** the installed `swapon` rejected JSON output;
  its requested raw two-column mode then returned five columns. Both previews
  refused before configuration changes. Inspected actual output, replaced the
  assumptions with the kernel `/proc/swaps` format and tested that parser.
  Both prior script files/failed preview records are retained as evidence;
  only the final hash-named script is the current command.
- **Exact next action:** the operator privately runs
  `sudo python3 -I /home/aicowork/hermes-prerequisites-be66c2b6f902dc44.py --apply`
  on the server and supplies the sudo password at its terminal prompt. The
  script writes nonsecret status to
  `/var/lib/hermes-production-prerequisites/report.json` and keeps individual
  attempt reports. After completion, retrieve that report through the verified
  SSH key and independently check package/swap state and remaining boot gates.
  Actual prerequisite application and rerun verification remain NOT_RUN.
- **Goal continuation check — 2026-09-28 04:37 UTC:** the previous turn made
  progress by preparing/uploading the reviewed script and passing its preview.
  This continuation found no prerequisite report and no matching `sudo` or
  Python apply process, including absolute executable paths; `/proc` has no
  hidepid option. Restic remains absent and zram0 active. No live process handle
  exists to wait on and no apply was restarted. This is the second consecutive
  turn encountering the same private-sudo blocker, not a verified live wait.
  All independent prerequisite preparation is complete; root application,
  root-only commissioning inspection and their dependent checks still require
  the operator's private password step. The workstation launcher is
  `.toolbox/hermes-production-access/run-prerequisites.sh` (Bash syntax,
  ShellCheck and shfmt checks passed); it opens the pinned SSH session and runs
  exactly the current hash-named script with sudo, without changing sudo policy.
- **Blocked audit — 2026-09-28 04:39 UTC:** the previous continuation was
  no progress, not a verified wait. This third consecutive goal turn confirmed
  the same blocker: no apply process, no prerequisite report, Restic absent and
  zram0 active. Independent preparation is complete. Mark the overall goal
  BLOCKED pending the private sudo step; do not poll repeatedly, retry apply,
  weaken sudo policy or claim qualification. Resume when the operator reports
  completion or provides another concrete change in access/state, then inspect
  the report and live process state before taking further action.

### Prerequisite failure recovery — 2026-09-28

- **Resumption:** the operator ran the reviewed private sudo step and supplied
  its failure report. This is new external state; the earlier blocked audit
  is historical. Reuse the existing Restic/zram-only authorization.
- **SP-APPLY — FAIL, partial changes preserved:** Restic 0.19.1 installed,
  swap is now inactive and the persistent zram configuration override exists.
  The setup service is failed; zram0 remains initialized at 8 GiB and the
  generated unit remains until daemon reload. See the immutable
  [failure snapshot](evidence/2026-09-27-hermes-production/server-prerequisites-apply-failure-r1.json).
- **Diagnosis:** the scoped service journal reports `Device or resource busy`
  during teardown, followed by later setup attempts reporting `Device zram0
  not found` with the configuration already overridden. The precise opener
  at the original busy failure is unknown. Current zram0 has no active swap,
  mountpoint or holders; its memory-backed device has not been reset.
- **SP-RECOVERY — IN_PROGRESS:** correct the prerequisite helper to deactivate
  swap before stopping setup, verify the device is unused, reset only zram0
  when still initialized, verify the reset before clearing its failed state,
  then retain/create the persistent override and reload generators. Refuse
  busy devices and conflicting configuration; preserve all prior attempts.
  No reboot, disk/TPM changes or deployment are included.
- **Required recovery checks:** meaningful regressions for this partial-failure
  state, the original active-swap state, safe repeated execution and refusal
  of busy/mounted/backed devices or reset failures; script/lint checks,
  target preview, and live privileged application plus independent state
  checks. Mocked tests cannot substitute the live privileged gates.
- **Exact next action:** finish and test the recovery helper, publish a new
  immutable hash-named copy and update the private sudo launcher. A fresh
  SSH session still reports that sudo requires the operator's password.

- **SP-RECOVERY-PREP — PASS:** the corrected
  [helper](evidence/2026-09-27-hermes-production/server-prerequisites-recovery-r1-script.txt)
  is uploaded as `/home/aicowork/hermes-prerequisites-8ae885cbe870e579.py` with SHA256
  `8ae885cbe870e5795e8e4049cefb47ead1fbf74a4bffcbc5a66d283cc998a59f`. The
  [receipt](evidence/2026-09-27-hermes-production/server-prerequisites-recovery-r1-preparation.json)
  records a successful read-only target preview, zero active swap devices,
  the initialized zram0 and available `zramctl` 2.41.5. The earlier helper is
  preserved but superseded; the workstation launcher now selects this copy.
- **SP-RECOVERY-TEST — PASS within mocked scope:** all 17 focused cases pass;
  the preserved original transaction reproduces exactly
  `zram-setup-state-needs-review` for the reported failure state. Tests cover
  recovery, active swap ordering, repeated execution, unrelated device state,
  busy/reset/stop failures and postcondition failures. Privileged commands,
  unit transitions and device identity are mocked; filesystem checks use
  temporary fixtures. See the retained
  [test source](evidence/2026-09-27-hermes-production/server-prerequisites-recovery-r1-tests.txt)
  and [results](evidence/2026-09-27-hermes-production/server-prerequisites-recovery-r1-tests.json).
  Syntax and Ruff check/format pass. This does not establish live recovery.
- **Diagnosis evidence:** the scoped
  [journal and device state](evidence/2026-09-27-hermes-production/server-prerequisites-recovery-r1-diagnosis.json)
  are retained. The correction uses the documented
  [kernel deactivate/reset sequence](https://docs.kernel.org/admin-guide/blockdev/zram.html#deactivate);
  the inspected [zram-generator 1.2.1 reset implementation](https://github.com/systemd/zram-generator/blob/v1.2.1/src/setup.rs)
  writes the reset sysfs attribute directly. The original busy opener was not
  established, so an ordering race remains an inference, not a proved cause.
- **SP-RECOVERY-APPLY — BLOCKED on private sudo input:** the current SSH login
  still needs a password for sudo. Run the updated workstation launcher:
  `bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-access/run-prerequisites.sh`.
  It retains pinned SSH authentication and the existing sudo policy.
  This is the exact next action. After application, retrieve the new report
  and independently verify no swap, zero/absent zram device size, inactive
  units and no regenerated swap unit; inspect the sanitized root facts.
  Live recovery and live rerun verification remain NOT_RUN, as do reboot,
  TPM/recovery, production deployment and the outstanding qualification gates.

### Prerequisites verified live — 2026-09-28 13:22 UTC application

- **SP01 / SP-RECOVERY-APPLY — DONE / PASS:** the operator completed the
  corrected private sudo step; its root-owned report identifies the reviewed
  helper SHA256 and status PASS. Independent pinned-key SSH verification
  confirmed Restic 0.19.1, no active swap, zram0 absent, both units inactive,
  the root-owned `/etc/systemd/zram-generator.conf -> /dev/null` override and
  no generated zram swap unit. The post-application preview also passed.
  See the [live report and independent checks](evidence/2026-09-27-hermes-production/server-prerequisites-recovery-r1-live.json).
  The preceding private-sudo recovery blocker is resolved. Persistent
  configuration is verified; reboot behavior and a second privileged apply
  are NOT_RUN. Repeated execution passed in isolated regression tests only.
- **Root storage inspection:** all three logical volumes are linear:
  root 30 GiB, var 60 GiB and Hermes 80 GiB. The volume group has
  326333628416 bytes (approximately 303.9 GiB) unallocated. LUKS2 has one
  keyslot, no TPM tokens, no configured keyfile bypass and no `tpm2-device=auto`
  in its matching crypttab row. The inspected initramfs module list includes
  `systemd-cryptsetup` and omits `tpm2-tss`; this is the module-list check, not
  a full inventory of every embedded TPM library. No repartitioning is needed
  for the previously inspected capacity budgets.
- **Remaining outcome:** the narrow prerequisite repair is complete; the
  overall preproduction goal is incomplete. G03–G06 and physical G08 remain
  open. No reboot, TPM enrollment, recovery-key changes, application deployment,
  provider/Telegram operation or Git delivery occurred during this recovery.
- **Exact next action:** establish operator recovery-console availability and
  an encrypted off-host destination for the LUKS-header/recovery backup.
  These nonsecret inputs were requested after live verification. Then prepare
  the exact target-bound commissioning scope for approval before changing
  LUKS/crypttab/initramfs or initiating boot/power tests. Use the existing
  [private commissioning procedure](../HERMES_PRODUCTION_DEPLOYMENT.md#existing-server-preparation-and-private-commissioning)
  as the canonical source; the Restic/zram-only scope does not authorize those
  additional operations. Preserve the existing recovery slot and verify its
  passphrase privately before any enrollment. The previously completed
  synthetic localhost backup fixture is not an off-host recovery attestation.
- **Updated operator input:** physical access and knowledge of the LUKS
  passphrase are confirmed by the operator. This supports availability of a
  private console; it is not evidence of a successful recovery-unlock test.
  The backup-destination question remains unanswered. Offered either a
  separately prepared temporary encrypted recovery copy on this workstation
  or another named backup host/path; do not reuse the synthetic repository
  for actual server recovery data without an approved separate scope.
- **Recovery publication checks — PASS:** Bash syntax, ShellCheck and shfmt
  for the updated launcher; record Markdown lint; full-tree secret scan
  (499 reviewed files); source-aware migration verification (498 rows); and
  `git diff --check`. The initial record-lint spacing failures were corrected.
  Refresh record lint/provenance after this final operator-input update.

### Temporary encrypted server recovery backup — approved extension

- **Approval:** the operator selected `This workstation — temporary encrypted
  backup` for the real server's LUKS-header backup. Physical access and knowledge
  of the passphrase are operator-reported. This authorizes preparing and
  verifying the encrypted backup, with private sudo input where required;
  TPM enrollment, crypttab/initramfs changes and reboot/power tests still
  need their separate concrete commissioning scope.
- **RB01 — IN_PROGRESS:** use only `aicowork@10.0.30.10`, LUKS UUID
  `8f5a57cb-f1d7-4eb7-8d1f-266d65f8cff6`, and the encrypted `/var` filesystem
  UUID `15a5d3d9-8e39-4fb9-9631-323e7b038a65`. Stage the header root-only on
  that filesystem, encrypt it before export, and remove the plaintext staging
  file. Retain the encrypted source and copy it into a separate ignored,
  owner-only workstation directory. Preserve the synthetic backup fixture.
- **Encryption design:** dedicated local RSA-3072 recovery key and public
  certificate; OpenSSL CMS AES-256-GCM with RSA-OAEP/SHA256. The private key
  stays on this workstation in an owner-only file; only the public certificate
  reaches the server. Existing OpenSSL tools suffice; no package installation
  or network service is needed. Retain recovery instructions beside the
  encrypted copy. This is a temporary encrypted header backup, not application
  state backup or a complete disaster-recovery certification.
- **Acceptance:** synthetic encryption/decryption roundtrip, wrong-key and
  tampering rejection; guarded target preview; root-created header with matching
  UUID; encrypted transfer hash match; decryption/hash/magic verification in
  memory without a plaintext workstation file; checked safe repeated execution.
  Root application requires a private interactive sudo prompt. No disk/header
  restore or modification is part of backup creation/verification.
- **Exact next action:** prepare and validate the key, target-bound backup helper
  and workstation transfer/verification launcher, then supply its private sudo
  command. Keep the passphrase and raw header out of logs and Git.

- **RB-PREP — PASS:** a dedicated RSA recovery key remains local-only under
  ignored `.toolbox/hermes-production-recovery/`, directory 0700/key 0600.
  The public certificate SHA256 is
  `6446c3506a759740ba8340a1bd055b99d2d4aadbf1023390333178414c5628ea`.
  [Encryption checks](evidence/2026-09-27-hermes-production/server-header-backup-encryption-r1.json)
  passed for actual AES-GCM/OAEP roundtrip, wrong key and tampered authentication
  tag. OpenSSL [CMS documentation](https://docs.openssl.org/3.5/man1/openssl-cms/)
  documents these options. The private key has filesystem protection without
  an additional key passphrase; retain the entire private recovery directory.
- **RB-HELPER — PASS in tested scope:** the
  [backup helper](evidence/2026-09-27-hermes-production/server-header-backup-r1-script.txt),
  [transfer verifier](evidence/2026-09-27-hermes-production/server-header-backup-r1-client.txt)
  and [launcher](evidence/2026-09-27-hermes-production/server-header-backup-r1-launcher.txt)
  are prepared. Twelve focused cases cover actual encryption/decryption,
  transaction/client reruns, corrupt existing artifacts, wrong target/header,
  failed encryption cleanup and preview/nonroot refusal. Root ownership,
  cryptsetup, target identity and network fetch remain mocked in these cases.
  See [test source](evidence/2026-09-27-hermes-production/server-header-backup-r1-tests.txt)
  and [validation](evidence/2026-09-27-hermes-production/server-header-backup-r1-validation.json).
  Ruff, Bash syntax, ShellCheck and shfmt passed. The key is confirmed Git-ignored.
- **RB-PREVIEW — PASS:** hash-named backup helper
  `/home/aicowork/hermes-header-backup-db2ceeae744d230d.py` uploaded mode 0600;
  its read-only server preview reports only encrypted header backup creation.
  [Preparation receipt](evidence/2026-09-27-hermes-production/server-header-backup-r1-preparation.json)
  binds its full source hash, target UUID, certificate and export location.
- **RB-APPLY / RB-OFFHOST — NOT_RUN, pending private sudo:** the prepared command
  is `bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-recovery/run-header-backup.sh`.
  Run it in the operator's workstation terminal. It performs bounded root
  header-backup/encryption, transfers only ciphertext and nonsecret metadata,
  then verifies decryption/hash/LUKS2 magic in memory. The expected local result
  is `backup/header.cms` plus server/verification reports beneath the ignored
  recovery directory. Recovery instructions are in its owner-only `RECOVERY.md`.
  Matching reruns retain the same encrypted artifact; conflicts fail closed.
  No actual backup exists yet in the evidence captured so far. This private
  sudo command is the exact next action, followed by independent retrieval
  and verification. Enrollment, recovery-unlock and boot gates remain open.
- **RB publication closure — PASS:** all 55 local record links exist; Markdown
  lint, the full-tree secret scan (506 reviewed files), source-aware manifest
  verification (505 rows) and diff whitespace checks passed. Cryptsetup is not
  installed in the existing Toolbox, so a real synthetic LUKS-format/header
  roundtrip was NOT_RUN; the reviewed target's cryptsetup 2.8.8 will perform
  the real bounded header export and UUID/metadata checks during private apply.
  A single post-preparation check found no server encrypted-backup report and
  no local verification report yet. Preparation is complete; RB application
  remains pending the supplied private sudo command. Preserve this handoff
  without repeated polling or changing boot/enrollment configuration.

### Real recovery backup verified — 2026-09-28

- **RB01 / RB-APPLY / RB-OFFHOST — DONE / PASS in header-copy scope:** the
  operator ran the prepared launcher. The server exported and encrypted a
  16777216-byte LUKS2 header with one keyslot. The workstation copy decrypted
  successfully with matching authentication, hash, size and LUKS2 magic.
  Independent pinned-SSH fetch and local verification were repeated; existing
  ciphertext/reports remained byte-identical. See the immutable
  [live verification](evidence/2026-09-27-hermes-production/server-header-backup-r1-live.json).
- **Identity:** LUKS UUID `8f5a57cb-f1d7-4eb7-8d1f-266d65f8cff6`;
  ciphertext SHA256
  `4d97171dce96796aa757e64342810a94880917fd40a34f6530ba908c2005478c`;
  plaintext header SHA256
  `c31f7d66d048401b6b03b219b8a05a06e20aef1df5962549ab1ab63499d2b03a`.
  Recovery materials are retained in the ignored owner-only workstation
  directory `.toolbox/hermes-production-recovery/`. The private key is 0600,
  single-link and was not included in evidence. Preserve this entire directory.
- **Scope limits:** this is a real encrypted off-host header copy, not a disk
  restore, application backup/restore, recovery-unlock or production acceptance.
  A second privileged header export is NOT_RUN; repeated server application
  remains covered by synthetic transaction tests. The live workstation
  transfer/decryption rerun is PASS. No TPM token or boot change was made.
- **Timestamp explanation:** the server's export timestamp is later than the
  first workstation verification timestamp because its clock is approximately
  27.31 seconds ahead. Current read-only
  [clock evidence](evidence/2026-09-27-hermes-production/server-clock-and-enrollment-intake-r1.json)
  shows server NTP enabled/synchronized and workstation NTP disabled/not
  synchronized. Preserve both original timestamps; clock configuration was
  not changed. Match these artifacts by their verified hashes, not by assumed
  wall-clock ordering across the two machines.

### BC01 — proposed TPM/boot commissioning scope; not yet authorized

- **Target and outcome:** configure automatic TPM2 unlock for the identified
  LUKS2 volume on `aicowork@10.0.30.10`, preserve its existing recovery
  passphrase slot and verify attended boot/recovery behavior. All mutations
  below remain pending approval; this proposal does not grant authorization.
  Follow the [canonical private commissioning procedure](../HERMES_PRODUCTION_DEPLOYMENT.md#existing-server-preparation-and-private-commissioning).
- **BC-A private checks:** at the physical console, test the known LUKS
  passphrase without opening another mapping or changing keyslots. Recheck
  target UUIDs, Secure Boot, existing keyslots/tokens, backup identities and
  relevant firmware power-restoration policy before capturing PCR7. The
  passphrase is supplied only to the private terminal prompt. Failure stops
  enrollment and leaves the currently running server available.

  ```bash
  sudo cryptsetup open --test-passphrase --type luks2 \
    /dev/disk/by-uuid/8f5a57cb-f1d7-4eb7-8d1f-266d65f8cff6
  ```

- **BC-B enrollment:** after BC-A passes, add one TPM2 token using SHA256 PCR7
  and no PIN. Retain the existing recovery slot. A matching existing token
  is verified and reused; an unexpected token/slot change stops for review.
  Enrollment without slot wiping uses the repository's explicit policy:

  ```bash
  sudo systemd-cryptenroll --tpm2-device=auto --tpm2-pcrs=7:sha256 \
    --tpm2-with-pin=no \
    /dev/disk/by-uuid/8f5a57cb-f1d7-4eb7-8d1f-266d65f8cff6
  ```

- **BC-C boot configuration:** retain protected copies of the affected
  configuration and current initramfs before replacing them. Update only the
  matching `/etc/crypttab` row with `tpm2-device=auto`; ensure its keyfile field
  still has no bypass. Add a scoped dracut configuration for
  `systemd-cryptsetup` and `tpm2-tss`, rebuild the current kernel's initramfs,
  and inspect its modules. Preserve unrelated rows, boot entries and storage.
  Repeated setup must converge without duplicate options or TPM tokens.
  Validate available space and installed modules before any replacement.
- **BC-D attended tests:** after configuration verification and confirmation
  that the operator is at the physical console, perform automatic reboot,
  complete shutdown/cold-start, passphrase recovery followed by automatic
  boot, and operator-assisted physical power-restoration verification.
  Capture boot IDs, scoped sanitized service status and distinct operator
  attestations; do not treat ordinary SSH reconnection as a recovery proof.
  Failure pauses further boot tests and retains recovery/diagnostic access.
- **Acceptance:** one matching PCR7/SHA256/no-PIN TPM token; original recovery
  slot retained; matching crypttab/initramfs checks pass; successful private
  passphrase check and each attended reboot/cold-start/recovery/power proof.
  Application deployment, provider/Telegram operations, unrelated storage,
  OS upgrades, header restoration and slot wiping are outside this proposal.
- **Authority and exact next action:** obtain one approval for BC-A through
  BC-D, or a narrower BC-A through BC-C approval with all reboot/power actions
  deferred. The user-approved goal requires explicit named-resource approval
  before privileged deployment/commissioning operations; the supplied global
  AGENTS instructions require explicit authorization for production changes.
  The repository also requires explicit authorization for credential
  provisioning ([AGENTS.md](../../AGENTS.md#safety-and-evidence)). The previous
  Restic/zram and header-backup approvals do not cover TPM/boot changes.
- **Authoritative command references:** installed cryptenroll help confirms
  the relevant options; [systemd 259 enrollment source](https://github.com/systemd/systemd/blob/v259/man/systemd-cryptenroll.xml)
  documents explicit PCR policy, and
  [cryptsetup 2.8.8 open documentation](https://gitlab.com/cryptsetup/cryptsetup/-/blob/v2.8.8/man/cryptsetup-open.8.adoc)
  covers the private passphrase-test operation. No commands in this proposed
  commissioning section have been executed.

### BC01 approval and implementation resumption

- **Approval evidence:** after the completed backup and next-stage scope were
  explained, the operator instructed `proceed`. Reuse this approval for BC-A
  through BC-D on the named server/LUKS UUID. No further scope approval is
  needed for the stated steps. Boot/power tests still require the operator's
  physical-console readiness, which is a timing prerequisite rather than
  another request to authorize the same actions.
- **BC01 — IN_PROGRESS:** prepare a guarded private-console entrypoint with
  target/backup checks, operator firmware-policy confirmation, private
  passphrase verification, one matching TPM enrollment, exact crypttab/dracut
  changes, retained configuration/initramfs copies and post-change inspection.
  Secret prompts remain attached to the private terminal; reports contain
  only sanitized status. Do not initiate reboot from the setup entrypoint.
- **Required checks:** preserve the original recovery keyslot, refuse a wrong
  target or unexpected TPM policy, validate a matching-token rerun, prove
  exact-row crypttab editing and failed-build recovery with isolated tests,
  and execute the target preview before the private root step. Independently
  inspect the resulting report before any attended boot test.
- **Exact next action:** inspect and reuse applicable maintained enrollment
  tooling, implement only necessary target-specific guards, then validate and
  publish the reviewed console command. The approved backup remains retained.
- **Firmware readiness input:** the operator confirmed that BIOS/UEFI
  `Restore on AC Power Loss` is already set to `Power On`. Record this as an
  operator attestation; actual wall-power restoration remains NOT_RUN.
- **Read-only boot intake:** current kernel `6.19.10-300.fc44.x86_64`, Secure
  Boot enabled, `/boot` UUID `1947d07c-1b67-4341-b196-65dbdce0fddc`;
  dracut lists both required modules. The current initramfs is 74140815 bytes,
  root-owned 0600; crypttab is root-owned 0600. Preserve these permissions.
  The proposed `99-hermes-production-tpm.conf` does not exist.
- **Reuse decision:** inspected maintained `manual/boot/tpm-enroll.sh` and
  production preflight policy. Preserve those package inputs. The manual
  helper directly rebuilds the live image and stages plaintext headers;
  target-specific guarded execution instead needs a validated candidate image,
  protected configuration/image backups and the already verified encrypted
  header copy. Reuse its explicit PCR7/SHA256/no-PIN policy and production
  token checks, without expanding to its slot-wiping revert mode.
- **BC-PREP / BC-PREVIEW — PASS:** the reviewed
  [target-bound helper](evidence/2026-09-27-hermes-production/server-boot-commission-r1-script.txt)
  is uploaded at `/home/aicowork/hermes-boot-commission-7bb3791ac872f42a.py` with SHA256
  `7bb3791ac872f42a8e94a7ee9d0e1c193bdd70b8dc711c0042a8694fa060bfe9`. Its unprivileged server preview passes all available
  target/kernel/Secure-Boot/module/path checks. Sensitive root checks remain
  deferred to the private apply. See the
  [preparation receipt](evidence/2026-09-27-hermes-production/server-boot-commission-r1-preparation.json).
- **BC-TEST — PASS within isolated scope:** 17 cases cover exact-row editing,
  slot/policy checks, real-file backups/permissions, matching-token reruns,
  failed or interrupted build rollback, invalid embedded crypttab, failure
  after image publication, recovery-copy/configuration drift and explicit
  rollback-failure reporting. See
  [test source](evidence/2026-09-27-hermes-production/server-boot-commission-r1-tests.txt)
  and [validation](evidence/2026-09-27-hermes-production/server-boot-commission-r1-validation.json).
  Root ownership, TPM, cryptsetup, dracut, SELinux and hardware are mocked;
  live boot acceptance is not established. Initial test-source formatting
  diagnostics were corrected; Ruff check/format now pass. Bash syntax,
  ShellCheck and shfmt pass for the
  [launcher](evidence/2026-09-27-hermes-production/server-boot-commission-r1-launcher.txt).
- **Setup behavior:** privately test the original slot with external tokens
  disabled, enroll once if absent, test that same passphrase slot again,
  retain original crypttab/image under root-only
  `/var/lib/hermes-production-boot/baseline/`, build and validate a candidate
  initramfs, then atomically replace the current image. Configuration/build
  failures attempt to restore the original configuration/image; an added TPM
  token is retained with the recovery slot and never wiped automatically.
  The script saves a sanitized root-owned report and never reboots. Existing
  unexpected policy/configuration changes fail closed instead of being merged.
- **BC-A/B/C live application — NOT_RUN:** at the server's private console run
  `sudo python3 -I /home/aicowork/hermes-boot-commission-7bb3791ac872f42a.py --apply`.
  The workstation alternative is
  `bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-boot/run-boot-setup.sh`,
  which opens the pinned private SSH terminal. The first setup normally asks
  for the LUKS passphrase three times: before enrollment, to enroll, and to
  verify that the original slot remains usable. Enter it only at those private
  prompts; it is never captured by the helper. This is the exact next action.
  After it returns, inspect `/var/lib/hermes-production-boot/report.json` and
  independently check the live configuration before BC-D attended tests.
- **Approval remains valid:** the pending private input is a credential and
  console interaction prerequisite, not another authorization request.
  BC-D reboot/power actions await successful configuration evidence and the
  operator's confirmation of physical-console readiness. The overall goal
  remains incomplete and repository changes remain uncommitted.
- **BC publication closure — PASS:** the prepared helper/launcher are frozen
  to the receipt hashes; 64 local record links exist; Markdown lint, full-tree
  secret scan (513 reviewed files), source-aware migration verification
  (512 rows) and diff whitespace checks pass. The local boot directory and
  launcher are owner-only 0700. Previous immutable evidence remains retained.
  No live TPM enrollment/configuration or reboot has been observed by the
  agent at this handoff; await the prepared private command's report.

### BC live failure and identity-format correction

- **Continuation classification:** the preceding turn made progress by preparing
  and validating the approved helper. This continuation found a completed
  apply report rather than a live process; the operator then supplied its
  matching terminal output. It is new authoritative state, not a wait.
- **BC-A / BC-B — PASS within setup scope:** the reviewed helper reports the
  recovery passphrase passed before enrollment, TPM token added at keyslot 1,
  and the original recovery passphrase passed afterward. No reboot occurred.
  **BC-C — FAIL:** candidate inspection returned `crypttab-target-row-count`.
  The failure snapshot is retained in
  [continuation evidence](evidence/2026-09-27-hermes-production/server-boot-commission-continuation-r1.json).
  No matching helper process remains. The current image still has its original
  74140815-byte size and the scoped dracut file is absent, consistent with the
  helper's completed rollback path. Full root hashes remain to be rechecked
  by the corrected helper before retrying.
- **Diagnosis:** installed dracut `70crypt/module-setup.sh` lines 105–106
  canonicalize `UUID=...` to `/dev/disk/by-uuid/...`; lines 134/139 emit that
  canonical device path into the embedded crypttab. The verifier only accepts
  the host crypttab's `UUID=` spelling. Correct the embedded-image check to
  accept exactly those two representations of the same pinned UUID; retain
  strict host-file matching, one-row count, keyfile and TPM-option guards.
- **BC-R2 — IN_PROGRESS:** add positive/negative alias regressions and exercise
  the original/corrected check with the server's actual `lsinitrd` on disposable
  synthetic CPIO images. Preserve the original helper/report. Publish a new
  hash-named helper and update the launcher after passing these checks. Reuse
  the enrolled token and original protected baseline; do not enroll another
  token, wipe slots or reboot during the retry.
- **Exact next action:** validate this identity-format correction, then rerun
  the scoped private setup. Same-scope approval remains valid; no new operation
  permission is needed, but private sudo/LUKS input remains necessary.

### BC-R2 validated private retry

- **Correction — PASS within tested scope:** 20 isolated cases pass, including
  the canonical embedded device spelling, rejection of duplicate aliases,
  wrong device identity, keyfile bypass and conflicting TPM options. The
  server's actual `lsinitrd` reproduced the original failure with synthetic
  CPIO, accepted the corrected helper and rejected four unsafe variants.
  These tests do not establish acceptance of a privileged live build or boot.
- **Published replacement:**
  [helper](evidence/2026-09-27-hermes-production/server-boot-commission-r2-script.txt),
  [test source](evidence/2026-09-27-hermes-production/server-boot-commission-r2-tests.txt),
  [launcher](evidence/2026-09-27-hermes-production/server-boot-commission-r2-launcher.txt)
  and [preparation receipt](evidence/2026-09-27-hermes-production/server-boot-commission-r2-preparation.json)
  retain the correction and installed dracut source evidence. Server path:
  `/home/aicowork/hermes-boot-commission-9a4c0ff7d97b202c.py`; SHA256:
  `9a4c0ff7d97b202c49d2bfce39b2834fdf1becc45b4e8bb322c3665035891e0d`.
  Unprivileged target preview, Ruff check/format, launcher Bash syntax,
  ShellCheck and shfmt pass; the
  [validation receipt](evidence/2026-09-27-hermes-production/server-boot-commission-r2-validation.json)
  binds the tested source identities. The original helper and failure are retained.
- **BC-C corrected live application — NOT_RUN:** run
  `bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-boot/run-boot-setup.sh`
  from the workstation's private terminal. The matching TPM token is reused;
  expect two private recovery-passphrase tests, plus sudo authentication if
  needed. The helper checks the protected baseline and existing TPM policy
  before rebuilding. It performs no reboot and never removes a keyslot.
- **Exact next action:** collect the corrected root report and independently
  inspect available live state after this private command. BC-D attended
  tests remain NOT_RUN until setup passes and physical-console readiness is
  confirmed. The overall goal remains incomplete; the private credential
  interaction is the current dependency, not a new permission request.
- **BC-R2 publication checks — PASS:** full-tree secret scan reviewed 519
  files with no findings, all three frozen helper identities match the
  working files, Markdown lint and diff whitespace checks pass. Source-aware
  migration verification passes with 518 rows. Refresh record links and
  provenance once more after this status-only closure update.
- **Continuation after publication — private input still pending:** a fresh
  pinned SSH inspection finds no running apply process, the unchanged boot ID
  `87e1d398-7465-4586-a77d-4eaf03245b73`, and the original R1 failure report
  timestamped `2026-09-28T14:28:44.965088+00:00`. The corrected R2 private
  apply has not produced a report. This is not a verified wait on a live
  process. The preceding turn made progress by correcting and validating R2;
  this continuation cannot advance BC-C without private sudo/LUKS input.
  Keep the goal active and the same exact private command above; no further
  permission is needed and no reboot or new enrollment is initiated.
- **Blocked audit — threshold reached:** the private-input dependency has
  remained through the R2 handoff and two consecutive continuations. The
  latest pinned SSH check again finds no active apply process and the same
  original failure report/boot ID. The preceding continuation made no
  progress toward live acceptance; its record refresh did not resolve the
  dependency. Mark the goal BLOCKED, not complete. No independent authorized
  action can satisfy the remaining live gates without private commissioning,
  operator console participation or the outstanding fixture/live-test inputs.
  Resume from the exact R2 command above and inspect its report before any
  boot operation. All existing same-scope authorizations remain valid.

### BC-C live PASS and BC-D attended reboot preparation

- **Resumption evidence:** the operator completed the corrected private setup
  and supplied its PASS report. Pinned SSH independently retrieved the
  matching root-owned report at `2026-09-28T16:07:34.435256+00:00`; retain
  [live setup evidence](evidence/2026-09-27-hermes-production/server-boot-commission-r2-live.json).
  The prior private-setup blocker is resolved. No matching apply process
  remains and the boot ID is still `87e1d398-7465-4586-a77d-4eaf03245b73`.
- **BC-A/B/C — PASS within setup scope:** both original-slot passphrase tests
  pass; TPM enrollment is `UNCHANGED`, the recovery slot is preserved and
  configuration is `UPDATED`. The root helper verified and published image
  SHA256 `26462706a0cb7cf18bda8563cafab2280381177715f32f0133eac6907b280378`;
  crypttab SHA256 is
  `c1d4d852af5786dc38601e75cddf3ba0657268e74ac595f3b4b61f1146202fe6`.
  These protected-file hashes are from the reviewed root helper, not an
  unprivileged rehash. Independent metadata confirms root ownership, image
  and crypttab mode 0600, protected baseline directory 0700 and the expected
  scoped dracut content. Secure Boot enabled, SELinux enforcing, system
  running, no failed units and no active swap are observed independently.
- **Remaining boot-selection check:** unprivileged `grubby --default-kernel`
  returned exit zero with a permission error and invalid `/boot` output.
  Do not count that as PASS. Default kernel and initramfs selection must be
  checked under private sudo immediately before reboot. The guarded helper
  also rejects a nonempty GRUB `next_entry`, unexpected file hashes, another
  boot ID, wrong root filesystem, unhealthy system or disabled security state.
  The [grubby upstream manual](https://github.com/rhboot/grubby/blob/main/grubby.8)
  documents the read-only boot selection queries; no boot entries are edited.
- **BC-D1 preparation — PASS within tested scope:**
  [guard](evidence/2026-09-27-hermes-production/server-attended-reboot-r1-script.txt),
  [tests](evidence/2026-09-27-hermes-production/server-attended-reboot-r1-tests.txt),
  [launcher](evidence/2026-09-27-hermes-production/server-attended-reboot-r1-launcher.txt)
  and [receipt](evidence/2026-09-27-hermes-production/server-attended-reboot-r1-preparation.json)
  are retained. Eight isolated tests pass with reboot/privileged commands
  mocked, including actual guard refusal for changed boot ID, file hash,
  default kernel/initramfs and one-shot selection. Ruff, Bash syntax,
  ShellCheck and shfmt pass. Server preview performs no reboot. Script SHA256:
  `3f403c355734681ce363e74d0d233fe9db70f51ddc5960f902d64a9a37d0ffa4`.
- **Physical-console readiness — OPERATOR_CONFIRMED:** the user answered
  `Ready at the console now`. Existing BC-D approval is reused. The
  workstation command is
  `bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-boot/run-attended-reboot.sh`.
  It opens pinned SSH for private sudo, verifies the exact completed setup
  and default entry, then requests `systemctl reboot`. It performs no
  enrollment, configuration editing or power-off. The pinned preboot ID
  prevents replay after a completed reboot. Reboot is NOT_RUN until observed.
- **BC-D1 acceptance / exact next action:** after the command runs, compare
  boot IDs, expected kernel, storage and credential-free service/security
  state through pinned SSH. Require a separate operator observation that
  the login screen appeared without entering a LUKS passphrase. SSH
  reconnection alone does not prove automatic unlock. If a passphrase prompt
  appears, retain console access and diagnose before continuing. Cold start,
  recovery boot followed by automatic boot, wall-power restoration and all
  remaining application/fixture gates stay NOT_RUN or BLOCKED as recorded.
- **Publication closure — PASS:** Markdown lint, 75 local record links,
  all three frozen reboot artifact identities, full-tree secret scan of 524
  files, source-aware migration verification with 523 rows and diff whitespace
  checks pass. A subsequent pinned SSH snapshot still has the original boot
  ID and no running reboot guard. The operator has the private command;
  observed automatic reboot and console result remain pending.

### BC-D1 selection refusal and automatic kernel detection

- **BC-D1 first attempt — REFUSED:** the reviewed guard reported
  `default-kernel-mismatch` before requesting reboot. The operator then ran
  `sudo grubby --default-kernel` and reported
  `/boot/vmlinuz-7.2.7-200.fc44.x86_64`. Independent SSH inventory confirms
  both 6.19.10 and 7.2.7 kernel-core packages and boot images, with the server
  still running 6.19.10 and its original boot ID. Both required dracut modules
  are available for 7.2.7. Preserve
  [refusal evidence](evidence/2026-09-27-hermes-production/server-attended-reboot-r1-refusal.json).
  The 6.19.10 setup PASS remains valid for that image; it does not validate
  the separate default 7.2.7 image. No kernel package was installed by this
  correction and the default selection is not changed.
- **Operator-directed improvement:** the user asked to detect the kernel
  automatically. The helper now reads the root-visible GRUB default, verifies
  an ordinary Fedora44 x86_64 kernel path, its installed kernel-core package
  and module directory, and saves a target/boot-ID binding. A changed default
  on retry or before reboot is refused. It never chooses the build kernel
  solely from `uname -r`. The canonical commissioning
  [runbook](../HERMES_PRODUCTION_DEPLOYMENT.md#existing-server-preparation-and-private-commissioning)
  now describes this distinction. Existing commissioning/reboot approval and
  confirmed physical-console readiness apply to this correction on the same
  server; the private command states its image-build and reboot effects.
- **Selected-image preparation — PASS within isolated scope:**
  [source](evidence/2026-09-27-hermes-production/server-selected-kernel-r1-script.txt),
  [tests](evidence/2026-09-27-hermes-production/server-selected-kernel-r1-tests.txt),
  [test output](evidence/2026-09-27-hermes-production/server-selected-kernel-r1-test-output.txt),
  [launcher](evidence/2026-09-27-hermes-production/server-selected-kernel-r1-launcher.txt)
  and [receipt](evidence/2026-09-27-hermes-production/server-selected-kernel-r1-preparation.json)
  are retained. Eighteen tests cover independent default/running versions,
  unsafe/rescue paths, package mismatch, selection drift, real-file backup,
  publication, no-op rerun, rollback/retry, interruption, explicit rollback
  failure and guarded reboot. Root ownership, TPM, dracut, SELinux and reboot
  remain mocked. Ruff, Bash syntax, ShellCheck and shfmt pass; server preview
  passes its unprivileged checks and defers root selection to private apply.
  Script SHA256:
  `d688d44d0bdae66bbadd4b596c9c573715c32197146d605847ccb160d1691c83`.
- **Behavior and preserved state:** reuse the hash-verified R2 image verifier
  and original TPM/recovery baseline. Retain the selected kernel's original
  image under a separate root-only baseline directory, build a candidate,
  verify TPM modules and embedded crypttab, and atomically publish only that
  image. Failed build/publication attempts restore the selected original and
  report rollback failures. Existing crypttab, scoped dracut configuration,
  TPM token, recovery slot and older image/baseline are not edited. A selected
  running kernel already validated by R2 reuses that image without rebuilding.
  Recheck target selection, original setup, TPM policy and image before
  requesting reboot. Reports distinguish `READY_TO_REBOOT` from boot proof.
- **Exact next action / live apply — NOT_RUN:** from the workstation's
  private terminal run
  `bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-boot/run-selected-kernel-reboot.sh`.
  This supersedes the earlier attended-reboot command for this attempt. It
  asks only for sudo authentication, rebuilds the detected default image if
  needed and reboots after checks pass. Read
  `/var/lib/hermes-production-boot/selected-kernel-report.json`, then require
  the changed boot ID, detected expected kernel, credential-free health and
  separate console observation of no-passphrase unlock. The boot-ID binding
  refuses another run after a completed reboot. Other mandatory gates remain
  open and production acceptance is not claimed.
- **Packaged documentation identity refreshed — PASS:** the runbook is a
  bundled input, so prior artifact
  `834adb288d5ebdec3a700426fdd054801be3dfa10010534731b8e32939851df8`
  is STALE for the updated documentation. A fresh retained-OCI test-signature,
  safe-extraction and candidate-rejection roundtrip produces artifact
  `7de0e45f99b8208b3b203e1e297760c44c11de68356e54449bbffc8a5905b1ab`;
  [package evidence](evidence/2026-09-27-hermes-production/bundle-kernel-selection-runbook.json)
  verifies that only `source/PRODUCTION_RUNBOOK.md` changed among the 38
  packaged entries. Executable sources, OCI images and receiver identity are
  unchanged; their existing offline evidence remains applicable. Temporary
  test keys/archive were removed. This does not qualify the candidate for
  production or advance any unperformed runtime/boot/application gate.
- **Latest live snapshot:** the selected-kernel report is absent, no matching
  apply-and-reboot process is running, and the original boot ID is unchanged.
  The prepared private command and subsequent console observation are the
  next dependencies; this is not a wait on a live job.

### BC-D1 selected-kernel reboot observed

- **Live apply — PASS within image/setup scope:** the operator ran the
  automatic-selection command. Its root report at
  `2026-09-28T16:34:50.068291+00:00` identifies selected kernel
  `7.2.7-200.fc44.x86_64`, configuration `UPDATED`, retained recovery slot,
  unchanged TPM enrollment and image SHA256
  `f8a7bfe4ce5c15cc1896cfdcc8f81405f3fd2c3377f6ea9b1ee9a8e150a0f44e`.
  Its selected-image baseline is retained under
  `/var/lib/hermes-production-boot/selected-kernel-7.2.7-200.fc44.x86_64`.
  `READY_TO_REBOOT` is a pre-reboot result, not a claim of automatic unlock.
- **Actual reboot and post-boot health — PASS:** pinned SSH reads a new boot
  ID, `cf087d12-cf0e-43a3-85df-bb4225213e33`, and the expected 7.2.7 kernel.
  Root, var, Hermes and boot filesystem UUIDs match; the LUKS cryptsetup unit
  is active/exited; the system is running with no failed units. Secure Boot
  is enabled, SELinux enforcing and swap absent. Retain
  [post-reboot evidence](evidence/2026-09-27-hermes-production/server-selected-kernel-r1-post-reboot.json),
  including the independently retrieved root report and its SHA256
  `961ac7b4035ed12f19f813f38cca4146e9d5dbddc21c35cd5a9097d4ea7a7256`.
  The preceding turn made progress by implementing and validating automatic
  selection; this turn observes a completed build and a different live boot.
- **Automatic-unlock attestation — PENDING:** ask whether the physical
  console reached login without entering the LUKS passphrase. SSH success,
  an active encrypted mapping and the root setup report do not independently
  answer that question. Do not mark BC-D1 automatic reboot PASS until the
  operator observation is received.
- **Next attended cycle, after that observation:** use a clean shutdown at
  the server console, `sudo systemctl poweroff`, and wait until it is fully
  off. Disconnect then restore its AC supply without pressing the power
  button. Record separately whether restoration powers it on automatically
  and whether a fresh cold boot reaches login without a LUKS passphrase;
  compare the resulting boot ID and health through pinned SSH. This one
  cycle can provide distinct cold-start and firmware-power-restoration
  observations; it is not an abrupt-running-power-loss or application
  crash-recovery test. No shutdown or physical power test has run yet.
- **Exact next action:** receive the already requested BC-D1 console
  observation before starting the next cycle. Cold start, recovery boot and
  subsequent automatic boot, firmware restoration, fixture/application
  qualification and the overall goal remain incomplete. Do not rerun the
  previous build/reboot command now that its preboot ID has changed.

### BC recovery preparation while console observation is pending

- **Continuation classification:** the preceding goal turn made progress by
  observing the completed reboot and capturing its new kernel/boot ID and
  healthy state. The requested no-passphrase console observation remains
  unanswered; no new reboot or power action is initiated during this turn.
- **Non-destructive recovery method — generator verification PASS:**
  [systemd 259 generator documentation](https://github.com/systemd/systemd/blob/v259/man/systemd-cryptsetup-generator.xml)
  defines a UUID-specific `rd.luks.options=` override confined to the initrd.
  The [generator implementation](https://github.com/systemd/systemd/blob/v259/src/cryptsetup/cryptsetup-generator.c)
  selects that override instead of the matching crypttab options. The
  [cryptsetup implementation](https://github.com/systemd/systemd/blob/v259/src/cryptsetup/cryptsetup.c)
  selects TPM operation when a TPM device option is present. This supports
  a one-boot recovery-slot override without deleting any enrolled token.
- **Installed implementation tested:** the server's actual generator ran as
  UID 1000 against disposable synthetic crypttab/UUID/cmdline inputs. Eight
  cases cover normal TPM options, recovery-only options, wrong-UUID isolation
  and initrd-only scope, each with `UUID=` and `/dev/disk/by-uuid/` spellings.
  Generated recovery commands omit `tpm2-device` and contain
  `discard,key-slot=0,password-cache=no,headless=no`; normal/wrong-UUID/host
  cases retain TPM auto. Synthetic input files remained unchanged and all
  temporary output was removed. No generated unit was activated, and no
  block device, boot entry, real crypttab or keyslot was modified. See
  [test source](evidence/2026-09-27-hermes-production/server-recovery-generator-r1-script.txt)
  and [result](evidence/2026-09-27-hermes-production/server-recovery-generator-r1.json).
- **Prepared later recovery test — NOT_RUN:** after the pending automatic
  reboot observation and the attended cold/power cycle, temporarily append
  this single parameter to the selected kernel's GRUB editor line for one
  boot only:
  `rd.luks.options=8f5a57cb-f1d7-4eb7-8d1f-266d65f8cff6=discard,key-slot=0,password-cache=no,headless=no`.
  Observe a real LUKS prompt and privately enter the known recovery passphrase.
  Inspect the resulting boot ID, expected one-boot kernel argument, storage
  and health, then boot normally again and verify no-passphrase automatic
  unlock. Do not save the override to persistent GRUB configuration. This
  is a prepared method supported by installed-generator evidence, not live
  recovery proof; physical firmware/menu interaction remains necessary.
- **Exact next action unchanged:** receive the original reboot's console
  observation before performing the next attended cycle. Further fixture,
  restore, application/provider and full qualification gates remain open.
- **Console-observation blocked audit — threshold reached:** the same
  missing observation remains through the reboot-result turn and two goal
  continuations. The preceding continuation made independent progress by
  testing the later recovery method; that preparation is now complete.
  Latest pinned SSH state still shows boot ID
  `cf087d12-cf0e-43a3-85df-bb4225213e33`, kernel 7.2.7, system running and no
  active commissioning process. This is not a verified wait. No remaining
  authorized independent action can supply the missing physical observation
  or satisfy the other private/live prerequisites. Mark the goal BLOCKED,
  not complete. Resume when the operator states whether login appeared
  without entering a LUKS passphrase; retain the prepared cold/power and
  recovery procedures and all existing same-scope approvals.

### BC-D1 automatic reboot PASS; BC-D2 cold/power cycle

- **Console observation received:** in answer to whether login appeared
  without a LUKS passphrase, the operator stated `didn´t reach LUKS, the
  server is online and working`. Record this as no LUKS prompt and an online,
  working server. Together with the independently observed new boot ID,
  selected 7.2.7 kernel, storage and security/service health, BC-D1 automatic
  reboot is PASS. See
  [automatic-reboot attestation](evidence/2026-09-27-hermes-production/server-automatic-reboot-r1.json).
  The former console-observation blocker is resolved; it is not another
  authorization request.
- **Pre-cycle baseline:** fresh pinned SSH at server time
  `2026-09-28T16:57:08.334820+00:00` still shows boot ID
  `cf087d12-cf0e-43a3-85df-bb4225213e33`, kernel 7.2.7, system running,
  no failed units, Secure Boot enabled, SELinux enforcing and no swap.
- **BC-D2 operator procedure issued:** at the server console run
  `sudo systemctl poweroff`; wait for full shutdown, disconnect AC, wait
  ten seconds and reconnect AC without pressing the power button. Observe
  automatic power-on and whether login appears without a LUKS prompt.
  Existing BC-D authority covers the cycle. The operator initiates it at
  the console; no remote shutdown has been performed by the agent.
- **Acceptance and exact next action:** obtain the already requested
  physical observations and inspect pinned SSH for a changed boot ID,
  expected kernel, four filesystem UUIDs, cryptsetup state, service health,
  Secure Boot, SELinux and absence of swap. Mark cold-start and firmware
  restoration separately from those observations. Until then both remain
  NOT_RUN. If the machine stays off or requests LUKS input, record that
  result before remediation. Recovery and subsequent automatic boot remain
  later gates; the prepared one-boot override is not applied during this
  normal cold-start cycle. Overall qualification remains incomplete.

### BC-D2 cold start and AC restoration PASS; BC-D3 recovery boot

- **Operator result:** after the instructed clean shutdown and AC cycle,
  the user reported `it worked, started automatically and no luks was
  requested`. Record distinct PASS observations for automatic firmware
  power-on after AC restoration and cold boot without a LUKS prompt.
  This is operator evidence of the physical actions, combined with
  independently checked runtime state; it is not an instrumented power trace.
- **Independent cold-boot verification — PASS:** pinned SSH shows a new boot
  ID, `01760717-a7ef-49a4-a424-c799e37921fb`, kernel 7.2.7, all four expected
  filesystem UUIDs, the encrypted-root service active/exited, system running
  and no failed units. Secure Boot remains enabled, SELinux enforcing, swap
  absent and no temporary `rd.luks.options` parameter is present. Retain
  [cold/power evidence](evidence/2026-09-27-hermes-production/server-cold-power-r1.json).
  BC-D2 cold start and firmware power restoration are PASS within the clean
  shutdown/physical AC-cycle scope. Abrupt running power loss is NOT_RUN.
- **BC-D3 procedure issued under existing approval:** reboot at the physical
  console; select the normal 7.2.7 GRUB entry and press `e`. Append the exact
  previously verified UUID-specific recovery parameter to the `linux` or
  `linuxefi` line, then boot with `Ctrl+X`. The operator enters the existing
  recovery passphrase only at the private LUKS prompt. The
  [GRUB menu editor](https://www.gnu.org/software/grub/manual/grub/html_node/Menu-entry-editor.html)
  supports editing that boot entry in memory. No persistent boot entry,
  crypttab, initramfs, keyslot or TPM token is changed by this procedure.
- **Recovery acceptance / exact next action:** require an observed LUKS
  prompt and successful private passphrase entry. Leave that recovered boot
  running while the agent checks its new boot ID, expected kernel, exact
  one-boot parameter, filesystems and security/service health. Only after
  that evidence is captured perform the final unedited reboot and require
  no-passphrase unlock plus independent health again. The prepared generator
  checks are supporting evidence only; BC-D3 recovery and BC-D4 subsequent
  automatic boot remain NOT_RUN until their actual observations arrive.
  The broader fixture, runtime, restore and provider gates remain open.

### BC-D3 recovery boot remote validation PASS; console observation pending

- **User request:** validate the server after the issued one-boot recovery
  procedure. Read-only pinned SSH captures boot ID
  `4cea93af-9409-42b1-a5c2-ad4c8d8cfd60`, different from the preceding cold
  boot, and running kernel `7.2.7-200.fc44.x86_64`.
- **Remote acceptance — PASS:** the command line contains exactly the
  requested UUID-specific `discard,key-slot=0,password-cache=no,headless=no`
  recovery override. All four filesystem UUIDs match, the LUKS service is
  active/exited, the system is running with no failed units, Secure Boot is
  enabled, SELinux is enforcing and swap is absent. The retained
  [remote recovery evidence](evidence/2026-09-27-hermes-production/server-recovery-boot-r1-remote.json)
  records server time `2026-09-28T20:28:31.081957+00:00`, explicit expected
  checks and no failures; SHA256
  `3c01bf6f73b350ec3c692c75118f1303124cd62af2aa7c911db6cad2139f5c92`.
  No server configuration, keyslot, token or boot entry was changed by
  validation.
- **Evidence boundary:** SSH establishes the recovery-configured boot and
  its healthy runtime state. It does not independently observe a physical
  LUKS prompt or private passphrase entry. BC-D3 remains IN_PROGRESS until
  the operator confirms those observations; the recovery boot need not be
  repeated. BC-D4 subsequent automatic boot remains NOT_RUN.
- **Exact next action:** receive the requested confirmation that the LUKS
  prompt appeared and the existing passphrase worked. Then perform one
  ordinary console reboot, `sudo systemctl reboot`, without editing GRUB,
  and verify a new boot ID, absent recovery override, no-passphrase console
  login and the same storage/security/service checks. Existing BC-D approval
  covers that final cycle. Full installation/runtime/restore/provider and
  production acceptance remain open.

### BC-D3 no-prompt result; corrected one-time recovery entry prepared

- **Operator result received — first recovery acceptance FAIL:** the user
  saw no LUKS prompt and asked the agent to set up the test automatically.
  The exact requested recovery argument was present, so an incorrectly
  entered argument is not supported by the remote evidence. Retain the
  [operator observation](evidence/2026-09-27-hermes-production/server-recovery-boot-r1-observation.json)
  separately from the passing remote storage/health checks. No passphrase
  recovery success is claimed for boot `4cea93af-9409-42b1-a5c2-ad4c8d8cfd60`.
- **Correction rationale:** the
  [systemd v259 unlock implementation](https://github.com/systemd/systemd/blob/v259/src/cryptsetup/cryptsetup.c)
  attempts external LUKS token plugins before its explicit passphrase path.
  The first test's argument override did not disable that route. The earlier
  eight generator tests checked generated arguments only and did not cover
  actual unlock behavior. This explains why those tests cannot prove a
  passphrase-only boot; it is source-based diagnosis rather than an
  instrumented trace of the token used during the failed attempt.
- **Prepared change under the user's explicit request:** copy the selected
  default BLS entry to a separately named recovery entry, preserve the same
  validated kernel/initramfs and original boot arguments, and add the exact
  recovery override plus
  `systemd.setenv=SYSTEMD_CRYPTSETUP_USE_TOKEN_MODULE=0` and a non-secret test
  marker. Remove `quiet` and `rhgb` from this copy so the console is visible.
  The [systemd environment argument](https://github.com/systemd/systemd/blob/v259/man/systemd.xml)
  propagates the token-plugin setting to child processes for that boot.
  The installed cryptsetup binary contains the corresponding environment
  control. It supplements the recovery override which removes explicit TPM
  options; neither half alone is treated as sufficient recovery proof.
- **One-time selection and preservation:** the helper uses `grub2-reboot`
  with the separate [Fedora BLS entry identity](https://fedoraproject.org/wiki/Changes/BootLoaderSpecByDefault).
  It requires a plain `/boot` partition and recognized GRUB one-time/default
  handling, preserves `saved_entry`, and checks original BLS/config/image,
  crypttab and LUKS metadata identities before and after arming. No initramfs
  build, TPM enrollment, keyslot change or normal-entry edit is performed.
  It clears its own next-entry selection and removes its unchanged copy on
  setup failure. Reruns on the same boot converge; the old boot-ID binding
  refuses replay after a reboot. The separate entry remains on disk after
  a successful test and must be removed during attended cleanup after the
  return-to-normal proof; it does not replace the normal saved default.
- **Preparation validation — PASS within scope:** 17 focused Toolbox tests
  cover preservation, explicit selectors, token-disable argument, conflicting
  state, unchanged reruns and partial-arm cleanup without removing unrelated
  state. Ruff check/format pass. The helper was uploaded over pinned SSH and
  its unprivileged preview passed; its SHA256 is
  `8d6ccdaef18f5f0a5b59d55646a8fb69e2575a34ba49cf9129802fd1e3098740`.
  Retain [source](evidence/2026-09-27-hermes-production/server-recovery-once-r2-script.txt),
  [tests](evidence/2026-09-27-hermes-production/server-recovery-once-r2-tests.txt),
  [launcher](evidence/2026-09-27-hermes-production/server-recovery-once-r2-launcher.txt)
  and [preparation result](evidence/2026-09-27-hermes-production/server-recovery-once-r2-preparation.json).
  Root preconditions, actual BLS creation/selection, reboot and corrected
  hardware recovery are NOT_RUN pending private sudo entry.
- **Exact next action:** with the operator at the physical console, run
  `bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-boot/run-recovery-test.sh`
  in the workstation's interactive terminal. The server requires the user's
  private sudo password; the helper then prepares the entry and reboots.
  Privately enter the known LUKS passphrase at the physical console and
  leave that boot running for independent verification. If recovery cannot
  complete, the unchanged normal Fedora entry remains available in GRUB.
  After successful recovery, prove one ordinary automatic boot and remove
  the temporary test entry. Overall production qualification remains open.

### Recovery continuation: live prerequisite check and final-cycle preparation

- **Previous goal turn — progress:** diagnosed the no-prompt result,
  implemented/tested/staged the corrected one-time recovery helper and
  preserved its failed predecessor's evidence. Current pinned SSH at server
  time `2026-09-28T20:41:18.152521+00:00` still shows boot ID
  `4cea93af-9409-42b1-a5c2-ad4c8d8cfd60`, kernel 7.2.7 and system running.
  The corrected helper has no running process and its public apply report
  is absent. The corrected recovery boot has not run; this is a private
  input dependency, not a verified wait on a live job.
- **Independent preparation — PASS within offline/preview scope:** prepared
  the later cleanup-and-normal-reboot helper. It requires a different boot
  ID with exactly the corrected recovery, token-disable and marker arguments,
  matching root-owned preparation/baseline records, an already cleared
  one-time selection and unchanged normal boot/configuration/LUKS identities.
  It preserves a copy and removes only the exact temporary BLS entry, then
  requests an ordinary reboot. Changed/unrelated entries are refused;
  unchanged cleanup reruns converge and another boot is refused. Private
  passphrase observation remains separate required evidence.
- **Evidence:** eight focused Toolbox tests pass for corrected-boot guards,
  removal ownership, retained-copy identity, failed-copy preservation and
  rerun behavior. Ruff check and format pass. The uploaded helper's
  unprivileged preview passes; root cleanup/reboot are NOT_RUN. Retain
  [source](evidence/2026-09-27-hermes-production/server-recovery-finish-r1-script.txt),
  [tests](evidence/2026-09-27-hermes-production/server-recovery-finish-r1-tests.txt),
  [launcher](evidence/2026-09-27-hermes-production/server-recovery-finish-r1-launcher.txt)
  and [preparation result](evidence/2026-09-27-hermes-production/server-recovery-finish-r1-preparation.json).
  Helper SHA256:
  `85ca63a84613c2b22c453506dff9fb0fb531fcf23ec7a74a105e4ef3c5db4f96`.
  This future helper does not modify the already issued recovery command
  and is not a substitute for the pending recovery test.
- **Exact next action unchanged:** the operator runs the already prepared
  `run-recovery-test.sh` in a private interactive terminal, supplies sudo
  there, and tests the LUKS passphrase at the physical console. After the
  actual recovery observation and remote verification, issue the prepared
  `run-finish-recovery.sh` to remove the temporary entry and perform BC-D4.
  No new scope approval is needed. G03 installation, G04 runtime/restore,
  G06 private exact-candidate live application tests and remaining G05/G08
  acceptance still need their existing prerequisites. No candidate package
  input, production application or retained recovery backup was changed.

### Corrected recovery private-input blocker: audit threshold reached

- **Previous turn — progress:** independently prepared and tested the final
  cleanup/normal-reboot helper. That work is now complete within preparation
  scope. This turn's pinned SSH at server time
  `2026-09-28T20:46:58.553765+00:00` again reads unchanged boot ID
  `4cea93af-9409-42b1-a5c2-ad4c8d8cfd60`, kernel 7.2.7 and system running.
  Neither recovery helper has a running process; both public apply reports
  are absent. No live process or session is being waited on.
- **Same blocker across three turns:** the user's correction/preparation
  turn, the first goal continuation and this continuation all require the
  same private sudo execution and physical LUKS-passphrase test. Independent
  recovery and cleanup preparation has been exhausted. Repository/package
  gates retain their scoped passes, while encrypted installation, runtime,
  restore and private live application gates cannot proceed with their
  existing missing prerequisites. Further status polling or synthetic tests
  cannot supply those live observations. Mark the goal BLOCKED, not complete.
- **Minimum intervention / exact resume point:** run the already issued
  `bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-boot/run-recovery-test.sh`
  in an interactive workstation terminal and provide sudo privately. At the
  physical server, observe the corrected boot and privately test the existing
  LUKS passphrase. Report whether the prompt appeared and the passphrase
  worked, or paste only a non-secret refusal/error. Leave a successful
  recovery boot running for verification; then use the prepared final-cycle
  helper after its prerequisites are confirmed. Existing same-scope approval
  remains valid, and no further permission request is needed to resume.

### Corrected recovery reboot requested; console and post-boot evidence pending

- **New operator evidence — progress:** the user supplied the corrected
  helper's root report at `2026-09-28T21:00:37.102993+00:00`, followed by
  the system reboot broadcast and SSH disconnect. `READY_TO_REBOOT` records
  the separate BLS recovery entry, preserved normal default, unchanged LUKS
  recovery/token enrollment and expected image/script identities. The
  private execution prerequisite is resolved. Retain the
  [operator apply report](evidence/2026-09-27-hermes-production/server-recovery-once-r2-operator-apply.json)
  with its provenance explicit; independent retrieval of the server's
  public report is still pending.
- **First availability check:** pinned SSH timed out before authentication,
  exit 255. This does not establish boot failure or a LUKS prompt. The
  server may be waiting for private console input; physical observation
  is required. No reboot/setup command is retried and no previous process
  is treated as still running solely from its preboot report.
- **Exact next action:** receive the already requested console observation,
  with the operator entering the existing LUKS passphrase privately if
  prompted. On SSH return, retrieve the root report and verify a new boot
  ID, the three exact recovery parameters, expected kernel, filesystem
  UUIDs, cryptsetup/service health, Secure Boot, SELinux and absence of
  swap. Only after both observation and remote checks pass issue the
  prepared cleanup/normal-reboot helper. BC-D3 recovery remains unproven;
  cleanup, BC-D4 automatic boot and broader qualification remain incomplete.

### BC-D3 corrected physical passphrase recovery PASS

- **Physical observation:** the operator answered `Yes — the prompt appeared
  and my passphrase worked`. No passphrase was shared with the agent.
- **Independent recovered-boot validation — PASS:** pinned SSH now reads
  boot ID `e1f41858-8315-4fd6-8949-50ee69e75daa`, different from the bound
  preboot ID, and kernel `7.2.7-200.fc44.x86_64`. All three corrected recovery
  parameters are present exactly. Four filesystem UUIDs match, the encrypted
  mapping's service is active/exited, the system is running with no failed
  units, Secure Boot is enabled, SELinux enforcing and swap absent. Server
  time is `2026-09-28T21:03:57.766113+00:00`.
- **Root report independently retrieved:** the server report exactly matches
  the operator-supplied preparation report, SHA256
  `e0b536aa641f377cceeac892121b7aab821b07cc0fac520074a2c28046e43c8d`.
  Its preboot `NOT_RUN` fields remain historical; the actual observation
  and post-boot checks establish BC-D3 PASS in the separate
  [corrected recovery evidence](evidence/2026-09-27-hermes-production/server-recovery-once-r2-postboot.json),
  SHA256 `14d1e32b5d3c94ead734b172f9cd4de246d0091146da84e2edc3fa0a6d271725`.
  The earlier no-prompt attempt remains FAIL and unchanged.
- **Final-cycle readiness:** the staged cleanup helper and both imported
  helpers still match their reviewed hashes, regular-file ownership, mode
  and link-count requirements. Root cleanup is not yet run. Its guarded
  operation verifies the normal saved default and original configuration,
  preserves a copy of the exact temporary BLS entry, removes only that
  entry and reboots normally. The current boot's plugin-disable setting
  is temporary and should be absent on the next normal boot.
- **Exact next action:** with the operator still at the console, run
  `bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-boot/run-finish-recovery.sh`
  in the workstation terminal and enter sudo privately. No GRUB editing is
  needed. Require a new boot ID, absent recovery/token-disable/marker
  parameters, unchanged expected kernel/storage/security/service health,
  the root cleanup report and separate observation that login appeared
  without entering a LUKS passphrase. BC-D4 and cleanup remain NOT_RUN
  until this occurs; the broader mandatory qualification gates remain open.

### BC-D4 first continuation: final private reboot step pending

- **Previous goal turn — progress:** the operator's successful passphrase
  observation and independent recovered-boot checks established BC-D3 PASS.
  The final cleanup/automatic-reboot command was issued under existing
  authority; no new scope approval is required.
- **Current state:** pinned SSH at server time
  `2026-09-28T21:06:59.360610+00:00` reads the same recovered boot ID
  `e1f41858-8315-4fd6-8949-50ee69e75daa`, kernel 7.2.7 and system running.
  All three temporary recovery parameters remain present. The final helper
  has no running process and its public cleanup report is absent. The final
  normal reboot has not occurred; this is not a verified wait on a live job.
- **Acceptance reconciliation:** repository/package gates retain their
  scoped passes. Physical passphrase recovery is proven, but BC-D4 requires
  a different normal boot without the temporary arguments and an operator
  observation of no-passphrase login. G03 installation, G04 runtime/restore
  and G06 private application acceptance still lack their live prerequisites;
  the current physical preparation does not replace them. Prepared helpers
  and synthetic tests cannot advance those missing live gates.
- **Exact next action unchanged:** run the already issued
  `run-finish-recovery.sh` with private sudo input at the workstation, while
  the operator remains at the server console. Then obtain the final boot
  observation and independent remote checks. No server mutation, package
  input change or new validation claim occurred during this continuation.

### BC-D4 final private-input blocker: audit threshold reached

- **Previous continuation — no progress toward live acceptance:** its
  availability check confirmed the same recovered boot and pending final
  private command; it did not complete another live gate. The current
  pinned SSH check at server time `2026-09-28T21:08:48.406465+00:00` again
  shows boot ID `e1f41858-8315-4fd6-8949-50ee69e75daa`, all three recovery
  arguments, kernel 7.2.7 and system running. The cleanup report is absent
  and no cleanup helper process is running. No verified live job is pending.
- **Blocked audit:** final private sudo execution and the physical
  no-passphrase observation remain dependencies across the recovery-result
  turn and two goal continuations. The prepared cleanup helper and its tests
  are complete; no additional authorized independent work can replace this
  private action or the other gates' missing installation/runtime/application
  prerequisites. Mark the goal BLOCKED, not complete, while retaining BC-D3
  recovery PASS and all earlier evidence.
- **Exact resume point:** run
  `bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-boot/run-finish-recovery.sh`
  on the workstation and enter sudo privately. After the server reboots,
  report whether it reaches login without a LUKS prompt, or provide the
  helper's non-secret refusal/error. Leave a successful normal boot running
  for independent report/boot/security/storage verification. Same-scope
  approval remains valid; the full qualification objective is unchanged.

### BC-D4 final automatic boot and physical commissioning PASS

- **Operator observation:** `no LUKS pathphrase requested the server is online`.
  This supplies the physical no-passphrase observation after the previously
  successful private recovery test; no secret was provided to the agent.
- **Independent normal-boot verification — PASS:** pinned SSH at server time
  `2026-09-28T21:18:30.222311+00:00` reads new boot ID
  `12c3478f-14c2-45d3-9bb8-f1badbc3b3f6`, different from the recovery boot
  `e1f41858-8315-4fd6-8949-50ee69e75daa`. Kernel remains
  `7.2.7-200.fc44.x86_64`; all temporary recovery parameters are absent.
  All four filesystem UUIDs match, cryptsetup is active/exited, system state
  is running with zero failed units, Secure Boot enabled, SELinux enforcing
  and swap absent.
- **Cleanup report independently retrieved — PASS:** root report SHA256
  `6db99de5e86e99812e68548bb5104d75b93fe6eaaad29d6e588c0695e7fe3eaa`
  records removal of only the temporary entry, retention of its exact copy,
  unchanged LUKS metadata and preserved normal default. Its preboot
  `subsequent_automatic_boot: NOT_RUN` remains historical; the independent
  postboot checks and operator observation now establish BC-D4 PASS. The
  [final automatic-boot evidence](evidence/2026-09-27-hermes-production/server-recovery-finish-r1-postboot.json)
  is bound to SHA256
  `234017f192931fcbf93d6737889f1b87d5a5615a98d1cad36cfa19f7b0b0764a`.
- **Approved BC-A through BC-D scope complete:** encrypted header copy,
  additive TPM enrollment, selected-kernel boot configuration, automatic
  warm boot, clean shutdown/AC-restoration cold start, private passphrase
  recovery and return to automatic boot now have their required scoped
  evidence. G08 passes for this physical target. No further boot helper
  execution is required. This does not establish abrupt running-power-loss
  recovery, re-enrollment, candidate application runtime or full release
  qualification. G03–G06 and T05 application deployment remain incomplete.

### Next qualification stage — prepared, awaiting authorization

- **Read-only environment refresh — PASS:** the
  [two-role preview report](evidence/2026-09-27-hermes-production/fixture-previews-after-physical-boot.json),
  SHA256 `e63cc371b3ff4fa9d14358904c3ab58f69fdd1324b3855b949c819fce5042447`,
  confirms both named domains/directories are absent, localhost ports 22224
  and 22225 available, 90087018496 bytes free and the retained Fedora44 ISO's
  checksum/signature valid. Installed Fedora43 guest metadata is selected
  for that verified Fedora44 media, as previously reviewed. The first
  preview attempt inside Toolbox failed because `virsh` was unavailable;
  the successful preview used the existing host tools. Both attempts are
  recorded. No VM, operational key or guest installation was created.
- **Concrete proposed scope:** reuse the two names, directories, ports,
  virtual disks, CPU/RAM limits, explicit disk identity, private key directory,
  capacity reserve and retention boundaries in
  [the existing resource proposal](#proposal-awaiting-live-operation-approval).
  Create and install both guests sequentially; privately commission their
  independent identities and boot/recovery configuration; stage the current
  test-signed candidate and bounded named-operation dispatcher; perform
  synthetic application runtime/isolation, unchanged rerun, rejection,
  controlled interruption and failed-upgrade/rollback checks inside those
  guests. Run one guest at a time, preserve at least 20 GiB host free space
  before large writes, and retain failures for diagnosis. Synthetic gateway
  networking remains disabled. Private console input is still required for
  the new guests' encryption and administrator secrets.
- **Stage boundaries:** no real provider credentials, provider spend or
  Telegram messages; no physical-server changes, existing-VM operations,
  host package installation, host network changes or backup-service changes.
  Independent encrypted backup/restore and real application tests remain
  gated on their own prepared resources and authorization. This narrower
  stage advances installation, runtime/repeatability and fixture boot checks;
  it does not waive the unperformed restore/application gates. The restore
  guest may be commissioned and retained ready for the later restore stage.
- **Cleanup and authority:** stop synthetic applications and cleanly shut
  down the two owned VMs after verification when safe; retain their disks,
  ownership/recovery material and sanitized evidence. Preserve a failed
  recovery guest for private diagnosis; never automatically restore headers
  or wipe keyslots. No commit/push/PR operation or production promotion.
  This stage is a proposal, not authorization. The goal and repository
  `AGENTS.md` require explicit VM lifecycle and private commissioning scope
  approval; the completed physical BC scope does not supply it.
- **Exact next action:** obtain approval of this bounded synthetic VM stage,
  then create only the named resources and hand off private console prompts
  without requesting secrets in chat. The complete preproduction goal remains
  active and incomplete; prior physical boot blockers are resolved.
- **Record validation — PASS:** Toolbox Markdown lint, full-tree secret scan
  (550 files), source-aware manifest verification (549 rows), exact diff
  whitespace check, 102 local link targets and both new immutable evidence
  hashes. Changes in this stage are record/evidence only; executable and
  packaged candidate inputs remain unchanged. An explicit approval request
  for the prepared VM stage is pending; no dependent lifecycle action runs
  before the answer.

### Synthetic VM stage approved — execution baseline

- **Approval evidence:** the operator answered `Approve the prepared synthetic
  VM stage` to the exact linked proposal above. Its named resources,
  operations, private commissioning, one-VM-at-a-time limits and cleanup
  boundaries are now authorized. Reuse that approval through this stage;
  physical-server changes, provider/Telegram activity and backup-service
  changes remain excluded. The original approved release acceptance criteria
  remain unchanged.
- **Execution order:** prepare dedicated private test signing, commissioning
  and forced-command deployment keys and the two installation settings;
  refresh the qualification preview with its actual public commissioning
  key, create that VM and expose its private installer console. The operator
  enters installation secrets only there. Verify installation and canary
  preservation before guest commissioning/runtime checks. Create the restore
  guest only while the first guest is shut down.
- **Expected first acceptance:** only the new explicitly identified system
  disk is installed, its unrelated attached disk canary remains unchanged,
  Fedora44 encrypted XFS/LVM layout and guest identity match the settings,
  and no installation secrets enter repository files or agent tool output.
  Private input is a dependency, not permission to store or invent passwords.
- **Exact next action:** inspect the rendered installer inputs and existing
  private-directory metadata, generate missing dedicated keys without
  replacing any existing files, then run the guarded qualification fixture
  creation with the reviewed media and settings. Preserve partial failures;
  do not repeat create against existing resources.
- **First creation — FAIL, resources retained:**
  [creation report](evidence/2026-09-27-hermes-production/synthetic-qualification-create-r1.json)
  records `command-failed:virt-install`. No guest domain was created; the
  rendered Kickstart, empty qcow2, unrelated-disk canary and PREVIEW ownership
  record remain in the approved qualification directory. The actual stderr
  includes `Failed to bind UNIX domain socket: Permission denied`; the preceding
  IPv6 route warning was not the fatal error. Host network and security policy
  remain unchanged.
- **Demonstrated fixture defect:** production primitives deliberately strip
  the subprocess environment, but the host fixture reused that wrapper without
  retaining HOME/XDG session paths. Two user virtqemud processes were observed:
  the ordinary process has HOME/XDG_RUNTIME_DIR, while the failed fixture's
  process has neither and selected the home-cache socket path. Libvirt's
  [documented runtime path selection](https://www.libvirt.org/manpages/libvirtd.html)
  confirms this distinction. Preserve only validated session path variables
  for fixture virtualization commands, retaining the production command policy.
  Add regression coverage for consistent inventory/creation session selection
  and rejection of missing or unsafe runtime directories. G01/G07 and affected
  source/provenance checks are STALE during this correction.
- **Recovery boundary:** after correction and focused tests, inspect both
  session inventories, retained ownership/canary and empty image metadata.
  Resume the same approved installation only if ownership and blankness are
  established; never rerun create or delete/recreate the retained files.
  This is correction of the approved new fixture startup, not authorization
  to operate another VM or change host permissions. Retain separate failed
  and successful attempt evidence.

### Synthetic fixture session correction verified; private installation retry pending

- **Preparation and corrected creation — PASS:**
  [private setup metadata](evidence/2026-09-27-hermes-production/synthetic-stage-private-preparation.json)
  records five dedicated test key fingerprints and both password-free
  installation settings. Both actual settings pass Fedora44 Kickstart
  validation. The [retained-resource inspection](evidence/2026-09-27-hermes-production/synthetic-qualification-failed-resource-inspection.json)
  proves blank qcow2 data, unchanged canary/Kickstart and absence of both
  names in both libvirt sessions. The [corrected startup](evidence/2026-09-27-hermes-production/synthetic-qualification-resume-r1.json)
  then starts the same retained disk/canary successfully under the ordinary
  session environment. No host permission or network change was made.
- **Actual VM identity:** `hermes-production-qualification`, UUID
  `27b76faa-7e0b-4162-9fad-e9f85684309a`, 8 GiB RAM/two vCPUs, exactly the
  approved two disk paths/serials, enabled enrolled Secure Boot keys, TPM2
  emulator and localhost-only 22224 forwarding. The
  [installer handoff](evidence/2026-09-27-hermes-production/synthetic-qualification-installer-handoff.json)
  records these facts. Restore remains uncreated; its
  [corrected read-only preview](evidence/2026-09-27-hermes-production/restore-preview-session-r1.json)
  passes with the actual public commissioning key.
- **Regression and repository verification — PASS:** both new tests first
  failed against the previous implementation, then all 44 focused cases
  passed. A single test-formatting finding was corrected; focused fixture
  tests and selected Ruff check/format pass. The first canonical run passed
  execution tests but failed provenance because new evidence was published
  after manifest generation; its log remains unchanged. The corrected run
  captured output under ignored staging with a stable manifest:
  [offline gate](evidence/2026-09-27-hermes-production/offline-fixture-session-r2.log)
  PASS (610 Python cases, 140 ShellSpec examples and remaining canonical
  checks), [check-only lint](evidence/2026-09-27-hermes-production/lint-fixture-session-r2.log)
  PASS. Publish completed logs before the final provenance refresh.
- **Candidate refreshed — PASS:**
  [package report](evidence/2026-09-27-hermes-production/bundle-fixture-session-r1.json)
  binds artifact `f9097588d061ef9a1ceab69cf75786bb17837ce45ae6bec596919a0fe097661b`,
  archive `9a7aa383626d986cebe09055f37f6f7ee1ad2af87feeea2ff580110302b64fc7`
  and unchanged receiver `243d6db51984625138f02c8740352a3510ce37c3518568c6849e2fdc70f180a4`.
  Only the packaged runbook differs from the preceding candidate; all
  executable/image inputs match. Signature/extraction and rejection of an
  unqualified candidate for production pass. The test-signed archive is
  retained under ignored `synthetic-stage/candidate-session-r1.tar` for
  later guest tests. No candidate deployment occurred.
- **Installer storage validation — FAIL, private retry pending:** the
  [operator-reported error](evidence/2026-09-27-hermes-production/synthetic-qualification-encryption-prompt-r1.json)
  says the requested vda3 encryption has no key. The agent's initial console
  refresh supplied a blank first value; subsequent private operator input
  is unknown and was not read. The destination menu shows only vda selected
  and the 64 MiB vdb canary unselected. Source extracted from the exact signed
  DVD's Anaconda 44.30 RPM shows the passphrase dialog runs at initialization;
  the destination menu instead enters partitioning choices. Do not change
  that layout or substitute an empty passphrase.
- **Exact next action:** await the operator's Ctrl+] detach, then restart only
  the guest installer and serial console services to obtain a fresh private
  passphrase dialog with the original Kickstart. Do not send a newline to
  inspect a pending private-input prompt. Detach before returning the console
  to the operator, require nonempty private entry/confirmation, and verify
  actual installation, canary preservation and secret hygiene afterward.
  Existing synthetic-stage authority covers this correction; physical-server
  boot commissioning remains PASS and unchanged. Full qualification is still
  incomplete.
- **Publication closure — PASS:** the
  [verification index](evidence/2026-09-27-hermes-production/verification-fixture-session-r1.json)
  binds three corrected source/document files and eleven retained evidence
  files. All 112 record link targets exist. Final publication Markdown lint,
  full-tree secret scan (562 files), source-aware provenance (561 rows),
  immutable final-server-boot hash and diff whitespace checks pass. The
  operator-detach request remains pending; no agent console connection is
  open and no installer restart has yet occurred.

### Installer console handoff — first continuation

- **Previous goal turn: progress.** Approved fixture creation exposed and
  corrected the session-environment defect; the new VM started, repository
  gates and candidate verification passed, and live storage validation
  identified the missing private encryption input. A console detach was
  requested before restarting the installer interface.
- **Current authoritative check:** at `2026-09-28T21:48:45.342287+00:00`, the
  only session VM remains `hermes-production-qualification`, UUID
  `27b76faa-7e0b-4162-9fad-e9f85684309a`, state running. The agent has no
  console connection, has not restarted the installer and has received no
  detach confirmation. A running VM is not evidence that installation has
  resumed or that a private-input prerequisite has passed.
- **Current continuation: no progress toward live acceptance.** The same
  private console handoff remains required. All independent correction,
  packaging and verification work is complete within its recorded scope;
  the one-VM-at-a-time limit prevents starting the restore guest concurrently,
  and the broader restore/application prerequisites remain unavailable.
  Keep the full goal active and incomplete at this first continuation.
- **Exact next action unchanged:** wait for the already requested `Detached`
  reply after Ctrl+], then restart only the guest installer/serial interface
  and hand back its fresh private passphrase prompt. Do not re-request scope
  approval or attach to the operator's console in the meantime.

### Installer console handoff — blocked audit threshold reached

- **Previous continuation: no progress.** It confirmed the same VM and
  missing console handoff; no live installation gate advanced. The current
  check at `2026-09-28T21:50:26.337779+00:00` again confirms the expected VM
  UUID in running state and additionally finds an operator `virsh console`
  client, PID 51861, still open for this exact guest. The agent has no console
  connection and the prepared installer restart remains NOT_RUN.
- **Evidence reconciliation:** all three source hashes and eleven evidence
  hashes in the fixture verification index still match. Repository/package
  passes remain valid within their scope. Actual encrypted installation,
  post-install canary/secret hygiene, guest commissioning, runtime, restore
  and real application acceptance remain incomplete. No autonomous process
  is verified to be completing the blocked private-input step.
- **Blocked audit:** the same private installer handoff/input dependency has
  now persisted across the original result turn and two continuations.
  Independent authorized corrections and checks are complete; the existing
  console client and missing private input prevent further live progress.
  Mark the full goal BLOCKED, not complete. Preserve both the running guest
  and its retained resources; do not disconnect the operator or start the
  second guest to bypass the one-VM-at-a-time limit.
- **Exact resume point:** the operator presses Ctrl+] and reports `Detached`.
  Then use existing approval to restart only Anaconda and its serial console
  interface, detach before private passphrase entry and resume installation
  acceptance. No new resource-scope approval is needed. No commit, push,
  production application deployment, provider call or Telegram operation
  occurred during this audit.

### Console detached — observed shutdown requires installer boot restoration

- **Operator progress:** `Detached` resolves the console handoff. Fresh host
  inspection confirms no matching console clients; the guest has independently
  entered `shut off (shutdown)`. Do not execute the earlier live-service
  restart proposal against a stopped guest or assume installation completed.
- **Current state at `2026-09-28T21:52:20.241503+00:00`:** the same approved
  UUID is defined with its normal hard-disk boot configuration. Its qcow2 is
  entirely unallocated zero data; the system was not installed. The retained
  Kickstart and unrelated-disk canary still match their recorded SHA256 values.
  See [detached-state evidence](evidence/2026-09-27-hermes-production/synthetic-qualification-detached-state-r1.json).
- **Authorized correction:** use the installed `virt-install --reinstall`
  operation on this exact stopped, empty qualification domain, supplying the
  same verified DVD, unchanged Kickstart and serial-console arguments. Local
  CLI help and implementation confirm that reinstall takes existing guest
  configuration, skips disk creation and restores its prior persistent XML.
  Verify UUID, disk paths, capacity, canary and empty-disk state immediately
  before execution. Preserve the prior inactive XML and attempt evidence.
  No VM definition, disk, TPM or unrelated resource is deleted or replaced.
- **Exact next action:** boot the installer with no automatic console input,
  inspect only its fresh non-secret prompt, detach, then let the operator
  privately enter and confirm a nonempty LUKS passphrase. Do not send Enter
  merely to refresh the display. Existing synthetic-stage approval applies;
  the previous blocked audit is resolved and a fresh audit begins if another
  dependency later prevents progress.

### Fresh prompt observed; DVD packages and final Kickstart retention corrected

- **Installer boot — started, exact-XML comparison FAIL retained:**
  [restart attempt](evidence/2026-09-27-hermes-production/synthetic-qualification-installer-reboot-r1.json)
  records successful `virt-install` exit and running state but a changed
  persistent XML. Subsequent exact inspection established that only the
  expected read-only DVD source was inserted in the existing CD-ROM device;
  all other XML is identical after removing that source element. Do not
  relabel the original strict comparison as a pass. Detach that DVD after
  installation when it is no longer required, preserving normal disk boot.
- **Fresh passphrase prompt — PASS observed:** Anaconda 44.30 displayed its
  initial `Passphrase:` prompt without any input from the agent. The console
  simultaneously reported that `restic` and `tpm2-tools` were absent from
  the Server DVD. No private input was requested or sent during this attempt.
  The agent switched to the installer shell and ran `systemctl poweroff`;
  power-down was observed. Later libvirt reports `shut off (unknown)`, so an
  initial overly specific shutdown-reason assertion was retained as a failed
  inspection before checking actual power state, blankness and canary.
  The [findings report](evidence/2026-09-27-hermes-production/synthetic-qualification-installer-findings-r1.json)
  records an entirely unallocated system disk and unchanged canary.
- **Mandatory-package correction:** reuse the repository's established
  signed Fedora release-repository method, without the old disposable
  fixture's secret/enrollment behavior. Keep DVD-available DNF, repository
  configuration and signing keys in `%packages`. A bounded, error-on-failure
  `%post --nochroot` supplies the target resolver's runtime path and installs
  `restic` and `tpm2-tools` through chroot, using only repository `fedora`,
  releasever 44 and `gpgcheck=1`. Verify both RPMs before the following TPM
  initramfs step. No ignore-missing option, host package installation or
  unrelated repository change is introduced. The
  [release metadata query](evidence/2026-09-27-hermes-production/fedora-release-prerequisites-r1.json)
  confirms `restic 0.18.1-3.fc44` and `tpm2-tools 5.7-5.fc44` availability;
  this is read-only availability evidence, not a guest installation pass.
- **Secret-copy retention correction:** Anaconda's authoritative
  [boot-option documentation](https://anaconda-installer.readthedocs.io/en/latest/user-guide/boot-options.html#inst-nosave)
  confirms that final input/output Kickstarts cannot be removed reliably by
  a `%post` script. The fixture now supplies `inst.nosave=all_ks`; the
  Kickstart `%pre` requires exactly one `all_ks` or `all` value and refuses
  absent, partial or conflicting values before private input. Remove the
  ineffective post-script deletion. Private log inspection and checking that
  final Kickstart copies are absent remain actual installation gates.
- **Focused checks — PASS:** 46 production tests, selected Ruff check/format,
  and both corrected rendered Kickstarts under Fedora44 `ksvalidator`.
  The new package test executes the actual post script with fake privileged
  commands and confirms a failed install exits immediately; the retention
  test executes the actual guard against valid, missing, partial and duplicate
  boot options. Initial test-formatting feedback was corrected. Earlier
  immutable checks remain scoped to their earlier inputs; G01/G02/G07 and
  T04 are stale/in progress until canonical/package refresh.
- **Exact next action:** retain the old rendered inputs, publish only the
  corrected qualification Kickstart to its owned fixture directory, then
  boot the same verified empty VM with `inst.nosave=all_ks`. Confirm the
  initial private prompt without sending any input, detach and return it to
  the operator. Run canonical checks with logs under ignored staging, then
  publish completed evidence and the updated candidate. No second VM or
  physical-server change is included.

### Corrected installer prompt and candidate refresh — 2026-09-28

- **Same-resource installer restart — PASS within boot scope:** the
  [corrected boot report](evidence/2026-09-27-hermes-production/synthetic-qualification-inputs-reboot-r1.json)
  records UUID `27b76faa-7e0b-4162-9fad-e9f85684309a`, unchanged persistent
  XML and canary, no disk recreation, and successful installer startup.
  Current rendered Kickstart SHA256 is
  `b9387f78909f5286d0c3e06fe1d548ca4eeb31eb7934df7ef9abeb6c45837908`.
  The agent observed Anaconda `44.30-2.fc44` at a fresh initial `Passphrase:`
  without the prior missing-package warning. The agent sent no guest input
  and detached using Ctrl+] before requesting private operator entry.
  The [handoff report](evidence/2026-09-27-hermes-production/synthetic-qualification-inputs-handoff-r1.json)
  distinguishes prompt readiness from actual installation acceptance.
- **Canonical repository gates — PASS:**
  [offline checks](evidence/2026-09-27-hermes-production/offline-installer-inputs-r1.log)
  passed 612 Python cases, 140 ShellSpec examples and the remaining canonical
  checks; [check-only lint](evidence/2026-09-27-hermes-production/lint-installer-inputs-r1.log)
  passed. Logs were collected under ignored staging, then published only
  after completion. The
  [verification index](evidence/2026-09-27-hermes-production/verification-installer-inputs-r1.json)
  binds the corrected fixture, Kickstart template, tests, runbook and retained
  evidence. No live installation/runtime result is inferred from these checks.
- **Updated test candidate — PASS within packaging scope:**
  [signature/extraction report](evidence/2026-09-27-hermes-production/bundle-installer-inputs-r1.json)
  identifies artifact
  `d9e514e98060423b8f09db3739d672c416161b241d614f8bf719bec6f7f8f44d`,
  archive SHA256
  `4fa4cea949e83430d53838ee0163ac35242ecf2309041f66e4c06d3188105897`,
  and retained archive
  `.toolbox/hermes-production-validation/synthetic-stage/candidate-installer-inputs-r1.tar`.
  Only `source/PRODUCTION_RUNBOOK.md` differs from the previous candidate;
  receiver identity remains
  `243d6db51984625138f02c8740352a3510ce37c3518568c6849e2fdc70f180a4`.
  The dedicated test signer was used without exposing its key. Production
  policy rejected this unqualified candidate as expected. Earlier artifacts
  and failed attempt reports remain unchanged.
- **Exact next action:** operator reconnects using
  `virsh -c qemu:///session console hermes-production-qualification --safe`,
  types a new nonempty VM LUKS passphrase at the already waiting first prompt,
  confirms it privately, and reports installer completion or a non-secret
  error. A blank Enter must not be used to refresh that prompt. Do not attach
  or capture the console during private entry. Private administrator setup,
  completed installation, actual mandatory package verification, absent
  Kickstart copies, private log inspection and final canary preservation
  still precede guest commissioning and runtime acceptance. No restore VM
  has been created; physical application deployment and provider/Telegram
  operations remain NOT_RUN. The overall goal is incomplete.
- **Publication closure — PASS within repository scope:** Markdown lint,
  126 local link targets, all four source bindings and nine evidence bindings,
  full working-tree secret scan, source-aware migration manifest and exact
  diff checks passed. G01/G02/G07 and T04 are current; G03 installation and
  G04–G06 qualification remain incomplete. The private console handoff above
  is the next required operator action, with no additional scope approval.

### Console correction — approved implementation baseline, 2026-09-28

- **Request:** operator reports successful installation but about six passphrase
  requests and incorrect visualization, and explicitly asks to fix the menu.
  The supplied attachment contains clean installer shutdown, not the retry
  messages; the exact rejection reason is therefore unknown.
- **Observed:** the same qualification UUID is shut off; its system disk now
  contains a checksum-valid GPT with 1024 MiB EFI, 2048 MiB boot and the
  remaining 177950 MiB system partition. The unrelated canary hash is unchanged.
  This does not establish encrypted unlock, installed package or secret hygiene
  acceptance. Preserve the installed disk and do not rerun its installer.
- **Bounded correction:** use an explicit text/serial terminal profile with
  `TERM=xterm-256color`, quiet boot status, and retained Anaconda tmux. Add a
  private-terminal-only console entrypoint that directly executes `virsh`
  without reading, capturing or injecting input; keep safe attachment and
  fixed approved roles. Explain the new-passphrase/confirmation pair, validation
  retries, invisible input, and tmux redraw without submitting a blank value.
  Upstream passphrase strength checks remain unchanged.
- **Acceptance:** offline tests verify the interactive TTY boundary, role and
  ownership checks, unchanged attach behavior and deterministic boot settings;
  canonical gates, runbook and candidate package refresh follow. Actual visual
  and repeated-entry acceptance remains pending the next private installer
  session; no successful runtime reproduction is claimed from a shutdown log.
- **Exact next action:** implement and test the console correction, publish
  immutable evidence, then resume private installed-system commissioning.

### Console correction — implemented and checked

- **Implementation:** new fixture boots use explicit `inst.text`, one serial
  console, `TERM=xterm-256color`, `quiet` and `systemd.show_status=no`; tmux
  remains available for redraw. The verified media's `anaconda-tmux@.service`
  contains `PassEnvironment=TERM`, consistent with the upstream documentation.
  A `--console` mode requires all standard streams to be TTYs, validates the
  fixed role and ownership record, then replaces the process with
  `virsh console --safe` using the existing user session. It reads/captures no
  private input, sends no initial key, and performs no VM lifecycle operation.
  The [runbook](../HERMES_PRODUCTION_DEPLOYMENT.md#qualification-fixture-and-acceptance)
  documents numbered choices, invisible input, confirmation/retry semantics
  and the installer-only Ctrl+b then r redraw shortcut.
- **Evidence:** [48 focused checks](evidence/2026-09-27-hermes-production/focused-console-r2.log),
  [canonical offline and lint](evidence/2026-09-27-hermes-production/offline-console-r1.log)
  (614 Python cases, 140 ShellSpec examples) PASS. Initial formatting feedback
  remains in its separate first-attempt log. An actual invocation with
  redirected streams refused before accessing the guest. The
  [verification index](evidence/2026-09-27-hermes-production/verification-console-r1.json)
  binds current source and immutable evidence. The stopped-disk
  [GPT/canary inspection](evidence/2026-09-27-hermes-production/menu-report-disk-inspection-r1.json)
  and [eight-byte LUKS2 magic check](evidence/2026-09-27-hermes-production/menu-report-luks-magic-r1.json)
  support only their stated metadata scope.
- **Candidate refresh:** [package verification](evidence/2026-09-27-hermes-production/bundle-console-r1.json)
  PASS for artifact
  `4bbe1e57f13880f94f64a758f29f737a50ba2503609d6a2c2f9fa664d2ee8ad8`,
  archive SHA256
  `bac2dfcfc7d6de4db46a7be33e3370f20eae9f5ea802f30c91197476f90a2ab0`,
  retained as ignored `synthetic-stage/candidate-console-r1.tar`. Only the
  packaged runbook changed; executable receiver identity is unchanged.
  Production policy still rejects the unqualified candidate.
- **Limitations and exact next action:** the installed VM remains shut off
  and has not been reinstalled. No private prompt or visual acceptance was
  rerun. Source inspection shows that Anaconda asks for a value and its
  confirmation, and repeats on validation failure; the specific cause of the
  operator's six requests remains unknown without the rejection message.
  Existing password checks were not changed. Receive the requested non-secret
  confirmation whether the VM administrator password was set, then continue
  the appropriate private installed-system commissioning path. Observe the
  corrected installer display during the next approved fresh fixture run;
  preserve G03–G06 as incomplete until their actual criteria pass.

- **Publication closure — PASS:** 133 local link targets, the changed runbook
  section anchor, three source hashes and six evidence hashes checked; final
  Markdown, full-tree secret scan, source-aware manifest and diff checks pass.
  G01/G02/G07 and T04 are current within repository scope. Private installed
  system commissioning and live UI acceptance remain incomplete.

### Installed qualification VM commissioning — resumed 2026-09-28

- **Authority:** operator says `continue`; reuse the approved synthetic stage's
  existing VM lifecycle, private commissioning and test boundaries. The VM
  administrator password state is still unknown; do not infer a password or
  reset an existing account on that basis.
- **Prepared next action:** verify the stopped qualification VM's exact UUID,
  owned disk paths, resources, Secure Boot/TPM and canary; retain its inactive
  XML. Eject only the verified read-only installer DVD, confirm the remaining
  XML is unchanged, then start its existing hard-disk boot. Do not run the
  installer, replace its disk, change keyslots or alter the physical server.
- **Acceptance for this step:** normal boot reaches the existing LUKS prompt;
  detach without submitting input, hand private unlock to the operator, and
  inspect available guest access afterward. Installed-system package/layout,
  administrator access, secret hygiene and boot qualification remain pending.
  If access is unavailable, prepare a verified-media recovery path within the
  same approved VM; preserve the existing installed system.

### First installed-system boot — private unlock handoff

- **Applied within approved scope:**
  [boot report](evidence/2026-09-27-hermes-production/installed-boot-r1.json)
  records the exact qualification UUID, stopped-state canary verification,
  removal of only the read-only DVD source, unchanged remaining XML and
  normal hard-disk startup. No disk recreation or installation was run.
- **Observed:** the installed kernel `6.19.10-300.fc44.x86_64` reports Secure
  Boot enabled and root `/dev/mapper/hermes_system-root`. Its LUKS UUID is
  `bf1c622c-17c0-4d2b-9b51-82c345ad1de7`. The agent observed the existing
  disk's passphrase prompt without sending any guest input, then detached.
  [Handoff evidence](evidence/2026-09-27-hermes-production/installed-boot-handoff-r1.json)
  separates prompt observation from a successful private unlock.
- **Independent preparation:** a read-only guest audit is ready under ignored
  `synthetic-stage/installed-guest-audit-r1.py`, SHA256
  `ed58d3d4b58af13434bc405945121135a35360d823006df8a5c839d816620f4a`.
  Syntax parsing passes; guest execution is NOT_RUN. It binds the exact VM
  UUID and LUKS UUID, reports password status without a hash, checks required
  RPMs/mounts/SELinux/Secure Boot/swap/default kernel and public SSH identity,
  and reports only keyslot IDs/token types and Kickstart-copy existence. It
  does not inspect private keys, passphrases or installer-log contents. A
  bounded guest-agent ping reports not connected while private unlock is
  pending; do not weaken guest policy to make the agent available.
- **Exact next action:** operator runs
  `python3 -B /var/home/aicloudopspecial/code/repos/hermes-fedora-host/vm/hermes-production-fixture.py --role qualification --console`,
  enters the VM's existing LUKS passphrase once, and after the login prompt
  detaches with Ctrl+] and reports `unlocked`. No blank Enter for refresh;
  the Anaconda-only redraw shortcut does not apply to normal boot. Then use
  available authorized guest access to collect the read-only facts. If such
  access is absent, prepare the private verified-media recovery path without
  reinstalling or changing an existing administrator password by assumption.
  G03–G06 and the overall goal remain incomplete.

### Private unlock readiness — verified wait, 2026-09-28

- **Previous turn classification:** progress: the approved installed VM was
  started from its hard disk, the LUKS prompt was observed, the private console
  was handed off, and the bounded read-only audit was prepared.
- **Current authoritative state:** [readiness poll](evidence/2026-09-27-hermes-production/installed-boot-readiness-r1.json)
  at 22:42:58 UTC confirms the same domain UUID is running. Its guest agent is
  not connected and localhost SSH provides no banner. No console was attached
  and no authentication was attempted; private unlock is not verified.
- **Blocker audit:** this is the second consecutive resumed goal turn with
  private unlock/guest access pending. Keep the goal active at this point;
  no completed installation/runtime proof or changed scope is inferred.
  The second VM cannot run concurrently under the approved one-VM limit;
  repository checks and audit preparation are already complete. The exact
  next action remains the preceding private LUKS unlock handoff, followed by
  the read-only installed-system checks when access becomes available.

### Private unlock blocker — third consecutive resumed turn

- **Previous turn classification:** verified wait: the named libvirt domain
  was confirmed running by live XML/state and readiness probes, without
  opening the private console or attempting authentication.
- **Current authoritative evidence:** [readiness audit](evidence/2026-09-27-hermes-production/installed-boot-readiness-r2.json)
  at 22:44:40 UTC again confirms UUID
  `27b76faa-7e0b-4162-9fad-e9f85684309a` running, guest agent disconnected and
  no SSH banner on its verified localhost forwarding. This does not prove
  the operator has or has not typed a passphrase; successful unlock/access
  remains unverified. No new operator confirmation has been received.
- **Blocked audit satisfied:** the same private unlock/guest-access dependency
  has persisted through the user-triggered installed-boot turn and two
  automatic continuations. The installed VM, prepared audit and all evidence
  are retained. No further required qualification can advance without private
  input or changed guest availability; the one-VM-at-a-time boundary prevents
  concurrent restore-guest commissioning. Mark the goal BLOCKED, not complete.
- **Minimum intervention and exact next action:** use the previously prepared
  private console command to enter the VM's LUKS passphrase, detach with
  Ctrl+] at the login prompt, and report `unlocked` (or a non-secret error).
  Then recheck access and execute the prepared read-only audit. Do not
  restart/reinstall the waiting guest, collect its passphrase, or replace
  live installation/runtime/restore/application gates with offline results.

### Private administrator setup — recovery preparation, 2026-09-29 UTC

- **Progress and operator input:** operator reports `unlocked`; current probes
  confirm the same running VM and an SSH banner on its localhost-only port.
  The guest agent remains disconnected. Operator explicitly confirms only
  the LUKS passphrase was set, with no `operator` password. The earlier unlock
  blocker is resolved; do not repeat its blocked-turn count.
- **SSH trust:** a public candidate Ed25519 key was collected without
  authentication. Its fingerprint is
  `SHA256:lcfXGGLMwN88u+qwkBdjmJKagPoyMkpn7cJSOxWLUKQ`. It remains
  untrusted until checked through the VM recovery console; no accept-new
  authentication or host-key checking bypass is allowed.
- **Same approved scope:** cleanly shut down only the existing qualification
  VM using ACPI and wait for authoritative shutoff. Boot the verified Fedora
  DVD kernel with `inst.rescue`, the corrected text/serial terminal profile
  and no production Kickstart or install inputs. `virt-install --reinstall`
  is used solely as its existing-domain temporary-media boot mechanism;
  rescue mode is explicit and no disk creation/formatting command is supplied.
  Preserve UUID, disks, TPM/NVRAM, normal boot configuration and canary.
- **Expected private handoff:** verified Anaconda 44.30 rescue source offers
  Continue to mount the installed OS read-write, prompts for its LUKS
  passphrase, then opens a shell. Operator privately sets the missing account
  password and checks the installed SSH public-key fingerprint there. The
  passphrase and password never enter the agent's commands or evidence.
  Record actual menu/prompt observations and any failure without inferring
  successful account setup from a boot or readiness report.

### Rescue discovery and console shortcut correction, 2026-09-29 UTC

- **Observed rescue attempt:** the verified DVD reached explicit rescue mode.
  The strict persistent-configuration comparison failed because virt-install
  changed libosinfo metadata from Fedora43 to unknown. Preserve the failure;
  restoring only that metadata made the comparison pass, allowing only the
  intended readonly DVD source. UUID, system/canary disks, TPM and normal boot
  remain preserved. The recovery menu redrew correctly with Ctrl+b then r;
  Continue reached the private encrypted-device prompt, where the agent detached.
- **Operator report:** recovery subsequently displayed `No Linux systems found`
  and opened a root shell. Neither mounted-root discovery nor administrator
  password setup has passed. Diagnose device unlock, LVM activation and mounted
  OS identity before changing the installed system; do not infer lost data.
- **User-requested correction:** change the awkward console detach shortcut
  to Ctrl+Q using virsh's documented `--escape '^q'`, preserve safe private
  attachment, and distinguish new-installation guidance from boot/recovery.
  Existing sessions keep their old shortcut until reconnected.
- **Acceptance and gates:** focused console regression, canonical offline and
  check-only lint/secret/provenance checks, refreshed test candidate, and live
  attachment/detachment without guest lifecycle changes. G01/G02/G07 and T04
  are STALE/in progress for this source/runbook change until reverified. Guest
  recovery remains G03 IN_PROGRESS; no application or production acceptance.
- **Exact next action:** verify the console correction while awaiting the
  operator's detach, then inspect the recovery shell's block devices and mounts.

- **Live diagnosis:** the known LUKS2 partition was present but no encrypted
  mapping, logical volume or `/mnt/sysroot` mount existed. A direct one-attempt
  cryptsetup prompt was prepared and Ctrl+Q detached with exit zero. The
  operator's screenshot later showed `No key available with this passphrase`
  and a shell; that attempt failed. Reconnecting did not replay the waiting
  prompt. Correct the handoff: operator clears the known shell and starts the
  unlock command while attached, so it prints a visible prompt. No blank Enter
  for redraw, no interpretation of the privately entered value and no key change.
- **Private retry:** operator reports a freshly visible direct prompt returning
  to the shell without an error. They used mapping name `hermes_rescue_root.`
  (a trailing period), which is a temporary device name only. Verify the actual
  mapping and installed root after detach; do not treat this report alone as a
  successful mounted-system audit.
- **Repository correction checks:** 48 focused production tests, 614 canonical
  Python cases, 140 ShellSpec examples, the remaining canonical shell/manual
  checks and check-only lint PASS. The combined command then failed only on an
  extra invocation of a nonexistent `ruff` pre-commit hook; retain its log.
  Running the installed Ruff check and format-check directly passed. Final
  runbook text explains serial output replay and the visible-prompt handoff.
  Candidate `ce65bbcfac61f573cefdf8d8d335d858984d0f8f863cd9e7322d2c68dab4d322`
  has archive SHA256
  `ae66cbfb5c0c803d85fcfc789375a1a276018d4cab75774c82b874b76a5e4d2b`;
  package/signature/extraction and unqualified-production rejection PASS.
  The intermediate shortcut candidate remains retained separately.

- **Mounted recovery — PASS within scope:**
  [console-bound observation](evidence/2026-09-27-hermes-production/admin-rescue-mounted-r1.json)
  confirms the exact VM, LUKS2 device and three logical volumes. Activated only
  `hermes_system` through the known decrypted mapping. Mounted root readonly
  with XFS `norecovery` first; Fedora44 identity and root UUID match the expected
  installation. The installed public SSH fingerprint matches the prior candidate
  and is now pinned in an owner-only local known-hosts file. Remounted root
  read-write and mounted its `/var` plus private-propagation `/dev`, `/proc`,
  `/sys` bindings for administrator setup. `passwd -S operator` reports locked.
  The initial chroot public-key check lacked `/dev/null`; the public key was
  instead checked directly from the mounted path, and needed bind mounts were
  then added. No password hash, secret input or private key was inspected.
- **Display follow-up:** `clear` is absent from this rescue image. The shell
  builtin `printf '\033[2J\033[H'` visibly cleared the stale display. The
  maintained runbook now records this tested fallback and requires the operator
  to start secret prompts only after connecting. Final
  [package refresh](evidence/2026-09-27-hermes-production/bundle-console-shortcut-r3.json)
  is candidate `f23b0fa47c86c9e303743e5dc76ba78b11c2376cf225fcf663571c10c588ace8`,
  archive SHA256
  `984a1890b1fee301ebc01bc8d22cd1cdbb711215ad3e32ec24bd4e15acad7efc`.
  Earlier shortcut package reports remain historical after these documentation
  refinements; the executable receiver hash is unchanged.
- **Private handoff:** agent detached at the known mounted recovery shell.
  Operator reconnects and explicitly runs `chroot /mnt/sysroot passwd operator`
  so both new-password prompts are visible. Await successful private setup and
  detach; preserve the running recovery VM. The next bounded operation is
  installation of a fixed root-owned read-only audit command with an exact
  sudoers argument rule, followed by trusted normal-boot commissioning.

- **Publication closure — PASS:**
  [final verification index](evidence/2026-09-27-hermes-production/verification-console-shortcut-r2.json)
  binds final sources to preserved test, package and recovery evidence. Code
  hashes remain those tested by the canonical gate; subsequent edits changed
  documentation only. Final Markdown, 140 local link targets, full-tree secret
  scan, source/evidence hashes, provenance and diff checks pass. G01/G02/G07
  and T04 are current within repository scope; G03–G06 remain incomplete.
  Exact next action: receive private administrator-setup completion and detach,
  verify account status without reading its hash, install the bounded audit
  command, then resume trusted normal-boot qualification. No console attachment
  or capture is active during the operator's password entry.

### Bounded audit helper verification while private setup is pending

- **Continuation classification:** the prior turn made concrete progress:
  corrected/live-tested Ctrl+Q, recovered the encrypted root and pinned its SSH
  identity. This continuation verified the same qualification VM is running;
  no console process was attached at the inventory instant. This observation
  does not establish administrator-password completion. Do not attach or
  capture the console while that private step remains pending.
- **Independent correction:** synthetic tests of the prepared, not-yet-installed
  audit helper found that `assert`-based guards could disappear with Python
  optimization. Version r2 uses explicit refusal exceptions and a fixed child
  command environment. Preserve r1 and its failed test log; the separate symlink
  test failure was an overly narrow expected error, corrected to accept either
  safe refusal before writes. No guest was changed by these checks.
- **Verification — PASS within synthetic scope:**
  [six tests and syntax evidence](evidence/2026-09-27-hermes-production/audit-installer-preparation-r2.json)
  cover wrong VM including optimized Python, wrong mount, corrupt payload,
  symlinked privilege directory, conflicting existing file, failed sudo rule
  validation, and content/mode/inode stability on rerun. Root ownership and
  privileged subprocesses were mocked; the real Toolbox `visudo -cf` parsed
  the exact rule in a temporary file. Neither host nor guest sudo configuration
  was changed. No production or runtime acceptance is implied.
- **Prepared inputs:** use only ignored `synthetic-stage/install-audit-console-r2.txt`
  (SHA256 `48230c1ffb0ceb64ad06d955715f5f08934f3673968954f66b8c7e90f7c9b07a`),
  containing installer r2
  `c6f260c14a8539d4a298b4345586bc415e03f8fa56748a05c4a78ef40b68293a`
  and the unchanged fixed read-only audit payload. The older r1 transport is
  superseded and must not be executed. Packaged sources/candidate are unchanged.
- **Exact next action / blocker:** await the operator's `password set and
  detached`, then verify `passwd -S operator` without reading any password
  hash. Install the prepared bounded audit command from the known rescue shell,
  verify its exact files/modes and unchanged rerun, and resume normal-boot
  commissioning. The goal remains incomplete; no required live gate has been
  waived or replaced by these helper tests.

- **Handoff correction:** the operator ran `chroot /mnt/sysroot passwd operator`
  at the workstation's `aicloudopspecial@ai` prompt and received missing
  `/mnt/sysroot`. That command did not enter or change the VM. The immediately
  preceding inventory confirms the exact qualification UUID remains running.
  Corrected instructions include the full local fixture `--role qualification
  --console` command, Anaconda Ctrl+b then r redraw, and running chroot only
  at the guest's `bash-5.3#` prompt. The private password step remains pending;
  the goal is incomplete. Do not mistake this workstation error for loss of
  the previously verified guest mount, or capture private console input.

### Private administrator setup — blocked audit and resume point

- **Current evidence:**
  [read-only inventory](evidence/2026-09-27-hermes-production/private-admin-blocked-r1.json)
  confirms the same VM UUID remains running; no virsh console process was
  present at the check. No console was attached or captured, and no guest
  restart, shutdown or configuration mutation was performed. Lack of a console
  process does not prove the password was set.
- **Blocked audit:** the same private administrator-setup condition has remained
  unresolved across at least three consecutive goal turns. Independent work
  completed the shortcut correction, mounted recovery, SSH identity verification
  and bounded audit-helper correction/testing. The preceding turn corrected a
  workstation-versus-guest command error but completed no new guest operation.
  No remaining dependent commissioning action can proceed through the pending
  private handoff without risking interruption. Mark the goal BLOCKED rather
  than continuing status-only loops. This is not completion.
- **Minimum intervention:** on the workstation, run the following connection
  command. After Connected, use Ctrl+b then r to redraw and verify the guest's
  `bash-5.3#` prompt before running the second command inside that guest.

  ```bash
  python3 -B /var/home/aicloudopspecial/code/repos/hermes-fedora-host/vm/hermes-production-fixture.py --role qualification --console
  ```

  ```bash
  chroot /mnt/sysroot passwd operator
  ```

  Enter and confirm the administrator password privately. After the success
  message, press Ctrl+Q and report `password set and detached`. Never send the
  password. Leave the recovery VM running and retain its unlocked/mounted state.
- **Resume:** verify account status only; execute the hash-bound r2 audit
  transport, verify file ownership/modes and an unchanged rerun, then continue
  trusted normal-boot commissioning and the original G03–G06 acceptance work.
  Candidate `f23b0fa47c86c9e303743e5dc76ba78b11c2376cf225fcf663571c10c588ace8`
  remains unqualified. Repository checks and physical boot commissioning do not
  prove the required VM runtime, restore, boot or application gates. No production
  application deployment or Git delivery occurred.

### Administrator access verified; resuming installed-system qualification

- **Blocker resolved:** operator reports `passwd: password updated successfully`.
  Current inventory confirms the exact VM is running and its console is free.
  After safe attachment, `passwd -S operator` reports `P`; no password value or
  hash was read. Prior blocked-audit counts do not carry into this resumed work.
- **Bounded access — PASS:**
  [installed access evidence](evidence/2026-09-27-hermes-production/admin-access-installed-r2.json)
  records installation of the verified r2 helper and exact fixed-command sudo
  rule. Root ownership, 0644/0440 modes and hashes match; real chroot visudo
  succeeds. A second run preserves content, modes, ownership, inode and mtime.
  Actual noninteractive sudo attempts as operator reject both another command
  and an extra audit argument with password-required errors. This is recovery
  setup evidence, not installed-runtime qualification. The temporary grant is
  retained until commissioning can replace/remove it with exact-file checks.
- **Return-to-boot guard:** persistent configuration matches its pre-rescue
  baseline except the intentionally added readonly DVD source. Normal boot
  remains hard disk. Preserve UUID, disks, NVRAM/TPM and unrelated canary. Sync
  and unmount only the known rescue root tree; cleanly power off, confirm
  shutoff, remove only the rescue DVD source, verify baseline equality/canary,
  then start the existing disk installation. No reinstall or disk recreation.
- **Exact next action:** carry out that guarded return to normal boot. Detach
  before the operator privately enters the existing VM LUKS passphrase; use
  the already pinned SSH identity and commissioning key for the fixed read-only
  installed-system audit once SSH becomes available.

- **Normal boot handoff:**
  [preparation](evidence/2026-09-27-hermes-production/admin-normal-boot-prepared-r1.json)
  and [private handoff](evidence/2026-09-27-hermes-production/admin-normal-boot-handoff-r1.json)
  confirm clean rescue unmount/poweroff, original persistent XML restored exactly
  after ejecting only the DVD source, and unchanged unrelated-disk SHA256.
  Started this same installed VM paused. The operator uses
  `virsh -c qemu:///session --escape '^q' console hermes-production-qualification --safe --resume`
  so attachment precedes resume and the fresh disk-unlock prompt is visible.
  This is an explicit one-time resume handoff; the ordinary fixture console
  helper retains its no-lifecycle behavior. No agent console capture is active.
  Await the existing VM LUKS unlock and `booted and detached`, then run the
  prepared pinned-key, noninteractive read-only audit. Administrator setup is
  resolved; this is the separate normal-boot unlock, not an account-password retry.

- **Normal boot completed; SSH authentication failure retained:** operator reports
  `booted and detached`; live readiness confirms the resumed VM and SSH banner.
  [Authentication evidence](evidence/2026-09-27-hermes-production/admin-ssh-rejection-r1.json)
  records host-key verification PASS and rejection of the expected commissioning
  key. The generated Kickstart key matches its dedicated public key; one bounded
  verbose attempt confirms that exact fingerprint was offered and not accepted.
  Stop repeating authentication attempts. Password prompts remain disabled;
  neither private key content nor user password was inspected. The fixed root
  audit has not yet run in the installed system.
- **Exact next action:** operator privately logs into the normal VM console as
  `operator`, then detaches while leaving its user shell logged in. Inspect the
  actual home/authorized-key ownership, modes, public fingerprint and SELinux
  labels through that shell; correct the demonstrated cause within the approved
  commissioning scope, then retry pinned-key access. Do not restart/reinstall,
  weaken SSH trust or change unrelated host configuration to resolve this failure.

### Reserved administrator-name collision — corrective baseline

- **New evidence:** verified Fedora44 DVD package
  `setup-2.15.0-28.fc44.noarch.rpm` contains
  `operator:x:11:0:operator:/root:/usr/sbin/nologin`. Anaconda 44.30's
  `create_user` raises on an existing username; its installation task catches
  that exception as a warning. The fixture used `admin: operator`, which the
  renderer incorrectly accepted. The console did not retain a usable operator
  shell despite the operator report; a harmless attempted shell command instead
  reached a getty password prompt. That attempted login was canceled/detached;
  no password input was sent or captured. Confirm the actual installed passwd
  entry in recovery before changing it.
- **Evidence correction:** the earlier `P` status proves a password was set for
  the named account, not that it is a suitable administrator. The fixed audit
  grant's syntax, idempotence and argument boundaries remain observed; broader
  administrator-access acceptance is invalidated by this identity gap. Preserve
  all reports, including failed authentication. Do not redefine the reserved
  system account into an interactive administrator.
- **Approved corrective scope:** repair the existing qualification guest without
  reinstalling or recreating its disks; use `hermesadmin` for the intended human
  administrator after verifying that name is unused. Restore the system operator
  account's password lock and remove only the misdirected commissioning key/grant
  introduced by this fixture, preserving unrelated keys/configuration. A private
  password may be transferred internally to the corrected account without ever
  emitting it, passing a hash in arguments or persisting a separate credential
  copy; otherwise use a private prompt. Keep all credential material inside the
  encrypted guest. Existing VM commissioning authorization covers this repair.
- **Repository prevention:** reject Fedora base-system and Hermes service names
  at render time; reject names already present in the installer before storage
  mutation; verify the final account's human UID, own home, login shell, wheel
  membership and installed public-key permissions/context before installation
  may succeed. Change current examples and test fixtures to `hermesadmin`.
  Preserve the actual installed Kickstart/settings as historical inputs. Mark
  G01/G02/G07 and T04 stale/in progress when code/runbook changes; rerun focused
  red-before-green regressions, canonical offline/lint and final package checks.
- **Exact next action:** prepare verified-media recovery for this same VM and
  a private disk-unlock handoff, while implementing/tests for the demonstrated
  account-name defect. No production target, providers or Git delivery changes.

### Administrator collision corrected in the qualification guest

- Mounted only the known encrypted root read-only first. Confirmed the installed
  reserved UID 11 account and the fixture public key under `/root`, owned by
  UID 11; `hermesadmin` was absent. This confirms the media-derived diagnosis.
- [Guarded repair](evidence/2026-09-27-hermes-production/admin-collision-repaired-r1.json)
  creates `hermesadmin` UID/GID 1000 with Bash, its own home, wheel membership and
  the dedicated commissioning key. The already-set password was transferred
  only inside guest memory through stdin to the password utility. No password
  or hash was emitted or copied off guest. The reserved account keeps its original
  identity and is locked; only the exact misplaced fixture key was removed.
- Corrected the fixed read-only audit and exact sudo rule. Six synthetic repair
  guards pass; actual rerun preserves account/key/audit file metadata and both
  unrelated-command and extra-argument noninteractive sudo attempts are denied.
  Root ownership, public-key fingerprint, SELinux labels and visudo checks pass.
  This is recovery setup evidence; installed runtime/SSH acceptance remains open.
- Installer prevention now rejects reserved or pre-existing administrator names
  and verifies the final human identity, key and labels. New tests failed before
  the fix (12 reserved-name failures and two absent guards); all 51 focused tests
  now pass. Original installation settings/KS remain unchanged; corrected future
  role settings are retained separately as `*-admin-r2.json` in local staging.
- Refreshed candidate `b53ee4899b049b019ee4f0a1155a03545f1ed792520d578cee9174643060a12e`
  verifies its test signature and extraction; production rejects its unqualified
  status. Only the packaged renderer and runbook changed from the previous
  candidate. Canonical offline/lint/provenance checks are being refreshed.
- **Exact next action:** cleanly unmount/power off rescue, eject only its readonly
  DVD, verify normal persistent XML and canary, then start paused for attachment
  before the private normal-boot unlock. Run the corrected pinned-key audit as
  `hermesadmin` after the operator detaches.

- **Private normal-boot handoff ready:**
  [verified handoff](evidence/2026-09-27-hermes-production/admin-repair-boot-handoff-r1.json)
  records clean unmount/shutdown, ejected rescue DVD, original persistent XML
  restored and unchanged unrelated canary. Same VM started paused, no agent
  console capture. The operator attaches with `--safe --resume`, unlocks the
  existing LUKS volume privately, and detaches at the login screen. Normal SSH
  uses `hermesadmin`; another operator-account login is not required.

### Installed administrator access verified after repair

- Operator reports normal boot and detach. The corrected fixed audit succeeds
  over the existing commissioning key with the previously pinned SSH host
  identity. [Installed audit](evidence/2026-09-27-hermes-production/installed-guest-audit-r2.json)
  verifies `hermesadmin` UID/GID 1000, wheel, Bash, own home, exact key and safe
  ownership/modes/SELinux labels. The reserved operator is locked. General
  noninteractive sudo is still denied; the grant allows only the fixed audit.
- Installed kernel/default both `6.19.10-300.fc44.x86_64`; SELinux enforcing,
  Secure Boot enabled, swap absent, correct encrypted linear LVM/XFS sizes and
  mounted UUIDs. Known retained Kickstart paths are absent. Private installer-log
  inspection is still NOT_RUN; path absence alone does not close secret hygiene.
- Live prerequisites found: Podman is 5.8.1, below the profile's minimum 5.8.4;
  LUKS has only its recovery slot and no TPM token. `mcelog.service` is the sole
  failed unit; its journal explicitly rejects this VM's AMD family 25 CPU.
  These are commissioning work, not an administrator-access failure. No package,
  TPM, service or physical-server change has been performed in response yet.
- Canonical offline PASS: 617 Python cases, 140 ShellSpec examples and all shell,
  guide, full-tree secret and provenance checks. Initial check-only lint FAIL
  is retained: only the newly appended tracker table/blank-line formatting failed.
  Corrected that maintained record; rerun lint and publication checks without
  changing any preserved evidence or repeating unrelated runtime tests.
- **Exact next action:** finish publication verification, prepare the bounded
  guest-only package/service prerequisites for a private sudo invocation, then
  continue encrypted recovery/TPM commissioning. No general passwordless root
  grant, production operation, provider call or independent backup-service change.

- **Publication correction PASS:** the maintained tracker table/blank-line errors
  are fixed; the full check-only lint gate, full-tree secret scan and source-aware
  manifest verify pass. The preceding failed lint remains retained. G01/G02/G07
  and T01/T04 are current within repository scope; live gates remain incomplete.
- **Next private prerequisite handoff prepared:**
  [bounded scope and hashes](evidence/2026-09-27-hermes-production/guest-prerequisites-prepared-r1.json)
  bind the staged public script to this VM UUID and root/var filesystem UUIDs.
  Four synthetic guard tests pass. The private launcher checks workstation free
  capacity, uses pinned key-only SSH and verifies the exact remote script hash
  under sudo before execution. Upgrade only Podman and required dependencies
  through signed Fedora44 release/updates repositories; preserve the original
  mcelog unit and add a KVM-only condition for its observed unsupported CPU.
  Unchanged reruns preserve the drop-in; partial configuration can be resumed.
  No reboot, TPM operation, provider call or production change is included.
- **Exact next action:** operator runs the staged private prerequisite launcher
  and enters the preserved `hermesadmin` password only at sudo. Then verify
  resulting package/service facts over pinned SSH and continue VM commissioning.
  Root execution is NOT_RUN until that private handoff completes; no arbitrary
  passwordless command access was granted to avoid the private prompt.

### Qualification guest prerequisites passed; recovery backup preparation

- Operator's private prerequisite run reports PASS: Podman 5.8.1 to 5.8.7,
  unsupported mcelog skipped through the bounded KVM condition, no failed units,
  no reboot/enrollment/deployment. Independent pinned-key
  [installed audit r3](evidence/2026-09-27-hermes-production/installed-guest-audit-r3.json)
  confirms Podman 5.8.7, system state running, no failures, retained administrator
  identity, SELinux enforcing, Secure Boot enabled and no swap. The user also
  successfully authenticated sudo with the privately preserved password.
- **Recovery preparation baseline:** continue the approved synthetic VM's private
  boot/recovery commissioning and the operator's temporary encrypted workstation
  backup preference. Prepare a dedicated qualification-only RSA recovery key and
  public certificate under an ignored owner-only local recovery directory; reuse
  the already tested AES-GCM/OAEP header workflow with this VM's exact LUKS/var/VM
  identities. Do not reuse the physical server's recovery key or contact it.
  The guest receives only a public certificate. Plaintext staging stays on its
  encrypted var; the workstation receives ciphertext and verifies decryption in
  memory. Preserve all recovery material. This temporary VM header backup does
  not perform or certify the independently gated application backup/restore.
- **Expected acceptance:** existing transaction/decryption/idempotence/corruption
  regressions plus VM identity guard; a private sudo invocation creates only
  the encrypted header, transfer/hash/authenticated decryption verify locally,
  and unchanged reruns preserve it. No LUKS slot or boot change before that proof.
- **Exact next action:** prepare and test the VM-specific backup helper and
  private launcher, then supply the hash-bound sudo command. TPM enrollment
  will follow only after the VM's encrypted recovery copy has been verified.

### Qualification header verified; consolidated boot bootstrap baseline

- The initial header launcher stopped at SSH connection refusal before sudo or
  backup execution. Later inspection found the same VM running (restored) and
  pinned-key audit r4 passed. Added a read-only UUID/state/SSH-banner readiness
  check; it performs no lifecycle operation. The operator retried successfully.
- Independent ciphertext fetch and authenticated in-memory decryption PASS on
  2026-09-29 at 17:41:53 UTC. Receipt binds LUKS
  `bf1c622c-17c0-4d2b-9b51-82c345ad1de7`, certificate
  `2e801bc6061a4587b2630a102943c2b36caf7bb0545fce278d46d1d0292aca5f`
  and ciphertext
  `df86ddc62312059f511572252b41eb84d08d835a79ec0756e9228b21453e73d9`.
  Plaintext 16 MiB header hash is
  `7e1dd8c12f5301aa441c04d6d728a4073b59a494fb841fc4e046a0fbb7c3b56c`.
  Fifteen header-helper regressions PASS. Restore/passphrase/TPM NOT_RUN.
  Guest report time (02:27 UTC) differs from workstation receipt time; use
  identities and authenticated contents, not guest wall time, for this proof.
- **Bootstrap baseline:** fulfill the already approved VM boot commissioning and
  goal's consolidated private setup requirement. Prepare one hash-bound private
  sudo bootstrap that installs root-owned, exact-content VM-only helpers;
  verifies the existing recovery passphrase, additively enrolls PCR7/SHA256
  without PIN, verifies that passphrase again, and builds/verifies the dynamically
  detected selected kernel's initramfs while retaining originals. No reboot
  during private setup. Preserve slot 0, normal default and all recovery copies.
- After successful setup, grant only exact named helper invocations for facts,
  normal reboot/poweroff, a separate one-time recovery entry with poweroff, and
  exact temporary-entry cleanup with return to normal boot. No wildcard paths,
  arbitrary arguments, apply operation or general shell in the passwordless rule.
  Recovery shutdown allows paused start/console attachment before a fresh prompt.
  Each state transition is serialized and bound to boot identity; refuse unsafe
  replay, changed inputs, unrelated entries and partial states requiring review.
- **Expected acceptance:** existing TPM transaction/rollback and recovery-entry
  tests plus dynamic selection, wrong-VM, replay and bounded-installation guards;
  private setup PASS, independent root facts, named-command denial checks and
  live warm/cold/passphrase/return-to-normal boot proofs. Physical power restore,
  independent application restore and provider acceptance remain separate gates.
- **Exact next action:** finish and test the consolidated bootstrap, bind it to
  this verified ciphertext, stage public helper bytes through pinned SSH, and
  hand off one private sudo/LUKS setup command. Do not enroll before that handoff.

### Consolidated qualification boot handoff prepared

- [Preparation and source bindings](evidence/2026-09-27-hermes-production/qualification-boot-prepared-r1.json)
  retain the independent header receipt, audit r4, public helper identities,
  stage receipt and test evidence. The non-root header preview refused the
  root-only DMI read; the identity guard was retained. No backup mutation occurred
  in that preview. The first bootstrap lint run found two builder style errors;
  its failed log is retained and the corrected rerun passes.
- Boot tests PASS: 20 TPM transaction/rollback cases, eight selection/transition
  and trusted-state cases, 25 recovery-entry/cleanup cases, and eight bounded
  bootstrap cases. Tests cover exact reruns preserving files, conflicting or
  corrupted payload refusal, no grant after failed setup, removal of only the
  newly added rule on validation failure, wrong VM and unsafe links. These are
  synthetic safety tests, not live boot or passwordless-grant acceptance.
- Public bootstrap `d05c0b23ee8676b77cd91bbbca1867bc7630a406578acd1fee7bd506c21d60d8`
  is staged under `hermesadmin` through pinned SSH. Embedded helper bytes match
  the tested sources. Private launcher syntax and TTY guard checked. Root
  installation, enrollment, live command-denial and all VM boot proofs NOT_RUN.
- **Exact next action:** operator runs
  `.toolbox/hermes-production-validation/synthetic-stage/qualification-boot/run-private-bootstrap.sh`
  privately, entering sudo and the existing VM LUKS passphrase at the three
  labeled first-setup prompts. The script does not reboot. On success, verify
  fixed root facts and refusal of extra/unrelated commands, then perform the
  already approved VM warm/cold/recovery/return-to-normal boot sequence.
- Record publication initially failed only for two new extra blank lines; the
  failed log is retained. Corrected those maintained lines and reran the scoped
  Markdown/secret/provenance/whitespace checks. Earlier evidence is unchanged.
- Publication correction PASS: scoped Markdown lint, full-tree secret scan,
  source-aware manifest and whitespace checks. A separate local fixed-operation
  client is prepared for post-bootstrap facts, live command-denial checks and
  boot transitions; it has not invoked any guest command yet.

### Private-input blocker revalidated

- Previous continuation was no progress: pinned SSH succeeded, but both boot
  setup reports were absent. Rechecked on 2026-09-29 at 17:56:57 UTC: SSH exit 0,
  `bootstrap-report.json` and `report.json` still absent. This is a private-input
  dependency, not a verified wait on a running process. No reboot was attempted.
- The same blocker has persisted across the preparation turn and two goal
  continuations. Independent preparation and its applicable checks are finished;
  further live qualification depends on private setup. Goal marked BLOCKED, not
  complete. All unperformed live gates remain open.
- **Exact next action:** operator runs the prepared
  `.toolbox/hermes-production-validation/synthetic-stage/qualification-boot/run-private-bootstrap.sh`
  in a private terminal and returns its non-secret result. Then resume with
  independent root facts and bounded-command denial checks before boot testing.

### Qualification automatic boot passed; private recovery handoff

- Operator private bootstrap reports PASS with recovery slot preserved and
  passphrase tests before/after enrollment passing. Independent fixed root facts
  verify the exact prepared helper, selected/running kernel, image/crypttab
  hashes, PCR7 SHA256 no-PIN policy, healthy system and preserved recovery slot.
  Both unrelated root commands and extra arguments are denied by sudo.
- [Live boot evidence](evidence/2026-09-27-hermes-production/qualification-boot-live-r1.json)
  records distinct boot IDs for automatic warm reboot and clean cold start,
  unchanged image/crypttab/PCR identities, no recovery marker, and a healthy
  running system. No passphrase was supplied during either test. Persistent VM
  definition and unrelated disk canary remain unchanged. Initial guest clock
  skew resolved by cold-start verification; evidence retains workstation time.
- The fixed recovery helper preserved the normal default and all LUKS metadata,
  armed only its separate one-time passphrase entry, and powered off cleanly.
  The same VM was started paused after identity, definition, capacity and canary
  checks. No agent console capture is active. Recovery boot and subsequent
  return-to-normal proof remain NOT_RUN; this does not close G05 or full scope.
- **Exact next action:** operator attaches with
  `virsh -c qemu:///session --escape '^q' console hermes-production-qualification --safe --resume`,
  enters the existing VM LUKS passphrase privately, detaches using Ctrl+Q at
  login, and reports prompt/unlock success. Then independently verify recovery
  boot, remove only the owned temporary entry and test the normal reboot.

### Qualification recovery and normal boot verified

- Operator reports `vm unlocked` during the requested private recovery test.
  Independent root facts show a new boot with recovery parameters. The fixed
  cleanup helper verified the exact slot-0/token-disabled parameters, preserved
  all LUKS metadata and normal default, retained then removed only the owned
  entry, and rebooted. A subsequent distinct boot is healthy with no recovery
  parameters and unchanged crypttab/image/PCR/recovery-slot identities.
- [Boot sequence proof](evidence/2026-09-27-hermes-production/qualification-boot-live-r2.json)
  separates operator-reported unlock from independently verified boot facts.
  This closes this VM's basic recovery sequence, not re-enrollment, installation
  log hygiene, application runtime, independent restore or provider gates.
- **Next application commissioning baseline:** reuse the approved synthetic
  stage: bind the current signed candidate's receiver sources, this VM's
  identities, test signing trust and dedicated deployment public key. Prepare
  a private root bootstrap installing the existing bounded dispatcher and
  commissioning evidence; select fixture/synthetic mode with gateway networking
  disabled. Preserve existing root boot helpers and all recovery evidence. No
  backup endpoint will be contacted: independent Restic service/restore remains
  deferred and must not be represented as commissioned. Private sudo is still
  required because the installed boot grant intentionally excludes application
  installation and general root execution.
- **Exact next action:** prepare and verify the synthetic application bootstrap
  against candidate and host identities, then hand off the private sudo command.

### Synthetic application dispatcher private setup prepared

- [Source, target and test bindings](evidence/2026-09-27-hermes-production/qualification-application-prepared-r1.json)
  retain the seven passing guard tests and staging receipt. Candidate archive
  SHA256, test signature and all 15 receiver source hashes verify; receiver
  identity remains `01770100903218a972d0b5262ff272849d1fba756c54d97aa1d65cddd755ac5c`.
  Config schema, generated launcher syntax and private TTY refusal pass. Initial
  builder style failure is retained; formatting correction and rerun pass.
- Read-only guest identity inspection was delayed by automatic approval review
  timeout, not a safety determination. The single permitted retry succeeded.
  Machine identity, host public-key hash and source address were read through
  pinned SSH. No physical host or other VM was contacted.
- Staged public bootstrap
  `f3586dcaba63f9cb0b5328a80c2f0d0dc3ee0722a7fa69a68eef4c9ae305770a`
  is bound to the completed normal boot. It refuses wrong VM, changed boot or
  source, conflicting files and production mode; installs only the existing
  signed receiver/dispatcher; and records actual commissioning proofs. Fixture
  exclusions retain NOT_RUN for independent restore and physical power tests.
- Backup configuration deliberately uses `backup.invalid` as an unconfigured
  placeholder. No backup password is provisioned and no endpoint is contacted;
  backup execution is outside this stage. No application containers, provider
  requests or Telegram messages have run. Root bootstrap execution is NOT_RUN.
- **Exact next action:** operator runs
  `.toolbox/hermes-production-validation/synthetic-stage/qualification-application/run-private-bootstrap.sh`
  privately and supplies sudo only. Then validate the bounded dispatcher and
  current preflight before staged synthetic deployment and runtime tests.

### Application platform refusal and memory-only remedy proposal

- Operator application bootstrap failed `bootstrap-preflight-failed:platform`,
  before dispatcher installation. Its protected public source/config staging
  may exist and must be retained; this is not a claim of zero staging writes.
- [Read-only platform diagnosis](evidence/2026-09-27-hermes-production/qualification-application-platform-r1.json)
  found 8,244,031,488 bytes exposed by Linux, below the unchanged 8,321,499,136-byte
  minimum. Fedora44 Server/x86-64, expected machine identity, SELinux enforcing,
  cgroup v2, EFI, TPM, Secure Boot and absent swap are observed. Assigned memory
  is 8 GiB; exposed memory is lower. Do not weaken the platform requirement.
- [Prepared memory-only change](evidence/2026-09-27-hermes-production/qualification-memory-proposal-r1.json)
  changes only the qualification VM's memory/currentMemory from 8 to 9 GiB;
  preview XML is retained locally. Host MemAvailable was 25,958,100 KiB. No
  libvirt definition, active allocation or boot state has been changed.
- This exceeds the approved 8 GiB resource envelope. Explicit approval has
  been requested for this one VM, followed by clean shutdown/start and refreshed
  boot/commissioning checks. Restore VM and physical server are excluded.
- **Exact next action:** await resource approval; if approved, validate the exact
  preview/baseline and cleanly apply the memory-only change, verify the platform
  and boot identities, and prepare an updated private application bootstrap.
  Existing pre-change boot evidence remains historical; do not claim live
  application acceptance or treat the failed bootstrap as installed.

### Approved qualification memory adjustment completed

- **Approval:** operator explicitly selected `Approve 9 GiB for qualification VM`.
  Scope is this VM only; restore fixture and physical server remain unchanged.
- Cleanly shut down through the fixed boot helper; compared the entire inactive
  definition to its retained baseline; changed only memory/currentMemory; verified
  the resulting full definition, free capacity and unchanged canary; then started
  the VM. The [applied change](evidence/2026-09-27-hermes-production/qualification-memory-applied-r1.json)
  records 9 GiB. Retained original ownership metadata; current ownership now
  reports 9216 MiB. Future definition guards must use the retained local
  `qualification-application/memory-9gib-applied-r1.xml` baseline rather than the
  historical 8 GiB XML. No guest package, kernel or LUKS configuration changed.
- [Memory and boot revalidation](evidence/2026-09-27-hermes-production/qualification-boot-memory-r1.json)
  PASS: 9,288,417,280 exposed bytes exceed the unchanged 8,321,499,136-byte minimum.
  A new automatic cold boot is healthy with no recovery parameters and unchanged
  kernel/image/crypttab/PCR/LUKS identities. Previous passphrase-recovery proof is
  retained for those unchanged identities; recovery was not repeated at 9 GiB.
- The first application bootstrap is STALE for its bound boot ID; original
  sources are preserved under local `qualification-application/prepared-r1/`.
  [Refreshed handoff](evidence/2026-09-27-hermes-production/qualification-application-prepared-r2.json)
  binds bootstrap `9c2c5e9e641c0fdc10bc6ffb5613bcc39ae617170ab4c38d97d7515af68139ab`
  to the new boot and passes all seven guard tests. It is staged through pinned
  SSH. No root application installation has run since the memory correction.
- **Exact next action:** retry the same private application launcher; it now
  selects the revised hash-bound script. Enter sudo only, then verify installed
  dispatcher/preflight before synthetic deployment. Root application bootstrap,
  runtime, restore and provider acceptance remain unperformed.

### Runtime sudo denial parsing correction baseline

- After the approved memory fix, private bootstrap reached runtime-account
  verification and refused `runtime-sudo-access-or-inspection-failed`. The
  non-login `hermes` account now exists as UID/GID 1001. Read-only sudo listing
  returns exit 0 with exactly `User hermes is not allowed to run sudo on
  hermes-qualification.` Existing code wrongly requires exit 1. No privileges
  were observed; do not grant any to make the check pass.
- **Correction scope:** recognize only the explicit C-locale no-privileges
  response with supported successful/denial listing statuses; reject actual
  grants, ambiguous text, diagnostics and inspection failures. Add red-before-
  green regressions. Inspect and correct partial-bootstrap receiver selection
  so a private retry can select its corrected receiver before any application
  exists, while preserving an active application's selected receiver.
- G01/G02/G07 and source-bound candidate evidence become STALE for these source
  changes. Retain all failed attempts and the old installed receiver. Re-run
  focused and required repository gates, regenerate/sign/verify the candidate,
  and rebuild the private setup for its new receiver identity before retrying.
- **Exact next action:** add failing regressions for the observed denial and
  partial bootstrap, implement the bounded corrections, then validate and
  refresh the candidate/bootstrap. No automatic general root access is added.

### Runtime sudo and partial-bootstrap correction verified

- [Observed listing](evidence/2026-09-27-hermes-production/qualification-sudo-diagnostic-r1.json)
  proves the exact no-privileges response with exit 0. The corrected predicate
  accepts only the complete C-locale denial with exit 0 or 1. Actual grants,
  empty/ambiguous output, unsupported statuses and inspection errors are refused.
  The red test also exposed that the old substring check accepted an inspection
  error containing `not allowed`; the exact-match fix closes that false positive.
- A separate red regression reproduced the obsolete receiver selection after
  an interrupted initial bootstrap. Successful private setup now selects its
  validated receiver only while no application exists. An active application's
  receiver remains selected; unchanged reruns retain file identity/metadata.
  One new active-application test initially had an incomplete mocked account
  fixture (KeyError); its setup was corrected before the passing rerun.
- [Verification and handoff](evidence/2026-09-27-hermes-production/qualification-application-prepared-r3.json):
  55 focused Python, 621 canonical Python, 140 ShellSpec, full check-only lint,
  full-tree secret scan and source-aware provenance PASS. Seven private bootstrap
  guard tests also pass. G01/G02/G07 are current for these source changes.
- New test-signed candidate
  `6b3e4e7f141a114e428b56f885c9b47b3231f4043aad93b4e66f3d1d3e916ed5`,
  archive `2b52d813a368c233697d5b10921d6e28567a0ec6ae08660b68900a46c11a4e68`,
  receiver `bad84b56cd7d384e73ff60d3831f866ecff525f409e864699fd3989d8bf2c647`,
  passes signature/extraction and unqualified-production rejection. Only packaged
  preflight, host bootstrap and runbook changed. Old candidate remains retained
  as STALE; no previously unperformed live gate is promoted by repository tests.
- Corrected private bootstrap
  `7d93bb6f2a13f00cc65afdf1d9e68d86e585fd91bccb07df12357374f2f5f60d`
  is staged with the verified new receiver. Prior local sources are retained in
  `qualification-application/prepared-r2/`; old guest receivers are not removed.
- **Exact next action:** operator retries the same private application launcher
  with sudo only. Then verify the new bounded dispatcher and commissioning
  before synthetic deployment. Root retry and application runtime remain NOT_RUN.

### Preproduction resumption and application bootstrap verified — 2026-09-29

- **Authority:** user resumed all mandatory preproduction gates, retaining the
  named synthetic VM approval, 9 GiB/two-CPU qualification allocation, sequential
  8 GiB restore fixture and 20 GiB workstation free-space floor. No physical
  server contact, Git delivery, delegation, external backup, provider spending
  or Telegram messages are authorized by this resumption. Existing dirty work,
  VM disks and recovery artifacts are preserved.
- **Fresh revalidation:** branch `codex/hermes-production-bundle`; all 35 packaged
  source files, four prepared source hashes and seven retained evidence hashes
  match the current candidate. Archive SHA256 and all 15 staged receiver hashes
  match. The running VM UUID, complete inactive XML, 9 GiB/two-CPU allocation,
  pinned SSH identity, machine identity, boot ID and remote bootstrap hash match
  the current baseline. Restore domain remains absent. Workstation free space
  is 70.88 GiB. See [resumption evidence](evidence/2026-09-27-hermes-production/qualification-resume-application-r1.json).
- **Private blocker resolved:** the public bootstrap receipt is now present
  and PASS, SHA256 `4da430b36ac94bb0c3c8810bbbf5e9b7a850ba95be9e069e35d7d402ffa71135`.
  Its corrected bootstrap/receiver, synthetic mode and exact commissioning
  gates/evidence match the staged script. Root ownership, safe modes, exact
  file set and every installed receiver hash pass. [Receipt validation](evidence/2026-09-27-hermes-production/qualification-bootstrap-validated-r1.json)
  and actual [named preflight](evidence/2026-09-27-hermes-production/qualification-live-preflight-r1.json)
  pass all seven checks and match the receipt's commissioning identities.
  [Named status](evidence/2026-09-27-hermes-production/qualification-live-status-before-r1.json)
  confirms no current application or transaction; this does not establish runtime
  acceptance. The agent did not invoke the private bootstrap or receive sudo input.
- **Transport:** productionctl's named operations use the dedicated deployment
  key. A local validation SSH adapter explicitly adds `IdentityAgent=none`,
  `ForwardAgent=no`, no global known-hosts and no password/keyboard-interactive
  fallback to its existing batch, identity-only, pinned strict host checks.
  Packaged source is unchanged. Initial sandbox transport refusals were resolved
  by reviewed read-only access; no guest or host permissions were weakened.
- **Expected next acceptance:** preview then apply the unchanged signed candidate
  only through the bounded dispatcher; observe actual synthetic gateway/worker
  verification, durable committed journal, matching release/receiver and stage
  timings. Then verify unchanged reruns and the remaining rejection, interruption,
  failed-update and rollback behaviors with separately retained live evidence.
  No backup operation may use the unconfigured endpoint/password. Installer-log
  private hygiene, TPM re-enrollment, isolated encrypted application restoration
  and exact-candidate private application tests remain open.
- **Exact next action:** run the named synthetic deployment preview and, if its
  current preflight passes, apply this candidate and verify actual runtime.

### First live deployment supervision failure — corrective baseline

- Named deployment preview PASS. Applying candidate `6b3e4e7f...e916ed5` reached
  durable attempt `96cbdc942a0442b8b3ff9912e498c3a6`, stage `prepared`, without
  a current application, snapshot or completed import/configuration. The receiver
  remains alive under the original writer lock. A read-only process-name audit
  observes receiver PID 4192, guard PID 4280 and adopted runtime-user `catatonit`
  PID 4293. Do not treat SSH availability or continued preflight PASS as deployment
  success. G04's initial live deployment is FAIL/BLOCKED on safe interruption.
- Seven actual dispatcher rejection cases PASS: unknown operation, extra and
  duplicate fields, nonboolean apply, ignored shell command, wrong pinned host
  key and concurrent-operation `operation-busy`. These observations do not close
  corruption, application canary, rollback or runtime gates.
- **Correction:** rootless Podman's first invocation may create a persistent
  namespace pause process. The generic subreaper must continue retaining the
  lock for all of its descendants. Initialize the namespace through the existing
  runtime user manager with a fixed, bounded, waited Podman-info service before
  any transaction/backend Podman invocation; preserve generic writer supervision.
  This follows systemd's [service-parent and waited execution contract](https://www.man7.org/linux/man-pages/man1/systemd-run.1.html)
  and Podman's [rootless namespace reuse implementation](https://github.com/containers/podman/blob/v5.8.7/pkg/rootless/rootless_linux.go).
  Add initialization failure and dispatch ordering regressions; rerun focused,
  canonical Toolbox, lint, secret/provenance and signed-candidate checks.
- G01/G02/G07, T01/T04 and source-bound candidate/receipt results become STALE
  when the correction changes packaged code. Earlier reports remain retained;
  boot/storage/recovery evidence is unaffected by application-source changes.
- **Private interruption prepared:** only the exact first prepared attempt,
  unchanged VM/boot/receiver, known root dispatcher/guard tree and verified
  non-writing Podman pause may be interrupted. Eight guard tests pass. The helper
  never signals `writer_guard`, replaces/removes the lock, changes the journal,
  starts containers, reboots or touches backup/provider services. Changed PIDs,
  unexpected descendants or application state are refused. Its hash-bound private
  launcher is `qualification-application/run-private-interruption-r1.sh` in local
  staging. Root execution is NOT_RUN; operator private sudo is pending.
- **Exact next action:** implement/test/package the namespace initialization
  correction while awaiting the interruption result. Then verify the retained
  public interruption receipt and recover the prepared journal through reviewed
  bounded operations before any private receiver update or new deployment.

### Namespace correction verified and private recovery handoff retained

- [Correction and preparation index](evidence/2026-09-27-hermes-production/qualification-namespace-prepared-r1.json)
  binds the maintained source hashes, canonical/focused/lint/package logs and
  staged private bootstrap. Focused Python: 57 PASS; canonical Python: 623 PASS;
  ShellSpec: 140 PASS; full check-only lint, full-tree secret scan and source-aware
  provenance PASS at the canonical run. Real dispatcher SIGKILL and detached-writer
  lock/recovery tests pass with the generic writer guard unchanged. Publication
  checks are refreshed after these additional records rather than rerunning
  unchanged executable tests.
- The corrected initializer runs only fixed credential-free Podman-info in a
  bounded, waited user-manager service before transaction recovery/backend work.
  False/empty rootless responses and initialization failures are refused before
  recovery. An initial test fixture incorrectly combined mocked root identity
  with a real unprivileged lock; its corrected red run demonstrates the missing
  initializer and missing dispatch ordering. The first broad focused run also
  found the real-process fixture needed the new OS-setup stub; after that narrow
  fixture update all 57 tests pass. Both unsuccessful runs are preserved.
- [Replacement bundle](evidence/2026-09-27-hermes-production/bundle-namespace-init-r1.json):
  candidate `579403970f8225aea05866752e82e8800b3bac3f5abcf2cd892ffc9f52944295`,
  archive `d2f206c87e4adc6373969f2720dc68b3e9d2e67ecf3525d0e9eebb9026a1d074`,
  receiver `a1edcaad3a47e22ce4246b13243eb39c8d66038388def6c21feb5dd31bb5671c`.
  Retained `.toolbox/hermes-production-validation/synthetic-stage/candidate-namespace-init-r1.tar`
  is 1,148,764,160 bytes. Only packaged runbook, host and runtime changed. Test
  signature/extraction and unqualified-production rejection PASS; this is still
  an unqualified candidate. Old archive/receiver/bootstrap and first-attempt
  evidence remain retained as STALE for replacement-candidate qualification.
  Workstation free space after packaging is 65.67 GiB, above the 20 GiB floor.
- [Private replacement staging](evidence/2026-09-27-hermes-production/qualification-namespace-staged-r1.json)
  binds bootstrap `31501c3893e12a4f308ed018ddc9959bb11f90b2c3fd329fdddd2265615712a0`.
  Eleven guards PASS, including wrong/stale boot, changed payload, changed initial
  attempt, missing interruption proof, production mode, named recovery ordering
  and unchanged recovery reruns. After a verified interruption receipt it primes
  namespace infrastructure under the operation lock, uses installed named
  `rollback --apply` to recover only the initial `prepared` attempt to `aborted`,
  then installs the corrected receiver. Rollback's subsequent
  `no-matching-rollback-snapshot` is expected only when that exact recovery result
  is independently confirmed; no older application or snapshot exists. The
  bootstrap does not start containers, reboot, provision backup access or make
  provider/Telegram calls. Root execution and new runtime remain NOT_RUN.
- [Latest pinned handoff status](evidence/2026-09-27-hermes-production/qualification-live-status-handoff-r1.json)
  at 19:59 UTC still reports no current application and the same initial
  `prepared` journal. [Public interruption check](evidence/2026-09-27-hermes-production/qualification-interruption-current-r1.json)
  reports `APPLICATION_INTERRUPTION_REPORT_ABSENT`. The old operation/guard
  remain retained; neither has been killed by the agent. Do not repeat deploy
  or substitute a fresh/recreated VM for this preserved failed attempt.
- **Remaining mandatory gates:** G03 private installer-log hygiene; G04 actual
  replacement runtime, repeatability/rejection/interruption, failed-update and
  rollback plus isolated encrypted application backup/restore; G05 TPM
  re-enrollment; G06 separately authorized exact-candidate private
  provider/Telegram/approval tests. The unconfigured backup endpoint/password
  remain untouched. No physical server contact, Git delivery or delegation.
- **Exact next action — operator private input:** run
  `bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-validation/synthetic-stage/qualification-application/run-private-interruption-r1.sh`
  in the private workstation terminal and return only its final non-secret
  status/error. This is an input dependency for the already authorized synthetic
  interruption, not a request for broader sudo access or deployment authority.
  Once its receipt is independently validated, the next private setup launcher
  is `.toolbox/hermes-production-validation/synthetic-stage/qualification-namespace/run-private-bootstrap.sh`;
  do not invoke that replacement before the interruption result is checked.
  Resume fresh actual runtime tests against the replacement candidate only
  after its root bootstrap/preflight/receiver proofs pass. Full objective remains
  BLOCKED, not complete.

- **Publication verification PASS:**
  [retained publication log](evidence/2026-09-27-hermes-production/qualification-namespace-publication-r1.log)
  records Markdown lint, full working-tree secret scan with positive control and
  source-aware manifest verification. All prepared source/evidence index hashes
  and 171 local documentation link targets verify. Both generated private
  launchers parse, their wrappers pass Bash syntax, and both refuse execution
  without a private TTY before reading access inputs or contacting the guest.
  These final record/log additions receive another narrow publication refresh;
  packaged source, candidate and executable tests are unchanged. G01/G02/G07 and
  T01/T04 are PASS/DONE within repository scope. T02/T03 and mandatory G03–G06
  remain incomplete for the replacement candidate.

### Private interruption r1 refused; executable identity correction staged

- Operator returned `STOP: unexpected-process-tree` from the r1 private helper.
  Its preserved source puts that refusal before all signal calls. Fresh pinned
  [read-only predicate diagnosis](evidence/2026-09-27-hermes-production/qualification-interruption-refusal-diagnostic-r1.json)
  confirms the same boot, exact receiver/guard argument comparisons, root/runtime
  UIDs, parent relationships and only the original three processes in this tree.
  The pause has no children. No interruption receipt exists. Reading the three
  processes' executable links as the unprivileged administrator is denied;
  actual root executable identity remains a private-execution precondition.
- [Fixed installed executable inspection](evidence/2026-09-27-hermes-production/qualification-pause-executable-r1.json)
  finds `/usr/libexec/podman/catatonit` resolves to
  `/usr/libexec/catatonit/catatonit`, a root-owned regular mode-0755 file with
  safe root-owned ancestors and SHA-256
  `73fddf8122b7a92630bcffccf92c9742f64e49b2f61b067a431bc6280d7f618a`.
  R1 incorrectly assumed the kernel executable link would retain the argv
  symlink path; it excludes this observed resolved path. This explains a likely
  executable-predicate mismatch, not a live interruption PASS. The failed query
  for the nonexistent `/usr/bin/catatonit` package path is retained and supplies
  no package ownership proof.
- [Fresh bounded status](evidence/2026-09-27-hermes-production/qualification-interruption-refusal-status-r1.json)
  still has the exact initial `prepared` attempt, no selected application and
  seven actual preflight checks PASS. Libvirt UUID/running-state check PASS;
  no lifecycle operation was performed. The writer guard, operation lock,
  journal, VM disks and recovery artifacts remain preserved. The agent did not
  signal any process or receive sudo input.
- R2 requires the exact observed resolved executable, its pinned bytes, unchanged
  alias resolution and safe root-owned ancestors. It retains the same VM/boot,
  receiver, journal, PIDs, UIDs, argument, descendant and pidfd checks. It still
  never signals the guard or removes/replaces the lock. If process predicates
  fail again, only named boolean comparisons are printed; raw process arguments,
  environments and unrecognized paths are never emitted. R1 and its eight-test
  record remain byte-for-byte retained; 13 R2 guard tests PASS locally.
- [Hash-bound R2 staging](evidence/2026-09-27-hermes-production/qualification-interruption-prepared-r2.json)
  pins helper `a2c62d0df3add6f2d06d59b11c02afd7f45a5b56bb982b9de8c575e1ad221e2e`
  at `/home/hermesadmin/hermes-qualification-interrupt-a2c62d0df3add6f2.py`,
  administrator-owned mode 0600. [Retry evidence index](evidence/2026-09-27-hermes-production/qualification-interruption-resume-r2.json)
  binds preserved R1 and new helper/tests/private launcher. Root execution is
  NOT_RUN. Packaged production source, replacement candidate, receiver and
  private replacement bootstrap are unchanged; previous repository executable
  test results remain applicable within their tested scope. Record/evidence
  publication checks are refreshed separately.
- **Exact next action — operator private input:** run
  `bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-validation/synthetic-stage/qualification-application/run-private-interruption-r2.sh`
  in the private workstation terminal, entering sudo privately, and return only
  the final non-secret status/error. This completes the same already authorized
  bounded synthetic interruption; no broader sudo authorization is requested.
  Verify its public receipt independently before the staged replacement bootstrap
  or new deployment. G03–G06 and the full preproduction objective remain open;
  no backup/provider/Telegram operations or production acceptance are claimed.

- **R2 handoff verification PASS within staging scope:**
  [Toolbox guard/syntax/private-terminal checks](evidence/2026-09-27-hermes-production/qualification-interruption-verified-r2.json)
  confirm all 13 guards, Python/Bash syntax and refusal before access inputs or
  guest contact without a private TTY. [Publication checks](evidence/2026-09-27-hermes-production/qualification-interruption-publication-r2.log)
  pass Markdown, full working-tree secret scan with positive control, source-aware
  provenance, 177 local documentation targets and unchanged replacement archive,
  bootstrap and prepared source/evidence hashes. Final additions receive another
  narrow publication refresh. [VM configuration recheck](evidence/2026-09-27-hermes-production/qualification-interruption-vm-r2.json)
  confirms the retained 9 GiB/two-CPU baseline, running UUID and absent restore
  domain. Initial raw-byte XML comparison failed only because `virsh` added a
  terminal newline; exact comparison after removing terminal newlines and
  canonical XML comparison PASS. No baseline or VM configuration was changed.
  These results do not establish successful interruption or live runtime.

### Actual interruption and corrected bootstrap verified; runtime resumed

- [Independent R2 interruption validation](evidence/2026-09-27-hermes-production/qualification-interruption-validated-r2.json)
  confirms the root-owned safe public receipt, exact VM/boot/old candidate,
  receiver/attempt and retained journal hash. All three old processes are absent;
  `guard_signals` is `NONE`. Actual named `verify` acquires the retained operation
  lock and refuses `unfinished-transaction` before any backend command. The
  [interrupted original deployment client result](evidence/2026-09-27-hermes-production/qualification-live-deploy-interrupted-r1.json)
  exits 1 and remains historical failure evidence, not runtime acceptance.
  [Read-only transition observations](evidence/2026-09-27-hermes-production/qualification-goal-public-state-r1.json)
  and [replacement handoff check](evidence/2026-09-27-hermes-production/qualification-namespace-handoff-r2.json)
  are retained. The operator completed private R2 execution; the agent sent no
  signals or received private sudo input.
- Operator privately ran the staged namespace bootstrap. [Independent validation](evidence/2026-09-27-hermes-production/qualification-namespace-bootstrap-validated-r1.json)
  binds bootstrap `31501c38...5712a0` and receiver `a1edcaad...5671c`, checks the
  full public receipt and safe root-owned parents/files, all 15 receiver hashes
  and exact file set. [Actual named preflight](evidence/2026-09-27-hermes-production/qualification-namespace-live-preflight-r1.json)
  passes seven checks and matches receipt commissioning identities. [Named status](evidence/2026-09-27-hermes-production/qualification-namespace-live-status-before-r1.json)
  proves the initial journal is exactly `aborted`, SHA-256
  `d932020271a3886f8f4e06a89713403184b9cad138f5f45576d72a8979d92771`,
  with no current application. Receipt confirms named recovery, no application
  changes, no deployment/reboot/provider calls and no configured backup service.
  VM/boot/kernel and the current 9 GiB/two-CPU baseline remain unchanged; restore
  domain is absent. Encrypted header-copy re-verification is not application
  backup/restore or TPM re-enrollment evidence.
- [Local validator correction](evidence/2026-09-27-hermes-production/qualification-namespace-validator-correction-r1.json)
  retains an initial field-name failure: the staged baseline calls the field
  `running_kernel`, while the validator first referenced `kernel`. Correcting only
  this local read-only check yields PASS; no packaged or guest source changed.
- The new local named-operation driver binds the replacement archive hash and
  requires the independent corrected-bootstrap proof before any apply operation.
  It retains strict pinned transport and the dedicated deployment key. Previous
  source/evidence hashes still match. **Exact next action:** preview, then apply
  unchanged replacement candidate `57940397...44295`; observe actual gateway/
  worker verification and committed journal, then rerun and rejection/update/
  rollback qualification. G03, G05, G06 and full G04 remain incomplete. The
  managed Goal was paused by the user's conversation interruption; receipt input
  resumes this authorized work, and no goal is marked complete.

### Replacement candidate actual runtime and unchanged rerun PASS

- [Actual synthetic runtime/repeatability index](evidence/2026-09-27-hermes-production/qualification-live-namespace-runtime-r1.json)
  binds all 13 retained reports for candidate `57940397...44295`, receiver
  `a1edcaad...5671c` and unchanged boot `d83a7442...779d15`. The actual named apply
  returns `CHANGED`; journal `da4acc2f4f704e2a99da54b8b26afbc0` is durably
  `committed` and both current pointers match. Independent named `verify` passes
  actual credential-free configuration/process/image/SELinux/rootless/resource/
  read-only/socket/network checks in the maintained engine. This is synthetic
  runtime qualification, not provider/Telegram or production acceptance.
- Actual stage timings: import 35.247 s, configuration 1.878 s, restart 0.453 s,
  verification 2.494 s, stopped-stage work 0.138 s and transfer authentication/
  extraction 3.214 s. The namespace pause is now observed as a child of the
  runtime user manager, rather than a writer guard; it remains alive across
  successful operation completion. Generic writer supervision is unchanged.
- The same archive rerun returns `UNCHANGED`. Current pointers and the committed
  journal are identical; two actual `conmon` PIDs/start identities, runtime
  infrastructure identities and both public Quadlet hashes remain identical.
  Seven fresh actual malformed-protocol/forced-command/wrong-host-key/concurrency
  rejection cases PASS against this receiver, including `operation-busy` while
  the confirmed live apply ran.
- An authenticated test fixture changes only the declared worker image identity
  to an intentionally absent ID, retaining all payload files and this same
  receiver. Its qualification identity is recomputed and test-signed; production
  policy correctly refuses it. A separate 10 KiB tampered-signature fixture is
  rejected by the actual dispatcher with `command-failed:ssh-keygen`, before any
  application/journal transition; subsequent runtime verification passes. This
  establishes signature corruption rejection, not every payload-corruption case.
  Source/candidate inputs and original archives remain retained. Workstation free
  space after negative-fixture packaging is 57.30 GiB, above the 20 GiB floor.
- **Exact next action:** finish the confirmed live intentional-import-failure
  update; independently verify durable recovery to the exact current candidate,
  matching receiver/config/images, then exercise explicit rollback idempotence.
  The update uses only its automatic local stopped-state transaction snapshot;
  no external Restic operation, provider request or Telegram message is run.
  Reboot/interruption/missing-mount and isolated encrypted application restoration
  remain open, as do G03 private log hygiene, G05 re-enrollment and G06 private
  application tests. G04 is still IN_PROGRESS, not a broad PASS.

### Actual failed-update recovery and rollback rerun verified

- [Failed-update recovery index](evidence/2026-09-27-hermes-production/qualification-live-failed-update-recovery-r2.json) binds both actual failed imports and independent runtime/status postconditions. Both attempts durably recover the exact candidate and receiver from a matching stopped-state snapshot. The first observer expected `podman`, but the maintained supervisor names its first command argument, `runuser`; the failed observer is preserved. After independent recovery verification, the corrected observer's fresh live retry matches `STOP: command-failed:runuser`. No application source or receiver changed.
- The corrected attempt `72a322befaef4c36a574af98a7aed3c8` retains `recovered`, its matching snapshot and final candidate as `previous`. Actual runtime verification passes. Explicit named rollback returns `UNCHANGED`; the journal and current pointers remain identical. This proves retry after automatic recovery, not yet explicit restoration after a committed successful update.
- **Exact next action:** prepare a test-signed upgrade fixture differing only in a public qualification marker, perform the approved synthetic upgrade and explicit rollback to the final candidate, then verify its actual application warm/cold boot. Preserve all snapshots and failed-attempt evidence; do not contact the unconfigured backup endpoint or provider/Telegram services. Full G04, private G03/G05/G06 and production acceptance remain open.

### Successful synthetic update and explicit rollback PASS

- [Actual explicit rollback index](evidence/2026-09-27-hermes-production/qualification-live-explicit-rollback-r1.json) binds ten reports. Test-signed upgrade `b158afd9...8cc40` adds only one public qualification marker; all original payload, retained images and receiver remain identical. Actual upgrade returns `CHANGED`, runtime verification passes and transaction `ab3fdeabf3574cf4a740ed83aaf84b5b` commits with a matching stopped-state snapshot of the final candidate.
- Named rollback returns `ROLLED_BACK`; the same transaction becomes `recovered`, both current pointers return to final candidate `57940397...44295` and receiver `a1edcaad...5671c`, and independent actual runtime verification passes. This is live restoration through the maintained local transaction snapshot path, not external Restic backup or isolated application restore evidence.
- A full retained archive with its original valid manifest/signature and exactly one altered runbook payload byte is rejected by the actual dispatcher with `artifact-hash-mismatch`. Current pointers and the prior journal are identical afterward; runtime verification passes. All archives, snapshots and failure artifacts are retained. Workstation free space after preparation is 53.75 GiB, above the 20 GiB floor.
- **Exact next action:** finish guarded application warm reboot and cold start using the current 9 GiB/two-CPU XML baseline, stable transaction and exact final-candidate health checks. Remaining G04 interruption/missing-mount/isolated restore, G03 private installer-log hygiene, G05 TPM re-enrollment and G06 separately authorized private live tests stay open.

### Final-candidate application warm reboot and cold start PASS

- [Application boot evidence index](evidence/2026-09-27-hermes-production/qualification-live-application-boot-r1.json) binds the guarded lifecycle, readiness, named health and root boot reports. The current 9 GiB/two-CPU persistent XML matches before each transition; only the qualification VM runs. Warm reboot changes boot ID from `d83a7442...779d15` to `24de6c28...02a722`; subsequent clean shutdown/cold start yields `084890b8...74b649`. No console input is sent during this sequence.
- After each boot, pinned named status and actual application verification PASS for exact candidate `57940397...44295` and receiver `a1edcaad...5671c`. The recovered journal, current pointers, kernel, PCR7, crypttab and selected initramfs identities remain unchanged. Root facts confirm normal running state, preserved recovery slot, no temporary recovery parameters and PCR7/SHA256/no-PIN policy. These are application boot proofs; private passphrase recovery and TPM re-enrollment are not repeated or inferred.
- The first cold-start status read occurred before SSH readiness and failed. Its report is preserved; no boot action was replayed. A separate pinned readiness observation and then full named runtime/root boot checks pass.
- **Exact next action:** revalidate the already-approved empty restore fixture's 8 GiB/two-CPU preview and resource reserve, then cleanly stop qualification before creating the isolated restore VM. Its private installation and independently commissioned backup inputs remain required; the explicitly unconfigured application backup endpoint is never contacted. Current-candidate controlled interruption/missing-mount tests need bounded private root setup, while G03 installer-log hygiene, G05 re-enrollment and G06 private tests remain open.

### Restore fixture created; precise private-input handoff

- [Actual restore creation](evidence/2026-09-27-hermes-production/qualification-restore-created-r1.json) records fresh signed-media verification, corrected `hermesadmin` settings with its dedicated restore commissioning public key, and reviewed preview followed by approved creation. Restore UUID is `dbe191ac-8b57-45da-bece-f1ccea027cec`; current XML SHA256 is `16f664cdb5364ff15e6daab225ff9528fe11f17a6a964845ed3522faecc7166e`. Memory/current memory are 8 GiB with two CPUs; localhost forwarding is `127.0.0.1:22225`. Secure Boot firmware, TPM emulator, new system disk and separate canary are retained.
- Qualification was cleanly stopped only after a fresh exact-candidate status/runtime/root-boot guard. Its 9 GiB XML, existing disk, TPM/NVRAM and recovery artifacts remain preserved. Only restore runs. Workstation free space after creation is 53.85 GiB, above the 20 GiB floor. No private console input or installer log is captured. Creation is not installation, application restoration or backup acceptance.
- **Exact next action — operator private terminal:**

  ```bash
  python3 -B /var/home/aicloudopspecial/code/repos/hermes-fedora-host/vm/hermes-production-fixture.py --role restore --console
  ```

  Follow the canonical [private installation procedure](../HERMES_PRODUCTION_DEPLOYMENT.md#fresh-server-installation). Enter installation secrets privately and use administrator `hermesadmin`. Ctrl+Q detaches without stopping the VM; the Anaconda redraw is Ctrl+b, release, r. Report only a non-secret installation status or error. Do not rerun fixture creation or start qualification while restore runs. After installation cleanly shuts down, verify its canary and disk ownership, commission its own identities and pin its SSH host key from the private console before any SSH connection.
- **Remaining mandatory gates:** G03 private installer-log secret hygiene; G04 final-candidate controlled interruption/missing-mount setup and actual isolated encrypted application backup/restore; G05 TPM re-enrollment; G06 separately authorized exact-candidate provider, Telegram and approval tests. The application Restic endpoint remains explicitly unconfigured and its password absent. External backup access needs separate authorization/private inputs; header-copy verification and local transaction rollback do not satisfy application restore. No physical server contact, production application deployment, general sudo grant, Git delivery or delegation occurs. The full objective remains intact and incomplete.
- **Managed Goal:** the conversation interruption paused its automatic continuation. This turn continued authorized work to the next private prerequisite. Do not mark the Goal complete; after private setup, `/goal resume` resumes its managed continuation.

### Publication and preserved-resource closure at this private prerequisite

- [Check-only publication log](evidence/2026-09-27-hermes-production/qualification-live-runtime-publication-r1.log) records full lint PASS, full-tree secret scan with positive control PASS, exact candidate archive/bootstrap/source and prepared evidence hashes unchanged, 195 local documentation targets/eight Markdown fragments valid, source-aware manifest PASS and exact diff hygiene PASS. Subsequent closure records receive a narrow final documentation/secret/provenance refresh. Executable inputs are unchanged, so the applicable 57 focused/623 canonical Python and 140 ShellSpec passes remain current within repository scope; these tests do not substitute for the live results above.
- [Final resource observation](evidence/2026-09-27-hermes-production/qualification-final-vm-preservation-r1.json) independently confirms restore alone running, qualification cleanly stopped, both approved memory/CPU and persistent XML baselines unchanged, and the stopped qualification canary SHA256 still equal to its original ownership record. Restore installation/canary acceptance remains unverified. All disks, local transaction snapshots, failed states and encrypted recovery artifacts are retained.
- [Current-candidate handoff index](evidence/2026-09-27-hermes-production/qualification-live-current-candidate-handoff-r1.json) binds the actual runtime/failure/rollback/boot/publication indexes and preserved-resource record. Twelve qualification/reproduction helper sources are retained under ignored private `qualification-namespace/live-r1`, indexed by hash; failed observer and premature-read evidence remain immutable. A local [index reader path correction](evidence/2026-09-27-hermes-production/qualification-live-index-reader-correction-r1.json) is retained; corrected verification covers every nested evidence hash. Current candidate stays test-signed and correctly refused for unqualified production use.
- **Exact next action:** the operator opens the already-created restore VM console using the copyable command above and performs private installation; share only a non-secret result. No repeated bootstrap, fixture creation, broader sudo authorization or external backup/provider/Telegram operation is requested. G03–G06 and full preproduction completion remain blocked on their stated private prerequisites; the historical physical commissioning does not authorize application deployment.

### Restore installer shutdown verified; private first boot paused

- The operator supplied non-secret Anaconda shutdown output ending in `Power down`. [Independent stopped-state inspection](evidence/2026-09-27-hermes-production/restore-postinstall-inspected-r1.json) confirms both approved VMs shut off, the exact restore UUID/resources and disk paths, a clean qcow2 with approximately 3.52 GiB allocated, and canary SHA256 `5419b4c0...3fbb0e7` identical to the original creation record. The current persistent XML equals its creation baseline: hard-disk boot, no installer kernel/initrd and an already empty CDROM. No ejection, reinstall, disk recreation or configuration change was needed. Shutdown and allocated storage do not certify the installed OS, account, package set, encrypted mounts or log hygiene.
- [First-boot handoff](evidence/2026-09-27-hermes-production/restore-first-boot-handoff-r1.json) rechecks these guards and the 20 GiB workstation reserve, then starts only restore **paused** from its existing system disk. Qualification stays shut off; restore remains at the authorized 8 GiB/two CPUs. Persistent XML SHA256 remains `16f664cd...7166e`. Workstation free space before the handoff is 50.16 GiB. No guest console is attached by the agent; no private input is collected.
- **Exact next action — operator private terminal:**

  ```bash
  virsh -c qemu:///session --escape '^q' console hermes-production-restore --safe --resume
  ```

  This is a one-time first-boot resume after console attachment. Enter the restore VM's existing LUKS passphrase privately. Wait for login and use administrator `hermesadmin`; Ctrl+Q detaches. Report only a non-secret boot/login status or error. The ordinary fixture console helper does not resume a paused guest. Do not replay creation or start qualification while restore is active.
- **After private boot:** verify the public SSH host identity through this private console before any SSH connection; use the dedicated restore commissioning key with BatchMode/IdentitiesOnly/IdentityAgent=none, strict pinned known-hosts and no forwarding. Then observe its own kernel, machine/LUKS/filesystem/account/package and memory identities under bounded access before preparing commissioning. Do not infer minimum-memory acceptance from 8 GiB XML: runtime preflight uses exposed memory. No restore memory expansion is authorized. If administrator login fails, preserve the installation and use the separately reviewed private verified-media recovery procedure rather than guessing credentials or reinstalling.
- G03–G06 and the full preproduction objective remain incomplete. Qualification runtime/rollback and its earlier canary proofs retain their exact candidate scope; the new restore observations provide no application backup/restore or TPM/provider/Telegram acceptance. Current private prerequisite is first-boot unlock and console-verified access, not another bootstrap authorization.

### Restore normal login prompt reported; console-pinned access pending

- The operator first reported detaching, then supplied the Fedora44 Server normal `hermes-restore login:` banner with kernel `6.19.10-300.fc44.x86_64` on `ttyS0`. [Independent host-side observation](evidence/2026-09-27-hermes-production/restore-login-prompt-observed-r1.json) confirms the exact restore UUID now running, qualification shut off, restore alone active, and unchanged 8 GiB/two-CPU persistent XML. This combines an operator-reported console banner with actual libvirt facts; it does not establish successful administrator login, package/encrypted-mount/memory acceptance, installer-log hygiene or application restoration. No unpinned SSH connection or console capture occurs.
- **Exact next action — private restore console:** enter username `hermesadmin` and the administrator password privately. After login, run `cat /etc/ssh/ssh_host_ed25519_key.pub` and share that public key only; if login fails, share only the non-secret error. The public host key is safe to send and permits a console-verified pin for the dedicated restore commissioning key. If detached, reconnect with the ordinary restore console command; the VM is already running and needs no additional resume/start.
- After the console pin, inspect the guest through BatchMode/IdentitiesOnly/IdentityAgent=none, strict pinned known-hosts and no forwarding. Root-only commissioning/audit still uses bounded private setup; do not generalize the qualification VM's sudo grants or assume an administrator password was set. Preserve this installed restore disk on failure. G03–G06 and the full objective remain incomplete; no backup/provider/Telegram or physical-server operation is authorized by this banner.

### Restore administrator password forgotten; verified-media recovery prepared next

- The operator reports forgetting the restore VM's `hermesadmin` password. No failed-password guessing or credential retrieval is attempted. The existing canonical private [recovery procedure](../HERMES_PRODUCTION_DEPLOYMENT.md#fresh-server-installation) covers setting the installed administrator password from Fedora-verified rescue media after private LUKS unlock. This is account recovery for the already-approved synthetic restore VM, preserving its installed disk and separate canary. No old password/hash is requested or exposed.
- **Approved recovery outcome:** exact restore UUID `dbe191ac-8b57-45da-bece-f1ccea027cec`, 8 GiB/two CPUs, installed disk, canary, TPM/NVRAM and unrelated configuration preserved; operator changes only `hermesadmin`'s password through the private rescue console. Retain baseline XML and failure evidence. Root-only rescue operations and the existing bounded-access preparation do not authorize general passwordless sudo.
- **Exact next action:** verify current restore XML/resources and qualification shutoff, request a graceful ACPI shutdown, recheck the stopped canary and signed Fedora44 DVD, then review a rescue-only `virt-install --reinstall` preview against the exact existing domain. That libvirt launch mode must use only `inst.rescue`, retain both existing disks and allow only the expected readonly DVD/temporary rescue kernel/initrd changes. Stop on drift or shutdown failure; never recreate disks or reinstall the OS. After rescue starts, the operator privately unlocks the existing LUKS device, mounts the installed system and runs the canonical `chroot /mnt/sysroot passwd hermesadmin` inside the guest.
- Current prerequisite is private password reset, followed by console-verified SSH identity and actual installed-system audit. G03–G06 and full preproduction completion remain open. The qualification VM stays shut off; its exact candidate and historical evidence are unchanged.

### Restore password recovery — rescue preview correction and launch guards

- [Graceful shutdown](evidence/2026-09-27-hermes-production/restore-password-recovery-shutdown-r1.json) confirms both approved VMs shut off, exact restore UUID/resources, unchanged baseline XML SHA256 `16f664cd...7166e`, original canary SHA256 `5419b4c0...3fbb0e7` and 50.14 GiB workstation free. No force-off, password reset or backup/provider operation occurred.
- [First preview observer failure](evidence/2026-09-27-hermes-production/restore-password-rescue-preview-failed-r1.json) is retained. The generated kernel path had already been removed by virt-install's documented-in-installed-source `finally` cleanup, including XML-only mode. The corrected observer validates both complete generated XML stages and the temporary path class; it does not claim those ephemeral files were retained or independently hashed.
- Corrected rescue-only preview PASS: retained Fedora44 ISO SHA256 `85837793...cf1f` and Fedora44 signer `36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6` verified. Both XML stages preserve the complete baseline apart from the explicitly permitted readonly ISO source and initial temporary kernel/initrd/console command line/reboot policy. No Kickstart, disk creation or formatting input is supplied. Preview XML and helper remain under `.toolbox/hermes-production-restore/`.
- **Exact next action:** guarded launch of only the already-existing restore VM with the inspected rescue-only arguments; recheck its complete persistent XML, active identity/resources, disk/TPM/NVRAM identities and qualification shutoff. Then hand the operator the private console for rescue Continue/mount, private LUKS unlock and `chroot /mnt/sysroot passwd hermesadmin`. Password reset, root discovery and console-pinned SSH remain NOT_RUN until actually observed/reported.

### Restore password recovery — verified rescue running; private reset pending

- [Corrected preview](evidence/2026-09-27-hermes-production/restore-password-rescue-preview-r2.json) and [actual read-only observation](evidence/2026-09-27-hermes-production/restore-password-rescue-observed-r3.json) PASS for the existing restore UUID, 8 GiB/two CPUs, original disks/serials, UEFI/Secure Boot, TPM/NVRAM, unchanged canary and qualification shutoff. Restore alone is running; workstation free remains 49.89 GiB. Rescue was launched exactly once. Persistent configuration differs only by the readonly signed Fedora DVD source; active boot uses the exact approved rescue kernel/initrd/command line. No password, SSH or backup/provider operation has occurred.
- Preserve the [first post-launch observer failure](evidence/2026-09-27-hermes-production/restore-password-rescue-start-observer-failed-r1.json) and [read-only observer failure](evidence/2026-09-27-hermes-production/restore-password-rescue-observer-failed-r2.json). These concern libvirt's retained baseline `<boot dev="hd">`, generated `tpm0` alias and positive unique active disk-source indices, rather than disk/path/resource drift. All remaining active comparisons were inspected together before the corrected observer passed. Persistent XML comparison remains exact after removing only the known readonly DVD source. No launch was repeated.
- [Handoff index](evidence/2026-09-27-hermes-production/restore-password-recovery-handoff-r1.json) binds six immutable observations/failures and six retained local helpers. The agent has not attached to or captured this rescue console. Rescue-menu discovery, successful private LUKS unlock, mounted-root identity and administrator password reset remain unverified.
- **Exact next action — operator private terminal:**

  ```bash
  virsh -c qemu:///session --escape '^q' console hermes-production-restore --safe
  ```

  Choose the rescue menu's Continue/mount option and enter the existing restore LUKS passphrase privately. At the guest rescue shell, first confirm `cat /mnt/sysroot/etc/hostname` reports `hermes-restore.test`; only then run the canonical `chroot /mnt/sysroot passwd hermesadmin` and enter the new administrator password privately. If the installed system is not mounted or its identity differs, report only the non-secret error and preserve the rescue state. After success, `cat /mnt/sysroot/etc/ssh/ssh_host_ed25519_key.pub` supplies the public host key for the next console-pinned access step; it is safe to share. Ctrl+Q detaches. Never send the new password or LUKS passphrase.
- After the operator confirms the reset and detaches, verify the mounted guest identity/non-secret account result, cleanly unmount and power off rescue, eject only the DVD source, revalidate the original persistent XML and canary, then return to normal private boot. Do not restart or recreate the installed disk, expand memory, enroll TPM or install a general sudo grant as password-recovery shortcuts. G03–G06 and full preproduction acceptance remain incomplete.

- **Recovery handoff publication:** [check log](evidence/2026-09-27-hermes-production/restore-password-recovery-publication-r1.log) records unchanged exact-candidate source/prepared evidence, recovery helper/evidence hash verification, current local documentation targets/fragments, Toolbox Markdown lint, full-tree offline secret scan with positive control, source-aware migration provenance and whitespace PASS. That retained log covers the 778-row state before publication of the log itself and this result line. Final publication closure repeats the affected checks against the complete current working tree in `.toolbox/hermes-production-restore/password-recovery-publication-r2.log`; full runtime tests are reused because candidate source is unchanged. Private password reset remains pending and all mandatory gates retain their stated scope.

### Restore private password reset reported; public identities pinned after detachment

- Operator reports `passwd: password updated successfully`, then explicitly confirms `detached` after all private password prompts finish. The prior private-password prerequisite is resolved as operator evidence. Agent safely attaches without `--force` only after that confirmation; guest UID0, exact approved UUID, installed hostname `hermes-restore.test` and mounted root `/dev/mapper/hermes_system-root` (XFS) are independently observed.
- [Public identity evidence](evidence/2026-09-27-hermes-production/restore-password-reset-public-identities-r1.json) records restore LUKS2 UUID `3f6f7774-6672-40d9-afc7-d1bd03f9baa1`, actual mounted root/var/Hermes/boot/EFI layout and its public Ed25519 SSH host key read from the installed root. A new owner-only pin is retained at `.toolbox/hermes-production-validation/synthetic-stage/restore-known-hosts-r1` for localhost22225. No unpinned SSH connection, password/hash, private key, machine-id or administrator-account metadata is collected.
- [Automatic review boundaries](evidence/2026-09-27-hermes-production/restore-recovery-auto-review-boundaries-r1.json) preserve the pre-confirmation console rejection and the bundled-probe rejection. The first was resolved by explicit private-phase completion/detachment. The second was resolved by removing the machine-id/account metadata reads entirely; narrowed public storage/key checks were approved. Do not mistake the operator password result for an independently observed account-status result.
- **Exact next action:** verify installed public package facts and the password-reset file's SELinux context without reading its content; sync and recursively unmount only the verified `/mnt/sysroot` tree, then gracefully power off rescue. After authoritative shutoff, eject only the known readonly rescue DVD, require exact original persistent XML and unchanged canary, and start the existing restore disk paused for private normal-boot LUKS unlock. Retain all disks/recovery artifacts and the 20 GiB reserve. G03–G06 remain incomplete; installer-log hygiene, TPM/application restore and separately authorized provider/Telegram work are not inferred from this recovery.

- [Rescue package/context facts](evidence/2026-09-27-hermes-production/restore-rescue-public-package-context-r1.json) confirm presence of all 18 queried mandatory installed packages, including Restic and TPM tools. These are the restore installation's actual versions, not an assertion of version parity with qualification. `chroot /mnt/sysroot restorecon /etc/shadow` exits zero after the operator's password reset; its contents are never read. Public console host fingerprint is `SHA256:fxewxdFeEgXZj7iwlzKwTJ0qQ5cUsZSYT9/RQEG+mLE`. Normal-runtime package/preflight, SELinux, memory and Secure Boot gates still require actual normal boot. Guarded unmount/poweroff/ejection and private normal boot are next.

### Restore recovery closed within scope; normal disk boot awaits private unlock

- Guarded guest command required exact restore UUID/hostname/root mount, changed cwd away from the mounted tree, synced, recursively unmounted only `/mnt/sysroot`, emitted `HERMES_RESTORE_CLEAN_UNMOUNT_PASS`, then powered off gracefully. Console process exited and guest reached `Power down`; no force-off/lazy unmount occurred.
- [Stopped-state return preparation](evidence/2026-09-27-hermes-production/restore-normal-after-recovery-prepared-r1.json) confirms both approved VMs shut off, original canary SHA256 `5419b4c0...3fbb0e7`, clean qcow2 at its unchanged virtual size, and the 20 GiB workstation reserve. Ejected only the known readonly `sda` rescue DVD. The complete persistent XML is again byte-identical to original baseline SHA256 `16f664cd...7166e`, preserving 8 GiB/two CPUs, disks, TPM and NVRAM paths.
- [One-time normal-boot handoff](evidence/2026-09-27-hermes-production/restore-normal-after-recovery-handoff-r1.json) starts only the same installed restore disk **paused**. Active XML has normal hard-disk boot, no rescue kernel/initrd/command line and empty CDROM. Qualification remains shut off. No agent console is attached for the private unlock. This is ordinary return from account recovery, not an application restore or TPM qualification result.
- **Exact next action — operator private workstation terminal:**

  ```bash
  virsh -c qemu:///session --escape '^q' console hermes-production-restore --safe --resume
  ```

  Enter the existing **restore LUKS passphrase**, then wait for normal login. Use `hermesadmin` with the **new administrator password** if logging in. Ctrl+Q detaches; report only `booted and detached` or a non-secret error. No Anaconda menu/redraw is needed for this normal boot. Password recovery need not be repeated.
- After actual normal boot, run `.toolbox/hermes-production-restore/hermes-restore-normal-public-audit-r1.py` with the dedicated restore commissioning key. Its pin is bound to the actual installed public host key; BatchMode/IdentitiesOnly/IdentityAgent=none, strict host checking and no forwarding are enforced. The prepared audit reads public OS/kernel/boot/SELinux/Secure Boot/swap/package/mount/capacity facts only; it omits machine-id and account metadata rejected by automatic review, reads no private key/log/credential content, and provides no root grant. It is prepared, NOT_RUN. Inspect actual exposed memory before any application/bootstrap scope decision; no restore RAM expansion is authorized.
- G03 private installer-log hygiene, G04 controlled faults and isolated encrypted application backup/restore, G05 TPM re-enrollment, and G06 separately authorized exact-candidate live tests remain incomplete. Qualification's final candidate `57940397...294295` and current runtime/rollback evidence are unchanged. Production acceptance remains unclaimed.

- **Publication method for this recovery result:** verify unchanged candidate sources/prepared evidence, all new public recovery evidence/helpers and local documentation links/fragments, then run Toolbox Markdown, full-tree offline secret scan, source-aware migration generation/verification and whitespace checks. The retained final log is `.toolbox/hermes-production-restore/normal-after-recovery-publication-r1.log`; no executable candidate source changed, so its current canonical runtime/unit/lint evidence is reused within the original scope.

- [Recovery result index](evidence/2026-09-27-hermes-production/restore-normal-after-recovery-index-r1.json) binds the five new public observations/hand-off receipts and two retained helpers. Automatic-review refusals are retained as historical boundaries, with safe alternatives explicitly recorded. No rejected machine-id/account probe was executed or reproduced indirectly.

- [Current qualification preservation](evidence/2026-09-27-hermes-production/restore-qualification-preservation-r2.json) revalidates the approved **9 GiB** baseline, two CPUs, exact UUID, complete disk/TPM/NVRAM/boot configuration and shutoff. The first exact-byte observer refused one extra trailing LF from `virsh dumpxml`; retained current XML and parsed whole-document comparison prove it is only serialization whitespace. No VM action followed that refusal, no historical 8 GiB baseline was used and qualification's runtime evidence is not invalidated by whitespace.
- **Actual publication:** `.toolbox/hermes-production-restore/normal-after-recovery-publication-r1.log` records source/prepared evidence and both recovery indexes, exact retained candidate archive SHA256, local documentation links/fragments, Markdown lint, full-tree secret scan, source-aware provenance (785 rows) and whitespace PASS. The final closure at `.toolbox/hermes-production-restore/normal-after-recovery-publication-r2.log` repeats affected current-tree checks after preserving this qualification observer result; it retains the same candidate and scope. Private normal boot remains the exact next action above.

### Restore normal boot verified; actual memory and package/service blockers

- Operator reports `booted and detached`. [Actual pinned public audit](evidence/2026-09-27-hermes-production/restore-normal-public-audit-r1.json) authenticates the dedicated commissioning key under the console-derived host pin, strict checking, BatchMode/IdentitiesOnly/IdentityAgent=none and no forwarding. Only restore is running, qualification is shut off, and its full persistent baseline/resource configuration is unchanged. Normal Fedora44 kernel `6.19.10-300.fc44.x86_64`, boot ID `21cf3b59-d295-47b3-8003-0ec0fefffea9`, SELinux Enforcing, SecureBoot enabled, no swap and all five expected encrypted-root/XFS/EFI mount identities are observed. Free `/var` is 83,984,822,272 bytes. This is public boot/storage access evidence, not complete application/installer-log/TPM acceptance.
- [Exact unchanged platform predicate](evidence/2026-09-27-hermes-production/restore-normal-platform-predicate-r1.json) independently evaluates the same `os.sysconf(SC_PHYS_PAGES)*os.sysconf(SC_PAGE_SIZE)` test as `production/preflight.py`: actual 8,244,031,488 bytes (7.68 GiB) is below 8,321,499,136 bytes (7.75 GiB, 8 GiB minus the existing 256 MiB tolerance), deficit 77,467,648 bytes. Result **FAIL minimum-8gib-memory**. No threshold weakening, kernel-reservation change or RAM increase is performed. Full application preflight remains NOT_RUN because its bounded receiver/commissioning is not yet installed.
- [Actual prerequisite binding](evidence/2026-09-27-hermes-production/restore-normal-prerequisite-binding-r1.json) confirms Podman binary 5.8.1, below the unchanged 5.8.4 minimum, expected KVM/AMD family25 and original mcelog vendor-unit SHA256 `78d3ea28...01b056`. The normal system is degraded with only mcelog failed; its own journal classifies unsupported CPU. Raw journal/CPU contents, machine-id and account metadata are neither published nor retained.
- [Reviewable correction preparation](evidence/2026-09-27-hermes-production/restore-prerequisites-memory-prepared-r2.json) and [binding index](evidence/2026-09-27-hermes-production/restore-normal-readiness-index-r1.json) retain a restore-only clone of the previously qualified prerequisite helper, bound to this VM and its root/var UUIDs. Four guard/idempotence tests PASS in Toolbox; launcher shell syntax and refusal without a private terminal PASS. The launcher also requires restore running and qualification shut off before SSH. The public helper is staged exclusively at `/home/hermesadmin/hermes-restore-prerequisites-r1.py`, but root execution is NOT_RUN. It upgrades only Podman/required dependencies from signed Fedora44 repositories, preserves the mcelog vendor unit and adds only the guarded KVM condition. No general passwordless sudo grant, application deployment, TPM enrollment, reboot or backup/provider action is supplied.
- **Prepared private prerequisite command (already within synthetic preparation authority):**

  ```bash
  bash .toolbox/hermes-production-restore/prerequisites-r1/run-private-prerequisites-r2.sh
  ```

  Run from the repository root in the operator's private terminal; enter the new administrator password only at sudo. Share only its final non-secret status/error. This package/service step can run independently of the RAM decision; it does not fix or waive the memory predicate.
- **Exact next authorization request:** increase only `hermes-production-restore` from the specifically approved 8 GiB to **9 GiB**, retaining two CPUs, exact UUID, system/canary disks, TPM/NVRAM and all other settings. `.toolbox/hermes-production-restore/prerequisites-r1/memory-9gib-proposal-r1.xml` SHA256 `596355a5...1bfba` changes only `memory` and `currentMemory` from 8,388,608 to 9,437,184 KiB. The complete remaining XML structure is identical. Approval is REQUIRED and has NOT been received; the VM remains running at 8 GiB. After approval, use graceful shutdown, stopped-state canary/config guards, only the proposed memory definition, paused private normal boot and actual exposed-memory revalidation. Preserve artifacts and the 20 GiB workstation reserve. Do not infer restore approval from qualification's separate 9 GiB approval.
- Canonical candidate and its receiver are unchanged; source/payload identity and historical runtime evidence retain their tested scope. G03 private installer-log hygiene, G04 current controlled-fault/encrypted application restore, G05 re-enrollment and G06 separately authorized exact-candidate live tests remain incomplete. The native goal controller is still PAUSED; this turn makes manual resumed-task progress and does not claim goal completion or silently recreate/resume that controller.
- **Publication method:** final current-tree index/source/helper/doc-link checks, Toolbox Markdown lint, full-tree offline secret scan, source-aware migration generation/verification and whitespace checks are retained in `.toolbox/hermes-production-restore/normal-readiness-publication-r1.log`. Current canonical source tests are reused because executable candidate inputs have not changed.

- **Actual readiness publication PASS:** retained `normal-readiness-publication-r1.log` SHA256 `013f57bfc571c4e10643824cf783c7d01c4b9b6e0988bb9cee2f54adaa332ebd` records unchanged candidate/preflight inputs, all recovery/readiness evidence/helper hashes, exact archive, current local links/fragments, Markdown lint, full-tree secret scan (792 files), source-aware provenance (791 rows) and whitespace checks. The final closure log `.toolbox/hermes-production-restore/normal-readiness-publication-r2.log` repeats affected checks after recording this actual result and reconciling current gate rows. No package/service/root operation or memory increase occurred; the pending approval/private handoff remains unchanged.

## Restore private prerequisites — actual postconditions (2026-09-29 23:25 UTC)

- **Method/expected result:** preserve the operator's public prerequisite receipt, then use strict console-pinned, key-only commissioning SSH and the exact 8 GiB/two-CPU XML with qualification shut off. Observe Podman >=5.8.4, no failed units, only the reviewed KVM mcelog condition, preserved vendor unit, installed filesystem identities, SELinux/Secure Boot and swap contract. Execute the unchanged memory predicate using actual guest `sysconf` values. This is public prerequisite evidence; the full application preflight and private commissioning are not inferred.
- [Operator result](evidence/2026-09-27-hermes-production/restore-prerequisites-operator-result-r1.json) reports the bounded private helper completed at 23:21:25 UTC: Podman 5.8.1 → 5.8.7, unsupported KVM CPU condition installed and no failed units. It reports application deployment, TPM enrollment, reboot and production changes NOT_RUN. The independently observed state is recorded separately.
- [Public observation R3](evidence/2026-09-27-hermes-production/restore-post-prerequisites-public-audit-r3.json) at 23:24:57 UTC independently verifies Podman binary and RPM 5.8.7, system state `running`, zero failed units and mcelog `inactive/dead`, `ConditionResult=no`, `Result=success`. The exact root-owned 0644 drop-in SHA256 is `7f7cb7f0f5149acf6e2d04ae5b95a29d82ce872b31b7ca17f2f212e6d71312ee`; vendor unit SHA256 remains `78d3ea288eebc5583a1ad0ea169ba1f41b20b6db89508b1f501ad61c6d01b056`. Boot ID `21cf3b59-d295-47b3-8003-0ec0fefffea9`, the five mounted filesystem facts, enforcing SELinux, enabled Secure Boot, disabled swap and 8 GiB XML remain unchanged. No root grant, private logs, account metadata, raw machine ID or credential contents were read.
- [Preserved observer failure R2](evidence/2026-09-27-hermes-production/restore-post-prerequisites-observer-failed-r2.json) records an audit-helper quoting error before public collection; it made no guest changes. The corrected R3 validates both host and transmitted Python syntax before running. Failed helper/log bytes remain retained.
- [Actual result](evidence/2026-09-27-hermes-production/restore-post-prerequisites-result-r1.json) and [binding index](evidence/2026-09-27-hermes-production/restore-post-prerequisites-index-r1.json) bind the public/failed observations, operator receipt, exact helpers/logs, unchanged preflight source and both memory XMLs. Package/service correction is PASS within this scope. The older below-minimum Podman/degraded-service observations are historical and superseded by R3; their immutable files remain unchanged. No qualified-application evidence is invalidated by this separate restore-VM prerequisite correction.
- **Remaining actual failure:** exposed RAM is 8,244,031,488 bytes versus the unchanged 8,321,499,136-byte minimum, deficit 77,467,648 bytes. The full application preflight is NOT_RUN because the restore receiver has not been privately commissioned. No new commissioning attestation is manufactured from this public audit; future restore boot/package bindings must use its current package identities.
- **Exact next action:** obtain the pending explicit restore-only 8 → 9 GiB approval for the already prepared `memory-9gib-proposal-r1.xml`, SHA256 `596355a5a546025f5990ee88336a98cf015795f1785051a8b3a9a7eba981bfba`. Only then perform guarded graceful shutdown, stopped canary/config preservation, memory-only definition, paused private normal boot and exposed-memory revalidation. The operator's successful prerequisite run does not authorize this RAM increase. Do not rerun the completed package/service step or the password-recovery phase.
- **Remaining gates:** G03 private installer-log hygiene; G04 current controlled interruption/missing mount and isolated encrypted application backup/restore/startup; G05 TPM re-enrollment; G06 exact-candidate provider/Telegram/approval tests with separately authorized private inputs. The unconfigured backup endpoint remains uncontacted. The physical target remains untouched; no Git delivery or delegation occurred. Full objective remains open, with no production acceptance claim.
- **Publication method:** revalidate exact candidate/archive, source/evidence/helper bindings and local documentation targets/fragments; run Toolbox Markdown lint, full-tree secret scan, source-aware manifest generation/verification and whitespace checks. Retain new exclusive `.toolbox/hermes-production-restore/post-prerequisites-publication-r1.log` and a final closure log after reconciling current rows. Unchanged candidate executable tests are reused within their existing scope.

- **Publication attempt R1:** exact candidate/archive, all evidence/helper bindings and local links PASS; Markdown lint rejected one newly added extra blank line (MD012). The failed `post-prerequisites-publication-r1.log` is preserved. Only that new separator was corrected; R2 reruns the affected publication checks, with R3 reserved for final closure.

- **Actual publication R2 PASS:** `.toolbox/hermes-production-restore/post-prerequisites-publication-r2.log` SHA256 `db725f05fe95e17393517d876508dc7e40f2afbfcf29f84dacbe969a79f6a5ca` retains current source/evidence/helper/archive bindings, local links/fragments, Markdown lint, full-tree secret scan with positive control (797 files), source-aware provenance (796 rows) and whitespace checks. The final R3 closure repeats affected checks after reconciling current rows. G03–G06 remain incomplete; the next action remains the explicit restore-only RAM approval, with no goal completion or production acceptance.

## Restore memory increase — approved application (2026-09-29)

- **Approval:** the user replied “yes” to the explicit restore-only 8 → 9 GiB increase and restart request. This supersedes the earlier pending RAM approval only; retain two CPUs, the exact restore UUID and all other VM settings, disks and recovery artifacts. Private unlock remains an operator phase. No broader sudo, application/provider/Telegram/backup or physical-target authorization follows.
- **Method/expected result:** revalidate pinned evidence/proposal, exact current XML and one-VM rule; gracefully shut down using ACPI, with no forced power-off fallback. While both guests are stopped, verify canary and non-repairing QCOW2 integrity; define only the approved memory XML and compare its full structure; start only restore paused for a private normal boot. Preserve a new 9 GiB baseline and the original 8 GiB evidence. After private unlock and detachment, inspect actual exposed RAM via pinned public SSH and require the unchanged minimum predicate to PASS.
- **Exact next action:** run the guarded preview and memory application. Stop on identity/config/disk/space drift; preserve any failure evidence. G03–G06 and full preproduction acceptance remain open.

- **Actual application PASS at 23:31:33 UTC:** [preview](evidence/2026-09-27-hermes-production/restore-memory-9gib-preview-r1.json), [stopped preservation/integrity](evidence/2026-09-27-hermes-production/restore-memory-9gib-prepared-r1.json), [paused handoff](evidence/2026-09-27-hermes-production/restore-memory-9gib-handoff-r1.json) and [binding index](evidence/2026-09-27-hermes-production/restore-memory-9gib-index-r1.json) retain exact restore UUID `dbe191ac-8b57-45da-bece-f1ccea027cec`. ACPI shutdown completed without force-off; QCOW2 check passed, virtual size and disk inode were preserved, unrelated-disk SHA256 remains `5419b4c0655822bb292a539bed080d6b0c97dc8710a9a7bb26c58d3e33fbb0e7`, and about 50 GiB workstation space remains. The complete qualification 9 GiB XML structure was revalidated unchanged while that guest stayed shut off.
- **Current restore lifecycle baseline:** `.toolbox/hermes-production-restore/prerequisites-r1/memory-9gib-applied-r1.xml`, SHA256 `596355a5a546025f5990ee88336a98cf015795f1785051a8b3a9a7eba981bfba`. It exactly matches the approved proposal; only `memory`/`currentMemory` changed to 9,437,184 KiB. Two CPUs, disk sources/serials, TPM, NVRAM and remaining XML are preserved. Active paused XML SHA256 is `4e1ed324421f0ab0cbb637d43b7e3d7e9e164216965eea99493374458bf05571`. Use this new baseline for future restore lifecycle guards; preserve all historical 8 GiB XMLs without using them as current guards.
- [Idempotent rerun](evidence/2026-09-27-hermes-production/restore-memory-9gib-rerun-r1.json) PASS: retained handoff and current resource/configuration guards produced `ALREADY_APPLIED_NO_LIFECYCLE_REPLAY`. No duplicate shutdown, define, start or console attachment occurred. Both helper syntax and real preview guards passed. A new pinned public audit is prepared at `.toolbox/hermes-production-restore/prerequisites-r1/public-memory-9gib-audit-r1.py`; it uses the current 9 GiB baseline and must run only after private normal boot is available.
- **Evidence freshness:** the former 8 GiB RAM failure and its public boot observation are historical for the changed restore VM; actual 9 GiB guest exposure, boot ID, security/mount/service state and full application preflight remain NOT_RUN at this handoff. The approved XML result does not substitute for that live check. The final candidate executable/archive and qualification guest evidence are unchanged within their retained scopes.
- **Exact next private action:** resume the already paused restore VM and unlock its existing encrypted disk in the operator's private terminal:

  ```bash
  virsh -c qemu:///session --escape '^q' console hermes-production-restore --safe --resume
  ```

  Once the Fedora login prompt appears, press Ctrl+Q to detach; no login or password reset is required for this handoff. Report only “booted and detached” after all private prompts are finished. Do not send any password/passphrase. The agent has not attached or captured the private console. After that result, run the prepared pinned public audit and validate actual exposed RAM and boot facts against the new baseline.
- **Publication method:** verify preserved candidate/archive and old/new evidence/helper/9 GiB baseline hashes, local links/fragments, Toolbox Markdown lint, full-tree secret scan, source-aware manifest generation/verification and whitespace checks; retain exclusive `.toolbox/hermes-production-restore/memory-9gib-publication-r1.log` and final closure log. G03–G06 remain open; TPM, application deployment, backup/provider/Telegram/physical operations and Git delivery were not performed by this memory step.

- **Actual memory publication R1 PASS:** `.toolbox/hermes-production-restore/memory-9gib-publication-r1.log`, SHA256 `590c201aad29b66fbd4e8e46174a02c2ab1e037c263cb460fef4c0775a5a7a65`, verifies preserved candidate/source/archive, old/new evidence/helper/baseline bindings and local targets/fragments; Toolbox Markdown lint, full-tree secret scan with positive control (803 files), source-aware provenance (802 rows) and whitespace checks PASS. Final closure is retained in `memory-9gib-publication-r2.log` after these current row/result updates. No live guest RAM or boot PASS is inferred; private unlock remains the exact next action and G03–G06 stay open.

## Restore 9 GiB normal boot — independently verified (2026-09-29 23:37 UTC)

- **Operator report:** “rebooted and detached”. [Pinned public audit](evidence/2026-09-27-hermes-production/restore-memory-9gib-public-audit-r1.json), [actual result](evidence/2026-09-27-hermes-production/restore-memory-9gib-live-result-r1.json) and [binding index](evidence/2026-09-27-hermes-production/restore-memory-9gib-live-index-r1.json) independently verify actual normal boot and the unchanged memory predicate. Qualification remains shut off; restore alone is running with the exact current 9 GiB/two-CPU XML.
- **Actual PASS:** boot ID `f5fad6ba-4a4a-4556-b933-2dbac98469d0` is new; kernel remains `6.19.10-300.fc44.x86_64`. Guest RAM is 9,288,417,280 bytes versus the 8,321,499,136-byte minimum. The five mount identities, package list/Podman binary 5.8.7, enforcing SELinux, enabled Secure Boot, absent swap, original mcelog vendor unit and bounded KVM condition are preserved; system state is `running` with no failed units. Free `/var` is 83,831,140,352 bytes. No application/TPM/restore acceptance is inferred from public facts.
- **Exact next action:** prepare a bounded, private installer-log secret-hygiene check for the current restore identity/boot. It must inspect only retained Anaconda logs and expected saved-Kickstart paths, keep any private comparison input solely in memory/stdin, require actual private operator review, and publish only a sanitized receipt. No logs or secrets are copied to the workstation/artifacts; no general passwordless sudo grant is installed. Root operation is NOT_RUN until the operator runs the reviewed private launcher.
- G03 remains open until actual private hygiene evidence exists for the required installed fixtures. G04 restore/private fault setup, G05 re-enrollment and G06 separately authorized private live tests remain open. The explicitly unconfigured application backup endpoint remains uncontacted; all historical evidence and dirty work remain preserved.

- **Private hygiene preparation PASS within synthetic scope:** [prepared/staged record](evidence/2026-09-27-hermes-production/restore-installer-hygiene-prepared-r1.json) binds the current restore UUID/boot/9 GiB XML, all source/test/launcher/staging hashes and the actual public boot evidence. Nine focused Toolbox tests PASS; Python/transmitted/shell syntax and private-terminal refusal PASS. Root ownership/commands and private review were mocked in tests; this does not close G03. `less` is available in the real restore VM. Its installed manual confirms `LESSSECURE=1` disables shell/editor/history/logfile and other unsafe features; the pager receives a fixed environment without `LESSSECURE_ALLOW` or preprocessors.
- **Bounded root phase:** the staged public helper is `/home/hermesadmin/hermes-restore-private-installer-hygiene-r1.py`, SHA256 `46df3a07be7e613de77adc1cef7559a8f50a0977a6d306d3983121f109aec31a`, mode0600 and commissioning-user owned. The private launcher verifies its exact kind/owner/mode/link/hash before executing through operator-entered sudo. It binds DMI VM UUID, current boot, mounted UUIDs and LUKS UUID; inspects saved-Kickstart presence and only retained Anaconda logs; refuses unsafe/binary/oversized/changed paths. It compares the actual recovery passphrase solely in memory/stdin, first proving it with read-only `cryptsetup --test-passphrase`; neither that value nor its hash is published. The private pager requires operator confirmation after ALL logs are reviewed. Only after an unchanged log-set recheck does it create root-owned public `/var/lib/hermes-production-restore-public/installer-hygiene-r1.json` with sanitized statuses and log-set binding. Existing logs are never copied to the workstation, modified or deleted. An unchanged successful receipt is returned on rerun without repeating private input/review.
- **Exact next operator command**, from the repository root in a private terminal:

  ```bash
  bash .toolbox/hermes-production-restore/installer-hygiene-r1/run-private-installer-hygiene.sh
  ```

  Enter sudo and the existing restore LUKS recovery passphrase privately. Review every pager file using `:n` for the next file and `q` to exit; type `reviewed` only after the full private review found no secrets. Share only the final non-secret status/error. No agent console is attached, no general passwordless sudo is installed, and no application, TPM enrollment, reboot or backup/provider operation is included. No additional operational authorization is requested for this already approved fixture gate; its missing prerequisite is actual private input/review. Qualification installer hygiene still needs its own separately bound observation while only that VM runs.
- **Publication method:** revalidate exact candidate/archive, preserved and new source/evidence/helper/live-RAM bindings, local links/fragments and current lifecycle baseline; run Toolbox Markdown lint, full-tree secret scan, source-aware manifest generation/verification and whitespace checks. Retain exclusive `.toolbox/hermes-production-restore/live-ram-hygiene-publication-r1.log` and final closure log. Full G03–G06 remain open; no production acceptance follows from this preparation.

- **Actual publication R1 PASS:** `.toolbox/hermes-production-restore/live-ram-hygiene-publication-r1.log`, SHA256 `a07174feae65c112c9ec3c4aab7a7eabbd41acb1115f140d0c564a33ccede13c`, verifies preserved candidate/source/archive and all historical/new memory/live-RAM/private-hygiene bindings, current baseline and local links/fragments. Toolbox Markdown lint, full-tree secret scan with positive control (807 files), source-aware provenance (806 rows) and whitespace checks PASS. Final closure is retained in `live-ram-hygiene-publication-r2.log` after current gate/result reconciliation. The exact next action is the staged private installer-hygiene launcher; actual guest root execution and G03 hygiene remain NOT_RUN, with full G03–G06 still open.

### Managed goal resumed; private receipt absent and current fault helper prepared

- **Managed goal:** the native controller is now observed ACTIVE; earlier PAUSED entries remain historical. The full objective stays incomplete. Current executable/candidate/receiver/source/evidence identities are unchanged; no goal completion is recorded.
- **Fresh public blocker:** [two pinned checks](evidence/2026-09-27-hermes-production/restore-installer-hygiene-receipt-status-r1.json) retain `INSTALLER_HYGIENE_REPORT_ABSENT`, latest at 2026-09-30T00:10:20.240060+00:00. Restore remains on boot `f5fad6ba-4a4a-4556-b933-2dbac98469d0` with current approved 9 GiB XML; qualification stays shut off. The public reader validates fixed identity/source/schema/root-file metadata before publishing any receipt values. It reads no private installer logs or input. G03 remains BLOCKED on the already staged private review; no repeat password reset, package update or memory restart is needed.
- **Independent G04 preparation:** [locally validated watcher](evidence/2026-09-27-hermes-production/qualification-interruption-writer-prepared-r1.json) uses the existing authenticated marker-only C fixture with final candidate A as previous. Cached images skip OCI import, so the future interruption targets the actual supervised stopped-state snapshot tar writer. Eleven focused Toolbox tests PASS, including real candidate subreaper/flock retention across fixture dispatcher SIGKILL, fixture writer SIGSTOP/resumption and normal guard drainage. VM/root/process matching are synthetic in those tests. Actual host guard refuses today's shut-off qualification before guest contact; the watcher refuses a non-private terminal before privileged inspection. No guest staging, launcher, signals or application operation was performed.
- **Future bounded method:** after the restore private phase ends and qualification alone is running, first bind a new private launcher/staging step to its actual boot, complete current 9 GiB XML, pin and actual preflight/runtime. The watcher checks exact receiver/source/configuration/current A/prior journal/lease, tar executable/open output and inherited lock descriptor. It pauses only that writer, rechecks identities, kills only the dispatcher through a PID handle, holds the writer for 60 seconds for actual named `operation-busy` proof, then resumes it in cleanup and lets the guard drain. Named deployment of exact A must recover the stopped journal to `aborted`, return `UNCHANGED`, verify actual runtime and preserve a subsequent rerun. Retain incomplete snapshot output and every failure. Never signal the guard, replace/delete the lock or clear a journal. Missed/mismatched targets refuse; a finished marker upgrade needs independent named rollback before another separately prepared attempt. No new sudo grant is introduced. These preparation tests do not close G04.
- **Exact next action:** the operator runs the already staged restore hygiene command privately and shares only its non-secret result. The command is unchanged:

```bash
bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-restore/installer-hygiene-r1/run-private-installer-hygiene.sh
```

- **Remaining mandatory gates:** G03 private installer-log hygiene; G04 current live interruption/missing-mount and isolated encrypted application backup/restore/startup; G05 TPM re-enrollment; G06 separately authorized exact-candidate provider/Telegram/approval tests and protected inputs. The unconfigured application backup endpoint remains uncontacted. Disks/recovery artifacts and dirty work remain retained; no physical target contact, provider/Telegram/external backup, reboot, Git delivery or delegation occurs in this resumption.
- **Publication method:** revalidate unchanged candidate/source/archive, historical/current RAM and private-hygiene bindings plus the new public-receipt and watcher helper/result hashes; validate links/fragments and Markdown; run full-tree secret scan, source-aware manifest generation/verification and whitespace checks. Retain exclusive `private-blocker-preparation-publication-r1.log`, then reconcile current rows and retain the final closure log.

- **Actual blocker/preparation publication R1 PASS:** `.toolbox/hermes-production-restore/private-blocker-preparation-publication-r1.log`, SHA256 `03ccbd2157005108a9ed4ae477f7bf8bdc79e88c573ab21a1eabe7e5ecc396ba`, verifies unchanged candidate/source/archive, retained recovery/RAM/hygiene inputs, both public-receipt observations, all new watcher helpers/results, marker archive, current XML baselines and local links/fragments. Toolbox Markdown lint, full-tree secret scan with positive control (809 files), source-aware provenance (808 rows) and whitespace checks PASS. Final closure is retained in `private-blocker-preparation-publication-r2.log` after current row reconciliation. This does not execute the private review or live interruption, close G03–G06 or claim production acceptance.

### Three-turn private-input blocked audit

- [Fresh blocked audit](evidence/2026-09-27-hermes-production/preproduction-private-input-blocked-audit-r1.json) classifies the prior continuation as concrete progress (tested watcher and authoritative evidence), then revalidates the same private prerequisite. The original restore reboot/resumption, first automatic continuation and this second automatic continuation all leave actual private installer review missing. Latest pinned check at 2026-09-30T00:15:08.916573+00:00 still reports `INSTALLER_HYGIENE_REPORT_ABSENT` on unchanged restore boot `f5fad6ba-4a4a-4556-b933-2dbac98469d0`. Complete current 9 GiB XML/pin/one-VM/reserve guards PASS; restore is running and qualification shut off. No private log/input is inspected or live process stopped. No confirmed live process/session handle supports a verified wait; operator-private process state remains unknown.
- **Impasse:** all current source/publication checks and material local fault-watcher preparation are finished. The next mandatory observations require operator-private review/commissioning/recovery input. Do not switch VMs while the restore private phase is pending. G04 requires actual controlled faults and isolated encrypted application restore; G05 re-enrollment and G06 separately authorized provider/Telegram/approval inputs remain unmet. The explicitly unconfigured backup endpoint/password cannot be used. Further status restatements or local mocks cannot close these gates.
- **Goal transition decision:** the same blocker now meets the three-consecutive-turn audit threshold. After validating this retained handoff, set the native goal to BLOCKED, never COMPLETE. Keep every mandatory gate and the original outcome intact. Earlier ACTIVE/PAUSED observations remain historical; the transition tool result is the authoritative native status. No extra authorization request is needed for the already staged private review.
- **Exact next action:** unchanged private restore installer-log review from the copyable command in the preceding handoff. Share only the final non-secret result; never the sudo/LUKS value or raw logs. After its validated receipt, resume the same goal and continue actual qualification. Preserve both VM disks, recovery artifacts, writer guard/lock/journal, dirty work and immutable evidence. No deployment, enrollment, reboot, backup/provider/Telegram, physical-server, Git or delegation operation is performed by this audit.
- **Publication before transition:** verify unchanged candidate/source/archive and all prior/new source/evidence/receipt/watcher/RAM bindings, local links and Markdown; run the full-tree secret scan, source-aware manifest generation/verification and whitespace checks. Retain exclusive `.toolbox/hermes-production-restore/private-input-blocked-audit-publication-r1.log`. G03–G06 and production acceptance remain open.

### User unblock: native goal active and private review job running

- **Actual resumption:** the user said “unblock it”; after initial status remained BLOCKED, the native controller is now independently observed ACTIVE. This starts a fresh resumed audit. The full objective and all authorization boundaries remain intact; no tool-driven replacement goal, completion, broader sudo grant or new operational approval is created.
- [Private-terminal handoff](evidence/2026-09-27-hermes-production/restore-installer-hygiene-private-terminal-r2.json) binds the unchanged staged helper/launcher and all new public GUI-control sources/metadata. A fresh pinned receipt check still reported absent before launch. The first separate terminal/wrapper handles ended without completion metadata; fixed UID/PID/comm-only root python3/less inspection found no matching running process. Its cause is unknown and R1 artifacts are retained. The R2 retry uses a persistent user-session service `hermes-restore-installer-review-r2.service`, a built-in separate Konsole profile and null service streams. Two actual observations confirm service MainPID `187668` and the same wrapper PID `187748`/start identity live, with no completion result yet. No further launch is permitted while this handle remains live.
- **Privacy and scope:** passwords/passphrases and all pager content stay directly on the user-only TTY. The agent neither reads the window/PTY nor captures its streams, process arguments/environment or private logs. Only specific process/service metadata and numeric completion are published locally. Both new wrappers actually refuse non-private stdin/out/error before guest contact. The unchanged root helper performs only the already-approved private installation/log/recovery comparison and sanitized receipt publication; application deployment, TPM enrollment, reboot, external backup/provider/Telegram, physical-host, Git and delegation operations remain NOT_RUN.
- **Verified wait / exact next action:** the operator finishes private sudo and the existing restore LUKS recovery input in that window, reviews every file (`:n`, then `q`) and types `reviewed` only if all files are clean. Poll the same registered live service/wrapper handle; observation timeout is not terminal and must not cause a relaunch. After sanitized numeric completion, independently validate the fixed root-owned public receipt against boot `f5fad6ba-4a4a-4556-b933-2dbac98469d0`, VM/LUKS/source/schema identities and actual outcomes. Do not infer hygiene PASS from SSH, window availability or exit code. A failure requires only its non-secret final status/error, never raw logs or credentials.
- **Remaining gates:** G03 restore receipt and qualification private hygiene; G04 actual current controlled faults and isolated encrypted application restore/startup; G05 re-enrollment; G06 separately authorized private exact-candidate provider/Telegram/approval inputs. Keep qualification shut off and retain both approved 9 GiB XML baselines, disks, recovery artifacts and unrelated dirty work while this private phase is live.
- **Affected publication method:** verify unchanged candidate/archive and prior/new source/evidence/private receipt/GUI-job bindings, local links/fragments and Markdown; run full-tree secret scan, source-aware manifest generation/verification and whitespace checks. Retain exclusive `.toolbox/hermes-production-restore/private-review-live-publication-r1.log`. This validates the handoff; it does not close the live/private gates.

### Private command terminal; native goal stays active pending safe diagnosis

- [Authoritative ended-command record](evidence/2026-09-27-hermes-production/restore-installer-hygiene-private-command-ended-r1.json) binds the sanitized completion file (`PRIVATE_COMMAND_ENDED`, exit 1), actual R3 service/wrapper observation and independent pinned R5 receipt query. At 2026-09-30T01:50:42.299596+00:00, `INSTALLER_HYGIENE_REPORT_ABSENT` still holds on unchanged restore boot. Root-helper success or its failure reason cannot be inferred from this exit code. No private output/log/credential was collected.
- The service and wrapper remain alive only for the private final result and “Press Enter to close” prompt. The review command itself is terminal; that open window is not a live review job and must not be treated as a verified wait. Do not restart solely because a receipt is absent or the command failed. Keep this attempt and all earlier artifacts intact.
- **Exact next action:** obtain only the final non-secret status/error from the existing Konsole window, inspect its demonstrated cause and prepare a bounded correction/retry if needed. The async question asks only that safe result, never password/passphrase/log text. No repeated authorization or general passwordless sudo is requested. The user unblock reactivated the native goal; this is the first turn of the resumed blocked audit, so do not mark that goal blocked again prematurely or complete it. G03–G06 and the full objective remain open.
- **Affected closure checks:** verify unchanged exact-candidate/archive and retained/new source/evidence/completion/public-receipt bindings, local links, Markdown, full-tree secret scan, source-aware provenance and whitespace. Retain exclusive `.toolbox/hermes-production-restore/private-review-ended-publication-r1.log`. Both 9 GiB VM baselines/disks/recovery artifacts and dirty work are preserved; qualification stays shut off and no application/enrollment/reboot/backup/provider/Telegram/physical/Git/delegation operation occurs.

- **First resumed automatic continuation:** [fresh private-diagnostic recheck](evidence/2026-09-27-hermes-production/restore-private-diagnostic-recheck-r1.json) at 2026-09-30T01:58:53.885385+00:00 confirms the same absent receipt, unchanged restore boot/current 9 GiB guards and qualification shut off. The prior turn made concrete progress through the actual private job attempt; this turn makes no mandatory-gate progress because its final non-secret error is still missing. The command remains authoritatively ended with exit 1, so the open window is not a verified wait. This is resumed goal turn two: leave the native goal ACTIVE, retain the pending diagnostic question and do not replay operations or broaden privileges. The exact next action and G03–G06 remain unchanged. Affected documentation/provenance checks are retained in `.toolbox/hermes-production-restore/private-diagnostic-recheck-r1.log`.

- **Second resumed automatic continuation / native goal BLOCKED:** [fresh three-turn diagnostic audit](evidence/2026-09-27-hermes-production/restore-private-diagnostic-blocked-audit-r1.json) records `INSTALLER_HYGIENE_REPORT_ABSENT` at 2026-09-30T02:04:48.362883+00:00 on unchanged restore boot. Current 9 GiB identity/pin/one-VM/reserve guards PASS, with qualification shut off. A specific service/wrapper observation still finds the GUI alive, but the review command's authoritative result remains exit 1; this is not a verified wait. The previous and current automatic turns make no gate progress, and the same unmet private diagnostic prerequisite has now persisted for three resumed turns. `update_goal` actually returned `blocked`; the full objective remains incomplete. Exact next action: obtain only the final non-secret status/error from the existing private terminal and diagnose before any retry. G03–G06 remain open; no private streams/logs/secrets are read and no operational replay occurs. Preserve the failed attempt, both VM disks/recovery artifacts and dirty work. Affected Markdown, secret-scan, provenance and whitespace checks are retained in `.toolbox/hermes-production-restore/private-diagnostic-blocked-audit-r1.log`.

### Private review usability correction — preparation

- The operator reports that the full saved installer-log pager is extremely long. The earlier private error is no longer the only known state: the operator's new direct attempt reached the log viewer, but no completed hygiene receipt is yet verified. The operator is asked to exit with `q` and answer `cancel`, without falsely attesting `reviewed`; wait for confirmation before any guest staging or new private attempt.
- Prepare a private whole-log diagnostic screen using the installed offline Betterleaks scanner, the unchanged VM/boot/storage guards and existing in-memory recovery-value comparison. Keep every retained log in scope, verify a synthetic positive control for each scanned input, disable provider validation and isolate the scanner network. Retain only fixed classifications/counts and source/log-set identities publicly; raw scanner output and any flagged excerpts remain in guest memory/private TTY only. Preserve earlier helpers/evidence and logs.
- This diagnostic does not replace the full-review attestation, invent a no-secrets guarantee or close G03. Report automated screening and any targeted private findings distinctly; use the result to make the remaining private review concrete. Candidate executable inputs and other gates are unchanged. Expected preparation checks: real offline scanner controls/negative fixtures, privacy/error/coverage/rerun guards and affected documentation/secret/provenance checks. Guest execution remains NOT_RUN until the current private session is stopped and the prepared replacement is staged and validated.

- **Prepared and staged shorter diagnostic:** [preparation evidence](evidence/2026-09-27-hermes-production/restore-installer-screening-prepared-r1.json) binds the helper, existing offline Betterleaks 1.1.2 executable, exact scanner configuration, launcher, 15 focused tests, staging metadata and strict public-report reader. Actual local scanner controls cover clean/empty inputs, assignments despite inline allow comments, and secrets at the start/middle/end of a larger synthetic input. Guest sudo/network namespace/scanning are still NOT_RUN. Current 9 GiB identity/pin/one-VM/reserve guards PASS; both prior hygiene and new screening reports remain absent. Public mode-0600 helper/scanner inputs were staged only after the operator confirmed `stopped`; no private log or terminal input was inspected.
- **Method and limits:** retain all saved logs and scan every input privately with an appended in-memory positive control, the existing exact recovery-value comparisons and isolated scanner networking. Only fixed classifications/counts/source and log-set identities may be published. Display at most 20 finding locations privately; do not claim that displayed locations cover all findings or that a clear automated result is a full manual review. G03 remains OPEN in every successful diagnostic report. Earlier helpers/receipts remain preserved; the candidate itself is unchanged. The first public-config quoting issue and a synthetic directory-mode test issue were corrected before the retained 15-test PASS and before staging.
- **Exact next action:** run `bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-restore/installer-screening-r1/run-private-screening.sh` in the private workstation terminal, enter sudo and the existing restore recovery value privately, and share only final status/counts. Independently validate its root-owned public report with the prepared bounded reader before using the result. This launches no pager and does not deploy, enroll TPM, reboot or call backup/provider/Telegram services. Keep G03–G06 and the original objective intact. Affected publication checks are retained in `.toolbox/hermes-production-restore/installer-screening-r1/publication-r1.log`.

### Actual private screening and bounded finding review

- [Independently validated live diagnostic](evidence/2026-09-27-hermes-production/restore-installer-screening-live-r1.json) confirms 12 retained files, 6,980,807 bytes, 12 per-input positive controls and 25 potential finding locations on unchanged restore boot. The frozen private helper completed the read-only recovery test, known-value comparison and actual network-isolated scanner before publishing this receipt. It is not a manual hygiene PASS. No raw private logs or scanner contents were collected by the agent; the first 20 locations pasted by the operator do not cover the other five.
- Prepare a private viewer that reproduces every finding against the same boot, log-set and pinned scanner/source/configuration identities, then shows all 25 finding locations (byte-identical excerpts may be grouped only if every location stays covered). Reuse the validated prior known-recovery comparison only while the exact log-set binding still matches; do not ask for that recovery secret again. Require an explicit private classification for every group, preserve logs, and publish only fixed outcome/count fields. A possible secret or uncertainty blocks clearance. Targeted review remains distinct from a full manual review and G03 remains OPEN.
- Preparation acceptance: wrong identity/log drift/count drift/non-private TTY rejection; complete last-five and duplicate-location coverage; safe terminal rendering; explicit classification/stop handling; no-op matching-report rerun; synthetic and real scanner checks where applicable; pinned staging and affected documentation/secret/provenance checks. Actual private classification is NOT_RUN until the operator executes the prepared command. No application, TPM, reboot, backup/provider/Telegram, physical-host, Git or delegation operations are introduced.

- **Bounded viewer prepared and staged:** [targeted-review preparation](evidence/2026-09-27-hermes-production/restore-installer-findings-review-prepared-r1.json) binds the frozen viewer/launcher/tests, actual public staging and unchanged staging rerun, prior validated screening identity, and strict public reader. Fourteen focused Toolbox tests PASS, including all 25/last-five coverage, duplicate-context accounting, missing/invalid locations, log/receipt drift, safe terminal rendering, refusal of skipped classification, and unchanged matching-report rerun. Actual private classification remains NOT_RUN; the public result is currently absent. Each group requires `clear`, `secret` or `unsure`; `stop` cancels. A secret or uncertainty records a blocker and unreviewed counts. Even complete `clear` classification records G03 OPEN and manual full review NOT_RUN. No raw private content enters agent output or evidence.
- **Exact next action:** privately run `bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-restore/installer-findings-review-r1/run-private-findings-review.sh` and classify the displayed findings without sharing log content. Only sudo may need private entry; the prior recovery comparison is reused strictly against the same screened log set. Send final status/counts, then independently validate using the bounded public reader with a fresh observation label. No application, TPM, reboot, backup/provider/Telegram, physical-host, Git or delegation operation is performed. Publication checks are retained in `.toolbox/hermes-production-restore/installer-findings-review-r1/publication-r1.log`.

- **First automatic continuation after the finding-review handoff:** the native goal is observed ACTIVE following resumption. The previous user-triggered turn made concrete progress through independently validated live screening and the tested/staged complete private viewer. This continuation revalidates current 9 GiB identity/pin/one-VM/reserve guards, qualification shut off and unchanged prepared source/evidence. At 2026-09-30T03:00:57.370113+00:00, the pinned public reader reports `PRIVATE_FINDINGS_REVIEW_REPORT_ABSENT`; retained `.toolbox/hermes-production-restore/installer-findings-review-r1/public-review-observation-r2.json` and matching log have SHA256 `90f6e4bb30e67f669d912cf305c8b5387c218421e9237074bf704fe31cf1eaf0`. No mandatory-gate progress is claimed by this recheck. No specific running private-process handle is known, so this is not a verified wait and absence does not prove failure or authorize replay. The exact private command/classification handoff above remains current; do not request the same authorization again. G03–G06 and the full objective remain open. This is resumed goal turn two; keep the native goal ACTIVE. Affected documentation/provenance checks are retained in `.toolbox/hermes-production-restore/installer-findings-review-r1/continuation-publication-r1.log`.

- **Second automatic continuation / fresh three-turn blocked audit:** at 2026-09-30T03:02:54.075110+00:00, the pinned public reader again reports `PRIVATE_FINDINGS_REVIEW_REPORT_ABSENT`; `.toolbox/hermes-production-restore/installer-findings-review-r1/public-review-observation-r3.json` and matching log have SHA256 `a9ce88c9a6cfd3f842e833b786e428bdefe669a5c098166ad5d5c3790de75157`. Current 9 GiB identity/pin/one-VM/reserve guards and unchanged prepared source/evidence checks PASS, with qualification shut off. The prior and current automatic continuations make no gate progress; the same private classification prerequisite remains unmet across the user-triggered handoff and both continuations. No specific current private-process handle is known; absence is not a failure or permission to restart. The actual native `update_goal` result is `blocked` (updated_at `1790737361`), never complete. This status change does not stop any private viewer. The exact command and safe status/count handoff above remain current. G03–G06 still require private results/commissioning/recovery or separately authorized protected inputs; current app backups cannot use the unconfigured endpoint/password. All independent source/test/preparation work is finished within scope; another local mock cannot supply these live results. Keep the full objective, VM disks, recovery artifacts and dirty work intact. Affected documentation/secret/provenance checks are retained in `.toolbox/hermes-production-restore/installer-findings-review-r1/blocked-audit-publication-r1.log`.

### Private finding prompt correction R2

- The operator reports the R1 viewer ended with fixed reason `classification-not-recognized-no-receipt` after an unrecognized answer on group two; the SSH session closed. The independently pinned R4 observation still finds no R1 completion receipt. Retain R1 unchanged and do not count its partially reported answers as completed classification evidence.
- Prepare R2 to reprompt at the same finding after empty/unrecognized input, accept case-insensitive exact classification words, and cancel cleanly on `stop`, EOF or interruption. Never echo or persist invalid input and never select a default answer. Clarify that credentials mean passwords, private keys, access tokens and recovery secrets; public certificate names/identifiers alone are not credentials. The kernel [module-signing documentation](https://docs.kernel.org/admin-guide/module-signing.html#public-keys-in-the-kernel) describes built-in public verification keys and the same Fedora signing-key label. Do not broadly suppress certificate-related findings or mark unreviewed findings clear.
- Preserve all 25-location coverage, matching log-set/source/scanner bindings and G03 OPEN. Use a new helper/receipt/launcher identity, test typo recovery and cancellation with the prior complete guard suite, and stage only the reviewed replacement public source. No application/TPM/reboot/backup/provider/Telegram/physical/Git/delegation operation is added.

- **R2 correction tested and staged:** [prompt-correction evidence](evidence/2026-09-27-hermes-production/restore-installer-findings-review-prompt-r2.json) retains the reproduced failure, 15 passing focused checks, preserved R1 evidence, new helper/launcher identity, actual public staging/unchanged rerun, and bounded R2 public reader. The new prompt reprompts on typos/empty input and normalizes case only; it never supplies a default, counts an invalid answer or echoes/persists invalid input. `stop`, EOF and interruption cancel. No prior partial answers are imported. The two operator-shown public certificate labels do not authorize classifying the remaining locations automatically.
- **Exact next action:** privately run `bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-restore/installer-findings-review-r2/run-private-findings-review.sh`. The review begins at the first finding; classify every group explicitly and share only final status/counts. Use the R2 bounded public reader afterward. Current 9 GiB identity/pin/one-VM/reserve guards PASS; qualification remains shut off. No private viewer is started by staging, and no application, TPM, reboot, backup/provider/Telegram, physical-host, Git or delegation action occurs. R1 and R2 observation results are both absent before handoff; G03–G06 remain open. Publication checks are retained in `.toolbox/hermes-production-restore/installer-findings-review-r2/publication-r1.log`.

- **R2 resumption blocked audit:** the correction turn made progress; its first automatic continuation obtained an absent-receipt observation before interruption, and the intervening warning explanation made no gate progress. The current continuation again finds the same private result missing. Retained R2 observations: r2 at 2026-09-30T03:19:04.723539+00:00 (JSON/log SHA256 `12a2e93588b98597378a65dfc81c7f9096da26c569ac655a1fab38d08d970794`); r3 at 2026-09-30T03:20:20.920741+00:00 (JSON/log SHA256 `d33b9f482e37b6f6094b469053f605a5ef4fdee4e00434576ba38ac9ff277a40`). Current 9 GiB identity/pin/one-VM/reserve and frozen preparation checks PASS; qualification stays shut off. The same private-classification prerequisite has persisted across at least three resumed goal turns. With no confirmed live private-process handle and no independent authorized gate work available, the actual native goal transition returned `blocked` (updated_at `1790738406`), never complete. Public absence proves neither private-process failure nor permission to replay. No console was attached, viewer restarted or private stream/log inspected by this audit. The R2 command and safe final status/count handoff above remain current; G03–G06, disks, recovery artifacts, dirty work and the full objective are preserved. Affected publication checks are retained in `.toolbox/hermes-production-restore/installer-findings-review-r2/blocked-audit-publication-r1.log`.

### Actual R2 targeted finding classification complete

- **Independently validated live result:** [R2 completed-review evidence](evidence/2026-09-27-hermes-production/restore-installer-findings-review-live-r2.json) records the operator's actual receipt at 2026-09-30T14:10:39.645393+00:00, retrieved through pinned SSH with the frozen bounded public reader. All 25 groups and all 25 locations are reviewed clear; secret, uncertain and unreviewed counts are zero. Root ownership/mode/schema, helper identity, restore VM/boot/LUKS and the prior screening/log-set bindings match. The receipt canonical SHA256 is `3ae3b271a029cf9f8c521057f7af8b3fb1987cfd3886c07309096850a052059c`. This resolves the missing-targeted-classification blocker. R1 failure and earlier absent-receipt observations remain historical; do not replay the completed R2 viewer.
- **Exact scope and remaining prerequisite:** the unchanged log set is `d5c3ed0b4dca53744e181b88e3ec5b02eb4724fc21457d05955b120780dac2ac`; prior whole-log screening covered 12 files and 6,980,807 bytes with 12 positive controls and a private known-recovery comparison. The targeted receipt explicitly retains `G03: OPEN` and `manual_full_review: NOT_RUN`. A separate fresh pinned check at 2026-09-30T14:15:39.245710+00:00 reports `INSTALLER_HYGIENE_REPORT_ABSENT`. Therefore neither all-file manual review nor the full G03 gate is passed. The agent read only public receipts, not raw logs or private terminal input. The operator's earlier Notepad redaction was of a pasted copy, not a VM-log modification; no log repair is called for.
- **Current external state:** complete 9 GiB XML/UUID/pin/one-VM/reserve guards PASS; restore remains on boot `f5fad6ba-4a4a-4556-b933-2dbac98469d0`, qualification is shut off. No VM lifecycle, application, TPM, backup/provider/Telegram, physical-host, Git delivery or delegation operation was performed. The native controller was observed BLOCKED; this evidence update does not mark the goal complete or recreate it.
- **Exact next action:** finish the separate full private restore log review through the already staged launcher below. This is the all-file review, not another 25-finding classification. It requires private sudo and the existing recovery comparison input under the original helper; only confirm `reviewed` after actually reviewing every file. Use `:n` to move to the next file and `q` to leave the pager. If the review is not complete, cancel rather than attest. Return only its final non-secret status; independently validate the root-owned public receipt before advancing this prerequisite.

```bash
bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-restore/installer-hygiene-r1/run-private-installer-hygiene.sh
```

- **Remaining mandatory gates:** G03 full restore review and separately bound qualification hygiene; G04 live current-candidate interruption/missing-mount and isolated encrypted application backup/restore/startup with private commissioning; G05 TPM re-enrollment; G06 separately authorized exact-candidate provider/Telegram/approval inputs. Existing fault-watcher preparation remains preparation only. The unconfigured backup endpoint/password stays unused. Every disk, recovery artifact, historical receipt and unrelated dirty file remains preserved.
- **Publication method:** validate the frozen candidate executable inputs/archive and all new/prior receipt/helper bindings, changed local links, then run Toolbox Markdown lint, full-tree secret scan, source-aware migration-manifest generation/verification and whitespace checks. Retain the results in `.toolbox/hermes-production-restore/installer-findings-review-r2/live-receipt-publication-r1.log`. No unchanged full application test suite is repeated for this receipt/documentation update.

### Restore full private installer hygiene complete; recovery preparation resumed

- [Validated full hygiene evidence](evidence/2026-09-27-hermes-production/restore-installer-hygiene-live-r1.json) binds the actual root-owned receipt produced at 2026-09-30T14:48:46.244875+00:00, independently retrieved at 14:50:00.925912+00:00. Exact helper, VM, boot, LUKS, schema, file permissions and unchanged log-set identities match. All 12 retained files (6,980,807 bytes) received the operator's full private review; saved Kickstart paths are absent and the read-only recovery test plus literal/serialized/URL/base64 known-value comparison PASS. This is an operator attestation of the full review, independently bound to the public receipt; the agent did not inspect private log contents or credentials. Neither the completed targeted classification nor full restore review needs repeating.
- G03 remains open only for its other required fixture evidence, including qualification-VM installer hygiene. The latest host guard confirms current 9 GiB XML/pin/UUID/reserve identities, restore running and qualification shut off. Earlier absent receipts and failed review attempts remain immutable history. The native controller was last observed BLOCKED; do not replace the goal or infer completion from this material progress.
- **Next preparation and expected result:** adapt the existing tested encrypted header-copy workflow to this restore VM's own LUKS/var/boot identities and a separate local recovery recipient. Bind the completed hygiene receipt, use only the operator's private sudo terminal for guest root backup creation, transfer only encrypted header bytes to the workstation, and verify authenticated decryption/hash/size in memory. Preserve the local key and ciphertext, use current one-VM/9 GiB/reserve guards, and refuse mismatched reruns. Focused transaction/authentication/identity/failure/rerun tests plus pinned public staging must pass before handing over the private command. This local VM recovery copy is distinct from external backup service operations and application restoration; no TPM slot/config changes, reboot, application, provider/Telegram, physical-server, Git delivery or delegation action is included.

- **Recovery preparation PASS within scope:** [restore-specific prepared evidence](evidence/2026-09-27-hermes-production/restore-recovery-header-prepared-r1.json) binds the public recipient, source/helper/launcher/reader/tests, frozen hygiene receipt and staging metadata. Twenty focused Toolbox tests PASS with synthetic LUKS metadata and real CMS encryption/decryption/authentication, tamper/wrong-recipient rejection, transaction cleanup, preserved reruns and identity/boot/hygiene-drift rejection. The recovery key remains in the ignored owner-only restore recovery directory and was neither printed nor staged; the VM receives only the public recipient embedded in the reviewed helper. These tests do not establish an actual header backup or TPM acceptance.
- **Actual staging and bounded limitation:** helper SHA256 `681b54f7790ef86903edf8c4410bfd0f0741708f209081bc5c1f978bce8e8c72` is retained at `/home/hermesadmin/hermes-restore-header-681b54f7790ef869.py`, UID1000 mode0600. The initial non-root preview failed because `/sys/class/dmi/id/product_uuid` is root:root mode0400. Its failure and fixed-code/permission-only diagnostic are preserved; no private contents were inspected. Keep the root identity check and execute it only after private sudo; no permission change or relaxed guard is introduced. Subsequent public staging/hygiene-binding checks PASS twice with `UNCHANGED`. The launcher actually refuses non-private streams before SSH. Current 9 GiB/one-VM/reserve guards PASS.
- **Exact next operator command:** create the restore VM's encrypted LUKS header copy and verify its local ciphertext in memory. Only sudo may prompt; no LUKS input is needed for this step. Share only the final non-secret verification result. This does not enroll TPM, reboot, deploy an application or contact an external backup service. The workstation copy shares the VM's physical failure domain and is not independent production disaster recovery or application restore evidence.

```bash
bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-restore/recovery-r1/run-header-backup.sh
```

- **After the private command:** revalidate the source/hygiene/host guards and run its bounded ciphertext/public-report verifier; record actual header-copy evidence before preparing any additive TPM enrollment. Preserve guest and workstation artifacts and their dedicated private key. Matching backup reruns verify and retain the existing copy; mismatches refuse without replacing it. G03 qualification hygiene, G04 live faults/application restore, G05 re-enrollment and G06 protected live inputs remain mandatory. No unconfigured application backup endpoint is used.
- **Publication:** retained `.toolbox/hermes-production-restore/recovery-r1/publication-r1.log` records final-candidate source/archive and new/prior source/receipt bindings, changed local links, Toolbox Markdown lint, full-tree secret scan, source-aware manifest verification and whitespace checks. The unchanged application test suite is not repeated for this private helper preparation and evidence update.

### Restore encrypted header verified; bounded TPM bootstrap preparation

- [Actual encrypted-header verification](evidence/2026-09-27-hermes-production/restore-recovery-header-live-r1.json) independently repeats the pinned ciphertext fetch and authenticated in-memory decryption. Header size is 16,777,216 bytes; SHA256 `af8a73eb1e346b75c915fd048fbc92def603f0ce7dd5f9986b76b10837110236`, ciphertext `47c3392c5803f8dddb682382ffbc062f3d9181662b8144ef16c97d88f3e848a9`, recipient `21fbc7b53a0b39a672d199f8e77b670df10643e8963e528502ce504d37e532d3`. The guest report has one existing recovery keyslot and exact reviewed source/VM/LUKS identities. Matching local artifacts were retained unchanged. No plaintext header was written on the workstation, and no private key or recovery value was printed. This local workstation copy shares the VM's physical failure domain; application restore and independent production disaster recovery remain unproved.
- **Timestamp reconciliation:** a fresh pinned public observation finds the restore guest 31.485 seconds ahead of the workstation midpoint (0.1911-second round trip), despite guest NTP reporting synchronized. This explains why the guest creation timestamp is later than the original host verification timestamp. Preserve both original receipts and use authenticated bytes and the controlled fetch sequence for ordering; do not silently adjust evidence or claim synchronized clocks. No clock setting was changed.
- **Next preparation and expected checks:** adapt the previously tested qualification boot helpers to the restore UUID, five mounted filesystem identities and verified recovery ciphertext. The private setup must prove the existing passphrase before and after additive SHA256-PCR7/no-PIN enrollment, preserve the original keyslot and baseline crypttab/initramfs, validate a staged initramfs before replacement and refuse unrelated drift. Bind this first private setup to the current boot and completed hygiene receipt. Only after setup and runtime facts pass may it install the five exact root-owned boot helper operations (facts, reboot, poweroff, one-time recovery arm/poweroff and matching cleanup/reboot); no shell, arbitrary arguments or passwordless private enrollment is granted. Actual boot operations and console recovery remain later separately observed tests; the private bootstrap itself must not reboot.
- Reuse and rerun the focused policy/real-file transaction/rollback/partial-retry/recovery-entry/bootstrap authorization tests, add changed-boot/hygiene guards, validate transmitted scripts and non-private-terminal refusal, then stage public source with a preserved unchanged rerun. Keep the current 9 GiB XML/one-VM/pin/20 GiB reserve guards. No application, external backup service, provider/Telegram, physical target, Git delivery or delegation operation is included. G03 qualification hygiene, G04 live fault/application restore, G05 re-enrollment and G06 protected live inputs remain mandatory.

- **Prepared/tested/staged PASS within scope:** [restore TPM bootstrap preparation](evidence/2026-09-27-hermes-production/restore-tpm-bootstrap-prepared-r1.json) binds bootstrap `354591d70b878c829e4355cbb1fe5b8a0919918cae14d4d4c9cbf1fd73eaa030`, all three exact embedded helpers, launcher, named-operation client, current host guard, receipt validator and tests. Sixty-four focused boot/policy/transaction/recovery/bootstrap tests plus four public-receipt tests PASS in Toolbox. Privileged commands and root ownership are mocked; real temporary files exercise state preservation, retries and rollback. Payload/source/transmitted-reader/shell syntax and refusal of non-private streams PASS. These are preparation results, not live TPM or boot acceptance.
- **Actual public staging:** bootstrap retained at `/home/hermesadmin/hermes-restore-boot-354591d70b878c82.py`, commissioning-user mode0600; first staging reports `STAGED`, repeat `UNCHANGED`. All 14 required executables and `/dev/tpmrm0` are present. Hostname/current boot and completed hygiene receipt match, with complete current 9 GiB XML/pin/one-VM/reserve checks PASS. The bounded public reader reports `BOOTSTRAP_REPORT_ABSENT` before handoff. Guest root execution, new sudo rule, TPM enrollment and lifecycle operations have not run. Root DMI/initramfs/token checks remain mandatory inside private setup; tool availability is not their substitute.
- **Exact next operator command:** use the private workstation terminal below. Enter sudo and the existing restore LUKS passphrase only at its labeled private prompts; three LUKS entries are expected on initial setup (before enrollment, enrollment, after enrollment). The launcher first revalidates the encrypted recovery copy in memory. The bootstrap preserves the original recovery slot and boot files, adds the reviewed TPM token/configuration, and only after successful setup enables the five fixed boot-test commands. It does not reboot, deploy an application or contact an external backup/provider/Telegram service. Share only the final non-secret result.

```bash
bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-restore/boot-r1/run-private-bootstrap.sh
```

- **After success:** validate the root-owned bootstrap receipt using `boot-r1/check-public-bootstrap.py` with fresh label `r2`, then independently call bounded facts and test sudo denial for an unrelated command/extra arguments. Continue actual automatic warm/cold boot, private passphrase recovery and subsequent automatic boot only with matching identities and the one-VM guard. Do not attach a console during private input. Re-enrollment, qualification installer hygiene, current application faults/isolated restoration and separately authorized protected live tests remain open. The application backup endpoint is still unconfigured and unused. Native goal status was last observed BLOCKED; no completion or replacement goal was created.
- **Publication:** `.toolbox/hermes-production-restore/boot-r1/publication-r1.log` retains exact candidate/archive, prior/new source/helper/receipt bindings, changed local links, Toolbox Markdown lint, full-tree secret scan, source-aware manifest generation/verification and whitespace checks. Existing candidate executable acceptance is not broadened by private setup preparation; unchanged application tests are not repeated.

### Actual restore TPM setup and bounded boot qualification

- The strict pinned public readers independently validate the completed bootstrap and exact TPM setup reports, including passphrase tests before and after enrollment, original recovery-slot preservation, one SHA256-PCR7/no-PIN token and matching crypttab/initramfs identities. `boot-r1/public-receipt-r2.json` and `public-setup-report-r1.json` retain the sanitized reports. The fixed root facts command independently confirms the current system running on initial boot `f5fad6ba-4a4a-4556-b933-2dbac98469d0`, matching source/kernel/mount/security/TPM/configuration identities. Actual `check-grant` proves an unrelated command and extra arguments are denied by sudo. The earlier private-setup blocker is resolved; do not rerun bootstrap.
- **Authorized next live method:** call only the installed named reboot operation, wait with pinned non-interactive public SSH for a new boot ID, and require fresh named root facts with the same kernel/crypttab/initramfs/PCR7/recovery-slot and healthy-system checks. Then use named clean poweroff, require shut-off state and unchanged current 9 GiB persistent XML plus unrelated-disk canary, verify both guests stopped and the workstation reserve, and start only the owned restore VM. Require another new boot ID and matching healthy root facts without operator recovery input. No console is attached or captured. Preserve all transition attempts; a timeout or failed guard stops further lifecycle actions without force-off. Actual recovery-passphrase boot remains a separate private operator step after these automatic tests.

- **Actual automatic boot results PASS:** [restore live boot evidence](evidence/2026-09-27-hermes-production/restore-tpm-automatic-boot-live-r1.json) binds the independent setup receipt, root facts, grant denial tests and every named transition. Initial boot `f5fad6ba-4a4a-4556-b933-2dbac98469d0` changed to warm boot `c3e8775d-cdd8-47a0-a350-c57e2212dc80`, then cold boot `5bd1214c-0518-48fa-b2ff-4985085efe5c`. Kernel `6.19.10-300.fc44.x86_64`, crypttab `3de8ab9027d74fc406e773cd6bec5076f282504e6d0fcec3ea931e7955f98f17`, initramfs `004102cd24ab964530393e43100da12aac17effd33d6a1063962131c5503b1a9` and PCR7 `9488fb8f963f81eec491074b49485b126cb2a420618ac08fd3949e3772a1a5ea` remain unchanged. Both fresh root observations validate the original recovery slot, SHA256-PCR7/no-PIN token, mounted identities, Secure Boot, SELinux, absent swap and healthy units. No console or private input was used by the agent; the operator was instructed to leave the console untouched. Cold boot readiness was observed after 17.268 seconds. This is boot evidence only; no application is deployed on restore.
- The stopped cold-start guards verified both guests shut off, no managed save, unchanged complete 9 GiB/two-CPU XML, correct regular owned disks, intact unrelated-disk canary and 52,514,451,456 bytes workstation free before starting only restore. The VM definition and disks were not replaced. Historical 8 GiB ownership metadata is retained and is not used as the current lifecycle baseline.
- **Next private recovery method:** use the installed hash-bound `--arm-and-poweroff` helper to add only a separate one-time BLS entry, preserve the normal saved default and original boot files/LUKS metadata, and power off. It selects the original keyslot and disables TPM token modules only for that one boot. Recheck current stopped identities/canary/reserve and start restore paused. Provide a private-terminal-only `virsh console --safe --resume` wrapper so the operator attaches before execution reaches the passphrase prompt. Never attach/capture the console from the agent; no bootloader editing, key removal or password reset is part of this test. After actual private unlock and explicit detachment, independently verify the corrected recovery boot, use the existing named cleanup/reboot operation, and prove subsequent automatic boot. Preserve the one-time entry's retained copy and every attempt.

- **Actual recovery preparation and paused handoff:** [retained private handoff](evidence/2026-09-27-hermes-production/restore-tpm-private-recovery-handoff-r1.json) binds the successful named `recovery` result, exact one-time BLS entry, normal entry/configuration and LUKS metadata hashes, guarded stopped state and paused start. The helper preserves the normal saved default, token enrollment and recovery slot. Both guests were verified stopped before starting only restore paused; current 9 GiB/two-CPU XML and unrelated-disk canary match, no managed save was discarded, and 52,505,391,104 bytes workstation free remained. The agent has not attached or captured a console, resumed this private boot or entered any secret. Actual recovery unlock and subsequent automatic boot remain NOT_RUN.
- The private console wrapper passes shell syntax and actual non-TTY refusal before libvirt. Its paused-VM metadata guard also PASSes against the exact active/persistent XML and retained handoff; it checks no terminal contents. It uses `virsh --escape '^q' console hermes-production-restore --safe --resume`, so the operator attaches before the VM reaches the recovery prompt. It does not force another console user off. A second launch after resume refuses the paused-state guard rather than guessing whether private input is active.
- **Exact next operator action:** run the following in the private workstation terminal. At the disk-unlock prompt, enter the existing restore LUKS passphrase (not the administrator login password). Wait for the `hermes-restore login:` prompt, then press Ctrl+Q to detach; login is unnecessary. Reply only `booted and detached` once the secret prompt is finished and the console has detached. Preserve the VM and boot entry if the recovery attempt fails; report only the non-secret status, never the value or console/log contents.

```bash
bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-restore/boot-r1/run-private-recovery-console.sh
```

- **Continuation after that report:** independently validate current root facts with recovery parameters present, the new boot ID and unchanged identities; then run the installed named `finish-recovery` operation, retain the exact removed entry, observe a new automatic boot with recovery parameters absent and require healthy root facts. Do not infer recovery from SSH alone or invoke cleanup while operator-private input/console activity remains unresolved. G03 qualification hygiene, G04 current live faults/isolated application restore, G05 re-enrollment and G06 protected exact-candidate tests remain open. All disks, recovery artifacts, unrelated dirty work and historical evidence are preserved; no production deployment/acceptance is claimed.
- **Publication:** `.toolbox/hermes-production-restore/boot-r1/live-boot-publication-r1.log` records retained source/candidate/archive and actual boot/handoff/evidence bindings, local links, Toolbox Markdown lint, full-tree secret scan, source-aware manifest generation/verification and whitespace checks. Native goal status was last observed BLOCKED; this private-input handoff neither completes nor replaces it.

### Restore private recovery and subsequent automatic boot verified

- [Fresh live recovery evidence](evidence/2026-09-27-hermes-production/restore-tpm-recovery-live-r1.json) distinguishes the operator report “booted and detached” from independent pinned root facts. Recovery boot `11065a57-afa3-491c-870a-aa3419b5a449` has the required temporary parameters, unchanged disk/kernel/TPM/configuration identities and a healthy system. No private input or console contents were captured by the agent.
- The exact named cleanup preserved the one-time entry copy (`cd2afa80376e2f887f07b5c805789d1c7eab6030efae48ac8864b93628b32b31`), removed only that unchanged entry, retained the normal saved default and proved LUKS metadata unchanged. Its requested reboot was separately observed as boot `35b9ffc1-26b6-474c-a23e-68983f95bfbb`, with recovery parameters absent, the original recovery slot preserved and all root boot/security/health checks passing. Qualification remained shut off; both current 9 GiB baselines and all recovery artifacts remain intact.
- The prior private-recovery handoff is resolved. Next: prepare and test the restore-specific synthetic application bootstrap against this exact boot, completed hygiene/header evidence and frozen candidate receiver. It must retain the bounded named dispatcher and empty application state, use private sudo, and leave application deployment and unconfigured backup service operations NOT_RUN. Re-enrollment, qualification hygiene, current application faults/isolated restore and separately authorized protected live tests remain required.

### Restore synthetic application dispatcher prepared

- [Prepared handoff](evidence/2026-09-27-hermes-production/restore-application-prepared-r1.json) binds the current restore boot, public machine/SSH identities, actual hygiene/header/full basic boot sequence and unchanged final candidate `579403970f8225aea05866752e82e8800b3bac3f5abcf2cd892ffc9f52944295`. Receiver `a1edcaad3a47e22ce4246b13243eb39c8d66038388def6c21feb5dd31bb5671c` and every packaged executable input match the frozen candidate. Restore runtime and deployment account inspection found both application accounts absent; no application installation is inferred.
- Fifteen focused Toolbox guards PASS, covering exact receiver/source integrity, stale boot/VM/recovery rejection, fixture-only mode, completed private hygiene/recovery receipt binding, preservation of existing application/pending transactions, matching file reruns and strict public receipt schema/proof validation. Root account/service operations are mocked; these tests establish preparation only. Shell/transmitted/Python syntax and actual non-TTY refusal before SSH PASS.
- Public bootstrap `1d93bbc35f961b023ea1b75676290f0c5126871eed1c7606b0a549e9c3ffd996` is staged at `/home/hermesadmin/hermes-restore-application-1d93bbc35f961b02.py`, commissioning-user mode0600. Its real staging rerun is `UNCHANGED`; current 9 GiB/pinned identity/one-VM/reserve guards PASS. The strict public reader reports `APPLICATION_BOOTSTRAP_REPORT_ABSENT`. The separate restore deployment key remains local, ignored and owner-only; only its public key is embedded. No root bootstrap or application deployment has run.
- **Exact next operator command:** run this in the private workstation terminal, entering sudo privately. No LUKS prompt is expected. The helper installs the reviewed synthetic receiver, locked runtime account and forced-command deployment dispatcher with actual preflight/commissioning checks. It refuses an existing application or pending transaction and does not deploy containers, reboot, change TPM slots or contact any backup/provider/Telegram service. The restore backup endpoint remains explicitly unconfigured and its password unprovisioned; later backup setup still needs its own concrete reviewed configuration.

```bash
bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-restore/application-r1/run-private-bootstrap.sh
```

- Share only the final non-secret status/error. After success, use `application-r1/check-public-bootstrap.py r2` to validate the root-owned receipt, then inspect/use the bounded `productionctl.py` named preflight with the restore deployment key and exact pinned host. Bootstrap success alone is not runtime/restore acceptance. Keep qualification shut off during this private handoff; retain all disks, recovery material, prior receipts and dirty work.
- G03 qualification hygiene, G04 current-candidate interruption/missing mount and isolated encrypted application backup/restore/startup, G05 TPM re-enrollment and G06 separately authorized protected exact-candidate tests remain open. Native goal status was last observed BLOCKED; no replacement or completion was requested. Publication checks are retained in `.toolbox/hermes-production-restore/application-r1/publication-r1.log`; unchanged full application suites are not repeated for these helper/receipt/documentation additions.

### Active goal resumption: restore dispatcher receipt still absent

- The native goal is independently observed ACTIVE, starting a fresh resumed blocked audit. The prior turn made concrete progress by completing the restore recovery sequence and staging the tested private application bootstrap. The full objective remains unchanged.
- [Fresh public observations and named-inspection preparation](evidence/2026-09-27-hermes-production/restore-application-receipt-status-r1.json) retain `APPLICATION_BOOTSTRAP_REPORT_ABSENT` at 16:20:40Z and 16:22:34Z on 2026-09-30. Current 9 GiB/identity/pin/one-VM/reserve guards PASS; qualification remains shut off. Existing helper/boot/prepared evidence bindings are unchanged. No private process is claimed to be running solely because a receipt is missing.
- Prepared `application-r1/run-named-inspection.py` calls the frozen existing production controller only for `preflight` or `status`, after a fresh strict public receipt check. The dedicated deployment key is local and the SSH wrapper supplies the required agent/password/forwarding prohibitions. Actual syntax and invalid deploy/backup/`--apply` refusals PASS. The missing receipt caused exit3 before any deployment-key connection or named operation. Actual application preflight remains NOT_RUN; local preparation does not close G04.
- The next operator action remains the already staged private `application-r1/run-private-bootstrap.sh`; no new authorization or repeated password-reset/boot work is required. After its success, the exact agent continuation is `python3 -I -B .toolbox/hermes-production-restore/application-r1/run-named-inspection.py preflight r4`. Public observation labels r1–r3 are consumed and preserved. Follow with a fresh-label named status check only after preflight succeeds.
- G03 qualification hygiene, G04 actual faults/isolated encrypted application restoration, G05 re-enrollment and G06 protected separately authorized live inputs remain unmet. Keep restore running and qualification stopped during the pending private setup. No provider/Telegram/external backup/physical-host or Git operation occurred. This is the first resumed audit of the current private-input blocker; the native goal remains active and incomplete. Publication checks are retained in `application-r1/receipt-status-publication-r1.log`.

### Restore application private-input impasse — native goal BLOCKED

- [Third consecutive resumed audit](evidence/2026-09-27-hermes-production/restore-application-blocked-audit-r1.json) confirms the same missing completion receipt. Latest independent pinned observation is `APPLICATION_BOOTSTRAP_REPORT_ABSENT` at 2026-09-30T16:25:10.395031Z; current boot/9 GiB/pin/one-VM/reserve guards remain valid. Each guarded named-preflight attempt stops before connecting with the deployment key. No application preflight/deployment ran. Receipt absence is not evidence that an operator-private process is running or stopped; no live agent-owned operation handle remains.
- The first resumed turn completed inspection-client preparation; the following two turns revalidated the unchanged private blocker and made no additional gate progress. Local preparation/publication checks are complete. Actual remaining gate observations require private setup, private review/recovery or separately authorized protected live inputs; repeating mocks or switching away during the pending restore handoff cannot close them. The native controller now confirms **BLOCKED**, following the required three-turn audit. The full objective is preserved and incomplete.
- **Exact operator action remains unchanged:** run the following in the private workstation terminal and enter sudo privately. No LUKS prompt is needed. Share only the final non-secret result. This installs only the bounded synthetic restore dispatcher; it does not deploy containers, reboot or contact backup/provider/Telegram services.

```bash
bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-restore/application-r1/run-private-bootstrap.sh
```

- **Resume after the private result:** revalidate worktree and exact prepared inputs, then run `python3 -I -B .toolbox/hermes-production-restore/application-r1/run-named-inspection.py preflight r6`. Labels r1–r5 are already consumed and retained. Require a valid root-owned receipt, exact receiver/bootstrap identities and actual named preflight before continuing. Keep qualification shut off; preserve both VM disks, keys/recovery artifacts, historical evidence and dirty work.
- G03–G06 remain open in their recorded scopes; the unconfigured application backup endpoint stays unused. No production acceptance, physical-host contact, provider/Telegram/external backup operation, Git delivery or delegation is claimed. Final handoff publication checks are retained in `application-r1/blocked-audit-publication-r1.log`; unchanged full application tests are not repeated.

### Restore private dispatcher independently qualified for named operations

- [Actual bootstrap and named-inspection evidence](evidence/2026-09-27-hermes-production/restore-application-bootstrap-live-r1.json) validates the operator-reported PASS against two strict public receipt reads and independent deployment-key `preflight` and `status`. Exact restore VM, current boot, bootstrap `1d93bbc35f961b023ea1b75676290f0c5126871eed1c7606b0a549e9c3ffd996` and receiver `a1edcaad3a47e22ce4246b13243eb39c8d66038388def6c21feb5dd31bb5671c` match. All seven actual preflight checks PASS; host/boot/package commissioning identities match the receipt.
- The status reports `current: null` and `transaction: null`. Preserve this empty target for isolated restoration. This resolves the missing-bootstrap blocker; do not rerun private bootstrap. No containers, Restic application backup/restore or external backup endpoint calls were performed. Native goal was last observed BLOCKED before the new evidence; authorized task work resumes without creating a replacement or claiming completion.
- Next authorized sequence: named clean restore poweroff, both current 9 GiB XML/UUID/disk/canary/reserve guards, start only qualification, then fresh pinned boot facts and current-candidate named preflight/status/verify. Bind and stage the prepared private interruption watcher only after those observations pass. G03 qualification hygiene, G04 actual faults/isolated application restore, G05 re-enrollment and G06 protected live tests remain mandatory.

### Qualification resumed; exact-boot interruption watcher staged

- [Fresh VM switch and runtime evidence](evidence/2026-09-27-hermes-production/qualification-resumed-after-restore-r1.json) binds named clean restore shutdown, both approved current 9 GiB definitions and disk canaries, the retained qualification-start intent and independent root boot facts. Restore stays shut off and empty; only qualification runs. Its new boot ID is `e70a19f2-8e56-4a14-918d-92f3990fe712`. Actual named preflight/status/credential-free runtime verification PASS for candidate A `579403970f8225aea05866752e82e8800b3bac3f5abcf2cd892ffc9f52944295`, receiver `a1edcaad3a47e22ce4246b13243eb39c8d66038388def6c21feb5dd31bb5671c` and the preserved recovered journal `ab3fdeabf3574cf4a740ed83aaf84b5b`.
- The first post-start XML comparison failed after the start because it compared active runtime annotations with inactive disk definitions. The original helper and start intent are preserved. A separate read-only observer explicitly validated the expected aliases, numeric source indices, empty backing-store elements and empty-CD format omission, while comparing the full configured boot/disk structure and both persistent baselines. No definition, disk or security setting changed and no lifecycle operation was replayed. Fresh root facts independently prove healthy boot and unchanged kernel/crypttab/initramfs/PCR7/recovery-slot identities.
- [Prepared and staged interruption R2](evidence/2026-09-27-hermes-production/qualification-interruption-writer-staged-r2.json) binds helper `1a82079f170c022fb68255ccab7ce636a5bdf68874f304bfe9b69e48af40dfd0` to that boot, exact A/marker-C candidates, receiver, synthetic host configuration and recovered starting journal. Public staging reports `STAGED`, then `UNCHANGED`; initial public READY is absent. No root watcher, signals, update or recovery ran. The workstation reserve and one-VM/current-9-GiB/pin guards passed.
- Thirteen focused watcher tests and four strict public-receipt tests PASS. Tests exercise real fixture SIGSTOP/SIGKILL/pidfds/flock/guard drainage, readable retained tar hashes and preservation; actual guest root/process matching is mocked. The first expanded test run failed because one success-rerun fixture retained a placeholder boot ID; the fixture was corrected to the new required identity without weakening the guard. Failed and subsequent logs remain retained; only final-source results are current. Shell/Python/transmitted syntax, non-private-terminal refusal and the live harness's no-side-effect preview PASS. The original R1 preparation remains historical.
- The root watcher exposes its PID/start/parent tuple in strict public receipts. The agent's reader checks live process identity without reading arguments, environments, terminal contents or private logs. An old READY file alone never authorizes the marker upgrade. The watcher may pause only the matched snapshot tar child and kill only its dispatcher; it never signals the writer guard. It resumes the writer automatically, verifies guard drainage and retained stopped journal/lock identity, and validates the retained tar without extracting or printing filenames. Its result is limited to interruption/drainage/archive preservation, not application restoration.
- **Exact next operator command:** enter sudo privately and leave the foreground terminal open. When `READY_FOR_ONE_MARKER_UPGRADE` appears, send only that line so the agent can independently validate the live process before starting the approved synthetic test. No new sudo rule, reboot, backup/provider/Telegram operation or physical-server contact is involved.

```bash
bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-validation/synthetic-stage/qualification-namespace/interruption-writer-r2/run-private-watcher.sh
```

- **Agent continuation after fresh live READY:** run `python3 -I -B .toolbox/hermes-production-validation/synthetic-stage/qualification-namespace/interruption-writer-r2/run-live-interruption.py --apply`. This single-attempt harness verifies retained preparation hashes and starting state, launches the approved marker-C upgrade, observes the held-writer receipt, requires actual named `operation-busy` rollback refusal and unchanged current pointer/stopped journal, waits for verified drainage, then deploys exact A to recover and requires `UNCHANGED` plus actual runtime verification. Preserve its local process handle and all intent/results on any timeout or failure; never replay the upgrade merely because an observation timed out. Source/candidate/archive identities are unchanged.
- After a successful harness, independently verify rerun/process parity and retain snapshot/canary/recovery-artifact evidence. Missing-mount, isolated encrypted application backup/restore/startup, qualification full private installer hygiene, TPM re-enrollment and separately authorized exact-candidate provider/Telegram/approval tests remain mandatory. The unconfigured backup endpoint is unused. Native goal was last observed BLOCKED; this new private-watcher handoff is not completion. Publication checks are retained in `interruption-writer-r2/publication-r1.log`.

### Qualification interruption private-input impasse — native goal BLOCKED

- [Three consecutive resumed audits](evidence/2026-09-27-hermes-production/qualification-interruption-writer-blocked-audit-r2.json) retain pinned READY observations at 16:44:28Z, 16:47:40Z and 16:48:11Z on 2026-09-30. Every observation reports `WATCHER_RECEIPT_ABSENT`; watcher liveness is not inferred. Current 9 GiB XML/UUID/pin/one-VM/reserve guards PASS. Qualification remains the sole running VM; restore stays shut off. No private console, terminal contents, process arguments, environment or raw logs were inspected.
- The prior two goal continuations made no gate progress and were not verified waits on a live handle. This third audit confirms the same private prerequisite remains missing. All 25 preparation bindings, 34 packaged source inputs and both exact A/C archives remain unchanged; no live-attempt intent exists. Repeating preparation tests cannot close a live gate. Remaining independent gates require private commissioning, private hygiene/recovery work or separately authorized protected inputs; switching guests during this pending private handoff would not resolve them. The native goal transition returned **BLOCKED** (`updated_at: 1790786875`), never complete. Preserve the full objective and G03–G06.
- **Exact next action remains the private watcher command below.** Enter sudo privately and keep the terminal open. Send only `READY_FOR_ONE_MARKER_UPGRADE` when it appears. Do not rerun restore bootstrap or alter sudo policy. Receipt absence alone does not establish whether an operator-private prompt is active.

```bash
bash /var/home/aicloudopspecial/code/repos/hermes-fedora-host/.toolbox/hermes-production-validation/synthetic-stage/qualification-namespace/interruption-writer-r2/run-private-watcher.sh
```

- Resume by revalidating the preparation and a fresh READY receipt with `watcher_process_live: true`; observation labels r1–r4 are consumed and retained. Only then use the prepared single-attempt `run-live-interruption.py --apply` harness above. Never replay an existing intent or restart an operation because an observation times out. All disks, recovery material, journals, guards, locks, prior evidence and dirty work remain preserved. No fault, application mutation, lifecycle, backup/provider/Telegram, physical-host, Git delivery or delegation operation occurred during these audits. No production acceptance is claimed.
- Blocked-handoff publication checks are retained in `interruption-writer-r2/blocked-audit-publication-r1.log`: evidence/source/archive bindings, local links, Toolbox Markdown lint, full-tree secret scan, source-aware manifest generation/verification and whitespace checks. The unchanged application suite is not repeated for this evidence/documentation-only update.

### Qualification administrator password forgotten — private recovery preparation

- The operator reports forgetting the qualification VM administrator password. The earlier private password reset applied to the separate restore VM. The watcher and recent application bootstrap do not change `hermesadmin`'s password. Do not guess, retrieve or publish a password/hash, weaken sudo permissions or repeat the restore reset.
- Prepare the canonical verified-media rescue procedure for qualification UUID `27b76faa-7e0b-4162-9fad-e9f85684309a`, using its current 9 GiB baseline and preserving both disks, TPM/NVRAM, recovery material, current application and journal. The operator must first confirm the failed sudo prompt is cancelled; until then, no lifecycle change or console attachment is authorized by inference. Fresh pinned observation r5 reports `WATCHER_RECEIPT_ABSENT` at 2026-09-30T16:55:00.568882Z; this does not infer private-process liveness. Actual named status/preflight PASS for exact candidate A and the unchanged recovered journal `ab3fdeabf3574cf4a740ed83aaf84b5b` is retained at `/tmp/hermes-production-named-operation-r2/password-recovery-before-r1.json`.
- After cancellation: guarded clean poweroff, retained stopped-state canary checks, Fedora44 media hash/signature validation and rescue-only preview against the exact existing domain. Start only that existing qualification VM in rescue mode after verifying the preview; no disk recreation, installation, formatting, application update or external service operation. All secret input stays in the operator's private console. The installed-system hostname/LUKS identities must match before `chroot /mnt/sysroot passwd hermesadmin`; preserve SELinux context afterward, unmount cleanly and return to the unchanged normal boot configuration.
- Recovery and password reset are NOT_RUN at this preparation step. A subsequent boot invalidates the R2 watcher's exact boot binding; preserve R2 and all historical evidence, then prepare a new bound helper only after independent boot/application revalidation. G03–G06 and the full objective remain open. Do not run the earlier watcher command during recovery.
- [Prepared recovery evidence](evidence/2026-09-27-hermes-production/qualification-password-recovery-prepared-r1.json) retains the unchanged actual candidate/journal observation, absent public watcher receipt, current baseline and new rescue-preview helper. Eleven synthetic XML acceptance/rejection cases PASS, covering exact approved structure and rejection of memory/UUID/NVRAM/boot-command/kernel-location/disk/serial/read-only-media drift. Actual cached Fedora44 ISO SHA256 and pinned signer verification PASS. This validates preparation only: the live `virt-install --print-xml` preview, shutdown, rescue start and password reset remain NOT_RUN.
- The first preparation validation failed because Toolbox did not have the Fedora public signing key at its own `/usr/share` path. The unchanged original helper and failure record are retained. The corrected helper uses the existing host public key exposed at `/run/host/usr/share`, still requiring the exact Fedora44 signing fingerprint and ISO checksum. No package, credential or security-policy change was made.
- Await the operator's `cancelled` confirmation before the first lifecycle operation; no private console is attached by the agent. After guarded clean shutdown, the exact preparation command is `python3 -I -B .toolbox/hermes-production-validation/synthetic-stage/qualification-password-recovery-r1/preview-rescue.py`. Inspect its retained live result and approve only the already scoped rescue launch arguments; a preparation PASS alone cannot justify starting an unvalidated domain configuration. Handoff publication checks are retained in `qualification-password-recovery-r1/publication-r1.log`.

### Qualification shutdown authorized by the operator; agent execution denied

- On 2026-09-30 the operator explicitly requested the qualification VM shutdown and stated they will run the rescue preview command themselves. `qemu:///session` lists only `hermes-production-qualification` as running and `hermes-production-restore` as shut off. (The earlier `qemu:///system` query shows no domains and is not the lab connection.)
- The agent's attempt to run the named poweroff (`qualification-boot/run-boot-operation.py poweroff`) was refused by the agent permission policy before execution. No SSH, sudo, lifecycle, console or disk operation ran; no observation file was created. The operator runs the shutdown instead.
- **Exact next action (operator):** from `.toolbox/hermes-production-validation/synthetic-stage`, run `python3 -I -B qualification-boot/run-boot-operation.py poweroff` and expect `"status": "REQUESTED"`. Wait for `virsh -c qemu:///session domstate hermes-production-qualification` to report `shut off`, without force-off. Then run `python3 -I -B qualification-password-recovery-r1/preview-rescue.py`, which repeats the stopped-state XML/canary guards and must report `PASS_RESCUE_ONLY_PREVIEW_NO_GUEST_START`. Rescue start and password reset remain NOT_RUN; G03–G06 are unchanged.
- Operator-run named poweroff: `REQUESTED` with `ssh_exit: 0` from expected boot `e70a19f2-8e56-4a14-918d-92f3990fe712`. Kernel/crypttab/initramfs/PCR7 identities are unchanged, recovery parameters are absent and the recovery slot is preserved. The observation is retained at `qualification-boot/observations/20261001T015759995406-poweroff.json`. The agent's read-only wait observed both domains `shut off` at 2026-10-01T01:58:11Z, with no force-off. The R2 watcher's boot binding is now consumed. **Exact next action (operator):** run `preview-rescue.py` as above and return its output for validation before any rescue start.
- Operator-run rescue preview: `PASS_RESCUE_ONLY_PREVIEW_NO_GUEST_START` at 2026-10-01T01:58:59Z. Preview `46741cdda77de6c6c1cb94a01a050d5a72acc267fb4cd8c447f46de6c2722b7c`, media `85837793…cf1f` and signer `36F612DC…9F90A6` match. Independent agent diff: the inactive definition still equals the 9 GiB baseline. Stage 0 adds only the read-only DVD source, rescue kernel/initrd/cmdline and `on_reboot=destroy`, replacing hd boot. Stage 1 adds only the read-only DVD source. Both stages keep the same `system.qcow2`/`unrelated.raw` disks. Both VMs are shut off.
- Prepared guarded one-shot launcher `qualification-password-recovery-r1/start-rescue.py` (sha256 `789248d09a3f8a1a76d51edd8119b90c624f84a39200fafa382bccc6ce741db6`), following the earlier `start-admin-collision-rescue-r1.py` pattern. It reuses the preview helper's guards, requires the retained preview hash/arguments, creates an exclusive intent before the launch and never replays it, logs the launch, then requires the qualification VM running, restore shut off and persistent XML equal to baseline plus the DVD source. `--check` PASS at 2026-10-01T02:00:08Z with no intent/start files created. Rescue start and password reset remain NOT_RUN.
- **Exact next action (operator, explicit approval of the rescue start):** `python3 -I -B .toolbox/hermes-production-validation/synthetic-stage/qualification-password-recovery-r1/start-rescue.py`. Then privately run `virsh -c qemu:///session console hermes-production-qualification`, choose Continue/mount and enter the qualification LUKS passphrase privately. Require `cat /mnt/sysroot/etc/hostname` = `hermes-qualification.test` before `chroot /mnt/sysroot passwd hermesadmin`; then `chroot /mnt/sysroot restorecon /etc/shadow`. Report only non-secret results. Clean unmount, poweroff, DVD ejection and the normal-boot return follow the restore precedent.
- Operator-approved rescue start: `RESCUE_STARTED_CONFIG_VERIFIED` at 2026-10-01T02:01:26Z, retained in `qualification-password-recovery-r1/start-r1.json` with intent and launch log `c83b3fe0ec84e4d674630e72b6f40512f86f3c13a07342af26b993d8d829e0b0`. Independent agent check: qualification is running (domain id 8) and restore is shut off. The active definition has the same UUID, 9 GiB, `on_reboot=destroy`, the exact `inst.rescue` cmdline and only `system.qcow2`, `unrelated.raw` and the read-only signed DVD. virt-install's "Starting install" wording is its generic message; no installer was selected. The private console, LUKS unlock and password reset remain NOT_RUN. **Exact next action (operator, private console):** the hostname check, `passwd hermesadmin` and `restorecon /etc/shadow` steps above; report only non-secret results.
- Rescue storage discovery (operator-reported, 2026-10-01): Anaconda rescue found no installed root, the same `ROOT_NOT_FOUND` behavior as the 2026-09-29 rescue on this VM. `lsblk` shows `vda1` vfat, `vda2` xfs and `vda3` crypto_LUKS `bf1c622c-17c0-4d2b-9b51-82c345ad1de7`, with no mapping or mount. The manual `cryptsetup open` first reported the systemd-tpm2 token PCR policy mismatch. This is expected: the rescue's direct kernel boot does not reproduce the Secure Boot PCR7 state, so it is correct refusal, not tamper evidence. All three operator-typed passphrase attempts returned `No key available with this passphrase`. `hermes_system` is not activated and nothing is mounted. The record shows a single installer passphrase in slot 0, proven by the 2026-09-29 recovery boot and the passphrase tests before/after TPM enrollment, and the 2026-10-01 poweroff facts report `recovery_slot_preserved: true`; no recorded operation changed keyslots. A failed `open` does not modify the header. Password reset remains NOT_RUN. **Exact next action:** non-secret keyslot listing, then a single test-only passphrase attempt.
- Keyslot listing (non-secret, operator-pasted): data segment `0: crypt`, LUKS2 keyslots 0 and 1, token `0: systemd-tpm2` bound to keyslot 1, digest `0: pbkdf2`. This matches the recorded single-passphrase slot 0 plus the TPM slot. A single test-only attempt `cryptsetup open --test-passphrase --key-slot 0 --tries 1 -v /dev/vda3` failed (`No key available with this passphrase`, code -2). That makes two failed unlock rounds against an intact slot 0, so retries stopped for reassessment. The qualification Kickstart uses `keyboard us`, and earlier installer/recovery passphrase entries used the same `virsh console` path. The evidence cannot distinguish a mistyped or misremembered passphrase from an input-path difference, and slot 0's passphrase is not proven lost. The VM stays in the rescue shell; exiting it powers the VM off (`on_reboot=destroy`). **Decision pending (operator):** (1) retry test-only with a stored qualification passphrase after privately checking the special-character input path, or (2) the TPM normal-boot `rd.break` route. Route 2 requires separate approval because it changes keyslots and requires rerunning this VM's recovery proof (G05).

### Qualification LUKS passphrase reported lost — TPM normal-boot password route

- **Operator decision (2026-10-01):** "the passphrase is gone". Keyslot 0 is intact but its passphrase is unknown. As a result, this VM no longer meets the baseline's known-good recovery-passphrase requirement, and its G05 recovery proof no longer reflects an operable recovery path. Earlier recovery evidence stays historical.
- **Approach change:** reset the administrator password through the normal Secure Boot path. The TPM unlocks automatically, and a one-time GRUB edit adds `rd.break console=ttyS0,115200n8`. PCR7 binds Secure Boot state/authorities, not the kernel command line, so this works without either secret. Record this as an observed property consistent with the baseline's stated non-protection of an intact stolen machine, not as a new protection claim. The VM has no graphics device, so OVMF/GRUB use the serial console. SELinux label: `setfiles` against the targeted file_contexts for `/etc/shadow` only, then verify `shadow_t`; no full autorelabel, to avoid resetting container/MCS labels. Fallback if labeling fails: one later `enforcing=0` boot with `restorecon /etc/shadow`, treated as non-evidentiary.
- **Finding:** the installed qualification boot helpers (`commission-boot.py` `check_tokens`, `recovery-once.py`) bind the full keyslot-0 identity and the exact keyslot set. Any recovery-passphrase replacement therefore requires re-commissioning the boot baseline and rerunning this VM's recovery proof. That keyslot work is NOT authorized yet and needs its own baseline and approval.
- Prepared `qualification-password-recovery-r1/return-normal-paused.py` (sha256 `4f1ce8c6b2faf61fe26dff64d71fe7a15313678909b6618295082ff65d68da01`) from the restore precedent. It requires the rescue start record, both VMs shut off, the inactive XML equal to the baseline plus only the known read-only DVD on `sda`, both canaries, the 20 GiB reserve and a clean qcow2 check. It then makes a one-shot exclusive intent, ejects with `change-media --eject --config`, requires the exact baseline structure, starts paused and verifies no rescue kernel/initrd/cmdline, hd boot and no DVD. While rescue was running, `--check` correctly refused (`qualification-not-stopped`) and created no files.
- **Exact next action (operator):** `exit` the rescue shell (nothing is mapped or mounted; `on_reboot=destroy` stops the domain). Then the agent runs `--check`, and the operator runs the helper and the private GRUB `rd.break` steps.
- Operator exited rescue (domain stopped via `on_reboot=destroy`) and ran the recorded helper (sha256 `4f1ce8c6…da01`, matching the record) directly, which ran the full guard set. Result `NORMAL_DISK_BOOT_PAUSED_AWAITING_PRIVATE_CONSOLE` at 2026-10-01T02:37:35Z: qcow2 check has 0 errors, virtual size 189817421824, persistent XML `93423a83…a422a`, active XML `04052ee8…b123`. Independent agent check: qualification is paused (domain id 9) and restore is shut off. The inactive definition equals the baseline structure. The active domain has no rescue kernel/initrd/cmdline, boots from `hd` and has no DVD source. **Exact next action (operator, private console):** resume, interrupt GRUB, add one-time `rd.break console=ttyS0,115200n8`, then reset the password and label `/etc/shadow`. Report the `ls -Z` result.
- Console `--resume` reported `Failed to resume domain` because the domain was already running (`running (unpaused)`), so the GRUB window was missed. The guest booted normally to `hermes-qualification login:` with no passphrase entered. Fresh named facts: `OBSERVED`, new boot `8b3dc86e-971d-4653-87ea-c250d2481501`, system `running`. Kernel `6.19.10-300.fc44`, PCR7 `9488fb8f…a5ea`, crypttab `f1458594…9be3`, initramfs `2df447c5…5ef4ce` and the `PCR7_SHA256_NO_PIN` policy are unchanged. Recovery parameters are absent and the recovery slot is preserved. **Exact next action:** operator keeps the console attached and runs the named `reboot`, then presses Esc for GRUB and proceeds with one-time `rd.break`.
- Operator-run named `reboot`: `REQUESTED` from boot `8b3dc86e-971d-4653-87ea-c250d2481501` with unchanged kernel/crypttab/initramfs/PCR7 identities. `ssh_exit: 255` is the expected connection drop, which the helper accepts for transitions. The private GRUB `rd.break` step is pending with the operator.

## Approved scope change — unattended production path (2026-10-01)

**Approval evidence:** after the qualification VM's LUKS passphrase was reported lost, the user asked "how can you make it production deployment simplified and fast keeping the security?". In plan mode they chose: discard the current qualification/restore VMs and requalify automatically; a generated, escrowed break-glass admin password; installer-generated, escrowed LUKS recovery key. They then approved the plan saved at `~/.claude/plans/this-is-taking-an-tingly-barto.md`. The original baseline's security scope is unchanged; this changes only how it is established.

**Baseline (frozen):**

- **Outcome:** unattended production install from one prepared ISO (about 15 minutes) plus one deploy command; release qualification as one unattended disposable-VM pipeline (about an hour). Same contract: LUKS2 + SHA256 PCR7 TPM no-PIN, Secure Boot, signed bundles, forced-command dispatcher without a general root shell, rootless read-only containers, offline worker, no secrets in Git/arguments/logs.
- **Escrow:** an operator RSA-4096 escrow certificate, rendered public-only. The installer generates the LUKS recovery key, admin break-glass password and header backup, encrypted with CMS AES-256-GCM + RSA-OAEP-SHA256. The ciphertext is fetched, decrypt-verified and deleted from the server by `productionctl enroll`. Nobody types or memorizes a secret.
- **Kickstart:** `%pre` random temporary passphrase in installer RAM via `%include`. `%post` adds the recovery key and TPM PCR7 enrollment, test-unlocks with the recovery key, writes matching crypttab/dracut, backs up the header and wipes the temporary slot, then sets the escrowed admin password and writes a non-secret receipt. The installer reboots. **Go/no-go:** installer and installed PCR7 must match, so the installer boots through firmware/shim/GRUB, never direct kernel boot. Fallback: one firstboot enrollment after a single escrowed-recovery-key console entry.
- **Firstboot:** a one-shot unit verifies TPM unlock, generates host config from the real identities, runs the existing bootstrap, publishes SSH fingerprints to the console issue, reboots once and writes the automatic commissioning record.
- **Proofs:** per-host automatic (`recovery_unlock`, `encrypted_offhost_recovery`, `automatic_reboot`); per-release in signed qualification evidence (`recovery_then_automatic_boot`, `isolated_restore`, `automatic_cold_start`); per physical target `console_access` and `firmware_power_restoration` via `productionctl attest`.
- **Operations:** dispatcher `credentials` named operation reading a bounded env document from SSH stdin; `pin-host`; `media` (verified ISO → `mkksiso` with Kickstart, controller files and `inst.nosave=all_ks`); `vm/hermes-production-qualify.py` writing `qualification.json` for `bundle --evidence`.
- **Authority:** repository implementation and local disposable-VM qualification. Destroying the two existing VMs/disks requires a separate explicit go-ahead after showing exact resources. Production canary, real credentials, commits, pushes and PRs remain separately gated. No delegation.

| Task | Outcome / dependencies | Progress | Gates | Exact next action |
| --- | --- | --- | --- | --- |
| U01 | Renderer fields, escrow and secret-generating Kickstart; none | ✅ DONE | UG1/UG3 | — |
| U02 | Firstboot commissioning module/unit; U01 | ✅ DONE | UG1/UG3 | — |
| U03 | Commissioning proof split, `attest`, `enroll`, `pin-host`; U01/U02 | ✅ DONE | UG1/UG3 | Physical `attest console/power` runs on the first physical target |
| U04 | Dispatcher `credentials` operation and CLI; none | 🔄 IN_PROGRESS | UG1 | Offline tests PASS; a live run needs real credentials (G06) |
| U05 | `media` builder (local tool image instead of Toolbox `lorax`); U01 | ✅ DONE | UG1/UG3 | — |
| U06 | Qualification pipeline; U01–U05 | ✅ DONE | UG1/UG3/UG4 | Remaining automation: interruption/missing-mount faults, off-host restore |
| U07 | Runbook rewrite and record; U01–U06 | ✅ DONE | UG2 | — |
| U08 | Discard old VMs (separate go-ahead) | ✅ DONE | — | — |

| Gate | Method / expected result | Status |
| --- | --- | --- |
| UG1 | New focused unit tests plus the canonical Toolbox offline gate PASS | ✅ PASS (final attempt 3: all checks, 644 reviewed tests) |
| UG2 | Markdown lint, links, full-tree secret scan, provenance manifest PASS | ✅ PASS (check-only lint, local links, full-tree secrets, source-aware manifest 839 rows) |
| UG3 | Live go/no-go: unattended install and firstboot with no passphrase prompt in a fresh Secure Boot + swtpm VM booted from the built ISO | ✅ PASS (r7, r8) |
| UG4 | Full pipeline `qualification.json` all PASS, twice from scratch, with stage timings | 🚧 BLOCKED — local stages PASS twice (r7, r8); restore/application need a backup host and real credentials; repeatability faults not yet automated |

Prior G03/G04/G05 work is STALE: superseded by this approach, with its evidence kept as history. G01/G02/G07 become STALE when U01–U05 change the source.

### Unattended path — implementation progress (2026-10-01)

- **Implemented (U01–U06 source):**
  - `production/escrow.py`: CMS AuthEnvelopedData AES-256-GCM + RSA-OAEP-SHA256, verified round trip with OpenSSL 3.5.8 on host and Toolbox.
  - `production/kickstart.py` + template: new validated fields, `%pre` random temporary passphrase via `%include`, reinstall guard, hash-pinned controller payload, `reboot --eject`.
  - `production/install.py`: `%post` keyslots, PCR7 enrollment, header escrow, admin/restic secrets, receipt, unit.
  - `production/commission.py`: per-boot TPM unseal proof, bootstrap, issue codes, automatic reboot, attestations.
  - `preflight.py`: proof split.
  - `host.py`: `attest`/`credentials` named operations.
  - `production/client.py`: pin and enroll.
  - `production/media.py`: verified ISO → `mkksiso` in a no-network, cap-dropped, private-label local tool container.
  - `productionctl.py`: new subcommands.
  - `vm/hermes-production-fixture.py`: firmware cdrom boot, serial log, `qualify` role.
  - `vm/hermes-production-qualify.py`: pipeline.
- **Design findings during implementation:**
  - Anaconda's fresh `/dev/shm` mount in the target means secrets travel via a dedicated tmpfs mounted inside the target and removed after `%post`.
  - `/var/tmp` (1777) fails root-parent checks, so that tmpfs mounts at `/var/lib/hermes-install`.
  - A `%post` shim update could change SbatLevel and PCR7 on first boot, so `shim-*` is excluded from the install-time upgrade.
  - The host is Kinoite without `mkksiso`/`mtools`, and Toolbox provisioning forbids elevated installs, hence the local tool image built from `localhost/dev-base:fedora-44`.
  - Old candidates are refused by the new receiver, so the pipeline signs a fresh test candidate.
- **UG1 attempt 1:** 75 production tests PASS (new `ProductionUnattendedTests` and `ProductionQualifyPipelineTests` allowlisted). Canonical offline gate: every check PASS except the migration manifest, which fails as expected until regeneration. Retained at the scratchpad `gates/offline-u1.log`. UG1 stays 🔄 until regeneration and rerun.
- **Next:** live UG3 go/no-go with `vm/hermes-production-qualify.py --apply` on the host (local disposable `hermes-production-qualify` VM only; the old VMs are untouched), then docs (U07), manifest regeneration and gates.
- **Live run r1 (`.toolbox/hermes-qualify/runs/20261001T033432Z`):** `prepare`/`candidates` PASS, `media` FAIL. `mkksiso` rebuilds `efiboot.img` with `mkefiboot`, which needs loop devices, and the rootless container has none. The Fedora 44 DVD `efiboot.img` holds a full `grub.cfg` (not a chain stub), with `set default="1"` (media test) and a 60 s timeout. **Fix:** `mkksiso --skip-mkefiboot -R` sets the default to Install with a 5 s timeout. The ISO-level `grub.cfg` is copied into `efiboot.img` with `mcopy`, `xorriso -boot_image any replay` keeps both El Torito records, `implantisomd5 --force` runs, and the result is verified by reading the EFI `grub.cfg` back. A manual prototype showed BIOS and UEFI boot records intact and the arguments plus `inst.ks` in the UEFI menu entry.
- **Live run r2:** `media` PASS (26 s), `create` PASS, and GRUB auto-booted Install over serial through firmware→shim→GRUB. Anaconda `%pre` then failed. Reading `/tmp/ks-script-*.log` through the disposable VM's console showed `install: command not found`. The installer image also lacks `timeout` (the original template's package step called it outside the chroot as well). It has `cp mkdir chmod mount umount rmdir rm chroot lsblk blockdev python3 findmnt`, `/dev/tpmrm0`, and `/run/install/repo` containing the payload. **Fix:** `mkdir -m`/`cp`+`chmod`, `timeout` run inside the target chroot, and a new regression test refusing `install`/`timeout`/`clear` in installer-environment sections. 76 production tests PASS. Run r3 started with `--replace-previous` (owned `qualify` role only).
- **Live run r3:** `%pre` PASS ("Starting automated install"). Anaconda then hung at "Trying to detect CD-ROM automatically" (`/tmp/packaging.log`, 03:42:58 onward, read through the disposable VM's console). The template's `cdrom` method assumed the old direct-kernel fixture with a separately attached DVD; a USB-written ISO would not be a CD-ROM either. **Fix:** remove `cdrom`; `media` reads the verified DVD's volume ID (`xorriso -pvd_info`) and adds `inst.repo=hd:LABEL=<volid>`, verified in the UEFI menu entry. A regression asserts no `cdrom` line. 76 tests PASS. Run r4 started.
- **Live run r4:** install source, storage (LUKS2 with the temporary passphrase), 649 packages, and the signed upgrade plus `restic`/`tpm2-tools` step PASS. The controller-copy `%post` then refused with "Pinned Hermes installer payload not found": `/dev/sr0` is mounted twice (`/run/install/repo` by dracut, `/run/install/sources/mount-0000-hdd-device` by Anaconda), and the code required exactly one match. **Fix:** accept any candidate matching the pinned manifest hash (each file is still re-hashed), refuse only when none match. Regression added for the two-mount case. 76 tests PASS. Run r5 started.
- **Live run r5:** the duplicate-mount fix worked. In the real installer, `install-commission` passed escrow-certificate validation, packages and Podman version, the recovery key slot, PCR7 TPM enrollment, recovery-key test unlock, **installer TPM token-only unseal**, temporary-slot removal (final slots 1 recovery + 2 TPM), the `hermes-production` LUKS label, crypttab `tpm2-device=auto` and dracut for both the DVD kernel and the updated 7.2.8 kernel. It then refused `crypttab-target-row-count`: dracut's embedded crypttab names the device `/dev/disk/by-uuid/<uuid>` (the old commissioning helper accepted this form). **Fix:** `crypttab_tpm(..., embedded=True)` accepts that path for the initramfs check only; regression added. A probe in the same disposable installer showed SELinux permissive, `setfiles` exit 0 with the correct `etc_t` label, `tpm2_pcrread` working, OpenSSL 3.5.8 and systemd 259.9. 76 tests PASS. Run r6 started.
- **Live run r6 — UG3 core evidence:**
  - **Unattended install PASS in 421 s.** All `%post` steps passed. The installed system booted kernel 7.2.8 with **no passphrase prompt**: install-time PCR7 enrollment carries over to the real firmware→shim→GRUB boot path.
  - Firstboot refused `bootstrap-preflight-failed`. Break-glass diagnosis on the disposable VM (escrow fetched over the admin key, decrypted with the run's test escrow key, `sudo -S` with the escrowed password) showed every check PASS except `conflicts: unmanaged-hermes-unit-conflict`, caused by the installer's own `hermes-commission.service`. **Fix:** `preflight.commissioning_unit()` allows exactly that root-owned unit with byte-identical content (`COMMISSION_UNIT_BYTES`, now shared with `install.py`) and its `multi-user.target.wants` symlink.
  - With that source copied to `/root/hermes-fix` in the guest: real `bootstrap --apply` → `BOOTSTRAPPED`; installed preflight all PASS except the expected `commissioning`. Real `commission-boot` → `tpm_unseals: true`, reboot requested. The second boot unit succeeded with `tpm_unseals: true` and the banner reprinted on `ttyS0` via `agetty --reload` (util-linux 2.41.5).
  - **Design bug found:** `automatic_reboot` stayed pending because the self-requested reboot stops the still-activating unit, so `ExecStop` never clears the running marker and the next boot is treated as unclean. **Fix:** clear the marker before requesting that reboot; `ExecStop` remains for ordinary shutdowns, preserving power-loss detection. Regressions added for both. 78 tests PASS. Run r7 starts from scratch.
- **Live run r7 — full pipeline PASS** (`.toolbox/hermes-qualify/runs/20261001T045829Z`; report sha256 `36d34f1de5933cdfbb3dc9a8daa7000675968efac8a6ef4535122db4918f7c51`, `qualification.json` `32c059d40ea75e7fd7d49216cf7a84756e581fb6686eb2ea1b9a9852803e4c2b`). Candidate `a5bf4b1f07f205d149fedb44fb9e654b52cb0916305b3e0a2001e2c10bd8c930`, upgrade `30bbcd62274b35f19168cbd6c4dbfd2ab42a22d0cf1faa221bcb44c5aa34581b`; the candidate receiver identity matched the installed payload's.
  - **Stage timings (s):** prepare 0.7, candidates 3.6, media 26.3, create 3.4, **install 426.2**, **commission 45.1**, enroll 3.0, **deploy 52.5**, rerun 8.3 (`UNCHANGED`), failed_update 9.0 (corrupt bundle refused, release unchanged), upgrade_rollback 31.9, warm_reboot 27.2, cold_start 27.3, recovery_boot 3010.2, canary 5.1 (unrelated disk unchanged). Install → commissioned → deployed took about 9.5 minutes with no secret typed.
  - **recovery_boot:** with Secure Boot off for one boot, the TPM refused, `Please enter passphrase for disk luks-…` appeared, the harness typed the 71-character escrowed test recovery key, and the system booted with `SecureBoot disabled`. NVRAM was then restored, the next boot was automatic with no prompt, and verify passed. The 3010 s figure is a harness defect: `virsh console` ignores SIGTERM, so `waitpid` blocked until the agent killed that pipeline-owned console child. **Fix:** close the pty (hangup), bounded wait, then SIGKILL.
  - **Banner fix:** completed commissioning left the last "Pending" line on the console. The banner now shows only the host key and "Commissioning complete". 78 tests PASS.
  - **Gates (honest local run):** installation PASS, runtime PASS, boot PASS; restore BLOCKED (no off-host backup host); application BLOCKED (no real credentials); repeatability NOT_RUN (interruption and missing-mount not automated); repository NOT_RUN (offline gate report not passed in).
  - **UG3 PASS.** Run r8 (final source, VM removed on PASS) started for confirmation.
- **Live run r8 — confirmation on final source PASS** (`runs/20261001T060020Z`; report `93aad884ce97a3d7427f48d2421f90d221af6bbc6e4bda3d5f876249f83cd9e3`, `qualification.json` `c13a2a1f8d6c4383cc78016e9594be4c2a3e2c968ffe23602f9d02bd2a2ef865`). Every stage PASS in **741 s total**: install 431.2, commission 45.1, enroll 2.8, deploy 51.9, rerun 7.6, failed_update 9.2, upgrade_rollback 32.2, warm_reboot 27.7, cold_start 30.9, **recovery_boot 63.4** (the console fix works), canary 5.1. The owned VM was removed on PASS; the old pet VMs were not touched. Test-signed bundle copies, ISOs, saved NVRAM and diagnostic escrow copies were deleted from the run directories; reports and test keys remain.
- **Repository gates:** canonical offline gate attempt 2: every check PASS (644 reviewed Python tests, including the 21 new ones) except the migration manifest, which is regenerated last. Check-only lint PASS (the earlier `detect-private-key` hit was my test literal, since replaced). Local links and anchors in the changed docs PASS.
- **Current outcome:** the unattended path is implemented and proven locally. A fresh Secure Boot + TPM2 machine installs, commissions and deploys in about 9.5 minutes, with no secret typed or remembered; recovery uses the escrowed key. **Still open, not claimed:** off-host isolated restore (needs a backup host), exact-candidate DeepSeek/Telegram/approval tests (needs real credentials, G06), automated interruption/missing-mount faults, physical `attest console/power` on a real target, and the production canary (separately authorized). The old VMs are kept pending the operator's go-ahead (U08).
- **Final repository gates PASS:** offline gate attempt 3 PASS on the final tree, with every check including the source-aware migration manifest (839 rows). This record was then updated (documentation only) and the manifest regenerated and re-verified; no executable input changed afterwards.
- **Exact next action:** obtain the operator's decision on U08 (discard the two listed old VMs). Then, when available: a backup host for off-host restore, real credentials for the application gate, and a physical target for attestation and the canary.

### Cleanup — operator instruction "Delete all unnecessary and start from scratch if needed" (2026-10-01)

- **Deleted (inventoried first):**
  - The 13 superseded test candidate bundles in `.toolbox/hermes-production-validation/synthetic-stage/candidate-*.tar` (about 13 GB). The new receiver refuses them, and their identities remain in this record.
  - Six stale fast-lab image-cache entries and one partial `.building` entry under `.toolbox/hermes-disposable/v2/prepared/` (about 44 GB). The current lab cache key `58d31918…` matched none of them. Entry `f86703e7…` was kept: it is the image source of the passing qualification runs.
  - The unreferenced older gateway image `hermes-agent@sha256:6bece064…` (2.8 GB).
  - Free space rose from 47 GB to 103 GB.
- **Kept:** the verified Fedora DVD and CHECKSUM; `f86703e7…`; the current gateway image `fca358f1…`; `localhost/hermes-media-tools:fedora-44`; all small logs/JSON from earlier work (23 MB); qualification run reports and test keys; lab reports; the physical server's `.toolbox/hermes-production-{recovery,boot,access,backup}` material (recovery material for a real machine, not unnecessary); the shared dev-toolbox containers and images (not this project's); the stopped local backup-fixture container and its image (managed by `backup-fixture.py`).
- **Blocked for the agent:** destroying and undefining `hermes-production-qualification` (still running) and `hermes-production-restore` was refused by the agent permission policy ("Interfere With Workloads"). Their disks (`.toolbox/hermes-production-fixture` 15 GB, `.toolbox/hermes-production-restore` 3.8 GB) and their NVRAM/swtpm state remain for the operator to remove. U08 stays 🚧 until then.
- **Start from scratch:** not needed. Run r8 already passed from scratch on the final source, no source changed since, and a read-only pipeline preview confirms its inputs are intact.
- **U08 done (2026-10-01):** at the operator's explicit request, the agent ran exactly the four listed commands. `hermes-production-qualification` (27b76faa…) was destroyed and undefined with `--nvram --tpm`, `hermes-production-restore` (dbe191ac…) was undefined with `--nvram --tpm`, and `.toolbox/hermes-production-fixture` and `.toolbox/hermes-production-restore` were removed. Verified: no session domains remain, the NVRAM and swtpm directories are empty, and 122 GB is free. Committed evidence and the physical server's recovery material are untouched.
- **Exact next action:** none in repository scope. When available: a backup host (off-host restore gate), real DeepSeek/Telegram credentials (application gate, G06), and the physical target for `attest console/power` and the separately authorized production canary.

## Approved scope change — production reinstall without off-host backup (2026-10-01)

**Approval evidence:** the user asked to "get installation to production in a fast and simple way" and answered the follow-up questions:

- reinstall 10.0.30.10 ("I need to reinstall");
- a read-only server query ("Yes, read-only query");
- the live application test ("Yes");
- the disk layout ("Yes, use this layout");
- backups: "No backups for now", after the router was explained as unsuitable. That option was presented as explicit approval to relax the release backup-restore rule.

**Server facts (read-only query, 2026-10-01):** single NVMe `/dev/disk/by-id/nvme-512GB_SSD_MQ26W40711034` (476.9 GiB), 13.6 GiB RAM, Secure Boot enabled, `/dev/tpmrm0` present, `eno1` 10.0.30.10/24 with gateway 10.0.30.254, current Fedora 44 kernel 7.2.7. The existing manual install becomes obsolete on reinstall.

**Baseline (frozen):**

- Host contract accepts `restic_repository: "none"`; `backup` then refuses with `backup-not-configured`. Adding a repository later is a host-configuration change (private re-bootstrap).
- Release qualification: the restore gate PASSes on the local failed-update-restore and rollback evidence when the operator selects no off-host backup, with the waiver recorded in the qualification report. Without that selection it stays BLOCKED.
- Automate the repository (offline gate run by the pipeline) and repeatability (concurrency, interruption via dispatcher SIGKILL and recovery, missing-mount refusal and recovery via the escrowed break-glass in the disposable VM) gates.
- The application gate is a pipeline mode with operator-held credentials and operator-observed Telegram allow/reject plus approval.
- Production settings: disk `nvme-512GB_SSD_MQ26W40711034`, root 30 GiB, /var 100 GiB, /home/hermes 120 GiB (about 220 GiB VG free), budgets 4/8 GiB.
- Security contract otherwise unchanged. Wiping the server, production keys and the canary remain operator actions at the console.

| Task | Outcome | Progress |
| --- | --- | --- |
| P01 | `restic_repository: "none"` contract + backup refusal + docs/tests | ✅ DONE |
| P02 | Pipeline repository/restore-waiver/repeatability automation | ✅ DONE (r11) |
| P03 | Pipeline live application mode | 🔄 IN_PROGRESS — implemented and offline-tested; the live run needs the operator |
| P04 | Production settings, keys and ISO for 10.0.30.10 | 🔄 IN_PROGRESS — server facts and `operator-setup` ready; keys/ISO are operator steps |
| P05 | Operator: live test, reinstall, commission, deploy | ⬜ TODO |

- **P01 DONE:** `restic_repository: "none"` accepted by the host contract and renderer; `backup` and `restore-rehearsal` refuse with `backup-not-configured` before preflight. Tests added (80 PASS).
- **P02 live (run r10, `runs/20261001T202229Z`):** prepare, **repository (offline gate inside the pipeline, 105.9 s)**, candidates, media, create, install 426.1, commission 45.1, enroll, deploy 50.9, rerun, failed_update and **concurrent_upgrade 32.6 s** (second request refused `STOP: operation-busy`; upgrade CHANGED, rollback ROLLED_BACK, verify PASS) all PASS.
  - `interrupted_upgrade` FAIL `ssh-failed:no-output`: `pkill -f 'productionctl.py dispatch'` also matched its own `sh -c`/`sudo` parent, killing the break-glass session. **Fix:** bracket pattern `[p]roductionctl.py dispatch`.
  - On the kept VM the interruption itself had worked. The journal was left at `configuration` with no dispatcher remaining; one `rollback` recovered (`UNCHANGED`), the current release was back to the candidate and verify passed.
  - `missing_mount` premise corrected: a plain unmount is healed by `RequiresMountsFor` remounting the right XFS. Faults are now a **substituted** tmpfs and an **unavailable** (runtime-masked) mount. Both were blocked by the runtime guard and refused by the dispatcher (`host-preflight-failed`) on the kept VM, then recovered with verify PASS.
- **P04 prepared:** a second read-only query showed the server sees the workstation as `192.168.99.184` (no NAT), so `deploy_from` is `192.168.99.184/32`; timezone America/Bogota. Server facts are in `.toolbox/hermes-production-access/server-10.0.30.10.json` (non-secret, 0600). New `productionctl operator-setup` creates the admin/deploy keys, the passphrase-protected signing and escrow keys, `allowed_signers` and `install.json`; tested offline. Runbook updated (operator-setup, `"none"` backups, new pipeline stages and flags). Run r11 starts from scratch.
- **Run r11 — from scratch PASS** (`runs/20261001T203644Z`; report `35e86b52f00243f9fdd88b51c732e5282a957cfbe6379aa352ec29c7569a60e2`, `qualification.json` `0ed6ead0adc40be93d31ce9c5cde9608eb4c45a8c5879d003e4f0d90bcbc40ed`). **868 s total:** repository 105.6, install 421.1, commission 45.1, deploy 50.8, concurrent_upgrade 32.9 (`operation-busy`), **interrupted_upgrade 23.0** (killed at `configuration`, recovered `UNCHANGED`), **missing_mount 11.7** (substituted and unavailable both `BLOCKED`), warm 30.3, cold 30.5, recovery_boot 59.6, canary 5.1. Gates: repository, installation, runtime, repeatability, restore (recorded no-off-host-backup waiver) and boot PASS; application BLOCKED pending the operator's live run. The owned VM was removed on PASS.
- **Terminal prompts verified** through a pseudo-terminal harness with test passphrases only: `ssh-keygen` signing-key creation (two prompts), OpenSSL escrow-key encryption (two prompts, `ENCRYPTED PRIVATE KEY`) and escrow decryption (one prompt) all prompt on the TTY despite captured stdout/stderr.
- **Source freeze for production:** the operator's live qualification run, `bundle --evidence` and `media` must use this exact tree; any change to the controller source or runbook makes the qualification stale.
- **Exact next action (operator):** `operator-setup`, the gateway environment file, the live qualification run, `bundle`, `media`, USB, then the server steps (see the runbook fast path).
- **Operator report (2026-10-01):** "I just reinstalled new fedora 44 server". Read-only checks: `~/hermes-production` does not exist, so `operator-setup`, the live qualification, `bundle` and `media` (steps 1–5) were not run and no Hermes image was built. The server answers on 10.0.30.10:22 with a new, **unverified** ED25519 key `SHA256:SaZ43qiraQ0H08WiViAOE+fyYnjX7VggmavJgTNx8Oc`. It was not pinned and no login was attempted. This is a stock Fedora installation without the Hermes escrow, TPM enrollment or commissioning. **Next:** steps 1–5 on the workstation, then boot the Hermes USB image over this install (it erases the disk; the reinstall guard does not block, because the stock install has no `hermes-production` LUKS label).
- **Operator steps 1 and 5 (2026-10-01):** `operator-setup` CREATED `~/hermes-production` (directory 0700, private keys 0600). The escrow key is OpenSSL-encrypted (certificate `7d9e6a91b53156d74155b666260c7f0b66cacdc17b5425081944a0e3546bf801`), and `install.json` validates as production on `nvme-512GB_SSD_MQ26W40711034` with `restic_repository: "none"`. The signing key was first created without a passphrase; the operator then added one, and the agent verified that an empty passphrase is refused. `media` BUILT `hermes-production.iso`, 3732 MiB, sha256 `ee80b73137e12a1db2a47ba2d95775e17101a41b36ac590a7726943c0ea59df6`. The agent independently confirmed the manifest `ad2a917e…dcef` equals the one recomputed from the current tree and settings, and that the UEFI entry boots Install with `inst.nosave=all_ks inst.text inst.repo=… inst.ks=…` and no serial-console override (installer output on the physical screen). Receiver identity of the current tree: `526410e7…`. **Freeze:** `scripts/hermes/**` and `docs/HERMES_PRODUCTION_DEPLOYMENT.md` must not change until the live qualification, `bundle` and deploy are complete.
- **Defect found before the production boot (2026-10-01):** after the operator wrote the stick, the agent compared the image's GPT EFI System Partition (`Appended2`, what UEFI firmware boots from USB) with the El Torito `efiboot.img`. They differed. `xorriso -boot_image any replay` re-appended the DVD's original ESP, whose `grub.cfg` still had `set default="1"` ("Test this media"), a 60 s timeout and no Kickstart. The stick would have started an interactive installation. Every VM run had booted the El Torito image as a virtual CD and could not catch this. The operator was told not to boot the stick.
  - **Fix:** `-append_partition 2 0xef /work/efiboot.img` after replay, prototyped on a scratch DVD copy (ESP bytes equal the updated image, `set default="0"`, 5 s timeout, both El Torito records intact). `media` now requires a single GPT ESP whose bytes start with the updated image, and checks `grub.cfg` in both copies.
  - **Fidelity:** the qualification VM now boots the media as a read-only USB disk (`--import`, `on_reboot=destroy`; the pipeline removes the disk with `virt-xml` and restores `on_reboot=restart`).
  - Runbook updated (USB ESP, raw write, no Ventoy). 80 tests PASS. The operator's `hermes-production.iso` (`ee80b731…`) and the stick are superseded and must be rebuilt and rewritten after run r12.
- **Run r12 — USB-disk boot path PASS** (`runs/20261002T001516Z`; report `934cd115c8b63e6075ed82779b8cfec0c33e4888f7ae17986cb43286c98a238d`, `qualification.json` `b52e8a844681012ad99081a52847846f33a4125504d01406c1634756ac623985`, candidate `468e903f…`). The qualification VM booted the image as a read-only USB disk: the firmware skipped the empty target, GRUB auto-selected "Install Fedora 44", the Kickstart loaded from the USB ESP path and the automatic install ran. Every stage PASS in 890 s (install 437.1, commission 45.1 with TPM unlock and no prompt, deploy 52.6, all fault, reboot and recovery stages). Gates: everything PASS except application (BLOCKED until the operator's live run); restore under the recorded waiver.
- **Operator stick:** rebuilt from the current tree (`hermes-production.iso` `3c6d1e86dbb44ded2c63ce7a2761b1004869122f09f9ba40a196a2647969d239`). The agent confirmed its USB ESP menu (`set default="0"`, 5 s, Kickstart arguments). The operator reported `cmp` STICK_OK. The old image is kept as `.broken`. The server currently runs a plain Fedora 44 install that the stick will replace. **Next (operator):** boot the server from the stick and send the banner's SSH fingerprint and console code.
- **Production server installed from the stick (2026-10-02):** the console photo shows Fedora 44 Server on kernel 7.2.8-200.fc44, hostname `hermes-production`, and the commissioning banner with only `console_access`, `encrypted_offhost_recovery` and `firmware_power_restoration` pending. `recovery_unlock` and `automatic_reboot` were already PASS: the TPM unlocked on both automatic boots with no prompt.
  - **Host key verification:** the photo reading `SHA256:91PDK2pBJLFUAt/e0euF3Sf4ZJ5G7y+9xw2b1FE1OkA` matched the scanned `SHA256:9lPDK2pBJLFUAt/e0euF3Sf4ZJ5G7y+9xw2b1FElOkA` with only two `1`/`l` console-font look-alikes. Pinned in `~/hermes-production/known_hosts`.
  - **Console attestation:** the code `9A275-CFFD9` read from the photo was submitted by the agent with the deploy key: `attested: console_access`, now missing `encrypted_offhost_recovery` and `firmware_power_restoration`.
  - **Read-only raw preflight (deploy key):** platform `fedora44-x86_64-enforcing`, storage on `/dev/nvme0n1p3` with LUKS2 + PCR7 token, crypttab and initramfs checks PASS, packages, runtime account, SSH policy and conflicts PASS. Commissioning is incomplete, as expected.
  - **CLI gap:** remote `preflight` hides its report when the status is FAIL. The raw request reads it.
  - **Finding:** Fedora Server's Cockpit web console (`cockpit.socket`, firewall zone service) is reachable on 10.0.30.10:9090. Mitigated, not exploitable as is: root is locked and the admin password is a random escrowed secret. It is still extra password-login surface. Close it after enrollment; future Kickstarts should disable it.
- **Enrollment (2026-10-02):** the operator's `enroll` returned ENROLLED, attesting `encrypted_offhost_recovery`, with only `firmware_power_restoration` missing. LUKS UUID `9a0831b5-1d06-4324-b80a-1c79bacbfa0f`; escrow `~/hermes-production/10.0.30.10-escrow.cms` (0600, `19765afc9a4dac038d72df41b4b4277ba7b8049fff49524853a0c72b9238b725`) with recovery key, admin and Restic passwords, LUKS header and receipt. The agent verified the server copy is removed and that `hermesadmin` sudo requires the password.
- **Cockpit closed:** the operator used the escrowed admin password over the pinned admin key to disable `cockpit.socket` and remove the `cockpit` firewall service. The agent verified 9090 is closed from the workstation, the socket is disabled and inactive, and SSH stays reachable. Follow-up: the production Kickstart should disable Cockpit for future installs (template change after deploy).
- **Power-restoration proof and commissioning complete (2026-10-02):** the operator pulled AC power and restored it. The server switched on by itself (operator-confirmed) and booted with the TPM unlocking and no prompt (agent-observed: SSH back within a minute, `tpm_unseals: true`). The banner showed power-restoration code `2CDCA-8CA20`, which the agent submitted with the deploy key: `COMMISSIONED`, nothing missing. Full installed preflight through the dispatcher is **PASS** on every check (platform, packages, storage_boot, runtime_account, ssh_policy, conflicts, commissioning). 10.0.30.10 is a commissioned production host with no application deployed yet. **Next:** the operator's credentials file, the live application qualification run, `bundle --evidence`, then `credentials` and `deploy`.
- **Live run r13 (`runs/20261002T013438Z`, operator credentials):** every stage through enroll PASS, and `credentials` STORED. `deploy` CHANGED and the gateway started, connected to Telegram (polling) and answered the operator's `uname -sr` message. The follow-up `verify` FAILED: the raw dispatcher reason was `unexpected-credential-fields`. The stored `.env` (names only, no values, inspected through the test VM's escrowed break-glass) contained the three operator settings, the four disabled-feature switches and **`API_SERVER_KEY`, written by the gateway image at start** for its built-in API server (disabled; no port). Synthetic mode never checks credentials, so only a live run could catch this.
  - **Fix:** `runtime.CONTAINER_MANAGED = {API_SERVER_KEY}` is accepted only when validating the stored file; operator files (`productionctl credentials`, `--live-env`) stay strict; `API_SERVER_ENABLED` must still be `false`.
  - **Test correction:** the contract requires approval for dangerous commands and memory writes, not every command, so the live questions now check `uname -sr` answers directly and `rm -rf /tmp/hermes-approval-check` stops for approval and does not run when denied.
  - **Agent slip:** an edit to `application()` cut five methods from `vm/hermes-production-qualify.py` (untracked, so no Git copy). They were restored verbatim from the passing r7–r12 source, and a test now requires a method for every stage. 82 tests PASS.
  - **Server impact:** the receiver changed, so 10.0.30.10 (stick receiver) needs the documented private controller update (`bootstrap` from the new source with the escrowed admin password) before deploy. Host config, signer trust, disk and commissioning stay unchanged.
- **Live run r14 (`runs/20261002T015701Z`, operator credentials):** every stage through deploy PASS, including **deploy and verify in production mode** (53.8 s; the container-managed key fix works). In `application`, after the operator's Telegram interactions, the allowlist-swap `credentials` call FAILED. The stored `.env` then held only the three operator settings and the container key: the four contract switches were gone, and `verify` refused (`DeployError`). Cause: the `credentials` operation replaced the file and restarted without re-running the contract's configure step (`harden-config.py` merges the switches). **Fix:** stop, store, `backend.configure(current)`, restart, verify. If configure fails, the previous file is restored (with its owner) before restarting, so the gateway never starts without the switches. Unit test covers the order and the restore. 83 tests PASS. Before asking for another attended run, the agent runs the same path unattended in a throwaway VM with **dummy** credentials (two rotations, verify, switch names).
- **Dummy-credential rotation check PASS** (unattended, agent-run, throwaway VM, synthetic credentials only): install, commission, enroll, credentials, deploy (52.9 s) and two `credentials` rotations (28.8 s) each returned `restarted`, `verify` PASS and kept all four contract switches plus `API_SERVER_KEY`. The check first replaced the operator's r14 VM (owned pipeline role), which also stopped the operator's bot in it. **Next (operator):** rerun the attended live qualification on this exact tree.
- **Run r15 — attended live qualification PASS, all seven gates** (`runs/20261002T024125Z`; `qualification.json` `fc01102da1c6c9a3a9d338d434741b5b995a9a06578e56c8a07efb7ce30ab1f8`, artifact `8c03e71ae69165f6…`, release receiver `cbfe4c3b…`). Every stage PASS, including **application 212.3 s** with operator-observed answers: `uname -sr` answered; `rm -rf /tmp/hermes-approval-check` stopped for approval and did not run after denial; no reply while the allowlist excluded the operator. Restore PASS rests on the recorded no-off-host-backup waiver. The agent confirmed the candidate identity equals the evidence and that no source file changed since qualification. The VM was removed on PASS, so the bot token is free. **Next (operator):** `bundle --evidence`, the private controller update on 10.0.30.10, `credentials`, `deploy`, `verify`.
- **Production deployment on 10.0.30.10 (2026-10-02):**
  - **Release:** the operator signed `hermes-qualified.tar` (the agent verified the signature, the evidence identity `8c03e71a…`, all seven gates PASS and production-policy acceptance).
  - **Controller update:** applied privately (`BOOTSTRAPPED`, receiver `cbfe4c3b…`, matching the release); preflight stayed PASS with commissioning PASS. Credentials STORED.
  - **Deploy:** the operator's `deploy` printed `STOP: BrokenPipeError`, but the server committed the transaction (previous none, candidate `8c03e71ae69165f694f25f25c0abb4bd67ba76b927452932766a837d7a0930c8`; import 59.8 s, configuration 3.5 s, restart 1.0 s, verification 6.1 s). Read-only `status` shows that release current, and `verify` PASS (credential-free runtime). The operator's immediate `verify` had overlapped the still-running transaction. `/var` is 4% used and `/home/hermes` 5%.
  - **Defect (client):** `remote()` treats a broken pipe after the server stops reading the stream as failure and kills the SSH session instead of waiting for the result. Fix in the next release, together with surfacing remote `STOP:` reasons and reports with status FAIL. Changing `productionctl.py` now would make the release's receiver identity differ from the installed one.
  - **Open follow-ups:** client fix; production Kickstart disables Cockpit; no off-host backup (operator decision, recorded waiver); operator backs up `~/hermes-production` (escrow, signing key, escrow ciphertext); Git delivery not requested.
- **Follow-up fixes (operator request "fix the two small issues now", 2026-10-02):**
  - **Client:** `productionctl.remote()` uses an unbuffered stdin and tolerates `BrokenPipeError` when the server stops reading, then waits for and uses the server's exit and result. A non-zero exit returns a `status: FAIL` report when present (a failing remote `preflight` is readable), otherwise raises `remote:<last sanitized STOP reason>`, falling back to `remote-operation-failed`. A regression with a stand-in `ssh` that never reads an 8 MiB upload covers result, refusal, FAIL report and an unsanitized-stderr fallback.
  - **Installer:** the Kickstart uses `firewall --enabled --service=ssh --remove-service=cockpit` and `services --enabled=sshd,chronyd --disabled=cockpit.socket`. The pipeline's `enroll` stage now requires `cockpit.socket` disabled and inactive and no `cockpit` firewall service in the VM.
  - Runbook updated (Cockpit, CLI behavior, controller-update commands). 84 tests PASS.
  - **Production impact:** none now. The client fix runs locally and works against the installed receiver. The next release changes the receiver identity, so it needs the documented controller update before deploy. The production host's Cockpit was already disabled by hand. Validation: canonical offline gate and an unattended full pipeline run on this tree.
