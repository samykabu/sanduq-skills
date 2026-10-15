"""Regression tests for the skill review (cycle 1): plan privacy, git exclusions, report ownership, installer safety."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import helpers
from helpers import PlanProject
from sanduq_progress import hooks_install, paths
from sanduq_progress.collect import plan as plancol
from sanduq_progress.lock import Lock
from test_hooks_install import UNRELATED, HooksCase


def ignored(root, rel):
    return subprocess.run(['git', 'check-ignore', '-q', '--', rel], cwd=root).returncode == 0


class PlanPrivacy(PlanProject):
    """A1/F8: the tracked plan.json holds ids and fingerprints, never item text."""
    SECRET_PLAN = '# P\n\n- [ ] rotate token=abcdef123456789 in /home/alice/private/key.pem\n- [ ] Write the parser\n'

    def test_tracked_plan_json_has_no_item_text_and_the_ignored_host_file_has_it(self):
        self.write_plan(self.SECRET_PLAN)
        self.init_plan()
        tracked = self.ctx.plan_file.read_text(encoding='utf-8')
        for leak in ('abcdef123456789', 'alice', 'key.pem', 'parser'):
            self.assertNotIn(leak, tracked)
        entries = json.loads(tracked)['ids']
        self.assertEqual([sorted(e) for e in entries], [['fp', 'id']] * 2)
        self.assertTrue((self.ctx.host_dir / 'plan-keys.json').is_file())
        self.assertTrue(ignored(self.root, f'{self.ctx.feature}/.host/plan-keys.json'))

    def titles(self):
        return {t['title']: t['id'] for t in plancol.collect(self.ctx)['tasks']}

    def test_ids_stay_stable_across_rewording_with_local_text_and_across_equal_text_without_it(self):
        self.write_plan('- [ ] Write the parser\n- [ ] Add the CLI verbs\n')
        self.init_plan()
        self.write_plan('- [ ] Add the CLI verbs\n- [ ] Write the parser and tests\n')
        self.cli('refresh')
        self.assertEqual(self.titles(), {'Add the CLI verbs': 'P002', 'Write the parser and tests': 'P001'})
        (self.ctx.host_dir / 'plan-keys.json').unlink()  # a fresh clone: fingerprints only
        self.write_plan('- [ ] Write the parser and tests\n- [ ] Add the CLI verbs\n')
        self.cli('refresh')
        self.assertEqual(self.titles(), {'Add the CLI verbs': 'P002', 'Write the parser and tests': 'P001'})

    def test_a_plan_json_from_before_fingerprints_is_migrated_without_the_text(self):
        self.init_plan()
        info = json.loads(self.ctx.plan_file.read_text(encoding='utf-8'))
        info['ids'] = [{'id': 'P001', 'key': 'set up the database'}]
        info['next'] = 1
        self.ctx.plan_file.write_text(json.dumps(info), encoding='utf-8')
        self.cli('refresh')
        self.assertNotIn('set up the database', self.ctx.plan_file.read_text(encoding='utf-8'))


class GitExclusions(PlanProject):
    def test_glob_characters_in_a_custom_dir_are_escaped(self):
        self.assertEqual(paths.glob_escape('reports/[review]'), 'reports/\\[review\\]')
        self.assertEqual(paths.glob_escape('a*b?c'), 'a\\*b\\?c')
        self.assertEqual(paths.glob_escape('#x'), '\\#x')
        self.assertEqual(paths.glob_escape('!x'), '\\!x')

    def test_init_with_a_bracketed_dir_ignores_view_and_host(self):
        self.init_plan('--dir', 'reports/[review]')
        self.assertTrue(ignored(self.root, 'reports/[review]/.host/plan-source.json'))
        self.assertTrue(ignored(self.root, 'reports/[review]/.view/data.js'))
        self.assertFalse(ignored(self.root, 'reports/r/.view/data.js'))

    def test_init_still_lists_no_local_file_when_the_exclusions_do_not_take_effect(self):
        # the nested .gitignore inside .host/ and .view/ keeps them ignored even when info/exclude matches nothing
        from test_skill_review_c3 import local_leaks
        real = paths.glob_escape
        paths.glob_escape = lambda path: path
        self.addCleanup(setattr, paths, 'glob_escape', real)
        self.init_plan('--dir', 'reports/[review]')
        self.cli('refresh')
        self.assertEqual(local_leaks(self.root), [])

    def test_nothing_under_specs_is_a_report_directory(self):
        for value in ('specs/001-x/progress', 'specs/x', 'Specs/y/z'):
            code, line = self.cli('init', '--plan', 'docs/plan.md', '--dir', value)
            self.assertEqual((code, line.split()[2]), (2, 'PROGRESS_USAGE'), value)
        self.assertFalse((self.root / 'specs').exists())


class Ownership(PlanProject):
    def external(self, name='plan.md', text='- [ ] one\n- [ ] two\n'):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(helpers.remove_tree, outside)
        path = Path(outside.name).resolve() / name
        path.write_text(text, encoding='utf-8')
        return path

    def test_a_different_external_plan_with_the_same_name_is_refused_unless_rebound(self):
        first, second = self.external(), self.external()
        self.init_plan(plan=str(first))
        code, line = self.cli('init', '--plan', str(second))
        self.assertEqual((code, line.split()[2]), (3, 'PROGRESS_PLAN_EXISTS'), line)
        self.assertEqual(Path(json.loads(self.ctx.plan_source_file.read_text())['path']), first)
        self.assertEqual(self.cli('init', '--plan', str(first))[0], 0)  # the same file is fine
        code, line = self.cli('init', '--plan', str(second), '--rebind')
        self.assertEqual(code, 0, line)
        self.assertEqual(Path(json.loads(self.ctx.plan_source_file.read_text())['path']), second)

    def test_a_dir_holding_another_tools_plan_json_is_never_overwritten(self):
        (self.root / 'docs' / 'plan.json').write_text('{"name": "mine", "x": 1}', encoding='utf-8')
        code, line = self.cli('init', '--plan', 'docs/plan.md', '--dir', 'docs')
        self.assertEqual((code, line.split()[2]), (3, 'PROGRESS_DIR_CONFLICT'), line)
        self.assertEqual((self.root / 'docs' / 'plan.json').read_text(encoding='utf-8'), '{"name": "mine", "x": 1}')
        self.assertFalse((self.root / 'docs' / 'facts.jsonl').exists() or (self.root / 'docs' / '.view').exists())
        (self.root / 'docs' / 'plan.json').write_text('not json', encoding='utf-8')
        self.assertEqual(self.cli('init', '--plan', 'docs/plan.md', '--dir', 'docs')[0], 3)


class PlanIds(unittest.TestCase):
    def ids(self, text):
        parsed = plancol.parse(text)
        plancol.assign(parsed['items'], [])
        return [(i['id'], i['title']) for i in parsed['items']]

    def test_ordinary_words_that_look_like_ids_are_text(self):
        for word in ('MP3 export', 'GPT-4 integration', 'Q3 goals review', 'A4 print layout', 'ES6 migration'):
            self.assertEqual(self.ids(f'- [ ] {word}\n'), [('P001', word)], word)

    def test_documented_id_forms_are_ids(self):
        got = self.ids('- [ ] T001 a\n- [ ] T-12: b\n- [ ] P003 c\n- [ ] **US3**: d\n- [ ] T4: e\n- [ ] T005) f\n- [ ] AB12. g\n')
        self.assertEqual([i for i, _ in got], ['T001', 'T-12', 'P003', 'US3', 'T4', 'T005', 'AB12'])

    def test_same_words_are_not_dropped_as_duplicates(self):
        got = self.ids('- [ ] MP3 export\n- [ ] MP3 import\n')
        self.assertEqual([t for _, t in got], ['MP3 export', 'MP3 import'])

    def test_a_duplicate_id_is_reported_in_diagnostics_not_dropped(self):
        parsed = plancol.parse('- [ ] T001 a\n- [ ] T001 b\n')
        self.assertEqual((len(parsed['items']), parsed['duplicates']), (2, ['T001']))


class RefreshReadsOnce(PlanProject):
    def test_a_refresh_collects_the_plan_once(self):
        self.init_plan()
        calls = []
        real = plancol._read
        plancol._read = lambda ctx: calls.append(1) or real(ctx)
        self.addCleanup(setattr, plancol, '_read', real)
        self.cli('refresh')
        self.assertEqual(len(calls), 1)


class Installer(HooksCase):
    def test_f1_f2_commands_use_the_braced_variable_and_end_in_exit_zero(self):
        self.cli('hooks', 'install', '--host', 'claude')
        for _, _, command in self.ours(self.read('claude', 'project')):
            self.assertIn('${CLAUDE_PROJECT_DIR}/', command)
            self.assertNotIn('$CLAUDE_PROJECT_DIR', command.replace('${CLAUDE_PROJECT_DIR}', ''))
        self.cli('hooks', 'uninstall', '--host', 'claude')
        self.cli('hooks', 'install', '--host', 'claude', '--scope', 'user')
        for _, _, command in self.ours(self.read('claude', 'user')):
            self.assertTrue(command.endswith('; exit 0'), command)

    @unittest.skipUnless(shutil.which('bash'), 'needs bash')
    def test_a_vanished_script_does_not_block_the_host(self):
        command = f'{sys.executable.replace(chr(92), "/")} "{self.root.as_posix()}/gone/hook.py" stop {hooks_install.TAG}; exit 0'
        self.assertEqual(subprocess.run(['bash', '-c', command], capture_output=True).returncode, 0)

    def test_status_flags_entries_whose_script_is_gone(self):
        self.cli('hooks', 'install', '--host', 'claude', '--scope', 'user')
        self.assertTrue(self.cli('hooks', 'status', '--host', 'claude')[1].startswith('progress: hooks claude project 0/5 user 5/5;'))
        hooks_install.HOOK_SCRIPT.unlink()
        self.assertIn('user 5/5 (5 script missing)', self.cli('hooks', 'status', '--host', 'claude')[1])

    def test_f6_an_unreadable_other_scope_does_not_block_a_project_install_or_status(self):
        self.path('claude', 'user').parent.mkdir(parents=True, exist_ok=True)
        self.path('claude', 'user').write_text('{broken', encoding='utf-8')
        self.assertIn('user unreadable', self.cli('hooks', 'status', '--host', 'claude')[1])
        self.assertEqual(self.cli('hooks', 'install', '--host', 'claude')[0], 0)
        code, line = self.cli('hooks', 'install', '--host', 'claude', '--scope', 'user', '--force-both')
        self.assertEqual((code, line.split()[2]), (3, 'PROGRESS_HOOKS_SETTINGS'))  # the target file still hard-fails

    def test_a7_a_second_scope_is_refused_unless_forced(self):
        self.assertEqual(self.cli('hooks', 'install', '--host', 'claude')[0], 0)
        code, line = self.cli('hooks', 'install', '--host', 'claude', '--scope', 'user')
        self.assertEqual((code, line.count('\n'), line.split()[2]), (3, 0, 'PROGRESS_HOOKS_DUPLICATE'), line)
        self.assertFalse(self.path('claude', 'user').exists())
        self.assertEqual(self.cli('hooks', 'install', '--host', 'claude', '--scope', 'user', '--force-both')[0], 0)
        self.assertEqual(self.cli('hooks', 'install', '--host', 'codex', '--scope', 'user')[0], 0)  # another host is unaffected

    def test_a5_a_concurrent_edit_is_kept_by_a_re_read(self):
        self.write('claude', 'project', UNRELATED)
        path = self.path('claude', 'project')
        changed = []

        def interfere(target):
            if not changed:
                changed.append(1)
                data = json.loads(path.read_text(encoding='utf-8'))
                data['permissions']['deny'] = ['Bash(rm *)']
                path.write_text(json.dumps(data), encoding='utf-8')

        self.patch_seam(interfere)
        self.assertEqual(self.cli('hooks', 'install', '--host', 'claude')[0], 0)
        data = self.read('claude', 'project')
        self.assertEqual(data['permissions']['deny'], ['Bash(rm *)'])
        self.assertEqual(len(self.ours(data)), 5)
        self.assertFalse(Path(str(path) + '.progress-lock').exists())

    def test_a5_a_file_that_keeps_changing_is_refused_and_left_alone(self):
        self.write('claude', 'project', UNRELATED)
        path = self.path('claude', 'project')
        count = []

        def interfere(target):
            count.append(1)
            data = json.loads(path.read_text(encoding='utf-8'))
            data['env'][f'N{len(count)}'] = '1'
            path.write_text(json.dumps(data), encoding='utf-8')

        self.patch_seam(interfere)
        code, line = self.cli('hooks', 'install', '--host', 'claude')
        self.assertEqual((code, line.split()[2]), (3, 'PROGRESS_HOOKS_CONFLICT'), line)
        self.assertEqual(self.ours(self.read('claude', 'project')), [])
        self.assertFalse(Path(str(path) + '.progress-lock').exists())

    def patch_seam(self, function):
        real = hooks_install.before_replace
        hooks_install.before_replace = function
        self.addCleanup(setattr, hooks_install, 'before_replace', real)

    def test_a_held_lock_is_refused_in_one_line(self):
        path = self.path('claude', 'project')
        path.parent.mkdir(parents=True, exist_ok=True)
        real = hooks_install.LOCK_WAIT
        hooks_install.LOCK_WAIT = 0.2
        self.addCleanup(setattr, hooks_install, 'LOCK_WAIT', real)
        with Lock(hooks_install.install_lock_path(self.root, 'claude')):
            code, line = self.cli('hooks', 'install', '--host', 'claude')
        self.assertEqual((code, line.split()[2]), (3, 'PROGRESS_HOOKS_CONFLICT'), line)

    def test_f11_a_python_command_with_spaces_or_shell_characters_is_refused(self):
        for value in ('C:/Program Files/Python/python.exe', 'python;rm', 'py"x'):
            code, line = self.cli('hooks', 'install', '--host', 'claude', '--python', value)
            self.assertEqual((code, line.split()[2]), (2, 'PROGRESS_USAGE'), value)
        self.assertFalse(self.path('claude', 'project').exists())

    def test_a6_installing_hooks_after_init_opens_a_bind(self):
        self.assertNotIn('bind=', self.cli('hooks', 'install', '--host', 'claude')[1])
        self.init_plan()
        code, line = self.cli('hooks', 'install', '--host', 'claude')
        self.assertEqual(code, 0, line)
        nonce = line.rsplit('bind=', 1)[1]
        pending = json.loads(self.ctx.bindings.read_text(encoding='utf-8'))['pending']
        self.assertIn(nonce, [p['nonce'] for p in pending])


if __name__ == '__main__':
    unittest.main()
