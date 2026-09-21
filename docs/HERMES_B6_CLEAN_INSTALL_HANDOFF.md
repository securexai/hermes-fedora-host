# Hermes manual-profile handoff — B6 clean-install validation

**Target:** `aicowork@10.0.30.10` (`hermes.ai.lab.local`), Fedora 44 Server
**Profile:** manual guide — two rootless containers, digest-pinned upstream gateway, offline Fedora worker
**Branch:** `codex/hermes-manual-guide-plan`
**Status:** clean-install validation through **B6** ✅ — M02–M05, M04 steps 7–14 and Phase 7 all pass on
this freshly installed host
**Boot regime:** **Regime B**, re-proven from a fresh install. The host powers itself on after AC
restoration and unlocks its LUKS root via TPM2 (PCR 7, SHA-256) with **no passphrase and no keyboard
input**. A stolen intact server boots itself — that is the accepted cost.
**Secret policy:** no credential value appears in this document, the change ledger, the evidence record, or
Git. Provider and bot credentials live only in the profile `.env` on LUKS-encrypted storage, plus one
off-host archive on the LUKS-encrypted workstation.

This document **supersedes** the B6 row of [`HERMES_MANUAL_HANDOFF.md`](HERMES_MANUAL_HANDOFF.md) and the
sections of it that this run has changed. That file remains the reference for the *previous* install. The
companion artifacts for this run are the
[change ledger](plans/evidence/2026-09-14-hermes-b6-change-ledger.md) (C1–C48) and the
[evidence record](plans/evidence/2026-09-14-hermes-b6-baseline.json).

## 1. What is deployed

| Component | Identity |
| --- | --- |
| Host | AZW SER3, Fedora Linux 44 (Server Edition), kernel `7.2.5-200.fc44`, 13 GiB RAM / 4 cores |
| machine-id | `fedeed82ba3041dcbbf91c033a76a00c` |
| Gateway image | `docker.io/nousresearch/hermes-agent@sha256:9469b3e78b9545b6d576eb8887a95352e9a0ea83730eaf31431cf862ca1010e1` (v2026.9.11) |
| Worker image | `localhost/hermes-worker:1` = `60a498cb38ac5edb9c76a3dd5024ab9b0342ff2928a84784191183453ca31397` |
| Base image | `registry.fedoraproject.org/fedora@sha256:2648f667bd180801195d3f3a385cf0d2e390bd80611dbedac8275253c89cdbc7` |
| Runtime account | `hermes`, uid/gid 1001, `nologin`, locked, no sudo, subuid/subgid `589824:65536` |
| Containers | `hermes-worker` (`Network=none`, `ReadOnly=true`, 2 GiB, 512 pids), `hermes-gateway` (egress, no published ports, `ReadOnly=true`, `Tmpfs=/run`, `Tmpfs=/tmp`, 2 GiB, 256 pids) |
| Slice budget | `user-1001.slice`: `MemoryHigh=6G`, `MemoryMax=8G`, `TasksMax=1536` |
| Model | `openai-api` / `gpt-5.6-luna` |
| Profile state | `config.yaml` 3678 bytes sha256 `072e3a0b…`; `.env` 529 bytes, 10 keys, mode 600, owner `599823:599823` |
| Quadlets | `/etc/containers/systemd/users/1001/{hermes-worker,hermes-gateway}.container` |

Storage: LUKS2 `nvme0n1p3`, UUID `8919c2b1-5d9a-4fb9-8f85-97d286cbe7ec`, VG `fedora_hermes`, four linear
LVs, dedicated XFS `/home/hermes`. TPM2 token enrolled against `PCR 7:sha256`, **no PIN**; keyslots 2 with
the passphrase slot preserved. **PCR7 =
`22103EAC50D6EF26DABCBA626A8E70754586CE66D600563A82CEFBF2CA206A73`**, byte-identical across **eight**
boots including this run's AC power cycle. Secure Boot: **enabled (user)**.

The two machines in this lab both expose `/dev/nvme0n1p3`. **Always confirm `cryptsetup luksUUID` matches the
server value above before any device-path command.** This has already caused one wrong-machine incident.

## 2. Trust and transport

