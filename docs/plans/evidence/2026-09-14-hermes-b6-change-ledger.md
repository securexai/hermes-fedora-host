# Hermes B6 clean-install validation — change ledger

**Purpose:** the authoritative chronological record of every change made during the B6 validation, as
the source document for a replication guideline. Read alongside
[the evidence record](2026-09-14-hermes-b6-baseline.json) (full detail and findings) and
[the runbook](../../HERMES_BOOT_CLEAN_INSTALL.md) (ordering authority).

**Conventions** — these apply to every entry below.

- Timestamps are UTC. `~` means approximate where the exact value was not captured.
- `priv` is the privilege the change needed: `console` (physical access), `root` (sudo), `user`
  (aicowork), `agent` (read-only over ssh, no change).
- Each entry records the exact command, the effect, how it was verified, and how to reverse it.
- **Redaction convention:** the operator's numeric Telegram user ID is replaced throughout this record by
  `<redacted-telegram-user-id>`. The value is not a credential and the run originally recorded it
  deliberately; it was redacted on 2026-09-14 at the operator's request, before the first commit, because a
  commit makes a personal identifier permanent. **The substitution was applied inside quoted journal output
  as well**, so those quotations are no longer byte-verbatim at exactly that field — nothing else in any
  quotation was altered. Where a value's *length* is load-bearing evidence (the `.env` byte accounting) the
  length is retained and the value is not.
- **As of C6 the agent has no privileged access on the host** (`sudo -n` requires a password; no
  NOPASSWD entry; `/root` unreadable). Every change below was operator-executed. Any entry applied by
  the agent would be marked `priv=root (agent)`, and that would be a deviation from the reference
  posture, which records `password required, no NOPASSWD entry`.

## Fixed environment for this run

| Item | Value |
| --- | --- |
| Hardware | AZW SER3, firmware `PCS.HF5U.V025.P5C4.06.BL` |
| Hostnames | transient `hermes.ai.lab.local`; static unset; workstation `fedora` |
| Address | `10.0.30.10` on `eno1`, firewalld zone `FedoraServer` |
| OS / kernel | Fedora Linux 44 (Server Edition), `6.19.10-300.fc44.x86_64` |
| LUKS | `/dev/nvme0n1p3`, UUID `8919c2b1-5d9a-4fb9-8f85-97d286cbe7ec`, mapper `luks-8919c2b1-…` |
| VG | `fedora_hermes`; LVs `root` 60G, `var` 40G, `hermes` 250G, `swap` 8G, all **linear**; `VFree 115.92g` |
| Machine ID | `fedeed82ba3041dcbbf91c033a76a00c` |
| PCR7 at start | `22103EAC50D6EF26DABCBA626A8E70754586CE66D600563A82CEFBF2CA206A73` (identical to the reference host's B1 value) |
| Recovery workstation | `fedora`; repo `/var/home/cloudops/code/repos/mikrotik`; `private/` is gitignored |

## Change log

### C1 — Fedora 44 Server install

`priv=console`, operator, ~2026-09-14T00:00Z

- **Command:** interactive Fedora 44 Server install, encrypted storage with custom partitioning.
- **Effect:** `nvme0n1p1` 1G vfat `/boot/efi`; `nvme0n1p2` 2G ext4 `/boot`; `nvme0n1p3` 473.9G LUKS2;
  VG `fedora_hermes` with linear LVs `root` 60G, `var` 40G, `hermes` 250G (XFS) and `swap` 8G;
  administrator `aicowork` in `wheel`; Secure Boot left enabled.
- **Verified:** Phase 2 baseline PASS — separate `/home/hermes` mount, all LVs linear, `cgroup2fs`,
  SELinux `Enforcing`, Secure Boot enabled, `keyslots=1`, `tpm2_tokens=0`.
- **Reverse:** reinstall. This destroys the LUKS volume and every key slot in it.

### C2 — Baseline inventory

`priv=root`, operator, 2026-09-14T00:20:15Z

- **Command:** staged read-only script `~/hermes-m01-baseline.sh`
  (sha256 `369e039983411aa3556abb5215325409283881ea53627053c08f3549a4b6f1fd`), output teed to
  `~/hermes-m01-baseline.out` (mode 0600, left on host).
- **Effect:** none — read-only.
- **Verified:** output recorded; the resolver discovery cross-check passed on the real host.
- **Reverse:** n/a.

### C3 — Recovery material for the new volume

`priv=root`, operator, 2026-09-14T00:27:00Z

- **Commands:**
  `install -d -m 0700 /root/recovery`
  `cryptsetup luksHeaderBackup /dev/nvme0n1p3 --header-backup-file /root/recovery/nvme0n1p3-pre-tpm-20260914T002700Z.header`
  `cp -a /etc/crypttab /root/recovery/crypttab-pre-tpm-20260914T002700Z`
  `vgcfgbackup fedora_hermes`
- **Effect:** `/root/recovery` (0700) holding the header backup (16 777 216 bytes, mode 0400) and the
  crypttab backup (113 bytes, mode 0600); LVM metadata written to `/etc/lvm/backup`.
- **Verified:** header `8b4ca6884c4bc4c5a3ceba12266704e27fc2916d2d698a3f3fc2968c3e28e336`, crypttab
  `f4b732ad0f9149139bae466a016e55287aa136c780e56cebe33ad9fe75dba43c`; `luksUUID` confirmed
  `8919c2b1-…`; `cryptsetup open --test-passphrase` returned `SERVER_PASSPHRASE_OK`.
- **Reverse:** delete `/root/recovery`; regenerate the LVM metadata with `vgcfgbackup`.
- **Note:** the passphrase must additionally be stored durably and offline, separately from the header
  backup (runbook step 3.2). That is an operator obligation and is **not** recorded here.

### C4 — Stage recovery material for off-host transfer

`priv=user`, operator, ~2026-09-14T00:30Z

- **Command:** `install -o aicowork -g aicowork -m 0600 /root/recovery/<file> /home/aicowork/` for the
  header and the crypttab backup (because `/root` is not readable as `aicowork`).
- **Effect:** staging copies in `/home/aicowork/`.
- **Verified:** hashes matched the originals before transfer.
- **Reverse:** **outstanding** — delete `~/nvme0n1p3-pre-tpm-*.header` and `~/crypttab-pre-tpm-*`.

### C5 — Off-host transfer of recovery material

`priv=agent`, 2026-09-14

- **Command:** `scp` of both staged files into
  `private/hermes-boot-recovery-8919c2b1/` on the workstation (0700, on the LUKS-encrypted btrfs
  subvolume `luks-da58ecdb-…`). The directory name is keyed on the LUKS UUID so it cannot be confused
  with the reference host's material in `private/hermes-boot-recovery/`.
- **Effect:** the break-glass material now exists off-host and on encrypted storage.
- **Verified:** both sha256 values matched the staged copies exactly.
- **Reverse:** delete the directory.

### C6 — Authorize key-based SSH for the agent

`priv=user`, operator, 2026-09-14

- **Commands:** staged `id_ed25519_cloudops.pub`; `install -d -m 0700 ~/.ssh`;
  append to `~/.ssh/authorized_keys` guarded by `grep -qxF`; `chmod 0600`; `sudo restorecon -RFv ~/.ssh`;
  then `rm -f ~/id_ed25519_cloudops.pub`.
- **Effect:** enabled key authentication for `aicowork`. Password authentication remains enabled —
  hardening it is preparation guide §7 and is **not** done.
- **Verified:** `ssh-keygen -lf ~/.ssh/authorized_keys` printed
  `SHA256:4n2jc2lCZzZX6xFJ84kapol9En3xcZ6hfWfQjpBodNI`; the agent then authenticated and confirmed
  hostname `hermes.ai.lab.local` and machine ID `fedeed82ba3041dcbbf91c033a76a00c`.
- **Reverse:** remove that line from `authorized_keys`.

### C7 — Incidental: workstation `.ssh` relabel (wrong machine, but a real fix)

`priv=root`, operator, 2026-09-14 — **executed on the workstation by mistake**

- **Command:** `install -d -m 0700 ~/.ssh`, append guard, `chmod 0600`, `sudo restorecon -RFv ~/.ssh`,
  `rm -f ~/id_ed25519_cloudops.pub` — intended for the server, run on `fedora`.
- **Effect:** the append silently did nothing (`cat ~/id_ed25519_cloudops.pub` failed because on the
  workstation the key is at `~/.ssh/`, so `grep -qF ""` matched every line and the append was skipped).
  `restorecon` did make a real correction: `~/.ssh/id_ed25519_cloudops` went from
  `system_u:object_r:dosfs_t:s0` to `system_u:object_r:ssh_home_t:s0`. The `dosfs_t` label — a FAT/exFAT
  label — was wrong for a private key and almost certainly came from copying it off the exFAT USB.
- **Verified:** the key still parses and matches its `.pub`; `~/.ssh/authorized_keys` kept its
  2026-04-30 mtime, proving it was not modified; no other file under the home directory carried a
  `dosfs_t` label.
- **Reverse:** n/a — the relabel was desirable. Note the user field remains `system_u` where siblings
  are `unconfined_u`; `restorecon -F` did not normalise it and the reason is not established.

### C8 — Remove host-side staging duplicates (C4 reversed)

`priv=user`, **agent**, 2026-09-14 — the first change applied by the agent; it needed no privilege

- **Command:** on the server as `aicowork`,
  `rm -f ~/nvme0n1p3-pre-tpm-*.header ~/crypttab-pre-tpm-*`.
- **Effect:** removed the 16 777 216-byte header backup and the 113-byte crypttab backup from
  `/home/aicowork`. `~/id_ed25519_cloudops.pub` had already been removed by C6.
- **Verified:** the off-host copies were re-hashed **immediately before** deletion and matched
  (`8b4ca688…` and `f4b732ad…`). After deletion, `ls -la ~` shows only the baseline script and its
  output plus dotfiles.
- **Reverse:** not needed — `/root/recovery` retains the originals, and the verified off-host copies are
  in `private/hermes-boot-recovery-8919c2b1/`.
- **Open item:** the server's `~/.bash_history` now records this run's commands. Nothing sensitive was
  passed as a command argument — the LUKS passphrase and the sudo password were both read from hidden
  prompts — but a replication run should keep it that way, and consider clearing history afterwards.

### C9 — Stage the boot helpers on the host

`priv=user`, **agent**, 2026-09-14

- **Command:** `scp -r scripts/hermes/manual/boot aicowork@10.0.30.10:~/hermes-boot` from the repo root.
- **Effect:** the five helpers now sit in `~/hermes-boot`, owned by `aicowork`, mode 0600 — `b4-verify.sh`,
  `fallback-wipe.sh`, `lib-luks-identity.sh`, `rehearse-clean-install.sh`, `tpm-enroll.sh`. They are
  invoked as `sudo bash <file>`, so no execute bit is needed and root can read them regardless.
- **Verified:** sha256 of all five on the host compared against the local directory — **byte-identical**:
  `b4-verify.sh d14dff3c…`, `fallback-wipe.sh 6c0c117b…`, `lib-luks-identity.sh 629c6092…`,
  `rehearse-clean-install.sh 271c86a6…`, `tpm-enroll.sh f1e2e0af…`.
- **Reverse:** `rm -rf ~/hermes-boot`.
- **Trap:** `scp -r` into an *existing* `~/hermes-boot` nests the source as `~/hermes-boot/boot` and every
  documented path breaks. On any re-stage, remove the directory first. Because the helpers were staged
  before the host-preparation steps, re-verify this manifest (or re-stage) immediately before B3.

### C10 — 5.1 controlled update and host tools

`priv=root`, operator, 2026-09-14 ~01:01–01:10Z — **COMPLETE**

- **Commands:** 5.1a `dnf upgrade --refresh --assumeno` (preview only) → `~/step4-5.1-preview.log`;
  5.1b `dnf upgrade --refresh -y` → `~/step4-5.1-apply.log`; 5.1c `dnf install -y <tool list>` →
  `~/step4-5.1-tools.log`; 5.1d the guide's verification commands.
- **Outcome of 5.1b — `Complete!`:** 396 packages **upgraded**, 21 **installed**, 396 replaced, 815
  transaction steps, 816 MiB downloaded, ~333 MiB net added, zero error/failure/killed matches. The
  versions removed at the end (`glibc-common 2.43-2`, `libgcc 16.0.1-0.10`) are the normal
  replaced-package cleanup, not uninstalls — `glibc-common` appears in the log as `2.43-8 replacing
  2.43-2`.
- **Outcome of 5.1c — `Complete!`:** the transaction installed **13 packages** (15 steps including
  verification and preparation): `dnf5-plugin-automatic 5.4.4.0`, `git 2.55.0`, `skopeo 1.22.2`,
  `sysstat 12.7.9`, plus dependencies `git-core`, `git-core-doc`, `perl-Error`, `perl-Git`,
  `perl-TermReadKey`, `perl-lib` and — notably — `pcp-conf`, `pcp-libs`, `pcp-selinux-import`.
  **`sysstat` now depends on `pcp` on Fedora 44**, which is worth knowing for replication: the
  dependency chain is not obvious from the guide's list. `sysstat`'s `%post` also enabled
  `sysstat.service` and three timers.
- **`tpm2-tools` provenance — a correction.** It was **not** installed by 5.1c: dnf reported
  `Package "tpm2-tools-5.7-5.fc44.x86_64" is already installed`, and the 5.1b apply log shows
  `[343/815] Installing tpm2-tools-0:5.7-5` from the base `fedora` repository, as one of the 21 newly
  installed packages. So the controlled upgrade installs `tpm2-tools` as a dependency, and the guide's
  omission of it from both install lists is harmless **provided 5.1's upgrade runs before B4**. The
  earlier note in this ledger that the guide is unusable without adding it was overstated. It still
  matters in the DVD-only/offline installer path that `docs/plans/2026-09-07-hermes-unattended.md:366`
  records, and if 5.1 is skipped; keeping it explicit in the 5.1 line is harmless insurance.
- **Verified versions:**

  | Package | Before | After |
  | --- | --- | --- |
  | podman | 5.8.1 | **5.8.4** |
  | dnf5 | 5.4.1.0 | 5.4.4.0 |
  | openssh-server | 10.2p1-7 | 10.2p1-14 |
  | systemd | — | 259.8 |
  | tpm2-tools | absent | **5.7-5.fc44** |

- **Kernel — confirmed and installed:** the transaction carried `kernel 7.2.5-200.fc44` with
  `kernel-core`, `kernel-modules` and `kernel-modules-core`. `/boot` now holds both
  `initramfs-6.19.10-300.fc44.x86_64.img` and **`initramfs-7.2.5-200.fc44.x86_64.img`**, the latter
  produced by the kernel's `%post` scriptlet (`kernel-install add 7.2.5-200.fc44.x86_64`) while the
  transaction ran. The reference host ended on `7.2.4-200.fc44`; this run received `7.2.5-200.fc44`.
  `uname -r` is still **6.19.10-300.fc44** and `boot_id` is unchanged — **the reboot has not happened.**
- **Two figures match the reference run exactly:** podman moved **5.8.1 → 5.8.4**, the same transition
  the reference ledger records, and `tpm2-tools-5.7-5.fc44` is the same build the unattended track
  installed. A fresh install reaching the reference's post-update versions is a useful reproducibility
  signal.
- **Post-upgrade health:** `systemctl --failed` reports **0 units**, so the `gssproxy.service` and
  `auditd.service` "unit file changed on disk" warnings during the transaction left no failures. chrony
  is synchronised (stratum 3, `_gateway`) and Secure Boot is still **enabled**.
- **Reboot required before B3.** `tpm-enroll.sh:206-208` runs `dracut -f` and derives the initramfs name
  from `uname -r`. Enrolling while 6.19.10 is running would rebuild **6.19.10's** initramfs and leave
  the already-built 7.2.5 initramfs without the TPM unlock configuration. Change 7 (5.5, static hostname
  - reboot) must therefore complete before B3, confirmed by `uname -r` becoming `7.2.5-200.fc44` and a
  new `boot_id`.
- **Operational observation — intermittent `ssh` failures.** Outbound `ssh` calls sometimes fail with
  `hostname contains invalid characters`. The emitter is confirmed: `grep -oa` finds that string exactly
  once, in **`/usr/bin/ssh`** — not in `scp`, `sftp`, `sudo`, `sshd` or any PAM module. The failures come
  in **random bursts and are not command-dependent**: five consecutive `sha256sum` calls failed and then
  the identical command succeeded, while trivial `echo` calls succeeded immediately before and after the
  burst; `scp` to the same host returned `rc=0` throughout; and the host was up with `sshd` active,
  load ~0.75 and a 1.1 ms ping during the failures. An earlier note here attributed this to the in-flight
  5.1 transaction, but it recurred long after `Complete!` and after a reboot, so that explanation was too
  narrow and the trigger remains unidentified. Practical rules: **retry**, treat a single failed remote
  check as inconclusive rather than as a failed check, and never conclude a hash or state mismatch from
  one attempt — this run produced a false `MISMATCH - do not run` verdict on the staged 5.2 helper that
  a retry immediately disproved.
- **Reverse:** once complete, the pre-upgrade state is not recoverable by a simple rollback — dnf keeps
  no automatic snapshot here.

### C11 — Stage the 5.2 SSH helper and public key

`priv=user`, **agent**, 2026-09-14

- **Command:** `scp` of the **repo-root** `setup-ssh-key-only.sh` and `~/.ssh/id_ed25519_cloudops.pub`
  into `/home/aicowork/`.
- **Effect:** the tested helper (20 277 bytes) and the public key (106 bytes) are staged for the §7
  key-only SSH step. Nothing has been executed — the helper is inert until run, and password
  authentication is still enabled.
- **Verified:** the staged helper's sha256 is
  `32ac4ba34bbff15ecef8869cb32b2e426bd6a9e8ee68b0768bb38e13215ad5dd`, identical to the repo-root copy.
  The stale `scripts/hermes/manual/` copy — the one the guide's 5.2 actually stages — is a different
  file entirely (`eacc931a…`, 17 232 bytes), so the size alone distinguishes them. This staging transfer
  took place inside the intermittent-`ssh` window described in C10, and an initial hash comparison
  failed there; it was re-run afterwards and matched on three consecutive attempts.
- **Reverse:** delete the two files.
- **Note:** because the helper was staged before the SSH hardening step, re-verify this hash immediately
  before running it.

### C12 — Reboot onto kernel 7.2.5 (attended by a console unlock)

`priv=console`, operator, 2026-09-14 ~01:2xZ

- **What happened:** the host was rebooted — a **plain** reboot, not 5.5's hostname+reboot step, since
  the static hostname is still unset. It then sat unreachable until the LUKS passphrase was entered at
  the console. That is exactly the pre-enrollment behaviour gate B4 exists to eliminate: with no TPM
  token, every reboot stops at the prompt, and nothing remote can bring it back.
- **Effect:** `uname -r` moved from `6.19.10-300.fc44` to **`7.2.5-200.fc44`**, and `boot_id` changed from
  `72d8d61b-9bb1-4491-beef-616a2e2e7d15` to `95d9c7ad-8c0d-4264-8635-ccdee6f572d7`. Both kernels remain
  installed.
- **Verified after the reboot:**
  - `failed_units=0` — counted with `systemctl list-units --state=failed --no-legend --plain | wc -l`
  - **PCR7 is byte-identical before and after the kernel switch:**
    `22103EAC50D6EF26DABCBA626A8E70754586CE66D600563A82CEFBF2CA206A73`. This confirms on the real host
    that PCR7 measures the Secure Boot *policy state*, not boot contents — the same conclusion the design
    claims and the reference recorded as a measurement-neutral firmware change. It also means the
    eventual PCR7 binding is stable across kernel upgrades.
  - Secure Boot still `enabled`, TPM nodes `/dev/tpm0` and `/dev/tpmrm0` present, chrony synchronised.
- **Significance:** the enrollment precondition is now **satisfied**. `tpm-enroll.sh`'s `dracut -f`
  derives the initramfs from `uname -r`, so it will now rebuild **7.2.5's** initramfs — the kernel that
  will actually boot. The ordering risk described in C10 is retired even though 5.5's hostname change
  has not been made. 5.5 still needs doing for its own sake.
- **Correction recorded:** an interim note in this ledger reported *"2 failed units"* after the reboot.
  That was a counting error on the agent's part —
  `systemctl --failed --no-pager | tail -n +2 | wc -l` counts *output lines*, including the blank line
  and the `0 loaded units listed.` summary, and so reports 2 when there are none. Counting unit lines
  gives 0. The same sloppy idiom is the subject of findings elsewhere in this run.
- **Reverse:** reboot again — which again requires a console unlock until B3 completes.

### C13 — 5.2 key-only SSH hardening

`priv=root, console`, operator, 2026-09-14 ~01:14Z — **COMPLETE and independently verified**

- **Commands:** the dry run first (`--dry-run`, clean, no refusals), then the same invocation without it,
  at the console with the console session held open, using the **tested repo-root** helper:

  ```bash
  sudo bash ~/setup-ssh-key-only.sh --user aicowork --public-key-file ~/id_ed25519_cloudops.pub --interface eno1 --zone FedoraServer
  ```

- **Helper output:** all four packages already installed (`Nothing to do.`);
  `Warning: ALREADY_ENABLED: 'ssh' already in 'FedoraServer'`;
  `Local configuration validation passed. Remote access remains UNVERIFIED.`
- **Effect:** sshd now offers **`publickey` only** — `password` and `keyboard-interactive` are gone.
  Key authentication for `aicowork` had already been authorised in C6.
- **Verified from a separate workstation session — the two-sided proof:**

  | Test | Command shape | Result |
  | --- | --- | --- |
  | Positive | `-o PasswordAuthentication=no -o KbdInteractiveAuthentication=no -o PreferredAuthentications=publickey -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519_cloudops` | **`KEY_OK`** |
  | Negative (must be refused) | `-o PubkeyAuthentication=no -o PreferredAuthentications=password,keyboard-interactive` | `Permission denied (publickey)`, exit 255, no command ran ✓ |

  Offered methods during the negative test: `publickey` only.

- **Where the change landed — recorded now that root could read it:** the helper installed a drop-in,
  `/etc/ssh/sshd_config.d/00-local-key-only.conf` (mode 0644, 134 bytes, mtime matching the apply).
  `sudo sshd -T` confirms the effective values, and a drop-in makes the hardening reviewable and
  reversible rather than an in-place edit of `sshd_config`. Fedora's own `40-redhat-crypto-policies.conf`
  and `50-redhat.conf` sit alongside it, both mode 0600.
- **Effective sshd configuration, captured on the host** (`sudo sshd -T | grep …` →
  `~/step4-5.2-effective.log`, 134 bytes). All five match the preparation guide §7 intent exactly:

  ```text
  permitrootlogin no
  pubkeyauthentication yes
  passwordauthentication no
  kbdinteractiveauthentication no
  authenticationmethods publickey
  ```

  Note the deliberate absence of `AllowUsers` — the guide calls it an optional extra restriction for a
  single-admin host, and this run did not add it.
- **Consequence for the rest of the run:** password authentication is now off, so a broken sshd
  configuration requires **console access** to recover. The helper's rollback trap and the held-open
  console session are the mitigation, and every remaining SSH step depends on the key pair working.
- **Helper template defect:** its printed verification hint suggests `~/.ssh/id_ed25519_fedora`, a key
  that does not exist on this workstation — the real one is `id_ed25519_cloudops`. Same class as the
  guide's phase 5.2 naming `~/.ssh/id_ed25519.pub`. The hint is a template with `SERVER_IP` in it, but
  the key name is wrong for this environment and would send an operator hunting for a missing file.
- **An earlier false reading, recorded for honesty:** a check taken *while the helper was still running*
  reported that password auth was still offered. That was a mid-run snapshot taken before the helper
  reached the sshd configuration step, not a failure. Re-testing after the process exited showed
  `publickey` only. **Do not evaluate a mutating step until its process has exited.**
- **Reverse:** restore the previous sshd configuration and reload; the helper's error handler attempts
  this itself on failure.

### C14 — 5.3 firewall/Cockpit — COMPLETE (applied in two phases after a timer revert)

`priv=root`, operator, 2026-09-14 ~01:20Z (phase 1) and ~01:35Z (phase 2, recovery)

Two phases, because the first attempt was reverted by the guide's own safety timer. Both are recorded:
the revert is the more instructive half of this change.

**Phase 1 — runtime change, then revert.**

- **Applied:** `firewall-cmd --get-active-zones` showed `FedoraServer` on `eno1`; listeners were sshd 22
  (v4 and v6) and `*:9090` socket-activated by systemd; the timed rollback was armed with
  `systemd-run --unit=hermes-fw-rollback --on-active=5m /usr/bin/firewall-cmd --reload`; and
  `firewall-cmd --remove-service=cockpit` returned `success`.
- **Verified — the required SSH proof:** a forced key-only login succeeded immediately after the runtime
  removal (`SSH_OK`, hostname `hermes.ai.lab.local`). The change is therefore safe to persist.
- **Not applied in time:** `--runtime-to-permanent`, `--check-config`, stopping the timer, and
  `systemctl disable --now cockpit.socket`. `cockpit.socket` remained active and enabled, `*:9090` still
  listened, and `~/step4-5.3-cockpit.log` was never created.
- **Outcome:** the 5-minute timer fired `firewall-cmd --reload` and restored the permanent rules — which
  still permitted cockpit, since nothing had been persisted. **This is the safety mechanism working as
  designed, not a failure.** The end state returned to the pre-5.3 configuration and the change simply
  had to be re-applied.

**Phase 2 — direct-to-permanent recovery.**

- **Commands:** the recovery skips the timer entirely, because the SSH proof from phase 1 already
  satisfied the only thing the timer was protecting:

  ```bash
  sudo systemctl stop hermes-fw-rollback.timer 2>/dev/null
  sudo firewall-cmd --permanent --remove-service=cockpit
  sudo firewall-cmd --reload
  sudo firewall-cmd --check-config
  sudo firewall-cmd --list-services          # dhcpv6-client ssh
  sudo systemctl disable --now cockpit.socket 2>&1 | tee ~/step4-5.3-cockpit.log
  sudo ss -lntp | grep ':9090' || echo "cockpit no longer listening"
  ```

- **Operator-reported output:** three `success` lines (permanent removal, reload, `--check-config`),
  `dhcpv6-client ssh`, `Removed '/etc/systemd/system/sockets.target.wants/cockpit.socket'.`, and
  `cockpit no longer listening`.
- **Verified by the agent over SSH after the block exited:**

  | Check | Result |
  | --- | --- |
  | `cockpit.socket` active / enabled | `inactive` / `disabled` |
  | listeners on `:9090` | **none** — unprivileged `ss -lnt` shows only `22`, `5355`, and the resolver on `53` |
  | `hermes-fw-rollback.timer` | `inactive`, `not-found`; `list-unit-files` returns 0 units |
  | failed units | 0 |
  | `~/step4-5.3-cockpit.log` | created, 67 bytes, containing the unit-removal line |
  | firewalld runtime + permanent service lists | **not agent-verifiable** — polkit refuses `firewall-cmd --list-services` for a non-root login (`Authorization failed`), and `/etc/firewalld/zones/` is mode-0700. Rests on the operator's paste. |

- **Scope note — the cockpit packages stay installed.** The guide asks only to disable the socket and
  remove the `cockpit` service from the active zone; it does not remove software. `cockpit-367-1.fc44`,
  `cockpit-ws`, and `cockpit-bridge` therefore remain installed by design, with no listener and no
  firewall opening. Removal is reversible by re-enabling the socket.
- **Finding — the rollback timer is an undocumented deadline.** The guide's 5.3 pattern ("Make one
  runtime change, open a fresh SSH connection to prove it, then write the same change permanently and
  cancel the timer") reads as an open-ended window, but `--on-active=5m` gives the operator five minutes
  in total. If the proof or the operator's turnaround takes longer, the rollback fires first and the
  change is silently reverted — which is what happened here. The SSH proof itself took seconds; it was
  the operator's turnaround that exceeded the remaining window. A replication run should either keep the
  proof step to seconds or lengthen `--on-active` to cover realistic operator latency.
- **Guidance for replication:** once the SSH proof has passed, write straight to permanent with
  `--permanent --remove-service=cockpit`, `--reload`, `--check-config`, then disable the socket. This
  avoids the timer race entirely and is correct whether or not the timer has already fired.
- **Reverse:** `sudo firewall-cmd --permanent --add-service=cockpit && sudo firewall-cmd --reload &&
  sudo systemctl enable --now cockpit.socket`. The packages were never removed, so this restores the
  prior state exactly.

### C15 — 5.4 bounded journal and download-only update staging

`priv=root`, operator, 2026-09-14 ~01:27Z (host local 20:27) — **COMPLETE and agent-verified**

- **Applied — bounded journal.** Created the drop-in `/etc/systemd/journald.conf.d/60-hermes-host.conf`
  (85 bytes, mode 0644) with the guide's four settings, then `systemctl restart systemd-journald` and
  `journalctl --flush`. The directory did **not** exist beforehand, so the change includes creating it.
  `/var/log/journal` already existed (created at install time), so `Storage=persistent` was already the
  effective behaviour and this setting ratifies rather than changes it; the three size/retention bounds
  are the substantive part of the change.
- **Verified by the agent over SSH:** `systemd-analyze cat-config systemd/journald.conf` shows two
  `[Journal]` blocks — the packaged main file and our drop-in — with `Storage=persistent`,
  `SystemMaxUse=1G`, `SystemKeepFree=2G` and `MaxRetentionSec=14day` applied. `journalctl --disk-usage`
  reported 24M both before and after, consistent with nothing having been evicted yet.
- **Verified — audit:** `systemctl is-active auditd` = `active`;
  `ausearch -m AVC,USER_AVC -ts recent` = `<no matches>`, so SELinux is enforcing without denials at
  this point in the build. The guide's instruction to investigate denials rather than install a generated
  `audit2allow` policy therefore has nothing to act on.
- **Applied — download-only staging.** `/etc/dnf/automatic.conf` **did not exist** despite
  `dnf5-plugin-automatic` being installed, because the RPM declares it as a zero-byte `%ghost`
  placeholder. Created it (120 bytes) with the guide's staging content, then
  `systemctl enable --now dnf5-automatic.timer`.
- **Verified by the agent over SSH:** the override is 120 bytes with the intended content and **zero**
  occurrences of the probe string; `/etc/dnf/dnf5-plugins/` is empty; the timer is `enabled` **and**
  `active`, with the `timers.target.wants` symlink created and the next run at
  `Mon 2026-09-14 06:38:11 -05`. Failed units 0.
- **Finding — the shipped defaults already match the guide's intent.** The distribution file
  `/usr/share/dnf5/dnf5-plugins/automatic.conf` already ships `apply_updates = no`,
  `download_updates = yes`, `upgrade_type = default`, `reboot = never` and `emit_via = stdio`. This step
  therefore **pins** behaviour that was already the default rather than changing it. That is still worth
  doing: an explicit override cannot be silently flipped by a future package update that edits the
  shipped default, which is precisely the class of change that would turn a staging host into an
  auto-patching one.
- **Finding (proven) — which config path is live.** Two `%ghost` paths are declared and both are absent
  on a fresh install: `/etc/dnf/automatic.conf` and `/etc/dnf/dnf5-plugins/automatic.conf`. The plugin
  binary carries the string *"Configuration file location \"{}\" for dnf automatic is deprecated."*
  A three-case probe settled which is which: the deprecation warning appeared **only** in the case where
  `/etc/dnf/dnf5-plugins/automatic.conf` existed, and never when only `/etc/dnf/automatic.conf` existed.
  Therefore **`/etc/dnf/automatic.conf` is the current documented override** — confirming both
  `dnf5-automatic(8)` and the guide — while `/etc/dnf/dnf5-plugins/automatic.conf` is still read but
  deprecated. The risk of a silent no-op from writing the wrong file is closed.
- **Finding — probe methodology, and a warning to future replications.** `emit_via` is **not** a usable
  config-read probe: with no updates available and `emit_no_updates = no`, the tool never emits a report
  and so never evaluates the emitter, which is why all three cases were silent on that signal.
  `upgrade_type = BOGUS_PROBE` likewise produced no error and exit 0. The deprecation warning was the
  only discriminating signal available. A future run should either probe a key the tool is forced to
  evaluate on every invocation, or simply demonstrate that the deprecated path warns and the documented
  one does not.
- **Error, on the agent's side, recorded for the replication.** The first verification block contained a
  **faulty restore**: it copied the pristine file to `/root/automatic.conf.good`, then mutated
  `/etc/dnf/automatic.conf`, then moved the *mutated* file to `/root/automatic.conf.tmp` and "restored"
  from that same mutated file — leaving `emit_via = BOGUS_EMITTER_PROBE` live on the host — and deleted
  the pristine copy. It was caught by the block's own final `cat` and `wc -c` (134 bytes against the
  expected 120). Corrected within the same step by rewriting the file from the known-good content, and
  the final state was independently re-verified at 120 bytes with zero `BOGUS` occurrences. **The
  lesson for the replication: a restore must copy from a snapshot taken before the mutation, and must be
  proven by reading the restored file back, never by trusting the copy command itself.**
