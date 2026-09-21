#!/usr/bin/env python3
"""M03 probe: resolve the profile terminal policy and exercise the real SSH backend.

Run inside the gateway container as the runtime user (UID 10000):

    podman exec --user 10000:10000 --workdir /opt/hermes hermes-gateway \
        /opt/hermes/.venv/bin/python3 /opt/hermes/gateway-ssh/m03-probe.py

This deliberately goes through the same code path the terminal tool uses
(``tools.terminal_scope`` + ``tools.environments.ssh``), so it proves the
profile config resolves to the SSH backend and that a command lands in the
offline worker. It never prints credential material.
"""

import json
import os
import sys

HERMES_HOME = os.environ.get("HERMES_HOME", "/opt/data")

from tools.terminal_scope import build_profile_terminal_scope  # noqa: E402
from tools.environments.ssh import SSHEnvironment  # noqa: E402


def main() -> int:
    policy = build_profile_terminal_scope(HERMES_HOME)
    terminal = {k: v for k, v in sorted(policy.items()) if k.startswith("TERMINAL_")}
    print("resolved_terminal_policy=" + json.dumps(terminal, sort_keys=True))

    backend = terminal.get("TERMINAL_ENV")
    print("resolved_backend=" + str(backend))
    if backend != "ssh":
        print("RESULT=FAIL_UNEXPECTED_BACKEND")
        return 2

    env = SSHEnvironment(
        host=terminal["TERMINAL_SSH_HOST"],
        user=terminal["TERMINAL_SSH_USER"],
        port=int(terminal.get("TERMINAL_SSH_PORT", "22")),
        key_path=terminal.get("TERMINAL_SSH_KEY", ""),
        cwd="~",
        timeout=60,
    )
    try:
        result = env.execute("echo HERMES_WORKER_ROUNDTRIP_OK; id -un; head -1 /etc/os-release")
        rc = result.get("returncode")
        output = str(result.get("output", ""))
        print("execute_returncode=" + str(rc))
        print("execute_output=" + output.strip())
        ok = rc == 0 and "HERMES_WORKER_ROUNDTRIP_OK" in output
        print("RESULT=" + ("PASS" if ok else "FAIL"))
        return 0 if ok else 3
    finally:
        try:
            env.cleanup()
        except Exception as exc:  # noqa: BLE001 - cleanup must not mask the result
            print("cleanup_warning=" + str(exc))


if __name__ == "__main__":
    sys.exit(main())
