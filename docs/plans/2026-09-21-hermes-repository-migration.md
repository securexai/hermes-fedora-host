# hermes-fedora-host — complete Hermes repository migration

Record state: CORRECTIONS APPLIED — pending independent re-review

> An independent review of the uncommitted working tree returned
> **CHANGES REQUIRED** with nine findings (R1–R9). A second independent re-review
> then returned **CHANGES REQUIRED** again, confirming R6 (R6a/R6b/R6c) and R4 as
> still blocking and adding integration-accounting and wording follow-ups. The
> completion claims in the task table below are **superseded** by
> "Post-review corrections" and "Second independent re-review corrections" at the
> end of this record. The migration is **not** a completed, reviewed artifact
> until a fresh payload-identity-bound re-review passes. The next action is that
> fresh review; this record does not mark the migration accepted or runtime-ready.

## Approved baseline — preserve after approval

- **Intended outcome:** `hermes-fedora-host` becomes the self-contained home for
  Hermes installation/deployment code, documentation, tests and sanitized
  historical artifacts, developed and validated against the dev-toolbox `infra`
  profile — with no dependency on sibling checkouts for active Hermes paths.
- **Approved scope:** the user selected **"Complete repository migration only"**
  on 2026-09-21: import Hermes installation/deployment code, docs, tests and
  sanitized evidence; preserve the installed instance and all source
  repositories unchanged.
- **Out of scope and constraints:**
  - No live-host operations: no SSH to deployment targets or guests, no
    deployment, no VM lifecycle, no provider calls, no credential provisioning,
    no TPM/installed-grant changes.
  - `mikrotik`, `fedora-virtualization-host` and `dev-toolbox` are left
    unchanged, including their dirty and untracked work.
  - No commits, pushes, merges, or PR changes without a separate request.
  - "Artifacts" means versionable source, manifests, templates and sanitized
    evidence — not VM disks, backups, container storage, private keys,
    credentials, or live application state.
  - Runtime acceptance is not established by any gate in this record.
- **Acceptance criteria:**
  1. Every selected source artifact is accounted for in the migration manifest,
     and active Hermes paths have no undeclared dependency on sibling checkouts.
  2. Existing manual-profile regressions still pass; restored offline
     deployment/guide/spec/Python gates pass, or the migration remains
     explicitly incomplete.
  3. Tooling verification, secret scanning and applicable hook checks pass
     without unrecorded evidence changes.
  4. Documentation identifies current entrypoints, historical results,
     unsupported paths, runtime prerequisites and remaining gates accurately.
  5. Final diff review confirms no lost corrections, leaked secrets, unrelated
     source-repo changes, or live-host operations.
- **Approval date and timezone:** 2026-09-21, America/Bogota (UTC−05).
- **Approval reference:** the plan presented in this session and approved by the
  user, together with the scope answer "Complete repository migration only
  (Recommended)".
- **Authorized actions and boundaries:** creating a local migration branch,
  copying source working-tree bytes into `hermes-fedora-host`, authoring and
  adapting repository files, running offline checks inside the existing
  `dev-infra-hermes` Toolbox. Not authorized: runtime/deployment execution,
  credential access or provisioning, git commits or pushes, or modifying other
  repositories.

## Tasks

| ID | Task and dependencies | Progress | Gate and expected result | Gate status | Evidence / docs / next action |
| --- | --- | --- | --- | --- | --- |
| T01 | Capture the migration baseline: source/destination/toolbox identities, dirty-input hashes, mode and image fingerprints; classify the whole candidate set and resolve transitive local dependencies. Deps: none | ✅ DONE | Every candidate classified IDENTICAL / DIFFERENT / MISSING; every difference explained; dependency gaps resolved or recorded | ✅ PASS | 302 candidates: 131 identical, 17 different (16 = exact `shfmt` reformat, 1 = trailing-newline drift), 154 missing; image chain and container IDs re-verified. See "Baseline reconnaissance" |
| T02 | Import the missing Hermes assets with resolved dependencies, preserving all reviewed corrections and destination-only changes. Deps: T01 | ✅ DONE | Destination contains every in-scope artifact; no source correction lost; no excluded path present | ✅ PASS | 168 files added (163 imported + 5 authored), 10 adapted, manifest at `docs/migration-manifest.txt` (311 entries, 0 hash mismatches) |
| T03 | Align dev-toolbox integration and authoritative documentation: `infra` Dev Container, relocation-safe instructions, README/guides, hook-parity correction, migration manifest and provenance. Deps: T02 | ✅ DONE | Active docs name real entrypoints and no obsolete checkout path; parity map contains no unsupported claim | ✅ PASS | Dev Container switched to `dev-infra`; `AGENTS.md`, `docs/ENVIRONMENT.md` authored; README/CONTRIBUTING/hook-parity corrected; 10 adapted files recorded with reasons |
| T04 | Restore and run the safe offline gate set, with an explicit allowlist separating offline from network/privileged suites. Deps: T02, T03 | ✅ DONE | Baseline verify, extensions, hooks, secret scan and every offline suite pass, or the migration stays incomplete | ✅ PASS | Offline entrypoint 10/10 suites PASS; pre-commit 17/17 hooks; 341-file explicit pass; extensions validator PASS; dev-toolbox infra verify PASS |
| T05 | Final review and close-out: diff audit, evidence preservation check, limitations and exact next action. Deps: T04 | ✅ DONE | No lost correction, leaked secret, live-host operation, or unrecorded evidence change; record finalized | ✅ PASS | Manifest re-verified (311/311); source repos unchanged; no commits; no excluded path or secret literal present |

## Evidence history

### Baseline reconnaissance (read-only)

- **Command or review method and working directory:** `git rev-parse`,
  `git status --porcelain`, `sha256sum`, `git ls-files`, path classification and
  dependency grep from `/var/home/aicloudopspecial/code/repos/DS-Workspace`, plus
  `podman image inspect` / `podman container inspect`.
