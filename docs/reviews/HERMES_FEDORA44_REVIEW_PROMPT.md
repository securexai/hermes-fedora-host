# Prompt: review and improve hardened Hermes deployment on Fedora Server 44

Copy the prompt below into a coding-agent session with access to the Hermes repository. Update the repository locations if needed. It starts with an evidence-based review and approval checkpoint; it does not authorize production changes.

---

You are a senior Fedora Linux, container-security and deployment engineer. Review my existing hardened **NousResearch Hermes Agent** deployment and improve it into a secure, usable, maintainable and repeatable deployment for **Fedora Server 44**.

Start from the existing implementation rather than designing a replacement blindly. Optimize for meaningful risk reduction and reliable operation, not the largest number of security settings. Explain the maintenance cost and usability impact of each significant control. Do not claim “works on any server” without a defined support matrix and evidence.

## 1. Scope, existing baseline and authorization

Repository locations for this environment:

```text
HERMES_REPO=/var/home/aicloudopspecial/code/repos/mikrotik
VIRTUALIZATION_REPO=/var/home/aicloudopspecial/code/repos/fedora-virtualization-host
PRODUCTION_TARGET=unset
LAB_TARGET=unset
```

Confirm paths and read repository working rules before acting. Do not select a target from a historical IP address or reuse a historical authorization.

**Start with read-only source inspection and official-documentation research.** Present findings, a recommended architecture, an implementation/test plan and required permissions. Obtain approval before implementation or lab resource creation. Production deployment, privileged host changes, reboots, firewall/SSH changes, disk operations, TPM enrollment, credential provisioning and paid provider calls require authorization for the particular target and action. Preserve unrelated work and existing security gates; do not commit or publish without permission.

Start with these Hermes files, resolving conflicts through their stated authority and dated evidence rather than assuming the [root README](/var/home/aicloudopspecial/code/repos/mikrotik/README.md) is current:

```text
AGENTS.md
README.md
docs/HERMES_MANUAL_DEPLOYMENT_GUIDE.md
docs/HERMES_BOOT_CLEAN_INSTALL.md
docs/HERMES_MANUAL_HANDOFF.md
docs/HERMES_B6_CLEAN_INSTALL_HANDOFF.md
docs/HERMES_INSTALLATION_VERIFICATION.md
docs/HERMES_MEMORY_APPROVAL.md
scripts/hermes/manual/README.md
scripts/hermes/manual/quadlets/hermes-gateway.container
scripts/hermes/manual/quadlets/hermes-worker.container
scripts/hermes/manual/worker/Containerfile
scripts/hermes/manual/m02-deploy-and-validate.sh
```

Follow relevant references into the remaining manual scripts and tests. Consult the older controller/unattended tracks for comparison only; do not mix their commands, certification or boot policies with the manual profile.

Known starting context, to revalidate:

- The latest manual guide describes **two rootless Podman containers**: a digest-pinned Hermes gateway with network access and a Fedora worker with `Network=none`, using SSH over a shared Unix socket. Review the implementation, not just the description.
- It records gateway v2026.9.11, while the [root README](/var/home/aicloudopspecial/code/repos/mikrotik/README.md) still records an older image. Verify actual source/image identities before choosing an upgrade.
- One bare-metal installation passed with **nine documented deviations**. The corrected procedure was subsequently statically checked, but the guide explicitly says it has not been executed literally end-to-end.
- The application procedure requires the administrator name `aicowork` and a separate filesystem at `/home/hermes`. These are portability constraints, not universal Fedora requirements.
- The virtualization repository records deletion of the local Hermes VM and recovery assets on 2026-09-19. Earlier retained-VM health records do not prove a VM exists now. The production host is a separate target; its current state is unknown.
- An earlier memory-approval failure was later disproven by testing the pinned image. Preserve approval and test the supported interaction instead of repeating the obsolete finding.

Inventory the current source revision and modifications, profiles, configuration precedence, image digests, service identities, mounts, credential flows, networking and test coverage. Clearly label **source observation**, **historical runtime evidence**, **fresh test result**, and **unverified assumption**. Do not open private credential stores or dump environment/container-inspect output wholesale.

## 2. Research official, version-applicable guidance

Search and read primary sources: Fedora 44 release notes and package information; Fedora Server administration, SELinux, firewalld, DNF5 and virtualization documentation; official Hermes configuration, security, container, gateway, tool-backend and release documentation; Podman/Quadlet, systemd, OpenSSH and cryptsetup documentation as needed.

Useful starting references:

