"""Tests for verify-arrow-ends.py: arrows must be straight for their arrowhead's length before each tip."""

from __future__ import annotations

import io
import math
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from _helpers import ASSETS, load

arrows = load("verify-arrow-ends.py")
self_check = load("self_check.py")

# --- direction sheet fixtures: arrows in every direction, one- and two-headed, curved and cornered ---

LEAD = 16  # straight stretch the fixed geometry keeps before each tip
MARKER = (
    '<marker id="h" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
    'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z"/></marker>'
)


def fmt(*pts):
    return ", ".join(f"{x:g} {y:g}" for x, y in pts)


def curve(p0, p3, d0, d3, bulge, fixed):
    """A loop from p0 leaving along d0 to p3 arriving along d3, bulging by `bulge` along d0."""
    if not fixed:  # the bug: the curve is still turning right up to the tips
        c1 = (p0[0] + d0[0] * bulge, p0[1] + d0[1] * bulge)
        c2 = (p3[0] - d3[0] * bulge, p3[1] - d3[1] * bulge)
        return f"M {fmt(p0)} C {fmt(c1, c2, p3)}"
    a = (p0[0] + d0[0] * LEAD, p0[1] + d0[1] * LEAD)
    b = (p3[0] - d3[0] * LEAD, p3[1] - d3[1] * LEAD)
    c1 = (a[0] + d0[0] * (bulge - LEAD), a[1] + d0[1] * (bulge - LEAD))
    c2 = (b[0] - d3[0] * (bulge - LEAD), b[1] - d3[1] * (bulge - LEAD))
    return f"M {fmt(p0)} L {fmt(a)} C {fmt(c1, c2, b)} L {fmt(p3)}"


def elbow(p0, p3, fixed, r=8):
    """Horizontal, vertical, horizontal; the fix finishes the last corner LEAD before the tip."""
    (x0, y0), (x3, y3) = p0, p3
    sx = 1 if x3 > x0 else -1
    sy = 1 if y3 > y0 else -1
    trunk = x3 - sx * (r + (LEAD if fixed else 4))
    return (f"M {x0} {y0} H {trunk - sx * r} Q {trunk} {y0} {trunk} {y0 + sy * r} "
            f"V {y3 - sy * r} Q {trunk} {y3} {trunk + sx * r} {y3} H {x3}")


def vertical_elbow(p0, p3, fixed, r=8):
    (x0, y0), (x3, y3) = p0, p3
    sx = 1 if x3 > x0 else -1
    sy = 1 if y3 > y0 else -1
    trunk = y3 - sy * (r + (LEAD if fixed else 4))
    return (f"M {x0} {y0} V {trunk - sy * r} Q {x0} {trunk} {x0 + sx * r} {trunk} "
            f"H {x3 - sx * r} Q {x3} {trunk} {x3} {trunk + sy * r} V {y3}")


def cases(fixed):
    """(label, d, two_headed) for the 12 cells of the direction sheet."""
    out = []
    curves = [
        ("arrives down", (170, 110), (50, 110), (0, -1), (0, 1), 80),
        ("arrives up", (50, 40), (170, 40), (0, 1), (0, -1), 80),
        ("arrives right", (70, 120), (140, 30), (-1, 0), (1, 0), 60),
        ("arrives left", (150, 30), (80, 120), (1, 0), (-1, 0), 60),
    ]
    for two in (False, True):
        for name, p0, p3, d0, d3, bulge in curves:
            out.append((("two-headed " if two else "") + name, curve(p0, p3, d0, d3, bulge, fixed), two))
    out.append(("corners, enters right", elbow((70, 30), (150, 140), fixed), False))
    out.append(("corners, enters left", elbow((150, 30), (70, 140), fixed), False))
    out.append(("corners, enters down, two-headed", vertical_elbow((50, 40), (170, 120), fixed), True))
    out.append(("corners, enters up, two-headed", vertical_elbow((170, 130), (50, 50), fixed), True))
    return out


def sheet(d, two_headed=False, extra="", width="1.6", marker=MARKER):
    start = ' marker-start="url(#h)"' if two_headed else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg"><defs>{marker}</defs>{extra}'
            f'<path d="{d}" fill="none" stroke-width="{width}" marker-end="url(#h)"{start}/></svg>')


