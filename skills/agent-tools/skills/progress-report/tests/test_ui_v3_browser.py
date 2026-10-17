"""Browser tests for the v3 Timeline layout (schema sanduq.progress.v3). Same skip rules as test_ui_browser.py."""
import copy
import datetime
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
UI = HERE.parent / "assets" / "ui"
FIX = HERE / "fixtures"
sys.path.insert(0, str(HERE.parent / "scripts"))
sys.path.insert(0, str(HERE))
import helpers  # noqa: E402
from sanduq_progress import model, theme  # noqa: E402
from sanduq_progress.paths import Ctx  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

PW = None
BROWSER = None
SKIP = "playwright/chromium unavailable"
UPDATE_WAIT = 30000
ORDER = ["v3-header", "v3-attention", "v3-orchestrator", "v3-stages", "v3-timeline", "v3-workstreams", "v3-decisions", "v3-runs", "v3-history"]
ISO = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")


def setUpModule():
    global PW, BROWSER, SKIP
    if sync_playwright is None:
        return
    try:
        PW = sync_playwright().start()
        for kw in ({}, {"channel": "chrome"}, {"channel": "msedge"}):
            try:
                BROWSER = PW.chromium.launch(**kw)
                SKIP = ""
                break
            except Exception as exc:
                SKIP = "playwright/chromium unavailable: " + str(exc).splitlines()[0][:80]
        if BROWSER is None:
            PW.stop()
            PW = None
    except Exception as exc:
        SKIP = "playwright failed to start: " + str(exc).splitlines()[0][:80]


def tearDownModule():
    if BROWSER:
        BROWSER.close()
    if PW:
        PW.stop()


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def fresh(proj, rev=None):
    """Shifts every timestamp so the snapshot is 'now'; the fixture keeps its real 2026-10 dates."""
    p = copy.deepcopy(proj)
    gen = datetime.datetime.strptime(p["generated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    delta = datetime.datetime.now(datetime.timezone.utc) - gen

    def walk(x):
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v) for v in x]
        if isinstance(x, str) and ISO.match(x):
            t = datetime.datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
            return (t + delta).strftime("%Y-%m-%dT%H:%M:%SZ")
        return x
    p = walk(p)
    if rev is not None:
        p["rev"] = rev
    return p


def write_data(view, proj):
    tmp = view / "data.js.tmp"
    tmp.write_text("window.__SANDUQ_PROGRESS__ = " + json.dumps(proj, ensure_ascii=False) + ";\n", encoding="utf-8")
    tmp.replace(view / "data.js")


@unittest.skipIf(sync_playwright is None, "playwright not installed")
class V3Test(unittest.TestCase):
    scheme = None
    layout = None
    width = 1280

    def setUp(self):
        if SKIP:
            self.skipTest(SKIP)
        self.view_tmp = tempfile.TemporaryDirectory()
        self.view = Path(self.view_tmp.name)
        for f in ("index.html", "base.css", "blocks.js"):
            shutil.copy(UI / f, self.view / f)
        theme.write_assets(self.view, theme.resolve_doc({}))
        if self.layout:
            (self.view / "layout.js").write_text('window.__SANDUQ_PROGRESS_LAYOUT__={"layout":"%s"};\n' % self.layout, encoding="utf-8")
        self.bctx = BROWSER.new_context(viewport={"width": self.width, "height": 900}, color_scheme=self.scheme)
        self.page = self.bctx.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))

    def tearDown(self):
        if getattr(self, "bctx", None):
            self.bctx.close()
            helpers.remove_tree(self.view_tmp)

    def open(self, proj=None, hash_=""):
        write_data(self.view, proj if proj is not None else fresh(load("ui_v3_sample.json")))
        self.page.goto((self.view / "index.html").as_uri() + hash_)
        self.page.wait_for_selector("h1")

    def text(self, sel):
        return self.page.inner_text(sel)

    def wait_text(self, sel, needle, timeout=UPDATE_WAIT):
        self.page.wait_for_function("([s,n])=>{const e=document.querySelector(s);return e&&e.textContent.includes(n)}", arg=[sel, needle], timeout=timeout)

    def hash(self):
        return self.page.evaluate("location.hash")

    def focused(self):
        return self.page.evaluate("document.activeElement && document.activeElement.getAttribute('data-k')")

    def open_runs(self):
        self.page.focus("#v3-runs summary")
        self.page.keyboard.press("Enter")
        self.page.wait_for_selector("#v3-runs table.runs")


