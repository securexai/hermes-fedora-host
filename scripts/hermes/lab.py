#!/usr/bin/env python3
"""Local Hermes lab: preview changes, then explicitly apply to owned disposable VMs."""

from __future__ import annotations

import argparse
import copy
import difflib
import json
import pathlib
import re
import shutil
import statistics
import sys
import time
import uuid
from datetime import datetime, timezone

from lab_profile import ProfileError, digest, file_hash, load, render_unit
from lab_runtime import (
    GUEST,
    ROOT,
    STATE,
    Instance,
    LabError,
    cache_key,
    checked,
    directory,
    lock,
    prepare,
    read_cache,
    source_identity,
    write_json,
)

PROFILES = ROOT / "scripts/hermes/lab-profiles"


def profile_path(name):
    path = pathlib.Path(name)
    return path if path.suffix == ".json" else PROFILES / (name + ".json")


class Report:
    def __init__(self, profile, action):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.path = STATE / "reports" / (stamp + "-" + uuid.uuid4().hex[:8])
        directory(self.path)
        self.data = {
            "version": 1,
            "utc": stamp,
            "action": action,
            "profile": profile,
            "profile_sha256": digest(profile),
            "source": source_identity(),
            "steps": [],
            "live_smoke": "NOT_RUN",
            "production_acceptance": "NOT_RUN",
        }
        self.save()

    def save(self):
        write_json(self.path / "report.json", self.data)

    def step(self, name, function):
        entry = {"name": name, "status": "IN_PROGRESS"}
        self.data["steps"].append(entry)
        self.save()
        started = time.monotonic()
        print(f"STEP={name}", flush=True)
        try:
            result = function()
            entry["status"] = "PASS"
            return result
        except BaseException:
            entry["status"] = "FAIL"
            raise
        finally:
            entry["seconds"] = round(time.monotonic() - started, 3)
            self.save()


def doctor():
    names = (
        "virsh",
        "virt-install",
        "qemu-img",
        "genisoimage",
        "gpg",
        "gpgv",
        "curl",
        "ssh",
        "scp",
        "podman",
        "toolbox",
    )
    missing = [name for name in names if not shutil.which(name)]
    print(
        json.dumps(
            {"missing_tools": missing, "free_gib": round(shutil.disk_usage(ROOT).free / 2**30, 1)},
            sort_keys=True,
        )
    )
    if missing:
        raise LabError("required lab tools are missing")
    checked(["virsh", "--readonly", "-c", "qemu:///session", "list", "--all", "--name"], timeout=30)
    checked(["podman", "info", "--format", "{{.Host.Security.Rootless}}"], timeout=30)
    print("DOCTOR=PASS local tools and session services reachable")


def toolbox(script):
    return checked(
        [
            "toolbox",
            "run",
            "--container",
            "dev-infra-hermes",
            "bash",
            "-c",
            'cd "$1" && bash "$2"',
            "hermes-lab",
            str(ROOT),
            script,
        ]
    )


def quick(profile):
    for name in ("gateway", "worker"):
        template = (ROOT / f"scripts/hermes/manual/quadlets/hermes-{name}.container").read_text()
        render_unit(template, name, profile)
    checked(
        [
            "toolbox",
            "run",
            "--container",
            "dev-infra-hermes",
            "bash",
            "-c",
            'cd "$1" && python3 -B -m unittest tests.test_hermes_lab tests.test_hermes_disposable',
            "hermes-lab",
            str(ROOT),
        ]
    )
    result = checked(
        [
            "podman",
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--env",
            "DEEPSEEK_API_KEY=",
            "--env",
            "TELEGRAM_BOT_TOKEN=",
            "--env",
            f"HERMES_LAB_MODEL={profile['model']}",
            "--volume",
            f"{ROOT / 'tests/hermes-synthetic-smoke.py'}:/run/hermes-synthetic-smoke.py:ro,Z",
            "--entrypoint",
            "/opt/hermes/.venv/bin/python3",
            profile["gateway_image"],
            "/run/hermes-synthetic-smoke.py",
        ]
    )
    if "PASS:" not in result.stdout:
        raise LabError("synthetic smoke did not report acceptance")


