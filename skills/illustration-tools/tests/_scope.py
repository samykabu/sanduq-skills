"""Batched scope calls shared by the cross-type and hand-variant scope tests: one real CLI run per verifier and batch."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from _helpers import SCRIPTS


def run(kind: str, *paths: Path) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / f"verify-{kind}.py"), *map(str, paths)],
        capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    return result.returncode, result.stdout + result.stderr


def assert_all_out_of_scope(case, kind: str, *paths: Path) -> None:
    """Every path is skipped: a per-path skip line, or the verifier's skipped-file count covering all of them."""
    code, output = run(kind, *paths)
    case.assertEqual(code, 0, output)
    if f"({len(paths)} file(s) skipped as out of scope)" in output:
        return
    lines = [line for line in output.splitlines() if "out of scope" in line]
    for path in paths:
        case.assertTrue(any(path.name in line for line in lines), f"{path.name} not reported out of scope:\n{output}")


def assert_all_checked(case, kind: str, *paths: Path) -> None:
    code, output = run(kind, *paths)
    case.assertEqual(code, 0, output)
    case.assertNotIn("out of scope", output)


def add_per_kind(cls, kinds, name: str, body) -> None:
    """One test method per verifier, so xdist can spread them and unittest still discovers them."""
    for kind in kinds:
        setattr(cls, f"test_{name}_{kind.replace('-', '_')}", lambda self, kind=kind: body(self, kind))
