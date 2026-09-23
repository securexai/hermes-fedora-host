"""Fixed-project credential broker. No arbitrary URLs, project IDs, or account IDs on the wire."""

import argparse
import http.client
import os
from pathlib import Path
import re
import socket
import socketserver
import struct
import time

from common import Failure, atomic, canonical, decode, lock, protected_file, report, require, run


class OpenAI:
    def __init__(self, admin):
        self.admin = admin

    def call(self, method, path, body=None, token=None):
        connection = http.client.HTTPSConnection("api.openai.com", timeout=30)
        try:
            connection.request(method, "/v1/" + path,
                               body=canonical(body) if body is not None else None,
                               headers={"Authorization": "Bearer " + (token or self.admin),
                                        "Content-Type": "application/json"})
            response = connection.getresponse()
            raw = response.read(1024 * 1024 + 1)
            require(len(raw) <= 1024 * 1024, "provider-response-too-large", 69)
            # Do not propagate server bodies on errors, including redirects.
            if response.status == 401:
                return {"unauthorized": True}
            require(200 <= response.status < 300, "provider-administration-failed", 69)
            return decode(raw)
        finally:
            connection.close()


class Broker:
    def __init__(self, policy, api, state):
        require(set(policy) == {"test_project", "production_project", "test_uid", "production_uid"},
                "invalid-broker-policy")
        disabled = policy["production_project"] is None and policy["production_uid"] is None
        for key in (("test_project",) if disabled else ("test_project", "production_project")):
            require(isinstance(policy[key], str) and re.fullmatch(r"proj_[A-Za-z0-9_-]+", policy[key]),
                    "invalid-broker-project")
        require(policy["test_project"] != policy["production_project"], "projects-must-be-separated")
        require(type(policy["test_uid"]) is int and policy["test_uid"] > 0
                and (disabled or type(policy["production_uid"]) is int
                     and policy["production_uid"] > 0 and policy["test_uid"] != policy["production_uid"]),
                "broker-roles-must-be-separated")
        self.policy, self.api, self.state = policy, api, Path(state)

    def secret(self, lease, value=None):
        path = self.state / (lease + ".cred")
        if value is not None:
            encrypted = run(["systemd-creds", "encrypt", "--user", "--name=api-key", "-", "-"],
                            data=value.encode())
            atomic(path, encrypted)
            return value
        return run(["systemd-creds", "decrypt", "--user", "--name=api-key", str(path), "-"]).decode().strip()

    def handle(self, uid, message):
        require(isinstance(message, dict) and set(message) == {"operation", "role", "lease"}, "invalid-broker-request", 64)
        role, operation, lease = message["role"], message["operation"], message["lease"]
        require(role in ("test", "production"), "invalid-broker-role", 64)
        require(self.policy[role + "_project"] is not None and self.policy[role + "_uid"] is not None,
                "broker-role-disabled", 77)
        require(uid == self.policy[role + "_uid"], "broker-peer-denied", 77)
        require(operation in ("check", "issue", "read", "revoke"), "invalid-broker-operation", 64)
        require(isinstance(lease, str) and re.fullmatch(r"[a-f0-9]{32}", lease), "invalid-lease", 64)
        path = self.state / (lease + ".json")
        project = self.policy[role + "_project"]
        prefix = "organization/projects/" + project + "/service_accounts"
        if operation == "check":
            result = self.api.call("GET", prefix)
            require(isinstance(result.get("data"), list), "provider-administration-unavailable", 69)
            return {"ok": True, "role": role}
        with lock(self.state / "broker.lock"):
            record = decode(path.read_bytes()) if path.exists() else None
            if record:
                require(record["role"] == role, "lease-role-mismatch", 77)
            if operation == "issue":
                if record:
                    require(record["state"] == "ready", "lease-needs-reconciliation", 75)
                    return {"ok": True, "lease": lease, "key": self.secret(lease)}
                # Write before network mutation. An uncertain response never triggers blind reissuance.
                record = {"role": role, "state": "issuing", "name": "hermes-" + lease,
                          "created_at": int(time.time())}
                atomic(path, canonical(record))
                result = self.api.call("POST", prefix, {"name": record["name"]})
                require(isinstance(result.get("id"), str)
                        and re.fullmatch(r"[A-Za-z0-9_-]+", result["id"]), "invalid-service-account-response")
                record["account_id"] = result["id"]
                # Persist the account ID before touching credentials; cleanup can identify it after failure.
                atomic(path, canonical(record))
                value = result.get("api_key", {}).get("value")
                require(isinstance(value, str) and value and not any(c in value for c in "\n\r\x00"),
                        "missing-service-account-key")
                self.secret(lease, value)
                record["state"] = "ready"
                atomic(path, canonical(record))
                return {"ok": True, "lease": lease, "key": value}
            require(record is not None, "unknown-lease", 66)
            if operation == "read":
                require(record["state"] == "ready", "lease-not-ready", 75)
                return {"ok": True, "lease": lease, "key": self.secret(lease)}
            if record["state"] == "revoked":
                return {"ok": True, "lease": lease, "revoked": True}
            require("account_id" in record, "lease-needs-reconciliation", 75)
            key = self.secret(lease)
            if record["state"] != "deleted":
                result = self.api.call("DELETE", prefix + "/" + record["account_id"])
                require(result.get("deleted") is True, "service-account-deletion-unconfirmed", 69)
                record["state"] = "deleted"
                atomic(path, canonical(record))
            # Only 401 proves key rejection. Network failures, 403 and model errors are not revocation.
            probe = self.api.call("GET", "models", token=key)
            require(probe.get("unauthorized") is True, "credential-revocation-unverified", 69)
            record["state"] = "revoked"
            atomic(path, canonical(record))
            (self.state / (lease + ".cred")).unlink(missing_ok=True)
            return {"ok": True, "lease": lease, "revoked": True}


