# Fedora 44 Server for Hermes

## A manual-first preparation, hardening and operations guide

**Target:** `aicowork@10.0.30.10`
**Profile:** Fedora 44 Server; rootless Podman; separate gateway and offline worker
**Prepared:** September 12, 2026
**Status:** Guidance and local source review only. No server connection, package installation, enrollment or deployment
was performed for this guide.

> **Partly superseded on 2026-09-13 — read this first.** This guide's baseline excludes TPM auto-unlock and
> firmware changes, and §6 says to leave TPM enrollment alone. That is still correct **for the preparation
> stage it describes**. The operator subsequently adopted the stricter **Regime B** requirement — recover
> from power loss with no human present — which *does* include TPM enrollment and the firmware AC-back
> setting. Both are implemented and proven under gates B1–B5: follow
> [boot automation](../HERMES_BOOT_AUTOMATION.md) for the prerequisite design and
> [the clean-install runbook](../HERMES_BOOT_CLEAN_INSTALL.md) for the ordering on a fresh install, where
> the boot prerequisites come **before** application deployment. The hold in §2 is unchanged: use
> `boot/tpm-enroll.sh`, never the uploaded `configure-tpm2-auto-unlock.sh`.
>
> **The practical decision:** Keep the installed storage layout. Prepare Fedora first. Run Hermes under a separate
> unprivileged account, using administrator-managed rootless Quadlets. Prove the offline-worker transport and credential
> isolation before enabling the gateway, and validate CLI before Telegram.
>
> **Do not run the uploaded TPM auto-unlock script as part of this baseline.** Its crypttab editing has reproducible
> problems, and custom boot enrollment is outside the supplied plan.

## How to use this guide

Read Sections 1–3 first. Work through the host-preparation sections one at a time, during an authorized maintenance
window. Commands marked **Server** run as `aicowork` on the Fedora server; commands marked **Workstation** run on your
workstation. A `sudo` prefix means an administrator action—not a privilege to give the agent.

These are manual steps, not a script to paste as one large block. Stop when a check disagrees with the expected result.
Back up an existing configuration before replacing it, and merge rather than discard unrelated settings. All application
deployment remains behind the M01–M06 acceptance gates in the uploaded plan. Preparing this document does not mark any
gate passed or authorize a remote deployment.

### The short route

| Stage | Outcome required before continuing |
|---|---|
| Access and recovery | Verified server identity; working admin login; console access; known LUKS passphrase |
| Fedora preparation | Updated OS; expected mounts; SELinux enforcing; active firewall; synchronized time |
| Runtime preparation | Separate `hermes` user; valid subordinate IDs; rootless Podman; data on the intended LV |
| Worker validation | Offline worker and authenticated Unix-socket SSH transport work; no secret leakage |
| Application acceptance | Pinned image and model work through CLI; then Telegram authorization and recovery tests pass |

## 1. Preserve the decisions already made

### Server and storage

Your installation screenshots showed a drive labeled **512 GB**, even though it was initially described as 500 GB. Use
the actual installed sizes rather than repartitioning to match a nominal capacity. The following is the accepted layout
from the conversation, still requiring live verification:

| Item | Accepted allocation | Format or role |
|---|---:|---|
| `/boot/efi` | 1 GiB | EFI/FAT32 |
| `/boot` | 2 GiB | ext4 |
| `nvme0n1p3` | About 473.92 GiB inside the opened mapping | LUKS-encrypted LVM PV |
| VG | `fedora_hermes` | Regular LVM allocation |
| `/` | 60 GiB | XFS |
| `/var` | 40 GiB | XFS |
| `/home/hermes` | 250 GiB | XFS |
| swap | 8 GiB | Encrypted through the parent LUKS device |
| VG reserve | About 115.92 GiB | Free extents, not another filesystem |

Keep this layout. Do not reformat, change filesystem type or allocate the reserve just to prepare Hermes. The dedicated
data filesystem separates its capacity from `/` and `/var`; it does not automatically give each container or workspace
an individual quota. Rootless Podman normally stores images under the account's home directory. [S5]

### Accounts and application design

`aicowork` is the human administrator. `hermes` is the runtime account: no sudo, no ordinary login, no administrator SSH
keys.

The supplied plan selects **two rootless containers**, a digest-pinned upstream gateway and a recorded Fedora worker
image. The worker has `Network=none`; communication is authenticated SSH carried over a narrowly shared Unix socket.
Neither container gets a Podman or Docker control socket. CLI validation precedes Telegram. Keep the selected dedicated
OpenAI API key and `gpt-5.6-luna`; do not silently substitute a provider or model. [F3: lines 53–63, 111–157, 409–417]

```text
Your workstation
    |
    | SSH, verified host key; administrator account aicowork
    v
Fedora 44 Server — 10.0.30.10
    |
    +-- Host administration: aicowork + sudo
    |
    +-- Runtime: hermes, rootless Podman, lingering user manager
         |
         +-- Gateway: provider/Telegram access; gateway-only credentials
         |      |
         |      +-- Authenticated SSH over a shared Unix socket
         |                     |
         +-- Offline worker <--+
                Workspace only; preinstalled tools; no Internet or LAN route

Neither container receives the host runtime socket or aicowork's home.
```

**Terms:** the gateway handles model and messaging requests; the worker runs permitted tools; a Quadlet is a
container-service definition read by Podman/systemd.

The two-container pattern is the agreed design, not a claim of production validation. Containers share the kernel. The
gateway necessarily uses its own credentials. Worker output can return to the gateway and then to a model provider: an
offline worker does not make the entire agent an offline system. [F3: lines 225–229]

## 2. What this review confirmed—and what it did not

### Current upstream findings

The official release page confirms **Hermes 0.21.2 / `v2026.9.11`**, including session-store corrections. Keep it as the
reviewed candidate, but record the actual registry digest before deployment. A release tag is not an image digest or
evidence of a validated image. [S1]

The selected `gpt-5.6-luna` model is listed in OpenAI's API documentation. That establishes the documented model
identifier; account access and a real tool-calling request still need testing. [S2]

