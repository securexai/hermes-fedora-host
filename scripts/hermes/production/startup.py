"""Keep interrupted transactions from auto-starting after process death or reboot."""

import os
from contextlib import contextmanager
from pathlib import Path

from .primitives import atomic, canonical, read_json, require

LEASE = Path("/run/hermes-production-lease.json")
READY = Path("/run/hermes-production-ready.json")
JOURNAL = Path("/var/lib/hermes-production/journal.json")


def boot_id():
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip()


def process_identity(pid):
    require(type(pid) is int and pid > 0, "invalid-startup-lease")
    process = Path(f"/proc/{pid}")
    require(process.stat().st_uid == 0, "startup-lease-not-root")
    # Field 22 is the process start time; split after comm, which can contain spaces.
    return (process / "stat").read_text().rsplit(") ", 1)[1].split()[19]


def active_lease():
    value = read_json(LEASE, owner=0)
    require(
        value["boot"] == boot_id() and value["start"] == process_identity(value["pid"]),
        "dead-startup-lease",
    )
    return value


def stable():
    return not JOURNAL.exists() or read_json(JOURNAL, owner=0)["stage"] in (
        "committed",
        "recovered",
        "aborted",
    )


def guard():
    if LEASE.exists():
        value = active_lease()
        require(
            os.geteuid() == 0 or value["allow_application"] is True,
            "application-start-blocked-by-transaction",
        )
    elif os.geteuid() == 0:
        require(stable(), "unfinished-transaction-blocks-boot")
        atomic(READY, canonical({"boot": boot_id()}), 0o644)
    else:
        require(
            read_json(READY, owner=0) == {"boot": boot_id()}, "application-start-not-authorized"
        )


def allow_application():
    value = active_lease()
    require(value["pid"] == os.getpid(), "startup-lease-not-owned")
    value["allow_application"] = True
    atomic(LEASE, canonical(value), 0o644)


@contextmanager
def operation():
    # Caller holds the persistent operation lock. A stale lease is recoverable
    # only through this root-owned dispatcher, never through the runtime account.
    READY.unlink(missing_ok=True)
    atomic(
        LEASE,
        canonical(
            {
                "pid": os.getpid(),
                "start": process_identity(os.getpid()),
                "boot": boot_id(),
                "allow_application": False,
            }
        ),
        0o644,
    )
    try:
        yield
    finally:
        if stable():
            atomic(READY, canonical({"boot": boot_id()}), 0o644)
        else:
            READY.unlink(missing_ok=True)
        LEASE.unlink(missing_ok=True)
