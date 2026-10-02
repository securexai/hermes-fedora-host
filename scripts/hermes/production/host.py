"""Private commissioning bootstrap and bounded installed receiver."""

from __future__ import annotations

import os
import pwd
import stat
import tempfile
import time
from contextlib import ExitStack
from pathlib import Path

from . import bundle, preflight, receivers, startup
from .operations import Transaction
from .primitives import (
    Refused,
    atomic,
    canonical,
    decode,
    digest,
    durable_directory,
    lock,
    protected_directory,
    public_directory,
    read_json,
    regular,
    require,
    run,
)
from .runtime import STATE, Backend, credential_text, credentials

INSTALL = Path("/usr/local/libexec/hermes-production")
ETC = Path("/etc/hermes-production")
HOME = Path("/home/hermes")
SYSTEMD = Path("/etc/systemd/system")
SSH = Path("/etc/ssh")
SUDOERS = Path("/etc/sudoers.d/hermes-production")
DEPLOY_HOME = Path("/var/empty/hermes-deploy")
OPERATIONS = {"preflight", "deploy", "status", "verify", "backup", "upgrade", "rollback"}
# Named operations that carry one bounded body after the request header.
BODY_OPERATIONS = {"attest", "credentials"}


def mount_guard(config, uid):
    directory = SYSTEMD / f"user@{uid}.service.d"
    public_directory(directory)
    # Guard the system user manager (user units cannot order system mount units).
    content = (
        "[Unit]\nRequiresMountsFor=/home/hermes\n"
        "AssertPathIsMountPoint=/home/hermes\n"
        "[Service]\nExecStartPre=+/usr/local/libexec/hermes-production/productionctl.py mount-check\n"
    )
    atomic(directory / "50-hermes-mount.conf", content.encode(), 0o644)


def check_mount():
    config = read_json(INSTALL / "mount.json", owner=0)
    mounted = preflight.mount("/home/hermes")
    require(
        mounted["target"] == "/home/hermes"
        and mounted["fstype"] == "xfs"
        and mounted["uuid"] == config["home_uuid"],
        "expected-hermes-mount-absent",
    )
    if os.geteuid() == 0:
        preflight.encrypted(mounted["source"], config["luks_uuid"])
    startup.guard()


