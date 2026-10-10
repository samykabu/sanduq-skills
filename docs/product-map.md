# Product map

Sanduq Skills ships seven [skills](glossary.md#skill) in three [bundles](glossary.md#bundle). Each
bundle installs as one Claude Code [plugin](glossary.md#plugin) and has its own version.

![Product map. The dev-tools bundle holds the user-manual core skill, with four skills that extend it: API docs, release docs, UI screenshots, and preview publishing. A dashed arrow shows user-manual using illustrate, from the illustration-tools bundle, for diagrams. The agent-tools bundle holds delegate-task on its own.](media/product-map.animated.svg)

Editable source: [product-map.html](media/product-map.html). Still version:
[product-map.svg](media/product-map.svg).

## The bundles

| Bundle | Version | Skills | What it is for |
| --- | --- | --- | --- |
| `illustration-tools` | 3.4.0 | [illustrate](skills/illustrate.md) | Diagrams and charts as editable HTML, with SVG, PNG, animated SVG, and GIF export. |
| `dev-tools` | 1.1.1 | [user-manual](skills/user-manual.md) and four extensions | Application manuals for end users, administrators, and technical readers. |
| `agent-tools` | 1.1.3 | [delegate-task](skills/delegate-task.md) | Handing a task to another agent CLI and measuring what it did. |

## What each skill does

- **[illustrate](skills/illustrate.md)** draws 44 kinds of diagrams and charts in your project's
  [theme](glossary.md#theme).
- **[user-manual](skills/user-manual.md)** is the core of the manual tools. It discovers your
  modules, writes the pages, audits coverage, and builds HTML and PDF
  [editions](glossary.md#edition).
- **[user-manual-api-docs](skills/user-manual-api-docs.md)** adds API reference pages, split by
  [audience](glossary.md#audience).
- **[user-manual-release-docs](skills/user-manual-release-docs.md)** adds release notes and
  [migration guides](glossary.md#migration-guide).
- **[user-manual-ui-screenshots](skills/user-manual-ui-screenshots.md)** adds repeatable,
  [redacted](glossary.md#redaction) screenshots.
- **[user-manual-preview-publishing](skills/user-manual-preview-publishing.md)** adds private pull
  request [previews](glossary.md#preview) and release publishing.
- **[delegate-task](skills/delegate-task.md)** runs one task on another agent CLI, the
  [harness](glossary.md#harness), and reports a measured result.

## How they relate

- **The four extensions build on user-manual.** They follow its rules and write into its
  `User-Manual/` folder. Without them, user-manual still applies its core rules to that work and
  reports what remains.
- **user-manual uses illustrate when it is installed.** Its rules say to generate diagrams with
  the illustrate skill when it is available, including ER diagrams for the data reference.
  Illustrate does not depend on user-manual.
- **delegate-task stands alone.** No other skill here calls it, and it calls none of them.
- **Every skill works on its own.** None needs Spec Kit. You can install only the ones you need.

## Where to start

| You want to | Start with |
| --- | --- |
| Draw a diagram or chart | [illustrate](skills/illustrate.md) |
| Document an application | [user-manual](skills/user-manual.md) |
| Add API, release, screenshot, or preview work to a manual | the matching extension page above |
| Get a second agent to do or check a task | [delegate-task](skills/delegate-task.md) |

## Related

- [Glossary](glossary.md)
- [Animated examples](examples.md)
- [README](../README.md)
