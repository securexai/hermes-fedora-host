#!/usr/bin/env bash
# shellcheck shell=bash
# Compatibility test entrypoint for the complete Hermes Server certification.
# VM lifecycle and the provider gate are owned by hermes-certify-vm.sh.

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

case "${1:-}" in
  -h | --help)
    cat <<'EOF'
Run the complete disposable Fedora Server 44 Hermes certification.

Usage:
  ./tests/test-hermes-e2e-vm.sh \
    --iso PATH --checksum PATH --fedora-keyring PATH \
    --identity-file PATH --provider ID --model MODEL

The command delegates VM creation, DNF5/reboot testing, provider authentication,
exact HERMES_OK acceptance, revocation, purge, destruction, and promotion-record
generation to hermes-certify-vm.sh.
EOF
    exit 0
    ;;
esac

exec "$REPO_ROOT/hermes-certify-vm.sh" "$@"
