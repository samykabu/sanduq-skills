"""Adversarial tests for the packaged self_check.py (ported from diagram-design, MIT)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _helpers import ASSETS, baseline, load

self_check = load("self_check.py")

# A minimal static diagram that satisfies the contract; Illustrate's legacy examples predate it.
STATIC = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>T</title>
  <link href="https://fonts.googleapis.com/css2?family=Geist:wght@400&display=swap" rel="stylesheet">
  <style>body { background: #f5f5f5; }</style>
</head>
<body>
<svg viewBox="0 0 100 50" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="t-title t-desc">
  <title id="t-title">Title</title><desc id="t-desc">Description.</desc>
  <rect x="1" y="1" width="60" height="40" fill="#f5f5f5"/>
</svg>
</body>
</html>
"""
TEMPLATE = ASSETS / "template-motion.html"
ANIMATED = ASSETS / "example-policy-trace-animated.html"


def verify(source: str) -> list[str]:
    with tempfile.TemporaryDirectory() as scratch:
        candidate = Path(scratch) / "candidate.html"
        candidate.write_text(source, encoding="utf-8")
        return self_check.verify(candidate)


class StaticContract(unittest.TestCase):
    def assertRejected(self, source: str, needle: str) -> None:
        errors = verify(source)
        self.assertTrue(any(needle in error for error in errors), f"wanted {needle!r} in {errors}")

    def test_static_passes(self):
        self.assertEqual(verify(STATIC), [])

    def test_css_looking_prose_passes(self):
        self.assertEqual(verify(STATIC.replace("<body>", "<body><p>Document @import and url(x).</p>", 1)), [])

    def test_rejections(self):
        cases = [
            ("<body>", '<body onload="fetch(1)">', "executable attribute"),
            ("<body>", '<body><img src="https://tracker.example/p.gif">', "remote reference"),
            ("</style>", '@import "https://tracker.example/t.css";</style>', "CSS @import"),
            ("</style>", ".t { background: url(https://tracker.example/p.gif); }</style>", "non-fragment CSS url()"),
            ("</style>", '@\\69mport "https://tracker.example/t.css";</style>', "CSS @import"),
            ("</style>", ".t { background: \\75rl(https\\3a //tracker.example/p.gif); }</style>", "non-fragment CSS url()"),
            ("</style>", '.t { background: image-set("https://t.example/p.gif" 1x); }</style>', "CSS image-set()"),
            ("<body>", '<body style="background:url(local.png)">', "non-fragment CSS url()"),
            ("</svg>", '<rect fill="url(https://t.example/p.svg#paint)"></rect></svg>', "non-fragment CSS url()"),
            ("<body>", '<body style="background:url(r.png)" style="background:none">', "non-fragment CSS url()"),
            ("</style>", '.t { content: "/*"; background: url(r.png); --x: "*/"; }</style>', "non-fragment CSS url()"),
            ("https://fonts.googleapis.com/css2", "https://fonts.googleapis.com.evil.tld/css2", "approved Google Fonts"),
            ("<body>", '<body><a href="javascript:alert(1)">x</a>', "executable URL"),
            ("<body>", '<body><a href="data:text/html,x">x</a>', "executable URL"),
            ("<body>", "<body><iframe></iframe>", "not allowed"),
            ("</body>", "<script>alert(1)</script></body>", "canonical data-diagram-controls attribute"),
            ('role="img"', 'role="presentation"', "role=img"),
            ('id="t-title"', 'id="title"', "diagram-prefixed"),
        ]
        for old, new, needle in cases:
            with self.subTest(needle=needle, new=new):
                self.assertRejected(STATIC.replace(old, new, 1), needle)

    def test_css_continuations_normalized(self):
        for newline in ("\n", "\r\n", "\r", "\f"):
            continuation = "\\" + newline
            normalized = self_check.normalize_css_escapes(
                f'url("https:{continuation}/{continuation}/tracker.example/p.gif")'
            )
            self.assertEqual(normalized, 'url("https://tracker.example/p.gif")')

    def test_theme_neutral(self):
        # Applied output (any theme's Google Fonts URL, no Fonts link at all) passes the same contract.
        cobalt = STATIC.replace(
            "css2?family=Geist:wght@400&display=swap", "css2?family=IBM+Plex+Sans:wght@400&display=swap"
        )
        self.assertEqual(verify(cobalt), [])
        self.assertEqual(verify(STATIC.replace(STATIC.splitlines()[5] + "\n", "")), [])


