#!/usr/bin/env python3
"""Generate or verify docs/migration-manifest.txt.

For every file in the reviewed working tree the manifest records:

    dest_sha256 dest_mode source_sha256 source_mode origin state path

* ``origin``  — SOURCE (from a source or companion checkout), FOUNDATION (tracked
  at the migration base commit), AUTHORED (added here with no source counterpart).
* ``state``   — IDENTICAL / REFORMAT / ADAPTED for SOURCE, UNCHANGED / MODIFIED
  for FOUNDATION, ADDED for AUTHORED.
* ``dest_mode`` is the **actual working-tree** executable mode, not the Git index
  mode, so a working-tree chmod is visible. Index/worktree disagreements are
  recorded and re-checked separately.
* ``source_*`` — the source working-tree hash and executable mode, or ``-``.

The header carries a strict, machine-readable identity block (each key appears
exactly once) with:

* the **payload identity** — SHA-256 over sorted
  ``path\\0dest_sha256\\0dest_mode\\n`` lines. This deliberately EXCLUDES the
  manifest itself, so it identifies the payload and is not a hash binding this
  file. The manifest's own SHA-256 is recorded separately in the handoff;
* the base commit, the source/tooling/companion HEADs;
* the recursive dirty-input fingerprint (algorithm ``hermes-dirty-input-v3``),
  which enumerates every changed and untracked file, including deletions and
  index-vs-worktree mode/type changes, with per-input audit lines. Selection is
  independent of Git's ``core.filemode`` setting: tracked inputs whose actual
  mode differs from the index are included even when ``git status`` hides the
  difference;
* the retained **superseded** v2 dirty-input fingerprint (algorithm
  ``hermes-dirty-input-v2``) and **historical** v1 fingerprint (algorithm
  ``v1-changed-paths-with-file-bytes``), kept so the earlier recorded values are
  not silently redefined;
* a reproducible **inventory identity** — SHA-256 over a path-sorted JSON object
  mapping every manifest-excluding destination path to its ``sha256`` and
  ``mode``, serialized with ``indent=2``, ``sort_keys=True`` and a trailing LF.
  ``--inventory`` prints that exact document, so
  ``--inventory | sha256sum`` reproduces the recorded fingerprint;
* a complete inclusion/exclusion inventory over the declared Hermes scope
  (``--report-excluded`` prints the excluded candidates);
* an explicit supersession note for the stale docs/extraction-manifest.txt.

Companion artifacts are mapped to their real repository and source-relative path
by ``COMPANION_SOURCES``; a missing known companion source is a hard error rather
than a silent downgrade to "no source counterpart".

``--verify`` re-checks the destination rows and payload identity, and — when the
source, tooling and companion checkouts are present — parses the identity block
strictly and re-derives every recorded HEAD, dirty-input fingerprint, audit line
and provenance row. Without those checkouts it reports destination-only
verification explicitly instead of claiming a full check.
"""

import argparse
import hashlib
import json
import os
import pathlib
import stat
import subprocess
import sys

DEST_DEFAULT = pathlib.Path(__file__).resolve().parents[1]
WORKSPACE_DEFAULT = DEST_DEFAULT.parent
SOURCE_DEFAULT = WORKSPACE_DEFAULT / "mikrotik"
TOOLBOX_DEFAULT = WORKSPACE_DEFAULT / "dev-toolbox"
COMPANION_DEFAULT = WORKSPACE_DEFAULT / "fedora-virtualization-host"
BASE_COMMIT = "de8fb8ba1ef8729e895e340ff6244232d3d2193e"
REASONS_FILE = "docs/migration-adaptations.txt"
OUTPUT_FILE = "docs/migration-manifest.txt"

GENERATOR_VERSION = "3"
PAYLOAD_ALGORITHM = "sha256-lines(path NUL dest_sha256 NUL dest_mode LF, path-sorted)"
INVENTORY_ALGORITHM = (
    "sha256(json object path -> {sha256, mode}, path-sorted, sort_keys, indent 2, trailing LF)"
)
DIRTY_ALGORITHM = "hermes-dirty-input-v3"
PREVIOUS_DIRTY_ALGORITHM = "hermes-dirty-input-v2"
LEGACY_DIRTY_ALGORITHM = "v1-changed-paths-with-file-bytes"
# Status recorded for a tracked input whose only worktree-versus-index difference
# is an executable-mode change that ``git status`` did not report because
# ``core.filemode`` is false. It is the same porcelain status Git reports for a
# mode-only worktree change when it does trust file modes, so the fingerprint
# does not depend on that setting.
UNREPORTED_MODE_STATUS = " M"

# Destination path -> source-relative path inside the companion checkout.
COMPANION_SOURCES = {
    "docs/reviews/HERMES_MANUAL_OFFLINE_REVIEW.md": "docs/HERMES_MANUAL_OFFLINE_REVIEW.md",
    "docs/reviews/HERMES_MANUAL_CORRECTION_REVIEW.md": "docs/HERMES_MANUAL_CORRECTION_REVIEW.md",
    "docs/reviews/HERMES_MANUAL_CORRECTION_REPRO.py": "docs/HERMES_MANUAL_CORRECTION_REPRO.py",
    "docs/reviews/HERMES_FEDORA44_REVIEW_PROMPT.md": "docs/HERMES_FEDORA44_REVIEW_PROMPT.md",
}

