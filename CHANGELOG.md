# Changelog

## Unreleased — agent-tools 1.3.0

- Native check batches, bounded collection, explicit retries and startup diagnostics. See the [bundle changelog](skills/agent-tools/CHANGELOG.md).

Bundles are versioned independently and tagged `<bundle>-vX.Y.Z`. History before this repository
existed is in [samykabu/sanduq](https://github.com/samykabu/sanduq/blob/main/CHANGELOG.md).

## 2026-10-17 — agent-tools 1.2.3: progress-report correctness patch

- `progress-report`: stage from accepted receipts, stale pauses no longer block, frozen durations, one lane per run,
  attention-first layout with kind-filtered events. See [agent-tools CHANGELOG](skills/agent-tools/CHANGELOG.md#123--2026-10-17).

## 2026-10-16 — agent-tools 1.2.2: progress-report docs for the single Spec Kit hook command

- See [agent-tools CHANGELOG](skills/agent-tools/CHANGELOG.md#122--2026-10-16).

## 2026-10-16 — agent-tools 1.2.1: progress-report Codex hook approval

- `progress-report`: `hooks status --host codex` reports registered and approved hooks and project trust (Codex skips
  unapproved hooks silently); `hooks install --host codex` and `progress status` point at the missing approval.
  Details in the [bundle changelog](skills/agent-tools/CHANGELOG.md).

## 2026-10-15 — agent-tools 1.2.0: progress-report

- New skill `progress-report` in `agent-tools`: a live, deterministic progress report for any Markdown plan
  checklist (plan mode, no Spec Kit) or a Spec Kit feature, with `progress hooks install|uninstall|status`
  for Claude Code and Codex. It is the portable source of the Sanduq Progress extension, relicensed MIT.
  Details in the [bundle changelog](skills/agent-tools/CHANGELOG.md).
- `progress-report`: `.host/` and `.view/` now carry a nested `.gitignore` holding a single `*`, so a parent
  re-include rule (for example `!claude-*.json`) cannot expose host-named snapshots. Default `.progress/<name>`
  directories no longer add redundant exclude lines.

## 2026-10-11 — illustration-tools 3.4.1: exports keep the page styles

- Fix: SVG, `--animated` and `--gif` exports copied only the `<svg>` element and dropped the page's
  `<style>`, so shapes styled by page classes or `var(--token)` fell back to the SVG default black
  fill. 29 shipped examples were affected: process and dp-integration (light, dark, full, hand),
  data-flow and medallion (same four), loop (light, dark, full, terminal), it-state and
  dp-security-matrix (light, dark, full), state-lifecycle (dark, full) and policy-trace-animated.
  Every export now carries the page rules into the SVG's own `<style>`: html/body rules become
  `:root` keeping only tokens and inherited text and paint properties (no layout), `@media` blocks
  such as `prefers-color-scheme` are kept, and `@import`, `@font-face`, `@keyframes`, animations,
  transitions and the page's motion runtime rules are left out. Reduced-motion gating is unchanged.
- Fix: a figure holding nested `<svg>` icons (high-level, high-level-vertical) was cut at the first
  inner `</svg>`, and an HTML comment containing `--` (streamgraph, all four variants) is not XML;
  10 such exports failed to open. Exports now take the whole top-level figure and drop HTML comments.
- New `tests/test_export_page_styles.py`: every shipped example's exports parse as the whole figure,
  define every custom property they use and style every page class they use; a rendered check
  compares black pixels against the source page.

## 2026-10-10 — illustration-tools 3.4.0: animated arrows, GIF export, straight arrow ends

- `--arrows=draw|flow|pulse|draw-flow|chevrons` (default `draw`) animates every arrow in its
  direction in `--animated` exports, for motion figures and ordinary diagrams alike.
- `--gif` exports the same animation as a looping GIF (`--theme light|dark`, `--fps`).
- Illustrate: arrows end straight. A marker follows the exact end tangent, but the eye follows the
  line arriving at the head, so a curve or rounded corner still bending at the tip made its head look
  wrong. New §6 connector rule 7: every arrow runs straight for its arrowhead's length + 4px (10px
  minimum) before each tip, both tips when two-headed; routed connectors finish their last corner
  there (shrinking it to `r=4` when tight) and curves put their last control point on that lead.
  SKILL.md, primitives-core.md and the type references that prescribe `r=8` corners state the rule.
- New `scripts/verify-arrow-ends.py` (in CI, and run by `self_check.py`): sizes each arrowhead from
  its marker (`markerWidth`, `refX`, `viewBox`, `markerUnits` x stroke width) and fails a tip that
  bends more than 3° within its lead. Covers `<path>` (arcs sampled), `<polyline>` and `<line>`.
- Fixed 65 bent arrow ends in shipped examples: 23 in light, 21 each in dark and full (architecture,
  datalake, deployment, high-level, high-level-vertical, it-state, medallion, state); the 8 matching
  hand-drawn variants are regenerated. The medallion promotion-arc formula now ends on a 16px lead.

## 2026-10-10 — illustration-tools 3.3.0: animated SVG export

- `export_diagram.py --animated` writes `<name>.animated.svg` from a motion figure: each step fades in
  once on the figure's own clock, as CSS inside the SVG, with no script and no remote fonts, so it
  plays as a README image on GitHub. Reduced motion shows the complete figure, and the last frame is
  that same figure; a rendered test enforces it.
- Fix: exported SVGs gave HTML-style valueless attributes (`data-motion-item`) no value, which is not
  XML, so browsers opening the `.svg` by itself showed a parse error. Every export now parses as XML.

## 2026-10-10 — notices only where they apply

- `dev-tools` 1.1.1 and `agent-tools` 1.1.3 no longer carry `THIRD_PARTY_NOTICES.md`: neither bundle
  contains third-party material. The notices cover Illustrate only and stay in `illustration-tools`.
  Release archives add notices only for bundles that have them.

## 2026-10-10 — repository created

- Portable skills move here from `samykabu/sanduq`, which keeps the Spec Kit extensions and the
  Claude Code plugin marketplace. The marketplace now installs bundles from this repository.
- All bundles are relicensed under **MIT**. Each bundle carries `LICENSE`; `illustration-tools` also carries
  `THIRD_PARTY_NOTICES.md` for the material it bundles.
- `illustration-tools` 3.2.1: neutral example footers; plugin authorship updated.
- `dev-tools` 1.1.0: the portable User Manual skills gain theme selection, right-to-left theme
  styles, per-edition asset privacy, and the newer freshness state (see the bundle notes in
  `samykabu/sanduq` for details). New test suite.
- `agent-tools` 1.1.2: see [its changelog](skills/agent-tools/CHANGELOG.md).
- Install with `npx skills add samykabu/sanduq-skills`. The old `npx skills add samykabu/sanduq`
  path no longer lists these skills.
