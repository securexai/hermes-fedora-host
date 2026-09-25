#!/usr/bin/env bash
# Check-only lint gate over the full reviewed working tree (tracked + untracked).
#
# Certification invokes this inside the dev-toolbox `infra` container instead of
# `pre-commit run --all-files`, because:
#   * `--all-files` covers only Git-tracked paths; imported entrypoints may still
#     be untracked when certification runs, and a `--files` pass over the whole
#     working tree covers them.
#   * the auto-fixing baseline hooks (trailing-whitespace, end-of-file-fixer,
#     mixed-line-ending) would rewrite inputs before aborting. A certificate must
#     never mutate the artifact it certifies.
#   * the repository's error-only ShellCheck hook would weaken the certifier's
#     former default-severity run. This gate runs ShellCheck at default severity
#     over the certifier's original reviewed file set, so the promoted gate keeps
#     that coverage, and separately runs the repository's error-only gate over
#     every shell file.
#
# Nothing here writes to the working tree. Run it inside `dev-infra-hermes`.
#
# Usage:
#   toolbox/run-check-only-lint.sh
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly SCRIPT_DIR REPO_ROOT

cd "$REPO_ROOT"

for command in git shellcheck shfmt pre-commit; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf 'ERROR: %s is required for the check-only lint gate\n' "$command" >&2
    exit 69
  fi
done

mapfile -d '' -t worktree < <(git ls-files -z -co --exclude-standard)

shell_files=()
markdown_files=()
for path in "${worktree[@]}"; do
  [[ -f "$path" ]] || continue
  case "$path" in
    *.sh) shell_files+=("$path") ;;
    *.md) markdown_files+=("$path") ;;
    *)
      first_line="$(head -n 1 -- "$path" 2>/dev/null || true)"
      case "$first_line" in
        '#!'*bash* | '#!'*'/sh'* | '#!'*' sh'*) shell_files+=("$path") ;;
      esac
      ;;
  esac
done

if ((${#shell_files[@]} == 0 || ${#markdown_files[@]} == 0)); then
  printf 'ERROR: expected both shell and Markdown files in the working tree\n' >&2
  exit 70
fi
printf 'Check-only lint: %d shell files, %d Markdown files\n' \
  "${#shell_files[@]}" "${#markdown_files[@]}"

# The certifier's original shellcheck input (source hermes-certify-vm.sh). Kept
# exactly so the promoted gate does not silently narrow its reviewed coverage;
# run at default severity.
certifier_shell=()
for path in hermes-deploy.sh hermes-certify-vm.sh tests/test-hermes-e2e-vm.sh \
  vm/create-hermes-server-vm.sh vm/lib-hermes-luks-console.sh vm/lib-vm-common.sh; do
  [[ -f "$path" ]] && certifier_shell+=("$path")
done
for path in scripts/hermes/*.sh; do
  [[ -f "$path" ]] && certifier_shell+=("$path")
done

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

run "shellcheck (certifier reviewed set, default severity)" \
  shellcheck "${certifier_shell[@]}"
run "shellcheck (whole working tree, repository error-only gate)" \
  shellcheck --severity=error "${shell_files[@]}"

# Match the pre-commit shfmt hook: check-only diff mode, spec/ excluded.
shfmt_files=()
for path in "${shell_files[@]}"; do
  case "$path" in
    spec/*) ;;
    # These retired, untracked Gate 2 grant sources are byte-bound to the
    # historical 2026-09-24 record. Keep ShellCheck coverage, but do not make
    # a formatting gate demand rewriting the reviewed installed wrapper hash.
    scripts/hermes/manual/lab/gate2-test-grants.sh | scripts/hermes/manual/lab/gate2-test-guest.sh | scripts/hermes/manual/lab/gate2-test-host.sh) ;;
    *) shfmt_files+=("$path") ;;
  esac
done
run "shfmt check-only" shfmt -d -l -i 2 -ci -bn "${shfmt_files[@]}"

# Non-mutating Markdown lint over the tracked and untracked Markdown files.
# `.markdownlint-cli2.yaml` sets fix: false, so the hook reports instead of
# rewriting preserved or maintained documents.
run "markdownlint (check-only)" pre-commit run markdownlint-cli2 --files "${markdown_files[@]}"

# Read-only baseline hooks over the whole working tree. The rewriting hygiene
# hooks are intentionally absent here; they belong to the developer pre-commit
# stage and to `toolbox/run-offline-checks.sh`'s non-mutating checks.
readonly READ_ONLY_HOOKS=(
  check-merge-conflict
  check-case-conflict
  check-executables-have-shebangs
  check-shebang-scripts-are-executable
  check-added-large-files
  check-yaml
  check-json
  check-toml
  detect-private-key
)
for hook in "${READ_ONLY_HOOKS[@]}"; do
  run "pre-commit ${hook}" pre-commit run "$hook" --files "${worktree[@]}"
done

if ((failures > 0)); then
  printf '\nFAIL: %d check-only lint gate(s) failed\n' "$failures" >&2
  exit 1
fi
printf '\nPASS: check-only lint gate passed\n'