- The worker has **no route at all** (`Network=none`). Its SSH host key lives in a persistent, worker-only
  directory, so rebuilding the image cannot silently change the identity the gateway pinned.
- The gateway reaches the worker only through a shared Unix socket
  (`/home/hermes/transport/worker.sock`); `ProxyCommand` runs a small Python bridge because the gateway
  image ships neither `socat` nor `nc`.
- The `gateway-ssh` `ssh`/`scp`/`sftp` shims are bind-mounted over `/opt/hermes/bin/*`, first on PATH.
  OpenSSH honours the first-obtained option, so the shim's `StrictHostKeyChecking=yes` beats the backend's
  `accept-new`. A missing or changed worker host key **fails closed** (verified).
- **Worker-failure containment is verified, and there is no silent local fallback.** With the worker
  stopped, a tool call fails cleanly with `Terminal environment unavailable` — it does **not** run locally
  in the gateway. Verified for `read_file` as well as `terminal`, since both route through the same SSH
  sandbox. This matters: silent local execution would put operator commands in the internet-connected
  gateway while appearing to be confined to the worker.
- **Transport probe passes after a reboot:** `gateway/m03-probe.py` →
  `resolved_backend=ssh`, `execute_returncode=0`, `execute_output=HERMES_WORKER_ROUNDTRIP_OK`,
  worker identity `NAME="Fedora Linux"`.
- **Host exposure:** listeners are `sshd` (22) and `systemd-resolved` (53, 5355) only, before and after the
  power cycle. No published container ports.

## 3. Runtime identity (important)

The gateway image's `main-wrapper.sh` drops to its **`hermes` user, UID 10000**, which maps to host UID
**599823**. That mapped identity — not root — runs `ssh`, reads the pinned key and connects to the socket.

| Path | Mode | Why |
| --- | --- | --- |
| `/home/hermes` | `0700` | host-side isolation for everything below |
| `/home/hermes/gateway-ssh` | `0711` | UID 10000 must traverse it |
| `gateway-ssh/worker_client_ed25519` | `0600`, mapped UID 10000 | OpenSSH refuses group/world-readable keys |
| `/home/hermes/transport` | `0711` | UID 10000 must reach the socket |
| `worker.sock` | `0666` | connectable by UID 10000 |
| profile `.env` | `0600`, mapped UID 10000 | credential file |

**The re-labelling rule, with its mechanism now measured rather than guessed.** A file created inside a
bind-mounted directory inherits **the directory's** SELinux level, not the creating process's. Two
consequences, both verified by A/B experiment:

- **Use `:z`, never `:Z`, on any directory a second container mounts.** `:Z` (private relabel) stamps the
  *directory* with that container's MCS categories; every child then inherits them, and the long-running
  service — which gets a fresh pair at each start — is denied its own state DB and logs. That was the
  original failure here. `:z` stamps the shared `container_file_t:s0`, so any container can read it and the
  label is restart-stable. Eight `:Z` sites on `gateway-state` were found and corrected.
- **A file created while its container is running keeps the host default label** (`user_home_t`), because
  `/home/hermes/...` matches the policy's user-home rule. Relabel it, e.g.
  `chcon --reference=/home/hermes/gateway-ssh/known_hosts <file>`, or restart the container.
  `:Z` remains correct for genuinely single-container paths (`worker-state/home`,
  `worker-state/ssh-host-keys`, the four `gateway-ssh` binary mounts).

## 4. Terminal backend configuration

The gateway binds a **per-profile terminal scope**; while bound, `terminal_env` resolves **only** from the
profile's `/opt/data/.env` and `/opt/data/config.yaml`.

**Correction to the guide worth carrying forward:** `m03-configure-and-probe.sh` writes
`terminal.ssh_host`, `terminal.ssh_user`, `terminal.ssh_port` and `terminal.ssh_key` into `config.yaml`,
and Hermes reports all four as **"not a recognized config key"**. The step still passes because the Quadlet
independently sets the same values as `TERMINAL_*` environment variables. **Treat the Quadlet `Environment=`
lines as authoritative**, and do not delete them on the assumption that `config.yaml` covers it.