IDENTITY_KEYS = (
    "version",
    "base_commit",
    "payload_algorithm",
    "payload_fingerprint",
    "payload_rows",
    "payload_excludes",
    "inventory_algorithm",
    "inventory_fingerprint",
    "inventory_rows",
    "inventory_excludes",
    "source_root",
    "source_head",
    "source_dirty_algorithm",
    "source_dirty_fingerprint",
    "source_dirty_inputs",
    "source_dirty_files",
    "source_dirty_deletions",
    "source_dirty_mode_or_type_changes",
    "source_dirty_previous_algorithm",
    "source_dirty_previous_fingerprint",
    "source_dirty_historical_algorithm",
    "source_dirty_historical_fingerprint",
    "toolbox_root",
    "toolbox_head",
    "toolbox_dirty_algorithm",
    "toolbox_dirty_fingerprint",
    "toolbox_dirty_inputs",
    "toolbox_dirty_files",
    "toolbox_dirty_deletions",
    "toolbox_dirty_mode_or_type_changes",
    "toolbox_dirty_previous_algorithm",
    "toolbox_dirty_previous_fingerprint",
    "toolbox_dirty_historical_algorithm",
    "toolbox_dirty_historical_fingerprint",
    "companion_root",
    "companion_head",
    "destination_mode_policy",
    "destination_index_mode_mismatches",
)

# The declared Hermes scope. A source file matching any of these is a candidate
# that must appear either in the manifest or in the exclusion inventory.
SCOPE_EXACT = {
    "hermes-deploy.sh",
    "hermes-certify-vm.sh",
    "hermes-remediation-wizard.sh",
    "hermes-simple-deploy.sh",
    "hermes-fedora-server-install-guide.html",
    "secure-hermes-installation-plan.html",
    "setup-ssh-key-only.sh",
    "setup-ssh-key-only.md",
    ".shellspec",
}
SCOPE_TESTS = (
    "tests/test-hermes-",
    "tests/test_hermes_",
    "tests/test_remaining_preflight.py",
    "tests/test_ssh_key_only.py",
    "tests/check_ssh_key_only_docs.py",
    "tests/lib-test-helpers.sh",
    "tests/Containerfile.e2e",
    "tests/Containerfile.sshd",
)
SCOPE_DOCS_EXACT = {
    "docs/VM_TESTING_GUIDE.md",
    "docs/plans/2026-09-12-fedora-ssh-key-only.md",
}
SCOPE_ROOT_GLOBS = (
    "devbox.json",
    "devbox.lock",
    ".mcp.json",
    ".claude/settings.local.json",
    "lefthook.yml",
)

# Reasons for candidate files that are deliberately not in the destination.
EXCLUSIONS = {
    "devbox.json": "Retired Devbox environment; replaced by the dev-toolbox infra profile",
    "devbox.lock": "Retired Devbox lockfile; replaced by uv.lock and the infra profile",
    ".mcp.json": "Credential-bearing local MCP configuration; never extracted",
    ".claude/settings.local.json": "Credential-bearing local settings; never extracted",
    "AGENTS.md": "Source-repository guidance; this repository authors its own",
    "CLAUDE.md": "Source-repository guidance; this repository authors its own",
    "lefthook.yml": "Lefthook retired; gates ported to .pre-commit-config.yaml",
    ".gitignore": "Destination already has an adopted equivalent",
    ".markdownlint-cli2.yaml": "Destination already has an adopted equivalent",
}


class ManifestError(Exception):
    """Raised when recorded manifest metadata is malformed or inconsistent."""


class CompanionSourceMissing(Exception):
    """Raised when a known companion artifact has no source file."""


def git(repo, *args, binary=True):
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=True
    )
    return result.stdout if binary else result.stdout.decode()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(pathlib.Path(path).read_bytes())


def index_modes(repo):
    """path -> git index mode (100644/100755/120000) from the working tree index."""
    modes = {}
    out = git(repo, "ls-files", "-s", "-z")
    for record in out.split(b"\0"):
        if not record:
            continue
        meta, path = record.split(b"\t", 1)
        mode = meta.split(b" ", 1)[0].decode()
        modes[path.decode()] = mode
    return modes


def base_modes(repo, base):
    modes = {}
    out = git(repo, "ls-tree", "-r", "-z", base)
    for record in out.split(b"\0"):
        if not record:
            continue
        meta, path = record.split(b"\t", 1)
        mode = meta.split(b" ", 1)[0].decode()
        modes[path.decode()] = mode
    return modes


def worktree_files(repo):
    out = git(repo, "ls-files", "-z", "-co", "--exclude-standard")
    return [p for p in out.decode().split("\0") if p]


def filesystem_mode(path):
    """Actual working-tree mode class: 100755/100644/120000/040000."""
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode):
        return "120000"
    if stat.S_ISDIR(info.st_mode):
        return "040000"
    return "100755" if info.st_mode & 0o111 else "100644"


def content_digest(path):
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode):
        return sha256_bytes(os.readlink(path).encode())
    if stat.S_ISREG(info.st_mode):
        return sha256_file(path)
    return "-"