- **Expected result:** source, destination and environment identities are known
  and stable before any copy.
- **Actual result and status:** ✅ captured.
  - Destination `hermes-fedora-host` @ `hermes/hermes-foundation`
    `de8fb8b`, clean, in sync with `origin`. Migration branch
    `hermes/hermes-repository-migration` created from it.
  - Source `mikrotik` @ `codex/hermes-fedora44-manual-review` `130bf8f2…` with
    **14 modified tracked files, 0 untracked** (excluding `__pycache__`). The
    reviewed corrections exist only as that working-tree delta; copying HEAD
    alone would lose them.
  - Environment baseline re-verified: base `72f3583d…` → python `965ea02e…`
    (parent `72f3583d…`) → infra `af934ead…` (parent `965ea02e…`); container
    `dev-infra-hermes` runs `af934ead…`. `dev-toolbox` is still local-only (no
    remote), dirty at `c0f0889`, so the profile standard cannot be pinned by a
    public commit.
- **Checked files, artifact, or relevant state:** the full Hermes candidate set
  (302 paths), `PROVENANCE.md`, `docs/extraction-manifest.txt`, image labels.
- **Documentation updated:** this record.
- **Sanitized evidence link, if needed:** none.

### Candidate classification

- **Command or review method and working directory:** path-pattern scope over
  `git ls-files` in both repositories, then per-file `sha256sum` comparison.
- **Expected result:** each candidate is identical, an explained difference, or
  missing.
- **Actual result and status:** ✅ 302 candidates — **131 IDENTICAL**,
  **17 DIFFERENT**, **154 MISSING**.
  - All 16 shell files differing between source and destination are **exactly**
    the documented `shfmt -i 2 -ci -bn` reformat: for each, the destination file
    is byte-identical to `shfmt` output of the source file
    (`shfmt --version` 3.7.0, inside `dev-infra-hermes`). No correction was
    lost.
  - The 17th difference is
    `docs/plans/2026-09-20-hermes-manual-review-corrections.md`: one trailing
    blank line removed by the repository formatter, so the extracted copy no
    longer matches the SHA-256 `f838188c…` that `PROVENANCE.md` records for the
    canonical record. Recorded as a defect to resolve in T02 (see decisions).
  - All 14 source dirty files were traced: 5 identical, 8 reformat-only, 1
    authored here (`docs/CONTRIBUTING.md`), and the 14th is the corrections
    record above. Every reviewed correction is present in the destination.
- **Checked files, artifact, or relevant state:** `mikrotik` candidate paths,
  destination equivalents.
- **Documentation updated:** this record.
- **Sanitized evidence link, if needed:** none.

### Dependency resolution

- **Command or review method and working directory:** reference extraction
  (`$REPO_ROOT`/`$SCRIPT_DIR`/literal repo-relative paths) across the 154 missing
  files, then existence checks against the post-import union.
- **Expected result:** every referenced local path is either in scope, or
  recorded as a genuine gap.
- **Actual result and status:** ✅ resolved, with findings that widen the import
  scope:
  - `tests/test-hermes-guide.sh` requires `docs/VM_TESTING_GUIDE.md` (Hermes/VM
    focused) and `AGENTS.md`/`lefthook.yml`, which do not exist here.
  - `spec/vm/*` is required by `vm/lib-hermes-luks-console.sh` coverage and is
    therefore in scope, not just `spec/hermes/`.
  - `setup-ssh-key-only.sh` (root and `scripts/hermes/manual/`) is referenced by
    `tests/test-hermes-manual-profile.sh`, `rehearse-clean-install.sh` and
    `m01-host-prepare.sh`; the sibling `docs/plans/2026-09-12-fedora-ssh-key-only.md`
    and its evidence JSON are in scope with it.
  - `spec/hermes/fixtures/` does **not** exist in the source repository, so the
    "must not call ssh" examples in `deploy_spec.sh` currently pass trivially.
    Recorded; addressed in T04.
  - Dangling references in source docs (`docs/HERMES_FROM_SCRATCH.md`,
    `docs/research/HERMES_AGENT_HARDENING.md`, `docs/plan-execution.md`,
    `scripts/diff_docs.py`, `scripts/.cmd.sh`) are absent from the source
    repository too, so they are pre-existing source gaps, not migration gaps.
  - `docs/user-guide/*`, `docs/guide/*`, `docs/reference/*` matches are
    references to upstream Hermes product documentation, not this repository.
- **Checked files, artifact, or relevant state:** 124 distinct referenced local
  paths.
- **Documentation updated:** this record; to be consolidated in the migration
  manifest.
- **Sanitized evidence link, if needed:** none.

### T02 — import and evidence preservation (Gate 5)

- **Command or review method and working directory:** `cp` of source working-tree
  bytes with source-index file modes, then per-file SHA-256 comparison; from
  `/var/home/aicloudopspecial/code/repos/DS-Workspace`.
- **Expected result:** every in-scope artifact present and byte-identical to the
  reviewed source, with no excluded path.
- **Actual result and status:** ✅ PASS.
  - 163 files imported; all 163 verified byte-identical to source immediately
    after the copy. 23 of them carry the executable bit from the source index.
  - The canonical correction record was restored byte-for-byte after formatter
    drift, so its hash again equals the `f838188c…` value that `PROVENANCE.md`
    records.
  - Excluded paths confirmed absent: `.mcp.json`, `.claude/settings.local.json`,
    `devbox.json`, `devbox.lock`, source `AGENTS.md`/`CLAUDE.md`, `lefthook.yml`.
    No source `__pycache__` was imported (the `__pycache__` present under
    `.venv/` is gitignored generated bytecode).
  - No code file references a sibling checkout; no `devbox` or `dev-toolbox`
    dependency remains in migrated shell or Python code after T03.
- **Checked files, artifact, or relevant state:** the 163 imported paths and
  `docs/migration-manifest.txt`.
- **Documentation updated:** this record; `docs/migration-manifest.txt`.
- **Sanitized evidence link, if needed:** `docs/migration-manifest.txt`.

