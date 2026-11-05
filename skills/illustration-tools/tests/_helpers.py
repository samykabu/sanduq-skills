"""Shared paths and loaders for the Illustrate skill tests (stdlib only)."""

from __future__ import annotations

import importlib.util
import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

EXT_DIR = Path(__file__).resolve().parent.parent
SKILL_DIR = EXT_DIR / "skills" / "illustrate"
SCRIPTS = SKILL_DIR / "scripts"
ASSETS = SKILL_DIR / "assets"
REPO = EXT_DIR.parent.parent

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load(filename: str):
    """Import a script by file name (hyphenated names included)."""
    name = filename.removesuffix(".py").replace("-", "_")
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_cli(filename: str, *args) -> tuple[int, str]:
    """Run a script's main() in-process as `python scripts/<filename> *args` would: (exit code, stdout + stderr).

    For tests where the verdict is under test, not the process: one subprocess costs ~0.2 s, this ~5 ms.
    The real CLI path (argv, encoding) stays covered by the subprocess runs in test_verifier_*_scope.py.
    """
    module = load(filename)
    argv, sys.argv = sys.argv, [filename, *map(str, args)]
    out = io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(out):
            try:
                code = module.main()
            except SystemExit as exit:
                code = exit.code
                if isinstance(code, str):  # sys.exit("message") prints it and exits 1
                    print(code, file=sys.stderr)
                    code = 1
    finally:
        sys.argv = argv
    return code or 0, out.getvalue()


def baseline(filename: str) -> set[str]:
    path = SCRIPTS / filename
    if not path.is_file():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def core_examples() -> list[Path]:
    """Editorial examples `apply` must handle: every example except hand, terminal and consultant."""
    return [
        path
        for path in sorted(ASSETS.glob("example-*.html"))
        if not any(token in path.stem for token in ("-hand", "-terminal", "consultant"))
    ]
