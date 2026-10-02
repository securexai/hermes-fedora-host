"""Read-only Fedora contract. Collection failures are failures, never permissive defaults."""

from __future__ import annotations

import grp
import os
import platform
import pwd
import re
import shutil
import stat
from pathlib import Path

from .primitives import Refused, decode, digest, is_sha, read_json, require, run, sha

GIB = 1024**3
CONFIG = Path("/etc/hermes-production/host.json")
COMMISSION = Path("/etc/hermes-production/commissioning.json")
PACKAGES = (
    "podman",
    "container-selinux",
    "passt",
    "openssh-clients",
    "openssh-server",
    "policycoreutils",
    "shadow-utils",
    "sudo",
    "restic",
    "cryptsetup",
    "mokutil",
    "tpm2-tools",
    "tpm2-tss",
    "dracut",
    "systemd",
    "tar",
    "util-linux",
)
# Per-host proofs. Recovery-boot, cold-start and isolated-restore behavior is the
# same software on every host and is proven per release in the signed bundle's
# qualification evidence instead of being re-attested by hand on each machine.
HOST_PROOFS = frozenset({"recovery_unlock", "encrypted_offhost_recovery", "automatic_reboot"})
TARGET_PROOFS = frozenset({"console_access", "firmware_power_restoration"})
PROOFS = HOST_PROOFS | TARGET_PROOFS


def required_proofs(config):
    """Physical production targets also need console and wall-power proofs."""
    return PROOFS if config["kind"] == "production" else HOST_PROOFS


# Installed by the unattended installer; the only Hermes unit allowed before bootstrap.
COMMISSION_UNIT = Path("/etc/systemd/system/hermes-commission.service")
COMMISSION_UNIT_BYTES = b"""[Unit]
Description=Hermes production commissioning (until all proofs pass)
Wants=network-online.target
After=network-online.target sshd-keygen.target sshd.service
ConditionPathExists=!/var/lib/hermes-production/commissioned

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/python3 -I -B /usr/local/libexec/hermes-installer/productionctl.py commission-boot
ExecStop=/usr/bin/python3 -I -B /usr/local/libexec/hermes-installer/productionctl.py commission-boot --clean-shutdown
TimeoutStartSec=1800

[Install]
WantedBy=multi-user.target
"""


def commissioning_unit(path):
    """The exact installer-written unit, or its enablement symlink; nothing else."""
    path = Path(path)
    if path == COMMISSION_UNIT:
        info = path.lstat()
        return (
            stat.S_ISREG(info.st_mode)
            and info.st_uid == 0
            and not info.st_mode & 0o022
            and path.read_bytes() == COMMISSION_UNIT_BYTES
        )
    return (
        path.name == COMMISSION_UNIT.name
        and path.parent == COMMISSION_UNIT.parent / "multi-user.target.wants"
        and path.is_symlink()
        and os.readlink(path) in (str(COMMISSION_UNIT), "../" + COMMISSION_UNIT.name)
    )


def configuration(value):
    require(
        isinstance(value, dict)
        and set(value)
        == {
            "schema",
            "kind",
            "application_mode",
            "machine_id",
            "home_uuid",
            "luks_uuid",
            "ssh_host_sha256",
            "artifact_budget_bytes",
            "state_budget_bytes",
            "restic_repository",
            "restic_password_file",
            "deploy_public_key",
            "deploy_from",
        },
        "invalid-host-fields",
    )
    require(
        value["schema"] == 1 and value["kind"] in ("production", "fixture"), "invalid-host-schema"
    )
    require(
        value["application_mode"] in ("production", "synthetic")
        and (value["kind"] == "fixture" or value["application_mode"] == "production"),
        "invalid-application-mode",
    )
    require(re.fullmatch(r"[a-f0-9]{32}", value["machine_id"] or ""), "invalid-machine-id")
    for field in ("home_uuid", "luks_uuid"):
        require(
            re.fullmatch(r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}", value[field] or ""),
            "invalid-storage-uuid",
        )
    require(is_sha(value["ssh_host_sha256"]), "invalid-ssh-host-hash")
    for field in ("artifact_budget_bytes", "state_budget_bytes"):
        require(
            type(value[field]) is int and GIB <= value[field] <= 16 * 1024 * GIB,
            "invalid-capacity-budget",
        )
    # SFTP only: no credentials in URLs, arbitrary restic helper commands, or local-only
    # backup. "none" is an explicit operator decision to run without off-host backup;
    # the backup operation then refuses instead of pretending to protect anything.
    require(
        value["restic_repository"] == "none"
        or re.fullmatch(
            r"sftp:[a-z_][a-z0-9_-]*@[A-Za-z0-9.-]+:/[A-Za-z0-9_./-]+",
            value["restic_repository"] or "",
        ),
        "offhost-sftp-repository-required",
    )
    require(
        value["restic_password_file"] == "/etc/hermes-production/restic-password",
        "unexpected-backup-secret-path",
    )
    require(
        re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/]{60,100}={0,2}", value["deploy_public_key"] or ""),
        "invalid-deployment-public-key",
    )
    import ipaddress

    try:
        network = ipaddress.ip_network(value["deploy_from"], strict=True)
    except ValueError as exc:
        raise Refused("invalid-deployment-source-network") from exc
    require(network.prefixlen > 0, "deployment-source-unrestricted")
    return value


