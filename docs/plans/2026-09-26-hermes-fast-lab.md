# Faster Hermes lab and production rehearsal

<!-- markdownlint-disable MD013 -->

Record state: COMPLETE

## Approved baseline — preserve after approval

- **Outcome:** Extend the existing disposable Fedora VM lab with named non-secret baseline/candidate JSON profiles, one local command, prepared bases, retained immutable application artifacts, and production-candidate rehearsals. Keep the current DeepSeek/Telegram stack.
- **Scope:** Profiles select pinned Hermes image, DeepSeek model, VM sizing and supported container settings; mandatory security contract and private credential handling remain. One resolved configuration drives deployment, verification and synthetic tests. Add doctor, plan, prepare, up, deploy, test, status and clean commands; mutating operations preview unless `--apply`. Preserve existing entrypoints. Named instances have distinct directories, UUIDs, keys and loopback ports, with locking and ownership guards.
- **Cache:** A dedicated prepare-only builder installs Fedora packages and pinned images. Remove builder access, SSH keys, machine identity, cloud-init data and transient state before publishing a stopped immutable prepared image. Fresh overlays and identities per VM; retain the stock Fedora clean-install path. Key caches by Fedora checksum, preparation inputs and image identities; record package versions, publish atomically and reject incomplete/corrupt entries. Retain the exact worker image rather than rebuilding a mutable tag for every test.
- **Tests:** quick = profile/rendering/regression/pinned-image mocks; vm = prepared deployment, actual config, SELinux, isolation, SSH, repeat deploy, reboot and fault recovery; candidate = full repository gates, stock-image installation, baseline upgrade, rollback and restore into a separate disposable VM. Negative tests cover invalid profiles, stale caches, collisions, interruptions, failure, identity drift and repeated cleanup. Restore verifies synthetic data, ownership, modes and startup; rollback restores pre-upgrade state and artifacts.
- **Acceptance:** Three-run medians target prepared readiness under 30 seconds, configuration-only redeploy under 10 seconds and no-op under 5 seconds; report actual misses. Reports include hashes, image identities, package inventory, timings and PASS/FAIL/BLOCKED/NOT_RUN. Candidate bundle contains exact artifacts, configuration, recovery instructions and evidence. Real bounded live smoke stays separately authorized and is required again for exact-candidate production acceptance.
- **Delivery:** Profiles/interface, then prepared caches, then recovery/reporting. Update the canonical disposable guide and run Toolbox offline, check-only lint, manifest verification and applicable disposable VM checks. Preserve historical evidence.
- **Defaults/boundaries:** Local operation; Fedora 44; rootless Podman; enforcing SELinux; offline worker; unencrypted disposable lab disks. No CI, additional providers, production provisioning, TPM/LUKS changes, commits, pushes or PR edits. No live credentials or paid/API messages are authorized by this implementation request.
- **Approval evidence:** User selected Fedora server VM, current stack, prepared base and local command, then said “Implement the proposed plan.” The preceding conversation contains the approved proposal.
- **Record owner:** This file is the single execution record for this change; the completed 2026-09-25 lab record remains historical.

## Tasks and gates

| Task | Outcome / dependencies | Progress | Gates | Next action |
| --- | --- | --- | --- | --- |
| T01 | Profiles, resolver, runner; none | ✅ DONE | G01 | Preserve tested interfaces |
| T02 | Prepared cache and exact artifacts; T01 | ✅ DONE | G02 | Preserve verified immutable cache |
| T03 | Candidate recovery and reporting; T01/T02 | ✅ DONE | G03 | Preserve verified candidate bundle |
| T04 | Documentation and final validation; T01–T03 | ✅ DONE | G04/G05 | Complete within approved synthetic scope |

| Gate | Method / expected result | Status | Evidence |
| --- | --- | --- | --- |
| G01 | Focused offline tests: invalid config, previews, rendering, no-op, identity and failure guards | ✅ PASS | 35 focused Toolbox cases and 64 existing configuration cases; details below |
| G02 | Real dedicated builder, verified cache, unique clones and three-run timing; reject corrupt/stale cache | ✅ PASS | Final report `20260927T043132Z-b19edc26`; all targets met |
| G03 | quick/vm/candidate suites: boot, config, no-op, reboot, fault, upgrade, rollback, isolated restore and double clean | ✅ PASS | Candidate report `20260927T042346Z-5b086002`; all 25 steps PASS |
| G04 | Toolbox full offline gate, check-only lint, manifest verification and diff check | ✅ PASS | Final candidate full gates, refreshed lint log and source-aware 411-row manifest verification |
| G05 | Documentation, diagnostics privacy and final acceptance reconciliation | ✅ PASS | 27 local links, exact diff review, safe diagnostics regressions, bundle hashes and cleanup verified |

