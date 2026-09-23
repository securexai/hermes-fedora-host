# Unattended Hermes execution record

Approved 2026-09-07 by the user's explicit implementation request in this task.
Branch: `codex/hermes-unattended`. Production mutation is not authorized by this record.

## Current continuation — 2026-09-12 04:43Z

✅ PASS: B4-linux r8 completed its eight prerequisites, exact kernel-signature rejection and control
recovery. Independent L2 passed at 04:43:49Z, within the four-hour limit. The original broker metadata,
resources, grants and historical snapshots are reconciled. The lifecycle's intentional exit 69 remains
recorded; this supplemental PASS does not certify or sign a production release.
[Live evidence](evidence/2026-09-12-hermes-b4-linux-r8-live.json) retains the full result and limitations.

🔄 IN_PROGRESS: B4-initrd r9 dispatched once under standing user authorization. Package validation
passed all 103 files; per-case preparation fingerprints are unchanged. Available RAM is 10,582,584 KiB
versus the unchanged 9,437,184 minimum, and no VM exists. Reuse unchanged offline evidence; never reuse
live acceptance, identities, TPM state or consumed grants. B3 and B4-linux are 2 of 14 completed live cases;
12 remain. Production P2–P4 remain open, and production deployment requires user approval.

R9 L0 passed at 04:46:05Z and dispatched once at 04:46:33Z. Its total cleanup deadline is 08:46:01Z.
Exact next action: preserve r9 inputs and wait for all eight prerequisites, then execute its negative boot,
recovery and mandatory independent cleanup before b4-cmdline. Four hours maximum per block.

## Approved baseline

Extend the existing controller into a certified release pipeline after one-time enrollment.
Prepared Fedora Server host; deployment only, preserving agent approvals. Use the current workstation
for certification, isolated OpenAI credential administration, signing, deployment, and encrypted backups.
Maintenance: Sunday 02:00–04:00 America/Bogota; missed windows defer. Normal operation has no terminal
input. Trust failures stop safely with a recovery action.

- Enroll host identity, TPM2/LUKS2/Secure Boot, recovery access, dedicated restricted SSH identity,
  root-owned dispatcher, release signer, maintenance policy, and credentials. Rotate the exposed sudo
  password before privileged work. Never make the old uploaded-script helper permanently passwordless.
- Sign exact artifact, package transaction, boot, provider/model, baseline, and certification evidence.
  Verify on controller and host before extraction/execution; reject unsafe paths, links, extras, stale
  records, wrong hosts, and altered contents. Preserve host binding and first-use expiry.
- Separate certification, signing, deployment, and credential identities. Add noninteractive config,
  release, upgrade, structured status, target locks, release-keyed state, bounded calls, and recovery.
- Isolate administrative credentials behind a local fixed-operation service. Separate test/production
  accounts; prove provider-side revocation before promotion. Rotate production credentials only after
  replacement acceptance. Encrypt credentials with systemd; expose runtime files only in volatile storage.
- Certify signed UKI/initramfs/command-line boot with Secure Boot and signed PCR11 policy, retain offline
  recovery and previous signed boot entry. Never type LUKS passphrases automatically in this profile.
- Pull consistent encrypted Restic backups to the workstation; verify restoration before mutation.
  Retain eight successful pre-change snapshots and protect the active rollback snapshot. Automatically
  roll back application artifacts on failed acceptance; OS failure requires explicit recovery.
- Replay certified RPM transactions strictly; keep download-only automatic updates. Scan images and
  block undispositioned high/critical vulnerabilities. Preserve rootless, SELinux, read-only, resource,
  listener, network and agent policies. Test capability/label exceptions before removing them.
- Notify only on meaningful completion/failure/action with secret-free state. Preserve wrappers,
  fingerprints, canonical evidence ledger, and ordered deployment tasks.

## Tasks and validation gates

Later approved policy change: the user accepted advisory image vulnerability scans with an explicit
denylist for assessed unacceptable risks. Severity counts alone no longer block. Scan integrity and
completion, denylist matches, signatures, identity, credentials, runtime, backup and boot acceptance
remain mandatory. This supersedes the earlier severity/disposition rule. Official images only remains
in force. Implement this change before resuming the pending certification work.

Scope decision: the user instructed "document only" for image issues and explicitly excluded maintaining
the Hermes image. Use official upstream images only. Custom image forks, rebuilds, patches and ongoing
image maintenance are out of scope. Keep the recorded findings and existing promotion gate; no exception
or external issue submission is authorized by this decision. This supersedes the local image-remediation
work item while preserving the remaining deployment implementation scope.

| ID | Task / dependencies | Progress | Gate | Gate status | Evidence / next action |
| --- | --- | --- | --- | --- | --- |
| U01 | Release trust and input boundary | ✅ PASS | Tamper, signature, expiry, path, host, protocol tests and source review | ✅ PASS | 128 unattended, 12 offline replay and 11 certifier tests; prior boundary review retained |
| U02 | Controller and privileged dispatch; U01 | IN_PROGRESS | Closed-stdin install/upgrade/rerun, locks, interrupted transport | PARTIAL | UA-03 lab stages, locks and closed reruns passed; signed production dispatch awaits UA-05 |
| U03 | Credential service and runtime delivery; U01 | IN_PROGRESS | Mock API lifecycle, canary leakage, rotation/revocation | PARTIAL | UA-03 test-key delivery, read-only overlay and real API acceptance/revocation passed; production role remains disabled |
| U04 | Backups and rollback; U02 | IN_PROGRESS | Failed backup, verified restore, interrupted update | PARTIAL | UA-03 semantic encrypted restore and rejected receipts passed; earlier rollback fixture evidence retained |
| U05 | Boot, package, scan and signing pipeline; U01 | IN_PROGRESS | Exact replay, TPM boots, advisory scan/denylist, cleanup | PARTIAL | UA-03 exact replay, updated UKI boots and advisory scan passed; cleanup and signing passed UA-04; scheduling remains separate |
| U06 | Scheduler, documentation and offline integration; U02–U05 | ✅ PASS | Suites, lint, links, no-input public seam | ✅ PASS | S1–S4, L1–L6 and F1–F4 PASS; lab lifecycle evidence and limits below |
| U07 | Disposable certification; U01–U06 | ✅ PASS | HERMES_OK, restore, revocation, cleanup, signed promotion | ✅ PASS | UA-03 and UA-04 evidence; scheduler integration remains under U06 |
| U08 | Production readiness; U07 | 🔄 IN_PROGRESS | Hardware recovery and explicitly authorized enrollment | TODO | Production work authorized; password rotation confirmed by operator; P1–P4 below |

## Current next action — 2026-09-12

R7 is independently cleaned; no fixture is active. The user authorized revising and implementing a faster
lab sequence while preserving any active run, all isolation/gates, and the production approval boundary.
Complete the preparation queue and resource checks below, then dispatch the next eligible fresh B4-linux
run only after sufficient RAM and independent predecessor cleanup. Preserve all failed attempts and grants.
No production mutation, commits, pushes or ordinary scheduler enablement is authorized.

## Evidence

The [earlier offline observation](evidence/2026-09-07-unattended-offline.json) records command outcomes,
output hashes and the uncommitted source fingerprint. It is not certification or promotion evidence.

- Pre-implementation review: 138 ShellSpec examples and 217 guide checks passed; no production probe.
- The repository-relative `docs/plan-execution.md` link is missing. Used the existing global guide at
  `/var/home/cloudops/.codex/docs/plan-execution.md`; this record follows its gate procedure.
- Work begins from a clean `main` checkout; no commits or pushes are authorized.
- Offline Python suite: 81 tests passed, including real OpenSSH signing/verification and real Restic
  encryption/dump round trips. Mock lifecycle and host-stage checks are not live certification.
- The first real Restic integration run failed because its default cache used an unavailable home path.
  Added `--no-cache` to backup, restore, preflight and retention; subsequent integration tests passed.
- Public registry scan with Trivy 0.74.0 succeeded, but vulnerability policy failed: 20 critical,
  463 high and 191 unknown-severity package findings, with no dispositions. These are package findings,
  not unique CVEs or demonstrated exploits. See [durable scan summary](evidence/2026-09-07-hermes-image-scan.json).
  Full raw report is temporary at `/tmp/hermes-trivy-report.json`; its SHA-256 is in the summary.
- Scanner compatibility fix accepts Docker Hub's equivalent repository spelling without `docker.io/`,
  retains the exact repository and digest binding, and isolates registry configuration and cache.
- Rollback restores the Hermes-owned configuration with container UID/GID 10000 in the rootless user
  namespace. A regression ensures that this path does not use the root atomic writer.
- Regression checks: 138 ShellSpec examples and 217 guide checks passed; ShellCheck and repository
  shfmt flags passed. An initial shfmt invocation omitted repository indentation flags and reported
  formatting differences; it made no edits. Rechecking with `-i 2 -ci -bn` passed.
- Both new Markdown documents passed non-fixing lint in an isolated copy; local links resolve.
  `git diff --check` passed. These checks do not validate systemd or Fedora behavior on a live host.
- No services enabled, provider API mutations, TPM enrollment, production SSH, commits, or pushes occurred.
- New upstream digest `sha256:efb82540aeb8ac21c58ecb4482bd3eb103ea617da2af2c61f12526ed68f6c2d9`
  resolved from the public registry and scanned with Trivy 0.74.0. It still fails: 19 critical,
  379 high and 159 unknown package findings. Eighteen critical findings have no listed fixed version.
  See [candidate scan and blocking findings](evidence/2026-09-07-hermes-candidate-scan.json).
  No pin change, image execution, rebuild, publication or disposition was performed.
- Read-only libvirt inventory was empty. Broker policy/socket, signer enrollment policy and candidate/
  evidence handoff are absent at the documented paths. No new VM was created. At that observation TPM provisioning was
  unimplemented; the later staging work below does not yet complete the certifier.
- Maintenance tests cover missed windows, missing releases, incomplete results, canary-safe failures,
  changed-release notifications, duplicate suppression and delivery retries. Signer tests reject stale
  and mixed-run evidence, premature destruction/revocation, and candidate path traversal.
- The real finalizer was exercised with disposable signing keys and synthetic evidence: it preserved
  the candidate fingerprint and started the signing expiry after evidence assembly. This is an offline
  fixture, not live evidence eligible for promotion.
- Credential materialization and configuration capture no longer read Hermes-owned paths with root
  authority. The new reader tests reject symlinks and oversized input. Runtime-directory ordering was
  added before credential materialization; live boot compatibility is still unverified.
- `systemd-analyze verify` passed for the six new/changed signer, maintenance and notification units,
  and separately for the changed runtime credential unit.
  The first sandboxed verification failed on restricted sockets; read-only verification outside the
  sandbox passed. Calendar verification passed with an argument-vector invocation: next Sunday at
  02:00 Bogotá. An initial shell invocation expanded the wildcard; it was corrected without unit edits.

### Signed installer and policy follow-up

- Implemented the approved advisory/denylist policy and bound the frozen policy hash into scan evidence.
  [Reevaluation](evidence/2026-09-07-advisory-policy.json) preserves the historical stricter scan failures.
- Added workstation UKI construction, separate OVMF variable enrollment, verified EFI media round trips,
  and an explicit TPM staging profile. Private keys remain outside the guest. Staging stops powered off;
  installed UKI injection and first-boot orchestration remain incomplete.
- The installer test initially rejected an empty PCR phase. Inspected pinned ukify's phase parser and
  removed that unsupported phase; all 89 Python tests then passed. Synthetic initrd tests prove artifact
  construction and signature validation, not bootability.
- The refreshed legacy suite initially had two failures: a changed VM command layout and PyYAML missing
  from the new Devbox Python environment. Updated the layout assertion and added an explicit dependency.
  The first dependency installation hit sandbox cache restrictions; retried using the approval mechanism.
- ShellCheck and repository shfmt checks passed for the changed VM creator and promotion script;
  217 guide checks passed. Live TPM/API certification and production remain unpassed.

The [refreshed offline observation](evidence/2026-09-07-signed-installer-offline.json) records the
updated source subset identity: 89 Python tests, 138 ShellSpec examples, 217 guide checks, affected
ShellCheck/shfmt checks, and five-document nonfix lint and local link validation passed. The initial
Markdown check found one overlong line; wrapping it resolved the failure. No production changes occurred.

## Historical next action — before lab certification

This section preserves the earlier work sequence. U07 and UA-03/UA-04 subsequently passed;
use the current next action below and the dated closure entries for current status.

Continue the authorized repository and disposable-lab implementation; production remains excluded.
Image issues are documentation-only work for this repository, following the user's later scope decision.
Evaluate a new official upstream image when available; do not create or maintain a custom build.
A missing enrolled fixture, invalid/failed scan or explicit denylist match must block certification and
signing. Severity findings are advisory. Never generate synthetic PASS evidence for promotion.

Next connect guest kernel/initrd extraction and installed UKI construction to the disposable TPM/UKI
certifier, complete the privileged-boundary review, and validate real enrolled boot/recovery fixtures.
Use the approved advisory/denylist image policy. Add semantic restore, actual runtime credential compatibility,
provider-side revocation and failure-matrix evidence before signing. Finish scheduler lifecycle and
candidate-to-certifier scheduling. Local notifications are implemented but live desktop delivery is
unverified. U07 and U08 remain unpassed; offline fixtures do not constitute deployment certification.

### 2026-09-07 continuation: lab UKI handoff

Approval reference: user "Continue" after the next-step explanation. Scope remains repository and
isolated lab work; production is excluded. Preserve the existing uncommitted implementation.

Task progress: the lab UKI injection and bounded first-boot helper are implemented, with the
Kickstart public enrollment marker, promotion fingerprint coverage, tests and operational procedure.
The U01–U08 baseline remains open; this completes only the bounded handoff implementation block.

- ✅ PASS: offline boundary gate: 104 Python tests, including real signed-UKI verification and
  tamper rejection, wrong/running domain rejection, PCR mismatch, failed copy and damaged-backup
  recovery, idempotent reruns, pinned SSH and bounded first-boot observations.
- ✅ PASS: disk I/O gate: one real libguestfs FAT/QCOW2 integration test passed, including initial
  injection, readback and an unchanged rerun preserving original EFI bytes. This fixture mocks
  domain and signature gates; it never boots a Hermes guest and cannot issue promotion evidence.
- ✅ PASS: 138 ShellSpec examples; promotion script ShellCheck/shfmt; both TPM Kickstart post
  bodies passed Bash syntax and ShellCheck. Validation details and tested source identity are in
  [the handoff observation](evidence/2026-09-07-lab-uki-handoff.json).
- ✅ PASS: 217 final guide checks, six-document nonfix lint, local file links and whitespace validation.
- 🚧 BLOCKED: real first boot and UA-02 acceptance: the read-only local libvirt inventory is empty.
  Enrolled broker/signer fixtures and automatic installed-UKI candidate handoff remain absent.

The installed guestfish rejected `-f -`; corrected stdin invocation and added a parser regression.
Sandbox appliance probes failed on temporary paths and then socket binding. Temporary-directory
configuration and an approved run outside the sandbox allowed the real disk test to pass. Earlier
failures remain recorded in the observation. Concurrent final Devbox checks raced on its generated
command script; the serialized guide retry passed. Review also tightened retries to reject a damaged
existing EFI backup before replacement. The final disk rerun passed after that change.

No production access, provider mutations, VM enrollment, commits or pushes occurred. The helper keeps
`boot_verified: false`, even when pinned SSH observes the intended command line and Secure Boot.
First injection retains distribution EFI recovery files, not an already-certified previous signed UKI;
that recovery gate remains open. The helper lock covers its own invocations, so exclusive operator
control of the disposable fixture is still required during disk access.

Exact next action: integrate guest kernel/initrd extraction and installed UKI construction with the
disposable candidate/TPM certifier, then validate real enrolled boot and recovery fixtures in UA-02
order. Complete the privileged-boundary review before dependent certification or signing.

### 2026-09-07 continuation: guest candidate construction

Approval reference: user "proceed" after the next-task explanation. Scope: repository and disposable
lab integration; preserve existing edits. Dependencies: existing staging, UKI builder and injection.

- ✅ PASS: export guest boot inputs and construct/freeze/inject the same candidate UKI (offline).
- ✅ PASS: boundary gate: reject incomplete/tampered exports before signing or disk writes; test
  candidate identity, ordered handoff and failure behavior with offline fixtures.
- ✅ PASS: regression gate: unattended Python, Hermes/VM ShellSpec, guide, changed shell syntax/lint,
  documentation lint/links and whitespace checks. Record source identity and exact results.
- 🚧 BLOCKED: scoped handoff review complete; full review and enrolled UA-02 fixtures remain.

Affected guidance: VM testing guide, unattended deployment guide and canonical evidence ledger.
Exact next action: implement a bounded public ESP export and candidate orchestration.

Implementation complete for the guest candidate handoff block. The staging post script exports only
public boot inputs after dracut, with a fixed-name checksum manifest. `lab_candidate.py` validates the
export and enrolled public key, constructs the UKI, freezes the candidate, verifies byte identity and
injects that candidate under the existing disk lock. Existing candidate directories fail closed.

- ✅ PASS: 109 unattended Python tests (final rerun after identity check), 138 ShellSpec examples,
  217 guide checks, and both Kickstart post bodies passed Bash syntax and ShellCheck.
- ✅ PASS: scoped privileged-boundary source review: fixed disposable domain/disk; public-only export;
  exact manifest names reject traversal/duplicates; enrolled PCR key and UKI byte binding; signing keys
  remain workstation-local; lock spans handoff; no shell evaluation of guest data; candidate construction
  precedes disk writes; failure cannot emit a boot PASS or promotion record. Existing EFI backups remain.
- 🚧 BLOCKED: UA-02: read-only libvirt inventory is empty; signer and broker policies are absent at
  `/etc/hermes-unattended/{signer,broker}.json`. Sandbox denied the initial inventory socket; the approved
  read-only retry succeeded. No guest, provider account or production resource was mutated.

Review limitations: exported hashes establish consistency only; the controlled guest is a trust input.
Post-download size limits do not bound appliance disk consumption before download completes. Exclusive
operator control remains necessary against other libvirt clients. This scoped review does not close
U01's full independent privileged-boundary review or prove boot, recovery, package replay or signing.

Exact next action: provide/enroll the isolated broker and signer identities and controlled TPM staging
fixture, then run the new handoff and real UA-02 boot/recovery checks in order. Full privileged-boundary
review remains required before dependent certification/signing. U07 and U08 remain unpassed.

Documentation validation initially failed on one overlong VM-guide line; wrapped it and reran the
five-document nonfix lint, local file-link and whitespace gate. See the
[candidate observation](evidence/2026-09-07-guest-candidate.json) for validation and source identities.

### 2026-09-07 continuation: full boundary review and live lab

Approval reference: user's five-step request, explicitly authorizing repository and disposable-lab
review, repairs and setup. Existing branch and unrelated edits are preserved. Production is excluded.
This section is the canonical continuation; no additional execution tracker is created.

| Block | Dependencies | Progress | Validation gate | Validation status |
| --- | --- | --- | --- | --- |
| R1 boundary review and repairs | Existing U01–U06 sources | ✅ PASS | Root, signing, credential and VM boundary review; regressions; affected checks | ✅ PASS |
| R2 disposable TPM staging | R1 | ✅ PASS | Verified Fedora media, separate test keys, private recovery material, fixed isolated VM and shutdown marker | ✅ PASS |
| R3 handoff and recovery | R2 | ✅ PASS | Guest export, signed UKI, pinned automatic boot, tamper rejection, actual recovery and cold boot | ✅ PASS |
| R4 isolated services and certification | R3; enrollment inputs | 🔄 IN_PROGRESS | Isolated identities, credential lifecycle/revocation, semantic restore, ordered UA-02–UA-04 evidence | UA-02 ✅ PASS; UA-03/UA-04 ✅ PASS; historical setup evidence below |

Review findings under repair: root identity setup follows mutable user-owned paths during ownership
and mode changes; dispatcher inherits caller environment; VM creation can overwrite orphan storage;
TPM staging reuses a published fixture recovery passphrase. Remaining source review is in progress.
Do not exercise signing or privileged operations until R1 passes.
Affected documentation: VM guide, unattended guide, this record and canonical evidence ledger.
Exact next action: repair these boundaries and add adversarial regressions before lab provisioning.

R1 source review completed before signing tests or lab operations. Reviewed `common`, `release`,
`dispatcher`/wrapper, `host`, `materialize`, `credentials`/socket units, `signer`, `finalize`,
`build_release`, controller/policy/maintenance, boot builders, candidate/injection and VM/Kickstart.
Repaired the four findings above, a signer ancestor rename race (descriptor-relative reads), and
packager checks that previously rejected changed payloads only after signing. The signed payload
is intentionally root-authorized code; only the enrolled certifier may supply promotion evidence.
Mock evidence cannot establish certifier isolation, boot recovery or provider revocation.

Focused non-signing review regression: five tests passed after two fixture failures caused by
sandbox ancestor ownership remapping (root appears as UID 65534). Test-only ancestor metadata now
models enrollment while retaining real filesystem rename/symlink behavior. ShellCheck, shfmt and
whitespace checks passed. Full regression gate remains pending; only disposable synthetic keys
may be used by offline tests until it passes. No privileged or production operation has run.

R1 regression gate: ✅ PASS, 113 unattended Python tests, 138 Hermes/VM ShellSpec examples,
217 guide checks, changed shell ShellCheck/shfmt. No external signing identity was used.
Source review and repairs permit dedicated disposable lab signing/setup; this is not UA-02 acceptance.
The reviewed boundary assumes exclusive local hypervisor control and root-owned installed code/policy.
Full independent review here means a separate review pass, not a separate agent (delegation was not requested).

R2 preflight: supplied Fedora 44 checksum has a valid signature under key
`36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6`; DVD SHA-256 matches
`85837793bfa36db6bc709b4cecd2ec116951b87d9c53c3d95eb2fac8dcf7cf1f`. Four CPUs,
10,068,896 KiB available memory and 394,293,846,016 bytes free storage passed thresholds.
Local libvirt inventory is empty; both dedicated storage files are absent. Initial sandbox libvirt
read was denied; approved read-only retry succeeded. R2 is 🔄 IN_PROGRESS.
Exact next action: generate private lab recovery/SSH/boot/PCR keys, build installer from the verified
DVD, create fresh enrolled OVMF variables, and start only the fixed disposable TPM staging domain.

R2 first creation attempt failed before disk creation: general libvirt pool is root-owned mode 0711.
Read-only local sudo inventory confirms cloudops has NOPASSWD authority; no production account is involved.
Use a fixed dedicated `hermes-tpm-lab` subdirectory, operator-owned mode 0711, preserving general pool
permissions. Creator and disk helpers now share that fixed path; legacy profile is unchanged.
R1 affected path regression is 🔁 STALE until revalidated. Next: run affected tests, create only the
dedicated lab directory, then retry staging.

Dedicated-path regression ✅ PASS: 113 Python tests, 138 ShellSpec examples, ShellCheck/shfmt.
Created only the dedicated lab storage directory (cloudops-owned 0711; restored SELinux context).
Fresh installer UKI and OVMF variables use separate private lab Secure Boot/PCR keys; private recovery
and SSH material are in the ignored `private/hermes-tpm-lab-20260907/` directory, mode 0700.
No private values were logged. The fixed TPM VM is now installing from the verified DVD.
[Review and preflight evidence](evidence/2026-09-07-privileged-boundary-review.json) records progress.
Exact next action: wait for installer shutdown, verify the stage marker, extract guest boot inputs
and independently pin the guest SSH key via offline recovery access. UA-02 remains unpassed.

The live creator process ended with signal 143 while the domain remained running in Anaconda.
Cause is not established; no reinstall or VM destruction occurred. Monitor the existing UUID
`4db6369a-2b8b-427f-a47a-a5d83bb40cff`; detach media only after shutdown.
The prior export-size limitation is now repaired: check appliance file sizes before downloading
metadata, boot inputs and EFI readbacks; recheck copied lengths. 114 Python tests passed, including
rejection before any oversized-file download. Real appliance validation remains pending.

Identity reruns account for container-owned data: the unprivileged Hermes child performs descriptor
ownership/mode changes inside its own Podman user namespace. This preserves mapped container UID
compatibility without granting host root authority over mutable paths. Revalidate the focused
identity boundary before any runtime use; actual runtime compatibility remains an UA-03 check.

Final repaired-source validation: 114 Python tests and 217 guide checks passed. The bounded disk
read/injection implementation passed one real libguestfs test in 220.797 seconds, preserving original
EFI content across an unchanged rerun. Earlier 138 ShellSpec examples and changed shell lint/format
checks remain valid (their inputs have not changed). Documentation lint found two overlong VM-guide
lines; wrapped them, with the lint retry pending. Local file links passed.

R2 live staging ❌ FAIL: installer post log reports “Could not read pcr values: Operation not
supported”; Anaconda records ScriptError 43. The stage marker is not accepted and no installed UKI
was injected. Retain the failed fixture for diagnosis. Exact next action: inspect exposed TPM PCR
banks and installer/target systemd versions, repair the cause, revalidate, then retry enrollment.

R2 diagnosis: target systemd 259.5-1.fc44 exposes a SHA-256 PCR bank and reports Secure Boot
enabled. Explicit `7:sha256` passes the original PCR-reading point but fails the signature/unseal
safety check. Direct public PCR11 observation is all zeros and all three boot-phase services are
inactive. The supplied 2 MiB OVMF pair did not establish measured UKI boot in this fixture.
No zero-PCR policy was signed and no signature safety check was removed. Added pre-install and
pre-enrollment rejection of uninitialized PCR7/PCR11. Preserve the failed disk and retry with the
supplied 4 MiB firmware pair converted to raw and separately enrolled variables.
The explicit-bank syntax follows [systemd documentation](https://github.com/systemd/systemd/blob/v259/man/systemd-cryptenroll.xml);
[systemd's bank-selection code](https://github.com/systemd/systemd/blob/v259/src/shared/tpm2-util.c) informed diagnosis.

Corrected firmware live observation: PCR11 is
`e82c9d7b2e1b17c40a9e2bf6fcd42ba88c9c579a62487c7dd7ba86387fce32ef`, exactly matching
`systemd-measure calculate` over the original installer's measured PE sections at `sysinit:ready`.
Installer initrd phase service is inactive; sysinit and ready services are active. Correct installer
policy to `sysinit`/`sysinit:ready`; retain `enter-initrd` for installed-system unlock. This is an
offline-predicted artifact policy, never a signature over an arbitrary live PCR. The current run
will receive only the corrected public signature, with measured-section identity verified first.
Its repaired enrollment is lab evidence; a clean certification run is still required by UA-03.

Corrected public policy hash verified inside the installer. TPM enrollment succeeded as slot 1,
then dracut failed because `tpm2-tss` requires the missing `tpm2` executable. DVD-only DNF repair
failed with “No match for argument: tpm2-tools”; no signature check was bypassed. The TPM profile
now installs that prerequisite from the existing signed Fedora 44 release repository in a bounded
post step, with installer-chroot DNS preserved. The release repository excludes updates.
All three revised pre/post bodies pass Bash syntax and ShellCheck. Preserve the successful TPM
slot: repair only the dependency, dracut regeneration and public export; do not re-enroll needlessly.
Exact next action: verify signed package installation, resume the public-export tail, shut down
and independently pin the new SSH host identity before installed-UKI injection.

Signed Fedora release installation ✅ PASS: `tpm2-tools-5.7-5.fc44.x86_64` installed with
DNF exit 0 and package verification enabled. Retained TPM slot 1 and resumed only dracut/export
tail; exit 0 and the root stage marker were observed through the disposable guest console.
The resolver same-file guard and all three current Kickstart bodies pass Bash syntax/ShellCheck.
R2 remains 🔄 IN_PROGRESS until offline recovery access and installed-UKI boot are observed.
Exact next action: clean shutdown, detach installer media, independently pin SSH identity using
the dedicated recovery key, then extract/build/inject the installed UKI.

Offline recovery probe opened the current encrypted disk but initially failed because SSH host keys
are generated on first boot. Provisioned a dedicated guest ED25519 identity offline, restored its
SELinux labels, and independently read it back. Recovery access, stage marker, Fedora version and
SSH pin ✅ PASS. No unpinned SSH connection occurred. Private evidence: `recovery-access.json`.

R3 extraction ❌ FAIL: guestfish adds a printer newline to `cat`, causing valid manifest rejection.
Fixed bounded reads to preserve exactly the measured file bytes and reject changed lengths.
116 unattended Python tests ✅ PASS, including real printer-newline and changed-length regressions.
Keep the failed extraction directory; retry into a fresh directory. Live read/injection validation
is 🔁 STALE until the corrected reader completes the real handoff.
Exact next action: extract, build and inject the installed UKI; then verify pinned automatic boot.

R3 installed handoff ✅ PASS for the repaired fixture: public guest inputs extracted and hashed;
workstation UKI built, signed, and verified; recovery QCOW2 copied/checked; both EFI paths replaced
with verified readbacks. UKI SHA-256 `b705c8e74abc8b43ea8be7fb0b627cb3fdb4ac6ad63b8e1a3e6d8d122e103e97`.
Pinned SSH observed automatic boot with the exact signed command line and Secure Boot enabled.
Live evidence reports enforcing SELinux, initialized PCR11, no crypttab key files, recovery slot 0
and TPM slot 1 bound to SHA-256 PCR7 plus signed PCR11. No console unlock input was supplied.
The first privileged probe used an ungranted direct Python sudo command and was rejected; the
fixture's existing exact sudo Bash path succeeded. No privilege policy was broadened.

Private evidence: `live-handoff.json`, `installed-build.json`, `installed-live-evidence.json`,
`recovery-access.json`. No release candidate or promotion record was issued. R3 remains
🔄 IN_PROGRESS for actual tamper rejection and recovery boot. Exact next action: clean shutdown,
alter one measured UKI byte, observe firmware rejection, restore the verified UKI, and boot again.

R2 disposable staging and R3 repaired handoff/recovery ✅ PASS within their bounded lab scope.
Altered `.linux` bytes failed `sbverify`; both EFI copies matched the altered hash. Firmware
explicitly rejected both paths with Access Denied and no bootable device. Preserved the screenshot.
Stopped only the firmware-halted disposable guest, restored both paths from the verified trusted
UKI, checked readbacks and observed automatic recovery boot with a new boot ID and unchanged
Secure Boot, SELinux and TPM policy. No recovery passphrase was submitted to a console.
[Sanitized live handoff evidence](evidence/2026-09-07-hermes-tpm-handoff.json) records the observations.
UA-02 remains unpassed for isolated services; UA-03 clean certification and UA-04 cleanup are pending.

R4 🔄 IN_PROGRESS: enroll separate lab signer/certifier/deployment identities under dedicated
`/var/lib/hermes-lab-unattended` paths with a lab-only, disabled signing unit. Validate role
separation and refusal without genuine certification evidence; no production follow-up unit.
Broker enrollment awaits the requested OpenAI test project ID and encrypted admin-credential path.
Do not invent project IDs, credentials, or passing certification evidence.
Exact next action: prepare and validate the isolated signer enrollment, then resolve broker inputs.

R4 isolated signer enrollment ✅ PASS for setup and negative acceptance. Separate lab UIDs,
root-owned reviewed code/policy, a private release key and static `hermes-lab-sign.service` are
installed under `/var/lib/hermes-lab-unattended`. The unit has no production follow-up trigger.
Actual OS permission tests passed. The service rejected absent certification with exit 78,
published no archive, and its expected failed state was then reset.
[Signer enrollment evidence](evidence/2026-09-07-hermes-lab-signer.json) records roles and checks.

R4 overall 🚧 BLOCKED on the OpenAI test project ID and workstation encrypted admin-credential
path requested during this run. No administrative API call or broker service activation occurred.
Credential lifecycle/revocation, semantic backup restore, clean package/update/runtime certification
and UA-04 cleanup remain unpassed. The recovered VM is confirmed shut off, with recovery material
and failed-run disks retained; the plan stays open. Production, commits, pushes and PRs are unchanged.
Exact next action: obtain those two broker enrollment inputs (never raw credentials), prepare its
isolated test-only policy, verify UA-02, then execute UA-03 and UA-04 in order.

Final recovery-material permission gate initially ❌ FAIL: the replacement QCOW2 inherited mode
0644 from its creation. Tightened the stopped disk to 0600 and made the creator explicitly set
0600 immediately after disk creation. All eleven inspected private state/material paths now pass
mode restrictions. This metadata repair does not change measured UKI bytes or TPM policy.
138 Hermes/VM ShellSpec examples and ShellCheck ✅ PASS after the creator repair. The first shfmt
invocation omitted repository indentation flags and failed; the documented
`shfmt -d -l -i 2 -ci -bn` command ✅ PASS without formatting unrelated code.

Documentation lint (five changed/current Hermes documents, nonfix isolated copy), local links
and whitespace checks ✅ PASS before this closing record. The documented `diff_docs.py` audit
command is 🚧 BLOCKED: its file is absent, and focused searches in available skill/plugin roots
found no replacement. Preserve this unavailable check; no complete documentation audit is claimed.
The evidence ledger and current task statuses were manually reconciled with observed lab outputs.
The final documentation/guide checks below are rerun after this record update.
Exact next action remains the two missing broker inputs, followed by isolated enrollment and
ordered UA-02–UA-04 gates; also restore the unavailable documentation-audit dependency.

Broker enrollment input update: the user supplied the test project identifier. Recorded it in
private `broker-enrollment-inputs.json`; provider validation remains pending. The expected encrypted
admin credential `/etc/credstore.encrypted/hermes-lab-openai-admin` is still absent according to
a privileged metadata-only check. R4 remains 🚧 BLOCKED on that credential, not the project ID.
Exact next action: the operator enters the admin key through the supplied hidden workstation
encryption prompt; then validate encrypted credential delivery and enroll the isolated test broker.
No provider request, broker activation or production operation occurred during this input update.

Credential entry update: the operator's multiline `sudo devbox run -- bash -c` invocation failed
with `nset: command not found` before the hidden prompt. Prepared a local script-file entrypoint
at `/tmp/hermes-encrypt-lab-admin.py` to avoid multiline argument transport. It requires a normal
user terminal, prompts without echo, encrypts through stdin, verifies decryption to `/dev/null`,
and exclusively creates the fixed root-owned mode-0600 ciphertext file. Syntax and mocked data
flow/redaction checks pass; real credential entry remains pending. No secret was supplied to these
checks. Exact next action: operator runs `devbox run -- python3 /tmp/hermes-encrypt-lab-admin.py`
without leading sudo, then the agent validates encrypted credential delivery before enrollment.

R4 resumed after the operator successfully encrypted the admin credential. Root-owned mode-0600
regular ciphertext metadata ✅ PASS. Test project ID is already recorded privately.
Before broker activation, add an explicitly disabled production role and root-configurable lab
paths to the existing broker, with regression gates for incomplete policies, UID separation,
production requests rejected before API access, and activated-socket identity. This implements
the previously approved isolated test-only enrollment; no production policy is supplied.
Then validate real systemd credential encryption/decryption under the isolated service identity
before issuing any provider credential. Preserve uncertain issuance for reconciliation.
Exact next action: implement/review the test-only boundary, run affected tests, and enroll a
separate lab broker/socket without a production service or maintenance trigger.

### 2026-09-07 isolated broker credential gate

R4 credential enrollment ✅ PASS: the operator supplied the encrypted admin credential, verified
root-owned mode 0600. The static lab broker runs as UID 985; only certifier UID 987 can use its
socket. Both production policy fields are null. The original signer snapshot is unchanged; the
broker uses a separately hashed root-owned code directory and dedicated private state.

The actual unit passed systemd verification, encrypted admin delivery and dummy user-scoped
credential encryption/decryption before provider issuance. The fixed test-project read succeeded.
One disposable service account was issued, its encrypted key reread, repeat issuance returned the
same key, and the key authenticated against the model list. Account deletion followed by HTTP 401
proved revocation; the encrypted lease was removed. Production requests and deployment/signer
socket access were rejected. Other lab roles cannot read the encrypted admin credential.
See [sanitized broker evidence](evidence/2026-09-07-hermes-lab-broker.json).

Regression validation ✅ PASS: 119 Python tests in 10.832s. The first 119-test run failed because the
sandbox denied the real Unix socket bind; the approved run with local socket access passed.
The prior 118-test run also passed. Relevant enrolled source hashes are recorded in the evidence.
No raw keys were written to repository evidence or command output. No production operation occurred.

R4 overall remains 🔄 IN_PROGRESS; UA-02 is not yet passed. Exact next action: complete the guest
runtime credential mount and semantic application backup/restore fixtures, then integrate a clean
exact-candidate certification run in UA-03 order. Do not sign or promote incomplete gate evidence.

Documentation gate ✅ PASS: four-document nonfix lint, local links and whitespace checks. The first
lint identified two extra blank lines; both were corrected and the gate rerun successfully. The
previously recorded missing repository docs-sync script remains unavailable. After credential
validation, both static lab broker units were stopped and confirmed inactive; enrollment and the
encrypted admin credential are retained for the next fixture. Restart the socket and service when
resuming the guest credential gate. No provider lease remains active from this test.

### 2026-09-07 guest runtime and restore continuation

Approval reference: user "proceed" after the UA-02 next-step explanation. Scope: existing disposable
lab, guest credential delivery and semantic application backup/restore; proceed to UA-03 only after
UA-02 passes. Production remains excluded. Preserve the existing feature branch and uncommitted work.

- 🔄 IN_PROGRESS: R4 / UA-02 runtime fixture. Gate: encrypted credential materializes into the
 read-only volatile mount, channel settings survive, actual application accepts the mount, and
 cold boot restores service ordering without exposing credential bytes.
- ⬜ TODO: R4 / UA-02 restore fixture. Gate: encrypted backup restores usable application state
 and current credential remains valid; record failure handling and sanitized evidence.
- ⬜ TODO: affected regression and documentation gates, then ordered UA-03 integration.

Read-only local libvirt inventory observed the disposable domain shut off. Initial sandbox socket
access was denied; approved read-only retry succeeded. Exact next action: verify fixed domain
identity, start the existing lab VM, and inspect guest prerequisites through pinned SSH.

Runtime prerequisite observation ❌ FAIL: the repaired installer fixture booted with a read-only
root and failed remount service. Installed policy expected etc_t for fstab/crypttab, but both had
root_t; ld.so.cache also had an incorrect label. Remounted only the disposable root writable and
restored /etc labels using installed policy. Subsequent automatic reboot ✅ PASS: writable root,
active remount service and enforcing SELinux. The interrupted installer history may explain these
labels; a clean UA-03 run must establish correct installation without manual repair.

Signed Fedora Podman update ✅ PASS: only Podman changed from 5.8.1 to 5.8.4 (GPG checking enabled).
UA-02 fixture initialization ❌ FAIL: Podman rejected missing /run/user/1001 on the fresh Hermes
account. Moved user-manager startup before first Podman invocation. Gate: live canary runtime
initialization and affected regression suite; previous offline host-source evidence is 🔁 STALE.
Exact next action: complete the repaired canary fixture, then runtime credential and restore gates.

Second identity attempt ❌ FAIL: the user manager was active, but Podman inherited /home/lab and
could not chdir after dropping privileges. The Hermes command helper now uses env --chdir under
the Hermes identity. Live initialization progressed to image installation. Added two regressions.
Affected Python suite ✅ PASS: 121 tests in 18.433s with local socket access. The initial restricted
run ❌ FAIL: 121 tests, one existing broker socket test denied by sandbox; retained as environment
failure, then rerun with approved socket access. Runtime/restore gates remain 🔄 IN_PROGRESS.

Runtime materializer ❌ FAIL: container UID 10000 cannot traverse the host account's mode-0700
home when reading an absolute data path. Enter the data directory in the unprivileged Podman
namespace before setpriv, then read/restore relative paths as UID/GID 10000. Host home permissions
are preserved. Live materializer restart ✅ PASS; overlay inspection confirms .env mounted read-only.
The full installer rerun still fails in a later command; diagnosis is ongoing. Updated Python suite
✅ PASS: 121 tests in 13.399s. Guide checks ✅ PASS: 217 checks. Runtime/restore remain unpassed.

Requested certification model: user supplied gpt6-luna. Official Luna documentation identifies
gpt-5.6-luna; clarification is pending before inference. No provider key has been issued in this
continuation; all guest credential checks use a generated canary.

Full canary runtime installation ✅ PASS after restoring the dependent user manager following
credential-service restart. Requires= had stopped that manager, causing user daemon-reload failure.
Live checks verified matching encrypted/volatile canary, read-only overlay and container root,
healthy runtime, no published ports, and enforcing SELinux.

Semantic encrypted restore ✅ PASS: wrote and loaded a synthetic application configuration marker,
quiesced Hermes, archived data through rootless Podman, used the real Restic backup/dump gate,
observed deliberately changed configuration, restored the archive as the rootless namespace owner,
and verified the original state through hermes_cli.config.load_config plus runtime health/security.
Temporary plaintext stayed in workstation /dev/shm; the disposable Restic repository was removed.

Application rollback ❌ FAIL: tempfile returned an absolute path, reintroducing private-home
traversal after the UID drop. Replaced it with descriptor-relative creation, replace and cleanup,
including directory fsync. Preserve and resume the original fixture backup. Added actual writer
execution with getcwd unavailable to the regression gate. Previous Python pass is 🔁 STALE until
the revised rollback test completes. Exact next action: finish rollback and powered-off boot checks.

Repaired application rollback ✅ PASS: original configuration restored byte-for-byte, rotated canary
credential retained, runtime healthy. Final affected Python gate ✅ PASS: 121 tests in 10.463s.
138 ShellSpec examples passed in 20.53s; 217 guide checks passed. Nonfix lint on isolated copies of
the two edited Markdown files passed; updated ledger/task documentation requires final lint below.
The first lint invocation inherited repository-wide globs (24 files, zero errors); the isolated-copy
method then verified exactly the intended files without source rewrites.

Pre-cold-boot observation ✅ PASS: current encrypted canary matches the read-only runtime overlay,
all channel settings are preserved, runtime healthy, root read-only, no ports, SELinux enforcing.
Confirmed domain shut off before starting the powered-off boot check. Sanitized observations and
source/fixture hashes are in [UA-02 evidence](evidence/2026-09-07-hermes-ua02-runtime.json).
Exact next action: complete automatic cold-boot verification, resolve the requested model identifier,
then perform runtime API acceptance before advancing to clean UA-03 certification.

Powered-off boot ✅ PASS: new boot ID observed through pinned SSH without console input. The
credential service and user manager were active; runtime healthy, read-only root/credential mount,
channel settings preserved, encrypted/current canary matched, SELinux enforcing, and no ports.
Bounded leakage check ✅ PASS: the current canary was absent from container inspection metadata
and the last 200 runtime log lines (stdout and stderr checked in memory; no raw logs reproduced).

R4 / UA-02 remains 🚧 BLOCKED for actual API runtime acceptance: requested gpt6-luna is not the
identifier found in official documentation, which lists gpt-5.6-luna. A clarification is pending;
no substitution, provider issuance, inference, release signing, or production operation occurred.
All independent canary/runtime/semantic restore work above is complete. Retain the repaired lab
fixture powered off and its original rollback backup. UA-03 and UA-04 remain unmet.

Final documentation gate: four-file isolated-copy nonfix lint ✅ PASS; final local-link and
whitespace checks recorded in the accompanying evidence. Exact next action: resolve model ID,
start the preserved lab and isolated broker, verify project model access, and perform real runtime
credential/inference/revocation acceptance. Only then continue ordered clean UA-03 certification.

### 2026-09-07 Luna model selection

Approval reference: user "verify and add it" after identifying gpt-5.6-luna as the documented Luna ID.
Scope: set the unattended controller example and retained disposable runtime to gpt-5.6-luna,
update current guidance, and remove the model-clarification blocker. Production is excluded.
Gate: official model documentation, JSON readback, guest application configuration readback,
affected guide checks, Markdown lint, local links and whitespace.
Source: [official Luna model page](https://developers.openai.com/api/docs/models/gpt-5.6-luna).
Project access and actual inference remain separate unperformed acceptance checks.

Model configuration ✅ PASS: controller JSON selects gpt-5.6-luna with openai-api. The retained
guest was updated using the existing set-model.py helper as container UID/GID 10000. Its saved
model/default/default_model fields and hermes_cli.config.load_config all report gpt-5.6-luna;
manual approval policy remains intact. No inference or provider issuance occurred. The guest was
cleanly powered off afterward. Guide gate ✅ PASS: 217 checks. JSON parsing and model readback
✅ PASS. Model clarification is resolved; actual project access and runtime API acceptance remain
pending. Historical canary observations above retain their original scope.
Exact next action: resume isolated broker/runtime API acceptance using gpt-5.6-luna, then the
ordered clean certification gates. This model-selection change does not certify a release.

Documentation gate ✅ PASS: four-file isolated-copy nonfix Markdown lint, 45 local file links,
and git diff --check. Evidence method: existing set-model.py followed by application-loader and
saved-field assertions; sanitized guest readback is private/hermes-tpm-lab-20260907/luna-model.json.

### 2026-09-07 real API acceptance continuation

Approval reference: user "proceed" after the UA-02 through UA-04 next-step description.
Scope: isolated lab credential delivery, gpt-5.6-luna project access, runtime inference and
provider-side revocation; continue ordered certification only after its prerequisites pass.
Production remains excluded. Existing branch and unrelated changes are preserved.

- 🔄 IN_PROGRESS: UA-02 real API acceptance. Gate: pinned lab identity, healthy runtime,
  selected-model access, actual inference, no credential leakage and confirmed HTTP 401 after revocation.
- ⬜ TODO: UA-03 and UA-04, dependent on UA-02 and their existing acceptance requirements.
- Validation: bounded lab procedures with sanitized JSON evidence, documentation lint,
  affected links and whitespace checks; record exact procedure identities and UTC timestamps.

Initial observation: preserved lab domain is shut off, UUID 4db6369a-2b8b-427f-a47a-a5d83bb40cff.
Sandbox denied the first read-only libvirt query; approved retry succeeded.
Exact next action: start the fixed lab and broker, verify prerequisites, then execute API acceptance
with guaranteed test-lease revocation on failure. No production password is needed for this lab.

Live prerequisite gate ✅ PASS: pinned SSH; boot ID a92c4c01-c116-4d85-b9a5-1814b7839e68;
healthy runtime, read-only root and credential overlay, preserved channel settings, enforcing SELinux,
active credential service/user manager, no published ports, and no canary in container metadata or
the last 200 stdout/stderr log lines. Method: existing `hermes-ua02-verify-runtime.py` through pinned SSH.
Prepared private procedure `procedures/hermes-lab-api-acceptance.py`; Python compilation ✅ PASS.
It checks selected-model access, delivers the test key through captured stdin and pinned SSH,
runs the existing harmless Hermes inference command, restores the prior encrypted credential,
and attempts provider revocation in its finalizer. No raw API responses are emitted.

🚧 BLOCKED: automatic approval review rejected execution before the procedure started. Its stated
reason: explicit authorization is needed for the sensitive bearer credential payload and external
destination `api.openai.com`, despite authorization for UA-02 testing. No test credential was issued,
no API request or inference ran, and UA-03/UA-04 remain gated. This is an approval blocker, not an API failure.
Exact next action: obtain explicit authorization to issue a temporary test-project credential and send
it in HTTPS Authorization headers to `https://api.openai.com/v1/` for model access and harmless inference,
then revoke it. Restart the isolated broker/lab and execute the prepared procedure after authorization.

Closure observation at 2026-09-07 23:04 UTC: lab domain confirmed shut off; both broker units
confirmed inactive (expected `systemctl is-active` exit 3). Initial sandbox bus read was denied;
approved read-only retry confirmed state. No fixture destruction or release signing occurred.
Prepared procedure SHA-256: `5119e1d1825de24c15b9122d0698f32d6ff1776b988b60201f4b9b8288bc442b`.
Validation ✅ PASS on this uncommitted checkout: `devbox run -- ./tests/test-hermes-guide.sh`
(217 passed), isolated-copy four-file nonfix Markdown lint (0 errors), local-link check (45 links),
and `devbox run -- git diff --check`. The private lint/link helpers are the existing
`/tmp/hermes-ua02-lint.py` and `/tmp/hermes-ua02-links.py`. No implementation changes were made;
the canonical execution record captures the operational result and outstanding approval gate.

Explicit egress approval: user "yes, approved and then revoke" authorizes issuing the temporary
test-project credential, sending it via HTTPS to `api.openai.com` for model access and harmless
inference, and revoking it afterward. UA-02 API acceptance is 🔄 IN_PROGRESS; execute the prepared
procedure and verify revocation and lab shutdown before closing this continuation.

First real API attempt at 2026-09-07 23:08 UTC: selected-model access ✅ PASS (HTTP 200);
credential delivery ❌ FAIL before inference; cleanup also reported restoration failure.
Temporary lease `56c680a9f88132f0991ee7e6ad68ccbd` was issued and provider revocation ✅ PASS.
Evidence: private `api-acceptance-56c680a9f88132f0991ee7e6ad68ccbd.json`.
Diagnosis: the test procedure omitted the already documented dependent user-manager restart after
credential-service restart. Repair the private procedure using that established ordering and restore
the lab canary before retry. Preserve the failed result; no application-source change is needed.

Recovery ✅ PASS: the revoked key was replaced by a fresh non-secret canary; credential service,
user manager and healthy runtime restored. The corrected test procedure explicitly restarts the
user manager and stops it before restoring the previous encrypted credential in its finalizer.
Python compilation ✅ PASS. [First-attempt evidence](evidence/2026-09-07-hermes-api-attempt1.json)
retains the failed delivery gate and successful provider revocation. Retry is 🔄 IN_PROGRESS.

Real API retry ✅ PASS, 2026-09-07 23:10:28–23:13:20 UTC. The isolated project returned HTTP 200
for `gpt-5.6-luna`; the real Hermes CLI returned exactly `HERMES_OK` plus newline with exit 0
and empty stderr. Credential delivery, read-only root/overlay, no published ports, bounded leakage
checks and restoration of the prior encrypted canary all passed. Provider revocation ✅ PASS
for retry lease `a61fb03119aed29a8bf10ce348132692` after inference and restoration.
[Sanitized evidence](evidence/2026-09-07-hermes-api-acceptance.json) records the timestamps and
procedure SHA-256 `97044091e484eb1262a4f2f069eb202ada128f3369c2250d0e5abe97c97ba3ae`.

Independent broker metadata check ✅ PASS: both attempt leases have state revoked, role test,
and no remaining encrypted credential file. Enrolled broker source hashes match its manifest;
the reviewed revoke path requires provider deletion followed by HTTP 401 before recording revoked.
UA-02 is ✅ PASS for the repaired isolated fixtures, with prior failed attempts retained.
UA-03 and UA-04 remain ⬜ TODO; no release was signed and production was not accessed.
Exact next action: complete the clean candidate/certifier integration and execute UA-03's exact replay,
no-input boot/update, runtime/inference, restore and negative gates before UA-04 cleanup/signing.

Closure at 2026-09-07 23:15 UTC ✅ PASS: post-restoration runtime check confirmed healthy runtime,
matching canary, preserved channels, read-only overlay/root, enforcing SELinux and no ports or bounded
canary leakage. Lab VM then confirmed shut off; broker service/socket both inactive (expected exit 3).
Documentation validation on this uncommitted checkout ✅ PASS: 217 guide checks, four-file nonfix
Markdown lint, 49 local file links, and `git diff --check`, using the commands recorded above.
Current evidence ledger and deployment task table now reflect UA-02 fixture acceptance.

### 2026-09-07 UA-03 continuation

Approval reference: user "Proceed" after the UA-03 integration, certification and UA-04 sequence.
Scope remains repository implementation and the disposable lab; production is excluded.

- 🔄 IN_PROGRESS: inspect candidate preparation, package replay and enrolled boot prerequisites.
  Gate: sanitized pinned-lab inventory identifies the actual boot manager, package baseline and
  required inputs; preserve the UA-02 fixture and its recovery material.
- ⬜ TODO: implement clean candidate/certifier integration. Gate: meaningful offline rejection and
  ordering tests, affected regression suites, documentation lint, links and whitespace.
- ⬜ TODO: exact-candidate live UA-03 gates; UA-04 depends on all required UA-03 evidence.

Exact next action: inventory the retained lab through pinned SSH and resolve preparation prerequisites
before freezing a candidate. No existing fixture evidence may be relabeled as clean certification.

Pinned-lab inventory ✅ PASS: expected UUID, automatic boot and Secure Boot observed. Prerequisite
gate ❌ FAIL: systemd-boot is not installed, `/EFI/Linux` has no UKI, `sbverify` is missing, and
the enrolled host policy/certificate are absent. Available `/var` space exceeds 20 GiB. The direct
UKI fixture cannot exercise `Host.preflight` or `Host.install_boot` as currently implemented.
Private sanitized inventory: `private/hermes-tpm-lab-20260907/ua03-prerequisites.json`.
The initial sandbox SSH wait timed out because system SSH configuration was inaccessible;
approved pinned-SSH inventory succeeded without changing SSH configuration.

🔄 IN_PROGRESS: disposable boot-manager prerequisite repair. Gate: verify both the previous UKI
and boot manager against the existing authority before writes, retain recovery artifacts, observe
automatic boot through the signed manager, and rerun host prerequisites. Installing verification
tools in this repaired fixture does not establish a clean certification baseline.

Boot-manager enrollment repair ✅ PASS for the retained fixture: source and working UKI signatures
verified before writes, previous direct path preserved, signed-manager installation verified by hashes.
The first procedure used an unavailable direct sudo entrypoint; retry used the existing lab sudo shell.
The subsequent installation reached `installing` but ❌ FAIL at `bootctl set-default`: diagnostics
reported "Not booted with a supported boot loader." Corrected first-boot selection to `loader.conf`;
six offline enrollment tests passed, including rerun, signature rejection and conflicting-input cases.
Automatic powered-off boot ✅ PASS: new boot ID `a05973f5-9bf0-420a-9558-189ad7fecb83`, running
`systemd-boot 259.8-1.fc44`, Secure Boot enabled, pinned SSH. Runtime/canary preservation, read-only
root and overlay, SELinux, no ports and bounded leakage checks passed after that boot.

Stored transaction preparation ✅ PASS: DNF5 downloaded 329 RPMs without changing the installed
inventory (15 installs, 314 upgrades and 314 replaced entries). Baseline SHA-256:
`5e3e0cb5f3e41fa73b200e28e25ea0c93d364a8183acfceaaeec84294b3ad11c`.
🔄 IN_PROGRESS: validate paths, exact RPM identities/signatures and predicted result inventory.
Gate defined before replay: retain a recoverable baseline; verify every package; compare the actual
post-replay inventory and boot/runtime result. Candidate preparation and host replay now share the
transaction validator. Existing 121-test evidence is 🔁 STALE for the subsequent package changes.
The earlier run failed only because sandbox policy denied a Unix socket; approved retry passed
121 tests in 11.381s. Guide checks passed 217/217 before the latest documentation additions.

Exact next action: finish real package verification, preserve the preparation baseline, then resolve
and test the updated-kernel handoff before proceeding to the clean candidate certification matrix.

Interruption checkpoint (2026-09-08 UTC, 2026-09-07 Bogotá): all 329 real RPM signatures and identities
✅ PASS after preserving Fedora's `gpg-pubkey` architecture `(none)` in inventory normalization.
Predicted post-update inventory SHA-256:
`f40cbc4f9054a85fb9635016f58d304ef74f8cc2323927f877b997f821606b1d`.
The earlier `invalid-package-nevra` failure is retained here; nine package tests now pass.
The standalone encrypted-disk preparation backup passed QCOW2 integrity and logical equality checks;
its identity is recorded in `private/hermes-tpm-lab-20260907/ua03-baseline-backup.json`.
The lab was restarted and pinned SSH became ready. The subsequent retained Restic/semantic-restore
execution request was interrupted; no UA-03 restore result or Restic directory exists at checkpoint.
No package replay or new provider operation was performed in this continuation.

Validation ✅ PASS: 121 unattended tests (13.435s), six enrollment tests, nine transaction tests,
138 ShellSpec examples (21.48s), five-file isolated-copy nonfix Markdown lint, 53 local links,
and `git diff --check`. The guide check passed 217/217 before later documentation additions;
rerun that affected documentation gate before closing. Exact commands are the contributor-guide
commands plus `devbox run -- python3 /tmp/hermes-ua03-doccheck.py`.

Exact next action: complete the retained Restic semantic-restore gate, then stage exact package replay
on the preparation fixture, verify its actual inventory, and build/test the updated-kernel UKI handoff.
Clean candidate/certifier integration and the full UA-03 matrix remain incomplete; UA-04 is gated.

Resume reference: user "Resume tasks". The retained Restic semantic-restore gate is
🔄 IN_PROGRESS. Preserve its snapshot and the verified standalone disk copy before package mutation.
Package replay remains dependent on a passing restoration result; production remains excluded.

Retained Restic restoration ✅ PASS: application-loaded seed, deliberately changed state, restored
state/security settings and healthy runtime verified. Encrypted snapshot retained as
`8549804d848fd59a9119d1f186228b4238c98400c4974f727bb4d12996b7e0b6`.
The first exact replay staging ❌ FAIL: DNF5 5.4.1.0 has no `replay --offline` option, either as a
command option or in global position. No offline transaction or reboot marker was stored. Its journal
remains `package-staging`; preserve that failed attempt when resuming. Upstream replay source confirms
that its parser does not expose offline staging.

🔄 IN_PROGRESS: replace the unsupported CLI combination with systemd's documented offline-update
target, retaining strict DNF replay with all repositories disabled. Gate: exclusive updater selection,
marker removal before execution, signature and inventory rechecks, failed/interrupted update records,
and mandatory normal boot after success. No weaker solver or live-repository fallback is permitted.
Reference: [systemd offline-update specification](https://github.com/systemd/systemd/blob/main/man/systemd.offline-updates.xml).
Affected earlier test passes are 🔁 STALE until the new offline runner and host transition checks pass.

Offline-runner gates ✅ PASS: seven focused tests cover competing updater markers, staging failures,
signature failure, wrong result inventory and the subsequent-normal-boot requirement. Transaction
tests pass 9/9; the unattended suite passes 122 tests in 9.525s, including the new host completion gate.
The generated unit adopts the installed Fedora offline service's D-Bus dependency and shutdown
ordering, with a private network namespace and core dumps disabled. Seven focused tests passed again
after that unit adjustment. Live `systemd-analyze verify` passed during staging.

Recovery of the unsupported-flag attempt ✅ PASS: unchanged inventory and absent update state/markers
verified before preserving its root-owned journal as `hermes-ua03-preparation-failed-dnf-flag.json`.
The corrected preparation attempt reached `offline-update-staged` and `reboot-pending` with no terminal
input. 🔄 IN_PROGRESS: verify offline completion, exact resulting inventory, subsequent normal boot
and restored runtime. Do not freeze or certify a candidate until the preparation result is established.

Preparation offline replay ✅ PASS at 2026-09-08 01:14:59 UTC: the actual inventory exactly matches
`f40cbc4f9054a85fb9635016f58d304ef74f8cc2323927f877b997f821606b1d`; the runner recorded completion
and a subsequent normal boot was observed through pinned SSH. Boot ID:
`9996a2c0-7097-4419-a603-faa5d4b431d3`; Secure Boot enabled. The retained recovery UKI still runs
kernel `6.19.10-300.fc44.x86_64`; the newly installed kernel's signed UKI must be built and tested next.
Post-update runtime preservation ✅ PASS: healthy runtime, encrypted/current canary agreement,
read-only root/overlay, preserved channels, enforcing SELinux, no ports and bounded leakage checks.
This is preparation evidence, not clean-candidate certification.

Updated-kernel export first attempt ❌ FAIL: after regenerating initrd, the traditional
`/boot/vmlinuz-7.1.13-200.fc44.x86_64` path was absent. Preserve the partial export. The retry uses
the canonical `/usr/lib/modules/VERSION/vmlinuz` and verifies its exact `kernel-core` RPM ownership
before copying into a fresh export directory. 🔄 IN_PROGRESS: updated-kernel export and workstation UKI signing.

Updated-kernel export and signing ✅ PASS: kernel `7.1.13-200.fc44.x86_64` inputs were
exported with verified RPM ownership and transfer hashes. Signed UKI SHA-256:
`44edb95fe330b997d24a908205de78b8823c332c70162401fd4079f3a5b2d677`.
Evidence: private `ua03-kernel-export.json` and `ua03-uki-build.json`. Boot validation remains pending.
Transaction archive names now permit the literal `+` and `^` used by Fedora RPMs; ten transaction
tests pass. Offline completion is published only after updater cleanup; eight focused tests pass.

Candidate review preserved two superseded candidates: the first stripped the machine-id newline;
v2 corrected that binding but its live preflight ❌ FAIL before UKI installation because the code
expected `tpm2-public-key-pcrs` instead of systemd's recorded `tpm2_pubkey_pcrs` field.
Retained installed/recovery evidence shows PCR7 and signed PCR11 enrollment. The payload check is
corrected without changing enrollment. Validation ✅ PASS: 124 unattended tests in 11.532s using
`devbox run -- python3 -m unittest discover -s tests -p test_hermes_unattended.py` on the current
uncommitted branch, including valid-token acceptance and missing-policy rejection.
Earlier frozen candidates are 🔁 STALE for certification and must not be signed.

Exact next action: freeze candidate v3, install its UKI through its exact payload in a fresh guest
staging directory, then cold-boot and verify the updated kernel, Secure Boot and runtime preservation.
The failed v2 staging directory is retained. Clean UA-03 certification and UA-04 remain pending.

## UA-03 resume: updated-kernel boot validation

Approval reference: user "proceed with UA-03"; recorded 2026-09-08T01:51:43.440846+00:00.
Scope: repository and existing disposable lab certification; UA-04 and production remain gated.

- 🔄 IN_PROGRESS: reconcile retained artifacts and install/test the updated signed UKI.
  Gate: verify candidate bytes and host binding, preserve signed recovery entry, observe automatic
  boot with kernel `7.1.13-200.fc44.x86_64`, Secure Boot, exact inventory and healthy runtime.
- ⬜ TODO: clean-candidate integration and remaining UA-03 acceptance/failure matrix.
- ⬜ TODO: affected regression, documentation lint and evidence synchronization.

Live pinned-SSH inspection confirms the fixed lab UUID, old running kernel, expected post-replay
inventory, signed recovery entry and enabled Secure Boot. Retained export/build records exist,
but the candidate-install record is empty and only the recovery UKI is installed.
The host dispatch policy is absent; full clean-candidate certification cannot yet pass.
Exact next action: validate corrected candidate host binding, install its signed updated UKI,
and observe automatic updated-kernel boot before proceeding to clean certification.

Updated UKI warm and powered-off boots ✅ PASS for kernel, pinned SSH, Secure Boot, exact inventory
and retained-runtime checks. Boot IDs: `52f39ce3-8f91-44b9-9ce2-0eaf728651e8` and
`7c3ae38d-35a6-467a-bb54-a48b196b8149`. Full boot acceptance ❌ FAIL: TPM anchor services
cannot unseal after the initrd phase. The same failure exists in the prior recovery-kernel boot.
A bounded decrypt-to-`/dev/null` probe reports missing PCR signature; the UKI carries one signature
while boot logs confirm later PCR11 phase extensions. No raw credential/debug log was retained.

🔄 IN_PROGRESS: repair installed UKI phase signatures using the normal boot phase sequence.
Gate: retain PCR7/signed-PCR11 and existing keys; confirm TPM service recovery, automatic cold boot,
exact updated kernel/inventory, runtime security and previous-image recovery. This invalidates
the candidate fingerprint and affected build evidence; installer phase policy remains separate.
Exact next action: reproduce missing post-initrd signatures in the real UKI test, fix the builder,
then build and validate a fresh candidate.

Real UKI regression ❌ FAIL before the fix (`1 != 4` distinct PCR policies), then ✅ PASS:
six boot-build integration tests. Corrected image SHA-256:
`1d602560d4ebc2a55987a0d7b7a8d17d816715c4be5f937a74d35f13d804361e`.
Live reboot ✅ PASS: all three previously failed TPM services are active; updated kernel and runtime
isolation/canary preservation pass. Boot ID: `1ef6d4cf-7ea4-4e26-a29d-a16cb5a6b7cb`.

Corrected-image installation initially ❌ FAIL with ENOSPC on the 600 MiB ESP. Boot selection and
signed recovery images remained intact. The old public export was copied with per-file hash/fsync
verification to `/var/lib/hermes-ua03-preserved-esp-export`, then its duplicate ESP files were removed.
Installation retry ✅ PASS. Recovery copies and relocation hashes are retained in the private ledger.
A capacity regression also failed before repair and passed afterward; the host now rejects insufficient
ESP space before writing or selecting a new boot image. Candidate v4 source evidence is 🔁 STALE
for this subsequent host change; its boot-image observations remain preparation evidence only.

Python discovery ✅ PASS: 150 tests in 145.325s, including real disposable disk tests. The later
capacity change requires the running unattended-suite recheck. Exact next action: finish corrected
cold-boot and previous-image recovery checks, then reconcile prerequisites for clean certification.

Corrected cold boot ✅ PASS: `e1f0ee8d-5286-45a9-b52a-dc90cf95f60b`, kernel
`7.1.13-200.fc44.x86_64`, all TPM setup/product services active, exact inventory and Secure Boot.
Previous signed-image recovery ✅ PASS: one-shot boot selected `hermes-enrollment.efi`, reached pinned
SSH with kernel `6.19.10-300.fc44.x86_64` and Secure Boot; corrected image remained the default.
Recovery boot ID: `92d2e8ff-b2f5-4334-a390-193bb20a3147`. A normal reboot back to the corrected
image is in progress; confirm its kernel, TPM services and runtime before leaving the fixture.

The [sanitized preparation evidence](evidence/2026-09-08-hermes-ua03-boot-preparation.json) binds
observations to source hashes and distinguishes them from certifier-owned passing gate records.
Final unattended checks ✅ PASS: 126 tests in 12.975s, including the added capacity regression.
Guide checks ✅ PASS: 217/217. Remaining documentation and ShellSpec checks are in progress.

UA-03 remains 🔄 IN_PROGRESS. The existing controller requests production credentials and requires
already-certified signed input; it cannot substitute for the missing isolated candidate certifier.
The retained fixture also has the post-replay inventory, so exact replay must start from the preserved
pre-update baseline. Do not relabel these preparation observations as clean-candidate acceptance.
Exact next action after final fixture-health verification: integrate the trusted isolated candidate
certifier, freeze current sources, and execute from the preserved baseline with test-only credentials.

Final fixture-health gate ✅ PASS: corrected kernel, all three TPM services active, healthy runtime,
read-only root/credential overlay, preserved channel settings and encrypted canary, enforcing SELinux,
no published ports, and no canary in inspected metadata/bounded logs. Boot ID:
`13b8c141-ebe5-4517-a6d6-519cad6fe1d4`. The lab is running on the corrected default UKI.

Validation ✅ PASS on this uncommitted tree: 138 ShellSpec examples (35.41s), 126 final unattended
tests (12.975s), 217 guide checks, six-file nonfix Markdown lint, 70 local links and `git diff --check`.
Commands: contributor-guide checks and `devbox run -- python3 /tmp/hermes-ua03-final-doccheck.py`.
The earlier 150-test discovery additionally covered disposable disk I/O, enrollment and package tests.
No new provider credential/inference operation, release signing, commit or production operation occurred.

UA-03 remains 🔄 IN_PROGRESS; clean-candidate and negative-matrix gates remain ⬜ TODO.
Exact next action: implement the isolated candidate-certifier integration, freeze the current source
including the ESP-capacity guard, and replay from the preserved pre-update baseline. Preserve both
failed candidate directories, all recovery material and the relocated public export until its gates pass.

## UA-03 completion run

Approval reference: user "proceed until finished", recorded 2026-09-08T02:15:11.921777+00:00.
Scope: complete isolated candidate-certifier implementation and UA-03 acceptance; preserve UA-04
and production gates. Temporary test-project credentials/inference are within UA-03; production
credentials, production deployment, commits and release publication are excluded.

- ✅ PASS: C1 isolated certifier and validation. Gate: fixed lab identity, candidate byte
  verification, test-only credential scope, durable run identity, no fabricated promotion evidence,
  meaningful negative tests, and required offline checks.
- ✅ PASS: C2 preserved-baseline replay. Depends on C1. Gate: retain repaired fixture recovery copy,
  restore exact baseline, run the frozen payload with stdin closed, verify RPM inventory and boot.
- ✅ PASS: C3 full UA-03 runtime/restore/inference/negative matrix. Depends on C2. Gate: all required
  observations bound to the same candidate/run; failures retained; temporary credentials revoked.
- ✅ PASS: C4 final documentation/evidence checks. Depends on C1–C3. Gate: current ledger, tests,
  nonfix Markdown lint, links, source identity and no pending UA-03 gates.

Exact next action: inspect enrollment, candidate and host interfaces; implement the isolated
certifier without adding a production bypass or weakening the release signer.

C1 isolated endpoint/coordinator implemented. The guest endpoint is bound to the fixed domain UUID,
host identity, manifest hash and run ID; it streams and hashes regular candidate files before execution.
Production dispatcher/signing policy is unchanged. The coordinator uses only the test broker role,
volatile credential/archive transfers, encrypted backup receipts and a separate fixed-domain power helper.
Credential cleanup runs after failure and is available independently for interrupted-run reconciliation.

C1 boundary gate ✅ PASS: nine tests cover exact tar transfer, byte/hash/host/path/link/truncation
rejection, fixed lab/nonroot policy and revocation despite guest failure. Existing unattended checks
✅ PASS: 126 tests in 12.907s. Both new wrappers pass ShellCheck and shfmt. These are offline results;
no live certification or enrollment success is inferred. Snapshot guard now uses Python `-B` so
execution cannot add mutable bytecode files to the frozen candidate tree.
Exact next action: preserve the repaired disk, restore the verified pre-update baseline, enroll the
restricted lab endpoint and run the frozen candidate with test-only broker access.

C2 setup failures retained: Nix `chcon` returned unsupported context access; Fedora `/usr/bin/chcon`
verified both images as `virt_image_t` and preserved the label. The initial local helper install lacked
its parent directory; the follow-up creates it explicitly. Isolated Restic initialization then exposed
an inaccessible operator-owned Devbox path. A root-owned executable directory now pins resolved Nix
store tools; the certifier runs with a clean environment and its own working directory. Restic init
passed under the actual certifier UID. No provider credential was issued during these setup failures.

C2 preservation/restore ✅ PASS: the corrected repaired disk is retained separately; the active disk
is a verified logical copy of the pre-update baseline, with its SELinux image label preserved.
Restricted guest enrollment ✅ PASS: separate forced-command key, exact no-argument sudo wrapper,
fixed-domain marker/identity and enrolled candidate hash. Production host policy remains disabled.
A live request from the actual certifier UID rejected the wrong run ID before stage execution.

The initial transient service ❌ FAIL at EXEC because SELinux blocks direct init-domain execution of
Nix `default_t` binaries. No run state or provider credential existed. The certifier now runs in a
bounded supervised scope through its existing user context, with an independent native-Python
credential-cleanup timer. SELinux remains enforcing; no broad policy or Nix relabeling was introduced.
C3 is 🔄 IN_PROGRESS: live run `fa8640ea8e2d4fe6a907ecda12976fe4ebbc3a71e9103cc4bdb876a8c2478f68`.
Candidate fingerprint: `c083055d2a16d5eecb6ef189f7e5ba035a45293c8e7fe6d39a3eedfdcac23d15`.
Exact next action: observe the new certifier's rejection/backup gates, then ordered package/runtime boots.

C3 clean replay ❌ FAIL: candidate v5 selected the updated UKI before RPM replay. The guest entered
emergency mode; offline recovery inspection found only `6.19.10-300.fc44.x86_64` modules and the
replay journal still `staged`. The new kernel had no matching on-disk modules. Bounded shutdown and
ACPI requests did not stop the emergency guest; its CPU was stopped while preserving its disk.
The supervised retry loop was terminated; independent cleanup ✅ PASS for provider revocation,
with candidate/run-bound `credential_revocation.json`. Guest credential restoration failed while
unreachable; baseline restoration will restore the original encrypted credential. No pass is inferred.

Fix gate 🔄 IN_PROGRESS: regression tests first failed for the absent delayed-selection interface;
after implementation 10 offline replay tests pass. Install the UKI without selecting it, run replay
under the existing kernel, verify exact resulting inventory and UKI hash, then select the new entry.
The coordinator also now retries only transient transport errors during boots, preserving permanent
acceptance failures. These changes invalidate v5 source certification; retain v5 and create v6 with
a fresh run. Exact next action: retain the failed disk and run, restore baseline, freeze/enroll v6,
and repeat the full candidate acceptance sequence.

V6 run `27e9fcc4ff716a8485703e18ca94558c41d21743280039eae462ed442c8cf012` was deliberately
interrupted at snapshot, before credential issuance: review found the offline service lacked Python
`-B`, which would add bytecode to the frozen candidate. Its failed journal and disk are retained.
V7 includes both fixes. Gate ✅ PASS: 127 unattended tests (15.382s), 12 offline replay tests
(0.100s), and 10 certifier tests (0.041s). Tests cover delayed selection, failed replay preservation,
changed-UKI rejection, no bytecode writes and permanent-vs-transient boot errors.
V7 fingerprint: `6529cba125d25c15251b21303cba1b389bc90f42947e267de8d775772a6e00c0`.
Run: `071c1a72e5af326711ff036abb7a6d1ccfc04c6a4ca6a9d498636da41171204b`.
Exact next action: finish verified baseline restoration, enroll v7, and run ordered live acceptance.

V7 baseline preservation/restore ✅ PASS: `ua03-cert-v6-failed.qcow2` retained; logical comparison
against the original pre-update baseline passed. Frozen v7 is enrolled under a distinct root-owned
policy and certifier-owned state. Regression ✅ PASS: 138 ShellSpec examples (30.72s), 217 guide
checks. Intermediate documentation lint ❌ FAIL: one 135-character line introduced in the deployment
guide; wrapped without changing meaning. Final lint/link checks remain pending the result update.

V7 live progress: restricted enrollment, rejection/lock gates, encrypted backup byte restoration,
and test credential issuance completed. The guest reached the offline replay service under the
existing kernel and began the RPM update, replacing v5's pre-replay emergency failure.
Enrollment also exposed an operator-access defect: the new SSH drop-in excludes the `lab` operator;
the restricted certifier remains reachable. Required repair gate 🔄 IN_PROGRESS: preserve both
identities in the lab allow-list, verify both pinned keys, and reobserve the candidate after recovery.
No arbitrary-operation action was added to the restricted endpoint to work around that boundary.
Exact next action: finish v7 acceptance/credential cleanup, then repair and verify operator access
through the existing offline recovery procedure before declaring UA-03 complete.

V7 reached `persistence-reboot`: actual frozen `Host.advance` verified exact post-update inventory,
recorded offline completion, a subsequent normal boot, runtime installation/hardening and exact
Hermes CLI `HERMES_OK`. The console independently showed kernel `7.1.13-200.fc44.x86_64`.
This is intermediate progress; persistence, cold boot, semantic restore, scan, revocation and the
operator-access repair must still finish before UA-03 passes.

V7 ❌ FAIL during persistence transition. The coordinator reported guest credential-restoration
failure and overwrote its primary error; provider revocation ✅ PASS with the same candidate/run
binding. No clean-candidate pass is claimed. Offline repair preserved the `lab` operator alongside
the restricted account; pinned operator authentication now passes. Guest inspection confirms
`offline.status=complete` and the updated kernel. A test reproduces a definite host-stage bug:
acceptance ran before checking that the persistence boot ID changed, so a stopping runtime could
trigger rollback. The corrected stage waits for the new boot before bounded runtime health/acceptance.
Eleven focused host-stage tests pass. The coordinator now retains primary and cleanup errors separately;
11 certifier tests pass. The exact v7 primary error remains unknown until shutdown-transport reproduction.
Exact next action: restore the prior credential, run the bounded status-only reboot probe, then freeze
and certify fresh source; preserve v7's failed state and disk.

V7 recovery ✅ PASS: prior encrypted credential restored and runtime healthy; provider revocation
remains proven. Status-only shutdown probe observed successful status → SSH 255 with empty stdout
→ successful status, with no unexpected protocol banner. It did not reproduce an alternate transport
classification defect. The exact overwritten v7 error remains unknown; the host reboot-ordering
regression is independently reproduced and fixed. No broader error retry was introduced.
V8 freezes fingerprint `c3972189b097ed0a47d8ff47d8f093eec1cc9e455c6450fafbe9c85789d45746`.
Gate ✅ PASS: 128 unattended tests (16.059s), 11 certifier tests (0.044s). V8 enrollment preserves
both `lab` and `hermes-certify` in the effective SSH allow-list; verify both keys before issuing a key.
Exact next action: retain v7, finish baseline restore, verify both enrolled SSH identities and run v8.

V8 baseline restore and dual-identity enrollment ✅ PASS. Operator probe observes the original
kernel, no candidate host journal and no offline transaction. The baseline's known old-policy TPM
service failures are not treated as candidate acceptance; updated-UKI TPM services must pass afterward.
V8 run `10043da8a121484e729c1295c9207c8712cb94fa1a3efcc00e06e63c5a211b47` is 🔄 IN_PROGRESS,
with an independent test-credential cleanup timer and fresh encrypted backup repository.
Exact next action: observe the ordered replay/runtime boots and remaining candidate gates.

V8 ❌ FAIL before package deployment: broker issuance was rejected, and cleanup reported unknown
provider revocation. The preserved primary error is `credential-broker-rejected`; guest remained
`backup-verified`. The broker journal is `issuing`, with no account ID or encrypted key.
A separate fixed-project, read-only reconciliation ran as the broker UID using systemd credential
delivery: provider GET returned HTTP 200 with a complete listing and zero matching accounts for
lease `10043da8a121484e729c1295c9207c87`. No key was delivered to the guest. This is account-absence
reconciliation, not fabricated HTTP-401 evidence. The original rejection cause remains unknown.
The failed run, disk and reconciliation record are retained; its cleanup timer is stopped.
A fresh v9 attempt uses unchanged payload source, a new release/run and original baseline.
Exact next action: restore, enroll and verify v9; repeat full acceptance without reusing v8 live gates.

V9 verified baseline restore ✅ PASS; v8 failed disk retained. Frozen v9 fingerprint
`13aefaacc776ebf182fa4d6091f877167fc6deb0faedacd65749301b6b22f40b`; all payload/RPM/UKI
hashes equal the tested v8 source. Run `f7fc227e7ded428e339fbd8770bc7fb504a3ae27e1b0ebf794d8bcdbf35dc6a2`.
Exact next action: verify both SSH identities after enrollment, then run full certification.

V9 live credential issuance/delivery ✅ PASS; the prior broker rejection did not recur. Rejection,
lock and verified encrypted-backup checks completed before issuance. The actual candidate host
reached `reboot-pending`; fresh offline replay is underway. All four failed/interrupted attempts
and v8 provider account-absence reconciliation are preserved separately.
Exact next action: observe replay completion, ordered runtime acceptance and persistence reboot.

V9 launcher exited with signal status 143, but the systemd scope remained active and the actual
certifier process continued at `reboot-pending`; guest console confirmed active RPM replay. No
restart or new credential was issued. A bounded private progress sink now holds/drains the existing
stdout/stderr pipes, retaining only allowlisted JSON progress and hashes of unexpected output.
The certifier's durable state remains authoritative. Candidate and executed certifier code are unchanged.
Exact next action: monitor the active scope and durable state through completion, then verify cleanup.

V9 post-update operator observation ✅ PASS: kernel `7.1.13-200.fc44.x86_64`, boot ID
`5cddf15e-9556-41fa-8fb7-ef5a3f03f70e`, offline replay `complete` at epoch 1788839302,
and host phase `runtime-pending` (after exact inventory verification). Firmware handoff was slower
than v7 but progressed without intervention. The only failed unit reported is the baseline's
VM-inapplicable `mcelog.service`; updated TPM services no longer appear in the failed-unit list.
Full TPM/runtime observations remain mandatory in the certifier. Exact next action: runtime acceptance
and the corrected persistence-reboot stage, then cold boot, restore, scan and credential cleanup.

V9 reached persistence reboot after successful first inference. The subsequent operator observation
shows new boot ID `b15c4e77-016e-45e3-98b9-d891888ce4e5` and the expected updated kernel;
the coordinator remains active at the persistence gate while bounded runtime startup completes.
The mcelog journal explicitly reports unsupported virtual AMD processor family 23; this pre-existing
hardware-diagnostic limitation is outside Hermes runtime acceptance and is retained, not silently fixed.
Exact next action: require second acceptance and `closed`, then independent cold-boot observations.

V9 ordered deployment and inference gates ✅ PASS at epoch 1788839799. Observed stages are exactly
`reboot-pending`, `persistence-reboot`, `closed`; installed inventory is
`f40cbc4f9054a85fb9635016f58d304ef74f8cc2323927f877b997f821606b1d`.
The actual Hermes CLI passed before and after the persistence reboot. The independent warm
observation also passed; the certifier has begun the powered-off cold-boot gate.
Exact next action: cold boot, closed deploy/upgrade reruns, semantic Restic restore, scan and revocation.

V9 cold-boot and runtime gates ✅ PASS: cold boot ID `bd5ff55d-3c66-41cb-aa26-1d611c937620`
differs from the warm/persistence boot. The bound observer passed signed UKI selection/hash,
expected kernel and RPM inventory, Secure Boot, active TPM units, SELinux, runtime health,
read-only root/credential overlay, no published ports, hardened application configuration and bounded
credential-leak checks. Exact next action: finish closed reruns, semantic restore, scan and revocation.

V9 reached `ua03-acceptance-passed`: semantic application restore and the real image scan passed,
with all recorded negative/rerun checks passing. This is not final completion until prior-credential
restoration and provider-side revocation succeed. Exact next action: require cleanup completion,
verify both SSH identities and final runtime, publish sanitized bound evidence, and close C1–C4.

V9 live run ✅ PASS: durable `ua03-complete`, prior credential restored and bound provider revocation
passed at epoch 1788840125. The supervised scope exited successfully and its redundant cleanup timer
was stopped. C4 post-check initially ❌ FAIL because its parser expected one `sshd -T` allow-list
line; actual output correctly reports one line per user. The helper now flattens those lines and
requires exactly the two expected users. Evidence assembly correctly refused the missing post-check.
No guest policy or certified code changed for this parser repair. Exact next action: rerun final
access observation, assemble evidence, update ledgers and finish documentation checks.

C1–C3 ✅ PASS with [sanitized candidate/run evidence](evidence/2026-09-08-hermes-ua03-certification.json).
Final access verification passed after cleanup: both pinned SSH keys, exact allow-list, unchanged
candidate/code hashes, active TPM services, expected kernel/inventory, healthy isolated runtime and
restored read-only credential overlay. All seven UA-03 gate records match the same fingerprint/run.
The scope is inactive with success and the redundant cleanup timer is stopped. Prior failed attempts
and recovery disks are retained; no UA-04 destruction/purge/signing evidence was manufactured.

C4 🔄 IN_PROGRESS: current ledgers updated; final documentation, links and whitespace checks remain.
Exact next action: run final document checks, then mark UA-03 complete. The next operational gate is
UA-04, followed by explicitly authorized UA-05. The broader plan remains open for those gates and
automatic candidate scheduling integration; production recovery/password-rotation requirements remain.

### UA-03 completion

✅ PASS: C1–C4 and UA-03 completed at 2026-09-08T04:09:33.036619+00:00.
The seven required UA-03 gates, nine negative/rerun checks, final access verification and source
identity checks passed for the single v9 candidate/run. No UA-03 acceptance gate remains pending.

Final verification on `codex/hermes-unattended`, under Devbox: 217 guide checks; nonfix Markdown
lint on six affected documents; 68 local links and both new anchors; `git diff --check`; bound-evidence
consistency and secret-field exclusion. All ✅ PASS. Earlier unchanged-source results remain valid:
128 unattended tests, 12 offline replay tests, 11 certifier tests and 138 ShellSpec examples.
The successful scope is inactive and no UA-03 cleanup timer remains. Candidate and executed source
hashes are retained in the evidence; this checkout is uncommitted.
Evidence SHA-256: `389a50c10428736893cc98138e57bc58c45668e0a297f3cfec3b4f803e460246`.

UA-04 purge/destruction/signing and UA-05 authorized production enrollment remain pending; automatic
candidate scheduling integration remains separate. Failed attempts, recovery material and the tested
candidate are retained. The scan passed the approved advisory policy with findings preserved.
The overall plan remains open. Exact next operational action: execute UA-04 in the task-ledger order;
production enrollment cannot precede its required evidence and authorization.

### UA-04 cleanup and signing

Approval: user “proceed UA-04 cleanup and signing”, reaffirmed “keep going”, 2026-09-08 UTC.
Scope: the isolated UA-03 lab, its disposable data and recovery copies, and exact-candidate release signing.
Production enrollment, Git commits and pushes remain outside this approval. Preserve sanitized failure
evidence and the certified candidate; remove disposable credential/data copies only after inventory.

| Task | Dependency | Progress | Validation gate | Result |
| --- | --- | --- | --- | --- |
| D1 | UA-03 | ✅ PASS | Verify candidate hashes, seven bound gates, revocation and cleanup inventory | ✅ PASS |
| D2 | D1 | ✅ PASS | Purge lab application/credential state and disposable backups; verify absence | ✅ PASS |
| D3 | D2 | ✅ PASS | Remove exact lab domain, disks, firmware and TPM state; verify absence | ✅ PASS |
| D4 | D3 | ✅ PASS | Enrolled isolated signer issues exact release; independently verify signature and payload | ✅ PASS |
| D5 | D4 | ✅ PASS | Update ledgers, lint affected documents, check links and whitespace | ✅ PASS |

The existing branch is `codex/hermes-unattended` with pre-existing uncommitted implementation.
Preflight is read-only so far. Required UA-03 evidence is recorded as current; live identity validation
and precise cleanup inventory remain. Exact next action: validate D1 before dependent cleanup.

D1 ✅ PASS at epoch 1788842046: `/tmp/hermes-ua04-preflight.py`, run through Devbox with local sudo,
verified 347 candidate files, all seven original gates and executed source identities. The exact lab
UUID and dedicated image directory match. Six issued test leases are revoked with encrypted copies
absent. The interrupted v8 issuance has a complete HTTP 200 provider listing with zero matches,
recorded at epoch 1788838352; no key was saved. Evidence: private `ua04-preflight.json` and the
existing v8 reconciliation record. This reuses provider evidence; it is not a new provider request.

The enrolled signer differs only in its relevant release path validator: the certified version accepts
RPM filenames containing `+` and `^`. Its signing, finalization and packaging modules match. Before
signing, update that isolated verifier to the exact tested hash; preserve the authority and role boundaries.
D2 next action: stop the guest runtime, purge its Hermes identities/data/credentials and fixture privilege,
then remove exact disposable backup/key copies. Retain source, candidate and sanitized observations.

D2 ✅ PASS: guest purge completed at epoch 1788842197, using the pinned lab SSH key and UUID guard.
The Hermes and certifier guest accounts, application home, credentials, runtime configuration and
fixture sudo rules are absent; the user runtime stopped. Local purge verified 29 exact disposable
backup/key paths absent and no broker encrypted leases. Evidence: private `ua04-guest-purge.json`
and `ua04-data-purge.json`; procedures `/tmp/hermes-ua04-{purge-guest,run-purge,purge-local}.py`.
The isolated signer's five dependency hashes now match the certified source; the prior verifier is retained.
Exact next action: D3, remove the identified VM, its dedicated storage and retained disposable recovery disks,
then independently check domain, firmware and TPM absence. Logical removal does not claim media sanitization.

D3 ✅ PASS at epoch 1788842297: `/tmp/hermes-ua04-destroy.py` used the direct local-hypervisor
exception. The UUID-guarded domain was stopped and undefined with NVRAM/TPM removal. All 16
inventoried paths, the dedicated storage pool, and matching QEMU/swtpm processes are absent.
Removed files total 68,979,458,048 logical bytes, including failed/recovery disks and installer media.
Evidence: private `ua04-destruction-inventory.json` and `ua04-vm-destroyed.json`; failure observations remain.
Exact next action: bind these two observed gates to the original run, stage the certifier-owned handoff,
invoke the enrolled isolated signing service, and verify the complete archive independently.

D4 ✅ PASS: enrolled `hermes-lab-sign.service` exited successfully (status 0). Release issued at epoch
1788842376 and independently verified at 1788842421 as deployment UID 986. All 356 files, signature,
nine gates, run/fingerprint identity and deployment-role key/output restrictions passed. Archive SHA-256:
`618fd2bbb7bebecc313fc9873bb6a9c1396c24d2b36b9183c41e88f44f5dc559`.
The exact release remains bound to the lab host. No production operation occurred.

Final control inventory found the empty libvirt pool definition still active and the reusable lab broker
running after signing. D3 proved storage-directory absence, not pool-definition absence. Ancillary cleanup
removed the pool definition/autostart, stopped the broker/socket, and removed the temporary local power
sudo rule/helper. These follow-up operations do not change the signed domain/disk/TPM observations.
The follow-up procedure then stopped on ❌ FAIL from `visudo -c`; investigate before final closure.
No signing evidence or archive was rewritten. Exact next action: classify the sudo validation failure,
finish ancillary absence checks, publish sanitized evidence and complete D5 document validation.

D5 🔄 IN_PROGRESS: [public UA-04 evidence](evidence/2026-09-08-hermes-ua04-cleanup-signing.json) and
current readiness/task ledgers now reflect the signed lab-bound release. Ancillary cleanup ✅ PASS
at epoch 1788842523: pool definition absent, broker/socket inactive, runtime admin credential absent,
power helper/rule absent and zero active lab units. Failed transient-unit results were saved before reset.
Retain reusable inactive enrollment, signing authority, certified artifacts and historical observations.

The default sudo check ❌ FAIL is classified outside this change: `/etc/sudoers.d/cloudops` is mode 0644,
not 0440. Its contents and mode were not changed. `visudo -c -f /etc/sudoers` ✅ PASS verifies syntax
of the remaining policy. No additional sudo privilege was added. Exact next action: run guide, nonfix
Markdown, local-link, evidence consistency and whitespace checks; then close UA-04 while UA-05 stays pending.

### UA-04 completion

UA-04 D1–D5 ✅ PASS on 2026-09-08 UTC. Exact release `ua03-cert-20260908-05` was signed by the
isolated enrolled authority and independently verified as deployment UID 986. The selected archive
is `/var/lib/hermes-lab-unattended/releases/selected.tar`; first-use expiry is 2026-09-09 04:39:36 UTC.
The [public evidence](evidence/2026-09-08-hermes-ua04-cleanup-signing.json) records exact hashes,
observed cleanup, preserved enrollment, validation and the ancillary-cleanup ordering.

Validation at epochs 1788842630–1788842633, Devbox, `codex/hermes-unattended` uncommitted checkout:
217 guide checks, six-document nonfix Markdown lint, 72 local links, `git diff --check`, archive SHA-256
and signed/public evidence equality all ✅ PASS. Logs are private `ua04-{guide,markdown-links,whitespace}.log`
and `ua04-document-validation.json`. No repository runtime source changed during UA-04; previous offline
regression evidence remains applicable. The installed signer verifier now matches the certified source.

The old `repo-docs-sync/scripts/diff_docs.py` dependency is absent, so that broad audit was not run.
The replacement focused audit checks current readiness and task status against the signed evidence,
production gate and source gate schema. Final closure-text lint and focused audit are recorded in
private `ua04-final-document-check.json`; their completion is required for this closing entry.

Remaining limitations: lab host binding, retained advisory findings, logical deletion rather than
physical sanitization, and the unrelated default sudo permissions failure (explicit syntax check passed).
No production changes, commits, pushes or PR modifications occurred. U07 disposable certification is
complete. The broader plan remains open for U06 scheduling integration and UA-05 production prerequisites.
Exact next operational action: prepare UA-05 enrollment only under explicit production authorization,
with documented password rotation and hardware boot/recovery gates; this lab-bound archive cannot
be applied to a different host.

### Commit and push delivery

Approval: user “Commit and push”, 2026-09-08 UTC. Scope: the existing unattended feature branch,
its implementation/tests, documentation and sanitized UA-01–UA-04 evidence. Private lab material,
release archives and production changes remain excluded.

| Task | Progress | Gate | Validation |
| --- | --- | --- | --- |
| G1 | ✅ PASS | Review exact staged scope, secret scan, applicable offline suites and hooks | ✅ PASS |
| G2 | ✅ PASS | Create Conventional commit with existing Git signing identity; verify commit | ✅ PASS |
| G3 | ✅ PASS | Push existing feature branch without force; verify remote SHA and clean checkout | ✅ PASS |

Preflight: `codex/hermes-unattended`, origin `securexai/mikrotik`; existing pending feature changes
only. No commit-signing override is saved globally. Exact next action: stage the reviewed feature
paths, validate the staged artifact and run required checks before committing.

G1 validation: 167 Python tests and 138 ShellSpec examples ✅ PASS. Staged inventory contains 85
feature files (under 1 MiB total), no private paths, no large binaries, valid Python/JSON, and clean
whitespace. The evidence screenshot was inspected. Existing source certification remains unchanged.

Initial secret checks retained ❌ FAIL results: Gitleaks flagged 16 evidence SHA-256 mappings, and
the repository grep heuristic flagged variable assignments, credential paths and synthetic fixtures.
Each Gitleaks finding was verified as a named source-file hash. A temporary invocation-only hook
configuration replaces the grep heuristic with Gitleaks 8.30.1, allowing only those 16 reviewed
fingerprints after asserting their exact staged lines are unchanged. The reviewed scan ✅ PASS;
all other pre-commit, commit-message and pre-push hooks remain enabled. Repository policy is unchanged.

ShellCheck, shfmt, Markdown lint (24 maintained documents) and branch checks ✅ PASS in the initial
hook run; the actual commit repeats the hooks with the reviewed scanner. Private logs and the exact
reviewed findings are retained under `private/hermes-tpm-lab-20260907/commit-*`. The first Nix scanner
lookup failed to reach its registry, then recovered through cache and fetched Gitleaks successfully.
Exact next action: create and verify the signed feature commit, push without force, verify remote SHA.

G2/G3 ✅ PASS: signed feature commit `2406296614f531d62896603b716c0f2bd3cbe92f` was pushed without force to
`origin/codex/hermes-unattended`. `git verify-commit` passed against the existing Git signing public
key; `git ls-remote` matched local HEAD and the working tree was clean before this closure entry.
The initial remote read failed transient DNS resolution; subsequent resolution and push succeeded.
Pre-push checks passed: 115 RouterOS, 52 Nix guide, 217 Hermes guide checks, 55 Hermes ShellSpec
examples and feature-branch guard. Full Hermes/VM ShellSpec had already passed 138 examples.

This closure entry is delivered in a separate signed documentation commit under the same authorization.
Exact next action: push and verify that bookkeeping commit; afterward no Git delivery gate remains.
UA-05 production enrollment and U06 scheduler integration remain outside this completed Git delivery.

### U06 scheduled candidate and certification continuation — 2026-09-08

Approval: user “proceed” after the proposed U06 scheduler integration step. Scope is reversible
repository implementation and offline validation on `codex/hermes-unattended`; no production changes,
service activation, destructive lab operations, provider writes, commits or pushes are included.

The current certifier requires exact per-run guest enrollment. The previous UA-04 fixture was destroyed.
Preserve that boundary: automate freezing enrolled public inputs and invoking the isolated certifier,
with a prepare-only enrollment seam, durable interruption detection, independent credential cleanup and
no implicit signing/deployment trigger. Fully automatic fixture provisioning/enrollment and UA-04 cleanup
remain prerequisites for an end-to-end repeating release pipeline; do not invent their evidence.

| Task | Dependencies | Progress | Validation gate | Gate status |
| --- | --- | --- | --- | --- |
| S1 | Existing prepare/certify interfaces | ✅ PASS | Strict policy, window, immutable run binding, lock, failed/interrupted replay tests | ✅ PASS |
| S2 | S1 | ✅ PASS | Closed-input certifier invocation, cleanup after failure/timeout, service/timer verification | ✅ PASS |
| S3 | S1–S2 | ✅ PASS | Affected Python suites, Hermes/VM ShellSpec, guide checks, nonfix Markdown, links and diff hygiene | ✅ PASS |
| S4 | S3 and fresh enrolled disposable fixture | ✅ PASS | Live service TPM/API run and dedicated cleanup evidence; signing excluded | ✅ PASS |

Historical UA-03/UA-04 passes remain bound to their original artifacts; they do not certify this scheduler.
Affected guidance: `docs/HERMES_UNATTENDED_DEPLOYMENT.md`, contributor check reference and current task ledger.
Next action: implement S1 and S2, then run S3. No live claim may be made before S4 passes.

S1/S2 implementation: `schedule.py` prepares a selected recipe, binds policies and frozen bytes in a private
journal, and invokes the isolated certifier with closed stdin. It retains failed/interrupted state, checks
the maintenance window twice, prevents concurrent/duplicate execution, and invokes credential cleanup after
failure or timeout. The service independently repeats cleanup on stop and emits fixed local failure events.
UA-03 completion requests attention for UA-04; no signing or deployment transition is added.

Validation so far, 2026-09-08 UTC, Devbox on this feature checkout: 189 Python tests ✅ PASS, including 22
scheduler tests and an actual closed-stdin subprocess. The first expanded scheduler test run ❌ FAIL was a
SyntaxError in a newly added test fixture string; corrected the quoting before the 189-test pass.
The first bundled `systemd-analyze verify` ❌ FAIL could not resolve America/Bogota or `sysinit.target`.
The installed Fedora validator through Devbox (`/usr/bin/systemd-analyze verify --man=no` on all three new
units) ✅ PASS. No unit was installed or activated. S3 next action: finish existing suites and document checks,
record artifact hashes and outcomes, then retain S4 as the outstanding live gate.

S3 ✅ PASS at 2026-09-08 12:56 UTC, base `4a19d3f5c04f7ec927c85b586511a969933b96a9`, uncommitted feature
checkout. The [offline observation](evidence/2026-09-08-hermes-scheduler-offline.json) records commands,
source/test/unit SHA-256 identities, actual results and retained failed attempts. The affected Python run
passed 189 tests. Review then replaced the environment-only bytecode setting with explicit `-B` because
`-E` ignores Python environment settings; the 22 scheduler tests and installed-systemd unit verification
passed again. The other 167 Python tests are unaffected by that scheduler-only change. Existing checks:
138 Hermes/VM ShellSpec examples and 217 guide checks passed. Four-document nonfix Markdown lint,
56 local links, tracked diff hygiene and new-file whitespace checks passed. No shell source changed,
so ShellCheck/shfmt are ➖ N/A for this continuation.

The first document check's overlong line and the direct Devbox calendar wildcard expansion are retained
as ❌ FAIL observations; the corrected nonfix lint and argument-vector calendar check both ✅ PASS.
The timer resolves to Sunday 2026-09-13 02:00 America/Bogota. Final closure text and its new evidence link
are checked after this entry; that focused recheck supersedes the earlier document/link count.

U06 remains open. This implementation schedules an explicitly enrolled recipe and preserves the exact
per-candidate guest enrollment requirement. It does not yet automate fixture provisioning/enrollment or
UA-04 purge/destruction. There is no automatic transition from UA-03 to signing. The previous fixture's
recorded destruction prevents reusing its historical live evidence for S4; no live inventory was queried
in this continuation. No service activation, privileged operation, provider mutation, production action,
commit or push occurred.

Exact next action: prepare and authorize a fresh disposable fixture run for S4, including test-provider
credential issuance/revocation and dedicated-fixture cleanup, then validate the scheduler under its actual
service identity and sandbox. Those external writes and destructive cleanup require explicit operational
authorization under repository rules. Full repeating lifecycle closure additionally requires implementing
and validating automatic fixture enrollment and UA-04 cleanup without relaxing their trust gates.

### S4 live scheduler validation — 2026-09-08

Approval: user “proceed” immediately after the explicit S4 proposal covering fresh disposable TPM lab
creation/enrollment, actual service-identity/sandbox validation, test-provider credential operations,
revocation, recovery and dedicated-fixture cleanup. These lab operations are now authorized. Production,
Git delivery and release publication are excluded. Preserve existing pending S1–S3 changes and history.

| Task | Dependency | Progress | Acceptance gate | Validation |
| --- | --- | --- | --- | --- |
| L1 | S3 | ✅ PASS | Empty domain inventory, verified media, resources, retained roles and fresh private inputs | ✅ PASS |
| L2 | L1 | ✅ PASS | Fresh TPM/Secure Boot install, pinned operator access, signed boot manager, offline recovery and baseline | ✅ PASS |
| L3 | L2 | ✅ PASS | Install reviewed scheduler under isolated lab identity; real outside-window deferral, exact recipe/guest enrollment | ✅ PASS |
| L4 | L3 | ✅ PASS | Actual scheduled UA-03, failure cleanup and independent credential reconciliation | ✅ PASS |
| L5 | L4 or failed-run recovery | ✅ PASS | Revoke keys, purge only fresh fixture state, destroy exact VM/storage, stop temporary lab services | ✅ PASS |
| L6 | L1–L5 | ✅ PASS | Sanitized evidence, documentation and affected validation reflect actual outcomes | ✅ PASS |

L1 observations: local libvirt inventory is empty, available memory is 9,973,460 KiB and free repository
storage is 382,375,661,568 bytes. Local cloudops noninteractive sudo is available; no production/aicowork
account is involved. Reusable lab broker/signer records remain; destroyed guest keys and storage must
not be resurrected from historical evidence. Fresh private material will use a separate ignored directory.

The scheduler permits Sunday 02:00–04:00 America/Bogota; today is Tuesday. Current authorization does
not explicitly change that policy. Prepare the fixture and verify actual deferral first; successful
outside-window scheduler execution needs a separately recorded lab-only exception or the next window.
Do not fake the clock or replace a deferral with certification evidence. Exact next action: verify
retained public media, create fresh fixture keys and firmware, then run the TPM staging creator.

L1 integration finding: the creator previously let libvirt choose a random UUID, while the certifier
and power helper require the fixed lab UUID. Bind only TPM-profile creation to that existing UUID before
launching the new fixture. The VM guide is updated alongside it. Affected shell validation and VM contract
checks must pass before creation; their prior observations are 🔁 STALE for this changed creator.
A role inventory probe initially used an assumed broker account name and failed; actual retained broker
identity is `hermes-lab-credentials` (UID 985), with certifier UID 987 and signer UID 992. No role was changed.

L1 ✅ PASS: the Fedora checksum signature was verified against the retained keyring and pinned fingerprint,
and the complete DVD SHA-256 matches the expected release. Kernel/initrd were freshly extracted from
that verified DVD. Fresh separate Secure Boot/PCR keys, recovery and operator SSH keys were generated
privately; signed installer sections/signature and enrolled 4 MiB firmware were verified by existing builders.
The dedicated lab pool was newly created with existing narrow ownership/SELinux conventions. Evidence is
private `hermes-scheduler-lab-20260908/{media,installer-build,firmware-build}.json`; no secret was printed.
Creator ShellCheck, repository shfmt and 83 VM ShellSpec examples ✅ PASS. Next: create the fixed TPM VM,
observe installation shutdown, then verify the installed marker and recovery-unlocked filesystem before boot.

L2 is installing. The first direct creator invocation failed before media/VM creation because an EFI tool
was unavailable in its shell; the Devbox invocation successfully built/read-back-verified media and started
the fixed VM. Installer diagnostic probes retain only structured status, never raw console output.

Preparation usability repair: explicit `--prepare-only` now permits local candidate freezing outside the
maintenance window. This performs no guest or provider operation. Automatic runs and actual certification
still defer outside the approved window. Added a regression proving later ordinary execution defers; affected
scheduler evidence is 🔁 STALE until that suite passes. The lab-only timing exception remains unanswered.

Service-tooling prerequisite: the host system PATH lacks Restic and Trivy, while retained isolated binaries
exist under root-controlled lab tooling. Add support for a root-owned `bin/` beside installed scheduler code;
reject unsafe directory ownership and preserve the fixed environment. This avoids changing global executables
or inheriting the operator's Devbox PATH. Two new boundary tests cover rejection and exact PATH construction.
The local preparation regression passed (23 tests); scheduler tests must repeat after this tooling repair.

Current scheduler regression ✅ PASS: 25 tests after the local-preparation and enrolled-tooling repairs.
S3's prior aggregate evidence is marked 🔁 STALE pending L6 closure for the updated files. L2 installer
progress confirms 651 package installations, 432 configuration actions and no completed TPM stage yet.
Exact next action: allow installation to finish, then run the prepared offline-recovery and signed-UKI
handoff procedures; do not start provider operations before the fixture and enrollment gates pass.

L2 installation ✅ PASS at 2026-09-08 13:24 UTC: creator completed after 1,035 seconds, observed guest
shutdown and detached both installer devices. Live domain UUID matches the certifier/power-helper binding.
Offline recovery and the installed UKI handoff are now running; boot and runtime acceptance remain pending.
The retained broker is test-only with no encrypted lease files. Six records are revoked; one older issuing
record has a separate completed HTTP-200 reconciliation with no matching account. This is recorded history,
not a new provider-side query. No provider key has been issued in S4. Next: verify recovery readback and
fresh pinned SSH, then installed signed-UKI boot.

L2 boot/runtime/restore checks ✅ PASS: offline recovery opened the fresh encrypted disk; pinned SSH
first boot succeeded without console input. A subsequent cold boot selected the exact enrolled signed
boot manager/UKI with a new boot ID, Secure Boot, enforcing SELinux and all three TPM services active.
The isolated runtime is healthy with a canary credential on a read-only mount and application-loaded
security configuration. A consistent Restic snapshot was encrypted, independently dumped, and restored
after deliberate application-state damage; the application reloaded the original marker and security
settings. Its encrypted recovery snapshot is retained through the preparation mutation.

The new baseline differs from the retained old one. A fresh 332-RPM transaction was stored without changing
installed packages; signatures and expected inventory were verified. Next: download the verified bundle,
shut down and preserve/compare the complete preparation disk, then replay packages and build the updated UKI.
No OpenAI credential has been issued. L2 is not closed until the resulting baseline/boot preparation completes.

L2 preparation checkpoint (2026-09-08): the verified 332-RPM bundle was downloaded and validated locally.
The powered-off baseline backup passed qcow2 check and logical disk comparison; identity is retained in
private ua03-baseline-backup.json. The first SSH readiness probe failed because product_uuid is root-only;
pinned SSH independently passed, and the root-guarded replay staged successfully. A second probe attempt
remained pending while package replay rebooted; the helper now uses the enrolled sudo shell. The initial probe failure
is not a guest boot failure. Exact next action: observe offline replay completion, export updated boot
inputs, build the signed candidate UKI, and restore the verified preparation baseline before certification.
The lab timing exception is still pending; no provider credential has been issued.

L6 interim checks: 138 Hermes/VM ShellSpec examples and 217 guide assertions passed.
Markdown verification first rejected the temporary configuration filename; after correcting its name,
the tool reported 24 files and zero errors. Git status shows no additional paths changed.
The aggregate Python discovery includes the optional disposable libguestfs disk integration and is still running.
The second readiness probe timed out during the offline boot; the replay observer remains the authoritative
completion check. Exact next action remains L2 replay observation and updated UKI preparation.

L2 offline replay ✅ PASS: ua03-replay-observation.json records a new boot ID, exact expected
package inventory 09d32a1b717e5f7c8806772182183c4078233dc342c2a82bf5eb5cb7f885412d,
Secure Boot enabled, and require_complete success. The running enrollment kernel is still 6.19.10;
updated UKI construction and boot certification remain distinct pending steps. Export is now running.
L6 aggregate Python ✅ PASS: 193 tests, including the disposable libguestfs disk integration, in 231.103s.
Installed systemd unit validation and focused five-file Markdown lint passed; git diff --check passed.
Exact next action: finish export/build, restore the checked baseline, then install isolated scheduler units.

L2 ✅ PASS: updated kernel 7.1.13-200.fc44.x86_64 was exported and signed UKI
b01f8ee85a5c6ff777f9f55767159590772c9cb4922078414ff872ccc0d757e8 passed builder verification.
The baseline disk was restored after qcow2 check and logical comparison, preserving the updated disk.
Pinned SSH returned and baseline inventory exactly matched 88687312ab0603300b8f5a4abcbf3846ac80d1f99af3592bd222f00194faa73a.
The first immediate runtime probe failed; diagnosis found credentials active and container health starting.
Using the existing bounded health wait passed runtime health, canary, read-only credential overlay and
application configuration checks. Private evidence: ua03-uki-build.json, baseline-restore.json,
baseline-result.json, runtime-diagnose-result.json and runtime-observe-result.json.
Next: L3 install isolated scheduler, verify actual off-window deferral, then freeze the exact candidate.

L3 ✅ PASS: installed isolated unit hermes-lab-scheduler-80da1dacb547 returned deferred under the real
Tuesday clock and ExecStopPost returned no-certifier-state. Its prepare unit completed under the service
sandbox, freezing candidate ccd489a8cd55a20e9caf6616004c3d55bf368e7fc94bbb3bf635b057b0dc36eb.
The guest endpoint was enrolled to that candidate and run; pinned operator access remained available.
The restricted key rejected a wrong run ID. The first test frame omitted its required newline and was
rejected as invalid-lab-frame; the corrected frame returned invalid-lab-run as expected. No certifier
state or provider credential was created. Evidence: private scheduler-run.json, guest-enrollment.json,
enrollment-check.json and the two isolated unit journals. No timer is installed or enabled.

L4 🚧 BLOCKED pending the separate one-time lab timing decision. The approved Sunday 02:00–04:00
America/Bogota policy remains unchanged; no out-of-window certification exception was inferred.
L5 remains dependent on certification/recovery. The prepared fixture is retained for continuation,
with shutdown requested and all one-shot scheduler units completed. No broker activation, provider key
issuance, production operation, commit or push occurred. Candidate validity is 24 hours: if it expires,
prepare a fresh run and rebind guest enrollment before certification; do not reuse expired evidence.
Exact next action: resolve the lab timing decision; then implement/test any explicitly approved bounded
exception, restart the exact fixture, run L4 success/failure cleanup and reconciliation, then L5/L6.

Pause-state verification: virsh domstate confirms the fixture is shut off.

Final checks: diff whitespace passed. Concurrent Devbox validation briefly failed before lint because
its generated .cmd.sh disappeared; a sequential retry passed focused five-file Markdown lint.
Use sequential Devbox invocations for remaining checks to avoid that shared generated-script race.

### L4 timing exception approved — 2026-09-08

User replied Yes to the explicit one-time, expiring lab-only certification exception.
Approved scope: this prepared disposable candidate, existing L4 success/failure recovery and L5 cleanup;
production window, publication and Git delivery remain unchanged. Before execution, add a root-owned
grant bound to full scheduler/certifier policy digest, fixed lab domain/target, run and prepared candidate,
with an issuance time and maximum four-hour expiry. Record grant digest in the existing journal before
certifier dispatch; failed/interrupted journals cannot restart. Gate: boundary regression tests pass,
installed code matches reviewed artifacts, and candidate remains valid. Then activate the existing lab
broker, execute real scheduler certification, verify cleanup/reconciliation and complete L5/L6.
L4 🔄 IN_PROGRESS; prior source validation is stale for the exception change until rechecked.

Timing-exception gate ✅ PASS: 31 scheduler regressions cover exact binding, one dispatch, expiry
recheck, invalid timestamps, wrong target, missing preparation, root ownership and failed-run refusal.
Installed schedule.py SHA-256 0c2412f18217ce2d7131d3c7f2a44d84edf391ebf799e9dda0eb773e3f2ce188
matches source. Root-owned grant SHA-256 f9eef1c97b647fcf10366b4c4ba63e53ed1d4681333ca671bca8ddb2b04a9923
is bound to the existing prepared journal; expiry epoch 1788893517. Systemd override verified.
The exact lab booted with pinned SSH, test-only broker started, runtime health check is pending.
Next: start the actual scheduler service after health readiness, observe required gates and retain failures.

L4 attempt 1 ❌ FAIL at credential issuance: certifier recorded credential-broker-rejected; both
cleanup layers retained credential-cleanup-failed because the lease is issuing without an account ID.
Independent admin GET reconciliation completed with HTTP 200 and no matching account; no encrypted
lease exists. A subsequent read-only broker check passed. Preserve the failed run and issuing record.
Temporary lab-only broker transport diagnostics record only HTTP method/status or exception type,
never URL, token or bodies. Recovery: restore the checked baseline, enroll a fresh run of the same
payload/UKI, and retry once within the original approved expiry, retaining all failed state.
No journal or lease is reset. The original timing expiry remains the hard limit across recovery.
Next: baseline restoration and fresh enrollment; inspect transport evidence if issuance fails again.

Recovery enrollment: fresh run 222e63ae4440f0ea5f1e7daf9daabbc71e656a24c80788b62377085104ca17fa
uses the same verified baseline, payload and UKI; its candidate manifest is
dde149bc95e7166b8da26ebe2fad101e1a82023299101a103b7147c9718071d0. The checked baseline
was restored while preserving attempt-1 disk/state. Pinned SSH, baseline inventory and restricted guest
binding passed. The grant retains expiry 1788893517. The initial transport diagnostic wrapper caused
a TypeError on GET; replacing class substitution with a response-method wrapper corrected it, and the
read-only broker check passed. No second issuance yet. A private evidence-copy attempt needed root
read access and was completed without changing originals. Next: runtime health then recovery scheduler run.

Recovery run issuance ✅ PASS: diagnostic POST HTTP 200 at epoch 1788879954, followed by
deploying and reboot-pending. No first-attempt lease was reissued or changed. Independent final
reconciliation will check both names again, including the earlier uncertain issuance, after revocation.
Exact next action: observe completion of package replay and warm/cold/runtime/restore/scan gates.

The recovery VM boot display showed kernel 7.1.13-200.fc44.x86_64 without manual unlock.
The controller subsequently recorded persistence-reboot after initial runtime/inference acceptance.
An auxiliary host-path probe did not find its expected candidate file and is not acceptance evidence;
a simultaneous SSH refusal coincided with the recorded persistence reboot. Continue using certifier gates.
Next: warm/cold acceptance, semantic restore, scan and automatic credential cleanup.

Recovery run package_replay, inference, boot and runtime gates ✅ PASS. The powered-off cold boot
completed through the same scheduler service sandbox and fixed-domain power helper. The first-run
failure event was independently read and reports only action-required/code 69. The current certifier
is performing semantic restoration; scan and provider cleanup remain pending.

Recovery UA-03 ✅ PASS: all seven acceptance/revocation gates exist, with both scheduler and
certifier journals at ua03-complete. Independent final reconciliation at epoch 1788881294
confirmed the successful account and the earlier uncertain account are both absent; the encrypted
lease is absent and the successful broker record is revoked. ExecStopPost is still completing.
Next: verify final service result and harmless completed-run invocation, export bound evidence,
then purge guest/local secrets and destroy the exact disposable domain and storage.

L4 ✅ PASS: the real systemd service completed successfully, all 350 frozen candidate files and
executed code hashes verified, and seven bound gates were exported to
[live scheduler evidence](evidence/2026-09-08-hermes-scheduler-live.json). Provider DELETE returned
HTTP 200 and the revoked key returned HTTP 401. Independent reconciliation proved both attempted
account names absent. A completed service rerun returned already-certified and left scheduler,
certifier and revoked-lease records byte-for-byte unchanged. No release was signed.
The scan passed the approved advisory policy with 20 critical and 458 high findings retained.
L5 is now executing the reviewed guest purge, exact VM/storage destruction, local key/backup purge,
and temporary service/grant removal. Preserve public candidate/evidence and earlier lab history.

### S4 closure — 2026-09-08

L4/L5 ✅ PASS: [bound live evidence](evidence/2026-09-08-hermes-scheduler-live.json) includes all seven
acceptance gates, failure signaling, independent reconciliation, completed-run verification and
guest/local/VM cleanup. The exact domain, dedicated pool, NVRAM/TPM and hypervisor processes are absent.
Forty-two local temporary paths were removed; fresh keys/backups, both window grants, scheduler units
and temporary power privilege are absent. The retained broker/socket is stopped, its runtime admin
credential is absent, and the diagnostic override was removed. Public evidence/candidates and earlier
history remain. No new release signing, production operation, commit or push occurred.

Validation identity: base 4a19d3f5c04f7ec927c85b586511a969933b96a9, uncommitted feature checkout;
executed source hashes are in live evidence. The latest 31 scheduler regressions passed after the grant
change; the preceding 193-test run includes the optional disk integration and remains evidence for
unchanged components. The 138 ShellSpec examples and changed VM shell checks remain applicable.
Final guide, Markdown, link and whitespace checks are now running for the completed documentation.

S4 operational scope is complete. L6/S3 documentation validation is the remaining gate before closure.
U06 as a full repeating lifecycle remains open: the next implementation is automatic fresh-fixture
provisioning, exact per-run guest enrollment and teardown, preserving the existing trust/gate ordering.
The Sunday timer was validated offline; this successful service run used the approved expiring exception.
The scan remains advisory with recorded findings. Failed attempt history and its reconciled issuing
record are preserved rather than relabeled as successful issuance.

Final closure: S3/L6 ✅ PASS. The 217 guide checks, six-document nonfix Markdown lint, 80 local
file links, tracked/new-file whitespace and equality of every executed source hash all passed.
The [offline observation](evidence/2026-09-08-hermes-scheduler-offline.json) preserves the earlier
checks and records the latest 31-test scheduler validation. The final bookkeeping text is linted
after this entry. S4 is closed within its approved lab-only scope; no required S4 gate remains.
Exact next action for U06: implement and validate automatic fresh-fixture enrollment and teardown.
Production enrollment, signing/publication and Git delivery remain outside this authorization.

### Documentation reconciliation — 2026-09-08

Approval: user “perform Documentation reconciliation” in this task. Scope: current unattended
readiness summaries and execution status only; preserve historical observations and unrelated changes.
Canonical record: this section. Base revision: 4a19d3f5c04f7ec927c85b586511a969933b96a9,
with existing uncommitted scheduler work on codex/hermes-unattended.

| Task | Dependencies | Progress | Validation gate | Gate status |
| --- | --- | --- | --- | --- |
| D1 reconcile current summaries | Recorded S4 and UA-03/UA-04 closure | ✅ PASS | Summaries match recorded evidence; history and production restrictions preserved | ✅ PASS |
| D2 validate documentation | D1 | ✅ PASS | Hermes guide, scoped nonfix Markdown, local file links and whitespace pass | ✅ PASS |

Affected documentation: this record and the unattended deployment guide. No runtime implementation
or operational change is included.
Exact next action: U06 automatic fresh-fixture enrollment and teardown; no reconciliation gate remains.

D1/D2 closure: summaries reconciled against the recorded S4 and UA-03/UA-04 evidence, without
rerunning live operations. Historical observations remain intact. Validation on 2026-09-08 15:51 UTC
through Devbox on the feature checkout above: Hermes guide (`./tests/test-hermes-guide.sh`)
217 passed, zero failed; Markdown lint passed with zero errors; a Python check resolved all 41
relative file links in the two edited documents; `git diff --check` passed. The initial Markdown
invocation included 24 maintained files via inherited root globs; final scoped verification uses
isolated copies of the two documents with fix disabled. Final bookkeeping is rechecked after this entry.
No runtime checks are required for these status-only edits. Production and Git delivery remain excluded.

Final scoped lint initially failed MD013 on the new next-action line; wrapping it corrected the failure.

### U06 automatic fixture lifecycle — 2026-09-08

Approval: user “proceed with U06” following the next-task description in this task.
Scope: implement and validate automatic disposable fixture provisioning, exact per-run enrollment,
and teardown, preserving trust and gate ordering. Production, release signing/publication and Git delivery
remain excluded. Existing uncommitted scheduler work on `codex/hermes-unattended` is preserved.
Base revision: `4a19d3f5c04f7ec927c85b586511a969933b96a9` plus the recorded S4 working changes.
Canonical execution record: this section; historical S4 evidence remains specific to its executed bytes.

| Task | Dependencies | Progress | Validation gate | Gate status |
| --- | --- | --- | --- | --- |
| F1 lifecycle and privilege design | S4 closure | ✅ PASS | Inspect existing provisioning, enrollment, cleanup and trust interfaces; define bounded operations | ✅ PASS |
| F2 implement lifecycle | F1 | ✅ PASS | Fresh runs, exact binding, interruption recovery, cleanup ordering and isolation regressions pass | ✅ PASS |
| F3 integration and documentation | F2 | ✅ PASS | Affected suites, guide, scoped lint, local links and whitespace pass; procedures match implementation | ✅ PASS |
| F4 live repeating lifecycle | F3 and enrolled lab prerequisites | ✅ PASS | Real no-input provisioning/enrollment/certification/teardown; fresh second run and failure recovery observed | ✅ PASS |

Affected documentation: unattended deployment guide, VM guide, contributor commands, deployment task
ledger and canonical installation evidence ledger. Offline checks cannot satisfy F4 or promotion gates.
Exact next action: finish F1 interface inspection and implement the bounded lifecycle with regression coverage.

F1 design: use a separate root-enrolled lifecycle service to own fresh installer/recovery/boot inputs,
fixed-domain provisioning and cleanup. Keep candidate execution under the existing non-root certifier;
its identity receives no provisioning, enrollment or destruction authority. Provision from signed Fedora
media with new recovery, boot, operator and certifier keys each run; never clone an old TPM or credential.
Read back guest identity through offline recovery before pinned SSH. Freeze the actual stored transaction
and compatible UKI, restore the verified pre-update disk, then enroll the exact candidate/run in the guest.
A root-owned journal serializes the fixed fixture, retains interrupted/failed runs, and records cleanup
independently. Reconcile test credentials before guest/local purge and VM destruction. A maintenance slot
may finish once; later slots use distinct run IDs and evidence paths. No automatic release signing.

F1 ✅ PASS by inspection of the repository interfaces and retained S4 procedure source on 2026-09-08.
F2 🔄 IN_PROGRESS. Live validation requires a root-enrolled code/policy installation, the isolated broker
with its runtime credential available, and an authorized maintenance window. The earlier one-time S4
window grant does not apply to new runs. Exact next action: implement the lifecycle and offline fault tests.

F2 first regression run ❌ FAIL: `devbox run -- python3 -m unittest discover -s tests
-p test_hermes_lifecycle.py` ran 34 tests; 33 passed and the archive-parent symlink rejection test failed.
The synthetic archive wrote through an existing parent symlink in its temporary test directory.
No VM or provider operation ran. Add explicit parent/target link rejection before receiving files;
repeat this gate after the fix. The state-machine, domain and credential-cleanup ordering tests passed.

F2 implementation includes a separate root lifecycle journal/driver, restricted guest preparation and exact
candidate enrollment, and service/timer/policy templates. Source selection is checked independently by
reconstructing the candidate from root-owned inputs before guest-root enrollment. The certifier keeps only
its existing candidate/credential/power authority. Storage deletion checkpoints bind the root-owned pool
inode and retain failed/interrupted state. Fresh TPM, recovery and signing keys are generated per run.
No live VM, provider or production action, unit installation, commit or push has occurred.

Validation checkpoint: the repaired first suite passed 34 tests. The expanded suite passed 44 tests;
then all seven applicable Python suites passed 242 tests in 17.580 seconds, and Hermes/VM ShellSpec
passed 138 examples in 28.45 seconds. Subsequent independent-candidate approval and partial-bootstrap
cleanup changes invalidate only the lifecycle suite until its final rerun; the other six suites are unchanged.
The 48-test lifecycle checkpoint passed before the final partial-bootstrap tests were added.

Initial Devbox `systemd-analyze verify` ❌ FAIL: that binary could not resolve the Bogotá timezone or
`sysinit.target` in its environment. `devbox run -- /usr/bin/systemd-analyze verify` against all three
new lifecycle units ✅ PASS using the host systemd installation. This is syntax/dependency validation,
not an installed-service or live sandbox pass. Both attempts are retained here.

F3 documentation now describes one-time root enrollment, fresh-input/gate order, failure recovery and
retained evidence in the canonical unattended guide. Final scoped lint, links, guide checks and whitespace
are pending. F4 remains unrun: the new root source/policy installation and live broker prerequisite have
not been established; the current Tuesday is outside the approved Sunday window. The earlier S4 one-time
grant does not authorize this new lifecycle, which has no window bypass. Exact next action: complete F3,
then resolve the live enrollment/window prerequisite before any F4 fixture or test-provider operations.

F2 ✅ PASS: final lifecycle suite passed 54 tests in 0.180 seconds, including independent root candidate
selection, read-only broker readiness under the certifier UID, restrictive-umask traversal, partial-bootstrap
cleanup, and a reappeared domain blocking storage deletion. The other 198 Python tests from the aggregate
run are unchanged. The [bound offline observation](evidence/2026-09-08-hermes-lifecycle-offline.json) records
commands, outcomes, limitations and hashes of all eight new source/test/unit/policy files.

F3 checkpoint: 217 guide checks, 138 ShellSpec examples and host systemd verification passed.
Six-document nonfix Markdown lint and 85 local file links passed before final bookkeeping. Tracked diff
whitespace and new-file syntax/whitespace passed. On this workstation `/usr/local` resolves to
`/var/usrlocal`; source/policy templates now use the canonical root-owned `/var/lib/hermes-lifecycle-source`
installation path, preserving the strict ancestor checks. New units were verified again after that change.
Final bookkeeping lint/links/whitespace and evidence hash equality are the remaining F3 checks.

F4 🚧 BLOCKED: no new root-enrolled source/policy or live broker setup has been installed. Tuesday is
outside the approved Sunday 02:00–04:00 Bogotá window, and the prior candidate-specific S4 exception
cannot authorize this lifecycle. This entrypoint deliberately has no timing override. Any one-time timing
exception and its disposable VM/test-provider operations must be explicitly authorized before proceeding.
No new live certification, cleanup/destruction, provider key, promotion, production change or Git delivery
is claimed. The optional real-disk integration suite was not repeated because its source is unchanged.
Exact next action: finish F3 bookkeeping checks, then obtain the F4 timing/enrollment decision and prepare
its concrete isolated live run; preserve the failed and successful historical records.

F3 ✅ PASS — 2026-09-08 16:31 UTC: final six-document nonfix lint passed with zero errors;
86 local file links resolved. All eight new source/test/unit/policy hashes match the offline observation;
Python parsing, new-file whitespace and `git diff --check` passed. Source and runtime checks are complete
for F1–F3; the final status-only text is checked separately after this entry.

U06 remains 🔄 IN_PROGRESS because F4 has not run. Exact next action: obtain the one-time lab timing
and operational authorization (or retain the approved Sunday window), prepare the root-enrolled isolated
fixture/broker prerequisites, and execute F4 with bound evidence. No timer should be enabled until its
live gate passes. Preserve existing uncommitted S4 changes and both generations of evidence.

Final status-only lint initially ❌ FAIL: the updated current-next-action paragraph exceeded 120 columns.
Wrapping that paragraph corrected the issue; the final status check is rerun after this correction.

### F4 one-time lab exception approved — 2026-09-08

Approval reference: current user request explicitly authorizes privileged-path review, installation,
disposable fresh-fixture cycles with test credentials, verified teardown, a second fresh run and failure
recovery. Production, release signing, recurring timers and Git delivery remain excluded.
The existing feature branch and all prior working changes are preserved.

| Task | Dependencies | Progress | Validation gate | Gate status |
| --- | --- | --- | --- | --- |
| F4a review and expiring exception | F3 | ✅ PASS | Review privileged paths; exact-run root grant, expiry and replay rejection tests | ✅ PASS |
| F4b first real cycle | F4a | ✅ PASS | Root installation; fresh VM, acceptance, test-key revocation and verified teardown | ✅ PASS |
| F4c repeat and recovery | F4b | ✅ PASS | Distinct fresh VM identity; failure recovery and retained evidence | ✅ PASS |
| F4d closure | F4c | ✅ PASS | Remove temporary grants/services; Sunday schedule unchanged; documentation and checks | ✅ PASS |

Each temporary grant will bind one lifecycle policy and one fresh run, expire within four hours, and be
consumed durably before provisioning. The campaign uses separate grants for the two successful cycles
and controlled failure; no clock changes or recurring schedule changes are permitted. Cleanup must remain
available after expiry. Required evidence includes source/policy hashes, distinct guest identities,
acceptance and teardown records, provider reconciliation and unchanged timer state.

Review checkpoint: lifecycle, fixture, guest, scheduler, unit, component guidance and existing F1–F3
records inspected. Local cloudops noninteractive sudo is available; production aicowork is uninvolved.
Exact next action: finish privileged dependency review and implement/test the narrowly bound timing grant
before root enrollment or VM provisioning. F4 remains open and no live success is claimed.

F4a checkpoint — 2026-09-08: reviewed provisioning shell, offline disk/boot helpers, root guest operations,
fixed-domain power helper and scheduler privilege split. Test broker is retained, inactive and test-only;
production UID/project are disabled. Both recurring timer units and lifecycle service are currently absent.
The exception preserves policy checks and derives only an exact frozen-candidate grant with the same expiry.
59 lifecycle and 31 scheduler regressions passed through Devbox; `git diff --check` passed.
The initial read-only inventory command failed due to shell heredoc quoting; direct Python retry passed.
No privileged installation, VM provisioning or provider issuance has occurred at this checkpoint.
F4a ✅ PASS for reviewed paths and timing regressions. F4b 🔄 IN_PROGRESS: enroll reviewed root source,
verified media and fixed-lab tools; then run the service with one bound four-hour grant.

F4b live attempt 1 ❌ FAIL — 2026-09-08T16:59:18.393222+00:00: run
`d390d479737f553a30251f728a7294e3131a8312eef66aea602d554794960c78` failed during firmware
preparation, before `install_started` or scheduler enrollment. Root journal reports `failed-cleaned`:
private material, dedicated storage, domain, NVRAM and TPM absence verified. No provider key was issued.
Diagnosis: the installed service PATH lacked `virt-fw-vars`; the Devbox tool exists only in Nix.
Firmware sizes independently match the required 4 MiB pair. Added its root-enrolled resolved tool link
and explicit mtools links; root code bytes are unchanged. A distinct bounded grant now runs attempt 2,
`797b9f488aca92680b6055bd4d2857a6f861e1cda3da45fc05012b2324008327`.

Root enrollment created the required `hermes-certification` account. The existing broker accepted the older
`hermes-lab-certifier` account, so its test-only UID and socket ownership were temporarily updated; original
files are retained under `/var/lib/hermes-lifecycle-source/enrollment` for restoration. No production role
was enabled. The pre-existing empty libvirt pool definition is retained; its backing directory was absent.
Ordinary installed lifecycle invocation returned `deferred`; both recurring timer units remain absent.

Validation: 217 guide checks and 138 Hermes/VM ShellSpec examples passed. Initial parallel Devbox launches
failed before tests because they race on `.devbox/gen/scripts/.cmd.sh`; rerunning within one sequential
Devbox shell passed. Host systemd unit verification and whitespace passed. F4 remains open.
Exact next action: observe attempt 2 through installation, certification and verified teardown; retain
failures and complete two successful fresh runs plus recovery before closing F4.

F4 documentation lint initially ❌ FAIL on three extra blank lines in these appended entries; corrected.

F4a expanded validation: 60 lifecycle tests passed, including derived scheduler grant binding and preserved
expiry. Scoped two-document lint, 44 local links and whitespace passed. Running VM installation shows
increasing CPU and disk-write counters; no provider authentication terminal or secret output was captured.
For the controlled recovery gate, interrupt only the lifecycle service after the test lease is durably
recorded and delivered; verify its independent cleanup action revokes the lease and purges/destroys the
exact fixture. Preserve the failed status; recovery must never upgrade it to certification PASS.
This controlled interruption follows the required first and second successful fresh cycles.

Timing-isolation correction: removed the first-dispatch `/run` override from the normal lifecycle service
while its existing process continues. Readback confirms its future ExecStart contains no grant flag.
Subsequent lab dispatches will use a separate temporary unit, so grant expiry cannot interfere with a
future ordinary Sunday service invocation even if campaign cleanup is interrupted. Timers remain absent.
The removed override is retained as public dispatch evidence under the root enrollment directory.

The [live F4 observation](evidence/2026-09-08-hermes-lifecycle-live.json) now retains both attempts,
root-enrolled source hashes, immutable tool paths, signed-media verification, original/current timer state,
and ordinary off-window deferral. It is explicitly IN_PROGRESS; neither offline evidence nor an allocated
VM is counted as full lifecycle success. The canonical installation ledger reflects the active campaign.

F4b checkpoint — 2026-09-08T17:17:17.417483+00:00: attempt 2 completed unattended installation
and reached the powered-off handoff after approximately 18 minutes. Offline recovery readback verified
the injected SSH host public key and guest machine identity; `recovery_readback=true` is durable.
The driver is preparing the installed signed UKI before first encrypted boot. Certification and provider
issuance remain pending; this is progress evidence, not a completed lifecycle gate.

F4b attempt 2 ❌ FAIL: after installation, recovery readback and first encrypted boot, guest preparation
failed and automatic cleanup completed (`guest_purged`, `domain_destroyed`, `vm_destroyed`, `private_purged`).
No scheduler or provider credential was created. The root driver discarded the failing operation context.
Reassessment found a concrete invocation defect: lifecycle calls `lab_enroll_boot.py` with Python `-I`,
but that helper did not add its root-enrolled module directory to `sys.path`. The exact isolated `--help`
invocation reproduced `ModuleNotFoundError: common` locally before any privileged operation. This matches
the observed boot-manager handoff boundary, though the removed guest did not retain its own traceback.
Repair this isolated import and add a real CLI regression plus sanitized local failure-frame evidence.
F4a validation becomes 🔁 STALE for the changed source until affected tests pass; no fresh run starts first.

Isolated-import repair ✅ PASS: 61 lifecycle tests, seven boot-enrollment tests and 217 guide checks passed.
The root-installed helper also passes the exact `python3 -I -B ... --help` invocation. Installed source
was updated only after verified failed-run cleanup; previous source hashes are retained separately.
Failure-context regressions prove that exception messages are excluded. F4a returns to ✅ PASS for this
source revision. F4b remains 🔄 IN_PROGRESS; next action is a new fresh fixture through the separate
one-time lab unit, preserving both failed runs. No first successful cycle is claimed.

Next-dispatch preflight ❌ FAIL before fixture allocation: root policy loading rejected the enrolled ISO
owner. Live stat shows libvirt changed this campaign's reusable ISO from root to QEMU UID/GID 107;
checksum, keyring and firmware remain root-owned. This is a real rerun failure, not a timing rejection.
Change the driver to hash-verify a per-fixture ISO copy inside its owned pool and pass only that copy to
libvirt. Keep the trusted reusable media root-owned. Restore its ownership only after verifying its exact
signed hash and confirming the lab domain is absent. Test copied-media binding and teardown allowlisting
before another dispatch. F4a is 🔁 STALE for this source repair; both prior failed runs remain unchanged.

Media-copy repair ✅ PASS: 62 lifecycle regressions pass, including byte/hash binding, distinct inode,
unchanged reusable input, existing-copy rejection and cleanup allowlisting. The enrolled ISO matched its
signed hash and the domain was absent before restoring root ownership. Reviewed driver installed with
its previous source map retained. F4a returns to ✅ PASS; attempt 3 may now start as a fresh lab run.

Final-document checkpoint ❌ FAIL on appended blank lines and a long ledger line; formatting corrected.

Current repaired-source checkpoint: scoped three-document lint, Python syntax and whitespace pass.
Live media ownership observation confirms reusable ISO UID 0 and disposable copy UID 107 on distinct
inodes. Attempt 3 is installing; required first success, second success and credential-bearing recovery
remain TODO. Exact next action: observe this fresh run through boot-manager enrollment and certification.

Timing preservation checkpoint: host `systemd-analyze calendar` resolves the unchanged lifecycle timer
expression to Sunday 2026-09-13 02:00 Bogotá (07:00 UTC). Direct validation of an expired root-owned grant
against the installed code rejected it with `expired-or-invalid-lifecycle-lab-window`; this probe did not
invoke a fixture factory or change the active run. The probe file was removed. Ordinary off-window
entrypoint deferral remains separately recorded. Both timers are still absent/inactive.

F4b checkpoint — 2026-09-08T17:50:02.435128+00:00: attempt 3 completed installation, offline
identity readback, first encrypted boot, boot-manager enrollment and its reboot. The active child is the
fixed guest `bootstrap` operation, proving the repaired isolated helper passed its live handoff. The
reusable ISO remains root-owned while libvirt owns only the per-fixture copy. Full certification,
credential revocation and teardown remain pending; no complete lifecycle is claimed.

F4b attempt 3 ❌ FAIL at public archive validation after stored replay and boot-input export. Sanitized
failure frames identify `unpack_public`'s path check; automatic guest purge and complete fixture teardown
passed. No scheduler/test credential existed. A normal GNU ustar roundtrip passes. Inspection of the
previously certified public package archive identifies supported RPM caret versions (`passt-0^...` and
`passt-selinux-0^...`) as the only rejected filename class; the existing release validator allows caret.
A focused replay with that exact public filename reproduces `unsafe-public-archive` before the repair.
The destroyed guest's specific rejected member was not retained, so that member identity is inferred.
Allow caret in this receiver's filename alphabet, retaining traversal, depth, type, duplicate, symlink,
sparse and size checks. Add a real GNU tar regression and revalidate before another fresh VM run.
F4a is 🔁 STALE until that repair passes; F4 remains open with zero successful complete cycles.

Archive repair ✅ PASS: 63 lifecycle tests, including the real GNU ustar caret-version roundtrip, passed.
Prior installed source hashes and the failed run are retained. Reviewed repair installed only after
verified teardown. F4a returns to ✅ PASS; next action is another fresh run through the separate lab unit.

Additional archive-boundary check ✅ PASS: all 333 public package paths in the retained signed archive
were accepted by the installed repaired receiver using synthetic empty bodies. This validates the path
boundary only, not package contents or VM acceptance. The active fresh run is
`e8ee1c2d8032f14d23e146ffd6d3b28efe72b5a5f99f46fc152fb327f02d8376`; its ordinary preflight accepted
the still-root-owned reusable ISO after the prior teardown. Exact next action remains full live completion.

F4b checkpoint — 2026-09-08T18:55:16.723159+00:00: attempt 4 passed real archive reception,
built the updated signed UKI, restored and verified the baseline, and enrolled the independently approved
exact candidate. Root lifecycle and scheduler journals now report `certifying`; the certifier is at
`snapshot`, before test credential issuance. This validates the repaired export boundary on a real VM.
Full acceptance, credential revocation and teardown remain pending before the first cycle can pass.

F4b attempt 4 ❌ FAIL at the first encrypted backup. The candidate was enrolled; certifier state has no
lease and no backup receipt, and the broker has no matching run record. Cleanup reconciled the no-issuance
state, purged guest data and removed the VM/disk/NVRAM/TPM and private material. Inspection found that
`enroll_candidate` created an empty backup directory but never initialized its Restic repository.
Calling the real backup helper on an empty repository reproduced `operation-failed`. Add initialization
under the certifier identity before scheduling and a real encrypted roundtrip regression. F4a is
🔁 STALE until that repair passes. No complete lifecycle or test credential issuance is claimed.

Backup initialization repair ✅ PASS: 64 lifecycle tests passed. A separate root-enrolled probe used the
actual certifier UID 984 and service tooling to initialize Restic, back up and restore identical bytes;
all probe material was removed. No provider operation occurred. Independent teardown verification of
attempt 4 confirms all fixture/private paths absent, no broker lease, and unchanged earlier journals.
Reviewed source is installed with its prior source retained. F4a returns to ✅ PASS; next action is a
fresh lifecycle run with automatic repository initialization before scheduling.

Active attempt 5: `2e7bf9fb3039f2d4866bae4037af22415007309520d3c6e2b2ad9b5a9e22da47`, source identity
`de099ba3b68eb414be396f72bf0f591161a40ab75decb01c5e71bb3f3671a4cf`. Installed-source readback matches
its journal and all four prior failed-run journals remain unchanged. Installation is active. The current
required order is first complete cycle and independent teardown, completed-run idempotency, second fresh
complete cycle, then credential-bearing interruption/recovery and final control cleanup. No successful
complete cycle or provider issuance is recorded yet. Both recurring timers remain untouched.

F4b credential-bearing checkpoint — 2026-09-08T19:46:35.242844+00:00: attempt 5 initialized its
fresh Restic repository, verified the encrypted backup, issued and delivered a real test credential, and
reached certification `reboot-pending`. Independent broker metadata confirms role `test`, state `ready`,
and a durable backup receipt. No credential content was printed. Updated/persistence/cold-boot acceptance,
revocation and teardown remain pending; the first complete cycle is not yet PASS.

F4b checkpoint — 2026-09-08T20:01:21.850740+00:00: attempt 5 passed package replay, runtime installation,
first inference and the persistence reboot, and advanced to `cold-boot`. This is intermediate acceptance;
full cold-boot/restore/scanning gates and credential revocation/teardown remain required. Independent
read-only provider reconciliation is prepared and will run only after terminal revocation.

F4b attempt 5 ❌ FAIL at scanning after package replay, inference, persistence reboot, cold boot and
semantic encrypted restore passed. Initial certifier and scheduler revocation attempts failed; the root
cleanup retry subsequently reconciled the test lease and purged the complete fixture. Independent checks
confirm revoked broker state, absent encrypted lease, provider service-account absence (all list pages),
and absent VM/disk/NVRAM/TPM/private/backup paths. Earlier journals remain unchanged. The diagnostic
revocation call observed an already-revoked record and made no provider request. This is observed real
failure recovery, not successful certification; the two required complete fresh successes remain TODO.
Read-only broker diagnostics confirmed decryption and provider listing worked, but the original transient
revocation error was suppressed and its cause remains unproven. A public-candidate-only scan reproduction
is active before another VM is authorized by the existing sequential gate. No new key is being issued.

Scan diagnosis: the retained public candidate reproduces an unreachable IPv6 Docker CDN connection.
IPv4 TLS to that CDN passes. Forcing libc lookup fails with the Fedora/Nix NSS combination; explicitly
selecting Go lookup (`GODEBUG=netdns=go`) passes the real scan. Enroll that setting only in the root-owned
lab Trivy launcher, retaining the immutable binary and recording both hashes. No host networking or
vulnerability policy changes. A second probe through the actual child PATH and actual candidate denylist
must pass before another VM. The failed run remains failed; this probe cannot retroactively certify it.

Launcher verification ❌ FAIL on an IPv6 connection to `index.docker.io`; the resolver setting alone
is not a reliable repair. Preserve that failed probe. Host-native lookup returns IPv4 addresses and
IPv4 TLS to the CDN passed; direct public UDP DNS queries timed out. Host networking remains unchanged.
A repeated actual-policy scan is checking the observed intermittent transport condition. No scan gate
is bypassed and no fresh fixture starts before this preflight passes. Original transport failures and
broker retry causes remain distinct; a common cause is not proven.

Actual-policy scanner preflight ✅ PASS through the root-enrolled launcher and exact scheduler PATH;
Trivy exited 0 with no stderr. This confirms current operability, not elimination of transient networking.
Attempt 5 remains ❌ FAIL with verified recovery. Next action: a new fresh full lifecycle using unchanged
implementation source `de099ba3b68eb414be396f72bf0f591161a40ab75decb01c5e71bb3f3671a4cf` and the recorded
lab scanner launcher. All required certification gates remain mandatory.

Recovery-probe refinement: after the future run durably delivers its test credential, archive and remove
only that run's timing grant immediately before interrupting the lifecycle main process. This additionally
checks that independent cleanup remains available without the grant. Preserve the recorded expiry tests;
grant removal is not represented as an actual-clock expiry test. No signal has yet been sent.

Attempt 6 `5d49e5f4cc270b62cab898a1480f475c598b19ad00fbebfb72deeddea596093b` passed installation,
offline readback and first encrypted boot. Documentation validation: guide 217/217 PASS and whitespace
PASS. An initial temporary lint-config filename was rejected; a corrected invocation inherited repository
defaults and checked 24 files. File mtimes and status showed no unintended rewrites. An isolated temporary
copy check with explicit non-fixing config then checked exactly three edited documents: zero errors.
Exact next action: complete preparation and all live acceptance/cleanup gates for this fresh attempt.

Attempt 6 completed preparation replay/export, restored its verified baseline and enrolled the exact
candidate. Encrypted backup passed, a real test lease is ready/delivered, and certification reached
`reboot-pending`. Full acceptance, revocation and independent teardown remain required before F4b PASS.

F4b ✅ PASS — attempt 6 completed the full fresh lifecycle with service Result=success and stage=complete.
All acceptance gates passed, including real inference, persistence/cold boots, encrypted semantic restore,
and actual image scan. Broker revocation and guest purge preceded complete fixture/private-material
removal. Independent local teardown and provider reconciliation (both attempted lease names absent)
passed. Reinvoking the same completed grant exited 0, created no VM/run directory and left lifecycle,
scheduler, certifier and broker journal hashes unchanged. Exact evidence is in the live campaign artifact.
F4c 🔄 IN_PROGRESS: next action is a second fresh full run with identical reviewed implementation/tooling,
then the separately bound credential-bearing interruption probe. No recurring timer or release change.

Second-cycle attempt 7 `49ab9de4db47d1a2d654764f25c4b25f8308d02df360b8289adefa75ecdf14c8`
passed installation, offline readback and first encrypted boot. Independent comparison confirms distinct
machine/SSH identities and the same implementation source as attempt 6. Full certification and teardown
remain pending; next action is complete preparation and acceptance before the controlled recovery gate.

Attempt 7 completed preparation/export, verified baseline restoration and exact candidate enrollment.
Its encrypted backup passed and a real test-role credential is ready/delivered. Certification is at
`reboot-pending`. Next action: finish all acceptance and cleanup gates, independently reconcile both
successful cycles, then run the bounded interruption probe. F4c remains IN_PROGRESS.

Attempt 7 ❌ FAIL at scanning after replay, inference, persistence/cold boots and semantic restore.
Its test lease is revoked and credential cleanup passed; outer teardown is in progress. The retained
error is `operation-failed`, so this attempt's exact scanner diagnostic is unavailable; earlier public
candidate probes establish intermittent registry transport failures. Do not relabel this run successful.
Refine only the lab scanner launcher: same pinned Trivy binary and policy, at most six recognizable
network-transport retries within one 900-second total budget. Nontransport errors remain immediately
fatal; partial failed stdout is discarded. Six focused launcher tests PASS (success, transport recovery,
policy rejection, retry cap, shared deadline, timeout). Preserve the prior launcher and tool-generation
hashes. Install only after verified teardown; require a real actual-policy scan before another fresh VM.
The lifecycle implementation source is unchanged; tool enrollment generations remain explicitly distinct.

Attempt 7 independent teardown ✅ PASS; provider reconciliation confirms all three issued test accounts
absent. The root-enrolled retry launcher passed a real actual-policy scan with exit 0 and no stderr.
Its hash is `57101ba2565dec2dbd70ec056d39a81facd2ea9cf69d1a8af137391069f2f3ec`; the prior launcher and
six boundary tests are retained. Future dispatches verify both launcher and pinned-binary hashes and
retain a per-run tool snapshot. First success remains attempt 6; a second complete fresh success and
controlled interruption remain required. Next action: dispatch a new fresh cycle under the same source.

Reviewable tool evidence: [installed launcher snapshot](evidence/2026-09-08-hermes-lab-trivy-launcher.py)
and [six reproducible boundary tests](evidence/2026-09-08-hermes-lab-trivy-launcher-test.py). The saved
launcher hash matches the installed file; running the saved test artifact passes all six tests without
provider or VM access. These are dated lab enrollment artifacts, not a production installation change.
Attempt 8 `58aca82ba314ed778cddbf027e1adc40a1d34678bc15670691f2d39a5e425f29` is installing.

Attempt 8 passed preparation replay/export and restored-baseline enrollment. Its encrypted backup
passed and a real test credential is delivered; candidate deployment is active. The per-run scanner
snapshot binds the reviewed retry launcher. Required next action remains full acceptance and independent
teardown before the controlled interruption test. No first-pass evidence is overwritten.

### F4 bounded continuation approved

Approval: user's latest bounded-execution instruction in this task; recorded 2026-09-08T23:26:31.647945+00:00.
This supersedes earlier open-ended retry assumptions. Active run:
`58aca82ba314ed778cddbf027e1adc40a1d34678bc15670691f2d39a5e425f29`.
From this checkpoint, allow at most one additional full certification cycle if needed and then at most
one controlled credential-bearing interruption/recovery fixture. Neither may repeat automatically.
Preserve unrelated working-tree changes; no production, signing, timers, commits, pushes or PR writes.

| Task | Dependency | Progress | Required validation gate |
| --- | --- | --- | --- |
| B1 active run | Existing run | ✅ PASS | Terminal result; independent provider revocation and complete teardown |
| B2 diagnose if B1 fails | B1 cleanup | ➖ N/A: B1 passed | Reproduce the specific failure independently; smallest repair; focused checks |
| B3 optional full cycle | B2 PASS, if needed | ➖ N/A: two successes established | At most one new full cycle; all acceptance and independent teardown |
| B4 controlled recovery | Two applicable fresh successes | ✅ PASS | At most one fixture; delivered test key, interruption, cleanup without grant, independent verification |
| B5 close or report blocker | Terminal B1–B4 outcomes | ✅ PASS | Remove exception/privileges; restore broker; preserved Sunday/timers/release; documentation |

Stop condition: if the remaining bounded work cannot establish all F4 gates, perform safe final control
cleanup and report the exact blocker with F4 open. Do not launch another fixture to improve a failed result.

Evidence applicability: attempt 6 is a full success for source
`de099ba3b68eb414be396f72bf0f591161a40ab75decb01c5e71bb3f3671a4cf`, with distinct guest binding,
revocation, independent teardown, provider absence and idempotency. That source remains installed.
Its scan proves the pinned binary/unchanged policy on that candidate; it does not prove the subsequent
retry launcher. The newer launcher has six focused boundary tests and an actual-policy public scan;
the active run is its first full-cycle validation. Earlier failed source generations remain historical
and cannot certify repaired paths. Any new repair must invalidate affected evidence explicitly.

Inspection found seven prior terminal journals unchanged. The first three failed runs lack standalone
`independent-cleanup.json` files; their original cleanup records and later fresh-preflight observations
must be assessed explicitly. Do not invent contemporaneous independent evidence for them. Final audit
must verify absence of every run's remaining private paths as well as the global fixture resources.
Exact next action: let the current run finish, verify its cleanup independently, then apply the bounded gates.

B1 ✅ PASS: attempt 8 completed with all acceptance gates. Independent cleanup, provider reconciliation
and same-grant completed-run idempotency passed at Unix timestamps 1788911171–1788911184.
Freshness comparison at 1788911190 proves attempts 6 and 8 use distinct machine IDs, SSH identities,
candidates and UKIs under the same lifecycle source, with verified absence between runs. Attempt 8
validates the newer launcher; attempt 6 does not. No subsequent implementation repair was required.
The optional additional full cycle will not be used. Next action: dispatch exactly one controlled recovery
fixture and interrupt only after its test credential is delivered; verify cleanup with the grant removed.

B4 controlled fixture dispatched once at 1788911215:
`e2ab090db55d1a85f59d40ee726a32599ef1aea72528cbaf23f935c2663c6985`.
The root dispatch counter consumed the only recovery allowance before service start. Its exact-run
watcher requires certifier `deploying` (after successful guest credential delivery), a ready test lease,
and matching candidate/run identity; it removes the grant before SIGKILL of the temporary service main
process. Final control audit and evidence aggregation scripts are prepared but have not run.

B4 ✅ PASS at 1788913866: the only controlled fixture reached guest test-key delivery, then its
grant was removed before SIGKILL. Automatic `ExecStopPost` cleanup completed without the grant;
root state remains `failed-cleaned`, certification is false, and service Result remains `signal`.
Independent teardown and provider reconciliation passed at 1788913854–1788913856. All five issued
test-account names are absent across complete provider listing pages. Both successful cycles retain
their exact certification, lifecycle and broker journal hashes. No additional full cycle was used and
the controlled fixture was not repeated. Next action: remove temporary controls, restore original broker
bytes, verify preservation, and finish affected documentation checks before closing F4.

### F4 final closure

Live gates and final control/preservation audits passed at 1788913854–1788913897 (2026-09-09 UTC;
2026-09-08 Bogotá). The [sanitized evidence bundle](evidence/2026-09-08-hermes-lifecycle-live.json)
retains every failed attempt, both successful cycles, per-run source/tool identities, acceptance gates,
idempotency, independent cleanup, provider reconciliation, controlled interruption and final audits.

| Gate | Actual result | Evidence in bundle |
| --- | --- | --- |
| First fresh cycle | ✅ PASS: attempt 6, all seven acceptance gates | Run `5d49e5f4…`; acceptance, independent cleanup, provider reconciliation, idempotency |
| Second fresh cycle | ✅ PASS: attempt 8, all seven acceptance gates | Run `58aca82b…`; same records and revised launcher snapshot |
| Freshness and preservation | ✅ PASS: distinct machine, SSH, candidate and UKI identities; absent between runs; both journals unchanged after recovery | `two-fresh-successes.json`, recovery verification |
| Controlled recovery | ✅ PASS: exactly one delivered test key interrupted by SIGKILL; automatic cleanup without grant; failure retained | Run `e2ab090d…`; fault injection and recovery verification |
| Provider and teardown | ✅ PASS: all five issued accounts independently absent; all run-private paths and fixture resources absent | Final provider reconciliation, independent cleanup, final controls |
| Temporary controls | ✅ PASS: grant, temporary unit, sudo rule, power helper and diagnostic entrypoints removed; broker policy/socket restored byte-for-byte; runtime admin credential absent | `final-controls.json`, `final-preservation.json` |
| Protected scope | ✅ PASS: prior signed archive hash unchanged; no production access or release signing; both timers unchanged/absent; Sunday 02:00 Bogotá preserved | `final-preservation.json`, timer states |
| Execution bound | ✅ PASS: zero additional full cycles, one controlled fixture, no repeats; unused allowance cancelled | Bounded continuation record |

Evidence applicability: both full successes use lifecycle source
`de099ba3b68eb414be396f72bf0f591161a40ab75decb01c5e71bb3f3671a4cf`.
Attempt 6 used the prior scanner launcher; its full lifecycle evidence remains applicable to that source
and pinned scanner policy/binary, but it does not validate the later retry wrapper. Attempt 8 plus six
focused tests validates the revised wrapper. Earlier source-generation passes are stale for subsequently
repaired paths; original failures and source maps remain historical evidence. No implementation changed
after these two successes or during the controlled fixture.

Limits: deletion is logical, not physical sanitization. Calendar-triggered execution was not exercised.
Three early pre-credential failures lack contemporaneous standalone independent reports; original cleanup,
later fresh-preflight absence, and final all-run private-path absence are retained without inventing reports.
Original live scanner stderr for attempts 5 and 7 was unavailable; independent registry transport failures
do not prove the exact cause of each suppressed error. Advisory scan findings remain (20 critical and
458 high on the second success). Production/hardware recovery and recurring enablement remain separate.
The preexisting libvirt pool definition, reviewed dormant source/service installation, no-login evidence
owner, reusable media and public evidence are retained. Temporary power privilege and broker activation
are removed; future execution requires authorized prerequisite enrollment.

Final documentation checks are recorded below. Exact next action after this lab closure: await separate
operator authorization for recurring enablement or UA-05 production work; preserve the Sunday schedule.
The broader execution record remains open for its production gates; F4 does not authorize them.

Final validation ✅ PASS: `devbox run -- ./tests/test-hermes-guide.sh` returned 217 passed, zero failed
or skipped. Non-fixing Markdown lint in an isolated temporary directory passed all five affected documents
with zero errors and unchanged original hashes; 81 local link targets exist. `devbox run -- git diff --check`
passed. Earlier applicable final-source checks remain retained: lifecycle 64, boot enrollment 7, scheduler
31, Hermes/VM ShellSpec 138, three unit templates, and six scanner-launcher boundary tests. These were
not rerun after documentation-only closure edits. No commit, push or PR modification was performed.
F4/U06 is ✅ PASS; the broader production gates remain open. No campaign execution allowance remains.

## Production continuation — 2026-09-08

Approval: user requested proceeding with pending tasks after the UA-05 next-step explanation,
and confirmed the existing `aicowork` password was rotated. Rotation is operator-reported;
no password was requested or inspected. This authorizes the stated production readiness,
enrollment and deployment scope. Recurring enablement remains a separate decision.
Preserve existing implementation edits and production configuration.

| ID | Task / dependencies | Progress | Required validation gate | Gate status |
| --- | --- | --- | --- | --- |
| P1 | Read-only production inventory | 🔄 IN_PROGRESS | Pinned SSH identity, host baseline, boot/recovery prerequisites | PARTIAL: SSH restored; privileged inventory pending |
| P2 | Hardware boot and recovery; P1 | ⬜ TODO | Retained recovery access and prior boot; cold/update/tamper/recovery evidence | ⬜ TODO |
| P3 | Restricted enrollment and production-bound release; P2 | ⬜ TODO | Trust, identities, credential isolation, verified backup and exact binding | ⬜ TODO |
| P4 | Deployment acceptance; P3 | ⬜ TODO | No-input deployment/rerun, runtime inference, restore/rollback and documentation | ⬜ TODO |

Validation environment: current workstation and pinned `aicowork@10.0.30.10`.
Affected documentation: this record, canonical evidence ledger and ordered deployment task ledger.
Exact next action: inspect pinned SSH access and read-only host boot/storage prerequisites.
Stop dependent operations at an unmet gate; do not reuse the lab-bound release for production.

P1 observation at 2026-09-09T01:20:08.330689+00:00: workstation HEAD with existing
uncommitted changes; no production mutation. `devbox run -- ssh` with BatchMode,
StrictHostKeyChecking and a 10-second ConnectTimeout to `aicowork@10.0.30.10`
failed before authentication (exit 255, connection timeout). `devbox run -- ping -c 2 -W 2
10.0.30.10` received zero replies (exit 1). `devbox run -- ip route get 10.0.30.10`
reported source `192.168.70.157` via `192.168.70.254` on `eno1` (exit 0).
The documented production SSH boundary requires management CIDR `192.168.99.0/24`;
the source mismatch is a likely cause, not a live firewall diagnosis. Host power and live rules
remain unknown. P2–P4 cannot proceed before P1 passes.
Exact next action: restore the workstation's approved management-network access, confirm Hermes
is powered on, then repeat pinned read-only SSH inventory. No router or workstation network changes made.

Documentation validation for this continuation: 217 Hermes guide checks passed; three changed
Markdown files passed nonfix lint in an isolated copy; `git diff --check` passed. Initial lint
invocation failed on an unsupported temporary config filename; corrected filename retry passed.
The new ledger link targets the existing canonical record and its production continuation heading.

### P1 connectivity restored — 2026-09-09T01:44:14.643081+00:00

User supplied successful SSH, Secure Boot and LUKS-backed root observations after the network change.
A live `devbox run -- ssh` BatchMode/StrictHostKeyChecking probe then confirmed Fedora Server 44,
kernel `7.1.12-200.fc44.x86_64`, enforcing SELinux, active firewalld, TPM2 device/support and Secure Boot.
`bootctl status --no-pager` reported current loader GRUB 2.12 and `Measured UKI: no`;
ESP inventory was permission-denied. Reported ESP free space: 591 MiB. An old Talos default-entry
string was reported; its file existence or active use is not established. Preserve it pending inspection.
`sudo -n true` requires a password; the combined inventory command exited 1. This is partial
inventory evidence, not a passed boot gate. Earlier connectivity failures remain historical evidence.
No production settings changed. Next: operator runs privileged read-only boot inventory in the existing
interactive SSH terminal, and confirms physical console plus offline LUKS recovery access before P2.
Do not request the password, capture the authentication terminal, or apply the disposable lab helper
on production. The current GRUB boot does not satisfy the signed-UKI/PCR11 enrollment contract.

### Production recovery availability — 2026-09-09T01:48:18.114316+00:00

Operator confirmed physical console access and a known-working offline LUKS credential. This confirms
availability; a new recovery test and P2 boot gates remain unperformed. Operator-provided privileged
`bootctl status` confirms no systemd-boot installation, no loader.conf and zero boot-loader entries.
Live pinned SSH inventory identifies AZW SER3 hardware, systemd 259.8 and cryptsetup 2.8.7;
RPM reports systemd-boot-unsigned, systemd-ukify and sbsigntools absent. The first enrolled MOK
certificate shown is Fedora's public CA; no conclusion about the complete trust list is drawn.
The existing enrollment helper requires a disposable marker and lab-specific prior UKI; it cannot
be applied to production. Preserve those guards and existing Fedora boot paths.
Exact next action: operator performs a read-only LUKS credential test and supplies EFI entry/file
inventory from the existing sudo-capable terminal. Then prepare a production-specific boot transition
with retained EFI/LUKS backups and verified signing trust before any boot selection or TPM change.
No production mutation, key enrollment, reboot or package installation occurred.

### Production recovery credential test — 2026-09-09T01:51:15.570696+00:00

Operator-provided evidence: `cryptsetup open --test-passphrase /dev/nvme0n1p3` returned 0.
This verifies an accepted credential; it is not a completed offline recovery boot. `efibootmgr -v`
reports BootCurrent 0001 and BootOrder 0001,0007,0008,0003,0000,0002,0004,0005. Fedora 0001
uses the previously observed ESP and shimx64.efi. Talos/Windows entries remain untouched.
The lowercase `find -name '*.efi'` inventory does not exclude uppercase `.EFI` files.
Prepared the [production boot backup procedure](../HERMES_UNATTENDED_DEPLOYMENT.md#production-boot-recovery-backup).
Gate before boot mutation: verified private local and off-host boot/header backups, preserved Fedora
entry and signing trust. The backup procedure has not yet run on production. P1 trust inventory and
P2 remain open; no enrollment, package, firmware or TPM changes occurred.
Exact next action: operator executes the backup block in the sudo-capable SSH terminal and reports
only its checksum results and directory path; then arrange and verify protected off-host retention.

Validation of the backup procedure and documentation on the current uncommitted tree: 217 guide
checks PASS; Bash syntax and ShellCheck PASS for the command block; three-document nonfix lint
PASS after fixing two added blank-line errors; whitespace check PASS. New relative procedure link
and target heading verified by inspection. These checks do not establish backup execution or recovery.

### Production local recovery backup — 2026-09-09T01:58:21.992126+00:00

Operator reports all three SHA256SUMS checks OK for luks-header.img, boot.tar and efibootmgr.txt
in `/root/hermes-boot-recovery.VoP66t50`. Local backup creation/check gate is operator-reported PASS;
independent off-host verification and recovery restoration remain TODO. No boot changes occurred.
Pinned SSH confirms the operator home/group are `/home/aicowork` and `aicowork`. Prepared empty
mode-0700 workstation destination
`/var/home/cloudops/.local/state/hermes-production-recovery/hermes-boot-recovery.VoP66t50`.
Exact next action: operator stages only the four backup/checksum files in a fresh mode-0700 directory
under their Hermes home, with mode-0600 files, using the existing interactive sudo session. Then copy
through pinned SSH to the private workstation destination and independently verify SHA256SUMS.
Retain the root original. Off-host retention remains an unmet prerequisite for boot mutation.

### Production off-host backup verified — 2026-09-09T02:01:17.851048+00:00

✅ PASS: copied the four exact backup/checksum files from the operator transfer directory via pinned
BatchMode SSH/SCP. Initial brace-pattern SCP failed because the remote SFTP path was literal; the
explicit four-source retry passed. No fallback transport or relaxed host verification was used.
Independent streaming SHA-256 comparison matched all three manifest entries. Mode-0700 destination
and private file permissions passed. LUKS header magic, Fedora shim/GRUB and kernel archive entries
were checked without extracting or printing sensitive contents. Boot archive size: 595,896,320 bytes.
Private evidence: `/var/home/cloudops/.local/state/hermes-production-recovery/`
`hermes-boot-recovery.VoP66t50/verification.json`. Root original and remote staging copy remain retained.
This passes off-host backup integrity/retention only, not restoration or physical recovery boot.
Read-only package follow-up found no `/usr/lib/systemd/boot/efi/linuxx64.efi.stub`, shim-x64 16.1-5,
GRUB EFI 2.12-64, systemd-udev 259.8, and SetupMode value 0. No production boot changes occurred.
Exact next action: prepare the production-specific UKI/stub and boot-manager package inputs and
establish a verified signing-trust enrollment path preserving the current Fedora firmware entry and
keys. P1/P2 are still open for full trust inventory, boot transition and physical recovery validation;
P3/P4 remain dependent. Never apply the disposable enrollment helper to the production host.

### Production package and trust preparation — 2026-09-09T02:04:57Z

Approval: user “proceed” after the UA-05 preparation explanation in this task. Continue the existing
P1/P2 scope on `codex/hermes-unattended`; preserve all existing working-tree changes.

| Block | Progress | Validation gate | Result |
| --- | --- | --- | --- |
| P1 package/trust preparation | 🔄 IN_PROGRESS | Pinned read-only inventory and documented package/trust inputs | PARTIAL |
| P1 privileged handoff | 🚧 BLOCKED | Operator ESP inventory and resolved package files/transaction | `sudo -n true` requires password |
| Preparation documentation | ✅ PASS | Hermes guide, scoped Markdown lint, whitespace and link checks | ✅ PASS |

Observed on pinned SSH to `10.0.30.10`, workstation revision
`4a19d3f5c04f7ec927c85b586511a969933b96a9` plus existing uncommitted changes:
Secure Boot enabled; kernel `7.1.12-200.fc44.x86_64`; systemd `259.8-1.fc44`;
shim `16.1-5.fc44`. Boot-unsigned, ukify and sbsigntools are absent.
Complete filtered MOK inventory reports Fedora CA 20200709 and `CN=grub`; ownership of the latter
is unknown. Pending MOK addition/deletion listings were empty. Firmware db lists Microsoft UEFI
CA 2011, Windows Production PCA 2011, UEFI CA 2023 and Option ROM UEFI CA 2023. PK is `Custom PK`;
KEK lists Microsoft KEK CA 2011. These are public certificate observations, not proof of private-key
custody or validation of every firmware revocation entry. Preserve them all.

Cache-only DNF candidate query returned boot-unsigned/ukify `259.8-1.fc44` and sbsigntools
`0.9.5-14.fc44`. File-list queries failed twice because updates metadata is absent; do not repeat
cache-only queries. Next use an explicit metadata refresh in the operator session, then inspect the
resolved package files and proposed transaction. Cached versions are provisional, not frozen inputs.
No packages, boot files, keys, TPM tokens or firmware selections changed.

Prepare the canonical production boot-input procedure before dependent operations. Candidate design:
separate Fedora shim path loading a production-signed systemd-boot and signed UKI, subject to actual
signature/SBAT and hardware acceptance. MOK trust must not be treated as direct firmware db trust.
Exact next action: finish and validate the procedure, then obtain the operator's privileged read-only
ESP inventory and refreshed package query results. P1 remains open; P2–P4 remain dependent.

Validation on 2026-09-09 UTC, current uncommitted documentation at the revision above:
`devbox run -- ./tests/test-hermes-guide.sh`: 217 passed. Initial scoped nonfix Markdown lint
failed on three newly added double blank lines; corrected and rerun passed. The inventory Bash
block passed `bash -n` and ShellCheck. `git diff --check` passed; new relative links and target
headings were checked in the source. No boot or recovery acceptance is implied by document checks.
Exact next action: operator runs the production boot input preparation inventory block in the existing
sudo-capable SSH terminal and returns public output/errors. P1 privileged handoff remains blocked
on that evidence; no additional authorization is requested for the already approved scope.

### Privileged access recheck — 2026-09-09T02:07:45Z

User reaffirmed “proceed”. Pinned BatchMode SSH to `aicowork@10.0.30.10` with
`sudo -n true` still returned exit 1: password required. P1 remains 🚧 BLOCKED on operator
privileged inventory; authorization is already present. No production mutation occurred.
Exact next action: operator runs the canonical production boot input preparation block in their
interactive SSH terminal and shares public output/errors. Repeating the same access probe without
a changed access condition will not advance this gate. This evidence-only append requires no
implementation tests; whitespace validation follows.

### Operator ESP inventory received — 2026-09-09T02:13:10Z

✅ PASS: operator-provided privileged EFI inventory confirms BootCurrent 0001, unchanged BootOrder,
Fedora shim and GRUB, two fallback EFI files and MokManager. Case-insensitive recursive file listing
shows no Talos EFI file beneath `/boot/efi/EFI`; stale Talos firmware/default strings remain preserved.
ESP available space is 619,642,880 bytes. This is inventory acceptance, not signed-UKI capacity acceptance.
Secure Boot enabled, TPM2 present, GRUB 2.12, no measured UKI and no installed systemd-boot remain observed.
Refreshed candidate versions match the previous provisional list. The operator's separate cache-only
file-list query again failed for missing updates metadata; no package installation occurred.

🔄 IN_PROGRESS: use refreshed file-list query over pinned SSH to resolve package input paths; then
prepare an assume-no transaction preview. Preserve failed cache-query evidence. P1 remains open on
package/trust preparation and P2 remains unstarted. Existing sudo authorization is unchanged; no need
to repeat the known passwordless-sudo failure. Update the canonical procedure to avoid cache-only
file queries in this environment. Validation gate: guide checks, scoped nonfix lint and whitespace.

The non-root pinned SSH `dnf5 --assumeno install` preview resolved the three exact requested NEVRAs:
19 new packages, no upgrades/removals, 4 MiB download and 14 MiB installed size. Exit 1 with
“Operation aborted by the user” is the expected assume-no outcome, not a failed solver. Sixteen
additional packages include ukify dependencies and weak dependency python3-pillow. No installation ran.
Continue downloading only the three selected input RPMs to the dedicated operator-owned
`/home/aicowork/.local/state/hermes-boot-inputs-20260909` for signature, file and scriptlet inspection;
this does not authorize treating the complete transaction as frozen or accepted. Keep keys and boot files intact.

✅ PASS: refreshed file-list query and all three RPM downloads completed despite HTTP mirror
connection timeouts. `rpmkeys --checksig` reports digests/signatures OK for all three RPMs using
Hermes's installed RPM trust. Three pinned SCP copies independently matched the recorded SHA-256
values in workstation directory `/var/home/cloudops/.local/state/hermes-production-boot-inputs/20260909`.

| RPM | SHA-256 |
| --- | --- |
| sbsigntools-0.9.5-14.fc44.x86_64.rpm | `70847eb164408de7f18606c1a14f025429ea924a7bc576c6559ba4a5862b8166` |
| systemd-boot-unsigned-259.8-1.fc44.x86_64.rpm | `89458cc20597787ebe898a8e2f9510b3dbd2153caefed7d1010b74f3301a8872` |
| systemd-ukify-259.8-1.fc44.noarch.rpm | `95fd279090e6f4280ddbf796d7c47d799dfcdc7004d3ed7980e9db21190abe11` |

Exact-member `rpm2cpio`/`cpio --to-stdout` extraction produced `linuxx64.efi.stub` and
`systemd-bootx64.efi` locally. SHA-256 identities are saved in `efi-inputs.sha256.json` in that directory.
`objdump -h` confirms x86-64 PE and SBAT sections; `sbverify --list` reports no signature table on
both, as expected for unsigned inputs. Boot-unsigned has no reported scripts/triggers/file triggers;
ukify and sbsigntools have no reported scripts. Full dependency/installed trigger review remains open.
Live `mokutil --list-sbat-revocations` returned sbat date 2024040900, shim 4, grub 4 and grub.peimage 2;
no systemd component was listed. This is observed revocation metadata, not hardware acceptance.
No installed package, key, EFI file, boot selection or TPM state was changed.

Exact next action: operator supplies SHA-256 hashes of the current kernel, initramfs, Fedora shim and
MokManager using the canonical procedure. Compare with private retained backup before reusing its
build inputs, then prepare production-only signing material and a concrete console enrollment handoff.
P1 remains open on complete input/trust binding. Do not start P2 boot changes before that gate passes.

Documentation validation for this continuation: 217 guide checks passed; four-document scoped
nonfix Markdown lint, Bash syntax/ShellCheck for preparation blocks and `git diff --check` passed
on the current uncommitted tree. Existing procedure links remain unchanged. These checks do not
close P1/P2. The next action remains the operator live-file hash comparison above.

### Production boot-file binding — 2026-09-09T02:20:26.791079+00:00

✅ PASS: the operator reported running kernel `7.1.12-200.fc44.x86_64` and live SHA-256
hashes for its kernel/initramfs, Fedora shim and MokManager. Independent streaming SHA-256
comparison of the four exact regular-file members in retained `boot.tar` matched all four.
Live hashes are operator-provided; backup comparisons were executed locally. Exact members were
copied to private mode-0600 workstation build inputs without extracting the full archive.
Evidence: `/var/home/cloudops/.local/state/hermes-production-boot-inputs/20260909/live-backup-binding.json`.
This establishes file identity, not initramfs suitability, signing trust or recovery acceptance.
Exact next action: inspect initramfs TPM/PCR support and review the production command line privately,
then prepare the dedicated signing and console-enrollment handoff. P1 remains open until the
complete build/trust inputs pass; P2 hardware boot tests remain dependent. No production changes occurred.

### Production initramfs and signing preparation — 2026-09-09T02:24:02.464165+00:00

Existing approval covers production-specific boot-input and signing preparation. Preserve the live
Fedora boot chain. Prepare local candidate artifacts only; no firmware/MOK/TPM enrollment in this block.

| Block | Progress | Required gate | Result |
| --- | --- | --- | --- |
| Initramfs and command line | ✅ PASS | TPM cryptsetup support, PCR phase ordering, signature handoff, root/LUKS options | Static checks pass; hardware untested |
| Dedicated local boot signing | 🔄 IN_PROGRESS | Separate production Secure Boot/PCR keys; signed UKI sections and manager signature; space | ⬜ TODO |
| Console enrollment handoff | ⬜ TODO | Public certificate fingerprint, staged chain and verified trust | ⬜ TODO |

Private initramfs listing confirms systemd-cryptsetup, TPM2 plugin, TSS libraries and enabled
systemd-pcrphase-initrd unit, ordered before cryptsetup. Its measured-UKI condition explains why the
current GRUB boot does not establish PCR-phase acceptance. Kernel config has `CONFIG_TCG_CRB=y`;
live TPM driver is `tpm_crb_acpi`. Absence of a separate CRB module is not a missing-driver finding.
`20-systemd-stub.conf` copies the synthetic UKI PCR public key/signature into `/run/systemd`.
Embedded crypttab has one entry and no keyfile. Command line has one root and LUKS UUID and no
builder-denied unsafe option. Private candidate removes only BOOT_IMAGE and adds
`rd.luks.options=tpm2-device=auto`; live settings are untouched.
Exact next action: generate distinct private production-only keys on the workstation, build with the
existing UKI builder, sign systemd-boot, and record signature/section/size evidence before handoff.

✅ PASS: existing `boot_build.py` built the private candidate with distinct RSA-3072 Secure Boot
and PCR11 keys. UKI SHA-256 `3a3edb624e1bcae176bcc08ec3e65ffe1240e4fad13c94cea41a0fdc3afe68cf`;
size 99,034,112 bytes. Builder verified its signature and required sections; independent `sbverify`
also passed. The production-signed systemd-boot passed `sbverify`. Candidate chain is 101,076,296 bytes,
within recorded ESP availability including 1 MiB reserve. Live space must be rechecked before copying.
Keys and signed boot artifacts remain in the private workstation input directory; evidence files are
`uki-build-result.json` and `signing-validation.json`. Builder correctly reports `boot_verified=false`.

Only the public DER certificate was copied by pinned SCP into the existing operator input directory;
remote SHA-256 matched `f23d1ee7b728ea0f9013a75e0b3fbb36c51bf59bbcefa78b1a06e48b4446365c`.
No MOK import, reboot, installed package, firmware selection or TPM token change was performed.
Exact next action: operator follows the
[certificate enrollment handoff](../HERMES_UNATTENDED_DEPLOYMENT.md#production-signing-certificate-enrollment)
at the physical console, then returns `mokutil --test-key` and Secure Boot status. P1 trust enrollment
remains pending; dependent P2 boot/recovery and P3/P4 remain unpassed.

Validation: 217 Hermes guide checks passed; scoped nonfix Markdown lint, Bash syntax/ShellCheck
of the enrollment command blocks, and whitespace validation passed on the current uncommitted
tree. New relative handoff link and heading checked by inspection. No source implementation changed.

### Operator MOK import requested — 2026-09-09T02:28:27.156680+00:00

Operator-provided terminal output shows `sudo mokutil --import` for the staged production
certificate prompted twice and returned without a displayed error. This records the import request,
not completed enrollment; no independent pending-list check was performed.
Exact next action: operator reboots with physical console and LUKS recovery access, confirms the
expected certificate in MokManager, then returns `mokutil --test-key` and `mokutil --sb-state` output.
P1 signing trust remains pending; P2 hardware candidate boot has not run.

### Production MOK presence verified — 2026-09-09T02:34:33.148188+00:00

✅ PASS: operator output and independent pinned SSH both report the exact public DER as already
enrolled, an empty pending-import list and Secure Boot enabled. Enrolled certificate listing includes
`CN=Hermes Production Secure Boot 20260909` alongside prior Fedora and grub certificates.
Operator firmware output retains BootCurrent 0001 and the prior BootOrder/Fedora shim path.
The kernel-trusted-keyring warning was reproduced; kernel keyring access remains unverified.
Upstream mokutil source distinguishes the MokListRT enrolled result from the MokNew pending result;
the warning does not negate the separately observed MOK presence. Why no enrollment screen was
observed is unknown; do not infer a console ceremony or repeat import from this evidence.
Exact next action: prepare and verify an isolated shim/systemd-boot/UKI staging and one-shot trial
procedure preserving Fedora defaults. MOK presence passes this subgate only; hardware chain
acceptance, P2 cold/update/tamper/recovery tests and TPM enrollment remain unpassed.

### Isolated production trial preparation — 2026-09-09

Approval: user “proceed” after the isolated staging and one-shot procedure next-task description.
Scope: verify retained public boot artifacts and prepare the canonical staging, trial and recovery
procedure locally; preserve existing changes on `codex/hermes-unattended`.

| Block | Progress | Required gate | Result |
| --- | --- | --- | --- |
| Trial preparation | ✅ PASS | Artifact identities/signatures, loader behavior, bounded staging and recovery procedure | ✅ PASS |
| Documentation | ✅ PASS | Guide checks, scoped Markdown lint, whitespace and referenced headings | ✅ PASS |
| Hardware execution | 🚧 BLOCKED | Operator console, privileged staging evidence and single trial | ⬜ TODO: fresh operator inventory |

Exact next action: verify the prepared chain and document a reviewable operator procedure before any trial.

Preparation closure: both `sbverify --cert` checks passed against the retained public production
certificate. Four hashes matched prior binding; UKI remains
`3a3edb624e1bcae176bcc08ec3e65ffe1240e4fad13c94cea41a0fdc3afe68cf`.
Private bundle: `/var/home/cloudops/.local/state/hermes-production-boot-inputs/20260909/trial-staging`,
four images plus `SHA256SUMS`, no private keys, 101,076,296 image bytes. Shim UTF-16 strings confirm
`grubx64.efi`; upstream v259 menu/entry and efibootmgr create-only behavior were inspected.
The canonical [trial handoff](../HERMES_UNATTENDED_DEPLOYMENT.md#isolated-production-boot-trial)
defines exclusive paths, unchanged defaults, cancellation and physical recovery.

Validation on the current uncommitted tree at `4a19d3f5c04f7ec927c85b586511a969933b96a9`:
217 guide checks passed; three-document nonfix Markdown lint passed from an isolated temporary
configuration directory; inventory Bash syntax and ShellCheck passed; whitespace and local heading
checks passed. Initial signature invocation failed due to Devbox shell variable expansion; explicit
Python argv invocation passed. Initial parallel Devbox guide invocation failed on a transient generated
script path; sequential retry passed. Initial lint configuration suffix was rejected; corrected lint
ran broadly, then explicit isolated nonfix verification confirmed the three intended documents.
No production changes were made. P1/P2 hardware gates remain open; no additional authorization is
needed for the read-only inventory already in scope. Exact next action: operator runs the read-only
staging gate in their sudo-capable terminal and returns public output/errors, enabling an exact
ESP-bound staging and BootNext command handoff. Do not repeat the known passwordless-sudo failure.

Evidence timestamp: 2026-09-09T02:39:22.536357+00:00.

### Trial inventory continuation

User reaffirmed “proceed”. Pinned BatchMode SSH read-only inventory confirmed the ESP is
`/dev/nvme0n1p1`, vfat, on disk `/dev/nvme0n1`, partition 1. Kernel remains
`7.1.12-200.fc44.x86_64`; Secure Boot is enabled. BootCurrent is 0001 with the original
Fedora shim path; BootOrder is `0001,0007,0008,0003,0000,0002,0004,0005`; no BootNext
was reported. `bootctl list --no-pager` failed with permission denied opening
`/boot/efi/loader/loader.conf`, making the aggregate SSH exit status 1.

Inventory progress is partial; the required privileged loader/path gate remains 🚧 BLOCKED.
No production mutation or repeated passwordless-sudo probe occurred. Exact next action: operator
runs privileged `bootctl status`, `bootctl list`, trial/loader path inventory and ESP free-space
checks from the canonical read-only staging gate and returns public output/errors.
This evidence-only append requires whitespace validation, not implementation tests.

Timestamp: 2026-09-09T02:40:24.788576+00:00.

### Privileged trial inventory accepted — 2026-09-09

Operator output confirms Secure Boot enabled, TPM2 present, current GRUB 2.12, no measured UKI,
no systemd-boot, zero entries and absent loader/trial directories. ESP has 619,642,880 free bytes.
The stale Talos default remains preserved. This passes the read-only staging inventory, not hardware boot.

| Block | Progress | Gate | Result |
| --- | --- | --- | --- |
| Guarded staging handoff | 🔄 IN_PROGRESS | Fixed hashes, exclusive creation, live binding, syntax/ShellCheck, pinned transfer identity | ⬜ TODO |
| Privileged staging | ⬜ TODO | Operator executes helper; destination hashes and unchanged firmware state | ⬜ TODO |

Scope remains the authorized isolated trial preparation. Prepare and transfer the public-image bundle
and a staging-only helper; operator performs sudo execution. No BootNext or reboot in this block.
Exact next action: validate and transfer the fixed-input staging helper, then obtain operator staging output.

Guarded staging handoff ✅ PASS: Bash syntax and ShellCheck passed. Initial ShellCheck found
a negated command that bypassed errexit; replaced with an explicit rejecting conditional and reran.
Pinned SCP transferred four images, manifest and helper into a fresh mode-0700 operator directory.
Remote `sha256sum --check --strict SHA256SUMS` passed all four; helper SHA-256 matched locally:
`befabc2661735290f2c61cf5efb6a12381b49d83a750a69c5176c31ea67c065a`. Remote `bash -n` passed.
This is preparation/transfer evidence, not privileged staging acceptance. Canonical helper instructions
are in the deployment guide. Exact next action: operator runs the staging helper with sudo and
returns output/errors. No EFI files, boot selection, TPM tokens or reboot were changed by this step.

Documentation validation: 217 guide checks and `git diff --check` passed on the current tree.

### Staging attempt stopped before hash output — 2026-09-09

Operator execution printed Secure Boot enabled and certificate already enrolled, then returned
without STAGING_OK or hash-check output. Staging acceptance is ❌ FAIL; exact root-session exit
location is unknown. Independent pinned SSH verifies the original helper hash and firmware
BootCurrent/BootOrder preconditions; unprivileged efibootmgr exits zero. These do not explain
the privileged exit. No evidence supports claiming successful copying.

Prepare ERR-trap diagnostics (line and exit only, no command/secret expansion) and a --check-only
mode that exits before mkdir/copy. Validation gate: Bash syntax, ShellCheck, stop-before-write
control-flow review and pinned transfer hash equality. Exact next action: operator runs the
updated helper with --check-only and returns its output. Full staging remains gated on diagnosis.

Diagnostic helper gate ✅ PASS: syntax, ShellCheck, stop-before-write review and pinned remote
hash equality passed. Initial trap triggered ShellCheck SC2154; a positional-argument error
function resolved it. Updated helper SHA-256:
`92f8ebdd90f628d3e55551a6bdf56dac4cb3bab70f636160700d71ff9b49b6c5`. Privileged diagnosis remains pending.

### MOK exit semantics repair — 2026-09-09

Operator diagnostic identifies line 16 (`mokutil --test-key`) returning 1 after enrolled output.
Installed package is mokutil-0.7.2-3.fc44. The upstream 0.7.2 `test_key` implementation returns
1 on the already-enrolled branch and 0 for not-enrolled; current master reverses those values.
The earlier shell-wrapped status observation was not reliable evidence of the command exit.
Source: <https://github.com/lcp/mokutil/blob/0.7.2/src/mokutil.c>.

Helper now requires exact C-locale enrolled output for the bound certificate and status 0 or 1,
rejecting pending/blocked/not-enrolled/error results. Read-only --ignore-keyring confines this check
to firmware certificate databases; it does not change trust or imply kernel-keyring acceptance.
Syntax, ShellCheck and eight result-classification regressions passed. Pinned transfer hash matched:
`43672fff50781fa58a46432c41d3dba8dd5a2947201d1540426517b2dc437672`.
Privileged preflight remains pending. Exact next action: operator reruns
--check-only; after PREFLIGHT_OK, full staging may proceed within existing authorization.

### Production trial staging accepted

✅ PASS: operator output reports PREFLIGHT_OK and STAGING_OK, all four live input hashes,
all four source hashes and all four destination hashes match. The Type #1 trial entry resolves
to the isolated UKI. The helper's full firmware comparison passed. Independent pinned SSH
confirms BootCurrent 0001, original BootOrder `0001,0007,0008,0003,0000,0002,0004,0005`,
no BootNext and no trial firmware entry. Installed efibootmgr 18 help confirms create-only
does not add to BootOrder. Staging passed; candidate hardware boot remains untested.

Next gate: operator registers the isolated shim with --create-only on verified disk
/dev/nvme0n1 partition 1, then returns efibootmgr -v output. Require exactly one new trial
entry, unchanged prior entries/BootOrder and no BootNext before selecting any one-shot boot.
Do not rerun the exclusive staging helper or guess the allocated boot number.
Exact next action: execute the canonical firmware registration handoff; no reboot in that command.

Evidence timestamp: 2026-09-09T02:49:29.582208+00:00.

Staging handoff documentation: 217 guide checks and whitespace validation passed.

### Trial firmware registration accepted

✅ PASS based on operator create-only and verbose inventory output: new active Boot0006 is
Hermes trial 20260909 on the verified ESP, pointing to the isolated shimx64.efi. Previous
entries and BootOrder `0001,0007,0008,0003,0000,0002,0004,0005` are preserved; BootCurrent
remains 0001 and no BootNext is shown. This is firmware registration, not hardware acceptance.

Exact next action: operator at physical console with retained LUKS recovery credential sets
BootNext 0006, verifies the unchanged BootOrder, then performs one reboot and selects the trial
entry. On failure select original Fedora Boot0001. Collect bootctl status, kernel, Secure Boot
and firmware state after return. Do not enroll TPM tokens or change permanent defaults.

Timestamp: 2026-09-09T02:50:46.185958+00:00.

Handoff validation: 217 guide checks and whitespace validation passed on the current tree.

### One-shot trial selected

✅ PASS: operator output twice confirms BootNext 0006, BootCurrent 0001 and preserved
BootOrder `0001,0007,0008,0003,0000,0002,0004,0005`. Boot0006 still points to the isolated
trial shim on the verified ESP. Reboot and hardware chain acceptance remain pending.
Exact next action: with physical console and LUKS recovery credential ready, operator reboots
once using the canonical one-shot handoff, then returns loader/UKI, Secure Boot and firmware
observations. On failure return through original Fedora Boot0001. No repeat BootNext write needed.
Evidence-only update; whitespace validation applies.

Timestamp: 2026-09-09T02:52:53.721860+00:00.

### First production measured-UKI boot

Operator attachment and console report confirm manual LUKS passphrase entry. The boot inventory
shows systemd-boot/stub 259.8-1.fc44, the isolated loader and UKI paths, trial entry selected,
Measured UKI yes, Secure Boot enabled and expected kernel 7.1.12-200.fc44.x86_64.
BootCurrent is 0006 and BootNext is consumed. This passes the initial hardware chain subgate.
TPM unlock enrollment was not performed in this workflow; the passphrase prompt is consistent
with that state and does not invalidate measured-UKI boot.

❌ FAIL: exact firmware preservation. BootOrder is now `0001,0008,0003,0000`; prior entries
0002, 0004, 0005 and 0007 are absent. Fedora 0001 remains first and the isolated trial entry
remains outside BootOrder. Cause is unknown; do not attribute removal to firmware or systemd
without evidence, or restore a BootOrder referencing absent entries.

❌ FAIL: systemd-tpm2-setup.service. Independent pinned SSH journal inspection shows existing
SRK found and public-key files saved, then Esys_LoadExternal error 0x000002c4 and
“Failed to unseal secret using TPM2: State not recoverable”; two NvPCRs already initialized.
Root cause and relation to existing TPM state remain unknown. No TPM clear/reset or token
mutation is justified. Random Seed now reports system token set and seed present; contents
were not inspected.

P2 remains 🔄 IN_PROGRESS with dependent enrollment blocked. Exact next action: read-only
diagnosis of TPM setup/NvPCR compatibility and firmware-entry loss; preserve existing recovery
credentials, TPM state, EFI files and remaining firmware entries. Cold/update/tamper/recovery
gates remain unpassed. No production changes made during this inspection.

Observed: 2026-09-09T02:58:02.709731+00:00.

### Read-only diagnosis of first trial failures

Approval: user “proceed” after the two-failure diagnostic next-task description. Scope is
read-only diagnosis; preserve boot files, firmware entries, TPM state and unrelated changes.

✅ PASS diagnostic evidence: pinned SSH current/previous-boot journals, installed units/package
versions, public PCR key size and TPM return-code decoder inspected. Early setup successfully
initialized two NvPCRs; late setup found the same SRK and saved public-key files, then failed
Esys_LoadExternal during unsealing. Previous GRUB boot skipped both setup services because
ConditionSecurity=measured-uki was unmet. `tpm2_rc_decode 0x2c4` returns parameter(2),
value out of range or incorrect for context. This does not establish TPM corruption.

Live `/run/systemd/tpm2-pcr-public-key.pem` is RSA-3072. Upstream v259 code links the late
NvPCR anchor-secret synchronization to credential unsealing and signed-PCR policy external
public-key loading. Hardware algorithm/key-size incompatibility is a hypothesis, not confirmed.
Source references: systemd v259 src/tpm2-setup/tpm2-setup.c, src/shared/tpm2-util.c and
src/shared/creds-util.c at <https://github.com/systemd/systemd/tree/v259/src>.

Firmware diagnosis remains inconclusive: focused current-boot journal search found no record
identifying who deleted the four entries. BootOrder still retains Fedora first. Removed entries
were CD/DVD, removable, network and the prior MBR-backed UEFI OS entry; do not infer automatic
firmware pruning as fact. Random seed and system token creation is independently explained
by successful systemd-boot-random-seed.service output; no seed contents were read.

🚧 BLOCKED next evidence: TPM device is root:tss mode 0660. Operator must run read-only
tpm2_testparms comparisons using /dev/tpmrm0. Tool is installed; upstream tool manual confirms
algorithm-suite capability testing. Exact next action: compare RSA-2048 and RSA-3072 with
RSASSA/SHA256 and return output/status, then evaluate key compatibility before planning any
repair. Do not restart setup, clear the TPM, recreate missing entries or change policy yet.

Timestamp: 2026-09-09T03:00:50.871883+00:00.

### TPM algorithm comparison accepted — 2026-09-09

Operator capability tests: RSA2048:RSASSA-SHA256 exited 0; RSA3072:RSASSA-SHA256 printed
Unsupported algorithm specification and exited 5. Installed tpm2-tools is 5.7-5.fc44.
Inspected upstream 5.7 tools/tpm2_testparms.c and lib/tpm2_alg_util.c: parser explicitly
accepts 3072; this exact error is emitted after Esys_TestParms returns a TPM parameter error,
not by argument parsing. The tested RSA3072 suite is rejected by the TPM; RSA2048 passes.
Source: <https://github.com/tpm2-software/tpm2-tools/blob/5.7/tools/tpm2_testparms.c>.

Compatibility diagnosis is strongly supported: the live PCR policy public key is RSA3072,
and systemd fails while loading an external key. Exact LoadExternal recovery is not yet tested.
Proposed next scope: prepare a separate RSA2048 PCR policy key and rebuilt trial UKI, retaining
the existing Secure Boot signing key/certificate and previous candidate. Review the existing
NvPCR anchor credential binding and recovery implications before any production replacement;
rebuilding alone does not prove existing sealed credentials will migrate. No keys or artifacts
changed during diagnosis. Firmware-entry loss remains unexplained.
Exact next action: authorize and prepare the bounded compatibility repair, then revalidate the
new candidate and retained-state recovery before a separately controlled hardware trial.

### RSA2048 compatibility candidate preparation — 2026-09-09

Approval: user “yes” to local repair preparation after the RSA algorithm diagnosis.
Scope: generate a distinct private RSA2048 PCR key, rebuild a separate UKI using retained
inputs and the existing Secure Boot key, and review retained NvPCR credential recovery.
No production key, credential, boot file, firmware or TPM mutation is authorized by this block.

| Block | Progress | Gate | Result |
| --- | --- | --- | --- |
| Local candidate | 🔄 IN_PROGRESS | Key separation, unchanged input hashes, signature/sections, old candidate retained | ⬜ TODO |
| Recovery review | 🔄 IN_PROGRESS | Identify old credential binding and safe next gate without secret disclosure | ⬜ TODO |

Exact next action: build in an exclusive private directory and inspect upstream anchor recovery behavior.

Local candidate gate ✅ PASS. Private directory:
`/var/home/cloudops/.local/state/hermes-production-boot-inputs/20260909/rsa2048-candidate`.
UKI SHA-256 `1392a4914759481e45ece24eb38e5e8aac0de5d66f1f11a42d8b1ffc864f6bbc`,
99,025,920 bytes. Existing builder passed signature and required sections; independent sbverify
passed and objcopy extraction matched the new 2048-bit PCR public key. Input hashes, phase
list and Secure Boot certificate match the old build; old UKI hash remains unchanged.
Evidence: private build-result.json and validation.json. Hardware boot remains unverified.

Recovery review ✅ PASS with unresolved prerequisite: pinned SSH metadata-only stat finds
/run/systemd/nvpcr/nvpcr-anchor.cred (6,935 bytes, regular, 0644); standard /var/lib copy
is absent (stat exits 1 for that absence). No credential contents were printed or decrypted.
Upstream v259 tpm2_nvpcr_acquire_anchor_secret uses /run as the primary encrypted credential
with persistent and boot-partition secondary copies; late synchronization decrypts the existing
credential. Changing PCR keys does not automatically rewrap an existing credential. Its exact
embedded binding and any ESP copy have not been independently inspected. Existing logs
and source support, but do not alone prove, old-PCR-key binding.

Local preparation is complete. Deployment gate 🚧 BLOCKED: preserve the volatile encrypted
anchor and inventory ESP secondary-copy presence before reboot; review recovery/rebinding
without clearing TPM or deleting anchors. These production steps require their own authorized
execution scope. Exact next action: prepare the bounded anchor-preservation/recovery handoff
and separate candidate staging; do not reboot or replace production files from this local build.

### Encrypted anchor preservation and binding review — 2026-09-09

User “continue” authorized recovery preparation. ✅ PASS: pinned SCP preserved the encrypted
/run anchor in private workstation anchor-recovery/nvpcr-anchor.cred beneath the production
boot-input directory. Directory 0700, file 0600; remote/local SHA256 matched. No decryption
or production change occurred. Private preservation.json records hash/size and binding-review.json
records public metadata only.

Public credential header identifies TPM2 HMAC with public-key policy, PCR11 mask 2048.
Embedded public key normalizes to the retained original RSA3072 key. Initial DER comparison
failed, then DER parsing failed; format inspection showed PEM despite the source field comment.
PEM normalization passed. Payload authentication was not tested; this is header-binding evidence.
The RSA2048 candidate cannot automatically rewrap this existing credential.

Exact next action: operator inventories ESP anchor-copy paths and LUKS token types using the
canonical recovery inventory. Preserve all state; no unseal/reset/delete or reboot. Determine
existing consumers before proposing any replacement anchor or controlled NvPCR reinitialization.

### Existing LUKS TPM token discovered — 2026-09-09

Operator read-only inventory shows no NvPCR-named file on ESP and LUKS token ID 1 of type
systemd-tpm2. This corrects any broader inference that no TPM token exists: the current
workflow did not enroll one, but an existing token is present. Origin, policy, referenced
keyslots and relationship to NvPCR are unknown. The passphrase prompt alone cannot diagnose
why this token did not unlock the trial. Preserve token/keyslots and the recovery credential.

Exact next action: operator returns allowlisted token policy fields only (PCR selections,
public-key PCR selections, bank, PIN-required boolean, keyslot references, presence of pcrlock
and public-key fields). Do not export TPM blobs, policy hashes or credential contents.
No re-enrollment, token removal, TPM clear, anchor replacement or reboot before policy review.

### Existing LUKS token policy identified — 2026-09-09

Operator allowlisted metadata confirms token 1 type systemd-tpm2, keyslot 2, SHA256 PCRs
0 and 7. No public-key policy or PCR-lock fields were reported. This token's recorded policy
is distinct from the RSA3072 PCR11 NvPCR anchor policy; preserve it and keyslot 2.
Metadata does not establish why automatic unlock failed, nor whether other consumers depend
on the NvPCR anchor. No token or anchor mutation is justified solely by this observation.
Exact next action: inspect the current boot's cryptsetup unit journal for the actual unlock
failure, then complete the bounded candidate/recovery proposal without deleting existing state.

Independent pinned SSH cryptsetup journal confirms two TPM policy-mismatch failures during
initrd unlock, then successful activation using operator passphrase. This explains automatic
unlock fallback for the existing token; which PCR changed and when is not established.
It is separate from the later NvPCR RSA3072 LoadExternal failure. Exact next action: prepare
the controlled RSA2048 candidate boot with manual unlock retained; resolve anchor continuity
and obtain production staging/reboot scope before executing. No existing token deletion.

### Anchor recovery continuation — 2026-09-09

Read-only inspection: standard /var/lib/systemd/nvpcr, /var/lib/systemd/pcrlock and
/etc/systemd/pcrlock directories are absent. Listed PCR-lock policy-building service units
are disabled. This is not an exhaustive absence-of-consumers proof. Initial analyze verb
nv-pcrs was invalid; corrected nvpcrs reached TPM access and failed permission denied.

Upstream v259 tpm2_define_nvpcr_nv_index reuses existing indices only after verifying public
attributes; it does not require deleting them. tpm2_nvpcr_acquire_anchor_secret generates
a new random anchor when neither persistent nor passed encrypted copies exist. Thus a
new candidate boot may create a new anchor, not migrate the backed-up one. Its exact behavior
on the physical TPM and any prior-policy continuity remain untested. No TPM clear is proposed.

Exact next action: operator runs sudo systemd-analyze nvpcrs and inventories the standard
PCR-lock policy JSON paths. Use public metadata to finish a reviewable trial proposal explicitly
accounting for new-anchor identity and retaining LUKS token/keyslot and old encrypted backup.
No production mutation occurred. Whitespace validation applies to this evidence-only append.

### NvPCR inventory accepted and bounded trial proposal — 2026-09-09

Operator sudo inventory reads cryptsetup index 0x1d10201 and hardware index 0x1d10200.
Standard /var/lib/systemd/pcrlock.json and /run/systemd/pcrlock.json are absent. Existing
LUKS token 1 is bound to SHA256 PCR0/7, not a public-key or PCR-lock policy. These scoped
observations find no dependency linking that LUKS token to the old NvPCR anchor; arbitrary
external/custom consumers have not been exhaustively excluded.

Reviewable proposed production scope (awaiting approval):

1. Recheck live identities, preserved recovery backup, ESP space and retained Fedora entry.
2. Stage the already verified RSA2048 UKI as a separate file and uniquely named Type #1 entry
   beside the previous candidate; keep old images, firmware defaults, signing certificate and
   LUKS token 1/keyslot 2 unchanged. Reuse isolated Boot0006 shim/systemd-boot chain.
3. At the physical console, select Boot0006 once and explicitly choose the RSA2048 entry;
   retain manual LUKS unlock. BootOrder baseline for this trial is the observed current
   0001,0008,0003,0000; historical disappearance remains unresolved, not silently accepted.
4. Permit normal systemd boot-time NvPCR setup to generate and persist a new anchor if no
   usable old secondary copy exists. This is replacement anchor identity, not migration.
   Keep the encrypted old-anchor workstation backup; no TPM clear or manual NV deletion.
5. Require Secure Boot, correct UKI and measured boot, successful early/late TPM setup,
   new encrypted-anchor persistence evidence, unchanged LUKS policy and firmware inventory.
   If any gate fails, preserve evidence and return via Fedora; do not enroll new unlock tokens.

Exact next action: obtain explicit authorization for the new-anchor production trial, then
prepare its fixed-hash staging helper and operator handoff. Local candidate construction and
read-only recovery review are complete; hardware repair and automatic unlock remain unpassed.

### RSA2048 production trial approved — 2026-09-09

Approval: user “yes” to the explicit bounded production trial, including possible new NvPCR
anchor creation. Approved scope is the five-step proposal above. Preserve old candidate,
LUKS token/keyslot, encrypted anchor backup and Fedora path. No TPM clear or NV deletion.
Staging 🔄 IN_PROGRESS; required gate: fixed hashes, live baseline, exclusive new files,
helper syntax/ShellCheck and pinned transfer verification. Exact next action: transfer a
guarded staging-only helper; operator performs sudo, then select the separate trial entry.

❌ FAIL / 🔁 STALE: pre-transfer rehash found prior RSA2048 candidate changed after its
recorded validation; sbverify reports no signature table. Earlier objcopy --dump-section
without a separate output rewrote the input image. Prior local candidate validation is
invalidated; the changed file was not transferred. Retained original RSA3072 candidate is
unaffected. Rebuilt from unchanged inputs/key into hermes-production-rsa2048-v2.efi.

Replacement candidate ✅ PASS: builder sections/signature checks and independent read-only
sbverify passed; final hash remained stable before and after verification and matched pinned
SCP destination. SHA256: 9ec0a06a4ac5fc556d8896d19f23146966ee87d66a1f54bc328b7f7f5ff63922.
Guarded helper Bash syntax/ShellCheck passed; its transferred hash matches. Only new image
and helper were copied to fresh mode0700 operator directory hermes-rsa2048-trial-20260909.
No private key transfer, privileged staging, TPM mutation or reboot was performed.
Exact next action: operator executes stage-rsa2048.sh with sudo and returns its output;
require RSA2048_STAGING_OK before the one-shot selection handoff.

### RSA2048 production staging accepted — 2026-09-09

✅ PASS based on operator output: new source hash and retained old chain hashes pass;
helper destination verification and firmware equality pass via RSA2048_STAGING_OK.
The new Type #1 entry hermes-trial-rsa2048-20260909.conf resolves to the v2 image.
Old entry remains displayed default/selected. BootOrder is 0001,0008,0003,0000.
Exact next action: with console and LUKS passphrase ready, operator selects the new
systemd-boot entry once via bootctl set-oneshot and selects Boot0006 via efibootmgr
BootNext. Verify both selections before reboot; then collect correct v2 UKI, Secure Boot,
TPM services, firmware and anchor persistence evidence. Approved new-anchor creation
remains within scope; no automatic LUKS enrollment or old-token removal is authorized.

### RSA2048 one-shot selection verified — 2026-09-09

✅ PASS: operator output shows BootNext 0006 and preserved BootOrder 0001,0008,0003,0000.
Independent pinned SSH decoded only the public loader selection EFI variables:
LoaderEntryOneShot is hermes-trial-rsa2048-20260909.conf; LoaderEntryDefault remains
Talos-v1.11.5.efi. The list display marks the effective next selection as default, not
literally one-shot. No permanent loader-default change occurred.
Exact next action: operator performs the approved single reboot with physical console and
LUKS passphrase, then returns v2 UKI, Secure Boot, TPM service and firmware observations.
Anchor persistence evidence follows before acceptance. No repeat selection writes needed.

### RSA2048 hardware trial result — 2026-09-09

✅ PASS initial candidate boot: operator attachment confirms the v2 UKI, intended Type #1
entry, Secure Boot enabled, measured UKI yes, BootCurrent 0006 and consumed BootNext.
BootOrder remains 0001,0008,0003,0000. SRK identity remains unchanged. Early setup
initialized both NvPCRs. Prior RSA3072 LoadExternal failure is absent from reported logs.

❌ FAIL full TPM setup/persistence: late service wrote the anchor to the standard /var/lib
path but failed ESP credential creation with Permission denied. Independent pinned SSH
confirms rw vfat mount, SELinux Enforcing and exact AVC denial of file create by init_t
on dosfs_t for the temporary nvpcr-anchor credential. Additional AVCs deny init_t writes
to tpm2-measure.log labeled syslogd_var_run_t. These are confirmed SELinux denials, not
a read-only mount. Service ProtectSystem=no; no ReadWritePaths or RootDirectory override.

Installed TPM decoder identifies 0x14c as already-defined NV index (early setup succeeds)
and 0x128 as PCR changed since checked. Late retries preceded successful /var persistence;
do not treat these messages as evidence of successful ESP persistence or TPM corruption.
Exact next action: inspect installed SELinux file labels, expected transitions and shipped
policy for TPM setup, then prepare a narrowly reviewed compatibility repair and validation
gate. Preserve Enforcing, anchors and LUKS token; no automatic audit2allow or TPM clear.
RSA2048 compatibility improves but full trial gate remains unpassed.

### SELinux shipped-policy diagnosis — 2026-09-09

Read-only continuation: installed selinux-policy/targeted 44.8-1.fc44 and systemd
259.8-1.fc44. Live executable init_exec_t and measurement-log syslogd_var_run_t match
matchpathcon; no demonstrated label drift on those paths. VFAT ESP is dosfs_t while
path database suggests boot_t; VFAT lacks ordinary per-file persistent security labels,
so do not infer restorecon is a valid repair from that difference alone.

Upstream Fedora bug 2507393 reports the same init_t/dosfs_t credential-create denial.
PR 3321, Confine systemd-tpm2-setup, remains open/unmerged at inspection. Its patch
introduces an executable type/domain but marks that domain permissive; reject direct
installation as the enforcing production repair. Sources:
<https://bugzilla.redhat.com/show_bug.cgi?id=2507393> and
<https://github.com/fedora-selinux/selinux-policy/pull/3321>.

Cached package query offers installed 44.8 only; this is not a refreshed update check.
Unprivileged rpm -V failed with permission-denied access to policy store; no package
corruption conclusion is warranted. sesearch is unavailable on Hermes. No labels,
policy modules, mount options, packages or services changed.

Diagnosis gate ✅ PASS: shipped policy compatibility gap is supported by matching live
labels, exact AVCs and upstream report. Repair gate ⬜ TODO: prepare a dedicated enforcing
service domain with reviewed TPM/device, credential, ESP and measurement-log access;
compile and inspect against the installed base policy before any production installation.
Validation must prove correct domain transition, successful setup/ESP persistence and no
new scoped AVCs with SELinux Enforcing; preserve rollback and old encrypted anchors.
No generic init_t allow rules, permissive domain, TPM clear or broad audit2allow output.
Exact next action: obtain the installed base-policy/interface inputs and prepare/compile
the isolated local policy candidate; production policy installation requires explicit scope.

### Enforcing SELinux candidate preparation — 2026-09-09

Approval: user “proceed” to local candidate preparation, inspection and a reviewable production
installation/rollback proposal. Production policy installation and service execution remain excluded.
Continue on the existing feature branch and preserve unrelated changes.

| Task | Progress | Required gate | Validation |
| --- | --- | --- | --- |
| SE1: obtain inputs | 🔄 IN_PROGRESS | Pinned host policy, matching Fedora interfaces, hashes | ⬜ TODO |
| SE2: enforcing candidate | ⬜ TODO | Compile, link against copied base, inspect effective permissions and transition | ⬜ TODO |
| SE3: handoff and documentation | ⬜ TODO | Bounded install/rollback, acceptance conditions, documentation checks | ⬜ TODO |

Live read-only probe confirms policy 44.8-1.fc44 and systemd 259.8-1.fc44, SELinux Enforcing.
The host has a readable on-disk policy. Development interfaces are absent on host and workstation;
obtain matching package inputs in an isolated local build environment. No production changes made.
Exact next action: preserve the public policy input and build against version-matched interfaces.

SE1: 🔄 IN_PROGRESS; public on-disk host policy copied with matching pinned SSH SHA256.
Version-matched development interfaces and targeted package obtained in an isolated rootless
Fedora 44 container. Exact installed-store gate 🚧 BLOCKED: unprivileged module-store read
is denied; matching package policy differs from the installed host policy. Operator export
requested using the [canonical input procedure](../HERMES_SELINUX_TPM_REPAIR.md#exact-installed-store-input-gate).

SE2: local candidate complete; matching-package gate ✅ PASS: module compilation and isolated
semodule linking, 19 effective-permission assertions and executable context mapping passed.
The domain is enforcing and no generic init_t ESP/log permissions changed. Type-wide dosfs_t,
init_var_run_t/init_var_lib_t and existing log grants are explicitly documented for review.
No new capabilities or IP socket creation; base daemon/domain permissions remain inherited.
Exact-production compatibility and actual execution remain unpassed. Binary-to-CIL linking
failed on omitted interface information after correcting an MLS flag; do not reconstruct
missing production attributes. Failed attempts and reproducible checks are retained in
[the sanitized observation](evidence/2026-09-09-hermes-selinux-candidate.json).

SE3: proposed installation, acceptance, idempotency and rollback procedure prepared in the
[canonical repair guide](../HERMES_SELINUX_TPM_REPAIR.md). No production module installation,
label change, service restart, TPM operation or reboot occurred. Production approval is not
requested yet because the required exact-store gate is unmet. Existing changes preserved.
Exact next action: receive the operator's private targeted/active policy export, verify its
hash, rebuild an isolated unmodified baseline and compare with the host, then link and inspect
the candidate against that store. Only after this passes prepare the fixed-hash trial helper
and request the bounded installation/service-run scope. UA-05/P2 remains blocked.

Documentation gate ✅ PASS: 217 Hermes guide checks, five repair-guide local links and verifier
Python syntax passed. Initial five-document lint found four pre-existing bare source URLs in
this execution record; formatting them as links preserves the historical claims. Final lint
and whitespace results are recorded with the observation. Local build container stopped and
retained for exact-store continuation; compiled policies and inspection evidence are private.
SE3 local handoff is complete; exact-store input remains the next required gate as above.

### Exact-store continuation check — 2026-09-09

User requested continuation. At 2026-09-09T03:45:07Z, on branch
`codex/hermes-unattended`, a read-only SSH probe to `aicowork@10.0.30.10`
with `BatchMode=yes` and `StrictHostKeyChecking=yes` checked readability of
`/home/aicowork/hermes-selinux-policy-inputs-20260909/targeted-active.tar.gz`.
Expected: readable archive and SHA256. Actual: `POLICY_EXPORT_UNAVAILABLE`, exit 0;
the archive is absent or unreadable at the documented path. The retained local candidate
directory also has no exported archive. No privileged or production mutation occurred.

SE1 progress: 🚧 BLOCKED on operator input. Exact-store validation: ⬜ TODO, not run.
Prior matching-package evidence remains limited to that package baseline.
Exact next action: operator creates the private policy-only export using the
[canonical procedure](../HERMES_SELINUX_TPM_REPAIR.md#exact-installed-store-input-gate),
then transfer with pinned SSH, verify SHA256 and resume isolated baseline/candidate checks.
UA-05/P2 and the production trial remain blocked. No implementation change was needed;
this execution record is the affected documentation.

Documentation validation ✅ PASS: `devbox run -- markdownlint-cli2 docs/plans/2026-09-07-hermes-unattended.md`
reported 0 errors (25 files selected by repository configuration); `devbox run -- git diff --check --
docs/plans/2026-09-07-hermes-unattended.md` exited 0. Checks ran on the working record above during this
continuation; this result note was appended afterward.

### Exact-store validation resumed — 2026-09-09

User supplied the operator export and SHA256 after requesting continuation. Scope remains
local validation and reviewable trial preparation; production installation/service execution is excluded.
Pinned SSH transfer matched `d9687d0fcef3a931ce0edcab4fc7d29b369c7982f6c7aa53116752f48586dc5a`.
All 1,759 archive entries are regular files/directories confined to targeted/active.
Fresh read-only host checks confirm unchanged policy hash, package versions and Enforcing status.
The exported policy.kern hash equals the previously copied and freshly checked host policy hash.
SE1 input acquisition ✅ PASS; SE2 exact-store validation 🔄 IN_PROGRESS.

Required gates, in order: rebuild the unmodified exported store and compare its policy with the host;
link the fixed candidate in a separate store copy and run all permission/context assertions;
prepare a fixed-hash trial helper and validate its failure boundaries locally; synchronize documentation.
Hardware service/persistence acceptance remains separate and requires explicit production approval.
Exact next action: compare the rebuilt baseline, then link and inspect the candidate only if it matches.

SE2 exact-store gate ✅ PASS: corrected isolated rebuild is byte-identical to the current Hermes
policy; candidate link, 19 permission assertions and exact executable mapping passed.
Initial -p/-S path-combination failure is retained in the
[observation](evidence/2026-09-09-hermes-selinux-exact-store.json); its preliminary baseline
claim was invalidated and replaced with the successful rebuild against the exported store.
Source files match the compiled module inputs. No production mutation occurred.

SE3 trial preparation: fixed-hash policy installation helper and canonical guide updated.
Syntax, ShellCheck and missing-approval/corrupt-module rejection checks passed; hardware installation
success remains untested. Helper backs up private policy/anchors and stops before service execution.
The guide remains authoritative for physical-console preflight, domain evidence, service acceptance,
idempotency and rollback. Exact next action: complete documentation validation, then obtain explicit
approval for the bounded production installation and late-service trial. UA-05/P2 remains blocked
until actual service/persistence acceptance; cold boot is a separate gate.

SE3 local review preparation ✅ PASS. Documentation checks: 217 Hermes guide assertions,
four-document nonfix Markdown lint, eight repair-guide local links and whitespace checks passed.
Initial lint failures and the corrected isolated-copy validation method are retained in the observation.
Only policy installation helper syntax and rejection boundaries were executed; live installation remains untested.
Build container stopped and retained after checks completed; private original export and policy outputs retained.
Exact next action: obtain explicit approval for the guide's bounded production trial, including type-wide ESP
permission, policy installation and late-service TPM operations; verify the operator recovery prerequisites first.
Do not reboot or claim UA-05/P2 acceptance until the separate runtime and persistence gates pass.

### Approved production SELinux trial — 2026-09-09T14:03:54.075838+00:00

User approved with “proceed” in response to the bounded production trial and recovery prerequisites.
Scope: stage/install the reviewed policy and run the late setup service once, repeating only after
acceptance passes; no reboot or early-service restart. Approval persists for this scope.
Fresh pinned SSH confirms the validated baseline hash and Enforcing. Noninteractive sudo
requires an operator password; no privileged change was attempted. Local helper/module hashes
match the exact-store observation. Trial progress 🔄 IN_PROGRESS; installation validation ⬜ TODO.
Exact next action: stage the verified artifacts privately, verify remote hashes, then have the operator
run the fixed helper with sudo in their own terminal. Never transmit or capture the sudo password.

Staging ✅ PASS: exclusive mode-0700 directory `/home/aicowork/hermes-selinux-trial-20260909`
created; helper and module transferred with pinned SCP and remote SHA256 matched the exact-store record.
Fresh package versions match. Late unit remains failed/MainPID=0; early unit active/MainPID=0.
No policy installation, relabel, service restart or reboot performed. Installation progress
🚧 BLOCKED on interactive operator sudo; validation ⬜ TODO. Approval is already recorded.
Exact next action: operator runs the staged installation helper at the console with recovery available,
then supplies its non-secret result. Stop before service execution until installation checks pass.

Staging documentation validation: initial two-document lint ❌ FAIL on three duplicate blank lines.
Whitespace check passed. Duplicate blank lines corrected; final two-document lint ✅ PASS, zero errors.

### Production policy installation observed — 2026-09-09T14:07:14.016961+00:00

Operator helper output reports POLICY_INSTALL_VERIFIED. Pinned read-only SSH independently
confirms on-disk policy SHA256 67d4f87afb2df3137fb8ab81f8f260942c3b43238bb275d16826b6c7a2ede8c0,
SELinux Enforcing, and actual/expected executable type hermes_tpm2_setup_exec_t.
Late unit remains failed, MainPID=0, ExecMainStatus=1: service acceptance has not run.
Operator output also reports systemd-boot not installed in ESP and a module filename/name warning.
These messages did not prevent the helper success checks; firmware/recovery acceptance is not inferred from them.
Installation checks ✅ PASS for the helper and independent disk/label observations.
Loaded-kernel policy and off-host encrypted recovery copies remain ⬜ TODO before service execution.
Exact next action: operator exports the loaded policy and root-private installation backups into
an exclusive private directory; transfer with pinned SSH and verify hashes, then inspect loaded-policy
transition and prepare the approved service run with baseline and actual-domain evidence.
No additional restart or reboot was performed in this continuation. Approval persists.

Documentation validation: initial lint ❌ FAIL on one long status line; rewrapped.
Final isolated nonfix three-document lint ✅ PASS, zero errors; whitespace check passed before this note.

### Loaded policy and recovery export continuation

Operator supplied loaded-policy and encrypted recovery export hashes. Pinned SCP copies match both.
Private archive path/type checks passed; required policy and runtime/persistent encrypted-anchor
backups are present. Recovery transfer ✅ PASS. Loaded-policy semantic comparison 🔄 IN_PROGRESS;
binary hash differs from on-disk policy, so service execution is blocked pending explanation.
Approved scope remains one late-service trial with a repeat only after acceptance; no reboot.
The single-run observation helper is prepared locally. Its acceptance gate requires actual process
domain observation, exact zero service exit, working audit capture without new scoped denials,
matching anchor copies and preserved SRK/LUKS metadata/firmware/policy/label with Enforcing.
Fixture checks reject exit 76, missing domain evidence, AVC/audit failures and preservation drift.
Exact next action: finish the loaded-policy comparison, then stage the helper only if that gate passes.

Loaded-policy gate ✅ PASS: expected and kernel-exported binaries convert to byte-identical CIL
with checkpolicy -b -C -M; seinfo properties/counts match. Direct loaded-policy inspection confirms
the intended init transition and enforcing candidate domain. The full sediff attempt was terminated
after seven minutes and about 8 GiB RSS; no result is claimed for it. Methods and hashes are in the
[loaded-policy observation](evidence/2026-09-09-hermes-selinux-loaded-policy.json).
The loaded policy differs in binary representation without a detected represented-policy change.
Off-host encrypted backup and loaded-policy prerequisites now pass.
Exact next action: stage the hashed single-run helper and have the operator invoke it with sudo;
review its sanitized result before allowing the already-approved second run. No service ran here.

Service-helper staging ✅ PASS: pinned transfer remote SHA256 matches the loaded-policy observation.
Execution progress 🚧 BLOCKED on interactive operator sudo; approval already exists.
Exact next action: operator runs the staged helper with --approved-first-run, then supplies its sanitized
summary. Do not repeat the service until the first-run acceptance evidence is reviewed.

Final documentation check: initial lint ❌ FAIL on a long helper-status line; rewrapped.
Three-document nonfix lint ✅ PASS after correction. Guide check passed 217 assertions; whitespace passed.
Build container stopped after inspections, with private artifacts retained.

### First service trial failed — 2026-09-09T14:46:24.729742+00:00

Operator ran the staged first-run helper. Audit collection stopped on a rejected date format.
Independent pinned SSH confirms the late unit ran on 2026-09-09 from 09:43:14 to 09:43:16 -05,
then exited 1 (Result=exit-code). Policy hash, executable label and Enforcing remain as validated.
The unit journal reports permission denied probing /dev/nvme0n1p2 and locating XBOOTLDR;
it reports existing SRK matches and two NvPCRs already initialized. Root audit evidence is still required
to identify the denied access precisely. No successful persistence acceptance is inferred.

First-run validation ❌ FAIL. Dependent repeat 🚧 BLOCKED, since approval allows a repeat only after success.
Helper audit collection ❌ FAIL: LC_ALL=C ausearch rejects 09/09/2026; the corrected 09/09/26
passes parsing but unprivileged access to audit configuration/logs is denied. A concurrent Devbox read
raced on .cmd.sh and was repeated serially; no production operation ran in that failed local call.
The helper also saved post-run state and process-domain observations only after audit collection,
so these in-memory observations were lost on the query failure. Do not reconstruct them as observed.

Authorized continuation: preserve failed evidence, recover state and scoped audit records without
a service restart, and fix local evidence persistence/date handling. Required gates: safe read-only
recovery helper, regression checks for audit failure retention/date formatting, synchronized records.
Exact next action: stage read-only recovery collection for operator sudo; preserve current encrypted
anchors before any policy rollback. No new policy, restart or reboot is authorized by this failure.

Local evidence fix ✅ PASS: syntax and query-error retention/empty-result/AVC checks passed.
Recovery-helper staging ✅ PASS: remote SHA256 matches local; original deployed helper retained.
[Failure observation](evidence/2026-09-09-hermes-selinux-first-run-failure.json) records exact findings and limits.
The old loaded-policy observation still identifies the historical helper; corrected local code does not
upgrade the failed run. Privileged recovery 🚧 BLOCKED on operator sudo, not additional approval.
Exact next action: operator runs recover-first-service.py and supplies its sanitized result/archive hash;
retrieve and inspect the evidence before rollback or considering a revised policy trial.

Documentation gate ✅ PASS: 217 Hermes guide assertions, four-document nonfix Markdown lint,
11 repair-guide local links and git diff --check passed before this result note.
Next action remains the operator read-only recovery command; first-run acceptance remains ❌ FAIL.

### Failed-trial recovery verified — 2026-09-09T15:50:35.153518+00:00

Pinned recovery transfer matches operator SHA256
61ccca46c39741583770c1bca31f819be98951c651ab18dfceba4ba4d3f0332e.
Archive paths/types and encrypted-anchor content hashes match the recorded recovery snapshot.
Recovery gate ✅ PASS: original/current anchors, SRK, LUKS metadata, firmware, loaded policy and
executable label are preserved, with Enforcing. ESP anchor is absent; first service acceptance remains ❌ FAIL.
The three scoped AVCs identify the dedicated enforcing domain and deny nsfs_t:file getattr,
cert_t:dir search, and fixed_disk_device_t:blk_file read on nvme0n1p2. This confirms the observed
block-device probe denial. Whole-run audit continuity remains unknown: the false recovery field
represents missing original observations, not proof of lost audit records.

Approved failed-trial rollback now follows the canonical procedure: preserve old/new encrypted
anchors (complete), remove only the trial priority-400 module, restore the exact executable label,
verify the original on-disk policy hash, then stop for repair review. No TPM, anchor, token or firmware
changes, restart or reboot are in this rollback. Required rollback-helper gate: hash/label/module
guards, syntax/ShellCheck/format checks and retained result evidence.
Exact next action: stage the guarded rollback helper for operator sudo; a revised permission set
and any new service trial require review beyond the failed first-run gate.

Rollback preparation/staging ✅ PASS: syntax, ShellCheck, formatting and missing-argument rejection
checks passed; pinned remote hash matches the [recovery observation](evidence/2026-09-09-hermes-selinux-recovery.json).
Rollback execution 🚧 BLOCKED on interactive operator sudo. No rollback or restart performed.
Exact next action: operator runs rollback-reviewed-candidate.sh --approved-trial-rollback;
verify reported success independently and stop for revised-policy/recovery review.

Documentation validation: 217 guide checks passed. Initial lint ❌ FAIL on a duplicate blank line;
corrected four-document nonfix lint ✅ PASS. Whitespace check passed before this result note.

### Failed-trial rollback verified — 2026-09-09T17:57:26.186789+00:00

Rollback progress complete; gate ✅ PASS. The operator reports successful removal of the last trial
module. Independent pinned SSH confirms the original on-disk policy SHA256, init_exec_t actual/expected
label and Enforcing. The service still records the same failed first invocation; no newer start occurred.
See the [rollback observation](evidence/2026-09-09-hermes-selinux-rollback.json) for exact evidence and limits.
No fresh privileged kernel-policy or TPM/recovery snapshot was claimed after rollback. Preserved prior
recovery evidence remains authoritative for its observation time.

This closes only the approved failed-trial rollback, not UA-05/P2 or the unattended deployment plan.
First-run acceptance remains ❌ FAIL; persistence/repeat gates remain 🚧 BLOCKED.
Exact next action: review the smallest permission set for namespace metadata, certificate traversal and
partition probing; prepare and validate a revised candidate locally before proposing another bounded trial.
The recorded AVCs are evidence for review, not authorization to apply broad generated allow rules.
No additional production policy, service retry or reboot is authorized by this closure.

Documentation gate ✅ PASS: 217 guide assertions, four-document nonfix Markdown lint, 14 local
repair-guide links and git diff --check passed before this result note. Exact next action remains
local revised-policy review; no operator command is pending for the completed rollback.

### Revised SELinux candidate local scope — 2026-09-09

Approval reference: user “proceed” after the local revised-policy next-step proposal.
Scope: local policy review, isolated build/inspection, validation evidence and trial proposal.
Existing feature branch codex/hermes-unattended retained; unrelated changes preserved.
No production installation, service execution or reboot is included.

| Task | Dependency | Progress | Required validation gate |
| --- | --- | --- | --- |
| SE4 permission review | completed rollback | ✅ PASS | Three scoped AVCs reviewed; v259 find-esp source supports read-only probing; caller uncertainty recorded |
| SE5 revised candidate | SE4 | ✅ PASS | Exact baseline hash; compile/link, 31 permission/delta assertions and mapping passed |
| SE6 review handoff | SE5 | ✅ PASS | Fixed artifacts, negative control, 217 guide assertions, four-document lint, 17 links and whitespace passed |

Earlier candidate passes remain historical and do not validate revised artifacts.
Exact next action: inspect retained source and policy inputs, then implement the justified permissions.

### Revised local validation result — 2026-09-09

SE4 and SE5 ✅ PASS: candidate 1.1.0 compiles and links in the retained isolated Fedora 44 container.
The baseline rebuild matches the recorded original disk policy. All 31 permission/delta assertions
pass, with exactly three new TE rules and unchanged type attributes and executable mapping.
The original 1.0.0 policy is a negative control: the revised verifier rejects exactly its three missing
permission sets. A shell wrapper status-expansion failure is retained in the evidence; the independent
negative-result JSON check passes without claiming the wrapper preserved the verifier exit status.

The [revised evidence](evidence/2026-09-09-hermes-selinux-revised.json) pins source, verifier, module
and v2 installer hashes, methods, environment and limitations. Original private artifacts and first-trial
helpers are retained. The new installer uses an exclusive v2 backup directory and passes syntax,
ShellCheck, formatting and three pre-mutation rejection checks. No production access occurred.

SE6 ✅ PASS: 217 guide assertions, four-document nonfix lint, 17 local file links and whitespace checks.
The canonical
[installation proposal](../HERMES_SELINUX_TPM_REPAIR.md#revised-installation-proposal) requests only
policy installation, read-only loaded-policy/recovery validation and guarded policy/label recovery.
It records type-wide raw-device read exposure. The existing first-run helper remains pinned to the old
loaded policy, so a service restart requires a separately prepared helper and approval after that gate.
UA-05/P2 and cold-boot persistence remain 🚧 BLOCKED. The overall deployment plan remains open.
Exact next action: obtain explicit approval for the revised installation scope. Local SE4–SE6 work is complete.

### Revised production installation approval — 2026-09-09T18:47:31.027346+00:00

Approval reference: user “approved” following the fixed revised-candidate installation proposal.
Scope: installation, read-only loaded-policy/backup verification, and bounded policy/label rollback
if needed. No setup service restart, TPM operation or reboot is included. Approval persists.

| Task | Dependency | Progress | Required gate |
| --- | --- | --- | --- |
| SE7 stage/install v2 | SE4–SE6 | ✅ PASS | Operator helper success; independent hash, label, package and Enforcing checks |
| SE8 loaded policy/recovery | SE7 | ✅ PASS | Pinned hashes, safe preserved backups, identical CIL, matching properties/counts and direct transition/domain checks |

Current source/module hashes must match the reviewed evidence before transfer. Operator sudo may
be required; never collect or transmit the password. Existing feature branch and unrelated changes retained.
Exact next action: verify read-only host baseline and stage the reviewed artifacts privately.

SE7 staging ✅ PASS: live policy hash, versions, actual/expected label and Enforcing match the
reviewed baseline. Late/early MainPID=0; late service retains its original failed invocation.
The exclusive mode-0700 v2 directory contains mode-0600 reviewed module/installer and export helper;
all remote hashes match local artifacts. Noninteractive sudo requires a password.
Installation progress 🚧 BLOCKED on interactive operator sudo; installation validation ⬜ TODO.
SE8 export preparation ✅ PASS: allowlisted archive, private modes, policy/backup guards and exclusive
output are implemented; the retained offline fixture passes success and rejection boundaries.
Initial inline fixture ❌ FAIL from missing account mock; corrected retained test ✅ PASS.
Live export and loaded-policy equivalence remain ⬜ TODO, dependent on successful installation.

See [staging evidence](evidence/2026-09-09-hermes-selinux-v2-staging.json) and the
[operator handoff](../HERMES_SELINUX_TPM_REPAIR.md#approved-v2-operator-handoff).
Exact next action: operator runs the two-command guarded installation/export sequence and returns
its sanitized result. Approval already exists; no further approval or password disclosure is requested.
No policy installation, relabel, setup service restart, TPM operation or reboot occurred in this turn.

Handoff validation: 217 guide assertions ✅ PASS. Initial five-document lint ❌ FAIL on the updated
status line length; rewrapped that line and rerunning the bounded documentation gate.

Final handoff documentation gate ✅ PASS: five-document nonfix lint, 19 repair-guide local file links
and git diff --check. No additional implementation change invalidated the export fixture pass.
Exact next action remains the approved operator installation/export command; installation and loaded-policy
validation are pending, with no further approval needed for their recorded scope.

### V2 installation reported; verification underway — 2026-09-09T19:32:06.644165+00:00

The operator reports POLICY_INSTALL_VERIFIED and successful policy/recovery export with 11 files.
Scope remains the approved installation and read-only verification; no service execution or reboot.
SE7 independent installation verification and SE8 transfer/comparison are 🔄 IN_PROGRESS.
The systemd-boot and module-name messages are retained as operator observations; the helper's
success does not establish boot or runtime acceptance.
Exact next action: verify pinned host state, transfer the exports and compare the approved candidate.

SE7 ✅ PASS: operator installation success independently confirmed by pinned SSH: expected disk
policy hash, matching dedicated executable label/mapping, correct package versions and Enforcing.
Late/early service start timestamps remain unchanged with MainPID=0. The late service is still failed
from the first trial; this is not a new runtime result.

SE8 transfer/archive ✅ PASS: both hashes match the operator, all 11 outer members are safe allowlisted
regular files, original store policy and reviewed module hashes match, and encrypted anchors match
both each other and preserved failed-trial recovery copies. Remote/local export directory/archive
permissions are private. Nested policy-store paths/types and its original policy hash pass inspection.
Two initial mode assertions ❌ FAIL: they incorrectly required source mode 0600 for preserved public
policy/encrypted anchors. Reassessment against cp --preserve=mode and original backups confirms unchanged
0644 member modes inside the private archive. Corrected preservation/privacy checks ✅ PASS; no modes changed.

Loaded-policy CIL comparison ✅ PASS: checkpolicy conversion of expected/loaded policies is identical;
direct SETools checks confirm the init transition and enforcing candidate domain. Final property/count
comparison and documentation gate are in progress. No production mutation or service execution in this continuation.
Exact next action: finalize the loaded-policy evidence and documentation; runtime/persistence remain separate gates.

### V2 installation and loaded-policy gates verified

SE7–SE8 ✅ PASS. The loaded kernel-policy binary differs from the disk binary, as retained in the
[installed observation](evidence/2026-09-09-hermes-selinux-v2-installed.json), but CIL conversion is
identical and normalized seinfo properties/counts match. Direct transition/domain checks also pass.
All approved installation/export verification is complete; no policy rollback is indicated by these checks.
The earlier failed service trial remains ❌ FAIL; revised service execution and persistence remain ⬜ TODO.
UA-05/P2 is still 🚧 BLOCKED on runtime/persistence acceptance, and the overall plan remains open.

Exact next action: prepare and validate a v2 first-run observation helper pinned to the verified loaded
policy and new backup path, then obtain explicit approval for one bounded late-service trial. No service
execution, early-unit restart or reboot is authorized by the completed installation scope.

Final verification documentation gate ✅ PASS: 217 guide assertions, four-document nonfix lint,
20 repair-guide local links and git diff --check. Comparison container stopped and retained after
all checks completed. No production rollback was needed. Exact next action remains local preparation
of the v2 first-run helper, followed by explicit service-trial approval; no operator command is pending.

### V2 single-service preparation authorized — 2026-09-09

Approval reference: the user confirmed the next task is preparing the guarded v2 single-service trial
for explicit approval, then instructed "proceed". Scope: local helper, offline adversarial validation,
and reviewable operator procedure. Continue on the existing `codex/hermes-unattended` branch;
preserve unrelated uncommitted work and historical trial artifacts. Production staging, service execution,
repeat, rollback and reboot are not authorized by this preparation request.

| ID | Task / dependency | Progress | Required validation gate | Validation |
| --- | --- | --- | --- | --- |
| SE9 | Separate guarded v2 first-run helper; SE7–SE8 | ✅ PASS: complete | Pin verified loaded/disk policy and v2 backups; reject drift, busy units and reuse; exactly one late-service request; retain private observations on failure | ✅ PASS: pinned hashes and boundary review |
| SE10 | Offline adversarial validation; SE9 | ✅ PASS: complete | Reject unauthorized/drifted/repeated runs before restart; audit errors, exit 76, missing domain, changed metadata and timeout never pass; no automatic recovery | ✅ PASS: 32 tests, syntax and local parser |
| SE11 | Approval handoff and documentation; SE10 | ✅ PASS: complete | Exact scope, hashes, acceptance and recovery limits; guide assertions, focused nonfix Markdown lint, local links and diff whitespace | ✅ PASS: 217 guide assertions, handoff syntax/ShellCheck, five-document lint, 37 links and whitespace |

Affected documentation: [canonical repair procedure](../HERMES_SELINUX_TPM_REPAIR.md),
[evidence ledger](../HERMES_INSTALLATION_VERIFICATION.md),
[ordered deployment tasks](../../vm/DEPLOYMENT_TASKS.md), and contributor test command.
Validation records will include UTC time, local environment, commands/results and artifact hashes.
Required runtime/idempotency/cold-boot gates remain open; local simulation cannot close UA-05/P2.
Exact next action: implement the separate v2 helper and validate all preflight and failure boundaries
before presenting a bounded production trial for explicit approval.

SE9 implementation complete; SE10 validation 🔄 IN_PROGRESS. The separate helper pins the verified
v2 loaded/disk policy and recovery payload hashes, guards both setup units, verifies the effective
single-command contract, rejects failure/reboot hooks and pending dependency work, and reserves one
exclusive result directory. Audit parser validation runs before any restart; process, service, audit,
journal and encrypted-anchor evidence are collected independently where possible.

Initial offline validation ✅ PASS: 28 synthetic-state tests. Source review then added guards for
systemd failure actions/stop propagation and refreshed audit state immediately before execution.
The earlier pass is 🔁 STALE for those additions; the affected suite passed again with 29 tests.
No failed test run, production staging, live service execution or reboot occurred. Remaining SE10 work:
validate real local CLI representation and syntax, then record final artifact hashes and documentation.
Exact next action: finish offline boundary validation and prepare the explicit approval handoff under SE11.

SE10 compatibility check found that local `systemctl show` omits an empty ExecStartPre without
`--all`; its omission would have blocked the proposed live preflight. The new regression reproduced
this: ❌ FAIL, 30 tests with one failure in test_unit_show_requests_empty_properties_and_rejects_missing_fields
(missing --all). Previous passes are 🔁 STALE for this correction. Added --all to the bounded property
query; no service ran. Exact next action: rerun the affected suite and the corrected local representation
check, then finish SE11 documentation validation.

SE10 final validation ✅ PASS: 31 tests, Python syntax and a real read-only workstation unit parser
check. The second CLI probe showed that --all still omits empty command arrays. Rather than treating
omission as empty, the helper now confirms the five supported hooks through typed D-Bus values.
An exploratory query of ExecStopPre failed because v259 does not expose it; source inspection confirmed
that it is not part of the final supported hook list. These unsuccessful probes and the regression failure
are preserved in [preparation evidence](evidence/2026-09-09-hermes-selinux-v2-service-preparation.json).
The helper also rejects ExecCondition and Upholds. All final guards pass their affected offline tests.

SE11 🔄 IN_PROGRESS: the canonical repair guide now contains the proposed approval scope, fixed helper
hash, root-private operator command, acceptance and recovery limits. The evidence ledger, ordered tasks
and contributor test command are synchronized. Exact next action: validate those documents and the
proposed shell handoff, inspect the scoped changes, then request explicit staging/single-service approval.

SE11 command validation: guide assertions ✅ PASS; operator handoff syntax and ShellCheck ✅ PASS;
diff whitespace ✅ PASS. Markdown lint ❌ FAIL on four duplicate blank lines added in this continuation.
Removed only those extra blank lines. Final source review also found that repeated ExecStart properties
could otherwise overwrite one another during parsing; the helper now rejects duplicate property rows,
with a regression covering an extra command followed by the approved executable. Prior source hashes and
31-test evidence are 🔁 STALE for this added boundary; the historical results remain in the evidence record.
Exact next action: validate the final 32-test helper, refresh its approval hash, then rerun affected
Markdown/links/handoff checks and complete SE11. No production action occurred.

Final source validation ✅ PASS: 32 tests, Python syntax and the real local property parser, with
final helper hash recorded in the preparation evidence and approval handoff. Final guide assertions
✅ PASS: 217/217; shell handoff syntax/ShellCheck ✅ PASS; 37 local links and fragments ✅ PASS;
source/patch whitespace ✅ PASS. The second Markdown pass still failed on one blank line at the
boundary before this continuation; the first edit normalized only the new section. Inspected that exact
boundary and normalized it without changing the preceding historical text. Preserve both failed lint
logs; only the affected documentation/closure checks need repeating.
Exact next action: finish the corrected nonfix Markdown gate, record SE11 completion and request the
proposed staging/single-service approval. Runtime and cold-boot acceptance remain open.

### V2 trial preparation complete; execution approval pending

SE9–SE11 ✅ PASS. The separate helper and tests are finalized, the operator handoff pins the verified
helper SHA-256, and all required local gates passed: 32 tests, syntax, real read-only workstation property
parsing, 217 guide assertions, shell handoff syntax/ShellCheck, five-document nonfix lint, 37 local links
and whitespace. Artifact identities, exact methods, environment, UTC timestamps, retained failures and
limitations are in the [preparation evidence](evidence/2026-09-09-hermes-selinux-v2-service-preparation.json).
The final blank-line corrections apply only to this continuation and its boundary; historical work is preserved.

No Hermes connection, staging, production mutation, service execution, commit or push occurred in this
preparation. Runtime, repeat/idempotency and cold-boot acceptance remain ⬜ TODO; UA-05/P2 remains
🚧 BLOCKED and the overall deployment plan stays open. No prior runtime failure is upgraded.
Exact next action: obtain explicit approval for the repair guide's private staging, one console-supervised
late-service invocation and read-only result review. Then verify the pinned host and artifact, stage the
helper, and provide the prepared operator command. No production operator command is pending before approval.

### V2 single-service staging and trial authorized — 2026-09-09T20:43:08.372473+00:00

Approval reference: the user instructed "proceed" after the explicit next-step explanation covering
private staging, one physical-console-supervised late-service invocation, TPM/encrypted-anchor effects,
and read-only review. This authorizes the concrete procedure prepared under SE9–SE11. Honor the existing
operator-confirmed password rotation and console/manual LUKS recovery prerequisites. No new permission
request is needed for this scope. Repeat/idempotency, early-service restart, policy/anchor recovery,
TPM clearing, LUKS changes and reboot remain outside this authorization.

| ID | Task / dependency | Progress | Required validation gate | Validation |
| --- | --- | --- | --- | --- |
| SE12 | Pinned host verification and private helper staging; SE9–SE11 plus current approval | ✅ PASS: complete | Prepared helper hash unchanged; strict pinned SSH identity; live unprivileged baseline matches; exclusive private file with matching hash | ✅ PASS: live checks and independent remote verification |
| SE13 | One operator-supervised late-service trial; SE12 | 🚧 BLOCKED: preflight failed; exclusive attempt consumed | Root preflight and all runtime acceptance checks in the canonical procedure; preserve private evidence on failure | ❌ FAIL: operator preflight RuntimeError; no service request reported |
| SE14 | Read-only result review and documentation; SE13 | ✅ PASS: failure review complete | Verify sanitized result against retained observations; keep persistence/repeat gates open; scoped guide/lint/link/whitespace checks | ✅ PASS: operator retained-file diagnostic plus independent CLI reproduction; runtime not performed |

Validation records will identify UTC time, environment, commands/methods, artifact hashes and observed
limits. Affected documents: canonical repair procedure, evidence ledger and ordered deployment tasks.
No live trial has run in this continuation. Exact next action: inspect pinned SSH settings and verify the
live unprivileged host baseline, then exclusively stage the unchanged helper and provide the approved
operator command. Preserve all unrelated local work and historical failed evidence.

### V2 service helper staged; approved operator execution pending

SE12 ✅ PASS: pinned SSH confirms hostname, Enforcing, reviewed disk-policy SHA-256, dedicated actual
and expected executable context, package versions and unchanged late/early invocation timestamps with
MainPID/ControlPID zero. The late unit still retains the original failed trial. The unchanged reviewed
helper was exclusively created mode 0600 in the existing operator-owned mode-0700 staging directory;
a separate pinned read-only SSH check confirms bytes, owner, modes, regular type and no symlink components.
See the [staging observation](evidence/2026-09-09-hermes-selinux-v2-service-staging.json).

SE13 progress 🚧 BLOCKED on interactive operator sudo; validation ⬜ TODO. The noninteractive sudo probe
requires a password. No service request, TPM operation, policy change or reboot occurred. Full privileged
kernel-policy, backup, audit and TPM/storage guards remain for the helper; these are not live staging passes.
SE14 result review remains 🚧 BLOCKED on trial observations. Handoff documentation validation is
✅ PASS; unchanged source/test hashes retain the completed offline gates.

Exact next action: operator runs the [approved command](../HERMES_SELINUX_TPM_REPAIR.md#approved-v2-single-service-operator-handoff)
once on Hermes with physical console and working manual LUKS recovery available, then returns the sanitized
summary. Approval already covers this scope; no repeated approval or password disclosure is requested.
Stop and preserve evidence on any failure; do not bypass the exclusive trial guard. Runtime,
repeat/idempotency and cold-boot acceptance remain open; UA-05/P2 and the overall plan remain blocked/open.

Handoff checks: 217 guide assertions, command syntax/ShellCheck, 40 local file/heading links and diff
whitespace ✅ PASS. Initial four-document Markdown lint ❌ FAIL on one overlong approval-scope line;
rewrapped that line without changing scope or the operator command. The failed log is preserved in the
staging evidence; final corrected Markdown/closure validation is ✅ PASS. No source change
invalidated the retained 32-test helper validation. Exact next action remains the approved operator
command; service execution and result review await interactive sudo and the returned sanitized summary.

### V2 preflight stopped before service request — 2026-09-09T23:12:13.163535+00:00

Operator reports the approved helper hash verified, followed by passed=false, service_requested=false,
empty checks and RuntimeError in phase preflight at 2026-09-09T23:10:56.604573+00:00. SE13 validation
❌ FAIL; execution remains 🚧 BLOCKED. This is a preflight failure, not a new failed service invocation.
The sanitized summary does not identify the failed operation. The reviewed helper discards exception
messages; retained intermediate files and bounded read-only diagnostics are needed to narrow the cause.

SE14 progress 🔄 IN_PROGRESS; validation ⬜ TODO. Existing approval covers read-only result review.
Gate: independently inspect both units, compare retained observations where accessible, and identify
which preflight guard failed without invoking trial/main or changing production files. Preserve the copied
helper and exclusive service-first directory; do not delete/rename either or repeat the service command.
No restart, recovery, policy change or reboot is authorized by this diagnostic continuation.
See the [failure observation](evidence/2026-09-09-hermes-selinux-v2-preflight-failure.json).
Exact next action: pinned read-only unit/host inspection, then a minimal operator diagnostic only if
root-private evidence is inaccessible. Runtime, repeat/idempotency and cold-boot gates remain open.

Read-only diagnosis: both units retain the SE12 invocation IDs/timestamps and MainPID/ControlPID zero;
Enforcing and reviewed disk-policy hash match. Effective service command/hook guards pass. The first
live diagnostic failed when the helper's command wrapper discarded a failing dependency query. An
independent collector then reproduced systemctl rejecting the required root mount, -.mount, as an option.
The query lacks the end-of-options marker. Preserve both diagnostics in the failure observation.
This establishes a helper defect; protected preflight evidence is still needed to attribute the original stop.

| ID | Task / dependency | Progress | Required validation gate | Validation |
| --- | --- | --- | --- | --- |
| SE15 | Local dependency-query correction; SE14 reproduced CLI defect | ✅ PASS: local correction complete | Preserve original artifact; regression reproduces root-mount option parsing; corrected query accepts active root mount and still rejects inactive dependencies; full affected suite and read-only live query | ✅ PASS: 33 tests, syntax and live read-only corrected root query |

The correction is local only and leaves the exclusive trial directory unchanged. The original bytes are
preserved privately and remain unchanged on Hermes. Original source validation becomes 🔁 STALE for the
changed local artifact; historical results and the failed production preflight remain. No new service
attempt or guard bypass is authorized. Exact next action: reproduce the defect in a regression, correct
only the dependency query, and prepare minimal read-only operator evidence inspection.

SE15 ✅ PASS: the new GNU-option-parser regression reproduced the original -.mount failure (33 tests,
one error). The one-line correction adds -- before the dependency unit operand. All 33 tests now pass;
helper/test syntax passes and the pinned live corrected read-only query returns active. No trial path,
acceptance rule or exclusive guard changed. Remote original artifacts remain untouched; original bytes
are also preserved in a private local copy. Source hashes and failed/passing evidence are recorded.

SE14 remains 🚧 BLOCKED on root-private observations; independent unprivileged review is complete.
The canonical guide marks the former service command historical and provides a minimal read-only
operator diagnostic under existing review authorization. Documentation/diagnostic validation is
✅ PASS. Exact next action: operator runs the
[read-only diagnostic](../HERMES_SELINUX_TPM_REPAIR.md#read-only-v2-preflight-diagnosis) and returns its
sanitized JSON to establish the original stopping point. No rerun, staging, recovery or reboot follows
until protected evidence is reviewed and a concrete continuation is defined.

Failure-review handoff validation ✅ PASS: 217 guide assertions, diagnostic Python/shell syntax and
ShellCheck, four-document nonfix Markdown lint and diff whitespace. The first local-link checker
❌ FAIL was a validator false positive: it parsed a Python subscript/call inside the diagnostic code fence
as a Markdown link. Reassessed the method to exclude fenced code; corrected local links and final closure
pass. Both validator observations remain in the failure evidence. No service action, remote write or
reboot occurred during diagnosis; exact next action remains the read-only operator diagnostic above.

### V2 protected preflight evidence reviewed; guarded continuation — 2026-09-09T23:23:13.823046+00:00

The operator diagnostic reports before.json present; audit-before.json, audit-preflight.json,
process-observation.json and restart.log absent. Rechecking the frozen original helper against the retained
snapshot fails at systemctl during preflight. Combined with independent reproduction of -.mount option
parsing, success of the corrected query and unchanged unit invocation IDs, SE14 failure review ✅ PASS.
The exact command was not durably captured by the original helper; this limitation remains recorded.
SE13 preflight failure remains ❌ FAIL and does not become runtime acceptance.

Scope decision: the user already authorized private staging, one console-supervised service invocation
with TPM/encrypted-anchor effects, and result review. No service invocation occurred. A guarded continuation
of that same single invocation stays within the existing approval; no repeated permission request is needed.
Do not delete, rename, overwrite or reuse the original helper/result directory. Require its exact failed
summary, only the two expected files, original helper identity, unchanged saved/current state and no request
markers. Use a separate fixed continuation directory with its own exclusive reservation; preserve the
original evidence before/after and reject any continuation reuse. No retry/idempotency invocation, early
service, rollback, TPM clear, LUKS change or reboot is included.

| ID | Task / dependency | Progress | Required validation gate | Validation |
| --- | --- | --- | --- | --- |
| SE16 | Guarded continuation wrapper; SE14–SE15 | ✅ PASS: complete | Pin corrected/original code, exact prior failed state, no request markers; exclusive new directory; unchanged runtime guards; preserve original evidence; private failure diagnostics | ✅ PASS: source review and 52 offline tests |
| SE17 | Continuation validation and documented handoff; SE16 | ✅ PASS: complete | Reject drift/tampering/missing evidence/reuse; no service call before all guards; inherited 33 tests; syntax, guide, Markdown, links, exact hashes | ✅ PASS: 52 tests, syntax, 217 guide checks, shell/copy fixtures, lint and 48 links |
| SE18 | Private staging and one operator continuation; SE17 | 🚧 BLOCKED: continuation preflight failed | Live unprivileged baseline unchanged; staged hashes/private modes; root guards then at most one real service invocation; inspect resulting evidence | Staging ✅ PASS; preflight ❌ FAIL; service not requested per operator |

Affected documents: canonical repair guide, evidence ledger, ordered tasks and contributor test command.
The local-only correction remains pinned to its verified hash. Exact next action: implement and validate
the continuation without changing original attempt evidence, then stage under existing scope and provide
the one operator command. Save validation failures, artifact hashes and remaining gates before handoff.

SE16 wrapper implementation complete. It pins the exact original/corrected source, exact failed summary,
root ownership/private modes, only two prior files and recorded invocation identities. It preserves that
attempt, compares both fresh preflight snapshots with the saved baseline and adds prior-evidence
preservation to acceptance. The same corrected core retains one restart request and existing stop gates.
Private diagnostics now retain failing command arguments/operation reasons without printing raw data.

Initial SE17 offline validation ✅ PASS: 51 tests (33 core and 18 continuation). Review added a regression
for byte changes in prior evidence between admission and service request, even when JSON values are equal.
Earlier suite evidence is 🔁 STALE for the changed test artifact; source behavior is unchanged.
Exact next action: final affected tests, pinned live baseline and documented handoff validation before
private staging under the existing one-invocation scope. No production mutation occurred in preparation.

Final source validation ✅ PASS: 52 tests (33 core plus 19 continuation), Python syntax and artifact hashes.
Fresh pinned SSH confirms unchanged units, Enforcing, disk policy, labels/packages and original staged hash;
the corrected root-mount query reports active and both new staging names are absent. Noninteractive sudo
still needs a password. SE17 command/document checks are 🔄 IN_PROGRESS; exact next action is complete
those gates, then exclusively stage and independently verify both reviewed artifacts. The operator handoff
uses explicit existing-file rejection plus shell noclobber; it cannot overwrite either root destination.
No service request or production write has occurred in this continuation preparation.

SE17 ✅ PASS: 52 offline tests and syntax; 217 guide assertions; shell syntax/ShellCheck; five-document
nonfix lint; 48 local links; diff whitespace. Five disposable copy/hash fixtures pass: clean private copy,
existing destination, dangling symlink, an intervening destination protected by noclobber, and hash mismatch.
No privileged helper was executed in these fixtures. Exact reviewed hashes are recorded in the continuation
evidence and canonical handoff. SE18 staging is 🔄 IN_PROGRESS under the previously approved one-invocation
scope; runtime validation remains ⬜ TODO. Exact next action: create the two private staging files exclusively,
verify their remote bytes/modes independently, and hand off the operator command.

### Guarded v2 continuation staged; operator command pending

SE16–SE17 ✅ PASS. SE18 staging ✅ PASS: two exclusive mode-0600 files in the operator-owned mode-0700
directory; independent pinned SSH verifies both approved hashes and the unchanged original helper.
Fresh unit identities/timestamps, idle processes, Enforcing, disk-policy hash, labels and packages match
the earlier baseline. The corrected root-mount query returns active. Evidence is in the
[continuation observation](evidence/2026-09-09-hermes-selinux-v2-continuation.json).

SE18 operator execution is 🚧 BLOCKED on interactive sudo; runtime validation ⬜ TODO. Full protected
prior-file/summary/hash, snapshot, policy/backup and audit checks will run before any service request.
Only the two new operator staging files were created; no original helper/result files changed, no service
request or TPM/LUKS/policy action occurred, and no reboot, commit or push was performed.

Exact next action: with physical console and working manual LUKS recovery available, operator runs the
[guarded continuation command](../HERMES_SELINUX_TPM_REPAIR.md#v2-continuation-operator-handoff) once and
returns the sanitized summary. Existing approval covers that first real service invocation. Preserve both
attempt directories and all helpers on any failure; do not remove/rename guards. Runtime, repeat/idempotency
and cold-boot acceptance remain open; SE13's original preflight failure and UA-05/P2 block remain recorded.

Final handoff documentation closure ✅ PASS after the staging-status update. Source hashes and
52-test results remain current; no implementation changed after those checks.

### V2 continuation preflight failure reported — 2026-09-09T23:40:41.420736+00:00

Operator verifies both copied artifact hashes and reports a second preflight RuntimeError at
2026-09-09T23:39:18.235067+00:00, with passed=false, service_requested=false and empty checks.
SE18 preflight validation ❌ FAIL; the continuation reservation is consumed. This is not evidence of
a service invocation or a new SELinux runtime denial. Both historical failed attempts remain preserved.

| ID | Task / dependency | Progress | Required validation gate | Validation |
| --- | --- | --- | --- | --- |
| SE19 | Read-only continuation failure review; SE18 failure | ✅ PASS: metadata review complete | Verify live identities and retained diagnostics; isolate failed query before any change | ✅ PASS: operator metadata and recorded version-matched review explain the raw-output mismatch; old log provenance remains unverified |

After two unsuccessful preflights, reassess from retained evidence rather than preparing another attempt.
The wrapper now saves operation/command diagnostics; no helper re-execution is needed to retrieve them.
Existing result-review approval covers these reads. No new helper modification, staging, invocation,
trial-directory removal/rename or reboot is part of this diagnostic continuation.
See the [continuation failure observation](evidence/2026-09-09-hermes-selinux-v2-continuation-failure.json).
Exact next action: verify pinned live unit state, then obtain the protected saved diagnostics and changed
snapshot field names through a minimal read-only operator command. Acceptance gates remain open.

Independent SE19 live observation ✅ PASS: pinned SSH confirms unchanged late/early invocation IDs/start
timestamps, no running setup processes, Enforcing, reviewed disk-policy hash and all three staged source
hashes. Noninteractive sudo still requires a password. This supports the reported absence of a new service
invocation but does not reveal the failed preflight guard. No production files or service state changed.

The canonical guide now marks both prior run commands historical and supplies a saved-JSON-only diagnostic.
It reports operation reasons, safe command identity, audit health and changed snapshot/unit field names;
no helper function or trial is executed. Diagnostic/document validation is ✅ PASS. Exact next action:
operator runs the [saved diagnostic](../HERMES_SELINUX_TPM_REPAIR.md#read-only-continuation-failure-diagnostic)
and returns its JSON. Do not prepare another attempt or change a helper until that evidence is reviewed.

SE19 read-only handoff validation ✅ PASS: three synthetic saved-evidence scenarios (field differences,
missing snapshot and audit health) preserve input file hashes and omit snapshot-value canaries. Diagnostic
Python/shell syntax and ShellCheck pass, as do 217 guide assertions, four-document nonfix lint, 51 local
links and whitespace. The 52-test source/test hashes remain unchanged; no helper edit or production mutation
occurred. Runtime acceptance remains unperformed. Exact next action is the saved-JSON operator diagnostic;
its output is required to identify this failed guard before considering any further continuation.

### Continuation failure isolated to first audit query — 2026-09-10T02:22:59.741240+00:00

Operator saved diagnostics identify query_audit RuntimeError: Audit query failed; absence of denials is
unverified. before.json, audit-before.json and audit-preflight.json exist; journal-before.json,
audit-ready.json, process-observation.json and restart.log do not. Both snapshots and all unit fields match.
Audit status reports enabled=1, pid=1182, lost=0 and backlog=0. The state/policy/unit preflight and initial
audit-health check therefore passed; failure is the first query before journal/recovery-copy/request stages.

SE19 remains 🚧 BLOCKED on the underlying query metadata. Source inspection confirms audit-preflight.json
retains timestamp arguments, returncode and stderr; audit-preflight.log retains raw stdout. Query failure
may arise from a nonzero return, any stderr, or unexpected empty output. No specific cause is inferred
without those fields, and daemon status alone cannot establish absence of denials. Preserve the audit gate.

Existing read-only approval covers returning saved metadata plus stdout length/exact no-matches boolean.
Raw audit stdout stays private. No source change, new attempt, production mutation or reboot is indicated.
Exact next action: operator runs the [audit metadata diagnostic](../HERMES_SELINUX_TPM_REPAIR.md#audit-query-metadata-diagnostic)
and returns its JSON. The helper and both consumed directories remain unchanged; acceptance gates stay open.
Documentation/command validation for this narrowed handoff ✅ PASS: Python/shell syntax, ShellCheck,
metadata-only output fixture, 217 guide assertions, four-document nonfix lint, 51 local links and whitespace.
No source changed; prior offline tests are retained. Exact next action remains the operator metadata read.

### Audit 4.2.1 output contract verified; bounded correction — 2026-09-10T02:29:14.846016+00:00

Operator metadata: returncode=1, empty stderr, zero stdout bytes, no no-matches marker; timestamp arguments
09/09/26 and 18:39:18. Pinned SSH RPM query confirms audit and audit-libs 4.2.1-1.fc44.x86_64.
Version-matched [upstream source](https://github.com/linux-audit/audit-userspace/blob/v4.2.1/src/ausearch.c)
returns 1 for no matches and suppresses the marker in raw mode. The
[manual](https://github.com/linux-audit/audit-userspace/blob/v4.2.1/docs/ausearch.8) also defines exit 1 for
argument/read errors and --input-logs to force configured log input. The old helper used the wrong raw
output contract and inherited stdin selection. Saved metadata matches no-match output, but input provenance
was not recorded; this does not establish absence of real audit denials.

Preserve every prior helper and both consumed directories. Prepare one new hash-pinned wrapper that reuses
the unchanged corrected core and prior continuation code, verifies both exact failed attempts/no request
markers and matching snapshots, and exclusively reserves service-continuation-2. Keep the existing approved
limit of one real late-service invocation, which has not happened. No new permission request is needed for
that same scope; no repeat service, early unit, policy/anchor recovery, TPM clear, LUKS change or reboot.

| ID | Task / dependency | Progress | Required validation gate | Validation |
| --- | --- | --- | --- | --- |
| SE20 | Correct audit query contract; SE19 metadata/source review | ✅ PASS: complete | Pin audit version; force configured logs with closed stdin; preserve errors; silently empty raw exit 1 needs exact default-format no-match confirmation; installed binary synthetic probes | ✅ PASS: 74 offline tests, installed synthetic probes and unchanged source/test hashes; live audit acceptance pending |
| SE21 | Preserve both failed attempts and stage guarded audit continuation; SE20 | ✅ PASS: complete | Exact prior files/summaries/hashes and audit metadata; matching snapshots; exclusive new reservation; no preflight bypass; regression, documentation and remote staging hashes | ✅ PASS: unchanged 74-test source; fresh pinned baseline; exclusive staging and independent hashes/private modes; 217 guide assertions, four-document lint, links and whitespace |

Existing 52-test code and source hashes remain unchanged. Add the correction in a separate wrapper; no
rewrite or repinning of the historical core/wrapper. Record real-binary synthetic tests separately from
privileged live-log acceptance. Exact next action: verify installed ausearch behavior using synthetic stdin
without live-log access, implement/tests the paired-query correction and both-attempt admission, then
finish the concrete operator handoff and private staging under existing scope.

Installed audit binary synthetic format checks ✅ PASS: raw unmatched input returns 1 without the marker,
default unmatched input returns the marker, a matching synthetic AVC is returned, and a bad date is rejected.
The unprivileged probe cannot read auditd.conf and emitted configuration warnings; these are retained and
would fail the real query gate. This proves formatting/argument behavior only, not live-log query acceptance.

Initial wrapper validation ✅ PASS: 72 tests. The new wrapper pins audit packages, uses --input-logs and
closed stdin, and requires a clean default-format no-match confirmation for a silent raw exit 1. It pins
both consumed attempts, their unchanged snapshots and linked evidence, preserves every old helper, and
reserves service-continuation-2 exclusively. Existing core acceptance, diagnostics and one-request behavior
are reused. Review added wrong-host and intervening second-attempt byte-change regressions; the earlier
suite evidence is 🔁 STALE for this test-only addition. No old source or host files were changed.
Exact next action: final affected tests and documentation/command checks, then fresh pinned baseline and
exclusive staging under the existing one-real-invocation approval.

### Resumed final audit-continuation gates — 2026-09-10T02:50:26.193931+00:00

SE20 implementation ✅ PASS: final affected suite passes 74 tests on the existing feature branch.
SE21 🔄 IN_PROGRESS: finish handoff syntax/copy fixtures, guide assertions, Markdown and local links,
then exclusively stage the single new wrapper and independently verify its hash/private mode.
Fresh pinned SSH confirms the recorded unit identities, Enforcing, policy, labels, packages and root mount;
the new staging path is absent. Interactive sudo remains unavailable. No service request occurred.
Existing approval and the one-real-invocation scope are unchanged. Exact next action: complete the
local documentation/command gate before private staging; then hand off the console-supervised command.

SE21 local gate ✅ PASS: 74 affected tests, guide assertions, Python/shell syntax, ShellCheck,
four disposable copy/hash fixtures, nonfix Markdown, local file links and whitespace. Initial lint invocation
❌ FAIL due to an unsupported temporary config filename; corrected invocation ✅ PASS. The link harness
initially matched Python inside a code fence; excluding fenced code resolves that false positive.
Exact next action: exclusively stage and independently verify the reviewed audit wrapper under existing scope.

### SE21 private staging continuation — 2026-09-10T13:10:19.521581+00:00

User instruction: continue with the next task. SE20 and the SE21 local gate retain their recorded passes;
the reviewed audit wrapper and all three test-file hashes still match. No source change is needed.
SE21 remains 🔄 IN_PROGRESS under the existing private-staging approval. Required remaining gate:
fresh pinned host baseline, exclusive mode-0600 staging in the existing mode-0700 directory, then an
independent remote hash/ownership/mode check. Preserve all prior helpers and consumed attempts.
Exact next action: refresh the read-only baseline, stage only the reviewed audit wrapper if it matches,
then update the handoff and documentation checks. The service trial still needs the supervised console.

SE21 remote staging gate ✅ PASS at 2026-09-10T13:11:56.371606+00:00: fresh pinned baseline matched, exclusive
creation succeeded and a separate SSH readback verified all four helper hashes, file mode 0600, directory
mode 0700, regular single-link files and operator ownership. Late/early unit fields are unchanged.
Only the new operator-owned audit wrapper was created; no helper was executed or service requested.
Noninteractive sudo is unavailable. Exact next action: update the current operator handoff and ledgers,
run affected documentation checks, then obtain the console-supervised result under existing approval.

| ID | Task / dependency | Progress | Required validation gate | Validation |
| --- | --- | --- | --- | --- |
| SE22 | One console-supervised audit continuation and read-only result review; SE20–SE21 | 🚧 BLOCKED: invocation consumed; saved ioctl request codes and certificate identity need operator sudo | Execute the canonical handoff once under existing approval; all privileged prior-attempt, audit, policy, anchor, domain and service checks pass; review sanitized result and preserved evidence | ❌ FAIL: service requested, exit 1, 22 scoped AVCs and no ESP anchor; reported preservation and audit checks pass |

SE22 preserves the existing one-real-invocation approval and does not authorize a repeat or reboot.

### SE21 closure — 2026-09-10T13:15:19.338657+00:00

SE21 progress ✅ PASS: complete; validation ✅ PASS. The
[durable observation](evidence/2026-09-09-hermes-selinux-v2-audit-continuation.json) records the tested
source/test hashes, pinned host baseline, exact staging and independent readback programs, timestamps,
private-mode/ownership checks and sanitized local validation logs. The existing 74-test pass remains
applicable because the helper, preserved dependencies and all three test files match their recorded hashes;
the suite was not repeated. Current validation passed 217 guide assertions, four-document nonfix Markdown,
153 local file links, both current handoff anchors, unchanged operator-command identity and whitespace.

Affected procedure, deployment task ledger and canonical evidence ledger are synchronized. Earlier failed
preflights and local harness failures remain recorded. SE22 is 🚧 BLOCKED on the operator's supervised
console execution; validation ⬜ TODO. UA-05/P2 and runtime/repeat/cold-boot acceptance remain open.
Exact next action: run the canonical audit-continuation handoff once with interactive sudo and return
only its sanitized summary for read-only review. No service invocation, reboot, commit or push occurred.

### SE22 runtime failure review — 2026-09-10T13:27:15.407720+00:00

The operator returned summary timestamp 2026-09-10T13:25:13.134745+00:00: service_requested=true,
passed=false, 22 scoped AVCs, observed hermes_tpm2_setup_t, intact audit collection and no collection errors.
Restart/service acceptance and ESP-anchor presence fail. All reported preservation checks pass and
SELinux remains Enforcing. The single approved real invocation is consumed; no retry or reboot is authorized.

SE22 progress 🔄 IN_PROGRESS: read-only failure review; runtime validation ❌ FAIL. Preserve all three
attempts and helpers. Required review gate: independently inspect current unit identities and public
policy/label state, then obtain only grouped permission/type/class AVC diagnostics from the retained
root-private files. Validate the diagnostic on synthetic records for grouping, unknown-record accounting,
secret exclusion and unchanged input files; run affected documentation checks before handoff.
Exact next action: pinned read-only host check, then prepare the saved-file diagnostic if operator sudo
is still required. Do not infer a permission fix or change policy from the count alone.

Pinned live review ✅ PASS: late invocation 65b49476a60341369fd98bf447db9984 started at
2026-09-10 08:25:08 -05 and exited 1. Both MainPID/ControlPID values are zero; the early invocation and
reviewed unprivileged policy/label/package/helper baselines match. Root-private evidence is unreadable
and noninteractive sudo is unavailable. The operator summary is retained separately from this live
observation in the [failure evidence](evidence/2026-09-10-hermes-selinux-v2-runtime-failure.json).
SE22 review is 🚧 BLOCKED on the saved denial groups; its runtime gate remains ❌ FAIL.

SE22 diagnostic/document gate ✅ PASS at 2026-09-10T13:31:49.998440+00:00: the synthetic fixture checks grouped
22 records with explicit unknown accounting, omitted private name/command canaries, preserved input
bytes and rejected wrong owner/mode, oversized, symlinked and hardlinked files. This is diagnostic
validation only; synthetic records are not production evidence. Python/shell syntax and ShellCheck,
217 guide assertions, four-document nonfix Markdown, 157 local links and whitespace passed.
The exact command and reproducible fixture program/hash/log paths are retained in the failure evidence.
No policy or execution helper changed, and no production mutation was performed by this review.
SE22 runtime validation remains ❌ FAIL and its review 🚧 BLOCKED on root-private denial groups.
Exact next action: the operator runs the current saved-AVC diagnostic once and returns its JSON; review
the denied operations before proposing a correction. Preserve all three attempts; do not retry or reboot.

### SE22 grouped AVC review — 2026-09-10T13:36:21.563730+00:00

Operator saved-log hash 896a6d7f3e58ce4e16480ff94e0391cca9244604dbed679a0e4e1a1a4779b32c
accounts for all 22 records with no unparsed lines: cert_t:file read (1),
fixed_disk_device_t:blk_file ioctl (20), and fs_t:filesystem getattr (1), all from
hermes_tpm2_setup_t with permissive=0. Group collection ✅ PASS; runtime remains ❌ FAIL.

The reviewed 1.1.0 policy intentionally excludes certificate-file reads and fixed-disk ioctls.
SE22 review is 🔄 IN_PROGRESS. Required next gate: identify numeric ioctl requests, correlate the
retained journal failure and review the matching source before proposing permission changes.
Preserve the installed/reviewed policy and verifier, every helper and all three attempts.
Existing approval covers read-only evidence review; the service invocation remains consumed.
Exact next action: read-only package/journal availability check and authoritative source review;
if saved details still require operator sudo, prepare one combined sanitized metadata diagnostic.

Independent journal review identifies an access failure checking /boot's filesystem type, followed by
ESP discovery failure. /boot is xfs. This supports the fs_t denial as the failing discovery path, but
the exact Fedora downstream source is unverified. Upstream v259.8 source retrieval returned 404;
version-family v259 and version-matched util-linux 2.41.5 source are recorded with that limitation.
SELinux extended ioctl permissions offer request-number constraints; the existing 1.1.0 no-ioctl and
no-certificate-file-read verifier requirements remain unchanged pending request-specific review.
Exact next action: validate and hand off the combined numeric-ioctl/public-basename diagnostic against
the same pinned log. SE22 review is 🚧 BLOCKED on those root-private fields; runtime remains ❌ FAIL.

SE22 request-metadata handoff gate ✅ PASS at 2026-09-10T13:43:23.102286+00:00: synthetic saved-log tests verify
full request-code retention, decimal/hex normalization, explicit missing/malformed counts, public-name
allowlisting, canary exclusion, immutable input and rejection of a changed log hash. The private-file
reader is byte-identical to the previously validated diagnostic. Python/shell syntax, ShellCheck,
217 guide assertions, four-document nonfix Markdown, 158 local links and whitespace passed.
The failure evidence records the exact diagnostic, fixture program, commands, hashes and log paths.
SE22 runtime remains ❌ FAIL; request-specific review is 🚧 BLOCKED on operator sudo. Exact next action:
run the canonical request-metadata diagnostic and return its JSON; review the numbers and object
identity before drafting any permission changes. All three attempts remain consumed and preserved.

### SE22 request evidence complete; v3 correction preparation — 2026-09-10T14:32:02.331152+00:00

Operator request metadata matches the previously pinned scoped-log hash. All 20 ioctl records have
numeric commands (11 distinct low-word values); the certificate/config basename is openssl.cnf.
SE22 failure review ✅ PASS; runtime validation remains ❌ FAIL. The service invocation is consumed.

Continue authorized local correction/review work in separate v3 files; preserve all reviewed v2 sources,
installed policy, helpers and consumed attempts. No production staging, installation, service invocation
or reboot is authorized for this new candidate. Keep this as the canonical execution record.

| ID | Task / dependencies | Progress | Required validation gate | Validation |
| --- | --- | --- | --- | --- |
| SE23 | Decode requests and inspect public config metadata; SE22 | 🔄 IN_PROGRESS | Authoritative ioctl definitions, request-mask semantics, version/identity limits and permission-scope review | ⬜ TODO |
| SE24 | Separate v3 policy candidate and offline verifier; SE23 | ⬜ TODO | Link against captured exact store, unchanged v2 baseline, enforcing transition, exact added permissions/xperms, negative controls for extra ioctl and data writes | ⬜ TODO |
| SE25 | Concrete installation/rollback handoff and documentation; SE24 | ⬜ TODO | Reviewed hashes and bounded procedure, operational guards, appropriate offline checks and clear remaining runtime/approval gates | ⬜ TODO |

Exact next action: map the 11 requests using public kernel headers, confirm openssl.cnf metadata without
reading its contents, then build the separate policy in the retained isolated Fedora container.

### Architecture reassessment amendment authorized — 2026-09-10

Approval reference: user request “Reassess and simplify the current Hermes unattended-production plan”.
Scope: read-only dependency review and necessary local plan, code, tests and documentation; no delegation,
commit, push, production mutation, service invocation, reboot, TPM clear, LUKS slot removal, anchor replacement
or privilege change. Earlier operational grants and consumed invocations do not authorize new operations.
Save this amendment before implementation; preserve the approved baseline, every failed observation and task ID.
SE22 request metadata has already arrived and its failure review passed; runtime remains failed. SE23–SE25 are
separate prepared v3 correction work. Pause their dependent policy expansion for this architecture review;
preserve all prepared files and exact-store artifacts. Do not add permissions merely to silence denials.

The required outcome remains zero terminal input for normal cold boots, reboots, approved updates and Hermes
startup, with explicit recovery on trust failure. Evaluate the existing LUKS2 + Secure Boot + signed UKI +
PCR7/signed PCR11 no-PIN enrollment, keeping SRK and all existing protections. NvPCR independence is a hypothesis
to validate against package configuration, boot/initramfs, tokens, credentials and consumers, not a conclusion.
Official upstream images, advisory scanning plus denylist, encrypted semantic backups, credential isolation,
protected controller signing, previous approved image, release signatures, host binding, Enforcing SELinux,
maintenance windows and meaningful notifications all remain required.

| ID | Task / dependencies | Progress | Required validation gate | Validation |
| --- | --- | --- | --- | --- |
| AR01 | Architecture and current dependency evidence | 🔄 IN_PROGRESS | Classify application, package and test dependencies; inspect available boot/initramfs/token/credential/service evidence; authoritative versioned sources; explicit unknowns | ⬜ TODO |
| AR02 | Minimal supported local change; AR01 | ⬜ TODO | Only evidence-justified configuration and validation changes; preserve prepared policy and existing host configuration; adverse-input regressions | ⬜ TODO |
| AR03 | Exact migration/recovery and synchronized guidance; AR01–AR02 | ⬜ TODO | Ordered concrete operations with approval boundaries; seven acceptance gates below; lint, links and applicable local checks | ⬜ TODO |
| AR04 | New candidate certification; AR02–AR03 and fresh lab authorization | 🚧 BLOCKED: no new lab grant | Separate fresh candidate-bound lab proof, cleanup/revocation and promotion binding | ⬜ TODO |
| AR05 | Production migration and certification; AR04 and operation-specific approval | 🚧 BLOCKED: no production changes authorized | Revalidate hardware prerequisites and pass P2 before P3/P4; all seven gates on production | ⬜ TODO |

Acceptance design for AR04/AR05: (1) powered-off cold start and Hermes inference with closed stdin/no console
input; (2) approved kernel/UKI transaction followed by unattended unlock/startup without manual reenrollment;
(3) previous approved UKI and retained matching modules boot with the same enrollment; (4) unauthorized boot
artifacts rejected by firmware/shim and/or TPM policy without runtime credential release; (5) actual offline
recovery-key access with encryption/slot state preserved; (6) reboot credential availability, correct trusted
boot binding and isolation, bounded leak checks and unavailable-on-untrusted-boot negative test; (7) rerun
idempotency, interrupted-update recovery, atomic boot selection and preservation of unrelated configuration.
Record concrete methods and expected observations in AR03 before any certification.

Evidence applicability: historical UA-01–UA-04, S4/F4 and SE checks remain history for their original artifacts.
Any changed boot configuration/initramfs/UKI, preflight or certifier invalidates its corresponding candidate
acceptance and promotion fingerprint; mark those gates STALE for the amended candidate without overwriting
historical PASS/FAIL results. Unchanged signing, advisory policy, recovery backups and reviewed v2/v3 files
may retain their existing scoped evidence when their hashes match. P2 was never passed; P3/P4 remain blocked.
Affected documentation: this canonical execution record, verification ledger, deployment tasks, unattended
guide and TPM/SELinux repair procedure; add one canonical dependency/migration procedure if needed.
Exact next action: complete read-only architecture evidence, then choose and implement the smallest supported
local correction. Bundle only new unavailable privileged metadata into one operator request after independent work.

### AR01 findings and AR02 implementation decision — 2026-09-10

Read-only evidence supports a conditional standard-TPM2 candidate, not production migration approval.
LUKS token 1/keyslot 2 is recorded as SHA256 PCR0/7 with no signed-PCR/public-key or PCR-lock policy.
The retained initrd crypttab has no key file and only discard,x-initrd.attach,tpm2-device=auto; TPM plugin,
TSS and PCR11 phase support are present, but NvPCR setup/definitions are absent from that retained initrd.
Live pinned SSH at 14:42 UTC confirms Fedora systemd 259.8, dracut 108, Secure Boot, Enforcing SELinux,
two vendor NvPCR definitions, no /etc overrides, the unchanged failed late invocation and no installed
hermes-runtime-credentials unit. The production root crypttab and credential inventory remain unreadable.
The retained initrd is a historical artifact; its relationship to today's running UKI needs a fresh hash binding.

Versioned upstream source separates SRK setup from optional NvPCR enumeration; masked definitions are skipped.
Product measurement directly loads hardware.nvpcr and must be disabled with those definitions; masking the
setup service itself would also discard SRK setup and is not selected. Signed-PCR LUKS enrollment and
host+tpm2 credentials do not use NvPCR anchoring. A custom measurement or policy consumer would invalidate
this simplification. No such consumer is visible in repository code, but privileged host inventory is incomplete.

AR01 review progress ✅ PASS for available evidence; consumer absence and current artifact binding remain explicit
unverified migration prerequisites. AR02 🔄 IN_PROGRESS: prepare an offline-only, conflict-preserving profile
renderer for two /etc/nvpcr masks, the product-service mask and an additive dracut inclusion file; retain setup
and PCR11 units. Make service checks profile-aware without accepting an unexplained failed/masked setup unit.
Require no-PIN SHA256 PCR7/signed PCR11 token metadata and flag weaker parallel automatic tokens for explicit
review. Make future runtime credential encryption specify PCR7 and the public PCR11 key rather than relying
on discovery. Do not rewrite existing credentials or token slots. Preserve all signing phases and existing
v2/v3 artifacts. Unknown consumers mean do not apply the rendered profile on production.

AR02 gate: synthetic metadata rejects missing/weak/mixed/PIN/PCR-lock tokens; profile preparation preserves
conflicts and resumes partial writes; service observation rejects partial masks and failed setup; credential
commands require the explicit key without printing values. Run affected Python/guide/controller checks and
document checks once. Historical U01/U03/U05/U06/U07 and UA-01–UA-04 boot/runtime/candidate validation becomes
🔁 STALE for these changed source inputs; their original passes remain valid only for their frozen artifacts.
Exact next action: implement the local profile and explicit checks, then finish the canonical review/migration
procedure and collect one sanitized missing-metadata request. SE23–SE25 remain paused and preserved.

### AR02 security review and local checks — 2026-09-10

The standard profile's 14 offline regressions passed. Affected suites passed 131 unattended, 11 certifier,
64 lifecycle, 10 transaction and 12 offline-replay tests; 217 guide checks and 138 ShellSpec examples passed.
Offline systemctl reports the rendered product unit masked (expected exit 1). cat-config reported no visible
main NvPCR configuration; this is not a test of actual TPM setup or dracut archive contents. No live TPM or
service operation was executed. The rendered four-file tree is retained with the local evidence.

Security review clarified the legacy-token gate: removing metadata alone leaves the old slot usable with
retained token material. The migration procedure therefore requires a separate explicit decision after new-token
and distinct recovery-slot verification; no slot retirement is authorized now. Current-header slot retirement
also does not prove resistance to attacker-held historical LUKS-header rollback. Protected recovery backups and
that limitation remain explicit. No destructive operation, permission expansion or v3 policy change occurred.
AR02 implementation/validation ✅ PASS: local only. AR03 🔄 IN_PROGRESS: finish documentation lint/link and
sanitized collector checks, then record final artifact hashes and preserved evidence. AR04/AR05 remain blocked.

AR02 follow-up: source review found the offline-root guard should reject aliases such as /tmp/.. and
/proc/self/root before any writes, including when invoked by root. Tightened canonical-root rejection and
expanded the existing adversarial test. The earlier 14-test result is 🔁 STALE for this renderer change;
repeat only the profile suite. Other checked paths are unchanged. Exact next action: final focused profile
and documentation/collector checks, with preservation hashes and results recorded before handoff.

AR03 first document harness: collector canary/immutability checks and 222 local file/fragment links passed;
ShellCheck ❌ FAIL on SC2016 for the deliberately single-quoted inner staging shell. Kept the correct shell
boundary and documented its narrow suppression. No production command ran. The original failed result remains
recorded; rerun the corrected documentation harness and scoped nonfix Markdown before AR03 completion.

AR03 nonfix lint invocation ❌ FAIL before file checking: markdownlint-cli2 0.21.0 requires a supported
configuration suffix (.jsonc rather than .json). Renamed only the private check configuration as directed by
the tool; no Markdown was changed by that failed invocation. Preserve this harness failure and rerun once.

AR03 lint reassessment: the repository configuration overrode the external config's globs, checking 26 files
and reporting three newly added long lines. The changed-file set remained limited to the intended files;
no additional preexisting file changed. Corrected those lines and moved verification to an isolated copy with
its own nonfix configuration. The final operator collector also reuses the already supplied LUKS token policy,
so it does not ask the operator to repeat token diagnostics; only missing current boot/config/credential and
consumer evidence is requested. Refresh its synthetic fixture for that reduced read-only command set.

### AR01–AR03 local closure and remaining gates — 2026-09-10

The authorized local review and implementation are complete. Available live/recorded evidence supports a
conditional standard-TPM2 candidate; it does not certify NvPCR independence for every production consumer.
The [dependency/migration procedure](../HERMES_TPM_DEPENDENCY_REVIEW.md) is the authoritative current guide,
with B1–B7, concrete enrollment and legacy-slot proposal, preservation/rollback rules and one new collector.
Both SRK setup units and PCR11 phase measurements are retained; the failed setup unit is not masked.
No new SELinux permission was added and no prepared v3 or reviewed v2 source/test/evidence file changed.

| ID | Progress | Validation / remaining gate |
| --- | --- | --- |
| AR01 | ✅ PASS: available evidence reviewed | Required/optional/unverified dependencies documented; privileged consumer/configuration inventory remains a migration prerequisite |
| AR02 | ✅ PASS: local implementation complete | 242 affected Python tests in total, including final 14-test profile/root-alias suite; 217 guide checks and 138 ShellSpec examples pass |
| AR03 | ✅ PASS: local documentation complete | Collector canary/immutability checks, 222 file/fragment links, shell/Python syntax, ShellCheck and seven-file isolated nonfix Markdown pass; historical harness failures retained |
| AR04 | 🚧 BLOCKED: fresh lab authorization required | New candidate UA-01–UA-04/B1–B7 and matching promotion fingerprint; consumed S4/F4 grants are unavailable |
| AR05 | 🚧 BLOCKED: AR04 and operation-specific production approvals | Hardware P2/B1–B7, then P3 and P4 in order; no existing partial/lab pass is production proof |

Validation environment: Devbox on the current workstation, base revision 4a19d3f plus the preserved working tree;
no VM/service/TPM operation was performed. The final profile rerun supersedes its earlier 14-test evidence after
the root-alias guard fix. Other tested execution paths are unchanged. Prior documentation harness failures
(SC2016, config suffix/scope, line lengths and one added double blank) are retained; none is runtime evidence.
The [sanitized observation](evidence/2026-09-10-hermes-tpm-dependency-review.json) records exact commands,
timestamps, logs and artifact identities. Seven-file lint uses an isolated copy so repository fix-mode cannot
rewrite unrelated files. Unchanged v2 tests were not repeated: 33 existing policy/source/test/evidence hashes
match the turn baseline, all five prepared v3 source hashes match their recorded identities, and the retained
RSA2048-v2 UKI/initrd match their original build hashes.

Historical UA-01–UA-04/S4/F4 passes remain valid only for original frozen artifacts. Changed host, credential,
profile, observer and payload inputs invalidate amended-candidate boot/runtime/replay/credential certification
and signing/promotion binding. P2 never passed; P3/P4 remain blocked. No production state, credential, anchor,
TPM or LUKS slot was modified; no service invocation, reboot, commit, push or delegation occurred.

Exact next action: return only the new collector JSON and whether custom/external consumers depend on NvPCR;
reuse already supplied SE22 request metadata and LUKS policy. Review that evidence before requesting a fresh
bounded lab grant. No production operation approval is being requested yet. The original plan remains open
for AR04/AR05 and P2–P4; all other approved runtime/image/backup/signing/identity/window/notification requirements
are preserved. No document update is required for unrelated workstation/network components or retained archives.

AR03 closeout ✅ PASS on 2026-09-10 UTC: final isolated nonfix lint passed all seven intended documents after
wrapping the updated next-action paragraph. The earlier failed checks remain in the evidence logs. All
independent authorized local work is complete; the next action and blocked gates above remain unchanged.

### AR01 operator inventory received — 2026-09-10

The user supplied the requested read-only inventory, timestamp 2026-09-10T15:44:01.044947+00:00.
Continue under the existing architecture-review authorization: record and validate this evidence, correlate
packaged references with read-only loaded/generated configuration, and update the current dependency guide,
ledger and task summary. No new lab or production operation approval is implied by diagnostic output.
Save this follow-up before documentation changes; preserve the original evidence and prepared v2/v3 work.

AR01 follow-up 🔄 IN_PROGRESS. Gate: parse the supplied JSON, match current selected-file/initrd/public-key
identities to retained evidence, distinguish bounded absence from arbitrary consumer absence, and classify
remaining enrollment/boot prerequisites. AR03 documentation check 🔁 STALE for the upcoming changed prose;
run focused guide/lint/link and evidence-preservation checks. Runtime source is unchanged, so reuse its
unchanged-artifact local evidence. AR04/AR05 and P2–P4 remain blocked in their existing order.
Exact next action: validate supplied metadata, complete independent read-only service correlation, then
record results and ask only for genuinely missing custom/external consumer knowledge.

### AR01 inventory findings and unchanged implementation — 2026-09-10

The supplied inventory ✅ PASS: selected RSA2048-v2 on-disk image and current initrd match retained build
hashes; the public PCR11 key in /run matches the reviewed key. Reuse those unchanged artifacts' prior inspection.
Root crypttab has automatic TPM unlocking, no keyfile and no NvPCR/PCR-lock option. Both expected unattended
credential files are absent. These observations resolve the earlier bounded privileged metadata request.

Independent pinned read-only SSH at 15:47–15:48 UTC confirms no persistent PCR11 public-key file, disabled/inactive
state for all seven packaged PCR-lock services, no loaded/enabled template instances and no NvPCR/PCR-lock option
in the effective generated cryptsetup command. The uninstantiated PCR-lock template show query returned 1;
read its packaged definition and unit-file state instead. No service instance was started. Early/late setup
invocation IDs are unchanged; the late failure remains. Product measurement is still active.

BootCurrent 0006 is absent from BootOrder 0001,0008,0003,0000, with no BootNext reported. Selected-file hashes
are not proof of the next unattended boot default or a fresh measured-boot observation. B1–B3 stay open.
The expected credential files are absent, not newly certified; enrollment and B6 remain required. The approved
migration already installs the reviewed public key and enrolls credentials, so no additional runtime code is
justified. Custom/external consumers outside the bounded scan still need operator confirmation.

AR01 inventory review ✅ PASS; AR02 unchanged local implementation ✅ PASS with matching tested source hashes.
AR03 🔄 IN_PROGRESS: validate the updated dependency/ledger/task guidance and sanitized evidence. Preserve
all earlier failed checks and historical passes; no new runtime or production pass is implied. Exact next action:
complete local document/evidence checks, then ask only about custom/external NvPCR consumers.

### AR01 inventory follow-up closure — 2026-09-10

AR01 supplied-inventory review ✅ PASS; AR02 unchanged implementation ✅ PASS; AR03 updated guidance ✅ PASS:
217 guide checks, 225 local file/fragment links, collector canary/immutability checks, command syntax/ShellCheck
and seven-file isolated nonfix Markdown passed in Devbox. The final closure prose receives a final scoped lint
check; results and exact commands are retained in the existing sanitized observation. Seven previously tested
runtime/test files match their recorded hashes, so the prior 242 Python tests and 138 ShellSpec examples are
reused for their unchanged execution paths, not reported as rerun. All other existing repository files are
unchanged from this follow-up's baseline; v2/v3 policy, failed evidence and historical approvals are preserved.

No new boot image, credential, configuration, service invocation, TPM/LUKS/anchor operation or privilege change
was performed on production. No lab run, commit, push or delegation occurred. AR04 remains 🚧 BLOCKED on a fresh
bounded lab grant and amended candidate UA-01–UA-04/B1–B7 acceptance. AR05 remains 🚧 BLOCKED on AR04, the remaining
custom/external consumer confirmation and operation-specific production approvals; P2 precedes P3/P4.

Exact next action: confirm only whether Hermes has custom/external TPM sealing or remote-attestation consumers
using hardware/cryptsetup NvPCR beyond the inspected setup; identify a known consumer's purpose/configuration
location without secrets. The requested JSON, SE22 metadata and LUKS diagnostics are already received. Then
prepare the concrete fresh lab grant for review. No production operation approval is requested at this point.

### AR04 campaign preparation authorized — 2026-09-10

Approval reference: user selected “1,2,3,4” after the ordered readiness tasks. Proceed with dependency review,
fresh lab campaign preparation/certification and concrete production-operation preparation, preserving gate
ordering. This does not identify or approve a new production mutation, privilege grant or service invocation;
prepare the exact bounded operations first. Old lab grants and consumed invocations remain unavailable.
No commit, push or delegation. The operator answered “I don't know” about custom/external TPM consumers;
record this as unknown rather than absence. Continue independent lab/local work while investigating discoverable
consumer evidence. Do not repeat the completed privileged crypttab/boot/credential or SE22/LUKS diagnostics.

| ID | Progress | Gate and next action |
| --- | --- | --- |
| AR01 | 🔄 IN_PROGRESS: residual consumer review | Inspect relevant installed software/custom execution configuration read-only; document inaccessible areas and limits; unknown does not establish absence |
| AR02 | 🔄 IN_PROGRESS: lab integration review | Verify the fresh fixture actually carries the standard profile into baseline and updated initrds; correct only necessary local gaps with adverse-input/preservation tests |
| AR03 | 🔄 IN_PROGRESS: concrete campaign and production operation blocks | Save exact identities, operation bounds, prerequisites and recovery; lint/link checks and affected offline tests before review |
| AR04 | 🔄 IN_PROGRESS: independent preparation; live run gated | Fresh root-owned run/policy-bound grant and required isolated lab controls; no reuse of expired grants; all amended B1–B7/UA-01–UA-04 evidence required |
| AR05 | 🚧 BLOCKED: AR04 and unresolved consumer review | P2 then P3/P4; concrete production approvals still required; no production action is authorized merely by this task selection |

Validation: inventory provenance and bounded privacy checks; affected fixture/profile/offline suites; original
source preservation; exact rendered profile/initrd assertions before any passing lab claim. Reuse unchanged
artifact evidence. Changes to fixture/runtime/observer inputs make corresponding candidate/promotion evidence
STALE without overwriting historical results. The existing dependency guide remains the canonical migration
procedure; extend it for new concrete campaign details rather than duplicating a second execution record.
Exact next action: inspect fixture integration and current local lab prerequisites, then complete independent
local fixes, read-only consumer review and a reviewable fresh operation package before requesting missing inputs.

### AR02 installer integration and AR04 concrete operation package — 2026-09-10

Found an execution gap: the previous local profile renderer was not connected to the disposable installer.
The same renderer and common helper now travel on verified installer OEM media and run on the offline target
before dracut. Lifecycle signing checks both baseline and updated archives for the three exact masks, TPM/PCR11
module metadata and unknown NvPCR definitions. It records the archive identities without claiming boot success.
No separate profile template or additional SELinux permission was introduced; production remains untouched.

AR02 local gate ✅ PASS: 20 profile, 65 lifecycle and 131 unattended Python tests; 138 ShellSpec examples.
The signed installer-media regression independently reads back both helper files. A disposable synthetic
cpio/gzip archive passed the actual lsinitrd inspection; this is not a Fedora dracut build or VM/TPM boot.
The earlier profile/fixture hashes are STALE for this amended candidate; historical results remain preserved.

AR01 accessible consumer audit: 10 files / 39,536 bytes, no TPM-reference hits. Relevant packages are only
ima-evm-utils-libs and TPM/TSS tools/libraries in the inspected package-name filter. The sbin alias is the
already scanned bin directory. Protected cron and Hermes/root user-service/Quadlet paths remain unreadable;
the operator's unknown answer cannot fill that gap. A tested narrower interactive read-only SSH collector is
prepared for those paths only. It does not repeat the received boot/crypttab/credential, package or SE22 data.

AR04 preparation found the fixed VM, pool, NVRAM and emulated TPM absent; the broker is inactive. Its existing
policy authorizes test UID 987, while the lifecycle certifier is UID 984. A new campaign therefore needs the
concrete temporary broker/socket access change and fixed-domain power grant, plus explicit service invocation.
The preserved old root lifecycle journal is failed-cleaned, not a current pass. No existing grant is reused.

A 71-file source snapshot and exact policy/unit/socket/sudoers/helper proposal are retained in the private
review package linked by the [campaign observation](evidence/2026-09-10-hermes-standard-tpm2-campaign.json).
The [canonical dependency procedure](../HERMES_TPM_DEPENDENCY_REVIEW.md#fresh-lab-campaign-prepared-on-september-10)
defines AR04-L0 temporary enrollment, L1 one run with a newly issued maximum-four-hour grant and L2 mandatory
revocation/cleanup/restoration. No grant was issued, temporary privilege installed or service started.

Coverage review found that the existing certifier's payload rejection is not boot-artifact rejection. L1
covers a subset of B1–B7; B3 previous-image boot, B4 boot trust negatives and the full B7 interruption matrix
remain separate dependent live gates after initial integration succeeds. No automatic promotion/signing is
permitted from L1 alone. AR04 and production P2–P4 remain blocked. AR03 final document/operation-package checks
are in progress; complete them before requesting the protected read and concrete L0/L1/L2 approval together.

AR03 first unit-file validation ❌ FAIL: the Devbox-selected verifier's unit search could not resolve
sysinit.target for either temporary unit. The generated units were not loaded or started. Reassess with
Fedora's /usr/bin/systemd-analyze and explicit installed unit directories; retain the original failure.
Other checks ✅ PASS: 217 guide checks, 237 local links, eight-file isolated nonfix Markdown, sudoers syntax
and diff whitespace. Final collector terminal/privacy, kickstart and frozen-package verification remains.

### AR03 campaign preparation closure and exact next action — 2026-09-10

AR02 local integration ✅ PASS; AR03 concrete initial lab package and documentation ✅ PASS. Fedora's explicit
unit verifier passed both temporary units after correcting the validation tool/search path; the first failed
verifier output remains. Frozen archive, policy/run binding, helper identity, protected-only collector privacy,
uncaptured operator-terminal boundary and all three kickstart shell blocks pass the saved campaign verifier.
The 71 source files exactly match the current checkout. No root installation or run grant was issued.

Validation totals for this continuation: 216 affected Python tests, 138 ShellSpec examples, 217 guide checks,
237 local links, eight-file nonfix Markdown, sudoers/unit syntax, kickstart syntax/ShellCheck and actual
synthetic archive inspection. This remains local evidence. Final closure prose is checked again by scoped lint;
its exact result is recorded in the campaign observation. Unchanged prior suites retain their original scope.
All v2/v3 policy sources/tests/evidence and other unrelated preexisting files match the turn baseline. Only the
seven intended runtime/test/kickstart files, eight documents and two new sanitized evidence/collector files changed.

AR01 🚧 BLOCKED: protected cron and Hermes/root user-service/Quadlet evidence is missing; the operator's unknown
answer is retained. AR04 🚧 BLOCKED: exact temporary broker/socket access, fixed-domain power permission and
one-run service invocation still need the new AR04-L0/L1/L2 approval. A successful first cycle is only partial
B1–B7 evidence; additional boot trust/previous-image/interruption gates remain dependent work. AR05/P2–P4 stay
blocked in order; no production operation, new service invocation, reboot, TPM/anchor/slot change or privilege
change was performed. No lab run, commit, push or delegation occurred.

Exact next action: from the workstation's interactive terminal, run the protected-only remote collector linked
in the dependency guide and return its JSON; do not repeat completed diagnostics. Review and approve AR04-L0/L1/L2
as one bounded temporary lab campaign: test UID 987→984/socket access, fixed-VM power grant, one fresh maximum-four-hour
run, provider revocation/cleanup and restoration to the original controls. Lab preparation can proceed independently
of the remaining production read once those concrete operations are approved. No production approval is requested
before the required lab results and concrete production artifacts exist.

### AR01 protected evidence received; AR04-L0/L1/L2 explicitly approved — 2026-09-10

Approval reference: the user's message accompanying the root collector JSON states:
“I approve AR04-L0/L1/L2: temporary broker/socket access for UID 984, fixed-VM power permission,
one fresh lab run with a maximum four-hour grant, and mandatory cleanup and restoration.”
This authorizes the exact prepared operations and identities in the canonical dependency procedure.
No production operation, new grant after a consumed attempt, release signing, commit, push or delegation is authorized.

AR01 bounded dependency review ✅ PASS: operator evidence at 16:41:36 UTC reports effective UID 0,
protected-consumer-remainder coverage complete, no hits or unreviewed paths, empty visited cron directory
and absent Hermes/root user-service/Quadlet directories. Correlated with the earlier accessible audit,
no custom NvPCR consumer was identified. The operator's unknown answer and consumer_absence_proven=false
remain explicit limits; arbitrary external consumers are not disproved. No repeated production diagnostic is needed.

AR04-L0 🔄 IN_PROGRESS: recheck frozen source/policy/control identities, exclusive destinations, old campaign
inactivity and fixed resource absence before temporary installation. AR04-L1 ⬜ TODO: issue the single fresh
run-bound grant only immediately before dispatch. AR04-L2 ⬜ TODO: mandatory cleanup/restoration after any outcome.
Validation requires exact root-owned source/control readback, the actual lifecycle journal and provider/guest cleanup,
then original broker hash/UID/socket and privilege restoration. Preserve failed stages and all previous evidence.
A passing first cycle covers only the documented B1–B7 subset; AR04 and AR05/P2–P4 remain open in order.
Exact next action: complete L0 guards and enroll the approved temporary controls, dispatch L1 once,
then reconcile L2 and record the results before preparing any further live operation.

AR04-L0 ✅ PASS at 16:49:36 UTC: exclusive root installation of the 71-file reviewed source, exact
policy and temporary units/socket/power rules; syntax, readback and broker restriction checks passed.
Old source/policy/journal/resources were preserved. Broker test UID is temporarily 984; production remains disabled.
AR04-L1 🔄 IN_PROGRESS: the single grant was issued at 16:49:59 UTC, expiring at 20:49:59 UTC.
Invocation a1ba292946b740b2ab03e97e38cdf2a8 entered provisioning with source identity
9ec3fcc4cd93f26563abe58d64f0de5943ea299fabc9bbfefc84045098b97766. No acceptance pass is inferred.
The [live observation](evidence/2026-09-10-hermes-standard-tpm2-live.json) preserves the approval,
operator inventory and per-operation results separately from the earlier preparation evidence.
Exact next action: observe this run without retry, then execute mandatory L2 reconciliation and restoration.

AR04-L1 checkpoint at 17:06:34 UTC: unattended installation finished and the fresh disposable recovery key
opened the encrypted guest disk. Expected staging marker and pinned SSH public-key readback passed;
lifecycle recovery_readback=true. This is lab B5 evidence only. Baseline archive inspection/signing and
first unattended encrypted boot are still pending; certification remains false.

### AR04 first live result, restoration and bounded correction review — 2026-09-10

AR04-L1 ❌ FAIL, observed at 17:07:32 UTC: baseline build stopped in inspect_initrd at the exact mask
assertion (tpm_profile.py:135), after module validation and successful lab recovery readback.
No installed UKI was signed, no first installed encrypted boot ran, and certification stayed false.
The lifecycle automatically reached failed-cleaned: domain/disk/NVRAM/swtpm and private inputs removed.
The failed archive/listing was not retained by the current cleanup implementation; do not invent its exact contents.
The code-location evidence identifies a missing/duplicate/non-symbolic/non-absolute-null mask assertion,
not which mask or whether supported dracut path normalization caused it.

AR04-L2 ✅ PASS at 17:12:52 UTC: exact original broker bytes, ownership, modes and xattrs restored;
test UID 987 restored and production disabled. Temporary units/socket override/power helper/sudoers and
active grant removed. Broker/socket stopped; runtime credential and fixed disposable resources absent.
No test provider credential was issued. Old policy, journal and timers match their pre-run identities.
Failure notification unit completed successfully. The consumed grant is retained only as historical evidence.

Authorized local follow-up: inspect/reproduce the packaged dracut mask representation using disposable
user-owned paths; correct only demonstrated compatibility or diagnostic-retention gaps. Preserve this failed
root snapshot and grant; do not retry the service or reuse its run ID. Before a code correction, record its
evidence and acceptance gate here. Required checks: actual packaged dracut-install/archive round-trip,
wrong/missing/duplicate/unsafe mask rejection and preserved pre-signing failure. Runtime input changes make
the prepared snapshot and dependent certification STALE; production P2–P4 remain blocked.
Exact next action: reproduce the mask transformation locally and prepare a bounded tested correction,
then request a fresh concrete lab operation only after its reviewable artifacts and checks are complete.

Local reproduction at 17:14:26 UTC ✅ PASS: unprivileged dracut-install 108-8.fc44, using only a
disposable sysroot and destination, copied all three masks but rewrote targets to ../../dev/null
for hardware/cryptsetup and ../../../dev/null for the service. Dracut v108 ln_r/convert_abs_rel source
confirms this supported transformation. This reproduces a checker compatibility defect; it does not
recover the deleted lab archive or establish its precise failure cause.

AR02 bounded correction 🔄 IN_PROGRESS, saved before implementation: accept only /dev/null or
the exact root-relative equivalent for each fixed mask, requiring unambiguous real directory entries
for relative-path traversal. Keep missing, duplicate, regular-file, wrong/escaping-target, redirected-parent,
unknown-definition, missing-module and changed-archive rejection. Persist only sanitized mask/module
counts/verdicts and archive identity before failing, so mandatory secret cleanup retains useful evidence.
No production configuration, SELinux permission or renderer output changes are proposed.
Validation: real packaged dracut-install to cpio/lsinitrd reproduction; meaningful adverse-path/retention tests,
affected profile/lifecycle suites and documentation checks. Preserve the consumed root snapshot unchanged;
prepare a distinct unissued run/source/policy package for any later separately approved integration.

AR02 correction local gate ✅ PASS: 23 profile and 66 lifecycle tests. The profile suite now performs an
actual packaged dracut-install → cpio/gzip → lsinitrd round-trip, plus unsafe-path and secret-canary rejection.
Lifecycle failure saves sanitized archive verdicts and still prevents signing. Renderer output and permissions
are unchanged. The tested runtime files changed only in the developer checkout; the failed root snapshot is preserved.

AR03 r2 package 🔄 IN_PROGRESS: a distinct 71-file snapshot, policy, units and unissued run proposal are
prepared at review-package-r2. Source archive 052a2294e22b1f5ca12ccf6fa18bc80fec41ef3e6df74d068e64abe7abcef1ee;
policy 6fb4f69cdee32a3331a561345d9776bdbeeab2aa1fbc8979f2dfde8619083da0; proposed run
e2fc5937ad3c02f437df891f0d224e099c3ef2cda49b53436f7d35baba6a7c05. This proposal is not approved or issued.
The canonical dependency procedure defines the exact r2 paths and L0/L1/L2 bounds. Complete package syntax,
media-helper readback, document/link and preservation checks before requesting another concrete operation.
AR04 remains blocked on fresh integration and the rest of B1–B7; AR05/P2–P4 remain blocked in order.

AR03 r2 source/control/media checks ✅ PASS at 17:21:31 UTC: 71 exact regular archive members/modes/hashes,
current source match and unchanged failed root snapshot; both units, sudoers and real signed installer-media
helper readback pass. Ninety affected Python tests passed in total (23 profile, 66 lifecycle, one media check).
Unchanged previous suites retain their earlier scoped evidence. No new lab operation was performed.

Document validation: 249 local links and 217 guide checks ✅ PASS; diff whitespace ✅ PASS.
First final nonfix Markdown ❌ FAIL with three overlong lines in the dependency procedure.
Retain that output; wrap only those lines and rerun scoped lint before closing local preparation.

The second nonfix Markdown check also ❌ FAIL: manual line splits joined into overlong continuation lines.
Reassessment: wrap the three complete prose paragraphs within 117 columns, then verify lengths and scoped lint.
Both failed lint outputs remain preserved; no implementation or operational gate changed.
Independent restoration readback passes. Its first extra provider-path check used an overlong lease name
and is retained as partial evidence; the corrected canonical run_id[:32] check confirms no lease/credential.
The original L2 verification already used that canonical derivation and remains valid.

The paragraph-wrap lint ❌ FAIL exposed an ordered-list formatting regression: contiguous steps 2/3
were folded into step 1. Restore those unchanged steps from the retained document mirror and explicitly
wrap only step 1's prose. Preserve the failed check; do not renumber or change migration gate ordering.

### AR04 first-attempt closure and r2 review handoff — 2026-09-10

AR01 ✅ PASS for the completed bounded dependency review; arbitrary external integrations remain unproven.
AR02 ✅ PASS for the evidence-justified local compatibility/diagnostic correction. AR03 ✅ PASS for the
distinct r2 package and final preparation checks. The consumed AR04-L1 result remains ❌ FAIL;
AR04-L0 and AR04-L2 remain ✅ PASS. No installed-system boot, runtime or full certification pass is claimed.

Validation: 90 affected Python tests pass, including real packaged dracut/archive and signed media readback;
217 guide checks, 249 local links, both r2 units, exact sudoers and diff whitespace pass. Eight-file nonfix
Markdown passes after preserving and correcting the formatting failures. Final handoff prose receives a
scoped lint/link/whitespace readback recorded in the live observation. Unchanged prior test evidence is reused
only within its original artifact scope. The first archive's exact contents remain unavailable after cleanup.

Preservation: only two runtime files, their two test files and six current documents changed from this turn's
baseline; one sanitized live observation was added. All 33 preexisting SELinux source/test/evidence files,
other unrelated files, the original prepared archive and failed root snapshot are unchanged. No new production
operation, commit, push or delegation occurred. The user-authorized temporary lab controls are fully restored;
no r2 installation or grant exists.

AR04 🚧 BLOCKED on a separately approved r2 integration attempt and remaining B1–B7 evidence, including
previous-approved-image boot, boot trust negatives and the complete interruption matrix. AR05/P2–P4 remain
blocked in order; lab recovery readback cannot satisfy production recovery. Candidate/promotion evidence
for changed runtime inputs is STALE. Preserve prepared v3 work paused and the approved security requirements.

Exact next action: review the canonical dependency procedure's corrected integration package r2 and approve
AR04-L0/L1/L2 for that distinct archive/policy/run ID: temporary UID 984 broker/socket access, fixed-VM power
permission, one fresh grant lasting at most four hours, and mandatory cleanup/restoration. The first approval
authorized one run and is consumed; do not reuse it. No additional AR01 operator evidence is requested.

### AR04 r2 L0/L1/L2 approval and execution — 2026-09-10

The user's “approved” response explicitly accepts the preceding concrete r2 operation request.
This authorizes temporary UID 984 broker/socket access, the fixed-VM power permission and exactly one
fresh lifecycle with a maximum four-hour grant, followed by mandatory cleanup/restoration on every outcome.
The frozen archive is 052a2294e22b1f5ca12ccf6fa18bc80fec41ef3e6df74d068e64abe7abcef1ee;
policy binding 6fb4f69cdee32a3331a561345d9776bdbeeab2aa1fbc8979f2dfde8619083da0;
run e2fc5937ad3c02f437df891f0d224e099c3ef2cda49b53436f7d35baba6a7c05.
Retain the unissued proposal as preparation history; record the new approval and grant separately.
No production operation, release signing, second attempt, commit, push or delegation is authorized.

AR04-L0 r2 🔄 IN_PROGRESS: revalidate exact frozen source/control identities, exclusive destinations,
original broker state, fixed resource absence and inactive prior campaigns before installing root-owned controls.
AR04-L1 r2 ⬜ TODO: mint the single fresh run-bound grant immediately before dispatch; no automatic retry.
AR04-L2 r2 ⬜ TODO: reconcile provider/guest cleanup, restore original broker bytes/metadata/xattrs and UID 987,
remove matching temporary controls/grant, and verify resource/runtime credential absence and preserved old records.
Validation is the actual lifecycle journal, retained sanitized initrd verdicts, unit results and independent
cleanup/restoration checks. Local correction tests remain valid for unchanged files; live integration remains open.
AR04's complete B1–B7 matrix and AR05/P2–P4 remain required in order even if this integration passes.
Exact next action: complete L0 guards, dispatch L1 once within its bound, then finish and record L2.

AR04-L0 r2 ✅ PASS at 17:56:18 UTC: exact 71-file frozen source/control installation, syntax and readback,
root-protected inputs, original broker/fixed-resource guards and prior snapshot checks passed.
Only approved temporary test UID/socket/power controls changed; production remains disabled.
AR04-L1 r2 🔄 IN_PROGRESS: the single bound grant is issued and the lifecycle dispatched once.
Record its exact timestamps/invocation in the r2 observation; cleanup/restoration remains mandatory.

R2 interim observation: unattended installation and disposable recovery-key disk readback passed by
18:13:42 UTC. By 18:14:27 UTC the real baseline initrd inspection passed: all three masks are unique
relative-null links with verified directory chains; required modules are present, no unknown definition
was found, and the archive remained unchanged. Initrd SHA256:
230974bc001f5cb4b6117b0d88af230057bc9c492e2e7dae0c31053d593e58b0.
This validates the r2 compatibility correction in a real guest build; boot/runtime acceptance is still pending.
The controller stdin was independently observed as /dev/null. Local guide checks pass 217/217; 254 local
links and retained procedure/collector checks pass. The unchanged r2 source reuses its 90 affected test results.

AR04-L1 r2 ❌ FAIL, observed terminal failed-cleaned by 18:37:55 UTC. Preparation advanced through
first signed-UKI boot with expected command line and Secure Boot, signed boot-manager enrollment and
its observation, canary runtime setup, stored package transaction, verified baseline disk, offline replay,
updated initrd inspection/signing, baseline restoration and exact candidate enrollment. Both real initrd
mask checks pass. Candidate d39cf3d34960350bc7d8a8f41a688aa1a586fd306809658ca43aededa109b23f;
artifact fingerprint 52e87eb3deab128fd0b754d5705847d67da91258714f668d5557a4a996f60476;
updated kernel 7.2.4-200.fc44.x86_64. Preparation is not full candidate update/boot certification.

The certifier retained required-command-unavailable before provider credential issuance and recorded no
acceptance gates. This covers an OS process-launch error; the missing or inaccessible executable is not
established yet. Preserve the failure and investigate retained code/state before choosing any correction.
No new run is authorized. The approved r2 attempt and grant are consumed.

AR04-L2 r2 ✅ PASS at 18:38:19 UTC, with independent readback: guest/credential reconciliation, fixed VM,
disk/NVRAM/swtpm/private cleanup, original broker bytes/metadata/xattrs and UID 987, socket 0600/user/group,
temporary control/grant removal and old policy/journal/timer preservation all pass. No provider credential
was issued. Both r1/r2 source snapshots are preserved. Production, release signing and v3 work remain unchanged.

A read-only serial diagnostic yielded no bytes (inconclusive). A VM display capture showed the offline
replay job running with package policy reload messages. Its initial collector returned 1 after capture
because unprivileged chmod of the root-owned image was denied; private-parent image readback succeeded.
No terminal input or custom permission change was used. Preserve that partial collector result separately
from the lifecycle failure. Exact next action: finish the local command-dependency diagnosis and any
justified preparation/validation, then update current guidance and remaining gates before handoff.

### R2 certifier tool-path correction amendment — 2026-09-10

Read-only inspection identifies a concrete lab dependency defect: schedule.child deliberately builds a
sanitized PATH from its own root-owned adjacent bin plus standard directories. R2 had no adjacent bin.
The parent lifecycle PATH resolves Restic and Trivy through /var/lib/hermes-lifecycle-source/bin, while
neither resolves in the actual child search path. Parent Restic initialization therefore does not prove
child backup/scanner readiness. The recorded OS launch error precedes credential issuance and is consistent
with missing child Restic; the exact failed executable/stage was not retained. No NvPCR or SELinux permission
dependency follows from this failure. Fedora's packaged systemd already includes systemd-analyze; a proposed
missing-systemd-subpackage hypothesis was rejected before implementation using the package manifest.

Authorized local amendment before implementation: retain the child's sanitized environment, use its existing
root-enrolled adjacent-bin configuration for the already reviewed Restic/Trivy tools, and add a shared child
readiness check before allocating a disposable VM. Retain a sanitized failure stage for future diagnosis.
Prepare a distinct, unissued package and document exact tool identities; do not install it or issue another grant.
Preserve r1/r2 source, candidates, failure journals and consumed grants, and all other approved requirements.
Validation: reproduce the old child resolution failure without VM/provider access; exercise corrected discovery,
missing/inaccessible tool rejection, caller-PATH isolation, fail-before-allocation behavior and secret-free
failure-stage retention. Run affected scheduler/certifier/lifecycle tests and relevant local documentation checks.
Changed orchestration inputs make future candidate certification/promotion stale; passing r2 archive/preparation
observations remain historical evidence for their exact artifacts. AR04 and AR05/P2–P4 stay blocked in order.

Local validation ❌ FAIL: the first scheduler/lifecycle checks exposed an import indentation error in
schedule.binding introduced while extracting the shared environment helper. Certifier tests passed 12/12.
Preserve those logs; restore the original local hashlib import and place shutil at module scope, verify
syntax, then rerun only the failed scheduler/lifecycle suites. The root-owned r2 snapshot is unchanged.
The actual UID 984 read-only child-path reproduction confirms Restic launch errno 2 (ENOENT), with neither
Restic nor Trivy resolvable under the exact r2 child environment. No certifier, provider or VM was invoked.

Local correction ✅ PASS: 33 scheduler, 69 lifecycle and 12 certifier tests (114 total); missing/nonexecutable
or broken-link tools, ignored caller PATH, pre-allocation stop, fixed certifier UID and safe failure-stage
retention are covered. The earlier import failure is retained. No renderer, TPM, guest package or SELinux
permission change was made. The existing child environment is preserved through a shared helper.

R3 preparation source/control gate ✅ PASS: 73 regular archived files (71 repository sources plus two
reviewed tool copies), exact manifest/hashes/modes, both units, sudoers and copied Restic/Trivy version probes.
Nix store objects verify. An initial preparation guard rejected the managed 1775 /nix/store parent; investigation
confirmed root-owned immutable package objects and verified their pinned bytes instead. No store permission
was changed; the partial source copy was verified and resumed. Future L0 must verify the root-owned adjacent
bin and actual UID 984 tool execution before dispatch. This preview does not claim that future gate passed.

The unapproved, unissued r3 package is bound to archive
7101a25a928ad3d5665a652c880962637251f0ca7b02ba53c880f4be0158300e,
policy d0bb04d7513ebd77750fb94f8831bc85cc14486191569d31e95282188919354a,
run 67ccc802152b9b7a8f500435a7d5e67429755be276b3e924bda581c79685f032.
The [canonical r3 procedure](../HERMES_TPM_DEPENDENCY_REVIEW.md#certifier-tool-configuration-package-r3)
defines exact destinations, added tools, preconditions, one-run bound and mandatory restoration.
R3 is not installed and no new grant exists. Both consumed lab runs and their outcomes remain preserved.

Preservation readback: only three runtime files, their three tests and six current documents changed from
this turn's initial snapshot; one sanitized r2 observation was added. All 33 SELinux source/test/evidence files,
other unrelated files and both root-owned failed snapshots are preserved. Production, commits/pushes,
release signing, delegation and new service invocations after r2 restoration remain absent.
Final document/link/guide/whitespace checks are pending before the review handoff.

### R2 closure and r3 review handoff — 2026-09-10

AR01 bounded review ✅ PASS. AR02 local corrections ✅ PASS. AR03 r3 preparation ✅ PASS.
AR04-L0 r2 ✅ PASS; AR04-L1 r2 ❌ FAIL; AR04-L2 r2 ✅ PASS with independent restoration.
The first r1 failure and all earlier statuses remain preserved. R2 demonstrates real baseline/updated archive
compatibility and unattended preparation with the standard TPM profile; it is not a full certification pass.
No provider test credential was issued, no release was signed and production remains unchanged.

Validation ✅ PASS: 114 affected Python tests, 217 guide checks, 258 local links, eight-file scoped nonfix
Markdown, procedure shell/collector checks and diff whitespace. Both r3 units, exact sudoers, 73-file archive
and copied-tool version probes pass; Nix objects verify. Preserve the failed import check, initial package
preparation guard and partial diagnostic collection results. The final handoff prose receives a scoped
lint/link/whitespace readback in the r2 live observation. Unchanged earlier evidence is reused only for its
original artifacts; changed orchestration requires fresh candidate certification/promotion.

AR04 🚧 BLOCKED on separately approved r3 integration and the remaining B1–B7 matrix. B3 previous-approved
image boot, B4 boot-artifact/PCR11 rejection and the complete B7 interruption matrix remain independent live
gates. AR05/P2–P4 remain blocked in order; no production boot/recovery PASS or readiness claim is made.
The exact production migration/recovery procedure remains in the dependency guide and requires its ordered
concrete approvals. SE22 runtime FAIL/review PASS and SE23–SE25 prepared v3 work remain unchanged.

Exact next action: review and approve AR04-L0/L1/L2 for the distinct r3 package above: exclusive source/tool
installation and actual UID 984 tool-readiness/version checks, temporary broker/socket access for UID 984,
fixed-VM power permission, one fresh maximum-four-hour lifecycle grant, and mandatory cleanup/restoration.
Neither consumed approval authorizes this next run. No additional operator inventory is required.
No r3 root installation, grant, production operation, commit, push or delegation occurred during preparation.

### AR04 r3 L0/L1/L2 approval and execution — 2026-09-10

The user's “approved” response accepts the preceding concrete r3 request: reviewed tool installation and
readiness checks under UID 984, temporary broker/socket access, fixed-VM power permission, exactly one fresh
maximum-four-hour lifecycle, and mandatory cleanup/restoration. The approval binds archive
7101a25a928ad3d5665a652c880962637251f0ca7b02ba53c880f4be0158300e,
policy d0bb04d7513ebd77750fb94f8831bc85cc14486191569d31e95282188919354a,
run 67ccc802152b9b7a8f500435a7d5e67429755be276b3e924bda581c79685f032.
Keep the preparation proposal unmodified; record approval and the issued grant separately. Preserve both
consumed runs, failed evidence, existing v3 policy work and unrelated changes. No production operation,
release signing, subsequent attempt, timer enablement, commit, push or delegation is authorized.

AR04-L0 r3 🔄 IN_PROGRESS: validate frozen package/73 files and exclusive destinations, original broker and
inactive prior campaigns, fixed-resource absence, trusted tool objects and exact installed readback. Validate
the actual child tool environment and both version probes under UID 984 before issuing the grant.
AR04-L1 r3 ⬜ TODO: issue the single run-bound maximum-four-hour grant immediately before one dispatch.
AR04-L2 r3 ⬜ TODO: reconcile provider/guest cleanup and independently verify exact original-control restoration,
temporary grant/access removal, resource/private-state absence and preservation of old source/policy/journals.
Full AR04 B1–B7 and AR05/P2–P4 remain open in order; dispatch or preparation does not establish certification.
Exact next action: finish L0 guards and actual-UID readiness, dispatch L1 once, then complete L2 on every outcome.

AR04-L0 r3 ✅ PASS at 2026-09-11T01:58:49Z: all 73 installed files match the approved archive;
actual UID 984 resolves SSH/sudo and both adjacent tool copies. Restic 0.19.1 and Trivy 0.74.0
version probes pass with the sanitized child environment. Original r1/r2 sources and journals are preserved.
Temporary reviewed controls are installed; production remains disabled. Next: one L1 dispatch, then L2.

AR04-L1 r3 🔄 IN_PROGRESS: dispatched exactly once at 2026-09-11T01:59:12Z, invocation
0b3287ece4ae49fdb48399df299fd1d5. Grant expires 2026-09-11T05:59:12Z. The controller confirms
actual-identity tool readiness before allocation. [R3 live observation](evidence/2026-09-11-hermes-standard-tpm2-r3-live.json)
records this distinct execution. AR04-L2 remains mandatory on every outcome.

R3 preparation observation at 2026-09-11T02:15:32Z: unattended installation completed and actual
encrypted-root recovery-key readback passed in the disposable fixture. No installed-boot or full
certification PASS is inferred; initrd review and signed boot are next. Production recovery remains unverified.

R3 preparation checkpoints: baseline archive ✅ PASS by 02:16:32Z, first installed signed boot
✅ PASS by 02:17:33Z, and baseline runtime/store plus verified baseline disk copy ✅ PASS by
02:24:39Z on September 11 UTC. The controller input is null. These sampled completion bounds
and exact archive/image hashes are retained in the r3 observation. Approved-update preparation is active;
full candidate certification and L2 remain pending.

R3 updated archive ✅ PASS by 02:35:49Z. Candidate preparation completed and certification began
by 02:36:51Z. At 02:38:11Z the certifier was reboot-pending, after encrypted backup and isolated
test-credential issuance. This passes the r2 missing-tool failure point; it is not yet a reboot/runtime
acceptance PASS. Provider revocation and L2 remain required before closing this consumed attempt.

### R3 integration pass and restored controls — 2026-09-11 UTC

AR04-L0 r3 ✅ PASS at 01:58:49Z. AR04-L1 r3 ✅ PASS: the single authorized invocation completed
successfully by 03:00:56Z. AR04-L2 r3 ✅ PASS at 03:01:21Z, independently verified in the same second.
The grant and invocation are consumed; no retry, production operation or release signing occurred.
The [r3 live observation](evidence/2026-09-11-hermes-standard-tpm2-r3-live.json) is the authoritative
sanitized execution evidence, including actual gate records, hashes, input checks and restoration.

All seven existing certifier gates pass: package replay, inference, warm/cold boot, runtime, encrypted semantic
restore, advisory scanning and provider revocation. The protocol/payload negative matrix and closed deploy/upgrade
rerun pass. Warm and cold observations both show Secure Boot, SELinux Enforcing, matching SRK public files,
successful early/late SRK services, the standard TPM profile, healthy Hermes and protected available credentials.
They identify distinct boot IDs and the same updated kernel 7.2.4-200.fc44.x86_64 and UKI hash
`e6384a32e8602b73168407b18198a8b189f4d634d6b05693b10ecca631e08501`.
Candidate manifest SHA256 is `f81c54e9e9904b220ab26f7c296862d0f27daa398e0cf6434c955e1c14723b3b`;
artifact fingerprint is `cb0946686666b49cd2a22e4f09558ca330362f213883c7c1a80cd9e1a5e7c49c`.
These are disposable-lab results, not production hardware proof or a signed promotion release.

L2 verified provider state revoked and credential file absent; guest/private/backup inputs and fixed VM,
disk, NVRAM and swtpm absent; original broker bytes, metadata, xattrs and test UID 987 restored; production role
still disabled; original socket user/group and 0600 mode restored inactive. Temporary units, override, sudoers,
power helper and active grant were removed. All three root-owned source snapshots, old policy/journals/timers,
r1/r2 failed evidence and the prepared v3 work remain preserved. Deletion is logical, not a storage-erasure claim.
Two read-only monitor processes were intentionally stopped during observation; the lifecycle ran exactly once
without interruption or retry. No provider terminal or raw credential was captured.

AR01 ✅ PASS bounded dependency review; AR02 ✅ PASS local correction; AR03 ✅ PASS r3 preparation/execution
package. AR04 🔄 IN_PROGRESS: the r3 integration subset passes, while the full B1–B7 matrix remains open.
The dependency conclusion is now supported by real standard-profile warm/cold boot and credential observations:
NvPCR anchoring is not required by this tested path. SRK, TPM disk/credential sealing and signed PCR11 remain
required for the chosen design. Arbitrary external NvPCR consumers remain unproven; the accepted inventories
are complete within scope and must not be requested again. SE22 FAIL/review PASS and SE23–SE25 remain unchanged.

Remaining certification: B3 previous-approved-image boot after the completed update with matching modules and
credentials; B4 separate boot-artifact/PCR11/command-line rejection and corresponding B6 credential denial;
B7 interruptions around artifact copy, replay and selection, complete retention/configuration checks, and
external notification delivery. Existing payload rejection does not certify boot-trust rejection. Preserve valid
r3 evidence for its exact artifacts; any changed code, policy, candidate, boot image or fixture identity makes
its affected certification/promotion evidence 🔁 STALE and requires fresh binding and acceptance.
AR05/P2–P4 remain 🚧 BLOCKED in order, and amended release signing is not authorized. Production remains unchanged.

No runtime code changed during this r3 execution. All 71 repository source files still match the approved
snapshot, so the 114 passing affected Python tests remain valid. Live UID 984 tool execution and the seven
integration gates provide new validation. Final scoped document/link/guide/whitespace and preservation checks
are pending for the closure text. The exact production migration/recovery procedure remains in the
[dependency guide](../HERMES_TPM_DEPENDENCY_REVIEW.md#migration-preparation-and-approval-sequence).
Exact next action: finish those local closure checks, then use the remaining lab gate specification in the guide
to prepare a fresh bounded fixture campaign; obtain its concrete approval before any new grant or invocation.
No further operator diagnostic request is needed for the completed dependency review.

R3 closure validation ✅ PASS: 217 guide checks, 269 local links, procedure shell and collector privacy checks,
eight-document scoped nonfix Markdown recheck, and whitespace. The initial overlong Markdown status line
and the trailing space introduced while wrapping it both failed; both results are preserved. The exact
line was corrected and Markdown passed. Repository preservation ✅ PASS: only the six authorized documentation
files and new r3 observation changed; all other bytes/modes, runtime/tests, prepared v3 work, previous evidence,
HEAD and branch are unchanged. The 114 affected tests are reused against unchanged source. Final text
receives one final scoped readback in the r3 observation. AR04 integration is complete; the remaining lab
matrix and AR05/P2–P4 stay open as specified above.

Scan scope: the existing advisory-denylist-v1 gate passed with policy SHA256
`a5c084a0b4879376ba307c85ea8c76a05857c217b09417cce19a72f472d2340d`. Its aggregate findings were
20 CRITICAL, 467 HIGH, 1516 MEDIUM, 975 LOW and 65 UNKNOWN. PASS means the configured advisory/denylist
policy passed; it is not a zero-vulnerability or exploitability assessment. The policy was not weakened.

L2 supplemental grant review: the parent grant is absent and the run is complete, but the consumed derived
candidate-window.json remains beside its state. Under the already approved mandatory cleanup, archive only
that exact root-owned grant after verifying its run/candidate/scheduler binding and original time interval,
then remove its active-path copy and independently verify both grant paths absent. This is evidence retention
and removal of a consumed lab allowance, not a new invocation or authorization. The initial L2 proof above
covered the parent grant; this supplement closes the derived-path check. Preserve both archived grants.

L2 derived-grant supplement ✅ PASS at 2026-09-11T03:09:28Z. Its exact validated bytes are retained
root-private at mode 0600; both parent and derived active grant paths are independently verified absent.
The already completed run was not invoked again. Future L2 procedures must cover both grant levels.
All authorized r3 operations are complete; the remaining certification specification and production gates
above are the exact next work. No additional operator evidence is requested.

## Remaining lab preparation amendment — 2026-09-11

Approved scope: the user requested local preparation of B3 first, then B4 and B7, with exact cleanup,
fresh run identities and bounded execution. The request explicitly requires fresh lab execution approval;
r3 is consumed. Preserve the existing `codex/hermes-unattended` feature branch and unrelated working changes.
This section is the canonical execution record; the new remaining-lab runbook will own the test procedures.
No grant issuance, lab allocation, provider call, notification delivery or privileged installation is authorized.

| Task | Dependency / authorized work | Progress | Validation gate (defined before implementation) | Gate status |
| --- | --- | --- | --- | --- |
| AR04-RP01 | Inspect r3 evidence, current source and resource/cleanup contracts | ✅ PASS | Source-grounded B3/B4/B7 steps; preserve consumed grants and historical evidence | ✅ PASS |
| AR04-RP02 | RP01; prepare B3 previous-image probe and ordered return-to-new-image experiment | ✅ PASS | Offline rejection/observation tests; verify post-update inventory, boot identities, modules and credential protection | ✅ PASS |
| AR04-RP03 | RP01; prepare B4 artifact/PCR11/command-line and B7 interruption/notification cases | ✅ PASS | Distinct fault/control cases, explicit result predicates, deterministic injection points and bounded recovery | ✅ PASS |
| AR04-RP04 | RP02–RP03; freeze review package, individual run IDs, operation bounds and cleanup | ✅ PASS | Exclusive identities, complete hash manifest, exact controls/removal paths, no issued grant or executable approval | ✅ PASS |
| AR04-RP05 | RP04; synchronize affected documentation and evidence | ✅ PASS | Relevant offline suites, guide, scoped nonfix Markdown, links, whitespace and preservation readback | ✅ PASS |
| AR04-RX | RP01–RP05 and fresh explicit lab approval; execute ordered cases | 🚧 BLOCKED | Actual lab observations, rejection controls, delivered notifications and independent cleanup | ⬜ TODO |

Expected local result: a concrete review package covering each remaining case, with live results explicitly
unperformed. Execution must stop at unmet prerequisites and record failures separately from cleanup.
Validation evidence will record UTC timestamps, source identities and commands. No production documentation
behavior is being changed by this test preparation. Exact next action: implement the B3 test preparation,
then complete B4/B7 and the review package before requesting the new lab approval.

RP01 inspection ✅ PASS: existing r3 evidence and cleanup are preserved; the deployed standard profile masks
`hardware.nvpcr`, `cryptsetup.nvpcr`, and `systemd-pcrproduct.service`, retaining both SRK setup services.
Notification transport is the existing desktop `notify.py`; no messaging integration is added.
RP02 implementation is complete locally; validation ✅ PASS at 2026-09-11T13:58Z: 10 new offline tests
(including real child-process interruption of atomic writes), 12 certifier, 69 lifecycle, 33 scheduler and
12 offline replay tests. These are local tests only. Subsequent observer import-path and explicit credential
service/mode checks require the focused final recheck. RP03 operator-session, tamper and interruption probes
are prepared; the runbook, frozen package and final validation remain in progress. No lab action occurred.
Exact next action: finish the per-case commands, freeze fresh identities/controls, and verify the package.

RP03 source review corrected two test hazards before final validation: replay completion can no longer be
reported as interruption (a live SIGKILL plus intermediate inventory is required), and the publication probe
holds the target lock and rechecks current staging state. Test-only copy chunking and supplemental-session
failure status are explicitly documented. Supplemental results do not create release/promotion evidence.

Final affected offline validation ✅ PASS at 2026-09-11T14:19:11Z: 138 Python tests, 138 ShellSpec examples,
217 Hermes guide checks, ShellCheck, shfmt and whitespace. The original Markdown command failed because the
temporary config filename was unsupported; the corrected isolated, nonfix run identified one long line and
three newly added extra blank lines. Those failures are retained; only those new formatting defects were fixed.
Package/links/final documentation readback are the remaining local gates. Lab execution remains NOT APPROVED.

### Local preparation closure — 2026-09-11

AR04-RP01–RP05 local preparation is complete. Final documentation and preservation checks passed.
The [runbook](../HERMES_REMAINING_LAB_TESTS.md) and
[preparation observation](evidence/2026-09-11-hermes-remaining-lab-preparation.json) bind the review package.
It contains 79 frozen source files, fourteen distinct unused case/run identities and exact per-case
installation, dispatch, grant archival, cleanup and independent restoration scripts. Budget is four hours
per separately approved row, including cleanup; no aggregate campaign execution is approved.

Package validation ✅ PASS at 2026-09-11T14:23:58Z: all 79 archive members and 310 package files match;
source matches the current workspace; root/policy/unit identities and time budgets are distinct and bound;
all 56 control-entrypoint checks reject missing approval before any operational command. UID was simulated
only for those negative tests; actual root installation/UID-984 tool execution remains a future L0 gate.
The complete B3 image/credential/module round trip is connected to the existing certifier. B4/B7 use bounded
operator sessions, explicit fault/control observations and separate supplemental results. The immutable
package manifest SHA256 is `16b38ee626915b5c2f14c8a3d51e036fbacac55e1c239e4d813918240c48fc63`.
The source archive SHA256 is `88ce89ee5c11c420c6d73185bab47e2b9e46fe318ec5a0c2e46ef2a2f83d1867`.

No grant, approval record, VM, provider request, desktop delivery or production change was made. No commit,
push, PR change or branch switch occurred. Existing uncommitted work and r3 evidence are preserved.
AR04-RX is 🚧 BLOCKED on fresh approval; all live B3/B4/B7 validations are ⬜ TODO. AR05/P2–P4 remain
blocked in order. This closes only the preparation amendment, not AR04 or the overall unattended plan.
Exact next action: request fresh approval for the `b3` block only, root
`/var/lib/hermes-remaining-20260911-b3-c618944c`, run
`c618944cdf9ab726cd663548b1f47c835892c09627c1a78ef98279384262c5f0`, then perform its L0/L1/L2 in order.

Final documentation recheck retained one extra blank line in `vm/DEPLOYMENT_TASKS.md`; the initial replacement
had targeted the wrong preceding word. The exact location was inspected and corrected. RP05 remains in
validation until the scoped recheck and link/preservation audit pass. No runtime source changed.

Final documentation and preservation ✅ PASS at 2026-09-11T14:28:04Z: seven isolated nonfix Markdown files,
202 local link targets, whitespace and source preservation. All 249 unrelated existing files, HEAD and the
existing feature branch retain their original identities. The retained formatting failures above are closed.
All preparation gates pass; no live gate has been run. Exact next action remains fresh b3-only approval.

### B3-only L0/L1/L2 approval and execution — 2026-09-11

The user replied “Approved” to the concrete B3-only L0/L1/L2 request, including mandatory cleanup within
four hours. This authorizes one dispatch of the frozen b3 case, run
`c618944cdf9ab726cd663548b1f47c835892c09627c1a78ef98279384262c5f0`, rooted at
`/var/lib/hermes-remaining-20260911-b3-c618944c`. The approved package manifest remains
`16b38ee626915b5c2f14c8a3d51e036fbacac55e1c239e4d813918240c48fc63`.
B4/B7, new release signing and production operations are outside this approval; r3 remains consumed.
The approved preparation baseline above and inert operation proposal are preserved.

| Task | Dependency and scope | Progress | Required validation gate | Validation |
| --- | --- | --- | --- | --- |
| AR04-RX-B3-L0 | RP01–RP05 and fresh user approval; immutable enrollment | ✅ PASS | Package/source hashes, exclusive resources, actual UID tools, protected inputs, prior-run preservation | ✅ PASS |
| AR04-RX-B3-L1 | L0 PASS; one bounded B3 dispatch | ✅ PASS | Existing seven certifier gates plus previous-image/update round trip and run-bound acceptance | ✅ PASS |
| AR04-RX-B3-L2 | Mandatory on every outcome | ✅ PASS | Provider/guest cleanup, exact fixture/control/grant removal, independent restoration and evidence | ✅ PASS |

[B3 live observation](evidence/2026-09-11-hermes-b3-live.json) records actual UTC times, commands and results.
Package verification passes for all 310 files. A blanket workspace mode comparison failed on the B4 canary
script (workspace 0644, approved archive 0755); bounded review confirms all 77 repository source bytes match.
The other two archive entries are the explicitly packaged host tools. Execute the unchanged approved archive;
no runtime or unrelated workspace edits are needed. Required documentation closure covers this plan, the
installation evidence ledger, remaining-lab runbook, dependency review and deployment ledger.
Exact next action: record the root-owned B3 approval, execute L0, dispatch L1 once only if L0 passes,
and finish L2 with independent restoration within the four-hour block deadline.

AR04-RX-B3-L0 ✅ PASS at 2026-09-11T16:48:51Z: all 79 installed source files match; actual UID 984
resolves and runs Restic 0.19.1 and Trivy 0.74.0. Exclusive resources and protected prior state pass.
The four-hour block began at 16:48:48Z; mandatory cleanup deadline is 20:48:48Z (15:48:48 Bogota).
Next: issue the run-bound grant and dispatch B3 once, then complete L2 regardless of acceptance outcome.

AR04-RX-B3-L1 🔄 IN_PROGRESS: exactly one dispatch at 2026-09-11T16:49:17Z, invocation
`26d18772a42d4503957318f2188329df`. The 10,200-second experiment grant expires at 19:39:17Z.
This consumes the B3 dispatch allowance. Fixture creation and certification are active; no acceptance PASS
is inferred. Exact next action: observe this invocation, retain fresh identities, and complete mandatory L2.

B3 preparation observation at 2026-09-11T17:06:17Z: fresh installation completed, pinned guest identity and
recovery readback passed; the actual baseline initrd archive passes the standard TPM2 masks/module checks.
Its initrd, signed image and guest identity hashes are retained in the live observation. First no-input boot
and completed-update acceptance remain pending. Next: observe the existing invocation through those gates.

B3 preparation observation at 2026-09-11T17:27:22Z: initial signed boot and verified baseline copy pass;
the prepared update completed and its actual updated initrd passes the standard TPM2 archive checks.
Fresh baseline/updated image and initrd hashes are retained in the live observation. The controller is
restoring the verified baseline before candidate enrollment and exact certification replay. No B3 PASS yet.
Exact next action: observe the existing certification path and mandatory L2; do not redispatch.

B3 certification observation at 2026-09-11T17:46:05Z: package replay and exact inference gates pass,
including the required update/persistence sequence. Candidate `e9bfce43eb1a8ba6faa6de98e094b4d65cd34670fa5600ae0c0816bf2e1546ea`
is now in updated-image cold-boot acceptance. Previous-image round trip, remaining acceptance and L2
are still pending. Exact next action: observe the approved round trip and retain all required run-bound gates.

B3 previous-image gate ✅ PASS at 2026-09-11T17:52:17Z; independent bound-evidence readback passed
at 17:53:27Z. Kernel sequence was `7.2.4-200.fc44.x86_64` → `6.19.10-300.fc44.x86_64` →
`7.2.4-200.fc44.x86_64`, with three distinct boot IDs and identical post-update RPM inventory, both
module-tree hashes, encrypted credential bytes, public PCR key and LUKS metadata. Both prior/return
inferences were exact `HERMES_OK`; Secure Boot, Enforcing, TPM services and protected runtime checks pass.
No reenrollment occurred. Remaining restore/scan/revocation and root acceptance/L2 gates are pending;
this intermediate pass does not close the block. Next: observe completion, then restore controls independently.

AR04-RX-B3-L1 ✅ PASS: root acceptance binds all eight passing gates to the exact candidate; independent
readback passed at 17:58:56Z. At 17:59:36Z the single service is inactive with success and lifecycle
`complete`; credentials, guest data, VM and private material are marked cleaned. AR04-RX-B3-L2 is
🔄 IN_PROGRESS for exact broker/control restoration, parent/derived grant archival and independent readback.
Exact next action: run the approved L2 scripts, then synchronize and validate closure documentation.

### B3 operational closure — 2026-09-11 UTC

AR04-RX-B3-L0/L1/L2 ✅ PASS. The lifecycle completed at 17:59:26Z; exact control restoration passed
at 18:00:07Z and independent restoration passed at 18:00:17Z. The entire operational block took
71 minutes 28 seconds, within the four-hour deadline of 20:48:48Z. The single dispatch allowance is consumed.
The [B3 live observation](evidence/2026-09-11-hermes-b3-live.json) owns the exact identities and results.

All eight root-accepted gates pass: package replay, inference, updated boot/runtime, previous-image round trip,
semantic encrypted restore, frozen-policy scan and credential revocation. Nine existing rejection/rerun checks
also pass. The scan retains 20 critical and 467 high findings under `advisory-denylist-v1`; it is not a
vulnerability-free image. Selected-entry checks are enforced by the frozen observer; raw bootctl histories
are not retained. The previous boot ran against the unchanged post-update inventory without reenrollment.

L2 verifies provider revocation and credential absence; guest/private/backup removal; fixed VM, disk pool,
NVRAM and swtpm absence; exact original broker bytes/metadata/xattrs and UID 987; inactive original socket;
removal of temporary units, override, sudo rule and power helpers; and preserved prior policies/journals/timers.
Both parent and derived grants were validated, archived root-owned at mode 0600, and removed from active paths.
The independent readback preserves r1/r2/r3 and current frozen source snapshots. Deletion is logical.
No runtime source changed, new release was signed, production operation occurred, or Git write was performed.

Operational scope is complete. Documentation closure is 🔄 IN_PROGRESS; required gate is scoped nonfix
Markdown, Hermes guide checks, local link validation, whitespace and frozen-package/source preservation.
Exact next action: finish those local checks. B4/B7 remain unapproved and unexecuted; `b4-linux` is the next
separate four-hour block after fresh explicit approval. AR04 as a whole and AR05/P2–P4 remain open/blocked.

B3 documentation closure ✅ PASS at 2026-09-11T18:05:08Z: 217 guide checks, six isolated nonfix Markdown
files, 196 local link paths, whitespace, 310 frozen package files and all 77 repository source bytes pass.
The first Markdown invocation linted 27 files because repository configuration overrode its intended scope;
that scope failure is retained. No Markdown modification timestamps advanced during it. A separate copied
six-document tree then passed with unchanged copy/workspace hashes. Prior Python/ShellSpec evidence remains
bound to unchanged source; those suites were not rerun for this execution-only/documentation change.
The final canonical-record readback is retained in the live observation.

The approved B3-only block and its documentation are complete. This does not close the full AR04 campaign.
Exact next action: await separate explicit approval for `b4-linux` only, with its four-hour L0/L1/L2 bound.
B3 and r3 approvals are consumed; no further lab execution is authorized. B4/B7 and production gates remain open.

Readiness follow-up — 2026-09-11: corrected the stale current-next-action summary above to B4-linux,
consistent with the completed B3 evidence. No lab or production operation is authorized by this status request.
For reporting only, AR01–AR03 are three completed milestones out of AR01–AR05 (60%, unweighted).
AR04 remains partial and AR05 blocked; P2–P4 have zero completed production acceptance gates.
This milestone count is not an estimate of remaining time, risk or deployment readiness.
Exact next action remains separate approval of the prepared `b4-linux` L0/L1/L2 block only.

### All-pending-tasks continuation authorized — 2026-09-11

Approval reference: user “proceed with all pending tasks” after the sixteen-item pending-task summary and
sudo/authorization explanation. This is new authorization for the thirteen prepared B4/B7 blocks and the
ordered P2–P4 production work within the existing migration scope. It supersedes the need to ask again for
each already described block; it does not remove prerequisite gates, per-case time limits, protected-path
rules, recovery requirements, or the prohibition on repeating a consumed one-dispatch fixture.
Keep per-case approval/grant records separate and issue only the current case's grant immediately before
its single dispatch. The thirteen lab blocks have a combined upper bound of 52 hours including cleanup;
only one fixture/control set may exist at a time. Desktop delivery is included only in b7-notifications.
No Git commit, push, delegation, permanent scheduler enablement or unrelated privilege cleanup is requested.

Approved baseline: unchanged r4 package manifest
`16b38ee626915b5c2f14c8a3d51e036fbacac55e1c239e4d813918240c48fc63`, source archive
`88ce89ee5c11c420c6d73185bab47e2b9e46fe318ec5a0c2e46ef2a2f83d1867`; existing feature branch and
unrelated changes are preserved. B3's eight-gate acceptance and independent restoration are prerequisites.
Each lab case's validation is its specified fault witness and healthy control, plus L0 enrollment and L2
independent cleanup. A failure blocks dependent cases; retain failed evidence and perform mandatory cleanup.
Production operations are made concrete and identity-checked at their ordered gates before execution.
Missing physical-console/recovery availability or required operator authentication remains an actual blocker.

| Task | Dependency | Progress | Required validation | Validation |
| --- | --- | --- | --- | --- |
| b4-linux | b3 | 🚧 BLOCKED | Case witness/control; L0 and independent L2; ≤4h | ❌ FAIL |
| b4-initrd | b4-linux | 🚧 BLOCKED | Case witness/control; L0 and independent L2; ≤4h | ⬜ TODO |
| b4-cmdline | b4-initrd | 🚧 BLOCKED | Case witness/control; L0 and independent L2; ≤4h | ⬜ TODO |
| b4-pcr11 | b4-cmdline | 🚧 BLOCKED | Case witness/control; L0 and independent L2; ≤4h | ⬜ TODO |
| b4-external | b4-pcr11 | 🚧 BLOCKED | Case witness/control; L0 and independent L2; ≤4h | ⬜ TODO |
| b4-credential | b4-external | 🚧 BLOCKED | Case witness/control; L0 and independent L2; ≤4h | ⬜ TODO |
| b7-before-copy | b4-credential | 🚧 BLOCKED | Case witness/control; L0 and independent L2; ≤4h | ⬜ TODO |
| b7-during-copy | b7-before-copy | 🚧 BLOCKED | Case witness/control; L0 and independent L2; ≤4h | ⬜ TODO |
| b7-before-publish | b7-during-copy | 🚧 BLOCKED | Case witness/control; L0 and independent L2; ≤4h | ⬜ TODO |
| b7-during-replay | b7-before-publish | 🚧 BLOCKED | Case witness/control; L0 and independent L2; ≤4h | ⬜ TODO |
| b7-before-select | b7-during-replay | 🚧 BLOCKED | Case witness/control; L0 and independent L2; ≤4h | ⬜ TODO |
| b7-after-select | b7-before-select | 🚧 BLOCKED | Case witness/control; L0 and independent L2; ≤4h | ⬜ TODO |
| b7-notifications | b7-after-select | 🚧 BLOCKED | Case witness/control; L0 and independent L2; ≤4h | ⬜ TODO |
| P2 | Full AR04 lab matrix and reviewed production inputs | 🚧 BLOCKED | Hardware B1–B7, retained recovery, exact boot/trust/configuration preservation | ⬜ TODO |
| P3 | P2 PASS | 🚧 BLOCKED | Restricted identities, isolated credentials, verified backup, production-bound release | ⬜ TODO |
| P4 | P3 PASS | 🚧 BLOCKED | Deployment/inference, restore/rerun, final documentation | ⬜ TODO |

Affected documentation: this canonical record, remaining-lab runbook, installation evidence ledger, dependency
procedure, VM guide and deployment ledger; update current status and retain historical evidence at each closure.
Preflight: workstation noninteractive sudo and all 310 package-file hashes pass. A parallel Devbox read failed
because its generated `.cmd.sh` was concurrently removed; the sequential retry read the ledger successfully.
Keep subsequent Devbox commands sequential to avoid that shared generated-script race.
Exact next action: independently reverify B3 cleanup, preserve current source/evidence hashes, record the
b4-linux approval, then perform its L0/L1, explicit rejection/control experiment, and mandatory L2.

B4-linux L0 ✅ PASS at 2026-09-11T21:20:22Z: all 79 frozen files and actual UID-984 tools match;
protected inputs, exclusive destinations and historical source checks pass. The block started at 21:20:18Z;
mandatory cleanup deadline is 2026-09-12T01:20:18Z (September 11, 20:20:18 Bogota).
Exact next action: dispatch the b4-linux fixture once, await operator-ready, run the specified rejection/control
experiment, then perform mandatory L2 before advancing.

B4-linux L1 🔄 IN_PROGRESS: dispatched exactly once at 2026-09-11T21:20:43Z, invocation
`dd35e0b7080c4dca8990443ece08b45c`. The experiment grant expires at 2026-09-12T00:10:43Z.
This case allowance is consumed; other authorized blocks remain unissued and dependent.
Next: observe this fixture through complete certification, then run the B4-linux probe only after operator-ready.

B4 artifact operator preparation: the approved procedure is transcribed in the private local continuation
operator directory, with exclusive per-phase checkpoints, exact trial readback, a bounded screen capture and
independent healthy-control/preservation checks. Syntax and the existing lifecycle tool environment pass.
This helper starts no fixture and will run only after the current run publishes operator-ready. Its source
hash is recorded in the continuation evidence; no frozen package or runtime source is changed.

B4-linux preparation observation at 2026-09-11T21:36:46Z: installation completed; fresh guest identity
and recovery readback pass. The existing invocation is preparing its signed baseline. No supplemental
experiment has run. Timestamped sanitized observations are retained under this case root.
Next: wait for complete eight-gate certification and operator-ready before invoking the approved probe.

B4-linux preparation observation at 2026-09-11T21:57:07Z: the verified baseline copy and both actual
initrd archive reviews pass. The updated image has been built; its digest and archive checks are retained
in the root-owned observations. The fixture is restoring its verified baseline for exact certification replay.
The supplemental probe remains unexecuted; next is the eight-gate prerequisite and operator-ready marker.

B4-linux prerequisite certification ❌ FAIL at the `reboot-pending` transition (recorded 2026-09-11T22:00:26Z):
`lab-operation-failed`; no operator-ready marker and no deliberate tamper experiment. Provider revocation
passes, but prior-credential restoration failed while the guest was unreachable. Automatic cleanup retained
the VM and private recovery material; its terminal state is `cleanup-failed`. At 22:02Z the VM screen showed
the existing offline replay still running within its 25-minute bound. No power interruption was performed.
L2 is 🚧 BLOCKED pending guest recovery, and all dependent cases/production are blocked by the failed gate.
The original single-dispatch allowance remains consumed. Exact next action: observe this existing replay,
recover guest credential cleanup when reachable, finish L2, then diagnose and prepare a concrete correction.

### B4-linux failure remediation preparation — 2026-09-11

The all-pending instruction authorizes necessary reversible local corrections and review preparation.
Frozen r4 inputs and this failed run remain unchanged; no replacement dispatch is authorized by this edit.
Observed evidence: a parsed response without a protocol error became `lab-operation-failed` after an
acknowledged `reboot-pending` stage, while the guest continued its offline replay. The original SSH exit
code/response shape was not retained, so exact transport causation remains unconfirmed. Inspect and cover
the narrow case of a complete, correctly bound positive pending-reboot reply followed by SSH failure.
Never retry a reported guest error, malformed reply, wrong release or unrelated operation. Preserve the
existing prior-stage and deadline requirements; retain only allowlisted transport metadata on failures.

Local remediation gates: reproduce the boundary with a focused failing regression; implement only the
certifier transport correction and bounded diagnostics; pass focused and full required Python tests,
relevant ShellSpec/guide/documentation checks, and review the exact diff. Preserve pre-existing edits.
Any source correction invalidates r4 applicability for future runs; retain r4/B3 historical evidence and
prepare a fresh reviewable package before requesting a replacement one-dispatch lab allowance.
Mandatory cleanup recovery of the current fixture has priority and remains within its original time bound.

### B4-linux operational closure and corrected preparation

B4-linux L0 ✅ PASS; prerequisite L1 ❌ FAIL before operator-ready; tamper experiment ➖ N/A because its
prerequisite failed. The primary failure and initial cleanup failure remain recorded. Offline replay completed
at 22:07:49Z without a forced power interruption; subsequent readback verified the expected package inventory,
updated kernel, Enforcing and retained previous image/modules. This recovery observation is not certification.
A read-only recovery probe initially used the wrong sudo command form; the existing authorized bash wrapper
then passed, without a privilege change. Cleanup-only recovery restored the prior credential and purged the
fixture. L2 ✅ PASS at 22:14:10Z; independent restoration ✅ PASS at 22:14:22Z, also rechecking B3 preservation.
The block took 54 minutes 3 seconds, within its four-hour limit; both grants are archived and inactive copies,
private material, VM/storage/NVRAM/swtpm and temporary controls are absent. Original broker metadata and UID 987
are restored. The failed allowance is consumed. All dependent B4/B7 and P2–P4 gates remain blocked.

Local correction: the focused red run had four failing reboot-stage/SSH-exit subcases among 15 tests. The
corrected focused suite passes 16 tests; the other required suites pass 126, for 142 Python tests total.
ShellSpec passes 138 examples. Exact positive, same-release pending-reboot deploy replies with SSH exit 255/143
are classified as transport loss; the existing prior-stage/deadline guard still decides whether to retry.
Reported guest errors and unbound replies remain failures. Primary transport metadata survives cleanup failure,
without retaining raw response contents. This demonstrates the handling defect locally; the original live exit
code was not captured, so its precise cause remains unconfirmed. Frozen r4 inputs were never modified.

The single-block r5 review package passes 103 file checks, all 79 archive members, 77 repository byte matches,
and four simulated-UID missing-approval refusals before operations. Its one runtime change is `certify.py`;
old r4/B3 evidence retains its original binding and supplies no corrected-code PASS. The runbook records exact
new package/run/source/policy identities. No approval record, grant, root enrollment or new fixture exists.
Documentation closure is 🔄 IN_PROGRESS. Exact next action: complete scoped documentation and diff review,
then request only the fresh replacement B4-linux allowance required by the consumed one-dispatch limit.

B4-linux correction/documentation preparation ✅ PASS at 2026-09-11T22:21:53Z: 142 Python tests,
138 ShellSpec examples, 217 guide checks, six isolated nonfix Markdown files, 203 local link paths,
whitespace and exact runtime/test diff review pass. The first scoped Markdown check found a doubled blank
line and a missing blank after the new task table; both are corrected and the failed check is preserved.
The original r4 package still passes all 310 file checks; the separate unapproved r5 package passes 103.
Source changes are bound to r5 and have no live acceptance. No additional lab dispatch, production operation,
Git commit/push or ordinary scheduler enablement occurred. The canonical campaign remains open and blocked.
Exact next action: fresh explicit approval for only r5 B4-linux L0/L1/L2, one dispatch and mandatory cleanup
within four hours. Authorization for the other pending tasks remains recorded, subject to the failed gate
and corrected source preparation. Final record readback is retained in the continuation evidence.

### Continued lab execution authorized through production boundary — 2026-09-11

Approval reference: user “do not request approval until production deployment and keep completing all tasks”.
This instruction authorizes necessary local corrections, package refreshes and fresh bounded replacement lab
runs without another approval prompt. It supersedes the prior requirement to ask for each replacement block.
It does not authorize reusing a consumed grant, concurrent fixtures, skipping failed gates, or extending any
run beyond its four-hour total cleanup limit. Record the same standing authorization in each fresh run's
approval record; issue its grant only immediately before its single dispatch. Preserve failed attempts.
Production deployment remains the user-approval boundary. No Git writes, delegation or ordinary timer
enablement is requested. Continue independent preparation when a prerequisite fails, and repair/retest locally
before a fresh run. The plan remains open until all required lab and documentation gates are complete.

Next: enroll r5 B4-linux using its verified 103-file package, dispatch once, complete prerequisite certification,
then the bounded signature rejection/control experiment and mandatory independent L2. Later blocks require
corrected frozen sources and their preceding acceptance/cleanup gates. Prior B3 and failed r4 remain history.

R5 B4-linux L0 ✅ PASS at 22:58:07Z; one L1 dispatch at 22:58:24Z, invocation
`46d180908e0b4344ac97833c658d50bd`. Block start 22:58:04Z; mandatory cleanup deadline
2026-09-12T02:58:04Z (September 11, 21:58:04 Bogota). The experiment grant expires at 01:48:24Z.
Standing authorization is recorded separately from the consumed r4 allowance. Next: await this fresh
fixture's full certification and operator-ready marker; perform the bounded probe and mandatory L2.

R5 observation at 23:11:29Z: installation remains active with increasing disk/CPU activity; no certification
result yet. The four current status documents now reflect the standing authorization and r5 cleanup deadline.
Local preparation also produced a generic subsequent-block package builder and bounded external-command-line
and credential-denial operator scripts in the private continuation-operators directory. Their Python and embedded
guest-program syntax checks pass; they have not run against a fixture and claim no live acceptance.
Exact next action: finish r5 prerequisite certification, then its single artifact rejection/control experiment,
automatic cleanup and independent L2 verification before preparing the dependent fresh block.

R5 observation at 23:24:43Z: baseline initrd review ✅ PASS, signed baseline boot/guest readiness observed,
and verified cold baseline copy saved. Update preparation remains 🔄 IN_PROGRESS. No operator probe has run.
Local preparation now includes paired-PCR boot/control, external-command-line, credential-denial and three
publication-interruption operator scripts; syntax checks pass, but all live probe results remain ⬜ TODO.
The public-only scripts are outside the frozen runtime source. They will be hash-bound to each future package
and copied into its root-owned run before use. Failed evidence is retained, and no old grant is reused.
Six current documents pass isolated Markdown validation; the initial line-wrap failure and correction are retained
in the private validation directory. Next: continue the r5 update preparation and prerequisite certification.

R5 prerequisite certification 🔄 IN_PROGRESS at 23:36:10Z after both actual initrd reviews, baseline
restoration and fresh candidate enrollment. Updated kernel is `7.2.4-200.fc44.x86_64`; certifier stage is
`deploying`. The B4 tamper probe remains gated on full certification and operator-ready.
Exact next action: observe the acknowledged reboot transitions, then all eight candidate gates.

### R5 final-gate failure and authorized bounded reconciliation — 2026-09-12 UTC

R5 prerequisite certification ❌ FAIL at provider revocation after seven gates passed. No operator-ready
file or tamper experiment occurred. The original failure is retained. At 00:01:32Z, the existing cleanup retry
confirmed broker state `revoked` and absence of the encrypted test credential; fixture cleanup remains underway.
The first provider error was intentionally sanitized by the broker and its exact cause is unconfirmed.

Under the September 11 standing authorization, prepare a bounded retry of the same idempotent test-lease
revocation operation. Retain the existing provider deletion/HTTP-401 acceptance requirement, do not issue another
credential, and fail closed after the retry limit. Record sanitized attempt outcomes for success and failure.
Validation gate: immediate success, transient failure then confirmed success, exhausted attempts without a PASS,
and nonretryable malformed replies; run affected certifier/broker/lifecycle checks. Preserve r5 source/journals.
After independent r5 cleanup PASS and local checks, prepare and dispatch one fresh replacement B4-linux run,
with a new identity and its own four-hour limit. Do not ask for another lab approval or skip the failed gate.

R5 independent cleanup ✅ PASS at 2026-09-12T00:04:12Z, 3968.077656 seconds after block start.
All fixture/private resources and temporary controls/grants are absent; original broker metadata and UID 987
are restored. The original failed certifier journal remains unchanged. Later credential-revocation evidence
is cleanup recovery only; it does not convert the failed certification into acceptance.

Bounded revocation correction ✅ PASS locally: 21 certifier tests, 131 unattended trust/broker tests,
69 lifecycle tests, 33 scheduler tests, 12 remaining-lab tests and 12 offline-replay tests (278 Python total),
138 ShellSpec examples and 217 guide checks. The regression first failed before implementation. Only the
existing test lease is reconciled, with at most three requests and 1/5-second delays; provider deletion and
actual rejection remain mandatory. Nonretryable malformed replies and interruptions fail immediately.
Exact next action: complete current document checks, prepare a fresh B4-linux replacement with closed r5
evidence preserved, enroll and dispatch once under the standing authorization, then complete its bounded gates.

### R6 replacement B4-linux enrollment — standing authorization

Fresh package `/var/home/cloudops/.local/state/hermes-remaining-lab/20260912-b4-linux-review-r6`:
103 file checks, 79 archive members, 77 current repository byte matches and all four missing-approval
refusals ✅ PASS. Six current documents pass isolated Markdown checks; 202 local link paths pass.
The package preserves B3 and both failed B4 attempts with exact closed-history hashes.

- Run: `f8cd58976a1696b697734012f02cda0cd5853b97a1392e065941a84d90ca63b3`.
- Root: `/var/lib/hermes-remaining-20260912-b4-linux-r6-f8cd5897`.
- Unit: `hermes-remaining-20260912-b4-linux-r6-f8cd5897.service`.
- Manifest SHA256: `ca338646561689dfe564f0a9744f565ca5fb5639b2f1d7ccfa3b5ea5af4bceab`.
- Source archive SHA256: `4fde15f7b35b49dd83347b2e30c8482dc6ad4a950346e7e2dde522b18d34b311`.
- Policy binding: `851c8ad90465684047665c934d8c6bbaf2fc7465223a4f98beb7ecb6dc5897fb`.

Authorization remains the user's September 11 instruction to complete all tasks without another approval
request until production deployment. This is a new single-dispatch lab run; r4/r5 grants remain consumed.
Record the actual start and four-hour cleanup deadline, pass L0, dispatch once, and require full prerequisite
certification before the one-byte `.linux` rejection and healthy recovery control. Complete exact cleanup
and independent L2 before moving to `b4-initrd`. No production operation or ordinary timer enablement follows.

R6 L0 ✅ PASS at 2026-09-12T00:11:54Z. Exactly one L1 dispatch at 00:12:21Z, invocation
`21fe426f079c4c3bacd3254498f58ba5`. Block start is 00:11:43.321520Z; mandatory cleanup deadline
is 04:11:43.321520Z (September 11 at 23:11:43 Bogotá). Grant expires at 03:02:21Z.
The 79-file root source, actual UID-984 tool path and all three historical runs passed enrollment checks.
Next: monitor this fresh fixture through prerequisite certification, then its one artifact rejection/control
experiment and mandatory cleanup. Later cases remain dependent on acceptance and independent restoration.

R6 installation is active. Its frozen artifact helper is copied to `root/operators/artifact_probe.py`,
SHA256 `8971f8bf64193922b565637222306a33fc59303e31455a1a27bcf821de4e9842`, root-owned mode 0600.
A separate root wrapper records only exception type and file/function/line on failure, excluding exception
text and locals. Wrapper SHA256 `473f21db5427a78c13f3a2e3c4aa0715dce027a94da6b89ac1b906f65c496a85`.
Neither wrapper nor probe has executed; operator-ready and all prerequisite gates remain mandatory.

Additional cleanup integration regression at 00:22:41Z: the unchanged r5 certifier reproduces
`provider-revocation-failed` after one simulated broker rejection; the current certifier reconciles the same
lease and records PASS only after confirmation. All 22 focused certifier tests pass (279 Python checks total
with the previously completed affected suites). Only a test was added; r6 frozen runtime bytes still match.

Prepared r6 read-only revocation-state watcher, SHA256
`68b1d89747333ab43a24540bb23cf02c17ec10c0e1ff9ab02a82212ffa37c0eb`. It reads only the fixed lease
record/status and credential-file presence, makes no API calls and never reads credential contents.
Run only at final credential cleanup; it exits after confirmed revocation or ten minutes. Not yet executed.

R6 updated initrd review ✅ PASS observed at 2026-09-12T00:48:35Z. Both actual initrd archives pass
standard-TPM2 mask/module checks. Baseline is preserved; candidate certification follows baseline restoration.
Updated EFI SHA256: `5277e62b7777486fd6eb49db602ba477b21c7c51ddbb9d5920b30830b7eb2c67`.
Six current documents passed isolated Markdown validation at 00:45:58Z; workspace and copies were unchanged.
Exact next action: require all eight prerequisite certification gates and operator-ready before the tamper probe.

R6 prerequisite certification 🔄 IN_PROGRESS observed at 2026-09-12T00:50:33Z. Candidate
`83419f27f8cc67210db2f596d3eda0f288fd942fcb1414863d44a966c332fecb` is enrolled with updated
kernel `7.2.4-200.fc44.x86_64`; all prior sources and cleanup histories remain frozen.
Exact next action: observe certified update/reboot progression, all eight gates, then the operator-ready marker.

R6 updated return boot observed read-only at 01:02:46Z: kernel `7.2.4-200.fc44.x86_64`,
offline replay inactive/success, update marker absent, credential service active/success, and new boot ID
`b499f309-c57a-41f6-b508-9bc1bd6acce1`. The certifier independently advanced to
`persistence-reboot`, observed at 01:03:47Z. No operator tampering has begun.
Exact next action: complete persistence and the remaining prerequisite certification gates.

R6 package replay and inference ✅ PASS at 01:05:17Z; cold-boot checks are underway.
The read-only revocation watcher was armed at 01:06:07Z with a 30-minute bounded launch wait.
It executes only when the certifier reaches final acceptance or failure, then observes for at most ten minutes.
It does not issue, revoke, or read a credential. Exact next action: observe cold/previous-boot recovery gates
and final revocation, then run the single B4 artifact experiment if prerequisite acceptance completes.

R6 prerequisite certification ✅ PASS: all eight gates, with first-attempt credential revocation at
01:15:06Z. Scheduler completion, acceptance and operator-ready were observed at 01:17:15Z.
Acceptance SHA256: `49596c45044efc75c9ee90a5aecfbd3582f1aac133af4433a99cde63d576b093`.
The scan passes `advisory-denylist-v1`, with 20 critical and 467 high findings retained; this is not
a vulnerability-free claim. The revocation watcher finished with revoked state and no encrypted credential.
B4-linux operator preparation 🔄 IN_PROGRESS: the frozen wrapper was invoked once after these prerequisites.
Exact next action: verify the one-byte mutation/signature control, one-shot rejection witness, healthy recovery
and preservation, then exact cleanup and independent L2 within the original 04:11:43Z deadline.

### R6 supplemental preparation failure and lab capacity correction

R6 B4-linux preparation ❌ FAIL at 01:17:58Z after the intact-image signature passed and the
one-byte `.linux` mutation was rejected by `sbverify`. The trial was not booted or selected.
Read-only guestfish diagnosis at 01:19:21Z confirms the 600-MiB EFI filesystem has zero available blocks
and a partial trial path. All eight prerequisite gates remain valid evidence; B4 acceptance did not occur.
Recovery is removing only the exact run-specific partial file after checking its prefix against the intended
trial, then validating the intact control and protected state before mandatory cleanup and independent L2.

Under the standing authorization, enlarge only the disposable Server kickstart EFI partition to 2048 MiB
and add an available-space check to future artifact operators before mutation/upload. Preserve all current
and historical frozen sources and failed journals; do not resize or recertify this active fixture.
Validation gate: inspected one-line Kickstart change, applicable guide checks, syntax/capacity behavior of
the public operator helper, package byte checks, then a fresh single-dispatch replacement and its live gates.
Exact next action: finish r6 recovery and independent cleanup, validate the correction, build the next fresh
B4-linux package with both authorized source corrections and the lab-only Kickstart change, then continue.

R6 independent cleanup ✅ PASS at 2026-09-12T01:26:22Z, 4478.822010 seconds after block start
(74 minutes 39 seconds). Original broker bytes/metadata/UID 987 are restored; VM, private material,
temporary controls and active grants are absent. All historical and current source snapshots are preserved.
[R6 live evidence](evidence/2026-09-12-hermes-b4-linux-r6-live.json) separates prerequisite PASS,
supplemental FAIL and recovery/cleanup PASS. All 217 guide checks pass after the lab Kickstart correction.
Future artifact and paired-PCR operators check available EFI space before copying their trial images.
Exact next action: freeze and validate a fresh B4-linux replacement package, pass L0, dispatch once under
the standing authorization, and repeat its required live gates with a new four-hour cleanup deadline.

### R7 B4-linux replacement — lab EFI capacity correction

Fresh package: `/var/home/cloudops/.local/state/hermes-remaining-lab/20260912-b4-linux-review-r7`.
Manifest SHA256: `6aebf7b654f0f3b19efa73bd5f9700834a92744f9621dac9bb482ae9ea090211`.
Source archive SHA256: `9fc151e19e1114ebbe02fade229e3b65b7509e960112eb69fcf62c9f7ea7bfc1`.
Run: `ef1bc7331132dd4cb43d4475347139b24cae0cd879e2165b2df708c7b101ef0a`.
Root: `/var/lib/hermes-remaining-20260912-b4-linux-r7-ef1bc733`.
Policy binding: `7200322b23fd50ae8377c85170f453ee0b01e701015398685217cbb392cddb78`.

Package validation ✅ PASS at 01:29:30Z: 103 files, 79 archive members, 77 current repository byte
matches and all four missing-approval refusals. The package includes the corrected 2048-MiB lab EFI
partition and pre-copy capacity guard. It preserves B3 and all three failed B4 attempts by exact hashes.
The September 11 standing authorization covers this fresh bounded replacement without another prompt.
Acceptance still requires all eight prerequisite gates, actual boot-manager rejection, healthy recovery,
exact cleanup and independent L2 within four hours. No existing grant or failed journal is reused.
Exact next action: record the actual L0 start/deadline, enroll, dispatch once, then execute those gates.

R7 L0 ✅ PASS at 2026-09-12T01:30:15Z. Exactly one L1 dispatch at 01:30:32Z, invocation
`6db32239207144fca0fd0aeeba57cedb`. Block start: 01:30:11.550540Z; mandatory cleanup deadline:
05:30:11.550540Z (September 12 at 00:30:11 Bogotá). Grant expiry: 04:20:32Z.
All 79 root source files and four preserved completed/failed lab histories passed enrollment verification.
Exact next action: complete this fresh fixture and prerequisite certification, then the one-shot trial
with verified EFI capacity and mandatory recovery/cleanup. Do not dispatch again.

### R7 early installer failure and resource checkpoint

R7 ❌ FAIL before installation completed: the installer subprocess failed and the original error output
was not retained. No candidate, test credential or operator experiment was created. Automatic cleanup
finished; L2 restored controls at 01:31:41Z and independent restoration ✅ PASS at 01:32:13Z.
The host resource check separately fails at 01:33Z: approximately 8.2 GiB available versus the required
9 GiB. This confirms a current blocker, not the exact historical installer error. Do not lower the requirement
or close unrelated applications. Preserve the failed run and wait for sufficient resources before a replacement.

Authorized local correction: record public memory/disk/CPU measurements both at fixture preflight and
immediately before starting the installer, retaining the existing minimums. Validation gate: a simulated
drop after media preparation must prevent installer dispatch and retain the failed checkpoint; the lifecycle
suite must pass. Exact next action: finish closed-run evidence, implement and verify this diagnostic gate,
and observe host capacity before preparing another fresh single-dispatch replacement.

### Throughput revision — 2026-09-12

Approved scope: the user's request to reduce total time to production readiness through earlier preflight,
preparation during active VM work, prompt eligible dispatch and valid evidence reuse. At inspection there
is no active libvirt domain; r7 controls are removed. Never modify a future active run's frozen package.

Measured bottlenecks: r6 spent approximately 38 minutes from dispatch to candidate certification and
27 minutes more to operator-ready; trial preparation then failed on EFI capacity. Independent cleanup
closed that attempt after 74 minutes 39 seconds. R5 closed after 66 minutes 8 seconds. These are observed
attempt timings, not forecasts for all cases. R7 failed before installation; its original error is unknown.
Current RAM is below the unchanged 9-GiB minimum. The host has approximately 13.6 GiB total RAM.

| ID | Revised task and dependencies | Acceptance gate | Status |
| --- | --- | --- | --- |
| TP1 | Reconcile current fixture/failed history | No active fixture disturbed; exact L2 evidence retained | ✅ PASS |
| TP2 | Prepare all public operator/control templates before dispatch | Static inventory complete; semantic review and guest checks remain live requirements | ✅ PASS |
| TP3 | Prepare subsequent cases during VM install/certification | All 13 templates inventoried; next package prepared; no active VM currently | ✅ PASS: preparation complete |
| TP4 | Dispatch promptly when eligible | Fresh identity/grant, actual resource/L0 checks, predecessor PASS and independent L2 | 🚧 BLOCKED: RAM below 9 GiB |
| TP5 | Reuse unchanged offline evidence | Per-case hashes and stale-input refusal; live candidate evidence remains run-bound | ✅ PASS |
| TP6 | Complete matrix and deployment package | Every required lab/security/recovery/revocation/cleanup gate, then reviewable production package | 🚧 BLOCKED: lab gates |

Expected savings (estimates): move 2–5 minutes of operator/package preparation per case off the serial
path, approximately 26–65 minutes across 13 cases, assuming preparation can overlap VM work. Preventing
one comparable late setup failure avoids approximately 65–75 minutes; this is conditional, not guaranteed.
Hash reuse avoids rerunning unchanged offline suites; no fixed saving is claimed without timing those suites.
The 52-hour aggregate limit remains an upper bound, not an estimate. Each block still has four hours total.

Parallel fixtures are not selected: two existing 8-GiB guests exceed this host's total RAM, and fixed domain,
IP, UUID, pool, broker and power-control ownership would require redesign and validation. Even with extra
hardware, estimated setup/validation is 4–8 hours, and current ordering prevents overlapping dependent
experiments. No measured saving supports implementation on this host.

Reusable clean installation images are not selected for this remaining campaign. Existing saved baselines
contain run-specific machine/SSH identities, disk encryption and TPM enrollment; cloning them would violate
isolation. A pre-enrollment image pipeline would need identity/key regeneration, fresh TPM/NVRAM and full
boot/recovery validation. Estimated setup plus validation is 4–8 hours versus at most approximately
3–4 hours of installation savings across 13 cases (assuming 15–20 minutes saved each). These are estimates;
retain fresh installs and revisit only if measured remaining campaign costs change that comparison.

Sequence: stage and inspect all remaining templates now; resolve preparation gaps while the active fixture
installs; after acceptance and independent L2, finalize the next package with fresh IDs/history, run only its
necessary changed-input and live preflight checks, and dispatch immediately. Keep the B4/B7 order unchanged.
No prepared snapshot is an approval, grant, live PASS or permission to use another run's credential or TPM.

Rollback: the preparation checker is read-only apart from its explicit report file. Discard a stale report
and rerun only affected checks; retain prior reports as history. If a new preparation guard fails, stop before
dispatch and correct it. For dispatched failures, use that frozen package's existing cleanup and independent
L2; never edit its inputs or reset its journals. Revert future-only optimizations by building a new package
from reviewed source, never by changing the active run. Production remains a separate approval boundary.

Throughput implementation: [preparation inventory](../../scripts/remaining-lab-preflight.py) checks all
13 operator/control sets, ownership/modes, 170/50-minute service bounds and root tool fingerprints.
Five focused tests pass: missing operator isolation, unsafe links/syntax, missing cleanup/unbounded unit,
content/permission drift, and per-case reuse unaffected by unrelated changes. A real guide edit correctly
invalidated the old snapshot. Snapshot PASS is static preparation only, not guest or witness acceptance.

The private package builder now requires unchanged per-case preparation evidence before creating a package
and records its report hash. The notification helper is prepared for fixed local events, deduplication,
service-failure coalescing, off-window evaluation, failed transport, explicit retry and exact state cleanup.
It never claims visible delivery from a successful send; the real receipt gate remains mandatory.
No notification, credential API request or VM action was performed by this preparation work.

Fresh r8 is prepared and validated, not enrolled or dispatched:
`/var/home/cloudops/.local/state/hermes-remaining-lab/20260912-b4-linux-review-r8`.
Manifest: `06c830f554eedb415d5240e8840a01cfc428790e341b9905c185f6fc0df1f039`.
Source archive: `0a82bef486cd0d0ceed018fef8fe5902623587c32b871166d7116031da7407d7`.
Run: `6d576e193ff4c6239bb40f6dd5d71f5c6b53773ce4af74e79e94a510b265f421`.
Root: `/var/lib/hermes-remaining-20260912-b4-linux-r8-6d576e19`.
Package checks pass: 103 files, 79 archive members, 77 repository byte matches and four missing-approval
refusals. No grant exists; no four-hour window has started. The inherited transport/revocation, EFI capacity
and resource-check corrections are frozen in this package; unchanged prior offline suites were not repeated.

[R7 evidence](evidence/2026-09-12-hermes-b4-linux-r7-live.json) now retains its failure and independent L2.
At 01:52:42Z, available memory was 8,391,688 KiB versus 9,437,184 required; noninteractive sudo works,
and no libvirt domain exists. Current blocker is capacity, not missing approval. Do not lower the gate or
close unrelated applications. Exact next action: check actual capacity and r8 input hashes, enroll/dispatch
once when eligible, then complete the ordered matrix and prepare the production deployment package.

Final throughput checks ✅ PASS at 01:55:47Z: five focused preparation tests, seven Markdown
documents, 222 local link paths, and r8 package validation. The [preparation evidence](evidence/2026-09-12-hermes-throughput-preparation.json)
records all 13 static case inventories and tool fingerprints. Latest RAM is 7,762,952 KiB versus
9,437,184 required; no VM exists and no r8 grant is issued. Live work remains 🚧 BLOCKED on capacity.
No production deployment package can be accepted until the remaining live matrix passes. Exact next action:
recheck resources and r8 hashes, enroll and dispatch once when eligible, then follow the revised sequence.

While r8 installs, prepare the production review directory locally: render the existing four-path TPM
profile into an exclusive offline tree and fingerprint its public configuration and source inputs.
Acceptance: exact three null masks and one dracut file, unchanged input hashes, and explicit missing live
boot/backup/token/release fields. This is preparation only; no production command may be executed from it.
Rollback: discard only the new local staging tree if stale; preserve production and all lab snapshots.

Offline production configuration review ✅ PASS: all four expected destinations match the existing
renderer. [Preparation evidence](evidence/2026-09-12-hermes-production-review-preparation.json) records
source fingerprints and absent live backup/image/token/release evidence explicitly. Production was not
accessed. The review directory is not an accepted deployment package; complete the live matrix first.

Documentation validation: Markdown initially failed on two overlong status lines; an initial replacement
missed those lines. Inspection identified them, wrapping fixed both, and the configured 28-document
Markdown check then passed. No runtime inputs changed and no offline runtime suite was repeated.

Independent preparation: four embedded guest-script syntax checks passed (credential probe including its
unrelated-user child, PCR control, external command line). Read-only desktop preflight confirms a session
bus, runtime directory, notify-send, gdbus and an owner for org.freedesktop.Notifications. No notification
was sent and visible receipt remains unverified; this closes tool availability only, not B7 acceptance.

R8 progress at 02:29:40Z: installation finished, recovery readback passed and fresh guest identity was
recorded. Baseline initrd inspection passed all three masks and required TPM/PCR11 modules with no unknown
definition. Boot and certifier acceptance remain pending. Approximate measured dispatch-to-installation
completion was 16–17 minutes, bounded by observations; it is not an exact installer runtime.

R8 entered certification by 02:50:47Z, approximately 39 minutes after dispatch (observation-bound
measurement). Both initrd inspections passed and the saved baseline was restored for the actual update
test. Candidate: `a88a306ba515570c1f3c2e63543bac036721826f29d9c8a6120fc4e5dc474166`.
Eight prerequisite gates, the B4-linux rejection/recovery experiment and independent L2 remain pending.

R8 prerequisites ✅ PASS: all eight root acceptance gates match this run, release and artifact.
Operator-ready was observed at 03:15:38Z; preparation started once immediately after independent binding
verification. Revocation attempt 1 recorded broker-rejected; the frozen bounded same-lease retry passed on
attempt 2. No credential was reissued. Acceptance SHA256:
`518fdcccb2b455c7ea69c2c3d7a95cb8405a51c4e056c90386b4d9746be2515f`.
The supplemental kernel rejection/recovery and independent L2 are still pending.

R8 B4-linux supplemental validation ✅ PASS; cleanup is 🔄 IN_PROGRESS. The exact one-byte kernel
mutation failed sbverify and the boot manager explicitly denied loading its exact EFI path. Hash-verified
frame-0013 is the visual witness. The serial keyword filter found no matching line, and trusted Fedora
fallback is not the acceptance basis. The UEFI LoadImage policy-denial interpretation is recorded with
primary-source references in the public case evidence. Approved control recovery passed at 03:24:49Z;
protected state and persistent default are unchanged. Case evidence SHA256:
`638ea957b538ac8dc5279c4b57659588d5f52cbe8fc0cd7beb980e333a86c578`.
Exact next action: complete frozen cleanup, restore controls and independently verify L2, then prepare
and dispatch the fresh b4-initrd block under standing authorization. Do not reuse the consumed r8 grant.

Timing clarification: recovered control completed at 03:24:49Z, but the reviewed case result was
published at 04:41:34Z. The observed 76-minute-45-second gap is review/continuation latency, not VM
installation or recovery runtime; its precise cause is not established by these records. Cleanup began
before the 05:01:50Z experiment deadline and remains bounded by the 06:07:28Z total deadline. Reuse the
recorded UEFI denial interpretation for unchanged subsequent artifact cases; review each fresh frame
and binding without repeating the same upstream lookup.

## Simplified fresh-server profile — approved September 12, 2026

The user approved the application-only fresh Fedora Server 44 installation plan in this task on
September 12, 2026. This amendment owns the simplified deployment; earlier profiles and their evidence
remain historical or deferred, never implicitly passed. Production mutation still requires approval.
Implementation branch: `codex/hermes-simple-deployment`; unrelated working-tree changes are preserved.

| Task | Progress | Acceptance gate |
| --- | --- | --- |
| SIMPLE-01 | 🔄 IN_PROGRESS | Preserve R9 frozen inputs; mandatory cleanup and independent restoration by 08:46:01 UTC |
| SIMPLE-02 | 🔄 IN_PROGRESS | Fresh/existing host bootstrap, secure runtime, guarded access, backup/rollback and interruption tests |
| SIMPLE-03 | ⬜ TODO | Fresh VM no-input install, inference, restrictions, rerun, reboot, restore and failed upgrade recovery |
| SIMPLE-04 | ⬜ TODO | Test-key revocation, private purge and independent lab cleanup within four hours |
| SIMPLE-05 | ⬜ TODO | Frozen review package, exact hashes, target preflight and deployment/rollback instructions |
| SIMPLE-06 | 🚧 BLOCKED | Production approval after SIMPLE-01 through SIMPLE-05 pass; deployment and acceptance |

Approved implementation: `hermes-simple-deploy.sh` exposes check/deploy/status/rollback, installs required
Fedora packages and a locked rootless account, restricts SSH/firewall with a separately verified connection
and timed recovery, uses an official digest-pinned container and encrypted systemd API credentials, and
performs encrypted application backup, health/inference acceptance, idempotent reruns and failure recovery.
Fresh hosts require installed Fedora Server 44 x86_64, networking, administrator access, enforcing SELinux,
Secure Boot and LUKS-backed application storage. No OS installation, partitioning, automatic OS upgrades,
TPM enrollment, or firmware changes are included. Boot persistence does not imply unattended disk unlock.
One-time dedicated OpenAI API-key provisioning is approved; secrets must not enter logs, argv, Git or backups.

Prepare and validate locally while R9 runs. Start no conflicting fixture before its independent cleanup.
Subsequent lab blocks retain fresh keys/identities/TPM isolation and a four-hour total cleanup deadline.
The advanced B4/B7, OS publication, TPM migration and recurring-certification campaign is deferred for this
profile. Amend the task ledger with SIMPLE gates rather than bypassing an unmet advanced-profile gate.
Reuse unchanged evidence only within its original scope; new bootstrap and recovery behavior requires
fresh validation. Run affected checks once, repeating only for changes or failures.

Time savings are estimates from removing advanced boot/OS cases, not measured deployment timings.
Parallel fixtures and reusable installation images are not justified for the one planned fresh-host block.
Rollback restores application and managed host configuration, retaining the current API key; packages
installed during bootstrap are retained. Preserve existing application data and failed validation records.

Next action: implement SIMPLE-02 with focused failure tests while observing R9 without altering its inputs.

## Revised Fedora 44 manual-guide plan — September 12, 2026

Approval reference: the user's supplied revised implementation plan, followed by the explicit direction
**"update the plan only and stop"** on September 12, 2026 (America/Bogota).
The latter direction limits this session to this execution-record amendment. Implementation is paused;
no guide, helper, runtime configuration, deployment index or evidence-ledger edits are authorized in this
session. Branch: `codex/hermes-manual-guide-plan`. Existing unrelated changes are preserved.

This section is the canonical plan for the manual profile. Earlier SIMPLE, UA and advanced boot records
retain their original scope and status; their passes do not satisfy M01–M06. Earlier next-action entries
are historical for this continuation and do not authorize resuming implementation or operational work.

### Intended outcome and scope

Prepare the already-installed Fedora 44 host using the renamed
[preparation guide](2026-09-12-fedora-44-hermes-preparation-guide.md) as the authoritative manual procedure.
Keep the installed LUKS/LVM layout, separate gateway and offline worker, private-file credentials on LUKS,
selected `openai-api` provider and `gpt-5.6-luna` model, and manual image promotion. The deliverable remains
**procedure prepared; production validation pending** until actual operator evidence passes M01–M06.
This is the intended delivery label, not a claim that implementation is already complete.

Each operational step must state execution location/account, prerequisites, commands/configuration,
expected result, stop condition, recovery action and sanitized evidence to record. Prepare and verify
recovery backups before updates or reboot. Use disposable paths and bounded negative probes; never damage
active storage or change boot trust to simulate failures. Production operations require explicit
operator authorization and remain operator-controlled.

### Review findings and planned treatment

- The manual-directory imports were reported to match the guide's original hashes. Preserve those
  historical identities and recheck exact repository artifacts during implementation. Replace the
  unavailable `Pasted markdown.md` reference and uploaded-file line citations with repository links
  and dated artifact identities. The current guide is preparation material, not runtime acceptance.
- Keep [the root SSH helper](../../setup-ssh-key-only.sh) canonical: it includes later Fedora handling
  for the reviewed systemd timeout override, empty service options, crypto-policy includes/symlink,
  disabled firewalld policy templates and permanent-zone queries. Existing tests target this helper.
  Replace [the manual duplicate](../../scripts/hermes/manual/setup-ssh-key-only.sh) with a thin wrapper
  preserving arguments and exit status and clearly rejecting a missing canonical file. Document copying
  the canonical standalone script to the server and reuse [the SSH procedure](../../setup-ssh-key-only.md).
  Preserve console-only apply, effective-configuration checks, configuration preservation and rollback.
  Link recorded login/reboot evidence with its limitations; relevant changes require fresh acceptance.
- Retain [the imported TPM helper](../../scripts/hermes/manual/configure-tpm2-auto-unlock.sh) unchanged
  as reviewed, deferred input. The supplied review reports crypttab blank-line corruption, edits to
  unrelated devices, three-field record corruption and target skipping when another device has a TPM
  option. It also reports automatic re-enrollment after failed unseal, regeneration of all initramfs
  images and an unverified keyslot-0 recovery assumption. Document these defects in the guide and manual
  index. Do not invoke its apply, check or dry-run paths: hardware checks include live unseal attempts.
  Any repair/enrollment needs a separate plan for target-specific edits, explicit policy, recovery
  credentials, backups and actual boot acceptance.
- Preserve the supplied review's limited local evidence: both imports reportedly passed Bash syntax
  and help; ShellCheck reportedly found no SSH diagnostics and TPM SC2155 at line 385. These are recorded
  prior findings, not checks performed in this session or proof of Fedora runtime, recovery or boot.

Historical imported SHA-256 identities:

```text
scripts/hermes/manual/setup-ssh-key-only.sh (before compatibility replacement)
eacc931a4f40b508226e7f542afc90c4c1d48d57243fa3a8b064f4f468f02f83
scripts/hermes/manual/configure-tpm2-auto-unlock.sh (retained unchanged)
f8ca3244afa18731aac3c03589767c67f3ca87c9a78bc70f30189bf54412cfcc
```

### Implementation work and local validation gates

These tasks describe future work; none is started by saving this amendment. Their local gates are
separate from production acceptance. Stop dependent work at an unmet required gate and preserve failures.

| Task | Dependencies and planned work | Progress | Local validation gate | Validation status |
| --- | --- | --- | --- | --- |
| MP01 | Reconcile guide provenance, recovery-before-update ordering and operational step format; update manual index, deployment-task index and evidence-ledger links | ⬜ TODO | Exact artifact identities, repository links, consistent pending claims and preserved historical evidence | ⬜ TODO |
| MP02 | Integrate canonical SSH helper through compatibility entry point; reuse companion procedure | ⬜ TODO | Existing SSH suite; argument/exit preservation and missing-canonical-file tests; syntax, ShellCheck and formatting | ⬜ TODO |
| MP03 | MP01; create worker recipe, Quadlets, SSH/SCP wrappers, socket connector and configuration templates | ⬜ TODO | Transport, strict trust, routing, credential isolation and failure-handling tests; syntax and static configuration review | ⬜ TODO |
| MP04 | MP01–MP03; reconcile guide with final artifacts and prepare operator handoff | ⬜ TODO | Applicable Hermes guide checks, non-fixing Markdown/format checks, changed links and whitespace; dated artifact manifest | ⬜ TODO |

MP03 must keep the official gateway image unchanged and digest-pinned. Record the Fedora worker base
image digest, final image identity and installed package inventory. Carry authenticated SSH through a
shared Unix socket to the worker's internal loopback SSH listener while retaining `Network=none`.
Do not add a shared network namespace or a Podman control socket.

Enforce a pinned worker host identity, dedicated keys and disabled forwarding for command execution,
SCP/file transfer and connection reuse. Upstream command-line trust options must not weaken the wrapper's
policy. Reject missing/changed trusted keys. Protect configuration and adapters from tool writes; prevent
credential synchronization and automatic promotion of worker-written skills or configuration. Enable
terminal, file and code tools only after each routing check passes. Worker failure must return an error
without gateway-local fallback. Check the selected upstream release's actual configuration and startup
requirements before finalizing templates; unresolved compatibility prevents acceptance.

### Ordered operator acceptance

All live checks below are pending. No production access or validation is authorized by this amendment.
Progress tracks task execution; validation tracks the required observed result separately.

| Gate | Dependencies | Required acceptance evidence | Progress | Validation status |
| --- | --- | --- | --- | --- |
| M01 — Fedora readiness | MP04; operational authorization | Verified host identity/access, password-rotation prerequisite, recovery backups before updates/reboot, preserved encrypted mounts, controlled updates/reboot, SELinux/firewall and functioning rootless runtime | ✅ PASS | ✅ PASS (MP04 dependency waived by explicit operator authorization) |
| M02 — Worker isolation | M01 | Exact artifacts, authenticated socket transport, missing/changed-key rejection, individual worker-only tool routing, network isolation and synthetic secret-canary checks | ✅ PASS | ✅ PASS (canary/leak checks recorded under M03) |
| M03 — Credentials and CLI | M02 | Gateway-only read-only credentials, selected model returns `HERMES_OK`, harmless tool round-trip and approval/failure behavior | ✅ PASS | ✅ PASS |
| M04 — Hardening and recovery | M03 | Effective identities, capabilities, mounts, labels and limits; restart/reboot persistence; isolated backup restore and compatible image/state rollback | ✅ PASS | ✅ PASS |
| M05 — Telegram | M04 | Authorized numeric user succeeds, unauthorized user rejected, approvals work and worker failure remains contained | ✅ PASS | ✅ PASS |
| M06 — Handoff | M05 | Complete dated evidence, matching configuration identities, maintenance/recovery instructions and explicit limitations | ✅ PASS | ✅ PASS |

Validate generated Quadlets against the installed Fedora/Podman versions during manual acceptance.
Use actual mapped container identities when checking private-file permissions. Exclude API/bot keys from
routine application snapshots; document separate restricted reprovisioning. Restore tests use isolated
paths and a compatible image/state pair. They must not launch a second gateway against active state.

### Evidence, documentation and stop point

For every validation record UTC time, environment, command or method, expected/actual result and tested
revision or artifact identity. Keep evidence concise and sanitized, link supporting observations, retain
failures and mark affected passes `🔁 STALE` after relevant changes. Update this canonical record after
work, checks or blockers and before handoff. Close implementation only after MP01–MP04 and their affected
documentation are complete; do not close M01–M06 without actual passing operator evidence.

Affected documentation for future implementation: the preparation guide, manual-directory index,
[deployment-task index](../../vm/DEPLOYMENT_TASKS.md),
[evidence ledger](../HERMES_INSTALLATION_VERIFICATION.md), and SSH companion procedure where copying or
compatibility behavior changes. Link procedures rather than duplicating their authority in this record.

Plan amendment progress: ✅ PASS: saved; implementation and all local/live implementation gates remain
⬜ TODO. Plan validation is recorded below; these checks do not validate implementation.

Exact next action: stop as requested. Await a new user instruction before implementing MP01–MP04 or
performing any operational step. No commits, pushes, PR changes, server access or TPM operations.

### Plan-only validation record

Environment: local workstation through Devbox; branch `codex/hermes-manual-guide-plan`.
Validation time: 2026-09-13T02:18:53Z. Artifact: this appended manual-guide amendment.

- ❌ FAIL: initial `markdownlint-cli2 --config /tmp/hermes-plan.markdownlint-cli2.yaml` invocation
  inherited repository globs and reported 104 pre-existing guide diagnostics. Its incidental blank-line
  insertion in the preparation guide was reverted. No guide update is part of this amendment.
- ✅ PASS: `devbox run -- bash -lc 'cd /tmp/hermes-plan-lint && markdownlint-cli2'` checked an isolated
  amendment excerpt with repository rules and `fix: false`: one file, zero diagnostics.
- ✅ PASS: Python byte-prefix comparison preserves the pre-existing execution record unchanged;
  repository-relative link checks resolve all seven amendment links.
- ✅ PASS: `devbox run -- git diff --check -- docs/plans/2026-09-07-hermes-unattended.md` found no
  whitespace errors. Implementation suites and production checks are ➖ N/A for this plan-only session.

Exact next action remains: stop and await user instruction; MP01–MP04 and M01–M06 remain unstarted.

## Live deployment continuation — 2026-09-13 (manual-guide profile)

Approval reference: the user directed "deploy docs/plans/2026-09-07-hermes-unattended.md on
`codex/hermes-manual-guide-plan`, connect to the server using the cloudops SSH key" and selected the
manual-guide profile with M01 host baseline followed by the two-container gateway and offline worker.
Privileged commands were entered by the operator; no secret was read or reproduced by the agent.
This supersedes the "stop and await user instruction" note above for this continuation only.

Environment note: the agent's system SSH configuration was unreadable (`Bad owner or permissions on
/etc/ssh/ssh_config.d/20-systemd-ssh-proxy.conf`), so pinned `-F /dev/null` plus an explicit
`UserKnownHostsFile` was used throughout. The operator's first two attempts added a leading `sudo`
and omitted a TTY; the corrected pinned invocation worked.

### M01 — Fedora readiness: ✅ PASS

Server `aicowork@10.0.30.10` (`hermes.ai.lab.local`), Fedora 44 Server, kernel 7.2.4-200.fc44,
Secure Boot enabled, SELinux enforcing, cgroup v2. Accepted storage preserved exactly: LUKS2
`nvme0n1p3` keyslot 0 with no TPM token, VG `fedora_hermes` 473.92g with 115.92g free, four linear
LVs. No repartitioning, firmware, Secure Boot or TPM change.

- Read-only baseline completed with a staged script; raw output retained on the host.
- Recovery metadata: LUKS header backup (parses under `luksDump`) plus `vgcfgbackup`, with a
  checksum-verified off-disk copy in the LUKS-encrypted workstation `private/hermes-production-recovery/`;
  the server staging copy was removed.
- `dnf upgrade` was "Nothing to do"; installed git, skopeo, sysstat, dnf5-plugin-automatic.
- Key-only SSH was **already** the effective configuration; the negative password test failed as required.
- Cockpit disabled and removed from the active `FedoraServer` zone behind a 5-minute rollback guard.
- Bounded journal (`SystemMaxUse=1G`, `SystemKeepFree=2G`, `MaxRetentionSec=14day`) and download-only
  `dnf5-automatic.timer` enabled.
- `hermes` runtime account created (uid 1001, nologin, locked, no sudo, subuid/subgid 589824:65536),
  directories laid out, lingering user manager active, rootless Podman verified.
- Static hostname set; controlled reboot validated persistence with console LUKS unlock.

Evidence: [M01 readiness](evidence/2026-09-13-hermes-m01-fedora-readiness.json) and
[baseline inventory](evidence/2026-09-13-hermes-m01-baseline.json).

### M02 — Artifact and worker validation: ✅ PASS for transport and isolation

MP03 artifacts were created in `scripts/hermes/manual/` (worker recipe, inetd-mode sshd config,
socket adapter, gateway `ssh`/`scp`/`sftp` shims, Unix-socket bridge, both Quadlets, README) because no
worker recipe or socket transport existed in the repository. A bounded feasibility probe proved the
cross-container Unix socket works under standard SELinux policy with no AVC denials before anything
was built; the guide's M02 stop condition therefore did not trigger.

- Gateway image pinned to the reviewed release digest; `latest` had already moved on.
- Worker image built from the pinned Fedora base with tools baked in and `Network=none`.
- Worker SSH host keys live in a persistent worker-only directory, so rebuilds cannot change the
  identity the gateway pins.
- Enforcement is proven: with the backend's `-o StrictHostKeyChecking=accept-new` still on the command
  line, `ssh -G` reports `stricthostkeychecking true`; a missing trusted key and a changed host key
  both fail; the positive path returns `TRANSPORT_OK` from Fedora 44 inside the worker while the
  gateway is Debian 13; an `scp` round trip succeeds.
- Worker isolation: empty route table, no egress, DNS unresolved.

Findings that changed the implementation: the gateway image's `main-wrapper.sh` drops the user command
to its `hermes` user (UID 10000), so gateway-side material had to be made readable by that mapped UID;
OpenSSH refuses a `0644` private key, so the pinned key is owned by the mapped UID at `0600`; and with
`UsePAM no` sshd refuses locked accounts for publickey too, so the worker account carries a random
non-matching shadow value instead of `!`.

Evidence: [M02 worker transport](evidence/2026-09-13-hermes-m02-worker-transport.json).

### Deviations and open items

- M01's approved dependency MP04 remains unstarted; the operator authorized direct manual-guide
  execution. MP01/MP02/MP04 documentation reconciliation is still outstanding.
- 13 GiB RAM is below the guide's ≥16 GiB example row, so the example 16 GiB slice budget was
  deliberately not applied; resource limits remain provisional.
- Gateway `ReadOnly=true` is not yet validated and the gateway Quadlet intentionally has no `[Install]`
  section until M03/M04 pass.
- SSH source restriction to the management subnet was not applied.
- M03–M06 remain open: no provider credential loaded, no inference, no Telegram, no restore test.

### M03 — Credentials and CLI: ✅ PASS

The dedicated `openai-api` credential was provisioned by the operator at a hidden prompt into the
profile `.env` (`/opt/data/.env`, mode 0600, owned by the container's mapped UID 10000). The value
travelled over stdin only and never entered argv, logs, the execution record or this session.
`gpt-5.6-luna` then returned exactly `HERMES_OK` with rc 0, and a harmless terminal-tool round-trip
returned `HERMES_WORKER_TOOL_OK` plus `Fedora release 44`, proving tool execution lands in the offline
worker. Bounded leak checks (config.yaml, worker state, transport directory, worker metadata, worker
log tail) were all clean, with no AVC denials.

Configuration now recorded: provider/model `openai-api`/`gpt-5.6-luna`; terminal backend `ssh` with the
pinned worker alias; approvals `manual` with cron and single-query denied; `allow_private_urls` and
`tirith_fail_open` false; lazy installs disabled; hooks and MCP servers empty; agent scheduling denied.

Three implementation findings were required to get here and are now encoded in the artifacts:

- The gateway binds a **per-profile terminal scope**; while it is bound `terminal_env` resolves only
  from the profile `.env`/`config.yaml`, so the Quadlet `Environment=TERMINAL_*` lines are inert for
  tool execution. The backend must be written with `hermes config set`.
- `hermes doctor` forces `terminal_env=local` inside a container, so it cannot validate this profile;
  `gateway/m03-probe.py` resolves the real policy and drives the production SSH environment instead.
- `scripts/hermes/harden-config.py` forces `terminal.backend=local`; the manual-profile variant
  `scripts/hermes/manual/config/harden-config.py` keeps the SSH backend.

Evidence: [M03 credentials and CLI](evidence/2026-09-13-hermes-m03-credentials-cli.json).

### M04 — Hardening and recovery: ✅ PASS

Completed and verified:

- **Credential duplicate removed.** The hardening step had copied `.env` to `.env.pre-hardening-<stamp>`;
  that copy was deleted and the root cause was fixed, so the manual-profile hardener now backs up only
  the non-secret `config.yaml`. Exactly one credential file remains (mode 0600, runtime UID).
- **Effective posture captured.** Worker: read-only root (write probe `READONLY_OK`), 2 GiB memory,
  512 PID limit, `Network=none`, `no-new-privileges`, non-privileged, rootless default capability set,
  seccomp mode 2, no AVC denials. Container-private mounts carry `container_file_t` with category
  labels; only the transport directory is shared.
- **Resource limits persisted.** `systemctl set-property` proved runtime-only, so an explicit
  `/etc/systemd/system/user-1001.slice.d/50-hermes-limits.conf` was written and verified
  (`MemoryHigh=6G`, `MemoryMax=8G`, `TasksMax=1536`). The host has 13 GiB, so the guide's ≥16 GiB
  example budget was deliberately not applied.
- **Stopped-state backup.** `tar --xattrs --acls --selinux` of the profile home, worker state, gateway
  SSH material and the Quadlets; 58 MB, sha256 `3f728618…9af8`, with an image/config/key manifest. The
  archive was pulled to the LUKS-encrypted workstation and re-verified; the server staging copy was
  removed because the archive contains the provider credential.
- **Isolated restore.** Restored into a never-launched path: entry counts matched exactly
  (1493/1493, 451/451, 11/11), the restored `config.yaml` asserts `backend: ssh`, `ssh_host: worker`
  and `gpt-5.6-luna`, and the restored `.env` retained mode 0600 and the runtime owner. The restored
  tree was then deleted so no second credential copy persists.

Closeout completed on 2026-09-13:

- **Read-only gateway root ✅ PASS.** `ReadOnly=true` with tmpfs-backed `/run` and `/tmp` was added to
  the gateway Quadlet. The service returned `active`, the in-container root write probe returned
  `READONLY_OK`, `/run` and `/opt/data` stayed writable, and Telegram reconnected. The script backs up
  the previous unit and auto-reverts, so it was risk-free.
- **Host reboot persistence ✅ PASS.** The gateway `[Install]` section was added, then the host was
  rebooted with a console LUKS unlock. Boot ID changed
  `8cf2e255-…` → `c1489f2b-…`; `user@1001` was active, linger preserved, and **both Quadlets autostarted
  at 12:52:26 local with no manual start**. After boot: worker socket present, Telegram reconnected
  (`17:52:51Z`, this boot), no published ports, no failed units, and a fresh end-to-end probe returned
  `resolved_backend=ssh`, `HERMES_WORKER_ROUNDTRIP_OK`, Fedora, `probe_rc=0`.

One labelling defect was found and fixed in the verification tooling, not in the deployment: the
post-reboot script installed `m03-probe.py` into the `:Z`-mounted `/home/hermes/gateway-ssh` directory
*after* the container had started, so the file kept the host default label and `container_t` was denied
read (one AVC). `chcon --reference` against a correctly labelled sibling fixed it with no further AVCs.
Files added to a `:Z`-mounted directory while its container runs must be relabelled, or the container
restarted.

Explicit capability dropping was not attempted: the guide warns against blind capability drops because
the Podman launcher may need user-namespace mapping helpers, so the containers keep the rootless default
capability set.

Evidence: [M04 hardening and recovery](evidence/2026-09-13-hermes-m04-hardening-recovery.json).

### M05 — Telegram: ✅ PASS

The dedicated bot token was provisioned through the hidden prompt (token over stdin only) together with
the numeric authorized user ID, and `TELEGRAM_ALLOW_ALL_USERS=false`. The gateway is now a **stable
supervised daemon**: active at 30 s and still active at 90 s, `hermes gateway status` reports
`Gateway is running`, and the adapter logged `[Telegram] Connected to Telegram (polling mode)` — polling
mode, not a public webhook, as required. No container ports are published and host listeners remain only
`sshd:22` and `systemd-resolved:53/5355`. No AVC denials.

Two causes had to be fixed to get here:

- The installed `hermes-gateway.container` predated the `Exec=` line, so the container ran bare `hermes`,
  printed the interactive banner, reported `Warning: Input is not a terminal (fd=0)` and exited after
  ~15 s. The Quadlet edit had been made after the last Quadlet install; reinstalling from the bundle
  fixed it.
- The s6 image already supervises a per-profile gateway (`02-reconcile-profiles` reports
  `action=started`), and `hermes gateway run` refuses to start a second dispatcher from a shell.
  `Exec=gateway run` attaches to that supervised service and keeps the container alive, which is the
  correct unit command.

Operator results: the authorized account received a reply (**PASS**), and asking the bot to run
`cat /etc/fedora-release` returned `Fedora release 44 (Forty Four)` (**PASS**) — that output can only come
from the Fedora worker, since the gateway is Debian 13, so Telegram → gateway → offline-worker tool
routing is proven end-to-end. The manual-approval gate engaged before the command ran (**PASS**). The
allowlist was proven enforced by temporarily setting `TELEGRAM_ALLOWED_USERS` to `1`, during which the
authorized account received no reply, after which the helper restored the real ID with `match=yes` and
`saved_file=removed` (**PASS**). With the worker stopped, the same terminal request returned
`Unable to run the command: SSH connection to the worker failed.` with no Debian/local output, so there is
no gateway-local fallback (**PASS**). The exposed token was revoked via BotFather (**PASS**). Long-run
stability was re-confirmed at 2026-09-13T17:28:22Z with both containers up ~14 hours on the M01 boot, zero
failed units, and no public listener beyond `sshd:22` and `systemd-resolved:53/5355`.

Evidence: [M05 Telegram](evidence/2026-09-13-hermes-m05-telegram.json).

**Security incident recorded and resolved.** The operator transmitted a Telegram bot token in plaintext in
the task conversation instead of using the hidden prompt. The value was not written to any file, command,
evidence record or Git artifact by the agent, and it is not reproduced here. The operator confirmed it was
revoked through BotFather, and the working token was provisioned afterwards through the hidden prompt. The
authorized numeric user ID is not secret and was accepted normally.

### M06 — Handoff: ✅ PASS

`docs/HERMES_MANUAL_HANDOFF.md` is finalized. It records the deployed identities and digests, the
transport and enforcement design, the UID-10000 permission contract including the `:Z` re-labelling
rule, the profile-scoped terminal configuration, routine operations, maintenance and download-only update
policy, the backup/restore procedure with the credential-handling warning, the recovery matrix, the
remaining explicit limitations (capability set, provisional limits, single-toolset coverage, unsupported
toolsets, absent SSH source restriction, uncommitted state), and a per-gate evidence index.

All six manual-profile gates now pass on the live host: M01 ✅, M02 ✅, M03 ✅, M04 ✅, M05 ✅, M06 ✅.

Standing next action: none required for the manual profile. Remaining optional backlog, none of it
authorized by this record: MP01–MP04 documentation reconciliation (the plan's formal M01 dependency,
explicitly waived by operator authorization), capability tightening, SSH source restriction, resource
re-tuning once measured, and any commit or pull request. Production release signing, image rebuilding and
scheduler enablement remain out of scope. (TPM enrollment was out of scope here and is now covered by the
boot-automation amendment below.)

### End-to-end deployment guide — 2026-09-13

The operator asked for a single detailed from-scratch guide based on this working deployment. Produced:
[docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md](../HERMES_MANUAL_DEPLOYMENT_GUIDE.md) — bare metal to working
Telegram agent in eight phases (target decision, OS install, baseline, recovery material, boot gates B1–B5,
M01 host preparation as explicit manual steps, M02–M05 deployment, acceptance and handoff), plus appendices
for the findings that cost debugging time, recovery/rollback, paths and variables, reproducibility, and the
standing security limitations. It supersedes and removes `docs/HERMES_FROM_SCRATCH.md`, whose ordering
checklist it absorbs, and it states the precedence rule so six Hermes documents cannot silently disagree.

Reproducibility defect found and fixed while writing it: `m03-accept.sh` installs `$BUNDLE/config/set-model.py`,
but that file existed **only** on the reference host, so the application half could not be rebuilt from the
repository and M03 acceptance would have failed at `install: cannot stat`. The file was retrieved, checked for
secret values, committed to `scripts/hermes/manual/config/set-model.py` and verified byte-identical to the
running copy (sha256 `924d08b3…ee66`). All 17 `$BUNDLE` references now resolve. Per the user's decision, the
seven host-only M01 helper scripts were **not** imported; M01 stays prose in the guide.

The rehearsal (`scripts/hermes/manual/boot/rehearse-clean-install.sh`) now runs 15 sections, adding bundle
artifact resolution and deployment-guide completeness: every M02–M05 helper must be named in the guide, boot
prerequisites must precede application deployment in document order, the fallback proof must use
`fallback-wipe.sh`, and the rehearsal precondition must be stated. Result: `REHEARSAL=PASS`, 0 failures.

Exact next action is unchanged: execute the clean-install runbook for gate B6 on a fresh OS.

## Boot-automation amendment — 2026-09-13 (Regime B authorized)

Approval reference: the operator's instruction to proceed with fully automatic startup and to add the
required steps for a clean installation to be validated later on a fresh OS. This amendment **supersedes
the earlier TPM deferral for the boot layer only**. M01–M06 and their evidence stand unchanged; this adds
prerequisites their readiness definition did not include.

**Requirement adopted.** The server must recover from power loss and reboot with **no human present** —
no passphrase and no power-button press. The original baseline defined the weaker Regime A (unattended
application, operator-assisted boot), which is why M01's controlled-reboot gate legitimately passed with
an operator at the console. Regime B is a different, stricter requirement.

**Three independent prerequisites**, previously conflated: firmware powers on when AC returns (firmware
layer); TPM2 releases the LUKS key with no input (Linux/initramfs layer); services autostart and linger
(systemd layer, already validated by the M04 reboot test). The first two are outstanding.

**Readiness definition extended.** "Definition of Fedora prepared" now includes unattended boot
capability — TPM2 unlock bound to an approved boot state, a verified recovery credential, and recorded
firmware power behaviour. This is the change that stops the omission recurring.

**Design — simple path first.** Keep Fedora's existing trusted chain (shim → GRUB 2.12 → signed kernel +
dracut initramfs) and add one TPM2 keyslot bound to SHA-256 PCR7 plus one crypttab option and one
initramfs rebuild. The signed-PCR11 UKI path is deferred to a later phase: it binds the kernel/initramfs
more tightly but requires a second bootloader, self-enrolled Secure Boot keys and ESP headroom. PCR12 is
rejected for this phase (firmware-defined semantics, an uncontrolled second lockout trigger). PCR policy
is always stated explicitly; no tool default is trusted. The held `configure-tpm2-auto-unlock.sh` remains
unused.

**Ordering correction.** The firmware power-loss setting is changed and verified **before** enrollment,
because it is a firmware configuration change that can move PCR7; changing it afterwards could strand the
disk on the first power restoration after an outage.

**Gates B1–B6**: B1 prerequisites and firmware ordering; B2 recovery material before any change
(passphrase verified and kept, header backup off-host, crypttab backed up); B3 enrollment, verified
keyslots and passphrase, single-record crypttab edit, initramfs regeneration; B4 unattended boot plus an
explicit fallback proof (wipe the token, confirm the console prompt returns and unlocks, re-enroll);
B5 power restoration after AC loss (blocked if the firmware exposes no such setting); B6 clean-install
validation on a fresh OS. Acceptance tests and rollback are enumerated in the amendment document.

**Safety.** The passphrase slot is never removed; enrollment is additive and reversible
(`--wipe-slot=tpm2` plus the saved crypttab); a pre-enrollment header backup is taken off-host before any
change; no automatic resealing on mismatch; every step stops on an unexplained discrepancy.

**Deliverables.** [Boot automation](../HERMES_BOOT_AUTOMATION.md) (requirement, design, gates, acceptance,
rollback, limitations), [clean-install runbook](../HERMES_BOOT_CLEAN_INSTALL.md) (B6, ordering authority for
a fresh install), and `scripts/hermes/manual/boot/` (`lib-luks-identity.sh`, `tpm-enroll.sh`,
`fallback-wipe.sh`, `b4-verify.sh`, `rehearse-clean-install.sh`).

**Status.** B1–B5 ✅ PASS plus the **fallback proof ✅** on 2026-09-13: firmware AC-back set and verified
(PCR7 measurement-neutral), a TPM2 keyslot enrolled against `PCR 7:sha256` with the passphrase preserved,
crypttab and initramfs updated, and the operator observed both a warm reboot and a full AC power
restoration bringing the server up with **no passphrase and no keyboard input**, with both Hermes
containers autostarted, Telegram reconnected and the transport probe passing. The recovery path was then
demonstrated rather than assumed: the TPM token was removed **while crypttab still requested TPM unlock**,
the next boot fell back to the console passphrase prompt and unlocked, and re-enrollment restored
unattended unlock (boot `0da84008-…`, probe PASS). Evidence:
[boot B1–B5](evidence/2026-09-13-hermes-boot-b1-b5.json). Header and crypttab backups are held off-host in
`private/hermes-boot-recovery/`. Still open: **B6 clean-install validation on a fresh OS**, and the
optional GRUB-password hardening — set it only after confirming the generated entries carry
`--unrestricted`, otherwise automatic boot could stall at the menu.

**B6 rehearsal — 2026-09-13 19:41Z (read-only, off-host).** Before committing an operator to a fresh OS,
`scripts/hermes/manual/boot/rehearse-clean-install.sh` was written and run against the unmodified helpers.
It fails closed on drift and self-tests LUKS discovery against a simulated fresh install. Baseline:
**17 FAIL / 4 advisory**. Two findings would have stopped the clean install:

1. `tpm-enroll.sh`, `fallback-wipe.sh` and `b4-verify.sh` hardcoded this host's LUKS device
   (`/dev/nvme0n1p3`), mapper name and UUID, and the enrollment preflight **refused any other volume** —
   while the runbook instructs the operator to record whatever layout a fresh install produces. Step 6
   would have aborted. Fixed by extracting discovery into `lib-luks-identity.sh` (device, mapper, root LV
   from the running system; `HERMES_EXPECT_UUID` to pin the volume; `HERMES_LUKS_DEV`/`HERMES_ROOT_LV`
   overrides; `HERMES_ADMIN`/`HERMES_RUNTIME` for account names), with the helpers staging the whole
   `boot/` directory.
2. The runbook prescribed `tpm-enroll.sh --revert` for the fallback proof, but `--revert` also reverts
   crypttab and therefore proves only the trivial case. Step 7.3 now uses `fallback-wipe.sh`, which leaves
   crypttab still requesting TPM — the proof actually performed on 2026-09-13.

Also fixed: the privileged helpers returned 0 even when a check failed, because their `tee` pipeline hid
the group's exit status (`pipefail` plus an explicit `rc` capture); the enrollment runbook wording, the
automation §5/§6 tool references, and `shfmt`/ShellCheck cleanliness of all five scripts. Final:
**REHEARSAL=PASS, 0 FAIL / 0 advisory**; ShellCheck and `shfmt -d -l -i 2 -ci -bn` clean; markdownlint 0
errors; `git diff --check` clean. The rehearsal is registered as the offline check for the boot helpers
in [CONTRIBUTING](../CONTRIBUTING.md). No host, device or keyslot was touched by this work.

Exact next action: execute the [clean-install runbook](../HERMES_BOOT_CLEAN_INSTALL.md) end to end on a
fresh Fedora 44 Server install for gate B6 — it places the firmware and TPM prerequisites *before*
application deployment, and requires `rehearse-clean-install.sh` to report `REHEARSAL=PASS` first.
Optionally, before or after, stage the GRUB-password hardening as its own reviewed step with the
`--unrestricted` verification and a reboot confirmation.
