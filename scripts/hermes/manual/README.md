# Hermes manual profile: offline worker transport

This directory holds the two-container artifacts for the approved manual profile:
a digest-pinned upstream gateway and an offline Fedora worker reached only over a
shared Unix socket.

**Current contract:** [the manual-profile contract](../../../docs/HERMES_MANUAL_PROFILE_CONTRACT.md)
is authoritative for the posture these artifacts are supposed to produce; this file describes the
artifacts themselves. The approved improvement plan and its evidence record is
[the 2026-09-20 execution record](../../../docs/plans/2026-09-20-hermes-manual-profile-improvement.md).

Historical status, kept dated rather than repeated: the M01–M06 gates passed on the reference host on
2026-09-13/14 with nine recorded deviations, and the B6 clean-install runbook passed on 2026-09-14.
Those results belong to that host and that text; see
[the manual handoff](../../../docs/HERMES_MANUAL_HANDOFF.md) and
[the B6 handoff](../../../docs/HERMES_B6_CLEAN_INSTALL_HANDOFF.md). No live host is claimed today.

## Running the helpers

Every helper sources `lib-manual-common.sh` and is **inspect-only by default**. Host-mutating helpers
additionally require a reviewed host identity:

```bash
sudo bash ~/hermes-manual/m02-deploy-and-validate.sh                     # shows nothing changed
sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> \
  bash ~/hermes-manual/m02-deploy-and-validate.sh --apply                # makes the change
```

- Results are reported as `CHECK <name>=<result>` lines and tallied by `mp_finalize`. A `FAIL` fails
  the run, an `UNVERIFIED` makes it incomplete (exit 3), and a run that asserts nothing fails. A check
  owned by a later gate is recorded with `mp_defer` and reported as `RESULT=PASS (PARTIAL)`; it is
  never turned into a PASS and never blocks a gate defined to exclude it.
- Every mutating helper serializes on **one profile lock** (`mp_lock_profile`,
  `/run/lock/hermes-manual-profile.lock`), including credential and configuration operations, so two
  different helpers cannot interleave changes to the same profile.
- `m03-contract.sh --apply` is the credential-free path that applies and verifies
  `config/profile-contract.yaml`; `m04-posture.sh` only installs the helper. Provider and messaging
  acceptance stay in `m03-accept.sh`, separately gated by `--allow-provider-call`.
- A run's required cleanup (state restoration and private temporary-state removal) executes **before**
  `mp_finalize` publishes its result. Successful work followed by a failed cleanup is recorded as
  `CHECK cleanup_required=FAIL` and the run exits non-zero; the in-memory cleanup result is authoritative,
  so a failed evidence-log append cannot turn that failure back into a PASS. An existing failure or
  interruption status is still reported first, so a cleanup problem never masks the primary cause.
- `m03-contract.sh` hands `/home/hermes/gateway-state` to the container's own UID/GID (10000) inside
  the rootless user namespace rather than resetting it to host `hermes`, which maps to namespace UID 0
  and would lock the selected container user out. An existing valid mapped ownership is preserved and
  the mode is tightened to 0700, never broadened.
- `m03-contract.sh` runs the contract helper and verifier **inside a live gateway** with `podman exec`
  (`--user 10000:10000 --workdir /opt/hermes`), so it never mounts the private SSH tree with `:ro,Z` and
  never makes Podman relabel it under a running gateway. A one-shot `podman run` is used only when a
  successful container inventory proves no container is running; an undeterminable state refuses.
- `m03-configure-and-probe.sh` reads the profile **before** any lifecycle change: a converged profile
  with an unchanged probe stops nothing and starts nothing. Reads use `podman exec` against a running
  gateway, so a live private mount is never relabelled by a throwaway `podman run -v ...:z`. The
  container inventory — not the unit text — is the authority for whether that mount is live: a container
  that outlives a non-active unit still blocks mutation. **Unit-state and container-state uncertainty are
  different.** A failed or transitional **container** query refuses everything, because a possibly-live
  private mount must not be mounted or relabelled. A failed or transitional **unit** query is never read
  as "stopped": it refuses the stop when the container is provably not running, but when the inventory
  proves the container *is* running the helper may stop the gateway and records the start as a
  restoration obligation — that container proves the gateway is up and the restoration hook can bring it
  back. Private material is written only after the unit is stopped **and** the inventory proves no
  container holds the mount. The 20-second daemon-stability observation is an intentional probe that runs
  only after a real change.
- `m04-backup.sh` and `m02-deploy-and-validate.sh` capture the pre-run service state conclusively before
  stopping anything (`mp_capture_service_state`): a failed query or a transitional value refuses the stop
  instead of stranding a service the restoration hook cannot know it must restart.
  `m03-configure-and-probe.sh` shares the capture but has the one documented running-container exception
  above: a failed or transitional unit state still refuses the stop unless the container inventory
  independently proves the gateway container is running. When no mutation is attempted, backup records
  `restore_service_state=NOT_APPLICABLE` rather than a misleading PASS.
