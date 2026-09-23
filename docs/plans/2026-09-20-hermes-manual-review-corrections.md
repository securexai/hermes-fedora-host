# Hermes manual profile — Gate 2 review corrections

Record state: **ACTIVE / implementation complete, offline-validated.** Created 2026-09-20
(America/Bogota). This is the canonical execution record for correcting the eleven review findings
raised against branch `codex/hermes-fedora44-manual-review` at reviewed HEAD `2340887`.

**Parent records:** [Gate 2 lab plan](2026-09-20-hermes-manual-gate2-lab-plan.md) (§0 is the
authoritative runtime status) and
[manual-profile improvement plan](2026-09-20-hermes-manual-profile-improvement.md).

## 1. Authorization and boundaries

- Authorized: read both repositories, edit this repository on this branch, add regression tests, run
  offline tests and syntax checks.
- **Not authorized and not performed:** commits, pushes, PR changes, privileged grants, deployment-target
  contact or mutation, VM creation/destruction, host configuration, credential provisioning,
  paid/provider calls, or resuming Gate 2 deployment.
- Historical approvals in the plan records are evidence, not current authorization. The stopping point
  remains after Gate 2 Phase 5; Phases 6–7 and Gate 3 stay **NOT RUN**.
- No real credential appears in a fixture, log, or test output. Test secrets are assembled at runtime
  or written through a format string, so no scanner-friendly `KEY=value` literal was added.

## 2. Tested revision identity

| Item | Value |
| --- | --- |
| Branch | `codex/hermes-fedora44-manual-review` |
| Base / reviewed HEAD | `2340887183f75f30215088f37b39bf63a0a453c0` (`2340887`) |
| Working tree | 29 modified files, 6 new files; **all results below apply to the dirty working tree**, not to a commit |
| Diffstat | `29 files changed, 1120 insertions(+), 432 deletions(-)` plus the untracked files |
| Environment | Fedora Linux 44 Kinoite (`44.20260918.0`), Bash 5.3.9, Python 3.14.7 with PyYAML 6.0.3 |

Reconnaissance confirmed the reviewed revision was checked out with a clean tree, so every finding was
revalidated against exactly the reviewed source and no unrelated work needed reconciling.

Tooling gap: `shellcheck`, `shfmt`, `markdownlint-cli2`, `shellspec` and `devbox` are **not installed**,
so the Lefthook lint/format/hook checks could not run. Substitutes actually run: `bash -n` over every
touched shell file, `python3 -m py_compile`, `git diff --check`, the repository suites listed in §5,
and the clean-install rehearsal. This limitation is repeated in §7.

## 3. Finding-by-finding resolution

| # | Finding | Verdict | Correction (source) | Regression evidence | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | Host-root escalation: the privileged wrapper executes a generator from the user-writable checkout | **Confirmed** | `lab/gate2-rebuild-kickstart-iso.sh` now executes only root-owned regular files under the libexec directory; validates directory/owner/symlink/mode/arguments and scrubs the environment; `lab/gate2-install-grants.sh` installs a root-owned generator + template and no longer records or reads `/etc/hermes-gate2/repo-path` | `tests/test-hermes-manual-review.sh` §F1: a poisoned checkout generator is not executed, the root-owned one is, symlinked/writable dependencies and call-time arguments are refused | ✅ PASS |
| 2 | Empty `hooks`/`mcp_servers` mappings merge instead of replacing | **Confirmed** | `config/profile-contract.yaml` gains a reviewed `replace:` list; `config/harden-config.py` deletes each path before merging; `config/verify-contract.py` independently asserts the collections are empty on disk | `tests/test_hermes_manual_hardening.py`; red reproduced against the reviewed `harden-config.py` (populated hooks/MCP preserved) | ✅ PASS |
| 3 | Backup ignores stop failures, checks only the worker and does not enforce tar rc | **Confirmed** | `m04-backup.sh`: refuses to archive unless both services are inactive and no profile container runs; enforces creation rc **and** archive readability; enforces extraction rc; compares every required component's content **and** mode/owner/type; restores prior service state via a trap hook | `tests/test-hermes-manual-backup.sh`: happy path, credential-free path, stop-command failure, sticky-active writer, running container, creation failure, extraction failure, metadata drift | ✅ PASS |
| 4 | `mp_secure_tmpdir` loses cleanup registration through command substitution; traps do not restore service state and suppress failures | **Confirmed** | `mp_secure_tmpdir` registers in the calling shell; new `mp_secure_tmpdir_var`; new `mp_on_cleanup` hook registry run on EXIT/INT/TERM with a once-only guard; restoration hooks return non-zero and are reported while the primary status is preserved; SIGKILL limitation documented | `tests/test-hermes-manual-review.sh` §F4: registration, INT/TERM hook + directory removal, cleanup-failure reporting, primary status preservation; `m04-backup` hook wiring and restore-on-failure | ✅ PASS |
| 5 | Phase-specific locks do not serialize the same profile | **Confirmed** | One `MP_PROFILE_LOCK_PATH` with `mp_lock_profile`, used by every mutating helper including `provision-openai-key.sh` and `provision-telegram.sh`; no phase lock path remains | `tests/test-hermes-manual-review.sh` §F5: eight different real helpers are each refused while another holds the profile lock | ✅ PASS |
| 6 | Missing probe tool / execution error read as denied egress (false isolation PASS) | **Confirmed** | `mp_classify_egress` distinguishes success, denial, DNS failure, timeout, missing tool and probe error; `m02` proves `curl`+`timeout` exist first, probes literal IPv4 **and** IPv6 addresses with bounds, and reports DNS separately; a missing tool is UNVERIFIED | `tests/test-hermes-manual-review.sh` §F6 (classification matrix + source assertions) | ✅ PASS |
| 7 | ausearch's non-zero "no matches" outcome read as UNVERIFIED | **Confirmed** (m01 already fixed) | New `mp_audit_avc_check` centralizes clean log / actual denials / absent tool / read error; 11 helpers converted; no ad-hoc `mp_check avc_denials` remains | `tests/test-hermes-manual-review.sh` §F7: stubbed clean log, denials, read error, absent tool; plus an enumeration guard. Live red was observed before conversion (7 helpers failed) | ✅ PASS |
| 8 | Gate 2 omits contract application (`m04-posture` only installs it) | **Confirmed** | New credential-free `m03-contract.sh` applies and verifies the contract; new `config/verify-contract.py`; Gate 2 plan Phase 6, the deployment guide, the manual README and the contributor guide sequence it | `tests/test-hermes-manual-review.sh` §F8; `tests/test_hermes_manual_hardening.py` verifier tests | ✅ PASS |
| 9 | Credential-free acceptance impossible: `doctor=UNVERIFIED`, gateway stability required | **Confirmed** | `mp_info` for informational diagnostics and `mp_defer` for later-gate checks; `m03-activate` doctor → informational; `m03-configure` absent schema → informational, gateway stability → deferred; `m03-accept` credentials/inference/tool round-trip → deferred; `mp_finalize` reports `RESULT=PASS (PARTIAL: n deferred)` and still blocks on required UNVERIFIED/FAIL | `tests/test-hermes-manual-review.sh` §F9 (partial result; UNVERIFIED still blocks; info not counted) | ✅ PASS |
| 10 | Non-idempotent convergence (rewrites, backups and rebuilds on every run) | **Confirmed** | `harden-config.py` is convergent (no write, no backup, stable hash/mode/owner; `--check`; `--upgrade`; collision-safe backups); `m02` skips the rebuild on unchanged inputs and skips the restart when nothing changed; `m03-activate` skips the Quadlet install, `daemon-reload` and start when unchanged; `m04-posture` rewrites the drop-in and reloads only on change; `m03-configure` skips a `config set` that would be a no-op | `tests/test_hermes_manual_hardening.py` (second/third application: hash, mtime, mode, owner, backup count); `tests/test-hermes-manual-review.sh` §F10 (`mp_content_differs`, stamps, `mp_should_rebuild`, `mp_install_if_changed`) | ✅ PASS |
| 11 | Contradictory plans and evidence | **Confirmed** | Gate 2 plan gains a §0 authoritative status; obsolete interactive/encrypted/awaiting-Phase-3 statements are labelled superseded; the parent plan's ACTIVE-vs-COMPLETED and "awaiting approval" contradictions are reconciled; the contract doc and manual README record the deployed `mp_defer`/lock semantics; the TOFU host-key verification stays explicitly outstanding | `docs` changes validated by `tests/test-hermes-guide.sh` (217 checks) and the clean-install rehearsal (`REHEARSAL=PASS`) | ✅ PASS |

