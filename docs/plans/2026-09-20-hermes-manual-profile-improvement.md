# Hermes Fedora 44 manual-profile improvement

Record state: **COMPLETED for the offline implementation (T01–T07).** Every runtime, lab, credential
and production gate remains **NOT RUN** and is delegated to the Gate 2 record. This file is the
historical execution record for the repository implementation; the authoritative current runtime
status is [the Gate 2 plan](2026-09-20-hermes-manual-gate2-lab-plan.md) §0, and the review findings
against HEAD `2340887` are tracked in
[the review-corrections record](2026-09-20-hermes-manual-review-corrections.md).

## Approved baseline — preserve after approval

- Intended outcome: turn the existing two-container Hermes manual profile into a
  repeatable, fail-closed, testable deployment without replacing it or inflating
  the control count.
- Approved scope: repository implementation and offline validation in
  `/var/home/aicloudopspecial/code/repos/mikrotik` on a feature branch; the
  narrow CLI/Telegram text, terminal/file and approval-gated memory profile; the
  existing offline worker and pinned gateway; optional PCR7 boot retained as a
  separately authorized profile.
- Out of scope and constraints: no lab resource creation, no target access, no
  credential provisioning, no provider or messaging calls, no privileged host
  change, no reboot, no disk/TPM operation, no commit, no push, no publication,
  no changes to controller/unattended certification policy, and no custom
  SELinux policy, secrets broker or signed-UKI work.
- Acceptance criteria: the repository encodes the approved architecture, the new
  offline suite passes, existing repository gates still pass, and the run stops
  with a reviewed diff plus an exact lab authorization request.
- Approval date and timezone: 2026-09-20, America/Bogota (date only recorded).
- Approval reference: approved plan in this session (plan-mode approval of
  "Fedora 44 Hermes manual-profile improvement plan").
- Authorized actions and boundaries: write under the Hermes repository on branch
  `codex/hermes-fedora44-manual-review`; run offline tests and syntax checks;
  read public documentation and public image metadata. Stop before any action
  that needs a target, a credential, money, privileges, or publication.

## Tasks

| ID | Task and dependencies | Progress | Gate and expected result | Gate status | Evidence / docs / next action |
| --- | --- | --- | --- | --- | --- |
| T01 | Canonical record, shared library, configuration contract, manifest, offline suite; dependencies: none | ✅ DONE | `bash tests/test-hermes-manual-profile.sh` runs and reports the intended failures without touching a target | ✅ PASS | Suite written first and observed red (159 passed / 116 failed); see T01 evidence |
| T02 | Safe execution: inspect-by-default mutating helpers, rc capture through `tee`, no predictable temp executables, locks, host binding; dependencies: T01 | ✅ DONE | Suite sections "No predictable temporary executables", "Failure propagation through tee", "Mutation is explicit", "Gate ordering" and "Inspection is privilege-free" pass | ✅ PASS | All helpers converted; `tpm-enroll.sh` defaults to preflight; 12 helpers verified inspect-only as a non-root user |
| T03 | Pinned configuration and credential handling; dependencies: T01 | ✅ DONE | Suite "Configuration contract" passes; synthetic-canary checks added | ✅ PASS | Contract-driven posture; a real bug was caught and fixed (see decisions) |
| T04 | Repeatable worker image selection, trust-pin preservation, shim policy, service-state restoration; dependencies: T02 | ✅ DONE | Suite "Release identity" and "Transport trust policy" pass; M02 no longer mutates the live pin | ✅ PASS | Disposable client copy; pin verification; prior service state restored on both paths |
| T05 | Backup/restore and optional boot safeguards; dependencies: T02 | ✅ DONE | Boot preflight is non-mutating; restore path stops on failure and refuses to keep a healthy service in a changed state | ✅ PASS | `m04-backup`, `m04-postboot-probe`, `tpm-enroll`, `fallback-wipe` reviewed |
| T06 | Documentation: contract document, guide/runbook corrections, README and contributor wiring; dependencies: T02–T05 | ✅ DONE | Suite "Documentation parity" passes; existing guide and rehearsal gates still pass | ✅ PASS | Contract document, staging unification, precedence correction |
| T07 | Final offline gate and authorization request; dependencies: T01–T06 | ✅ DONE | Full offline suite green; diff reviewed; lab request written | ✅ PASS | See final evidence and handoff |

