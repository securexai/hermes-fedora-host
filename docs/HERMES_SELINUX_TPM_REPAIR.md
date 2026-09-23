# Hermes TPM setup SELinux candidate

Status as of 2026-09-10: revised candidate 1.1.0 remains installed and SELinux is Enforcing. SE22 runtime
failed with 22 scoped AVCs and no ESP anchor; its invocation is consumed. **SE22 request metadata has been
received and failure review passed.** It identifies all ioctl commands and openssl.cnf; do not repeat the
saved metadata diagnostic. SE23–SE25 are separate prepared v3 correction work and are preserved/paused.

The [architecture reassessment](HERMES_TPM_DEPENDENCY_REVIEW.md) now precedes policy expansion. It prepares a
conditional standard TPM2 configuration that retains SRK setup and PCR11 measurement. The requested boot,
configuration and credential inventory is received and reviewed. The operator does not know of custom/external
integrations; the protected cron/user-service/Quadlet report is now received with no hits or unreviewed paths.
AR01 bounded review passes; arbitrary external use remains unproven. Do not repeat either collector or SE22 diagnostics.
The approved standard-profile lab attempt failed baseline archive validation and cleanup/restoration passed.
Its [live observation](plans/evidence/2026-09-10-hermes-standard-tpm2-live.json) preserves that failure and
the distinct r2 correction package. R2 passed archive/preparation checks, then failed certification;
cleanup/restoration passed. Its [live observation](plans/evidence/2026-09-10-hermes-standard-tpm2-r2-live.json)
records the confirmed child tool-path defect and the prepared r3 package. The separately approved r3
lab run passed its seven existing certifier gates; L2 and independent restoration passed on September 11 UTC.
[R3 evidence](plans/evidence/2026-09-11-hermes-standard-tpm2-r3-live.json) records successful warm/cold SRK setup
with Enforcing and the standard profile. Full B1–B7 and production gates remain open. No SELinux permission expansion follows.
Follow its
[migration and recovery procedure](HERMES_TPM_DEPENDENCY_REVIEW.md#migration-preparation-and-approval-sequence).
No new production policy install, service invocation, anchor operation or reboot is authorized. Keep all reviewed sources,
private backups and three attempts. The handoffs below preserve repair history and must not be re-executed
under consumed approvals. Runtime, repeat/idempotency, cold-boot and UA-05/P2 gates remain open.

## Inputs and design

Target: Fedora Server 44, systemd 259.8-1.fc44, selinux-policy 44.8-1.fc44, SELinux Enforcing.
The [module](../scripts/hermes/selinux/hermes_tpm2_setup.te) declares an enforcing domain;
the [file context](../scripts/hermes/selinux/hermes_tpm2_setup.fc) labels only
/usr/lib/systemd/systemd-tpm2-setup. Fedora init_daemon_domain provides the init transition.
Both root-filesystem setup services execute this binary; the retained UKI/initramfs is unchanged.
This is not an initramfs policy repair or proof of unattended boot.

The [upstream proposal](https://github.com/fedora-selinux/selinux-policy/pull/3321)
is a design reference, not the installed candidate: it marks its domain permissive.
The local candidate does not. Required writes follow the
[systemd v259 setup code](https://github.com/systemd/systemd/blob/v259/src/tpm2-setup/tpm2-setup.c)
and [anchor synchronization code](https://github.com/systemd/systemd/blob/v259/src/shared/tpm2-util.c).

Permission scope that must be accepted before a live trial:

- TPM device read/write is required for the service's SRK/NvPCR operations. SELinux cannot
  restrict these grants to particular TPM commands; no restart is authorized by compilation.
- Existing init_var_run_t and init_var_lib_t labels are preserved. Atomic credential/public-key
  writes require create, write, rename and cleanup. Grants cover those types beyond the named paths.
- VFAT uses dosfs_t across the ESP. Atomic anchor creation therefore grants this service writes
  to all dosfs_t files, including EFI images. This is not filename-limited access. The candidate
  gives no new dosfs_t writes to init_t and does not change mount labels or firmware variables.
- Measurement-log access covers existing syslogd_var_run_t files, with no create/unlink grant.
- Standard Fedora daemon/domain interfaces also inherit base-policy permissions, including
  local sockets and conditional rules. Inspect effective policy, not just the source allow lines.
  The candidate adds no Linux capabilities, permissive mode, policy-loading rights or IP socket creation.

## Offline build and inspection

Use an isolated Fedora container; do not run semodule on the workstation or Hermes for this gate.
Install version-matched selinux-policy-devel and selinux-policy-targeted 44.8-1.fc44 plus
checkpolicy, policycoreutils-devel, setools-console and make. All repository commands use devbox run --.
Inside that isolated environment, copy the candidate files into an empty directory and run:

```bash
make -f /usr/share/selinux/devel/Makefile hermes_tpm2_setup.pp
```

Preserve the container's policy.35 before `semodule -n -i hermes_tpm2_setup.pp`, then preserve
the resulting policy.35 and run the [offline verifier](../scripts/hermes/selinux/verify_policy.py):

```bash
python3 verify_policy.py package-base.35 package-merged.35
```

The verifier checks transition, enforcing status, intended permissions, unchanged init_t grants,
and selected forbidden access. It does not prove runtime completeness. Keep effective sesearch
output, package versions and hashes with evidence. Package linking checks shipped neverallow rules.

The copied Hermes binary policy differs from the clean matching-package baseline. Binary-to-CIL
conversion cannot faithfully reconstruct the module interfaces needed for linking. Do not fabricate
missing attributes or claim the package test validates the exact production store.

### Exact installed-store input gate

The initial SSH operator could not read /var/lib/selinux/targeted/active. The operator supplied the
export below; exact-store validation now passes in the [recorded run](plans/evidence/2026-09-09-hermes-selinux-exact-store.json).
For a refreshed baseline, the operator must export this policy-only directory under sudo. It contains policy
modules and store
settings, not TPM credentials. Do not include /run, /boot or any credential directory.
The following creates a private, exclusive export; an existing destination makes it fail:

```bash
sudo sh -eu -c '
  dest=/home/aicowork/hermes-selinux-policy-inputs-20260909
  umask 077
  mkdir "$dest"
  tar -C /var/lib/selinux -czf "$dest/targeted-active.tar.gz" targeted/active
  sha256sum "$dest/targeted-active.tar.gz"
  chown -R aicowork:aicowork "$dest"
'
```

Transfer with pinned SSH, compare hashes, retain a private original, and inspect archive paths before
extracting into an isolated container. Rebuild a copy of the exact store without the candidate first;
compare its effective policy with the copied host policy and explain any difference. Then install the
candidate into a second copy using semodule -n in the container and run the verifier. Refresh host
policy/package hashes before the comparison. A mismatch or unresolved dependency blocks installation.

## Historical 1.0.0 candidate and helper

The original 1.0.0 exported store rebuilt byte-for-byte identically to the freshly checked Hermes policy.
The candidate linked against a separate copy, passed 19 permission assertions, and mapped the
setup executable to the intended enforcing domain. This closes the offline exact-store gate.

The [installation helper](../scripts/hermes/selinux/install-reviewed-candidate.sh) pins the module,
baseline and expected merged-policy hashes. After explicit approval and completion of the physical-console
preflight below, it checks host/package/context drift, rejects an existing candidate or backup directory,
backs up policy and encrypted anchors privately, installs the verified module, and relabels only the setup executable.
It never restarts a service, reboots, or automatically rolls back. A repeated invocation stops for review.
The helper requires both existing runtime and /var/lib anchors; a missing one blocks installation.
Its installation success path passed the operator helper and independent disk/label checks.
Loaded-policy and runtime acceptance remain separate. Syntax, ShellCheck and rejection of missing
approval arguments/corrupt modules passed locally. Hashes are in the
[exact-store evidence](plans/evidence/2026-09-09-hermes-selinux-exact-store.json).

After approval, stage the reviewed helper and matching .pp privately and verify both hashes from that record.
Run the helper with `bash install-reviewed-candidate.sh --approved-policy-install /absolute/path/to/candidate.pp`
under operator sudo only after completing step 1 below. This implements the installation portion of step 2;
complete its remaining transition checks before any service execution. If it fails after installation starts,
stop and use the rollback procedure; policy rollback cannot undo service-side TPM changes.
The backup directory is `/var/lib/hermes-selinux-trial-20260909`; preserve it for recovery and review.

## Historical 1.0.0 production trial scope

Obtain explicit approval for this bounded trial only after the exact-store gate passes. Prepare a
fixed-hash helper against the approved module and live baseline; do not install a raw merged policy.

1. At the physical console with manual LUKS recovery available, verify Enforcing, package versions,
   current UKI and firmware inventory, and no existing module/context override with this name.
   Record service states and a journal/audit cursor. Preserve a root-private copy of the active
   policy store, executable context, and current encrypted anchors from /run, /var/lib and the ESP
   if present; transfer encrypted backups privately and record only hashes and metadata.
2. Install the approved .pp at priority 400 with semodule, then restorecon only the exact executable.
   Verify matchpathcon and the init_t-to-hermes_tpm2_setup_t transition against the loaded policy.
   Do not recursively relabel systemd state or the ESP. Keep Enforcing and existing LUKS tokens.
3. Restart only systemd-tpm2-setup.service once. This can perform TPM operations and synchronize
   anchor copies; it requires the trial approval. Do not restart the early unit or reboot in this scope.
   Collect actual process-domain evidence during execution (or a scoped audit record of execution);
   a static transition rule alone is insufficient. Do not enable shell tracing or print credentials.
4. Require service success with ExecMainStatus=0, actual dedicated-domain execution, no new relevant
   AVCs, and encrypted-anchor presence and matching hashes across expected copies. Exit 76 is not
   acceptance even though systemd lists it as a successful status. Verify the SRK, existing LUKS
   token/keyslot policy, executable label and firmware inventory are preserved.
5. Repeat the late service once only after the first run passes, under the same approved scope,
   and require unchanged anchor/SRK hashes and no new relevant AVCs. Stop on any failure and preserve
   evidence. Cold-boot persistence remains a separate console-controlled gate requiring its own scope.

## Historical 1.0.0 late-service observation helper

The [single-run helper](../scripts/hermes/selinux/run-reviewed-service.py) is prepared for the approved
first trial. Loaded-policy validation and off-host encrypted backup verification passed in the
[recorded observation](plans/evidence/2026-09-09-hermes-selinux-loaded-policy.json). It requires operator
sudo, a fixed loaded-policy hash, Enforcing, the dedicated
executable label, working audit collection, and the expected SRK and anchor files. It uses the verified
Hermes LUKS partition `/dev/nvme0n1p3` for a private metadata digest; no key or token content is printed.

The helper snapshots recovery metadata, runs only the late service once, samples its actual process
domain, and checks exit status, scoped AVCs, audit loss, anchor consistency, SRK, LUKS metadata, firmware,
loaded policy and labels. Evidence is root-private under
`/var/lib/hermes-selinux-trial-20260909/service-first`; only a sanitized summary is printed.
An existing result directory blocks a rerun. A missing observation is an unmet gate, even if the service
succeeded. An observation timeout stops the systemctl client but does not guarantee the unit has stopped;
inspect the unit before any recovery action. No automatic repeat, rollback or reboot is performed.
The approved second run requires a passing first result; the observed failed first run blocks it.

## Failed first-run recovery

The first late-service invocation on 2026-09-09 at 09:43:14–09:43:16 -05 exited 1. Its journal reports
permission denied probing `/dev/nvme0n1p2` and locating XBOOTLDR. The original helper passed a four-digit
year to ausearch under the C locale; the host rejects that date. Original in-memory process and audit-start
observations were not saved before that error and cannot be claimed as recovered observations.

The [read-only recovery helper](../scripts/hermes/selinux/recover-first-service.py) verifies the original
staged helper hash, uses only its snapshot utilities, and queries the exact failed-run audit window using
the accepted two-digit year. It preserves current encrypted anchors and compares recovery-time hashes
against the saved pre-run snapshot. It prints sanitized status and denial fields, and creates a private
archive for pinned transfer. It never retries the service, changes policy, or reboots.

Run it with operator sudo at the staged path, then provide the summary and `RECOVERY_SHA256`.
The export is `/home/aicowork/hermes-selinux-service-recovery-20260909/recovery.tar.gz`.
Any audit source-domain evidence is identified as recovered AVC evidence; it does not replace lost
process sampling or prove successful persistence. Preserve and inspect recovery evidence before rollback.

The repository first-run helper now uses the C-locale date format and saves process/state/audit-start
observations before the audit query, including query diagnostics on failure. That corrected executable
has not been staged over the original or authorized for another service run. Its historical hash remains
in the loaded-policy observation; no prior trial result is upgraded by the local correction.

## Rollback

Recovery evidence is now preserved off-host and validated in the
[recovery observation](plans/evidence/2026-09-09-hermes-selinux-recovery.json).
The [guarded rollback helper](../scripts/hermes/selinux/rollback-reviewed-candidate.sh) is staged at
`/home/aicowork/hermes-selinux-trial-20260909/rollback-reviewed-candidate.sh`.
Run it under operator sudo with `--approved-trial-rollback` as the recovery portion of the approved trial.
It verifies the expected trial/baseline hashes, module priority, labels, recovery-file presence and idle
setup processes; then removes only the trial module and restores the exact executable label.
Success requires the original on-disk policy hash, original mapping and Enforcing. It neither starts a
service nor changes anchors, LUKS metadata, firmware or TPM state. A repeated invocation stops for review.
Rollback passed the operator helper and independent on-disk policy/context checks in the
[rollback observation](plans/evidence/2026-09-09-hermes-selinux-rollback.json).
The retained command is historical recovery guidance; do not rerun it against the restored baseline.

If module installation or label validation fails, stop before service execution. Remove only the new
priority-400 hermes_tpm2_setup module, run restorecon on the exact executable, and verify its recorded
init_exec_t context plus the original policy behavior. An already-existing module is a preflight blocker;
never remove somebody else's module as rollback. Retain the untouched store backup for comparison.

If the service ran, policy rollback alone cannot undo TPM or anchor changes. Preserve new and old
anchors and observations, remove the new module/restore the executable label, then stop for recovery
review. Do not overwrite anchors, clear TPM/NV state, remove LUKS tokens, or perform an automatic reboot.
The original SELinux service failure may return after policy rollback. Fedora/manual unlock remain
recovery paths; this document does not authorize changing their boot configuration.

## Revised 1.1.0 candidate review

The revision retains the original enforcing domain, executable mapping, and existing grants.
The recovered [three scoped AVCs](plans/evidence/2026-09-09-hermes-selinux-recovery.json)
justify namespace file `getattr` and certificate-directory `search`. The precise certificate lookup
and namespace caller are not established by the sanitized records; these grants permit metadata or
traversal only, without namespace entry or certificate-file reads.

[systemd v259 partition discovery](https://github.com/systemd/systemd/blob/v259/src/shared/find-esp.c)
uses libblkid to inspect filesystem and partition signatures. The revision grants fixed-disk block
`read`, with `open` and `getattr` prerequisites. It adds no block writes or ioctl permission.
This is a candidate for the observed denial, not proof that subsequent libblkid operations will succeed.
Any further denial requires evidence and review; do not automatically expand the permission set.

The new block permissions are type-wide: the service can read raw contents of accessible devices
labelled fixed_disk_device_t, including devices other than XBOOTLDR. This is the material additional
exposure for review. Existing type-wide ESP writes and TPM operations remain as described above.
No partition relabel, Linux capability, permissive domain or broad device interface is added.

Offline validation passed all 31 assertions against the rebuilt exact store, including an exact
three-rule TE delta and unchanged type attributes relative to 1.0.0. The executable mapping is unchanged.
See the [revised evidence and hashes](plans/evidence/2026-09-09-hermes-selinux-revised.json).
This validates the captured policy inputs; the installer must still reject any current host drift.

### Revised installation proposal

Use [the v2 installer](../scripts/hermes/selinux/install-reviewed-candidate-v2.sh) only after explicit
production approval and the physical-console/recovery preflight above. It pins the revised module and
merged-policy hashes, retains the baseline check, and uses the exclusive backup directory
`/var/lib/hermes-selinux-trial-20260909-v2`. The first-trial installer and rollback helper remain
historical artifacts and must not be used for this revision.

The proposed next production scope is installation plus read-only loaded-policy and recovery export
validation. It does not include a service restart or reboot. Verify the loaded policy semantically against
the revised linked policy and preserve the new encrypted backups off-host before proposing service execution.
The existing service helper pins the first-trial kernel policy hash and backup path; it intentionally
cannot execute this revision. A new first-run helper must be pinned to the verified loaded policy.

If installation fails, stop and preserve the exclusive backup. Before any rollback, verify no setup
service has run since the installation preflight and preserve any changed encrypted anchors. A rollback
removes only priority-400 hermes_tpm2_setup and restores the exact executable with restorecon; require
the original baseline hash, original init_exec_t mapping and Enforcing. If any of those guards cannot be
established, retain the state for review. Do not reuse the old rollback helper's hashes or recovery paths.
The installation approval must include this bounded policy/label recovery, without TPM or boot changes.

### Approved v2 operator handoff

The user approved installation, loaded-policy/backup verification and bounded policy/label recovery.
Service restart and reboot remain outside this approval. Pinned read-only SSH confirms the original
baseline hash, packages, Enforcing and init_exec_t actual/expected label. Both units have MainPID=0;
the late unit retains the failed first-trial invocation. Noninteractive sudo requires an operator password.

The installer, reviewed module and [export helper](../scripts/hermes/selinux/export-reviewed-policy-v2.py)
are staged privately in `/home/aicowork/hermes-selinux-trial-20260909-v2`; remote hashes match the
[staging evidence](plans/evidence/2026-09-09-hermes-selinux-v2-staging.json). At the physical console
with manual recovery available, run:

```bash
sudo bash /home/aicowork/hermes-selinux-trial-20260909-v2/install-reviewed-candidate-v2.sh \
  --approved-policy-install /home/aicowork/hermes-selinux-trial-20260909-v2/hermes_tpm2_setup.pp &&
sudo python3 /home/aicowork/hermes-selinux-trial-20260909-v2/export-reviewed-policy-v2.py \
  --approved-policy-export
```

The second command runs only after the installation helper passes. It checks the installed policy,
label and backup hashes, then exports the loaded policy plus an allowlist of installation metadata and
encrypted anchor backups into the exclusive private `/home/aicowork/hermes-selinux-export-20260909-v2`.
It does not copy arbitrary state directories or start services. Supply the installer result and export
summary; never provide the sudo password or archive contents. The next gate is pinned transfer,
archive validation and loaded-policy comparison. Any command failure stops this sequence for review;
do not rerun, restart or reboot. Existing result directories are intentionally preserved.

### V2 installation and loaded policy verified

The operator installation result is independently confirmed by pinned SSH: expected disk policy hash,
dedicated executable label/mapping, unchanged packages and Enforcing. Both setup units retain their
prior start timestamps and MainPID=0; the late unit still records the failed first-trial invocation.
The two printed installer messages did not prevent these installation checks; they establish no boot result.

The [installed observation](plans/evidence/2026-09-09-hermes-selinux-v2-installed.json) records matching
operator/export hashes, safe allowlisted archive contents, preserved original file modes and private
outer export permissions. Encrypted anchors match each other and the preserved failed-trial recovery copies.
The nested policy store contains the expected original baseline. Do not rerun the installation/export handoff.

Loaded and disk policy binary hashes differ; checkpolicy CIL conversion is identical and seinfo
properties/counts match. Direct checks confirm the init transition and enforcing candidate domain.
These gates validate installation and recovery exports, not a successful service run or cold boot.
Next prepare a reviewed first-run helper pinned to the new loaded-policy hash and v2 backup directory.
Any late-service trial still requires explicit approval. The historical first-trial helper remains unsuitable.

## Approved v2 single-service trial

The original v2 helper passed 32 offline tests, syntax and workstation property parsing before staging.
These are historical preparation checks; the live preflight later exposed a missing option terminator
in a dependency query. The [local helper](../scripts/hermes/selinux/run-reviewed-service-v2.py) now contains
the correction and [33 tests](../tests/test_hermes_selinux_service_v2.py) pass; it has not been restaged.
See the original
[preparation evidence](plans/evidence/2026-09-09-hermes-selinux-v2-service-preparation.json).
No Hermes connection, remote staging, service execution or reboot occurred during preparation.
The earlier 1.0.0 failed acceptance remains historical evidence and is not upgraded by these checks.

### Approved single-service scope

On 2026-09-09 the user approved private transfer of the reviewed helper to Hermes at the pinned SSH
identity for `10.0.30.10`, verification of its hash, and **one** console-supervised invocation of
`systemd-tpm2-setup.service`, followed by read-only review of the resulting private observations.
The operator must have the physical
console and working manual LUKS recovery available. The prior password-rotation prerequisite remains in force.

Running this service can perform TPM operations and synchronize encrypted anchors in `/run`, `/var/lib`
and the ESP. The installed enforcing policy grants type-wide fixed-disk reads, ESP writes and TPM device
access, as described in the [candidate review](#revised-110-candidate-review). Approval must cover those
service effects. It does not include a second invocation, the early service, policy replacement or rollback,
anchor restoration, clearing TPM/NV state, LUKS token changes or a reboot. Policy rollback cannot undo TPM writes.

The helper pins the loaded policy
`28f3153377e6b7065dcf0e235936ffa360b1f1fdf1e68896f5fda681e020487e`, the reviewed disk policy,
package versions, executable label/mapping, installation recovery hashes and recorded service start times.
It rejects a busy setup unit, pending jobs, inactive required dependencies, propagation to other services,
extra command hooks, automatic restart and emergency actions. The expected command follows the
[systemd v259 late unit](https://github.com/systemd/systemd/blob/v259/units/systemd-tpm2-setup.service.in).
Empty command arrays are independently verified through D-Bus because systemctl can omit their text output.
Host drift requires review; the helper does not prevent independent administrator activity during a trial.

### Approved v2 single-service operator handoff

**Historical command: attempted and stopped in preflight. Do not run again.** Preserve the copied helper
and service-first directory. Continue with the [read-only diagnosis](#read-only-v2-preflight-diagnosis).
The hash below identifies the unchanged staged/attempted artifact, not the corrected local source.

The helper is **staged and independently verified** at
`/home/aicowork/hermes-selinux-trial-20260909-v2/run-reviewed-service-v2.py`. Its SHA-256 is:

```text
3ed9e2e9d8c751b1cb6281648cef4f1691b81fb480442da247b301578af51500
```

Pinned SSH checks passed for the live disk policy, executable label/mapping, package versions and idle
setup processes at their recorded invocation timestamps. The mode-0600 helper belongs to `aicowork`
inside the existing mode-0700 directory; a separate read-only hash check matches the reviewed bytes.
See the [staging observation](plans/evidence/2026-09-09-hermes-selinux-v2-service-staging.json).
Noninteractive sudo requires a password. No service invocation has occurred during staging.
Privileged policy/backup, audit and TPM/storage guards remain for the helper's preflight.

The following approved command was attempted once and is retained as historical evidence. It copies
the staged helper into the root-private backup directory, verifies the bytes and uses isolated imports.
Its preflight failure consumed the exclusive attempt; it is not a current operator instruction.

```bash
sudo sh -eu -c '
  umask 077
  src=/home/aicowork/hermes-selinux-trial-20260909-v2/run-reviewed-service-v2.py
  dst=/var/lib/hermes-selinux-trial-20260909-v2/run-reviewed-service-v2.py
  [ ! -e "$dst" ] && [ ! -L "$dst" ]
  install -o root -g root -m 0600 -- "$src" "$dst"
  printf "%s  %s\n" 3ed9e2e9d8c751b1cb6281648cef4f1691b81fb480442da247b301578af51500 "$dst" | sha256sum -c -
  exec /usr/bin/python3 -I "$dst" --approved-v2-first-run
'
```

The helper exclusively reserves `/var/lib/hermes-selinux-trial-20260909-v2/service-first` before
preflight. An existing directory blocks every rerun, including after a failed preflight. Preserve both the
copied helper and result directory; do not delete or rename them to bypass the guard. Audit date parsing,
audit health, private encrypted-anchor copies and a refreshed state comparison precede the only restart request.

### Acceptance and stop conditions

All helper checks must pass: a fresh completed invocation with `ExecMainCode=1`, `ExecMainStatus=0`,
successful conditions and service result, observed `hermes_tpm2_setup_t` execution tied to the late unit's
cgroup, no relevant AVCs and intact audit collection. Exit 76, a skipped invocation or missing process
sampling is an unmet gate. Require an encrypted anchor under the actual ESP credential directory, matching
anchor copies, preserved prior anchors/SRK/LUKS metadata, unchanged firmware/boot identity/policy/labels,
and an unchanged early unit. These observations do not establish cold-boot persistence or repeat idempotency.

Private evidence includes before/after snapshots, encrypted-anchor copies and their path maps, sampled
process domains, service states, journal, audit diagnostics and `summary.json`. Only the sanitized summary
is printed. Supply that summary; do not paste credentials, raw audit/journal records or archive contents.
If one collector fails, other observations are retained where possible and the trial cannot pass.

On any failure, timeout, missing observation or unexpected state, stop and preserve evidence. A timeout
terminates the waiting systemctl client only; the service may continue. Inspect both units read-only before
any recovery action. No automatic repeat, rollback or reboot occurs. Even a passing single-service trial
leaves separate repeat/idempotency and console-controlled cold-boot acceptance gates open under UA-05/P2.

### Read-only v2 preflight diagnosis

**Completed diagnostic, retained as history.** The operator returned before.json present, no audit/process/
restart markers, and Command failed: systemctl during read-only preflight. Continue with the
[guarded continuation](#guarded-v2-continuation); the diagnostic below is not a pending command.

The operator-reported attempt at 2026-09-09T23:10:56.604573+00:00 stopped with RuntimeError in preflight,
service_requested=false and no acceptance checks. Pinned live queries confirm both units retain their
prior invocation IDs/timestamps and no running setup processes. Enforcing and the disk policy match.
The late unit requires the root mount, -.mount. The original helper omitted -- before this unit name;
systemctl interpreted it as an option and failed. A corrected read-only live query reports active.
The local one-line correction passes 33 tests, including regression reproduction before the fix and
continued rejection of an inactive dependency. Its result directory and rerun guard are unchanged.

This proves a helper defect, but the exact original stopping point remains unverified until the protected
retained evidence is inspected. The original helper discarded exception messages, so the printed type
alone is insufficient. See the [failure observation](plans/evidence/2026-09-09-hermes-selinux-v2-preflight-failure.json).
No corrected helper was staged, and no second attempt, guard reset or reboot is authorized.

Run this read-only command in the interactive Hermes terminal. It verifies and loads the original helper
without calling main/trial, reads the saved snapshot (or takes a current read-only snapshot if absent),
and rechecks preflight. It does not save files, request a service action or change the trial guard.
Return its sanitized JSON; enter the sudo password only in the terminal. Existing result-review approval
covers this diagnostic command.

```bash
sudo python3 -I -B - <<'PYDIAG'
import hashlib, json, os
from pathlib import Path
os.environ.update(PATH="/usr/sbin:/usr/bin:/sbin:/bin", LC_ALL="C")
p = Path("/var/lib/hermes-selinux-trial-20260909-v2/run-reviewed-service-v2.py")
source = p.read_bytes()
assert hashlib.sha256(source).hexdigest() == "3ed9e2e9d8c751b1cb6281648cef4f1691b81fb480442da247b301578af51500"
ns = {"__name__": "read_only_review"}
exec(compile(source, str(p), "exec"), ns)
t = p.parent / "service-first"
names = ("before.json", "audit-before.json", "audit-preflight.json", "process-observation.json", "restart.log")
result = {"files_present": {name: (t / name).is_file() for name in names}}
phase = "retained-before" if (t / "before.json").is_file() else "current-snapshot"
try:
    before = json.loads((t / "before.json").read_text()) if phase == "retained-before" else ns["snapshot"]()
    phase = "read-only-preflight"
    ns["preflight"](before)
    result["preflight"] = "PASS"
except Exception as error:
    result["error"] = {"phase": phase, "type": type(error).__name__}
    if isinstance(error, RuntimeError):
        result["error"]["reason"] = str(error)
print(json.dumps(result, indent=2))
PYDIAG
```

## Guarded v2 continuation

The protected diagnostic confirms a retained snapshot and a systemctl preflight failure before audit
collection. Independent live reproduction identifies the missing -- before -.mount; the corrected query
returns active. Both unit invocation IDs/timestamps remain unchanged. The original helper did not retain
the exact failing argv, so attribution combines these observations; it is not a captured command trace.

The existing approval covers private staging, one console-supervised late-service invocation with the
previously reviewed TPM/encrypted-anchor effects, and read-only result review. That invocation has not
occurred. This continuation keeps that scope and does not require another permission request. Console,
manual LUKS recovery and the recorded password-rotation prerequisites remain in force. No repeat service
invocation, early-service restart, policy/anchor recovery, TPM clear, LUKS modification or reboot is included.

### Continuation guards and artifacts

The [continuation wrapper](../scripts/hermes/selinux/continue-reviewed-service-v2.py) loads the exact
[corrected core](../scripts/hermes/selinux/run-reviewed-service-v2.py) without calling its original main.
It requires the original root-private helper hash and an exact failed summary timestamped
2026-09-09T23:10:56.604573+00:00, with false service_requested, false passed and only the recorded error.
The old result directory must contain exactly before.json and summary.json; unexpected files or request
markers stop execution. Root ownership, private modes, regular file types, no symlinks/hardlinks and
unambiguous JSON are required. Recorded invocation IDs and the root-mount dependency must match.

The wrapper preserves the old files and exclusively creates
`/var/lib/hermes-selinux-trial-20260909-v2/service-continuation-1`. Its existence blocks all reuse, including
after another preflight failure. Both fresh preflight snapshots must exactly match the retained failed-attempt
snapshot, and prior evidence bytes must remain unchanged. The corrected dependency query uses -- before
unit names. All other runtime, audit, domain, ESP-anchor and preservation checks remain in effect.
Acceptance additionally requires the original attempt to remain unchanged after observation.

Private diagnostics retain failing command arguments and operation reasons. Only sanitized summary fields
are printed. No automatic repair, rollback, retry or reboot occurs. The earlier preflight failure remains
failed evidence. [52 offline tests](../tests/test_hermes_selinux_continuation_v2.py) cover the 33 core and 19
continuation cases; see the [continuation evidence](plans/evidence/2026-09-09-hermes-selinux-v2-continuation.json).

| Artifact staged under the operator-private v2 directory | SHA-256 |
| --- | --- |
| run-reviewed-service-v2-corrected.py | 6fd1a7c96efc3729173d321398ce0b111f2d5f0cea46df6b0c2d9c2605f3ec07 |
| continue-reviewed-service-v2.py | fd2546742abdba2d7d568a4af31d481a96084dbcea5829cfbc832430bb5e7ab1 |

### V2 continuation operator handoff

**Historical command: attempted and stopped during preflight. Do not run again.** Both source hashes
verified; the operator reports service_requested=false at 2026-09-09T23:39:18.235067+00:00. The continuation
directory is consumed. Use the [read-only saved diagnostic](#read-only-continuation-failure-diagnostic).

Both continuation artifacts are staged and independently verified with the hashes above, mode 0600
and operator ownership inside the existing mode-0700 directory. The original staged helper hash remains
unchanged. Live unprivileged policy/label/package and unit-identity checks pass. Noninteractive sudo needs
a password. Preserve both original attempt files and its helper; the service-first command remains historical.

The following command is retained as the attempted handoff, not a current operator instruction. It
refuses existing destinations, copies with noclobber, verifies both hashes and invokes the guarded wrapper.

```bash
sudo sh -eu -c '
  umask 077
  src=/home/aicowork/hermes-selinux-trial-20260909-v2
  dst=/var/lib/hermes-selinux-trial-20260909-v2
  core=run-reviewed-service-v2-corrected.py
  wrapper=continue-reviewed-service-v2.py
  for name in "$core" "$wrapper"; do
    if [ -e "$dst/$name" ] || [ -L "$dst/$name" ]; then
      printf "%s\n" "STOP: destination exists; preserve evidence" >&2
      exit 1
    fi
  done
  set -C
  for name in "$core" "$wrapper"; do
    cat "$src/$name" > "$dst/$name"
  done
  printf "%s  %s\n" 6fd1a7c96efc3729173d321398ce0b111f2d5f0cea46df6b0c2d9c2605f3ec07 "$dst/$core" fd2546742abdba2d7d568a4af31d481a96084dbcea5829cfbc832430bb5e7ab1 "$dst/$wrapper" | sha256sum -c -
  exec /usr/bin/python3 -I -B "$dst/$wrapper" --approved-v2-continuation
'
```

On any failure, stop and preserve both attempt directories and all helpers. Do not remove or rename a
guard to retry. A passing result would establish only the single-service gate; repeat/idempotency and
cold-boot acceptance remain separate open gates under UA-05/P2.

### Read-only continuation failure diagnostic

**Completed diagnostic, retained as history.** It identifies query_audit as the failed operation, with
matching snapshots and no request markers. Continue with the [audit metadata diagnostic](#audit-query-metadata-diagnostic).

The second attempt reports preflight RuntimeError with no service request. Independent pinned SSH confirms
both unit identities/timestamps and idle processes remain unchanged, as do Enforcing, the disk-policy hash
and all staged helper hashes. The generic printed error does not establish the failed guard. Do not assume
it is another root-mount parsing failure or a new SELinux denial.

After two failed preflights, inspect the saved operation/command diagnostics and old/new snapshot differences
before any further helper change or attempt. Preserve service-first, service-continuation-1 and all helpers.
This read-only command needs operator sudo, which remains unavailable noninteractively. Existing result-review
approval covers it. It reads known JSON files, prints diagnostic reason/type, bounded command identity,
audit-health fields and changed snapshot field names. It does not load helper code, print snapshot values,
change files or request a service action. Return its JSON output; enter the password only in the terminal.

```bash
sudo python3 -I -B - <<'PYDIAG'
import json
from pathlib import Path
root = Path("/var/lib/hermes-selinux-trial-20260909-v2")
trial = root / "service-continuation-1"
result = {"diagnostics": {}}
operations = ("snapshot", "preflight", "audit_status", "query_audit", "journal_cursor", "preserve_anchors")
for name in ("command-failure.json", *("diagnostic-" + x + ".json" for x in operations)):
    p = trial / name
    if p.is_file():
        data = json.loads(p.read_text())
        result["diagnostics"][name] = {k: data[k] for k in ("operation", "type", "reason") if k in data}
        if "argv" in data:
            result["diagnostics"][name]["command"] = data["argv"] if data["argv"][0] == "systemctl" else data["argv"][:1]
names = ("before.json", "audit-before.json", "audit-preflight.json", "journal-before.json", "audit-ready.json", "process-observation.json", "restart.log")
result["files_present"] = {name: (trial / name).is_file() for name in names}
if (trial / "audit-before.json").is_file():
    audit = json.loads((trial / "audit-before.json").read_text())
    result["audit_health"] = {k: audit.get(k) for k in ("enabled", "pid", "lost", "backlog")}
if (trial / "before.json").is_file():
    old = json.loads((root / "service-first/before.json").read_text())
    new = json.loads((trial / "before.json").read_text())
    result["changed_snapshot_fields"] = sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))
    result["changed_unit_fields"] = {u: sorted(k for k in old["units"][u].keys() | new["units"][u].keys() if old["units"][u].get(k) != new["units"][u].get(k)) for u in old["units"].keys() & new["units"].keys()}
print(json.dumps(result, indent=2))
PYDIAG
```

See the [continuation failure observation](plans/evidence/2026-09-09-hermes-selinux-v2-continuation-failure.json).
No new attempt, guard removal/rename, helper change or reboot follows until the saved diagnostics are reviewed.

### Audit query metadata diagnostic

**Completed diagnostic, retained as history.** The returned metadata is reviewed below; use the
[audit continuation handoff](#v2-audit-continuation-operator-handoff) after staging validation passes.

The operator reports matching old/new snapshots and unit fields. The audit daemon status reports enabled=1,
pid=1182, lost=0 and backlog=0. The first query then fails with Audit query failed; absence of denials is
unverified. No journal cursor, refreshed audit-ready state, process observation or restart log exists.
This isolates the failing operation; it does not establish a query parser error or absence of AVCs.

The helper retains its query arguments, return code and stderr in audit-preflight.json. Read those fields
and only the stdout size/exact no-matches classification below. The raw .log stays private. This reads
existing files under the previously approved result-review scope and changes no host state. Return the JSON;
enter the sudo password only in the terminal. Do not execute either helper, reset a guard or reboot.

```bash
sudo python3 -I -B - <<'PYDIAG'
import json
from pathlib import Path
p = Path("/var/lib/hermes-selinux-trial-20260909-v2/service-continuation-1")
result = json.loads((p / "audit-preflight.json").read_text())
output = (p / "audit-preflight.log").read_bytes()
result["stdout_bytes"] = len(output)
result["stdout_is_no_matches"] = output.strip() == b"<no matches>"
print(json.dumps(result, indent=2))
PYDIAG
```

## Guarded audit continuation

The operator returned exit 1, empty stderr and zero raw stdout bytes. The recorded version-matched
Audit 4.2.1 source review and installed-binary synthetic probes identify the raw no-match output contract.
The earlier query did not force log input, so that old result cannot establish absence of denials.
The [audit wrapper](../scripts/hermes/selinux/continue-reviewed-service-v2-audit.py) requires the exact
installed audit packages, uses --input-logs with closed stdin, and accepts a silent raw exit 1 only when
a second default-format query returns exit 1, empty stdout and exactly the no-matches stderr marker.
Warnings, argument/read errors and inconsistent results fail the gate. Raw records remain private.

Both failed attempts, their exact summaries, linked evidence and matching snapshots must pass admission.
The wrapper pins and reuses the unchanged prior wrapper and corrected core. It exclusively reserves
service-continuation-2; any existing reservation blocks execution. Prior evidence is rechecked before
request and during acceptance. All original policy, audit, domain, encrypted-anchor and service guards
remain active. The 74 offline tests pass; installed synthetic probes establish formatting only, not
privileged live-log acceptance. See the
[audit continuation evidence](plans/evidence/2026-09-09-hermes-selinux-v2-audit-continuation.json).

### V2 audit continuation operator handoff

**Consumed on 2026-09-10 at 13:25 UTC; historical command, do not run again.** The service was requested
and runtime acceptance failed. Continue only with the [read-only diagnostic](#read-only-v2-runtime-failure-diagnostic).
The following staging and approval description records the pre-invocation state.

Staging validation **passed on 2026-09-10 at 13:11 UTC**. A separate pinned SSH readback verified the
reviewed SHA-256 below, regular single-link file type, operator ownership, file mode 0600 and directory
mode 0700. All prior helper hashes and late/early service invocation fields are unchanged. See the
[staging observation](plans/evidence/2026-09-09-hermes-selinux-v2-audit-continuation.json).
No helper execution or service request occurred during staging.
The existing approval covers the same one real late-service invocation, which neither failed attempt
requested. Physical console, working manual LUKS recovery and the password-rotation prerequisite remain
required. Interactive sudo is needed. No repeated invocation, early-service action, rollback, TPM clear,
LUKS change or reboot is included.

Only the new audit wrapper is copied. Preserve the original helper, corrected core, prior wrapper and
both consumed result directories. The command refuses an existing root destination, copies privately
with noclobber, checks the reviewed hash and invokes the wrapper once.

```bash
sudo sh -eu -c '
  umask 077
  src=/home/aicowork/hermes-selinux-trial-20260909-v2/continue-reviewed-service-v2-audit.py
  dst=/var/lib/hermes-selinux-trial-20260909-v2/continue-reviewed-service-v2-audit.py
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    printf "%s\n" "STOP: destination exists; preserve evidence" >&2
    exit 1
  fi
  set -C
  cat "$src" > "$dst"
  printf "%s  %s\n" 0733fc3d33b04da645ab71e204479e3de3361bc7b72675d82fb72c095b8453f3 "$dst" | sha256sum -c -
  exec /usr/bin/python3 -I -B "$dst" --approved-v2-audit-continuation
'
```

On failure, preserve all three attempts and every helper; do not remove or rename guards or retry.
Return only the sanitized summary. A passing result establishes the single-service gate; repeat/idempotency
and console-controlled cold-boot acceptance remain separate open gates under UA-05/P2.

## Read-only v2 runtime failure diagnostic

**Completed; retained as history.** All 22 records were parsed into the groups below. Continue with the
[request-code diagnostic](#read-only-ioctl-request-metadata); do not repeat the grouping command.

The operator summary reports intact audit collection and 22 scoped AVC records. Their exact permissions
and target types are not in that summary. The live unit reports exit 1; this does not establish which
denial caused the exit or missing ESP anchor. The
[failure observation](plans/evidence/2026-09-10-hermes-selinux-v2-runtime-failure.json) separates the operator
report from independent live checks. The prior invocation is consumed; no retry or reboot follows.

At the Hermes console as aicowork, run the read-only command below and enter the sudo password locally.
Existing result-review approval covers this command. It reads only the saved scoped-avcs.log, checks its
file type/owner/mode and bounds, and prints counts grouped by source type, target type, object class and
denied permissions. It omits raw filenames, paths, commands and journal records. A permissive value of
-1 means the field was absent. Unparsed records are counted; they are not treated as absence of denials.
No helper is imported, service requested or file changed. Return this JSON only.

```bash
sudo python3 -I -B - <<'PYDIAG'
import collections, hashlib, json, os, re, stat
from pathlib import Path
p = Path("/var/lib/hermes-selinux-trial-20260909-v2/service-continuation-2/scoped-avcs.log")
if any(q.is_symlink() for q in p.parents):
    raise SystemExit("STOP: unexpected evidence path")
with os.fdopen(os.open(p, os.O_RDONLY | os.O_NOFOLLOW), "rb") as f:
    info = os.fstat(f.fileno())
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
            or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
            or info.st_size > 2 * 1024 * 1024):
        raise SystemExit("STOP: unexpected evidence file")
    data = f.read(2 * 1024 * 1024 + 1)
if len(data) > 2 * 1024 * 1024:
    raise SystemExit("STOP: evidence exceeds limit")
rows = [line for line in data.decode("utf-8").splitlines() if line.strip()]
groups = collections.Counter()
unparsed = 0
for line in rows:
    source = re.search(r"\bscontext=[^:\s]+:[^:\s]+:([a-zA-Z_][a-zA-Z0-9_]*_t):", line)
    target = re.search(r"\btcontext=[^:\s]+:[^:\s]+:([a-zA-Z_][a-zA-Z0-9_]*_t):", line)
    kind = re.search(r"\btclass=([a-z][a-z0-9_]*)\b", line)
    perms = re.search(r"\bavc:\s+denied\s+\{\s*([a-z_ ]+?)\s*\}", line)
    enforcing = re.search(r"\bpermissive=([01])\b", line)
    if not all((source, target, kind, perms)):
        unparsed += 1
        continue
    key = (source[1], target[1], kind[1], tuple(sorted(set(perms[1].split()))),
           int(enforcing[1]) if enforcing else -1)
    groups[key] += 1
print(json.dumps({
    "scoped_log_sha256": hashlib.sha256(data).hexdigest(),
    "record_count": len(rows), "unparsed_records": unparsed,
    "groups": [{"source_type": s, "target_type": t, "class": c,
                "permissions": list(perms), "permissive": mode, "count": count}
               for (s, t, c, perms, mode), count in sorted(groups.items())]
}, indent=2))
PYDIAG
```

## Denial review after the v2 runtime failure

The operator's pinned scoped log contains 22 records with no unparsed entries, all from
hermes_tpm2_setup_t with permissive=0:

| Target type | Object class | Denied permission | Records | Remaining question |
| --- | --- | --- | --- | --- |
| cert_t | file | read | 1 | Which public certificate/config file was requested? |
| fixed_disk_device_t | blk_file | ioctl | 20 | Which numeric ioctl commands were requested? |
| fs_t | filesystem | getattr | 1 | Live /boot filesystem-type check reports Permission denied |

Read-only journal review finds the /boot filesystem check failure followed by ESP discovery failure;
findmnt reports xfs at /boot. This is consistent with the fs_t denial. The upstream v259
[ESP search](https://github.com/systemd/systemd/blob/v259/src/shared/find-esp.c) returns access failures
while examining its boot candidates, and
[anchor writing](https://github.com/systemd/systemd/blob/v259/src/shared/tpm2-util.c) first resolves the
boot credential directory. Exact Fedora systemd 259.8 source was not retrieved; v259.8 upstream lookup
returned 404. These version-family sources support the explanation without proving downstream identity.

Installed util-linux/libblkid is 2.41.5. Its
[block helpers](https://github.com/util-linux/util-linux/blob/v2.41.5/lib/blkdev.c) contain size/sector/geometry
queries, but the count alone cannot identify the observed calls.
[SELinux extended permissions](https://github.com/SELinuxProject/selinux/blob/master/secilc/docs/cil_access_vector_rules.md#allowx)
can constrain ioctl request numbers alongside the ordinary ioctl permission. Obtain the actual numbers
before drafting those grants. The certificate/config identity is also required; the 1.1.0 policy and
its verifier intentionally exclude certificate-file reads. The policy, verifier and all helpers remain unchanged.

### Read-only ioctl request metadata

At the Hermes console, run this command and return only its JSON. It reads the same saved scoped log,
requires its previously reported SHA-256, and prints numeric ioctl command counts plus recognized public
certificate/config basenames. Other names are reported as unidentified; raw audit text remains private.
The prior invocation is consumed. This command does not run a helper, query live audit logs, change
files, alter policy or request a service. Existing read-only review approval covers it.

```bash
sudo python3 -I -B - <<'PYDIAG'
import collections, hashlib, json, os, re, stat
from pathlib import Path
p = Path("/var/lib/hermes-selinux-trial-20260909-v2/service-continuation-2/scoped-avcs.log")
if any(q.is_symlink() for q in p.parents):
    raise SystemExit("STOP: unexpected evidence path")
with os.fdopen(os.open(p, os.O_RDONLY | os.O_NOFOLLOW), "rb") as f:
    info = os.fstat(f.fileno())
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
            or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
            or info.st_size > 2 * 1024 * 1024):
        raise SystemExit("STOP: unexpected evidence file")
    data = f.read(2 * 1024 * 1024 + 1)
if len(data) > 2 * 1024 * 1024:
    raise SystemExit("STOP: evidence exceeds limit")
expected = "896a6d7f3e58ce4e16480ff94e0391cca9244604dbed679a0e4e1a1a4779b32c"
if hashlib.sha256(data).hexdigest() != expected:
    raise SystemExit("STOP: saved log differs from reviewed evidence")
rows = [line for line in data.decode("utf-8", errors="replace").splitlines() if line.strip()]
ioctls = [line for line in rows if re.search(r"\bavc:\s+denied\s+\{\s*ioctl\s*\}", line)]
requests = collections.Counter()
missing = 0
for line in ioctls:
    match = re.search(r"\bioctlcmd=(0x[0-9a-fA-F]{1,8}|[0-9]{1,10})(?=\s|$)", line)
    if match:
        value = int(match[1], 16 if match[1].startswith("0x") else 10)
        requests[hex(value)] += 1
    else:
        missing += 1
certs = []
for line in rows:
    if not re.search(r"\btcontext=[^:\s]+:[^:\s]+:cert_t:", line):
        continue
    match = re.search(r'\bname="([^"\n]*)"', line)
    name = match[1] if match else ""
    known = name if name in {"openssl.cnf", "ca-bundle.crt", "ca-bundle.trust.crt", "openssl-fips.cnf"} else "unidentified"
    certs.append({"known_public_basename": known, "name_field_present": bool(match)})
print(json.dumps({"scoped_log_sha256": expected, "record_count": len(rows),
    "ioctl_records": len(ioctls), "missing_ioctl_commands": missing,
    "ioctl_commands": dict(sorted(requests.items())), "certificate_records": certs}, indent=2))
PYDIAG
```