- **Reverse:** drop the drop-in and `systemctl restart systemd-journald`; `systemctl disable --now
  dnf5-automatic.timer`; remove `/etc/dnf/automatic.conf`. All three return the host to the fresh-install
  behaviour, since none of the underlying packages were removed.

### C16 — 5.5 static hostname and reboot — COMPLETE, persistence proven

`priv=root`, operator, 2026-09-14 ~01:35Z (name) and ~01:50Z (reboot), host local 20:35 / 20:50

- **Commands:** `sudo hostnamectl set-hostname hermes.ai.lab.local` on the server; on the workstation,
  appended `10.0.30.10  hermes.ai.lab.local hermes` to `/etc/hosts`.
- **Value chosen — and a correction to this ledger.** Row 7 of the remaining-changes table previously read
  "5.5 static hostname (distinct from `hermes.ai.lab.local`)". That was **wrong** and it is corrected: the
  static hostname must *equal* the FQDN. It matches the router's DNS record, the DHCP-derived transient
  name, and `NETWORK_DESIGN.md`; a deliberately different value would put the host's own name out of step
  with its DNS record for no benefit. The value is observable anyway — `hostnamectl --static` was **empty**
  before and populated after, and `/etc/hostname` went from 1 byte to 20 — so no trick is needed to prove
  the change took.
- **Before / after, captured by the agent:**

  | | before | after |
  | --- | --- | --- |
  | `hostnamectl --static` | *(empty)* | `hermes.ai.lab.local` |
  | `hostnamectl --transient` | `hermes.ai.lab.local` | `hermes.ai.lab.local` |
  | `/etc/hostname` | 1 byte | 20 bytes |
  | `hostnamectl` summary | `Static hostname: (unset)` | `Static hostname: hermes.ai.lab.local` |

- **Workstation resolution confirmed:** `getent hosts hermes.ai.lab.local` and `getent hosts hermes` both
  return `10.0.30.10`. This **had** to come from `/etc/hosts` — see the DNS section above, where the
  reserved `.local` TLD is shown to make the name unresolvable through systemd-resolved.
- **End-to-end proof by name:** `ssh aicowork@hermes.ai.lab.local` returned `NAME_OK` with
  `hostname`/`static`/`transient` all reading `hermes.ai.lab.local`.
- **Host-key handling — no trust was assumed.** The operator's first attempt failed with
  `Host key verification failed`, which is the correct refusal: `known_hosts` pinned the key under
  `10.0.30.10` and the connection used a new name. Rather than run `ssh-keyscan`'s trust-on-first-use, the
  three live fingerprints offered under the **name** were compared against those offered under the **IP**
  and against the entries already pinned in `known_hosts`. All three types agreed byte-for-byte —
  ED25519 `SHA256:zKNIkM19QcwfrMnTQ5IjVe4Y52A/mYzfWZ+nk75imuY`, RSA
  `SHA256:WQhldbgtXHDqFhlMmIX+Nw6rzbFq6CqaXtuWoQlc7zw`, ECDSA
  `SHA256:zsM2ziRa1mvBThOAGT1+qqGsYLTHmj4WbUIfN/Paor4` — proving the name resolves to the same host that
  was already trusted. The connection was then verified with `-o HostKeyAlias=10.0.30.10`, which checks the
  name's key against the pinned IP entry. **`known_hosts` was left unmodified**, so this run added no new
  trust anchor. An attempt to append the name to `known_hosts` was blocked by the agent's sandbox
  (read-only mount) and was not needed.
- **Operator note for bare-name SSH:** `ssh aicowork@hermes.ai.lab.local` needs
  `-i ~/.ssh/id_ed25519_cloudops` unless the name is added to the workstation's `~/.ssh/config` `Host`
  pattern, because the default identity filenames do not exist on this workstation. `ssh hermes` already
  works and goes to the IP.
- **PROVEN — the reboot.** The guide is explicit that "only the reboot proves the host boots as intended; the
  written configuration alone does not." The guarded pre-reboot block ran on the server, the operator
  unlocked LUKS at the console with the Phase 3 passphrase, and the agent then verified the result:

  | Check | Pre-reboot | Post-reboot |
  | --- | --- | --- |
  | `boot_id` | `95d9c7ad-8c0d-4264-8635-ccdee6f572d7` | **`2b79a995-dbec-44e8-a337-07de2973b93c`** (changed → a real reboot) |
  | `hostnamectl --static` | `hermes.ai.lab.local` | `hermes.ai.lab.local` (**persisted**) |
  | `/etc/hostname` | 20 bytes | `hermes.ai.lab.local` |
  | kernel | `7.2.5-200.fc44` | `7.2.5-200.fc44` |
  | failed units | 0 | 0 |
  | **PCR7** | `0x22103EAC50D6EF26DABCBA626A8E70754586CE66D600563A82CEFBF2CA206A73` | **identical** |
  | SELinux | Enforcing | `Enforcing (1)` |
  | listeners | 22, 5355, 53 | 22, 5355, 53 (**no `:9090`**) |
  | `cockpit.socket` | inactive / disabled | inactive / disabled (**5.3 persisted**) |
  | `dnf5-automatic.timer` | enabled / active | enabled / active (**5.4 persisted**) |

  The LUKS prompt appeared at the console as predicted — B3 enrollment has not happened, so nothing could
  unlock the volume unattended. That is the expected behaviour at this stage and the reason 5.5 needs
  console access.
- **All mounts returned correctly:** `/dev/mapper/fedora_hermes-root` on `/` (xfs),
  `fedora_hermes-var` on `/var`, `fedora_hermes-swap` as swap, and `fedora_hermes-hermes` on
  `/home/hermes` — which `mountpoint -q` confirms is a mount point, empty (0 entries), labelled
  `user_home_dir_t`. Free space: `/` 57G, `/var` 39G, `/boot` 1.4G.
- **SSH posture survived the reboot, tested both ways:** key auth returned `KEY_OK`; password and
  keyboard-interactive were refused with `Permission denied (publickey)` and the server advertised
  `Authentications that can continue: publickey`. The C13 hardening is persistent.
- **Instrument note — PCR7 is readable without root.** `tpm2_pcrread sha256:7` fails as `aicowork`
  (`/dev/tpm0` and `/dev/tpmrm0` are mode 0600), but `/sys/class/tpm/tpm0/pcr-sha256/7` is mode **444**, so
  the agent can verify the measurement directly. Use the sysfs path for verification and reserve
  `tpm2_pcrread` for confirmation at the console.
- **Instrument note — a fourth machine discriminator.** The two machines have different PCR7 values:
  the server reads `22103EAC…` and the workstation `EF99FE48…`. This is a hardware/firmware identity, so it
  separates the machines even more reliably than the hostname. **The agent got this wrong once in this
  very step**: it read `/sys/class/tpm/tpm0/pcr-sha256/7` in its own (workstation) shell and briefly
  compared the workstation's value against the server's pre-reboot value, which looked like a PCR7 change
  across the reboot. The value only matched once the read was performed over ssh on the server. Recorded
  because it is the same wrong-machine failure mode as the operator incidents, committed by the agent.
- **Reverse:** `sudo hostnamectl set-hostname ''` (or any other value) and remove the workstation
  `/etc/hosts` line; reboot to observe.

### C17 — 5.6 the runtime account `hermes`

`priv=root`, operator, 2026-09-14 ~01:57Z (host local 20:57) — **COMPLETE and agent-verified**

- **Precheck order followed as the guide requires — the mount was verified before anything was created.**
  `findmnt --mountpoint /home/hermes` returned `/dev/mapper/fedora_hermes-hermes` on xfs
  (`rw,relatime,seclabel,inode64,logbufs=8,logbsize=32k,noquota`), and `getent passwd hermes` was empty, so
  the account did not exist and was created.
- **Command — exactly the guide's form, deliberately without `-u`:** `useradd --user-group
  --no-create-home --home-dir /home/hermes --shell /usr/sbin/nologin hermes`, then `passwd --lock hermes`,
  `chown hermes:hermes /home/hermes`, `chmod 0700 /home/hermes`, `restorecon -v /home/hermes`.
  `restorecon` printed nothing, i.e. the label already matched — consistent with the directory having been
  created correctly at install time.
- **Account facts, verified by the agent over ssh:**

  | Property | Value |
  | --- | --- |
  | UID / GID | **1001 / 1001** (a regular account, not a system UID — the guide's explicit requirement) |
  | passwd entry | `hermes:x:1001:1001::/home/hermes:/usr/sbin/nologin` |
  | shell | `/usr/sbin/nologin` — non-login |
  | groups | `hermes` only — no supplementary or privileged group |
  | `/home/hermes` | mode **0700**, owner `hermes:hermes`, label `user_home_dir_t` |
  | still a mountpoint | **YES** (the dedicated XFS filesystem is intact under the new ownership) |
  | subordinate IDs | `/etc/subuid` and `/etc/subgid` both `hermes:589824:65536` — **exactly 65,536** each, meeting the guide's minimum |
  | `newuidmap` / `newgidmap` | present (`/usr/bin/`, from shadow-utils) |
  | failed units | 0 |

- **Two properties rest on the operator's output because they cannot be read unprivileged:** the password
  lock state (`sudo passwd -S hermes` → `hermes L`, where `L` is locked) and the sudo-rights check
  (`sudo -l -U hermes` → `User hermes is not allowed to run sudo on hermes.`). `/etc/shadow` and `sudo -l`
  both need root, and the agent has none. Both outputs are consistent with the intent, but they are
  **operator-reported, not independently re-verified** — flagged rather than overstated.
- **Honest limitation on the "empty directory" check:** the post-reboot verification read `/home/hermes` as
  empty while it was still mode 0755. After 5.6 it is mode 0700, so the agent can no longer list it and the
  emptiness is no longer independently re-checkable. Nothing wrote to the directory between the two reads,
  so the earlier observation stands, but the check is now operator-side only.
- **Note on the chosen range:** 589824:65536 is a clean, non-overlapping allocation and exactly meets the
  minimum; this run records it as the actual value rather than prescribing it, since the guide says a fixed
  UID is not required.
- **Reverse:** `sudo userdel hermes` and `sudo chown root:root /home/hermes && sudo chmod 0755
  /home/hermes`; remove the `hermes:` lines from `/etc/subuid` and `/etc/subgid`. Nothing in
  `/home/hermes` existed before this step.

### C18 — 5.7 directories, user-manager guard, linger, rootless Podman

`priv=root`, operator, 2026-09-14 ~01:55Z (host local 20:55) — **COMPLETE**

- **Directories created** with `install -d -o hermes -g hermes -m 0700`: `.config`, `.local`,
  `.cache/podman-tmp`, `gateway-state`, `workspace`, `worker-state`, `transport`. `restorecon -Rv
  /home/hermes` printed nothing, so no relabelling was required.
- **User-manager guard installed** at
  `/etc/systemd/system/user@1001.service.d/20-hermes-data.conf` with `RequiresMountsFor=/home/hermes` and
  `AssertPathIsMountPoint=/home/hermes`, then `daemon-reload`. **The drop-in is definitely loaded** —
  `systemctl show user@1001.service -p DropInPaths` lists it explicitly, and `RequiresMountsFor` is echoed
  back, which can only have come from it.
- **A false alarm, investigated and resolved.** `systemctl show -p AssertPathIsMountPoint` returns
  **empty**, which looks like systemd silently ignoring the guard — the same class as the known defect
  where `fallback-wipe.sh` prints `crypttab_unchanged` without enforcing it. It is not a defect. This run
  proved it by comparison against a shipped unit: `lastlog2-import.service` genuinely contains
  `ConditionPathExists=` lines, and `systemctl show -p ConditionPathExists` returns **empty for it too**.
  This systemd exposes only the aggregate `ConditionResult`/`AssertResult` and their timestamps, not the
  individual path-based directives, so their absence is expected reporting behaviour. Corroborating:
  `AssertPathIsMountPoint=` is documented in the installed `systemd.unit(5)`, `systemd-analyze verify
  user@1001.service` is clean, no "unknown key" entry appears in the journal, and the unit reports
  `AssertResult=yes` with an `AssertTimestamp`.
- **Linger and the persistent user manager:** `loginctl show-user hermes` reports `Linger=yes`,
  `State=lingering`, `RuntimePath=/run/user/1001`; `user@1001.service` is `active` and `static`; `/run/user/1001`
  exists (mode 0700, `hermes:hermes`).
- **Rootless Podman — the guide's `h()` wrapper, output exactly as required:**

  ```text
  rootless=true cgroups=v2 manager=systemd driver=overlay graphroot=/home/hermes/.local/share/containers/storage
           0       1001          1
           1     589824      65536
  ```

  `rootless=true`, cgroups **v2**, **systemd** cgroup manager, and the graphroot on the **dedicated XFS
  volume** rather than the root filesystem — which is the property that matters, and the reason this check
  was worth doing before any image is pulled. The `uid_map` is the correct rootless mapping: container
  root (0) → the `hermes` UID, and 65,536 subordinate IDs mapped from 589824.
- **Guide prohibitions verified:** `podman.socket` is `disabled`/`inactive` at the system level and
  `disabled` at the user level, so no Podman API socket exists to be mounted into a container.
- **Verification boundary, stated plainly:** `/home/hermes` is mode 0700 and owned by `hermes`, so the
  agent is refused traversal. The seven subdirectories, the graphroot, and the `h()` output are therefore
  **operator-reported only** and cannot be independently re-verified from an unprivileged session. The
  agent independently confirmed everything outside that boundary: the drop-in's presence and effect,
  linger state, user-manager activity, the disabled socket, and 0 failed units. This is the same
  structural gap recorded in the evidence record's `verification_layer_gap`.
- **5.8 (optional resource budgets) was not applied.** The guide labels it optional and sizes it from
  measured RAM; `m04-posture.sh` applies and verifies it in Phase 6. Deferred deliberately, with the
  guide's warning noted: the previous values must be recorded and tested before limits become part of
  acceptance, and hard limits are emergency containment because exceeding them terminates processes.
- **Reverse:** remove the drop-in and `daemon-reload`; `loginctl disable-linger hermes`; `systemctl stop
  user@1001.service`; remove the created directories. Nothing in `/home/hermes` predates this run.

### C19 — B1 firmware power-loss behaviour, and the reboot that verifies it

`priv=console` (firmware) + `root` (reboot), operator, 2026-09-14 ~01:59Z (host local 20:59)

- **What changed:** the firmware's power-loss / AC-back behaviour was set to **power on** at the server
  console. **The option's exact name and its prior value are still outstanding** — the runbook Step 2
  explicitly requires recording both, and neither is reconstructible from the OS afterwards.
- **A false completion, caught by the agent.** The operator first reported the setting as configured, but
  the host had **not rebooted**: `boot_id` was still `2b79a995-…` with 7 minutes of uptime, and the
  workstation's `boot_id` was likewise unchanged. Since `boot_id` is regenerated by the kernel on every
  boot, an unchanged value proves no restart occurred, and a firmware setting cannot take effect without
  one. The agent therefore declined to record B1 as done and reported the discrepancy; the operator then
  rebooted, and the setting is now carried by a real boot. **This is the check worth repeating in a
  replication: verify the reboot rather than the claim.**
- **Reboot evidence — the runbook's third requirement:**

  | Check | Before | After |
  | --- | --- | --- |
  | `boot_id` | `2b79a995-dbec-44e8-a337-07de2973b93c` | **`115453bc-6f3c-40e0-8c64-0650c30bff1d`** |
  | Secure Boot | enabled (user) | **enabled**, `SetupMode = 0` (keys still enrolled, not Setup Mode) |
  | **PCR7** | `0x22103EAC…206A73` | **byte-identical** |
  | kernel | `7.2.5-200.fc44` | `7.2.5-200.fc44` |
  | failed units | 0 | 0 |
  | TPM nodes | present | `/dev/tpm0`, `/dev/tpmrm0` both present |
  | static hostname | `hermes.ai.lab.local` | persisted |
  | listeners | 22/5355/53 | unchanged (no unexpected listener) |

- **Finding — the AC-back setting is measurement-neutral, on this host too.** PCR7 did not move. This is
  now the **third** event across which PCR7 has been byte-identical: the install baseline, the 5.1 kernel
  upgrade reboot, the 5.5 hostname reboot, and now the firmware-change reboot. It corroborates the
  reference host's result and means the eventual PCR7 binding targets the same value as the reference.
- **Verification boundary — the firmware setting itself is NOT agent-verifiable.** There is no
  OS-visible interface for AC-power-loss behaviour, and the firmware's PK/KEK/db state cannot be read from
  the running system to prove nothing else was altered while in setup. The only OS-observable
  consequences are the new boot and the unchanged PCR7. **The real proof of this setting is gate B5**
  (orderly shutdown, pull AC at the wall, confirm the machine powers itself on), which is by design. B1
  therefore passes on the evidence available, with the firmware write itself taken on the operator's
  report.
- **Deviation:** this run executed the runbook's Steps 3–5 before Step 2; see deviations item 7. The
  binding constraint — firmware before enrollment — is preserved, as B3 has not started.
- **Reverse:** re-enter firmware setup and restore the prior AC-back value (which is why recording it
  matters), then reboot.

### C20 — DEFECT FOUND AND FIXED: LUKS discovery was broken on util-linux 2.41.5

`priv=none` (repo edit by the agent), 2026-09-14 ~02:03Z — **blocks B3, B4 and B5 until fixed**

**This is the single most valuable finding of gate B6 so far: a defect that offline rehearsal passed
clean, that a real Fedora 44 install hit immediately, and that would have made the entire boot-automation
track impossible to complete.**

- **Symptom.** `tpm-enroll.sh --preflight` failed closed with
  `STOP: cannot identify a LUKS2 device behind / (is the root encrypted?)` on a host whose root was
  demonstrably LUKS2-backed (`/dev/nvme0n1p3` → `luks-8919c2b1-…` → `fedora_hermes-root` on `/`).
- **TWO independent version-dependent breaks, both found on the real host.** The first was visible
  immediately from the preflight failure. The second was found only because the agent re-tested the parse
  on the host *after* applying the first fix and noticed `parent` was still empty — **fixing the first
  break alone was not enough**, and a less careful run would have re-staged and failed again.
- **Break 1 — tree glyphs in `NAME`.** `lsblk` from **util-linux 2.41.5** draws the inverse dependency
  tree with **box-drawing glyphs in the NAME column, even when piped and even with `-n`**:

  ```text
  fedora_hermes-root                          lvm
  └─luks-8919c2b1-5d9a-4fb9-8f85-97d286cbe7ec crypt
    └─nvme0n1p3                               part
      └─nvme0n1 disk
  ```

  The original parse `awk '$2 == "crypt" { print $1; exit }'` returned `└─luks-8919c2b1-…`, so the follow-up
  lookup on `/dev/mapper/└─luks-…` failed with *not a block device*.
- **Break 2 — `PKNAME` of a crypt device is empty on its first line.** Even with the glyphs removed,
  `lsblk -no PKNAME "/dev/mapper/$mapper" | head -n1` still returned the **empty string**. Reproduced
  directly: that command prints the crypt device's **own** PKNAME first — blank, because its parent sits
  above it and is not part of the default forward listing — and then the PKNAMEs of its LVM children
  (`dm-0` four times, once per LV). `head -n1` therefore selects the blank line, `parent` is empty,
  discovery returns non-zero, and the caller reports the misleading *"is the root encrypted?"* on a host
  whose root was perfectly well encrypted.
- **Final fix — one call, no `PKNAME`.** `lib-luks-identity.sh` now resolves the mapper **and** its backing
  device from a single raw inverse listing: the entry of type `crypt` is the mapper, and the next line up
  the chain is the device that holds it.

  ```bash
  read -r mapper dev_name <<<"$(lsblk --raw -no NAME,TYPE -s "$root_src" 2>/dev/null \
    | awk '$2 == "crypt" { printf "%s ", $1; getline; print $1; exit }')"
  ```

  `--raw` suppresses alignment and tree formatting; taking the next chain entry avoids `PKNAME` and both of
  its version-dependent behaviours. `dev_name` is still validated as an existing block device downstream by
  `hermes_resolve_luks_identity`. New sha256
  `0bcaca9bc66a52e72b7b47be241766423aed63187e43b9dcdbce74f5e171aae6` (was `629c6092…`).
  **Verified on the real host, unprivileged:** mapper `luks-8919c2b1-5d9a-4fb9-8f85-97d286cbe7ec` and
  device `/dev/nvme0n1p3`, both matching the Phase 3 record, with `/dev/nvme0n1p3` confirmed a block device.
- **A second defect found while fixing the first — the rehearsal was blind to both.**
  `rehearse-clean-install.sh`'s `lsblk` stub printed **clean, glyph-free output unconditionally** and
  returned a **helpful** `nvme0n1p3` for `PKNAME`, so `REHEARSAL=PASS` proved nothing about either real
  behaviour. The stub is now faithful in both respects: it emits the box-drawing tree unless `--raw`/`-r`
  is passed, and its `PKNAME` branch returns a leading blank line followed by `dm-0` children exactly as the
  real tool does. New sha256 `3e21dafe3804f2bc15cdc7024bf661c17689a560c92777c5e98e9414b399d11b`
  (was `271c86a6…`).
- **Proven three ways, not asserted:**

  | Code under test | Rehearsal result |
  | --- | --- |
  | original (`lsblk -no …` + `PKNAME`), faithful stub | **`FAIL`**, `failures=4` — `DEV`, `MAPPER`, `ROOT_LV`, `UUID` all empty |
  | glyphs fixed, `PKNAME` call reintroduced | **`FAIL`**, `failures=4` — proves the stub catches break 2 specifically |
  | final fix (`--raw` + positional chain) | **`PASS`**, `failures=0 advisories=0` |

  Each regression run temporarily reverted only the relevant fragment in place and restored from a copy,
  with the restore confirmed by sha256 equality.
- **CORRECTION to this run's own earlier evidence.** The baseline recorded
  `resolver_cross_check: "PASS - the discovery risk carried since round 3 is retired"`. **That was a false
  pass.** It captured the *content* of the `lsblk -s` chain correctly but never reproduced the *exact byte
  output* including glyphs, so it validated the chain rather than the parse. It is corrected to FAIL in the
  evidence record. The lesson generalises: verifying that a tool's output contains the expected data is not
  the same as verifying that the parser handles the output the tool actually emits.
- **Why this matters for the guideline.** This is the failure mode a clean-install validation exists to
  catch, and it is invisible to an offline rehearsal that stubs the tools it is supposed to be testing.
  Any rehearsal that stubs `lsblk`, `cryptsetup` or `dracut` must stub them **faithfully**, including
  version-specific formatting, or it manufactures confidence rather than measuring it.
- **Remaining action:** re-stage the fixed `boot/` directory to the host and re-run the preflight. The
  staged copy on the host is still the broken `629c6092…` revision.

### C21 — B3 TPM2 enrollment, PCR7 sha256, no PIN

`priv=root` (operator), 2026-09-14 ~02:08Z (host local 21:08) — **COMPLETE, and independently verified**

- **Preflight first, as the runbook requires:** `sudo HERMES_EXPECT_UUID=8919c2b1-… bash
  ~/hermes-boot/tpm-enroll.sh --preflight` → **`PREFLIGHT=OK (no changes made)`**, with
  `device=/dev/nvme0n1p3`, `mapper=luks-8919c2b1-5d9a-4fb9-8f85-97d286cbe7ec`,
  `root_lv=/dev/mapper/fedora_hermes-root`, `luks_uuid=8919c2b1-…` (pin matched), `keyslots=1
  tpm2_tokens=0`, `matching_records=1`.
- **Pre-change state was byte-identical to the Phase 3 record — no drift in the interval.**
  `/etc/crypttab` hashed `f4b732ad…` and the helper's fresh pre-change header backup hashed `8b4ca688…`,
  both exactly the values captured in Phase 3. This is a useful integrity check: nothing had quietly
  modified the crypttab or the LUKS header between taking the recovery material and using it.
- **Enrollment:** `sudo HERMES_EXPECT_UUID=8919c2b1-… bash ~/hermes-boot/tpm-enroll.sh`, which runs
  `systemd-cryptenroll --tpm2-device=auto --tpm2-pcrs=7:sha256 --tpm2-with-pin=no`. Output:
  `New TPM2 token enrolled as key slot 1.` and `enroll_rc=0`.
- **The values that matter, each independently confirmed by the agent reading
  `/home/aicowork/hermes-tpm-enroll.out`** — not taken from the console paste:

  | Value | Result | Meaning |
  | --- | --- | --- |
  | `enroll_rc` | **0** | the token was created |
  | `keyslots_after` | **2** | slot 0 passphrase **retained**, slot 1 TPM2 added |
  | `tpm2_tokens_after` | **1** | exactly one `systemd-tpm2` token |
  | `passphrase_slot` | **OK** | break-glass credential still opens the volume |
  | `lines_before` / `lines_after` | **1 / 1** | crypttab rewritten in place, not restructured |
  | `dracut_rc` | **0** | initramfs regenerated successfully |
  | `tpm2_and_cryptsetup_lines` | **18** | the initramfs really does carry the TPM unlock path |
  | `ENROLL=done` | present | |

  **Why reading the log mattered:** the recorded defect says `tpm-enroll.sh:205-210` prints `dracut_rc`
  and the line count but **asserts neither**, so `ENROLL=done` would be reported even after a failed
  `dracut`. Because the helper writes its full output to a file owned by `aicowork`, the agent could read
  those two un-asserted values directly instead of trusting a paste. **The two most safety-critical values
  in B3 were therefore verified rather than reported.** This is a materially better verification position
  than the defect implies, and it is worth preserving in the replication.
- **crypttab edit, scoped correctly:** the single matching record gained `,tpm2-device=auto` —
  `luks-8919c2b1-… UUID=8919c2b1-… none discard,x-initrd.attach,tpm2-device=auto` — and the line count was
  unchanged. The helper's own guard (`[ "$lines_before" -eq "$lines_after" ]`) is one of the checks it
  *does* enforce.
- **Nothing else moved:** `boot_id` still `115453bc-…` (no reboot yet), PCR7 still `0x22103EAC…`, static
  hostname intact, 0 failed units. Enrollment does not alter Secure Boot policy state, so PCR7 holding is
  expected — but it is checked, not assumed.
- **Recovery material pulled off-host and hash-verified (runbook 6.3):**

  | File | sha256 | Check |
  | --- | --- | --- |
  | `nvme0n1p3-tpm-20260914T020803Z.header` | `6603c7ad620358d047747b9ca9462cc6fe4b1c26ad9fba189a376f3ac84a053a` | matches host |
  | `crypttab-pre-tpm-20260914T020803Z` | `f4b732ad0f9149139bae466a016e55287aa136c780e56cebe33ad9fe75dba43c` | matches host, and identical to the Phase 3 copy |

  Both now sit in the gitignored `private/hermes-boot-recovery-8919c2b1/`, alongside the Phase 3 pre-TPM
  header (`8b4ca688…`). **Both header states — pre-TPM and post-TPM — are therefore off-host**, which is
  what matters before a reboot changes the boot path. The staging directory on the host was then deleted
  per 6.3, after the copies were verified; the `/root/recovery` originals remain as the local copy.
  `fallback-wipe.sh` was checked first and has no dependency on the staging directory, so removing it
  cannot affect B4.
- **Locale detail worth recording:** under the helper's `LC_ALL=C`, `lsblk` draws the tree with **ASCII**
  `` `- `` characters rather than the Unicode `└─` seen in a UTF-8 shell. **Both forms break a naive field
  parse**, so the C20 fix (`--raw`) is what actually matters; the glyph *characters* differ but the defect
  does not.