## Evidence history

### T01 — offline suite written first (behavioural red)

- Command or review method and working directory: `./tests/test-hermes-manual-profile.sh`, repository root.
- Expected result: fail loudly on the defects the plan targets, so the corrections are verified rather than asserted.
- Actual result and status: **red** — 159 passed, 116 failed, exit 1. Failures covered the missing
  contract document, every helper's missing library sourcing, eight predictable `/tmp` Python helpers
  (six files), and missing mutation gating. Two failures were defects in the test itself and were
  corrected: a comment that mentioned `| tee` was read as a pipeline, and the library was expected to
  source itself.
- Checked files, artifact, or relevant state: `scripts/hermes/manual/**`, `tests/test-hermes-manual-profile.sh`.
- Documentation updated, or explanation of omission when it matters to a reviewer: not applicable at red.
- Sanitized evidence link, if needed: none.

### T02–T06 — corrections and final offline gates

- Command or review method and working directory: repository root.
- Expected result: every check passes, and no existing repository gate regresses.
- Actual result and status:
  - `./tests/test-hermes-manual-profile.sh` → **297 passed, 0 failed, 0 skipped** (exit 0).
  - `./tests/test-hermes-guide.sh` → **217 passed, 0 failed, 0 skipped** (exit 0).
  - `bash scripts/hermes/manual/boot/rehearse-clean-install.sh` → **REHEARSAL=PASS, failures=0, advisories=0**.
  - `bash -n` over all 31 manual shell artifacts and `ast.parse` over the six Python artifacts: pass (part of the suite).
  - `git diff --check main` → clean.
- Checked files, artifact, or relevant state: 31 modified files plus seven new files; see the final diffstat below.
- Documentation updated, or explanation of omission when it matters to a reviewer: contract document added;
  guide, runbook, manual README, contributor guide and root README updated; three superseded statements
  are marked as superseded with the reason.
- Sanitized evidence link, if needed: none.

Additional provenance when warranted:

- Timestamp with timezone: 2026-09-20, America/Bogota.
- Environment and relevant versions/configuration: Fedora Linux 44 Kinoite workstation
  (`44.20260918.0`), Bash 5.3.9, Python 3.14.7 with PyYAML, Podman 5.8.4 (generator dry-run only).
  ShellCheck, shfmt, markdownlint and Devbox are **not** installed, so lint, formatting and the
  Lefthook hooks were **not** run.
- Tested revision or artifact fingerprint, including relevant dirty/untracked inputs: branch
  `codex/hermes-fedora44-manual-review`; base commit `17d6415c8fe72d91d3c91e87e942e2a09b0d544e`;
  the whole change set was uncommitted at the time of these measurements and was subsequently
  committed as `2340887` (`feat(hermes): add the Gate 2 lab plan, kickstart automation and scoped
  grants`). The results above apply to that working tree; the commit identity is recorded separately.
- Diffstat: 31 modified files, 7 added files; the exact insertion/deletion totals are in `git diff --stat main`.

### Self-review pass — two defects found after the first green run

- Command or review method and working directory: a static ordering audit plus an actual non-root run of
  every deployment helper in inspect mode, repository root.
- Expected result: inspection should need no privileges, leak nothing, and write its log where the
  operator expects it.
- Actual result and status: the first green offline run was **not** sufficient. Two defects were found
  and fixed:
  1. **Wrong administrator accessor (behavioural, high impact).** `mp_admin_account` returned the
     account's *home directory*, and every helper then passed that value to `getent passwd` as if it
     were a name. The log path became `/hermes-*.out` (the `STOP: cannot create` message and the
     `Read-only file system` error were only visible because the helper was actually executed), and
     every `chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT"` named a nonexistent user. The library now
     exposes distinct `mp_admin_account` (name) and `mp_admin_home` (home) accessors with the reason
     recorded inline, and the suite asserts the two are different values.
  2. **Gate ordering (static).** `m02` took the operation lock before the apply gate, so merely
     inspecting needed root and a free lock; `m04-backup` created a private temporary directory before
     installing the cleanup trap, so inspection leaked a 0700 directory under `TMPDIR`. Both fixed, and
     two ordering invariants are now asserted for every helper.
