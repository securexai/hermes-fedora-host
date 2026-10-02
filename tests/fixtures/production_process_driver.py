"""Temporary subprocess fixture; every path and host operation is synthetic."""

import io
import os
import subprocess
import sys
import time
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

root = Path(__file__).resolve().parent
sys.path.insert(0, (root / "source").read_text())
from production import host, primitives, receivers, runtime, startup  # noqa: E402


def write_later():
    (root / "writer-pid").write_text(str(os.getpid()))
    deadline = time.monotonic() + 20
    while not (root / "finish").exists():
        if time.monotonic() > deadline:
            raise RuntimeError("fixture-deadline")
        time.sleep(0.01)
    (root / "data").write_text("new-state")
    (root / "written").touch()


class Backend:
    uid = os.getuid()

    def initialize_namespace(self):
        # OS setup is synthetic here; keep real dispatcher/subreaper locking.
        (root / "namespace-initialized").touch()

    def current(self):
        return "old"

    def prepare(self, *args):
        pass

    def release(self, release):
        return root, {}

    def stop(self):
        pass

    def snapshot(self, *args):
        return "snapshot"

    def restore(self, *args):
        (root / "data").write_text("old-state")
        (root / "restored").touch()

    def import_images(self, *args):
        pass

    def configure(self, release):
        runtime.Backend.receiver_action(self, release, "configure")

    def activate(self, *args):
        pass

    def verify(self, *args):
        assert (root / "data").read_text() == "old-state"

    def set_current(self, *args):
        pass


def main():
    if sys.argv[1] == "release-action":
        (root / "receiver-pid").write_text(str(os.getpid()))
        if (root / "detached").exists():
            subprocess.Popen(
                [sys.executable, "-I", __file__, "writer"],
                close_fds=True,
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Test kills this receiver as well, leaving only its detached child.
            time.sleep(20)
        else:
            write_later()
        return
    if sys.argv[1] == "writer":
        write_later()
        return
    request = {"operation": sys.argv[1], "apply": True}
    cfg = {"application_mode": "synthetic", "kind": "fixture", "artifact_budget_bytes": 1}
    with (
        patch.object(host, "read_json", return_value=cfg),
        patch.object(host.preflight, "configuration", return_value=cfg),
        patch.object(host.preflight, "enforce", return_value={}),
        patch.object(host, "STATE", root),
        patch.object(host, "Backend", return_value=Backend()),
        patch.object(host, "run", return_value=SimpleNamespace(returncode=0)),
        patch.object(startup, "operation", side_effect=nullcontext),
        patch.object(host.bundle, "unpack", return_value={"files": {}}),
        patch.object(host.bundle, "identity", return_value="new"),
        patch.object(receivers, "running_matches", return_value=False),
        patch.object(receivers, "for_release", return_value=root),
    ):
        # Emulate only dispatch's root check; filesystem lock ownership stays real.
        original_require = host.require
        with patch.object(
            host,
            "require",
            side_effect=lambda condition, reason: original_require(
                condition or reason == "installed-root-dispatcher-required", reason
            ),
        ):
            try:
                host.dispatch(io.BytesIO(primitives.canonical(request)))
            except primitives.Refused as error:
                print(str(error), file=sys.stderr)
                raise SystemExit(1) from None


if __name__ == "__main__":
    main()