class LayoutTests(V3Test):
    def test_sections_come_in_the_specified_order(self):
        self.open()
        ids = self.page.eval_on_selector_all("[data-v3]", "els=>els.map(e=>e.id)")
        self.assertEqual(ids, ORDER)
        self.assertEqual(self.page.eval_on_selector_all("#app > *", "els=>els.map(e=>e.id||e.className)")[:5],
                         ["v3-header", "v3-attention", "v3-orchestrator", "v3-stages", "v3cols"])
        self.assertEqual(self.errors, [])

    def test_header_attention_and_orchestrator_provenance(self):
        self.open()
        hdr = " ".join(self.text("#v3-header").split())
        for needle in ("Signal quality scoring", "Issue #842", "Stage pr", "in-progress", "current", "Next action Merge the pull request",
                       "active claim", "ago", "Snapshot", "UTC", "23 / 23", "14 / 16", "89 (5 failed or abandoned)"):
            self.assertIn(needle, hdr)
        att = self.text("#v3-attention")
        self.assertIn("codex hooks not approved", att)
        self.assertIn("no recovery recorded", att)
        orch = self.text("#v3-orchestrator")
        self.assertEqual(self.page.locator("#v3-orchestrator .prov.self").count(), 2)
        self.assertIn("self-reported", orch)
        self.assertIn("host hook", orch)
        self.assertIn("gpt-6.1-sol", orch)
        self.assertIn("unknown", orch)  # context and active have no value: no invented numbers
        self.assertIn("20h 5m", orch)

    def test_two_columns_side_by_side_on_desktop_and_stacked_on_narrow(self):
        self.open()
        box = lambda sel: self.page.eval_on_selector(sel, "e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.width]}")
        a, b = box("#v3-timeline"), box("#v3-workstreams")
        self.assertGreater(b[0], a[0] + a[2] - 2)
        self.assertAlmostEqual(a[1], b[1], delta=3)
        self.page.set_viewport_size({"width": 700, "height": 900})
        self.page.wait_for_timeout(150)
        a, b = box("#v3-timeline"), box("#v3-workstreams")
        self.assertGreater(b[1], a[1])
        self.assertAlmostEqual(a[0], b[0], delta=2)

    def test_workstreams_and_decisions(self):
        self.open()
        ws = self.text("#v3-workstreams")
        for needle in ("Workstream A", "Workstream B", "Shared", "9 / 9 done", "5 / 5 done", "codex gpt-6.1-sol", "to now"):
            self.assertIn(needle, ws)
        self.assertEqual(self.page.locator("#v3-workstreams .wsrow").count(), 3)
        self.assertFalse(self.page.locator("#v3-workstreams details.wsdone").first.evaluate("e=>e.open"))  # done is collapsed
        self.assertTrue(self.page.locator("#v3-workstreams details.wsdone .tchip").first.is_hidden())
        dec = " ".join(self.text("#v3-decisions").split())
        for needle in ("None pending", "C1Q1", "Which retry policy", "editor not recorded", "time not recorded", "Applied", "applied",
                       "Sources checked: workflow decisions, clarifications", "Unavailable: facts (absent), legacy board (unsupported)"):
            self.assertIn(needle, dec)
        self.assertLess(dec.lower().index("pending"), dec.lower().index("made"))
        self.assertEqual(self.page.get_attribute("#v3-decisions a", "href"), "https://github.com/example/repo/issues/842#issuecomment-1")

    def test_pending_decisions_are_listed_before_made_ones(self):
        p = fresh(load("ui_v3_sample.json"))
        made = p["decisions"]["made"][0]
        p["decisions"]["pending"] = [dict(copy.deepcopy(made), source_id="C2Q1", state="pending", answer=None, question="Pick a queue?", answered_at=None, applied=None)]
        self.open(p)
        dec = self.text("#v3-decisions")
        self.assertLess(dec.index("C2Q1"), dec.index("C1Q1"))


class GanttTests(V3Test):
    def test_one_row_per_selected_stage_with_markers_and_open_interval(self):
        p = fresh(load("ui_v3_sample.json"))
        p["stages"].append({"id": "waived", "label": "Excluded stage", "order": 99, "selected": False, "status": "excluded", "validity": "unknown",
                            "episodes": [], "unknown_runs": [], "run_count": 0, "failed_runs": 0, "run_time": {"value": None}, "models": [], "first_start": None, "last_end": None})
        self.open(p)
        self.assertEqual(self.page.locator("#v3-stages button.grow").count(), 16)
        self.assertNotIn("Excluded stage", self.text("#v3-stages"))
        self.assertEqual(self.page.locator("#v3-stages .fm").count(), 5)  # 2 failed + 3 abandoned
        self.assertEqual(self.page.locator("#v3-stages .gbar.open").count(), 1)
        self.assertIn("open", self.text("button[data-k='g-pr']"))
        self.assertIn("not started", self.text("button[data-k='g-finalize']"))
        self.assertIn("hatched bar is still open", self.text("#v3-stages"))
        # every bar stays inside its track
        bad = self.page.evaluate("[...document.querySelectorAll('.gbar')].filter(b=>b.offsetLeft<0||b.offsetLeft+b.offsetWidth>b.parentElement.offsetWidth+1).length")
        self.assertEqual(bad, 0)

    def test_gantt_detail_opens_with_keyboard_and_shows_unknown_group(self):
        self.open()
        self.page.focus("button[data-k='g-execute']")
        self.assertTrue(self.page.is_hidden("#v3-ep"))
        self.page.keyboard.press("Enter")
        self.page.wait_for_selector("#v3-ep:not([hidden])")
        detail = self.text("#v3-ep")
        self.assertIn("Execute: episodes", detail)
        self.assertIn("Episode 1", detail)
        self.assertIn("Episode unknown (4)", detail)
        self.assertEqual(self.page.get_attribute("button[data-k='g-execute']", "aria-expanded"), "true")
        self.assertIn("g=execute", self.hash())
        self.assertEqual(self.focused(), "g-execute")
        self.page.keyboard.press("Tab")
        self.page.keyboard.press("Shift+Tab")
        self.page.keyboard.press("Space")  # a button toggles on Space too
        self.page.wait_for_selector("#v3-ep[hidden]", state="attached")
        self.assertEqual(self.page.get_attribute("button[data-k='g-execute']", "aria-expanded"), "false")
        # a stage with two episodes and an open one
        self.page.click("button[data-k='g-tasks']")
        self.assertIn("Episode 2", self.text("#v3-ep"))
        self.assertIn("invalidated", self.text("#v3-ep"))
        self.page.click("button[data-k='g-pr']")
        self.assertIn("open", self.text("#v3-ep"))
        self.assertIn("running", self.text("#v3-ep"))

    def test_row_focus_is_visible(self):
        self.open()
        self.page.focus("button[data-k='g-scope']")
        self.assertNotEqual(self.page.evaluate("getComputedStyle(document.activeElement).outlineStyle"), "none")

    def test_unknown_timing_renders_unknown_not_a_guess(self):
        p = fresh(load("ui_v3_sample.json"))
        for s in p["stages"]:
            if s["id"] == "plan":
                s["first_start"] = s["last_end"] = None
        self.open(p)
        self.assertIn("timing unknown", self.text("button[data-k='g-plan']"))
        self.assertEqual(self.page.locator("button[data-k='g-plan'] .gbar").count(), 0)


