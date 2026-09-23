# Hermes Bare-Metal Deployment Handoff

> [!IMPORTANT]
> The task is paused at the offline disk-image gate. The physical host has not received any Hermes
> deployment changes. Resume only after the operator confirms that the encrypted Clonezilla image
> was created and its integrity check passed.

## Contents

- [Mission](#mission)
- [Current checkpoint](#current-checkpoint)
- [Authoritative environment](#authoritative-environment)
- [Verified physical-host baseline](#verified-physical-host-baseline)
- [Repository and execution guardrails](#repository-and-execution-guardrails)
- [Completed validation](#completed-validation)
- [Resume gate: offline clean-state image](#resume-gate-offline-clean-state-image)
- [Post-image deployment sequence](#post-image-deployment-sequence)
- [Physical-host acceptance checklist](#physical-host-acceptance-checklist)
- [Rollback and clean retest](#rollback-and-clean-retest)
- [Immediate next action](#immediate-next-action)

## Mission

Deploy the hardened Hermes Agent baseline on the clean Fedora Kinoite 44 host at
`aicowork@10.0.30.10`, validate it on the physical network, and prove reboot persistence. Preserve
an exact pre-Hermes disk image so the server can return to its clean state for recovery or a fresh
retest.

The host is a fresh-install target. Use the phases in
[`hermes-kinoite-install-guide.html`](../hermes-kinoite-install-guide.html). The existing
[`hermes-remediation-wizard.sh`](../hermes-remediation-wizard.sh) remediates an existing deployment;
it assumes a `hermes` account, data directory, image, and backup. Do not run it on this clean host.

## Current checkpoint

- Date: 2026-08-27, America/Bogota.
- Static guide/wizard/E2E consistency: 173 passed, 0 failed, 0 skipped.
- Disposable Kinoite VM E2E with Trivy: 93 passed, 0 failed, 0 skipped.
- VM reboot persistence passed, and the successful test VM was removed automatically.
- E2E artifacts:
  `$HOME/.local/state/hermes-e2e-vm/run-20260827T040748Z`.
- The physical host remained unchanged during testing and was reachable by strict key-only SSH at
  the end of the baseline audit.
- The next action requires the operator at the physical console: create and verify the encrypted
  Clonezilla image.

## Authoritative environment

| Item | Value |
|---|---|
| Repository | `/var/home/cloudops/code/repos/mikrotik` |
| Target | `aicowork@10.0.30.10` |
| Verified hostname | `ai` |
| SSH private key | `/var/home/cloudops/.ssh/id_ed25519_cloudops` |
| Known-hosts file | `/var/home/cloudops/.ssh/known_hosts` |
| Admin user | `aicowork` |
| Management source | `192.168.99.0/24`; workstation observed as `192.168.99.188` |
| Target interface | `eno1` |
| Target VLAN/IP | VLAN 30, `10.0.30.10/24`, gateway `10.0.30.254` |
| Kinoite ISO | `$HOME/Downloads/Fedora-Kinoite-ostree-x86_64-44-1.7.iso` |
| ISO SHA-256 | `4a944312b4e861ab625fd9786957174ef122a8a406bbb54caba7665e0d9f0e92` |
| Hermes image tag | `v2026.8.19` |
| Hermes image digest | `sha256:3811ed13da874fba2ac99b6d492db9a203d34cb6dccf90d886948c00d0ccec09` |

Use `10.0.30.10` until local DNS is independently verified. Do not depend on
`hermes.ai.lab.local`.

## Verified physical-host baseline

| Check | Observed result |
|---|---|
| Platform | AZW SER3, x86-64 |
| Operating system | Fedora Linux 44.1.7 Kinoite |
| OSTree commit | `13e5eb8feb19a2cd200d10ecd06c5d04f77c6e5324e74f8d57940e67b6189b3d` |
| OSTree signature | Valid Fedora signature |
| Kernel | `6.19.10-300.fc44.x86_64` |
| Secure Boot | Enabled |
| SELinux | Enforcing |
| Firewalld and sshd | Active |
| Cgroups | v2 |
| Podman | `5.8.1-1.fc44.x86_64`; upgrade required |
| Memory | 13 GiB total |
| Persistent storage | 475 GiB LUKS-encrypted Btrfs; 465 GiB available |
| Internal disk | `/dev/nvme0n1`, model `512GB SSD`, 476.9 GiB |
| Time | America/Bogota; NTP synchronized |
| Hermes identity | Absent |
| Hermes data, images, containers, service | Absent |

An external 476.9 GiB `/dev/sda` appeared during one audit and was absent during the final audit.
Treat external device names as transient. Identify every source and destination by model, transport,
capacity, and role at the physical console before imaging or restoring.

## Repository and execution guardrails

- Read the root `AGENTS.md` before resuming.
- Run repository tools through `devbox run --`. Run the libvirt Hermes VM E2E directly because the
  repository explicitly exempts that hypervisor-driving script from Devbox.
- Preserve all existing working-tree changes. At handoff creation, these were:
  - modified `enable-sshd.sh`;
  - modified `tests/Containerfile.sshd`;
  - modified `tests/test-sshd-e2e.sh`;
  - modified `tests/test-sshd-unit.sh`;
  - untracked `docs/HERMES_INSTALLATION_VERIFICATION.md`.
- The untracked verification document contains a separate 2026-08-26 run with different totals.
  Do not overwrite it or silently combine its claims with the 2026-08-27 evidence in this handoff.
- Do not commit, push, or modify a pull request unless the user explicitly requests it.
- Keep provider credentials out of commands, logs, screenshots, Git, and agent-visible messages.
  The human operator enters credentials directly into the interactive TTY.
- Use only a dedicated low-value provider credential with a spending cap and alerts.
- Keep the physical console and two independent SSH sessions available while changing sshd or
  firewalld.

## Completed validation

The following commands and outcomes have already completed for the current tree:

```bash
devbox run -- ./tests/test-hermes-guide.sh
# 173 passed, 0 failed, 0 skipped

./tests/test-hermes-e2e-vm.sh \
  --iso /var/home/cloudops/Downloads/Fedora-Kinoite-ostree-x86_64-44-1.7.iso \
  --with-trivy -v
# 93 passed, 0 failed, 0 skipped
```

The VM run proved the Fedora upgrade to Podman 5.8.4, host policy, dedicated identity, digest
mapping, image pull, smoke test, TTY onboarding seam, fail-closed patch, root-owned Quadlet,
production acceptance, and reboot persistence.

The Trivy report produced these raw per-target totals:

- Debian target: 387 findings (368 HIGH, 19 CRITICAL).
- Node.js target: 10 findings (9 HIGH, 1 CRITICAL).
- Two Rust targets: 2 HIGH findings each.

These are scanner rows, not deduplicated vulnerabilities or a security approval. Review
`06-trivy.log` in the E2E state directory before assigning any valuable credential.

## Resume gate: offline clean-state image

The operator must complete these steps before any physical-host mutation:

1. Shut down Fedora normally from the console.
2. Boot a checksum-verified Clonezilla Live USB.
3. Attach a separate external image repository with sufficient free space.
4. Select `device-image`, then `local_dev`, then `savedisk`.
5. Identify the source as the internal NVMe disk by all of these properties:
   - device: `nvme0n1` in the audited Fedora boot;
   - model: `512GB SSD`;
   - transport: NVMe;
   - capacity: 476.9 GiB.
6. Select the external USB disk or partition as the image repository. Confirm that it is not the
   internal NVMe source.
7. Name the image `aicowork-kinoite44-pre-hermes-20260827`.
8. Encrypt the Clonezilla image with a dedicated recovery passphrase stored in the operator's
   password manager. Do not reuse the LUKS or provider password.
9. Enable Clonezilla's saved-image integrity check and require it to pass.
10. Power off, disconnect imaging media as appropriate, and boot Fedora normally.
11. Confirm the image name and successful integrity check in the conversation.

Completion criterion: the operator supplies the image name, states that Clonezilla's integrity
check passed, and strict SSH works again after the normal Fedora boot.

## Post-image deployment sequence

### 1. Re-establish the safety envelope

1. Verify the known host key and strict public-key access to `aicowork@10.0.30.10`.
2. Open a second independent key-only SSH session and keep both sessions open.
3. Verify Secure Boot, LUKS, SELinux, firewalld, cgroup v2, time synchronization, resources,
   listeners, and the booted OSTree deployment.
4. Verify that the `hermes` user, data directory, images, containers, and service are still absent.
5. Stop on any mismatch and diagnose it before applying the guide.

Use strict SSH options equivalent to:

```bash
devbox run -- ssh \
  -i /var/home/cloudops/.ssh/id_ed25519_cloudops \
  -o IdentitiesOnly=yes \
  -o PreferredAuthentications=publickey \
  -o PasswordAuthentication=no \
  -o KbdInteractiveAuthentication=no \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=/var/home/cloudops/.ssh/known_hosts \
  aicowork@10.0.30.10
```

### 2. Execute the fresh-install guide

Follow the guide phases in order and use its exact commands and canonical artifacts:

1. **Host foundation:** stage the current Fedora update, reboot, and require Podman 5.8.4 or
   newer. Below 5.8.6, use direct root-owned Quadlet placement and avoid the affected replacement
   command.
2. **Host policy:** apply the reviewed sshd and firewalld settings with `ADMIN_USER=aicowork`,
   `MGMT_SUBNET=192.168.99.0/24`, and `IFACE=eno1`. Mask sleep targets, disable unused discovery
   and printing services, disable LLMNR/mDNS, and enable staged OSTree updates.
3. **Dedicated identity:** create the locked `hermes` account with a private home, subordinate ID
   maps, linger, no SSH keys, and no privileged group membership.
4. **Supply chain:** verify the named tag maps to the pinned digest, pull as `hermes`, inspect the
   local digest, run Trivy, and complete the smoke test.
5. **Persistence:** create and validate `/home/hermes/data` with the guide's ownership and SELinux
   model.
6. **Human onboarding:** let the operator complete the real TTY setup with the dedicated low-value
   credential. Keep the credential out of captured output.
7. **Fail-closed policy:** apply the guide's canonical hardening patch and read the effective
   values back as container uid 10000.
8. **Quadlet cutover:** install the digest-pinned root-owned Quadlet and both root-owned drop-ins,
   then start `hermes.service`.
9. **Production acceptance:** run the guide's user and root acceptance programs without weakening
   any assertion.
10. **Reboot proof:** write a harmless persistence marker, reboot, and rerun the post-boot checks.

Completion criterion: every acceptance item below passes after reboot and strict SSH remains
available from the management workstation.

## Physical-host acceptance checklist

- Secure Boot enabled, SELinux enforcing, LUKS active, firewalld active, and cgroup v2 active.
- Podman 5.8.4 or newer; direct Quadlet placement retained while Podman is below 5.8.6.
- Key-only SSH works from `192.168.99.0/24`; password, keyboard-interactive, and root login are
  denied.
- SSH forwarding, X11 forwarding, tunnels, and gateway ports are denied.
- The firewalld zone has the management-subnet rich rule and no unrestricted `ssh`, `mdns`, or
  `kdeconnect` service.
- Only sshd listens off-loopback on the host.
- The `hermes` account is locked, private, unprivileged, and has no authorized keys.
- `hermes.service` is active and healthy from the root-owned Quadlet.
- The container runs the pinned digest with command `gateway run`.
- The container has a read-only root, `NoNewPrivileges`, no published ports, no engine socket, and
  only loopback listeners.
- Effective capabilities are exactly CHOWN, DAC_OVERRIDE, FOWNER, SETGID, and SETUID;
  `CapEff=00000000000000cb`.
- The only persistent mount is `/home/hermes/data` to `/opt/data` with the shared SELinux label.
- Limits are 4 GiB memory, 200% CPU, 512 systemd tasks, and 512 container PIDs; logs use journald.
- Manual approvals and all documented fail-closed values match the guide.
- After reboot, the gateway is healthy, the marker persists, and the boot-time relabel action exits
  successfully.

## Rollback and clean retest

Use a service-level rollback only for an image update: restore the previous image digest and the
encrypted Hermes data backup if a migration changed data.

Use Clonezilla for a complete clean-state reset. `rpm-ostree rollback` is insufficient because
`/var` and `/var/home` persist across OSTree deployment changes.

For a full reset:

1. Encrypt and export any Hermes data that must survive the reset.
2. Obtain explicit user confirmation immediately before overwriting the internal disk.
3. Boot Clonezilla and select `device-image`, `local_dev`, and `restoredisk`.
4. Select `aicowork-kinoite44-pre-hermes-20260827` as the source image.
5. Identify the destination as the internal 476.9 GiB NVMe by model, transport, and capacity.
6. Enable the image integrity check and use the partition table stored in the image.
7. Confirm the destructive destination twice, restore, power off, and remove the external media.
8. Boot Fedora and verify the clean baseline: strict SSH, Secure Boot, the recorded OSTree commit,
   Podman 5.8.1, and no Hermes identity, data, image, container, or service.
9. Repeat the post-image deployment sequence for a fresh retest.

## Immediate next action

Wait for the operator to complete the Clonezilla `savedisk` operation and report:

- the exact image name;
- that encryption was enabled;
- that Clonezilla's image-integrity check passed;
- that Fedora booted normally afterward;
- that strict key-only SSH to `aicowork@10.0.30.10` works again.

Only then begin the physical-host deployment sequence.
