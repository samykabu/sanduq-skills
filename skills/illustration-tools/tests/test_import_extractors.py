"""Stdlib unittest suite for the draw.io / Mermaid / Excalidraw import pipeline.

Run from the extension directory:  python -m unittest discover -s tests -v
Source labels in the fixtures are untrusted data; the adversarial cases prove they stay inert.
"""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "illustrate" / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"

CASES = {
    "drawio": ("drawio_extract.py", ["sample-architecture.drawio"]),
    "mermaid": (
        "mermaid_extract.py",
        ["sample-flowchart.mmd", "sample-readme-with-mermaid.md", "sample-adversarial.mmd"],
    ),
    "excalidraw": (
        "excalidraw_extract.py",
        ["sample-whiteboard.excalidraw", "sample-adversarial.excalidraw"],
    ),
}


def run(args: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class ExtractorTests(unittest.TestCase):
    def test_every_fixture_digests(self) -> None:
        for kind, (script, fixtures) in CASES.items():
            for fixture in fixtures:
                with self.subTest(kind=kind, fixture=fixture):
                    proc = run([str(SCRIPTS / script), str(FIXTURES / fixture)])
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertIn("budget:", proc.stdout)
                    self.assertIn("### Nodes", proc.stdout)

    def test_adversarial_labels_stay_inert(self) -> None:
        for script, fixture in (
            ("mermaid_extract.py", "sample-adversarial.mmd"),
            ("excalidraw_extract.py", "sample-adversarial.excalidraw"),
        ):
            with self.subTest(fixture=fixture):
                out = run([str(SCRIPTS / script), str(FIXTURES / fixture)]).stdout
                # Link targets never reach the digest; URLs inside labels are escaped data,
                # so no live Markdown link or raw HTML can form.
                self.assertNotIn("do-not-follow", out)
                self.assertNotIn("](http", out)
                self.assertNotIn("<br", out)
                self.assertNotIn("<script", out.lower())
                self.assertIn("discarded:", out)

    def test_malformed_drawio_xml_exits_2(self) -> None:
        # The drivers cover the wrong-suffix exit 2 of every extractor; only this reaches draw.io's XML parse error.
        proc = run([str(SCRIPTS / "drawio_extract.py"), str(FIXTURES.parent / "test_import_extractors.py")])
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("malformed XML", proc.stderr)


def drawio_edge(style: str) -> str:
    """A two-node .drawio with one a->b connector carrying `style`."""
    return (
        '<mxfile><diagram name="p" id="p"><mxGraphModel><root>'
        '<mxCell id="0"/><mxCell id="1" parent="0"/>'
        '<mxCell id="a" value="A" vertex="1" parent="1">'
        '<mxGeometry x="0" y="0" width="80" height="40" as="geometry"/></mxCell>'
        '<mxCell id="b" value="B" vertex="1" parent="1">'
        '<mxGeometry x="200" y="0" width="80" height="40" as="geometry"/></mxCell>'
        f'<mxCell id="e" edge="1" parent="1" source="a" target="b" style="{style}">'
        '<mxGeometry relative="1" as="geometry"/></mxCell>'
        "</root></mxGraphModel></diagram></mxfile>"
    )


class DrawioArrowheadTests(unittest.TestCase):
    """The tail is the semantic source: arrowheads decide direction, not attribute order."""

    CASES = {
        # style: (source, target, bidirectional, undirected, entry_points, terminals)
        "": ("a", "b", False, False, ["A"], ["B"]),
        "startArrow=classic;endArrow=none": ("b", "a", False, False, ["B"], ["A"]),
        "startArrow=classic;endArrow=classic": ("a", "b", True, False, [], []),
        "startArrow=none;endArrow=none": ("a", "b", False, True, [], []),
    }

    def test_arrowheads_normalize_endpoints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "edge.drawio"
            for style, (src, tgt, bidi, undirected, entries, terminals) in self.CASES.items():
                with self.subTest(style=style or "default"):
                    path.write_text(drawio_edge(style), encoding="utf-8")
                    proc = run([str(SCRIPTS / "drawio_extract.py"), str(path), "--json"])
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    page = json.loads(proc.stdout)["pages"][0]
                    (edge,) = page["edges"]
                    self.assertEqual((edge["source"], edge["target"]), (src, tgt))
                    self.assertEqual(edge["bidirectional"], bidi)
                    self.assertEqual(edge["undirected"], undirected)
                    self.assertEqual(page["analysis"]["entry_points"], entries)
                    self.assertEqual(page["analysis"]["terminals"], terminals)


class VerifierTests(unittest.TestCase):
    """Full structural gates in place, plus upstream's mutation regressions on one mutated temp copy.

    The drivers write only to their own temp dirs, so the pristine run needs no copy of the tree. A mutation
    fails inside the driver's last docs check, so that check runs in-process against the mutated file.
    """


def pristine(case, kind):
    proc = run([str(ROOT / "tests" / f"verify-{kind}-import.py")])
    case.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


for _kind in CASES:
    setattr(VerifierTests, f"test_verifier_passes_on_pristine_tree_{_kind}", lambda self, kind=_kind: pristine(self, kind))


class MutationTests(unittest.TestCase):
    def rejects(self, kind: str, check: str, attribute: str, old: str, new: str, reason: str) -> None:
        """Point the driver's `attribute` file at a temp copy with `old` replaced; `check` must fail with `reason`."""
        spec = importlib.util.spec_from_file_location(f"verify_{kind}_import_mutation", ROOT / "tests" / f"verify-{kind}-import.py")
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        original = getattr(driver, attribute)
        text = original.read_text(encoding="utf-8")
        self.assertIn(old, text)
        with tempfile.TemporaryDirectory() as directory:
            mutated = Path(directory) / original.name
            mutated.write_text(text.replace(old, new, 1), encoding="utf-8")
            setattr(driver, attribute, mutated)
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
                getattr(driver, check)()
        self.assertEqual(raised.exception.code, 1, stdout.getvalue())
        self.assertIn(reason, stderr.getvalue())

    def test_stale_slash_command_is_rejected(self) -> None:
        for kind, check in (("drawio", "check_docs"), ("excalidraw", "check_docs_and_wiring")):
            with self.subTest(kind=kind):
                self.rejects(kind, check, "IMPORT_REF", f"/illustrate:import-{kind}", "/illustrate:import", "slash command")

    def test_elbowed_drawio_worked_example_route_is_rejected(self) -> None:
        self.rejects("drawio", "check_docs", "EXAMPLE", 'd="M560,232 H640"', 'd="M560,232 H592 V252 H640"',
                     "direct horizontal connector")

    def test_extra_accent_in_excalidraw_example_is_rejected(self) -> None:
        # A resolved theme accent counts the same as the upstream default literal.
        self.rejects("excalidraw", "check_docs_and_wiring", "EXAMPLE", "</svg>", '<g fill="#2563eb"/>' * 5 + "</svg>", "accent")


if __name__ == "__main__":
    unittest.main()
