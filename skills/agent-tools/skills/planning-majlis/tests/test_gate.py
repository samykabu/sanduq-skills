import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gate  # noqa: E402

BRIEF = """# Brief

## Roster

- `chair` (core)
- `product` (core)
- `architect` (core)
- `security` (core)
- `qa-chaos` (core)
- `ux` (optional): it has screens

Not seated: end-user.
"""

SCORECARD = """# Scorecard

| Role | Kind | R1 | R2 | Conditions |
|---|---|---|---|---|
| chair | core | 6 | 9 | spike SP-1 |
| product | core | 7 | 9 | |
| architect | core | 8 | 10 | |
| security | core | 5 | 9 | |
| qa-chaos | core | 6 | 9 | |
| ux | optional | 7 | 9 | |
"""

RECORD = """# Decision record — v2

## 1. Decisions

**DR-1 Use one database (resolves XB-commercial-1).** Text with a \\| pipe.

**DR-2 Sign releases.** Cites SP-1 and OD-1.

## 2. Resolution ledger

| ID | Raised by | Finding | Resolution | DR | Status |
|---|---|---|---|---|---|
| XB-commercial-1 | chair | two stores | one store | DR-1 | RESOLVED |
| XB-security-chaos-1 | security | unsigned | signed | DR-2 | RESOLVED |
| XB-security-chaos-2 | security | name | owner picks | — | OWNER-DECISION |

## 4. Spike register (UNVERIFIED facts)

| ID | Unverified fact | Test and pass criterion | Fallback | Scheduled before |
|---|---|---|---|---|
| SP-1 | API allows 100/min | load test | queue | week 1 |

## 5. Owner decisions

| ID | Question | Options | Recommended default | Status |
|---|---|---|---|---|
| OD-1 | Product name | a; b | a | OWNER-DECISION |
"""


class GateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        (self.ws / "deliverables").mkdir()
        self.write("00-brief.md", BRIEF)
        self.write("scorecard.md", SCORECARD)
        self.write("record.md", RECORD)
        self.write("deliverables/D2.md", "Uses DR-1 and DR-2; spike SP-1.\n")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        (self.ws / name).write_text(text, encoding="utf-8")

    def gate(self, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = gate.main([str(self.ws), "--json", *extra])
        return code, {c["check"]: c for c in json.loads(out.getvalue())["checks"]}

    def test_passing_workspace(self):
        code, checks = self.gate()
        self.assertEqual(code, 0, checks)
        self.assertTrue(all(c["ok"] for c in checks.values()))

    def test_low_latest_score_fails_even_if_earlier_round_was_high(self):
        self.write("scorecard.md", SCORECARD.replace("| security | core | 5 | 9 |", "| security | core | 9 | 8 |"))
        code, checks = self.gate()
        self.assertEqual(code, 1)
        self.assertEqual(checks["scores"]["problems"], ["security: latest score 8 is below 9"])

    def test_open_row_fails(self):
        self.write("record.md", RECORD.replace("| DR-2 | RESOLVED |", "| — | OPEN |"))
        code, checks = self.gate()
        self.assertEqual(code, 1)
        self.assertEqual(checks["open"]["problems"], ["OPEN row: XB-security-chaos-1"])

    def test_owner_decision_rows_do_not_block(self):
        code, checks = self.gate()
        self.assertTrue(checks["open"]["ok"])

    def test_missing_core_role_and_unseated_score_row(self):
        self.write("00-brief.md", BRIEF.replace("- `security` (core)\n", ""))
        code, checks = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("core role not seated: security", checks["roster"]["problems"])
        self.assertIn("security: has a scorecard row but is not seated", checks["scores"]["problems"])

    def test_seated_role_without_score_row(self):
        self.write("00-brief.md", BRIEF.replace("Not seated", "- `end-user` (optional): yes\n\nNot seated"))
        code, checks = self.gate()
        self.assertIn("end-user: seated but has no scorecard row", checks["scores"]["problems"])

    def test_undefined_citation_in_deliverable(self):
        self.write("deliverables/D3.md", "Relies on DR-7 and OD-2.\n")
        code, checks = self.gate()
        self.assertEqual(code, 1)
        self.assertEqual(checks["ids"]["problems"], [
            "D3.md: DR-7 is cited but not defined in the record",
            "D3.md: OD-2 is cited but not defined in the record"])

    def test_broken_table_row(self):
        self.write("tracks.md", "| A | B |\n|---|---|\n| one | two | three |\n| `a|b` | c |\n")
        code, checks = self.gate()
        self.assertEqual(code, 1)
        self.assertEqual(len(checks["tables"]["problems"]), 2)

    def test_escaped_pipe_is_one_cell(self):
        self.write("tracks.md", "| A | B |\n|---|---|\n| `a\\|b` | c |\n")
        code, checks = self.gate()
        self.assertTrue(checks["tables"]["ok"], checks["tables"])

    def test_external_record_for_feature_mode(self):
        (self.ws / "record.md").unlink()
        other = Path(self.tmp.name) / "deliverables" / "project-record.md"
        other.write_text(RECORD, encoding="utf-8")
        code, checks = self.gate("--record", str(other))
        self.assertEqual(code, 0, checks)

    def test_missing_files_fail_clearly(self):
        for name in ("00-brief.md", "scorecard.md", "record.md"):
            (self.ws / name).unlink()
        code, checks = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("00-brief.md has no '## Roster' section", checks["roster"]["problems"])
        self.assertIn("record not found", checks["open"]["problems"][0])

    def test_missing_workspace_is_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(gate.main([str(self.ws / "nope")]), 2)


if __name__ == "__main__":
    unittest.main()
