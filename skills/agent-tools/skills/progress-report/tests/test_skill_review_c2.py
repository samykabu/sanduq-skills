"""Regression tests for the skill review (cycle 2): exact exclusion checks, installer locking, fingerprint cost, id rule."""
import json
import os
import subprocess
import threading
import time
import unittest
from pathlib import Path

from helpers import PlanProject
from sanduq_progress import hooks_install
from sanduq_progress.collect import plan as plancol
from sanduq_progress.lock import Lock
from sanduq_progress.util import ProgressError
from test_hooks_install import HooksCase


def git_status(root):
    return subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=root, capture_output=True,
                          text=True).stdout


def commit_all(root, message, force=False):
    subprocess.run(['git', 'add', *(['-f'] if force else []), '.'], cwd=root, check=True)
    subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', message], cwd=root, check=True)


class ExactExclusions(PlanProject):
    def reinclude(self):
        (self.root / '.gitignore').write_text('reports/*/.host/*\n!reports/*/.host/\n!reports/*/.host/plan-keys.json\n', encoding='utf-8')
        commit_all(self.root, 'ignore rules')

    def test_a1_a_reincluded_plan_keys_file_is_still_ignored_through_the_nested_gitignore(self):
        from test_skill_review_c3 import local_leaks
        self.reinclude()
        self.init_plan('--dir', 'reports/p')
        self.cli('refresh')
        (self.root / 'reports' / 'p' / '.host' / 'plan-keys.json').write_text('{}', encoding='utf-8')
        self.assertEqual(local_leaks(self.root), [])
        listed = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'], cwd=self.root, capture_output=True,
                                text=True).stdout
        self.assertNotIn('.host/', listed)
        self.assertNotIn('.view/', listed)

    def test_a1_every_actual_destination_is_checked(self):
        seen = []
        real = subprocess.run

        def spy(cmd, *args, **kwargs):
            if isinstance(cmd, list) and cmd[:2] == ['git', 'check-ignore']:
                seen.extend(kwargs['input'].decode('utf-8').split(chr(0)))
            return real(cmd, *args, **kwargs)

        subprocess.run = spy
        self.addCleanup(setattr, subprocess, 'run', real)
        self.init_plan('--dir', 'reports/p')
        names = {Path(p).name for p in seen}
        for expected in ('plan-keys.json', 'plan-source.json', 'state.json', 'report.json', 'data.js', 'diagnostics.log',
                         'lock', 'index.html'):
            self.assertIn(expected, names)

    def test_f11_a_refused_init_leaves_no_tracked_change_and_no_directories(self):
        # a tracked .host file defeats every ignore rule
        host = self.root / 'reports' / '[review]' / '.host'
        host.mkdir(parents=True)
        (host / 'plan-keys.json').write_text('{}', encoding='utf-8')
        commit_all(self.root, 'tracked', force=True)
        code, line = self.cli('init', '--plan', 'docs/plan.md', '--dir', 'reports/[review]')
        self.assertEqual((code, line.split()[2]), (3, 'PROGRESS_EXCLUDE_FAILED'), line)
        self.assertEqual(git_status(self.root), '')
        self.assertFalse((self.root / '.progress').exists())
        self.assertFalse((self.root / 'reports' / '[review]' / '.view').exists())

    def test_f11_a_refused_preflight_registers_nothing_and_removes_what_it_created(self):
        import progress
        from sanduq_progress.util import ProgressError

        def refuse(root, directory):
            raise ProgressError('PROGRESS_EXCLUDE_FAILED', 'git does not ignore x', 3)

        real = progress.check_plan_excluded
        progress.check_plan_excluded = refuse
        self.addCleanup(setattr, progress, 'check_plan_excluded', real)
        before = git_status(self.root)
        code, line = self.cli('init', '--plan', 'docs/plan.md', '--dir', 'reports/p')
        self.assertEqual((code, line.split()[2]), (3, 'PROGRESS_EXCLUDE_FAILED'), line)
        self.assertFalse((self.root / 'reports').exists())
        self.assertFalse((self.root / '.progress').exists())
        self.assertFalse((self.root / '.specify').exists())
        self.assertEqual(git_status(self.root), before)


