# Hermes unattended release deployment

Current production boot procedure: [standard TPM2 dependency review and migration](HERMES_TPM_DEPENDENCY_REVIEW.md).
The 2026-09-10 amendment precedes further NvPCR/SELinux expansion; SE22 metadata review is complete and its
service invocation is consumed. Existing trial handoffs below are historical and do not authorize new actions.
The conditional profile retains SRK setup, signed PCR11, all runtime/security controls and recovery state;
both requested privileged inventories are received and AR01 bounded consumer review passes. Do not repeat
either collector. The user approved the single AR04-L0/L1/L2 lab campaign; its
[live observation](plans/evidence/2026-09-10-hermes-standard-tpm2-live.json) tracks actual results and restoration.
The first run failed baseline archive validation and cleanup/restoration passed. The corrected
[r2 package](HERMES_TPM_DEPENDENCY_REVIEW.md#corrected-integration-package-r2) received its own
approval and is now consumed: preparation passed, certification failed, and cleanup/restoration passed.
Its [live observation](plans/evidence/2026-09-10-hermes-standard-tpm2-r2-live.json) records the child tool-path defect
and prepared [r3 package](HERMES_TPM_DEPENDENCY_REVIEW.md#certifier-tool-configuration-package-r3).
R3 received separate approval and completed successfully on September 11 UTC: all seven existing certifier
gates passed; L2 and independent restoration passed at 03:01:21Z. Its
[live observation](plans/evidence/2026-09-11-hermes-standard-tpm2-r3-live.json) records the consumed grant and removed access.
Full amended lab certification and production gates remain open.

Implementation and validation are tracked in the
[approved execution record](plans/2026-09-07-hermes-unattended.md).
This is a separate enrolled protocol; the interactive controller and its historical certification
remain available. Neither historical promotion records nor offline test results authorize this profile.

## Readiness

The profile is not production-certified. Do not install or enable the supplied service templates on
production until the ordered unattended gates in [the task ledger](../vm/DEPLOYMENT_TASKS.md) pass.
Production enrollment remains disabled. Earlier disposable runs were cleaned up; the September 10 campaign
has its own explicit grant and mandatory cleanup, recorded separately in the live observation.
Example configurations intentionally fail validation.

The [2026-09-08 UA-03 certification](plans/evidence/2026-09-08-hermes-ua03-certification.json) passed
exact package replay, update/persistence/cold boots, runtime, real inference, encrypted semantic restore,
negative/rerun checks, advisory scanning and test-key revocation.
[UA-04 cleanup and signing](plans/evidence/2026-09-08-hermes-ua04-cleanup-signing.json) also passed:
the guest data, disposable backups/keys, VM, recovery disks, firmware and TPM state are removed.
The isolated signer issued the exact release, independently verified with all nine gates and 356 files.
It remains bound to the tested lab host; UA-05 production enrollment is still required.
Candidate scheduling for an enrolled recipe passed
[live scheduler validation](plans/evidence/2026-09-08-hermes-scheduler-live.json), including service execution,
failure reconciliation, completed-run behavior and dedicated-fixture cleanup. This run used an approved
expiring lab window exception; Sunday timer behavior was validated offline. No new release was signed.
The U06 fresh-fixture lifecycle now has repository implementation and offline regression coverage.
Live repeating provisioning, exact per-run enrollment and cleanup remain unvalidated; the complete
repeating release workflow is not yet ready. See [automatic fixture lifecycle](#automatic-fixture-lifecycle).

The original severity-based policy rejected both scanned images. The
[scan observation](plans/evidence/2026-09-07-hermes-image-scan.json) records 20 critical and 463 high
package findings, plus 191 unknown-severity findings.
The [newer upstream candidate scan](plans/evidence/2026-09-07-hermes-candidate-scan.json) records
19 critical and 379 high package findings remain. No fixed version is listed for 18 of its 19 critical
findings. The candidate was scanned by digest but was not selected, executed, or deployed.

Image maintenance belongs upstream. By the operator's decision, this repository documents image findings
and consumes official Hermes images only; it will not fork, rebuild, patch, or maintain a custom Hermes
image. Findings have not been reported externally by this work.

The operator subsequently approved advisory scans with an explicit denylist. High, critical and unknown
severity counts are recorded without automatically blocking. A completed, valid scan of the exact image
is still required; scanner failure, digest mismatch and assessed denylist matches block signing.
The [policy reevaluation](plans/evidence/2026-09-07-advisory-policy.json) passes both existing reports under
the new policy, with advisories retained. It is not a new scan or completed VM certification.

The versioned [policy file](../scripts/hermes/unattended/vulnerability-policy.json) currently has an empty
denylist: no specific finding has been assessed and enrolled as unacceptable. Each future entry requires
`id`, `package`, `reason`, `owner` and `assessed_at` (an ISO date). `package="*"` covers all packages for
that vulnerability. Denials apply across image/package versions and remain active until explicitly
removed; an upstream version change cannot silently bypass them. Old exception records are rejected.
The policy is frozen into the candidate and its hash bound to signed scan evidence. Signature, identity,
credential, runtime, backup/restore and boot gates are unchanged.

The VM creator retains its legacy console-unlock profile and now has an explicit `--tpm-stage`
profile for signed installer media and emulated TPM enrollment. It stops powered off before installed
UKI injection through the lab handoff. The separate [isolated certifier](#isolated-candidate-certification)
runs candidate acceptance. Production hardware recovery validation has its own required gate. `finalize.py` verifies
completed evidence; it does not manufacture it or substitute for running those gates.

## Interfaces

```text
hermes-deploy.sh deploy|upgrade|rollback --non-interactive --config PATH --release PATH
hermes-deploy.sh check|status --non-interactive --config PATH
```

All responses on this interface are JSON. Exit 64 means invalid protocol/configuration; 66 means
missing input; 69 means an unavailable operation or timeout; 75 means busy/deferred/recovery needed;
77 means denied authority; 78 means a failed trust or acceptance gate. Remote failures are deliberately
sanitized and may be reported as a general rejected operation rather than echoing remote error output.
There is no fallback to an interactive terminal, password prompt, host-key acceptance, or OAuth flow.

Configuration contains paths and identifiers only. See the
[controller](../scripts/hermes/unattended/examples/controller.json),
[host](../scripts/hermes/unattended/examples/host.json), and
[broker](../scripts/hermes/unattended/examples/broker.json) examples.
Use separate deployment, certification, signing, and credential-service identities. The workstation
root account is still a trust boundary. Administrative provider credentials never enter the host or VM.

The selected API model is `gpt-5.6-luna`, matching the
[official Luna identifier](https://developers.openai.com/api/docs/models/gpt-5.6-luna).
The controller example records this selection. Candidate preparation must use the same `--model`
value; project access and actual inference must pass before the model is certified for deployment.

## Enrollment contract

Enrollment is an explicitly authorized operator procedure. Before privileged production work, rotate
the `aicowork` sudo password affected by the recorded terminal-echo incident.

1. Verify the SSH ED25519 fingerprint at the console and record the machine-id SHA-256. Keep using
   `10.0.30.10`; do not assume resolver validation has passed.
2. Establish Fedora Server 44, the approved package baseline, enforcing SELinux, firewalld, management-only
   SSH, locked root login, and a working TPM2/LUKS2/Secure Boot chain. Keep existing agent approval policy.
3. Enroll signed UKI boot with systemd-boot, PCR7 and signed PCR11 policy, and an offline recovery key.
   Preserve the prior signed boot entry and matching kernel modules. Validate cold boot, updated boot,
   rejected tampered boot, and
   recovery. The backend requires every systemd TPM token to use no-PIN SHA256 PCR7/signed PCR11; review
   parallel legacy automatic tokens before promotion. Future runtime credentials explicitly use this policy.
   The backend deliberately refuses a GRUB-only or unverified TPM configuration.
   Keep enough free ESP space for the complete new UKI plus 1 MiB of working space, alongside
   retained boot entries. Insufficient space blocks installation before boot selection changes.
4. Install the Python modules and `dispatch` wrapper root-owned under
   `/usr/local/libexec/hermes-unattended/`. Create `/var/lib/hermes-unattended` as root mode `0700` and
   `/etc/hermes-unattended` as root mode `0755`. Trust files and every parent must not be group/world writable.
5. Enroll the dedicated SSH key with a fixed forced command invoking
   `sudo -n /usr/local/libexec/hermes-unattended/dispatch`. Use `restrict` and an explicit management source
   restriction. Grant sudo only that exact no-argument wrapper, with no `SETENV`, arbitrary shell, or
   upload helper authority. Preserve the separate operator recovery account in the effective SSH policy.
6. Install the dedicated signing public key as an allowed signer named `hermes-release`. The private
   signing key stays with the workstation signing identity, separate from deployment SSH credentials.
7. Configure distinct OpenAI test and production projects and non-root broker peer UIDs. For a test-only
   lab, set both `production_project` and `production_uid` to JSON `null`; production requests are rejected
   before provider access. Provision the administrative credential through systemd encrypted credentials,
   and verify issue/delete/rejection with disposable accounts.
8. Initialize the encrypted Restic repository and separately retain its recovery password. Install the
   service templates only after validating their identities, paths, credentials, and dependencies.

Required workstation tools include Python 3 with `zoneinfo`, OpenSSH, Restic, and Trivy for release scans.
The host additionally needs Fedora's DNF5 offline/replay support, Podman, systemd-creds, cryptsetup,
systemd-boot, mokutil, and sbverify. The credential broker requires working user-scoped
`systemd-creds encrypt/decrypt --user` under its isolated service identity; failure is not downgraded
to plaintext storage. Its `--config`, `--state-dir`, and `--socket` options support isolated lab paths;
the configuration and ancestors must be root-controlled, the state directory private to the broker,
and the systemd-activated listening Unix socket must match the configured path. Use separate static
lab units without production triggers, and verify dummy encryption under the actual unit sandbox
before issuing a provider key. No services are automatically enabled by checking out these files.

## Release lifecycle

`prepare.py` freezes repository payloads, a stored DNF5 transaction with all RPMs, the expected
post-transaction package inventory hash (`installed-after.sha256`), and the signed host-compatible UKI.
It writes `candidate.json` and an artifact fingerprint, not a promotion record.

`scan_candidate.py --candidate PATH --output PATH --run-id HEX64` performs the real image scan using the
candidate's frozen policy and writes its bound scan gate, including advisory counts. The certifier must
use the same run ID for its remaining evidence. A successful scan alone never produces a signed release.

`boot_build.py` builds a signed UKI on the workstation from explicit kernel, initrd, os-release, command
line and systemd-stub inputs. It uses separate Secure Boot and PCR-policy keys, SHA-256 PCR11 signatures
for the initrd phase (installed systems) or supported installer boot phases. It verifies the EFI signature
and required sections before publishing the file.
Private boot keys stay on the workstation. This builder does not enroll firmware or a TPM and returns
`boot_verified=false`; actual cold-boot, update, tamper and recovery tests remain required. The pinned
Devbox systemd/ukify tools are development dependencies, not replacements for workstation system services.

`firmware.py` creates a separate OVMF variable file with the test certificate enrolled in both PK and
db. `efi_media.py` verifies the signed installer and matching PCR public key, then builds and reads back
a FAT EFI boot disk containing only the installer UKI, Kickstart and public key. No private signing key
enters the guest. See the [VM staging procedure](VM_TESTING_GUIDE.md#unattended-tpm-staging).

The trusted certifier must produce one JSON record per required gate: `inference`, `restore`,
`credential_revocation`, `data_purge`, `vm_destroyed`, `boot`, `runtime`, `package_replay`, and
`vulnerability_scan`. Each record must contain its gate, `result=PASS`, exact `release_id`, and
`artifact_fingerprint`. These files belong to the trusted certifier identity and must not be writable
by the deployment identity. Stating `PASS` manually is not certification.

The enrolled `signer.py` service also requires a shared 64-character hexadecimal `run_id` and integer
Unix `completed_at` in every gate record. Records must be at most 24 hours old; destruction must follow
all other gates, and credential revocation must follow inference. The
[signer policy](../scripts/hermes/unattended/examples/signer.json) is root-owned and enrolls distinct
certifier and signer UIDs. Candidate and evidence files must be certifier-owned with no group/world
write access. Their parent directories may be owned only by root or that certifier. Grant the signer
read access through its group using directory mode `0750` and file mode `0640`; no secrets belong in
this handoff. Keep the private signing key mode `0600` under the signing identity.

`finalize.py` checks frozen payload hashes and every evidence binding, starts the 24-hour first-use
window after cleanup, and calls `build_release.py`. The signer authenticates the canonical manifest
using OpenSSH namespace `hermes-release@ai.lab.local`. The archive contains regular files only;
unexpected files, links, traversal, duplicate JSON keys, sparse files, and archive extensions are rejected.
Candidate paths are validated before opening payload files. The signing service copies the checked
handoff into private signer-owned staging, preserving the exact evidence bytes and frozen payload hashes.
It publishes the completed archive atomically at `/var/lib/hermes-releases/selected.tar`. Existing
candidate archives are not re-signed to renew their expiry; interrupted publication requires recovery.

The root dispatcher repeats signature, host binding, and payload checks. It stores immutable releases
under a separate `releases/` directory and binds their manifest hash in root-owned state. A same-ID
replacement is rejected. The signed `payload/host.py` is executable root authority: protecting and
isolating the signer is essential. Hashes without the trusted signature do not authorize execution.

## Execution and recovery

The controller verifies dependencies, broker reachability, backup access, release, model, host, and
maintenance window before starting remote changes. It takes a per-target lock, stages the release,
quiesces the service, pulls a snapshot into volatile workstation storage, and encrypts it with Restic.
A byte-identical Restic dump is required before the host acknowledges the backup. Actual archive
restoration and application recovery must additionally pass in the disposable VM.

The host then receives a dedicated API credential through encrypted SSH stdin, encrypts it with
systemd, stages the certified package replay, and journals the reboot. Strict replay runs through the
[systemd offline-update target](VM_TESTING_GUIDE.md#freeze-the-package-transaction), because DNF5's
replay command has no `--offline` option. The existing kernel runs the offline replay with its
installed modules. The updated UKI is copied first but selected only after exact RPM inventory and
UKI hash verification; failed replay preserves the previous boot selection. Offline Python execution
disables bytecode writes to preserve the frozen candidate. A changed boot ID is insufficient: recorded replay completion,
a subsequent normal boot and the post-update installed package fingerprint must all match.
The runtime is installed and hardened,
then exact `HERMES_OK` and an independent persistence reboot are required before closure.
While that reboot is pending, the host checks the boot ID before touching the stopping runtime.
After the new boot, bounded runtime health waiting precedes acceptance. Primary certification
failures and cleanup failures are retained separately.

Runtime credentials are mounted as a read-only volatile `.env` overlay. Channel settings are preserved;
the provider key and OpenAI endpoint are controlled by the materializer. The image must pass acceptance
with this extra mount; the legacy single-mount acceptance test alone is not sufficient.
The materializer reads channel settings as container UID/GID 10000, rejecting symlinks, non-regular files
and oversized input. Configuration backup and restoration likewise avoid root authority in Hermes-owned
storage. The installer orders credential materialization after the user's runtime-directory service and
before its user manager. UA-03 and the scheduler run passed live cold-boot/runtime acceptance for their
bound lab candidates; production boot validation remains part of UA-05.
Fresh account setup starts the user manager before invoking Podman, so its runtime directory exists.
Commands run from the Hermes home after dropping privileges, avoiding an inaccessible SSH operator
working directory. The UA-02 live fixture exposed and corrected both initialization failures.
Data readers and configuration rollback enter the data directory inside the rootless Podman
namespace before switching to container UID/GID 10000. This permits access beneath a mode-0700
Hermes home while keeping file reads and writes under the container identity.
Configuration rollback creates and replaces files relative to an open data-directory descriptor.
After restarting credential materialization, installation and rollback explicitly start the dependent
user manager before issuing user-bus commands.

A failed pre-package operation restores the previous application files and service. A timed backup guard
also handles an abandoned quiesced service. Interrupted package staging is not blindly retried: inspect
the journal and recover the OS. Application rollback does not reverse RPM transactions. After a successful
credential rotation, later application rollback keeps the current key rather than reviving a revoked key.

Successful pre-change backup IDs are tracked locally. Retention forgets only owned successful snapshots
beyond the last eight, always protecting the current rollback snapshot. Failed/unrecognized snapshots
are not implicitly deleted. Provider-side deletion and HTTP 401 verification precede a revocation result;
403, timeout, and local logout are not accepted as proof.

The supplied timer selects Sunday 02:00 in `America/Bogota`, with no missed-run catch-up. The controller
requires at least 30 minutes remaining to start new work. It deploys a selected signed release; automatic
fixture enrollment and post-certification cleanup must also be automated before calling the entire
release lifecycle unattended. The separate candidate scheduler is described below. Firmware/trust failures
and workstation unavailability remain recovery boundaries.

`hermes-sign.service` starts maintenance only after successful signing. The signing and maintenance
services run as separate users; the deployment user has read access to published archives and no write
access to the signing directory. This deployment timer chain is separate from `hermes-certification.timer`,
which prepares a candidate and
invokes the enrolled isolated certifier. Certification has no automatic signing or deployment trigger;
UA-04 must still complete first. Do not connect the historical interactive certifier as a substitute.

`maintenance.py` publishes only fixed outcome codes and a hashed release identifier in
`/var/lib/hermes-notifications/latest.json`. It records missing releases and failed or incomplete
deployments as requiring attention. `hermes-maintenance-failed.service` covers service-level failure,
including timeout. Outside-window invocations defer without starting the controller.

Install `hermes-notify.service` and `hermes-notify.timer` as user units in the operator's graphical
session. They use `notify-send` for local desktop delivery, retry failed delivery, and suppress repeated
unchanged outcomes. They never send Slack, email, or provider response bodies. These units are templates;
none have been installed or enabled during implementation. The latest-event file does not provide a
historical event queue: a desktop that is offline can receive the latest outcome after it returns.

## Verification

```bash
python3 -m unittest discover -s tests -p test_hermes_unattended.py
shellspec spec/hermes/ spec/vm/
./tests/test-hermes-guide.sh
shellcheck hermes-deploy.sh scripts/hermes/deploy-lib.sh scripts/hermes/promotion-record.sh scripts/hermes/unattended/dispatch
git diff --check
```

References: [OpenSSH signatures](https://man.openbsd.org/ssh-keygen),
[systemd credentials](https://systemd.io/CREDENTIALS/),
[DNF5 replay](https://dnf5.readthedocs.io/en/stable/commands/replay.8.html),
[Restic automation](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html),
[Hermes providers](https://hermes-agent.nousresearch.com/docs/integrations/providers/),
[OpenAI service-account creation](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/projects/subresources/service_accounts/methods/create),
[OpenAI service-account deletion](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/projects/subresources/service_accounts/methods/delete).

The [staged guest candidate procedure](VM_TESTING_GUIDE.md#build-the-staged-guest-candidate) now connects
public boot export, UKI construction, candidate freeze and disk injection. The scheduler consumes an already
signed compatible UKI and stored transaction; it does not provision or enroll a new TPM fixture.
The boot helper never emits passing certification evidence.

## Privileged-boundary review continuation

The [execution record](plans/2026-09-07-hermes-unattended.md) records the source review and repairs.
The dispatcher starts with a fixed environment. Hermes-owned data directory creation and mode changes
run as Hermes. The signer opens evidence through held directory descriptors, rejects redirected
parents, and checks payload hashes and gate records before signing. Isolated certifier ownership
remains a required enrollment boundary; these checks cannot establish that a certifier's claims are true.
TPM lab creation requires private per-fixture recovery input and refuses existing dedicated storage;
see the [VM guide](VM_TESTING_GUIDE.md#unattended-tpm-staging). Live recovery remains a separate gate.

## Isolated candidate certification

`certify.py --config /absolute/root-owned/policy.json` runs UA-03 as the enrolled non-root
certifier identity. The policy fixes the test broker socket, `hermes-certify@172.16.99.12`, the
retained disposable domain UUID, pinned SSH identity, frozen candidate, expected kernel, encrypted
Restic repository and one run ID. No production credential role or target override is accepted.

Enroll `lab-dispatch` and the verifier modules root-owned under
`/usr/local/libexec/hermes-lab-certifier/` in the disposable guest. Bind
`/etc/hermes-lab-certifier.json` to the exact candidate manifest hash, machine identity and run ID.
Only the dedicated restricted SSH key may invoke the no-argument wrapper through sudo. Preserve the
operator recovery identity. Preserve the effective existing `AllowUsers` list when adding the lab
identity and verify both pinned operator and certifier keys after reloading SSH. This endpoint is
separate from production enrollment and cannot issue a
release or mark the production host enrolled. The fixed local `lab-power` helper permits only power
operations for the matching disposable domain and its dedicated disk; it grants no arbitrary virsh command.

When running under a supervised scope, direct sanitized progress output to a private durable log
before dispatch so the invoking terminal or tool connection can close independently.

Boot waits retry only unavailable SSH transport or a transport timeout; a permanent guest rejection
stops the run and triggers cleanup. Frozen Python payloads run without writing bytecode.

The runner verifies frozen bytes, tests rejected requests, stages the candidate, captures an encrypted
backup, issues a test credential, executes the actual candidate host stages, and observes exact package
inventory, warm/cold boot, TPM services, runtime isolation, inference and semantic application restore.
It then applies the frozen image scan policy. Candidate and evidence directories belong to the certifier;
the signer still requires all remaining UA-04 evidence before it can issue a release.

Failures retain `state.json`, the backup receipt and any completed observations. A failed run cannot
be silently resumed under the same identity or converted to passing evidence. Fix its cause, preserve
its artifacts, restore the verified baseline and enroll a new run. `--cleanup-only` reconciles the
recorded run's temporary credential without issuing another one. Install it as an independent
service cleanup action when scheduling certification, so abrupt runner termination cannot leave a
credential without a cleanup procedure. Cleanup restores the prior encrypted guest credential and
requires provider-side revocation; a cleanup failure prevents UA-03 completion.

Application archives and provider keys remain in memory or volatile storage during transfer; backups
are encrypted with Restic. Signing keys and administrative provider credentials never enter the VM.

## Scheduled candidate certification

`schedule.py` freezes the exact inputs selected by a root-owned `hermes-schedule-v1` policy, then invokes
`certify.py` as the enrolled non-root certifier. It accepts no shell commands, production target or signing
key. Root-owned policy and ancestor checks apply to both scheduler and certifier configuration files.
The certifier retains its fixed disposable domain, test-only broker, pinned SSH and exact guest enrollment
requirements. Its service identity and sandbox passed
[live candidate certification](plans/evidence/2026-09-08-hermes-scheduler-live.json) with an explicitly
approved lab window grant. The service was started directly; calendar behavior was checked separately,
and the live off-window invocation deferred. The separate [automatic fixture lifecycle](#automatic-fixture-lifecycle)
now implements provisioning/enrollment and teardown; its live gate is pending. The S4 observation above
used the ordered operator procedures and does not validate that new driver.

The scheduler policy has exactly these fields:

| Field | Meaning |
| --- | --- |
| `schema` | `hermes-schedule-v1` |
| `certifier_config` | Absolute path to the root-owned `hermes-certify-v1` policy described above |
| `state_dir` | Existing private certifier-owned scheduler directory, separate from candidate, evidence and certifier state |
| `prepare` | Object containing `repository`, `transaction`, `uki`, `host_identity`, `release_id`, `model`, `baseline` |

The first four recipe values are absolute paths: the selected repository, complete stored RPM transaction,
already signed compatible UKI and public host identity JSON. `baseline` is the enrolled package inventory
SHA-256. Selection is explicit enrollment of these inputs; the scheduler does not choose unreviewed upstream
versions, build custom images, construct a UKI or update guest trust. The candidate destination, run ID,
backup and evidence paths come from the certifier policy. Use fresh directories and a new run ID per candidate.

The supplied `hermes-certification.service` and timer are installation templates, not activated services.
Install reviewed modules root-owned under `/usr/local/libexec/hermes-unattended/`. Optional service-local
Restic/Trivy executables may be installed in its root-owned `bin/` directory; that directory and its ancestors
must be root-controlled. The child prepends it to the fixed system PATH and never inherits caller PATH.
Enroll the service account
as the certifier UID and create private scheduler, candidate-parent, certifier-state and evidence directories
under `/var/lib/hermes-certification/`. The service can write that state tree and
`/var/lib/hermes-certification-events/`; place its writable Restic repository there too. Public input files
and the enrolled SSH/backup credentials must be readable by the certifier. Keep signing and administrative
credentials under their separate identities. The existing fixed-domain `lab-power` sudo helper is required;
the unit intentionally permits that elevation. Its sandbox and power helper require live validation together.

The timer starts Sunday at 02:00 America/Bogota and does not catch up missed windows. The scheduler checks
the existing 30-minute minimum window before automatic preparation and again before certification.
Explicit `--prepare-only` freezes local public inputs outside the window without invoking the certifier.
Credential cleanup can also run outside the window. Separate preparation permits exact guest enrollment:

```bash
python3 scripts/hermes/unattended/schedule.py \
  --config /etc/hermes-unattended/schedule.json \
  --events /var/lib/hermes-certification-events --prepare-only
```

Run under the enrolled certifier identity. The command returns the frozen candidate manifest SHA-256.
Enroll that exact hash and run ID in the disposable guest using the restricted endpoint procedure above.
A subsequent scheduled invocation without `--prepare-only` revalidates those frozen bytes before invoking
the certifier. Without matching guest enrollment the certifier rejects the candidate; the scheduler cannot
create its own trust exception. Initial provisioning, per-candidate guest enrollment, and UA-04 purge/destruction
still require their ordered operational procedures. The previous UA-04 run destroyed its fixture.

An explicitly approved disposable-lab timing exception uses `--lab-window-grant /absolute/root-owned.json`.
The file has exactly `schema: hermes-lab-window-v1`, `binding` (the full policy binding from the prepared
scheduler journal), `run_id`, `candidate_sha256`, and integer Unix `issued_at`/`expires_at` fields.
It must be root-owned on a protected path, issued no later than now, unexpired, and valid for at most
four hours. Only the fixed disposable domain and endpoint are accepted. Enroll it as an explicit service
argument after candidate preparation and guest binding; never change the bound policy to bypass the clock.
The scheduler rechecks expiry before dispatch and records the grant SHA-256 in its existing journal.
Completed runs do not dispatch again; failed/interrupted runs still require recovery and fresh enrollment.
Cleanup remains available after expiry. Remove the grant and service override during lab cleanup.
This does not change the Sunday timer or authorize production operations.

`schedule.json` in the private scheduler state directory binds the complete policies and frozen candidate.
A nonblocking lock prevents overlapping runs through that state directory. Completed runs do not repeat;
changed policies, changed bytes, partial preparation, interrupted certification and failures require recovery.
Preserve the old journal and evidence, reconcile credentials using the enrolled policy, restore the verified
lab baseline, and enroll a fresh run and state directories. Do not delete a journal to force a retry.

The child receives closed stdin, a fixed environment and a 110-minute timeout. On ordinary failure or timeout,
the scheduler attempts `certify.py --cleanup-only` with a separate five-minute bound. The service also invokes
cleanup through `ExecStopPost`, including after interrupted starts. A power loss still requires cleanup on
recovery. Failed cleanup is never counted as success. No scheduler state is promotion evidence.

Fixed local events are published under `/var/lib/hermes-certification-events/latest.json`; exception text and
child output are excluded. Preparation or UA-03 completion requests operator attention for the remaining
gates. Deferred and already-completed runs emit no new event. The service failure unit covers timeout or
termination before Python can publish. Configure a separate instance of the existing desktop notifier with
this event path and its own notification state directory to receive deduplicated local alerts.

There is deliberately no `OnSuccess` signing or deployment transition. The signer still requires all UA-04
records, including actual purge and VM destruction, bound to the same candidate and run. Historical lab
certification does not establish scheduler or production readiness.

## Automatic fixture lifecycle

`lifecycle.py` is a separate root-enrolled service for U06. It calls `lifecycle_fixture.py` to provision
only `lab-hermes-server` with UUID `4db6369a-2b8b-427f-a47a-a5d83bb40cff` and the dedicated TPM pool.
It invokes the existing scheduler/certifier under `hermes-certification` using `runuser`. The certifier
receives no lifecycle sudo permission. Production targets and release signing are absent from this interface.
The one-time F4 campaign passed two fresh cycles, completed-run idempotency and credential-bearing
interruption recovery; see the [execution record](plans/2026-09-07-hermes-unattended.md#f4-final-closure)
for source/tool applicability and live evidence. Its temporary controls were removed and broker changes
restored. Recurring enablement still requires separate operator authorization and prerequisite enrollment.
Synthetic tests alone do not establish VM, TPM, provider or promotion evidence.

### One-time enrollment prerequisites

Use the [lifecycle policy template](../scripts/hermes/unattended/examples/lifecycle.json). Its placeholder
hash and fingerprint intentionally prevent execution. The JSON must contain exactly the template's fields.
Enroll verified signed Fedora 44 media, its exact ISO SHA-256, the authenticated Fedora signing fingerprint,
a dedicated verification keyring, the matching OVMF 4 MiB QCOW2 code/variable pair and the approved model.
The code and variable regions are 3,653,632 and 540,672 bytes, respectively, when converted to raw.
The source repository, policy, media and every ancestor must be root-owned and not group/world-writable.
Keep a reviewed source installation at `/var/lib/hermes-lifecycle-source/repository`; do not point this
privileged service at a developer-writable checkout. Policy paths accept absolute paths without whitespace,
parent traversal or shell syntax. The state, event and repository paths cannot overlap.

Provision root-owned mode-0711 `/var/lib/hermes-lifecycle` and `/var/lib/hermes-lifecycle-events` directories.
Run-private directories remain mode 0700; only the certifier's individual inputs/state/evidence directories
belong to its non-root account. Existing lifecycle runs and their root journals must remain unchanged.

The existing isolated test broker must be enrolled for that certifier UID and available at
`/run/hermes-lab-credentials/broker.sock`, with its administrative credential confined to that service.
The existing fixed-domain `lab-power` helper must also be root-installed and available to the certifier.
Use the root-owned service tooling layout documented for the candidate scheduler, including its `bin`
directory for child tools. The lifecycle service additionally needs libvirt, libguestfs, QEMU, xorriso,
Fedora signature verification, `virt-fw-vars`, mtools (`mformat`, `mmd`, `mcopy`) and the UKI signing
toolchain. On this Fedora/Nix lab, the enrolled Trivy launcher sets `GODEBUG=netdns=go` for
that process; its default lookup reached an unusable IPv6 CDN address, while forcing libc lookup
failed with the host NSS configuration. Preserve the pinned binary and record the root-owned launcher
hash. This setting alone did not eliminate intermittent registry transport failures; require a real
scan PASS and never substitute connectivity diagnostics for it. The lab launcher permits at most six
recognizable transport attempts within one 900-second budget, discards failed partial output, and
leaves nontransport failures fatal. Record the launcher source and its tested hash with tool enrollment.
The adjustment does not change the scan policy or host networking.
Install reviewed tool wrappers under
`/var/lib/hermes-lifecycle-source/bin`; keep private release-signing and production credentials separate.
No policy, unit, sudo grant, broker credential or timer is installed by the offline tests.

The service/timer templates are `hermes-lifecycle.service`, `hermes-lifecycle.timer` and
`hermes-lifecycle-failed.service` in the unattended `systemd/` directory. The root service has the authority
needed for local fixture creation and destruction; its isolation boundary is the reviewed root-owned code,
fixed resource identities and dedicated certifier account. F4 exercised this service and its non-root
child dispatch on the disposable lab host; it does not establish production readiness.
Enable this timer only after F4 and operator authorization. The timer selects Sunday 02:00 Bogotá and
has no persistent catch-up. Do not enable a separate candidate timer against a lifecycle-owned fixture.

### Explicit disposable-lab timing exception

An explicitly authorized one-time campaign may invoke `lifecycle.py --lab-window-grant /absolute/grant.json`.
The grant and all ancestors must be root-owned, without group/world write access. Its exact fields are
`schema` (`hermes-lifecycle-lab-window-v1`), `binding` (SHA-256 of canonical lifecycle policy), `run_id`
(64 lowercase hexadecimal characters), and integer `issued_at`/`expires_at` epochs, at most four hours apart.
It binds one fresh run and is consumed before provisioning; retained run directories prevent replay even
after a later run completes. A repeat of the current completed run allocates no fixture.

The window is checked again before certification. Only after the candidate is frozen and independently
approved does the driver derive the existing candidate-specific scheduler grant, retaining the original
expiry. Cleanup remains available after expiry or grant removal. Each approved fresh cycle needs its own
root-enrolled grant. Normal invocations still follow Sunday 02:00–04:00 Bogotá; neither timer is changed.
Use a separate temporary service for lab dispatch; do not leave a grant override on the normal service.
Remove temporary grants after retaining their public identity in the execution record.

### Per-run order

1. Refuse an existing fixed domain, TPM/NVRAM or dedicated pool. Check host resources, verify the signed
   Fedora checksum and exact ISO, and record the root source identity. Attach only a verified per-fixture
   ISO copy, since libvirt can change ownership of attached media; preserve the reusable root-owned ISO.
2. Generate fresh boot, PCR, recovery, operator SSH and guest SSH keys. Create a fresh encrypted TPM
   installation from the verified media. No old disk, TPM or provider credential is cloned.
3. Read back the guest host key and machine identity through offline recovery before pinned SSH. Build
   and inject the installed signed UKI, enroll the signed boot manager, then verify its boot and TPM services.
4. Bootstrap the pinned official image with a local random canary, store and validate a signed RPM
   transaction, and preserve a checked baseline disk. Replay the stored transaction on the preparation
   fixture, export its resulting kernel/initrd, build its compatible UKI and restore/compare the baseline.
5. Generate a fresh certifier key and backup password, initialize the fresh Restic repository under the
   certifier identity, and freeze the scheduler candidate. Independently
   reconstruct its expected fingerprint from root-owned inputs before enrolling the exact manifest hash,
   run ID, guest identity and kernel in the restricted guest endpoint. Certifier-selected substitutions fail.
6. Recheck the maintenance window before invoking the existing scheduler. Require all seven bound UA-03
   gates and unchanged candidate bytes before recording acceptance.
7. Reconcile credentials, purge guest application data and the run's certifier keys/backups, then verify
   exact domain, storage, NVRAM and TPM destruction. Remove private boot/operator/recovery inputs and
   retain the public candidate, source identity, acceptance and cleanup observations. Deletion is logical.

A completed maintenance date cannot dispatch twice. A later maintenance date creates a distinct random run
and preserves prior journals. Preparation that outlasts the window is cleaned up without certification.
No window override exists in this lifecycle entrypoint. A missed or completed slot stays quiet; meaningful
completion or failure produces a fixed, secret-free local event. These events do not themselves establish
release eligibility, produce a signature or trigger deployment.

### Interruption and cleanup

An interrupted or failed active run prevents a new fixture. The service's `ExecStopPost` invokes the same
entrypoint with `--cleanup-only`; this is available outside the maintenance window. Under the reviewed
root installation, the recovery command is:

```bash
python3 -B -E -s /var/lib/hermes-lifecycle-source/repository/scripts/hermes/unattended/lifecycle.py \
  --config /etc/hermes-unattended/lifecycle.json --cleanup-only
```

Run operator commands through the repository's Devbox/VM execution convention. Cleanup retries do not
rerun preparation, issue another credential, sign a release or turn interrupted acceptance into PASS.
The root journal binds deletion checkpoints to the exact storage directory inode. Credential reconciliation
failure stops guest/local purge and destruction; inaccessible guest purge also stops destruction and retains
recovery inputs. The existing broker can require operator reconciliation after an uncertain issuance.
Preserve that failed run and reconcile its exact account before retrying cleanup; never delete journals,
change the run ID or fabricate revocation evidence to force a retry.

Public observations are in each run's `lifecycle.json`, `approved.json`, `frozen.json`, `acceptance.json`
and `cleanup.json` where those stages completed. `work/candidates/candidate` and `work/evidence` retain
candidate and certifier evidence. The root cleanup observation is not automatically handed to the signer;
any later signing still requires the existing independent UA-04 evidence/promotion procedure.

## Production boot recovery backup

After pinned host inventory and a successful operator LUKS credential test, run this block in the
existing interactive production SSH terminal. Enter sudo authentication only at its terminal prompt.
The block verifies the observed LUKS UUID and EFI mount before creating a unique root-only directory.
It preserves boot files, encryption metadata and the recorded firmware boot entries without changing
boot selection or encryption. The header backup contains sensitive keyslot material; keep it private.

```bash
sudo bash -eu -c '
  umask 077
  test "$(cryptsetup luksUUID /dev/nvme0n1p3)" = "566d41dd-003d-4e65-8a42-652fee07c40f"
  mountpoint -q /boot/efi
  backup_dir=$(mktemp -d /root/hermes-boot-recovery.XXXXXXXX)
  cryptsetup luksHeaderBackup /dev/nvme0n1p3 --header-backup-file "$backup_dir/luks-header.img"
  cryptsetup isLuks "$backup_dir/luks-header.img"
  tar --acls --xattrs --selinux -C / -cpf "$backup_dir/boot.tar" boot
  efibootmgr -v > "$backup_dir/efibootmgr.txt"
  tar -tf "$backup_dir/boot.tar" > /dev/null
  cd "$backup_dir"
  sha256sum luks-header.img boot.tar efibootmgr.txt > SHA256SUMS
  sha256sum -c SHA256SUMS
  printf "Backup directory: %s\n" "$backup_dir"
'
```

A failure stops the block and retains any partial backup for inspection; reruns create a separate directory.
Success requires all three checksum checks to print OK. This validates local creation and readability,
not a recovery restore. Before boot mutation, retain and verify a protected off-host copy as well;
a backup stored on the same encrypted root filesystem is insufficient for offline recovery.
This step does not satisfy the later cold-boot, updated-boot, tamper-rejection or recovery-boot gates.

## Production boot input preparation

Continue P1 in the [canonical execution record](plans/2026-09-07-hermes-unattended.md#production-continuation--2026-09-08)
before P2 hardware boot testing. Retain the verified local/off-host recovery backups and Fedora entry.
The following inventory does not install packages or change boot selection. Run in the existing
operator SSH terminal on `10.0.30.10`; authenticate sudo interactively without recording the terminal.
Report command errors and the public inventory output only; never provide passwords or backup contents.

```bash
sudo bootctl status --no-pager
sudo efibootmgr -v
sudo find /boot/efi/EFI -type f -iname '*.efi' -printf '%P %s bytes\n'
df -B1 /boot/efi
sudo dnf5 --refresh repoquery --available --latest-limit=1 \
  --queryformat '%{name} %{evr} %{arch}\n' \
  systemd-boot-unsigned systemd-ukify sbsigntools
sudo dnf5 --refresh repoquery --available --latest-limit=1 --files \
  systemd-boot-unsigned systemd-ukify
```

Metadata refresh updates the DNF cache only. If a query fails, stop package preparation and retain
its error. Match the boot manager and stub to the selected Fedora systemd baseline. The expected
inputs are `systemd-bootx64.efi` and `linuxx64.efi.stub` from the resolved RPM file lists;
verify actual ownership and paths before extraction. Fedora describes
[systemd-boot-unsigned](https://packages.fedoraproject.org/pkgs/systemd/systemd-boot-unsigned/)
as an unsigned boot manager and
[systemd-ukify](https://packages.fedoraproject.org/pkgs/systemd/systemd-ukify/index.html)
as the UKI construction tool. Keep private signing keys on the workstation as required by the
existing builder contract; host package installation is a separate reviewed transaction.

Before installing anything, resolve the exact RPM transaction with an assume-no preview, inspect
scriptlets and dependencies for boot side effects, verify RPM signatures and record NEVRAs and SHA-256
hashes of downloaded inputs. Do not silently upgrade the whole system to satisfy boot tooling.
Build from the actual production kernel/initrd and reviewed command line, using a dedicated production
Secure Boot key and separate PCR11 policy key. Never reuse disposable lab keys or the lab enrollment helper.

The candidate trust path is firmware → retained Fedora-signed shim in a separate Hermes directory →
production-signed systemd-boot → production-signed UKI. Upstream
[shim documentation](https://github.com/rhboot/shim/blob/main/README.md)
describes second-stage verification and the shim 16.1 loader protocol. This is a proposed hardware path,
not a passed production gate. Confirm the exact Fedora shim build, second-stage filename, SBAT metadata,
denylists and signature verification before staging. A certificate in MOK does not establish trust for
a direct firmware launch. Keep existing PK, KEK, db, dbx, MOK and Fedora files intact; do not enter Setup
Mode, clear keys, overwrite fallback EFI files or run a generic boot-manager installation blindly.

After these inputs pass inspection, prepare a dedicated public-certificate enrollment handoff with its
SHA-256 fingerprint. Operator console enrollment and verification must precede trial boot selection.
Retain the current boot default; any later one-shot trial requires known console recovery and an exact
restoration procedure. Measure the complete signed UKI against available ESP space, retaining the old
boot chain and at least 1 MiB extra. Validate cold boot, updated UKI, tamper rejection and physical recovery
before P2 passes or any production TPM unlock/enrollment is treated as accepted.

Before reusing retained backup files as UKI inputs, obtain current live hashes in the operator terminal
and compare them with exact files extracted privately from the verified backup. For the observed kernel:

```bash
uname -r
sudo sha256sum \
  /boot/vmlinuz-7.1.12-200.fc44.x86_64 \
  /boot/initramfs-7.1.12-200.fc44.x86_64.img \
  /boot/efi/EFI/fedora/shimx64.efi \
  /boot/efi/EFI/fedora/mmx64.efi
```

If the running kernel differs, stop and select its actual inputs before building. Hash output is sufficient;
keep initramfs contents and recovery archive private. Hash equality establishes file identity only.

## Production signing certificate enrollment

Use this handoff only after local candidate signatures/sections and backup identity pass in the
[execution record](plans/2026-09-07-hermes-unattended.md). Physical console and the retained LUKS
recovery credential must be available for the reboot. The current Fedora boot path remains selected.
The [upstream mokutil manual](https://github.com/lcp/mokutil/blob/master/man/mokutil.1)
requires the physical operator to confirm pending imports in MokManager.

The prepared certificate is `Hermes Production Secure Boot 20260909`. Its DER SHA-256 is
`f23d1ee7b728ea0f9013a75e0b3fbb36c51bf59bbcefa78b1a06e48b4446365c`.
Only this public certificate is staged on Hermes; private signing keys remain on the workstation.
In the operator SSH terminal, first verify its hash:

```bash
sha256sum /home/aicowork/.local/state/hermes-boot-inputs-20260909/hermes-production-sb.der
```

If it matches, request import interactively:

```bash
sudo mokutil --import /home/aicowork/.local/state/hermes-boot-inputs-20260909/hermes-production-sb.der
```

Choose a temporary enrollment password locally; never share or record it. Reboot only while ready at
the physical console with the recovery credential. In MokManager select Enroll MOK, inspect the
certificate identity, continue and confirm with that password. Do not delete existing keys or disable
Secure Boot. Return through the retained Fedora entry and unlock the existing LUKS boot as usual.
If the certificate differs or the enrollment screen is unavailable, stop and report the observation.

After returning to Fedora:

```bash
mokutil --test-key /home/aicowork/.local/state/hermes-boot-inputs-20260909/hermes-production-sb.der
mokutil --sb-state
```

An enrolled result and enabled Secure Boot establish this MOK enrollment only. The candidate UKI and
systemd-boot still require a separately staged, verified shim chain and hardware trial. Do not enroll
TPM unlock tokens, change BootOrder or treat P2 as passed from these two checks.

## Isolated production boot trial

This is the prepared P1/P2 handoff, not evidence of hardware acceptance. Continue the
[execution record](plans/2026-09-07-hermes-unattended.md#isolated-production-trial-preparation--2026-09-09).
The workstation bundle is private and contains boot images, no signing keys:
`/var/home/cloudops/.local/state/hermes-production-boot-inputs/20260909/trial-staging`.
Its four-image size is 101,076,296 bytes; require at least 102,124,872 free bytes plus entry-file space
on the live ESP. Recheck input hashes, Secure Boot, enrolled certificate, console and recovery access.

### Read-only staging gate

In the operator's sudo-capable SSH terminal, run the following without terminal recording. Return
public output and errors only. Passwordless sudo was previously unavailable to the automation session.

```bash
sudo efibootmgr -v
findmnt -no SOURCE,FSTYPE,TARGET /boot/efi
lsblk -o NAME,PATH,TYPE,PKNAME,PARTN,FSTYPE,MOUNTPOINTS
sudo bootctl status --no-pager
sudo bootctl list --no-pager
sudo ls -ld /boot/efi/EFI/hermes-trial-20260909 /boot/efi/loader
sudo find /boot/efi/loader -maxdepth 2 -type f -printf '%P\n'
df -B1 /boot/efi
mokutil --sb-state
mokutil --list-sbat-revocations
```

Missing trial/loader paths are expected on a clean staging target; distinguish those errors from
permission or I/O failures. Resolve the actual ESP disk and partition from this output; do not infer
it from a historical device name. Stop if BootNext is already set, the trial path exists unexpectedly,
Fedora's retained entry differs, the kernel inputs changed, or recovery access is unavailable.
Inspect existing loader configuration and entry identifiers privately before adding an entry;
record existing files and any LoaderEntryDefault/LoaderEntryOneShot values without changing them.

### Staging and trial sequence

1. Transfer only the four images and `SHA256SUMS` from the private bundle over the already pinned SSH
   connection to a fresh mode-0700 operator directory. Verify hashes there against the workstation
   manifest. Revalidate the current shim/MokManager and kernel/initramfs hashes against the prior
   binding. Copy under sudo only after the read-only gate passes.
2. Create `/boot/efi/EFI/hermes-trial-20260909` exclusively. Copy `shimx64.efi`, `mmx64.efi`,
   `grubx64.efi` and `hermes-production.efi` into that directory. Here `grubx64.efi` is the
   production-signed systemd-boot, matching the retained shim's inspected second-stage filename.
   Verify every destination hash against `SHA256SUMS` and flush writes. On partial failure, stop;
   reconcile the four exact paths before retrying. Never overwrite a mismatching existing file.
3. Add only the new, exclusive `/boot/efi/loader/entries/hermes-trial-20260909.conf` entry below.
   Preserve existing loader configuration and entries; create missing directories only after checking
   their actual type. This entry uses the UKI inside the dedicated directory, avoiding a new
   automatically discovered UKI in the shared `/EFI/Linux` directory.

```text
title Hermes production trial 20260909
efi /EFI/hermes-trial-20260909/hermes-production.efi
```

1. Review `bootctl list` to ensure that exact entry resolves. Record the original BootOrder and all
   existing Boot#### identities. With the verified ESP disk and partition, use `efibootmgr --create-only`
   with `--disk`, `--part`, `--label 'Hermes trial 20260909'` and
   `--loader '\EFI\hermes-trial-20260909\shimx64.efi'`. Determine the single newly created boot number
   by comparing inventories. Do not use ordinary `--create`, which changes BootOrder. Stop if the
   old BootOrder or any existing entry changed; restore the recorded BootOrder before proceeding.
2. At the physical console with the verified LUKS recovery credential, set `efibootmgr --bootnext`
   to that exact new number. Re-read firmware state: BootNext must match the new shim entry and
   BootOrder must match the baseline. Reboot once. Hold Space as systemd-boot starts and select
   **Hermes production trial 20260909**. Do not press `d` or edit the kernel command line.
   If the menu or exact entry is unavailable, return through the firmware's retained Fedora entry.
3. Unlock with the retained LUKS credential if prompted. No TPM token is enrolled by this procedure.
   After boot, collect `bootctl status --no-pager`, `uname -r`, `mokutil --sb-state`,
   `efibootmgr -v` and `systemctl --failed --no-pager`. Inspect measured-UKI/PCR and cryptsetup
   observations privately; do not export credentials or full initramfs contents. Require the selected
   UKI identity, expected kernel, Secure Boot enabled, consumed BootNext and unchanged BootOrder.
   A successful boot establishes only this trial; cold/update/tamper/recovery acceptance remains open.

The [systemd v259 documentation](https://github.com/systemd/systemd/blob/v259/man/systemd-boot.xml)
describes Type #1 EFI entries and the Space menu key. The
[shim loader protocol](https://github.com/rhboot/shim/blob/main/README.md#shim-loader-protocol)
describes second-stage image validation in shim 16.1; signatures alone do not prove this hardware path.
The [efibootmgr implementation](https://github.com/rhboot/efibootmgr/blob/main/src/efibootmgr.c)
distinguishes create-only from BootOrder insertion and provides BootNext selection/deletion.

### Cancel and recover

Before reboot, cancel this trial's pending BootNext with `sudo efibootmgr --delete-bootnext` only after
confirming it references the recorded trial entry. A failed boot may hang; one-shot selection does not
provide a watchdog. At the console reset if necessary and explicitly select the original Fedora entry,
then unlock with the retained recovery credential. Keep Secure Boot enabled and all existing keys.

After returning through Fedora, verify its original shim path, BootOrder, kernel and runtime health.
If trial BootNext remains, remove only that selection. Remove the newly recorded trial Boot#### with
`efibootmgr --bootnum` and `--delete-bootnum` only after verifying its label and exact isolated shim path.
Retain files for diagnosis until their hashes and ownership have been reconciled; later cleanup removes
only the four trial images and the one trial entry created above. Preserve pre-existing directories,
Fedora/fallback files, loader configuration and all unrelated EFI variables. Do not wipe or restore the
whole ESP for an isolated trial failure. Recovery restoration itself remains a separate P2 test.

### Prepared staging helper

After the 2026-09-09 privileged inventory passed, the fixed-input bundle and `stage-trial.sh` were
transferred to `/home/aicowork/.local/state/hermes-trial-20260909` over pinned SSH. The helper checks
source and live-input hashes, ESP identity/space, certificate enrollment and firmware baseline, then
creates the trial and loader directories exclusively. Partial runs require reconciliation before rerun.
It verifies destination hashes and unchanged firmware state; it neither sets BootNext nor reboots.

Run in the operator terminal and return output/errors; stop on any failure:

```bash
sudo bash /home/aicowork/.local/state/hermes-trial-20260909/stage-trial.sh
```

Expected final marker: `STAGING_OK: hashes verified; firmware unchanged; no reboot requested.`
The separately gated one-shot selection follows only after staging output is accepted.

For an early helper failure, use the same command with `--check-only` to run preflight without
ESP writes. Failures now report `STAGING_FAILED` with line number and exit status. Return that
output before retrying full staging; do not bypass a failed precondition.

The helper accounts for mokutil 0.7.2 exit semantics by requiring the exact enrolled-certificate
message and status 0 or 1. It uses read-only `--ignore-keyring` to test firmware enrollment only;
pending, blocked, not-enrolled and error results fail. Kernel keyring acceptance remains separate.

### Production trial firmware registration

The operator's staging output passed all hashes and firmware preservation checks. Independent SSH
confirmed no existing trial firmware entry. Run the following once; stop on a creation error and
return the inventory before retrying. This registers the isolated shim without selecting a reboot.

```bash
sudo efibootmgr --create-only --disk /dev/nvme0n1 --part 1 \
  --label 'Hermes trial 20260909' \
  --loader '\EFI\hermes-trial-20260909\shimx64.efi'
sudo efibootmgr -v
```

Require exactly one new trial Boot#### and BootOrder `0001,0007,0008,0003,0000,0002,0004,0005`,
with prior entries unchanged and no BootNext. Return the output to bind the one-shot selection to
that new number. Do not guess it or rerun creation. Console/LUKS recovery readiness is required
before the later BootNext and reboot step. If BootOrder changed, stop and restore the recorded
order before proceeding as described in the trial sequence.

### Registered trial one-shot handoff

The accepted registration allocated Boot0006 to the isolated shim. With physical console and
the retained LUKS recovery credential ready, select it for one boot:

```bash
sudo efibootmgr --bootnext 0006
sudo efibootmgr
```

Require BootNext 0006 and unchanged BootOrder `0001,0007,0008,0003,0000,0002,0004,0005`.
If either differs, stop before reboot. To cancel the confirmed trial selection, use
`sudo efibootmgr --delete-bootnext`. After the expected state is verified, run `sudo systemctl reboot`.
Hold Space as systemd-boot starts and select Hermes production trial 20260909. Use the retained
LUKS credential if prompted. If the trial fails or hangs, return through the firmware's original
Fedora Boot0001 entry, leaving Secure Boot enabled.

After returning, report console observations and collect:

```bash
sudo bootctl status --no-pager
uname -r
mokutil --sb-state
sudo efibootmgr -v
systemctl --failed --no-pager
```

The expected candidate kernel is 7.1.12-200.fc44.x86_64; kernel version alone cannot prove the trial
booted. Require loader/UKI evidence and consumed BootNext. Hardware acceptance remains pending
until observations are reconciled; TPM enrollment and the remaining P2 tests are separate gates.

### TPM trial capability diagnosis

The measured-UKI trial exposed a late NvPCR unseal failure (LoadExternal 0x2c4); the SRK and
early NvPCR initialization succeeded. Compare the live TPM's algorithm support before altering
the RSA-3072 PCR policy key. In the operator terminal, run these read-only capability checks:

```bash
sudo tpm2_testparms -T device:/dev/tpmrm0 rsa2048:rsassa-sha256
printf 'RSA2048 exit=%s\n' "$?"
sudo tpm2_testparms -T device:/dev/tpmrm0 rsa3072:rsassa-sha256
printf 'RSA3072 exit=%s\n' "$?"
```

Return output and both exit codes, including errors. These checks do not enroll keys or unseal
credentials. Unsupported RSA-3072 would support the compatibility hypothesis; successful tests
would require further public-key parameter diagnosis. Firmware-entry removal remains a separate
unresolved observation, not a reason to clear TPM state or replace EFI entries.

### RSA2048 candidate recovery prerequisite

The local compatibility candidate retains the existing Secure Boot certificate and all kernel,
initramfs, command-line and stub inputs, with a separate RSA2048 PCR policy key. Validation
is recorded in the canonical plan; it is not deployed or hardware-accepted.

Before another trial, preserve the existing encrypted NvPCR anchor from the volatile /run
location in protected storage and inventory its persistent/ESP copies without displaying or
decrypting contents. The standard /var/lib copy was absent during read-only diagnosis.
Changing the UKI PCR key alone does not migrate the old anchor credential. Review recovery
and any required rewrapping separately; do not clear TPM state, delete the anchor or assume
that a new successful boot establishes continuity of existing NvPCR bindings.

### Anchor recovery inventory

A protected workstation copy of the encrypted volatile anchor now exists, with matching remote
and local hashes. Its public header references the old RSA3072 PCR11 policy key. No plaintext
was recovered, so this backup alone does not establish recoverability. Before considering a
replacement anchor, inventory secondary copies and LUKS consumers without displaying secrets:

```bash
sudo find /boot/efi -type f -iname '*nvpcr*' -printf '%P %s bytes\n'
sudo cryptsetup luksDump --dump-json-metadata /dev/nvme0n1p3 | python3 -c 'import json,sys; d=json.load(sys.stdin); print("Token types:", {k:v.get("type") for k,v in d.get("tokens",{}).items()})'
```

Return only this filtered output and errors. The JSON is filtered directly; do not paste the
full LUKS metadata or any credential contents. Absence of a TPM LUKS token does not rule out
other NvPCR consumers. Do not reboot, delete the anchor or clear TPM state during inventory.

### RSA2048 replacement candidate staging

Use only the corrected `hermes-production-rsa2048-v2.efi` candidate, SHA256
`9ec0a06a4ac5fc556d8896d19f23146966ee87d66a1f54bc328b7f7f5ff63922`. The original local
RSA2048 file failed final identity/signature checks and was never transferred.
The new candidate and guarded helper are in the operator-owned staging directory. Run:

```bash
sudo bash /home/aicowork/.local/state/hermes-rsa2048-trial-20260909/stage-rsa2048.sh
```

Require RSA2048_STAGING_OK and the distinct Hermes RSA2048 trial 20260909 entry.
The helper preserves the old images and firmware selection; partial runs require inspection
before retry. Return output before setting BootNext or rebooting. The approved next boot
may generate a new NvPCR anchor; it is not migration of the preserved old encrypted anchor.

### RSA2048 one-shot trial

After RSA2048_STAGING_OK, with console and recovery passphrase ready, select both layers:

```bash
sudo bootctl set-oneshot hermes-trial-rsa2048-20260909.conf
sudo efibootmgr --bootnext 0006
sudo bootctl list --no-pager
sudo efibootmgr
```

Require the RSA2048 entry selected for the next boot and BootNext 0006, with BootOrder unchanged
from 0001,0008,0003,0000. Stop on any command error or mismatched selection. Then run
`sudo systemctl reboot`. At the menu choose Hermes RSA2048 trial 20260909 if prompted.
Use the retained LUKS passphrase; automatic unlock repair is separate. If the trial fails,
return via original Fedora Boot0001. On return collect:

```bash
sudo bootctl status --no-pager
systemctl --failed --no-pager
sudo journalctl -b -u systemd-tpm2-setup-early.service -u systemd-tpm2-setup.service --no-pager -n 35
sudo efibootmgr
sudo stat -c '%n size=%s mode=%a' /run/systemd/nvpcr/nvpcr-anchor.cred /var/lib/systemd/nvpcr/nvpcr-anchor.cred
sudo find /boot/efi -type f -iname '*nvpcr*' -printf '%P %s bytes\n'
```

Do not print or decrypt credential contents. Require the v2 UKI, measured boot and Secure Boot,
consumed one-shot selections, successful TPM services and persistent anchor evidence before
accepting the compatibility repair.

### TPM setup SELinux compatibility candidate

The RSA2048 trial's late setup service is blocked by SELinux anchor/log writes. Use the
[policy candidate and gated repair procedure](HERMES_SELINUX_TPM_REPAIR.md).
Local compilation does not close hardware persistence acceptance or authorize policy installation.
