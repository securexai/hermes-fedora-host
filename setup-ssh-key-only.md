# Fedora Server: SSH key access from console setup

Use `setup-ssh-key-only.sh` on a standard Fedora Server with Bash 5+, DNF, systemd,
NetworkManager and firewalld. The original `setup-ssh-server.sh` remains available;
running that original helper afterwards enables password authentication again.

This helper prepares local configuration. Successful workstation login and reboot persistence
are separate acceptance tests. Keep the server console available throughout setup.
Do not run against production without explicit operational authorization.

## Prepare on the workstation

Reuse a suitable existing key, or create a dedicated key with a passphrase when prompted:

```bash
test ! -e ~/.ssh/id_ed25519_fedora && test ! -e ~/.ssh/id_ed25519_fedora.pub &&
  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_fedora
ssh-keygen -lf ~/.ssh/id_ed25519_fedora.pub
```

Never overwrite an existing key. Transfer only the `.pub` file using removable media or the
server console. The private key stays on the workstation. See
[Fedora cryptography guidance](https://fedoraproject.org/wiki/Cryptography).

## Verify the fresh server

At its console, log in to the intended non-root account:

```bash
whoami
cat /etc/fedora-release
ip -br address
```

Examples below use `aicowork`, `10.0.30.10`, `enp1s0`, and `FedoraServer`.
Verify the account and address against this installation; obtain the actual interface and zone
from the server. For this repository's `aicowork`, complete the documented sudo-password rotation
after the terminal-echo incident before privileged operator work.

If `ssh-keygen` is unavailable, install `openssh-clients` at the console before using the helper.
The helper validates the supplied key before its own package installation. Compare fingerprints:

```bash
ssh-keygen -lf /tmp/aicowork.pub
```

If firewalld is running, inspect its management interface association:

```bash
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --get-zone-of-interface=enp1s0
sudo firewall-cmd --zone=FedoraServer --list-all
nmcli -g GENERAL.CON-UUID device show enp1s0
```

For an inactive firewall, its live association is checked after startup during apply.
The explicit zone must also agree with the persistent interface assignment, or the NetworkManager
connection's `connection.zone` (the permanent default zone when that property is empty).
An exact `no zone` response (including firewalld exit code 2) uses that NetworkManager fallback;
other query failures stop validation.
The script never changes zone assignments or chooses the first active zone.

## Preview and apply

Place the script on the server, then run at the console:

```bash
sudo bash ./setup-ssh-key-only.sh \
  --user aicowork \
  --public-key-file /tmp/aicowork.pub \
  --interface enp1s0 \
  --zone FedoraServer \
  --dry-run
```

The dry run performs read-only checks, including candidate effective SSH settings when sshd is
installed. It creates no files, installs no packages, generates no host keys and changes no services
or firewall state. Missing packages and inactive firewall checks are deferred until apply.
If existing sshd cannot evaluate the candidate, the preview fails without changing anything.

Apply with the same command after removing `--dry-run`. The helper:

1. Installs the required OpenSSH, firewalld and SELinux utilities with DNF.
2. Preserves existing authorized entries, appending a single validated public key when absent.
   Existing restrictions on the same key remain in effect; a restricted key is never supplemented
   with an unrestricted duplicate. It sets `.ssh` to `0700`, `authorized_keys` to `0600`, assigns
   the selected account ownership and restores SELinux labels on those two paths.
3. Writes only `/etc/ssh/sshd_config.d/00-local-key-only.conf`, owned by root with mode `0644`:

   ```text
   PubkeyAuthentication yes
   AuthenticationMethods publickey
   PasswordAuthentication no
   KbdInteractiveAuthentication no
   PermitRootLogin no
   ```

4. Generates missing host keys without replacing existing keys. Runs `sshd -t` and verifies the
   five effective authentication values, port 22 and the standard authorized-key destination.
5. Allows the SSH service in the selected zone, both immediately and permanently, then verifies both.
6. Enables sshd at boot, reloading an already active daemon or starting an inactive one.
   Checks that sshd is active and enabled.

No firewall reload is needed because both configurations are updated explicitly. This allowance
covers traffic handled by the zone; it is not limited to a single workstation.
See [firewalld command semantics](https://firewalld.org/documentation/man-pages/firewall-cmd.html).

## Supported configuration and failure recovery

The helper targets a fresh installation. It refuses conditional `Match` configuration, nonstandard
includes, unreviewed service overrides, socket activation, nonstandard key-file locations or ports, source-based
zones, selected-zone rich rules/custom ports, direct rules, and custom policies. The stock
`allow-host-ipv6` policy is accepted only when every effective field matches its standard definition.
The five shipped `gateway` policy-set members are accepted only when each reports administratively
disabled in both runtime and permanent configuration. Enabled or unreadable gateway policies and
unknown policies still require review. See [firewalld policy sets](https://firewalld.org/documentation/man-pages/firewalld.policy-sets.html).
It accepts the standard Fedora SSH drop-in include and the crypto-policy include in `50-redhat.conf`
or Fedora 44's `40-redhat-crypto-policies.conf`; the target must be the standard
`/etc/crypto-policies/back-ends/opensshserver.config`. See the
[Fedora 44 OpenSSH package](https://packages.fedoraproject.org/pkgs/openssh/openssh-server/fedora-44.html).
The sole accepted systemd service drop-in is
`/usr/lib/systemd/system/service.d/10-timeout-abort.conf`, with exactly `[Service]` and
`TimeoutStopFailureMode=abort` after removing comments, blank lines and surrounding whitespace.
This inherited [Fedora timeout policy](https://fedoraproject.org/wiki/Changes/Shorter_Shutdown_Timer)
does not configure SSH authentication. Additional drop-ins or changed
contents require manual review. Do not delete or mask the Fedora timeout policy to bypass the check.
In `/etc/sysconfig/sshd`, the helper accepts only blank lines, full-line `#`/`;` comments and explicit
empty assignments (`OPTIONS=`, `OPTIONS=""`, or `OPTIONS=''`), with optional surrounding whitespace.
It preserves this file and never evaluates it as shell code. Nonempty options, other variables and
other syntax require manual review; do not delete existing settings to bypass that review.
The main SSH configuration and forwarding options are preserved. Effective conflicts cause failure;
the script does not rewrite unrelated configuration to overcome them. OpenSSH uses the first
obtained value for most settings: see [sshd_config](https://man.openbsd.org/sshd_config).

Run with the selected account idle and no concurrent edits to SSH/firewall configuration.
Symlinks anywhere in destination paths and hard-linked destination files are refused.
The read-only crypto-policy input has one exception: a direct absolute symlink from
`/etc/crypto-policies/back-ends/opensshserver.config` to
`/usr/share/crypto-policies/DEFAULT/opensshserver.txt`. The link must be root-owned, and its parent
directories, target and target ancestors must be root-owned and not group/world writable; other
symlinks along those paths are refused. The regular packaged target may have hard links because it
is read-only input; managed destination files still require a single link. The helper never changes that policy
file or symlink. This matches the [documented crypto-policy layout](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/security_hardening/using-system-wide-cryptographic-policies).
The home must belong to the account and must not be group/world writable. This console helper
does not coordinate concurrent administrators or an actively hostile account changing its home.
It does not audit arbitrary nftables rules, PAM account policy, account expiration, or external network
filters. These may still prevent login; local validation is not proof of remote reachability.

Before managed changes, the helper records the prior drop-in and authorized-key contents/metadata,
`.ssh` ownership/mode/SELinux context, service activation/enablement and firewall allowances in a
root-only directory under `/var/tmp/ssh-key-only.*`, outside SSH includes. Failure or a handled
INT/TERM/HUP restores those managed files, metadata, services and allowances. Existing firewall SSH
allowances are preserved. Failed restoration is reported explicitly; recovery files remain for console
inspection. Successful runs remove their temporary recovery directory.

Installed packages and newly generated host keys remain after rollback and are reported. SIGKILL,
power loss and concurrent configuration changes cannot be recovered automatically. Use the saved
files and `state` record from the console; validate restored SSH configuration before reloading it.
The account password remains usable for console login and sudo.

## Workstation acceptance

At the server console, display the public host-key fingerprint:

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Compare it with the fingerprint offered by the workstation connection. A reinstall can change the
host key: verify through the console before replacing any saved host entry.

```bash
ssh -o ControlPath=none \
  -o IdentitiesOnly=yes \
  -o PreferredAuthentications=publickey \
  -i ~/.ssh/id_ed25519_fedora \
  aicowork@10.0.30.10
```

`ControlPath=none` tests a new connection. A private-key passphrase prompt is normal.
See [SSH client options](https://man.openbsd.org/ssh_config).

Test that account-password authentication is rejected, without a password prompt:

```bash
ssh -o ControlPath=none \
  -o PubkeyAuthentication=no \
  -o PreferredAuthentications=password,keyboard-interactive \
  aicowork@10.0.30.10
```

For disposable Fedora acceptance, also verify SELinux is `Enforcing`, reject root login, compare
unrelated SSH/firewall settings before and after, and repeat the helper to check idempotency.
For a meaningful root test, install a disposable public key for root in the isolated fixture before
the trial and attempt root authentication with that key; a missing root key alone is insufficient
evidence that `PermitRootLogin no` is enforced. Never provision such a test key on production.

Reboot persistence remains a separate gate. Schedule and authorize the test reboot explicitly,
retain console access, then verify a fresh key login after boot along with `systemctl is-active sshd`
and `systemctl is-enabled sshd`. This helper never reboots the server.

## Maintainer verification

From the preparation repository:

```bash
bash -n setup-ssh-key-only.sh
shellcheck setup-ssh-key-only.sh
shfmt -d -l -i 2 -ci -bn setup-ssh-key-only.sh
python3 -m unittest discover -s tests -p test_ssh_key_only.py
```

Offline tests run redirected copies in temporary directories with real public-key validation and mocked
services/firewall/sshd. They do not establish real Fedora, SELinux, remote-login or reboot acceptance.
