# Hook and gate parity: Hermes Lefthook → dev-toolbox pre-commit

This maps every gate enforced in the source `mikrotik` repository to its
successor here. It exists so that adopting the shared pre-commit baseline does
not silently drop a Hermes check. Source of truth for the old gates:
`mikrotik/lefthook.yml` at branch `codex/hermes-fedora44-manual-review`.

## Pre-commit stage

| Source gate (Lefthook) | Source command | Successor | Status |
| --- | --- | --- | --- |
| `shellcheck` | `shellcheck {staged_files}` | `shellcheck-py` hook, rev `v0.11.0.1` (**0.11.0**, matching the image RPM) | Ported, version-aligned |
| `shfmt-check` | `shfmt -d -l -i 2 -ci -bn {staged_files}` | local `shfmt` hook, same flags, check-only, `spec/` excluded | Ported (was missing upstream) |
| `markdownlint` | `markdownlint-cli2 --no-globs {staged_files}` | `markdownlint-cli2` hook, rev `v0.23.3` | Ported, version upgraded from 0.18.1 |
| `no-secrets` | `git diff --cached` grep for password/secret/token/key patterns | `betterleaks` hook (`v1.1.2`) with `.betterleaks.toml` | Replaced by a purpose-built scanner |
| `branch-check` | block direct commits to `main` | `no-commit-to-branch` hook (`main`, `master`, `develop`, `release/*`) | Ported |

## Commit-msg stage

| Source gate | Successor | Status |
| --- | --- | --- |
| `conventional-commit` (regex over an 11-type list) | `commitlint` hook with `@commitlint/config-conventional` | Ported |

Hermes's regex allowed `feat|fix|docs|chore|refactor|test|ci|style|perf|build|revert`.
`commitlint.config.js` from the template allows the same eleven types, so no
commit-message convention is lost.

## Pre-push stage

The shared template intentionally omits `pre-push` because no baseline hook uses
that stage. The Hermes-specific suites are therefore ported as an explicit
project extension rather than silently dropped.

| Source gate | Source command | Decision |
| --- | --- | --- |
| `test-hermes-guide` | `./tests/test-hermes-guide.sh` | Ported as a project `pre-push` hook |
| `test-hermes-deploy-spec` | `shellspec spec/hermes/` | **N/A** — the only upstream spec exercises the deployment entrypoints (`hermes-deploy.sh`, `hermes-certify-vm.sh`, provider auth, VM lifecycle) that are out of scope. ShellSpec stays installed as a declared extension for future in-scope unit specs |
| `test-routeros` | `./tests/test-routeros.sh` | Out of scope — stays in the source repository |
| `test-vlan30-firewall` | `./tests/test-vlan30-firewall-deploy.sh` | Out of scope — stays in the source repository |
| `test-nix-guide` | `./tests/test-nix-guide.sh` | Out of scope — stays in the source repository |
| `branch-check` | block direct push to `main` | Local convenience only; server-side protection is deferred |

## Non-hook gates carried across unchanged

These were run manually or by the execution record, not wired into a hook, and
are preserved as project check entrypoints:

- `scripts/hermes/manual/boot/rehearse-clean-install.sh` — emits
  `REHEARSAL=PASS` / `REHEARSAL=FAIL` with `failures=` / `advisories=`.
- `scripts/hermes/promotion-record.sh` — `promotion_record_fingerprint` over a
  fixed path list.
- `scripts/hermes/certification-evidence.sh` — certification transcript
  validation.
- Egress classification and stream redaction checks in `lib-manual-common.sh`,
  with their secret-safe tests.

## Deliberate changes

1. **Lefthook is retired.** It is superseded by pre-commit; running both would
   give two gate definitions that can drift.
2. **`no-secrets` grep is retired** in favour of betterleaks. The grep gate
   excluded `*.md` and a `token = self.` self-assignment; the replacement's rule
   set and allowlist live in `.betterleaks.toml` and must be reviewed for
   equivalent coverage.
3. **markdownlint moves from 0.21.0 to the shared pinned 0.23.3.** The source
   gate used `--no-globs` to avoid a Node heap exhaustion caused by ~2000
   vendored Markdown files under `private/`. Those vendored trees are **not**
   extracted, so the heap problem should not recur; verify on the real tree.
4. **Server-side branch protection is not enabled in this milestone**, so the
   local `no-commit-to-branch` hook is convenience only and is bypassable with
   `--no-verify`. This is a known, accepted deviation.

## Known gap in the standard itself

The `shfmt` gate shipped in the dev-toolbox template is **not** enabled in
dev-toolbox's own dogfood config, because that repository's own shell scripts are
not yet formatted to `-i 2 -ci -bn` (measured 941 diff lines across 7 files,
including two unrelated untracked pnpm scripts). Enabling it there is a
follow-up in dev-toolbox, not in this repository.
