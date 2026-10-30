---
name: user-manual
description: Create, update, audit and publish a standalone application User Manual with End User, Administrator and Technical editions, in English and optional Arabic. Use without Spec Kit to start a manual, document a feature or module, audit coverage, write API documentation (OpenAPI, AsyncAPI, GraphQL, webhooks), release notes and migration guides, plan and capture UI screenshots, set up private previews and versioned releases, or render the editions as Markdown for GitHub, through your own templates and tools (Pandoc, Quarto, a script), or as an MkDocs HTML site and PDF.
---

# User Manual

Maintain one evidence-backed Markdown source under `User-Manual/`. Publish three editions: End User,
Administrator/Operator and Technical Reference. Markdown is the product; rendering is a separate,
replaceable step.

## Choose the smallest workflow

- New manual: interview the user, inspect the repository, propose a module map, obtain approval,
  then run `scripts/init_manual.py` with an approved JSON module file.
- Existing manual: read `User-Manual/manual.yml`, inspect the requested scope and relevant Git diff,
  then update only affected pages and assets.
- Coverage audit: run `scripts/audit_manual.py` and explain every error and warning.
- Build: run `scripts/build_manual.py` only after the audit passes. It assembles each edition, then
  renders it with `renderer.kind` in `manual.yml`: `markdown` (default), `command` or `mkdocs`.
- Freshness: `scripts/manual_state.py record --feature <dir>` after an update; `status` exits 1
  when the inputs or manual outputs changed since the record.

`init_manual.py` copies the build, audit and state scripts (and the shipped stylesheets, in `tools/theme/`)
to `User-Manual/tools/` for CI. After
upgrading this skill, refresh those copies from its `scripts/` directory. `--no-tools` skips the
copies when CI runs the scripts from another place. The CI workflows follow the `ci:` mapping in
`--ci-policy <file>`, else in `.specify/workflow.yml` when it exists.

This skill does not require `.specify/`, a feature specification, or any Spec Kit command. Scope
work from the user's request, repository evidence and version-control changes.

## Route only what is needed

| Task | Read |
| --- | --- |
| Discovery and interview | [discovery.md](references/discovery.md) |
| Page structure and Markdown syntax | [content-model.md](references/content-model.md) |
| Audience and language | [audience-language.md](references/audience-language.md) |
| Incremental changes | [incremental-update.md](references/incremental-update.md) |
| Entities, columns, enumerations, ER diagrams | [data-reference.md](references/data-reference.md) |
| Renderers, templates, brand, HTML, PDF, RTL | [publishing.md](references/publishing.md) |
| API documentation | [api-docs.md](references/api-docs.md) |
| Release notes and migration guides | [release-docs.md](references/release-docs.md) |
| UI screenshots | [ui-screenshots.md](references/ui-screenshots.md) |
| Previews and release publishing | [preview-publishing.md](references/preview-publishing.md) |

## Non-negotiable rules

1. Require English. Arabic is optional per project, but pages, renderers, diagrams and PDFs must
   support RTL from initialization.
2. Use plain, natural English or Arabic. Write for the declared audience; never reuse a technical
   explanation unchanged for an end user.
3. Ground claims in implementation, contracts, tests, observed behavior, schemas, or approved
   infrastructure sources. Mark unknowns and never invent behavior.
4. Never include secrets, credentials, tokens, private keys, connection strings, production
   records, or unredacted personal data. Use deterministic synthetic examples.
5. Store the approved, extensible module map in `User-Manual/manual.yml`. Add later discoveries as
   `proposed` until approved.
6. Keep Markdown canonical and write GitHub's own syntax, so every page reads correctly on GitHub;
   the build translates it for other renderers. Generate other formats only through the build.
7. Generate only useful diagrams, with the `illustrate` skill when installed. Keep system overviews
   separate from readable module-level detail: a system ER overview plus smaller module ER
   diagrams. Document every evidenced entity, column, data type, relationship, constraint and
   enumeration.
8. Preserve hand-authored content outside owned markers and make reruns converge.
9. Link a page only to pages its audience receives. The build rejects cross-audience page links and
   missing assets, and stages only the assets an edition's pages reach, so one audience never ships
   another's screenshots or samples.

## Real-life example

For "Create a manual for our booking platform," identify booking, customer, payment and operations
modules from routes, navigation, APIs, tests and schema files. Ask the user to approve that module
map. Then create audience-aware tutorials, safe screenshots, API and data references, English
content and optional Arabic content under `User-Manual/`, and render it the way the project
chooses: Markdown on GitHub, the team's Word template through Pandoc, or an MkDocs site with PDFs.
