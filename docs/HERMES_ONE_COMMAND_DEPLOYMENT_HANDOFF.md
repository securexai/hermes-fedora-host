# Hermes one-command deployment handoff

This handoff describes the production interface for a dedicated Fedora Server
44 Hermes appliance. The controller is
[`hermes-deploy.sh`](../hermes-deploy.sh); the disposable certification
interface is [`hermes-certify-vm.sh`](../hermes-certify-vm.sh).

The new [unattended release profile](HERMES_UNATTENDED_DEPLOYMENT.md) has a separate enrollment and
certification contract. It is not yet production-certified. The interactive procedure below remains
the historical operational interface; its records do not authorize the new source tree.

## Safety contract

- Production deployment requires a fresh promotion record from a passing
  `lab-hermes-server` VM.
- The record must match the exact provider, model, pinned Hermes image, and
  repository artifact fingerprint.
- First production use binds the record to the target SSH ED25519 fingerprint
  and machine-id hash. A different host cannot reuse it.
- The certifier issues no record until authenticated `HERMES_OK`, credential
  revocation, fresh-data purge, and VM destruction succeed.
- Production package mutation and planned reboots require typed
  `CONFIRM-HERMES-PRODUCTION` confirmation.
- Provider OAuth, API-key entry, and final authenticated inference remain
  interactive gates. Credentials never appear in shell arguments, logs, state,
  or records.

## Current promotion state

Final-source disposable run `run-20260901T183122Z` passed every certification
and cleanup gate. Its strict-valid, mode-`0600` record is
`/var/home/cloudops/.local/state/hermes-certification/promotion-20260901T183122Z.record`.
The previous production installation was removed with `rollback --purge-fresh`.
The record matches the final artifact fingerprint and authorized the fresh
deployment to `aicowork@10.0.30.10`. The controller is closed, provider
authentication is ready, and the direct status reports `health=healthy`,
`readonly=true`, `ports={}`, and `drift=none`. Historical failed certification
and bootstrap attempts remain in the evidence ledger; they are not current
deployment blockers.

## Public command grammar

```text
./hermes-deploy.sh [deploy|configure-provider|check|status|rollback|revoke-auth|adopt-host] [options]
```

Common options are `--target USER@HOST`, `--identity-file PATH`,
`--management-cidr CIDR`, and `--interface NAME`. `deploy` and
`configure-provider` also accept `--provider ID`, `--model ID`, and
`--promotion-record PATH`.

| Command | Purpose |
| --- | --- |
| `deploy` | Install, resume, or converge the managed Hermes service. |
| `configure-provider` | Authenticate and switch the provider/model using a fresh record. |
| `check` | Run read-only local and remote preflight. |
| `status` | Show platform, host identity, promotion, provider, health, image, and drift. |
| `rollback` | Restore Hermes and manifest-tracked host configuration. |
| `revoke-auth` | Log out one selected provider. |
| `adopt-host` | Bind a reinstalled host and archive legacy local state. |

The local state directory is
`${XDG_STATE_HOME:-$HOME/.local/state}/hermes-deploy`.

## Certification command

Use the official Fedora Server 44 x86_64 DVD already present on the workstation:

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

The certifier verifies the signed checksum and expected SHA-256
`85837793bfa36db6bc709b4cecd2ec116951b87d9c53c3d95eb2fac8dcf7cf1f`, creates
an 8 GiB, 2-vCPU, 40 GiB LUKS/Secure Boot Server VM at `172.16.99.12`, runs
the complete provider acceptance, revokes all supported providers, purges
fresh data, destroys the VM, and prints `PROMOTION_RECORD=/absolute/path`.

After all automated reboot and credential-free acceptance gates, certification
first requires `ENCRYPTED_REBOOT_EVIDENCE_OK watched_boots=3`, then prints
`AUTHENTICATION_READY provider=<id>` and waits. The evidence contains one
initial unlock plus three ordered sequences of an explicit reboot marker, the
encrypted-root cryptsetup boundary, and one prompt submission. These represent
the offline transaction, post-update, and persistence boots. Missing,
duplicate, cross-boot, or out-of-order evidence fails closed before OAuth and
is checked again before promotion. `START-AUTH` is a readiness response
consumed by that running certifier, not a shell command. When Codex owns the
managed certification terminal, the operator's standing preference authorizes
Codex to submit it automatically, suppress the write result, and stop reading
that terminal. The operator still completes the provider login. Otherwise,
enter it directly into the waiting certifier. Provider authentication—and the
15-minute `openai-codex` device-login window—starts only after this readiness
confirmation.

## Progress evidence

Use [`HERMES_INSTALLATION_VERIFICATION.md`](HERMES_INSTALLATION_VERIFICATION.md)
as the chronological evidence ledger and
[`vm/DEPLOYMENT_TASKS.md`](../vm/DEPLOYMENT_TASKS.md) as the executable task
list. Each task defines its command, pass condition, and durable evidence
filename. Offline command logs belong under a timestamped `progress-*`
directory in the certification state root. VM logs belong under the certifier's
`run-*` directory.

