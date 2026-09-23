# Hermes Agent hardening research

Research date: 2026-08-23

> [!WARNING]
> This is historical research for Hermes Agent v0.20.5 (`v2026.8.19`). The canonical deployment pin moved to
> v0.20.6 (`v2026.8.27`) on 2026-08-27; do not use this report as current release or security approval until it is
> refreshed against the new tag.

Target versions:

- Hermes Agent v0.20.5, tag `v2026.8.19`, commit `fcbd1076a93841fa88855acce810e342a5b78101`
- Official multi-architecture image
  `docker.io/nousresearch/hermes-agent@sha256:3811ed13da874fba2ac99b6d492db9a203d34cb6dccf90d886948c00d0ccec09`
- Fedora Kinoite 44 host
- Podman 5.8.1 at audit time; remediated to 5.8.4 with a rootless, administrator-owned Quadlet

Scope: whole-process isolation, container and host controls, runtime configuration, secrets, extensions, inbound and
outbound networking, supply chain, updates, backups, SSH, and local DNS naming. This report assesses the documented
baseline. It does not replace the separate live-host validation over SSH.

Confidence labels follow the repository research rubric. `verified` means that an exact-version vendor document,
official advisory, registry record, or standards document was fetched and supports the claim. `likely` denotes a
reasoned implementation recommendation supported by primary sources but not tested on the target host. `unknown`
means that the available official material does not establish the fact.

## Answer

The proposed rootless Podman and root-owned Quadlet architecture is the correct security boundary for Hermes because
it wraps the whole agent process tree, not only terminal commands. The installation could not be accepted while it
remained on Podman 5.8.1: that version is affected by a high-severity host-environment disclosure fixed in 5.8.4 and
a Quadlet replacement defect fixed in 5.8.6. Fedora supplied Podman 5.8.4 on 2026-08-23. That build is acceptable only
with the second advisory's documented workaround: install the administrator-owned Quadlet by direct file placement
and never use `podman quadlet install --replace` until 5.8.6 or later is installed. The remaining acceptance work is
to verify the digest-pinned image, restrictive container settings, explicit Hermes runtime overrides, no unintended
listeners, constrained egress, extension inventory, secret permissions, and tested backup and restore.

## Findings

### Version and artifact identity

- Hermes v0.20.5 is the release identified by tag `v2026.8.19`, release commit `fcbd107`, and release date
  2026-08-19. [`verified`]. Source: [Hermes Agent v0.20.5 release][hermes-release]. The release page says this patch
  collected hundreds of changes after v0.20.4 and deferred the complete curated notes to v0.21.0. Version-specific
  review therefore needs the tagged source, not only the abbreviated release notes.

- The deployment digest resolves to the official `nousresearch/hermes-agent` multi-architecture image and the amd64
  manifest identifies the full release commit in its OCI revision label. [`verified`]. Source:
  [Docker Hub v2026.8.19 image][hermes-image]. An independent registry inspection on 2026-08-23 reproduced index
  digest `sha256:3811ed13...ccec09`, amd64 manifest `sha256:f3cba6ab...df1b5`, and revision
  `fcbd1076a93841fa88855acce810e342a5b78101`.

- The published image sets `HERMES_HOME=/opt/data`, confines the write-safe root to `/opt/data`, disables Hermes lazy
  installs, and keeps the installed application under `/opt/hermes`. [`verified`]. Sources:
  [Docker Hub v2026.8.19 image][hermes-image] and [Hermes Docker guide][hermes-docker]. The Docker guide further
  describes `/opt/data` as the single persistent location for configuration, secrets, sessions, memories, skills,
  hooks, plugins, cron state, logs, and tool home directories.

### Security boundary and process isolation

- Hermes treats OS-level isolation as the load-bearing boundary when the agent consumes untrusted input. Approval
  prompts, redaction, scanners, allowlists, and prompt-injection checks are explicitly described as useful heuristics,
  not containment. [`verified`]. Source: [Hermes security policy][hermes-security-policy].

- A terminal-only container backend does not confine `execute_code`, MCP subprocesses, Python plugins, hook handlers,
  or skill loading. Whole-process wrapping does confine those paths under the same filesystem, network, process, and
  syscall boundary. [`verified`]. Source: [Hermes security policy][hermes-security-policy].

