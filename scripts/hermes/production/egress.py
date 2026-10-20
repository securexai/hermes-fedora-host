"""Host egress guard: the runtime account reaches the public internet, not local networks.

Rootless pasta opens the containers' connections from processes owned by the `hermes`
account, so one nftables output rule set keyed on that uid covers the worker and the
gateway: private, carrier-grade NAT, link-local (including cloud metadata), multicast and
reserved destinations are dropped, and so is host loopback except DNS (pasta forwards
container DNS to the host's stub resolver). The table is owned here and never touches
firewalld's own table. A oneshot unit loads it at boot before the user manager starts.

The rules, unit and drop-in are host-wide, while every receiver that may still run
(for recovery or rollback) checks them. So bootstrap records their hashes, and a
receiver checks the files against that record and the loaded table only for the
coverage it requires: a later release may block more without breaking older ones.
"""

from __future__ import annotations

import ipaddress
import shutil
from pathlib import Path

from .primitives import atomic, canonical, decode, public_directory, read_json, require, run, sha

TABLE = "hermes_egress"
RULES = Path("/etc/hermes-production/egress.nft")
# Hashes of the installed guard files, written by bootstrap and read by every receiver.
RECORD = Path("/etc/hermes-production/egress.json")
UNIT = Path("/etc/systemd/system/hermes-egress.service")
SYSTEMD = Path("/etc/systemd/system")
DROPIN = "40-hermes-egress.conf"
BLOCKED_V4 = (
    "0.0.0.0/8",
    "10.0.0.0/8",
    "100.64.0.0/10",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.0.0.0/24",
    "192.168.0.0/16",
    "198.18.0.0/15",
    # Multicast 224/4 and reserved 240/4 (incl. broadcast); nft merges them into one prefix.
    "224.0.0.0/3",
)
BLOCKED_V6 = ("fc00::/7", "fe80::/10", "ff00::/8")
UNIT_BYTES = b"""[Unit]
Description=Hermes egress guard (runtime account kept off local networks)
DefaultDependencies=no
After=local-fs.target
Before=network-pre.target
Wants=network-pre.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/sbin/nft -f /etc/hermes-production/egress.nft
ExecStop=/usr/sbin/nft delete table inet hermes_egress

[Install]
WantedBy=multi-user.target
"""
DROPIN_BYTES = b"[Unit]\nRequires=hermes-egress.service\nAfter=hermes-egress.service\n"


def rules(uid):
    """Atomic, idempotent nft program: declare, delete, then define the owned table."""
    require(type(uid) is int and uid >= 1000, "invalid-runtime-uid")
    v4, v6 = ", ".join(BLOCKED_V4), ", ".join(BLOCKED_V6)
    return (
        f"table inet {TABLE}\n"
        f"delete table inet {TABLE}\n"
        f"table inet {TABLE} {{\n"
        "\tchain output {\n"
        "\t\ttype filter hook output priority filter; policy accept;\n"
        f"\t\tmeta skuid {uid} ip daddr {{ {v4} }} counter drop\n"
        f"\t\tmeta skuid {uid} ip6 daddr {{ {v6} }} counter drop\n"
        f"\t\tmeta skuid {uid} ip daddr 127.0.0.0/8 th dport != 53 counter drop\n"
        f"\t\tmeta skuid {uid} ip6 daddr ::1 th dport != 53 counter drop\n"
        "\t}\n"
        "}\n"
    ).encode()


def install(uid):
    """Write the rules, unit, user-manager dependency and their hash record (bootstrap)."""
    require(shutil.which("nft") is not None, "nftables-required")
    atomic(RULES, rules(uid), 0o644)
    atomic(UNIT, UNIT_BYTES, 0o644)
    dropin = SYSTEMD / f"user@{uid}.service.d"
    public_directory(dropin)
    atomic(dropin / DROPIN, DROPIN_BYTES, 0o644)
    record = {"dropin": sha(dropin / DROPIN), "rules": sha(RULES), "unit": sha(UNIT)}
    atomic(RECORD, canonical(record), 0o644)
    return [RULES, UNIT, dropin / DROPIN, RECORD]


def activate():
    """After daemon-reload: enable and start for boot, then reload the table in place.

    Never restart the unit: the runtime user manager Requires= it, so a restart would
    also restart the running application. The rules program replaces the owned table
    atomically, so loading it again is idempotent.
    """
    run(["systemctl", "enable", "--now", UNIT.name])
    run(["nft", "-f", str(RULES)])


