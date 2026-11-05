# Regenerate: python docs/media/build_skill_diagrams.py docs/media
"""Generate product-map, planning-majlis-flow and delegate-task-flow (html + static svg + animated svg).

Same Cobalt Porcelain tokens and layout grammar as Sanduq's docs/diagrams/build_overview_diagrams.py.
The animated file is the static drawing plus a reduced-motion-gated reveal.
"""
import sys
from html import escape
from pathlib import Path

OUT = Path(sys.argv[1])
SANS = "'IBM Plex Sans', system-ui, sans-serif"
MONO = "'IBM Plex Mono', ui-monospace, monospace"
SERIF = "'IBM Plex Serif', serif"
FONTS = "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&amp;family=IBM+Plex+Sans:wght@400;500;600&amp;family=IBM+Plex+Serif:ital,wght@0,400;1,400&amp;display=swap"
LIGHT = dict(paper="#f6f8fc", paper2="#ffffff", ink="#15233c", muted="#4f6078", soft="#6b7a90",
             rule="#c7d2e2", accent="#2563eb", tint="rgba(37,99,235,0.09)", link="#1d4ed8")
DARK = dict(paper="#101827", paper2="#17233a", ink="#f5f7fb", muted="#b6c2d4", soft="#8796ac",
            rule="#40506a", accent="#6ea0ff", tint="rgba(110,160,255,0.14)", link="#8ab4ff")


def tokens(t):
    return ';'.join(f'--{k}:{v}' for k, v in t.items())


CSS = (
    f"svg{{{tokens(LIGHT)}}}"
    f"@media (prefers-color-scheme: dark){{svg{{{tokens(DARK)}}}}}"
    f"text{{font-family:{SANS};fill:var(--ink)}}"
    f".m{{font-family:{MONO};fill:var(--muted)}}.lb{{fill:var(--muted)}}"
    f".e{{font-family:{MONO};fill:var(--soft);letter-spacing:.08em}}"
    ".bg{fill:var(--paper)}.zone{fill:none;stroke:var(--rule)}"
    ".box{fill:var(--paper2);stroke:var(--rule)}.focal{fill:var(--tint);stroke:var(--accent)}"
    ".dash{stroke-dasharray:5 4}"
    ".c{fill:none;stroke:var(--muted);stroke-width:1.5}.opt{stroke-dasharray:5 4}"
    ".lk{fill:none;stroke:var(--link);stroke-width:1.5}"
    ".mh{fill:none;stroke:var(--muted)}.mhl{fill:none;stroke:var(--link)}"
)


def defs():
    return ('<defs>'
            '<marker id="ar" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
            '<path class="mh" d="M0 1 L7 4 L0 7"/></marker>'
            '<marker id="arl" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
            '<path class="mhl" d="M0 1 L7 4 L0 7"/></marker></defs>')


def node(x, y, w, h, name, subs, cls='box', size=16):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" class="{cls}"/>']
    cx = x + w / 2
    top = y + h / 2 - len(subs) * 9 + 5
    out.append(f'<text x="{cx:g}" y="{top:g}" text-anchor="middle" font-size="{size}" font-weight="600">{escape(name)}</text>')
    for i, s in enumerate(subs):
        out.append(f'<text class="m" x="{cx:g}" y="{top + 19 + i * 16:g}" text-anchor="middle" font-size="12">{escape(s)}</text>')
    return ''.join(out)


def diamond(cx, cy, w, h, name, subs):
    pts = f'{cx},{cy - h / 2:g} {cx + w / 2:g},{cy} {cx},{cy + h / 2:g} {cx - w / 2:g},{cy}'
    out = [f'<polygon points="{pts}" class="focal"/>',
           f'<text x="{cx}" y="{cy - 4 - (len(subs) - 1) * 8:g}" text-anchor="middle" font-size="15" font-weight="600">{escape(name)}</text>']
    for i, s in enumerate(subs):
        out.append(f'<text class="m" x="{cx}" y="{cy + 14 - (len(subs) - 1) * 8 + i * 16:g}" text-anchor="middle" font-size="12">{escape(s)}</text>')
    return ''.join(out)


def label(x, y, text, anchor='start'):
    return f'<text class="lb" x="{x}" y="{y}" font-size="12" text-anchor="{anchor}">{escape(text)}</text>'


