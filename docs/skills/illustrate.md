# illustrate

Illustrate draws diagrams and charts as one self-contained HTML file you can open, edit, and export.

| | |
| --- | --- |
| Bundle | `illustration-tools` (Claude Code plugin `illustration-tools@sanduq`) |
| Version | 3.4.0 |
| Prerequisites | Nothing for HTML. Python 3.10+ for themes and SVG export. Node 18+ for the hand-drawn style. Playwright with Chromium for PNG and GIF; Pillow for GIF. |
| Hosts | Codex: yes. Claude Code: yes. Claude Desktop: HTML yes; exports unverified. |

## Install

Follow the [Install section of the README](../../README.md#install) for your
[host](../glossary.md#host). In Claude Code, install the `illustration-tools`
[plugin](../glossary.md#plugin).

## First prompt

<details open>
<summary><strong>Codex</strong></summary>

```text
$illustrate Draw a state machine for an order: placed, paid, shipped, delivered, and cancelled.
Show that cancelling is only possible before shipping.
```
</details>

<details>
<summary><strong>Claude Code</strong></summary>

```text
/illustration-tools:illustrate Draw a state machine for an order: placed, paid, shipped,
delivered, and cancelled. Show that cancelling is only possible before shipping.
```

You can also skip the command and just ask: "draw a state machine for our order lifecycle".
</details>

Before drawing, the skill states its plan: the diagram type, the size, and anything it will leave
out. Redirect it then if the plan is wrong.

## What you get

- One `.html` file with an inline SVG diagram, a title, and an accessible description.
- On first use, a `.github/illustration-theme.yml` file that records your project's
  [theme](../glossary.md#theme).
- On request only, an [export](../glossary.md#export) next to the HTML: `.svg`, `.png`,
  `.animated.svg`, or `.gif`.

![Sequence diagram: a client calls an API with a bearer token; it gets the body back when the token is valid, or a 401, then refreshes the token with the auth service and retries. Each arrow draws on in turn.](../media/example-sequence-oauth.animated.svg)

Arrow style `draw`. Source: [example-sequence-oauth.html](../media/example-sequence-oauth.html).
More in [examples](../examples.md).

## Options worth knowing

**Themes.** Pick Cobalt Porcelain (the default), Emerald Mist, Sanduq Classic, or your own colors
and fonts. Each has a light and a dark palette. The theme applies to every diagram in the project.

**Diagram types.** There are 44, in these groups:

| Group | Types |
| --- | --- |
| Systems and structure | architecture, architecture delta, IT current-state, high-level, deployment, layer stack, nested, data-platform integration, dependency graph, UML class |
| Behavior and process | flowchart, sequence, state machine, swimlane, process, data flow, loop, user journey, story map, kanban |
| Data models | ER, database schema, medallion, data-platform security matrix |
| Time and planning | timeline, Gantt, Wardley map |
| Hierarchy and comparison | tree, org chart, pyramid or funnel, Venn, quadrant, fishbone |
| Charts | bar, line, scatter, heatmap, waterfall, treemap, radar, polar, Sankey |
| Spatial | exploded axonometric, axonometric plan |

**Styles.** Each diagram can be minimal light, minimal dark, full editorial, or hand-drawn. Two
technical-color families cover cloud and infrastructure maps and numbered process flows. They
include a built-in copy, PNG, and PDF toolbar.

**Export.** Ask in plain words ("export it as SVG"), or run the exporter from the skill folder:

```bash
python scripts/export_diagram.py diagram.html                  # SVG and PNG
python scripts/export_diagram.py diagram.html --svg-only
python scripts/export_diagram.py diagram.html --png-only --scale 3
python scripts/export_diagram.py diagram.html --animated --arrows=pulse
python scripts/export_diagram.py diagram.html --gif --arrows=chevrons --theme dark --fps 15
```

- `--animated` writes an [animated SVG](../glossary.md#animated-svg) for READMEs.
- `--gif` writes the same animation as a GIF.
- `--arrows` sets the [arrow style](../glossary.md#arrow-style): `draw` (the default), `flow`,
  `pulse`, `draw-flow`, or `chevrons`.
- `--theme light|dark` and `--fps 1-30` apply to GIFs only.

**Redraw an existing diagram.** Give it a `.drawio`, `.mmd`, or `.excalidraw` file. It keeps the
content and redraws it in your theme, then lists what it merged or dropped.

## Limits

- At most 9 nodes and 12 arrows per diagram. Larger subjects become an overview plus a detail.
  A faithful redraw of an existing file may go up to 24 nodes, grouped into zones.
- Exports happen only when you ask.
- An animated export needs arrows with arrowheads or a step-by-step motion figure.
- A GIF cannot follow the reader's [reduced motion](../glossary.md#reduced-motion) setting. Prefer
  the animated SVG where SVG images are allowed.
- The animated SVG uses local fonts only, so text may look slightly different from the HTML.
- Not for photos or generated raster images.

## Related

- [Product map](../product-map.md)
- [Animated examples](../examples.md)
- [user-manual](user-manual.md), which uses this skill for its diagrams when it is installed
- [Glossary](../glossary.md)