- **Reverse:** `sudo bash ~/hermes-boot/tpm-enroll.sh --revert` wipes the TPM2 keyslot and restores the
  most recent crypttab backup, then regenerates the initramfs. The passphrase slot was never removed, so
  the volume is recoverable at every point.

### C22 — B4 part 1: unattended boot — PASS

`priv=root` (reboot) + `console` (observation), operator, 2026-09-14 ~02:10Z (host local 21:10)

- **The gate:** reboot and confirm the machine reaches a login prompt with **no passphrase prompt and no
  keyboard input**. Operator reported the server came back; the agent then verified it from evidence rather
  than accepting the screen report.
- **Boot evidence:**

  | Check | Result |
  | --- | --- |
  | `boot_id` | `115453bc-…` → **`c8c25e62-e978-449d-abff-f2b8cdecece0`** |
  | kernel | `7.2.5-200.fc44` |
  | Secure Boot | **enabled** |
  | **PCR7** | **`0x22103EAC…` unchanged** (fifth boot across which it has not moved) |
  | failed units | 0 |
  | static hostname | `hermes.ai.lab.local` |
  | Hermes unit files installed | **0** — correct for this stage, as runbook step 7.2 requires |

- **The decisive evidence, from the journal rather than the console:**

  ```text
  Reached target tpm2.target - Trusted Platform Module
  Starting systemd-cryptsetup@luks\x2d8919c2b1\x2d…service - Cryptography Setup for luks-8919c2b1-…
  Finished systemd-cryptsetup@luks\x2d8919c2b1\x2d…service - Cryptography Setup for luks-8919c2b1-…
  Reached target cryptsetup.target - Local Encrypted Volumes
  ```

  The unit is `loaded active exited`, it started at 21:10:49 and **finished at 21:10:50 — about one
  second**, and `tpm2.target` was reached immediately before it. A search of the whole boot log for
  `please enter passphrase` / `enter passphrase for` / `timed out waiting for … passphrase` returns
  **nothing**.
- **Why this is proof and not merely consistent with success.** The crypttab record's key field is
  **`none`** — there is no keyfile fallback — and its only option of interest is `tpm2-device=auto`. The
  volume can therefore be unlocked in exactly two ways: the TPM2 token, or an interactive passphrase
  prompt. **No prompt occurred, so the TPM2 token unsealed.** That is a deduction from the configuration
  plus the absence of a prompt, not an inference from a screen the agent could not see. The unlock is also
  correctly placed: systemd starts twice in the log (the initramfs instance at 21:10:48 and the host
  instance at 21:10:57), and the cryptsetup unit belongs to the **first**, initramfs instance — which is
  where it must run for this to work without a human.
- **Runbook step 7.2 also satisfied:** both Hermes units are *not yet installed* (0 unit files) and there
  are no failed units, exactly as expected before Phase 9.
- **Not yet done — runbook step 7.3, the fallback proof.** `fallback-wipe.sh` must remove the TPM token
  while deliberately leaving the crypttab requesting TPM unlock, after which the next boot **must** prompt
  for the passphrase. That is the difference between a proven and an assumed recovery path.
- **Reverse:** none needed; this step only rebooted.

### C23 — B4 part 2: the fallback proof — PASS

`priv=root` (wipe/reboot) + `console` (passphrase entry), operator, 2026-09-14 ~02:13Z (host local 21:13)

This is the half of B4 that separates a **proven** recovery path from an **assumed** one, and both the
runbook and the helper are explicit that it must be done the honest way: wipe **only** the TPM token and
leave the crypttab still requesting TPM unlock, so the initramfs is forced to fall back.

- **Wipe — `fallback-wipe.sh`, verified from `~/hermes-fallback-wipe.out`:**

  | Value | Before | After |
  | --- | --- | --- |
  | `keyslots` | 2 | **1** (passphrase retained) |
  | `tpm2_tokens` | 1 | **0** (token gone) |
  | crypttab sha256 | `f9a08169…` | `f9a08169…` — **unchanged** |
  | crypttab record | …`,tpm2-device=auto` | **still `,tpm2-device=auto`** |
  | `passphrase_slot` | — | **OK** |
  | `wipe_rc` | — | 0 |

  **The crypttab record and both hashes were read out of the helper's log**, which is what makes the
  un-enforced `crypttab_unchanged` check verifiable anyway: the recorded defect is that line 85 only
  *prints* that value without asserting it, so a silently reverted crypttab would still yield `WIPE=done`
  and a meaningless "proof". The log let the agent confirm independently that crypttab **still asked for
  TPM**, which is the precondition that makes the reboot a real test.
- **Crypttab hash chain — a clean, checkable sequence:**

  | Stage | sha256 |
  | --- | --- |
  | Phase 3, pre-enrollment | `f4b732ad0f9149139bae466a016e55287aa136c780e56cebe33ad9fe75dba43c` |
  | after B3 enrollment (gained `tpm2-device=auto`) | `f9a0816951716f5026ff3552ae78942765a0f3ee0ea4b8c831a8ceaf56d68710` |
  | after the wipe | `f9a08169…` — **identical** |

- **The reboot — the passphrase prompt appeared only when it should have.** The contrast with the
  unattended boot is the evidence:

  | Observation | B4.1 (TPM) | B4.2 (fallback) |
  | --- | --- | --- |
  | `boot_id` | `c8c25e62-…` | **`878d6f19-4f24-48e2-b9a1-2197072db28d`** |
  | cryptsetup unit running time | 21:10:49 → 21:10:50 (**~1 s**) | 21:14:39 → 21:14:56 (**~17 s**) |
  | `systemd-ask-password-plymouth.service` | never activated | **Started 21:14:39, Deactivated 21:14:59** |
  | `Set cipher…` log lines | once | **twice** (21:14:39 and 21:14:54) |
  | PCR7 | `0x22103EAC…` | **unchanged** |
  | Secure Boot / failed units | enabled / 0 | enabled / 0 |

  The activation of the interactive ask-password service between 21:14:39 and 21:14:59 **is** the prompt
  being serviced, and the ~17-second unlock matches human typing time; neither appears in the TPM boot.
  The duplicated `Set cipher` line is consistent with an initial attempt that did not complete followed by
  the successful passphrase unlock. The timing is the independent confirmation: a ~1 s unlock here would
  have meant the fallback was never genuinely exercised, whatever the screen showed.
- **What this proves:** with the token absent but crypttab still demanding TPM, the initramfs **falls back
  to the console passphrase prompt and the passphrase unlocks the volume**. The break-glass path works.
- **Reverse / next:** re-enroll with `tpm-enroll.sh` to restore the TPM path. Until that is done the host
  cannot boot unattended, so it must not be power-cycled in the interim.

### C24 — B4 part 3: re-enrollment restores the TPM path

`priv=root` (operator), 2026-09-14 ~02:17Z (host local 21:17) — **COMPLETE and verified**

- **Re-enrolled** with the same pinned command. Verified from `~/hermes-tpm-enroll.out`: `enroll_rc=0`,
  `keyslots_after=2`, `tpm2_tokens_after=1`, `passphrase_slot=OK`, `lines_before=1 lines_after=1`,
  **`dracut_rc=0`**, **`tpm2_and_cryptsetup_lines=18`**, `ENROLL=done`. The TPM path is restored.
- **crypttab idempotency confirmed in practice.** The helper printed
  `note: tpm2-device=auto already present in crypttab` and left the file byte-identical — its awk matches
  the existing option and simply re-emits the line, so re-running enrollment does not duplicate the option.
  The `lines_before == lines_after` assertion held again.
- **Two incorrect passphrase attempts were rejected before the correct one.**
  `systemd-cryptenroll` reported `Password not correct, please try again` twice and then succeeded. This was
  operator typing, not a fault, and it is mildly useful evidence in its own right: **the passphrase slot
  actually enforces correctness** rather than accepting anything. No lockout occurred (LUKS2 has no
  attempt limit by default), so a break-glass attempt cannot brick the volume through repetition. The
  passphrase itself is not recorded, and its length is deliberately not noted.
- **Recovery material — four distinct header states now exist and all the important ones are off-host:**

  | State | sha256 | Location |
  | --- | --- | --- |
  | original pre-TPM (Phase 3) | `8b4ca688…` | off-host |
  | post-B3 enrollment | `6603c7ad…` | off-host |
  | post-wipe / pre-re-enrollment | `6f51b5d6…` | `/root/recovery` only (transient state) |
  | **post-re-enrollment (current)** | `9debd27b…` | **off-host** |

  The two new staged files were pulled and hash-verified against the host's values, then the host staging
  directory was deleted per 6.3. The states that matter for recovery — the original pre-TPM header and the
  **current** header — are both off-host.
- **Finding — the helper stages fewer artefacts than the runbook describes.** Runbook 6.3 says to move the
  "pre/post header backups and the crypttab backup" off-host, but `tpm-enroll.sh` stages only the
  **post**-change header plus the crypttab backup; the pre-change header is left in `/root/recovery` and is
  never staged. The net requirement was still met here because Phase 3 had already placed the pre-TPM
  header off-host, and because the pre-change header of a *re*-enrollment is a transient state of little
  value. A replication should not rely on the helper alone for the "pre" half of that sentence. Recorded as
  a documentation/helper mismatch rather than a blocker, since the runbook's Phase 3 step independently
  guarantees the recovery-critical copy.
- **Reverse:** `tpm-enroll.sh --revert` wipes the token and restores a crypttab backup.

### C25 — B5 power restoration — PASS, and the real proof of the B1 firmware setting

`priv=console`, operator, 2026-09-14 ~02:19Z (host local 21:19) — **COMPLETE**

- **Procedure:** orderly shutdown (`systemctl poweroff`), AC pulled **at the wall** (not the power button),
  left unpowered ~30 s, AC restored. **The server powered itself on with no human input** — the operator's
  direct observation, and the one fact in this entire run that no OS-side evidence could establish.
- **Why this is the only real proof of B1.** There is no OS interface that exposes AC-back behaviour, so
  B1 could only ever be "the setting was written and nothing contradicted it". B5 is the behavioural test:
  the machine started itself from a genuine power-off. **C19 and C25 together are what make the firmware
  change evidenced rather than asserted.**
- **The shutdown was orderly, which B5 requires.** The previous boot's log ends with a normal SIGTERM
  shutdown at 21:19:53 — `NetworkManager: caught SIGTERM, shutting down normally;` `crond: (CRON) INFO
  (Shutting down);` `ModemManager: caught signal, shutting down…` — so the filesystems went down cleanly
  before power was removed. This was not a power-cut test of the filesystem; it was a power-cut test of the
  boot path.
- **Cold boot evidence — the machine unlocked itself, exactly as it had on the warm reboot:**

  | Check | Result |
  | --- | --- |
  | `boot_id` | `878d6f19-…` → **`4e97672b-b62b-4259-bc17-79ec7d2db0e1`** |
  | cryptsetup unit | 21:20:22 → **21:20:23 (~1 s)** — TPM unseal, same signature as B4.1 |
  | **`passphrase` occurrences in the boot log** | **0** |
  | `systemd-ask-password-*.service` | never activated (only the always-started `.path` watch) |
  | PCR7 | **`0x22103EAC…` unchanged** — sixth boot without movement |
  | Secure Boot | enabled (`SecureBoot` efivar = 1) |
  | SELinux | **Enforcing** (`/sys/fs/selinux/enforce` = 1) |
  | failed units | 0 |
  | all four mounts | `/` xfs, `/var` xfs, `/boot` ext4, `/home/hermes` xfs — all present, `/home/hermes` confirmed a mountpoint |
  | listeners | 22, 5355, resolver 53 — **no `:9090`** |
  | Hermes unit files | 0 — still correct before Phase 9 |

- **Timings recorded (runbook B5 asks for them):** `systemd-analyze` reports
  `6.443s (firmware) + 8.747s (loader) + 944ms (kernel) + 8.547s (initrd) + 13.061s (userspace) = 37.745s`,
  with `multi-user.target reached after 13.036s in userspace`. The 8.5 s initrd stage is where the TPM
  unseal happens. The operator's wall-clock figures were not captured separately; these are the
  system-measured breakdown.
- **Runbook acceptance mapping at this point:**

  | # | Acceptance test | Status |
  | --- | --- | --- |
  | 1 | No passphrase prompt on any boot, warm or cold | **PASS** — B4.1 warm, B5 cold, both 0 prompt occurrences |
  | 2 | Wall-power cycle → powers on, unlocks, both containers autostart, Telegram replies | **2 of 4** — powers on and unlocks proven here; containers and Telegram depend on Phase 9 (M02–M05), which has not run |
  | 3 | Passphrase still unlocks at the console when the TPM token is absent | **PASS** — proven explicitly in C23, not assumed |
  | 4 | Secure Boot remains enabled and SELinux enforcing throughout | **PASS** — checked at every gate, most recently above |

- **Outstanding, non-blocking:** the **B1 firmware option name and prior value** are still unrecorded.
  B5 has now proven the setting *works*, so this is no longer a technical risk, but it remains the one hole
  in the written record and the thing a replication would need in order to find the same menu entry.
- **Reverse:** none needed.

### C26 — M02 step 1: deploy and validate — PASS on every criterion

`priv=root` (operator), 2026-09-14 ~02:26Z (host local 21:26)

- **Bundle sanity:** all 11 declared artefacts `ok` (`worker/*`, `gateway/*`, `quadlets/*`), so the staged
  bundle is complete — and because it was staged fresh from the repo in this run, every deployed file is
  byte-identical to the repo (verified before the run; see the bundle-vs-repo table).
- **Keys.** Worker client key fingerprint read back as `SHA256:zabzHaYz…`, matching what
  `provision-worker-client-key.sh` reported. A new **worker host key** was generated
  (`SHA256:PvXwn0d75WthOGXkQHX8L6oDRf4a5rzTd2+fT3JyveE`) and pinned into the gateway's `known_hosts`.
  The gateway shim directory shows `worker_client_ed25519` owned by host UID **599823**, which is container
  UID **10000** under `hermes`'s subuid mapping — confirmed inside the namespace by
  `podman unshare stat` returning `10000 10000`.
- **Worker image built from the pinned base:** the Containerfile's
  `FROM registry.fedoraproject.org/fedora@sha256:2648f667…` matches the digest actually pulled, and
  `worker_build_rc=0` with image `localhost/hermes-worker:1` = `60a498cb38ac…` (131 packages installed).
- **Gateway image pulled at its pinned digest:** `docker.io/nousresearch/hermes-agent@sha256:9469b3e7…`
  matches the Quadlet's `Image=` line exactly.
- **Worker started and genuinely running.** `worker_start_rc=0`, `worker_state=active`,
  `hermes-worker Up 4 seconds localhost/hermes-worker:1`. **Verified independently of the helper** by
  inspecting processes: `conmon -n hermes-worker` with its storage at
  `/home/hermes/.local/share/containers/storage`, plus `socat` as the socket adapter, `catatonit`, and
  `hermes`'s user manager and dbus — and exactly **one** conmon, the gateway being correctly inactive.
- **Isolation proven the right way round — by failure:**

  | Probe | Result |
  | --- | --- |
  | worker `/proc/net/route` | **empty** (no route table at all) |
  | worker egress probe | `curl: (6) Could not resolve host: example.com` → `EGRESS_NO`, `DNS_UNRESOLVED` |
  | worker Quadlet | `Network=none` — the config matches the observed behaviour |

- **Transport acceptance, including the two deliberate negatives the guide asks for:**

  | Test | Result |
  | --- | --- |
  | positive round trip | `TRANSPORT_OK`, hostname `worker`, `Fedora release 44 (Forty Four)` — the worker's identity returned **while the gateway is Debian** |
  | **missing trusted key must fail** | `No ED25519 host key is known for worker … Host key verification failed`, `missing_key_rc=255` |
  | **changed host key must fail** | `Host key for worker has changed … Host key verification failed`, `changed_key_rc=255` |
  | scp round trip through the socket | `SCP_OK`, `scp_rc=0`, transferred file hash `f3873b86f11e` |

  The two negatives are the substance of this gate: they show the transport is actually *authenticated*
  rather than merely *connected*. Option precedence was also dumped explicitly
  (`identitiesonly yes`, `stricthostkeychecking true`, the pinned `identityfile`/`userknownhostsfile`, and
  the `proxycommand` through `unix-bridge.py`), so the shims are demonstrably overriding the backend's
  `accept-new` default rather than relying on it.
- **Gateway runtime identity can read its material:** as container UID 10000 it reports
  `uid=10000(hermes) gid=10000(hermes)`, with `KEY_READABLE`, `KNOWN_HOSTS_READABLE`, `SHIM_EXECUTABLE`.
  Note it also shows `ls: cannot open directory '/opt/hermes/gateway-ssh': Permission denied` — that is the
  `0711` directory mode doing its job (traverse without list), not a fault.
- **Clean:** `recent AVC denials: <no matches>`, 0 failed units, and `gateway_state=inactive` — M02
  deliberately leaves activation to M03.
- **FINDING — the egress prerequisite list was incomplete.** The pre-deployment egress check (recorded
  earlier in this ledger) verified `registry.fedoraproject.org`, `api.openai.com` and `api.telegram.org`,
  and described the first as covering "the worker image build". It **omitted the gateway image registry**:
  M02 pulls `docker.io/nousresearch/hermes-agent@sha256:9469b3e7…`, which is neither of those hosts. The
  pull succeeded here, so Docker Hub egress is in fact open, but a replication behind a tighter firewall
  would have hit an unannounced failure at M02 step 1 having passed every pre-flight check. The egress list
  should name `docker.io` / `registry-1.docker.io` explicitly.
- **Reverse:** `m02` leaves no irreversible state; removing the Quadlets and
  `podman rmi localhost/hermes-worker:1` undoes it.

### C27 — M03 step 2: activate, with no credential loaded — PASS

`priv=root` (operator), 2026-09-14 ~02:29Z (host local 21:29)

- **Gateway activated:** `daemon_reload_rc=0`, `gateway_start_rc=0`, `gateway_state=active`,
  `gateway_enable_state=generated` (from `inactive`). `hermes-gateway.service` is `active (running)` under
  **s6 supervision**, with the Quadlet at `/etc/containers/systemd/users/1001/hermes-gateway.container`.
- **Both containers running, verified independently of the helper:** `pgrep -c conmon` = **2**, naming
  `hermes-worker` and `hermes-gateway`, with `s6-svscan`/`s6-supervise` (7 processes) and the worker's
  `socat` adapter in `hermes`'s user manager.
- **Nothing is published — the isolation holds with the application up:**

  | Probe | Result |
  | --- | --- |
  | `ports=[]` for both containers | empty |
  | explicit port query | empty |
  | host listeners | **only** `22` (sshd), `5355` + `53` (systemd-resolved) |

- **The step's actual point — proven by the *absence* of credentials.** The gateway log shows
  `Auxiliary: marking openrouter unhealthy for 60s (payment / credit error)` and
  `Nous Portal not configured (run: hermes auth)`, plus `No env user allowlists configured`. Those are
  precisely the errors of an **uncredentialed** gateway, so activation demonstrably succeeded without any
  provider secret present — which is what separates a shim problem from a credential problem at step 5.
- **Shim resolution proven:** inside the container `which ssh` → `/opt/hermes/bin/ssh` (and `scp` likewise),
  both installed at 02:26. Container identity is `uid=0(root)` — expected for the upstream Debian s6 image,
  and the reason the *host-side* shim ownership (mapped UID 10000) matters rather than the in-container one.
- **The SSH backend is configured, not local:**
  `TERMINAL_ENV=ssh`, `TERMINAL_SSH_HOST=worker`, `TERMINAL_SSH_KEY=/opt/hermes/gateway-ssh/worker_client_ed25519`,
  `TERMINAL_SSH_USER=worker`, `TERMINAL_SSH_PORT=22`, `TERMINAL_SSH_PERSISTENT=true`.
- **Confirms the guide's warning about `hermes doctor`, live.** Doctor printed
  *"Running inside a container — using local terminal backend (docker-in-docker is not configured by
  default)"* **while `TERMINAL_ENV=ssh` was set in the same container.** Doctor is therefore demonstrably
  reporting its own forced `terminal_env=local` rather than the deployment's actual backend, exactly as the
  guide says — and it never exercises the SSH path. `gateway/m03-probe.py`, which the scripts drive, is the
  valid check. Doctor exited 0 with 4 advisory items, none of which are gate criteria here.
- **Clean:** `recent AVC denials: <no matches>`, 0 failed units, no reboot (`boot_id` unchanged).
- **Reverse:** stop the gateway unit; `.container` removal plus `daemon-reload` reverts.

### C28 — M03 step 3: configure and probe — PASS, with two findings about *how* it passes

`priv=root` (operator), 2026-09-14 ~02:31Z (host local 21:31)

- **Result: PASS.** `RESULT=PASS`, `probe_rc=0`, `resolved_backend=ssh`,
  `execute_output=HERMES_WORKER_ROUNDTRIP_OK`, and the probe's own evidence from inside the worker:
  `worker`, `NAME="Fedora Linux"`. The gateway survived a restart and re-probe (`start_rc=0`,
  `gateway_state_after_20s=active`), both containers up with `ports=[]`, and
  `recent AVC denials: <no matches>`.
- **It probed the real backend, not `local`.** The resolved policy dump contains
  `TERMINAL_ENV: ssh`, `TERMINAL_SSH_HOST: worker`, `TERMINAL_SSH_KEY: /opt/hermes/gateway-ssh/worker_client_ed25519`
  and `resolved_backend=ssh`, and the command genuinely executed on the worker (its home grew
  `.hermes/`, `credentials/`, `skills/` and the earlier `scp-probe.txt`). This is the check the guide says
  to use instead of `hermes doctor`, and it exercised the SSH path that doctor cannot.
- **FINDING 1 — four of the five config keys step 3 writes are not recognised by Hermes.** The writer
  printed, for each of them:

  ```text
  ⚠ 'terminal.ssh_host' is not a recognized config key — it was saved anyway, but Hermes may not read it.
  ```

  and the same for `terminal.ssh_user`, `terminal.ssh_port` and `terminal.ssh_key`. Only
  `terminal.backend = ssh` was accepted silently. **The step still passes because the Quadlet already sets
  the identical values as environment variables** (`quadlets/hermes-gateway.container:42-46`:
  `TERMINAL_ENV`, `TERMINAL_SSH_HOST`, `TERMINAL_SSH_USER`, `TERMINAL_SSH_PORT`, `TERMINAL_SSH_KEY`,
  `TERMINAL_SSH_PERSISTENT`). So the config write is **redundant with the Quadlet, and this run cannot
  show that it is load-bearing at all** — the probe would very likely pass with an untouched `config.yaml`.
  This is not a failure, but it is a misleading step: an operator who reads step 3 as "this is what points
  the gateway at the worker" could later remove or alter the Quadlet's `Environment=` lines believing
  `config.yaml` covers it, and get a silent fallback. **Open question for a replication, deliberately not
  tested here:** does the deployment still work with the Quadlet env removed and the config keys present?
  Testing it would mean editing the artifact under test mid-run, which this gate should not do.
- **FINDING 2 — `config.yaml` is rewritten in place, with no backup, and loses its documentation.** The
  script's backup-and-drop section is gated on the config being *below the v12 floor*; it reported
  `on_disk_version=none size=112921` and `config is not below the v12 floor; left in place`, so **no backup
  was taken** — and then the write commands rewrote the file anyway. The before/after top-level key
  listings show the same set of keys but at drastically different line numbers (`gateway:` 1220 → 83,
  `updates:` 1968 → 138), i.e. the ~113 KB commented upstream config was compacted to a bare key list. The
  settings survive; the explanatory comments do not. `config.yaml` lives at
  `/home/hermes/gateway-state/config.yaml` on the host (`/opt/data/config.yaml` in the container), and the
  post-write size was not printed by the helper.
- **Config state confirmed by readback:** `terminal.backend=ssh`, `ssh_host=worker`, `ssh_user=worker`,
  `ssh_port=22`, `ssh_key=/opt/hermes/gateway-ssh/worker_client_ed25519`.
- **Reverse:** restore `config.yaml` from a copy — which is exactly the backup this run does not have, so
  a replication should snapshot `/home/hermes/gateway-state/config.yaml` **before** step 3.

### C29 — M03 step 4: provision the OpenAI key

`priv=root` (operator), 2026-09-14 ~02:33Z (host local 21:33) — **secret handled correctly**

- **Handled safely end to end.** The script reads the key from the terminal **without echo**, twice
  (key + confirm), refuses to run without a real tty (`[ ! -t 0 ]` → `STOP`), feeds it to a one-shot
  container **over stdin so it never enters an argument list**, and that container writes the file with
  `umask 077` then `chmod 0600`. The script itself never prints the key.
- **Verified that nothing leaked into the captured log:** `grep -c 'sk-'` = **0** and
  `grep -cE 'OPENAI_API_KEY=.+'` = **0**. The entire log is the two prompts, the line count, the
  provisioned path and the metadata line. Nothing else.
- **`.env` shape:** `mode=600 owner=599823:599823 size=222`, 2 lines — the owner being mapped container
  UID 10000, and two lines matching the two variables the script writes.
- **Deliberate omission:** the script prints `file_sha256=` of the `.env`. That is a fingerprint of a file
  containing a credential. It is not the key and is not practically attackable, but it serves no
  verification purpose here, so **this record does not reproduce it**, in line with the working rule
  against committing credential-derived material. The value is in the operator's console log only.
- **FINDING 2 QUANTIFIED — `config.yaml` really was gutted by step 3.**

  | | before step 3 | after step 3 |
  | --- | --- | --- |
  | size | **112,921 bytes** | **2,983 bytes** (−97.4%) |
  | mode | 644 | 640 |
  | backup | — | **none exists** |

  The helper's own backup path is gated on the config being *below the v12 floor*, so it declined to back
  up and then the write commands rewrote the file regardless. The settings survive and the mode was
  tightened, but ~110 KB of upstream explanatory comments are gone and there is no copy to compare
  against. **A replication should copy `/home/hermes/gateway-state/config.yaml` aside before step 3.**
- **The standing hazard is now armed.** This script writes `.env` with
  `cat > /opt/data/.env` — **truncate, not merge** (line 63). Until step 8 it is harmless because nothing
  else is in `.env`; **from step 8 onward, re-running it would silently delete `TELEGRAM_BOT_TOKEN` and
  the allowlist while still reporting success.** Recorded here at the moment it becomes true rather than
  only in the earlier findings list.
- **Reverse:** delete `.env`; the next activation simply has no provider credential, as in C27.

### C30 — M03 step 5: accept — PASSES both criteria, and exposes a real SELinux defect

`priv=root` (operator), 2026-09-14 ~02:35Z (host local 21:35)

**The gate itself passes, on the criteria that matter:**

| Criterion | Result |
| --- | --- |
| authenticated inference | `inference_output=HERMES_OK` **exactly**, `inference_rc=0`, `INFERENCE_RESULT=PASS` |
| **harmless tool round trip executed IN THE WORKER** | `tool_output=HERMES_WORKER_TOOL_OK` **and** `Fedora release 44 (Forty Four)`, `tool_rc=0` |
| credential-leak checks (5) | `config_yaml_leak=no`, `worker_state_leak=no`, `transport_leak=no`, `worker_metadata_leak=no`, `worker_log_leak=no` |
| manual-profile hardening | `approvals.mode=manual`, `cron_mode=deny`, `single_query_mode=deny`, `destructive_slash_confirm=true`, `redact_secrets=true`, `allow_private_urls=false`, `allow_lazy_installs=false`, `tirith_fail_open=false`, `hooks={}`, `mcp_servers={}`, `cron_scheduling=False` |
| provider/model | `provider=openai-api`, `default_model=gpt-5.6-luna` |
| SSH backend preserved through hardening | `terminal.backend=ssh`, `ssh_host=worker`, `ssh_key=/opt/hermes/gateway-ssh/worker_client_ed25519` |

