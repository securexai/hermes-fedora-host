# Root entrypoint organization

Record state: COMPLETE

## Approved baseline — preserve after approval

- Outcome: organize deployment implementations and guides in their owning directories,
  preserving root commands and guide paths as compatibility entrypoints.
- Approval: user supplied the implementation plan and explicitly requested implementation.
- Baseline: clean `9353b562fea89ccf549da92c087cda67d8305a25` on
  `chore/repository-hygiene`; branch `chore/root-entrypoint-organization` created from it.
- Canonical moves: `hermes-deploy.sh` to `scripts/hermes/deploy.sh`;
  `hermes-remediation-wizard.sh` to `scripts/hermes/remediation-wizard.sh`;
  `hermes-simple-deploy.sh` to `scripts/hermes/simple/deploy.sh`;
  `hermes-certify-vm.sh` to `vm/hermes-certify-vm.sh`; both root HTML guides and
  `setup-ssh-key-only.md` to `docs/` with their existing basenames.
- Root launchers use location-relative `exec` without changing caller working directory;
  preserve arguments, environment, streams, signals and status. Preserve the deployment
  library repository-root contract, defaults, syntax and safety checks.
- Root HTML navigation preserves fragments and supplies visible fallback links;
  root Markdown navigation retains heading anchors and links to canonical sections.
  Preserve guide styling/content except necessary path corrections.
- Keep standalone SSH script and its manual-profile copy byte-identical. Keep root
  configuration, README, AGENTS and PROVENANCE. Do not retire workflows.
- Extend provenance with verified destination-to-original-source mappings, adaptation
  reasons and hard failures for missing declared sources. Regenerate manifest.
- Acceptance: old commands and guide paths work; equivalent offline behavior; unchanged
  safety gates; no unexplained changes beyond layout work. Preserve default-severity
  ShellCheck coverage, artifact checks and certification fingerprint coverage.
- Boundaries: no packages, host changes, deployment, guest access, VM lifecycle,
  historical rewrites, external-link changes, commit, push or merge. Leave uncommitted.
- Verification runs in `dev-infra-hermes`; fixtures replace potentially live actions.
- This file is the sole execution record. Historical certification is STALE for changed
  inputs; historical records remain byte-for-byte, with no new live acceptance claimed.

## Tasks and gates

| Task | Outcome and dependencies | Progress | Gates | Next action |
| --- | --- | --- | --- | --- |
| T01 | Baseline, branch and record; none | ✅ DONE | G01 | None |
| T02 | Canonical files, compatibility and docs; T01 | ✅ DONE | G02, G03 | None |
| T03 | Provenance, fingerprint and regression coverage; T02 implementation | ✅ DONE | G02, G04 | None |
| T04 | Verification and delivery; T02, T03 | ✅ DONE | G02–G06 | None |

| Gate | Method and expected result | Status | Evidence |
| --- | --- | --- | --- |
| G01 | Git baseline/status; exact clean commit and requested branch | ✅ PASS | Clean baseline verified; branch created |
| G02 | Toolbox offline suite, check-only lint and extension verification; all pass | ✅ PASS | Full rerun passed; final documentation refresh follows record freeze |
| G03 | Fixture launcher tests, SSH regressions, local links/fragments and browser guides/redirects; pass | ✅ PASS | Offline fixtures, SSH and links pass; user confirmed manual browser acceptance below |
| G04 | Provenance mapping/missing-source and fingerprint regressions; source-aware manifest verification; pass | ✅ PASS | 24 provenance tests, fingerprint mutations and source-aware 403-row verification |
| G05 | Whitespace, dependency dry-run and preservation of tools/dependencies/caches/history/SSH copies; unchanged | ✅ PASS | No dependency changes; 465 files preserved; whitespace clean |
| G06 | Review exact diff against acceptance and boundaries; no unexplained changes | ✅ PASS | Exact tracked diff and new canonical files reviewed; bounded layout changes |

## Evidence history

- G01: `git status --short`, branch and HEAD inspection: clean baseline at the full
  revision above. Initial branch creation hit the read-only Git sandbox; authorized
  escalation succeeded. No implementation changes preceded this record.

### Focused verification, first attempt

- Toolbox relocation fixtures: 3 tests PASS (arguments, environment, working
  directory, streams, PID/exec, signals, guide/SSH preservation and fingerprints).
