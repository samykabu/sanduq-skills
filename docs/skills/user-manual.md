# user-manual

user-manual creates and maintains an application manual from your repository, with separate
editions for end users, administrators, and technical readers.

| | |
| --- | --- |
| Bundle | `dev-tools` (Claude Code plugin `dev-tools@sanduq`) |
| Version | 1.1.1 |
| Prerequisites | Python 3.10+. For HTML: `pip install mkdocs-material` (or another MkDocs theme). For PDF: the requirements in the skill's `references/publishing.md`, including system libraries. |
| Hosts | Codex: yes. Claude Code: yes. Claude Desktop: unverified. |

## Install

Follow the [Install section of the README](../../README.md#install) for your
[host](../glossary.md#host). In Claude Code, the `dev-tools` [plugin](../glossary.md#plugin)
installs this skill and its four extensions together.

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

## What you get

All content lives under `User-Manual/` in your repository:

- `manual.yml`: the approved module map, languages, [audiences](../glossary.md#audience), and
  publishing settings.
- `docs/en/` (and `docs/ar/` if you enable Arabic): one Markdown page per module, plus shared pages.
- `theme/`: stylesheets for light, dark, print, and right-to-left layouts.
- `tools/`: copies of the build, audit, and state scripts, so CI can run them.
- Built output in `site/` and `pdf/`: one HTML site per [edition](../glossary.md#edition), and on
  release one PDF per edition and language. Treat these as generated.

Outside that folder, it adds two CI workflows if they don't exist yet:
`.github/workflows/user-manual-preview.yml` and `.github/workflows/user-manual-release.yml`.

Markdown is the source of truth. Every page records its audience, content type, evidence paths,
and last-verified date.

## Options worth knowing

- **New or existing.** For a new manual it interviews you and scaffolds. For an existing manual it
  reads `manual.yml` and your git changes, then updates only the affected pages.
- **Coverage audit.** `scripts/audit_manual.py` lists gaps. Ask "audit the manual" and it explains
  each one.
- **Build one edition.** `scripts/build_manual.py --audience end-user --language en` builds a site.
  Add `--pdf` for a PDF, `--archive` for a zip, or `--module <id>` for one module only.
- **HTML theme.** Set `renderer.theme` in `manual.yml`: `material` (the default), `readthedocs`,
  `mkdocs`, or any installed MkDocs theme.
- **Arabic.** English is required. Arabic is optional, with right-to-left layout built in.
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
- Without the extensions installed, API, release, screenshot, and hosted-preview work follows the
  core rules only, and the skill reports what remains.

## Related

- Extensions: [user-manual-api-docs](user-manual-api-docs.md),
  [user-manual-release-docs](user-manual-release-docs.md),
  [user-manual-ui-screenshots](user-manual-ui-screenshots.md),
  [user-manual-preview-publishing](user-manual-preview-publishing.md)
- [illustrate](illustrate.md)
- [Product map](../product-map.md)
- [Glossary](../glossary.md)
