# Changelog

## 1.4.0 — 2026-10-17

`progress-report` 1.2.0: a v3 projection with stages, workstreams, runs and a timeline. This entry covers the data side; the
Timeline view ships in the same release.

- `progress status --json` now prints `sanduq.progress.v3` by default. `--schema v2` prints the v2 document unchanged, and the
  Workflow shim, the one-line summary, `progress export --schema v2` and the `classic` layout use it. `report.json` holds v3.
- Stages come from Workflow's published `stage_plan` (canonical order and policy filter for older producers). Episodes come from
  `workflow/lifecycle.jsonl`; older data gives labelled partial episodes from receipts and recoveries, or an unknown group.
- Runs are keyed by delegation run id, with recorded retry links, exact-claim candidate acceptance, intents kept apart as
  `dispatch`, namespaced host children and labelled durations. Nothing is inferred from timing or matching text.
- Workstreams: lane facts marked with `progress lane --workstream`, the workstream tags that `tasks.md` declares in its legend, and
  a Shared group. Role markers and `[P]` never count.
- Decisions from three adapters (facts, Workflow ledger, `workflow/clarifications.json`), each reported as available, absent,
  unsupported or invalid. An unrecorded editor or answer time stays null.
- `progress bind --host H --model M --effort E` stores a coordinator self-report in `.host/`, shown as self-reported and never
  preferred over what the host observed.
- `progress theme --layout timeline|classic` sets the layout key in `layout.js`; `classic` feeds the browser the v2 document.
- Every source file read is listed with a content fingerprint and generation.
- `progress export` accepts `--schema`; `status` rejects an unknown schema with `PROGRESS_USAGE`.
- Fixture `tests/fixtures/run-842` gains the tasks.md legend and a derived `workflow/clarifications.json` (C1Q1).

## 1.3.1 — 2026-10-17

Fixes from the review of the sanduq vendoring PR.

- `delegate-task` on Linux: check batches no longer fail on kernels that lack the `/proc/<pid>/task/<tid>/children` file. The
  containment helper now falls back to scanning `/proc/*/stat` for its own children, and it still stops with a clear
  `CHILD_ENUMERATION_UNAVAILABLE` if `/proc` cannot be read at all.
- `delegate-task` on Windows: environment names are matched without regard to case, so a batch or per-check `PATH`
  replaces an inherited `Path` instead of sitting beside it. Order stays inherited, then batch, then per-check.
- `delegate-task`: every check's launcher is resolved before the batch creates an attempt, so a missing executable
  fails up front instead of partway through; on Unix the launcher must be executable. Public delegate summaries no
  longer include the raw usage block.
- `delegate-task` on Windows: a cancel request that arrives before the check is launched now starts nothing and reports a
  closed, not-started result.
- `progress-report`: when two lanes in the facts log name the same delegation identity, they now fold into one lane
  (before, the second one kept its own duplicate row).
- `progress-report`: a receipt that Workflow marked stale no longer decides the current stage. The stage comes from the
  latest receipt that is not stale. Stale receipts still count for pause history and the events list.

## 1.3.0 — 2026-10-17

- Add native argv check batches with immutable attempts, exclusive execution ownership and explicit retries.
- Bound public collection by UTF-8 bytes while retaining complete raw evidence and omission metadata.
- Add bounded delegate summaries and startup diagnostics with an optional deadline; preserve legacy result semantics.

- `progress-report` correctness patch, found on a real 23-task run (frozen as `tests/fixtures/run-842`):
  - The header names the stage from the latest accepted receipt when no claim is active (it was blank).
  - A checkpoint `pause` that later stages superseded is no longer a blocker.
  - Finished lanes stop at their last terminal evidence; a lane with attempts shows the sum of their own durations, and a
    reused lane id restarts at its current owner (a 26-minute run no longer reads 13h 52m).
  - A facts lane and the Workflow delegation for the same run are one lane, matched only by durable ids (the lane owner
    is the run id or the delegation identity), never by label, time window or requested model: on the fixture 77 lanes
    become 72, and the 44 that carry tasks or attempts are the table.
  - UI: decisions and blockers come before lanes; no board for a lane with no tasks; done-only boards start closed; lanes
    with nothing to read collapse into one line; events keep stage, failure and decision lines and filter by kind; a line
    explains missing host hook data; "None made" now reads "No decisions recorded in Workflow decisions".
  - The default block order changed; a project's own `theme.json` order is kept.
  - Review fixes: a closed lane that absorbs a newer running attempt is active; retired `W<n>` ids and folded ids keep
    aliases (blocker targets, `by.ref`, lane references); a closed lane's closure yields to any attempt that started
    after it closed (running, failed, blocked or unaccepted success); a pause is history once the status leaves `paused`
    or a newer claim exists, and the event says why ("superseded: newer claim"); notes reach the
    events list within their own bound; the header shows a stage status other than in-progress ("pr · paused"); board and
    quiet-lane summaries keep keyboard focus across a refresh; the missing-telemetry note is host-neutral.

## 1.2.2 — 2026-10-16

