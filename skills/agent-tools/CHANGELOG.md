# Changelog

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
