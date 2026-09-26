# Scoped Python diagnostic corrections

Record state: COMPLETED

## Approved baseline — preserve after approval

- Outcome: correct the supported findings from the read-only triage and document remaining diagnostics.
- Approval: the user's `approved` message after the triage report and branch discussion.
- Baseline: clean `codex/hermes-deepseek-e2e-r1` at `db0a719f147755c68c27fed0067d742bf8ef3e6a`.
- Working branch: `codex/python-triage-corrections`, created from that baseline.
- Scope: the two test import blocks, unattended test fixtures, broker record narrowing,
  VM target record typing, documented first-party ty import paths, and maintained-code diagnostic review.
- Acceptance: the scoped Ruff and ty findings are corrected; the required offline and check-only gates pass;
  current provenance matches the changed inputs; remaining maintained-code findings have a recorded classification.
- Boundaries: use existing Toolbox tools offline, with no dependency or skill changes, mandatory ty gate,
  blanket ignores, historical evidence edits, commits, pushes, deployment, credentials, or VM operations.
- Triage evidence: `/tmp/hermes-ty-triage.TtYyzu9Y/TRIAGE.md` and its `SHA256SUMS`.
- Existing mandatory gate results are historical and become STALE for the source/configuration inputs changed here.
- Owner: this file is the single execution record for this correction; no deployment plan is resumed.

## Tasks and gates

| Task ID | Outcome and dependencies | Task progress | Required gate IDs | Exact next action |
| --- | --- | --- | --- | --- |
| T01 | Correct supported source and fixture findings; no dependencies | ✅ DONE | G01, G02 | Complete; offline regression also passed |
| T02 | Document import context and review remaining maintained-code findings; T01 | ✅ DONE | G03 | Retain the classified backlog below |
| T03 | Validate and refresh current provenance; T01, T02 | ✅ DONE | G04, G05, G06 | Complete; Git delivery authorized |

| Gate ID | Method and expected result | Gate status | Latest evidence |
| --- | --- | --- | --- |
| G01 | Non-fixing selected Ruff check: zero findings | ✅ PASS | `ruff-final.log`, exit 0 |
| G02 | ty on the two tests, broker and VM target utility: zero supported findings | ✅ PASS | `target-final.log`, exit 0 |
| G03 | Full-context ty review of scripts, tests, VM and Toolbox Python; classify remaining findings | ✅ PASS | Review below; ty itself exits 1 with 174 diagnostics |
| G04 | Existing offline gate: all reviewed synthetic checks pass | ✅ PASS | `offline.log`, exit 0; 511 Python tests |
| G05 | Existing check-only lint gate: pass | ✅ PASS | `lint2.log`, exit 0; prior failure retained |
| G06 | Source-aware current migration manifest and preserved-input hashes: pass | ✅ PASS | `manifest-record-refresh.log`; 102 preserved inputs and skill identity match |

## Evidence history

- Before implementation: branch and HEAD match the triage; no tracked or untracked changes.
- Read the current repository guidance and the installed plan-execution skill and record rules.
- The plan covers the corrections proposed in the triage; the remaining broad ty results are diagnostic review,
  not authorization to rewrite every Python component or introduce a required gate.
- Logs for this correction are retained privately in `/tmp/hermes-python-corrections.Nww0lEom/`.
- Existing Toolbox versions remain uv 0.12.9, ty 0.0.82 and Ruff 0.16.8.
  Every project uv invocation used `UV_NO_SYNC=1`, `UV_PYTHON_DOWNLOADS=never`, `UV_OFFLINE=1`.
- G01: `uv run --locked ruff check --no-fix --no-cache --output-format full` on the original five selected
  files plus `vm/retire-legacy-labs.py`: exit 0, all checks passed. Both affected test settings saved in full.
- G02: `uv run --locked ty check --output-format full --color never` on the two tests,
  `scripts/hermes/unattended/credentials.py` and `vm/retire-legacy-labs.py`: exit 0, all checks passed.
  This covers the current source and configured import paths, including the added broker rejection regression.
- Maintained-code diagnostic baseline with the proposed paths: 254 diagnostics before source corrections.
  After source corrections and the documented configuration: 174 diagnostics; exit 1, retained in full.
  The original 307 whole-project count included 10 historical evidence findings and different import resolution.
  These counts describe different inputs/scopes; excluding historical files is not a code correction.
- G06 preparation attempt 1: manifest generation refused the changed foundation `pyproject.toml` without
  an adaptation reason (exit 1, `manifest-generate.log`). Added its explicit optional-diagnostics reason;
  the failed attempt is retained and no provenance check was weakened.
- G04: `bash toolbox/run-offline-checks.sh` inside `dev-infra-hermes`, with integration opt-in empty and
  Python bytecode/downloads disabled: exit 0. All shell assertion groups and 140 ShellSpec examples passed;
  511 reviewed Python tests passed (87 allowlist targets), including the added unknown-lease regression.
  The synthetic secret-scan positive control and 394-file working-tree scan passed; source-aware manifest
  verification passed for 393 payload rows. This covers all current source and Python configuration changes.
  Later execution-record edits require documentation and manifest revalidation, not another unchanged test run.