- Running the official Hermes image as the persistent gateway is the correct whole-process mode for this deployment.
  The outer rootless Podman container should remain the primary boundary; selecting `terminal.backend: docker` inside
  that already-containerized process is not a substitute for the outer boundary. [`verified`]. Sources:
  [Hermes security policy][hermes-security-policy] and [Hermes Docker guide][hermes-docker].

- Rootless Podman always uses a user namespace; container root maps to the invoking host user by default, and the
  rootless user's subordinate UID/GID ranges must exist in `/etc/subuid` and `/etc/subgid`. Containers created by that
  user are not managed as root-owned Podman containers. [`verified`]. Source:
  [Podman 5.8.1 command reference][podman-main].

- The official Hermes image must start its s6 `/init` as container root so it can initialize and correct ownership of
  `/opt/data`; it then drops every supervised service and the main process to the `hermes` user. Overriding the image
  entrypoint or forcing `User=10000` would bypass this documented startup model. [`verified`]. Source:
  [Hermes Docker guide][hermes-docker]. Host privilege remains bounded by the outer rootless user namespace, but the
  init process can still modify files deliberately mounted into the container.

### Podman 5.8.1 blocking vulnerabilities

- Podman 5.8.1 is in the affected range for CVE-2026-57231 / GHSA-4hq8-gpf5-8p68, a high-severity issue in which a
  malformed image environment entry can cause Podman to copy host environment variables into the container. The
  affected range is 1.8.1 through 5.8.3 and the v5 fix is 5.8.4. [`verified`]. Source:
  [Podman environment-leak advisory][podman-env-advisory]. Digest pinning reduces image substitution risk but does not
  make a vulnerable runtime acceptable.

- Podman 5.8.1 is also in the affected range for CVE-2026-19730 / GHSA-fx76-2j3w-2mx6. With
  `podman quadlet install --replace`, a shorter replacement could retain trailing content such as an old capability or
  volume mount. The v5 fix is 5.8.6; manual file placement is the documented workaround. [`verified`]. Source:
  [Podman Quadlet replacement advisory][podman-quadlet-advisory]. Direct administrator-owned placement avoids the
  affected command path; this is a required workaround, not merely a risk reduction.

- Podman 5.8.1 is not affected by the separately disclosed WORKDIR symlink traversal fixed in 5.7.1. [`verified`].
  Source: [Podman WORKDIR advisory][podman-workdir-advisory]. This does not offset the two applicable findings above.

- Upgrade Podman to at least 5.8.4 before security acceptance. If the installed version is below 5.8.6, never use
  `podman quadlet install --replace`; use direct administrator-owned file placement as the official advisory directs.
  Upgrade to 5.8.6 or later when Fedora supplies it so the workaround is no longer necessary. [`verified`]. Sources:
  [Podman environment-leak advisory][podman-env-advisory] and
  [Podman Quadlet replacement advisory][podman-quadlet-advisory]. Re-run the live inspection after every upgrade
  because the package version and effective Quadlet output are host state, not properties of this repository.

### Quadlet and container hardening baseline

- `/etc/containers/systemd/users/<UID>/` is an official rootless Quadlet search path intended for an administrator to
  target a specific user's systemd manager. A rootless Quadlet must be placed in a rootless search path; setting
  `User=` or `Group=` in a system Quadlet does not turn it into a rootless unit. [`verified`]. Source:
  [Podman 5.8.1 systemd unit reference][podman-quadlet-unit]. This supports an administrator-owned file that the
  `hermes` service account can read but cannot edit.

- The container should keep a read-only root filesystem and create only explicit writable storage for `/opt/data`
  plus bounded temporary filesystems. Podman 5.8.1 documents that container roots are writable by default and that
  `--read-only` prohibits image-root writes while writable tmpfs mounts may still be provided. [`verified`]. Source:
  [Podman 5.8.1 run reference][podman-run].

- The `/opt/data` bind mount should use the private SELinux `:Z` label and SELinux must remain enforcing. Podman 5.8.1
  documents `:Z` as a private, unshared container label; disabling SELinux separation would remove this layer.
  [`verified`]. Source: [Podman 5.8.1 run reference][podman-run].

