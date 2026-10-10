# user-manual-api-docs

user-manual-api-docs writes API reference pages, with a separate bundle for each audience so
internal operations never leak into public docs.

| | |
| --- | --- |
| Bundle | `dev-tools` (Claude Code plugin `dev-tools@sanduq`) |
| Version | 1.1.1 |
| Prerequisites | Python 3.10+. Works best with a checked-in API contract, such as an OpenAPI or AsyncAPI file. |
| Hosts | Codex: yes. Claude Code: yes. Claude Desktop: unverified. |

It extends [user-manual](user-manual.md). You can use it alone, but its pages are meant to sit
inside a manual.

## Install

Follow the [Install section of the README](../../README.md#install). With `npx skills`, add
`--skill user-manual-api-docs`. In Claude Code, the `dev-tools` [plugin](../glossary.md#plugin)
includes it.

## First prompt

<details open>
<summary><strong>Codex</strong></summary>

```text
$user-manual-api-docs Document our order API for external partners. Keep refund administration
in the administrator edition and leave out health and debug routes.
```
</details>

<details>
<summary><strong>Claude Code</strong></summary>

```text
/dev-tools:user-manual-api-docs Document our order API for external partners. Keep refund
administration in the administrator edition and leave out health and debug routes.
```

Or just ask: "write API docs for the public endpoints".
</details>

## What you get

- Separate API bundles for public, administrator, and internal [audiences](../glossary.md#audience).
- For each operation: its purpose, who calls it, the authentication idea, permissions, the method
  and path (or channel), parameters, request and response shapes, errors, limits, versioning, and
  a safe synthetic example.
- A plain-language explanation before each technical block.
- The bundled contract kept as an artifact and linked from the matching manual page.

## Options worth knowing

- **Surfaces covered.** REST and OpenAPI, AsyncAPI, GraphQL, RPC, webhooks, and code APIs.
- **Contract first.** If a contract file exists, it is linted and bundled before anything is
  rendered.
- **No contract.** It drafts the reference from the code and tests, marks it as a draft, and records
  the missing contract as documentation debt.
- **Audience rules.** Classification comes from explicit contract metadata or approved path and tag
  rules. When it is unclear, the operation stays out.

## Limits

- It never treats an endpoint as public just because of its route.
- Bearer tokens, cookies, secrets, real identifiers, and production hosts are
  [redacted](../glossary.md#redaction).
- Pin the API tooling version in your project. Don't rely on "latest" in CI.

## Related

- [user-manual](user-manual.md), the core skill
- [user-manual-release-docs](user-manual-release-docs.md), for API migration guides
- [Product map](../product-map.md)
- [Glossary](../glossary.md)
