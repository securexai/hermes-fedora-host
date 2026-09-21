# Independent offline review: Hermes manual-profile corrections

## Verdict

**Changes requested. The existing suites pass, but “all eleven findings corrected” is not supported.**
Two high-priority defects and eight additional correction gaps are listed below. Eight findings have
local behavioral reproductions; R1 and R10 are source-derived and have not been exercised on a guest.
No implementation fixes were made during this review.

## Reviewed artifact and boundaries

- Review performed 2026-09-20, America/Bogota (environment observation: `10:29:19-05:00`).
- Repository: `/var/home/aicloudopspecial/code/repos/mikrotik`.
- Branch: `codex/hermes-fedora44-manual-review`.
- HEAD: `2340887183f75f30215088f37b39bf63a0a453c0`.
- Working tree: 29 modified and 6 untracked files; tracked diffstat: 1121 insertions, 432 deletions.
- Dirty-input digest: `a46c6ef17f29bce5ac00e34d8a92a7a7cb9919e08534024ebcd5f3c10ddd23fa`.
  Computed as SHA-256 over sorted changed/untracked relative paths, each followed by NUL and the
  SHA-256 binary digest of that file's contents. This identifies the reviewed changes, not the whole checkout.
- Bash 5.3.9, Python 3.14.7, PyYAML 6.0.3.
- The [handoff record](/var/home/aicloudopspecial/code/repos/mikrotik/docs/plans/2026-09-20-hermes-manual-review-corrections.md)
  was treated as a claim to verify, not as runtime evidence or authorization.
- No target contact, actual privileged command, installed-grant inspection/change, VM operation,
  provider call, real credential access/provisioning, commit, push, or implementation edit.
  Tests used synthetic state and mocked privileged/runtime commands. The rehearsal generated disposable test keys.

## Findings, ordered by priority

### R1 — P1: The new contract helper removes access for its own container user

**Source-derived; guest reproduction NOT RUN.**