- `NoNewPrivileges=true`, the default seccomp profile, a complete capability drop followed by only the capabilities
  proven necessary for the s6 initialization path, and no privileged mode are appropriate controls. Podman documents
  that `no-new-privileges` prevents privilege gain through executable set-ID bits and file capabilities, and warns
  that added capabilities increase breakout risk. [`verified`]. Source: [Podman 5.8.1 run reference][podman-run].
  `SYS_ADMIN`, `SYS_PTRACE`, `MKNOD`, `SYS_MODULE`, or an unconfined seccomp profile should fail acceptance.

- The exact minimal capability additions needed by this release under rootless Podman are not declared in the Hermes
  Docker guide. [`unknown`]. The image documents first-boot chown and a later UID/GID drop, but it does not publish a
  Podman capability manifest. Resolve this by inspecting the generated `ExecStart`, running first boot with an empty
  data directory, verifying normal restart, and then testing whether any proposed capability can be removed.

- Memory, CPU, PID, open-file, and temporary-filesystem limits should be explicit and measured against the intended
  features. Podman 5.8.1 otherwise allows unlimited memory when no limit is set and defaults to a PID limit of 2048;
  Hermes recommends 2–4 GB and two cores for general use, with browser automation requiring more memory.
  [`verified`]. Sources: [Podman 5.8.1 run reference][podman-run] and [Hermes Docker guide][hermes-docker]. A numeric
  limit is a deployment choice, so acceptance should include a representative workload rather than assuming a value.

- Do not mount the host Podman/Docker socket, host SSH directory, whole home directory, devices, or other host paths.
  The official image contains a Docker CLI and its documentation describes socket mounting as the explicit opt-in that
  lets the agent drive the host daemon. [`verified`]. Source: [Hermes Docker guide][hermes-docker]. Such a socket would
  defeat the intended container boundary.

- Use a private bridge namespace, not host networking, and publish no ports for a messaging-only gateway. Podman warns
  that host networking gives a container access to host loopback-bound services and sockets. [`verified`]. Source:
  [Podman 5.8.1 run reference][podman-run]. No `PublishPort`, `Network=host`, `--device`, `--privileged`, or host IPC/PID
  namespace should appear in the generated unit.

### Hermes configuration overrides

- A production profile should be created through the setup wizard's Blank Slate path and then audited against the
  generated file. A fresh Blank Slate enables only the provider/model plus file and terminal toolsets; web, browser,
  code execution, memory, delegation, cron, skills, plugins, and MCP are off until selected. [`verified`]. Source:
  [Hermes quickstart][hermes-quickstart]. The installed `config.yaml`, not the wizard choice, is the acceptance record.

- Set `tool_loop_guardrails.hard_stop_enabled: true` for an unattended gateway. Its default is false, and the exact
  Docker guide recommends explicit hard stops for server deployments. [`verified`]. Source:
  [Hermes Docker guide][hermes-docker]. Keep finite thresholds and verify that the running profile resolves them.

- Keep `security.allow_private_urls: false`, `security.redact_secrets: true`, and
  `security.protected_instruction_files: true`. Hermes documents private URL blocking as default and validates every
  redirect against private, loopback, link-local, CGNAT, reserved, and cloud-metadata destinations. [`verified`].
  Source: [Hermes security guide][hermes-security]. This remains an application heuristic; a shell or plugin can make
  its own network request, so network policy must independently block prohibited destinations.

- Keep Tirith enabled and set `security.tirith_fail_open: false` for the hardened profile. Tirith is enabled by default,
  but its default is to allow execution if the scanner is absent or times out. [`verified`]. Source:
  [Hermes security guide][hermes-security]. Verify scanner availability after every image change so fail-closed does
  not unexpectedly disable required work.

- Keep `security.allow_lazy_installs: false` and `HERMES_DISABLE_LAZY_INSTALLS=1`. The general application default is
  true, but the official image intentionally overrides it to prevent runtime dependency writes. [`verified`]. Sources:
  [Hermes security guide][hermes-security], [Hermes Docker guide][hermes-docker], and
  [Docker Hub v2026.8.19 image][hermes-image]. Verify that the image-supplied environment retains the variable; the
  [exact environment-variable reference][hermes-environment] says not to add this internal bridge variable to `.env`.
  Do not authorize ad hoc `npx`, `uvx`, `pip`, or package-manager installs during unattended turns; build and pin a
  reviewed derived image when an extra dependency is required.