- G05 attempt 1: check-only lint exited 1 solely on MD056 in this new record: an unescaped type-union pipe
  added an extra table cell. ShellCheck, shfmt and all nine read-only baseline hooks passed.
  Reworded the table cell; retained `lint.log` and rerun the gate without changing its rules.
- G05 attempt 2: `bash toolbox/run-check-only-lint.sh`, same existing Toolbox, exit 0.
  All ShellCheck/shfmt/Markdown checks and nine read-only hooks passed. Installed hook cache markers
  were inspected under `/opt/pre-commit-cache`; pip and npm downloads were disabled.
- G06: current manifest regenerated and source-aware verification passed after the review was recorded.
  All 102 baseline history/lock/Python-version inputs selected from the triage's hash manifest matched;
  installed modern-python entry and upstream-marker hashes also matched. No historical record was edited.
- Final review at 2026-09-26 18:24 America/Bogota: exact source/configuration diff inspected;
  `git diff --check` passed; diagnostic table sums to 174 across 41 files.
  `SHA256SUMS` and `inputs-final.sha256` in the private log directory retain log and final-input identities.
  Logs replace the checkout prefix and synthetic canary strings and remove terminal color escapes.
  The original failed attempts remain retained. Final record-only updates are followed by a narrow Markdown
  check and a fresh manifest generation/verification; the unchanged source suites are not repeated.

## Decisions and approved scope changes

- Delivery authorization: the user subsequently requested `commit and push` for this correction branch.
  Commit and push with the existing hooks enabled; no pull request or deployment action is authorized.
- Keep the current Python constraints, lockfile, package manager, lint rules and runtime test allowlists.
- Add only source-backed import paths after checking collisions with the other flat script layouts.
- Configured `tests/` and `scripts/hermes/unattended/` only; inspected bare `host`/`controller` imports refer
  to unattended modules. The separate simple layout was not added as a competing global import root.
- SSH fixture follow-up: the existing five ty findings arise from optional `shutil.which` and integer fixture
  values absent from the inferred initial dictionary. Added a fail-fast missing-keygen check and precise value union.
- Added one synthetic broker test for read/revoke of an unknown lease: preserve code 66 and reject before
  mocked provider calls or secret access. The existing class-level offline allowlist includes this safe test.

## Remaining maintained-code review

The configured optional check covers 105 tracked Python files across scripts, tests, VM and Toolbox.
The final diagnostic log has 172 errors and 2 warnings, not a passing project-wide ty result.
The source correction removed 80 findings against the comparable 254-diagnostic import-path baseline.
All remaining messages were retained in `maintained-final.log`; representative source boundaries were inspected
to distinguish runtime guards from checker limitations. No rule is disabled and no maintained directory is excluded.

Categories: **E** environment/import configuration; **F** fixture or dynamic loading;
**T** type annotation/narrowing gap; **D** supported signature defect; **U** unresolved runtime precondition.
Mixed rows identify which findings belong to which cause. These classifications do not establish deployment safety.

