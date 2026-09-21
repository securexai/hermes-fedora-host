# Hermes manual-profile handoff

**Target:** `aicowork@10.0.30.10` (`hermes.ai.lab.local`), Fedora 44 Server
**Profile:** manual guide — two rootless containers, digest-pinned upstream gateway, offline Fedora worker
**Branch:** `codex/hermes-manual-guide-plan`
**Status:** M01 ✅, M02 ✅, M03 ✅, M04 ✅, M05 ✅, M06 ✅ final — all gates pass on the live host
**Boot regime:** M01–M06 certified **Regime A** (unattended application, operator-assisted boot). The
operator has since adopted the stricter **Regime B** — recovery from power loss with no human present —
and it is now **implemented**: see [boot automation](HERMES_BOOT_AUTOMATION.md) gates B1–B6 ✅ and the
[clean-install runbook](HERMES_BOOT_CLEAN_INSTALL.md). The host now powers itself on after AC restoration
and unlocks its LUKS root via TPM2 (PCR7) with **no passphrase and no button press**. **B6 clean-install
validation ✅ passed on 2026-09-14** on a fresh Fedora 44 Server install; its record is the
[B6 handoff](HERMES_B6_CLEAN_INSTALL_HANDOFF.md), which supersedes this document's B6 row. A stolen intact
server now boots itself — that is the accepted cost of Regime B.
**Secret policy:** no credential value appears in this document, the execution record, the evidence
files, or Git. Provider and bot credentials live only in the profile `.env` on LUKS-encrypted storage.

**Rebuilding or starting over?** Follow [the end-to-end deployment guide](HERMES_MANUAL_DEPLOYMENT_GUIDE.md) —
it runs the whole build from bare metal and defers to the
[clean-install runbook](HERMES_BOOT_CLEAN_INSTALL.md) for the boot gates.

## 1. What is deployed

| Component | Identity |
| --- | --- |
| Gateway image | `docker.io/nousresearch/hermes-agent@sha256:9469b3e78b9545b6d576eb8887a95352e9a0ea83730eaf31431cf862ca1010e1` (release v2026.9.11) |
| Worker image | `localhost/hermes-worker:1` (locally built, digest recorded per build) |
| Base image | `registry.fedoraproject.org/fedora@sha256:2648f667bd180801195d3f3a385cf0d2e390bd80611dbedac8275253c89cdbc7` |
| Runtime account | `hermes`, uid 1001, `nologin`, locked, no sudo, subuid/subgid `589824:65536` |
| Containers | `hermes-worker` (`Network=none`), `hermes-gateway` (egress, no published ports) |
| Model | `openai-api` / `gpt-5.6-luna` |
| Quadlets | `/etc/containers/systemd/users/1001/{hermes-worker,hermes-gateway}.container` |

Storage is unchanged from the accepted design: LUKS2 `nvme0n1p3`, VG `fedora_hermes`, four linear LVs,
`/home/hermes` 250 GiB. A TPM2 token **is** now enrolled against `PCR 7:sha256` for Regime B — keyslots 2,
one `systemd-tpm2` token, passphrase slot preserved — so the earlier "no TPM token is enrolled" statement
no longer applies; see [boot automation](HERMES_BOOT_AUTOMATION.md).

## 2. Trust and transport

- The worker has no route at all. Its SSH host key lives in a persistent, worker-only directory
  (`/home/hermes/worker-state/ssh-host-keys`), so rebuilding the image cannot silently change the
  identity the gateway has pinned.
- The gateway reaches the worker only through a shared Unix socket
  (`/home/hermes/transport/worker.sock`); `ProxyCommand` runs a small Python bridge because the gateway
  image ships neither `socat` nor `nc`.
- `gateway/ssh`, `gateway/scp` and `gateway/sftp` are bind-mounted over `/opt/hermes/bin/*`, which is
  first on the image PATH. OpenSSH honours the first obtained option value, so the shim's
  `StrictHostKeyChecking=yes` beats the backend's own `-o StrictHostKeyChecking=accept-new`. A missing
  or changed worker host key fails closed (verified).
- The worker sshd sets no `AcceptEnv`, so the gateway's SSH environment passthrough stays empty.

## 3. Runtime identity (important)

The gateway image's `main-wrapper.sh` drops the user command to its **`hermes` user, UID 10000**. That
mapped identity — not root — is what runs `ssh`, reads the pinned key, and connects to the socket.
Consequences to preserve when editing permissions:

| Path | Mode | Why |
| --- | --- | --- |
| `/home/hermes` | `0700` | host-side isolation for everything below |
| `/home/hermes/gateway-ssh` | `0711` | UID 10000 must traverse it |
| `gateway-ssh/worker_client_ed25519` | `0600`, owned by mapped UID 10000 | OpenSSH refuses group/world-readable keys |
| `/home/hermes/transport` | `0711` | UID 10000 must reach the socket |
| `worker.sock` | `0666` | connectable by UID 10000 |
| profile `.env` | `0600`, mapped UID 10000 | credential file |

