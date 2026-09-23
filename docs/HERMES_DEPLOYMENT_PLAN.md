# Hermes Fedora Server 44 deployment plan

This is the implementation and operations plan for the dedicated Hermes host at
`10.0.30.10`. The disposable Fedora Server 44 certification gate and the first
production deployment have completed.

## Current status

Final-source run `run-20260901T183122Z` passed certification and cleanup and
issued matching mode-`0600` promotion record `promotion-20260901T183122Z.record`.
The prior production installation was removed with `rollback --purge-fresh`;
the record then authorized a fresh deployment to `aicowork@10.0.30.10`.
Provider acceptance and exact `HERMES_OK` passed, the controller closed, and
the direct status reports `health=healthy`, `readonly=true`, `ports={}`, and
`drift=none`. The local controller state records the bound promotion and
`stage-closed` without credential material.

## Historical repair narrative

Disposable run `run-20260831T212756Z` passed signed-media verification, Fedora
Server installation, DNF5 update, runtime and root acceptance, one initial LUKS
unlock, three independent reboot-boundary-prompt sequences, provider
acceptance, and exact authenticated `HERMES_OK`. Its final status is healthy,
read-only, port-free, and drift-free. The run then revoked provider
authentication, purged fresh data, removed fixture privilege, destroyed the
domain and both dedicated storage files, and issued strict-valid mode-`0600`
record
`/var/home/cloudops/.local/state/hermes-certification/promotion-20260831T212756Z.record`.
Its first-use window expires at `2026-09-01T22:22:17Z`. The first production
attempt exposed a controller defect before record binding or host mutation.
The repair changes the artifact fingerprint, so this historical record cannot
authorize the repaired tree; a fresh certification is required.

The earlier post-close failure remains preserved as regression evidence. Its
repair maps absent optional clean-VM state to safe defaults, performs bounded
status convergence, and retains a secret-free failure artifact. The focused,
controller, complete offline, guide, syntax, compile, lint, and format gates
all pass. `PROD-01` (host adoption), `PROD-02` (preflight), `REG-06` (sudo
bootstrap repair), and `REG-07` (four-argument update-mode repair) are
complete. At that point, `LAB-06` had to issue a matching record before
blocked task `PROD-03` (deployment) could resume; `PROD-04` (persistence
verification) followed. The tasks had to continue in order. See
[`HERMES_INSTALLATION_VERIFICATION.md`](HERMES_INSTALLATION_VERIFICATION.md)
for the chronological evidence and [`VM Deployment Testing Tasks`](../vm/DEPLOYMENT_TASKS.md)
for command-level pass criteria.

The production host adoption then completed, but its first read-only check
failed with two blockers: `/var` had about 11.36 GiB free on a 15 GiB root
logical volume, below the required 20 GiB, and non-loopback listeners were
present on ports 5355 and 9090. The root LV has since been expanded to 40 GiB
and XFS growth was verified; a direct read-only check now shows about 35.9 GiB
free. The host hardening policy was then applied: LLMNR is disabled and the
`cockpit.socket` is masked. A direct read-only listener check now shows only
the expected SSH and loopback listeners. The full check then returned exact
`PREFLIGHT_OK`. At this historical checkpoint, no production package mutation
or reboot had started.

The first `PROD-03` invocation passed preflight and verified all four uploaded
bootstrap artifacts, then stopped with `sudo: a password is required`. Fedora
scopes password-backed sudo timestamps to the SSH TTY, but the helper bootstrap
opened a new TTY and incorrectly used `sudo -n`. Cleanup left no remote helper,
temporary artifact, controller stage, promotion binding, provider
authentication, package mutation, or reboot. The bootstrap now permits its one
sudo prompt in that same TTY; the scoped helper remains non-interactive after
installation. A red/green regression passes. Because
`scripts/hermes/deploy-lib.sh` is fingerprinted, `LAB-06` must certify the
repaired tree before production could continue.

The first `LAB-06` attempt, `run-20260901T015813Z`, passed media,
installation, initial unlock, and SSH recovery, then stopped before Hermes
identity creation. The four-argument deployment preflight had silently left
update mode disabled, so it rejected Podman 5.8.4 and the `dnf5-automatic`
timer instead of installing them. `REG-07` fixes that argument parser and adds
a deterministic red/green contract. The controller suite now passes 52
examples, the complete Hermes/VM suite passes 135 examples, and all 217 guide
checks pass. Failed-run cleanup removed the certifier process, domain, QCOW2,
and OEMDRV; no provider authentication or promotion record occurred. At this
historical point, a fresh `LAB-06` rerun remained required.

