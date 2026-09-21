# hermes-fedora-host — Toolbox migration and dev-toolbox standard hardening

Record state: ACTIVE

## Approved baseline — preserve after approval

- **Intended outcome:** A `hermes-fedora-host` repository whose development
  environment is the canonical dev-toolbox `infra` profile, containing the
  broader Hermes manual-profile scripts, docs, tests and evidence, with verified
  provenance, pre-commit hook parity, and passing offline validation gates.
- **Approved scope:** harden the canonical dev-toolbox standard (three approved
  changes); publish the dev images and pin CI by digest; reconcile the Toolbox
  image chain; declare project-specific tool extensions with a non-writing
  validator; create the repository with a recorded provenance baseline; extract
  the Hermes manual-profile work from the mikrotik working tree (not HEAD);
  adopt the pre-commit template plus ported Hermes gates; run the offline
  validation gates and obtain a fresh fingerprint-bound review.
- **Out of scope and constraints:**
  - Gate 2 deployment and all privileged runtime work: rootless Podman, SELinux
    `:z`/`:Z` relabel, DAC to `gateway-state`, systemd interruption/recovery,
    reboot persistence, guest/provider/messaging acceptance. These stay
    **NOT RUN**.
  - Server-side GitHub branch protection is deferred to a later milestone; local
    hooks remain convenience-only enforcement for milestone 1.
  - No contact with deployment targets, guests, providers, or routers.
  - No credentials provisioned. Credential-bearing files (`.mcp.json`,
    `.claude/settings.local.json`) are never extracted.
  - Existing dirty worktrees in `dev-toolbox`, `mikrotik` and
    `fedora-virtualization-host` are preserved; only additive edits to
    dev-toolbox hooks/templates are in scope.
  - dev-toolbox is a local-only repository (no remote); it cannot be pinned by a
    public commit or published without creating a remote.