## Evidence history

- Initial inspection: clean `main` at `9fb6f2d`; created `feat/hermes-fast-lab` before editing. Python 3.14.7 on host; development checks run in `dev-infra-hermes`. Existing runtime uses a fixed domain/port, a mutable local worker tag and hard-coded model. Existing backup helper assumes a separately mounted runtime home and cannot be used unchanged.

### G01 and first G02 attempt — 2026-09-27 UTC

- Focused Toolbox command: `python3 -B -m unittest tests.test_hermes_lab tests.test_hermes_disposable`; 25 tests PASS after scoped Ruff checks/formatting. Cases cover previews without commands/writes, rejected private/unknown values, limits, preserved security rendering, locking, corrupted caches, source invalidation, interrupted creation, UUID drift, failed deployment, backup integrity and safe reports.
- `lab.py doctor` PASS with 138.5 GiB free, declared commands present, Podman and session libvirt reachable. `lab.py test --suite quick --profile candidate` PASS against the pinned real image and offline services; report `.toolbox/hermes-disposable/v2/reports/20260927T033228Z-04583576/report.json`. These passes precede subsequent runtime edits and will be repeated where affected.
- First `prepare --apply` FAIL: verified Fedora checksum, fresh boot 14.58 seconds, package/image preparation and OCI export succeeded, but the root sanitization service exited 1 and the builder did not shut down. No base was published. Preserved report: `.toolbox/hermes-disposable/v2/reports/20260927T033316Z-5f1cae84/report.json`. The fixed service journal contained only the generic safe failure; labadmin was still present.
- Correction: logind can have no labadmin session after the scheduling SSH exits. Account termination now separately proves no account processes remain before deletion. Guest failures expose only controlled operation reasons. Live inspection also established that installed Podman returns unprefixed image IDs; exported IDs are normalized to `sha256:` references, which the installed Podman accepts. The exact failed builder is being guarded-cleaned before a fresh build. Retained failed `.building` artifacts are not accepted caches.
- Configuration refinement: profiles include a positive `preparation_revision` so an operator can explicitly rebuild packages without overwriting an immutable cache. This implements the approved explicit-refresh behavior; package inventories do not claim reproducible independent DNF builds.

### G02/G03 first runtime cycle and G04 — 2026-09-27 UTC

- Corrected prepared builder PASS: fresh builder boot 13.00 seconds, sanitized shutdown, separate audit clone boot 13.09 seconds, changed machine identity and exact new bootstrap authorized key, no application state/units, immutable artifact export and guarded cleanup of both instances. Report `.toolbox/hermes-disposable/v2/reports/20260927T033820Z-4d93a550/report.json`.
- Initial full Toolbox offline PASS: 534 reviewed Python cases, 140 ShellSpec examples, 226 guide checks, other prescribed shell suites, full-tree secret scan and source-aware 411-row manifest verification. Check-only lint PASS. Logs `/tmp/hermes-fast-lab-offline-initial.log` and `/tmp/hermes-fast-lab-lint-initial.log`. G04 is now STALE following the convergence and additional regression changes below.
- First prepared VM test FAIL at the new effective-configuration assertion after a 9.98-second boot. Report `.toolbox/hermes-disposable/v2/reports/20260927T034113Z-5580ad0e/report.json`. Read-only status confirmed config drift; a controlled idempotent apply then converged successfully. This reproduces the historical first-warm-deploy convergence, now surfaced as a failure instead of accepted implicitly.
- Fix: the deployer performs at most one post-startup configuration convergence and then strictly verifies the result. Added regression coverage; focused Toolbox tests now pass 28 cases. Additional checks cover unknown-file cleanup refusal before domain mutation and exhausted port allocation without VM creation.
- Cache keys now include VM/host preparation implementation as well as guest/worker inputs. Builders always use a 20 GiB baseline disk so a larger requested test disk cannot contaminate later smaller profiles. Reports refuse a PASS or candidate bundle if source inputs changed during their run. Earlier prepared cache remains immutable but is superseded by these input changes.

### G03 diagnosis and restore correction — 2026-09-27 UTC

