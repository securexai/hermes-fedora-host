# Portable Hermes production deployment

<!-- markdownlint-disable MD013 -->

This is the canonical procedure for the signed Fedora Server 44 production profile. Implementation and qualification are tracked in the [execution record](plans/2026-09-27-hermes-production-bundle.md). **Production acceptance is open.** Do not interpret a candidate signature, passing unit tests, or historical VM results as production certification.

The [manual-profile contract](HERMES_MANUAL_PROFILE_CONTRACT.md) remains the application security specification. The production adapter calls the same `profile-deploy.py` configuration, transport and Quadlet implementation as the [fast lab](HERMES_DISPOSABLE_LAB.md). It adds host prerequisites and transactional state handling. Existing lab entrypoints remain available.

## Fast path

A fresh server needs one prepared USB image and a handful of commands. Nobody types or remembers a secret: the installer generates the LUKS recovery key, the administrator break-glass password and the Restic password, and seals them to your escrow certificate.

```bash
P=/protected/production   # created by operator-setup; owner-only
python3 -B scripts/hermes/productionctl.py operator-setup --server server.json --output $P --apply  # once, asks two passphrases
python3 -B scripts/hermes/productionctl.py media-tools --apply                                      # once
python3 -B vm/hermes-production-qualify.py … --no-offhost-backup --live-env $P/gateway.env --apply  # qualify the release
python3 -B scripts/hermes/productionctl.py bundle --artifacts ENTRY --signing-key $P/signing_ed25519 \
  --evidence RUN/qualification.json --output $P/hermes-qualified.tar --apply
python3 -B scripts/hermes/productionctl.py media --settings $P/install.json --signers $P/allowed_signers \
  --iso Fedora-Server-dvd-x86_64-44-1.7.iso --checksum Fedora-Server-44-1.7-x86_64-CHECKSUM \
  --output $P/hermes.iso --apply
# Write hermes.iso to USB, boot the server from it, wait for the login banner.
T="--host HOST --known-hosts $P/known_hosts --identity $P/deploy_ed25519"
python3 -B scripts/hermes/productionctl.py pin-host --host HOST --fingerprint SHA256:… \
  --known-hosts $P/known_hosts --apply                               # fingerprint read at the console
python3 -B scripts/hermes/productionctl.py enroll $T --admin hermesadmin --admin-identity $P/admin_ed25519 \
  --escrow-key $P/escrow/escrow-key.pem --escrow-out $P/HOST-escrow.cms --apply
python3 -B scripts/hermes/productionctl.py attest $T --proof console --code CODE --apply   # code on the console
python3 -B scripts/hermes/productionctl.py attest $T --proof power --code CODE --apply     # after a power pull
python3 -B scripts/hermes/productionctl.py credentials $T --env-file $P/gateway.env --apply
python3 -B scripts/hermes/productionctl.py deploy $T --bundle $P/hermes-qualified.tar --apply
```

`operator-setup` creates the admin and deployment SSH keys (owner-only, unencrypted: the deployment key reaches only the bounded dispatcher and the admin key alone cannot gain root), the passphrase-protected release-signing and escrow keys, `allowed_signers`, and `install.json` from the server facts (`disk_id`, sizes, `hostname`, `timezone`, `deploy_from`, budgets, `restic_repository`). The gateway environment file (`DEEPSEEK_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS`, mode 0600) is written by you and never printed. Keep the directory on encrypted storage and back up the escrow and signing keys separately; without the escrow key a lost server cannot be unlocked by hand.

