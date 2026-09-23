#!/usr/bin/env python3
"""Inspect an offline linked policy with SETools; never load kernel policy."""
import argparse
import hashlib
import json
from pathlib import Path

import setools

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("base", type=Path)
parser.add_argument("merged", type=Path)
parser.add_argument("--previous", type=Path, help="Prior linked candidate for exact TE-rule delta inspection")
args = parser.parse_args()
base = setools.SELinuxPolicy(str(args.base))
merged = setools.SELinuxPolicy(str(args.merged))
domain = "hermes_tpm2_setup_t"
checks = {}


def rules(policy, **kwargs):
    return list(setools.TERuleQuery(policy, **kwargs).results())


def require(name, condition):
    checks[name] = bool(condition)


require("candidate_enforcing", not merged.lookup_type(domain).ispermissive)
require("no_new_permissive_types",
        {str(t) for t in merged.types() if t.ispermissive}
        == {str(t) for t in base.types() if t.ispermissive})
transitions = rules(merged, ruletype=["type_transition"], source="init_t",
                    target="hermes_tpm2_setup_exec_t", tclass=["process"])
require("init_transition", any(str(r.default) == domain for r in transitions))
for target, cls, perms in [
    ("dosfs_t", "file", {"create", "write", "rename"}),
    ("syslogd_var_run_t", "file", {"open", "write", "lock"}),
    ("tpm_device_t", "chr_file", {"open", "read", "write"}),
    ("init_var_lib_t", "file", {"create", "write", "rename"}),
    ("init_var_run_t", "file", {"read", "write"}),
    ("hermes_tpm2_setup_exec_t", "file", {"entrypoint"}),
    ("nsfs_t", "file", {"getattr"}),
    ("cert_t", "dir", {"search"}),
    ("fixed_disk_device_t", "blk_file", {"getattr", "open", "read"}),
]:
    grants = rules(merged, ruletype=["allow"], source=domain, target=target, tclass=[cls])
    # Accessing conditional on unconditional SETools rules can raise; use string form instead.
    granted = set().union(*(set(r.perms) for r in grants if "; [" not in str(r)))
    require("access_" + target, perms <= granted)
for cls in ["capability", "capability2"]:
    require("no_" + cls, not rules(merged, ruletype=["allow"], source=domain, tclass=[cls]))
for cls in ["tcp_socket", "udp_socket", "rawip_socket"]:
    require("no_create_" + cls,
            not rules(merged, ruletype=["allow"], source=domain, tclass=[cls], perms=["create"]))
for target, cls, perms in [
    ("shadow_t", "file", ["read", "write"]),
    ("security_t", "security", ["load_policy", "setenforce"]),
    ("efivarfs_t", "file", ["write", "create", "unlink"]),
]:
    require("no_mutation_" + target,
            not rules(merged, ruletype=["allow"], source=domain, target=target,
                      tclass=[cls], perms=perms))
for target, cls, expected in [
    ("nsfs_t", "file", {"getattr"}),
    ("cert_t", "dir", {"search"}),
    ("fixed_disk_device_t", "blk_file", {"getattr", "open", "read"}),
]:
    grants = rules(merged, ruletype=["allow"], source=domain, target=target, tclass=[cls])
    granted = set().union(*(set(r.perms) for r in grants))
    require("bounded_" + target, granted <= expected)
require("no_cert_file_read", not rules(merged, ruletype=["allow"], source=domain,
        target="cert_t", tclass=["file"], perms=["read", "write"]))
for target in ["dosfs_t", "syslogd_var_run_t", "nsfs_t", "cert_t", "fixed_disk_device_t"]:
    query = dict(ruletype=["allow"], source="init_t", target=target)
    require("unchanged_init_" + target,
            {str(r) for r in rules(base, **query)} == {str(r) for r in rules(merged, **query)})
delta = None
if args.previous:
    previous = setools.SELinuxPolicy(str(args.previous))
    old_rules = {str(r) for r in previous.terules()}
    new_rules = {str(r) for r in merged.terules()}
    expected = {
        "allow hermes_tpm2_setup_t nsfs_t:file getattr;",
        "allow hermes_tpm2_setup_t cert_t:dir search;",
        "allow hermes_tpm2_setup_t fixed_disk_device_t:blk_file { getattr open read };",
    }
    delta = {"added": sorted(new_rules - old_rules), "removed": sorted(old_rules - new_rules)}
    require("exact_previous_te_delta", set(delta["added"]) == expected and not delta["removed"])
    require("unchanged_type_attributes", {str(t): sorted(str(a) for a in t.attributes()) for t in previous.types()}
            == {str(t): sorted(str(a) for a in t.attributes()) for t in merged.types()})
result = {"base_sha256": hashlib.sha256(args.base.read_bytes()).hexdigest(),
          "merged_sha256": hashlib.sha256(args.merged.read_bytes()).hexdigest(),
          "checks": checks, "passed": all(checks.values()), "previous_te_delta": delta,
          "scope": "offline policy inspection only; not hardware or persistence acceptance"}
print(json.dumps(result, indent=2))
raise SystemExit(0 if result["passed"] else 1)
