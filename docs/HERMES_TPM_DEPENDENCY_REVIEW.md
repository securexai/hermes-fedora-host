# Hermes standard TPM2 dependency review and migration

Review date: 2026-09-10. **Prepared locally; not applied or certified on production.**
The [execution record](plans/2026-09-07-hermes-unattended.md#architecture-reassessment-amendment-authorized--2026-09-10)
is the sole task tracker (AR01–AR05); this document is the current dependency and migration procedure.
[Sanitized evidence](plans/evidence/2026-09-10-hermes-tpm-dependency-review.json) separates live observations,
operator reports, retained artifacts, source analysis and local tests. Earlier instructions for the
[SELinux repair](HERMES_SELINUX_TPM_REPAIR.md) remain historical, with consumed invocation approvals.

## Decision and limits

Prepare the standard LUKS2/Secure Boot/signed UKI/PCR7 plus signed PCR11 path without NvPCR anchoring.
The inspected systemd code supports this separation, and the existing enrollment already uses
`--tpm2-pcrlock=`. The repository has no application consumer of NvPCR measurements. Production migration
requires fresh certification. Both requested privileged inventories were received and reviewed on September 10;
no custom NvPCR consumer was identified in the bounded configuration/package review. The operator does not know
of external integrations, and arbitrary external use remains unproven. **Do not disable the
failed setup service:** it also provisions/preserves the SRK. Keep both setup units and the PCR11 phase units.

The minimal configuration masks `hardware.nvpcr` and `cryptsetup.nvpcr` through `/etc/nvpcr`, and masks
`systemd-pcrproduct.service`, whose sole packaged operation measures the firmware product ID into hardware
NvPCR. Definition masks alone are insufficient: that consumer directly loads its definition and may fail.
The additive dracut file carries these masks into future initrds while retaining TPM/TSS and PCR11 modules.
This uses package configuration rather than replacing systemd binaries or granting additional SELinux access.
No existing NV index, SRK, anchor, slot, credential, policy module or firmware entry is deleted by preparation.

If inventory finds an active custom NvPCR consumer or an anchor-dependent policy that must be preserved,
stop this migration. Document its concrete caller, input policy and recovery requirement; reassess the
minimal configuration. Only then resume the evidence-justified parts of SE23–SE25. A failed service or an
AVC count alone does not justify extra permissions. The v2 policy and prepared v3 material are retained.

## Dependencies and evidence

“Required” means required by the approved outcome or selected architecture. “Optional” describes a supported
feature with no identified Hermes requirement. “Unverified” is an unmet evidence prerequisite, not absence.

| Dependency | Classification | Evidence and implication |
| --- | --- | --- |
| LUKS2 encrypted root and offline recovery | Required | Recorded production device `/dev/nvme0n1p3`; accepted credential test returned 0 on September 9. Protected header/boot backups have an off-host integrity pass. Actual offline recovery boot remains untested. |
| TPM automatic disk unlock | Required | Normal boot cannot prompt. Existing token 1/keyslot 2 uses SHA256 PCR0/7 and failed policy checks before manual unlock. It has no recorded signed-PCR or PCR-lock binding. Anchor repair would not fix that mismatch. |
| TPM SRK | Required for the selected TPM path | `systemd-tpm2-setup` runs SRK setup separately from NvPCR enumeration. Unseal/seal operations use the TPM primary/storage key machinery. Preserve the TPM key and public-file identities; do not equate public-key files with the secret TPM key. |
| Both SRK setup units | Retained package implementation | Live early unit succeeded; late unit failed after SRK matching, during anchor persistence. Units are wanted by sysinit, with no reported RequiredBy consumer. Their ordering is not proof that disk unlock depends on anchor persistence. Do not mask either unit. |
| Secure Boot and signed UKI | Required | Production RSA2048 trial boot was recorded as measured and signature-trusted. Live Secure Boot/Enforcing checks pass. September 10 inventory identifies the selected RSA2048-v2 entry and its on-disk hash matches the retained UKI. This is not a new measured-boot or next-default acceptance test. Firmware → dedicated Fedora shim → signed systemd-boot → signed UKI preserves existing Fedora recovery. |
| Intended kernel/initrd/command line | Required | Builder embeds `.linux`, `.initrd`, `.cmdline`, `.osrel`, `.pcrpkey`, `.pcrsig`. Selected-file and current initrd hashes match retained build inputs. Reuse their inspected TPM plugin/TSS/PCR11 support and crypttab: no keyfile, only discard,x-initrd.attach,tpm2-device=auto. That initrd has no NvPCR setup/definitions. |
| Signed PCR11 policy and measurement phases | Required | Installed builder signs enter-initrd, leave-initrd, sysinit and ready states. This supports disk unlock and late credential access with a stable policy key across approved updates. Retain those phases; signing a new UKI is not manual TPM reenrollment. |
| PCR-lock policy | Optional, not selected | Lab enrollment explicitly passes empty `--tpm2-pcrlock=`. Recorded production token has no PCR-lock fields; standard policy JSON paths are absent. The seven packaged services are disabled/inactive, and no template instances are loaded or enabled. PCR-lock uses TPM NV authorization policy data; it is distinct from NvPCR measurement/anchoring. |
| NvPCR initialization | Optional for inspected Hermes path; arbitrary external use unproven | Live vendor definitions are hardware index 0x1d10200 and cryptsetup index 0x1d10201, with no /etc overrides. Setup enumerates unmasked definitions. This package default creates the anchor dependency; ordinary signed-PCR11 LUKS enrollment does not. |
| NvPCR anchor persistence | Required only while using those NvPCRs | Setup synchronizes the encrypted anchor from /run to /var and ESP so early boots can retain the same identity. /var alone is unavailable before encrypted root unlock. No ESP anchor was accepted in SE22. Preserve existing encrypted copies; do not treat replacement as continuity. |
| Product-ID measurement | Optional for this selected path | The installed unit calls only `systemd-pcrextend --graceful --product-id`, targeting hardware NvPCR. Local test logic required it active; the Hermes application and its configured SSH/machine identity do not consume it. The completed bounded audit found no custom consumer; arbitrary external attestation use remains unproven. |
| NvPCR separator unit | Retained, no anchor dependency found | Installed `systemd-pcrnvdone.service` measures a separator into PCR9 and has initrd-only conditions. It does not initialize an NvPCR. Retain it and normal PCR11 services; do not mass-disable PCR services. |
| Cryptsetup keyslot measurement | Optional, off in observed root/generated/retained initrd | systemd enables NvPCR keyslot measurement only with nonempty `tpm2-measure-keyslot-nvpcr=`. Supplied root crypttab and independently inspected effective generated command show TPM auto, no NvPCR/PCR-lock option and no root crypttab keyfile. |
| Runtime credentials | Required; expected production files absent | The expected encrypted provider credential, host credential secret and credential service are absent. This is unfinished enrollment, not proof that all legacy credentials are absent. Repository uses host+tpm2, `LoadCredentialEncrypted`, a volatile read-only provider overlay and ordered user-manager startup. Future encryption explicitly requires PCR7 and the PCR11 public key; the persistent public-key path must first be installed under enrollment approval. |
| Workstation broker, signing, Restic, release and SSH identity | Required, independent of host NvPCR in inspected code | Preserve separate roles, encrypted backups, semantic restore, release signatures and host binding. There is no repository consumer connecting these to Hermes NvPCR. Do not bundle workstation credential/privilege migration into the production operation; the separate temporary lab controls are tracked below. |

Source basis: upstream [setup implementation](https://github.com/systemd/systemd/blob/v259/src/tpm2-setup/tpm2-setup.c)
and [configuration masking](https://github.com/systemd/systemd/blob/v259/src/basic/conf-files.c) establish separate
SRK/NvPCR operations and administrative masks. [NvPCR and anchor code](https://github.com/systemd/systemd/blob/v259/src/shared/tpm2-util.c)
explains definition loading and persistence. [Product measurement](https://github.com/systemd/systemd/blob/v259/src/pcrextend/pcrextend.c)
and [crypttab options](https://github.com/systemd/systemd/blob/v259/man/crypttab.xml) identify the explicit consumers.
[Credential documentation](https://github.com/systemd/systemd/blob/v259/man/systemd-creds.xml) describes automatic
public-key discovery and empty default fixed-PCR selection; the
[credential implementation](https://github.com/systemd/systemd/blob/v259/src/shared/creds-util.c) supplies no PCR-lock
policy. [UKI documentation](https://github.com/systemd/systemd/blob/v259/man/systemd-stub.xml) explains embedded
command-line protection and PCR signatures. These are v259 family sources, not a verified Fedora 259.8 source
reconstruction. Installed Fedora unit/dracut files were read separately; downstream and hardware behavior must
pass the fresh lab/production gates. Missing upstream paths and failed retrievals are recorded in evidence.
Cryptsetup 2.8.7 documents [token-only verification](https://github.com/mbroz/cryptsetup/blob/v2.8.7/man/cryptsetup-open.8.adoc)
and the distinct [token metadata operations](https://github.com/mbroz/cryptsetup/blob/v2.8.7/man/cryptsetup-token.8.adoc).

## Inventory received and reviewed

The operator's 2026-09-10 15:44 UTC JSON satisfies the requested bounded privileged inventory. Its UKI and
initrd hashes exactly match the retained RSA2048-v2 build. The selected entry is
`hermes-trial-rsa2048-20260909.conf`; `/run/systemd/tpm2-pcr-public-key.pem` matches the reviewed policy key.
Independent read-only SSH at 15:47–15:48 UTC confirms that public file is regular, root-owned and 0444,
while `/etc/systemd/tpm2-pcr-public-key.pem` is absent. Install only the reviewed public key during the
separately approved enrollment step; do not recreate signing keys or silently change the credential key path.

The root crypttab has TPM automatic unlock, no keyfile and no NvPCR/PCR-lock option. The loaded generated
cryptsetup command confirms those policy-option results, with only the packaged timeout drop-in. The bounded
configuration scan finds packaged PCR-lock, product and separator units; all seven non-template PCR-lock
services are disabled/inactive, and no template instances are loaded or enabled. Product measurement remains
active and both setup invocations are unchanged: early succeeded, late failed. Preserve that failure.
The template itself has no runnable uninstantiated unit; its `systemctl show` query returned 1. Reading its
packaged file and listing unit files confirmed the static template, without starting an instance.

`/etc/credstore.encrypted/hermes-openai-api` and `/var/lib/systemd/credential.secret` are absent in the
operator's privileged metadata. Their future creation and reboot/isolation proof remain required. This does
not inspect or classify other legacy credential locations. No extra runtime change follows from these facts;
the prepared migration already requires public-key installation and explicit credential enrollment.

`BootCurrent: 0006` is absent from `BootOrder: 0001,0008,0003,0000`, and no BootNext line was reported.
The selected trial entry and matching file hashes do not prove the next power-on default or that on-disk bytes
are a fresh measurement of the running image. Default selection, cold boot and previous-image acceptance remain
B1–B3 gates. No firmware selection was changed. Custom scripts, arbitrary TPM objects and remote attestation
outside the bounded scan remain unproven; the completed collector does not establish their absence.
No additional operator diagnostic is requested for AR01.

## Local implementation and evidence applicability

- [Profile renderer/checker](../scripts/hermes/unattended/tpm_profile.py): renders four configuration paths into
  an existing private offline directory, refuses `/`, refuses symlinked parents/conflicts, and can resume a
  partial render. Existing unrelated files are preserved. Partial/truncated conflicting content stops for review.
- [Host preflight](../scripts/hermes/unattended/host.py): every systemd TPM token must select exactly SHA256
  PCR7 and signed PCR11, have public-key metadata, use no PIN and no PCR-lock. A stronger new token cannot hide
  the old automatic path. Metadata checks do not prove key identity, token selection, or actual unsealing.
  All additional unlock mechanisms must still be reviewed in certification.
- New runtime credential encryption explicitly passes the public-key path and PCR selections. Existing
  credentials are not automatically reencrypted. Missing/wrong key or failed encryption must stop issuance;
  no downgrade to host-only or plaintext is introduced.
- The disposable installer now carries the same renderer and its shared helper on verified OEM media and runs
  it against the offline installation root before dracut. The lifecycle checks baseline and updated initrd
  archives for all three exact masks, TPM/PCR11 module metadata and unknown NvPCR definitions before UKI signing.
  Archive masks may use /dev/null or dracut's exact relative equivalent; relative traversal requires
  unambiguous directory entries. Sanitized mask/module verdicts and the archive hash survive a failed check
  and secret cleanup. These checks do not prove boot or absence of every embedded secret; B1–B7 remain necessary.
- Certifier/lifecycle observers use the same profile check. Vendor profile still requires product measurement;
  standard profile requires its mask and rejects newly introduced unmasked definitions. Both require successful
  setup and matching early/persistent SRK public files. A skipped early unit is allowed only with its failed
  condition and matching public files; late failure, exit 76 or a masked setup unit fails. Actual unattended
  unlock remains an independent boot test. New payloads include the checker and receive new fingerprints.

Historical UA-01–UA-04, S4/F4 and policy evidence remains attached to its original artifacts. Changed host,
observer, payload or profile input makes amended candidate boot/runtime/credential/replay/certification and
promotion evidence **STALE**. Fresh UA-01 then UA-02–UA-04 is required before amended UA-05. P2 never passed;
P3/P4 remain blocked. Unchanged recovery backups, original signed archives, advisory/denylist policy and v2/v3
sources retain only their already recorded scope. Source preservation is not a new runtime pass.

## Acceptance gates

Execute each on an authorized disposable candidate first and on production only with concrete operation approval.
Record candidate/run identity, host/TPM/boot ID, image and initrd hashes, package inventory, token policy/key
identity, configuration hash, timestamps, command/method, result and secret-free evidence. Never copy lab PASS
into production. No existing lab grant or consumed service-invocation approval is reusable.

| Gate | Method and required result | Stop/recovery condition |
| --- | --- | --- |
| B1 unattended cold boot and Hermes startup | Independently establish powered-off state, start without console/key injection and with automation stdin closed; bound SSH readiness wait. Verify selected measured signed UKI, Secure Boot, Enforcing, TPM unlock with no passphrase fallback, SRK continuity, credential service, rootless/read-only runtime and exact HERMES_OK inference. Repeat normal reboot with the same observations. | Timeout, prompt, fallback unlock, wrong image/key/domain or runtime failure leaves P2 open. Use B5 recovery under its approval. |
| B2 approved update | Freeze exact signed RPM transaction and new UKI from matching kernel/initrd/command line using controller/protected production keys. Assert previous kernel-core/modules are retained by transaction. Back up/verify semantic restore, replay, boot and run B1 checks without reenrollment. Verify both artifact signatures and matching policy-key identity. | Never select before modules are installed. Before selection, failed replay retains the old default; failure after selection requires explicit recovery and verification of the actual selected entry. |
| B3 previous approved image | Keep prior UKI, its signed PCR11 policies, matching kernel modules and usable boot chain. Select it once under approval, boot without input and verify unlock, credential access, runtime and package compatibility. Then return to accepted default under approval. | Existing Fedora/GRUB entry is recovery availability, not previous-approved-UKI proof. A prior trial image is not automatically certified for the new profile. |
| B4 unauthorized artifacts | In lab, separately alter kernel, initrd and embedded command line without resigning; verify signature rejection. Also test a Secure-Boot-trusted image without an approved PCR11 signature: no automatic root unlock or credential release. Validate external command-line override is ignored/rejected under Secure Boot. No recovery key is injected into these tests. | A weaker parallel token may defeat policy rejection. Review all automatic paths and remove/retire only under separate approval. No production tamper test by overwriting an approved image. |
| B5 recovery | Operator uses the independently retained offline recovery key to open the actual LUKS device from trusted recovery media with automatic TPM unlock unavailable, mounts/accesses expected root data and preserves header/slot inventory. Test access, not just availability; retain off-host header/EFI backups. | Do not deliberately clear TPM, delete slots or alter anchors to simulate failure. Header restoration is an emergency destructive operation with separate approval. |
| B6 credentials | After B1/B2/B3, independently verify credential service start, correct key delivered only to the intended volatile read-only mount, modes/ownership and no value in bounded process/inspect/log/config output. Test failed untrusted boot cannot release a disposable credential in lab. | Missing key/signature, incorrect account, wrong boot state or leak blocks promotion. Explicit credential rotation/reseal acceptance and old-key retention are required before replacement. |
| B7 idempotency/interruption/preservation | Rerun profile/config and completed controller stage; compare exact files, tokens/SRK/anchors, SSH/firmware identity, SELinux and unrelated settings. Interrupt before/after artifact copy, package replay and boot selection in disposable fixtures. Verify recoverable state, atomic final publication, preserved previous image/modules, backup snapshot, bounded retries and one meaningful notification. | Do not treat a partially written image, partial profile, changed baseline or failed transaction as success. Trust/configuration changes invalidate earlier results. |

## Migration preparation and approval sequence

This is a review procedure, not authorization to execute production blocks. Read-only probes and local
rendering are authorized now. New lab runs, production writes, service invocation, boot selection/reboot,
credential operations and policy/privilege changes need explicit approval for each concrete block.

1. Reuse both accepted inventories above and SE22 request metadata; do not repeat either collector. AR01
   bounded review is complete. If later evidence identifies an external anchor/NvPCR consumer, stop and reassess.
   Preserve SE22 FAIL and all three attempts. Root/generated/initrd options and current selected-file hashes
   match the reviewed standard path. Recheck operation-specific identities before a later approved mutation;
   stop on drift.
2. Recheck retained recovery and physical console readiness without asking for any secret. Before any production
   mutation, make a fresh root-private header/boot/configuration/anchor inventory and verified off-host backup
   under a concrete backup approval. Use the existing
   [boot recovery backup](HERMES_UNATTENDED_DEPLOYMENT.md#production-boot-recovery-backup); record which of the
   four new configuration paths were originally absent. Never export plaintext credentials or signing keys.
3. Render the proposed configuration locally. This creates no live service or TPM operation:

   ```bash
   # The inner shell owns the staging variable.
   # shellcheck disable=SC2016
   devbox run -- bash -c '
   stage=$(mktemp -d /tmp/hermes-standard-tpm2.XXXXXXXX)
   python3 scripts/hermes/unattended/tpm_profile.py --root "$stage"
   printf "%s\n" "$stage"
   '
   ```

   Review these exact destinations and contents:

   ```text
   /etc/nvpcr/hardware.nvpcr -> /dev/null
   /etc/nvpcr/cryptsetup.nvpcr -> /dev/null
   /etc/systemd/system/systemd-pcrproduct.service -> /dev/null
   /etc/dracut.conf.d/99-hermes-standard-tpm2.conf
   ```

   The last file adds `tpm2-tss systemd-pcrphase` modules and explicitly installs the three masks. Existing
   dracut configuration remains intact; inspect conflicting omit rules. The renderer cannot be used on `/`.
   After step 4 passes, under step 5 configuration-only approval, install only absent paths exclusively, or verify an
   existing path matches exactly. Stop on any different content or symlink. Do not run systemctl mask/start,
   daemon-reload or dracut as an incidental side effect of copying these four paths. Do not remove vendor files.
4. Obtain a fresh bounded lab grant and apply the reviewed profile to a disposable fixture. Build its initrd
   through Fedora dracut, inspect the actual archive for all three masks plus cryptsetup/TSS/PCR11 support,
   and confirm no embedded secret/keyfile or active NvPCR consumer. A config-file check cannot prove dracut
   copied symlinks. Build/sign with the existing controller and separate lab keys. Run B1–B7 and ordered
   UA-01–UA-04 including revoke/purge/destroy. Close the grant; never reuse a consumed allowance.
5. Only after lab acceptance, prepare a **new** production initrd/UKI with a unique versioned filename, keeping
   the production Secure Boot key and RSA2048 PCR11 key already prepared. Do not replace their files. Use
   `dracut --force <new-private-initrd-path> <approved-kernel-version>` only under the production build approval;
   never regenerate every installed initrd in this migration. Export boot inputs privately and use
   [boot_build.py](../scripts/hermes/unattended/boot_build.py) with explicit inputs. Compare embedded public key,
   command line and `.pcrsig` coverage; independently sbverify the complete UKI. Keep the previous image and
   its matching modules, and free ESP space for a complete temporary copy plus retained images.
6. Prepare the previous approved image under the same no-NvPCR profile, or demonstrate an already retained image
   satisfies B3. Rebuilding changes its identity and requires signing/certification. The old unmodified trial
   and original Fedora path remain emergency recovery paths; do not count them as B3 without observation.
   Stage each complete verified file atomically beside existing files, add a uniquely named entry, and retain
   firmware defaults. One-shot selection, a supervised boot and any service invocation are separate approvals.
7. After the new measured UKI boots with physical recovery available, propose **additive** TPM enrollment:

   ```bash
   sudo systemd-cryptenroll /dev/nvme0n1p3 \
     --tpm2-device=/dev/tpmrm0 --tpm2-pcrs=7:sha256 \
     --tpm2-public-key=/etc/systemd/tpm2-pcr-public-key.pem \
     --tpm2-public-key-pcrs=11 --tpm2-with-pin=no --tpm2-pcrlock= \
     --tpm2-signature=/run/systemd/tpm2-pcr-signature.json
   ```

   This command requires its own enrollment approval and one-time operator recovery authentication; never
   capture it with tee/script or store a recovery key in argv. Before execution, install/verify only the
   reviewed **public** RSA2048 key at the stated path under that approval. Verify it matches the running and
   previous approved UKIs. No wipe-slot option is used. Record new token/slot identities and exact policy.
   Use token-only noninteractive unlock verification under separate concrete approval before trusting it:
   `sudo cryptsetup open --type luks2 --test-passphrase --token-only --token-id=<new-token-id>
   /dev/nvme0n1p3 </dev/null`. Substitute the independently observed numeric ID; do not guess it.
   This verifies that token alone, not cold boot or the absence of alternative unlock paths.
8. The old token 1/PCR0+7 is a parallel automatic path. Keep it and slot 2 during additive enrollment and
   recovery/new-token verification, but do not claim final signed-PCR11-only protection while it is usable.
   **Removing only the token metadata is not revocation:** a retained blob can still unlock its surviving
   slot. The final legacy-slot decision remains a separate approval gate. If fresh inventory proves slot 2
   is exclusively the old TPM slot, the new token alone passes, and a different offline recovery slot passes
   an explicit `--key-slot=<recovery-slot>` test with external tokens disabled, prepare this exact retirement:
   `sudo cryptsetup luksKillSlot /dev/nvme0n1p3 2`. No such operation is authorized or executed in this review.
   Recheck device UUID, entire header/token/slot inventory and backup immediately before requesting approval;
   stop on any drift. Never run a blanket `--wipe-slot=tpm2`, which could also remove the new enrollment.
   If retirement is declined, retain the state and leave B4/final enrollment blocked unless equivalent
   restriction of that path is independently demonstrated. Header backups retain earlier access and must
   remain protected; current-header retirement does not prove resistance to attacker-held historical-header
   rollback. That stronger threat would require a separate design review, not an implied NvPCR guarantee.

9. Execute B1–B7 under concrete production approvals; set the permanent boot default only after acceptance.
   Preserve failed service/audit evidence; a new boot, not reset-failed, must establish current successful
   SRK setup without anchor creation. Keep SELinux Enforcing and the installed v2 policy during the first
   scoped migration. Any later removal of the local module/context is a separate privilege/policy operation
   requiring its own review and stock-policy evidence. No v3 permission expansion is bundled here.
10. Pass P2 before P3 enrollment of restricted identities and a fresh production-bound signed release. The
    controller's new credential command applies only during authorized credential provisioning. Verify B6
    before rotating/replacing an existing production credential. P4 then verifies runtime, backup/restore,
    inference and rerun behavior. Keep official upstream images, advisory scanning with denylist, protected
    signing/release verification, host binding, Sunday 02:00–04:00 Bogotá windows and meaningful notifications.
    Timer enablement and any privileged operational grant remain separate authorizations.

## Recovery and interrupted migration

If copying configuration stops, preserve evidence and stop dependent builds/boots. Rerun only after comparing
all four paths; identical complete paths can remain. Restore changed paths from the per-operation backup only
under recovery approval. For paths originally absent, removal of exactly the three matching /dev/null symlinks
and the hash-matching dracut file reverses configuration; do not recursively delete directories or vendor files.
This does not revert an initrd/UKI already built with the profile. Keep that file as failed evidence and select
the prior verified entry once under approval. Do not rebuild the previous image during recovery.

If artifact publication or package replay is interrupted, do not select partial files or infer completion from
SSH returning. Compare the signed manifest and replay journal, kernel/modules inventory and boot ID. Existing
controller replay only selects the new entry after successful package installation; uncertain replay remains
an explicit OS-recovery state. Preserve its snapshot and journal. The previous UKI alone is insufficient if
its modules were removed; transaction retention is therefore a required B2/B3 check.

If TPM unlock fails, use the physical console and trusted Fedora/recovery boot with the offline key. Do not
clear the TPM, replace anchors or reenroll repeatedly. Preserve current LUKS metadata, SRK/public-file hashes,
boot artifact, selection and scoped diagnostics. A retired slot cannot be recovered merely by importing token
JSON. Restore slot/header state only from an authenticated protected backup under an explicit destructive-recovery
review after comparing all subsequent changes; restoring an old header can restore the old weaker unlock policy.
Adding a token, changing PCR7 trust or modifying boot measurements
requires fresh acceptance; restoring firmware trust databases is not a routine rollback.

If any retained NvPCR consumer needs the old anchor, merely unmasking definitions can reinitialize measurements
under an incompatible early-boot identity. Stop, retain original encrypted anchors and the previous boot chain,
and review anchor continuity before another boot or service request. This procedure never promises anchor
recovery by copying ciphertext to /run or by replacing an NV index.

## Remaining operator evidence

The original requested JSON, SE22 metadata and LUKS diagnostics have been received and reviewed.
**Do not repeat these diagnostics or either inventory collector.** The operator answered “I don't know”
about custom/external integrations. The accessible audit found no TPM reference in 10 custom execution/configuration
files, and only TPM/TSS libraries/tools and ima-evm-utils-libs in the package-name filter.

The subsequent operator-supplied root JSON at 16:41:36 UTC closes the protected remainder: cron was visited
and empty; Hermes/root user-service and Quadlet directories were absent. It reports no hits or unreviewed paths,
coverage_complete=true and consumer_absence_proven=false. The
[live observation](plans/evidence/2026-09-10-hermes-standard-tpm2-live.json) retains the exact sanitized report
and provenance. AR01 bounded review passes: no custom NvPCR consumer was identified in the inspected scope.
Arbitrary external or remotely invoked consumers remain unproven; this does not justify an absence claim.
The [protected-only collector](plans/evidence/2026-09-10-hermes-tpm-consumer-inventory.py) remains as the
reproducible historical method; no further operator input is required for this completed review.

The collector below is retained as the reproducible method for the accepted September 10 observation. It reads
fixed public/configuration metadata and prints no TPM blob, credential value, private key or raw unit/crypttab
content. It invokes no service and writes no file. Fresh token/slot checks belong to the later operation-specific
enrollment/retirement preflight, not this completed evidence request.

```bash
sudo python3 -I -B - <<'PYINVENTORY'
import datetime, hashlib, json, os, stat, subprocess
from pathlib import Path

def run(args):
    p = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
    if p.returncode:
        raise RuntimeError("read-only command failed: " + args[0])
    return p.stdout

os.environ["LC_ALL"] = "C"
result = {"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}
entries = json.loads(run(["bootctl", "--json=short", "list"]))
result["selected_boot_entries"] = [{"id": e.get("id"), "linux": e.get("linux"), "efi": e.get("efi")}
                                   for e in entries if e.get("isSelected")]
firmware = run(["efibootmgr"]).decode()
result["firmware_selection"] = [line for line in firmware.splitlines()
                                if line.startswith(("BootCurrent:", "BootOrder:", "BootNext:"))]
result["crypttab"] = []
for line in Path("/etc/crypttab").read_text().splitlines():
    if not line.strip() or line.lstrip().startswith("#"):
        continue
    fields = line.split()
    options = fields[3].split(",") if len(fields) > 3 else []
    result["crypttab"].append({"keyfile_configured": len(fields) > 2 and fields[2] not in ("none", "-"),
        "tpm_auto": "tpm2-device=auto" in options,
        "nvpcr_measurement": any(x.startswith("tpm2-measure-keyslot-nvpcr=") and x.split("=", 1)[1]
                                 for x in options),
        "pcrlock_option": any("pcrlock" in x for x in options)})
result["boot_hashes"] = {}
for path in ("/boot/initramfs-7.1.12-200.fc44.x86_64.img",
             "/boot/efi/EFI/hermes-trial-20260909/hermes-production-rsa2048-v2.efi"):
    p = Path(path)
    if p.is_symlink() or not p.is_file():
        result["boot_hashes"][path] = "absent-or-symlink"
    else:
        with p.open("rb") as stream:
            result["boot_hashes"][path] = hashlib.file_digest(stream, "sha256").hexdigest()
result["public_key_hashes"] = {}
for path in ("/etc/systemd/tpm2-pcr-public-key.pem", "/run/systemd/tpm2-pcr-public-key.pem"):
    p = Path(path)
    result["public_key_hashes"][path] = (hashlib.sha256(p.read_bytes()).hexdigest()
                                       if p.is_file() and not p.is_symlink() else None)
result["credentials"] = {}
for path in ("/etc/credstore.encrypted/hermes-openai-api", "/var/lib/systemd/credential.secret"):
    p = Path(path)
    if not os.path.lexists(p):
        result["credentials"][path] = {"exists": False}
    else:
        s = p.lstat()
        result["credentials"][path] = {"exists": True, "mode": oct(stat.S_IMODE(s.st_mode)),
                                       "uid": s.st_uid, "regular": stat.S_ISREG(s.st_mode)}
result["consumer_references"] = []
for directory in ("/etc/systemd/system", "/usr/lib/systemd/system", "/etc/dracut.conf.d"):
    for p in sorted(Path(directory).rglob("*")):
        if p.is_symlink() or not p.is_file() or p.suffix not in (".service", ".conf"):
            continue
        if p.stat().st_size > 1024 * 1024:
            raise RuntimeError("oversized configuration; manual review required")
        text = p.read_text(errors="replace")
        kinds = [x for x in ("nvpcr", "pcrlock", "LoadCredentialEncrypted", "SetCredentialEncrypted") if x in text]
        if kinds:
            result["consumer_references"].append({"file": str(p), "kinds": kinds})
result["pcrlock_paths"] = {p: os.path.lexists(p) for p in (
    "/var/lib/systemd/pcrlock.json", "/run/systemd/pcrlock.json", "/etc/systemd/pcrlock.json")}
print(json.dumps(result, indent=2))
PYINVENTORY
```

This is a bounded inventory, not proof about every arbitrary TPM object, command-line override, custom script
or remote attestation consumer. Reference hits must be correlated with enabled/generated units before migration.
The received hashes match retained inputs, so their prior inspection is reused. Any later drift requires private
review and invalidates the corresponding boot evidence. Do not send a key, token blob, credential file or raw journal.

## Fresh lab campaign prepared on September 10

**Historical first attempt, now consumed:** L0 passed, L1 failed before the first installed boot, and L2
restoration passed. Do not reexecute this package or reuse its grant. The separately prepared
[r2 package](#corrected-integration-package-r2) below requires its own explicit approval.

The user explicitly approved AR04-L0/L1/L2 on September 10 with the protected inventory response.
That approval covers exactly the temporary operations below and one new maximum-four-hour run.
The [campaign observation](plans/evidence/2026-09-10-hermes-standard-tpm2-campaign.json) binds the prepared local
files, test results and exact source archive as prepared. The subsequent
[live observation](plans/evidence/2026-09-10-hermes-standard-tpm2-live.json) records installation, grant issuance
and execution separately; do not reuse the grant or assume completion from dispatch.

The review package is retained privately at
`/var/home/cloudops/.local/state/hermes-standard-tpm2-campaign/20260910T160319Z/review-package`.
It contains 71 frozen source files, their manifest/archive, lifecycle policy, temporary service/failure units,
socket override, fixed-domain power helper and exact sudoers entry. Archive SHA256:
`9e7d8b765750fd0579bf1f4719ddaced14dc4c71e1864b0b03852e20f46f6a14`.

| Operation | Concrete scope | Required result / stop |
| --- | --- | --- |
| AR04-L0: enroll temporary lab controls | Exclusively create `/var/lib/hermes-standard-tpm2-20260910` with root-owned source, policy, state and events. Preserve the old source, policy and run journals. Verify the private copied archive against the hash above before extracting only its reviewed regular files. State/events use 0711; source parents 0755. Back up the existing broker JSON privately, require its recorded hash, change only test_uid from 987 to 984, keep production disabled, and add the prepared socket override for hermes-certification. Install the two reviewed power-helper files under `/usr/local/libexec/hermes-lab-power` and the exact no-argument sudoers entry in `/etc/sudoers.d/hermes-standard-tpm2-power`. Validate before activation. | Stop on existing destinations, changed broker baseline, active old campaign, unexpected resources or failed syntax/identity checks. This temporarily changes lab credential and power access; it is not authorized merely by preparing the files. |
| AR04-L1: one fresh lifecycle | Start the isolated broker socket and one temporary `hermes-standard-tpm2-20260910.service`. Mint one root-owned `hermes-lifecycle-lab-window-v1` grant immediately before dispatch, for the proposal's run ID/policy binding and at most four hours. Use only lab-hermes-server / UUID 4db6369a-2b8b-427f-a47a-a5d83bb40cff / 172.16.99.12 / dedicated hermes-tpm-lab pool. Reverify signed Fedora media, generate fresh disposable boot/TPM/recovery/SSH keys, build the baseline and updated UKIs, run the existing certifier with closed stdin, encrypted Restic backups and the isolated test project/model gpt-5.6-luna. | One run only; no automatic retry or reissued grant. The program records archive inspection and actual boot/runtime/replay/scan results separately. No production access, hardware TPM clear, release signing or timer enablement. A failed attempt remains failed. |
| AR04-L2: reconcile and remove temporary controls | Run the existing lifecycle cleanup for that run, including provider revocation, guest purge and removal of its VM/disk/OVMF variables/emulated TPM and private keys. Retain sanitized evidence. Stop broker/service/socket, restore the exact prior broker JSON, remove only the matching temporary override, power grant/helper, service units and grant, then reload unit metadata and verify socket/runtime credential absence. Retain reviewed source and public records. | Cleanup is required after success, failure, interruption or expiry. If revocation/cleanup fails, preserve required recovery state and report the blocker; never claim cleanup or promotion. Restore the original test UID 987 and disabled production role; preserve unrelated privileges and timers. |

The proposed run ID is `3882cd7b48e3d8472f12d73792f7d9afa210bab572352612f1034129e2a08605` and policy binding is
`7c0a629483c42d365745681ddc5c4fc52290f30d2617efd756d2df7c474c65ad`. The approved grant was issued at 16:49:59 UTC
with expiry 20:49:59 UTC; it was removed during L2 at 17:12:52 UTC. Its one-run allowance is consumed. At
preparation, the encrypted broker admin credential was present, root-owned 0600; its contents were not read. Existing
broker/service units are inactive and the domain, dedicated pool, NVRAM and emulated TPM are absent. The retained
previous run remains `failed-cleaned`.

This first cycle is a required integration gate, not all of AR04. Existing automation covers updated-image
cold/warm boots, runtime/credential observation, exact replay, backup/restore, rerun and payload/protocol rejection.
It does **not** establish B3 previous-approved-image boot, B4 separate boot-artifact and unapproved-PCR-policy
rejection, or the complete B7 interruption matrix. Recovery-key disk readback is lab evidence only. After L1/L2,
review those results and prepare fresh, separately bounded fixtures for the uncovered gates; do not label the
existing payload-tamper check as a firmware/TPM rejection test. AR04 and UA-04 signing remain open until the full
amended candidate matrix, cleanup and artifact binding pass. Older grants are unavailable.

## Corrected integration package r2

The first run passed unattended installation and disposable recovery-key disk readback. It failed the
baseline initrd mask assertion before signing or first installed boot. Automatic cleanup reached
failed-cleaned; L2 independently restored the exact original broker bytes/metadata/xattrs and test UID 987,
removed temporary controls, stopped the broker/socket and verified disposable resource/private-key absence.
No provider test credential was issued. The old policy/journal/timers and failed root snapshot are preserved.

The failed archive was not retained, so its precise mask contents are unavailable. A local unprivileged
reproduction using installed dracut 108-8.fc44 showed that all three masks survive installation but are
rewritten to ../../dev/null for NvPCR and ../../../dev/null for the service. This matches
[dracut v108 link conversion](https://raw.githubusercontent.com/dracut-ng/dracut-ng/108/src/install/dracut-install.c).
The checker now accepts only those exact relative equivalents with unambiguous real archive directories.
Missing/duplicate/non-symbolic/wrong targets and redirected parents still fail. Sanitized counts/verdicts
and archive identity are saved before rejection; raw archive listings and arbitrary link targets are not retained.
The reproduced checker defect is corrected locally; a new full guest build/boot must still establish acceptance.

**Historical r2 attempt, now consumed:** L0 passed at 17:56:18 UTC; L1 was dispatched once at 17:56:53 UTC
with expiry 21:56:53 UTC. Preparation passed, certification failed, and L2 restored controls and removed the grant
at 18:38:19 UTC. Do not reexecute this package. The
[r2 live observation](plans/evidence/2026-09-10-hermes-standard-tpm2-r2-live.json) records execution separately
from the retained unissued proposal. This approval cannot cover another attempt.

The approved package is
`/var/home/cloudops/.local/state/hermes-standard-tpm2-campaign/20260910T160319Z/review-package-r2`.
It retains 71 source files; only the two profile/lifecycle runtime files differ from the first snapshot.
The [live observation](plans/evidence/2026-09-10-hermes-standard-tpm2-live.json) records all proposal/control hashes.

| Binding | Exact r2 value |
| --- | --- |
| Source archive SHA256 | 052a2294e22b1f5ca12ccf6fa18bc80fec41ef3e6df74d068e64abe7abcef1ee |
| Policy binding | 6fb4f69cdee32a3331a561345d9776bdbeeab2aa1fbc8979f2dfde8619083da0 |
| New run ID | e2fc5937ad3c02f437df891f0d224e099c3ef2cda49b53436f7d35baba6a7c05 |
| Exclusive root destination | /var/lib/hermes-standard-tpm2-20260910-r2 |
| Lifecycle unit | hermes-standard-tpm2-20260910-r2.service |
| Failure unit | hermes-standard-tpm2-20260910-r2-failed.service |
| Temporary socket override | /etc/systemd/system/hermes-lab-credentials.socket.d/90-hermes-standard-tpm2-20260910-r2.conf |
| Temporary sudoers file | /etc/sudoers.d/hermes-standard-tpm2-r2-power |

The L0/L1/L2 operation bounds above apply with these new paths and identities. L0 must freshly require
absent destinations and fixed VM/disk/NVRAM/swtpm, inactive broker/old campaign, sufficient resources,
root-protected inputs and original broker SHA256 eb5013ab097de85bc0106bb217dc9de62621b6fe17983b28c13d91edec1e5d79.
Back up that broker and change only test UID 987→984 with the matching socket override; production stays disabled.
Install the same reviewed no-argument power helper only under /usr/local/libexec/hermes-lab-power.
L1 may issue one new maximum-four-hour run-bound grant immediately before the explicit service dispatch.
No timestamp/grant is issued during preparation and no automatic retry is allowed. L2 is mandatory on every
outcome, with the same provider reconciliation, guest cleanup, original-control restoration and verification.
Preserve the first root snapshot and journals. Do not update its source/policy or reset its consumed allowance.

Local profile/lifecycle correction tests and packaged dracut/archive readback pass; exact final check results
are recorded in the live observation. Previous-image boot, boot-artifact/PCR11 rejection, the complete
interruption matrix and production P2–P4 remain required even if the next integration run succeeds.

## Certifier tool configuration package r3

R2 passed unattended installation and lab recovery-key readback, first signed-UKI boot with the expected
command line and Secure Boot, boot-manager observation with Enforcing/SRK/profile checks, canary runtime setup,
verified stored-package replay and baseline restoration. Baseline and updated initrd checks both passed.
The updated 7.2.4-200.fc44.x86_64 image was built and the exact candidate enrolled; full candidate certification
then failed before provider credential issuance. This does not establish B2 booting that new UKI or any full gate.
All disposable resources and temporary controls were removed, original broker state restored, and both failed
root snapshots retained. Its disk and disposable TPM/keys were purged, so r2 cannot be resumed as a boot fixture.
R2's one-run allowance is consumed; its recorded expiry is not remaining authorization.

The retained error is required-command-unavailable. The scheduler intentionally constructs a sanitized child PATH;
its optional root-owned bin beside schedule.py was absent in r2. Neither Restic nor Trivy exists in the remaining
standard search directories. The actual UID 984 read-only reproduction confirms Restic launch fails with ENOENT.
This is a concrete controller-tool dependency, separate from application TPM/NvPCR requirements. The exact original
failed executable/stage was not retained; missing child Restic is the supported explanation, not a new boot failure.
No package, TPM policy or SELinux permission change is justified by that launch error.

The local correction shares one child-environment function between dispatch and a pre-allocation check under the
actual certifier UID. It requires SSH, sudo, Restic and Trivy to resolve as executable files in that environment;
caller PATH is not inherited. A failed check stops before broker access, private-key generation or VM allocation.
The certifier now retains only an allowlisted prior stage on failure, without command arguments or output.

**Historical r3 integration, now consumed:** L0 passed at 2026-09-11T01:58:49Z; the single L1 run began
at 01:59:12Z and passed all seven existing certifier gates. L2 and independent restoration passed at
03:01:21Z, with the grant removed before its 05:59:12Z expiry. Do not reexecute this package. See the
[r3 live observation](plans/evidence/2026-09-11-hermes-standard-tpm2-r3-live.json). Its immutable preparation
proposal remains historical; the separate approval and dispatch record establish authorization. The package is
`/var/home/cloudops/.local/state/hermes-standard-tpm2-campaign/20260910T160319Z/review-package-r3`.
It freezes 71 repository sources plus two regular executable tool files. Only schedule.py, lifecycle_fixture.py
and certify.py differ from r2's repository snapshot. The profile renderer/checker, installer and TPM settings are
unchanged. Existing Restic and the reviewed bounded Trivy launcher are copied byte-for-byte into
repository/scripts/hermes/unattended/bin; the child environment keeps its existing trust checks.

| Binding | Exact r3 value |
| --- | --- |
| Source archive SHA256 | 7101a25a928ad3d5665a652c880962637251f0ca7b02ba53c880f4be0158300e |
| Policy binding | d0bb04d7513ebd77750fb94f8831bc85cc14486191569d31e95282188919354a |
| New run ID | 67ccc802152b9b7a8f500435a7d5e67429755be276b3e924bda581c79685f032 |
| Exclusive root destination | /var/lib/hermes-standard-tpm2-20260910-r3 |
| Lifecycle/failure units | hermes-standard-tpm2-20260910-r3.service / hermes-standard-tpm2-20260910-r3-failed.service |
| Temporary socket override | /etc/systemd/system/hermes-lab-credentials.socket.d/90-hermes-standard-tpm2-20260910-r3.conf |
| Temporary sudoers file | /etc/sudoers.d/hermes-standard-tpm2-r3-power |
| Adjacent Restic file SHA256, mode 0755 | 488bee64dd71077d7153474b3581fd449b7fa74a182d5f0dcfcf8f4d8a76db03 |
| Adjacent Trivy launcher SHA256, mode 0755 | 57101ba2565dec2dbd70ec056d39a81facd2ea9cf69d1a8af137391069f2f3ec |

The [r2 live observation](plans/evidence/2026-09-10-hermes-standard-tpm2-r2-live.json) includes every r3 control
hash, exact tool origin and pinned Trivy binary. Restic 0.19.1 and Trivy 0.74.0 store objects pass nix-store
verification; copied tool version probes pass with a sanitized PATH. The Nix store's managed 1775 parent is
unchanged; frozen byte hashes and verified immutable package objects bind the copied tools. L0 verified the
installed adjacent bin is root-owned 0755 with protected parents. The original tool installation is preserved.

The prior L0/L1/L2 bounds apply with these r3 identities. L0 must exclusively install all 73 verified regular
archive members and the exact controls, recheck original broker hash/UID and absent fixed resources, and preserve
both consumed snapshots/policies/journals. Before L1, check the new child environment and both tool versions under
UID 984, including availability of their pinned Nix objects; stop on drift or failed discovery/execution. This is
part of the concrete L0 review, not permission to alter Nix/store/SELinux permissions. The temporary broker/socket
and no-argument fixed-domain power scope is unchanged. L1 may mint one fresh grant of at most four hours immediately
before a single dispatch. No retry/reissue, timer enablement, release signing or production operation is included.
L2 must reconcile credentials/guest cleanup, archive the parent grant and derived candidate-window.json privately
after validating their run/candidate/scheduler bindings and time interval, remove both active-path copies and
matching temporary access controls, restore exact broker bytes/metadata/xattrs and UID 987, verify
fixed-resource/runtime-credential absence, and retain public evidence
and reviewed source. If cleanup fails, retain needed recovery state and report it; do not claim certification.

Local scheduler/lifecycle/certifier tests pass 114/114; archive/control and copied-tool checks pass. Root ownership
and actual UID 984 discovery/version probes passed L0. R2 preparation evidence is valid only for its
frozen artifacts; changing orchestration requires fresh complete candidate certification. B3 previous-approved-image
boot, B4 boot-artifact/PCR11 rejection, full B7 interruption coverage and AR05/P2–P4 remain required separately.
No further consumer inventory or repeated SE22 diagnostics are requested.

## Remaining lab gate specification after r3

R3's seven existing certifier gates and L2/independent restoration passed; its grant is consumed. The
[r3 observation](plans/evidence/2026-09-11-hermes-standard-tpm2-r3-live.json) retains exact warm/cold boot,
credential, recovery, scan and restore evidence. The destroyed fixture cannot be resumed or promoted as a
production identity. The following specifies the remaining campaign; it is not a new operational approval.

| Gate | Required experiment and evidence | Stop or acceptance condition |
| --- | --- | --- |
| B3 and previous-image B6 | In a fresh approved fixture, complete the update first, retain both approved signed images and their module trees, select the previous image once, and cold boot without input. Record selected image/hash, kernel/modules, new boot ID, Secure Boot, Enforcing, both SRK services, Hermes/inference and credential availability/protection. Then boot the new approved image again. | Both images must work without reenrollment. A baseline restore before certification or the mere presence of previous.efi does not satisfy this gate. |
| B4 and untrusted-boot B6 | Use separate disposable copies for kernel, initramfs and embedded-command-line tampering; also a firmware-trusted UKI lacking an approved PCR11 signature, and an external command-line override. Preserve the trusted control image and recovery route. Record exact tested hashes and firmware/TPM/runtime outcomes without supplying recovery input to the negative boot. | Tampered images must be rejected by signature validation; a trusted but unapproved PCR11 image must not obtain automatic disk/credential access; an external override must not alter the protected intended command line. Demonstrate successful control boot after each rejection. Do not substitute payload-hash rejection or a generic boot timeout. |
| B7 interrupted publication | Interrupt before copy, during temporary-file copy and before final atomic publication/boot selection. Record ESP contents/hashes, selected default, replay journal and both complete approved images. | No partial artifact is selected; rerun preserves complete existing configuration and recovery paths. Verify each interruption independently. |
| B7 interrupted replay/selection | Interrupt package replay and the boundary between successful replay and boot selection. Compare the signed transaction, package inventory, journal, kernel/modules and boot IDs; exercise documented explicit recovery when completion is uncertain. | No false completion or routine unattended prompt. The previous approved image must remain usable with matching modules, and a clean rerun must not replay completed work incorrectly. |
| B7 notifications and closure | Trigger the campaign's approved failure/maintenance notification cases and verify actual delivery, then revoke credentials, purge guest/private state and independently restore temporary controls on every branch. | A local journal event alone is not external delivery proof. Any unresolved revocation, leaked grant or remaining fixture blocks closure. |

Preparation must bind a fresh source/policy/run identity and fixed disposable resources, define a maximum duration
and one dispatch limit for each approved block, and include exact cleanup/recovery commands before requesting
operation approval. Use the current controller and protected signing path; no trust-policy or SELinux permission
expansion is implied. Retain r3's valid evidence for unchanged artifacts, and mark affected results stale when a
new implementation, image, transaction or fixture identity changes their binding. No production operation follows
until the full matrix and ordered release/hardware gates pass.

The [remaining lab runbook](HERMES_REMAINING_LAB_TESTS.md) now provides the concrete local preparation,
B3 implementation, separate B4/B7 cases, per-case limits and exact control cleanup. The separately approved
B3 L0/L1/L2 block passed on September 11. [B3 live evidence](plans/evidence/2026-09-11-hermes-b3-live.json)
records the completed update → previous approved image → updated image sequence, all eight certifier gates,
and independent cleanup/restoration at 18:00:17Z within four hours. Packages, both module trees, credential
bytes, public PCR key and LUKS metadata were preserved across three distinct boots, without reenrollment.
This closes B3 for that lab candidate only. The user subsequently authorized all pending tasks; `b4-linux`
failed during prerequisite certification, before tampering. Independent cleanup passed at 22:14:22Z within
four hours. Later B4/B7 blocks remain blocked and unissued. The
[continuation evidence](plans/evidence/2026-09-11-hermes-remaining-continuation.json) records execution.
The user subsequently authorized bounded replacement runs without further lab approval prompts.
Corrected r5 passed seven gates, then failed initial provider revocation. Cleanup subsequently confirmed
revocation; independent restoration passed on September 12 at 00:04:12Z, within four hours. No tamper test ran.
A bounded revocation correction and fresh replacement are being prepared under the same standing authorization.
That correction passed offline checks; r6 passed L0 and dispatched once on September 12 at 00:12:21Z.
All eight prerequisites passed; the trial copy then filled the 600-MiB EFI partition before any negative
boot. Recovery and independent cleanup passed at 01:26:22Z within four hours. The next fresh fixture
uses 2048 MiB and pre-copy capacity checks; B4 acceptance remains pending.
R7 failed before installation and independent L2 passed at 01:32:13Z. R8 is prepared but undispatched;
current RAM is below the unchanged 9-GiB minimum. The canonical execution record owns the throughput revision.
Each fresh run still requires its own recorded grant and verified cleanup before dependent work.
Both B3 and r3 dispatch allowances are consumed; production deployment remains the approval boundary.

## Production operation preparation

AR01 bounded consumer review is complete. AR05 remains blocked on AR04 and the concrete production gates. The ordered
production blocks are the existing [migration steps](#migration-preparation-and-approval-sequence): fresh protected
recovery/configuration backup; four-path configuration installation and a new versioned initrd build; controller
signing/staging of exact new and previous-approved images; one-shot selection/boot with console recovery; additive
TPM enrollment and new-token-only verification; separately approved legacy-slot retirement if justified; B1–B7/P2
acceptance; then P3 restricted identities/credential enrollment and production-bound release, followed by P4
deployment and restore/rerun acceptance. Normal timer enablement is a separate approval.

Image hashes, new token/slot IDs and fresh backup identity do not exist yet and must not be guessed. Produce
those reviewable artifacts at their ordered gates before requesting the corresponding production operation.
The current prepared image, old TPM slot, anchors, v2 policy and v3 sources remain preserved. No blanket slot
wipe, setup-service mask, SELinux permission expansion or routine manual reenrollment is part of this proposal.