- `progress-report` docs: Spec Kit now runs every Progress event through one internal command, `speckit.progress.hook`
  (not registered as an agent skill, so it no longer uses the host's skill budget); `commands.md` and `hosts.md` show
  the new hook commands. Codex asks to re-approve the hooks once because their command strings changed.

## 1.2.1 — 2026-10-16

- `progress-report`: Codex runs project hooks only when the project is trusted and each hook is approved in the user
  config; unapproved hooks are skipped silently, so the session never binds. `progress hooks status --host codex` now
  reports registered and approved counts per scope and whether the project is trusted, and counts Spec Kit's hooks in
  `.codex/config.toml`. `hooks install --host codex` reminds you to approve the hooks, and `progress status` hints
  `no bound session (codex hooks not approved?)`. Trust and approval state is read, never written.

## 1.2.0 — 2026-10-15

- `progress-report`: `.host/` and `.view/` each hold a nested `.gitignore` with `*`, so local-only files stay ignored
  even when a parent `.gitignore` re-includes them; `init` creates them before its ignore preflight and rolls them
  back if the preflight refuses.
- New skill `progress-report`: a live, deterministic progress report for a Markdown plan checklist or a
  Spec Kit feature. It is the portable home of the Sanduq Progress extension (1.0.1), under MIT; the
  extension will vendor it from here.
- Plan mode: `progress init --plan PATH [--name NAME] [--dir DIR]` turns any `- [ ]` / `- [x]` file into a
  report in `.progress/<name>/`. Headings become phases, ids such as `T001` are kept, other items get
  stable `P001`... ids (equal text first, then 60 percent similar text, then the next number; numbers are
  never reused), and `(depends on …)` / `(after …)` annotations become edges. The plan is only read. The
  tracked `plan.json` stores ids and one-way text fingerprints, never item text (the text used for fuzzy
  matching lives in the git-ignored `.host/`). An id with no bold and no `:` `.` `)` must be `T`, `US` or `P`
  plus digits, so MP3, GPT-4, Q3, ES6, X11, H264 and RFC-7231 are text; a repeated id becomes an automatic one. A plan outside the repository is
  stored as `external:<name>`; its absolute path and a path fingerprint stay in a git-ignored file, and a
  different file of the same name is refused unless `--rebind`.
- Plan report safety: glob characters in `--dir` are escaped in the git exclusions and `init` verifies them
  with `git check-ignore` (`PROGRESS_EXCLUDE_FAILED`) on the actual local-only files, before anything is registered or created; a `--dir` that holds another tool's `plan.json` is
  refused before any write (`PROGRESS_DIR_CONFLICT`); nothing under `specs/` is a report directory; the plan
  is read once per refresh.
- Target resolution for every verb: `--plan NAME|PATH` or `--feature DIR`; with exactly one active report no
  flag is needed, otherwise `PROGRESS_NO_FEATURE` lists the candidates on one line.
- Works with no Spec Kit: project state lives in `.progress/.project/` when there is no `.specify/`.
  Feature mode, Workflow collection and every 1.0.1 behaviour are unchanged.
- `progress hooks install|uninstall|status --host claude|codex [--scope project|user]` writes tagged native
  hook entries (`.claude/settings.json`, `.codex/hooks.json`), preserves all other settings, removes only its
  own entries, and refuses (exit 3) when Spec Kit's Progress hooks are already registered. The Codex file
  shape is unverified against a running host. Commands use the braced `${CLAUDE_PROJECT_DIR}` and end in
  `; exit 0` so a vanished plugin path cannot block the host (`hooks status` flags it; uninstall before
  updating the plugin). Settings are edited under a lock and only if unchanged since read; entries in the
  other scope are refused unless `--force-both`; an unreadable other-scope file does not stop an install;
  `--python` with spaces is refused; `install` prints `bind=<nonce>` when a report exists, so hooks can be
  installed before or after `init`.
- UI: a plan report shows its plan file in the header instead of the Workflow stage.
- 323 tests (stdlib unittest, 100 of them new for plan mode, the hook installer and the review fixes); browser tests skip without Playwright.

## 1.1.3 — 2026-10-10

- Remove a third-party notices file that did not apply: this bundle contains no third-party material.

## 1.1.2 — 2026-10-10

- Relicensed under MIT; the plugin now carries LICENSE.
- Claude runs report the model that did the work: `actual_model` is the `modelUsage` entry with the
  most output tokens, not a side call's model.
- Moved to the samykabu/sanduq-skills repository.
- `--resume` with an unknown run id reports "no such run to resume" before looking for the harness CLI.
- Fix a relay SIGTERM on Linux publishing the harness as killed by SIGKILL instead of `relay_aborted`;
  the test fake harness no longer truncates stdout past 64 KiB on POSIX pipes. All 174 tests pass on
  Windows and Linux.

## 1.1.1 — 2026-09-27

- Fix sandboxed Codex continuation by placing exec options before the resume subcommand (B6).
- Add an end-to-end fake-harness test that rejects misplaced sandbox options.
- Keep the driver and result schemas unchanged; this is an argument-order fix.

## 1.1.0 — 2026-09-26

- Add the machine-readable `delegate-task.driver.v1` contract for workflow
  integration, including requested and observed model fields.
- Make the driver entry point work when the skill is installed through a
  symlinked folder.
- Keep run status and measured file changes explicit in the result contract;
  172 driver tests pass.

## 1.0.0

- Initial `agent-tools` plugin bundle with the `delegate-task` skill.
