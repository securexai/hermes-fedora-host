# Hermes manual profile — Gate 2 (credential-free lab) execution plan

Record state: **ACTIVE**. Approved 2026-09-20 (America/Bogota), D1 **Option A**, later amended by
D-01/D-02/D5 below.

## 0. Authoritative current status (2026-09-20)

This is the single current status for Gate 2; earlier sections are history and several are
explicitly superseded.

- **Phases 0–5: PASS** on the fresh fixture `lab-hermes-manual-r1` (capacity, media verification,
  fixture creation, kickstart install, Phase 4 baseline 11/11, Phase 5 host preparation 25/25).
- **Phases 6–7 and Gate 3: NOT RUN.** Work stopped after Phase 5 by user instruction. The stopping
  point has not moved and this record does not authorize resuming deployment.
- **Review corrections (2026-09-20):** the review findings against HEAD `2340887` are addressed in
  [the review-corrections record](2026-09-20-hermes-manual-review-corrections.md). Those corrections
  are repository changes with offline evidence only; they are **not** runtime acceptance.
- **Open deviations:** D-01 (no encryption on this fixture), D-02 (kickstart instead of interactive
  install), D-03 (temporary guest sudo grant, root-equivalent in practice), D-04 (guest host key
  pinned by TOFU).
- **Outstanding, not to be closed by inference:** the guest ED25519 host-key fingerprint has **not**
  been verified at the console (D-04). That verification stays outstanding until an operator
  independently confirms it. Historical VM observations in this file are evidence of what was seen on
  those dates; they are not fresh evidence.
- **Containment for the pre-fix host grant (review finding 1):** the revision under review installed a
  host wrapper (`gate2-rebuild-kickstart-iso.sh`) that ran a generator from the user-writable checkout
  as root. If that grant was installed, remove it with
  `sudo bash scripts/hermes/manual/lab/gate2-install-grants.sh --remove`, or reinstall it from the
  corrected source before any further privileged use; the corrected installer places a root-owned
  generator and template in the libexec directory and no longer records or reads a checkout path. The
  agent cannot verify or change the installed grant from this repository.
- **Next action:** request authorization to resume Phase 6 (credential-free application deployment,
  now including `m03-contract.sh`) on the retained fixture. Provider/messaging acceptance and the
  optional encrypted/TPM profiles remain separately gated and NOT RUN.

**Parent record:** [the manual-profile improvement plan](2026-09-20-hermes-manual-profile-improvement.md),
whose remaining runtime gates this plan discharges. **Authority:** the user's Gate 2 authorization of
2026-09-20 (America/Bogota), quoted in §1. **Scope of this document:** planning and its dated execution
record; the authoritative current status is §0.

## 1. Authorization received

| Parameter | Authorized value |
| --- | --- |
| Guest name | `lab-hermes-manual-r1` |
| Retired fixture | `lab-hermes-server` is retired: must not be recreated or reused |
| Inheritance | None. Fresh VM, disk, recovery assets, network attachment and SSH identity |
| Resources | 2 vCPU / 8 GiB RAM / 80 GiB disk |
| Capacity precondition | Verify and report host free disk space first; **do not create the fixture if capacity is insufficient** |
| Network | `fvh-nat` |
| Address | Obtain a fresh DHCP lease; do **not** assign, pin or recover `172.16.99.12` |
| SSH identity | Fresh host identity; no inherited trust |
| Guest reboots | Authorized as required for Gate 2: clean-deployment, idempotent-rerun, update/rollback |
| Retention on success | Retain the fixture temporarily for Gate 3 |
| Retention on failure | Preserve the failed fixture and relevant logs/artifacts for diagnosis; do not destroy immediately |
| Destruction | No destruction of retained diagnostic or Gate 3 assets without explicit approval |