- If web tools are ever enabled, explicitly set both `web.keyless_fallback: false` and `web.keyless_rescue: false`
  unless anonymous multi-vendor routing is an accepted data-flow. v0.20.5 defaults to rotating no-key requests among
  five vendors and may rescue a failed keyed request through that ring. [`verified`]. Sources:
  [Hermes web-search guide][hermes-web] and [Hermes v0.20.5 release][hermes-release]. With web disabled, verify that the
  tools are absent as well as setting these defense-in-depth values.

- For an unattended hardened baseline, preserve `approvals.cron_mode: deny`,
  `approvals.single_query_mode: deny`, `approvals.mcp_reload_confirm: true`, `hooks_auto_accept: false`, and
  `cron.allow_agent_scheduling: false`; consider `approvals.mode: manual` where an authenticated operator can answer.
  These are the exact v0.20.5 safe defaults except that the overall approval mode defaults to smart. [`verified`].
  Sources: [Hermes configuration reference][hermes-configuration],
  [Hermes configuration-defaults source][hermes-config-defaults], [Hermes hook guide][hermes-hooks], and
  [Hermes cron guide][hermes-cron]. Approval rules are defense in depth, not the security boundary.

- Leave the API and dashboard disabled and do not publish ports. The API requires `API_SERVER_ENABLED=true`; the
  dashboard requires `HERMES_DASHBOARD=1` and otherwise stays down. A non-loopback dashboard requires an authentication
  provider and fails closed without one. [`verified`]. Source: [Hermes Docker guide][hermes-docker]. If either surface
  becomes necessary, bind it to loopback, reach it through an SSH tunnel or authenticated VPN, use a long random key or
  supported identity provider, restrict CORS to exact origins, and firewall the port to named administrators.

- The Docker guide records a June 2026 campaign in which exposed unauthenticated dashboard/API surfaces were used to
  drive agents into planting SSH-key persistence. [`verified`]. Source: [Hermes Docker guide][hermes-docker]. Treat an
  unexpected listener on 8642 or 9119 as a security failure even if the VLAN is not internet-routed.

### Secrets, identity, and persistent state

- The host data directory should be owned only by the dedicated rootless service account and mode 0700; `.env`, MCP
  OAuth tokens, auth files, private keys, and backup archives should be mode 0600 or stricter. Hermes explicitly
  requires mode 0600 for `.env`, never placing it in version control, and records MCP tokens with mode 0600.
  [`verified`]. Sources: [Hermes security guide][hermes-security] and [Hermes MCP guide][hermes-mcp].

- Environment filtering limits accidental disclosure to subprocesses but cannot hide credentials from skills,
  plugins, or hook code loaded inside the agent process. [`verified`]. Source:
  [Hermes security policy][hermes-security-policy]. Use separate, least-privilege service credentials; do not reuse
  personal administrator tokens, and rotate credentials when an extension or persistent volume is suspected compromised.

- Do not put secret values in the administrator-owned Quadlet. Prefer the protected `/opt/data/.env` or an approved
  secret-injection mechanism, understanding that Hermes itself must ultimately read the value. [`likely`]. Sources:
  [Hermes Docker guide][hermes-docker] and [Hermes security policy][hermes-security-policy]. Moving a secret from a
  file to an environment variable does not protect it from trusted in-process code.

- Separate containers and data directories are required when profiles need different credentials, network access, or
  trust envelopes. Multiple profiles in one container share a process tree and resource boundary; Hermes recommends
  distinct containers for credential, network, resource, or compliance isolation. [`verified`]. Source:
  [Hermes Docker guide][hermes-docker]. Never point two live containers at the same data directory.

### Plugins, skills, hooks, MCP, and cron

- Treat every plugin, skill script, and hook as privileged code. Hermes states that in-process plugins and hook handlers
  can access the agent's credentials and that reviewing only a skill's prose is insufficient when it contains scripts.
  [`verified`]. Source: [Hermes security policy][hermes-security-policy]. Keep the baseline inventories empty and enable
  one reviewed capability at a time.

- Third-party general plugins are opt-in, but several bundled provider/platform plugin categories load outside
  `plugins.enabled`, and existing user plugins may be grandfathered into the allowlist during migration. [`verified`].
  Source: [Hermes plugin guide][hermes-plugins]. Acceptance must therefore enumerate discovered, enabled, disabled,
  provider-selected, platform-selected, memory, and context-engine plugins; checking only `plugins.enabled` is
  incomplete.