### T03 — environment and documentation alignment

- **Command or review method and working directory:** targeted edits plus a
  repository-wide scan for `devbox`, `lefthook` and absolute checkout paths.
- **Expected result:** active instructions describe the real environment and
  resolve; historical records stay intact.
- **Actual result and status:** ✅ PASS.
  - Dev Container image moved from `dev-base` to `dev-infra`, matching the
    project profile.
  - Authored `AGENTS.md` and `docs/ENVIRONMENT.md`; rewrote `README.md` as the
    entrypoint; corrected `docs/CONTRIBUTING.md` and `docs/hook-parity.md`.
  - The parity map's stale claim that `test-hermes-guide` was N/A is replaced by
    its actual successor wiring, and the ShellSpec row now reflects that the
    specs run.
  - Ten migrated files were adapted and each is recorded with a reason in the
    manifest: nine for the Devbox→Toolbox translation, checkout-path correction
    or environment-dependent skip, and `hermes-certify-vm.sh` for its offline
    test block.
  - The `docs/plans/2026-09-12-fedora-ssh-key-only.md` personal-skill command in
    `vm/DEPLOYMENT_TASKS.md` is now recorded as NOT RUN rather than a command
    that cannot resolve.
- **Checked files, artifact, or relevant state:** `README.md`, `AGENTS.md`,
  `docs/ENVIRONMENT.md`, `docs/CONTRIBUTING.md`, `docs/hook-parity.md`,
  `.devcontainer/devcontainer.json`, `.pre-commit-config.yaml`,
  `.markdownlint-cli2.yaml`, `.gitignore`, and the ten adapted files.
- **Documentation updated:** all of the above.
- **Sanitized evidence link, if needed:** `docs/migration-manifest.txt`.

### T04 — restored offline gates

- **Command or review method and working directory:** `bash
  toolbox/run-offline-checks.sh`, `pre-commit run --all-files`, an explicit
  `pre-commit run --files` over every tracked and untracked path,
  `toolbox/verify-extensions.sh`, and the dev-toolbox
  `scripts/verify.sh infra dev-infra-hermes`, all inside `dev-infra-hermes`.
- **Expected result:** every offline suite runs and passes; hooks and secret
  scanning pass without rewriting preserved evidence.
- **Actual result and status:** ✅ PASS.
  - `toolbox/run-offline-checks.sh` exit 0, **10/10 suites**: manual profile
    358/0, manual review 142/0, backup 43/0, configure 64/0, contract 30/0,
    m01-tempdir 9/0, clean-install rehearsal `REHEARSAL=PASS`, guide and
    deployment tree 219/0, ShellSpec 138 examples 0 failures, Python suites
    `Ran 446 tests … OK (skipped=5)`.
  - `pre-commit run --all-files` exit 0 with all **17 hooks Passed**, and the
    explicit 341-file pass exit 0 as well. A pre/post hash snapshot proved **no
    file was rewritten**.
  - `toolbox/verify-extensions.sh` exit 0; dev-toolbox
    `verify.sh infra dev-infra-hermes` printed `PASS`.
  - This closes the previous milestone's N/A decisions for the guide suite and
    the deployment ShellSpec suite, and wires in the migrated Python suites for
    the first time.
  - Two individual tests assert the presence of `guestfish` (libguestfs). The
    Toolbox `infra` profile deliberately excludes VM runtime tooling, so those
    tests now skip with an explicit reason instead of erroring; they still assert
    on a host that has libguestfs. Control run: the same two errors occur in the
    unmodified source tree, so this is a pre-existing environment gap, not a
    migration regression.
  - `tests/test-hermes-e2e-vm.sh` and `tests/test-hermes-links.sh` are
    deliberately not run (real VM lifecycle; network fetches). They are imported
    and recorded, not silently dropped.
  - `spec/hermes/fixtures/` was absent in the source repository, which made three
    "must not contact a host" examples vacuous. A fixture `ssh` that records the
    attempt was added; a negative control confirmed it creates the marker when
    invoked, and the suite passes with no marker created.
- **Checked files, artifact, or relevant state:** the whole migrated tree.
- **Documentation updated:** `docs/CONTRIBUTING.md`, `docs/hook-parity.md`,
  `toolbox/run-offline-checks.sh`, this record.
- **Sanitized evidence link, if needed:** none.

### T05 — final audit

- **Command or review method and working directory:** `git status`,
  `git rev-parse`, `git diff --stat`, manifest re-verification with
  `sha256sum -c`, and secret/excluded-path greps from the workspace root.
- **Expected result:** no lost correction, leaked secret, source-repo change or
  live-host operation; manifest accurate.
- **Actual result and status:** ✅ PASS.
  - `docs/migration-manifest.txt` re-verified: **311 entries, 0 mismatches**
    (154 IMPORTED, 130 PRESENT, 16 REFORMAT_ONLY, 1 RESTORED, 10 ADAPTED).
  - Source repositories unchanged: `mikrotik` still `130bf8f2` with 14 modified
    / 0 untracked; `dev-toolbox` still `c0f0889` with the same dirty set;
    `fedora-virtualization-host` untouched.
  - No commit, push or merge: the migration branch is 0 commits ahead of
    `hermes/hermes-foundation`. 168 files added, 10 tracked files modified.
  - No credential literal or private key found in the destination tree; no
    excluded artifact present.
- **Checked files, artifact, or relevant state:** the full destination diff.
- **Documentation updated:** this record.
- **Sanitized evidence link, if needed:** none.

## Migration manifest

### In scope — import

