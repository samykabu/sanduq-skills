# Process

## Contents

- Workspace layout
- Phase 0: brief and roster
- Phase 1: recon
- Phase 2: tracks
- Phase 3: critiques
- Phase 4: the decision record
- Phase 5: the re-score loop
- Phase 6: writers
- Phase 7: consistency pass
- Phase 8: owner hand-off
- Feature mode

## Workspace layout

```text
planning/<slug>/
  00-brief.md          the request, constraints, owner decisions already known, roster, mode
  01-recon.md          verified facts with sources; UNVERIFIED list
  tracks/track-n-<topic>.md
  critiques/critique-n-<group>.md
  record.md            the single source of truth (versioned)
  rescores/round-n-<group>.md
  scorecard.md         one row per seated role, one score column per round
  deliverables/        D1..D6 (full) or spec.md (feature)
```

Use the folder the user names instead of `planning/<slug>/` when given. Templates for every file are
in `templates/`.

## Phase 0: brief and roster

Write `00-brief.md` from `templates/brief.md`: the request in the user's words, binding constraints
(stack, budget, deadlines, runners, licences, names that must never appear), decisions the owner has
already made, the roster (see `roster.md`) and the mode.

Exit: roster confirmed by the user or named in the request.

## Phase 1: recon

One worker (the architect, or the integrations role when seated) reads the existing code, docs and
the platforms the plan depends on, and writes `01-recon.md`: each fact with its source (file and
line, URL, command output) and the date checked. Facts it could not check go in an **UNVERIFIED**
list. No opinions, no design.

Exit: every later phase can cite recon facts by number (`F-n`).

## Phase 2: tracks

Split the problem into 3–5 tracks (full mode) by domain, each led by one or two seated roles; for
example product and scope, architecture and code, data and security, integrations, delivery and
cost. Start one worker per track in parallel. Each reads `00-brief.md` and `01-recon.md` in full and
writes its track from `templates/track.md`:

- an outcome paragraph, the design, and the facts it re-verified;
- a **blocker ledger**: every problem it found, each `Tn-Bm` row closed in the track (RESOLVED with
  the mechanism, or OWNER-DECISION with a default). A track does not finish with OPEN rows.

Exit: every track file exists with no OPEN rows in its own ledger.

## Phase 3: critiques

Start one worker per critic group (`roster.md`) in parallel. Each is told it wrote none of the
material, reads `00-brief.md`, `01-recon.md` and every track in full, and writes from
`templates/critique.md`:

- re-verified facts it relied on;
- findings `XB-<group>-n`, each with severity (blocker or major or minor), the evidence, and the
  **minimum mechanism** that would fix it, written so the consolidator can adopt it as is;
- a first score 0–10 per role in the group, with the condition that would raise it (`rubric.md`).

Exit: every group has a critique; `scorecard.md` has the first column.

## Phase 4: the decision record

One consolidating worker (the architect, with the chair's brief) writes `record.md` v1 from
`templates/record.md`:

- **§1 decisions** `DR-n`: one bold heading line each (`**DR-n Title.**`), then the binding text;
- **§2 resolution ledger**: one row per critique finding and per track OWNER-DECISION row, with status
  RESOLVED (and the DR that resolves it), OWNER-DECISION (default in force) or OPEN;
- **§3 superseded text**: what earlier files said that must not be copied;
- **§4 spike register** `SP-n`: every UNVERIFIED fact, its test, pass criterion, fallback and date;
- **§5 owner decisions** `OD-n`: the question, the options, the recommended default.

Exit: every finding has a ledger row.

## Phase 5: the re-score loop

Repeat until the gate passes or six rounds have run:

1. Start one worker per critic group in parallel. Each reads the current record in full, checks it
   against its own earlier critique, scores each of its roles (`rubric.md`) and lists new or
   unresolved findings. Output `rescores/round-n-<group>.md`.
2. Add the scores as a new column in `scorecard.md`. Add each new finding as an OPEN ledger row.
3. Run `python <SKILL_DIR>/scripts/gate.py <workspace>`. If it passes, leave the loop.
4. Emergency drill: start one worker per cluster of OPEN rows (targeted, only those rows). Each
   proposes the exact record change. The consolidator applies them, bumps the record version, and
   adds a changelog line; each fixed row becomes RESOLVED with its DR.

A role that stays below 9 states the precise condition that would make it a 9. If that condition is
an owner decision, the row becomes OWNER-DECISION with a default and stops blocking.

After six rounds without a pass, stop and hand the blocking rows to the owner.

## Phase 6: writers

Start one writer per deliverable in parallel. Writers read the record (and only the record, the brief
and recon); they never take text from tracks or critiques that the record superseded. Full-mode
deliverables, trimmed to what the seated roles cover and what the owner wants:

| ID | Deliverable | Leads |
| --- | --- | --- |
| D1 | Product analysis, feasibility, business case (numbers sourced or labelled assumptions) | chair, product |
| D2 | Architecture and security specification | architect, security |
| D3 | Feature specifications: stories, acceptance criteria, edge cases | product, qa-chaos |
| D4 | UX flows and screen states (only with `ux`) | ux, end-user |
| D5 | Start playbook and delivery phases with go/no-go criteria | chair, devops-finops |
| D6 | Implementation plan and estimate, with the estimating method stated | architect, devops-finops |

Every deliverable cites the DR, SP and OD ids it relies on.

## Phase 7: consistency pass

A worker that wrote no deliverable reads all of them against the record and lists every
contradiction, stale number or missing citation. Writers (or the consolidator) fix them; a fact the
record lacks goes into the record first. Run `gate.py` again: it checks tables and ids too.

## Phase 8: owner hand-off

Summarize in plain language: what the plan is, the gate result as printed, the score history, each
open owner decision with its default in one sentence, the spikes that must run first, and anything
not verified. Nothing changes after the hand-off without the owner's approval; an approved change
gets a record version and a ledger row.

## Feature mode

Same rules, smaller run:

1. `00-brief.md` with the roster (core plus the optional roles the feature touches).
2. Recon on the existing repo and its current decisions.
3. One design track led by the architect and product.
4. Critiques by groups that did not write the track.
5. Record: append a section to the project's existing decision record if there is one (new DR ids
   continue its numbering); otherwise create `record.md`.
6. Re-score loop until `gate.py` passes.
7. One writer produces `deliverables/spec.md`: stories, acceptance criteria, design, security, test
   plan and ordered tasks, each citing its DRs.
