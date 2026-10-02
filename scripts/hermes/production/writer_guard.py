"""Linux subreaper retaining inherited transaction locks until all writers exit.

This private helper is launched in its own session. Descendants may close every
inherited fd or double-fork: the guard still owns the lock and adopts/reaps them.
Never kill this guard to cancel a command; terminate the writers or let them exit.
"""

import ctypes
import os
import signal
import subprocess
import sys
import time


def child_signals():
    for sig in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal.SIG_DFL)


def main():
    # Arguments are private plumbing followed by the original argv, never secrets.
    timeout = float(sys.argv[1])
    for fd in sys.argv[2].split(","):
        os.fstat(int(fd))
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, ctypes.c_ulong(1), 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        return 125  # Refuse before spawning any writer.
    for sig in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal.SIG_IGN)
    # This standalone helper is single-threaded; reset ignored signals in the
    # child without changing the guard's cancellation behavior.
    child = subprocess.Popen(sys.argv[3:], start_new_session=True, preexec_fn=child_signals)
    deadline = time.monotonic() + timeout if timeout else None
    result, descendant_failed = None, False
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break  # No child or adopted descendant can still write.
        if pid:
            code = os.waitstatus_to_exitcode(status)
            if pid == child.pid:
                child.returncode = code
                result = code if code >= 0 else 128 - code
            else:
                descendant_failed |= code != 0
            continue
        if deadline is not None and time.monotonic() >= deadline:
            # An unreaped leader reserves its PID. Once reaped, its old process
            # group ID could be reused; never signal that stale numeric identity.
            if result is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            deadline = None
            descendant_failed = True
            # A descendant may have created another session. Keep the lock until
            # it too exits; timeout never permits recovery to race a live writer.
        time.sleep(0.02)
    return (result or int(descendant_failed)) if result is not None else 125


if __name__ == "__main__":
    raise SystemExit(main())
