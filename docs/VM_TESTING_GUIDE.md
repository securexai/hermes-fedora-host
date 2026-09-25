# VM-Based Testing Guide

**Current disposable Hermes DeepSeek lab:** follow
[HERMES_DISPOSABLE_LAB.md](HERMES_DISPOSABLE_LAB.md). The encrypted Server
certifier and retained TPM/LUKS fixtures below are separate historical or
production-candidate procedures; their results do not certify the new lab.

This repository uses disposable libvirt VMs for checks that containers cannot cover: real Fedora boot,
encrypted storage, Secure Boot, DNF5 reboot transactions, SSH persistence, and the Hermes rootless Podman
runtime. The Hermes production path is certified on Fedora Server 44 before the physical host is changed.

## Testing layers

| Layer | Tool | Scope |
| --- | --- | --- |
| Offline text | Bash and ShellSpec | Controller contracts, artifact consistency, and documentation |
| Mocked scripts | Bash with mocks | Deployment and failure-path logic |
| Container E2E | Podman | General workstation setup and SSH helper behavior |
| Hermes VM certification | libvirt/QEMU | Fedora Server install, DNF5 reboot, runtime, provider, purge, and destruction |

## VM identities

| VM | Name | MAC | IP | Purpose |
| --- | --- | --- | --- | --- |
| Fedora Cloud | `lab-fedora` | `52:54:00:ab:10:02` | `172.16.99.11` | General Fedora VM testing |
| Hermes Server | `lab-hermes-server` | `52:54:00:ab:10:03` | `172.16.99.12` | Disposable promotion certification |

The lab network is `lab-vlans` on `172.16.99.0/24`. The Hermes certifier uses the fixed Server identity and
destroys its VM and dedicated storage before printing a promotion record.

## Prerequisites

Set up libvirt and QEMU once:

```bash
sudo ./vm/setup-hypervisor.sh
./vm/setup-hypervisor.sh --check
```

The Hermes certification host needs KVM, at least 2 online CPUs, 9 GiB of available memory, and 60 GiB free in
`/var/lib/libvirt/images`. The certification VM itself receives 8 GiB RAM, 2 vCPUs, and a 40 GiB encrypted disk.

The operator supplies the Fedora Server DVD, its signed checksum, Fedora's public keyring, and the SSH identity.
The certifier never downloads installer media.

## Hermes Server certification

Run the complete certification from the repository root. Export the operator
inputs first. `HERMES_REPO` defaults to the current checkout location; set it
if your checkout is elsewhere. `HERMES_SSH_IDENTITY` must be the SSH private
key you have independently verified for the target.

```bash
HERMES_REPO=${HERMES_REPO:-$HOME/code/repos/hermes-fedora-host}
HERMES_MEDIA_DIR=${HERMES_MEDIA_DIR:-$HOME/Downloads/fedora-server-44-1.7}
HERMES_SSH_IDENTITY=${HERMES_SSH_IDENTITY:?export the verified SSH private key path}
cd "$HERMES_REPO"

./hermes-certify-vm.sh \
  --iso "$HERMES_MEDIA_DIR/Fedora-Server-dvd-x86_64-44-1.7.iso" \
  --checksum "$HERMES_MEDIA_DIR/Fedora-Server-44-1.7-x86_64-CHECKSUM" \
  --fedora-keyring "$HERMES_MEDIA_DIR/fedora.gpg" \
  --identity-file "$HERMES_SSH_IDENTITY" \
  --provider openai-codex \
  --model gpt-5.6-luna
```

The certifier runs its repository checks inside the dev-toolbox `infra` container
(`toolbox/run-offline-checks.sh` plus the check-only lint gate); it needs
`toolbox` and a local `dev-infra-hermes` container, and host hypervisor tooling
(`virsh`, `virt-install`, `qemu-img`, `xorriso`) on the host itself.

The certifier verifies the signed checksum and expected SHA-256, runs the repository's offline tests, installs
Fedora Server 44 with LUKS and Secure Boot, and invokes the controller in certification mode. After the automated
reboot and credential-free acceptance gates, it prints `AUTHENTICATION_READY provider=<id>` and waits without
starting provider authentication. `START-AUTH` is a readiness response consumed by that running certifier, not a
shell command; enter it in the same certification terminal. For `openai-codex`, the 15-minute device-login timer
starts only after that confirmation. The certifier then requires an exact
authenticated `HERMES_OK`, revokes all supported providers, purges fresh Hermes data, removes the temporary fixture
privilege, destroys the VM, verifies destruction, and prints `PROMOTION_RECORD=/absolute/path`.

