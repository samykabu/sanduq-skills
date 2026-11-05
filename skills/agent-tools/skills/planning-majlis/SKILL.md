---
name: planning-majlis
description: Plans new software or a new feature with a majlis, a committee of expert roles run as parallel subagents. Specialists drill into the problem, independent critics attack the result, everything is folded into one decision record, and rounds repeat until every seated role scores 9/10 with no open blockers; then writers produce the specs. Use when asked to "plan this product", "design this feature with a committee", "run a planning majlis", "get the experts to review this plan", or for a gated, multi-perspective plan before building.
---

# Planning majlis

Run a committee of expert roles that plans software before anyone builds it. You are the **chair's
clerk**: you brief the roles, keep the files and run the gate. You never score, and you never decide
what the owner decides.

## Rules that hold for the whole run

1. **The gate.** The plan passes only when every seated role's latest score is **9/10 or higher** and
   the decision record has **0 OPEN rows**. `python <SKILL_DIR>/scripts/gate.py <workspace>` decides it;
   never declare a pass the script did not print.
2. **Never invent numbers.** Every figure has a source, a stated method, or is marked `UNVERIFIED`
   in the spike register. A claim that depends on an unverified fact says so.
3. **Authors never review their own work.** A critic has written nothing it reviews. Critics read the
   files only, never the authors' reasoning or chat.
4. **The record is the single source of truth.** Tracks and critiques are inputs; when a deliverable
   and the record disagree, the record wins and the deliverable is fixed.
5. **The owner decides money, legal, naming, scope and brand.** Each such question becomes an `OD-n`
   row with a recommended default; the run continues on the default and reports it. Never change an
   owner decision quietly.
6. **Stop after 6 re-score rounds** without a pass, and report the blocking rows to the owner.
7. **Cost.** A full run uses roughly 15× the tokens of a normal chat. Say so before a full run.

## Step 1: seat the roles

Five **core** roles always sit: `chair`, `product`, `architect`, `security`, `qa-chaos`.
Four are **optional**: `ux`, `integrations`, `devops-finops`, `end-user`.

1. If the request names the roles (for example "roles: core, ux, end-user"), use them and skip to 3.
2. Otherwise propose the optional roles from the request using `references/roster.md`, then **ask the
   user** which to seat, with your harness's question tool if it has one or in chat, and wait.
3. Write the roster into `00-brief.md`. It never changes mid-run; adding a role later starts its own
   critique round.

## Step 2: pick the mode

- **Full** (new product or system): recon → tracks → critiques → record → re-score loop → writers →
  consistency pass. Default deliverables D1–D6, trimmed to the seated roles.
- **Feature** (an addition to existing software): recon on the repo → one design track → critique by
  roles that did not write it → record entries → re-score loop → one feature spec. If the project
  already has a decision record, append to it.

Ask only if the request leaves the mode unclear.

## Step 3: run it

Copy this checklist into your reply and tick it as you go:

```text
[ ] 0 Workspace: planning/<slug>/ (or the folder the user names) with 00-brief.md and the roster
[ ] 1 Recon: 01-recon.md, verified facts with sources, UNVERIFIED list
[ ] 2 Tracks (parallel): tracks/track-n-<topic>.md, each closing its own blocker ledger
[ ] 3 Critiques (parallel, isolated): critiques/critique-n-<group>.md with first scores
[ ] 4 Record v1: record.md (decisions, resolution ledger, spikes, owner decisions)
[ ] 5 Re-score loop: rescores/round-n-<group>.md -> emergency drill on the gaps -> record v+1
      until gate.py passes or 6 rounds
[ ] 6 Writers (parallel): deliverables/ from the record only
[ ] 7 Consistency pass by a role that wrote none of them; fix, re-run gate.py
[ ] 8 Owner hand-off: plain-language summary, open owner decisions with defaults
```

Phase details, entry and exit criteria: `references/process.md`.
How to start subagents in Claude Code, Codex and OpenCode: `references/spawning.md`.
Role briefs: `references/personas/<role>.md`. Scoring: `references/rubric.md`.
File templates: `references/templates/`.

## Running the roles

- `SKILL_DIR` is the folder holding this file. Pass workers absolute paths to their persona file,
  template, inputs and output file.
- Start every worker of a phase **in parallel** as a subagent, one per track, critic group or
  deliverable. Each writes one file and returns only its path and a five-line summary.
- Give each worker an objective, its inputs, its output path and template, and its boundaries
  (which files it may write; that it must not edit others). Vague briefs duplicate work.
- Models: critics, track authors and writers run on the strongest model available; small models only
  for mechanical checks. Leave models unset unless the user names them.
- A worker that fails is re-run once with the cause named (for example a denied permission: "stay
  inside the project folder"). Only a worker that fails twice runs in this session instead.
- If the harness cannot start subagents at all, run the roles one after another, each from a fresh
  reading of its inputs, and say in the hand-off that isolation was weaker.

## Hand-off

End with: the gate result as printed, the record version, the deliverables written, each open owner
decision in one plain sentence with its default, and what was not verified.
