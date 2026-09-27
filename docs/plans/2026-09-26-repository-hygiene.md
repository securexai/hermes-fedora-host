# Repository hygiene and dependency cleanup

Record state: VALIDATED; local delivery pending at record freeze

## Approved baseline — preserve after approval

- Intended outcome: finish repository hygiene with one local commit on
  `chore/repository-hygiene`, preserving the selected toolchain.
- Approval evidence: the user requested implementation of the supplied
  “Repository hygiene and dependency cleanup” plan in this session.
- Starting state verified: clean `main` at
  `04c8d72c67694401dd157abeff54010461da19c8`.
- Scope: remove only ignored, untracked `.ruff_cache/0.16.6` and expected
  bytecode in the six inspected `__pycache__` directories under `toolbox`,
  `tests`, `vm`, `scripts/hermes`, `scripts/hermes/unattended` and
  `scripts/hermes/manual/lab`. Reject symlinks and unexpected contents.
- Documentation: feature branches start from `main`; distinguish current
  disposable lab from completed migrations and retained alternatives; document
  optional tools and dependency audits; update adaptation reasons and manifest.
- Preserve installed packages, ShellSpec, current Ruff cache, Fedora lab-image
  cache, local review evidence, historical records, deployment code, dependency
  declarations, lockfile, pins and required gates.
- Acceptance: dependency dry-run proposes no changes; extension verification,
  offline suite, check-only lint, source-aware manifest verification, changed
  links, whitespace, preservation and commit hooks pass. Cleanup repeat removes
  nothing. Finish clean with `chore: clean repository guidance and stale caches`.
- Boundaries: local commit authorized; no package removal, upgrades, shared
  Toolbox or host changes, workflow retirement, restructuring, push, merge,
  production changes or live deployment operations.
- Canonical record: this file; owner: repository hygiene implementation.

## Tasks and gates

| Task | Outcome / dependency | Progress | Gates | Next action |
| --- | --- | --- | --- | --- |
| T01 | Record baseline and inspect caches | ✅ DONE | G01 | None |
| T02 | Update guidance and manifest; after T01 | ✅ DONE | G02, G03 | None |
| T03 | Verify and repeat cleanup; after T02 | ✅ DONE | G01, G04, G05 | None |
| T04 | Review and local commit; after T03 | 🔄 IN_PROGRESS | G06 | Commit with hooks; verify clean tree |

| Gate | Method / expected result | Status | Evidence |
| --- | --- | --- | --- |
| G01 | Validate ignored untracked regular caches; repeat deletes zero | ✅ PASS | See validation evidence |
| G02 | Review docs and local Markdown links; no broken links | ✅ PASS | See validation evidence |
| G03 | Regenerate manifest, source-aware `--verify`, `git diff --check` | ✅ PASS | See validation evidence |
| G04 | Toolbox dependency dry-run, extensions, offline and check-only lint | ✅ PASS | See validation evidence |
| G05 | Compare baseline hashes/modes and package inventory; protected inputs unchanged | ✅ PASS | See validation evidence |
| G06 | Exact staged diff, installed commit hooks, clean feature branch | 🔄 IN_PROGRESS | Hooks passed; delivery pending |

## Evidence history

- Initial inspection: branch and HEAD match the supplied plan; tracked/untracked
  status is clean. Read repository guidance, plan-execution rules and current
  entrypoints. Branch creation required normal sandbox escalation for `.git`
  writes and then succeeded; no repository content changed before this record.

### Implementation and audit

- Cache preflight verified all seven exact directories and 28 regular files as
  ignored, untracked, repository-contained and expected cache content, with no
  symlinks. Removed 424,351 logical bytes / 487,424 allocated bytes including
  directory blocks. The bounded helper is temporary, outside the repository.
- Captured SHA-256/modes for 751 protected tracked and generated inputs, including
  the environment, ShellSpec, current Ruff cache, lab cache and local evidence.
- Dependency audit in `dev-infra-hermes`: `uv sync --locked --offline --dry-run`
  resolved six packages, checked five installed packages, “Would make no changes”.
  `toolbox/verify-extensions.sh` passed: ShellSpec 0.28.1, Ruff 0.16.8,
  ty 0.0.82, yamllint 1.38.0 and shared profile contract.
