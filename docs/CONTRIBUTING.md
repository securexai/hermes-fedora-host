# Contributing

This repository holds the Hermes manual-profile work. It does **not** contain the
runtime or deployment assets (VM creation, provisioning entrypoints, unattended
controller); those remain in the source repository.

## Repository rules

- Work on a feature branch. Do not commit directly to `main`.
- Use Conventional Commits.
- Run the offline checks below inside the `dev-infra-hermes` Toolbox before
  pushing, from the repository root.

## Offline checks

| Check | Command |
| --- | --- |
| Manual profile (primary parity gate) | `bash tests/test-hermes-manual-profile.sh` |
| Manual review regressions (F1–F4, C1–C5) | `bash tests/test-hermes-manual-review.sh` |
| Backup fault injection | `bash tests/test-hermes-manual-backup.sh` |
| Configure drift and convergence | `bash tests/test-hermes-manual-configure.sh` |
| Contract ownership and mount safety | `bash tests/test-hermes-manual-contract.sh` |
| M01 temporary-state cleanup | `bash tests/test-hermes-manual-m01-tempdir.sh` |
| Python config hardening | `python3 -B -m unittest discover -s tests -p test_hermes_manual_hardening.py` |
| Clean-install rehearsal gate | `bash scripts/hermes/manual/boot/rehearse-clean-install.sh` |
| Declared tool extensions | `toolbox/verify-extensions.sh` |

`test-hermes-manual-profile` is the gate that also checks documentation parity
between the manual `README.md` and the deployment guide.

### ShellSpec

ShellSpec 0.28.1 is installed as a declared extension, but **no in-scope spec is
retained**. The only upstream spec, `spec/hermes/deploy_spec.sh`, exercises the
deployment entrypoints (`hermes-deploy.sh`, `hermes-certify-vm.sh`, provider
authentication, VM lifecycle) that are deliberately out of scope, so it is
**N/A** here, like `test-hermes-guide.sh`.

## What these checks do not establish

The suites use synthetic fixtures and mocked privileged commands. They do **not**
establish runtime or deployment acceptance. Rootless Podman behaviour, SELinux
`:z`/`:Z` relabelling, DAC access to `gateway-state`, systemd interruption and
recovery, reboot persistence, and real guest or provider acceptance all remain
**NOT RUN** and require separate authorization.

`test-hermes-guide.sh` from the source repository is a whole-repository
documentation suite; it asserts the presence of the runtime and deployment assets
that are deliberately out of scope here, so it is **N/A** in this repository.

## Sources

The reviewed artifact, its fingerprints and its evidence history are recorded in
[PROVENANCE.md](../PROVENANCE.md) and
[docs/plans/2026-09-20-hermes-fedora-host-toolbox-migration.md](plans/2026-09-20-hermes-fedora-host-toolbox-migration.md).