The second criterion is the substantive one: the model's tool call genuinely ran **inside the worker**
(returning its Fedora identity) rather than in the gateway container. A key that merely authenticates would
pass the first and fail the second.

- **NEW DEFECT — enforced AVC denials on the gateway state database.** Seven denials this boot, all
  identical:

  ```text
  avc: denied { lock } for pid=6173 comm="hermes" path="/opt/data/state.db-shm"
    scontext=system_u:system_r:container_t:s0:c519,c720
    tcontext=system_u:object_r:container_file_t:s0:c253,c452
    tclass=file permissive=0
  ```

  The process's **MCS categories (`c519,c720`) differ from the file's (`c253,c452`)**, and `permissive=0`
  means the lock is genuinely blocked. It is on `state.db-shm`, SQLite's WAL shared-memory file — the
  primitive SQLite uses for cross-process locking, so this is state-database machinery, not an incidental
  file touch.
- **Diagnosis — one shared directory is mounted with the *exclusive* relabel by several containers.**
  `:Z` asks for a **private** relabel, which is correct only when a volume belongs to a single container.
  Each container start relabels the tree to *its own* MCS categories, so the next container finds labels
  belonging to a previous one:

  | Volume | Mounted by | Option | Verdict |
  | --- | --- | --- | --- |
  | `/home/hermes/transport` | gateway **and** worker Quadlets | **`:z`** | correct — shared |
  | `/home/hermes/gateway-state` → `/opt/data` | gateway Quadlet:26, `provision-openai-key.sh:61`, `provision-telegram.sh:66` | **`:Z`** | **wrong — shared by three containers** |

  The codebase already makes the right distinction elsewhere, which is what makes this a defect rather than
  a design choice. **`provision-telegram.sh:66` will relabel `/opt/data` a fourth time at step 8**, so the
  denials will recur unless the option is corrected.
- **Impact.** The gateway currently works — inference and the tool round trip both passed — so the harm is
  latent rather than immediate, and the honest statement is that the *current* observable effect is the
  denials themselves. But lock denials on `state.db-shm` are exactly the failure mode that produces
  intermittent SQLite `database is locked` / I/O errors and state-persistence failures rather than clean
  errors, and **Phase 7 acceptance explicitly requires "no new AVC denials"**, so this must be resolved
  rather than noted.
- **Correct fix is labelling, not policy.** The guide is explicit: investigate AVC denials rather than
  installing a generated `audit2allow` module or setting SELinux permissive. The fix is to mount the shared
  state directory with **`:z`** (shared) in the gateway Quadlet and in both one-shot provisioning scripts,
  then restart and confirm the denials stop. Pending the label confirmation below.

### C31 — fix for the AVC denials: `:Z` → `:z`, plus an explicit relabel

`priv=none` (repo edit by the agent) + `priv=root` (relabel, operator), 2026-09-14 ~02:40Z (host local 21:40)

- **Diagnosis confirmed before touching anything.** `/home/hermes/gateway-state` and every file in it
  carried `container_file_t:s0:c253,c452` while the running gateway's `ProcessLabel` was
  `container_t:s0:c519,c720` — a category mismatch, with `permissive=0` so the denials were enforced. By
  contrast `/home/hermes/transport`, shared by two containers and mounted `:z`, carries
  `container_file_t:s0` with **no MCS categories at all** — which is exactly why it works, and which
  identified the fix.
- **Repo fix (three places, minimal):** `:Z` → `:z` for the shared state directory only —
  `quadlets/hermes-gateway.container:26`, `provision-openai-key.sh:61`, `provision-telegram.sh:66`. Every
  other `:Z` mount was **deliberately left alone**, because each really is used by a single container
  (`worker-state/*`, `gateway-ssh/*`). New hashes: gateway Quadlet `f3aa4461…`,
  `provision-openai-key.sh` `7b73e1cd…`, `provision-telegram.sh` `2670427c…`. Re-staged and verified
  byte-identical to the repo.
- **The option change alone was NOT sufficient — worth recording, because it is counter-intuitive.**
  Restarting with `:z` left the labels untouched: podman saw an existing `container_file_t` label and
  judged it adequate, so the stale MCS categories survived and the denials continued (981 more in the
  restart window). **Changing the mount option is necessary but does not relabel an already-container-
  labelled directory.**
- **Explicit relabel, which did work:** `sudo chcon -R system_u:object_r:container_file_t:s0
  /home/hermes/gateway-state` → `chcon_rc=0`, and the directory, `state.db-shm` and `logs/gateway.log` all
  became `container_file_t:s0` with **no MCS suffix**, matching `transport`. The gateway's own
  `ProcessLabel` correctly keeps its categories; what matters is that the files carry none.
- **VERIFIED FIXED — the denials stopped completely:**

  | Minute | Denials |
  | --- | --- |
  | 21:39 | 1,577 |
  | 21:40 | 400 (the relabel second) |
  | **21:41 – 21:44** | **0 each** |

  **Last denial: 21:40:11**, the exact second `chcon` ran. All 1,986 denials in the window carry
  `pid=6173`, the pre-restart gateway, and **zero** denials reference the new label. Both containers
  running, 0 failed units.
- **How bad it had been:** the pre-fix window counted **11,355** denial records, and the set included
  `denied { append }` on `/opt/data/logs/agent.log`, `errors.log` and `gateway.log`. The gateway could not
  lock its state database **and could not write its own logs** — so it was failing in a way it was also
  unable to report. Latent-looking denials were in fact an active retry loop, which is why this was fixed
  rather than filed.
- **A false alarm, recorded for honesty.** Reading the `.env` variable *names* showed
  `GATEWAY_ALLOW_ALL_USERS`, `API_SERVER_ENABLED`, `WEBHOOK_ENABLED` and `HERMES_DASHBOARD`, which looked
  like an insecure allow-all posture ahead of the Telegram gate. Reading `config/harden-config.py:97-115`
  showed the opposite: the harden step **forces** those four to `false`/`0`, replacing the value when the
  key already exists rather than merely adding it. Those names are the secure defaults, and step 9's
  unauthorized-rejection test should behave correctly. **Names are not values** — the check was worth
  making and the concern was unfounded.
- **Also noted as good practice:** `harden-config.py:94-96` deliberately does **not** write a
  `.pre-hardening-*` copy of `.env`, on the stated grounds that it holds the provider credential and a
  second copy would be an unnecessary secret duplicate — which also explains why `.env` grew from 222 to
  318 bytes by **merging** while only `provision-openai-key.sh` truncates.
- **Deviation declared:** this edits the artifact under test mid-run. Justified because Phase 7 acceptance
  requires no new AVC denials and the alternative was to validate a deployment known to fail its own final
  gate; recorded in the deviations list.

### C32 — M04 step 6: posture and resource budgets

`priv=root` (operator), 2026-09-14 ~02:42Z (host local 21:42)

- **Pre-values captured before the change, as the guide requires:**

  | Object | Before |
  | --- | --- |
  | `user-1001.slice` | `MemoryHigh=infinity`, `MemoryMax=infinity`, `MemorySwapMax=infinity`, `CPUQuotaPerSecUSec=infinity` |
  | `hermes.slice` | same (exists but unused) |
  | gateway container | `Memory=2147483648` (2 GiB), `NanoCpus=0` |
  | worker container | `Memory=2147483648` (2 GiB), `NanoCpus=0` |

- **Applied:** `set_property_rc=0` → slice `MemoryHigh=6442450944` (6 GiB),
  `MemoryMax=8589934592` (8 GiB), `TasksMax=1536`. This host is 13 GiB / 4 cores, matching the
  reference, so the conservative figures apply without rescaling. Both containers stayed up
  (`hermes-worker`, `hermes-gateway`), `worker_state=active`, 0 failed units.
- **Credential cleanup:** only `/home/hermes/gateway-state/.env` (318 bytes, mode 600) — **no duplicate
  copies present**. The helper's removal pass had nothing to remove.
- **FALSE ALARM, corrected — the limits ARE persistent, and the helper checks the wrong path.** The
  helper printed

  ```text
  -- persistent drop-in --
  ls: cannot access '/etc/systemd/system/user-1001.slice.d/': No such file or directory
  ```

  which reads as "the budget was not persisted". Investigated and refuted: `systemctl set-property`
  without `--runtime` writes its drop-ins to **`/etc/systemd/system.control/<unit>.d/`**, and both files
  are there — `50-MemoryHigh.conf` and `50-MemoryMax.conf`. The budget therefore **does** survive a
  reboot, and the guide's repeated warning that "`systemctl set-property` proved to be runtime-only" does
  not apply to this invocation. The helper's persistence check simply names a directory that
  `set-property` never writes to, so it reports a false negative on the one property it was added to
  confirm.
- **REAL helper defect — the read-only posture check cannot run at all.** Both containers report:

  ```text
  readonly=Error: template: inspect:1:33: executing "inspect" at <.HostConfig.ReadOnly>:
    can't evaluate field ReadOnly in type *define.InspectContainerHostConfig
  ```

  `HostConfig.ReadOnly` does not exist in podman 5.8.4's inspect schema, so this check errors rather than
  returning a value. **The substance is still covered** by the functional probe, which is the stronger
  evidence anyway: inside the worker, `touch /m04-readonly-probe` → `Read-only file system` →
  `READONLY_OK`, while `TMP_WRITABLE_OK`. Also recorded there: `NoNewPrivs=1`, `Seccomp=2` (filter mode),
  `mountinfo_lines=41`, and `CapEff == CapBnd == 00000000800405fb` (no capability gain).
- **SELinux fix held through this step:** `gateway-state` now reads `container_file_t:s0` with **no MCS
  suffix** (matching `transport`), and **0 denials since 21:41:00** — the last denial in the journal is
  still 21:40:11. The helper's own "recent AVC denials" section shows only those stale pre-fix records,
  because its window reaches back ten minutes.
- **LATENT RISK, flagged with a prediction to test at the next reboot.** The remaining `:Z` mounts are
  `worker-state/home` and `worker-state/ssh-host-keys` (worker only) and `gateway-ssh/*` (gateway only).
  Their labels currently carry MCS categories tied to the container instance that created them —
  `gateway-ssh` is visibly `container_file_t:s0:c253,c452` while the gateway process is `c519,c720`, a
  mismatch that does no harm today **only because that mount is read-only** (`:ro`), so no write is ever
  attempted. `worker-state/home` is *writable* by the worker and its labels have never been exercised
  across a restart. Since a `:z` label carries no categories and is therefore restart-stable by
  construction, while a `:Z` label is only safe when it matches the current instance's categories — and we
  have direct evidence of one case where it did not — **the prediction is that the next worker restart
  may produce the same class of denials under `/home/worker`.** The coming reboot in step 11 is the cheap
  test; if it happens, the fix is the one already proven here. **REFUTED BY MEASUREMENT in C33 item 6:**
  the tree is uniformly `container_file_t:s0` with no MCS suffix at all, including files the running
  gateway wrote minutes earlier, because new files inherit the **directory's** level rather than the
  creating process's. There is no pending `:Z` restart risk.
- **Reverse:** `systemctl revert user-1001.slice` removes the control drop-ins and returns the budget to
  `infinity`.

### C33 — M04 step 7: stopped-state backup and isolated restore

`priv=root` (operator), 2026-09-14 ~02:43Z (host local 21:43); re-verified 21:47–21:53.

**Both of the guide's acceptance criteria are met.**

| Check | Result |
| --- | --- |
| Entry counts, source vs restored | `gateway_state` 1524/1524, `worker_state` 450/450, `gateway_ssh` 11/11 — exact |
| Restored config asserts the SSH backend | `^  backend: ssh` = **1** |
| Restored config asserts the model | `gpt-5.6-luna` = **3** |
| Restored config asserts the worker host | `^  ssh_host: worker` = **1** |
| Restored `.env` | mode 600, owner `599823:599823`, 1 `OPENAI_API_KEY` line |
| Archive | 1988 entries, 98,283,520 bytes, sha256 `0a61e03f74b21383082890ddcab143c170aabaf4cd1ba7cea695ea11798adfe3` |
| Restored credential copy removed | `restore_test_dir_removed=yes`, and independently confirmed absent |

The helper prints those three config assertions as **unlabelled bare counts** (`1`, `3`, `1`); the
mapping above comes from reading `m04-backup.sh:114-116` rather than from the output alone.

1. **The helper stops the gateway and never restarts it — already documented in this record, now
   confirmed live, with one sharpen.** `application_layer_findings.backup_path_review.operational_notes`
   in the baseline JSON already states that `m04-backup.sh` restarts only the worker and that the gateway
   "returns through its Quadlet `[Install]` autostart at the next boot". Line 61 stops
   `hermes-gateway.service`, line 62 stops `hermes-worker.service`, and lines 135-136 restart **only the
   worker**. Confirmed live over SSH immediately afterwards, before any repair: exactly one conmon
   process, `-n hermes-worker`, and `gateway=inactive` — *inactive* rather than *failed*, i.e. a clean
   stop. Line 64's `podman ps -a` printed **nothing**, which is Quadlet's `ExecStop` removing the
   container, so that line cannot serve as a warning either. The asymmetry is correct in
   `m02-deploy-and-validate.sh:149-150`, where M02 runs before the gateway is ever started.
   **The sharpen:** the record's rationale holds only because a *later* step restores it, and
   `provision-telegram.sh` does **not** restart the gateway — so it stays down for the whole of step 8,
   and `m05-telegram.sh:47` is the first thing that would bring it back. Step-8 output therefore
   describes a host whose gateway is stopped, which matters if that output is read as evidence of a
   working system. **Recovered by starting the gateway manually** — `gateway=active`, both containers up —
   which is also what produced finding 5 below.

2. **DEFECT — `diff_rc` measures `head`, not `diff`.** `m04-backup.sh:111-112` is
   `diff -r … 2>&1 | head -n 10` followed by `echo "diff_rc=$?"`; `$?` after a pipeline is the **last**
   command's status, and `head` returns 0 unconditionally. The `diff_rc=0` in the step-7 output therefore
   asserts nothing. Same class as the corrected `resolver_cross_check` false PASS. The operator
   hand-reproduced the two lines and also got `diff_rc=0`, but in that run `$RESTORE` was unset so both
   arguments collapsed to `/home/hermes/gateway-state` and diff compared a path with itself — recorded as a
   **code-structure** finding, not a demonstrated one.

3. **The ten `diff` errors are explained and benign — and the hidden remainder was predicted before it was
   looked at.** The archive census shows exactly **13 symlinks**, all
   `…/gateway-state/home/.cache/uv/wheels-v6/pypi/<pkg>/<ver>` pointing at absolute in-container targets
   `/opt/data/home/.cache/uv/archive-v0/…`, which are dangling on the host. `diff -r` follows them into
   "No such file or directory". The output was truncated at `head -n 10`, so 13 − 10 = 3 were hidden; they
   were named in advance from the archive listing as `tabulate`, `typing-extensions`, `yarl` and confirmed.
   **Corrected re-run** with `diff -rq --no-dereference`: `restored_symlinks=13`, matching the prediction
   exactly. Of 30 differing lines, 21 are unambiguous runtime churn (`gateway.pid`, `gateway.sock`,
   `gateway.lock`, `state/gateway.loop-tick.152.sock`, seven `*.db-wal`/`*.db-shm`, `cron/ticker_*`,
   `state/gateway.heartbeat`, `state/gateway.lifecycle.json`, `gateway_state.json`,
   `channel_directory.json`, three `cache/*.json`, `gateway-starts.log`, `logs/gateways/default/current`),
   and one is `.clean_shutdown`, present **only in the backup** — a positive signal, since it proves the
   archive really is a stopped-state capture and the live copy is gone because starting the gateway
   consumes it.

4. **`config.yaml` came back byte-identical — and the ledger's M03 size figure was wrong.** `cmp` is clean
   between live and restored `config.yaml`: **3678 bytes**, mtime 21:35:09, unchanged across the later
   restart, so the gateway does not rewrite it at runtime. The 2983-byte figure recorded at M03 is stale
   and is corrected here; this is a measurement error in the ledger, **not** backup drift.

5. **`.env` differed between backup and live, and the resolution vindicates the backup.** The decisive test
   is the manifest's own `env_file_sha256`, taken from the live file at 21:43: the archive's `.env` hashes
   to exactly `0331d5dd7263aa7abc957c4cea5b924db11e8764178a2550414ffa1c67313d21` (318 bytes, mtime
   21:35:09). The live file is now **398 bytes**, mtime **21:46:46**, sha256 `635d58bb…`. The delta is
   exactly 80 bytes = `API_SERVER_KEY=` (15) + 64 hex characters + newline, and the key-name lists differ by
   exactly that one name — so **the gateway generates `API_SERVER_KEY` and writes it into `.env` on first
   start.** Consequences: the manifest's `env_file_sha256` is a *stopped-state* value and is stale the
   moment the gateway starts (a replicator comparing hashes will see a mismatch that looks like tampering
   and is not); and `.env` is a **runtime-mutated** file, not a static artifact.
   - **Generate-once, not per-start:** after a full restart, size is still 398, sha unchanged,
     `api_server_key_lines=1`, `duplicates=` empty, all seven names present. `.env` is therefore stable
     through step 9's two restarts, which was the question that mattered.
   - **Inert:** `API_SERVER_ENABLED=false` and `ss -ltn` shows only 22, 53 and 5355, before and after.

6. **CORRECTION TO C32 — the flagged `:Z` restart risk does not exist, and the real mechanism is
   inheritance from the *directory*.** C32 predicted that the remaining `:Z` mounts carry instance-specific
   MCS categories that the step-11 reboot would trip. **Measured and falsified:**
   `find /home/hermes/gateway-state -maxdepth 2 -not -context '*:container_file_t:s0'` returned
   **nothing** — the whole tree is `container_file_t:s0`, including `.env` written minutes earlier by the
   running gateway, and it stayed `s0` across a restart. New files inherit the **directory's** level, not
   the creating process's. That is the correct explanation of the C31 failure: a `:Z` mount had relabelled
   the *directory* with one instance's categories, children inherited them, and the gateway running as
   `c519,c720` was denied. `:z` plus the explicit `chcon` fixed it at the directory, and inheritance has
   held it there since. **There is no pending `:Z` restart risk and step 11 is not its test.** C32's bullet
   is annotated in place rather than deleted, so the refuted prediction stays visible.

7. **LATENT DEFECT, not yet triggered — `provision-telegram.sh:72` can silently wipe `.env`.**
   `grep -vE "^(TELEGRAM_BOT_TOKEN|TELEGRAM_ALLOWED_USERS|TELEGRAM_ALLOW_ALL_USERS)=" /opt/data/.env > "$tmp" || true`
   is a **read of `.env` by a throwaway container**. If that read were ever denied — i.e. any future MCS
   mismatch — grep exits 2, the `|| true` suppresses it, `set -e` on line 68 cannot fire *by construction*
   because `cmd || true` always succeeds, `$tmp` stays empty, and `mv -f` installs a **three-line `.env`**
   holding only the Telegram keys: `OPENAI_API_KEY`, `API_SERVER_KEY` and the four hardening flags gone.
   The only symptom would be `env_lines=3` on line 79, while `telegram_token_lines=1` on line 86 still
   reports success — a credential-destroying failure that looks like a pass. **Dormant today** because the
   tree is uniformly `s0` and an empty category set is a subset of every process's category set, so the
   read cannot be denied. Recorded anyway: it is one directory relabel away from firing, and the
   step-8 read-path rehearsal is in flight and will be appended when it returns.

8. **Step 8 is safe for the reason the helper's own comment claims, now checked against the code.**
   Lines 71-78 filter out only the three `TELEGRAM_*` keys, append the new ones, `chmod 0600`, and `mv -f`
   atomically — everything else survives. **`provision-openai-key.sh:63` remains the only truncating
   writer** (`cat > /opt/data/.env`), and it is now *more* dangerous than when the standing warning was
   written, because `.env` contains a gateway-generated key that no provisioning script knows about.

9. **Instrument defects on the agent side, all four caught before they entered the record.** (a) A block
   used `mktemp /root/…`, `find /home/hermes/…` and a `> /root/…` redirect without `sudo`, so it produced
   no data; (b) `sudo ausearch … 2>/dev/null` masked a permission failure and printed
   `avc_count_today=0` — a **false zero**, proven false by `unprivileged_ausearch_rc=1` with
   `Error opening config file (Permission denied)`; (c) `sudo wc -l < file` performs the redirection in the
   *unprivileged* shell, producing empty rather than zero; (d) `runuser` without root returns
   `may not be used by non-root users`. All four are the same failure mode this run has now corrected
   twice elsewhere: an instrument that returns a confident value when it has actually failed.

10. **A second, redundant slice drop-in now exists.** This helper writes
    `/etc/systemd/system/user-1001.slice.d/50-hermes-limits.conf` (line 36) with
    `MemoryHigh=6G`/`MemoryMax=8G`/`TasksMax=1536`, while C32's `set-property` wrote the same values to
    `/etc/systemd/system.control/user-1001.slice.d/`. Both are system-level and both are effective, and the
    values agree, so this is duplication rather than a conflict — but the two directories are different and
    a replicator will find two files where the ledger previously described one. **Reverse:** remove the
    drop-in directory and `systemctl revert user-1001.slice`.

11. **SELinux regression check, second and third datapoints.** No denials after 21:40:11 across the
    gateway restart that remounts `gateway-ssh` (`:Z`, `:ro`) and `gateway-state` (`:z`). `avc_today=14442`
    is unchanged by the restart, the last timestamp stays 21:40:11, no denial names `.env`, and the
    `worker-state`/`/home/worker` grep is empty. Zero failed units.

12. **Off-disk transfer of the archive — COMPLETE, hash-verified.** The helper stages the backup for
    transfer but does not perform it, and the archive contains the provider credential, so the only copy
    was sitting on the host that Phase 7 power-cycles. Pulled with an **unprivileged** `scp` as `aicowork`
    (the directory is owned by `aicowork` at 0700 with the archive at 0600, so no privilege was needed) to
    `private/hermes-app-backups/` on the LUKS-encrypted workstation. The transferred `app-state.tar`
    re-hashes to `0a61e03f74b21383082890ddcab143c170aabaf4cd1ba7cea695ea11798adfe3` — **identical** to the
    archive identity recorded above, so the off-host copy is byte-identical to the validated archive and
    the backup-fidelity proof carries over to it. `private/` is excluded from git by `.gitignore:74`
    (confirmed with `git check-ignore -v`), and `git status --porcelain` shows **0** `private/` paths, so
    this is not a Git artifact. **The host copy was deliberately not deleted in the same step:** deletion
    is destructive and gets its own guarded block, so the transfer is verified before the other copy is
    removed. Recorded as documentation of a real change, not as a claim about the guide.

13. **Step-8 read path verified safe — and the rehearsal confirmed the label-inheritance model a third
    time, unasked.** The corrected rehearsal ran as root and reproduced step 8's exact `:z` mount and
    filter logic:
    - The throwaway container ran as `system_u:system_r:container_t:s0:c286,c472` — **its own MCS pair**,
      distinct from the gateway's. It read `/opt/data/.env` (`container_file_t:s0`, 398 bytes) with
      **`READ_OK`** and `lines_visible=7`. That is the direct proof that an empty category set on the file
      is a subset of *every* container's category set, which is exactly why the `provision-telegram.sh:72`
      `|| true` hazard is dormant rather than merely unlikely.
    - The dry-run filter carried forward **all 7 keys** (`carried_forward_keys=7`,
      `carried_forward_lines=7`) into a scratch file, then removed it (`scratch_removed=yes`).
    - **Pre-commitment for the live run:** `provision-telegram.sh` should print **`env_lines=10`** — the 7
      carried-forward keys plus the 3 Telegram keys. `env_lines=3` is the signature of the wipe and must
      abort the sequence, not be read as success.
    - **Third confirmation of item 6, and the strongest one.** The scratch file `.env.step8dryrun`,
      created by the `c286,c472` container inside an `s0` directory, came out
      **`container_file_t:s0` with no categories** — so new files inherit the **directory's** level and not
      the creator's. Items 6 and 13 now rest on measurement from two different containers with two
      different MCS pairs.

### C34 — M05 step 8: Telegram provisioning

`priv=root` (operator, interactive), 2026-09-14 ~02:56Z (host local 21:56)

- **Preflight, because the BUNDLE copy is what executes rather than the repo copy.** The bundle's
  `provision-telegram.sh` hashes to
  `2670427c4f8b3cff775dc64b20a500a6230bd3a6849c923121326ff063e305f5`, matching the C31-fixed repo
  revision exactly. The `:z` mount is on line 66, and `grep -c systemctl` returns **0** — confirming from
  the artifact itself that this script does not restart the gateway, which is the step-8 half of C33 item 1.
- **Before:** `.env` 398 bytes, 7 keys, mode 600, owner 599823:599823.
- **Result — the pre-commitment from C33 item 13 was met exactly: `env_lines=10`.** That is the 7 keys the
  C2 dry run proved get carried forward, plus the 3 Telegram keys. The `provision-telegram.sh:72`
  `|| true` hazard **did not fire**.
- **After:** 529 bytes, 10 keys, mode 600, owner 599823:599823, label
  `system_u:object_r:container_file_t:s0` with **no MCS categories**.
- **Byte accounting closes exactly.** 529 − 398 = **131** added bytes, fully explained by the three new
  lines: `TELEGRAM_ALLOWED_USERS=<10-digit id>` = 35, `TELEGRAM_ALLOW_ALL_USERS=false` = 31,
  `TELEGRAM_BOT_TOKEN=<45-char token>` = 65. Every added byte is accounted for, so nothing was silently
  inserted or dropped alongside them.
- **Key order preserved**, which is what the filter's structure predicts: the original 7
  (`OPENAI_BASE_URL`, `OPENAI_API_KEY`, `API_SERVER_ENABLED`, `HERMES_DASHBOARD`,
  `GATEWAY_ALLOW_ALL_USERS`, `WEBHOOK_ENABLED`, `API_SERVER_KEY`) followed by `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_ALLOWED_USERS`, `TELEGRAM_ALLOW_ALL_USERS`.
- **FOURTH CONFIRMATION of the C33 item 6 inheritance model, and the first on the real provisioning path.**
  The `.env.new` that the throwaway container created inside the `s0` `gateway-state` directory came out
  `container_file_t:s0` with **no** categories, despite that container carrying its own MCS pair, and
  `mv -f` preserved it. The model — new files inherit the **directory's** level, not the creator's — now
  holds across three distinct containers with three distinct MCS pairs.
- **Security posture of the run itself:** `allow_all_users=false`, `telegram_token_lines=1`,
  `authorized_users=<redacted-telegram-user-id>` (a numeric Telegram ID, which the script's own header classifies as
  non-secret). No token material was displayed, and the command was **deliberately not** piped through
  `tee`, so no secret entered a log or the evidence files.
  `file_sha256=c720b21e9d5d01d91fd63b7eecc8c9cbc3e6a4b688b12381f9744285615a4a81`.
- **Expected non-event, recorded so it is not later read as a fault:** the gateway is still running with
  the **pre-Telegram** configuration. It does not see the new keys until `m05-telegram.sh` restarts it at
  step 9.
- **GAP — carried forward, not assumed away.** The key-name list and the byte accounting strongly imply the
  original lines were carried through unchanged, but *neither proves their **values** are byte-identical*,
  because the filter rewrites the entire file via `grep` plus `mv -f`. The decisive check is queued as the
  step-8 closure: `head -c 398 /home/hermes/gateway-state/.env | sha256sum` must equal
  `635d58bba315269f9df6a3d5149bc931cf0e53a3cd9c33c7a0fbf8e187ccd688`, the hash of the 398-byte pre-step-8
  file. Since the filter writes the 7 original lines first and *then* appends, the first 398 bytes must be
  the old file exactly.
- **GAP CLOSED — the merge is byte-faithful *with values*, not merely by key name.**
  `head -c 398 /home/hermes/gateway-state/.env | sha256sum` returned
  `635d58bba315269f9df6a3d5149bc931cf0e53a3cd9c33c7a0fbf8e187ccd688` — **exactly** the hash of the
  398-byte pre-step-8 file — and the 131 bytes appended after that point name only
  `TELEGRAM_BOT_TOKEN=`, `TELEGRAM_ALLOWED_USERS=` and `TELEGRAM_ALLOW_ALL_USERS=`. The
  filter-append-`mv` path is therefore verified end to end, and the **only** remaining risk in
  `provision-telegram.sh` is the `|| true` on a code path that is currently unreachable.
- **Host archive removed, after re-confirming the hash on the host immediately beforehand.**
  `0a61e03f74b21383082890ddcab143c170aabaf4cd1ba7cea695ea11798adfe3` re-verified on the host, matching the
  already-verified off-host copy, then `rm -rf` → `host_archive_removed=yes`. The deletion was wired
  *inside* the integrity conditional on purpose: had the prefix hash mismatched, the archive would have
  been the recovery source and nothing would have been deleted.
  `private/hermes-app-backups/` on the LUKS-encrypted workstation is now the only copy.
  **Caveat for the final phase:** this is the **step-7** state and contains no `TELEGRAM_*` keys, so it is a
  valid recovery point for the provider configuration but *not* a snapshot of the fully configured
  gateway. A fresh backup after step 9 would capture the complete state.