`media`, `pin-host`, `enroll` and the VM pipeline run on the workstation host (outside the Toolbox), like the VM fixture. Release qualification is one unattended command, described in [Release qualification](#release-qualification).

## Compatibility contract

- x86-64 Fedora **Server** 44; SELinux enforcing; cgroup v2; UEFI Secure Boot enabled; usable TPM2 resource manager.
- At least 8 GiB installed RAM. Root, `/etc`, `/var`, controller state and the dedicated XFS `/home/hermes` must descend through the configured LUKS2 device. The initial adapter accepts an unambiguous linear LVM stack, rejects thin/RAID/ambiguous stacks, and requires swap disabled. It never converts storage.
- Explicit filesystem UUID, LUKS UUID, machine ID and SSH public-key file hash. Missing or substituted `/home/hermes` blocks both the system user manager and each generated application service.
- One SHA256 PCR7 TPM token with no PIN, a separate escrowed recovery keyslot, matching `crypttab` and `systemd-cryptsetup` plus `tpm2-tss` in the running kernel's initramfs. Commissioning evidence must match the current boot/package/configuration identities.
- OpenSSH must enable public-key authentication and PAM for the locked deployment account. The client accepts `--port` for nonstandard SSH ports and requires the matching pinned `known_hosts` entry.
- Podman >= 5.8.4 and the packages enumerated by `production/preflight.py`, including Restic, LVM, cryptsetup, TPM tools, OpenSSH and SELinux policy. Package installation and OS patch selection happen in private commissioning, outside routine application deployment.
- `/var` free space must cover 20 GiB plus **three artifact budgets and two state budgets**. `/home/hermes` must additionally have one artifact budget plus one state budget free. Budgets are explicit byte counts, not measured installation speed promises. Monitor retained releases/backups/failed-state directories and reclaim them deliberately after successful restore rehearsals; there is no automatic pruning.
- A preexisting `hermes` account must already be locked, non-login, non-administrative, have the expected home and non-overlapping subordinate UID/GID ranges of at least 65536 IDs. Conflicting state or user unit overrides are rejected. The fresh bootstrap creates the account with these restrictions.
- Only the gateway receives provider/Telegram configuration. The offline worker uses `Network=none`, persistent SSH keys and the pinned Unix-socket transport. No application ports are published and no container-engine sockets are mounted. Container roots are read-only and limits are checked.

The gateway retains outbound network access; the worker shares its host kernel, and worker output can reach the provider through the gateway. PCR7 follows Secure Boot policy rather than an exact initramfs measurement. TPM-only unlock permits an intact stolen machine to boot and unlock when its policy is accepted. UKI/PCR11 is a different, deferred profile. See the [PCR registry](https://uapi-group.org/specifications/specs/linux_tpm_pcr_registry/) and [systemd 259 enrollment documentation](https://github.com/systemd/systemd/blob/v259/man/systemd-cryptenroll.xml).

## Controller and release preparation

Run development and verification inside the existing `dev-infra-hermes` Toolbox. The production host needs Python's standard library, not the development Toolbox. Commands below are run from this repository unless an installed absolute path is shown.

```bash
python3 -B scripts/hermes/productionctl.py --help
python3 -B scripts/hermes/productionctl.py bundle \
  --artifacts /protected/prepared-cache-entry \
  --signing-key /protected/production-signing-key \
  --output /protected/hermes-candidate.tar
```

The default is a preview. Add `--apply` to create the archive. Use a retained fast-lab preparation directory containing its `manifest.json`, `gateway.oci` and `worker.oci`. The builder checks archive hashes, the selected upstream digest and image IDs, records package inventory and hashes the shared implementation. It does not rebuild the worker. Resolve and verify the current upstream release when preparing a candidate; updating an image digest is an explicit source change followed by full qualification.

Keep the production signing key off servers. Generate it on the release workstation with OpenSSH, protect it according to operator policy, and make it available to `ssh-keygen` through the workstation's signing process. The CLI does not collect a signing-key passphrase. Never put a signing private key in Git or in a release. [OpenSSH signing](https://man.openbsd.org/ssh-keygen)

The trusted `allowed_signers` file contains the selected public key:

An unlocked workstation SSH agent is supported: pass the corresponding public-key file as `--signing-key`. Without an agent, the provided private-key file must be owner-only and usable by OpenSSH. Signing failures do not publish a partial archive.

```text
hermes-production namespaces="hermes-production-v1" ssh-ed25519 REPLACE_WITH_PUBLIC_KEY_BASE64
```

Independently verify that key's fingerprint during commissioning. The production namespace is separate from the older unattended controller. The verifier accepts regular archive members only, rejects traversal, links, duplicates, unexpected files and altered bytes, and verifies the signature before publishing any executable payload. Its project signature authenticates this project's release; it does not assert an upstream signature.

```bash
python3 -B scripts/hermes/productionctl.py inspect-bundle \
  --bundle /protected/hermes-candidate.tar --signers /protected/allowed_signers
```

A candidate cannot deploy to a `kind: production` host. Qualification supplies a JSON object with `artifact_sha256` from the candidate, `gates` and `reports`. Both maps have exactly `repository`, `installation`, `runtime`, `repeatability`, `restore`, `boot`, `application` keys. Gate values use `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`, `STALE`; report values are SHA256 hashes of separately retained, sanitized evidence. All must be `PASS` to rebuild with `bundle --evidence /protected/qualification.json --apply`. The signed manifest retains the qualification report. Source, package or image changes invalidate its artifact identity. These are release-operator attestations; the signer must inspect actual evidence, not invent a passing JSON file.

## Fresh-server installation

Use [Fedora-verified Server 44 installation media](https://fedoraproject.org/security/). Never use the older `fedora-server.ks` lab fixture on production. The production template has no fixture password, no floating disk names and no unrestricted disk clearing.

### Escrow key (once per operator)

`escrow-key --output DIR --apply` creates an RSA-4096 key and a self-signed certificate. OpenSSL asks for the key passphrase on the terminal; keep the key off servers and protect it like any root credential. The certificate is public and is rendered into installation settings. Escrow uses OpenSSL CMS AuthEnvelopedData: AES-256-GCM content encryption with the key wrapped by RSA-OAEP-SHA256.

### Installation settings

Create a non-secret settings JSON with exactly these fields (sizes are MiB, budgets bytes):

```json
{
  "disk_id": "/dev/disk/by-id/wwn-REPLACE_WITH_WHOLE_DISK_ID",
  "disk_min_mib": 180000,
  "root_mib": 30720,
  "var_mib": 81920,
  "hermes_mib": 61440,
  "hostname": "hermes.example.org",
  "admin": "hermesadmin",
  "admin_public_key": "ssh-ed25519 REPLACE_WITH_ADMIN_PUBLIC_KEY_BASE64",
  "timezone": "Etc/UTC",
  "kind": "production",
  "application_mode": "production",
  "escrow_certificate": "-----BEGIN CERTIFICATE-----\n…\n-----END CERTIFICATE-----\n",
  "deploy_public_key": "ssh-ed25519 REPLACE_WITH_DEPLOYMENT_PUBLIC_KEY_BASE64",
  "deploy_from": "192.0.2.10/32",
  "artifact_budget_bytes": 4294967296,
  "state_budget_bytes": 8589934592,
  "restic_repository": "sftp:backup@backup.example.org:/backups/hermes"
}
```

`restic_repository` may be `"none"`: an explicit decision to run without off-host backup. `backup` then refuses with `backup-not-configured` instead of implying protection, and adding a repository later is a host-configuration change (private re-bootstrap). Without an off-host copy, losing the server or its disk loses the Hermes state.

The renderer reuses the installed host contract for every value that reaches `host.json`, requires distinct administrator and deployment keys, requires an RSA escrow certificate of at least 3072 bits, and refuses budgets the requested `/var` and `/home/hermes` sizes cannot hold. Choose an unused human administrator name such as `hermesadmin`; Fedora reserves `operator`. The renderer rejects Fedora base-system and Hermes service names, the installer refuses an existing identity before storage changes, and the final installation check requires a human UID, a separate home, Bash, wheel membership, and the expected public key with safe ownership, permissions and SELinux labels.

### Build the installation image

`media` verifies the Fedora-signed `CHECKSUM` and the DVD hash, renders the Kickstart, stages the hash-pinned controller payload (controller source, `install.json`, `allowed_signers`) and runs `mkksiso` with `inst.nosave=all_ks inst.text`, selecting the plain Install entry with a 5-second timeout. `mkksiso` runs in a local tool image that `media-tools --apply` builds once from `localhost/dev-base:fedora-44`; each run uses no network, drops all capabilities and works on a private-label reflink copy of the verified DVD. Rootless containers have no loop devices, so `mkefiboot` is skipped: the UEFI boot image's `grub.cfg` (a full menu on the Fedora 44 DVD, read directly by UEFI boot) is replaced with `mtools`, `xorriso` replays both El Torito boot records, the GPT EFI System Partition that UEFI firmware boots from a USB stick is replaced with the same updated boot image (a plain replay would keep the DVD's original menu there, which starts an interactive installation), and the media checksum is re-implanted. The result is checked by extracting the embedded manifest and Kickstart, and by reading the `grub.cfg` from both the El Torito image and the USB EFI partition.

Write the image raw to a USB stick (`dd … conv=fsync`); this erases the whole stick. Do not copy the ISO onto a Ventoy or similar multi-boot stick: its own boot loader changes the Secure Boot measurement, so the installed system's TPM would not unlock automatically. `kickstart --settings … --signers … --output …` renders the Kickstart alone for review. [Kickstart syntax](https://pykickstart.readthedocs.io/en/latest/kickstart-docs.html), [mkksiso](https://weldr.io/lorax/mkksiso.html)

The ISO still boots through the signed shim and GRUB, so the installer measures the same Secure Boot PCR7 state as the installed system. Do not boot the installer kernel directly (for example `virt-install --location`): that changes PCR7 and the install-time enrollment would not unlock the installed system.

### What the unattended installation does

- `%pre` refuses a missing TPM, a non-UEFI boot, the wrong or undersized disk, an existing administrator name, a missing `inst.nosave` option, and a disk that already holds a Hermes installation unless `hermes.reinstall=yes` is on the kernel command line. It generates a random temporary LUKS passphrase in installer RAM and supplies it through a `%include`; the rendered Kickstart contains no passphrase value.
- Network services: only SSH is enabled in the firewall; Fedora Server's Cockpit web console (password login on port 9090) is disabled and its firewall service removed.
- Storage: disk-scoped `clearpart`, EFI and `/boot` outside LUKS, encrypted linear LVM with root, `/var` and dedicated XFS `/home/hermes`, no swap.
- Packages: the mandatory `restic` and `tpm2-tools` plus current signed Fedora 44 updates, using only the `fedora` and `updates` repositories with signature checks. `shim-*` keeps the installer's version: a newer shim can apply a new SbatLevel at first boot, which changes PCR7.
- `%post` (inside a private tmpfs that is unmounted afterwards): adds a systemd-format recovery key, enrolls one SHA256 PCR7 no-PIN TPM2 token, test-unlocks with the recovery key and with the TPM token, removes the temporary keyslot, labels the LUKS header `hermes-production`, writes the matching crypttab and initramfs, backs up the header, sets a random administrator password and a random Restic password, and seals the recovery key, both passwords, the header backup and an enrollment nonce to the escrow certificate. Only the ciphertext stays on the server, at `/home/ADMIN/hermes-escrow.cms`, plus a non-secret install receipt.
- The installer reboots. `hermes-commission.service` then runs on every boot until commissioning is complete.

### First boot and commissioning

The first boot generates `host.json` from the real machine ID, `/home/hermes` UUID, LUKS UUID and SSH host key, runs the same reviewed `bootstrap`, prints the SSH host-key fingerprint and a per-boot console code to the login banner, and reboots once. The second boot proves that the TPM token unseals under the installed boot path. Then, from the workstation:

1. `pin-host` scans the host key and pins it only if it matches the fingerprint you read at the console. `ssh-keyscan` alone is not authentication.
2. `enroll` fetches the escrow over the administrator key, stores it at `--escrow-out`, decrypts it in memory, proves the decrypted enrollment nonce to the host through the deployment dispatcher, and deletes the server copy. Without the escrow key the nonce cannot be produced, so a stolen deployment key alone cannot complete commissioning.
3. Physical targets only: `attest --proof console --code …` with the code shown at the console, then pull wall power, let the firmware restore it, and `attest --proof power --code …` with the power-restoration code shown after that automatic boot.

The commissioning record is written automatically with the host, boot and package hashes. Per-host proofs are `recovery_unlock`, `encrypted_offhost_recovery` and `automatic_reboot`; production targets also need `console_access` and `firmware_power_restoration`. Recovery-boot, cold-start and isolated-restore behavior is identical software on every host and is proven per release in the signed qualification evidence.

### Break-glass

`escrow-open --escrow FILE --escrow-key KEY --item recovery-key|admin-password|restic-password` prints one item to an interactive terminal only; `--item luks-header.img --output FILE` writes the header backup. The administrator password is for console emergencies; routine work goes through the deployment dispatcher.

## Existing-server preparation and private commissioning

This is a local administrator session with recovery console access. Do not grant the routine deployment key a general root shell. Preserve existing services, firewall policy, OS update policy and unrelated storage; preflight reports incompatibilities instead of repairing them automatically.

1. Verify server identity and SSH fingerprint through the console. Record `/etc/machine-id`, `/home/hermes` filesystem UUID, underlying LUKS UUID, and SHA256 of `/etc/ssh/ssh_host_ed25519_key.pub`. Build a client `known_hosts` file from the verified public key. `ssh-keyscan` alone is not authentication.
2. Set and check firmware restoration after power loss before measuring/enrolling PCR7. Verify the existing LUKS recovery passphrase **before enrollment**, using `cryptsetup open --test-passphrase` at the private console. Keep the VM/server running if recovery authentication fails; do not change keyslots, restore headers or reboot it.
3. Create an owner-only LUKS header backup on encrypted storage and verify its encrypted off-host copy and recovery instructions. Preserve the existing recovery keyslot. At the private console enroll explicitly with `systemd-cryptenroll --tpm2-device=auto --tpm2-pcrs=7:sha256 --tpm2-with-pin=no /dev/disk/by-uuid/LUKS_UUID`. Never use `--wipe-slot` as part of this deployment.
4. Configure only the matching crypttab row with `tpm2-device=auto`; ensure no unintended keyfile bypass. Detect the next boot's kernel under root with `grubby --default-kernel` and inspect `grubby --info=DEFAULT`; `uname -r` identifies the running kernel and can differ after package updates. Verify that the selected kernel and its modules are installed, retain its original image, and bind the build to that detected selection. Include `systemd-cryptsetup` and `tpm2-tss` in dracut, build a candidate with `--kver` set to the detected version, and inspect its modules and embedded crypttab before publication. Recheck the default kernel/initramfs and reject a changed selection or pending one-shot boot override before reboot. Verify reboot, complete power-off/cold start, recovery unlock, then automatic boot again. Hardware power restoration must be checked on the physical target.
5. Install compatible runtime packages deliberately. Prepare encrypted off-host Restic access with a protected repository password file and pinned SSH host identity; initialize and test the repository privately. Application operations use batch SSH and do not prompt.
6. Prepare root-owned `/root/hermes-host.json` and `/root/allowed_signers`. The host JSON has exactly the fields below. Public-key values are public material; passwords, provider keys and bot tokens are not configuration inputs.

```json
{
  "schema": 1,
  "kind": "production",
  "application_mode": "production",
  "machine_id": "REPLACE_WITH_MACHINE_ID",
  "home_uuid": "REPLACE_WITH_FILESYSTEM_UUID",
  "luks_uuid": "REPLACE_WITH_LUKS_UUID",
  "ssh_host_sha256": "REPLACE_WITH_PUBLIC_KEY_FILE_SHA256",
  "artifact_budget_bytes": 4294967296,
  "state_budget_bytes": 8589934592,
  "restic_repository": "sftp:backup@backup.example.org:/backups/hermes",
  "restic_password_file": "/etc/hermes-production/restic-password",
  "deploy_public_key": "ssh-ed25519 REPLACE_WITH_DEPLOYMENT_PUBLIC_KEY_BASE64",
  "deploy_from": "192.0.2.10/32"
}
```

```bash
sudo python3 -I scripts/hermes/productionctl.py preflight --config /root/hermes-host.json
sudo python3 -I scripts/hermes/productionctl.py bootstrap \
  --config /root/hermes-host.json --signers /root/allowed_signers
sudo python3 -I scripts/hermes/productionctl.py bootstrap \
  --config /root/hermes-host.json --signers /root/allowed_signers --apply
```

Bootstrap installs a fixed root-owned launcher and an immutable receiver under `/usr/local/libexec/hermes-production/receivers/<receiver-hash>/`, a locked non-login `hermes` runtime account, linger/mount guards and a separate `hermes-deploy` SSH account. That account has a fixed forced command and a sudo rule for the dispatcher only. It receives a small named-operation request, never an arbitrary script or command. No firewall or unrelated update settings are changed. Bootstrap inputs are protected local files; routine SSH operations cannot replace trust or host configuration. The CLI retains umask `077`. Newly created public receiver, SSH-key and Quadlet directories and their missing parents explicitly receive `0755`; private configuration/state remains `0700` with owner-only data files. Existing unsafe paths fail closed rather than being broadened. Unchanged bootstrap reruns preserve receiver files and selection. If an initial bootstrap failed before any application was deployed, a successful private retry selects its validated receiver; an active application keeps its existing receiver. Runtime sudo inspection accepts only an explicit no-privileges response, including Fedora sudo’s successful listing exit status; grants and inspection errors remain failures.

1. Provision `/home/hermes/gateway-state/.env` with `credentials --env-file … --apply` (bounded stdin to the dispatcher, values never echoed), or privately, mode 0600, inside an owner-only gateway-state directory. Initial owner is the runtime account; deployment maps it to container UID 10000. Only `DEEPSEEK_API_KEY`, `TELEGRAM_BOT_TOKEN`, and a comma-separated numeric `TELEGRAM_ALLOWED_USERS` allowlist are input credentials. The contract adds disabled allow-all/dashboard/API/webhook settings. Do not add other providers or upstream SSH-synchronization environment variables. Do not paste this file into commands, reports or chat. Protect `/etc/hermes-production/restic-password` as root:root 0600.
2. Retain a root-owned `/etc/hermes-production/commissioning.json`: `host_sha256`, `boot_sha256` and `packages_sha256` from the preflight facts/canonical JSON hashes, plus `gates` and `evidence` maps for `recovery_unlock`, `encrypted_offhost_recovery`, `automatic_reboot`, `console_access` and `firmware_power_restoration`. Use actual gate states and hashes of sanitized records. The receiver requires all applicable proofs `PASS` (fixtures: the first three); changing the host configuration or boot/package identity requires new evidence. On an existing server this record is an operator attestation; fresh installations write it automatically (see [First boot and commissioning](#first-boot-and-commissioning)).

Run installed `preflight` after commissioning. A failure lists checks without exposing command output or private values. Routine status/verification cannot promote incomplete commissioning.

## Routine operations

Before a mutating operation's first backend command, the dispatcher initializes the runtime user's rootless Podman namespace through a fixed `hermes-production-namespace` transient user service. It runs only credential-free `podman info`, waits for completion and requires a rootless result. The service uses a 120-second start timeout, a 30-second stop timeout and control-group cleanup. Its persistent namespace pause belongs to the user manager, so it cannot indefinitely hold the writer subreaper's operation lock. Initialization failure stops the operation before transaction recovery or application changes. The waiter remains supervised without a separate parent timeout; the service manager owns timeout and cleanup. Application commands continue using the existing writer subreaper. [systemd service execution and waiting](https://www.man7.org/linux/man-pages/man1/systemd-run.1.html)

The preflight's `commissioning_identity` object provides the three hashes for the commissioning record. PCR7's current SHA256 measurement participates in the boot hash, so policy changes invalidate the attestation. For a VM fixture, `console_access` and `firmware_power_restoration` may remain `NOT_RUN`; the three per-host proofs are still required. Release qualification separately requires the restore and boot gates to pass, and each physical production target requires its firmware proof.

Fixture configuration explicitly selects `application_mode: synthetic` for credential-free tests with gateway networking disabled, or `application_mode: production` for separately commissioned live application tests. A production host cannot select synthetic mode. Changing this setting changes the host identity and requires private recommissioning. No credentials are needed for the synthetic fixture's generated environment.

```bash
python3 -B scripts/hermes/productionctl.py preflight \
  --host hermes.example.org --identity /protected/deploy-key --known-hosts /protected/known_hosts
python3 -B scripts/hermes/productionctl.py deploy \
  --host hermes.example.org --identity /protected/deploy-key --known-hosts /protected/known_hosts \
  --bundle /protected/hermes-qualified.tar
```

Review the preview, then repeat with `--apply`. A refusal prints the server's sanitized reason as `STOP: remote:<reason>` (for example `remote:operation-busy`); a failing `preflight` still prints its full report. If the server stops reading an upload early, the client waits for the server's own result instead of reporting the broken pipe. The same CLI can run locally as root against installed configuration. `preflight`, `status` and `verify` are read-only; `bootstrap`, `deploy`, `upgrade`, `rollback`, `backup`, bundle creation and Kickstart rendering preview until `--apply`. Bundle inspection uses temporary staging, verifies, then removes it. Remote preview checks the host; authenticate the selected bundle with `inspect-bundle` before applying.

`deploy` refuses replacement of a different current release: use `upgrade --bundle ... --apply` for an explicitly selected update. A matching release runs verification and returns `UNCHANGED` without backup, import or restart. Operations serialize under one root-owned lock. The journal and per-attempt records retain completed stages and measured durations. Interrupted transactions recover before another mutation; read-only verification refuses unfinished transactions. Boot and container-start guards reject unfinished journals and dead operation leases. Only the active root dispatcher can temporarily allow application startup while it verifies an update or recovery.

Commands launched while holding the operation lock run below a separate Linux subreaper that inherits the same open lock descriptor. It retains that lock until the receiver and all mutating descendants have exited, including descendants that detach or close inherited descriptors. Killing the dispatcher with `SIGKILL` therefore leaves recovery reporting `operation-busy` while writers remain alive. Command timeouts terminate the command's process group and wait for any detached descendants; they never release serialization merely because the timeout elapsed. In a private investigation, let writers finish or terminate the writer processes and let the subreaper reap them. Do not kill `writer_guard.py`, delete/replace `operation.lock`, or manually clear the journal to bypass a busy operation. This uses Linux [subreaper adoption](https://man7.org/linux/man-pages/man2/PR_SET_CHILD_SUBREAPER.2const.html) and [shared open-description lock lifetime](https://man7.org/linux/man-pages/man2/flock.2.html); it does not defend against an administrator deliberately killing the guard itself.

If recovery activation, verification, pointer selection or journal finalization fails, cleanup attempts both gateway and worker stops, then checks for remaining containers. An error stopping one service does not skip the other. The unfinished journal and a unique `attempts/ATTEMPT.recovery-failed-ID.json` record retain the interrupted stage, recovery phase and `services_stopped` result without exception text or command output. A finalization failure restores the unfinished journal even if its terminal rename already happened. `service-stop-failed-safety-unconfirmed` means service shutdown could not be established; do not treat the application as safely stopped. `retention-failed` additionally identifies journal/evidence persistence failures requiring private filesystem investigation. Preserve these records, correct the reported failure and retry `rollback --apply` through the dispatcher; recovery repeats the stopped-state restoration before activation. A successful retry retains earlier failure records. Failed initial installation has no prior snapshot and requires private recovery rather than automatic rollback.

An update stops both writers, takes a consistent state/configuration/identity snapshot, imports both retained images, configures through the shared engine, starts services and verifies. `rollback --apply` restores the snapshot's matching state, configuration, Quadlets and retained image pair and exact receiver version before committing recovery. Every release is checked against all of its retained receiver/helper hashes. Configuration and verification run through the matching receiver in an isolated Python process; a mixed helper set is refused. The journal remains unfinished until both controller selection and the matching application pointer are durable. If interrupted between those writes, the selected receiver recovers the prior snapshot and both pointers before the journal becomes stable. It never simply starts an old image against migrated data. Failed-attempt state is retained under private `.failed-*` directories on the Hermes filesystem. Runtime UID/subordinate mappings must match the snapshot; remapping is not automatic.

`credentials --env-file FILE --apply` validates the gateway environment locally (exactly the three operator settings, optionally the four disabled-feature switches), sends it over the dispatcher's standard input, writes it owner-only without echoing values, and restarts and verifies a running release. Synthetic hosts refuse it. At start the gateway image adds its own `API_SERVER_KEY` for its built-in API server to the stored file; checks of the stored file accept that one container-managed key, while `API_SERVER_ENABLED` must remain `false` and no port is published. Operator files may not contain it. `attest` accepts only codes from the escrow or the console; neither `attest` nor `credentials` needs complete commissioning.

`verify` performs configuration, image, resource, process identity, SELinux label, rootless, read-only, socket transport and worker network checks. It does not make a paid provider request. Upstream transfer-canary, wrong-host-key rejection, actual approval handling and Telegram authorized/unauthorized interactions remain separate qualification tests.

`backup --apply` takes a stopped-state snapshot and sends it, the matching release and its immutable receiver to the configured encrypted off-host Restic repository, then restarts services. It requires a previously initialized repository and protected SSH/password access. It does not prune snapshots. Follow the [Restic SFTP preparation procedure](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html).

## Recovery and isolated restore

On an empty commissioned synthetic fixture, use the local-only `restore-rehearsal --snapshot FULL_RESTIC_SNAPSHOT_ID` command, then add `--apply`. It restores and verifies into private encrypted staging, validates the signed release and state archive, extracts safely and compares the restored files. It removes its staging afterward and retains `/var/lib/hermes-production/restore-rehearsal.json`. It never starts a restored live gateway. This provides filesystem-restoration evidence; application restart and boot recovery remain distinct acceptance checks.

The installed receiver and shared Python helpers must match those hashed by each release, including the rollback release. For a controller update, privately run the same reviewed `bootstrap --config ... --signers ... --apply` from the new source before sending its qualified bundle. On a host installed from the unattended image, copy the source with the administrator key and run bootstrap with the escrowed administrator password at the `sudo` prompt:

```bash
cd scripts/hermes
tar -cf - productionctl.py production-launcher.py lab_profile.py production/*.py | ssh -i $P/admin_ed25519 -o UserKnownHostsFile=$P/known_hosts hermesadmin@HOST 'rm -rf ~/hermes-controller && mkdir -m 700 ~/hermes-controller && tar -C ~/hermes-controller -xf -'
cd -
ssh -t -i $P/admin_ed25519 -o UserKnownHostsFile=$P/known_hosts hermesadmin@HOST 'sudo python3 -I -B ~/hermes-controller/productionctl.py bootstrap --config /etc/hermes-production/host.json --signers /etc/hermes-production/allowed_signers --apply'
```

 Bootstrap stages that receiver alongside the existing version and leaves the active receiver selected. Then use the ordinary explicit `upgrade --bundle ... --apply`. Missing or altered receiver code is rejected before stopping the application. The transaction selects the new receiver only after application verification; failed updates and explicit rollback restore the previous selection with its matching state/configuration/images. Retain **both** receiver directories and their releases for as long as rollback or backup recovery may need them. There is no automatic receiver pruning.

The fixed launcher and transaction protocol are version 1. Bootstrap refuses an unfinished transaction, inconsistent controller/application pointers or an attempted launcher change. Recover a pending transaction through `rollback --apply` before staging another receiver. A protocol/launcher change or a legacy flat receiver layout requires a separately reviewed private migration; do not overwrite the launcher or copy new helpers over an existing receiver. Ordinary application updates cannot install controller code or change signer trust.

For isolated off-host restoration, privately bootstrap the exact source version required by the backup before rehearsal. The restored receiver copy is hash-checked against the signed release as well as the locally commissioned copy; it is never automatically executed from backup staging.

Keep production disconnected from an isolated rehearsal to avoid two gateways sharing a live Telegram token. Use an encrypted, isolated fixture with the same runtime UID/subordinate mappings for application restoration. Retain the isolated result and measured state/configuration/identity checks; a successful `restic backup` or `restic check` alone does not prove restoration. The local rehearsal command supplies filesystem evidence; application startup with restored state and boot recovery require the private operator procedure and remain explicit qualification gates.

If TPM unlock fails, use the retained recovery passphrase through the private console. Do not auto-wipe TPM slots or automatically restore a header. After recovery, inspect Secure Boot/PCR policy changes and initramfs contents, requalify the boot sequence, and only then refresh commissioning evidence. Keep old headers and failed-attempt evidence protected and separately labeled.

## Release qualification

`vm/hermes-production-qualify.py` qualifies a release in one unattended command, on the workstation host:

```bash
python3 -B vm/hermes-production-qualify.py --iso Fedora-Server-dvd-x86_64-44-1.7.iso \
  --checksum Fedora-Server-44-1.7-x86_64-CHECKSUM --artifacts .toolbox/hermes-disposable/v2/prepared/ENTRY \
  [--no-offhost-backup] [--live-env gateway.env] [--toolbox dev-infra-hermes] [--replace-previous] [--keep] --apply
```

Without `--apply` it previews. A run creates `.toolbox/hermes-qualify/runs/UTC/` (owner-only) with throwaway administrator, deployment, signing and escrow keys, signs a candidate from the current source plus an upgrade-marker and a payload-corrupt variant, builds the ISO with a serial console, and installs the owned VM `hermes-production-qualify` (Secure Boot with enrolled keys, swtpm TPM2, 9 GiB, an unrelated canary disk, SSH on `127.0.0.1:22227` only) from that ISO attached as a read-only USB disk, the same firmware boot path as a production stick. It first runs the canonical offline gate in the Toolbox. It then uses the real operator interface: console-fingerprint pinning, escrow enrollment, deploy, unchanged rerun, refused corrupt update with the current release unchanged, a second request refused with `operation-busy` while an upgrade holds the lock, upgrade and rollback, a dispatcher killed with `SIGKILL` during image import and recovered to the previous release, a missing `/home/hermes` that blocks both the runtime user manager and the dispatcher until remounted (fault injection uses the VM's escrowed test break-glass password), warm reboot, cold start, a recovery boot (one boot with Secure Boot disabled changes PCR7, the TPM refuses and the escrowed test recovery key unlocks), an automatic boot afterwards, and the canary hash. No passphrase prompt may appear on any automatic boot. Every stage is timed in `qualification-report.json`; `qualification.json` feeds `bundle --evidence`.

The VM never reuses the older `hermes-production-qualification`/`hermes-production-restore` guests. `--replace-previous` removes only a VM whose ownership record carries the pipeline role. Test secrets stay in the run directory.

Gate results: `repository`, `installation`, `runtime`, `repeatability` and `boot` come from the stages above. `restore` passes on failed-update restore, rollback and interruption recovery only with `--no-offhost-backup`, and the report then records that operator waiver; otherwise it stays `BLOCKED` until isolated restore from an encrypted off-host Restic repository runs. `application` is `BLOCKED` unless `--live-env FILE` is given: the VM then runs in production application mode with your credentials, and in an interactive terminal you confirm that a harmless terminal command (`uname -sr`) runs and answers, that a destructive one (`rm -rf /tmp/hermes-approval-check`) stops for your Telegram approval and does not run when you deny it (the contract requires approval for dangerous commands and memory writes, not for every command), and that the bot ignores you while the pipeline temporarily allowlists a different user ID. Run it only while no other gateway uses the same bot token. A release is production-qualified only when all seven gates pass.

| Gate | Required observation |
| --- | --- |
| repository | Canonical Toolbox offline checks, check-only lint, links, full-tree secrets and migration provenance |
| installation | Unattended installation from the built ISO, automatic commissioning, escrow enrollment, unrelated disk intact |
| runtime | Correct host acceptance and incompatible-host rejection; effective tool/config/approval contract, identities, SELinux, mount guards, no ports/engine mounts, worker isolation, pin rejection and SSH credential canaries |
| repeatability | Unchanged deployment, concurrent operation rejection, corruption rejection, interruption and missing-mount failure |
| restore | Failed upgrade restores matching state/config/images; encrypted off-host backup restores into an isolated fixture |
| boot | TPM unlock, reboot, cold start, recovery-key unlock and subsequent automatic boot |
| application | Exact-candidate DeepSeek tool round trip, Telegram authorized/rejected users and approval behavior |
| physical target | Console code and power-restoration code attested on each target |

Record `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN` or `STALE` with the exact artifact/environment identity. Preserve unsuccessful runs. Synthetic tests do not establish runtime security or encrypted production timing.

`vm/hermes-production-fixture.py --role qualification|restore|qualify --console` attaches a terminal to a fixture console (`Ctrl+Q` detaches); it never starts, reinstalls or captures the guest.

## Patches and Fedora upgrades

Application updates require a new explicit signed/qualified bundle; no automatic release promotion is installed. Existing OS update policy is preserved. Before relevant Podman/systemd/SELinux/kernel/firmware/boot-policy changes, verify backup and recovery availability, record the proposed package set, rehearse the affected controls and refresh target evidence. Host checks deliberately stop unattended application operations when commissioning fingerprints are stale.

Fedora's approximately 13-month maintenance period makes release migration necessary. Plan the next supported Fedora qualification before Fedora 44 reaches end of maintenance; do not carry an obsolete Fedora44 acceptance record into a later release. [Fedora lifecycle policy](https://docs.fedoraproject.org/en-US/releases/lifecycle/)
