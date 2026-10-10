# user-manual-ui-screenshots

user-manual-ui-screenshots plans and takes repeatable, redacted screenshots of web and mobile
screens for the manual.

| | |
| --- | --- |
| Bundle | `dev-tools` (Claude Code plugin `dev-tools@sanduq`) |
| Version | 1.1.1 |
| Prerequisites | Python 3.10+. Your project's own UI test runner; Playwright for web. A way to run the app with synthetic data. |
| Hosts | Codex: yes. Claude Code: yes. Claude Desktop: unverified. |

It extends [user-manual](user-manual.md) and stores images beside the manual pages that use them.

## Install

Follow the [Install section of the README](../../README.md#install). With `npx skills`, add
`--skill user-manual-ui-screenshots`. In Claude Code, the `dev-tools`
[plugin](../glossary.md#plugin) includes it.

## First prompt

<details open>
<summary><strong>Codex</strong></summary>

```text
$user-manual-ui-screenshots Plan screenshots for the password reset flow: sign-in, request
confirmation, and success, in English and Arabic at mobile width. Mask emails and tokens.
```
</details>

<details>
<summary><strong>Claude Code</strong></summary>

```text
/dev-tools:user-manual-ui-screenshots Plan screenshots for the password reset flow: sign-in,
request confirmation, and success, in English and Arabic at mobile width. Mask emails and tokens.
```

Or just ask: "add screenshots for the checkout pages".
</details>

## What you get

- A [capture matrix](../glossary.md#capture-matrix): which role, interface, state, language, and
  theme to capture.
- Screenshots stored under the owning module and language.
- Alt text and a caption for each image that explain the task and the expected result.
- Coverage notes for each image: scenario, role, state, viewport, theme, locale, runner, and the
  source test.

## Options worth knowing

- **Roles.** End user, delegated user, administrator, operator, and a denied role.
- **Interfaces.** Desktop web, responsive web, and real native mobile where the app has it.
- **States.** Happy path, empty, loading, validation, error, permission denied, and completion.
- **Language and direction.** English left-to-right, plus Arabic right-to-left when it is enabled.
- **Theme.** The default, plus an alternate theme only when it changes what the reader sees.

## Limits

- It picks the smallest useful set of states, not every combination.
- It never captures production data. Unstable or sensitive areas are
  [redacted](../glossary.md#redaction) with masks.
- Locale, timezone, viewport, color scheme, reduced motion, fonts, and network responses are fixed,
  and animations are off.
- Run captures in a pinned environment. Browser, OS, and font differences change the pixels.
- It uses your existing automation runner. It doesn't add a new one.

## Related

- [user-manual](user-manual.md), the core skill
- [user-manual-preview-publishing](user-manual-preview-publishing.md)
- [Product map](../product-map.md)
- [Glossary](../glossary.md)