One preattached console watcher remains active across every encrypted reboot. It starts disarmed and submits the
fixture passphrase only after Fedora emits an explicit reboot marker, starts
`systemd-cryptsetup@luks...` for the encrypted root, and displays the exact LUKS prompt in that order. The matcher
tolerates in-place terminal repaint bytes before `Starting` and systemd's `luks\x…<UUID-tail>` middle-ellipsis form
only when the retained tail begins with hexadecimal data. Generic path-units progress is ignored because Fedora emits
it both before the prompt and again after unlock. The cryptsetup start is the per-boot boundary, but only after a
fresh reboot marker; a same-boot cryptsetup redraw cannot arm the watcher. One marker and boundary authorize only one
submission, so same-boot and cross-boot associations fail closed.
Before OAuth, ordered evidence must contain one initial unlock and three reboot-marker, cryptsetup-boundary, and
prompt sequences. The certifier validates the evidence again before promotion.
Certification allows up to ten minutes for SSH to return. On failure, the run directory retains a
sanitized `unlock-monitor.log`, VM state, and console screenshot before cleanup; a failed run never produces a
promotion record.

Do not use the low-level creator as a production substitute. It is available for VM lifecycle troubleshooting:

```bash
./vm/create-hermes-server-vm.sh --iso "$HERMES_MEDIA_DIR/Fedora-Server-dvd-x86_64-44-1.7.iso" \
  --ssh-key "$HERMES_SSH_IDENTITY.pub"
./vm/create-hermes-server-vm.sh --destroy
```

For the retained workstation fixture used before manual Hermes deployment, follow
the [local VM lifecycle guide](HERMES_LOCAL_VM.md). Its lab firewall, SSH identity,
console unlock procedure and cleanup are separate from promotion certification.

## Retained DeepSeek manual-profile VM

The [fresh end-to-end record](plans/2026-09-23-hermes-deepseek-e2e-r1.md) covers
`lab-hermes-deepseek-e2e-r1`, separate from the disposable controller certifier
and the retained `lab-hermes-manual-r1` fixture. Use the guarded
[`deepseek-e2e-create-fixture.sh`](../scripts/hermes/manual/lab/deepseek-e2e-create-fixture.sh)
for the 2-vCPU, 12-GiB, 120-GiB UEFI Secure Boot/vTPM guest on `fvh-nat`.
Set `HERMES_MEDIA_DIR` to the verified Fedora media directory and run `--check`
before `--create`. A relative media path resolves from the repository root; the
libvirt storage pool supplies the absolute disk path. Repeating `--create`
verifies a matching VM and returns `UNCHANGED`. An orphaned disk or mismatched
domain is preserved for inspection. After interactive installation, the helper's
`--finalize` inspects the running and saved CD-ROM definitions separately and
ejects the verified installer ISO from either state. A second run returns
`UNCHANGED`; it never removes the retained guest. If live ejection fails, shut
the guest down gracefully and rerun `--finalize` before starting it from disk.
The new VM's LUKS passphrase, administrative password and dedicated provider
credentials are entered through private prompts. A guest cold-start proof is
limited to the VM and is not the physical power-loss test in this guide.

## Production promotion

After the certification record exists, verify the new production SSH ED25519 fingerprint at the local console.
Then run `adopt-host`, type `ADOPT-HERMES-HOST`, run the read-only `check`, and deploy with the exact record:

```bash
./hermes-deploy.sh adopt-host \
  --target aicowork@10.0.30.10 \
  --identity-file "$HERMES_SSH_IDENTITY" \
  --management-cidr 192.168.99.0/24 \
  --interface eno1

./hermes-deploy.sh check \
  --target aicowork@10.0.30.10 \
  --identity-file "$HERMES_SSH_IDENTITY" \
  --management-cidr 192.168.99.0/24 \
  --interface eno1

./hermes-deploy.sh deploy \
  --target aicowork@10.0.30.10 \
  --identity-file "$HERMES_SSH_IDENTITY" \
  --management-cidr 192.168.99.0/24 \
  --interface eno1 \
  --provider openai-codex \
  --model gpt-5.6-luna \
  --promotion-record /absolute/path/from/PROMOTION_RECORD
```

Production package mutation and planned reboots require typing `CONFIRM-HERMES-PRODUCTION`. Provider credentials
and the final `HERMES_OK` are entered and accepted again on production; VM certification does not transfer secrets.