**Re-labelling rule (learned the hard way):** `/home/hermes/gateway-ssh` and `/home/hermes/transport` are
bind-mounted with `:Z`, and Podman labels the source **at container start**. A file created in one of
those directories *while its container is running* keeps the host default label (`user_home_t`), and
`container_t` is then denied read (an AVC). Either relabel the new file, e.g.
`chcon --reference=/home/hermes/gateway-ssh/known_hosts <file>`, or restart the container so Podman
re-labels the mount.

## 4. Terminal backend configuration

The gateway binds a **per-profile terminal scope**. While it is bound, `terminal_env` resolves **only**
from the profile's `/opt/data/.env` and `/opt/data/config.yaml`; the container environment is ignored.
Configure it with `hermes config set`, not solely with Quadlet `Environment=` lines.

Current values: `terminal.backend=ssh`, `terminal.ssh_host=worker`, `terminal.ssh_user=worker`,
`terminal.ssh_port=22`, `terminal.ssh_key=/opt/hermes/gateway-ssh/worker_client_ed25519`.

Note that `hermes doctor` forces `terminal_env=local` inside a container, so it cannot validate this
profile. Use `gateway/m03-probe.py`, which resolves the real policy and drives
`tools.environments.ssh.SSHEnvironment`.

## 5. Routine operations

All container control runs as the `hermes` account's user manager (linger is enabled).

```bash
# Rootless operations helper (run as root)
h() { sudo -u hermes -- env -i --chdir=/home/hermes HOME=/home/hermes USER=hermes LOGNAME=hermes \
  PATH=/usr/local/bin:/usr/bin:/bin XDG_RUNTIME_DIR=/run/user/1001 \
  DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus TMPDIR=/home/hermes/.cache/podman-tmp "$@"; }

h systemctl --user status hermes-worker.service
h systemctl --user status hermes-gateway.service
h podman ps -a --format '{{.Names}} | {{.Status}} | ports=[{{.Ports}}]'
h podman logs --tail 100 hermes-gateway
h podman exec --user 10000:10000 --workdir /opt/hermes hermes-gateway hermes config get terminal.backend
```

Both Quadlets autostart at boot (validated by the M04 reboot test). The gateway carries
`[Install] WantedBy=default.target`; lingering keeps the `hermes` user manager alive so no interactive
login is needed.

## 6. Maintenance

- **OS updates are download-only.** `dnf5-automatic.timer` stages packages; nothing is applied
  automatically. Apply deliberately in a maintenance window, then reboot with console access.
- **Application images are promoted manually.** Never replace the pinned digest with a floating tag.
  Record the new digest before promoting.
- **Journal** is bounded to 1G / keep-free 2G / 14-day retention. `/var/log/audit` and Hermes logs are
  separate.
- Do not add a Podman control socket to either container, and do not add `AutoUpdate=registry`.

## 7. Backup and recovery

A stopped-state backup was taken and an isolated restore was verified (see M04 evidence). Reproduce with:

```bash
h systemctl --user stop hermes-gateway.service
h systemctl --user stop hermes-worker.service
tar --xattrs --acls --selinux -C / -cpf /root/hermes-app-$(date -u +%Y%m%dT%H%M%SZ).tar \
  home/hermes/gateway-state home/hermes/worker-state home/hermes/gateway-ssh \
  etc/containers/systemd/users/1001
h systemctl --user start hermes-worker.service
```

The archive **contains the provider credential**; store it only on encrypted media and never in Git.
Verify a restore into an isolated path before relying on it, and never run two gateways against the
same state directory.

| Situation | Recovery |
| --- | --- |
| SSH misconfiguration | Console; restore previous files; `sshd -t`; reload |
| Firewall mistake | Console, or timed reload of known-good permanent rules |
| Missing Hermes data mount | Leave the user manager/application stopped; repair the mount; do not recreate data on `/` |
| Bad image promotion | Stop writers; restore compatible pre-change state and the previous digest |
| Failed boot update | Console and the existing fallback kernel; unlock with the known credential |
| Storage pressure | Stop new work; inspect growth; deliberate cleanup or LV expansion |
| Worker/transport failure | Tool error; there is no local or online-worker fallback |
| Lost sudo access | Console recovery; `aicowork` remains in `wheel`; key-only SSH does not require a login password |

## 8. Explicit limitations

- Capability dropping was not attempted: the effective set is the rootless Podman default, because the
  guide warns that blind drops can break user-namespace mapping helpers.
- Resource limits are provisional: 2 GiB / 512 PIDs for the worker, 2 GiB / 256 PIDs for the gateway, and
  a `MemoryHigh=6G` / `MemoryMax=8G` / `TasksMax=1536` parent slice on a 13 GiB host — below the guide's
  ≥16 GiB example row. Re-measure before changing.
