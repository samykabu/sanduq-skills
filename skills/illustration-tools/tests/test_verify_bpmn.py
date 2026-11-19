#!/usr/bin/env python3
"""Tests for verify-bpmn.py - both polarities.

The shipped examples (light, dark, full and the authored hand variant) must
pass. Every rule is then proven on a synthetic diagram with its own IDs,
coordinates and marker name, built at two different origins, so nothing can
pass by memorising the shipped layout. Each negative case makes one edit that
still renders and expects the one finding that names it.

Run from the extension root: python -m unittest tests/test_verify_bpmn.py
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from _helpers import ASSETS, load, run_cli

bpmn = load("verify-bpmn.py")
VARIANTS = [ASSETS / f"example-bpmn{suffix}.html" for suffix in ("", "-dark", "-full", "-hand")]


def diagram(ox: int = 20, oy: int = 30, routes: bool = False) -> str:
    """A small valid Process: start -> task -> exclusive split -> end, or -> user task -> end."""
    def tags(names: str) -> str:
        return f' data-bpmn-routes="{names}"' if routes else ""

    top, low = oy + 60, oy + 180
    default = ' data-bpmn-default-route="yes"' if routes else ""
    return f"""<html><body>
<svg viewBox="0 0 {ox + 720} {oy + 260}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="t d" data-diagram="bpmn"{default}>
  <title id="t">Order check</title>
  <desc id="d">A clerk checks an order; stock decides whether it ships.</desc>
  <defs><marker id="tip" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="#333"/></marker></defs>
  <g data-bpmn="participant" data-bpmn-id="shop" data-bpmn-name="Shop">
    <rect x="{ox}" y="{oy}" width="700" height="240" fill="none" stroke="#333"/>
    <text x="{ox + 15}" y="{oy + 120}">Shop</text>
  </g>
  <g data-bpmn="lane" data-bpmn-id="clerk" data-bpmn-name="Clerk" data-pool="shop">
    <rect x="{ox + 30}" y="{oy}" width="670" height="120" fill="none" stroke="#333"/>
    <text x="{ox + 40}" y="{top}">CLERK</text>
  </g>
  <g data-bpmn="lane" data-bpmn-id="depot" data-bpmn-name="Depot" data-pool="shop">
    <rect x="{ox + 30}" y="{oy + 120}" width="670" height="120" fill="none" stroke="#333"/>
    <text x="{ox + 40}" y="{low}">DEPOT</text>
  </g>
  <line data-bpmn="sequenceFlow" data-bpmn-id="f1" data-source="begin" data-target="check"{tags("yes no")} x1="{ox + 84}" y1="{top}" x2="{ox + 120}" y2="{top}" stroke="#333" marker-end="url(#tip)"/>
  <line data-bpmn="sequenceFlow" data-bpmn-id="f2" data-source="check" data-target="stock"{tags("yes no")} x1="{ox + 220}" y1="{top}" x2="{ox + 268}" y2="{top}" stroke="#333" marker-end="url(#tip)"/>
  <line data-bpmn="sequenceFlow" data-bpmn-id="f3" data-bpmn-name="No" data-source="stock" data-target="lost"{tags("no")} x1="{ox + 312}" y1="{top}" x2="{ox + 386}" y2="{top}" stroke="#333" marker-end="url(#tip)"/>
  <path data-bpmn="sequenceFlow" data-bpmn-id="f4" data-bpmn-name="Yes" data-source="stock" data-target="ship"{tags("yes")} d="M{ox + 290} {oy + 82} V{oy + 150}" fill="none" stroke="#333" marker-end="url(#tip)"/>
  <line data-bpmn="sequenceFlow" data-bpmn-id="f5" data-source="ship" data-target="sent"{tags("yes")} x1="{ox + 340}" y1="{low}" x2="{ox + 406}" y2="{low}" stroke="#333" marker-end="url(#tip)"/>
  <text data-bpmn-label-for="f3" x="{ox + 330}" y="{top - 8}" fill="#333">no</text>
  <text data-bpmn-label-for="f4" x="{ox + 300}" y="{oy + 110}" fill="#333">YES</text>
  <g data-bpmn="startEvent" data-bpmn-id="begin" data-lane="clerk">
    <circle cx="{ox + 70}" cy="{top}" r="14" fill="#fff" stroke="#333" stroke-width="1"/>
  </g>
  <g data-bpmn="task" data-bpmn-id="check" data-bpmn-name="Check Order" data-lane="clerk">
    <rect x="{ox + 120}" y="{oy + 30}" width="100" height="60" rx="6" fill="#fff" stroke="#333"/>
    <text x="{ox + 170}" y="{top}"><tspan>Check</tspan><tspan>Order</tspan></text>
  </g>
  <g data-bpmn="exclusiveGateway" data-bpmn-id="stock" data-bpmn-name="In stock?" data-lane="clerk">
    <polygon points="{ox + 290},{oy + 38} {ox + 312},{top} {ox + 290},{oy + 82} {ox + 268},{top}" fill="#fff" stroke="#333"/>
    <path data-bpmn-marker="exclusive" d="M{ox + 283} {oy + 53} L{ox + 297} {oy + 67} M{ox + 297} {oy + 53} L{ox + 283} {oy + 67}" fill="none" stroke="#333" stroke-width="2"/>
    <text x="{ox + 290}" y="{oy + 30}">In stock?</text>
  </g>
  <g data-bpmn="endEvent" data-bpmn-id="lost" data-lane="clerk">
    <circle cx="{ox + 400}" cy="{top}" r="14" fill="#fff" stroke="#333" stroke-width="3"/>
  </g>
  <g data-bpmn="userTask" data-bpmn-id="ship" data-bpmn-name="Ship Order" data-lane="depot">
    <rect x="{ox + 240}" y="{oy + 150}" width="100" height="60" rx="6" fill="#fff" stroke="#333"/>
    <g data-bpmn-marker="user" fill="none" stroke="#333"><circle cx="{ox + 252}" cy="{oy + 161}" r="3"/><path d="M{ox + 246} {oy + 171} V{oy + 169} A6 5 0 0 1 {ox + 258} {oy + 169} V{oy + 171} Z"/></g>
    <text x="{ox + 290}" y="{low}">Ship Order</text>
  </g>
  <g data-bpmn="endEvent" data-bpmn-id="sent" data-lane="depot">
    <circle cx="{ox + 420}" cy="{low}" r="14" fill="#fff" stroke="#333" stroke-width="3"/>
  </g>
