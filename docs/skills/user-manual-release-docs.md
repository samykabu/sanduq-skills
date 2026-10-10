# user-manual-release-docs

user-manual-release-docs writes release notes and migration guides for each audience, based only
on what actually shipped.

| | |
| --- | --- |
| Bundle | `dev-tools` (Claude Code plugin `dev-tools@sanduq`) |
| Version | 1.1.1 |
| Prerequisites | Python 3.10+. A git history that covers the release. |
| Hosts | Codex: yes. Claude Code: yes. Claude Desktop: unverified. |

It extends [user-manual](user-manual.md) and links its notes to the manual's pages.

## Install

Follow the [Install section of the README](../../README.md#install). With `npx skills`, add
`--skill user-manual-release-docs`. In Claude Code, the `dev-tools` [plugin](../glossary.md#plugin)
includes it.

## First prompt

<details open>
<summary><strong>Codex</strong></summary>

```text
$user-manual-release-docs Write the release notes for everything merged since the last tag. We
renamed the customerId field to accountId in the orders API, so add a migration guide too.
```
</details>

<details>
<summary><strong>Claude Code</strong></summary>

```text
/dev-tools:user-manual-release-docs Write the release notes for everything merged since the last
tag. We renamed the customerId field to accountId in the orders API, so add a migration guide too.
```

Or just ask: "prepare release notes for this version".
</details>

## What you get

- [Release docs](../glossary.md#release-docs) split by [audience](../glossary.md#audience) and
  module: a short note for end users, actions for administrators, and compatibility details for
  technical readers.
- Sections only where there is evidence: added, changed, fixed, deprecated, removed, security, and
  known issues.
- A [migration guide](../glossary.md#migration-guide) when readers must act. It covers who and
  which versions are affected, prerequisites, safety checks, before and after, ordered steps,
  verification, rollback, downtime, and known limits.
- For API changes, old and new payload examples.

## Options worth knowing

- **When a guide is written.** Only when a release changes data, API contracts, configuration,
  permissions, workflows, deployment, compatibility, or user behavior in a way that needs action.
- **Evidence.** Each item comes from git changes, contracts, schemas, configuration, tests, or
  deployment files.
- **Plain language.** Each item says who is affected, what changed, when to act, and how to check
  it worked.

## Limits

- It never invents versions, dates, issue numbers, support windows, or guarantees.
- Deprecation timing appears only when there is evidence for it.
- Database steps describe the schema change without production records or credentials.
- Internal implementation detail stays out of end-user notes.

## Related

- [user-manual](user-manual.md), the core skill
- [user-manual-api-docs](user-manual-api-docs.md)
- [Product map](../product-map.md)
- [Glossary](../glossary.md)
