#!/usr/bin/env python3
"""Apply the reviewed manual-profile configuration contract to a Hermes profile.

The posture lives in ``profile-contract.yaml`` so configuration, tests and
documentation share one reviewed source of truth. This helper:

* refuses to rewrite a config.yaml it cannot parse (fail closed);
* merges scalars and lists, but REPLACES the security-controlled collections
  named in the contract's ``replace`` list, so an empty ``hooks: {}`` removes
  existing hooks instead of merging into them;
* preserves genuinely unrelated operator keys;
* never invents a ``_config_version`` the deployment cannot substantiate;
* is convergent: a re-run that changes nothing writes nothing, creates no
  backup, and leaves mode/ownership/hashes alone;
* creates a pre-change backup only when it actually changes the file;
* supports ``--check`` (verify only, no writes) and ``--upgrade`` (an explicit,
  operator-requested re-apply that always writes and backs up).
"""

from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import os
import pathlib
import shutil
import stat as stat_module
import tempfile
from typing import Any

import yaml

CONTRACT_VERSION = 1
DEFAULT_CONTRACT = pathlib.Path(__file__).with_name("profile-contract.yaml")


def fail(message: str) -> None:
    raise SystemExit(f"STOP: {message}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify the profile already satisfies the contract; write nothing")
    parser.add_argument("--upgrade", action="store_true",
                        help="explicit upgrade: write and back up even when nothing changed")
    return parser.parse_args(argv)


def load_contract(contract_path: pathlib.Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, str], list[str]]:
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
    if contract.get("version") != CONTRACT_VERSION:
        fail(f"unsupported contract version in {contract_path}: {contract.get('version')!r}")
    desired = contract.get("config") or {}
    desired_env = {str(k): str(v) for k, v in (contract.get("env") or {}).items()}
    replace_paths = [str(path) for path in (contract.get("replace") or [])]
    return contract, desired, desired_env, replace_paths


def merge(target: dict, patch: dict) -> dict:
    """Recursively merge *patch* into *target*; lists and scalars replace."""
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            merge(target[key], value)
        else:
            target[key] = copy.deepcopy(value)
    return target


def drop_path(target: dict, dotted: str) -> None:
    """Delete *dotted* (``a.b.c``) from *target* when the parents are mappings."""
    parts = [part for part in dotted.split(".") if part]
    if not parts:
        return
    node: Any = target
    for part in parts[:-1]:
        node = node.get(part) if isinstance(node, dict) else None
        if not isinstance(node, dict):
            return
    if isinstance(node, dict):
        node.pop(parts[-1], None)


def effective(document: Any) -> Any:
    """The document without the volatile convergence timestamp."""
    clone = copy.deepcopy(document)
    if isinstance(clone, dict):
        profile = clone.get("manual_profile")
        if isinstance(profile, dict):
            profile.pop("applied_utc", None)
    return clone


def atomic_write(path: pathlib.Path, text: str) -> None:
    """Replace *path* atomically, preserving its mode and (best-effort) owner."""
    mode: int | None = None
    uid = gid = -1
    if path.exists():
        current = path.stat()
        mode = stat_module.S_IMODE(current.st_mode)
        uid, gid = current.st_uid, current.st_gid
    handle, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp_name, mode if mode is not None else 0o600)
        if uid != -1:
            try:
                os.chown(tmp_name, uid, gid)
            except PermissionError:
                # Non-root operator: the file stays owned by the invoker, which
                # is the same result as editing it in place would give.
                pass
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def load_existing(config_path: pathlib.Path) -> dict:
    """Parse an existing configuration, or return {} when absent/empty."""
    if not (config_path.exists() and config_path.read_text(encoding="utf-8").strip()):
        return {}
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        fail(f"config.yaml is not valid YAML; refusing to rewrite it ({exc})")
    if not isinstance(config, dict):
        fail("config.yaml root is not a mapping")
    return config


def apply_contract(existing: dict, desired: dict, replace_paths: list[str]) -> dict:
    config = copy.deepcopy(existing)
    for dotted in replace_paths:
        drop_path(config, dotted)
    merge(config, desired)
    return config