### C35 — M05 step 9: gateway activation with Telegram

`priv=root` (operator), 2026-09-14 ~03:00Z (host local 22:00)

- **Result: PASS on every pre-commitment, and the authorized-message test passes.**
  `restart_rc=0`, `gateway_state_after_25s=active`, `gateway_state_after_85s=active`, both containers up with
  `ports=[]`, `recent AVC denials: <no matches>`, and 0 failed units. The decisive log line is
  `2026-09-14 03:00:15 [Telegram] Connected to Telegram (polling mode)`. No public listener beyond
  `systemd-resolve` (53, 5355) and `sshd` (22).
- **Pre-commitment met: `env_sha256` is still `c720b21e…`.** So the gateway's `API_SERVER_KEY` append
  (C33 item 5) really is generate-once, now confirmed across two restarts, and step 9's restart did not
  rewrite `.env`.
- **Secret-leak check on the output file: 0/0/0.** `openai_key_shaped=0`, `telegram_token_shaped=0`, so
  neither an `sk-…`-shaped nor a `<digits>:<35 chars>`-shaped string reached
  `/home/aicowork/hermes-m05-telegram.out`. `redaction_markers=0` is expected and not a failure: the log
  tail contained no token-bearing line to redact, so the redactor had nothing to substitute.
- **Operator-reported: a Telegram message from the authorized account got a reply from the bot.** This is
  operator-observed only — the agent cannot see the operator's Telegram client — and is recorded as such,
  the same way the `passwd -S` and `sudo -l` results are.
- **FINDING 1 — the profile config is one the image refuses to migrate, and the guard that should have
  caught it is inverted.** Every gateway start logs
  `[config-migrate] WARNING: This config predates version 12 (~2 years old) and can no longer be
  auto-migrated.` Verified against the byte-identical archived copy (`config.yaml`, 3678 bytes, 178 lines,
  sha256 `072e3a0b789b597eb883140bdc6cd09dff59b8231ca473c31496e076ce17bd0a`, matching the step-7 manifest's
  `gateway_config_sha256`): **`_config_version` is absent entirely**, and absent from
  `config.yaml.pre-hardening-20260914T023509Z` as well. This **extends C28 FINDING 2**: that recorded
  `on_disk_version=none` and filed it as a missing-backup problem. The sharper consequence is that
  `m03-configure-and-probe.sh:92` reads
  `if [ -n "${ver:-}" ] && [ "$ver" -lt 12 ] 2>/dev/null`, so a config with **no** version fails the `-n`
  test and takes the *else* branch — "config is not below the v12 floor; left in place" — while an absent
  version is exactly what the image's own migrator calls pre-v12. **The guard is inverted for the one case
  it exists to handle.** Impact is not a failure today (the gateway runs, Telegram connects, M03 inference
  passed) but the profile is permanently un-migratable and the upstream remedy — "manually set
  `_config_version: 12` after reviewing the changelog" — appears nowhere in the guide. **Not fixed**, because
  setting a version blind is a claim about schema compatibility this run cannot substantiate.
- **FINDING 2 — the guide's credential step produces a pairing the gateway warns about.**
  `agent.auxiliary_client: OPENAI_BASE_URL is set (https://api.openai.com/v1) but model.provider is
  'openai-api'. Auxiliary clients may route to the wrong endpoint.` `provision-openai-key.sh` writes both
  `OPENAI_BASE_URL` and `OPENAI_API_KEY` while the config sets `provider: openai-api`, and the gateway
  itself says the combination may misroute **auxiliary** clients — summarisation, titles and similar
  background calls. Main inference is unaffected (that is the M03 `INFERENCE_RESULT=PASS` path), so this is
  invisible to the current acceptance criteria and would surface later as unexplained auxiliary behaviour.
- **FINDING 3 — `HERMES_DASHBOARD=0` does not stop the dashboard service from starting.** The log shows
  `s6-rc: info: service dashboard: starting` … `successfully started`, and the surrounding banner says the
  dashboard is supervised alongside "if `HERMES_DASHBOARD` is set". `harden-config.py` writes
  `HERMES_DASHBOARD=0`, so the supervision appears to test *presence* rather than truthiness. **Impact is
  currently nil and that is verified, not assumed:** `podman port` is empty, `ports=[]` on both containers,
  and `ss -ltn` shows no additional host listener, so the container's own network namespace keeps it
  unreachable. Recorded because the hardening flag does not do what the record implies it does.
- **Observation, not a defect — ~28 `tools.registry: check_fn … returned False` lines.** Optional tool
  groups (browser, discord, spotify, feishu, home assistant, x, yuanbao, image/video generation, kanban,
  connectors, react, web api key) are unavailable because their dependencies or credentials are absent,
  which is expected for a transport-only deployment. One mild inconsistency worth noting: every
  `check_browser_*` returns False while the same log reports
  `Found agent-browser Chromium binary: …/chrome-headless-shell`, so the browser tools are gated on
  something other than the binary's presence.
- **Post-step-9 baseline before the operator tests** (`m05-tests.sh status`, read-only):
  `allowlist=<redacted-telegram-user-id>`, `allow_all=false`, `token_lines=1`,
  `env_mode=600 owner=599823:599823 size=529`, `gateway=active`, `worker=active`, both containers
  `ports=[]`, and `saved_allowlist=none`. The last value is procedural rather than cosmetic:
  `allowlist-swap` fails closed if `/root/hermes-m05-allowlist.saved` already exists, so `none` means the
  unauthorized-account test is clear to run.

### C36 — DEFECT FOUND AND FIXED: the C31 `:Z` fix was incomplete — five more files, six more lines

`priv=root` (operator) for the bundle push, 2026-09-14 ~03:05Z

- **What C31 missed.** C31 fixed three `:Z` sites on the shared `gateway-state` directory. A complete
  inventory by direct inspection finds **eight**, and five files were left untouched:

  | File | Line | State |
  | --- | --- | --- |
  | `quadlets/hermes-gateway.container` | 26 | fixed by C31 |
  | `provision-openai-key.sh` | 61 | fixed by C31 |
  | `provision-telegram.sh` | 66 | fixed by C31 |
  | `m03-configure-and-probe.sh` | 47 | **missed** — now fixed |
  | `m03-accept.sh` | 44 | **missed** — now fixed |
  | `m05-tests.sh` | 67 | **missed** — now fixed |
  | `m05-gateway-diag.sh` | 57 | **missed** — now fixed |
  | `m05-gateway-diag2.sh` | 69 and 78 | **missed** — now fixed |

- **CORRECTION TO C31's EXPLANATION — the fix was not durable, it was lucky.** The denials are timestamped
  **21:40:11**, and `m03-accept.sh` (C30, M03 step 5) ran in exactly that minute carrying
  `-v "$GW_STATE":/opt/data:Z` on line 44. So the container that private-relabelled the directory with
  `c253,c452` — the categories the gateway, running as `c519,c720`, was then denied on — was most likely the
  one launched by a script C31 never modified. C31's `chcon` repaired the directory and the option changes
  covered three other sites, but the culprit path simply was not executed again afterwards. **The same class
  of failure was therefore reachable at any time from four unmodified scripts**, and the M05 tests were about
  to reach it: `m05-tests.sh allowlist-swap` and `allowlist-restore` both call `set_allowlist()`, which
  mounts the live state directory with `:Z`.
- **Why `:Z` is wrong here, stated in terms of the verified model.** `:Z` is the *private* relabel: podman
  relabels the source tree to categories unique to that container. The directory is the thing that gets
  relabelled, and per C33 item 6 every child inherits the **directory's** level — so one `:Z` mount
  re-stamps the whole tree with a foreign pair and every subsequently created file inherits it. A directory
  shared by a long-running service and any number of throwaway containers needs `:z`, which relabels to the
  shared `container_file_t:s0` and is therefore stable.
- **Fix applied to all six lines** (`:Z` → `:z`, one character each) in the five files above. The remaining
  `:Z` sites in `scripts/hermes/manual/` are all on genuinely **private, single-container** paths and are
  deliberately left alone: `quadlets/hermes-worker.container:25` (`worker-state/home`) and `:26`
  (`worker-state/ssh-host-keys`, `ro,Z`), and `quadlets/hermes-gateway.container:30-33` (the four
  `gateway-ssh` binary mounts, `ro,Z`). Those match the documented meaning of `:Z`.
