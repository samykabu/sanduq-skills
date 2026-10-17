"""Saves PNGs of the v3 sample (1280 and 360 px, light and dark). Usage: python ui_v3_screenshots.py OUT_DIR"""
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))
from playwright.sync_api import sync_playwright  # noqa: E402
from sanduq_progress import theme  # noqa: E402
import test_ui_v3_browser as t  # noqa: E402

out = Path(sys.argv[1] if len(sys.argv) > 1 else HERE.parent / "screenshots")
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
    view = Path(tmp)
    for f in ("index.html", "base.css", "blocks.js"):
        shutil.copy(t.UI / f, view / f)
    theme.write_assets(view, theme.resolve_doc({}))
    t.write_data(view, t.fresh(t.load("ui_v3_sample.json")))
    browser = None
    for kw in ({}, {"channel": "chrome"}, {"channel": "msedge"}):
        try:
            browser = pw.chromium.launch(**kw)
            break
        except Exception:
            continue
    for width in (1280, 360):
        for scheme in ("light", "dark"):
            ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
            page = ctx.new_page()
            page.goto((view / "index.html").as_uri() + "#g=execute")
            page.wait_for_selector("h1")
            page.wait_for_timeout(300)
            page.screenshot(path=str(out / ("ui_v3_%d_%s.png" % (width, scheme))), full_page=True)
            ctx.close()
    browser.close()