- Initial sandbox Toolbox access failed before testing with “failed to get the
  Podman version”; the approved audit succeeded using normal host-access
  escalation. No package sync or provisioning was performed.
- Maintained README, contribution and environment guidance updated; adaptation
  explanations updated. Earlier dated records remain untouched.

### Validation evidence (2026-09-26, America/Bogota)

All commands ran from the repository root; development gates ran inside the
existing `dev-infra-hermes` Toolbox. Inputs are baseline `04c8d72` plus the three
maintained Markdown guides, adaptation explanations, regenerated manifest and
this new record. No implementation or dependency file changed.

- G01: after offline validation, the same guarded cleanup removed six regenerated
  bytecode files (68,105 logical / 81,920 allocated bytes). Immediate repeat
  found zero directories and zero files. Initial net reclaim remains 487,424
  allocated bytes (476 KiB); gross removal including regenerated files was
  569,344 allocated bytes. Filesystem accounting may differ due to compression
  or shared extents.
- G02: reviewed the exact guidance diff against the current disposable-lab guide
  and historical organization record. A local Markdown-link check resolved all
  30 links in the four changed documents; no external or anchor links occurred.
- G03: manifest generation produced 394 rows and 13 excluded candidates;
  `python3 -B toolbox/generate-migration-manifest.py --verify` reported
  source-aware verification with matching inputs. `git diff --check` passed.
- G04: `bash toolbox/run-offline-checks.sh` passed every gate, including 140
  ShellSpec examples, 510 Python cases from 87 explicit targets, positive-control
  full-tree secret scanning and source-aware manifest verification.
  `bash toolbox/run-check-only-lint.sh` passed over 101 shell files and 49
  Markdown files. Extension and dry-run audit results are recorded above.
- G05: all five installed distributions matched `uv.lock` exactly: pathspec
  1.1.1, PyYAML 6.0.3, Ruff 0.16.8, ty 0.0.82 and yamllint 1.38.0.
  A SHA-256/mode comparison of all 751 protected inputs before and after the
  gates reported no changes. This covers deployment code, dependency files,
  installed tools, current Ruff and Fedora lab caches, and preserved evidence.
- Execution-local full logs: `/tmp/hermes-hygiene-offline.log` and
  `/tmp/hermes-hygiene-lint.log`. These temporary logs are not permanent artifacts.
- A final README wording refinement and this evidence update invalidate only
  prior documentation lint/scan and manifest results for those bytes. Refresh
  affected checks and hooks before committing; implementation tests remain
  applicable to unchanged code. No failed validation result is being waived.

### Staged review and delivery preparation

- G06 preparation: exact staged diff reviewed; only the six approved files are
  included. `git diff --cached --check` passed. Staged `pre-commit run` and
  `pre-commit run --hook-stage commit-msg` passed, including the staged secret
  scan, Markdown lint and Conventional Commits validation.
- This final record update requires manifest regeneration and affected-check
  refresh. The containing commit must rerun installed hooks without bypasses.
  A failed refresh or commit blocks delivery and must be recorded before retry.

## Handoff or closure

- Current outcome: documentation, bounded cache cleanup and required
  implementation/environment validation passed; protected inputs unchanged.
- Remaining at record freeze: refresh affected documentation/manifest checks,
  then commit and inspect final Git state.
- Material limitations: no live deployment, VM lifecycle or provider checks were
  run; those operations are excluded from this hygiene task.
- Exact next action: regenerate the manifest, refresh source-aware verification,
  local links, full-tree scanning and lint, stage/review the final diff, and create
  `chore: clean repository guidance and stale caches` with installed hooks.
- Delivery receipt: the successful containing commit records local delivery.
  Verify its parent is `04c8d72`, the branch is `chore/repository-hygiene`, all
  protected hashes remain unchanged and `git status --porcelain` is empty.
  Report actual commit and post-commit observations in the final response.
  This pre-commit record does not claim a future commit or clean-tree observation.
