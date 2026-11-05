# github-wiki-publish

Publish existing pages, reports, diagrams, and assets to a GitHub repository Wiki. The skill
preserves unrelated pages and navigation, adapts links, checks Unicode and assets, and verifies
publication. It works independently of the manual skills and does not require Spec Kit.

| | |
| --- | --- |
| Bundle | `dev-tools` 2.0.4 (Claude Code plugin `dev-tools@sanduq`) |
| Prerequisites | Supplied content and access to the destination Wiki through a suitable connector or authenticated Git. An authenticated browser for rendered verification. |
| Verification | Used on 2026-11-05 to publish the wikis of both Sanduq repositories from Claude Code: remote commits checked, and every page's headings, links, sidebar and images checked in a signed-in browser through the page DOM. Screenshots were not available in that session. |
| Hosts | Claude Code: yes (live publication, see above). Codex: local Git checks passed. Claude Desktop: unverified; needs an authenticated Git/browser workspace. |

## Install and update

In Claude Code, as a plugin:

```text
/plugin marketplace add samykabu/sanduq
/plugin install dev-tools@sanduq
```

The marketplace pins a released bundle, so it can lag this repository until the marketplace update
is merged. Update an installed plugin with the host's plugin manager.

As a plain skill, from the repository where you want to use it:

```bash
npx skills add samykabu/sanduq-skills --skill github-wiki-publish -a claude-code
```

Use `-a codex` for Codex and add `-g` for a user installation. To update, rerun the same command and
accept the replacement, or for a user installation run `npx skills update github-wiki-publish -g`
(Skills CLI 1.7.2). Start a new host session to load the updated instructions.

To pin a release, check out the bundle tag in a separate directory and install from it:

```bash
git clone --branch dev-tools-v2.0.4 --depth 1 https://github.com/samykabu/sanduq-skills.git sanduq-skills-v2.0.4
npx skills add ./sanduq-skills-v2.0.4 --skill github-wiki-publish -a claude-code
```

Each dev-tools release, for example
[dev-tools 2.0.4](https://github.com/samykabu/sanduq-skills/releases/tag/dev-tools-v2.0.4), has
`dev-tools-v<version>.zip` for the bundle, `github-wiki-publish-v<version>.zip` for this skill, and
`SHA256SUMS`. The single-skill archive is the upload route in the root
[Claude Desktop instructions](../../README.md#install). Desktop has no authenticated Git or browser,
so publishing from there is untested.

## First prompt

```text
/dev-tools:github-wiki-publish Publish reports/review.html and its static preview to this
repository's Wiki. Keep the report's date and limitations, and link to the original artifact.
```

With a plain-skill install, call it as `/github-wiki-publish`. In Codex, use the same prompt with `$github-wiki-publish`.

## What it does

1. Works out where the pages go and which files you meant. It asks only when a choice changes
   what gets published.
2. Publishes through a connector if your host has one that can write wiki pages. Otherwise it
   clones the wiki's own Git repository into a scratch folder and finds its real default branch,
   which is often `master` even when the code repository uses `main`.
3. Copies your pages and images in and rewrites links so they work on the wiki. Pages it was not
   asked to touch stay as they are, and so do sidebar entries.
4. Commits only those paths and pushes. If someone else pushed first, it fetches and merges once;
   it never force-pushes, and a failed push leaves the clone in place so nothing is lost.
5. Confirms the commit is on the remote, then opens the page in a signed-in browser when it can,
   to check that text, links and images actually render. You get the page URL, the revision, and
   anything it could not check.

## How a run goes

![Publishing to a GitHub wiki: resolve the destination, use a connector if one can write wiki pages, otherwise clone the wiki repository fresh, map pages and assets, commit only those paths, fetch and push without force. A rejected push gets one fetch and merge; the same conflict again stops with the clone kept. Then the remote commit is verified and the served page is checked in a signed-in browser.](../media/github-wiki-publish-flow.animated.svg)

The retry loop runs once. If the same conflict comes back, the skill stops and keeps its clone, so
nothing you or someone else wrote is overwritten. [Editable source](../media/github-wiki-publish-flow.html).

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