def bootstrap(config_path, signers, *, apply=False):
    require(os.geteuid() == 0, "private-root-console-required")
    config = preflight.configuration(read_json(config_path, owner=0))
    signer_data = regular(signers, owner=0).read_bytes()
    require(
        len(signer_data) <= 16384 and b"hermes-production " in signer_data,
        "production-signer-identity-required",
    )
    report = preflight.collect(config, commissioned=False)
    require(report["status"] == "PASS", "bootstrap-preflight-failed")
    if not apply:
        return {
            "status": "PREVIEW",
            "actions": [
                "install trusted receiver",
                "create locked runtime and bounded deployment accounts",
                "install mount guard and SSH forced command",
                "enable runtime user manager",
            ],
            "preflight": report,
        }
    # Recommissioning changes need local review; routine reruns are idempotent.
    if preflight.CONFIG.exists():
        require(
            read_json(preflight.CONFIG, owner=0) == config,
            "host-config-change-requires-recommissioning",
        )
        require(
            regular(ETC / "allowed_signers", owner=0).read_bytes() == signer_data,
            "signer-change-requires-recommissioning",
        )
    for path in (ETC, STATE):
        protected_directory(path)
    for name in ("releases", "backups", "attempts", "incoming"):
        protected_directory(STATE / name)
    with lock(STATE / "operation.lock"):
        source = Path(__file__).resolve().parents[1]
        require(startup.stable(), "recover-pending-transaction-before-bootstrap")
        if (STATE / "current.json").exists():
            current = read_json(STATE / "current.json", owner=0)
            require(
                read_json(INSTALL / "controller.json", owner=0)
                == {"receiver": current["receiver"]},
                "controller-application-selection-mismatch",
            )
            # Prove rollback policy is intact before staging another version.
            Backend(config).release(current["release"])
        receiver = receivers.install(source)
        atomic(preflight.CONFIG, canonical(config))
        atomic(
            INSTALL / "mount.json",
            canonical({"home_uuid": config["home_uuid"], "luks_uuid": config["luks_uuid"]}),
            0o644,
        )
        atomic(ETC / "allowed_signers", signer_data, 0o644)
        atomic(STATE / "bootstrap.json", canonical({"host_sha256": digest(config)}))
        if preflight.account() is None:
            # No broad admin/shell privilege and no replacement of existing identities.
            run(
                [
                    "useradd",
                    "--no-create-home",
                    "--user-group",
                    "--home-dir",
                    "/home/hermes",
                    "--shell",
                    "/usr/sbin/nologin",
                    "hermes",
                ]
            )
            run(["usermod", "--lock", "hermes"])
        account = preflight.account(required=True)
        require(HOME.stat().st_uid in (0, account.pw_uid), "home-owner-conflict")
        os.chown(HOME, account.pw_uid, account.pw_gid)
        os.chmod(HOME, 0o700)
        try:
            deployment = pwd.getpwnam("hermes-deploy")
        except KeyError:
            run(
                [
                    "useradd",
                    "--no-create-home",
                    "--user-group",
                    "--home-dir",
                    "/var/empty/hermes-deploy",
                    "--shell",
                    "/bin/sh",
                    "hermes-deploy",
                ]
            )
            run(["usermod", "--lock", "hermes-deploy"])
            deployment = pwd.getpwnam("hermes-deploy")
        require(
            deployment.pw_dir == "/var/empty/hermes-deploy"
            and deployment.pw_uid >= 1000
            and deployment.pw_shell == "/bin/sh",
            "deployment-account-conflict",
        )
        public_directory(DEPLOY_HOME)
        forced = str(INSTALL / "productionctl.py") + " dispatch"
        sudoers = f"hermes-deploy ALL=(root) NOPASSWD: {forced}\n"
        atomic(ETC / "sudoers.check", sudoers.encode(), 0o440)
        run(["visudo", "-cf", str(ETC / "sudoers.check")])
        atomic(SUDOERS, sudoers.encode(), 0o440)
        key = f'restrict,from="{config["deploy_from"]}",command="sudo -n {forced}" {config["deploy_public_key"]}\n'
        atomic(ETC / "authorized_keys", key.encode(), 0o644)
        # sshd reads the key as the unprivileged account: this directory contains only public keys.
        public = SSH / "hermes-production"
        public_directory(public)
        atomic(public / "authorized_keys", key.encode(), 0o644)
        sshd = (
            "Match User hermes-deploy\n    AuthenticationMethods publickey\n"
            "    PasswordAuthentication no\n    KbdInteractiveAuthentication no\n"
            "    AuthorizedKeysFile /etc/ssh/hermes-production/authorized_keys\n"
            "    DisableForwarding yes\n    PermitTTY no\n"
            f"    ForceCommand sudo -n {forced}\nMatch all\n"
        )
        sshpath = SSH / "sshd_config.d/40-hermes-production.conf"
        if sshpath.exists():
            require(regular(sshpath, owner=0).read_bytes() == sshd.encode(), "sshd-policy-conflict")
        atomic(sshpath, sshd.encode(), 0o600)
        run(["sshd", "-t"])
        effective = run(
            [
                "sshd",
                "-T",
                "-C",
                "user=hermes-deploy,host=localhost,addr=" + config["deploy_from"].split("/")[0],
            ]
        ).stdout
        for expected in (
            b"disableforwarding yes",
            b"permittty no",
            b"passwordauthentication no",
            b"authenticationmethods publickey",
            ("forcecommand sudo -n " + forced).encode(),
        ):
            require(expected in effective.splitlines(), "effective-sshd-policy-conflict")
        mount_guard(config, account.pw_uid)
        run(["systemctl", "daemon-reload"])
        run(
            [
                "restorecon",
                "-R",
                str(INSTALL),
                str(ETC),
                str(public),
                str(sshpath),
                str(SUDOERS),
            ]
        )
        run(["systemctl", "reload", "sshd"])
        run(["loginctl", "enable-linger", "hermes"])
        run(["systemctl", "start", f"user@{account.pw_uid}.service"])
        # A failed first bootstrap may have selected an older receiver before
        # any application existed. Private recovery selects the now-validated
        # receiver only in that unactivated state; active releases keep theirs.
        if not (STATE / "current.json").exists():
            receivers.select(receiver)
    return {
        "status": "BOOTSTRAPPED",
        "commissioning": "REQUIRED",
        "host_sha256": digest(config),
        "receiver": receiver,
    }


