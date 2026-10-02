"""Host egress guard: the runtime account reaches the public internet, not local networks.

Rootless pasta opens the containers' connections from processes owned by the `hermes`
account, so one nftables output rule set keyed on that uid covers the worker and the
gateway: private, carrier-grade NAT, link-local (including cloud metadata), multicast and
reserved destinations are dropped, and so is host loopback except DNS (pasta forwards
container DNS to the host's stub resolver). The table is owned here and never touches
firewalld's own table. A oneshot unit loads it at boot before the user manager starts.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .primitives import atomic, decode, public_directory, require, run

TABLE = "hermes_egress"
RULES = Path("/etc/hermes-production/egress.nft")
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
    """Write the rules, unit and user-manager dependency (bootstrap, root)."""
    require(shutil.which("nft") is not None, "nftables-required")
    atomic(RULES, rules(uid), 0o644)
    atomic(UNIT, UNIT_BYTES, 0o644)
    dropin = SYSTEMD / f"user@{uid}.service.d"
    public_directory(dropin)
    atomic(dropin / DROPIN, DROPIN_BYTES, 0o644)
    return [RULES, UNIT, dropin / DROPIN]


def activate():
    """After daemon-reload: enable and start for boot, then reload the table in place.

    Never restart the unit: the runtime user manager Requires= it, so a restart would
    also restart the running application. The rules program replaces the owned table
    atomically, so loading it again is idempotent.
    """
    run(["systemctl", "enable", "--now", UNIT.name])
    run(["nft", "-f", str(RULES)])


def _prefixes(right):
    items = right.get("set") if isinstance(right, dict) and "set" in right else [right]
    found = set()
    for item in items:
        if isinstance(item, dict) and "prefix" in item:
            found.add(f"{item['prefix']['addr']}/{item['prefix']['len']}")
        else:
            found.add(str(item))
    return found


def loaded(uid):
    """Normalize the live table into comparable rules; refuse anything unexpected."""
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
        require(expr and "drop" in expr[-1], "egress-rule-not-drop")
        meta = [e["match"] for e in expr if "match" in e and "meta" in e["match"]["left"]]
        require(
            len(meta) == 1
            and meta[0]["left"]["meta"]["key"] == "skuid"
            and meta[0]["right"] == uid,
            "egress-rule-uid-mismatch",
        )
        dest = [
            e["match"]
            for e in expr
            if "match" in e and e["match"]["left"].get("payload", {}).get("field") == "daddr"
        ]
        require(len(dest) == 1, "egress-rule-destination")
        family = dest[0]["left"]["payload"]["protocol"]
        port = [
            e["match"]
            for e in expr
            if "match" in e and e["match"]["left"].get("payload", {}).get("field") == "dport"
        ]
        except_dns = len(port) == 1 and port[0]["op"] == "!=" and port[0]["right"] == 53
        require(not port or except_dns, "egress-rule-port")
        observed.append((family, frozenset(_prefixes(dest[0]["right"])), except_dns))
    return sorted(observed, key=repr)


def expected():
    return sorted(
        [
            ("ip", frozenset(BLOCKED_V4), False),
            ("ip6", frozenset(BLOCKED_V6), False),
            ("ip", frozenset({"127.0.0.0/8"}), True),
            ("ip6", frozenset({"::1"}), True),
        ],
        key=repr,
    )


def check(uid):
    """Loaded table, rules file and unit all match; the unit is enabled and active."""
    require(RULES.read_bytes() == rules(uid), "egress-rules-file-drift")
    require(UNIT.read_bytes() == UNIT_BYTES, "egress-unit-drift")
    dropin = SYSTEMD / f"user@{uid}.service.d" / DROPIN
    require(dropin.read_bytes() == DROPIN_BYTES, "egress-dropin-drift")
    for state, expected_state in (("is-enabled", "enabled"), ("is-active", "active")):
        out = run(["systemctl", state, UNIT.name], check=False).stdout.decode().strip()
        require(out == expected_state, f"egress-unit-not-{expected_state}")
    require(loaded(uid) == expected(), "egress-table-mismatch")
    return "egress-guard-active"


def host_address():
    """The host's own source address toward the internet (a LAN address on a VLAN)."""
    routes = decode(run(["ip", "-j", "route", "get", "1.1.1.1"]).stdout)
    require(routes and routes[0].get("prefsrc"), "egress-host-address-unavailable")
    return routes[0]["prefsrc"]