- **Acceptance criteria (gates):**
  - **G1** dev-toolbox: parity checker green, setup tests pass, all three
    profiles verify, bumped hooks actually execute and report the pinned
    versions.
  - **G2** dev-container digest published and CI runs the same pinned gates
    against that digest with results matching the local container.
  - **G3** rebuilt image chain is internally consistent (each child's
    `io.dev-toolbox.parent-id` equals its parent's ID) and
    `scripts/verify.sh infra <new-container>` prints `PASS`.
  - **G4** extension validator asserts every declared extension tool's
    presence/version and re-asserts the base verify contract, writing nothing.
  - **G5** provenance record captures source repo, branch, HEAD, changed/untracked
    counts, diffstat, fingerprint algorithm and values.
  - **G6** no excluded path present; secret scan clean.
  - **G7** every Lefthook gate mapped to a pre-commit successor; the template
    installed; `pre-commit run --all-files` plus an explicit `--files` pass pass.
  - **G8** all offline suites reproduce their recorded results on the migrated
    tree, the previously unrun lint/format gates execute, and a fresh
    fingerprint-bound offline review is recorded.
- **Approval date and timezone:** 2026-09-20, America/Bogota (UTC−05).
- **Approval reference:** user message supplying the destination repository
  `https://github.com/securexai/hermes-fedora-host.git` and "proceed"
  (2026-09-20), together with the preceding decision answers: canonical bumps as
  a separate verified change; registry/digest CI parity; local hooks only for
  milestone 1.
- **Authorized actions and boundaries:** cloning the empty destination
  repository, editing dev-toolbox hooks/templates for the three approved
  changes, rebuilding Toolbox images and creating new containers, publishing an
  image to a registry (pending credentials), extracting files into
  `hermes-fedora-host`, running offline tests and non-writing lint, committing
  and pushing to `origin` of `hermes-fedora-host`. Not authorized: runtime or
  deployment execution, Gate 2, pushing a dev-toolbox remote that does not
  exist, or provisioning credentials.

## Tasks

| ID | Task and dependencies | Progress | Gate and expected result | Gate status | Evidence / docs / next action |
| --- | --- | --- | --- | --- | --- |
| T01 | Harden canonical dev-toolbox: bump `shellcheck-py` v0.10.0.1 → v0.11.0.1; bump `markdownlint-cli2` v0.18.1 → v0.23.3; add check-only shfmt gate to the shipped template (root dogfood deferred — see decisions). Deps: none | ✅ DONE | `scripts/check-precommit-parity.sh` green; `scripts/test-setup.sh` PASS; `scripts/verify.sh base\|python\|infra` PASS; bumped hooks execute and report pinned versions | ✅ PASS | All gates green 2026-09-20. shellcheck hook reports 0.11.0; markdownlint rev `916ad0a` (v0.23.3); `shfmt (check only)` runs. dev-toolbox change intentionally left uncommitted (repo has no remote) |
| T02 | Publish `dev-base`/`dev-python`/`dev-infra:fedora-44` to a registry; add digest-pinned CI running the same gates. Deps: T01 | ⬜ TODO | CI and local container produce matching results; digests recorded | ⬜ NOT_RUN | Likely 🚧 BLOCKED: `gh` token scopes lack `write:packages` |
| T03 | Reconcile image chain (base tag `72f3583d` vs children built from untagged `b82aa0f9`); create fresh container `dev-infra-hermes`. Deps: T01 | ✅ DONE | every child `parent-id` == parent ID; `verify.sh infra dev-infra-hermes` PASS | ✅ PASS | base `72f3583d` → python `965ea02e` (parent `72f3583d`) → infra `af934ead` (parent `965ea02e`); container on `af934ead`; verify PASS; RPM manifest 385 pkgs, sha256 `860b9dfe…` |
| T04 | Author `toolbox/extensions.yaml` + validator + installer (shellspec 0.28.1; ruff, ty, yamllint via `uv.lock`). Deps: T03 | ✅ DONE | validator asserts tools and re-asserts the base contract, modifying no tracked file | ✅ PASS | shellspec 0.28.1 installed and validated; ruff 0.16.8, ty 0.0.82, yamllint 1.38.0 via `uv run --locked`; all checks PASS |
| T05 | Repository scaffold, `.gitignore`, `pyproject.toml` (`requires-python >=3.13`, `.python-version` 3.14), `uv.lock`, `PROVENANCE.md`. Deps: none | ✅ DONE | provenance records source HEAD `130bf8f2`, 14/0, diffstat, algorithm, `d7a336b6…`, `c82e470c…` | ✅ PASS | PROVENANCE.md records source state, companion artifacts, template hashes and image IDs; `uv.lock` resolved (6 packages) |
| T06 | Extract Hermes manual profile, docs, tests, evidence; exclude runtime/deployment; sanitize site coupling. Deps: T05 | ⬜ TODO | no excluded path present; betterleaks clean | ⬜ NOT_RUN | Pending |
| T07 | Adopt pre-commit template + port Hermes pre-push/rehearsal gates; record gate parity map. Deps: T01, T06 | ⬜ TODO | full parity map; `pre-commit run --all-files` and `--files` pass | ⬜ NOT_RUN | Pending |
| T08 | Offline validation on migrated tree + fresh fingerprint-bound review. Deps: T07 | ⬜ TODO | suites reproduce: 358/0, 142/0, 43/0, 64/0, 30/0, 9/0, 21 OK, 217/0, rehearsal PASS; lint gates run; review recorded | ⬜ NOT_RUN | Satisfies the §14.8 outstanding action |
| T09 | Close-out: single execution record finalized; branch protection revisited. Deps: T08 | ⬜ TODO | outcome, limitations and next action recorded | ⬜ NOT_RUN | Pending |

## Evidence history

### Baseline reconnaissance (read-only)

- **Command or review method and working directory:** `git status`,
  `git rev-parse`, `git ls-remote`, `podman image inspect`, and fingerprint
  recomputation from `/var/home/aicloudopspecial/code/repos`
- **Expected result:** source identities and image provenance match the approved
  plan
- **Actual result and status:** matches. Destination
  `https://github.com/securexai/hermes-fedora-host.git` cloned empty (no
  branches). `dev-toolbox` has **no remote**. mikrotik `130bf8f2` with 14
  modified / 0 untracked; recomputed dirty-input fingerprint
  `d7a336b635f13100164a71054f8528f03565fe1100171c02112a5892ed403d87`. Base tag
  `72f3583d5e07` is newer than the untagged `b82aa0f9088a` that `dev-python`
  (`fa2c9fa02fbe`) and `dev-infra` (`7d2aff394c43`) were built from; container
  `dev-base-44` runs the stale `b82aa0f9088a`.
- **Checked files, artifact, or relevant state:** `.pre-commit-config.yaml` and
  `templates/.pre-commit-config.yaml` in dev-toolbox pin `shellcheck-py`
  v0.10.0.1 and `markdownlint-cli2` v0.18.1; neither config has a shfmt gate.
- **Documentation updated:** this record.
- **Sanitized evidence link, if needed:** none

Additional provenance:

- **Timestamp with timezone:** 2026-09-20T22:13−05:00
- **Environment and relevant versions/configuration:** Fedora Linux 44.20260918.0
  (Kinoite); Bash 5.3.9; Python 3.14.7; `podman` and `toolbox` present; `uv`,
  `ruff`, `pre-commit`, `shellcheck`, `shfmt`, `markdownlint-cli2`, `commitlint`,
  `shellspec`, `trivy`, `lefthook` absent from the host.
- **Tested revision or artifact fingerprint, including relevant dirty/untracked
  inputs:** mikrotik `d7a336b6…` (14 modified, 0 untracked); dev-toolbox
  `151c1b47537f1cbb0f5f478c8b9894040ea985b9` with 8 modified, 1 deletion,
  9 untracked.
- **Upstream version verification:** `shellcheck-py` publishes tag `v0.11.0.1`
  (and a `v0.11.0.1-1` re-tag); `markdownlint-cli2` latest tag is `v0.23.3`.

### T01 — canonical dev-toolbox hardening (Gate 1)

- **Command or review method and working directory:** `scripts/check-precommit-parity.sh`, `scripts/test-setup.sh`, `scripts/verify.sh <profile> dev-<profile>-44`, and a throwaway-repo `pre-commit run --all-files`, from `/var/home/aicloudopspecial/code/repos/dev-toolbox`
- **Expected result:** parity green; setup tests pass; all three profiles verify; the bumped hooks resolve at the pinned revisions and execute
- **Actual result and status:** ✅ PASS, all four checks.
  - `scripts/check-precommit-parity.sh` exit 0.
  - `scripts/test-setup.sh` → `PASS: profile ordering, repeat setup, stale containers, invalid input, build failure, build-only, parent changes and overrides`.
  - `scripts/verify.sh base|python|infra` → `PASS` for all three, against the Fedora 44 containers.
  - Throwaway repo using the template config: `pre-commit run --all-files` exit 0, every hook Passed. The `shellcheck-py` environment resolves to commit `745efac` and reports `version: 0.11.0`; `markdownlint-cli2` resolves to `916ad0a` (= `v0.23.3`); the new `shfmt (check only)` hook Passed.
- **Checked files, artifact, or relevant state:** `dev-toolbox/.pre-commit-config.yaml` (pins bumped only) and `dev-toolbox/templates/.pre-commit-config.yaml` (pins bumped plus the shfmt gate)
- **Documentation updated:** this record; `docs/hook-parity.md`
- **Sanitized evidence link, if needed:** none

Additional provenance:

- **Timestamp with timezone:** 2026-09-20, America/Bogota (UTC−05)
- **Environment and relevant versions/configuration:** verification ran inside `dev-base-44`, `dev-python-44` and `dev-infra-44`; the `infra` profile reported Python 3.14.7, uv 0.12.9, ruff 0.16.6, restic 0.19.1
- **Tested revision or artifact fingerprint, including relevant dirty/untracked inputs:** dev-toolbox remains dirty (8 modified, 1 deletion, 9 untracked) on `codex/toolbox-profiles` @ `151c1b47`; the two config edits are uncommitted on top, so a dev-toolbox commit SHA is not yet available to pin
- **shfmt scoping evidence (read-only):** `shfmt -d -l -i 2 -ci -bn` over dev-toolbox's 7 shell files produced **941 diff lines** (`bootstrap-repo.sh` 63, `scripts/check-precommit-parity.sh` 12, `scripts/pnpm-host.sh` 539, `scripts/test-pnpm-host.sh` 181, `scripts/test-setup.sh` 60, `scripts/verify.sh` 12, `setup.sh` 74). Enabling the gate in dev-toolbox's own config would therefore require reformatting unrelated in-progress work, so it was scoped to the template.

### T03 — Toolbox image-chain reconciliation (Gate 3)

- **Command or review method and working directory:** `./setup.sh infra --build-only`; `CONTAINER_NAME=dev-infra-hermes ./setup.sh infra`; `bash scripts/verify.sh infra dev-infra-hermes` — from `/var/home/aicloudopspecial/code/repos/dev-toolbox`
- **Expected result:** each derived image's `io.dev-toolbox.parent-id` equals its parent's image ID; the new container runs the current infra image; verification prints `PASS`
- **Actual result and status:** ✅ PASS. base `72f3583d…` (no parent) → python `965ea02e…` (parent `72f3583d…`) → infra `af934ead…` (parent `965ea02e…`). Container `dev-infra-hermes` runs `af934ead…`. `verify.sh infra dev-infra-hermes` → `PASS: infra Toolbox tools, paths, offline smoke checks and synthetic secret detection`.
- **Checked files, artifact, or relevant state:** image IDs, `io.dev-toolbox.parent-id` labels, container image; RPM manifest 385 packages, sha256 `860b9dfeae6d6d3e2429518b046754d4fb7016e82625117d94d041d03ac01374`
- **Documentation updated:** this record; `PROVENANCE.md`
- **Sanitized evidence link, if needed:** none

Additional provenance: 2026-09-20, America/Bogota (UTC−05). The pre-existing `dev-base-44` container still references the untagged base `b82aa0f9…`; it was left untouched and is superseded by `dev-infra-hermes`.

### T04 — Declared project tool extensions (Gate 4)

- **Command or review method and working directory:** `toolbox/install-extensions.sh` then `toolbox/verify-extensions.sh`, inside `dev-infra-hermes`, from the repository root
- **Expected result:** every declared extension is present at its pinned version and the shared profile contract still holds
- **Actual result and status:** ✅ PASS. `shellspec 0.28.1` installed from the checksum-pinned upstream release; `ruff 0.16.8`, `ty 0.0.82`, `yamllint 1.38.0` resolved through `uv run --locked`; all 11 profile tools present; RPM manifest non-empty; all five managed `/opt` directories writable. Validator output ends `PASS: declared extensions and profile contract verified`.
- **Checked files, artifact, or relevant state:** `toolbox/extensions.yaml`, `toolbox/install-extensions.sh`, `toolbox/verify-extensions.sh`, `pyproject.toml`, `uv.lock`
- **Documentation updated:** this record; `PROVENANCE.md`; `docs/hook-parity.md`
- **Sanitized evidence link, if needed:** none

Additional provenance: shellspec tarball `shellspec-dist.tar.gz` is 76 365 bytes with SHA-256 `350d3de04ba61505c54eda31a3c2ee912700f1758b1a80a284bc08fd8b6c5992`; upstream publishes no digest, so this value was computed from the pinned release and is recorded in `toolbox/extensions.yaml`. Both scripts pass `shfmt -d -i 2 -ci -bn` and `shellcheck`. `uv run --locked` may materialise the gitignored `.venv`; no tracked file is modified.

### T05 — Repository scaffold and provenance (Gate 5)

- **Command or review method and working directory:** repository scaffolding plus `uv lock`, from the repository root
- **Expected result:** provenance names the exact source state, including the uncommitted corrections
- **Actual result and status:** ✅ PASS. `PROVENANCE.md` records the source repo/remote/branch/HEAD `130bf8f2…`, 14 modified / 0 untracked, diffstat 1400/109, both fingerprints, the fingerprint algorithm, the five correction/review artifacts with SHA-256, the six adopted template hashes, the three image IDs and the RPM-manifest hash. `uv.lock` resolved 6 packages on CPython 3.14.7.
- **Checked files, artifact, or relevant state:** `PROVENANCE.md`, `pyproject.toml`, `.python-version` (3.14), `uv.lock`, `.gitignore`
- **Documentation updated:** this record
- **Sanitized evidence link, if needed:** none

Additional provenance: 2026-09-20, America/Bogota (UTC−05). dev-toolbox is local-only (no remote), so the adopted template is identified by file hash rather than by a dev-toolbox commit.

## Decisions and approved scope changes

| Date and timezone | Decision and reason | Approval reference when required | Affected tasks / evidence |
| --- | --- | --- | --- |
| 2026-09-20 −05 | Repository is `hermes-fedora-host` at `~/code/repos/hermes-fedora-host`, initial branch `main`, work on a feature branch | User-supplied destination and "proceed" | T05–T09 |
| 2026-09-20 −05 | Profile basis is `infra`; it provides the Python 3.14.7 + PyYAML 6.0.3 environment the reviewed Hermes evidence was produced on | Preceding decision round | T03, T04 |
| 2026-09-20 −05 | Canonical bumps (ShellCheck 0.11.0 parity, markdownlint 0.23.3, shfmt gate) change dev-toolbox as a separate, verified change rather than project-local overrides | Decision answer: "Change dev-toolbox as a separate, verified change" | T01, T07 |
| 2026-09-20 −05 | CI parity is achieved by publishing the dev image and pinning CI by digest, not by a generic runner | Decision answer: "Publish dev-infra… pin CI by digest" | T02 |
| 2026-09-20 −05 | Server-side branch protection is deferred; local hooks only for milestone 1. Accepted deviation from the gold standard (GitHub not authoritative yet) | Decision answer: "Local hooks only for the first milestone" | T09 |
| 2026-09-20 −05 | Project language tooling (ruff, ty, PyYAML, yamllint) is pinned through the project lockfile; the `infra` globals are convenience only | Gold-standard table | T04, T05, T07 |
| 2026-09-20 −05 | Runtime tooling (restic execution, Trivy, systemd/systemdUkify/sbsign/virt-firmware, host package set) stays out of the development profile | Gold-standard table | T06 |
| 2026-09-20 −05 | The `shfmt` gate ships in the template but is **not** enabled in dev-toolbox's own dogfood config, because dev-toolbox's shell files are not yet formatted to `-i 2 -ci -bn` (941 diff lines across 7 files, including unrelated untracked pnpm scripts). Enabling it in dev-toolbox is a separate follow-up | Bounded implementation decision under the approved "add shfmt gate"; avoids reformatting unrelated in-progress work | T01, T07 |

## Handoff / closure

- **Current outcome:** T01, T03, T04 and T05 complete with Gates 1, 3, 4 and 5
  PASS. The dev-toolbox standard is hardened and verified; the image chain is
  internally consistent (`dev-infra-hermes` on `af934ead…`); project extensions
  are declared, installed and validated; provenance is recorded.
- **Remaining gates and blockers:** G2 NOT_RUN and expected 🚧 BLOCKED until a
  registry credential with package-write scope exists (current `gh` token scopes:
  `admin:public_key`, `gist`, `read:org`, `repo`). G6–G8 NOT_RUN (extraction not
  started).
- **Material limitations:** the reviewed Hermes corrections remain an
  uncommitted working-tree delta in mikrotik; dev-toolbox is uncommitted and has
  no remote, so the adopted template is identified by file hash, not commit SHA;
  server-side branch protection is deferred; runtime acceptance is not covered by
  any gate here.
- **Exact next action:** execute T06 — extract the Hermes manual profile, docs,
  tests and evidence from the mikrotik **working tree** (not HEAD), excluding
  runtime/deployment assets and credential files, and sanitize site coupling.
- **Final state:** ACTIVE