def runtime_images(instance):
    return instance.vm.guest(
        "sudo -n python3 -c \"import sys;sys.path.insert(0,'/opt/hermes-deploy/scripts/hermes');import lab_guest;print(lab_guest.deploy.podman('ps','--format','{{.ID}}').stdout)\""
    ).stdout.split()


def verify_vm(instance, manifest, report):
    identity = instance.identities()
    containers = runtime_images(instance)
    report.step("unchanged-deploy", lambda: instance.deploy(manifest))
    if instance.identities() != identity or runtime_images(instance) != containers:
        raise LabError("no-op deploy changed identities or restarted containers")
    varied = copy.deepcopy(instance.profile)
    varied["gateway"]["pids_limit"] += -1 if varied["gateway"]["pids_limit"] == 4096 else 1
    alternate = Instance(instance.name, varied)
    report.step("configuration-change", lambda: alternate.deploy(manifest))
    report.step("configuration-restore", lambda: instance.deploy(manifest))
    report.step("reboot", instance.vm.reboot)
    report.step("worker-recovery", instance.vm.fault_test)
    return identity


def vm_suite(args, profile, report):
    cache, manifest = report.step("prepare", lambda: prepare(profile))
    report.data["artifacts"] = manifest
    identities = []
    readiness = []
    noop = []
    configuration = []
    for _ in range(args.repeat):
        instance = Instance(args.instance, profile)
        with lock("instance-" + instance.name):
            readiness.append(report.step("fresh-prepared-vm", lambda: instance.up(cache, manifest)))
            identities.append(verify_vm(instance, manifest, report))
            noop.append(report.data["steps"][-5]["seconds"])
            configuration.append(report.data["steps"][-4]["seconds"])
            report.step("clean", instance.clean)
            report.step("repeat-clean", instance.clean)
    if any(len({entry[key] for entry in identities}) != len(identities) for key in identities[0]):
        raise LabError("fresh instances reused identities")
    timings = {"ready": readiness, "unchanged": noop, "configuration": configuration}
    report.data["timings"] = {
        key: {"seconds": values, "median": statistics.median(values)}
        for key, values in timings.items()
    }
    report.data["performance"] = (
        "NOT_RUN"
        if args.repeat < 3
        else (
            "PASS"
            if all(
                statistics.median(timings[key]) < limit
                for key, limit in (("ready", 30), ("unchanged", 5), ("configuration", 10))
            )
            else "FAIL"
        )
    )
    report.save()


def download_backup(instance, report):
    result = json.loads(instance.vm.guest(GUEST + "backup").stdout)
    target = report.path / "synthetic-state.tar"
    instance.copy_from("/var/tmp/hermes-lab-state.tar", target)
    target.chmod(0o600)
    instance.vm.guest("rm /var/tmp/hermes-lab-state.tar")
    result["archive_sha256"] = file_hash(target)
    return target, result


def restore_backup(instance, archive, evidence):
    if file_hash(archive) != evidence["archive_sha256"]:
        raise LabError("backup checksum changed")
    if not re.fullmatch(r"[a-f0-9]{64}", evidence["state_sha256"]):
        raise LabError("backup state fingerprint is invalid")
    instance.copy_to(archive, "/var/tmp/hermes-lab-restore.tar")
    restored = json.loads(instance.vm.guest(GUEST + "restore " + evidence["state_sha256"]).stdout)
    if restored["state_sha256"] != evidence["state_sha256"]:
        raise LabError("restored content or metadata differs from backup")