def backup(backend):
    current = backend.current()
    require(current, "no-current-release")
    _, manifest = backend.release(current)
    receiver = receivers.for_release(manifest)
    password = regular(backend.config["restic_password_file"], owner=0, private=True)
    from uuid import uuid4

    backend.stop()
    try:
        snapshot = backend.snapshot(uuid4().hex, current)
        env = {
            "RESTIC_REPOSITORY": backend.config["restic_repository"],
            "RESTIC_PASSWORD_FILE": str(password),
            "HOME": "/root",
        }
        result = run(
            [
                "restic",
                "--json",
                "-o",
                "sftp.args=-oBatchMode=yes -oStrictHostKeyChecking=yes",
                "backup",
                "--tag",
                "hermes-production",
                str(backend.state / "backups" / snapshot),
                str(backend.state / "releases" / current),
                str(receiver),
            ],
            env=env,
            timeout=7200,
        )
        summaries = [decode(line) for line in result.stdout.splitlines()]
        summaries = [row for row in summaries if row.get("message_type") == "summary"]
        require(
            len(summaries) == 1 and summaries[0].get("snapshot_id"), "restic-snapshot-not-confirmed"
        )
        receipt = {
            "status": "PASS",
            "release": current,
            "restic_snapshot": summaries[0]["snapshot_id"],
        }
        atomic(backend.state / "backups" / snapshot / "offhost.json", canonical(receipt))
        return receipt
    finally:
        backend.restart_previous(current)


def store_credentials(data):
    """Write the gateway environment owner-only; keep any existing mapped owner."""
    account = preflight.account(required=True)
    directory = HOME / "gateway-state"
    if not directory.exists() and not directory.is_symlink():
        directory.mkdir(mode=0o700)
        os.chown(directory, account.pw_uid, account.pw_gid)
        os.chmod(directory, 0o700)
    info = directory.lstat()
    require(
        stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700,
        "unsafe-gateway-state-directory",
    )
    target = directory / ".env"
    if target.exists() or target.is_symlink():
        current = regular(target, private=True).lstat()
        owner = (current.st_uid, current.st_gid)
    else:
        owner = (account.pw_uid, account.pw_gid)
    atomic(target, data, 0o600)
    os.chown(target, *owner)
    credentials(target)


def provision_credentials(config, stream, *, apply):
    """Bounded stdin document -> gateway .env. Values are never echoed or logged."""
    require(config["application_mode"] == "production", "credentials-require-production-mode")
    data = stream.read(16385)
    require(len(data) <= 16384, "credential-file-too-large")
    try:
        credential_text(data.decode())
    except UnicodeDecodeError as exc:
        raise Refused("invalid-credential-file") from exc
    if not apply:
        return {"status": "PREVIEW", "operation": "credentials", "document": "VALID"}
    report = preflight.collect(config, commissioned=False, installed=True, capacity=False)
    require(report["status"] == "PASS", "credentials-preflight-failed")
    with lock(STATE / "operation.lock"), ExitStack() as stack:
        backend = Backend(config)
        current = backend.current()
        if not current:
            store_credentials(data)
            return {"status": "STORED", "restarted": False}
        stack.enter_context(startup.operation())
        run(["systemctl", "start", f"user@{backend.uid}.service"])
        backend.initialize_namespace()
        Transaction(STATE, backend).recover()
        backend.stop()
        stored = HOME / "gateway-state/.env"
        previous = regular(stored, private=True).read_bytes() if stored.exists() else None
        try:
            store_credentials(data)
            # Re-apply the contract (harden-config merges the disabled-feature switches
            # into the stored environment). Never start the gateway without them.
            backend.configure(current)
        except BaseException:
            if previous is not None:
                owner = stored.lstat()
                atomic(stored, previous, 0o600)
                os.chown(stored, owner.st_uid, owner.st_gid)
            raise
        finally:
            backend.restart_previous(current)
        backend.verify(current)
        return {"status": "STORED", "restarted": True, "release": current}


