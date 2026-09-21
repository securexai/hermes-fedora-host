"""Read-only Hermes SSH preflight. Run once with sudo; prints a sanitized JSON report.

No packages, configuration, keys, firewall rules or service states are changed.
The helper is hash-checked, then only its read-only inspection functions are called.
Authentication prompts are handled by sudo before this program starts.
"""

import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


EXPECTED_HELPER = "06e70bdb99c78d76b6f0de051e5fddce6bb1cd3d8719613ade367918ad1df569"
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
        sys.exit("Helper hash differs from reviewed S7; stop for review.")
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

    run("sshd_syntax", ["/usr/sbin/sshd", "-t"])
    run("effective_current_ssh", ["/usr/sbin/sshd", "-T"], fields={
        "pubkeyauthentication", "authenticationmethods", "passwordauthentication",
        "kbdinteractiveauthentication", "permitrootlogin", "port", "authorizedkeysfile", "usepam"})
    inspect("service_overrides", "inspect_service_overrides")
    inspect("service_environment", "inspect_service_environment")
    if inspect("supported_ssh_configuration", "inspect_config"):
        inspect("candidate_key_only_configuration", "effective_check candidate")
    else:
        report["checks"].append({"name": "candidate_key_only_configuration",
                                 "blocked": "supported_ssh_configuration failed"})
    inspect("firewall_compatibility", "firewall_check")
    run("active_zones", ["firewall-cmd", "--get-active-zones"])
    run("default_zone", ["firewall-cmd", "--get-default-zone"])
    for scope in ([], ["--permanent"]):
        for query in (["--get-zone-of-interface=eno1"], ["--zone=FedoraServer", "--list-all"],
                      ["--get-policies"], ["--direct", "--get-all-rules"], ["--info-service=ssh"]):
            run("firewall " + " ".join(scope + query), ["firewall-cmd", *scope, *query])
        result = subprocess.run(["firewall-cmd", *scope, "--get-policies"],
                                capture_output=True, text=True, timeout=15, env=ENV)
        if result.returncode == 0 and "allow-host-ipv6" in result.stdout.split():
            run("ipv6_policy " + " ".join(scope),
                ["firewall-cmd", *scope, "--policy=allow-host-ipv6", "--list-all"])
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
