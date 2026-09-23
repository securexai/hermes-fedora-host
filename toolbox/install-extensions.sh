#!/usr/bin/env bash
# Provision the project-declared tool extensions from toolbox/extensions.yaml.
#
# This is the documented, reproducible replacement for ad-hoc container
# customisation. It fetches a version-pinned artefact, verifies its SHA-256, and
# unpacks it inside the repository. It never writes to host or system paths and
# never needs elevated privileges, so removing the Toolbox container loses
# nothing: rerun this script.
#
# Scope: this script installs the repository-local ShellSpec extension only. The
# uv-locked Python tooling is materialised by `uv sync --locked`. Run
# `toolbox/provision-environment.sh` to do both and verify the result.
#
# Usage:
#   toolbox/install-extensions.sh            # install everything missing
#   toolbox/install-extensions.sh --force    # reinstall even if present
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly SCRIPT_DIR REPO_ROOT

SHELLSPEC_VERSION="0.28.1"
SHELLSPEC_SHA256="350d3de04ba61505c54eda31a3c2ee912700f1758b1a80a284bc08fd8b6c5992"
SHELLSPEC_URL="https://github.com/shellspec/shellspec/releases/download/${SHELLSPEC_VERSION}/shellspec-dist.tar.gz"
readonly SHELLSPEC_VERSION SHELLSPEC_SHA256 SHELLSPEC_URL

readonly TOOLS_DIR="${REPO_ROOT}/toolbox/.tools"
readonly SHELLSPEC_DIR="${TOOLS_DIR}/shellspec"

force=0
for arg in "$@"; do
  case "$arg" in
    --force) force=1 ;;
    -h | --help)
      printf 'Usage: %s [--force]\n' "${0##*/}"
      exit 0
      ;;
    *)
      printf 'ERROR: unknown argument: %s\n' "$arg" >&2
      exit 64
      ;;
  esac
done

if [[ -x "${SHELLSPEC_DIR}/shellspec" && "$force" -eq 0 ]]; then
  printf 'shellspec already installed: %s\n' "$("${SHELLSPEC_DIR}/shellspec" --version)"
  exit 0
fi

command -v curl >/dev/null || {
  printf 'ERROR: curl is required\n' >&2
  exit 69
}
command -v tar >/dev/null || {
  printf 'ERROR: tar is required\n' >&2
  exit 69
}
command -v sha256sum >/dev/null || {
  printf 'ERROR: sha256sum is required\n' >&2
  exit 69
}

scratch="$(mktemp -d)"
trap 'rm -rf -- "${scratch}"' EXIT

printf 'Fetching shellspec %s\n' "${SHELLSPEC_VERSION}"
curl -fsSL -o "${scratch}/shellspec-dist.tar.gz" "${SHELLSPEC_URL}"

printf '%s  %s\n' "${SHELLSPEC_SHA256}" "${scratch}/shellspec-dist.tar.gz" | sha256sum -c - >/dev/null

mkdir -p "${TOOLS_DIR}"
rm -rf -- "${SHELLSPEC_DIR}"
tar -xzf "${scratch}/shellspec-dist.tar.gz" -C "${TOOLS_DIR}"

[[ -x "${SHELLSPEC_DIR}/shellspec" ]] || {
  printf 'ERROR: expected executable not found: %s\n' "${SHELLSPEC_DIR}/shellspec" >&2
  exit 70
}

installed="$("${SHELLSPEC_DIR}/shellspec" --version)"
[[ "${installed}" == "${SHELLSPEC_VERSION}" ]] || {
  printf 'ERROR: version mismatch: expected %s, got %s\n' "${SHELLSPEC_VERSION}" "${installed}" >&2
  exit 70
}

printf 'Installed shellspec %s at %s\n' "${installed}" "${SHELLSPEC_DIR}"
