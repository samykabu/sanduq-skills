# Changelog

## Unreleased — agent-tools

- **agent-tools.** `delegate-task`: `contract` lists `--clean-env` and `--keep-env`; finalisation masks token shapes in `stdout.log` and `stderr.log`; `collect` deletes finished runs older than `DELEGATE_PRUNE_DAYS` days (default 30, `0` disables). `progress-report`: the statusline runs the chained command only from an untracked `config.json` that still names the command recorded at install. See the [bundle changelog](skills/agent-tools/CHANGELOG.md). `progress-report`: user text carries `dir="auto"`, so Arabic renders right-to-left.

## 2026-10-27 — dev-tools 1.5.0

- **dev-tools 1.5.0.** Adds `github-wiki-publish`, a standalone skill for publishing existing
  pages, reports, diagrams, and assets to a GitHub Wiki. It preserves unrelated content, checks
  links and Unicode, reconciles concurrent Git changes, and reports remote verification separately
  from browser rendering. The existing release workflow includes the skill in the bundle and
  creates its individual ZIP with SHA256 checksums. Local Git behavior checks passed; a live
  browser test of the new skill remains unrun, and Claude Desktop support is unverified.

## 2026-10-22 — agent-tools 1.7.1

- **agent-tools 1.7.1.** The `progress-report` bench writes the LEGACY protocol path with `/` on every OS, so its report is identical on Windows and Linux (Windows counted 5 more bytes per protocol read). See the [bundle changelog](skills/agent-tools/CHANGELOG.md).

## 2026-10-21 — dev-tools 1.4.0, illustration-tools 3.7.1, agent-tools 1.7.0: round 5

- **dev-tools 1.4.0.** `init_manual.py --no-tools` skips the script copies in `User-Manual/tools/`, for a project whose CI runs the scripts from another place. Without `--ci-policy` the CI workflows follow the `ci:` mapping in `<repo-root>/.specify/workflow.yml` when that file exists (before, the shipped default was used); `sanduq_ci.load_ci` reads a directory as a project root. `manual.yml` gains `lifecycle.impact_scope: all`. Sanduq can now vendor `init_manual.py` instead of keeping its own copy.
- **illustration-tools 3.7.1.** The data verifiers share `scripts/svg_scan.py` (the SVG scanner, first-wins attributes, `median`, `line_of`, the printed-number reader and the hand-variant test), loaded the way they load `theme_tokens.py`. Each verifier keeps its own transform contract. No output changes; a copied verifier needs `svg_scan.py` beside it.
- **agent-tools 1.7.0.** `progress-report` removes `status --json --schema v2`, `export --schema v2` and the `classic` page layout, deprecated in 1.6.1. A v2 or classic request exits 2 with one line that names an installed Sanduq Workflow and, below 1.17.0, its upgrade command. A `theme.json` that still says `classic` shows the timeline, and `progress status` ends its line with a notice; it also flags an installed Sanduq Workflow older than 1.17.0. The one-line status and `runs --json` are unchanged. The bench reads `PROGRESS_BENCH_CLI`, `PROGRESS_BENCH_SKILL` and `PROGRESS_BENCH_DOC` so a repository that vendors it can run it in its own layout. See the [bundle changelog](skills/agent-tools/CHANGELOG.md).

## 2026-10-21 — agent-tools 1.6.2

- **agent-tools 1.6.2.** `progress-report` declares the `.git/info/exclude` lines it writes in `.git/info/sanduq-runtime.json`, so Sanduq Memory accepts Progress's runtime files in a feature folder instead of refusing to queue it.

## 2026-10-21 — dev-tools 1.3.0, illustration-tools 3.7.0, agent-tools 1.6.1: optimization round 4

