"""Standalone SVG export: live markup, XML safety, unique defs, paint, fonts (ported diagram-design fixes)."""
import importlib.util
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from _helpers import run_cli

SKILL = Path(__file__).resolve().parents[1] / "skills" / "illustrate"
spec = importlib.util.spec_from_file_location("export_diagram", SKILL / "scripts" / "export_diagram.py")
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)

NS = {"s": "http://www.w3.org/2000/svg"}


def svg_of(body, head="", opening='<svg viewBox="0 0 100 50">', source=None, **options):
    html = f"<!doctype html><html><head>{head}</head><body>{opening}{body}</svg></body></html>"
    return export.standalone_svg(html, source, **options)


def parse(svg):
    return ET.fromstring(svg.encode("utf-8"))


def page_css(svg):
    match = re.search(r'<style data-illustrate-export-page="true">(.*?)</style>', svg, re.S)
    return match.group(1) if match else ""


class LiveMarkupTests(unittest.TestCase):
    def test_commented_scripted_and_text_svg_is_not_the_figure(self):
        html = (
            '<!-- <svg viewBox="0 0 1 1"><rect id="old"/></svg> -->'
            '<script>const icon = "<svg viewBox=\'0 0 2 2\'></svg>";</script>'
            '<textarea><svg viewBox="0 0 3 3"></svg></textarea>'
            '<svg viewBox="0 0 100 50" data-label="a/>b"><rect id="live" width="10" height="10"/></svg>'
        )
        root = parse(export.standalone_svg(html))
        self.assertEqual(root.get("viewBox"), "0 0 100 50")
        self.assertEqual(root.find("s:rect", NS).get("id"), "live")

    def test_nested_icons_stay_inside_and_comments_are_dropped(self):
        svg = svg_of('<!-- a -- b --><g><svg viewBox="0 0 4 4"><rect/></svg><rect id="after"/></g>')
        root = parse(svg)
        self.assertEqual(len(root.findall(".//s:svg", NS)), 1)
        self.assertIsNotNone(root.find(".//s:rect[@id='after']", NS))
        self.assertNotIn("<!--", svg)

    def test_comments_a_browser_closes_early_are_refused(self):
        for comment in ("<!--><rect/>-->", "<!---><rect/>-->", "<!-- x --!><rect/>-->"):
            with self.subTest(comment=comment), self.assertRaisesRegex(export.ExportError, "closes early"):
                svg_of(comment)

    def test_only_live_page_styles_are_carried(self):
        head = ("<!-- <style>.node{fill:red}</style> -->"
                "<script>const css = '<style>.node{fill:blue}</style>';</script>"
                "<style>.node{fill:green}</style>")
        svg = svg_of('<rect class="node"/>', head)
        css = page_css(svg)
        self.assertIn(".node" + page_guard(svg) + "{fill:green}", css)
        self.assertNotIn("red", css)
        self.assertNotIn("blue", css)

    def test_page_style_cdata_in_another_svg_is_unwrapped(self):
        html = ('<svg viewBox="0 0 10 10"><rect class="a" width="10" height="10"/></svg>'
                '<svg width="0" height="0"><style><![CDATA[.a{fill:#123456}]]></style></svg>')
        svg = export.standalone_svg(html)
        css = page_css(svg)
        self.assertIn(".a" + page_guard(svg) + "{fill:#123456}", css)
        self.assertNotIn("CDATA", css)

    def test_figure_cdata_is_kept_verbatim(self):
        svg = svg_of('<style><![CDATA[ .a > .b { fill: #f00 } /* <!-- x --> */ ]]></style><g class="a"><rect class="b"/></g>')
        parse(svg)
        self.assertIn("<![CDATA[ .a > .b { fill: #f00 } /* <!-- x --> */ ]]>", svg)


