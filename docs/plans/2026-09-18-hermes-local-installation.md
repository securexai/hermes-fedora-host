# Hermes installation in the retained local VM

Record state: COMPLETE — installation, reboot and authenticated provider acceptance pass

## Approved baseline

The user requested Hermes installation, then approved expanding the retained VM
from 40 to 80 GiB and preparing its required filesystem and administrator account,
preserving the existing installation. Approval reference: the conversation's
`perform hermes installation` request and subsequent `yes` to that exact proposal.

Target: `lab-hermes-server`, UUID `5e5eae87-7a80-4214-bfaf-cb2363f2b330`,
pinned SSH at `lab@172.16.99.12`. Keep Secure Boot, enforcing SELinux, LUKS root,
the console unlock helper, lab isolation, disabled VM/network autostart and
unrelated workstation resources. No TPM migration, production operations,
production credentials, Telegram integration, commits or pushes are authorized.
The published fixture passphrase means this remains a disposable test environment.

Use the manual application's ordered M01/M02/M03 steps. The bare-metal TPM and
wall-power gates are inapplicable to the approved console-unlocked local VM;
validate its existing cold-start/reboot path instead. Provider authentication
requires a separately supplied disposable credential through a hidden local prompt.
Do all credential-free installation and validation first.

## Tasks and gates

| ID | Task and dependency | Progress | Required gate | Gate status |
| --- | --- | --- | --- | --- |
| I01 | Inspect and preserve recovery; none | DONE | Exact domain/disk identity, capacity and stopped-state backup verified | PASS |
| I02 | Expand storage; I01 | DONE | 80 GiB disk, unchanged root identity, dedicated XFS LV under existing LUKS at `/home/hermes`, fstab configured; boot proof belongs to I05 | PASS |
| I03 | Prepare accounts and runtime; I02 | DONE | Required admin, locked unprivileged runtime, subids, guarded user manager, rootless Podman | PASS |
| I04 | Deploy pinned application; I03 | DONE | M02 positive transport and negative trust checks; worker network isolation; M03 profile routing | PASS |
| I05 | Lifecycle and handoff; I04 | DONE | Reboot persistence, security posture, current guide and evidence; explicit credential-dependent limits | PASS |
| I06 | Disposable provider acceptance; I05 and local hidden credential input | DONE | Exact authenticated `HERMES_OK`, worker tool round trip and bounded credential-isolation checks | PASS |

## Evidence history

- Initial preflight: pinned SSH works; Fedora 44, Secure Boot enabled, SELinux enforcing,
  cgroup v2. Disk is 40 GiB; encrypted `vg_root` has 32.98 GiB root and 4 GiB swap,
  with zero free extents. `/home/hermes` and both application accounts are absent.
- Workstation image filesystem has 235 GiB free. `sudo -n` requires authentication;
  direct `virsh` through the desktop policy confirms the exact running domain.
- The prior installation turn corrected one printed SSH example to keep the two
  setup helpers identical. Rehearsal passed, all 217 guide checks passed, and shell
  syntax/whitespace checks passed. No guest change occurred during that turn.
- Existing unrelated worktree changes and the completed VM-creation record are preserved.
- I01/I02: desktop authentication succeeded. Orderly shutdown preceded the backup;
  `qemu-img compare` reported identical images. Recovery disk, its SHA-256 and
  original domain XML are root-only under
  `/var/lib/libvirt/images/hermes-local-recovery-20260918/` on the workstation.
  Disk metadata verified 40 GiB before and 80 GiB after expansion, without a backing file.
  Existing console unlock succeeded after restart.
- Guest partition 3, its same LUKS mapping and its PV were expanded. Created only
  the new `vg_root/hermes` LV (32 GiB, XFS); root and swap sizes and root UUID stayed
  unchanged. Eight GiB remains free in the VG. The new filesystem UUID is
  `fe7bd671-2203-4011-9523-b3b33c2d03b9`; it is mounted and recorded in fstab.
  `findmnt --verify` reported zero errors and the expected pre-reload systemd warning;
  daemon-reload subsequently completed. Guest metadata backups remain root-only in
  `/root/hermes-local-pre-expand-20260918`; the off-guest disk copy also retains the
  original partition, LUKS and LVM metadata.
