"""Regression controls for the migration provenance generator and verifier.

These tests build an isolated synthetic workspace (four tiny Git repositories)
and drive the real generator through its CLI. They do not read or modify any
sibling repository: every fixture lives in a temporary directory.

The controls exist because an independent re-review demonstrated that the
previous generator/verifier:

* collapsed untracked directories instead of enumerating their files, so the
  two Containerfiles and nested untracked inputs were not fingerprinted;
* skipped deletions entirely, so removing a dirty input changed nothing;
* derived destination modes from the Git index, so a working-tree ``chmod`` was
  invisible;
* never compared the recorded source/tooling HEAD or dirty-input identity, so a
  manifest whose identity metadata had been falsified still verified;
* never populated companion source hashes/modes and silently downgraded a
  missing known companion source to "no source counterpart".

A later independent re-review found that the v2 dirty-input algorithm still
selected inputs from ``git status`` alone, so with ``core.filemode=false`` a
``chmod`` on an otherwise clean tracked input was invisible; these controls now
pin the v3 algorithm, which scans the index independently of that setting.
"""

import contextlib
import importlib.util
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
GENERATOR = REPO_ROOT / "toolbox" / "generate-migration-manifest.py"
MANIFEST_REL = "docs/migration-manifest.txt"

IDENTITY_PREFIX = "# identity\t"
DIRTY_PREFIX = "# dirty\t"


