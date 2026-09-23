#!/usr/bin/env python3
"""Run the explicitly reviewed test targets for this repository.

The pre-push gate and the certification gate call this with `--set offline`
(see toolbox/run-offline-checks.sh); the opt-in integration runner calls it with
`--set integration`. Nothing is discovered: every target is read from a reviewed
allowlist file. A `module.Class` target runs every `test*` method in that class
(including methods added later); a `module.Class.method` target pins one method.
A new module or class never runs until it is reviewed and added. A target that
fails to import is reported as an error rather than being skipped.

For `--set integration`, any skipped test means a prerequisite was missing, so
the run reports NOT RUN and exits 3 instead of looking green.
"""

import argparse
import os
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ALLOWLISTS = {
    "offline": HERE / "offline_allowlist.txt",
    "integration": HERE / "integration_allowlist.txt",
}

INTEGRATION_ENV = "HERMES_RUN_INTEGRATION_TESTS"


def load_targets(path):
    targets = []
    for number, raw in enumerate(path.read_text().splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if "." not in line:
            raise SystemExit(f"{path}:{number}: target must be module.Class, got {line!r}")
        targets.append(line)
    if not targets:
        raise SystemExit(f"{path}: no reviewed targets found")
    return targets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", choices=sorted(ALLOWLISTS), default="offline")
    parser.add_argument("--list", action="store_true", help="print resolved targets and exit")
    args = parser.parse_args()

    if args.set == "integration" and os.environ.get(INTEGRATION_ENV) != "1":
        raise SystemExit(
            f"refusing to run the integration set without {INTEGRATION_ENV}=1; "
            "use toolbox/run-integration-checks.sh"
        )

    targets = load_targets(ALLOWLISTS[args.set])
    if args.list:
        print("\n".join(targets))
        return 0

    # The reviewed test modules import sibling test modules by bare name, so the
    # tests directory must be on sys.path (unittest discovery did this before).
    sys.path.insert(0, str(HERE))
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(targets)
    resolved = suite.countTestCases()
    if resolved < len(targets):
        print(
            f"ERROR: {len(targets)} reviewed targets resolved to only {resolved} test cases; "
            "check the allowlist for empty or renamed classes",
            file=sys.stderr,
        )
        return 1

    print(f"Running {resolved} reviewed {args.set} test cases from {len(targets)} explicit targets")
    result = unittest.TextTestRunner(verbosity=1).run(suite)

    if not result.wasSuccessful():
        return 1
    if args.set == "integration" and result.skipped:
        for case, reason in result.skipped:
            print(f"SKIPPED: {case.id()} — {reason}", file=sys.stderr)
        print(
            f"NOT RUN: {len(result.skipped)} integration test(s) skipped for missing "
            "prerequisites; integration acceptance remains NOT RUN and this is not a pass",
            file=sys.stderr,
        )
        return 3
    if result.skipped:
        print(f"WARNING: {len(result.skipped)} offline test(s) skipped", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
