# Changelog

Bundles are versioned independently and tagged `<bundle>-vX.Y.Z`. History before this repository
existed is in [samykabu/sanduq](https://github.com/samykabu/sanduq/blob/main/CHANGELOG.md).

This file keeps each bundle's current major version (illustration-tools 3.x, dev-tools 2.x, agent-tools 1.x).

## 2026-11-05 — dev-tools 2.0.5

- **dev-tools 2.0.5.** `user-manual`: `build_manual.py --all` builds the audiences configured in `manual.yml`, so a manual with end-user and administrator editions no longer fails for missing technical pages. Omitting the audience selection retains the three-audience fallback; invalid selections fail before building. Explicit single-edition behavior is unchanged.

## 2026-11-05 — dev-tools 2.0.4

- **dev-tools 2.0.4.** `github-wiki-publish`: a page that begins with its own H1 is published without it and named after it (spaces as hyphens, backticks and forbidden characters removed), because the Wiki already shows the filename as the title; Home keeps a deliberately different H1. Home is served at `/wiki`, so its images, page links and the sidebar use absolute Wiki URLs.

## 2026-11-05 — agent-tools 1.9.2

- **agent-tools 1.9.2.** The plugin description names each of the three skills. No behaviour change. See the [bundle changelog](skills/agent-tools/CHANGELOG.md).

## 2026-11-04 — agent-tools 1.9.1

- **agent-tools 1.9.1.** `delegate-task` keeps structured logs parseable after secret masking and preserves numeric usage telemetry. Credential values remain masked, including numeric values and nested containers. See the [bundle changelog](skills/agent-tools/CHANGELOG.md).

## 2026-10-31 — dev-tools 2.0.3

- **dev-tools 2.0.3.** `user-manual`: a `manual.yml` from before 2.0.0 (MkDocs settings such as `theme` or `primary`, and no `renderer.kind`) keeps building with the `mkdocs` renderer instead of switching to Markdown, and the build prints a notice to add `kind: mkdocs`. When a renderer command is Pandoc and sets no `--from`, the build adds `--from=gfm+rebase_relative_paths`, so pages read as GitHub Markdown and images resolve from each page; the documented recipe is plain `pandoc {pages} ...` again. `build_manual.py --help` lists the renderers, the placeholders and both behaviours.

## 2026-10-30 — agent-tools 1.9.0

- **agent-tools 1.9.0.** New skill `planning-majlis`: a gated planning committee of expert roles run as parallel subagents, in full mode (new software) or feature mode. Five core roles always sit; optional roles are proposed from the request and confirmed by the user. `scripts/gate.py` decides the gate: every seated role at 9/10 or higher and no OPEN rows in the decision record. See [docs/skills/planning-majlis.md](docs/skills/planning-majlis.md).

## 2026-10-30 — dev-tools 2.0.2

- **dev-tools 2.0.2.** `user-manual`: code examples are left exactly as written. The build and the audit find fenced and indented code blocks with a CommonMark parser (markdown-it-py, now in `requirements.lock` next to PyYAML), the block rules GitHub uses, list items and unclosed fences included. The build no longer reads a code example such as `[region]: endpoint,` as a link definition (which stopped the build with "Missing manual asset"), no longer rewrites links inside code, and the MkDocs renderer no longer converts alerts or `<details>` shown inside code. The audit checks links and MkDocs-only syntax outside code only; it still scans code for secrets.

## 2026-10-30 — dev-tools 2.0.1

- **dev-tools 2.0.1.** `user-manual`: the MkDocs renderer labels each page in the navigation with its front-matter `title` again; 2.0.0 strips front matter from assembled pages, so pages whose title differed from their first heading lost it. `edition.json` now lists every page's title under `titles`. The documented Pandoc recipe reads pages with `-f gfm+rebase_relative_paths`, so images resolve from each page's own folder; checked with Pandoc 3.1.3 on a nested page with a screenshot.

## 2026-10-30 — dev-tools 2.0.0

- **dev-tools 2.0.0 (breaking).** `user-manual` no longer depends on MkDocs. `build_manual.py` assembles each edition (audience and language, optionally one module) as Markdown with only the assets its pages reach, plus `edition.json` (title, language, direction, pages in reading order, navigation, brand) and `metadata.yml` (Pandoc-style title block with `lang` and `dir`). `renderer.kind` in `manual.yml` then renders it: `markdown` (the default; the edition itself, readable on GitHub), `command` (your own tool and templates, such as Pandoc or Quarto, with `{pages}`, `{edition}`, `{metadata}`, `{output}` and other placeholders, run from `User-Manual/`), or `mkdocs` (the HTML site and `--pdf`). `--renderer` overrides the kind for one build and `--print-renderer` reports it for CI. Zensical compatibility builds are removed.
- One skill instead of five: the `user-manual-api-docs`, `user-manual-release-docs`, `user-manual-ui-screenshots` and `user-manual-preview-publishing` skills are removed; their instructions are references `user-manual` loads when a task needs them (`references/api-docs.md`, `release-docs.md`, `ui-screenshots.md`, `preview-publishing.md`).
- Pages are written in GitHub-flavored Markdown so they read correctly on GitHub: GitHub alerts (`> [!NOTE]`) and `<details>`. The MkDocs renderer converts alerts to admonitions titled in the edition's language and renders Markdown inside `<details>`. `audit_manual.py` warns about MkDocs-only syntax (`!!!`, `???`, `=== "..."`) and names the GitHub form.
- `theme/brand.yml` (title, subtitle, author, copyright, logo, primary colour) reaches every renderer: the manifest and metadata for a command, the site name, logo, accent colour and PDF cover for MkDocs. `theme/pdf/cover.html` and `styles.scss` replace the PDF cover and add PDF styles; `renderer.custom_dir` (or `theme_options.custom_dir`) may be relative to `User-Manual/`.
- Links with a title, `<angle-bracketed>` targets (paths with spaces) and reference definitions are rewritten and their assets staged like plain links, in the build and the audit.
- Installs are split: `requirements.lock` (PyYAML only), `requirements-mkdocs.lock` and `requirements-pdf.lock`; the CI templates install only what the selected renderer needs and build PDFs only with `mkdocs`. New manuals get `renderer.kind: markdown`, `theme/brand.yml` and no copies of the stylesheets or the inert `mkdocs.yml`.
- No migration from 1.x: add `renderer: {kind: mkdocs}` to keep an MkDocs site, and replace calls to the removed skills with `user-manual`.

## 2026-10-29 — agent-tools 1.8.2

- **agent-tools 1.8.2.** `delegate-task`: `collect --summary` reads the journal bounded when it looks up `process_containment` for a lost run, so recovering a run with a large journal no longer runs out of memory. See the [bundle changelog](skills/agent-tools/CHANGELOG.md).

## 2026-10-29 — agent-tools 1.8.1

- **agent-tools 1.8.1.** `delegate-task` (Windows): the supervisor runs the harness inside a kill-on-close job object it alone holds, so killing the supervisor ends every harness descendant; results report `process_containment`, and a lost run reports the job's closure. See the [bundle changelog](skills/agent-tools/CHANGELOG.md).

## 2026-10-27 — agent-tools 1.8.0

- **agent-tools 1.8.0.** `delegate-task`: `contract` lists `--clean-env` and `--keep-env`; finalisation masks token shapes in `stdout.log` and `stderr.log`; `collect` deletes finished runs older than `DELEGATE_PRUNE_DAYS` days (default 30, `0` disables). `progress-report`: the statusline runs the chained command only from an untracked `config.json` that still names the command recorded at install. See the [bundle changelog](skills/agent-tools/CHANGELOG.md). `progress-report`: user text carries `dir="auto"`, so Arabic renders right-to-left.

## 2026-10-22 — agent-tools 1.7.1

- **agent-tools 1.7.1.** The `progress-report` bench writes the LEGACY protocol path with `/` on every OS, so its report is identical on Windows and Linux (Windows counted 5 more bytes per protocol read). See the [bundle changelog](skills/agent-tools/CHANGELOG.md).

## 2026-10-21 — illustration-tools 3.7.1, agent-tools 1.7.0

- **illustration-tools 3.7.1.** The data verifiers share `scripts/svg_scan.py` (the SVG scanner, first-wins attributes, `median`, `line_of`, the printed-number reader and the hand-variant test), loaded the way they load `theme_tokens.py`. Each verifier keeps its own transform contract. No output changes; a copied verifier needs `svg_scan.py` beside it.
- **agent-tools 1.7.0.** `progress-report` removes `status --json --schema v2`, `export --schema v2` and the `classic` page layout, deprecated in 1.6.1. A v2 or classic request exits 2 with one line that names an installed Sanduq Workflow and, below 1.17.0, its upgrade command. A `theme.json` that still says `classic` shows the timeline, and `progress status` ends its line with a notice; it also flags an installed Sanduq Workflow older than 1.17.0. The one-line status and `runs --json` are unchanged. The bench reads `PROGRESS_BENCH_CLI`, `PROGRESS_BENCH_SKILL` and `PROGRESS_BENCH_DOC` so a repository that vendors it can run it in its own layout. See the [bundle changelog](skills/agent-tools/CHANGELOG.md).

## 2026-10-21 — agent-tools 1.6.2

- **agent-tools 1.6.2.** `progress-report` declares the `.git/info/exclude` lines it writes in `.git/info/sanduq-runtime.json`, so Sanduq Memory accepts Progress's runtime files in a feature folder instead of refusing to queue it.

## 2026-10-21 — illustration-tools 3.7.0, agent-tools 1.6.1

- **illustration-tools 3.7.0.** `scripts/generate-hand-variants.cjs --in <file> --out <file> [--seed N]` converts one diagram, so a project can make a hand-drawn version of its own file. It needs Node 18+ and a one-time `npm ci` in the skill folder; without the packages it says so and exits 1. With no arguments it regenerates the shipped examples as before. `primitive-sketchy.md` and `variants.md` give the installed route and say to deliver the minimal variant when Node is missing. The three import references run the step 7 checks (`verify-geometry.py`, `self_check.py --strict`, or `--profile technical-color`, and the type's verifier) before the taste gate. `technical-color-process-flow.md` replaces the Claude.ai preview procedure with three lines: run step 7, run `lint-render.py` when Playwright is installed, else ask the user to open the file. CI installs the generator's packages so its test runs.
- **agent-tools 1.6.1.** `progress-report` docs mark `--schema v2` and the `classic` layout as deprecated; they will be removed in a later release. No code changes. See the [bundle changelog](skills/agent-tools/CHANGELOG.md).

## 2026-10-20 — illustration-tools 3.6.0, agent-tools 1.6.0

- **illustration-tools 3.6.0.** Every shipped template and example now passes the check the skill's procedure requires: 274 of 296 HTML files pass `self_check.py --strict` (51 before), and the 18 technical-color files pass the new `--profile technical-color`, which allows exactly the pinned export toolbar. A baseline test keeps it that way. `scripts/icon_lookup.py` finds icons without reading the catalog (`primitive-icons.md` 81.9 KB to 4.6 KB). `export.md` is read only when the exporter fails; `output-spec.md` is split so imports read only their half (`size-classes.md`). The technical-color toolbar section exists once.
- **agent-tools 1.6.0.** `progress-report` browser tests run only with `PROGRESS_UI_TESTS=1` (the default suite drops from 219 s to 138 s); `live_ab.py` moved to `tests/` beside the bench it imports, so nothing outside `tests/` imports from it.

## 2026-10-19 — illustration-tools 3.5.0, agent-tools 1.5.0

- **illustration-tools 3.5.0.** `illustrate` SKILL.md is procedure-first: 11.7 KB and 155 lines instead of 34.7 KB and 442, with the create procedure as the second section and the stable §0 to §12 tags kept. New references: `type-index.md` (one line per type and variant, so a caller reads 6.5 KB to choose), `taste-gate.md` (judgement checks, read once per diagram) and `variants.md`. `type-line`, `type-scatter`, `type-bar` and `type-treemap` are split into `slopegraph`, `ridgeline`, `streamgraph`, `bump`, `bubble`, `beeswarm`, `dumbbell` and `marimekko` files (a plain line chart reads 2.8 KB instead of 43 KB). `self_check.py --strict` adds the mechanical taste-gate checks and `verify-geometry.py --orthogonal` the connector check; default output is unchanged. The unloaded `commands/` folder is removed.
- **agent-tools 1.5.0.** `progress-report` `hook.py` reads the event from the payload when no argument is given, so one entry file serves the Spec Kit dispatcher and direct wiring; `hooks install` writes SessionEnd for Codex (five events on both hosts) and takes `--post-tool-matcher`; `verbs.md` names the long docs as human references.

## 2026-10-18 — illustration-tools 3.4.3, agent-tools 1.4.3: portable plugin manifests

- Every bundle gains a root `plugin.json` in the Agent Plugins 1.0.0 format, mirroring its `.claude-plugin/plugin.json`, so Codex (`codex plugin marketplace add samykabu/sanduq`, then `codex plugin add <bundle>@sanduq`) and Claude Code install the same bundle. CI checks the two manifests agree and validates every SKILL.md against the Agent Skills frontmatter rules. No skill content changes.

## 2026-10-18 — agent-tools 1.4.2: review fixes

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

## 2026-10-17 — agent-tools 1.3.1: review fixes

- Linux children enumeration fallback, case-insensitive Windows env merge, cancel-before-launch on Windows, duplicate
  facts lanes folded, stale receipts skipped for the current stage. See [agent-tools CHANGELOG](skills/agent-tools/CHANGELOG.md#131--2026-10-17).

## 2026-10-17 — agent-tools 1.3.0: progress-report correctness patch

- `progress-report`: stage from accepted receipts, stale pauses no longer block, frozen durations, one lane per run,
  attention-first layout with kind-filtered events. See [agent-tools CHANGELOG](skills/agent-tools/CHANGELOG.md#130--2026-10-17).

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
- `agent-tools` 1.1.2: see [its changelog](skills/agent-tools/CHANGELOG.md).
- Install with `npx skills add samykabu/sanduq-skills`. The old `npx skills add samykabu/sanduq`
  path no longer lists these skills.
