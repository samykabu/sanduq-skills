"""`export_diagram.py --animated`: a reveal that GitHub can play, ending on the complete figure."""
import importlib.util
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "illustrate"
spec = importlib.util.spec_from_file_location("export_diagram", SKILL / "scripts" / "export_diagram.py")
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)

MOTION_SOURCES = [SKILL / "assets" / "template-motion.html", *sorted((SKILL / "assets").glob("*-animated.html"))]


def pixel_difference(first, second):
    """None when two PNG screenshots show the same figure; otherwise the box and count of changed pixels.

    Chromium re-rasterises thin antialiased edges slightly differently between page loads (channel
    differences up to ~35/255 on a few edge pixels). A missing, faded or moved part differs at full
    contrast, so only pixels differing by more than 64 count.
    """
    if first == second:
        return None
    import io
    from PIL import Image, ImageChops
    diff = ImageChops.difference(*(Image.open(io.BytesIO(shot)).convert("RGB") for shot in (first, second)))
    changed = diff.point(lambda value: 255 if value > 64 else 0)
    box = changed.getbbox()
    return None if box is None else (box, sum(1 for pixel in changed.getdata() if max(pixel)))


class AnimatedExportTests(unittest.TestCase):
    def test_every_shipped_motion_figure_exports_a_sandbox_safe_reveal(self):
        for source in MOTION_SOURCES:
            with self.subTest(source=source.name):
                html = source.read_text(encoding="utf-8")
                svg = export.animated_svg(html)
                ET.fromstring(svg.encode("utf-8"))  # a standalone .svg is XML: browsers refuse it otherwise
                ET.fromstring(export.standalone_svg(html).encode("utf-8"))
                self.assertNotIn("<script", svg)
                self.assertNotIn("@import", svg)
                self.assertNotIn("data-motion-decorative", svg)
                style = re.search(r'<style data-illustrate-animation="true">(.*?)</style>', svg, re.S).group(1)
                self.assertIn("@media (prefers-reduced-motion: no-preference)", style)
                steps = set(export.STEP_RE.findall(svg))
                self.assertEqual(set(re.findall(r'\[data-step="(\d+)"\]\{animation-delay', style)), steps)

    def test_animation_is_the_only_addition_to_the_static_figure(self):
        html = (SKILL / "assets" / "template-motion.html").read_text(encoding="utf-8")
        static = export.DECORATIVE_RE.sub("", export.standalone_svg(html).replace(export.FONT_STYLE, ""))
        animated = re.sub(r'<style data-illustrate-animation="true">.*?</style>', "", export.animated_svg(html), flags=re.S)
        self.assertEqual(animated, static)

    def test_figures_without_steps_or_over_budget_are_refused(self):
        with self.assertRaises(export.ExportError):
            export.animated_svg('<svg viewBox="0 0 10 10"><rect width="10" height="10"/></svg>')
        slow = ('<style>:root{--motion-hold: 2000ms}</style><svg viewBox="0 0 10 10">'
                + "".join(f'<g data-motion-item data-step="{n}"><rect/></g>' for n in range(1, 6)) + "</svg>")
        with self.assertRaisesRegex(export.ExportError, "motion budget"):
            export.animated_svg(slow)

    def test_final_frame_equals_the_reduced_motion_frame(self):
        try:
            from playwright.sync_api import sync_playwright
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("Playwright and Pillow are needed for the rendered comparison")
        with tempfile.TemporaryDirectory() as tmp, sync_playwright() as playwright:
            browser = playwright.chromium.launch(args=["--disable-gpu", "--disable-lcd-text", "--force-color-profile=srgb", "--font-render-hinting=none"])
            try:
                for source in MOTION_SOURCES[:3]:
                    with self.subTest(source=source.name):
                        path = Path(tmp) / (source.stem + ".animated.svg")
                        path.write_text(export.animated_svg(source.read_text(encoding="utf-8")), encoding="utf-8")
                        shots = {}
                        for motion in ("no-preference", "reduce"):
                            page = browser.new_page(reduced_motion=motion, viewport={"width": 1200, "height": 900})
                            page.goto(path.as_uri())
                            page.wait_for_timeout(9000 if motion == "no-preference" else 1500)
                            shots[motion] = page.screenshot()
                            if motion == "no-preference":
                                page.goto(path.as_uri())
                                page.wait_for_timeout(100)
                                shots["start"] = page.screenshot()
                            page.close()
                        self.assertEqual(pixel_difference(shots["no-preference"], shots["reduce"]), None,
                                         "the reveal must end on the static figure")
                        self.assertIsNotNone(pixel_difference(shots["start"], shots["reduce"]),
                                             "the reveal must actually animate")
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