def render_env(env_path: pathlib.Path, desired_env: dict[str, str]) -> tuple[str, str]:
    """Return (original, updated) text for the .env allowlist without writing."""
    if not desired_env:
        return "", ""
    if env_path.exists():
        original = env_path.read_text(encoding="utf-8")
        lines = original.splitlines()
    else:
        original = ""
        lines = []
    output: list[str] = []
    seen: set[str] = set()
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else ""
        if key in desired_env:
            output.append(f"{key}={desired_env[key]}")
            seen.add(key)
        else:
            output.append(line)
    for key, value in desired_env.items():
        if key not in seen:
            output.append(f"{key}={value}")
    return original, "\n".join(output) + "\n"


def env_needs_update(env_path: pathlib.Path, desired_env: dict[str, str]) -> bool:
    """True when the .env allowlist does not already match the contract."""
    if not desired_env:
        return False
    original, updated = render_env(env_path, desired_env)
    return updated != original


def update_env(env_path: pathlib.Path, desired_env: dict[str, str]) -> bool:
    """Merge the allowlist into the profile .env; return True when it changed."""
    if not desired_env:
        return False
    original, updated = render_env(env_path, desired_env)
    if updated == original:
        return False
    atomic_write(env_path, updated)
    return True


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    data_dir = pathlib.Path(os.environ.get("HERMES_DATA_DIR", "/opt/data"))
    contract_path = pathlib.Path(os.environ.get("HERMES_PROFILE_CONTRACT", str(DEFAULT_CONTRACT)))
    config_path = data_dir / "config.yaml"
    env_path = data_dir / ".env"
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    contract, desired, desired_env, replace_paths = load_contract(contract_path)
    existing = load_existing(config_path)
    config = apply_contract(existing, desired, replace_paths)

    # Record the reviewed posture so the profile is self-describing without
    # adding a schema version. Purely informational for the operator and tests.
    profile = config.get("manual_profile")
    if not isinstance(profile, dict):
        profile = {}
        config["manual_profile"] = profile
    previous_profile = existing.get("manual_profile") if isinstance(existing.get("manual_profile"), dict) else {}
    profile["contract_version"] = CONTRACT_VERSION
    profile["contract_sha256"] = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    # Convergence: keep the previous timestamp unless something actually changed,
    # so a matching re-run is byte-for-byte stable instead of churning metadata.
    profile["applied_utc"] = previous_profile.get("applied_utc", stamp)

    config_changed = effective(existing) != effective(config) or not config_path.exists()
    env_changed = env_needs_update(env_path, desired_env)

    if args.check:
        # Verify BOTH the configuration and the environment allowlist without
        # writing either. A matching config with a drifted .env is not converged.
        if config_changed or env_changed:
            print("PROFILE_CONTRACT_CHECK=FAIL the on-disk configuration or environment does not match the contract")
            return 1
        print("PROFILE_CONTRACT_CHECK=PASS the on-disk configuration and environment match the contract")
        return 0

    if args.upgrade:
        config_changed = True
    if not config_changed:
        wrote_env = update_env(env_path, desired_env)
        print(f"PROFILE_CONTRACT_UNCHANGED version={CONTRACT_VERSION} config={config_path} env_changed={int(wrote_env)}")
        print("Manual-profile configuration already converged; no write, no backup.")
        return 0

    # The change is real: timestamp it and back up the pre-change file once. The
    # backup name is made unique so two changes in the same second (for example
    # an apply followed immediately by --upgrade) cannot overwrite a backup.
    profile["applied_utc"] = stamp
    if config_path.exists():
        backup = data_dir / f"config.yaml.pre-contract-{stamp}"
        counter = 1
        while backup.exists():
            backup = data_dir / f"config.yaml.pre-contract-{stamp}-{counter}"
            counter += 1
        shutil.copy2(config_path, backup)
    atomic_write(config_path, yaml.safe_dump(config, sort_keys=False))
    update_env(env_path, desired_env)

    print(f"PROFILE_CONTRACT_APPLIED version={CONTRACT_VERSION} config={config_path}")
    print("Manual-profile configuration applied; SSH backend preserved; no secret values displayed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
