"""generate-hand-variants.cjs converts one consumer file with --in/--out, and says what it needs when it cannot."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from _helpers import ASSETS, SCRIPTS, SKILL_DIR

GENERATOR = SCRIPTS / "generate-hand-variants.cjs"
NODE = shutil.which("node")


def run(*args: str, script: Path = GENERATOR) -> subprocess.CompletedProcess:
    return subprocess.run([NODE, str(script), *args], capture_output=True, text=True, encoding="utf-8")


@unittest.skipUnless(NODE, "node is not installed")
class OneFile(unittest.TestCase):
    @unittest.skipUnless((SKILL_DIR / "node_modules").is_dir(), "run npm ci in the skill folder first")
    def test_in_out_reproduces_a_committed_hand_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "flowchart-hand.html"
            # flowchart is TYPES[1], so the full run seeds it 1000 + 2 * 101.
            result = run("--in", str(ASSETS / "example-flowchart.html"), "--out", str(out), "--seed", "1202")
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual((ASSETS / "example-flowchart-hand.html").read_bytes(), out.read_bytes())

    def test_a_partial_call_prints_the_usage(self):
        for args in (("--in", "a.html"), ("--out", "b.html"), ("--in", "a.html", "--out", "b.html", "--seed", "x"),
                     ("--input", "a.html")):
            with self.subTest(args=args):
                result = run(*args)
                self.assertEqual(2, result.returncode)
                self.assertIn("usage:", result.stderr)

    def test_missing_packages_name_the_install_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "scripts" / GENERATOR.name
            script.parent.mkdir()
            shutil.copy2(GENERATOR, script)
            result = run("--in", "a.html", "--out", "b.html", script=script)
            self.assertEqual(1, result.returncode)
            self.assertIn("npm ci", result.stderr)


if __name__ == "__main__":
    unittest.main()