# --- tests ---

class Parser(unittest.TestCase):
    def ends(self, d):
        return [(round(s.points[0][0], 6), round(s.points[0][1], 6), round(s.points[-1][0], 6), round(s.points[-1][1], 6))
                for sub in arrows.parse_path(d) for s in sub]

    def test_relative_lines_and_close(self):
        self.assertEqual(self.ends("m10 10 h10 v10 l-5 5 z"),
                         [(10, 10, 20, 10), (20, 10, 20, 20), (20, 20, 15, 25), (15, 25, 10, 10)])

    def test_implicit_lineto_after_moveto(self):
        self.assertEqual(self.ends("M0 0 10 0 10 10"), [(0, 0, 10, 0), (10, 0, 10, 10)])

    def test_smooth_cubic_reflects_previous_control(self):
        second = arrows.parse_path("M0 0 C0 10 10 10 10 0 S20 -10 20 0")[0][1]
        self.assertEqual(second.t0, (0.0, -10.0))  # first control reflected to (10, -10)

    def test_smooth_quad_reflects_previous_control(self):
        second = arrows.parse_path("M0 0 Q5 10 10 0 T20 0")[0][1]
        mid = second.points[len(second.points) // 2]
        self.assertAlmostEqual(mid[1], -5.0)  # control reflected to (15, -10)

    def test_arc_is_sampled_on_its_circle(self):
        seg = arrows.parse_path("M0 0 A10 10 0 0 1 20 0")[0][0]
        for x, y in seg.points:
            self.assertAlmostEqual(math.dist((x, y), (10, 0)), 10, places=6)
        self.assertLess(min(y for _, y in seg.points), -9.99)  # sweep=1 runs over the top
        self.assertGreater(seg.t1[1], 0)  # and lands heading down

    def test_packed_arc_flags(self):
        self.assertEqual(self.ends("M0 0 a10 10 0 0120 0"), [(0, 0, 20, 0)])

    def test_subpaths(self):
        self.assertEqual(len(arrows.parse_path("M0 0 H10 M20 0 H30")), 2)


class Bend(unittest.TestCase):
    def test_straight_lead_after_corner(self):
        self.assertLess(arrows.end_bend("M0 0 H40 Q48 0 48 8 V40", 12), 0.01)

    def test_corner_at_the_tip(self):
        self.assertGreater(arrows.end_bend("M0 0 H40 Q48 0 48 8", 12), 30)

    def test_start_judged_backwards(self):
        d = "M48 8 Q48 0 40 0 H0"
        self.assertGreater(arrows.start_bend(d, 12), 30)
        self.assertLess(arrows.end_bend(d, 12), 0.01)

    def test_arc_ending_at_tip_bends_and_lead_fixes_it(self):
        self.assertGreater(arrows.end_bend("M0 0 A10 10 0 0 1 20 0", 12), 3)
        self.assertLess(arrows.end_bend("M0 0 A10 10 0 0 1 20 0 V14", 12), 0.01)


class Directions(unittest.TestCase):
    """The 12 direction cases: bent versions fail, fixed versions pass, both tips of two-headed arrows."""

    def test_bent_cases_fail(self):
        for label, d, two in cases(fixed=False):
            with self.subTest(label):
                self.assertTrue(arrows.check_source(sheet(d, two)), d)

    def test_fixed_cases_pass(self):
        for label, d, two in cases(fixed=True):
            with self.subTest(label):
                self.assertEqual(arrows.check_source(sheet(d, two)), [])

    def test_bent_two_headed_curves_fail_at_both_tips(self):
        for label, d, two in cases(fixed=False)[4:8]:
            with self.subTest(label):
                found = arrows.check_source(sheet(d, two))
                self.assertTrue(any("arrow end" in f for f in found), found)
                self.assertTrue(any("arrow start" in f for f in found), found)

    def test_start_tip_only_counts_with_marker_start(self):
        d = "M48 8 Q48 0 40 0 H0"  # bent at the start only
        self.assertEqual(arrows.check_source(sheet(d)), [])
        self.assertEqual(len(arrows.check_source(sheet(d, two_headed=True))), 1)


class Markers(unittest.TestCase):
    def test_stroke_width_units(self):
        marker = {"markerwidth": "8", "refx": "7"}
        self.assertAlmostEqual(arrows.marker_head_length(marker, 1.5), 10.5)

    def test_viewbox_scales_ref_x(self):
        marker = {"viewbox": "0 0 10 10", "markerwidth": "8", "refx": "9"}
        self.assertAlmostEqual(arrows.marker_head_length(marker, 1.6), 7.2 * 1.6)

    def test_user_space_ignores_stroke_width(self):
        marker = {"markerwidth": "16", "refx": "15", "markerunits": "userSpaceOnUse"}
        self.assertAlmostEqual(arrows.marker_head_length(marker, 3), 15)

    def test_head_ahead_of_the_tip(self):
        marker = {"markerwidth": "18", "refx": "0", "markerunits": "userSpaceOnUse"}
        self.assertAlmostEqual(arrows.marker_head_length(marker, 1), 18)

    def test_lead_margin_and_minimum(self):
        self.assertEqual(arrows.lead_for(10.5), 14.5)
        self.assertEqual(arrows.lead_for(3), 10)

    def test_bigger_head_needs_longer_lead(self):
        d = "M0 0 H40 Q48 0 48 8 V20"  # 12px straight before the tip
        self.assertEqual(arrows.check_source(sheet(d, width="1")), [])  # lead 11.2
        self.assertTrue(arrows.check_source(sheet(d, width="3")))  # lead 25.6

    def test_inherited_stroke_width(self):
        d = "M0 0 H40 Q48 0 48 8 V20"
        source = sheet(d, width="1").replace(' stroke-width="1"', "").replace("<path d=\"M0", '<g stroke-width="3"><path d="M0')
        source = source.replace("/></svg>", "/></g></svg>")
        self.assertTrue(arrows.check_source(source))


class Elements(unittest.TestCase):
    def doc(self, element):
        return f'<svg><defs><marker id="m" markerWidth="8" refX="7"/></defs>{element}</svg>'

    def test_line_always_passes(self):
        self.assertEqual(arrows.check_source(self.doc('<line x1="0" y1="0" x2="5" y2="3" marker-end="url(#m)"/>')), [])

    def test_polyline_short_last_segment_fails(self):
        self.assertTrue(arrows.check_source(self.doc('<polyline points="0,0 40,0 40,4" marker-end="url(#m)"/>')))

    def test_polyline_long_last_segment_and_collinear_pass(self):
        self.assertEqual(arrows.check_source(self.doc('<polyline points="0,0 40,0 40,30" marker-end="url(#m)"/>')), [])
        self.assertEqual(arrows.check_source(self.doc('<polyline points="0,0 40,0 40,4 40,30" marker-end="url(#m)"/>')), [])

    def test_polyline_marker_start(self):
        self.assertTrue(arrows.check_source(self.doc('<polyline points="0,4 0,0 40,0" marker-start="url(#m)"/>')))

    def test_unresolved_marker_is_skipped(self):
        self.assertEqual(arrows.check_source(self.doc('<path d="M0 0 Q8 0 8 8" marker-end="url(#nope)"/>')), [])


class SelfCheck(unittest.TestCase):
    def test_self_check_reports_bent_arrows(self):
        d = cases(fixed=False)[0][1]
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "bent.html"
            path.write_text(f"<html><body>{sheet(d)}</body></html>", encoding="utf-8")
            self.assertTrue(any("arrow end bends" in e for e in self_check.verify(path)))


class ShippedAssets(unittest.TestCase):
    def test_all_assets_clean(self):
        paths = sorted(ASSETS.rglob("*.html"))
        self.assertGreater(len(paths), 200)
        findings = [f for path in paths for f in arrows.check(path)]
        self.assertEqual(findings, [])

    def test_cli_all_exits_zero(self):
        argv = sys.argv
        sys.argv = ["verify-arrow-ends.py", "--all"]
        try:
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(arrows.main(), 0)
        finally:
            sys.argv = argv
        self.assertIn("0 finding(s)", out.getvalue())


if __name__ == "__main__":
    unittest.main()