`hermes doctor` forces `terminal_env=local` inside a container and cannot validate this profile. Use
`gateway/m03-probe.py`.

The worker image has **no `hostname` command** — use `cat /etc/os-release` or `uname -n`. Its base is
`Fedora Linux 44 (Container Image)`; the gateway's is `Debian GNU/Linux 13 (trixie)`, which makes the two
trivially distinguishable.

## 5. Routine operations

```bash
# Rootless operations helper (run as root)
h() { sudo -u hermes -- env -i --chdir=/home/hermes HOME=/home/hermes USER=hermes LOGNAME=hermes \
  PATH=/usr/local/bin:/usr/bin:/bin XDG_RUNTIME_DIR=/run/user/1001 \
  DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus TMPDIR=/home/hermes/.cache/podman-tmp "$@"; }

h systemctl --user status hermes-worker.service hermes-gateway.service
h podman ps -a --format '{{.Names}} | {{.Status}} | ports=[{{.Ports}}]'
sudo bash /home/aicowork/hermes-m02-bundle/m05-tests.sh status
```

Both Quadlets carry `[Install] WantedBy=default.target` and autostart at boot; lingering keeps the `hermes`
user manager alive with no interactive login. Note that Quadlet-generated units report **`generated`**, not
`enabled`, from `systemctl is-enabled` — that is expected, not a failure.

**Dangerous-command approvals work — and benign commands are deliberately not gated.** Inspect a verdict
without executing anything:

```bash
h podman exec hermes-gateway /opt/hermes/bin/hermes approvals test '<command>'
# exit 0 = allow, 2 = ask-approval, 3 = deny
```

`rm -rf …` and `systemctl restart …` return **ask-approval**, and the prompt arrives in Telegram as a
**button**. `cat`, `ls`, `curl` return **allow** and run silently. The guide's acceptance step says only
"trigger an approval-required action" — it must be a **dangerous** command, or no prompt will appear.

## 6. Maintenance

- **OS updates are download-only.** `dnf5-automatic.timer` stages packages; nothing applies automatically.
  Apply deliberately in a maintenance window, then reboot **with console access**. Note
  `/etc/dnf/automatic.conf` does not exist on a fresh install and must be created — it is a `%ghost`.
- **Application images are promoted manually.** Never replace a pinned digest with a floating tag. Record
  the new digest before promoting.
- **Journal** bounded to 1G / keep-free 2G / 14-day retention. `/var/log/audit` is separate.
- Do not add a Podman control socket to either container, and do not add `AutoUpdate=registry`.
- **`provision-openai-key.sh` must never be re-run once Telegram is provisioned.** It writes `.env` with a
  bare `cat >` — an unconditional truncate — and would delete `TELEGRAM_*`, `API_SERVER_KEY` and the four
  hardening flags while reporting success. It is the only one of the four `.env` writers that truncates.
  Also note the gateway **appends a generated `API_SERVER_KEY`** to `.env` on its first start, so any hash
  recorded while the gateway was stopped goes stale the moment it starts.

## 7. Backup and recovery

Two verified archives exist, **off-host only**, in `private/hermes-app-backups/` on the LUKS-encrypted
workstation:

| Stamp | Bytes | sha256 | Captures |
| --- | --- | --- | --- |
| `20260914T024351Z` | 98,283,520 | `0a61e03f…` | step-7 state, before Telegram provisioning |
| `20260914T035903Z` | 110,520,320 | `67c35be3…` | **fully configured** state, post-Phase-7 |

**A backup is not trusted until a corrected diff says so.** `m04-backup.sh`'s own `diff_rc` comes from
`head` and can never fail, and `tar` preserves the 13 uv-cache symlinks whose absolute container targets are
dangling on the host. The method that actually works, and that produced a **zero-diff** result:

```bash
# with the gateway STOPPED, so the tree is frozen - restart it afterwards
T=$(mktemp -d /root/rediff-XXXXXX)
tar --xattrs --acls --selinux -C "$T" -xpf "$ARCHIVE"
diff -rq --no-dereference /home/hermes/gateway-state "$T/home/hermes/gateway-state"
cmp /home/hermes/gateway-state/.env "$T/home/hermes/gateway-state/.env"
```

