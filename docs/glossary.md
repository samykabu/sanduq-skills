# Glossary

Terms used across the Sanduq Skills documentation, in alphabetical order. Each entry says what the
term means and where it matters.

### Animated SVG

An SVG image that plays its own animation with CSS and no script. Illustrate writes one as
`<name>.animated.svg` when you export with `--animated`. It plays where Markdown shows SVG images,
such as a README. Where it matters: [illustrate](skills/illustrate.md), [examples](examples.md).

### Arrow style

How the arrows move in an animated export: `draw`, `flow`, `pulse`, `draw-flow`, or `chevrons`.
You pick it with `--arrows`. Only `draw` ends on the still, complete figure; the others loop.
Where it matters: [illustrate](skills/illustrate.md#options-worth-knowing).

### Audience

The group of readers a page or bundle is written for. The manual skills use three: end user,
administrator (or operator), and technical. Each audience gets its own wording and its own output.
Where it matters: every `user-manual*` skill.

### Bundle

A folder of related skills that ship and version together, under `skills/<bundle>/`. This
repository has three: `illustration-tools`, `dev-tools`, and `agent-tools`. Each bundle is tagged
`<bundle>-vX.Y.Z`. Where it matters: installing, [product map](product-map.md).

### Capture matrix

The plan that says which screenshots to take: which role, interface, state, language, and theme.
It aims for the smallest set that teaches a reader or proves a documented branch.
Where it matters: [user-manual-ui-screenshots](skills/user-manual-ui-screenshots.md).

### Delegation result

What `delegate-task` hands back after a run: the status, why that status was chosen, a summary,
the files git measured as changed, the files the other agent claimed, and token usage.
Where it matters: [delegate-task](skills/delegate-task.md).

### Delegation status

The one-word outcome of a delegated run: `successful`, `failed`, or `abandoned`. Always read it with
its [provenance](#provenance). Where it matters: [delegate-task](skills/delegate-task.md).

### Edition

One published build of the manual for one audience and one language, for example the English
End User edition. Each edition gets its own HTML site and, on release, its own PDF.
Where it matters: [user-manual](skills/user-manual.md).

### Export

Turning an Illustrate HTML diagram into a separate file: a still SVG, a transparent PNG, an
animated SVG, or a GIF. Exports contain the diagram only, not the page around it. Export runs only
when you ask. Where it matters: [illustrate](skills/illustrate.md).

### Git-measured changes

The files that git saw change while a delegated run was going (`dirty_paths_changed`). They are
evidence. The files the other agent says it changed (`files_claimed`) are only a claim.
Where it matters: [delegate-task](skills/delegate-task.md).

### Harness

An agent command-line tool that `delegate-task` can hand a task to: Claude Code, Codex, OpenCode,
Copilot, or Pi. A harness is the target of a delegation, not the place you run the skill from.
Compare [host](#host). Where it matters: [delegate-task](skills/delegate-task.md).

### Host

The agent application you run a skill in: Codex, Claude Code, or Claude Desktop. Hosts differ in
how you install and call skills and in what local tools they can run.
Where it matters: every skill page, the README's support table.

### Lane

One unit of assignment in a progress report: a worker, a delegated run or a host subagent that owns a
list of tasks. You record lanes (`L1`); host child agents appear on their own (`C1`).
Where it matters: [progress-report](skills/progress-report.md).

### Marketplace

A catalog of Claude Code plugins that you add once and then install plugins from. The Sanduq
marketplace is added with `/plugin marketplace add samykabu/sanduq`.
Where it matters: installing in Claude Code.

### Migration guide

A step-by-step guide for readers who must act because of a release: what changed, who is affected,
the ordered steps, how to check success, and how to roll back.
Where it matters: [user-manual-release-docs](skills/user-manual-release-docs.md).

### Module map

The approved list of product areas the manual covers, stored in `User-Manual/manual.yml`. Each
module has an id, a name, a description, a status, its interfaces, its audiences, and evidence
paths. New areas start as `proposed` until you approve them.
Where it matters: [user-manual](skills/user-manual.md).

### Plan

Any Markdown file with `- [ ]` and `- [x]` items. `progress-report` reads it as a task list, never
writes it, and gives items without an id a stable one (`P001`).
Where it matters: [progress-report](skills/progress-report.md).

### Plugin

The Claude Code packaging of a bundle. Installing the `dev-tools` plugin, for example, gives you all
five manual skills. Where it matters: installing in Claude Code.

### Preview

A private build of the manual for a pull request, so reviewers can read the change before merge.
It is always a private CI artifact first, and optionally a hosted preview on an approved provider.
Where it matters: [user-manual-preview-publishing](skills/user-manual-preview-publishing.md).

### Projection

A report rebuilt from its sources (the plan, host hooks, recorded facts) on every refresh, so deleting
it loses nothing. Where it matters: [progress-report](skills/progress-report.md).

### Provenance

The reason a delegation status was chosen, in one word, such as `harness_telemetry`, `timeout`, or
`self_report`. It is stored as `status_provenance.primary`, with every other true observation listed
in `evidence`. Where it matters: [delegate-task](skills/delegate-task.md).

### Reduced motion

A reader's system setting that asks for less animation. Animated SVG exports respect it and show
the complete still figure instead. A GIF cannot respect it.
Where it matters: [illustrate](skills/illustrate.md), [examples](examples.md).

### Redaction

Hiding or replacing sensitive content, such as email addresses, tokens, or real records, before it
reaches documentation. The manual skills use synthetic data and mask unstable or sensitive parts of
screenshots. Where it matters: [user-manual-ui-screenshots](skills/user-manual-ui-screenshots.md),
[user-manual-api-docs](skills/user-manual-api-docs.md).

### Release docs

Release notes and migration guides written for each audience from what actually shipped.
Where it matters: [user-manual-release-docs](skills/user-manual-release-docs.md).

### Sandbox mode

For `delegate-task`, the `--sandbox` flag. It asks the target harness for its own read-only mode and
turns on a check for writes. The default is full bypass, with no restrictions.
Where it matters: [delegate-task](skills/delegate-task.md).

### Skill

A folder with a `SKILL.md` file that teaches an agent one job, plus optional `references/` and
`scripts/`. The agent loads it when your request matches its description.
Where it matters: everywhere.

### Theme

The colors and fonts Illustrate applies to every diagram in a project, stored in
`.github/illustration-theme.yml`. Built-in themes are Cobalt Porcelain (default), Emerald Mist, and
Sanduq Classic, each with light and dark palettes. You can also define your own.
Where it matters: [illustrate](skills/illustrate.md).