The exact tagged Hermes SSH backend builds commands using `StrictHostKeyChecking=accept-new`. It also invokes file
synchronization and environment passthrough mechanisms. Therefore, the offline-worker adapter must prove strict host-key
behavior and credential isolation rather than relying on the word “SSH.” [S3, S4]

The tagged Dockerfile starts its supervisor/bootstrap as container root and subsequently drops the application to the
image's Hermes user, whose default UID is 10000. It performs initialization work and has an entrypoint dispatcher. Do
not assume that overriding the image user or dropping every capability will work without checking startup. Host-rootless
operation and the user identity inside a container are different things. [S10]

### Uploaded scripts

| File | Recommendation | Reason |
|---|---|---|
| `setup-ssh-key-only.sh` | Candidate for a console-based manual SSH setup | Validates effective SSH settings, checks the explicit interface/zone, restores labels and attempts rollback. It explicitly says remote access is unverified. |
| `configure-tpm2-auto-unlock.sh` | Hold; do not use for this baseline | Incorrectly broad crypttab edits, weak readiness inference, automatic resealing behavior, and boot-policy scope conflicts. |
| `Pasted markdown.md` | Preserve as the source decision record | Defines two containers, an offline worker, manual gates and no deployment authorization. |

**Local tests actually performed:** both shell files passed `bash -n` and their `--help` path under Bash 5.2.37. A
temporary-text test reproduced the TPM script's crypttab rewriting problems. No SSH configuration, disk enrollment,
initramfs generation or Fedora runtime test was performed. ShellCheck was not available in this environment. Uploaded
files were not modified. The presence of these scripts does not prove they have run on your server. Inspect the current
state before changing it; do not undo an existing working setup merely because a script is attached.

The TPM script searches the whole crypttab for any TPM option, and otherwise appends text to every non-comment line. It
can skip the target when another entry already contains the option; alter unrelated devices; corrupt blank lines; and
append an option to the keyfile field of a three-field entry. Its generic token test does not establish which token
unlocked the device or that the next initramfs will boot. These are source-review findings, with the line-rewriting
defects reproduced using a local fixture. [F2: lines 284–318, 366–390, 438–452, 505–528]

## 3. Establish safe access before changing anything

**Keep a working console or out-of-band recovery path available.** Unless an existing auto-unlock setup has
independently passed its recovery tests, expect a reboot to require the disk-unlock passphrase at the console. Do not
schedule an unattended reboot until that recovery path is proven.

At the **server console**, record the SSH host-key fingerprint:

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Compare it with the workstation connection prompt. A reinstall can legitimately change host keys, but independently
verify the new fingerprint before updating a saved known-host entry. Do not use `StrictHostKeyChecking=no` or blindly
erase a mismatch.

The uploaded plan records the workstation identity below. Use it only where that existing private key is actually
present. After saving the verified host key, connect from the **workstation**:

```bash
ssh -o StrictHostKeyChecking=yes \
    -o IdentitiesOnly=yes \
    -o ForwardAgent=no \
    -i /var/home/cloudops/.ssh/id_ed25519_cloudops \
    aicowork@10.0.30.10
```

The private key stays on the workstation. Any key copied to the server for `authorized_keys` must be the `.pub` file
only. [F3: lines 77–109; S11]

At the **server**, verify the administrator identity and sudo access:

```bash
whoami
id
sudo -v
```

Expected: `aicowork`, successful administrative authentication. Keep this session open and use a second fresh connection
to validate later SSH or firewall changes.

## 4. Inspect the actual Fedora installation

**Server — read-only inspection:**

```bash
cat /etc/fedora-release
hostnamectl
lscpu
free -h
swapon --show
ip -br address
ip route
nmcli connection show --active
```

Record CPU count, RAM and whether `10.0.30.10` is static or backed by a DHCP reservation. Do not guess the gateway,
subnet mask, DNS server, interface name or management subnet from the address alone.

```bash
lsblk -o NAME,SIZE,FSTYPE,FSVER,TYPE,MOUNTPOINTS
findmnt --mountpoint /
findmnt --mountpoint /var
findmnt --mountpoint /home/hermes
sudo vgs
sudo lvs -o vg_name,lv_name,lv_size,segtype
sudo cryptsetup isLuks --type luks2 /dev/nvme0n1p3

df -hT / /var /home/hermes
getenforce
stat -fc %T /sys/fs/cgroup
sudo systemctl is-active firewalld
sudo firewall-cmd --get-active-zones
sudo ss -lntup
timedatectl
```

Expected: Fedora 44 Server; the accepted mounts; LUKS2 recognized; XFS for the three data filesystems; regular rather
than thin LVs; `Enforcing`; cgroup v2 (`cgroup2fs`); active firewalld. A mismatch is a stop-and-review condition, not
permission to reformat anything. Quadlet requires cgroup v2. [S6]

The supplied repository plan calls for at least **8 GiB RAM and 20 GiB free under `/var`**. Those are that profile's
prerequisites, not a measured Hermes minimum; also check available space under `/home/hermes`. [F3: lines 65–89]

Record a sanitized baseline with a UTC timestamp. Do not collect passwords, environment dumps, private keys or API
tokens.

## 5. Update Fedora and install host tools

**Server — after baseline acceptance and during an authorized maintenance window:**

```bash
sudo dnf upgrade --refresh
```

