#!/usr/bin/env bash
# Unattended application installation on an already installed Fedora Server host.
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$SCRIPT_DIR/scripts/hermes/simple/controller.py" "$@"
