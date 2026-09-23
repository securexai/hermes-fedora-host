# Repository working rules

This repository holds the Hermes Fedora host work: the reviewed manual profile
(gateway + offline worker over a shared Unix socket), the installation and
certification entrypoints, the VM assets and the dated evidence record. It does
**not** hold production credentials, VM disks, or the unrelated network,
Kubernetes and workstation components that stay in the source repository.

## Reading map

| Component | Entry points |
| --- | --- |
| Installation guide (canonical, human-facing) | [`hermes-fedora-server-install-guide.html`](hermes-fedora-server-install-guide.html) |
| One-command controller | `hermes-deploy.sh`, `scripts/hermes/deploy-lib.sh` |
| Manual profile (M01–M05) | `scripts/hermes/manual/README.md`, `docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md` |
| Manual-profile contract | `docs/HERMES_MANUAL_PROFILE_CONTRACT.md` |
| Unattended controller | `docs/HERMES_UNATTENDED_DEPLOYMENT.md`, `scripts/hermes/unattended/` |
| VM creation and testing | `vm/DEPLOYMENT_TASKS.md`, `docs/VM_TESTING_GUIDE.md` |
| Evidence ledger | `docs/HERMES_INSTALLATION_VERIFICATION.md` |
| Migration provenance | `PROVENANCE.md`, `docs/migration-manifest.txt` |
| Environment and migration record | `docs/ENVIRONMENT.md`, `docs/plans/` |

## Development environment

Development happens inside the dev-toolbox `infra` Toolbox (`dev-infra-hermes`);
the host itself intentionally has no development toolchain. The Toolbox shares
the host home directory and user session, so it is a development convenience,
**not** a security sandbox. Keep credentials out of images and out of Git.

The retired Devbox environment has no equivalent here. `devbox run -- <cmd>` in
preserved historical records translates to running `<cmd>` inside the Toolbox;
see [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md).

## Checks

Run the offline gate set from the repository root inside the Toolbox. The single
shared entrypoint is `toolbox/run-offline-checks.sh` — the same command the
pre-push hook uses.

```bash
toolbox run --container dev-infra-hermes bash -c \
  'cd ~/code/repos/hermes-fedora-host && bash toolbox/run-offline-checks.sh'
```

Offline checks use synthetic fixtures and mocked privileged commands. They do
**not** establish deployment, runtime, SELinux, systemd or provider acceptance.

## Safety and evidence

- Ground every claim in inspected files, command output, or an authoritative
  source. Distinguish a recorded historical result from a live check.
- Never reproduce raw credentials in output, logs, examples or Git artifacts.
  Inspect only the sensitive files a task actually needs.
- Do not deploy, contact deployment targets or guests, run VM lifecycle
  operations, or provision credentials without explicit authorization.
- Preserve evidence: dated plans, `docs/plans/evidence/**`, `docs/reviews/**` and
  `docs/archive/**` are byte-bound to recorded SHA-256 values. Do not reformat or
  "fix" them; if an input changes, mark the affected pass STALE and rerun it.
- Never let an auto-fixing hook see a preserved evidence document. The rewriting
  hooks exclude those paths in `.pre-commit-config.yaml` for this reason.
- Unresolved credential-rotation obligations recorded in the migration history
  remain the operator's responsibility; neither token-shaped text nor a
  historical note proves a credential is valid or revoked.

## Git

- Create a feature branch before editing; do not commit directly to `main`.
- Use Conventional Commits with project-native authorship and no AI attribution.
- Do not commit, push, merge, or modify pull requests unless explicitly asked.
  Inspect status, branch and the exact diff first.
- Preserve existing branches, worktrees and other repositories' dirty work.
- Keep authorized commits atomic and update the owning plan record when a step,
  check, blocker or scope change occurs.
