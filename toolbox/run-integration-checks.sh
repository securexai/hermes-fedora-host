#!/usr/bin/env bash
# Opt-in integration gate. This is NOT part of the pre-push gate and NOT part of
# certification: it drives real host tooling (libguestfs appliance and disk
# work, qemu-img conversion, UKI builds, packaged dracut archive readback, a real
# sshd binary). Run it only under explicit authorization and preferably on a
# disposable host or VM.
#
# Tool availability is not authorization, and a missing prerequisite is NOT a
# pass: if any required tool is absent this script reports NOT RUN and exits 3
# rather than letting skipped tests look green. The list must cover every fixture
# an integration test can skip on, including the OVMF variables template that
# test_hermes_unattended firmware coverage requires.
#
# The shared runner additionally treats any skipped integration test as NOT RUN
# and exits 3, so a prerequisite added here or discovered there cannot be reported
# as a green run.
#
# Usage:
#   toolbox/run-integration-checks.sh
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly SCRIPT_DIR REPO_ROOT

cd "$REPO_ROOT"

missing=()
for command in guestfish qemu-img ukify sbverify mcopy cpio lsinitrd openssl; do
  command -v "$command" >/dev/null 2>&1 || missing+=("$command")
done
[[ -f /usr/lib/dracut/dracut-install ]] || missing+=("/usr/lib/dracut/dracut-install")
[[ -f /usr/sbin/sshd ]] || missing+=("/usr/sbin/sshd")
[[ -f /usr/share/edk2/ovmf/OVMF_VARS.fd ]] || missing+=("/usr/share/edk2/ovmf/OVMF_VARS.fd")
compgen -G '/usr/lib/modules/*/vmlinuz' >/dev/null || missing+=("a test kernel under /usr/lib/modules/*/vmlinuz")

if ((${#missing[@]} > 0)); then
  printf 'NOT RUN: integration prerequisites missing: %s\n' "${missing[*]}" >&2
  printf 'Integration acceptance remains NOT RUN; this is not a pass.\n' >&2
  exit 3
fi

export HERMES_RUN_INTEGRATION_TESTS=1
printf 'Running the opt-in integration set (real host tooling)\n'
python3 -B tests/run-reviewed-suites.py --set integration
