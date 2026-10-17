"""Review cycle 1 (Fable and Astra) fixes for the consumer side: acceptance, episodes, nullable stages, evidence shapes,
recoveries, open/unknown timing, bounded and consistent reads, Markdown tasks, hostile ids and the layout republish."""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

import helpers
from helpers import T0
from sanduq_progress import model, render_md, validate
from sanduq_progress.collect import clarifications as clarcol, lifecycle as lifecol
from test_v3_model import NOW, Synthetic, parse

LIVE_842 = Path('D:/Projects/abushanab-net/Bunyan--issue-842/specs/842-persist-and-publish-versioned-project-workflow-graphs/workflow/checkpoint.json')
VECTOR = helpers.FIXTURES / 'clarifications-vector.json'


class Acceptance(Synthetic):
    def test_only_the_candidate_run_is_accepted_not_every_run_of_the_claim(self):
        self.ledger(self.attempt('r1', status='failed', claim_id='c1'),
                    self.attempt('r2', claim_id='c1', started='2026-10-15T11:00:00Z', ended='2026-10-15T11:10:00Z'))
        self.lifecycle(self.event(1, 'claim', episode_id='ep1', claim_id='c1'),
                       self.event(2, 'accepted', episode_id='ep1', claim_id='c1', delegation_run_ids=['r1', 'r2'], candidate_run_id='r2',
                                  at='2026-10-15T11:20:00Z'))
        runs = {r['run_id']: r for r in self.build()['runs']}
        self.assertEqual((runs['r1']['candidate_accepted'], runs['r2']['candidate_accepted']), (None, True))
        self.assertEqual(self.stage(self.build(), 'execute')['episodes'][0]['runs'], ['r1', 'r2'])  # membership is still recorded

    def test_an_accepted_event_with_no_candidate_accepts_nobody(self):
        self.ledger(self.attempt('r1', claim_id='c1'))
        self.lifecycle(self.event(1, 'claim', episode_id='ep1', claim_id='c1'),
                       self.event(2, 'accepted', episode_id='ep1', claim_id='c1', delegation_run_ids=['r1'], at='2026-10-15T11:20:00Z'))
        self.assertEqual({r['candidate_accepted'] for r in self.build()['runs']}, {None})

    def test_a_failed_or_abandoned_worker_does_not_imply_evidence_rejected(self):
        self.ledger(self.attempt('f', status='failed'), self.attempt('a', status='abandoned'), self.attempt('ok', accepted_at='2026-10-15T10:30:00Z'))
        runs = {r['run_id']: r['evidence_accepted'] for r in self.build()['runs']}
        self.assertEqual(runs, {'f': None, 'a': None, 'ok': True})