| File under repository root | Count | Classification and inspected cause |
| --- | ---: | --- |
| `scripts/hermes/gate2-guest-recovery.py` | 2 | E: `libvirt` and `libvirt_qemu` absent from the project venv search context |
| `scripts/hermes/manual/config/harden-config.py` | 1 | T: repeated `dict.get` after an `isinstance` check does not retain narrowing at line 212 |
| `scripts/hermes/manual/gateway/m03-probe.py` | 2 | E: imports belong to the Hermes deployment application |
| `scripts/hermes/manual/gateway/memory-approval-probe.py` | 4 | E: runtime `/opt/hermes` modules are outside the checkout environment |
| `scripts/hermes/manual/lab/deepseek-guest-password-recovery.py` | 2 | E: `libvirt` and `libvirt_qemu` project-vs-host environment gap |
| `scripts/hermes/manual/lab/deepseek-test-grant.py` | 3 | T: repeated XML lookup, `stop` annotated `None` despite always raising, and validated regular tar member still typed optional |
| `scripts/hermes/selinux/recover-first-service.py` | 5 | F: hash-checked `exec` populates a namespace initially inferred as `dict[str, str]`; its callable and Path entries are invisible to ty |
| `scripts/hermes/selinux/run-reviewed-service-v2.py` | 1 | T: heterogeneous collector results obscure the string returned by `query_audit` |
| `scripts/hermes/selinux/verify_policy.py` | 1 | E: `setools` unavailable in the selected project environment |
| `scripts/hermes/simple/data.py` | 1 | T: `members` permits only directories/regular files; the regular-file extraction result remains optional in stubs |
| `scripts/hermes/simple/host.py` | 1 | U: unguarded `MemTotal` regex result; malformed/missing data would fail before the intended resource verdict; caller/platform contract needs review |
| `scripts/hermes/unattended/boot_build.py` | 1 | T: `require(systemctl, ...)` raises but does not narrow the optional string for `Path` |
| `scripts/hermes/unattended/certify.py` | 2 | T: runtime exception attributes `transport` and `revocation_attempts` have no declared type contract |
| `scripts/hermes/unattended/certify_guest.py` | 8 | T: three tar/guard narrowing findings; five optional restore arguments whose dispatcher supplies stream/message but whose signature permits None |
| `scripts/hermes/unattended/certify_power.py` | 1 | U: disk `source` lookup is unguarded; outer exception handling rejects it, but malformed-XML contract should be explicit |
| `scripts/hermes/unattended/gates.py` | 3 | T: `stdout=PIPE` is supplied, while stubs keep `process.stdout` optional |
| `scripts/hermes/unattended/host.py` | 1 | T: journal starts with string values but later stores `previous_active` as bool |
| `scripts/hermes/unattended/lab_boot.py` | 3 | T: preceding `require(all(...))` guards driver/source/target, but repeated XML lookups are not narrowed |
| `scripts/hermes/unattended/lab_candidate.py` | 2 | T: `require(match is not None, ...)` does not narrow the regex match |
| `scripts/hermes/unattended/lifecycle_fixture.py` | 4 | T: validated tar member, XML source guard, and two tuple-union findings when appending the one-element sync command |
| `scripts/hermes/unattended/release.py` | 3 | T: `members` validates regular files, but `extractfile` retains its optional result type |
| `tests/hermes-synthetic-smoke.py` | 4 | E: three pinned-image application imports; D: `log_message` renames the base's keyword `format` to `_format`, so a base-compatible keyword call fails |
| `tests/test_deepseek_boot_inspect.py` | 3 | F: optional dynamic module spec/loader not narrowed |
| `tests/test_deepseek_guest_password_recovery.py` | 3 | F: optional dynamic module spec/loader not narrowed |
| `tests/test_deepseek_guest_permission_inspect.py` | 3 | F: optional dynamic module spec/loader not narrowed |
| `tests/test_deepseek_host_grant_finalize.py` | 3 | F: optional dynamic module spec/loader not narrowed |
| `tests/test_deepseek_test_grant.py` | 3 | F: optional dynamic module spec/loader not narrowed |
| `tests/test_hermes_certify.py` | 11 | T: seven heterogeneous manifest/policy findings and four dynamic exception-attribute findings |
| `tests/test_hermes_lab_enroll_boot.py` | 4 | F: fixture mock `self.run` overlaps inherited `TestCase.run` |
| `tests/test_hermes_lifecycle.py` | 15 | T/F: thirteen heterogeneous state findings; two mock return-values accessed through statically declared methods |
| `tests/test_hermes_live_smoke.py` | 1 | F: dynamic module's `PRIVATE` fixture override is absent from `ModuleType` |
| `tests/test_hermes_offline.py` | 16 | F: loop-created `boot_id` and `run` mocks; `run` overlaps inherited `TestCase.run` |
| `tests/test_hermes_schedule.py` | 2 | T: nested prepare mapping widened with string-valued policy fields |
| `tests/test_hermes_selinux_audit_v2.py` | 11 | F: loader/module overrides and heterogeneous patch kwargs; two warnings despite explicit `from unittest.mock import Mock, patch` |
| `tests/test_hermes_selinux_continuation_v2.py` | 11 | F: loader/module overrides and heterogeneous patch kwargs |
| `tests/test_hermes_selinux_export.py` | 13 | F: loader and synthetic module attribute overrides |
| `tests/test_hermes_selinux_service_v2.py` | 4 | F: loader and synthetic `TRIAL` override |
| `tests/test_hermes_transaction.py` | 4 | T: nested RPM records widened with string-valued transaction fields |
| `tests/test_migration_provenance.py` | 3 | F: optional dynamic module spec/loader not narrowed |
| `tests/test_remaining_preflight.py` | 3 | F: optional dynamic module spec/loader not narrowed |
| `tests/test_reviewed_runner.py` | 6 | F: three loader findings; two synthetic module class assignments; one deliberately injected test method |

The remaining signature defect is outside the scoped source correction and is recorded for a subsequent patch.
No runtime failure in an actual HTTP request was reproduced: the supported defect is the incompatible keyword signature.
Prioritize its small correction and the two unresolved input contracts before broader typing cleanup.
The script and test dynamic-loading cases need explicit loader and interface contracts, not blanket `Any` or ignores.
Preserved evidence remains excluded from this optional maintained-code scope and is unchanged; its old ten diagnostics
remain in the original broad-run evidence. No external package installation or deployment action was performed.

## Handoff or closure

- Current outcome: scoped corrections, optional ty import configuration, documentation and required gates complete.
- Remaining gates: none for this scope. The optional broader ty check still reports 174 classified diagnostics.
- Material limitations: static and synthetic validation cannot establish live deployment acceptance;
  no integration suite, VM operation, provider call or dependency/skill change occurred.
- Exact next action: commit and push the reviewed correction branch under the subsequent delivery authorization.
  Report the resulting commit and remote status separately. A later correction can address the recorded
  signature defect and unresolved input contracts before further typing cleanup.
- Final state: COMPLETED.
