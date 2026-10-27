# dev-tools

Six standalone skills for application manuals and GitHub Wiki publishing, without requiring
Spec Kit. `github-wiki-publish` publishes existing pages, reports, diagrams, and assets independently
of the five manual skills.

| Skill | Use it for |
| --- | --- |
| `user-manual` | Complete discovery, initialization, incremental updates, audits, HTML, and PDF. |
| `user-manual-api-docs` | Public, administrator, and private API reference bundles. |
| `user-manual-release-docs` | Audience-aware release notes and migration guides. |
| `user-manual-ui-screenshots` | Deterministic, redacted web and mobile screenshots. |
| `user-manual-preview-publishing` | Private PR artifacts, approved previews, and releases. |
| `github-wiki-publish` | Publish existing pages, reports, diagrams, and assets to a GitHub Wiki. |

Install the complete core:

```bash
npx skills add samykabu/sanduq-skills --skill user-manual
```

Install Wiki publishing on its own:

```bash
npx skills add samykabu/sanduq-skills --skill github-wiki-publish -a codex
```

See the [Wiki publishing guide](../../docs/skills/github-wiki-publish.md) for prerequisites,
updates, pinned versions, release archives, and verification limits.

Or install the Claude Code plugin bundle:

```text
/plugin marketplace add samykabu/sanduq
/plugin install dev-tools@sanduq
```

See the root [README](../../README.md) for prompts and real-life scenarios for every skill.