class Episodes(Synthetic):
    def test_a_claim_time_invalidation_makes_no_episode_and_does_not_break_the_run_join(self):
        self.ledger(self.attempt('r1', claim_id='c1'))
        self.lifecycle(self.event(1, 'claim', episode_id='ep1', claim_id='c1', at='2026-10-15T09:00:00Z'),
                       self.event(2, 'invalidated', stage='verify', at='2026-10-15T09:00:01Z', caused_by_claim_id='c1', reason='execute claimed'),
                       self.event(3, 'invalidated', stage='review', at='2026-10-15T09:00:01Z', caused_by_claim_id='c1', reason='execute claimed'))
        report = self.build()
        self.assertEqual(self.stage(report, 'verify')['episodes'], [])
        self.assertEqual(self.stage(report, 'review')['episodes'], [])
        self.assertEqual(self.stage(report, 'verify')['validity'], 'stale')
        execute = self.stage(report, 'execute')
        self.assertEqual(len(execute['episodes']), 1)
        run = report['runs'][0]
        self.assertEqual(run['episode_id'], execute['episodes'][0]['id'])
        self.assertEqual(execute['unknown_runs'], [])
        text = ' '.join(e['text'] for e in report['timeline'])
        self.assertIn('Verify invalidated: execute claimed', text)

    def test_an_invalidation_never_sets_an_episode_start(self):
        self.lifecycle(self.event(1, 'invalidated', episode_id='ep1', at='2026-10-15T09:00:00Z'),
                       self.event(2, 'claim', episode_id='ep1', claim_id='c1', at='2026-10-15T10:00:00Z'))
        episode = self.stage(self.build(), 'execute')['episodes'][0]
        self.assertEqual(episode['started_at'], '2026-10-15T10:00:00Z')
        self.lifecycle(self.event(1, 'invalidated', episode_id='ep1', at='2026-10-15T09:00:00Z'))
        self.assertIsNone(self.stage(self.build(), 'execute')['episodes'][0]['started_at'])

    def test_events_that_only_name_a_claim_are_loose(self):
        self.lifecycle(self.event(1, 'accepted', claim_id='c9', at='2026-10-15T10:00:00Z'))
        execute = self.stage(self.build(), 'execute')
        self.assertEqual(execute['episodes'], [])
        self.assertEqual(execute['accepted_at'], '2026-10-15T10:00:00Z')  # it still feeds acceptance and validity

    def test_a_feature_level_pause_and_recovery_have_no_stage_and_make_no_episode(self):
        self.lifecycle(self.event(1, 'paused', stage=None, at='2026-10-15T09:00:00Z', reason='context budget'),
                       self.event(2, 'recovered', stage=None, at='2026-10-15T09:10:00Z', reason='claim cleared'),
                       self.event(3, 'mystery'))
        got = lifecol.collect(self.feature_dir)
        self.assertEqual((got['state'], len(got['events']), got['skipped']), ('available', 2, 1))
        report = self.build()
        self.assertEqual(validate.validate(report), [])
        self.assertEqual([e for s in report['stages'] for e in s['episodes']], [])
        texts = [e['text'] for e in report['timeline']]
        self.assertIn('Feature paused: context budget', texts)
        self.assertIn('Feature recovered: claim cleared', texts)
        note = next(s for s in report['sources'] if s['name'] == 'workflow-lifecycle')['note']
        self.assertIn('1 unusable record(s) skipped', note)

    def test_a_stage_is_still_required_for_the_other_events(self):
        self.lifecycle(self.event(1, 'accepted', stage=None))
        self.assertEqual(lifecol.collect(self.feature_dir)['state'], 'invalid')


class Recoveries(unittest.TestCase):
    def test_the_real_nested_recovery_shape_makes_seven_episodes_for_the_842_fixture(self):
        with tempfile.TemporaryDirectory() as base:
            report, _ = helpers.run842_report(base, schema='v3')
        episodes = [(s['id'], e) for s in report['stages'] for e in s['episodes'] if e['source'] == 'checkpoint-recovery']
        self.assertEqual(len(episodes), 7)
        self.assertEqual(sorted(sid for sid, _ in episodes), ['clarify', 'execute', 'execute', 'plan', 'plan', 'qa_document', 'review'])
        for _, e in episodes:
            self.assertIsNotNone(e['started_at'])  # the claim's claimed_at is kept as the start evidence
            self.assertTrue(e['identity'].startswith('specs/842-versioned-workflow-graphs/stage:'))
        self.assertNotIn('fixture-token', json.dumps(report))  # the claim token is never read

    @unittest.skipUnless(LIVE_842.is_file(), 'the live #842 checkpoint is not on this machine')
    def test_the_live_842_checkpoint_shows_all_seven_recoveries_and_leaks_no_token(self):
        live = json.loads(LIVE_842.read_text(encoding='utf-8'))
        tokens = [r['claim']['token'] for r in live['recoveries']]
        with tempfile.TemporaryDirectory() as base:
            ctx = helpers.run842_ctx(base)
            (ctx.feature_dir / 'workflow' / 'checkpoint.json').write_text(json.dumps(live), encoding='utf-8')
            report = model.build(ctx, parse(helpers.RUN842_NOW), 1, {}, schema='v3')
        shown = [e for s in report['stages'] for e in s['episodes'] if e['source'] == 'checkpoint-recovery']
        self.assertEqual(len(shown), 7)
        text = json.dumps(report)
        self.assertFalse([t for t in tokens if t in text])

    def test_a_flat_older_recovery_record_is_still_read(self):
        from sanduq_progress.collect import workflow as wf
        got = wf.recoveries([{'stage': 'plan', 'reason': 'x', 'at': '2026-10-15T08:00:00Z'}, {'reason': 'no time'}])
        self.assertEqual([(r['stage'], r['started_at'], r['identity']) for r in got], [('plan', None, None)])