| Group | Content |
| --- | --- |
| Hermes entrypoints | `hermes-deploy.sh`, `hermes-certify-vm.sh`, `hermes-remediation-wizard.sh`, `hermes-simple-deploy.sh` |
| Guides | `hermes-fedora-server-install-guide.html`, `secure-hermes-installation-plan.html`, `docs/VM_TESTING_GUIDE.md` |
| Libraries | `scripts/hermes-wizard-lib.sh`, `scripts/remaining-lab-preflight.py`, `scripts/hermes/**` (incl. `unattended/`, `selinux/`, `simple/`, `wrappers/`, `manual/`) |
| Specs | `spec/spec_helper.sh`, `spec/hermes/**`, `spec/vm/**`, `.shellspec` |
| Tests | `tests/test-hermes-*.sh`, `tests/test_hermes_*.py`, `tests/test_remaining_preflight.py`, `tests/check_ssh_key_only_docs.py`, `tests/test_ssh_key_only.py`, `tests/lib-test-helpers.sh`, `tests/Containerfile.e2e`, `tests/Containerfile.sshd` |
| VM | `vm/**` (12 files) |
| Docs | `docs/HERMES_*`, `docs/*TPM*`, `docs/*SELINUX*`, `docs/plans/*hermes*`, `docs/archive/*hermes*`, `docs/plans/evidence/**` |
| Host helper | `setup-ssh-key-only.sh`, `setup-ssh-key-only.md`, `docs/plans/2026-09-12-fedora-ssh-key-only.md`, `docs/plans/evidence/2026-09-12-fedora-ssh-key-only.json` |

### Out of scope — excluded, with reason

| Content | Reason |
| --- | --- |
| `network/`, `kubernetes/`, RouterOS/VLAN/Nix tests and scripts | Unrelated components that remain in the source repository |
| `tests/test-hermes-e2e-vm.sh` requires live VM lifecycle | Imported as a *non-executed* live suite; never run in this phase (recorded, not gated) |
| `devbox.json`, `devbox.lock` | Retired Devbox environment; replaced by the dev-toolbox `infra` profile |
| `.mcp.json`, `.claude/settings.local.json` | Credential-bearing local configuration; never extracted |
| `AGENTS.md`, `CLAUDE.md` (source) | Source-repository guidance; this repository authors its own |
| `.gitignore`, `.markdownlint-cli2.yaml`, `lefthook.yml` | Destination already has adopted equivalents; Lefthook is retired |
| `__pycache__/` | Generated bytecode, not source |
| VM disks, backups, container storage, private keys, credentials, live state | Operational artifacts, not repository content |

## Decisions and approved scope changes

| Date and timezone | Decision and reason | Approval reference when required | Affected tasks / evidence |
| --- | --- | --- | --- |
| 2026-09-21 −05 | Scope is **complete repository migration only**; the installed instance and live reconciliation are a separate later phase | User scope answer "Complete repository migration only (Recommended)" | All tasks |
| 2026-09-21 −05 | `spec/vm/**` and `docs/VM_TESTING_GUIDE.md` enter scope because imported `vm/` code and the guide suite reference them | Implementation detail of the approved "resolve transitive dependencies" requirement | T02 |
| 2026-09-21 −05 | The corrections record's trailing-newline drift is resolved by restoring byte-identical evidence content and protecting preserved evidence from auto-fixing hooks, rather than by rewriting the recorded provenance hash | Preserves the approved requirement that evidence bytes are preserved unless sanitization is explicitly recorded | T02, T04 |
| 2026-09-21 −05 | Live suites (`tests/test-hermes-e2e-vm.sh`, device/VM lifecycle paths) are imported but never executed here; they are recorded as imported-not-gated | Approved boundary: no VM lifecycle, deployment, or live-host operations | T04 |
| 2026-09-21 −05 | `test-hermes-guide.sh` assertions that inspect source-repository structure (`lefthook.yml`, source `AGENTS.md`) are adapted to this repository's equivalents, preserving the gate's intent rather than deleting the checks | Supports the approved "no unsupported parity claims" requirement | T03, T04 |
| 2026-09-21 −05 | The two tests that assert `guestfish` presence now skip with an explicit reason instead of erroring, because libguestfs is VM runtime tooling that the approved scope keeps out of the development profile. A control run proved the failures are pre-existing in the source tree | Approved boundary: runtime tooling stays out of the dev profile; the plan forbids lowering a gate merely to pass, so the skip is narrow, documented, and still asserts where the tool exists | T04 |
| 2026-09-21 −05 | The missing `spec/hermes/fixtures/` directory is restored with a fixture `ssh`, so the suite's "must not contact a host" examples actually assert something instead of passing vacuously | Approved requirement to restore the ShellSpec deployment tests *and fixtures* | T04 |
| 2026-09-21 −05 | Migrated documents are excluded from the auto-fixing hooks and from `markdownlint-cli2` (which runs with `fix: true`), so their manifest hashes stay accurate; repo-authored documents remain fully linted | Preserves the approved evidence-preservation rule the earlier milestone established; extends it to the newly migrated documents | T03, T04 |

## Post-review corrections (2026-09-21, independent review R1–R9)

An independent review of the uncommitted working tree returned **CHANGES
REQUIRED** with nine findings. The working tree was preserved and corrected in
place; the completion claims in the task table are superseded by this section.

