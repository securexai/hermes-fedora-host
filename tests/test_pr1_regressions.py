"""Synthetic PR #1 follow-ups: no VM, host mutation, server, or provider calls."""

import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
POWER = ROOT / "scripts/hermes/unattended/certify_power.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("missing fixture module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PowerGuardTests(unittest.TestCase):
    def setUp(self):
        self.module = load("power_guard_fixture", POWER)
        self.xml = (
            f"<domain><name>{self.module.DOMAIN}</name><uuid>{self.module.UUID}</uuid>"
            f'<devices><disk device="disk"><source file="{self.module.DISK}"/>'
            "</disk></devices></domain>"
        )

    def invoke(self, optimize, raw=b'{"action":"start"}\n', uid=0, argv=None, xml=None):
        code = compile(POWER.read_text(), str(POWER), "exec", optimize=optimize)
        output = io.StringIO()
        with (
            patch("os.geteuid", return_value=uid),
            patch.object(sys, "argv", [str(POWER)] if argv is None else argv),
            patch.object(sys, "stdin", types.SimpleNamespace(buffer=io.BytesIO(raw))),
            patch("subprocess.check_output", side_effect=[
                (self.xml if xml is None else xml).encode(), b"running\n"
            ]) as inspect,
            patch("subprocess.run") as action,
            contextlib.redirect_stdout(output),
        ):
            status = 0
            try:
                exec(code, {"__name__": "__main__"})
            except SystemExit as error:
                status = error.code
        return status, json.loads(output.getvalue()), inspect.call_args_list, action.call_args_list

    def test_invalid_requests_never_inspect_or_act_even_optimized(self):
        cases = [
            {"uid": 1000}, {"argv": [str(POWER), "extra"]},
            {"raw": b'{"action":"destroy"}\n'},
            {"raw": b'{"action":"start","extra":true}\n'},
            {"raw": b'{"action":"start"}'}, {"raw": b"x" * 1025 + b"\n"},
            {"raw": b"[]\n"}, {"raw": b"null\n"}, {"raw": b"bad\n"},
        ]
        for optimize in (0, 1, 2):
            for case in cases:
                with self.subTest(optimize=optimize, case=case):
                    status, result, inspections, actions = self.invoke(optimize, **case)
                    self.assertEqual((status, result), (78, {"ok": False, "error": "lab-power-rejected"}))
                    self.assertEqual(inspections, [])
                    self.assertEqual(actions, [])

    def test_invalid_identity_and_disk_allow_only_dumpxml(self):
        variants = [
            self.xml.replace(self.module.DOMAIN, "wrong"),
            self.xml.replace(self.module.UUID, "wrong"),
            self.xml.replace('device="disk"', 'device="cdrom"'),
            self.xml.replace(self.module.DISK, "/wrong"),
            self.xml.replace(f'<source file="{self.module.DISK}"/>', ""),
            self.xml.replace("<devices>", '<devices><disk device="disk"/>'),
            "<domain><devices/></domain>", "invalid XML",
        ]
        for optimize in (0, 1, 2):
            for xml in variants:
                with self.subTest(optimize=optimize, xml=xml):
                    status, result, inspections, actions = self.invoke(optimize, xml=xml)
                    self.assertEqual((status, result), (78, {"ok": False, "error": "lab-power-rejected"}))
                    self.assertEqual(len(inspections), 1)
                    self.assertEqual(inspections[0].args[0][-2:], ["dumpxml", self.module.DOMAIN])
                    self.assertEqual(actions, [])

    def test_valid_actions_preserve_fixed_commands(self):
        base = ["/usr/bin/virsh", "-c", "qemu:///system"]
        for optimize in (0, 1, 2):
            for action in ("state", "start", "shutdown"):
                with self.subTest(optimize=optimize, action=action):
                    status, result, inspections, actions = self.invoke(
                        optimize, raw=(json.dumps({"action": action}) + "\n").encode()
                    )
                    self.assertEqual(status, 0)
                    self.assertEqual(result, {"ok": True, "domain_uuid": self.module.UUID, "state": "running"})
                    self.assertEqual([call.args[0] for call in inspections], [
                        base + ["dumpxml", self.module.DOMAIN], base + ["domstate", self.module.DOMAIN]
                    ])
                    self.assertEqual([call.args[0] for call in actions],
                                     [] if action == "state" else [base + [action, self.module.DOMAIN]])


class MemoryInputTests(unittest.TestCase):
    def test_preflight_memory_contract_with_synthetic_host(self):
        module = load("simple_host_fixture", ROOT / "scripts/hermes/simple/host.py")
        for text, reason in [
            ("MemTotal:       8388608 kB\n", "cgroup-v2-required"),
            ("MemTotal:       8388607 kB\n", "8-gib-memory-required"),
            ("MemFree: 9000000 kB\n", "memtotal-invalid"),
            ("MemTotal: nonsense kB\n", "memtotal-invalid"),
            ("MemTotal: 9000000 MB\n", "memtotal-invalid"),
            ("MemTotal: -1 kB\n", "memtotal-invalid"),
        ]:
            with self.subTest(text=text), contextlib.ExitStack() as stack:
                path = MagicMock()
                path.read_text.side_effect = [
                    'ID=fedora\nVERSION_ID=44\nVARIANT_ID=server\n', text
                ]
                flag = MagicMock()
                flag.read_bytes.return_value = b"\0\0\0\0\1"
                path.glob.return_value = [flag]
                path.exists.return_value = False
                stack.enter_context(patch.object(module, "Path", return_value=path))
                stack.enter_context(patch.object(module.os, "geteuid", return_value=0))
                stack.enter_context(patch.object(module.platform, "machine", return_value="x86_64"))
                stack.enter_context(patch.object(module, "out", return_value=b"Enforcing"))
                stack.enter_context(patch.object(module, "crypt_backed"))
                stack.enter_context(patch.object(module.shutil, "disk_usage", return_value=
                                                types.SimpleNamespace(free=20 * 1024 ** 3)))
                with self.assertRaisesRegex(module.Failure, "^" + reason + "$"):
                    module.preflight({})


class HttpSignatureTests(unittest.TestCase):
    def test_quiet_logging_accepts_base_keyword_and_positional_calls(self):
        dependencies = {
            "hermes_cli": types.SimpleNamespace(runtime_provider=MagicMock()),
            "openai": types.SimpleNamespace(OpenAI=MagicMock()),
            "plugins.platforms.telegram": types.SimpleNamespace(adapter=MagicMock()),
        }
        with patch.dict(sys.modules, dependencies):
            module = load("synthetic_smoke_fixture", ROOT / "tests/hermes-synthetic-smoke.py")
        handler = object.__new__(module.MockServices)
        output = io.StringIO()
        with contextlib.redirect_stderr(output), contextlib.redirect_stdout(output):
            self.assertIsNone(handler.log_message(format="quiet"))
            self.assertIsNone(handler.log_message("%s", "quiet"))
        self.assertEqual(output.getvalue(), "")