Review the transaction before accepting it. Install the host tools needed for the selected profile:

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
```

`tpm2-tools` is listed explicitly because the manual profile's `boot/b4-verify.sh` reads PCR 7 with
`tpm2_pcrread`, and the enrollment and fallback helpers use it as well. The 5.1b upgrade happens to pull it in
as a dependency on a networked install, which is why its absence here is harmless *on that path* — it matters
for the DVD-only/offline path, which this repository recorded dracut failing on. Listing it keeps the profile
self-contained. (Corrected in C53; the deployment guide's §5.1 list was corrected in C51, and this second list
was initially missed.)

Use Fedora's configured signed repositories. Do not disable signature verification or add an unrelated repository to
work around a missing package. Resolve missing providers with `dnf provides` and review the result. Fedora publishes
Podman, passt, subordinate-ID utilities and the DNF5 plugin packages; exact versions must come from the server's
repositories. [S7, S8, S9, S28]

Do not install Docker alongside Podman just for compatibility. Do not run the Hermes curl-to-shell installer on the host
for this containerized profile. Keep Python application dependencies, browser packages and build toolchains in the
appropriate images, not the base server.

```bash
sudo systemctl enable --now chronyd
chronyc tracking
mokutil --sb-state
rpm -q podman container-selinux passt systemd dnf5
```

If Secure Boot is not in the agreed state, stop and review firmware/boot implications. Do not automatically change
firmware settings or enroll boot keys. Confirm console access and the LUKS passphrase before any controlled reboot:

```bash
sudo systemctl reboot
```

After unlocking at the console and reconnecting, repeat the mount, SELinux and service checks. Only the reboot test—not
the written configuration—establishes that this host boots as intended.

## 6. Back up encryption metadata; leave TPM enrollment alone

Verify that `/dev/nvme0n1p3` is the intended LUKS device before these commands. They back up metadata; they do not
reformat or enroll a token.

```bash
sudo install -d -m 0700 /root/recovery
sudo cryptsetup luksHeaderBackup /dev/nvme0n1p3 \
  --header-backup-file "/root/recovery/nvme0n1p3-$(date -u +%Y%m%dT%H%M%SZ).header"
sudo vgcfgbackup fedora_hermes
```

Move a verified copy of the header backup and LVM metadata to separate, encrypted storage. A copy only under `/root` is
not a recovery solution for failure of this disk. Keep the LUKS passphrase separately. A header backup contains
sensitive keyslot material; do not attach it to tickets or public repositories. `vgcfgbackup` saves LVM metadata, not
filesystem contents. [S19, S20]

**TPM auto-unlock is an optional later decision, not baseline hardening.** It changes the physical-access threat model
and update/recovery behavior. Automatic unlock can make an intact stolen machine bootable; it is not inherently stronger
than requiring a separate passphrase. The script's default PCR `0+7` includes firmware measurements, so firmware changes
can invalidate the policy. **Superseded (C53):** the authoritative policy for this profile is **PCR 7 only, SHA-256
bank, no PIN** — PCR 7 already covers Secure Boot and the firmware state that PCR 0 was reaching for, and the validation
run enrolled exactly that. Treat the `0+7` description above as the superseded script's behaviour, not the target.
Either way the conclusion holds: firmware changes can invalidate the policy, so re-verify rather than automatically
resealing to whatever state is present. Do not automatically reseal to whatever boot state happens to be present after a
failure. A later revision should verify the target and boot policy, back up first, preserve a tested independent
recovery credential, edit only the matching crypttab record and test an actual reboot. [S12; F2: lines 66–73, 438–452]

Do not use the script's `PASSWORD=...` command-line example: it can leave a secret in shell history and environment. Do
not assume the manual recovery passphrase is specifically in keyslot 0; verify actual slots.

## 7. Configure key-only SSH without locking yourself out

The attached SSH script is designed for console use and a standard Fedora SSH configuration. It rejects various
customized `Match`, include, socket activation and firewall configurations instead of guessing. Its dry-run is useful
but does not validate a real remote login. [F1: lines 81–99, 130–149, 197–240, 386–427]

At the **server console**, identify the actual interface and zone:

```bash
ip -br address
sudo firewall-cmd --get-active-zones
```

Place the reviewed script and your public-key file in a known working directory. Substitute the real interface and zone
in this example; the literal `REPLACE_...` values are intentionally not usable:

```bash
sudo bash ./setup-ssh-key-only.sh \
  --user aicowork \
  --public-key-file ./id_ed25519_cloudops.pub \
  --interface REPLACE_WITH_INTERFACE \
  --zone REPLACE_WITH_ZONE \
  --dry-run
```

Review all output. When appropriate, execute the same command without `--dry-run`, still from the console. Do not bypass
its checks merely to force success.

Its intended effective settings are:

```text
PubkeyAuthentication yes
AuthenticationMethods publickey
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
```

Verify syntax and effective configuration:

```bash
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T | grep -E \
'^(pubkeyauthentication|authenticationmethods|passwordauthentication|kbdinteractiveauthentication|permitrootlogin) '
```

In a **new workstation connection**, require public-key authentication and disable connection multiplexing for the test:

```bash
ssh -o ControlPath=none -o StrictHostKeyChecking=yes \
    -o IdentitiesOnly=yes -o ForwardAgent=no \
    -o PreferredAuthentications=publickey \
    -i /var/home/cloudops/.ssh/id_ed25519_cloudops \
    aicowork@10.0.30.10
```

Verify `sudo -v` inside that session. Separately, the following must fail because it deliberately disables public-key
authentication:

```bash
ssh -o ControlPath=none -o StrictHostKeyChecking=yes \
    -o PubkeyAuthentication=no \
    -o PreferredAuthentications=password,keyboard-interactive \
    aicowork@10.0.30.10
```

Keep the administrator's local password for sudo and console recovery. Key-only SSH does not require locking the human
admin password. Keep Fedora's maintained cryptographic policy rather than copying an old cipher list. For a single-admin
host, an explicitly reviewed `AllowUsers aicowork` rule is an optional additional restriction; validate it before
closing recovery access. [S11]

**Recovery:** use the console to restore the previous SSH configuration, run `sshd -t`, then reload `sshd`. The script's
error handler attempts restoration, but cannot guarantee recovery after a successful local change that later proves
unreachable remotely. [F1: lines 289–327, 379–383]

## 8. Keep the host network exposure small

The baseline is **SSH for management; no published Hermes ports**. Telegram will use the selected polling mode, not a
public webhook listener. Leave the current IP configuration alone while hardening.

Inspect before changing:

```bash
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --list-all-zones
sudo firewall-cmd --permanent --list-all-zones
sudo ss -lntup
```

Use the actual active management zone. If Cockpit is unnecessary, disable its socket and remove the `cockpit` service
from that zone only after confirming SSH works. If keeping Cockpit, restrict it to management access; do not expose it
publicly just because Fedora installed it.

For firewall changes, keep permanent rules known-good while testing runtime rules. A timed reload can restore the
permanent rules if a runtime test cuts access:

```bash
# Only after confirming the PERMANENT rules preserve your management access.
sudo systemd-run --unit=hermes-fw-rollback \
  --on-active=5m /usr/bin/firewall-cmd --reload
