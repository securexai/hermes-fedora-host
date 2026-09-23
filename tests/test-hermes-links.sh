#!/usr/bin/env bash
# shellcheck shell=bash
#
# Network-dependent health checks for the Hermes deployment sources.
# Keep this script outside the offline pre-push suite.

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s nullglob

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
readonly REPO_ROOT

readonly GUIDE="$REPO_ROOT/hermes-fedora-server-install-guide.html"
readonly PLAN="$REPO_ROOT/docs/HERMES_DEPLOYMENT_PLAN.md"
readonly VERIFICATION="$REPO_ROOT/docs/HERMES_INSTALLATION_VERIFICATION.md"
readonly SECURITY_PLAN="$REPO_ROOT/secure-hermes-installation-plan.html"
readonly FEDORA_SERVER_URL="https://fedoraproject.org/server/download/"

for file in "$GUIDE" "$PLAN" "$VERIFICATION" "$SECURITY_PLAN"; do
  [[ -f "$file" ]] || {
    printf 'ERROR: required file not found: %s\n' "$file" >&2
    exit 1
  }
done

if ! rg --fixed-strings --quiet "$FEDORA_SERVER_URL" "$GUIDE" "$VERIFICATION" "$SECURITY_PLAN"; then
  printf 'ERROR: Hermes documents do not name the official Fedora Server source\n' >&2
  exit 1
fi

mapfile -t urls < <(
  {
    printf '%s\n' "$FEDORA_SERVER_URL"
    rg --no-filename -o 'https?://[^"<> )]+' "$GUIDE" "$PLAN" "$VERIFICATION" "$SECURITY_PLAN"
  } \
    | sed -E 's/[.,]$//' \
    | awk '$0 !~ /\$/ && $0 !~ /nvd\.nist\.gov/' \
    | sort -u
)

if ((${#urls[@]} == 0)); then
  printf 'ERROR: no HTTPS sources found\n' >&2
  exit 1
fi

printf 'Checking %d Hermes source links with bounded retries...\n' "${#urls[@]}"
failures=0
for url in "${urls[@]}"; do
  if curl --fail --silent --show-error --location \
    --retry 3 --retry-all-errors --retry-delay 2 --connect-timeout 10 --max-time 30 \
    -o /dev/null "$url"; then
    printf 'PASS %s\n' "$url"
  else
    printf 'FAIL %s\n' "$url" >&2
    failures=$((failures + 1))
  fi
done

if ((failures > 0)); then
  printf '%d link checks failed\n' "$failures" >&2
  exit 1
fi

printf 'All Hermes source links passed.\n'
