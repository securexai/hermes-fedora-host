#!/usr/bin/env bash
# M04 step 2: stopped-state application backup plus an isolated restore test.
#
# Default is inspect-only; re-run with --apply to make changes.
#
# Both containers are stopped for a consistent archive. Archiving is refused
# unless every writer is POSITIVELY confirmed stopped (services inactive and no
# profile container running). The service state observed before the backup is
# restored by a trap-registered hook, so an early failure, an INT or a TERM still
# restores it. The restore test never launches the restored application.
#
#   sudo HERMES_EXPECT_MACHINE_ID_SHA256=<hash> bash ~/hermes-manual/m04-backup.sh --apply
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
ADMIN_ACCOUNT=$(mp_admin_account)
ADMIN_HOME=$(mp_admin_home)
OUT=$(mp_new_log "$ADMIN_HOME/hermes-m04-backup.out")
RUNTIME_ACCOUNT="${HERMES_RUNTIME:-hermes}"
RUNTIME_HOME="${HERMES_RUNTIME_HOME:-/home/${RUNTIME_ACCOUNT}}"
HERMES_UID=$(id -u "$RUNTIME_ACCOUNT")
TS=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="${HERMES_BACKUP_BASE:-$ADMIN_HOME}/hermes-app-backup-$TS"
GW_STATE="$RUNTIME_HOME/gateway-state"
WSTATE="$RUNTIME_HOME/worker-state"
GWSSH="$RUNTIME_HOME/gateway-ssh"
QUADLET_DIR="${HERMES_QUADLET_DIR:-/etc/containers/systemd/users/$HERMES_UID}"

mp_require_apply 'would stop both containers, archive the application state, test a restore, and restart them'
mp_require_host_identity
mp_lock_profile
mp_install_trap
# Registered in THIS shell (not via command substitution) so an interrupted run
# removes the restored credential copy.
mp_secure_tmpdir_var RESTORE
mp_require_tools podman tar

h() {
  if ! mountpoint -q "$RUNTIME_HOME"; then
    printf 'STOP: %s is not mounted.\n' "$RUNTIME_HOME" >&2
    return 1
  fi
  sudo -u "$RUNTIME_ACCOUNT" -- env -i --chdir="$RUNTIME_HOME" \
    HOME="$RUNTIME_HOME" USER="$RUNTIME_ACCOUNT" LOGNAME="$RUNTIME_ACCOUNT" \
    PATH=/usr/local/bin:/usr/bin:/bin \
    TERM="${TERM:-xterm}" XDG_RUNTIME_DIR="/run/user/$HERMES_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$HERMES_UID/bus" \
    TMPDIR="$RUNTIME_HOME/.cache/podman-tmp" "$@"
}

# The pre-run state must be CONCLUSIVE before anything is stopped: the
# restoration hook can only restart a service it positively knows was active, so
# a transient query failure must never silently become "no restoration needed"
# (C2). An undeterminable obligation refuses the whole lifecycle mutation.
prior_ok=1
gw_prior=$(mp_capture_service_state h hermes-gateway.service) || prior_ok=0
worker_prior=$(mp_capture_service_state h hermes-worker.service) || prior_ok=0

# Trap-registered and idempotent: it acts only when the current state differs
# from the state observed before the run, and returns non-zero when a service
# that was active cannot be restored.
restore_service_state() {
  local now rc=0
  if [ "$worker_prior" = "active" ]; then
    now=$(h systemctl --user is-active hermes-worker.service 2>/dev/null || true)
    if [ "$now" != "active" ]; then
      if ! h systemctl --user start hermes-worker.service; then
        printf 'RESTORE_FAILED worker service was active before this run and could not be restarted\n' >&2
        rc=1
      fi
    fi
  fi
  if [ "$gw_prior" = "active" ]; then
    now=$(h systemctl --user is-active hermes-gateway.service 2>/dev/null || true)
    if [ "$now" != "active" ]; then
      if ! h systemctl --user start hermes-gateway.service; then
        printf 'RESTORE_FAILED gateway service was active before this run and could not be restarted\n' >&2
        rc=1
      fi
    fi
  fi
  printf 'worker_state_at_exit=%s\n' "$(h systemctl --user is-active hermes-worker.service 2>/dev/null || true)"
  printf 'gateway_state_at_exit=%s\n' "$(h systemctl --user is-active hermes-gateway.service 2>/dev/null || true)"
  return "$rc"
}
mp_on_cleanup restore_service_state

