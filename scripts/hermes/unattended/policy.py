"""Enrollment policy. No defaults for identity, model, keys or authorization."""

from datetime import datetime, timedelta
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from common import decode, protected_file, require
from release import sha

CONFIG_FIELDS = {"schema", "target", "identity_file", "known_hosts", "allowed_signers", "host",
                 "state_dir", "provider", "model", "maintenance", "backup_repository",
                 "backup_password_file", "credential_socket"}


def load_config(path):
    config = decode(protected_file(path).read_bytes())
    require(isinstance(config, dict) and set(config) == CONFIG_FIELDS, "invalid-config-fields", 64)
    require(config["schema"] == "hermes-controller-v1", "invalid-config-schema", 64)
    require(isinstance(config["target"], str)
            and re.fullmatch(r"[a-z_][a-z0-9_-]*@[a-zA-Z0-9][a-zA-Z0-9.-]*", config["target"]),
            "invalid-target", 64)
    for key in ("identity_file", "known_hosts", "allowed_signers", "state_dir", "backup_repository",
                "backup_password_file", "credential_socket"):
        require(isinstance(config[key], str) and Path(config[key]).is_absolute()
                and not any(c in config[key] for c in "\n\r\x00"), "invalid-config-path", 64)
    for key in ("identity_file", "known_hosts", "allowed_signers"):
        protected_file(config[key])
    require(Path(config["identity_file"]).stat().st_mode & 0o077 == 0, "ssh-identity-not-private")
    require(config["provider"] == "openai-api", "unattended-provider-unsupported", 64)
    require(isinstance(config["model"], str) and re.fullmatch(r"[A-Za-z0-9._:/-]+", config["model"]),
            "invalid-model", 64)
    host = config["host"]
    require(isinstance(host, dict) and set(host) == {"machine_id_sha256", "ssh_fingerprint"}
            and sha(host["machine_id_sha256"]) and isinstance(host["ssh_fingerprint"], str)
            and re.fullmatch(r"SHA256:[A-Za-z0-9+/]{43}", host["ssh_fingerprint"]), "invalid-host-binding", 64)
    require(config["maintenance"] == {"timezone": "America/Bogota", "weekday": 6,
                                       "start_hour": 2, "end_hour": 4}, "unenrolled-maintenance-policy", 64)
    return config


def maintenance_open(now=None, minimum_seconds=1800):
    now = datetime.now(ZoneInfo("America/Bogota")) if now is None else now.astimezone(ZoneInfo("America/Bogota"))
    end = now.replace(hour=4, minute=0, second=0, microsecond=0)
    return now.weekday() == 6 and now.hour >= 2 and now + timedelta(seconds=minimum_seconds) <= end


def ssh_options(config):
    return ["ssh", "-F", "/dev/null", "-T", "-i", config["identity_file"],
            "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "UserKnownHostsFile=" + config["known_hosts"], "-o", "GlobalKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=15", "-o", "ConnectionAttempts=1", "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=3", "-o", "ClearAllForwardings=yes", config["target"]]