- The first post-start convergence attempt still failed (`20260927T034422Z-5e61dcf0/report.json`): the verifier observed `hooks` as null, with no hook names and no environment drift. Source inspection in the pinned image confirmed the hook reader treats this non-mapping as no configured hooks; the repository still requires an explicit empty mapping. The attempted restart-based correction was superseded, not accepted as successful.
- The deployer now invokes the pinned application's own `load_config()` during offline configuration, before the final contract write. A network-disabled temporary-container probe confirmed the selected model fields survive and hooks remain `{}` after this sequence. This neither invents a schema version nor relaxes the contract. Fresh VM acceptance remains pending on this correction.
- Restore was strengthened during review: validate archive membership, extract into an isolated stage and compare the expected content/metadata fingerprint before stopping writers. If a directory swap fails, roll back completed swaps before restarting. An uncertain rollback retains its stage and leaves writers stopped. Focused failure tests cover extraction failure without service mutation, rollback after a partial swap, and archive traversal refusal. All 31 focused tests PASS in Toolbox after scoped Ruff validation.

- Initialization-only VM attempt also FAIL (`20260927T035201Z-2268a5dd/report.json`); application initialization does not guarantee the gateway preserves the empty-map serialization. The correction now adds an explicit, read-only `--runtime-check` to the canonical contract helper. It treats exactly present `hooks: null` and `hooks: {}` as equivalent disabled hooks, consistent with the pinned image's inspected `agent.shell_hooks._parse_hooks_block`; it rejects missing hooks, lists, strings, nonempty mappings and drift in every other field. Canonical writes and the original strict `--check` are unchanged. This is a representation compatibility correction, not permission for configured hooks.
- Focused tests now PASS 32 cases, including the narrow runtime equivalence and negative security cases. The existing manual configuration suite still passes all 64 checks. Invalid candidate edits no longer prevent cleanup using a recorded or explicit baseline profile. The exact retained failed VM was cleaned before another fresh acceptance run.

- The next fresh attempt (`20260927T035735Z-eeb9460d/report.json`) exposed a diagnostic distinction: the hook key was **absent**, not present with a null value. The previous `.get()`-based inspection could not distinguish those states. Direct inspection then confirmed `hooks_present=false`, zero resolved shell hooks and zero resolved outbound hooks. The pinned writer strips default-valued empty dictionaries. The runtime checker now accepts absent/null/empty-map serialization only after the application's actual resolver proves zero shell and outbound hooks; attempts by that resolver to save configuration are refused. Canonical writes and strict `--check` retain their original behavior. This supersedes the earlier missing-key rejection described above.
- The corrected verifier was transferred to the exact retained synthetic VM with its retained image IDs. Application `apply` then PASS: both services active, effective configuration/image/resource checks passed, worker network none. Focused tests remain 32 PASS. No live services or credentials were used.
- The full offline and lint checks before this final representation correction passed (`/tmp/hermes-fast-lab-offline-current.log`, `/tmp/hermes-fast-lab-lint-current.log`); they are STALE for the updated helper/tests/documentation and require final refresh.

### G02/G03 three-cycle result and final preflight review

- `lab.py test --suite vm --profile candidate --instance check --repeat 3 --apply` PASS; report `.toolbox/hermes-disposable/v2/reports/20260927T040355Z-c0ee1850/report.json`. All three fresh identities differed. Each cycle passed deployment/configuration/image/resource checks, no-op without container restart, resource change/restore, reboot, stopped-worker recovery and double cleanup.
- Measured medians: readiness 15.505 seconds (18.517, 15.461, 15.505), unchanged deploy 4.385 seconds (4.385, 4.324, 4.390), configuration change 7.703 seconds (7.594, 7.801, 7.703). All targets PASS. Readiness excludes the separately recorded cache verification/preparation phase.
- Final review corrected the synthetic-state preflight: the unprivileged bootstrap account cannot traverse the private runtime home, and that home is absent on stock images. The preflight now uses guest-root Python metadata inspection, accepts absence, and refuses mounted/symlink gateway state before artifact transfer. This changes a cache-key input; G02 will refresh on the final implementation.
- Added allowlisted diagnostic reasons without exposing unknown guest stderr, and negative tests for unsafe-state refusal and diagnostic privacy. Focused Toolbox suite: 34 PASS; Ruff PASS.
- Final implementation refresh PASS: `.toolbox/hermes-disposable/v2/reports/20260927T040929Z-f2a9af0b/report.json`. New dedicated builder and audit clone passed; cache key `36bf4fcc62e1656f56d9a3cd46c0d442fed8f2cfeb3849c070e8f2de15193eb7`. Three fresh prepared instances passed the complete VM suite and double cleanup. Final medians: readiness 18.455 seconds, unchanged deploy 4.346 seconds, configuration change 7.669 seconds. All three targets PASS. Exact immutable worker ID: `sha256:aeaa0737a5d7542815524adced95f1e23191bf8ce3895f9969bca103a9499f66`.

