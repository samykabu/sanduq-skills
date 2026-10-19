"""`progress hooks install|uninstall|status`: native hook entries for Claude Code and Codex."""
import copy
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
from sanduq_progress import hooks_install

UNRELATED = {
    'permissions': {'allow': ['Bash(git status)']},
    'env': {'KEEP': '1'},
    'hooks': {
        'PostToolUse': [{'matcher': 'Edit', 'hooks': [{'type': 'command', 'command': 'echo formatted', 'timeout': 5}]}],
        'Notification': [{'hooks': [{'type': 'command', 'command': 'notify-send done'}]}],
    },
}
SPECKIT = {'hooks': {'PostToolUse': [{'hooks': [{'type': 'command',
                                                  'command': 'python .specify/events.py speckit.progress.hook-post-tool-use post_tool_use 10'}]}]}}


class HooksCase(PlanProject):
    def setUp(self):
        super().setUp()
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(helpers.remove_tree, self.home)
        os.environ['SANDUQ_PROGRESS_HOME'] = self.home.name
        for name in ('CLAUDE_CONFIG_DIR', 'CODEX_HOME'):
            os.environ.pop(name, None)
        # Project scope writes a repo-relative path, so the hook script must live inside the repo: vendor a copy of the scripts.
        shutil.copytree(helpers.SCRIPTS, self.root / '.claude' / 'skills' / 'progress-report' / 'scripts',
                        ignore=shutil.ignore_patterns('__pycache__'))
        real = hooks_install.HOOK_SCRIPT
        hooks_install.HOOK_SCRIPT = self.root / '.claude' / 'skills' / 'progress-report' / 'scripts' / 'hook.py'
        self.addCleanup(setattr, hooks_install, 'HOOK_SCRIPT', real)

    def path(self, host, scope):
        return hooks_install.settings_path(self.root, host, scope)

    def write(self, host, scope, data):
        path = self.path(host, scope)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

    def read(self, host, scope):
        return json.loads(self.path(host, scope).read_text(encoding='utf-8'))

    def ours(self, data):
        return [(name, group.get('matcher'), h['command']) for name, groups in data.get('hooks', {}).items() for group in groups
                for h in group['hooks'] if hooks_install.TAG in h['command']]


