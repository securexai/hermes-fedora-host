#!/usr/bin/python3
"""Connect an OpenSSH ProxyCommand's stdio to the worker's shared Unix socket.

The gateway image is Debian and ships neither socat nor nc, so this small
bridge is bind-mounted in and used as the ProxyCommand for ssh, scp and sftp.

Usage: unix-bridge.py /run/hermes-transport/worker.sock
"""

import errno
import os
import select
import socket
import sys


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "/run/hermes-transport/worker.sock"
    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        conn.connect(path)
    except OSError as exc:
        sys.stderr.write("unix-bridge: cannot connect to %s: %s\n" % (path, exc))
        return 1

    stdin_fd = sys.stdin.fileno()
    stdout_fd = sys.stdout.fileno()
    sock_fd = conn.fileno()

    want_read = {stdin_fd, sock_fd}
    while want_read:
        try:
            readable, _, _ = select.select(list(want_read), [], [])
        except OSError as exc:
            if exc.errno == errno.EINTR:
                continue
            raise
        if stdin_fd in readable:
            data = os.read(stdin_fd, 65536)
            if data:
                conn.sendall(data)
            else:
                want_read.discard(stdin_fd)
                try:
                    conn.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
        if sock_fd in readable:
            data = conn.recv(65536)
            if data:
                os.write(stdout_fd, data)
            else:
                break

    try:
        conn.close()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