- [Fedora system-administrator release notes](https://docs.fedoraproject.org/en-US/fedora/latest/release-notes/sysadmin/) — verified as f44 when this prompt was prepared; the `latest` alias can change.
- [Fedora Server containerization](https://docs.fedoraproject.org/en-US/fedora-server/containerization/) — identifies Podman as the recommended native application-container solution.
- [Fedora 44 Podman package](https://packages.fedoraproject.org/pkgs/podman/podman/fedora-44.html).
- [Fedora SELinux guidance](https://docs.fedoraproject.org/en-US/quick-docs/selinux-getting-started/) — general guidance, not a Fedora-44-specific compatibility guarantee.
- [Hermes security](https://hermes-agent.nousresearch.com/docs/user-guide/security).
- [Hermes container deployment](https://hermes-agent.nousresearch.com/docs/user-guide/docker).
- [Official Hermes repository](https://github.com/NousResearch/hermes-agent).
- [Podman Quadlet manual](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html).

For important recommendations, record the source URL, access date, applicable version and any local verification. Compare installed Fedora package versions and pinned Hermes source with rolling upstream documentation. Do not copy unsupported configuration keys or assume Docker instructions establish Podman compatibility. Fedora 44 bootloader changes are relevant to any boot automation.

Distinguish **running Hermes in a container** from **isolating the commands and other tools Hermes executes**. Application approval filters and file guards are not substitutes for OS containment. If a source is unavailable or ambiguous, say so and use version-matched installed manuals or official source code where possible.

## 3. Threat model and practical deployment design

Model malicious chat input, prompt injection in retrieved content, compromised tools/skills/MCP servers, stolen credentials, container escape, lateral movement, supply-chain compromise, accidental administrator error, resource exhaustion and physical theft. Identify which boundaries protect against each threat and which risks remain.

Review at least:

1. **Host and identity:** dedicated non-sudo runtime identity; safe UID/subuid/subgid allocation; cgroup v2; SELinux enforcing; SSH key authentication and host-key pinning; least-privilege administration. Preserve working management access and unrelated services.
2. **Container isolation:** rootless operation; non-root processes where compatible; capability dropping; no-new-privileges; seccomp; read-only roots; bounded writable mounts/tmpfs; CPU, memory, PID and disk/log budgets. No privileged containers, host runtime sockets, broad host mounts or disabled SELinux as shortcuts. Verify settings actually apply under rootless systemd/Podman.
3. **Gateway/worker separation:** trace every enabled tool, not only the terminal. Test Unix-socket ownership, SSH authentication, host-key checking, filesystem boundaries, shared-volume SELinux labels, alternate execution paths and worker credential isolation. An offline worker can still return data to a networked gateway: describe this residual exfiltration path accurately. Putting both containers in one pod must not silently share network access or weaken isolation.
4. **Networking:** no published application ports by default for outbound-only messaging. Inspect actual listeners, including IPv6 and container loopback; disabled flags are not proof a listener is absent. Restrict management ingress. Evaluate enforceable gateway egress controls, DNS, proxies, private-network/metadata access and provider connectivity without making routine updates or authentication impractical. Do not claim firewalld ingress rules automatically restrict rootless-container egress.
5. **Secrets and state:** separate provider/bot credentials from worker-accessible state; minimal read-only injection where supported; safe provisioning, rotation and revocation; redacted logs; restrictive permissions; encrypted off-host backups and tested restore. Read-only credentials remain readable by a compromised process that legitimately uses them. Keep secret values out of command arguments, chat, Git and test evidence.
6. **Hermes policy and usability:** explicit messaging allowlists; fail-closed unattended approvals; no blanket YOLO; minimal enabled tools, plugins and MCP servers; supported memory approval; configuration-schema compatibility; provider and auxiliary-client routing. Test interactive CLI, authorized messaging, worker tool use, approved memory and normal maintenance.
7. **Supply chain and updates:** fully qualified images pinned by digest, verified provenance/signatures where actually available, worker build inputs and resulting artifact identity, dependency/vulnerability scanning, timely security updates and tested rollback. A pinned base image plus unpinned package installation is not a fully reproducible build. Scan success is not “no vulnerabilities”; report accepted findings and exception expiry.
8. **Boot, storage and recovery:** distinguish the application baseline from optional LUKS/TPM/Secure Boot/UKI profiles. Evaluate PCR7-only unattended unlock, intact-device theft, boot-entry editing, unmeasured initramfs, firmware/kernel updates and recovery key/header custody. Never weaken an existing stronger profile silently. Hardware power-on behavior and physical TPM security cannot be certified by a container or virtual TPM alone.

Propose a portable baseline plus explicitly selected stronger/alternative profiles. Parameterize administrator/runtime account, paths, storage policy, provider/model, management CIDRs/interfaces, image identity and resource limits. Do not carry over lab IPs, hostnames, fixed UIDs or disk sizes.

Define supported architectures and existing-host versus fresh-install behavior. Start with the demonstrated x86-64 target; add others only with verified image/package support and tests. Fedora Server is not Kinoite/CoreOS: keep host provisioning methods distinct. A server without TPM must receive an explicit supported alternative or a clear preflight rejection, never an undisclosed security downgrade. Do not require repartitioning merely to install the application unless an approved profile genuinely requires it.

## 4. Implement safe, idempotent automation after approval

Prefer extending and simplifying existing artifacts over adding another competing installer. Separate inspection, installation, verification, upgrades, rollback and destructive removal. Provide one documented supported entrypoint, non-secret configuration and actionable failures.

Required properties:

- Inspection/dry-run makes no deployment changes or secret material; show the proposed diff.
- Explicit apply; validate all inputs and prerequisites before mutation; detect ownership/name conflicts.
- Safe argument handling, restrictive temporary files, concurrency locking, atomic validated configuration replacement, meaningful exit codes and preserved primary failures through logging pipelines.
- Capture recovery state before changes; restore temporary negative-test changes on failure/interruption; bound waits and retries; resume partial work safely.
- Avoid unnecessary service restarts, configuration rewrites, package transactions or identity/key regeneration on a matching rerun. Separate upgrades from ordinary convergence.
- Preserve unmanaged files, operator settings, approved memory and credentials. Never overwrite unknown configuration or broadly prune containers/VMs.
- Validate generated Quadlet units against the installed version. Use the correct rootless user manager, runtime directory, working directory, lingering and boot dependencies; account for generated-unit enablement semantics.
- Design firewall/SSH changes to prevent lockout and provide a tested rollback. Storage and boot changes need separate explicit gates.

Specifically investigate whether the current deployment script propagates failed build/reload/start commands, restores host-key files after negative tests, and truly converges on rerun. Recheck the versionless Hermes configuration, auxiliary-provider warning, dashboard/API flags, capability defaults, worker build reproducibility and health-check coverage. Treat these as review targets, not automatically proven current defects.

Add focused regression tests for confirmed defects. Use project-native development tooling; do not introduce heavyweight dependencies merely to run the installer.

## 5. Test progressively in disposable environments

First discover available Podman, systemd, KVM/libvirt, storage and permissions without changing the host. Present required resources and cleanup scope. Use unique owned lab identities and verified Fedora images. Never reuse production bot/provider credentials or run a second gateway against production state.

Use layers with explicit limits:

- **Static/unit:** shell syntax/lint, configuration validation, rendering, failure propagation, rollback and regression tests. Mocks prove logic, not kernel isolation.
- **Rootless Podman containers/pods:** application startup, permissions, mounts, tool routing, credential isolation, networking and resource limits. Do not grant privilege or share host sockets to make tests pass. A Fedora container on another host does not validate a Fedora 44 kernel or boot stack.
- **Disposable Fedora Server 44 VM:** real systemd/Quadlet startup, SELinux enforcement, firewalld, DNF5, fresh installation, repeated apply, interrupted-run recovery, restart/reboot persistence, backup/restore, image upgrade and rollback. Use virtual UEFI/TPM only for the corresponding optional profile and label physical-hardware limitations.

At minimum exercise:

1. Fresh install, second apply and third apply; compare normalized configuration hashes, ownership/modes, image identities, firewall state, service restart counts and persistent data. Explain volatile exclusions; exit code 0 alone is not idempotency evidence.
2. Invalid/unsupported inputs, missing prerequisites, conflicting state, failed image pull/build, interrupted apply, bad config and concurrent execution; verify fail-closed behavior and safe recovery.
3. Authorized and unauthorized gateway interaction, approval denial/timeouts, worker tool round trip, memory staging/approval/fresh-session recall, no worker access to synthetic secrets, denied worker networking, read-only filesystem boundaries and no unexpected published ports.
4. Service crash/restart, reboot without an interactive runtime-user login, missing data mount, backup and restore onto a fresh fixture, failed update and rollback. Include data-schema compatibility; an old image alone may not undo a state migration.
5. Optional real provider/messaging acceptance using operator-approved short-lived test credentials and a bounded spend, followed by revocation and verified cleanup. Mark this untested when credentials/approval are unavailable.

Use bounded non-destructive negative tests with synthetic secrets. If VM testing is unavailable, run the feasible lower layers and provide exact commands/prerequisites for remaining tests. Do not weaken controls, fabricate evidence or label skipped checks as passing.

## 6. Deliverables and completion criteria

Deliver:

- A concise baseline and threat model, with prioritized findings tied to source/evidence and official references.
- A recommended architecture/support matrix and security-versus-usability tradeoffs, including rejected overcomplicated options.
- Approved implementation changes, regression tests and one canonical operator guide covering installation, verification, updates, backup/restore, troubleshooting and rollback.
- A test matrix with **PASS / FAIL / NOT RUN / NOT APPLICABLE**, exact artifact/environment identities, commands, sanitized evidence and cleanup results.
- Remaining vulnerabilities, accepted risks, hardware-specific gates and production deployment prerequisites.

Completion means the documented procedure has actually been followed on a fresh supported fixture, repeated applications converge without unintended changes, claimed boundaries pass positive and negative tests, and recovery/usability checks pass. Where facilities or authorization are missing, deliver an explicitly partial result with the exact next action. Do not call it production-certified or universally portable on the strength of old records, static checks, scanner thresholds or one successful bot reply.

**Begin by reporting the discovered baseline, conflicting/stale records, highest-priority gaps and your proposed plan. Ask only for decisions or permissions that materially affect the next step.**
