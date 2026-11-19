"""Stdlib unittest suite for the draw.io / Mermaid / Excalidraw / PlantUML import pipeline.

Run from the extension directory:  python -m unittest discover -s tests -v
Source labels in the fixtures are untrusted data; the adversarial cases prove they stay inert.
"""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "illustrate" / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"

CASES = {
    "drawio": ("drawio_extract.py", ["sample-architecture.drawio"]),
    "mermaid": (
        "mermaid_extract.py",
        ["sample-flowchart.mmd", "sample-readme-with-mermaid.md", "sample-adversarial.mmd"],
    ),
    "excalidraw": (
        "excalidraw_extract.py",
        ["sample-whiteboard.excalidraw", "sample-adversarial.excalidraw"],
    ),
    "plantuml": (
        "plantuml_extract.py",
        ["sample-sequence.puml", "sample-class.puml", "sample-adversarial.puml"],
    ),
}


def run(args: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class ExtractorTests(unittest.TestCase):
    def test_every_fixture_digests(self) -> None:
        for kind, (script, fixtures) in CASES.items():
            for fixture in fixtures:
                with self.subTest(kind=kind, fixture=fixture):
                    proc = run([str(SCRIPTS / script), str(FIXTURES / fixture)])
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertIn("budget:", proc.stdout)
                    self.assertIn("### Nodes", proc.stdout)

    def test_adversarial_labels_stay_inert(self) -> None:
        for script, fixture in (
            ("mermaid_extract.py", "sample-adversarial.mmd"),
            ("excalidraw_extract.py", "sample-adversarial.excalidraw"),
            ("plantuml_extract.py", "sample-adversarial.puml"),
        ):
            with self.subTest(fixture=fixture):
                out = run([str(SCRIPTS / script), str(FIXTURES / fixture)]).stdout
                # Link targets never reach the digest; URLs inside labels are escaped data,
                # so no live Markdown link or raw HTML can form.
                self.assertNotIn("do-not-follow", out)
                self.assertNotIn("](http", out)
                self.assertNotIn("<br", out)
                self.assertNotIn("<script", out.lower())
                if not fixture.endswith(".puml"):  # the PlantUML digest omits an empty discard ledger
                    self.assertIn("discarded:", out)

    def test_malformed_drawio_xml_exits_2(self) -> None:
        # The drivers cover the wrong-suffix exit 2 of every extractor; only this reaches draw.io's XML parse error.
        proc = run([str(SCRIPTS / "drawio_extract.py"), str(FIXTURES.parent / "test_import_extractors.py")])
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("malformed XML", proc.stderr)


def drawio_edge(style: str) -> str:
    """A two-node .drawio with one a->b connector carrying `style`."""
    return (
        '<mxfile><diagram name="p" id="p"><mxGraphModel><root>'
        '<mxCell id="0"/><mxCell id="1" parent="0"/>'
        '<mxCell id="a" value="A" vertex="1" parent="1">'
        '<mxGeometry x="0" y="0" width="80" height="40" as="geometry"/></mxCell>'
        '<mxCell id="b" value="B" vertex="1" parent="1">'
        '<mxGeometry x="200" y="0" width="80" height="40" as="geometry"/></mxCell>'
        f'<mxCell id="e" edge="1" parent="1" source="a" target="b" style="{style}">'
        '<mxGeometry relative="1" as="geometry"/></mxCell>'
        "</root></mxGraphModel></diagram></mxfile>"
    )


class DrawioArrowheadTests(unittest.TestCase):
    """The tail is the semantic source: arrowheads decide direction, not attribute order."""

    CASES = {
        # style: (source, target, bidirectional, undirected, entry_points, terminals)
        "": ("a", "b", False, False, ["A"], ["B"]),
        "startArrow=classic;endArrow=none": ("b", "a", False, False, ["B"], ["A"]),
        "startArrow=classic;endArrow=classic": ("a", "b", True, False, [], []),
        "startArrow=none;endArrow=none": ("a", "b", False, True, [], []),
    }

    def test_arrowheads_normalize_endpoints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "edge.drawio"
            for style, (src, tgt, bidi, undirected, entries, terminals) in self.CASES.items():
                with self.subTest(style=style or "default"):
                    path.write_text(drawio_edge(style), encoding="utf-8")
                    proc = run([str(SCRIPTS / "drawio_extract.py"), str(path), "--json"])
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    page = json.loads(proc.stdout)["pages"][0]
                    (edge,) = page["edges"]
                    self.assertEqual((edge["source"], edge["target"]), (src, tgt))
                    self.assertEqual(edge["bidirectional"], bidi)
                    self.assertEqual(edge["undirected"], undirected)
                    self.assertEqual(page["analysis"]["entry_points"], entries)
                    self.assertEqual(page["analysis"]["terminals"], terminals)


def extract_json(test: unittest.TestCase, script: str, name: str, text: str | bytes, *args: str) -> dict:
    """Write `text` to a temp file called `name`, run `script --json`, and return the parsed IR."""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / name
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(text, encoding="utf-8")
        proc = run([str(SCRIPTS / script), str(path), "--json", *args])
    test.assertEqual(proc.returncode, 0, proc.stderr)
    return json.loads(proc.stdout)


class MermaidRegressionTests(unittest.TestCase):
    """Ordinary Mermaid syntax that used to fail or lose content (upstream fixes through #522)."""

    def mermaid(self, text: str | bytes, name: str = "source.mmd", *args: str) -> dict:
        return extract_json(self, "mermaid_extract.py", name, text, *args)

    def test_bom_apostrophes_dotted_hyphenated_and_invisible_ids(self) -> None:
        source = (
            "﻿flowchart LR\n"
            "  user-profile --> box.office\n"
            "  A ~~~ B\n"
            "  C[Bob's box] -->|it's| D\n"
        ).encode("utf-8")
        diagram = self.mermaid(source)["diagrams"][0]
        self.assertEqual(diagram["kind"], "flowchart")
        self.assertEqual(
            sorted(node["id"] for node in diagram["nodes"]),
            ["A", "B", "C", "D", "box.office", "user-profile"],
        )
        labels = {node["id"]: node["label"] for node in diagram["nodes"]}
        self.assertEqual(labels["C"], "Bob's box")
        edges = [(e["source"], e["target"], e["label"]) for e in diagram["edges"]]
        # The invisible ~~~ link keeps its endpoints as nodes but draws no edge.
        self.assertEqual(edges, [("user-profile", "box.office", ""), ("C", "D", "it's")])

    def test_outer_markdown_fence_hides_sample_blocks(self) -> None:
        source = (
            "````markdown\n```mermaid\nflowchart LR\n  X --> Y\n```\n````\n\n"
            "```mermaid\nflowchart LR\n  Real --> Diagram\n```\n"
        )
        payload = self.mermaid(source, "readme.md")
        self.assertEqual(len(payload["diagrams"]), 1)
        self.assertEqual({n["id"] for n in payload["diagrams"][0]["nodes"]}, {"Real", "Diagram"})

    def test_sequence_config_autonumber_and_highlight(self) -> None:
        source = (
            "sequenceDiagram\n"
            '%%{init: {"theme":"dark"}}%%\n'
            "autonumber 10 5\n"
            "participant A\nparticipant B\n"
            "alt ok\nrect rgb(1,2,3)\nA->>B: hi\nend\nelse bad\nB->>A: no\nend\n"
        )
        diagram = self.mermaid(source)["diagrams"][0]
        self.assertEqual(diagram["discarded"]["config_directives"], 1)
        self.assertEqual(diagram["autonumber"], [{"line": 3, "off": False, "start": 10, "step": 5}])
        # The rect highlight's `end` must not close the enclosing alt fragment.
        self.assertEqual(
            diagram["fragments"],
            [{"kind": "alt", "label": "ok", "line": 6, "depth": 0, "regions": ["bad"]}],
        )
        self.assertEqual([e["label"] for e in diagram["edges"]], ["hi", "no"])

    def test_unicode_repeated_bare_and_composite_states(self) -> None:
        source = (
            "stateDiagram\n"
            "  待机 : 等待输入\n"
            "  待机 : 第二行\n"
            "  Lonely\n"
            '  state "Big Thing" as Big {\n    Inner\n  }\n'
            "  [*] --> 待机\n"
        )
        diagram = self.mermaid(source)["diagrams"][0]
        nodes = {n["id"]: n for n in diagram["nodes"]}
        self.assertEqual(nodes["待机"]["label"], "等待输入\n第二行")
        self.assertIn("Lonely", nodes)
        self.assertEqual(nodes["Big"]["label"], "Big Thing")
        self.assertEqual(nodes["Inner"]["parent"], "Big")

    def test_er_aliases_quoted_names_and_cardinality_words(self) -> None:
        source = (
            "erDiagram\n"
            "  p[Person] {\n    string name\n  }\n"
            '  "Line Item" ||--o{ p : has\n'
            "  CAR 1 to zero or more DRIVER : uses\n"
            "  A }o..o{ B : link\n"
        )
        diagram = self.mermaid(source)["diagrams"][0]
        labels = {n["id"]: n["label"] for n in diagram["nodes"]}
        self.assertEqual(labels["p"], "Person")
        self.assertIn("Line Item", labels)
        edges = {(e["source"], e["target"]): (e["label"], e["style"]) for e in diagram["edges"]}
        self.assertEqual(edges[("Line Item", "p")], ("|| -- o{ · has", "solid"))
        self.assertEqual(edges[("CAR", "DRIVER")], ("|| -- o{ · uses", "solid"))
        self.assertEqual(edges[("A", "B")], ("}o .. o{ · link", "dashed"))

    def test_quadrant_chart_redraws_as_quadrant(self) -> None:
        diagram = self.mermaid((FIXTURES / "sample-quadrant.mmd").read_text(encoding="utf-8"))["diagrams"][0]
        self.assertEqual(diagram["kind"], "quadrant")
        self.assertEqual(diagram["analysis"]["type_candidates"], ["quadrant"])
        self.assertEqual(set(diagram["quadrants"]), {"1", "2", "3", "4"})
        self.assertTrue(diagram["points"])
        self.assertTrue(all(0 <= p["x"] <= 1 and 0 <= p["y"] <= 1 for p in diagram["points"]))


class DrawioRegressionTests(unittest.TestCase):
    PAGE = (
        '<mxfile><diagram name="blank" id="b"><mxGraphModel><root><mxCell id="0"/>'
        '<mxCell id="1" parent="0"/></root></mxGraphModel></diagram>'
        '<diagram name="日本語" id="j"><mxGraphModel><root>'
        '<mxCell id="0"/><mxCell id="1" parent="0"/>'
        '<mxCell id="g" value="Group" vertex="1" parent="1">'
        '<mxGeometry x="100" y="100" width="200" height="100" as="geometry"/></mxCell>'
        '<mxCell id="c" value="Child" vertex="1" parent="g">'
        '<mxGeometry x="0.5" y="0.5" width="40" height="20" relative="1" as="geometry">'
        '<mxPoint x="-20" y="-10" as="offset"/></mxGeometry></mxCell>'
        '<mxCell id="h" value="Hidden" vertex="1" parent="1" visible="0">'
        '<mxGeometry x="0" y="0" width="40" height="20" as="geometry"/></mxCell>'
        '<mxCell id="t" value="List&lt;String&gt; a &lt; b" vertex="1" parent="1">'
        '<mxGeometry x="400" y="0" width="80" height="40" as="geometry"/></mxCell>'
        '<mxCell id="tb" value="Users" style="shape=table;" vertex="1" parent="1">'
        '<mxGeometry x="0" y="300" width="160" height="60" as="geometry"/></mxCell>'
        '<mxCell id="r1" value="" style="shape=tableRow;" vertex="1" parent="tb">'
        '<mxGeometry y="30" width="160" height="30" as="geometry"/></mxCell>'
        "</root></mxGraphModel></diagram></mxfile>"
    )

    def test_unicode_page_nested_relative_hidden_rows_and_brackets(self) -> None:
        page = extract_json(self, "drawio_extract.py", "p.drawio", self.PAGE, "--page", "日本語")["pages"][0]
        self.assertEqual(page["name"], "日本語")
        nodes = {n["id"]: n for n in page["nodes"]}
        self.assertNotIn("h", nodes)  # visible="0" cells never reach the IR
        self.assertEqual((nodes["c"]["x"], nodes["c"]["y"]), (180.0, 140.0))
        self.assertEqual(nodes["t"]["label"], "List<String> a < b")
        self.assertEqual((nodes["tb"]["shape"], nodes["r1"]["shape"]), ("table", "table-row"))

    def test_unwritable_out_exits_2_with_named_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "p.drawio"
            path.write_text(self.PAGE, encoding="utf-8")
            blocker = Path(directory) / "file"
            blocker.write_text("", encoding="utf-8")
            proc = run([str(SCRIPTS / "drawio_extract.py"), str(path), "--out", str(blocker / "digest.md")])
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("cannot write", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)


class ExcalidrawRegressionTests(unittest.TestCase):
    @staticmethod
    def scene(container_type: str) -> str:
        return json.dumps({"type": "excalidraw", "version": 2, "elements": [
            {"id": "r1", "type": "rectangle", "x": 0, "y": 0, "width": 100, "height": 50,
             "groupIds": ["inner", "outer"], "boundElements": [{"id": "t1", "type": "text"}]},
            {"id": "t1", "type": "text", "x": 5, "y": 5, "width": 90, "height": 40,
             "text": "Order\nService", "originalText": "Order Service", "containerId": "r1"},
            {"id": "r2", "type": "rectangle", "x": 200, "y": 0, "width": 100, "height": 50,
             "groupIds": ["inner", "outer"]},
            {"id": "r3", "type": "ellipse", "x": 400, "y": 0, "width": 100, "height": 50, "groupIds": ["outer"]},
            {"id": "x", "type": container_type, "x": 0, "y": 200, "width": 100, "height": 50,
             "boundElements": [{"id": "t2", "type": "text"}]},
            {"id": "t2", "type": "text", "x": 5, "y": 205, "width": 90, "height": 40,
             "text": "Logo", "originalText": "Logo", "containerId": "x"},
        ]})

    def test_original_text_outer_groups_and_unimported_bound_text(self) -> None:
        scene = extract_json(self, "excalidraw_extract.py", "s.excalidraw", self.scene("mystery"))["scene"]
        nodes = {n["id"]: n for n in scene["nodes"]}
        self.assertEqual(nodes["r1"]["label"], "Order Service")  # originalText, not the wrapped text
        # Text bound to a discarded container survives as standalone text.
        self.assertEqual((nodes["t2"]["shape"], nodes["t2"]["label"]), ("text", "Logo"))
        self.assertNotIn("x", nodes)
        self.assertEqual(scene["discarded"]["unknown_elements"], 1)
        groups = {g["id"]: g["children"] for g in scene["analysis"]["collapsible_groups"]}
        self.assertEqual(groups, {"outer": 3, "inner": 2})

    def test_supported_container_keeps_its_bound_label(self) -> None:
        scene = extract_json(self, "excalidraw_extract.py", "s.excalidraw", self.scene("embeddable"))["scene"]
        nodes = {n["id"]: n for n in scene["nodes"]}
        self.assertEqual((nodes["x"]["shape"], nodes["x"]["label"]), ("embed", "Logo"))
        self.assertNotIn("t2", nodes)


class PlantumlTests(unittest.TestCase):
    def test_fenced_markdown_selects_sequence_and_class_blocks(self) -> None:
        source = (
            "# Doc\n\n```plantuml\n@startuml\nAlice -> Bob : hi\n@enduml\n```\n\n"
            "```puml\n@startuml\nclass User\nclass Admin\nUser <|-- Admin\n@enduml\n```\n"
        )
        payload = extract_json(self, "plantuml_extract.py", "doc.md", source, "--diagram", "all")
        sequence, klass = payload["diagrams"]
        self.assertEqual(sequence["kind"], "sequence")
        self.assertEqual([(e["source"], e["target"], e["label"]) for e in sequence["edges"]], [("Alice", "Bob", "hi")])
        self.assertEqual(klass["kind"], "class")
        (edge,) = klass["edges"]
        self.assertEqual((edge["source"], edge["target"], edge["arrowhead"]), ("Admin", "User", "inheritance"))

    def test_supported_extensions_and_include_refusal(self) -> None:
        body = (FIXTURES / "sample-sequence.puml").read_text(encoding="utf-8")
        for suffix in (".puml", ".plantuml", ".pu"):
            with self.subTest(suffix=suffix):
                diagram = extract_json(self, "plantuml_extract.py", "s" + suffix, body)["diagrams"][0]
                self.assertEqual(diagram["kind"], "sequence")
        # Block 0 of the multi fixture carries !includeurl: it fails closed when selected,
        # while the class block stays reachable.
        multi = str(FIXTURES / "sample-multi.puml")
        refused = run([str(SCRIPTS / "plantuml_extract.py"), multi])
        self.assertEqual(refused.returncode, 2)
        self.assertIn("include not inlined", refused.stderr)
        selected = run([str(SCRIPTS / "plantuml_extract.py"), multi, "--diagram", "1", "--json"])
        self.assertEqual(selected.returncode, 0, selected.stderr)
        self.assertEqual(json.loads(selected.stdout)["diagrams"][0]["kind"], "class")

    def test_unsupported_kind_names_supported_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "a.puml"
            path.write_text("@startmindmap\n* root\n@endmindmap\n", encoding="utf-8")
            proc = run([str(SCRIPTS / "plantuml_extract.py"), str(path)])
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("unsupported diagram kind", proc.stderr)
        self.assertIn("supported: sequence, class", proc.stderr)


class VerifierTests(unittest.TestCase):
    """Full structural gates in place, plus upstream's mutation regressions on one mutated temp copy.

    The drivers write only to their own temp dirs, so the pristine run needs no copy of the tree. A mutation
    fails inside the driver's last docs check, so that check runs in-process against the mutated file.
    """


def pristine(case, kind):
    proc = run([str(ROOT / "tests" / f"verify-{kind}-import.py")])
    case.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


for _kind in CASES:
    setattr(VerifierTests, f"test_verifier_passes_on_pristine_tree_{_kind}", lambda self, kind=_kind: pristine(self, kind))


class MutationTests(unittest.TestCase):
    def rejects(self, kind: str, check: str, attribute: str, old: str, new: str, reason: str) -> None:
        """Point the driver's `attribute` file at a temp copy with `old` replaced; `check` must fail with `reason`."""
        spec = importlib.util.spec_from_file_location(f"verify_{kind}_import_mutation", ROOT / "tests" / f"verify-{kind}-import.py")
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        original = getattr(driver, attribute)
        text = original.read_text(encoding="utf-8")
        self.assertIn(old, text)
        with tempfile.TemporaryDirectory() as directory:
            mutated = Path(directory) / original.name
            mutated.write_text(text.replace(old, new, 1), encoding="utf-8")
            setattr(driver, attribute, mutated)
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
                getattr(driver, check)()
        self.assertEqual(raised.exception.code, 1, stdout.getvalue())
        self.assertIn(reason, stderr.getvalue())

    def test_stale_slash_command_is_rejected(self) -> None:
        for kind, check in (
            ("drawio", "check_docs"),
            ("excalidraw", "check_docs_and_wiring"),
            ("plantuml", "check_docs_and_wiring"),
        ):
            with self.subTest(kind=kind):
                self.rejects(kind, check, "IMPORT_REF", f"/illustrate:import-{kind}", "/illustrate:import", "slash command")

    def test_elbowed_drawio_worked_example_route_is_rejected(self) -> None:
        self.rejects("drawio", "check_docs", "EXAMPLE", 'd="M560,232 H640"', 'd="M560,232 H592 V252 H640"',
                     "direct horizontal connector")

    def test_extra_accent_in_excalidraw_example_is_rejected(self) -> None:
        # A resolved theme accent counts the same as the upstream default literal.
        self.rejects("excalidraw", "check_docs_and_wiring", "EXAMPLE", "</svg>", '<g fill="#2563eb"/>' * 5 + "</svg>", "accent")


if __name__ == "__main__":
    unittest.main()
