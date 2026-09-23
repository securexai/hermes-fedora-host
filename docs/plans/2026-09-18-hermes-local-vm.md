# Local Fedora Server 44 Hermes VM

Record state: COMPLETE

## Approved baseline

The user approved creation on the current Kinoite workstation of a Fedora Server 44
VM ready for manual Hermes deployment: 2 vCPUs, 8 GiB RAM, 40 GiB disk, LUKS-encrypted
system volume, Secure Boot, and the existing host console passphrase helper.
The helper must run on every cold start or reboot; this is not TPM-based unlock.
EFI and boot partitions remain unencrypted. Keep VM autostart disabled.

Use the legacy creator in [the VM guide](../VM_TESTING_GUIDE.md), without TPM staging
or unattended Hermes services. Store the disk on the existing XFS partition mounted
at `/var/lib/libvirt/images`. No repartitioning, production operations, provider
authentication, Hermes application installation, commits or pushes are in scope.
Retain the guest for the next manual deployment step. No production secrets may
enter this fixture, which uses a published disposable encryption passphrase.

Approval reference: conversation instructions to proceed after selecting the
VM-ready milestone, manual deployment and the existing console unlock helper.

## Tasks and gates

| ID | Task | Progress | Gate and expected result | Gate status |
| --- | --- | --- | --- | --- |
| H01 | Host prerequisites | DONE | Required tools active, KVM available, resources sufficient | PASS |
| H02 | Verified Server 44 media and dedicated SSH key; depends on H01 | DONE | Signed checksum and pinned SHA-256 match; private key protected | PASS |
| H03 | Storage, network and guest creation; depends on H01/H02 | DONE | No collisions; production destinations blocked; installation completes | PASS |
| H04 | Boot and runtime checks; depends on H03 | DONE | Server 44, Secure Boot, LUKS, SELinux, pinned SSH and rootless Podman pass | PASS |
| H05 | Lifecycle and documentation; depends on H04 | DONE | Cold start/reboot unlock pass; smoke container removed; usage and cleanup documented | PASS |

## Evidence history

### Initial host inspection, 2026-09-18 (America/Bogota)

- MikroTik worktree was clean on main; created `codex/hermes-local-vm` for this record.
- Host: Fedora Kinoite 44.20260918.0, rpm-ostree idle, no pending deployment.
- KVM device exists; CPU has 8 cores/16 threads. Approximately 25 GiB RAM available.
- Dedicated XFS partition: about 241 GiB free; mounted read-write on the real host.
- Image directory is root:root 0755; user cannot directly write there.
- libvirt, qemu-kvm, virt-install and edk2-ovmf packages are absent.
- Podman is rootless with overlay storage in encrypted home storage.
- Host route is 192.168.99.0/24; planned lab subnet 172.16.99.0/24 has no observed route collision.
- `sudo -n true` fails: interactive authentication is required. No password requested or recorded.
- Devbox is absent from host PATH. Repository offline checks have not run.
- Fedora 44 distribution signing key is installed; installer media was not found in Downloads.

### Host package staging completed, 2026-09-18 (America/Bogota)

- Executed through the normal host authorization interface:
  `rpm-ostree install --idempotent --allow-inactive qemu-kvm libvirt libvirt-client virt-install edk2-ovmf xorriso`.
- After the conversation interruption, `rpm-ostree status` confirms State: idle and
  a pending deployment with 166 added packages and all requested layered packages.
- The booted deployment remains unchanged; `virsh`, `virt-install`, `qemu-img` and
  `xorriso` are not yet available. H01 remains BLOCKED on a workstation reboot.
- No Cockpit installation, firewall modification, partition change or reboot was performed.
- `bash -n` passed for the existing VM creator, common shell library and console shell helper.
  This is syntax evidence only, not VM runtime verification.
- Source revision before the new record: `8e13ae4404d39469676622337492e7d255c4235a`.
  The only worktree addition is this execution record. No implementation scripts changed.