```

Make one runtime change, then establish a fresh SSH connection. After it succeeds, write that same specific change to
the permanent configuration and cancel the rollback timer:

```bash
sudo systemctl stop hermes-fw-rollback.timer
sudo firewall-cmd --check-config
```

A rollback timer is not protection against a broken permanent configuration. Do not run a blanket firewall reset or
flush nftables. Firewalld separates runtime and permanent state, and a reload replaces runtime configuration with the
permanent rules. [S13]

For tighter SSH source restrictions, first establish the actual management workstation or subnet, including its IPv6
path if used. An IP of `10.0.30.10` is not proof that all of `10.0.30.0/24` should be trusted.

**Worker network:** `Network=none` is a container setting, not a host firewall rule. Do not put the worker in the
gateway's pod or shared network namespace. **Gateway egress:** no published ports does not restrict outbound traffic.
Keep provider/Telegram access deliberately scoped; stronger gateway destination restrictions require an enforced proxy
or network policy and their own tests. Avoid hard-coded API IP allowlists that become stale. [S14]

## 9. Bound logs and make updates predictable

### System journal

Back up or review existing overrides before creating `/etc/systemd/journald.conf.d/60-hermes-host.conf`:

```ini
[Journal]
Storage=persistent
SystemMaxUse=1G
SystemKeepFree=2G
MaxRetentionSec=14day
```

Apply and inspect:

```bash
sudo systemctl restart systemd-journald
sudo journalctl --flush
journalctl --disk-usage
```

These are proposed budgets for your 40 GiB `/var`, not mandatory system defaults. They bound journal usage and maximum
age; they do not guarantee 14 days of retention when the size limit is reached. Hermes file logs and `/var/log/audit`
need separate retention. Do not enable full prompt/environment debug logging in production. [S15]

Verify auditing is available:

```bash
sudo systemctl is-active auditd
sudo auditctl -s
sudo ausearch -m AVC,USER_AVC -ts recent
```

Investigate unexpected AVC denials. Do not install a generated `audit2allow` policy or set SELinux permissive as a
shortcut. For later targeted auditing, watch administrator-owned configuration and credential permission changes—not
every workspace file access. Preserve useful audit evidence without recording secrets.

### Download-only OS updates

Review or back up `/etc/dnf/automatic.conf`, then set these values, preserving unrelated settings:

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
sudo systemctl cat dnf5-automatic.service
sudo systemctl enable --now dnf5-automatic.timer
systemctl list-timers dnf5-automatic.timer
```

Check that no service override supplies `--installupdates`. Review updates weekly and promptly address urgent security
fixes in a controlled window. Download-only is staging, not patching. The DNF5 timer honors its configuration unless
command-line overrides change it. Keep application images manually promoted and digest-pinned; do not add a Podman
`AutoUpdate=registry` policy to this profile. [S16; F3: lines 183–185]

## 10. Create the dedicated runtime account correctly

### Verify the mount before creating or changing directories

```bash
findmnt --mountpoint /home/hermes
sudo ls -ldZ /home/hermes
getent passwd hermes
```

When `hermes` does not exist, create a **regular unprivileged account with a non-login shell**, not a system-UID
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

An existing account must be inspected first: correct home, shell, UID/GID and group membership. Do not silently recreate
it. A fixed numeric UID is not required; record the actual one. Avoid `useradd --system` here because subordinate-ID
allocation and user-manager behavior need to be deliberately verified for rootless containers. [S5]

```bash
id hermes
getent passwd hermes
sudo -l -U hermes
sudo grep '^hermes:' /etc/subuid /etc/subgid
command -v newuidmap
command -v newgidmap
```

Expected: no wheel/sudo privileges, no Docker group, and valid subordinate UID and GID ranges. Require at least 65,536
subordinate IDs of each kind for this profile. Check ranges against **all entries** in `/etc/subuid` and `/etc/subgid`,
not only the `hermes` line. If missing, an administrator must select unused ranges before running `usermod --add-subuids
START-END` and the corresponding GID command. Do not copy an arbitrary range from a guide. Do not change mappings after
building the container store without a migration plan. [S5]

### Prepare separate directories

Before any containers are running:

```bash
sudo install -d -o hermes -g hermes -m 0700 \
  /home/hermes/.config \
  /home/hermes/.local \
  /home/hermes/.cache/podman-tmp \
  /home/hermes/gateway-state \
  /home/hermes/workspace \
  /home/hermes/worker-state \
  /home/hermes/transport
sudo restorecon -Rv /home/hermes
```

Do not later run recursive `chown` or `restorecon` over an active rootless container store. Container files can belong
to mapped subordinate UIDs and have container-specific labels.

Create administrator-controlled locations separately:

```bash
HERMES_UID=$(id -u hermes)
sudo install -d -o root -g root -m 0755 \
  "/etc/containers/systemd/users/$HERMES_UID" /etc/hermes
sudo install -d -o root -g root -m 0700 /etc/hermes/secrets
```

`/etc/hermes/secrets` is only a reserved administrator directory at this stage. Final rootless mount permissions must be
designed for the verified container UID mapping; a root-only directory is not automatically readable by a rootless
runtime.

## 11. Start a persistent rootless user manager safely

A non-login shell does not prevent administrators from running specific commands as `hermes`. Do not give that account
an interactive login just to make `systemctl --user` convenient.

First protect the user manager against a missing data mount. Review any existing `20-hermes-data.conf` before writing
it, then create this **system-level** drop-in:

```bash
HERMES_UID=$(id -u hermes)
sudo install -d -m 0755 "/etc/systemd/system/user@${HERMES_UID}.service.d"
sudo tee "/etc/systemd/system/user@${HERMES_UID}.service.d/20-hermes-data.conf" >/dev/null <<'EOF'
[Unit]
RequiresMountsFor=/home/hermes
AssertPathIsMountPoint=/home/hermes
EOF
```

Then:

```bash
HERMES_UID=$(id -u hermes)
sudo systemctl daemon-reload
sudo loginctl enable-linger hermes
sudo systemctl start "user@${HERMES_UID}.service"
loginctl show-user hermes -p Linger -p RuntimePath
```

