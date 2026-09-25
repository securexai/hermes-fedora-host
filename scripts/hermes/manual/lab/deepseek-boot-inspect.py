#!/usr/bin/env python3
"""Read-only boot inspection of the retained DeepSeek VM through QEMU guest agent.

Run with a private workstation sudo prompt. The fixed guest script reads only
identity, boot and initramfs metadata; it does not request credentials.
"""

import base64
import json
import os
import subprocess
import sys
import time

DOMAIN = "lab-hermes-deepseek-e2e-r1"
UUID = "4349a2bc-67b6-42b7-a6ef-5aeee5ee4009"
MAC = "52:54:00:83:bf:4b"
MACHINE_SHA256 = "f8c01e74f672760c10bdbc91023d98ff5173bb9652da1d6e3d2c4cba00d00682"
VIRSH = ("/usr/bin/virsh", "-c", "qemu:///system")

INSPECT = r"""
set -euo pipefail
printf 'guest_user=%s\n' "$(id -un)"
printf 'guest_hostname=%s\n' "$(cat /etc/hostname)"
printf 'guest_machine_sha256=%s\n' "$(sha256sum /etc/machine-id | cut -d' ' -f1)"
printf 'boot_id=%s\n' "$(cat /proc/sys/kernel/random/boot_id)"
kernel=$(uname -r)
initrd="/boot/initramfs-$kernel.img"
printf 'kernel=%s\ninitrd=%s\n' "$kernel" "$initrd"
test -r "$initrd"
modules=$(lsinitrd -m "$initrd")
for name in systemd-cryptsetup tpm2-tss; do
  if printf '%s\n' "$modules" | tr ' ' '\n' | grep -Fxq "$name"; then
    printf 'module_%s=present\n' "$name"
  else
    printf 'module_%s=missing\n' "$name"
  fi
done
if awk '$1 !~ /^#/ && $4 ~ /(^|,)tpm2-device=auto(,|$)/ { found++ }
        END { exit !(found == 1) }' /etc/crypttab; then
  printf 'crypttab_tpm2=present-on-one-record\n'
else
  printf 'crypttab_tpm2=missing-or-ambiguous\n'
fi
printf 'root_source=%s\n' "$(findmnt -no SOURCE --target /)"
/usr/bin/cryptsetup luksDump --dump-json-metadata /dev/vda3 | python3 -c '
import json, sys
metadata = json.load(sys.stdin)
tokens = [token for token in metadata.get("tokens", {}).values()
          if token.get("type") == "systemd-tpm2"]
print("tpm2_tokens=" + str(len(tokens)))
print("luks2_keyslots=" + str(len(metadata.get("keyslots", {}))))
if len(tokens) == 1:
    token = tokens[0]
    print("tpm2_pcr7_sha256_no_pin=" + str(
        token.get("tpm2-pcrs") == [7]
        and token.get("tpm2-pcr-bank") == "sha256"
        and not token.get("tpm2-salt")
    ).lower())
'
"""


def virsh(*args: str) -> str:
    result = subprocess.run([*VIRSH, *args], check=True, capture_output=True, text=True, timeout=30)
    return result.stdout.strip()


def agent(payload: dict) -> dict:
    response = json.loads(virsh("qemu-agent-command", DOMAIN, json.dumps(payload)))
    if "error" in response or "return" not in response:
        raise RuntimeError("guest agent rejected inspection")
    return response["return"]


def inspect_guest() -> str:
    payload = {
        "execute": "guest-exec",
        "arguments": {
            "path": "/usr/bin/bash",
            "arg": ["-s"],
            "input-data": base64.b64encode(INSPECT.encode()).decode(),
            "capture-output": True,
        },
    }
    pid = agent(payload)["pid"]
    for _ in range(100):
        status = agent({"execute": "guest-exec-status", "arguments": {"pid": pid}})
        if status["exited"]:
            output = base64.b64decode(status.get("out-data", "")).decode(errors="replace")
            if status.get("exitcode") != 0:
                error = base64.b64decode(status.get("err-data", "")).decode(errors="replace")
                raise RuntimeError(
                    f"guest boot inspection failed (exit={status.get('exitcode')}, "
                    f"stderr={error[:500]!r})"
                )
            if len(output) > 4000:
                raise RuntimeError("guest inspection output exceeded bound")
            return output
        time.sleep(0.1)
    raise RuntimeError("guest inspection did not finish within 10 seconds")


def main() -> None:
    if os.geteuid() != 0:
        raise RuntimeError("run as host root with a private sudo prompt")
    if virsh("domuuid", DOMAIN) != UUID:
        raise RuntimeError("VM UUID mismatch")
    interfaces = virsh("domiflist", DOMAIN)
    if not any(
        len(parts := line.split()) >= 5
        and parts[1] == "network"
        and parts[2] == "fvh-nat"
        and parts[4] == MAC
        for line in interfaces.splitlines()
    ):
        raise RuntimeError("VM MAC or network mismatch")
    if virsh("domstate", DOMAIN) != "running":
        raise RuntimeError("VM is not running")
    output = inspect_guest()
    expected = (
        "guest_user=root",
        f"guest_machine_sha256={MACHINE_SHA256}",
    )
    # The Fedora installer left /etc/hostname empty on this VM. Keep the
    # recorded machine ID as the guest pin; reject an unexpected nonempty name.
    hostname = next(
        (line for line in output.splitlines() if line.startswith("guest_hostname=")), None
    )
    if hostname not in ("guest_hostname=", "guest_hostname=lab-hermes-deepseek-e2e-r1") or not all(
        line in output.splitlines() for line in expected
    ):
        observed = ", ".join(
            line
            for line in output.splitlines()
            if line.startswith(("guest_user=", "guest_hostname=", "guest_machine_sha256="))
        )
        raise RuntimeError(f"guest identity mismatch ({observed[:300]})")
    print(output, end="")


if __name__ == "__main__":
    try:
        main()
    except (
        RuntimeError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        KeyError,
        ValueError,
    ) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
