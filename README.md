# hermes-fedora-host

Hermes deployment work for a Fedora host, developed against the shared
dev-toolbox Toolbox profile standard (local checkout at
`~/code/repos/dev-toolbox`) rather than the retired Devbox environment.

## Status

Under construction. The approved migration plan is the canonical record:
[docs/plans/2026-09-20-hermes-fedora-host-toolbox-migration.md](docs/plans/2026-09-20-hermes-fedora-host-toolbox-migration.md).

Scope and boundaries of the current milestone:

- Development happens inside the dev-toolbox `infra` Toolbox profile. The host
  itself intentionally has no development toolchain installed.
- Toolbox shares the host home directory and user session. It is a development
  convenience, **not** a security sandbox. Keep credentials out of images.
- Offline checks do **not** establish deployment acceptance. Gate 2 and all
  privileged runtime work (rootless Podman, SELinux relabelling, DAC, systemd
  recovery, reboot, guest/provider acceptance) remain out of scope and unrun.

## License

Not yet declared.
