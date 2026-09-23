# Fedora SSH key-only execution record

Approved 2026-09-12 by the user instruction to implement the supplied plan.
This historical record tracks preparation; it does not authorize production execution.

## Approved baseline

Create a dedicated Bash 5+ Fedora Server console helper and companion guide alongside
`/home/cloudops/code/scripts/setup-ssh-server.sh`. Prepare reviewable copies in this repository.
Preserve the original helper and unrelated workspace changes. No production execution, reboot,
commit, push, or PR changes. Explicit user, public-key file, interface and zone arguments;
read-only dry run; key preservation and deduplication; dedicated key-only drop-in;
validated effective configuration; runtime and permanent firewall allowance; service enablement;
rollback with residual package/host-key disclosure. Remote acceptance is separate.

## Tasks and gates

| ID | Dependency | Task progress | Validation status | Acceptance and method |
| --- | --- | --- | --- | --- |
| S1 | None | ✅ COMPLETE | ✅ PASS | Bash syntax, ShellCheck, shfmt, scoped Markdown lint and links passed; final document refresh checked separately |
| S2 | S1 | ✅ COMPLETE | ✅ PASS | 17 tests passed, including real sshd candidate parsing and mocked preservation/failure paths |
| S3 | S1, S2, disposable server | 🚧 BLOCKED | 🚧 BLOCKED | Disposable Fedora: key login; password/root rejection; enforcing SELinux; unrelated settings; rerun |
| S4 | S3, scheduled reboot authorization | ⬜ TODO | 🚧 BLOCKED | Scheduled test reboot and subsequent key login; no reboot authorized in baseline |
| S5 | S1, S2 | ✅ COMPLETE | ✅ PASS | Installed both files at the approved destination; exact bytes/hashes verified; original helper unchanged |

Affected documentation: [companion guide](../../setup-ssh-key-only.md); this record is the canonical tracker.
S3 cannot substitute existing Hermes certification evidence. S4 remains separately recorded.

## Evidence and decisions

- 2026-09-12: inspected repository guidance, contributor checks, original external helper,
  SSH helper conventions, VM guide and Hermes ledger. Original external helper enables passwords.
- Created branch `codex/fedora-ssh-key-only` from `4a19d3f`; existing changes preserved.
- Read-only hypervisor inventory through Devbox failed: sandbox denied libvirt socket access.
  No VM or production state was changed. Assess elevated read-only inventory before S3.
- Initial plan-writing command failed because Devbox reinterpreted multiline shell arguments.
  Rewrote this record using the patch tool; use file-based commands for subsequent multiline work.
- Source references and operator procedures live in the companion guide.
- User explicitly reconfirmed `/home/cloudops/code/scripts` as the destination during implementation.
- Elevated read-only `virsh -c qemu:///system list --all` succeeded: no defined VMs.
  The image pool contains only a Kinoite installer ISO; Downloads contains Fedora Server installation
  media, but no installed disposable Server/Cloud image. No guest was created or modified. S3 needs a
  provisioned disposable Fedora Server; an installer ISO alone cannot execute its acceptance checks.
- Initial ShellCheck: ❌ FAIL, empty-assignment and unused-variable warnings; corrected.
- Initial 13-test run: ❌ FAIL, three failures caused by querying SELinux context on an unlabeled
  temporary filesystem. Query context only when SELinux is enabled; no SELinux enforcement claim
  follows from this mock test. Corrected 13-test run: ✅ PASS, 111.303 seconds.
- Expanded 16-test run: ✅ PASS, 133.171 seconds. Later candidate-parser correction invalidated this
  result: 🔁 STALE. Tests include persistent NetworkManager assignment, standard IPv6 policy and
  modified-policy rejection, plus read-only candidate conflict detection.
- Additional real `/usr/sbin/sshd` candidate test: ❌ FAIL, `/dev/fd/63` unavailable because sshd closes
  inherited descriptors. Switched candidate input to `/dev/stdin`; targeted rerun: ✅ PASS, 0.236 seconds.
  This validates configuration parsing, not network authentication.
