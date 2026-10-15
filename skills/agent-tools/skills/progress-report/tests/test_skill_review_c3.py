"""Regression tests for the skill review (cycle 3): nested .gitignore in local-only dirs, no redundant excludes."""
import subprocess
import unittest

from helpers import PlanProject, Project
from sanduq_progress import snapshot

PARENT_RULES = '.host/*\n!claude-*.json\n.view/*\n!*.json\n!data.js\n'


def local_leaks(root):
    status = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=root, capture_output=True,
                            text=True).stdout.splitlines()
    others = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'], cwd=root, capture_output=True,
                            text=True).stdout.splitlines()
    return [line for line in (*status, *others) if '/.host/' in line or '/.view/' in line or '.host/' in line.split()[-1]
            or '.view/' in line.split()[-1]]


class NestedGitignore(Project):
    def test_feature_mode_dirs_stay_ignored_when_a_parent_rule_reincludes_snapshots(self):
        (self.root / '.gitignore').write_text(PARENT_RULES, encoding='utf-8')
        from test_hosts import bash_bind_payload
        nonce = self.init()
        self.hook('post_tool_use', bash_bind_payload(self, 'claude-sess-1', nonce))
        self.assertTrue(snapshot.snapshot_path(self.ctx, 'claude', 'claude-sess-1').exists())  # a real host-named file
        for leaf in ('.host', '.view'):
            self.assertEqual((self.ctx.dir / leaf / '.gitignore').read_text(encoding='utf-8'), '*\n')
        self.assertEqual(local_leaks(self.root), [])

    def test_a_hook_written_snapshot_is_ignored_too(self):
        (self.root / '.gitignore').write_text(PARENT_RULES, encoding='utf-8')
        nonce = self.init()
        from test_hosts import bash_bind_payload
        self.hook('post_tool_use', bash_bind_payload(self, 'claude-sess-1', nonce))
        self.hook('post_tool_use', self.payload('claude_pre_task.json'))
        self.assertEqual(local_leaks(self.root), [])

    def test_migration_keeps_the_nested_gitignore(self):
        self.init()
        legacy = self.ctx.view / 'host'
        legacy.mkdir()
        (legacy / 'claude-old.json').write_text('{}', encoding='utf-8')
        (self.ctx.host_dir / '.gitignore').unlink(missing_ok=True)
        self.assertTrue(snapshot.migrate_host_dir(self.ctx))
        self.assertTrue((self.ctx.host_dir / 'claude-old.json').exists())
        self.assertEqual((self.ctx.host_dir / '.gitignore').read_text(encoding='utf-8'), '*\n')

    def test_a_linked_gitignore_is_refused(self):
        from sanduq_progress.util import ProgressError, ensure_local_dir
        self.init()
        target = self.ctx.host_dir / '.gitignore'
        target.unlink(missing_ok=True)
        try:
            target.symlink_to(self.root / 'elsewhere')
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        with self.assertRaises(ProgressError):
            ensure_local_dir(self.ctx.host_dir)


class PlanNestedGitignore(PlanProject):
    def test_plan_dirs_stay_ignored_and_default_dirs_add_no_extra_excludes(self):
        (self.root / '.gitignore').write_text(PARENT_RULES, encoding='utf-8')
        self.init_plan()
        self.assertEqual(local_leaks(self.root), [])
        exclude = (self.root / '.git' / 'info' / 'exclude').read_text(encoding='utf-8').splitlines()
        self.assertIn('.progress/*/.view/', exclude)
        self.assertEqual([line for line in exclude if line.startswith('.progress/') and line.endswith(('/.view/', '/.host/')) and '*' not in line], [])

    def test_a_custom_dir_still_gets_its_own_excludes(self):
        self.init_plan('--dir', 'reports/p')
        exclude = (self.root / '.git' / 'info' / 'exclude').read_text(encoding='utf-8').splitlines()
        self.assertIn('reports/p/.host/', exclude)
        self.assertEqual((self.root / 'reports' / 'p' / '.host' / '.gitignore').read_text(encoding='utf-8'), '*\n') if (self.root / 'reports' / 'p' / '.host').exists() else None


if __name__ == '__main__':
    unittest.main()