def _networks(right):
    items = right.get("set") if isinstance(right, dict) and "set" in right else [right]
    found = set()
    for item in items:
        if isinstance(item, dict) and "prefix" in item:
            found.add(ipaddress.ip_network(f"{item['prefix']['addr']}/{item['prefix']['len']}"))
        else:
            require(isinstance(item, str), "egress-rule-destination")
            found.add(ipaddress.ip_network(item))
    return frozenset(found)


def loaded(uid):
    """Normalize the live table; refuse anything but exact uid drop rules.

    Each rule may hold only `meta skuid == uid`, `ip/ip6 daddr == {...}`, optionally
    `th dport != 53`, a counter and a final drop: nothing that narrows or negates it.
    """
    data = decode(run(["nft", "-j", "list", "table", "inet", TABLE]).stdout)["nftables"]
    chains = [row["chain"] for row in data if "chain" in row]
    require(
        len(chains) == 1
        and chains[0].get("name") == "output"
        and chains[0].get("hook") == "output"
        and chains[0].get("type") == "filter"
        and chains[0].get("policy") == "accept",
        "egress-chain-mismatch",
    )
    observed = []
    for row in (r["rule"] for r in data if "rule" in r):
        expr = row["expr"]
        require(expr and expr[-1] == {"drop": None}, "egress-rule-not-drop")
        meta, dest, port = [], [], []
        for item in expr[:-1]:
            if "counter" in item:
                continue
            match = item.get("match")
            require(isinstance(match, dict), "egress-rule-unexpected-expression")
            left = match.get("left", {})
            if "meta" in left:
                meta.append(match)
            elif left.get("payload", {}).get("field") == "daddr":
                dest.append(match)
            elif left.get("payload", {}).get("field") == "dport":
                port.append(match)
            else:
                require(False, "egress-rule-unexpected-expression")
        require(
            len(meta) == 1
            and meta[0]["op"] == "=="
            and meta[0]["left"]["meta"]["key"] == "skuid"
            and meta[0]["right"] == uid,
            "egress-rule-uid-mismatch",
        )
        require(len(dest) == 1 and dest[0]["op"] == "==", "egress-rule-destination")
        family = dest[0]["left"]["payload"]["protocol"]
        require(family in ("ip", "ip6"), "egress-rule-destination")
        except_dns = len(port) == 1 and port[0]["op"] == "!=" and port[0]["right"] == 53
        require(not port or except_dns, "egress-rule-port")
        observed.append((family, _networks(dest[0]["right"]), except_dns))
    return observed


def required():
    """(family, network, except_dns) this receiver needs blocked for the runtime uid."""
    return (
        [("ip", ipaddress.ip_network(n), False) for n in BLOCKED_V4]
        + [("ip6", ipaddress.ip_network(n), False) for n in BLOCKED_V6]
        + [("ip", ipaddress.ip_network("127.0.0.0/8"), True)]
        + [("ip6", ipaddress.ip_network("::1"), True)]
    )


def covered(observed):
    """Every required network lies inside a loaded drop rule of the same kind."""
    return all(
        any(
            family == fam and except_dns == dns and any(net.subnet_of(n) for n in nets)
            for fam, nets, dns in observed
        )
        for family, net, except_dns in required()
    )


def check(uid):
    """Files match bootstrap's record, the unit is enabled and active, coverage holds."""
    record = read_json(RECORD, owner=0)
    dropin = SYSTEMD / f"user@{uid}.service.d" / DROPIN
    require(
        set(record) == {"dropin", "rules", "unit"}
        and sha(RULES) == record["rules"]
        and sha(UNIT) == record["unit"]
        and sha(dropin) == record["dropin"],
        "egress-files-drift",
    )
    lines = set(dropin.read_text().splitlines())
    require(
        {"Requires=hermes-egress.service", "After=hermes-egress.service"} <= lines,
        "egress-dropin-drift",
    )
    for state, expected_state in (("is-enabled", "enabled"), ("is-active", "active")):
        out = run(["systemctl", state, UNIT.name], check=False).stdout.decode().strip()
        require(out == expected_state, f"egress-unit-not-{expected_state}")
    require(covered(loaded(uid)), "egress-table-mismatch")
    return "egress-guard-active"


def default_gateway():
    """The host's IPv4 default gateway (a LAN router), or None without a default route."""
    routes = decode(run(["ip", "-j", "-4", "route", "show", "default"]).stdout or b"[]")
    for route in routes:
        if route.get("gateway"):
            return str(ipaddress.ip_address(route["gateway"]))
    return None
