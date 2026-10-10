# Changelog

Bundles are versioned independently and tagged `<bundle>-vX.Y.Z`. History before this repository
existed is in [samykabu/sanduq](https://github.com/samykabu/sanduq/blob/main/CHANGELOG.md).

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