- Pin an installed plugin to a full immutable commit. Hermes verifies an exact 40-character commit and refuses to
  update a pinned plugin automatically. [`verified`]. Source: [Hermes plugin guide][hermes-plugins]. Review plugin
  source, manifest, installer, dependencies, requested permissions, outbound destinations, and all update diffs.

- Shell hooks run with the full service-account credentials. They fail open by default on spawn, timeout, or invalid
  output, and editing a previously approved script does not invalidate consent because approval keys on the command
  string, not a content hash. [`verified`]. Source: [Hermes hook guide][hermes-hooks]. Keep hooks empty initially; when
  a security gate is required, configure it fail-closed, protect the script from the service account, and run
  `hermes hooks doctor` after changes.

- Installing an MCP catalog entry can clone code and run bootstrap/package-install commands. Catalog review is a
  project review gate, not a sandbox; MCP entries are not auto-updated. A failed discovery probe can also leave no
  per-tool filter. [`verified`]. Source: [Hermes MCP guide][hermes-mcp]. Keep `mcp_servers` empty initially. For each
  approved server, pin packages or commits, define an explicit tool include-list, supply only server-specific secrets,
  set timeouts, and prefer a narrowly scoped remote HTTPS endpoint over an unpinned `npx -y` subprocess.

- Cron jobs run unattended in fresh sessions and may execute scripts; the default prevents cron-run agents from
  recursively creating more jobs. [`verified`]. Source: [Hermes cron guide][hermes-cron]. Keep cron empty until a job
  has a named owner, explicit tools/skills, least-privilege credentials, bounded runtime, deterministic destination,
  and reviewed failure behavior. Preserve the deny mode for dangerous commands and agent scheduling.

### Inbound and outbound network policy

- Every messaging channel must use an explicit user/channel allowlist or authenticated pairing; do not set
  `GATEWAY_ALLOW_ALL_USERS=true`. Hermes describes itself as single-tenant and requires authorization on every
  network-exposed surface. [`verified`]. Sources: [Hermes security policy][hermes-security-policy] and
  [Hermes security guide][hermes-security]. Separate instances are required where different callers need different
  capabilities.

- A Podman bridge supplies network namespace isolation but not destination-aware egress control. `Network=none`
  removes connectivity entirely, while host networking exposes host-loopback services. [`verified`]. Source:
  [Podman 5.8.1 run reference][podman-run]. For Hermes to reach an external model or messaging provider, the hardened
  deployment therefore needs either explicit firewall/router destination policy or an authenticated egress proxy.

- Allowing only TCP 443 to the internet is not sufficient to contain prompt-driven exfiltration because arbitrary
  HTTPS destinations remain reachable. [`likely`]. Source: [Hermes security policy][hermes-security-policy], which
  recommends whole-process network policy and identifies OpenShell's L7 egress policy as the stronger option. Maintain
  an allowlist of exact model, messaging, update, time, and DNS endpoints; deny LAN, management, metadata, and unrelated
  internet destinations from the Hermes trust zone.

- Do not grant private-network access merely to reach a local inference or integration server. If a LAN service is
  required, place it in a dedicated segment, authenticate it, allow only that destination and port at the network
  boundary, and document the risk before enabling `security.allow_private_urls`. [`verified`]. Source:
  [Hermes security guide][hermes-security].

### Supply chain, updates, logging, and backups

- Digest pinning gives immutable artifact selection but does not prove publisher identity by itself. The tagged Docker
  workflow pins GitHub Actions by commit, builds and tests before publishing, keeps pull-request builds secret-free,
  and records the source revision. [`verified`]. Sources: [Hermes Docker workflow][hermes-docker-workflow],
  [Hermes Dockerfile][hermes-dockerfile], and [Docker Hub v2026.8.19 image][hermes-image].

- No official Hermes documentation or tagged workflow reviewed here documents a required image-signature verification
  command, signer identity, or verification policy for `nousresearch/hermes-agent`. [`unknown`]. Source:
  [Hermes Docker workflow][hermes-docker-workflow]. The registry index contains attestation-manifest descriptors, but
  this review did not verify their predicate, subject, or signer. Retain the approved digest, verify its release-commit
  label, scan the exact digest, and do not describe the image as cryptographically publisher-verified without a
  documented trust policy.

