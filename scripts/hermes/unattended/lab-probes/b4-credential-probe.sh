#!/bin/sh
# Disposable, public canary only; included in both B4 probe initrds.
set -eu
umask 077
probe_root=/hermes-lab-b4
probe_run=$(cat "$probe_root/run-id")
case "$probe_run" in
  *[!0-9a-f]* | '') exit 78 ;;
esac
[ "${#probe_run}" -eq 64 ]
[ -c /dev/tpmrm0 ]
[ -s /.extra/tpm2-pcr-signature.json ]
[ -s "$probe_root/canary.cred" ]
[ -x /usr/bin/systemd-creds ]
if /usr/bin/systemd-creds decrypt --name=b4-canary \
  --tpm2-signature=/.extra/tpm2-pcr-signature.json \
  "$probe_root/canary.cred" /dev/null 2>/run/hermes-b4-canary-error; then
  printf 'HERMES_B4_CREDENTIAL_ALLOWED run=%s\n' "$probe_run"
else
  printf 'HERMES_B4_CREDENTIAL_DENIED run=%s\n' "$probe_run"
fi
# Interpretation requires the matching successful control, valid signatures,
# actual negative boot identity and a reviewed crypto-policy failure reason.
