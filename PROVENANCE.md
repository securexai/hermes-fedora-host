# Provenance

This file records exactly which source state this repository was derived from, so
that later reviews can tell whether an evidence claim still applies.

## Hermes source (content extracted into this repository)

| Item | Value |
| --- | --- |
| Repository | `/var/home/aicloudopspecial/code/repos/mikrotik` |
| Remote | `git@github.com:securexai/mikrotik.git` |
| Branch | `codex/hermes-fedora44-manual-review` |
| HEAD | `130bf8f2dbdc95e0db25407d5b3b155b627d1473` |
| Working tree at capture | **14 modified tracked files, 0 untracked** — the reviewed corrections exist only as an uncommitted working-tree delta |
| Diffstat | 1400 insertions(+), 109 deletions(-) |
| Dirty-input fingerprint | `d7a336b635f13100164a71054f8528f03565fe1100171c02112a5892ed403d87` |
| Fingerprint recorded by §14.8 before its final write | `c82e470c72a6441b03ad91e984e1a611970ffec130bf5f233d1194f0836a925b` |

**Fingerprint algorithm** (as defined in the correction record §10.1 / §13.1):
take the sorted, unique set of changed and untracked relative paths; for each,
aggregate `path.encode() + b"\0" + sha256(file_bytes).digest()` using raw digest
bytes (not hexadecimal text); then SHA-256 the concatenation.

Because the reviewed corrections are uncommitted, **copying HEAD alone would lose
the F1–F4 corrections**. Extraction must snapshot the working tree.

## Canonical correction record and out-of-tree review evidence

The canonical record lives in the source repository. Its companions live only in
the sibling checkout and are extracted here alongside it.

| Artifact | Location | SHA-256 |
| --- | --- | --- |
| Canonical correction record (§§1–14) | `mikrotik/docs/plans/2026-09-20-hermes-manual-review-corrections.md` | `f838188c228cc7f44db944e6156cc49c3304556f1f265a59967846800a12643f` |
| Independent offline review (R1–R10) | `fedora-virtualization-host/docs/HERMES_MANUAL_OFFLINE_REVIEW.md` | `3f6f17803ab2419737a47e45f5fc27d9da7d70efb43efb5f110a5495fcc1a01a` |
| Independent correction review (C1–C5) | `fedora-virtualization-host/docs/HERMES_MANUAL_CORRECTION_REVIEW.md` | `3c3c0ea0ddb56689e6f2d3090bd20c76dbfdacc47e94f81c9d2d64a35d95293d` |
| Counterexample replay script | `fedora-virtualization-host/docs/HERMES_MANUAL_CORRECTION_REPRO.py` | `47b8e05eb7553fb73e8d2f6e8660af335e6d4741db9af091089e1004b6e31f96` |
| Fedora 44 review prompt | `fedora-virtualization-host/docs/HERMES_FEDORA44_REVIEW_PROMPT.md` | `871b196059a8154faf35a4721e1ea4f75b8f20a62485d8b32348943ded64a62f` |

## Environment standard (dev-toolbox)

| Item | Value |
| --- | --- |
| Repository | `/var/home/aicloudopspecial/code/repos/dev-toolbox` |
| Remote | **none** — local-only, so the standard cannot yet be pinned by a public commit |
| Branch | `codex/toolbox-profiles` |
| HEAD | `151c1b47537f1cbb0f5f478c8b9894040ea985b9` |
| Working tree | dirty: the profile standard itself is uncommitted (10 modified, 1 tracked deletion, 9 untracked, including two uncommitted config edits made for this project) |

Adopted template files and their SHA-256 at capture:

| Template | SHA-256 |
| --- | --- |
| `.pre-commit-config.yaml` | `63a9a53a17d4e34a12da6f27622131c8389e4509ffa8ad2d1a8b406f018abd98` |
| `.betterleaks.toml` | `50d4ddee6d58705854df812e07a23c16434f6d19312a0e84940b50bfc31557d2` |
| `commitlint.config.js` | `c4dd919f9f66fe3082d0a29a1741aa91d33bdd85be8036c83645472a70af5f5d` |
| `.markdownlint-cli2.yaml` | `efb2ca27c3b35c8f1481bdb05b588570031042111cab5e23aaf036111ed04004` |
| `.editorconfig` | `60a78af72fcc2d4d7c862d2983da35fbceb6991ca092a56a7e00727d35d28f2e` |
| `.devcontainer/devcontainer.json` | `750c162c24c07955bf6b8a5b6b7bcc203f4a66df8c96b72d9fcf714426ee9718` |

The two canonical hooks changed for this project (verified in the migration
record, T01): `shellcheck-py` v0.10.0.1 → v0.11.0.1 and `markdownlint-cli2`
v0.18.1 → v0.23.3, plus a check-only `shfmt` gate added to the shipped template.

## Development environment images

| Layer | Image ID |
| --- | --- |
| `localhost/dev-base:fedora-44` | `72f3583d5e076360afef8bf9085f80e595b03f0060021943113c7a9a20755774` |
| `localhost/dev-python:fedora-44` | `965ea02e6072a337a6ded20eefed1b355b414120b51098290721bf196918e519` |
| `localhost/dev-infra:fedora-44` | `af934ead06123ec721bc5b7a6e61fdc27eea5bd82d5cb223703b584e5dedf551` |
| Toolbox container | `dev-infra-hermes`, on `af934ead…` |

The container's RPM manifest has 385 entries; its SHA-256 is
`860b9dfeae6d6d3e2429518b046754d4fb7016e82625117d94d041d03ac01374`.
Derived images pin their parent by exact image ID, so a replaced parent forces a
rebuild. Rebuilding an image does **not** update an existing container.

## Evidence-scope rule

The offline passes recorded in the source correction record apply to the source
artifact fingerprinted above and to the environment it ran in. If any migrated
file changes, the affected pass becomes **STALE for that input**; the original
successful result is retained, not deleted, and the affected check is rerun.
Offline passes never establish deployment acceptance.