class Timing(Synthetic):
    def test_a_terminal_run_with_no_end_is_end_unknown_and_never_open(self):
        self.ledger(self.attempt('lost', status='failed', ended=None))
        stage = self.stage(self.build(), 'execute')
        self.assertEqual((stage['open'], stage['timing'], stage['last_end']), (False, 'end-unknown', None))
        self.assertEqual(stage['first_start'], '2026-10-15T10:00:00Z')

    def test_a_live_run_or_running_episode_makes_the_stage_open(self):
        self.ledger(self.attempt('live', status='running', ended=None))
        stage = self.stage(self.build(), 'execute')
        self.assertEqual((stage['open'], stage['timing'], stage['last_end']), (True, 'open', None))
        self.ledger()
        (self.feature_dir / 'workflow' / 'checkpoint.json').write_text(
            json.dumps({'feature': 'specs/001-demo', 'status': 'in-progress', 'generation': 1, 'active': {'stage': 'plan'}}), encoding='utf-8')
        self.lifecycle(self.event(1, 'claim', stage='plan', episode_id='ep1', claim_id='c1', at='2026-10-15T09:00:00Z'))
        plan = self.stage(self.build(), 'plan')
        self.assertEqual((plan['open'], plan['timing'], plan['first_start']), (True, 'open', '2026-10-15T09:00:00Z'))

    def test_episode_boundaries_count_toward_first_start_and_last_end(self):
        self.lifecycle(self.event(1, 'claim', episode_id='ep1', claim_id='c1', at='2026-10-15T09:00:00Z'),
                       self.event(2, 'accepted', episode_id='ep1', claim_id='c1', at='2026-10-15T09:30:00Z'))
        stage = self.stage(self.build(), 'execute')
        self.assertEqual((stage['first_start'], stage['last_end'], stage['timing'], stage['open']),
                         ('2026-10-15T09:00:00Z', '2026-10-15T09:30:00Z', 'closed', False))

    def test_a_stage_with_nothing_recorded_has_unknown_timing(self):
        self.lifecycle(self.event(1, 'invalidated', at='2026-10-15T09:00:00Z'))
        self.assertEqual(self.stage(self.build(), 'execute')['timing'], 'unknown')


class Workstreams(Synthetic):
    def test_a_run_with_a_missing_or_invalid_start_has_no_workstream(self):
        self.init()
        self.cli('lane', 'L1', '--tasks', 'T002', '--owner', 'ann', '--workstream')
        self.ledger(self.attempt('dated', identity='specs/001-demo/T002', started='2030-01-01T00:00:00Z'),
                    self.attempt('none', identity='specs/001-demo/T002', started=None),
                    self.attempt('bad', identity='specs/001-demo/T002', started='not a time'))
        runs = {r['run_id']: r['workstream'] for r in self.build()['runs']}
        self.assertEqual(runs, {'dated': 'L1', 'none': None, 'bad': None})

    def test_an_explicit_assignment_reference_still_places_a_run_without_a_start(self):
        self.init()
        self.cli('lane', 'L1', '--tasks', 'T002', '--owner', 'ann', '--workstream')
        self.ledger(self.attempt('named', identity='specs/001-demo/T002', started=None, lane_id='L1'),
                    self.attempt('wrong', identity='specs/001-demo/T003', started=None, lane_id='L1'))
        runs = {r['run_id']: r['workstream'] for r in self.build()['runs']}
        self.assertEqual(runs, {'named': 'L1', 'wrong': None})


