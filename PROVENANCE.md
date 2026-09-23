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
| Dirty-input fingerprint (`hermes-dirty-input-v3`) | `27e1c35fe8d46d2d8c949c13fee0e9c1cda5c164096a7d21734a8519845877f3` (14 inputs, 14 files, 0 deletions, 0 mode/type changes) |
| Superseded v2 dirty-input fingerprint (retained, not redefined) | `27e1c35fe8d46d2d8c949c13fee0e9c1cda5c164096a7d21734a8519845877f3` (identical here: this checkout has no unreported mode change) |
| Historical v1 dirty-input fingerprint (superseded; see algorithm below) | `d7a336b635f13100164a71054f8528f03565fe1100171c02112a5892ed403d87` |
| Fingerprint recorded by §14.8 before its final write | `c82e470c72a6441b03ad91e984e1a611970ffec130bf5f233d1194f0836a925b` |

**Historical v1 fingerprint algorithm** (as defined in the correction record
§10.1 / §13.1): take the sorted, unique set of changed and untracked relative
paths; for each, aggregate `path.encode() + b"\0" + sha256(file_bytes).digest()`
using raw digest bytes (not hexadecimal text); then SHA-256 the concatenation.
That v1 algorithm is retained, clearly labelled, as history: it skipped deletions
and collapsed untracked directories, so it was not a complete dirty-input
identity.

**Superseded v2 fingerprint algorithm** (`hermes-dirty-input-v2`): the v3
algorithm below but *without* the independent index/filesystem mode scan. It
selected inputs from `git status` alone, so a mode-only change to an otherwise
clean tracked file was invisible whenever `core.filemode` was false. Its value is
retained in the manifest and `PROVENANCE.md` so the earlier recorded identity is
not silently redefined.

**Current fingerprint algorithm** (`hermes-dirty-input-v3`, computed by
`toolbox/generate-migration-manifest.py`): from
`git status --porcelain -z --untracked-files=all`, take every entry, sort by path,
and for each aggregate
`path \0 status \0 kind \0 index_mode \0 worktree_mode \0 content_sha256 \n`.
It recursively enumerates untracked files, encodes deletions as `kind=missing`,
and records index-vs-worktree mode/type changes. In addition, it walks the Git
index independently of `core.filemode` and adds every tracked input whose actual
mode differs from the index — with the canonical `" M"` status — so a `chmod` on an
otherwise clean input cannot be hidden by that setting. The manifest records the
v3, the superseded v2 and the historical v1 values.

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

The capture-time repository row above remains historical. The current
checkout is `/var/home/aicloudopspecial/code/repos/dev-toolbox`; the manifest
records that path as `toolbox_root`. Its HEAD and dirty-input fingerprint are
recomputed during source-aware verification.

The two config edits made for this project were subsequently committed in
`dev-toolbox` as `c0f0889` on `codex/toolbox-profiles`. That commit is
**unpushed**: `dev-toolbox` has no remote. The adopted template is therefore
still identified here by file hash rather than by a dev-toolbox commit.

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

## Repository migration (2026-09-21)

The first extraction above covered the reviewed manual profile only. The
**complete repository migration** then brought over the remaining Hermes assets:
the installation and certification entrypoints, the full `scripts/hermes/**`
tree (unattended, SELinux, simple, wrappers), the VM assets and ShellSpec specs,
the guides, and the dated evidence documents.

The authoritative, checkable record of that migration is
[`docs/migration-manifest.txt`](docs/migration-manifest.txt), generated by
`toolbox/generate-migration-manifest.py` and verified with its `--verify` mode.
It records, for every file in the reviewed working tree:

```text
dest_sha256 dest_mode source_sha256 source_mode origin state path
```

with `origin` = SOURCE (from a source or companion checkout) / FOUNDATION (tracked
at the migration base commit) / AUTHORED (added here with no source counterpart),
a `state` per origin, and the source and destination executable modes.
`dest_mode` is the **actual working-tree** mode; index/worktree disagreements are
recorded and re-checked. Every `SOURCE/ADAPTED` and `FOUNDATION/MODIFIED` row has
a reason in [`docs/migration-adaptations.txt`](docs/migration-adaptations.txt).
The four `docs/reviews/**` companion artifacts are mapped to their real
`fedora-virtualization-host` source paths and carry populated source hashes/modes;
The header carries a
strict identity block (each key exactly once) with the source/tooling/companion
HEADs, the current, superseded and historical dirty-input fingerprints with
accurate counts, plus the **payload identity** — SHA-256 over sorted
`path\0dest_sha256\0dest_mode` lines for every row — and a separately recomputable
**inventory identity** (see "Inventory identity" below). Both deliberately EXCLUDE
this manifest, so neither is a hash binding this file; the manifest's own SHA-256
is reported separately in the handoff. The header also carries a complete
inclusion/exclusion inventory over the declared Hermes scope.

Re-verify it with:

```bash
python3 toolbox/generate-migration-manifest.py --verify
```

### Inventory identity (reproducible)

