"""Lint isolated copies so repository fix/glob settings cannot affect other files."""

from pathlib import Path
import re
import subprocess
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
FILES = ["setup-ssh-key-only.md", "docs/plans/2026-09-12-fedora-ssh-key-only.md"]


def main():
    config = yaml.safe_load((ROOT / ".markdownlint-cli2.yaml").read_text())
    config.update(fix=False, globs=FILES)
    for name in FILES:
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", (ROOT / name).read_text()):
            if "://" not in target and not target.startswith("#"):
                assert ((ROOT / name).parent / target.split("#")[0]).exists(), target
    with tempfile.TemporaryDirectory(prefix="ssh-doc-lint-") as temporary:
        target = Path(temporary) / ".markdownlint-cli2.yaml"
        target.write_text(yaml.safe_dump(config))
        for name in FILES:
            copy = Path(temporary) / name
            copy.parent.mkdir(parents=True, exist_ok=True)
            copy.write_bytes((ROOT / name).read_bytes())
        return subprocess.run(
            ["markdownlint-cli2", "--config", str(target), "--no-globs", *FILES],
            cwd=temporary,
            check=False,
        ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