- First documentation invocation inherited repository globs (33 files); replaced with isolated copies
  of exactly the two changed Markdown documents and a temporary configuration with `fix: false`.
  Scoped result: ✅ PASS, two files and zero errors. Subsequent final record edits require another check.
- Standard firewalld IPv6 policy fields checked against upstream policy and command-renderer sources.
  Default-zone lookup uses the documented combined runtime/permanent setting; no permanent flag.
- Final S1/S2 validation completed 2026-09-12 at 20:33:24 UTC on Fedora 44 workstation kernel
  `7.2.4-200.fc44.x86_64`, through Devbox. Bash syntax, ShellCheck, shfmt, all 17 tests (134.481 seconds),
  two-file Markdown lint and `git diff --check` returned zero. No skips in the 17-test run.
  [Machine-readable evidence](evidence/2026-09-12-fedora-ssh-key-only.json) retains exact commands,
  timestamps, outputs and SHA-256 identities for the tested script, guide and behavior suite.
- S5: installed `/home/cloudops/code/scripts/setup-ssh-key-only.sh` (0755) and
  `/home/cloudops/code/scripts/setup-ssh-key-only.md` (0644) after successful validation. The installer
  refused existing destinations, verified source hashes against evidence, compared installed bytes,
  and verified the original `setup-ssh-server.sh` hash remained unchanged. No server helper was executed.
- Repeat scoped documentation/link checks with
  `devbox run -- python3 tests/check_ssh_key_only_docs.py`. The original temporary validator is superseded
  by this retained equivalent, which also checks relative link targets. Final record refresh is validated
  separately and does not invalidate unchanged shell/test artifacts.

## Remaining acceptance and handoff

### Reported Fedora service drop-in correction

2026-09-12: user supplied Hermes dry-run failure and the full systemd unit output.
The inherited `/usr/lib/systemd/system/service.d/10-timeout-abort.conf` contains only
`[Service]` and `TimeoutStopFailureMode=abort` apart from comments and blank lines.
Prepare a narrow local correction on the existing feature branch; preserve unknown-override refusal.
No production execution is authorized by this correction.

| ID | Dependency | Task progress | Validation status | Acceptance and method |
| --- | --- | --- | --- | --- |
| S6 | S1, S2 | ✅ COMPLETE | ✅ PASS | Exact path/content exception implemented; 21 behavior tests and shell/documentation checks passed; live acceptance remains S3/S4 |

Earlier S1/S2 evidence describes the previous artifact and is stale for the corrected script.
S5 records the previous delivery only; external copies need refreshing after S6 validation.
S6 evidence, 2026-09-12, Devbox on workstation Linux `7.2.4-200.fc44.x86_64`:

- `devbox run -- bash -n setup-ssh-key-only.sh`: expected/actual exit 0.
- `devbox run -- shellcheck setup-ssh-key-only.sh`: expected/actual exit 0.
- `devbox run -- shfmt -d -l -i 2 -ci -bn setup-ssh-key-only.sh`: expected/actual no diff, exit 0.
- `devbox run -- python3 -m unittest discover -s tests -p test_ssh_key_only.py`:
  expected all pass; actual 21 tests passed, no skips, 85.415 seconds.
- `devbox run -- python3 tests/check_ssh_key_only_docs.py`: initial invocation failed (exit 127,
  Devbox temporary launcher missing during concurrent invocations); sequential retry passed,
  two files, zero lint errors and relative links valid. Final record refresh checked separately.
- `devbox run -- git diff --check`: expected/actual exit 0.
- Script SHA-256: `0b8fbc8b662e70cb34b844971fbfcc4d7cef9ca5045115661e2e98f0921bb70a`.
- Behavior suite SHA-256: `93080afb13e35d18398dbac3e82e751b0169ceea0d7c54621e298c0e938958f9`.
- Companion guide SHA-256: `562e6530c2014ea1eb4b558f68d7f45dc1646a6d5ec6c5782bd95c0410d563ce`.

Next action for this correction: transfer the corrected repository helper to the operator's server copy
and rerun the same console dry run. This session changed repository files only; the historical S5
external installation and Hermes copy have not been refreshed. S3/S4 remain unmet.

### Empty sshd environment correction