An earlier handoff quoted a 361-file inventory digest
(`79c1cfc44c12d107f0431405563ecb6b2e7930d40795014fea1fdf9f7e1861dc`). That claim
is **withdrawn**: the inventory document and its serialization were not preserved,
and an independent re-review could not reproduce it from any common layout. It is
replaced by two identities that are recorded and recomputed by the manifest
itself:

- **Inventory identity** — `inventory_fingerprint` in the identity block: SHA-256
  over a path-sorted JSON object mapping every manifest-excluding destination path
  to its `sha256` and `mode`, serialized with `sort_keys`, `indent 2` and a
  trailing LF. Reproduce the exact document and digest with:

  ```bash
  python3 toolbox/generate-migration-manifest.py --inventory | sha256sum
  ```

  and compare against `inventory_fingerprint` (the `--inventory` run also prints
  the digest, row count and exclusion on stderr). `--verify` re-checks it.
- **Manifest SHA-256** — reported separately in the handoff, never inside the
  manifest, because a file cannot record its own hash.

The manifest is excluded from the inventory for the same self-reference reason it
is excluded from the payload, so the complete artifact is identified by the
360-row inventory identity **plus** the manifest's separately reported SHA-256.

Key points:

- Source state is unchanged from the extraction above: `mikrotik` at
  `130bf8f2…` with 14 modified tracked files and 0 untracked.
  `hermes-dirty-input-v3` is
  `27e1c35fe8d46d2d8c949c13fee0e9c1cda5c164096a7d21734a8519845877f3` (identical to
  the superseded v2 value, because this checkout has no mode-only change that
  `core.filemode` would hide); the historical v1 value is
  `d7a336b635f13100164a71054f8528f03565fe1100171c02112a5892ed403d87`. The
  reviewed corrections still exist only as that uncommitted working-tree delta.
- The six Hermes evidence artifacts that the first filename-pattern selection
  missed (`2026-09-07-advisory-policy.json`, `guest-candidate.json`,
  `lab-uki-handoff.json`, `privileged-boundary-review.json`,
  `signed-installer-offline.json`, `unattended-offline.json`) are now included
  and appear as manifest rows.
- `docs/extraction-manifest.txt` is **SUPERSEDED** by
  `docs/migration-manifest.txt` and is preserved unmodified as historical
  evidence. It has **153** actual hash rows, not the 166 once claimed; two of
  those rows no longer match the destination (the restored correction record and
  the adapted guide test). Do not treat it as a current-tree assertion.
- `docs/plans/2026-09-20-hermes-manual-review-corrections.md` was restored
  byte-for-byte so its hash again matches the canonical `f838188c…` value.
- Only exact preserved-record paths are excluded from the rewriting hooks and
  the Markdown linter; maintained guides are linted check-only (`fix: false`)
  and are not blanket-excluded. See
  [`.markdownlint-cli2.yaml`](.markdownlint-cli2.yaml).
- Third independent re-review corrections (2026-09-22): the dirty-input algorithm
  is now `hermes-dirty-input-v3`, so mode provenance no longer depends on Git's
  `core.filemode` setting; `toolbox/scan-secrets.sh` prints only fixed
  classifications and numeric counts; and the unreproducible 361-file inventory
  claim is replaced by the recorded inventory identity above. See the
  "Third independent re-review corrections" section of
  [`docs/plans/2026-09-21-hermes-repository-migration.md`](docs/plans/2026-09-21-hermes-repository-migration.md).
- The environment changed from Devbox to the dev-toolbox `infra` profile; see
  [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) for the translation and for which
  documents are preserved records versus current instructions.

### dev-toolbox baseline (dirty-input fingerprint)

The adopted environment standard is still local-only and dirty, so it is
identified by content, not only by commit. The current identity uses the
`hermes-dirty-input-v3` algorithm described above:

| Item | Value |
| --- | --- |
| Repository | `/var/home/aicloudopspecial/code/repos/dev-toolbox` |
| Remote | **none** — local-only |
| Branch | `codex/toolbox-profiles` |
| HEAD | `c0f0889d83531b57167a546e461ceac3f14fa572` |
| Dirty working tree | 22 changed/untracked inputs: 21 files and 1 tracked deletion |
| Dirty-input fingerprint (`hermes-dirty-input-v3`) | `2b8f8cf97ae8c11573c635fa3cb33b8e6c16d38f68cf4ce65c5fa805e84f3315` |
| Superseded v2 fingerprint (retained) | `2b8f8cf97ae8c11573c635fa3cb33b8e6c16d38f68cf4ce65c5fa805e84f3315` (identical here: no mode-only change hidden by `core.filemode`) |
| Historical v1 fingerprint (superseded) | `128c314180d3dfcadb8271dc8d203d9591f02abc98a1e8ec6fcb1aadc7dfed03` (17 recorded paths; collapsed untracked directories and skipped the tracked deletion) |

This fingerprints the dirty `Containerfile`, the `profiles/Containerfile.infra`
and `profiles/Containerfile.python` build inputs, and the nested setup inputs that
the six template hashes above do not cover. `docs/migration-manifest.txt`
recomputes and records the same values, so a drift in the tooling baseline is
detectable.
