#!/usr/bin/env bash
# shellcheck shell=bash
# Shared, output-based Hermes authentication status parser.

if [[ -n "${_HERMES_PROVIDER_AUTH_STATUS_LOADED-}" ]]; then
  return 0
fi
readonly _HERMES_PROVIDER_AUTH_STATUS_LOADED=1

# Hermes has returned exit status zero for both logged-in and logged-out
# accounts. The only accepted status is an exact, whole output line.
provider_auth_status_logged_in() {
  local provider=$1
  local output=$2
  grep -Fqx -- "$provider: logged in" <<<"$output"
}
