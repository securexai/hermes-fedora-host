#!/usr/bin/env bash
# M02 deploy and validate: offline worker transport, enforcement shims, Quadlets.
#
# Default is inspect-only. Re-run with --apply to make changes:
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/m02-deploy-and-validate.sh --apply
#
# Idempotent: existing trust material is preserved, never regenerated or
# overwritten. An existing pinned host key that disagrees with the persistent
# worker host key is a hard stop: rotating trust is a deliberate operation, not
# a side effect of re-running this helper.
#
# Negative tests run against a disposable copy of the client material, so the
# live, privately labelled pin is never edited or relabelled.
#
# Identity note: the gateway image's main-wrapper.sh drops the user command to
# its `hermes` user (UID 10000) with s6-setuidgid. Every gateway-side file is
# therefore tested for readability as UID 10000, not root.
set -u
set -o pipefail
export LC_ALL=C

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib-manual-common.sh
. "$HERE/lib-manual-common.sh" || {
  printf 'STOP: cannot load %s/lib-manual-common.sh (stage the whole manual/ tree)\n' "$HERE" >&2
  exit 1
}

mp_parse_mode "$@"
mapfile -t MP_ARGS < <(mp_positionals "$@")
BUNDLE="${MP_ARGS[0]:-$HERE}"
[ -d "$BUNDLE" ] || mp_die "bundle directory not found: $BUNDLE"

ADMIN_ACCOUNT=$(mp_admin_account)
ADMIN_HOME=$(mp_admin_home)
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m02-deploy.out")
HERMES_UID=$(id -u hermes)
GW_IMAGE=docker.io/nousresearch/hermes-agent@sha256:fca358f12efd65bfaaca05884166f15c0e2788375ca30d77061ac1ebc96452b7
BUILD=/home/hermes/.cache/hermes-m02-build
BUILD_STAMP=/home/hermes/.cache/hermes-m02-build.sha256
CLIENT_DIR=/home/hermes/.cache/hermes-m02-client
GWSSH=/home/hermes/gateway-ssh
TRANSPORT=/home/hermes/transport
WSTATE=/home/hermes/worker-state
QUADLET_DIR=/etc/containers/systemd/users/$HERMES_UID
WORKER_NAME=hermes-worker
GW_UID=10000

mp_require_apply 'would build the worker image, install the shims and Quadlets, and restart the worker unit'
mp_require_host_identity
mp_lock_profile
mp_install_trap
mp_require_tools podman ssh-keygen

h() {
  if ! mountpoint -q /home/hermes; then
    printf 'STOP: /home/hermes is not mounted.\n' >&2
    return 1
  fi
  sudo -u hermes -- env -i --chdir=/home/hermes \
    HOME=/home/hermes USER=hermes LOGNAME=hermes PATH=/usr/local/bin:/usr/bin:/bin \
    TERM="${TERM:-xterm}" XDG_RUNTIME_DIR="/run/user/$HERMES_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$HERMES_UID/bus" \
    TMPDIR=/home/hermes/.cache/podman-tmp "$@"
}

# Run the pinned gateway image as a throwaway, network-less process under the
# SAME identity the real gateway uses for ssh/scp (UID 10000), against the
# disposable copy of the client material.
gclient() {
  entry="$1"
  shift
  h podman run --rm --network none --user "$GW_UID:$GW_UID" --entrypoint "$entry" \
    -v "$TRANSPORT":/run/hermes-transport:z \
    -v "$CLIENT_DIR":/opt/hermes/gateway-ssh:ro,Z \
    -v "$CLIENT_DIR/ssh":/opt/hermes/bin/ssh:ro,Z \
    -v "$CLIENT_DIR/scp":/opt/hermes/bin/scp:ro,Z \
    -v "$CLIENT_DIR/sftp":/opt/hermes/bin/sftp:ro,Z \
    "$GW_IMAGE" "$@"
}