| Finding | Correction |
| --- | --- |
| R1 HIGH — test discovery was not a safe offline allowlist | `tests/offline_allowlist.txt` enumerates the exact reviewed `module.Class[.method]` unit targets and `tests/run-reviewed-suites.py` loads only those; discovery is no longer used. Real disk, boot-build, packaged-dracut, installed-guestfish-parser and real-sshd cases moved to `tests/integration_allowlist.txt`, each gated on `HERMES_RUN_INTEGRATION_TESTS=1` and run only through `toolbox/run-integration-checks.sh`, which reports NOT RUN and exits 3 when prerequisites are absent. The guestfish mocked command-construction assertion is no longer suppressed by a missing binary. |
| R2 HIGH — six referenced evidence artifacts omitted | The six `2026-09-07-*.json` Hermes evidence artifacts (`advisory-policy`, `guest-candidate`, `lab-uki-handoff`, `privileged-boundary-review`, `signed-installer-offline`, `unattended-offline`) were imported byte-identical with source modes and are manifest rows. The shared workstation assets (`tests/test-sshd-vm.sh`, `setup.sh`, `enable-sshd.sh`) are explicitly dispositioned as not migrated in `docs/VM_TESTING_GUIDE.md`, `vm/create-fedora-vm.sh`, `vm/setup-hypervisor.sh` and both Containerfiles instead of being silently referenced. |
| R3 HIGH — certifier replaced the execution model and weakened its gate | `hermes-certify-vm.sh` `run_offline_tests` now invokes an explicit Toolbox check-only gate: `toolbox run --container dev-infra-hermes bash -c 'bash toolbox/run-offline-checks.sh && bash toolbox/run-check-only-lint.sh'`. Host runtime operations stay on the host; ShellCheck runs at the certifier's original default severity over its reviewed set plus the repository's error-only gate over the whole working tree; `shfmt` and Markdown run check-only; no hook in the gate rewrites files. |
| R4 MEDIUM — the green secret hook did not cover the artifact | `toolbox/scan-secrets.sh` scans the full tracked+untracked working tree with `--validation=false`, after a fresh synthetic `ghp_` positive control. The staged-only nature of the `betterleaks` pre-commit hook is documented in `.pre-commit-config.yaml`, `docs/CONTRIBUTING.md` and the script itself. |
| R5 MEDIUM — active guides blanket-excluded from Markdown lint | The `docs/HERMES_*.md` wildcard and the VM-guide ignore are replaced by exact preserved-record paths. Maintained guides are linted check-only (`fix: false`); one MD013 finding in the manual profile contract was reflowed and one meaningful trailing space in the deployment guide is covered by a narrow, documented MD038 override instead of excluding the file. |
| R6 MEDIUM — provenance incomplete and partly stale | `toolbox/generate-migration-manifest.py` regenerates `docs/migration-manifest.txt` with destination/source hashes, executable modes, origin, state and per-file adaptation reasons; the header records the whole-artifact fingerprint, a complete inclusion/exclusion inventory and both dirty-input fingerprints. `docs/extraction-manifest.txt` is explicitly superseded (153 real rows, two known mismatches) without rewriting it, and `PROVENANCE.md` records the supersession and the full dev-toolbox dirty-input fingerprint. |
| R7 MEDIUM — instructions and environment assertions not executable | `docs/CONTRIBUTING.md` scope and suite tables corrected; `vm/DEPLOYMENT_TASKS.md` uses the repository-local ShellSpec and `pre-commit`-based Markdown; the VM guide and both HTML guides use explicit `HERMES_REPO`/`HERMES_MEDIA_DIR`/`HERMES_SSH_IDENTITY` variables; `.devcontainer/devcontainer.json` provisions through `toolbox/provision-environment.sh`; `toolbox/verify-extensions.sh` no longer synchronises anything (`UV_NO_SYNC=1`); README no longer calls the controller supported without the changed, unaccepted host/Toolbox integration caveat. |
| R8 LOW — SSH fixture not a durable isolated contract | `spec/hermes/fixtures/ssh` requires a harness opt-in and a marker inside a per-example `mktemp -d` scratch directory; `spec/hermes/deploy_spec.sh` sets up and tears down per example and adds committed positive (exit 255 plus marker) and negative (refusal without opt-in) controls. |
| R9 LOW — guide checks did not prove pre-push wiring | `tests/check_hook_wiring.py` parses the hook id/entry/stages/`always_run`/`pass_filenames` and the runner's real invocation lines, with eight negative controls exercised by `--self-test`; `tests/test-hermes-guide.sh` now calls the positive and self-test forms instead of grepping for strings that comments satisfy. |

## Second independent re-review corrections (2026-09-21)

A second independent review of the same uncommitted working tree returned
**CHANGES REQUIRED**, confirming that R6 remained unresolved and that R4's new
positive control was still defective. The working tree was preserved (no sibling
repository was modified) and corrected in place again.

| Finding | Correction |
| --- | --- |
| R6a — the tooling fingerprint still omitted build inputs | The dirty-input algorithm is now `hermes-dirty-input-v2`: `git status --porcelain -z --untracked-files=all` enumerates individual untracked files recursively, deletions are encoded as `kind=missing` with a deterministic record, and index-vs-worktree mode/type changes are captured. The manifest records the exact algorithm, accurate counts (`inputs`/`files`/`deletions`/`mode_or_type_changes`) and per-input audit lines. `profiles/Containerfile.infra` and `profiles/Containerfile.python` are now fingerprinted. The historical v1 fingerprint is retained and labelled as superseded, not silently redefined. |
| R6b — verification did not verify the claimed identity | `--verify` parses a strict identity block (exactly one of each key; unknown, duplicated, missing or malformed keys are rejected) and compares the recorded source/tooling/companion HEADs and dirty-input fingerprints against recomputed values instead of searching for a digest anywhere in the text. Destination modes are read from the filesystem, so a working-tree chmod is detected; index/worktree mismatches are audited. The manifest-excluding digest is described as a **payload identity**, not a binding of the manifest; the manifest's own SHA-256 is recorded separately in the handoff. Source-aware vs destination-only verification is stated explicitly. |
| R6c — companion origin resolution was incorrect | `COMPANION_SOURCES` now maps each `docs/reviews/**` artifact to its real `fedora-virtualization-host` source-relative path; the checkout root is `--companion`-configurable and derived from the current workspace. All four companion rows carry populated source hashes/modes. A missing known companion source fails generation/verification instead of degrading to "no source counterpart". |
| R4 — scanner errors counted as a passing positive control | `toolbox/scan-secrets.sh` now requires the documented findings exit code and inspects a redacted structured JSON report for the expected `github-pat` rule on the exact synthetic control file. A no-finding result, any other exit code, malformed output, an unrelated finding or an unredacted report fails the control; a full-tree scanner operational error also fails. `--validation=false` is retained on both invocations and scanner output is never echoed. |
| R1 integration accounting | `toolbox/run-integration-checks.sh` adds the OVMF variables template (`/usr/share/edk2/ovmf/OVMF_VARS.fd`) to its prerequisite list, and `tests/run-reviewed-suites.py` reports **NOT RUN** and exits 3 whenever any integration test was skipped. |
| R1 allowlist wording | `tests/offline_allowlist.txt` and `docs/CONTRIBUTING.md` now state the real boundary: a `module.Class` entry approves the class and so also runs `test*` methods added later; only `module.Class.method` entries pin one method. |
| Whitespace | The new trailing blank-line defect in `.markdownlint-cli2.yaml` was removed. The intentional historical EOF bytes of the canonical correction record are preserved untouched. |