def g(step, body):
    return f'<g class="s s{step}">{body}</g>'


def svg(slug, w, h, title, desc, body, css):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" '
            f'aria-labelledby="{slug}-title {slug}-desc"><title id="{slug}-title">{escape(title)}</title>'
            f'<desc id="{slug}-desc">{escape(desc)}</desc>{defs()}<style>{css}</style>'
            f'<rect class="bg" width="{w}" height="{h}"/>{body}</svg>')


def motion_css(steps, step_ms):
    delays = ''.join(f'.s{i}{{animation-delay:{(i - 1) * step_ms}ms}}' for i in range(1, steps + 1))
    return ('@media (prefers-reduced-motion: no-preference){'
            '.s{animation:rv 480ms cubic-bezier(.2,.8,.2,1) both}'
            '@keyframes rv{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}'
            f'{delays}}}')


def write(slug, w, h, title, desc, body, steps, step_ms=480, note=''):
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    static = svg(slug, w, h, title, desc, body, CSS)
    (OUT / f'{slug}.svg').write_text(xml + static + '\n', encoding='utf-8', newline='\n')
    (OUT / f'{slug}.animated.svg').write_text(xml + svg(slug, w, h, title, desc, body, CSS + motion_css(steps, step_ms)) + '\n',
                                              encoding='utf-8', newline='\n')
    page = (f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)}</title><link rel="stylesheet" href="{FONTS}">'
            f'<style>body{{margin:24px;background:#f6f8fc;color:#15233c;font-family:{SANS}}}'
            f'@media (prefers-color-scheme: dark){{body{{background:#101827;color:#f5f7fb}}}}'
            f'h1{{font-family:{SERIF};font-weight:400}}.diagram{{overflow-x:auto}}'
            f'svg{{width:100%;min-width:{w}px;max-width:{w}px;display:block}}p{{max-width:72ch;line-height:1.5}}</style>'
            f'<h1>{escape(title)}</h1><p>{escape(desc)}</p><div class="diagram">{static}</div>'
            f'<p>Editable source. Theme: Cobalt Porcelain, light and dark. {escape(note)} '
            f'Exports: <code>{slug}.svg</code> (static) and <code>{slug}.animated.svg</code> '
            f'(same drawing plus a one-time reveal, off when reduced motion is requested).</p></html>\n')
    (OUT / f'{slug}.html').write_text(page, encoding='utf-8', newline='\n')


