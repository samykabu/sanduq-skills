"""Regression coverage for CSS declaration scans in static chart verifiers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _helpers import ASSETS, run_cli


CSS_CHECKERS = (
    "architecture-delta",
    "beeswarm",
    "bubble",
    "bump",
    "heatmap",
    "marimekko",
    "polar",
    "ridgeline",
    "slopegraph",
    "streamgraph",
    "waterfall",
)
ESCAPED_PROPERTY_CHECKERS = (
    "beeswarm", "bubble", "bump", "marimekko", "ridgeline", "slopegraph",
    "streamgraph", "waterfall",
)


class CssDeclarationTests(unittest.TestCase):
    def verify_with_css(self, directory: Path, diagram: str, css: str) -> tuple[int, str]:
        asset = ASSETS / f"example-{diagram}.html"
        source = asset.read_text(encoding="utf-8")
        self.assertIn("</style>", source)
        path = directory / asset.name
        path.write_text(source.replace("</style>", f"\n{css}\n</style>", 1), encoding="utf-8")
        return run_cli(f"verify-{diagram}.py", path)

    def test_quoted_style_data_and_comments_do_not_change_geometry(self):
        cases = (
            ('body { --notes: "Draft; transform: translate(9px)" }', True),
            ("/* rect { transform: translate(9px) } */", True),
            ('rect { --notes: "/*"; transform: translate(9px); --end: "*/" }', False),
            ('rect { /**/ transform: translate(9px) }', False),
        )
        with tempfile.TemporaryDirectory() as path:
            for diagram in CSS_CHECKERS:
                for css, expected_pass in cases:
                    with self.subTest(diagram=diagram, css=css):
                        code, output = self.verify_with_css(Path(path), diagram, css)
                        self.assertEqual(code, 0 if expected_pass else 1, output)

    def test_escaped_property_is_reported_but_an_escape_in_quoted_data_is_allowed(self):
        with tempfile.TemporaryDirectory() as path:
            for diagram in ESCAPED_PROPERTY_CHECKERS:
                with self.subTest(diagram=diagram):
                    allowed = r'body { --notes: "style sample; tr\61nsform: translate(9px)" }'
                    code, output = self.verify_with_css(Path(path), diagram, allowed)
                    self.assertEqual(code, 0, output)
                    escaped = r"rect { tr\61nsform: translate(9px) }"
                    code, output = self.verify_with_css(Path(path), diagram, escaped)
                    self.assertEqual(code, 1, output)
                    self.assertIn("escaped CSS property", output)
