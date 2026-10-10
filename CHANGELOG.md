# Changelog

Bundles are versioned independently and tagged `<bundle>-vX.Y.Z`. History before this repository
existed is in [samykabu/sanduq](https://github.com/samykabu/sanduq/blob/main/CHANGELOG.md).

## 2026-10-10 — repository created

- Portable skills move here from `samykabu/sanduq`, which keeps the Spec Kit extensions and the
  Claude Code plugin marketplace. The marketplace now installs bundles from this repository.
- All bundles are relicensed under **MIT**. Each bundle carries `LICENSE` and `THIRD_PARTY_NOTICES.md`.
- `illustration-tools` 3.2.1: neutral example footers; plugin authorship updated.
- `dev-tools` 1.1.0: the portable User Manual skills gain theme selection, right-to-left theme
  styles, per-edition asset privacy, and the newer freshness state (see the bundle notes in
  `samykabu/sanduq` for details). New test suite.
- `agent-tools` 1.1.2: see [its changelog](skills/agent-tools/CHANGELOG.md).
- Install with `npx skills add samykabu/sanduq-skills`. The old `npx skills add samykabu/sanduq`
  path no longer lists these skills.
