#!/usr/bin/python3 -I
"""Portable signed Hermes production interface. Mutations preview without --apply."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from production import bundle, host, kickstart, preflight  # noqa: E402
from production.primitives import Refused, canonical, read_json, regular, require  # noqa: E402


def remote(args, *, operation=None, apply=None, body=None):
    require(args.known_hosts and args.identity, "pinned-ssh-inputs-required")
    require(1 <= args.port <= 65535, "invalid-ssh-port")
    import re

    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", args.host), "invalid-ssh-host")
    regular(args.known_hosts)
    regular(args.identity, private=True)
    operation = operation or args.operation
    apply = args.apply if apply is None else apply
    command = [
        "ssh",
        "-p",
        str(args.port),
        "-F",
        "/dev/null",
        "-T",
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "ClearAllForwardings=yes",
        "-o",
        "UserKnownHostsFile=" + str(Path(args.known_hosts).absolute()),
        "-i",
        str(Path(args.identity).absolute()),
        "hermes-deploy@" + args.host,
    ]
    # The remote key's forced command ignores SSH_ORIGINAL_COMMAND. No shell string is sent.
    # Spool output privately to avoid pipe deadlocks while streaming large OCI archives.
    import tempfile

    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
        # Unbuffered stdin: after the server stops reading, closing never re-flushes data.
        with subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=output, stderr=error, bufsize=0
        ) as process:
            try:
                try:
                    process.stdin.write(canonical({"operation": operation, "apply": apply}))
                    if body is not None:
                        process.stdin.write(body)
                    elif operation in ("deploy", "upgrade") and apply:
                        require(args.bundle, "signed-bundle-required")
                        with regular(args.bundle).open("rb") as stream:
                            shutil.copyfileobj(stream, process.stdin, 1024 * 1024)
                    process.stdin.close()
                except BrokenPipeError:
                    # The dispatcher stopped reading: it refused the request, or it already
                    # has the complete archive. Only its own result decides the outcome.
                    pass
                code = process.wait(timeout=7200)
            except BaseException:
                process.kill()
                process.wait()
                raise
        from production.primitives import decode

        output.seek(0)
        text = output.read(1024 * 1024)
        if code == 0:
            return decode(text)
        # A report with status FAIL (such as a failing preflight) is still the answer.
        try:
            report = decode(text) if text.strip() else None
        except Refused:
            report = None
        if isinstance(report, dict) and report.get("status") == "FAIL":
            return report
        # The dispatcher prints only sanitized reason codes after "STOP: ".
        error.seek(0)
        reasons = [
            line[len("STOP: ") :]
            for line in error.read(65536).decode(errors="replace").splitlines()
            if line.startswith("STOP: ")
        ]
        require(False, "remote:" + reasons[-1] if reasons else "remote-operation-failed")


def local(operation, apply, body=b"", bundle_path=None):
    """Installed-host invocation as root through the same dispatcher."""
    import tempfile

    with tempfile.TemporaryFile() as request:
        request.write(canonical({"operation": operation, "apply": apply}))
        request.write(body)
        if operation in ("deploy", "upgrade") and apply:
            require(bundle_path, "signed-bundle-required")
            with regular(bundle_path).open("rb") as stream:
                shutil.copyfileobj(stream, request)
        request.seek(0)
        return host.dispatch(request)


def target(item):
    item.add_argument("--host")
    item.add_argument("--port", type=int, default=22)
    item.add_argument("--known-hosts")
    item.add_argument("--identity", help="Deployment key for the bounded dispatcher")


def body_operation(args, operation, body, apply):
    if args.host:
        return remote(args, operation=operation, apply=apply, body=body)
    return local(operation, apply, body)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    for operation in sorted(host.OPERATIONS):
        item = sub.add_parser(operation)
        item.add_argument("--apply", action="store_true")
        target(item)
        item.add_argument("--bundle")
        item.add_argument(
            "--config", help="Read-only preflight of a proposed local host configuration"
        )
    bootstrap = sub.add_parser("bootstrap")
    bootstrap.add_argument("--config", required=True)
    bootstrap.add_argument("--signers", required=True)
    bootstrap.add_argument("--apply", action="store_true")
    build = sub.add_parser("bundle")
    build.add_argument("--artifacts", required=True)
    build.add_argument("--output", required=True)
    build.add_argument("--signing-key", required=True)
    build.add_argument("--evidence")
    build.add_argument("--apply", action="store_true")
    install = sub.add_parser("kickstart", help="Render the Kickstart only, for review")
    install.add_argument("--settings", required=True)
    install.add_argument("--signers", required=True)
    install.add_argument("--output", required=True)
    install.add_argument("--apply", action="store_true")
    media = sub.add_parser("media", help="Build the unattended installation ISO")
    media.add_argument("--settings", required=True)
    media.add_argument("--signers", required=True)
    media.add_argument("--iso", required=True)
    media.add_argument("--checksum", required=True)
    media.add_argument("--output", required=True)
    media.add_argument("--serial-console", action="store_true")
    media.add_argument("--apply", action="store_true")
    tools = sub.add_parser("media-tools", help="Build the local mkksiso helper image once")
    tools.add_argument("--apply", action="store_true")
    key = sub.add_parser("escrow-key", help="Create the operator escrow key and certificate")
    key.add_argument("--output", required=True)
    key.add_argument("--unencrypted-test-key", action="store_true", help=argparse.SUPPRESS)
    key.add_argument("--apply", action="store_true")
    setup = sub.add_parser(
        "operator-setup", help="Create production keys and install settings (interactive)"
    )
    setup.add_argument("--output", required=True)
    setup.add_argument("--server", required=True, help="JSON file with the server facts")
    setup.add_argument("--apply", action="store_true")
    pin = sub.add_parser("pin-host", help="Pin the SSH key whose fingerprint the console shows")
    pin.add_argument("--host", required=True)
    pin.add_argument("--port", type=int, default=22)
    pin.add_argument("--fingerprint", required=True)
    pin.add_argument("--known-hosts", required=True)
    pin.add_argument("--apply", action="store_true")
    enroll = sub.add_parser("enroll", help="Fetch, verify and store the installation escrow")
    target(enroll)
    enroll.add_argument("--admin", required=True)
    enroll.add_argument("--admin-identity", required=True)
    enroll.add_argument("--escrow-key", required=True)
    enroll.add_argument("--escrow-out", required=True)
    enroll.add_argument("--apply", action="store_true")
    attest = sub.add_parser("attest", help="Submit a console or power-restoration code")
    target(attest)
    attest.add_argument("--proof", required=True, choices=("console", "power"))
    attest.add_argument("--code", required=True)
    attest.add_argument("--apply", action="store_true")
    secrets_ = sub.add_parser("credentials", help="Send the gateway environment over stdin")
    target(secrets_)
    secrets_.add_argument("--env-file", required=True)
    secrets_.add_argument("--apply", action="store_true")
    opened = sub.add_parser("escrow-open", help="Break-glass: show one escrowed item")
    opened.add_argument("--escrow", required=True)
    opened.add_argument("--escrow-key", required=True)
    opened.add_argument(
        "--item",
        required=True,
        choices=("recovery-key", "admin-password", "restic-password", "luks-header.img"),
    )
    opened.add_argument("--output", help="Required for the binary LUKS header")
    inspect = sub.add_parser("inspect-bundle")
    inspect.add_argument("--bundle", required=True)
    inspect.add_argument("--signers", required=True)
    sub.add_parser("install-commission", help=argparse.SUPPRESS)
    boot = sub.add_parser("commission-boot", help=argparse.SUPPRESS)
    boot.add_argument("--clean-shutdown", action="store_true")
    sub.add_parser("dispatch")
    sub.add_parser("mount-check")
    internal = sub.add_parser("release-action", help=argparse.SUPPRESS)
    internal.add_argument("action", choices=("configure", "verify"))
    internal.add_argument("release")
    restore = sub.add_parser("restore-rehearsal")
    restore.add_argument("--snapshot", required=True)
    restore.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.operation == "release-action":
            require(os.geteuid() == 0, "root-receiver-action-required")
            from production import receivers
            from production.runtime import Backend

            config = preflight.configuration(read_json(preflight.CONFIG, owner=0))
            backend = Backend(config)
            _, manifest = backend.release(args.release)
            require(receivers.running_matches(manifest), "mixed-receiver-execution-refused")
            getattr(backend, args.action)(args.release)
            result = {"status": "PASS"}
        elif args.operation == "dispatch":
            result = host.dispatch(sys.stdin.buffer)
        elif args.operation == "mount-check":
            host.check_mount()
            return 0
        elif args.operation == "bootstrap":
            result = host.bootstrap(args.config, args.signers, apply=args.apply)
        elif args.operation == "install-commission":
            from production import install

            result = install.commission()
        elif args.operation == "commission-boot":
            require(os.geteuid() == 0, "root-commissioning-required")
            from production import commission

            result = commission.clean_shutdown() if args.clean_shutdown else commission.boot()
        elif args.operation == "restore-rehearsal":
            from production.restore import rehearse

            result = rehearse(args.snapshot, apply=args.apply)
        elif args.operation == "bundle":
            result = (
                bundle.build(args.artifacts, args.output, args.signing_key, evidence=args.evidence)
                if args.apply
                else {"status": "PREVIEW", "operation": "sign-retained-artifacts"}
            )
        elif args.operation == "kickstart":
            result = kickstart.write(
                args.settings, args.output, signers=args.signers, apply=args.apply
            )
        elif args.operation == "media":
            from production import media as builder

            result = builder.build(
                args.settings,
                args.signers,
                args.iso,
                args.checksum,
                args.output,
                serial_console=args.serial_console,
                apply=args.apply,
            )
        elif args.operation == "media-tools":
            from production import media as builder

            result = builder.tools(apply=args.apply)
        elif args.operation == "escrow-key":
            from production import escrow

            result = escrow.generate(
                args.output, encrypt=not args.unencrypted_test_key, apply=args.apply
            )
        elif args.operation == "operator-setup":
            from production import client

            result = client.operator_setup(args.output, read_json(args.server), apply=args.apply)
        elif args.operation == "pin-host":
            from production import client

            result = client.pin_host(
                args.host, args.port, args.fingerprint, args.known_hosts, apply=args.apply
            )
        elif args.operation == "enroll":
            from production import client

            require(args.host, "remote-host-required")

            def proof(nonce):
                body = canonical({"proof": "escrow", "code": nonce})
                return remote(args, operation="attest", apply=True, body=body)

            result = client.enroll(
                (args.host, args.port, args.known_hosts),
                args.admin,
                args.admin_identity,
                args.escrow_key,
                args.escrow_out,
                proof,
                apply=args.apply,
            )
        elif args.operation == "attest":
            body = canonical({"proof": args.proof, "code": args.code.strip()})
            result = (
                body_operation(args, "attest", body, True)
                if args.apply
                else {"status": "PREVIEW", "operation": "attest", "proof": args.proof}
            )
        elif args.operation == "credentials":
            from production.runtime import credentials

            credentials(args.env_file, container_managed=False)
            body = regular(args.env_file, private=True).read_bytes()
            result = body_operation(args, "credentials", body, args.apply)
        elif args.operation == "escrow-open":
            from production import escrow

            content = escrow.unseal(args.escrow, args.escrow_key)
            item = content.get(args.item)
            require(item is not None, "item-not-in-escrow")
            if args.item == "luks-header.img":
                require(args.output, "header-output-required")
                out = Path(args.output)
                require(not out.exists() and not out.is_symlink(), "header-output-exists")
                from production.primitives import atomic

                atomic(out, item, 0o600)
                result = {"status": "WRITTEN", "output": str(out)}
            else:
                # Break-glass display goes to a terminal only, never into logs or pipes.
                require(sys.stdout.isatty(), "escrow-item-requires-interactive-terminal")
                print(item.decode())
                return 0
        elif args.operation == "inspect-bundle":
            import tempfile

            with tempfile.TemporaryDirectory(prefix="hermes-inspect-") as directory:
                with regular(args.bundle).open("rb") as stream:
                    result = bundle.unpack(stream, Path(directory) / "payload", args.signers)
        elif args.host:
            require(not args.config, "remote-host-configuration-is-commissioned-locally")
            result = remote(args)
        elif args.operation == "preflight" and args.config:
            result = preflight.collect(
                preflight.configuration(read_json(args.config)), commissioned=False
            )
        else:
            require(not args.config, "use-installed-host-configuration")
            result = local(args.operation, args.apply, bundle_path=args.bundle)
        print(canonical(result).decode(), end="")
        return 1 if result.get("status") == "FAIL" else 0
    except (Exception, KeyboardInterrupt) as exc:
        # Do not print subprocess output, parsed input values, or credential-bearing exceptions.
        message = str(exc) if isinstance(exc, Refused) else type(exc).__name__
        print("STOP: " + message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    os.umask(0o077)
    raise SystemExit(main())