Regression controls for the R6a/R6b/R6c/R4 defects were **added to the working
tree** as `tests/test_migration_provenance.py`, `tests/test_secret_scan.py` and
`tests/test_reviewed_runner.py` (they are untracked and HEAD is unchanged), and
are part of the reviewed offline allowlist. The later P2-1/P2-2 controls extend
the first two files.

### Dirty-file reconciliation correction

The **Candidate classification** text above states "5 identical, 8 reformat-only,
1 authored here (`docs/CONTRIBUTING.md`), and the 14th is the corrections record
above", which sums to 15 for 14 dirty files.

That sentence is retained as history and is **superseded**. The correct
reconciliation of the 14 dirty source paths is:

- 8 byte-identical,
- 5 exact `shfmt -i 2 -ci -bn` transformations,
- 1 authored contributor guide (`docs/CONTRIBUTING.md`),

= **14**. The canonical corrections record is one of the 8 byte-identical files,
not an additional 15th path. This was independently re-derived and re-confirmed by
the second review.

### Correction validation (first re-review — superseded)

> These results applied to the artifact before the second re-review corrections.
> They are retained as history; the current results are in the next subsection.

| Check | Result |
| --- | --- |
| `toolbox/run-offline-checks.sh` (aggregate) | **exit 0, 12/12 PASS** — manual profile 358/0/0; manual review 142/0/0; backup 43/0/0; configure 64/0/0; contract 30/0/0; m01-tempdir 9/0/0; clean-install `REHEARSAL=PASS`; guide/tree 220/0/0; ShellSpec 140 examples 0 failures; reviewed Python allowlist 443 tests OK (0 skips); secret scan PASS; manifest verify PASS |
| Reviewed offline Python allowlist | 443 tests, 0 skipped, 0 failures (was 446 discovered with 5 skips) |
| ShellSpec `spec/` | 140 examples, 0 failures (was 138; two committed fixture controls added) |
| Guide and deployment-tree suite | 220 passed, 0 failed (structural hook-wiring checks replaced two string greps) |
| `toolbox/run-check-only-lint.sh` | all gates PASS (ShellCheck default + error-only, `shfmt`, Markdown, nine read-only hooks) |
| `toolbox/scan-secrets.sh` | positive control detected; 0 findings across 348+ tracked/untracked files |
| `toolbox/generate-migration-manifest.py --verify` | matches the working tree (357 rows) |
| `toolbox/verify-extensions.sh` | PASS (ShellSpec 0.28.1, Ruff 0.16.8, ty 0.0.82, yamllint 1.38.0) |
| `toolbox/run-integration-checks.sh` | **NOT RUN** — prerequisites absent; exits 3 by design |

### Correction validation (second re-review — historical, superseded by the third pass)

All checks ran inside the existing `dev-infra-hermes` Toolbox with
`PYTHONDONTWRITEBYTECODE=1 UV_OFFLINE=1 UV_NO_SYNC=1 UV_NO_ENV_FILE=1
UV_PYTHON_DOWNLOADS=never`. No real integration, deployment, VM, SSH, provider,
credential, TPM or service operation was executed.

