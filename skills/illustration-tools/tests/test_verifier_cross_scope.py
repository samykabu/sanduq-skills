"""Per-type verifiers must not claim other types' files.

A file is in a verifier's scope when its stem names the type or it carries the
type's own data-contract marker. Naming another type's shipped example
explicitly must report it as out of scope (exit 0), not fail it as a malformed
instance; the verifier's own example must still be checked and pass, including
under a stem that does not name the type (the marker alone claims it).
The own example under its own name is checked by test_verifier_hand_scope.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from _helpers import ASSETS
from _scope import add_per_kind, assert_all_checked, assert_all_out_of_scope

VERIFIERS = (
    "architecture-delta", "axonometric-plan", "exploded", "heatmap",
    "polar", "sankey", "treemap", "waterfall",
)
OTHERS = VERIFIERS + (
    "architecture", "bar", "beeswarm", "bubble", "bump", "flowchart",
    "marimekko", "slopegraph",
)


class CrossTypeScope(unittest.TestCase):
    pass


def scope(case, kind):
    """Other types' examples are out of scope; the marker alone claims the own example under a neutral stem."""
    with case.subTest("other types' examples are out of scope"):
        assert_all_out_of_scope(case, kind, *(ASSETS / f"example-{other}.html" for other in OTHERS if other != kind))
    with case.subTest("the marker claims a file without the type stem"), tempfile.TemporaryDirectory() as directory:
        copy = Path(directory) / "renamed-figure.html"
        shutil.copyfile(ASSETS / f"example-{kind}.html", copy)
        assert_all_checked(case, kind, copy)


add_per_kind(CrossTypeScope, VERIFIERS, "scope", scope)


class SankeyProse(unittest.TestCase):
    def test_prose_mentioning_sankey_is_not_claimed(self):
        source = (ASSETS / "example-flowchart.html").read_text(encoding="utf-8")
        source = source.replace("</h1>", "</h1><p>The next report is a Sankey diagram.</p>", 1)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "example-flowchart.html"
            target.write_text(source, encoding="utf-8")
            assert_all_out_of_scope(self, "sankey", target)


if __name__ == "__main__":
    unittest.main()
