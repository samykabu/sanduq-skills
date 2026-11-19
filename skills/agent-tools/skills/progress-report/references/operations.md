# Operations: prerequisites, scripts, examples, limitations, troubleshooting

## Prerequisites

Python 3.11 or newer and git. The scripts use only the standard library; the report is static HTML. Hooks need
Claude Code or Codex; Codex also needs the project trusted and its hooks approved.

| Script | Purpose | Arguments |
| --- | --- | --- |
| `scripts/progress.py` | The Progress CLI; exit 0 ok, 2 usage, 3 refused, 4 lock busy | `<verb> [flags]` (see the Verbs table in `SKILL.md`) |
| `scripts/hook.py` | Hook entry the host calls; installed by `progress hooks install`, never run by hand | `<event>`, host JSON on stdin |

## Examples

```bash
python .claude/skills/progress-report/scripts/progress.py init --plan docs/plan.md
python .claude/skills/progress-report/scripts/progress.py lane L1 --tasks P001-P003 --owner worker-a --harness codex
python .claude/skills/progress-report/scripts/progress.py block P004 --by L1
python .claude/skills/progress-report/scripts/progress.py status
```

## Limitations

- The report shows only what the plan file, hooks and recorded facts say. Without hooks, model, effort and context
  stay unknown.
- Hooks cover Claude Code and Codex only. Other harnesses are tracked through `lane` and the plan checklist.
- When a status line was already configured, `hooks install` chains it: the previous command runs as a shell string,
  as the host would run it, and only from untracked local state that still matches `statusline.previous`.

## Troubleshooting

| Error | Cause | Fix |
| --- | --- | --- |
| `PROGRESS_NOT_INITIALIZED` | No report directory yet | Run `progress init` (or `init --plan PATH`) |
| `PROGRESS_NO_FEATURE` | Several reports, or none | Pass `--plan NAME` or `--feature DIR`; the line lists candidates |
| `PROGRESS_FORBIDDEN_CONTENT` | The text looks like a secret or holds a path outside the repository | Rewrite it without them |
| `PROGRESS_HOOKS_SETTINGS` | The host's hook file is not valid JSON | Fix that file; Progress left it untouched |
| `PROGRESS_LOCK_BUSY` (exit 4) | Another Progress process holds the lock | Retry once |

Every code, with its cause and fix: the error-code table in `README.md`.
