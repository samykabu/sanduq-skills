# Product map

Sanduq Skills ships six [skills](glossary.md#skill) in three [bundles](glossary.md#bundle). Each
bundle installs as one Claude Code [plugin](glossary.md#plugin) and has its own version.

![Product map. illustration-tools holds illustrate; dev-tools holds user-manual and github-wiki-publish; agent-tools holds delegate-task, progress-report and planning-majlis. A dashed arrow shows user-manual drawing with illustrate when it is installed, and a note says planning-majlis can run its critics through delegate-task. Below, the samykabu/sanduq repository lists the three bundles in its plugin marketplace and copies four of the skills into its Spec Kit extensions.](media/product-map.animated.svg)

Editable source: [product-map.html](media/product-map.html). Still version:
[product-map.svg](media/product-map.svg).

## The bundles

| Bundle | Version | Skills | What it is for |
| --- | --- | --- | --- |
| `illustration-tools` | 3.7.1 | [illustrate](skills/illustrate.md) | Diagrams and charts as editable HTML, with SVG, PNG, animated SVG, and GIF export. |
| `dev-tools` | 2.0.4 | [user-manual](skills/user-manual.md) and [github-wiki-publish](skills/github-wiki-publish.md) | Application manuals and standalone publishing of existing pages, reports, diagrams, and assets to a GitHub Wiki. |
| `agent-tools` | 1.9.2 | [delegate-task](skills/delegate-task.md), [progress-report](skills/progress-report.md) and [planning-majlis](skills/planning-majlis.md) | Handing a task to another agent CLI and measuring what it did; keeping a live progress report of a plan or feature; planning software or a feature with a gated committee of expert roles. |

## What each skill does

- **[illustrate](skills/illustrate.md)** draws 44 kinds of diagrams and charts in your project's
  [theme](glossary.md#theme).
- **[user-manual](skills/user-manual.md)** discovers your modules, writes the pages, and audits
  coverage. It also writes API references split by [audience](glossary.md#audience), release notes
  and [migration guides](glossary.md#migration-guide), and [redacted](glossary.md#redaction)
  screenshots, and sets up private pull request [previews](glossary.md#preview). It assembles each
  [edition](glossary.md#edition) as Markdown and renders it the way you choose: as Markdown, through
  your own templates and tools, or as an MkDocs site and PDF.
- **[delegate-task](skills/delegate-task.md)** runs one task on another agent CLI, the
  [harness](glossary.md#harness), and reports a measured result.
- **[github-wiki-publish](skills/github-wiki-publish.md)** publishes supplied content to a GitHub
  Wiki, preserves unrelated pages and navigation, and verifies the remote commit and served page
  when authenticated browser access is available.
- **[progress-report](skills/progress-report.md)** keeps a live report of a Markdown [plan](glossary.md#plan) or a
  Spec Kit feature: tasks, [lanes](glossary.md#lane), blockers, decisions, and what the Claude Code and Codex hooks
  observe. It is a [projection](glossary.md#projection), so no agent is spent on upkeep.
- **[planning-majlis](skills/planning-majlis.md)** plans new software or a feature with a committee of
  expert roles run as parallel subagents, and gates the plan: every seated role at 9/10 with no open
  blockers in the decision record.

## How they relate

- **user-manual does its own API, release, screenshot and preview work.** Since dev-tools 2.0
  they are reference files inside the skill, loaded when a task needs them.
- **user-manual uses illustrate when it is installed.** Its rules say to generate diagrams with
  the illustrate skill when it is available, including ER diagrams for the data reference.
  Illustrate does not depend on user-manual.
- **delegate-task and progress-report stand alone.** They fit together:
  `progress runs` can read the runs that delegate-task writes to `.delegate/runs`, and a lane can name the harness and
  model you delegated to.
- **planning-majlis stands alone.** It can use delegate-task, when installed, to run a critic on a
  different agent CLI or model from the authors.
- **github-wiki-publish stands alone.** It accepts existing pages, reports, diagrams, and assets
  without requiring `user-manual` or Spec Kit. Write or generate the pages first, then publish
  them.
- **Every skill works on its own.** None needs Spec Kit. You can install only the ones you need.

## Where to start

| You want to | Start with |
| --- | --- |
| Draw a diagram or chart | [illustrate](skills/illustrate.md) |
| Document an application | [user-manual](skills/user-manual.md) |
| Add API, release, screenshot, or preview work to a manual | [user-manual](skills/user-manual.md) |
| Publish existing pages, reports, diagrams, or assets to a repository Wiki | [github-wiki-publish](skills/github-wiki-publish.md) |
| Get a second agent to do or check a task | [delegate-task](skills/delegate-task.md) |
| Watch progress on a plan or feature, and see which agent does what | [progress-report](skills/progress-report.md) |
| Plan new software or a feature with a committee of experts before building | [planning-majlis](skills/planning-majlis.md) |

## Related

- [Glossary](glossary.md)
- [Animated examples](examples.md)
- [README](../README.md)