- The tagged Dockerfile checksum-verifies downloaded SQLite and s6 archives and digest-pins the uv and Node source
  images, but its Debian builder and runtime bases use the mutable `debian:13.4` tag. [`verified`]. Source:
  [Hermes Dockerfile][hermes-dockerfile]. This is an upstream reproducibility gap; it does not change the immutability
  of the already-approved final digest.

- Update by selecting a reviewed release, resolving and recording its new digest, backing up persistent data, testing
  setup/migration and a representative workload, switching the Quadlet digest, then verifying runtime identity and
  logs. Hermes recreates the stateless image around `/opt/data` and makes timestamped configuration backups before a
  schema migration. [`verified`]. Source: [Hermes Docker guide][hermes-docker]. Do not track `latest` in production.

- Back up all of `/opt/data`, because it is the documented single source of persistent state, and encrypt the backup
  because it contains `.env`, auth tokens, sessions, memories, logs, skills, and hooks. [`verified`]. Source:
  [Hermes Docker guide][hermes-docker]. Stop the gateway or take a storage-level atomic snapshot before copying the
  directory and perform a periodic restore drill. [`likely`]. The stop/snapshot recommendation follows from Hermes'
  warning that its session and memory files are not designed for concurrent writers.

- Persistent gateway and boot-reconciliation logs live inside `/opt/data`; container logs alone disappear when the
  container is removed. [`verified`]. Source: [Hermes Docker guide][hermes-docker]. Set host retention and disk alerts,
  review unauthorized-access and extension-change events, and ensure secrets are not copied into monitoring systems.

- Keep the Fedora image deployment current and preserve a tested rollback deployment. Fedora's Kinoite/rpm-ostree
  reference lists `rpm-ostree upgrade --check`, `rpm-ostree upgrade`, `rpm-ostree status`, and
  `rpm-ostree rollback`. [`likely (generic Kinoite reference)`]. Source: [Fedora Kinoite rpm-ostree cheat sheet][fedora-ostree].
  Host update cadence and the actually deployed Fedora commit still require live validation.

### SSH and local DNS naming

- OpenSSH provides public-key authentication, password-authentication control, direct-root-login control, named-user
  allowlists, and a switch that disables forwarding features. [`verified (upstream OpenSSH)`]. Source:
  [OpenSSH `sshd_config` manual][openssh-sshd-config]. For Fedora 44, validate the effective packaged configuration
  with `sshd -T`; use a dedicated named account, prove key login before disabling password authentication, restrict the
  firewall to management sources, and preserve an out-of-band recovery path. [`likely`]. The live Fedora build and
  policy remain authoritative; no version-matched Fedora 44 SSH hardening page was verified in this pass.

- `hermes.ai.lab.local` conflicts with the special-use meaning of `.local.`. RFC 6762 assigns that suffix and all names
  below it to Multicast DNS behavior, which can create resolver ambiguity for a unicast private zone. [`verified`].
  Source: [RFC 6762][rfc6762].

- For a residential lab, migrate the unicast zone to `home.arpa.` or use a subdomain of a registered domain. RFC 8375
  designates `home.arpa.` for non-unique residential homenets and specifies ordinary DNS resolution. [`verified`].
  Source: [RFC 8375][rfc8375]. A rename must update DNS, certificates, SSH host aliases/known-host records, monitoring,
  firewall objects, and installation documentation together.

### Acceptance checklist derived from the evidence

The installation is ready for security acceptance only when every applicable item below is demonstrated by live
output. These are recommendations inferred from the verified findings; the live audit records the final status.

- [`likely`] Podman reports 5.8.4 or later; below 5.8.6, the Quadlet was installed by direct administrator-owned file
  placement and the affected `podman quadlet install --replace` command was not used.
- [`likely`] The running image ID, repository digest, OCI revision, and Hermes version match the approved release.
- [`likely`] The generated service comes from the root-owned per-UID rootless Quadlet and runs in the dedicated user
  manager; no editable copy shadows it in a higher-precedence user path.
- [`likely`] The container is rootless, unprivileged, read-only, SELinux-confined, seccomp-confined, no-new-privileges,
  capability-minimized, resource-bounded, and limited to `/opt/data:Z` plus explicit tmpfs mounts.
- [`likely`] No daemon socket, host home, SSH material, devices, host namespaces, or unexpected bind mounts exist.
- [`likely`] No host ports or unexpected listeners exist; API, dashboard, and allow-all gateway modes are disabled.
- [`likely`] Egress reaches only documented providers and infrastructure; LAN, management, metadata, and unrelated
  internet destinations are denied independently of Hermes' application checks.