def status_entries(repo):
    """Every dirty entry, with untracked directories expanded recursively."""
    out = git(repo, "status", "--porcelain", "-z", "--untracked-files=all")
    raw = out.split(b"\0")
    entries = []
    index = 0
    while index < len(raw):
        record = raw[index]
        index += 1
        if not record:
            continue
        status = record[:2].decode(errors="replace")
        path = record[3:].decode(errors="replace")
        entries.append({"status": status, "path": path})
        if status[0] in "RC" and index < len(raw):
            # Rename/copy: the original path follows and is a removal input.
            entries.append({"status": status[0] + "-", "path": raw[index].decode(errors="replace")})
            index += 1
    return entries


def tracked_mode_mismatches(repo, modes):
    """Tracked inputs whose index mode differs from the actual filesystem mode.

    ``git status`` does not report a mode-only change when ``core.filemode`` is
    false, so selecting dirty inputs from ``git status`` alone can miss an
    execution-relevant ``chmod`` on an otherwise clean tracked file. This walks
    the index directly instead, independently of that setting. Gitlinks and other
    special entries are skipped; deletions and content-driven type changes are
    already reported by ``git status``.
    """
    mismatches = {}
    for path, index_mode in modes.items():
        if index_mode not in ("100644", "100755", "120000"):
            continue
        candidate = pathlib.Path(repo) / path
        if not (candidate.is_symlink() or candidate.is_file()):
            continue
        worktree_mode = filesystem_mode(candidate)
        if worktree_mode != index_mode:
            mismatches[path] = (index_mode, worktree_mode)
    return mismatches


def dirty_entries(repo, include_unreported_modes=True):
    """Per-input audit records for every changed/untracked path in ``repo``.

    ``include_unreported_modes`` is the v3 behaviour: tracked index/filesystem
    mode differences are included even when ``git status`` hides them. Setting it
    to false reproduces the superseded v2 algorithm exactly.
    """
    modes = index_modes(repo)
    entries = []
    selected = set()
    for item in status_entries(repo):
        path = item["path"]
        selected.add(path)
        candidate = pathlib.Path(repo) / path
        if candidate.is_symlink():
            kind = "symlink"
        elif candidate.is_file():
            kind = "file"
        else:
            kind = "missing"
        if kind == "missing":
            digest, worktree_mode = "-", "-"
        else:
            digest, worktree_mode = content_digest(candidate), filesystem_mode(candidate)
        entries.append(
            {
                "path": path,
                "status": item["status"],
                "kind": kind,
                "index_mode": modes.get(path, "-"),
                "worktree_mode": worktree_mode,
                "digest": digest,
            }
        )
    if include_unreported_modes:
        for path, (index_mode, worktree_mode) in tracked_mode_mismatches(repo, modes).items():
            if path in selected:
                continue
            candidate = pathlib.Path(repo) / path
            kind = "symlink" if candidate.is_symlink() else "file"
            entries.append(
                {
                    "path": path,
                    "status": UNREPORTED_MODE_STATUS,
                    "kind": kind,
                    "index_mode": index_mode,
                    "worktree_mode": worktree_mode,
                    "digest": content_digest(candidate),
                }
            )
    entries.sort(key=lambda entry: entry["path"])
    return entries


def dirty_summary(entries):
    """Fingerprint and accurate counts for a list of dirty-input records.

    Deterministic representation: for each input, sorted by path,
    ``path NUL status NUL kind NUL index_mode NUL worktree_mode NUL content_sha256 LF``.
    Deletions contribute ``kind=missing`` and ``digest=-``; mode and type changes
    contribute differing ``index_mode``/``worktree_mode`` values.
    """
    aggregate = hashlib.sha256()
    for entry in entries:
        fields = ("path", "status", "kind", "index_mode", "worktree_mode", "digest")
        aggregate.update("\0".join(entry[field] for field in fields).encode())
        aggregate.update(b"\n")
    files = sum(1 for entry in entries if entry["kind"] in ("file", "symlink"))
    deletions = sum(1 for entry in entries if entry["kind"] == "missing" or "D" in entry["status"])
    mode_changes = sum(
        1
        for entry in entries
        if entry["index_mode"] != "-"
        and entry["worktree_mode"] != "-"
        and entry["index_mode"] != entry["worktree_mode"]
    )
    return {
        "fingerprint": aggregate.hexdigest(),
        "entries": entries,
        "inputs": len(entries),
        "files": files,
        "deletions": deletions,
        "mode_or_type_changes": mode_changes,
    }


def dirty_identity(repo):
    return dirty_summary(dirty_entries(repo))


def previous_dirty_fingerprint(repo):
    """Superseded v2 algorithm, retained so the earlier value stays auditable.

    v2 selected inputs from ``git status --porcelain -z --untracked-files=all``
    only, so a mode-only change to a clean tracked file was invisible whenever
    ``core.filemode`` was false. It is recorded only as superseded history.
    """
    return dirty_summary(dirty_entries(repo, include_unreported_modes=False))["fingerprint"]


def inventory_document(current):
    """Canonical destination inventory document and its SHA-256.

    ``current`` maps a path to ``(sha256, mode)``. The document is a path-sorted
    JSON object (``sort_keys=True``, ``indent=2``) ending in a single LF, so the
    digest is reproducible with ``--inventory | sha256sum``. The manifest itself
    is excluded because it cannot hash itself; the complete artifact is
    identified by this inventory plus the manifest's separately reported SHA-256.
    """
    document = {
        rel: {"sha256": current[rel][0], "mode": current[rel][1]} for rel in sorted(current)
    }
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    return text, hashlib.sha256(text.encode()).hexdigest()


