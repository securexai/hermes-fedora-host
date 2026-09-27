#!/usr/bin/env bash
# Compatibility entrypoint; implementation: scripts/hermes/simple/deploy.sh.
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd) || exit
exec "$SCRIPT_DIR/scripts/hermes/simple/deploy.sh" "$@"