- [`likely`] The effective config has hard loop stops, fail-closed Tirith, private-URL denial, redaction, protected
  instructions, no lazy installs, no keyless web fallback/rescue, deny-mode unattended approvals, and a minimal toolset.
- [`likely`] Plugin, skill, hook, MCP, cron, platform, memory-provider, and context-engine inventories are empty or each
  entry has an owner, immutable revision, permission review, and network/credential scope.
- [`likely`] Data and secret permissions are restrictive, least-privilege credentials are used, and no raw secret is
  emitted during validation.
- [`likely`] The SSH key path works with host-key verification; password and root login are disabled only after key
  access is proven and recovery access exists.
- [`likely`] Host and container updates, log review, encrypted backup, restore, and rollback procedures have been
  exercised and recorded.
- [`likely`] The `.local` naming migration is planned or the documented mDNS/unicast conflict is explicitly accepted.

## Unresolved or conflicting

- [`unknown`] The live Hermes server state was not available to this research pass. Resolve with the separate SSH audit:
  package versions, image identity, generated Quadlet service, mounts, namespaces, capabilities, SELinux labels,
  resource limits, listeners, firewall, effective Hermes config, extension inventory, file modes, logs, and backup state.

- [`unknown`] The exact minimal container capability set for the v0.20.5 s6 first-boot and steady-state paths is not
  published. Resolve by capability-removal testing on an empty disposable data directory and on a normal restart.

- [`unknown`] A publisher-signature trust policy for the official Docker image could not be verified from the tagged
  source, workflow, release, Docker guide, or registry page. The observed attestation descriptors require separate
  predicate and signer verification before they can be treated as provenance evidence.

- [`unknown`] This report does not assert that the exact image is free of OS or language-package vulnerabilities.
  Resolve with a current vulnerability scan of the pinned digest, review every material finding, and repeat after each
  digest or runtime update.

- [`unknown`] A version-matched Fedora 44 SSH hardening page was not verified. The upstream OpenSSH controls are
  verified, but the separate live audit must establish the Fedora package's effective configuration with `sshd -T`.

## Sources

Each source below was opened and inspected in full or at the relevant exact-version source lines, then checked with
`curl -L` on 2026-08-23. Every final URL returned HTTP 200; the OpenBSD manual required one retry after a transient DNS
failure. Search-result snippets were used only for discovery, never as evidence.

1. [Hermes Agent v0.20.5 release][hermes-release] — NousResearch, 2026-08-19 — exact release
2. [Hermes security policy][hermes-security-policy] — NousResearch — exact tag `v2026.8.19`
3. [Hermes Docker guide][hermes-docker] — NousResearch — exact tag `v2026.8.19`
4. [Hermes security guide][hermes-security] — NousResearch — exact tag `v2026.8.19`
5. [Hermes configuration reference][hermes-configuration] — NousResearch — exact tag `v2026.8.19`
6. [Hermes quickstart][hermes-quickstart] — NousResearch — exact tag `v2026.8.19`
7. [Hermes web-search guide][hermes-web] — NousResearch — exact tag `v2026.8.19`
8. [Hermes MCP guide][hermes-mcp] — NousResearch — exact tag `v2026.8.19`
9. [Hermes plugin guide][hermes-plugins] — NousResearch — exact tag `v2026.8.19`
10. [Hermes hook guide][hermes-hooks] — NousResearch — exact tag `v2026.8.19`
11. [Hermes cron guide][hermes-cron] — NousResearch — exact tag `v2026.8.19`
12. [Hermes Docker workflow][hermes-docker-workflow] — NousResearch — exact tag `v2026.8.19`
13. [Hermes Dockerfile][hermes-dockerfile] — NousResearch — exact tag `v2026.8.19`
14. [Docker Hub v2026.8.19 image][hermes-image] — NousResearch registry artifact — exact release tag
15. [Podman 5.8.1 command reference][podman-main] — Podman project — exact version 5.8.1
16. [Podman 5.8.1 run reference][podman-run] — Podman project — exact version 5.8.1
17. [Podman 5.8.1 systemd unit reference][podman-quadlet-unit] — Podman project — exact version 5.8.1
18. [Podman environment-leak advisory][podman-env-advisory] — Podman project, 2026-06-24
19. [Podman Quadlet replacement advisory][podman-quadlet-advisory] — Podman project, 2026-08-13
20. [Podman WORKDIR advisory][podman-workdir-advisory] — Podman project, 2026-06-17
21. [Fedora Kinoite rpm-ostree cheat sheet][fedora-ostree] — Fedora Project — generic Kinoite reference
22. [OpenSSH `sshd_config` manual][openssh-sshd-config] — OpenBSD Project — current upstream reference
23. [RFC 6762][rfc6762] — IETF, 2013 — Multicast DNS standard
24. [RFC 8375][rfc8375] — IETF, 2018 — `home.arpa.` special-use domain
25. [Hermes configuration-defaults source][hermes-config-defaults] — NousResearch — exact tag `v2026.8.19`
26. [Hermes environment-variable reference][hermes-environment] — NousResearch — exact tag `v2026.8.19`