def legacy_dirty_fingerprint(repo):
    """Historical v1 algorithm, retained verbatim so old identities stay auditable.

    It uses ``git status --porcelain -z`` without ``--untracked-files=all`` (so
    untracked directories collapse and disappear from ``is_file()``) and skips
    deletions. It is recorded only as superseded history.
    """
    out = git(repo, "status", "--porcelain", "-z")
    paths = set()
    entries = out.split(b"\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        status = entry[:2].decode(errors="replace")
        path = entry[3:].decode(errors="replace")
        if status.strip() == "D":
            continue
        paths.add(path)
        if status[0] in "RC" and index < len(entries):
            paths.add(entries[index].decode(errors="replace"))
            index += 1
    aggregate = hashlib.sha256()
    for path in sorted(paths):
        candidate = pathlib.Path(repo) / path
        if not candidate.is_file():
            continue
        aggregate.update(path.encode())
        aggregate.update(b"\0")
        aggregate.update(hashlib.sha256(candidate.read_bytes()).digest())
    return aggregate.hexdigest(), len(paths)


def is_reformat(source_path, dest_path):
    if not str(dest_path).endswith(".sh"):
        return False
    try:
        result = subprocess.run(
            ["shfmt", "-i", "2", "-ci", "-bn"],
            input=pathlib.Path(source_path).read_bytes(),
            capture_output=True,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0 and result.stdout == pathlib.Path(dest_path).read_bytes()


def companion_counterpart(args, rel):
    """(sha256, mode, path) for a declared companion artifact.

    A missing known companion source raises instead of becoming "no source".
    """
    src_rel = COMPANION_SOURCES[rel]
    candidate = pathlib.Path(args.companion) / src_rel
    if not candidate.is_file():
        raise CompanionSourceMissing(
            f"{rel}: known companion source {src_rel} not found under {args.companion}"
        )
    return sha256_file(candidate), filesystem_mode(candidate), candidate


def source_counterpart(args, rel):
    """(sha256, mode, path) for the mikrotik source of ``rel``, or None."""
    candidate = pathlib.Path(args.source) / rel
    if not candidate.is_file():
        return None
    return sha256_file(candidate), filesystem_mode(candidate), candidate


def source_state(rel, counterpart, dest_hash, dest_mode, dest_path, reasons, problems):
    """Classify a SOURCE row whose counterpart is ``counterpart``."""
    src_hash, src_mode, src_path = counterpart
    if src_hash == dest_hash:
        if src_mode == dest_mode:
            return "IDENTICAL"
        if rel not in reasons:
            problems.append(f"{rel}: mode-only adaptation needs a reason")
        return "ADAPTED"
    if is_reformat(src_path, dest_path):
        return "REFORMAT"
    if rel not in reasons:
        problems.append(f"{rel}: SOURCE/ADAPTED needs a reason")
    return "ADAPTED"


def load_reasons(dest):
    reasons = {}
    path = dest / REASONS_FILE
    if not path.is_file():
        return reasons
    for number, raw in enumerate(path.read_text().splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" not in line:
            raise SystemExit(f"{REASONS_FILE}:{number}: expected 'path<TAB>reason'")
        rel, reason = line.split("\t", 1)
        reasons[rel.strip()] = reason.strip()
    return reasons


def exclusion_reason(rel):
    if rel in EXCLUSIONS:
        return EXCLUSIONS[rel]
    if rel.startswith("docs/plans/evidence/"):
        return "Network/VLAN or other non-Hermes evidence; outside the Hermes scope"
    if rel.startswith("docs/archive/"):
        return "Non-Hermes archive material; outside the Hermes scope"
    return "Excluded by the approved Hermes scope; unrelated to this repository"


def in_scope(rel):
    if rel in SCOPE_EXACT:
        return True
    if rel.startswith(("scripts/hermes/", "spec/", "vm/")):
        return True
    if rel.startswith(SCOPE_TESTS):
        return True
    if rel in SCOPE_DOCS_EXACT:
        return True
    if rel.startswith("docs/HERMES_") or rel.startswith("docs/plans/evidence/"):
        return True
    if rel.startswith("docs/archive/"):
        return "hermes" in rel.lower()
    if rel.startswith("docs/plans/") and "hermes" in rel:
        return True
    if rel.startswith("docs/") and ("TPM" in rel or "SELINUX" in rel):
        return True
    return rel in SCOPE_ROOT_GLOBS


def destination_state(dest):
    """Destination rows (filesystem modes), payload identity and mode audit.

    Returns ``(current, payload_fingerprint, index_mode_mismatches, missing)``.
    """
    index = index_modes(dest)
    current = {}
    mismatches = []
    missing = []
    for rel in worktree_files(dest):
        if rel == OUTPUT_FILE:
            continue
        path = dest / rel
        if path.is_symlink() or path.is_file():
            mode = filesystem_mode(path)
            current[rel] = (content_digest(path), mode)
            index_mode = index.get(rel)
            if index_mode is not None and index_mode != mode:
                mismatches.append((rel, index_mode, mode))
        else:
            missing.append(rel)
            current[rel] = ("-", "-")
    mismatches.sort()
    aggregate = hashlib.sha256()
    for rel in sorted(current):
        dest_hash, dest_mode = current[rel]
        aggregate.update(f"{rel}\0{dest_hash}\0{dest_mode}\n".encode())
    return current, aggregate.hexdigest(), mismatches, missing


def dirty_audit_lines(name, entries):
    return [
        "\t".join(
            [
                "# dirty",
                name,
                entry["path"],
                entry["status"],
                entry["kind"],
                entry["index_mode"],
                entry["worktree_mode"],
                entry["digest"],
            ]
        )
        for entry in entries
    ]


def environment_identity(args, mismatches):
    source_entries = dirty_entries(args.source)
    source = dirty_summary(source_entries)
    source_legacy = legacy_dirty_fingerprint(args.source)
    toolbox_entries = dirty_entries(args.toolbox)
    toolbox = dirty_summary(toolbox_entries)
    toolbox_legacy = legacy_dirty_fingerprint(args.toolbox)
    identity = {
        "version": GENERATOR_VERSION,
        "base_commit": BASE_COMMIT,
        "payload_algorithm": PAYLOAD_ALGORITHM,
        "payload_fingerprint": "",
        "payload_rows": "",
        "payload_excludes": OUTPUT_FILE,
        "inventory_algorithm": INVENTORY_ALGORITHM,
        "inventory_fingerprint": "",
        "inventory_rows": "",
        "inventory_excludes": OUTPUT_FILE,
        "source_root": str(args.source),
        "source_head": git(args.source, "rev-parse", "HEAD", binary=False).strip(),
        "source_dirty_algorithm": DIRTY_ALGORITHM,
        "source_dirty_fingerprint": source["fingerprint"],
        "source_dirty_inputs": str(source["inputs"]),
        "source_dirty_files": str(source["files"]),
        "source_dirty_deletions": str(source["deletions"]),
        "source_dirty_mode_or_type_changes": str(source["mode_or_type_changes"]),
        "source_dirty_previous_algorithm": PREVIOUS_DIRTY_ALGORITHM,
        "source_dirty_previous_fingerprint": previous_dirty_fingerprint(args.source),
        "source_dirty_historical_algorithm": LEGACY_DIRTY_ALGORITHM,
        "source_dirty_historical_fingerprint": source_legacy[0],
        "toolbox_root": str(args.toolbox),
        "toolbox_head": git(args.toolbox, "rev-parse", "HEAD", binary=False).strip(),
        "toolbox_dirty_algorithm": DIRTY_ALGORITHM,
        "toolbox_dirty_fingerprint": toolbox["fingerprint"],
        "toolbox_dirty_inputs": str(toolbox["inputs"]),
        "toolbox_dirty_files": str(toolbox["files"]),
        "toolbox_dirty_deletions": str(toolbox["deletions"]),
        "toolbox_dirty_mode_or_type_changes": str(toolbox["mode_or_type_changes"]),
        "toolbox_dirty_previous_algorithm": PREVIOUS_DIRTY_ALGORITHM,
        "toolbox_dirty_previous_fingerprint": previous_dirty_fingerprint(args.toolbox),
        "toolbox_dirty_historical_algorithm": LEGACY_DIRTY_ALGORITHM,
        "toolbox_dirty_historical_fingerprint": toolbox_legacy[0],
        "companion_root": str(args.companion),
        "companion_head": git(args.companion, "rev-parse", "HEAD", binary=False).strip(),
        "destination_mode_policy": "filesystem (index modes audited separately)",
        "destination_index_mode_mismatches": str(len(mismatches)),
    }
    audit = dirty_audit_lines("source", source_entries) + dirty_audit_lines("toolbox", toolbox_entries)
    return identity, audit


def classify(args):
    dest, source = args.destination, args.source
    base = base_modes(dest, BASE_COMMIT)
    reasons = load_reasons(dest)

    rows = []
    problems = []
    for rel in worktree_files(dest):
        if rel == OUTPUT_FILE:
            # A manifest cannot record its own hash: writing the row would change
            # the hash it records. It is identified by the payload fingerprint.
            continue
        dest_path = dest / rel
        if not (dest_path.is_symlink() or dest_path.is_file()):
            problems.append(f"{rel}: tracked path is missing from the working tree")
            continue
        dest_hash = content_digest(dest_path)
        dest_mode = filesystem_mode(dest_path)

        companion = None
        if rel in COMPANION_SOURCES:
            try:
                companion = companion_counterpart(args, rel)
            except CompanionSourceMissing as exc:
                problems.append(str(exc))

        counterpart = None
        if companion:
            counterpart = companion
            origin = "SOURCE"
            state = source_state(rel, companion, dest_hash, dest_mode, dest_path, reasons, problems)
        elif rel in base:
            # Foundation files take precedence over a same-named mikrotik file:
            # they were adopted at the migration base, not imported here.
            base_bytes = git(dest, "show", f"{BASE_COMMIT}:{rel}")
            state = (
                "UNCHANGED"
                if (dest_hash == sha256_bytes(base_bytes) and dest_mode == base[rel])
                else "MODIFIED"
            )
            origin = "FOUNDATION"
            if state == "MODIFIED" and rel not in reasons:
                problems.append(f"{rel}: FOUNDATION/MODIFIED needs a reason")
        else:
            counterpart = source_counterpart(args, rel)
            if counterpart:
                origin = "SOURCE"
                state = source_state(
                    rel, counterpart, dest_hash, dest_mode, dest_path, reasons, problems
                )
            else:
                origin, state = "AUTHORED", "ADDED"

        if counterpart:
            src_hash, src_mode = counterpart[0], counterpart[1]
        else:
            src_hash, src_mode = "-", "-"
        rows.append(
            {
                "path": rel,
                "dest_hash": dest_hash,
                "dest_mode": dest_mode,
                "src_hash": src_hash,
                "src_mode": src_mode,
                "origin": origin,
                "state": state,
            }
        )
    rows.sort(key=lambda row: row["path"])

    included = {row["path"] for row in rows}
    excluded = []
    for rel in sorted(worktree_files(source)):
        if not rel or not in_scope(rel):
            continue
        if rel in included:
            continue
        excluded.append((rel, exclusion_reason(rel)))

    payload = hashlib.sha256()
    for row in rows:
        payload.update(f'{row["path"]}\0{row["dest_hash"]}\0{row["dest_mode"]}\n'.encode())

    current, _, mismatches, destination_missing = destination_state(dest)
    for rel in destination_missing:
        problems.append(f"{rel}: tracked path is missing from the working tree")
    identity, audit = environment_identity(args, mismatches)
    inventory_digest = inventory_document(current)[1]
    identity["payload_fingerprint"] = payload.hexdigest()
    identity["payload_rows"] = str(len(rows))
    identity["inventory_fingerprint"] = inventory_digest
    identity["inventory_rows"] = str(len(current))

    audit_lines = list(audit)
    audit_lines += [
        "\t".join(["# companion", dest_rel, str(args.companion), src_rel])
        for dest_rel, src_rel in sorted(COMPANION_SOURCES.items())
    ]
    audit_lines += [
        "\t".join(["# mode-mismatch", rel, index_mode, worktree_mode])
        for rel, index_mode, worktree_mode in mismatches
    ]
    return {
        "rows": rows,
        "excluded": excluded,
        "problems": problems,
        "reasons": reasons,
        "payload_fingerprint": payload.hexdigest(),
        "identity": identity,
        "audit": audit_lines,
        "mismatches": mismatches,
    }


def render(args, result):
    rows = result["rows"]
    excluded = result["excluded"]
    identity = result["identity"]
    counts = {}
    for row in rows:
        counts[(row["origin"], row["state"])] = counts.get((row["origin"], row["state"]), 0) + 1

    lines = [
        "# Migration manifest - Hermes assets migrated into hermes-fedora-host",
        "#",
        "# Generated by toolbox/generate-migration-manifest.py. Verify with:",
        "#   python3 toolbox/generate-migration-manifest.py --verify",
        "#",
        "# Columns: dest_sha256 dest_mode source_sha256 source_mode origin state path",
        "#   origin SOURCE      added from a source or companion checkout",
        "#   origin FOUNDATION  tracked at the migration base commit",
        "#   origin AUTHORED    added in this repository with no source counterpart",
        "#   state  IDENTICAL / REFORMAT / ADAPTED / UNCHANGED / MODIFIED / ADDED",
        "#   dest_mode is the actual working-tree mode; index/worktree disagreements",
        "#   are listed below and in the identity block.",
        "#   '-' in a source column means there is no source counterpart.",
        "#",
        f"# Destination: hermes-fedora-host, base commit {BASE_COMMIT}",
        f"# Source:      {args.source}",
        f"# Tooling:     {args.toolbox}",
        f"# Companion:   {args.companion}",
        "#",
        "# --- identity (machine-readable; each key appears exactly once) ---",
    ]
    for key in IDENTITY_KEYS:
        lines.append(f"# identity\t{key}\t{identity[key]}")
    lines += [
        "# --- end identity ---",
        "#",
        "# Payload identity (manifest-excluding): " + identity["payload_fingerprint"],
        "#   SHA-256 over sorted 'path\\0dest_sha256\\0dest_mode\\n' for every row",
        "#   below. This deliberately EXCLUDES this manifest file, so it identifies",
        "#   the payload and is not a hash binding this file. The manifest's own",
        "#   SHA-256 is recorded separately in the handoff, not here.",
        "#",
        "# Inventory identity (manifest-excluding): " + identity["inventory_fingerprint"],
        "#   Reproducible inventory of the whole destination: SHA-256 over a",
        "#   path-sorted JSON object mapping every path to its sha256 and mode,",
        "#   serialized with sort_keys, indent 2 and a trailing LF. Reproduce it with",
        "#   'python3 toolbox/generate-migration-manifest.py --inventory | sha256sum'.",
        "#   It excludes the manifest for the same self-reference reason as the",
        "#   payload; the full artifact is this inventory plus the manifest's own",
        "#   SHA-256, which is reported separately.",
        "#",
        "# Dirty-input fingerprint algorithm (hermes-dirty-input-v3):",
        "#   git status --porcelain -z --untracked-files=all; for each entry sorted",
        "#   by path: sha256( path \\0 status \\0 kind \\0 index_mode \\0",
        "#   worktree_mode \\0 content_sha256 \\n ). Recursively enumerates untracked",
        "#   files, encodes deletions as kind=missing, and records index-vs-worktree",
        "#   mode/type changes. Selection is independent of core.filemode: a tracked",
        "#   input whose actual mode differs from the index is included even when git",
        "#   status hides it, with the canonical ' M' status. The superseded v2",
        "#   fingerprint ('hermes-dirty-input-v2', status-selected only) and the",
        "#   historical v1 fingerprint ('v1-changed-paths-with-file-bytes', which",
        "#   skipped deletions and collapsed untracked directories) are retained in",
        "#   the identity block so earlier recorded values are not redefined.",
        "#",
        f"# Rows: {len(rows)}; excluded candidates: {len(excluded)}",
        "# This manifest does not list a row for itself (a file cannot record its own",
        "# hash); it is identified by the payload fingerprint above.",
        "#",
        "# Counts by origin/state:",
    ]
    for (origin, state), count in sorted(counts.items()):
        lines.append(f"#   {origin}/{state}: {count}")
    lines += [
        "#",
        "# Superseded record: docs/extraction-manifest.txt is SUPERSEDED by this file",
        "# and is preserved unmodified as historical evidence. It has 153 actual hash",
        "# rows (not the 166 once claimed); two of those rows no longer match the",
        "# destination: the restored correction record and the adapted guide test.",
        "# Use this manifest, not the old one, for completeness and current hashes.",
        "#",
        "# Row-count basis: the old manifest listed only selected source-derived files",
        "# (311 rows). This one records the whole reviewed working tree, so it also",
        "# includes FOUNDATION rows tracked at the base commit and AUTHORED rows added",
        "# here without a source counterpart.",
        "#",
        "# Adapted files and reasons are listed in docs/migration-adaptations.txt.",
        "#",
        "# Dirty-input audit (tab-separated):",
        "#   # dirty <repo> <path> <status> <kind> <index_mode> <worktree_mode> <sha256>",
        "#     status is the git porcelain status; ' M' is also used for a tracked",
        "#     mode-only change that git did not report because core.filemode is false",
        "#   # companion <dest_path> <companion_root> <source_relative_path>",
        "#   # mode-mismatch <path> <index_mode> <worktree_mode>",
    ]
    lines += result["audit"]
    lines += [
        "#",
        "# Excluded Hermes-scope candidates (path<TAB>reason):",
    ]
    for rel, reason in excluded:
        lines.append(f"#   EXCLUDED\t{rel}\t{reason}")
    lines += [
        "#",
        "# --- rows ---",
    ]
    for row in rows:
        lines.append(
            f'{row["dest_hash"]} {row["dest_mode"]} {row["src_hash"]} {row["src_mode"]} '
            f'{row["origin"]} {row["state"]} {row["path"]}'
        )
    return "\n".join(lines) + "\n"


def parse_manifest(text):
    rows = {}
    for number, line in enumerate(text.splitlines(), start=1):
        if not line or line.startswith("#"):
            continue
        parts = line.split(" ", 6)
        if len(parts) != 7:
            raise ManifestError(f"line {number}: malformed manifest row: {line!r}")
        dest_hash, dest_mode, src_hash, src_mode, origin, state, path = parts
        if path in rows:
            raise ManifestError(f"line {number}: duplicate manifest row for {path}")
        rows[path] = (dest_hash, dest_mode, src_hash, src_mode, origin, state)
    return rows


def parse_identity(text):
    identity = {}
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.startswith("# identity\t"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            raise ManifestError(f"line {number}: malformed identity line: {line!r}")
        key, value = parts[1], parts[2]
        if key not in IDENTITY_KEYS:
            raise ManifestError(f"line {number}: unknown identity key {key!r}")
        if key in identity:
            raise ManifestError(f"line {number}: duplicate identity key {key!r}")
        identity[key] = value
    absent = [key for key in IDENTITY_KEYS if key not in identity]
    if absent:
        raise ManifestError("missing identity keys: " + ", ".join(absent))
    return identity


def mode_mismatch_lines(mismatches):
    return {
        "\t".join(["# mode-mismatch", rel, index_mode, worktree_mode])
        for rel, index_mode, worktree_mode in mismatches
    }


def verify(args):
    manifest_path = args.destination / OUTPUT_FILE
    text = manifest_path.read_text()
    failures = []
    if not text.startswith("# Migration manifest"):
        failures.append("manifest header missing")

    recorded = None
    identity = None
    try:
        recorded = parse_manifest(text)
    except ManifestError as exc:
        failures.append(str(exc))
    try:
        identity = parse_identity(text)
    except ManifestError as exc:
        failures.append(str(exc))

    current, fingerprint, mismatches, missing = destination_state(args.destination)
    for rel in missing:
        failures.append(f"{rel}: tracked path is missing from the working tree")

    if identity is not None:
        if identity.get("version") != GENERATOR_VERSION:
            failures.append(f"identity version {identity.get('version')!r} != {GENERATOR_VERSION!r}")
        if identity.get("payload_algorithm") != PAYLOAD_ALGORITHM:
            failures.append("recorded payload algorithm differs from the implementation")
        if identity.get("payload_fingerprint") != fingerprint:
            failures.append("recorded payload fingerprint differs from the recomputed destination payload")
        if identity.get("payload_rows") != str(len(current)):
            failures.append("recorded payload row count differs from the working tree")
        if identity.get("payload_excludes") != OUTPUT_FILE:
            failures.append("recorded payload exclusion differs from the implementation")
        inventory_digest = inventory_document(current)[1]
        if identity.get("inventory_algorithm") != INVENTORY_ALGORITHM:
            failures.append("recorded inventory algorithm differs from the implementation")
        if identity.get("inventory_fingerprint") != inventory_digest:
            failures.append("recorded inventory fingerprint differs from the recomputed destination inventory")
        if identity.get("inventory_rows") != str(len(current)):
            failures.append("recorded inventory row count differs from the working tree")
        if identity.get("inventory_excludes") != OUTPUT_FILE:
            failures.append("recorded inventory exclusion differs from the implementation")
        if identity.get("base_commit") != BASE_COMMIT:
            failures.append("recorded base commit differs from the implementation")
        if identity.get("destination_index_mode_mismatches") != str(len(mismatches)):
            failures.append("recorded destination index/worktree mode-mismatch count differs")
        recorded_mismatch = {
            line for line in text.splitlines() if line.startswith("# mode-mismatch\t")
        }
        if recorded_mismatch != mode_mismatch_lines(mismatches):
            failures.append("destination index/worktree mode-mismatch audit differs")

    if recorded is not None:
        for path, (dest_hash, dest_mode) in current.items():
            if path not in recorded:
                failures.append(f"{path}: missing from the manifest")
            elif recorded[path][:2] != (dest_hash, dest_mode):
                failures.append(f"{path}: destination hash or mode differs from the manifest")
        for path in recorded:
            if path not in current:
                failures.append(f"{path}: recorded in the manifest but not present in the working tree")

    unavailable = [
        name
        for name, root in (
            ("source", args.source),
            ("toolbox", args.toolbox),
            ("companion", args.companion),
        )
        if not pathlib.Path(root).is_dir()
    ]
    if unavailable:
        print(
            "VERIFY MODE: destination-only (checkout(s) unavailable: "
            + ", ".join(unavailable)
            + "); destination rows, payload identity and mode audit were checked, "
            "but HEAD/dirty-input/provenance identity was NOT re-derived",
            file=sys.stderr,
        )
        return failures

    print("VERIFY MODE: source-aware (source, toolbox and companion checkouts present)", file=sys.stderr)
    result = classify(args)
    failures.extend(result["problems"])
    for key, value in result["identity"].items():
        recorded_value = None if identity is None else identity.get(key)
        if recorded_value != value:
            failures.append(f"identity {key}: recorded {recorded_value!r} != recomputed {value!r}")
    recorded_dirty = {line for line in text.splitlines() if line.startswith("# dirty\t")}
    recomputed_dirty = {line for line in result["audit"] if line.startswith("# dirty\t")}
    if recorded_dirty != recomputed_dirty:
        failures.append("dirty-input audit lines differ from the recomputed inputs")
    recorded_companion = {line for line in text.splitlines() if line.startswith("# companion\t")}
    recomputed_companion = {line for line in result["audit"] if line.startswith("# companion\t")}
    if recorded_companion != recomputed_companion:
        failures.append("companion origin map differs from the recomputed mapping")
    if result["payload_fingerprint"] != fingerprint:
        failures.append("source-aware payload fingerprint differs from the destination fingerprint")
    recomputed = {
        row["path"]: (
            row["dest_hash"],
            row["dest_mode"],
            row["src_hash"],
            row["src_mode"],
            row["origin"],
            row["state"],
        )
        for row in result["rows"]
    }
    for path, values in recomputed.items():
        if recorded is not None and path in recorded and recorded[path] != values:
            failures.append(f"{path}: manifest row differs from recomputed provenance")
    for rel, _ in result["excluded"]:
        if f"EXCLUDED\t{rel}\t" not in text:
            failures.append(f"{rel}: excluded candidate missing from the inventory")
    return failures


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--source", type=pathlib.Path, default=SOURCE_DEFAULT)
    parser.add_argument("--destination", type=pathlib.Path, default=DEST_DEFAULT)
    parser.add_argument("--toolbox", type=pathlib.Path, default=TOOLBOX_DEFAULT)
    parser.add_argument("--companion", type=pathlib.Path, default=COMPANION_DEFAULT)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--report-excluded", action="store_true")
    args = parser.parse_args()

    if args.inventory:
        current, _, _, _ = destination_state(args.destination)
        text, digest = inventory_document(current)
        sys.stdout.write(text)
        print(
            f"INVENTORY SHA-256: {digest} ({len(current)} rows; excludes {OUTPUT_FILE})",
            file=sys.stderr,
        )
        return 0

    if args.verify:
        failures = verify(args)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        if failures:
            return 1
        rows = 0
        try:
            rows = len(parse_manifest((args.destination / OUTPUT_FILE).read_text()))
        except ManifestError:
            rows = 0
        print(f"PASS: {OUTPUT_FILE} matches the working tree ({rows} rows)")
        return 0

    for name, root in (
        ("source", args.source),
        ("toolbox", args.toolbox),
        ("companion", args.companion),
    ):
        if not pathlib.Path(root).is_dir():
            print(f"ERROR: {name} checkout not found: {root}", file=sys.stderr)
            return 1

    result = classify(args)
    if args.report_excluded:
        for rel, reason in result["excluded"]:
            print(f"{rel}\t{reason}")
        return 0
    if result["problems"]:
        for problem in result["problems"]:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1
    text = render(args, result)
    (args.destination / OUTPUT_FILE).write_text(text)
    print(
        f"wrote {OUTPUT_FILE}: {len(result['rows'])} rows, "
        f"{len(result['excluded'])} excluded candidates, "
        f"payload fingerprint {result['payload_fingerprint']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
