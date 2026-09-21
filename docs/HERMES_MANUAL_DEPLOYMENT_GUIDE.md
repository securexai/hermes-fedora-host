# Hermes on Fedora Server — end-to-end deployment guide

**Audience:** the operator who owns the hardware and will type every privileged command.
**Outcome:** a Fedora 44 Server that survives a wall-power cycle with **no keyboard input** and answers on
Telegram through an offline, network-isolated worker.
**Chosen profile:** the **manual profile** — two rootless Podman containers, a digest-pinned upstream gateway
and an offline Fedora worker reached only over a shared Unix socket.
**Budget:** a maintenance window with multiple console reboots. The console steps in Phase 4 cannot be done
over SSH.

## Scope: this is not the automated track

This guide documents the manual profile that was built and validated by hand. It is **not**
[the unattended deployment](HERMES_UNATTENDED_DEPLOYMENT.md), `hermes-deploy.sh`, or the one-command
controller. Those are a separate, still-partly-open track with their own certification gates. Do not mix
commands from them into this procedure.

## How this guide relates to the other documents

Six Hermes documents cover overlapping ground. This table is the tie-breaker, so they can never silently
disagree:

| Document | Role |
| --- | --- |
| **This guide** | The procedure. What to type, in what order, from bare metal to working agent. |
| [Clean-install runbook](HERMES_BOOT_CLEAN_INSTALL.md) | **Ordering authority** for the boot gates. If this guide and the runbook disagree on boot order, the runbook wins. |
| [Preparation guide](plans/2026-09-12-fedora-44-hermes-preparation-guide.md) | The rationale and source-review record behind Phase 5. |
| [Boot automation](HERMES_BOOT_AUTOMATION.md) | Design and acceptance criteria for gates B1–B5. |
| [Manual handoff](HERMES_MANUAL_HANDOFF.md) | Post-deployment operations, maintenance and recovery. Hand this to whoever runs the box. |
| [Execution record](plans/2026-09-07-hermes-unattended.md) | The dated evidence ledger of what was actually done. |

## Status — what is proven, and what is not

**Read this before following the guide.** It states how much to trust the rest of the document.

**Proven.** On one bare-metal host (`hermes.ai.lab.local`, Fedora 44 Server, AZW SER3), on 2026-09-13/14:
M01–M06 pass, boot gates **B1–B6** pass including an explicit fallback proof, M04 steps 7–14 pass, and
**Phase 7 passed on all five criteria** after a real wall-power cycle with no keyboard input. Every change made
along the way is recorded in the [B6 change ledger](plans/evidence/2026-09-14-hermes-b6-change-ledger.md).

**Not proven — and this is the part that matters.** That run did **not** follow this text literally: it
recorded **nine deviations**, listed under "Deviations to declare for replication" in that ledger. Where the
guide itself was at fault — a missing package, a key name that does not exist, a wrong default — the guide was
corrected afterwards. **Those corrections are verified statically only** (`bash -n`, `shellcheck`, `shfmt`,
and the read-only rehearsal). **None of them has been executed against a host.** So:

- the procedure is **proven to have worked once, under close supervision, with nine recorded departures from
  its own text**; and
- the current text is **internally consistent with the artifacts and statically checked, but has never been
  run as written.**

**Memory approval follow-up, 2026-09-18.** The pinned image's real CLI and gateway
slash handlers passed staging, approval, rejection and fresh-process recall tests.
A model test also accurately reported a queued write as not yet saved, then recalled
it in a fresh session after approval. The earlier conclusion that memory approval
was unusable was incorrect for this image. Follow the
[memory approval procedure](HERMES_MEMORY_APPROVAL.md); keep `memory.write_approval`
enabled and approve a reviewed request with `/memory approve <id>`.

**Twelve further limitations and six explicitly unverified items** are recorded in
[the B6 handoff](HERMES_B6_CLEAN_INSTALL_HANDOFF.md) §8 and §9 — among them that the **B1 firmware option name
was never captured**, so a clean install on different hardware has no instruction for the one firmware setting
the whole unattended-boot promise depends on. Read that handoff alongside this guide.

**When you follow it:** expect to record deviations, and treat an **unrecorded** deviation as a defect in this
guide. A second clean install performed literally, with zero unresolved deviations, is the gate that would let
this section claim more. It has not been done.

---

## Reference values from the validated deployment

Use these as defaults and substitute your own where marked. The application scripts already carry the pinned
digests; you do not type them by hand.