- **Bundle re-staged and verified**, because the bundle copy is what executes (C13, and step 8's preflight):
  `m03-configure-and-probe.sh` `7edfbff71f87058a4bdd6a98ac7d845370b4015bac6b53754916eafcfeda0308`,
  `m03-accept.sh` `fcea2b4340b93a05a3bacd9669ecc08382a2419879117a5c43f4d8e0222cbd71`,
  `m05-tests.sh` `9b6b95ba280ac31e8edfef767f10bf74adf0a31ddbb125ef693cd01672ff495c`,
  `m05-gateway-diag.sh` `1f0bee7efbb6ca60c5f092449e2e2a7378c00a1fe940a6f4622c2e05e4ab5363`,
  `m05-gateway-diag2.sh` `5364d0b15640cf362cf1cf5ae8378ce8e1fb75519718f02c9e4ad0adcf7c4f19`. Each pair was
  hash-compared repo-against-host after the push and all five **MATCH**; the staged line now reads
  `-v "$STATE":/opt/data:z`, confirmed by reading it back from the host. Modes reset to 0600 to match the
  rest of the bundle.
- **Documentation defect that plausibly caused the spread:** `scripts/hermes/manual/README.md:69` states
  "socket; everything else uses `:Z` (private)". That is the stated policy these six lines were written
  under, and it is wrong for any directory shared with a second container.
- **MECHANISM PROVEN on the live host, by A/B measurement on scratch directories**, so the live tree was
  never touched. Two throwaway directories were created, labelled `container_file_t:s0`, and each mounted
  into the pinned image with one flag:
  - **`:Z`** → the container ran as `container_t:s0:c46,c189`, and afterwards **both the directory and the
    file it created** were `container_file_t:s0:c46,c189`. The private relabel lands on the *directory*, and
    the child inherits it.
  - **`:z`** → the container ran as `container_t:s0:c918,c1003` — a **different** pair, as expected — and
    afterwards both the directory and the file were `container_file_t:s0` with **no categories**.
  The second arm is the decisive one and independently re-confirms the inheritance model a fifth time: the
  creating process carried `c918,c1003`, yet the file it made came out `s0`, so the file inherited the
  **directory's** level and not the creator's — with the two values deliberately different, which the earlier
  confirmations could not distinguish. Both probe directories were removed (`probe_dirs_removed=yes`).
- **Consequence, stated precisely.** With `:Z` the shared directory becomes readable only by containers
  holding that exact category pair, so the next gateway instance — which always receives a fresh pair — is
  denied its own state DB and logs. With `:z` the directory is `s0`, and because an empty category set is a
  subset of every process's category set, any container can read it and the label is restart-stable. C36's
  six line changes are what move the five scripts from the first case to the second.
- **Still outstanding from this entry:** the `allowlist-swap` run that exercises `m05-tests.sh:67` on the
  real path. The mechanism is proven by the A/B; that run is the confirmation that the *fixed* script
  behaves under it.

### C37 — M05 operator tests

`priv=root` (operator), 2026-09-14 ~03:07Z (host local 22:07)

**Test 2 — an unauthorized account is ignored: PASS.**

- The swap ran cleanly: `saved_original=<redacted-telegram-user-id>`, `env_lines=10`, `gateway=active`,
  `allowlist_now=1`. **Operator-observed: the bot remained silent** when the authorized account sent a
  message while unauthorized. Operator-observed only, since the agent cannot see the Telegram client — but
  note the direction of this one: silence is the *absence* of an event, so unlike test 1 it cannot be
  confirmed by the agent at all.
- **C36 LIVE CONFIRMATION — the fixed mount does not relabel the shared directory.** After the swap,
  `/home/hermes/gateway-state` and its `.env` were still `system_u:object_r:container_file_t:s0` with **no
  MCS categories**. This is the real-path proof that C36's `:Z` → `:z` change works, because `allowlist-swap`
  calls `set_allowlist()`, whose line 67 is one of the six fixed lines. Under the old `:Z` this same
  operation would have private-relabelled the directory to the throwaway container's categories — which is
  precisely how the 21:40:11 denials were produced. The A/B proof on scratch directories (C36) predicted
  this; the live run confirms it.
- **No new denials:** `avc_today=14442`, unchanged, last denial still `21:40:11` — and that is measured
  across both a gateway restart and a state-directory mount that previously caused the C31 failure.
- **Byte accounting closes exactly again:** `.env` went 529 → **520** bytes, a delta of **−9**, which is the
  allowlist value shrinking from the 10-character account ID to `1` (1 character). Key count stayed **10**.
  The ID itself is redacted in this record; its **length** is kept, because the −9 delta is only checkable
  against it.
- **Order changed by design, and the record must not read it as corruption.** `set_allowlist()` filters the
  `TELEGRAM_ALLOWED_USERS=` line out and re-appends it, so it moved to the end:
  `… API_SERVER_KEY TELEGRAM_BOT_TOKEN TELEGRAM_ALLOW_ALL_USERS TELEGRAM_ALLOWED_USERS`. **The `.env`
  sha256 therefore does not return to `c720b21e…` even after the restore**, and that is expected. The
  integrity signals that actually matter are the key count (10), the size (529 again after restore) and the
  allowlist readback (`match=yes`). Recorded explicitly because a replicator comparing hashes will otherwise
  conclude the credential file was damaged by a test that in fact preserved it perfectly.
- **Restore verified, and every pre-commitment met.** `allowlist=<redacted-telegram-user-id>` restored,
  `saved_allowlist=none`, `saved_file=removed`, `gateway=active`, `worker=active`, both `ports=[]`. `.env`
  is back to **529 bytes** with **10 keys** — the exact inverse of the swap's −9 — and the label is still
  `system_u:object_r:container_file_t:s0` with no categories.
  `env_sha=b44b9fde4ebdeda61b5f07872202b0b6bbd70f2a1c89d3f13aa0625e7bf46f38`, deliberately **not**
  `c720b21e…`, because `TELEGRAM_ALLOWED_USERS` now sits last — which is precisely what the order note above
  predicted *before* the run, so the record does not have to explain the hash away after the fact.
  `avc_today=14442` unchanged, last denial still `21:40:11`.
- **On the `saved_file` check specifically:** it used `sudo bash -c 'test -f …'` rather than
  `[ -f /root/… ]`. Run as `aicowork`, the plain test would hit `/root`'s 0700 mode, fail, and print
  `removed` **whether or not the file existed** — a false negative on the one check that proves the
  credential-adjacent fallback file is gone. Same failure class as the `sudo ausearch 2>/dev/null` false zero
  and the `head`-masked `diff_rc`.
- **Test 2 therefore passes end to end, with a real before/after contrast on the same account:** silence
  while the allowlist held `1`, and a reply after the restore. The functional evidence for the restore does
  not depend on the printed `match=yes`, and the artifact detail confirms it independently.
- **Approvals policy in force for the next test**, read from the archived byte-identical `config.yaml`:
  `mode: manual`, `timeout: 300`, `cron_mode: deny`, `single_query_mode: deny`, `mcp_reload_confirm: true`,
  `destructive_slash_confirm: true`, with `security.redact_secrets: true`. The **300-second timeout** is the
  operationally important field: an unanswered approval prompt expires after five minutes, so a slow reply
  would look like a broken approval path when it is actually a timeout.
- **Still to run:** the approval-required action path, and the `worker-stop`/`worker-start` fallback test.

### C38 — M05 test 3: the first real tool round trip, and the approval question

`priv=root` (operator), 2026-09-14 ~03:12Z (host local 22:12)

- **The probe command was the agent's own bad choice, and its failure nonetheless proves the transport
  works.** `hostname` is the legacy binary and is absent from the minimal worker image; a shell builtin
  (`$HOSTNAME`) and `uname -n` exist, the command does not. The suggested probe should have been verified
  against the worker image before being issued. **The error is still decisive evidence**, because the
  journal records where it came from:

  ```text
  2026-09-14 03:12:54,047 WARNING agent.tool_executor: Tool terminal returned error (0.57s):
  {"output": "bash: line 5: hostname: command not found", "exit_code": 127, "error": null,
   "cwd": "/home/worker", "hint": "`hostname` is not installed or not on PATH. …"}
  ```

  **`"cwd": "/home/worker"`** is the worker's bind-mounted home
  (`/home/hermes/worker-state/home:/home/worker`), so the tool executed **on the worker over SSH** rather
  than locally in the gateway.
- **Independently confirmed by a presence contrast that makes the inference airtight.** The worker reports
  `NO_HOSTNAME_BINARY` while the gateway has `/usr/bin/hostname`, so a `command not found` for that name
  could only have originated on the worker. The two are also unambiguously distinguishable in general:
  `uname -n` gives worker `65cee893ac3b` and gateway `66f14cf878d1`.
- **The base images differ exactly as the guide's identity check assumes:** worker
  `NAME="Fedora Linux"` / `VERSION="44 (Container Image)"`, gateway
  `PRETTY_NAME="Debian GNU/Linux 13 (trixie)"`. This is the discriminator the record already leans on, now
  confirmed for both containers side by side in one run.
- **Full path proven end to end:** Telegram → gateway → tool executor → SSH → worker → error → back to
  Telegram, with the agent relaying the failure accurately (`exit_code: 127`, and the hint text it passed
  on). A *successful* command would be better evidence still, and is queued below.
- **OPEN — `approvals.mode: manual` did not visibly gate this call, but this is not yet established.** The
  tool executed and returned in **0.57s** with no approval-related line anywhere in the 60-line journal
  window (22:09:09–22:12:55) other than the tool result itself. That is consistent with the call never
  having been held for approval — which would contradict `approvals.mode: manual` and is a real finding if
  true. It is equally consistent with an approval prompt having appeared and been answered, which the
  gateway would not necessarily log. **The operator has not yet reported whether a prompt appeared**, and
  the agent cannot see Telegram. **RESOLVED by the operator's answer: NO prompt appeared — the bot simply
  ran the command.** The journal
  corroborates it: no approval-related line anywhere in the window, and the tool returned in 0.57s. So
  `approvals.mode: manual` did not gate a `terminal` tool call. **What that means is less certain than it
  first appears, and the record should not overclaim.** The guide mentions the gate exactly **once**
  (`docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md:653`, "the manual-approval gate") and `m05-telegram.sh:93` says
  only "Trigger an approval-required action" — **neither states which actions require approval.** The
  config's other approval-adjacent keys each name a specific gate: `mcp_reload_confirm`,
  `destructive_slash_confirm`, `cron_mode: deny`, `single_query_mode: deny`, plus
  `memory.write_approval: true` and `skills.write_approval: true`. That supports a reading in which
  `mode: manual` governs **how** approval is obtained rather than **which** actions need it — in which case
  no prompt for `terminal` is correct behaviour. **The defensible finding is therefore about the guide, not
  the gateway: step 9's third test is not verifiable as written**, because it names no triggering action, so
  an operator cannot distinguish "the approval path works" from "nothing I did required approval" — a test
  that cannot fail is not evidence. **Next step to settle it properly:** exercise an action the config
  *does* name as gated — a memory write (`memory.write_approval: true`) — and see whether a prompt appears.
- **The clean round trip SUCCEEDED.** Sent `cat /etc/os-release`; the bot returned `NAME="Fedora Linux"` /
  `VARIANT="Container Image"` — the **worker**, not the Debian-based gateway — and the journal shows the
  corresponding send at 03:15:25 with `final_len=719` and **no** `tool_executor` error line. Together with
  the `cwd: "/home/worker"` evidence above, the SSH terminal backend is now proven with a *successful*
  command and not only with a well-routed failure.
- **Observation — `gateway.run` logs a possible-duplicate-send warning on both replies:**

  ```text
  Normal final-send NOT suppressed despite active stream consumer for session
  agent:main:telegram:dm:<redacted-telegram-user-id>: streamed=False previewed=False content_delivered=False
  transformed=False final_len=57 — possible duplicate send (see wecom ack-timeout RCA).
  ```

  Present at 03:09:50 (`final_len=57`, the test-1 reply), 03:12:55 (`final_len=100`, the `hostname` error
  reply) and 03:15:25 (`final_len=719`, the successful os-release reply). **Operator answer: every reply
  arrived exactly once**, including the 719-character output — so the warning is **noise rather than
  duplication**. But it fires on **100% of sends** (three for three), which makes it a log-noise defect
  rather than an intermittent one: it will appear in every acceptance transcript and trains the reader to
  ignore the one line that would matter if duplication ever did occur.

### C39 — MAJOR FINDING: the approval gate enqueues the write, and the decision never reaches the operator

`priv=root` (operator), 2026-09-14 host local 22:18–22:21

- **What the operator did:** asked the bot over Telegram to "remember that the lab switch is a CRS310". The
  bot replied *"Updating memory +memory: …"* and *"I'll remember that the lab switch is a CRS310."*
- **What actually happened — the write was parked, not applied.** The gateway created
  `/home/hermes/gateway-state/pending/memory/4d827599.json` (341 bytes, 22:18):

  ```json
  {
    "id": "4d827599", "subsystem": "memory", "action": "add",
    "summary": "add to memory: The lab switch is a MikroTik CRS310.",
    "origin": "assistant_tool", "created_at": 1789355906.8587286,
    "payload": {"action": "add", "target": "memory",
                "content": "The lab switch is a MikroTik CRS310.", "old_text": null}
  }
  ```

  That is an **approval request**, not a memory record: it carries `subsystem`, `action`,
  `origin: assistant_tool` and a `payload`, and has **no status, no decision and no decider**. It remains
  undecided.
- **The committed store was never touched.** `/home/hermes/gateway-state/memories` has mtime **21:29**, not
  22:18. The memory was therefore **not written**, and the bot's *"I'll remember that"* is a **false
  confirmation** of a change that did not happen.
- **The gateway logged no approval activity whatsoever.** `grep -inE 'memor|approv|pending'` across
  `/home/hermes/gateway-state/logs/*.log` returned **nothing**, despite the gateway having just created a
  structured approval item. A queue that is written to but never mentioned in any log is invisible to
  precisely the operator this run is writing guidance for.
- **This resolves C38's open question, and in the opposite direction from the cautious reading taken
  there.** The gate **does** exist and **does** engage — but only for subsystems carrying an explicit
  `write_approval` flag. **No `pending/terminal` item was ever created**, which is why the earlier
  `terminal` call ran ungated. C38's mechanism claim ("`mode: manual` governs *how* approval is obtained")
  was right; C38 was wrong to leave the gate's *existence* in doubt, and is annotated accordingly.
- **The defect is in the decision path, and it is the worst kind for a guide:** the request is enqueued, the
  operator is never prompted, the queue cannot be drained from the interface the guide actually uses
  (Telegram), and the agent reports success. `approvals.timeout: 300` should have expired the request after
  five minutes; whether anything ever expires or cleans up this queue is the follow-up test.
- **Consequence for the acceptance criteria:** step 9's third test — "trigger an approval-required action
  and confirm the approval prompt/response path" — **cannot pass on this deployment**. Worse, the operator
  has no way to notice: they are told the memory was stored, and the agent's later behaviour simply will not
  include it.
- **Reverse:** delete `/home/hermes/gateway-state/pending/memory/4d827599.json` to clear the stuck request.
  Setting `memory.write_approval: false` would also stop the enqueuing, but this run should **not** do that:
  it would hide the defect rather than fix it, and it would silently diverge the config from the guide.
- **CORRECTION AND MAJOR REFRAME — the decision path exists; the guide simply never names it.** `hermes --help`
  lists **`approvals`** as a subcommand, alongside `memory`, `dashboard`, `logs`, `doctor`, `verify`, `send`,
  `sessions`, `cron` and many others. A pending approval **can** therefore be decided — from the CLI, inside
  the container — so the defect is **undocumented operator procedure, not a broken gateway**. Nothing in the
  guide or in any manual script mentions `hermes approvals`, and no Telegram prompt arrives, so an operator
  following the guide has no route to the queue at all. **C39's earlier framing ("the defect is in the
  decision path") is too strong and is corrected here:** the queue is decidable, just not from anywhere the
  guide points. The severity stands — a silent false confirmation is still a silent false confirmation — but
  the remedy changes from "fix the gateway" to "document the command".
- **`memories` is not merely stale, it is EMPTY.** `drwx------ 2 … 6 … /home/hermes/gateway-state/memories`
  with mtime 21:29:08 and **no entries**. Nothing has ever been committed to it, so the dropped write is not
  one memory among many: the agent's memory holds **nothing at all** while the bot tells the operator it has
  remembered something.
- **The only listening socket inside the gateway container is `127.0.0.1:8642`.** From `/proc/net/tcp`,
  state `0A` (LISTEN), uid 10000 — loopback-only, and the container publishes no port, so it is unreachable
  from the host or the LAN. This is consistent with the dashboard hypothesis and with C35's finding that
  `HERMES_DASHBOARD=0` does not stop the dashboard service, though the socket's owner is not yet identified.
  The same table shows the container's outbound 443 connections to `149.154.166.110` (Telegram) and
  `162.159.140.245` (Cloudflare, consistent with the DoH fallback-IP discovery the adapter logs), which
  independently confirms egress and the polling transport.
- **CORRECTION TO THE AGENT'S OWN CLAIM IN THE PREVIOUS BLOCK.** I stated the request was "already past 300
  seconds old" before running the timeout test. It was **271 seconds** — under the timeout. **The timeout
  test is inconclusive and must be re-run**, and the claim is withdrawn rather than left standing. This is
  the fifth agent-side estimation/instrument error of the run and the same class as the others: asserting a
  computed value without computing it.
- **TIMEOUT TEST — DEFINITIVE, and the queue is never swept.** Re-run with
  `pending_age_seconds=387`, well past the 300-second window. `4d827599.json` is still present, still
  341 bytes, same 22:18 mtime, **still undecided with no status field**. So `approvals.timeout: 300` does
  **not** expire, deny or clean up pending requests: an undecided request persists indefinitely and the
  queue only ever grows. For an operator this means every "remember this" they send is parked forever,
  silently.
- **`memories_entries=0`** — the committed store is confirmed empty, exactly as predicted, so the dropped
  write is not one lost item among many.
- **RE-CORRECTION — the agent's own "reframe" in the previous block was WRONG and is withdrawn.**
  `hermes approvals --help` returns:
  *"Tools for the dangerous-command approval system. `hermes approvals suggest` mines past approval
  decisions from the session database and proposes command_allowlist entries so repeatedly-approved commands
  stop prompting"*, with exactly two subcommands — **`suggest`** and **`test`**. There is **no list, no
  approve, no reject**, and no relationship to the memory pending queue. I inferred a decision path from a
  single word in a long command listing, without reading that command's own subcommands, and then used the
  inference to soften C39. **C39's original framing therefore stands: no route to decide a pending memory
  approval has been found.** Two agent errors are now recorded against C39 — the mis-computed timeout claim
  and this over-read — and both are the same failure: treating an unverified inference as a finding.
- **NEW SUBSTANTIVE DISCOVERY — a second, separate approval subsystem the record did not know about.** The
  "dangerous-command approval system" maintains a `command_allowlist` and exposes
  `hermes approvals test <command>`, which **dry-runs the verdict without executing anything** and returns
  exit **0 = allow / 2 = ask / 3 = deny**. This is the tool that can settle C38's open question about whether
  `terminal` commands are approval-gated at all, and it is the mechanism `approvals.mode: manual` most
  plausibly governs — quite distinct from the `write_approval` queue that swallowed the memory.
- **The dashboard runs and answers HTTP despite `HERMES_DASHBOARD=0`.** `curl http://127.0.0.1:8642/` returns
  `http_code=404`, so a real HTTP service is listening there; the container's process table shows
  `/proc/24 s6-supervise dashboard`, and the socket is loopback-only on an unpublished port. This
  strengthens C35 finding 3 from "the service starts" to "the service starts **and serves HTTP**", while
  remaining unreachable from the host or LAN.
- **No new AVC denials across all of this activity:** `avc_today=14442`, last denial still `21:40:11`, with
  both containers up and `ports=[]`. The C36 `:z` fix continues to hold.
- **Agent-side efficiency note:** rather than asking the operator to paste privileged output, the probe was
  written to the host as `/home/aicowork/hermes-m05-approval-probe.sh` (sha256
  `0a481eb3749c8102dc3b3365b25d1f0ac9de613200d93407198db7094616e6a4`, mode 700), read-only, and it chowns its
  own output to `aicowork`. The operator runs **one command** and the agent reads the result over SSH. This
  is the pattern for every remaining privileged check in this run.

### C40 — M05 test 3 resolved: the dangerous-command gate works, and the guide never says to use it

`priv=root` (operator, via read-only probe), 2026-09-14 ~03:25Z

- **The dangerous-command approval system is functional.** `hermes approvals test` dry-runs a verdict
  without executing anything:

  | Command | Exit | Verdict | Rule |
  | --- | --- | --- | --- |
  | `cat /etc/os-release` | 0 | allow | no guard matched; would run without a prompt |
  | `ls -la /tmp` | 0 | allow | no guard matched |
  | `curl http://example.com` | 0 | allow | no guard matched |
  | `rm -rf /tmp/hermes-probe-nothing` | **2** | **ask-approval** | **delete in root path** |
  | `systemctl restart sshd` | **2** | **ask-approval** | **stop/restart system service** |

- **C38 IS RESOLVED AS NO DEFECT, and its earlier framing is withdrawn.** The `hostname` call that produced
  no prompt was **benign**, and `cat /etc/os-release` is too — the gate allows both by design and would
  raise an interactive prompt only for a dangerous pattern. So "no approval prompt appeared" was **correct
  behaviour**, not a broken gate, and the whole of C38's uncertainty on that point can be closed. What
  remains is a **narrow documentation defect**: step 9 instructs the operator to "trigger an
  approval-required action" without ever saying that this means a *dangerous* command. Any benign tool call
  will pass silently, so an operator following the guide literally would conclude the gate is missing when
  it is working.
- **`hermes memory` offers no route to the pending queue either.** Its subcommands are `setup`, `status`,
  `off` and `reset`. Combined with `hermes approvals` exposing only `suggest` and `test`, **C39's conclusion
  stands: there is no decision interface for a parked memory approval on this host.**
- **The dashboard/approval-UI hypothesis is FALSIFIED.** On `127.0.0.1:8642` inside the container, only
  `/health` returns **200**; `/`, `/api`, `/api/approvals`, `/approvals`, `/pending`, `/api/pending`,
  `/status` and `/dashboard` all return **404**. It is a health endpoint, not an approval surface, so the
  earlier attempt to tie the stuck queue to the unreachable dashboard is dead. The dashboard/HTTP service
  itself remains loopback-only and unpublished.
- **`hermes approvals suggest`** reports *"No allowlist candidates found in approval history (last 90 days)"*,
  confirming an approval history exists and is being mined, and that nothing dangerous had been approved
  often enough to propose an allowlist entry.
- **NEWLY EXPOSED WEAKNESS IN C39's OWN EVIDENCE, flagged not buried.** `hermes memory --help` states that
  the **built-in** memory is `MEMORY.md`/`USER.md` and "is always active". That means the `memories/`
  directory C39 relied on — empty, mtime 21:29 — **may not be the store this write would have gone to**, so
  "`memories` was never touched" may have been evidence aimed at the wrong path. C39's *conclusion* is
  unaffected, because the undecided pending request is independent proof that the write was parked, but the
  supporting evidence is weaker than C39 states and is being verified rather than left as-is.
- **Probe 3 CLOSES the C39 evidence weakness — and the corrected evidence is stronger than the original.**
  **No `MEMORY.md` and no `USER.md` exists anywhere** under the state tree (a depth-5 search found none), so
  the agent's built-in memory is not merely empty, it has **never been created**. The string `CRS310` appears
  in exactly four places: `logs/agent.log`, `logs/gateway.log`, `pending/memory/4d827599.json` and
  `state.db-wal`. **None of them is a memory store** — three are conversation history and one is the parked
  request itself. The write therefore genuinely never landed, now on correctly-targeted evidence rather than
  on a directory that may have been the wrong one.
- **The parked request is still the only pending item, ~69 minutes old.** The queue holds exactly one file,
  unchanged: nothing has decided it, expired it, or cleaned it up.
- **The loopback HTTP service is the gateway's own aiohttp API.** `agent.log` records the probe's requests as
  `aiohttp.access: 127.0.0.1 "GET /api/approvals HTTP/1.1" 404`, so the surface on 8642 is an aiohttp
  application with an `/api/` namespace and a `/health` endpoint — and the probe is auditable in its own
  access log. **Note for the record:** `.env` carries `API_SERVER_ENABLED=false` while this API is
  listening, the same shape as `HERMES_DASHBOARD=0` failing to stop the dashboard. Whether that flag is meant
  to suppress this internal surface is **not established**, and exposure is nil because the socket is
  loopback-bound and the container publishes no port. Recorded as an **observation, not a finding**.
- **Test 3 (properly) and the worker-failure fallback are now being run in a single scripted pass**, with the
  worker restart guarded by a `trap` so an interrupted run cannot leave it stopped.
- **A genuine end-to-end test 3 is now possible and is queued:** have the bot run a command that trips a
  guard (`rm -rf /tmp/hermes-probe-nothing`, harmless because the path does not exist) and confirm an
  interactive approval prompt actually arrives in Telegram, then approve it. That exercises the prompt and
  response path the guide asks for, using the gate we have now proven exists.

### C41 — M05 operator tests: the approval path and the worker fallback — BOTH PASS

`priv=root` (operator, interactive), 2026-09-14 ~03:28–03:29Z

**Test 3 — the approval prompt/response path: PASS, delivered as a Telegram button.**

```text
03:28:27 inbound message: platform=telegram chat=<redacted-telegram-user-id> msg='run the command rm -rf /tmp/hermes-probe-nothing'
03:28:30 tools.terminal_tool: Creating new ssh environment for task session:...
03:28:30 tools.environments.base: Session snapshot created (session=25dadfef8f7a, cwd=/home/worker)
03:28:36 hermes_plugins.telegram_platform.adapter: Telegram button resolved 1 approval(s) for session
         agent:main:telegram:dm:<redacted-telegram-user-id> (choice=once, user=X)
03:28:36 agent.tool_executor: tool terminal completed (6.56s, 138 chars)
03:28:38 Turn ended: ... response_len=31
```

- The prompt **is** delivered to Telegram, **as a button**, and the answer was recorded as `choice=once`.
- `rm -rf /tmp/hermes-probe-nothing` executed and the path is still absent
  (`ls: cannot access ... ABSENT_AS_EXPECTED`), so the test had no side effects.
- **Step 9's third criterion now genuinely passes and C38 is fully closed:** the gate classifies, prompts,
  and resolves. **The guide's only fault is that it never says "dangerous command"** — a benign tool call
  passes silently by design, so an operator following the wording literally would wrongly conclude the gate
  is missing.
- **This materially strengthens C39 by contrast.** Both mechanisms live under `approvals:` in the same
  configuration and behave nothing alike:

  | Mechanism | Prompt delivered? | Decided? |
  | --- | --- | --- |
  | dangerous command (command_allowlist machinery) | **YES — Telegram button** | **YES — `choice=once`** |
  | memory write (`memory.write_approval: true`) | no | no — parked 70+ minutes |

  The delivery path demonstrably **exists and works** in this deployment; the memory `write_approval` queue
  simply does not use it. That is a far stronger statement than "no route to the queue was found", and it
  localises the defect to the memory queue's notification rather than to approvals as a whole.

**Test B — the worker-failure fallback: PASS, with no silent local execution.**

```text
03:29:16 WARNING agent.tool_executor: Tool read_file returned error (0.14s):
         {"content": "", "total_lines": 0, ..., "error": "Terminal environment unavailable:
          could not stat /etc/os-release (the sandbox may ..."}
03:29:21 Turn ended: ... response_len=151
```

- With the worker stopped (`worker_state=failed`, `socket_present=no`), the request **failed cleanly** with
  `Terminal environment unavailable`. **No `Fedora Linux`** (which would mean it reached the worker) and
  **no `Debian`** (which would mean it silently ran locally in the gateway).
- That second case was the failure mode worth testing: an operator believing commands are confined to a
  `Network=none` worker while they actually execute in the internet-connected gateway. **The confinement
  holds.**
- The tool actually selected was `read_file`, not `terminal`, and it routes through the same SSH sandbox — so
  the confinement covers both paths rather than only the obvious one.
- Worker restored: `worker_after=active`, socket present (`srw-rw-rw-`, `container_file_t:s0`), and
  `hermes-worker | Up 6 seconds`. As in C33, stopping the worker leaves the unit `failed` rather than
  `inactive`; `systemctl start` clears it.
- **No new AVC denials** (`avc_today=14442`, last `21:40:11`), both containers up with `ports=[]`, and the
  pending queue still holds exactly the one parked memory request.

### C42 — M04 step 10 (M04a): read-only gateway root — PASS, with the Telegram check the script omits

`priv=root` (operator), 2026-09-14 ~03:32Z

- **Preflight established this is a confirmation rather than a new change.** The bundle's
  `quadlets/hermes-gateway.container` already carries `ReadOnly=true`, `Tmpfs=/run`, `Tmpfs=/tmp`
  (lines 21-23) and `:z` on line 26, and hashes to
  `f3aa44612b694d50b8c9fc404de597b14be9954199c16dc2773a17d49104f421` — byte-identical to the repo copy and
  the same revision C31 fixed. `m03-activate.sh` installed from that same bundle path, so step 10 reinstalls
  the identical file. **No `:Z` landmine**, which was the risk worth checking: had the read-only variant
  carried the old `:Z`, installing it would have re-broken exactly what C36 just fixed.
- **Result `RESULT=PASS`, confirmed independently rather than taken on the script's word:**
  - Write probes inside the **running** gateway: `READONLY_OK` (literally
    `touch: cannot touch '/m04-verify-probe': Read-only file system`), `RUN_WRITABLE_OK`,
    `DATA_WRITABLE_OK`.
  - `podman inspect` → `readonly_rootfs=true`, `tmpfs=map[/run:… /tmp:…]`.
  - Installed unit still hashes to `f3aa4461…`.
- **The script's own Telegram check is weaker than it reads, and the wrapper compensated.** `telegram_state()`
  greps the last 200 journal lines with **no `-b`**, so a connection logged during an *earlier* boot can
  satisfy it — which is how a restarted-but-disconnected gateway would still be reported as passing. The
  independent check, bounded by a timestamp marker taken before the run, gives
  `telegram_connect_events_since_mark=1` and `telegram_connect_events_this_boot=4`, with the journal showing
  the restart at `22:32:01` and `[Telegram] Connected to Telegram (polling mode)` at `22:32:17` — **after**
  the restart. So the gateway genuinely reconnected; the number is not a stale line.
- **SELinux undisturbed:** `gateway-state` and `.env` remain `container_file_t:s0` with no MCS categories
  after `restorecon` ran on the installed unit.
- **`avc_today=14442`, last denial still `21:40:11`**, both containers up with `ports=[]`.
- **Next: step 11 (M04b1)** — `m04-reboot.sh`, then a reboot **at the console**. This is the first boot with
  the application present, and the real test of `[Install] WantedBy=default.target` plus lingering: whether
  both containers come back **unattended**, with the TPM unlocking without a passphrase.

### C43 — M04 step 11 (M04b1): unattended reboot with the application present — PASS

`priv=root` (operator) + console, 2026-09-14 ~03:47Z

- **`boot_id` changed** from `4e97672b-b62b-4259-bc17-79ec7d2db0e1` to
  **`5c26f346-8f01-446a-b50e-397a0ccca086`**, with `uptime` reading "up 0 minute" on first contact. A real
  reboot, verified rather than assumed — the same discipline that caught the earlier false B1 completion.
- **Both containers autostarted with no intervention whatsoever.** `ps` over SSH, before any operator action,
  already showed `conmon … -n hermes-worker` and `-n hermes-gateway`. **That is precisely the property step
  11 exists to test:** `[Install] WantedBy=default.target` plus lingering brought the entire application back
  on its own, so M04b1 passes on its own terms rather than on a script's verdict.
- **No passphrase was requested at the console**; the boot completed unattended, consistent with C22 and C25.
- **No new host exposure:** listeners remain 22, 53 (×2) and 5355 only.
- **Pre-reboot state captured by the script:** `gateway_enable_state=generated`,
  `worker_enable_state=generated`, `linger=hermes`, `gateway=active`, `worker=active`,
  `worker_started=2026-09-13 22:29:59`, `gateway_started=2026-09-13 22:31:53`. Worth knowing before anyone
  reads it as a failure: **Quadlet-generated units report `generated`, not `enabled`**, because the
  `[Install] WantedBy=default.target` directive is realised by the generator rather than by a symlink in
  `*.wants/`.
- **DEFECT — the script's own header is stale and contradicts the boot track it follows.** It states "The host
  requires the LUKS passphrase at the console, so run this only when the operator is physically at the
  console." That was true before B3 and is **false now**: C22, C24 and C25 proved the TPM2 token unlocks
  unattended, including across an AC power-pull. An operator who believes the header might read a clean
  unattended boot as a failure, or wait at the console for a prompt that never arrives. Same class as the
  other stale documentation this run has recorded.
- **Cosmetic defect — `user_manager` prints two lines.** Line 52 is
  `h systemctl --user is-active "user@$HERMES_UID.service" 2>/dev/null || systemctl is-active …`. The `h`
  wrapper's stderr is discarded but its stdout (`inactive`) is still captured, so the output is
  `user_manager=inactive` followed by a bare `active` on the next line, and the value a reader takes depends
  on which line they read. The system-level answer `active` is the correct one.

### C44 — M04 step 12 (M04b2): autostart proven; the probe failure is an SELinux label, and step 13 is its repair

`priv=root` (operator), 2026-09-14 ~03:49Z

- **Autostart PROVEN, which is precisely what M04b2 exists to test.** `boot_time=2026-09-13 22:47:11`
  against both containers' `StartedAt=22:47:35` — **+24s** — and the wrapper's comparison reports
  `STARTED_THIS_BOOT (autostart proven)` for **both**. `boot_changed=yes`, `user_manager=active`,
  `linger=hermes`, both units `active`, worker socket present. This is the check the script omits, and it is
  the difference between "running" and "autostarted".
- **No passphrase prompt:** boot at `22:47:11` to containers at `22:47:35` is 24 seconds end to end, and a
  passphrase prompt blocks until answered. **Note the wrapper's `ask_password_activations_this_boot=8` is NOT
  evidence of a prompt** — the grep matched the bare string, which also matches the benign
  `systemd-ask-password-console.path` / `-wall.path` units every systemd host starts at boot. That count is
  **the agent's instrument being too loose**, recorded as such rather than as a finding; classification of
  the individual lines is queued as probe 4.
- **Failed units: NONE in either manager.** The wrapper added the user-manager check the script omits, and
  both the system and user lists are empty.
- **The `probe_rc=2` failure is now explained, and it is not an unknown stage condition.** The AVC denial:

  ```text
  avc: denied { read } for pid=1828 comm="python3" name="m03-probe.py" dev="dm-3" ino=2660436
  scontext=system_u:system_r:container_t:s0:c423,c1012
  tcontext=unconfined_u:object_r:user_home_t:s0 tclass=file permissive=0
  ```

  with the probe's own error: `can't open file '/opt/hermes/gateway-ssh/m03-probe.py': [Errno 13]
  Permission denied`. `m04-postboot.sh:83` installs the probe into the `:Z`-mounted `gateway-ssh` **after**
  the gateway has started, so the new file keeps the host's path-based default label **`user_home_t`** —
  `/home/hermes/...` matches the policy's user-home rule — instead of `container_file_t`, and `container_t`
  is denied `read`.
- **This is documented — in step 13, not step 12, and the agent's first framing is withdrawn.**
  `m04-postboot-probe.sh`'s header states the mechanism exactly: *"a file created afterwards keeps the host
  default label (user_home_t) and container_t is denied read. This script labels it like its siblings and
  re-runs the probe."* It then runs `chcon --reference="$GWSSH/known_hosts" "$PROBE"` and re-runs, with a
  gateway restart as fallback. **So the failing probe at step 12 is by design and M04b3 is its repair**; any
  claim that the transport probe is simply broken is **withdrawn**.
- **What remains a genuine defect, stated narrowly:** (1) `m04-postboot.sh` prints a **failed transport probe
  with no note that the failure is expected** — the explanation lives in a different script's header, so a
  literal reading of step 12's output is "the transport broke after the reboot"; (2) it emits a **new AVC
  denial on every run**, and Phase 7's acceptance criterion is "no new AVC denials", so this by-design denial
  is indistinguishable from a real regression unless it is baselined; (3) the fix is **one line** — relabel
  the file where it is installed, or install it before the gateway starts — which would let step 12's probe
  pass, remove the denial, and make step 13's repair unnecessary.
- **Baseline updated: `avc_today=14443`**, the one new denial being the by-design one above at `22:49:06`.
  **Phase 7's check must therefore look for denials occurring after Phase 7 begins, not count today's
  total.**
- **Integrity holds:** `.env` still 529 bytes with 10 keys, mode 600, owner `599823:599823`;
  `gateway-state` still `container_file_t:s0`; and the parked approval `4d827599.json` **survived the
  reboot** unchanged — so the stuck queue is durable across a reboot, not merely long-lived.

### C45 — M04 step 13 (M04b3): the relabel repair works and the transport is proven after a reboot

`priv=root` (operator), 2026-09-14 ~03:50Z

- **`chcon --reference` succeeded and was sufficient on the first attempt.** `chcon_rc=0`;
  `m03-probe.py` went from `unconfined_u:object_r:user_home_t:s0` to
  `system_u:object_r:container_file_t:s0:c423,c1012`, matching its siblings. **The gateway-restart fallback
  never ran.**
- **The probe passes end to end inside the running gateway:**

  ```text
  resolved_backend=ssh
  execute_returncode=0
  execute_output=HERMES_WORKER_ROUNDTRIP_OK
  worker
  NAME="Fedora Linux"
  RESULT=PASS
  probe_rc=0
  ```

  with `backend_lines=1` confirming the profile still asserts the SSH backend. **This is the strongest
  transport evidence in the run:** it exercises the production code path inside the running gateway, over
  SSH, to the `Network=none` worker, **after a reboot** — not a one-shot container invocation.
- **The label contrast is the clearest illustration of the C36 class yet.** Before the fix, every file in
  `gateway-ssh` was `container_file_t:s0:c423,c1012` — `known_hosts`, `ssh`, `scp`, `sftp`,
  `unix-bridge.py`, `set-model.py`, `manual-harden-config.py`, `worker_client_ed25519` and its `.pub` — and
  **only** the freshly-installed `m03-probe.py` was `user_home_t`. One file, created after the container
  started, in a directory whose label every sibling already carried.
- **No second AVC denial.** The `recent AVC denials` section shows only the by-design denial from C44 at
  `22:49:06`, so step 13 repaired the situation without adding to the journal.
- **RESOLVED — `ask_password_activations_this_boot=8` was the agent's grep being too loose, exactly as
  suspected.** All eight lines are watch/socket units, not a prompt: three
  `systemd-ask-password-console.path … skipped, unmet condition check ConditionPathExists=!/run/plymouth/pid`,
  one `Started systemd-ask-password-plymouth.path` (a **`.path`** watch, **not** the `.service`), one
  `Started systemd-ask-password-wall.path`, and three
  `Listening on systemd-ask-password.socket - Query the User Interactively for a Password`. **None is an
  activation of `systemd-ask-password-plymouth.service`**, which is the exact marker C23 used for the
  fallback boot. Independent corroboration: `systemd-analyze` reports 34.704s total startup with no
  blocking. **No passphrase was requested; the count is withdrawn as evidence.**
- **INSTRUMENT PROBLEM, and it is retroactive — the `-ts 'MM/DD/YYYY HH:MM:SS'` form returned a FALSE ZERO.**
  Probe 4's section 4 printed **nothing** for all denials since 22:45 and reported `avc_since_2245=0`, while
  that same window demonstrably contains the `22:49:06` denial. `2>/dev/null` hid the reason.
  **This matters beyond probe 4:** an earlier block used the identical form
  (`-ts 09/13/2026 21:44:00`) and recorded `0` as evidence that no denials followed the gateway restart.
  That conclusion remains supported by the `-ts today` timestamp *tail*, which showed the last denial at
  `21:40:11` — but **the `-ts` count itself was never valid evidence**, and the form is quarantined pending
  the test now queued. This is the sixth agent-side instrument error of the run and the same family as the
  rest: a command that reports a confident number while having failed.

### C46 — M04 step 14: b4-verify recheck — PASS on every independent assertion

`priv=root` (operator), 2026-09-14 ~03:52Z

- **PCR7 is UNCHANGED across the seventh boot, and `PCR7_MATCH=NO` was the agent's transcription error.**
  The check reported `len_pcr=64 len_expected=63`: the value **the agent typed into the script** was one
  character short — the `E` was dropped from `…A82CEFBF…`. Both the JSON and this ledger record the full
  64-character value `22103EAC50D6EF26DABCBA626A8E70754586CE66D600563A82CEFBF2CA206A73`, which is
  **exactly what the host reports**. So PCR7 is byte-identical on this boot as on the previous six and no
  Secure Boot policy state has changed. The workstation's own PCR7 reads `EF99FE48…`, confirming that local
  and remote reads are of different machines.
  **Rule recorded:** an expected value retyped inline is **itself an instrument**, and this one failed. A
  comparison of this kind must read the expected value **out of the evidence record** rather than restating
  it, so the two cannot drift. This is the seventh agent-side instrument error of the run.
- **The `ausearch -ts` false zero is confirmed and explained.** The form is rejected outright:

  ```text
  --- a) -ts 09/13/2026 22:45:00 ---
  Error parsing start date (09/13/2026)
  ```

  while `-ts today` returns `14443` and `-ts recent` returns `1`. So `-ts 'MM/DD/YYYY HH:MM:SS'` is
  **unusable on this host**, which retroactively invalidates every count built on it — including the earlier
  "0 denials since 21:44" record. That conclusion survives only because the `-ts today` timestamp *tail*
  independently showed `21:40:11` as the last denial at the time. Any future windowed AVC check here must
  use `-ts today`/`-ts recent` plus a timestamp comparison, or an epoch argument.
- **`b4-verify.sh` exits 0, exactly as the record predicted** (`b4_verify_exit=0`). It has no assertion path,
  so **its exit code carries no information at all**, and the runbook's description of it as a re-assertion
  is wrong. Everything below comes from the independent assertions instead.
- **All independent assertions pass:**
  - **TPM2 policy exactly as specified:** `keyslots=2`, `tpm2_tokens=1`, `tpm2-hash-pcrs: 7`,
    `tpm2-pcr-bank: sha256`, `tpm2-pin: false`.
  - **Volume identity guarded before any device path:** `luks_uuid=8919c2b1-5d9a-4fb9-8f85-97d286cbe7ec` —
    the server volume, not the workstation's.
  - **`SecureBoot enabled (user)`.**
  - **Zero failed units in both managers:** `system_manager_failed=0`, user-manager list empty.
  - **`telegram_connected_this_boot=1`** — the gateway reached Telegram on this boot.
  - **`probe_rc=0`**, and its own log line shows the probe file now carrying
    `context=system_u:object_r:container_file_t:s0:c423,c1012`, so **C45's relabel persisted** — the fix is
    durable, not momentary.
  - Both containers up with `ports=[]`; listeners limited to 22, 53 and 5355; `.env` 529 bytes with 10 keys;
    `gateway-state` still `container_file_t:s0`.
- **AVC baseline for Phase 7: `avc_today=14443`** — 14442 historical, all at or before `21:40:11`, plus
  **1** at `22:49:06` which is the by-design step-12 denial. **Phase 7 must therefore compare against the
  `22:49:06` watermark, not against zero.**

### C47 — PHASE 7 FINAL ACCEPTANCE: PASS on all five criteria

`priv=root` (operator) + console, 2026-09-14 ~03:54Z

- **The power cycle was real and orderly.** `boot_id` moved `5c26f346-8f01-446a-b50e-397a0ccca086` →
  **`743ac226-999b-4f0e-acb4-7c64446ea102`**, `boot_time=2026-09-13 22:53:55`, `uptime` "up 0 minute" on
  first contact. The sequence was a clean `systemctl poweroff`, then **AC pulled at the wall**, then
  restored — not a reboot.
- **NO KEYBOARD INPUT — proven, not asserted.** `plymouth_prompt_service_lines=0`:
  `systemd-ask-password-plymouth.service`, the actual prompt unit, was **never activated** on this boot.
  This is the correct marker — the `.service`, not the `.path` watch whose loose match produced C45's false
  count — and it is the difference between "the machine restarted" and "the machine restarted
  **unattended**", which is the entire claim of Phase 4/B4.
- **PCR7 UNCHANGED across the AC cycle:** `22103EAC50D6EF26DABCBA626A8E70754586CE66D600563A82CEFBF2CA206A73`,
  byte-identical to the recorded value now across **eight** boots. The TPM enrollment's measurement remains
  valid.
- **CRITERION 1 — both containers running: PASS.** `worker=active`, `gateway=active`, and **both
  `STARTED_THIS_BOOT`** — worker `22:54:18`, gateway `22:54:19`, against boot `22:53:55`, i.e. **+23s and
  +24s**. They autostarted from `[Install] WantedBy=default.target` plus lingering with no human
  involvement whatsoever.
- **CRITERION 2 — transport probe returns the worker's Fedora identity: PASS.**
  `resolved_backend=ssh`, `execute_returncode=0`, `execute_output=HERMES_WORKER_ROUNDTRIP_OK`, `worker`,
  `NAME="Fedora Linux"`, `RESULT=PASS`.
- **CRITERION 3 — Telegram replies: PASS, operator-confirmed** after the power cycle. This is the one
  criterion the host cannot self-report, and it is the proof that the messaging path survived a full
  power loss.
- **CRITERION 4 — no published ports beyond sshd and systemd-resolved: PASS.** `podman port hermes-gateway`
  returns nothing; the only host listeners are `sshd` (22) and `systemd-resolve` (53 ×2, 5355).
- **CRITERION 5a — no failed units: PASS in both managers.** `system_manager_failed=0`; the user-manager
  list is empty.
- **CRITERION 5b — no new AVC denials: PASS.** `avc_today=14443`, unchanged, and the last five denial
  timestamps are all `21:40:11` except the single by-design `22:49:06` from C44. **Nothing after the
  watermark**, so neither the power cycle nor the unattended boot introduced one.
- **Supporting evidence:** TPM2 token intact (`0: luks2`, `1: luks2`, `tpm2-hash-pcrs: 7`,
  `tpm2-pcr-bank: sha256`, `tpm2-pin: false`), `SecureBoot enabled`, `.env` 529 bytes / 10 keys / mode 600 /
  owner `599823:599823`, `gateway-state` still `container_file_t:s0`. **The parked approval
  `4d827599.json` survived the AC cycle unchanged**, so C39's stuck queue is durable across a full power
  loss.
- **B6 IS THEREFORE COMPLETE ON THE HOST SIDE.** The boot track (B1-B5), the application deployment
  (M02-M05), M04 steps 7-14 and Phase 7 have all been executed on this machine. What remains is Phase 8 —
  consolidating the record and producing the handoff — plus the two open items named in `not_yet_done`.

### C48 — Fresh application-state backup of the fully configured gateway

`priv=root` (operator) + agent, 2026-09-14 ~03:59Z

- **A ZERO-DIFF backup — a stronger result than step 7's.** `m04-backup.sh` was run again against the
  post-Phase-7 state, then both of its known defects were compensated for; critically, **the corrected diff
  ran while the gateway was still stopped**, so the tree was frozen:
  - **`TRUE_diff_rc=0` with `diff_lines=0`** — **not one differing path**. Step 7's equivalent produced 30
    lines of runtime churn plus ten truncation-hidden symlink errors, because the gateway had been restarted
    before that comparison was made.
  - **`restored_symlinks=13`**, matching the prediction for the third time.
  - **`IDENTICAL: config.yaml (3678 bytes)`** and **`IDENTICAL: .env (529 bytes)`**, byte-compared.
  - `restore_test_dir_removed=yes`, `rediff_dir_removed=yes`.
- **Archive identity:** `/home/aicowork/hermes-app-backup-20260914T035903Z/app-state.tar`,
  **110,520,320 bytes**, sha256
  `67c35be354dc6fb185fdce4d7a384566ebf2a12b544da126fd16432fd7c3adb4`. The manifest records
  `gateway_config_sha256=072e3a0b…` — unchanged since 21:35, confirming the gateway does **not** rewrite
  `config.yaml` at runtime — and `env_file_sha256=b44b9fde…`, the current 10-key `.env` including
  `TELEGRAM_*`.
- **The gateway was restored to service:** `gateway=active`, `telegram_connected_this_boot=1`, both
  containers up with `ports=[]`. **`avc_today=14443` unchanged**, so stopping and restarting the gateway
  produced no denial — another datapoint that the C31/C36 label fix holds under a further cycle.
- **Off-host transfer, hash-verified, and only then the host copy deleted.** Pulled to
  `private/hermes-app-backups/20260914T035903Z/`; the local archive re-hashes to exactly the recorded value,
  *and only on that match* was the host directory removed. `host_copy=removed`, and **no
  `hermes-app-backup-*` directories remain on the host at all**.
- **Layout tidied and both archives re-verified.** The step-7 pair was moved into
  `private/hermes-app-backups/20260914T024351Z/` so each archive identifies itself by timestamp. Both re-hash
  to their recorded values — `0a61e03f…` (step 7) and `67c35be3…` (fresh) — and `private/` remains entirely
  gitignored (`.gitignore:74`) with **0** private paths in `git status`.
- **Sensitivity note:** this archive contains **both** the Telegram bot token and the OpenAI key, so it is a
  heavier credential artifact than the step-7 archive. It now exists in exactly one place — the
  LUKS-encrypted workstation — which is the intended state.
- **Reverse:** delete `private/hermes-app-backups/20260914T035903Z/` to remove the post-configuration
  recovery point. Restoring from it is a `tar -xpf` into `/`, per C33's reverse.

### C49 — Phase 8: the B6 clean-install handoff

`priv=none` (agent), 2026-09-14 ~04:05Z

- **Deliverable:** `docs/HERMES_B6_CLEAN_INSTALL_HANDOFF.md`, modelled on the nine-section structure of
  `docs/HERMES_MANUAL_HANDOFF.md` but written for **this** install.
- **Why a new document rather than an in-place edit:** the existing handoff describes the *previous* install
  of the same host, and `AGENTS.md` asks that existing material be preserved. The new file states explicitly
  that it **supersedes** that file's B6 row — which still reads `⬜ TODO` — and the sections this run has
  changed. **Nothing existing was overwritten.**
- **What it carries that the template could not:**
  - the **measured** SELinux inheritance rule and the resulting `:z`/`:Z` decision, replacing the template's
    "learned the hard way" note with the mechanism and the eight corrected sites;
  - the correction that the **Quadlet `Environment=` lines are authoritative**, not the `config.yaml` keys
    the guide writes and Hermes reports as unrecognised;
  - the dangerous-command approval verdicts, and the fact that the guide's acceptance step must use a
    **dangerous** command or no prompt will ever appear;
  - the **zero-diff backup verification method**, required because `m04-backup.sh`'s own check cannot fail
    and because 13 uv-cache symlinks make a naive `diff -r` report spurious errors;
  - the verified worker-failure containment result — no silent local fallback, for `read_file` as well as
    `terminal`;
  - twelve explicit limitations and a **separate section of six items that remain unverified**, which Phase 8
    requires be stated rather than implied.
- **The stalest claim in the template is now closed:** its evidence index reads
  `| B6 (clean-install validation) | docs/HERMES_BOOT_CLEAN_INSTALL.md | ⬜ TODO |`. This run performed that
  validation, and the handoff records it as done with the evidence trail behind it.

### Pre-Step-4 baseline — the "before" for every change still to come

Captured read-only just before C9, so each later change has a diff-able starting point.

| Item | Value before host preparation |
| --- | --- |
| static hostname | *(unset — empty)* |
| transient hostname | `hermes.ai.lab.local` |
| `/etc/systemd/journald.conf.d/` | **does not exist** (change 5.4 creates it) |
| `/etc/dnf/automatic.conf` | **does not exist** (change 5.4 creates it; `dnf5-plugin-automatic` uninstalled) |
| firewalld | zone `FedoraServer` (default), interface `eno1` |
| Cockpit on `:9090` | listening (1 socket) — the exposure decision in change 5.3 |
| `/etc/crypttab` | not readable as `aicowork` (0600 root); value from the sudo baseline: `luks-8919c2b1-… UUID=8919c2b1-… none discard,x-initrd.attach` |
| kernel | `6.19.10-300.fc44.x86_64`, the only kernel installed |
| PCR7 / Secure Boot / boot_id | `22103EAC…6A73` / `enabled` / `72d8d61b-9bb1-4491-beef-616a2e2e7d15` |

### Repository and signature state (the precondition 5.1 depends on)

Checked read-only before the upgrade, because the guide requires Fedora's signed repositories and
forbids adding an unrelated one.

| Check | Result |
| --- | --- |
| Repo files | `fedora.repo`, `fedora-updates.repo`, `fedora-updates-testing.repo`, `fedora-cisco-openh264.repo` — all Fedora-official, no third-party repo |
| Enabled repos | `fedora`, `updates`, `fedora-cisco-openh264`; **`updates-testing` is `enabled=0`** |
| `gpgcheck` | `=1` on every repo — package signature verification on |
| `repo_gpgcheck` | `=0` (Fedora's default: metadata is covered by TLS, packages by gpgcheck) |
| Repo key reference | all four repos point at `file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-$releasever-$basearch`, which expands to `RPM-GPG-KEY-fedora-44-x86_64` — **present** |
| Imported signing keys | exactly one: `Fedora (44) <fedora-44-primary@fedoraproject.org>` |
| Keys on disk | 302 (the `fedora-gpg-keys` package ships every historical key — normal) |

`fedora-cisco-openh264` being enabled is not a deviation from "no unrelated repository": it is hosted
and signed by Fedora, ships enabled on a default install, and uses the same Fedora key as the others.
A first check wrongly reported its key path as missing because `$releasever`/`$basearch` are dnf
variables that a shell does not expand; the corrected check confirms the expanded path exists.

### Step 5 prerequisites (runtime account, directories, sizing)

Captured read-only before the changes that depend on them.

| Check | Result |
| --- | --- |
| `hermes` account | **absent** — correct before 5.6 |
| `/etc/subuid` | `aicowork:524288:65536` |
| `/etc/subgid` | `aicowork:524288:65536` |
| **Predicted `hermes` subid range** | **`589824:65536`** — Fedora allocates the next free range, and this matches the guide's reference row, so 5.6 should reproduce it |
| `/` free | 57G |
| `/var` free | 40G — the guide requires ≥20 GiB |
| `/home/hermes` free | 246G |
| `/boot` free | 1.5G at 19% used — sufficient for `dracut` to regenerate the initramfs |
| `/home/hermes` entries | 0 — empty, nothing to preserve |
| chronyd / auditd / sshd / firewalld | all already **active** |

This closes a gap in the step 1 baseline script, which did not capture subordinate-ID ranges — the
reference M01 record had done so (`aicowork 524288:65536`), and the fresh install matches it exactly.

### 5.4 configuration path — verified against upstream documentation

The guide says to "review `/etc/dnf/automatic.conf` and set staging", but on this host that file **does not
exist** after `dnf5-plugin-automatic` was installed by C10 — `/etc/dnf/automatic.conf` is absent while
`/etc/dnf/dnf5-plugins/` exists. That looked like a wrong path in the guide; it isn't.

Per [the dnf5 automatic documentation](https://dnf5.readthedocs.io/en/stable/dnf5_plugins/automatic.8.html):
default values come from `/usr/share/dnf5/dnf5-plugins/automatic.conf`, and **host-specific overrides are
read from `/etc/dnf/automatic.conf`**. The docs go on to say you should either copy the distribution file
as a baseline or create the override from scratch with only the required settings. So the guide's path is
correct and the file simply is not created at install time — it has to be created.

Also worth recording, because it changes what the step accomplishes: the values the guide prescribes are
the **documented defaults** — `apply_updates` default `False`, `download_updates` default `True`,
`reboot` default `never`, `emit_via` default `stdio`. Writing the override therefore makes the
download-only policy explicit and auditable rather than changing behaviour; the system is already
download-only without it. The deprecated-looking `/etc/dnf/dnf5-plugins/automatic.conf` is a legacy path,
and upstream has an open issue about the *order of precedence* between the two
([dnf5#1770](https://github.com/rpm-software-management/dnf5/issues/1770)), so this run uses only the
documented `/etc/dnf/automatic.conf`.

**Proven on the host in C15, not just documented.** Both paths are zero-byte `%ghost` placeholders that
the RPM declares and never creates, so on a fresh install *neither* exists and a wrong choice would be an
undetectable no-op. A three-case probe settled it: with only `/etc/dnf/automatic.conf` present the plugin
was silent; with only `/etc/dnf/dnf5-plugins/automatic.conf` present it printed

```text
Warning: Configuration file location "/etc/dnf/dnf5-plugins/automatic.conf" for dnf automatic is deprecated.
```

The warning tracked the presence of that path exactly, which proves the legacy path is still **read** and
that the documented path is the current one. The guide is correct as written.

**A probe-design warning for anyone repeating this.** `emit_via` and `upgrade_type` are both useless as
config-read probes: with no updates available and `emit_no_updates = no`, the tool never emits a report, so
it never evaluates the emitter — all three probe cases were silent on that signal, and a bogus
`upgrade_type` exited 0 without complaint. The deprecation warning was the only discriminating signal
available. Choose a probe the tool must evaluate on every invocation, or rely on that warning.

### DNS resolution for `hermes.ai.lab.local` — the record is right, the resolver path is broken

Found while preparing 5.5, and it changes what that step is for.

**The router's record is correct.** Both router interfaces answer authoritatively —
`dig +short @10.0.30.254 hermes.ai.lab.local` and `dig +short @192.168.99.254 hermes.ai.lab.local` each
return `10.0.30.10`, `NOERROR`, one answer, TTL 86400 — and the reverse lookup of `10.0.30.10` returns
`hermes.ai.lab.local`. The name comes from the VLAN 30 DHCP network's `domain=ai.lab.local`.

**The workstation still cannot resolve it, and the cause is structural.** Through the workstation's
systemd-resolved stub, `dig hermes.ai.lab.local` returns **`status: REFUSED`** together with dig's own
warning `.local is reserved for Multicast DNS`, and `resolvectl query hermes.ai.lab.local` fails with
`No appropriate name servers or networks for name found`. Querying the identical name directly against
either router interface succeeds, which isolates the fault to the client's resolver path and not to the
DNS data.

The lab domain `ai.lab.local` ends in the **reserved mDNS TLD `.local`** (RFC 6762). systemd-resolved
routes every name under `.local` to multicast DNS and refuses to forward it to unicast servers. On this
workstation `resolvectl status eno1` reports `-mDNS`, so mDNS is disabled too — the name has **no route
at all**: not unicast (reserved) and not multicast (disabled). This is exactly what NETWORK_DESIGN.md
meant by "resolution failed from the audit workstation; validate the resolver path before relying on it",
and it is why AGENTS.md says to use the verified IP `10.0.30.10`.

Blast radius: every unicast name under `.local` in this lab is affected, not just this host —
`router.mgmt.lab.local` behaves the same way — and every Linux client running systemd-resolved will
behave this way.

So 5.5's "update the workstation's host entry and confirm it resolves" is **not a formality**: the
`/etc/hosts` entry is the only mechanism that will make the name resolve on that client, because the DNS
path cannot carry a `.local` name. Setting the static hostname to `hermes.ai.lab.local` remains correct —
it matches the DNS record, the DHCP-derived transient name and NETWORK_DESIGN.md — but resolution must
come from `/etc/hosts` per client.

**Structural fix, outside gate B6:** rename the lab domain away from the reserved `.local` suffix (for
example `ai.lab.internal`) so unicast DNS can serve it. A narrower alternative worth testing on the
workstation is an explicit routing domain, `resolvectl domain eno1 '~ai.lab.local'`, which may override
the mDNS special-casing for that one suffix; it was **not** tested here because it needs root on the
workstation.

### Egress prerequisites for the application phase — verified before deployment

Checked read-only from the host while host preparation was still in progress, so a blocked egress path
would be found now rather than halfway through M02–M05.

| Destination | Needed for | DNS | TCP 443 |
| --- | --- | --- | --- |
| `registry.fedoraproject.org` | the worker image build (`podman build` from the pinned Fedora base) | `38.145.32.20` | **OPEN** |
| `api.openai.com` | provider egress for the gateway | `162.159.140.245` | **OPEN** |
| `api.telegram.org` | Telegram polling for the gateway | `149.154.166.110` | **OPEN** |

Routing and resolution: `default via 10.0.30.254 dev eno1 proto dhcp src 10.0.30.10 metric 100`,
resolver `127.0.0.53` (systemd-resolved). All three paths are open, which is the precondition for
M02's image build and for the gateway's provider and messaging egress. It also confirms the design's
choice of Telegram **polling** rather than a webhook — no inbound path is required.

### The deployed artifacts come from the staged bundle, not from the repo

Worth recording before the application phase, because it decides what an identity check should compare.

The operator stages the bundle **by hand from the workstation** — guide §6.1,
`scp -r scripts/hermes/manual aicowork@<HOST>:~/hermes-m02-bundle`. `m02-deploy-and-validate.sh` does **not**
create it: it validates the copy it is handed (`bundle sanity`, line 58) and then consumes it. (An earlier
version of this paragraph credited `m02-deploy-and-validate.sh` with staging it — corrected at C50.) Every
later script defaults to that path — `BUNDLE="${1:-/home/aicowork/hermes-m02-bundle}"` — and reads its
Quadlets and helpers from `$BUNDLE/quadlets/…` and `$BUNDLE/gateway/…`, not from
`scripts/hermes/manual/`. `m03-activate.sh` re-installs both Quadlets from
`$BUNDLE/quadlets/`, and `m04-readonly-gateway.sh` installs the read-only variant from the same place.

Consequence for a replication run: the artifact that actually gets deployed is the **bundle's** copy.
Checking that the bundle exists is not enough — the check that matters at M02 is a **bundle-versus-repo
comparison**, at minimum sha256 of `quadlets/hermes-gateway.container` and
`quadlets/hermes-worker.container`. This run already found one stale duplicate lurking inside
`scripts/hermes/manual/` (the SSH helper, C13), so the same drift between repo and bundle is a live
possibility rather than a theoretical one. The reference bundle is also not tracked by git, so the file
hash is the only identity available.

**This bundle went stale at C50.** That pass fixed nine files under `scripts/hermes/manual/` in the
repository only; the bundle still holds the pre-C50 version of all nine, so a step re-run from `$BUNDLE`
executes the old, defective script. Re-stage it from the current repository before re-running anything
from it — C50 item 6 lists the nine expected post-C50 hashes.

### C50 — Tier-1 remediation pass: procedure defects fixed in the repository, and the B6 status propagated

**Date:** 2026-09-14, after the C49 handoff.
**Trigger:** operator review of the handoff's limitation list, with an explicit instruction to fix the
repo-side defects only — no privileged work, no host change, no service interruption.
**Scope discipline:** this pass changed **procedure and record only**. Nothing was deployed, no host file
was written, no container was touched, and no artifact the validated deployment actually runs
(`quadlets/`, `worker/`, `gateway/`, `config/`) was modified. The running host is unchanged by C50, so the
Phase 7 acceptance recorded in C47 still stands exactly as written.

**1. The defect that caused the entire SELinux class of failure.** `scripts/hermes/manual/README.md` stated
the labelling rule as "`/home/hermes/transport` is `:z`; everything else uses `:Z` (private)". That
sentence is the origin of the eight `:Z` sites on the shared `gateway-state` directory found in C30, C31
and C36 — the mistake was followed faithfully from its own documentation. It is replaced with the
**measured** model, in the two parts the experiments actually established: `:z` is required on every
directory that **more than one container mounts** (because `:Z` stamps the directory with one container's
private MCS categories and a service that gets a fresh pair at each start is denied its own state DB), and
`:Z` remains correct for **single-container paths** — the worker's `worker-state/*` and the four
`gateway-ssh` binary mounts, which nothing else mounts. A newly written file inside a mount keeps the host
default `user_home_t` label and must be relabelled explicitly. The replacement also carries the operational
consequence that cost this run time: **changing the option does not relabel files already on disk**, so a
switch to `:z` must be followed by an explicit `chcon -R`.

**2. Nine script defects, each observed live during the run.** Every fix is to a *check* or a
*provisioning step*, so each closes a way the procedure could report success it had not earned.

| File | Defect as observed | Fix |
| --- | --- | --- |
| `m04-postboot.sh:83` | installs `m03-probe.py` into the `:ro,Z` `gateway-ssh` directory with no relabel, so the new file keeps the host default `user_home_t`, the probe fails at step 12, and one AVC denial is logged that is indistinguishable from a regression (C44) | relabel at install time, and print the resulting context |
| `m04-backup.sh:135` | restarts **only** the worker; the gateway, stopped for the backup, is left down — previously declared as deviation 9 | restart both, and print both states |
| `m04-backup.sh:111` | `diff_rc` was read after a pipe to `head`, so it measured `head` and the check could not fail | `PIPESTATUS[0]`, plus `diff -rq --no-dereference` for the dangling uv-cache symlinks |
| `boot/b4-verify.sh:151` | `exit "$rc"` where `rc` came from the `tee` pipeline alone — the script exited 0 on any host state (C46) | explicit `ASSERT name=PASS\|FAIL\|UNVERIFIED` lines with the verdict derived from them; the AVC assertion is scoped to the run rather than the boot, because a by-design denial already present in the boot would have produced a false FAIL |
| `m04-readonly-gateway.sh:55` | `telegram_state()` counted "Connected to Telegram" across all boots, so an earlier boot satisfied a post-restart check | `journalctl -b` |
| `m04-readonly-gateway.sh:90` | auto-reverted only on `is-active`, though the guide promises a revert "if Telegram does not return" | revert now requires connectivity, behind a bounded 60s poll so a slow reconnect is not read as failure |
| `m03-configure-and-probe.sh:92` | inverted guard: a version-less config fell through to "not below the v12 floor", which is false | the three cases are now distinct and each message is true; **the disposition is unchanged** — a version-less config is still left in place, because asserting a schema version is a compatibility claim this run has not substantiated |
| `m04-reboot.sh:5,61` | header and prompt still claimed a console LUKS passphrase is required, which B3 made false | corrected, with the passphrase condition stated precisely (token removed, or PCR 7 changed) |
| `provision-telegram.sh:72` | `grep -vE … > "$tmp" \|\| true` swallowed every failure, including a real read error that would have silently dropped the other keys | only the legitimate "selected no lines" exit 1 is tolerated; anything else stops the run, and the preserved key count is printed |
| `provision-openai-key.sh:63` | `cat > /opt/data/.env` truncated the file, so re-running it destroyed `TELEGRAM_*`, `API_SERVER_KEY` and the hardening flags | replaced with the same filter-and-append merge `provision-telegram.sh` already uses, plus a preserved-key count. **This retires the run's standing warning that the script must never be re-run once Telegram is provisioned.** |

**3. Documentation defects.** The guide's Telegram check now names the approval test explicitly — it must
use a command the policy actually gates — and lists the benign commands as deliberately ungated (C38,
C40). The stale passphrase claim in `m04-reboot.sh` is fixed above.

**4. B6 status propagated into every boot-track record.** `docs/HERMES_BOOT_AUTOMATION.md` (header and
gate section 8), `docs/HERMES_MANUAL_HANDOFF.md` (header, the Regime B bullet, and the gate-table row that
still read `⬜ TODO`), `docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md` ("has not yet been executed end to end"),
and `docs/HERMES_BOOT_CLEAN_INSTALL.md` (which carried no status line at all) now record B6 as
**✅ PASS, 2026-09-14** and point at the C49 handoff. That handoff's evidence index cited `C1–C48`;
corrected, and now `C1–C50`.

**5. A correction to the propagation plan itself, made by inspection.** The initial list of stale B6
statements included two lines in `docs/HERMES_INSTALLATION_VERIFICATION.md` (1430 and 1466). **Both were
left alone deliberately.** That file's `B1–B7` is a *different taxonomy*: its B6 is "credentials" in the
AR04 / `HERMES_TPM_DEPENDENCY_REVIEW.md` gate set, not the clean-install gate. Editing those lines would
have asserted that a credential-verification gate had passed, on the strength of an unrelated clean
install. The two taxonomies share gate letters and nothing else; a replication must not conflate them.

**6. Identity — and one gap in the chain, stated rather than papered over.** For the nine scripts the
pre-edit identity is **measured, not inferred**: the deployed bundle at
`/home/aicowork/hermes-m02-bundle` still holds the exact artifacts the run executed, read back over SSH
during this pass. Its `m03-configure-and-probe.sh` hashes to `7edfbff7…`, byte-identical to the value C36
recorded — independent confirmation that the bundle is the validated artifact and that the pairs below are
real.

| File | Before (as deployed) | After (C50) |
| --- | --- | --- |
| `README.md` | `72bdd2feb4e004e00602348afe88249fbb864dadecf2078ee6b25e8df8bd5057` | `0c2bdbbbc20b1e7bfea930984cd891db53b5a0b4cc1bb7f4273df4fedb8dcf7c` |
| `m04-postboot.sh` | `c278aa1059f64d1e21efa98abf9edaece23940462b212f9d168553513994a9db` | `5103eb6472f95daee5a57ae006a9c57e5ea66f0dd1114ec64a8de3a8e486e3e9` |
| `m04-backup.sh` | `b2964d7469e2328fcf2c8e6b4050de5b0f277646e6256db3e0cd434aab2c01ec` | `5793e8a8b892838c08a816ac7bb6f59fd6c1c913b67505a28a4cc9b18093194b` |
| `m04-readonly-gateway.sh` | `c0f1273b4fdf5f37a5d6527b4a83a289e74ed0b4447e427c89d50a0db1ad2f42` | `94e20872067739835ce171ea6a55e309876e579b7f0607ba88a4edf07737b292` |
| `m03-configure-and-probe.sh` | `7edfbff71f87058a4bdd6a98ac7d845370b4015bac6b53754916eafcfeda0308` | `8f41dcbd25f7dfef034cba8b6a2b4c78fec9c23ddbe0e372f945e1fcc2c888a0` |
| `m04-reboot.sh` | `cda185f12abd6ad4632db2b1fc5f3fd477f74a4f2ba81dff75403934efac82ed` | `de233b9da684a800522111eedd73a6682915aa8bc8e7b2a4b73224ff10eafc80` |
| `provision-telegram.sh` | `2670427c4f8b3cff775dc64b20a500a6230bd3a6849c923121326ff063e305f5` | `e8d9918904f69eaae9f28699fbeab9fe81df5af4a9171e72f31bd297e3011061` |
| `provision-openai-key.sh` | `7b73e1cd21d1efcf9aa647ed294da8c291a8f8d5852c4faedfef9cd85984777c` | `f2c3fb37f1f97686683a1db74d3375bf314be40255d9e52f3082f08957ab3c1b` |
| `boot/b4-verify.sh` | `d14dff3c27a99cf7cb636baa11029c84b2787ce110e8928d8c06bde002ea141e` | `fced1fb9e4f07379f341ce4891dd2a511c67bdf7aaa0e15f0e34a9dc939e81a3` |

**The gap:** the five documents edited in item 4 (`HERMES_BOOT_AUTOMATION.md`, `HERMES_MANUAL_HANDOFF.md`,
`HERMES_MANUAL_DEPLOYMENT_GUIDE.md`, `HERMES_BOOT_CLEAN_INSTALL.md` and the C49 handoff) are **untracked in
git and were never hashed**, so their pre-edit identity is not recoverable from any record. Their identity
chain therefore *begins* at C50. This is stated rather than back-filled: a hash produced by reversing an
edit would be an inferred value dressed as a measurement, which is the same error class as the false zeros
catalogued in the evidence record.

**7. What was verified on this pass, and the limit of it.** All eight changed shell scripts pass `bash -n`.
**No script was executed** — running them needs the privileged host work this pass was scoped to exclude.
So these fixes are verified by syntax and by inspection against the live defect each one addresses, not by
re-running the steps: the fixed procedure is *not* itself certified by this entry. That is the honest
boundary, and the reason every row above cites the change that observed the defect it removes.

**8. Consequence for the host, and for a replication.** The bundle at `/home/aicowork/hermes-m02-bundle` is
now **stale relative to the repository** for the nine files in item 6: it holds the *pre-C50* copies (its
directory mtime is `2026-09-13 21:23:15 -0500`). Two limits on what that does and does not mean, so the
finding is not read as larger than it is:

- **Nothing at runtime reads the bundle.** The installed Quadlets under
  `/etc/containers/systemd/users/<uid>/` and the state under `/home/hermes/gateway-state` are what the
  containers use. Only *re-running a step script on this host* is affected, and only if it is not re-staged
  first. The deployed system is unchanged — C47 still stands.
- **A replication re-stages it anyway.** Guide §6.1 copies the bundle from the workstation with
  `scp -r scripts/hermes/manual …` and already instructs `rm -rf ~/hermes-m02-bundle` first, precisely so a
  redeploy cannot layer a stale copy underneath a fresh one. The nine hashes above are the expected values
  for that stage, and a bundle-versus-repo sha256 comparison is the check that should gate it — nothing in
  M02 verifies the copy against the repository today, it only checks the files are readable.

Re-staging **this host's** bundle is a host write and was deliberately left outside this pass. It is a
convenience for re-running steps here, not a precondition for a replication.

**9. Still open, deliberately.** The memory approval queue (C39) is documented as a known defect and left
unfixed: the gateway image is digest-pinned upstream, so a local code fix would diverge from the pinned
artifact and invalidate the run's identity evidence. The `_config_version` question, the Quadlet
`TERMINAL_*` question, auxiliary-client routing, the resolver path and the B1 firmware option name all
remain exactly as recorded in handoff section 9. Nothing in C50 closes them.

### C51 — Folding the replication deviations into the guide, and two corrections to the record

**Date:** 2026-09-14, after C50.
**Trigger:** operator review of what remained, and the explicit instruction to fix the guide before preparing
commits. **The reasoning that made this the priority:** the guide is the deliverable of a "follow along"
validation, and as written it did **not** reproduce the validated run. A reader following it literally would
have built a host whose final boot gate could not run. This entry closes that gap.
**Scope:** documentation only. No script, no host file, and no deployed artifact was touched. The nine C50
script hashes are unchanged (re-verified: `README.md` `0c2bdbbb…`, `boot/b4-verify.sh` `c7092b96…`).

**1. Two defects that would break a literal replication.**

- **`docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md` §5.1 omitted `tpm2-tools`** from the host tool list, while
  `boot/b4-verify.sh` reads PCR 7 with `tpm2_pcrread` and the enrollment and fallback helpers use it too.
  This was deviation 2 — known, recorded, and left in the guide. Added, with the reason stated inline rather
  than as a silent edit.
- **§5.2 named `~/.ssh/id_ed25519.pub`, which does not exist on the reference workstation** (deviation 3).
  The working key is `id_ed25519_cloudops.pub`, and the helper must be the repo-root copy. Corrected in all
  three places, with a note that the key *name* is not significant but a missing file fails late.

**2. The process hazards became guide content.** Deviations 5, 6 and 8 were pure run history — a wrong-machine
reboot, a shared LUKS device path, a `!` history-expansion defect in the host guards. They are now Appendix A
items 10–13, written as rules rather than as incident reports, because the same mistakes are available to any
operator pasting blocks: guard every paste-able block by hostname, keep the guard message in **single quotes**
(an interactive bash expands `!!` from history inside double quotes), never `exit` from a guard, and guard
device paths with `cryptsetup luksUUID`. Item 12 records the "check that cannot fail" pattern behind C50's
two verdict fixes; item 13 records that a verification step's own output can be the defect.

**3. The step table now says what the scripts actually do.** Deviation 9 — the gateway stopped for the backup
and never restarted — is **resolved at the source by C50**, and §6.3 row 7 now states that the script stops
both containers and restarts them, row 8 warns the gateway must be running, and row 14 states that
`b4-verify.sh` exits non-zero on a failed assertion. §6.4 gained the same detail for the recovery check.

**4. The runbook's one load-bearing ordering constraint is now written down.** Deviation 7 was that the run
did not follow the runbook's numbering literally. Inspecting it showed the runbook is **not** wrong — Step 2
(firmware) already precedes Step 6 (enrollment) — but nothing said *which* part of that order matters.
`docs/HERMES_BOOT_CLEAN_INSTALL.md` "Before you start" item 3 now states it: firmware before enrollment,
because the keyslot is sealed against the measurements the machine produces at enrollment time; steps 3–5 are
independent of Step 2 and may precede it.

**5. Two corrections to this record itself.**

- The pre-existing bundle paragraph credited `m02-deploy-and-validate.sh` with **staging** the bundle. It does
  not: guide §6.1 stages it by hand with `scp -r`, and `m02` only validates readability and consumes it. Fixed
  at the paragraph, and it also means **nothing verifies the bundle against the repository** — which is
  precisely how a stale copy sits there unnoticed.
- C50 item 8 said re-staging was the operator's next action. That **overstated** it: nothing at runtime reads
  the bundle, and guide §6.1 re-copies it (instructing `rm -rf` first) on any replication. Both item 8 and the
  handoff's §8 update now carry that qualifier.

**6. Identity, and the same gap restated.** Both edited documents are untracked in git and were never hashed,
so as with the five documents in C50 item 6 their chain **begins here**:
`docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md` `80f7463b7942cf458dea18694d3b18f3c00fd67cd593796e1a19ff1ba961b5da`,
`docs/HERMES_BOOT_CLEAN_INSTALL.md` `3be1c2359f4f2c48f3b3f1361a3f5453d48edcafc033e27358a45b54ea068f99`.

**7. The rehearsal was re-run, and it passes.** C50 changed `boot/b4-verify.sh` — one of the helpers
`rehearse-clean-install.sh` exists to inspect — and C51 edited the runbook and guide that the same script
cross-checks, so the `REHEARSAL=PASS` obtained before B6 was stale by construction. Re-run on 2026-09-14 from
the workstation, read-only, no privileges, no host mutation:

```text
failures=0 advisories=0
REHEARSAL=PASS
```

Section 15 confirms every deployment helper is still named in the guide and that the boot prerequisites still
precede application deployment; section 16 exercises the worker-key helper end to end in a temporary directory.
So these edits are validated **against the helpers**, not merely by my reading of them — the strongest
verification available without re-running the deployment. **The remaining limit is unchanged:** no changed
script has been *executed against the host* (C50 item 7), so the C50 fixes rest on syntax, inspection and this
static rehearsal.

**8. The pre-commit lint pass found two defects in C50's own output.** Preparing the commits meant running
the repository's hooks by hand first — `shellcheck`, `shfmt -d -l -i 2 -ci -bn` and `markdownlint-cli2` over
the staged files, per `lefthook.yml`. Both findings were in code C50 had just written, and both would have
**blocked the commit**:

- **`shellcheck` SC2016 in `provision-openai-key.sh`.** Converting the `.env` writer from a one-line
  `sh -c '…'` into a multi-line script introduced `$tmp`/`$rc` references inside a single-quoted string, which
  shellcheck reports as "expressions don't expand in single quotes" — correct here, since expansion inside the
  container is intended. Fixed with the same `# shellcheck disable=SC2016` directive and explanatory comment
  that `provision-telegram.sh` already carries for the identical pattern, rather than by suppressing the check
  globally.
- **`shfmt` rejected two hunks in `boot/b4-verify.sh`** — the `case` arms in `avc_total_today` and a
  `cmd; rc=$?` line that the formatter splits. Applied with the repository's own settings
  (`shfmt -w -i 2 -ci -bn`); the changes are confined to code C50 added, and the other 24 staged scripts were
  already conformant.

**Identity consequence, recorded because the C50 table above has been revised:** the two files now carry
their post-lint hashes — `provision-openai-key.sh` `f2c3fb37f1f97686683a1db74d3375bf314be40255d9e52f3082f08957ab3c1b`
and `boot/b4-verify.sh` `fced1fb9e4f07379f341ce4891dd2a511c67bdf7aaa0e15f0e34a9dc939e81a3`. The intermediate
values C50 first recorded (`10bef45a…` and `c7092b96…`) never existed outside this session. Final state
verified: `shellcheck` clean and `shfmt` clean across all 25 staged shell scripts.

**9. `markdownlint` was broken for every commit in this repository, and the ledger itself failed it.** Two
separate defects, both found only because the hooks were run by hand before committing:

- **The ledger carried 21 lint errors** — 17 × MD040 (bare fences around logged output), 3 × MD013
  (over-long lines) and 1 × MD036. The repository's standard is that documents pass: the 470 KB tracked
  evidence ledger `docs/plans/2026-09-07-hermes-unattended.md` reports **0 errors**. Fixed to meet it —
  fences labelled `text` (they hold command output, journal lines and AVC denials), the over-long prose
  rewrapped, one long inline command moved into a `bash` block so it is preserved verbatim rather than
  truncated, and the standalone `**Conventions**` pseudo-heading given trailing text.
- **The pre-commit hook could not pass at all.** `.markdownlint-cli2.yaml` sets `globs: ["**/*.md", …]`, and
  markdownlint-cli2 **merges those globs with the file list**, so the hook's `{staged_files}` was ignored and
  the whole repository was linted on every commit. That is why it failed on files the author had not touched,
  and — once `private/` held an unpacked gateway rootfs containing ~2000 vendored `.md` files, one of them
  1 MB — why it died with `FATAL ERROR: Ineffective mark-compacts near heap limit`. Fixed in two places:
  `private/**` added to `ignores` in `.markdownlint-cli2.yaml` (it is gitignored, so linting it was always
  pointless), and `--no-globs` added to the `markdownlint` command in `lefthook.yml`, so the hook lints what
  is actually being committed — plainly what `{staged_files}` was meant to do.

