#!/bin/bash
# shellcheck shell=bash
#
# Shared test assertion functions for RouterOS configuration validation
#
# Sourced by test-routeros.sh — not executed directly.

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit

PASS=0
FAIL=0
SKIP=0
VERBOSE=false

# --- Output helpers ----------------------------------------------------------

_green() { printf '\033[0;32m%s\033[0m' "$1"; }
_red() { printf '\033[0;31m%s\033[0m' "$1"; }
_yellow() { printf '\033[0;33m%s\033[0m' "$1"; }
_bold() { printf '\033[1m%s\033[0m' "$1"; }

section() {
  echo ""
  _bold "=== $1 ==="
  echo ""
}

# --- Assertions --------------------------------------------------------------

_pass() {
  PASS=$((PASS + 1))
  $VERBOSE && echo "  $(_green PASS): $1" || true
}

_fail() {
  FAIL=$((FAIL + 1))
  echo "  $(_red FAIL): $1"
  [[ -n "${2:-}" ]] && echo "        $2" || true
}

_skip() {
  SKIP=$((SKIP + 1))
  $VERBOSE && echo "  $(_yellow SKIP): $1" || true
}

# assert_equals "expected" "actual" "test name"
assert_equals() {
  local expected="$1" actual="$2" name="$3"
  if [[ "$expected" == "$actual" ]]; then
    _pass "$name"
  else
    _fail "$name" "expected: '$expected', got: '$actual'"
  fi
}

# assert_contains "needle" "haystack" "test name"
assert_contains() {
  local needle="$1" haystack="$2" name="$3"
  if echo "$haystack" | grep -qF -- "$needle"; then
    _pass "$name"
  else
    _fail "$name" "string not found: '$needle'"
  fi
}

# assert_grep "pattern" "file" "test name"
assert_grep() {
  local pattern="$1" file="$2" name="$3"
  if grep -qE -- "$pattern" "$file"; then
    _pass "$name"
  else
    _fail "$name" "pattern not found: '$pattern'"
  fi
}

# assert_no_grep "pattern" "file" "test name"
assert_no_grep() {
  local pattern="$1" file="$2" name="$3"
  if ! grep -qE -- "$pattern" "$file"; then
    _pass "$name"
  else
    local match
    match=$(grep -m1 -nE -- "$pattern" "$file")
    _fail "$name" "unexpected match: $match"
  fi
}

# assert_order "pattern_first" "pattern_second" "file" "test name"
# Checks that the first occurrence of pattern_first appears before pattern_second
assert_order() {
  local first="$1" second="$2" file="$3" name="$4"
  local line_first line_second
  line_first=$(grep -m1 -nE -- "$first" "$file" | head -1 | cut -d: -f1)
  line_second=$(grep -m1 -nE -- "$second" "$file" | head -1 | cut -d: -f1)

  if [[ -z "$line_first" ]]; then
    _fail "$name" "first pattern not found: '$first'"
  elif [[ -z "$line_second" ]]; then
    _fail "$name" "second pattern not found: '$second'"
  elif [[ "$line_first" -lt "$line_second" ]]; then
    _pass "$name"
  else
    _fail "$name" "line $line_first ('$first') should be before line $line_second ('$second')"
  fi
}

# assert_set_equals "expected_items" "actual_items" "test name"
# Both args are newline-separated sorted lists
assert_set_equals() {
  local expected="$1" actual="$2" name="$3"
  local missing extra
  missing=$(comm -23 <(echo "$expected" | sort) <(echo "$actual" | sort))
  extra=$(comm -13 <(echo "$expected" | sort) <(echo "$actual" | sort))

  if [[ -z "$missing" && -z "$extra" ]]; then
    _pass "$name"
  else
    local detail=""
    [[ -n "$missing" ]] && detail="missing: $(echo "$missing" | tr '\n' ' ')"
    [[ -n "$extra" ]] && detail="${detail:+$detail; }extra: $(echo "$extra" | tr '\n' ' ')"
    _fail "$name" "$detail"
  fi
}

# assert_min_count "min" "actual_count" "test name"
# Guards against silent pass-by-absence when extraction returns empty
assert_min_count() {
  local min="$1" actual="$2" name="$3"
  if [[ "$actual" -ge "$min" ]]; then
    _pass "$name"
  else
    _fail "$name" "expected at least $min, got $actual"
  fi
}

# --- Summary -----------------------------------------------------------------

# Exits non-zero if any test failed (used as script exit code)
print_summary() {
  local total=$((PASS + FAIL + SKIP))
  echo ""
  echo "========================================"
  printf "Results: %s passed, %s failed, %s skipped (%d total)\n" \
    "$(_green "$PASS")" \
    "$(_red "$FAIL")" \
    "$(_yellow "$SKIP")" \
    "$total"
  echo "========================================"
  [[ "$FAIL" -eq 0 ]]
}
