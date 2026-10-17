"""Clarification records: `workflow/clarifications.json`, written by Scope after a published clarification round
(producer contract, version 1). Progress renders from this file and makes no GitHub calls.

    {"v": 1, "items": [{source_id, revision, question, options, answer: {kind, value}|null, state, url, editor|null,
                        observed_at, answered_at|null, applied: {at, evidence}|null, evidence: [..]}]}

`state` is pending, conflict, answered, applied, waived, superseded or withdrawn. `answer.kind` is single, multiple or
text. `editor` and `answered_at` are null when the evidence does not record them; Progress never fills them in. Several
items may share a `source_id` (revisions): the highest `revision` is current and the others are shown as superseded."""
from pathlib import Path

from ..util import clean, read_json

STATES = ('pending', 'conflict', 'answered', 'applied', 'waived', 'superseded', 'withdrawn')
KINDS = ('single', 'multiple', 'text')


def _str(value, cap):
    return clean(value, cap) if isinstance(value, str) and value.strip() else None


def _answer(value):
    if not isinstance(value, dict) or value.get('kind') not in KINDS:
        return None
    raw = value.get('value')
    if value['kind'] == 'multiple':
        items = [clean(x, 200) for x in raw if isinstance(x, str) and x.strip()] if isinstance(raw, list) else []
        return {'kind': 'multiple', 'value': items} if items else None
    text = _str(raw, 400)
    return {'kind': value['kind'], 'value': text} if text else None


def _item(item):
    if not isinstance(item, dict) or not _str(item.get('source_id'), 80) or item.get('state') not in STATES:
        return None
    revision = item.get('revision')
    applied = item.get('applied') if isinstance(item.get('applied'), dict) else None
    url = item.get('url')
    options = item.get('options')
    evidence = item.get('evidence')
    return {'source_id': _str(item['source_id'], 80),
            'revision': revision if isinstance(revision, int) and not isinstance(revision, bool) else 1,
            'question': _str(item.get('question'), 200),
            'options': [clean(o, 200) for o in options[:20] if isinstance(o, str)] if isinstance(options, list) else [],
            'answer': _answer(item.get('answer')), 'state': item['state'],
            'url': url if isinstance(url, str) and url.startswith('https://') else None,
            'editor': _str(item.get('editor'), 80), 'observed_at': _str(item.get('observed_at'), 40),
            'answered_at': _str(item.get('answered_at'), 40),
            'applied': {'at': _str(applied.get('at'), 40),
                        'evidence': [clean(e, 200) for e in (applied.get('evidence') or [])[:10] if isinstance(e, str)]
                        if isinstance(applied.get('evidence'), list) else []} if applied else None,
            'evidence': [clean(e, 200) for e in evidence[:10] if isinstance(e, str)] if isinstance(evidence, list) else []}


def collect(feature_dir):
    """{'state': absent|available|unsupported|invalid, 'items': [...], 'skipped': n}."""
    path = Path(feature_dir) / 'workflow' / 'clarifications.json'
    if not path.is_file():
        return {'state': 'absent', 'items': [], 'skipped': 0}
    data = read_json(path, None)
    if not isinstance(data, dict) or not isinstance(data.get('items'), list):
        return {'state': 'invalid', 'items': [], 'skipped': 0}
    if data.get('v') != 1:
        return {'state': 'unsupported', 'items': [], 'skipped': 0}
    items = [x for x in map(_item, data['items']) if x]
    return {'state': 'available', 'items': items, 'skipped': len(data['items']) - len(items)}
