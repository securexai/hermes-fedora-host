#!/usr/bin/env bash
# Provision the gateway-side worker client key before M02.
#
# Run as root on the Hermes host:
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/provision-worker-client-key.sh
#
# M02 does not create this key, and on a clean install nothing else does either:
# m02-deploy-and-validate.sh stops with "STOP: worker client key missing". Run
# this helper first.
#
# Rerun-safe:
#   * an existing private key is never regenerated or overwritten;
#   * a missing public key is rebuilt from the private key;
#   * modes and ownership are re-asserted on every run.
# Only the public-key fingerprint is printed; private key material never is.
#
# This is an action script: it relies on `set -e` to fail closed and prints its
# result, rather than running the verification helpers' CHECK accounting. The
# ownership order below is load-bearing and asserted by the clean-install
# rehearsal, so do not reorder it.
#
# provision_worker_client_key() has no side effects at source time, so the clean
# install rehearsal can exercise it in a temporary directory.
set -o errexit
set -o nounset
set -o pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib-manual-common.sh
. "$HERE/lib-manual-common.sh" || {
  printf 'STOP: cannot load %s/lib-manual-common.sh (stage the whole manual/ tree)\n' "$HERE" >&2
  exit 1
}

GW_ACCOUNT="${HERMES_GATEWAY_ACCOUNT:-hermes}"
KEYDIR="${HERMES_GATEWAY_SSH_DIR:-/home/${GW_ACCOUNT}/gateway-ssh}"
GW_UID="${HERMES_GATEWAY_UID:-10000}"

# provision_worker_client_key KEYDIR
#
# Create KEYDIR/worker_client_ed25519 and its .pub when absent, rebuild the
# public key from an intact private key, and pin the modes the gateway needs
# (0600 private, 0644 public). An existing private key is preserved. Returns
# non-zero when a private key exists but cannot yield a public key.
provision_worker_client_key() {
  local keydir="$1"
  local key="$keydir/worker_client_ed25519"
  local pub="$key.pub"
  local tmp

  install -d -m 0711 "$keydir"

  if [ -e "$key" ] && [ ! -f "$key" ]; then
    printf 'STOP: %s exists but is not a regular file.\n' "$key" >&2
    return 1
  fi

  if [ ! -f "$key" ]; then
    ssh-keygen -q -t ed25519 -N '' -C 'hermes-worker-client' -f "$key"
    printf 'generated new worker client key\n'
  else
    printf 'existing worker client key preserved\n'
  fi

  if [ ! -s "$pub" ]; then
    tmp=$(mktemp "$keydir/.worker_client_ed25519.pub.XXXXXX")
    # -P '' keeps this non-interactive: the gateway uses the key without a
    # passphrase, so a protected key must fail closed rather than prompt.
    if ! ssh-keygen -y -P '' -f "$key" >"$tmp" 2>/dev/null || [ ! -s "$tmp" ]; then
      rm -f "$tmp"
      printf 'STOP: cannot rebuild the public key from %s\n' "$key" >&2
      return 1
    fi
    mv -f "$tmp" "$pub"
    printf 'rebuilt missing public key from the existing private key\n'
  else
    printf 'existing public key preserved\n'
  fi

  chmod 0600 "$key"
  chmod 0644 "$pub"
}

# Run a command with the runtime account's environment. Mirrors the `h`
# convenience function in the deployment guide and m02-deploy-and-validate.sh.
as_hermes() {
  local runtime_uid
  runtime_uid=$(id -u "$GW_ACCOUNT")
  sudo -u "$GW_ACCOUNT" -- env -i --chdir="/home/$GW_ACCOUNT" \
    HOME="/home/$GW_ACCOUNT" USER="$GW_ACCOUNT" LOGNAME="$GW_ACCOUNT" \
    PATH=/usr/local/bin:/usr/bin:/bin TERM="${TERM:-xterm}" \
    XDG_RUNTIME_DIR="/run/user/$runtime_uid" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$runtime_uid/bus" \
    TMPDIR="/home/$GW_ACCOUNT/.cache/podman-tmp" "$@"
}

main() {
  local key="$KEYDIR/worker_client_ed25519"

  if [ "$(id -u)" -ne 0 ]; then
    printf 'STOP: run as root on the Hermes host.\n' >&2
    exit 1
  fi
  mp_require_host_identity
  # Worker-key provisioning mutates the same profile as deployment, so it takes
  # the one profile lock. The sourceable provision_worker_client_key() function
  # stays lock-free so the clean-install rehearsal can exercise it directly.
  mp_lock_profile
  if ! mountpoint -q "/home/$GW_ACCOUNT"; then
    printf 'STOP: /home/%s is not mounted.\n' "$GW_ACCOUNT" >&2
    exit 1
  fi
  if ! id -u "$GW_ACCOUNT" >/dev/null 2>&1; then
    printf 'STOP: runtime account %s does not exist.\n' "$GW_ACCOUNT" >&2
    exit 1
  fi

  provision_worker_client_key "$KEYDIR" || exit 1

  # Hand the whole tree to the runtime account first, including the private key.
  # ssh-keygen ran as root, and rootless Podman cannot chown a root-owned inode
  # from inside the account's user namespace, so the private key must already be
  # owned by that account before the mapped-UID chown below -- which is the
  # ownership state m02-deploy-and-validate.sh starts from.
  chown "$GW_ACCOUNT:$GW_ACCOUNT" "$KEYDIR" "$key" "$key.pub"
  as_hermes podman unshare chown "$GW_UID:$GW_UID" "$key"

  ssh-keygen -lf "$key.pub"
  printf 'worker client key ready: %s\n' "$key"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