class RunsTests(V3Test):
    def test_runs_collapsed_by_default_and_keyboard_operable(self):
        self.open()
        self.assertFalse(self.page.locator("#v3-runs details").first.evaluate("e=>e.open"))
        self.assertTrue(self.page.is_hidden("#v3-runs table"))
        self.assertIn("All runs (89)", self.text("#v3-runs summary"))
        self.open_runs()
        self.page.wait_for_function("location.hash.includes('o=runs')")
        self.assertEqual(self.page.locator("#v3-runs table.runs tbody tr").count(), 10)
        self.assertIn("Page 1 of 9", self.text("#v3-runs"))
        # failures first
        first5 = self.page.eval_on_selector_all("#v3-runs tbody tr", "els=>els.slice(0,5).map(e=>e.classList.contains('failrow'))")
        self.assertEqual(first5, [True] * 5)
        self.assertFalse(self.page.locator("#v3-runs tbody tr").nth(5).evaluate("e=>e.classList.contains('failrow')"))
        # tab order: search, status filter, then run buttons
        self.page.keyboard.press("Tab")
        self.assertEqual(self.focused(), "q")
        self.page.keyboard.press("Tab")
        self.assertEqual(self.focused(), "rs")
        self.page.keyboard.press("Tab")
        self.assertTrue(self.focused().startswith("run-"))
        key = self.focused()
        self.page.keyboard.press("Enter")
        self.assertEqual(self.page.get_attribute("[data-k='%s']" % key, "aria-expanded"), "true")
        self.assertEqual(self.page.locator("#v3-runs tr.rdetail").count(), 1)
        self.assertIn("Identity", self.text("#v3-runs tr.rdetail"))
        self.assertEqual(self.focused(), key)
        self.assertEqual(self.errors, [])

    def test_search_filter_and_pagination(self):
        self.open()
        self.open_runs()
        p = self.page
        p.fill("[data-k='q']", "t015")
        self.assertEqual(p.locator("#v3-runs tbody tr").count(), 2)  # the failed run and its linked retry
        self.assertIn("Showing 1 to 2 of 2 runs (filtered from 89)", self.text("#v3-runs .runcount"))
        self.assertIn("q=t015", self.hash())
        p.fill("[data-k='q']", "")
        p.select_option("[data-k='rs']", "failed")
        self.assertEqual(p.locator("#v3-runs tbody tr").count(), 2)
        self.assertIn("s=failed", self.hash())
        p.select_option("[data-k='rs']", "abandoned")
        self.assertEqual(p.locator("#v3-runs tbody tr").count(), 3)
        p.select_option("[data-k='rs']", "")
        p.fill("[data-k='q']", "no-such-run-xyz")
        self.assertIn("No runs match", self.text("#v3-runs .runcount"))
        p.fill("[data-k='q']", "")
        self.assertIn("Page 1 of 9", self.text("#v3-runs"))
        p.click("[data-k='pg-next']")
        self.assertIn("Page 2 of 9", self.text("#v3-runs"))
        self.assertIn("p=2", self.hash())
        self.assertEqual(p.locator("#v3-runs tbody tr.failrow").count(), 0)
        for _ in range(7):
            p.click("[data-k='pg-next']")
        self.assertIn("Page 9 of 9", self.text("#v3-runs"))
        p.keyboard.press("Enter")  # Next is inert on the last page and must keep focus
        self.assertIn("Page 9 of 9", self.text("#v3-runs"))
        self.assertEqual(p.locator("#v3-runs tbody tr").count(), 9)  # 89 runs: last page holds 9
        self.assertEqual(self.focused(), "pg-next")  # focus survives hitting the end
        p.click("[data-k='pg-prev']")
        self.assertIn("Page 8 of 9", self.text("#v3-runs"))
        p.select_option("[data-k='rs']", "unverified")  # a new filter returns to page 1
        self.assertNotIn("p=", self.hash())
        self.assertEqual(p.locator("#v3-runs tbody tr").count(), 3)

    def test_dispatch_intents_are_listed_apart_from_runs(self):
        self.open()
        self.open_runs()
        self.assertIn("Dispatch intents (1)", self.text("#v3-runs"))
        self.assertIn("intent-9", self.text("#v3-runs .dispatch"))
        self.assertIn("not counted as runs", self.text("#v3-runs .dispatch"))
        self.assertNotIn("intent-9", self.text("#v3-runs table"))