def text(*argv):
    return run(list(argv)).stdout.decode().strip()


def mount(path):
    rows = decode(
        run(["findmnt", "--json", "--target", str(path), "-o", "TARGET,SOURCE,FSTYPE,UUID"]).stdout
    )
    require(len(rows["filesystems"]) == 1, "ambiguous-mount")
    return rows["filesystems"][0]


def encrypted(source, expected):
    """All ancestry paths must cross the expected LUKS2 mapping; reject layered/RAID ambiguity."""
    require(source.startswith("/dev/") and "[" not in source, "unsupported-storage-source")
    nodes = decode(
        run(["lsblk", "--json", "--inverse", "--paths", "-o", "NAME,TYPE,FSTYPE", source]).stdout
    )["blockdevices"]
    seen = set()

    def walk(node):
        name, kind = node["name"], node["type"]
        require(name not in seen, "ambiguous-storage-ancestry")
        seen.add(name)
        if kind == "crypt":
            parents = node.get("children", [])
            require(len(parents) == 1, "ambiguous-encrypted-device")
            device = parents[0]["name"]
            require(text("cryptsetup", "luksUUID", device) == expected, "unexpected-luks-device")
            metadata = decode(
                run(["cryptsetup", "luksDump", "--dump-json-metadata", device]).stdout
            )
            require(metadata.get("keyslots"), "missing-luks2-keyslots")
            return device, metadata
        require(kind in ("lvm", "part", "disk"), "unsupported-storage-topology")
        if kind == "lvm":
            require(text("lvs", "--noheadings", "-o", "segtype", name) == "linear", "nonlinear-lvm")
        parents = node.get("children", [])
        require(len(parents) == 1, "unencrypted-or-ambiguous-storage")
        return walk(parents[0])

    require(len(nodes) == 1, "ambiguous-storage-device")
    return walk(nodes[0])


def subordinate(path, uid):
    ranges = []
    own = []
    for line in Path(path).read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        name, start, count = line.split(":")
        start, count = int(start), int(count)
        require(start >= 65536 and count > 0, "invalid-subordinate-range")
        ranges.append((start, start + count))
        if name in ("hermes", str(uid)):
            own.append((start, count))
    ranges.sort()
    require(all(a[1] <= b[0] for a, b in zip(ranges, ranges[1:])), "overlapping-subordinate-ranges")
    require(len(own) == 1 and own[0][1] >= 65536, "runtime-subordinate-range-missing")


def account(*, required=False):
    try:
        user = pwd.getpwnam("hermes")
    except KeyError:
        require(not required, "runtime-account-missing")
        return
    require(
        user.pw_uid >= 1000
        and user.pw_dir == "/home/hermes"
        and user.pw_shell in ("/sbin/nologin", "/usr/sbin/nologin"),
        "runtime-account-conflict",
    )
    require(
        {g.gr_name for g in grp.getgrall() if "hermes" in g.gr_mem} <= {"hermes"},
        "runtime-supplementary-groups",
    )
    require(grp.getgrgid(user.pw_gid).gr_name == "hermes", "runtime-primary-group")
    require(text("passwd", "-S", "hermes").split()[1] in ("L", "LK"), "runtime-password-unlocked")
    # Listing denial can exit 0 (Fedora sudo) or 1. Accept only the complete
    # C-locale denial, never a grant or an inspection error containing similar text.
    result = run(["sudo", "-n", "-l", "-U", "hermes"], check=False)
    require(
        result.returncode in (0, 1)
        and re.fullmatch(
            rb"User hermes is not allowed to run sudo on [A-Za-z0-9_.-]+\.",
            (result.stdout + result.stderr).strip(),
        )
        is not None,
        "runtime-sudo-access-or-inspection-failed",
    )
    for file in ("/etc/subuid", "/etc/subgid"):
        subordinate(file, user.pw_uid)
    require(not (Path(user.pw_dir) / ".ssh/authorized_keys").exists(), "runtime-ssh-access")
    return user


