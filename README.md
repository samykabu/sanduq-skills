# Sanduq Skills

Portable agent skills for software delivery. Each skill does one job, works without Spec Kit, and
runs in Codex, Claude Code, or Claude Desktop.

[![License: MIT](https://img.shields.io/badge/license-MIT-233C32)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-7-C65B36)](#the-skills)

If you use [Spec Kit](https://github.com/github/spec-kit) and want these tools wired into its
lifecycle (QA, manuals, pull requests, project memory, issue-to-PR orchestration), see the
companion repository [samykabu/sanduq](https://github.com/samykabu/sanduq).

## The skills

| Skill | What it does | Bundle (Claude Code plugin) |
| --- | --- | --- |
| [`illustrate`](docs/skills/illustrate.md) | Draws 44 kinds of diagrams and charts (architecture, sequence, state, flow, ER, timelines, Sankey, and more) as editable HTML with SVG/PNG export, plus animated SVG or GIF for READMEs, in your project's colors and fonts. | `illustration-tools` |
| [`user-manual`](docs/skills/user-manual.md) | Creates and maintains an application manual with End User, Administrator, and Technical editions, in Markdown, MkDocs HTML, and PDF. English is required; Arabic (right-to-left) is optional. | `dev-tools` |
| [`user-manual-api-docs`](docs/skills/user-manual-api-docs.md) | API reference pages for public, administrator, and private audiences. | `dev-tools` |
| [`user-manual-release-docs`](docs/skills/user-manual-release-docs.md) | Release notes and migration guides per audience. | `dev-tools` |
| [`user-manual-ui-screenshots`](docs/skills/user-manual-ui-screenshots.md) | Repeatable, redacted screenshots of web and mobile screens. | `dev-tools` |
| [`user-manual-preview-publishing`](docs/skills/user-manual-preview-publishing.md) | Private previews of the manual for pull requests, and release builds. | `dev-tools` |
| [`delegate-task`](docs/skills/delegate-task.md) | Hands one task to another agent CLI (Claude Code, Codex, OpenCode, Copilot, Pi) in the background and reports what it did, what git measured, and the tokens used. | `agent-tools` |

The five `user-manual*` skills work together, but you can install only the ones you need.

## Documentation

- [Product map](docs/product-map.md): what each bundle and skill does, and how they relate.
- One page per skill: [illustrate](docs/skills/illustrate.md), [user-manual](docs/skills/user-manual.md),
  [user-manual-api-docs](docs/skills/user-manual-api-docs.md),
  [user-manual-release-docs](docs/skills/user-manual-release-docs.md),
  [user-manual-ui-screenshots](docs/skills/user-manual-ui-screenshots.md),
  [user-manual-preview-publishing](docs/skills/user-manual-preview-publishing.md), and
  [delegate-task](docs/skills/delegate-task.md).
- [Glossary](docs/glossary.md): the terms these skills use.
- [Animated examples](docs/examples.md): one diagram per arrow style, with the exact export command.

## Install

Pick your host. Run commands from the repository you want to work on.

<details open>
<summary><strong>Codex</strong></summary>

```bash
npx skills add samykabu/sanduq-skills --list                     # see what's available
npx skills add samykabu/sanduq-skills --skill illustrate -a codex
```

Codex installs project skills under `.agents/skills/`. Add `-g` to install for your user instead.
Start a new session, then call a skill with `$illustrate`.
</details>

<details>
<summary><strong>Claude Code</strong></summary>

As plugins (recommended; updates arrive through the marketplace):

```text
/plugin marketplace add samykabu/sanduq
/plugin install illustration-tools@sanduq
/plugin install dev-tools@sanduq
/plugin install agent-tools@sanduq
```

Call them as `/illustration-tools:illustrate`, `/dev-tools:user-manual`, `/agent-tools:delegate-task`,
or just describe the task. The marketplace is hosted in `samykabu/sanduq` and installs from this
repository.

Or as plain skills: `npx skills add samykabu/sanduq-skills --skill illustrate -a claude-code`
(installs under `.claude/skills/`).
</details>

<details>
<summary><strong>Claude Desktop</strong></summary>

1. Download the skill archive (for example `illustrate-v3.4.0.zip`) from [Releases](https://github.com/samykabu/sanduq-skills/releases),
   or zip the skill folder yourself (for example `skills/illustration-tools/skills/illustrate/`).
2. In Claude Desktop, open **Settings → Capabilities**, make sure code execution is on, and upload
   the zip under **Skills**.
3. Ask for what you need in plain words, for example "draw a sequence diagram of our login flow".

Claude Desktop runs skills in a sandbox. Generating HTML diagrams works there. Steps that need
local tools (PNG export with a browser, MkDocs and PDF builds, and `delegate-task`, which drives
CLIs on your machine) may not; see [support by host](#support-by-host).
</details>

## Prerequisites

| Skill | You need |
| --- | --- |
| `illustrate` | Nothing for HTML. Python 3.10+ for themes and SVG export. Node 18+ for the hand-drawn style. Playwright with Chromium for PNG: `pip install playwright && playwright install chromium`. |
| `user-manual*` | Python 3.10+. For HTML: `pip install mkdocs-material` (or another MkDocs theme). For PDF: the PDF requirements listed in the skill's `references/publishing.md`, including system libraries. |
| `delegate-task` | Node 18+, git (to measure changes), and at least one signed-in agent CLI to delegate to. |
| `npx skills` installs | Node 18+ and npm. |

## Support by host

| Skill | Codex | Claude Code | Claude Desktop |
| --- | --- | --- | --- |
| `illustrate` | Yes | Yes | HTML yes; exports unverified |
| `user-manual*` | Yes | Yes | Unverified |
| `delegate-task` | Yes | Yes | No (needs local CLIs) |

"Unverified" means not yet tested on a clean install. Reports are welcome.

## First run

```text
$illustrate Draw a sequence diagram of refund approval: the operator approves, the booking API
checks access and records the decision, and the payment provider settles. Show what happens when
approval is repeated.
```

You get one self-contained HTML file you can open in a browser and edit. Ask for
`Export it as SVG` when you want to embed it, or `Export it as an animated SVG with pulsing arrows`
(or as a GIF) for a README: arrows can draw on, flow, pulse or slide chevrons in their direction.

```text
$user-manual Create a manual for our booking application. Inspect the repository, interview me
about audiences, and propose the module map before writing anything.
```

## Releases and versions

Each bundle is versioned on its own and tagged `<bundle>-vX.Y.Z` (for example
`illustration-tools-v3.2.1`). See [CHANGELOG.md](CHANGELOG.md). Releases before the move to this
repository are recorded in [samykabu/sanduq](https://github.com/samykabu/sanduq).

## Contributing

Change the skill under `skills/<bundle>/skills/<name>/`, run its tests, and bump the bundle's
`plugin.json` version when behavior changes.

```bash
python -m pip install -r requirements-test.txt
python -m unittest discover -s skills/illustration-tools/tests -q
python -m unittest discover -s skills/dev-tools/skills/user-manual/tests -q
node skills/agent-tools/skills/delegate-task/test/run.mjs
```

## License

MIT; see [LICENSE](LICENSE). Some Illustrate code and bundled icons keep their upstream licenses,
listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