- No SSH source restriction to a management subnet was applied.
- Only the terminal toolset was exercised end-to-end; other toolsets are unverified. Browser,
  computer-use, Discord, Feishu, Home Assistant, image/video generation, Spotify and X search are
  disabled/unavailable, which matches the guide's initial-scope restrictions.
- `sftp` shim exists but the current backend does not exercise it.
- The Telegram bot token was exposed in plaintext in the task conversation during deployment; the
  operator revoked it in BotFather and re-provisioned through the hidden prompt. Treat that bot's
  credential history as burned.
- Everything remains uncommitted on `codex/hermes-manual-guide-plan`; no commits, pushes or PRs were
  authorized.
- **Regime B is implemented and its recovery path is proven.** The host powers on after AC restoration
  and unlocks via TPM2 with no passphrase (B1–B5 PASS), and removing the TPM token was shown to fall back
  to the console passphrase prompt and unlock (fallback proof PASS). **B6 clean-install validation closed on
  2026-09-14**: the procedure was executed end to end from a fresh Fedora 44 Server install and passed, so
  it is no longer proven only by amendment on an existing install. That run's record — including twelve
  limitations it did not clear — is the [B6 handoff](HERMES_B6_CLEAN_INSTALL_HANDOFF.md).
- **A pre-B6 rehearsal found two defects that would have failed the clean install, and both are fixed.**
  (1) The boot helpers hardcoded this host's LUKS device, mapper name and UUID and *refused* any other
  volume, while the runbook instructs the operator to use whatever layout a fresh install produces —
  the enrollment preflight would have stopped at step 6. Identity is now discovered from the running
  system (`boot/lib-luks-identity.sh`), with `HERMES_EXPECT_UUID` to pin it and a self-test against a
  simulated fresh install. (2) The runbook prescribed `tpm-enroll.sh --revert` for the fallback proof,
  but `--revert` also reverts crypttab, so it proves only the trivial case; the proof now uses
  `boot/fallback-wipe.sh`, which leaves crypttab requesting TPM. Re-run `boot/rehearse-clean-install.sh`
  before and after any edit to the runbook or those helpers; `REHEARSAL=PASS` is the precondition for B6.
- **Keep the LUKS passphrase recorded and known.** With TPM unlock in place it is rarely typed, so it is
  easy to forget — and it is the only break-glass path into the disk. During the fallback proof it was
  mistyped twice before succeeding.
- **New standing risk from Regime B:** a stolen intact server boots itself, and the provider and bot
  credentials are on that volume. Revoke the OpenAI key and bot token remotely if the machine is lost.
  **Disk-only theft is still protected** (the TPM is on the motherboard). Because PCR7 binds Secure Boot
  *policy state* rather than boot contents, two paths are currently open and worth closing: unencrypted
  `/boot` is not measured, so a tampered initramfs could harvest the key; and Fedora GRUB allows editing a
  boot entry, so `rd.break` gives root on the already-unlocked volume. Cheapest first step:
  `grub2-setpassword`. Real fixes: clevis/tang, or the UKI/signed-PCR11 phase.

Validated on the live host, and therefore **not** limitations any more: Telegram end-to-end (authorized
reply, manual approval gate, unauthorized rejection, worker-failure containment), the read-only gateway
root filesystem, host reboot persistence with autostart, and the stopped-state backup plus isolated
restore.

## 9. Evidence index

| Gate | Evidence | Status |
| --- | --- | --- |
| M01 | `docs/plans/evidence/2026-09-13-hermes-m01-baseline.json`, `...-m01-fedora-readiness.json` | ✅ PASS |
| M02 | `docs/plans/evidence/2026-09-13-hermes-m02-worker-transport.json` | ✅ PASS |
| M03 | `docs/plans/evidence/2026-09-13-hermes-m03-credentials-cli.json` | ✅ PASS |
| M04 | `docs/plans/evidence/2026-09-13-hermes-m04-hardening-recovery.json` | ✅ PASS |
| M05 | `docs/plans/evidence/2026-09-13-hermes-m05-telegram.json` | ✅ PASS |
| M06 | this document plus the canonical execution record `docs/plans/2026-09-07-hermes-unattended.md` | ✅ PASS |
| B1–B5 (Regime B boot) | `docs/HERMES_BOOT_AUTOMATION.md`, `scripts/hermes/manual/boot/{tpm-enroll,fallback-wipe,b4-verify,rehearse-clean-install}.sh` + `lib-luks-identity.sh`, `docs/plans/evidence/2026-09-13-hermes-boot-b1-b5.json` | ✅ PASS |
| B6 (clean-install validation) | `docs/HERMES_BOOT_CLEAN_INSTALL.md`, `docs/HERMES_B6_CLEAN_INSTALL_HANDOFF.md` | ✅ PASS |

Artifacts: `scripts/hermes/manual/` (README, `worker/`, `gateway/`, `boot/`, `quadlets/`, `config/`, and the
`m0*-*.sh` run scripts).