2026-09-12: the next operator dry run refused `/etc/sysconfig/sshd`; supplied active contents
were exactly `OPTIONS=""`. Prepare a local correction accepting explicit empty OPTIONS assignments
without evaluating the file. Preserve nonempty/unknown-setting refusal and file contents.

| ID | Dependency | Task progress | Validation status | Acceptance and method |
| --- | --- | --- | --- | --- |
| S7 | S6 | ✅ COMPLETE | ✅ PASS | Empty OPTIONS accepted and preserved; nonempty values, other variables, executable text and nonregular files rejected; 24 tests plus shell/documentation checks passed |

S6 validation remains historical and is stale for the S7 artifact. External copies require another transfer.
The operator used SSH through sudo without triggering the environment-based console guard; that guard
is not proof of a local console. Apply remains a console-only procedure; no live changes are made here.
S7 validation on 2026-09-12 at 21:31 UTC, in the same Fedora 44 workstation Devbox environment:

- `devbox run -- bash -n setup-ssh-key-only.sh`: expected/actual exit 0.
- `devbox run -- shellcheck setup-ssh-key-only.sh`: expected/actual exit 0.
- `devbox run -- shfmt -d -l -i 2 -ci -bn setup-ssh-key-only.sh`: expected/actual no diff, exit 0.
- `devbox run -- python3 -m unittest discover -s tests -p test_ssh_key_only.py`:
  expected all pass; actual 24 tests passed, no skips, 107.273 seconds.
- `devbox run -- python3 tests/check_ssh_key_only_docs.py`: expected/actual two files,
  zero lint errors, relative links valid; repeated after this record refresh.
- `devbox run -- git diff --check`: expected/actual exit 0.
- Script SHA-256: `06e70bdb99c78d76b6f0de051e5fddce6bb1cd3d8719613ade367918ad1df569`.
- Guide SHA-256: `524131e68eaa1f93be0d12a29022e50b672bd5c06c286bd8881bdb975887f933`.
- Behavior suite SHA-256: `04f022202681d16e1ff3ff3f460e534c4213e78848818bfec56e0705ae7ca70e`.

Next action for S7: transfer the current repository helper/guide to Hermes and repeat the operator's
console dry run with `eno1` and `id_ed25519_cloudops.pub`. Neither external copies nor production
configuration were changed here. Disposable live acceptance S3 and reboot acceptance S4 remain unmet.

### Consolidated live preflight

2026-09-12: user requested faster direct Hermes validation and confirmed key/agent setup complete.
Scope is read-only SSH configuration and firewall preflight, with one operator-run privileged collector
if sudo authentication is needed. No production configuration change or reboot is authorized.

| ID | Dependency | Task progress | Validation status | Acceptance and method |
| --- | --- | --- | --- | --- |
| S8 | S7, key access | ✅ COMPLETE | ❌ FAIL | Operator root report retrieved; unsupported include/policies and permanent-zone status found; candidate gate blocked |

Live pinned key-only SSH as `aicowork@10.0.30.10` succeeded. Fedora 44, SELinux Enforcing,
`eno1` at `10.0.30.10/24`, enabled/active sshd and firewalld, disabled/inactive sshd.socket,
home/SSH-directory/authorized-keys modes 0700/0700/0600 observed. Remote helper matches S7 SHA-256.
NetworkManager connection.zone is empty; default-zone fallback still needs validation.
`sudo -n true` failed: password required. No privileged checks or configuration changes occurred.
Prepared [original read-only collector](evidence/2026-09-12-hermes-ssh-preflight-s7.py); it verifies the S7 helper
hash, calls only inspection functions, filters effective SSH output to authentication/port/key-path
fields, and collects runtime/permanent firewall diagnostics. Candidate parsing depends on supported
SSH configuration; other checks continue independently. It does not change configuration or run apply.
At 2026-09-12 21:48 UTC, through workstation Devbox:

- `python3 -m py_compile docs/plans/evidence/2026-09-12-hermes-ssh-preflight.py`: expected/actual exit 0.
- `python3 docs/plans/evidence/2026-09-12-hermes-ssh-preflight.py`: expected/actual exit 1 with
  root-required message; this verifies the unprivileged guard, not live root checks.
