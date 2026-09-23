#!/usr/bin/env bash
# Run every offline check for this repository.
#
# This is the single entrypoint shared by the pre-push hook, contributors and the
# certifier's check-only gate, so a green local run means the same offline set
# ran. (No CI runner exists for this repository yet.) It runs with synthetic
# fixtures only: no network, no VM, no credentials and no privileged commands.
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
run "clean-install rehearsal" bash scripts/hermes/manual/boot/rehearse-clean-install.sh
run "guide and deployment tree" bash tests/test-hermes-guide.sh
run "deployment and VM specs" toolbox/.tools/shellspec/shellspec spec/

# Reviewed Python suites. `tests/offline_allowlist.txt` enumerates the exact
# reviewed `module.Class` unit targets and `tests/run-reviewed-suites.py` loads
# only those; nothing is discovered. Installing libguestfs, a kernel package,
# ukify, dracut or openssh-server therefore cannot pull real VM, disk, firmware,
# archive or host-service work into this gate. The real integration cases live
# in `tests/integration_allowlist.txt` and run only through the explicit opt-in
# `toolbox/run-integration-checks.sh`; integration acceptance stays NOT RUN here.
run "python suites (reviewed offline allowlist)" python3 -B tests/run-reviewed-suites.py --set offline

# Non-writing secret scan over the full working tree, including untracked files.
# The pre-commit `betterleaks` hook is staged-only and its upstream entry cannot
# be widened with filenames, so this closes the coverage gap the hook leaves.
run "secret scan (full working tree)" bash toolbox/scan-secrets.sh

# Provenance is part of the gate: the manifest must still match the working tree.
# This requires the source checkout and the dev-toolbox checkout recorded in
# PROVENANCE.md (both exist on the development workstation).
run "migration manifest" python3 toolbox/generate-migration-manifest.py --verify

# `tests/test-hermes-e2e-vm.sh` and `tests/test-hermes-links.sh` are deliberately
# NOT run here. The first drives real VM lifecycle through hermes-certify-vm.sh;
# the second fetches external documentation URLs over the network. Both are kept
# in the tree for their owners and are excluded by explicit decision in the
# repository migration record, not by omission. `tests/check_ssh_key_only_docs.py`
# needs a standalone `markdownlint-cli2` binary and is not a unittest module.
if ((failures > 0)); then
  printf '\nFAIL: %d offline check(s) failed\n' "$failures" >&2
  exit 1
fi
printf '\nPASS: all offline checks passed\n'
