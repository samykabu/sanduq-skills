---
name: github-wiki-publish
description: "Publish or update pages, reports, diagrams and assets in a GitHub repository Wiki, preserving existing content and verifying the published result. Use for GitHub Wiki publishing or sync requests, rather than GitHub Pages deployment or general documentation generation."
---

# GitHub Wiki Publish

Publish the requested material to the repository's existing Wiki. Keep content generation separate from publication: use the supplied pages, reports and assets, adapting links and navigation as needed. Follow the target project's rules without importing conventions from another project.

## Establish the destination and scope

- Resolve the GitHub host, repository, Wiki URL, source files and intended page names from the request and repository context. Ask only about unresolved choices that materially change the publication.
- Distinguish preparation from publishing. An explicit request to publish authorizes the named Wiki update; do not ask again for the same action. A request for a draft or assessment alone does not authorize a push.
- Discover relevant connector capabilities first. If they cannot manage Wiki content and assets adequately, use the Wiki's separate Git repository. Explain the fallback briefly. Ordinary repository Contents APIs do not address the Wiki repository.
- Verify access using the existing authenticated connection or Git credentials. Never embed credentials in URLs, pages or retained evidence. An unauthenticated 404 does not prove a private Wiki is absent.
- If no Wiki Git repository exists, check whether the Wiki is disabled or needs its first page created through GitHub. Do not enable repository features or alter access as a side effect. Use an authorized first-page creation when possible; otherwise report the specific missing prerequisite.

## Prepare a bounded update

For Git publication, read [the Git procedure](references/git-publication.md). Use a fresh scratch clone, discover its actual default branch and read the existing destination pages, Home and sidebar before writing.

- Map each source file to a destination page or asset. Preserve unrelated pages, hand-authored sections and navigation. An absent source file is not a deletion instruction. Replace a whole page only when it belongs to the requested update; use a narrow edit for shared Home/sidebar content. Keep existing links and avoid duplicate navigation entries on repeat runs.
- Read and write text explicitly as UTF-8. Copy binary assets byte for byte. Do not silently repair source facts or refresh a report from a different dataset. Preserve its real date, provenance and limitations; use the appropriate upstream generator only if regeneration is in scope.
- Rewrite links for the Wiki's actual destination. Repository-relative links may break after moving a page. Copy referenced assets or link to an accessible repository revision; do not leave local paths, unpublished branch links or inaccessible external resources.
- Use supported inline images with meaningful alt text. For an HTML report or animated/interactive diagram, provide a useful static preview and links to the original artifact when the Wiki cannot render it. Do not describe downloadable HTML as an application served inside the Wiki. Follow project-specific diagram tools when generating new artwork is in scope; no particular generator is required by this skill.
- Check local links and assets, representative non-ASCII text, and the exact changed paths. Inspect the final diff for unintended deletion, overwritten content, credentials and generated debris. Keep temporary clones and local evidence out of the application repository unless the user or project requires retained sources there.

## Publish and verify

Apply publication only within the user's existing authorization. A Wiki update does not authorize pushing an application branch, changing issues, deploying a site, scheduling sync or installing CI.

- Commit only the intended Wiki paths, then fetch and reconcile concurrent changes as described in the Git procedure. Push normally to the Wiki's discovered default branch. Never force-push to overcome another writer.
- On rejection, fetch and inspect once. Integrate compatible edits and recheck the complete diff. If the same conflict recurs, intent cannot be resolved, or access fails, stop retries and retain the recoverable clone with a precise blocker. Do not delete it on failure.
- Verify the published commit against the live remote. A clean working tree alone does not prove local commits were pushed.
- Inspect the actual served page through an authenticated browser when available: page text, representative Unicode, navigation, links, image loading and legibility. For charts, compare the rendered result with the source facts. Check a full-size image when its inline preview obscures labels. Correct observed defects within scope and recheck affected content.
- If authenticated rendered verification is unavailable, report publication and remote verification separately from the unrun browser check. Do not claim a rendered pass from local files, an HTTP response or a successful push.

Report the page URL, published revision, material changes, checks performed and any unresolved limitation. Keep recovery paths when work remains unpublished. Do not add a new approval gate, content schema, project lifecycle or test regime.
