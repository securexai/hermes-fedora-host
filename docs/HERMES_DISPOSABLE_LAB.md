# Disposable Hermes lab

This is the current **lab** procedure for the pinned Hermes DeepSeek/manual
profile. It uses the same `scripts/hermes/profile-deploy.py` implementation and
gateway digest in `scripts/hermes/manual/manifest.yaml` for every lab run. It
does not deploy to production or promote an artifact. The older M01–M05,
TPM/LUKS, retained-VM and encrypted certifier procedures remain historical or
separate production-candidate work; their dated evidence does not certify this
lab.

The gateway and worker are rootless Podman services under the guest `hermes`
account. The worker has `Network=none` and only a Unix-socket SSH endpoint. The
gateway has no network in synthetic mode. The worker image contains no per-VM
SSH identity; each VM generates a client key, host key and pinned `known_hosts`
entry. The VM's disk is an **unencrypted** qcow2 overlay on a verified Fedora
Cloud base. SELinux must be enforcing. File permissions and the worker split
limit accidental disclosure to the tool environment, but do not protect a
secret from host administrators, a compromised gateway process, or offline
access to unencrypted storage.

## Requirements and commands

On a Fedora host, use libvirt's `qemu:///session`, `virt-install`, `qemu-img`,
`genisoimage`, `gpgv`, Fedora's `distribution-gpg-keys`, `curl`, `ssh`, `scp`,
rootless Podman, and Python 3. The current host's libosinfo lacks a Fedora 44
profile, so the runner uses the compatible `fedora43` metadata profile while
booting a **Fedora 44** Cloud image. The VM gets 4 GiB RAM, 2 vCPUs, a 20 GiB
unencrypted overlay and localhost TCP 22222 forwarded to guest SSH by `passt`.
Free that port first. No host sudo grant or reusable password is needed for
routine tests. The cloud-init `labadmin` account has guest-only passwordless
sudo and a locked password; its per-instance SSH key and the guest host key
are generated automatically. The guest seed is not a reusable base.

Run from the repository root:

```bash
bash scripts/hermes/lab-test.sh test         # routine, network-disabled container
bash scripts/hermes/lab-test.sh status
bash scripts/hermes/lab-test.sh clean        # no persistent routine container

python3 vm/hermes-disposable.py verify-base  # signed Fedora checksum + SHA-256
python3 vm/hermes-disposable.py run          # fresh VM, cloud-init, deploy, checks
python3 vm/hermes-disposable.py status
python3 vm/hermes-disposable.py deploy       # changed source or safe rerun
python3 vm/hermes-disposable.py reboot       # boot ID changes; both services return
python3 vm/hermes-disposable.py fault-test   # stop worker, redeploy, verify repair
python3 vm/hermes-disposable.py clean        # exact owned instance only
python3 vm/hermes-disposable.py clean        # repeat-clean check
```

