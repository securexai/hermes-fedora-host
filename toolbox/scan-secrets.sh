#!/usr/bin/env bash
# Non-writing secret scan over the full reviewed working tree.
#
# Why this exists:
#   The pre-commit `betterleaks` hook is a *staged* scan. Its upstream entry is
#   fixed as `betterleaks git --pre-commit --redact --staged --verbose`, so
#   passing filenames to that hook cannot widen it. On a working tree with
#   nothing staged the hook scans 0 bytes and "Passed" proves nothing about the
#   imported content.
#
# What it does:
#   1. Scans a synthetic, positively detectable token as a control. The control
#      passes only when the scanner exits with the documented findings exit code
#      AND the redacted structured report contains the expected rule for that
#      exact synthetic file. A no-finding result, an operational error (any other
#      exit code), malformed output or an unrelated finding all fail the control.
#   2. Scans every tracked and untracked (non-ignored) file in the working tree,
#      including files that were never staged, with live provider validation
#      disabled (`--validation=false`) so the check is offline and deterministic.
#
# Scanner output is never echoed. Only fixed classifications and numeric counts
# are printed: no rule identifier, path, redaction field or JSON error text from
# the scanner's report is ever interpolated into a message, so a misbehaving or
# hostile scanner cannot use a report field to place an unredacted token in the
# log. Reports live in a temporary directory outside the repository.
#
# This script never writes inside the repository: the control token lives in a
# temporary directory outside it. Run it inside the dev-toolbox `infra` container.
#
# Usage:
#   toolbox/scan-secrets.sh
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly SCRIPT_DIR REPO_ROOT
readonly CONFIG="${REPO_ROOT}/.betterleaks.toml"
readonly FINDINGS_EXIT=1
readonly EXPECTED_CONTROL_RULE="github-pat"

cd "$REPO_ROOT"

for command in betterleaks git mktemp openssl python3; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf 'ERROR: %s is required for the secret scan\n' "$command" >&2
    exit 69
  fi
done

