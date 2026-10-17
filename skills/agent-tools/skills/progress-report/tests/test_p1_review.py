"""Phase 1 review cycle 1: regressions for the findings (A = Astra, F = Fable)."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import helpers
from helpers import Ctx
from sanduq_progress import model

NOW = helpers.RUN842_NOW


def parse(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def rebuild(edit, now=NOW):
    with tempfile.TemporaryDirectory() as base:
        ctx = helpers.run842_ctx(base)
        edit(ctx.feature_dir)
        return model.build(ctx, parse(now), 1, {})


def edit_json(feature_dir, name, change):
    path = feature_dir / 'workflow' / name
    data = json.loads(path.read_text(encoding='utf-8'))
    change(data)
    path.write_text(json.dumps(data), encoding='utf-8')


def ledger():
    return json.loads((helpers.RUN842 / 'workflow' / 'delegations.json').read_text(encoding='utf-8'))['attempts']


def fact_lane(lane_id, owner, since, ended=None, requested=None, tasks=()):
    base = {'v': 1, 'kind': 'lane', 'id': lane_id, 'actor': 'agent:coordinator', 'source': 'cli', 'tasks': list(tasks), 'owner': owner,
            'label': lane_id, 'requested': requested or {}}
    rows = [dict(base, ts=since, state='open')]
    if ended:
        rows.append(dict(base, ts=ended, state='closed'))
    return rows


def attempt(identity, run_id, started, ended=None, status=None, harness='codex', model_name='gpt-6-astra'):
    row = {'identity': identity, 'run_id': run_id, 'status': status or ('successful' if ended else 'running'), 'started_at': started,
           'requested_harness': harness, 'requested_model': model_name}
    if ended:
        row['ended_at'] = ended
    return row


def synth(base, facts=(), attempts=(), checkpoint=None):
    """A tiny Spec Kit project with the given lane facts and delegation attempts."""
    base = Path(base)
    (base / '.specify').mkdir(parents=True, exist_ok=True)
    feature = base / 'specs' / '9-demo'
    (feature / 'workflow').mkdir(parents=True, exist_ok=True)
    (feature / 'progress').mkdir(parents=True, exist_ok=True)
    (feature / 'tasks.md').write_text('- [ ] T001 first\n', encoding='utf-8')
    (feature / 'workflow' / 'delegations.json').write_text(json.dumps({'attempts': list(attempts)}), encoding='utf-8')
    if checkpoint is not None:
        (feature / 'workflow' / 'checkpoint.json').write_text(json.dumps(checkpoint), encoding='utf-8')
    (feature / 'progress' / 'facts.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in facts), encoding='utf-8')
    return Ctx(base, 'specs/9-demo')


STAGE = 'specs/9-demo/stage:plan'
REQ = {'harness': 'codex', 'model': 'gpt-6-astra'}


class Folded(unittest.TestCase):
    def test_a1_a_closed_folded_lane_with_a_newer_running_attempt_is_active(self):
        template = next(a for a in ledger() if a['identity'].endswith('/stage:clarify'))

        def edit(feature_dir):
            def change(data):
                data['attempts'].append(dict(template, run_id='codex-20261017135900-aaaa01', status='running', started_at='2026-10-17T13:59:00+00:00',
                                             ended_at=None, accepted_at=None))
            edit_json(feature_dir, 'delegations.json', change)
        report = rebuild(edit)
        lane = next(l for l in report['lanes'] if l['owner'] == template['identity'])
        self.assertEqual(lane['status'], 'active')
        self.assertGreaterEqual(report['summary']['lanes_active'], 1)

    def test_a2_retired_worker_lane_ids_resolve_to_the_surviving_lane(self):
        base = rebuild(lambda d: None)
        shown = {l['id'] for l in base['lanes']}
        rows = ledger()
        order = list(dict.fromkeys(a['identity'] for a in sorted(rows, key=lambda a: (a.get('started_at') or '', str(a['run_id'])))))
        retired = [(n, i) for n, i in enumerate(order, 1) if f'W{n}' not in shown]
        self.assertTrue(retired, 'the fixture folds some W lanes away')
        number, identity = retired[0]
        runs = {x['run_id'] for x in rows if x['identity'] == identity}
        owner = next(l['id'] for l in base['lanes'] if runs & {a['run_id'] for a in l['attempts']})

        def edit(feature_dir):
            line = {'v': 1, 'ts': '2026-10-17T13:00:00Z', 'kind': 'block', 'id': 'B9', 'actor': 'agent:coordinator', 'source': 'cli',
                    'target': f'W{number}', 'by': {'type': 'lane', 'ref': f'W{number}'}, 'state': 'open', 'resolved_at': None}
            with open(feature_dir / 'progress' / 'facts.jsonl', 'a', encoding='utf-8') as stream:
                stream.write(json.dumps(line) + '\n')
        blocker = next(b for b in rebuild(edit)['blockers'] if b['id'] == 'B9')
        self.assertEqual((blocker['target'], blocker['by']['ref']), (owner, owner))


class Closure(unittest.TestCase):
    """A closed facts lane reads done unless one of its attempts was still active after the close (10:00 open, 13:10 closed)."""
    RUN = 'codex-20261017130500-aaaa'
    IDENTITY = 'specs/9-demo/stage:implement'

    def lane(self, owner, started, ended, status, now='2026-10-17T14:00:00Z'):
        facts = fact_lane('L1', owner, '2026-10-17T13:00:00Z', '2026-10-17T13:10:00Z', REQ)
        attempts = [attempt(self.IDENTITY, self.RUN, started, ended, status=status)]
        with tempfile.TemporaryDirectory() as base:
            report = model.build(synth(base, facts, attempts), parse(now), 1, {})
        lane = next(l for l in report['lanes'] if l['id'] == 'L1')
        self.assertEqual(len(lane['attempts']), 1, 'the attempt is linked to the closed lane')
        return lane['status'], report['summary']['lanes_active']

    def each_owner(self):
        return (('run id', self.RUN), ('identity', self.IDENTITY))

    def test_c3_an_attempt_that_ended_before_the_close_leaves_the_lane_done(self):
        for name, owner in self.each_owner():
            with self.subTest(owner=name):
                self.assertEqual(self.lane(owner, '2026-10-17T13:05:00+00:00', '2026-10-17T13:09:00+00:00', 'failed')[0], 'done')

    def test_c3_a_lane_closed_while_its_run_is_still_running_reads_active(self):
        for name, owner in self.each_owner():
            with self.subTest(owner=name):
                status, active = self.lane(owner, '2026-10-17T13:05:00+00:00', None, 'running')
                self.assertEqual(status, 'active')
                self.assertGreaterEqual(active, 1)

    def test_c3_an_attempt_started_before_the_close_and_failed_after_it_reads_failed(self):
        for name, owner in self.each_owner():
            with self.subTest(owner=name):
                self.assertEqual(self.lane(owner, '2026-10-17T13:05:00+00:00', '2026-10-17T13:20:00+00:00', 'failed')[0], 'failed')

    def test_c3_an_attempt_started_after_the_close_and_unaccepted_is_not_done(self):
        for name, owner in self.each_owner():
            with self.subTest(owner=name):
                self.assertNotEqual(self.lane(owner, '2026-10-17T13:15:00+00:00', '2026-10-17T13:20:00+00:00', 'successful')[0], 'done')

    def test_c3_an_attempt_started_after_the_close_and_blocked_is_blocked(self):
        for name, owner in self.each_owner():
            with self.subTest(owner=name):
                self.assertEqual(self.lane(owner, '2026-10-17T13:15:00+00:00', '2026-10-17T13:20:00+00:00', 'blocked')[0], 'blocked')


class Linking(unittest.TestCase):
    def lanes(self, facts, attempts, now):
        with tempfile.TemporaryDirectory() as base:
            return model.build(synth(base, facts, attempts), parse(now), 1, {})

    def test_c2_identical_windows_and_requests_never_link_on_timing(self):
        facts = (fact_lane('L1', 'tool-a', '2026-10-17T13:00:00Z', '2026-10-17T13:10:00Z', REQ)
                 + fact_lane('L2', 'tool-b', '2026-10-17T13:00:00Z', '2026-10-17T13:10:00Z', REQ))
        report = self.lanes(facts, [attempt(STAGE, 'codex-20261017130500-aaaa', '2026-10-17T13:05:00+00:00', '2026-10-17T13:06:00+00:00')], '2026-10-17T14:00:00Z')
        self.assertEqual(sorted(l['id'] for l in report['lanes']), ['L1', 'L2', 'W1'])

    def test_c2_one_candidate_with_a_matching_request_does_not_merge_either(self):
        facts = fact_lane('L1', 'tooling', '2026-10-17T13:00:00Z', '2026-10-17T13:10:00Z', REQ)
        report = self.lanes(facts, [attempt(STAGE, 'codex-20261017130500-aaaa', '2026-10-17T13:05:00+00:00', '2026-10-17T13:06:00+00:00')], '2026-10-17T14:00:00Z')
        self.assertEqual([(l['id'], len(l['attempts'])) for l in report['lanes']], [('L1', 0), ('W1', 1)])

    def test_c2_an_open_lane_and_its_running_host_run_stay_separate(self):
        facts = fact_lane('L40', 'tooling', '2026-10-17T13:00:00Z', None, REQ)
        report = self.lanes(facts, [attempt(STAGE, 'codex-20261017130010-aaaa', '2026-10-17T13:00:10+00:00', status='successful', ended='2026-10-17T13:00:40+00:00')], '2026-10-17T13:01:00Z')
        self.assertEqual({l['id']: l['status'] for l in report['lanes']}['L40'], 'active')  # the unrelated run did not turn it waiting

    def test_c2_a_lane_owned_by_the_run_id_links_it(self):
        facts = fact_lane('L1', 'codex-20261017130500-aaaa', '2026-10-17T13:00:00Z', '2026-10-17T13:10:00Z', REQ)
        report = self.lanes(facts, [attempt(STAGE, 'codex-20261017130500-aaaa', '2026-10-17T13:05:00+00:00', '2026-10-17T13:06:00+00:00')], '2026-10-17T14:00:00Z')
        self.assertEqual([(l['id'], len(l['attempts'])) for l in report['lanes']], [('L1', 1)])


class Pause(unittest.TestCase):
    def pause_edit(self, status, claimed=None, at='2026-10-17T13:59:00+00:00'):
        def edit(feature_dir):
            def change(data):
                data['pause']['at'], data['status'] = at, status
                data['active'] = {'stage': 'verify', 'claimed_at': claimed} if claimed else None
            edit_json(feature_dir, 'checkpoint.json', change)
        return edit

    def test_f2_a_pause_stays_a_blocker_while_the_checkpoint_is_paused(self):
        self.assertEqual([b['id'] for b in rebuild(self.pause_edit('paused'))['blockers']], ['WP'])

    def test_f2_a_new_claim_supersedes_the_pause(self):
        self.assertEqual(rebuild(self.pause_edit('paused', claimed='2026-10-17T13:59:30+00:00'))['blockers'], [])

    def test_f2_an_older_claim_does_not(self):
        self.assertEqual([b['id'] for b in rebuild(self.pause_edit('paused', claimed='2026-10-17T13:58:00+00:00'))['blockers']], ['WP'])

    def test_c2_pause_history_names_the_real_reason_not_an_accepted_stage(self):
        text = lambda report: next(e['text'] for e in report['events'] if e['kind'] == 'workflow')
        claimed = text(rebuild(self.pause_edit('paused', claimed='2026-10-17T13:59:30+00:00')))
        self.assertIn('superseded: newer claim', claimed)
        self.assertNotIn('accepted', claimed)
        self.assertIn('superseded: status is in-progress', text(rebuild(self.pause_edit('in-progress'))))

    def test_f2_a_status_that_is_no_longer_paused_supersedes_the_pause(self):
        self.assertEqual(rebuild(self.pause_edit('in-progress'))['blockers'], [])


class Events(unittest.TestCase):
    def test_f3_notes_reach_events_within_their_own_bound(self):
        report = rebuild(lambda d: None)
        kinds = {}
        for event in report['events']:
            kinds[event['kind']] = kinds.get(event['kind'], 0) + 1
        self.assertEqual(kinds['note'], model.NOTE_LIMIT)
        self.assertEqual(kinds['stage'], 16)  # the notes did not push stage acceptances out
        self.assertLessEqual(len(report['events']), model.KEEP_LIMIT + model.OTHER_LIMIT + model.NOTE_LIMIT)


class Source(unittest.TestCase):
    """UI wording that needs no browser."""
    JS = (Path(helpers.__file__).resolve().parent.parent / 'assets' / 'ui' / 'blocks.js').read_text(encoding='utf-8')

    def test_f9_missing_telemetry_wording_is_host_neutral(self):
        self.assertNotIn("'No host hook data \\u2014 Codex worktree hooks not active?'", self.JS)
        self.assertIn("o.host === 'codex'", self.JS)

    def test_a5_board_and_quiet_summaries_carry_stable_ids(self):
        self.assertIn("'data-k': 'quiet-lanes'", self.JS)
        self.assertIn("'data-k': 'board-' + key", self.JS)


if __name__ == '__main__':
    unittest.main()
