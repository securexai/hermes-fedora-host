# Hermes manual-profile contract

**Applies to:** the manual profile — a pinned upstream gateway container and an offline Fedora
worker container, run rootless under an unprivileged runtime account on Fedora Server 44.
**Record state:** source-level contract, offline-validated. **No runtime verification has been
performed for this document.** Every claim below is grounded in inspected repository artifacts or in
the pinned release's own source, and is labelled accordingly.

**Authority and supersession.** This document is the current contract for the manual profile. Where
it disagrees with an older description, this document wins for *current* behaviour:

| Older statement | Status | Why |
| --- | --- | --- |
| "`terminal.ssh_host` (and the other `terminal.ssh_*` keys) are not recognized config keys; the Quadlet `TERMINAL_*` environment is authoritative." — [B6 handoff](HERMES_B6_CLEAN_INSTALL_HANDOFF.md) §4 | **Superseded.** | The pinned release maps every `terminal.<key>` to `TERMINAL_<KEY>` in `hermes_cli/config.py`, and while a profile scope is bound `tools/terminal_scope.py` resolves `TERMINAL_*` **only** from the profile's `.env` and `config.yaml`. Profile configuration is therefore authoritative for the gateway; the Quadlet environment covers unscoped CLI runs and must stay consistent. |
| "`scripts/hermes/manual/` and the guides remain untracked in Git." — B6 handoff §8 item 12 | **Superseded.** | The artifacts are tracked; `git ls-files` lists them. |
| "Review and apply: `m02`…`m05` as documented" | **Amended.** | Mutating helpers are inspect-only by default and require `--apply`; see *Failure semantics*. |
| Boot helpers staged to `~/hermes-boot` | **Amended.** | The whole `scripts/hermes/manual/` tree is staged once; the boot helpers source the shared library one level up. |

Historical records ([the manual handoff](HERMES_MANUAL_HANDOFF.md), [the B6 handoff](HERMES_B6_CLEAN_INSTALL_HANDOFF.md),
[the change ledger](plans/evidence/2026-09-14-hermes-b6-change-ledger.md)) are evidence of what was
done on particular dates. They are not current runbooks.

## 1. Support matrix

| Layer | Supported | Not claimed |
| --- | --- | --- |
| Application host | Fedora Linux 44 (Server Edition), x86-64, cgroup v2, SELinux Enforcing, rootless Podman 5.8.x, systemd 259.x | Other Fedora releases, ARM, cgroup v1, SELinux disabled or permissive |
| Storage | Dedicated XFS `/home/hermes` filesystem on LUKS-encrypted storage | NFS/SMB homes, `virtiofs`, shared or unsupported filesystems |
| Accounts | A locked, non-login unprivileged runtime account (`hermes`) with ≥65,536 subordinate IDs; an administrator account whose name is **configurable** (`HERMES_ADMIN`) | System-UID runtime accounts; a fixed administrator name |
| Capability scope | CLI and Telegram **text** conversations; terminal and file work executed in the offline worker; approval-gated memory | Browser, computer-use, code execution, scheduling, delegation, external messaging/integrations, media tools |
| Lab hypervisor (for validation) | The virtualization repository's Fedora 44 Kinoite NAT profile, x86-64 | Any claim that Kinoite is the application target |
| Optional no-input boot | UEFI Secure Boot on, working TPM2/SHA-256 PCR7, console recovery, verified firmware AC-restoration behaviour | VM-only certification of hardware boot; protection against theft of an intact powered-off server |

"Works on any server" is not a claim this profile makes. A different host, firmware revision or
filesystem can invalidate the boot half without touching the application half.

## 2. Configuration precedence

Three different subsystems read configuration, and conflating them is the single most common source
of "it worked in the CLI and not in Telegram" confusion.

| Subsystem | Authoritative source | Notes |
| --- | --- | --- |
| Terminal backend, while a profile scope is bound (gateway, dashboard, cron, Telegram) | Profile `config.yaml` `terminal:` and profile `.env` `TERMINAL_*` | `tools/terminal_scope.py` resolves **only** from these; a missing key takes a defined default, never the ambient environment. A malformed profile fails closed. |
| Terminal backend for unscoped one-shot CLI runs | Quadlet `Environment=TERMINAL_*` | Convenience only. Must stay consistent with the profile. |
| Gateway platforms, allowlists, toolsets | Profile `config.yaml` (`platform_toolsets`, `gateway.platforms`) and profile `.env` credentials | Environment credentials never override an explicit `enabled: false`. |