No finding was "already fixed" except the audit handling in `m01-host-prepare.sh`, which was correct
and is now the shared implementation. No finding was "not reproduced".

## 4. Evidence history

### R00 — inventory and reproduction

- HEAD `2340887183f75f30215088f37b39bf63a0a453c0`, clean tree. Each finding re-read against this source.
- F2 red reproduced: extracted `git show HEAD:scripts/hermes/manual/config/harden-config.py`, ran it on a
  profile with populated `hooks`/`mcp_servers`; both were preserved while the run printed
  `PROFILE_CONTRACT_APPLIED` — the reported defect.
- F7 red observed live: the new §F7 enumeration failed for seven helpers (`m01-baseline` excluded as a
  tool-list check; the diagnostic-only `m05-gateway-diag*` scripts graded nothing) before conversion.
- F1/F3/F4/F5/F6/F9/F10 defects were confirmed by reading the reviewed source at the paths above; the
  new tests are written against the corrected behavior and the reviewed code cannot satisfy them
  (the shared functions and checks did not exist).

### R01–R11 — implementation and green gates

Final gate run (repository root):

| Command | Result |
| --- | --- |
| `./tests/test-hermes-manual-profile.sh` | 358 passed, 0 failed, 0 skipped |
| `./tests/test-hermes-manual-review.sh` | 64 passed, 0 failed, 0 skipped |
| `./tests/test-hermes-manual-backup.sh` | 23 passed, 0 failed, 0 skipped |
| `python3 -m unittest discover -s tests -p test_hermes_manual_hardening.py` | 12 tests OK (run repeatedly after a backup-collision fix; stable) |
| `./tests/test-hermes-guide.sh` | 217 passed, 0 failed, 0 skipped |
| `bash scripts/hermes/manual/boot/rehearse-clean-install.sh` | `REHEARSAL=PASS failures=0 advisories=0` |
| `bash -n` over every touched shell file; `python3 -m py_compile`; `git diff --check` | clean |

A defect found by the new tests and fixed during implementation: `harden-config.py` named backups with
second resolution, so an apply followed within the same second by `--upgrade` overwrote the first
backup. Backup names are now made unique; the test was failing 3/3 before the fix and passes 5/5 after.

## 5. Status matrix

| Finding | Repository fix | Offline behavioral evidence | Runtime acceptance |
| --- | --- | --- | --- |
| 1 privileged wrapper | ✅ PASS | ✅ PASS | ⬜ NOT RUN (needs host grant reinstall/removal) |
| 2 replacement semantics | ✅ PASS | ✅ PASS | ⬜ NOT RUN |
| 3 backup correctness | ✅ PASS | ✅ PASS | ⬜ NOT RUN (needs the guest) |
| 4 interruption cleanup | ✅ PASS | ✅ PASS (lib + wiring) | ⬜ NOT RUN |
| 5 profile lock | ✅ PASS | ✅ PASS | ⬜ NOT RUN |
| 6 egress isolation | ✅ PASS | ✅ PASS (classifier) | ⬜ NOT RUN (needs a present probe in the guest) |
| 7 audit interpretation | ✅ PASS | ✅ PASS (stubbed ausearch) | ⬜ NOT RUN |
| 8 contract application | ✅ PASS | ✅ PASS | ⬜ NOT RUN |
| 9 credential-free acceptance | ✅ PASS | ✅ PASS | ⬜ NOT RUN |
| 10 convergence | ✅ PASS | ✅ PASS | ⬜ NOT RUN (needs the guest) |
| 11 documentation | ✅ PASS | ✅ PASS (guide + rehearsal) | ➖ N/A |

Overall conclusion: **repository fixes validated offline; runtime acceptance pending.**

## 6. Runtime validation proposal (authorization required)

**Identity binding — by fixture, not by a historical address.** Target the domain
`lab-hermes-manual-r1` by its live `virsh domuuid` and the MAC recorded in Phase 2
(`52:54:00:94:58:36`), resolving the address from a fresh `virsh net-dhcp-leases fvh-nat` at run time.
Do **not** use or pin `172.16.99.12` or any stored address.

**Preconditions:** the retained fixture is running; `sudo-1(true)` availability and the host grant
state are confirmed first. If the pre-fix host grant is still installed, the operator removes it with
`gate2-install-grants.sh --remove` and reinstalls the corrected grant before any privileged step.

**Mutations (all on the one retained guest, none destructive):**

1. Re-profile the guest key-only path and confirm the new locks: run `m03-contract.sh --apply`, then
   `m03-configure-and-probe.sh --apply`, `m04-posture.sh --apply`, `m04-backup.sh --apply`.
2. Convergence: run the same helpers a second and third time; require unchanged config/`.env` hashes,
   unchanged Quadlet hashes, no new backup files, no additional worker-image rebuild and no restart
   churn (compare `podman image inspect` IDs and recorded restart counters).
3. Worker isolation: an IPv4 and IPv6 probe with `curl`/`timeout` present (a missing tool must report
   UNVERIFIED), plus DNS, missing/changed worker host key, stopped worker and wrong `worker.sock` mode.
4. Backup/restore: a stopped-state backup with an isolated restore, then a deliberate
   `tar`-failure injection is **not** run on the guest; the offline fault injection remains the evidence
   for failure paths.
5. Reboot persistence: one clean reboot, then re-verify worker autostart, transport probe, mounts,
   labels and no new AVC denials. Record the boot ID.
6. Failure recovery: interrupt a helper with TERM and confirm the private directory is removed and the
   prior service state is restored.

**Resource limits:** the fixture stays at 2 vCPU / 8 GiB / 80 GiB sparse qcow2 on `fvh-nat`; abort if
`/var/lib/libvirt/images` falls below 60 GiB free. No host configuration change.

**Rollback and retained assets:** every helper keeps its pre-change backup
(`config.yaml.pre-contract-*`) and the previous Quadlet files; rollback is reinstalling the previous
files and restarting the units. Retain the guest, its disk, `virsh dumpxml`, sanitized journals and the
mode-0600 helper logs and JSON evidence. No destruction without explicit approval.

**Cleanup:** remove the temporary host grant with `gate2-install-grants.sh --remove` when the run ends;
leave the fixture running and retained for Gate 3. Provider/messaging acceptance and the optional
encrypted-storage/TPM profiles stay **NOT RUN** unless separately authorized.

## 7. Remaining risks, permissions and next steps

- **Lint/format/hooks NOT RUN** (tooling absent). Substitute checks are weaker; run `shellcheck`, `shfmt`
  and `markdownlint-cli2` in a Devbox shell before committing.
- **Host grant containment is operator-side.** The repository cannot verify or change the installed
  grant; the corrected installer must be run, or the grant removed, before further privileged use.
- **Runtime behavior is unproven.** SELinux/Podman/systemd/Fedora semantics, real service-state
  restoration under a real INT/TERM, real backup/restore and real reboot persistence need the guest.
- **TOFU guest host key remains unverified at the console (D-04).** It must stay outstanding.
- **Required permissions for the next step:** authorization to resume Gate 2 Phase 6 on
  `lab-hermes-manual-r1` (guest access, one reboot, no credential provisioning), and — separately —
  authorization for any provider/messaging or encrypted/TPM work.
- **Exact next step:** present §6 and request the Phase 6 resumption authorization. Do not commit,
  push or deploy without a separate instruction.

## 8. Handoff / closure

- Outcome: all eleven findings corrected in the working tree with focused behavioral regression tests;
  all affected offline gates pass; documentation reconciled with one authoritative status.
- Not done: commits, runtime validation, provider/messaging acceptance, encrypted/TPM profiles.
- Final verdict: **repository fixes validated offline; runtime acceptance pending.**

## 9. Second iteration — repository-only correction plan (R1–R10)

The independent review re-expressed the work as ten findings (R1–R10) with additional specificity. This
section records that pass; it does not replace §3, and together they are the current state.

