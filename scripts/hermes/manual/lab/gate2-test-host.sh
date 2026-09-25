#!/usr/bin/env bash
# Installed root-owned under /var/usrlocal/libexec/hermes-gate2-test on the hypervisor.
# Only the exact Gate 2 fixture may be started or shut down. No caller paths or
# environment variables are passed to virsh.
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin LC_ALL=C

DOMAIN=lab-hermes-manual-r1
UUID=d39e5ca7-aded-457c-b01d-a1817a4725a8
MAC=52:54:00:94:58:36
URI=qemu:///system

die() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
[[ $# == 1 ]] || die 'exactly one operation is required'
case "$1" in status|start|shutdown) action=$1 ;; *) die 'operation denied' ;; esac
[[ $(id -u) == 0 && ${SUDO_USER:-} == aicloudopspecial ]] || die 'wrong invoking identity'

actual_uuid=$(/usr/bin/virsh -c "$URI" domuuid "$DOMAIN")
[[ $actual_uuid == "$UUID" ]] || die 'fixture UUID mismatch'
/usr/bin/virsh -c "$URI" domiflist "$DOMAIN" | /usr/bin/awk -v mac="$MAC" \
  '$2 == "network" && $3 == "fvh-nat" && $5 == mac {ok=1} END {exit !ok}' \
  || die 'fixture network or MAC mismatch'
state=$(/usr/bin/virsh -c "$URI" domstate "$DOMAIN")
/usr/bin/logger -t hermes-gate2-test -- "host action=$action domain=$DOMAIN state_before=$state"
case "$action:$state" in
  status:*) printf 'domain=%s state=%s\n' "$DOMAIN" "$state" ;;
  start:shut\ off) /usr/bin/virsh -c "$URI" start "$DOMAIN" ;;
  start:running) printf 'already running\n' ;;
  shutdown:running)
    /usr/bin/virsh -c "$URI" shutdown "$DOMAIN"
    for ((i=0; i<60; i++)); do
      [[ $(/usr/bin/virsh -c "$URI" domstate "$DOMAIN") == 'shut off' ]] && break
      sleep 2
    done
    [[ $(/usr/bin/virsh -c "$URI" domstate "$DOMAIN") == 'shut off' ]] || die 'shutdown did not finish'
    ;;
  shutdown:shut\ off) printf 'already shut off\n' ;;
  *) die "operation $action refused in state $state" ;;
esac
/usr/bin/logger -t hermes-gate2-test -- "host action=$action result=success"
