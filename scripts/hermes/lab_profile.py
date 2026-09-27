"""Strict, non-secret lab profiles shared by host, guest and tests."""

from __future__ import annotations

import hashlib
import json
import pathlib
import re


class ProfileError(ValueError):
    pass


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_hash(path: pathlib.Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def mapping(value: object, keys: set[str], name: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ProfileError(f"{name}: missing or unknown fields (values suppressed)")
    return value


def integer(value: object, low: int, high: int, name: str) -> None:
    if type(value) is not int or not low <= value <= high:
        raise ProfileError(f"{name}: integer outside supported range")


def validate(value: object) -> dict:
    p = mapping(
        value,
        {
            "version",
            "preparation_revision",
            "fedora",
            "gateway_image",
            "model",
            "vm",
            "gateway",
            "worker",
        },
        "profile",
    )
    if type(p["version"]) is not int or p["version"] != 1 or p["fedora"] != 44:
        raise ProfileError("only profile version 1 and Fedora 44 are supported")
    if not isinstance(p["gateway_image"], str) or not re.fullmatch(
        r"docker\.io/nousresearch/hermes-agent@sha256:[a-f0-9]{64}", p["gateway_image"]
    ):
        raise ProfileError("gateway_image must be an immutable Hermes digest")
    if not isinstance(p["model"], str) or not re.fullmatch(
        r"deepseek-[a-z0-9.-]{1,64}", p["model"]
    ):
        raise ProfileError("model must be a DeepSeek model identifier")
    integer(p["preparation_revision"], 1, 99999, "preparation_revision")
    vm = mapping(p["vm"], {"memory_mb", "vcpus", "disk_gb"}, "vm")
    integer(vm["memory_mb"], 2048, 32768, "vm.memory_mb")
    integer(vm["vcpus"], 1, 16, "vm.vcpus")
    integer(vm["disk_gb"], 20, 200, "vm.disk_gb")
    for name in ("gateway", "worker"):
        resource = mapping(p[name], {"memory_mb", "pids_limit", "restart_seconds"}, name)
        integer(resource["memory_mb"], 128, vm["memory_mb"], f"{name}.memory_mb")
        integer(resource["pids_limit"], 32, 4096, f"{name}.pids_limit")
        integer(resource["restart_seconds"], 0, 60, f"{name}.restart_seconds")
    return p


def load(path: pathlib.Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16384:
        raise ProfileError("profile must be a small regular file")
    try:
        return validate(json.loads(path.read_text()))
    except (UnicodeError, json.JSONDecodeError):
        raise ProfileError("profile is not valid JSON (contents suppressed)") from None


def render_unit(content: str, name: str, profile: dict, worker_id: str | None = None) -> str:
    validate(profile)
    if worker_id is not None and not re.fullmatch(r"sha256:[a-f0-9]{64}", worker_id):
        raise ProfileError("worker image identity is invalid")
    resource = profile[name]
    replacements = {
        "Image=": profile["gateway_image"]
        if name == "gateway"
        else worker_id or "localhost/hermes-worker:1",
        "Memory=": f"{resource['memory_mb']}m",
        "PidsLimit=": str(resource["pids_limit"]),
    }
    for key, value in replacements.items():
        if sum(line.startswith(key) for line in content.splitlines()) != 1:
            raise ProfileError("Quadlet template field is missing or ambiguous")
        content = re.sub(rf"^{key}.*$", key + value, content, flags=re.M)
    return content.replace(
        "[Service]\n", f"[Service]\nRestartSec={resource['restart_seconds']}\n", 1
    )