class XmlSyntaxTests(unittest.TestCase):
    def test_html_attributes_become_xml(self):
        root = parse(svg_of('<g data-motion-item data-step=1><rect/></g>'))
        group = root.find("s:g", NS)
        self.assertEqual(group.get("data-motion-item"), "")
        self.assertEqual(group.get("data-step"), "1")

    def test_label_character_references_keep_their_html_meaning(self):
        root = parse(svg_of("<text>A&nbsp;&rarr;&#128;&amp;&lt;B&notit</text>"
                            '<text aria-label="x&nbsp;y &amp; z">t</text>'))
        texts = root.findall("s:text", NS)
        self.assertEqual(texts[0].text, "A →€&<B¬it")
        self.assertEqual(texts[1].get("aria-label"), "x y & z")

    def test_namespace_is_checked_and_xlink_declared(self):
        svg = svg_of('<defs><path id="p" d="M0 0h1"/></defs><use xlink:href="#p"/>')
        self.assertIn('xmlns:xlink="http://www.w3.org/1999/xlink"', svg)
        use = parse(svg).find("s:use", NS)
        self.assertTrue(use.get("{http://www.w3.org/1999/xlink}href").endswith("-p"))
        with self.assertRaisesRegex(export.ExportError, "xmlns"):
            svg_of("<rect/>", opening='<svg xmlns="http://example.com/not-svg" viewBox="0 0 10 10">')
        with self.assertRaisesRegex(export.ExportError, "xmlns:xlink"):
            svg_of("<rect/>", opening='<svg xmlns:xlink="http://example.com" viewBox="0 0 10 10">')

    def test_root_viewbox_must_be_positive_and_finite(self):
        for box in ("0 0 0 10", "0 0 10 -4", "0 0 1e999 10", "0 0 10", "a b c d", "0 0 NaN 10"):
            with self.subTest(viewBox=box), self.assertRaises(export.ExportError):
                svg_of("<rect/>", opening=f'<svg viewBox="{box}">')
        with self.assertRaisesRegex(export.ExportError, "no viewBox"):
            svg_of("<rect/>", opening="<svg>")
        parse(svg_of("<rect/>", opening='<svg viewBox="0,0,10.5,4e1">'))

    def test_title_and_desc_stay_before_new_defs(self):
        root = parse(svg_of("<title>T</title><desc>D</desc><rect/>"))
        self.assertEqual([child.tag.split("}")[1] for child in root][:3], ["title", "desc", "defs"])


class DefsIdTests(unittest.TestCase):
    BODY = (
        '<title id="t">T</title><defs>'
        '<marker id="arrow"><path d="M0 0L4 2"/></marker>'
        '<linearGradient id="g:1"><stop offset="0"/></linearGradient>'
        '<symbol id="s"><rect/></symbol></defs>'
        '<path class="edge" d="M0 0H9" marker-end="url(#arrow)"/>'
        '<rect fill="url(\'#g:1\')" stroke="url(&quot;#g:1&quot;)"/>'
        '<rect style="fill:url(#g\\:1)"/>'
        '<use href="#s"/><use xlink:href="#s"/>'
        '<rect id="outside" fill="url(#missing)"/>'
        '<set attributeName="fill" to="url(#g:1)"/>'
        '<text>url(#arrow) is text</text>'
    )
    HEAD = "<style>.edge{marker-end:url(#arrow)}#arrow path{fill:#333}.label::after{content:'url(#arrow)'}</style>"

    def test_defs_ids_and_every_reference_are_prefixed_per_file(self):
        svg = svg_of(self.BODY, self.HEAD, source=Path("flow chart.html"))
        root = parse(svg)
        self.assertEqual({e.get("id") for e in root.iter() if e.get("id")},
                         {"t", "flow-chart-arrow", "flow-chart-g:1", "flow-chart-s", "outside"})
        for expected in ('marker-end="url(#flow-chart-arrow)"', "fill=\"url('#flow-chart-g:1')\"",
                         'stroke="url(&quot;#flow-chart-g:1&quot;)"', 'style="fill:url(#flow-chart-g\\:1)"',
                         'href="#flow-chart-s"', 'xlink:href="#flow-chart-s"', 'fill="url(#missing)"',
                         'to="url(#flow-chart-g:1)"', "<text>url(#arrow) is text</text>"):
            self.assertIn(expected, svg)
        css = page_css(svg)
        self.assertIn(".edge" + page_guard(svg) + "{marker-end:url(#flow-chart-arrow)}", css)
        self.assertIn("#flow-chart-arrow path" + page_guard(svg) + "{fill:#333}", css)
        self.assertIn("content:'url(#arrow)'", css)  # a CSS string is not a reference

    def test_two_inline_figures_do_not_share_defs_ids(self):
        first = parse(svg_of(self.BODY, source=Path("a.html")))
        second = parse(svg_of(self.BODY, source=Path("b.html")))
        ids = lambda root: {e.get("id") for e in root.iter() if e.tag.endswith(("marker", "linearGradient", "symbol"))}
        self.assertFalse(ids(first) & ids(second))

    def test_already_prefixed_ids_are_left_alone(self):
        svg = svg_of('<defs><marker id="flow-arrow"/></defs><path marker-end="url(#flow-arrow)"/>', source=Path("flow.html"))
        self.assertIn('id="flow-arrow"', svg)
        self.assertNotIn("flow-flow-", svg)


