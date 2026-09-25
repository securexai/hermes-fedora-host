# VM deployment testing tasks

For the current unencrypted DeepSeek lab commands and gates, use
[HERMES_DISPOSABLE_LAB.md](../docs/HERMES_DISPOSABLE_LAB.md). The certification
checklist below belongs to the older encrypted/production-candidate track.

This is the executable progress checklist for disposable Hermes certification and production promotion. The
chronological evidence ledger is
[`HERMES_INSTALLATION_VERIFICATION.md`](../docs/HERMES_INSTALLATION_VERIFICATION.md).

## Status rules

- `PASS` requires the documented pass condition and an existing durable evidence path.
- `BLOCKED` identifies a reproduced failure that prevents later tasks.
- `PENDING` means the task has not run against the current implementation.
- Complete tasks in ID order. Never skip from a blocked certification task to production.
- Never capture an interactive provider terminal with `tee` or `script`; it may display OAuth or credential material.

## Simplified application-only profile

The September 12 user-approved fresh-server amendment is tracked by SIMPLE-01 through SIMPLE-06 in the
[canonical execution record](../docs/plans/2026-09-07-hermes-unattended.md#simplified-fresh-server-profile--approved-september-12-2026).
Execute its cleanup, implementation, fresh-host validation, independent cleanup, package and production
approval gates in order. Earlier UA/B gates remain applicable to their advanced profile and are not passes
for this distinct application-only installer. Advanced boot/OS migration is deferred, not deployed.

## Current task ledger

Unattended profile gates are additional to the historical tasks below. Execute them in order;
the old console-unlock VM fixture cannot satisfy the TPM boot gate. Track implementation and evidence in
[the unattended execution record](../docs/plans/2026-09-07-hermes-unattended.md).

| ID | Task | Pass condition | Evidence | Status |
| --- | --- | --- | --- | --- |
| `UA-01` | Offline trust and stage tests | New Python suite and existing Hermes/VM checks pass | [114 Python, real disk I/O, 138 ShellSpec and boundary review](../docs/plans/evidence/2026-09-07-privileged-boundary-review.json) | `PASS`: offline only |
| `UA-02` | Isolated enrollment fixtures | Roles, signer, credential service, Restic, TPM2 and signed UKI recovery validated | TPM, isolated broker/signer, semantic restore and rollback observed; [runtime API acceptance and revocation passed](../docs/plans/evidence/2026-09-07-hermes-api-acceptance.json) | `PASS`: repaired lab fixtures only |
| `UA-03` | Disposable no-input certification | Exact replay, automatic cold/update boots, runtime, inference, backup restore and negative tests pass | [Fresh candidate/run evidence](../docs/plans/evidence/2026-09-08-hermes-ua03-certification.json); final access and credential revocation verified | `PASS`: isolated candidate only |
| `UA-04` | Revoke, purge, destroy and sign | Provider-side revocation proven, all disposable state removed, exact signed release issued | [Cleanup and independently verified signed release](../docs/plans/evidence/2026-09-08-hermes-ua04-cleanup-signing.json) | `PASS`: lab-bound release |
| `UA-05` | Production enrollment | Fresh authorized candidate certification, P2/B1–B7 hardware boot/recovery and P3/P4 deployment acceptance | [SE22 failure](../docs/plans/evidence/2026-09-10-hermes-selinux-v2-runtime-failure.json) remains; request metadata and failure review complete. SE23–SE25 v3 work preserved/paused. [AR01–AR05 architecture amendment](../docs/plans/2026-09-07-hermes-unattended.md#architecture-reassessment-amendment-authorized--2026-09-10) prepares standard TPM2 configuration with SRK setup retained. AR01 bounded consumer review passes with the protected inventory received. The approved first AR04 run failed baseline archive validation and was cleaned/restored; the approved r2 attempt passed preparation but failed certification, and was cleaned/restored. The separately approved r3 run passed all seven existing certifier gates; L2 and independent restoration passed. Its grant is consumed. See the [live observation](../docs/plans/evidence/2026-09-10-hermes-standard-tpm2-live.json); full fresh lab certification and concrete production approvals remain required. | `BLOCKED`: P2 never passed; amended candidate evidence STALE |

For the amended standard TPM2 candidate, historical UA-01–UA-04 passes above remain scoped to their frozen
artifacts. Changed host/preflight, credential and observer/profile inputs make candidate boot/runtime/replay
and promotion evidence **STALE**; rerun ordered UA-01–UA-04 with a fresh grant before UA-05. Acceptance B1–B7 and
the exact migration/recovery sequence are in the [dependency procedure](../docs/HERMES_TPM_DEPENDENCY_REVIEW.md).
SE22's service invocation and previous lab exceptions are consumed, not reusable authorization.

September 10 continuation: both inventories are received and AR01 bounded review passes. No custom NvPCR
consumer was identified; arbitrary external use remains unproven. The standard profile is connected to the
disposable installer, with baseline/updated initrd checks before signing. The user explicitly approved
AR04-L0/L1/L2; that single run failed archive validation and cleanup/restoration passed. The distinct
[corrected r2 package](../docs/HERMES_TPM_DEPENDENCY_REVIEW.md#corrected-integration-package-r2) received explicit
approval and began at 17:56:53 UTC. It passed both initrd checks and preparation, then failed certification
with a process-launch error. L2 restored the controls and removed its grant at 18:38:19 UTC. The
[r2 live observation](../docs/plans/evidence/2026-09-10-hermes-standard-tpm2-r2-live.json) records the child tool-path
defect and prepared r3 package. The r2 allowance is consumed. The separately approved r3 L0/L1/L2
passed, including independent restoration at 2026-09-11T03:01:21Z.
[R3 evidence](../docs/plans/evidence/2026-09-11-hermes-standard-tpm2-r3-live.json) binds all seven existing certifier
gates to its exact candidate; the r3 allowance is consumed and temporary access is removed.
Its existing certifier covers only part of B1–B7; previous-image boot, boot-artifact trust rejection and the full
interruption matrix remain separate live gates.
The r3 integration subset passes; full amended certification, release signing and production remain open.

The [remaining lab package](../docs/HERMES_REMAINING_LAB_TESTS.md) prepares B3 first and separate B4/B7
cases. B3 L0/L1/L2 passed on September 11: all eight certifier gates, the three-boot image round trip and
independent L2 restoration pass in the [B3 live evidence](../docs/plans/evidence/2026-09-11-hermes-b3-live.json).
The single block finished at 18:00:17Z, within its four-hour limit; its approval is consumed. The user subsequently
authorized all pending tasks. `b4-linux` failed before its tamper experiment; independent cleanup passed at
22:14:22Z within four hours. The user subsequently authorized bounded replacements without further
lab approval prompts. Corrected r5 passed seven gates, then failed initial provider revocation. Its cleanup
retry confirmed revocation; independent restoration passed on September 12 at 00:04:12Z, within four hours.
No tamper test ran; bounded revocation reconciliation and a fresh replacement are being prepared.
The correction subsequently passed offline checks; r6 passed L0 and dispatched once on September 12 at
00:12:21Z. All eight prerequisites passed, but trial preparation filled the 600-MiB EFI partition.
No negative boot ran. Recovery and independent cleanup passed at 01:26:22Z within four hours;
the next fresh fixture uses 2048 MiB and pre-copy capacity checks. B4 acceptance remains pending.
Later B4/B7 blocks remain dependent on this result and independent cleanup.
The [continuation evidence](../docs/plans/evidence/2026-09-11-hermes-remaining-continuation.json) records execution.
R7 subsequently failed before installation; independent cleanup passed at 01:32:13Z.
R8 passed both resource checkpoints and dispatched once at 02:11:51Z on September 12.
Its B4-linux rejection/recovery and independent cleanup passed at 04:43:49Z, within four hours.
[Live evidence](../docs/plans/evidence/2026-09-12-hermes-b4-linux-r8-live.json) retains the exact result.
Fresh B4-initrd r9 dispatched once at 04:46:33Z; cleanup is due by 08:46:01Z.
All 13 operator templates
have a static preparation inventory; live acceptance and production gates remain open.

Production gates remain blocked on the full lab matrix and concrete hardware/recovery prerequisites.

U06 scheduler service validation and dedicated-fixture cleanup passed in the
[fresh scheduler run](../docs/plans/evidence/2026-09-08-hermes-scheduler-live.json).
The service ran under an explicitly approved expiring lab window grant; actual off-window deferral,
failure signaling/reconciliation and completed-run behavior were also checked. No new release was signed.
Automatic fixture provisioning, exact guest enrollment and teardown passed U06/F4 in the
[live lifecycle campaign](../docs/plans/evidence/2026-09-08-hermes-lifecycle-live.json): two fresh successes,
idempotency, one credential-bearing interruption/recovery, independent revocation and complete teardown.
Temporary controls were removed and broker changes restored. Recurring timers remain untouched and
disabled; enablement and UA-05 still require separate authorization. Evidence applicability and limits
are recorded in the [canonical plan](../docs/plans/2026-09-07-hermes-unattended.md#f4-final-closure).
The historical UA-03/UA-04 release above retains its original candidate binding.

| ID | Task | Pass condition | Evidence | Status |
| --- | --- | --- | --- | --- |
| `DOC-01` | Synchronize and lint Hermes documentation | Guide checks, Markdown lint, doc audit, and `git diff --check` pass | Logs `33` through `37` in `progress-status-fix-20260831T205707Z` | `PASS` |
| `REG-01` | Run focused LUKS watcher replay | `11 examples, 0 failures` | `/var/home/cloudops/.local/state/hermes-certification/progress-20260831T190249Z/01-luks-console-shellspec.log` | `PASS` |
| `REG-02` | Run provider/controller replay | `44 examples, 0 failures` | `/var/home/cloudops/.local/state/hermes-certification/progress-fix-20260831T193144Z/02-reg02-green.log` | `PASS` |
| `REG-03` | Run complete offline gate | Every command exits zero | Logs `10b` through `16` in `progress-fix-20260831T193144Z` | `PASS` |
| `REG-04` | Cover the final post-close status seam | Red replay fails after `stage-closed`; green replay retains the exact secret-free failing check | Logs `01` through `11` in `progress-status-fix-20260831T205707Z` | `PASS` |
| `REG-05` | Re-run the complete offline gate after the status repair | Every command exits zero with the new regression included | Logs `12` through `28` in `progress-status-fix-20260831T205707Z` | `PASS` |
| `REG-06` | Repair production helper bootstrap across SSH TTYs | Red replay shows `sudo -n`; green replay prompts in the bootstrap TTY; all offline gates pass | Private production ledger and controller regression | `PASS` |
| `REG-07` | Repair four-argument deployment preflight update mode | Red replay retains `ALLOW_UPDATE=0`; green replay enables update mode; all offline gates pass | Logs `09` through `15` in `progress-production-20260901T004057Z` | `PASS` |
| `LAB-01` | Verify failed-run cleanup | Known failed-run certifier PIDs, domain, QCOW2, and OEMDRV are absent | Prior cleanup log plus `run-20260831T194212Z` verification | `PASS` |
| `LAB-02` | Verify host resources and clean lab state | At least 2 CPUs, 9 GiB available RAM, 60 GiB free, no lab domain/storage | `20b-lab-preflight-retry.log` in `progress-fix-20260831T193144Z` | `PASS` |
| `LAB-03` | Run fresh Fedora Server 44 certification | Media, install, update, runtime, SSH, and three ordered reboot sequences pass | `run-20260831T212756Z` | `PASS` |
| `LAB-04` | Complete provider acceptance | Readiness entered in certifier terminal; authenticated response is exactly `HERMES_OK` | Provider and inference stages in `run-20260831T212756Z` | `PASS` |
| `LAB-05` | Verify cleanup and issue promotion record | Providers revoked, data purged, fixture removed, VM/storage absent, valid record printed | `run-20260831T212756Z` and `promotion-20260831T212756Z.record` | `PASS` |
| `LAB-06` | Recertify the repaired production controller | A fresh disposable run passes all gates and issues a record matching the repaired artifact fingerprint | `run-20260901T034903Z` and `promotion-20260901T034903Z.record` | `PASS` |
| `REG-08` | Reset local controller state after a fresh-data rollback | A subsequent `deploy` takes the complete install path, not the provider-only resume path | ShellSpec regressions; 138 examples and 217 guide checks | `PASS` |
| `LAB-07` | Certify the final controller source | Media, installation, provider acceptance, `HERMES_OK`, revocation, purge, and destruction pass | `run-20260901T183122Z` and `promotion-20260901T183122Z.record` | `PASS` |
| `PROD-01` | Adopt reinstalled production host | Console fingerprint matches and adoption succeeds | Private host ledger (outside repository) | `PASS` |
| `PROD-02` | Run read-only production check | Exact `PREFLIGHT_OK` and no mutation | Private host ledger (outside repository) | `PASS` |
| `PROD-03` | Deploy with matching record | Confirmation, provider acceptance, and exact `HERMES_OK` succeed | Bound state plus `31-production-deploy-evidence.log` in the private production ledger | `PASS` |
| `PROD-04` | Verify production persistence | Post-reboot `status` is healthy and drift-free | `32-production-status.log` in the private production ledger | `PASS` |
| `PROD-05` | Purge the previous installer-created production instance | Hermes identity/data absent; temporary helper and sudo rule absent | Secret-free direct probes and local `stage-rollback` state | `PASS` |
| `PROD-06` | Fresh production redeployment | Bound final record, provider/inference acceptance, and closed healthy status | Local bound state and direct status (`healthy`, readonly, port-free, drift-free) | `PASS` |

## Progress log setup

Create one mode-`0700` directory per verification pass. The current repair and verification pass uses the exact
directory shown here; future passes use a new UTC timestamp.

Run these commands inside the dev-toolbox `infra` container (`dev-infra-hermes`). `shellspec` is repository-local at
`toolbox/.tools/shellspec/shellspec`, and `markdownlint-cli2` is not a global executable — it runs through
`pre-commit` (check-only; the config sets `fix: false`).

```bash
progress_dir=${HERMES_PROGRESS_DIR:-$HOME/.local/state/hermes-certification/progress-$(date -u +%Y%m%dT%H%M%SZ)}
install -d -m 0700 "$progress_dir"
set -o pipefail

git status --short --branch 2>&1 \
  | tee "$progress_dir/00-worktree.log"
toolbox/.tools/shellspec/shellspec spec/vm/luks_console_spec.sh 2>&1 \
  | tee "$progress_dir/01-luks-console-shellspec.log"
toolbox/.tools/shellspec/shellspec spec/hermes/deploy_spec.sh 2>&1 \
  | tee "$progress_dir/02-deploy-shellspec.log"
chmod 0600 "$progress_dir"/*.log
```

The pipeline status is the command status because `pipefail` is enabled. A log file by itself is not a pass.

## Documentation verification

Run these commands for `DOC-01`:

```bash
./tests/test-hermes-guide.sh 2>&1 \
  | tee "$progress_dir/03-hermes-guide.log"
pre-commit run markdownlint-cli2 --all-files 2>&1 \
  | tee "$progress_dir/04-markdownlint.log"
# 05-doc-diff-audit.log: NOT RUN — see note below
git diff --check 2>&1 \
  | tee "$progress_dir/06-git-diff-check.log"
```

The doc-diff audit script belonged to a personal skill directory in the source
operator's home and is not part of this repository's migrated tree. It is listed
above as the slot it occupied; until an equivalent is added, `DOC-01` relies on
the guide suite, Markdown linting and `git diff --check`, and the audit slot is
recorded as not run rather than passed.

The documentation task passes when the guide, Markdown, and diff checks exit zero and the doc audit reports no new
Hermes accuracy issue. Pre-existing findings outside the Hermes scope remain listed in the audit log.
The audit's three active-Hermes findings in provider tables are classified false positives: each is a model identifier
containing `/`, not a repository path.

## Regression gate

`REG-02` was repaired by adding one `luks-reboot-observed` event before each cryptsetup boundary in the valid
provider-readiness fixture. The original failure is retained in `01-reg02-red.log`; the repaired replay passed
`44 examples, 0 failures` in `02-reg02-green.log`.

The first combined ShellSpec invocation failed before running because concurrent Devbox processes raced on its
generated `.cmd.sh` file. That infrastructure failure is retained in `10-shellspec-all.log`. The isolated retry in
`10b-shellspec-all-retry.log` passed `127 examples, 0 failures`; logs `11` through `16` record the remaining successful
offline gates. With the retry evidence retained, `REG-03` is `PASS`.

The reproducible commands for `REG-03` are:

```bash
toolbox/.tools/shellspec/shellspec spec/hermes/ spec/vm/ 2>&1 \
  | tee "$progress_dir/10-shellspec-all.log"
./tests/test-hermes-guide.sh 2>&1 \
  | tee "$progress_dir/11-hermes-guide.log"
bash -n hermes-deploy.sh hermes-certify-vm.sh scripts/hermes/*.sh \
  vm/create-hermes-server-vm.sh vm/lib-hermes-luks-console.sh vm/lib-vm-common.sh 2>&1 \
  | tee "$progress_dir/12-bash-syntax.log"
python3 -m py_compile vm/hermes-luks-console.py 2>&1 \
  | tee "$progress_dir/13-python-compile.log"
shellcheck hermes-deploy.sh hermes-certify-vm.sh scripts/hermes/*.sh \
  tests/test-hermes-e2e-vm.sh vm/create-hermes-server-vm.sh \
  vm/lib-hermes-luks-console.sh vm/lib-vm-common.sh 2>&1 \
  | tee "$progress_dir/14-shellcheck.log"
shfmt -i 2 -ci -bn -d hermes-deploy.sh hermes-certify-vm.sh \
  scripts/hermes tests/test-hermes-e2e-vm.sh vm/create-hermes-server-vm.sh \
  vm/lib-hermes-luks-console.sh vm/lib-vm-common.sh 2>&1 \
  | tee "$progress_dir/15-shfmt.log"
pre-commit run markdownlint-cli2 --all-files 2>&1 \
  | tee "$progress_dir/16-markdownlint.log"
```

Do not start another disposable VM while any `REG-*` task is blocked.

`REG-04` and `REG-05` were created from the `LAB-05` failure after `LAB-03` and `LAB-04` had passed. The retained red
replays prove both the first-attempt controller failure and the wrapper's strict-pipeline exit on absent optional state.
The green replay verifies safe defaults, allowlisted drift reasons, 12 bounded convergence attempts at five-second
intervals, and a mode-`0600` certifier diagnostic. The controller suite passes 49 examples and the complete suite passes
132 examples. The initial complete-suite, ShellCheck, and shfmt failures are retained beside their successful retries.
`REG-04` and `REG-05` therefore permit, but do not replace, a fresh disposable certification.

## Lab preflight and cleanup

The failed runs used certifier PIDs `1194780` and `1325549`. Verify their cleanup and the exact dedicated resources:

```bash
bash -c '
  if kill -0 1194780 2>/dev/null; then exit 1; else echo "PASS pid=1194780 absent"; fi
  if kill -0 1325549 2>/dev/null; then exit 1; else echo "PASS pid=1325549 absent"; fi
  if virsh -c qemu:///system dominfo lab-hermes-server >/dev/null 2>&1; then
    exit 1
  else
    echo "PASS domain=lab-hermes-server absent"
  fi
  if [[ -e /var/lib/libvirt/images/lab-hermes-server.qcow2 ]]; then
    exit 1
  else
    echo "PASS storage=qcow2 absent"
  fi
  if [[ -e /var/lib/libvirt/images/lab-hermes-server-oemdrv.iso ]]; then
    exit 1
  else
    echo "PASS storage=oemdrv absent"
  fi
' 2>&1 | tee "$progress_dir/07-failed-run-cleanup.log"
```

For cleanup evidence, all five markers must report `PASS` and the command must exit zero. Before `LAB-03`, verify
resources separately:

```bash
{
  getconf _NPROCESSORS_ONLN
  awk '/MemAvailable:/ { print $2 * 1024 }' /proc/meminfo
  df --output=avail -B1 /var/lib/libvirt/images
  virsh -c qemu:///system list --all
} 2>&1 | tee "$progress_dir/20-lab-preflight.log"
```

Pass thresholds are 2 online CPUs, 9 GiB available memory, and 60 GiB free storage, with no
`lab-hermes-server` domain or dedicated storage files.

## Production preflight attempt

The production host adoption completed, but the first read-only check returned
`PREFLIGHT_FAILED count=2`. The target root logical volume was 15 GiB total
with about 11.36 GiB available under `/var`, below the 20 GiB requirement. The
operator expanded it to 40 GiB and grew XFS; a fresh direct check now reports
about 35.9 GiB available. The same check still observes TCP and UDP port 5355
and TCP port 9090 on non-loopback addresses; `systemd-resolved` reports LLMNR
enabled and `cockpit.socket` is listening. The operator then applied the host
hardening policy; a fresh direct read-only check shows LLMNR disabled,
`cockpit.socket` inactive and masked, and no unexpected non-loopback listener.

The full production check then returned exact `PREFLIGHT_OK`, so `PROD-02`
passes. The controller status-propagation repair and its regression evidence
are recorded in the private host ledger outside this repository. The repaired
certification and production deployment later completed; `PROD-03` and
`PROD-04` are now `PASS` with the evidence named in the task ledger.

## Fresh certification evidence

Run the [Hermes certifier](../hermes-certify-vm.sh) only after `REG-03` and `LAB-02` pass. The operator supplies the
official Fedora Server 44 DVD, signed checksum, Fedora keyring, and SSH identity. Do not redirect its terminal output.

At `AUTHENTICATION_READY`, `START-AUTH` must go to the exact certification terminal; it is not a Bash command. The
operator's standing preference authorizes Codex to submit it automatically when Codex owns that managed terminal.
Codex must suppress the write result and stop reading the terminal before authentication output appears. The operator
still completes the provider login. This preference does not authorize credential handling, account approval, or
production mutation. Require the complete inference response to equal the nine ASCII characters `HERMES_OK`.

For the new exact `run-*` directory, `unlock-monitor.log` must contain:

- One initial `luks-prompt-verified input-submitted=1` before `monitor-ready`.
- Exactly three `luks-reboot-observed input-submitted=0` events.
- Exactly three `luks-boot-boundary-observed input-submitted=0` events.
- Exactly three watched `luks-prompt-verified input-submitted=1` events.
- For each watched boot, those three events in reboot, boundary, prompt order with no reuse across boots.

Validate the transcript with the same implementation used by the controller:

```bash
run_dir=${HERMES_CERT_RUN_DIR:-$HOME/.local/state/hermes-certification/run-YYYYMMDDTHHMMSSZ}

bash -c '
  source scripts/hermes/certification-evidence.sh
  certification_unlock_evidence_is_valid "$1"
' _ "$run_dir/unlock-monitor.log"
```

`LAB-05` passes only after all provider credentials are revoked, fresh data is purged, fixture privilege is absent,
the domain and both storage files are absent, and the certifier prints a valid mode-`0600` `PROMOTION_RECORD` path.

Run `run-20260831T212756Z` passes `LAB-03` through `LAB-05`. It contains provider and inference acceptance,
drift-free final status, authentication revocation, and fresh-data rollback stages. The certifier then verified fixture
removal, destroyed the domain and both dedicated storage files, and issued strict-valid mode-`0600` record
`/var/home/cloudops/.local/state/hermes-certification/promotion-20260831T212756Z.record` (that operator's local state
path; substitute your own `$XDG_STATE_HOME`).

Run `run-20260831T194212Z` passed `LAB-03` and `LAB-04`, then failed inside the controller's final post-close
`status_command`. The certifier therefore never created `status.log`, `guest-facts`, `vm-destroy.log`, or a promotion
record. Failure cleanup reached `stage-auth-revoked` and `stage-rollback`; the certifier PID, domain, QCOW2, and OEMDRV
are absent. A deterministic replay found that optional binding and promotion files were read through unguarded
`sed | tail` pipelines under `pipefail`; the clean VM intentionally lacked those files. The repair is covered by
`REG-04` and `REG-05`. This is still verified failed-run cleanup, not a successful `LAB-05` promotion.

## Production promotion

Historical task `LAB-05` passed for the pre-repair tree, and `REG-06` plus
`REG-07` changed fingerprinted controller artifacts. The failed repaired-tree
attempts remain retained above. Fresh run `run-20260901T034903Z` subsequently
passed all certification gates and issued matching mode-`0600` record
`promotion-20260901T034903Z.record`. The first production deployment bound
that record to `aicowork@10.0.30.10`, completed provider acceptance and exact
`HERMES_OK`, then closed the controller. The secret-free post-reboot status is
healthy and drift-free in `32-production-status.log`. The completed sequence
was:

1. Verify the reinstalled host's SSH ED25519 fingerprint at the local console.
2. Run `hermes-deploy.sh adopt-host` and type `ADOPT-HERMES-HOST`.
3. Run the read-only production `check` and require exact `PREFLIGHT_OK`.
4. Run `deploy` with the matching promotion record and type `CONFIRM-HERMES-PRODUCTION`.
5. Complete production provider authentication and exact `HERMES_OK` acceptance without logging the auth terminal.
6. Run `status` after the planned reboot and save its secret-free output as `32-production-status.log`.

The certifier is the only supported Hermes VM promotion path. It never downloads media, issues a record before VM
destruction, or carries provider credentials into production.

## Final clean production redeployment

The model-default repair and `REG-08` changed fingerprinted controller
artifacts, so the earlier repaired-tree promotion record was intentionally not
used for the final deployment. Final-source run `run-20260901T183122Z` passed
the complete disposable certification sequence and issued
`promotion-20260901T183122Z.record` mode `0600`.

Production then ran `rollback --purge-fresh`; direct secret-free probes
confirmed the old Hermes identity and data were absent and the temporary root
helper and sudo rule were removed. A fresh deployment bound the final record,
completed provider and inference acceptance with `openai-codex` and
`gpt-5.6-luna`, and closed. Direct status reported `health=healthy`,
`readonly=true`, `ports={}`, and `drift=none`.

Two failed workstation-terminal attempts echoed a sudo entry because a piped
purge confirmation occupied standard input while sudo required a terminal. The
task-specific terminals were closed, the retry used a masked password dialog,
and no credential material is recorded in this repository. Rotate the
`aicowork` sudo password before further privileged operator work.