**Superseded in this table by later decisions:** the original D1 description ("interactive install
with custom encrypted partitioning", §1 header) was superseded by **D-02** (kickstart install) and
**D5/D-01** (no LUKS2 on this fixture). The table above is the current parameter set.

**Explicitly out of scope for this authorization:** Gate 3; any provider or bot credential; TPM/PCR7
enrollment or the optional no-input boot profile (Phase 4 of the manual guide); production; commits,
pushes or publication; changes to the physical host beyond creating the one authorized guest.

**Standing constraint from the approved parent plan:** the Gate 3 artifact set and any `CONFIRM-*`
prompt are not involved here. `PRODUCTION_TARGET` and `LAB_TARGET` remain unset; the lab target for
this plan is the guest defined above and nothing else.

## 2. Read-only reconnaissance (performed; no mutations)

Timestamp: 2026-09-20, America/Bogota. All commands were read-only; no `--apply`, no
`virt-install`, no resource created.

### 2.1 Capacity — the required verification

| Filesystem | Type | Size | Used | Available | Use% |
| --- | --- | ---: | ---: | ---: | ---: |
| `/var/lib/libvirt/images` (pool target) | XFS | 246 GiB | 4.8 GiB | **241 GiB** | 2% |
| `/var` (incl. `/var/home`) | btrfs | 217 GiB | 47 GiB | 169 GiB | 22% |

Free inodes on the pool filesystem: **128,849,405** (1% used).

**Capacity verdict: SUFFICIENT for a fresh 80 GiB guest**, on this evidence:

- the guest disk will be a **sparse qcow2** on a dedicated XFS filesystem with 241 GiB free, so a
  nominal 80 GiB disk does not consume 80 GiB; a Fedora Server install with a small toolset plus the two
  container images is expected to occupy roughly 15–30 GiB, and the plan sets a hard floor below;
- the pool filesystem is separate from `/var`, so guest disk growth cannot fill the root/host filesystems;
- `/var` has 169 GiB free for staged media and for profile backups that must not live on the guest.

**Important honesty note:** `/var/lib/libvirt/images` is not listable by this account (mode-restricted),
so its *contents* were not inspected. Confirming that the baseline is empty requires the read-only root
step in §5. The capacity *figures* above come from `df`, which is complete without root.

### 2.2 Virtualization platform

| Item | Observed |
| --- | --- |
| `virsh` / `virt-install` | 12.0.0 / 5.1.0 |
| `qemu-kvm` | 2:10.2.2-1.fc44 |
| `/dev/kvm` | present, mode `crw-rw-rw-` |
| `libvirt-daemon-kvm`, `libvirt-client`, `edk2-ovmf` | installed (the `libvirt` metapackage is intentionally absent on this modular host) |
| Daemon model | `virtqemud.socket` active; `libvirtd.socket` inactive |
| TCP/TLS listeners 16509/16514 | **none** |
| SELinux / firewalld | **Enforcing** / **active** |
| Secure Boot firmware | `OVMF_CODE.secboot.fd`, `OVMF_VARS.secboot.fd`, and an Secure-Boot-**enrolled** descriptor (`30-edk2-ovmf-4m-qcow2-x64-sb-enrolled.json`) are present |

### 2.3 Existing guests, networks and pools

- **Domains: none.** `virsh list --all` is empty, including no `lab-hermes-server`.
- Networks: `default` (NAT, 192.168.122.0/24) and `fvh-nat`, both active and autostart. The retired
  `lab-vlans` (172.16.99.0/24) **does not exist**.
- `fvh-nat`: NAT forward, bridge `virbr-fvh`, host `192.168.124.1/24`, DHCP range
  `192.168.124.2`–`192.168.124.254`, **no current leases** — so a fresh lease is guaranteed and cannot
  collide with a historical address.
- Storage pools: only `default` → `/var/lib/libvirt/images`. The former `hermes-local-media` pool is
  gone, consistent with the recorded 2026-09-19 reset.

### 2.4 Local lab state and identities

- `~/.local/state/hermes-local-vm` (the deleted 172.16.99.12 fixture's state): **absent**.
- `~/.local/state/hermes-manual-lab` (the state dir this plan proposes): **absent**.
- No SSH keypair exists for this account's lab use (only an unrelated `github-securexai` key).
- No `172.16.99.*`, `lab-hermes-server`, `hermes.ai.lab.local` or `10.0.30.10` entries appear anywhere in
  this account's SSH configuration. There is no inherited trust to break.

### 2.5 Blocking gap: install media

**No Fedora Server install media is present on this host.** The only Fedora image found is
`Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2` (583 MB) in a leftover `/var/tmp/fvh-t06-media-*`
directory from the T06 host test, with its CHECKSUM. There is no Server DVD ISO, no Server CHECKSUM and
no Fedora keyring for it.

The virtualization repository's own disposable-guest pattern (`host.py smoke`) is explicitly
*cloud-base image + `genisoimage` cloud-init seed + `virt-install --import`*, requires root, and is
described in its own documentation as a deliberate mutation. It produces a guest with a plain,
unencrypted, single-filesystem root. **That cannot satisfy this profile**, which requires LUKS2-encrypted
storage and a *separate* `/home/hermes` filesystem (Phase 5.7 of the manual guide asserts the mount
point). `libguestfs-tools` (`virt-customize`, `guestfish`) is **not installed**, so the layout cannot be
scripted into a cloud image with present tooling either.

## 3. Decision required before execution

### D1 — Install source (blocking)

| Option | What it means | Assessment |
| --- | --- | --- |
| **A. Fedora Server 44 install (chosen, later amended)** | Operator supplies, or authorizes downloading, the official *Fedora Server 44 DVD ISO* plus its signed `CHECKSUM` and the Fedora release keyring. **As amended by D-02/D-01/D5:** the install was performed by a kickstart (not interactively) and **without LUKS2** on this fixture; a dedicated `/home/hermes` filesystem was still required and was produced. | Chosen: it exercises the documented procedure and the storage contract minus encryption. **The original "interactive, encrypted" wording here is superseded**; see §0 and D5. |
| B. Cloud base image + new LUKS provisioning automation | Install `libguestfs-tools` and write new tooling to create LUKS + `/home/hermes` in the cloud image. | Rejected as the Gate 2 path: new, unproven automation, extra package installation on the host, and it does **not** follow the documented install. Reasonable as a later reproducibility project. |
| C. Reduce scope to an unencrypted guest | Use the cloud image as-is. | Rejected: changes the acceptance criteria. The `/home/hermes` mount assertion, the encrypted-storage support claim and the meaningfulness of the restore test would all be void. Only acceptable as an explicitly *reduced* variant with the support matrix amended — which is a scope change needing separate approval. |

**Requested from the user for D1:** the absolute path to the Fedora Server 44 DVD ISO, its signed
CHECKSUM file and the Fedora keyring file — **or** explicit authorization to download them (URL,
expected size ≈ 2–3 GiB, and the redirect to `/var/tmp` or `~/Downloads`).

The historical certifier document names `Fedora-Server-dvd-x86_64-44-1.7.iso` with SHA-256
`85837793bfa36db6bc709b4cecd2ec116951b87d9c53c3d95eb2fac8dcf7cf1f`. That value is treated as a **lead to
verify against Fedora's published CHECKSUM**, never as trusted input, because it comes from a dated
record rather than from the vendor today.

### D2 — LUKS passphrase handling (SUPERSEDED for this fixture)

**Superseded by D5/D-01:** this fixture has no LUKS volume, so there is no passphrase to handle and
Gate 2 boots are not passphrase-assisted. The constraints below remain the rule for any future
encrypted profile and are preserved as history.

Gate 2 does not enroll TPM auto-unlock, so every boot requires the LUKS passphrase at the console.

- Unlock is an **operator** action in the operator's own terminal.
- **The agent will not receive, type, script, capture, or log the passphrase**, and will not run
  `virsh console` in a captured session. This follows the repository rule against capturing interactive
  terminals that may display secrets.
- The consequence is a real usability cost and a scheduling constraint: Gate 2 needs the operator at the
  console for the install plus three reboots.
- The VNC console will be bound to `127.0.0.1` only.

### D3 — Fresh SSH identity (proposed)

- New dedicated keypair at `~/.local/state/hermes-manual-lab/id_ed25519` (dir `0700`, key `0600`),
  generated during Gate 2. No existing key is reused, and `/var/home/cloudops/.ssh/id_ed25519_cloudops`
  is neither available nor appropriate for this account.
- New empty `known_hosts` in the same directory. **No `accept-new` for the first connection:** the
  guest's ED25519 host-key fingerprint is read at the console and written explicitly, matching the
  documented "verify the fingerprint at the console first" pattern.
- The guest admin account proposed is `aicowork` for fidelity with the guide; the profile now supports
  `HERMES_ADMIN`, which will be exercised as a *separate* variation rather than as the Gate 2 baseline.

## 4. What Gate 2 can and cannot establish

**In scope (credential-free):** platform identity and storage layout; SELinux/Secure Boot/cgroup state;
rootless mappings; actual runtime identity, seals, capabilities, mounts and temporary storage; worker
network isolation and its negative cases; the pinned SSH transport including missing/changed host key;
the real terminal backend probe; the configuration contract; the synthetic file-sync canary path;
resource limits; Quadlet autostart; the credential-free memory-approval probe; stopped-state backup with
an isolated restore; and helper failure paths.

**Reduced by D-01 (encryption dropped for this fixture, user decision of 2026-09-20):** encrypted-storage
acceptance is not exercised. Gate 2 cannot support any claim about LUKS2, about credentials at rest on
encrypted storage, or about TPM/PCR7 unlock. Those remain unverified.

**Out of scope and will be reported as UNVERIFIED, not as passing:**

- **Messaging and provider acceptance.** Gate 3 owns both. A credential-free gateway is *not* a stable
  long-running daemon, so gateway daemon stability, Telegram reply, allowlist enforcement and provider
  inference cannot be established here. The worker's autostart and the transport probe can be.
- **TPM/PCR7 no-input boot.** Optional profile, not authorized here. Gate 2 boots are
  passphrase-assisted, so Gate 2 must not be cited as evidence for the unattended-boot promise.
- **Host OS rollback.** The update/rollback boot exercises staged package updates and a container
  image/manifest rollback, not a Fedora release downgrade.

This split matters: without it, a green Gate 2 could be misread as "the appliance works".

## 5. Execution phases

Owners: **[A]** = agent over SSH/shell; **[O]** = operator at the console.

### Phase 0 — Preflight and capacity gate (root, read-only) [A]

1. `df -hT /var/lib/libvirt/images` and `df -i` — record; require **≥120 GiB available** and **≥1 GiB
   free inodes** on that filesystem.
2. `virsh -c qemu:///system list --all` — require it to contain **no** domain, and specifically no
   `lab-hermes-server`.
3. `virsh pool-list --all --details`; as root `ls -la /var/lib/libvirt/images` — record the baseline and
   require no `lab-hermes-manual-r1*` and no `lab-hermes-server*` artifacts.
4. `virsh net-list --all` — require `fvh-nat` active and `lab-vlans` absent.
5. `virsh net-dhcp-leases fvh-nat` — record; require no lease for the new MAC.
6. `mokutil --sb-state` is *not* applicable to the host; instead record the host's own Secure Boot state
   for completeness.
7. Re-check `git status` in both repositories to confirm no unrelated change is pending.

**Gate:** any capacity figure below the floors, or any surviving retired artifact, **stops the run** and
is reported. No fixture is created.

### Phase 1 — Media and identity staging [A]/[O]

1. Place the Server ISO, CHECKSUM and keyring in a stated directory; `sha256sum` the ISO; verify the
   signed CHECKSUM with `gpgv` against the Fedora keyring. Require an exact match. (Integrity checking
   only — this does **not** invoke the controller/certification tooling and creates no promotion record.)
2. Create `~/.local/state/hermes-manual-lab` (`0700`), generate the fresh keypair, write an empty
   `known_hosts` (`0644`), and record the public-key fingerprint.
3. Record a sanitized baseline: date, host `uname -r`, libvirt/qemu versions, ISO hash, key fingerprint.

### Phase 2 — Create `lab-hermes-manual-r1` [A]

`virt-install` with, at minimum:

- `--name lab-hermes-manual-r1`, `--memory 8192`, `--vcpus 2`, `--cpu host-passthrough`
- `--machine q35`, `--boot uefi` with **Secure Boot enabled** (the firmware-enrolled descriptor)
- `--disk path=/var/lib/libvirt/images/lab-hermes-manual-r1/disk.qcow2,size=80,format=qcow2,bus=virtio,discard=unmap`
  — sparse, in its own guest directory so cleanup is bounded
- `--network network=fvh-nat,model=virtio` — a **freshly generated** MAC; no pinned historical MAC
- `--graphics vnc,listen=127.0.0.1`, `--noautoconsole`
- **No** `--import`, no cloud image, no `lab-hermes-server` naming, no 172.16.99.0/24 network

Then record `virsh dumpxml` (sanitized), the assigned MAC, and the fresh DHCP lease from
`virsh net-dhcp-leases fvh-nat`, and require the address to be inside `192.168.124.0/24`.

### Phase 3 — Fedora Server 44 install [O], supervised by [A]

Interactively at the console. **Amended by D5/D-01: no LUKS2 on this fixture.** Everything else stands.

- storage: **unencrypted** (deviation D-01). Do not enroll TPM either; that profile is out of scope.
- custom layout producing a **dedicated filesystem mounted at `/home/hermes`** — proposal to type:
  `/boot/efi` 1 GiB, `/boot` 2 GiB, LVM for the remainder, LVs `root` 20 GiB, `var` 15 GiB,
  `hermes` 30 GiB XFS, `swap` 4 GiB. The guide says not to force the reference host's numbers, so
  **record what the installer actually produces**. Required: `/home/hermes` is a **separate filesystem**
  of ≥20 GiB. This is not optional — the helpers abort when it is not a mount point;
- administrator `aicowork` in `wheel`;
- Secure Boot left enabled; SELinux left enforcing.

**Recorded as deviations:** any step where the installer, the media or the operator departs from the
guide's text — this is the deviation-counting exercise the guide asks for.

### Phase 4 — Fresh-guest precondition inspection [A]

Over SSH, after the console host-key fingerprint has been verified and written:

`lsblk`/`findmnt` layout, `cryptsetup luksDump` (require keyslots=1, TPM tokens=0), `mokutil --sb-state`
(enabled), `getenforce` (Enforcing), cgroup v2, kernel and OS release, free space under `/var` and on
`/home/hermes`, `getent passwd` for both accounts, `subuid`/`subgid` ≥65,536, `newuidmap` present.

**Gate:** storage or security state that contradicts the support matrix stops before deployment and is
reported. The guest is preserved.

### Phase 5 — Host preparation (manual guide Phase 5) [A], console steps [O]

Controlled update; package set (including `tpm2-tools`, which the guide records as non-optional for the
boot checks but which Gate 2 uses only for inspection); key-only SSH with a **new connection proof and a
negative test**; firewall review with a timed rollback and fresh-connection proof; bounded journal;
download-only update policy; static hostname and reboot; runtime account; directories; the
user-manager drop-in **with the `/home/hermes` mount assertion**; rootless verification; slice budget.

Each step records expected vs actual, and any departure becomes a deviation entry.

### Phase 6 — Application deployment with the improved helpers [A]

**Reviewed sequence (updated 2026-09-20 to close review finding 8):**

1. Stage the **whole** `scripts/hermes/manual/` tree and supply
   `HERMES_EXPECT_MACHINE_ID_SHA256` from the guest baseline.
2. `provision-worker-client-key.sh`; `m02-deploy-and-validate.sh --apply`;
   `m03-activate.sh --apply`; `m03-configure-and-probe.sh --apply`;
   **`m03-contract.sh --apply`** (credential-free contract application and verification);
   `m04-posture.sh --apply`; `m04-backup.sh --apply`.
   `m03-contract.sh` is where the configuration contract is actually applied and verified;
   `m04-posture.sh` only installs the helper. Omitting it left the contract unapplied.
3. Run the memory-approval probe and the synthetic file-sync canary checks.
4. **Stop before credential provisioning.** `provision-openai-key.sh` and `provision-telegram.sh` are
   **not** run; `m03-accept.sh`'s provider calls are **not** run. Helper checks that depend on a
   provider or on a stable gateway daemon are recorded with `mp_defer` as explicitly deferred to
   Gate 3 — never as PASS. Gate 3 owns provider and messaging acceptance.
5. Negative checks: worker IPv4 and IPv6 egress with the probe tool **present** (an absent tool is
   UNVERIFIED, not isolation); missing and changed worker host key; stopped worker; missing data mount;
   missing/malformed profile; wrong mode on `worker.sock`.

Evidence: each helper's own `.out` log (mode 0600) plus a sanitized JSON per gate.

### Phase 7 — Reboot persistence and rollback (three boots) [O] unlocks, [A] verifies

| Boot | Test | Required observations |
| --- | --- | --- |
| 1 | Clean-deployment boot | distinct boot ID; worker unit and container autostart with no manual start; transport probe passes; memory probe passes; no published ports; no new AVC denials; `/home/hermes` still the asserted mount |
| 2 | Idempotent-rerun boot | re-run the Phase 6 helpers with `--apply`; config/`.env`/host-key/pin hashes unchanged; no duplicate `.env.pre-*`; no drift; then boot and re-verify as boot 1 |
| 3 | Update/rollback boot | apply staged Fedora updates offline; re-verify the profile; roll the container image/manifest pin back to the previous digest and forward again, verifying the pin and the transport each time |

Gateway daemon stability is measured but reported **UNVERIFIED** (no messaging platform configured).
Boot IDs are recorded so three distinct boots are provable.

### Phase 8 — Evidence, retention, decision [A]

- Sanitized evidence under `docs/plans/evidence/2026-09-20-hermes-manual-gate2-*.json`, plus
  `git status`/revision fingerprints for both repositories and the artifact hashes under test.
- **Success:** retain `lab-hermes-manual-r1` for Gate 3. No destruction.
- **Failure:** retain the guest, its disk, `virsh dumpxml`, sanitized journals and helper logs for
  diagnosis. No destruction.
- Destruction of retained assets requires explicit approval and will not be inferred from silence.

## 5a. Execution record so far

Evidence: [phase 0 / media / identity JSON](evidence/2026-09-20-hermes-manual-gate2-phase0-media.json).

- **Phase 0 capacity gate: PASS.** `/var/lib/libvirt/images` (XFS) has **241 GiB** available and
  **128,849,405** free inodes, against floors of 120 GiB and 1,000,000. A first check reported FAIL
  because the check command itself was wrong (`df -i` combined with `--output=`, then comparing an empty
  string); it was corrected and the false result is recorded.
- **Phase 0 baseline: clean.** 0 domains, no retired `lab-hermes-server`, no `lab-vlans`, only
  `default` + `fvh-nat` networks, 0 leases on `fvh-nat`, only the `default` pool, SELinux Enforcing,
  firewalld active, no libvirt TCP/TLS listener.
- **Phase 1 media: downloaded and verified.** `Fedora-Server-dvd-x86_64-44-1.7.iso`, 3,913,023,488 bytes,
  SHA-256 `85837793…cf1f` — verified twice: signature verified against **two independent trust paths**
  (the vendor `fedora.gpg` keyring and the locally rpm-trusted `fedora-44-primary` key), and the hash
  re-checked after the download completed. The value that previously existed only in a dated document is
  now corroborated by the live vendor signature.
- **Phase 1 identity: fresh.** `~/.local/state/hermes-manual-lab` (0700) with a new passphrase-less lab
  key (0600, fingerprint `SHA256:Zn4aHfyBo/R7QH6Invg+NokZL3ThwFtsSQQuqMJcPJg`) and an empty
  `known_hosts`. No prior key, state or trust is reused.
- **Phase 2 definition validated without mutation.** `virt-install --dry-run --print-xml` accepts the
  definition: q35, Secure Boot enabled, 8 GiB, 2 vCPU, virtio disk, NIC on `fvh-nat` with a freshly
  generated MAC, and **VNC bound to 127.0.0.1 only**. Proof of no mutation: 0 domains, 0 volumes, no
  guest directory, pool still 241 GiB.
- **Near-miss, corrected.** The first check used `--print-xml 9`; in virt-install a step number selects
  *which install phase* to print, and bare `--print-xml` still performs storage creation. Nothing was
  created (verified), and the check now uses `--dry-run --print-xml` with no step number. Recorded
  because a near-miss that could have created a guest outside the approved sequence belongs in the record.
- **Phase 2 attempt 1 FAILED — no fixture created; nothing to clean up.** `--create` aborted because the
  install ISO lived under `/var/home/aicloudopspecial` (mode `0700`) and QEMU runs as the `qemu` user, so it
  could not read the media (`Permission denied`). `virt-install` had already warned about exactly this.
  State afterwards: domain **not** defined, disk **not** present, cleanup **not** required, and **no
  destructive action taken**. The only leftover is the empty guest directory the retry reuses.
- **Fix:** the helper now decides a qemu-readable media path *before* allocating anything. As root it proves
  readability with `runuser -u qemu -- test -r` and stages a re-verified copy under
  `/var/lib/libvirt/boot/<domain>/` when the source is unreadable; unprivileged `--check` reports the same
  condition statically. A final pre-allocation guard fails closed if the media is still unreadable.
- **Phase 2 attempt 2 SUCCEEDED.** The helper staged a re-verified media copy where `qemu` can read it and
  created the guest. Verified afterwards: q35 (`pc-q35-10.2`), Secure Boot + enrolled keys, 2 vCPU,
  8 GiB, virtio disk on `vda`, NIC on `fvh-nat` with a fresh MAC `52:54:00:94:58:36`, the **staged** ISO as
  cdrom, sVirt label enforcing, no `172.16.99` reference anywhere, and VNC on **127.0.0.1:5900 only**. The
  disk is sparse — pool availability is unchanged at 241 GiB. `virsh domdisplay` prints
  `vnc://127.0.0.1:0`; the domain XML and a listening socket confirm the real endpoint is
  `127.0.0.1:5900` (the `:0` is the VNC display number).
- **~~Awaiting Phase 3 (operator).~~ SUPERSEDED — kept as history.** Phase 3 was completed by the
  kickstart path (D-02) with **no encryption** (D5/D-01), and Phase 4 followed. The original text
  ("interactive … with encrypted storage") no longer describes what happened or what is required.

### D5 — Encryption dropped for this fixture (decided)

On 2026-09-20 the user directed that the Gate 2 fixture be installed **without LUKS2 encryption**, after the
agent reported that the libvirt images pool sits on a raw, unencrypted partition. This is a **scope
reduction**, recorded as deviation **D-01**, not a change to the product posture.

Accepted consequences:

- Gate 2 becomes a **reduced profile**; encryption-related acceptance is **not exercised** and Gate 2 must
  not be cited as evidence for the encrypted-storage path.
- Gate 3 credentials would sit on an unencrypted guest disk on an unencrypted host partition. This is an
  explicit, recorded risk acceptance.
- `cryptsetup` keyslot/token inspection is **NOT_APPLICABLE** for this fixture.
- The optional TPM/PCR7 no-input boot profile becomes **structurally impossible** here: there is no LUKS
  volume to bind a token to. That profile stays unverified and untouched.

**Not** reduced by this decision: Secure Boot stays enabled; a **dedicated `/home/hermes` filesystem of
≥20 GiB stays mandatory** (every manual helper begins with `mountpoint -q /home/hermes` and stops otherwise);
SELinux stays enforcing; the offline worker and pinned transport are unchanged.

**Refinement (agent analysis, recorded after the decision).** For *this* gate the reduction costs little:
Gate 2 is credential-free, so there is nothing on the guest disk worth protecting. The cost lands on Gate 3,
where real tokens would be written: the practical lab risk is that a `qcow2` is a copyable file — the
retention policy itself plans to preserve the disk on failure — so every copy of an unencrypted image is a
plaintext credential store. Guest LUKS would protect data at rest only, never against a compromised host.
The stronger option, if wanted later, is to encrypt the **host images pool** (`/var/lib/libvirt/images` is
currently raw `/dev/nvme1n1p4`): one host-boot unlock covers every guest with no per-guest prompts. That is a
separate host-change project needing its own authorization.

**Host-pool encryption: DECLINED (2026-09-20).** Requested and then withdrawn before any artifact or change was made. No host disk was encrypted, moved, unmounted, reformatted or wiped; the images pool remains on raw `/dev/nvme1n1p4`.

**Gate 3 precondition G3-PRE (OPEN).** Before Gate 3 provisions any real credential, the credential-at-rest
decision must be taken explicitly — accept unencrypted storage with short-lived revocable spend-capped lab
credentials, give this fixture LUKS, or encrypt the host pool. This is not a Gate 2 blocker; it becomes one
the moment real tokens exist.

A separate, unaddressed finding stands on its own: **the VM images pool is not encrypted at the host level**
(`/dev/nvme1n1p4`, XFS, outside the LUKS container that holds `/var/home`). That affects any guest on this
host, including Gate 3, and is recorded in the evidence file rather than fixed here.

### D-02 — Install method automated (deviation)

The plan's Phase 3 specifies an interactive console install. It is instead performed by a **kickstart** on an
`OEMDRV`-labelled ISO, at the user's request, because the manual partitioning step is where a wrong
configuration was actually made ("Automatic partitioning selected", which would not have created
`/home/hermes`), and a repeatable fixture is a stated project goal. **Everything after the install still
follows the guide.** Artifacts: `lab/gate2-kickstart.ks.in`, `lab/gate2-make-kickstart.sh`.

Fixed by the kickstart: `/boot/efi` 1 GiB, `/boot` 2 GiB, LVM `vg_hermes` with `/` 20 GiB, `/var` 15 GiB,
**`/home/hermes` 30 GiB (required)**, swap 4 GiB; no encryption (D-01); root locked; `aicowork` in `wheel`
with a locally-hashed password and the lab SSH key; SELinux enforcing; firewalld enabled; firstboot disabled.

**Not validatable locally:** `pykickstart`/`ksvalidator` is absent, so the kickstart is not machine-validated.
Anaconda reports parse errors at boot, visible in the console screenshot. One omission was caught by review
before use: no install source was declared, which matters because two CD-ROMs are attached — `cdrom` is now
explicit.

### Progress — install and Phase 4

- **Phase 3 (kickstart install): SUCCESS.** The OEMDRV mechanism worked once the file parsed; the guest booted
  into Fedora 44 Server with hostname `lab-hermes-manual-r1` and the media ejected.
- **Phase 4 (baseline): PASS** — 11 checks, 0 failures, 0 unverified, run through the granted guest rule.
  **`/home/hermes` is `vg_hermes-lv_hermes`, a separate XFS filesystem**, which the whole profile depends on.
  SELinux Enforcing, Secure Boot enabled, cgroup v2, time synced, `aicowork` in `wheel`. Encryption reported
  `NOT_APPLICABLE` per D-01 rather than failing.
- **New deviation D-04:** the guest host key was pinned by TOFU (`ssh-keyscan`), not verified at the console as
  the plan required. Fingerprint `SHA256:1f39et9Z…zcQ`. Operator confirmation at the console is outstanding.
- **New defect F-07:** unprivileged libvirt access is intermittently denied (2/10 in 30 s, active seat0 session,
  healthy daemon). Cause unproven; a granted observation wrapper exists but is not deployed because
  retry-wrapper observation suffices.
- **Phase 5 (host preparation): PASS** — 25 checks, 0 failures, 0 unverified. Key-only SSH is enforced
  (`passwordauthentication no`, and a password-only attempt is refused with `Permission denied (publickey)`),
  the firewall zone is `FedoraServer` with `dhcpv6-client ssh`, Cockpit's socket is disabled, the journal is
  bounded, updates are download-only, the runtime account `hermes` (uid 1001, nologin, locked, no sudo,
  subuid/subgid 65536) exists, `/home/hermes` is a separate filesystem with the mount assertion installed, and
  rootless Podman reports `rootless=true` with its store on `/home/hermes`. No AVC denials recorded.
- **Two more defects of mine fixed (F-08, F-09):** `firewall-cmd --get-active-zones` returns
  `FedoraServer (default)`, and passing that annotated string as a zone name made the SSH helper reject it —
  three checks failed from that one cause. Separately, `ausearch` exits non-zero when it finds nothing, which
  my check misread as unmeasurable.

### Stopping point

Per the user's instruction, work stops after Phase 5. **Phases 6 and 7 and Gate 3 are NOT run.** The fixture
`lab-hermes-manual-r1` is running and retained; nothing was destroyed. Phase 5's own log notes that `dnf`
upgraded `nmcli` while the old NetworkManager was running, so the guest logs a version-mismatch advisory — the
procedure reboots before deployment anyway.

### Failure log — kernel-side media loss (F-03)

The first kickstart boot failed with `BdsDxe: No bootable option or device was found.`: the domain's `sda` cdrom
had lost its `<source>`, so the guest had no bootable media. The DVD file was intact and `qemu`-readable, and
no eject command exists anywhere in the record. The most likely mechanism is that the live installer's device
probing opened the tray and a subsequent `attach-disk --config` persisted that empty-tray state — recorded as a
**hypothesis, not a proven cause**. The granted wrapper is now idempotent: it verifies and repairs both optical
media, checks `qemu` readability and root ownership, and only then restarts the guest. The kickstart ISO is now
attached explicitly on the SATA bus rather than libvirt's SCSI default.

### D-03 — Temporary guest privilege grant (deviation)

The kickstart `%post` installs `/etc/sudoers.d/90-hermes-manual-lab`, letting `aicowork` run the staged helpers
under `/usr/bin/bash` as root without a password. **Honest assessment: this is root-equivalent in practice** —
the helpers run arbitrary commands as root, so the grant's narrowness is largely cosmetic. It is acceptable
only because this guest is disposable and credential-free during Gate 2. **Cost:** Gate 2 does not validate
the reference posture of "password required, no NOPASSWD entry"; that needs a separate run with
operator-executed privileged steps. Safety: validated with `visudo -cf` and removed if validation fails.

The **host** grant is genuinely narrow: one argument-free wrapper in `/etc/sudoers.d/90-hermes-gate2-lab`,
installed and removed by `lab/gate2-install-grants.sh`. A naive `virsh *` grant was rejected as
root-equivalent (it would allow attaching a host partition to a guest).

### D4 — Privileged access (surfaced during execution; needs your decision)

`sudo -n true` fails for this account, and the pool directory is root-only.

- **Host side:** the reviewed [`lab/gate2-create-fixture.sh`](../../scripts/hermes/manual/lab/gate2-create-fixture.sh)
  is written for you to run once with `sudo`. Its `--check` mode needs no root and already passes.
- **Guest side options:**
  - **(a) Recommended:** you execute the privileged guest helpers over your own SSH session; the agent
    analyses the mode-0600 logs it owns as `aicowork` and maintains the evidence. This matches the
    2026-09-14 practice (that run's deviation #1) and leaves the posture under test unmodified.
  - **(b)** You grant a temporary, documented, revertible sudo rule for the staged helper paths only.
    Faster, but a deviation that must be recorded and reverted.
- **The agent will not enter a sudo password and will not handle the LUKS passphrase** (D2).

## 6. Stop conditions

1. Capacity below the §5 Phase 0 floors → stop before creation.
2. Media absent or its checksum/signature unverifiable → stop (D1 unresolved).
3. Any required check `FAIL`s, or any required check is `UNVERIFIED` → the gate is **incomplete**, not
   passed; preserve and report.
4. Unexpected AVC denials, SELinux left permissive, or Secure Boot disabled → stop and preserve; never
   install an `audit2allow` policy or relax a control to proceed.
5. Any step that would touch the production target, the physical host's configuration, or a real
   credential → stop.
6. Free space on `/var/lib/libvirt/images` dropping below **60 GiB** during the run → stop and report
   before continuing.
7. A request to destroy a retained fixture without explicit approval → refuse.

## 7. Risks and limitations of this plan

- **Operator dependency at the console** for the install plus three unlocks (D2). Gate 2 cannot be fully
  autonomous, by design.
- **Gate 2 is not appliance acceptance.** Provider/messaging and the unattended-boot promise remain
  unproven until Gates 3 and 4.
- **The interactive install is not bit-reproducible.** Deviations are expected and recorded; a later
  kickstart-based install is a separate improvement, deliberately not part of Gate 2 because Gate 2 must
  test the documented procedure.
- **Host package installation** is limited to the virtualization/perception tooling already present; no
  host change is planned. If option B for D1 were ever chosen it would require installing
  `libguestfs-tools` on the host, which needs its own approval.
- **Sparse disk math.** Nominal 80 GiB is not allocated up front, but the pool filesystem is monitored and
  has a hard floor.
- **Retained fixture becomes credential-bearing at Gate 3.** From that point it must be treated as
  sensitive even though Gate 2 itself stores no real credentials.
- **`hermes-manual-lab` state is a new identity.** Nothing from the retired fixture is reused, so any
  historical runbook fragment that assumes the old address or user is inapplicable here.

## 8. Approval record (historical)

Approved 2026-09-20 (America/Bogota): the plan as written, D1 **Option A**, with the agent authorized to
download and verify the install media. **Items 2 and 5 below were later superseded** by D5/D-01 (no
LUKS2 on this fixture) and D-02 (kickstart install); they are preserved as the record of what was
approved at the time.

1. **D1:** Option A — official Fedora Server 44 DVD ISO; agent downloads and verifies CHECKSUM + signature.
2. **D2:** confirmed — the operator performs the console install and the LUKS unlocks; the agent must not
   handle the passphrase. *(Superseded for this fixture: no LUKS volume exists.)*
3. **D3:** confirmed — fresh keypair under `~/.local/state/hermes-manual-lab`, console fingerprint
   verification before the first connection. *(Fingerprint verification is still outstanding — D-04.)*
4. **§4/§5/§6:** confirmed as written.
5. **Phase 3 shape:** confirmed — encrypted storage with a dedicated `/home/hermes` ≥20 GiB; exact sizes
   recorded from the installer rather than forced. *(Superseded: unencrypted, per D5/D-01; the separate
   `/home/hermes` requirement stands and was met.)*

On approval, this record becomes ACTIVE, the parent record's remaining-gates entry points here, and
execution begins at Phase 0 — which re-verifies capacity before anything is created. *(Done; see §0 for
the current status and next action.)*
