# Hermes Fedora Server 44 installation verification

This is the dated evidence record for the Fedora Server 44 Hermes appliance.
The executable contract is documented in
[`HERMES_ONE_COMMAND_DEPLOYMENT_HANDOFF.md`](HERMES_ONE_COMMAND_DEPLOYMENT_HANDOFF.md).

## Current conclusion

**Local TPM unlock, 2026-09-18 local time:** additive SHA256 PCR7 enrollment passed
on the retained VM, preserving recovery slot 0. Reboot and verified powered-off
cold start both returned over pinned SSH without a console helper or key input.
Both services and Telegram returned automatically; memory and allowlist checks
passed. Secure Boot and SELinux enforcing remain enabled. The first initramfs
rebuild exposed missing `tpm2-tools`; installing that package and its FAPI dependency
resolved it before reboot. This is the manual PCR7 profile, not signed-UKI/PCR11
certification. See the [execution record](plans/2026-09-18-hermes-local-installation.md#automatic-tpm-unlock-follow-up)
and [current boot/recovery procedure](HERMES_LOCAL_VM.md#tpm-unlock-and-recovery).

**Local Telegram follow-up, 2026-09-18:** the user provisioned a bot token locally.
After gateway restart, Telegram `getMe` succeeded and the gateway reported
`Connected to Telegram`. One numeric user ID is configured, allow-all is disabled,
and the credential file is mode `0600`. Both containers remain running with no
published ports. The operator confirmed the exact `HERMES_TELEGRAM_OK` reply from
the authorized account, completing the end-to-end message test. A temporary allowlist
exclusion produced no reply after 30 seconds (operator-reported), with unauthorized
activity in gateway logs. The original allowlist was restored and the gateway
reconnected; the operator confirmed a reply after restoration, completing the
access-restriction test. User-provided screenshots confirm memory staging, exact-ID
approval and recall after `/new` through Telegram. A subsequent reboot changed
the boot ID, automatically restored both services and Telegram connectivity, and
preserved the allowlist and approved-memory file hash. The operator confirmed
correct fresh-session recall after reboot. Other approval flows remain untested. See the
[local operating guide](HERMES_LOCAL_VM.md#telegram-access).

**Local workstation fixture, 2026-09-18:** the retained `lab-hermes-server` VM now
has an 80 GiB disk and a dedicated encrypted-backed Hermes filesystem. Manual
gateway/worker installation and credential-free transport/hardening checks pass.
Post-installation reboot validation also passed: the data mount, both services
and actual worker routing survived the console-assisted reboot. The first supplied
provider credential received HTTP 401; its locally entered replacement passed exact
`HERMES_OK`, the worker tool round trip and bounded credential-isolation checks
using `openai-api` / `gpt-5.6-luna`. This is separate from production and promotion certification.
See the [local installation record](plans/2026-09-18-hermes-local-installation.md)
and [lifecycle guide](HERMES_LOCAL_VM.md).

**Memory follow-up, 2026-09-18:** the same pinned image passed the real CLI/gateway
memory staging, exact-ID approval/rejection and fresh-process recall checks. A
two-call model test accurately reported a staged write as not yet saved, then
recalled it after explicit approval in a fresh session. The earlier conclusion
that the queue was unusable was not reproduced and its operating guidance was
corrected. Approval remains enabled and the live user's queue was not modified.
See the [memory procedure](HERMES_MEMORY_APPROVAL.md) and
[source-bound evidence](plans/evidence/2026-09-18-hermes-memory-approval.json).

**2026-09-10 architecture review:** SE22 request metadata is complete; failure review passed while runtime
remains failed and its invocation is consumed. SE23–SE25 v3 preparation is preserved and paused. The
[dependency review and migration procedure](HERMES_TPM_DEPENDENCY_REVIEW.md) prepares the standard TPM2 path
with SRK setup retained. The 15:44 UTC operator inventory is received: selected-file/initrd/key hashes match,
root/generated options have no NvPCR/PCR-lock consumer, and expected unattended credential files are absent.
The 16:41 UTC root inventory closes the protected cron/user-service/Quadlet remainder with no hits or unresolved
paths. AR01 bounded review passes; arbitrary external integrations remain unproven. Live amended certification
and all B1–B7 production gates remain open. New local
preflight/credential/observer inputs invalidate candidate certification and promotion for those changed inputs.
AR04-L0/L1/L2 received explicit approval on September 10; that run failed baseline archive validation and
cleanup/restoration passed. The approved r2 attempt passed both real initrd checks and preparation, then failed
certification with a process-launch error; cleanup/restoration passed. The restricted child PATH lacks Restic/Trivy.
The [r2 live observation](plans/evidence/2026-09-10-hermes-standard-tpm2-r2-live.json) records the evidence and
prepared r3 package. Its separately approved run completed successfully on September 11 UTC: L0,
all seven existing certifier gates and L2/independent restoration passed.
[R3 live evidence](plans/evidence/2026-09-11-hermes-standard-tpm2-r3-live.json) records the consumed grant.
The full amended B1–B7 matrix and production P2–P4 remain open.

The [remaining lab package](HERMES_REMAINING_LAB_TESTS.md) is locally prepared on September 11: B3 first,
then separate B4/B7 operator cases with fresh identities, bounded time and exact cleanup. The user approved
B3 L0/L1/L2 only, and that single run passed. [B3 live evidence](plans/evidence/2026-09-11-hermes-b3-live.json)
binds all eight certifier gates to the fresh candidate: updated → previous → updated boots used three distinct
boot IDs with unchanged post-update packages, modules, credentials, PCR key and LUKS metadata. Both images
passed runtime/inference checks without reenrollment. Independent L2 restoration passed at 18:00:17Z,
71 minutes 28 seconds after block start and before the four-hour deadline. The B3 approval is consumed.
The scan passed its frozen advisory/denylist policy with 20 critical and 467 high findings retained.
The user subsequently authorized all pending tasks on September 11. B4-linux failed during its prerequisite
certification, before any tampering. Independent cleanup passed at 22:14:22Z, about 54 minutes after block start.
Later B4/B7 blocks remain blocked and unissued. The [continuation evidence](plans/evidence/2026-09-11-hermes-remaining-continuation.json)
records execution. [B4-linux evidence](plans/evidence/2026-09-11-hermes-b4-linux-live.json) retains the failure
and successful cleanup. A local reboot-transport correction is tested and a replacement package is prepared,
and the user subsequently authorized fresh bounded replacement runs without another approval pause.
R5 enrolled at 22:58:07Z and dispatched once at 22:58:24Z. Seven gates passed, then initial provider
revocation failed. Cleanup subsequently confirmed revocation; independent restoration passed on September 12
at 00:04:12Z, within four hours. No tamper test ran. The failure is retained while a bounded revocation
retry correction and fresh replacement are prepared.
[R5 live evidence](plans/evidence/2026-09-11-hermes-b4-linux-r5-live.json) retains the failed certification and cleanup.
R3/B3 evidence remains bound to its original inputs.
R6 dispatched once on September 12 at 00:12:21Z and passed all eight prerequisites. Trial preparation
then filled its 600-MiB EFI partition; no negative boot occurred. Exact recovery and independent cleanup
passed at 01:26:22Z, within four hours. A fresh replacement uses a 2048-MiB lab EFI partition and
pre-copy capacity checks. [R6 evidence](plans/evidence/2026-09-12-hermes-b4-linux-r6-live.json) preserves the failure.

R7 subsequently failed before installation; independent cleanup passed at 01:32:13Z.
R8 passed both resource checkpoints and dispatched once at 02:11:51Z on September 12.
Its B4-linux rejection/recovery and independent cleanup passed at 04:43:49Z, within four hours.
[Live evidence](plans/evidence/2026-09-12-hermes-b4-linux-r8-live.json) retains the exact result.
Fresh B4-initrd r9 dispatched once at 04:46:33Z; cleanup is due by 08:46:01Z.
All 13 operator templates
have a static preparation inventory; live acceptance and production gates remain open.

AR05/P2–P4 remain dependent on the full lab matrix and concrete production prerequisites. The UA-03/UA-04 statements below
are historical evidence for their exact September 8 lab candidate.

The unattended profile passed **UA-03 certification and UA-04 cleanup/signing** on 2026-09-08 UTC.
The [candidate-bound evidence](plans/evidence/2026-09-08-hermes-ua03-certification.json) records release
`ua03-cert-20260908-05`, its exact source/artifact identity and one consistent certification run.
[UA-04 evidence](plans/evidence/2026-09-08-hermes-ua04-cleanup-signing.json) records verified guest/data purge,
disposable backup/key removal, VM/recovery-disk/NVRAM/TPM destruction and exact-release signing.
Independent deployment-identity verification passed the signature, all 356 files and nine bound gates.
[UA-05 production enrollment](../vm/DEPLOYMENT_TASKS.md) remains pending; production was not accessed.

The signed archive is selected at `/var/lib/hermes-lab-unattended/releases/selected.tar`, with SHA-256
`618fd2bbb7bebecc313fc9873bb6a9c1396c24d2b36b9183c41e88f44f5dc559`.
Its first-use window is 2026-09-08 04:39:36 UTC through 2026-09-09 04:39:36 UTC.
The signature retains the exact lab host binding; it does not authorize deployment to another host.
For that September 8 cleanup, reusable signer/broker enrollment and sanitized observations remained;
the broker/socket was inactive, its runtime credential absent and temporary power privilege removed. Ancillary control cleanup
followed signing; the signed destruction gate already proved domain, disk, firmware and TPM absence.
Logical deletion is verified, not physical media sanitization. An unrelated existing sudoers permission
check fails for `/etc/sudoers.d/cloudops` (0644 rather than 0440); sudo syntax passes, and that file was unchanged.

The clean baseline replay installed the exact stored transaction of 329 RPMs and booted kernel
`7.1.13-200.fc44.x86_64`. Actual Hermes CLI inference returned exact `HERMES_OK` before and after
an independent persistence reboot. Powered-off cold boot, selected signed UKI, active TPM services,
SELinux enforcement, runtime isolation, read-only credentials, hardened agent configuration,
encrypted semantic backup restoration and nine rejection/rerun checks passed.
The prior encrypted credential was restored; provider deletion and HTTP 401 verification proved
revocation of the temporary test key. Both pinned SSH identities and final runtime observations passed.

The actual image scan passed the approved advisory/denylist policy, recording 20 critical and 457 high
package findings, plus other severities. This is not a vulnerability-free image; findings and the frozen
policy hash are retained in the certification evidence. The operator's upstream-only image decision
remains unchanged. The baseline's `mcelog.service` cannot support the VM's AMD processor; this retained
hardware-diagnostic limitation is outside Hermes runtime acceptance.

The [execution record](plans/2026-09-07-hermes-unattended.md#ua-03-completion-run) preserves the failed
and interrupted attempts, repairs, credential reconciliation and exact next gate. Repairs include
installing kernel packages before selecting their UKI, disabling frozen-payload bytecode writes,
checking persistence boot identity before runtime acceptance, waiting for runtime startup, preserving
primary/cleanup errors and retaining operator SSH access. The final source passed 128 unattended tests,
12 offline replay tests, 11 certifier tests, 138 ShellSpec examples and 217 guide checks.

Earlier [UA-02 runtime](plans/evidence/2026-09-07-hermes-ua02-runtime.json),
[real API acceptance](plans/evidence/2026-09-07-hermes-api-acceptance.json), and
[updated-kernel preparation](plans/evidence/2026-09-08-hermes-ua03-boot-preparation.json) observations
remain as fixture history, including prior-image recovery. They do not substitute for the fresh UA-03
run. Automatic fixture lifecycle integration and production hardware recovery remain separate work.
The dated production observations below concern the earlier interactive profile, not this new release.

### Scheduler validation (2026-09-08)

The [fresh scheduler observation](plans/evidence/2026-09-08-hermes-scheduler-live.json) records successful
certification through the installed service identity and sandbox. An explicitly approved, root-owned,
expiring lab grant permitted this Tuesday invocation; the ordinary off-window invocation deferred.
The run replayed 332 RPMs and passed updated/persistence/cold boots, exact inference, runtime isolation,
encrypted semantic restore and the frozen scan policy. All 350 candidate files and executed code hashes
were verified. A completed service rerun preserved the journals and revoked lease without recertifying.

An earlier issuance attempt failed closed. Independent provider reconciliation found no matching account,
and its failed journal remains retained. A fresh run succeeded; account deletion returned HTTP 200,
the key returned HTTP 401, and final independent reconciliation found neither attempted account.
Guest/data purge, fresh backup/key removal, VM/disk/NVRAM/TPM destruction and temporary service/grant
removal passed. The broker/socket is stopped and its runtime administrative credential is absent.
These are logical deletion observations, not physical media sanitization.

The scan passed the existing advisory/denylist policy with 20 critical and 458 high findings retained.
No new release was signed, and production and the earlier signed archive were not changed.
Calendar-triggered execution was not exercised. Prior S4 evidence remains specific to its source and
candidate; the separate F4 observations below establish the automatic fresh-fixture lifecycle.

### Fresh lifecycle validation (campaign 2026-09-08; closure 2026-09-09 UTC)

**F4 passed.** The [live evidence](plans/evidence/2026-09-08-hermes-lifecycle-live.json) records two
successful fresh cycles (`5d49e5f4…` and `58aca82b…`) with distinct machine, SSH, candidate and UKI
identities under the same lifecycle source. Both passed all seven acceptance gates, provider revocation,
independent teardown and completed-run idempotency. Fixture absence was verified between runs.

The single controlled fixture (`e2ab090d…`) received its test credential before the one-time grant was
removed and its service was killed. Automatic cleanup ran without the grant, revoked the key, purged
private material and destroyed the VM/disk/NVRAM/TPM state. The run remains failed and uncertified.
Independent provider listing confirmed all five issued test accounts absent; both successful journals
remained unchanged. No additional full cycle was used after the bounded authorization and no fixture
was repeated under that allowance.

Temporary grants, service, sudo rule, power helper and diagnostic entrypoints were removed. Broker policy
and socket were restored byte-for-byte; the broker is stopped and its runtime administrative credential
is absent. All run-private paths and fixture resources are absent. The preexisting pool definition and
reviewed dormant source/service installation remain. The prior signed archive hash is unchanged;
production and release signing were untouched. Both recurring timers remain absent/inactive, and the
normal Sunday 02:00 Bogotá schedule still resolves to 2026-09-13 07:00 UTC. Enablement is not authorized.

The [execution record](plans/2026-09-07-hermes-unattended.md#f4-final-closure) preserves failures, repairs,
source generations and limits. Earlier source evidence does not certify subsequently repaired paths.
The first successful cycle used the earlier scanner launcher; the second success and six focused tests
cover the revised bounded transport-retry wrapper. The pinned scanner binary and advisory/denylist policy
were unchanged; 20 critical and 458 high findings remain on the second success. The original scanner
stderr for two failed runs was unavailable, so independently reproduced transport failures cannot prove
each run's exact cause. Three early pre-credential failures lack standalone contemporaneous independent
cleanup reports; original cleanup and later absence checks are retained. Logical deletion is verified,
not physical sanitization. Calendar-triggered execution and production hardware recovery remain untested.

### Historical production profile (2026-09-01)

As of 2026-09-01, final-source certification run `run-20260901T183122Z` passed
every certification and cleanup gate and issued strict-valid mode-`0600`
promotion record
`/var/home/cloudops/.local/state/hermes-certification/promotion-20260901T183122Z.record`.
The record matches provider `openai-codex`, model `gpt-5.6-luna`, the pinned
image, and the current artifact fingerprint.

The previous production installation was purged with `rollback --purge-fresh`,
then a new production deployment bound the final-source record to
`aicowork@10.0.30.10`. `PROD-01` through `PROD-06` are `PASS`: provider
acceptance and exact authenticated `HERMES_OK` completed, the controller
closed, and the direct read-only status reports `health=healthy`,
`readonly=true`, `ports={}`, and `drift=none`. The secret-free evidence is in
the private production ledger. Historical failures and their repairs remain
below as evidence; there is no current production blocker.

The successful final-source run passed signed-media verification, installation,
update, runtime, SSH recovery, three independently ordered encrypted reboots,
provider acceptance, exact authenticated `HERMES_OK`, final drift-free status,
provider revocation, fresh-data purge, fixture-privilege removal, and VM
destruction.
The certifier exited, the domain is absent, and both dedicated storage files
are absent. Strict validation confirms the record matches provider
`openai-codex`, model `gpt-5.6-luna`, the pinned image, and the current
certification artifact fingerprint.

The previous post-close failure and its deterministic root-cause replay remain
retained. The repair maps absent optional state to `unbound` or
`unconfigured`, reports only allowlisted drift identifiers, performs bounded
post-close convergence, and retains a mode-`0600`, secret-free diagnostic on
failure. The model writer now updates all compatible default-model fields, and
`rollback --purge-fresh` clears stale local deployment and promotion state so
the next deploy starts the full fresh path. The controller suite passes 127
examples and the complete Hermes/VM ShellSpec suite passes 138 examples.

The target contract is Fedora Server 44 x86_64, LUKS-backed storage, UEFI
Secure Boot, enforcing SELinux, firewalld, cgroup v2, Podman 5.8.4 or newer,
and an SSH-only host boundary. The production target remains
`aicowork@10.0.30.10` on management CIDR `192.168.99.0/24` through `eno1`.

## Evidence and progress protocol

This document is the canonical, secret-free evidence ledger. The executable
task list is [`vm/DEPLOYMENT_TASKS.md`](../vm/DEPLOYMENT_TASKS.md). A task may
be marked `PASS` only when its documented pass condition and evidence path both
exist. Terminal recollection or a correct-looking event count is not enough.

Offline checks write mode-`0600` command output below a timestamped progress directory:

```bash
progress_dir="/var/home/cloudops/.local/state/hermes-certification/progress-$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 0700 "$progress_dir"
set -o pipefail

devbox run -- shellspec spec/vm/luks_console_spec.sh 2>&1 \
  | tee "$progress_dir/01-luks-console-shellspec.log"
devbox run -- shellspec spec/hermes/deploy_spec.sh 2>&1 \
  | tee "$progress_dir/02-deploy-shellspec.log"
devbox run -- chmod 0600 "$progress_dir"/*.log
```

The complete command set and filename mapping are in the task list. Do not
pipe the interactive certifier through `tee` or `script`: provider output may
contain an OAuth URL, device code, API key prompt, or other credential material.
The certifier instead retains sanitized evidence below
`/var/home/cloudops/.local/state/hermes-certification/run-<UTC timestamp>/`.

Expected run artifacts are:

- `media-verification` and `checksum-signature.log` for Fedora media.
- `vm-create.log` for installation, initial unlock, and SSH recovery.
- `unlock-monitor.log` for reboot, cryptsetup boundary, and prompt events.
- `controller-state/hermes-deploy/lab_172.16.99.12/stage-*` for completed stages.
- `vm-failure.log` and `vm-failure-screen.ppm` when a run fails.
- `status.log`, `guest-facts`, and `vm-destroy.log` on the successful path.
- A separate mode-`0600` promotion record only after acceptance and verified cleanup.

## Current verification snapshot

| Check | Most recent evidence | Result |
| --- | --- | --- |
| Documentation synchronization | 217 guide checks, Markdown lint, doc audit, and diff check | `PASS` |
| Focused LUKS watcher replay | `11 examples, 0 failures` on 2026-08-31 | `PASS` |
| Provider/controller ShellSpec | `127 examples, 0 failures`, including model and fresh-rollback regressions | `PASS` |
| Complete offline gate | `138 examples, 0 failures`; guide, syntax, lint, and format checks pass | `PASS` |
| Failure cleanup | Known failed-run certifier PIDs, domain, QCOW2, and OEMDRV absent | `PASS` |
| Lab preflight | 4 CPUs, 10,391,838,720 available bytes, 354,603,245,568 free bytes, clean lab | `PASS` |
| Fresh reboot-marker VM run | `run-20260831T212756Z`; validator accepted all three ordered sequences | `PASS` |
| Exact authenticated inference | Provider and inference acceptance stages in `run-20260831T212756Z` | `PASS` |
| Post-close status repair | Deterministic red/green replay; focused suite passes 5 examples | `PASS` |
| Fresh repaired VM certification | Final status, revocation, purge, fixture removal, and destruction passed | `PASS` |
| Historical promotion record | `promotion-20260831T212756Z.record`; valid only for the pre-repair tree | `PASS` |
| Production host adoption | `HOST_ADOPTED` observed; durable state recorded in the private progress ledger | `PASS` |
| Production read-only preflight | Exact `PREFLIGHT_OK` after root expansion and listener hardening | `PASS` |
| Production sudo bootstrap repair | Red/green cross-TTY regression plus full offline gate | `PASS` |
| Four-argument preflight repair | Red/green update-mode regression plus full offline gate | `PASS` |
| First repaired-tree certification attempt | `run-20260901T015813Z`; safe failure and cleanup verified | `FAIL` |
| Second repaired-tree certification attempt | `run-20260901T022455Z`; all machine gates passed, auth timed out | `FAIL` |
| Superseded repaired-tree certification | `run-20260901T034903Z`; source changes later changed its fingerprint | `PASS` |
| Final-source certification | `run-20260901T183122Z` and matching mode-`0600` record | `PASS` |
| Fresh production deployment | Previous installation purged, final-source record bound through `stage-closed` | `PASS` |
| Production persistence | Direct read-only status: healthy, read-only, port-free, drift-free | `PASS` |

## 2026-09-01 final-source certification and clean production deployment

The repaired-tree record from `run-20260901T034903Z` became ineligible when
the model/default-state and fresh-rollback source changes altered the certified
artifact fingerprint. `LAB-07` therefore recertified the final source as
`run-20260901T183122Z`. It passed all machine, provider, acceptance, cleanup,
purge, and destruction gates before issuing
`promotion-20260901T183122Z.record` with mode `0600`.

`PROD-05` ran `rollback --purge-fresh` directly against the production host.
Read-only probes confirmed the old installer-created Hermes identity and data
were removed, and the controller retained only the rollback marker needed to
start a new deployment. `PROD-06` then completed a new device-authorized
production deployment with the final-source record. The controller closed with
provider `openai-codex`, model `gpt-5.6-luna`, and a bound promotion record.
Its direct read-only status reports `health=healthy`, `readonly=true`,
`ports={}`, and `drift=none`; the temporary root helper and temporary sudo rule
are absent.

Two failed workstation terminal attempts exposed a sudo entry because a piped
confirmation consumed standard input while sudo still needed a terminal. Those
task terminals were closed; the successful retry used a masked local dialog.
No credential material is retained in this repository or the evidence ledger.
Rotate the affected `aicowork` sudo password before additional privileged work.

## 2026-09-01 production sudo bootstrap blocker

The first `PROD-03` invocation passed exact `PREFLIGHT_OK` and verified the
SHA-256 of four uploaded helper artifacts. It then failed with
`sudo: a password is required` before displaying the production mutation
confirmation. The controller had authenticated sudo in one SSH pseudo-terminal,
then opened a separate pseudo-terminal for helper bootstrap and invoked
`sudo -n`. Fedora's TTY-scoped sudo timestamp did not carry into that new
terminal, and `-n` prohibited the required prompt.

Read-only cleanup verification found no executable deployment helper, no
remaining `/tmp/hermes-deploy.*` artifact owned by `aicowork`, no running
deployment process, no local deployment-stage or promotion-binding file, and
no non-interactive sudo authorization. The attempt therefore performed no
production package mutation, provider authentication, or reboot.

The bootstrap now invokes interactive sudo inside its own SSH terminal. After
that one prompt installs the narrow `/usr/local/libexec/hermes-deploy-root`
rule, all later root actions remain non-interactive and constrained to that
helper. A regression first reproduced the five-argument
`sudo -n /usr/bin/bash -c` call, then passed with the four-argument
`sudo /usr/bin/bash -c` call. Bash parsing, ShellCheck, repository shfmt,
52 controller examples, 135 combined Hermes/VM examples, and all 217 guide
checks pass.

The promotion gate also worked as intended: the historical record contains
the certified pre-repair artifact fingerprint, while the repaired tree has a
different fingerprint because `scripts/hermes/deploy-lib.sh` is in the signed
artifact set. Do not reuse or weaken that record. Fresh task `LAB-06` must
certify the repaired tree and issue a matching record before `PROD-03` resumes.

## 2026-09-01 first LAB-06 attempt

Fresh repaired-tree run `run-20260901T015813Z` passed the offline gates,
signed-media verification, Fedora installation, initial encrypted unlock, and
SSH recovery. Its deployment preflight then reported two prerequisites as
unavailable: Podman 5.8.4 and the `dnf5-automatic` timer. The certifier exited
78 before Hermes identity creation, provider authentication, or inference.

The failure was deterministic. Production deployment supplies four arguments
to `remote-preflight.sh`: management CIDR, interface, update permission, and
the host module. The parser assigned `ALLOW_UPDATE` only when the argument
count was exactly three, so the valid four-argument call silently retained
`ALLOW_UPDATE=0` and rejected prerequisites the deploy path is responsible for
installing. `REG-07` changes that condition to accept three or more arguments.

The regression first reproduced `allow-update=0` and a failed four-argument
preflight, then passed with update mode enabled. Bash parsing, ShellCheck,
repository shfmt, 52 controller examples, 135 combined Hermes/VM examples,
and all 217 guide checks pass. The failed run retained mode-`0600` sanitized
diagnostics. Its certifier process is absent, `lab-hermes-server` is absent
from `qemu:///system`, and both dedicated storage paths are absent. No
promotion record was issued. At that point, `LAB-06` remained pending for a
fresh rerun against the repaired parser.

## 2026-09-01 second LAB-06 attempt

Fresh run `run-20260901T022455Z` passed 135 ShellSpec examples, all 217 guide
checks, signed-media verification, Fedora installation, initial encrypted
unlock, and exact deployment `PREFLIGHT_OK`. It installed the missing
`dnf5-automatic` package contract, updated Fedora 44 and Podman from 5.8.1 to
5.8.4, created the fresh identity, pulled the digest-locked image, applied host
and runtime hardening, and passed credential-free and root acceptance.

Encrypted reboot evidence also passed exactly: one initial prompt submission,
three reboot markers, three boot boundaries with `input-submitted=0`, and
three verified prompts with `input-submitted=1`. The controller emitted
`ENCRYPTED_REBOOT_EVIDENCE_OK watched_boots=3` before provider authentication.
This confirms `REG-07` cleared the prior machine blocker.

At `AUTHENTICATION_READY`, the readiness input was submitted on the managed
certifier terminal. Provider login was not completed in the browser within the
device-login window. No provider-acceptance or inference stage was written,
and sanitized diagnostics record controller exit 78 at phase
`post-reboot-credential-free`. This is an unmet external authentication gate,
not a machine-gate regression.

The run failed closed. The certifier process is absent,
`lab-hermes-server` is absent from `qemu:///system`, both exact storage files
are absent, all retained run diagnostics are mode `0600`, and no promotion
record exists for `run-20260901T022455Z`. Production was not contacted.
At that point, `LAB-06` remained pending for a fresh run while the operator
was available to complete the displayed browser login.

## 2026-09-01 production preflight blocker

The reinstalled production host was adopted successfully, but its first
read-only check found two blockers. The root logical volume was 15 GiB total
with about 11.36 GiB available under `/var`, so deleting cached files alone
could not meet the required 20 GiB free. The operator expanded the LV to 40
GiB and grew XFS; a fresh direct check now reports 37,620,468 KiB available
(about 35.9 GiB), clearing the storage blocker.

The same check observed TCP and UDP port 5355 on non-loopback addresses and
TCP port 9090. `systemd-resolved` reported LLMNR enabled, and
`cockpit.socket` was listening. The operator applied the host hardening policy;
a fresh direct read-only check now shows LLMNR disabled, `cockpit.socket`
inactive and masked, and no non-loopback listeners beyond SSH. The full check
then returned exact `PREFLIGHT_OK`. No production package mutation, provider
authentication, or reboot was started. The sanitized operator ledger is
`/var/home/cloudops/.local/state/hermes-certification/progress-production-20260901T004057Z/STATUS.md`.

The workstation controller status-reporting defect exposed by this attempt was
also repaired: failed remote preflight status is now preserved after temporary
file cleanup, and the installed-helper path fails closed as well.

The stale provider-readiness fixture was repaired with three ordered
`luks-reboot-observed` events. The original replay failed with 44 examples and
one failure; the repaired replay passed all 44 examples. The complete offline
suite then passed all 127 examples. A parallel Devbox invocation failed before
ShellSpec started because its generated `.cmd.sh` file disappeared; the
failure and the successful isolated retry are both retained. This was an
execution-environment race, not a suppressed test failure.

## 2026-08-31 successful repaired certification

Run directory:
`/var/home/cloudops/.local/state/hermes-certification/run-20260831T212756Z`.

- Fedora's signed checksum and the exact expected DVD SHA-256 passed before VM
  creation.
- Fedora Server 44, kernel `7.1.12-200.fc44.x86_64`, Podman 5.8.4, and the
  digest-pinned Hermes image were recorded in `guest-facts`.
- `unlock-monitor.log` passed the shared validator with one initial unlock and
  exactly three independent reboot, encrypted-root boundary, and prompt
  sequences.
- `stage-provider-acceptance` and `stage-inference-acceptance` prove provider
  acceptance and a complete response equal to exact `HERMES_OK`.
- `status.log` reports `health=healthy`, `readonly=true`, `ports={}`,
  `drift=none`, and `drift_reasons=none`.
- `stage-auth-revoked` and `stage-rollback` completed. The successful certifier
  path then verified that the fresh Hermes identity and temporary fixture sudo
  file were absent before destroying the VM.
- `vm-destroy.log` records cleanup. The certifier PID, libvirt domain, QCOW2
  disk, and OEMDRV image are absent.
- The certifier issued
  `/var/home/cloudops/.local/state/hermes-certification/promotion-20260831T212756Z.record`
  with mode `0600`. Strict validation against the provider, model, image, and
  current artifact fingerprint exits zero. Its first-use window expires at
  `2026-09-01T22:22:17Z`.
- No `status-failure.log` or `vm-failure.log` exists for this run. Production
  was not touched.

This closes `LAB-03` through `LAB-05`. Continue with `PROD-01` through
`PROD-04` in order while the record remains valid for first use.

## 2026-08-31 readiness-fixture repair and offline gate

Evidence directory:
`/var/home/cloudops/.local/state/hermes-certification/progress-fix-20260831T193144Z`.

- `01-reg02-red.log` reproduces the stale readiness fixture failure.
- `02-reg02-green.log` records `44 examples, 0 failures` after adding one
  reboot marker before each watched cryptsetup boundary.
- `10-shellspec-all.log` retains the parallel Devbox `.cmd.sh` race and exit
  status 127.
- `10b-shellspec-all-retry.log` records the isolated successful retry:
  `127 examples, 0 failures`.
- `11-hermes-guide.log` records 217 checks passed and zero failed.
- `12-bash-syntax.log` through `16-markdownlint.log` record successful Bash
  syntax, Python compilation, ShellCheck, shfmt, and Markdown checks.
- `20-lab-preflight.log` retains the failed nested-quoting wrapper attempt;
  no VM state changed.
- `20b-lab-preflight-retry.log` records the successful standalone preflight:
  resource thresholds passed, required inputs were readable, and the exact
  disposable domain and storage paths were absent.
- `LAB-03` and `LAB-04` later passed in `run-20260831T194212Z`.
- `REG-04` now passes. Its retained red replay reproduces the strict-pipeline
  exit on absent optional state, and the green replay verifies safe defaults,
  allowlisted drift reasons, bounded convergence, and a mode-`0600` certifier
  diagnostic.
- `REG-05` passes with 132 ShellSpec examples plus the guide, Bash syntax,
  Python compilation, ShellCheck, shfmt, Markdown, and diff checks.
- The then-pending proof obligation was later satisfied by
  `run-20260831T212756Z`.

## 2026-08-31 post-close-status repair

Evidence directory:
`/var/home/cloudops/.local/state/hermes-certification/progress-status-fix-20260831T205707Z`.

- `01-reg04-red.log` proves the old controller returned the first transient
  post-close status failure without retrying.
- `05-reg04-wrapper-reason-red.log` deterministically reproduces wrapper exit 2
  at the first absent optional state-file read.
- `06-reg04-wrapper-reason-green.log` verifies that absent binding and
  promotion files now produce `unbound` and `unconfigured`, while real drift is
  reported by an allowlisted reason identifier.
- `08b-reg04-certifier-diagnostic-green.log` verifies the certifier retains a
  mode-`0600`, secret-free status failure artifact.
- `10-reg04-exhaustion-red.log` retains the bounded-exhaustion diagnostic
  regression; `11-reg04-focused-final-green.log` passes all 5 focused examples.
- `12-deploy-shellspec.log` passes all 49 controller examples, and
  `13b-shellspec-all-retry.log` passes all 132 repository examples.
- The initial complete run and lint/format attempts are retained alongside
  their successful isolated retries. No failure was erased or reclassified as
  a pass.

This repair did not touch production. Its proof obligation was later satisfied
by `run-20260831T212756Z`.

## 2026-08-31 post-close-status certification attempt

Run `run-20260831T194212Z` produced the following secret-free evidence:

- Fedora media verification passed. The unattended install powered off after
  765 seconds, the initial LUKS prompt was verified once, and SSH recovered in
  six seconds.
- Controller stages prove update, runtime, credential-free acceptance, the
  planned Hermes reboot, and post-reboot credential-free acceptance completed.
- `unlock-monitor.log` contains one initial prompt followed by exactly three
  reboot, encrypted-root boundary, and verified-prompt sequences. The shared
  validator exits zero with `initial=1 watched=3 boundaries=3 monitor_ready=1`.
- Provider and authenticated inference acceptance completed. The controller
  writes `stage-inference-acceptance` only after the inference acceptance script
  returns success, and that script succeeds only when the complete response is
  exactly `HERMES_OK`.
- Wrapper installation and `stage-closed` completed. The controller then exited
  nonzero before returning from `deploy`, so the certifier never reached its
  separate unlock-evidence check, `status.log`, or `guest-facts` writes.
- The controller's last operation after `stage-closed` is `status_command`.
  Code order and artifacts therefore localized the failing boundary to the
  final post-close status call. After cleanup, a controlled replay established
  the exact cause: optional binding and promotion reads used unguarded
  `sed | tail` pipelines, and the first absent file terminated the wrapper.
- Failure diagnostics captured the still-running VM. Cleanup then recorded
  `stage-auth-revoked` and `stage-rollback`. The certifier PID, domain, QCOW2,
  and OEMDRV are absent, and no promotion record exists.

This run resolves the reboot-association and authenticated-inference questions.
The post-close defect it exposed is repaired and covered offline. Production
remains blocked because only a fresh disposable run can prove final status,
successful-path cleanup, VM destruction, and promotion-record issuance.

## 2026-08-31 reboot-association certification attempt

Run `run-20260831T171430Z` produced the following secret-free evidence:

- Deterministic installer kernel arguments booted the Server DVD without timed
  keyboard injection. Installation powered off after 835 seconds, the initial
  LUKS prompt was unlocked once, and SSH recovered.
- The 778 MiB DNF5 update completed, Fedora 44 and Podman 5.8.4 were verified,
  the digest-pinned runtime passed credential-free and root acceptance, and SSH
  recovered after the persistence reboot.
- The event log recorded one initial prompt and three watched prompts. It also
  recorded cryptsetup boundaries at `17:33:16Z`, `17:33:30Z`, and
  `17:46:28Z`. The `17:33:30Z` boundary was a same-boot redraw; it incorrectly
  armed the prompt later observed at `17:41:22Z` after the next real reboot.
- Because the then-current validator checked counts and local ordering without
  requiring a reboot marker, the transcript superficially satisfied
  `initial=1 watched=3 boundaries=3 monitor_ready=1`. It did not prove three
  reboot-to-prompt sequences.
- The run was stopped before OAuth. Durable state reaches
  `stage-post-reboot-credential-free` but contains no `stage-oauth` or
  `stage-model-configured`. Failure cleanup recorded `stage-auth-revoked` and
  `stage-rollback`.
- Diagnostics were captured while the VM was running. Cleanup subsequently
  removed the domain, QCOW2 disk, and OEMDRV image; all three are absent.

The minimized replay now includes an explicit reboot marker before each
cryptsetup boundary. The watcher emits `luks-reboot-observed input-submitted=0`
and accepts only this sequence for each watched boot:

```text
luks-reboot-observed input-submitted=0
luks-boot-boundary-observed input-submitted=0
luks-prompt-verified input-submitted=1
```

The shared validator independently enforces the same sequence and exact count.
The focused replay passes 11 examples. The provider-readiness fixture remains
red because it still supplies boundaries and prompts without reboot markers.

## 2026-08-31 operator-gate certification attempt

Run `run-20260831T061910Z` produced the following secret-free evidence:

- Installation powered off after 755 seconds. The initial encrypted boot,
  update, runtime, root acceptance, and persistence checks completed.
- Its watcher transcript contains the same invalid association pattern: a
  second cryptsetup boundary appeared 12 seconds after the first watched
  prompt, while the next prompt arrived more than seven minutes later.
- The persistent watcher ended after its six-hour timeout with three watched
  submissions. Controller state later reached `stage-oauth`,
  `stage-post-auth-hardening`, and `stage-model-configured`, then recorded
  `stage-auth-revoked` and `stage-rollback`.
- The exact post-model failure line was present only in the interactive terminal
  and was not retained in the sanitized run directory. This is an explicit
  evidence gap: the run is failed/incomplete, and no cause beyond the durable
  stage boundary is inferred.
- Operator instructions were ambiguous enough that `START-AUTH` was entered in
  an unrelated Bash shell at least once. `START-AUTH` is input for the waiting
  certifier terminal, not an executable command. The prompt now states that
  distinction before and during the readiness loop.
- No exact `HERMES_OK` or promotion record was produced. Provider revocation,
  rollback, VM destruction, and both storage removals were verified.

## 2026-08-31 ellipsized-unit certification attempt

Run `run-20260831T054115Z` produced the following secret-free evidence:

- The frozen gate passed 121 ShellSpec examples, 214 guide checks, Python
  compilation, ShellCheck, formatting, and Markdown lint. Fedora's signed
  checksum and expected DVD SHA-256 also passed.
- The unattended installation powered off after 750 seconds. The exact initial
  LUKS prompt received one fixture submission, SSH returned in six seconds, the
  persistent watcher reported `monitor-ready`, prerequisites were installed,
  and host policy converged.
- The complete 778 MiB DNF5 transaction was downloaded and staged. On its
  update reboot, the retained screen showed the encrypted-root unit and exact
  prompt, but the event log contained no watched boundary or submission.
- A read-only memory snapshot of the watcher established the exact normalized
  mismatch without sending guest input. systemd had middle-ellipsized the long
  escaped unit as `systemd-cryptsetup@luks\x…<UUID-tail>` and placed an ANSI
  reset between the ellipsis and retained hexadecimal UUID tail. Temporary
  debugger and screenshot files were removed after extracting this secret-free
  fact.
- The controller exhausted its 900-second reconnect budget. Provider
  authentication never started, no Hermes identity was created, `HERMES_OK`
  was not attempted, and no promotion record was issued.
- Diagnostics were captured before cleanup. The certifier removed the libvirt
  domain, QCOW2 disk, and OEMDRV image; all three absences were verified.

The exact captured ANSI-plus-UTF-8-ellipsis replay failed deterministically
before the repair with `first=no second=no verified-events=0 boundaries=0`.
The classifier now supports the complete `luks\x2d...` and plain-hyphen forms,
plus `luks\x…` only when the retained UUID tail begins with hexadecimal data.
It still requires `Starting systemd-cryptsetup`, the exact passphrase prompt,
and one boundary per submission. Generic progress and same-boot redraws remain
rejected. At that stage, the focused suite passed 11 examples and the complete
ShellSpec suite passed 122 examples.

## 2026-08-31 in-place-status certification attempt

Run `run-20260831T050246Z` produced the following secret-free evidence:

- The frozen gate passed 120 ShellSpec examples, 214 guide checks, Python
  compilation, ShellCheck, formatting, and Markdown lint. Fedora's signed
  checksum and expected DVD SHA-256 also passed.
- The unattended installation powered off after 745 seconds. The exact initial
  LUKS prompt received one fixture submission, SSH returned, prerequisites and
  host policy converged, and the DNF5 update was staged.
- The persistent watcher was attached and reported `monitor-ready` before the
  controller began. On the first update reboot, the retained console screenshot
  showed `Starting systemd-cryptsetup@luks...` followed by the exact LUKS
  prompt. The event log nevertheless recorded no watched boundary and no input
  submission.
- The controller exhausted its 900-second update-reconnect budget and failed
  closed. Provider authentication never started, no Hermes identity was
  created, `HERMES_OK` was not attempted, and no promotion record was issued.
- Diagnostics were captured before cleanup. The certifier then removed the
  libvirt domain, QCOW2 disk, and OEMDRV image; all three absences were verified.

The minimized replay models an in-place Fedora status repaint immediately
before the visually exact cryptsetup start. It deterministically failed before
the repair with `first=no second=no verified-events=0 boundaries=0`. The parser
had required `Starting` to occur at the raw buffer start or directly after a
carriage return or newline. It now searches for the exact
`Starting systemd-cryptsetup@luks...` marker independently of preceding repaint
residue, while still requiring the exact passphrase prompt and clearing the
buffer after one submission. Generic path-units progress and same-boot prompt
redraws remain rejected. At that stage, the focused suite passed 10 examples
and the complete ShellSpec suite passed 121 examples.

## 2026-08-31 post-unlock-boundary certification attempt

Run `run-20260831T042140Z` produced the following secret-free evidence:

- The frozen gate passed 120 ShellSpec examples, 212 guide checks, Python
  compilation, ShellCheck, formatting, and Markdown lint. Fedora's signed
  checksum and expected DVD SHA-256 also passed.
- The unattended install powered off after 745 seconds. The exact initial LUKS
  prompt received one fixture submission, SSH returned, prerequisites and host
  policy converged, and the 778 MiB DNF5 transaction completed with
  `UPDATE_VERIFIED podman=5.8.4 fedora=44`.
- The same preattached watcher submitted exactly once for the offline-update
  boot, post-update boot, and persistence reboot. The digest-pinned runtime
  passed credential-free and root acceptance both before and after persistence.
- Fedora emitted `Reached target paths.target - Path Units.` again seven to
  eleven seconds after each successful unlock. Those post-unlock lines re-armed
  the then-current classifier, so the final transcript contained three watched
  submissions but four boundary events.
- The controller rejected the transcript with
  `initial=1 watched=3 boundaries=4 monitor_ready=1` before
  `AUTHENTICATION_READY`. OAuth never started, `HERMES_OK` was not attempted,
  and no promotion record was issued.
- Failure cleanup revoked all three provider slots and purged the fresh Hermes
  identity. Direct `sudo /usr/bin/rm` could not remove the fixture rule because
  that rule authorizes `/usr/bin/bash`; fallback cleanup therefore destroyed
  the domain, QCOW2 disk, and OEMDRV image.

The minimized replay now includes a path-units line before cryptsetup, the
encrypted-root `Starting systemd-cryptsetup@luks...` line, the exact prompt,
and another path-units line after submission. The watcher arms only on the
cryptsetup start and ignores both generic progress markers. This produced a
deterministic red test before the repair and passes afterward while retaining
the duplicate-redraw checks. Fixture cleanup now streams a fixed `rm` script to
`sudo -n /usr/bin/bash -s`, exactly matching the disposable VM's sudo rule, and
verifies absence afterward. At that stage, the complete ShellSpec suite passed
120 examples.

## 2026-08-31 quiet-boot-boundary certification attempt

Run `run-20260831T034451Z` produced the following secret-free evidence:

- Fedora's signed checksum and expected DVD SHA-256 passed, followed by the
  complete frozen offline gate.
- The unattended Server 44 installation completed, the exact initial LUKS
  prompt received one fixture submission, SSH returned, prerequisites were
  installed, host policy converged, and a 778 MiB DNF5 update was staged.
- The update reboot reached Fedora's quiet serial-console boundary,
  `Reached target paths.target - Path Units.`, followed by the exact LUKS
  prompt. The then-running watcher recognized only `Linux version ...`; it
  correctly sent no input and recorded no false unlock event.
- The 900-second update reconnect gate expired before provider authentication.
  OAuth never started, `HERMES_OK` was not attempted, and no promotion record
  was issued.
- Failure diagnostics retained VM state and a console screenshot. Verified
  cleanup removed the domain, QCOW2 disk, and OEMDRV image.

An exact quiet-boot replay failed before that parser change and passed after it.
That iteration treated the observed path-units line as a per-boot boundary and
retained `Linux version ...` as a verbose-boot fallback. The later
post-unlock-boundary run proved that neither marker pair uniquely identifies an
unlock cycle and superseded that classifier. A separate regression found that the controller's intended
two-second reconnect timeout preceded a 15-second general SSH option and was
therefore overridden; the short timeout now appears last and its effective
value is tested. At that stage, the complete ShellSpec suite passed 120 examples.

## 2026-08-31 prompt-boundary certification attempt

Run `run-20260831T021443Z` produced the following secret-free evidence:

- Fedora's signed checksum and expected DVD SHA-256 passed, followed by the
  complete frozen offline test gate.
- The unattended installation completed, and the DNF5 offline transaction
  reached `UPDATE_VERIFIED podman=5.8.4 fedora=44`.
- The digest-pinned runtime passed credential-free acceptance and
  `ROOT_ACCEPTANCE_OK` before and after the persistence reboot.
- The one-shot installer unlock submitted once. The persistent watcher then
  submitted twice for the offline-transaction boot, three times for the
  post-update boot, and three times for the persistence boot. Each group was
  recorded in the same second, proving same-boot redraws rather than additional
  reboot cycles.
- The controller reached `AUTHENTICATION_READY provider=openai-codex`. The run
  was intentionally stopped there: `START-AUTH` was not entered, OAuth never
  started, no device code was issued, and no account credential was used.
- Signal cleanup revoked all provider slots, purged the fresh Hermes identity,
  and retained diagnostics. A remote `bash -c` argument-boundary defect made
  fixture-privilege cleanup unverifiable, so the fallback destroyed the exact
  VM, domain definition, QCOW2 disk, and OEMDRV image. No promotion record was
  issued.

The minimized PTY replay now models normal boot output between the first prompt
and its same-boot redraw. It went red deterministically on three consecutive
runs. That iteration made the watcher start disarmed, re-arm after an observed
boot boundary, trim stale same-boot output, and record each boundary. The later
reboot-association run proved that cryptsetup output alone was still not a
unique reboot identity; the current reboot-marker sequence supersedes that
classifier. The controller invokes the shared validator before exposing
`AUTHENTICATION_READY`, and the certifier invokes it again before promotion
work. The fixture cleanup now invokes `/usr/bin/rm` directly across SSH. The
complete ShellSpec suite at that stage passed with 120 examples.

## 2026-08-31 OAuth-timeout certification attempt

Run `run-20260831T011307Z` produced the following secret-free evidence:

- Fedora's signed checksum was accepted and the DVD matched the expected
  SHA-256.
- The DNF5 offline transaction completed with
  `UPDATE_VERIFIED podman=5.8.4 fedora=44`.
- The digest-pinned runtime passed `ACCEPTANCE_VERIFIED mode=credential-free`
  and `ROOT_ACCEPTANCE_OK` before and after the persistence reboot.
- One preattached watcher unlocked the offline transaction boot, the normal
  post-update boot, and the persistence reboot. SSH returned after each boot.
- The controller reached ChatGPT/Codex authentication. Hermes reported
  `Login timed out after 15 minutes`; provider authentication did not complete,
  `HERMES_OK` was not reached, and the certifier exited with status 78.
- Failure cleanup ran rollback and fresh-data purge, destroyed the VM, and
  removed both `lab-hermes-server.qcow2` and
  `lab-hermes-server-oemdrv.iso`. No promotion record was issued.

This attempt first exposed two deterministic reliability defects. Provider
authentication started before confirming that the operator was present, and a
redraw of one LUKS prompt produced a duplicate submission event. It motivated
the typed `START-AUTH` gate and the initial redraw replay. The later
prompt-boundary run showed that re-arming on arbitrary console progress was
still too permissive.

## 2026-08-30 certification attempt

The earlier attempt produced the following terminal evidence:

- Fedora's signed checksum was accepted and the DVD matched the expected
  SHA-256.
- The DNF5 offline transaction completed with
  `UPDATE_VERIFIED podman=5.8.4 fedora=44`.
- The digest-pinned runtime passed `ACCEPTANCE_VERIFIED mode=credential-free`
  and `ROOT_ACCEPTANCE_OK`.
- The next persistence reboot failed with
  `host did not return after the credential-free Hermes reboot`.
- Failure cleanup destroyed `lab-hermes-server`. Provider authentication had
  not started, and no promotion record was issued.

The failure exposed an encrypted-reboot timing and observability gap. The
certifier now runs a preattached console-unlock watcher, allows ten minutes
for certification reconnects, records unlock attempts, captures sanitized VM
state and a console screenshot before cleanup, and identifies a created Hermes
identity from durable controller state. ShellSpec, guide consistency,
ShellCheck, formatting, and Markdown checks pass after that repair. A fresh
end-to-end run remains the authoritative acceptance test.

## Required certification evidence

The certifier must capture, without secrets:

- Fedora Server DVD checksum and signed-checksum verification result.
- Fedora version, kernel, Podman version, and pinned Hermes image digest.
- Exact provider/model and an authenticated response equal to `HERMES_OK`.
- Successful service health and persistence checks.
- Ordered encrypted-boot evidence: one installer unlock plus three sequences of
  fresh reboot marker, encrypted-root cryptsetup boundary, and one prompt
  submission.
- Revocation of all supported provider credentials.
- Purge of fresh Hermes identity/data.
- Destruction of `lab-hermes-server` before promotion-record issuance.

The promotion record contains only identifiers, timestamps, hashes, versions,
and boolean cleanup results. It is mode `0600`, expires 24 hours after issue,
and is bound on first production use to the target's SSH ED25519 fingerprint
and `/etc/machine-id` hash.

## Evidence-producing commands

### Disposable VM

```bash
cd /var/home/cloudops/code/repos/mikrotik

./hermes-certify-vm.sh \
  --iso /var/home/cloudops/Downloads/Fedora-Server-dvd-x86_64-44-1.7.iso \
  --checksum /var/home/cloudops/Downloads/Fedora-Server-44-1.7-x86_64-CHECKSUM \
  --fedora-keyring /var/home/cloudops/Downloads/fedora.gpg \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --provider openai-codex \
  --model gpt-5.6-luna
```

After `ENCRYPTED_REBOOT_EVIDENCE_OK watched_boots=3` and
`AUTHENTICATION_READY provider=openai-codex`, the standing operator preference
authorizes Codex to submit `START-AUTH` automatically when Codex owns the
managed certification terminal. Codex must suppress the write result and stop
reading terminal output before authentication details appear. The operator
still completes the provider login; this preference does not authorize Codex
to handle credentials or approve production changes. The 15-minute
device-login timer starts only after the readiness response.

Expected DVD SHA-256:
`85837793bfa36db6bc709b4cecd2ec116951b87d9c53c3d95eb2fac8dcf7cf1f`.

### Production adoption and read-only preflight

```bash
./hermes-deploy.sh adopt-host \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 \
  --interface eno1

./hermes-deploy.sh check \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 \
  --interface eno1
```

Adoption requires typing `ADOPT-HERMES-HOST`. `check` is read-only and does not
create deployment state.

### Production deployment

```bash
./hermes-deploy.sh deploy \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 \
  --interface eno1 \
  --provider openai-codex \
  --model gpt-5.6-luna \
  --promotion-record /absolute/path/to/promotion.record
```

The operator must type `CONFIRM-HERMES-PRODUCTION` before package mutation and
planned reboots. Provider authentication and the final `HERMES_OK` acceptance
remain manual account gates.

## Provider and billing evidence

| Provider | Auth flow | Billing boundary | Default model |
| --- | --- | --- | --- |
| `openai-codex` | ChatGPT/Codex device OAuth | Subscription access | `gpt-5.6-luna` |
| `openai-api` | Secure API-key prompt | OpenAI API usage billing | `gpt-5.6-luna` |
| `nous` | Nous Portal OAuth | Nous Portal account | `anthropic/claude-sonnet-4.6` |

OpenAI subscription access and OpenAI API usage billing are separate. The
controller never accepts an API key as a command-line argument and never writes
credential material to deployment state or a promotion record.

## Verification status

| Gate | Status | Evidence required |
| --- | --- | --- |
| Signed, expected Server 44 media | Verified | 2026-08-31 signature and checksum logs |
| DNF5 update and Podman 5.8.4 | Verified in 2026-08-31 runs | `UPDATE_VERIFIED podman=5.8.4 fedora=44` |
| Credential-free runtime and root acceptance | Verified in 2026-08-31 runs | `ACCEPTANCE_VERIFIED` and `ROOT_ACCEPTANCE_OK` |
| Persistence reboot behavior | Verified | Latest run proved three reboot-boundary-prompt sequences |
| Focused encrypted-boot replay | Verified after repair | 11 examples pass with reboot-marker ordering enforced |
| Provider/controller ShellSpec | Verified | 127 examples pass, including model and fresh-rollback regressions |
| Ordered encrypted-boot evidence | Verified | Latest run has one initial unlock and three ordered watched sequences |
| Provider authentication and `HERMES_OK` | Verified stage | Inference stage can exist only after exact-response acceptance succeeds |
| Post-close status repair | Verified offline | Exact strict-pipeline failure reproduced; 5 focused examples pass |
| Historical repaired certification | Verified | `run-20260831T212756Z` passed final status and successful-path cleanup |
| Credential revocation and fresh-data purge | Verified | Successful run contains revocation and rollback stages |
| VM destruction before record | Verified | Domain and both dedicated storage files were absent before record issuance |
| Historical promotion record | Verified for pre-repair tree | Mode-`0600` record no longer matches repaired fingerprint |
| Production host adoption | Verified | `HOST_ADOPTED`; private progress ledger records the operator confirmation |
| Production read-only preflight | Verified | Exact `PREFLIGHT_OK` after root expansion and listener hardening |
| Production sudo bootstrap repair | Verified offline | Cross-TTY red/green replay passes |
| Four-argument preflight repair | Verified offline | Update-mode red/green replay and complete suite pass |
| Second repaired-tree attempt cleanup | Verified | Auth-window failure left no process, domain, storage, or record |
| Superseded repaired-tree certification | Verified historical evidence | `run-20260901T034903Z`; source changes later altered the fingerprint |
| Final-source certification | Verified | `run-20260901T183122Z` and strict-valid matching record |
| Fresh production deployment and read-only status | Verified | Purged prior installation; closed controller reports healthy, read-only, port-free, drift-free |

Historical deployment evidence is retained separately under
[`docs/archive/`](archive/) and is not a substitute for this Server 44
certification.

## Unattended staged candidate continuation (2026-09-07)

The [execution record](plans/2026-09-07-hermes-unattended.md) tracks public guest boot export,
installed UKI construction, candidate freeze and injection. Offline evidence does not supersede the
historical production observations above. At the start of this continuation, the local libvirt
inventory was empty and UA-02 was blocked. The later lab observations below supersede that initial
state; they do not authorize production changes.

## Privileged review and dedicated TPM lab (2026-09-07)

The full source boundary review and repairs passed 116 Python tests, 138 ShellSpec examples,
217 guide checks and changed shell lint/format checks.
[Review evidence](plans/evidence/2026-09-07-privileged-boundary-review.json) preserves failures and results.
The dedicated TPM2/Secure Boot VM passed public guest-input extraction, workstation UKI construction,
injection/readback and automatic pinned-SSH boot. Altering the signed UKI caused explicit firmware
rejection on both EFI paths. Offline recovery-key access and automatic boot after restoring the
verified UKI also passed, with a fresh boot ID, Secure Boot enabled and SELinux enforcing.
[Live evidence](plans/evidence/2026-09-07-hermes-tpm-handoff.json) records this repaired staging run.

The [isolated lab signer](plans/evidence/2026-09-07-hermes-lab-signer.json) is enrolled with distinct
identities and root-owned reviewed code. Actual permission checks and rejection of an empty handoff
passed; no release was signed. Its static unit has no production trigger. The recovered VM is shut
off and its dedicated recovery material remains private.

UA-02 remains blocked on isolated broker enrollment inputs and remaining fixtures. Credential
lifecycle/revocation, semantic restore, clean UA-03 certification and UA-04 cleanup are unpassed.
These observations do not constitute complete certification. Production remains unchanged.

### 2026-09-07 isolated broker credential observation

The [lab broker observation](plans/evidence/2026-09-07-hermes-lab-broker.json) records actual encrypted
credential delivery, isolated user-scoped encryption, fixed test-project access, one disposable
account issue/reread/reuse, successful key authentication, deletion and HTTP 401 revocation proof.
Production is explicitly disabled in this lab policy; deployment and signing identities cannot use
its socket. The encrypted lease was removed. No production change or promotion occurred.
UA-02 remains incomplete pending runtime credential delivery and semantic application restoration;
UA-03/UA-04 certification is not established by this credential fixture.

## 2026-09-08 production enrollment continuation

The operator authorized pending UA-05 work and confirmed rotation of the existing `aicowork`
password. This is operator confirmation, not independent password verification. The initial
read-only SSH connection to `10.0.30.10` timed out before authentication; no production changes
occurred. The workstation route uses VLAN 70 while the documented SSH boundary is management
VLAN 99. Restore approved management access before continuing P1 in the
[canonical execution record](plans/2026-09-07-hermes-unattended.md#production-continuation--2026-09-08).
Hardware enrollment, boot/recovery validation and deployment remain unpassed.

Subsequent live pinned SSH succeeded: Fedora 44, SELinux enforcing, firewalld active, TPM2 present,
and Secure Boot enabled. Current loader is GRUB 2.12 with `Measured UKI: no`; ESP inventory
requires sudo authentication. Connectivity is restored; privileged inventory and physical recovery
validation remain pending. See the P1 continuation in the canonical execution record. No boot changes made.

Operator subsequently reported LUKS credential test exit 0 and BootCurrent 0001 using Fedora shimx64.efi.
This establishes credential acceptance, not an offline recovery boot. Boot/header backups and signed
production UKI enrollment remain pending; the canonical execution record links the backup procedure.

Operator reports the three local boot/header backup checksum checks passed in
`/root/hermes-boot-recovery.VoP66t50`. Independent off-host verification and recovery restoration
remain pending; details and next action are in the canonical execution record.

Off-host backup verification subsequently PASS: all three SHA-256 hashes independently matched
on the workstation, destination/files have private permissions, and LUKS header magic plus archived
Fedora shim/GRUB/kernel entries were checked. Private evidence and exact next action are in the
canonical plan. No restoration, boot change or production UKI enrollment has been performed.

Production package/trust preparation continued with pinned SSH: full filtered MOK and firmware
PK/KEK/db certificate inventory was observed, while ownership of the existing `grub` MOK and custom
PK remains unknown. Required boot packages are absent; cached candidate versions are provisional.
Package file resolution failed due to missing updates metadata, and privileged inventory requires
operator sudo authentication. The [boot input procedure](HERMES_UNATTENDED_DEPLOYMENT.md#production-boot-input-preparation)
provides the exact next inventory. P1 remains open; no package installation or boot mutation occurred.

Operator ESP inventory subsequently confirmed the active Fedora shim entry and 619,642,880 bytes free.
Refreshed package file resolution and downloads passed after mirror timeouts; three RPM signatures
passed on Hermes and workstation copies matched SHA-256. Unsigned EFI stub/manager were extracted
locally and SBAT metadata inspected. Full input/trust binding and hardware boot/recovery gates remain
open; exact hashes and the next live-file comparison are in the canonical execution record.

Production boot-file binding subsequently PASS: all four operator-provided live hashes matched
the retained backup kernel, initramfs, shim and MokManager. Private build copies and evidence are
recorded in the canonical plan. Initramfs suitability, signing trust and physical boot/recovery
remain unverified; production boot state is unchanged.

Production initramfs static checks and local signed-candidate construction passed. The TPM driver
is built into the kernel; PCR phase ordering and UKI signature handoff files are present. Candidate
UKI/manager signatures and sections passed; only the public signing certificate was staged on Hermes.
MOK enrollment awaits the operator console handoff in the canonical procedure. No hardware boot
acceptance, firmware change or TPM enrollment was performed; see the canonical plan for artifact identities.

Production MOK presence subsequently verified by pinned SSH: exact candidate certificate reports
already enrolled, pending-import list is empty and Secure Boot is enabled. Existing Fedora boot path
is operator-reported unchanged. Kernel keyring access warning persists; hardware candidate boot
remains untested. See the canonical plan for the next isolated-chain staging gate.

### Isolated boot trial preparation — 2026-09-09

Local preparation verified both production signatures and retained image hashes, and assembled a
private four-image staging bundle (101,076,296 bytes). The shim binary contains the expected
`grubx64.efi` second-stage filename. The [trial procedure](HERMES_UNATTENDED_DEPLOYMENT.md#isolated-production-boot-trial)
preserves Fedora defaults and specifies staging, one-shot selection and recovery. Live privileged
ESP/loader inventory is required before copying files or selecting a trial. No hardware acceptance,
production staging, reboot or TPM enrollment was performed by this preparation.

### Production trial staged

Operator output confirms the isolated images and Type #1 entry are staged with matching hashes
and unchanged firmware state. Independent pinned SSH confirms retained Fedora BootCurrent/BootOrder
and no BootNext. Firmware registration is next; measured-UKI hardware boot and P2 acceptance
remain pending. See the canonical execution record for the preserved failed attempts and repair.

### First production measured-UKI trial result

The operator booted the isolated systemd-boot/stub and UKI with Secure Boot enabled, measured
UKI reported and BootCurrent 0006. Manual LUKS unlock was used; production TPM unlock has
not been enrolled by this workflow. Initial hardware chain acceptance passes, but P2 remains
open: systemd-tpm2-setup failed with Esys_LoadExternal 0x000002c4 during unsealing, and four
prior firmware entries disappeared with BootOrder reduced to `0001,0008,0003,0000`.
Independent pinned SSH confirms the service failure and changed firmware inventory. Causes
remain unverified. See the execution record for the exact next read-only diagnosis; do not
clear TPM state or claim successful unattended boot.

### TPM policy algorithm incompatibility evidence

Operator TestParms comparisons accept RSA2048:RSASSA-SHA256 and reject RSA3072:RSASSA-SHA256.
The installed tool's version-matched source confirms this rejection follows a TPM response,
not an unsupported CLI argument. The live PCR policy key is RSA3072, strongly supporting
a compatibility cause for LoadExternal failure. Repair and existing NvPCR credential migration
remain untested; no TPM reset, key replacement or UKI replacement has been performed.

### Local RSA2048 candidate prepared

A separate 99,025,920-byte UKI passed local signature/section validation with an embedded
RSA2048 PCR public key. All original input hashes and the Secure Boot certificate are unchanged;
the previous candidate is preserved. No production artifacts changed. Metadata inspection finds
the volatile encrypted NvPCR anchor but no standard /var/lib copy. Anchor preservation and
recovery review gate the next hardware trial; no migration or automatic unlock is verified.

### RSA2048 hardware boot and SELinux blocker

The v2 RSA2048 UKI booted with Secure Boot and measured boot; firmware BootOrder was
preserved relative to this trial baseline. Early NvPCR initialization succeeded and late
setup wrote the encrypted anchor under /var/lib. The service still failed: an independently
observed SELinux AVC denied init_t creation of the ESP credential (dosfs_t). Separate AVCs
deny writes to the TPM measurement log (syslogd_var_run_t). The ESP is mounted read-write.
Full persistence acceptance remains blocked on a reviewed SELinux compatibility repair;
Enforcing, existing keys/tokens and encrypted backups remain intact.

### SELinux compatibility diagnosis

Executable and measurement-log contexts match the installed Fedora 44.8 policy. The
observed init_t/dosfs_t denial matches upstream bug 2507393. Open PR 3321 introduces
a dedicated but permissive domain; it is not an accepted enforcing repair. No label,
policy or mount mutation was performed. A dedicated enforcing policy candidate and
validation against the installed policy remain required before the persistence gate closes.

### Enforcing SELinux candidate offline validation

A dedicated enforcing TPM setup candidate compiles and links in an isolated Fedora 44.8 store.
Nineteen permission checks and the exact executable context mapping passed; init_t ESP/log grants
are unchanged. The copied production policy differs from the clean package baseline, and its
root-owned module store is unreadable over unprivileged SSH. Exact-store compatibility remains
blocked on operator input; no production module, label, service or TPM state changed.
See [offline evidence](plans/evidence/2026-09-09-hermes-selinux-candidate.json) and the
[candidate, permission scope and recovery procedure](HERMES_SELINUX_TPM_REPAIR.md).

### Exact installed-store validation passed

Operator export SHA256 matched the pinned transfer. Rebuilding the unmodified installed store
produced the exact current host-policy hash; the candidate linked in a separate copy and passed
all 19 permission assertions plus executable context mapping. See the
[exact-store observation](plans/evidence/2026-09-09-hermes-selinux-exact-store.json).
The fixed-hash policy installation helper is prepared for review. No production installation,
relabel, restart, TPM operation or reboot occurred; UA-05/P2 hardware acceptance remains blocked
on the explicitly approved trial in the [repair guide](HERMES_SELINUX_TPM_REPAIR.md).

### Production SELinux policy installed

Operator helper reports successful installation. Independent pinned SSH confirms the exact expected
on-disk merged policy hash, dedicated executable context and SELinux Enforcing. The late service
still has its prior failed status and has not been restarted. Loaded-policy verification and private
off-host recovery copies precede the approved runtime trial; UA-05/P2 remains open.
See the [canonical execution record](plans/2026-09-07-hermes-unattended.md).

### Loaded-policy and off-host recovery gates passed

Pinned transfers match both operator hashes. The expected and kernel-exported policies have different
binary hashes but identical checkpolicy CIL output and matching seinfo properties/counts. Direct checks
confirm the loaded init transition and enforcing candidate domain. Recovery archive validation confirms
policy and encrypted runtime/persistent anchors are preserved off-host. Full sediff was stopped for
resource use and is not claimed as passing. See the
[loaded-policy observation](plans/evidence/2026-09-09-hermes-selinux-loaded-policy.json).
The verified first-run service helper is staged; runtime acceptance and cold boot remain untested.

### First service trial failed; evidence recovery required

Pinned SSH confirms the late service ran on 2026-09-09 at 09:43:14–09:43:16 -05 and exited 1.
Its journal reports permission denied during the XBOOTLDR block-device probe. The helper then failed
on its ausearch date format, masking the service result and losing unsaved in-memory observations.
SELinux remains Enforcing with the expected candidate policy and executable label. No retry is permitted
by the failed first-run gate. Read-only audit/recovery collection is staged; see the
[repair guide](HERMES_SELINUX_TPM_REPAIR.md). No denial cause or persistence success is assumed.

### Failed-trial recovery preserved; rollback pending

Pinned archive transfer and encrypted-anchor hashes verify the operator recovery record. Independent
comparison of its before/current snapshots confirms preserved SRK, anchors, LUKS metadata, firmware,
loaded policy, label and Enforcing. The ESP anchor is absent. Scoped AVCs prove the dedicated domain
ran and was denied namespace getattr, certificate-directory search and fixed-disk block-device read.
Original audit continuity remains unknown, not confirmed lost. The guarded policy rollback is staged
under the approved failed-trial recovery procedure; no rollback or service retry has run yet.
See the [recovery observation](plans/evidence/2026-09-09-hermes-selinux-recovery.json).

### Failed SELinux trial rolled back

The operator helper reports the trial module removed and rollback verified. Independent pinned SSH
confirms the original on-disk policy hash, init_exec_t executable context/mapping and Enforcing.
The late service retains its 09:43:14–09:43:16 -05 failed invocation, with no newer start recorded.
The [rollback observation](plans/evidence/2026-09-09-hermes-selinux-rollback.json) records verification limits.
Recovery backups remain preserved. UA-05/P2 is still blocked; revised-policy design and offline validation
precede any proposal for another production trial.

### Revised SELinux candidate local preparation — 2026-09-09

Candidate 1.1.0 adds namespace metadata, certificate-directory traversal and read-only fixed-disk
probing permissions. The copied exact host store rebuilds to the recorded original baseline hash;
compilation/linking and all 31 permission/delta assertions pass. Evidence is recorded in the
[canonical execution record](plans/2026-09-07-hermes-unattended.md). This is local evidence only.
The [revised proposal](HERMES_SELINUX_TPM_REPAIR.md#revised-installation-proposal) documents raw-device
read exposure and a separate backup directory. No production write, service retry or reboot occurred.
UA-05/P2 remains blocked on runtime and persistence acceptance.

### Revised policy installation approved and staged

The user approved v2 policy installation, read-only loaded-policy/backup verification and bounded
policy recovery. Pinned SSH confirms the recorded baseline and idle setup processes. Reviewed
artifacts and the export helper are staged with matching hashes. Installation is blocked on interactive
operator sudo; no installation or restart is claimed. Follow the
[operator handoff](HERMES_SELINUX_TPM_REPAIR.md#approved-v2-operator-handoff) and
[staging evidence](plans/evidence/2026-09-09-hermes-selinux-v2-staging.json).

### Revised policy installation and export verified

SE7/SE8 pass: pinned SSH confirms the reviewed disk policy, dedicated label and Enforcing; exported
hashes match the operator. Safe private backups retain the original store and encrypted anchors, with
anchor hashes matching preserved recovery evidence. Loaded-policy CIL and properties/counts match
the reviewed policy, with direct transition/domain checks. See the
[installed observation](plans/evidence/2026-09-09-hermes-selinux-v2-installed.json).
The late service retains its prior failed invocation; no revised runtime result or cold boot is claimed.
The next gate is a separately reviewed and approved v2 late-service trial. UA-05/P2 remains open.

### Guarded v2 single-service trial prepared locally — 2026-09-09

SE9–SE10 pass: the separate v2 helper pins the verified policy and recovery baseline, requires a single
exclusive trial, and preserves private observations across collection failures. All 32 synthetic offline
tests and syntax checks pass; the property parser also passed a read-only workstation systemd check.
The [preparation evidence](plans/evidence/2026-09-09-hermes-selinux-v2-service-preparation.json)
retains the failed empty-property regression and the corrected D-Bus verification approach.
The [proposed scope and exact handoff](HERMES_SELINUX_TPM_REPAIR.md#approved-v2-single-service-trial)
await explicit approval for staging and one late-service invocation. No Hermes probe or production mutation
occurred. Revised runtime, repeat/idempotency and cold-boot acceptance remain open; UA-05/P2 is still blocked.

### Guarded v2 single-service trial approved and staged — 2026-09-09

The user approved private staging, one console-supervised late-service invocation with its TPM/encrypted-anchor
effects, and read-only result review. SE12 passes: pinned SSH confirms the reviewed live unprivileged
baseline, and the exclusively staged mode-0600 helper in the mode-0700 directory independently hashes
to the approved bytes. See the [staging observation](plans/evidence/2026-09-09-hermes-selinux-v2-service-staging.json).
The late service retains its prior failed invocation. Interactive operator sudo is required; no new service
trial or reboot has run. Privileged preflight and runtime results remain pending. Follow the
[approved operator command](HERMES_SELINUX_TPM_REPAIR.md#approved-v2-single-service-operator-handoff) once,
with physical console and manual recovery available, and return only the sanitized summary.
No new approval is needed for this scope. UA-05/P2 remains blocked; repeat/idempotency and cold-boot
acceptance are separate open gates.

### V2 preflight failure and local dependency fix — 2026-09-09

Operator reports the original helper hash verified and a preflight RuntimeError with service_requested=false.
SE13 validation fails before a reported service request. Pinned live checks independently confirm unchanged
late/early invocation IDs and timestamps, idle processes, Enforcing and the reviewed disk-policy hash.
A required root mount named -.mount exposes a missing -- in the helper's dependency query; systemctl rejects
it as an option. The local correction passes 33 tests and the corrected live read-only query returns active.
The failed regression and historical helper bytes are preserved in the
[failure observation](plans/evidence/2026-09-09-hermes-selinux-v2-preflight-failure.json).
Root-private evidence is still needed to attribute the original stop; follow the
[read-only diagnostic](HERMES_SELINUX_TPM_REPAIR.md#read-only-v2-preflight-diagnosis).
No corrected source was staged, no trial guard was reset and no new service invocation or reboot occurred.
UA-05/P2 and runtime/repeat/cold-boot acceptance remain open.

### Protected v2 preflight review complete; continuation prepared

The operator read-only diagnostic reports before.json present, audit/process/restart markers absent,
and Command failed: systemctl while rechecking the original preflight. Together with independent root-mount
option parsing reproduction and unchanged live invocation IDs, this completes SE14 failure review.
SE13 remains a failed preflight and runtime acceptance remains unperformed.

SE16 continuation preparation and 52 offline tests pass. The wrapper pins the original failed evidence
and corrected core, requires unchanged state, preserves the old directory, reserves a separate single-use
directory and retains the original runtime acceptance rules. Existing approval still covers one real
service invocation, which has not occurred; no repeat, recovery or reboot is added. Follow the
[continuation procedure](HERMES_SELINUX_TPM_REPAIR.md#guarded-v2-continuation) after its staging gate passes.
See the [continuation observation](plans/evidence/2026-09-09-hermes-selinux-v2-continuation.json).
SE17 documentation/command checks and SE18 private staging pass. Independent pinned SSH verifies both
new hashes and private modes plus the unchanged original helper. Operator execution remains blocked on
interactive sudo; no service invocation or reboot occurred. Runtime/repeat/cold-boot gates remain open.

### Guarded continuation stopped in preflight — 2026-09-09

The operator reports both copied hashes verified, followed by a preflight RuntimeError at
2026-09-09T23:39:18.235067+00:00 with service_requested=false. SE18 preflight validation fails; runtime
remains unperformed. Independent pinned SSH confirms unchanged late/early invocation identities, idle
processes, Enforcing, disk-policy hash and all staged helper hashes. The precise failing guard is unknown.

SE19 review awaits protected saved diagnostics and snapshot field differences. The
[read-only diagnostic](HERMES_SELINUX_TPM_REPAIR.md#read-only-continuation-failure-diagnostic) reads only
existing JSON and needs interactive operator sudo. No new helper or attempt is prepared after this second
preflight failure. Preserve both consumed result directories. See the
[failure observation](plans/evidence/2026-09-09-hermes-selinux-v2-continuation-failure.json).
UA-05/P2 and runtime/repeat/cold-boot gates remain open; no new service invocation or reboot was observed.

### Continuation failure isolated to audit query

The operator saved-file diagnostic identifies query_audit as the failing operation after state/policy/unit
preflight. Old/new snapshots and unit fields match. Audit status reports enabled=1, pid=1182, lost=0 and
backlog=0; the first query fails before journal/recovery-copy/service-request stages. The exact ausearch
failure remains unknown until its saved return code/stderr/output shape are inspected. Audit daemon health
does not establish query success or absence of denials. Follow the
[audit metadata diagnostic](HERMES_SELINUX_TPM_REPAIR.md#audit-query-metadata-diagnostic) and retain the
[failure observation](plans/evidence/2026-09-09-hermes-selinux-v2-continuation-failure.json).
No source or production change occurred; both attempts remain consumed and runtime/cold-boot gates open.

### Audit continuation prepared after metadata review

SE19 diagnosis is complete: saved exit 1 with empty raw output matches the recorded Audit 4.2.1 output
contract, but the old query input provenance was unverified. SE20 correction passes 74 offline tests and
requires forced configured-log input plus an explicit default-format no-match confirmation. Synthetic
installed-binary probes validate formatting only; privileged audit acceptance remains pending.
Fresh pinned SSH confirms unchanged unit identities, policy, labels and packages. The subsequent SE21
staging observation below completes the private-staging gate under the existing one-real-invocation approval.
Both failed attempts remain preserved. Runtime, repeat/idempotency and cold-boot gates remain open.

### SE21 audit continuation privately staged — 2026-09-10

At 13:11 UTC the new audit wrapper was exclusively created in the existing operator-private directory.
Independent pinned SSH readback verified its reviewed hash, mode 0600, regular single-link type and owner;
the directory remains mode 0700. All three previous helper hashes and both service invocation fields
match the pre-staging baseline. Fresh Enforcing, policy, label, package and root-mount checks passed.
See the [durable observation](plans/evidence/2026-09-09-hermes-selinux-v2-audit-continuation.json).

The source and three test-file hashes still match the recorded 74-test pass; no implementation changed.
Only the operator-owned audit wrapper was created. No helper was executed, service requested or reboot
performed. Root-private attempt/loaded-policy/anchor guards and privileged live-log acceptance await the
already approved single invocation. Interactive operator sudo is unavailable to the noninteractive session.
Run the [console handoff](HERMES_SELINUX_TPM_REPAIR.md#v2-audit-continuation-operator-handoff) once and return
only the sanitized summary. UA-05/P2, runtime, repeat/idempotency and cold-boot acceptance remain open.

### SE22 audit continuation ran and failed — 2026-09-10

Operator summary timestamp 13:25:13 UTC reports service_requested=true and passed=false, 22 scoped AVCs,
observed hermes_tpm2_setup_t and no collection errors. Restart/service acceptance, no-AVC and ESP-anchor
gates fail; the other 20 reported checks pass, including preservation and audit integrity. These are
operator-reported observations pending read-only review of the retained denial records.

Pinned SSH independently confirms new late invocation 65b49476a60341369fd98bf447db9984, start at
08:25:08 -05, exit 1 and idle processes. The early unit, Enforcing, disk policy, labels, packages and
all staged helper hashes are unchanged. Root-private evidence is unreadable and noninteractive sudo
is unavailable. See the [failure observation](plans/evidence/2026-09-10-hermes-selinux-v2-runtime-failure.json).

SE22 runtime validation ❌ FAIL; review is 🚧 BLOCKED on the
[saved AVC diagnostic](HERMES_SELINUX_TPM_REPAIR.md#read-only-v2-runtime-failure-diagnostic). The approved
real invocation is consumed. Preserve every attempt/helper; no retry, policy/anchor change or reboot
is authorized. UA-05/P2 and runtime/repeat/cold-boot acceptance remain open.

### SE22 denial groups reviewed; request metadata pending

The operator reports scoped-log SHA-256 896a6d7f3e58ce4e16480ff94e0391cca9244604dbed679a0e4e1a1a4779b32c:
22 records, none unparsed, grouped into cert_t:file read (1), fixed_disk_device_t:blk_file ioctl (20),
and fs_t:filesystem getattr (1). Every group reports hermes_tpm2_setup_t and permissive=0.
Independent journal review identifies Permission denied checking /boot's filesystem type, then failed
ESP discovery; /boot is xfs. The fs_t denial is consistent with that failure. The grouped output does
not identify ioctl numbers or the certificate/config object; it does not justify a blanket ioctl grant.

The [source review and next diagnostic](HERMES_SELINUX_TPM_REPAIR.md#read-only-ioctl-request-metadata)
retain the exact downstream-source limitation. SE22 runtime remains ❌ FAIL; review is 🚧 BLOCKED on
root-private request metadata. No policy/helper changes, retry or reboot occurred. The approved
invocation is consumed and UA-05/P2 remains open.

## 2026-09-10 standard TPM2 architecture reassessment

The [sanitized observation](plans/evidence/2026-09-10-hermes-tpm-dependency-review.json) records live pinned
read-only metadata, retained initrd inspection and versioned upstream/installed package analysis. Standard
signed-PCR11 disk unlocking and host+tpm2 credentials have no identified NvPCR dependency in the inspected
implementation. Vendor definitions and product measurement create the anchor dependency. SRK services stay
in place; unsupported assumptions about disabling the failed setup unit or widening permissions are excluded.
Production root crypttab/current-image binding/credential inventory and custom consumers are still unverified.

Local changes prepare a conflict-preserving offline profile and explicit boot-policy/credential checks.
The [canonical plan](plans/2026-09-07-hermes-unattended.md#architecture-reassessment-amendment-authorized--2026-09-10)
records approval, source identity, validation, stale gates and exact next action. The
[migration/recovery procedure](HERMES_TPM_DEPENDENCY_REVIEW.md#migration-preparation-and-approval-sequence)
retains existing token/slot/anchor state during preparation and flags the legacy automatic token for a later
separate operation-specific decision. No production change, service invocation or reboot was performed.
Historical SE22 FAIL, v2 exact-store validation and prepared v3 sources remain preserved. No new candidate or
production PASS has been issued. Follow the single remaining inventory request; do not repeat SE22 diagnostics.

### 2026-09-10 privileged inventory received and correlated

The operator supplied the requested JSON at 15:44 UTC. Review confirms the selected RSA2048-v2 file and current
initrd match their retained build hashes, and the public PCR11 key in /run matches the reviewed key. Root crypttab
has no keyfile, NvPCR keyslot measurement or PCR-lock option. The expected encrypted provider credential and
host credential secret are absent. Independent read-only pinned SSH at 15:47–15:48 confirms the persistent
public-key path is absent, the generated cryptsetup command has no NvPCR/PCR-lock option, seven packaged
PCR-lock services are disabled/inactive and no template instances are loaded or enabled.

The [updated dependency procedure](HERMES_TPM_DEPENDENCY_REVIEW.md#inventory-received-and-reviewed) records these
observations and their limits. BootCurrent 0006 is absent from BootOrder; matching selected-file hashes are
not fresh measured-boot, next-default or no-input boot proof. The early/late setup invocation identities are
unchanged, preserving the late failure. No runtime source changed and no service was invoked.

AR01 supplied-inventory review ✅ PASS; custom/external consumer confirmation remains open. Do not repeat the
collector or SE22/LUKS diagnostics. Fresh lab certification and production P2/B1–B7, then P3/P4 remain required
under new concrete approvals. Credential enrollment and persistent public-key installation are still pending.

### 2026-09-10 fresh campaign preparation and coverage limits

The operator selected the ordered next tasks and answered that custom/external TPM integrations are unknown.
A further bounded read-only audit found no reference in 10 accessible custom configuration/execution files;
protected cron and Hermes/root user-service/Quadlet paths still require the new protected-only read.
The original boot/crypttab/credential and SE22/LUKS diagnostics are complete and must not be repeated.

The [campaign observation](plans/evidence/2026-09-10-hermes-standard-tpm2-campaign.json) records a local installer
integration fix: the shared standard profile is applied before dracut, and baseline/updated archives are
checked before signing. Local validation passes 216 affected Python tests, 138 ShellSpec examples and an actual
synthetic cpio/gzip/lsinitrd round-trip. No live dracut/VM/TPM or production acceptance is claimed.

The root broker currently binds test UID 987; lifecycle needs UID 984. Exact temporary broker/socket access,
fixed-domain power permissions, one fresh run and mandatory cleanup are prepared as AR04-L0/L1/L2 for review.
No such control changed and no service was invoked. The existing certifier covers only part of B1–B7; separate
previous-image boot, boot-artifact trust rejection and full interruption evidence remain required before AR04
or amended release signing. Production P2 has never passed; P3/P4 remain blocked and prepared v2/v3 work is retained.

### 2026-09-10 protected consumer closure and authorized initial lab run

AR01 bounded review ✅ PASS: the operator's 16:41:36 UTC protected-only root report has no hits or
unreviewed paths; cron is empty and Hermes/root user-service/Quadlet directories are absent.
External consumers remain unproven; this is not an arbitrary-consumer absence claim. All requested
operator inventory and SE22/LUKS evidence is received. Do not repeat those diagnostics.

The user explicitly approved AR04-L0/L1/L2. Temporary control enrollment passed at 16:49:36 UTC and the
one authorized run began at 16:49:59 UTC. Its four-hour grant cannot be reused. See the
[live observation](plans/evidence/2026-09-10-hermes-standard-tpm2-live.json) for actual results and cleanup.
Dispatch establishes no boot/certification pass. AR04's remaining matrix and production P2–P4 stay open.

### 2026-09-10 first amended lab failure, cleanup and local correction

AR04-L1 ❌ FAIL: unattended installation and lab recovery-key readback passed, but the baseline initrd
mask assertion failed before signing or first installed boot. The exact failed archive was removed by
mandatory cleanup, so its mask contents remain unavailable. The run stayed uncertified and reached failed-cleaned.
AR04-L2 ✅ PASS at 17:12:52 UTC: domain/disk/NVRAM/swtpm/private state absent, original broker bytes/metadata
and UID 987 restored, temporary access and active grant removed, broker/socket/runtime credential absent.
No provider test credential was issued. Production and preserved old source/policy/journals were unchanged.

A real local dracut reproduction identified a checker incompatibility with equivalent relative /dev/null
masks. The bounded correction and retained sanitized failure verdicts pass 23 profile and 66 lifecycle tests.
This is local evidence, not a new full guest build/boot. The distinct unissued
[r2 package](HERMES_TPM_DEPENDENCY_REVIEW.md#corrected-integration-package-r2) needs explicit new operation
approval; the first grant is consumed. AR04 and production P2–P4 remain blocked.

### 2026-09-10 r2 preparation pass, certification failure and restored controls

The approved r2 attempt passed unattended installation, recovery-key readback, first signed-UKI boot,
boot-manager enrollment/observation, canary runtime preparation, stored transaction replay, both real initrd
checks and exact candidate enrollment. These are preparation observations, not completed UA-03/B1–B7 gates.
The original archive compatibility correction is now exercised successfully in baseline and updated builds.

Certification ❌ FAIL with required-command-unavailable before provider credential issuance. No acceptance
gate was recorded. The exact failed executable/stage was not retained; actual UID 984 reproduction confirms
that the scheduler's sanitized PATH cannot resolve Restic or Trivy and launching Restic yields ENOENT.
The parent service's extra PATH does not carry into the scheduler child. No NvPCR or SELinux expansion is justified.
L2 ✅ PASS at 18:38:19 UTC, independently verified: guest/private resources removed, broker bytes/metadata/xattrs
and UID 987 restored, socket/runtime credential absent, temporary privileges/units/grant removed, old state preserved.

The [r3 procedure](HERMES_TPM_DEPENDENCY_REVIEW.md#certifier-tool-configuration-package-r3) uses the existing
root-owned adjacent tools directory and adds early child-environment readiness plus safe failure-stage retention.
Local affected tests pass 114/114 after a preserved import-indentation failure. R3 remains unapproved/unissued.
Full candidate certification, previous-image boot, boot-trust negatives, the full interruption matrix and P2–P4
remain open; neither consumed lab approval authorizes another run or a production operation.

### 2026-09-11 r3 integration and independent restoration passed

The [r3 live observation](plans/evidence/2026-09-11-hermes-standard-tpm2-r3-live.json) records L0/L1/L2 ✅ PASS.
All seven existing certifier gates passed for candidate f81c54e9e9904b220ab26f7c296862d0f27daa398e0cf6434c955e1c14723b3b:
update replay, inference, warm/cold boot, runtime/credentials, encrypted semantic restore, advisory scan and
provider revocation. Warm/cold boots observed kernel 7.2.4-200.fc44.x86_64, Secure Boot, Enforcing, matching SRK
files and both SRK setup services passing under the standard TPM profile. The negative protocol/payload matrix
and closed rerun passed. These establish real lab evidence without NvPCR anchoring for this path.

At 03:01:21 UTC L2 and independent verification confirmed original broker bytes/metadata/xattrs and UID 987,
removed temporary access and parent grant, and absent VM/private/runtime credentials. All three source snapshots and
prior failures remain intact; no release was signed or production changed. The allowance is consumed.
Full AR04 remains open for B3, B4 and the remaining B6/B7 branches described in the
[remaining lab gate specification](HERMES_TPM_DEPENDENCY_REVIEW.md#remaining-lab-gate-specification-after-r3).
P2 hardware acceptance has never passed; P3/P4 remain blocked in order. Do not repeat received inventories or SE22 diagnostics.

The advisory scan reported 20 CRITICAL and 467 HIGH findings; PASS is scoped to the unchanged
advisory/denylist policy, not absence of vulnerabilities. Full aggregate counts and policy hash are in r3 evidence.

At 03:09:28 UTC the consumed derived candidate grant was also archived privately and its active path removed.
A separate check verified both grant paths absent without another service invocation.

## 2026-09-13 worker client key ownership fix — offline pass, real-VM gate blocked

The pre-M02 blocker ("transfer private-key ownership before rootless chown") was independently reviewed and
fixed in `scripts/hermes/manual/provision-worker-client-key.sh`: it now chowns `KEYDIR`, the private key and the
public key to `hermes:hermes` before the rootless mapped chown (`podman unshare chown 10000:10000`), which is
the ownership state `m02-deploy-and-validate.sh` starts from. The finding is confirmed — `ssh-keygen` runs as
root, and M02 only ever mapped-chowns a key already staged hermes-owned.

Offline checks pass: `rehearse-clean-install.sh` = `REHEARSAL=PASS` (`failures=0 advisories=0`; section 16 now
asserts the ownership sequence and its rerun re-assertion), `tests/test-hermes-guide.sh` 217/217, ShellCheck and
shfmt exit 0, markdownlint 0 errors, and reverting the ownership line makes the rehearsal fail with three
failures. Helper sha256 `979692cf…c8de6`.

The authorized disposable Fedora 44 VM validation could not run. This environment is a bubblewrap container:
`./vm/setup-hypervisor.sh --check` reports **MISSING KVM acceleration (/dev/kvm not found)** and **MISSING
libvirt storage permissions**, `vm/lib-vm-common.sh:91-93` hard-fails without `/dev/kvm`, `sudo` is blocked by
`no_new_privs`, and a Podman-equivalent namespace cannot be built (`newuidmap: write to uid_map failed:
Operation not permitted`; `podman unshare` needs a writable `/run/user/1000`). No fixture was created, so
nothing was destroyed, and `virsh -c qemu:///system list --all` stayed empty. The in-VM steps (mapped
10000:10000 ownership and mode, rerun hash, public-key recovery, M02 `KEY_READABLE`, worker transport and the
negative isolation/trust checks) remain unverified. Full record:
[worker-key ownership validation](plans/evidence/2026-09-13-hermes-worker-key-ownership-validation.json).

On resume at 23:37 UTC the environment was re-checked and remained blocked identically (`container-other`/`bwrap`,
no `/dev/kvm`, `no_new_privs`, `newuidmap` EPERM, read-only `/run/user/1000`), so no in-VM execution occurred and
the passing offline checks were not repeated. The next evidence must come from real rootless Podman execution;
live validation remains outstanding. **B6 remains open.**
