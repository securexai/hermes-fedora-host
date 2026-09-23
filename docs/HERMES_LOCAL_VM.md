# Retained local Hermes VM

This disposable Fedora Server 44 fixture contains the manual Hermes gateway and
offline worker. A locally supplied disposable provider key passed authenticated
acceptance; no production secrets were installed. The LUKS passphrase is the
published test fixture value; do not store sensitive data here.
The [VM creation record](plans/2026-09-18-hermes-local-vm.md) preserves the original
40 GiB baseline. Current installation evidence and remaining gates belong in the
[installation record](plans/2026-09-18-hermes-local-installation.md).

## Identity and access

- Domain: `lab-hermes-server`; guest user: `lab`; IP: `172.16.99.12`.
- Network: `lab-vlans`; bridge: `virbr-lab`; MAC: `52:54:00:ab:10:03`.
- Resources: 2 vCPUs, 8 GiB RAM, 80 GiB disk; Secure Boot and LUKS system storage.
- EFI and `/boot` are unencrypted. VM and lab network autostart stay disabled.
- Private workstation state: `/var/home/aicloudopspecial/.local/state/hermes-local-vm`.
- Guest disk: `/var/lib/libvirt/images/lab-hermes-server.qcow2`.
- Verified installer copy: `/var/lib/libvirt/images/hermes-local-media/`.

Run workstation commands from this repository, using installed host tools directly.
Set `state` as shown below in each workstation terminal before using later commands.
The dedicated identity and pinned host key are required for SSH:

```bash
state=/var/home/aicloudopspecial/.local/state/hermes-local-vm
ssh -i "$state/id_ed25519" -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$state/known_hosts" \
  lab@172.16.99.12
```

The disposable `lab` account can run `sudo -n /usr/bin/bash`. This is fixture
administration, not the production host's access policy. Never replace a mismatched
SSH pin merely to make a connection succeed; verify the exact guest identity first.
The initial pin used the repository's trust-on-first-use procedure on this isolated
fixture; it was not independently enrolled through a console or guest agent.

The image's `mcelog.service` reports an unsupported AMD CPU and remains failed.
The requested OS security, container and boot checks passed; the execution record
retains this service limitation.

## Installed application and remaining gates

The pinned manual-profile gateway and offline worker are installed and running.
Their rootless Quadlets live under `/etc/containers/systemd/users/1002/`.
Both containers have read-only roots, no-new-privileges, 2 GiB individual memory
limits and no published ports. The parent slice has 4 GiB high / 5 GiB maximum
limits. The worker has no network connectivity; the gateway reaches it through
pinned SSH over a shared Unix socket. Positive transport, SCP, negative host-key
checks and the actual Hermes terminal backend probe passed.

`/home/hermes` is a dedicated 32 GiB XFS LV inside the original LUKS container.
The original root and swap remain unchanged, and 8 GiB remains free in `vg_root`.
The mount is recorded in fstab; the runtime user manager asserts that it is mounted.

- Runtime account: `hermes`, UID 1002, locked password, nologin, no sudo, lingering enabled.
- Administrator account: `aicowork`, UID 1001, wheel, same dedicated fixture SSH key.
  Its password is locked; privileged fixture work still uses the existing `lab`
  account. Set a fresh password locally before using password-based sudo as `aicowork`.
- Bundle: `/home/aicowork/hermes-m02-bundle`.
- Provider/model: `openai-api` / `gpt-5.6-luna`, verified from runtime configuration.
  The replacement disposable key passed exact `HERMES_OK` inference and the agent
  worker-tool round trip. Telegram is configured as described below. Provider acceptance
  followed the reboot test; a second full reboot after key entry was not performed.
- **Post-installation reboot persistence passed on 2026-09-18.** After desktop
  authorization succeeded, the console watcher unlocked the rebooted guest, pinned
  SSH returned with a new boot ID, the data mount and both services returned
  automatically, and the real worker-backend probe passed. Future reboots still
  use TPM unlocking; the watcher is retained for recovery.
- Memory approval and fresh-session recall passed the follow-up tests. Use the
  [memory review procedure](HERMES_MEMORY_APPROVAL.md); queued writes require explicit
  approval. Upstream dependency/configuration warnings remain; this is not full
  production certification. See the [manual guide](HERMES_MANUAL_DEPLOYMENT_GUIDE.md).

After SSH login as `lab`, inspect services using the runtime identity:

```bash
sudo -n /usr/bin/bash -c '
  uid=$(id -u hermes)
  sudo -u hermes env --chdir=/home/hermes HOME=/home/hermes \
    XDG_RUNTIME_DIR=/run/user/$uid \
    systemctl --user status hermes-worker.service hermes-gateway.service --no-pager
'
```

## Telegram access

Telegram was configured on 2026-09-18 using the bundle's `provision-telegram.sh`
hidden-input helper. Open the bot from the authorized Telegram account and send
`/start`, then a message. The setup allows one numeric user ID and sets
`TELEGRAM_ALLOW_ALL_USERS=false`; the credential file has mode `0600`.
The gateway connected successfully after its service restart, Telegram `getMe`
accepted the token, and both containers remained running with no published ports.
The operator confirmed the exact `HERMES_TELEGRAM_OK` reply from the authorized
account on 2026-09-18, completing the end-to-end message test. A temporary allowlist
exclusion produced no reply after 30 seconds according to the operator; the gateway
logged unauthorized activity. The original allowlist was restored and the gateway
reconnected. The operator confirmed a reply after restoration, completing the
access-restriction test. User-provided screenshots also confirm Telegram memory
staging, exact-ID approval and recall after `/new`. A subsequent console-assisted
VM reboot passed: both services started automatically, Telegram reconnected,
the allowlist was preserved, and approved-memory content was unchanged. The
operator confirmed correct recall in a fresh Telegram session after reboot. Other approval flows
remain untested.

