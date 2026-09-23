# shellcheck shell=bash
# ShellSpec spec_helper.sh — loaded before every spec file

# Project root for file path references in Include and file operations
spec_helper_configure() {
  export PROJECT_ROOT="${SHELLSPEC_PROJECT_ROOT}"
}

# Set PROJECT_ROOT immediately for non-configure contexts
export PROJECT_ROOT="${SHELLSPEC_PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
