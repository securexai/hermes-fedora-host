# Remaining Hermes lab tests: B3, B4 and B7

Prepared 2026-09-11. **B3 L0/L1/L2 passed on September 11; its approval is consumed.**
The single block finished with independent cleanup at 18:00:17Z, within four hours.
[B3 live evidence](plans/evidence/2026-09-11-hermes-b3-live.json) records the three-boot round trip, all eight
certifier gates and exact restoration. The user subsequently authorized all pending B4/B7 blocks on September 11.
B4-linux failed during prerequisite certification, before tampering; its allowance is consumed. Independent
cleanup passed at 22:14:22Z within four hours. Later blocks remain blocked and unissued.
The [continuation evidence](plans/evidence/2026-09-11-hermes-remaining-continuation.json) records their status.
R3's grant is also consumed.
This is an operator-run package. The
[canonical execution record](plans/2026-09-07-hermes-unattended.md#remaining-lab-preparation-amendment--2026-09-11)
tracks preparation and validation; this document owns the procedures. Actual observations will be separate.
The [dependency review](HERMES_TPM_DEPENDENCY_REVIEW.md#acceptance-gates) owns B1–B7 acceptance.

## B4-linux replacement prepared after the failed run

The [failed-run evidence](plans/evidence/2026-09-11-hermes-b4-linux-live.json) records successful recovery and
cleanup after an early `reboot-pending` certification failure. The original SSH exit code was not retained;
a matching transport-handling gap was reproduced locally and corrected. Exact positive pending-reboot replies
for the enrolled release may be retried after SSH exit 255/143 only through the existing acknowledged-stage
and deadline guard. Guest errors, malformed/unbound replies and unrelated operations remain terminal.
Only fixed transport metadata is retained on failure; no response body or credential is logged.

A single replacement **b4-linux** package is prepared at
`/var/home/cloudops/.local/state/hermes-remaining-lab/20260911-b4-linux-review-r5`.
Its manifest SHA256 is `d43397263837c24e8a3ea1085af55d5cd79a6d8dbce997ac3a027c09856bbd5c`;
source archive SHA256 is `28d10ed215410166143f81053267b9686c4e053b57334a71bf9ba70108a36d44`.
Run ID: `6fc9af8163e7b1e96e703b5e8adfcf2f8cb33bb62ca7c5b14b94d05eeedacc9e`.
It preserves the four-hour L0/L1/L2 bound and adds exact preservation checks for completed B3 and failed r4.
Local verification passes 103 package files, 79 archived sources and four missing-approval refusals.
The only changed runtime source is `certify.py`; preparation itself performed no enrollment or dispatch.

The user subsequently authorized continued lab corrections and fresh bounded runs without further approval
prompts until production deployment. R5 B4-linux passed L0 and dispatched once at 22:58:24Z. Each replacement
uses a new run identity and grant; consumed grants stay consumed. Other blocks remain dependent on its PASS
and independent cleanup. Refresh their source snapshots for the correction before any later execution.
The original r4 package below is retained unchanged as historical preparation and evidence.
R5 later passed seven prerequisite gates, then failed initial provider revocation. Its cleanup retry confirmed
revocation and independent restoration passed on September 12 at 00:04:12Z, within four hours. No tamper
probe ran. A bounded retry of the same idempotent revocation request is being validated before a fresh
replacement. The broker still requires actual key rejection; failed attempts never become certification PASS.
The correction passed offline checks. Fresh r6 passed L0 and dispatched once on September 12 at 00:12:21Z,
with mandatory cleanup by 04:11:43Z. Its package is
`/var/home/cloudops/.local/state/hermes-remaining-lab/20260912-b4-linux-review-r6`; exact identities are in
the canonical execution record. The current lab acceptance remains pending.
R6 passed all eight prerequisite gates, then failed trial preparation because its 600-MiB EFI partition
filled during the copy. No negative boot occurred. Exact partial-file recovery passed; independent cleanup passed at 01:26:22Z,
within four hours. Future fresh fixtures use a 2048-MiB EFI partition, and operators check available space before
copying trial images. B4 acceptance remains pending; the failed attempt and its source stay preserved in
[R6 live evidence](plans/evidence/2026-09-12-hermes-b4-linux-r6-live.json).

## Preparation queue and evidence reuse

Run [remaining-lab-preflight.py](../scripts/remaining-lab-preflight.py) before freezing a package:

```bash
devbox run -- python3 scripts/remaining-lab-preflight.py \
  --operators "$OPERATORS" --templates "$TEMPLATES" \
  --source-manifest "$SOURCE_MANIFEST" --output "$NEW_REPORT"
devbox run -- python3 scripts/remaining-lab-preflight.py \
  --verify "$NEW_REPORT" --case b4-linux
```

Use the recorded private operator/template locations; output must be a new file. The inventory checks
all 13 cases' scripts, cleanup controls, service time limits, file ownership/modes and host tool hashes.
It records current RAM, noninteractive sudo access and absence of libvirt domains without modifying them.
Syntax is not semantic acceptance. Guest tools, pinned SSH/root permissions, actual free EFI capacity,
case witnesses and cleanup must still pass their live gates. Notification delivery needs actual visible receipt.

Prepare and review later operators while a fixture runs. Reuse matching per-case preparation inputs and
unchanged offline test evidence; a changed input or failed gate invalidates the affected evidence. Always
repeat live L0/resource checks. Finalize each fresh run identity, keys, grant and predecessor history only
when the previous required case and independent cleanup pass. Never reuse live candidate-bound evidence
for a different run. The prepared package builder rejects stale per-case preparation reports before writing.
Current host resources do not support parallel 8-GiB fixtures; clean enrolled disks are not reusable templates.

## Package and approval units

The frozen local package is
`/var/home/cloudops/.local/state/hermes-remaining-lab/20260911-review-r4`.
Its `manifest.json` binds every prepared file; `cases.json` contains the exact independent run IDs,
policy hashes, root directories, units and cleanup destinations. The repository
[preparation observation](plans/evidence/2026-09-11-hermes-remaining-lab-preparation.json) records its hashes.
Image, initrd, credential-envelope, transaction and machine identities are created in the freshly approved
fixture. Record them before each experiment; never substitute r3's image or machine hashes.

Each row is a separate **one-dispatch** approval unit and a fresh complete fixture. Install only one row's
controls at a time. The fixed disposable resources can be reused only after the previous row's independently
verified cleanup. No grant is included in the prepared package. The `approval-template.json` is inert;
an `approval.json` may record a new user approval only after it actually arrives, with its reference,
case and package manifest hash. The file is not itself a source of user authorization.

| Order / block | Experiment | Prerequisite | Maximum time including cleanup |
| --- | --- | --- | --- |
| 1 / `b3` | Completed update → previous approved image → updated image; full acceptance and cleanup | Fresh approval of this block | 4 hours |
| 2 / `b4-linux` | Unsigned modification of `.linux` | B3 PASS | 4 hours |
| 3 / `b4-initrd` | Unsigned modification of `.initrd` | Prior required block PASS | 4 hours |
| 4 / `b4-cmdline` | Unsigned modification of embedded `.cmdline` | Prior required block PASS | 4 hours |
| 5 / `b4-pcr11` | Trusted firmware signature, unapproved PCR11 authority; paired initrd canary | Prior required block PASS | 4 hours |
| 6 / `b4-external` | External EFI command-line override | Prior required block PASS | 4 hours |
| 7 / `b4-credential` | Unauthorized account and wrong PCR-signature credential access | Prior required block PASS | 4 hours |
| 8 / `b7-before-copy` | Interrupt before temporary UKI creation | B4 matrix PASS | 4 hours |
| 9 / `b7-during-copy` | Interrupt after an actual partial temporary write/fsync | Prior required block PASS | 4 hours |
| 10 / `b7-before-publish` | Interrupt after full temporary-file fsync, before rename | Prior required block PASS | 4 hours |
| 11 / `b7-during-replay` | Interrupt a live DNF replay after observed inventory mutation | Prior required block PASS | 4 hours |
| 12 / `b7-before-select` | Interrupt verified replay before boot selection | Prior required block PASS | 4 hours |
| 13 / `b7-after-select` | Interrupt after selection, before completion journal | Prior required block PASS | 4 hours |
| 14 / `b7-notifications` | Maintenance/failure delivery, deduplication, deferral and failed transport | B7 fault matrix PASS | 4 hours |

The thirteen remaining authorized rows have a combined 52-hour upper bound and execute serially.
B3 and B4-linux passed with independent cleanup; B4-initrd is active. Earlier failed attempts remain recorded.
Failure stops dependent rows. A timeout is FAIL or BLOCKED,
never rejection evidence. Each row allows one deliberate fault, one bounded control recovery, and one clean
replay where specified; no fresh lifecycle retry, new grant, automatic reboot loop or repeated injection.

Budget per row: L0 installation ≤10 minutes; L1 preparation and experiments ≤170 minutes; mandatory fixture
cleanup ≤50 minutes; control restoration and independent checks ≤10 minutes. Services enforce
`TimeoutStartSec=170min`, `TimeoutStopSec=50min`, `KillMode=control-group`, closed stdin and no restart.
The grant expires after 10,200 seconds. Cleanup does not require an unexpired grant. Stop experiments when
L1 ends; exhaustion of cleanup time leaves closure BLOCKED with recovery material retained.

Individual limits: approved SSH/boot observation ≤600 seconds per boot; controlled shutdown ≤180 seconds
plus a bounded power call; negative boot ≤180 seconds; canary probe ≤30 seconds; inference ≤120 seconds;
DNF mutation checkpoint ≤120 seconds plus one bounded inventory query; offline replay service ≤25 minutes;
desktop send ≤15 seconds. The outer service deadline applies even if an inner command is slower.

## L0: immutable enrollment and preflight

The exact L0/L1/L2 scripts are in each package `blocks/<case>/` directory. They are prepared source, not
previously executed operations. Before invoking any privileged script, verify its package hash and the
fresh approval record. Use the [local hypervisor exception](VM_TESTING_GUIDE.md) for these lifecycle commands.
Do not change the ordinary scheduler timers or use production credentials.

```bash
packet=/var/home/cloudops/.local/state/hermes-remaining-lab/20260911-review-r4
block="$packet/blocks/b3"
devbox run -- python3 "$packet/verify-package.py"
# Only after the fresh b3 approval has been recorded:
sudo timeout --kill-after=10s 10m /usr/bin/python3 "$block/install-controls.py"
sudo timeout --kill-after=10s 60s /usr/bin/python3 "$block/dispatch.py"
```

L0 requires the fixed domain `lab-hermes-server`, UUID `4db6369a-2b8b-427f-a47a-a5d83bb40cff`, disk pool
`/var/lib/libvirt/images/hermes-tpm-lab`, NVRAM
`/var/lib/libvirt/qemu/nvram/lab-hermes-server_VARS.fd` and
`/var/lib/libvirt/swtpm/4db6369a-2b8b-427f-a47a-a5d83bb40cff` all absent. Target is `172.16.99.12`;
root operation SSH is the fixture's pinned `lab` account, distinct from production `aicowork`.

Require ≥2 CPUs, ≥9 GiB available RAM and ≥60 GiB free storage; signed Fedora media; protected tool/source
paths; actual UID 984 Restic/Trivy discovery/version checks; broker UID 987 and its recorded hash; production
broker role disabled. Reverify the original r1/r2/r3 source, journal, policy and consumed-grant state.
Back up exact broker bytes, owner, group, mode and xattrs before changing only its test UID to 984.
Install only exclusive, hash-checked per-case units, socket override, fixed-domain power helper and no-argument
sudo rule. L0 starts no service and issues no grant. Do not repair unrelated privileges or trust policy.

L1 exclusively creates one run-bound grant and dispatches once. The existing fixture driver generates fresh
Secure Boot/PCR, SSH, recovery and backup identities; verifies media and initrds; freezes the transaction and
candidate; reconstructs the root-approved candidate independently. Reused image names do not imply reused bytes.
No signing key is copied into the guest. No production release is signed.

## B3: previous approved image after the update

This row uses the current lifecycle and certifier with the added
[previous-image checks](../scripts/hermes/unattended/lab_previous.py). It runs without operator intervention
once approved. It does not restore the baseline disk before the previous-image experiment.

1. At the initial candidate staging boundary, bind `hermes-enrollment.efi` to the existing root-owned boot
   enrollment record; verify its Secure Boot signature and that it is the running baseline entry. Record
   its kernel and a content/mode/link fingerprint of its complete module tree, including `modules.dep`.
2. Perform the original encrypted backup, disposable test-key issuance, exact stored update, persistence
   reboot, runtime and cold-boot acceptance. Require the original updated-image gates.
3. Require the host journal `closed` and the updated default. Recheck the previous image/module fingerprints.
   Use `bootctl --esp-path=/boot/efi set-oneshot hermes-enrollment.efi`; shut down, observe powered-off state,
   start with closed stdin, and independently observe the previous image.
4. Require its selected entry/hash, previous kernel and modules, unchanged **post-update** RPM inventory,
   Secure Boot, Enforcing, both SRK setup observations, active credential service, protected encrypted file,
   correct read-only runtime credential, bounded leak checks and exact Hermes `HERMES_OK` inference.
5. Select the new candidate once and repeat cold boot/inference. Require three distinct boot IDs; the first
   and third image/kernel must match, and the previous image/kernel must differ. Preserve both module trees,
   encrypted credential bytes, public PCR key and LUKS metadata across all three observations. No resealing,
   token/slot changes, TPM reset, automatic fallback input or reenrollment can satisfy B3.
6. Complete the existing restore, scan, revocation and cleanup gates. Require `previous_boot.json` in the
   certifier evidence and root `acceptance.json`, bound to this run/candidate, in addition to all seven
   original gates. L2 and independent restoration are required before B3 closes.

If the previous image fails, stop the acceptance path. The updated persistent default and operator recovery
path remain available for bounded cleanup. Use the L2 procedure; do not rebuild or overwrite the previous image
and call it the same test. New observer/controller sources invalidate r3 evidence for this new run, while r3's
original evidence remains valid for its frozen inputs.

## Operator sessions for B4 and B7

The other rows use [lab_session.py](../scripts/hermes/unattended/lab_session.py) inside the same bounded service.
B4 and notification rows first run complete updated/B3 certification. Fault rows instead use
[lab_stage.py](../scripts/hermes/unattended/lab_stage.py) to stage the exact candidate, encrypted verified
backup and a public synthetic credential. They issue no provider lease or synthetic-key API request.

Wait for the run's `operator-ready.json`; record its candidate and deadline. An absent marker is not permission
to execute a probe. B7 publication work must start within 10 minutes of this marker and before the existing
20-minute backup guard; if the guard has restored state, stop the case. Its normal timer is preserved.

Use this root Python context in the approved workstation operation, with values read from that row's
`case.json` and `policy.json`, not typed from a different run:

```python
import json, sys
from pathlib import Path
case = json.loads(Path(block, 'case.json').read_text())
proposal = json.loads(Path(block, 'operation-proposal.json').read_text())
root = Path(proposal['root_destination'])
sys.path.insert(0, str(root / 'repository/scripts/hermes/unattended'))
from common import atomic, canonical, decode, run, require
from lifecycle import load
from lifecycle_fixture import Fixture
policy = load(root / 'policy.json')
directory = root / 'state' / case['run_id']
state = decode((directory / 'lifecycle.json').read_bytes())
require(state['run_id'] == case['run_id'], 'wrong-operator-run')
require((directory / 'operator-ready.json').is_file(), 'operator-session-not-ready')
fixture = Fixture(policy, directory, state, lambda **values: None)
fixture.check_owned()
```

`fixture.ssh()` is the pinned lab operator transport; `fixture.poweroff()`, `fixture.wait_ssh()` and
`fixture.guestfish()` are existing fixed-domain primitives. Never reconstruct SSH with host-key checking disabled.
For example, invoke the public preservation probe through the existing authorized lab root path:

```python
import shlex
command = ('exec /usr/bin/python3 -I -B /usr/local/libexec/hermes-lab-certifier/lab_faults.py '
           'snapshot --run-id ' + case['run_id'])
before = decode(run(fixture.ssh() + ['sudo -n /usr/bin/bash -c ' + shlex.quote(command)], timeout=180))
atomic(directory / 'case-before.json', canonical(before))
```

The `snapshot` result hashes configuration, metadata and xattrs without printing file contents. It records
ESP entries, package inventory, journals, old modules, LUKS metadata, profile masks, public SRK and identity.
Add before/after fingerprints for any case-specific file before creating it; record every added path exactly.
Preserve the original encrypted backup and recovery key until reconciliation succeeds.

At the end, write an exclusive root-owned `operator-result.json` containing exactly `case`, `run_id`,
`candidate_sha256`, `result` (`PASS`, `FAIL` or `BLOCKED`), and the SHA256 of the reviewed public evidence bundle.
The session detects it, ends the experiment and cleans up. Its lifecycle is deliberately `failed-cleaned`,
`certified=false`: a supplemental experiment result cannot fabricate full certification. Missing/rejected result
or timeout also triggers cleanup. The case result and cleanup result are separate gates.

## B4: boot artifact rejection

Use one fresh row for each section. In the root operator context, create a case-private working directory under
`fixture.private`, preserving all approved images. Generate exactly one modified copy from `updated.efi`:

```python
from lab_faults import mutate
trial = fixture.private / (case['case'] + '.efi')
section = {'b4-linux': '.linux', 'b4-initrd': '.initrd', 'b4-cmdline': '.cmdline'}[case['case']]
record = mutate(fixture.private / 'updated.efi', trial, section)
atomic(directory / 'tamper.json', canonical(record))
```

The helper changes one byte in the selected PE section and preserves the control image and existing signature.
Require `sbverify --cert <this-fixture-sb.crt> <control>` success and the same verifier's signature rejection for
`trial`; missing tools, a malformed PE or missing section are fixture failures, not trust rejection.
Before creating or copying the trial, require free space on `/boot/efi` of at least the intact UKI size
plus 1 MiB; record available and required bytes. An insufficient fixture leaves the case failed/blocked
before the copy. Fresh disposable Server fixtures reserve 2048 MiB for the EFI partition.
Power off and upload the trial through `fixture.guestfish` to
`/boot/efi/EFI/Linux/hermes-<case>-<run-id-first-12>.efi`; read back its hash. Restart the approved control,
record current/default entries, select only that trial with `bootctl set-oneshot`, then cold boot without input.

Observe at most 180 seconds. Record the selected requested path/hash and explicit firmware/boot-manager
signature or security-violation evidence from the VM screen or a bounded boot-console capture. Capture only
firmware/boot output, never a provider terminal. A control fallback or SSH timeout by itself cannot pass.
If no explicit rejection is observable, mark BLOCKED/FAIL and retain the exact artifact hashes for review.
Power off if necessary, boot the intact approved control once and recheck selected image, Secure Boot,
Enforcing, retained modules, credential service and protected credential. Delete only the exact trial entry/file
whose recorded hash matches, or let fixture destruction remove it. Do not overwrite either approved image.

## B4: unapproved PCR11 and credential denial

A Secure Boot signature and a signed PCR11 policy are separate controls. The
[systemd 259 stub specification](https://github.com/systemd/systemd/blob/v259/man/systemd-stub.xml)
describes measured UKI sections and the embedded PCR signature/public-key handoff. The
[credential specification](https://github.com/systemd/systemd/blob/v259/man/systemd-creds.xml)
defines the signed-PCR credential policy. Verify actual behavior; documentation is not lab evidence.

For `b4-pcr11`, build **paired probe images** in this fresh fixture, using the current controller's
`boot_build.build` and this fixture's protected signing keys. Preserve both original approved images.

1. In the trusted running guest, create a **public synthetic** canary with
   `systemd-creds encrypt --name=b4-canary --with-key=tpm2 --tpm2-pcrs=7
   --tpm2-public-key=/etc/systemd/tpm2-pcr-public-key.pem --tpm2-public-key-pcrs=11 - <new-private-canary-path>`.
   Feed `hermes-public-b4-canary-<run-id>` over stdin. It is deliberately a TPM-only canary; actual runtime
   credentials remain host+TPM sealed and are never exported or embedded in an initrd.
2. Build a new versioned initrd with the installed kernel, the current standard profile and the prepared
   [probe script](../scripts/hermes/unattended/lab-probes/b4-credential-probe.sh) and
   [unit](../scripts/hermes/unattended/lab-probes/hermes-b4-credential-probe.service). The staging tree contains
   `/hermes-lab-b4/{probe.sh,run-id,canary.cred}`, the unit in `/etc/systemd/system/`, and its
   `initrd.target.wants` symlink. Use `dracut --force --install '/usr/bin/systemd-creds /bin/sh /usr/bin/cat'
   --include <new-private-staging-tree> / <new-private-initrd> <recorded-updated-kernel>`.
   The probe reads only the canary, sends plaintext to `/dev/null`, uses the embedded `.pcrsig`, and emits one
   fixed result marker with the run ID. Check the actual archive includes the probe, canary, unit, TPM support
   and exact profile masks. An absent/non-running probe fails the experiment.
3. Export that public initrd and the unchanged kernel/osrel/cmdline into `fixture.private`, check hashes, then
   build the approved probe control using `fixture.private/sb.key`, `sb.crt`, `pcr.key`, `pcr.pub` and the same
   `boot_build.toolchain()` stub as the existing fixture. Cold boot it and require
   `HERMES_B4_CREDENTIAL_ALLOWED run=<run-id>`, automatic root unlock, Enforcing and a healthy control.
4. Generate a new disposable PCR private/public key pair only in `fixture.private`; do not enroll it. Build
   the second image from the same kernel/initrd/cmdline with the **same Secure Boot key** and this unapproved
   PCR key. Record both public-key hashes, image/section hashes and successful Secure Boot verification.
   Its structurally valid PCR signatures must be from the unapproved authority. No enrolled PCR key, token,
   firmware db, anchor, SRK, disk keyslot or actual host credential is changed.
5. Select this image once and cold boot without any recovery input. Require its matching
   `HERMES_B4_CREDENTIAL_DENIED` marker, an observed PCR-policy unseal failure, and no automatic root unlock,
   Hermes runtime or actual credential delivery. A missing marker, parser/tool/device error, or merely an
   unreachable SSH endpoint cannot pass. Preserve a bounded, sanitized explanation of the cryptographic
   failure; do not copy token blobs or credential contents.
6. Boot the identical approved probe control again. Require the ALLOWED marker and automatic root/runtime
   recovery. Then return to the original updated image and recheck the configuration/key/token baseline.

The canary proves direct TPM signed-PCR denial in the negative boot. Actual host+TPM credential unavailability
also depends on the observed locked root. Record these as distinct facts, not as a claim that a production
credential was decrypted in the negative environment. A successful unauthorized unseal is FAIL even if other
boot steps happen to fail. No `guestfish` recovery unlock is allowed while the negative boot is running.

For `b4-credential`, use a separate fresh trusted fixture. Prove that an unrelated guest user (`nobody`) cannot
open the encrypted credential or volatile provider file, attempting `os.open(..., os.O_RDONLY)` and discarding
all data; only `PermissionError` is expected. An absent path or account is an invalid test. Verify the intended
runtime still reads the correct read-only overlay. Also generate a valid unapproved PCR signature as above,
export only its public `.pcrsig` with `objcopy --dump-section`, and attempt `systemd-creds decrypt
--name=openai-api --tpm2-signature=<unapproved-signature-json> <encrypted-runtime-credential> /dev/null`.
Require cryptographic rejection, not JSON parse failure, followed by successful decrypt to `/dev/null` with the
original approved signature. Inspect errors privately, emit only an allowlisted outcome and hashes, and never
print plaintext or provider configuration.

## B4: external command-line override

For `b4-external`, keep the UKI bytes unchanged. Create one exclusive Type #1 loader entry
`/boot/efi/loader/entries/hermes-b4-external-<run-id-first-12>.conf` with exactly:

```text
title Hermes external command-line rejection test
efi /EFI/Linux/hermes-<this-candidate-release-id>.efi
options hermes_lab_override=<this-run-id>
```

Resolve the candidate release ID from the root-approved manifest and validate the file/hash before selection.
Select that `.conf` entry once, cold boot, and inspect the resulting `/proc/cmdline`. Its command line must equal
the approved embedded command line, with the attempted marker absent; verify Secure Boot, Enforcing, protected
root options, credential service and unchanged UKI hash. The
[stub specification](https://github.com/systemd/systemd/blob/v259/man/systemd-stub.xml) documents ignoring EFI
invocation overrides when Secure Boot and embedded `.cmdline` are present. This safe marker tests that boundary;
it does not disable SELinux or encryption. The regular observer's selected-entry check intentionally expects a
Type #2 entry, so record this Type #1 selection separately rather than weakening the observer. Remove only the
matching test `.conf`, return to the approved Type #2 entry and run its ordinary control observation.

## B7: preparation and preservation baseline

Each fault uses a fresh `lab_stage.py` candidate with a verified encrypted semantic backup and synthetic canary.
The backup quiesces Hermes. Before taking the case baseline, use the guest root operator path to restart
`hermes-runtime-credentials.service`, start `user@<actual-hermes-uid>.service`, then restart the Hermes user
service and require `host.wait_health(manifest['image'])`. This materializes the public canary without inference
or an API request. Require the host journal still `credential-ready`; a fired backup guard invalidates staging.
Keep the candidate immutable. Record `case-before.json`, both complete UKI hashes, module fingerprints,
configuration bytes/metadata/xattrs, public key/SRK/identity hashes, loader state, signed transaction identity,
RPM inventory, host journal and replay journal (or absence). Profile rerenders must preserve unrelated files;
verify all four standard-profile paths, not just the service mask.

Before the fault, shut down and make **one full cold disk copy** at
`fixture.private/case-before.qcow2` using `qemu-img convert -f qcow2 -O qcow2`, followed by `qemu-img check` and
`qemu-img compare`. Record its hash and fixed-resource ownership. The private directory is automatically purged
by L2. Keep the existing TPM/NVRAM; never reuse another run's snapshot, restore an old TPM, reset counters,
reenroll or remove a journal to make an uncertain transaction appear new. Resume the original approved baseline.

## B7: interrupted publication

Run the exact probe below through `fixture.ssh()` and the root operator shell, using this row's point:

```text
/usr/bin/python3 -I -B /usr/local/libexec/hermes-lab-certifier/lab_faults.py publish-fault
  --run-id <this-run-id> --point before-copy|during-copy|before-publish
  --evidence /var/lib/hermes-lab-certification/fault-<this-point>.json
```

The helper requires the exact staged candidate, unchanged package baseline, retained previous image/modules,
and an absent new publication target. It exercises the existing `common.atomic` implementation. The partial
case changes only write chunking to guarantee that bytes were written and fsynced before process death;
the before-publish case stops after the complete temporary file's fsync and immediately before rename.
This test instrumentation is outside the frozen host payload and is not shipped in a production release.

The target lock is held and current `credential-ready` state is rechecked before the write.
Expected exit is 137 **and** a matching one-use checkpoint. Process status alone is insufficient. Snapshot ESP
state afterward: old image/default/modules/configuration must match; the new final path must be absent; a
`.pending-*` file must never appear as a boot entry or default. Before-copy expects no new pending file,
during-copy expects a nonzero shorter file, and before-publish expects a full matching temporary file.

Record the exact new temporary filename, inode and hash from the before/after difference. Remove only that
file after verifying those values; do not use `rm .pending-*`. Rerun `Host.install_boot()` once from the frozen
candidate through the root operator context. Verify the resulting final hash, successful signature check,
retained previous image, unchanged default and no partial selection. Repeat the complete installation once
only to check byte preservation; no reboot/replay or API call occurs in these publication-only probes.
Return to a healthy baseline control and compare configuration/profile rerender results before ending the row.

## B7: interrupted replay and selection

Keep the same per-row baseline copy and approved encrypted backup. Stage the existing transaction without
starting a race against the normal five-second reboot timer: in the guest root context, load the enrolled
candidate with `lab_faults.enrolled(run_id)`, call `instance.install_boot()`, set the host journal to
`package-staging` with the current `boot_before`, call `gates.replay_packages(transaction_directory, baseline,
boot_entry=entry)`, and set it to `reboot-pending`. These are the same ordered operations as `Host.advance()`.
Do not alter the candidate or the transaction.

Privately save the original generated `/etc/systemd/system/hermes-offline-replay.service` and verify its digest
against the offline journal. Replace only its `ExecStart` with:

```text
ExecStart=/usr/bin/python3 -I -B /usr/local/libexec/hermes-lab-certifier/lab_faults.py replay-fault --run-id <this-run-id> --point <this-point> --evidence /var/lib/hermes-lab-certification/fault-<this-point>.json
```

Record the original/test-unit hashes and replacement as test instrumentation; update only the journal's
`unit_sha256` to the exact test-unit hash so existing ownership cleanup remains meaningful. Preserve all other
unit fields, including `FailureAction=reboot`, `PrivateNetwork=yes` and the 25-minute timeout. Validate with
`systemd-analyze verify`, reload metadata, then perform one reboot with stdin closed.

| Point | Required fault witness | Expected durable state / follow-up |
| --- | --- | --- |
| `during-replay` | DNF killed while alive and RPM inventory between the initial and final inventories; checkpoint records mutation | No complete journal; record actual inventory and old modules. If mutation is not observed within the bound, the checkpoint fails and the case cannot claim interrupted RPM mutation. |
| `before-select` | Original replay returned successfully and expected inventory matched, before any `set-default` | Old default retained, journal incomplete; new artifact complete; ordinary resume requires explicit recovery. |
| `after-select` | `set-default` returned, before cleanup/completion journal | New default may be selected; incomplete journal must prevent false completion even when the new kernel boots. |

After the single reboot/failure return, read the checkpoint, inventory, journals and boot IDs. Require the
`/system-update` marker removed, no repeated replay loop and no `complete` status. Invoke the existing
`offline.require_complete` and require `offline-package-recovery-required`; do not run normal inference with
the synthetic credential. Test current ordinary resume refusal without deleting state. Confirm the previous
image still boots with its matching modules; if mutation removed them, retain FAIL and do not force a pass.

Explicit recovery within this row: shut down the verified fixed domain; preserve the failed disk at
`fixture.private/case-failed.qcow2`; restore the verified full `case-before.qcow2` into the exact fixed disk;
check/compare, restore its SELinux label and select the intact previous entry using the trusted boot manager.
No LUKS/TPM secret input is supplied. Record the changed boot ID, restored configuration and baseline inventory.
This is a declared disk recovery, not a resume or previous-image acceptance claim for the failed disk.

Run one clean replay with the original generated unit and unchanged candidate/transaction; verify expected
inventory, new selected UKI/modules and durable completion after its new boot. Calling `offline.execute` again
with no selected marker must report `offline-update-not-selected` without rerunning DNF. Preserve all failed
journals from `case-failed.qcow2` as sanitized evidence before L2 deletes that disk copy. Full controller closed
rerun and real inference are independently exercised by B3; do not label this synthetic-credential recovery
as a full candidate certification. If recovery cannot complete within the remaining bound, stop and retain
BLOCKED with the exact next recovery action.

## B7: notifications

The implemented transport is the workstation's desktop notification service via `notify-send`, not email,
Telegram or another messaging account. Fresh approval of `b7-notifications` must explicitly include local
desktop notification delivery. No external chat recipient is needed or inferred.

Use this row's root-owned `events` directory, a fresh private desktop-user state directory named by the run ID,
at `/var/home/cloudops/.local/state/hermes-remaining-notifications/<run-id>`, and the real logged-in desktop
session. Never copy another user's D-Bus credentials or start a fake session.
For the existing `maintenance.publish`, publish `failed` (code 69), `action-required` (75), and `completed` (0)
in that order, delivering each immediately using the frozen `notify.py --event <events/latest.json>
--state <fresh-desktop-state>` under the desktop user. Record each event hash/outcome and actual visible receipt
(operator acknowledgement or a bounded screenshot containing only the Hermes notification). A D-Bus send
return code or local event file alone is not visible-delivery proof.

For each event, invoke the notifier again and require `notified=false`, unchanged event/seen hashes, and no
second visible message. Invoke `maintenance.py --service-failed` after the existing failure event within 120
seconds and verify no duplicate event. Publish `deferred`; require no notification. Recheck the existing
maintenance-window function at an off-window timestamp offline; never enable ordinary timers for this test.

For a transport failure, use a subprocess with only `DBUS_SESSION_BUS_ADDRESS` set to an explicit nonexistent
socket under this row's private desktop directory. Deliver one new event with a fresh `seen` state and a
15-second bound: require failure and no `seen` advance. Restore the actual session environment, make one
explicit retry of the same event, require delivery once, then verify deduplication. Subsequent unrelated state
transitions may notify again; the current notifier deduplicates the latest event, not all historical events.
Remove only this row's desktop state after checking its owner, mode, path and contents. Record actual deletion.
A headless/unavailable notification session leaves this gate BLOCKED; do not substitute a mock for delivery.

## L2: exact cleanup, control restoration and verification

Cleanup is required after every success, expected fault, failure, interruption or expiry. The generated
service always runs the existing lifecycle `--cleanup-only` as `ExecStopPost`. It first reconciles any
attempted provider lease, restores/purges guest state, then destroys this fixture and removes private material.
B4/B7 sessions use the same cleanup state and driver; their operator shell must be finished before L2 begins.

```bash
# Same approved block directory as L0; no wildcard unit names or paths.
sudo timeout --kill-after=10s 51m /usr/bin/systemctl stop "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["unit"])' "$block/operation-proposal.json")"
# Run after the service's cleanup has finished; do not race it with another cleanup process.
sudo timeout --kill-after=10s 5m /usr/bin/python3 "$block/restore-controls.py"
sudo timeout --kill-after=10s 5m /usr/bin/python3 "$block/verify-restoration.py"
```

The 51-minute command is an observation/stop bound, not an extra allocation beyond the row's 50-minute cleanup
budget. Start it with the remaining deadline, and preserve evidence if that deadline is exceeded. Long-running
operator commands should yield output/control at least every 60 seconds; do not pipe provider terminals to logs.

Before destroying private recovery material, require provider deletion/revocation and absence of its stored
`.cred`, plus guest purge. Retain unresolved revocation state and needed recovery inputs on failure. Never
skip a failed prerequisite to remove the resources that would be needed to complete it. In the existing driver,
unreachable guest cleanup can still attempt provider revocation but blocks subsequent destructive cleanup.
Use the intact approved control image to regain guest access under this row's recovery scope.

Exact guest/fixture removal is implemented by `Fixture.cleanup`: verify the pool owner cookie/run/policy and
inode, fixed domain XML/UUID/disk set and absence of shared resources; purge guest Hermes/test identities and
configuration; remove only this run's `work/inputs`, `work/backup` and `private`; destroy/undefine only
`lab-hermes-server` with `--nvram --tpm`; verify VM/process absence; remove only the enumerated owned pool files
and pool directory. Private `case-before/case-failed` copies, signing/SSH/recovery keys, canaries and scratch
initrds therefore have exact cleanup ownership. Do not add unlisted files to the shared pool.

`restore-controls.py` then validates terminal cleanup (or a proven pre-dispatch failure), stops the exact
case/failure units and lab broker/socket, restores the saved broker bytes/uid/gid/mode/xattrs and UID 987,
removes only hash-matching case unit files, its socket override, sudoers file and the two fixed power helper
files, and reloads unit metadata. Root-owned public source/policy/evidence snapshots are retained as history.
If L0 stops before metadata backup, no broker/access mutation has begun; retain the exclusive source snapshot,
verify temporary controls are absent and record that pre-enrollment failure rather than fabricating L2 PASS.

Archive **both** the parent `grant.json` and any derived `state/<run-id>/candidate-window.json` to mode-0600
files under this row's `control-backup`, validating schema, run, policy/scheduler/candidate binding and identical
time interval before removing active copies. The derived grant may be absent in B7 staging-only rows; record
N/A with that reason. A failed row's grant is still consumed. Do not reset an active pointer, delete a failed
journal, extend expiry or repeat dispatch.

Independent verification requires all active grant/control/private paths, VM, disk/pool, NVRAM, swtpm and
runtime broker credentials absent; provider lease revoked or never issued; broker bytes/metadata/xattrs and
socket user/group/0600 restored inactive; original r1/r2/r3 source/policy/journals preserved; ordinary timers
unchanged. Check the supplemental desktop state separately for `b7-notifications`. Logical deletion is the
claim; physical media erasure is not. Any drift, unknown file, conflicting owner or unrevoked lease leaves L2
BLOCKED and prevents the next row. Retain exact paths and the next necessary recovery action without secrets.

## Evidence and closure

For each task, separately record progress and validation (`TODO`, `IN_PROGRESS`, `BLOCKED`, `FAIL`, `PASS`,
`STALE`, or `N/A` with the corresponding status emoji). Evidence must include UTC start/end, command/method,
source archive and policy/case/run IDs, candidate/transaction/image/initrd/module identities, selected/requested
boot entries and boot IDs, fault witness, actual result, paired control result and independent cleanup result.
Preserve unsuccessful checks; changed source, trust, transaction, image or machine identity invalidates affected
passes. Actual operations are recorded in new evidence files; this preparation record must never become a
synthetic lab PASS. No amended release signing, production mutation, permanent default change or timer
enablement is authorized by preparing or executing these disposable tests.