- Provenance: 23 passed, 1 FAIL. The synthetic adaptation fixture changed its
  foundation reasons file without a reason for that file. Added the missing fixture
  explanation; production enforcement correctly rejected the fixture. Rerun pending.
- Toolbox access required authorized sandbox escalation; no host modifications.

### First full gates and relocation follow-up

- `toolbox/run-check-only-lint.sh`: PASS (105 shell files, 51 Markdown files).
  Later launcher guard and rehearsal changes make shell coverage STALE until rerun.
- `toolbox/verify-extensions.sh`: PASS; installed ShellSpec 0.28.1, Ruff 0.16.8,
  ty 0.0.82, yamllint 1.38.0. `uv sync --locked --offline --dry-run`: no changes.
- Full offline attempt: 515 Python cases and 140 ShellSpec examples passed;
  226 guide assertions passed. Two gates FAIL: rehearsal detected the two newly
  relocated `deploy.sh` basenames; manifest became STALE during final test edits.
- Correction: document the intentional legacy/simple controller pair in the
  existing rehearsal variant list, retaining duplicate SSH helper identity checks.
  Regenerate manifest and rerun offline gates after implementation freeze.
- Expanded relocation suite: 5 tests PASS, including local Markdown/HTML links
  and fragment destinations, and identical root/canonical help from outside repo.
- Browser tool reports “No browser is available”; visual/redirect browser check
  BLOCKED. Attempted loopback preview server was sandbox-denied; no server left
  running. No software installed or browser settings changed to work around it.
- Preservation comparison: 465 snapshotted files unchanged (tools, dependency
  files, existing caches and historical evidence); both SSH copies separately
  compared against baseline by regression tests.

### Final implementation validation — 2026-09-26, America/Bogota

- Checked inputs: uncommitted working tree based on `9353b56` on
  `chore/root-entrypoint-organization`, including all new canonical files, the new
  regression module and this record. No commits, staged changes or external writes.
- Toolbox from repository root, `PYTHONDONTWRITEBYTECODE=1`:
  `bash toolbox/run-offline-checks.sh` PASS; 517 Python tests from 88 explicit
  targets, 140 ShellSpec examples, 226 guide assertions, all manual/rehearsal
  gates, full-working-tree secret scan and source-aware manifest verification.
  The first failed run above is superseded, not erased.
- `bash toolbox/run-check-only-lint.sh` PASS after shell corrections; default
  ShellCheck severity includes moved implementations. No safety checks removed.
- `bash toolbox/verify-extensions.sh` PASS and
  `uv sync --locked --offline --dry-run` reports “Would make no changes”.
- `python3 -B -m unittest discover -s tests -p test_root_entrypoints.py` PASS:
  five cases exercise all four root launchers with synthetic targets in checkout
  paths containing spaces; preserve quoted/empty arguments, cwd, environment,
  stdin/out/err, PID, SIGTERM and status 37; compare root/canonical help safely;
  validate maintained local Markdown/HTML links and fragments; compare guides
  and both SSH helpers to baseline; mutate every launcher/implementation to
  prove certification fingerprints change. Included in the full offline run.
- Provenance regressions cover all seven mappings, missing declared sources,
  adaptation explanations, tampered mapping audit, and successful source-aware
  verification. The manifest includes both canonical and compatibility files.
- Preservation: 465 snapshot file hashes/modes unchanged; no additional files
  in the inspected installed-tool/cache directories. Independently compared
  all 94 historical plan files, four reviews and four archive files to baseline:
  byte-identical. Both SSH helper copies are byte-identical to baseline.
- Reviewed original-to-canonical diffs: only repository path resolution and
  necessary guide href corrections; guide CSS, external URLs, script defaults,
  command grammar and operational safety checks preserved. Root launchers use
  `exec` and fail if location resolution fails. No package or host changes.
- Final documentation review updated the environment guide's canonical path
  inventory and clarified adaptation reasons. These documentation/record edits
  invalidate the previous manifest and require the refresh below before handoff.
- Transient complete logs: `/tmp/hermes-layout-offline-final.log`,
  `/tmp/hermes-layout-lint-final.log`, `/tmp/hermes-layout-extensions.log`,
  `/tmp/hermes-layout-provenance.log`, `/tmp/hermes-layout-links.log`.

### Browser connection retry — 2026-09-26

- User reported extension installation and requested continuation. Re-read the
  execution skill and inspected branch/status; source-aware manifest verification
  PASS for the unchanged 403-row implementation before this record update.