| R | Requirement | Verdict | Correction | Regression evidence |
| --- | --- | --- | --- | --- |
| R1 | Enforce exact values for security-controlled replacement paths; preserve valid mapped ownership; initialize fresh state for the container UID | Confirmed | `replace:` now covers `approvals` and `security` (whole-subtree replacement via `drop_path`); `verify-contract.py` exact-compares every replaced subtree; `atomic_write` preserves an existing owner where permitted and creates fresh state at 0600 owned by the applying (container UID 10000) process | `test_hermes_manual_hardening.py`: extra `security` key fails verification and is removed by apply; fresh state uid/gid/mode |
| R2 | Require conclusive stopped-writer evidence before archiving; reject failed queries and transitional states | Confirmed | `m04-backup.sh` accepts only `inactive`/`dead`; empty output (failed query), `deactivating`/`activating` and any other state are not proof; a failed `podman ps` query is also not proof | `test-hermes-manual-backup.sh`: `is-active` rc failure, `deactivating`, `podman ps` failure scenarios |
| R3 | Restoration failure invalidates success while preserving a primary failure; nonzero INT/TERM statuses | Confirmed | m02/m03-configure/m04-backup append a required `CHECK restore_*_state=PASS\|FAIL`, so a failed restore fails an otherwise-successful run; `mp_finalize` reports the primary pipeline rc first; `mp_install_trap` exits 130/143 | backup restore-failure and both-fail scenarios; review test `trap-child` asserts 130/143 |
| R4 | Propagate installation failures and reconcile required ownership/modes | Confirmed | `mp_install_if_changed` now returns non-zero on failure and reconciles mode/owner on the unchanged path; `mp_install_reconcile` adds a CHECK; m02 (dirs, shims, Quadlets), m03-activate, m03-contract and m04-posture all propagate | review test §R4 (mode reconcile, `CHANGED`/`UNCHANGED`, failure rc, CHECK PASS/FAIL) |
| R5 | Include worker-key provisioning in the shared profile lock | Confirmed | `main()` in `provision-worker-client-key.sh` takes `mp_lock_profile`; the sourceable function stays lock-free for the rehearsal | review test §F5 now lists `provision-worker-client-key.sh` among the contending helpers |
| R6 | Register temporary-state cleanup in the process that owns the exit trap | Confirmed | `mp_secure_tmpdir_var` is used by m01 and m04-backup (the real helper path is exercised); the library INT/TERM tests prove removal | review test §F4; `test-hermes-manual-backup.sh` wiring |
| R7 | Distinguish missing tools, execution failures, timeouts and unresolved names | Confirmed | new `mp_classify_dns`; m02 proves `getent`+`timeout` exist, then classifies `DNS_RESOLVED`/`DNS_UNRESOLVED`/`DNS_TIMEOUT`/`PROBE_UNAVAILABLE`/`PROBE_ERROR`; only definitive not-found passes | review test §F6 DNS matrix + m02 source assertions |
| R8 | Credential-free contract verification | Confirmed | `verify-contract.py` remains the credential-free path and now exact-checks replaced subtrees; `m03-contract.sh` uses it | `test_hermes_manual_hardening.py` verifier tests |
| R9 | `--check` verifies environment policy without writing | Confirmed | `harden-config.py` renders the `.env` allowlist without writing and fails `--check` when either config or environment drifts | `test_hermes_manual_hardening.py::test_check_mode_verifies_environment_policy_without_writing` |
| R10 | DNS grading and convergence: detect drift before stopping services; avoid relabeling live private mounts; skip writes/lifecycle changes when converged | Confirmed | `m03-configure-and-probe.sh` reads current values first, stops and relabels only when drift or a changed probe requires it, skips the start when already active, and leaves the live mount untouched when converged; paths are `HERMES_RUNTIME_HOME`-overridable so the real call path is testable | new `tests/test-hermes-manual-configure.sh`: converged (no stop/start/relabel), drift (stop, no relabel), changed probe (stop before relabel), inspect (no calls) |

Additional test hygiene from the plan: the existing inspect check in
`tests/test-hermes-manual-profile.sh` no longer writes into a real administrator home; it resolves a
synthetic account to a temporary home through a `getent` stub.

Second-iteration gate run (repository root, dirty tree on top of §2):

| Command | Result |
| --- | --- |
| `./tests/test-hermes-manual-profile.sh` | 358 passed, 0 failed |
| `./tests/test-hermes-manual-review.sh` | 81 passed, 0 failed |
| `./tests/test-hermes-manual-backup.sh` | 32 passed, 0 failed |
| `./tests/test-hermes-manual-configure.sh` | 17 passed, 0 failed |
| `python3 -m unittest discover -s tests -p test_hermes_manual_hardening.py` | 16 tests OK |
| `./tests/test-hermes-guide.sh` | 217 passed, 0 failed |
| `bash scripts/hermes/manual/boot/rehearse-clean-install.sh` | `REHEARSAL=PASS failures=0 advisories=0` |
| `bash -n` over touched shell, `py_compile`, `git diff --check` | clean |

The rehearsal initially failed (5 assertions) because the newly locked key helper ran without a
writable lock path; the fixture now supplies `MP_PROFILE_LOCK_PATH` in its temp directory. That is
recorded rather than hidden: the lock is exercised by the rehearsal, not bypassed.

Still **NOT RUN**: runtime/lab acceptance, provider/messaging acceptance, encrypted/TPM profiles, and
lint/format/hooks (tooling absent). Final verdict unchanged:
**repository fixes validated offline; runtime acceptance pending.**

## 10. Third iteration — authoritative R1–R10 reconciliation (baseline saved before edits)

§9 is retained as a historical claim set. Its R-number mapping does **not** consistently match the
independent review ([HERMES_MANUAL_OFFLINE_REVIEW.md](/var/home/aicloudopspecial/code/repos/fedora-virtualization-host/docs/HERMES_MANUAL_OFFLINE_REVIEW.md)),
so this section is keyed to the authoritative R1–R10 mapping supplied with the correction
authorization (R1 contract-helper ownership, R2 stopped-writer evidence, R3 failure propagation,
R4 install convergence, R5 provisioning lock, R6 M01 temporary state, R7 DNS false PASS,
R8 verifier replacement semantics, R9 non-writing environment check, R10 no-op lifecycle convergence).

### 10.1 Baseline at plan time (verified, not copied)

| Item | Value |
| --- | --- |
| Branch / HEAD | `codex/hermes-fedora44-manual-review` / `2340887183f75f30215088f37b39bf63a0a453c0` |
| Changed tracked / untracked | 31 / 7 |
| Tracked diffstat | `1360 insertions(+), 482 deletions(-)` |
| Dirty-input fingerprint | `0e751e9bf0b64b831a964750c1819c254a88e5fc11a36c88a71efc278ab02794` |
| Environment | 2026-09-20, America/Bogota; Bash 5.3.9, Python 3.14.7, PyYAML 6.0.3 |
| Tooling | `devbox`, `shellcheck`, `shfmt`, `markdownlint-cli2`, `shellspec` ABSENT (not installed) |

The fingerprint was recomputed from the working tree with the authorized algorithm (sorted unique
changed/untracked paths; `path + NUL + sha256(bytes)` aggregated into one SHA-256).

### 10.2 Approved scope

Repository-only: edit this repository on this branch; add behavioral regressions; run offline tests,
`bash -n`, Python syntax validation, `git diff --check`; update the canonical record and affected docs.
Not authorized and not performed: deployment, lab/production contact, host configuration or installed
grants, real credentials, provider calls, package installation, commits, pushes, delegation. Gate 2
stays paused after Phase 5.

### 10.3 Task dependencies and gates

| Task | Depends on | Repository fix gate | Behavioral gate |
| --- | --- | --- | --- |
| T1 R1 ownership | baseline | m03-contract.sh owns state via namespace UID 10000 | real-helper ownership path: fresh / valid-mapped / legacy |
| T2 R2 writer evidence | baseline | rc **and** state validated | failed query, transitional, podman-query failure, normal inactive rc=3 |
| T3 R3 propagation | T2 | restore CHECK precedes finalize in m02/m03/m04 | success+cleanup-failure, primary failure, INT/TERM |
| T4 R4 install | baseline | failure propagated; metadata reconciled, no needless write | changed/unchanged mode+owner; converged no ctime churn |
| T5 R5 lock | baseline | worker/openai/telegram entrypoints take the shared lock | contention fixture includes all three |
| T6 R6 M01 tmpdir | baseline | temp state registered in the trap-owning shell | real M01 normal/failure/interruption leaves no temp state |
| T7 R7 DNS | baseline | actual resolver status captured | executed m02 DNS block: resolved/unresolved/timeout/missing |
| T8 R8 verifier | baseline | exact compare for every `replace:` path | extra `platform_toolsets`/`security` key fails; unmanaged key passes |
| T9 R9 env check | baseline | `--check` reads env allowlist without writing | drifted/missing `.env` fails; no write, no backup |
| T10 R10 convergence | T3 | drift read without live-mount relabel; no-op when converged | active and inactive converged: no stop, no live-mount relabel |

RED-to-GREEN discipline: for each remaining defect the regression is written first and the intended
failure observed where the defect exists; pre-existing correct fixes are validated, not re-broken.
Runtime DAC/SELinux/systemd semantics stay unproven offline.

