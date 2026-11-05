"""Generated hand variants are out of scope for every per-type verifier.

generate-hand-variants.cjs redraws marks as rough.js paths, dropping the data
contract. Naming such a file explicitly must report it as out of scope (exit 0)
rather than claim it and fail; the authored example must still pass.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from _helpers import ASSETS
from _scope import add_per_kind, assert_all_checked, assert_all_out_of_scope

TYPES = (
    "architecture-delta", "axonometric-plan", "beeswarm", "bubble", "bump",
    "exploded", "heatmap", "marimekko", "polar", "ridgeline", "sankey",
    "slopegraph", "streamgraph", "treemap", "waterfall",
)


class HandVariantScope(unittest.TestCase):
    pass


def scope(case, kind):
    """The shipped -hand file and the same rough markup under a stem without -hand are out of scope; the authored
    example is checked and passes."""
    hand = ASSETS / f"example-{kind}-hand.html"
    with case.subTest("hand variants are out of scope"), tempfile.TemporaryDirectory() as directory:
        sketch = Path(directory) / f"example-{kind}-sketch.html"
        shutil.copyfile(hand, sketch)
        assert_all_out_of_scope(case, kind, hand, sketch)
    with case.subTest("the authored example still passes"):
        assert_all_checked(case, kind, ASSETS / f"example-{kind}.html")


add_per_kind(HandVariantScope, TYPES, "scope", scope)


if __name__ == "__main__":
    unittest.main()
