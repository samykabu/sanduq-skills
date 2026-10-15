"""Plan collector: any Markdown checklist is a task list. The plan file is read, never written; whoever owns the plan
checks items off.

Recognised: `- [ ] Title`, `- [x] T001 [P] Title (depends on T000, P002)`, `(after T001)`. A level-2 or deeper heading
names the phase of the items below it; the first level-1 heading is the title. Fenced blocks and inline code spans are
ignored, so ids quoted in prose never create tasks or edges.

Ids. An item that starts with an id (`T001`, `US3`, `**T001**:`) keeps it. Every other item gets an auto id `P001`,
`P002`, ... The map from item text to auto id is stored in the tracked `plan.json` of the report and applied in this order,
so ids stay stable as the plan is edited:

1. an item whose normalised text equals a stored one reuses its id (first unused match, in plan order);
2. an item whose text is at least 60 percent similar to a stored, still unmatched one reuses that id (best match first);
3. anything else takes the next number. Numbers are never reused, even after an item is deleted.

Reordering therefore changes nothing, and a small rewording keeps the id. Rewording an item beyond recognition, or
deleting it and adding another, gives a new id. Checking an item off never changes its id.
"""
import difflib
import re
from pathlib import Path

from ..paths import RESERVED_ID, TASK_REF, plan_info, plan_source
from ..util import clean, read_json

ITEM = re.compile(r'^\s*[-*+]\s+\[([ xX])\]\s+(.*)$')
HEADING = re.compile(r'^(#{1,6})\s+(.*?)\s*#*\s*$')
FENCE = re.compile(r'^\s*(```|~~~)')
SPAN = re.compile(r'(`+)(.+?)\1')
LEAD_ID = re.compile(r'^(?:\*\*|__)?(' + TASK_REF + r')(?:\*\*|__)?(?:[:.)]|\s|$)\s*(.*)$')
DEPENDS = re.compile(r'\((?:depends on|after)\s+([^)]*)\)', re.I)
PARALLEL = re.compile(r'(?<![\w`])\[P\](?![\w`])')
REF = re.compile(r'(?<![\w-])' + TASK_REF + r'(?![\w-])')
SIMILAR = 0.6
MAX_BYTES = 1 << 20


def _blank_spans(text):
    return SPAN.sub(lambda m: ' ' * len(m.group(0)), text)


def _key(text):
    """Normalised item text: what identifies an item across edits (case, spacing and markdown emphasis are ignored)."""
    text = re.sub(r'[*_`~]', '', text.lower())
    return re.sub(r'\s+', ' ', text).strip()[:120]


def _number(ident):
    match = re.fullmatch(r'P(\d+)', str(ident))
    return int(match.group(1)) if match else 0


def parse(text):
    """Return {'title', 'items'}: items in plan order with `id` (explicit ids only; auto items carry None)."""
    items, seen, phase, title, fence = [], set(), None, None, None
    for line in text.splitlines():
        marker = FENCE.match(line)
        if marker:
            fence = None if fence == marker.group(1) else (fence or marker.group(1))
            continue
        if fence:
            continue
        heading = HEADING.match(line)
        if heading:
            if len(heading.group(1)) == 1:
                title = title or clean(heading.group(2), 160)
            else:
                phase = clean(heading.group(2), 120)
            continue
        found = ITEM.match(line)
        if not found:
            continue
        body = found.group(2)
        lead = LEAD_ID.match(body)
        ident = lead.group(1).upper() if lead and not RESERVED_ID.fullmatch(lead.group(1).upper()) else None
        if ident and ident in seen:
            continue
        if ident:
            seen.add(ident)
            body = lead.group(2)
        bare = _blank_spans(body)
        refs = []
        for match in DEPENDS.finditer(bare):
            refs += [r.upper() for r in REF.findall(match.group(1)) if r.upper() not in refs]
        shown = re.sub(r'\(\s*(?:depends on|after)\s+[^)]*\)', '', body, flags=re.I)
        shown = clean(PARALLEL.sub('', shown), 160)
        items.append({'id': ident, 'title': shown, 'phase': phase or '', 'done': found.group(1) != ' ',
                      'parallel': bool(PARALLEL.search(bare)), 'refs': refs, 'key': _key(shown)})
    return {'title': title, 'items': items}


def assign(items, stored, floor=0):
    """Give every auto item its id. `stored` is the previous [{id, key}] map; returns (ids list, next number)."""
    explicit = {i['id'] for i in items if i['id']}
    autos = [i for i in items if not i['id']]
    previous = [dict(s) for s in stored if isinstance(s, dict) and re.fullmatch(r'P\d+', str(s.get('id'))) and s['id'] not in explicit]
    highest = max([floor, *(_number(s['id']) for s in previous), *(_number(e) for e in explicit)] or [0])
    taken = {}
    free = list(range(len(previous)))
    for index, item in enumerate(autos):  # 1. exact text
        for slot in free:
            if previous[slot].get('key') == item['key']:
                taken[index] = previous[slot]['id']
                free.remove(slot)
                break
    pairs = []
    for index, item in enumerate(autos):  # 2. similar text, best first
        if index in taken:
            continue
        for slot in free:
            ratio = difflib.SequenceMatcher(None, item['key'], str(previous[slot].get('key') or '')).ratio()
            if ratio >= SIMILAR:
                pairs.append((-ratio, abs(index - slot), index, slot))
    for _, _, index, slot in sorted(pairs):
        if index not in taken and slot in free:
            taken[index] = previous[slot]['id']
            free.remove(slot)
    for index, item in enumerate(autos):  # 3. new numbers
        if index not in taken:
            highest += 1
            while f'P{highest:03d}' in explicit:
                highest += 1
            taken[index] = f'P{highest:03d}'
    for index, item in enumerate(autos):
        item['id'] = taken[index]
    return [{'id': i['id'], 'key': i['key']} for i in autos], highest


def _read(ctx):
    source = plan_source(ctx.root, ctx.feature)
    if source is None:
        return None
    try:
        with open(source, 'rb') as stream:
            return stream.read(MAX_BYTES).decode('utf-8', errors='replace')
    except OSError:
        return None


def collect(ctx):
    """Tasks of a plan in the shape the projection expects, plus the id map to persist."""
    info = plan_info(ctx.root, ctx.feature)
    text = _read(ctx)
    if text is None:
        return {'title': None, 'tasks': [], 'ids': info.get('ids') or [], 'next': info.get('next') or 0, 'missing': True}
    parsed = parse(text)
    ids, highest = assign(parsed['items'], info.get('ids') or [], int(info.get('next') or 0))
    known = {i['id'] for i in parsed['items']}
    tasks = []
    for item in parsed['items']:
        depends = [r for r in item['refs'] if r in known and r != item['id']]
        tasks.append({'id': item['id'], 'title': item['title'], 'phase': item['phase'], 'done': item['done'],
                      'parallel': item['parallel'], 'depends_on': depends})
    return {'title': parsed['title'], 'tasks': tasks, 'ids': ids, 'next': highest, 'missing': False}


def persist(ctx):
    """Store the id map so the next edit keeps ids stable. Caller holds the report lock. Writes only on change."""
    from ..util import write_json
    info = plan_info(ctx.root, ctx.feature)
    if not info:
        return False
    got = collect(ctx)
    if got['missing']:
        return False
    if info.get('ids') == got['ids'] and info.get('next') == got['next']:
        return False
    info['ids'], info['next'] = got['ids'], got['next']
    write_json(ctx.plan_file, info)
    return True