### 10.4 Retained pre-existing work vs this pass

**Retained unchanged (pre-existing §9 work, revalidated):** `scripts/hermes/manual/config/verify-contract.py`
(R8 exact replacement), `scripts/hermes/manual/config/harden-config.py` and `profile-contract.yaml`
(R9 non-writing env check, R8 replacement list), `provision-worker-client-key.sh` /
`provision-openai-key.sh` / `provision-telegram.sh` (R5 shared lock), the m04/m02/m03-configure
restoration CHECK wiring (R3), the R2 writer checks, the R4 install propagation, plus all other §9
files not listed below.

**Changed in this pass (13 existing files + 2 new test suites):**

| File | Finding |
| --- | --- |
| `scripts/hermes/manual/m03-contract.sh` | R1: namespace UID/GID ownership of the state directory |
| `scripts/hermes/manual/m04-backup.sh` | R2: validate the query **status**, not only the state text |
| `scripts/hermes/manual/lib-manual-common.sh` | R4 no-op metadata writes; R3 `mp_run_cleanup` return status |
| `scripts/hermes/manual/m01-host-prepare.sh` | R6: allocate/register in the trap-owning shell |
| `scripts/hermes/manual/m02-deploy-and-validate.sh` | R7: extractable markers around the real DNS grading wiring |
| `scripts/hermes/manual/m03-configure-and-probe.sh` | R10: `gcur` (exec when live), drift-first, no lifecycle change when converged; R3 failed-stop check |
| `tests/test-hermes-manual-review.sh` | R4/R5/R7/R3 regressions |
| `tests/test-hermes-manual-backup.sh` | R2 regressions (real systemctl status 3; unexpected status) |
| `tests/test-hermes-manual-configure.sh` | R10/R3 regressions (mount behaviour, inactive converged, failed stop/apply/restore) |
| `tests/test_hermes_manual_hardening.py` | R8/R9 regressions (extra `platform_toolsets`, unmanaged keys, missing `.env`) |
| `docs/CONTRIBUTING.md`, `docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md`, `scripts/hermes/manual/README.md` | documentation of the changed behaviour and the new suites |
| `tests/test-hermes-manual-contract.sh` (new) | R1 focused suite |
| `tests/test-hermes-manual-m01-tempdir.sh` (new) | R6 focused suite |

### 10.5 Authoritative R1–R10 disposition

| R | Fix in this tree | Behavioral regression | Actual outcome | Remaining limitation |
| --- | --- | --- | --- | --- |
| R1 | ✅ state dir handed to namespace UID/GID 10000; existing mapping preserved; mode only narrowed | `tests/test-hermes-manual-contract.sh` (15 checks): fresh mapping, preserved mapping, legacy repair, mode narrowing, chown-failure propagation | ✅ GREEN; red 5 failed with the old `install -d -o hermes` path | real DAC/SELinux access by the guest container **NOT RUN** |
| R2 | ✅ query status must be 0 or 3 **and** state must be `inactive`/`dead`; failed `podman ps` blocks | backup suite: rc 3 accepted, bare failure rejected, forced status rejected, transitional, podman failure | ✅ GREEN; red 1 failed without the status check | real systemd/journal state **NOT RUN** |
| R3 | ✅ m02/m03-configure/m04-backup append a required restoration CHECK before finalize; `mp_run_cleanup` now returns non-zero on failure; INT/TERM return 130/143 | m04 restore-failure + both-fail; m03-configure failed-stop/apply/restore; review `trap-child` 130/143; `mp_run_cleanup` return | ✅ ~~GREEN~~ **SUPERSEDED — see §11/§12**: the review reproduced C1 (the EXIT trap still published PASS after a cleanup failure) and C2 (an unknown prior state stranded services). Both are corrected in §12; red 3 failed without the m03-configure stop guard | real INT/TERM service recovery **NOT RUN** |
| R4 | ✅ `mp_install_if_changed` propagates failure and reconciles mode/owner only when they differ | review suite: changed/unchanged mode, install rc, CHECK PASS/FAIL, converged ctime stable, all callers propagate | ✅ GREEN; red 1 failed with unconditional chmod | real filesystem/SELinux metadata **NOT RUN** |
| R5 | ✅ (pre-existing) worker/openai/telegram entrypoints take `mp_lock_profile` | F5 contention now covers all three; refused worker-key run reaches no mutation | ✅ GREEN | real concurrent operator sessions **NOT RUN** |
| R6 | ✅ allocation/registration moved into the trap-owning parent shell | new M01 suite: structural ordering, non-signal parent completion, TERM process-group interruption, no host write | ✅ GREEN; red 2 failed with the allocation inside the pipeline | SIGKILL leak remains documented; full exit-0 M01 run **NOT RUN** offline |
| R7 | ✅ (pre-existing) resolver tool gate + `mp_classify_dns` | executed the **real** m02 DNS block (markers) with a mocked `h`: resolved/unresolved/timeout/missing/absent | ✅ GREEN (validation of a pre-existing fix; no red manufactured) | a real guest probe **NOT RUN** |
| R8 | ✅ (pre-existing) every `replace:` path exact-compared | hardening suite: extra `platform_toolsets` fails, apply removes it, unmanaged keys pass | ✅ GREEN (validation) | live applier on a real profile **NOT RUN** |
| R9 | ✅ (pre-existing) `--check` reads the `.env` allowlist without writing | hardening suite: drifted env fails, missing env fails, no write, no backup, converged env untouched | ✅ GREEN (validation) | real profile `.env` **NOT RUN** |
| R10 | ✅ `gcur` reads via `podman exec` against a live gateway; drift determined before any stop; converged run makes no lifecycle change; failed stop blocks mutation | configure suite: active and inactive converged (no stop/start, no live state mount), config/probe drift, failed stop/apply/restore | ✅ ~~GREEN~~ **SUPERSEDED — see §11/§12**: the review reproduced C3 (the live exec lost the runtime UID) and C4 (a failed unit query selected the one-shot relabel path), and found C5 in the contract helper. All are corrected in §12; red 3 (relabel), 2 (inactive churn), 3 (failed stop) | real Podman/SELinux relabel behaviour **NOT RUN** |

### 10.6 Third-iteration gate run (2026-09-20, America/Bogota; dirty tree at fingerprint §10.7)

| Command | Actual result |
| --- | --- |
| `bash tests/test-hermes-manual-profile.sh` | 358 passed, 0 failed |
| `bash tests/test-hermes-manual-review.sh` | 111 passed, 0 failed |
| `bash tests/test-hermes-manual-backup.sh` | 34 passed, 0 failed |
| `bash tests/test-hermes-manual-configure.sh` | 33 passed, 0 failed |
| `bash tests/test-hermes-manual-contract.sh` (new) | 15 passed, 0 failed |
| `bash tests/test-hermes-manual-m01-tempdir.sh` (new) | 9 passed, 0 failed |
| `python3 -B -m unittest discover -s tests -p test_hermes_manual_hardening.py` | 21 tests OK |
| `bash tests/test-hermes-guide.sh` | 217 passed, 0 failed |
| `bash scripts/hermes/manual/boot/rehearse-clean-install.sh` | `REHEARSAL=PASS failures=0 advisories=0` |
| `bash -n` over every touched shell file | PASS |
| Python AST parse of the touched/new Python files (`-B`, no bytecode) | PASS |
| `git diff --check` | clean |
| `__pycache__` created under the checkout | none |

Red-to-green evidence (defect temporarily reintroduced in the working tree, suite observed failing,
file restored to the fixed version, suite re-run green): R1 5→0 failures; R2 1→0; R3 m03-configure
3→0; R4 1→0; R6 2→0; R10 3→0 (mount relabel) and 2→0 (inactive lifecycle churn). R5/R7/R8/R9 were
pre-existing fixes and were validated without manufacturing a red result.

### 10.7 Final inventory and limitations

| Item | Value |
| --- | --- |
| Branch / HEAD | `codex/hermes-fedora44-manual-review` / `2340887183f75f30215088f37b39bf63a0a453c0` |
| Changed tracked / untracked | 31 / 9 (40 total) |
| Tracked diffstat | `1461 insertions(+), 497 deletions(-)` |
| Final dirty-input fingerprint | `190909746d4edba34415cd00926426e851774ed64393ff798a583a18809b4859` (measured immediately before this line; because this record is itself a changed file, re-reading it after the edit yields a new digest — recompute with the §10.1 algorithm) |
| Tooling | `devbox`, `shellcheck`, `shfmt`, `markdownlint-cli2`, `shellspec` ABSENT; direct offline runs are **fallback evidence**, lint/format/hooks remain **NOT RUN** |

