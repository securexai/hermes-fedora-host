"""SSH controller; authentication is provisioned separately and never prompted."""
import argparse
import base64
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
FILES = {name: HERE / name for name in ("host.py", "data.py")}
FILES.update({name: HERE.parent / name for name in (
    "hermes.container", "60-hermes-runtime.conf", "70-hermes-volume-label.conf",
    "harden-config.py", "set-model.py")})
FILES["materialize.py"] = HERE.parent / "unattended/materialize.py"


def validate(config):
    required = {"target", "identity_file", "known_hosts_file", "management_cidr",
                "management_interface", "image", "provider", "model"}
    if set(config) != required:
        raise ValueError("config-fields-invalid")
    if not re.fullmatch(r"[a-z_][a-z0-9_-]*@[A-Za-z0-9.-]+", config["target"]):
        raise ValueError("target-invalid")
    if config["target"].startswith("root@"):
        raise ValueError("use-nonroot-administrator")
    network = ipaddress.ip_network(config["management_cidr"], strict=True)
    if network.version != 4 or network.prefixlen == 0:
        raise ValueError("management-network-invalid")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,15}", config["management_interface"]):
        raise ValueError("interface-invalid")
    if not re.fullmatch(r"docker.io/nousresearch/hermes-agent@sha256:[0-9a-f]{64}", config["image"]):
        raise ValueError("official-image-digest-required")
    if config["provider"] != "openai-api":
        raise ValueError("simple-profile-requires-openai-api")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", config["model"]):
        raise ValueError("model-invalid")
    for name in ("identity_file", "known_hosts_file"):
        path = Path(config[name])
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise ValueError(name + "-invalid")
        info = path.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise ValueError(name + "-unsafe-owner-mode")
        if name == "identity_file" and info.st_mode & 0o077:
            raise ValueError("identity-file-not-private")
    return config


def ssh(config):
    return ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "IdentitiesOnly=yes", "-o", "ControlMaster=no", "-o", "ControlPath=none",
            "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=3", "-o", "ClearAllForwardings=yes",
            "-o", "UserKnownHostsFile=" + config["known_hosts_file"],
            "-i", config["identity_file"], "--", config["target"]]


def request(config, action, key=None, token=None):
    # Bootstrap uses existing administrator authority, never a newly granted
    # unrestricted sudo rule. Configuration cannot become remote shell syntax.
    payload = {name: base64.b64encode(path.read_bytes()).decode() for name, path in FILES.items()}
    message = {"config": config, "action": action, "files": payload, "key": key, "token": token}
    raw = base64.b64encode(json.dumps(message).encode()).decode()
    script = ("import base64,json\nREQUEST=json.loads(base64.b64decode(" + repr(raw) + "))\n"
              "exec(compile(base64.b64decode(REQUEST['files']['host.py']), '<hermes-simple>', 'exec'))\n")
    result = subprocess.run(ssh(config) + ["sudo -n /usr/bin/python3 -I -"], input=script.encode(),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1800)
    if result.returncode:
        raise RuntimeError("remote-" + action + "-failed (exit " + str(result.returncode) + ")")
    try:
        value = json.loads(result.stdout)
    except ValueError:
        raise RuntimeError("invalid-remote-response") from None
    if not isinstance(value, dict) or not value.get("ok"):
        raise RuntimeError("remote-" + action + "-rejected")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "deploy", "status", "rollback"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--key-stdin", action="store_true", help="read one-time API key from protected stdin")
    args = parser.parse_args()
    config = validate(json.loads(args.config.read_text()))
    key = None
    if args.key_stdin:
        if args.command != "deploy" or sys.stdin.isatty():
            raise ValueError("key-input-requires-deploy-and-protected-pipe")
        key = sys.stdin.buffer.read(8193).decode().strip()
        if not key or len(key) > 8192 or any(c.isspace() for c in key) or "\x00" in key:
            raise ValueError("invalid-key-input")
    if args.command == "deploy":
        request(config, "check")
        prepared = request(config, "prepare", key=key)
        key = None
        if prepared.get("unchanged"):
            result = prepared
        else:
            # Separate transports prove access after restrictions. Recovery survives
            # this controller and either SSH transport disappearing.
            try:
                request(config, "confirm-access", token=prepared["token"])
                result = request(config, "deploy", token=prepared["token"])
            except (RuntimeError, subprocess.SubprocessError, KeyboardInterrupt):
                try:
                    request(config, "recover")
                except (RuntimeError, subprocess.SubprocessError):
                    pass
                raise
    else:
        result = request(config, args.command)
    print(json.dumps({k: result[k] for k in ("ok", "phase", "unchanged", "image", "bootstrap") if k in result}))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print("Hermes simple deployment failed: " + (str(error) if isinstance(error, RuntimeError)
              else type(error).__name__) + ". Check sanitized host state; no pass was issued.", file=sys.stderr)
        raise SystemExit(1) from None