- `python3 tests/check_ssh_key_only_docs.py`: expected/actual two files, no lint errors, links valid.
- `git diff --check`: expected/actual exit 0.
- Collector SHA-256: `a4675c7ecf974ad20c40b8220b26381e9f259aa8d486fc5553cb82572c01c1be`.

Next action: operator copies this collector to `~/hermes-ssh-preflight.py` on Hermes and runs
`sudo python3 ~/hermes-ssh-preflight.py > ~/hermes-ssh-preflight.json` once. Retrieve the JSON
over the working key connection and review all results. No collector was copied remotely by this session.
This baseline key login does not close S3 key-only acceptance.

Operator ran the collector; [S7 live report](evidence/2026-09-12-hermes-ssh-preflight-s7.json)
at 2026-09-12 21:51:04 UTC confirms syntax and service override/environment checks pass.
Current SSH still allows passwords and root public-key login; candidate parsing was blocked by the
unsupported Include gate. Firewall lists the five gateway policy-set members; their disable state was
not collected. Permanent interface lookup returns exit 2 with `no zone` on stderr, which S7 rejects
before the intended NetworkManager/default-zone fallback. Unprivileged follow-up queries were denied.

| ID | Dependency | Task progress | Validation status | Acceptance and method |
| --- | --- | --- | --- | --- |
| S9 | S8 findings | ✅ COMPLETE | ✅ PASS | Local compatibility fixes and expanded collector prepared; 27 helper tests, 2 collector tests and static/doc checks pass; live confirmation remains S10 |
| S10 | S9, operator sudo | ✅ COMPLETE | ❌ FAIL | Firewall compatibility passed; crypto-policy symlink blocked supported config, candidate and full dry run |

S7 offline passes remain historical and are stale for S9. Prepare local compatibility fixes together;
do not assume the live include or gateway disable states until the refreshed collector confirms them.
The collector will include Include directives, full policy status, independent NetworkManager checks
and key/path preconditions so further findings are reviewable without individual command exchanges.
S9 evidence, 2026-09-12 21:57 UTC, same Fedora 44 workstation Devbox environment:

- `devbox run -- python3 -m unittest discover -s tests -p test_ssh_key_only.py`:
  expected/actual all 27 tests passed, no skips, 134.126 seconds.
- `devbox run -- python3 docs/plans/evidence/2026-09-12-hermes-ssh-preflight-test.py`:
  expected/actual both tests passed in 0.005 seconds; host reads and subprocesses mocked.
  Tests verify failure gates block candidate/full preview while independent diagnostics continue.
- `devbox run -- bash -n setup-ssh-key-only.sh` and `devbox run -- shellcheck setup-ssh-key-only.sh`:
  expected/actual exit 0. Initial shfmt check failed on two parenthesis-spacing differences;
  `devbox run -- shfmt -w -i 2 -ci -bn setup-ssh-key-only.sh` corrected only that whitespace during
  the behavior-suite run. Subsequent `devbox run -- shfmt -d -l -i 2 -ci -bn setup-ssh-key-only.sh` passed.
- `devbox run -- python3 -m py_compile docs/plans/evidence/2026-09-12-hermes-ssh-preflight.py`:
  expected/actual exit 0.
- `devbox run -- python3 tests/check_ssh_key_only_docs.py`: expected/actual zero lint errors and
  relative links valid; repeated after final record refresh. `devbox run -- git diff --check`: exit 0.
- Script SHA-256: `4e1d7c302dd27ed6e208b8f100eae2e9aec7f310262f492ec66b6dd01a1d4931`.
- Guide SHA-256: `3d56f0ac989b772aff3310aa24df55bad20f8966ee3f22e5465bfc6b85179180`.
- Suite SHA-256: `8e3d20a11de133ea990ac78762de4ef75c779e88fb139a7da601adb627681f47`.
- Updated collector SHA-256: `704e044209a3be78929ff1426c708cdef48d6f7deb4b8aeeadb2e41e702045df`.
- Original report SHA-256: `9050a0950de279137dd22e7dfe35a986f7e57331c98e93b3d6c92082687c45e1`.

