# planning-majlis

planning-majlis plans new software, or a new feature, with a committee of expert roles (a *majlis*)
before anything is built. Specialists drill into the problem, critics who wrote none of it attack the
result, every finding is folded into one decision record, and re-score rounds repeat until every
seated role scores 9/10 with no open blockers. Then writers produce the specifications from the
record.

| | |
| --- | --- |
| Bundle | `agent-tools` (Claude Code plugin `agent-tools@sanduq`) |
| Version | 1.9.0 |
| Prerequisites | A host that can start subagents for full isolation. Python 3.9+ for the gate script. |
| Hosts | Claude Code, Codex and OpenCode, each with its built-in subagent. Hosts without subagents run the roles one after another, with weaker isolation. |

## Install

Follow the [Install section of the README](../../README.md#install). In Claude Code, install the
`agent-tools` [plugin](../glossary.md#plugin). For Codex and OpenCode,
`npx skills add samykabu/sanduq-skills --skill planning-majlis -a codex` installs it under
`.agents/skills/`, which both read.

## First prompt

<details open>
<summary><strong>Codex</strong></summary>

```text
$planning-majlis Plan adding team workspaces to this app. Feature mode.
```
</details>

<details>
<summary><strong>Claude Code</strong></summary>

```text
/agent-tools:planning-majlis Plan a self-hosted tool that books meeting rooms from a phone.
```
</details>

<details>
<summary><strong>OpenCode</strong></summary>

```text
Use the planning-majlis skill to plan adding CSV import to this service. Roles: core, ux.
```
</details>

The skill asks which optional roles to seat unless your prompt names them.

## The roles

Five core roles always sit: **chair** (investment, scope, IP), **product**, **architect**,
**security** and **QA and chaos**. Four are optional, proposed from your request with a reason each:

| Optional role | Seat it when |
| --- | --- |
| UX | There are screens, a phone app, a website or onboarding |
| Integrations and AI | It depends on an external API, SaaS, LLM or agent |
| DevOps and FinOps | It is hosted, deployed or has running cost |
| End user | People other than the builders will set it up and use it |

Every seated role holds a veto: the plan cannot pass while any of them scores below 9.

## What you get

A workspace, `planning/<slug>/` by default:

- `00-brief.md`: your request, constraints, decisions already made, and the roster.
- `01-recon.md`: verified facts with sources, and an UNVERIFIED list.
- `tracks/`, `critiques/`, `rescores/`: the committee's working files.
- `record.md`: the decision record, the single source of truth. Decisions (`DR-n`), a resolution
  ledger for every finding, superseded text, a spike register for unverified facts (`SP-n`), and
  owner decisions with recommended defaults (`OD-n`).
- `scorecard.md`: each role's score per round.
- `deliverables/`: in full mode D1–D6 (product and business case, architecture and security, feature
  specifications, UX flows, delivery phases, implementation plan), trimmed to the seated roles; in
  feature mode one `spec.md`.

## Full mode and feature mode

- **Full mode**, for a new product: recon, 3–5 parallel tracks, isolated critiques, the record, the
  re-score loop, parallel writers, and a consistency pass.
- **Feature mode**, for an addition: recon on the repository, one design track, critiques, record
  entries (appended to the project's existing record when it has one), the re-score loop, and one
  feature spec.

## The gate

`scripts/gate.py <workspace>` decides it, and the skill never declares a pass the script did not
print. It checks that the five core roles are seated, that each seated role's latest score is at
least 9, that the record has no OPEN rows, that every `DR`, `SP` and `OD` id the record and
deliverables cite exists, and that every Markdown table row has as many cells as its header.
`--record PATH` points it at an existing project record; `--json` prints the result as JSON.

## Rules the committee follows

- Never invent a number: cite it, state the method, or mark it UNVERIFIED.
- Authors never review their own work; critics read files, not the authors' reasoning.
- The owner decides money, legal, naming, scope and brand. Each such question is recorded with a
  default, and the run continues on the default.
- At most six re-score rounds; then the blocking rows go to the owner.

## Limits

- A full run uses many more tokens than a normal chat (Anthropic measured multi-agent research runs at
  about 15 times). Feature mode keeps it smaller, but a feature run still took more than an hour in
  the evals.
- `opencode run` (non-interactive) rejects reads outside the project folder, so a worker that needs
  one fails. Keep the work inside the project, or allow `external_directory` in the OpenCode config.
- The skill leaves models unset. Critics and writers should run on the strongest model you have.
- To put critics on a different agent CLI or model from the authors, install
  [delegate-task](delegate-task.md).

## Related

- [Product map](../product-map.md)
- [delegate-task](delegate-task.md)
- [Glossary](../glossary.md)
