# agent-tools

Skills for driving *other* agent CLIs from inside one, and for keeping a live progress report of the work — without Spec Kit.

| Skill | Use it for |
| --- | --- |
| `delegate-task` | Hand one task to Claude Code, OpenAI Codex, OpenCode, GitHub Copilot, or Pi; run it in the background; get back a status with its provenance, the file changes git actually measured, and normalised token counts. |
| `planning-majlis` | Plan new software or a feature with a committee of expert roles run as parallel subagents: tracks, isolated critiques, one decision record, and re-score rounds until every seated role scores 9/10 with no open blockers. Works in Claude Code, Codex and OpenCode. |
| `progress-report` | A live, deterministic progress report for a Markdown plan checklist or a Spec Kit feature: lanes, tasks, blockers, decisions, and the model, effort and context the hooks observe. Installs native Claude Code and Codex hooks; spends no agent tokens on upkeep. |

Install the Claude Code plugin bundle:

```text
/plugin marketplace add samykabu/sanduq
/plugin install agent-tools@sanduq
```

Or install a skill on its own:

```bash
npx skills add samykabu/sanduq-skills --skill delegate-task
npx skills add samykabu/sanduq-skills --skill progress-report
npx skills add samykabu/sanduq-skills --skill planning-majlis
```

## After installing: delegate-task

The driver is a dependency-free Node script (Node ≥ 18) that lives inside the skill, so where the
skill was installed decides where the driver is. Resolve it once:

```bash
# plugin install
DELEGATE="$CLAUDE_PLUGIN_ROOT/skills/delegate-task/delegate.mjs"
# npx skills install, or a copy committed into the repository
DELEGATE=".claude/skills/delegate-task/delegate.mjs"

export DELEGATE_RUNS_DIR="$PWD/.delegate/runs"
node "$DELEGATE" doctor
```

⚠️ **Set `DELEGATE_RUNS_DIR` on a plugin install, and add `.delegate/` to the project's
`.gitignore`.** Run artifacts hold your task text, the full prompt, and the harness's raw output.
Left at the default they are written beside the driver — the shared plugin directory — mixed across
every project you delegate from. `node "$DELEGATE" prune --keep 20 --yes` clears old ones.

`doctor` probes each CLI's version, so it distinguishes *not installed* from *installed but broken*.
At least one agent CLI must be on `PATH` and already logged in; `git` is what makes the measurement
layer work.

See the plugin [changelog](CHANGELOG.md) and the skill's [README](skills/delegate-task/README.md) — also available
[in Arabic](skills/delegate-task/README.ar.md) — for worked examples, the result schema, and the
three normative contracts. The root [README](../../README.md) lists every sanduq skill and
extension.

## After installing: progress-report

A standard-library Python script (3.11 or newer) that lives inside the skill. Resolve it once, from the repository root:

```bash
# plugin install
PROGRESS="python $CLAUDE_PLUGIN_ROOT/skills/progress-report/scripts/progress.py"
# npx skills install, or a copy committed into the repository
PROGRESS="python .claude/skills/progress-report/scripts/progress.py"

$PROGRESS init --plan docs/plan.md        # any Markdown checklist; creates .progress/plan/
$PROGRESS hooks install --host claude     # optional: model, effort, context, child agents
$PROGRESS status
```

Plan mode needs no Spec Kit; Spec Kit projects use `init --feature specs/<dir>`. See the skill's
[README](skills/progress-report/README.md) for the quick starts, every command and the error codes.

## Tests

```bash
cd skills/delegate-task && node test/run.mjs
python -m unittest discover -s skills/progress-report/tests -q    # standard library; browser tests skip without Playwright
```

173 cases. They drive a fake harness through `DELEGATE_BIN_<HARNESS>`, so the suite spends no
tokens and needs no agent CLI installed.

## B6 validation (2026-09-27)

Codex `exec` options, including `-s read-only`, now precede the `resume` subcommand. Verified against `codex-cli 0.157.1` help and a live sandboxed continuation.

- Driver suite: 173 reported passing cases, 0 failures. The existing Windows-only no-op skip cases remain unexecuted POSIX coverage, not live passes.
- Live parent: `codex-20260926232642-f56c99`; continuation: `codex-20260926232849-8610ae`; same session `01a0e00a-de27-71a2-900c-8f02ea434698`.
- Continuation: successful (`harness_telemetry`), exit 0, permission mode `codex: -s read-only`, no measured Git file delta. This proves CLI continuation compatibility; the driver's Git measurement is not proof against every possible write.
- The `delegate-task.driver.v1` and `delegate-task.result.v2` schemas are unchanged. Plugin version 1.1.1 is packaged as a standalone tagged release. Validation is local plus the live Codex continuation above; no GitHub CI pass or consumer adoption is claimed.
