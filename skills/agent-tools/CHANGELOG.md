# Changelog

## 1.2.0 — 2026-10-15

- New skill `progress-report`: a live, deterministic progress report for a Markdown plan checklist or a
  Spec Kit feature. It is the portable home of the Sanduq Progress extension (1.0.1), under MIT; the
  extension will vendor it from here.
- Plan mode: `progress init --plan PATH [--name NAME] [--dir DIR]` turns any `- [ ]` / `- [x]` file into a
  report in `.progress/<name>/`. Headings become phases, ids such as `T001` are kept, other items get
  stable `P001`... ids (equal text first, then 60 percent similar text, then the next number; numbers are
  never reused), and `(depends on …)` / `(after …)` annotations become edges. The plan is only read. The
  tracked `plan.json` stores ids and one-way text fingerprints, never item text (the text used for fuzzy
  matching lives in the git-ignored `.host/`). A bare id needs a delimiter and two digits (or `T`/`US`), so
  MP3, GPT-4, Q3 and ES6 are text; a repeated id becomes an automatic one. A plan outside the repository is
  stored as `external:<name>`; its absolute path and a path fingerprint stay in a git-ignored file, and a
  different file of the same name is refused unless `--rebind`.
- Plan report safety: glob characters in `--dir` are escaped in the git exclusions and `init` verifies them
  with `git check-ignore` (`PROGRESS_EXCLUDE_FAILED`); a `--dir` that holds another tool's `plan.json` is
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