class EvidenceShapes(unittest.TestCase):
    def collect(self, doc):
        with tempfile.TemporaryDirectory() as base:
            folder = Path(base) / 'workflow'
            folder.mkdir()
            (folder / 'clarifications.json').write_text(json.dumps(doc), encoding='utf-8')
            return clarcol.collect(base)

    def test_the_producer_shape_keeps_evidence_applied_evidence_and_the_link(self):
        with tempfile.TemporaryDirectory() as base:
            ctx = helpers.run842_ctx(base)
            got = clarcol.collect(ctx.feature_dir)
        item = got['items'][0]
        self.assertEqual(len(item['evidence']), 2)
        self.assertTrue(all(len(t) <= 200 for t in item['evidence']))
        self.assertEqual([k['url'] for k in item['evidence_links']], [item['url']])
        self.assertEqual(len(item['applied']['evidence']), 2)

    def test_plain_strings_and_a_string_applied_evidence_are_tolerated(self):
        got = self.collect({'v': 1, 'items': [{'source_id': 'Q', 'state': 'applied', 'evidence': ['plain', {'kind': 'disposition', 'explanation': 'x' * 400}],
                                                'applied': {'at': '2026-10-16T18:34:25Z', 'evidence': 'one string'}}]})
        item = got['items'][0]
        self.assertEqual(item['evidence'][0], 'plain')
        self.assertEqual(len(item['evidence'][1]), 200)
        self.assertEqual(item['applied']['evidence'], ['one string'])

    def test_an_object_flattens_to_kind_comment_explanation_and_a_bare_url_only_when_nothing_else(self):
        got = self.collect({'v': 1, 'items': [{'source_id': 'Q', 'state': 'pending', 'evidence': [
            {'kind': 'comment', 'comment_id': 7, 'url': 'https://example.test/c7', 'explanation': 'asked'},
            {'kind': 'link', 'url': 'https://example.test/only'}, {'kind': 'x', 'url': 'javascript:alert(1)'}, {}, 5]}]})
        item = got['items'][0]
        self.assertEqual(item['evidence'], ['comment comment 7 asked', 'link https://example.test/only', 'x'])
        self.assertEqual([k['url'] for k in item['evidence_links']], ['https://example.test/c7', 'https://example.test/only'])

    @unittest.skipUnless(VECTOR.is_file(), 'tests/fixtures/clarifications-vector.json is not present')
    def test_the_shared_vector(self):
        vector = json.loads(VECTOR.read_text(encoding='utf-8'))
        got = self.collect(vector['clarifications'])
        want = vector['expect']
        self.assertEqual(got['state'], want['state'])
        shown = [{'source_id': i['source_id'], 'evidence': len(i['evidence']), 'links': len(i['evidence_links']),
                  'applied_evidence': len(i['applied']['evidence']) if i['applied'] else 0} for i in got['items']]
        self.assertEqual(shown, want['items'])
        self.assertTrue(all(len(t) <= 200 for i in got['items'] for t in i['evidence']))
        self.assertTrue(all(k['url'].startswith('https://') for i in got['items'] for k in i['evidence_links']))

    def test_the_v3_decision_carries_evidence_and_links(self):
        with tempfile.TemporaryDirectory() as base:
            report, _ = helpers.run842_report(base, schema='v3')
        decision = next(d for d in report['decisions']['made'] if d['source'] == 'clarification')
        self.assertEqual(len(decision['evidence']), 2)
        self.assertEqual(len(decision['evidence_links']), 1)
        self.assertEqual(validate.validate(report), [])


class BoundedReads(Synthetic):
    def lines(self, n):
        return [self.event(i, 'claim', episode_id=f'ep{i}', claim_id=f'c{i}', at='2026-10-15T09:%02d:00Z' % (i % 60)) for i in range(1, n + 1)]

    def test_a_large_lifecycle_is_read_from_its_tail_within_the_cap(self):
        self.lifecycle(*self.lines(50))
        path = self.feature_dir / 'workflow' / 'lifecycle.jsonl'
        raw = path.read_bytes()
        got = lifecol.collect(self.feature_dir, cap=2000)
        self.assertTrue(got['truncated'])
        self.assertEqual(got['bytes'], len(raw))
        self.assertGreater(len(got['events']), 3)
        self.assertLess(len(got['events']), 50)
        self.assertEqual(got['corrupt'], 0)  # the cut line is dropped, not counted as corrupt
        self.assertEqual({e['event_id'] for e in got['events']} - {f'e{i}' for i in range(1, 51)}, set())
        self.assertIn('e50', {e['event_id'] for e in got['events']})  # the newest events are the ones kept

    def test_the_report_says_older_events_were_not_read_and_the_hash_covers_the_bytes_parsed(self):
        self.lifecycle(*self.lines(50))
        raw = (self.feature_dir / 'workflow' / 'lifecycle.jsonl').read_bytes()
        old = lifecol.READ_CAP
        lifecol.READ_CAP = 2000
        self.addCleanup(setattr, lifecol, 'READ_CAP', old)
        source = next(s for s in self.build()['sources'] if s['name'] == 'workflow-lifecycle')
        self.assertIn('older events not read', source['note'])
        self.assertEqual(source['fingerprint'], hashlib.sha256(raw[-2000:]).hexdigest()[:16])
        self.assertEqual(source['bytes'], len(raw))

    def test_an_oversized_clarifications_file_is_invalid_and_never_parsed(self):
        folder = self.feature_dir / 'workflow'
        folder.mkdir(exist_ok=True)
        (folder / 'clarifications.json').write_text(json.dumps({'v': 1, 'items': [], 'pad': 'x' * 5000}), encoding='utf-8')
        got = clarcol.collect(self.feature_dir, cap=1000)
        self.assertEqual((got['state'], got['truncated'], got['items']), ('invalid', True, []))
        old = clarcol.READ_CAP
        clarcol.READ_CAP = 1000
        self.addCleanup(setattr, clarcol, 'READ_CAP', old)
        source = next(s for s in self.build()['decisions']['sources'] if s['name'] == 'clarification')
        self.assertEqual(source['state'], 'invalid')
        self.assertIn('size cap', source['note'])


