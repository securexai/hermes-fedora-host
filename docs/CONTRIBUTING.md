# Contributing

This repository holds the complete Hermes Fedora host work: the manual profile
(gateway + offline worker over a shared Unix socket), the installation and
certification entrypoints, the unattended controller, the VM assets and specs,
the guides and the dated evidence record. The unrelated MikroTik network,
Kubernetes and workstation components stay in the source repository and are not
part of this tree.

## Repository rules

- Work on a feature branch. Do not commit directly to `main`.
- Use Conventional Commits.
- Run the offline checks below inside the `dev-infra-hermes` Toolbox before
  pushing, from the repository root.

## Offline checks

Run the whole offline set through the single shared entrypoint — the same
command the `pre-push` hook uses:

```bash
toolbox run --container dev-infra-hermes bash -c \
  'cd ~/code/repos/hermes-fedora-host && bash toolbox/run-offline-checks.sh'
```

The individual suites it runs:

| Check | Command |
| --- | --- |
| Manual profile (primary parity gate) | `bash tests/test-hermes-manual-profile.sh` |
| Manual review regressions (F1–F4, C1–C5) | `bash tests/test-hermes-manual-review.sh` |
| Backup fault injection | `bash tests/test-hermes-manual-backup.sh` |
| Configure drift and convergence | `bash tests/test-hermes-manual-configure.sh` |
| Contract ownership and mount safety | `bash tests/test-hermes-manual-contract.sh` |
| M01 temporary-state cleanup | `bash tests/test-hermes-manual-m01-tempdir.sh` |
| Clean-install rehearsal gate | `bash scripts/hermes/manual/boot/rehearse-clean-install.sh` |
| Guide and deployment-tree checks | `bash tests/test-hermes-guide.sh` |
| Deployment and VM ShellSpec specs | `toolbox/.tools/shellspec/shellspec spec/` |
| Reviewed Python unit allowlist | `python3 -B tests/run-reviewed-suites.py --set offline` |
| Full working-tree secret scan | `bash toolbox/scan-secrets.sh` |
| Migration manifest | `python3 toolbox/generate-migration-manifest.py --verify` |

The manifest check recomputes destination hashes, actual working-tree executable
modes and the payload identity (which deliberately excludes the manifest itself;
the manifest's own SHA-256 is reported separately). It parses the recorded
identity block strictly and, when the `mikrotik`, `dev-toolbox` and companion
checkouts named in [PROVENANCE.md](../PROVENANCE.md) are present, re-derives every
recorded HEAD, dirty-input fingerprint, audit line and provenance row
(source-aware verification). Without them it reports destination-only verification
explicitly and warns that identity was **not** re-derived. Regenerate with
`python3 toolbox/generate-migration-manifest.py` after any change to the tree, and
add a reason to `docs/migration-adaptations.txt` for every newly adapted file.

The Python suites are **not** discovered. `tests/offline_allowlist.txt` lists the
exact reviewed `module.Class` (and, for the mixed ssh-key-only class,
`module.Class.method`) targets that make up the offline set. The boundary is
**class-level**: a `module.Class` entry approves the whole class, so it
automatically runs every `test*` method added to that class later, while a
`module.Class.method` entry approves one method only. A new module or class does
not run, and installing libguestfs, a kernel package, `ukify`, dracut or
`openssh-server` does not widen the gate into real VM, disk, firmware or
host-service work, until it is reviewed and added to the allowlist.

Two further entrypoints are deliberately separate:

| Entrypoint | Purpose |
| --- | --- |
| `toolbox/run-check-only-lint.sh` | Check-only lint (ShellCheck, shfmt, Markdown, read-only baseline hooks) over the tracked **and untracked** working tree. Used by certification; never rewrites files. |
| `toolbox/run-integration-checks.sh` | Opt-in real-tooling integration set from `tests/integration_allowlist.txt`. Reports **NOT RUN** and exits non-zero when prerequisites are missing, rather than passing by omission. |

`test-hermes-manual-profile` is the gate that also checks documentation parity
between the manual `README.md` and the deployment guide.

Declared tool extensions are provisioned with `toolbox/provision-environment.sh`
(repository-local ShellSpec plus `uv sync --locked`) and validated with
`toolbox/verify-extensions.sh`; see [ENVIRONMENT.md](ENVIRONMENT.md).

### Secret scanning

The pre-commit `betterleaks` hook is a **staged** scan: its upstream entry is
`betterleaks git --pre-commit --staged`, so it scans nothing when nothing is
staged and passing filenames cannot widen it. It is not full-tree coverage.
`toolbox/scan-secrets.sh` is the full-working-tree scan: it enumerates tracked
and untracked non-ignored files, disables live provider validation
(`--validation=false`), and first scans a fresh synthetic token as a positive
control so a scanner that silently finds nothing fails instead of passing.

The environment is described in [ENVIRONMENT.md](ENVIRONMENT.md): the retired
`devbox run -- <cmd>` form translates to running `<cmd>` inside
`dev-infra-hermes`.

### ShellSpec

ShellSpec 0.28.1 is installed as a declared extension and runs the deployment and
VM specs:

```bash
toolbox/.tools/shellspec/shellspec spec/
```

### Suites that are not run offline

These exist in the tree for their owners but are **not** part of the offline
gate, because they need a VM, a network, live infrastructure or real host
tooling:

| Suite | Why it is excluded |
| --- | --- |
| `tests/test-hermes-e2e-vm.sh` | Drives real VM lifecycle through `hermes-certify-vm.sh` |
| `tests/test-hermes-links.sh` | Fetches external documentation URLs over the network |
| `tests/integration_allowlist.txt` targets (`test_hermes_lab_disk.LabDiskIntegrationTests`, `test_hermes_unattended.BootBuildIntegrationTests`, `test_hermes_unattended.InstalledGuestfishParserTests`, `test_hermes_tpm_profile.PackagedDracutIntegrationTests`, `test_ssh_key_only.KeyOnlyTests.test_real_sshd_candidate_and_first_value_conflict`) | Real libguestfs disk/appliance work, UKI builds, packaged dracut archive readback and a real `/usr/sbin/sshd`. Run only through `toolbox/run-integration-checks.sh`; acceptance remains NOT RUN otherwise |

The migrated lab, SELinux, TPM-profile and ssh-key-only **unit** classes are part
of the reviewed offline allowlist and do run in the gate. Only the real-tooling
integration cases are separated.

## What these checks do not establish

The suites use synthetic fixtures and mocked privileged commands. They do **not**
establish runtime or deployment acceptance. Rootless Podman behaviour, SELinux
`:z`/`:Z` relabelling, DAC access to `gateway-state`, systemd interruption and
recovery, reboot persistence, and real guest or provider acceptance all remain
**NOT RUN** and require separate authorization.

`test-hermes-guide.sh` asserts the presence and consistency of the installation
guide, the deployment entrypoints, the VM assets and the evidence documents. Those
assets now exist in this repository, so the suite runs here. Two of its original
assertions inspected the *source* repository's structure (a `lefthook.yml` and
the source `AGENTS.md`); they were re-pointed at this repository's equivalents —
the pre-push entrypoint and the local `AGENTS.md` — in the repository migration.

## Sources

The reviewed artifact, its fingerprints and its evidence history are recorded in
[PROVENANCE.md](../PROVENANCE.md) and
[docs/plans/2026-09-20-hermes-fedora-host-toolbox-migration.md](plans/2026-09-20-hermes-fedora-host-toolbox-migration.md).