def get_scope(svg: str) -> str:
    return f'[data-illustrate-export="{parse(svg).get("data-illustrate-export")}"]'


def page_guard(svg: str) -> str:
    scope = get_scope(svg)
    return f":where({scope},{scope} *)"


class PageCssTests(unittest.TestCase):
    def test_inert_nested_template_preview_is_not_selected_as_a_figure(self):
        html = ('<template id="preview"><template><style>.label{fill:red}</style>'
                '<svg viewBox="0 0 20 20"><title>Hidden</title></svg></template></template>'
                '<svg viewBox="0 0 10 10"><title>Live</title><rect class="label"/></svg>')
        svg = export.standalone_svg(html, system_fonts=True)
        self.assertEqual(list(parse(svg))[0].text, "Live")
        self.assertNotIn("fill:red", svg)

    def test_quoted_comment_text_and_escaped_selectors_survive(self):
        head = r"<style>/* gone */.label::after{content:'/* kept */'}.a\,b{fill:#123}[data-x='{;}']{stroke:#456}</style>"
        svg = svg_of('<rect class="label"/>', head)
        css = page_css(svg)
        guard = page_guard(svg)
        self.assertNotIn("gone", css)
        self.assertIn("content:'/* kept */'", css)
        self.assertIn(r".a\,b" + guard + "{fill:#123}", css)
        self.assertIn("[data-x='{;}']" + guard + "{stroke:#456}", css)

    def test_print_rules_stay_print_only(self):
        head = ("<style>@media print{.diagram-container{overflow-x:visible}svg{min-width:0;color:#000}"
                ".node{fill:#f00}}.node{fill:#0f0}</style>")
        svg = svg_of('<rect class="node"/>', head)
        css = page_css(svg)
        guard = page_guard(svg)
        self.assertEqual(css, "@media print{.diagram-container" + guard + "{overflow-x:visible}svg" + guard
                              + "{color:#000}.node" + guard + "{fill:#f00}}.node" + guard + "{fill:#0f0}")

    def test_ancestor_rules_still_move_to_root(self):
        head = "<style>body{display:grid;color:#123;--ink:#111}.frame{max-width:900px}.node{fill:var(--ink)}</style>"
        svg = svg_of('<rect class="node"/>', head)
        css = page_css(svg)
        self.assertIn(get_scope(svg) + "{color:#123;--ink:#111}", css)
        self.assertNotIn("display:grid", css)


class PowerPointPaintTests(unittest.TestCase):
    def test_rgba_and_transparent_paint_are_split_where_safe(self):
        # Separate figures: any other fill-opacity in a figure could be inherited, which keeps rgba.
        rect = {}
        for markup in ('<rect id="a" fill="rgba(1,2,3,0.5)"/><rect id="c" fill="transparent" stroke="rgba(0,0,0,2)"/>'
                       '<g id="d" fill="rgba(1,2,3,0.5)"><rect fill="#fff"/></g>',
                       '<rect id="b" fill="rgba(300,-4,16,0.5)" fill-opacity="0.5"/>'):
            rect.update({e.get("id"): e for e in parse(svg_of(markup)).iter() if e.get("id")})
        self.assertEqual((rect["a"].get("fill"), rect["a"].get("fill-opacity")), ("#010203", "0.5"))
        self.assertEqual((rect["b"].get("fill"), rect["b"].get("fill-opacity")), ("#ff0010", "0.25"))
        self.assertEqual((rect["c"].get("fill"), rect["c"].get("stroke-opacity")), ("none", "1"))
        self.assertEqual(rect["d"].get("fill"), "rgba(1,2,3,0.5)")  # a child overrides the paint

    def test_unrelated_page_selectors_do_not_prevent_paint_normalization(self):
        svg = svg_of('<rect class="mark" fill="rgba(1,2,3,0.5)"/>', "<style>.other{fill:red}</style>")
        self.assertIn('fill="#010203" fill-opacity="0.5"', svg)

    def test_css_opacity_keeps_rgba(self):
        svg = svg_of('<rect class="x" fill="rgba(1,2,3,0.5)"/>', "<style>.x{fill-opacity:.2}</style>")
        self.assertIn('fill="rgba(1,2,3,0.5)"', svg)


