# Incremental repository organization

Record state: VALIDATED FOR DELIVERY

## Approved baseline

The user approved the supplied consolidation plan and requested implementation.
Consolidate all local committed work onto
`docs/incremental-repository-organization` with a fast-forward to
`db0a719f147755c68c27fed0067d742bf8ef3e6a`, then create one local commit named
`docs: record incremental repository organization` and finish with a clean tree.
Only this record, contribution guidance and required provenance updates may differ
from that incoming commit. Preserve every other branch pointer, historical record,
implementation file, local evidence file and installed tool.

Authorized: the fast-forward, documentation/provenance edits, required offline
checks and one local commit. Excluded: directory restructuring, pushes, remote
updates, branch deletion, rewriting history, VM operations and live provider tests.

Acceptance requires all starting tips to be ancestors of the final branch,
unchanged other pointers and preserved local artifacts with effective ignore rules.
Run the offline suite, check-only lint and extension verification inside
`dev-infra-hermes`; require source-aware manifest verification, valid changed
links, whitespace checks, exact staged review and required commit hooks.

## Starting inventory

```text
codex/hermes-deepseek-e2e-r1 db0a719f147755c68c27fed0067d742bf8ef3e6a
docs/incremental-repository-organization ff8d35415b7bff000d0dd19910bae74eca6f7894
hermes/hermes-foundation de8fb8ba1ef8729e895e340ff6244232d3d2193e
hermes/hermes-repository-migration ef3fc9c4efe1adbf7631ce96be203871e9c6c75f
main ff8d35415b7bff000d0dd19910bae74eca6f7894

```

No tracked changes or stashes existed. All starting branch tips are ancestors of
`db0a719`. Incoming paths do not collide with local artifact files.
The local artifact SHA-256 inventory is retained at
`/tmp/hermes-organization-preservation.json` for this execution.

## Tasks and gates

| Task | Outcome and dependency | Progress | Gates | Next action |
| --- | --- | --- | --- | --- |
| T01 | Preserve inventory and integrate; none | ✅ DONE | G01 | Preserve through final check |
| T02 | Guidance and provenance; T01 | ✅ DONE | G02 | Retain provenance |
| T03 | Validate delivery; T02 | ✅ DONE | G03, G04 | Commit and verify receipt |

| Gate | Method and expected result | State | Evidence |
| --- | --- | --- | --- |
| G01 | Ancestry, pointer, file hashes and ignore checks; all preserved | ✅ PASS | All tips included; 390 hashes unchanged; ignored artifacts |
| G02 | Manifest generator with source-aware verification and changed links; valid | ✅ PASS | See evidence below |
| G03 | Toolbox offline, lint and extensions; all pass | ✅ PASS | See evidence below |
| G04 | Exact allowed diff, whitespace and staged hooks; all pass | ✅ PASS | See evidence below |

## Evidence history

Initial inspection on 2026-09-26 matched the approved branch inventory.
The first merge attempt could not write read-only Git metadata; it changed no
branch. The authorized retry with metadata write access fast-forwarded successfully
from `ff8d354` to `db0a719`; no merge commit was created.
Preservation inventory contains 390 regular files. No scope change.

### Validation on 2026-09-26

All commands ran from this repository root. Development checks ran through
`toolbox run --container dev-infra-hermes bash -c` in the existing container.
The initial sandbox Toolbox attempt could not read the Podman version; the
host-access retry succeeded. No check was weakened.

Checked inputs: `db0a719` plus this record, `docs/CONTRIBUTING.md`,
`docs/migration-adaptations.txt` and generated `docs/migration-manifest.txt`.
The manifest records the exact payload and source identities without introducing
a self-referential fingerprint in this record.

- G01: SHA-256 comparison against the starting inventory passed for all 390
  regular artifact files. None appears in the non-ignored untracked inventory.
  `git check-ignore` confirmed the correction-evidence and ShellSpec rules.
  `git merge-base --is-ancestor` passed for all five original tips; the other
  four local branch pointers remained unchanged.
- G02: generation produced 393 manifest rows and 13 excluded candidates.
  `python3 -B toolbox/generate-migration-manifest.py --verify` reported
  **source-aware** verification and matched the working tree. All relative links
  in the changed Markdown documents resolve to existing local files.
- G03: `bash toolbox/run-offline-checks.sh` passed every offline gate, including
  140 ShellSpec examples, 510 reviewed Python cases, the full-tree secret scan
  with positive control, and source-aware manifest verification.
  `bash toolbox/run-check-only-lint.sh` passed (101 shell files, 48 Markdown
  files). `bash toolbox/verify-extensions.sh` passed, including ShellSpec 0.28.1,
  Ruff 0.16.8, ty 0.0.82 and yamllint 1.38.0.
- G04: working-tree and staged whitespace checks passed. Exact diff review
  confirmed only the four authorized files differ from `db0a719`; implementation
  and historical evidence are unchanged. Staged `pre-commit run` and the
  `commit-msg` hook passed, including Conventional Commits validation.

Detailed local logs are retained under `/tmp/hermes-organization-` with suffixes
`run-offline-checks.sh.log`, `run-check-only-lint.sh.log`,
`verify-extensions.sh.log` and `hooks.log`. These are execution-local evidence,
not permanent repository artifacts.

This final evidence update invalidates the earlier manifest and documentation
scan inputs only. Regenerate the manifest and refresh source-aware verification,
full-tree scanning and staged hooks before delivery; the unchanged implementation
suite and extension results remain applicable. Preserve any failed refresh as a
new evidence entry rather than treating these earlier passes as a substitute.

## Delivery and closure

Validation outcome: consolidation and the scoped documentation changes passed
all required pre-delivery gates. No implementation or historical evidence changed.
No VM, provider, deployment, push or remote-update operations were performed.

Exact next action at record freeze: regenerate the manifest, rerun affected
checks, review the final staged diff, then create the authorized local commit
`docs: record incremental repository organization` with hooks enabled.

The successful containing Git commit is the durable delivery receipt; this
pre-commit record does not claim a future commit or clean-tree observation.
After committing, verify its parent is `db0a719`, all original tips remain
ancestors, other pointers and artifact hashes are unchanged, the target branch
is checked out, and `git status --porcelain` is empty. Report the actual commit
and final observations in the delivery response. A failure blocks completion.
