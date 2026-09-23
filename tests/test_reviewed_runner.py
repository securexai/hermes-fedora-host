"""Contracts for the reviewed-suite runner and the integration prerequisite gate.

An independent re-review demonstrated that a synthetic integration set whose only
test was skipped still exited 0, so a missing prerequisite could look like a green
integration run. It also showed that class-level allowlist targets automatically
include newly added methods, which the previous documentation denied.
"""

import contextlib
import importlib.util
import io
import os
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
RUNNER = HERE / "run-reviewed-suites.py"
INTEGRATION_SCRIPT = REPO_ROOT / "toolbox" / "run-integration-checks.sh"

SYNTHETIC_MODULE = "synthetic_reviewed_suite"


def load_runner():
    spec = importlib.util.spec_from_file_location("reviewed_runner_under_test", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_synthetic_module():
    module = types.ModuleType(SYNTHETIC_MODULE)

    class Passing(unittest.TestCase):
        def test_ok(self):
            pass

    class Skipped(unittest.TestCase):
        @unittest.skip("synthetic missing prerequisite")
        def test_missing_prerequisite(self):
            pass

    module.Passing = Passing
    module.Skipped = Skipped
    sys.modules[SYNTHETIC_MODULE] = module
    return module


class ReviewedRunnerTests(unittest.TestCase):
    def setUp(self):
        self.runner = load_runner()
        self.module = build_synthetic_module()
        self.addCleanup(sys.modules.pop, SYNTHETIC_MODULE, None)
        self._tmp = tempfile.TemporaryDirectory(prefix="hermes-runner-")
        self.addCleanup(self._tmp.cleanup)
        self.allowlist = pathlib.Path(self._tmp.name) / "integration.txt"

    def _run(self, target, opt_in=True):
        self.allowlist.write_text(f"{target}\n")
        out, err = io.StringIO(), io.StringIO()
        environment = {"HERMES_RUN_INTEGRATION_TESTS": "1"} if opt_in else {}
        with (
            mock.patch.dict(self.runner.ALLOWLISTS, {"integration": self.allowlist}),
            mock.patch.dict(os.environ, environment, clear=False),
            mock.patch.object(sys, "argv", ["run-reviewed-suites.py", "--set", "integration"]),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            if not opt_in:
                os.environ.pop("HERMES_RUN_INTEGRATION_TESTS", None)
            code = self.runner.main()
        return code, out.getvalue(), err.getvalue()

    def test_integration_skips_are_not_success(self):
        code, out, err = self._run(f"{SYNTHETIC_MODULE}.Skipped")
        self.assertNotEqual(code, 0, f"a fully skipped integration set returned {code}")
        self.assertIn("NOT RUN", (out + err).upper())

    def test_integration_passing_suite_returns_zero(self):
        code, out, err = self._run(f"{SYNTHETIC_MODULE}.Passing")
        self.assertEqual(code, 0, f"{out}\n{err}")

    def test_integration_set_requires_opt_in(self):
        with self.assertRaises(SystemExit):
            self._run(f"{SYNTHETIC_MODULE}.Passing", opt_in=False)

    def test_class_target_includes_newly_added_methods(self):
        class Expanded(unittest.TestCase):
            def test_existing(self):
                pass

        self.module.Expanded = Expanded
        before = unittest.TestLoader().loadTestsFromNames(
            [f"{SYNTHETIC_MODULE}.Expanded"]
        ).countTestCases()
        Expanded.test_added_without_allowlist_edit = lambda self: None
        after = unittest.TestLoader().loadTestsFromNames(
            [f"{SYNTHETIC_MODULE}.Expanded"]
        ).countTestCases()
        self.assertEqual((before, after), (1, 2))

    def test_ovmf_prerequisite_is_declared(self):
        text = INTEGRATION_SCRIPT.read_text()
        self.assertIn("/usr/share/edk2/ovmf/OVMF_VARS.fd", text)