| Check | Result |
| --- | --- |
| New regression controls (red) | `tests/test_migration_provenance.py`, `tests/test_secret_scan.py`, `tests/test_reviewed_runner.py` run against the unchanged pre-correction disposable artifact: **33 tests, 23 failures + 1 error** — the controls detect the demonstrated defects |
| New regression controls (green) | same 33 tests against the corrected tree: **33 tests, OK (0 failures, 0 errors)** |
| `toolbox/run-offline-checks.sh` (aggregate) | **exit 0, 12/12 run invocations PASS** (counting convention: the entrypoint contains twelve `run` calls, each counted once) — manual profile 358/0/0; manual review 142/0/0; backup 43/0/0; configure 64/0/0; contract 30/0/0; m01-tempdir 9/0/0; clean-install `REHEARSAL=PASS`; guide/tree 220/0/0; ShellSpec 140 examples 0 failures; reviewed Python allowlist 476 tests OK (0 skips); secret scan PASS; manifest verify PASS (360 rows) |
| Reviewed offline Python allowlist | 476 tests, 0 skipped, 0 failures (+33 controls over the first re-review's 443) |
| Hook-wiring structural check | positive PASS; `--self-test` rejected all eight negative controls |
| `toolbox/run-check-only-lint.sh` | exit 0 — ShellCheck certifier set + error-only, `shfmt` check-only, check-only Markdown and nine read-only hooks all PASS |
| `toolbox/scan-secrets.sh` | exit 0 — redacted `github-pat` control on the exact synthetic file and a clean 361-file full-tree scan |
| `toolbox/generate-migration-manifest.py --verify` | source-aware PASS (360 rows); destination-only mode is reported explicitly when a checkout is absent, and identity is then **not** re-derived |
| `toolbox/verify-extensions.sh` | PASS (ShellSpec 0.28.1, Ruff 0.16.8, ty 0.0.82, yamllint 1.38.0) |
| `git diff --check` | exit 2 with only the preserved historical EOF exception at `docs/plans/2026-09-20-hermes-manual-review-corrections.md:779`; the new `.markdownlint-cli2.yaml` blank-line defect is removed |
| `toolbox/run-integration-checks.sh` | **NOT RUN** — prerequisites absent; exits 3 by design. The shared runner now also reports NOT RUN/nonzero for any skipped integration test |

The corrected payload identity and the manifest's separate SHA-256 are not written
inside this record: both would create a self-referential loop. The payload
identity is carried by `docs/migration-manifest.txt` itself (which excludes the
manifest), and the manifest's own SHA-256 is reported in the handoff and in the
next independent review request.

## Third independent re-review corrections (2026-09-22)

A third independent review confirmed that the R6/R4 counterexamples are rejected
and that the second correction pass was substantially effective. It recorded
**CHANGES REQUIRED** for two narrower robustness defects, an unresolved inventory
handoff claim and three non-blocking record items. They are corrected here; the
earlier fixes are preserved, not rolled back.

| Finding | Correction |
| --- | --- |
| P2-1 MEDIUM — source/tooling mode provenance still depended on Git's `core.filemode` setting | The dirty-input algorithm is now `hermes-dirty-input-v3`. Selection is no longer `git status`-only: the generator walks the Git index independently of `core.filemode` and includes every tracked input whose actual filesystem mode differs from the index, with the canonical `" M"` status. A mode-only `chmod` on an otherwise clean tracked input therefore changes the fingerprint even when Git reports the tree as clean. The superseded `hermes-dirty-input-v2` fingerprint and the historical v1 fingerprint are both retained in the identity block, so no earlier recorded value is silently redefined. |
| P2-2 MEDIUM — scanner report fields could still leak into logs | The report classifier now prints only fixed classifications and numeric counts. It never interpolates a `RuleID`, path, `Match`/`Secret` value or JSON error text into output; malformed reasons are fixed codes (`unreadable`, `empty`, `invalid-json`, `not-a-list`, `entry-shape`). Report bytes are decoded with `errors="replace"`, so a non-UTF-8 report cannot raise an uncaught decode error. Replacement decoding normalizes invalid bytes rather than rejecting every non-UTF-8 report: bytes that break JSON syntax fall through to `invalid-json`, while invalid bytes inside an otherwise valid JSON string are normalized and can still yield a parsed finding (it remains a finding, and its fields are still never logged). The shell prints fixed messages and only the expected rule constant (a script literal). Negative controls plant the script's own synthetic token in `RuleID`, in other report fields and in malformed or non-UTF-8 report bodies for both the control and full-tree scans. |
| Inventory digest discrepancy — the claimed 361-file inventory SHA-256 was not reproducible | The unreproducible claim (`79c1cfc4…`) is **withdrawn** and replaced by a recorded, recomputable inventory identity. `docs/migration-manifest.txt` now carries `inventory_algorithm`/`inventory_fingerprint`/`inventory_rows`/`inventory_excludes`, and `toolbox/generate-migration-manifest.py --inventory` prints the exact document so `--inventory \| sha256sum` reproduces it; `--verify` re-checks it. The manifest is excluded from the inventory for the same reason as the payload, so the complete artifact is the inventory identity **plus** the manifest's separately reported SHA-256. See `PROVENANCE.md`. |
| Non-blocking record cleanup | The current dev-toolbox baseline path in `PROVENANCE.md` is corrected to the `DS-Workspace` checkout (the capture-time path is retained as captured and annotated, not rewritten); the regression description now says the controls were "added to the working tree" rather than "committed"; and the aggregate claim's counting convention is corrected to twelve entrypoint `run` invocations. |

### Focused regression controls (third pass)

All commands ran inside the existing `dev-infra-hermes` Toolbox with
`PYTHONDONTWRITEBYTECODE=1 UV_OFFLINE=1 UV_NO_SYNC=1 UV_NO_ENV_FILE=1
UV_PYTHON_DOWNLOADS=never`.

| Check | Result |
| --- | --- |
| Red control: new controls against the unchanged pre-correction scripts | The P2-1 control (`test_clean_tracked_chmod_is_fingerprinted_when_git_ignores_modes`) fails against the pre-correction generator (3 failures + 1 error in that suite), and two P2-2 controls fail against the pre-correction scanner: `test_full_scan_rule_identifier_canary_is_not_echoed` (the synthetic token is echoed from `RuleID`) and `test_non_utf8_report_is_classified_not_crashed` (an uncaught decode traceback). The controls detect the demonstrated defects |
| `tests/test_migration_provenance.py` (green) | 22 tests, OK (0 failures, 0 errors, 0 skips) |
| `tests/test_secret_scan.py` (green) | 16 tests, OK (0 failures, 0 errors, 0 skips) |
| `tests/test_reviewed_runner.py` | 5 tests, OK |
| `toolbox/run-offline-checks.sh` (aggregate) | exit 0, **12/12 run invocations PASS** — manual profile 358/0/0; manual review 142/0/0; backup 43/0/0; configure 64/0/0; contract 30/0/0; m01-tempdir 9/0/0; clean-install `REHEARSAL=PASS`; guide/tree 220/0/0; ShellSpec 140 examples 0 failures; reviewed Python allowlist 486 tests OK (0 skips); secret scan PASS; manifest verify PASS (360 rows) |
| `toolbox/run-check-only-lint.sh` | exit 0 — ShellCheck certifier set + error-only, `shfmt` check-only, check-only Markdown and nine read-only hooks all PASS |
| `toolbox/verify-extensions.sh` | PASS (ShellSpec 0.28.1, Ruff 0.16.8, ty 0.0.82, yamllint 1.38.0) |
| `toolbox/scan-secrets.sh` | exit 0 — redacted `github-pat` control on the exact synthetic file and a clean 361-file full-tree scan |
| `toolbox/generate-migration-manifest.py --verify` | source-aware PASS (360 rows); destination-only mode is still reported explicitly and identity is then **not** re-derived |
| `toolbox/generate-migration-manifest.py --inventory \| sha256sum` | reproduces the recorded `inventory_fingerprint` |
| `git diff --check` | exit 2 with only the preserved historical EOF exception at `docs/plans/2026-09-20-hermes-manual-review-corrections.md:779` |

The green and aggregate rows above are **implementation-agent results** measured on
the frozen corrected tree. The independent third review reproduced the 43 focused
tests and the read-only gates it lists, but it did **not** reproduce the aggregate
run or the 486-test Python allowlist, so those remain implementation-agent results,
not independently reproduced results.

The third review's real-tooling limits carry over unchanged: no VM, boot, SSH,
provider, credential, TPM, service, installer or integration operation was
executed, and the repository remains a corrected uncommitted working tree.

## Independent acceptance and close-out (2026-09-22)

The bounded third correction pass was independently reviewed and accepted. Review
verdict: **ACCEPTABLE — third correction pass**, with no remaining blocking finding
in the reviewed seven-file correction delta. The single follow-up was a LOW,
non-blocking UTF-8 wording clarification, resolved in this close-out through
documentation and comments only (no scanner behaviour change).

Local review evidence, **outside this repository**:
`/var/home/aicloudopspecial/hermes-migration-review-pass3/REVIEW.md`, review clock
2026-09-22T18:46:02-05:00. That report and its supporting logs exist only in the
local filesystem; they are local review evidence, **not** a repository-contained
artifact and not part of the migration payload.

Accepted baseline (historical; the close-out edits below supersede it):

| Item | Accepted value |
| --- | --- |
| Branch / HEAD | `hermes/hermes-repository-migration` / `de8fb8ba1ef8729e895e340ff6244232d3d2193e` |
| Files / rows | 361 files including the manifest; 360 payload/inventory rows |
| Payload identity (manifest-excluding) | `8437c01897893980036d17fd6a044ce462bb2694268dc33f065b4fd353155316` |
| Inventory identity (manifest-excluding) | `48e517c36f681fb8c2dbf957cd100a39e0b817cf9c5d86432183fe79fcad4143` |
| Manifest SHA-256 (reported separately) | `c2e42005e47585935ea11219b3498bcded5b2ef404f0b474441ed12d110b473b` |

Those values are the identities the independent review reconstructed from the
tracked/nonignored inventory, file bytes and actual filesystem modes. They describe
the artifact **as reviewed**, not the artifact after any later edit. They are kept
here as clearly labelled historical accepted values; the current identities are
recomputed by `--verify`/`--inventory` and reported in the close-out handoff rather
than embedded in this payload document, because a document inside the payload
cannot contain the current hash of that payload.

Scope of the acceptance:

- It accepts the **bounded repository correction pass** — the seven-file delta, its
  regression controls and the replacement inventory identity — for the accepted
  identities above.
- It is **not** full migration or runtime recertification. The reviewer did not
  reproduce the full aggregate gate or the 486-test Python allowlist; those remain
  implementation-agent results.
- The reviewer independently reproduced the 43 focused tests (22 provenance + 16
  scanner + 5 reviewed-runner), the source-aware and destination-only manifest CLI,
  the inventory reproducibility and mutation controls, the check-only lint, the
  real full-tree secret scan, the extension validator, the wiring self-test and
  endpoint preservation.
- **Runtime/deployment readiness remains NOT ESTABLISHED.**
- **Commit/push authorization remains pending.** Nothing is staged, committed,
  pushed, merged or modified in a pull request.

Effect of this close-out: the record edits and the regenerated
`docs/migration-manifest.txt` produce a **different artifact** from the accepted
baseline above. The prior acceptance applies to the earlier baseline only and does
not automatically cover these edits; a narrow follow-up review is required.

## Handoff / closure

- **Current outcome:** the bounded third correction pass is **independently
  accepted** for the historical baseline identities recorded in "Independent
  acceptance and close-out" above. This close-out then edited the migration record,
  the scanner comment and the regenerated manifest, so the working tree is now a
  **different artifact** from the accepted baseline and awaits a narrow follow-up
  review of exactly that delta.
- **Gates:** the task-table gates above are retained as history for the original
  artifact; the earlier aggregate results remain implementation-agent results, not
  independently reproduced results. The third-pass and close-out measured results
  are in "Focused regression controls (third pass)" and "Independent acceptance and
  close-out".
- **Remaining gates and blockers:**
  - Narrow follow-up review of the close-out delta (migration record, scanner
    comment, regenerated manifest) — **NOT RUN**.
  - Commit/push authorization — **PENDING**, not granted; nothing is staged.
  - Full aggregate offline gate against the close-out artifact — **NOT RUN** (the
    earlier aggregate run is not carried forward as a result for this artifact).
  - Registry publication and digest-pinned CI — **BLOCKED** on a registry
    credential with package-write scope.
  - `vm/DEPLOYMENT_TASKS.md` `DOC-01`'s doc-sync audit slot — **NOT RUN**.
  - Runtime, lab, SELinux, systemd, reboot and provider acceptance — **NOT RUN**.
  - Real-tooling integration suite — **NOT RUN** (the opt-in runner reports this
    explicitly rather than passing by omission).
  - Runtime/deployment readiness — **NOT ESTABLISHED**.
- **Material limitations:**
  - The accepted identities above are historical and do not describe the current
    close-out artifact.
  - The environment standard still cannot be pinned by a public commit:
    `dev-toolbox` has no remote and remains dirty, so it is identified by commit
    plus the full dirty-input fingerprint recorded in `PROVENANCE.md`.
  - The reviewed corrections remain an uncommitted working-tree delta in
    `mikrotik`.
  - Adapted files are listed with reasons in `docs/migration-adaptations.txt`.
  - Credential rotation obligations recorded in the source repository remain the
    operator's responsibility.
- **Exact next action:** obtain the narrow follow-up review of the close-out delta
  keyed to the recomputed payload and inventory identities plus the manifest's
  separate SHA-256 reported in the close-out handoff; only then decide whether to
  request commit/push authorization for the migration branch.
- **Final state:** CLOSE-OUT RECORDED — pending narrow follow-up review; commit/push
  NOT authorized