The companion guide links the official Fedora package and firewalld policy-set documentation.
Firewalld v2.4.0's [command source](https://github.com/firewalld/firewalld/blob/v2.4.0/src/firewall-cmd.in)
confirms `no zone` is an error-path response and supports querying administrative policy disable state.
No unsupported live include is presumed safe and no policy is accepted solely by its name.

Next action: operator copies S9 helper/guide and the
[updated collector](evidence/2026-09-12-hermes-ssh-preflight.py) to Hermes, then runs that collector
with sudo, redirecting stdout to `~/hermes-ssh-preflight.json`. Retrieve it over SSH and complete S10.
No production settings or external helper copies were changed by this session; S3/S4 remain unmet.

S10 [live report](evidence/2026-09-12-hermes-ssh-preflight-s9.json), 2026-09-12 21:59:36 UTC,
matches the S9 hash. Runtime/permanent firewall compatibility passed; all gateway policies explicitly
disabled, source lists empty and NetworkManager/default-zone fallback verified. SSH includes match the
documented Fedora layout. The crypto-policy input is a symlink, which the shared destination guard rejects.
Pinned read-only SSH `namei -l /etc/crypto-policies/back-ends/opensshserver.config` confirms it points to
`/usr/share/crypto-policies/DEFAULT/opensshserver.txt`, with root-owned non-group/world-writable directories
and target file. The link itself is root-owned. Candidate and full dry run remain blocked.
The [S9 collector](evidence/2026-09-12-hermes-ssh-preflight-s9.py) is preserved as historical evidence.

| ID | Dependency | Task progress | Validation status | Acceptance and method |
| --- | --- | --- | --- | --- |
| S11 | S10 | ✅ COMPLETE | ✅ PASS | Exact DEFAULT input link accepted with trusted ownership/modes; focused tests/static checks pass; corrected path check also passed live on Hermes |
| S12 | S11, stable packages, operator sudo | ✅ COMPLETE | ✅ PASS | Post-update report passes syntax, service/config checks, candidate, firewall and complete dry run; NetworkManager version warning retained |

Scope is a read-only input exception, preserving symlink rejection for managed destinations and other
SSH config files. S9 path/config evidence is stale for S11; unchanged firewall evidence remains valid.
S11 validation on 2026-09-12, workstation Devbox and pinned read-only Hermes SSH:

- Initial four crypto tests passed in 12.718 seconds. Added direct-link validation to reject an
  intermediate alias, invalidating that evidence; seven focused tests then passed in 13.496 seconds.
- Initial direct Hermes `inspect_crypto_path` invocation failed because the packaged target has two
  hard links (`stat -c '%h:%a:%u:%F'` returned `2:644:0:regular file`). This is read-only input;
  corrected the exception to allow a regular root-owned non-writable packaged target with hard links.
  Managed destinations retain their single-link requirement. Previous focused evidence became stale.
- Final focused command:

  ```bash
  devbox run -- python3 -m unittest discover -s tests -p test_ssh_key_only.py -k crypto -k symlink -k conditional -k real_sshd
  ```

  expected/actual seven tests passed, no skips, 15.541 seconds. Covers hard-linked policy preservation,
  unknown/dangling/indirect targets, writable paths, ownership mismatch, managed symlink/hard-link
  refusal, supported/unsupported includes and actual sshd candidate parsing.
- Final read-only Hermes check: stream reviewed helper over pinned key SSH to
  `bash -c 'source /dev/stdin; crypto=/etc/crypto-policies/back-ends/opensshserver.config; inspect_crypto_path'`.
  Expected/actual exit 0. No remote file copy, sudo, setup invocation or configuration change.
- `devbox run -- bash -n setup-ssh-key-only.sh`, `devbox run -- shellcheck setup-ssh-key-only.sh`,
  `devbox run -- shfmt -d -l -i 2 -ci -bn setup-ssh-key-only.sh`: expected/actual exit 0.
- `devbox run -- python3 docs/plans/evidence/2026-09-12-hermes-ssh-preflight-test.py`:
  expected/actual two mocked collector tests passed, 0.004 seconds.