class TimelineTests(V3Test):
    def test_curated_timeline_is_bounded_with_show_all(self):
        self.open()
        rows = self.page.locator("#v3-timeline li.tl-row")
        self.assertEqual(rows.count(), 12)
        self.assertIn("Showing the latest 12 of 23", self.text("#v3-timeline"))
        self.assertIn("PR opened", self.text("#v3-timeline"))
        self.page.click("[data-k='tl-all']")
        self.assertEqual(rows.count(), 23)
        self.assertIn("tl-all", self.hash())
        self.assertEqual(self.page.get_attribute("[data-k='tl-all']", "aria-expanded"), "true")
        self.assertIn("Scope accepted", self.text("#v3-timeline"))
        # an expandable row opens on Enter and says what it links to
        self.page.focus("[data-k='tl-tl-08']")
        self.page.keyboard.press("Enter")
        self.assertIn("refs:", self.text("#v3-timeline"))
        self.assertIn("run-", self.text("#v3-timeline li.tl-row.k-failure details[open]"))


class RefreshTests(V3Test):
    def test_expanded_filter_page_and_focus_survive_a_refresh(self):
        self.open()
        p = self.page
        p.click("[data-k='tl-all']")
        p.focus("[data-k='tl-tl-04']")
        p.keyboard.press("Enter")
        p.click("button[data-k='g-execute']")
        p.click("[data-k='wsd-A']")
        self.open_runs()
        p.fill("[data-k='q']", "run-0")
        p.click("[data-k='pg-next']")
        p.click("[data-k='pg-next']")
        p.focus("[data-k^='run-run-']")
        key = self.focused()
        p.keyboard.press("Enter")
        before = {
            "hash": self.hash(),
            "rows": p.locator("#v3-runs tbody tr").count(),
            "page": self.text("#v3-runs .pager"),
        }
        newer = fresh(load("ui_v3_sample.json"), rev=41)
        newer["feature"]["title"] = "Renamed feature"
        write_data(self.view, newer)
        self.wait_text("h1", "Renamed feature")
        self.assertEqual(self.hash(), before["hash"])
        self.assertEqual(p.locator("#v3-runs tbody tr").count(), before["rows"])
        self.assertEqual(self.text("#v3-runs .pager"), before["page"])
        self.assertEqual(p.input_value("[data-k='q']"), "run-0")
        self.assertEqual(p.locator("#v3-timeline li.tl-row").count(), 23)
        self.assertTrue(p.locator("[data-k='tl-tl-04']").evaluate("e=>e.parentElement.open"))
        self.assertEqual(p.get_attribute("button[data-k='g-execute']", "aria-expanded"), "true")
        self.assertIn("Episode unknown", self.text("#v3-ep"))
        self.assertTrue(p.locator("[data-k='wsd-A']").evaluate("e=>e.parentElement.open"))
        self.assertEqual(p.get_attribute("[data-k='%s']" % key, "aria-expanded"), "true")
        self.assertEqual(self.focused(), key)
        # a reload restores the same view from the hash
        p.reload()
        p.wait_for_selector("h1")
        self.assertEqual(p.input_value("[data-k='q']"), "run-0")
        self.assertEqual(self.text("#v3-runs .pager"), before["page"])
        self.assertEqual(self.errors, [])

    def test_focus_in_the_search_box_keeps_the_caret_across_a_refresh(self):
        self.open()
        self.open_runs()
        self.page.fill("[data-k='q']", "abcdef")
        self.page.evaluate("document.querySelector(\"[data-k='q']\").setSelectionRange(2,3)")
        write_data(self.view, fresh(load("ui_v3_sample.json"), rev=50))
        self.page.evaluate("window.__q = document.querySelector(\"[data-k='q']\")")
        self.page.wait_for_function("document.querySelector(\"[data-k='q']\") !== window.__q", timeout=UPDATE_WAIT)
        self.assertEqual(self.focused(), "q")
        self.assertEqual(self.page.evaluate("[document.activeElement.selectionStart, document.activeElement.selectionEnd]"), [2, 3])


