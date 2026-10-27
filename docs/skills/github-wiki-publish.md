# github-wiki-publish

Publish existing pages, reports, diagrams, and assets to a GitHub repository Wiki. The skill
preserves unrelated pages and navigation, adapts links, checks Unicode and assets, and verifies
publication. It works independently of the manual skills and does not require Spec Kit.

| | |
| --- | --- |
| Bundle | `dev-tools` 1.5.0 (Claude Code plugin `dev-tools@sanduq`) |
| Prerequisites | Supplied content and access to the destination Wiki through a suitable connector or authenticated Git. An authenticated browser for rendered verification. |
| Verification | Local Git behavior checks passed. A live browser test of the new skill remains unrun. |
| Hosts | Codex: local Git checks passed. Claude Code: unverified. Claude Desktop: unverified; needs an authenticated Git/browser workspace. |

## Install and update

From the repository where you want to use the skill:

```bash
npx skills add samykabu/sanduq-skills --skill github-wiki-publish -a codex
```

Use `-a claude-code` for Claude Code. Add `-g` for a user installation. To update this individual
skill, rerun the same command and accept replacement of its installed files. Start a new host
session to load the updated instructions.

For a user installation, Skills CLI 1.7.2 also supports:

```bash
npx skills update github-wiki-publish -g
```

For a pinned release, check out the bundle tag in a separate directory, then install from it:

```bash
git clone --branch dev-tools-v1.5.0 --depth 1 https://github.com/samykabu/sanduq-skills.git sanduq-skills-v1.5.0
npx skills add ./sanduq-skills-v1.5.0 --skill github-wiki-publish -a codex
```

For Claude Code's managed plugin route:

```text
/plugin marketplace add samykabu/sanduq
/plugin install dev-tools@sanduq
```

The companion marketplace pins a released bundle; its version can lag this repository until
the marketplace update is merged. Use the host's plugin manager to update that installed bundle.

The [dev-tools 1.5.0 release](https://github.com/samykabu/sanduq-skills/releases/tag/dev-tools-v1.5.0)
provides `dev-tools-v1.5.0.zip` for the bundle and `github-wiki-publish-v1.5.0.zip` for the skill,
with `SHA256SUMS`. The individual archive is the upload route described in the root
[Claude Desktop instructions](../../README.md#install). Uploading it does not establish that
Desktop has the authenticated Git and browser workspace publication needs; that support remains
unverified. Keep a pinned version until you deliberately install a newer release.

## First prompt

For Codex:

```text
$github-wiki-publish Publish docs/architecture.md and its images to this repository's Wiki.
Preserve unrelated pages and sidebar entries. Verify the published revision and rendered page.
```

For Claude Code:

```text
/dev-tools:github-wiki-publish Publish reports/review.html and its static preview to this
repository's Wiki. Keep the report's date and limitations, and link to the original artifact.
```

## What it does

1. Resolves the destination, source files, page names, access, and authorized publication scope.
2. Uses a suitable connector when available, otherwise the Wiki's separate Git repository and
   a fresh scratch clone. It discovers the actual default branch.
3. Maps sources to pages and assets, preserves unrelated content, adapts links and navigation,
   copies binaries unchanged, and checks the complete intended diff.
4. Commits only the intended paths, fetches and reconciles concurrent changes, and pushes
   normally. A conflict or rejected push stays recoverable.
5. Checks the published commit against the live remote and inspects the served page through an
   authenticated browser when available. The report gives the URL, revision, changes, checks,
   and unresolved limits.

## Limits

- It publishes supplied content; content generation and report regeneration need their own scope.
- A Wiki is separate from the application repository. Publishing does not authorize an application
  branch push, a deployment, CI installation, or changes to repository settings.
- HTML reports and interactive diagrams may need a static preview plus a link to the original.
  Downloadable HTML is not an application served inside the Wiki.
- If the Wiki needs its first page or access is unavailable, the skill reports the prerequisite.
- Remote Git verification and authenticated browser verification are separate results. A
  successful push does not prove that links, images, Unicode, or chart labels render correctly.
- The new skill's local Git behavior checks passed; authenticated live browser verification and
  Claude Desktop publication have not been tested.

## Related

- [Skill instructions](../../skills/dev-tools/skills/github-wiki-publish/SKILL.md)
- [Git publication procedure](../../skills/dev-tools/skills/github-wiki-publish/references/git-publication.md)
- [Product map](../product-map.md)
- [user-manual](user-manual.md)
- [illustrate](illustrate.md)