- **dev-tools 1.3.0.** `init_manual.py` no longer overwrites an existing `docs/<lang>/index.md`; it writes the stub only when the page is missing, as it already did for module pages. `build_manual.py` captures the MkDocs or Zensical output: a successful build prints one line per edition, and a failed build prints the edition name and the last 40 lines of the renderer's output to stderr. `assets/user-manual-config.template.yml` is removed; no script read it.
- **illustration-tools 3.7.0.** `scripts/generate-hand-variants.cjs --in <file> --out <file> [--seed N]` converts one diagram, so a project can make a hand-drawn version of its own file. It needs Node 18+ and a one-time `npm ci` in the skill folder; without the packages it says so and exits 1. With no arguments it regenerates the shipped examples as before. `primitive-sketchy.md` and `variants.md` give the installed route and say to deliver the minimal variant when Node is missing. The three import references run the step 7 checks (`verify-geometry.py`, `self_check.py --strict`, or `--profile technical-color`, and the type's verifier) before the taste gate. `technical-color-process-flow.md` replaces the Claude.ai preview procedure with three lines: run step 7, run `lint-render.py` when Playwright is installed, else ask the user to open the file. CI installs the generator's packages so its test runs.
- **agent-tools 1.6.1.** `progress-report` docs mark `--schema v2` and the `classic` layout as deprecated; they will be removed in a later release. No code changes. See the [bundle changelog](skills/agent-tools/CHANGELOG.md).

## 2026-10-20 — illustration-tools 3.6.0, agent-tools 1.6.0: optimization round 3

- **illustration-tools 3.6.0.** Every shipped template and example now passes the check the skill's procedure requires: 274 of 296 HTML files pass `self_check.py --strict` (51 before), and the 18 technical-color files pass the new `--profile technical-color`, which allows exactly the pinned export toolbar. A baseline test keeps it that way. `scripts/icon_lookup.py` finds icons without reading the catalog (`primitive-icons.md` 81.9 KB to 4.6 KB). `export.md` is read only when the exporter fails; `output-spec.md` is split so imports read only their half (`size-classes.md`). The technical-color toolbar section exists once.
- **agent-tools 1.6.0.** `progress-report` browser tests run only with `PROGRESS_UI_TESTS=1` (the default suite drops from 219 s to 138 s); `live_ab.py` moved to `tests/` beside the bench it imports, so nothing outside `tests/` imports from it.

## 2026-10-19 — illustration-tools 3.5.0, dev-tools 1.2.0, agent-tools 1.5.0: optimization round 2

- **illustration-tools 3.5.0.** `illustrate` SKILL.md is procedure-first: 11.7 KB and 155 lines instead of 34.7 KB and 442, with the create procedure as the second section and the stable §0 to §12 tags kept. New references: `type-index.md` (one line per type and variant, so a caller reads 6.5 KB to choose), `taste-gate.md` (judgement checks, read once per diagram) and `variants.md`. `type-line`, `type-scatter`, `type-bar` and `type-treemap` are split into `slopegraph`, `ridgeline`, `streamgraph`, `bump`, `bubble`, `beeswarm`, `dumbbell` and `marimekko` files (a plain line chart reads 2.8 KB instead of 43 KB). `self_check.py --strict` adds the mechanical taste-gate checks and `verify-geometry.py --orthogonal` the connector check; default output is unchanged. The unloaded `commands/` folder is removed.
- **dev-tools 1.2.0.** `build_manual.py --all` builds every configured audience and language in one call; the preview and release workflows use it.
- **agent-tools 1.5.0.** `progress-report` `hook.py` reads the event from the payload when no argument is given, so one entry file serves the Spec Kit dispatcher and direct wiring; `hooks install` writes SessionEnd for Codex (five events on both hosts) and takes `--post-tool-matcher`; `verbs.md` names the long docs as human references.

## 2026-10-19 — dev-tools 1.1.3: pinned actions and fork guard for the User Manual workflows

- `user-manual` preview and release workflows pin every action to a commit SHA with its version in a comment: `actions/checkout` v4.3.0, `actions/setup-python` v5.6.0, `actions/upload-artifact` v4.6.2 and `actions/github-script` v7.1.0.
- The preview job skips pull requests from forks when the project's linux runner is self-hosted, so a self-hosted runner never executes a fork's checkout and scripts. The new `self_hosted` template flag renders the guard; GitHub-hosted projects get no `if:`.

## 2026-10-18 — illustration-tools 3.4.3, dev-tools 1.1.2, agent-tools 1.4.3: portable plugin manifests

- Every bundle gains a root `plugin.json` in the Agent Plugins 1.0.0 format, mirroring its `.claude-plugin/plugin.json`, so Codex (`codex plugin marketplace add samykabu/sanduq`, then `codex plugin add <bundle>@sanduq`) and Claude Code install the same bundle. CI checks the two manifests agree and validates every SKILL.md against the Agent Skills frontmatter rules. No skill content changes.

## 2026-10-18 — agent-tools 1.4.2: fixes from the sanduq #90 review

- `progress-report` decodes Scope's spreadsheet-style option labels (`AA` is the 27th option), applies a session-bound self-report
  only when the observed session matches, lists every file a build read as a source, and keeps a losing workstream visible. See the
  [bundle changelog](skills/agent-tools/CHANGELOG.md#142--2026-10-18).

## 2026-10-18 — agent-tools 1.4.1: README for the Timeline page

- `progress-report` README describes the Timeline page; no code changes. See the
  [bundle changelog](skills/agent-tools/CHANGELOG.md#141--2026-10-18).

## 2026-10-18 — agent-tools 1.4.0: Progress Timeline

- `progress-report` 1.2.0: v3 projection (stages, workstreams, runs, decisions, timeline) with the Timeline view as the
  default page, `--schema v2` compatibility, coordinator self-report and `theme --layout`. See the
  [bundle changelog](skills/agent-tools/CHANGELOG.md#140--2026-10-18).

## 2026-10-17 — illustration-tools 3.4.2: stable render verification

- Pause page clocks during render comparisons and advance them explicitly for declared reveal holds. JavaScript timers can no longer produce inconsistent clipping results between captures.
- Restore SVG and ancestor styles exactly after capture, including when a capture fails.

Bundles are versioned independently and tagged `<bundle>-vX.Y.Z`. History before this repository
existed is in [samykabu/sanduq](https://github.com/samykabu/sanduq/blob/main/CHANGELOG.md).

## 2026-10-17 — agent-tools 1.3.1: review fixes

- Linux children enumeration fallback, case-insensitive Windows env merge, cancel-before-launch on Windows, duplicate
  facts lanes folded, stale receipts skipped for the current stage. See [agent-tools CHANGELOG](skills/agent-tools/CHANGELOG.md#131--2026-10-17).

## 2026-10-17 — agent-tools 1.3.0: progress-report correctness patch

- `progress-report`: stage from accepted receipts, stale pauses no longer block, frozen durations, one lane per run,
  attention-first layout with kind-filtered events. See [agent-tools CHANGELOG](skills/agent-tools/CHANGELOG.md#130--unreleased).

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
