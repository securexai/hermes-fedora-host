#!/usr/bin/env python3
"""Structural check that the Hermes guide gate is actually wired to pre-push.

The previous regression only grepped for the strings `test-hermes-guide` and
`hermes-offline-suites` anywhere in the files. Comments satisfied it, and
changing the hook entry or stage did not remove the searched id, so a green run
did not prove the claimed wiring. This checker parses the hook definition and the
runner instead:

  * exactly one local hook with id ``hermes-offline-suites``
  * its entry is ``bash toolbox/run-offline-checks.sh``
  * it runs at the ``pre-push`` stage, with ``always_run: true`` and
    ``pass_filenames: false``
  * ``toolbox/run-offline-checks.sh`` really invokes
    ``bash tests/test-hermes-guide.sh`` through its ``run`` helper, and invokes
    the reviewed offline Python allowlist runner (not discovery)

``--self-test`` additionally applies known mutations (removed hook, wrong entry,
wrong stage, commented-out invocation, discovery instead of the allowlist) and
requires every one to be rejected, so the checker itself cannot silently rot.

Exit 0 when every required property holds, 1 otherwise.
"""

import argparse
import copy
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

HOOK_ID = "hermes-offline-suites"
EXPECTED_ENTRY = "bash toolbox/run-offline-checks.sh"
EXPECTED_STAGES = ["pre-push"]
GUIDE_RUN = re.compile(r'^\s*run\s+"[^"]*"\s+bash\s+tests/test-hermes-guide\.sh\s*$', re.MULTILINE)
ALLOWLIST_RUN = re.compile(
    r'^\s*run\s+"[^"]*"\s+python3\s+-B\s+tests/run-reviewed-suites\.py\s+--set\s+offline\s*$',
    re.MULTILINE,
)


def load_yaml(path):
    try:
        import yaml
    except ImportError:  # pragma: no cover - environment guard
        raise SystemExit("PyYAML is required for the hook-wiring check (dev-toolbox infra profile)")
    with open(path, encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def find_hooks(document):
    hooks = []
    for repository in document.get("repos", []) or []:
        for hook in repository.get("hooks", []) or []:
            hooks.append(hook)
    return hooks


def check(precommit_path, offline_path):
    """Return a list of human-readable failures (empty means wired correctly)."""
    document = load_yaml(precommit_path)
    offline = pathlib.Path(offline_path).read_text(encoding="utf-8")
    return check_from_data(document, offline)


def mutations(document, offline):
    """Yield (label, mutated_document, mutated_offline) negative controls."""
    def with_hook(mutate):
        changed = copy.deepcopy(document)
        for repository in changed.get("repos", []) or []:
            for hook in repository.get("hooks", []) or []:
                if hook.get("id") == HOOK_ID:
                    mutate(hook)
        return changed

    removed = copy.deepcopy(document)
    for repository in removed.get("repos", []) or []:
        repository["hooks"] = [h for h in repository.get("hooks", []) or [] if h.get("id") != HOOK_ID]
    yield "hook removed", removed, offline
    yield "wrong entry", with_hook(lambda h: h.__setitem__("entry", "bash tests/test-hermes-guide.sh")), offline
    yield "wrong stage", with_hook(lambda h: h.__setitem__("stages", ["pre-commit"])), offline
    yield "always_run disabled", with_hook(lambda h: h.__setitem__("always_run", False)), offline
    yield "pass_filenames enabled", with_hook(lambda h: h.__setitem__("pass_filenames", True)), offline

    duplicated = copy.deepcopy(document)
    for repository in duplicated.get("repos", []) or []:
        for hook in repository.get("hooks", []) or []:
            if hook.get("id") == HOOK_ID:
                repository["hooks"].append(copy.deepcopy(hook))
                break
    yield "duplicate hook id", duplicated, offline

    commented = GUIDE_RUN.sub("# guide suite removed from the offline gate", offline)
    yield "guide invocation commented out", document, commented

    discovery = ALLOWLIST_RUN.sub("run \"python suites\" python3 -B -m unittest discover -s tests", offline)
    yield "discovery instead of allowlist", document, discovery


def self_test(document, offline, quiet=False):
    problems = []
    base = check_from_data(document, offline)
    if base:
        problems.append("the real wiring already fails: " + "; ".join(base))
    for label, changed_document, changed_offline in mutations(document, offline):
        if not check_from_data(changed_document, changed_offline):
            problems.append(f"negative control was NOT rejected: {label}")
        elif not quiet:
            print(f"negative control rejected: {label}")
    return problems


def check_from_data(document, offline):
    """Same as check() but against an in-memory document and runner text."""
    failures = []
    matches = [hook for hook in find_hooks(document) if hook.get("id") == HOOK_ID]
    if len(matches) != 1:
        return [f"expected exactly one hook with id {HOOK_ID!r}, found {len(matches)}"]
    hook = matches[0]
    if hook.get("entry") != EXPECTED_ENTRY:
        failures.append(f"hook entry is {hook.get('entry')!r}, expected {EXPECTED_ENTRY!r}")
    if hook.get("stages") != EXPECTED_STAGES:
        failures.append(f"hook stages are {hook.get('stages')!r}, expected {EXPECTED_STAGES!r}")
    if hook.get("always_run") is not True:
        failures.append(f"hook always_run is {hook.get('always_run')!r}, expected True")
    if hook.get("pass_filenames") is not False:
        failures.append(f"hook pass_filenames is {hook.get('pass_filenames')!r}, expected False")
    if not GUIDE_RUN.search(offline):
        failures.append("run-offline-checks.sh does not invoke tests/test-hermes-guide.sh through its run helper")
    if not ALLOWLIST_RUN.search(offline):
        failures.append(
            "run-offline-checks.sh does not invoke the reviewed offline allowlist runner "
            "(tests/run-reviewed-suites.py --set offline)"
        )
    if re.search(r"unittest\s+discover", offline):
        failures.append("run-offline-checks.sh still discovers tests instead of using the reviewed allowlist")
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--precommit", default=str(pathlib.Path(__file__).resolve().parents[1] / ".pre-commit-config.yaml"))
    parser.add_argument("--offline", default=str(pathlib.Path(__file__).resolve().parents[1] / "toolbox/run-offline-checks.sh"))
    parser.add_argument("--self-test", action="store_true", help="also require every negative control to be rejected")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        document = load_yaml(args.precommit)
        offline = pathlib.Path(args.offline).read_text(encoding="utf-8")
        problems = self_test(document, offline, quiet=args.quiet)
    else:
        problems = check(args.precommit, args.offline)

    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    if not args.quiet:
        print("PASS: guide gate is structurally wired to pre-push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
