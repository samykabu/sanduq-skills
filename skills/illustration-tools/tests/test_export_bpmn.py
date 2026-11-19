"""The BPMN export plays one selected route while preserving the static process."""

import importlib.util
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[1] / "skills" / "illustrate"
spec = importlib.util.spec_from_file_location("export_diagram", SKILL / "scripts" / "export_diagram.py")
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)

FORK = """<svg viewBox="0 0 190 94" data-diagram="bpmn">
  <defs><marker id="head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5"
                orient="auto"><path d="M0 0 L10 5 L0 10 Z" fill="#334155"/></marker></defs>
  <g transform="translate(0 10)">
    <line data-bpmn="sequenceFlow" data-bpmn-id="common" data-source="start" data-target="choice"
          data-bpmn-routes="approved rejected" x1="24" y1="35" x2="76" y2="35" stroke="#334155"
          marker-end="url(#head)"/>
  </g>
  <path data-bpmn="sequenceFlow" data-bpmn-id="yes" data-source="choice" data-target="end-a"
        data-bpmn-routes="approved" d="M84 41 V25 H160" fill="none" stroke="#334155" marker-end="url(#head)"/>
  <path data-bpmn="sequenceFlow" data-bpmn-id="no" data-source="choice" data-target="end-b"
        data-bpmn-routes="rejected" d="M84 49 V67 H160" fill="none" stroke="#334155" marker-end="url(#head)"/>
  <circle data-bpmn="startEvent" data-bpmn-id="start" data-lane="one" cx="18" cy="45" r="6" fill="none" stroke="#334155"/>
  <path data-bpmn="exclusiveGateway" data-bpmn-id="choice" data-lane="two" d="M76 45 L84 37 L92 45 L84 53 Z"
        fill="#fff" stroke="#334155"/>
  <circle data-bpmn="endEvent" data-bpmn-id="end-a" data-lane="two" cx="168" cy="25" r="8" fill="none" stroke="#334155"/>
  <circle data-bpmn="endEvent" data-bpmn-id="end-b" data-lane="two" cx="168" cy="67" r="8" fill="none" stroke="#334155"/>
</svg>"""


def animated_flow_ids(svg):
    root = ET.fromstring(svg)
    return [element.attrib["data-for-flow"] for element in root.iter() if "data-for-flow" in element.attrib]