[fedora-ostree]: https://docs.fedoraproject.org/en-US/fedora-kinoite/_attachments/silverblue-cheatsheet.pdf
[hermes-configuration]: https://github.com/NousResearch/hermes-agent/blob/v2026.8.19/website/docs/user-guide/configuration.md
[hermes-config-defaults]: https://github.com/NousResearch/hermes-agent/blob/v2026.8.19/hermes_cli/config_defaults.py
[hermes-cron]: https://github.com/NousResearch/hermes-agent/blob/v2026.8.19/website/docs/user-guide/features/cron.md
[hermes-docker-workflow]: https://github.com/NousResearch/hermes-agent/blob/v2026.8.19/.github/workflows/docker.yml
[hermes-docker]: https://github.com/NousResearch/hermes-agent/blob/v2026.8.19/website/docs/user-guide/docker.md
[hermes-dockerfile]: https://github.com/NousResearch/hermes-agent/blob/v2026.8.19/Dockerfile
[hermes-environment]: https://github.com/NousResearch/hermes-agent/blob/v2026.8.19/website/docs/reference/environment-variables.md
[hermes-hooks]: https://github.com/NousResearch/hermes-agent/blob/v2026.8.19/website/docs/user-guide/features/hooks.md
[hermes-image]: https://hub.docker.com/layers/nousresearch/hermes-agent/v2026.8.19/images/sha256-f3cba6abf5ed80d47a271498d663ace5dda87f45000552afb8be8370a35df1b5
[hermes-mcp]: https://github.com/NousResearch/hermes-agent/blob/v2026.8.19/website/docs/user-guide/features/mcp.md
[hermes-plugins]: https://github.com/NousResearch/hermes-agent/blob/v2026.8.19/website/docs/user-guide/features/plugins.md
[hermes-quickstart]: https://github.com/NousResearch/hermes-agent/blob/v2026.8.19/website/docs/getting-started/quickstart.md
[hermes-release]: https://github.com/NousResearch/hermes-agent/releases/tag/v2026.8.19
[hermes-security-policy]: https://github.com/NousResearch/hermes-agent/blob/v2026.8.19/SECURITY.md
[hermes-security]: https://github.com/NousResearch/hermes-agent/blob/v2026.8.19/website/docs/user-guide/security.md
[hermes-web]: https://github.com/NousResearch/hermes-agent/blob/v2026.8.19/website/docs/user-guide/features/web-search.md
[openssh-sshd-config]: https://man.openbsd.org/sshd_config
[podman-env-advisory]: https://github.com/podman-container-tools/podman/security/advisories/GHSA-4hq8-gpf5-8p68
[podman-main]: https://docs.podman.io/en/v5.8.1/markdown/podman.1.html
[podman-quadlet-advisory]: https://github.com/podman-container-tools/podman/security/advisories/GHSA-fx76-2j3w-2mx6
[podman-quadlet-unit]: https://docs.podman.io/en/v5.8.1/markdown/podman-systemd.unit.5.html
[podman-run]: https://docs.podman.io/en/v5.8.1/markdown/podman-run.1.html
[podman-workdir-advisory]: https://github.com/podman-container-tools/podman/security/advisories/GHSA-q6r4-3wmg-fwcq
[rfc6762]: https://www.rfc-editor.org/info/rfc6762/
[rfc8375]: https://www.rfc-editor.org/info/rfc8375/
