# progress-report

progress-report keeps a live report of a plan or a Spec Kit feature: which tasks are done, which
[lanes](../glossary.md#lane) own which tasks, what is blocked, which decisions are open, and which model,
effort and context the agent sessions use. The report is a [projection](../glossary.md#projection), rebuilt
from the plan and the host's hook payloads, so no agent is spent keeping it up to date.

| | |
| --- | --- |
| Bundle | `agent-tools` (Claude Code plugin `agent-tools@sanduq`) |
| Version | 1.4.2 (Progress 1.2.0) |
| Prerequisites | Python 3.11+ and git. Standard library only. A browser to open the report. Spec Kit is optional. |
| Hosts | Codex: yes (the Codex hook file is unverified). Claude Code: yes. Claude Desktop: no (writes project files and host hooks). |

## Install

Follow the [Install section of the README](../../README.md#install). In Claude Code, install the
`agent-tools` [plugin](../glossary.md#plugin).

The script is `scripts/progress.py` inside the skill. Where the skill is installed decides its path:
`.claude/skills/progress-report/` after `npx skills add`, `.agents/skills/progress-report/` for Codex, or
`$CLAUDE_PLUGIN_ROOT/skills/progress-report/` with the plugin. Run it from the repository root.

## First prompt

<details open>
<summary><strong>Codex</strong></summary>

```text
$progress-report Track docs/plan.md. Create the report, install the Codex hooks, and tell me where to
open it.
```
</details>

<details>
<summary><strong>Claude Code</strong></summary>

```text
/agent-tools:progress-report Track the plan you just saved in ~/.claude/plans. Create the report and
install the Claude hooks for this project.
```

Or just ask: "show me a progress dashboard for this plan".
</details>

The skill runs `progress init --plan PATH`, relays its one line, and (when asked) `progress hooks install`.

## What you get

- A static page, `.progress/<name>/.view/index.html`, that works from `file://` and refreshes every 3 seconds. It shows
  the header with a progress bar, the orchestrator's model, effort and context, one row per lane, task boards
  (Active, Waiting, Blocked, Done), decisions, blockers and recent events.
- A one-line state from `progress status`, and a deterministic Markdown or JSON export.
- Committed facts: `.progress/<name>/facts.jsonl` (lanes, blockers, decisions, notes) and `plan.json` (the plan
  reference and stable item ids). The view and host snapshots are git-ignored.

Every measured value shows how well it was measured (exact, partial, estimated, or unknown). Unknown is never
replaced by a guess.

## Plan mode and Spec Kit mode

| | Plan mode | Spec Kit mode |
| --- | --- | --- |
| Tasks come from | Any Markdown file with `- [ ]` / `- [x]` items | `specs/<feature>/tasks.md` |
| Create | `progress init --plan docs/plan.md` | `progress init --feature specs/001-demo` |
| Report lives in | `.progress/<name>/` (or `--dir`) | `specs/<feature>/progress/` |
| Task ids | The plan's (`T001`) or stable `P001`... | `T001`... |
| Needs Spec Kit | No | Yes (and Workflow files are used when present) |

With one plan or feature active, no target flag is needed. With several, pass `--plan NAME|PATH` or
`--feature DIR`; the error lists the candidates.

The plan file is only read: whoever owns the plan checks items off. A plan outside the repository, such as
`~/.claude/plans/x.md`, is read in place and recorded as `external:x.md`, never by absolute path.

## Hooks

```bash
progress hooks install --host claude          # .claude/settings.json
progress hooks install --host codex           # .codex/hooks.json
progress hooks status
progress hooks uninstall --host claude
```

The entries are tagged, so uninstall removes only them and every other setting is kept. In a Spec Kit project that
already registers Progress hooks through the Sanduq extension, `install` refuses (exit 3). Nothing is written for a
host you do not name.

## Options worth knowing

- `--statusline yes` on `init` (Claude Code) adds the exact model, context use and session time to the report.
- `progress theme --preset cobalt` or `--from-illustrate` restyles the page.
- `progress lane L1 --tasks P001-P004 --owner worker-a --harness codex --model gpt-6.1-sol` records an assignment. Task
  start, completion and retries need no command.

Every verb, flag, output line, exit code and JSON schema is in the skill's
[command reference](../../skills/agent-tools/skills/progress-report/docs/commands.md).

## Limits

- Active work time is always unknown; hosts give no interval evidence.
- The Codex hook file shape, the Codex session end and the delivery of a background child's stop event are
  unverified against a running host.
- A plan item rewritten beyond recognition gets a new id (rewording and reordering keep it).
- The page reads local files only and needs a browser with JavaScript.

## Related

- [Product map](../product-map.md)
- [Glossary](../glossary.md)
- The skill's own [README](../../skills/agent-tools/skills/progress-report/README.md), the
  [contracts](../../skills/agent-tools/skills/progress-report/docs/contracts.md), and the
  [host notes](../../skills/agent-tools/skills/progress-report/docs/hosts.md)
