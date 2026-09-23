#!/usr/bin/env bash
# shellcheck shell=bash
# Secret-free validation for the disposable VM encrypted-boot transcript.

if [[ -n "${_HERMES_CERTIFICATION_EVIDENCE_LOADED-}" ]]; then
  return 0
fi
readonly _HERMES_CERTIFICATION_EVIDENCE_LOADED=1
readonly HERMES_CERTIFICATION_EXPECTED_WATCHED_BOOTS=3

certification_unlock_evidence_is_valid() {
  local event_log=$1
  local expected_watched=${2:-$HERMES_CERTIFICATION_EXPECTED_WATCHED_BOOTS}
  [[ -r "$event_log" && "$expected_watched" =~ ^[1-9][0-9]*$ ]] || return 1

  awk -v expected="$expected_watched" '
    $2 == "monitor-ready" {
      ready += 1
      if (monitor_ready) {
        invalid = 1
      }
      monitor_ready = 1
      rebooted = 0
      armed = 0
      next
    }
    $2 == "luks-reboot-observed" && $3 == "input-submitted=0" {
      reboots += 1
      if (!monitor_ready || rebooted || armed) {
        invalid = 1
      }
      rebooted = 1
      next
    }
    $2 == "luks-boot-boundary-observed" && $3 == "input-submitted=0" {
      boundaries += 1
      if (!monitor_ready || !rebooted || armed) {
        invalid = 1
      }
      rebooted = 0
      armed = 1
      next
    }
    $2 == "luks-prompt-verified" && $3 == "input-submitted=1" {
      if (!monitor_ready) {
        initial += 1
      } else {
        watched += 1
        if (!armed) {
          invalid = 1
        }
        armed = 0
      }
      next
    }
    END {
      valid = ready == 1 && initial == 1 && reboots == expected &&
        boundaries == expected && watched == expected && !invalid &&
        !rebooted && !armed
      exit(valid ? 0 : 1)
    }
  ' "$event_log"
}

certification_unlock_evidence_summary() {
  local event_log=$1
  [[ -r "$event_log" ]] || {
    printf 'initial=0 watched=0 boundaries=0 monitor_ready=0\n'
    return 1
  }
  awk '
    $2 == "monitor-ready" { ready += 1; monitor_ready = 1; next }
    $2 == "luks-boot-boundary-observed" && $3 == "input-submitted=0" {
      boundaries += 1
      next
    }
    $2 == "luks-prompt-verified" && $3 == "input-submitted=1" {
      if (monitor_ready) {
        watched += 1
      } else {
        initial += 1
      }
    }
    END {
      printf "initial=%d watched=%d boundaries=%d monitor_ready=%d\n",
        initial, watched, boundaries, ready
    }
  ' "$event_log"
}