- I03: signed Fedora package installation completed. Created `aicowork` (1001,
  wheel, existing fixture public key) and `hermes` (1002, nologin, no extra groups).
  Both passwords are locked; no production password was reused. `lab` remains
  the fixture's privileged operator; `aicowork` needs a locally set password for
  password-based sudo. Subuid/subgid ranges passed the 65,536-ID minimum.
  Rootless Podman reports cgroup v2, systemd, overlay and graphroot under the new
  mount. Lingering and the mount assertion guard are active. Persistent parent
  slice limits are 4 GiB high / 5 GiB maximum for this 8 GiB VM.
- Fresh rehearsal passed with zero failures/advisories; application script syntax
  passed before staging. M02 is running; its exit status alone will not be used
  as acceptance because the helper logs individual check return codes.
- I04 completed: M02 build/start/positive-command/SCP return codes were zero;
  missing and changed host keys both returned 255. Worker DNS and egress failed
  as required, with no network routes. Gateway UID 10000 can read its key and
  execute the shims; directory listing is intentionally denied by mode 0711.
  M03 resolved the profile backend to SSH and returned `HERMES_WORKER_ROUNDTRIP_OK`
  as `worker` on Fedora, with `RESULT=PASS`. The gateway remained active.
- Gateway digest: `sha256:9469b3e78b9545b6d576eb8887a95352e9a0ea83730eaf31431cf862ca1010e1`.
  Built worker ID: `0ef6770d77cfbc83ddcb06c1e11ca708d588447ce727370116341591f4a0440b`.
  Both containers are rootless, read-only, nonprivileged, without published ports,
  with no-new-privileges and 2 GiB individual limits. Worker network mode is none.
  Manual hardening passed explicit configuration assertions, preserving SSH routing.
  A fresh backend probe after hardening passed. SELinux remains enforcing,
  Secure Boot enabled, and fstab validation now has zero warnings/errors.
- Application evidence lives in `/home/aicowork/hermes-m02-deploy.out`,
  `hermes-m03-activate.out`, and `hermes-m03-configure.out` on the guest.
  No provider credential or messaging integration was provisioned. The bundled
  doctor reports missing authentication and upstream dependency/config warnings;
  it is not used as the transport acceptance test. M02/M03 reported no recent AVCs.
- I05 attempt: `pkexec /usr/bin/bash /tmp/hermes-local-reboot-host.sh` returned
  `Not authorized` before running the script. A separate watcher using normal
  libvirt user authorization exited with `detail=virsh-error exit-code=1`, without
  an attachment/ready marker. No reboot was issued. These are host authorization
  failures, not evidence of a guest boot failure or an application regression.
- Final live check at 2026-09-18 22:57:13 UTC: both units active, no published
  container ports, new XFS mount active, fstab verification clean, Secure Boot
  enabled and SELinux enforcing. Recent AVC search returned no matches. Only the
  previously recorded unsupported-CPU `mcelog.service` is failed. Current boot ID:
  `11976008-15bd-4fa3-9980-4ad1de466774`. This does not establish post-install reboot
  persistence. An initial status command had the wrong runtime working directory;
  using the documented `env --chdir=/home/hermes` resolved that diagnostic error.
- Scripts, M02/M03 logs and final-state evidence are retained in the dedicated
  workstation state directory's `installation/` subdirectory. Expansion scripts
  are one-time execution evidence, not rerun instructions. The console attachment
  failure is recorded in `installation-unlock-events.log` beside that directory.
- Updated the local lifecycle guide with installed state, access, recovery and
  remaining gates; linked this record from the original VM handoff and evidence ledger.
- Final repository checks: 217 guide checks passed; affected local links and
  whitespace passed; `git diff --check` and changed shell syntax passed.
  Markdownlint-cli2 0.23.2 reported no issues on isolated document copies with
  fixes disabled. The first sandboxed fetch failed DNS resolution; the host-side
  fetch succeeded. ShellCheck and shfmt remain unavailable, so no pass is claimed.
  No commit, push, production change or provider authentication occurred.

### Successful lifecycle continuation, 2026-09-18 UTC