Note what was **not** done: 94 further errors remain in
`docs/plans/2026-09-12-fedora-44-hermes-preparation-guide.md`, an untracked document from earlier work that
is not part of this change. It was left alone; scoping the hook to staged files is what stops it blocking
unrelated commits.

**Verification after all of the above:** `shellcheck` 0 findings, `shfmt` 0 differences, `markdownlint-cli2`
0 errors across the 7 staged documents, and the repository's own guide test `./tests/test-hermes-guide.sh`
reporting **217 passed, 0 failed**.

**10. One personal identifier was redacted before the first commit.** The operator's numeric Telegram user ID
appeared **16 times across three files** — this ledger (8), the evidence record (6) and
`2026-09-13-hermes-m05-telegram.json` (2). It is **not a credential**, and the run recorded it deliberately:
that file's own text said "numeric IDs are not secret and are recorded deliberately". That judgement is
reversed here, on the operator's instruction, because committing makes a personal identifier permanent in
history. All 16 became `<redacted-telegram-user-id>`.

Three consequences were handled rather than left to a blind substitution:

- **Two sentences depended on the value's length.** The `.env` byte accounting reads "a delta of −9, which is
  the allowlist value shrinking from the 10-character account ID to `1`". A placeholder is 27 characters, so
  the arithmetic would have stopped making sense; the **length is retained and the value is not**, and both
  occurrences say so.