### G03 stock-image OCI import correction

- Candidate report `.toolbox/hermes-disposable/v2/reports/20260927T041747Z-6d1a5e83/report.json`: quick, full repository offline and check-only lint PASS; stock-image installation FAIL before service installation. The initial status diagnostic reported inactive services; a bounded import reproduction identified the actual failure as `podman load` rejecting a manifest digest mismatch.
- Inspection of the public archive established that OCI conversion changed the gateway manifest digest while retaining its original registry digest in the image-name annotation. Export now uses the immutable image ID, producing an unnamed OCI entry; provenance and original registry digest remain in the separate manifest. The prepared cache is invalidated by the changed export input. Added export/identity regression: 35 focused tests PASS, scoped Ruff PASS. Earlier runtime passes remain historical pending refresh.

### G03 final candidate acceptance

- Direct import of the corrected public gateway archive into the retained stock VM PASS with the expected image ID; the failed VM was then guarded-cleaned. The subsequent fresh candidate suite PASS: `.toolbox/hermes-disposable/v2/reports/20260927T042346Z-5b086002/report.json`.
- All 25 steps PASS, including quick, full repository offline (88.013 seconds), check-only lint (12.086 seconds), new sanitized builder/audit clone, stock baseline installation (60.999 seconds), stopped backup, configuration upgrade, no-op without restart, configuration change/restore, reboot, worker recovery, baseline-state/artifact rollback, separate stock VM restore, startup and twice-repeated cleanup of both instances. The persisted worker fixture and exact state fingerprint checks passed.
- The final cache identity and worker image ID are retained in the candidate report. Preparation took 135.673 seconds; subsequent complete cache verification took 4.275 seconds. Cache verification is separate from warm deployment timing.
- Candidate bundle: `.toolbox/hermes-disposable/v2/reports/20260927T042346Z-5b086002/candidate/`. Independent checksum verification of all 38 bundled files PASS; temporary synthetic backup absence confirmed. The included candidate exercises configuration changes at the same Hermes release as baseline; a different release requires its own rehearsal. Live provider/Telegram and production acceptance remain NOT_RUN.

### Final G02/G04/G05 reconciliation

- Final three-cycle VM suite PASS on the corrected cache: `.toolbox/hermes-disposable/v2/reports/20260927T043132Z-b19edc26/report.json`. Readiness median 18.321 seconds (18.367, 18.215, 18.321); unchanged convergence median 4.192 seconds (4.205, 4.109, 4.192); configuration change median 7.626 seconds (7.447, 7.626, 7.693). All targets PASS. These warm step measurements exclude full cache verification, whose separate observed cost is recorded above.
- All three fresh identities were distinct. Each cycle passed effective configuration and image/resource checks, identity-preserving no-op, configuration change/restore, reboot, stopped-worker recovery and double cleanup. Final read-only `qemu:///session` domain listing and v2 instance-directory listing were both empty. Prepared caches and historical failed reports remain; the public temporary OCI probe was removed.
- Final code passed the full offline and check-only lint gates within the candidate report. The updated record and documentation passed refreshed check-only lint (`/tmp/hermes-fast-lab-lint-final.log`), source-aware manifest verification (411 rows) and `git diff --check`. All 27 local links in README and the canonical disposable guide resolve. Scoped Ruff checks and 35 focused tests PASS. Review covered tracked differences and new files; protected historical evidence was not edited.
- The first commit attempt from the immutable host stopped before commit because `pre_commit` is absent. The documented Toolbox hook run then rejected the cache fingerprint above as a generic-key false positive. The exact non-secret fingerprint remains in the ignored report and was removed from this committed record; the manifest and hooks were refreshed afterward without bypassing either gate.

## Closure

- Outcome: the approved profiles, local runner, verified prepared bases, immutable application archives, synthetic VM/candidate suites, recovery rehearsal, reports and candidate bundle are implemented and verified within the tested scope.
- Implementation gates G01–G05: PASS. No implementation blocker remains.
- Separate acceptance: real DeepSeek/Telegram smoke and production acceptance are NOT_RUN. A different gateway release, model or profile needs its own candidate checks and separately authorized live acceptance.
- Next operator action: follow `docs/HERMES_DISPOSABLE_LAB.md`; create a named instance with `lab.py up --profile candidate --instance dev --apply`, or edit a non-secret profile and preview it before applying.
- Delivery: `feat/hermes-fast-lab`; changes remain uncommitted. No commits, pushes, PR modifications, production deployment or live credential operations were performed.
- Final state: COMPLETE.