class Consistency(Synthetic):
    def test_a_file_that_changes_during_collection_is_flagged_and_the_fingerprint_is_of_the_bytes_parsed(self):
        self.init()
        self.cli('note', 'first')
        before = hashlib.sha256(self.ctx.facts.read_bytes()).hexdigest()[:16]
        real = model_v3_clarcol().collect

        def collect_then_append(feature_dir):
            out = real(feature_dir)
            with open(self.ctx.facts, 'a', encoding='utf-8') as stream:  # a producer appends after facts were parsed
                stream.write('\n')
            return out
        module = model_v3_module()
        module.clarcol.collect = collect_then_append
        self.addCleanup(setattr, module.clarcol, 'collect', real)
        state = {}
        report, _ = model.build_pair(self.ctx, NOW, 1, state)
        facts = next(s for s in report['sources'] if s['name'] == 'facts')
        self.assertEqual((facts['fingerprint'], facts['consistent']), (before, False))
        self.assertTrue(report['collection']['dirty'])
        self.assertEqual(report['collection']['inconsistent_sources'], ['facts'])
        self.assertTrue(state['dirty'])  # the refresh that runs next will not certify these bytes
        self.assertTrue(all(s['consistent'] for s in report['sources'] if s['name'] != 'facts'))

    def test_a_file_read_twice_with_different_bytes_is_inconsistent(self):
        self.put('checkpoint.json', {'feature': 'specs/001-demo', 'status': 'in-progress', 'generation': 1, 'receipts': {}})
        module = model_v3_module()
        real = module._raw_receipts

        def rewrite_then_read(ctx):
            (self.feature_dir / 'workflow' / 'checkpoint.json').write_text(
                json.dumps({'feature': 'specs/001-demo', 'status': 'in-progress', 'generation': 2, 'receipts': {}, 'pad': 'longer'}), encoding='utf-8')
            return real(ctx)
        module._raw_receipts = rewrite_then_read
        self.addCleanup(setattr, module, '_raw_receipts', real)
        report = model.build(self.ctx, NOW, 1, {}, schema='v3')
        checkpoint = next(s for s in report['sources'] if s['name'] == 'workflow-checkpoint')
        self.assertFalse(checkpoint['consistent'])

    def test_a_quiet_build_is_consistent_and_hashes_what_it_read(self):
        self.put('checkpoint.json', {'feature': 'specs/001-demo', 'status': 'in-progress', 'generation': 4, 'receipts': {}})
        raw = (self.feature_dir / 'workflow' / 'checkpoint.json').read_bytes()
        report = self.build()
        self.assertTrue(all(s['consistent'] for s in report['sources']))
        self.assertFalse(report['collection']['dirty'])
        checkpoint = next(s for s in report['sources'] if s['name'] == 'workflow-checkpoint')
        self.assertEqual((checkpoint['fingerprint'], checkpoint['generation'], checkpoint['bytes']),
                         (hashlib.sha256(raw).hexdigest()[:16], 4, len(raw)))


def model_v3_module():
    from sanduq_progress import model_v3
    return model_v3


def model_v3_clarcol():
    return model_v3_module().clarcol


class MarkdownTasks(unittest.TestCase):
    def test_the_v3_export_lists_tasks_by_phase_with_workstream_and_state(self):
        with tempfile.TemporaryDirectory() as base:
            report, _ = helpers.run842_report(base, schema='v3')
        text = render_md.render(report)
        self.assertIn('\n## Tasks\n', text)
        lines = [l for l in text.splitlines() if l.startswith('- [x] T') or l.startswith('- [ ] T')]
        self.assertEqual(len(lines), 23)
        self.assertTrue(all(l.endswith(', done') for l in lines))
        self.assertTrue(any(' - Workstream A, done' in l for l in lines))
        self.assertTrue(any(' - Shared, done' in l for l in lines))
        self.assertIn('### ', text.split('\n## Tasks\n')[1].split('\n## ')[0])  # grouped under phase headings