def boot(config, metadata):
    tokens = [v for v in metadata.get("tokens", {}).values() if v.get("type") == "systemd-tpm2"]
    require(len(tokens) == 1, "expected-one-tpm-token")
    token = tokens[0]
    require(
        token.get("tpm2-pcrs") == [7]
        and token.get("tpm2-pcr-bank") == "sha256"
        # systemd 259 omits this field for a no-PIN enrollment.
        and token.get("tpm2-pin", False) is False
        and not token.get("tpm2_pcrlock")
        and not token.get("tpm2_pubkey_pcrs")
        and not token.get("tpm2-public-key-pcrs"),
        "unexpected-tpm-policy",
    )
    require(len(metadata["keyslots"]) >= 2, "recovery-keyslot-missing")
    entries = [
        line.split()
        for line in Path("/etc/crypttab").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    entries = [e for e in entries if len(e) >= 2 and e[1] == "UUID=" + config["luks_uuid"]]
    require(
        len(entries) == 1
        and len(entries[0]) == 4
        and entries[0][2] in ("none", "-")
        and "tpm2-device=auto" in entries[0][3].split(","),
        "crypttab-policy-mismatch",
    )
    modules = text("lsinitrd", "-m", "/boot/initramfs-" + platform.release() + ".img").split()
    require({"systemd-cryptsetup", "tpm2-tss"} <= set(modules), "initramfs-tpm-modules-missing")
    return digest(
        {
            "token": token,
            "crypttab": entries,
            "kernel": platform.release(),
            "initramfs": sha("/boot/initramfs-" + platform.release() + ".img"),
            "secureboot": text("mokutil", "--sb-state"),
            "pcr7_sha256": text("tpm2_pcrread", "sha256:7"),
        }
    )


def collect(config, *, commissioned=True, installed=False, capacity=True):
    """Return only nonsecret evidence; aggregate independently actionable failures."""
    configuration(config)
    require(os.geteuid() == 0, "root-required-for-read-only-inspection")
    checks, facts = {}, {}

    def check(name, fn):
        try:
            facts[name] = fn()
            checks[name] = "PASS"
        except (Refused, OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            checks[name] = "FAIL"
            facts[name] = str(exc) if isinstance(exc, Refused) else "inspection-unavailable"

    def host():
        release = platform.freedesktop_os_release()
        require(
            release.get("ID") == "fedora"
            and release.get("VERSION_ID") == "44"
            and release.get("VARIANT_ID") == "server"
            and platform.machine() == "x86_64",
            "requires-x86_64-fedora-server-44",
        )
        require(
            Path("/etc/machine-id").read_text().strip() == config["machine_id"],
            "machine-identity-mismatch",
        )
        require(
            sha("/etc/ssh/ssh_host_ed25519_key.pub") == config["ssh_host_sha256"],
            "ssh-host-identity-mismatch",
        )
        require(
            text("getenforce") == "Enforcing"
            and Path("/sys/fs/cgroup/cgroup.controllers").exists(),
            "selinux-or-cgroup-contract",
        )
        require(
            Path("/sys/firmware/efi").is_dir()
            and Path("/dev/tpmrm0").exists()
            and text("mokutil", "--sb-state") == "SecureBoot enabled",
            "secureboot-tpm-required",
        )
        require(
            os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") >= 8 * GIB - 256 * 1024**2,
            "minimum-8gib-memory",
        )
        require(
            not text("swapon", "--noheadings", "--show=NAME"), "production-profile-requires-no-swap"
        )
        return "fedora44-x86_64-enforcing"

    def storage():
        home = mount("/home/hermes")
        require(
            home["target"] == "/home/hermes"
            and home["fstype"] == "xfs"
            and home["uuid"] == config["home_uuid"],
            "dedicated-hermes-xfs-mount-required",
        )
        device, metadata = encrypted(home["source"], config["luks_uuid"])
        for target in ("/", "/var", "/etc", "/var/lib/hermes-production"):
            # The controller state directory may not exist until bootstrap.
            probe = target if Path(target).exists() else "/var/lib"
            encrypted(mount(probe)["source"], config["luks_uuid"])
        if capacity:
            require(
                shutil.disk_usage("/var").free
                >= 20 * GIB
                + 3 * config["artifact_budget_bytes"]
                + 2 * config["state_budget_bytes"],
                "var-capacity-for-artifacts-and-backups",
            )
            require(
                shutil.disk_usage("/home/hermes").free
                >= config["artifact_budget_bytes"] + config["state_budget_bytes"],
                "hermes-capacity-insufficient",
            )
        return {"device": device, "boot_sha256": boot(config, metadata)}

    def packages():
        run(["rpm", "-q", *PACKAGES, "lvm2"])
        version = tuple(map(int, text("podman", "--version").split()[-1].split(".")[:3]))
        require(version >= (5, 8, 4), "podman-at-least-5.8.4-required")
        return sorted(
            text(
                "rpm", "-q", "--qf", "%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\n", *PACKAGES, "lvm2"
            ).splitlines()
        )

    check("platform", host)
    check("packages", packages)

    def ssh_policy():
        output = run(
            [
                "sshd",
                "-T",
                "-C",
                "user=hermes-deploy,host=localhost,addr=" + config["deploy_from"].split("/")[0],
            ]
        ).stdout.splitlines()
        require(
            b"usepam yes" in output and b"pubkeyauthentication yes" in output,
            "ssh-pam-public-key-policy-required",
        )
        return "PAM-and-public-key-enabled"

    check("ssh_policy", ssh_policy)
    check("storage_boot", storage)
    check("runtime_account", lambda: account(required=installed) and "compatible")

    def conflicts():
        marker = Path("/var/lib/hermes-production/bootstrap.json")
        managed = marker.exists() and read_json(marker, owner=0) == {"host_sha256": digest(config)}
        if not managed:
            require(
                not any(
                    path.exists() or path.is_symlink()
                    for path in (
                        Path("/etc/sudoers.d/hermes-production"),
                        Path("/etc/ssh/hermes-production"),
                        Path("/etc/ssh/sshd_config.d/40-hermes-production.conf"),
                        Path("/usr/local/libexec/hermes-production"),
                    )
                ),
                "unmanaged-controller-path-conflict",
            )
            require(
                not any(Path("/home/hermes").glob("*-state")), "existing-unmanaged-hermes-state"
            )
            locations = (Path("/etc/containers/systemd"), Path("/etc/systemd/system"))
            require(
                not any(
                    p.name.startswith("hermes-") and not commissioning_unit(p)
                    for d in locations
                    for p in d.rglob("*")
                ),
                "unmanaged-hermes-unit-conflict",
            )
            require(
                not any(
                    (Path("/home/hermes") / name).exists()
                    for name in ("gateway-ssh", "transport", ".local/share/containers")
                ),
                "unmanaged-runtime-resources",
            )
            try:
                pwd.getpwnam("hermes-deploy")
            except KeyError:
                pass
            else:
                raise Refused("unmanaged-deployment-account")
        # Runtime account must have no user-owned startup overrides.
        for name in (".config/systemd/user", ".config/containers/systemd"):
            require(not (Path("/home/hermes") / name).exists(), "runtime-unit-override-conflict")
        return "no-conflicts"

    check("conflicts", conflicts)
    if commissioned:

        def proofs():
            report = read_json(COMMISSION, owner=0)
            require(
                set(report)
                == {"host_sha256", "boot_sha256", "packages_sha256", "gates", "evidence"}
                and report["host_sha256"] == digest(config)
                and report["boot_sha256"] == facts["storage_boot"]["boot_sha256"]
                and report["packages_sha256"] == digest(facts["packages"]),
                "commissioning-stale",
            )
            require(
                set(report["gates"]) == PROOFS
                and all(report["gates"][gate] == "PASS" for gate in required_proofs(config))
                and set(report["gates"].values()) <= {"PASS", "FAIL", "BLOCKED", "NOT_RUN", "STALE"}
                and set(report["evidence"]) == PROOFS
                and all(is_sha(v) for v in report["evidence"].values()),
                "commissioning-incomplete",
            )
            return "commissioning-evidence-current"

        check("commissioning", proofs)
    return {
        "status": "PASS" if set(checks.values()) == {"PASS"} else "FAIL",
        "host_sha256": digest(config),
        "checks": checks,
        "facts": facts,
        "commissioning_identity": {
            "host_sha256": digest(config),
            "boot_sha256": facts["storage_boot"].get("boot_sha256")
            if isinstance(facts.get("storage_boot"), dict)
            else None,
            "packages_sha256": digest(facts["packages"]) if checks["packages"] == "PASS" else None,
        },
    }


def enforce(config, **kwargs):
    report = collect(config, **kwargs)
    require(
        report["status"] == "PASS",
        "host-preflight-failed:" + ",".join(k for k, v in report["checks"].items() if v != "PASS"),
    )
    return report
