#!/usr/bin/env bash
# Provision the declared development environment for this repository.
#
# This is the reproducible, repo-owned provisioning step used by
# `.devcontainer/devcontainer.json` (postCreateCommand) and by any fresh Toolbox:
#
#   1. install the repository-local ShellSpec extension (pinned version, verified
#      SHA-256) through toolbox/install-extensions.sh;
#   2. materialise the uv-locked Python tools (Ruff, ty, yamllint) into the
#      gitignored `.venv` with `uv sync --locked`;
#   3. verify the result with toolbox/verify-extensions.sh.
#
# It needs network access the first time (the pinned ShellSpec release and any
# missing uv distributions) and writes only inside the repository, `$UV_*`
# directories and the uv cache. It requires no elevated privileges.
#
# Usage:
#   toolbox/provision-environment.sh
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly SCRIPT_DIR REPO_ROOT

if [[ ! -f "${REPO_ROOT}/pyproject.toml" || ! -f "${REPO_ROOT}/uv.lock" ]]; then
  printf 'ERROR: pyproject.toml and uv.lock are required to provision the locked tooling\n' >&2
  exit 70
fi
command -v uv >/dev/null 2>&1 || {
  printf 'ERROR: uv is required to provision the locked Python tooling\n' >&2
  exit 69
}

printf '=== repository-local extensions ===\n'
bash "${SCRIPT_DIR}/install-extensions.sh" "$@"

printf '\n=== uv-locked Python tooling ===\n'
(
  cd "$REPO_ROOT"
  uv sync --locked
)

printf '\n=== verification ===\n'
bash "${SCRIPT_DIR}/verify-extensions.sh"
