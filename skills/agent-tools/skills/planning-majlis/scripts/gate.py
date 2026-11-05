#!/usr/bin/env python3
"""Decide the planning-majlis gate for a workspace.

    python gate.py <workspace> [--record PATH] [--min-score 9] [--json]

Checks:
  roster     00-brief.md lists the seated roles under "## Roster"; all five core roles are seated
  scores     scorecard.md has one row per seated role (no others); each latest R<n> score >= min
  open       no ledger row in the record has a Status cell starting with OPEN
  ids        every DR-n, SP-n and OD-n cited in the record or deliverables/ is defined in the record
  tables     every Markdown table row in the workspace has as many cells as its header

Exit 0 when every check passes, 1 when any fails, 2 on a usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CORE = ("chair", "product", "architect", "security", "qa-chaos")
OPTIONAL = ("ux", "integrations", "devops-finops", "end-user")
ROLES = CORE + OPTIONAL
CITE = re.compile(r"\b(DR|SP|OD)-(\d+)\b")


def cells(line):
    """Cells of a table row; an escaped \\| stays inside its cell."""
    parts = re.split(r"(?<!\\)\|", line.strip())
    return [c.strip() for c in parts[1:-1]] if len(parts) > 2 else []


def tables(text):
    """Yield (first line number, rows) for each Markdown table, separator row dropped."""
    block, start = [], 0
    for n, line in enumerate(text.splitlines() + [""], 1):
        if line.lstrip().startswith("|"):
            if not block:
                start = n
            block.append(line)
            continue
        if len(block) >= 2:
            yield start, [cells(r) for i, r in enumerate(block) if i != 1]
        block = []


def roster(brief):
    section = re.search(r"^## Roster\s*$(.*?)(?=^## |\Z)", brief, re.M | re.S)
    if not section:
        return None
    found = re.findall(r"^- `?([a-z-]+)`?", section.group(1), re.M)
    return [r for r in found if r in ROLES]


def latest_scores(scorecard):
    """{role: score text} from the table whose header starts with Role."""
    for _, rows in tables(scorecard):
        head = rows[0]
        if not head or head[0].lower() != "role":
            continue
        rounds = [i for i, h in enumerate(head) if re.fullmatch(r"R\d+", h)]
        out = {}
        for row in rows[1:]:
            if not row:
                continue
            filled = [row[i] for i in rounds if i < len(row) and row[i]]
            out[row[0].strip("`")] = filled[-1] if filled else ""
        return out
    return None


def open_rows(record):
    found = []
    for line, rows in tables(record):
        head = [h.lower() for h in rows[0]]
        if "status" not in head:
            continue
        col = head.index("status")
        for row in rows[1:]:
            if col < len(row) and row[col].upper().startswith("OPEN"):
                found.append(row[0])
    return found


def defined_ids(record):
    ids = {f"DR-{n}" for n in re.findall(r"^\*\*DR-(\d+)\b", record, re.M)}
    for kind in ("SP", "OD"):
        ids |= {f"{kind}-{n}" for n in re.findall(rf"^\|\s*{kind}-(\d+)\s*\|", record, re.M)}
    return ids


def run(workspace, record_path, min_score):
    results = []

    def check(name, problems):
        results.append({"check": name, "ok": not problems, "problems": problems})

    brief_file = workspace / "00-brief.md"
    seated = roster(brief_file.read_text(encoding="utf-8")) if brief_file.is_file() else None
    if seated is None:
        check("roster", ["00-brief.md has no '## Roster' section"])
        seated = []
    else:
        check("roster", [f"core role not seated: {r}" for r in CORE if r not in seated])

    score_file = workspace / "scorecard.md"
    scores = latest_scores(score_file.read_text(encoding="utf-8")) if score_file.is_file() else None
    problems = []
    if scores is None:
        problems.append("scorecard.md has no table with a 'Role' header")
    else:
        for role in seated:
            text = scores.get(role)
            if text is None:
                problems.append(f"{role}: seated but has no scorecard row")
                continue
            m = re.match(r"\d+(?:\.\d+)?", text)
            if not m:
                problems.append(f"{role}: latest score unreadable ({text!r})")
            elif float(m.group()) < min_score:
                problems.append(f"{role}: latest score {m.group()} is below {min_score:g}")
        problems += [f"{r}: has a scorecard row but is not seated" for r in scores if r not in seated]
    check("scores", problems)

    if not record_path.is_file():
        check("open", [f"record not found: {record_path}"])
        record = ""
    else:
        record = record_path.read_text(encoding="utf-8")
        check("open", [f"OPEN row: {r}" for r in open_rows(record)])

    known = defined_ids(record)
    sources = [record_path] + sorted((workspace / "deliverables").rglob("*.md"))
    missing = []
    for path in sources:
        if path.is_file():
            for kind, n in CITE.findall(path.read_text(encoding="utf-8")):
                cid = f"{kind}-{n}"
                if cid not in known:
                    missing.append(f"{path.name}: {cid} is cited but not defined in the record")
    check("ids", sorted(set(missing)))

    bad = []
    files = set(workspace.rglob("*.md")) | ({record_path} if record_path.is_file() else set())
    for path in sorted(files):
        for line, rows in tables(path.read_text(encoding="utf-8")):
            width = len(rows[0])
            for i, row in enumerate(rows[1:], 1):
                if len(row) != width:
                    bad.append(f"{path.relative_to(workspace) if path.is_relative_to(workspace) else path.name}"
                               f": table at line {line}, row {i} has {len(row)} cells, header has {width}")
    check("tables", bad)
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description="Decide the planning-majlis gate for a workspace.")
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--record", type=Path, help="decision record (default: <workspace>/record.md)")
    ap.add_argument("--min-score", type=float, default=9)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not args.workspace.is_dir():
        print(f"gate: error workspace not found: {args.workspace}", file=sys.stderr)
        return 2
    results = run(args.workspace, args.record or args.workspace / "record.md", args.min_score)
    passed = all(r["ok"] for r in results)
    if args.json:
        print(json.dumps({"passed": passed, "checks": results}, indent=2))
    else:
        for r in results:
            print(f"{'PASS' if r['ok'] else 'FAIL'} {r['check']}")
            for p in r["problems"]:
                print(f"  - {p}")
        print("GATE PASSED" if passed else "GATE NOT PASSED")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