Do not rely on a user-level mount dependency to manage a system-level mount. The dependency above belongs to the system
user-manager service. Linger keeps that manager available without an ordinary login. [S17]

In your **server admin shell**, define this convenience function. It passes a small explicit environment and checks the
mount before each invocation:

```bash
HERMES_UID=$(id -u hermes)
h() {
  if ! mountpoint -q /home/hermes; then
    printf 'STOP: /home/hermes is not mounted.\n' >&2
    return 1
  fi
  sudo -u hermes -- env -i --chdir=/home/hermes \
    HOME=/home/hermes USER=hermes LOGNAME=hermes \
    PATH=/usr/local/bin:/usr/bin:/bin \
    TERM="${TERM:-xterm}" \
    XDG_RUNTIME_DIR="/run/user/$HERMES_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$HERMES_UID/bus" \
    TMPDIR=/home/hermes/.cache/podman-tmp \
    "$@"
}
```

This is an administrator convenience function, not a sudo grant to Hermes. Redefine it after reconnecting when needed.

```bash
h id
h systemctl --user is-system-running
h podman info --format \
'rootless={{.Host.Security.Rootless}} cgroups={{.Host.CgroupsVersion}} manager={{.Host.CgroupManager}} driver={{.Store.GraphDriverName}} graphroot={{.Store.GraphRoot}}'
h podman unshare cat /proc/self/uid_map
h podman unshare cat /proc/self/gid_map
```

Expected: rootless true, cgroup v2, systemd cgroup management and graphroot under
`/home/hermes/.local/share/containers/storage`. A degraded user manager requires investigation; it is not automatically
a failed installation, but record its failed units.

The explicit `TMPDIR` keeps image-download temporary storage on the data LV; Podman's default for those downloads is
`/var/tmp`. Put the same host-side `TMPDIR` in the `[Service]` section of future Quadlets. Inside-container temporary
storage is a separate setting. [S5]

Keep Fedora's available overlay/runtime defaults initially. Do not force VFS, change graphroot after pulling images, or
disable user namespaces. Do not enable `podman.socket` for this design, and do not mount any runtime socket into an
application container. [S18]

## 12. Stage the application design—but do not activate it prematurely

### Rootless Quadlets

The administrator-owned rootless source directory is:

```text
/etc/containers/systemd/users/<actual-hermes-UID>/
```

Not `/etc/containers/systemd/`, which is the rootful path. Do not try to obtain a rootless service by adding `[Service]
User=hermes` to a system Quadlet. User Quadlets generate user services. Autostart is expressed with `[Install]
WantedBy=default.target`; generated services are not enabled like ordinary hand-written unit files. Validate syntax
against the installed Podman version. [S6]

Administrator ownership is a change-control measure, not a tamper-proof boundary after compromise of the host `hermes`
account: rootless user configuration paths still exist. Keep those paths outside container mounts.

Record these intended components:

```text
hermes-worker.container
hermes-gateway.container
Administrator-owned worker transport configuration
Administrator-owned gateway SSH configuration and pinned worker host key
Recorded Fedora worker image build recipe and package manifest
Digest-pinned gateway image and deployment manifest
```

Do not put deployment private keys, gateway tokens or the Podman graphroot in a shared workspace mount.

### Resolve an image identity before starting it

Confirm the registry/repository and tag from the official release workflow and Docker documentation. Resolve its digest
using `skopeo inspect`; record the digest, architecture, release, provenance/revision and source of trust. A typical
command shape is:

```bash
# Substitute the verified repository and release tag; not a runnable identity.
skopeo inspect --format '{{.Digest}}' \
  docker://VERIFIED_REGISTRY/VERIFIED_REPOSITORY:VERIFIED_RELEASE_TAG
```

Pull the recorded digest as `hermes`, then use only that digest in the Quadlet. No floating `latest`, no invented
SHA256, no disabled TLS verification. Digest pinning prevents tag movement from changing the selected bytes; it does not
by itself authenticate the publisher or prove an image is safe. Review available upstream signatures/attestations rather
than assuming they exist. [S1, S21]

Before gateway activation, inspect the image's user, entrypoint, command, labels and actual version. Test startup
against the proposed read-only root and capabilities. The current image's bootstrap means that `User=1000`,
`UserNS=keep-id` and `DropCapability=all` are not universal drop-in choices. Do not use `chmod 777`, privileged mode or
writable application code to paper over a UID/startup mismatch. [S10]

### Required container controls

| Control | Gateway | Worker |
|---|---|---|
| Host runtime | Rootless Podman | Rootless Podman |
| Root filesystem | Read-only after startup requirements are validated | Read-only; tools baked into image |
| Network | Deliberate provider/Telegram access | `Network=none`; separate network namespace |
| Published ports | None | None |
| Files | Gateway state and its necessary credentials | Workspace and necessary worker/transport state only |
| Capabilities | Smallest tested set; drop unnecessary capabilities | Smallest tested set; consider SSH daemon startup requirements |
| Privilege escalation | Container-level no-new-privileges | Container-level no-new-privileges |
| Seccomp / SELinux | Default seccomp; enforcing labels | Default seccomp; enforcing labels |
| Resource bounds | Explicit memory/PID/temp-space budget | Explicit memory/PID/temp-space budget |
| Runtime control socket | Never mounted | Never mounted |

Use `[Container] NoNewPrivileges=true` for the container process. Do not blindly add `[Service] NoNewPrivileges=yes`,
`RestrictNamespaces=yes` or a restrictive host capability bounding set around the Podman launcher: the launcher may need
user-namespace mapping helpers. A high `systemd-analyze security` score is not a substitute for functional isolation
tests. [S6, S22]

### SELinux labeling

Use private container labels (`:Z`) for private bind-mounted data and a deliberately shared label (`:z`) only for the
minimal shared transport directory. Do not relabel all of `/home/hermes` as a shared container directory. Do not mount
`/`, `/home/aicowork`, `/run/user/<UID>` wholesale or `.local/share/containers` into either container. [S14]

Shared file labels alone do not prove an SSH Unix-socket connection between containers is permitted. Check socket
permissions, UID mapping and actual AVC denials. If standard policy cannot support the agreed topology, stop M02; custom
SELinux policy and disabling labels are not authorized fallbacks. [F3: lines 151–181]