@unittest.skipUnless(TEMPLATE.is_file() and ANIMATED.is_file(), "motion template/example not shipped")
class MotionContract(unittest.TestCase):
    def test_shipped_motion_files_pass(self):
        self.assertEqual(self_check.verify(TEMPLATE), [])
        self.assertEqual(self_check.verify(ANIMATED), [])

    def test_motion_rejections(self):
        animated = ANIMATED.read_text(encoding="utf-8")
        cases = [
            (animated.replace("'motion-ready'", "'motion-ready' /* patched */", 1), "exactly match the controller"),
            (animated.replace("</body>", "<script data-x></script></body>", 1), "at most one script"),
            (
                animated.replace('<g data-motion-item data-step="1"', '<g style="opacity:0" data-motion-item data-step="1"', 1),
                "hidden in source",
            ),
            (animated.replace("<noscript>", "<div>", 1).replace("</noscript>", "</div>", 1), "<noscript>"),
            (animated.replace('data-step-count="5"', 'data-step-count="٥"', 1), "ASCII decimal"),
        ]
        for source, needle in cases:
            with self.subTest(needle=needle):
                errors = verify(source)
                self.assertTrue(any(needle in error for error in errors), f"wanted {needle!r} in {errors}")


def procedure_errors(path: Path) -> list[str]:
    """The check SKILL.md step 7 runs on a copy of this asset: the technical-color profile or --strict."""
    if "technical-color" in path.relative_to(ASSETS).parts:
        return self_check.verify(path, profile="technical-color")
    return self_check.verify(path, strict=True)


class ShippedAssets(unittest.TestCase):
    """Every shipped HTML asset passes the check the procedure requires; only the gallery pages are listed."""

    def test_assets_against_baseline(self):
        known = baseline("self-check-baseline.txt")
        paths = sorted(ASSETS.rglob("*.html"))
        self.assertGreater(len(paths), 290)
        failing = {path.relative_to(ASSETS).as_posix() for path in paths if procedure_errors(path)}
        self.assertEqual(sorted(failing - known), [], "new failures of the procedure's check (fix the file)")
        self.assertEqual(sorted(known - failing), [], "stale self-check-baseline.txt entries (remove them)")
        self.assertTrue(all(name in {"icons.html", "index.html"} or name.startswith("index-") for name in known),
                        "only gallery pages may be listed; templates and examples must pass")


TOOLBAR_TEMPLATE = ASSETS / "technical-color" / "architecture" / "templates" / "template.html"


def verify_profile(source: str, profile: str = "technical-color") -> list[str]:
    with tempfile.TemporaryDirectory() as scratch:
        candidate = Path(scratch) / "candidate.html"
        candidate.write_text(source, encoding="utf-8")
        return self_check.verify(candidate, profile=profile)


class TechnicalColorProfile(unittest.TestCase):
    """--profile technical-color allows exactly the pinned toolbar the family's references require."""

    def setUp(self):
        self.source = TOOLBAR_TEMPLATE.read_text(encoding="utf-8")

    def test_templates_pass_the_profile_and_fail_the_default(self):
        self.assertEqual(verify_profile(self.source), [])
        default = verify_profile(self.source, "editorial")
        self.assertTrue(any("onclick" in e for e in default), default)
        self.assertTrue(any("cdn.jsdelivr.net" in e for e in default), default)

    def test_theme_colour_and_download_name_may_differ(self):
        source = self.source.replace("backgroundColor: '#f8fafc'", "backgroundColor: '#020617'").replace(
            "'diagram.png'", "'web-app.png'").replace("'diagram.pdf'", "'web-app.pdf'")
        self.assertEqual(verify_profile(source), [])

    def test_anything_else_is_refused(self):
        cdn = "https://cdn.jsdelivr.net/npm/jspdf@2.5.2/dist/jspdf.umd.min.js"
        cases = [
            ("</head>", '<script src="https://cdn.jsdelivr.net/npm/x@1/x.js" integrity="sha384-x" '
             'crossorigin="anonymous"></script></head>', "remote reference on <script>"),
            (cdn, "https://cdn.jsdelivr.net/npm/jspdf@2.5.3/dist/jspdf.umd.min.js", "remote reference on <script>"),
            ("sha384-en/", "sha384-xx/", "remote reference on <script>"),
            ('jspdf.umd.min.js" integrity', 'jspdf.umd.min.js" data-x="1" integrity', "remote reference on <script>"),
            ('onclick="downloadPNG(this)"', 'onclick="fetch(1)"', "executable attribute onclick"),
            ('<div class="toolbar">', '<div class="toolbar" onmouseover="downloadPNG(this)">',
             "executable attribute onmouseover"),
            ("link.download = 'diagram.png';", "link.download = 'diagram.png'; fetch('https://t.example');",
             "must carry only the canonical"),
            ("</body>", "<script>alert(1)</script></body>", "must carry only the canonical"),
        ]
        for old, new, needle in cases:
            with self.subTest(needle=needle, new=new[:40]):
                self.assertIn(old, self.source)
                errors = verify_profile(self.source.replace(old, new, 1))
                self.assertTrue(any(needle in e for e in errors), f"wanted {needle!r} in {errors}")

    def test_a_second_copy_of_a_pinned_script_is_refused(self):
        line = next(item for item in self.source.splitlines() if "html2canvas.min.js" in item)
        errors = verify_profile(self.source.replace(line, line + "\n" + line, 1))
        self.assertTrue(any("once each" in e for e in errors), errors)

    def test_accessible_svg_contract_still_applies(self):
        errors = verify_profile(self.source.replace(' role="img"', "", 1))
        self.assertTrue(any("role=img" in e for e in errors), errors)


