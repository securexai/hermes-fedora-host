# Temporary local backup fixture

This fixture exercises encrypted Restic backup over a real, pinned-key SFTP
connection and restores synthetic files into a fresh directory. It is a local
test on the development workstation. It does not establish independent off-host
recovery, restore the Hermes application, or satisfy production commissioning.
The [production qualification record](plans/2026-09-27-hermes-production-bundle.md)
owns the approved scope and acceptance results.

## Resource boundary

- Container: `hermes-preproduction-backup`, rootless Podman.
- Listener: `127.0.0.1:22226` only; no host SSH or firewall changes.
- Limits: 256 MiB memory, one CPU, 64 PIDs, read-only image filesystem.
- State: ignored `.toolbox/hermes-production-backup/`, plus an adjacent lock.
- Image: the retained, pinned worker OCI archive. No image build or pull.
- Client: existing Restic and SSH in `dev-infra-hermes`; no package installation.
- Data: synthetic files and generated fixture-only SSH keys and Restic password.

The worker image runs a separate SFTP-only configuration with no shell, forwarding
or password authentication. A chroot limits SFTP paths to the fixture repository.
Only the server configuration/key directory and encrypted repository are mounted
from the host. The client key and Restic password stay outside the server mounts.
SELinux private relabeling applies only to those two owned directories.

Before creating or restarting the service, the runner requires at least 20 GiB
free on the host filesystem. This is a startup reserve, not a storage quota.
No provider credentials, real application state or external backup service are
inputs. Do not put real data into this fixture.

## Run from the repository root on the host

Preview has no subprocess or filesystem side effects:

```bash
python3 -B scripts/hermes/backup-fixture.py test
```

After approval for the named local resource, run the test:

```bash
python3 -B scripts/hermes/backup-fixture.py test --apply
python3 -B scripts/hermes/backup-fixture.py status
```

The runner starts the owned container, verifies the pinned SFTP connection,
rejects wrong client keys and host keys, initializes the encrypted repository,
and requires rejection of an incorrect Restic password. It backs up the synthetic
tree, reads and checks all repository data, restores into a fresh isolated
directory and compares file content, sizes and modes. It also verifies the
container's identity, localhost binding, limits, mounts and security settings.
The plaintext-marker check supplements Restic's integrity/authentication checks;
it is not a cryptographic audit.

Run the same `test --apply` command again to check convergence. It keeps the
container identity, keys, password and source data and uses Restic's
`--skip-if-unchanged` to retain exactly one snapshot. Backup runs from inside the
source directory, so changing ancestor-directory metadata is not archived.
Each attempt gets a new
restore directory and sanitized report. This deliberate evidence retention is
the only expected accumulating state on successful unchanged test reruns.

`test --apply` stops the owned container on success or failure. It preserves
the encrypted repository, private fixture keys/password, restored synthetic
files and reports. Check failures return a nonzero exit code. A failed stop is
reported explicitly and changes the result to FAIL.

## Lifecycle and interrupted attempts

All operations use an exclusive task lock. `status` acquires that lock too, so
its first invocation can create the adjacent private lock file. `up --apply`
starts or reuses the service without performing the backup test. Stop it with:

```bash
python3 -B scripts/hermes/backup-fixture.py stop --apply
python3 -B scripts/hermes/backup-fixture.py stop --apply
```

A second stop reports `already-stopped` without changing retained data. The
runner refuses unknown directories, name/port conflicts, symlinks, changed
private files, source drift, missing owned containers and changed container
identity/settings. It never removes or prunes containers, images or directories.

If interrupted after container creation but before its ID was recorded, the
runner can adopt only the matching ownership label, pinned image and verified
configuration. An incomplete key/state initialization or partial Restic
repository is preserved and refused for inspection. Do not delete ownership
metadata to force a retry. Inspect the sanitized report and fix the specific
cause; container replacement or data removal requires a separately reviewed
action.

Reports under `.toolbox/hermes-production-backup/reports/` contain synthetic
file hashes, result codes and resource/snapshot identifiers. Keep private keys,
password files and raw SSH/Restic command output out of Git and chat. Retained
fixture credentials are solely for this disposable test resource.

## Evidence boundary

The fixture shares the workstation's storage and failure domain with any local
VMs. Local success leaves `encrypted_offhost_recovery` unverified and does not
close the complete production restore gate. The production preflight remains
unchanged. VM installation, application/provider tests, physical boot recovery,
production deployment and independent recovery storage require their own scope
and evidence.