class V3RobustnessTests(V3Test):
    def test_hostile_strings_render_as_text(self):
        p = fresh(load("ui_v3_sample.json"))
        evil = '<img src=x onerror="window.__PWNED__=1"><script>window.__PWNED__=1</script>'
        p["feature"]["title"] = evil
        p["timeline"][-1]["text"] = evil
        p["runs"][0]["summary"] = evil
        p["runs"][0]["worker_status"] = "failed"
        p["attention"][0]["text"] = evil
        p["decisions"]["made"][0]["question"] = evil
        p["decisions"]["made"][0]["url"] = "javascript:window.__PWNED__=1"
        p["stages"][0]["label"] = evil
        self.open(p)
        self.open_runs()
        self.assertIsNone(self.page.evaluate("window.__PWNED__ || null"))
        self.assertEqual(self.page.locator("main script, main img").count(), 0)
        self.assertIn("<script>window.__PWNED__=1</script>", self.text("h1"))
        self.assertEqual(self.page.locator("a[href^='javascript']").count(), 0)
        self.assertEqual(self.errors, [])

    def test_edge_report_plan_mode_without_stages_workstreams_or_decisions(self):
        self.open(fresh(load("ui_v3_edge.json")))
        ids = self.page.eval_on_selector_all("[data-v3]", "els=>els.map(e=>e.id)")
        self.assertEqual(ids, ORDER)
        self.assertIn("docs/plan.md", self.text("#v3-header"))
        self.assertNotIn("Stage", self.text("#v3-header .meta"))
        self.assertIn("This plan has no Workflow stages", self.text("#v3-stages"))
        self.assertEqual(self.page.locator("#v3-stages button.grow").count(), 0)
        self.assertIn("No workstreams are recorded", self.text("#v3-workstreams"))
        self.assertIn("None pending", self.text("#v3-decisions"))
        self.assertIn("None recorded.", self.text("#v3-decisions"))
        self.assertIn("Sources checked: workflow decisions. Unavailable: clarifications (unsupported).", " ".join(self.text("#v3-decisions").split()))
        self.assertIn("No curated events", self.text("#v3-timeline"))
        self.assertIn("Nothing needs attention", self.text("#v3-attention"))
        self.assertIn("All runs (0)", self.text("#v3-runs"))
        self.assertGreaterEqual(self.text("#v3-orchestrator").count("unknown"), 5)
        self.assertEqual(self.page.locator("#v3-orchestrator .fid").count(), 0)  # nothing is dressed up as measured
        self.assertEqual(self.errors, [])
        self.page.focus("#v3-runs summary")
        self.page.keyboard.press("Enter")
        self.assertIn("No runs match", self.text("#v3-runs"))

    def test_stale_banner_still_works_for_v3(self):
        p = load("ui_v3_sample.json")
        p = fresh(p)
        p["generated_at"] = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.open(p)
        self.assertIn("Stale", self.text("#banners"))


class CompatibilityTests(V3Test):
    layout = "classic"

    def test_classic_layout_renders_the_v2_view_unchanged_for_a_v2_report(self):
        p = fresh(load("projection-sample.json"))
        p["generated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.open(p)
        self.assertEqual(self.page.locator("[data-v3]").count(), 0)
        self.assertEqual(self.page.locator("#b-lanes tbody tr").count(), 3)
        self.assertIn("Add dependencies when creating a task", self.text("h1"))
        self.assertEqual(self.errors, [])

    def test_classic_layout_does_not_crash_on_a_v3_report(self):
        self.open()
        self.assertEqual(self.page.locator("[data-v3]").count(), 0)
        self.assertIn("classic layout needs a v2 report", self.text("#app"))
        self.assertIn("Signal quality scoring", self.text("h1"))
        self.assertEqual(self.errors, [])


class V2DefaultTests(V3Test):
    def test_a_v2_report_renders_classic_with_the_timeline_default(self):
        p = fresh(load("projection-sample.json"))
        self.open(p)
        self.assertEqual(self.page.locator("[data-v3]").count(), 0)
        ids = self.page.eval_on_selector_all("#app > *", "els=>els.map(e=>(e.querySelector('.body')||{}).id||e.tagName)")
        self.assertEqual(ids[:3], ["HEADER", "b-decisions", "b-blockers"])
        self.assertEqual(self.errors, [])

    def test_a_timeline_layout_setting_also_renders_v3(self):
        (self.view / "layout.js").write_text('window.__SANDUQ_PROGRESS_LAYOUT__={"layout":"timeline"};\n', encoding="utf-8")
        self.open()
        self.assertEqual(self.page.locator("[data-v3]").count(), len(ORDER))


class NarrowTests(V3Test):
    width = 360

    def test_no_page_scroll_while_the_gantt_scrolls_inside_its_own_box(self):
        self.open()
        p = self.page
        self.assertLessEqual(p.evaluate("document.documentElement.scrollWidth"), 360)
        box = p.evaluate("(()=>{const e=document.querySelector('.gscroll');return {sw:e.scrollWidth,cw:e.clientWidth,ox:getComputedStyle(e).overflowX}})()")
        self.assertEqual(box["ox"], "auto")
        self.assertGreater(box["sw"], box["cw"] + 100)
        self.assertLessEqual(box["cw"], 360)
        p.evaluate("document.querySelector('.gscroll').scrollLeft = 200")
        self.assertGreater(p.evaluate("document.querySelector('.gscroll').scrollLeft"), 0)
        self.assertLessEqual(p.evaluate("document.documentElement.scrollWidth"), 360)
        # everything open at once still fits
        p.click("button[data-k='g-execute']")
        p.click("[data-k='tl-all']")
        p.evaluate("document.querySelector('.gscroll').scrollLeft = 120")
        newer = fresh(load("ui_v3_sample.json"), rev=77)
        newer["feature"]["title"] = "Scrolled and refreshed"
        write_data(self.view, newer)
        self.wait_text("h1", "Scrolled and refreshed")
        self.assertEqual(p.evaluate("document.querySelector('.gscroll').scrollLeft"), 120)  # the Gantt keeps its place across a refresh
        self.open_runs()
        p.focus("[data-k^='run-run-']")
        p.keyboard.press("Enter")
        self.assertLessEqual(p.evaluate("document.documentElement.scrollWidth"), 360)
        self.assertEqual(p.evaluate("(()=>{const a=document.querySelector('#v3-timeline').getBoundingClientRect(),b=document.querySelector('#v3-workstreams').getBoundingClientRect();return b.top>=a.bottom-1&&Math.abs(a.left-b.left)<2})()"), True)
        self.assertEqual(self.errors, [])

    def test_narrow_edge_report_and_hostile_ids_do_not_widen_the_page(self):
        p = fresh(load("ui_v3_sample.json"))
        p["runs"][0]["run_id"] = "x" * 200
        p["runs"][0]["identity"] = "y" * 200
        p["timeline"][-1]["text"] = "z" * 300
        p["workstreams"][0]["label"] = "w" * 200
        self.open(p)
        self.open_runs()
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 360)
        self.open(fresh(load("ui_v3_edge.json")))
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 360)