- Post-fix behavioural result: **12 of 12** deployment helpers exit 0 with `INSPECT ONLY` as a
  non-root user, create **no** temporary directory, and write a mode-`0600` log in the configured
  administrator home (`log count: 12`). The suite now performs this run itself, because static greps
  cannot detect a wrong path or a leaked directory.
- Checked files, artifact, or relevant state: `scripts/hermes/manual/lib-manual-common.sh`, 17 callers,
  `m02-deploy-and-validate.sh`, `m04-backup.sh`, `tests/test-hermes-manual-profile.sh`.
- Documentation updated, or explanation of omission when it matters to a reviewer: the reasons for the
  split accessor are recorded as a comment at the definition, which is where the next reader will
  change it.
- Sanitized evidence link, if needed: none.

### Rehearsal gate recovery (failed attempt preserved)

- Command or review method and working directory: `bash scripts/hermes/manual/boot/rehearse-clean-install.sh`.
- Expected result: PASS, as before this change.
- Actual result and status: **FAIL** on the first attempt after implementation — `failures=8`. Cause was
  entirely this change set, and the gate was right:
  1. the runbook documented `--apply` for the enrollment helper while the helper's own flag grammar did
     not implement it (and `--preflight` was no longer documented);
  2. the deployment guide referenced two diagnostics that had been deleted;
  3. the guide advertised `HERMES_ADMIN` outside the boot-helper scope the gate reserves for it;
  4–8. the key helper failed its stubbed ownership fixture because the new host-identity requirement was
     not satisfied by the fixture — which masked the four ownership-order assertions behind it.
- Resolution: the enrollment helper gained a real flag grammar including `--apply`; the diagnostics were
  **restored and hardened** instead of deleted; the guide points at the contract document for account
  configuration instead of naming the variable; and the rehearsal fixture now supplies this machine's
  fingerprint, which strengthens the fixture's contract rather than bypassing it. Final result:
  **REHEARSAL=PASS, failures=0, advisories=0**.
- Checked files, artifact, or relevant state: `docs/HERMES_BOOT_CLEAN_INSTALL.md`,
  `docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md`, `scripts/hermes/manual/boot/tpm-enroll.sh`,
  `scripts/hermes/manual/m05-gateway-diag*.sh`,
  `scripts/hermes/manual/provision-worker-client-key.sh`,
  `scripts/hermes/manual/boot/rehearse-clean-install.sh`.
- Documentation updated, or explanation of omission when it matters to a reviewer: yes — the runbook now
  keeps `--preflight` and `--inspect` explicit, and the deletion decision was reversed.
- Sanitized evidence link, if needed: none.

## Decisions and approved scope changes

| Date and timezone | Decision and reason | Approval reference when required | Affected tasks / evidence |
| --- | --- | --- | --- |
| 2026-09-20 America/Bogota | Keep the narrow offline profile; retain PCR7 as an optional profile rather than an application prerequisite. | User answer to the two plan questions in this session | T02–T06, boot profile scope |
| 2026-09-20 America/Bogota | Encode the reviewed posture in `profile-contract.yaml` so configuration, tests and documentation share one source of truth. | Approved plan (Group C) | T03, T06 |
| 2026-09-20 America/Bogota | **Superseded mid-implementation:** deleting the two superseded diagnostics. The clean-install rehearsal asserts that every helper the deployment guide names exists, so deleting them would have removed a gate's protection. They were restored and hardened instead. | Approved plan Group A (preserve existing gates) | T02, rehearsal recovery |
| 2026-09-20 America/Bogota | Use the pinned image's **real** configuration keys (`toolsets`, `platform_toolsets`) rather than a friendlier `tools:` wrapper. The wrapper was merged verbatim and never translated, so the broad default allowlist would have remained in force while the suite still passed a verbatim comparison. The suite now asserts the effect. | Approved plan Group C ("inspect the resolved tool registry"; do not copy unsupported keys) | T03 |
| 2026-09-20 America/Bogota | Boot helpers now require the whole `scripts/hermes/manual/` tree to be staged, because they source the shared library one level up. The runbook, guide and manual README were updated together. | Approved plan Group B | T02, T06 |
| 2026-09-20 America/Bogota | The key helper's ownership order is deliberately unchanged and its rehearsal fixture now supplies the host fingerprint, because the new binding is stricter, not looser. | Approved plan Group B/D | T02 |
| 2026-09-20 America/Bogota | Split `mp_admin_account` (name) from `mp_admin_home` (home) after the behavioural run showed the single accessor produced a root-level log path and an invalid `chown` target. A static suite could not have caught this. | Approved plan Group B | T02 |
| 2026-09-20 America/Bogota | Add gate-ordering invariants (apply gate before lock; cleanup trap before private state) and run one helper in inspect mode inside the offline suite. | Approved plan Group B ("inspection mode as the default") | T02 |

