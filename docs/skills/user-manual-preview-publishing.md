# user-manual-preview-publishing

user-manual-preview-publishing sets up private previews of the manual for pull requests, and
versioned builds for releases, with access control per edition.

| | |
| --- | --- |
| Bundle | `dev-tools` (Claude Code plugin `dev-tools@sanduq`) |
| Version | 1.1.1 |
| Prerequisites | Python 3.10+. A manual created by [user-manual](user-manual.md). CI that can run workflows and upload artifacts. For hosted previews, an approved provider and its credentials. |
| Hosts | Codex: yes. Claude Code: yes. Claude Desktop: unverified. |

It extends [user-manual](user-manual.md). The core skill already adds the preview and release
workflows. This skill configures and troubleshoots them.

## Install

Follow the [Install section of the README](../../README.md#install). With `npx skills`, add
`--skill user-manual-preview-publishing`. In Claude Code, the `dev-tools`
[plugin](../glossary.md#plugin) includes it.

## First prompt

<details open>
<summary><strong>Codex</strong></summary>

```text
$user-manual-preview-publishing Set up manual previews for pull requests. Our repository is
public, so keep the administrator and technical editions protected.
```
</details>

<details>
<summary><strong>Claude Code</strong></summary>

```text
/dev-tools:user-manual-preview-publishing Set up manual previews for pull requests. Our
repository is public, so keep the administrator and technical editions protected.
```

Or just ask: "why didn't the manual preview publish on my PR?".
</details>

## What you get

- A private CI artifact with every [edition](../glossary.md#edition), linked from the pull request.
  This always comes first.
- Optionally, a hosted [preview](../glossary.md#preview), only when `manual.yml` names an approved
  provider.
- A provider descriptor at `User-Manual/providers/<provider-id>/preview.yml`. It records the
  provider, its review date, allowed audiences, pinned versions, the *names* of required secrets,
  the URL output, expiry, and fork behavior.
- One pull request comment, updated in place, with the preview links.
- On release, versioned HTML archives and one PDF per edition and language.

## Options worth knowing

- **Private repository.** The artifact is limited to people who can read the repository.
- **Public repository.** Only an encrypted bundle is uploaded. Set the
  `USER_MANUAL_PREVIEW_AGE_RECIPIENT` Actions variable to the public key, and share the private
  key outside the repository.
- **Hosted provider.** Before writing an adapter, the skill reads the provider's current official
  documentation. It runs only after the audit and builds succeed.
- **Fork pull requests.** When credentials aren't available, hosted deployment is skipped. The
  private artifact still builds, and the reason is reported.

## Limits

- Public hosting may contain only approved End User content.
- Administrator and Technical editions need real, provider-enforced sign-in. An unlisted URL is
  not enough.
- An adapter is rejected if internal editions lack sign-in, if credentials could reach fork code,
  or if previews never expire.
- Tokens never appear in commands, logs, generated configuration, URLs, or docs.
- Third-party actions and dependencies are pinned per your project's policy.

## Related

- [user-manual](user-manual.md), the core skill
- [user-manual-ui-screenshots](user-manual-ui-screenshots.md)
- [Product map](../product-map.md)
- [Glossary](../glossary.md)