- The administrator account is configurable with `HERMES_ADMIN`; the runtime account with
  `HERMES_RUNTIME`. Nothing assumes the reference host's name or IP.
- Secrets are redacted through the tracked `redact-stream.py`. No helper writes an executable helper
  into `/tmp`.
- The boot helpers keep their own `RESULT=`/`ENROLLMENT_VERDICT=`/`FALLBACK_PROOF=` contract.

The boot helpers live in `boot/` and source the shared library one level up, so **stage the whole
`scripts/hermes/manual/` tree**, not just `boot/`.

## Why the transport looks like this

The worker must keep `Network=none`. OpenSSH has no Unix-socket listener, so:

- the worker runs `socat` on a socket in a minimal shared directory and hands each
  accepted stream to `sshd -i` (inetd mode) — no TCP listener, not even loopback;
- the gateway runs the official image, whose entrypoint cannot be modified, so
  `ProxyCommand` is pointed at a small Python bridge (`gateway/unix-bridge.py`)
  because that image ships neither `socat` nor `nc`.

The Hermes backend spawns `ssh`/`scp` with
`-o StrictHostKeyChecking=accept-new`, and its `scp` call carries no host-key,
proxy or identity options at all. `gateway/ssh`, `gateway/scp` and
`gateway/sftp` are bind-mounted over `/opt/hermes/bin/{ssh,scp,sftp}`, which is
first on the image `PATH`. OpenSSH honours the **first** obtained value for an
option, so the shim's `StrictHostKeyChecking=yes`,
`UserKnownHostsFile`, `IdentityFile`, `IdentitiesOnly` and `ProxyCommand` win
over the backend's `accept-new`. Multiplexing and `SendEnv` are left to the
backend on purpose.

The worker `sshd` sets no `AcceptEnv`, so the gateway's SSH-specific environment
passthrough stays empty and provider credentials cannot ride into the worker.

## Identities

| Item | Location |
| --- | --- |
| Worker client key (gateway side) | `/home/hermes/gateway-ssh/worker_client_ed25519` |
| Worker public key (baked into worker image) | `/etc/ssh/authorized_keys/worker` |
| Worker host key (worker only, persistent) | `/home/hermes/worker-state/ssh-host-keys/` |
| Pinned worker host key (gateway side) | `/home/hermes/gateway-ssh/known_hosts` |

Host keys are deliberately **not** baked into the worker image: they live in a
persistent worker-only directory so rebuilding the image cannot silently change
the identity the gateway has pinned.

The worker client key is **not** created by M02: on a clean install there is no
`transport/keys` material to migrate and M02 stops with `STOP: worker client key
missing`. Run `provision-worker-client-key.sh` as root first. It is rerun-safe:
it preserves an existing private key, rebuilds a missing public key from it, and
re-asserts the `0711`/`0600`/`0644` ownership and modes above.

## Files

- `worker/Containerfile` — Fedora worker image recipe (tools baked in)
- `worker/sshd_worker_config` — inetd-mode sshd policy, no `AcceptEnv`
- `worker/worker-entrypoint`, `worker-socket-adapter`, `worker-sshd-inetd`
- `gateway/ssh`, `gateway/scp`, `gateway/sftp` — enforcement shims
- `gateway/unix-bridge.py` — stdio ↔ Unix-socket bridge for `ProxyCommand`
- `quadlets/hermes-worker.container`, `quadlets/hermes-gateway.container`
- `m03-contract.sh` — credential-free application and verification of `config/profile-contract.yaml`
- `config/harden-config.py`, `config/verify-contract.py`, `config/profile-contract.yaml` — the contract,
  its convergent applier, and its independent verifier

## Operational notes

- Rootless Quadlets install under `/etc/containers/systemd/users/<hermes-uid>/`
  (the *user* path, not `/etc/containers/systemd/`).
- **SELinux labelling rule — measured, not inferred.** Two rules, both established
  by A/B experiment during the clean-install validation; the mechanism is written
  up in `docs/HERMES_B6_CLEAN_INSTALL_HANDOFF.md` §3.
  - **Use `:z`, never `:Z`, on any directory that more than one container
    mounts.** `:Z` stamps the *directory* with that container's private MCS
    categories, its children inherit them, and a long-running service that
    receives a **fresh** category pair at each start is then denied its own state
    database and logs. That was the failure here: eight `:Z` sites on the shared
    `gateway-state` directory produced `avc: denied { lock }` on `state.db-shm`
    and `{ append }` on the logs, as `container_t:s0:c519,c720` against
    `container_file_t:s0:c253,c452`. `:z` stamps the shared
    `container_file_t:s0`, which any container can read and which is
    restart-stable. In this profile that means `/home/hermes/gateway-state` and
    `/home/hermes/transport`.
  - **`:Z` is correct for a path only one container ever mounts** — the worker's
    `worker-state/home` and `worker-state/ssh-host-keys`, and the four
    `gateway-ssh` binary mounts. Do not "fix" these to `:z`; nothing else mounts
    them, and the private categories are the point.
