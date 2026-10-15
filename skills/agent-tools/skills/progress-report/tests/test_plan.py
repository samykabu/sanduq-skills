"""Plan mode: any Markdown checklist is a task list. No Spec Kit anywhere in these tests."""
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import helpers
from helpers import FIXTURES, PLAN_MD, PlanProject, Project
from sanduq_progress import model, render_md
from sanduq_progress.collect import plan as plancol
from sanduq_progress.paths import Ctx, ProgressError, find_root, normalise_plan_dir, project_dir, resolve_target

NOW = datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc)
GOLDEN = FIXTURES / 'expected_plan_report.json'


def ids(parsed, stored=()):
    plancol.assign(parsed['items'], list(stored))
    return [(i['id'], i['title']) for i in parsed['items']]


class ParsePlan(unittest.TestCase):
    def test_headings_become_phases_and_the_first_h1_is_the_title(self):
        parsed = plancol.parse(PLAN_MD)
        self.assertEqual(parsed['title'], 'Launch plan')
        self.assertEqual([(i['phase'], i['done']) for i in parsed['items']],
                         [('Backend', True), ('Backend', False), ('Backend', False), ('Frontend', False), ('Frontend', True)])

    def test_explicit_ids_are_kept_and_the_rest_get_p_ids(self):
        got = ids(plancol.parse(PLAN_MD))
        self.assertEqual([i for i, _ in got], ['P001', 'P002', 'T010', 'P003', 'P004'])

    def test_depends_and_after_are_honoured_and_decoys_are_not_items(self):
        got = {t['id']: t for t in self.collect(PLAN_MD)['tasks']}
        self.assertEqual(got['P002']['depends_on'], ['P001'])
        self.assertEqual(got['T010']['depends_on'], ['P002'])  # P099 sits in a code span and does not exist
        self.assertNotIn('Decoy', ' '.join(t['title'] for t in got.values()))
        self.assertEqual(len(got), 5)
        self.assertTrue(got['P003']['parallel'])
        self.assertEqual(got['P003']['title'], 'Build the UI')

    def test_unknown_and_self_references_are_dropped(self):
        got = self.collect('- [ ] T001 One (depends on T001, T404, T002)\n- [ ] T002 Two\n')['tasks']
        self.assertEqual(got[0]['depends_on'], ['T002'])

    def test_markdown_dialects(self):
        got = ids(plancol.parse('* [ ] **US3**: Bold id\n+ [x] T7) Paren id\n- [ ] L1 reserved shape\n  - [ ] nested item\n'))
        self.assertEqual([i for i, _ in got], ['US3', 'T7', 'P001', 'P002'])

    def test_duplicate_explicit_ids_keep_the_first(self):
        self.assertEqual([t['id'] for t in self.collect('- [ ] T1 a\n- [ ] T1 b\n')['tasks']], ['T1'])

    def collect(self, text):
        parsed = plancol.parse(text)
        ids_, _ = plancol.assign(parsed['items'], [])
        known = {i['id'] for i in parsed['items']}
        return {'tasks': [{'id': i['id'], 'title': i['title'], 'parallel': i['parallel'],
                           'depends_on': [r for r in i['refs'] if r in known and r != i['id']]} for i in parsed['items']]}


