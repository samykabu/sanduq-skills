"""Builds the hand-modelled v3 UI fixtures (ui_v3_sample.json, ui_v3_edge.json). Deterministic; run with python."""
import datetime as dt
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "fixtures"
D0 = dt.datetime(2026, 10, 16, 0, 0, tzinfo=dt.timezone.utc)
FMT = "%Y-%m-%dT%H:%M:%SZ"


def at(day, hh, mm=0):
    return (D0 + dt.timedelta(days=day, hours=hh, minutes=mm)).strftime(FMT)


def plus(iso, minutes):
    t = dt.datetime.strptime(iso, FMT).replace(tzinfo=dt.timezone.utc)
    return (t + dt.timedelta(minutes=minutes)).strftime(FMT)


def M(value, source="delegation-ledger", fidelity="exact", observed="2026-10-17T14:05:00Z"):
    return {"value": value, "source": source if value is not None else "none", "observed_at": observed if value is not None else None,
            "fidelity": fidelity if value is not None else "unknown"}


# id, label, first_start, last_end, run count
STAGES = [
    ("scope", "Scope", at(0, 17, 10), at(0, 17, 52), 3),
    ("specify", "Specify", at(0, 17, 55), at(0, 18, 14), 4),
    ("clarify", "Clarify", at(0, 18, 16), at(0, 20, 50), 3),
    ("plan", "Plan", at(0, 20, 52), at(0, 21, 10), 5),
    ("tasks", "Tasks", at(0, 21, 10), at(1, 5, 38), 6),
    ("analyze", "Analyze", at(0, 21, 24), at(1, 5, 20), 5),
    ("assure", "Assure", at(0, 21, 31), at(0, 21, 37), 3),
    ("execute", "Execute", at(0, 21, 37), at(1, 1, 30), 31),
    ("converge", "Converge", at(1, 1, 31), at(1, 2, 17), 3),
    ("verify", "Verify", at(1, 2, 17), at(1, 3, 40), 6),
    ("review", "Review", at(1, 3, 40), at(1, 5, 38), 9),
    ("manual", "User manual", at(1, 5, 40), at(1, 6, 10), 3),
    ("issues", "Tasks to issues", at(1, 6, 22), at(1, 6, 50), 4),
    ("ready", "Ready", at(1, 7, 0), at(1, 7, 40), 3),
    ("pr", "Pull request", at(1, 13, 20), None, 1),
    ("finalize", "Finalize", None, None, 0),
]
TASKS = [("T%03d" % i, "A" if i <= 9 else "B" if i <= 18 else "Shared") for i in range(1, 24)]
WS_OF = dict(TASKS)
CODEX = ["gpt-6.1-sol", "gpt-6-astra"]
CLAUDE = ["claude-sonnet-5-5", "claude-opus-5-5"]