def candidate_suite(args, profile, report):
    report.step("repository-offline", lambda: toolbox("toolbox/run-offline-checks.sh"))
    report.step("repository-lint", lambda: toolbox("toolbox/run-check-only-lint.sh"))
    baseline = load(PROFILES / "baseline.json")
    if baseline["vm"] != profile["vm"]:
        raise LabError(
            "upgrade rehearsal requires unchanged VM sizing; use vm suite for sizing variants"
        )
    base_cache, base_manifest = report.step("prepare-baseline", lambda: prepare(baseline))
    cache, manifest = report.step("prepare-candidate", lambda: prepare(profile))
    report.data["artifacts"] = manifest
    report.data["baseline_artifacts"] = base_manifest
    first = Instance(args.instance, baseline)
    restored = Instance(args.instance + "-restore", baseline)
    with lock("instance-" + first.name), lock("instance-" + restored.name):
        if first.exists() or restored.exists():
            raise LabError("candidate rehearsal requires two absent owned instance names")
        report.step(
            "stock-install-baseline", lambda: first.up(base_cache, base_manifest, stock=True)
        )
        first.vm.guest(GUEST + "fixture")
        archive, evidence = report.step(
            "stopped-state-backup", lambda: download_backup(first, report)
        )
        candidate = Instance(first.name, profile)
        report.step("candidate-artifacts", lambda: candidate.install_artifacts(cache, manifest))
        report.step("upgrade", lambda: candidate.deploy(manifest))
        verify_vm(candidate, manifest, report)
        report.step("rollback-stop", lambda: candidate.vm.guest(GUEST + "stop"))
        report.step("rollback-state", lambda: restore_backup(candidate, archive, evidence))
        report.step(
            "rollback-artifacts", lambda: first.install_artifacts(base_cache, base_manifest)
        )
        report.step("rollback-deploy", lambda: first.deploy(base_manifest))
        first.vm.guest(GUEST + "verify-fixture")
        report.step(
            "separate-restore-vm", lambda: restored.up(base_cache, base_manifest, stock=True)
        )
        report.step("isolated-state-restore", lambda: restore_backup(restored, archive, evidence))
        report.step("restored-startup", lambda: restored.deploy(base_manifest))
        restored.vm.guest(GUEST + "verify-fixture")
        for instance in (restored, first):
            report.step("clean-" + instance.name, instance.clean)
            report.step("repeat-clean-" + instance.name, instance.clean)
        archive.unlink()
    # Bundle the exact source and artifacts, excluding identities and state.
    if source_identity() != report.data["source"]:
        raise LabError("source changed during candidate rehearsal; bundle refused")
    bundle = report.path / "candidate"
    directory(bundle)
    write_json(bundle / "profile.json", profile)
    write_json(bundle / "manifest.json", manifest)
    write_json(bundle / "baseline-profile.json", baseline)
    write_json(bundle / "baseline-manifest.json", base_manifest)
    for label, source in (("candidate", cache), ("baseline", base_cache)):
        directory(bundle / label)
        for name in ("gateway.oci", "worker.oci"):
            shutil.copyfile(source / name, bundle / label / name)
    for relative in report.data["source"]:
        target = bundle / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    (bundle / "RECOVERY.md").write_text(
        "# Candidate recovery\n\nSynthetic lab rehearsal passed. This bundle does not authorize production deployment.\n\n"
        "Stop and verify both writers stopped before backup or restore. Restore the matching pre-upgrade state together "
        "with baseline artifacts and profile; never start an old image against upgraded state. "
        "Restore numeric ownership and modes, re-establish SELinux labels, then verify startup, configuration, "
        "worker isolation and application data. See the included lab.py candidate workflow and canonical lab guide.\n\n"
        "Real credentials and production backups are deliberately absent. Exact-candidate live acceptance remains NOT RUN.\n"
    )
    report.data["bundle_sha256"] = {
        str(p.relative_to(bundle)): file_hash(p) for p in sorted(bundle.rglob("*")) if p.is_file()
    }
    report.save()


