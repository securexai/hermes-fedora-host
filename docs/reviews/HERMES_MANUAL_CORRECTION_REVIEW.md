# Hermes correction handoff — independent offline review

**Verdict: changes requested.** The handoff fingerprint and every reported offline test result were
independently reproduced. Five remaining issues prevent accepting the correction pass as complete.
Three are reproduced failure paths; two are confirmed command/identity defects whose actual guest
DAC/SELinux effects remain untested. No deployment or implementation changes were performed.

Review started **2026-09-20T12:47:57-05:00**; environment rechecked at **12:54:40-05:00** (America/Bogota).
This follow-up preserves the [original review](/var/home/aicloudopspecial/code/repos/fedora-virtualization-host/docs/HERMES_MANUAL_OFFLINE_REVIEW.md) as historical evidence.

## 1. Verified input identity

| Item | Independently observed value |
| --- | --- |
| Repository | `/var/home/aicloudopspecial/code/repos/mikrotik` |
| Branch | `codex/hermes-fedora44-manual-review` |
| HEAD | `2340887183f75f30215088f37b39bf63a0a453c0` |
| Changed tracked / untracked | 31 / 9 (40 files) |
| Tracked diffstat | 1461 insertions, 497 deletions |
| Dirty-input SHA-256 | `6219b73768a098fb44c93b95b67d9d9430cb9132ce884c2d01399c1a361d8ee2` |
| Environment | Fedora 44 Kinoite `44.20260918.0`; Bash 5.3.9; Python 3.14.7; PyYAML 6.0.3 |

Fingerprint method: sort unique changed tracked and untracked relative paths; aggregate
`path.encode() + b'\0' + sha256(file_bytes).digest()` using SHA-256. It matched before testing and after
counterexample replay. The implementation checkout was not edited. The handoff's explanation of the
execution record's pre-final-write digest is consistent with the independently observed final digest.

## 2. Findings

### C1 — P2: EXIT trap still turns cleanup failure into success (R3 remains open)