mapfile -d '' -t tracked_and_untracked < <(git ls-files -z -co --exclude-standard)
if ((${#tracked_and_untracked[@]} == 0)); then
  printf 'ERROR: git returned no working-tree files to scan\n' >&2
  exit 70
fi

# Keep only paths that still exist as regular files (a tracked-but-deleted path
# must not abort the scan).
files=()
for path in "${tracked_and_untracked[@]}"; do
  [[ -f "$path" ]] && files+=("$path")
done
if ((${#files[@]} == 0)); then
  printf 'ERROR: no existing working-tree files to scan\n' >&2
  exit 70
fi
printf 'Secret scan: %d tracked/untracked files (validation disabled)\n' "${#files[@]}"

work="$(mktemp -d)"
trap 'rm -rf -- "${work}"' EXIT
control="${work}/synthetic-positive-control.txt"
control_report="${work}/control-report.json"
full_report="${work}/full-report.json"

cat >"${work}/report_check.py" <<'PY'
"""Classify a redacted betterleaks JSON report without printing its contents.

Only fixed classifications and numeric counts are printed. Report-derived
strings (rule identifiers, paths, Match/Secret values, JSON error text) are
NEVER echoed, so a misbehaving scanner cannot smuggle an unredacted token into
this script's output through any report field.
"""

import json
import os
import re
import sys

# Fixed reason codes; never derived from report content.
MALFORMED_REASONS = ("unreadable", "empty", "invalid-json", "not-a-list", "entry-shape")


def load_report(path):
    try:
        # errors="replace" prevents an uncaught decode error on non-UTF-8 report
        # bytes; it does not reject every non-UTF-8 report. It normalizes invalid
        # bytes, so bytes that break JSON syntax fall through to "invalid-json",
        # while invalid bytes inside an otherwise valid JSON string are replaced
        # and the report can still parse to a finding. The finding is still
        # classified as a finding, and no report field is ever printed.
        with open(path, encoding="utf-8", errors="replace") as stream:
            raw = stream.read().strip()
    except OSError:
        return None, "unreadable"
    if not raw:
        return None, "empty"
    try:
        data = json.loads(raw)
    except ValueError:
        return None, "invalid-json"
    if data is None:
        return [], ""
    if not isinstance(data, list):
        return None, "not-a-list"
    findings = []
    for item in data:
        if not isinstance(item, dict) or "RuleID" not in item or "File" not in item:
            return None, "entry-shape"
        findings.append((str(item["RuleID"]), str(item["File"])))
    return findings, ""


def main(argv):
    mode, report, expected, *rest = argv
    findings, error = load_report(report)
    if error:
        # Defensive: even a future edit of load_report cannot print anything but
        # a fixed reason code.
        print("MALFORMED " + (error if error in MALFORMED_REASONS else "entry-shape"))
        return 0
    if mode == "empty":
        # Count only: rule identifiers from the report are untrusted text.
        print("EMPTY" if not findings else f"FINDINGS {len(findings)}")
        return 0
    control = rest[0] if rest else ""
    if control:
        with open(control, encoding="utf-8", errors="replace") as stream:
            match = re.search(r"ghp_[A-Za-z0-9]+", stream.read())
        if match:
            with open(report, encoding="utf-8", errors="replace") as stream:
                if match.group(0) in stream.read():
                    print("UNREDACTED")
                    return 0
    rules = {rule for rule, _ in findings}
    if not findings:
        print("NO-FINDING")
    elif expected not in rules:
        print("WRONG-RULE")
    elif not any(
        rule == expected and os.path.realpath(path) == os.path.realpath(control)
        for rule, path in findings
    ):
        print("WRONG-FILE")
    else:
        print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
PY

# The control token is generated here, never committed and never validated
# against a provider. The repository allowlist does not match it, and a
# low-entropy sequential filler is NOT used: it must stay positively detectable.
printf 'synthetic positive control: ghp_%s\n' "$(openssl rand -hex 18)" >"$control"

# 1) Positive control: the scanner must report the expected finding for this
#    exact synthetic file with the documented findings exit code.
control_rc=0
betterleaks dir "$control" --config "$CONFIG" --validation=false --redact \
  --no-banner --no-color --exit-code "$FINDINGS_EXIT" \
  --report-format json --report-path "$control_report" \
  >"${work}/control.stdout" 2>"${work}/control.stderr" || control_rc=$?

if ((control_rc != FINDINGS_EXIT)); then
  printf 'FAIL: scanner positive control exited %d, expected the findings exit %d; ' "$control_rc" "$FINDINGS_EXIT" >&2
  printf 'a no-finding or operational-error result makes a green full-tree scan meaningless\n' >&2
  exit 1
fi

control_status="$(python3 "${work}/report_check.py" control "$control_report" "$EXPECTED_CONTROL_RULE" "$control")"
case "$control_status" in
  OK)
    printf 'PASS: scanner positive control reported a redacted %s finding for the synthetic file\n' "$EXPECTED_CONTROL_RULE"
    ;;
  NO-FINDING)
    printf 'FAIL: the scanner did not report the synthetic positive control despite exit %d\n' "$FINDINGS_EXIT" >&2
    exit 1
    ;;
  WRONG-RULE*)
    printf 'FAIL: the positive control finding did not use the expected %s rule\n' "$EXPECTED_CONTROL_RULE" >&2
    exit 1
    ;;
  WRONG-FILE)
    printf 'FAIL: the positive control finding did not cite the synthetic control file\n' >&2
    exit 1
    ;;
  UNREDACTED)
    printf 'FAIL: the positive control report contained the token unredacted\n' >&2
    exit 1
    ;;
  MALFORMED*)
    printf 'FAIL: the positive control report was malformed (%s)\n' "${control_status#MALFORMED }" >&2
    exit 1
    ;;
  *)
    printf 'FAIL: the positive control could not be evaluated (%s)\n' "$control_status" >&2
    exit 1
    ;;
esac

# 2) Full working-tree scan.
full_rc=0
betterleaks dir "${files[@]}" --config "$CONFIG" --validation=false --redact \
  --no-banner --no-color --exit-code "$FINDINGS_EXIT" \
  --report-format json --report-path "$full_report" \
  >"${work}/full.stdout" 2>"${work}/full.stderr" || full_rc=$?

full_status="$(python3 "${work}/report_check.py" empty "$full_report" "$EXPECTED_CONTROL_RULE")"
if ((full_rc == 0)); then
  case "$full_status" in
    EMPTY)
      printf 'PASS: no findings in the full reviewed working tree\n'
      ;;
    FINDINGS*)
      printf 'FAIL: the full working-tree scan reported %s findings\n' "${full_status#FINDINGS }" >&2
      exit 1
      ;;
    MALFORMED*)
      printf 'FAIL: the full working-tree scanner report was malformed (%s)\n' "${full_status#MALFORMED }" >&2
      exit 1
      ;;
    *)
      printf 'FAIL: unexpected full working-tree scanner state (%s)\n' "$full_status" >&2
      exit 1
      ;;
  esac
elif ((full_rc == FINDINGS_EXIT)); then
  printf 'FAIL: the full working-tree scan reported findings (scanner exit %d)\n' "$full_rc" >&2
  exit 1
else
  printf 'FAIL: the full working-tree scan failed with scanner exit %d (operational error)\n' "$full_rc" >&2
  exit 1
fi
