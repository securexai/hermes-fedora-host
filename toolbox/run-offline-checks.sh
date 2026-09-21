#!/usr/bin/env bash
# Run every offline check for this repository.
#
# This is the single entrypoint shared by the pre-push hook, contributors and
# CI, so that developer machines and CI run identical commands. It runs with
# synthetic fixtures only: no network, no container, no credentials and no
# privileged commands.
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly SCRIPT_DIR REPO_ROOT

cd "$REPO_ROOT"

failures=0

run() {
  local name=$1
  shift
  printf '\n=== %s ===\n' "$name"
  if "$@"; then
    printf 'PASS: %s\n' "$name"
  else
    printf 'FAIL: %s\n' "$name" >&2
    failures=$((failures + 1))
  fi
}

run "manual profile" bash tests/test-hermes-manual-profile.sh
run "manual review regressions" bash tests/test-hermes-manual-review.sh
run "backup fault injection" bash tests/test-hermes-manual-backup.sh
run "configure drift and convergence" bash tests/test-hermes-manual-configure.sh
run "contract ownership and mount safety" bash tests/test-hermes-manual-contract.sh
run "m01 temporary state" bash tests/test-hermes-manual-m01-tempdir.sh
run "python config hardening" python3 -B -m unittest discover -s tests -p test_hermes_manual_hardening.py
run "clean-install rehearsal" bash scripts/hermes/manual/boot/rehearse-clean-install.sh

# ShellSpec 0.28.1 is installed as a declared extension (toolbox/extensions.yaml),
# but the only upstream spec, spec/hermes/deploy_spec.sh, exercises the deployment
# entrypoints (hermes-deploy.sh, hermes-certify-vm.sh, provider authentication and
# VM lifecycle) that are out of scope here. It is therefore N/A, like
# test-hermes-guide.sh. The extension is retained so in-scope unit specs can run.

if ((failures > 0)); then
  printf '\nFAIL: %d offline check(s) failed\n' "$failures" >&2
  exit 1
fi
printf '\nPASS: all offline checks passed\n'