[m03-contract.sh:74](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m03-contract.sh#L73-L84)
executes `install -d -o hermes -g hermes -m 0700` on the existing gateway-state directory.
That resets its ownership and mode, including on a rerun. The subsequent
[one-shot container:60–64](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m03-contract.sh#L55-L65)
runs as UID/GID 10000 in the runtime account's default rootless namespace, with no ownership mapping option
and with the image bootstrap bypassed.

Host user `hermes` maps to namespace UID 0, not container UID 10000. A mode-0700 directory owned by that
host account therefore prevents the selected container user from accessing the mounted state. The helper
can undo a previously working mapped ownership and then fail both application and verification.

**Correction:** preserve correct existing mapped ownership; initialize fresh state using the runtime
namespace's UID/GID 10000 mapping. Add a test of the whole helper's ownership sequence and later verify
real DAC/SELinux behavior on the separately authorized fixture. Do not solve this by making state world-readable.

### R2 — P1: Backup still treats unknown writer state as positively stopped

**Behaviorally reproduced using the existing synthetic backup fixture.**

[m04-backup.sh:121–135](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m04-backup.sh#L121-L135)
discards status-query failures with `|| true`, accepts every service-state string except `active`, and
interprets a failed/empty `podman ps` as no running containers. This also accepts `deactivating` and
`activating`, rather than requiring a positively established stopped state.

With successful-but-ineffective stop stubs, failed service/container queries, and the synthetic worker
still marked active, the actual helper produced:

```text
CHECK writers_stopped=PASS
CHECK backup_archive=PASS
RESULT=PASS
ACTUAL_EXIT=0
SYNTHETIC_WRITER_STATE=active
```

A separate `deactivating` fixture also passed. The archive can therefore be labeled consistent without
establishing that writers have stopped.

**Correction:** validate both query status and an explicit acceptable state; account for systemctl's
normal nonzero inactive status rather than requiring zero indiscriminately. Require a successful Podman
inventory. Unknown, transitional, or failed observations must block archiving. Test all of these cases.

### R3 — P2: Restoration failures and some interruptions still return success

**Behaviorally reproduced.**

[m04-backup.sh:270–279](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m04-backup.sh#L268-L279)
captures restoration failure but only prints it; `mp_finalize` receives the earlier pipeline status.
The [cleanup runner and traps](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/lib-manual-common.sh#L339-L365)
likewise never promote a successful status to failure after unsuccessful cleanup.

Using the existing `STUB_START_FAIL=hermes-worker.service` seam:

```text
RESTORE_FAILED service state restoration failed
RESULT=PASS
CLEANUP_FAILED hook=restore_service_state (the primary status is preserved)
ACTUAL_EXIT=0
FINAL_WORKER=inactive
```

The same finalization pattern exists in
[m02-deploy-and-validate.sh:450–458](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m02-deploy-and-validate.sh#L450-L458)
and [m03-configure-and-probe.sh:198–206](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m03-configure-and-probe.sh#L198-L206).
Separately, `source "$LIB"; mp_install_trap; kill -TERM $$` exits 0 when no preceding command failed.

**Correction:** retain an already-nonzero primary failure, but make failed restoration nonzero when the
primary operation succeeded. Report restoration in required checks before publishing PASS. INT/TERM
should return an interruption status, not the incidental previous command's successful status.

### R4 — P2: The convergence installer reports successful changes when installation failed

**Behaviorally reproduced.**

[mp_install_if_changed:522–535](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/lib-manual-common.sh#L522-L535)
unconditionally prints `CHANGED` and returns 0 after `install`, even if that command fails.
The callers run without `errexit` and typically test only that an old destination remains readable.
A failed upgrade can thus retain stale helpers/contracts/Quadlets while claiming installation succeeded.

```text
install: cannot stat '<synthetic absent source>': No such file or directory
CHANGED <synthetic destination>
INSTALL_FUNCTION_RC=0 DEST_EXISTS=no
```

It also skips mode/owner reconciliation when bytes match: a destination at mode 0666 remained 0666
after requesting 0644 and was reported `UNCHANGED`.

**Correction:** propagate install failure and have callers abort/record FAIL. Convergence must compare
and repair required metadata as well as content, without needless rewrites of already-correct files.

### R5 — P2: Worker-key provisioning bypasses the shared profile lock

**Behaviorally reproduced at the real helper's `main` seam, with all mutation functions stubbed.**

[provision-worker-client-key.sh:104–122](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/provision-worker-client-key.sh#L104-L122)
checks identity and then provisions/chowns shared key material without calling `mp_lock_profile`.
A parent held the actual shared flock while the helper still reached its mutation function and returned 0:

```text
LOCK_HELD=yes
MUTATION_REACHED_WITH_LOCK_HELD=yes
PROVISION_EXIT=0
```

This is a residual omission, not a newly edited file. It invalidates the new claim that every mutating
helper participates and allows provisioning to interleave with deployment/backup key operations.

**Correction:** acquire the same lock before the first mutation. Extend the eight-helper contention
fixture to include this entrypoint and both credential-provisioning entrypoints.

### R6 — P2: M01's temporary-directory registration is still lost across its pipeline

**Behaviorally reproduced with the actual library and the caller's pipeline shape.**

[m01-host-prepare.sh:96–103](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m01-host-prepare.sh#L96-L103)
now calls `mp_secure_tmpdir_var` directly, but the call remains inside the `{ ... } | tee` reporting
subshell. The outer shell's trap never receives that child's cleanup registration.

```text
PARENT_REGISTERED=0
LEAKED_AFTER_EXIT=yes
```

This was reproduced with normal exit; it is not a SIGKILL limitation. The M01 directory here contains
a public-key copy, so this reproduction does not establish a credential leak. The backup helper's
directory allocation is correctly outside its pipeline and is not implicated in this particular defect.

**Correction:** allocate/register in the parent before the pipeline, or install/run cleanup in the
actual owning process. Add a call-site test, not only a direct library-function test.

### R7 — P2: Missing DNS tooling is still graded as isolation PASS

**Behaviorally reproduced by executing the unchanged DNS block with a mocked `h` command.**

[m02-deploy-and-validate.sh:358–368](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m02-deploy-and-validate.sh#L358-L368)
checks the earlier curl/timeout marker but never proves `getent` exists. It suppresses the DNS command
status and grades any output without an address as PASS. The printed `dns_rc` is the status of `echo`.

```text
-- worker DNS: timeout: failed to run command getent: No such file or directory --
dns_rc=0
CHECK worker_dns_isolation=PASS
```

**Correction:** check the actual DNS tool, capture its status immediately, and distinguish unresolved
names from missing tools, execution failures, and timeouts. The literal IPv4/IPv6 classifier improvement
does not cover this separate path.

### R8 — P2: The independent verifier permits extra security-controlled platform overrides

**Behaviorally reproduced against a synthetic, otherwise-conforming profile.**

[verify-contract.py:29–46](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/config/verify-contract.py#L29-L46)
recursively checks only desired mapping keys. Its additional exact-emptiness checks cover only hooks
and MCP servers, not all paths in the contract's replacement list.

Adding `platform_toolsets.discord: [hermes-cli]` still produced `CONTRACT_VERIFY=PASS`, exit 0,
although applying the contract would remove that broad override.

**Correction:** enforce exact desired values/subtrees for all replacement paths; continue allowing
unmanaged keys only outside those paths. Test reintroduced per-platform integrations. This is a verifier
gap; the actual applier did remove populated hooks/MCP mappings in the existing tests.

### R9 — P2: Hardening `--check` ignores environment-policy drift

**Behaviorally reproduced.**

[harden-config.py:199–206](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/config/harden-config.py#L199-L206)
returns from check mode based only on YAML configuration, before inspecting the environment policy.
After a successful apply, changing the API-server flag to `true` still produced:

```text
PROFILE_CONTRACT_CHECK=PASS the on-disk configuration matches the contract
CHECK_EXIT=0
```

The separate verifier catches environment drift when explicitly supplied its environment-file argument;
this finding concerns the advertised profile-contract check mode.

**Correction:** check the contract's environment allowlist without writing, or explicitly narrow/rename
the interface and stop describing it as full profile-contract verification. Test changed and missing
policy environment files.

### R10 — P2: No-change configuration runs still stop and start the gateway

**Source-derived residual defect; real restart counters NOT measured.**

[m03-configure-and-probe.sh:101–103](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m03-configure-and-probe.sh#L101-L103)
unconditionally stops the gateway before checking whether any setting differs, and
[lines 174–177](/var/home/aicloudopspecial/code/repos/mikrotik/scripts/hermes/manual/m03-configure-and-probe.sh#L174-L177)
unconditionally start it again. Skipping individual `config set` calls does not make the helper
service-convergent. A healthy, unchanged profile still gets a service interruption on every run.

**Correction:** determine configuration drift before lifecycle changes and separate deliberate daemon
acceptance probes from ordinary convergence. The proposed no-restart-churn acceptance criteria also need
explicit exceptions for deliberately stopped-state backup tests.

## Fresh check results

Run from the Hermes repository root, using host tools because Devbox is absent:

| Check | Actual result |
| --- | --- |
| `bash tests/test-hermes-manual-review.sh` | 64 passed, 0 failed |
| `bash tests/test-hermes-manual-backup.sh` | 23 passed, 0 failed |
| `python3 -B -m unittest discover -s tests -p test_hermes_manual_hardening.py` | 12 tests OK |
| `bash tests/test-hermes-guide.sh` | 217 passed, 0 failed |
| `bash scripts/hermes/manual/boot/rehearse-clean-install.sh` | `REHEARSAL=PASS failures=0 advisories=0` |
| Profile suite, isolated administrator-home adaptation | 358 passed, 0 failed |
| `bash -n` on all 23 changed/new shell files | PASS |
| Python AST parse of all 3 changed/new Python files | PASS; no bytecode compilation claimed |
| `git diff --check` | PASS |

**Profile-suite safety adaptation:** the original
[test:503–519](/var/home/aicloudopspecial/code/repos/mikrotik/tests/test-hermes-manual-profile.sh#L503-L519)
unconditionally removes a fixed log in the current account's real home before and after its inspection
check. Rather than touching that path, the test was loaded into memory with a stubbed passwd lookup
pointing to a disposable administrator home. Production code and the checked source files were unchanged.
The first adaptation placed the log inside the directory whose emptiness the test measures (357/1);
separating those two fixture directories corrected the harness error (358/0). This is not an unchanged
reproduction of the original profile-suite command.

Adversarial backup checks reused the pre-test setup/functions from the existing
[backup test](/var/home/aicloudopspecial/code/repos/mikrotik/tests/test-hermes-manual-backup.sh#L32-L201),
changing only synthetic command behavior in memory. The actual backup helper was unmodified. Other
probes used sourced library functions, the real provisioning `main` with mutation functions replaced,
the extracted unchanged DNS block, and hardening/verifier subprocesses on temporary synthetic profiles.
Only relevant markers were reported. No real services or containers were invoked.

**Not run:** Devbox, ShellCheck, shfmt, markdownlint-cli2, ShellSpec, Lefthook, SELinux/Podman/systemd
integration, actual interruption recovery of services, reboot/restore acceptance, provider/messaging,
or encrypted-storage/TPM checks. The named lint tools and Devbox are absent; passing syntax/static
checks is not a replacement for those gates.

## Disposition of the original eleven claims

| Original finding | Independent assessment |
| --- | --- |
| F1 privileged wrapper executes checkout code | The specific checkout dependency was removed; root-owned dependency installation and mocked rejection tests verified. Installed grant state remains unknown. |
| F2 populated hooks/MCP retained by merge | Corrected by the applier; behavioral tests pass. Broader verifier limitations remain in R8. |
| F3 backup failures and writer checks | Tar/create/extract checks improved, but closure blocked by R2 and R3. |
| F4 temporary cleanup/restoration | New primitives work directly, but call-site cleanup and exit-status gaps remain: R3/R6. |
| F5 one profile lock | Eight tested helpers contend correctly; coverage is incomplete: R5. |
| F6 missing tool interpreted as isolation | Literal-IP probes improved; DNS retains the false-positive path: R7. |
| F7 ausearch no-matches interpretation | Shared implementation and mocked clean/denial/error/absent cases verified; live audit behavior not tested. |
| F8 credential-free contract application | Added and sequenced, but new ownership defect blocks confidence in execution: R1. Verification also has R8/R9 gaps. |
| F9 informational/deferred accounting | Shared accounting tests pass; required UNVERIFIED still blocks. End-to-end credential-free acceptance is not proven. |
| F10 convergence | Python no-op/backup tests pass; installation error/metadata handling and lifecycle convergence remain incomplete: R4/R10. |
| F11 records reconciled | Current-runtime boundary and outstanding TOFU verification are explicit. Technical “all corrected” claims need revision in light of this review. |

## Next step

Correct the confirmed source defects and extend the offline tests before treating the corrections as
closed. This review does not authorize those implementation changes or resumption of Gate 2. Any later
runtime request must retain the domain-UUID/MAC/fresh-DHCP binding, explicit reboot scope, separate
credential/provider/TPM permissions, and outstanding console host-key verification.