The second `LAB-06` attempt, `run-20260901T022455Z`, verified the repair by
passing exact preflight, Fedora and Podman update, runtime, hardening,
credential-free acceptance, root acceptance, and all three ordered encrypted
reboots. It reached `AUTHENTICATION_READY`, and readiness input was submitted
on the managed terminal. The browser login was not completed within the
provider window, so no provider or inference stage was written. The run exited
78, destroyed its VM and both storage files, and issued no record. This left
the code gates green but the external provider gate incomplete. At that time,
`LAB-06` could be retried only while the operator was available for browser
authentication.

## Progress control

- `HERMES_INSTALLATION_VERIFICATION.md` is the canonical evidence ledger.
- `vm/DEPLOYMENT_TASKS.md` owns task IDs, commands, pass conditions, and evidence filenames.
- Offline output is retained below a mode-`0700` timestamped `progress-*` directory.
- VM evidence is retained below the certifier's mode-`0700` `run-*` directory.
- Interactive provider output is never redirected to a log because it may contain OAuth or credential material.
- A task changes to `PASS` only when its exact pass condition and durable evidence path both exist.
- Production mutation starts only after the matching promotion record exists and all preceding task IDs pass in order.

## Architecture

- `scripts/hermes/fedora-server-host.sh` is the private Fedora Server host
  module. It owns platform detection, prerequisites, DNF5 update policy,
  host policy, and host checks.
- `hermes-certify-vm.sh` creates `lab-hermes-server`, runs the complete
  deployment and provider acceptance flow, revokes credentials, purges fresh
  data, destroys the VM, and then emits a secret-free promotion record.
- `hermes-deploy.sh` is the only production state engine. It binds the first
  promotion record to the target host's SSH ED25519 fingerprint and machine-id.

## Required sequence

### 1. Certify the exact provider and model

The operator supplies already-downloaded Fedora media. The certifier verifies
the OpenPGP-signed checksum and the expected SHA-256 before creating the VM.
It never downloads media.

```bash
cd /var/home/cloudops/code/repos/mikrotik

./hermes-certify-vm.sh \
  --iso /var/home/cloudops/Downloads/Fedora-Server-dvd-x86_64-44-1.7.iso \
  --checksum /var/home/cloudops/Downloads/Fedora-Server-44-1.7-x86_64-CHECKSUM \
  --fedora-keyring /var/home/cloudops/Downloads/fedora.gpg \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --provider openai-codex \
  --model gpt-5.6-luna
```

The expected Server DVD SHA-256 is
`85837793bfa36db6bc709b4cecd2ec116951b87d9c53c3d95eb2fac8dcf7cf1f`.
After the automated reboot and credential-free acceptance gates, the certifier
requires one initial unlock and three ordered reboot-marker, cryptsetup-boundary,
and prompt sequences. It then prints
`ENCRYPTED_REBOOT_EVIDENCE_OK watched_boots=3`, followed by
`AUTHENTICATION_READY provider=<id>` and waits without starting provider
authentication. `START-AUTH` is a readiness response consumed by that running
certifier, not a shell command. For Codex-managed certification sessions, the
operator has authorized Codex to submit this response automatically. Codex
must discard the resulting terminal output and stop reading that terminal; the
operator completes the displayed provider login. This authorization does not
cover credentials, account approval, or production mutation. For
`openai-codex`, Hermes' 15-minute device-login timer begins only after the
response.
The certifier prints `PROMOTION_RECORD=/absolute/path` only after successful
provider authentication, exact `HERMES_OK`, credential revocation, fresh-data
purge, and VM destruction.

### 2. Adopt the reinstalled production host

At the physical console, verify the new SSH ED25519 host fingerprint. Then run:

```bash
cd /var/home/cloudops/code/repos/mikrotik

./hermes-deploy.sh adopt-host \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 \
  --interface eno1
```

Type `ADOPT-HERMES-HOST` when prompted. Adoption records the platform,
machine-id hash, and host-key fingerprint. It archives the legacy
`$HOME/hermes-deploy` directory below the XDG state root instead of deleting it.

### 3. Run the read-only production check

```bash
cd /var/home/cloudops/code/repos/mikrotik

./hermes-deploy.sh check \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 \
  --interface eno1
```

`check` does not create deployment state or mutate the host. It verifies SSH,
administrative inspection, Fedora Server 44, Podman, DNF5, LUKS, Secure Boot,
SELinux, firewalld, networking, storage, listeners, and host identity.