- Final `devbox run -- python3 tests/check_ssh_key_only_docs.py` and
  `devbox run -- git diff --check`: expected/actual pass after record refresh.
  Initial record lint failed on the long focused-test command; formatted it as a code block and reran lint.
- Script SHA-256: `32ac4ba34bbff15ecef8869cb32b2e426bd6a9e8ee68b0768bb38e13215ad5dd`.
- Guide SHA-256: `371baf4575d263cf25041fa4259af2ac9d719be46a11971e58c9338656f55b00`.
- Suite SHA-256: `e3299f7d109f7c469506b48a49197b6d2f49a3d59a39304a222865c7dce2684a`.
- Collector SHA-256: `63d1847bf01022d6d525acf751ca547dfce0d4446b5679e38a80a1aa97f12fc8`.
- S9 live report SHA-256: `757a8bd9fca323221f22a9f468bdb3ba72d62f5bc8c8b993e2ef1fb5940cdf75`.

Next action: operator transfers current helper/guide and collector, then runs the same sudo collector
command. Retrieve `~/hermes-ssh-preflight.json` and evaluate S12. Firewall checks are already verified;
the full candidate/dry run still needs root read access. No server settings were changed in this session.

S12 first [live report](evidence/2026-09-12-hermes-ssh-preflight-s11.json), 2026-09-12 22:10:46 UTC,
matches S11 helper SHA-256. Syntax, service overrides/environment, supported SSH configuration,
candidate key-only configuration and firewall compatibility all returned 0. Full read-only dry run
returned 1: firewall-cmd could not import `_random`, reporting compiled Python 3.14.7 versus runtime 3.14.3.
The current SSH configuration still allows password authentication. No apply was invoked by the collector.

Direct read-only follow-up at approximately 22:13–22:14 UTC observed:

- `rpm -q python3 python3-libs`: both 3.14.7-1.fc44, with a transaction-lock-busy diagnostic.
- A fresh `/usr/bin/python3` process reported 3.14.7 and successfully imported `_random`.
- `/usr/sbin/firewall-cmd --version` succeeded and reported 2.4.4 (earlier baseline was 2.4.0).
- `ps -C dnf,dnf5,rpm,packagekitd -o pid,comm,etime`: a running DNF process, PID 5877.

These observations support a concurrent package upgrade as the cause of the mixed-version import.
This session did not initiate or alter that DNF process. Earlier live package-dependent evidence is
stale for the upgraded environment; offline code checks remain valid. No helper correction is needed
based on this error. Report SHA-256:
`b2452971675f9332687f165bd39fd29ca632919ab2d598d962a0f00874db72ee`.

Subsequent `ps -p 5877 -o pid,comm,etime,stat` returned no process (exit 1): the observed DNF process
has exited. This establishes process completion, not the transaction's success status.
Documentation/link checks and `git diff --check` passed after recording these findings.

Next action: rerun the already transferred S11 collector with sudo and retrieve its report.
No new script transfer is required. Keep S12 open until
the complete preview passes in stable package state. S3/S4 and production apply remain unperformed.

S12 post-update [live report](evidence/2026-09-12-hermes-ssh-preflight-s11-after-update.json),
2026-09-12 22:24:47 UTC, matches S11 helper SHA-256. All required inspection gates and
`complete_read_only_dry_run` returned 0. The complete preview reports `DRY RUN: no changes made`.
The expected raw permanent-zone lookup still returns 2/`no zone`; the verified NetworkManager/default
fallback passes, so this diagnostic is not an unmet gate. The earlier Python import failure is preserved above.

Observed limitation: nmcli 1.56.1 reports the running NetworkManager daemon is 1.56.0 and advises a
restart. Zone queries and full preview succeeded despite the warning. No NetworkManager restart,
reboot, package operation, SSH reload or configuration apply was performed by this session.
Current configuration still reports `passwordauthentication yes` and root login `prohibit-password`;
the proposed key-only configuration passed evaluation but has not been applied.

Documentation/link validation and `git diff --check` passed after this record update.
Next action: report the successful preflight for review. Production apply requires explicit operational
authorization and console access; post-apply authentication checks and S3/S4 remain unperformed.
The canonical plan remains open for its outstanding live acceptance and reboot gates.