## Handoff / closure

- Current outcome: repository implementation and **all authorized offline gates pass**. The profile now
  has one reviewed configuration contract, one shared safety library, fail-closed accounting
  (`FAIL` fails; `UNVERIFIED` is incomplete; a run that asserts nothing fails), inspect-by-default
  mutation with host binding, no predictable root-owned temporary helpers, trust pins that are verified
  rather than overwritten, service-state restoration, an explicit release manifest, and an offline
  suite wired into the contributor guide and root README.
- Remaining gates and blockers: **every runtime, lab, credential and production gate is NOT RUN.**
  No target was contacted, no container was started, no lab resource was created, and no credential was
  provisioned. `PRODUCTION_TARGET` and `LAB_TARGET` remain unset. Specifically unverified:
  - resolved toolset/allowlist behaviour on the running image (including `toolset_allowed_for_platform`);
  - rootless mappings, SELinux labels, capability and seccomp posture, and resource limits at runtime;
  - worker IPv4/IPv6 egress isolation with a present probe tool, not an absent one;
  - the file-synchronization canary path and the credential-merge failure paths;
  - restart/relabel races, disk-full behaviour, and interrupted-run recovery;
  - update/rollback and semantic restore of a real profile;
  - the optional PCR7 boot chain, passphrase fallback and cold-start acceptance on hardware.
- Material limitations:
  - ShellCheck, shfmt, markdownlint and the Lefthook hooks were not run (Devbox absent). The suite
    substitutes `bash -n`, `ast.parse` and `git diff --check`, which are weaker.
  - `tests/test-hermes-links.sh` could not run: it requires `rg`, which is absent, and it is documented
    as an optional network-dependent check rather than a standing gate. As a substitute, every relative
    Markdown link in the seven documentation files this change touches was resolved directly —
    **58 links checked, all resolve**.
  - Nothing was committed or pushed. No promotion record, certification or signed release was created
    or implied; the controller and unattended tracks were not modified.
  - The public image metadata check corroborates the configured digest against release `v2026.9.11` and
    revision `939e45c…`, but the upstream tag is unsigned and no signature verification was performed.
- Gate 2 plan: [Gate 2 credential-free lab plan](2026-09-20-hermes-manual-gate2-lab-plan.md) —
  **ACTIVE**, approved 2026-09-20; Phases 0–5 complete, Phases 6–7 and Gate 3 **NOT RUN**. (The
  earlier "AWAITING APPROVAL" label in this record is superseded.)
- Review corrections: [Gate 2 review corrections](2026-09-20-hermes-manual-review-corrections.md) —
  fixes for the findings raised at HEAD `2340887`, with offline evidence only.
- Exact next action: request authorization to **resume Phase 6 on the retained fixture**
  `lab-hermes-manual-r1` (the review-corrections record lists the credential-free sequence). Provider
  or messaging credentials and the optional encrypted/TPM profiles each need separate authorization.
- **Gate 2 progress (recorded 2026-09-20):** Phases 0–5 completed on a fresh fixture `lab-hermes-manual-r1`:
  capacity gate PASS, media downloaded and signature-verified, fixture created, unattended kickstart install,
  Phase 4 baseline PASS (11/11) with `/home/hermes` confirmed as a separate XFS filesystem, and Phase 5 host
  preparation PASS (25/25) with key-only SSH enforced and rootless Podman verified. **Phases 6–7 and Gate 3
  were not run**, at the user's instruction to stop after Phase 5. The fixture is retained. The console
  verification of the guest host key (D-04) is still outstanding and must not be treated as done.
- Final state: COMPLETED (offline implementation T01–T07); runtime gates delegated and NOT RUN.