- The user requested continuation. Desktop authorization succeeded on the retained
  reboot script; scoped firewall validation/application/readback completed before
  the watcher attached and the guest-initiated reboot was requested.
- Boot ID changed from `11976008-15bd-4fa3-9980-4ad1de466774` to
  `c1bd02f1-1cbe-4137-b409-d587787a3fc3`; pinned SSH returned. The script completed
  with `REBOOT_PASS`. Earlier authorization failures remain historical evidence.
- At 23:12:06 UTC, the independent postboot check confirmed the same root and Hermes
  filesystem UUIDs, clean fstab verification, Secure Boot enabled, SELinux enforcing,
  rootless Podman, both units automatically active and both containers running.
  Read-only roots, no-new-privileges, no published ports, 2 GiB individual limits
  and the worker's network isolation remained in effect.
- The actual Hermes SSH backend probe returned `HERMES_WORKER_ROUNDTRIP_OK` as
  `worker` on Fedora with `RESULT=PASS`. Hardening assertions passed. The current
  boot's AVC search returned no matches. Only the previously recorded unsupported
  CPU `mcelog.service` remains failed. Final marker: `POSTBOOT_ACCEPTANCE_PASS`.
- Sanitized evidence: workstation state `installation/postboot.log`. The postboot
  check and `validated-source-sha256` are retained alongside it; no console watcher
  remains active. Provider inference and Telegram were not exercised.
- Updated-document verification passed: 217 guide checks, affected local links,
  whitespace and `git diff --check`; isolated Markdown lint reported no issues.
  The local guide now includes the pinned SSH command for hidden credential input.

## Handoff

### Authorized provider continuation

After successful reboot acceptance, the user chose to enter a disposable OpenAI
API key locally. This authorizes the manual profile's provider setup and bounded
model-response test; it does not authorize production credentials or Telegram.
The user reported no key prompt and no error message. Read-only checks confirmed
SSH, the provisioning helper, runtime tools and private profile permissions.
The user's missing-prompt symptom was not reproduced as a script failure.
A separate Konsole window was launched with the existing hidden-input helper;
no terminal recording or credential capture was used. I06 awaits confirmation
that local provisioning completed before any authenticated acceptance is run.

The user subsequently reported successful local provisioning. I06 then verified
that a nonempty provider credential existed with private file permissions and ran
the two bounded manual-profile tests. Both received HTTP 401 (incorrect API key).
The CLI nevertheless returned zero; explicit output assertions correctly marked
acceptance failed. The model configuration and hardening steps passed, and all
five bounded credential-isolation checks passed. This does not establish valid
provider authentication. The failed log is preserved privately on the guest as
`/home/aicowork/hermes-m03-accept-attempt1.out`; only redacted error output was
returned during diagnosis. No credential value was copied into this record.

The gateway was restarted to reload the changed configuration. A new unrecorded
Konsole window was opened for hidden replacement-key entry. The user reported
replacement provisioning; the second bounded acceptance attempt passed:

- Runtime configuration confirmed `openai-api` / `gpt-5.6-luna`.
- Authenticated response was exactly `HERMES_OK`; both CLI commands exited zero.
- The agent tool response contained `HERMES_WORKER_TOOL_OK` and `Fedora release 44`.
- Model configuration, manual hardening and all five bounded credential-isolation
  checks passed (config, worker state, transport, worker metadata, worker logs).
- After restarting the gateway to load the profile, the 23:20:21 UTC final check
  passed the actual worker probe, configuration assertions, mount/security checks
  and both running containers. No AVCs appeared in the current boot. The existing
  `mcelog.service` limitation remains. No additional full VM reboot was performed
  after credential entry; I05's reboot proof precedes provider provisioning.
- Credential-free summaries are retained as workstation state
  `installation/auth-acceptance-summary.txt` and `installation/post-auth.log`.
  The test credential is retained in the guest's private profile for this test
  installation; no credential value was copied into Git or workstation evidence.

Hermes installation and credential-free reboot acceptance are complete. The VM
is retained running with both rootless application services active. Use the
[local guide](../HERMES_LOCAL_VM.md) for access, cold start, reboot and recovery.

