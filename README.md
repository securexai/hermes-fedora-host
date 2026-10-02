# hermes-fedora-host

Hermes deployment work for a Fedora host, developed against the shared
dev-toolbox Toolbox profile standard rather than the retired Devbox environment.

This repository is the home for the Hermes installation and certification code,
the reviewed manual profile, the VM assets, the installation guides and the dated
evidence record. The MikroTik network, Kubernetes and workstation components stay
in the source repository and are not part of this tree.

## Start here

| I want to… | Read |
| --- | --- |
| Run the current disposable Hermes lab | [`docs/HERMES_DISPOSABLE_LAB.md`](docs/HERMES_DISPOSABLE_LAB.md) |
| Prepare the portable production profile (qualification open) | [`docs/HERMES_PRODUCTION_DEPLOYMENT.md`](docs/HERMES_PRODUCTION_DEPLOYMENT.md) |
| Test temporary local encrypted backup and file restore | [`docs/HERMES_LOCAL_BACKUP_FIXTURE.md`](docs/HERMES_LOCAL_BACKUP_FIXTURE.md) |
| Install Hermes on a Fedora host | [`docs/hermes-fedora-server-install-guide.html`](docs/hermes-fedora-server-install-guide.html) |
| Understand the environment and retired Devbox commands | [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) |
| Run the reviewed manual profile (M01–M05) | [`scripts/hermes/manual/README.md`](scripts/hermes/manual/README.md), [`docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md`](docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md) |
| Use the unattended controller | [`docs/HERMES_UNATTENDED_DEPLOYMENT.md`](docs/HERMES_UNATTENDED_DEPLOYMENT.md) |
| Review older VM certification | [`docs/VM_TESTING_GUIDE.md`](docs/VM_TESTING_GUIDE.md), [`vm/DEPLOYMENT_TASKS.md`](vm/DEPLOYMENT_TASKS.md) |
| See what was actually verified, and when | [`docs/HERMES_INSTALLATION_VERIFICATION.md`](docs/HERMES_INSTALLATION_VERIFICATION.md) |
| Check where this tree came from | [`PROVENANCE.md`](PROVENANCE.md), [`docs/migration-manifest.txt`](docs/migration-manifest.txt) |
| Contribute | [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md), [`AGENTS.md`](AGENTS.md) |

## Status

The current lab workflow is the
[disposable Hermes lab](docs/HERMES_DISPOSABLE_LAB.md): routine tests use
network-disabled containers and synthetic services; separately selected VM
checks use disposable, unencrypted Fedora guests. Real provider and Telegram
smoke tests are optional, private operations requiring explicit authorization.
The lab guide defines the commands and acceptance boundaries. The local
`python3 scripts/hermes/lab.py` entrypoint adds named configuration profiles,
prepared VM bases, and quick/VM/candidate test suites; mutating operations
preview unless `--apply` is supplied.

The separate [production bundle workflow](docs/HERMES_PRODUCTION_DEPLOYMENT.md)
adds signed retained artifacts, encrypted-host preflight, a bounded SSH
dispatcher, matching-state rollback and an unattended explicit-disk installation:
the installer generates and escrows every secret, firstboot commissions the host,
and `vm/hermes-production-qualify.py` qualifies a release in one disposable-VM run.
Its [execution record](docs/plans/2026-09-27-hermes-production-bundle.md) tracks
the remaining off-host restore, application and physical-target acceptance gates.

Repository and Toolbox migrations are completed historical work. Their records
remain available for provenance:

- [Repository migration](docs/plans/2026-09-21-hermes-repository-migration.md).
- [Toolbox migration](docs/plans/2026-09-20-hermes-fedora-host-toolbox-migration.md).
- [Branch consolidation](docs/plans/2026-09-26-incremental-repository-organization.md).

Development happens inside `dev-infra-hermes`. Toolbox shares the host home
directory and user session; it is a development convenience, **not** a security
sandbox. Keep credentials out of images. Offline checks do **not** establish
live deployment, SELinux, systemd, guest or provider acceptance. Dated results
and remaining limitations belong to the workflow and inputs actually tested.

### Recorded results versus current source

The installation ledger records real, dated passes on a specific host: manual
profile gates, TPM unlock, Telegram acceptance, memory approval and provider
authentication. Those results belong to the artifact and environment they were
produced on. **They do not certify the current source tree.** See
[`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) for the evidence-scope rule.

## Development

Development checks run inside the `dev-infra-hermes` Toolbox, from the repository
root. One entrypoint runs the whole offline set:

```bash
toolbox run --container dev-infra-hermes bash -c \
  'cd ~/code/repos/hermes-fedora-host && bash toolbox/run-offline-checks.sh'
```

The primary parity gate is `bash tests/test-hermes-manual-profile.sh`; the full
list is in [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). Provision the declared
toolchain once per clone with `toolbox/provision-environment.sh` (the Dev
Container runs it through `postCreateCommand`) and validate it with
`toolbox/verify-extensions.sh`. The default shell is Devbox/Lefthook-free; no
`devbox` command is used or required anywhere in this tree.

## Alternative and historical paths

`hermes-deploy.sh` remains an alternative one-command controller. Its changed
host and Toolbox integration requires fresh certification before acceptance.
The certifier's check gate requires the `dev-infra-hermes` Toolbox container
(see [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)). Treat controller invocations
as unaccepted until a fresh certification passes.

The tree also retains `hermes-simple-deploy.sh` and
`hermes-remediation-wizard.sh`, the manual M01–M05 profile, and the unattended
controller. Retained paths are kept for reference and recovery; their evidence
status is recorded in the ledger and the owning plan record, and none of them is
deployment acceptance on its own.

## Canonical files and compatibility

Deployment implementations live in `scripts/hermes/deploy.sh`,
`scripts/hermes/remediation-wizard.sh`, `scripts/hermes/simple/deploy.sh` and
`vm/hermes-certify-vm.sh`. The original root commands remain location-relative
compatibility launchers; invoke them with the same arguments from any directory.
They do not change the caller working directory.

The full [installation guide](docs/hermes-fedora-server-install-guide.html),
[security plan](docs/secure-hermes-installation-plan.html) and
[SSH setup guide](docs/setup-ssh-key-only.md) live in `docs/`. Root HTML pages
redirect locally, preserving URL fragments, with visible links as a fallback.
The root SSH guide retains its heading anchors and links to canonical sections.
`setup-ssh-key-only.sh` remains standalone for copying to a server or sourcing.

Relocation changes certification inputs: earlier promotion evidence does not
certify these files. See the [execution record](docs/plans/2026-09-26-root-entrypoint-organization.md)
for offline verification and limitations.

## License

Not yet declared.