</svg>
</body></html>"""


BASE = diagram()
ROUTED = diagram(routes=True)
LOOP = """  <g data-bpmn="task" data-bpmn-id="spin" data-bpmn-name="Spin" data-lane="depot">
    <rect x="460" y="180" width="80" height="60" rx="6" fill="#fff" stroke="#333"/><text x="500" y="210">Spin</text>
  </g>
  <g data-bpmn="task" data-bpmn-id="twirl" data-bpmn-name="Twirl" data-lane="depot">
    <rect x="600" y="180" width="80" height="60" rx="6" fill="#fff" stroke="#333"/><text x="640" y="210">Twirl</text>
  </g>
  <line data-bpmn="sequenceFlow" data-bpmn-id="f6" data-source="spin" data-target="twirl" x1="540" y1="200" x2="600" y2="200" stroke="#333" marker-end="url(#tip)"/>
  <line data-bpmn="sequenceFlow" data-bpmn-id="f7" data-source="twirl" data-target="spin" x1="600" y1="220" x2="540" y2="220" stroke="#333" marker-end="url(#tip)"/>
</svg>"""


class Shipped(unittest.TestCase):
    def test_every_variant_is_in_scope_and_clean(self):
        for path in VARIANTS:
            with self.subTest(path.name):
                self.assertTrue(bpmn.in_scope(path.read_text(encoding="utf-8")))
                self.assertEqual(bpmn.check(path), [])

    def test_all_flag_checks_the_four_examples(self):
        code, output = run_cli("verify-bpmn.py", "--all")
        self.assertEqual(code, 0, output)
        self.assertIn("4 BPMN file(s) checked, 0 finding(s)", output)

    def test_hand_variant_keeps_the_contract_and_the_canonical_markers(self):
        light, hand = (path.read_text(encoding="utf-8") for path in (VARIANTS[0], VARIANTS[3]))
        self.assertIn('class="rough-generated"', hand)
        for canonical in ('<marker id="arrow"', 'data-bpmn-marker="user"', 'data-bpmn-marker="exclusive"'):
            line = next(line for line in light.splitlines() if canonical in line)
            self.assertIn(line, hand)
        flows = [line for line in light.splitlines() if 'marker-end="url(#arrow)"' in line]
        self.assertEqual([line for line in hand.splitlines() if 'marker-end="url(#arrow)"' in line], flows)

    def test_hand_outline_must_hug_its_canonical_shape(self):
        hand = VARIANTS[3].read_text(encoding="utf-8")
        outline = hand.index('<path class="rough-generated" d="', hand.index('data-bpmn-id="pay"'))
        wandered = hand[:outline] + re.sub(r' d="[^"]+"', ' d="M700 380 L720 380 L720 400 L700 400 Z"', hand[outline:], count=1)
        self.assertNotEqual(wandered, hand)
        self.assertTrue(any("pay: task has no visible outline" in error for error in bpmn.check_source(wandered)))


class Synthetic(unittest.TestCase):
    def reject(self, source: str, reason: str, original: str = BASE) -> None:
        self.assertNotEqual(source, original, "the fixture edit did not apply")
        errors = bpmn.check_source(source)
        self.assertTrue(any(reason in error for error in errors), f"expected {reason!r}, got {errors}")

    def swap(self, old: str, new: str, reason: str, original: str = BASE) -> None:
        self.assertIn(old, original)
        self.reject(original.replace(old, new, 1), reason, original)

    def test_valid_at_any_origin_with_or_without_routes(self):
        for source in (BASE, ROUTED, diagram(300, 500), diagram(7, 3, routes=True)):
            self.assertEqual(bpmn.check_source(source), [])

    # -- identity and ownership ----------------------------------------------

    def test_duplicate_id(self):
        self.swap('data-bpmn-id="lost"', 'data-bpmn-id="sent"', "sent: duplicate data-bpmn-id")

    def test_missing_id(self):
        self.swap(' data-bpmn-id="check"', "", "missing data-bpmn-id")

    def test_element_outside_the_subset(self):
        self.swap('data-bpmn="exclusiveGateway"', 'data-bpmn="parallelGateway"', "outside the approved subset")

    def test_second_pool(self):
        self.swap("</svg>", '<g data-bpmn="participant" data-bpmn-id="bank" data-bpmn-name="Bank"><rect x="20" y="300" width="700" height="60" fill="none" stroke="#333"/><text>Bank</text></g></svg>',
                  "expected exactly one visible pool (participant), found 2")

    def test_lane_must_belong_to_the_pool(self):
        self.swap('data-pool="shop">\n    <rect x="50" y="150"', 'data-pool="bank">\n    <rect x="50" y="150"', "depot: data-pool 'bank' is not the pool")

    def test_node_must_name_a_lane(self):
        self.swap('data-bpmn-id="begin" data-lane="clerk"', 'data-bpmn-id="begin" data-lane="shop"', "begin: data-lane 'shop' is not a lane")

    def test_nested_elements(self):
        self.swap('<text x="35" y="150">Shop</text>', '<text x="35" y="150">Shop</text><g data-bpmn="lane" data-bpmn-id="inner" data-bpmn-name="In" data-pool="shop"><rect x="50" y="30" width="670" height="10" fill="none" stroke="#333"/><text>In</text></g>',
                  "inner: BPMN elements must not nest")

    def test_hidden_element(self):
        self.swap('<g data-bpmn="endEvent" data-bpmn-id="lost"', '<g opacity="0.1" data-bpmn="endEvent" data-bpmn-id="lost"', "lost: is hidden")

    def test_transformed_element(self):
        self.swap('<g data-bpmn="task" data-bpmn-id="check"', '<g transform="translate(0 200)" data-bpmn="task" data-bpmn-id="check"', "check: must not be moved by a transform")

    def test_names_must_be_printed(self):
        self.swap("<tspan>Check</tspan><tspan>Order</tspan>", "<tspan>Check</tspan><tspan>Stock</tspan>", "check: name 'Check Order' is not printed")
        self.swap(' data-bpmn-name="Ship Order"', "", "ship: userTask needs a data-bpmn-name")
        self.swap('<text x="60" y="90">CLERK</text>', "", "clerk: name 'Clerk' is not printed")

    # -- pool and lane geometry ------------------------------------------------

    def test_lanes_must_fill_the_pool(self):
        self.swap('<rect x="50" y="150" width="670" height="120"', '<rect x="50" y="150" width="670" height="100"', "lanes must stack top to bottom and fill the pool")

    def test_lane_must_reach_the_pool_edge(self):
        self.swap('<rect x="50" y="30" width="670"', '<rect x="50" y="30" width="600"', "clerk: a horizontal lane runs")

    def test_pool_corners_are_square(self):
        self.swap('<rect x="20" y="30" width="700" height="240"', '<rect rx="8" x="20" y="30" width="700" height="240"', "shop: participant corners must be square")

    def test_node_must_sit_inside_its_declared_lane(self):
        self.swap('data-bpmn-name="Ship Order" data-lane="depot"', 'data-bpmn-name="Ship Order" data-lane="clerk"', "ship: userTask is drawn outside its lane 'clerk'")

    def test_nodes_must_not_overlap(self):
        self.swap('<circle cx="440" cy="210" r="14"', '<circle cx="350" cy="210" r="14"', "ship: overlaps sent")

    # -- glyphs and markers ----------------------------------------------------

    def test_task_is_rounded(self):
        self.swap('<rect x="140" y="60" width="100" height="60" rx="6"', '<rect x="140" y="60" width="100" height="60"', "check: a task is a rounded rectangle")

    def test_event_is_a_circle(self):
        self.swap('<circle cx="90" cy="90" r="14" fill="#fff" stroke="#333" stroke-width="1"/>',
                  '<rect x="76" y="76" width="28" height="28" fill="#fff" stroke="#333"/>', "begin: startEvent must start with its <circle> shape")

    def test_end_event_is_thick(self):
        self.swap('<circle cx="420" cy="90" r="14" fill="#fff" stroke="#333" stroke-width="3"/>',
                  '<circle cx="420" cy="90" r="14" fill="#fff" stroke="#333" stroke-width="1"/>', "lost: an end event is a thick circle")

    def test_none_events_stay_empty(self):
        self.swap('stroke-width="1"/>\n  </g>', 'stroke-width="1"/><circle cx="90" cy="90" r="9" fill="none" stroke="#333"/>\n  </g>', "begin: a none event is an empty circle")

    def test_outline_must_be_visible_and_solid(self):
        self.swap('<circle cx="90" cy="90" r="14" fill="#fff" stroke="#333"', '<circle cx="90" cy="90" r="14" fill="#fff" stroke="none"', "begin: startEvent has no visible outline")
        self.swap('rx="6" fill="#fff" stroke="#333"/>\n    <text x="190"', 'rx="6" fill="#fff" stroke="#333" stroke-dasharray="4 3"/>\n    <text x="190"', "check: task outline must be a solid line")

    def test_gateway_is_a_diamond(self):
        self.swap('points="310,68 332,90 310,112 288,90"', 'points="288,68 332,68 332,112 288,112"', "stock: a gateway is a diamond")

    def test_exclusive_marker(self):
        marker = '<path data-bpmn-marker="exclusive" d="M303 83 L317 97 M317 83 L303 97" fill="none" stroke="#333" stroke-width="2"/>'
        self.swap(marker, "", "stock: exclusiveGateway needs exactly one exclusive marker")
        self.swap("M303 83 L317 97 M317 83 L303 97", "M303 90 L317 90", "stock: exclusive marker is an X")
        self.swap("M303 83 L317 97 M317 83 L303 97", "M303 83 L317 83 M303 97 L317 97", "stock: exclusive marker strokes must cross")
        self.swap("M303 83 L317 97 M317 83 L303 97", "M301 85 L311 95 M311 85 L301 95", "stock: exclusive marker must sit at the diamond's centre")
        self.swap(marker, marker.replace('stroke="#333"', 'stroke="none"'), "stock: exclusive marker is not visible")

    def test_user_marker(self):
        self.swap('<g data-bpmn-marker="user"', '<g data-marker="user"', "ship: userTask needs exactly one user marker")
        self.swap('<circle cx="272" cy="191" r="3"/>', '<circle cx="330" cy="230" r="3"/>', "ship: user marker belongs in the task's upper left corner")
        self.swap('<circle cx="272" cy="191" r="3"/>', "", "ship: user marker is a head circle over one shoulders path")

    def test_generic_task_carries_no_marker(self):
        self.swap('<text x="190" y="90">', '<path data-bpmn-marker="service" d="M150 70 L160 80" stroke="#333"/><text x="190" y="90">', "check: marker 'service' does not belong on a task")

    # -- sequence flows --------------------------------------------------------

    def test_flow_endpoints_must_be_flow_nodes(self):
        self.swap('data-source="ship" data-target="sent"', 'data-source="ship" data-target="gone"', "f5: data-target 'gone' must name a flow node")
        self.swap('data-source="ship" data-target="sent"', 'data-source="depot" data-target="sent"', "f5: data-source 'depot' must name a flow node")

    def test_flow_duplicates_and_self_loops(self):
        self.swap('data-source="ship" data-target="sent"', 'data-source="ship" data-target="ship"', "f5: connects a node to itself")
        self.swap('data-source="ship" data-target="sent"', 'data-source="check" data-target="stock"', "f5: duplicates the flow check -> stock")

    def test_flow_is_solid_visible_and_arrowed(self):
        flow = 'x1="104" y1="90" x2="140" y2="90" stroke="#333" marker-end="url(#tip)"/>'
        self.swap(flow, flow.replace('stroke="#333"', 'stroke="#333" stroke-dasharray="5,4"'), "f1: a sequence flow is a solid line")
        self.swap(flow, flow.replace('stroke="#333"', 'stroke="#333" style="stroke-dasharray: 2 2"'), "f1: a sequence flow is a solid line")
        self.swap(flow, flow.replace(' marker-end="url(#tip)"', ""), "f1: needs marker-end")
        self.swap(flow, flow.replace("#tip", "#nib"), "f1: needs marker-end")
        self.swap(flow, flow.replace('stroke="#333"', 'stroke="none"'), "f1: sequence flow has no visible stroke")
        self.swap(flow, flow.replace('stroke="#333"', 'stroke="#333" marker-start="url(#tip)"'), "f1: a sequence flow carries no marker-start")
        self.swap('<line data-bpmn="sequenceFlow" data-bpmn-id="f1"', '<line opacity="0.2" data-bpmn="sequenceFlow" data-bpmn-id="f1"', "f1: is hidden")

    def test_arrowhead_is_a_solid_head(self):
        self.swap('<polygon points="0 0, 8 3, 0 6" fill="#333"/>', '<polygon points="0 0, 8 3, 0 6" fill="none" stroke="#333"/>', "arrowhead marker must be a solid filled head")
        self.swap('refY="3" orient="auto"', 'refY="3"', "arrowhead marker must be a solid filled head")

    def test_flow_must_attach_to_both_nodes(self):
        self.swap('x1="104" y1="90" x2="140" y2="90"', 'x1="104" y1="90" x2="124" y2="90"', "f1: ends away from the outline of check")
        self.swap('x1="104" y1="90" x2="140" y2="90"', 'x1="104" y1="60" x2="140" y2="90"', "f1: starts away from the outline of begin")

    def test_flow_geometry(self):
        self.swap('d="M310 112 V180"', 'd="M310 112 v68"', "f4: geometry must be a <line> or an absolute")
        self.swap('d="M310 112 V180"', 'd="M310 112 H760 V290 H310 V180"', "f4: a sequence flow may not leave the pool")
        detour = BASE.replace('<line data-bpmn="sequenceFlow" data-bpmn-id="f5"', '<path fill="none" data-bpmn="sequenceFlow" data-bpmn-id="f5"')
        self.reject(detour.replace('x1="360" y1="210" x2="426" y2="210"', 'd="M360 210 H400 V90 H440 V196"'), "f5: runs through lost")

    # -- structure -------------------------------------------------------------

    def test_degrees(self):
        self.swap('data-source="ship" data-target="sent"', 'data-source="ship" data-target="begin"', "begin: a start event has no incoming")
        self.swap('data-source="ship" data-target="sent"', 'data-source="lost" data-target="sent"', "lost: an end event has incoming and no outgoing flow")
        self.swap('data-source="ship" data-target="sent"', 'data-source="check" data-target="sent"', "check: a task has incoming and exactly one outgoing flow (found 1 in, 2 out)")
        self.swap('data-bpmn-name="Yes" data-source="stock" data-target="ship"', 'data-bpmn-name="Yes" data-source="check" data-target="ship"', "stock: an exclusive gateway splits or merges")

    def test_start_and_end_are_required(self):
        self.swap('data-bpmn="startEvent"', 'data-bpmn="task" data-bpmn-name="x"', "diagram: needs exactly one start event")
        self.swap('data-bpmn="endEvent"', 'data-bpmn="startEvent"', "diagram: needs exactly one start event")

    def test_reachability(self):
        self.reject(BASE.replace("</svg>", LOOP), "spin: cannot be reached from a start event")
        self.reject(BASE.replace("</svg>", LOOP), "twirl: cannot be reached from a start event")

    def test_dead_end_cannot_reach_an_end(self):
        trapped = BASE.replace("</svg>", LOOP).replace('data-source="ship" data-target="sent"', 'data-source="ship" data-target="spin"')
        errors = bpmn.check_source(trapped)
        self.assertTrue(any("ship: cannot reach an end event" in error for error in errors), errors)

    # -- conditions ------------------------------------------------------------

    def test_gateway_outputs_are_named_and_labelled(self):
        self.swap(' data-bpmn-name="No"', "", "f3: an exclusive gateway output needs its condition")
        self.swap('<text data-bpmn-label-for="f3" x="350" y="82" fill="#333">no</text>', "", "f3: expected one visible data-bpmn-label-for label, found 0")
        self.swap('fill="#333">YES</text>', 'fill="#333">MAYBE</text>', "f4: label 'MAYBE' does not match data-bpmn-name 'Yes'")
        self.swap('data-bpmn-name="No"', 'data-bpmn-name="yes"', "stock: gateway outputs must carry distinct condition names")
        self.swap('<text data-bpmn-label-for="f3"', '<text visibility="hidden" data-bpmn-label-for="f3"', "f3: condition label is not visible")
        self.swap('<text data-bpmn-label-for="f3"', '<text style="fill:none" data-bpmn-label-for="f3"', "f3: condition label is not visible")
        self.swap('data-bpmn-label-for="f3"', 'data-bpmn-label-for="f9"', "f9: data-bpmn-label-for must sit on a <text> and name a sequence flow")

    # -- routes ----------------------------------------------------------------

    def swap_routed(self, old: str, new: str, reason: str) -> None:
        self.swap(old, new, reason, ROUTED)

    def test_default_route_must_be_declared(self):
        self.swap_routed('data-bpmn-default-route="yes"', 'data-bpmn-default-route="maybe"', "data-bpmn-default-route 'maybe' is not a declared route")
        self.swap('data-diagram="bpmn"', 'data-diagram="bpmn" data-bpmn-default-route="yes"', "data-bpmn-default-route 'yes' is not a declared route")

    def test_only_participating_flows_need_route_names(self):
        approved_only = ROUTED.replace('data-bpmn-routes="yes no"', 'data-bpmn-routes="yes"').replace(' data-bpmn-routes="no"', "")
        self.assertEqual(bpmn.check_source(approved_only), [])
        self.swap_routed('data-target="sent" data-bpmn-routes="yes"', 'data-target="sent" data-bpmn-routes="Yes!"', "f5: data-bpmn-routes lists")

    def test_route_is_one_path_from_start_to_end(self):
        self.swap_routed('data-target="lost" data-bpmn-routes="no"', 'data-target="lost" data-bpmn-routes="no yes"', "BPMN route 'yes' is ambiguous")
        self.swap_routed('data-target="sent" data-bpmn-routes="yes"', 'data-target="sent" data-bpmn-routes="no"', "route 'yes': BPMN playback stops at 'ship'")
        self.swap_routed('data-target="check" data-bpmn-routes="yes no"', 'data-target="check" data-bpmn-routes="no"', "route 'yes': BPMN playback stops at 'begin'")


class Scope(unittest.TestCase):
    def test_other_diagrams_fail_the_explicit_bpmn_check(self):
        code, output = run_cli("verify-bpmn.py", ASSETS / "example-swimlane.html")
        self.assertEqual(code, 1, output)
        self.assertIn('the first SVG must declare data-diagram="bpmn"', output)

    def test_marker_claims_a_file_under_any_stem(self):
        with tempfile.TemporaryDirectory() as scratch:
            good, bad = Path(scratch) / "figure.html", Path(scratch) / "broken.html"
            good.write_text(BASE, encoding="utf-8")
            bad.write_text(BASE.replace('data-bpmn-id="lost"', 'data-bpmn-id="sent"'), encoding="utf-8")
            self.assertEqual(run_cli("verify-bpmn.py", good)[0], 0)
            code, output = run_cli("verify-bpmn.py", good, bad)
            self.assertEqual(code, 1, output)
            self.assertIn("broken.html: sent: duplicate data-bpmn-id", output)
            self.assertEqual(run_cli("verify-bpmn.py", Path(scratch) / "absent.html")[0], 2)

    def test_malformed_or_commented_out_diagrams_fail_closed(self):
        self.assertTrue(any("invalid SVG" in error for error in bpmn.check_source(BASE.replace("</g>", "", 1))))
        self.assertTrue(bpmn.check_source(f"<!--{BASE}-->"))

    def test_browser_attributes_on_the_first_live_svg(self):
        source = BASE.replace('data-diagram="bpmn"', "data-diagram=bpmn").replace('data-bpmn-id="begin"', "data-bpmn-id=begin")
        source = source.replace('id="tip"', 'id="ArrowTip"').replace('marker-end="url(#tip)"', """marker-end='url("#ArrowTip")'""")
        self.assertEqual(bpmn.check_source(source), [])
        self.assertEqual(bpmn.check_source('<p class="rough-shape">Note</p>' + source), [])


if __name__ == "__main__":
    unittest.main()