Do not capture the interactive provider terminal with `tee` or `script`.
Authentication output may contain an OAuth URL, device code, or credential
prompt. Progress is established from sanitized certifier artifacts, exact
acceptance markers, cleanup evidence, and the secret-free promotion record.

## Production sequence

### Adopt the reinstalled host

Verify the new host ED25519 fingerprint at the physical console first:

```bash
./hermes-deploy.sh adopt-host \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 \
  --interface eno1
```

Type `ADOPT-HERMES-HOST`. The command records a hash of `/etc/machine-id` and
the host ED25519 public-key fingerprint. It moves legacy `$HOME/hermes-deploy`
state to a timestamped archive under the XDG state root.

### Check without mutation

```bash
./hermes-deploy.sh check \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 \
  --interface eno1
```

The check verifies Fedora Server 44, DNF5, Podman, SSH/sudo inspection,
LUKS, Secure Boot, SELinux, firewalld, cgroup v2, storage, networking,
listeners, and host state. It creates no deployment state.

> [!CAUTION]
> Require exact `PREFLIGHT_OK` before deployment. `PREFLIGHT_FAILED` remains a
> failure even if an older controller prints a trailing success summary. The
> production root filesystem must provide at least 20 GiB free under `/var`,
> and all non-loopback listeners must be approved by the host policy.

### Deploy with the record

```bash
./hermes-deploy.sh deploy \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 \
  --interface eno1 \
  --provider openai-codex \
  --model gpt-5.6-luna \
  --promotion-record /absolute/path/to/promotion.record
```

On Fedora hosts with TTY-scoped sudo timestamps, the read-only preflight and
the temporary helper bootstrap can each request the operator's sudo password.
The repaired controller permits the bootstrap prompt inside the same SSH TTY;
do not run a separate `sudo` command to prime another terminal. If the
controller reports `sudo: a password is required` immediately after the four
artifact checksum lines, stop: that controller is not eligible for production.

The controller prepares a DNF5 offline update, performs the planned reboot
gates, configures download-only `dnf5-automatic` with `apply_updates=False` and
`reboot=never`, installs the pinned image, and checks runtime persistence.

## Provider choices

| Provider | Authentication | Billing | Default model |
| --- | --- | --- | --- |
| `openai-codex` | ChatGPT/Codex device-code OAuth | ChatGPT subscription | `gpt-5.6-luna` |
| `openai-api` | Hermes masked API-key prompt | OpenAI API usage | `gpt-5.6-luna` |
| `nous` | Nous Portal OAuth | Nous Portal account | `anthropic/claude-sonnet-4.6` |

ChatGPT subscription access does not include OpenAI API usage credits. The
controller intentionally has no `--api-key` argument. A provider switch must
use a fresh certification record for the exact provider/model.

```bash
./hermes-deploy.sh configure-provider \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 --interface eno1 \
  --provider openai-codex --model gpt-5.6-luna \
  --promotion-record /absolute/path/to/openai-codex.record

./hermes-deploy.sh configure-provider \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 --interface eno1 \
  --provider openai-api --model gpt-5.6-luna \
  --promotion-record /absolute/path/to/openai-api.record

./hermes-deploy.sh configure-provider \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 --interface eno1 \
  --provider nous --model anthropic/claude-sonnet-4.6 \
  --promotion-record /absolute/path/to/nous.record
```

After a successful switch, the controller verifies provider status, exact
provider/model, service health, and `HERMES_OK`, then logs out the other
supported providers. If switching fails, it restores the previous provider,
model, and credentials.

## Channel integrations

Telegram bot token and user access configuration is documented in
[`HERMES_TELEGRAM_BOT_GUIDE.md`](HERMES_TELEGRAM_BOT_GUIDE.md). Environment
variables (`TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USERS`) are managed in
the host data path at `/home/hermes/data/.env`.

## Maintenance and rollback

```bash
./hermes-deploy.sh status \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 --interface eno1

./hermes-deploy.sh revoke-auth --provider openai-api \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 --interface eno1

./hermes-deploy.sh rollback \
  --target aicowork@10.0.30.10 \
  --identity-file /var/home/cloudops/.ssh/id_ed25519_cloudops \
  --management-cidr 192.168.99.0/24 --interface eno1
```

Rollback restores Hermes and manifest-tracked host configuration. It does not
reverse Fedora package or kernel updates. Keep physical console recovery
available for storage and boot incidents.

Use `--purge-fresh` only when intentionally replacing an installer-created
Hermes instance. It requires `PURGE-HERMES-FRESH`, removes that identity and
data, and clears stale local deployment completion and promotion-binding state.
The next `deploy` therefore performs a full installation.

## Verification

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

The [Fedora Server download page](https://fedoraproject.org/server/download/),
[DNF5 offline documentation](https://dnf5.readthedocs.io/en/stable/commands/offline.8.html),
[DNF5 automatic documentation](https://dnf5.readthedocs.io/en/stable/dnf5_plugins/automatic.8.html),
and [Hermes provider documentation](https://hermes-agent.nousresearch.com/docs/integrations/providers/)
are the external references for the implementation.