- Repository Devbox checks remain unrun because Devbox is absent. Direct host checks
  were used for package state; no repository validation pass is claimed.

### Post-reboot resumption, 2026-09-18 16:49 (America/Bogota)

- Resumed on `codex/hermes-local-vm`; the only worktree addition remains this record.
- Direct host checks outside the execution sandbox confirm `rpm-ostree` is idle
  and the booted deployment contains all six requested packages: qemu-kvm
  10.2.2, libvirt/libvirt-client 12.0.0, virt-install 5.1.0, edk2-ovmf
  20260812 and xorriso 1.5.8. The reboot prerequisite is satisfied.
- `/dev/kvm` exists on the host; 16 online CPUs, about 26 GiB available RAM
  and 241 GiB free on the existing XFS image partition satisfy resource thresholds.
  The sandbox itself hides KVM and libvirt sockets; its absence checks are not
  host evidence.
- `virsh -c qemu:///system list --all` failed because the daemon socket is absent.
  An initial modular-socket activation request timed out. Inspection of
  `vm/lib-vm-common.sh` confirmed the legacy creator explicitly requires active
  `libvirtd.service`; the subsequent `systemctl enable --now libvirtd.service`
  request also timed out awaiting authorization. Final host checks show both
  `libvirtd.service` and `virtqemud.socket` disabled and inactive. Neither request
  established a working hypervisor. `sudo -n true` requires a password.
- Storage is currently root:root mode 0711; narrowly scoped operator storage
  access remains unresolved. No Fedora Server media was found directly in Downloads.
  Host IPv4 routes still show no overlap with `172.16.99.0/24`.
- Devbox and Nix remain unavailable, so required repository checks have not run.
  No validation pass is claimed for this record update. H01 remains BLOCKED on
  administrative service activation; H02-H05 remain NOT_RUN.

### Direct-host continuation, 2026-09-18 (America/Bogota)

- User explicitly retired Devbox for this work; use directly available host tools.
  This supersedes the Devbox prerequisite above, without waiving applicable checks.
- The operator enabled `libvirtd.service` locally. Live verification confirms it
  active and `virsh -c qemu:///system list --all` succeeds with no guests.
  Only the existing `default` network is present; no storage pools are defined.
  H01 passes with the previously verified resources and installed tools.
- Direct `bash -n` passed for the creator and both shell libraries.
  Direct `./tests/test-hermes-guide.sh` passed all 217 checks.
  ShellSpec, ShellCheck, shfmt and markdownlint-cli2 are not installed on PATH.
- H02 passes. Media and the dedicated SSH identity are stored outside Git in
  `/var/home/aicloudopspecial/.local/state/hermes-local-vm` (0700). The private
  `id_ed25519` is 0600, generated specifically for this disposable guest.
  The DVD is `Fedora-Server-dvd-x86_64-44-1.7.iso`, 3913023488 bytes, SHA-256
  `85837793bfa36db6bc709b4cecd2ec116951b87d9c53c3d95eb2fac8dcf7cf1f`.
  Download source: Fedora's official release mirror redirector under
  `https://download.fedoraproject.org/pub/fedora/linux/releases/44/Server/x86_64/iso/`.
  The signed checksum verifies against the installed Fedora 44 distribution key,
  fingerprint `36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6`, and matches the
  repository pin. The first gpgv attempt rejected the ASCII-armored key format;
  dearmoring that same installed public key into `fedora-44.gpg` resolved it.
  `verified-checksum` retains the verified payload. The completed ISO hash passed.
