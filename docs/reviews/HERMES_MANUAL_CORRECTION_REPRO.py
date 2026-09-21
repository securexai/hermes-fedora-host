#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Replay independent review counterexamples against the fingerprinted tree.

Uses the reviewed repository's existing synthetic Bash fixture setup, with
in-memory fault injection only. No source changes, actual containers, privileged
commands, credentials, or network access. Refuses a different input fingerprint.
Exit 1 means review counterexamples were observed, not a harness failure.
Exit 2 means the tree/setup did not match the reviewed assumptions.

Run: python3 -B docs/HERMES_MANUAL_CORRECTION_REPRO.py [mikrotik-repository]
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

EXPECTED = "6219b73768a098fb44c93b95b67d9d9430cb9132ce884c2d01399c1a361d8ee2"
DEFAULT_REPO = Path("/var/home/aicloudopspecial/code/repos/mikrotik")


def fingerprint(repo: Path) -> str:
    paths: set[str] = set()
    for args in (("diff", "--name-only", "-z"),
                 ("ls-files", "--others", "--exclude-standard", "-z")):
        output = subprocess.check_output(["git", *args], cwd=repo).decode()
        paths.update(filter(None, output.split("\0")))
    aggregate = hashlib.sha256()
    for name in sorted(paths):
        aggregate.update(name.encode() + b"\0" + hashlib.sha256((repo / name).read_bytes()).digest())
    return aggregate.hexdigest()


def run(repo: Path, script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-s"], input=script, text=True, capture_output=True,
        cwd=repo, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        timeout=60, check=False,
    )


def fixture(repo: Path, filename: str, boundary: str) -> str:
    source = (repo / "tests" / filename).read_text()
    if source.count(boundary) != 1:
        raise ValueError(f"Unexpected fixture boundary: {filename}")
    setup = source.split(boundary)[0]
    old = 'SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)'
    if setup.count(old) != 1:
        raise ValueError(f"Unexpected fixture directory setup: {filename}")
    return setup.replace(old, f"SCRIPT_DIR={shlex.quote(str(repo / 'tests'))}")


def show(name: str, result: subprocess.CompletedProcess[str]) -> None:
    print(f"\n===== {name} (process exit {result.returncode}) =====")
    print(result.stdout, end="")
    print(result.stderr, end="")


def checked_fixture(repo: Path, name: str, script: str) -> str:
    result = run(repo, script)
    show(name, result)
    if result.returncode != 0:
        raise RuntimeError(f"Fixture setup/execution failed: {name}")
    return result.stdout