`profile-contract.yaml` is the single reviewed source of truth for the narrow posture. It is consumed
by `config/harden-config.py` and asserted by `tests/test-hermes-manual-profile.sh`, so a posture change
is one reviewed edit with one justification instead of three drifting copies.

**Replacement semantics for security-controlled collections.** A recursive merge only replaces scalars
and lists; an empty-mapping patch such as `hooks: {}` would merge into an existing mapping and leave
every pre-existing hook, MCP server, plugin or toolset in force while the run reported success. The
contract therefore names those paths in a `replace:` list (`hooks`, `mcp_servers`, `plugins`,
`toolsets`, `platform_toolsets`, `approvals`, `security`, `skills.external_dirs`,
`skills.trusted_project_dirs`), and the helper deletes each path from the existing configuration before
merging, so the resulting subtree equals the contract exactly — no extra operator control survives in a
security-controlled namespace. Genuinely unrelated keys (for example `agent.custom_operator_key`) are
still preserved. `config/verify-contract.py` independently re-checks every replaced subtree for exact
equality and requires the empty collections to be empty, so a populated integration is a FAIL rather
than a silently preserved one.

The helper is **convergent**: a re-run that changes nothing writes nothing, creates no backup and does
not touch the file's hash, mode or owner. An explicit `--upgrade` is the only path that re-writes and
backs up an already-converged profile. `--check` verifies **both** the configuration and the `.env`
allowlist policy without writing either, which is the credential-free verification path
`m03-contract.sh` uses in Gate 2. A fresh file is created at mode 0600 owned by the applying process
(the container's mapped UID 10000); an existing valid owner is preserved where the process may set it.

The contract deliberately does **not** set `_config_version`: the pinned release refuses to
auto-migrate an explicit version below its support floor, and asserting a schema version this
procedure cannot substantiate would be a compatibility claim it has not earned. An existing
`_config_version` is preserved untouched.

## 3. Tool allowlist

`toolsets` (global) and `platform_toolsets.cli` / `platform_toolsets.telegram` are set to
`terminal`, `file`, `memory`, `clarify`. These are the pinned release's real keys; an earlier draft of
the contract used a friendlier `tools:` wrapper, which the merge step would have written verbatim and
never translated, leaving the broad default allowlist in force. The broad `hermes-cli` composite
is **not** used: in the pinned release it is a bundle of every core tool, including browser
automation, code execution, computer-use, task delegation, scheduling and Home Assistant tools.
Declaring the narrow list is what makes the documented capability scope true rather than
aspirational.

Setting the list is necessary but may not be sufficient: tools also carry runtime capability gates.
The resolved registry must be inspected on the running image before acceptance, and that check is
recorded as unverified until it runs.

## 4. Trust and transport

- The worker has no route at all (`Network=none`). The only transport is a Unix socket in a minimal
  shared directory; the worker runs `socat` feeding `sshd -i` (inetd mode), never a TCP listener.
- The worker SSH host key lives in a persistent worker-only directory, so rebuilding the image cannot
  silently change the identity the gateway pins.
- `gateway/ssh`, `gateway/scp` and `gateway/sftp` are bind-mounted over the image's `bin` directory,
  which is first on `PATH`. OpenSSH uses the **first** obtained option value, so the shim's
  `StrictHostKeyChecking=yes`, `UserKnownHostsFile`, `GlobalKnownHostsFile=/dev/null`,
  `IdentityFile` and `IdentitiesOnly=yes` defeat the backend's own `-o StrictHostKeyChecking=accept-new`.
- **Trust pins are never silently replaced.** `m02` verifies an existing `known_hosts` against the
  persistent host key and stops if they disagree. Rotating trust is a deliberate operation.
- **Negative tests never touch live material.** They run against a disposable copy of the client
  directory, so the live `:Z`-labelled pin is not edited or relabelled. `HERMES_GATEWAY_SSH_DIR`
  exists so any disposable consumer can be pointed at a copy; the default is unchanged.
- The worker `sshd` sets no `AcceptEnv`, so the SSH channel carries no client environment. This is
  **not** the whole story: the pinned SSH backend also synchronizes registered credential files,
  skills and caches for the profile. Those paths are covered by synthetic-canary tests, not by the
  absence of `AcceptEnv`.

## 5. Credential flow

- Provider and bot credentials live only in the profile `.env` (mode 0600) on encrypted storage, and
  one off-host archive. `config.yaml` never holds a secret.
- Provisioning reads secrets from `/dev/tty` without echo and pipes them over stdin into a one-shot
  networkless container; the value never enters `argv`, a command line, a log or shell history.
- Writes merge: unrelated `.env` entries are preserved, and the file is replaced atomically. A
  read failure aborts instead of appending to a truncated file.
- The worker deliberately never receives provider credentials. It is not an OS trust boundary from
  the gateway: both containers share the host kernel and the runtime account's user namespace.
  **Worker output can return through the gateway to the provider** — offline worker networking does
  not prevent disclosure.
- Redaction is done by the tracked `redact-stream.py` helper. Short values are left alone so log
  noise is not mangled.

## 6. Failure semantics

| Mechanism | Behaviour |
| --- | --- |
| `mp_check <name> PASS\|FAIL\|UNVERIFIED\|NOT_APPLICABLE` | Emits one machine-readable line. Checks are tallied from the log, so they survive the subshell created by a `tee` pipeline. |
| `mp_info <name> <detail>` | Informational diagnostic. Printed for the operator but not a `CHECK` line, so it is never counted as a PASS or a failure. |
| `mp_defer <name> <reason>` | A required check owned by a LATER gate that this run is not authorized or able to perform. Reported separately; makes the result explicitly partial; never a PASS and never a block for a gate defined to exclude it. |
| `mp_finalize <log> <rc>` | Exit 0 only when the pipeline succeeded, at least one check ran, and no check FAILed. Any `UNVERIFIED` yields exit 3 and `RESULT=INCOMPLETE`. A run with only deferred checks yields `RESULT=PASS (PARTIAL: n deferred)` and exit 0. A run that asserts nothing is a failure. |
| `mp_parse_mode` / `mp_require_apply` | Mutating helpers are **inspect-only by default** and require `--apply`. An unrecognized option fails closed, so a typo can never be graded as inspect-only. |
| `mp_require_host_identity` | Host-mutating helpers require `HERMES_EXPECT_MACHINE_ID_SHA256` to match the reviewed host. Unset or mismatched refuses. |
| `mp_lock_profile` | One operation per profile at a time, shared by **every** mutating helper including credential and configuration operations; a second writer (of any helper) is refused rather than interleaved. |
| `mp_secure_tmpdir_var` / `mp_on_cleanup` | Private directories and restoration hooks are registered in the calling shell and run on EXIT, INT and TERM. A TERM trap preserves the primary status and reports restoration failures. SIGKILL cannot be trapped — a killed run can leave its private 0700 directory behind. |
| Service-state restoration | Helpers that stop the gateway or worker record the prior state before the reporting pipeline and restore it through a trap hook, so an early failure, an INT or a TERM does not leave the host half-changed. |
| `mp_audit_avc_check` | One interpretation of `ausearch`: a clean readable log (`<no matches>`, which exits non-zero) is a PASS, actual denials are a FAIL, a missing tool or unreadable log is UNVERIFIED. |
| Boot helpers | Keep their own `RESULT=`/`ENROLLMENT_VERDICT=`/`FALLBACK_PROOF=` contract with `pipefail` and an explicit rc capture, because the runbook and the rehearsal validate those markers. |

Corrected defects, all previously recorded rather than newly discovered:

- **Predictable root-owned temporary helpers.** The B6 baseline already recorded nine sites where a
  fixed `/tmp/*.py` redactor was written and executed as root while reading the credential file, and
  `tpm-enroll.sh` rewrote `/etc/crypttab` through `/tmp/crypttab.new`. All are removed; redaction is a
  tracked helper and the crypttab rewrite stays inside the root-only recovery directory.
- **Verification that could not fail.** Several helpers printed return codes and then exited 0 through
  `tee`. Every manual helper now either reports through `mp_finalize` or keeps an explicit
  verdict-and-exit path.
- **Silent trust rotation.** `m02` rewrote the pinned `known_hosts` on every run and temporarily edited
  the live pin to test negative cases. It now verifies-and-stops, and tests a copy.

## 7. Maintenance cost and usability impact

| Control | Cost to maintain | Cost to use | Why it is worth it here |
| --- | --- | --- | --- |
| Digest-pinned gateway; retained worker OCI archive | Rebuild and re-pin on every release and base update | Slightly slower updates; no automatic upgrade | Removes "the tag moved" drift. **Pinning without patch maintenance is not security** — it postpones updates, so the release cadence has to exist. |
| Owner-only worker client authorization at runtime (not baked into the image) | One extra mount and mode/ownership check | None | Rebuilding the worker no longer rotates the authorized key. |
| Read-only image roots, `no-new-privileges`, default seccomp, resource limits | Low; re-verify after image or Quadlet changes | Large jobs hit limits and must be sized deliberately | Real containment for a compromised tool process; no per-run operator cost. |
| Narrow tool allowlist and manual approvals | Keep the list in one contract file; re-check resolved tools after upgrades | Fewer capabilities; dangerous commands and memory writes need a human | The documented scope becomes true. Cost is paid once per upgrade, not per task. |
| Inspect-by-default with `--apply` and host binding | Every documented command gains one flag | One extra keystroke; prevents accidental mutation | Makes "I only meant to look" a real category. |
| `CHECK` accounting that fails on `UNVERIFIED` | Slightly noisier output | A non-critical check can force a re-run | Removes "green run, unmeasured system". |
| Trust-pin verification on re-run | Must follow the documented rotation procedure | A rebuild after a host-key change stops | Prevents silently accepting a substituted worker identity. |
| Stopped-state backup plus isolated restore test | Storage plus a short maintenance interruption | Periodic restore exercises | The only evidence that the backup is usable. |
| Optional PCR7 auto-unlock | Firmware/TPM state to maintain; supervised re-enrollment after firmware change | Helps recovery, **reduces** physical-theft protection: an intact stolen server boots itself | Opt-in per target with explicit acceptance of that trade. |

Deliberately **not** added in this iteration: a custom SELinux policy, a secrets broker, Kubernetes,
signed-UKI/PCR11 machinery, or an egress allowlist for the gateway. Each would add standing
maintenance without removing a demonstrated failure mode of this profile. The gateway's egress is
broader than provider-only access; that residual risk is recorded rather than papered over with an
unmaintainable domain list.

## 8. Standing limitations

- A stolen, intact, powered-off server boots itself when PCR7 auto-unlock is enrolled; credentials are
  on that volume. `/boot` is unencrypted and unmeasured, so a tampered initramfs could harvest the key.
- Fedora's GRUB permits editing a boot entry, so `rd.break` yields root on the already-unlocked volume.
- The worker is not a security boundary against the gateway: a gateway compromise can drive the worker.
- Rootless containers share the host kernel; this is not VM-grade isolation.
- Only terminal, file, memory and clarify paths are in scope. Everything else is unverified by choice.
- The offline worker prevents the *worker* from reaching the network. It does not prevent the agent
  from asking the gateway to reach the network.
- No runtime, lab, credential or production evidence is attached to this contract. The offline suite
  proves the artifacts encode this posture; it does not prove the posture holds at runtime.
- The Gate 2 lab fixture `lab-hermes-manual-r1` runs the **reduced, unencrypted** variant (deviation
  D-01). The encrypted-storage row of the support matrix is therefore **not exercised** there, and any
  claim about LUKS2, credentials at rest on encrypted storage, or TPM/PCR7 unlock remains unverified.
  The guest host key was pinned by TOFU and its console verification is still outstanding (D-04).

## 9. Verification

```bash
./tests/test-hermes-manual-profile.sh -v
```

This suite is offline: it requires no root, starts no container, contacts no target and reads no
credential store. It validates syntax, the shared library's behaviour (including that `UNVERIFIED`
never passes and that a concurrent writer is refused), temporary-file discipline, failure propagation,
mutation gating, the configuration contract, release identity, transport trust policy and
documentation parity.

Runtime claims still require the separately authorized lab gates described in
[the execution record](plans/2026-09-20-hermes-manual-profile-improvement.md).