# Compare a source tree with its restored copy: content AND metadata (mode,
# owner, type). Two views are used because `diff -rq` compares content only.
tree_metadata() { # <dir>
  (cd "$1" && find . -printf '%P|%m|%u:%g|%y\n' 2>/dev/null | LC_ALL=C sort)
}

rc=0
{
  echo "### M04 step 2: slice persistence, posture, backup and restore"
  echo "### generated: $TS"
  echo "### backup=$BACKUP"
  echo

  echo "===== container posture (worker) ====="
  h podman inspect hermes-worker --format \
    'readonly_rootfs={{.HostConfig.ReadonlyRootfs}} memory={{.HostConfig.Memory}} pids={{.HostConfig.PidsLimit}} netmode={{.HostConfig.NetworkMode}} userns={{.HostConfig.UsernsMode}} privileged={{.HostConfig.Privileged}}
securityopt={{.HostConfig.SecurityOpt}}
capdrop={{.HostConfig.CapDrop}} capadd={{.HostConfig.CapAdd}}
binds={{range .HostConfig.Binds}}{{.}} {{end}}' 2>&1 || true
  echo

  echo "===== stop writers before backup ====="
  stop_failed=0
  writers_stopped=1
  if [ "$prior_ok" -ne 1 ]; then
    echo "REFUSING to stop any service: the pre-run service state could not be"
    echo "determined, so a safe restoration could not be guaranteed."
    mp_check prior_service_state FAIL \
      "gateway='${gw_prior:-<no output>}' worker='${worker_prior:-<no output>}' is not a conclusive state"
    writers_stopped=0
  else
    mp_check prior_service_state PASS "gateway=$gw_prior worker=$worker_prior before the run"
    for svc in hermes-gateway hermes-worker; do
      if ! h systemctl --user stop "$svc.service" 2>/dev/null; then
        echo "stop_command_failed=$svc"
        stop_failed=1
      fi
    done
    for svc in hermes-gateway hermes-worker; do
      state=""
      state_rc=0
      state=$(h systemctl --user is-active "$svc.service" 2>/dev/null) || state_rc=$?
      echo "${svc}_state=${state:-<no output>} (query_rc=$state_rc)"
      # systemctl answers "inactive"/"dead" with its normal status 3, so 0 and 3 are
      # both acceptable query statuses; anything else is a genuine query failure.
      case "$state_rc" in
        0 | 3) ;;
        *) writers_stopped=0 ;;
      esac
      # Only a definite stopped state is conclusive. A failed query (empty output),
      # a transitional state or any other value is NOT proof the writer stopped.
      case "$state" in
        inactive | dead) ;;
        *) writers_stopped=0 ;;
      esac
    done
    running=""
    podman_rc=0
    running=$(h podman ps --format '{{.Names}}' 2>/dev/null) || podman_rc=$?
    echo "running_containers=${running:-none} (query_rc=$podman_rc)"
    if [ "$podman_rc" -ne 0 ]; then
      echo "container_query_failed=rc$podman_rc (a failed query is not proof of no writers)"
      writers_stopped=0
    elif printf '%s\n' "$running" | grep -qE 'hermes-(gateway|worker)'; then
      writers_stopped=0
    fi
  fi
  if [ "$prior_ok" -ne 1 ]; then
    mp_check writers_stopped FAIL "not attempted: the pre-run service state could not be determined"
  elif [ "$stop_failed" -eq 1 ]; then
    mp_check writers_stopped FAIL "a stop command failed; writers are not confirmed stopped"
  elif [ "$writers_stopped" -eq 1 ]; then
    mp_check writers_stopped PASS "gateway and worker inactive; no profile container running"
  else
    mp_check writers_stopped FAIL "a writer is still active after stop"
  fi
  echo

  if [ "$writers_stopped" -ne 1 ] || [ "$stop_failed" -eq 1 ]; then
    echo "REFUSING to archive: all writers must be positively confirmed stopped first."
    mp_check backup_archive FAIL "skipped because the writers were not confirmed stopped"
    mp_check restore_extract FAIL "skipped because no archive was created"
    mp_check restore_metadata FAIL "skipped because no archive was created"
    mp_check restore_tree_identical FAIL "skipped because no archive was created"
  else
    echo "===== create stopped-state backup ====="
    install -d -m 0700 "$BACKUP"
    tar_rc=0
    tar --xattrs --acls --selinux -C / -cpf "$BACKUP/app-state.tar" \
      "${GW_STATE#/}" \
      "${WSTATE#/}" \
      "${GWSSH#/}" \
      "${QUADLET_DIR#/}" 2>/dev/null || tar_rc=$?
    echo "tar_rc=${tar_rc:-1}"
    chmod 600 "$BACKUP/app-state.tar" 2>/dev/null || true
    ls -l "$BACKUP/app-state.tar"
    mp_sha256 "$BACKUP/app-state.tar"
    echo "-- archive contents summary --"
    tar -tf "$BACKUP/app-state.tar" 2>/dev/null | wc -l
    tar -tf "$BACKUP/app-state.tar" 2>/dev/null | grep -E 'config.yaml|\.env$|\.container$' | head -n 20 || true
    # BOTH the command status and the archive's own readability are required; a
    # partially written archive can still be listed by tar and must not pass.
    if [ "${tar_rc:-1}" -eq 0 ] && [ -s "$BACKUP/app-state.tar" ] \
      && tar -tf "$BACKUP/app-state.tar" >/dev/null 2>&1; then
      mp_check backup_archive PASS "sha256=$(mp_sha256 "$BACKUP/app-state.tar")"
    else
      mp_check backup_archive FAIL "tar creation failed (rc=$tar_rc) or the archive is missing/unreadable"
    fi
    echo

    echo "===== backup manifest (hashes, no secret values) ====="
    {
      echo "created_utc=$TS"
      echo "gateway_config_sha256=$(mp_sha256 "$GW_STATE/config.yaml")"
      echo "env_file_sha256=$(mp_sha256 "$GW_STATE/.env")"
      echo "worker_host_key_sha256=$(mp_sha256 "$WSTATE/ssh-host-keys/ssh_host_ed25519_key.pub")"
      echo "gateway_known_hosts_sha256=$(mp_sha256 "$GWSSH/known_hosts")"
      echo "archive_sha256=$(mp_sha256 "$BACKUP/app-state.tar")"
    } | tee "$BACKUP/manifest.txt"
    chmod 600 "$BACKUP/manifest.txt" 2>/dev/null || true
    mp_check backup_manifest "$([ -s "$BACKUP/manifest.txt" ] && echo PASS || echo FAIL)"
    echo

    echo "===== isolated restore test (never launched) ====="
    restore_rc=0
    tar --xattrs --acls --selinux -C "$RESTORE" -xpf "$BACKUP/app-state.tar" 2>/dev/null || restore_rc=$?
    echo "restore_tar_rc=${restore_rc:-1}"
    echo "-- restored tree --"
    ls -la "$RESTORE/${RUNTIME_HOME#/}/" 2>&1
    echo
    # Extraction failure is a hard failure: every later check depends on it.
    mp_check restore_extract "$([ "${restore_rc:-1}" -eq 0 ] && echo PASS || echo FAIL)" \
      "tar extraction rc=${restore_rc:-1}"

    echo "===== restore verification (all required components) ====="
    restore_ok=1
    metadata_ok=1
    for src in "$GW_STATE" "$WSTATE" "$GWSSH" "$QUADLET_DIR"; do
      rel="${src#/}"
      dst="$RESTORE/$rel"
      name=$(basename "$src")
      if [ ! -d "$dst" ]; then
        mp_check "restore_component_${name}" FAIL "restored component missing: $dst"
        restore_ok=0
        metadata_ok=0
        continue
      fi
      echo "-- $name: source=$(find "$src" | wc -l) restored=$(find "$dst" | wc -l) --"
      if diff -rq --no-dereference "$src" "$dst" >/dev/null 2>&1; then
        mp_check "restore_component_${name}" PASS
      else
        mp_check "restore_component_${name}" FAIL "restored tree differs from source"
        restore_ok=0
      fi
      if [ "$(tree_metadata "$src")" = "$(tree_metadata "$dst")" ]; then
        echo "   metadata (mode/owner/type) matches"
      else
        echo "   metadata differs:"
        diff <(tree_metadata "$src") <(tree_metadata "$dst") 2>/dev/null | head -n 10 || true
        metadata_ok=0
      fi
    done
    mp_check restore_tree_identical "$([ "$restore_ok" -eq 1 ] && echo PASS || echo FAIL)"
    mp_check restore_metadata "$([ "$metadata_ok" -eq 1 ] && echo PASS || echo FAIL)" \
      "mode, owner and file-type comparison for every component"

    echo "-- restored config assertions --"
    backend_lines=$(grep -cE '^  backend: ssh' "$RESTORE/${GW_STATE#/}/config.yaml" 2>/dev/null || true)
    ssh_host_lines=$(grep -cE '^  ssh_host: worker' "$RESTORE/${GW_STATE#/}/config.yaml" 2>/dev/null || true)
    echo "restored_backend_ssh_lines=${backend_lines:-0} restored_ssh_host_lines=${ssh_host_lines:-0}"
    mp_check restore_config_backend "$([ "${backend_lines:-0}" -ge 1 ] && [ "${ssh_host_lines:-0}" -ge 1 ] && echo PASS || echo FAIL)"
    src_env_mode=$(stat -c %a "$GW_STATE/.env" 2>/dev/null || echo absent)
    dst_env_mode=$(stat -c %a "$RESTORE/${GW_STATE#/}/.env" 2>/dev/null || echo absent)
    echo "source_env_mode=$src_env_mode restored_env_mode=$dst_env_mode"
    if [ "$src_env_mode" = absent ]; then
      # A credential-free profile legitimately has no .env; verify its ABSENCE is
      # preserved rather than inventing a required credential file.
      mp_check restore_env_mode "$([ "$dst_env_mode" = absent ] && echo PASS || echo FAIL)" \
        "no profile .env in the source and none restored (credential-free)"
    else
      mp_check restore_env_mode "$([ "$src_env_mode" = "$dst_env_mode" ] && echo PASS || echo FAIL)"
    fi
    echo "-- restored quadlets --"
    ls -l "$RESTORE/${QUADLET_DIR#/}/" 2>&1
    mp_check restore_quadlets "$([ -r "$RESTORE/${QUADLET_DIR#/}/hermes-gateway.container" ] && echo PASS || echo FAIL)"
    echo

    echo "===== remove the restored credential copy after verification ====="
    rm -rf "$RESTORE"
    mp_check restore_copy_removed "$([ ! -e "$RESTORE" ] && echo PASS || echo FAIL)"
    echo
  fi

  echo "===== stage the backup for off-disk transfer ====="
  if [ -d "$BACKUP" ]; then
    chown -R "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$BACKUP" 2>/dev/null || true
    chmod 700 "$BACKUP" 2>/dev/null || true
    chmod 600 "$BACKUP/app-state.tar" "$BACKUP/manifest.txt" 2>/dev/null || true
    ls -la "$BACKUP"
    echo "NOTE: the archive contains provider and bot credentials. Move it to approved"
    echo "      encrypted off-host storage; do not leave it on the server."
  fi
  echo "===== done ====="
} 2>&1 | tee "$OUT" || rc=$?