### Operator apply and fresh account login

2026-09-12: operator reports running the helper without `--dry-run` for `aicowork`, key
`id_ed25519_cloudops.pub`, interface `eno1`, zone `FedoraServer`. Supplied output ends after DNF
reports required packages already installed and `Nothing to do`; it omits the helper's final status.
Operator also reports a DNF upgrade/refresh, consistent with the previously observed concurrent upgrade.
The assistant did not execute production apply, service restarts or a reboot.

| ID | Dependency | Task progress | Validation status | Acceptance and method |
| --- | --- | --- | --- | --- |
| S13 | Operator apply | ✅ COMPLETE | ✅ PASS | Fresh account key login succeeds; server offers only publickey and refuses the connection with public-key authentication disabled |

Pinned read-only SSH observations after the operator's apply:

- Fresh SSH with `BatchMode=yes`, `IdentitiesOnly=yes`, `ControlPath=none`, strict host checking
  and the cloudops identity succeeded as `aicowork` (exit 0). Further read-only SSH calls also succeeded.
- SSH with `PubkeyAuthentication=no`, preferred password/keyboard-interactive methods,
  `NumberOfPasswordPrompts=0` and `ControlPath=none` returned 255. Protocol debug advertised only
  `publickey`, followed by `Permission denied (publickey)`. No password was supplied. This confirms
  password and keyboard-interactive methods are not offered for this account/connection.
- `systemctl show sshd firewalld -p Id -p ActiveState -p SubState -p Job -p Result -p UnitFileState`:
  both services active/running/enabled, no pending job, result success.
- `ps -C bash,dnf,dnf5,systemctl,firewall-cmd -o pid,ppid,comm,etime,stat,wchan`:
  two idle interactive Bash processes; no listed package or service-management commands.

Live account key-only behavior is verified. The supplied output alone does not prove that every apply
step and cleanup completed. Root-login configuration, live rollback/rerun behavior and post-reboot
access remain unverified; S13 does not close the broader disposable S3/S4 gates.
Next action: report current account authentication success and retain console access; obtain final
apply status/root-configuration evidence before claiming complete live application acceptance.

### Operator reboot and persistence verification

2026-09-12: operator explicitly announced a server restart, then reported Hermes back online and
supplied a successful fresh SSH connection using the cloudops key. The assistant did not initiate the reboot.

| ID | Dependency | Task progress | Validation status | Acceptance and method |
| --- | --- | --- | --- | --- |
| S14 | S13, operator reboot | ✅ COMPLETE | ✅ PASS | Fresh key login, password-method rejection, enabled/running SSH and firewall verified after operator reboot |

Independent read-only checks through workstation Devbox and pinned SSH to `aicowork@10.0.30.10`:

- Fresh key login with `BatchMode=yes`, `IdentitiesOnly=yes`, `ControlPath=none` and strict host checking:
  exit 0. `uptime -s` reports boot at `2026-09-12 17:33:11` in the server's local time.
- With public-key authentication disabled, preferred password/keyboard-interactive methods and zero
  password prompts, fresh SSH returned 255 and advertised only `publickey`, followed by
  `Permission denied (publickey)`. No password was supplied.
- `systemctl show sshd firewalld NetworkManager -p Id -p ActiveState -p SubState -p UnitFileState -p Result`:
  all three active/running/enabled with result success.
- `nmcli -g GENERAL.STATE,GENERAL.CONNECTION device show eno1`: exit 0, `100 (connected)`,
  `Wired connection 1`, with no version-mismatch warning.
- Scoped documentation/link checks and `git diff --check` passed after recording the results.

Account key-only SSH and service persistence are verified on the rebooted Hermes host. This production
observation is distinct from the baseline disposable S3/S4 campaign, which remains unperformed.
Root-login configuration/rejection, live rollback/rerun acceptance and full apply cleanup remain unverified.
Next action: deliver the verified post-reboot account-access results; retain the outstanding broader
acceptance limitations and do not claim the entire original plan is closed.

### Authorized Git delivery

