#!/usr/bin/env python3
"""One-command unattended release qualification in a disposable Secure Boot + TPM2 VM.

Builds run-local test keys and escrow, signs a candidate from the current source,
builds the unattended ISO, installs a fresh VM, then drives the real operator
interface: pin, enroll, deploy, rerun, failed and successful upgrade, rollback,
warm reboot, cold start, escrowed-recovery-key boot and canary checks. Every stage
is timed. Gates that need inputs this run lacks (an off-host backup host, real
provider credentials) are reported BLOCKED, never PASS.

Preview by default; `--apply` creates and later destroys the owned VM.
"""

from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import importlib.util
import io
import ipaddress
import json
import os
import pty
import re
import select
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/hermes"))
from production import bundle, client, escrow, media  # noqa: E402
from production.primitives import (  # noqa: E402
    Refused,
    atomic,
    canonical,
    decode,
    read_json,
    regular,
    require,
    sha,
)

CTL = ROOT / "scripts/hermes/productionctl.py"
WORK = ROOT / ".toolbox/hermes-qualify"
ROLE = "qualify"
ADMIN = "hermesadmin"
PROMPT = re.compile(rb"(?i)(?:passphrase|recovery key) for disk")
FINGERPRINT = re.compile(rb"SSH host key: (SHA256:[A-Za-z0-9+/]{43}) \(ED25519\)")
ESCROW_ONLY = re.compile(rb"Pending: encrypted_offhost_recovery\r?\n")
PLAIN_VARS = Path("/usr/share/edk2/ovmf/OVMF_VARS_4M.qcow2")
MIB = 1024**2