class RoundTrip(HooksCase):
    def test_claude_project_install_writes_the_five_events_and_uninstall_restores_the_file_exactly(self):
        self.write('claude', 'project', UNRELATED)
        original = self.path('claude', 'project').read_text(encoding='utf-8')
        code, line = self.cli('hooks', 'install', '--host', 'claude')
        self.assertEqual((code, line.count('\n')), (0, 0), line)
        self.assertTrue(line.startswith('progress: hooks installed claude project 5 entries in .claude/settings.json'), line)
        data = self.read('claude', 'project')
        events = self.ours(data)
        self.assertEqual(sorted(e[0] for e in events), sorted(['SessionStart', 'PreToolUse', 'PostToolUse', 'Stop', 'SessionEnd']))
        self.assertEqual({e[0]: e[1] for e in events}['PreToolUse'], 'Task|Agent|spawn_agent')
        for name, _, command in events:
            self.assertIn('"${CLAUDE_PROJECT_DIR}/.claude/skills/progress-report/scripts/hook.py"', command)
            self.assertTrue(command.endswith('; exit 0'), command)
            self.assertIn(f' {hooks_install.CLAUDE_EVENTS[[e[0] for e in hooks_install.CLAUDE_EVENTS].index(name)][1]} ', command)
        self.assertEqual(data['permissions'], UNRELATED['permissions'])
        self.assertEqual(data['env'], UNRELATED['env'])
        self.assertEqual(data['hooks']['Notification'], UNRELATED['hooks']['Notification'])
        self.assertEqual(data['hooks']['PostToolUse'][0], UNRELATED['hooks']['PostToolUse'][0])  # the user's own hook stays first
        self.assertEqual(len(data['hooks']['PostToolUse']), 2)
        code, line = self.cli('hooks', 'uninstall', '--host', 'claude')
        self.assertEqual((code, line), (0, 'progress: hooks removed claude project 5 entries from .claude/settings.json'))
        self.assertEqual(self.read('claude', 'project'), UNRELATED)
        self.assertEqual(self.path('claude', 'project').read_text(encoding='utf-8'), original)

    def test_codex_project_install_writes_the_same_five_events_and_round_trips(self):
        self.write('codex', 'project', {'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'echo bye'}]}]}, 'other': [1, 2]})
        before = self.read('codex', 'project')
        code, line = self.cli('hooks', 'install', '--host', 'codex')
        self.assertEqual(code, 0, line)
        self.assertIn('5 entries in .codex/hooks.json', line)
        events = self.ours(self.read('codex', 'project'))
        self.assertEqual(sorted(e[0] for e in events), sorted(['SessionStart', 'PreToolUse', 'PostToolUse', 'Stop', 'SessionEnd']))
        self.assertEqual(self.cli('hooks', 'uninstall', '--host', 'codex')[0], 0)
        self.assertEqual(self.read('codex', 'project'), before)

    def test_post_tool_matcher_is_written_only_when_asked(self):
        for host in ('claude', 'codex'):
            self.cli('hooks', 'install', '--host', host)
            self.assertIsNone({e[0]: e[1] for e in self.ours(self.read(host, 'project'))}['PostToolUse'])
            code, line = self.cli('hooks', 'install', '--host', host, '--post-tool-matcher', 'Bash|Task|Agent|spawn_agent')
            self.assertEqual(code, 0, line)
            matchers = {e[0]: e[1] for e in self.ours(self.read(host, 'project'))}
            self.assertEqual((matchers['PostToolUse'], matchers['PreToolUse'], len(matchers)), ('Bash|Task|Agent|spawn_agent', 'Task|Agent|spawn_agent', 5))
            self.assertIn('5 entries from', self.cli('hooks', 'uninstall', '--host', host)[1])

    def test_install_into_a_missing_file_creates_it_and_uninstall_leaves_an_empty_object(self):
        self.assertFalse(self.path('claude', 'project').exists())
        self.assertEqual(self.cli('hooks', 'install', '--host', 'claude')[0], 0)
        self.assertEqual(len(self.ours(self.read('claude', 'project'))), 5)
        self.assertEqual(self.cli('hooks', 'uninstall', '--host', 'claude')[0], 0)
        self.assertEqual(self.read('claude', 'project'), {})

    def test_user_scope_uses_an_absolute_path_and_the_home_override(self):
        self.write('claude', 'user', copy.deepcopy(UNRELATED))
        code, line = self.cli('hooks', 'install', '--host', 'claude', '--scope', 'user')
        self.assertEqual(code, 0, line)
        self.assertIn('in ~/.claude/settings.json', line)
        commands = [c for _, _, c in self.ours(self.read('claude', 'user'))]
        self.assertTrue(all(hooks_install.HOOK_SCRIPT.as_posix() in c for c in commands), commands)
        self.assertFalse((self.root / '.claude' / 'settings.json').exists())
        self.cli('hooks', 'uninstall', '--host', 'claude', '--scope', 'user')
        self.assertEqual(self.read('claude', 'user'), UNRELATED)

    def test_codex_user_scope_honours_codex_home(self):
        os.environ['CODEX_HOME'] = str(Path(self.home.name) / 'codexhome')
        self.assertEqual(self.cli('hooks', 'install', '--host', 'codex', '--scope', 'user')[0], 0)
        self.assertTrue((Path(self.home.name) / 'codexhome' / 'hooks.json').is_file())

    def test_reinstall_is_idempotent_and_replaces_only_its_own_entries(self):
        self.write('claude', 'project', copy.deepcopy(UNRELATED))
        for _ in range(3):
            self.assertEqual(self.cli('hooks', 'install', '--host', 'claude', '--python', 'py3')[0], 0)
        data = self.read('claude', 'project')
        self.assertEqual(len(self.ours(data)), 5)
        self.assertTrue(all(c.startswith('py3 ') for _, _, c in self.ours(data)))
        self.assertEqual(data['hooks']['Notification'], UNRELATED['hooks']['Notification'])

    def test_uninstall_without_a_file_or_entries_is_a_no_op(self):
        self.assertEqual(self.cli('hooks', 'uninstall', '--host', 'codex'), (0, 'progress: hooks removed codex project 0 entries'))
        self.write('claude', 'project', UNRELATED)
        self.assertEqual(self.cli('hooks', 'uninstall', '--host', 'claude')[1], 'progress: hooks removed claude project 0 entries from .claude/settings.json')
        self.assertEqual(self.read('claude', 'project'), UNRELATED)

    def test_a_group_that_mixes_a_user_hook_with_ours_keeps_the_user_hook(self):
        mixed = {'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'echo mine'},
                                                {'type': 'command', 'command': 'python "x/hook.py" stop ' + hooks_install.TAG}]}]}}
        self.write('claude', 'project', mixed)
        self.cli('hooks', 'uninstall', '--host', 'claude')
        self.assertEqual(self.read('claude', 'project'), {'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'echo mine'}]}]}})

    def test_the_written_command_runs_hook_py_and_exits_silently(self):
        self.cli('hooks', 'install', '--host', 'claude')
        command = next(c for name, _, c in self.ours(self.read('claude', 'project')) if name == 'PostToolUse')
        script = self.root / '.claude/skills/progress-report/scripts/hook.py'
        result = subprocess.run([sys.executable, str(script), 'post_tool_use', hooks_install.TAG], input=json.dumps({'session_id': 's'}),
                                capture_output=True, text=True, cwd=self.root, env={**os.environ, 'SANDUQ_PROGRESS_ROOT': str(self.root)})
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))
        self.assertIn('hook.py" post_tool_use --managed-by=progress-report', command)


