"""Offline relocation coverage; executable targets are synthetic fixtures only."""

import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MOVES = {
    "hermes-deploy.sh": "scripts/hermes/deploy.sh",
    "hermes-remediation-wizard.sh": "scripts/hermes/remediation-wizard.sh",
    "hermes-simple-deploy.sh": "scripts/hermes/simple/deploy.sh",
    "hermes-certify-vm.sh": "vm/hermes-certify-vm.sh",
}


class RootEntrypointTests(unittest.TestCase):
    def test_launchers_preserve_process_contract(self):
        with tempfile.TemporaryDirectory(prefix="hermes checkout with spaces ") as tmp:
            checkout = Path(tmp) / "checkout with spaces"
            checkout.mkdir()
            for old, new in MOVES.items():
                with self.subTest(launcher=old):
                    shutil.copy2(ROOT / old, checkout / old)
                    target = checkout / new
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(
                        '#!/usr/bin/env python3\n'
                        'import json, os, sys\n'
                        'print(json.dumps([sys.argv[1:], os.getcwd(), os.environ["LAYOUT_TEST"], '
                        'sys.stdin.read(), os.getpid()]))\n'
                        'print("fixture stderr", file=sys.stderr)\n'
                        'sys.exit(37)\n'
                    )
                    target.chmod(0o755)
                    args = ["two words", "", "*", "'quoted'", "$literal", "--target=fixture"]
                    process = subprocess.Popen(
                        [str(checkout / old), *args], cwd=tmp,
                        env={**os.environ, "LAYOUT_TEST": "unchanged value"},
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True,
                    )
                    out, err = process.communicate("fixture stdin", timeout=10)
                    self.assertEqual(process.returncode, 37)
                    self.assertEqual(json.loads(out), [args, tmp, "unchanged value", "fixture stdin", process.pid])
                    self.assertEqual(err, "fixture stderr\n")
                    target.write_text('#!/bin/sh\necho ready\nexec sleep 30\n')
                    process = subprocess.Popen([str(checkout / old)], cwd=tmp, stdout=subprocess.PIPE, text=True)
                    try:
                        self.assertEqual(process.stdout.readline(), "ready\n")
                        process.send_signal(signal.SIGTERM)
                        self.assertEqual(process.wait(timeout=5), -signal.SIGTERM)
                    finally:
                        if process.poll() is None:
                            process.kill()
                            process.wait()
                        process.stdout.close()

    def test_relocated_sources_preserve_ssh_and_guides(self):
        for rel in ["setup-ssh-key-only.sh", "scripts/hermes/manual/setup-ssh-key-only.sh"]:
            original = subprocess.check_output(["git", "show", f"9353b56:{rel}"], cwd=ROOT)
            self.assertEqual((ROOT / rel).read_bytes(), original)
        for name in ["hermes-fedora-server-install-guide.html", "secure-hermes-installation-plan.html"]:
            original = subprocess.check_output(["git", "show", f"9353b56:{name}"], cwd=ROOT).decode()
            self.assertEqual((ROOT / "docs" / name).read_text(), original.replace('href="docs/', 'href="'))
            redirect = (ROOT / name).read_text()
            self.assertIn('window.location.replace("docs/' + name + '" + window.location.search + window.location.hash)', redirect)
            self.assertIn('href="docs/' + name + '"', redirect)
        original = subprocess.check_output(["git", "show", "9353b56:setup-ssh-key-only.md"], cwd=ROOT).decode()
        self.assertEqual((ROOT / "docs/setup-ssh-key-only.md").read_text(), original)
        self.assertEqual(re.findall(r'^#+ .*$', original, re.M),
                         re.findall(r'^#+ .*$', (ROOT / "setup-ssh-key-only.md").read_text(), re.M))

    def test_every_launcher_and_implementation_invalidates_fingerprint(self):
        script = ROOT / "scripts/hermes/promotion-record.sh"
        required = re.findall(r'"\$root/([^"*]+)"', script.read_text().split('  # The new public seam')[0])
        with tempfile.TemporaryDirectory(prefix="hermes-fingerprint-") as tmp:
            for rel in required:
                path = Path(tmp) / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("synthetic certification input\n")
            def fingerprint():
                return subprocess.check_output(
                    ["bash", "-c", 'source "$1"; promotion_record_fingerprint "$2"', "test", str(script), tmp],
                    text=True,
                )
            before = fingerprint()
            for rel in [*MOVES, *MOVES.values()]:
                with self.subTest(path=rel):
                    path = Path(tmp) / rel
                    original = path.read_text()
                    path.write_text(original + "changed implementation\n")
                    self.assertNotEqual(before, fingerprint())
                    path.write_text(original)
                    self.assertEqual(before, fingerprint())
    def test_local_links_and_fragments(self):
        # Only maintained relocation-related documents; never fetch external URLs.
        from html.parser import HTMLParser
        from urllib.parse import unquote, urlsplit

        class HTMLLinks(HTMLParser):
            def __init__(self, text):
                super().__init__()
                self.links = []
                self.anchors = set()
                self.feed(text)

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if "id" in attrs:
                    self.anchors.add(attrs["id"])
                if tag == "a" and "name" in attrs:
                    self.anchors.add(attrs["name"])
                for key in ("href", "src"):
                    if key in attrs:
                        self.links.append(attrs[key])

        def markdown_anchors(text):
            result = set()
            counts = {}
            for title in re.findall(r'^#{1,6} (.+)$', text, re.M):
                slug = re.sub(r'[^\w\- ]', '', title.lower()).replace(' ', '-')
                count = counts.get(slug, 0)
                counts[slug] = count + 1
                result.add(slug + (f"-{count}" if count else ""))
            return result

        names = ["README.md", "AGENTS.md", "PROVENANCE.md", "docs/VM_TESTING_GUIDE.md",
                 "setup-ssh-key-only.md", "docs/setup-ssh-key-only.md",
                 "docs/plans/2026-09-26-root-entrypoint-organization.md"]
        for name in ("hermes-fedora-server-install-guide.html", "secure-hermes-installation-plan.html"):
            names.extend([name, "docs/" + name])
        checked = 0
        for name in names:
            source = ROOT / name
            text = source.read_text()
            links = HTMLLinks(text).links if source.suffix == ".html" else re.findall(r'\[[^\]]+\]\(([^)]+)\)', text)
            for link in links:
                url = urlsplit(link)
                if url.scheme or url.netloc:
                    continue
                with self.subTest(source=name, link=link):
                    target = source.parent / unquote(url.path) if url.path else source
                    self.assertTrue(target.exists(), str(target))
                    if url.fragment:
                        content = target.read_text()
                        anchors = HTMLLinks(content).anchors
                        if target.suffix == ".md":
                            anchors |= markdown_anchors(content)
                        self.assertIn(unquote(url.fragment), anchors)
                    checked += 1
        self.assertGreater(checked, 40)

    def test_help_through_root_and_canonical_commands(self):
        # --help exits before any transport, package or VM operations.
        with tempfile.TemporaryDirectory(prefix="hermes-help-") as tmp:
            for old, new in MOVES.items():
                with self.subTest(launcher=old):
                    outputs = []
                    for rel in (old, new):
                        result = subprocess.run([str(ROOT / rel), "--help"], cwd=tmp,
                                                capture_output=True, text=True, timeout=10)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        outputs.append((result.stdout, result.stderr))
                    self.assertEqual(*outputs)