## Fedora Cloud VM

The general Fedora Cloud fixture is retained for reference only. It exercises the
workstation `setup.sh` helper, which stays in the source repository and is **not**
part of this tree. The Cloud Base image is a **separate** download from the Server
DVD set; do not place it inside the Server-ISO directory.

```bash
cloud_dir=${HERMES_CLOUD_DIR:-$HOME/Downloads/fedora-cloud}
./vm/create-fedora-vm.sh --image "$cloud_dir/Fedora-Cloud-Base-44.qcow2"
./vm/create-fedora-vm.sh --destroy
```

`tests/test-sshd-vm.sh` is part of the same workstation stack and was **not**
migrated here. Run it from the source repository; it accepts `--fedora` for the
Cloud fixture and `--server` for a running `lab-hermes-server`.

## Cleanup and evidence

List VM state with `virsh -c qemu:///system list --all`. Do not manually reuse a successful certification VM or
promotion record. Certification run artifacts are stored below the XDG state directory with mode `0700`; the
promotion record contains no credentials and is valid for the initial 24-hour use window.

Set `run_dir` to the exact path printed by a failed certifier or the exact successful run directory, then inspect only
the secret-free artifacts:

```bash
run_dir=${HERMES_CERT_RUN_DIR:-$HOME/.local/state/hermes-certification/run-YYYYMMDDTHHMMSSZ}

rg -n \
  'monitor-ready|luks-(reboot-observed|boot-boundary-observed|prompt-verified)' \
  "$run_dir/unlock-monitor.log"
find \
  "$run_dir/controller-state/hermes-deploy/lab_172.16.99.12" \
  -maxdepth 1 -type f -name 'stage-*' -printf '%f\n'
virsh -c qemu:///system dominfo lab-hermes-server
stat \
  /var/lib/libvirt/images/lab-hermes-server.qcow2 \
  /var/lib/libvirt/images/lab-hermes-server-oemdrv.iso
```

After cleanup, `dominfo` and `stat` must fail because the exact domain and both storage files are absent. A successful
run must additionally contain `status.log`, `guest-facts`, `vm-destroy.log`, and the printed secret-free promotion
record. Do not redirect the provider-authentication terminal to a file.

See [the Hermes deployment plan](HERMES_DEPLOYMENT_PLAN.md), [the one-command
handoff](HERMES_ONE_COMMAND_DEPLOYMENT_HANDOFF.md),
and [the Fedora Server installation guide](../hermes-fedora-server-install-guide.html) for the complete contract.

## Unattended TPM staging

The TPM profile uses only `/var/lib/libvirt/images/hermes-tpm-lab/`, a dedicated directory owned by
its lab operator with mode 0711 and the libvirt image SELinux context. This avoids granting the operator
write access to the general image pool. Remove this profile with `--tpm-stage --destroy` only after
retaining required recovery evidence. The fixed domain must be absent before creation. TPM creation uses UUID
`4db6369a-2b8b-427f-a47a-a5d83bb40cff`, matching the isolated certifier and power helper.

The legacy VM profile remains unchanged. The new `vm/create-hermes-server-vm.sh --tpm-stage`
profile requires all of `--tpm-public-key`, `--firmware-code`, `--firmware-vars`, `--installer-uki`
and `--boot-certificate`, with absolute paths to regular files. It also requires
`--recovery-key-file`: a caller-owned mode-0600 file containing 64 random lowercase hexadecimal
characters (an optional trailing newline is accepted). Generate it privately for this fixture;
never use a production password or the published legacy fixture passphrase. Follow the existing verified Fedora
ISO prerequisites before using this profile. These are disposable lab inputs, never production keys.