For credential replacement, use the existing helper in an unrecorded terminal;
see the [manual deployment procedure](HERMES_MANUAL_DEPLOYMENT_GUIDE.md).
Never paste bot tokens into chat or capture the provisioning terminal.

## Provider credential maintenance

Provider acceptance passed on 2026-09-18. To replace the disposable test credential,
use your own workstation terminal and the existing hidden-input helper:

```bash
ssh -t -i "$state/id_ed25519" -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$state/known_hosts" \
  lab@172.16.99.12 \
  'sudo -n /usr/bin/bash /home/aicowork/hermes-m02-bundle/provision-openai-key.sh'
```

Set `state` as documented above. Do not paste credentials into chat, capture this
terminal with `tee` or `script`, or reuse production credentials. After replacing a credential,
rerun the manual guide's M03 authenticated acceptance, which must
produce exact `HERMES_OK` and a successful worker tool round trip. Installation
and reboot checks alone do not establish that acceptance.

## Recovery evidence

The verified pre-expansion 40 GiB disk copy and original domain XML are root-only
under `/var/lib/libvirt/images/hermes-local-recovery-20260918/` on the workstation.
This is a pre-installation recovery point; restoring it would discard the subsequent
installation and requires an explicit recovery decision. Do not overwrite the live
disk or boot the copy alongside the original (they share identities).

Installation scripts and sanitized M02/M03 logs are retained under
`$state/installation/` on the workstation. The one-time expansion scripts are
execution evidence, not rerun instructions. The guest retains root-only metadata
backups under `/root/hermes-local-pre-expand-20260918/`.

## Cold start

Inspect the domain and network first:

```bash
sudo virsh -c qemu:///system dominfo lab-hermes-server
sudo virsh -c qemu:///system net-info lab-vlans
```

Before every cold start, apply the lab-only firewall. These runtime rules disappear
on a workstation reboot. They block guest-initiated private-network access and host
services other than lab DNS/DHCP, while allowing established replies and public
IPv4 internet access. IPv6 forwarding from the lab is blocked. Other host traffic
and firewall tables are unaffected.

```bash
sudo nft --check --file vm/networks/hermes-local-vm.nft
sudo nft --file vm/networks/hermes-local-vm.nft
sudo nft list table inet hermes_local_vm
```

Stop if either nft command fails. If the lab network is inactive, start it with
`sudo virsh -c qemu:///system net-start lab-vlans`. With the guest shut off:

```bash
sudo virsh -c qemu:///system start lab-hermes-server
```

The TPM now unlocks the encrypted root automatically. Do not start the console
helper during a normal boot. Use pinned SSH to verify readiness, then check both
Hermes services. A failed SSH check is not a successful boot; inspect the console.
VM and network autostart remain disabled, so starting the workstation alone does
not start Hermes.

## Reboot

Request the reboot through pinned SSH. No console watcher is needed:

```bash
ssh -i "$state/id_ed25519" -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$state/known_hosts" \
  lab@172.16.99.12 'sudo -n /usr/bin/bash -c "systemctl reboot"'
```

Confirm pinned SSH returns with a changed `/proc/sys/kernel/random/boot_id`.
Check that both Hermes services and Telegram return automatically.

## TPM unlock and recovery

The manual-profile enrollment adds TPM slot 1 with SHA256 PCR7 binding and no PIN.
Recovery passphrase slot 0 is retained and was tested. The initramfs includes
`tpm2-tss`, the systemd TPM token plugin and `tpm2-device=auto` in crypttab;
`/etc/dracut.conf.d/91-hermes-local-tpm.conf` retains the module for future rebuilds.
This follows the [manual boot profile](HERMES_BOOT_AUTOMATION.md#2-design-decision-simple-path-first),
not the separate signed-UKI/PCR11 deployment. PCR7 binds Secure Boot policy, not
the exact kernel/initramfs. Preserve the VM's virtual TPM state with its disk;
this does not protect against a workstation administrator controlling both.

If Secure Boot policy or TPM state changes, automatic unlocking can fail. Enter
the existing recovery passphrase in the VM console or run the fixture helper:

```bash
sudo python3 vm/hermes-luks-console.py \
  --domain lab-hermes-server --uri qemu:///system --timeout 180 \
  --event-log "$state/unlock-events.log"
```

Inspect the cause before reenrollment; do not clear the TPM or remove recovery
slots. Guest backups are in `/root/hermes-local-tpm-recovery`. Private off-VM
archives and execution scripts are in `$state/installation/tpm/`. They include
pre-change crypttab/initramfs and pre/post-enrollment LUKS headers. Header restore
is an emergency operation requiring a separate recovery decision.

## Shutdown, recovery and cleanup

For a normal shutdown, use `sudo virsh -c qemu:///system shutdown lab-hermes-server`
and verify `domstate` becomes `shut off`. Preserve the installed guest and its evidence.
Do not rerun the creator over existing storage. After an interrupted installation,
retain the disk and unlock log for diagnosis; destruction requires an explicit choice.

For explicitly authorized cleanup, the existing
[`--destroy` procedure](VM_TESTING_GUIDE.md#hermes-server-certification) removes the
guest and its dedicated disk/OEMDRV image. After confirming no other domain uses
`lab-vlans`, stop and undefine that network, then remove only the dedicated
`inet hermes_local_vm` nftables table. Remove the dedicated installer directory and
private state directory only when their evidence and SSH identity are no longer
needed. Preserve the default network and all unrelated VM storage.