`verify-base` downloads the Fedora 44 1.7 Cloud Generic qcow2 and signed
checksum once into ignored `.toolbox/hermes-disposable/cache/`, verifies the
signature against the packaged Fedora 44 key and checks the image SHA-256.
The image and checksum are published on the
[official Fedora Cloud download page](https://fedoraproject.org/cloud/download/).
It rechecks both on reuse. `run` starts from that credential-free base, never
from a VM snapshot. It transfers only allowlisted, credential-free deployment
source to the guest. Rootless image layers are reused **within** a VM on warm
deploys; a new VM pulls/builds its own layers. Do not mistake the base-image
cache for a prebuilt application image cache. `clean` retains the verified base
but removes the exact session domain, overlay, seed, and disposable SSH keys.
It refuses changed domain UUIDs, unexpected attached disks, symlinks and
unrecognized instance files. If libvirt cannot be reached, `status` and
`clean` stop with an error; neither reports the VM absent. A failed `run` may
leave an instance to inspect; run `status`, correct the issue, then `deploy`,
or `clean` and start fresh.

The routine test loads the same pinned gateway image with `--network none` and
exercises its actual DeepSeek provider resolver and Telegram callback allowlist.
It sends one completion and one outbound-message request to loopback mock HTTP
services, and checks allow, reject and empty-allowlist fail-closed behavior with
synthetic values. It does not contact real services, receive an authenticated
Telegram message, or certify production. The VM test proves Fedora boot, cloud-init,
key-only and host-key-pinned SSH, rootless systemd startup, enforcing SELinux,
worker isolation, a gateway-to-worker SSH round trip, reboot, and repair after
an injected worker outage. It does not test real provider or bot integration.

## Optional private service smoke

The **host-only** source for dedicated, revocable test credentials is
`~/.local/share/hermes-disposable/private/`, mode 0700, with mode-0600 files.
Run this once in a private host terminal; never paste values into chat, shell
arguments, logs, the repository or a VM seed:

```bash
python3 scripts/hermes/live-smoke.py setup
python3 scripts/hermes/live-smoke.py status
python3 scripts/hermes/live-smoke.py smoke
python3 scripts/hermes/live-smoke.py revoke-local
```

`setup` privately asks for a dedicated DeepSeek key, dedicated Telegram bot
token, authorized test user ID, private chat ID, and whether a **$1 provider-side
cap** was independently verified or is unavailable. To discover the two numeric
IDs without copying them through a third-party bot, send `/start` to the
dedicated bot from the authorized account, then press Enter at the user-ID
prompt. Setup reads that pending private Telegram update, requires its sender
and chat IDs to match, and acknowledges it before the Hermes gateway starts.
It refuses ambiguous pending senders; enter known IDs manually in that case.
The live VM runner separately refuses an active webhook. The program does not
set or verify an account cap. Check that setting in the provider account before
marking it `verified`; current public DeepSeek API documentation establishes
usage accounting and rates, but no account-cap API was verified for this run.
`smoke` makes **at most one** DeepSeek chat-completion POST with 16 output tokens
and **one** outbound Telegram `sendMessage` POST, with no retry. It requires the
private chat ID to equal the authorized user ID. The script runs on the host,
not inside the Hermes gateway; it is an API connectivity smoke, **not** Hermes
end-to-end or authenticated Telegram inbound acceptance. A bot token cannot
manufacture an inbound message from an authorized user. On any failure,
inspect the status code and account settings in a private session; do not print
request URLs or response bodies, since Telegram URLs contain the bot token.

If DeepSeek rejects the key, stop the live VM profile before correcting it:

```bash
python3 vm/hermes-disposable.py live-stop
python3 scripts/hermes/live-smoke.py replace-deepseek
```

`replace-deepseek` privately prompts for a replacement key. It preserves the
dedicated bot and private chat files only when the operator confirms that the
recorded provider-side cap status still applies to the replacement key. If the
key belongs to another account, use `revoke-local` and a fresh `setup` instead.
`KEY=UNCHANGED` means the entered key matched the existing file; create a new
key in the [DeepSeek API platform](https://www.deepseek.com/platform/) before
retrying a provider-authentication failure.
The replacement command does not authenticate the key; run a new bounded
service smoke before another gateway round trip.

`revoke-local` deletes the restricted host files only. Revoke or replace the
DeepSeek key and Telegram bot token at their providers separately; local
deletion is not proof of provider-side revocation. A setup interrupted after
some files are written requires `revoke-local` before a fresh setup. These
host files are never transferred to a reusable VM base or image cache.

### Hermes live gateway round trip

The direct `smoke` above verifies the two APIs separately. To verify Hermes
itself, use a new, otherwise unused test bot and an authorized private chat.
After `setup` and a fresh synthetic VM `run`, use:

```bash
python3 vm/hermes-disposable.py live-start
python3 vm/hermes-disposable.py live-status
# Send one simple message from the authorized Telegram account; observe one reply.
python3 vm/hermes-disposable.py live-stop
python3 vm/hermes-disposable.py clean
```

`live-start` refuses a webhook or pending bot updates, then reads the restricted
host files without placing their values in arguments or output. It stops the
synthetic gateway, disables only the guest's observed `/dev/zram0` swap, mounts
the per-instance gateway state on tmpfs, sends the live profile over pinned
SSH stdin, and starts the same pinned Hermes image with the offline worker.
The guest profile allows only the selected numeric private user ID and sets
the all-users switch to false. Do not send the test message until `LIVE=READY` and a fresh
Telegram connection are confirmed. `live-stop` stops the gateway, unmounts the
guest tmpfs and restores the synthetic profile; `clean` destroys the disposable
VM. The host-only private source remains until `revoke-local`, and provider-side
key/bot revocation must be done separately.

Use only one authorized inbound message in this bounded run. The harness
limits operator-triggered messages but cannot independently enforce or count
the number of internal DeepSeek requests or a gateway retry; the operator's
provider-side $1 cap status is recorded, not set or verified by the script.
Inspect account usage after the run. This test is not a production deployment.
The [2026-09-25 execution record](plans/2026-09-25-hermes-disposable-lab.md)
records a passing direct DeepSeek/Telegram API smoke and an authorized Hermes
gateway round trip: the bot returned the requested marker plus onboarding text.
The user accepted the core round trip; exact-response fidelity was not proven.
The live guest profile and disposable VM were then removed. Gateway-internal
request counts and the operator-reported provider cap were not independently
verified by the harness.

## Retiring the older system VMs

The approved obsolete targets are exactly `lab-hermes-deepseek-e2e-r1` and
`lab-hermes-manual-r1` under `qemu:///system`. Their original guest-agent
teardown cannot remove a guest sudoers file under enforcing SELinux. The
replacement checks their UUIDs, MACs, `fvh-nat`, shut-off state, attachments,
NVRAM, TPM, snapshots, other-domain storage references, file ownership and the
temporary DeepSeek host grant hash before deleting anything. The manual VM's
private boot directory must contain exactly its two attached ISOs, the Fedora
checksum and public keyring, `ks.cfg`, and `guest-password.hash`, each with the
reviewed owner and mode. The script never prints or reads the password hash.
It removes only those six files, the two owned disks, per-VM firmware/TPM state
and the temporary DeepSeek host grant. The disposable session VM and shared
image caches are outside its target set.

Run once in a **private host terminal**; enter the sudo password there only:

```bash
cd /var/home/aicloudopspecial/code/repos/hermes-fedora-host
sudo python3 -I vm/retire-legacy-labs.py --apply
```

`RETIRE=PASS` is the script's post-action absence result; an already-complete
rerun also reports PASS. A `STOP:` line means the script refused a changed
identity, changed file, or partial state. In that case, do not broaden the
target or retry with weaker checks; inspect the exact remaining domains and
files and record a bounded recovery. The script cannot roll back a libvirt
`undefine` that succeeded before a later file deletion failed. The current
execution record distinguishes the earlier PolicyKit denial from actual
cleanup. It records the private result, independent absence checks and any
remaining rerun check.

## Evidence and boundaries

The current execution record is
[2026-09-25-hermes-disposable-lab.md](plans/2026-09-25-hermes-disposable-lab.md).
The recorded fresh run used Fedora Cloud 44 1.7, image SHA-256
`28680fe5b371a5a82ebf43a31926e086a168e59949d03969c5093e7071f90b7f`.
It reached SSH in 14.21 seconds, deployed in 59.32 seconds, and restored both
services after reboot in 15.12 seconds. An unchanged warm deploy reached
`DEPLOY=UNCHANGED` in 1.76 seconds. The main fresh-run cost is guest package
installation and image pull/build; base-image download is cached separately.
The first warm rerun performed one configuration convergence pass and reported
`CHANGED` in 5.51 seconds, then the next rerun reported `UNCHANGED`. These are
observations on this host, not timing guarantees.

Repository offline checks still run inside the `dev-infra-hermes` Toolbox with
`toolbox/run-offline-checks.sh`. They use synthetic fixtures and do not certify
systemd, SELinux, a real provider, Telegram delivery or production. The
encrypted-VM certifier remains a distinct historical/production path and is
not a prerequisite for this unencrypted lab.