**Location:** [lib-manual-common.sh:335–370](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/lib-manual-common.sh#L335-L370),
[finalization:93–127](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/lib-manual-common.sh#L93-L127).

Returning nonzero from `mp_run_cleanup` is insufficient: the EXIT trap saves the pre-cleanup status,
discards cleanup's return value, and exits with the saved value even when it is zero. Moreover,
`mp_finalize` prints PASS before the exit trap runs required cleanup.

**Reproduced with the real library and a deliberately failing synthetic cleanup hook:**

```text
check_total=1 check_fail=0 check_unverified=0 check_deferred=0
RESULT=PASS
CLEANUP_FAILED hook=bad (the primary status is preserved)
process exit: 0
```

The control case preserves an existing exit 7, as desired. The missing case is successful primary work
followed by failed cleanup. The [new test:133–138](/var/home/aicloudopspecial/code/repos/mikrotik/tests/test-hermes-manual-review.sh#L133-L138)
checks `mp_run_cleanup` directly, not its integration with the trap/finalizer, so it misses the defect.

**Required correction:** run required cleanup before publishing the final success result; if there is
no existing primary failure, propagate cleanup failure. Preserve an existing nonzero primary status
and the conventional interruption statuses. Test the actual finalizer/EXIT path, including temporary
state removal failure, rather than only the cleanup function's return value.

### C2 — P2: unknown initial service state lets backup strand both services (R3)

**Location:** [m04-backup.sh:60–90](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m04-backup.sh#L60-L90).

Both initial `is-active` failures are suppressed with `|| true`. Unknown state becomes an empty string;
the helper still stops the services, but restoration only restarts those recorded literally `active`.
If the initial queries fail transiently and later commands work, the archive passes and restoration
reports PASS while previously active services remain stopped.

**Reproduced using the real backup helper and its existing synthetic fixture:** both services start
active; only queries before the first stop fail. Subsequent stop, inactive-query, inventory, and archive
operations work normally.

```text
CHECK writers_stopped=PASS
CHECK backup_archive=PASS
RESULT=PASS
ACTUAL_EXIT=0 FINAL_WORKER=inactive FINAL_GATEWAY=inactive
CHECK restore_service_state=PASS
```

This is separate from R2: the strengthened checks correctly establish stopped writers before the
archive, but do not establish the pre-operation state needed for restoration. Similar unchecked prior
state snapshots exist in [m02:82–98](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m02-deploy-and-validate.sh#L82-L98)
and [m03-configure:100–115](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m03-configure-and-probe.sh#L100-L115);
the complete loss-of-state reproduction here targets backup.

**Required correction:** validate the prior state before lifecycle mutation, distinguish a legitimate
inactive response from an error/transitional state, and refuse mutation when restoration obligations
cannot be determined. Add an initially-active/transient-initial-query-failure case that proves no service
is stranded and no false restoration PASS is emitted.

### C3 — P2: live configuration/probe commands lose the runtime UID (R10 regression)

**Location:** [m03-configure-and-probe.sh:92–98](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m03-configure-and-probe.sh#L92-L98),
[probe:249–258](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m03-configure-and-probe.sh#L249-L258).

The inactive branch explicitly uses UID/GID 10000 and the required working directory, but the new live
branch calls `podman exec "$GW" "$@"` without either option. Exec does not inherit the supervised
application process's dropped UID. This is especially significant for the s6 image, whose user command
is [documented as dropping to UID 10000](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m02-deploy-and-validate.sh#L15-L17).
The gateway [Quadlet](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/quadlets/hermes-gateway.container#L6-L52)
does not select that container user.

**Observed through the actual live helper call path:**

```text
===== real backend probe as UID 10000 =====
CHECK terminal_backend_probe=PASS
podman exec hermes-gateway /opt/hermes/bin/hermes config get terminal.backend
```

The command observation is reproduced; the real image's effective UID was **not** measured. The helper
cannot substantiate its advertised UID-10000 proof with these arguments. Running as the bootstrap/default
user can fail access or produce a misleading permission/transport PASS instead of testing the gateway's
actual identity. Existing mocks do not enforce a user selection.

**Required correction:** retain explicit `--user 10000:10000 --workdir /opt/hermes` on live exec, as already
specified by the [probe's documented invocation](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/gateway/m03-probe.py#L4-L7)
and [postboot caller](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m04-postboot.sh#L94-L99).
Add argument/identity-sensitive coverage and eventually verify effective UID/GID in the authorized guest.

### C4 — P2: failed/unknown status is treated as permission to relabel (R10)

**Location:** [m03-configure-and-probe.sh:81–98](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m03-configure-and-probe.sh#L81-L98).

`gw_active` suppresses query failure and tests only for literal `active`. Every other result—including
an unreadable user bus or `deactivating`—selects `gcone`, creating new `:Z` mounts of the private SSH
material. A unit not known to be active is not proof that its container has stopped.

**Reproduced with the real helper:** the fixture's container remains active, but all service queries
fail. The helper uses eleven one-shot state mounts and still declares no relabel/no lifecycle change:

```text
profile terminal config and probe already converged; no service stop and no relabel
RESULT=PASS (PARTIAL: 1 check(s) deferred to a later gate; no required check failed)
ACTUAL_EXIT=0 SYNTHETIC_CONTAINER_STATE=active
podman-run-state-mount gateway_active=yes    # 11 occurrences
```

The actual SELinux effect is not reproduced; the unsafe branching and mount arguments are. The same
principle applies to the [post-stop gate:157–163](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m03-configure-and-probe.sh#L157-L163),
which records but does not require a successful stop status and does not establish container absence.

**Required correction:** represent active/stopped/unknown separately. Failed or transitional queries
must block relabeling/mutation, not select the one-shot path. Require conclusive service/container
quiescence before using live private paths. Cover query failure, transitional state, and a running
container despite a non-active unit.

### C5 — P2: contract application still privately relabels the live gateway's SSH tree

**Location:** [m03-contract.sh:59–68](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m03-contract.sh#L59-L68),
[application calls:127–163](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m03-contract.sh#L127-L163).

The contract helper always launches one-shot containers mounting the real gateway SSH directory with
`:ro,Z`; it neither establishes that the gateway is stopped nor restores its labels/state. `ro` prevents
container writes but does not prevent Podman's host-side SELinux relabeling. A new private MCS label can
invalidate the running gateway's access to its key, trust material, and shims.

The [planned sequence](/var/home/aicloudopspecial/code/repos/mikrotik/docs/plans/2026-09-20-hermes-manual-gate2-lab-plan.md#L298-L307)
places this helper after gateway activation/configuration. The issue also applies to later converged
reruns with a healthy active gateway. Fixing only the configure helper's happy path does not protect
that sequence.

**Actual contract-helper command path, existing fixture with a synthetic active gateway:**

```text
CHECK contract_verified=PASS
RESULT=PASS (PARTIAL: 4 check(s) deferred to a later gate; no required check failed)
ACTUAL_EXIT=0 PRIVATE_Z_RUNS=4 QUIESCE_CALLS=0 SYNTHETIC_GATEWAY=active
```

This confirms the mount/lifecycle command sequence, **not** a live SELinux denial. The simulated gateway
stays active because no stop is issued; Podman itself remains stubbed.

**Required correction:** avoid mounting/relabeling the active gateway's private material. Use a
non-relabeling path for live execution or safely isolated helper material, with explicit identity and
state checks; quiesce and restore only when genuinely needed. Exercise contract-after-active-configure
and second/third-run scenarios, including the private SSH mount—not just explicit `chcon` calls.

## 3. R1–R10 disposition

“Corrected offline” below addresses the original specific defect, not runtime acceptance or a claim
that the whole helper has no further defects.

| Original finding | Independent disposition |
| --- | --- |
| R1 mapped ownership | Original host-owner reset corrected in source and 15-check fixture. Fresh/legacy directory mapping is requested via rootless namespace chown; valid UID mapping is retained. Real DAC/SELinux unverified. C5 is a separate contract-helper issue. |
| R2 stopped writers | Corrected offline: service status and value, stop result, and successful container inventory are required. 34-check backup suite passes. C2 concerns the distinct prior-state/restoration obligation. |
| R3 cleanup/restoration | **Not complete:** C1 and C2 reproduce false-success/restoration gaps. Explicit restart-failure checks and signal statuses are improvements and pass existing tests. |
| R4 installer | Original hidden install-error and mode-drift defects corrected offline; no-op mode reconciliation verified. No claim of live filesystem/SELinux acceptance. |
| R5 provisioning lock | Corrected offline: all three entrypoints take the common lock before mutation; contention suite passes. |
| R6 M01 temp registration | Original pipeline-registration leak corrected: allocation is now in trap-owning parent. 9-check bounded fixture passes. Full successful M01 execution is intentionally not run; C1 still affects failed cleanup generally. |
| R7 DNS grading | Original missing-tool/incorrect-status defect corrected; actual marked grading block and classifier cases pass. Resolver execution in a guest remains unverified. |
| R8 exact replacement verifier | Corrected offline: extra platform toolsets rejected, apply removes them, unmanaged fields preserved. |
| R9 environment check | Original non-writing environment drift check corrected in source; hardening tests pass. No live environment read. |
| R10 convergence | Healthy active/inactive happy paths improve, but **not complete:** C3/C4 affect live identity and failure safety; C5 leaves the overall helper sequence unsafe for live private mounts. |

The [canonical record §10](/var/home/aicloudopspecial/code/repos/mikrotik/docs/plans/2026-09-20-hermes-manual-review-corrections.md#L292-L328)
should not retain an unqualified GREEN/completed disposition for R3/R10 after these findings. Its
historical red-to-green claims were not independently witnessed; this review reran the final suites and
added counterexamples without reverting or modifying the implementation.

## 4. Fresh validation

Direct fallback runs, completed **2026-09-20T12:49:32-05:00** from the implementation repository.
All suite results exactly matched the handoff:

| Command | Fresh result |
| --- | --- |
| `bash tests/test-hermes-manual-profile.sh` | 358 passed / 0 failed |
| `bash tests/test-hermes-manual-review.sh` | 111 / 0 |
| `bash tests/test-hermes-manual-backup.sh` | 34 / 0 |
| `bash tests/test-hermes-manual-configure.sh` | 33 / 0 |
| `bash tests/test-hermes-manual-contract.sh` | 15 / 0 |
| `bash tests/test-hermes-manual-m01-tempdir.sh` | 9 / 0 |
| `bash tests/test-hermes-guide.sh` | 217 / 0 |
| `python3 -B -m unittest discover -s tests -p test_hermes_manual_hardening.py` | 21 tests OK |
| `bash scripts/hermes/manual/boot/rehearse-clean-install.sh` | PASS; 0 failures, 0 advisories |
| `bash -n` for changed/untracked shell files | 28 files PASS |
| Python AST parsing, no bytecode | 3 files PASS |
| `git diff --check` | PASS |

The install-permission diagnostic in the review suite is expected fault injection, not a suite failure.
A grep escape warning was also emitted. No tool was installed. Devbox, ShellCheck, shfmt,
markdownlint-cli2 and ShellSpec remain absent; lint/format/hooks are **NOT RUN**, not replaced by syntax
checks. These suites do not establish runtime correctness.

## 5. Replay the counterexamples

The [replay script](/var/home/aicloudopspecial/code/repos/fedora-virtualization-host/docs/HERMES_MANUAL_CORRECTION_REPRO.py) uses only Python's standard library and the
already-reviewed Bash fixture setup. It injects faults into fixture text **in memory**, executes the real
helpers against synthetic temporary trees, and leaves implementation files untouched. It refuses any
different dirty-input fingerprint to avoid silently executing changed, unreviewed fixture setup.

From the review workspace:

```bash
python3 -B docs/HERMES_MANUAL_CORRECTION_REPRO.py
```

Observed final output:

```text
OBSERVED C1 cleanup failure still exits 0 after PASS
OBSERVED C2 unknown prior state permits backup to leave formerly active services stopped
OBSERVED C3 live exec omits the required runtime UID/GID
OBSERVED C4 unknown service state permits live-mount relabeling commands and PASS
OBSERVED C5 contract helper mounts live private material with :Z without quiescence
REVIEW_REPRO=FAIL open=5
```

Expected exit for this reviewed tree is **1** (five observed issues); exit 2 means setup/input mismatch.
C1/C2/C4 are executable failure-path reproductions. C3/C5 record actual helper command selection; their
real image identity/SELinux consequences are source-derived and explicitly remain runtime-unverified.
The replay is review evidence, not a substitute for permanent regression tests in the implementation repo.

## 6. Boundary and next action

No implementation edits, lab/production contact, installed-grant or host changes, real credential
access/provisioning, provider calls, package installation, commits, or pushes occurred. Existing dirty
work and the original review were preserved. Tests used synthetic fixtures; the rehearsal generated
only its disposable synthetic key material, not deployed credentials.

**Next action:** correct C1–C5 and add the missing failure/identity/sequence regressions, then obtain a
fresh independent offline review. Deployment remains paused after Gate 2 Phase 5. Real rootless Podman,
SELinux, systemd interruption/recovery, and reboot acceptance require separate authorization. This review
does not authorize or request deployment.