> [!CAUTION]
> Do not continue after `PREFLIGHT_FAILED`, even if an older controller prints
> a trailing “Preflight passed” summary. The root filesystem and listener
> policy have now been corrected, and the full check returned exact
> `PREFLIGHT_OK`. Proceed to deployment only with the matching promotion
> record and the required typed confirmation.

### 4. Deploy with the matching record

```bash
cd /var/home/cloudops/code/repos/mikrotik

./hermes-deploy.sh deploy \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 \
  --interface eno1 \
  --provider openai-codex \
  --model gpt-5.6-luna \
  --promotion-record /absolute/path/to/promotion.record
```

The production run asks for `CONFIRM-HERMES-PRODUCTION` before package
mutation and the planned persistence reboots. DNF5 prepares an offline update;
automatic updates are configured as download-only with no automatic reboot.

## Provider matrix

| Provider | Authentication | Billing | Default model |
| --- | --- | --- | --- |
| `openai-codex` | ChatGPT/Codex device-code OAuth | ChatGPT subscription access | `gpt-5.6-luna` |
| `openai-api` | Secure Hermes API-key prompt | Usage-based OpenAI API billing | `gpt-5.6-luna` |
| `nous` | Nous Portal OAuth | Nous Portal account | `anthropic/claude-sonnet-4.6` |

ChatGPT subscription access and OpenAI API billing are separate products. The
controller has no API-key argument; credentials stay in the terminal and are
excluded from arguments, logs, state, and promotion records.

Every provider/model combination requires a new certification record. To switch
an existing deployment, use `configure-provider` with a fresh matching record.

```bash
./hermes-deploy.sh configure-provider \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 \
  --interface eno1 \
  --provider openai-codex --model gpt-5.6-luna \
  --promotion-record /absolute/path/to/openai-codex.record

./hermes-deploy.sh configure-provider \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 \
  --interface eno1 \
  --provider openai-api --model gpt-5.6-luna \
  --promotion-record /absolute/path/to/openai-api.record

./hermes-deploy.sh configure-provider \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 \
  --interface eno1 \
  --provider nous --model anthropic/claude-sonnet-4.6 \
  --promotion-record /absolute/path/to/nous.record
```

## Gates and recovery

- Provider authentication, API-key entry, OAuth, and the authenticated
  `HERMES_OK` response are explicit operator gates.
- VM certification waits for `START-AUTH` readiness before invoking the
  provider-specific authentication command. Codex submits it automatically in
  a Codex-managed certification terminal under the operator's standing
  preference, then stops reading that terminal.
- A promotion record is valid for 24 hours for first use, exact provider/model,
  exact image, and the fingerprinted repository artifacts.
- A failed production deployment may resume on the same bound host when the
  record inputs are unchanged. A different host requires a new certification.
- `status` reports platform, host identity, update policy, promotion ID,
  provider/model, authentication, image pin, health, and drift without secrets.
- `rollback` restores Hermes and manifest-tracked host configuration. It never
  claims to reverse Fedora RPM or kernel updates.
- `rollback --purge-fresh` removes only installer-created Hermes identity and
  data after its typed confirmation. A successful purge clears stale local
  completion, provider, and promotion-binding markers so the next `deploy`
  takes the full fresh-install path instead of the provider-only resume path.
- `revoke-auth --provider ID` logs out one provider. A successful provider
  switch removes credentials for the other supported providers.

## Verification commands

Run repository checks through Devbox:

```bash
devbox run -- shellspec spec/hermes/ spec/vm/
devbox run -- ./tests/test-hermes-guide.sh
devbox run -- shellcheck hermes-deploy.sh hermes-certify-vm.sh scripts/hermes/*.sh \
  tests/test-hermes-e2e-vm.sh vm/create-hermes-server-vm.sh vm/lib-hermes-luks-console.sh vm/lib-vm-common.sh
devbox run -- shfmt -i 2 -ci -bn -d hermes-deploy.sh hermes-certify-vm.sh \
  scripts/hermes tests/test-hermes-e2e-vm.sh vm/create-hermes-server-vm.sh \
  vm/lib-hermes-luks-console.sh vm/lib-vm-common.sh
devbox run -- markdownlint-cli2 "**/*.md"
```

The official source references are the [Fedora Server download page](https://fedoraproject.org/server/download/),
[DNF5 offline documentation](https://dnf5.readthedocs.io/en/stable/commands/offline.8.html),
[DNF5 automatic-update documentation](https://dnf5.readthedocs.io/en/stable/dnf5_plugins/automatic.8.html),
and [Hermes provider documentation](https://hermes-agent.nousresearch.com/docs/integrations/providers/).