class Refusals(HooksCase):
    def test_spec_kit_registered_progress_hooks_refuse_a_second_registration(self):
        self.write('claude', 'project', SPECKIT)
        before = self.path('claude', 'project').read_text(encoding='utf-8')
        code, line = self.cli('hooks', 'install', '--host', 'claude')
        self.assertEqual((code, line.count('\n')), (3, 0))
        self.assertTrue(line.startswith('progress: error PROGRESS_HOOKS_SPECKIT'), line)
        self.assertEqual(self.path('claude', 'project').read_text(encoding='utf-8'), before)

    def test_the_refusal_also_covers_the_other_scope_of_the_same_host(self):
        self.write('codex', 'project', SPECKIT)
        code, line = self.cli('hooks', 'install', '--host', 'codex', '--scope', 'user')
        self.assertEqual(code, 3, line)
        self.assertFalse(self.path('codex', 'user').exists())
        self.assertEqual(self.cli('hooks', 'install', '--host', 'claude')[0], 0)  # Spec Kit's Codex hooks do not block Claude

    def test_invalid_json_and_odd_shapes_are_never_overwritten(self):
        path = self.path('claude', 'project')
        path.parent.mkdir(parents=True, exist_ok=True)
        for text in ('{not json', '[]', '{"hooks": []}'):
            path.write_text(text, encoding='utf-8')
            code, line = self.cli('hooks', 'install', '--host', 'claude')
            self.assertEqual((code, line.split()[2]), (3, 'PROGRESS_HOOKS_SETTINGS'), text)
            self.assertEqual(path.read_text(encoding='utf-8'), text)

    def test_project_scope_refuses_a_skill_outside_the_repository(self):
        hooks_install.HOOK_SCRIPT = Path(self.home.name) / 'skill' / 'scripts' / 'hook.py'
        code, line = self.cli('hooks', 'install', '--host', 'claude')
        self.assertEqual((code, line.split()[2]), (3, 'PROGRESS_HOOKS_PATH'))
        self.assertFalse(self.path('claude', 'project').exists())
        self.assertEqual(self.cli('hooks', 'install', '--host', 'claude', '--scope', 'user')[0], 0)

    def test_install_and_uninstall_need_a_host(self):
        for action in ('install', 'uninstall'):
            code, line = self.cli('hooks', action)
            self.assertEqual((code, line.split()[2]), (2, 'PROGRESS_USAGE'))
        self.assertEqual(self.cli('hooks', 'install', '--host', 'gemini')[0], 2)

    def test_hosts_are_not_touched_unless_asked(self):
        self.cli('hooks', 'status')
        self.init_plan()
        self.assertFalse((self.root / '.claude' / 'settings.json').exists() or (self.root / '.codex').exists())
        self.assertEqual(os.listdir(self.home.name), [])


class Status(HooksCase):
    def test_status_is_one_line_and_counts_each_host_and_scope(self):
        self.assertEqual(self.cli('hooks', 'status'),
                         (0, 'progress: hooks claude project 0/5 user 0/5; codex project 0/5 user 0/5; spec-kit no'))
        self.cli('hooks', 'install', '--host', 'claude')
        self.cli('hooks', 'install', '--host', 'codex', '--scope', 'user')
        code, line = self.cli('hooks', 'status')
        self.assertEqual(line, 'progress: hooks claude project 5/5 user 0/5; codex project 0/5; user 5/5 registered, 0/5 approved '
                               '(approve the hooks in Codex); spec-kit no')
        self.assertEqual(self.cli('hooks', 'status', '--host', 'claude')[1], 'progress: hooks claude project 5/5 user 0/5; spec-kit no')

    def test_status_reports_spec_kit_registration(self):
        self.write('claude', 'user', SPECKIT)
        self.assertTrue(self.cli('hooks', 'status')[1].endswith('spec-kit yes'))


