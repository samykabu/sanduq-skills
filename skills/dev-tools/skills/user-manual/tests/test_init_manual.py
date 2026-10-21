"""Portable init_manual: theme defaults, theme stylesheets and tool copies, no Spec Kit layout."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

INIT = Path(__file__).resolve().parents[1] / 'scripts/init_manual.py'
ASSETS = Path(__file__).resolve().parents[1] / 'assets/github'
sys.path.insert(0, str(INIT.parent))
import sanduq_ci  # noqa: E402


class InitManualTests(unittest.TestCase):
    def test_scaffold_records_the_theme_and_ships_every_stylesheet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            modules = root / 'modules.json'
            modules.write_text(json.dumps([{'id': 'refunds', 'name': 'Refunds', 'description': 'Refund requests',
                                            'evidence': ['src/refunds']}]), encoding='utf-8')
            result = subprocess.run([sys.executable, str(INIT), '--repo-root', str(root), '--modules-file', str(modules)],
                                    capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(0, result.returncode, result.stderr)
            manual = root / 'User-Manual'
            self.assertIn('  theme: material\n', (manual / 'manual.yml').read_text(encoding='utf-8'))
            for name in ('extra.css', 'rtl.css', 'print.css', 'rtl-generic.css', 'rtl-readthedocs.css',
                         'theme-readthedocs.css'):
                self.assertTrue((manual / 'theme' / name).is_file(), name)
            for name in ('audit_manual.py', 'build_manual.py', 'manual_state.py'):
                self.assertTrue((manual / 'tools' / name).is_file(), name)
            self.assertTrue((root / '.github/workflows/user-manual-preview.yml').is_file())
            self.assertFalse((root / '.specify').exists())

    def test_an_authored_home_page_survives_and_a_missing_one_gets_the_stub(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            modules = root / 'modules.json'
            modules.write_text(json.dumps([{'id': 'refunds', 'name': 'Refunds', 'description': 'Refund requests',
                                            'name_ar': 'المبالغ', 'description_ar': 'طلبات الاسترداد',
                                            'evidence': ['src/refunds']}]), encoding='utf-8')
            home = root / 'User-Manual/docs/en/index.md'
            home.parent.mkdir(parents=True)
            home.write_text('# My authored home page\n', encoding='utf-8')
            result = subprocess.run([sys.executable, str(INIT), '--repo-root', str(root), '--modules-file', str(modules),
                                     '--product-name', 'Shop', '--enable-arabic'],
                                    capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual('# My authored home page\n', home.read_text(encoding='utf-8'))
            arabic = (root / 'User-Manual/docs/ar/index.md').read_text(encoding='utf-8')
            self.assertIn('Shop', arabic)
            self.assertTrue((root / 'User-Manual/docs/en/modules/refunds/index.md').is_file())

    def init(self, root, *extra):
        modules = root / 'modules.json'
        modules.write_text(json.dumps([{'id': 'refunds', 'name': 'Refunds', 'description': 'Refund requests',
                                        'evidence': ['src/refunds']}]), encoding='utf-8')
        result = subprocess.run([sys.executable, str(INIT), '--repo-root', str(root), '--modules-file', str(modules),
                                 *extra], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(0, result.returncode, result.stderr)
        return root / 'User-Manual'

    def test_no_tools_skips_the_script_copies_and_manual_yml_records_the_impact_scope(self):
        import yaml
        with tempfile.TemporaryDirectory() as tmp:
            manual = self.init(Path(tmp), '--no-tools')
            self.assertFalse((manual / 'tools').exists())
            self.assertTrue((manual / 'theme/extra.css').is_file())
            config = yaml.safe_load((manual / 'manual.yml').read_text(encoding='utf-8'))
            self.assertEqual({'impact_scope': 'all'}, config['lifecycle'])

    def test_ci_selection_comes_from_the_project_policy_unless_a_file_is_named(self):
        policy = ('ci:\n  provider: github-actions\n  policy: self-hosted-required\n'
                  '  runners: {linux: [self-hosted, %s]}\n'
                  '  capabilities: {system_packages: preinstalled, python: preinstalled, python_version: "3.13"}\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.specify').mkdir()
            (root / '.specify/workflow.yml').write_text(policy % 'project-runner', encoding='utf-8')
            self.init(root)
            preview = (root / '.github/workflows/user-manual-preview.yml').read_text(encoding='utf-8')
            self.assertIn('project-runner', preview)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.specify').mkdir()
            (root / '.specify/workflow.yml').write_text(policy % 'project-runner', encoding='utf-8')
            (root / 'ci.yml').write_text(policy % 'named-runner', encoding='utf-8')
            self.init(root, '--ci-policy', str(root / 'ci.yml'))
            preview = (root / '.github/workflows/user-manual-preview.yml').read_text(encoding='utf-8')
            self.assertIn('named-runner', preview)
            self.assertNotIn('project-runner', preview)

    def test_preview_skips_fork_pull_requests_only_on_self_hosted_runners(self):
        import yaml
        template = (ASSETS / 'user-manual-preview.yml').read_bytes()
        ci = sanduq_ci.default_ci()
        ci.update(policy='self-hosted-required', runners={'linux': ['self-hosted', 'homek8-general']})
        ci['capabilities'].update(python='preinstalled', system_packages='preinstalled')
        job = yaml.safe_load(sanduq_ci.render(template, ci))['jobs']['preview']
        self.assertEqual('github.event.pull_request.head.repo.full_name == github.repository', job['if'])
        hosted = yaml.safe_load(sanduq_ci.render(template, sanduq_ci.default_ci()))
        self.assertFalse(any('if' in each for each in hosted['jobs'].values()))
        for name in ('user-manual-preview.yml', 'user-manual-release.yml'):
            for line in (ASSETS / name).read_text(encoding='utf-8').splitlines():
                if 'uses:' in line:
                    self.assertRegex(line, r'@[0-9a-f]{40} # v\d+\.\d+\.\d+$', name)


if __name__ == '__main__':
    unittest.main()