- **One quotation was substituted inside verbatim journal output** (`agent:main:telegram:dm:…`, `chat=…`).
  Those lines are no longer byte-verbatim at that field. Rather than leave it implicit, the redaction
  convention is stated in this ledger's Conventions block and in a new `redaction_note` key in the evidence
  record, so a reader is told which field was touched and that nothing else was.
- **The m05 evidence file's rationale was rewritten**, since "recorded deliberately" would otherwise now
  contradict the placeholder sitting in front of it.

Re-verified after the substitution: both JSON files parse, the staged markdown still reports 0 lint errors,
and `grep` finds **zero** remaining occurrences of the original value anywhere in the staged set.

**11. The commits, and two further hook findings that surfaced only when committing.** The work of C50 and
C51 was committed in three atomic commits on `codex/hermes-manual-guide-plan`:

| Commit | Message | Scope |
| --- | --- | --- |
| `9aed7e6` | `fix(hooks): scope markdownlint to staged files and skip private/` | the two lint-tooling files |
| `879d906` | `feat(hermes): add the manual deployment profile and its guides` | 44 files: `scripts/hermes/manual/` + the four guides |
| `64c0e5d` | `docs(hermes): record the B6 clean-install validation` | 10 files: the handoff, the ledger, the per-gate evidence |

56 files and 11,922 insertions in total. Nothing was pushed. (The commit carrying *this* entry cannot name
its own hash; it follows `64c0e5d`.)

Two findings, neither of which is a defect in the changed files:

- **The lint tools are only on `lefthook`'s PATH inside `devbox run`.** Invoking `git commit` from a plain
  shell makes the `shellcheck` and `shfmt-check` hooks die with `sh: line 1: shellcheck: command not found`.
  The tools live in `.devbox/nix/profile/default/bin/`, so the hooks must be driven by committing from inside
  the devbox shell — otherwise a commit either fails or, worse, is made with those two checks silently
  skipped. Recorded because it is invisible in the hook definitions themselves.
- **The `no-secrets` hook produced 24 false positives on this change set, and would block it.** Its pattern
  is `(password|secret|token|api[._-]?key|credential|private[._-]?key)\s*[:=]\s*["']?[^\s"$]`, which matches
  any *name* followed by a separator and any non-empty value. Every hit here was a credential **name** used
  as data rather than a value: `grep -c '^TELEGRAM_BOT_TOKEN='`, Python `startswith("OPENAI_API_KEY=")` in
  the log redactors, `printf 'OPENAI_API_KEY=%s\n'`, `${PASSWORD:-}`, and one usage example reading
  `PASSWORD="MySecretPassphrase"`. The two commits were therefore made with
  `LEFTHOOK_EXCLUDE=no-secrets`, **after** an independent scan of all 41 candidate files for live credential
  shapes (Telegram bot-token form, `sk-…`, `API_SERVER_KEY=<hex>`, private-key blocks) which found none —
  and after the pre-commit secret scan had already been run. **Recommended, not applied:** narrow the pattern
  so a value must look like a value (exclude a leading `%`, `$` or `-`, and require a plausible length). That
  is a deliberate non-change: loosening a security control to make my own commit pass is not a call this run
  should make unilaterally.

**12. The `b4-verify.sh` verdict path was tested, which narrows C50 item 7's gap.** C50 item 7 records that
no changed script had been executed. The one half of C50's work that *can* be executed without the host is
the new verdict logic, so it was extracted verbatim into a harness and run against six synthetic logs:

| Case | Expected | Observed |
| --- | --- | --- |
| all four assertions PASS | exit 0, `RESULT=PASS` | ✅ exit 0 |
| one `=FAIL` | exit 1 | ✅ exit 1, names 1 failed assertion |
| one `=UNVERIFIED` | exit 0, PASS **not** claimed | ✅ exit 0, "a PASS is NOT claimed for those" |
| log present, zero `ASSERT` lines | exit 1 | ✅ exit 1 |
| log missing entirely | exit 1 | ✅ exit 1 |
| pipeline `rc≠0`, log otherwise clean | exit 1 | ✅ exit 1 |

The last three are the cases that guard against the original defect class — a verification step reporting
success it did not earn — and each fails closed as intended. **The gap is narrowed, not closed:** the
assertion-*generating* half (container state, `probe_rc`, failed units, AVC counts) still has no execution
against a real host, because that needs root. C50 item 7 stands on that point.

One cosmetic observation, left alone rather than fixed: when the log is missing, `grep` prints three
`No such file or directory` lines just before the `RESULT=FAIL` line. Harmless — the RESULT line states the
cause — and suppressing it would hide the evidence of why.

### C52 — The stale SSH helper duplicate, found still unresolved after the work was committed

**Date:** 2026-09-14, after `84e7bc5`.
**Trigger:** the operator asked what remained. Checking the uncommitted tree to answer that question surfaced
`setup-ssh-key-only.sh` as an **untracked file at the repository root** — the same helper that had just been
committed at `scripts/hermes/manual/`. They are not the same program.

**The defect, and it is a bad one.** The committed copy was the **older and weaker** of the two, and the
guide told operators to copy it:

| | repo root (untracked) | `scripts/hermes/manual/` (was committed at `879d906`) |
| --- | --- | --- |
| sha256 | `32ac4ba3…` | `eacc931a…` |
| size / lines | 20,277 B / 495 | 17,232 B / 433 |
| mtime | 2026-09-12 **17:05** | 2026-09-12 **15:33** |

The root copy carries **62 lines of hardening the shipped copy lacks**, and each one is a security control
that would simply never execute on a replication:

- **`inspect_crypto_path()`** — resolves the crypto-policy symlink and validates the target, its ownership and
  its permissions. The shipped copy excluded the path from review entirely.
- **`inspect_service_overrides()`** — reads and validates the **contents** of sshd's drop-in. The shipped copy
  accepted or rejected on the *filename alone*, which a same-named file with different contents defeats.
- **`inspect_service_environment()`** — parses `/etc/sysconfig/sshd` narrowly and **never sources it**. The
  shipped copy grepped it coarsely.
- **Firewall policy templates** — a reviewed allowlist (`gateway-dmz-to-HOST`, `gateway-lan-to-HOST`,
  `gateway-lan-to-work`, `gateway-lan-to-world`, `gateway-world-to-HOST`) queried with `--query-disable`, where
  the shipped copy failed closed on everything except `allow-host-ipv6`.

**This was known and never closed.** Deviation 3 below records it: *"a stale copy of the SSH helper; this run
uses … the repo-root helper, which is the tested one."* C13's discussion names the duplicate too. The run
worked around it by using the right file — and then nobody replaced the wrong one. **The consequence is worse
than an open item: the record asserted that SSH hardening had been validated with the hardened helper while
the artifact a replicator would copy was the weaker one.** A replication would have performed a materially
less rigorous review than the validated run, and the record would not have shown it.

**An error of the agent's own, introduced during C51.** The §5.2 rewrite added *"The helper must be the
**repo-root** copy, which is the one this procedure was validated against"* directly above a command copying
`scripts/hermes/manual/setup-ssh-key-only.sh`. That is self-contradictory, and unfollowable from a fresh
clone, because the root copy is untracked. C51's own editing introduced a documentation defect of exactly the
kind C50 and C51 existed to remove.

**Fix applied.** The hardened root copy was promoted to `scripts/hermes/manual/setup-ssh-key-only.sh`, so the
tracked artifact is now the validated one — `eacc931a…` → `32ac4ba3…`, byte-identical to the root copy, and
the mode stays `0755`, consistent with `configure-tpm2-auto-unlock.sh`. Both copies are `bash -n`, `shellcheck`
and `shfmt` clean. The guide's prose now names the **tracked** path, states that the root copy is untracked
and therefore absent from a fresh clone, and records that since C52 the two are byte-identical.

**Verification.** `rehearse-clean-install.sh` re-run after the swap: **`REHEARSAL=PASS`, `failures=0
advisories=0`** — so the hardened helper satisfies every check the rehearsal makes of it, including the
section-16 key-provisioning sequence it drives end to end.

**Left in place deliberately:** the untracked root copy, at the operator's direction. It is now byte-identical
to the tracked one, so it can no longer cause a divergence — but the tracked path is authoritative, and the
duplicate that caused this should eventually be deleted rather than relied on.

### C53 — The closure pass: walking the register item by item

**Date:** 2026-09-14, after `67867c1`.
**Trigger:** the operator asked what remained, then asked the sharper question — given that C52's defect was
*detected and recorded but never closed*, what can be done about that class. The answer is not more prose. The
evidence record already enumerated every finding; what was missing was the pass that walks that enumeration
and marks each item **closed or open against the artifact**. This entry is that pass.

**1. The register was itself stale — the meta-defect.** `findings_index` in the evidence record marks items
`FIXED IN C20` and `FIXED IN C31`, following a convention of prefixing closed items. But **C50's fixes were
never back-annotated**, so four items C50 had already repaired still read as open:

| Register item | Actually fixed by |
| --- | --- |
| `provision-openai-key.sh:63` truncates the `.env` | **C50** (merge, not truncate) |
| `provision-telegram.sh:72` swallows its grep failure | **C50** (only exit 1 is tolerated) |
| `m04-readonly-gateway.sh` auto-revert ignores Telegram | **C50** (`journalctl -b` + connectivity) |
| `m04-backup.sh:111-112` reads `diff_rc` from `head` | **C50** (`PIPESTATUS`) |

A reader of the register would have believed all four were outstanding. This is the same failure as the stale
helper: **a record that describes a state the artifacts no longer have.** All 20 closed items now carry their
C-number, and the 3 that remain open carry none — so "no prefix" now means "still open", which is the property
the register lacked.

**2. Five fixes in this pass.**

| Fix | Where | Was |
| --- | --- | --- |
| `tpm2-tools` added to the **second** tool list | prep guide §5 | the half-fix C51 left: I corrected the deployment guide and missed the prep guide, the exact C52 pattern, one turn after naming it |
| the printed key name | `setup-ssh-key-only.sh:418` | printed `-i ~/.ssh/id_ed25519_fedora` — a **third** key name that exists nowhere, so following the helper's own hint fails |
| `/etc/dnf/automatic.conf` must be created | guide §5.4 | said "review" a file that does not exist on a fresh Fedora 44 install |
| the 5-minute deadline | guide §5.3 | `--on-active=5m` documented as a safety margin; it is a hard deadline on the whole procedure, and it fired during the run, silently reverting the change |
| the PCR policy | prep guide §6 | described the superseded script's `0+7`; the authoritative policy is **PCR 7, SHA-256, no PIN** |

**3. Two boot-path checks that could not fail, now enforced.** These were the class the run kept rediscovering
— a check that reports a value and never acts on it.

- **`fallback-wipe.sh`** printed `crypttab_unchanged=…` and did nothing with it. The rehearsal's guard was
  worse: it grepped the *source* for the string `crypttab_unchanged`, which the `echo` line itself satisfies,
  so `REHEARSAL=PASS` was carried on a value that could only ever be printed. The script now emits
  `FALLBACK_PROOF=INVALID` and the run exits non-zero — **after** the block, deliberately not by exiting early,
  so the passphrase check and the NEXT instructions still run and leave the host in a known state. The
  rehearsal now requires the *enforcement* (`FALLBACK_PROOF=INVALID` **and** `RESULT=FAIL`), not the word.
- **`tpm-enroll.sh`** printed `dracut_rc` and the initramfs TPM-line count and then reported `ENROLL=done`
  regardless — the state where the token is gone and the initramfs cannot unlock. It now emits
  `ENROLLMENT_VERDICT=FAIL` when either is wrong, and exits non-zero.

**4. The rehearsal gained the check that would have caught C52 — and immediately caught the agent.** New
section 17 asserts **artifact identity**, not form: any helper whose basename exists in more than one place
must be byte-identical, or be listed with a reason as an intentional variant. Every other check in that
rehearsal tests *form* — that a path exists, that a string appears — which is precisely why it reported PASS
throughout while the shipped SSH helper was the stale one.

On its first run it found five duplicate pairs and classified them:

- `setup-ssh-key-only.sh` — **DIVERGENT**, and it was the agent's own doing: the key-name fix in item 2 above
  was applied to `scripts/hermes/manual/` but not to the root copy the operator asked to keep, so the pair
  diverged **within this same pass**. The guard caught the C52 defect being re-created nine minutes after C52
  was written. Root copy resynced; both now `36185e36…`.
- `host.py` and `controller.py` — **not stale copies but two different programs sharing a basename** (944 and
  285 differing lines; `scripts/hermes/simple/` is the bounded application-only installer and provisioned SSH
  controller, `scripts/hermes/unattended/` is the signed release entrypoint and the noninteractive dispatcher
  seam). Allowlisted with those reasons. **Limitation stated plainly:** the check is name-based and cannot
  distinguish "one artifact, two copies" from "two programs, one name", so the allowlist is where that
  judgement is recorded, not something the check can infer.
- `harden-config.py` — intentional, already documented in `2026-09-07-hermes-unattended.md:5511`.
- `set-model.py` — byte-identical.

**5. What is genuinely still open, and why.** The pass left exactly three register items unannotated:

1. **Nine predictable root-owned `/tmp` paths across eight files**, including redaction helpers that run as
   root and read the credential `.env`. A design change (`mktemp` per invocation), not a one-liner, and it
   touches the redaction helpers on the hot path of several scripts.
2. **`m04-posture.sh:98` does not enforce `systemctl set-property`'s return code**, and its read-only probe
   covers the worker but not the gateway. Needs a host to verify the change honestly.
3. **No CI.** Twenty-odd Python suites and the rehearsal itself are wired to nothing. Out of scope for a
   documentation-and-procedure pass, and the largest item on the list.

**6. Identity.** `fallback-wipe.sh` `3f3670d3…`, `tpm-enroll.sh` `88404e14…`, `rehearse-clean-install.sh`
`b02d572e…`, `setup-ssh-key-only.sh` `36185e36…` (root copy identical), prep guide `b3d7a7dd…`, deployment
guide `1cb5e444…`. Verified after every edit: `bash -n` clean, `shellcheck` clean, `shfmt` clean, both JSON
files valid, and **`REHEARSAL=PASS` with `failures=0 advisories=0`**.

### C54 — Making the guide accurate about its own accuracy

**Date:** 2026-09-14, after `6b5c30f`.
**Trigger:** the operator asked a direct question — *can the guideline be called 100% accurate for clean
deployments?* The answer is **no**, and this entry records why, plus the two changes that let the guide be
**accurate about its own status** even though the procedure is not fully proven. That distinction is the whole
point: every significant defect this session found was a *confidence mismatch* — a record describing a state
the artifacts did not have — not a capability failure.

**1. The guide carried an overclaim, written by the agent.** The Status section ended: *"treat the guide as
proven, and read that handoff before relying on any single step."* It is not proven. The B6 run executed the
*steps* amid ~52 recorded changes and **nine declared deviations** from the guide's own text, and the current
text post-dates that run throughout C50–C53 — **none of which has ever been executed against a host.** Calling
that "proven" is exactly the error class this ledger has been cataloguing.

The section is rewritten as an evidence-status block that states, in order:

- what is proven (one host, B1–B6, M04 steps 7–14, Phase 7 on all five criteria, after a wall-power cycle);
- that the run **departed from the text nine times**, and that the guide-side faults were corrected afterwards;
- that those corrections are **verified statically only** — `bash -n`, `shellcheck`, `shfmt`, the rehearsal —
  and **never executed**;
- therefore the honest claim: *proven to have worked once, under close supervision, with nine recorded
  departures from its own text*;
- that a second clean install performed literally, with zero unresolved deviations, is the gate that would let
  the section say more — **and that it has not been done**.

**2. The most serious functional defect was absent from the guide entirely.** The memory write-approval queue
was documented in the handoff's §8 limitations and in this ledger, but **nowhere in the document a replicator
follows**. A guide-only reader would deploy, ask the agent to remember something, receive a confident
confirmation, and store nothing. Fixed in two places:

- a prominent paragraph in the new Status block, because it affects **any** deployment rather than being a
  missing step, and because a reader who never reaches the appendices must still see it; and
- **Appendix A item 14**, with the full mechanism: the parked request at
  `gateway-state/pending/memory/<id>.json` with no status field, no Telegram prompt, no expiry past
  `approvals.timeout: 300`, survival across reboot and AC cycle, the absent `MEMORY.md`/`USER.md`, and the
  documented interface having no way to drain the queue (`hermes approvals` → `suggest`/`test`; `hermes memory`
  → `setup`/`status`/`off`/`reset`). It records why it is not fixed here — the digest-pinned upstream image —
  and ends with the operational instruction: **do not rely on the agent's memory.**

**3. What is deliberately not claimed.** This entry does **not** claim the guide is now accurate for clean
deployments. It claims the guide now **tells the truth about how far it can be trusted**, which is a property
it can honestly have today, and which the previous text did not have. The three register items left open by
C53 are untouched: predictable `/tmp` paths, `m04-posture.sh`'s unenforced `set-property`, and no CI. None of
them affects whether someone can follow the procedure, so they were not chased for the sake of a shorter list.

**4. Identity.** `docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md` `1cb5e444…` → `b3b58f14…`. No script, host file or
deployed artifact was touched. `markdownlint-cli2` reports 0 errors on the result.

## Not yet applied — the remaining changes, with the privilege each needs

| Order | Change | priv | Source |
| --- | --- | --- | --- |
| ~~1~~ | ~~Delete host staging copies + stray `~/private/` tree~~ — **done as C8** | user | C4 reverse |
| ~~2~~ | ~~**B1** firmware power-loss → power on; record option name and prior value; change nothing else~~ — **done as C19; reboot confirmed (`boot_id` changed), Secure Boot still User Mode, PCR7 byte-identical. Option name and prior value still unrecorded** | **console** | runbook step 2 |
| ~~3~~ | ~~5.1 controlled `dnf upgrade --refresh`, then install the tool list **including `tpm2-tools`**~~ — **done as C10** | root | guide 5.1 |
| ~~4~~ | ~~5.2 key-only SSH via the **repo-root** `setup-ssh-key-only.sh`, dry run then apply, at the console~~ — **done as C13, verified from both sides** | root, console | guide 5.2 |
| ~~5~~ | ~~5.3 firewall: Cockpit decision, timed `firewall-cmd` rollback timer around any change~~ — **done as C14 in two phases; first attempt reverted by the 5-minute timer, recovery written direct-to-permanent** | root | guide 5.3 |
| ~~6~~ | ~~5.4 bounded journal + download-only update policy; enable `dnf5-automatic.timer`~~ — **done as C15, agent-verified; also proved `/etc/dnf/automatic.conf` is the live override and `/etc/dnf/dnf5-plugins/automatic.conf` is the deprecated one** | root | guide 5.4 |
| ~~7~~ | ~~5.5 static hostname set to the **FQDN `hermes.ai.lab.local`** (this row previously said "distinct from", which was wrong — see C16), then **reboot**~~ — **done as C16, persistence proven across a real reboot** | root, console | guide 5.5 |
| ~~8~~ | ~~5.6 runtime account `hermes`; record the real UID; verify ≥65536 subordinate IDs~~ — **done as C17; UID 1001, subids 589824:65536, agent-verified** | root | guide 5.6 |
| ~~9~~ | ~~5.7 directories, `user@<uid>.service.d` mount guard, linger, rootless Podman check~~ — **done as C18; rootless=true cgroups=v2, graphroot on the dedicated XFS volume** | root | guide 5.7 |
| ~~10~~ | ~~Stage `scripts/hermes/manual/boot/` to `~/hermes-boot`, verify the 5-file manifest~~ — **done as C9** | user | runbook step 6.1 |
| ~~11~~ | ~~**B3** `tpm-enroll.sh --preflight` then enroll with the pinned UUID; **read `dracut_rc` and the tpm2 line count**~~ — **done as C21; preflight OK, token in slot 1, passphrase slot retained, `dracut_rc=0`, 18 tpm2 lines — the last two read from the helper's own log** | root | runbook step 6 |
| ~~12~~ | ~~**B4** reboot, confirm no passphrase prompt; then the fallback proof (`fallback-wipe.sh`) and re-enroll~~ — **done as C22 (warm boot), C23 (fallback proven, ~17s prompt vs ~1s TPM) and C24 (re-enrolled)** | root, console | runbook step 7 |
| ~~13~~ | ~~**B5** orderly shutdown, pull AC at the wall, restore; confirm unattended unlock~~ — **done as C25; server powered itself on and unlocked with 0 passphrase occurrences — this is also the real proof of B1** | console | runbook step 8 |
| ~~14~~ | ~~M02–M05 application deployment, then final acceptance~~ — **done as C26–C47; Phase 7 PASS on all five criteria** | root | guide phase 6 |

**Physically impossible for the agent regardless of privilege:** step 2 (firmware setup), step 12's
console observations, step 13 (AC power), and the Telegram message tests that require the operator's own
account.

## Deviations to declare for replication

1. The agent held no privileged access; every privileged change was operator-executed.
2. `tpm2-tools` is not in either documented install list but is required by `b4-verify.sh:92`; this run
   adds it (a documented, intentional divergence from the guide's 5.1 line).
3. The guide's 5.2 names a key file that does not exist on the workstation, and a stale copy of the SSH
   helper; this run uses `id_ed25519_cloudops.pub` and the repo-root helper, which is the tested one.
   **RESOLVED at C52** — the stale shipped copy was promoted to the hardened version and the guide now names
   the tracked path; this deviation was still open when the work was first committed, which is what C52
   exists to correct.
4. ~~`m04`/`m05` scripts were not modified.~~ **Corrected twice: five files were changed by C36 (`:Z` →
   `:z`) and nine by C50**, all in the repository — C50 item 6 carries the exact before/after identities.
   The sentence is struck through rather than deleted because the counts in it were derived while it was
   still true. The defects that could affect a replication run are itemised in
   the evidence record's `findings_index`; as of C33 that is **7** items under `fix_before_deployment` and
   **11** under `fix_at_leisure`. This item previously hardcoded "six", which went stale as soon as more
   were found — the counts are named here only so a reader can tell the index has grown, and the index
   itself is the authority.
5. **The 5.5 pre-reboot block was pasted into the wrong machine, rebooting the workstation.** The operator
   had exited the server ssh session, so the live prompt was the workstation's; the unguarded block ran
   there and rebooted it. The server was never rebooted by that block. **Impact nil, verified rather than
   assumed:** the server was untouched (same `boot_id` `95d9c7ad-…`, static hostname intact, 0 failed
   units), the workstation returned with 0 failed units and both evidence artifacts intact, and both
   off-host recovery backups re-hashed after the reboot to their recorded values exactly
   (`8b4ca688…` header, `f4b732ad…` crypttab). This is the **fourth** wrong-machine incident of the run
   and it is the **agent's** process failure, not operator carelessness: the evidence record already
   prescribed a paste-safe host guard, and the agent still issued an unguarded multi-machine block.
   Every remaining block is now wrapped in
   `if [ "$(hostname)" != hermes.ai.lab.local ]; then echo WRONG MACHINE; else …; fi` — deliberately **no
   `exit`**, because an earlier `exit 1` guard closed the operator's session. Workstation-only blocks are
   guarded symmetrically against `fedora`. **By-product:** the unintended workstation reboot independently
   proved that the 5.5 `/etc/hosts` change survives a reboot, which is precisely the persistence property
   5.5 exists to demonstrate on the server.
6. Both machines expose a LUKS container at `/dev/nvme0n1p3`; any device-path command must be guarded by
   `cryptsetup luksUUID` (server `8919c2b1-5d9a-4fb9-8f85-97d286cbe7ec`, workstation
   `da58ecdb-2537-4b06-b794-10b8930b43c9`).
7. **The runbook's step order was not followed literally.** The runbook numbers Step 2 (firmware power-loss,
   gate B1) *before* Step 3 (recovery material) and Steps 4–5 (host preparation and runtime account), while
   this run executed Steps 3–5 first and reaches Step 2 last. **The binding constraint is preserved:**
   firmware still precedes TPM2 enrollment (Step 6 / gate B3), which is the dependency that matters, because
   B1 changes firmware settings and therefore can change PCR7. Declared because the runbook is the ordering
   authority for boot sequencing, and a replication following the numbers literally would perform B1
   earlier, before host preparation.
8. **An agent-side defect in the host guards themselves, found by the guard's first real test.** The guards
   warned with `echo "!! WRONG MACHINE …"` in **double** quotes. In an interactive bash shell `!` triggers
   history expansion, so `!!` expanded to the full text of the operator's previous command: the warning
   printed `clear WRONG MACHINE …` in one paste and `exit WRONG MACHINE …` in another. The guard still
   protected the operator — the protection lives in the `if` condition, not the message, and the
   wrong-machine paste was correctly inert — but the output was unreliable, and in the general case an
   expanded previous command could inject misleading text into a message an operator is meant to trust.
   **Fix, applied to every subsequent block: single quotes (which suppress history expansion) and no `!`
   characters in pasted strings.** Recorded because host guards are precisely the code an operator pastes
   blindly, so their output has to be trustworthy.
9. **The gateway was restarted at step 7, which the guide does not do.** `m04-backup.sh` stops
   `hermes-gateway.service` for the backup and never restarts it; in the guide's order the gateway is next
   brought back by `m05-telegram.sh` at step 9, so steps 8 and 10 run against a stopped gateway. This run
   started the gateway manually immediately after the helper finished, both to keep the host in its
   expected live state and because the `.env` investigation below depended on it. **Declared because it
   changes the observable state at step 8:** on a literal replication the gateway is down there, and any
   step-8 output read as evidence of a working system is not. It is also the reason this run could observe
   the gateway appending `API_SERVER_KEY` to `.env` (C33 item 5), and the reason the archive's
   `env_file_sha256` is a **stopped-state** value that goes stale the moment the gateway starts.