- Browser inventory returned `apps: [], browsers: []`. A dedicated Chrome tab
  attempt returned `Browser is not available: chrome`. Extension installation is
  user-reported; an active browser connection is not observed by this session.
- G03 remains BLOCKED. Requested that the user open the extension in its installed
  browser profile, confirm connection, and select the browser through the chat's
  `@` menu; if absent, check its Computer Use toggle and Manage status.
- No implementation files, packages, browser settings or host services changed.
  Refresh only this record's Markdown check, manifest and full-tree secret scan.

## Decisions and approved scope changes

### Connected browser retry — 2026-09-26, America/Bogota

- Resumed on the existing feature branch with the recorded dirty/untracked files.
  Before editing this record, Toolbox source-aware manifest verification PASS:
  all 403 rows match, with source, toolbox and companion checkouts present.
- Browser inventory now exposes Codex In-app Browser (`iab`). Attempted to open
  the root secure guide with `?layout-check=1#promotion` using its local file URL.
  Browser Use rejected navigation because its URL policy blocks the page and
  explicitly prohibited indirect workarounds or alternate browser surfaces.
  No redirect, rendered guide, fallback link or fragment behavior was observed.
- G03 remains BLOCKED by browser policy, superseding the missing-connection
  diagnosis. No workaround, browser setting change or installation attempted.
- Initial sandboxed Toolbox access failed to obtain the Podman version;
  authorized host-access retry passed. No deployment or guest access performed.
- This record update makes the manifest STALE until the record-freeze refresh
  described below. Implementation inputs remain verified against the prior
  manifest; previously recorded offline results remain applicable to them.

No scope expansion. The rehearsal's native intentional-variant mechanism now
documents the two distinct relocated `deploy.sh` programs. The standalone SSH
identity check remains enforced. Browser setup guidance was provided after the
user asked how to connect; no browser installation or settings change performed.

### Manual browser acceptance and closure

- User reported the guide was properly showing. In response to the explicit
  follow-up checklist covering both guides, root redirects into `docs/`,
  retention of `?layout-check=1#promotion`, and working fallback links with
  JavaScript disabled, the user confirmed: "yes, all links are working".
- G03 browser acceptance is therefore PASS by user-reported manual verification;
  it is not an agent-observed automated browser result. The earlier browser
  policy rejection remains preserved above and was not bypassed.
- Before this closure edit, source-aware manifest verification PASS for all
  403 rows on the same feature branch, confirming implementation inputs match
  the previously validated tree. Only this record and its manifest need refresh.
- The previous record-freeze refresh passed five entrypoint/link tests,
  check-only lint, full-tree secret scan, whitespace and source-aware manifest
  verification; transient log: `/tmp/hermes-layout-resume-refresh.log`.

## Handoff or closure

- Outcome: implementation, offline acceptance and user-reported manual browser
  acceptance complete. No remaining implementation tasks or acceptance gates.
- Record-freeze refresh for closure: regenerate manifest, verify source-aware,
  run relocation/link tests, check-only lint, secret scan and whitespace. Report
  the actual refresh receipt in delivery; a failure blocks acceptance. This avoids
  embedding a self-referential manifest hash in the record it fingerprints.
- Exact next action: none after successful record-freeze refresh. Transient
  refresh log: `/tmp/hermes-layout-closure-refresh.log`.
- Original delivery boundary was to leave changes uncommitted; the subsequent
  explicit Git delivery authorization below supersedes that boundary.
- Live deployment, VM, provider and host acceptance: NOT RUN, outside scope.
- Final state: COMPLETE within the approved layout and compatibility scope.

## Subsequent Git delivery authorization

- After accepting completion, the user explicitly requested "commit push and
  merge". This authorizes committing the reviewed changes, pushing the feature
  branch, and merging into the remote default branch, `main`.
- Remote inspection found no open pull request and `origin/main` at `04c8d72`.
  The feature branch includes the approved baseline hygiene commit `9353b56`;
  a fast-forward merge preserves that commit and the organization work without
  rewriting history. Preserve both existing feature branch pointers.
- Review covered the exact tracked diff, new canonical implementations and
  compatibility tests. Run installed commit and push hooks inside the existing
  Toolbox; do not bypass checks. Refresh the manifest for this record update.
- Implementation acceptance remains complete. Git command results and final
  local/remote commit equality provide the delivery receipt; do not infer Git
  delivery success from this authorization entry alone.