- **A file written into a mount while its container is running keeps the host
  default label** — `user_home_t`, because `/home/hermes/...` matches the
  policy's user-home rule — and the container is then denied it. Relabel it
  explicitly, `chcon --reference=/home/hermes/gateway-ssh/known_hosts <file>`, or
  restart the container. This is why `m04-postboot.sh` relabels the probe it
  installs before running it.
  **Changing a mount option is never enough on its own:** files already on disk
  keep their old label, so a switch to `:z` must be followed by
  `chcon -R system_u:object_r:container_file_t:s0 <dir>`.
  **Known limitation, code-inspection only (not reproduced offline):**
  `m03-contract.sh` relabels a contract file it has just written into a live
  `:Z` mount only when `mp_install_reconcile` reports `CHANGED`, and it suppresses
  both `chcon` failures. If that first label operation fails or is interrupted, a
  retry with byte-identical content takes the `UNCHANGED` path and does not repair
  the label; the subsequent contract run then fails because the running container
  cannot read the file. The real SELinux behaviour has not been exercised on a
  guest, so this is recorded as a limitation of the live path rather than as a
  reproduced defect.
- The rule previously written here — "`:z` for transport, `:Z` for everything
  else" — is what put the eight bad sites on `gateway-state`. The mistake was
  followed faithfully from its own documentation; it is replaced above.
- The gateway image's `main-wrapper.sh` runs the user command as its `hermes`
  user (UID 10000), so gateway-side material must be readable by that mapped
  UID: `/home/hermes/gateway-ssh` is `0711` and the pinned key `0644`, and the
  worker creates the socket `0666` over a `0711` transport directory. Host-side
  protection is the `0700` `/home/hermes` parent. This is why the runtime
  identity is tested explicitly rather than assumed to be root.
- The pinned private key must be owned by the mapped UID 10000 at `0600`,
  because OpenSSH refuses a group/world-readable private key.
- **Terminal backend selection is profile-scoped.** The gateway binds a
  per-profile terminal scope, and while it is bound `_tenv()` resolves only
  from the profile's `/opt/data/.env` and `/opt/data/config.yaml` — the
  container environment is ignored. Configure it with
  `hermes config set terminal.backend ssh` (and `ssh_host`/`ssh_user`/`ssh_port`/
  `ssh_key`), and keep the Quadlet `Environment=TERMINAL_*` values consistent
  for unscoped CLI runs.
- `hermes doctor` is **not** a valid check here: inside a container it forces
  `terminal_env = local` for its own reporting and never exercises the SSH
  backend. Use `gateway/m03-probe.py`, which resolves the real profile policy
  and drives `tools.environments.ssh.SSHEnvironment`.
- The gateway stays on the default network and publishes no ports; the worker
  has no route.
- Do not add a Podman control socket to either container.

## Memory approval verification

Use the [memory review procedure](../../../docs/HERMES_MEMORY_APPROVAL.md) for the
interactive `/memory pending`, `/memory approve <id>` and `/memory reject <id>`
commands. `gateway/memory-approval-probe.py` tests the shipped handlers in an isolated
profile without credentials or API calls. The earlier claim that this pinned image
could not drain its memory queue was corrected after those checks and a separate
model-based approval/recall test passed; keep the approval gate enabled.

## Boot helpers (`boot/`)

Gate B3–B5 helpers for the fully automatic (Regime B) server, used by the
[clean-install runbook](../../../docs/HERMES_BOOT_CLEAN_INSTALL.md):

- `lib-luks-identity.sh` — shared discovery of the LUKS2 device, mapper name and
  root LV. Nothing about the reference host is hardcoded, so the helpers run
  unchanged on a fresh install whose device, VG and UUID all differ. The others
  source it, so **stage the whole `boot/` directory**, not a single script.
- `tpm-enroll.sh` — `--preflight` / `--enroll` (default) / `--revert`. Binds
  PCR7 (`7:sha256`, no PIN), edits only the matching crypttab record, stages
  pre/post header backups for an off-host copy, and never removes the passphrase
  slot.
- `fallback-wipe.sh` — the honest fallback proof: wipes the TPM token but leaves
  crypttab still requesting TPM. `tpm-enroll.sh --revert` also reverts crypttab,
  so it proves only the trivial case and is *not* a substitute.
- `b4-verify.sh` — post-deploy recheck that the containers autostarted and the
  transport probe still passes after an unattended boot.
- `rehearse-clean-install.sh` — read-only gate run **before** B6: checks runbook
  references and ordering, doc/script flag and policy parity, absence of
  reference-host identity, and self-tests LUKS discovery against a simulated
  fresh install. `REHEARSAL=PASS` is the precondition for a clean-install run.