def load_fixture():
    spec = importlib.util.spec_from_file_location(
        "hermes_production_fixture", ROOT / "vm/hermes-production-fixture.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURE = load_fixture()
NAME, VM_DIR, PORT = FIXTURE.FIXTURES[ROLE]


class Stop(Exception):
    pass


def environment():
    return FIXTURE.session_environment() | {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C"}


def command(argv, *, timeout=600, check=True, data=None):
    result = subprocess.run(
        argv, input=data, capture_output=True, timeout=timeout, env=environment()
    )
    if check and result.returncode:
        reason = result.stderr.decode(errors="replace").strip().splitlines()[-1:] or ["no-output"]
        raise Refused(f"{Path(argv[0]).name}-failed:{reason[0][:200]}")
    return result


command_ = command


def ctl(*args, timeout=7200):
    """The real operator CLI; only its sanitized STOP reason is surfaced on failure."""
    result = command([sys.executable, "-I", "-B", str(CTL), *args], timeout=timeout, check=False)
    if result.returncode:
        stop = [
            line
            for line in result.stderr.decode(errors="replace").splitlines()
            if line.startswith("STOP:")
        ]
        raise Refused("productionctl-" + args[0] + ":" + (stop[-1] if stop else "failed"))
    return decode(result.stdout)


def virsh(*args, check=True, timeout=120):
    return command(["virsh", "-c", "qemu:///session", *args], timeout=timeout, check=check)


def state():
    return virsh("domstate", NAME, check=False).stdout.decode().strip()


def wait_state(target, timeout):
    deadline = time.monotonic() + timeout
    while state() != target:
        require(time.monotonic() < deadline, f"timeout-waiting-for-{target.replace(' ', '-')}")
        time.sleep(5)


class Run:
    def __init__(self, args):
        self.args = args
        self.stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
        self.dir = WORK / "runs" / self.stamp
        self.stages, self.facts = [], {}
        self.serial = VM_DIR / "serial.log"

    # Bookkeeping ---------------------------------------------------------------
    def save(self):
        report = {
            "run": self.stamp,
            "vm": NAME,
            "stages": self.stages,
            "facts": self.facts,
            "gates": self.gates(),
            "gate_waivers": self.waivers(),
            "gate_limits": GATE_LIMITS,
        }
        atomic(self.dir / "qualification-report.json", canonical(report), 0o600)
        return report

    def stage(self, name, function):
        started = time.monotonic()
        try:
            detail, status = function(), "PASS"
        except Exception as exc:  # noqa: BLE001 - every failure is reported, then stops
            detail = str(exc) if isinstance(exc, Refused) else f"{type(exc).__name__}: {exc}"
            status = "FAIL"
        self.stages.append(
            {
                "stage": name,
                "status": status,
                "seconds": round(time.monotonic() - started, 1),
                "detail": detail,
            }
        )
        self.save()
        print(f"[{status}] {name} ({self.stages[-1]['seconds']}s)", flush=True)
        if status == "FAIL":
            raise Stop(name)
        return detail

    def passed(self, *names):
        done = {row["stage"] for row in self.stages if row["status"] == "PASS"}
        return all(name in done for name in names)

    def gates(self):
        gates = dict.fromkeys(sorted(bundle.GATES), "NOT_RUN")
        failed = {row["stage"] for row in self.stages if row["status"] == "FAIL"}
        for gate, stages in GATE_STAGES.items():
            if failed & set(stages):
                gates[gate] = "FAIL"
            elif self.passed(*stages):
                gates[gate] = "PASS"
        # Off-host isolated restore needs a backup host. Only the operator's explicit
        # no-backup decision turns the local restore evidence into a PASS (recorded).
        if gates["restore"] == "PASS" and not self.args.no_offhost_backup:
            gates["restore"] = "BLOCKED"
        if not self.args.live_env and gates["application"] == "NOT_RUN":
            gates["application"] = "BLOCKED"
        return gates

    def waivers(self):
        if not self.args.no_offhost_backup:
            return {}
        return {
            "restore": "operator decision 2026-10-01: no off-host backup host; the release "
            "is qualified on failed-update restore, rollback and interruption recovery only"
        }

    # Helpers -------------------------------------------------------------------
    def target(self):
        return [
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
            "--known-hosts",
            str(self.dir / "known_hosts"),
            "--identity",
            str(self.dir / "deploy_ed25519"),
        ]

    def admin(self, remote_command, *, check=True, timeout=30):
        argv = client.ssh(
            "127.0.0.1",
            PORT,
            ADMIN,
            self.dir / "admin_ed25519",
            self.dir / "known_hosts",
            remote_command,
        )
        return command(argv, timeout=timeout, check=check)

    def boot_id(self):
        result = self.admin("cat /proc/sys/kernel/random/boot_id", check=False)
        value = result.stdout.decode().strip()
        return value if result.returncode == 0 and re.fullmatch(r"[a-f0-9-]{36}", value) else None

    def wait_boot(self, previous, timeout=1200):
        deadline = time.monotonic() + timeout
        while True:
            current = self.boot_id()
            if current and current != previous:
                return current
            require(time.monotonic() < deadline, "timeout-waiting-for-new-boot")
            time.sleep(5)

    def offset(self):
        return self.serial.stat().st_size if self.serial.exists() else 0

    def output_since(self, offset):
        if not self.serial.exists():
            return b""
        with self.serial.open("rb") as stream:
            stream.seek(offset)
            return stream.read()

    def wait_log(self, pattern, offset, timeout):
        deadline = time.monotonic() + timeout
        while True:
            output = self.output_since(offset)
            require(
                PROMPT.search(output) is None, "unexpected-passphrase-prompt-tpm-did-not-unseal"
            )
            match = pattern.search(output)
            if match:
                return match
            require(time.monotonic() < deadline, "timeout-waiting-for-console-output")
            time.sleep(5)

    def no_prompt_since(self, offset):
        require(PROMPT.search(self.output_since(offset)) is None, "passphrase-prompt-observed")

    # Stages --------------------------------------------------------------------
    def prepare(self):
        for path in (WORK, WORK / "runs", self.dir):
            path.mkdir(mode=0o700, exist_ok=path != self.dir)
        require(shutil.disk_usage(WORK).free >= 30 * 1024**3, "qualification-needs-30gib-free")
        for name in ("admin_ed25519", "deploy_ed25519", "signing_ed25519"):
            command(
                [
                    "ssh-keygen",
                    "-q",
                    "-t",
                    "ed25519",
                    "-N",
                    "",
                    "-C",
                    name,
                    "-f",
                    str(self.dir / name),
                ]
            )
        signer = (self.dir / "signing_ed25519.pub").read_text().split()
        atomic(
            self.dir / "allowed_signers",
            f'hermes-production namespaces="{bundle.NAMESPACE}" {signer[0]} {signer[1]}\n'.encode(),
            0o644,
        )
        escrow.generate(self.dir / "escrow", encrypt=False, apply=True)
        settings = {
            "disk_id": FIXTURE.DISK_ID,
            "disk_min_mib": 180000,
            "root_mib": 30720,
            "var_mib": 81920,
            "hermes_mib": 61440,
            "hostname": "hermes-qualify.test",
            "admin": ADMIN,
            "admin_public_key": " ".join((self.dir / "admin_ed25519.pub").read_text().split()[:2]),
            "timezone": "Etc/UTC",
            "kind": "fixture",
            "application_mode": "production" if self.args.live_env else "synthetic",
            "escrow_certificate": (self.dir / "escrow/escrow-certificate.pem").read_text(),
            "deploy_public_key": " ".join(
                (self.dir / "deploy_ed25519.pub").read_text().split()[:2]
            ),
            "deploy_from": self.args.deploy_from or default_gateway(),
            "artifact_budget_bytes": 4 * 1024**3,
            "state_budget_bytes": 4 * 1024**3,
            # Without a backup host the operator's explicit "none" is recorded as such.
            "restic_repository": "none"
            if self.args.no_offhost_backup
            else "sftp:backup@backup.invalid:/hermes-qualification",
        }
        atomic(self.dir / "settings.json", canonical(settings), 0o600)
        tools = media.tools(apply=True)
        self.facts["deploy_from"] = settings["deploy_from"]
        return {"run": str(self.dir), "media_tools": tools["status"]}

    def candidates(self):
        candidate = self.dir / "candidate.tar"
        ctl(
            "bundle",
            "--artifacts",
            str(self.args.artifacts),
            "--signing-key",
            str(self.dir / "signing_ed25519"),
            "--output",
            str(candidate),
            "--apply",
        )
        identities = derive_candidates(self.dir)
        self.facts["candidates"] = identities
        return identities

    def media(self):
        result = ctl(
            "media",
            "--settings",
            str(self.dir / "settings.json"),
            "--signers",
            str(self.dir / "allowed_signers"),
            "--iso",
            str(self.args.iso),
            "--checksum",
            str(self.args.checksum),
            "--output",
            str(self.dir / "hermes-qualify.iso"),
            "--serial-console",
            "--apply",
        )
        self.facts["media"] = {
            k: result[k] for k in ("media_sha256", "manifest_sha256", "iso_sha256")
        }
        return self.facts["media"]

    def create(self):
        result = FIXTURE.create(
            self.dir / "hermes-qualify.iso", self.dir / "settings.json", apply=True, role=ROLE
        )
        self.facts["unrelated_sha256"] = result["unrelated_sha256"]
        return result["status"]

    def install(self):
        wait_state("shut off", 90 * 60)
        media_path = str(self.dir / "hermes-qualify.iso")
        command(
            [
                "virt-xml",
                "--connect",
                "qemu:///session",
                NAME,
                "--remove-device",
                "--disk",
                f"path={media_path}",
            ]
        )
        command(
            [
                "virt-xml",
                "--connect",
                "qemu:///session",
                NAME,
                "--edit",
                "--events",
                "on_reboot=restart",
            ]
        )
        xml = virsh("dumpxml", NAME, "--inactive").stdout.decode()
        require(media_path not in xml, "installation-media-still-attached")
        require("<on_reboot>restart</on_reboot>" in xml, "reboot-policy-not-restored")
        self.commission_offset = self.offset()
        virsh("start", NAME)
        return {"usb_media_removed": True}

    def commission(self):
        # Two automatic boots: firstboot bootstraps and reboots, the second proves TPM unlock.
        self.wait_log(ESCROW_ONLY, self.commission_offset, 60 * 60)
        prints = FINGERPRINT.findall(self.output_since(self.commission_offset))
        require(prints and len(set(prints)) == 1, "console-fingerprint-unavailable")
        fingerprint = prints[-1].decode()
        ctl(
            "pin-host",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
            "--fingerprint",
            fingerprint,
            "--known-hosts",
            str(self.dir / "known_hosts"),
            "--apply",
        )
        return {"fingerprint": fingerprint}

    def enroll(self):
        result = ctl(
            "enroll",
            *self.target(),
            "--admin",
            ADMIN,
            "--admin-identity",
            str(self.dir / "admin_ed25519"),
            "--escrow-key",
            str(self.dir / "escrow/escrow-key.pem"),
            "--escrow-out",
            str(self.dir / "escrow.cms"),
            "--apply",
        )
        require(result["commissioning"]["status"] == "COMMISSIONED", "commissioning-incomplete")
        cockpit = self.root(
            "systemctl is-enabled cockpit.socket; systemctl is-active cockpit.socket; "
            "firewall-cmd --list-services",
            check=False,
        ).stdout.decode()
        require(
            cockpit.split()[:2] == ["disabled", "inactive"]
            and "cockpit" not in cockpit.split()[2:],
            "cockpit-web-console-not-disabled",
        )
        require(
            self.admin("test -e hermes-escrow.cms", check=False).returncode != 0,
            "server-escrow-copy-remains",
        )
        return {"members": result["members"], "commissioning": result["commissioning"]["status"]}

    def deploy(self):
        first = ctl(
            "deploy", *self.target(), "--bundle", str(self.dir / "candidate.tar"), "--apply"
        )
        require(first["status"] == "CHANGED", "initial-deploy-not-changed")
        require(first["release"] == self.facts["candidates"]["candidate"], "unexpected-release")
        require(ctl("verify", *self.target())["status"] == "PASS", "verify-failed")
        self.facts["deploy_timings"] = first.get("timings")
        # The forced command accepts named requests only; anything else is refused.
        argv = client.ssh(
            "127.0.0.1",
            PORT,
            "hermes-deploy",
            self.dir / "deploy_ed25519",
            self.dir / "known_hosts",
            "id",
        )
        for request in (b'{"apply":true,"operation":"exec"}\n', b"id\n"):
            refused = command(argv, data=request, check=False, timeout=60)
            require(refused.returncode != 0, "dispatcher-accepted-unknown-request")
        return {"release": first["release"]}

    def rerun(self):
        again = ctl(
            "deploy", *self.target(), "--bundle", str(self.dir / "candidate.tar"), "--apply"
        )
        require(again["status"] == "UNCHANGED", "rerun-not-unchanged")
        return again["status"]

    def failed_update(self):
        try:
            ctl("upgrade", *self.target(), "--bundle", str(self.dir / "corrupt.tar"), "--apply")
        except Refused:
            pass
        else:
            raise Refused("corrupt-candidate-accepted")
        current = ctl("status", *self.target())["current"]
        require(current["release"] == self.facts["candidates"]["candidate"], "current-changed")
        require(ctl("verify", *self.target())["status"] == "PASS", "verify-after-refusal")
        return "REFUSED_AND_UNCHANGED"

    def root(self, command, *, data=b"", timeout=300, check=True):
        """Break-glass root on the disposable VM with its escrowed test admin password."""
        if not hasattr(self, "_password"):
            self._password = escrow.unseal(
                self.dir / "escrow.cms", self.dir / "escrow/escrow-key.pem"
            )["admin-password"]
        argv = client.ssh(
            "127.0.0.1",
            PORT,
            ADMIN,
            self.dir / "admin_ed25519",
            self.dir / "known_hosts",
            "sudo -S -p '' sh -c " + shlex.quote(command),
        )
        return command_(argv, data=self._password + b"\n" + data, timeout=timeout, check=check)

    def dispatch_raw(self, request, timeout=120):
        """A raw named request, so the dispatcher's exact refusal reason is observable."""
        argv = client.ssh(
            "127.0.0.1",
            PORT,
            "hermes-deploy",
            self.dir / "deploy_ed25519",
            self.dir / "known_hosts",
        )
        return command_(argv, data=canonical(request), timeout=timeout, check=False)

    def background(self, *args):
        log = (self.dir / "background.log").open("wb")
        return subprocess.Popen(
            [sys.executable, "-I", "-B", str(CTL), *args],
            stdout=log,
            stderr=subprocess.STDOUT,
            env=environment(),
        )

    def lock_held(self):
        probe = "flock -n /var/lib/hermes-production/operation.lock true"
        return self.root(probe, check=False).returncode != 0

    def journal_stage(self):
        out = self.root("cat /var/lib/hermes-production/journal.json", check=False).stdout
        try:
            return decode(out)["stage"]
        except Refused:
            return None

    def current(self):
        return ctl("status", *self.target())["current"]["release"]

    def concurrent_upgrade(self):
        upgrade = self.background(
            "upgrade", *self.target(), "--bundle", str(self.dir / "upgrade.tar"), "--apply"
        )
        try:
            deadline = time.monotonic() + 300
            while not self.lock_held():
                require(upgrade.poll() is None, "upgrade-finished-before-concurrency-probe")
                require(time.monotonic() < deadline, "upgrade-lock-not-observed")
                time.sleep(1)
            busy = self.dispatch_raw({"operation": "rollback", "apply": True})
            require(
                busy.returncode != 0 and b"STOP: operation-busy" in busy.stderr,
                "concurrent-operation-not-refused-as-busy",
            )
            require(upgrade.wait(timeout=3600) == 0, "upgrade-failed")
        finally:
            if upgrade.poll() is None:
                upgrade.kill()
        require(self.current() == self.facts["candidates"]["upgrade"], "upgrade-release")
        require(ctl("verify", *self.target())["status"] == "PASS", "verify-after-upgrade")
        back = ctl("rollback", *self.target(), "--apply")
        require(back["release"] == self.facts["candidates"]["candidate"], "rollback-release")
        require(ctl("verify", *self.target())["status"] == "PASS", "verify-after-rollback")
        return {"concurrent": "operation-busy", "upgrade": "CHANGED", "rollback": back["status"]}

    def interrupted_upgrade(self):
        """SIGKILL the dispatcher mid-import; recovery must restore the previous release."""
        upgrade = self.background(
            "upgrade", *self.target(), "--bundle", str(self.dir / "upgrade.tar"), "--apply"
        )
        try:
            deadline = time.monotonic() + 900
            while self.journal_stage() not in ("import", "configuration"):
                require(upgrade.poll() is None, "upgrade-ended-before-interruption")
                require(time.monotonic() < deadline, "mutating-stage-not-observed")
                time.sleep(1)
            interrupted_at = self.journal_stage()
            # The bracket keeps pkill from matching its own sh/sudo command line.
            self.root("pkill -KILL -f '[p]roductionctl.py dispatch'")
            upgrade.wait(timeout=600)
        finally:
            if upgrade.poll() is None:
                upgrade.kill()
        deadline = time.monotonic() + 1800
        while True:
            result = self.dispatch_raw({"operation": "rollback", "apply": True}, timeout=1800)
            if result.returncode == 0:
                break
            require(b"operation-busy" in result.stderr, "recovery-refused")
            require(time.monotonic() < deadline, "writers-never-drained")
            time.sleep(10)
        require(self.current() == self.facts["candidates"]["candidate"], "recovery-release")
        require(ctl("verify", *self.target())["status"] == "PASS", "verify-after-recovery")
        return {"interrupted_at": interrupted_at, "recovered": decode(result.stdout)["status"]}

    def missing_mount(self):
        """Substituted and unavailable /home/hermes must block runtime and dispatcher.

        A plain unmount is not a fault: RequiresMountsFor makes systemd remount the right
        filesystem. Faults are a foreign filesystem at the path, or a mount that cannot run.
        """
        uid = self.root("id -u hermes").stdout.decode().strip()
        require(uid.isdigit(), "runtime-uid")
        user = f"user@{uid}.service"
        faults = {
            "substituted": "mount -t tmpfs -o mode=0700 hermes-substitute /home/hermes",
            "unavailable": "systemctl mask --runtime home-hermes.mount",
        }
        observed = {}
        for name, inject in faults.items():
            self.root(f"systemctl stop {user} && umount /home/hermes && {inject}")
            try:
                guard = self.root(f"systemctl start {user}", check=False)
                require(guard.returncode != 0, f"{name}-mount-did-not-block-runtime")
                refused = self.dispatch_raw({"operation": "status", "apply": False})
                require(
                    refused.returncode != 0 and b"host-preflight-failed" in refused.stderr,
                    f"dispatcher-accepted-{name}-mount",
                )
                observed[name] = "BLOCKED"
            finally:
                self.root(
                    f"systemctl stop {user}; systemctl unmask --runtime home-hermes.mount; "
                    "findmnt -n -o FSTYPE /home/hermes | grep -qx tmpfs && umount /home/hermes; "
                    f"systemctl reset-failed {user}; systemctl start home-hermes.mount {user}",
                    check=False,
                )
        require(ctl("verify", *self.target())["status"] == "PASS", "verify-after-remount")
        return observed

    def repository(self):
        log = self.dir / "repository-offline-checks.log"
        with log.open("wb") as stream:
            result = subprocess.run(
                [
                    "toolbox",
                    "run",
                    "--container",
                    self.args.toolbox,
                    "bash",
                    "-c",
                    f"cd {shlex.quote(str(ROOT))} && bash toolbox/run-offline-checks.sh",
                ],
                stdout=stream,
                stderr=subprocess.STDOUT,
                timeout=3600,
            )
        require(result.returncode == 0, "offline-gate-failed-see-repository-offline-checks.log")
        return {"log_sha256": sha(log)}

    def credentials(self):
        stored = ctl(
            "credentials", *self.target(), "--env-file", str(self.args.live_env), "--apply"
        )
        require(stored["status"] == "STORED", "credentials-not-stored")
        return stored

    def application(self):
        """Operator-observed live behavior; credentials never leave the operator's file.

        The contract requires approval for dangerous commands and memory writes, not for
        every command, so a harmless command must run directly and a destructive one must
        stop for approval.
        """
        require(sys.stdin.isatty(), "live-application-test-needs-an-interactive-terminal")
        results = {}
        results["tool_round_trip"] = ask(
            "From an ALLOWED Telegram account, send the bot:\n"
            "  Use the terminal tool to run: uname -sr\n"
            "Did it reply with a Linux kernel version?"
        )
        results["dangerous_command_needs_approval"] = ask(
            "Now send the bot:\n"
            "  Use the terminal tool to run: rm -rf /tmp/hermes-approval-check\n"
            "It must ask you to approve that command first. DENY it.\n"
            "Did it ask for approval, and not run the command after you denied it?"
        )
        rejecting = self.dir / "live-reject.env"
        text = regular(self.args.live_env, private=True).read_text()
        swapped = re.sub(r"(?m)^TELEGRAM_ALLOWED_USERS=.*$", "TELEGRAM_ALLOWED_USERS=1", text)
        try:
            atomic(rejecting, swapped.encode(), 0o600)
            ctl("credentials", *self.target(), "--env-file", str(rejecting), "--apply")
            results["unlisted_user_rejected"] = ask(
                "The allowlist now excludes your account. Send the bot any message.\n"
                "Did it stay silent for at least 60 seconds?"
            )
        finally:
            if rejecting.exists():
                rejecting.write_bytes(b"\0" * rejecting.stat().st_size)
                rejecting.unlink()
            ctl("credentials", *self.target(), "--env-file", str(self.args.live_env), "--apply")
        require(all(value == "YES" for value in results.values()), "live-application-failed")
        return results

    def warm_reboot(self):
        before, offset = self.boot_id(), self.offset()
        virsh("reboot", NAME)
        after = self.wait_boot(before)
        self.no_prompt_since(offset)
        require(ctl("verify", *self.target())["status"] == "PASS", "verify-after-reboot")
        return {"boot": after}

    def cold_start(self):
        before = self.boot_id()
        virsh("shutdown", NAME)
        wait_state("shut off", 10 * 60)
        offset = self.offset()
        virsh("start", NAME)
        after = self.wait_boot(before)
        self.no_prompt_since(offset)
        require(ctl("verify", *self.target())["status"] == "PASS", "verify-after-cold-start")
        return {"boot": after}

    def recovery_boot(self):
        """Secure Boot off for one boot changes PCR7: TPM refuses, the escrowed key unlocks."""
        key = escrow.unseal(self.dir / "escrow.cms", self.dir / "escrow/escrow-key.pem")[
            "recovery-key"
        ]
        before = self.boot_id()
        virsh("shutdown", NAME)
        wait_state("shut off", 10 * 60)
        xml = virsh("dumpxml", NAME, "--inactive").stdout.decode()
        nvram = Path(re.search(r"<nvram[^>]*>([^<]+)</nvram>", xml).group(1))
        saved = self.dir / "nvram.saved"
        shutil.copy2(nvram, saved)
        regular(PLAIN_VARS)
        shutil.copyfile(PLAIN_VARS, nvram)
        try:
            virsh("start", NAME)
            answer_prompt(key, timeout=15 * 60)
            during = self.wait_boot(before)
            state_ = self.admin("mokutil --sb-state", check=False).stdout.decode()
            require("disabled" in state_.lower(), "recovery-boot-did-not-change-secure-boot")
        finally:
            if state() != "shut off":
                virsh("shutdown", NAME, check=False)
                wait_state("shut off", 10 * 60)
            shutil.copyfile(saved, nvram)
        offset = self.offset()
        virsh("start", NAME)
        after = self.wait_boot(during)
        self.no_prompt_since(offset)
        require(ctl("verify", *self.target())["status"] == "PASS", "verify-after-recovery")
        return {"recovery_boot": during, "automatic_after": after}

    def canary(self):
        virsh("shutdown", NAME)
        wait_state("shut off", 10 * 60)
        require(sha(VM_DIR / "unrelated.raw") == self.facts["unrelated_sha256"], "canary-changed")
        return "UNCHANGED"

    def evidence(self):
        report = self.save()
        gates = report["gates"]
        digest_ = sha(self.dir / "qualification-report.json")
        atomic(
            self.dir / "qualification.json",
            canonical(
                {
                    "artifact_sha256": self.facts["candidates"]["candidate"],
                    "gates": gates,
                    "reports": dict.fromkeys(sorted(bundle.GATES), digest_),
                }
            ),
            0o600,
        )
        return gates


# What a local run cannot prove; reported with every result so no gate is overstated.
GATE_LIMITS = {
    "restore": "isolated restore from an encrypted off-host Restic repository needs a backup host",
    "application": "exact-candidate DeepSeek/Telegram/approval tests need --live-env credentials",
}
GATE_STAGES = {
    "repository": ("repository",),
    "installation": ("prepare", "media", "create", "install", "commission", "enroll", "canary"),
    "runtime": ("deploy",),
    "repeatability": (
        "rerun",
        "failed_update",
        "concurrent_upgrade",
        "interrupted_upgrade",
        "missing_mount",
    ),
    "restore": ("failed_update", "concurrent_upgrade", "interrupted_upgrade"),
    "boot": ("commission", "warm_reboot", "cold_start", "recovery_boot"),
    "application": ("application",),
}
STAGES = (
    "prepare",
    "repository",
    "candidates",
    "media",
    "create",
    "install",
    "commission",
    "enroll",
    "credentials",
    "deploy",
    "application",
    "rerun",
    "failed_update",
    "concurrent_upgrade",
    "interrupted_upgrade",
    "missing_mount",
    "warm_reboot",
    "cold_start",
    "recovery_boot",
    "canary",
)
LIVE_ONLY = {"credentials", "application"}


def ask(question):
    print("\n" + question + " [yes/no] ", end="", flush=True)
    return "YES" if sys.stdin.readline().strip().lower() in ("y", "yes") else "NO"


def default_gateway():
    """passt presents host-loopback connections from the host's default gateway."""
    routes = json.loads(command(["ip", "-j", "route", "show", "default"]).stdout or b"[]")
    require(len(routes) >= 1 and "gateway" in routes[0], "default-gateway-unavailable")
    return str(ipaddress.ip_network(routes[0]["gateway"] + "/32"))


def derive_candidates(directory):
    """Upgrade-marker and payload-corrupt variants of the freshly signed candidate."""
    source = directory / "candidate.tar"
    with tarfile.open(source, "r:") as original:
        baseline = json.loads(original.extractfile("manifest.json").read())
        changed = copy.deepcopy(baseline)
        name = "evidence/qualification-upgrade-marker.json"
        marker = canonical(
            {
                "scope": "upgrade-and-rollback-qualification-only",
                "baseline": bundle.identity(baseline),
            }
        )
        changed["files"][name] = {
            "sha256": hashlib.sha256(marker).hexdigest(),
            "size": len(marker),
            "mode": 0o644,
        }
        changed["qualification"]["artifact_sha256"] = bundle.identity(changed)
        bundle.validate(changed)
        with tempfile.TemporaryDirectory(prefix="signing-", dir=directory) as temporary:
            metadata = Path(temporary) / "manifest.json"
            metadata.write_bytes(canonical(changed))
            command(
                [
                    "ssh-keygen",
                    "-Y",
                    "sign",
                    "-f",
                    str(directory / "signing_ed25519"),
                    "-n",
                    bundle.NAMESPACE,
                    str(metadata),
                ],
                timeout=60,
            )
            replacements = {
                "manifest.json": metadata.read_bytes(),
                "manifest.sig": (Path(temporary) / "manifest.json.sig").read_bytes(),
            }
            with (
                (directory / "upgrade.tar").open("xb") as stream,
                tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as output,
            ):
                for item in original.getmembers():
                    if item.name in replacements:
                        data = replacements[item.name]
                        member = tarfile.TarInfo(item.name)
                        member.mode, member.size = item.mode, len(data)
                        output.addfile(member, io.BytesIO(data))
                    else:
                        output.addfile(item, original.extractfile(item))
                member = tarfile.TarInfo(name)
                member.mode, member.size = 0o644, len(marker)
                output.addfile(member, io.BytesIO(marker))
        target = "source/PRODUCTION_RUNBOOK.md"
        with (
            (directory / "corrupt.tar").open("xb") as stream,
            tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as output,
        ):
            for item in original.getmembers():
                data = original.extractfile(item).read() if item.name == target else None
                if data is not None:
                    output.addfile(item, io.BytesIO(bytes([data[0] ^ 1]) + data[1:]))
                else:
                    output.addfile(item, original.extractfile(item))
    return {"candidate": bundle.identity(baseline), "upgrade": bundle.identity(changed)}


def answer_prompt(key, timeout):
    """Attach to the serial console, wait for the LUKS prompt, type the test recovery key."""
    pid, fd = pty.fork()
    if pid == 0:
        os.execvpe(
            "virsh", ["virsh", "-c", "qemu:///session", "console", NAME, "--force"], environment()
        )
    seen, deadline = b"", time.monotonic() + timeout
    try:
        while not PROMPT.search(seen):
            require(time.monotonic() < deadline, "recovery-prompt-not-observed")
            ready, _, _ = select.select([fd], [], [], 5)
            if ready:
                try:
                    seen = (seen + os.read(fd, 4096))[-65536:]
                except OSError:
                    raise Refused("console-closed-before-prompt") from None
        time.sleep(1)
        os.write(fd, key + b"\r")
        time.sleep(5)
        os.write(fd, b"\x1d")
    finally:
        stop_console(pid, fd)


def stop_console(pid, fd):
    """Closing the pty hangs up virsh console; it ignores SIGTERM, so escalate to SIGKILL."""
    os.close(fd)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if os.waitpid(pid, os.WNOHANG)[0]:
            return
        time.sleep(0.5)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    os.waitpid(pid, 0)


def replace_previous():
    """Destroy only a VM this pipeline owns (ownership role check), never other guests."""
    ownership = VM_DIR / "ownership.json"
    exists = NAME in virsh("list", "--all", "--name").stdout.decode().split()
    if not exists and not VM_DIR.exists():
        return "NONE"
    require(read_json(ownership).get("role") == ROLE, "unowned-qualification-resources")
    if exists:
        if state() != "shut off":
            virsh("destroy", NAME, check=False)
        virsh("undefine", NAME, "--nvram", "--tpm")
    shutil.rmtree(VM_DIR)
    return "REMOVED"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", required=True, help="Fedora-Server-dvd-x86_64-44-*.iso")
    parser.add_argument("--checksum", required=True, help="Fedora-signed CHECKSUM file")
    parser.add_argument("--artifacts", required=True, help="Retained lab image cache entry")
    parser.add_argument("--deploy-from", help="Source network seen by the guest (default gateway)")
    parser.add_argument(
        "--toolbox", default="dev-infra-hermes", help="Toolbox for the offline gate"
    )
    parser.add_argument(
        "--no-offhost-backup",
        action="store_true",
        help="Operator decision: qualify restore on local recovery evidence (recorded waiver)",
    )
    parser.add_argument(
        "--live-env",
        help="Owner-only gateway environment for the operator-observed application test",
    )
    parser.add_argument(
        "--replace-previous",
        action="store_true",
        help="Remove the previous pipeline VM (owned role only)",
    )
    parser.add_argument("--keep", action="store_true", help="Keep the VM after the run")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if args.live_env:
        from production.runtime import credentials

        credentials(args.live_env, container_managed=False)  # Values are never printed.
    stages = [name for name in STAGES if args.live_env or name not in LIVE_ONLY]
    run = Run(args)
    if not args.apply:
        print(
            canonical(
                {
                    "status": "PREVIEW",
                    "vm": NAME,
                    "ssh": f"127.0.0.1:{PORT}",
                    "stages": stages,
                    "restore_waiver": bool(args.no_offhost_backup),
                    "application": "LIVE" if args.live_env else "BLOCKED",
                    "previous_vm": "present" if VM_DIR.exists() else "none",
                }
            ).decode(),
            end="",
        )
        return 0
    if args.replace_previous:
        replace_previous()
    require(not VM_DIR.exists(), "previous-qualification-vm-exists-use-replace-previous")
    status = 0
    try:
        for name in stages:
            run.stage(name, getattr(run, name))
    except Stop:
        status = 1
    finally:
        if run.dir.exists() and "candidates" in run.facts:
            run.evidence()
        if (
            not args.keep
            and status == 0
            and NAME in virsh("list", "--all", "--name").stdout.decode().split()
        ):
            replace_previous()
    print(
        canonical(
            {"status": "PASS" if status == 0 else "FAIL", "run": str(run.dir), "gates": run.gates()}
        ).decode(),
        end="",
    )
    return status


if __name__ == "__main__":
    os.umask(0o077)
    try:
        raise SystemExit(main())
    except Refused as exc:
        print("STOP: " + str(exc), file=sys.stderr)
        raise SystemExit(1) from None