class DarkTests(V3Test):
    scheme = "dark"

    def test_dark_tokens_reach_the_gantt_and_chips(self):
        self.open()
        self.assertEqual(self.page.evaluate("getComputedStyle(document.body).backgroundColor"), "rgb(18, 25, 22)")
        bar = self.page.evaluate("getComputedStyle(document.querySelector('.gbar')).backgroundColor")
        self.assertNotEqual(bar, "rgba(0, 0, 0, 0)")
        self.assertEqual(self.errors, [])


# ---- reports built by the real projection (model_v3), not only the ui_v3_*.json fixtures --------------------------------------

def synthetic_report(ledger=(), lifecycle=(), now="2026-10-17T14:00:00Z"):
    """The v3 document model.build gives for a small project with these delegation attempts and lifecycle events."""
    with tempfile.TemporaryDirectory() as base:
        root = Path(base)
        (root / ".specify").mkdir()
        feature = root / "specs" / "001-demo"
        (feature / "workflow").mkdir(parents=True)
        shutil.copyfile(FIX / "tasks.md", feature / "tasks.md")
        (feature / "workflow" / "delegations.json").write_text(json.dumps({"feature": "specs/001-demo", "attempts": list(ledger)}), encoding="utf-8")
        (feature / "workflow" / "lifecycle.jsonl").write_text("".join(json.dumps(e) + "\n" for e in lifecycle), encoding="utf-8")
        moment = datetime.datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        return model.build(Ctx(root, "specs/001-demo"), moment, 1, {}, schema="v3")


def attempt(run_id, stage, status="failed", start="2026-10-17T10:00:00Z", end="2026-10-17T10:10:00Z", **extra):
    row = {"identity": "specs/001-demo/stage:" + stage, "run_id": run_id, "status": status, "started_at": start, "ended_at": end,
           "requested_model": "m", "actual_model": "m", "actual_model_evidence": "driver-result"}
    row.update(extra)
    return row


def life(n, event, stage, at, **extra):
    row = {"v": 1, "event_id": "e%d" % n, "workflow_run_id": "wr", "generation": n, "at": at, "stage": stage, "event": event, "episode_id": None,
           "claim_id": None, "caused_by_claim_id": None, "candidate_run_id": None, "delegation_run_ids": [], "reason": None}
    row.update(extra)
    return row


