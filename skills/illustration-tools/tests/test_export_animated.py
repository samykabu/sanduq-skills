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


ARROW_STYLES = ("draw", "flow", "pulse", "draw-flow", "chevrons")
ARROW_SVG = (
    '<svg viewBox="0 0 300 120"><defs><marker id="h" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8"'
    ' markerHeight="8" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z"/></marker></defs>'
    '<path d="M 20 60 H 130" stroke="#333" stroke-width="2" fill="none" marker-end="url(#h)"/>'
    '<line x1="280" y1="30" x2="170" y2="30" stroke="#333" stroke-width="2" marker-start="url(#h)"/>'
    '<path d="M 170 90 H 280" stroke="#333" stroke-width="2" fill="none" marker-start="url(#h)" marker-end="url(#h)"/>'
    '</svg>'
)


def strip_animation(svg):
    """The animated SVG minus everything the animation adds: style block, overlays, travellers, tags."""
    svg = re.sub(r'<style data-illustrate-animation="true">.*?</style>', "", svg, flags=re.S)
    svg = re.sub(r'<(\w+)[^>]*\sclass="ia-[^"]*"[^>]*/>', "", svg)
    svg = re.sub(r'<g transform="[^"]*"></g>', "", svg)
    return re.sub(r' data-ia="\d+"', "", svg)


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
        for style in ARROW_STYLES:
            with self.subTest(arrows=style):
                animated = strip_animation(export.animated_svg(html, style))
                self.assertEqual(animated, static)

    def test_figures_without_steps_or_arrows_or_over_budget_are_refused(self):
        with self.assertRaises(export.ExportError):
            export.animated_svg('<svg viewBox="0 0 10 10"><rect width="10" height="10"/></svg>')
        with self.assertRaises(export.ExportError):
            export.animated_svg(ARROW_SVG, "sideways")
        slow = ('<style>:root{--motion-hold: 2000ms}</style><svg viewBox="0 0 10 10">'
                + "".join(f'<g data-motion-item data-step="{n}"><rect/></g>' for n in range(1, 6)) + "</svg>")
        with self.assertRaisesRegex(export.ExportError, "motion budget"):
            export.animated_svg(slow)

    def test_arrow_styles_follow_each_arrow_direction(self):
        svg = export.animated_svg(ARROW_SVG, "draw")
        ET.fromstring(svg.encode("utf-8"))
        self.assertIn(".ia-draw.ia-a0{animation:ia-draw-fwd", svg)   # marker-end: source to tip
        self.assertIn(".ia-draw.ia-a1{animation:ia-draw-rev", svg)   # marker-start only: drawn toward the start
        self.assertIn(".ia-draw.ia-a2{animation:ia-draw-both", svg)  # two-headed: middle out
        self.assertEqual(svg.count('class="ia-draw'), 3)
        self.assertIn("offset-path:path('M 280 30 L 170 30')", export.animated_svg(ARROW_SVG, "pulse"))  # lines ride their own path
        chevrons = export.animated_svg(ARROW_SVG, "chevrons")
        self.assertEqual(chevrons.count("ia-chev ia-fwd"), 3 + 1)    # one-headed: 3, two-headed: 1 each way
        self.assertEqual(chevrons.count("ia-chev ia-rev"), 3 + 1)
        for style in ARROW_STYLES:
            with self.subTest(arrows=style):
                svg = export.animated_svg(ARROW_SVG, style)
                ET.fromstring(svg.encode("utf-8"))
                motion = svg.split("@media (prefers-reduced-motion: no-preference){", 1)[1]
                self.assertNotIn("<script", svg)
                self.assertIn("animation", motion)

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


class ArrowRenderTests(unittest.TestCase):
    """Rendered checks for arrow animation on an ordinary (step-less) diagram, and for GIF export."""

    def setUp(self):
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("Playwright and Pillow are needed for rendered checks")

    def test_draw_style_ends_on_the_static_figure(self):
        from playwright.sync_api import sync_playwright
        html = (SKILL / "assets" / "example-state.html").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp, sync_playwright() as playwright:
            path = Path(tmp) / "state.animated.svg"
            path.write_text(export.animated_svg(html, "draw"), encoding="utf-8")
            browser = playwright.chromium.launch()
            try:
                shots = {}
                for motion, wait in (("no-preference", 6000), ("reduce", 1500)):
                    page = browser.new_page(reduced_motion=motion, viewport={"width": 1200, "height": 900})
                    page.goto(path.as_uri())
                    page.wait_for_timeout(wait)
                    shots[motion] = page.screenshot()
                    page.close()
            finally:
                browser.close()
        self.assertIsNone(pixel_difference(shots["no-preference"], shots["reduce"]))

    def test_gif_has_motion_and_ends_on_the_static_figure(self):
        import io
        from PIL import Image, ImageSequence
        from playwright.sync_api import sync_playwright
        figure, intro = export.animated_figure(ARROW_SVG, "draw")
        total, hold = export.animate_export.timeline("draw", intro)
        with tempfile.TemporaryDirectory() as tmp:
            gif = Path(tmp) / "arrows.gif"
            count = export.animate_export.render_gif(figure, gif, total, hold, fps=10)
            frames = [frame.convert("RGB") for frame in ImageSequence.Iterator(Image.open(gif))]
            self.assertLessEqual(len(frames), count)  # Pillow merges identical consecutive frames
            self.assertGreater(len(frames), 5)
            static = Path(tmp) / "static.svg"
            static.write_text(export.standalone_svg(ARROW_SVG), encoding="utf-8")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    page = browser.new_page(viewport={"width": 300, "height": 120})
                    page.goto(static.as_uri())
                    reference = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
                finally:
                    browser.close()

            def png(image):
                buffer = io.BytesIO()
                image.save(buffer, "PNG")
                return buffer.getvalue()

            self.assertIsNone(pixel_difference(png(frames[-1]), png(reference)), "the GIF must end on the static figure")
            self.assertIsNotNone(pixel_difference(png(frames[0]), png(reference)), "the GIF must animate")