Restore is a `tar -xpf` into `/`. **Never run two gateways against the same state directory.** These
archives contain the provider credential and the bot token; keep them only on encrypted media.

| Situation | Recovery |
| --- | --- |
| SSH misconfiguration | Console; restore previous files; `sshd -t`; reload |
| Firewall mistake | Console, or timed reload of known-good permanent rules |
| Missing Hermes data mount | Leave the application stopped; repair the mount; never recreate data on `/` |
| Bad image promotion | Stop writers; restore compatible pre-change state and the previous digest |
| Failed boot update | Console and the existing fallback kernel; unlock with the known passphrase |
| Worker/transport failure | Tool error; there is no local or online-worker fallback (verified) |
| Lost sudo access | Console recovery; `aicowork` remains in `wheel`; key-only SSH needs no login password |
| Lost machine | Revoke the OpenAI key and the Telegram bot token remotely |

**Keep the LUKS passphrase recorded and known.** With TPM unlock in place it is rarely typed, and it is the
only break-glass path into the disk.

## 8. Explicit limitations

**C50 update, after this handoff was written.** A repository-side remediation pass fixed several of the
procedure defects below — items **5, 6 and 7** in full, and item **2** only in the sense that the guard now
reports the truth instead of its opposite. The fixes carry before/after sha256 in entry **C50** of the
[change ledger](plans/evidence/2026-09-14-hermes-b6-change-ledger.md). They were **not executed**: the
changed scripts are verified by `bash -n` and by inspection against the defect each fix removes, so every
piece of live evidence in this document still belongs to the **pre-C50** scripts, and the host bundle
(`/home/aicowork/hermes-m02-bundle`) is now stale for all nine changed files — nothing at runtime reads that
bundle, so only a step re-run on this host is affected, and guide §6.1 re-stages it on any replication.
Items **3, 4, 8, 9, 10, 11 and 12** — and the *disposition* in item 2 — remain
open as recorded. Item 1 has a later correction linked below.

1. **Historical memory-approval finding, corrected by the 2026-09-18 follow-up.**
   The conclusion below that the queue cannot be reviewed was disproven by testing
   the pinned image's interactive `/memory` handlers and authenticated fresh-session
   recall. See the [current procedure and evidence](HERMES_MEMORY_APPROVAL.md).
   The following retains the original observation, not a current operational claim:
   **the memory `write_approval` queue appeared stuck in that run.**
   Asking the bot to remember something parks the write at
   `gateway-state/pending/memory/<id>.json` with no status, **never prompts in Telegram**, **never expires**
   (survives well past `approvals.timeout: 300`), **survives a reboot and an AC power cycle**, and the agent
   **reports success anyway**. `hermes approvals` has only `suggest` and `test`; `hermes memory` has only
   `setup`/`status`/`off`/`reset`. No committed memory file exists at all. **The agent will claim to
   remember things it has not stored.** This is the most serious open defect.
2. **The profile config can never be auto-migrated.** It has no `_config_version`, so every gateway start
   logs `predates version 12 … can no longer be auto-migrated`. The guard that should repair this —
   `m03-configure-and-probe.sh:92` — is **inverted**: it requires a *present* version below 12, so a
   version-less config takes the "left in place" branch. Not fixed, because asserting a schema version
   blind is a compatibility claim this run could not substantiate. **C50 made the guard report this
   truthfully and state the consequence; the disposition — and the absence of a version — is unchanged.**
3. **`OPENAI_BASE_URL` and `provider: openai-api` are an inconsistent pair.** The gateway warns that
   auxiliary clients may route to the wrong endpoint. Main inference is unaffected, so this is invisible to
   the current acceptance tests and would surface as unexplained background behaviour.
4. **`HERMES_DASHBOARD=0` does not stop the dashboard**, and `API_SERVER_ENABLED=false` does not stop the
   aiohttp API — both listen on loopback inside the container. Exposure is nil (loopback-only, unpublished),
   but the hardening flags do not do what the record implies.
