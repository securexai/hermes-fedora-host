#!/usr/bin/env bash
# Routine, credential-free checks against the same pinned Hermes image as deployment.
set -Eeuo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
manifest="$repo_root/scripts/hermes/manual/manifest.yaml"
image=$(sed -n 's/^    ref: \(docker.io\/nousresearch\/hermes-agent@sha256:[a-f0-9]\{64\}\)$/\1/p' "$manifest")
[[ -n $image ]] || {
  echo 'STOP: pinned Hermes image missing from manifest' >&2
  exit 1
}

case "${1:-test}" in
  test)
    exec podman run --rm --network none --read-only \
      --env DEEPSEEK_API_KEY= --env TELEGRAM_BOT_TOKEN= \
      --volume "$repo_root/tests/hermes-synthetic-smoke.py:/run/hermes-synthetic-smoke.py:ro,Z" \
      --entrypoint /opt/hermes/.venv/bin/python3 "$image" \
      /run/hermes-synthetic-smoke.py
    ;;
  status)
    if podman image exists "$image"; then
      printf 'PASS: pinned Hermes image cached: %s\n' "$image"
    else
      printf 'NOT CACHED: %s\n' "$image"
      exit 1
    fi
    ;;
  clean)
    # The test uses --rm and writes no persistent container state.
    printf 'PASS: routine test has no persistent container to clean\n'
    ;;
  *)
    echo 'Usage: lab-test.sh [test|status|clean]' >&2
    exit 2
    ;;
esac