def dispatch(stream):
    require(os.geteuid() == 0, "installed-root-dispatcher-required")
    config = preflight.configuration(read_json(preflight.CONFIG, owner=0))
    raw = stream.readline(4097)
    require(len(raw) <= 4096 and raw.endswith(b"\n"), "invalid-request-header")
    request = decode(raw)
    require(
        isinstance(request, dict)
        and set(request) == {"operation", "apply"}
        and request["operation"] in OPERATIONS | BODY_OPERATIONS
        and type(request["apply"]) is bool,
        "operation-not-permitted",
    )
    operation = request["operation"]
    if operation == "preflight":
        return preflight.collect(config)
    if operation == "backup":
        require(config["restic_repository"] != "none", "backup-not-configured")
    if operation == "attest":
        # Runs before commissioning is complete; the code itself is the proof.
        require(request["apply"], "attestation-requires-apply")
        body = stream.readline(4097)
        require(len(body) <= 4096 and body.endswith(b"\n"), "invalid-request-body")
        from . import commission

        with lock(STATE / "operation.lock"):
            return commission.attest(config, decode(body))
    if operation == "credentials":
        return provision_credentials(config, stream, apply=request["apply"])
    report = preflight.enforce(
        config, installed=True, capacity=operation in ("deploy", "upgrade", "backup")
    )
    if operation == "status":
        return {
            "status": "PASS",
            "preflight": report,
            "current": read_json(STATE / "current.json", owner=0)
            if (STATE / "current.json").exists()
            else None,
            "transaction": read_json(STATE / "journal.json", owner=0)
            if (STATE / "journal.json").exists()
            else None,
        }
    if not request["apply"] and operation != "verify":
        return {"status": "PREVIEW", "operation": operation, "host_sha256": digest(config)}
    with lock(STATE / "operation.lock"), ExitStack() as stack:
        backend = Backend(config)
        tx = Transaction(STATE, backend)
        if operation == "verify":
            require(
                not (STATE / "journal.json").exists()
                or read_json(STATE / "journal.json")["stage"]
                in ("committed", "recovered", "aborted"),
                "unfinished-transaction",
            )
            backend.verify(backend.current())
            return {"status": "PASS", "scope": "credential-free-runtime"}
        stack.enter_context(startup.operation())
        # A pending transaction may have blocked the user manager at boot.
        # Its root guard permits recovery now, while application guards stay shut.
        run(["systemctl", "start", f"user@{backend.uid}.service"])
        backend.initialize_namespace()
        if operation == "rollback":
            return tx.rollback()
        if operation == "backup":
            tx.recover()
            return backup(backend)
        if config["application_mode"] == "production":
            credentials(Path("/home/hermes/gateway-state/.env"))
        with tempfile.TemporaryDirectory(prefix="receive-", dir=STATE / "incoming") as directory:
            started = time.monotonic()
            payload = Path(directory) / "release"
            manifest = bundle.unpack(
                stream,
                payload,
                ETC / "allowed_signers",
                production=config["kind"] == "production",
                owner=0,
                max_bytes=config["artifact_budget_bytes"],
            )
            size = sum(row["size"] for row in manifest["files"].values())
            require(size <= config["artifact_budget_bytes"], "release-exceeds-reserved-capacity")
            release = bundle.identity(manifest)
            target = STATE / "releases" / release
            if target.exists():
                backend.release(release)
            else:
                os.rename(payload, target)
                durable_directory(target.parent)
            transfer = time.monotonic() - started
        result = tx.deploy(release, upgrade=operation == "upgrade")
        result["transfer_verification_seconds"] = transfer
        return result