The September 10 standard TPM2 candidate now carries the shared profile renderer on its installer media and
applies it to the offline target before dracut. It masks the two NvPCR definitions and product measurement while
retaining SRK setup and PCR11 phases. Lifecycle signing rejects baseline/updated initrds missing the three masks
or required TPM/PCR11 module metadata. See the
[fresh campaign scope and remaining boot gates](HERMES_TPM_DEPENDENCY_REVIEW.md#fresh-lab-campaign-prepared-on-september-10).
Local archive checks are not a new VM boot pass; earlier fixture evidence retains its original source identity.

Build the installer UKI with `scripts/hermes/unattended/boot_build.py --purpose installer`. Its embedded
command line must include `inst.stage2=hd:LABEL=Fedora-S-dvd-x86_64-44` and
`inst.ks=hd:LABEL=OEMDRV:/ks.cfg`. Use a separate PCR RSA key and Secure Boot key. Create the matching
OVMF variables with `firmware.py`; use the corresponding raw 4 MiB OVMF code/template pair.
Convert the supplied `OVMF_CODE_4M.secboot.qcow2` and `OVMF_VARS_4M.qcow2` to raw copies first.
The observed 2 MiB pair booted without PCR11 measurements and is not an accepted fixture.
The installer now rejects zero/uninitialized SHA-256 PCR7 or PCR11 before storage setup and again
before enrollment; TPM device presence and Secure Boot alone are insufficient. The creator
uses `efi_media.py` to verify and package the installer, public PCR key and Kickstart into EFI media.

This profile boots through Secure Boot firmware with an emulated TPM2, rather than direct kernel boot.
The installer obtains `tpm2-tools` from the signed Fedora 44 release repository because the Server
DVD omits it; network access is required and the package operation has a five-minute timeout.
The installer enrolls SHA-256 PCR7 plus signed PCR11 with the current installer signature safety check. The
private disposable recovery passphrase remains a recovery slot; it is not submitted to a boot console.
Installed UKIs sign the normal PCR11 states through `enter-initrd`, `leave-initrd`, `sysinit` and
`ready`. The post-initrd signatures support systemd TPM anchor services as well as initial disk unlock.
Private signing keys stay on the workstation. The generated installer media contains the private
fixture recovery value; retain it as protected recovery material and remove it during fixture cleanup.
Existing dedicated disk or installer files cause creation to stop before overwriting them. The installer and
installed UKI must use the same
Secure Boot certificate; a different authority can change PCR7 and prevent automatic unlocking.

Staging stops powered off after detaching installer media. The TPM Kickstart writes a public stage
marker and the enrolled PCR public key to the ESP. Earlier staged disks without these files cannot use
the new handoff. `scripts/hermes/unattended/lab_boot.py` injects an already-built installed UKI and can
start the fixed disposable VM without console input. It requires `guestfish`, `qemu-img`, `virsh`,
`ukify`, `sbverify`, and a working libguestfs appliance. Run it inside the
dev-toolbox `infra` container (see [ENVIRONMENT.md](ENVIRONMENT.md)).

Supply an installed UKI built from this guest's kernel and regenerated TPM-capable initrd. Its embedded
command line must name `root=/dev/mapper/vg_root-root`, the actual `rd.luks.uuid=...`, and
`rd.luks.options=tpm2-device=auto`. The staged ESP also exports the kernel, regenerated initrd, OS release
and fixed root command line;
an installer UKI or synthetic test initrd cannot substitute for these guest artifacts.

Use the UUID recorded when creating this fixture, the same Secure Boot certificate and PCR public key
used for enrollment, and a private existing state directory. For optional `--start`, provide the lab SSH
identity and a known-hosts file verified independently for this fixture; never use unauthenticated
key discovery as enrollment. A never-booted installation may not yet contain SSH host keys. In that
case, provision a dedicated guest host key offline through the recovery-unlocked disk, apply root
ownership, mode 0600 and the guest SELinux context, then independently read back its public key.
Retain the private guest key only with the protected disposable recovery material.
Example with operator-supplied paths:

```bash
python3 scripts/hermes/unattended/lab_boot.py \
  --domain-uuid "$lab_uuid" --uki "$installed_uki" \
  --certificate "$boot_certificate" --pcr-public-key "$pcr_public_key" \
  --state-dir "$lab_state_dir" --start \
  --identity-file "$lab_identity" --known-hosts "$lab_known_hosts" --timeout 300
```

The domain must be shut off with autostart disabled, no managed save, detached install media, emulated
TPM2 and Secure Boot firmware. The disk must be the dedicated, standalone lab QCOW2, with no snapshots.
Keep exclusive operator control of this fixture throughout the handoff; do not start or edit it from
another terminal or manager while disk access is in progress. The helper serializes its own invocations,
and rechecks shutdown before writes. Its lock does not serialize other VM management tools.

Both Fedora's `EFI/fedora/shimx64.efi` boot path and the fallback `EFI/BOOT/BOOTX64.EFI` receive the UKI.
The helper preserves each original as a sibling ending in `.hermes-original`, uploads to a temporary
sibling, checks the bytes, and then renames it into place. A matching rerun avoids replacement and never
overwrites saved originals. A mismatched saved backup blocks replacement; this helper does not upgrade
an already-injected different release. These preserved distribution files are recovery material, not proof of a
previous UKI signed by the enrolled lab authority. An interrupted handoff stays uncertified; with the VM
shut off, rerun the same inputs to finish, or restore the saved EFI files through offline recovery.
Original distribution boot files may require restoring the corresponding firmware trust as well.

`lab-boot.json` records completed injection before any start and is updated on successful observation.
A failed first boot leaves the injection record and the guest available for explicit recovery; the
helper does not force-stop it, automatically retry its boot, or submit a recovery passphrase.
First-boot observation requires pinned SSH, the exact embedded command line, and Secure Boot enabled.
It is deliberately marked `boot_verified: false`: TPM token/PCR validation, cold/update boots, tamper,
recovery and full runtime certification remain pending. Offline fixtures do not advance `UA-02`.

The disk API and domain operations follow the [guestfish reference](https://libguestfs.org/guestfish.1.html)
and [virsh reference](https://www.libvirt.org/manpages/virsh.html).

### Build the staged guest candidate

`lab_candidate.py` connects that public export to `boot_build.py`, `prepare.py` and the injection helper.
Use a fresh candidate destination and the same enrolled lab keys. Supply a trusted workstation EFI stub,
prepared RPM transaction, target identity JSON, baseline digest and release/model identifiers:

```bash
python3 scripts/hermes/unattended/lab_candidate.py \
  --domain-uuid "$lab_uuid" --stub "$efi_stub" \
  --secureboot-key "$boot_key" --certificate "$boot_certificate" \
  --pcr-key "$pcr_key" --pcr-public-key "$pcr_public_key" \
  --repository "$repository" --destination "$candidate_dir" --transaction "$transaction_dir" \
  --host-identity "$host_identity" --release-id "$release_id" --model "$model" \
  --baseline "$baseline_sha256" --state-dir "$lab_state_dir"
```

Optional `--start`, pinned SSH options and timeout match `lab_boot.py`. The same disk lock spans extraction,
build, candidate freeze and injection. Export sizes are checked before download and again after copying. Hashes
check consistency, not authenticity; use only the
controlled staged fixture. The candidate contains the exact injected UKI. `lab-candidate.json` retains
its fingerprint and build hashes, always with `boot_verified: false`. It is not a signer gate file.
A failed construction can leave a partial candidate: preserve it for diagnosis and choose a fresh
candidate destination for retry. After injection, use the existing same-UKI recovery procedure above.
No provider operations, scan gate, RPM replay, recovery certification or promotion signing occur here.

### Enroll the disposable boot manager

The direct-UKI staging fixture does not yet satisfy the unattended host's systemd-boot prerequisite.
`scripts/hermes/unattended/lab_enroll_boot.py` is a guest-side enrollment helper for that fixture only.
Stage root-owned public `boot-manager.efi`, `previous.efi` and `uki.crt` files in a private root-owned
directory. Sign the guest's systemd-boot binary on the workstation with the existing lab authority;
keep its private key on the workstation. The guest needs `sbsigntools` and `systemd-boot-unsigned`.

The helper checks the expected DMI UUID, staging marker, Secure Boot, both signatures and the exact
working direct UKI before enrollment. It retains that UKI as `EFI/Linux/hermes-enrollment.efi` and
preserves `EFI/fedora/shimx64.efi`. It installs the signed manager and selects the initial entry through
`loader.conf`: `bootctl set-default` cannot run until the machine has booted through a supported manager.
Conflicting files or changed inputs on a retry stop enrollment. Root-owned journal state remains
`installed-awaiting-boot`; this helper never writes a passing boot or certification gate.

Verify a new boot ID, the running systemd-boot interface, Secure Boot, TPM unlock and runtime health
after a powered-off boot. Retain offline recovery material until the full ordered certification and
cleanup gates pass. This repaired fixture still cannot substitute for clean candidate certification.
The [systemd bootctl reference](https://github.com/systemd/systemd/blob/main/man/bootctl.xml)
documents installation of `.efi.signed` boot-manager files.

### Freeze the package transaction

Use DNF5 `upgrade --store=PATH` on the preparation fixture to resolve and download the transaction
without applying it. Record `installed-before.txt` using the same sorted RPM inventory format as
`gates.package_baseline`. The manifest baseline must equal the SHA-256 of those exact bytes.
`transaction.expected_inventory` validates stored transaction version 1.0, its package operations and
local RPM paths, and calculates the expected resulting inventory. Save that inventory's SHA-256 in
`installed-after.sha256`. Unsupported operations or schemas block preparation.

`prepare.py` now checks this bundle before freezing a candidate. Before staging offline replay,
`gates.verify_packages` checks the live baseline, the complete local RPM set, every signature, and
each RPM's queried identity against its stored operation. It never resolves missing RPMs from a live
repository. `installed-after.sha256` remains a prediction until compared with the actual post-update
inventory; preparation is not passing replay evidence. Preserve a recoverable preparation baseline
before applying the transaction and extracting the resulting kernel/initrd for the candidate UKI.
See the [DNF5 store option](https://dnf5.readthedocs.io/en/latest/commands/upgrade.8.html#options)
and [strict replay contract](https://dnf5.readthedocs.io/en/latest/commands/replay.8.html).

DNF5 5.4.1.0 does not support `replay --offline`. The unattended implementation uses the standard
systemd offline-update target to execute strict `dnf5 --disable-repo=* --assumeyes replay PATH`.
`offline.py` validates its generated service, installs its target dependency, and creates
`/system-update` only after package verification. The service runs in a private network namespace,
clears its own marker before replay, rechecks signatures and records the actual inventory result.
It exits successfully without changes when another updater owns the marker.

Successful replay removes the generated service/dependency and reboots. Failed or interrupted
execution leaves its durable state under `/var/lib/hermes-unattended/offline/` for explicit recovery;
it must never be retried automatically. The early marker removal prevents an update reboot loop.
The host requires recorded replay completion and a subsequent normal boot before runtime installation.
Retain the preparation disk and Restic recovery snapshots on failure; do not clear an interrupted
journal to force a retry. The [systemd offline-update specification](https://github.com/systemd/systemd/blob/main/man/systemd.offline-updates.xml)
defines the target ordering and marker-ownership rules used here.

### Automatic fresh-fixture lifecycle

The U06 [lifecycle procedure](HERMES_UNATTENDED_DEPLOYMENT.md#automatic-fixture-lifecycle) is authoritative
for the new root-enrolled provision/enroll/certify/cleanup service. It creates a fresh TPM installation and
keys each run and retains exact run-bound journals; it does not reuse the destroyed S4 fixture.
The implementation has offline coverage and passed the bounded F4 lab campaign: two fresh successes,
idempotency, credential-bearing interruption/recovery, revocation and teardown. See the
[execution record](plans/2026-09-07-hermes-unattended.md#f4-final-closure) for source/tool applicability
and limitations. Temporary controls were removed; recurring timers remain disabled and require separate
authorization. Do not mix manual VM operations or the older candidate-only timer with an active lifecycle run.

## Remaining standard TPM2 lab tests

The disposable Fedora Server Kickstart reserves a 2048-MiB EFI partition for retained recovery images
and bounded boot-artifact probes. The earlier 600-MiB fixture filled during r6 B4-linux trial preparation;
its failed evidence is retained in the canonical execution record. Existing fixtures are not resized.

Use the [B3/B4/B7 operator package](HERMES_REMAINING_LAB_TESTS.md) for the remaining acceptance matrix.
It starts with a previous-approved-image cold boot after a completed update, then separate trust-rejection
and interrupted-update cases. Each proposed case has a fresh run ID and a four-hour total bound including
cleanup. Local preparation does not authorize VM allocation, provider use, notifications or privilege changes.
B3 subsequently passed its separately approved block, including independent cleanup at 2026-09-11T18:00:17Z
within four hours; see [B3 evidence](plans/evidence/2026-09-11-hermes-b3-live.json). B3 and r3 are consumed.
The user subsequently authorized all pending blocks. `b4-linux` failed during prerequisite certification;
independent cleanup passed at 22:14:22Z within four hours. Later blocks remain blocked and unissued.
The user subsequently authorized fresh bounded replacement runs without further lab approval prompts.
Corrected r5 dispatched once at 22:58:24Z, passed seven gates, then failed initial provider revocation.
The cleanup retry confirmed revocation; independent restoration passed on September 12 at 00:04:12Z,
within four hours. No tamper probe ran. A bounded revocation correction and fresh replacement are in preparation.
That correction passed offline checks; r6 passed L0 and dispatched once on September 12 at 00:12:21Z.
Its mandatory cleanup deadline is 04:11:43Z. The continuation evidence records its exact run and source identities.
Preserve the hypervisor exception and exact grant/control cleanup before any dependent case.
Production deployment remains the approval boundary.
