# user-manual

user-manual creates and maintains an application manual from your repository, with separate
editions for end users, administrators, and technical readers. Pages are Markdown that reads
correctly on GitHub; you choose how each edition is rendered.

| | |
| --- | --- |
| Bundle | `dev-tools` (Claude Code plugin `dev-tools@sanduq`) |
| Version | 2.0.3 |
| Prerequisites | Python 3.10+, PyYAML and markdown-it-py (`User-Manual/requirements.lock`). Rendering through your own tool needs that tool. The MkDocs renderer needs MkDocs and a theme; its PDF also needs the system libraries in the skill's `references/publishing.md`. |
| Hosts | Codex: yes. Claude Code: yes. Claude Desktop: unverified. |

## Install

Follow the [Install section of the README](../../README.md#install) for your
[host](../glossary.md#host). In Claude Code, the `dev-tools` [plugin](../glossary.md#plugin)
installs it.

## First prompt

<details open>
<summary><strong>Codex</strong></summary>

```text
$user-manual Create a manual for our booking application. Inspect the repository, interview me
about audiences, and propose the module map before writing anything.
```
</details>

<details>
<summary><strong>Claude Code</strong></summary>

```text
/dev-tools:user-manual Create a manual for our booking application. Inspect the repository,
interview me about audiences, and propose the module map before writing anything.
```

Or just ask: "create a user manual for this app".
</details>

The skill reads your code first. Then it proposes a [module map](../glossary.md#module-map): the
product areas the manual will cover. Nothing is written until you approve it.

## What it covers

One skill does all of the manual work. It loads the detailed instructions for a task only when the
task needs them:

- **Pages:** discovery, tutorials, how-to guides, reference and explanation pages per
  [audience](../glossary.md#audience), in English and optional Arabic.
- **API references:** REST/OpenAPI, AsyncAPI, GraphQL, RPC, webhooks and code APIs, with a separate
  bundle per audience so internal operations never reach public pages.
- **Release notes and [migration guides](../glossary.md#migration-guide)** written from what actually
  shipped.
- **Screenshots:** a [capture matrix](../glossary.md#capture-matrix) and repeatable,
  [redacted](../glossary.md#redaction) web and mobile screenshots from your own test runner.
- **[Previews](../glossary.md#preview) and releases:** a private build for every pull request and
  versioned release archives.

## What you get

All content lives under `User-Manual/` in your repository:

- `manual.yml`: the approved module map, languages, audiences, publishing settings and the
  [renderer](../glossary.md#renderer).
- `docs/en/` (and `docs/ar/` if you enable Arabic): one Markdown page per module, plus shared pages.
- `theme/brand.yml`: the title, subtitle, author, copyright, logo and colour every renderer shows.
  Your own templates go in `theme/` too.
- `requirements.lock` (PyYAML and markdown-it-py), `requirements-mkdocs.lock` and `requirements-pdf.lock`: install
  only what your renderer needs.
- `tools/`: copies of the build, audit, and state scripts, so CI can run them. `--no-tools` skips
  them.
- Built output in `site/` (and `pdf/` with the MkDocs renderer). Treat these as generated.

Outside that folder, it adds two CI workflows if they don't exist yet:
`.github/workflows/user-manual-preview.yml` and `.github/workflows/user-manual-release.yml`. They
install only what the selected renderer needs.

Markdown is the source of truth. Every page records its audience, content type, evidence paths,
and last-verified date.

## Rendering

The build assembles each [edition](../glossary.md#edition) (one audience and language) as Markdown:
it selects the pages, fixes the links between them, and copies only the images and files they use.
Then `renderer.kind` in `manual.yml` decides the output:

| `renderer.kind` | You get |
| --- | --- |
| `markdown` (default) | The assembled Markdown edition, readable on GitHub or a wiki |
| `command` | Whatever your own tool makes from the edition, with your templates: a Word file through Pandoc, a Quarto book, your own script |
| `mkdocs` | An MkDocs HTML site with any installed theme, and with `--pdf` a PDF |

A Word edition through your team's template:

```yaml
renderer:
  kind: command
  command: pandoc {pages} --metadata-file {metadata} --reference-doc theme/word.docx -o {output}/manual.docx
```

The command runs from `User-Manual/`, so its paths are relative to the manual. `{pages}` lists the
edition's pages in reading order; `{metadata}` gives Pandoc the title, author, language and text
direction. The full list of placeholders is in the skill's `references/publishing.md`.

## Writing for GitHub

Write GitHub's own Markdown, so pages read correctly in the repository: `> [!NOTE]` and the other
GitHub alerts for callouts, `<details>` for collapsible or alternative content, and plain pipe
tables. The MkDocs renderer converts them into its own boxes and sections, titled in the edition's
language. The audit warns about MkDocs-only syntax such as `!!! note` or `=== "Tab"` and names the
GitHub form to use.

## Options worth knowing

- **New or existing.** For a new manual it interviews you and scaffolds. For an existing manual it
  reads `manual.yml` and your git changes, then updates only the affected pages.
- **Coverage audit.** `scripts/audit_manual.py` lists gaps. Ask "audit the manual" and it explains
  each one.
- **Build one edition.** `scripts/build_manual.py --audience end-user --language en`. Add
  `--archive` for a zip, `--module <id>` for one module only, `--renderer <kind>` to try another
  renderer once, or `--pdf` with the MkDocs renderer.
- **MkDocs theme.** `renderer.theme`: `material` (the default), `readthedocs`, `mkdocs`, or any
  installed MkDocs theme. `renderer.custom_dir` is a theme override folder relative to
  `User-Manual/`. A cover template in `theme/pdf/cover.html` replaces the PDF cover.
- **Arabic.** English is required. Arabic is optional, with right-to-left layout built in. Every
  edition records its language and direction for any renderer. MkDocs PDFs keep right-to-left layout,
  use the Amiri font (`fonts-hosny-amiri` on Ubuntu) and title the contents in Arabic.
- **Freshness.** `scripts/manual_state.py record --feature <dir>` records the state after an
  update. `status` exits 1 if inputs or outputs changed since then.
- **Diagrams.** When [illustrate](illustrate.md) is installed, the skill uses it for diagrams,
  including a system ER overview and smaller per-module ER diagrams.

## Limits

- It documents only what it can find evidence for. Unknowns are marked, not invented.
- It never includes secrets, credentials, production records, or unredacted personal data.
  Examples use synthetic data.
- A page may link only to pages its own audience receives. The build rejects anything else.
- After you upgrade the skill, refresh `User-Manual/tools/` from the skill's `scripts/` folder.
- The skill does not install a renderer command's tool. Put it on the build machine or CI runner.
- A `manual.yml` from before 2.0.0 has MkDocs settings and no `renderer.kind`: it keeps building its
  MkDocs site, and the build asks you to add `kind: mkdocs` to make that explicit. The four
  `user-manual-*` companion skills are gone; ask `user-manual` for that work instead.

## Related

- [illustrate](illustrate.md)
- [Product map](../product-map.md)
- [Glossary](../glossary.md)