All I01–I06 gates pass. There is no remaining installation blocker. The local guide
is the operating procedure; the initial failed authentication attempt remains
recorded above. Telegram, TPM migration, production promotion, an OS-wide update
and vulnerability remediation were not performed. The fixture still uses its
published LUKS value and is not suitable for production secrets.

### Memory-approval follow-up

The user's subsequent request to fix memory approval led to inspecting and testing
the exact installed image. The claimed undrainable queue did not reproduce:
interactive CLI and gateway slash handlers passed staging, approval/rejection and
fresh-process recall. Two bounded model calls in an isolated temporary profile
also reported pending state truthfully and recalled the exact codeword after
approval. No image or approval-policy change was needed, and the live queue was
untouched. Corrected the misleading current guidance, retained historical evidence,
and added a repeatable credential-free probe. The
[canonical memory procedure](../HERMES_MEMORY_APPROVAL.md) links the source hashes
and sanitized results. Telegram end-to-end memory interaction was untested at
that point; the subsequent operator test is recorded below.

### Telegram follow-up

The user subsequently authorized Telegram access and provisioned the bot token
through the existing hidden-input helper in an unrecorded local terminal. The
installed helper's SHA-256 matched the repository copy. The credential file is
mode `0600`, one numeric user ID is allowlisted, and allow-all is disabled.
Gateway restart succeeded; Telegram `getMe` accepted the token and the gateway
reported a connection. Both containers remained running with no published ports,
zero gateway service restarts, and no polling-conflict marker in the inspected logs.
The operator confirmed receiving the exact `HERMES_TELEGRAM_OK` reply from the
authorized account on 2026-09-18; the end-to-end message test passes based on that
operator observation. Other Telegram approval flows remain untested; the memory
approval and reboot tests are recorded below. No token was copied into Git
or chat. Current procedure: [Telegram access](../HERMES_LOCAL_VM.md#telegram-access).

The user authorized a single-account rejection test. The existing `m05-tests.sh`
helper matched the repository SHA-256; its allowlist swap saved the original ID.
A five-minute systemd restoration timer was armed before the swap. While the
gateway remained connected, the operator reported no reply after 30 seconds.
The inspected journal contained two lines mentioning unauthorized activity.
Manual restoration completed at 23:55:57 UTC: the original allowlist matched,
allow-all remained false, the saved-ID file was removed, both services were active,
and the gateway had a Telegram connection marker. The fallback timer was then
stopped. The operator subsequently confirmed that Hermes replied after access was
restored, completing the access-restriction test. This used the same account with
temporary exclusion rather than a second Telegram account.

### Telegram memory-approval acceptance

User-provided screenshots confirm the end-to-end memory workflow: a harmless
personal fact was staged, a new session did not recall it before approval, an
exact-ID `/memory approve` command returned `Approved 1 memory write(s).`, and a
subsequent `/new` session recalled the approved fact correctly. Personal content
and queue identifiers are omitted from this record. This verifies the Telegram
memory approval path; it does not establish other tool approval flows or reboot
persistence. The original codeword example triggered a model refusal to store
perceived credentials; the operator used a harmless personal fact instead.

### Telegram and memory reboot follow-up

The user authorized proceeding with the local VM reboot persistence check.
Scope is the existing fixture only, using the retained console-unlock helper;
no production changes or credential replacement are included.

- R01 PASS: run the existing host reboot helper; require pinned SSH to
  return with a changed boot ID and stop the console watcher afterward.
- R02 PASS: verify the dedicated mount, automatic gateway/worker startup,
  Telegram reconnection, restricted access configuration and approved-memory
  file persistence without printing personal content or credentials.
- R03 PASS: ask the operator to start a fresh Telegram session and confirm
  recall after reboot; update current guidance and run affected document checks.

Baseline captured: boot ID `c1bd02f1-1cbe-4137-b409-d587787a3fc3`, mount UUID
`fe7bd671-2203-4011-9523-b3b33c2d03b9`, and approved-memory file fingerprint
retained in the tool evidence without personal content. Desktop authentication
was approved, and the existing helper returned `REBOOT_PASS` with new boot ID
`cc51abc7-5c95-4353-a6cc-258ab4640096`. At 2026-09-19 00:07:41 UTC (September 18
local time), the mount UUID was unchanged, both services had started automatically,
both containers were running without published ports, and the approved-memory
file hash matched the baseline. The original Telegram allowlist was preserved,
allow-all stayed false, and this boot's gateway journal confirmed Telegram
connection without a polling-conflict marker.

The operator confirmed correct recall after `/new` in Telegram following the
reboot. The temporary console watcher was no longer running. All R01–R03 gates
pass; the reboot follow-up is complete. The Hermes guide suite passed all 217
checks and `git diff --check` passed. No further action is required for this
follow-up; other tool approval flows and production certification remain outside
this acceptance result.

### Automatic TPM unlock follow-up

The user explicitly requested automatic TPM-based disk unlocking for this local
VM. Use the existing manual-profile SHA256 PCR7 policy, preserving Fedora's boot
chain and passphrase slot. No production, signed-UKI migration, TPM clearing,
keyslot removal, VM autostart or OS-wide update is authorized by this change.

- T01 PASS: inspect the pinned LUKS identity, existing TPM device, Secure Boot,
  cryptenroll/plugin/dracut support. Slot 0 exists; no tokens were enrolled.
- T02 PASS: back up the LUKS header, crypttab and current initramfs off-host;
  add TPM enrollment, preserve/test slot 0, update only the matching crypttab
  record, rebuild and inspect the initramfs. Fail closed on duplicate enrollment.
- T03 PASS: reboot and cold-start without the console helper or key injection;
  require new boot IDs, TPM unlock evidence, active services and Telegram connection.
- T04 PASS: document routine boot/recovery and limitations, validate affected
  artifacts and record results. Preserve the existing recovery passphrase.

The guest has systemd 259.5, a TPM2 cryptsetup plugin, the dracut `tpm2-tss`
module and `/dev/tpmrm0`. Secure Boot is enabled. Separate package names
`systemd-cryptsetup` and `tpm2-tools` were absent. Enrollment binaries worked, but
the first dracut rebuild failed: the installed module explicitly requires `tpm2`.
Installed only `tpm2-tools-5.7-5.fc44` and dependency `tpm2-tss-fapi-4.1.3-9.fc44`.
The second rebuild passed. No reboot was attempted with the failed rebuild.

Enrollment added slot 1 and one systemd TPM2 token bound to SHA256 PCR7 without
a PIN. Slot 0 was retained and passphrase-tested before and after enrollment and
after cold boot. Token-only unlock also passed before and after boot. Crypttab
still has no keyfile; its matching record now includes `tpm2-device=auto`.
The rebuilt initramfs was inspected for that record, the `tpm2-tss` module and
the systemd TPM token plugin. The additive dracut configuration preserves module
inclusion on subsequent rebuilds. Future kernel updates were not exercised.

Recovery files are in guest `/root/hermes-local-tpm-recovery`, with private
pre/post-enrollment archives and one-time execution scripts retained off-host
under `$state/installation/tpm/`. The original one-time enrollment script records
the failed dependency attempt; do not rerun it over the existing token. The
existing general manual enrollment procedure remains authoritative for new hosts.

Observed no-input boot sequence:

| Boot | ID | Result |
| --- | --- | --- |
| Before enrollment | `cc51abc7-5c95-4353-a6cc-258ab4640096` | Baseline |
| TPM reboot | `ae2fc49c-c05f-46fc-a751-12a4282024a8` | PASS, no console helper/input |
| TPM cold start | `547adbf7-aa14-45c8-af4b-5419e1f0efe1` | PASS, powered-off state verified first |

Final checks at 2026-09-19 00:17:40 UTC (September 18 local time) passed:
unchanged dedicated mount UUID, Secure Boot enabled, SELinux enforcing,
both services automatically active, no container ports published, Telegram
connected this boot, original allowlist preserved, approved-memory hash unchanged,
and both TPM-only and recovery-slot unlock tests. No helper injected a key during
either boot. No new model conversation was sent during this acceptance run.

All T01–T04 gates pass. Guide suite: 217 passed. Manual clean-install rehearsal:
PASS, zero failures/advisories. Shell syntax and `git diff --check` passed.
Normal boots now use the TPM; the console helper is recovery-only. VM/network
autostart stays disabled. This is the manual PCR7 fixture profile, not signed-UKI
certification or protection against a host administrator controlling the vTPM.