class StableIds(unittest.TestCase):
    def assign(self, text, stored=(), floor=0):
        parsed = plancol.parse(text)
        mapping, highest = plancol.assign(parsed['items'], list(stored), floor)
        return {i['title']: i['id'] for i in parsed['items']}, mapping, highest

    BASE = '- [ ] Write the parser\n- [ ] Add the CLI verbs\n- [ ] Publish the docs\n'

    def test_first_assignment_follows_plan_order(self):
        by_title, mapping, highest = self.assign(self.BASE)
        self.assertEqual(list(by_title.values()), ['P001', 'P002', 'P003'])
        self.assertEqual(highest, 3)

    def test_reordering_and_checking_off_keep_ids(self):
        first, mapping, _ = self.assign(self.BASE)
        again, _, _ = self.assign('- [x] Publish the docs\n- [ ] Write the parser\n- [x] Add the CLI verbs\n', mapping)
        self.assertEqual(again, {'Publish the docs': first['Publish the docs'], 'Write the parser': first['Write the parser'],
                                 'Add the CLI verbs': first['Add the CLI verbs']})

    def test_inserting_an_item_does_not_shift_the_others(self):
        first, mapping, _ = self.assign(self.BASE)
        edited, _, highest = self.assign('- [ ] Brand new first step\n' + self.BASE, mapping)
        self.assertEqual({k: v for k, v in edited.items() if k != 'Brand new first step'}, first)
        self.assertEqual(edited['Brand new first step'], 'P004')
        self.assertEqual(highest, 4)

    def test_a_small_rewording_keeps_the_id_and_a_big_one_does_not(self):
        first, mapping, _ = self.assign(self.BASE)
        edited, _, _ = self.assign('- [ ] Write the parser and tests\n- [ ] Add the CLI verbs\n- [ ] Totally different thing now\n', mapping)
        self.assertEqual(edited['Write the parser and tests'], first['Write the parser'])
        self.assertEqual(edited['Totally different thing now'], 'P004')

    def test_numbers_of_deleted_items_are_never_reused(self):
        _, mapping, highest = self.assign(self.BASE)
        _, mapping, highest = self.assign('- [ ] Write the parser\n- [ ] Add the CLI verbs\n', mapping, highest)  # P003 deleted
        added, _, _ = self.assign('- [ ] Write the parser\n- [ ] Add the CLI verbs\n- [ ] Ship it somewhere\n', mapping, highest)
        self.assertEqual(added['Ship it somewhere'], 'P004')

    def test_identical_texts_match_in_order(self):
        first, mapping, _ = self.assign('- [ ] Review\n- [ ] Review\n')
        parsed = plancol.parse('- [ ] Review\n- [ ] Review\n- [ ] Review\n')
        plancol.assign(parsed['items'], mapping)
        self.assertEqual([i['id'] for i in parsed['items']], ['P001', 'P002', 'P003'])

    def test_an_explicit_id_never_collides_with_an_auto_id(self):
        parsed = plancol.parse('- [ ] P001 Explicit\n- [ ] Auto one\n')
        plancol.assign(parsed['items'], [])
        self.assertEqual([i['id'] for i in parsed['items']], ['P001', 'P002'])


class PlanInit(PlanProject):
    def tracked_files(self):
        out = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'], cwd=self.root, capture_output=True,
                             text=True, check=True).stdout
        return sorted(out.split())

    def test_init_without_spec_kit_creates_the_layout_and_never_a_specify_dir(self):
        before = hashlib.sha256(self.plan_path.read_bytes()).hexdigest()
        self.init_plan()
        base = self.root / '.progress' / 'plan'
        self.assertTrue((base / 'facts.jsonl').is_file() and (base / 'plan.json').is_file())
        self.assertTrue((base / '.view' / 'index.html').is_file() and (base / '.view' / 'data.js').is_file())
        self.assertFalse((self.root / '.specify').exists() or (self.root / 'specs').exists())
        self.assertEqual(project_dir(self.root), self.root / '.progress' / '.project')
        self.assertEqual(before, hashlib.sha256(self.plan_path.read_bytes()).hexdigest())  # the plan is read, never written

    def test_view_host_and_project_state_are_git_ignored_and_facts_are_tracked(self):
        self.init_plan()
        self.bind()
        self.cli('lane', 'L1', '--tasks', 'P001', '--owner', 'me')
        files = self.tracked_files()
        self.assertIn('.progress/plan/facts.jsonl', files)
        self.assertIn('.progress/plan/plan.json', files)
        self.assertFalse([f for f in files if '/.view/' in f or '/.host/' in f or 'bindings' in f or f.endswith('.lock')], files)

    def test_name_defaults_to_the_slugified_file_stem_and_name_overrides(self):
        (self.root / 'docs' / 'My Big_Plan v2.md').write_text('- [ ] one\n', encoding='utf-8')
        self.init_plan(plan='docs/My Big_Plan v2.md')
        self.assertEqual(self.ctx.feature, '.progress/my-big-plan-v2')
        self.init_plan('--name', 'launch')
        self.assertEqual(self.ctx.feature, '.progress/launch')

    def test_reinit_is_idempotent_and_keeps_facts(self):
        self.init_plan()
        self.cli('note', 'kept')
        self.init_plan()
        self.assertEqual(len(self.ctx.facts.read_text(encoding='utf-8').splitlines()), 1)

    def test_another_plan_cannot_take_an_existing_report_name(self):
        self.init_plan()
        (self.root / 'docs' / 'other.md').write_text('- [ ] x\n', encoding='utf-8')
        code, line = self.cli('init', '--plan', 'docs/other.md', '--name', 'plan')
        self.assertEqual((code, line.split()[:3]), (3, ['progress:', 'error', 'PROGRESS_PLAN_EXISTS']))

    def test_missing_plan_file_is_a_one_line_error(self):
        code, line = self.cli('init', '--plan', 'docs/none.md')
        self.assertEqual((code, line.split()[:3], line.count('\n')), (2, ['progress:', 'error', 'PROGRESS_PLAN_MISSING'], 0))

    def test_name_and_dir_need_a_plan_and_a_valid_name(self):
        self.assertEqual(self.cli('init', '--name', 'x')[0], 2)
        code, line = self.cli('init', '--plan', 'docs/plan.md', '--name', 'Bad Name')
        self.assertEqual((code, line.split()[2]), (2, 'PROGRESS_USAGE'))

    def test_plan_and_feature_together_are_refused(self):
        code, line = self.cli('init', '--plan', 'docs/plan.md', '--feature', 'specs/001-x')
        self.assertEqual((code, line.split()[2]), (2, 'PROGRESS_USAGE'))