# A diagram that passes --strict: svg min-width = viewBox width, nodes on the 4px grid, one accent node,
# the legend strip below every node and inside the viewBox, fonts per role, an orthogonal connector.
STRICT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>T</title>
  <style>
    body { background: #f5f5f5; }
    .wrap { overflow-x: auto; box-shadow: none; }
    svg { width: 100%; min-width: 400px; display: block; }
    .node-name { font-family: 'Geist', sans-serif; }
    .sublabel { font-family: 'Geist Mono', monospace; }
    .focal { fill: rgba(235,108,54,0.08); stroke: #eb6c36; }
  </style>
</head>
<body>
<div class="wrap">
<svg viewBox="0 0 400 240" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="t-title t-desc">
  <title id="t-title">Title</title><desc id="t-desc">Description.</desc>
  <defs><marker id="t-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#4f5d75"/></marker></defs>
  <rect x="0" y="0" width="400" height="240" fill="#f5f5f5"/>
  <path d="M 200 92 H 240" fill="none" stroke="#4f5d75" marker-end="url(#t-arrow)"/>
  <rect x="40" y="60" width="160" height="64" rx="6" fill="#f5f5f5" stroke="#2d3142"/>
  <rect class="focal" x="240" y="60" width="120" height="64" rx="6"/>
  <text class="node-name" x="120" y="88">Name</text>
  <text class="sublabel" x="120" y="104">port 443</text>
  <g class="legend">
    <line x1="40" y1="168" x2="360" y2="168" stroke="#e0e0e0"/>
    <rect x="40" y="184" width="12" height="8" fill="#eb6c36"/>
    <text class="sublabel" x="60" y="192">Focal</text>
  </g>
</svg>
</div>
</body>
</html>
"""


def verify_strict(source: str) -> list[str]:
    with tempfile.TemporaryDirectory() as scratch:
        candidate = Path(scratch) / "candidate.html"
        candidate.write_text(source, encoding="utf-8")
        return self_check.verify(candidate, strict=True)


class StrictContract(unittest.TestCase):
    """--strict: the mechanical taste-gate boxes, one passing fixture and one failing edit per rule."""

    FAILING = [
        ("<text class=\"node-name\"", '<circle cx="80" cy="92" r="20" fill="#eb6c36"/><circle cx="160" cy="92" r="20" '
         'fill="#eb6c36"/><text class="node-name"', "accent is used on 3"),
        ('y1="168" x2="360" y2="168"', 'y1="100" x2="360" y2="100"', "legend starts"),
        ('viewBox="0 0 400 240"', 'viewBox="0 0 400 180"', "expand the viewBox"),
        ("min-width: 400px", "min-width: 360px", "does not equal the viewBox width"),
        ("min-width: 400px;", "", "no min-width on the svg"),
        ('<text class="node-name"', '<text style="writing-mode: vertical-rl" class="node-name"', "writing-mode"),
        ("box-shadow: none", "box-shadow: 0 1px 2px #cccccc", "box-shadow"),
        ('height="64" rx="6" fill="#f5f5f5"', 'height="64" rx="16" fill="#f5f5f5"', "rx=16"),
        ('<rect x="40" y="60"', '<rect x="42" y="60"', "off the 4px grid (x=42)"),
        (".node-name { font-family: 'Geist', sans-serif; }", ".node-name { font-family: 'Geist Mono', monospace; }",
         ".node-name must use the sans"),
        ('<text class="sublabel" x="120"', '<text class="sublabel" font-family="Instrument Serif, serif" x="120"',
         ".sublabel must use the mono"),
        ('stroke="#2d3142"', 'stroke="#000"', "pure-black"),
        ('d="M 200 92 H 240"', 'd="M 200 92 L 240 100"', "not orthogonal"),
        # the type exceptions hold only for their exact shapes
        ('d="M 200 92 H 240"', 'class="ring" d="M200 92 A240 180 0 0 1 240 100"', "not orthogonal"),
        ('d="M 200 92 H 240"', 'class="ring" d="M200 92 A240 240 0 0 0 240 100"', "not orthogonal"),
        ('d="M 200 92 H 240"', 'class="spoke" d="M200 92 L220 96 L240 100"', "not orthogonal"),
        ('d="M 200 92 H 240"', 'class="promotion" d="M 200,92 V 76 C 200,20 240,30 240,76 V 92"', "not orthogonal"),
        ('d="M 200 92 H 240"', 'd="M200 92 A240 240 0 0 1 240 100"', "not orthogonal"),
    ]

    def test_strict_fixture_passes(self):
        self.assertEqual(verify(STRICT), [])
        self.assertEqual(verify_strict(STRICT), [])

    def test_each_rule_fails_strict_only(self):
        for old, new, needle in self.FAILING:
            with self.subTest(needle=needle):
                self.assertEqual(STRICT.count(old), 1, old)
                source = STRICT.replace(old, new, 1)
                errors = verify_strict(source)
                self.assertTrue(any(needle in error for error in errors), f"wanted {needle!r} in {errors}")
                self.assertEqual(verify(source), [], "the default run must not change")

    def test_documented_exceptions_pass(self):
        cases = [
            # a full pill is a terminator, not a rounded box
            ('height="64" rx="6" fill="#f5f5f5"', 'height="64" rx="32" fill="#f5f5f5"'),
            # data-bound rects (bars, cells) are positioned by their value, off the grid by design
            ('<rect x="40" y="60"', '<rect data-value="42" x="42" y="60"'),
            # .5 offsets keep 1px strokes crisp
            ('<rect x="40" y="60"', '<rect x="40.5" y="60.5"'),
            # accent on the headline connector, on series dots and on aria-hidden decoration does not count
            ('stroke="#4f5d75" marker-end', 'stroke="#eb6c36" marker-end'),
            ('<text class="node-name"', '<circle cx="80" cy="140" r="4" fill="#eb6c36"/><circle cx="96" cy="140" r="4" '
             'fill="#eb6c36"/><circle aria-hidden="true" cx="120" cy="92" r="24" fill="#eb6c36"/><text class="node-name"'),
            # a comment that names a banned property is not a declaration
            ("<g class=\"legend\">", "<!-- never writing-mode --><g class=\"legend\">"),
            # a rounded elbow is orthogonal
            ('d="M 200 92 H 240"', 'd="M 200 92 H 212 Q 220 92 220 100 V 108 Q 220 116 228 116 H 240"'),
            # the documented type exceptions to rule 1: a Loop ring arc and spoke, a Medallion promotion arc
            ('d="M 200 92 H 240"', 'class="ring" d="M200 92 A240 240 0 0 1 240 100"'),
            ('d="M 200 92 H 240"', 'class="spoke" d="M200 92 L240 100"'),
            ('d="M 200 92 H 240"', 'class="promotion" d="M 200,92 V 76 C 200,20 240,20 240,76 V 92"'),
        ]
        for old, new in cases:
            with self.subTest(new=new):
                self.assertEqual(verify_strict(STRICT.replace(old, new, 1)), [])

    def test_terminal_variant_is_mono(self):
        source = STRICT.replace('<div class="wrap">', '<div class="wrap terminal">', 1).replace(
            ".node-name { font-family: 'Geist', sans-serif; }", ".node-name { font-family: 'Geist Mono', monospace; }", 1
        )
        self.assertEqual(verify_strict(source), [])

    def test_lint_skin_shares_the_skin_checks(self):
        lint_skin = load("lint-skin.py")
        self.assertIs(lint_skin.HEX_RE, self_check.HEX_RE)
        self.assertIs(lint_skin.normalize_hex, self_check.normalize_hex)
        categories = {f[1] for f in self_check.skin_findings('<rect fill="#000"/><script>x</script><img src="https://t.example/p.gif">')}
        self.assertEqual(categories, {"pure-black", "script", "external-asset"})


if __name__ == "__main__":
    unittest.main()