def load_generator():
    spec = importlib.util.spec_from_file_location("migration_manifest_under_test", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def write(path, text, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(mode)


def identity(text, key):
    """Return the single recorded value for an identity key."""
    values = []
    for line in text.splitlines():
        if not line.startswith(IDENTITY_PREFIX):
            continue
        fields = line.split("\t")
        if len(fields) == 3 and fields[1] == key:
            values.append(fields[2])
    if len(values) != 1:
        raise AssertionError(f"expected exactly one identity {key!r}, found {values!r}")
    return values[0]


def identity_keys(text):
    keys = []
    for line in text.splitlines():
        if line.startswith(IDENTITY_PREFIX):
            keys.append(line.split("\t")[1])
    return keys


def dirty_lines(text, repo_name):
    prefix = f"{DIRTY_PREFIX}{repo_name}\t"
    return [line for line in text.splitlines() if line.startswith(prefix)]


class MigrationProvenanceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="hermes-provenance-")
        self.addCleanup(self._tmp.cleanup)
        self.root = pathlib.Path(self._tmp.name)
        self.gen = load_generator()
        self.fixture = self._build_workspace()

    # -- fixture -------------------------------------------------------------

    def _build_workspace(self):
        root = self.root
        dest = root / "hermes-fedora-host"
        source = root / "mikrotik"
        toolbox = root / "dev-toolbox"
        companion = root / "fedora-virtualization-host"
        for repo in (dest, source, toolbox, companion):
            repo.mkdir(parents=True)
            git(repo, "init", "-q")
            git(repo, "config", "user.email", "review@example.invalid")
            git(repo, "config", "user.name", "Review")

        # Destination: a committed base plus untracked additions.
        write(dest / "FOUNDATION.md", "foundation\n")
        write(dest / "tool.sh", "#!/bin/sh\nexit 0\n", 0o755)
        write(dest / "docs/migration-adaptations.txt", "# synthetic fixture\n")
        git(dest, "add", "-A")
        git(dest, "commit", "-qm", "base")
        base = git(dest, "rev-parse", "HEAD").strip()
        write(dest / "AUTHORED.md", "authored here\n")
        write(dest / "docs/reviews/HERMES_MANUAL_OFFLINE_REVIEW.md", "companion review doc\n")

        # Source: one committed, now-dirty in-scope document.
        write(source / "docs/HERMES_A.md", "source A\n")
        git(source, "add", "-A")
        git(source, "commit", "-qm", "source")
        write(source / "docs/HERMES_A.md", "source A dirty\n")

        # Tooling: one modified tracked file plus two untracked nested inputs.
        write(toolbox / "Containerfile", "FROM scratch\n")
        git(toolbox, "add", "-A")
        git(toolbox, "commit", "-qm", "toolbox")
        write(toolbox / "Containerfile", "FROM scratch\n# dirty\n")
        write(toolbox / "profiles/Containerfile.infra", "FROM base\n")
        write(toolbox / "scripts/nested/tool.sh", "#!/bin/sh\nexit 0\n", 0o755)

        # Companion: committed placeholder plus an untracked source document.
        write(companion / "README.md", "companion\n")
        git(companion, "add", "-A")
        git(companion, "commit", "-qm", "companion")
        write(companion / "docs/HERMES_MANUAL_OFFLINE_REVIEW.md", "companion review doc\n")

        return SimpleNamespace(
            root=root,
            dest=dest,
            source=source,
            toolbox=toolbox,
            companion=companion,
            base=base,
            manifest=dest / MANIFEST_REL,
        )

    # -- drivers -------------------------------------------------------------

    def _main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with (
            mock.patch.object(self.gen, "SOURCE_DEFAULT", self.fixture.source),
            mock.patch.object(self.gen, "TOOLBOX_DEFAULT", self.fixture.toolbox),
            mock.patch.object(self.gen, "COMPANION_DEFAULT", self.fixture.companion),
            mock.patch.object(self.gen, "BASE_COMMIT", self.fixture.base),
            mock.patch.object(sys, "argv", ["generate-migration-manifest.py", *argv]),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            code = self.gen.main()
        return code, out.getvalue(), err.getvalue()

    def _generate(self, extra=()):
        code, out, err = self._main(["--destination", str(self.fixture.dest), *extra])
        self.assertEqual(code, 0, f"generation failed: {out}\n{err}")
        return self.fixture.manifest.read_text()

    def _verify(self):
        return self._main(["--destination", str(self.fixture.dest), "--verify"])

    def _assert_verify_fails(self, reason):
        code, out, err = self._verify()
        self.assertNotEqual(code, 0, f"verification unexpectedly passed ({reason})")
        return code, out, err

    # -- positive control ----------------------------------------------------

    def test_generated_manifest_verifies(self):
        self._generate()
        code, out, err = self._verify()
        self.assertEqual(code, 0, f"manifest did not verify: {out}\n{err}")

    # -- R6a: recursive dirty inventory --------------------------------------

    def test_untracked_nested_tooling_inputs_are_enumerated(self):
        text = self._generate()
        paths = {line.split("\t")[2] for line in dirty_lines(text, "toolbox")}
        self.assertIn("profiles/Containerfile.infra", paths)
        self.assertIn("scripts/nested/tool.sh", paths)
        self.assertEqual(identity(text, "toolbox_dirty_inputs"), "3")

    def test_deletions_and_mode_changes_have_deterministic_records(self):
        text = self._generate()
        algorithm = identity(text, "toolbox_dirty_algorithm")
        self.assertIn("v3", algorithm)
        # The superseded v2 value is retained, not silently redefined.
        self.assertEqual(
            identity(text, "toolbox_dirty_previous_algorithm"), "hermes-dirty-input-v2"
        )
        self.assertRegex(identity(text, "toolbox_dirty_previous_fingerprint"), r"^[0-9a-f]{64}$")
        # The header documents the algorithm instead of only naming a digest.
        self.assertIn("untracked-files=all", text)
        self.assertIn("core.filemode", text)

    def test_historical_fingerprint_is_retained_and_labelled(self):
        text = self._generate()
        historical = identity(text, "toolbox_dirty_historical_algorithm")
        current = identity(text, "toolbox_dirty_algorithm")
        self.assertNotEqual(historical, current)
        self.assertRegex(identity(text, "toolbox_dirty_historical_fingerprint"), r"^[0-9a-f]{64}$")

    def test_payload_identity_is_manifest_excluding(self):
        text = self._generate()
        self.assertIn("EXCLUDE", text.upper())
        payload = identity(text, "payload_fingerprint")
        manifest_sha = __import__("hashlib").sha256(self.fixture.manifest.read_bytes()).hexdigest()
        self.assertNotEqual(payload, manifest_sha)
        rows = [line for line in text.splitlines() if line and not line.startswith("#")]
        self.assertEqual(identity(text, "payload_rows"), str(len(rows)))

    # -- R6b: negative controls ----------------------------------------------

    def test_changed_untracked_nested_tooling_input_fails_verification(self):
        self._generate()
        write(self.fixture.toolbox / "scripts/nested/tool.sh", "#!/bin/sh\nexit 1\n", 0o755)
        self._assert_verify_fails("changed untracked nested tooling input")

    def test_tooling_deletion_fails_verification(self):
        self._generate()
        (self.fixture.toolbox / "Containerfile").unlink()
        self._assert_verify_fails("deleted dirty tooling input")

    def test_destination_executable_mode_change_fails_verification(self):
        self._generate()
        (self.fixture.dest / "tool.sh").chmod(0o644)
        self._assert_verify_fails("working-tree chmod on a tracked executable")

    def test_changed_source_head_fails_verification(self):
        self._generate()
        git(self.fixture.source, "commit", "-q", "--allow-empty", "-m", "moved head")
        self._assert_verify_fails("changed source HEAD")

    def test_changed_tooling_dirty_identity_fails_verification(self):
        self._generate()
        write(self.fixture.toolbox / "Containerfile", "FROM scratch\n# changed again\n")
        self._assert_verify_fails("changed tooling dirty-input identity")

    def test_falsified_identity_metadata_fails_verification(self):
        text = self._generate()
        falsified = text.replace(
            f"{IDENTITY_PREFIX}source_head\t{identity(text, 'source_head')}",
            f"{IDENTITY_PREFIX}source_head\t{'0' * 40}",
        )
        self.assertNotEqual(falsified, text)
        self.fixture.manifest.write_text(falsified)
        self._assert_verify_fails("falsified source HEAD metadata")

    def test_missing_identity_field_fails_verification(self):
        text = self._generate()
        removed = "\n".join(
            line for line in text.splitlines() if not line.startswith(f"{IDENTITY_PREFIX}source_head\t")
        )
        self.fixture.manifest.write_text(removed + "\n")
        self._assert_verify_fails("missing identity field")

    def test_duplicated_identity_field_fails_verification(self):
        text = self._generate()
        key = identity(text, "source_head")
        self.fixture.manifest.write_text(text + f"{IDENTITY_PREFIX}source_head\t{key}\n")
        self._assert_verify_fails("duplicated identity field")

    def test_malformed_identity_field_fails_verification(self):
        text = self._generate()
        mutated = "\n".join(
            f"{IDENTITY_PREFIX}source_head"
            if line.startswith(f"{IDENTITY_PREFIX}source_head\t")
            else line
            for line in text.splitlines()
        )
        self.fixture.manifest.write_text(mutated + "\n")
        self._assert_verify_fails("malformed identity field")

    # -- P2-1: mode provenance must not depend on core.filemode ---------------

    def _porcelain_paths(self, repo):
        return {
            line[3:]
            for line in git(repo, "status", "--porcelain").splitlines()
            if line.strip()
        }

    def _commit_clean_executable(self):
        script = self.fixture.toolbox / "clean-mode.sh"
        write(script, "#!/bin/sh\nexit 0\n", 0o755)
        git(self.fixture.toolbox, "add", "clean-mode.sh")
        git(self.fixture.toolbox, "commit", "-qm", "add clean executable")
        return script

    def test_clean_tracked_chmod_is_fingerprinted_when_git_ignores_modes(self):
        script = self._commit_clean_executable()
        git(self.fixture.toolbox, "config", "core.filemode", "false")
        self.assertNotIn(
            "clean-mode.sh", self._porcelain_paths(self.fixture.toolbox)
        )
        self._generate()
        # The chmod target is clean before the mutation: only its mode changes.
        script.chmod(0o644)
        # Git itself still hides the change (this is the reproduced gap) ...
        self.assertNotIn(
            "clean-mode.sh", self._porcelain_paths(self.fixture.toolbox)
        )
        # ... but the v3 selection scans the index, so the input is captured.
        entries = {entry["path"]: entry for entry in self.gen.dirty_entries(self.fixture.toolbox)}
        self.assertIn("clean-mode.sh", entries)
        self.assertEqual(entries["clean-mode.sh"]["status"], " M")
        self.assertEqual(entries["clean-mode.sh"]["index_mode"], "100755")
        self.assertEqual(entries["clean-mode.sh"]["worktree_mode"], "100644")
        # The superseded v2 selection missed exactly this input.
        v2_paths = {
            entry["path"]
            for entry in self.gen.dirty_entries(
                self.fixture.toolbox, include_unreported_modes=False
            )
        }
        self.assertNotIn("clean-mode.sh", v2_paths)
        self.assertNotEqual(
            self.gen.dirty_identity(self.fixture.toolbox)["fingerprint"],
            self.gen.previous_dirty_fingerprint(self.fixture.toolbox),
        )
        self._assert_verify_fails("clean tracked chmod hidden by core.filemode=false")

    def test_dirty_file_chmod_control_still_fails_verification(self):
        # Control: a mode change to an already-dirty file is rejected too, so the
        # new coverage is selection-specific rather than a general mode failure.
        self._generate()
        (self.fixture.toolbox / "Containerfile").chmod(0o755)
        self._assert_verify_fails("working-tree chmod on a dirty tooling input")

    # -- reproducible inventory identity --------------------------------------

    def test_recorded_inventory_fingerprint_is_reproducible(self):
        import hashlib

        text = self._generate()
        code, out, err = self._main(["--destination", str(self.fixture.dest), "--inventory"])
        self.assertEqual(code, 0, err)
        digest = hashlib.sha256(out.encode()).hexdigest()
        self.assertEqual(identity(text, "inventory_fingerprint"), digest)
        self.assertIn(digest, err)
        self.assertEqual(identity(text, "inventory_rows"), str(len(json.loads(out))))

    def test_inventory_fingerprint_change_fails_verification(self):
        text = self._generate()
        mutated = text.replace(
            f"{IDENTITY_PREFIX}inventory_fingerprint\t{identity(text, 'inventory_fingerprint')}",
            f"{IDENTITY_PREFIX}inventory_fingerprint\t{'0' * 64}",
        )
        self.assertNotEqual(mutated, text)
        self.fixture.manifest.write_text(mutated)
        self._assert_verify_fails("falsified inventory fingerprint")

    # -- R6c: companion provenance -------------------------------------------

    def test_companion_source_is_resolved_and_populated(self):
        text = self._generate()
        rows = [
            line
            for line in text.splitlines()
            if line.endswith(" docs/reviews/HERMES_MANUAL_OFFLINE_REVIEW.md")
        ]
        self.assertEqual(len(rows), 1, rows)
        _, _, src_hash, src_mode, origin, state, _ = rows[0].split(" ", 6)
        self.assertEqual(origin, "SOURCE")
        self.assertEqual(state, "IDENTICAL")
        self.assertRegex(src_hash, r"^[0-9a-f]{64}$")
        self.assertEqual(src_mode, "100644")

    def test_missing_known_companion_source_fails_generation(self):
        (self.fixture.companion / "docs/HERMES_MANUAL_OFFLINE_REVIEW.md").unlink()
        code, out, err = self._main(["--destination", str(self.fixture.dest)])
        self.assertNotEqual(code, 0, "generation accepted a missing known companion source")
        self.assertIn("companion", (out + err).lower())

    def test_companion_root_is_configurable(self):
        self._generate(extra=["--companion", str(self.fixture.companion)])
        code, out, err = self._verify()
        self.assertEqual(code, 0, f"{out}\n{err}")

    # -- identity block plumbing ---------------------------------------------

    def test_identity_block_has_no_duplicate_keys(self):
        text = self._generate()
        keys = identity_keys(text)
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn("payload_fingerprint", keys)
        self.assertIn("source_dirty_fingerprint", keys)
        self.assertIn("toolbox_dirty_fingerprint", keys)