class FontTests(unittest.TestCase):
    PLEX = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500&amp;"
            "family=Noto+Sans+Arabic:wght@400&amp;display=swap")

    def test_the_page_theme_fonts_are_imported(self):
        svg = svg_of("<rect/>", f'<link href="{self.PLEX}" rel="stylesheet">')
        self.assertIn("family=IBM+Plex+Sans:wght@400;500&amp;family=Noto+Sans+Arabic", svg)
        self.assertNotIn("Instrument+Serif", svg)
        parse(svg)

    def test_sample_default_and_no_foreign_imports(self):
        self.assertIn(export.FONT_STYLE, svg_of("<rect/>"))
        svg = svg_of("<rect/>", '<link href="https://example.com/fonts.css" rel="stylesheet">')
        self.assertNotIn("example.com", svg)
        self.assertIn(export.FONT_STYLE, svg)

    def test_authored_font_mode_stays_offline_without_cli_override(self):
        for mode in ("local", "system"):
            with self.subTest(mode=mode):
                svg = svg_of("<rect/>", f'<meta name="illustration-theme" content="cobalt/light/{mode}">')
                self.assertNotIn("fonts.googleapis.com", svg)
        comment_mode = '<!-- <meta name="illustration-theme" content="cobalt/light/local"> -->'
        self.assertIn(export.FONT_STYLE, svg_of("<rect/>", comment_mode))

    def test_system_fonts_make_no_request(self):
        svg = svg_of("<rect/>", f'<link href="{self.PLEX}" rel="stylesheet"><style>@import url("x.css");</style>',
                     system_fonts=True)
        self.assertNotIn("@import", svg)
        self.assertNotIn("googleapis", svg)


class CliTests(unittest.TestCase):
    def write(self, folder, name, body='<rect width="10" height="10"/>'):
        path = Path(folder) / name
        path.write_text(f'<!doctype html><svg viewBox="0 0 40 20">{body}</svg>', encoding="utf-8")
        return path

    def test_scale_must_be_a_finite_number_from_1_to_4(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.write(tmp, "d.html")
            for scale in ("0.5", "4.01", "nan", "inf", "two"):
                with self.subTest(scale=scale):
                    code, out = run_cli("export_diagram.py", source, "--svg-only", "--scale", scale)
                    self.assertEqual(code, 2)
                    self.assertIn("scale", out)
            code, out = run_cli("export_diagram.py", source, "--gif", "--scale", "1.5")
            self.assertEqual(code, 2)
            self.assertIn("--gif renders at --scale 1, 2 or 3", out)

    def test_svg_only_keeps_output_names_and_reports_write_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.write(tmp, "name #1 100%.html")
            code, out = run_cli("export_diagram.py", source, "--svg-only", "--system-fonts")
            self.assertEqual(code, 0, out)
            written = Path(tmp) / "name #1 100%.svg"
            self.assertIn(f"{written.resolve()} (", out)
            self.assertNotIn("@import", written.read_text(encoding="utf-8"))
            blocker = Path(tmp) / "file"
            blocker.write_text("x", encoding="utf-8")
            code, out = run_cli("export_diagram.py", source, "--svg-only", "--output", blocker / "out")
            self.assertEqual(code, 2)
            self.assertIn("Cannot write", out)


if __name__ == "__main__":
    unittest.main()
