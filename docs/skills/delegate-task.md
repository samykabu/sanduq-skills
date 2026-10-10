# delegate-task

delegate-task hands one task to another agent CLI in the background and reports what it did, what
git measured, and how many tokens it used.

| | |
| --- | --- |
| Bundle | `agent-tools` (Claude Code plugin `agent-tools@sanduq`) |
| Version | 1.1.3 |
| Prerequisites | Node 18+, git (to measure changes), and at least one signed-in agent CLI to delegate to. |
| Hosts | Codex: yes. Claude Code: yes. Claude Desktop: no (needs local CLIs). |

## Install

Follow the [Install section of the README](../../README.md#install). In Claude Code, install the
`agent-tools` [plugin](../glossary.md#plugin).

With a plugin install, set `DELEGATE_RUNS_DIR` (for example to `.delegate/runs` in your project)
and add `.delegate/` to `.gitignore`. Otherwise run files from every project pile up inside the
shared plugin folder.

## First prompt

<details open>
<summary><strong>Codex</strong></summary>

```text
$delegate-task Use claude to add input validation to parse_config() and a test for the bad-input
path. Run it in read-only mode first and show me what it would change.
```
</details>

<details>
<summary><strong>Claude Code</strong></summary>

```text
/agent-tools:delegate-task Use codex to add input validation to parse_config() and a test for the
bad-input path. Don't let it commit.
```

Or just ask: "have opencode give a second opinion on this fix".
</details>

The skill runs `doctor` first to see which CLIs are installed and working.

## What you get

A [delegation result](../glossary.md#delegation-result), printed and available as JSON:

- **Status**: `successful`, `failed`, or `abandoned` (see
  [delegation status](../glossary.md#delegation-status)).
- **Because**: the [provenance](../glossary.md#provenance) of that status, such as
  `harness_telemetry`, `timeout`, or `self_report`.
- **Changes**: the [git-measured changes](../glossary.md#git-measured-changes) next to the files the
  delegate claimed, with a flag when they disagree.
- **Tokens**: input and output totals, and cost and model where the harness reports them.
- **Summary**: the delegate's own account of its work.

Run files (prompt, logs, journal, result) go in `$DELEGATE_RUNS_DIR/<run_id>/`.

## Options worth knowing

**Harness targets.** A [harness](../glossary.md#harness) is the CLI that does the work. A
[host](../glossary.md#host) is where you run this skill. They are separate choices.

| Harness | id | Support | Read-only mode requested by `--sandbox` |
| --- | --- | --- | --- |
| Claude Code | `claude` | verified | plan permission mode |
| Codex | `codex` | verified | read-only sandbox, enforced by the CLI |
| OpenCode | `opencode` | verified | plan agent |
| Copilot | `copilot` | experimental | plan mode |
| Pi | `pi` | experimental | no approvals, read and search tools only |

Prefer `claude`, `codex`, or `opencode`. You can run the skill from Codex or Claude Code and target
any of these harnesses, including the one you are in.

**Flags you will use most:**

- `--cwd DIR` sets the working directory. Always set it.
- `--sandbox` turns on [sandbox mode](../glossary.md#sandbox-mode).
- `--timeout SEC` stops a run after this many seconds (default 1800).
- `--deliverable TEXT` and `--constraint TEXT` shape what comes back.
- `--allow-commit` lets the delegate commit.
- `--resume <run_id>` continues a finished run. Send only what should change.
- `--clean-env` passes only basic environment variables to the CLI.

Other commands: `status`, `collect --wait N`, `list`, `prune`, and `contract`.

## Limits

- **The default is full bypass.** The delegate can run any command without asking. Use
  `--sandbox` or a throwaway folder when that matters.
- A read-only check of `false` means no change was detected, not that nothing was written. It
  cannot see writes that were undone, ignored files, or files outside the repository.
- If something commits or stages during the run, the result is marked for review.
- Token totals are not comparable across harnesses. Copilot reports no tokens, and Codex reports
  no cost or model.
- Delegating to `claude` costs about 58,000 tokens before the task starts.
- Run files hold your task text and the raw output. Treat them as sensitive and clean up with
  `prune`.

## Related

- [Product map](../product-map.md)
- [Glossary](../glossary.md)
- The skill's own guides: writing the brief, reviewing the result, and running task queues, in
  [its references folder](../../skills/agent-tools/skills/delegate-task/references/)