class RealProjectionTests(V3Test):
    def run842(self):
        with tempfile.TemporaryDirectory() as base:
            report, _ = helpers.run842_report(base, schema="v3")
        return fresh(report)

    def test_real_run_842_output_renders_every_section_without_errors(self):
        report = self.run842()
        self.open(report)
        self.assertEqual(self.page.eval_on_selector_all("[data-v3]", "els=>els.map(e=>e.id)"), ORDER)
        shown = [s for s in report["stages"] if s["selected"] and s["status"] != "excluded"]
        self.assertEqual(self.page.locator("#v3-stages button.grow").count(), len(shown))
        self.assertEqual(self.page.locator("#v3-stages .gbar.open").count(), 0)  # nothing in the frozen run is open
        self.assertIn("All runs (89)", self.text("#v3-runs summary"))
        self.assertIn("History (", self.text("#v3-history summary"))
        self.assertEqual(self.errors, [])

    def test_a_timeline_run_reference_is_a_keyboard_link_that_opens_and_focuses_the_run(self):
        report = self.run842()
        failure = next(e for e in report["timeline"] if e["kind"] == "failure")
        run_id = failure["refs"][0]
        self.open(report)
        self.page.click("[data-k='tl-all']")
        self.page.focus("[data-k='tl-%s']" % failure["id"])
        self.page.keyboard.press("Enter")
        link = self.page.locator("#v3-timeline li.k-failure details[open] button.reflink", has_text=run_id).first
        link.focus()
        self.page.keyboard.press("Enter")
        self.page.wait_for_function("location.hash.includes('runs')")
        self.assertTrue(self.page.locator("#v3-runs details").first.evaluate("e=>e.open"))
        self.assertEqual(self.focused(), "run-" + run_id)
        self.assertEqual(self.page.get_attribute("[data-k='run-%s']" % run_id, "aria-expanded"), "true")
        self.assertIn("Identity", self.text("#v3-runs tr.rdetail"))
        self.assertEqual(self.errors, [])

    def test_a_run_on_a_later_page_is_found_by_the_link(self):
        report = self.run842()
        last = min((r for r in report["runs"] if r["worker_status"] not in ("failed", "abandoned")), key=lambda r: r["started_at"] or "")  # the oldest successful run sorts onto the last page
        self.assertNotIn(last["worker_status"], ("failed", "abandoned"))
        report["timeline"].append({"id": "tl-last", "at": report["generated_at"], "kind": "note", "text": "look at the oldest run", "refs": [last["run_id"]], "fidelity": "recorded"})
        self.open(report)
        self.page.click("[data-k='tl-all']")
        self.page.focus("[data-k='tl-tl-last']")
        self.page.keyboard.press("Enter")
        self.page.locator("#v3-timeline button.reflink", has_text=last["run_id"]).first.click()
        self.assertEqual(self.focused(), "run-" + last["run_id"])
        self.assertTrue(self.page.locator("[data-k='run-%s']" % last["run_id"]).is_visible())
        self.assertNotIn("Page 1 of", self.text("#v3-runs .pager"))
        self.assertEqual(self.errors, [])

    def test_a_stage_reference_selects_the_stage_row_and_its_episodes(self):
        report = self.run842()
        stage = next(e for e in report["timeline"] if e["kind"] == "stage" and e["refs"] and e["refs"][0] in {s["id"] for s in report["stages"]})
        sid = stage["refs"][0]
        self.open(report)
        self.page.click("[data-k='tl-all']")
        self.page.focus("[data-k='tl-%s']" % stage["id"])
        self.page.keyboard.press("Enter")
        self.page.locator("#v3-timeline li.k-stage details[open] button.reflink", has_text=sid).first.click()
        self.assertEqual(self.focused(), "g-" + sid)
        self.assertTrue(self.page.is_visible("#v3-ep"))
        self.assertIn("g=" + sid, self.hash())

    def test_history_lists_aliases_and_unresolved_lanes_with_stable_ids_and_links_resolvable_ones(self):
        report = self.run842()
        aliases = report["history"]["lane_aliases"]
        self.assertTrue(aliases)
        self.open(report)
        self.assertFalse(self.page.locator("#v3-history details").first.evaluate("e=>e.open"))  # collapsed by default
        self.page.focus("#v3-history summary")
        self.page.keyboard.press("Enter")
        self.page.wait_for_function("location.hash.includes('hist')")
        ids = self.page.eval_on_selector_all("#v3-history li[id]", "els=>els.map(e=>e.id)")
        self.assertEqual(len(ids), len(aliases) + len(report["history"]["unresolved"]))
        self.assertEqual(len(set(ids)), len(ids))
        self.page.reload()
        self.page.wait_for_selector("h1")
        self.assertEqual(self.page.eval_on_selector_all("#v3-history li[id]", "els=>els.map(e=>e.id)"), ids)  # stable across loads
        self.assertTrue(self.page.locator("#v3-history details").first.evaluate("e=>e.open"))  # and the open state is kept
        self.assertEqual(self.errors, [])

    def test_a_history_alias_that_points_at_a_run_is_a_link_to_that_run(self):
        p = fresh(load("ui_v3_sample.json"))
        self.open(p, "#o=hist")
        self.assertEqual(self.page.locator("#v3-history li button.reflink").count(), 2)  # L1 -> A (workstream) and L2 -> run:run-044
        self.page.locator("#v3-history li", has_text="L2").locator("button.reflink").focus()
        self.page.keyboard.press("Enter")
        self.assertEqual(self.focused(), "run-run-044")
        self.assertEqual(self.page.locator("#v3-history li", has_text="W7").locator("button.reflink").count(), 0)  # identity: has no target here
        self.assertIn("Retired scratch lane", self.text("#v3-history"))
        self.assertIn("codex-worker-3", self.text("#v3-history"))

    def test_hostile_ids_from_real_projection_output_render_and_navigate(self):
        ids = ["constructor", "__proto__", "hasOwnProperty", "toString"]
        ledger = [attempt(i, i, claim_id="c-" + i, start="2026-10-17T10:0%d:00Z" % n) for n, i in enumerate(ids)]
        events = [life(n, "claim", i, "2026-10-17T09:0%d:00Z" % n, episode_id="ep-" + i, claim_id="c-" + i, delegation_run_ids=[i]) for n, i in enumerate(ids, 1)]
        events.append(life(9, "paused", None, "2026-10-17T11:00:00Z", reason="context budget"))
        report = fresh(synthetic_report(ledger, events))
        self.assertEqual({r["run_id"] for r in report["runs"]}, set(ids))
        report["timeline"].append({"id": "tl-x", "at": report["generated_at"], "kind": "note", "text": "refs", "refs": ["constructor", "toString", "__proto__", "nowhere"], "fidelity": "recorded"})
        self.open(report)
        self.assertEqual(self.errors, [])
        self.assertEqual(self.page.locator("#v3-stages button.grow").count(), len([s for s in report["stages"] if s["selected"]]))
        self.assertEqual(self.page.locator("#v3-stages .fm").count(), 4)  # one failure marker per hostile stage
        self.page.click("button[data-k='g-constructor']")
        self.assertIn("Constructor: episodes", self.text("#v3-ep"))
        self.page.focus("[data-k='tl-tl-x']")
        self.page.keyboard.press("Enter")
        row = self.page.locator("#v3-timeline li:has(summary[data-k='tl-tl-x'])")
        self.assertEqual(row.locator("button.reflink").count(), 3)  # the unknown ref stays plain text
        self.assertIn("Feature paused: context budget", self.text("#v3-timeline"))
        row.locator("button.reflink", has_text="__proto__").click()
        self.assertEqual(self.focused(), "run-__proto__")
        self.assertEqual(self.page.locator("#v3-runs table.runs tbody tr:not(.rdetail)").count(), 4)
        self.assertEqual(self.errors, [])


