# Environment, checkout location and command translation

## Current development environment

Development happens inside the dev-toolbox `infra` Toolbox. The host itself has
no development toolchain installed.

| Item | Value |
| --- | --- |
| Profile | `infra` (Python, uv, Ruff, PyYAML, yamllint, OpenSSL, iproute, ping, DNS tools, Ncat, Restic) |
| Image | `localhost/dev-infra:fedora-44` |
| Container | `dev-infra-hermes` |
| Editor container | `.devcontainer/devcontainer.json` (same image) |
| Baseline standard | the `dev-toolbox` repository, local-only (no remote) |
| Project extensions | `toolbox/extensions.yaml` (ShellSpec; Ruff/ty/yamllint via `uv.lock`) |

Enter and use it:

```bash
toolbox run --container dev-infra-hermes bash -c 'cd ~/code/repos/DS-Workspace/hermes-fedora-host && bash'
```

The Toolbox shares the host home directory and user session. It is a development
convenience, **not** a security sandbox.

## Checkout location

This repository lives at `~/code/repos/DS-Workspace/hermes-fedora-host`. It is no
longer at the source repository's path, and the source repository's own
documentation refers to a checkout that does not exist on this workstation. When
a preserved document prints an absolute checkout path, treat the current location
above as authoritative.

## Devbox is retired

The source repository used the Devbox environment. This repository uses the
dev-toolbox Toolbox instead; `devbox.json` / `devbox.lock` were deliberately not
migrated. Translate commands like this:

| Retired (Devbox) | Current (dev-toolbox) |
| --- | --- |
| `devbox run -- <cmd>` | run `<cmd>` inside `dev-infra-hermes` |
| `devbox run -- shellcheck …` | `pre-commit run shellcheck --all-files` (error-only repo gate) or `toolbox/run-check-only-lint.sh` (default severity over the certifier set) |
| `devbox run -- shfmt -d -l -i 2 -ci -bn …` | `pre-commit run shfmt --all-files` or `toolbox/run-check-only-lint.sh` |
| `devbox run -- markdownlint-cli2 …` | `pre-commit run markdownlint-cli2 --all-files` (check-only; `fix: false`) |
| `devbox run -- shellspec spec/hermes/ spec/vm/` | `toolbox/.tools/shellspec/shellspec spec/` |
| `devbox run -- python3 -m unittest discover …` | `python3 -B tests/run-reviewed-suites.py --set offline` (explicit reviewed allowlist; discovery is not used) |
| `devbox run -- git diff --check` | `git diff --check` |
| (whole offline suite) | `bash toolbox/run-offline-checks.sh` |
| (full working-tree secret scan) | `bash toolbox/scan-secrets.sh` |
| (check-only lint, tracked + untracked) | `bash toolbox/run-check-only-lint.sh` |
| (opt-in real-tooling integration) | `bash toolbox/run-integration-checks.sh` (NOT RUN when prerequisites are absent) |
| (provision the declared toolchain) | `bash toolbox/provision-environment.sh`, then `toolbox/verify-extensions.sh` |

Lefthook is retired too: the source repository's pre-commit, commit-msg and
pre-push gates were ported to `.pre-commit-config.yaml`. The mapping, including
which source gates are deliberately not carried over, is in
[`hook-parity.md`](hook-parity.md).

## Generated environment state

Provision once per clone with `toolbox/provision-environment.sh`; validate with
`toolbox/verify-extensions.sh`, which runs the tools through `uv run --locked`
and never synchronises. `.venv/` and `toolbox/.tools/` are generated and
gitignored, and their console scripts embed an absolute interpreter path. A
checkout that has been moved (for example relocated under `DS-Workspace/`) can
therefore leave a stale `.venv/bin/<tool>` whose shebang names the old path;
direct execution then fails with exit 126 while `uv run --locked <tool>` still
works. Treat `uv run --locked` and the provisioning script as the supported
entrypoints, and recreate the virtualenv from scratch (remove `.venv`, then
provision) if a stale entrypoint matters. No gate depends on it.

## Current documents versus preserved records

Dated records are preserved byte-for-byte, so their `devbox run --` examples,
absolute paths and environment details are **as written at the time**. They are
history, not current instructions. The rewriting pre-commit hooks exclude the
exact preserved paths listed in `.pre-commit-config.yaml` so their recorded
SHA-256 values stay accurate.

Maintained documents are **not** blanket-excluded from Markdown lint: they are
linted check-only (`.markdownlint-cli2.yaml` sets `fix: false`), so findings are
reported and resolved rather than silently rewritten or ignored.

| Class | Paths | Status |
| --- | --- | --- |
| Current instructions | `README.md`, `AGENTS.md`, `docs/CONTRIBUTING.md`, `docs/ENVIRONMENT.md`, `docs/hook-parity.md`, `toolbox/**`, `tests/**` | Maintained here; Devbox and Lefthook replaced |
| Current guides | `hermes-fedora-server-install-guide.html`, `secure-hermes-installation-plan.html`, `docs/VM_TESTING_GUIDE.md`, `docs/HERMES_UNATTENDED_DEPLOYMENT.md`, `docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md`, `docs/HERMES_MANUAL_PROFILE_CONTRACT.md`, `vm/DEPLOYMENT_TASKS.md`, `setup-ssh-key-only.md` | Adapted for this environment; linted check-only, not blanket-excluded |
| Preserved records | the exact paths listed in `.markdownlint-cli2.yaml` and `.pre-commit-config.yaml`: the dated `docs/plans/2026-09-*.md` records, the preserved `docs/HERMES_*.md` handoffs and ledgers, `docs/plans/evidence/**`, `docs/reviews/**`, `docs/archive/**`, `scripts/hermes/manual/README.md` | Byte-preserved; historical environment references intentionally left intact |

## Evidence-scope rule

The recorded passes apply to the source artifact fingerprint and the environment
they ran in, both captured in [`../PROVENANCE.md`](../PROVENANCE.md) and
[`migration-manifest.txt`](migration-manifest.txt). If any migrated file changes,
the affected pass becomes **STALE for that input**; the original result is
retained, not deleted, and the affected check is rerun. Offline passes never
establish deployment acceptance.

## Outstanding credential obligations

The source repository's migration record notes a live-looking GitHub personal
access token in an untracked, gitignored local file that was deliberately **not**
extracted here, and a local settings file granting broad `sudo`/`podman`/`virsh`
allowances that was likewise not extracted. Rotation and revocation are the
operator's responsibility. Presence of token-shaped text does not by itself prove
a credential is valid or revoked, and no credential is stored in this repository.