def failure_reason(exc, instance=None):
    if isinstance(exc, (LabError, ProfileError)):
        return str(exc)
    if type(exc).__name__ == "LabError" and instance is not None:
        reasons = {
            "STOP: effective Hermes configuration differs from the requested profile",
            "STOP: Hermes services are not both active",
            "STOP: gateway-to-worker SSH round trip failed",
            "STOP: running container image differs from the locked artifact",
            "STOP: running container resource limits differ from the profile",
        }
        try:
            result = instance.vm.guest(
                "sudo -n python3 /opt/hermes-deploy/scripts/hermes/profile-deploy.py status",
                check=False,
                timeout=15,
            )
            if result.stderr.strip() in reasons:
                return result.stderr.strip().removeprefix("STOP: ")
        except Exception:
            pass
    return type(exc).__name__


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "doctor",
            "plan",
            "prepare",
            "up",
            "deploy",
            "test",
            "status",
            "clean",
            "live-start",
            "live-status",
            "live-stop",
        ),
    )
    parser.add_argument(
        "--profile",
        help="named JSON profile or JSON file; defaults to recorded instance or candidate",
    )
    parser.add_argument("--instance", default="dev")
    parser.add_argument("--suite", choices=("quick", "vm", "candidate"), default="quick")
    parser.add_argument("--repeat", type=int, choices=range(1, 4), default=1)
    parser.add_argument("--stock", action="store_true", help="up from verified stock Fedora image")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    report = None
    instance = None
    try:
        # Validate name before using it in any path, including read-only previews.
        placeholder = load(PROFILES / "baseline.json")
        instance = Instance(args.instance, placeholder)
        recorded = instance.path / "profile.json"
        profile = (
            load(profile_path(args.profile))
            if args.profile
            else (
                load(recorded)
                if recorded.exists()
                else (
                    placeholder
                    if args.action in ("clean", "status", "doctor")
                    else load(PROFILES / "candidate.json")
                )
            )
        )
        instance = Instance(args.instance, profile)
        if args.action == "doctor":
            doctor()
            return 0
        if (
            args.action == "plan"
            or (
                args.action in ("prepare", "up", "deploy", "clean", "live-start", "live-stop")
                or args.action == "test"
                and args.suite != "quick"
            )
            and not args.apply
        ):
            old = (
                json.dumps(load(recorded), indent=2, sort_keys=True).splitlines()
                if recorded.exists()
                else []
            )
            new = json.dumps(profile, indent=2, sort_keys=True).splitlines()
            print(
                "\n".join(
                    difflib.unified_diff(
                        old, new, fromfile="recorded", tofile="desired", lineterm=""
                    )
                )
            )
            print(
                f"PLAN action={args.action} suite={args.suite} instance={args.instance} cache={cache_key(profile)}; no changes"
            )
            return 0
        if args.action == "live-status":
            if instance.vm.domain_exists():
                instance.vm.assert_identity()
            instance.vm.live_status()
            return 0
        if args.action == "status":
            if recorded.exists() and load(recorded) != profile:
                raise LabError("requested profile differs from the deployed profile; inspect plan")
            if instance.vm.domain_exists():
                instance.vm.assert_identity()
                instance.vm.status()
            else:
                print(
                    "DOMAIN=ABSENT" + (" retained instance files" if instance.path.exists() else "")
                )
            return 0
        report = Report(profile, args.action)
        if args.action == "test":
            report.step("quick", lambda: quick(profile))
            if args.suite == "vm":
                vm_suite(args, profile, report)
            elif args.suite == "candidate":
                candidate_suite(args, profile, report)
        elif args.action == "prepare":
            _, manifest = report.step("prepare", lambda: prepare(profile))
            report.data["artifacts"] = manifest
        else:
            with lock("instance-" + instance.name):
                if args.action in ("live-start", "live-stop"):
                    if not recorded.exists() or load(recorded) != profile:
                        raise LabError("live operation requires the recorded deployed profile")
                    instance.artifacts(json.loads((instance.path / "artifact.json").read_text()))
                    report.step(
                        args.action,
                        instance.vm.live_start
                        if args.action == "live-start"
                        else instance.vm.live_stop,
                    )
                elif args.action == "clean":
                    report.step("clean", instance.clean)
                else:
                    cache, manifest = read_cache(profile)
                    report.data["artifacts"] = manifest
                    if args.action == "up":
                        report.step("up", lambda: instance.up(cache, manifest, stock=args.stock))
                    else:
                        old = instance.path / "artifact.json"
                        if (
                            not old.exists()
                            or json.loads(old.read_text()).get("key") != manifest["key"]
                        ):
                            report.step(
                                "import-artifacts",
                                lambda: instance.install_artifacts(cache, manifest),
                            )
                        report.step("deploy", lambda: instance.deploy(manifest))
        if source_identity() != report.data["source"]:
            raise LabError("source changed during the run; evidence is stale")
        report.data["status"] = "FAIL" if report.data.get("performance") == "FAIL" else "PASS"
        report.save()
        print(f"RESULT={report.data['status']} REPORT={report.path / 'report.json'}")
        return 0 if report.data["status"] == "PASS" else 1
    except (Exception, KeyboardInterrupt) as exc:
        if report:
            report.data["status"] = "FAIL"
            report.save()
            print(f"REPORT={report.path / 'report.json'}")
        reason = failure_reason(exc, instance)
        print(
            f"STOP: {reason}; owned failed instances are retained for inspection", file=sys.stderr
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
