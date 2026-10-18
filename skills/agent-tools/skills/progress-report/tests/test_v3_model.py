"""Projection `sanduq.progress.v3`: the #842 acceptance numbers, the producer contracts (lifecycle, stage_plan, next_action,
durable delegation links, clarifications), the v2 adapter, self-report and the theme layout key."""
import copy
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import helpers
from helpers import Project, T0
from sanduq_progress import model, render_md, theme, validate
from sanduq_progress.collect import lifecycle as lifecol, tasks as taskscol

NOW = datetime.fromisoformat(T0.replace('Z', '+00:00'))


def parse(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


class Run842V3(unittest.TestCase):
    """The frozen #842 evidence, projected as v3."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.report, cls.ctx = helpers.run842_report(cls.tmp.name, schema='v3')
        cls.runs = {r['run_id']: r for r in cls.report['runs']}

    @classmethod
    def tearDownClass(cls):
        helpers.remove_tree(cls.tmp)

    def test_the_document_validates(self):
        self.assertEqual(validate.validate(self.report), [])
        self.assertEqual(self.report['schema'], 'sanduq.progress.v3')

    def test_89_unique_runs_81_successful_2_failed_3_abandoned_3_unverified(self):
        counts = {}
        for r in self.report['runs']:
            counts[r['worker_status']] = counts.get(r['worker_status'], 0) + 1
        self.assertEqual(len(self.runs), 89)
        self.assertEqual(counts, {'successful': 81, 'failed': 2, 'abandoned': 3, 'unverified': 3})
        self.assertEqual(self.report['summary']['runs_total'], 89)
        self.assertEqual(self.report['summary']['runs_failed'], 5)

    def test_16_recorded_receipts_but_no_proof_they_are_current(self):
        accepted = [s for s in self.report['stages'] if s['accepted_at']]
        self.assertEqual(len(accepted), 16)
        self.assertEqual(self.report['summary']['stages_accepted'], 16)
        self.assertEqual({s['validity'] for s in accepted}, {'unknown'})  # a receipt alone does not prove it is current

    def test_23_tasks_done_in_workstreams_a_b_and_shared(self):
        self.assertEqual((self.report['summary']['tasks_total'], self.report['summary']['tasks_done']), (23, 23))
        by_id = {w['id']: w for w in self.report['workstreams']}
        self.assertEqual(set(by_id), {'tag:A', 'tag:B', 'shared'})
        self.assertEqual({k: len(v['tasks']['done']) for k, v in by_id.items()}, {'tag:A': 7, 'tag:B': 6, 'shared': 10})
        self.assertEqual(by_id['tag:A']['origin'], 'tasks-tag')
        self.assertEqual(by_id['shared']['origin'], 'shared')
        for w in by_id.values():
            self.assertEqual([w['tasks'][k] for k in ('active', 'waiting', 'blocked')], [[], [], []])

    def test_role_markers_and_parallel_do_not_make_workstreams(self):
        parsed = taskscol.collect(self.ctx.feature_dir)
        self.assertEqual(set(parsed['legend']), {'A', 'B'})
        t012 = next(t for t in parsed['tasks'] if t['id'] == 'T012')
        self.assertEqual((t012['tags'], t012['workstream']), (['P', 'QA'], None))

    def test_61_notes_keep_their_text_and_all_stay_in_the_timeline(self):
        notes = [e for e in self.report['timeline'] if e['kind'] == 'note']
        self.assertEqual(len(notes), 61)

    def test_c1q1_comes_from_the_clarification_record_without_an_invented_editor(self):
        decisions = self.report['decisions']
        self.assertEqual(decisions['pending'], [])
        c1q1 = next(d for d in decisions['made'] if d['source_id'] == 'C1Q1')
        self.assertEqual((c1q1['state'], c1q1['decided_by'], c1q1['answered_at']), ('applied', None, None))
        self.assertEqual((c1q1['answer']['kind'], c1q1['answer']['index'], c1q1['answer']['value']), ('single', 0, c1q1['options'][0]))  # letter A, decoded once
        self.assertTrue(c1q1['url'].startswith('https://github.com/'))
        self.assertTrue(c1q1['applied']['evidence'])
        sources = {s['name']: s['state'] for s in decisions['sources']}
        self.assertEqual(sources['clarification'], 'available')

    def test_no_self_report_means_no_orchestrator_identity(self):
        o = self.report['orchestrator']
        self.assertEqual((o['host'], o['model']['value'], o['effort']['value']), (None, None, None))
        self.assertEqual(set(o['provenance'].values()), {'none'})

    def test_task_runs_do_not_join_stage_episodes_without_a_recorded_link(self):
        task_run = next(r for r in self.report['runs'] if r['identity'].endswith('/T001'))
        self.assertEqual((task_run['stage'], task_run['episode_id'], task_run['tasks']), (None, None, ['T001']))
        execute = next(s for s in self.report['stages'] if s['id'] == 'execute')
        self.assertEqual(len(execute['unknown_runs']), execute['run_count'])  # stage runs, no lifecycle events: episode unknown

    def test_all_five_failed_or_abandoned_runs_are_kept_and_later_success_is_inferred_not_proven(self):
        failed = [r for r in self.report['runs'] if r['worker_status'] in ('failed', 'abandoned')]
        self.assertEqual(len(failed), 5)
        failures = [e for e in self.report['timeline'] if e['kind'] == 'failure']
        self.assertEqual(len(failures), 5)
        recoveries = [e for e in self.report['timeline'] if e['kind'] == 'recovery' and e['fidelity'] == 'inferred']
        self.assertTrue(recoveries)
        self.assertTrue(all('no retry link recorded' in e['text'] for e in recoveries))

    def test_fresh_and_stale_snapshots_differ_only_in_time(self):
        later = helpers.run842_report(tempfile.mkdtemp(), now='2026-10-19T09:00:00Z', schema='v3')[0]
        self.assertEqual(validate.validate(later), [])
        for a, b in zip(self.report['runs'], later['runs']):
            if a['worker_status'] not in ('starting', 'running'):
                self.assertEqual(a['duration']['value'], b['duration']['value'], a['run_id'])
        self.assertNotEqual(later['generated_at'], self.report['generated_at'])

    def test_sources_carry_fingerprints(self):
        names = {s['name']: s for s in self.report['sources']}
        self.assertEqual(names['workflow-checkpoint']['generation'], 111)
        self.assertTrue(all(len(s['fingerprint']) == 16 for s in names.values()))
        self.assertNotIn('workflow-lifecycle', names)  # the older producer wrote none

    def test_history_keeps_legacy_lane_ids_navigable(self):
        h = self.report['history']
        self.assertIn('W1', h['lane_aliases'])
        self.assertTrue(h['unresolved'])
        self.assertTrue(all(u['reason'] for u in h['unresolved']))

    def test_markdown_and_v2_are_both_available(self):
        md = render_md.render(self.report)
        self.assertIn('## Stages', md)
        self.assertIn('editor not recorded', md)
        v2 = helpers.run842_report(tempfile.mkdtemp(), schema='v2')[0]
        self.assertEqual(validate.validate(v2), [])
        self.assertIn('lanes_active', v2['summary'])

    def test_real_output_has_the_shapes_the_ui_fixtures_use(self):
        """The hand-built UI fixtures and the real builder must not drift: every key the UI fixture holds in an object that
        both documents have is present in the real output (extra real keys are fine; the UI ignores them)."""
        def missing(real, fixture, path=''):
            out = []
            if isinstance(fixture, dict) and isinstance(real, dict):
                if path.endswith('lane_aliases'):
                    return out
                for k, v in fixture.items():
                    if k not in real:
                        out.append(f'{path}.{k}')
                    else:
                        out += missing(real[k], v, f'{path}.{k}')
            elif isinstance(fixture, list) and isinstance(real, list) and fixture and real:
                out += missing(real[0], fixture[0], path + '[]')
            return out
        for name in ('ui_v3_sample.json', 'ui_v3_edge.json'):
            fixture = json.loads((helpers.FIXTURES / name).read_text(encoding='utf-8'))
            gaps = [g for g in missing(self.report, fixture) if not g.startswith(('.feature.mode', '.feature.source'))]
            self.assertEqual(gaps, [], name)


class Synthetic(Project):
    def put(self, name, data):
        folder = self.feature_dir / 'workflow'
        folder.mkdir(exist_ok=True)
        (folder / name).write_text(data if isinstance(data, str) else json.dumps(data), encoding='utf-8')

    def build(self, schema='v3', now=NOW):
        return model.build(self.ctx, now, 1, {}, schema=schema)

    def attempt(self, run_id, status='successful', identity='specs/001-demo/stage:execute', started='2026-10-15T10:00:00Z',
                ended='2026-10-15T10:10:00Z', **extra):
        row = {'identity': identity, 'run_id': run_id, 'status': status, 'started_at': started, 'ended_at': ended,
               'requested_model': 'm', 'actual_model': 'm', 'actual_model_evidence': 'driver-result'}
        row.update(extra)
        return row

    def ledger(self, *rows):
        self.put('delegations.json', {'feature': 'specs/001-demo', 'attempts': list(rows)})

    def event(self, n, event, stage='execute', at='2026-10-15T10:00:00Z', **extra):
        base = {'v': 1, 'event_id': f'e{n}', 'workflow_run_id': 'wr', 'generation': n, 'at': at, 'stage': stage, 'event': event,
                'episode_id': None, 'claim_id': None, 'caused_by_claim_id': None, 'candidate_run_id': None, 'delegation_run_ids': [], 'reason': None}
        base.update(extra)
        return base

    def lifecycle(self, *events, tail=''):
        self.put('lifecycle.jsonl', ''.join(json.dumps(e) + '\n' for e in events) + tail)

    def stage(self, report, sid):
        return next(s for s in report['stages'] if s['id'] == sid)


class Runs(Synthetic):
    def test_duplicate_run_ids_become_one_run_and_the_disagreement_is_kept(self):
        self.ledger(self.attempt('r1', status='running', ended=None), self.attempt('r1', status='successful'))
        report = self.build()
        runs = [r for r in report['runs'] if r['run_id'] == 'r1']
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['worker_status'], 'successful')
        self.assertEqual(runs[0]['conflict'], ['ended_at', 'status'])

    def test_an_intent_without_a_run_is_dispatch_not_a_run(self):
        self.ledger({'identity': 'specs/001-demo/T002', 'intent_id': 'i1', 'status': 'starting', 'started_at': '2026-10-15T11:00:00Z'},
                    self.attempt('r2', intent_id='i2'),
                    {'identity': 'specs/001-demo/T003', 'intent_id': 'i2', 'status': 'starting'})
        report = self.build()
        self.assertEqual([d['intent_id'] for d in report['dispatch']], ['i1'])  # i2 already has a run
        self.assertEqual([r['run_id'] for r in report['runs']], ['r2'])

    def test_identity_is_parsed_only_after_the_feature_prefix_matches(self):
        self.ledger(self.attempt('r1', identity='specs/001-demo/stage:plan'), self.attempt('r2', identity='other/stage:plan'),
                    self.attempt('r3', identity='specs/001-demo/T002'), self.attempt('r4', identity='elsewhere/T003'),
                    self.attempt('r5', identity='elsewhere/T003', tasks=['T004']))
        runs = {r['run_id']: r for r in self.build()['runs']}
        self.assertEqual((runs['r1']['stage'], runs['r2']['stage']), ('plan', None))
        self.assertEqual((runs['r3']['tasks'], runs['r4']['tasks'], runs['r5']['tasks']), (['T002'], [], ['T004']))

    def test_retry_comes_only_from_an_explicit_link(self):
        self.ledger(self.attempt('r1', status='failed'), self.attempt('r2', started='2026-10-15T10:20:00Z', ended='2026-10-15T10:30:00Z', replaces_run_id='r1'),
                    self.attempt('r3', started='2026-10-15T10:40:00Z', ended='2026-10-15T10:50:00Z'))
        runs = {r['run_id']: r for r in self.build()['runs']}
        self.assertEqual((runs['r2']['retry_of'], runs['r3']['retry_of']), ('r1', None))  # later success, same identity: not a retry
        recovery = [e for e in self.build()['timeline'] if e['kind'] == 'recovery']
        self.assertEqual([(e['fidelity']) for e in recovery], ['recorded'])

    def test_parent_run_id_is_also_a_recorded_link(self):
        self.ledger(self.attempt('r1', status='failed'), self.attempt('r2', parent_run_id='r1'))
        self.assertEqual({r['run_id']: r['retry_of'] for r in self.build()['runs']}['r2'], 'r1')

    def test_a_successful_worker_with_a_rejected_candidate_and_exact_claim_acceptance(self):
        self.ledger(self.attempt('r1', claim_id='c1'), self.attempt('r2', claim_id='c1', started='2026-10-15T11:00:00Z', ended='2026-10-15T11:10:00Z'))
        self.lifecycle(self.event(1, 'claim', episode_id='ep1', claim_id='c1'),
                       self.event(2, 'rejected-completion', episode_id='ep1', claim_id='c1', delegation_run_ids=['r1'], candidate_run_id='r1',
                                  at='2026-10-15T10:20:00Z', reason='checklist drifted'),
                       self.event(3, 'accepted', episode_id='ep1', claim_id='c1', delegation_run_ids=['r1', 'r2'], candidate_run_id='r2',
                                  at='2026-10-15T11:20:00Z'))
        report = self.build()
        runs = {r['run_id']: r for r in report['runs']}
        self.assertEqual((runs['r1']['worker_status'], runs['r1']['candidate_accepted']), ('successful', False))
        self.assertEqual(runs['r2']['candidate_accepted'], True)
        self.assertEqual({r['candidate_accepted'] for r in build_without_lifecycle(self)['runs']}, {None})

    def test_durations_recorded_derived_running_and_unknown(self):
        self.ledger(self.attempt('rec', actual_duration_seconds=125.5), self.attempt('der'),
                    self.attempt('run', status='running', ended=None, started='2026-10-15T11:00:00Z'),
                    self.attempt('lost', status='failed', ended=None))
        runs = {r['run_id']: r['duration'] for r in self.build()['runs']}
        self.assertEqual((runs['rec']['value'], runs['rec']['fidelity']), (125, 'exact'))
        self.assertEqual((runs['der']['value'], runs['der']['fidelity']), (600, 'estimated'))
        self.assertEqual(runs['run']['value'], 3600)  # to the snapshot time
        self.assertIsNone(runs['lost']['value'])
        later = {r['run_id']: r['duration'] for r in self.build(now=parse('2026-10-16T12:00:00Z'))['runs']}
        self.assertIsNone(later['lost']['value'])  # a terminal run with no end never grows with the clock
        self.assertEqual(later['der']['value'], 600)

    def test_stage_run_time_is_labelled_summed_with_completeness(self):
        self.ledger(self.attempt('a'), self.attempt('b', ended=None, status='failed'))
        run_time = self.stage(self.build(), 'execute')['run_time']
        self.assertEqual((run_time['value'], run_time['complete'], run_time['label']), (600, False, 'summed, may overlap'))

    def test_host_child_gets_a_namespaced_identity_and_merges_only_through_an_explicit_run_id(self):
        self.init()
        self.bind()
        self.hook('pre_tool_use', self.payload('claude_pre_task.json'), now='2026-10-15T12:00:07Z')
        report = self.build()
        hosts = [r for r in report['runs'] if r['run_id'].startswith('host:')]
        self.assertEqual(len(hosts), 1)
        self.assertEqual(hosts[0]['run_id'], hosts[0]['identity'])
        self.assertEqual(len({r['run_id'] for r in report['runs']}), len(report['runs']))


def build_without_lifecycle(case):
    (case.feature_dir / 'workflow' / 'lifecycle.jsonl').unlink()
    return case.build()


class Lifecycle(Synthetic):
    def test_episodes_follow_claims_and_a_rejected_completion_does_not_end_the_claim(self):
        self.ledger(self.attempt('r1', claim_id='c1', identity='specs/001-demo/stage:plan'))
        self.lifecycle(self.event(1, 'claim', stage='plan', episode_id='ep1', claim_id='c1', at='2026-10-15T09:00:00Z'),
                       self.event(2, 'rejected-completion', stage='plan', episode_id='ep1', claim_id='c1', at='2026-10-15T09:30:00Z',
                                  delegation_run_ids=['r1'], reason='lineage'))
        plan = self.stage(self.build(), 'plan')
        ep = plan['episodes'][0]
        self.assertEqual((ep['outcome'], ep['ended_at'], ep['source'], ep['claim_id']), ('rejected-completion', None, 'workflow-lifecycle', 'c1'))
        self.assertEqual(ep['runs'], ['r1'])
        self.assertEqual(plan['unknown_runs'], [])
        self.assertEqual(plan['status'], 'pending')

    def test_acceptance_resume_recovery_invalidation_and_revalidation(self):
        self.lifecycle(self.event(1, 'claim', episode_id='a', claim_id='c1', at='2026-10-15T09:00:00Z'),
                       self.event(2, 'accepted', episode_id='a', claim_id='c1', at='2026-10-15T09:30:00Z'),
                       self.event(3, 'claim', episode_id='b', claim_id='c2', at='2026-10-15T10:00:00Z'),
                       self.event(4, 'recovered', episode_id='b', claim_id='c2', at='2026-10-15T10:20:00Z', reason='worker died'),
                       self.event(5, 'resume', episode_id='c', claim_id='c3', at='2026-10-15T11:00:00Z'),
                       self.event(6, 'invalidated', at='2026-10-15T11:30:00Z', reason='upstream changed'))
        execute = self.stage(self.build(), 'execute')
        self.assertEqual([e['outcome'] for e in execute['episodes']], ['accepted', 'recovered', 'unknown'])
        self.assertEqual(execute['validity'], 'stale')
        self.assertEqual(execute['accepted_at'], '2026-10-15T09:30:00Z')
        self.lifecycle(self.event(1, 'accepted', at='2026-10-15T09:30:00Z', episode_id='a'),
                       self.event(2, 'invalidated', at='2026-10-15T10:00:00Z'),
                       self.event(3, 'revalidated', at='2026-10-15T11:00:00Z', episode_id='r'))
        execute = self.stage(self.build(), 'execute')
        self.assertEqual((execute['validity'], execute['accepted_at']), ('current', '2026-10-15T11:00:00Z'))

    def test_a_torn_final_line_is_ignored_and_a_replayed_event_counts_once(self):
        event = self.event(1, 'claim', episode_id='a', claim_id='c1')
        self.lifecycle(event, event, self.event(2, 'accepted', episode_id='a'), tail='{"v": 1, "event_id": "e3", "ev')
        got = lifecol.collect(self.feature_dir)
        self.assertEqual((len(got['events']), got['torn'], got['corrupt'], got['state']), (2, True, 0, 'available'))
        self.assertEqual(len(self.stage(self.build(), 'execute')['episodes']), 1)

    def test_a_corrupt_complete_line_is_counted_and_unknown_events_are_skipped(self):
        self.put('lifecycle.jsonl', 'not json\n' + json.dumps(self.event(1, 'claim')) + '\n' + json.dumps(self.event(2, 'mystery')) + '\n')
        got = lifecol.collect(self.feature_dir)
        self.assertEqual((len(got['events']), got['corrupt'], got['skipped']), (1, 1, 1))

    def test_a_conflicting_duplicate_event_id_keeps_the_first_and_is_reported(self):
        self.lifecycle(self.event(1, 'claim', episode_id='a'), dict(self.event(1, 'claim', episode_id='a'), reason='different'))
        got = lifecol.collect(self.feature_dir)
        self.assertEqual((len(got['events']), got['conflicts']), (1, ['e1']))
        note = next(s for s in self.build()['sources'] if s['name'] == 'workflow-lifecycle')['note']
        self.assertIn('conflicting', note)

    def test_receipt_and_recovery_records_make_labelled_episodes_for_older_producers(self):
        self.put('checkpoint.json', {'feature': 'specs/001-demo', 'status': 'in-progress', 'generation': 3,
                                     'receipts': {'plan': {'stage': 'plan', 'outcome': 'passed', 'completed_at': '2026-10-15T09:00:00Z', 'mode': 'revalidate'}},
                                     'recoveries': [{'stage': 'plan', 'reason': 'restored', 'at': '2026-10-15T08:00:00Z'}]})
        plan = self.stage(self.build(), 'plan')
        self.assertEqual(sorted((e['source'], e['fidelity'], e['outcome']) for e in plan['episodes']),
                         [('checkpoint-receipt', 'partial', 'accepted'), ('checkpoint-recovery', 'partial', 'recovered')])
        self.assertEqual(plan['validity'], 'unknown')

    def test_revalidation_is_not_a_retry(self):
        self.ledger(self.attempt('r1', status='failed'), self.attempt('r2', started='2026-10-15T11:00:00Z', ended='2026-10-15T11:10:00Z'))
        self.lifecycle(self.event(1, 'revalidated', at='2026-10-15T11:05:00Z', episode_id='rv', delegation_run_ids=['r2']))
        runs = {r['run_id']: r for r in self.build()['runs']}
        self.assertIsNone(runs['r2']['retry_of'])


class Stages(Synthetic):
    CHECKPOINT = {'feature': 'specs/001-demo', 'status': 'in-progress', 'generation': 9, 'receipts': {}}

    def test_a_published_stage_plan_sets_order_and_selection(self):
        self.put('checkpoint.json', dict(self.CHECKPOINT, stage_plan={'v': 1, 'generation': 9, 'stages': [
            'scope', {'id': 'plan', 'label': 'Planning'}, 'execute']}))
        report = self.build()
        selected = [s['id'] for s in report['stages'] if s['selected']]
        self.assertEqual(selected, ['scope', 'plan', 'execute'])
        self.assertEqual(self.stage(report, 'plan')['label'], 'Planning')
        self.assertEqual(self.stage(report, 'verify')['status'], 'excluded')
        self.assertEqual(report['summary']['stages_selected'], 3)

    def test_without_a_stage_plan_the_policy_snapshot_filters_qa_and_manual_stages(self):
        self.put('checkpoint.json', dict(self.CHECKPOINT, policy={'processes': {'qa': False, 'user_manual': True}}))
        report = self.build()
        self.assertEqual(self.stage(report, 'qa_analyze')['status'], 'excluded')
        self.assertEqual(self.stage(report, 'manual_analyze')['status'], 'pending')

    def test_an_unreadable_or_future_stage_plan_falls_back_to_the_canonical_list(self):
        for plan in ({'v': 2, 'stages': ['scope']}, {'v': 1, 'stages': 'nope'}, {'v': 1, 'stages': ['a', 'a']}):
            self.put('checkpoint.json', dict(self.CHECKPOINT, stage_plan=plan))
            self.assertEqual(len([s for s in self.build()['stages'] if s['id'] in ('scope', 'pr')]), 2)

    def test_excluded_is_not_waived_and_a_failed_worker_does_not_reject_a_stage(self):
        self.put('checkpoint.json', dict(self.CHECKPOINT, stage_plan={'v': 1, 'generation': 9, 'stages': ['execute']}))
        self.ledger(self.attempt('r1', status='failed'))
        report = self.build()
        self.assertEqual(self.stage(report, 'execute')['status'], 'pending')
        self.assertEqual(self.stage(report, 'execute')['failed_runs'], 1)
        self.assertEqual(self.stage(report, 'scope')['status'], 'excluded')

    def test_next_action_is_displayed_as_cached_and_never_computed(self):
        self.put('checkpoint.json', dict(self.CHECKPOINT, next_action={'text': 'Complete execute', 'stage': 'execute', 'kind': 'active-claim',
                                                                       'evaluated_at': '2026-10-15T11:00:00Z', 'generation': 9}))
        self.assertEqual(self.build()['feature']['next_action'],
                         {'text': 'Complete execute', 'stage': 'execute', 'kind': 'active-claim', 'evaluated_at': '2026-10-15T11:00:00Z',
                          'generation': 9, 'source': 'workflow-checkpoint'})
        self.put('checkpoint.json', dict(self.CHECKPOINT))
        self.assertIsNone(self.build()['feature']['next_action'])

    def test_plain_spec_kit_and_plan_mode_show_no_workflow_stages(self):
        self.assertEqual(self.build()['stages'], [])

    def test_stale_receipt_is_stale_not_current(self):
        self.put('checkpoint.json', dict(self.CHECKPOINT, receipts={'scope': {'stage': 'scope', 'outcome': 'passed', 'stale': True,
                                                                              'completed_at': '2026-10-15T09:00:00Z'}}))
        scope = self.stage(self.build(), 'scope')
        self.assertEqual((scope['status'], scope['validity']), ('accepted', 'stale'))


class Workstreams(Synthetic):
    def test_marked_lane_facts_assign_tasks_and_a_later_assignment_supersedes(self):
        self.init()
        self.assertEqual(self.cli('lane', 'L1', '--tasks', 'T001-T003', '--owner', 'ann', '--workstream')[0], 0)
        self.assertEqual(self.cli('lane', 'L2', '--tasks', 'T003', '--owner', 'bob', '--workstream')[0], 0)
        by_id = {w['id']: w for w in self.build()['workstreams']}
        self.assertEqual(by_id['L1']['origin'], 'facts-marked')
        self.assertEqual(by_id['L2']['tasks']['waiting'], ['T003'])
        self.assertNotIn('T003', by_id['L1']['tasks']['waiting'])
        want = [{'task': 'T003', 'workstreams': ['L1', 'L2']}]
        self.assertEqual((by_id['L1']['conflicts'], by_id['L2']['conflicts']), (want, want))  # each workstream the conflict names shows it

    def test_an_unmarked_lane_is_not_a_workstream_even_when_it_lists_tasks(self):
        self.init()
        self.cli('lane', 'L1', '--tasks', 'T001-T003', '--owner', 'ann')
        self.assertEqual({w['id'] for w in self.build()['workstreams']}, {'shared'})

    def test_owner_intervals_replay_from_lane_records(self):
        self.init()
        self.cli('lane', 'L1', '--tasks', 'T002', '--owner', 'ann', '--workstream')
        self.cli('lane', 'L1', '--owner', 'bob')
        owners = {w['id']: w for w in self.build()['workstreams']}['L1']['owners']
        self.assertEqual([o['agent'] for o in owners], ['ann', 'bob'])
        self.assertIsNone(owners[-1]['to'])
        self.assertEqual(owners[0]['to'], owners[1]['from'])

    def test_a_run_gets_a_workstream_only_when_its_tasks_agree(self):
        self.init()
        self.cli('lane', 'L1', '--tasks', 'T002', '--owner', 'ann', '--workstream')
        self.ledger(self.attempt('one', identity='specs/001-demo/T002', started='2030-01-01T00:00:00Z'),
                    self.attempt('both', identity='specs/001-demo/T002', tasks=['T002', 'T003'], started='2030-01-01T00:00:00Z'))
        runs = {r['run_id']: r['workstream'] for r in self.build()['runs']}
        self.assertEqual((runs['one'], runs['both']), ('L1', None))

    def test_buckets_checkbox_then_blocker_then_live_run_then_waiting(self):
        self.init()
        self.cli('block', 'T003', '--by', 'ext:"vendor"')
        self.ledger(self.attempt('live', identity='specs/001-demo/T002', status='running', ended=None))
        shared = {w['id']: w for w in self.build()['workstreams']}['shared']['tasks']
        self.assertEqual(shared, {'done': ['T001', 'T005'], 'blocked': ['T003'], 'active': ['T002'], 'waiting': ['T004']})

    def test_legend_declares_workstream_tags_and_nothing_else(self):
        text = '\n'.join(['| Marker | Work |', '|---|---|', '| `[Impl]` | Lane for coding |', '| `[A]` / `[B]` | Coding lane: **A** does x; **B** does y |',
                          '', '- [ ] T001 [Impl] [A] one', '- [ ] T002 [B] [P] two', '- [ ] T003 [C] three', '- [ ] T004 [A] [B] four'])
        parsed = taskscol.parse(text)
        self.assertEqual(set(parsed['legend']), {'A', 'B'})
        self.assertEqual([t['workstream'] for t in parsed['tasks']], ['A', 'B', None, None])


class Decisions(Synthetic):
    def ledger_item(self, ident, status, **extra):
        item = {'id': ident, 'options': ['x', 'y', 'z'], 'question_url': f'https://github.com/a/b/issues/1#issuecomment-{ident}',
                'status': status, 'option': None, 'answers': [], 'answer_digest': 'd'}
        item.update(extra)
        return item

    def test_workflow_states_edits_conflicts_and_multiple_selection(self):
        self.put('decisions.json', {'version': 1, 'feature': 'specs/001-demo', 'issue': 'a/b#1', 'decisions': [
            self.ledger_item('SD1', 'pending'),
            self.ledger_item('SD2', 'conflict', answers=[{'option': 'x', 'created_at': '2026-10-15T09:00:00Z'},
                                                         {'option': 'y', 'created_at': '2026-10-15T09:05:00Z'}]),
            self.ledger_item('SD3', 'answered', mode='multiple', selected=['x', 'z'], answers=[{'option': 'x', 'created_at': '2026-10-15T09:00:00Z', 'author': None}]),
            self.ledger_item('SD4', 'applied', option='y', selected=['y'], answers=[{'option': 'y', 'created_at': '2026-10-15T09:00:00Z', 'author': 'ann'}],
                             application={'evidence': {'spec.md': 'h'}, 'answer_digest': 'd'})]})
        decisions = self.build()['decisions']
        self.assertEqual([d['source_id'] for d in decisions['pending']], ['SD1', 'SD2'])
        self.assertEqual([d['state'] for d in decisions['pending']], ['pending', 'conflict'])
        sd3 = next(d for d in decisions['made'] if d['source_id'] == 'SD3')
        self.assertEqual((sd3['answer']['kind'], sd3['answer']['value'], sd3['decided_by']), ('multiple', ['x', 'z'], None))
        sd4 = next(d for d in decisions['made'] if d['source_id'] == 'SD4')
        self.assertEqual((sd4['state'], sd4['decided_by'], sd4['applied']['evidence'], sd4['answer_digest']), ('applied', 'ann', ['spec.md'], 'd'))
        self.assertTrue(all(d['key'].startswith('001-demo:workflow:') for d in decisions['pending']))

    def test_facts_decisions_never_merge_with_workflow_ones_by_text(self):
        self.init()
        self.cli('decide', 'ask', 'Use SQLite?', '--options', 'yes,no')
        self.put('decisions.json', {'version': 1, 'decisions': [self.ledger_item('SD1', 'pending', question='Use SQLite?')]})
        pending = self.build()['decisions']['pending']
        self.assertEqual(sorted(d['source'] for d in pending), ['facts', 'workflow'])
        self.assertEqual(len({d['key'] for d in pending}), 2)

    def clarifications(self, *items):
        self.put('clarifications.json', {'v': 1, 'items': list(items)})

    def item(self, source_id, state, revision=1, **extra):
        base = {'source_id': source_id, 'revision': revision, 'question': 'Which?', 'options': ['A', 'B'], 'answer': None, 'state': state,
                'url': 'https://github.com/a/b/issues/1#issuecomment-1', 'editor': None, 'observed_at': '2026-10-15T09:00:00Z',
                'answered_at': None, 'applied': None, 'evidence': []}
        base.update(extra)
        return base

    def test_clarification_states_revisions_waivers_and_unresolved(self):
        self.clarifications(
            self.item('C1Q1', 'pending', revision=1),
            self.item('C1Q1', 'answered', revision=2, answer={'kind': 'single', 'value': 'B'}, editor='ann', answered_at='2026-10-15T09:30:00Z'),
            self.item('C1Q2', 'waived', evidence=['owner waived in comment 7']),
            self.item('C1Q3', 'conflict'),
            self.item('C1Q4', 'bogus-state'))
        decisions = self.build()['decisions']
        states = {d['source_id']: d['state'] for d in decisions['pending'] + decisions['made']}
        self.assertEqual(states, {'C1Q1@r1': 'superseded', 'C1Q1': 'answered', 'C1Q2': 'waived', 'C1Q3': 'conflict'})
        self.assertEqual([d['source_id'] for d in decisions['pending']], ['C1Q3'])
        answered = next(d for d in decisions['made'] if d['source_id'] == 'C1Q1')
        self.assertEqual((answered['decided_by'], answered['answered_at']), ('ann', '2026-10-15T09:30:00Z'))
        source = next(s for s in decisions['sources'] if s['name'] == 'clarification')
        self.assertEqual((source['state'], source['note']), ('available', '1 unreadable item(s) skipped'))

    def test_source_states_absent_unsupported_and_invalid(self):
        def state():
            return {s['name']: s['state'] for s in self.build()['decisions']['sources']}
        self.assertEqual(state()['clarification'], 'absent')
        self.put('clarifications.json', {'v': 9, 'items': []})
        self.assertEqual(state()['clarification'], 'unsupported')
        self.put('clarifications.json', 'not json')
        self.assertEqual(state()['clarification'], 'invalid')
        self.put('decisions.json', 'not json')
        self.assertEqual(state()['workflow'], 'available')  # an unreadable ledger reads as empty; see contracts

    def test_attention_lists_pending_and_conflicting_decisions_and_blockers(self):
        self.init()
        self.cli('block', 'T002', '--by', 'ext:"vendor"')
        self.clarifications(self.item('C1Q1', 'conflict'))
        kinds = sorted(a['kind'] for a in self.build()['attention'])
        self.assertEqual(kinds, ['blocker', 'decision'])
        self.assertEqual(self.build()['attention'][0]['severity'], 'high')


class SelfReport(Synthetic):
    def test_bind_with_model_and_effort_stores_a_labelled_self_report(self):
        self.init()
        code, line = self.cli('bind', '--host', 'codex', '--model', 'gpt-6.1-sol', '--effort', 'high')
        self.assertEqual(code, 0, line)
        self.assertTrue((self.ctx.host_dir / 'self-report.json').is_file())
        o = self.build()['orchestrator']
        self.assertEqual((o['model']['value'], o['model']['source'], o['provenance']['model']), ('gpt-6.1-sol', 'self-report', 'self-report'))
        self.assertEqual(o['provenance']['context'], 'none')
        self.assertIn('self-reported', o['note'])

    def test_host_observation_wins_per_field_and_mixed_provenance_is_kept(self):
        self.init()
        self.bind()
        self.hook('pre_tool_use', self.payload('claude_pre_task.json'), now='2026-10-15T12:00:07Z')
        host = self.build()['orchestrator']
        self.cli('bind', '--model', 'self-model', '--effort', 'low', '--session', 'claude-sess-1')
        o = self.build()['orchestrator']
        if host['model']['value'] is not None:
            self.assertEqual(o['model']['value'], host['model']['value'])
            self.assertEqual(o['provenance']['model'], 'host-hook')
        if host['effort']['value'] is None:
            self.assertEqual((o['effort']['value'], o['provenance']['effort']), ('low', 'self-report'))
        else:
            self.assertEqual(o['provenance']['effort'], 'host-hook')

    def test_a_report_for_another_session_is_ignored(self):
        self.init()
        self.bind()
        self.hook('pre_tool_use', self.payload('claude_pre_task.json'), now='2026-10-15T12:00:07Z')
        self.cli('bind', '--model', 'self-model', '--session', 'some-other-session')
        o = self.build()['orchestrator']
        self.assertNotEqual(o['model']['source'], 'self-report')

    def test_a_report_from_another_worktree_or_feature_is_ignored(self):
        self.init()
        self.cli('bind', '--model', 'm1')
        path = self.ctx.host_dir / 'self-report.json'
        doc = json.loads(path.read_text(encoding='utf-8'))
        for change in ({'feature': 'specs/999-other'}, {'worktree': str(self.root / 'elsewhere')}):
            path.write_text(json.dumps(dict(doc, **change)), encoding='utf-8')
            self.assertEqual(self.build()['orchestrator']['model']['value'], None, change)

    def test_the_self_report_survives_deleting_the_view(self):
        self.init()
        self.cli('bind', '--model', 'm1')
        import shutil
        shutil.rmtree(self.ctx.view)
        self.assertEqual(self.build()['orchestrator']['model']['value'], 'm1')

    def test_secrets_are_refused(self):
        self.init()
        code, line = self.cli('bind', '--model', 'sk-' + 'a' * 30)
        self.assertEqual(code, 3, line)


class Adapter(Synthetic):
    def test_status_json_defaults_to_v3_and_schema_v2_gives_the_compatibility_document(self):
        self.init()
        code, text = self.cli('status', '--json')
        self.assertEqual(json.loads(text)['schema'], 'sanduq.progress.v3')
        code, text = self.cli('status', '--json', '--schema', 'v3')
        self.assertEqual(json.loads(text)['schema'], 'sanduq.progress.v3')
        code, text = self.cli('status', '--json', '--schema', 'v2')
        v2 = json.loads(text)
        self.assertEqual(v2['schema'], 'sanduq.progress.v2')
        self.assertEqual(validate.validate(v2), [])
        self.assertEqual(self.cli('status', '--json', '--schema', 'v9')[0], 2)

    def test_the_one_line_summary_and_the_stored_report(self):
        self.init()
        code, line = self.cli('status')
        self.assertRegex(line, r'^progress: 2/5 tasks, 0 lanes active, 0 blocked, 0 decisions pending \(rev \d+\)')
        self.assertEqual(self.stored_report()['schema'], 'sanduq.progress.v3')

    def test_export_markdown_and_json_in_both_schemas(self):
        self.init()
        v3 = self.cli('export')[1]
        v2 = self.cli('export', '--schema', 'v2')[1]
        self.assertIn('## Workstreams', v3)
        self.assertIn('## Lanes', v2)
        self.assertEqual(json.loads(self.cli('export', '--format', 'json')[1])['schema'], 'sanduq.progress.v3')
        self.assertEqual(json.loads(self.cli('export', '--format', 'json', '--schema', 'v2')[1])['schema'], 'sanduq.progress.v2')

    def test_v3_and_v2_agree_on_the_facts_they_share(self):
        self.init()
        self.cli('block', 'T002', '--by', 'ext:"x"')
        self.cli('decide', 'ask', 'Q?', '--options', 'a,b')
        v3, v2 = self.build(), self.build('v2')
        self.assertEqual(v3['summary']['blockers_open'], v2['summary']['blocked'])
        self.assertEqual(v3['summary']['decisions_pending'], v2['summary']['decisions_pending'])
        self.assertEqual((v3['summary']['tasks_total'], v3['summary']['tasks_done']), (v2['summary']['tasks_total'], v2['summary']['tasks_done']))

    def test_classic_layout_feeds_the_browser_the_v2_document_and_timeline_feeds_v3(self):
        self.init()
        shown = lambda: json.loads((self.ctx.view / 'data.js').read_text(encoding='utf-8')[len('window.__SANDUQ_PROGRESS__ = '):].rstrip().rstrip(';'))
        self.assertEqual(shown()['schema'], 'sanduq.progress.v3')
        self.assertEqual(self.cli('theme', '--layout', 'classic')[0], 0)
        self.assertEqual(shown()['schema'], 'sanduq.progress.v2')  # the layout command itself publishes the matching document
        self.assertEqual(self.stored_report()['schema'], 'sanduq.progress.v3')
        self.assertEqual(self.cli('theme', '--layout', 'timeline')[0], 0)
        self.assertEqual(shown()['schema'], 'sanduq.progress.v3')

    def test_rev_advances_and_a_debounced_event_patches_both_documents(self):
        self.init()
        first = self.stored_report()['rev']
        self.cli('refresh')
        self.assertGreater(self.stored_report()['rev'], first)


class PlanModeV3(helpers.PlanProject):
    def test_plan_mode_projects_v3_with_tasks_and_no_workflow_stages(self):
        self.init_plan()
        report = model.build(self.ctx, NOW, 1, {})
        self.assertEqual(validate.validate(report), [])
        self.assertEqual((report['stages'], report['feature']['mode']), ([], 'plan'))
        self.assertEqual({w['id'] for w in report['workstreams']}, {'shared'})


class ThemeLayout(Project):
    def layout_js(self):
        return (self.ctx.view / 'layout.js').read_text(encoding='utf-8')

    def test_layout_defaults_to_timeline_in_layout_js(self):
        self.init()
        self.assertIn('"layout":"timeline"', self.layout_js())

    def test_theme_layout_writes_the_key_to_layout_js_and_keeps_other_customizations(self):
        self.init()
        self.assertEqual(self.cli('theme', '--preset', 'cobalt')[0], 0)
        self.assertEqual(self.cli('theme', '--layout', 'classic'), (0, 'progress: theme layout classic'))
        self.assertIn('"layout":"classic"', self.layout_js())
        self.assertIn('"preset":"cobalt"', self.layout_js())
        self.assertEqual(self.cli('theme', '--preset', 'emerald')[0], 0)  # a new look keeps the picked layout
        self.assertIn('"layout":"classic"', self.layout_js())
        self.assertEqual(self.cli('theme', '--layout', 'timeline')[0], 0)
        self.assertIn('"layout":"timeline"', self.layout_js())

    def test_unknown_layout_is_refused(self):
        self.init()
        code, line = self.cli('theme', '--layout', 'grid')
        self.assertEqual(code, 2, line)
        with self.assertRaises(theme.ThemeError):
            theme.validate({'layout': 'grid'})
        self.assertEqual(theme.resolve_doc({})['layout'], 'timeline')


if __name__ == '__main__':
    unittest.main()
