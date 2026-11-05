"""svg_scan.py: the scanner and helpers the data verifiers share (IP19)."""

from __future__ import annotations

import ast
import unittest

from _helpers import SCRIPTS, load

# Byte-identical before IP19. Element and attrs_of stay local where a verifier reads them another way.
SHARED = ("first_wins", "_Scanner", "line_of", "median", "is_hand_variant")


class SvgScanTests(unittest.TestCase):
    def setUp(self):
        self.scan = load("svg_scan.py")

    def test_scanner_collects_each_mark_tag_with_ancestry_and_first_wins_attributes(self):
        source = ('<svg><g style="transform: x"><line x1="1" x1="2"/></g>\n'
                  '<path d="M0 0"/><text>a<title>tip</title></text><!-- <line x1="9"/> --></svg>')
        doc = self.scan.Scanner(source, ("line", "path"), lambda attrs: attrs.get("style"))
        self.assertIsNone(doc.error)
        self.assertEqual([e.attrs["x1"] for e in doc.lines], ["1"])
        self.assertEqual(doc.lines[0].ancestor, "an ancestor <g>/<svg> style transform")
        self.assertEqual((len(doc.paths), doc.paths[0].line, doc.paths[0].ancestor), (1, 2, None))
        self.assertEqual(source[doc.paths[0].offset:].split(" ")[0], "<path")
        self.assertEqual([e.body for e in doc.texts], ["a"])
        self.assertEqual([e.body for e in doc.named], ["tip"])

    def test_printed_number_reads_one_complete_token_with_the_verifier_reader(self):
        self.assertEqual(self.scan.printed_number("512,000 ms", lambda t: float(t.replace(",", ""))), (512000.0, None))
        self.assertEqual(self.scan.printed_number("1 of 2", float), (None, "prints more than one numeric token"))
        self.assertEqual(self.scan.printed_number("none", float), (None, "prints no number"))
        self.assertEqual(self.scan.printed_number("7", lambda t: None), (None, "prints a number this checker cannot read"))

    def test_no_verifier_keeps_its_own_copy_of_a_shared_helper(self):
        for path in sorted(SCRIPTS.glob("verify-*.py")):
            names = {node.name for node in ast.parse(path.read_text(encoding="utf-8")).body
                     if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
            with self.subTest(path.name):
                # marimekko's _Scanner is a subclass of svg_scan.Scanner, not a copy.
                self.assertFalse(names & set(SHARED) - ({"_Scanner"} if path.name == "verify-marimekko.py" else set()))


if __name__ == "__main__":
    unittest.main()