class MarkdownTasksStates(Synthetic):
    def test_open_tasks_show_their_state(self):
        self.init()
        self.cli('block', 'T003', '--by', 'ext:"vendor"')
        self.ledger(self.attempt('live', identity='specs/001-demo/T002', status='running', ended=None))
        text = render_md.render(self.build())
        self.assertRegex(text, r'- \[ \] T003 .* - Shared, blocked')
        self.assertRegex(text, r'- \[ \] T002 .* - Shared, active')
        self.assertRegex(text, r'- \[ \] T004 .* - Shared, waiting')


class HostileIds(Synthetic):
    def test_untrusted_ids_that_look_like_object_properties_project_validate_and_round_trip(self):
        ids = ['constructor', '__proto__', 'hasOwnProperty', 'toString']
        self.ledger(*[self.attempt(i, status='failed', identity='specs/001-demo/stage:' + i, claim_id='c-' + i) for i in ids])
        self.lifecycle(*[self.event(n, 'claim', stage=i, episode_id='ep-' + i, claim_id='c-' + i, delegation_run_ids=[i], at='2026-10-15T09:0%d:00Z' % n)
                         for n, i in enumerate(ids, 1)])
        report = self.build()
        self.assertEqual(validate.validate(report), [])
        self.assertEqual({r['run_id'] for r in report['runs']}, set(ids))
        self.assertEqual({s['id'] for s in report['stages']} & set(ids), set(ids))
        self.assertEqual(json.loads(json.dumps(report))['runs'][0]['run_id'], '__proto__')


class ThemeRepublish(helpers.Project):
    def shown(self, ctx):
        text = (ctx.view / 'data.js').read_text(encoding='utf-8')
        return json.loads(text[len('window.__SANDUQ_PROGRESS__ = '):].rstrip().rstrip(';'))['schema']

    def test_layout_republishes_data_js_for_every_initialised_report_and_only_those(self):
        from sanduq_progress.paths import Ctx
        self.init()
        other = self.root / 'specs' / '002-other'
        other.mkdir()
        (other / 'tasks.md').write_text((self.feature_dir / 'tasks.md').read_text(encoding='utf-8'), encoding='utf-8')
        self.assertEqual(self.cli('init', '--feature', 'specs/002-other')[0], 0)
        third = self.root / 'specs' / '003-never'
        third.mkdir()
        two = Ctx(self.root, 'specs/002-other')
        self.assertEqual((self.shown(self.ctx), self.shown(two)), ('sanduq.progress.v3',) * 2)
        self.assertEqual(self.cli('theme', '--layout', 'classic'), (0, 'progress: theme layout classic'))
        self.assertEqual((self.shown(self.ctx), self.shown(two)), ('sanduq.progress.v2',) * 2)
        self.assertEqual(self.stored_report()['schema'], 'sanduq.progress.v3')
        self.assertFalse((third / 'progress').exists())
        self.assertEqual(self.cli('theme', '--layout', 'timeline')[0], 0)
        self.assertEqual((self.shown(self.ctx), self.shown(two)), ('sanduq.progress.v3',) * 2)

    def test_a_preset_change_does_not_rebuild_anything(self):
        self.init()
        before = self.ctx.report.read_bytes()
        self.assertEqual(self.cli('theme', '--preset', 'cobalt')[0], 0)
        self.assertEqual(self.ctx.report.read_bytes(), before)

    def test_a_busy_report_lock_is_reported_not_silently_skipped(self):
        from sanduq_progress.lock import Lock
        self.init()
        hold = Lock(self.ctx.lock, retries=0, delay=0).acquire()
        self.addCleanup(hold.release)
        code, line = self.cli('theme', '--layout', 'classic')
        self.assertEqual(code, 0)
        self.assertIn('layout classic', line)
        self.assertIn('another progress command is running', line)
        self.assertIn('run progress refresh', line)


class VersionAndDocs(unittest.TestCase):
    def test_the_package_version_is_the_skill_version(self):
        from sanduq_progress import VERSION
        self.assertEqual(VERSION, '1.2.0')


if __name__ == '__main__':
    unittest.main()