## 13. The offline-worker acceptance work that cannot be skipped

The plan's Unix-socket integration is still a **proposed integration**. An ordinary TCP-only SSH worker cannot become
reachable merely by setting `Network=none`. Keep the offline property and build/validate the specified adapter rather
than quietly switching to a shared network.

The design to prove is: SSH client traffic is carried over a local filesystem socket; a worker-side adapter delivers
that stream to SSH inside the worker's isolated environment. Preinstall the adapter and all worker utilities in the
worker image. The socket is not a Podman control endpoint.

Required evidence before any real API secret is loaded:

1. **Identity:** a dedicated worker client key, a pre-pinned worker host key, and forwarding disabled. Test both a
   changed host key and a missing trusted key: both must fail.
2. **Transport and tools:** shell, file reads/writes and code execution land in the worker. Test each enabled tool; do
   not infer file/code isolation from a successful terminal command.
3. **Isolation:** the worker has no route to the Internet, host services, cloud metadata or management networks. Test
   with bounded disposable probes and inspect the network configuration; a failed ping alone is not proof.
4. **Secrets:** synthetic canaries in gateway-only credential locations do not appear in worker mounts, environment,
   synchronized files or logs. Repeat after loading any skill that can register environment or credential passthrough.
5. **Failure handling:** stopping the worker produces a tool error, not a fallback to gateway-local execution. Files
   returned from the worker remain untrusted inputs; do not automatically promote them into gateway configuration or
   executable plugins.

Hermes's tagged backend explicitly requests `accept-new` on its SSH command line. A `StrictHostKeyChecking=yes` entry in
an ordinary client config does not override a conflicting command-line option. A reviewed adapter/wrapper or another
supported mechanism must enforce strict behavior across `ssh`, `scp`, multiplexed connections and file synchronization.
Record that integration without mutating upstream application code in place. [S3, S11]

Hermes can synchronize configured and skill-selected credential files and forward selected environment values. This does
**not** mean it always forwards every master secret; it means an empty Docker-specific forwarding list is not enough for
the SSH profile. Keep SSH-specific passthrough empty, disable optional credential-bearing skills, and test the precise
selected release. [S4, S23]

If any of these tests fails, leave the application stopped. The Fedora host can be ready while M02/M03 remain open. Do
not describe that state as a finished hardened Hermes deployment.

## 14. Credentials, CLI and Telegram

Initially use restrictive files on encrypted storage, mounted read-only only where the verified gateway UID can read
them. This follows the supplied plan. File permissions must be tested from the actual container identity; do not assume
a host file owned by UID 10000 is correct for a rootless mapped user. Keep secrets out of Quadlet source, Git, shell
command arguments, screenshots and worker mounts. [F3: lines 127–149]

Mount only required secret files, not an entire administrator directory. A read-only secret mount prevents
modifications; it does not hide the secret from the gateway process that must use it. Do not give the gateway your
personal OpenAI, GitHub, cloud-admin or deployment credentials when a dedicated restricted credential will do.

Test `gpt-5.6-luna` with the intended API credential and a harmless request that returns `HERMES_OK`; then verify a
harmless tool round-trip. Record success/failure and model identity without printing the API key. A listing in the
public model catalog is not account authorization. [S2]

Keep human dangerous-command approval, deny unattended dangerous operations, keep SSRF protection enabled and runtime
dependency installs disabled, and validate Tirith failure behavior. Verify the actual candidate's configuration names
and effective behavior; do not invent a YAML key or rely on a prompt saying “be safe.” Initially disable
browser/computer-use, third-party plugins, broad MCP integrations, scheduled autonomous jobs and unrelated toolsets.
[F3: lines 141–149]

Only after CLI and recovery pass, enable Telegram with explicit numeric authorized user IDs and no public application
port. Test an authorized user, an unauthorized user and approval responses. Ensure a worker failure still cannot trigger
local fallback. Never write the bot token in the evidence ledger. [F3: lines 165–179]

## 15. Optimize conservatively

These are **proposed starting budgets**, not benchmark results. Your RAM and CPU are not yet confirmed.

| Host RAM | Example gateway memory cap | Example worker memory cap | Example total `hermes` slice cap | Intended reserve |
|---|---:|---:|---:|---|
| 8 GiB | 2 GiB | 2 GiB | 5 GiB | Around 3 GiB for host and remaining activity |
| 16 GiB | 3 GiB | 6 GiB | 10 GiB | Around 6 GiB |
| 32 GiB or more | 4 GiB | 8 GiB | 16 GiB initially | At least 16 GiB at 32 GiB total |

Start with one worker task at a time. Increase concurrency only after measuring. A container's memory limit and a parent
slice limit serve different purposes: the parent also bounds combined child activity. Leave space for the user manager,
container supervision, tmpfs, image pulls and builds. Treat hard memory limits as emergency containment: exceeding them
can terminate processes. [S24]

After confirming **at least 16 GiB RAM**, an example parent budget—not a universal command—is:

```bash
HERMES_UID=$(id -u hermes)
sudo systemctl set-property "user-${HERMES_UID}.slice" \
  MemoryHigh=8G MemoryMax=10G TasksMax=2048
```

Do not apply those numbers to an 8 GiB machine. Record old settings and test behavior before making limits part of
acceptance. Per-container PID limits such as 256 for the gateway and 512 for a build worker are starting proposals; the
exact supervisor/toolchain may require adjustment. Set bounded tmpfs mounts for `/tmp` and any required runtime
directories, and remember tmpfs consumes memory.

### High-value improvements

| Improvement | Recommendation |
|---|---|
| Dependencies | Bake worker tools into the image; no runtime package downloads |
| Container store | Keep the default rootless store on `/home/hermes`; use explicit TMPDIR for pulls |
| CPU | Start with Fedora defaults; use weights/limits to protect SSH responsiveness, then measure |
| Memory | Retain the existing encrypted swap; inspect any zram configuration rather than adding a second policy blindly |
| Filesystems | Keep XFS, regular LVM and the reserve; no repartitioning or speculative quota guarantee |
| Logging | Bounded journal and app logs; no verbose secrets or prompts |
| Updates | Stage downloads; manually promote tested images; keep rollback data |
| Availability | Test recovery and off-disk backup before unattended operation |