Remaining mandatory checks: run `shellcheck`, `shfmt -d -l -i 2 -ci -bn` and `markdownlint-cli2`
through `devbox run --` before any commit; run the runtime acceptance in §6 on the separately
authorized fixture (real DAC/SELinux access to `gateway-state`, Podman `:z` relabel behaviour, real
INT/TERM recovery, reboot persistence, provider/messaging).

## 11. Independent review status — 2026-09-20

The follow-up independent review matched the final dirty-input fingerprint and reran every reported
offline gate successfully. It then reproduced five remaining issues (C1–C5): cleanup failure can
still publish PASS; unknown prior service state can strand backup services; live `podman exec` omits
explicit UID/GID 10000; failed service-state queries can select relabeling one-shot mounts; and the
contract helper mounts shared gateway SSH material with `:Z` without quiescing the active gateway.
See the independent [correction review](https://github.com/securexai/fedora-virtualization-host/blob/main/docs/HERMES_MANUAL_CORRECTION_REVIEW.md)
and its fingerprint-bound replay. R3 and R10 therefore remain **CHANGES REQUESTED**; runtime
DAC/SELinux/systemd behavior remains unverified.

**Current review status:** repository state is preserved and may be committed for history, but it is
**not deployment-ready**. Gate 2 remains paused after Phase 5. The five C1–C5 corrections and fresh
independent offline review must precede any lab authorization request.

**Exact next action:** correct C1–C5, add the missing regressions, rerun all offline gates, and obtain
another independent review. Do not resume Gate 2 or deploy; runtime acceptance still requires separate
authorization.

**Boundary confirmation:** this pass made no lab or production contact, deployment, host or installed
grant change, real credential provision, provider call, or package installation. The explicit commit/push
request is the first repository publication; no runtime mutation is implied. Tests used synthetic state,
temporary fixtures and mocked privileged commands only.

## 12. Fourth iteration — C1–C5 correction pass (baseline saved before edits)

§11 records the independent review's five remaining issues and its exact next action. This section is the
execution record for correcting them. It does not rewrite §10 or §11: the unqualified R3/R10 GREEN
dispositions in §10.5 are superseded by §11's **CHANGES REQUESTED** and by the outcomes recorded below.

### 12.1 Baseline at plan time (verified, not copied)

| Item | Value |
| --- | --- |
| Branch / HEAD | `codex/hermes-fedora44-manual-review` / `130bf8f2dbdc95e0db25407d5b3b155b627d1473` (`130bf8f`, the commit that published the third iteration) |
| Working tree | clean: 0 changed tracked, 0 untracked |
| Dirty-input fingerprint | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` — the §10.1 aggregate over a zero-path input (sha256 of the empty string) |
| Environment | 2026-09-20T19:56:44-05:00, America/Bogota; Bash 5.3.9, Python 3.14.7, PyYAML 6.0.3 |
| Tooling | `devbox`, `shellcheck`, `shfmt`, `markdownlint-cli2`, `shellspec` ABSENT (not installed) |

The reviewer's replay tool `docs/HERMES_MANUAL_CORRECTION_REPRO.py` (review checkout) pins the pre-commit
dirty fingerprint `6219b737…` and refuses any other input, so it cannot be replayed against this committed
baseline. Its five counterexamples are instead ported into permanent repository regressions, which is what
§11's next action requires ("add the missing failure/identity/sequence regressions").

### 12.2 Approved scope

Unchanged from §10.2: repository-only edits on this branch, focused behavioral regressions, offline suites,
`bash -n`, Python syntax validation, `git diff --check`, documentation and this record. Not authorized and
not performed: deployment, lab/production contact, host configuration or installed grants, real
credentials, provider calls, package installation, or publication beyond this repository. Gate 2 stays
paused after Phase 5.

### 12.3 Tasks and gates (C1–C5)

| Task | Finding | Repository fix gate | Behavioral gate |
| --- | --- | --- | --- |
| V1 | C1 finalizer/EXIT cleanup | required cleanup runs before the result is published; cleanup failure with no primary failure becomes the failure; existing nonzero and 128+signal statuses preserved | real library + finalizer: failing hook, failing tempdir removal, primary-failure control, INT/TERM unchanged |
| V2 | C2 prior service state | prior state captured conclusively before any stop; an undeterminable obligation refuses mutation; m04-backup, m02 and m03-configure share the capture | real backup helper with transient pre-stop query failure: no archive, no stranded service, no false restoration PASS |
| V3 | C3 live exec identity | live `podman exec` keeps `--user 10000:10000 --workdir /opt/hermes` in m03-configure and m03-contract | fixture asserts the exact executed arguments of the live read |
| V4 | C4 relabel safety | container state (not the unit text) is the authority: active/stopped/unknown; unknown refuses; a one-shot `:z`/`:Z` mount only after the inventory proves the container is not running | converged active/inactive, failed queries with a live container, transitional queries, running container behind a non-active unit |
| V5 | C5 contract live private mount | the contract helper uses the live container (exec) when it is running and never mounts/relabels the live private SSH tree; unknown refuses; quiesce only when genuinely needed | contract-after-active-configure and second/third runs: no private `:Z` mount, no stop, convergence holds |

RED-to-GREEN discipline is unchanged: each remaining defect gets a regression observed failing against the
current source before the fix, and the fix is re-verified. R1–R9 items the review accepted as corrected
offline are not re-broken. Runtime DAC/SELinux/systemd semantics stay unproven.

### 12.4 Evidence history — RED → GREEN

Every regression was written first and observed failing against the reviewed source, then the fix was
applied and the suite re-run. No red was manufactured and no historical green was relabelled.

| Task | Red observed (against the reviewed source) | Fix | Green |
| --- | --- | --- | --- |
| V1/C1 | 6 new assertions failed: `mp_finalize` published `RESULT=PASS` and exit 0 after a failing hook, and after an unremovable registered private directory. The existing primary-failure control (exit 7) and clean-cleanup control already passed and still do | `mp_finalize` runs required cleanup **before** the tally, appends `CHECK cleanup_required=FAIL`, and the tally turns it into a non-zero exit; an existing non-zero primary status is still reported first; INT/TERM still return 130/143 | review suite 138/0 |
| V2/C2 | 8 new assertions failed: with only the pre-stop queries failing transiently, both active services were stopped, the archive was created, `RESULT=PASS` was printed, and `CHECK restore_service_state=PASS` was recorded while both services stayed inactive | new `mp_capture_service_state`; m04-backup captures conclusively before any stop, refuses mutation on an undeterminable state, records `writers_stopped=FAIL`/`backup_archive=FAIL`, and records `restore_service_state=NOT_APPLICABLE` instead of a false PASS; m02 and m03-configure use the same capture | backup suite 43/0 |
| V3/C3 | the live read asserted the explicit-identity form and failed: `gcur` issued `podman exec "$GW"` with neither option | live exec keeps `--user 10000:10000 --workdir /opt/hermes` in m03-configure and m03-contract | configure 48/0, contract 30/0 |
| V4/C4 | 10 new assertions failed: a failed unit query with a live container produced 11 `podman-run-state-mount gateway_active=yes` one-shot mounts, no service was stopped, and the run passed; a running container behind a non-active unit, a transitional state and a failed inventory likewise selected or permitted the wrong path | new `mp_container_state` tri-state; the container inventory is the authority; unknown refuses; the post-stop gate requires `stop_rc=0` **and** a stopped unit **and** a proven non-running container; an undeterminable prior state refuses the stop | configure suite 48/0 |
| V5/C5 | 8 new assertions failed: the contract helper made 4 `gateway-ssh:/opt/hermes/gateway-ssh:ro,Z` one-shot mounts, issued no `systemctl stop`, and never refused an undeterminable state | `gcur` drives a live gateway with `podman exec`; a one-shot run is used only when the inventory proves the container stopped; newly written files in the live mount get their sibling label; unknown refuses before any mount | contract suite 30/0 |

A defect found while implementing the above: `m03-contract.sh` never defined the container name (`GW`),
because the reviewed code never needed one. The new state check made it necessary, and under `set -u`
the reference aborted the report block. `GW=hermes-gateway` is now defined next to `GW_UID`/`GW_GID`.
That is recorded rather than hidden: the first C5 run exposed it and the fix was re-verified.

Supporting coverage added: `mp_capture_service_state` and `mp_container_state` are exercised directly
against fake runners (active/inactive/dead/failed/deactivating/failed-query, and running/absent/stopped/
failed-inventory/failed-inspect), and the review suite asserts that m02 and m03-configure call the
capture and that m03-configure and m03-contract use the container inventory.

Final gate run (repository root, 2026-09-20/21 America/Bogota; dirty tree at §12.5):

| Command | Actual result |
| --- | --- |
| `bash tests/test-hermes-manual-profile.sh` | 358 passed, 0 failed (unchanged) |
| `bash tests/test-hermes-manual-review.sh` | 138 passed, 0 failed (was 111) |
| `bash tests/test-hermes-manual-backup.sh` | 43 passed, 0 failed (was 34) |
| `bash tests/test-hermes-manual-configure.sh` | 48 passed, 0 failed (was 33) |
| `bash tests/test-hermes-manual-contract.sh` | 30 passed, 0 failed (was 15) |
| `bash tests/test-hermes-manual-m01-tempdir.sh` | 9 passed, 0 failed (unchanged) |
| `python3 -B -m unittest discover -s tests -p test_hermes_manual_hardening.py` | 21 tests OK (unchanged) |
| `bash tests/test-hermes-guide.sh` | 217 passed, 0 failed (unchanged) |
| `bash scripts/hermes/manual/boot/rehearse-clean-install.sh` | `REHEARSAL=PASS failures=0 advisories=0` |
| `bash -n` over the 9 changed shell files | PASS |
| Python AST parse of the changed Python files (`-B`) | PASS; no bytecode written (the ignored `__pycache__` trees predate this pass) |
| `git diff --check` | clean |

### 12.5 Outcome, limitations and next action

| Item | Value |
| --- | --- |
| Branch / HEAD | `codex/hermes-fedora44-manual-review` / `130bf8f2dbdc95e0db25407d5b3b155b627d1473` (unchanged; no commit) |
| Changed tracked / untracked | 13 / 0 |
| Diffstat (before this section's final write) | `13 files changed, 800 insertions(+), 102 deletions(-)` |
| Dirty-input fingerprint (before this section's final write) | `6c7447cda1204a485872296a31e2eda2962c3e04e8f909e0a5aba9984f088f92` — recompute with the §10.1 algorithm; because this record is itself changed, re-reading it after this edit yields a new digest |

Changed files this pass: `scripts/hermes/manual/{lib-manual-common,m02-deploy-and-validate,m03-configure-and-probe,m03-contract,m04-backup}.sh`,
`tests/test-hermes-manual-{review,backup,configure,contract}.sh`,
`docs/CONTRIBUTING.md`, `docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md`,
`scripts/hermes/manual/README.md`, and this record.

Disposition: C1–C5 are corrected offline with permanent repository regressions; R3 and R10 move from the
review's **CHANGES REQUESTED** to **corrected offline, pending fresh independent review**. R1, R2 and
R4–R9 keep the review's "corrected offline" status and are untouched by this pass.

Remaining mandatory checks (NOT RUN):

- `shellcheck`, `shfmt -d -l -i 2 -ci -bn`, `markdownlint-cli2` and the Lefthook hooks: the tooling
  (`devbox`, `shellcheck`, `shfmt`, `markdownlint-cli2`, `shellspec`) is still absent, so `bash -n`,
  the Python AST parse and `git diff --check` are fallback evidence only.
- Runtime acceptance on the separately authorized fixture: real rootless Podman, SELinux (`:z`/`:Z`)
  relabel behaviour, DAC access to `gateway-state`, systemd interruption/recovery, reboot persistence,
  and a real guest probe / provider acceptance.
- The C5 live path depends on the running container's own mounts; SELinux category inheritance for the
  contract files written into a live `:Z` mount is mitigated with the same `chcon --reference` used by
  m03-configure and m04-postboot, but the real label is **not verified** offline.
- The C1 SIGKILL limitation is unchanged (documented in the library), and a full exit-0 M01 run still
  cannot be exercised offline without touching host `/etc` or `/home/hermes`.

**Exact next action:** obtain a fresh independent offline review of this repository-only pass, keyed to
the §12.5 fingerprint, before requesting any Gate 2 authorization.

**Boundary confirmation:** this pass made no lab or production contact, no deployment, no host or
installed-grant change, no real credential provision, no provider call, and no package installation.
It did not commit or push. Gate 2 remains paused after Phase 5; runtime acceptance still requires
separate authorization. Tests used synthetic state, temporary fixtures and mocked privileged commands.

## 13. Fresh independent offline review — CHANGES REQUESTED

### 13.1 Reviewed identity and scope

Reviewed HEAD `130bf8f2dbdc95e0db25407d5b3b155b627d1473`, with the 13 changed tracked files,
0 untracked files, and `886 insertions(+), 102 deletions(-)` reported in the handoff.
The pre-review dirty-input fingerprint is **`2cafc14836b8ac37c2697f53acd6ccec58917afdae82476d952703572cf1f7a7`**,
matching the handoff exactly. This uses sorted changed/untracked paths, each encoded as
`path + NUL + sha256(file bytes).digest()` (raw digest bytes, not hexadecimal text), aggregated with SHA-256.
The §12.5 embedded `6c7447cd…` is explicitly pre-final-write evidence; it is not the final review input.
This section is the only repository edit made by the review, so its addition changes the aggregate.

The independent pass inspected the corrections, test coverage and deployment instructions, with two
focused read-only reviews for configure/contract behavior and documentation. No implementation fixes
were made. Historical red-to-green claims were not re-enacted by reverting source.

### 13.2 Findings

**F1 — P2, remaining C1 failure-accounting gap: failed log append still permits PASS.**
In [lib-manual-common.sh:108–114](../../scripts/hermes/manual/lib-manual-common.sh#L108-L114),
cleanup failure becomes a failing CHECK only by appending to the log. The append status is ignored,
and the later tally does not consult `cleanup_failed`. A synthetic non-writable log containing
`CHECK work=PASS`, plus a registered hook returning 1, reproduced the append error followed by
`check_fail=0`, `RESULT=PASS`, and exit 0. A failed append from an I/O error or full filesystem can
likewise lose the required failure even though stderr says the run is not reported as a pass.
Fail directly on the in-memory cleanup failure regardless of log-write success; add a regression
combining cleanup failure with evidence-append failure. This is a remaining edge in the new C1 fix,
not a claim that its ordinary writable-log regressions fail.

Safe standalone replay from the repository root (no privileged commands):

```bash
f=$(mktemp)
printf 'CHECK work=PASS\n' >"$f"
chmod 400 "$f"
bash -c 'source scripts/hermes/manual/lib-manual-common.sh
  bad_cleanup() { return 1; }
  mp_on_cleanup bad_cleanup
  mp_finalize "$1" 0' _ "$f"
rc=$?
chmod 600 "$f"
rm -f "$f"
printf 'actual_exit=%s (expected nonzero)\n' "$rc"
```

The permission-failure replay was run as UID 1000; root bypasses this particular permission fixture.

**F2 — P1, preexisting uncovered sequence gap: failed configure activates a previously inactive gateway.**
At [m03-configure-and-probe.sh:327–332](../../scripts/hermes/manual/m03-configure-and-probe.sh#L327-L332),
`apply_ok` means the stop succeeded, not that configuration or readback succeeded. Starting with an
inactive gateway and drifted `terminal.backend=local`, then setting the existing fixture's
`STUB_CONFIG_SET_FAIL=1`, reproduced `gateway_configured=FAIL` and
`readback_terminal_backend=FAIL`, followed by `start_rc=0` and `gateway_state_at_exit=active`.
The helper exits 1 but leaves a gateway running with known-bad terminal configuration; its initially
inactive state creates no restoration obligation to undo that start. This startup block predates the
current diff. It is an additional failure/sequence gap in R3/R10, not a newly introduced regression.
Require successful configuration/readback before newly activating an inactive gateway and test the
inactive + drift + failed-apply combination, separately from restoring an initially active gateway.

The reproduction reused the setup and `run_configure` function in
[test-hermes-manual-configure.sh:24–321](../../tests/test-hermes-manual-configure.sh#L24-L321),
without running the suite's normal cases: `seed_drifted`, set the sandbox gateway unit to `inactive`,
set `STUB_CONFIG_SET_FAIL=1`, and run `run_configure --apply`. Both the focused reviewer and the
integrating reviewer reproduced the result using the real helper through the mocked harness.
The existing failed-application test checks failure reporting but not the final lifecycle state.

**F3 — P2, preexisting deployment-guide omission: clean-install commands lack the required host pin.**
The worker-key command at [deployment guide:669](../HERMES_MANUAL_DEPLOYMENT_GUIDE.md#L669) and
application sequence prefix at [deployment guide:684–700](../HERMES_MANUAL_DEPLOYMENT_GUIDE.md#L684-L700)
use plain `sudo bash`. Those helpers require `HERMES_EXPECT_MACHINE_ID_SHA256` or an installed
root-owned host pin, but the guide does not establish the persistent application pin. On a clean host
these commands refuse; a shell export is not sufficient with normal sudo environment filtering.
Supply the independently reviewed hash explicitly in each sudo command, or document the authorized
pin bootstrap. Do not weaken the identity check or derive an expected identity blindly on the target.

**F4 — P2, new documentation mismatch: prior-state refusal has a running-container exception.**
[README:59–62](../../scripts/hermes/manual/README.md#L59-L62) promises refusal on failed/transitional
prior-state queries, and [deployment guide:734–736](../HERMES_MANUAL_DEPLOYMENT_GUIDE.md#L734-L736)
similarly overstates refusal. However,
[m03-configure-and-probe.sh:87–100](../../scripts/hermes/manual/m03-configure-and-probe.sh#L87-L100)
allows stopping on drift when the container is conclusively running even if the unit query is
failed/transitional. It treats that as a restoration obligation. Document this exception accurately
or enforce the stricter advertised behavior. This finding is a docs/source contradiction, not proof
that using the running container as a restoration obligation is itself unsafe.

### 13.3 Independently rerun gates and limits

| Offline command | Actual result |
| --- | --- |
| `bash tests/test-hermes-manual-profile.sh` | 358 passed, 0 failed |
| `bash tests/test-hermes-manual-review.sh` | 138 passed, 0 failed |
| `bash tests/test-hermes-manual-backup.sh` | 43 passed, 0 failed |
| `bash tests/test-hermes-manual-configure.sh` | 48 passed, 0 failed |
| `bash tests/test-hermes-manual-contract.sh` | 30 passed, 0 failed |
| `bash tests/test-hermes-manual-m01-tempdir.sh` | 9 passed, 0 failed |
| `python3 -B -m unittest discover -s tests -p test_hermes_manual_hardening.py` | 21 tests OK |
| `bash tests/test-hermes-guide.sh` | 217 passed, 0 failed |
| `bash scripts/hermes/manual/boot/rehearse-clean-install.sh` | `REHEARSAL=PASS failures=0 advisories=0` |
| `bash -n` on the 9 changed shell files | PASS |
| `git diff --check` before review-record edit | clean |

The raw-digest fingerprint matched before these checks. All named suites passing does not invalidate
the additional counterexamples. C2's tested refusal path and C3's explicit exec identity pass offline;
the named-container routing fixes in C4/C5 also pass their current mocks. R3/R10 are not closed.

`devbox`, `shellcheck`, `shfmt`, `markdownlint-cli2`, and `lefthook` remain absent; lint/format/hooks
were NOT RUN. No Python implementation changed in the reviewed diff. Runtime acceptance remains
NOT RUN: rootless Podman, actual DAC/SELinux access and relabel behavior, systemd signal recovery,
reboot, real guest/provider/messaging probes. The SIGKILL temporary-state limitation remains.
Additional inspection-only risk: the new live contract file labeling branch runs only for changed
files and suppresses both `chcon` failures. A failed/interrupted first label operation is not repaired
on an unchanged retry. Real SELinux impact was not tested and is not claimed as reproduced here.

### 13.4 Verdict and exact next action

**CHANGES REQUESTED.** Correct F1–F4 (including the two explicitly preexisting gaps), add permanent
failure/sequence regressions for F1/F2, rerun the offline gates, and obtain a fresh fingerprint-bound
review before any Gate 2 authorization request. Keep §12's evidence as historical evidence rather
than replacing it with an unqualified green disposition. Gate 2 remains paused after Phase 5;
this review authorizes neither deployment nor runtime acceptance.

**Boundary confirmation:** no lab/production contact, deployment, host configuration or installed-grant
change, real credential access/provisioning, provider calls, package installation, commit, or push.
Only synthetic fixtures, temporary state, mocked runtime commands, repository inspection and this
review-record edit were used.

## 14. Fifth iteration — F1–F4 correction pass (baseline saved before edits)

§13 records the latest independent review's four findings (F1–F4) and the exact next action. This
section is the execution record for correcting them. §10–§13 are retained unchanged as historical
evidence; where their wording overstates the prior-state refusal (see §14.6) that is recorded here
rather than rewritten there. §13.3's live-contract labeling-retry concern is dispositioned in §14.7.

### 14.1 Baseline at plan time (verified, not copied)

| Item | Value |
| --- | --- |
| Branch | `codex/hermes-fedora44-manual-review` |
| Expected / actual HEAD | `130bf8f2dbdc95e0db25407d5b3b155b627d1473` (matches) |
| Working tree | 13 modified tracked files, 0 untracked (the reviewer's §13 edit rides on the §12 files) |
| Tracked diffstat | `13 files changed, 1006 insertions(+), 102 deletions(-)` |
| Dirty-input fingerprint immediately before this section's write | `919ff6a351f56f1241ae71b676dd4ee82c223c6d44c61d7ebac018e3bcefd926` |
| Reviewed pre-record fingerprint (§13.1) | `2cafc14836b8ac37c2697f53acd6ccec58917afdae82476d952703572cf1f7a7` (measured before the reviewer added §13; differs from the value above exactly as §13.1 predicts) |
| Environment | 2026-09-20T20:15:55-05:00 America/Bogota; Fedora Linux 44 Kinoite, Bash 5.3.9, Python 3.14.7 with PyYAML 6.0.3 |
| Tooling | `devbox`, `shellcheck`, `shfmt`, `markdownlint-cli2`, `shellspec`, `lefthook` ABSENT (not installed) |

The fingerprint uses the §10.1 algorithm: sorted unique changed/untracked paths; for each path,
`path + NUL + sha256(file bytes).digest()` using raw digest bytes; then SHA-256 of the concatenation.
It was measured **before** this section was written and was therefore changed by this record edit.

### 14.2 Approved scope

Unchanged from §10.2/§12.2: repository-only edits on this branch, focused behavioral regressions, offline
suites, `bash -n`, Python syntax validation, `git diff --check`, documentation and this record. Not
authorized and not performed: deployment, lab/production contact, host configuration or installed grants,
real credentials, provider calls, package installation, commits, pushes, or delegation. Gate 2 stays
paused after Phase 5; the fresh independent review required by §13.4 has not happened yet.

### 14.3 Tasks and gates (F1–F4)

| Task | Finding | Repository fix gate | Behavioral gate |
| --- | --- | --- | --- |
| W1 | F1 cleanup failure vs failed evidence append | the in-memory cleanup result is authoritative; a failed `CHECK cleanup_required=FAIL` append cannot yield PASS | library finalizer: failing cleanup + failing append, ordinary success, cleanup failure with a writable log, existing primary failure, INT/TERM statuses |
| W2 | F2 failed configure activates an inactive gateway | a gateway that was inactive before the run is started only when configured, readback and probe checks pass; initially-active gateways keep their restoration obligation | real helper with synthetic state: inactive + drift + failed apply leaves the unit inactive; probe failure leaves it inactive; drift success still activates; initially-active failed configure is restored |
| W3 | F3 guide lacks the host pin | the deployment guide shows the reviewed `HERMES_EXPECT_MACHINE_ID_SHA256` binding (or an authorized, non-blind pin bootstrap) for the worker-key and application commands | guide/rehearsal documentation checks |
| W4 | F4 prior-state refusal overstatement | README, deployment guide and the configure suite header distinguish unit-state from container-state uncertainty and document the running-container restoration exception | existing configure suite plus the header/document text |

RED-to-GREEN discipline is unchanged: each behavioral defect gets a regression observed failing against
the reviewed source before the fix. F1 and F2 are the behavioral reds; F3/F4 are documentation
corrections validated by the guide/rehearsal checks. No accepted fix is reverted to manufacture red.
Runtime DAC/SELinux/systemd semantics stay unproven.

### 14.4 Evidence history — RED → GREEN

| Task | Red observed against the reviewed source (before the fix) | Fix | Green |
| --- | --- | --- | --- |
| W1/F1 | `tests/test-hermes-manual-review.sh` 140 passed / **2 failed**: with a registered hook returning 1 and the `CHECK cleanup_required=FAIL` append forced to fail, the finalizer printed `RESULT=PASS` and exited 0 (`rc=0`). The fixture is UID-independent (a shadowed `printf` for that one line), so it does not silently pass when run as root | `mp_finalize` keeps `cleanup_failed` in memory, guards the best-effort append, and fails on the in-memory result after the primary-status check | review suite **142/0** |
| W2/F2 | `tests/test-hermes-manual-configure.sh` 56 passed / **4 failed**: an initially inactive gateway with drifted `terminal.backend` and a failed `config set` was started and left `active`; a failed backend probe also started it | the start block now requires `config_ok && readback_ok && probe_ok` in addition to the successful stop; `restore_gateway_state` still restores an initially active gateway independently | configure suite **64/0** (48 baseline + 16 new assertions) |
| W3/F3 | documentation gap: the worker-key command and the 6.3 sequence were `sudo bash …` with no host binding, which refuses on a clean host because `sudo` drops an exported variable | 6.2 binds the worker-key command explicitly, documents the authorized non-blind `m00-pin-host-identity.sh` pin, and 6.3 gives the exact prefix | guide passes `tests/test-hermes-guide.sh` (217/0) and the new rehearsal checks (below) |
| W4/F4 | docs/source contradiction, no behavioral red (the behavior is intentional): the README/guide said a failed or transitional prior-state query refuses the stop, but `m03-configure` refuses only when the container is *not* provably running | README, deployment guide and the configure-suite header distinguish unit-state from container-state uncertainty and document the running-container restoration exception | configure suite 64/0 with the F2 controls |

The F1 regression also asserts the fault fixture actually failed the append (the log has no
`CHECK cleanup_required=FAIL`), so the green result is the in-memory authority, not a writable-log pass.
F1's other required controls already existed and still pass: ordinary success (`RESULT=PASS`, exit 0),
writable-log cleanup failure (recorded FAIL, exit 1), existing primary failure (rc 7 reported first), and
the INT/TERM `trap-child` statuses (130/143).

New rehearsal documentation checks: `guide binds the application sequence to the reviewed host identity`
and `guide forbids blindly deriving the expected identity on the target` (both PASS).

The `sudo VAR=value command` form the guide now uses is the documented sudo(8) environment-assignment
syntax; with the normal wheel `ALL` rule the SETENV tag is implied, so it is honored under ordinary
`env_reset`. A host with a restricted, non-SETENV sudo rule should use the 6.2 root-owned pin instead,
which is exactly why that alternative is documented. No privileged command was run to verify this; it is
read from the installed `sudo(8)`/`sudoers(5)` manuals.

### 14.5 Final offline gate run (2026-09-20, America/Bogota; dirty tree at §14.8)

| Command | Actual result |
| --- | --- |
| `bash tests/test-hermes-manual-profile.sh` | 358 passed, 0 failed |
| `bash tests/test-hermes-manual-review.sh` | 142 passed, 0 failed (was 138) |
| `bash tests/test-hermes-manual-backup.sh` | 43 passed, 0 failed |
| `bash tests/test-hermes-manual-configure.sh` | 64 passed, 0 failed (was 48) |
| `bash tests/test-hermes-manual-contract.sh` | 30 passed, 0 failed |
| `bash tests/test-hermes-manual-m01-tempdir.sh` | 9 passed, 0 failed |
| `python3 -B -m unittest discover -s tests -p test_hermes_manual_hardening.py` | 21 tests OK |
| `bash tests/test-hermes-guide.sh` | 217 passed, 0 failed |
| `bash scripts/hermes/manual/boot/rehearse-clean-install.sh` | `REHEARSAL=PASS failures=0 advisories=0` (two new checks) |
| `bash -n` on the changed shell files | PASS (`lib-manual-common.sh`, `m03-configure-and-probe.sh`, `rehearse-clean-install.sh`, `test-hermes-manual-review.sh`, `test-hermes-manual-configure.sh`) |
| Python AST parse of `config/harden-config.py`, `config/verify-contract.py` (`-B`) | PASS; no changed Python file this pass, no new `__pycache__` |
| `git diff --check` | clean |

The runner identity was UID 1000 (non-root). That matters only for F1: the regression deliberately does
not depend on mode bits, so it is red-capable for root too.

### 14.6 F4 — the documented prior-state exception

`m03-configure-and-probe.sh` computes `prior_ok=0` only when the unit query is undetermined **and** the
container is not provably running. When `mp_container_state` proves the gateway container is running, the
helper may stop the gateway even though the unit state is failed or transitional, and
`gw_restore_obligation=1` makes the cleanup hook restart it. The corrected wording:

- `scripts/hermes/manual/README.md` splits the two uncertainties (a failed/transitional **container**
  query refuses everything; a failed/transitional **unit** query refuses the stop unless the inventory
  proves the container is running) and records the exception in the shared-capture bullet.
- `docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md` §6.4 makes the same distinction.
- `tests/test-hermes-manual-configure.sh`'s header now says a failed/transitional/divergent **container**
  state refuses mutation and never selects the one-shot relabel path.

Historical overstatement, recorded rather than rewritten: §12.3's V2 gate text ("an undeterminable
obligation refuses mutation; m04-backup, m02 and m03-configure share the capture") and §12.4's V2 row
describe `mp_capture_service_state` as universally refusing. That is exact for `m04-backup` and `m02`,
and exact for `m03-configure` only when the container is not provably running; §14.6 is the corrected
statement. §10–§13 are left intact as the evidence they were.

### 14.7 §13.3 live-contract labeling-retry concern — disposition

Inspection only, not reproduced. `m03-contract.sh` relabels a contract file written into a live `:Z`
mount only when `mp_install_reconcile` reports `CHANGED`, and both `chcon` attempts are suppressed. A
first label that fails or is interrupted is therefore not repaired by a byte-identical retry; the next
contract run should fail because the live container cannot read the file. No SELinux guest was available
offline, so real acceptance is **not** claimed and no mock is presented as SELinux evidence. The
limitation is documented in the README operational notes; the repository behavior is unchanged by this
pass. If a future authorized guest run confirms it, the natural correction is to reconcile the label
(both attempts surfaced) on the unchanged path as well.

### 14.8 Outcome, limitations and next action

| Item | Value |
| --- | --- |
| Branch / HEAD | `codex/hermes-fedora44-manual-review` / `130bf8f2dbdc95e0db25407d5b3b155b627d1473` (unchanged; no commit) |
| Changed tracked / untracked | 14 / 0 |
| Diffstat before this section's final write | `14 files changed, 1284 insertions(+), 109 deletions(-)` |
| Fingerprint before §14 was written (pre-edit) | `919ff6a351f56f1241ae71b676dd4ee82c223c6d44c61d7ebac018e3bcefd926` |
| Fingerprint before this section's final write | `c82e470c72a6441b03ad91e984e1a611970ffec130bf5f233d1194f0836a925b` — measured **before** the final write; because this record is itself a changed file, re-reading it after the edit yields a new digest. Recompute with the §10.1 algorithm |

Changed files this pass: `scripts/hermes/manual/lib-manual-common.sh`,
`scripts/hermes/manual/m03-configure-and-probe.sh`,
`scripts/hermes/manual/boot/rehearse-clean-install.sh`, `scripts/hermes/manual/README.md`,
`docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md`,
`tests/test-hermes-manual-review.sh`, `tests/test-hermes-manual-configure.sh`, and this record. The other
six changed files are the preserved §12 corrections.

Disposition: F1–F4 are corrected offline with permanent repository regressions. The
outcome is **corrected offline, pending fresh independent review** — not deployment-ready.

Remaining mandatory checks (NOT RUN):

- `shellcheck`, `shfmt -d -l -i 2 -ci -bn`, `markdownlint-cli2` and the Lefthook hooks: the tooling
  (`devbox`, `shellcheck`, `shfmt`, `markdownlint-cli2`, `shellspec`) is still absent, so `bash -n`, the
  Python AST parse and `git diff --check` are fallback evidence only.
- Runtime acceptance on a separately authorized fixture: real rootless Podman, SELinux (`:z`/`:Z`) relabel
  behaviour (including §14.7), DAC access to `gateway-state`, systemd interruption/recovery, reboot
  persistence, and a real guest probe / provider acceptance.
- The F2 activation gate is validated only with synthetic systemd/Podman stubs; a real gateway's behavior
  when the probe fails remains unobserved.
- The SIGKILL temporary-state limitation and the full exit-0 M01 run limitation are unchanged.

**Exact next action:** obtain another independent fingerprint-bound offline review of this repository-only
pass (keyed to the post-write recomputation of the §14.8 fingerprint) before requesting any Gate 2
authorization. Gate 2 remains paused after Phase 5.

**Boundary confirmation:** no lab or production contact, no deployment, no host or installed-grant
change, no real credential access or provisioning, no provider call, no package installation, and no
commit or push. Only synthetic fixtures, temporary state, mocked privileged/runtime commands, repository
inspection and this record were used.