def main() -> int:
    repo = (Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_REPO).resolve()
    actual = fingerprint(repo)
    print(f"REVIEWED_INPUT={actual}")
    if actual != EXPECTED:
        raise ValueError("Input changed; inspect and reauthorize fixture assumptions before replay")
    violations: list[str] = []
    lib = shlex.quote(str(repo / "scripts/hermes/manual/lib-manual-common.sh"))
    with tempfile.TemporaryDirectory(prefix="hermes-correction-review-") as temp:
        log = shlex.quote(str(Path(temp) / "checks.log"))
        result = run(repo, f'''source {lib}
bad() {{ return 1; }}
mp_on_cleanup bad
mp_install_trap
mp_check primary PASS >{log}
mp_finalize {log} 0
''')
        show("C1 cleanup after successful finalize", result)
        if result.returncode == 0 and "RESULT=PASS" in result.stdout and "CLEANUP_FAILED" in result.stderr:
            violations.append("C1 cleanup failure still exits 0 after PASS")
    control = run(repo, f'''source {lib}
bad() {{ return 1; }}
mp_on_cleanup bad
mp_install_trap
exit 7
''')
    if control.returncode != 7:
        raise RuntimeError("Primary-failure preservation control did not return 7")
    print("Primary failure control: exit 7 preserved")

    setup = fixture(repo, "test-hermes-manual-backup.sh", "# --- happy path ---")
    setup = setup.replace(
        "  is-active)\n",
        '  is-active)\n    if [ ! -e "${STUB_STATES}/stopped-once" ]; then exit 1; fi\n', 1,
    ).replace("  stop)\n", '  stop)\n    : >"${STUB_STATES}/stopped-once"\n', 1)
    output = checked_fixture(repo, "C2 unknown initial backup service state", setup + r'''
reset_sandbox prior-query-failure
rc=0
out=$(run_backup prior-query-failure) || rc=$?
printf '%s\n' "$out" | /usr/bin/grep -E '^CHECK writers_stopped|^CHECK backup_archive|^RESULT='
printf 'ACTUAL_EXIT=%s FINAL_WORKER=%s FINAL_GATEWAY=%s\n' "$rc" "$(<"$STATES/hermes-worker.service")" "$(<"$STATES/hermes-gateway.service")"
/usr/bin/grep -E 'state_at_exit|CHECK restore_service_state' "$ADMIN_HOME/hermes-m04-backup.out"
if [ "$rc" -eq 0 ] && [ "$(<"$STATES/hermes-worker.service")" = inactive ] && [ "$(<"$STATES/hermes-gateway.service")" = inactive ]; then
  printf 'VIOLATION=C2\n'
fi
exit 0
''')
    if "VIOLATION=C2" in output:
        violations.append("C2 unknown prior state permits backup to leave formerly active services stopped")

    setup = fixture(repo, "test-hermes-manual-configure.sh", "# --- converged ---")
    output = checked_fixture(repo, "C3 live exec identity / C4 failed state query", setup + r'''
seed_converged
rc=0
out=$(run_configure --apply) || rc=$?
printf '%s\n' "$out" | /usr/bin/grep -E 'real backend probe|CHECK terminal_backend_probe|^RESULT='
printf 'ACTUAL_EXIT=%s\n' "$rc"
/usr/bin/grep '^podman exec ' "$CALL_LOG" | head -n 2
if [ "$rc" -eq 0 ] && /usr/bin/grep -q '^podman exec hermes-gateway ' "$CALL_LOG"; then
  printf 'VIOLATION=C3 (no explicit runtime UID/GID in live exec)\n'
fi
write_stub systemctl <<'EOF'
#!/usr/bin/env bash
printf 'systemctl %s\n' "$*" >>"${STUB_CALL_LOG:?}"
printf 'Failed to connect to user bus\n' >&2
exit 1
EOF
seed_converged
rc=0
out=$(run_configure --apply) || rc=$?
printf '%s\n' "$out" | /usr/bin/grep -E 'already converged|^RESULT='
printf 'ACTUAL_EXIT=%s SYNTHETIC_CONTAINER_STATE=%s\n' "$rc" "$(<"$STATES/hermes-gateway.service")"
/usr/bin/grep '^podman-run-state-mount' "$CALL_LOG"
if [ "$rc" -eq 0 ] && /usr/bin/grep -q '^podman-run-state-mount gateway_active=yes' "$CALL_LOG"; then
  printf 'VIOLATION=C4\n'
fi
exit 0
''')
    if "VIOLATION=C3" in output:
        violations.append("C3 live exec omits the required runtime UID/GID")
    if "VIOLATION=C4" in output:
        violations.append("C4 unknown service state permits live-mount relabeling commands and PASS")

    setup = fixture(repo, "test-hermes-manual-contract.sh", "# --- fresh state must be handed")
    output = checked_fixture(repo, "C5 contract private-mount command path", setup + r'''
# Simulate a retained active gateway; no real service exists or is queried.
printf 'active\n' >"$SANDBOX/gateway-state-marker"
write_stub systemctl <<'EOF'
#!/usr/bin/env bash
printf 'systemctl %s\n' "$*" >>"${STUB_CALL_LOG:?}"
marker="$(dirname "$STUB_CALL_LOG")/gateway-state-marker"
case "${2:-}" in
  is-active) /usr/bin/cat "$marker" ;;
  stop) printf 'inactive\n' >"$marker" ;;
  start) printf 'active\n' >"$marker" ;;
esac
EOF
seed_state_dir 0700
reset_calls
STUB_NS_UID=10000
rc=0
out=$(run_contract) || rc=$?
printf '%s\n' "$out" | /usr/bin/grep -E '^CHECK contract_verified|^RESULT='
z_runs=$(/usr/bin/grep -c '^podman run .*gateway-ssh:/opt/hermes/gateway-ssh:ro,Z' "$CALL_LOG" || true)
stop_calls=$(/usr/bin/grep -c '^systemctl --user stop' "$CALL_LOG" || true)
printf 'ACTUAL_EXIT=%s PRIVATE_Z_RUNS=%s QUIESCE_CALLS=%s SYNTHETIC_GATEWAY=%s\n' "$rc" "$z_runs" "$stop_calls" "$(<"$SANDBOX/gateway-state-marker")"
if [ "$rc" -eq 0 ] && [ "$z_runs" -gt 0 ] && [ "$stop_calls" -eq 0 ]; then
  printf 'VIOLATION=C5 (command observation; actual SELinux effect not tested)\n'
fi
exit 0
''')
    if "VIOLATION=C5" in output:
        violations.append("C5 contract helper mounts live private material with :Z without quiescence")
    if fingerprint(repo) != EXPECTED:
        raise RuntimeError("Repository inputs changed during replay")
    for violation in violations:
        print(f"OBSERVED {violation}")
    print(f"REVIEW_REPRO={'FAIL' if violations else 'PASS'} open={len(violations)}")
    return 1 if violations else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"REVIEW_REPRO=HARNESS_ERROR {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