- Root firewall inspection through desktop authentication found only firewalld
  and libvirt network tables. Prepared
  [`hermes-local-vm.nft`](../../vm/networks/hermes-local-vm.nft), scoped to
  `virbr-lab`, for H03. It preserves unrelated tables, permits lab DNS/DHCP
  and established replies, and drops guest-initiated private-network access,
  other host access and forwarded IPv6. It must be checked and applied before
  creating the network or guest. These are runtime rules: reapply after a host
  reboot before starting the lab. Their dedicated-table replacement follows
  the [nftables chain semantics](https://wiki.nftables.org/wiki-nftables/index.php/Configuring_chains).
  No network isolation pass is claimed before privileged validation and live probes.
- A later `virsh domcapabilities` request was denied by host policy; the earlier
  successful empty-domain inventory remains historical evidence, not proof of
  continued authorization. H03 is blocked pending local administrative
  authentication for the firewall check and hypervisor operations. Both dedicated
  guest storage paths remain absent. `git diff --check` passed for tracked changes;
  the new record and nft file remain untracked and require separate review.

### Installer launched, 2026-09-18 (America/Bogota)

- The operator completed desktop authentication. A fail-fast privileged sequence
  confirmed no guest, network or dedicated storage collisions, passed
  `nft --check --file vm/networks/hermes-local-vm.nft`, applied the rules and
  read back the dedicated table before starting the lab network.
- Copied the ISO to root-owned `/var/lib/libvirt/images/hermes-local-media/`,
  verified the pinned SHA-256 again and restored its SELinux context. The legacy
  creator runs as root; no operator write permission was granted to the image pool.
- Defined and started `lab-vlans`, explicitly disabling its autostart. The existing
  default network was preserved. The creator allocated the 40 GiB guest disk and
  launched installation with 8 GiB RAM and 2 vCPUs. Installation is still pending;
  H03 does not pass until installation and network protection checks complete.
- Whitespace checks passed for both new files, and relative links in this record
  resolve. These checks do not substitute for Markdown lint or guest acceptance.

### Initial guest acceptance, 2026-09-18 (America/Bogota)

- Installation completed after 215 seconds. The creator detached installer media,
  started the guest, observed the LUKS prompt and submitted the disposable value.
  SSH became responsive. Domain UUID: `5e5eae87-7a80-4214-bfaf-cb2363f2b330`.
  Both domain and lab network have autostart disabled.
- Guest checks confirm Fedora Server 44, `SecureBoot enabled`, SELinux `Enforcing`,
  a LUKS partition on `/dev/vda3` containing root and swap LVs, with EFI and `/boot`
  unencrypted. The root LV is 33 GiB. Rootless Podman reports `true`.
- The VM has a guest-agent channel, but `qemu-guest-agent` is not installed.
  Attempted host-key retrieval through that channel failed. Used the existing
  certifier's `StrictHostKeyChecking=accept-new` procedure on the isolated fixture;
  this is trust on first use, not independently authenticated key enrollment.
  All subsequent SSH commands require `StrictHostKeyChecking=yes` and the dedicated
  `known_hosts` file. The bridge neighbor matched `52:54:00:ab:10:03`.
- Probes to unused addresses in 10/8, 192.168/16 and 172.16/12, plus host port 9,
  timed out under the applied lab rules. No production destination was probed.
  Public registry access worked: rootless `fedora-minimal:44` printed
  `ROOTLESS_CONTAINER_OK`. The temporary container and image were removed;
  container and image inventories are empty.
- `guest-validation.log` and `unlock-events.log` in the private state directory
  retain runtime and initial-unlock evidence. Initial boot ID:
  `4867c6ce-877d-4b7a-aa38-b7304e419dc1`.
- Limitation: `mcelog.service` fails because mcelog reports unsupported AMD
  processor family 25. No service change was made; this is not an all-services-
  healthy claim. The requested OS security and Podman gates passed.
- Added [usage and recovery guidance](../HERMES_LOCAL_VM.md). Isolated copies of
  the two new Markdown files pass markdownlint-cli2 0.23.2 with repository rules
  and fixes disabled. The initial broader lint invocation made no tracked changes;
  only the focused two-file run is used as documentation lint evidence.

### Warm-reboot failure and recovery preparation, 2026-09-18 (America/Bogota)

- The bounded lifecycle check used `virsh reboot` with the watcher preattached.
  SSH did not return, and the watcher recorded no reboot marker, boot boundary
  or unlock submission. The display shows the LUKS prompt; retained screenshot:
  `virsh-reboot-luks-prompt.png` in the private state directory.
  The helper correctly withheld input without its required marker sequence.
- `lifecycle-validation.log` preserves this attempt and the firewall readback:
  six forwarded packets matched the private-address drop rule; the host input
  drop counter was also nonzero. Only the guest disk remains attached.
- Leading hypothesis: the hypervisor reboot path does not emit the guest-side
  marker expected by this watcher. Prepared a bounded retry using in-guest
  `systemctl reboot`, after one-shot prompt-gated recovery. No watcher matcher or
  safety condition was weakened. The retry first waits for the initial check
  and watcher to exit; it never starts competing console helpers.
- H05 remains failed until actual warm-reboot and cold-start acceptance succeeds.
  The current guest is at its LUKS prompt, not ready for application deployment.
  Updated the usage guide to request reboots from inside Fedora; final validation
  remains pending.

### Lifecycle acceptance, 2026-09-18 17:24 (America/Bogota)

- The first lifecycle command exited 1 after its bounded SSH wait. One-shot
  recovery passed without changing the helper; an empty console input refreshed
  the existing prompt, and the helper submitted the fixture value only after
  matching that prompt. Recovery boot ID:
  `cf24787c-0ebe-462b-8a4d-ba26b392a381`.
- The previous guest journal confirms the cause of the missing reboot marker:
  `virsh reboot` generated a short power-key event and `poweroff.target`, not
  the guest reboot marker. The in-guest `systemctl reboot` retry produced the
  required reboot, cryptsetup boundary and prompt sequence. It passed with boot ID
  `2043c65c-26a9-4699-82f8-e619745ec3a3`.
- Graceful shutdown reached `shut off`. A subsequent cold start and one-shot
  unlock passed with boot ID `7b214298-6b4e-438f-a920-bc9ad9c3527a`.
  Pinned SSH returned; Secure Boot remained enabled, SELinux enforcing and Podman
  rootless. The guest is retained running, with both autostart settings disabled.
- `lifecycle-retry.log` preserves successful recovery, warm reboot, cold start,
  firewall counters, detached media and final domain/network settings. Ordered
  events are in `unlock-events.log`. No watcher remains active after validation;
  follow the usage guide to attach one before future reboots.
- Public ED25519 SSH fingerprint:
  `SHA256:D9BRJdr/5Zd/SXj3aev3UMBeBm9ApfnAiWS0F6CWy8o`.
  Private key and host-pin files are owner-only within the 0700 state directory.
- Runtime acceptance is complete. No implementation change to the legacy creator or
  console helper was necessary; the corrected procedure uses a guest-initiated
  reboot and preserves the failed hypervisor-reboot evidence.
- Final direct-host validation passed: 217 guide checks, focused Markdown lint for
  all three affected documents, new relative links, whitespace and `git diff --check`.
  `source-revision` and `source-sha256` in the private state directory identify the
  tested implementation and lab firewall. H05 passes; no commit or push was made.

## Handoff

This is the historical VM-creation handoff. Subsequent approved disk expansion
and application installation are tracked in the
[installation record](2026-09-18-hermes-local-installation.md); use that record
and the local lifecycle guide for current state.

H01-H05 pass after the documented recovery and retry.
The retained VM is running with pinned SSH and no smoke-test container or image left.
No Hermes application or provider credential was installed. Devbox is no longer
required by explicit user instruction; run checks directly.

The VM-ready milestone is complete. The next user task is manual Hermes deployment,
which was excluded from this baseline and has not started. Follow the
[local lifecycle guide](../HERMES_LOCAL_VM.md) for later use; VM and lab network
autostart stay disabled, and firewall rules must be reapplied after a workstation
reboot. No promotion certification or production readiness is claimed.
