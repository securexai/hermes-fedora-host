#!/usr/bin/python3
"""Bounded transport retry for the pinned disposable-lab scanner."""
import os
import subprocess
import sys
import tempfile
import time

BINARY = '/nix/store/y2bs43cy44ndnwx9aqd0z9hl9cchhpnp-trivy-0.74.0/bin/trivy'
TRANSPORT = (b'network is unreachable', b'connection reset', b'connection refused',
             b'i/o timeout', b'tls handshake timeout', b'no such host',
             b'temporary failure in name resolution', b'context deadline exceeded')


def scan(arguments, runner=subprocess.run, monotonic=time.monotonic, pause=time.sleep,
         output=None, errors=None):
    output = sys.stdout.buffer if output is None else output
    errors = sys.stderr.buffer if errors is None else errors
    environment = dict(os.environ, GODEBUG='netdns=go')
    deadline = monotonic() + 900
    last = b''
    for attempt in range(6):
        remaining = deadline - monotonic()
        if remaining <= 0:
            break
        with tempfile.TemporaryFile() as captured:
            try:
                result = runner([BINARY, *arguments], stdout=captured, stderr=subprocess.PIPE,
                                env=environment, timeout=remaining)
            except subprocess.TimeoutExpired:
                last = b'lab-scanner-total-timeout\n'
                break
            last = result.stderr
            if result.returncode == 0:
                captured.seek(0)
                while chunk := captured.read(1024 * 1024):
                    output.write(chunk)
                if attempt:
                    errors.write(('lab-scanner-transport-retries=' + str(attempt) + '\n').encode())
                return 0
            message = last.lower()
            # Retry only network transport failure; report policy/configuration errors immediately.
            retryable = (b'dial tcp' in message or b'get "https://' in message) and any(
                marker in message for marker in TRANSPORT)
            if not retryable or attempt == 5:
                errors.write(last)
                return result.returncode if result.returncode > 0 else 1
        pause(min(5, max(0, deadline - monotonic())))
    errors.write(last)
    return 1


if __name__ == '__main__':
    raise SystemExit(scan(sys.argv[1:]))