| Item | Reference value | Yours |
| --- | --- | --- |
| Server reachable as | `aicowork@10.0.30.10` (`hermes.ai.lab.local`) | `aicowork@<HOST>` |
| Administrator account | `aicowork`, in `wheel`, sudo-capable | any sudo-capable account; see the manual-profile contract for how the name is configured |
| Runtime account | `hermes`, observed uid `1001`, `nologin`, locked, no sudo | same name, **record the real uid** |
| Subordinate IDs | `subuid`/`subgid` `589824:65536` | any unused ≥65536 range |
| Gateway image | `nousresearch/hermes-agent@sha256:9469b3e7…1010e1` (v2026.9.11, Debian 13) | pin the reviewed digest |
| Worker image | `localhost/hermes-worker:1`, built from Fedora 44 base `sha256:2648f667…` | same |
| Provider / model | `openai-api` / `gpt-5.6-luna` | `<PROVIDER>` / `<MODEL>` |
| Storage | LUKS2 root, VG `fedora_hermes`, four linear XFS LVs, `/home/hermes` 250 GiB, ~115.92 GiB reserve | see Phase 1 — **`/home/hermes` must be its own filesystem** |
| Host RAM | 13 GiB (below the guide's ≥16 GiB example) | see the resource caveat |

**Never put a credential value in a shell command, a file you commit, or a chat message.** Every secret in
this procedure is typed at a hidden prompt.

---

## Before you begin

### Step 0 — Choose the target, and protect the current one

| Target | Consequence | Choose it when |
| --- | --- | --- |
| **A spare machine or VM** | The working install is untouched. | You are validating the procedure. Recommended first. |
| **Reinstall the live host** | The working install, its LUKS volume and its credentials are destroyed. | You are deliberately rebuilding. |

Before any destructive action, confirm you hold **all four** of these off the machine you are about to erase:

1. the **LUKS passphrase** — the only break-glass path into the disk;
2. the **off-host recovery material** (LUKS header + crypttab backups);
3. a **stopped-state application backup** — it contains the provider credential, so keep it on encrypted media;
4. the **provider key and bot token**, or the ability to issue new ones.

If any answer is "probably on the server", stop and recover it first. A TPM-bound disk erased without its
header backup is unrecoverable.

### Step 1 — Have these in hand

| Need | Why it cannot be deferred |
| --- | --- |
| **Physical console or IPMI** | The LUKS prompt and the fallback proof are console-only. |
| **Fedora 44 Server install media** | Phase 1. |
| **An SSH key pair** for the administrator account | Phase 5 makes SSH key-only. |
| **Provider API key** | Phase 6, typed at a hidden prompt. |
| **Telegram bot token** (BotFather) and **your numeric user ID** | Phase 6. The user ID is not secret; the token is. |
| **Offline encrypted storage** | Phase 3/4 write header backups that must not stay on the host. |
| **Network plan** (address, gateway, management subnet) | Phase 1/5, before the firewall is tightened. |

### Step 2 — Rehearse before touching hardware

From a workstation that has this repository checked out:

```bash
bash scripts/hermes/manual/boot/rehearse-clean-install.sh
```

It is read-only and checks that this guide, the runbook and the scripts still agree. **`REHEARSAL=PASS` is a
precondition.** A `FAIL` means they have drifted and the deployment would stop partway.

---

## Phase 1 — Install Fedora 44 Server

Install from the official Fedora 44 Server media with **Secure Boot enabled** and **encrypted storage**.

### The accepted storage layout

The design needs `/home/hermes` to be its **own filesystem**, not a directory on `/`. Two things depend on
that: the user-manager guard in Phase 5.7 asserts it is a mount point, and the rootless container store lives
under it. Get this shape — sizes are the reference deployment's, scale them to your disk:

| Item | Reference allocation | Role |
| --- | ---: | --- |
| `/boot/efi` | 1 GiB | EFI / FAT32 |
| `/boot` | 2 GiB | ext4 |
| LUKS container | the remainder (~473.92 GiB) | LUKS2-encrypted LVM physical volume |
| Volume group | `fedora_hermes` | regular **linear** LVs, not thin-provisioned |
| `/` | 60 GiB | XFS |
| `/var` | 40 GiB | XFS |
| `/home/hermes` | 250 GiB | XFS — **must be a separate mount** |
| swap | 8 GiB | inside the encrypted container |
| VG reserve | ~115.92 GiB | left **unallocated**, not another filesystem |

1. In the installer, choose **encrypted** storage and then **custom partitioning**: create the LUKS container,
   the volume group, and the LVs above. Leave the reserve free; do not allocate it merely to prepare Hermes.
2. Keep swap encrypted through the parent LUKS device. Fedora also provides `zram` swap by default, which is
   fine to keep.
3. Use XFS for the three data filesystems and regular linear LVs. Do not introduce thin provisioning.
4. **What is not fixed:** the disk device name, the VG name and the LUKS UUID differ on every install, and the
   boot helpers discover them from the running system. So do not chase a nominal capacity — a drive sold as
   500 GB may report 512 GB — but do create the dedicated `/home/hermes` filesystem.
5. Create the administrator account `aicowork`, in `wheel`, with a sudo password. **The M02–M05 application
   bundle requires the administrator account `aicowork`**: the helpers stage material and write logs under
   `/home/aicowork` and default to it. `HERMES_ADMIN` re-points only the Phase 4 boot helpers; it does not make
   the application procedure portable to another account name.
6. Confirm console access and that you know the LUKS passphrase you chose.

**If you accept the installer's default layout instead**, `/home/hermes` will be a plain directory. The guard
in Phase 5.7 will then refuse to start the user manager. Reinstall with custom partitioning rather than
weakening that guard.

## Phase 2 — Baseline inventory

Verify the layout you actually got before changing anything:

```bash
cat /etc/fedora-release
hostnamectl
free -h
swapon --show
lsblk -o NAME,SIZE,FSTYPE,FSVER,TYPE,MOUNTPOINTS
findmnt --mountpoint /
findmnt --mountpoint /var
findmnt --mountpoint /home/hermes
sudo vgs
sudo lvs -o vg_name,lv_name,lv_size,segtype
sudo cryptsetup isLuks --type luks2 <LUKS_DEVICE>
df -hT / /var /home/hermes
getenforce
stat -fc %T /sys/fs/cgroup
sudo firewall-cmd --get-active-zones
sudo ss -lntup
sudo mokutil --sb-state
```

**Stop-and-review conditions:** `/home/hermes` is not a separate mount; cgroup is not v2 (`cgroup2fs`) —
Quadlet requires v2; SELinux is not `Enforcing`; Secure Boot is not enabled; the LVs are thin rather than
linear. A mismatch is a reason to stop and decide, not permission to reformat anything.

Sizing prerequisites for this profile: at least **8 GiB RAM** and **20 GiB free under `/var`**, plus room
under `/home/hermes`. The reference host has 13 GiB RAM — below the guide's ≥16 GiB example, which is why its
slice budget is deliberately conservative (Appendix A).

Record a sanitized baseline with a UTC timestamp: release, kernel, CPU/RAM, `lsblk`, `findmnt`, VG/LV layout,
LUKS version and **keyslot inventory**, `cryptsetup luksDump` summary, `getenforce`, cgroup version, firewalld
zones, listening sockets, `mokutil --sb-state`, TPM presence, and the LUKS UUID.

Two facts must be unambiguous before you continue:

- the **LUKS device identity** (device node, mapper name, UUID); and
- that **only the passphrase keyslot** exists.

From here on, never assume the reference host's device, VG name or UUID. The helper scripts discover the LUKS
device, mapper, root LV and runtime uid from the running system. Where you must type one, take it from this
baseline.

## Phase 3 — Recovery material, before anything changes

Confirm the passphrase works, then back up the metadata and move it off-host:

```bash
sudo cryptsetup open --test-passphrase <LUKS_DEVICE>
sudo install -d -m 0700 /root/recovery
sudo cryptsetup luksHeaderBackup <LUKS_DEVICE> \
  --header-backup-file "/root/recovery/$(basename <LUKS_DEVICE>)-pre-tpm-$(date -u +%Y%m%dT%H%M%SZ).header"
sudo cp -a /etc/crypttab /root/recovery/crypttab-pre-tpm-$(date -u +%Y%m%dT%H%M%SZ)
sudo vgcfgbackup <VG_NAME>
```

Then:

1. Store the passphrase somewhere durable and offline.
2. Move a **verified** copy of the header backup and the LVM metadata to encrypted storage that is not this
   machine. A copy only under `/root` is not a recovery solution for failure of this disk.
3. Label the header with its keyslot identity — a pre-enrollment header contains only the passphrase slot,
   one taken later also contains the TPM token. Never let the older one silently replace the newer.

A header backup contains keyslot material. Do not attach it to tickets, chat, or any repository.

## Phase 4 — Boot prerequisites (gates B1–B5), before any application

**This phase is why the guide is ordered the way it is.** Firmware configuration feeds PCR7, so it must move
*before* the TPM binding, not after. Application deployment comes later (Phase 6).

Stage the boot helpers as a **directory**, from **your workstation** in the repository root. They share a
library and fail closed without it, so the whole directory must go. The `aicowork@<HOST>:` prefix is required —
without it `scp` copies to the workstation's home, not the server:

```bash
scp -r scripts/hermes/manual aicowork@<HOST>:~/hermes-manual
```

It lands at `/home/aicowork/hermes-manual`, which is the path every command below uses. The boot
helpers are then at `~/hermes-manual/boot/` and find the shared `lib-manual-common.sh` one level up.
On a redeploy, run `ssh aicowork@<HOST> 'rm -rf ~/hermes-manual'` first: `scp -r` into an existing
directory nests the source (`~/hermes-manual/manual`) instead of refreshing it. Every command below
then runs **on the server**.

### 4.1 — Firmware power-loss behaviour (B1), at the console

1. Enter firmware setup and set the power-loss behaviour to **power on**. Menus name it *Restore AC Power
   Loss*, *AC Back*, *After Power Failure*, or *State After Power Loss*.
2. Record whether the option existed and what it is set to.
3. Reboot, then re-verify: Secure Boot still enabled, host reachable, no unexplained PCR7 change.

If the firmware exposes no such setting, record that and continue: **B5 becomes unachievable**, but B2–B4
still give you "no passphrase", leaving only a power-button press.

### 4.2 — Confirm recovery material (B2)

Phase 3 already did this. Confirm the off-host copy is present and readable before you enroll.

### 4.3 — Enroll the TPM2 keyslot (B3)

```bash
sudo bash ~/hermes-manual/boot/tpm-enroll.sh --preflight
```

Read every line and record the `device`, `mapper` and `luks_uuid` it prints. It refuses anything ambiguous.
Stop on any mismatch. Then enroll — it prompts for the **existing** passphrase, which is never echoed:

```bash
sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/boot/tpm-enroll.sh --enroll --apply
```

It binds **PCR 7 with the SHA-256 bank and no PIN**, verifies the passphrase slot still works, edits *only* the
matching crypttab record, regenerates the initramfs, and stages post-change recovery material.

Optional hardening: pin the volume so the script refuses any other one, using the UUID from Phase 2:

```bash
sudo HERMES_EXPECT_UUID=<UUID_FROM_BASELINE> bash ~/hermes-manual/boot/tpm-enroll.sh --preflight
```

Move the staged pre/post header backups and crypttab backup off-host, then delete the staging directory.

### 4.4 — Unattended boot (B4)

Reboot. **Expect no passphrase prompt.** Confirm Secure Boot is still enabled and the boot ID changed. Both
Hermes units should be absent at this stage — no application is deployed yet.

### 4.5 — Prove the fallback

This is the step that separates a proven recovery path from an assumed one. It removes the TPM token while
leaving crypttab still asking for TPM, so the next boot *must* fall back to the console prompt:

```bash
sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/boot/fallback-wipe.sh --apply
```

Reboot. **The passphrase prompt must appear.** Enter the passphrase; the system must boot. Then re-enroll:

```bash
sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/boot/tpm-enroll.sh --enroll --apply
```

`tpm-enroll.sh --revert --apply` is **not** a substitute: it also reverts crypttab, so it proves only the trivial case
where nothing asks for TPM. `--revert` is for abandoning TPM unlock entirely.

### 4.6 — Power restoration (B5)

Orderly shutdown, pull AC **at the wall**, restore AC. The server must power on by itself, unlock with no
input, and reach a running state. Record the observed sequence and timings. Skip only if 4.1 found no firmware
option.

**Stop if:** Secure Boot changed, PCR7 moved unexpectedly, or the passphrase no longer unlocks.

## Phase 5 — Host preparation (M01), manual steps

These are the steps that were executed by hand on the reference host. Substitute your own interface, zone,
device and VG names; the reference values appear in `<>`.

### 5.1 — Controlled update and host tools

```bash
sudo dnf upgrade --refresh
```

Review the transaction before accepting it. Then:

```bash
sudo dnf install \
  podman container-selinux passt \
  shadow-utils shadow-utils-subid \
  openssh-server openssh-clients \
  firewalld policycoreutils policycoreutils-python-utils \
  audit chrony cryptsetup lvm2 xfsprogs tpm2-tools \
  git jq skopeo tar rsync \
  dnf5-plugin-automatic dnf5-plugins \
  mokutil smartmontools sysstat
sudo systemctl enable --now chronyd
chronyc tracking
```

`tpm2-tools` is **not optional**: `boot/b4-verify.sh` reads PCR 7 with `tpm2_pcrread`, and the TPM enrollment
and fallback helpers use it too. It was missing from the first edition of this list, so a literal follower
built a host whose final boot gate could not run; added during the clean-install validation.

Use Fedora's signed repositories. Do not disable signature verification, do not add an unrelated repository,
and do not install Docker alongside Podman. Do not run the Hermes curl-to-shell installer on the host for this
containerized profile.

### 5.2 — Key-only SSH

Work at the **console** for this step, or you can lock yourself out.

**Use the public key you actually have.** The first edition of this guide named `~/.ssh/id_ed25519.pub`; on
the reference workstation that file does not exist — the working key is `id_ed25519_cloudops.pub`. Substitute
your own path; the name is not significant, but a key that is not there fails late and confusingly.

The helper to copy is the **tracked** one, `scripts/hermes/manual/setup-ssh-key-only.sh` — the hardened
version this procedure is validated against. A second working copy also existed at the repository root
during the first deployment; it is **untracked**, so a fresh clone will not contain it. Since C52 the two are
byte-identical, but always copy the path below:

```bash
scp scripts/hermes/manual/setup-ssh-key-only.sh aicowork@<HOST>:~/
scp ~/.ssh/id_ed25519_cloudops.pub aicowork@<HOST>:~/id_ed25519_cloudops.pub
```

Then, at the server console, identify the real interface and zone:

```bash
ip -br address
sudo firewall-cmd --get-active-zones
```

Run the helper with a dry run first, then for real:

```bash
sudo bash ~/setup-ssh-key-only.sh \
  --user aicowork \
  --public-key-file ~/id_ed25519_cloudops.pub \
  --interface <INTERFACE> --zone <ZONE> --dry-run
```

Then verify syntax and the effective settings:

```bash
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T | grep -E \
  '^(pubkeyauthentication|authenticationmethods|passwordauthentication|kbdinteractiveauthentication|permitrootlogin) '
```

From a **new** workstation connection, confirm public-key login works. Then confirm the negative test fails —
this one must be refused because it disables public-key authentication:

```bash
ssh -o ControlPath=none -o PubkeyAuthentication=no \
    -o PreferredAuthentications=password,keyboard-interactive aicowork@<HOST>
```

Keep the administrator's local password for `sudo` and console recovery; key-only SSH does not require locking
the human admin password.

### 5.3 — Firewall and Cockpit

Inspect before changing:

```bash
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --permanent --list-all-zones
sudo ss -lntup
```

For any firewall change, protect yourself with a timed reload that restores the permanent rules:

```bash
sudo systemd-run --unit=hermes-fw-rollback \
  --on-active=5m /usr/bin/firewall-cmd --reload
```

**`--on-active=5m` is a hard deadline on the whole procedure, not a safety margin.** You have five minutes in
total to make the runtime change, prove SSH still works from a **new** connection, write the change
permanently, and cancel the timer. In the validation run the SSH proof took seconds but the operator's
turnaround exceeded the remaining window, so the timer fired and silently reverted the change, which then had
to be re-applied directly to `--permanent`. Either keep the proof to seconds or raise `--on-active` to cover
realistic operator latency; do not assume the timer will wait for you.

Make one runtime change, open a fresh SSH connection to prove it, then write the same change permanently and
cancel the timer:

```bash
sudo systemctl stop hermes-fw-rollback.timer
sudo firewall-cmd --check-config
```

If Cockpit is not needed, disable its socket and remove the `cockpit` service from the active zone — only
after confirming SSH still works. Never run a blanket firewall reset or flush nftables.

### 5.4 — Bounded journal and download-only updates

Create `/etc/systemd/journald.conf.d/60-hermes-host.conf`:

```ini
[Journal]
Storage=persistent
SystemMaxUse=1G
SystemKeepFree=2G
MaxRetentionSec=14day
```

```bash
sudo systemctl restart systemd-journald
sudo journalctl --flush
journalctl --disk-usage
sudo systemctl is-active auditd
sudo ausearch -m AVC,USER_AVC -ts recent
```

Then set staging without applying. **On a fresh Fedora 44 install `/etc/dnf/automatic.conf` does not exist —
create it.** The values below are the upstream defaults, so this step makes the policy **explicit rather than
changing behaviour**, which is the point of it: this file is the live override, while
`/etc/dnf/dnf5-plugins/automatic.conf` is the deprecated location. Both facts were established during the
clean-install validation; an earlier edition of this step said only to "review" the file, which fails on a
fresh system.

```ini
[commands]
upgrade_type = default
download_updates = yes
apply_updates = no
reboot = never

[emitters]
emit_via = stdio
```

```bash
sudo systemctl enable --now dnf5-automatic.timer
systemctl list-timers dnf5-automatic.timer
```

Download-only is staging, not patching. Review staged updates weekly and apply them in a window. Do not add
`AutoUpdate=registry` to any container. Investigate AVC denials rather than installing a generated
`audit2allow` policy or setting SELinux permissive.

### 5.5 — Static hostname, then reboot

```bash
sudo hostnamectl set-hostname <FQDN>
```

Update the workstation's host entry and confirm it resolves, then reboot **with console access** to unlock
LUKS:

```bash
sudo systemctl reboot
```

After reconnecting, re-run the mount, SELinux and service checks. Only the reboot proves the host boots as
intended; the written configuration alone does not.

### 5.6 — The runtime account

Verify the mount before creating anything:

```bash
findmnt --mountpoint /home/hermes
sudo ls -ldZ /home/hermes
getent passwd hermes
```

If `hermes` does not exist, create a regular unprivileged account with a **non-login shell** — not a system-UID
account:

```bash
sudo useradd --user-group --no-create-home \
  --home-dir /home/hermes \
  --shell /usr/sbin/nologin hermes
sudo passwd --lock hermes
sudo chown hermes:hermes /home/hermes
sudo chmod 0700 /home/hermes
sudo restorecon -v /home/hermes
```

**A fixed numeric UID is not required — record the actual one.** Then confirm the security properties:

```bash
id hermes
sudo -l -U hermes
sudo grep '^hermes:' /etc/subuid /etc/subgid
command -v newuidmap
```

Require **at least 65,536** subordinate IDs of each kind. Do not copy an arbitrary range from this guide; pick
unused ranges.

### 5.7 — Directories and the persistent user manager

```bash
sudo install -d -o hermes -g hermes -m 0700 \
  /home/hermes/.config /home/hermes/.local /home/hermes/.cache/podman-tmp \
  /home/hermes/gateway-state /home/hermes/workspace \
  /home/hermes/worker-state /home/hermes/transport
sudo restorecon -Rv /home/hermes
```

Do not later run a recursive `chown` or `restorecon` over an active rootless container store.

Protect the user manager against a missing data mount, then enable lingering. **This guard asserts that
`/home/hermes` is a mount point** — the dedicated XFS filesystem required by Phase 1:

```bash
HERMES_UID=$(id -u hermes)
sudo install -d -m 0755 "/etc/systemd/system/user@${HERMES_UID}.service.d"
sudo tee "/etc/systemd/system/user@${HERMES_UID}.service.d/20-hermes-data.conf" >/dev/null <<'EOF'
[Unit]
RequiresMountsFor=/home/hermes
AssertPathIsMountPoint=/home/hermes
EOF
sudo systemctl daemon-reload
sudo loginctl enable-linger hermes
sudo systemctl start "user@${HERMES_UID}.service"
loginctl show-user hermes -p Linger -p RuntimePath
```

Define the administrator convenience function you will use for the rest of the deployment. Redefine it after
reconnecting:

```bash
HERMES_UID=$(id -u hermes)
h() {
  if ! mountpoint -q /home/hermes; then
    printf 'STOP: /home/hermes is not mounted.\n' >&2
    return 1
  fi
  sudo -u hermes -- env -i --chdir=/home/hermes \
    HOME=/home/hermes USER=hermes LOGNAME=hermes \
    PATH=/usr/local/bin:/usr/bin:/bin TERM="${TERM:-xterm}" \
    XDG_RUNTIME_DIR="/run/user/$HERMES_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$HERMES_UID/bus" \
    TMPDIR=/home/hermes/.cache/podman-tmp "$@"
}
```

Verify rootless operation:

```bash
h podman info --format \
'rootless={{.Host.Security.Rootless}} cgroups={{.Host.CgroupsVersion}} manager={{.Host.CgroupManager}} driver={{.Store.GraphDriverName}} graphroot={{.Store.GraphRoot}}'
h podman unshare cat /proc/self/uid_map
```

Expected: `rootless=true cgroups=v2`, systemd cgroup management, and a graphroot under `/home/hermes`.
Do not enable `podman.socket` and do not mount a runtime socket into an application container.

### 5.8 — Optional: conservative resource budgets

These are **proposed starting budgets**, not benchmark results. Size them from the RAM you actually measured
in Phase 2:

| Host RAM | Example gateway cap | Example worker cap | Example `hermes` slice cap | Intended reserve |
| --- | ---: | ---: | ---: | --- |
| 8 GiB | 2 GiB | 2 GiB | 5 GiB | ~3 GiB for host activity |
| 16 GiB | 3 GiB | 6 GiB | 10 GiB | ~6 GiB |
| 32 GiB or more | 4 GiB | 8 GiB | 16 GiB | at least 16 GiB |

**Do not apply the 16 GiB numbers to an 8 GiB machine.** On the reference host (13 GiB) the conservative
figures were used, and `systemctl set-property` proved to be **runtime-only**, so the limits were written as an
explicit slice drop-in instead. `m04-posture.sh` applies and verifies them in Phase 6; record the previous
values and test before making limits part of acceptance. A container memory limit and the parent slice limit
serve different purposes — the parent also bounds combined child activity. Treat hard limits as emergency
containment, because exceeding them terminates processes.

Start with one worker task at a time and raise concurrency only after measuring:

```bash
free -h
vmstat 1 10
iostat -xz 1 10
cat /proc/pressure/cpu /proc/pressure/memory /proc/pressure/io
h podman stats --no-stream
```

Do **not** disable SELinux, seccomp, kernel mitigations or user namespaces to chase performance, force
swappiness to 1, disable swapping entirely, switch to an untested I/O scheduler, or put `noexec` on the whole
container store. Bake worker tools into the image rather than downloading packages at runtime, keep the
rootless container store on `/home/hermes`, and keep the encrypted swap and the XFS/linear-LVM layout.

## Phase 6 — Deploy the application (M02–M05)

### 6.1 — Stage the bundle

From **your workstation** in the repository root, copy the whole bundle to the server. The `aicowork@<HOST>:`
prefix is required — without it `scp` copies to the workstation's home, not the server:

```bash
scp -r scripts/hermes/manual aicowork@<HOST>:~/hermes-m02-bundle
```

It lands at `/home/aicowork/hermes-m02-bundle`, which is the default `$BUNDLE` for every helper below. On a
redeploy, run `ssh aicowork@<HOST> 'rm -rf ~/hermes-m02-bundle'` first: `scp -r` into an existing directory
nests the source (`~/hermes-m02-bundle/manual`) instead of refreshing it. Read a script's header before running
it.

### 6.2 — Provision the worker client key (before M02)

**Bind the run to the reviewed host first.** Every M02–M05 helper is host-mutating and requires
`HERMES_EXPECT_MACHINE_ID_SHA256` to match the reviewed host, or the root-owned pin installed by
`m00-pin-host-identity.sh` (below). `sudo` resets the environment, so a value merely exported in your shell
does **not** reach the helper; pass it on the `sudo` command line. `<reviewed hash>` is the SHA-256 of
`/etc/machine-id` recorded in Phase 2 and confirmed against the reviewed deployment record. An unset or
mismatched value is refused, so a paste aimed at the wrong host stops instead of mutating it.

**Run this on the server as root before step 1 of 6.3.** M02 does not create the gateway's worker client key: on
a clean install it finds no `/home/hermes/transport/keys` to migrate and stops with
`STOP: worker client key missing`. The bundle carries a helper that provisions it:

```bash
sudo HERMES_EXPECT_MACHINE_ID_SHA256=<reviewed hash> \
  bash ~/hermes-m02-bundle/provision-worker-client-key.sh
```

It is rerun-safe: it generates an ed25519 key only when the private key is absent, preserves an existing private
key, rebuilds a missing public key from that private key, and re-asserts the ownership and modes the gateway
requires — `/home/hermes/gateway-ssh` `0711 hermes:hermes`, the private key
`/home/hermes/gateway-ssh/worker_client_ed25519` owned by the mapped UID `10000` at `0600`, and the public key
`hermes:hermes` at `0644`. It prints only the public-key fingerprint. Because it writes directly to the location
M02 expects, no `transport/keys` migration is involved on a clean install.

**One-time alternative: install the root-owned pin.** Repeating the variable on every command is noisy.
`m00-pin-host-identity.sh` writes `/etc/hermes-manual/host-identity.sha256` once, after which the plain
`sudo bash …` form works. **It must never be used to discover or invent the expected identity on the target:**
read the value it prints, confirm it equals the independently reviewed hash, and only then write the pin. A host
that pins whatever it reports proves only that it is itself, which defeats the binding.

```bash
sudo bash ~/hermes-m02-bundle/m00-pin-host-identity.sh          # inspect-only: prints host_identity_sha256=<hash>
# STOP unless it equals the reviewed Phase 2 hash. Then:
sudo bash ~/hermes-m02-bundle/m00-pin-host-identity.sh --apply  # writes the 0644 root-owned pin
```

### 6.3 — The ordered sequence

Run as root; `sudo` prompts for your password. Step 1 needs the key provisioned in 6.2. Unless the pin from
6.2 is installed, prefix every command in the table with `HERMES_EXPECT_MACHINE_ID_SHA256=<reviewed hash> `;
for example:

```bash
sudo HERMES_EXPECT_MACHINE_ID_SHA256=<reviewed hash> \
  bash ~/hermes-m02-bundle/m02-deploy-and-validate.sh --apply
```

The order is not arbitrary — the notes column records the dependencies that actually bit during the first deployment.

| # | Command (`sudo HERMES_EXPECT_MACHINE_ID_SHA256=<reviewed hash> bash ~/hermes-m02-bundle/…`, unless pinned in 6.2) | Gate | Notes |
| --- | --- | --- | --- |
| 1 | `m02-deploy-and-validate.sh --apply` | M02 | Worker image, shims, socket; validates transport and isolation |
| 2 | `m03-activate.sh --apply` | M03.1 | No credential loaded; proves shim resolution |
| 3 | `m03-configure-and-probe.sh --apply` | M03.2 | Writes the profile terminal backend |
| 3a | `m03-contract.sh --apply` | M03.2a | **Credential-free** application and verification of `config/profile-contract.yaml`. Safe to run before any credential exists; provider checks are deferred to Gate 3 |
| 4 | `provision-openai-key.sh` | M03 | **Hidden prompt**; writes the profile `.env` |
| 5 | `m03-accept.sh --apply --allow-provider-call` | M03 | **Requires the `.env` from step 4.** The second flag is the explicit opt-in for the paid inference and tool round trip |
| 6 | `m04-posture.sh --apply` | M04.1 | Effective posture; parent slice budget |
| 7 | `m04-backup.sh --apply` | M04.2 | Stopped-state backup + isolated restore. **Stops both containers**; it restarts them at the end |
| 8 | `provision-telegram.sh`, then `m05-telegram.sh --apply` | M05 | **Must precede the read-only test**, which verifies Telegram returns. The gateway must be **running** — check `podman ps` if step 7 was interrupted |
| 9 | `m05-tests.sh status` (read-only; its mutating sub-commands need `--apply`) | M05 | You send the Telegram messages from your own account |
| 10 | `m04-readonly-gateway.sh --apply` | M04a | Read-only rootfs; auto-reverts the unit if Telegram does not return |
| 11 | `m04-reboot.sh --apply`, then **reboot at the console** | M04b1 | |
| 12 | `m04-postboot.sh --apply` | M04b2 | Verifies autostart after the reboot |
| 13 | `m04-postboot-probe.sh --apply` | M04b3 | Relabels and re-runs the probe |
| 14 | `boot/b4-verify.sh` | recheck | Boot properties with the application present. Prints `ASSERT …` lines and **exits non-zero if any fails**; an unmeasurable check reports `UNVERIFIED` rather than passing |

### 6.4 — What to check as you go

- **Transport (step 1):** a positive round trip must return the worker's **Fedora** identity while the gateway
  is Debian, a missing trusted key must fail, and a changed host key must fail.
- **Credentials (steps 4–5):** the model must return exactly `HERMES_OK`, and a harmless tool round trip must
  land in the worker and return `Fedora release 44`.
- **Telegram (steps 8–9):** the bot is a **supervised daemon**, connected in **polling mode**, with no public
  webhook. Test the authorized reply, the manual-approval gate, the unauthorized rejection, and the
  worker-failure path. **The approval test must use a command the policy actually gates** — a destructive
  one such as `rm -rf /tmp/<probe-dir>` (verdict: "delete in root path") or `systemctl restart sshd`
  ("stop/restart system service"). Benign commands (`cat /etc/os-release`, `ls -la /tmp`, `curl <url>`)
  return **allow** and run with no prompt, so testing with one of those silently proves nothing. Check the
  verdict in advance with `hermes approvals test` — exit 0 = allow, 2 = ask-approval, 3 = deny.
- **Recovery (step 7):** entry counts must match exactly between source and restored tree, and the restored
  config must assert the SSH backend and your model. Delete the restored tree afterwards — it contains a
  credential copy. The script stops **both** containers for the backup and restarts them at the end; if it is
  interrupted, confirm with `podman ps -a` before continuing to step 8. Its `diff_rc` is now read from `diff`
  itself via `PIPESTATUS` — `0` is the only acceptable value, and it is compared with
  `diff -rq --no-dereference`, because the uv cache holds absolute in-container symlinks that dangle on the
  host and make a naive `diff -r` report spurious errors.

> **Correction to the B6 handoff, grounded in the pinned release's source.** The handoff states that
> `terminal.ssh_host` and the other `terminal.ssh_*` keys are not recognized config keys and that the
> Quadlet environment is authoritative. The pinned release maps every `terminal.<key>` to
> `TERMINAL_<KEY>` (`hermes_cli/config.py`), and while a profile terminal scope is bound the policy
> resolves **only** from the profile's `config.yaml` and `.env` (`tools/terminal_scope.py`). Profile
> configuration is therefore authoritative for the gateway and the Quadlet values must stay consistent
> with it. `m03-configure-and-probe.sh` now reads every key back and fails if it does not match,
> instead of reporting success from an unverified write. It also reads the profile **before** any
> lifecycle change, so a converged profile with an unchanged probe is not stopped or restarted, and it
> queries a running gateway with `podman exec --user 10000:10000 --workdir /opt/hermes` rather than
> creating a new `podman run -v ...:z` mount against a live private state directory. The container
> inventory, not the unit text, decides whether that mount is live: a container that outlives a
> non-active unit still blocks mutation, and a failed or transitional *container* query refuses the run
> instead of being read as "stopped". A failed or transitional *unit* query is also never read as
> "stopped": it refuses the stop unless the inventory independently proves the gateway container is
> running, in which case the run stops the gateway and records the restart as a restoration obligation.
> `m03-contract.sh` follows the same rule and drives a live gateway through
> `podman exec`, so contract application does not relabel the private SSH tree of a running gateway.
> A run's required cleanup (service restoration and temporary-state removal) now completes **before**
> the result is published, so a successful run whose cleanup failed is reported as a failure.

`hermes doctor` is **not** a valid check here: inside a container it forces `terminal_env=local` and never
exercises the SSH backend. Use `gateway/m03-probe.py`, which the scripts already drive.

## Phase 7 — Final acceptance

Orderly shutdown → pull AC **at the wall** → restore AC → **no keyboard input at any point** → confirm:

- both containers are running;
- the end-to-end transport probe returns the worker's Fedora identity;
- Telegram replies;
- no published ports beyond `sshd` and `systemd-resolved`;
- no failed units and no new AVC denials.

If this fails, the boot half was never actually proven on this machine. Re-read Phase 4 rather than patching
around it.

## Phase 8 — Record the evidence, then hand off

Per phase, record: UTC timestamp, exact command, expected vs actual result, and artifact identities —
keyslot/token inventory before and after, PCR set and bank, header-backup hashes, image digests, initramfs
identity — plus an explicit statement of what remains unverified. Record the firmware setting and the boot
sequence observed after the power cycle.

The reference deployment's evidence files are the shape to follow, one per gate:

- `docs/plans/evidence/2026-09-13-hermes-m01-baseline.json`
- `docs/plans/evidence/2026-09-13-hermes-m01-fedora-readiness.json`
- `docs/plans/evidence/2026-09-13-hermes-m02-worker-transport.json`
- `docs/plans/evidence/2026-09-13-hermes-m03-credentials-cli.json`
- `docs/plans/evidence/2026-09-13-hermes-m04-hardening-recovery.json`
- `docs/plans/evidence/2026-09-13-hermes-m05-telegram.json`
- `docs/plans/evidence/2026-09-13-hermes-boot-b1-b5.json`

Then produce the operational handoff using [the existing one](HERMES_MANUAL_HANDOFF.md) as the template: the
deployed identities and digests, the permission contract, routine operations, maintenance, backup and
recovery, and the standing limitations.

---

## Appendix A — Findings that will bite you

These are real defects discovered during the first deployment. Each one cost debugging time.

1. **The gateway drops to UID 10000.** Its `main-wrapper.sh` runs the user command as the image's `hermes`
   user, not root. Gateway-side files must be readable by that mapped UID: `/home/hermes/gateway-ssh` is
   `0711`, and the pinned key must be owned by the mapped UID at `0600` — OpenSSH refuses a group- or
   world-readable private key. Host-side isolation is the `0700` `/home/hermes` parent.
2. **A file created in a `:Z` directory while its container runs keeps the host label.** Podman labels the
   mount at container start, so the new file gets `user_home_t` and `container_t` is denied read (one AVC).
   Relabel it against a correctly labelled sibling, or restart the container.
3. **`UsePAM no` plus a locked account refuses publickey.** The *in-container* worker account therefore needs
   a random non-matching shadow value rather than `!`. The host `hermes` account stays locked — that one is
   correct.
4. **The terminal backend is profile-scoped.** While the profile is bound, `terminal_env` resolves only from
   the profile's `/opt/data/.env` and `config.yaml`; the Quadlet `Environment=TERMINAL_*` lines are inert for
   tool execution. Configure it with `hermes config set`.
5. **`hermes doctor` cannot validate this profile** inside a container. Use `gateway/m03-probe.py`.
6. **The gateway service needs `Exec=gateway run`.** Without it the container runs bare `hermes`, prints an
   interactive banner and exits after about 15 seconds. The s6 image already supervises a per-profile gateway;
   `gateway run` attaches to it.
7. **A Quadlet edit made after the last install is not picked up** until the unit is reinstalled from the
   bundle. This is what caused the 15-second exit above.
8. **Resource limits are below the guide's example.** The validated host has 13 GiB, so the ≥16 GiB example
   slice budget was deliberately not applied. Limits remain provisional: 2 GiB / 512 PIDs worker,
   2 GiB / 256 PIDs gateway, parent slice `MemoryHigh=6G`, `MemoryMax=8G`, `TasksMax=1536`.
9. **Automatic unlock makes an intact stolen machine bootable.** See Appendix E.
10. **Host guards exist because paste-able blocks land on the wrong machine.** Five times during the
    validation a block was run against the wrong host — once rebooting the workstation instead of the server.
    Wrap every paste-able block, privileged or not, in
    `if [ "$(hostname)" != <EXPECTED> ]; then echo 'WRONG MACHINE'; else …; fi`, and keep the message in
    **single quotes**: inside double quotes an interactive bash expands `!` from history, and `!!` printed the
    text of the operator's previous command. Never `exit` from a guard — an earlier version closed the
    operator's session instead of protecting it.
11. **Both machines can expose the LUKS container at the same device path.** On the reference pair, server and
    workstation both use `/dev/nvme0n1p3`. Guard every device-path command with `cryptsetup luksUUID`, or a
    recovery step can be aimed at the wrong disk.
12. **A check that cannot fail is worse than no check.** `m04-backup.sh` read `diff_rc` after a pipe to
    `head`, so it measured `head`; `b4-verify.sh` ended with `exit "$rc"`, where `rc` came from the `tee`
    pipeline, so it exited 0 whatever the host state. Both are fixed, but the pattern recurs: when a step's
    verdict comes from a pipeline, read `PIPESTATUS`, and prefer explicit assertion lines whose *count* is
    itself checked, so a missing log cannot read as success.
13. **A verification step's own output can be the defect.** `m04-postboot.sh` installed its probe into a
    `:Z` mount with no relabel, so step 12 printed a failed probe and one AVC denial every run — noise
    indistinguishable from a real regression unless the denial count is baselined first. Record the AVC
    watermark before a step and compare after it.
14. **Memory approval requires the interactive review interface.** The earlier validation
    observed a staged write and an allegedly successful agent reply, then concluded there was no
    way to apply it from the shell help menu. The 2026-09-18 follow-up tested the actual
    `/memory pending`, `/memory approve <id>` and `/memory reject <id>` handlers in the same
    pinned image; all passed, as did authenticated fresh-session recall. A staged request is
    not committed memory, and queue persistence without a status/expiry field is expected.
    See the [canonical procedure and evidence](HERMES_MEMORY_APPROVAL.md). The original
    misleading-reply observation remains historical and was not reproduced in the follow-up.

## Appendix B — Recovery and rollback

| Symptom | Action |
| --- | --- |
| No passphrase prompt on a boot where you expected one | Expected once B3 passes; verify with `boot/b4-verify.sh` |
| Prompt appeared, TPM did not unseal | Unlock at the console; re-enroll with `tpm-enroll.sh --enroll --apply`; record what moved |
| Enrollment interrupted | `tpm-enroll.sh --revert --apply`; the passphrase path stays intact |
| A keyslot was actually lost | Restore the header backup — never speculatively, since an older header silently deletes the TPM token |
| Bad crypttab edit | Restore the saved crypttab, regenerate the initramfs |
| Gateway will not stay up | Check `Exec=gateway run`; reinstall the Quadlet from the bundle |
| Missing data mount | Leave the user manager and application stopped; repair the mount; never recreate data on `/` |
| Storage pressure | Stop new work; inspect growth; deliberate cleanup or LV expansion |
| Worker or transport failure | Tool error; there is no local or online-worker fallback by design |
| Lost sudo access | Console recovery; the admin account remains in `wheel`; key-only SSH needs no login password |
| Rehearsal reports `FAIL` | Do not start. Fix the drift between guide, runbook and scripts first |

### M05 diagnostics and repair

The bundle also carries three helpers that are diagnostics and repairs rather than deployment steps. Reach for
them when the gateway will not stay up:

| Helper | Purpose |
| --- | --- |
| `m05-gateway-diag.sh` | Foreground probes to find why `hermes gateway run` exits; output is redacted |
| `m05-gateway-diag2.sh` | Corrected redaction; captures the real service logs and subcommand output |
| `m05-fix-and-activate.sh` | Reinstalls the current Quadlets — the gateway now carries `Exec=gateway run` — and proves it stays up as a supervised daemon |

## Appendix C — Paths, accounts and variables

| Item | Value |
| --- | --- |
| Runtime account home | `/home/hermes` (`0700`) |
| Quadlets | `/etc/containers/systemd/users/<RUNTIME_UID>/` |
| Gateway state / config | `/home/hermes/gateway-state` → `/opt/data` in container |
| Worker state, host keys | `/home/hermes/worker-state/ssh-host-keys/` |
| Gateway SSH material | `/home/hermes/gateway-ssh` (`0711`) |
| Worker client key | `/home/hermes/gateway-ssh/worker_client_ed25519` (`0600`, mapped UID 10000); provisioned by `provision-worker-client-key.sh` |
| Shared socket | `/home/hermes/transport/worker.sock` (`0666`, dir `0711`) |
| Profile `.env` | `/opt/data/.env` in container, `0600`, mapped UID 10000 |
| Helper bundle | `~/hermes-m02-bundle` (default `$BUNDLE`) |
| Boot helpers | `~/hermes-manual/boot` |
| Provider / model override | `HERMES_PROVIDER`, `HERMES_MODEL` (used by `config/set-model.py`) |
| Telegram settings | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS`, `TELEGRAM_ALLOW_ALL_USERS=false` |
| Terminal backend | `backend=ssh`, `ssh_host=worker`, `ssh_user=worker`, `ssh_port=22`, key `worker_client_ed25519` |

## Appendix D — What is reproducible, and what is not

- **Fully scripted from this repository:** the boot prerequisites (`scripts/hermes/manual/boot/`) and the
  application deployment (`m02`–`m05`, `provision-*`, `config/`).
- **Manual by design:** Phase 5 host preparation and the runtime account. The automated M01 helper scripts used
  on the reference host were **never committed** and exist only on that machine — treat this guide as the M01
  procedure, not those scripts.
- **Console-only, cannot be automated:** the firmware setting, the fallback proof, the AC power cycle, and
  final acceptance. They need a human at the machine.

## Appendix E — Standing security limitations

- **A stolen *intact* server boots itself**, with the provider and bot credentials on that volume. Revoke them
  remotely if the machine is lost. **Disk-only theft remains protected** — the TPM is on the motherboard.
- **PCR7 binds Secure Boot *policy state*, not boot contents.** Two paths stay open: `/boot` is unencrypted
  and unmeasured, so a tampered initramfs could harvest the key; and Fedora's GRUB allows editing a boot entry,
  so `rd.break` yields root on the already-unlocked volume. The cheapest first mitigation is a GRUB superuser
  password — but only after confirming the generated entries carry `--unrestricted`, or automatic boot will
  stall at the menu. Real fixes are clevis/Tang or the UKI/signed-PCR11 phase.
- The firmware TPM on this hardware class (`MSFT0101`) is weaker than a discrete TPM.
- The AC-back firmware setting is firmware state: a firmware update, CMOS clear or dead battery can silently
  revert it, and nothing detects that until the next real outage.
- Capability dropping was not attempted; the containers keep the rootless Podman default set.
- Only the terminal toolset is exercised end-to-end. Browser, computer-use and the other toolsets are
  disabled or unverified.
