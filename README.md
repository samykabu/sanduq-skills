# Sanduq Skills

Portable agent skills for software delivery. Each one does one job and runs in Claude Code, Codex,
or Claude Desktop. None needs Spec Kit.

[![License: MIT](https://img.shields.io/badge/license-MIT-233C32)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-6-C65B36)](#the-skills)

If you use [Spec Kit](https://github.com/github/spec-kit) and want these tools wired into its
lifecycle (QA, manuals, pull requests, project memory, issue-to-PR orchestration), see the
companion repository [samykabu/sanduq](https://github.com/samykabu/sanduq).

## The skills

Choose a skill by task. You install a bundle as a Claude Code plugin and call the skill inside it.

| Job | Skill | What it does | Bundle |
| --- | --- | --- | --- |
| Plan | [`planning-majlis`](docs/skills/planning-majlis.md) | Plans new software or a feature with a committee of expert roles run as subagents. It stops when every role scores 9/10 with no open blockers, or after six re-score rounds. *Majlis* is Arabic for a council. | `agent-tools` |
| Delegate and track | [`delegate-task`](docs/skills/delegate-task.md) | Hands one task to another agent CLI (Claude Code, Codex, OpenCode, Copilot, Pi) in the background and reports what it did, what git measured, and the tokens used. | `agent-tools` |
| Delegate and track | [`progress-report`](docs/skills/progress-report.md) | Keeps a live HTML progress report for a Markdown plan or a Spec Kit feature, fed by Claude Code and Codex hooks. Spends no agent tokens on upkeep. | `agent-tools` |
| Draw diagrams | [`illustrate`](docs/skills/illustrate.md) | Draws 44 kinds of diagrams and charts as editable HTML in your project's colors, with SVG, PNG, animated SVG and GIF export. | `illustration-tools` |
| Write and publish docs | [`user-manual`](docs/skills/user-manual.md) | Writes and maintains an application manual in Markdown, with editions per audience, API references, release notes and screenshots. Renders as Markdown, through your own tools, or as an MkDocs site and PDF; Arabic is optional. | `dev-tools` |
| Write and publish docs | [`github-wiki-publish`](docs/skills/github-wiki-publish.md) | Publishes existing pages, reports, diagrams, and assets to a GitHub Wiki, preserving unrelated content and checking what was published. It does not need a manual. | `dev-tools` |

![Six skills in three bundles. user-manual draws with illustrate when it is installed, and planning-majlis can run its critics through delegate-task. The samykabu/sanduq repository lists the three bundles in its plugin marketplace and copies four of the skills into its Spec Kit extensions.](docs/media/product-map.svg)

Every skill works on its own. user-manual calls illustrate, and planning-majlis calls delegate-task,
if those are installed.

## Documentation

The guides live in [`docs/`](docs/) and are published to the [wiki](https://github.com/samykabu/sanduq-skills/wiki).

- [Product map](docs/product-map.md): what each bundle and skill does, and how they relate.
- One page per skill, each with a first prompt and what you get back:
  [planning-majlis](docs/skills/planning-majlis.md), [delegate-task](docs/skills/delegate-task.md),
  [progress-report](docs/skills/progress-report.md), [illustrate](docs/skills/illustrate.md),
  [user-manual](docs/skills/user-manual.md) and [github-wiki-publish](docs/skills/github-wiki-publish.md).
- [Glossary](docs/glossary.md): the terms these skills use.
- [Animated examples](docs/examples.md): one diagram per arrow style, with the exact export command.

## Install

Pick your host. Run commands from the repository you want to work on.

<details open>
<summary><strong>Claude Code</strong></summary>

As plugins (recommended; updates arrive through the marketplace):

```text
/plugin marketplace add samykabu/sanduq
/plugin install illustration-tools@sanduq
/plugin install dev-tools@sanduq
/plugin install agent-tools@sanduq
```

Call them as `/illustration-tools:illustrate`, `/dev-tools:user-manual`, `/dev-tools:github-wiki-publish`, `/agent-tools:delegate-task`,
`/agent-tools:progress-report`, `/agent-tools:planning-majlis`, or just describe the task. The marketplace is hosted in `samykabu/sanduq` and installs from this
repository.

Or as plain skills: `npx skills add samykabu/sanduq-skills --skill illustrate -a claude-code`
(installs under `.claude/skills/`).
</details>

<details>
<summary><strong>Codex</strong></summary>

```bash
npx skills add samykabu/sanduq-skills --list                     # see what's available
npx skills add samykabu/sanduq-skills --skill illustrate -a codex
```

Codex installs project skills under `.agents/skills/`. Add `-g` to install for your user instead.
Start a new session, then call a skill with `$illustrate`.
</details>

<details>
<summary><strong>Claude Desktop</strong></summary>

1. Download the skill archive (for example `illustrate-v3.7.1.zip`) from [Releases](https://github.com/samykabu/sanduq-skills/releases),
   or zip the skill folder yourself (for example `skills/illustration-tools/skills/illustrate/`).
2. In Claude Desktop, open **Settings → Capabilities**, make sure code execution is on, and upload
   the zip under **Skills**.
3. Ask for what you need in plain words, for example "draw a sequence diagram of our login flow".

Claude Desktop runs skills in a sandbox. HTML diagrams work there. Anything that needs local tools
may not: PNG export, MkDocs and PDF builds, `delegate-task` (it drives CLIs on your machine),
`progress-report` (it writes project files and host hooks) and `github-wiki-publish` (it needs
authenticated Git and a browser). See [support by host](#support-by-host).
</details>

## Prerequisites

| Skill | You need |
| --- | --- |
| `illustrate` | Nothing for HTML. Python 3.10+ for themes and SVG export. Node 18+ for the hand-drawn style. Playwright with Chromium for PNG: `pip install playwright && playwright install chromium`. |
| `user-manual` | Python 3.10+. For HTML: `pip install mkdocs-material` (or another MkDocs theme). For PDF: the PDF requirements listed in the skill's `references/publishing.md`, including system libraries and, for Arabic, the Amiri font (`fonts-hosny-amiri` on Ubuntu). |
| `github-wiki-publish` | Access to the destination Wiki through a suitable connector or authenticated Git. An authenticated browser for rendered verification; supplied pages and assets. |
| `delegate-task` | Node 18+, git (to measure changes), and at least one signed-in agent CLI to delegate to. |
| `progress-report` | Python 3.11+ and git. Standard library only; a browser to open the report. Spec Kit is optional. |
| `planning-majlis` | A host that can start subagents (Claude Code, Codex, OpenCode) for full isolation; Python 3.9+ for the gate script. A full run uses many more tokens than a normal chat. |
| `npx skills` installs | Node 18+ and npm. |

## Support by host

| Skill | Claude Code | Codex | Claude Desktop |
| --- | --- | --- | --- |
| `illustrate` | Yes | Yes | HTML yes; exports unverified |
| `user-manual` | Yes | Yes | Unverified |
| `github-wiki-publish` | Yes (published two wikis, 2026-11-05) | Local Git checks passed; live browser test unrun | Unverified; needs an authenticated Git/browser workspace |
| `delegate-task` | Yes | Yes | No (needs local CLIs) |
| `progress-report` | Yes | Yes (Codex hook file unverified) | No (needs local files and hooks) |
| `planning-majlis` | Yes (4 evals behaved as expected; a feature-mode run takes more than an hour) | Yes (4 evals passed) | Unverified (no subagents; runs the roles in sequence) |

`planning-majlis` was also run in OpenCode with DeepSeek V4.1 Flash. All four evals behaved as expected, and its subagents ran through the Task tool.

"Unverified" means not yet tested on a clean install. Reports are welcome.

## First run

In Claude Code, with the plugins installed:

```text
/illustration-tools:illustrate Draw a sequence diagram of refund approval: the operator approves,
the booking API checks access and records the decision, and the payment provider settles. Show
what happens when approval is repeated.
```

You get one self-contained HTML file you can open in a browser and edit. Ask for
`Export it as SVG` when you want to embed it, or `Export it as an animated SVG with pulsing arrows`
(or as a GIF) for a README: arrows can draw on, flow, pulse or slide chevrons in their direction.

```text
/dev-tools:user-manual Create a manual for our booking application. Inspect the repository,
interview me about audiences, and propose the module map before writing anything.
```

With plain-skill installs, call them as `/illustrate` and `/user-manual`. In Codex, call them as
`$illustrate` and `$user-manual`.

## Releases and versions

Each bundle is versioned on its own and tagged `<bundle>-vX.Y.Z` (for example
`illustration-tools-v3.2.1`). See [CHANGELOG.md](CHANGELOG.md). Releases before the move to this
repository are recorded in [samykabu/sanduq](https://github.com/samykabu/sanduq).

`github-wiki-publish` is included in `dev-tools` (2.0.5 at the time of writing). The release workflow builds
`dev-tools-v<version>.zip`, a zip per skill such as `github-wiki-publish-v<version>.zip`, and `SHA256SUMS`. See its
[install and update guide](docs/skills/github-wiki-publish.md#install-and-update) for repository,
release, and pinned-version routes.

## Contributing

Change the skill under `skills/<bundle>/skills/<name>/`, run its tests, and bump the bundle's
`plugin.json` version when behavior changes.

```bash
python -m pip install -r requirements-test.txt
python -m unittest discover -s skills/illustration-tools/tests -q
python -m unittest discover -s skills/dev-tools/skills/user-manual/tests -q
node skills/agent-tools/skills/delegate-task/test/run.mjs
node --test skills/agent-tools/skills/delegate-task/test/execution-*.test.mjs
python -m unittest discover -s skills/agent-tools/skills/progress-report/tests -q
python -m unittest discover -s skills/agent-tools/skills/planning-majlis/tests -q
```

CI runs the four Python suites in one parallel pytest call (pytest and pytest-xdist are in
requirements-test.txt):

```bash
python -m pytest -n 4 skills/illustration-tools/tests skills/dev-tools/skills/user-manual/tests \
  skills/agent-tools/skills/progress-report/tests skills/agent-tools/skills/planning-majlis/tests
```

Illustrate's render lint (`lint-render.py --all`, Playwright with Chromium) runs on Linux only, in its own
CI job as four parallel slices; slice 0 also runs `--self-test` and the checks only `--all` runs. To run
one slice locally, from `skills/illustration-tools/skills/illustrate`:

```bash
python ../../tests/lint_render_shard.py 0 4
```

## License

MIT; see [LICENSE](LICENSE). Some Illustrate code and bundled icons keep their upstream licenses,
listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
