#!/usr/bin/env bash
# Validate the project-declared tool extensions and re-assert the parts of the
# shared profile contract this project depends on.
#
# This check modifies no tracked file and never installs, downloads or
# synchronises anything: it runs the uv-locked tools with UV_NO_SYNC=1, so a
# missing environment fails clearly instead of being materialised as a side
# effect of verification. Provision first with
# `toolbox/provision-environment.sh` (ShellSpec install + `uv sync --locked`).
# Run it inside the dev-toolbox `infra` container.
#
# Usage:
#   toolbox/verify-extensions.sh
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly SCRIPT_DIR REPO_ROOT

readonly SHELLSPEC_VERSION="0.28.1"
readonly SHELLSPEC_BIN="${REPO_ROOT}/toolbox/.tools/shellspec/shellspec"

failures=0

pass() { printf 'PASS: %s\n' "$*"; }
fail() {
  printf 'FAIL: %s\n' "$*" >&2
  failures=$((failures + 1))
}

# --- shared profile contract (mirrors dev-toolbox scripts/verify.sh) ---------
for tool in git gh curl ssh jq rg make pre-commit shellcheck shfmt betterleaks; do
  if command -v "$tool" >/dev/null 2>&1; then
    pass "profile tool present: ${tool}"
  else
    fail "profile tool missing: ${tool}"
  fi
done

if [[ -s /usr/share/dev-toolbox/rpm-manifest.txt ]]; then
  pass "rpm manifest present ($(wc -l </usr/share/dev-toolbox/rpm-manifest.txt) packages)"
else
  fail "rpm manifest missing or empty: /usr/share/dev-toolbox/rpm-manifest.txt"
fi

for dir in "${PRE_COMMIT_HOME:-}" "${UV_TOOL_DIR:-}" "${UV_TOOL_BIN_DIR:-}" "${UV_CACHE_DIR:-}" "${UV_PYTHON_INSTALL_DIR:-}"; do
  if [[ -z "$dir" ]]; then
    fail "managed directory variable is unset"
  elif [[ ! -w "$dir" ]]; then
    fail "managed directory not writable: ${dir}"
  elif [[ "$dir" != /opt/* ]]; then
    fail "managed directory outside /opt: ${dir}"
  else
    pass "managed directory writable: ${dir}"
  fi
done

# --- declared extension: shellspec ------------------------------------------
if [[ -x "$SHELLSPEC_BIN" ]]; then
  installed="$("$SHELLSPEC_BIN" --version)"
  if [[ "$installed" == "$SHELLSPEC_VERSION" ]]; then
    pass "shellspec ${installed}"
  else
    fail "shellspec version mismatch: expected ${SHELLSPEC_VERSION}, got ${installed}"
  fi
else
  fail "shellspec not installed at ${SHELLSPEC_BIN} (run toolbox/install-extensions.sh)"
fi

# --- declared extensions: Python tooling pinned by uv.lock -------------------
if [[ -f "${REPO_ROOT}/pyproject.toml" && -f "${REPO_ROOT}/uv.lock" ]]; then
  for cmd in "ruff --version" "ty --version" "yamllint --version"; do
    # shellcheck disable=SC2086 # deliberate word splitting into command + args
    if out="$(cd "$REPO_ROOT" && UV_NO_SYNC=1 UV_PYTHON_DOWNLOADS=never uv run --quiet --locked $cmd 2>&1)"; then
      pass "uv-locked ${cmd%% *}: ${out%%$'\n'*}"
    else
      fail "uv-locked '${cmd}' failed: ${out}"
    fi
  done
else
  fail "pyproject.toml and uv.lock are required to validate locked tooling"
fi

if ((failures > 0)); then
  printf '\nFAIL: %d extension/contract check(s) failed\n' "$failures" >&2
  exit 1
fi
printf '\nPASS: declared extensions and profile contract verified\n'
