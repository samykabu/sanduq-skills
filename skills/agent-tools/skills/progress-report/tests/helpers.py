"""Shared test helpers: a throwaway git project, fixture loading and an in-process CLI runner."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / 'fixtures'
SCRIPTS = HERE.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS))

import progress  # noqa: E402
from sanduq_progress import hook, snapshot  # noqa: E402
from sanduq_progress.paths import Ctx  # noqa: E402

T0 = '2026-10-15T12:00:00Z'


def remove_tree(tmp, attempts=10):
    """TemporaryDirectory.cleanup with retries: on Windows a just-closed browser, scanner or child process can still hold a
    file for a moment, which made cleanup raise PermissionError (WinError 32) intermittently."""
    for attempt in range(attempts):
        try:
            tmp.cleanup()
            return
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.2 * (attempt + 1))


def fixture(name, **replace):
    text = (FIXTURES / name).read_text(encoding='utf-8')
    for key, value in replace.items():
        text = text.replace('{' + key + '}', str(value).replace('\\', '/'))
    return text


class Project(unittest.TestCase):
    """A temp repo on branch 001-demo with specs/001-demo/tasks.md. Subclass tests call self.cli(...)."""
    branch = '001-demo'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(remove_tree, self.tmp)
        self.root = Path(self.tmp.name).resolve()
        subprocess.run(['git', 'init', '-q', '-b', self.branch], cwd=self.root, check=True)
        (self.root / '.specify').mkdir()
        self.feature_dir = self.root / 'specs' / '001-demo'
        self.feature_dir.mkdir(parents=True)
        shutil.copyfile(FIXTURES / 'tasks.md', self.feature_dir / 'tasks.md')
        self._env = dict(os.environ)
        os.environ['SANDUQ_PROGRESS_NOW'] = T0
        os.environ.pop('SPECIFY_FEATURE', None)
        os.environ.pop('SANDUQ_PROGRESS_ROOT', None)
        self.addCleanup(self._restore_env)
        self.ctx = Ctx(self.root, 'specs/001-demo')

    def _restore_env(self):
        os.environ.clear()
        os.environ.update(self._env)

    def cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = progress.main(['--root', str(self.root), *args])
        return code, out.getvalue().strip()

    def init(self, **config):
        code, line = self.cli('init')
        self.assertEqual(code, 0, line)
        if config:
            data = json.loads(self.ctx.config.read_text(encoding='utf-8'))
            data.update(config)
            self.ctx.config.write_text(json.dumps(data), encoding='utf-8')
        return line.rsplit('bind=', 1)[1]

    def workflow_file(self, name, target=None):
        folder = self.feature_dir / 'workflow'
        folder.mkdir(exist_ok=True)
        shutil.copyfile(FIXTURES / name, folder / (target or name))

    def payload(self, name, **extra):
        data = json.loads(fixture(name, CWD=self.root.as_posix(), ROLLOUT=(FIXTURES / 'codex_rollout.jsonl').as_posix()))
        data.update(extra)
        return data

    def hook(self, event, payload, now=None, host=None):
        from datetime import datetime
        moment = datetime.fromisoformat((now or T0).replace('Z', '+00:00'))
        return hook.handle(event, json.dumps(payload), root=self.root, now=moment, host=host)

    def bind(self, session='claude-sess-1', host='claude'):
        code, line = self.cli('bind', '--session', session, '--host', host)
        self.assertEqual(code, 0, line)

    def snap(self, session='claude-sess-1', host='claude'):
        path = snapshot.snapshot_path(self.ctx, host, session)
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None

    def report(self):
        """The v2 compatibility document for the current producers (report.json itself holds v3)."""
        from datetime import datetime
        state = json.loads(self.ctx.state.read_text(encoding='utf-8')) if self.ctx.state.exists() else {}
        from sanduq_progress import model
        return model.build_v2(self.ctx, datetime.fromisoformat(T0.replace('Z', '+00:00')), int(state.get('rev') or 0), state)

    def stored_report(self):
        return json.loads(self.ctx.report.read_text(encoding='utf-8'))


PLAN_MD = """# Launch plan

Notes mention T099 in prose and `P098` in a code span, neither is an item.

## Backend

- [x] Set up the database
- [ ] Build the API (depends on P001)
- [ ] T010 Wire auth (after P002) see `(depends on P099)`

```markdown
- [ ] Decoy inside a fence (depends on P001)
```

## Frontend

- [ ] Build the UI [P]
- [X] Pick a colour palette
"""


class PlanProject(Project):
    """A temp repo with NO Spec Kit (no .specify, no specs/) holding docs/plan.md. `init_plan` creates its report."""
    branch = 'main'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(remove_tree, self.tmp)
        self.root = Path(self.tmp.name).resolve()
        subprocess.run(['git', 'init', '-q', '-b', self.branch], cwd=self.root, check=True)
        (self.root / 'docs').mkdir()
        self.plan_path = self.root / 'docs' / 'plan.md'
        self.plan_path.write_text(PLAN_MD, encoding='utf-8')
        self._env = dict(os.environ)
        os.environ['SANDUQ_PROGRESS_NOW'] = T0
        for name in ('SPECIFY_FEATURE', 'SANDUQ_PROGRESS_ROOT'):
            os.environ.pop(name, None)
        self.addCleanup(self._restore_env)
        self.ctx = None

    def init_plan(self, *args, plan='docs/plan.md'):
        code, line = self.cli('init', '--plan', plan, *args)
        self.assertEqual(code, 0, line)
        directory = line.split()[2].split('/.view/')[0]
        self.ctx = Ctx(self.root, directory)
        return line.rsplit('bind=', 1)[1]

    def write_plan(self, text, path=None):
        (path or self.plan_path).write_text(text, encoding='utf-8')


RUN842 = FIXTURES / 'run-842'
RUN842_FEATURE = 'specs/842-versioned-workflow-graphs'
RUN842_NOW = '2026-10-17T14:00:00Z'  # after the last evidence in the frozen fixture (the final PR receipt is 13:58)


def run842_ctx(base):
    """Copy the frozen, sanitized #842 evidence (tests/fixtures/run-842) into `base` as a Spec Kit project and return its
    Ctx. The fixture has no .host telemetry and no .delegate/runs, exactly as the real run did."""
    base = Path(base)
    (base / '.specify').mkdir(parents=True, exist_ok=True)
    feature = base / RUN842_FEATURE
    (feature / 'workflow').mkdir(parents=True, exist_ok=True)
    (feature / 'progress').mkdir(parents=True, exist_ok=True)
    for name in ('workflow/checkpoint.json', 'workflow/delegations.json', 'workflow/decisions.json', 'workflow/clarifications.json',
                 'progress/facts.jsonl', 'tasks.md'):
        shutil.copyfile(RUN842 / name, feature / name)
    return Ctx(base, RUN842_FEATURE)


def run842_report(base, now=RUN842_NOW, schema='v2'):
    """The document the model builds for the frozen #842 fixture, at a fixed clock: the internal v2 base document by default
    (the phase 1 tests pin it), or the v3 projection."""
    from datetime import datetime
    from sanduq_progress import model
    ctx = run842_ctx(base)
    build = model.build if schema == 'v3' else model.build_v2
    return build(ctx, datetime.fromisoformat(now.replace('Z', '+00:00')), 1, {}), ctx