Do not disable SELinux, seccomp, kernel mitigations or user namespaces to chase performance. Do not globally force
swappiness to 1, disable all swapping, switch to an untested I/O scheduler or put `noexec` on the whole container store.
Workload behavior and compressed swap change the trade-offs; measure memory pressure and I/O rather than copying generic
tuning recipes. [S25]

Useful **server** measurements:

```bash
free -h
vmstat 1 10
iostat -xz 1 10
cat /proc/pressure/cpu /proc/pressure/memory /proc/pressure/io
h podman stats --no-stream
h podman system df
df -hT / /var /home/hermes
systemctl status fstrim.timer --no-pager
```

Inspect SSD health periodically. Do not add dm-crypt discard options solely because a generic SSD guide recommends them;
whether discard passes through encryption is a separate privacy/operations choice. [S29]

Set operational alerts or checks at approximately **75% used** and critical handling around **85% used** for each
filesystem. These are my suggested thresholds. The journal limit does not bound all `/var` usage; downloaded RPMs and
audit logs still matter. Do not automate `podman system prune --volumes` or `podman system reset`.

When a measured need arises, use the free extents. After backup and confirming the VG/LV names:

```bash
# Future capacity action only; do not run during initial preparation.
sudo lvextend -L +25G /dev/fedora_hermes/lv_hermes
sudo xfs_growfs /home/hermes
```

The filesystem growth is a separate step from LV growth. Do not assume it can be reversed by shrinking XFS; allocate in
small deliberate increments. [S20, S26]

## 16. Backups, rollback and recovery

Use a stopped-state application backup for initial acceptance: stop the gateway, ensure CLI/other writers are also
stopped, then stop the worker and capture the persistent data with an appropriate backup tool. Preserve ownership,
subordinate-ID mappings, ACLs and extended attributes or document the relabeling/restoration steps. Keep a manifest of
image digests, UID/GID mappings, Quadlets and selected configuration alongside the backup.

Back up gateway state, workspace, required worker state, configuration, worker trust keys, authorized access
information, encryption recovery material and the deployment manifest. Store provider/bot credentials only in encrypted
backups with restricted access. Exclude disposable image layers and caches when they can be reconstructed from pinned
artifacts, but retain a method of obtaining the previous known-good image.

For a full accepted lifecycle:

| Situation | Recovery approach |
|---|---|
| SSH misconfiguration | Console; restore previous files; validate with `sshd -t`; reload |
| Runtime firewall mistake | Timed reload of known-good permanent rules, or console recovery |
| Missing Hermes data mount | Leave user manager/application stopped; repair mount, do not recreate data on `/` |
| Bad image update | Stop writers; restore compatible pre-update state and previous image digest |
| Failed boot update | Console and existing fallback kernel; unlock with known recovery credential |
| Storage pressure | Stop new work; inspect growth; deliberate cleanup or LV expansion |
| Worker/transport failure | Tool error; no local or online-worker fallback |

An old image may not understand a database migrated by a new image. Image rollback alone is not sufficient; test a
compatible state restore. Never run two gateways against the same state directory. [S27]

Keep backups off this SSD and perform an actual restore into an isolated path before declaring M04 passed. A file called
“backup” is not evidence of successful recovery. LUKS-header restoration is not an ordinary application rollback
procedure.

## 17. Acceptance and handoff

Preserve the original gate names and order from the uploaded execution record. No live gate is passed by this document.

| Gate | Pass evidence required |
|---|---|
| M01 — Access and baseline | Verified host identity and SSH; console recovery; OS, mounts, hardware and security baseline |
| M02 — Artifact and worker validation | Exact image identities; authenticated strict worker transport; all enabled tools execute in the worker; offline isolation tests |
| M03 — Credentials and CLI | Selected API/model returns `HERMES_OK`; safe tool task; synthetic secret-canary isolation |
| M04 — Hardening and recovery | Effective runtime identity, capabilities, seccomp, SELinux, mounts and limits; restart/reboot; backup restore and rollback |
| M05 — Telegram | Authorized user succeeds; unauthorized user rejected; approvals work; worker failure has no fallback |
| M06 — Guideline acceptance | Dated sanitized evidence; actual commands/config identities; limitations and recovery match the installation |

For each check record: UTC timestamp, command, expected result, actual result, exact artifact/config identity and a
sanitized evidence reference. Keep failed results; mark affected prior passes stale after changing images, configuration
or host conditions. The uploaded plan's earlier branch/lint results are historical documentation evidence, not live host
acceptance. [F3: lines 159–185, 289–311]

### Definition of “Fedora prepared”

Verified admin access and recovery; expected mounts and encrypted storage; updates applied in a controlled window;
SELinux enforcing; active reviewed firewall; time synchronized; separate non-sudo runtime account; valid subordinate
ranges; functioning rootless user manager and Podman; bounded logs; download-only update policy; initial recovery
backups.

### Definition of “Hermes accepted”

All of M01–M06 pass on the actual server. In particular, no claim of full hardened readiness while socket transport,
image startup, credential isolation, Telegram authorization or restore testing remain unverified.

**Recommended immediate next action:** carry out the read-only M01 inventory through the verified management
connection during an authorized session. Do not begin with TPM enrollment or gateway deployment.

---

## Appendix A. Local script test details

Environment: local analysis container, GNU Bash 5.2.37; not Fedora 44 Server. No root-affecting apply path was invoked.

| Check | Result |
|---|---|
| `bash -n setup-ssh-key-only.sh` | PASS — shell syntax only |
| `bash setup-ssh-key-only.sh --help` | PASS — non-mutating help path |
| `bash -n configure-tpm2-auto-unlock.sh` | PASS — shell syntax only |
| `bash configure-tpm2-auto-unlock.sh --help` | PASS — non-mutating help path |
| TPM crypttab `sed` fixture | Defects reproduced |
| ShellCheck | Not run; unavailable |
| Fedora integration / TPM unseal / reboot | Not run |
| Hermes worker transport / provider / Telegram | Not run |

TPM editing fixture, before:

```text
# root mapping

luks-root UUID=1111 none discard
luks-backup UUID=2222 none
```

After applying only the script's `sed` expression to temporary text:

```text
# root mapping
,tpm2-device=auto
luks-root UUID=1111 none discard,tpm2-device=auto
luks-backup UUID=2222 none,tpm2-device=auto
```

The blank line became an invalid record, both devices were changed and the second device's keyfile field was altered.
No real crypttab was edited.

Uploaded script identities:

```text
setup-ssh-key-only.sh
SHA256 eacc931a4f40b508226e7f542afc90c4c1d48d57243fa3a8b064f4f468f02f83

configure-tpm2-auto-unlock.sh
SHA256 f8ca3244afa18731aac3c03589767c67f3ca87c9a78bc70f30189bf54412cfcc
```

These hashes identify the reviewed inputs; they are not publisher signatures or security certifications.

## Appendix B. Sources and evidence boundaries

The uploaded plan is the basis for the chosen profile. The website/source-code references below verify external
behavior; new sizes, resource budgets and process recommendations are explicitly proposed here. Public documentation
cannot establish this server's runtime state. The older linked repository files mentioned inside the plan were not
supplied or edited for this task.

### Uploaded sources

**F1:** `setup-ssh-key-only.sh`, uploaded in this conversation. Relevant ranges: key-only settings 103–149; firewall
        validation 197–240; rollback 289–327; apply 330–383; console/dry-run guards 386–427.

**F2:** `configure-tpm2-auto-unlock.sh`, uploaded in this conversation. Relevant ranges: defaults 66–73;
        token/readiness checks 276–364; crypttab edits 366–390; automatic reenrollment 438–452; verification 487–528.

**F3:** `Pasted markdown.md`, uploaded in this conversation. Relevant ranges: approved design 25–63 and 111–157; host
        prerequisites 65–109; manual gates 159–185; limits 225–229; evidence status 289–311; decisions 409–435;
        handoff 441–449.

### Official external sources reviewed

S1. Hermes release `v2026.9.11`: <https://github.com/NousResearch/hermes-agent/releases/tag/v2026.9.11>

S2. OpenAI GPT-5.6 Luna model: <https://developers.openai.com/api/docs/models/gpt-5.6-luna>

S3. Hermes tagged SSH backend:
<https://raw.githubusercontent.com/NousResearch/hermes-agent/v2026.9.11/tools/environments/ssh.py>

S4. Hermes tagged file synchronization:
<https://raw.githubusercontent.com/NousResearch/hermes-agent/v2026.9.11/tools/environments/file_sync.py>

S5. Podman main manual, rootless storage/runtime: <https://docs.podman.io/en/latest/markdown/podman.1.html>

S6. Podman Quadlet manual: <https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html>

S7. Fedora Podman package: <https://packages.fedoraproject.org/pkgs/podman/podman/>

S8. Fedora passt package: <https://packages.fedoraproject.org/pkgs/passt/passt/>

S9. Fedora subordinate-ID utility package: <https://packages.fedoraproject.org/pkgs/shadow-utils/shadow-utils-subid/>

S10. Hermes tagged Dockerfile: <https://raw.githubusercontent.com/NousResearch/hermes-agent/v2026.9.11/Dockerfile>

S11. OpenSSH server/client manuals: <https://man.openbsd.org/sshd_config> and <https://man.openbsd.org/ssh_config>

S12. systemd TPM enrollment manual source:
<https://raw.githubusercontent.com/systemd/systemd/main/man/systemd-cryptenroll.xml>

S13. firewalld command manual: <https://firewalld.org/documentation/man-pages/firewall-cmd.html>

S14. Podman run options, network namespaces and labels: <https://docs.podman.io/en/latest/markdown/podman-run.1.html>

S15. systemd journal configuration manual source:
<https://raw.githubusercontent.com/systemd/systemd/main/man/journald.conf.xml>

S16. DNF5 automatic updates manual: <https://dnf5.readthedocs.io/en/latest/dnf5_plugins/automatic.8.html>

S17. systemd unit and login manager manuals:
<https://raw.githubusercontent.com/systemd/systemd/main/man/systemd.unit.xml> and
<https://raw.githubusercontent.com/systemd/systemd/main/man/loginctl.xml>

S18. Podman API security: <https://docs.podman.io/en/latest/markdown/podman-system-service.1.html>

S19. Fedora LUKS-header backup guidance: <https://fedoraproject.org/wiki/Disk_Encryption_User_Guide> ; upstream
cryptsetup header-backup manual distributed by Arch:
<https://man.archlinux.org/man/core/cryptsetup/cryptsetup-luksHeaderBackup.8.en>

S20. Red Hat LVM metadata backup documentation:
<https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/7/html/logical_volume_manager_administration/backup>

S21. Skopeo upstream inspect documentation:
<https://github.com/podman-container-tools/skopeo/blob/main/docs/skopeo-inspect.1.md>

S22. systemd execution restrictions manual source:
<https://raw.githubusercontent.com/systemd/systemd/main/man/systemd.exec.xml>

S23. Hermes tagged credential-file registry:
<https://raw.githubusercontent.com/NousResearch/hermes-agent/v2026.9.11/tools/credential_files.py>

S24. systemd resource controls manual source:
<https://raw.githubusercontent.com/systemd/systemd/main/man/systemd.resource-control.xml>

S25. Linux VM tuning documentation: <https://www.kernel.org/doc/html/latest/admin-guide/sysctl/vm.html>

S26. Oracle Linux XFS growth documentation (standard XFS/LVM behavior, not Fedora-specific installation defaults):
<https://docs.oracle.com/en/operating-systems/oracle-linux/8/xfs/xfs-GrowinganXFSFileSystem.html>

S27. Hermes Docker documentation: <https://hermes-agent.nousresearch.com/docs/user-guide/docker>

S28. Fedora DNF5 automatic plugin package: <https://packages.fedoraproject.org/pkgs/dnf5/dnf5-plugin-automatic/>

S29. Upstream cryptsetup open/discard manual distributed by Arch: <https://man.archlinux.org/man/cryptsetup-open.8.en>

Local Bash parsing and fixture results are separate from all website evidence. Some official sites returned fetch
restrictions during research; no statement of live validation is based on those failures. Consult the installed
Fedora/Podman manual pages when options differ from newer upstream documentation.
