# Git publication

Use the existing Git transport and credentials; HTTPS and SSH are both valid. The Wiki repository is separate from the application's code repository. GitHub documents the [Wiki Git workflow](https://docs.github.com/en/communities/documenting-your-project-with-wikis/adding-or-editing-wiki-pages), [images and links](https://docs.github.com/en/communities/documenting-your-project-with-wikis/editing-wiki-content), and [Home/sidebar companions](https://docs.github.com/en/communities/documenting-your-project-with-wikis/creating-a-footer-or-sidebar-for-your-wiki).

## Clone and inspect

Choose a unique, nonexistent scratch directory. Never recursively clear a supplied path to make room for a clone. Use the verified repository host and identity; the HTTPS Wiki URL has the shape `https://HOST/OWNER/REPO.wiki.git`. Do not silently change hosts or authentication methods when one fails.

Pass arguments directly through the tool or process API where possible. Otherwise quote them for the actual shell; JSON stringification is not shell escaping.

```text
git ls-remote --symref <wiki-remote> HEAD
git clone <wiki-remote> <scratch>
git -C <scratch> remote -v
git -C <scratch> symbolic-ref --short refs/remotes/origin/HEAD
git -C <scratch> status --short
```

Record the initial remote revision and derive the default branch from the symbolic HEAD. Do not assume `master` or `main`. If HEAD is unavailable, inspect live remote refs and repository information; do not guess a publishing target. Reusing an existing clone requires checking its remote, branch, local commits and dirty files first. Preserve work you do not own.

Inspect the destination pages and any existing `Home.*`, `_Sidebar.*` and `_Footer.*`. Respect their markup format. Page filenames determine their titles; avoid GitHub's unsupported title characters `\ / : * ? " < > |` and platform-specific filename collisions. Preserve established naming when updating an existing page.

## Copy and check

Use an explicit source-to-destination map, including nested assets. Do not mirror-delete the Wiki or replace its complete tree merely because a source directory has fewer files.

In Python, use `read_text(encoding="utf-8")`, `write_text(..., encoding="utf-8")` and `shutil.copy2` for binary copies. Equivalent explicit UTF-8 APIs are fine. Check Unicode after the copy; a successful decode can still contain text damaged by an earlier transcoding step.

For a copied image, compare hashes or bytes. Resolve relative links from the destination page location. Use the actual Wiki page URL for navigation when relative resolution is uncertain. GitHub supports PNG, JPEG and GIF previews; retain other original formats as links when needed, then verify their served behavior.

```text
git -C <scratch> diff --check
git -C <scratch> status --short
git -C <scratch> diff -- <intended-existing-paths>
git -C <scratch> add -- <explicit-page-and-asset-paths>
git -C <scratch> diff --cached --check
git -C <scratch> diff --cached --stat
git -C <scratch> diff --cached -- <intended-paths>
```

Inspect newly added text and assets as well as existing-file diffs. Confirm the staged path list matches the intended update; do not use `add -A` in an arbitrary reused checkout.

## Commit, reconcile and push

If content is unchanged, compare local and remote history before reporting a no-op. A previous publication may have committed successfully and then failed to push.

Commit the reviewed changes if needed. Fetch immediately before publication and compare the local tip with `origin/<default-branch>`.

```text
git -C <scratch> commit -m <message>
git -C <scratch> fetch origin
git -C <scratch> log --oneline --left-right HEAD...origin/<default-branch>
```

If the remote moved, inspect its changes and merge/rebase compatible unpublished work using normal Git operations. Preserve concurrent navigation and page edits; do not resolve conflicts by replacing their content wholesale. Recheck paths, links and the complete publication diff against the refreshed remote. Leave ambiguous conflicts recoverable and report what needs a decision.

```text
git -C <scratch> push origin HEAD:refs/heads/<default-branch>
git -C <scratch> rev-parse HEAD
git -C <scratch> ls-remote origin refs/heads/<default-branch>
```

A matching tip verifies the push at that moment. If another writer advanced afterward, fetch and verify that the published commit is an ancestor of the current remote branch, then inspect whether later edits superseded the requested content. Keep the published SHA distinct from the latest observed SHA. Never report success from a rejected push or automatically loop through repeated races.

Retain the clone while conflicts, rejected pushes or rendering defects remain unresolved. Cleanup after a verified publication is optional and follows the host's file-safety rules; it must not remove a directory containing unrelated or unpublished work.