2026-09-12: user explicitly requested "commit push and merge fedora ssh key only changes".
Scope is this helper, companion guide, dedicated tests/checker and SSH execution evidence/record.
Unrelated router, Hermes lifecycle, README, contributor and hook changes remain outside this delivery.
Use an isolated feature worktree from current main so repository hooks cannot alter the unrelated work.

| ID | Dependency | Task progress | Validation status | Acceptance and method |
| --- | --- | --- | --- | --- |
| S15 | User Git authorization | ✅ COMPLETE | ✅ PASS | Exact isolated diff reviewed; 30 helper tests, 2 collector tests, shell/static/docs checks and pre-commit hook passed |
| S16 | S15 | ✅ COMPLETE | ✅ PASS | Commit 06fb688 pushed; PR #31 was clean, merged into main as 0ed86d6, and merged state verified |
| S17 | S16, user cleanup request | ✅ COMPLETE | ✅ PASS | Six Hermes testing artifacts removed; fresh key login verified after cleanup |

GitHub SSH fetch lacked a trusted host-key entry; use authenticated HTTPS through the existing gh
credential helper without changing repository remotes or disabling host verification.
Next action: populate isolated worktree with the scoped files and validate the exact proposed commit.

S15 validation in isolated worktree `/tmp/mikrotik-ssh-key-only`, based on fetched `origin/main`
`bb35bd2`:

- Exact staged delivery: 14 added files, 3,524 lines, limited to SSH helper, guide, behavior/doc tests,
  canonical execution record and preflight evidence. No unrelated dirty workspace files staged.
- `devbox run -- bash -n setup-ssh-key-only.sh`, `shellcheck`, and `shfmt -d -l -i 2 -ci -bn`:
  expected/actual exit 0.
- `devbox run -- python3 -m unittest discover -s tests -p test_ssh_key_only.py`:
  expected/actual 30 tests passed, 107.113 seconds.
- `devbox run -- python3 docs/plans/evidence/2026-09-12-hermes-ssh-preflight-test.py`:
  expected/actual two tests passed, 0.004 seconds.
- `devbox run -- python3 tests/check_ssh_key_only_docs.py` and `git diff --check`: exit 0.
- `devbox run -- lefthook run pre-commit`: all branch, secret, formatting, ShellCheck and Markdown lint
  checks passed. Markdown hook linted 24 maintained Markdown files with zero errors.

S16 delivery: commit `06fb688386dfb019f779783a1bbc4181fb6fc156`
`feat(ssh): add Fedora key-only setup helper` passed the Devbox pre-commit and commit-message hooks.
Required Devbox pre-push checks passed (RouterOS 115 tests, Nix guide 52 tests, Hermes guide 217 tests,
and 55 deployment specs). PR [#31](https://github.com/securexai/mikrotik/pull/31) had no required
status checks, `CLEAN` merge state and was merged at 2026-09-12 22:48:37 UTC into main as
`0ed86d60b1ad1e55e0608e7c43354f4ecae37e4f`.

S17 cleanup: at the user's request, removed these exact files from `/home/aicowork` on Hermes:
`setup-ssh-key-only.sh`, `setup-ssh-key-only.md`, `id_ed25519_cloudops.pub`,
`hermes-ssh-preflight.py`, `2026-09-12-hermes-ssh-preflight.py` and
`hermes-ssh-preflight.json`. Individual post-removal existence checks each returned exit 0; fresh
pinned key-based SSH login returned `aicowork`. The active authorized-keys file and system SSH/firewall
configuration were not removed or altered.

Next action: no further action under this Git delivery. The broader S3/S4 disposable-host acceptance
limitations remain historical and unperformed; do not treat S17 cleanup as validation of those gates.

Preparation and prior file delivery are complete; the overall plan remains open for S3/S4.
No password/root rejection, enforcing-SELinux application, or post-reboot login was tested.
No production operation, reboot, commit or push occurred. The original external helper remains unchanged.

Next action: provision a disposable Fedora Server with console access and execute the companion guide's
S3 acceptance checks using the recorded script identity. After S3 passes, explicitly schedule/authorize
the S4 test reboot and verify fresh key login. Do not treat offline passes as production certification.