# ---------------------------------------------------------------- product map
def product_map():
    W, BW, BH = 960, 280, 104
    X = [40, 340, 640]
    b = [g(1, '<rect x="20" y="40" width="920" height="260" rx="8" class="zone"/>'
              '<text class="e" x="40" y="70" font-size="12">SANDUQ-SKILLS · 6 SKILLS IN 3 BUNDLES · EACH BUNDLE IS ONE PLUGIN</text>')]
    b.append(g(2, node(X[0], 96, BW, BH, 'illustration-tools', ['illustrate', '44 diagram and chart types'])))
    b.append(g(3, node(X[1], 96, BW, BH, 'dev-tools', ['user-manual', 'github-wiki-publish', 'manuals and wiki publishing'])))
    b.append(g(4, node(X[2], 96, BW, BH, 'agent-tools', ['delegate-task', 'progress-report', 'planning-majlis'])))
    # uses: user-manual -> illustrate, planning-majlis -> delegate-task
    y = 96 + BH + 34
    b.append(g(5, f'<path class="c opt" d="M{X[1] + 70} {96 + BH} V{y} H{X[0] + BW // 2} V{96 + BH + 2}" marker-end="url(#ar)"/>'
                  + label(X[0] + BW // 2 + 12, y + 18, 'user-manual draws with illustrate when installed')
                  + label(X[2], y - 4, 'planning-majlis can run its critics')
                  + label(X[2], y + 12, 'through delegate-task')))
    # sanduq marketplace and extensions
    b.append(g(6, f'<path class="lk" d="M480 300 V{356 - 2}" marker-end="url(#arl)"/>'
                  + node(300, 356, 360, 80, 'samykabu/sanduq', ['marketplace lists the 3 bundles', 'Spec Kit extensions copy 4 skills'])))
    L = 470
    b.append(g(6, f'<line x1="20" y1="{L}" x2="940" y2="{L}" class="zone"/>'
                  f'<path class="c opt" d="M40 {L + 28} H80" marker-end="url(#ar)"/>' + label(90, L + 32, 'uses when installed')
                  + f'<path class="lk" d="M260 {L + 28} H300" marker-end="url(#arl)"/>' + label(310, L + 32, 'listed by, or copied into')))
    write('product-map', W, L + 56, 'Six skills in three bundles',
          'illustration-tools holds illustrate; dev-tools holds user-manual and github-wiki-publish; agent-tools '
          'holds delegate-task, progress-report and planning-majlis. user-manual draws with illustrate when it is '
          'installed, and planning-majlis can run its critics through delegate-task. Every skill also works on '
          'its own. The samykabu/sanduq repository lists the three bundles in its plugin marketplace and copies '
          'illustrate, user-manual, delegate-task and progress-report into its Spec Kit extensions.',
          ''.join(b), 6, note='Arrows point from a skill to what it uses.')


# -------------------------------------------------------------- planning majlis
def majlis():
    W = 1000
    CX, BW, BH, P = 300, 340, 58, 86
    x0 = CX - BW // 2
    steps = [
        ('Seat the roles', ['5 core roles, optional ones you confirm']),
        ('Recon', ['verified facts, UNVERIFIED list']),
        ('Tracks', ['specialists work in parallel']),
        ('Critiques', ['isolated critics score the tracks']),
        ('Decision record', ['one source of truth, owner rows']),
        ('Re-score round n', ['critics score the current record']),
    ]
    ys = [64 + i * P for i in range(len(steps))]
    b = [g(1, '<text class="e" x="40" y="36" font-size="12">PLANNING-MAJLIS · ONE RUN, FULL MODE</text>')]
    for i, ((name, subs), y) in enumerate(zip(steps, ys)):
        part = node(x0, y, BW, BH, name, subs, 'focal' if i == 5 else 'box')
        if i:
            part = f'<path class="c" d="M{CX} {ys[i - 1] + BH} V{y - 2}" marker-end="url(#ar)"/>' + part
        b.append(g(1 + (i + 1) // 2, part))
    gy = ys[-1] + BH + 90
    b.append(g(4, f'<path class="c" d="M{CX} {ys[-1] + BH} V{gy - 62}" marker-end="url(#ar)"/>'
                  + diamond(CX, gy, 300, 120, 'Gate (gate.py)', ['scores 9/10+, 0 OPEN rows', 'roster and tables valid'])))
    # no -> drill on the open rows -> record v+1 -> next round (back into Re-score)
    rx = 640
    b.append(g(5, f'<path class="lk" d="M{CX + 150} {gy} H{rx - 2}" marker-end="url(#arl)"/>'
                  + label(CX + 162, gy - 8, 'no')
                  + node(rx, gy - 40, 300, 80, 'Drill on the OPEN rows', ['one worker per cluster', 'record v+1'], 'box')
                  + f'<path class="lk" d="M{rx + 150} {gy - 40} V{ys[-1] + BH // 2} H{x0 + BW + 2}" marker-end="url(#arl)"/>'
                  + label(rx + 162, ys[-1] + BH // 2 + 60, 'next round, up to 6')
                  + f'<path class="lk dash" d="M{rx + 150} {gy + 40} V{gy + 118}" marker-end="url(#arl)"/>'
                  + label(rx + 162, gy + 84, 'round 6 failed')
                  + node(rx, gy + 120, 300, 64, 'Stop after round 6', ['report the unresolved blockers'], 'box dash')))
    # yes -> writers -> consistency pass (fix, gate again) -> hand-off
    wy = [gy + 100, gy + 186, gy + 272]
    outs = [('Writers', ['specs from the record only']),
            ('Consistency pass', ['fix contradictions, run gate.py again']),
            ('Hand-off', ['gate result, owner decisions, defaults'])]
    part = f'<path class="c" d="M{CX} {gy + 60} V{wy[0] - 2}" marker-end="url(#ar)"/>' + label(CX + 10, gy + 82, 'yes')
    for i, ((name, subs), y) in enumerate(zip(outs, wy)):
        if i:
            part += f'<path class="c" d="M{CX} {wy[i - 1] + BH} V{y - 2}" marker-end="url(#ar)"/>'
        part += node(x0, y, BW, BH, name, subs, 'focal' if i == 2 else 'box')
    b.append(g(6, part))
    b.append(g(6, '<rect x="640" y="64" width="300" height="114" rx="6" class="box dash"/>'
                  '<text x="656" y="90" font-size="14" font-weight="600">Owner decisions</text>'
                  + ''.join(label(656, 112 + k * 18, t) for k, t in enumerate(
                      ['Money, legal, naming, scope and brand', 'become OD rows with a default.', 'The run continues on the default',
                       'and the hand-off lists each one.']))))
    H = wy[-1] + BH + 30
    write('planning-majlis-flow', W, H, 'A planning-majlis run',
          'Full mode. The skill seats five core roles plus the optional roles you confirm, gathers verified '
          'facts, runs specialist tracks in parallel, then has isolated critics score them. Everything folds into '
          'one decision record. Each re-score round has the critics score the current record, then gate.py runs: '
          'it passes only when every seated role scores 9/10 or more, the record has no OPEN rows, and the roster '
          'and tables are valid. On a fail, a drill on the open rows writes the next record version and the next '
          'round starts; after six rounds without a pass the run stops and reports the unresolved blockers. On a '
          'pass, writers produce the specs from the record, a consistency pass fixes contradictions and runs the '
          'gate again, and the hand-off lists the owner decisions with their defaults. Feature mode runs one '
          'design track instead of several.',
          ''.join(b), 6, 520, note='From skills/agent-tools/skills/planning-majlis/references/process.md.')


# ---------------------------------------------------------------- delegate-task
def delegate():
    W = 1000
    BW, BH = 250, 70
    X = [40, 375, 710]
    y1, y2 = 70, 250
    b = [g(1, '<text class="e" x="40" y="40" font-size="12">DELEGATE-TASK · ONE TASK ON ANOTHER AGENT CLI</text>'
              + node(X[0], y1, BW, BH, 'start', ['returns a run_id at once', '--harness codex, claude, ...']))]
    b.append(g(2, f'<path class="c" d="M{X[0] + BW} {y1 + BH // 2} H{X[1] - 2}" marker-end="url(#ar)"/>'
                  + node(X[1], y1, BW, BH, 'Harness runs', ['in the background', 'you keep working'], 'focal')))
    # collect, with its "still running" loop over the top
    b.append(g(3, f'<path class="c" d="M{X[1] + BW} {y1 + BH // 2} H{X[2] - 2}" marker-end="url(#ar)"/>'
                  + node(X[2], y1, BW, BH, 'collect --wait N', ['waits up to N seconds'])
                  + f'<path class="c" d="M{X[2] + BW - 60} {y1} V{y1 - 22} H{X[2] + 60} V{y1 - 2}" marker-end="url(#ar)"/>'
                  + label(X[2] + BW // 2, y1 - 28, 'still running: collect again later', 'middle')))
    b.append(g(4, f'<path class="c" d="M{X[2] + BW // 2} {y1 + BH} V{y2 - 2}" marker-end="url(#ar)"/>'
                  + label(X[2] + BW // 2 + 10, y1 + BH + 50, 'finished')
                  + node(X[2], y2, BW, 96, 'Result', ['status and why (provenance)', 'files git measured vs claimed', 'tokens used'])))
    b.append(g(5, f'<path class="c" d="M{X[2]} {y2 + 48} H{X[1] + BW + 2}" marker-end="url(#ar)"/>'
                  + node(X[1], y2 + 13, BW, BH, 'You review it', ['read the diff and the checks', 'never trust exit code alone'])))
    b.append(g(6, f'<path class="c" d="M{X[1]} {y2 + 48} H{X[0] + BW + 2}" marker-end="url(#ar)"/>'
                  + label(X[0] + BW + 14, y2 + 40, 'good')
                  + node(X[0], y2 + 13, BW, BH, 'Keep or discard', ['the change is yours to commit'], 'box')
                  + f'<path class="lk" d="M{X[1] + BW // 2} {y2 + 13} V{y1 + BH + 2}" marker-end="url(#arl)"/>'
                  + label(X[1] + BW // 2 + 10, y1 + BH + 30, 'needs a fix: --resume <run_id>')
                  + label(X[1] + BW // 2 + 10, y1 + BH + 46, 'only the delta; a new run_id')))
    status = 'status: starting, running, stalled, adrift (supervisor died, harness alive), lost (both gone), done'
    b.append(g(6, label(40, y2 + 130, status)
                  + label(40, y2 + 148, 'Resume needs a finished run with a session id, on the same harness, folder, CLI version and model.')))
    H = y2 + 170
    write('delegate-task-flow', W, H, 'A delegate-task run',
          'start hands one task to another agent CLI and returns a run id straight away; the harness runs in '
          'the background while you keep working. collect --wait N waits up to N seconds; if the run is still '
          'going it says so and you collect again later. A finished run returns a status of successful, failed or '
          'abandoned with the reason for it, the files git measured next to the files the delegate claimed, and '
          'the tokens used. You review it and keep or discard the change, or resume the same session with only '
          'the change you want, which starts a new run linked to its parent. Resume needs a finished run with a '
          'session id, on the same harness, folder, CLI version and model.',
          ''.join(b), 6, note='From skills/agent-tools/skills/delegate-task/SKILL.md.')


# ------------------------------------------------------------------ user-manual
def manual():
    W = 1000
    BW, BH, CX = 300, 58, 300
    x0 = CX - BW // 2
    b = [g(1, '<text class="e" x="40" y="36" font-size="12">USER-MANUAL · NEW MANUAL OR AN UPDATE</text>'
              + diamond(CX, 110, 320, 96, 'manual.yml exists?', ['User-Manual/ set up']))]
    # new manual branch (left column)
    ny = [210, 296, 382]
    new = [('Interview and inspect', ['audiences, routes, APIs, schema']),
           ('Propose a module map', ['you approve it before writing']),
           ('init_manual.py', ['creates User-Manual/ and its CI tools'])]
    part = f'<path class="c" d="M{CX} {158} V{ny[0] - 2}" marker-end="url(#ar)"/>' + label(CX + 10, 186, 'no')
    for i, ((name, subs), y) in enumerate(zip(new, ny)):
        if i:
            part += f'<path class="c" d="M{CX} {ny[i - 1] + BH} V{y - 2}" marker-end="url(#ar)"/>'
        part += node(x0, y, BW, BH, name, subs)
    # approval loop on the module map
    part += (f'<path class="lk" d="M{x0} {ny[1] + 40} H{x0 - 40} V{ny[1] + 18} H{x0 - 2}" marker-end="url(#arl)"/>'
             + label(x0 - 44, ny[1] + 62, 'changes', 'end'))
    b.append(g(2, part))
    # existing manual branch (right column)
    rx = 640
    b.append(g(3, f'<path class="c" d="M{CX + 160} 110 H{rx + 150} V{ny[1] - 2}" marker-end="url(#ar)"/>'
                  + label(CX + 152, 102, 'yes')
                  + node(rx, ny[1], BW, BH, 'Read manual.yml and the diff', ['scope comes from your request'])))
    # write pages (both branches meet)
    wy = 480
    b.append(g(4, f'<path class="c" d="M{CX} {ny[2] + BH} V{wy - 2}" marker-end="url(#ar)"/>'
                  + f'<path class="c" d="M{rx + 150} {ny[1] + BH} V{wy + BH // 2} H{x0 + BW + 2}" marker-end="url(#ar)"/>'
                  + node(x0, wy, BW, BH, 'Write or update pages', ['only affected pages', 'diagrams via illustrate'], 'focal')))
    ay = wy + 120
    b.append(g(5, f'<path class="c" d="M{CX} {wy + BH} V{ay - 50}" marker-end="url(#ar)"/>'
                  + diamond(CX, ay, 280, 96, 'audit_manual.py', ['coverage, links, secrets'])
                  + f'<path class="lk" d="M{CX - 140} {ay} H{x0 - 40} V{wy + BH // 2} H{x0 - 2}" marker-end="url(#arl)"/>'
                  + label(x0 - 44, ay - 8, 'errors: fix', 'end')))
    by = ay + 100
    outs = [('build_manual.py', ['renderer: markdown, command or mkdocs']),
            ('manual_state.py record', ['freshness for the next change'])]
    part = f'<path class="c" d="M{CX} {ay + 48} V{by - 2}" marker-end="url(#ar)"/>' + label(CX + 10, ay + 70, 'clean')
    for i, (name, subs) in enumerate(outs):
        y = by + i * 86
        if i:
            part += f'<path class="c" d="M{CX} {by + BH} V{y - 2}" marker-end="url(#ar)"/>'
        part += node(x0, y, BW, BH, name, subs)
    # freshness: code changed later -> back to update
    sy = by + 86
    part += (f'<path class="lk dash" d="M{x0 + BW} {sy + BH // 2} H{rx + 150} V{ny[1] + BH + 2}" marker-end="url(#arl)"/>'
             + label(x0 + BW + 14, sy + BH // 2 - 8, 'later: status exits 1 when code changed'))
    b.append(g(6, part))
    H = sy + BH + 40
    write('user-manual-flow', W, H, 'Writing and keeping a user manual',
          'A new manual starts with an interview and a look at the repository, then a proposed module map that '
          'you approve, with as many rounds of changes as you need, before init_manual.py creates User-Manual/. '
          'An existing manual starts from manual.yml and the relevant diff. Both write or update only the affected '
          'pages, with diagrams from illustrate when it is installed. audit_manual.py must pass before '
          'build_manual.py renders the editions with the configured renderer: Markdown, your own command, or '
          'MkDocs. manual_state.py records freshness, and its status exits 1 once code changes, which sends you '
          'back to update the manual.',
          ''.join(b), 6, note='From skills/dev-tools/skills/user-manual/SKILL.md.')


# ---------------------------------------------------------- github-wiki-publish
def wiki():
    W = 1000
    BW, BH, CX = 320, 58, 300
    x0 = CX - BW // 2
    steps = [('Resolve the destination', ['wiki, pages, sources, what you allowed'])]
    b = [g(1, '<text class="e" x="40" y="36" font-size="12">GITHUB-WIKI-PUBLISH · ONE BOUNDED UPDATE</text>'
              + node(x0, 56, BW, BH, *steps[0]))]
    dy = 200
    b.append(g(2, f'<path class="c" d="M{CX} {56 + BH} V{dy - 50}" marker-end="url(#ar)"/>'
                  + diamond(CX, dy, 300, 96, 'Connector can write?', ['wiki pages and assets'])
                  + f'<path class="c" d="M{CX + 150} {dy} H{640 - 2}" marker-end="url(#ar)"/>' + label(CX + 162, dy - 8, 'yes')
                  + node(640, dy - 29, 320, BH, 'Publish through it', ['same mapping and checks'])))
    ys = [dy + 100, dy + 186, dy + 272, dy + 358]
    rows = [('Fresh clone of the wiki repo', ['find its real default branch']),
            ('Map pages and assets', ['rewrite links, keep unrelated pages']),
            ('Commit only those paths', ['review the full diff first']),
            ('Fetch, then push', ['never force-push'])]
    part = f'<path class="c" d="M{CX} {dy + 48} V{ys[0] - 2}" marker-end="url(#ar)"/>' + label(CX + 10, dy + 72, 'no')
    for i, ((name, subs), y) in enumerate(zip(rows, ys)):
        if i:
            part += f'<path class="c" d="M{CX} {ys[i - 1] + BH} V{y - 2}" marker-end="url(#ar)"/>'
        part += node(x0, y, BW, BH, name, subs, 'focal' if i == 3 else 'box')
    b.append(g(3, part))
    # rejected push: integrate once, else stop
    py = ys[3]
    b.append(g(4, f'<path class="lk" d="M{x0 + BW} {py + 20} H{640 - 2}" marker-end="url(#arl)"/>'
                  + label(x0 + BW + 12, py + 12, 'rejected')
                  + node(640, py - 8, 320, 66, 'Fetch and merge once', ['same conflict again: stop,', 'keep the clone, report']))
               + f'<path class="lk" d="M{800} {py - 8} V{ys[2] + BH // 2} H{x0 + BW + 2}" marker-end="url(#arl)"/>'
               + label(812, ys[2] + BH // 2 + 40, 'retry'))
    vy = [ys[3] + 100, ys[3] + 186]
    outs = [('Verify the remote commit', ['the push really landed']),
            ('Check the served page', ['signed-in browser: text, links, images'])]
    part = f'<path class="c" d="M{CX} {ys[3] + BH} V{vy[0] - 2}" marker-end="url(#ar)"/>'
    for i, ((name, subs), y) in enumerate(zip(outs, vy)):
        if i:
            part += f'<path class="c" d="M{CX} {vy[0] + BH} V{y - 2}" marker-end="url(#ar)"/>'
        part += node(x0, y, BW, BH, name, subs)
    part += label(40, vy[1] + BH + 34, 'You get the page URL, the published revision, what changed and anything it could not check.')
    b.append(g(5, part))
    H = vy[1] + BH + 56
    write('github-wiki-publish-flow', W, H, 'Publishing to a GitHub wiki',
          'The skill first resolves the destination wiki, the pages, the source files and what you allowed it to '
          'publish. It uses a connector when one can write wiki pages; otherwise it clones the wiki repository '
          'fresh and finds its real default branch. It maps pages and assets, rewrites links and leaves unrelated '
          'pages alone, commits only those paths after reviewing the diff, then fetches and pushes without ever '
          'force-pushing. A rejected push gets one fetch and merge; the same conflict again stops the run with the '
          'clone kept. It then checks the commit on the remote and, with a signed-in browser, the served page.',
          ''.join(b), 5, note='From skills/dev-tools/skills/github-wiki-publish/SKILL.md.')


# -------------------------------------------------------------- progress-report
def progress():
    W = 1000
    BW, BH = 280, 66
    b = [g(1, '<text class="e" x="40" y="36" font-size="12">PROGRESS-REPORT · A PROJECTION, NO AGENT KEEPS IT</text>')]
    ins = [('Plan or tasks.md', ['checkboxes you tick']),
           ('Host hooks', ['Claude Code or Codex events']),
           ('Facts you record', ['lane, block, decide, note'])]
    iy = [70, 170, 270]
    part = ''
    for (name, subs), y in zip(ins, iy):
        part += node(40, y, BW, BH, name, subs)
        part += f'<path class="c" d="M{40 + BW} {y + BH // 2} H{400} V{170 + BH // 2} H{460 - 2}" marker-end="url(#ar)"/>' if y != 170 else f'<path class="c" d="M{40 + BW} {y + BH // 2} H{460 - 2}" marker-end="url(#ar)"/>'
    b.append(g(2, part))
    b.append(g(3, node(460, 160, 220, 86, 'progress refresh', ['deterministic', 'same inputs, same report'], 'focal')))
    outs = [('Browser view', ['.view/index.html, live']),
            ('Markdown export', ['progress export --format md']),
            ('One-line status', ['progress status'])]
    part = ''
    for (name, subs), y in zip(outs, iy):
        part += node(720, y, 240, BH, name, subs)
        part += (f'<path class="c" d="M{680} {170 + BH // 2} H{700} V{y + BH // 2} H{720 - 2}" marker-end="url(#ar)"/>'
                 if y != 170 else f'<path class="c" d="M{680} {y + BH // 2} H{720 - 2}" marker-end="url(#ar)"/>')
    b.append(g(4, part))
    b.append(g(5, label(40, 380, 'Install the hooks once with progress hooks install --host claude (or codex). Without them, tasks are')
                  + label(40, 398, 'still tracked, but model, effort, context and child agents stay unknown. The report never writes your plan.')))
    write('progress-report-flow', W, 420, 'How a progress report stays current',
          'Three inputs feed the report: the plan file or tasks.md with its checkboxes, events from the Claude Code '
          'or Codex hooks, and the lane, blocker, decision and note facts you record. progress refresh projects them '
          'deterministically into a live browser view, a Markdown export and a one-line status. No agent is kept '
          'running to maintain it. Without the hooks, tasks are still tracked but model, effort, context and child '
          'agents stay unknown, and the report never writes the plan.',
          ''.join(b), 5, note='From skills/agent-tools/skills/progress-report/SKILL.md.')


product_map()
majlis()
delegate()
manual()
wiki()
progress()
