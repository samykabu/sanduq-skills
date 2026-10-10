"""SVG export carries the page CSS the figure depends on: classes and custom properties styled in <head>."""
import importlib.util
import io
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "illustrate"
spec = importlib.util.spec_from_file_location("export_diagram", SKILL / "scripts" / "export_diagram.py")
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)

SOURCES = sorted([*(SKILL / "assets").glob("example-*.html"), *(SKILL / "assets").glob("template*.html")])
# Figures whose shapes are styled only by page classes and tokens: black boxes before the fix.
PAGE_STYLED = ["example-process.html", "example-loop.html", "example-policy-trace-animated.html"]
CLASS_RE = r"\.{}(?![\w-])"
STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style\s*>", re.IGNORECASE | re.DOTALL)


def exports(html):
    """Every SVG the exporter writes for this source: static, and animated when the figure animates."""
    yield "svg", export.standalone_svg(html)
    try:
        yield "animated", export.animated_svg(html)
    except export.ExportError:
        pass


def figure_css(svg):
    return "".join(STYLE_RE.findall(svg))


class PageStyleExportTests(unittest.TestCase):
    def test_every_export_is_the_whole_figure_as_xml(self):
        # Nested <svg> icons once cut the figure at the first </svg>; "--" inside an HTML comment is not XML.
        for source in SOURCES:
            html = source.read_text(encoding="utf-8")
            for mode, svg in exports(html):
                with self.subTest(source=source.name, mode=mode):
                    root = ET.fromstring(svg.encode("utf-8"))
                    self.assertEqual(len(root.findall(".//{http://www.w3.org/2000/svg}svg")), html.count("<svg") - 1)

    def test_every_custom_property_the_figure_uses_is_defined_in_the_svg(self):
        for source in SOURCES:
            html = source.read_text(encoding="utf-8")
            for mode, svg in exports(html):
                with self.subTest(source=source.name, mode=mode):
                    defined = set(re.findall(r"(--[\w-]+)\s*:", figure_css(svg)))
                    used = set(re.findall(r"var\(\s*(--[\w-]+)\s*\)", svg))
                    self.assertEqual(used - defined, set())

    def test_every_page_class_the_figure_uses_is_styled_in_the_svg(self):
        for source in SOURCES:
            html = source.read_text(encoding="utf-8")
            figure = export.SVG_RE.search(html)
            page = "".join(STYLE_RE.findall(html[: figure.start()] + html[figure.end() :]))
            selectors = [s for block in re.findall(r"([^{}]+)\{", page) for s in block.split(",") if "motion" not in s]
            classes = set(" ".join(re.findall(r'\bclass="([^"]*)"', figure.group(0))).split())
            styled = {c for c in classes if any(re.search(CLASS_RE.format(re.escape(c)), s) for s in selectors)}
            for mode, svg in exports(html):
                with self.subTest(source=source.name, mode=mode):
                    css = figure_css(svg)
                    self.assertEqual({c for c in styled if not re.search(CLASS_RE.format(re.escape(c)), css)}, set())

    def test_page_rules_keep_tokens_and_drop_layout_motion_and_fetches(self):
        html = (
            "<style>@import url('x.css');@font-face{font-family:F;src:url(f.woff2)}"
            "html,body{display:flex;min-height:100vh;color:#123;--ink:#111;font-family:Geist}"
            "svg{width:100%;min-width:900px}.frame{max-width:1000px}"
            "@media (prefers-color-scheme: dark){:root{--ink:#eee}}@keyframes spin{to{opacity:0}}"
            ".node{fill:var(--ink);animation:spin 1s;transition:fill 1s}"
            "[data-motion-item]{transform:none!important}.motion-ready .node{opacity:0}"
            ".label::after{content:'a<b & c'}</style>"
            '<svg viewBox="0 0 10 10"><rect class="node" width="10" height="10"/></svg>'
        )
        svg = export.standalone_svg(html)
        ET.fromstring(svg.encode("utf-8"))
        css = re.search(r'<style data-illustrate-export-page="true">(.*?)</style>', svg, re.S).group(1)
        self.assertIn(":root{color:#123;--ink:#111;font-family:Geist}", css)
        self.assertIn("@media (prefers-color-scheme: dark){:root{--ink:#eee}}", css)
        self.assertIn(".node{fill:var(--ink)}", css)
        self.assertIn("a&lt;b &amp; c", css)
        for absent in ("@import", "@font-face", "@keyframes", "display:flex", "min-width", "min-height",
                       "animation", "transition", "data-motion", "motion-ready"):
            self.assertNotIn(absent, css)
        self.assertNotIn("@import", export.animated_svg(html.replace("<rect", '<rect data-motion-item data-step="1"')))

    def test_page_styled_figures_render_without_fallback_black(self):
        try:
            from PIL import Image
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Playwright and Pillow are needed for the rendered comparison")

        def black_share(png):
            image = Image.open(io.BytesIO(png)).convert("L")
            return image.point(lambda value: 255 if value < 24 else 0).histogram()[255] / (image.width * image.height)

        with tempfile.TemporaryDirectory() as tmp, sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                for name in PAGE_STYLED:
                    source = SKILL / "assets" / name
                    page = browser.new_page(reduced_motion="reduce", viewport={"width": 1400, "height": 1000})
                    page.goto(source.as_uri())
                    figure = page.locator("svg").first
                    box = figure.bounding_box()
                    reference = black_share(figure.screenshot())
                    page.close()
                    for mode, svg in exports(source.read_text(encoding="utf-8")):
                        with self.subTest(source=name, mode=mode):
                            image = Path(tmp) / f"{source.stem}.{mode}.svg"
                            image.write_text(svg, encoding="utf-8")
                            wrapper = image.with_suffix(".html")
                            wrapper.write_text(f'<body style="margin:0"><img src="{image.name}" style="display:block;'
                                               f'width:{box["width"]}px;height:{box["height"]}px"></body>', encoding="utf-8")
                            page = browser.new_page(reduced_motion="reduce", viewport={"width": 1400, "height": 1000})
                            page.goto(wrapper.as_uri())
                            page.wait_for_timeout(200)
                            share = black_share(page.locator("img").screenshot())
                            page.close()
                            self.assertLessEqual(share, reference + 0.02, "shapes fell back to the SVG default black")
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
