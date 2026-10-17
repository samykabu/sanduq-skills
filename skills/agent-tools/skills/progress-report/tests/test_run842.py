"""Phase 1 correctness patch, pinned on a frozen, sanitized copy of a real run (tests/fixtures/run-842).

The fixture is the evidence of one 23-task feature: 89 delegation attempts, 88 lane records, no host telemetry, a
checkpoint with no active claim, a pause that later stages superseded, and facts lanes that mirror stage runs. Before
the patch its projection had 77 lanes, no stage, a stale WP blocker and a lane that showed 13h 52m for 26 minutes of work."""
import copy
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import helpers
from sanduq_progress import model
from sanduq_progress.collect import workflow as wf



def parse(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


class Run842(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.report, cls.ctx = helpers.run842_report(cls.tmp.name)
        cls.ledger = json.loads((helpers.RUN842 / 'workflow' / 'delegations.json').read_text(encoding='utf-8'))['attempts']
        cls.lanes = {lane['id']: lane for lane in cls.report['lanes']}

    @classmethod
    def tearDownClass(cls):
        helpers.remove_tree(cls.tmp)

    def rebuild(self, now=helpers.RUN842_NOW, edit=None):
        """The projection again at another clock, optionally after `edit(feature_dir)` changed the copied evidence."""
        with tempfile.TemporaryDirectory() as base:
            ctx = helpers.run842_ctx(base)
            if edit:
                edit(ctx.feature_dir)
            return model.build(ctx, parse(now), 1, {})

    # ---- 1. stage ---------------------------------------------------------------------------------------------------
    def test_stage_comes_from_the_last_accepted_receipt_when_no_claim_is_active(self):
        stage = self.report['feature']['stage']
        self.assertEqual((stage['value'], stage['source'], stage['status']), ('pr', 'workflow-receipts', 'in-progress'))

    def test_an_active_claim_still_names_the_stage(self):
        def edit(feature_dir):
            path = feature_dir / 'workflow' / 'checkpoint.json'
            data = json.loads(path.read_text(encoding='utf-8'))
            data['active'] = {'stage': 'verify'}
            path.write_text(json.dumps(data), encoding='utf-8')
        self.assertEqual(self.rebuild(edit=edit)['feature']['stage'], {'value': 'verify', 'source': 'workflow-checkpoint'})

    def test_no_receipts_falls_back_to_a_terminal_status_and_otherwise_to_unknown(self):
        def edit(status):
            def run(feature_dir):
                path = feature_dir / 'workflow' / 'checkpoint.json'
                data = json.loads(path.read_text(encoding='utf-8'))
                data['receipts'], data['status'] = {}, status
                path.write_text(json.dumps(data), encoding='utf-8')
            return run
        self.assertEqual(self.rebuild(edit=edit('paused'))['feature']['stage'], {'value': 'paused', 'source': 'workflow-checkpoint'})
        self.assertIsNone(self.rebuild(edit=edit('in-progress'))['feature']['stage'])

    def test_rejected_or_undated_receipts_are_not_accepted(self):
        got = wf.accepted_receipts({'a': {'stage': 'a', 'outcome': 'passed', 'completed_at': '2026-01-01T00:00:00Z'},
                                    'b': {'stage': 'b', 'outcome': 'failed', 'completed_at': '2026-01-02T00:00:00Z'},
                                    'c': {'stage': 'c', 'outcome': 'passed'}})
        self.assertEqual([r['stage'] for r in got], ['a'])

    # ---- 2. stale pause ---------------------------------------------------------------------------------------------
    def test_a_pause_superseded_by_later_receipts_is_not_a_blocker(self):
        self.assertEqual(self.report['blockers'], [])
        self.assertEqual(self.report['summary']['blocked'], 0)
        paused = [e for e in self.report['events'] if e['kind'] == 'workflow']
        self.assertEqual(len(paused), 1)
        self.assertIn('resolved by a later accepted stage', paused[0]['text'])

    def test_a_pause_newer_than_every_receipt_is_still_a_blocker(self):
        def edit(feature_dir):
            path = feature_dir / 'workflow' / 'checkpoint.json'
            data = json.loads(path.read_text(encoding='utf-8'))
            data['pause']['at'], data['status'] = '2026-10-17T13:59:00+00:00', 'paused'  # Workflow leaves `pause` behind once it claims again
            path.write_text(json.dumps(data), encoding='utf-8')
        blockers = self.rebuild(edit=edit)['blockers']
        self.assertEqual([b['id'] for b in blockers], ['WP'])

    # ---- 3. durations -----------------------------------------------------------------------------------------------
    def test_a_reused_lane_shows_its_own_run_not_the_gap_since_it_was_first_created(self):
        lane = self.lanes['L1']
        self.assertEqual(lane['elapsed']['source'], 'delegation-ledger')
        self.assertNotEqual(lane['elapsed']['value'], 49971)
        self.assertLess(lane['elapsed']['value'], 3600)  # the T010 run: 22:40 to 23:06
        self.assertEqual(len(lane['attempts']), 1)

    def test_a_multi_attempt_lane_sums_attempt_durations_instead_of_spanning_the_gaps(self):
        by_identity = {}
        for a in self.ledger:
            by_identity.setdefault(a['identity'], []).append(a)
        checked = 0
        for lane in self.report['lanes']:
            runs = [a for a in self.ledger if a['run_id'] in {x['run_id'] for x in lane['attempts']}]
            if len(runs) < 2:
                continue
            total = sum(int((parse(a['ended_at']) - parse(a['started_at'])).total_seconds()) for a in runs)
            span = int((max(parse(a['ended_at']) for a in runs) - min(parse(a['started_at']) for a in runs)).total_seconds())
            self.assertEqual(lane['elapsed']['value'], total, lane['id'])
            self.assertLessEqual(lane['elapsed']['value'], span, lane['id'])
            checked += 1
        self.assertGreater(checked, 5)

    def test_finished_lanes_do_not_grow_with_the_clock(self):
        later = {l['id']: l for l in self.rebuild(now='2026-10-19T09:00:00Z')['lanes']}
        for lane_id, lane in self.lanes.items():
            if lane['status'] == 'done' or lane['origin'] != 'facts':
                self.assertEqual(later[lane_id]['elapsed'], {**lane['elapsed'], 'observed_at': later[lane_id]['elapsed']['observed_at']}, lane_id)

    def test_a_closed_facts_lane_with_no_runs_is_frozen_at_its_close_record(self):
        lane = self.lanes['L37']  # opened 04:52:10, closed 05:26:01
        self.assertEqual(lane['elapsed']['value'], 2031)

    # ---- 4. duplicate lanes -----------------------------------------------------------------------------------------
    def test_lane_count_drops_and_no_attempt_is_lost_or_duplicated(self):
        # Exact on the frozen fixture: 48 lanes (the baseline was 77). Timing alone no longer links a lane to a run, so
        # two facts lanes stay beside their runs; a deliberate change to linking should change this number on purpose.
        self.assertEqual(len(self.report['lanes']), 48)
        shown = [a['run_id'] for lane in self.report['lanes'] for a in lane['attempts']]
        self.assertEqual(len(shown), len(self.ledger))
        self.assertEqual(sorted(shown), sorted(a['run_id'] for a in self.ledger))

    def test_lanes_with_something_to_read_fit_the_budget(self):
        busy = [l for l in self.report['lanes'] if l['attempts'] or any(l['tasks'][k] for k in ('active', 'waiting', 'blocked', 'done'))]
        self.assertEqual(len(busy), 39)  # exact on the frozen fixture; a new lane with something to read should be a decision

    def test_stage_mirror_lanes_fold_into_one_lane_per_stage(self):
        clarify = self.lanes['L3']  # L3, L4, L6, L9 and L12 all described clarify runs
        self.assertEqual(clarify['owner'], 'specs/842-versioned-workflow-graphs/stage:clarify')
        self.assertEqual(len(clarify['attempts']), 5)
        for gone in ('L4', 'L6', 'L9', 'L12'):
            self.assertNotIn(gone, self.lanes)

    def test_a_blocker_on_a_folded_lane_id_resolves_to_the_surviving_lane(self):
        def edit(feature_dir):
            line = json.dumps({'v': 1, 'ts': '2026-10-17T13:00:00Z', 'kind': 'block', 'id': 'B9', 'actor': 'agent:coordinator', 'source': 'cli',
                               'target': 'L4', 'by': {'type': 'external', 'ref': 'waiting on owner'}, 'state': 'open', 'resolved_at': None})
            with open(feature_dir / 'progress' / 'facts.jsonl', 'a', encoding='utf-8') as stream:
                stream.write(line + '\n')
        report = self.rebuild(edit=edit)
        self.assertEqual([(b['id'], b['target']) for b in report['blockers']], [('B9', 'L3')])

    def test_a_lane_owned_by_a_run_the_ledger_does_not_hold_is_never_merged_by_time(self):
        held = {a['run_id'] for a in self.ledger}
        for lane_id in ('L33', 'L34', 'L35', 'L36'):  # tooling runs that merely overlapped a stage in time
            lane = self.lanes[lane_id]
            self.assertNotIn(lane['owner'], held)
            self.assertEqual(lane['origin'], 'facts')
            self.assertEqual(lane['attempts'], [], lane_id)

    def test_two_stages_in_one_window_are_not_guessed(self):
        lane = self.lanes['L19']  # execution-orchestrator spans an execute run and a plan revalidation
        self.assertEqual(lane['attempts'], [])

    def test_the_wide_lane_does_not_steal_runs_from_tighter_ones(self):
        runs = {a['run_id']: a['identity'] for a in self.ledger}
        for lane in self.report['lanes']:
            identities = {runs[a['run_id']] for a in lane['attempts']}
            if lane['origin'] == 'workflow-delegation' or lane['owner'] in identities:
                self.assertLessEqual(len(identities), 1, lane['id'])

    # ---- 5/6. data the UI needs -------------------------------------------------------------------------------------
    def test_events_keep_stage_failure_and_workflow_lines_inside_a_bound(self):
        kinds = {}
        for event in self.report['events']:
            kinds[event['kind']] = kinds.get(event['kind'], 0) + 1
        self.assertEqual(kinds['failure'], sum(1 for a in self.ledger if a['status'] in ('failed', 'abandoned') and a.get('ended_at')))
        self.assertEqual(kinds['stage'], 16)  # one per accepted receipt
        self.assertLessEqual(len(self.report['events']), model.KEEP_LIMIT + model.OTHER_LIMIT + model.NOTE_LIMIT)
        self.assertLessEqual(kinds['delegation'], model.OTHER_LIMIT)
        self.assertEqual([e['at'] for e in self.report['events']], sorted(e['at'] for e in self.report['events']))

    def test_orchestrator_telemetry_is_reported_missing_not_invented(self):
        orchestrator = self.report['orchestrator']
        self.assertIsNone(orchestrator['host'])
        self.assertIsNone(orchestrator['model']['value'])
        self.assertFalse(self.report['collection']['automatic'])

    def test_workflow_decisions_are_empty_in_the_fixture(self):
        self.assertEqual(self.report['decisions'], {'pending': [], 'made': []})

    def test_the_projection_keeps_its_schema(self):
        self.assertEqual(self.report['schema'], 'sanduq.progress.v2')
        for key in ('feature', 'orchestrator', 'lanes', 'unassigned_tasks', 'tasks', 'decisions', 'blockers', 'events', 'summary', 'collection'):
            self.assertIn(key, self.report)


if __name__ == '__main__':
    unittest.main()