# The prior state must be conclusive before the gateway is stopped: a transient
# query failure cannot be restored by the hook, so it must not authorize the
# stop (C2).
gw_prior_known=1
gw_prior=$(mp_capture_service_state h hermes-gateway.service) || gw_prior_known=0

# Runs from the EXIT/INT/TERM trap as well as at the normal end, so an early
# `exit` or an interrupt still restarts a gateway this helper stopped. It is
# idempotent: it acts only when the current state differs from the prior state.
restore_gateway_state() {
  local now rc=0
  now=$(h systemctl --user is-active hermes-gateway.service 2>/dev/null || true)
  if [ "$gw_prior" = "active" ] && [ "$now" != "active" ]; then
    printf 'restoring gateway service state (prior=active, now=%s)\n' "$now"
    if ! h systemctl --user start hermes-gateway.service; then
      printf 'RESTORE_FAILED gateway service was active before this run and could not be restarted\n' >&2
      rc=1
    fi
  fi
  printf 'gateway_state_at_exit=%s\n' "$(h systemctl --user is-active hermes-gateway.service 2>/dev/null || true)"
  return "$rc"
}
mp_on_cleanup restore_gateway_state

# sha256 of all worker build inputs, so an unchanged re-run can skip the build.
build_inputs_hash() {
  sha256sum "$BUNDLE"/worker/* 2>/dev/null \
    | sha256sum | cut -d' ' -f1
}

rc=0
{
  echo "### M02 deploy and validate"
  echo "### generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "### apply=$MP_APPLY bundle=$BUNDLE"
  echo

  echo "===== bundle sanity ====="
  missing=0
  for f in worker/Containerfile worker/sshd_worker_config worker/worker-entrypoint \
    worker/worker-socket-adapter worker/worker-sshd-inetd \
    gateway/ssh gateway/scp gateway/sftp gateway/unix-bridge.py \
    quadlets/hermes-worker.container quadlets/hermes-gateway.container; do
    if [ -r "$BUNDLE/$f" ]; then
      echo "ok        $f"
    else
      echo "MISSING   $f"
      missing=$((missing + 1))
    fi
  done
  if [ "$missing" -eq 0 ]; then
    mp_check bundle_complete PASS
  else
    mp_check bundle_complete FAIL "$missing required file(s) missing"
    exit 1
  fi
  echo

  echo "===== directories ====="
  install -d -o hermes -g hermes -m 0711 "$GWSSH" "$TRANSPORT" \
    "$WSTATE" "$WSTATE/home" "$WSTATE/ssh-host-keys" "$WSTATE/authorized_keys"
  dir_rc=$?
  mp_check runtime_directories "$([ "$dir_rc" -eq 0 ] && echo PASS || echo FAIL)" \
    "install -d rc=$dir_rc"
  [ "$dir_rc" -eq 0 ] || exit 1
  # $TRANSPORT must be traversable by the gateway's UID 10000 to reach the
  # socket; it holds only the socket, and /home/hermes (0700) bounds the host.
  chmod 0711 "$TRANSPORT"
  echo

  echo "===== worker client key (gateway side) ====="
  if [ -f "$TRANSPORT/keys/worker_client_ed25519" ] && [ ! -f "$GWSSH/worker_client_ed25519" ]; then
    mv "$TRANSPORT/keys/worker_client_ed25519" "$GWSSH/worker_client_ed25519"
    mv "$TRANSPORT/keys/worker_client_ed25519.pub" "$GWSSH/worker_client_ed25519.pub"
  fi
  rmdir "$TRANSPORT/keys" 2>/dev/null || true
  if [ ! -f "$GWSSH/worker_client_ed25519" ]; then
    mp_check worker_client_key FAIL "run provision-worker-client-key.sh first"
    echo "STOP: worker client key missing"
    exit 1
  fi
  chown hermes:hermes "$GWSSH/worker_client_ed25519.pub"
  chmod 0644 "$GWSSH/worker_client_ed25519.pub"
  install -o hermes -g hermes -m 0644 "$GWSSH/worker_client_ed25519.pub" "$WSTATE/authorized_keys/worker"
  ssh-keygen -lf "$GWSSH/worker_client_ed25519.pub"
  mp_check worker_client_key PASS
  echo

  echo "===== worker host key (worker only, persistent) ====="
  if [ ! -f "$WSTATE/ssh-host-keys/ssh_host_ed25519_key" ]; then
    ssh-keygen -q -t ed25519 -N '' -C 'hermes-worker-host' \
      -f "$WSTATE/ssh-host-keys/ssh_host_ed25519_key"
    echo "generated new worker host key"
  else
    echo "existing worker host key preserved"
  fi
  chown hermes:hermes "$WSTATE"/ssh-host-keys/ssh_host_ed25519_key*
  chmod 0600 "$WSTATE/ssh-host-keys/ssh_host_ed25519_key"
  chmod 0644 "$WSTATE/ssh-host-keys/ssh_host_ed25519_key.pub"
  ssh-keygen -lf "$WSTATE/ssh-host-keys/ssh_host_ed25519_key.pub"
  echo

  echo "===== pinned known_hosts (never silently replaced) ====="
  PINNED_LINE="worker $(cat "$WSTATE/ssh-host-keys/ssh_host_ed25519_key.pub")"
  if [ -f "$GWSSH/known_hosts" ]; then
    if [ "$(cat "$GWSSH/known_hosts")" = "$PINNED_LINE" ]; then
      echo "existing pin matches the persistent worker host key"
      mp_check known_hosts_pin PASS "existing pin verified"
    else
      mp_check known_hosts_pin FAIL "existing pin does not match the persistent worker host key"
      echo "STOP: refusing to overwrite an established trust pin."
      echo "      Rotate deliberately: provision-worker-client-key.sh, then update the pin by hand."
      exit 1
    fi
  else
    printf '%s\n' "$PINNED_LINE" >"$GWSSH/known_hosts"
    echo "created the initial pin"
    mp_check known_hosts_pin PASS "initial pin created"
  fi
  chown hermes:hermes "$GWSSH/known_hosts"
  chmod 0644 "$GWSSH/known_hosts"
  echo

  echo "===== install gateway shims and bridge ====="
  for shim in ssh scp sftp unix-bridge.py; do
    result=$(mp_install_reconcile "gateway_shim_${shim//[.-]/_}" 0755 hermes:hermes \
      "$BUNDLE/gateway/$shim" "$GWSSH/$shim") || exit 1
    echo "$result"
  done
  chown hermes:hermes "$GWSSH/worker_client_ed25519.pub"
  # The gateway's user command runs as hermes UID 10000, which must traverse the
  # directory; host-side protection is the 0700 /home/hermes parent.
  chmod 0711 "$GWSSH"
  chmod 0644 "$GWSSH/known_hosts" "$GWSSH/worker_client_ed25519.pub"
  # OpenSSH refuses a group/world-readable private key, so it must be owned by
  # the container's mapped UID 10000 at mode 0600. chown happens inside the
  # rootless user namespace, which maps 10000 -> the subordinate range.
  h podman unshare chown "$GW_UID:$GW_UID" "$GWSSH/worker_client_ed25519"
  echo "key_local_chown_rc=$?"
  chmod 0600 "$GWSSH/worker_client_ed25519"
  ls -lanZ "$GWSSH"
  echo

  echo "===== disposable client copy for one-shot containers ====="
  # A one-shot container must not relabel the live private mount, so it mounts a
  # copy instead. Ownership of the private key (mapped UID 10000) is preserved by
  # cp -a, which is why the copy still authenticates.
  rm -rf "$CLIENT_DIR"
  install -d -o hermes -g hermes -m 0711 "$CLIENT_DIR"
  cp -a "$GWSSH/ssh" "$GWSSH/scp" "$GWSSH/sftp" "$GWSSH/unix-bridge.py" \
    "$GWSSH/known_hosts" "$GWSSH/worker_client_ed25519" "$CLIENT_DIR/"
  chmod 0711 "$CLIENT_DIR"
  chmod 0600 "$CLIENT_DIR/worker_client_ed25519"
  ls -lanZ "$CLIENT_DIR"
  echo

  echo "===== worker image (convergent: rebuild only on changed inputs) ====="
  rm -rf "$BUILD"
  install -d -o hermes -g hermes -m 0700 "$BUILD"
  cp "$BUNDLE"/worker/* "$BUILD"/
  chown -R hermes:hermes "$BUILD"
  want_build_hash=$(build_inputs_hash)
  if h podman image inspect localhost/hermes-worker:1 >/dev/null 2>&1; then
    image_exists=1
  else
    image_exists=0
  fi
  if mp_should_rebuild "$BUILD_STAMP" "$want_build_hash" "$image_exists"; then
    echo "build inputs changed or image absent; building"
    h podman build -t localhost/hermes-worker:1 -f "$BUILD/Containerfile" "$BUILD"
    build_rc=$?
    echo "worker_build_rc=$build_rc"
    if [ "$build_rc" -ne 0 ]; then
      mp_check worker_image FAIL "podman build failed (rc=$build_rc)"
      exit 1
    fi
    mp_write_stamp "$BUILD_STAMP" "$want_build_hash"
    image_changed=1
  else
    echo "build inputs unchanged and image present; skipping rebuild"
    mp_write_stamp "$BUILD_STAMP" "$want_build_hash"
    image_changed=0
  fi
  worker_id=$(h podman image inspect localhost/hermes-worker:1 --format '{{.Id}}')
  echo "worker_id=$worker_id image_changed=$image_changed"
  if [ -n "${HERMES_EXPECT_WORKER_IMAGE:-}" ] && [ "${HERMES_EXPECT_WORKER_IMAGE}" != "$worker_id" ]; then
    mp_check worker_image FAIL "built $worker_id, expected ${HERMES_EXPECT_WORKER_IMAGE}"
    echo "STOP: the built worker image is not the retained artifact under review."
    exit 1
  fi
  mp_check worker_image PASS "id=$worker_id"
  echo

  echo "===== install rootless Quadlets (convergent) ====="
  install -d -o root -g root -m 0755 "$QUADLET_DIR" || mp_die "cannot create $QUADLET_DIR"
  quadlets_changed=0
  for unit in hermes-worker.container hermes-gateway.container; do
    result=$(mp_install_reconcile "quadlet_${unit%.container}" 0644 root:root "$BUNDLE/quadlets/$unit" "$QUADLET_DIR/$unit") || exit 1
    echo "$result"
    [[ "$result" == CHANGED* ]] && quadlets_changed=1
  done
  [ "$quadlets_changed" -eq 1 ] && restorecon -Rv "$QUADLET_DIR" || echo "quadlet labels unchanged; no restorecon"
  echo

  echo "===== user manager reload and worker start (convergent) ====="
  if [ "$quadlets_changed" -eq 1 ]; then
    h systemctl --user daemon-reload
    echo "daemon_reload_rc=$?"
  else
    echo "quadlets unchanged; daemon-reload skipped"
  fi
  # Stopping the gateway is not necessary when nothing changed; doing it on
  # every convergence run would flap a healthy service for no reason. It is also
  # refused when the prior state is undeterminable, because the restoration hook
  # can only restart a gateway it positively knows was active (C2): the unit is
  # left running instead of being stopped without a safe way back.
  if [ "$image_changed" -eq 1 ] || [ "$quadlets_changed" -eq 1 ]; then
    if [ "$gw_prior_known" -eq 1 ]; then
      h systemctl --user stop hermes-gateway.service 2>/dev/null || true
    else
      echo "gateway stop skipped: the pre-run gateway state could not be determined"
      mp_info gateway_stop_skipped "the unit is left running because its prior state is undeterminable"
    fi
    h systemctl --user restart hermes-worker.service
  else
    worker_now=$(h systemctl --user is-active hermes-worker.service 2>/dev/null || true)
    if [ "$worker_now" = "active" ]; then
      echo "worker already active with unchanged artifacts; restart skipped"
    else
      h systemctl --user restart hermes-worker.service
    fi
  fi
  worker_start_rc=$?
  echo "worker_start_rc=$worker_start_rc"
  sleep 4
  worker_state=$(h systemctl --user is-active hermes-worker.service)
  echo "worker_state=$worker_state"
  mp_check worker_service "$([ "$worker_state" = active ] && echo PASS || echo FAIL)"
  h podman ps -a --format '{{.Names}} {{.Status}} {{.Image}}'
  echo "-- transport dir --"
  ls -lZ "$TRANSPORT"
  echo

  echo "===== worker network isolation (bounded IPv4/IPv6 probes) ====="
  routes=$(h podman exec "$WORKER_NAME" cat /proc/net/route 2>/dev/null)
  echo "-- worker /proc/net/route --"
  printf '%s\n' "$routes"
  # A missing probe tool is NOT isolation. Prove the tools exist before probing,
  # and classify each probe instead of reading any failure as "denied".
  probe_tools=$(h podman exec "$WORKER_NAME" sh -c \
    'command -v curl >/dev/null 2>&1 && command -v timeout >/dev/null 2>&1 && echo PROBE_TOOLS_PRESENT || echo PROBE_TOOLS_ABSENT' 2>&1)
  resolver_tools=$(h podman exec "$WORKER_NAME" sh -c \
    'command -v getent >/dev/null 2>&1 && command -v timeout >/dev/null 2>&1 && echo RESOLVER_PRESENT || echo RESOLVER_ABSENT' 2>&1)
  echo "-- probe tools: $probe_tools ; resolver: $resolver_tools --"
  ipv4_class=PROBE_UNAVAILABLE
  ipv6_class=PROBE_UNAVAILABLE
  ipv4_out=""
  ipv4_rc=1
  ipv6_out=""
  ipv6_rc=1
  if [[ "$probe_tools" == *PROBE_TOOLS_PRESENT* ]]; then
    # Literal TEST-NET addresses: no DNS dependency. A network-less worker has no
    # route, so the connect fails immediately (rc 7) rather than timing out.
    for family in ipv4 ipv6; do
      case "$family" in
        ipv4) url="http://198.51.100.1/" ;;
        ipv6) url="http://[2001:db8::1]/" ;;
      esac
      out=$(h podman exec "$WORKER_NAME" sh -c \
        "timeout 6 curl -sS --max-time 5 --connect-timeout 3 -o /dev/null '$url'; echo \"rc=\$?\"" 2>&1)
      rc=$(printf '%s\n' "$out" | sed -n 's/^rc=\([0-9][0-9]*\)$/\1/p' | tail -n1)
      rc=${rc:-1}
      class=$(mp_classify_egress "$rc" "$out")
      printf '%s_probe rc=%s class=%s output=%s\n' "$family" "$rc" "$class" "$out"
      if [ "$family" = ipv4 ]; then
        ipv4_class=$class
        ipv4_out=$out
        ipv4_rc=$rc
      else
        ipv6_class=$class
        ipv6_out=$out
        ipv6_rc=$rc
      fi
    done
  else
    echo "curl/timeout absent inside the worker; egress is UNVERIFIED, not isolated"
  fi
  isolation_fail=0
  isolation_unverified=0
  for class in "$ipv4_class" "$ipv6_class"; do
    case "$class" in
      EGRESS_SUCCESS) isolation_fail=1 ;;
      EGRESS_DENIED) ;;
      *) isolation_unverified=1 ;;
    esac
  done
  if [ "$isolation_fail" -eq 1 ]; then
    mp_check worker_network_isolation FAIL "egress succeeded from a network-less worker (ipv4=$ipv4_class ipv6=$ipv6_class)"
  elif [ "$isolation_unverified" -eq 1 ]; then
    mp_check worker_network_isolation UNVERIFIED \
      "egress could not be conclusively denied (ipv4=$ipv4_class ipv6=$ipv6_class); a missing or inconclusive probe is not isolation"
  else
    mp_check worker_network_isolation PASS "IPv4 and IPv6 egress both denied (ipv4=$ipv4_class ipv6=$ipv6_class)"
  fi
  # DNS is reported separately: resolution inside a network-less worker is a real
  # failure, while an unresolved name is the expected denied case. A missing
  # resolver command or a timed-out query is inconclusive, never isolation.
  # MP-DNS-GRADING-BEGIN — tests/test-hermes-manual-review.sh extracts and runs
  # this exact block with a mocked `h` so the real probe/grading wiring is
  # exercised, not a reimplementation of it.
  if [[ "$resolver_tools" == *RESOLVER_PRESENT* ]]; then
    dns_raw=$(h podman exec "$WORKER_NAME" sh -c 'timeout 4 getent hosts example.com; echo "rc=$?"' 2>&1)
    dns_rc=$(printf '%s\n' "$dns_raw" | sed -n 's/^rc=\([0-9][0-9]*\)$/\1/p' | tail -n1)
    dns_rc=${dns_rc:-1}
    dns_class=$(mp_classify_dns "$dns_rc" "$dns_raw")
    echo "-- worker DNS: rc=$dns_rc class=$dns_class output=$dns_raw --"
    case "$dns_class" in
      DNS_RESOLVED)
        mp_check worker_dns_isolation FAIL "DNS resolved example.com inside a network-less worker"
        ;;
      DNS_UNRESOLVED)
        mp_check worker_dns_isolation PASS "DNS did not resolve example.com (expected with no route)"
        ;;
      *)
        mp_check worker_dns_isolation UNVERIFIED "DNS could not be conclusively classified ($dns_class)"
        ;;
    esac
  else
    mp_check worker_dns_isolation UNVERIFIED "getent/timeout absent inside the worker; a missing resolver is not isolation"
  fi
  # MP-DNS-GRADING-END
  echo

  echo "===== gateway runtime identity can read its material ====="
  id_out=$(gclient /usr/bin/id 2>&1)
  echo "$id_out"
  read_out=$(gclient /bin/sh -c 'ls -ld /opt/hermes/gateway-ssh; ls -l /opt/hermes/gateway-ssh; head -c 32 /opt/hermes/gateway-ssh/worker_client_ed25519 >/dev/null && echo KEY_READABLE; head -c 32 /opt/hermes/gateway-ssh/known_hosts >/dev/null && echo KNOWN_HOSTS_READABLE; test -x /opt/hermes/bin/ssh && echo SHIM_EXECUTABLE' 2>&1)
  echo "$read_out"
  if [[ "$read_out" == *KEY_READABLE* && "$read_out" == *KNOWN_HOSTS_READABLE* && "$read_out" == *SHIM_EXECUTABLE* ]]; then
    mp_check gateway_material_readable PASS
  else
    mp_check gateway_material_readable FAIL "gateway UID 10000 cannot read its own material"
  fi
  echo

  echo "===== proof of option precedence (shim vs backend accept-new) ====="
  gclient /opt/hermes/bin/ssh -G -o BatchMode=yes -o StrictHostKeyChecking=accept-new worker@worker 2>&1 \
    | grep -iE '^(stricthostkeychecking|userknownhostsfile|identitiesonly|proxycommand|identityfile) '
  echo

  echo "===== positive: command reaches the worker ====="
  pos_out=$(gclient /opt/hermes/bin/ssh -o BatchMode=yes -o ConnectTimeout=10 worker@worker \
    'echo TRANSPORT_OK; id -un; cat /etc/fedora-release' 2>&1)
  pos_rc=$?
  echo "$pos_out"
  echo "positive_rc=$pos_rc"
  if [ "$pos_rc" -eq 0 ] && [[ "$pos_out" == *TRANSPORT_OK* ]]; then
    mp_check transport_positive PASS
  else
    mp_check transport_positive FAIL "the pinned transport did not reach the worker"
    echo "-- worker auth diagnostics --"
    echo "client pubkey: $(ssh-keygen -lf "$GWSSH/worker_client_ed25519.pub")"
    h podman logs --tail 40 "$WORKER_NAME" 2>&1
    # Expansion inside the container's script is intended; the outer shell must not expand it.
    # shellcheck disable=SC2016
    h podman exec "$WORKER_NAME" sh -c \
      'id worker; getent passwd worker; awk -F: "/^worker:/{print \"shadow_field_len=\" length(\$2) \" first_char=\" substr(\$2,1,1)}" /etc/shadow; ls -l /etc/ssh/authorized_keys/; ssh-keygen -lf /etc/ssh/authorized_keys/worker; ls -ld /home/worker /home/worker/.hermes' 2>&1
    echo "-- verbose client (filtered) --"
    gclient /opt/hermes/bin/ssh -vvv -o BatchMode=yes -o ConnectTimeout=10 worker@worker true 2>&1 \
      | grep -iE 'offering|authentications that can continue|Authenticated|Permission denied|Server accepts|publickey' | head -n 20
  fi
  echo

  # Negative tests edit only the disposable copy, so the live pin is untouched.
  echo "===== negative: missing trusted key must fail ====="
  : >"$CLIENT_DIR/known_hosts"
  chmod 0644 "$CLIENT_DIR/known_hosts"
  miss_out=$(gclient /opt/hermes/bin/ssh -o BatchMode=yes -o ConnectTimeout=10 worker@worker \
    'echo SHOULD_NOT_CONNECT' 2>&1)
  miss_rc=$?
  echo "$miss_out" | tail -n 4
  echo "missing_key_rc=$miss_rc"
  mp_check transport_missing_key "$([ "$miss_rc" -ne 0 ] && echo PASS || echo FAIL)"
  cp -a "$GWSSH/known_hosts" "$CLIENT_DIR/known_hosts"
  echo

  echo "===== negative: changed host key must fail ====="
  ssh-keygen -q -t ed25519 -N '' -f "$BUILD/hermes-wronghostkey"
  printf 'worker %s\n' "$(cat "$BUILD/hermes-wronghostkey.pub")" >"$CLIENT_DIR/known_hosts"
  chmod 0644 "$CLIENT_DIR/known_hosts"
  chg_out=$(gclient /opt/hermes/bin/ssh -o BatchMode=yes -o ConnectTimeout=10 worker@worker \
    'echo SHOULD_NOT_CONNECT' 2>&1)
  chg_rc=$?
  echo "$chg_out" | tail -n 4
  echo "changed_key_rc=$chg_rc"
  mp_check transport_changed_key "$([ "$chg_rc" -ne 0 ] && echo PASS || echo FAIL)"
  rm -f "$BUILD/hermes-wronghostkey" "$BUILD/hermes-wronghostkey.pub"
  cp -a "$GWSSH/known_hosts" "$CLIENT_DIR/known_hosts"
  echo

  echo "===== note: M03 owns gateway activation ====="
  echo

  echo "===== recent AVC denials ====="
  mp_audit_avc_check avc_denials recent
  echo "===== done ====="
} 2>&1 | tee "$OUT" || rc=$?

# Runs in the CURRENT shell (append redirection, not a pipeline), so the hook's
# idempotence is preserved and its failure is reported without masking the
# primary pipeline status.
restore_rc=0
restore_gateway_state >>"$OUT" 2>&1 || restore_rc=$?
if [ "$restore_rc" -eq 0 ]; then
  printf 'CHECK restore_gateway_state=PASS\n' >>"$OUT"
else
  printf 'CHECK restore_gateway_state=FAIL "prior gateway state could not be restored"\n' >>"$OUT"
  printf 'RESTORE_FAILED gateway state restoration failed (see %s)\n' "$OUT" >&2
fi
chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
echo "WROTE=$OUT"
mp_finalize "$OUT" "${rc:-0}"