5. **`m04-postboot.sh` prints a failed transport probe and emits an AVC denial every run**, because it
   installs `m03-probe.py` into a `:Z` mount after the container has started (see §3). Step 13 repairs it,
   and that script's header documents the mechanism — but step 12's own output does not say the failure is
   expected, and the denial is indistinguishable from a real regression unless baselined. The fix is one
   line: relabel at install time. **Fixed in C50** — the script now relabels at install time and prints the
   resulting context.
6. **Verification scripts that cannot fail.** `b4-verify.sh` has no assertion path and exits 0 regardless of
   gateway state, failed units or AVCs, though the runbook calls it a re-assertion.
   `m04-readonly-gateway.sh` auto-reverts only on `is-active`, not on Telegram connectivity, and its
   `telegram_state()` lacks `journalctl -b`. `m04-backup.sh` stops the gateway and never restarts it, and
   its `diff_rc` is measured from `head`. **All four fixed in C50**, and `b4-verify.sh` now derives its exit
   status from explicit `ASSERT` lines rather than from the output pipeline.
7. **Documentation defects:** `m04-reboot.sh`'s header still claims a console LUKS passphrase is required,
   which B3 made false; `README.md:69` states `:Z` is the default for "everything else", which is how eight
   sites on a shared directory came to exist; the guide's approval test does not say "dangerous command".
   **All three fixed in C50** — and the README rule was replaced with the measured one, not merely reworded.
8. **`ausearch -ts 'MM/DD/YYYY HH:MM:SS'` fails on this host** with `Error parsing start date`. Use
   `-ts today` / `-ts recent` plus a timestamp comparison. Any earlier count built on that form was a false
   zero.
9. Capability dropping was not attempted; the effective set is the rootless Podman default. Resource limits
   remain provisional and were not re-measured.
10. Only the terminal, memory and read-file paths were exercised end-to-end. Browser, computer-use, Discord,
    Feishu, Home Assistant, image/video generation, Spotify and X search are unavailable — matching the
    guide's initial-scope restrictions.
11. **Standing Regime B risks, unchanged:** a stolen intact server boots itself and the credentials are on
    that volume; unencrypted `/boot` is not measured, so a tampered initramfs could harvest the key; Fedora
    GRUB allows editing a boot entry, so `rd.break` gives root on the already-unlocked volume. Cheapest
    first step: `grub2-setpassword`. Real fixes: clevis/tang or a UKI/signed-PCR11 phase.
12. `scripts/hermes/manual/` and the guides remain **untracked in Git**, so no commit pins the procedure and
    sha256 is the only identity a change has. There is no CI; `rehearse-clean-install.sh` is never invoked
    by any runner.

## 9. What remains unverified

- **The B1 firmware option name and its prior value.** B5 proved the *setting* works — the machine powers
  itself on after AC restoration — but the option was never named, and it needs a visit to firmware setup.
  This is the single hole in the boot track's record.
- **Whether the deployment still works with the Quadlet `TERMINAL_*` environment removed** and only the
  `config.yaml` keys present. Deliberately not tested, because it would mean editing the artifact under
  test mid-run.
- **The resolver path for `hermes.ai.lab.local`.** The lab domain sits under the reserved mDNS `.local`
  TLD, so systemd-resolved refuses it and name resolution depends on per-client `/etc/hosts`.
- **Auxiliary-client routing**, per limitation 3.
- **Any toolset other than terminal, memory and read-file**, per limitation 10.
- **The read-only gateway's auto-revert under a genuine Telegram failure** — the check that triggers it is
  too weak to exercise honestly.

## 10. Evidence index

| Artifact | Location |
| --- | --- |
| Change ledger, C1–C49 | `docs/plans/evidence/2026-09-14-hermes-b6-change-ledger.md` |
| Evidence record | `docs/plans/evidence/2026-09-14-hermes-b6-baseline.json` |
| Ordering authority | `docs/HERMES_BOOT_CLEAN_INSTALL.md` |
| Procedure | `docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md` |
| Off-host archives | `private/hermes-app-backups/{20260914T024351Z,20260914T035903Z}/` |
| Recovery material | `private/hermes-boot-recovery-8919c2b1/` |
| Artifacts | `scripts/hermes/manual/` (`README.md`, `worker/`, `gateway/`, `boot/`, `quadlets/`, `config/`, `m0*-*.sh`) |