def build_runs():
    runs = []

    def run(stage, start, minutes, status, tasks=(), ep=True, retry_of=None, summary=""):
        i = len(runs) + 1
        rid = "run-%03d" % i
        h = "codex" if i % 3 else "claude"
        model = (CODEX if h == "codex" else CLAUDE)[i % 2]
        gone = status == "abandoned"
        runs.append({
            "run_id": rid, "identity": "specs/842-signal-quality/%s" % (tasks[0] if tasks else stage), "stage": stage,
            "tasks": list(tasks), "episode_id": ("ep-%s-1" % stage) if ep else None, "workstream": WS_OF.get(tasks[0]) if tasks else None,
            "harness": h, "requested_model": model, "actual_model": M(None if gone else model, "driver-result"),
            "effort": M("high", "attempt", "partial" if i % 5 else "exact"),
            "started_at": start, "ended_at": None if gone else plus(start, minutes), "duration": M(None if gone else minutes * 60),
            "worker_status": status,
            "evidence_accepted": None if status in ("unverified", "abandoned") else status == "successful",
            "candidate_accepted": None if status in ("unverified", "abandoned", "failed") else True,
            "retry_of": retry_of, "summary": summary or ("%s run for %s" % (stage, tasks[0] if tasks else stage))})
        return rid

    def spread(idx, extra=None, unknown=0):
        stage, _, first, last, count = STAGES[idx]
        total = int((dt.datetime.strptime(last, FMT) - dt.datetime.strptime(first, FMT)).total_seconds() // 60)
        step = max(1, total // count)
        for k in range(count):
            dur = max(2, min(20, step - 1 if step > 2 else 2))
            st = plus(last, -dur) if k == count - 1 else plus(first, k * step)
            run(stage, st, dur, (extra or {}).get(k, "successful"), ep=k >= unknown)

    for idx in range(7):
        spread(idx, unknown=2 if STAGES[idx][0] == "analyze" else 0)
    order = []
    for t, _ in TASKS:
        if t in ("T015", "T016"):
            order += [(t, "failed"), (t, "retry")]
        elif t == "T018":
            order += [(t, "successful"), (t, "successful"), (t, "abandoned")]
        else:
            order.append((t, "successful"))
    order += [("T019", "successful"), ("T020", "successful"), ("T021", "successful"), ("T023", "successful")]
    assert len(order) == 31, len(order)
    failed, ex0 = {}, STAGES[7][2]
    for k, (t, st) in enumerate(order):
        start = plus(ex0, k * 7)
        if st == "retry":
            run("execute", start, 14, "successful", (t,), retry_of=failed[t], summary="Retry of %s" % failed[t])
        else:
            rid = run("execute", start, 12 + (k % 5) * 2, st, (t,), ep=k < 27,
                      summary={"failed": "Run did not pass its own checks", "abandoned": "Review-fix round abandoned"}.get(st, ""))
            if st == "failed":
                failed[t] = rid
    spread(8)
    spread(9, {4: "unverified"})
    spread(10, {3: "abandoned", 7: "unverified"})
    spread(11, {2: "unverified"})
    spread(12, {1: "abandoned"})
    spread(13)
    run("pr", at(1, 13, 20), 25, "successful", summary="Open the pull request")
    return runs


def build_sample():
    runs = build_runs()
    stages = []
    for order, (sid, label, first, last, count) in enumerate(STAGES, 1):
        rs = [r for r in runs if r["stage"] == sid]
        assert len(rs) == count, (sid, len(rs), count)
        known = [r["run_id"] for r in rs if r["episode_id"]]
        unknown = [r["run_id"] for r in rs if not r["episode_id"]]
        base = {"source": "workflow-lifecycle", "fidelity": "exact"}
        if sid == "pr":
            eps = [dict(base, id="ep-pr-1", n=1, claim_id="claim-pr-1", started_at=first, ended_at=None, outcome="running", runs=known, reason="Claim still open")]
        elif sid in ("tasks", "analyze"):
            eps = [dict(base, id="ep-%s-1" % sid, n=1, claim_id="claim-%s-1" % sid, started_at=first, ended_at=plus(first, 14), outcome="invalidated",
                        runs=known[:1], reason="Upstream scope change invalidated the receipt"),
                   dict(base, id="ep-%s-2" % sid, n=2, source="receipt-revalidation", fidelity="partial", claim_id=None, started_at=plus(last, -40),
                        ended_at=last, outcome="accepted", runs=known[1:], reason="Revalidated after upstream changes")]
        elif sid == "finalize":
            eps = []
        else:
            eps = [dict(base, id="ep-%s-1" % sid, n=1, claim_id="claim-%s-1" % sid, started_at=first, ended_at=last, outcome="accepted", runs=known, reason="")]
        for e in eps:
            for r in rs:
                if r["run_id"] in e["runs"]:
                    r["episode_id"] = e["id"]
        status = "pending" if sid == "finalize" else "running" if sid == "pr" else "accepted"
        stages.append({"id": sid, "label": label, "order": order, "selected": True, "status": status,
                       "validity": "unknown" if sid == "finalize" else "current", "accepted_at": last if status == "accepted" else None,
                       "episodes": eps, "unknown_runs": unknown, "run_count": len(rs),
                       "failed_runs": sum(1 for r in rs if r["worker_status"] in ("failed", "abandoned")),
                       "run_time": M(sum(r["duration"]["value"] or 0 for r in rs) if rs else None, "delegation-ledger", "partial"),
                       "models": sorted({r["requested_model"] for r in rs}), "first_start": first, "last_end": last,
                       "open": sid == "pr", "timing": "open" if sid == "pr" else "unknown" if first is None else "closed"})

    def ws(label, ident, owners):
        ids = [t for t, w in TASKS if w == ident]
        return {"id": ident, "label": label, "origin": "shared" if ident == "Shared" else "facts-marked",
                "tasks": {"done": ids, "blocked": [], "active": [], "waiting": []}, "owners": owners,
                "run_ids": [r["run_id"] for r in runs if r["workstream"] == ident], "conflicts": []}
    workstreams = [
        ws("Workstream A", "A", [{"agent": "codex gpt-6.1-sol", "from": at(0, 21, 37), "to": at(1, 0, 10)}, {"agent": "codex gpt-6-astra", "from": at(1, 0, 10), "to": None}]),
        ws("Workstream B", "B", [{"agent": "claude claude-sonnet-5-5", "from": at(0, 21, 37), "to": None}]),
        ws("Shared", "Shared", [{"agent": "coordinator", "from": at(0, 21, 37), "to": None}]),
    ]
    t15_fail = next(r["run_id"] for r in runs if r["tasks"] == ["T015"] and r["worker_status"] == "failed")
    t15_retry = next(r["run_id"] for r in runs if r["retry_of"] == t15_fail)
    tl = []

    def ev(when, kind, text, refs=(), fid="exact"):
        tl.append({"id": "tl-%02d" % (len(tl) + 1), "at": when, "kind": kind, "text": text, "refs": list(refs), "fidelity": fid})
    ev(at(0, 17, 52), "stage", "Scope accepted")
    ev(at(0, 18, 14), "stage", "Specify accepted")
    ev(at(0, 18, 16), "decision", "Clarify asked C1Q1: which retry policy applies?", ["842-signal-quality:clarifications:C1Q1"])
    ev(at(0, 20, 46), "decision", "C1Q1 answered: option A (editor not recorded)", ["842-signal-quality:clarifications:C1Q1"], "partial")
    ev(at(0, 20, 50), "stage", "Clarify accepted")
    ev(at(0, 21, 36), "stage", "Plan, tasks, analyze and assure accepted")
    ev(at(0, 21, 37), "note", "Execute started: workstreams A and B in parallel", [], "estimated")
    ev(at(0, 23, 52), "failure", "T015 run failed", [t15_fail])
    ev(at(0, 23, 59), "recovery", "T015 retried by a linked run", [t15_retry])
    ev(at(1, 0, 3), "failure", "T016 run failed")
    ev(at(1, 0, 36), "failure", "T018 review fixes needed three runs; one abandoned")
    ev(at(1, 1, 30), "stage", "Execute accepted")
    ev(at(1, 2, 17), "stage", "Converge accepted")
    ev(at(1, 4, 50), "revalidation", "Tasks and analyze invalidated by an upstream change", [], "partial")
    ev(at(1, 5, 38), "revalidation", "Tasks and analyze revalidated", [], "partial")
    ev(at(1, 5, 38), "stage", "Verify and Review accepted")
    ev(at(1, 6, 10), "stage", "User manual accepted")
    ev(at(1, 6, 40), "failure", "Tasks to issues: one abandoned run, no recovery recorded", [], "partial")
    ev(at(1, 6, 50), "stage", "Tasks to issues accepted")
    ev(at(1, 7, 40), "stage", "Ready accepted")
    ev(at(1, 9, 0), "note", "Coordinator note: waiting for the review window")
    ev(at(1, 13, 20), "stage", "Pull request stage claimed")
    ev(at(1, 13, 57), "stage", "PR opened")
    failed = sum(1 for r in runs if r["worker_status"] in ("failed", "abandoned"))
    return {
        "schema": "sanduq.progress.v3", "rev": 40, "generated_at": at(1, 14, 5), "stale_after_seconds": 600,
        "collection": {"automatic": True, "dirty": False},
        "feature": {"id": "842-signal-quality", "title": "Signal quality scoring for ingest pipelines", "dir": "specs/842-signal-quality",
                    "branch": "842-signal-quality", "issue": {"number": 842, "url": "https://github.com/example/repo/issues/842"}, "workflow": "sanduq",
                    "started_at": M(at(0, 17, 10), "checkpoint", "partial"),
                    "stage": {"value": "pr", "status": "in-progress", "validity": "current", "source": "workflow-checkpoint"},
                    "next_action": {"text": "Merge the pull request after checks pass", "stage": "pr", "kind": "active-claim",
                                    "evaluated_at": at(1, 13, 58), "generation": 61, "source": "workflow"}},
        "orchestrator": {"host": "codex", "session_id": "sess-842-a", "model": M("gpt-6.1-sol", "self-report", "estimated"),
                         "effort": M("high", "self-report", "estimated"), "context": M(None), "host_elapsed": M(72300, "host-hook", "exact"),
                         "active": M(None), "since": at(0, 17, 5),
                         "provenance": {"model": "self-report", "effort": "self-report", "context": "none", "host_elapsed": "host-hook", "active": "none"},
                         "note": "Codex hooks are not approved in this worktree; model and effort are the coordinator's own report."},
        "attention": [
            {"id": "a1", "kind": "telemetry", "severity": "info", "text": "codex hooks not approved: model and effort are coordinator self-reported", "refs": [], "since": at(0, 17, 5)},
            {"id": "a2", "kind": "failure", "severity": "medium", "text": "Abandoned run on Tasks to issues has no recovery recorded", "refs": [], "since": at(1, 6, 40)}],
        "stages": stages, "workstreams": workstreams, "runs": runs,
        "dispatch": [{"intent_id": "intent-9", "identity": "specs/842-signal-quality/pr", "created_at": at(1, 13, 52), "state": "queued"}],
        "decisions": {"pending": [], "made": [{
            "key": "842-signal-quality:clarifications:C1Q1", "source": "clarifications", "source_id": "C1Q1",
            "question": "Which retry policy applies to failed ingest batches?",
            "options": ["A: exponential backoff", "B: fixed delay", "C: no retry"], "answer": {"kind": "single", "value": "A"}, "state": "applied", "revision": 2,
            "answer_digest": "sha256:9d1c", "evidence": ["spec.md#retry"], "url": "https://github.com/example/repo/issues/842#issuecomment-1", "decided_by": None,
            "observed_at": at(0, 20, 50), "answered_at": None, "applied": {"at": at(0, 20, 52), "evidence": "plan.md updated"}, "stage": "clarify"}],
            "sources": [{"name": "workflow decisions", "state": "available"}, {"name": "facts", "state": "absent"},
                        {"name": "clarifications", "state": "available"}, {"name": "legacy board", "state": "unsupported"}]},
        "timeline": tl, "history": {"lane_aliases": {"L1": "A", "L2": "run:run-044", "W7": "identity:codex-worker-7"},
                    "unresolved": [{"id": "L9", "label": "Retired scratch lane", "reason": "no run id or delegation identity names this lane",
                                    "owners": [{"agent": "codex-worker-3", "from": at(0, 22, 0), "to": at(0, 23, 30)}]}]},
        "sources": [{"name": "checkpoint", "path": "workflow/checkpoint.json", "fingerprint": "ab12", "generation": 61, "read_at": at(1, 14, 5)}],
        "summary": {"tasks_total": 23, "tasks_done": 23, "stages_selected": 16, "stages_accepted": 14, "runs_total": len(runs), "runs_failed": failed,
                    "decisions_pending": 0, "blockers_open": 0}}


def build_edge():
    return {
        "schema": "sanduq.progress.v3", "rev": 3, "generated_at": at(1, 14, 5), "stale_after_seconds": 600, "collection": {"automatic": True, "dirty": False},
        "feature": {"id": "plan-launch", "title": "Launch plan", "dir": "docs", "branch": "main", "issue": None, "workflow": None, "mode": "plan",
                    "source": "docs/plan.md", "started_at": M(None), "stage": {"value": None, "status": None, "validity": "unknown", "source": "none"},
                    "next_action": None},
        "orchestrator": {"host": None, "session_id": None, "model": M(None), "effort": M(None), "context": M(None), "host_elapsed": M(None),
                         "active": M(None), "since": None, "provenance": {}, "note": None},
        "attention": [], "stages": [], "workstreams": [], "runs": [], "dispatch": [],
        "decisions": {"pending": [], "made": [], "sources": [{"name": "workflow decisions", "state": "available"}, {"name": "clarifications", "state": "unsupported"}]},
        "timeline": [], "history": {"lane_aliases": {}, "unresolved": []}, "sources": [],
        "summary": {"tasks_total": 0, "tasks_done": 0, "stages_selected": 0, "stages_accepted": 0, "runs_total": 0, "runs_failed": 0,
                    "decisions_pending": 0, "blockers_open": 0}}


if __name__ == "__main__":
    for name, doc in (("ui_v3_sample.json", build_sample()), ("ui_v3_edge.json", build_edge())):
        (OUT / name).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print(name, len(json.dumps(doc)))
