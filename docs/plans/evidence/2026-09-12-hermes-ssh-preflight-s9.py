"""Read-only Hermes SSH preflight. Run once with sudo; prints a sanitized JSON report.

No packages, configuration, keys, firewall rules or service states are changed.
The helper is hash-checked, then its read-only inspections and gated dry run are called.
Authentication prompts are handled by sudo before this program starts.
"""

import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


EXPECTED_HELPER = "4e1d7c302dd27ed6e208b8f100eae2e9aec7f310262f492ec66b6dd01a1d4931"
HELPER = Path("/home/aicowork/setup-ssh-key-only.sh")
ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"}
SETUP = """
source /dev/stdin
config=/etc/ssh/sshd_config
confdir=/etc/ssh/sshd_config.d
crypto=/etc/crypto-policies/back-ends/opensshserver.config
dropin=$confdir/00-local-key-only.conf
sshd=/usr/sbin/sshd
iface=eno1 zone=FedoraServer
"""


def main():
    if os.geteuid() != 0:
        sys.exit("Run this read-only collector with sudo.")
    helper = HELPER.read_bytes()
    digest = hashlib.sha256(helper).hexdigest()
    if digest != EXPECTED_HELPER:
        sys.exit("Helper hash differs from reviewed S9; stop for review.")
    report = {"timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "helper_sha256": digest, "checks": []}

    def run(name, command, source=None, fields=None):
        try:
            result = subprocess.run(command, input=source, text=True, capture_output=True,
                                    timeout=60, env=ENV)
            output = result.stdout
            if fields:
                output = "\n".join(line for line in output.splitlines()
                                   if line.split() and line.split()[0] in fields)
            item = {"name": name, "rc": result.returncode,
                    "stdout": output.strip(), "stderr": result.stderr.strip()}
        except subprocess.TimeoutExpired:
            item = {"name": name, "error": "timeout"}
        report["checks"].append(item)
        return item.get("rc") == 0

    def inspect(name, function):
        return run(name, ["bash", "-c", SETUP + "\n" + function], helper.decode())

    syntax_ok = run("sshd_syntax", ["/usr/sbin/sshd", "-t"])
    run("effective_current_ssh", ["/usr/sbin/sshd", "-T"], fields={
        "pubkeyauthentication", "authenticationmethods", "passwordauthentication",
        "kbdinteractiveauthentication", "permitrootlogin", "port", "authorizedkeysfile", "usepam"})
    overrides_ok = inspect("service_overrides", "inspect_service_overrides")
    environment_ok = inspect("service_environment", "inspect_service_environment")
    config_ok = inspect("supported_ssh_configuration", "inspect_config")
    candidate_ok = False
    if config_ok:
        candidate_ok = inspect("candidate_key_only_configuration", "effective_check candidate")
    else:
        report["checks"].append({"name": "candidate_key_only_configuration",
                                 "blocked": "supported_ssh_configuration failed"})
    firewall_ok = inspect("firewall_compatibility", "firewall_check")
    for path in [Path('/etc/ssh/sshd_config'), *sorted(Path('/etc/ssh/sshd_config.d').glob('*.conf'))]:
        try:
            includes = [line.strip() for line in path.read_text().splitlines()
                        if line.strip().lower().startswith(('include ', 'include='))]
            report['checks'].append({'name': 'include_directives', 'path': str(path), 'includes': includes})
        except OSError as error:
            report['checks'].append({'name': 'include_directives', 'path': str(path), 'error': str(error)})
    run("public_key_fingerprint", ["ssh-keygen", "-lf", "/home/aicowork/id_ed25519_cloudops.pub"])
    run("ssh_path_metadata", ["stat", "-c", "%a %U %G %n", "/home/aicowork",
                              "/home/aicowork/.ssh", "/home/aicowork/.ssh/authorized_keys"])
    run("nm_connection", ["nmcli", "-g", "GENERAL.CON-UUID", "device", "show", "eno1"])
    connection = report['checks'][-1]
    if connection.get('rc') == 0 and connection['stdout']:
        run("nm_zone", ["nmcli", "-g", "connection.zone", "connection", "show", connection['stdout']])
    run("active_zones", ["firewall-cmd", "--get-active-zones"])
    run("default_zone", ["firewall-cmd", "--get-default-zone"])
    for scope in ([], ["--permanent"]):
        for query in (["--get-zone-of-interface=eno1"], ["--zone=FedoraServer", "--list-all"],
                      ["--get-policies"], ["--direct", "--get-all-rules"], ["--info-service=ssh"]):
            run("firewall " + " ".join(scope + query), ["firewall-cmd", *scope, *query])
        run("policy_inventory " + " ".join(scope), ["firewall-cmd", *scope, "--get-policies"])
        inventory = report['checks'][-1]
        if inventory.get('rc') == 0:
            for policy in inventory['stdout'].split():
                run("policy_details " + " ".join(scope + [policy]),
                    ["firewall-cmd", *scope, "--policy=" + policy, "--list-all"])
        run("source_zone_inventory " + " ".join(scope), ["firewall-cmd", *scope, "--get-zones"])
        zones = report['checks'][-1]
        if zones.get('rc') == 0:
            for zone in zones['stdout'].split():
                run("zone_sources " + " ".join(scope + [zone]),
                    ["firewall-cmd", *scope, "--zone=" + zone, "--list-sources"])
    if all((syntax_ok, overrides_ok, environment_ok, config_ok, candidate_ok, firewall_ok)):
        inspect("complete_read_only_dry_run",
                "main --user aicowork --public-key-file /home/aicowork/id_ed25519_cloudops.pub "
                "--interface eno1 --zone FedoraServer --dry-run")
    else:
        report['checks'].append({'name': 'complete_read_only_dry_run', 'blocked': 'required preflight check failed'})
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
