"""The icon name index, the snippet data and the lookup script stay in step (stdlib only)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest

from _helpers import SCRIPTS, SKILL_DIR

INDEX = SKILL_DIR / "references" / "primitive-icons.md"
DATA = SCRIPTS / "icons.json"


def lookup(*terms: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "icon_lookup.py"), *terms],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )


class IconLookup(unittest.TestCase):
    def test_generated_files_match_the_vendored_svgs(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "build-icons.py"), "--check"],
                                capture_output=True, text=True, encoding="utf-8", check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_index_names_every_icon_and_stays_small(self):
        names = re.findall(r"^- `([^`]+)`: ", INDEX.read_text(encoding="utf-8"), re.M)
        icons = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertEqual(names, list(icons))
        self.assertGreaterEqual(len(names), 80)
        self.assertLess(INDEX.stat().st_size, 8000, "the index must not grow back into the catalog")
        self.assertNotIn("<svg width", INDEX.read_text(encoding="utf-8"))

    def test_exact_names_print_their_snippets(self):
        result = lookup("laptop", "server")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("<svg"), 2)
        self.assertIn("### laptop (Compute)", result.stdout)
        self.assertIn("Source: Tabler Icons", result.stdout)

    def test_a_keyword_prints_every_match(self):
        result = lookup("storage")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreaterEqual(result.stdout.count("<svg"), 2)

    def test_an_unknown_term_exits_2_with_the_nearest_names(self):
        result = lookup("laptp")
        self.assertEqual(result.returncode, 2)
        self.assertIn("nearest: laptop", result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
