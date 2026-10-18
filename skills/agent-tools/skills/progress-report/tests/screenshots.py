"""Regenerate docs/assets/progress-*.png from the frozen #842 run, projected as v3 (needs Playwright + a Chromium)."""
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))
from playwright.sync_api import sync_playwright  # noqa: E402
from sanduq_progress import theme  # noqa: E402
import helpers  # noqa: E402
import test_ui_v3_browser as t  # noqa: E402

OUT = HERE.parent / "docs" / "assets"


def main():
    with tempfile.TemporaryDirectory() as base:
        report, _ = helpers.run842_report(base, schema="v3")
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        view = Path(tmp)
        for f in ("index.html", "base.css", "blocks.js"):
            shutil.copy(t.UI / f, view / f)
        theme.write_assets(view, theme.resolve_doc({}))
        t.write_data(view, t.fresh(report))
        browser = None
        for kw in ({}, {"channel": "chrome"}, {"channel": "msedge"}):
            try:
                browser = pw.chromium.launch(**kw)
                break
            except Exception:
                continue
        if browser is None:
            sys.exit("no Chromium available")
        for name, scheme, width, height in (("progress-light", "light", 1280, 1400),
                                             ("progress-dark", "dark", 1280, 1400),
                                             ("progress-narrow", "light", 360, 1600)):
            ctx = browser.new_context(viewport={"width": width, "height": height}, color_scheme=scheme)
            page = ctx.new_page()
            page.goto((view / "index.html").as_uri())
            page.wait_for_selector("h1")
            page.wait_for_timeout(300)
            page.screenshot(path=str(OUT / (name + ".png")))
            ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
