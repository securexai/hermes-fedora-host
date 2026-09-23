"""Shared opt-in gate for reviewed integration tests.

The offline gate runs only the explicitly reviewed unit targets listed in
``tests/offline_allowlist.txt``. Tests that touch real VM, disk, firmware or
service tooling (guestfish, qemu-img, ukify, dracut-install, a real sshd binary)
are listed separately in ``tests/integration_allowlist.txt`` and run only from
the explicit opt-in runner ``toolbox/run-integration-checks.sh``, which exports
``HERMES_RUN_INTEGRATION_TESTS=1``.

Tool availability is not authorization: installing libguestfs, a kernel package
or openssh-server must not silently pull host-mutating work into the pre-push
gate. Integration acceptance stays NOT RUN unless an operator opts in.
"""

import os
import unittest

INTEGRATION_ENV = "HERMES_RUN_INTEGRATION_TESTS"


def integration_only(reason):
    """Return a skip decorator that requires the explicit integration opt-in.

    Stack it with any tool-availability decorator the individual test needs.
    """
    return unittest.skipUnless(
        os.environ.get(INTEGRATION_ENV) == "1",
        "opt-in integration test: set "
        f"{INTEGRATION_ENV}=1 and run toolbox/run-integration-checks.sh ({reason})",
    )