# Current-shell append so the hook's idempotence holds and a cleanup failure is
# reported without replacing the primary pipeline status. A restoration failure
# is recorded as a required CHECK, so it fails an otherwise-successful run; when
# the pipeline already failed, that primary status is what mp_finalize reports.
restore_rc=0
restore_service_state >>"$OUT" 2>&1 || restore_rc=$?
if [ "$prior_ok" -ne 1 ]; then
  # Nothing was stopped, so there is no restoration to grade. Recording
  # NOT_APPLICABLE (rather than PASS) is what stops the refusal from being
  # misread as "services were restored" (C2).
  printf 'CHECK restore_service_state=NOT_APPLICABLE "no lifecycle mutation was attempted because the pre-run state was undetermined"\n' >>"$OUT"
elif [ "$restore_rc" -eq 0 ]; then
  printf 'CHECK restore_service_state=PASS\n' >>"$OUT"
else
  printf 'CHECK restore_service_state=FAIL "prior service state could not be restored"\n' >>"$OUT"
  printf 'RESTORE_FAILED service state restoration failed (see %s)\n' "$OUT" >&2
fi
chown "$ADMIN_ACCOUNT:$ADMIN_ACCOUNT" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT"
echo "WROTE=$OUT"
echo "BACKUP_DIR=$BACKUP"
mp_finalize "$OUT" "${rc:-0}"