class TimingAndDecisionTests(V3Test):
    def test_only_an_open_stage_grows_to_now_and_an_unknown_end_is_drawn_apart(self):
        p = fresh(load("ui_v3_sample.json"))
        for s in p["stages"]:
            if s["id"] == "plan":
                s["last_end"], s["open"], s["timing"] = None, False, "end-unknown"
            if s["id"] == "scope":
                s["last_end"], s["open"], s["timing"] = None, True, "open"
        self.open(p)
        plan, scope = "button[data-k='g-plan']", "button[data-k='g-scope']"
        self.assertEqual(self.page.locator(plan + " .gbar.endunk").count(), 1)
        self.assertEqual(self.page.locator(plan + " .gbar.open").count(), 0)
        self.assertIn("end unknown", self.text(plan))
        self.assertEqual(self.page.locator(scope + " .gbar.open").count(), 1)
        self.assertEqual(self.page.locator("#v3-stages .gbar.open").count(), 2)
        width = lambda sel: self.page.eval_on_selector(sel, "e=>e.getBoundingClientRect().width")
        self.assertLess(width(plan + " .gbar"), 40)
        self.assertGreater(width(scope + " .gbar"), 300)
        self.assertIn("broken edge", self.text("#v3-stages"))

    def test_a_document_without_the_open_flag_never_extends_a_bar(self):
        p = fresh(load("ui_v3_sample.json"))
        for s in p["stages"]:
            s.pop("open", None)
            s.pop("timing", None)
        self.open(p)
        self.assertEqual(self.page.locator("#v3-stages .gbar.open").count(), 0)
        self.assertEqual(self.page.locator("button[data-k='g-pr'] .gbar.endunk").count(), 1)

    def selected(self, options, value, kind="single"):
        p = fresh(load("ui_v3_sample.json"))
        made = p["decisions"]["made"][0]
        made["options"], made["answer"] = options, {"kind": kind, "value": value}
        self.open(p)
        return self.page.evaluate(
            "(id)=>{const li=[...document.querySelectorAll('#v3-decisions li')].find(l=>l.querySelector('h3')&&l.querySelector('h3').textContent.includes(id));"
            "return [...li.querySelectorAll('.opts span')].map(e=>e.classList.contains('sel'))}", made["source_id"])

    def test_a_letter_answer_picks_the_option_at_that_position(self):
        self.assertEqual(self.selected(["First choice", "Second choice", "Third choice"], "B"), [False, True, False])

    def test_an_option_that_starts_with_the_letter_is_not_picked_by_prefix(self):
        self.assertEqual(self.selected(["Because it is safe", "Another way"], "A"), [True, False])  # position A is the first option
        self.assertEqual(self.selected(["Always retry", "Other", "Bad idea"], "B"), [False, True, False])  # not "Bad idea" (starts with B)

    def test_without_options_the_answer_matches_nothing_and_free_text_must_be_exact(self):
        self.assertEqual(self.selected([], "A"), [])
        self.assertEqual(self.selected(["Retry once", "Retry"], "Retry", kind="text"), [False, True])  # exact, never the prefix "Retry once"
        self.assertEqual(self.selected(["Retry once", "Other"], "Ret", kind="text"), [False, False])
        self.assertEqual(self.selected(["alpha", "beta", "gamma"], ["A", "C"], kind="multiple"), [True, False, True])

    def test_decision_evidence_renders_with_links_only_for_safe_urls(self):
        p = fresh(load("ui_v3_sample.json"))
        made = p["decisions"]["made"][0]
        made["evidence"] = ["comment 11 https://github.com/example/repo/issues/1#c", "plain evidence"]
        made["evidence_links"] = [{"text": made["evidence"][0], "url": "https://github.com/example/repo/issues/1#c"},
                                  {"text": made["evidence"][1], "url": "javascript:window.__PWNED__=1"}]
        made["applied"] = {"at": (made.get("applied") or {}).get("at"), "evidence": ["spec.md FR-004", "comment 12 ready"]}
        self.open(p)
        self.assertEqual(self.page.locator("#v3-decisions ul.evid li").count(), 2)
        self.assertEqual(self.page.locator("#v3-decisions ul.evid a").count(), 1)
        self.assertEqual(self.page.get_attribute("#v3-decisions ul.evid a", "href"), "https://github.com/example/repo/issues/1#c")
        self.assertIn("spec.md FR-004; comment 12 ready", self.text("#v3-decisions"))
        self.assertIsNone(self.page.evaluate("window.__PWNED__ || null"))

    def test_a_mixed_generation_snapshot_shows_a_banner(self):
        p = fresh(load("ui_v3_sample.json"))
        p["collection"]["inconsistent_sources"] = ["facts"]
        self.open(p)
        self.assertIn("Snapshot may mix generations", self.text("#banners"))


if __name__ == "__main__":
    unittest.main()
