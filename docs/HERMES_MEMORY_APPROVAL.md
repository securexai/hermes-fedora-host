# Hermes memory approval

The pinned manual-profile gateway supports memory approval. With
`memory.write_approval: true`, a queued write is **not saved memory** until the
operator approves it. Keep the approval gate enabled.

## Review and apply a write

In an interactive Hermes conversation, use these slash commands:

```text
/memory pending
/memory approve <id>
/memory reject <id>
```

Inspect the proposed content before approving its exact ID. Approve commits it to
`memories/MEMORY.md` or `memories/USER.md`; reject removes the pending request without
committing it. Avoid bulk approval of an unreviewed queue.

These are **interactive slash commands**, not the shell command
`hermes memory pending`. The shell command's smaller help menu does not establish
that interactive approval is unavailable. They do not require a Telegram bot.

Pending records under `pending/memory/` are the review queue. They need not have
a `status` field, and the shipped implementation does not expire them using
`approvals.timeout`. Persistence through a restart is expected for an outstanding
review request. Interactive CLI foreground writes may instead offer an inline
approval prompt; noninteractive/background writes are staged for review.

Do not treat an agent's natural-language confirmation or a tool's `success: true`
alone as proof of persistence: a result with `staged: true` still needs approval.
Approved memories enter the frozen prompt snapshot of a **new session**; start a
new conversation to test recall rather than expecting an existing snapshot to change.

## Access on the retained local VM

Connect with the dedicated key and pinned host key in the
[local VM guide](HERMES_LOCAL_VM.md#identity-and-access). At the guest's `lab` shell,
start an interactive Hermes CLI as its container runtime user:

```bash
sudo -n /usr/bin/bash -c '
  uid=$(id -u hermes)
  sudo -u hermes env --chdir=/home/hermes HOME=/home/hermes \
    XDG_RUNTIME_DIR=/run/user/$uid \
    podman exec -it --user 10000:10000 --workdir /opt/hermes \
    hermes-gateway /opt/hermes/bin/hermes
'
```

Type `/memory pending` inside that conversation. Do not send an approval command
to the model as a natural-language request or disable approval to clear a backlog.
Telegram is now configured on this VM. User-provided screenshots confirm a pending
write, successful exact-ID approval and recall after `/new`. Before approval, a
fresh session did not recall the pending fact. The personal content is omitted
from this record. See [Telegram access](HERMES_LOCAL_VM.md#telegram-access).

## Verification and correction of the earlier diagnosis

On 2026-09-18, the installed gateway digest
`sha256:9469b3e78b9545b6d576eb8887a95352e9a0ea83730eaf31431cf862ca1010e1`
passed isolated tests of the real interactive CLI and gateway slash handlers:

- Unapproved writes were queued without entering committed memory.
- Listing, approving and rejecting exact IDs worked through both handlers.
- Approved content was loaded into a fresh process; rejected content was absent.
- `memory.write_approval` stayed enabled and the synthetic queue was empty afterward.

A separate two-call model test using `openai-api` / `gpt-5.6-luna` reported that its
synthetic write was staged and not yet saved. After explicit approval, a fresh
session returned the exact stored random codeword. The test used a disposable
profile, removed it afterward, and did not modify the live user's memory queue.

The earlier handoff inferred that the queue could not be reviewed from the shell
help menu and the absence of status/expiry metadata. Inspection and these live
tests contradict that inference. Its report of a misleading agent confirmation
is retained as historical evidence; that behavior did **not** reproduce in this
run. This does not guarantee that a model will never misstate a tool result.
No gateway-image patch, version upgrade or approval-policy change was applied.
The [sanitized evidence](plans/evidence/2026-09-18-hermes-memory-approval.json)
binds these checks to the image, shipped source hashes and regression probe.

The reusable [regression probe](../scripts/hermes/manual/gateway/memory-approval-probe.py)
uses the pinned image's existing Python environment and a disposable credential-free
profile; it calls no model or messaging API. Run it from the repository through
pinned SSH, following the same identity options as the local VM guide:

```bash
state=/var/home/aicloudopspecial/.local/state/hermes-local-vm
ssh -i "$state/id_ed25519" -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$state/known_hosts" \
  lab@172.16.99.12 'sudo -n /usr/bin/bash -c '\''
    uid=$(id -u hermes)
    sudo -u hermes env --chdir=/home/hermes HOME=/home/hermes \
      XDG_RUNTIME_DIR=/run/user/$uid \
      podman exec -i --user 10000:10000 --workdir /opt/hermes \
      hermes-gateway /opt/hermes/.venv/bin/python3 -
  '\''' < scripts/hermes/manual/gateway/memory-approval-probe.py
```

Require `MEMORY_APPROVAL_PROBE=PASS` and a zero exit status. The gateway-handler
test does not constitute end-to-end Telegram acceptance.

Upstream describes the same supported review flow in its
[memory documentation](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md).
The findings above are grounded in the installed digest, not an assumption that
upstream `main` and the pinned image are identical.
