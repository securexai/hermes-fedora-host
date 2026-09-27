#!/usr/bin/env bash
# Compatibility entrypoint; implementation: vm/hermes-certify-vm.sh.
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd) || exit
exec "$SCRIPT_DIR/vm/hermes-certify-vm.sh" "$@"