class CodexApproval(HooksCase):
    EVENTS = ('session_start', 'pre_tool_use', 'post_tool_use', 'stop', 'session_end')

    def setUp(self):
        super().setUp()
        self.codex_home = Path(self.home.name) / 'codexhome'
        self.codex_home.mkdir()
        os.environ['CODEX_HOME'] = str(self.codex_home)
        self.addCleanup(os.environ.pop, 'CODEX_HOME', None)

    def config(self, trusted=True, approve=(), path_style=None):
        blocks = []
        if trusted:
            key = path_style(self.root.resolve().as_posix()) if path_style else self.root.resolve().as_posix().lower()
            blocks.append(f'[projects."{key}"]\ntrust_level = "trusted"\n')
        hooks_file = self.path('codex', 'project').resolve().as_posix()
        for event in approve:
            key = f'{hooks_file}:{event}:0:0'
            key = path_style(key) if path_style else key
            blocks.append(f'[hooks.state."{key}"]\ntrusted_hash = "sha256:abc"\n')
        (self.codex_home / 'config.toml').write_text('\n'.join(blocks), encoding='utf-8')

    def line(self):
        return self.cli('hooks', 'status', '--host', 'codex')[1]

    def test_unapproved_and_untrusted(self):
        self.cli('hooks', 'install', '--host', 'codex')
        self.config(trusted=False)
        self.assertEqual(self.line(), 'progress: hooks codex project 5/5 registered, 0/5 approved, project untrusted; user 0/5 '
                                      '(approve the hooks in Codex); spec-kit no')

    def test_trusted_but_unapproved(self):
        self.cli('hooks', 'install', '--host', 'codex')
        self.config()
        self.assertIn('project 5/5 registered, 0/5 approved; user', self.line())
        self.assertNotIn('untrusted', self.line())

    def test_fully_approved_is_quiet(self):
        self.cli('hooks', 'install', '--host', 'codex')
        self.config(approve=self.EVENTS)
        self.assertEqual(self.line(), 'progress: hooks codex project 5/5 registered, 5/5 approved; user 0/5; spec-kit no')

    def test_partially_approved_and_empty_hash_does_not_count(self):
        self.cli('hooks', 'install', '--host', 'codex')
        self.config(approve=self.EVENTS[:2])
        self.assertIn('2/5 approved', self.line())
        path = self.codex_home / 'config.toml'
        path.write_text(path.read_text(encoding='utf-8').replace('sha256:abc', ''), encoding='utf-8')
        self.assertIn('0/5 approved', self.line())

    def test_windows_style_paths_match_regardless_of_case_and_separators(self):
        self.cli('hooks', 'install', '--host', 'codex')
        self.config(approve=self.EVENTS, path_style=lambda p: p.upper().replace('/', chr(92) * 2))
        self.assertIn('5/5 approved', self.line())
        self.assertNotIn('untrusted', self.line())

    def test_spec_kit_hooks_in_config_toml_are_counted(self):
        config = self.root / '.codex' / 'config.toml'
        config.parent.mkdir(parents=True)
        blocks = []
        for event in ('SessionStart', 'PreToolUse', 'PostToolUse', 'Stop', 'SessionEnd'):
            blocks.append(f'[[hooks.{event}]]\n[[hooks.{event}.hooks]]\ntype = "command"\n'
                          f'command = "python .specify/events.py speckit.progress.hook-x"\n')
        config.write_text('\n'.join(blocks), encoding='utf-8')
        self.config()
        key = f'{config.resolve().as_posix()}:pre_tool_use:0:0'
        with open(self.codex_home / 'config.toml', 'a', encoding='utf-8') as f:
            f.write(f'\n[hooks.state."{key}"]\ntrusted_hash = "sha256:x"\n')
        line = self.line()
        self.assertIn('project 5/5 registered, 1/5 approved', line)
        self.assertTrue(line.endswith('spec-kit yes'))

    def test_install_reminds_about_approval(self):
        self.assertIn('approve each hook', self.cli('hooks', 'install', '--host', 'codex')[1])

    def test_status_hints_when_nothing_binds(self):
        self.init_plan()
        self.cli('hooks', 'install', '--host', 'codex')
        self.config(trusted=False)
        self.assertTrue(self.cli('status')[1].endswith('no bound session (codex hooks not approved?)'))
        self.config(approve=self.EVENTS)
        self.assertNotIn('no bound session', self.cli('status')[1])

    def test_no_hint_without_codex_hooks(self):
        self.init_plan()
        self.assertNotIn('no bound session', self.cli('status')[1])

    def test_user_trust_state_is_never_written(self):
        self.cli('hooks', 'install', '--host', 'codex')
        self.config(trusted=False)
        before = (self.codex_home / 'config.toml').read_bytes()
        self.line()
        self.cli('status')
        self.assertEqual((self.codex_home / 'config.toml').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