class InstallerLocking(HooksCase):
    def patch_seam(self, function):
        real = hooks_install.before_replace
        hooks_install.before_replace = function
        self.addCleanup(setattr, hooks_install, 'before_replace', real)

    def set_wait(self, seconds):
        real = hooks_install.LOCK_WAIT
        hooks_install.LOCK_WAIT = seconds
        self.addCleanup(setattr, hooks_install, 'LOCK_WAIT', real)

    def test_a2_a_spec_kit_registration_injected_during_the_first_attempt_is_caught(self):
        project, user = self.path('claude', 'project'), self.path('claude', 'user')
        project.parent.mkdir(parents=True, exist_ok=True)
        project.write_text('{}', encoding='utf-8')
        done = []

        def inject(target):
            if not done:
                done.append(1)
                user.parent.mkdir(parents=True, exist_ok=True)
                user.write_text(json.dumps({'hooks': {'Stop': [{'hooks': [{'type': 'command',
                                'command': 'python x speckit.progress.hook-stop'}]}]}}), encoding='utf-8')
                project.write_text('{"touched": 1}', encoding='utf-8')  # force the second attempt

        self.patch_seam(inject)
        code, line = self.cli('hooks', 'install', '--host', 'claude')
        self.assertEqual((code, line.split()[2]), (3, 'PROGRESS_HOOKS_SPECKIT'), line)
        self.assertEqual(self.ours(self.read('claude', 'project')), [])

    def test_a2_concurrent_project_and_user_installs_refuse_one_without_force_both(self):
        self.set_wait(5.0)
        results, started = {}, []

        def second():
            try:
                hooks_install.install(self.root, 'claude', 'user', 'python')
                results['user'] = 'ok'
            except ProgressError as exc:
                results['user'] = exc.code

        def pause(target):
            if not started:
                started.append(1)
                thread = threading.Thread(target=second)
                thread.start()
                self.addCleanup(thread.join)
                time.sleep(0.4)  # the second installer is now waiting on the lock

        self.patch_seam(pause)
        hooks_install.install(self.root, 'claude', 'project', 'python')
        deadline = time.time() + 10
        while 'user' not in results and time.time() < deadline:
            time.sleep(0.05)
        self.assertEqual(results.get('user'), 'PROGRESS_HOOKS_DUPLICATE')
        self.assertFalse(self.path('claude', 'user').exists())

    def test_a3_a_live_holder_paused_past_thirty_seconds_is_not_overtaken(self):
        self.set_wait(0.3)
        lock_path = hooks_install.install_lock_path(self.root, 'claude')
        with Lock(lock_path):
            old = time.time() - 120
            os.utime(lock_path, (old, old))
            code, line = self.cli('hooks', 'install', '--host', 'claude')
            self.assertEqual((code, line.split()[2]), (3, 'PROGRESS_HOOKS_CONFLICT'), line)
            self.assertTrue(lock_path.exists())
        self.assertEqual(self.cli('hooks', 'install', '--host', 'claude')[0], 0)  # released by its owner: free again
        self.assertTrue(lock_path.exists())  # never deleted by anyone else

    def test_a3_the_age_rule_is_gone(self):
        self.assertFalse(hasattr(hooks_install, 'LOCK_STALE'))


class FingerprintCost(unittest.TestCase):
    def test_a4_reversing_five_hundred_items_computes_a_linear_number_of_fingerprints(self):
        first = [{'id': None, 'key': f'item number {n} text'} for n in range(500)]
        mapping, _ = plancol.assign(first, [])
        stored = [{'id': m['id'], 'fp': m['fp'], 'key': m['key']} for m in mapping]
        flipped = [{'id': None, 'key': i['key']} for i in reversed(first)]
        calls = []
        real = plancol.fingerprint
        plancol.fingerprint = lambda key: calls.append(1) or real(key)
        self.addCleanup(setattr, plancol, 'fingerprint', real)
        plancol.assign(flipped, stored)
        self.assertLessEqual(len(calls), 1100)
        self.assertEqual({i['key']: i['id'] for i in flipped}, {i['key']: i['id'] for i in first})

    def test_a4_duplicate_texts_keep_their_order(self):
        mapping, _ = plancol.assign([{'id': None, 'key': 'same'}, {'id': None, 'key': 'same'}], [])
        again = [{'id': None, 'key': 'same'}, {'id': None, 'key': 'same'}]
        plancol.assign(again, [{'id': m['id'], 'fp': m['fp']} for m in mapping])
        self.assertEqual([i['id'] for i in again], ['P001', 'P002'])


class IdRule(unittest.TestCase):
    def test_f12_ordinary_tokens_that_look_like_ids_stay_text(self):
        for text in ('X11 forwarding', 'H264 encoder', 'ES2015 modules', 'RFC-7231 compliance', 'CVE-2024 fix', 'AB12 thing'):
            self.assertEqual(plancol.explicit_id(text), (None, text), text)

    def test_f12_documented_forms_are_ids(self):
        for text, expected in (('T001 write it', 'T001'), ('US12 as a user', 'US12'), ('T7 small', 'T7'),
                               ('**T12** bold', 'T12'), ('T-12: delimited', 'T-12'), ('X11: delimited', 'X11')):
            self.assertEqual(plancol.explicit_id(text)[0], expected, text)


if __name__ == '__main__':
    unittest.main()
