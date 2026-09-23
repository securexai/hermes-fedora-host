"""Negative controls for toolbox/scan-secrets.sh.

The script runs a synthetic positive control before the full working-tree scan.
An independent re-review showed that the previous implementation treated *any*
non-zero scanner exit as "positive control detected", so a scanner operational
error (exit 2) was reported as a passing control and the whole check exited 0.

A later independent re-review showed that the report classifier still printed
arbitrary ``RuleID`` values from the scanner's JSON report. A scanner that put an
unredacted token in a report field therefore leaked it to stderr even though the
scan failed closed. These controls plant the script's own synthetic token in
``RuleID``, in other report fields and in malformed or non-UTF-8 report bodies,
and assert that no report-derived text reaches the output.

These tests put a controlled fake ``betterleaks`` first on ``PATH`` and drive the
real script. They never run a real secret scanner against real credentials.
"""

import os
import pathlib
import stat
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
SCANNER = REPO_ROOT / "toolbox" / "scan-secrets.sh"

FAKE_SCANNER = r"""#!/usr/bin/env bash
# Controlled fake betterleaks. Behaviour is selected by environment variables.
set -u
state="${FAKE_STATE:?}"
count_file="${state}/count"
n=0
[[ -f "$count_file" ]] && n="$(cat "$count_file")"
n=$((n + 1))
printf '%s' "$n" >"$count_file"
report=""
target=""
args=("$@")
i=0
while (( i < ${#args[@]} )); do
  a="${args[i]}"
  case "$a" in
    --report-path) report="${args[i + 1]:-}"; i=$((i + 2)); continue ;;
    --report-format|--config|--exit-code|--log-level) i=$((i + 2)); continue ;;
    dir|file|directory|git) i=$((i + 1)); continue ;;
    --*) i=$((i + 1)); continue ;;
    *) [[ -z "$target" ]] && target="$a"; i=$((i + 1)); continue ;;
  esac
done
if (( n == 1 )); then mode="${FAKE_CONTROL_MODE:-finding}"; else mode="${FAKE_FULL_MODE:-clean}"; fi
# On the control invocation, capture the script's own synthetic token so later
# invocations can plant it in report fields the wrapper must never echo.
canary=""
if (( n == 1 )) && [[ -n "$target" && -f "$target" ]]; then
  canary="$(grep -o 'ghp_[A-Za-z0-9]*' "$target" | head -n 1 || true)"
  [[ -n "$canary" ]] && printf '%s' "$canary" >"${state}/token"
fi
[[ -f "${state}/token" ]] && canary="$(cat "${state}/token")"
emit() {
  printf '[{"RuleID":"%s","File":"%s","Secret":"%s","Match":"%s"}]\n' \
    "$1" "$2" "${FAKE_LEAK:-REDACTED}" "${FAKE_LEAK:-REDACTED}" >"$report"
}
case "$mode" in
  finding) emit github-pat "$target"; printf '%s\n' "${FAKE_LEAK:-}" >&2; exit 1 ;;
  nofinding) printf 'null\n' >"$report"; exit 0 ;;
  error2) exit 2 ;;
  malformed) printf 'not-json\n' >"$report"; exit 1 ;;
  wrongrule) emit aws-access-token "$target"; exit 1 ;;
  wrongfile) emit github-pat "/tmp/unrelated-file.txt"; exit 1 ;;
  unredacted)
    printf '[{"RuleID":"github-pat","File":"%s","Secret":"%s"}]\n' "$target" "$(cat "$target")" >"$report"
    exit 1
    ;;
  ruleid-canary) emit "$canary" "$target"; exit 1 ;;
  field-canary)
    printf '[{"RuleID":"github-pat","File":"%s","Secret":"%s","Match":"%s","Description":"%s","Extra":[{"note":"%s"}]}]\n' \
      "$target" "$canary" "$canary" "$canary" "$canary" >"$report"
    exit 1
    ;;
  raw-canary) printf '%s\n' "$canary" >"$report"; exit 1 ;;
  binary-canary) printf '%s\xff\xfe\n' "$canary" >"$report"; exit 1 ;;
  findings) emit github-pat "$target"; exit 1 ;;
  clean) printf 'null\n' >"$report"; exit 0 ;;
  *) exit 0 ;;
esac
"""

LEAK_TOKEN = "ghp_LEAKCANARY0123456789abcdef"


class SecretScanTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="hermes-secret-scan-")
        self.addCleanup(self._tmp.cleanup)
        self.root = pathlib.Path(self._tmp.name)
        self.fake_bin = self.root / "bin"
        self.state = self.root / "state"
        self.fake_bin.mkdir()
        self.state.mkdir()
        fake = self.fake_bin / "betterleaks"
        fake.write_text(FAKE_SCANNER)
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def run_scan(self, control_mode="finding", full_mode="clean"):
        env = dict(
            os.environ,
            PATH=f"{self.fake_bin}{os.pathsep}{os.environ['PATH']}",
            FAKE_STATE=str(self.state),
            FAKE_CONTROL_MODE=control_mode,
            FAKE_FULL_MODE=full_mode,
            FAKE_LEAK=LEAK_TOKEN,
        )
        return subprocess.run(
            ["bash", str(SCANNER)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )

    def assert_no_leak(self, result):
        combined = result.stdout + result.stderr
        self.assertNotIn(LEAK_TOKEN, combined, "the scan printed an unredacted token")

    def test_correct_positive_control_and_clean_full_scan_pass(self):
        result = self.run_scan()
        self.assert_no_leak(result)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("positive control", result.stdout)

    def test_control_with_no_finding_fails(self):
        result = self.run_scan(control_mode="nofinding")
        self.assert_no_leak(result)
        self.assertNotEqual(result.returncode, 0)

    def test_control_operational_error_exit_two_fails(self):
        result = self.run_scan(control_mode="error2")
        self.assert_no_leak(result)
        self.assertNotEqual(result.returncode, 0)

    def test_control_malformed_report_fails(self):
        result = self.run_scan(control_mode="malformed")
        self.assert_no_leak(result)
        self.assertNotEqual(result.returncode, 0)

    def test_control_wrong_rule_fails(self):
        result = self.run_scan(control_mode="wrongrule")
        self.assert_no_leak(result)
        self.assertNotEqual(result.returncode, 0)

    def test_control_wrong_file_fails(self):
        result = self.run_scan(control_mode="wrongfile")
        self.assert_no_leak(result)
        self.assertNotEqual(result.returncode, 0)

    def test_control_report_not_redacted_fails(self):
        result = self.run_scan(control_mode="unredacted")
        self.assert_no_leak(result)
        self.assertNotEqual(result.returncode, 0)

    def test_full_scan_findings_fail_after_valid_control(self):
        result = self.run_scan(full_mode="findings")
        self.assert_no_leak(result)
        self.assertNotEqual(result.returncode, 0)

    def test_full_scan_operational_error_fails_after_valid_control(self):
        result = self.run_scan(full_mode="error2")
        self.assert_no_leak(result)
        self.assertNotEqual(result.returncode, 0)

    def test_full_scan_malformed_report_fails_after_valid_control(self):
        result = self.run_scan(full_mode="malformed")
        self.assert_no_leak(result)
        self.assertNotEqual(result.returncode, 0)

    # -- P2-2: report fields must never reach the log -------------------------

    def scan_token(self):
        """The synthetic token the wrapper generated for the positive control."""
        token = (self.state / "token").read_text()
        self.assertTrue(token.startswith("ghp_"), token)
        return token

    def assert_token_not_echoed(self, result, token, reason):
        self.assertNotIn(token, result.stdout + result.stderr, reason)

    def test_full_scan_rule_identifier_canary_is_not_echoed(self):
        result = self.run_scan(full_mode="ruleid-canary")
        self.assertNotEqual(result.returncode, 0)
        self.assert_token_not_echoed(
            result, self.scan_token(), "a full-report RuleID reached the log"
        )

    def test_full_scan_unexpected_field_canary_is_not_echoed(self):
        result = self.run_scan(full_mode="field-canary")
        self.assertNotEqual(result.returncode, 0)
        self.assert_token_not_echoed(
            result, self.scan_token(), "a full-report field value reached the log"
        )

    def test_control_rule_identifier_canary_is_not_echoed(self):
        result = self.run_scan(control_mode="ruleid-canary")
        self.assertNotEqual(result.returncode, 0)
        self.assert_token_not_echoed(
            result, self.scan_token(), "a control-report RuleID reached the log"
        )

    def test_malformed_report_body_canary_is_not_echoed(self):
        result = self.run_scan(control_mode="raw-canary")
        self.assertNotEqual(result.returncode, 0)
        self.assert_token_not_echoed(
            result, self.scan_token(), "a malformed report body reached the log"
        )

    def test_malformed_full_report_body_canary_is_not_echoed(self):
        result = self.run_scan(full_mode="raw-canary")
        self.assertNotEqual(result.returncode, 0)
        self.assert_token_not_echoed(
            result, self.scan_token(), "a malformed full-report body reached the log"
        )

    def test_non_utf8_report_is_classified_not_crashed(self):
        # Scope note: this control's report bytes are not valid JSON at all, so
        # replacement decoding lands them on the fixed "invalid-json" reason.
        # Replacement decoding does not reject every non-UTF-8 report: invalid
        # bytes inside an otherwise valid JSON string are normalized and the
        # report can still parse to a finding. The guarantee under test is that
        # no uncaught decode error and no report-derived text reaches the log.
        result = self.run_scan(control_mode="binary-canary")
        combined = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", combined, "an uncaught decode error escaped the classifier")
        self.assertIn("malformed", combined)
        self.assert_token_not_echoed(
            result, self.scan_token(), "a non-UTF-8 report body reached the log"
        )