class BpmnExportTests(unittest.TestCase):
    def test_named_routes_preserve_both_branches_in_the_static_figure(self):
        svg = export.animated_svg(FORK, "flow", bpmn_route="approved")
        self.assertEqual(animated_flow_ids(svg), ["common", "yes"])
        self.assertEqual(animated_flow_ids(export.animated_svg(FORK, bpmn_route="rejected")), ["common", "no"])
        root = ET.fromstring(svg)
        ns = {"svg": "http://www.w3.org/2000/svg"}
        overlay = root.find("svg:g[@data-bpmn-playback]", ns)
        style = root.find("svg:defs/svg:style[@data-illustrate-animation]", ns)
        self.assertIn("@media (prefers-reduced-motion: no-preference)", style.text)
        self.assertEqual(overlay.get("aria-hidden"), "true")
        self.assertEqual(overlay[0].get("transform"), "translate(0 10)")
        self.assertTrue(all(token.get("opacity") == "0" for token in overlay.iter(f"{{{ns['svg']}}}circle")))
        root.remove(overlay)
        root.find("svg:defs", ns).remove(style)
        self.assertEqual(ET.tostring(root), ET.tostring(ET.fromstring(export.standalone_svg(FORK, system_fonts=True))))

    def test_default_and_implicit_linear_route(self):
        default = FORK.replace('data-diagram="bpmn"', 'data-diagram="bpmn" data-bpmn-default-route="rejected"')
        self.assertEqual(animated_flow_ids(export.animated_svg(default)), ["common", "no"])
        self.assertEqual(animated_flow_ids(export.animated_svg(default, bpmn_route="approved")), ["common", "yes"])
        linear = FORK.replace('data-bpmn="sequenceFlow" data-bpmn-id="no"', 'data-bpmn-id="no"')
        linear = linear.replace(' data-bpmn-routes="approved rejected"', '').replace(' data-bpmn-routes="approved"', '')
        self.assertEqual(animated_flow_ids(export.animated_svg(linear)), ["common", "yes"])

    def test_branch_without_route_and_unknown_route_are_refused(self):
        with self.assertRaisesRegex(export.ExportError, "requires --bpmn-route.*Available routes: approved, rejected"):
            export.animated_svg(FORK)
        with self.assertRaisesRegex(export.ExportError, "Unknown BPMN route 'other'"):
            export.animated_svg(FORK, bpmn_route="other")
        with self.assertRaisesRegex(export.ExportError, "requires a BPMN diagram"):
            export.animated_svg(FORK.replace(' data-diagram="bpmn"', ''), bpmn_route="approved")

    def test_invalid_route_graphs_are_refused(self):
        disconnected = FORK.replace(
            '</svg>',
            '<path data-bpmn="sequenceFlow" data-bpmn-id="extra" data-source="end-b" data-target="end-a" '
            'data-bpmn-routes="approved" d="M168 67 V25"/></svg>',
        )
        cases = (
            (FORK.replace('data-bpmn-routes="rejected"', 'data-bpmn-routes="approved"'), "ambiguous"),
            (FORK.replace('data-bpmn-routes="approved"', 'data-bpmn-routes="other"'), "before reaching an endEvent"),
            (FORK.replace('data-target="end-a"', 'data-target="choice"'), "cycle"),
            (FORK.replace('data-target="end-a"', 'data-target="missing"'), "link two nodes by ID"),
            (FORK.replace('data-bpmn-id="yes"', 'data-bpmn-id="choice"'), "Duplicate BPMN"),
            (FORK.replace('data-bpmn="startEvent"', 'data-bpmn="task"'), "exactly one startEvent"),
            (FORK.replace('d="M84 41 V25 H160"', 'd=""'), "needs SVG path"),
            (disconnected, "outside the start-to-end path"),
        )
        for source, error in cases:
            with self.subTest(error=error), self.assertRaisesRegex(export.ExportError, error):
                export.animated_svg(source, bpmn_route="approved")

    def test_gif_cli_plays_one_route_and_holds_the_static_frame(self):
        try:
            from PIL import Image, ImageSequence
            from playwright.sync_api import sync_playwright  # noqa: F401
        except ImportError:
            self.skipTest("Playwright and Pillow are needed for GIF export")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "fork.html"
            theme = "<style>@media (prefers-color-scheme:dark){:root{--accent:#27ceaf}}</style>"
            source.write_text(theme + FORK, encoding="utf-8")
            args = [str(source), "--gif", "--bpmn-route", "rejected", "--fps", "10", "--scale", "1", "--theme", "dark"]
            with patch.object(sys, "argv", ["export_diagram.py", *args]):
                self.assertEqual(export.main(), 0)
            with Image.open(source.with_suffix(".gif")) as gif:
                frames = [frame.convert("RGB") for frame in ImageSequence.Iterator(gif)]
        self.assertGreater(len(frames), 5)

        def token_y(frame):
            return {index // frame.width for index, (red, green, blue) in enumerate(frame.get_flattened_data())
                    if red < 100 and green > 160 and blue > 110}

        rows = set().union(*(token_y(frame) for frame in frames))
        self.assertTrue(any(row > 60 for row in rows), "a token must traverse the selected rejection branch")
        self.assertTrue(any(41 < row < 49 for row in rows), "a token must traverse the transformed shared flow")
        self.assertTrue(all(row > 36 for row in rows), "the approval branch must remain static")
        self.assertFalse(token_y(frames[-1]), "the final GIF frame must be static")


if __name__ == "__main__":
    unittest.main()