def client(path, operation, role, lease):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(120)
        connection.connect(path)
        connection.sendall(canonical({"operation": operation, "role": role, "lease": lease}))
        with connection.makefile("rb") as stream:
            raw = stream.readline(65537)
        require(len(raw) <= 65536, "broker-response-too-large")
        result = decode(raw)
        require(result.get("ok") is True, "credential-broker-rejected", 69)
        return result


def activated_socket(expected_path):
    require(os.environ.get("LISTEN_PID") == str(os.getpid()) and os.environ.get("LISTEN_FDS") == "1",
            "socket-activation-required")
    listener = socket.socket(fileno=3)
    require(listener.family == socket.AF_UNIX and listener.getsockname() == expected_path
            and listener.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) == socket.SOCK_STREAM
            and listener.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN) == 1,
            "broker-socket-mismatch")
    return listener


def serve():
    parser = argparse.ArgumentParser(description="Fixed-project credential broker")
    parser.add_argument("--config", default="/etc/hermes-unattended/broker.json")
    parser.add_argument("--state-dir", default="/var/lib/hermes-credentials")
    parser.add_argument("--socket", default="/run/hermes-credentials/broker.sock")
    args = parser.parse_args()
    require(all(Path(value).is_absolute() for value in (args.config, args.state_dir, args.socket)),
            "absolute-broker-paths-required")
    policy = decode(protected_file(args.config, 0).read_bytes())
    state = Path(args.state_dir)
    require(state.is_dir() and not state.is_symlink() and state.stat().st_uid == os.getuid()
            and not state.stat().st_mode & 0o077, "private-broker-state-required")
    credential = Path(os.environ["CREDENTIALS_DIRECTORY"]) / "openai-admin"
    broker = Broker(policy, OpenAI(credential.read_text().strip()), state)

    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.connection.settimeout(120)
            try:
                _, uid, _ = struct.unpack("3i", self.connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                raw = self.rfile.readline(65537)
                require(len(raw) <= 65536 and raw.endswith(b"\n"), "invalid-broker-frame", 64)
                response = broker.handle(uid, decode(raw))
            except (Failure, OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
                response = {"ok": False, "error": "credential-operation-failed"}
            self.wfile.write(canonical(response))

    # systemd owns and permission-controls the listening socket; no unlink/bind race.
    with socketserver.UnixStreamServer(args.socket, Handler, bind_and_activate=False) as server:
        server.socket.close()
        server.socket = activated_socket(args.socket)
        server.serve_forever()


if __name__ == "__main__":
    report(serve)