class DirConfinement(PlanProject):
    def test_dir_inside_the_repo_is_accepted_and_registered(self):
        self.init_plan('--dir', 'docs/progress/launch')
        self.assertEqual(self.ctx.feature, 'docs/progress/launch')
        self.assertTrue((self.root / 'docs/progress/launch/facts.jsonl').is_file())
        self.assertEqual(json.loads((self.root / '.progress/plans.json').read_text())['dirs'], ['docs/progress/launch'])
        self.assertIn('docs/progress/launch/.view/', (self.root / '.git/info/exclude').read_text())
        self.assertEqual(self.cli('status', '--plan', 'plan')[0], 0)  # found through the registry, by name

    def test_dir_outside_the_repo_or_with_dot_components_is_refused(self):
        outside = Path(self.tmp.name).parent / 'outside-plan-dir'
        for value in ('../escape', 'docs/../../escape', str(outside), '.', '.git/plan', 'specs/001-x', '/'):
            with self.subTest(value=value):
                code, line = self.cli('init', '--plan', 'docs/plan.md', '--dir', value)
                self.assertEqual((code, line.split()[:2]), (2, ['progress:', 'error']), line)
        self.assertFalse(outside.exists())

    def test_a_symlinked_dir_cannot_move_writes_outside_the_repo(self):
        outside = Path(self.tmp.name).parent / (Path(self.tmp.name).name + '-linked')
        outside.mkdir()
        self.addCleanup(lambda: [p.unlink() for p in outside.glob('*') if p.is_file()] and outside.rmdir() or None)
        try:
            os.symlink(outside, self.root / 'link', target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        code, line = self.cli('init', '--plan', 'docs/plan.md', '--dir', 'link/report')
        self.assertEqual(code, 2, line)
        self.assertEqual(list(outside.iterdir()), [])

    def test_normalise_plan_dir(self):
        self.assertEqual(normalise_plan_dir(self.root, 'a/b'), 'a/b')
        self.assertEqual(normalise_plan_dir(self.root, str(self.root / 'a' / 'b')), 'a/b')
        for bad in ('', '..', 'a/../b', '.git', 'specs/x', 'C:/x'):
            self.assertIsNone(normalise_plan_dir(self.root, bad), bad)


class ExternalPlan(PlanProject):
    def setUp(self):
        super().setUp()
        self.outside = tempfile.TemporaryDirectory()
        self.addCleanup(helpers.remove_tree, self.outside)
        self.external = Path(self.outside.name).resolve() / 'claude-plan.md'
        self.external.write_text('# Elsewhere\n\n- [x] First thing\n- [ ] Second thing\n', encoding='utf-8')

    def test_external_plan_is_read_only_and_never_recorded_by_absolute_path_in_tracked_files(self):
        before = hashlib.sha256(self.external.read_bytes()).hexdigest()
        self.init_plan(plan=str(self.external))
        self.assertEqual(self.ctx.feature, '.progress/claude-plan')
        info = json.loads(self.ctx.plan_file.read_text(encoding='utf-8'))
        self.assertEqual(info['source'], 'external:claude-plan.md')
        self.cli('lane', 'L1', '--tasks', 'P001', '--owner', 'me')
        self.cli('note', 'note about P002', '--target', 'P002')
        self.assertEqual(self.cli('status')[1].split(',')[0], 'progress: 1/2 tasks')
        for path in (self.ctx.plan_file, self.ctx.facts, self.root / '.progress' / 'plans.json'):
            if path.exists():
                text = path.read_text(encoding='utf-8')
                self.assertNotIn(self.outside.name, text, path.name)
                self.assertNotIn(self.outside.name.replace('\\', '/'), text, path.name)
        local = json.loads(self.ctx.plan_source_file.read_text(encoding='utf-8'))
        self.assertEqual(Path(local['path']), self.external)  # the absolute path lives only in the ignored .host
        self.assertEqual(before, hashlib.sha256(self.external.read_bytes()).hexdigest())
        ignored = subprocess.run(['git', 'check-ignore', '-q', '.progress/claude-plan/.host/plan-source.json'], cwd=self.root).returncode
        self.assertEqual(ignored, 0)

    def test_external_plan_changes_are_followed(self):
        self.init_plan(plan=str(self.external))
        self.external.write_text('# Elsewhere\n\n- [x] First thing\n- [x] Second thing\n', encoding='utf-8')
        self.assertTrue(self.cli('status')[1].startswith('progress: 2/2 tasks'))

    def test_missing_external_source_gives_an_empty_plan_not_a_crash(self):
        self.init_plan(plan=str(self.external))
        self.external.unlink()
        self.assertTrue(self.cli('status')[1].startswith('progress: 0/0 tasks'))

    def test_plan_path_resolves_to_its_report(self):
        self.init_plan(plan=str(self.external))
        self.assertEqual(self.cli('status', '--plan', str(self.external))[0], 0)


class Targets(PlanProject):
    def setUp(self):
        super().setUp()
        (self.root / 'docs' / 'second.md').write_text('- [ ] A\n- [x] B\n', encoding='utf-8')

    def test_the_one_active_plan_is_used_without_a_flag(self):
        self.init_plan()
        self.assertTrue(self.cli('status')[1].startswith('progress: 2/5 tasks'))

    def test_two_plans_need_a_flag_and_the_error_lists_both_on_one_line(self):
        self.init_plan()
        self.init_plan(plan='docs/second.md')
        code, line = self.cli('status')
        self.assertEqual((code, line.count('\n')), (2, 0))
        self.assertTrue(line.startswith('progress: error PROGRESS_NO_FEATURE'), line)
        self.assertIn('plan:plan', line)
        self.assertIn('plan:second', line)

    def test_plan_flag_takes_a_name_a_report_dir_or_the_plan_file(self):
        self.init_plan()
        self.init_plan(plan='docs/second.md')
        self.assertTrue(self.cli('status', '--plan', 'second')[1].startswith('progress: 1/2 tasks'))
        self.assertTrue(self.cli('status', '--plan', '.progress/plan')[1].startswith('progress: 2/5 tasks'))
        self.assertTrue(self.cli('status', '--plan', 'docs/second.md')[1].startswith('progress: 1/2 tasks'))
        self.assertTrue(self.cli('status', '--plan', str(self.root / 'docs' / 'plan.md'))[1].startswith('progress: 2/5 tasks'))

    def test_unknown_plan_lists_the_candidates(self):
        self.init_plan()
        code, line = self.cli('status', '--plan', 'nope')
        self.assertEqual(code, 2)
        self.assertIn('candidates: plan:plan', line)

    def test_no_report_at_all_keeps_the_original_hint(self):
        code, line = self.cli('status')
        self.assertEqual((code, line), (2, 'progress: error PROGRESS_NO_FEATURE pass --feature specs/<dir>'))

    def test_plan_and_feature_together_are_a_usage_error(self):
        self.init_plan()
        code, line = self.cli('status', '--plan', 'plan', '--feature', 'specs/001-x')
        self.assertEqual((code, line.split()[2]), (2, 'PROGRESS_USAGE'))

    def test_every_verb_accepts_the_plan_flag(self):
        self.init_plan()
        self.init_plan(plan='docs/second.md')
        for args in (('lane', 'L1', '--tasks', 'P001'), ('block', 'P002', '--by', 'P001'), ('note', 'hello'),
                     ('decide', 'ask', 'Which?', '--options', 'a,b'), ('refresh',), ('status', '--json'), ('export',)):
            with self.subTest(verb=args[0]):
                code, line = self.cli(args[0], '--plan', 'second', *args[1:])
                self.assertEqual(code, 0, line)
        self.assertEqual(len((self.root / '.progress/second/facts.jsonl').read_text().splitlines()), 4)
        self.assertEqual((self.root / '.progress/plan/facts.jsonl').read_text(), '')

    def test_spec_kit_feature_and_plan_side_by_side(self):
        (self.root / '.specify').mkdir()
        feature = self.root / 'specs' / '001-demo'
        feature.mkdir(parents=True)
        (feature / 'tasks.md').write_text((FIXTURES / 'tasks.md').read_text(encoding='utf-8'), encoding='utf-8')
        self.assertEqual(self.cli('init', '--feature', 'specs/001-demo')[0], 0)
        self.init_plan()
        code, line = self.cli('status')
        self.assertIn('plan:plan', line)
        self.assertIn('specs/001-demo', line)
        self.assertTrue(self.cli('status', '--feature', 'specs/001-demo')[1].startswith('progress: 2/5 tasks'))
        self.assertEqual(project_dir(self.root), self.root / '.specify' / 'progress')

    def test_resolve_target_api(self):
        self.init_plan()
        self.assertEqual(resolve_target(self.root), '.progress/plan')
        with self.assertRaises(ProgressError):
            resolve_target(self.root, plan='plan', feature='specs/x')

    def test_find_root_recognises_a_progress_only_project(self):
        with tempfile.TemporaryDirectory() as bare:
            (Path(bare) / '.progress').mkdir()
            (Path(bare) / 'sub').mkdir()
            self.assertEqual(find_root(Path(bare) / 'sub'), Path(bare).resolve())


class PlanVerbs(PlanProject):
    def test_lane_block_note_and_decision_use_plan_ids(self):
        self.init_plan()
        self.assertEqual(self.cli('lane', 'L1', '--tasks', 'P001-P002,T010', '--owner', 'me')[1], 'progress: L1 open 3 tasks')
        self.assertEqual(self.cli('block', 'P003', '--by', 'T010')[1], 'progress: B1 open P003 by T010')
        self.assertEqual(self.cli('block', 'T010', '--by', 'P002')[0], 0)
        self.assertEqual(self.cli('note', 'x', '--target', 'P004')[0], 0)
        self.assertEqual(self.cli('block', 'banana', '--by', 'P001')[0], 2)
        self.assertEqual(self.cli('decide', 'ask', 'Which?', '--options', 'a,b')[1], 'progress: D1 pending')
        report = json.loads(self.cli('status', '--json')[1])
        lane = next(l for l in report['lanes'] if l['id'] == 'L1')
        self.assertEqual(lane['tasks']['done'], ['P001'])
        self.assertEqual(report['tasks']['P003']['depends_on'], [])
        self.assertEqual(report['summary']['blocked'], 2)

    def test_editing_the_plan_keeps_lane_assignments_attached(self):
        self.init_plan()
        self.cli('lane', 'L1', '--tasks', 'P002', '--owner', 'me')
        self.write_plan(PLAN_MD.replace('- [x] Set up the database', '- [ ] A new first item\n- [x] Set up the database'))
        report = json.loads(self.cli('status', '--json')[1])
        self.assertEqual(report['tasks']['P002']['title'], 'Build the API')
        self.assertEqual(report['tasks']['P002']['lane'], 'L1')
        self.assertEqual(report['tasks']['P005']['title'], 'A new first item')
        self.cli('refresh')
        stored = json.loads(self.ctx.plan_file.read_text(encoding='utf-8'))
        self.assertEqual((stored['next'], 'P005' in [i['id'] for i in stored['ids']]), (5, True))

    def test_export_says_plan(self):
        self.init_plan()
        text = self.cli('export')[1]
        self.assertTrue(text.startswith('# Launch plan'))
        self.assertIn('Plan `plan`', text)

    def test_theme_lives_in_the_progress_project_dir_without_spec_kit(self):
        self.init_plan()
        code, line = self.cli('theme', '--preset', 'emerald')
        self.assertEqual((code, line), (0, 'progress: theme emerald'))
        self.assertTrue((self.root / '.progress' / '.project' / 'theme.json').is_file())
        self.assertIn('--accent:#0f8a64', (self.ctx.view / 'theme.css').read_text(encoding='utf-8'))
        self.assertFalse((self.root / '.specify').exists())


class PlanHooks(PlanProject):
    def test_a_bound_session_reports_model_and_children_for_a_plan(self):
        self.init_plan()
        self.bind()
        self.hook('pre_tool_use', self.payload('claude_pre_task.json'), now='2026-10-15T12:10:00Z')
        self.hook('post_tool_use', self.payload('claude_post_task.json'), now='2026-10-15T12:12:00Z')
        snaps = list(self.ctx.host_dir.glob('claude-*.json'))
        self.assertEqual(len(snaps), 1)
        self.assertEqual(self.report()['feature']['mode'], 'plan')
        self.assertEqual(self.snap()['children']['toolu_01TASK']['status'], 'done')
        self.cli('refresh')
        self.assertIn('C1', [lane['id'] for lane in self.report()['lanes']])

    def test_unbound_sessions_are_dropped_and_logged_in_the_progress_project_dir(self):
        self.init_plan()
        self.hook('post_tool_use', self.payload('claude_post_task.json', session_id='stranger'))
        self.assertIn('unbound', (self.root / '.progress' / '.project' / 'diagnostics.log').read_text())
        self.assertFalse((self.root / '.specify').exists())

    def test_fast_entry_exits_silently_in_a_project_without_progress(self):
        bare = tempfile.TemporaryDirectory()
        self.addCleanup(helpers.remove_tree, bare)
        hook = Path(helpers.SCRIPTS) / 'hook.py'
        result = subprocess.run(['python', str(hook), 'post_tool_use'], input=json.dumps({'session_id': 'x'}), capture_output=True,
                                text=True, cwd=bare.name, env={**os.environ, 'SANDUQ_PROGRESS_ROOT': bare.name})
        self.assertEqual((result.returncode, result.stdout), (0, ''))
        self.assertEqual(os.listdir(bare.name), [])


class PlanProjection(PlanProject):
    def scenario(self):
        self.init_plan()
        self.cli('refresh')
        self.bind()
        self.hook('pre_tool_use', self.payload('claude_pre_task.json'), now='2026-10-15T12:10:00Z')
        self.hook('post_tool_use', self.payload('claude_post_task.json'), now='2026-10-15T12:12:00Z')
        self.cli('lane', 'L1', '--tasks', 'P002,T010', '--label', 'Backend', '--owner', 'me', '--harness', 'claude')
        self.cli('block', 'T010', '--by', 'P002')
        self.cli('note', 'waiting on review', '--target', 'P002')

    def test_golden_plan_projection(self):
        self.scenario()
        built = model.build(self.ctx, NOW, 3, json.loads(self.ctx.state.read_text()))
        built = {**built, 'generated_at': '<now>', 'rev': 0}
        if os.environ.get('UPDATE_GOLDEN'):
            GOLDEN.write_text(json.dumps(built, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        self.assertEqual(built, json.loads(GOLDEN.read_text(encoding='utf-8')))

    def test_plan_mode_adds_only_mode_and_source_to_the_feature_block(self):
        self.scenario()
        feature = self.report()['feature']
        self.assertEqual((feature['mode'], feature['source'], feature['id'], feature['dir']),
                         ('plan', 'docs/plan.md', 'plan', '.progress/plan'))
        self.assertEqual(feature['title'], 'Launch plan')
        self.assertFalse(feature['workflow'])

    def test_markdown_export_of_a_plan_projection(self):
        self.scenario()
        text = render_md.render(self.report())
        self.assertIn('- [x] P001 Set up the database', text)
        self.assertIn('### Frontend', text)


class SpecKitUnchanged(Project):
    def test_feature_projection_has_no_plan_fields(self):
        self.init()
        feature = self.report()['feature']
        self.assertNotIn('mode', feature)
        self.assertNotIn('source', feature)
        self.assertEqual(project_dir(self.root), self.root / '.specify' / 'progress')


if __name__ == '__main__':
    unittest.main()
