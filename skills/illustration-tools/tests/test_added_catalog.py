"""Coverage for the upstream type ports and their Sanduq theme/hand paths."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _helpers import ASSETS, SCRIPTS, load, run_cli

TYPES = (
    "service-blueprint", "steps", "unit-grid", "requirement-traceability",
    "event-modeling", "schedule-network", "sbgn", "architecture-containment",
    "box-plot", "arc-diagram",
)
THEME = load("illustration_theme.py")
SELF_CHECK = load("self_check.py")


def example(slug: str, suffix: str = "") -> Path:
    return ASSETS / f"example-{slug}{suffix}.html"


class AddedCatalogCases(unittest.TestCase):
    def test_all_type_variants_pass_their_appropriate_gates(self):
        for slug in TYPES:
            with self.subTest(type=slug):
                code, output = run_cli(f"verify-{slug}.py", "--all")
                self.assertEqual(code, 0, output)
                for suffix in ("", "-dark", "-full", "-hand"):
                    path = example(slug, suffix)
                    self.assertEqual(SELF_CHECK.verify(path, strict=True), [], path.name)
                self.assertIn('class="rough-generated"', example(slug, "-hand").read_text(encoding="utf-8"))

    def test_gallery_routes_to_each_new_diagram(self):
        for name in ("index.html", "index-variation-1.html", "index-variation-2.html"):
            gallery = (ASSETS / name).read_text(encoding="utf-8")
            for slug in TYPES:
                with self.subTest(gallery=name, type=slug):
                    self.assertIn(f'"{slug}"', gallery)

    def test_specialized_verifiers_reject_inconsistent_data(self):
        cases = {
            "service-blueprint": ('data-focal="true"', 'data-focal="false"', "focal"),
            "steps": ('data-index="2"', 'data-index="1"', "duplicate data-index"),
            "unit-grid": ('data-unit-filled="64"', 'data-unit-filled="65"', "filled"),
            "requirement-traceability": ('data-trace-to="REQ-01"', 'data-trace-to="REQ-99"', "REQ-01"),
            "event-modeling": ('data-from="CMD-01" data-to="EVT-01"', 'data-from="CMD-02" data-to="EVT-01"', "endpoints do not match the stage"),
            "schedule-network": (">TF 1</text>", ">TF 0</text>", "printed tf"),
            "sbgn": ('data-from="bcar" data-to="v1"', 'data-from="bcar" data-to="missing"', "missing"),
            "architecture-containment": ('data-scope-kind="admin"', 'data-scope-kind="traffic"', "scope"),
            "box-plot": ('data-q2="22"', 'data-q2="24"', "median"),
            "arc-diagram": ('data-span="5"', 'data-span="6"', "span"),
        }
        with tempfile.TemporaryDirectory() as td:
            for slug, (before, after, message) in cases.items():
                with self.subTest(type=slug):
                    original = example(slug).read_text(encoding="utf-8")
                    self.assertIn(before, original)
                    path = Path(td) / f"example-{slug}.html"
                    path.write_text(original.replace(before, after, 1), encoding="utf-8")
                    code, output = run_cli(f"verify-{slug}.py", path)
                    self.assertEqual(code, 1, output)
                    self.assertIn(message, output)

    def test_box_plot_verifies_painted_marks_and_labels(self):
        source = example("box-plot").read_text(encoding="utf-8")
        median = '<line data-role="median" x1="204" y1="64.0" x2="204" y2="96.0" stroke="#2d3142"'
        auth = '<g data-name="Auth"'
        cases = (
            (source.replace(median, median.replace('stroke="#2d3142"', "stroke=none"), 1), "paints nothing"),
            (source.replace('</style>', 'text[data-name="Auth"] { display:none; }</style>', 1), "hides its bound label"),
            (source.replace(auth, '<g display=none data-name="Auth"', 1), "never drawn"),
            (source.replace(auth, '<g data-pinned data-name="Auth"', 1), ""),
        )
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "example-box-plot.html"
            for changed, diagnosis in cases:
                with self.subTest(diagnosis=diagnosis):
                    self.assertNotEqual(changed, source)
                    path.write_text(changed, encoding="utf-8")
                    code, output = run_cli("verify-box-plot.py", path)
                    self.assertEqual(code, int(bool(diagnosis)), output)
                    if diagnosis:
                        self.assertIn(diagnosis, output)

    def test_containment_checks_the_dasharray_rendered_with_important_priority(self):
        source = example("architecture-containment").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "example-architecture-containment.html"
            anchor = 'stroke-dasharray="4,4"'
            for declaration, expected in (("none!important;stroke-dasharray:4,4", 1),
                                          ("4,4!important;stroke-dasharray:none", 0)):
                with self.subTest(inline=declaration):
                    changed = source.replace(anchor, f'style="stroke-dasharray:{declaration}"', 1)
                    self.assertNotEqual(changed, source)
                    path.write_text(changed, encoding="utf-8")
                    code, output = run_cli("verify-architecture-containment.py", path)
                    self.assertEqual(code, expected, output)
                    if expected:
                        self.assertIn("admin band must use a dashed stroke", output)

    def test_service_blueprint_accepts_japanese_text_across_two_tspans(self):
        path = Path(__file__).parent / "fixtures/service-blueprint-japanese-two-line.html"
        code, output = run_cli("verify-service-blueprint.py", path)
        self.assertEqual(code, 0, output)

    def test_ported_verifiers_accept_project_fonts_and_colors(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            config_path = project / ".github/illustration-theme.yml"
            config_path.parent.mkdir()
            for preset, mode, fonts in (("cobalt", "light", "system"), ("emerald", "dark", "remote")):
                config = THEME.default_config(preset, mode, fonts)
                config_path.write_text(THEME.dump_yaml(config), encoding="utf-8")
                theme = THEME.resolved(config)
                for slug in TYPES:
                    with self.subTest(theme=preset, type=slug):
                        source = example(slug)
                        path = project / source.name
                        path.write_text(THEME.apply_theme(source.read_text(encoding="utf-8"), theme, source),
                                        encoding="utf-8")
                        result = subprocess.run(
                            [sys.executable, str(SCRIPTS / f"verify-{slug}.py"), str(path)],
                            cwd=project, capture_output=True, text=True, encoding="utf-8",
                        )
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
