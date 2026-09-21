#!/usr/bin/env python3
"""Credential-free verification that an on-disk profile satisfies the contract.

Runs no container and reads no secrets. It compares an existing ``config.yaml``
(and optionally ``.env``) against ``profile-contract.yaml`` using the same
replacement semantics as ``harden-config.py``. The security-controlled
collections named in the contract's ``replace`` list must be empty or absent in
the profile — a populated ``hooks`` or ``mcp_servers`` mapping is a FAIL, not a
silently preserved integration.

Exit 0 only when every required comparison passes. Prints one
``CONTRACT_VERIFY=`` marker plus a line per problem.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any

import yaml


def load_yaml(path: pathlib.Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def compare(path: str, want: Any, got: Any, problems: list[str]) -> None:
    if isinstance(want, dict):
        # An absent key is equivalent to an empty mapping: the contract's
        # `hooks: {}` / `mcp_servers: {}` may be satisfied by either.
        if want == {} and got is None:
            return
        if not isinstance(got, dict):
            problems.append(f"{path}: expected a mapping, got {type(got).__name__}")
            return
        for key, value in want.items():
            if key not in got:
                # An empty mapping the operator never created is equivalent to
                # one that is present and empty.
                if value == {}:
                    continue
                problems.append(f"{path}.{key}: missing")
            else:
                compare(f"{path}.{key}", value, got[key], problems)
    elif isinstance(want, list):
        if list(got or []) != list(want):
            problems.append(f"{path}: expected {want!r}, got {got!r}")
    elif want != got:
        problems.append(f"{path}: expected {want!r}, got {got!r}")


def parse_env(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def get_path(document: Any, dotted: str) -> Any:
    node: Any = document
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--env", default="")
    args = parser.parse_args(argv)

    contract = load_yaml(pathlib.Path(args.contract)) or {}
    config = load_yaml(pathlib.Path(args.config)) or {}
    problems: list[str] = []

    if not isinstance(config, dict):
        print("PROBLEM config.yaml root is not a mapping")
        print("CONTRACT_VERIFY=FAIL")
        return 1

    compare("config", contract.get("config") or {}, config, problems)

    # Exact replacement semantics: every path the contract says it replaces must
    # equal the contract value exactly (no extra operator keys left behind). An
    # absent empty mapping is equivalent to an empty one.
    for dotted in (contract.get("replace") or []):
        want_node = get_path(contract.get("config") or {}, dotted)
        got_node = get_path(config, dotted)
        if want_node == {} and got_node is None:
            continue
        if want_node != got_node:
            problems.append(f"replace.{dotted}: expected exactly {want_node!r}, got {got_node!r}")

    if args.env:
        actual = parse_env(pathlib.Path(args.env))
        for key, value in (contract.get("env") or {}).items():
            if actual.get(str(key)) != str(value):
                problems.append(f"env.{key}: expected {value!r}, got {actual.get(str(key))!r}")

    for problem in problems:
        print(f"PROBLEM {problem}")
    if problems:
        print("CONTRACT_VERIFY=FAIL")
        return 1
    print("CONTRACT_VERIFY=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
