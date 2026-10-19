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
