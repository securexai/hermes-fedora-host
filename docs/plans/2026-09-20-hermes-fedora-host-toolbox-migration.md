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
| T01 | Harden canonical dev-toolbox: bump `shellcheck-py` v0.10.0.1 → v0.11.0.1; bump `markdownlint-cli2` v0.18.1 → v0.23.3; add check-only shfmt local gate, in root and template configs. Deps: none | ⬜ TODO | `scripts/check-precommit-parity.sh` green; `scripts/test-setup.sh` PASS; `scripts/verify.sh base\|python\|infra` PASS; bumped hooks report pinned versions | ⬜ NOT_RUN | Pending |
| T02 | Publish `dev-base`/`dev-python`/`dev-infra:fedora-44` to a registry; add digest-pinned CI running the same gates. Deps: T01 | ⬜ TODO | CI and local container produce matching results; digests recorded | ⬜ NOT_RUN | Likely 🚧 BLOCKED: `gh` token scopes lack `write:packages` |
| T03 | Reconcile image chain (base tag `72f3583d` vs children built from untagged `b82aa0f9`); create fresh container `dev-infra-hermes`. Deps: T01 | ⬜ TODO | every child `parent-id` == parent ID; `verify.sh infra dev-infra-hermes` PASS | ⬜ NOT_RUN | Pending |
| T04 | Author `toolbox/extensions.yaml` + non-writing validator (shellspec 0.28.1; ruff, ty, PyYAML, yamllint via `uv.lock`). Deps: T03 | ⬜ TODO | validator asserts tools and re-asserts base contract, writes nothing | ⬜ NOT_RUN | Pending |
| T05 | Repository scaffold, `.gitignore`, `pyproject.toml` (`requires-python >=3.13`, `.python-version` 3.14), `uv.lock`, `PROVENANCE.md`. Deps: none | ⬜ TODO | provenance records source HEAD `130bf8f2`, 14/0, diffstat, algorithm, `d7a336b6…`, `c82e470c…` | ⬜ NOT_RUN | Started: baseline record (this file) |
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

## Handoff / closure

- **Current outcome:** baseline saved; destination repository cloned (empty);
  no implementation performed.
- **Remaining gates and blockers:** all gates NOT_RUN. T02 is expected to be
  blocked until a registry credential with package-write scope is available.
- **Material limitations:** the reviewed Hermes corrections remain an
  uncommitted working-tree delta in mikrotik; dev-toolbox remains uncommitted and
  remote-less; runtime acceptance is not covered by any gate here.
- **Exact next action:** execute T01 — harden the canonical dev-toolbox hooks in
  root and template configs, then run its verification gates.
- **Final state:** ACTIVE
