import { test } from 'node:test';
import {
  assert, asyncCli, check, cli, collectBatch, env, fixture, fs, here, path, plan, publicJson, runBatch, runner, spawn, spawnSync, tmp, until, validatePlan,
} from './execution-helpers.mjs';

test('default rerun executes no additional program; explicit latest retry executes once and preserves attempts', async () => {
  const marker = path.join(tmp, 'intentional.txt'), f = path.join(tmp, 'intentional.json');
  const p = plan('intentional', [check('count launches', 'once', marker, '1')]);
  fs.writeFileSync(f, JSON.stringify(p), 'utf8');
  const first = publicJson(cli(runner, ['run', '--plan', f]));
  const raw = fs.readFileSync(path.join(tmp, 'checks/intentional', first.attempt_id, 'result.json'), 'utf8');
  const refused = publicJson(cli(runner, ['run', '--plan', f, '--max-bytes', '2048']), 2048, 4);
  assert.equal(refused.requires_explicit_retry, true); assert.equal(refused.execution_performed, false);
  assert.equal(refused.attempt_id, first.attempt_id); assert.equal(fs.readFileSync(marker, 'utf8'), 'executed\n');
  const second = publicJson(cli(runner, ['run', '--plan', f, '--retry-of', first.attempt_id]));
  assert.equal(second.retry_of, first.attempt_id); assert.notEqual(second.attempt_id, first.attempt_id);
  assert.equal(fs.readFileSync(marker, 'utf8'), 'executed\nexecuted\n');
  assert.equal(fs.readFileSync(path.join(tmp, 'checks/intentional', first.attempt_id, 'result.json'), 'utf8'), raw);
  const wrong = cli(runner, ['run', '--plan', f, '--retry-of', 'attempt-1-aabbccddeeff']); assert.equal(wrong.status, 2); assert.match(wrong.stderr, /latest existing attempt/);
  const stale = cli(runner, ['run', '--plan', f, '--retry-of', first.attempt_id]); assert.equal(stale.status, 2);
  assert.equal(fs.readFileSync(marker, 'utf8'), 'executed\nexecuted\n');
  const before = fs.readdirSync(path.join(tmp, 'checks/intentional')).sort();
  const one = cli(runner, ['collect', '--batch', 'intentional']), two = cli(runner, ['collect', '--batch', 'intentional']);
  assert.equal(one.stdout, two.stdout); assert.deepEqual(fs.readdirSync(path.join(tmp, 'checks/intentional')).sort(), before);
});
test('explicit retry refuses live execution ownership', async () => {
  const marker = path.join(tmp, 'live-retry.txt'), f = path.join(tmp, 'live-retry.json');
  fs.writeFileSync(f, JSON.stringify(plan('live-retry', [check('live retry guard', 'once', marker, '700')])));
  const first = publicJson(cli(runner, ['run', '--plan', f]));
  const next = asyncCli(['run', '--plan', f, '--retry-of', first.attempt_id]);
  await until(() => fs.readFileSync(marker, 'utf8').split('\n').length === 3);
  const busy = await asyncCli(['run', '--plan', f, '--retry-of', first.attempt_id]).done;
  assert.equal(busy.code, 3); assert.equal(JSON.parse(busy.stdout).busy, true);
  assert.equal((await next.done).code, 0); assert.equal(fs.readFileSync(marker, 'utf8'), 'executed\nexecuted\n');
});
test('retry manifest binds argv/env and worktree identity, while allowing ordinary file edits', async () => {
  const cwd = path.join(tmp, 'identity-cwd'); fs.mkdirSync(cwd);
  const p = plan('identity', [check('manifest check', 'argv')], { cwd });
  const first = await runBatch(p, tmp);
  await assert.rejects(runBatch({ ...p, env: { CHANGED: '1' } }, tmp, { retryOf: first.attempt_id }), /manifest\/worktree identity changed/);
  await assert.rejects(runBatch({ ...p, checks: [check('manifest check', 'argv', 'changed')] }, tmp, { retryOf: first.attempt_id }), /manifest\/worktree identity changed/);
  fs.writeFileSync(path.join(cwd, 'ordinary-edit.txt'), 'source changed', 'utf8');
  const second = await runBatch(p, tmp, { retryOf: first.attempt_id }); assert.equal(second.status, 'successful');
  const replaced = path.join(tmp, 'identity-cwd-old'); fs.renameSync(cwd, replaced); fs.mkdirSync(cwd);
  await assert.rejects(runBatch(p, tmp, { retryOf: second.attempt_id }), /manifest\/worktree identity changed/);
  const gitCwd = path.join(tmp, 'git-identity'); fs.mkdirSync(gitCwd);
  assert.equal(spawnSync('git', ['init', '-q'], { cwd: gitCwd, windowsHide: true }).status, 0);
  const gp = plan('git-identity', [check('registered worktree', 'argv')], { cwd: gitCwd });
  const registered = await runBatch(gp, tmp);
  fs.renameSync(path.join(gitCwd, '.git'), path.join(gitCwd, '.git-previous'));
  assert.equal(spawnSync('git', ['init', '-q'], { cwd: gitCwd, windowsHide: true }).status, 0);
  await assert.rejects(runBatch(gp, tmp, { retryOf: registered.attempt_id }), /manifest\/worktree identity changed/);
});
test('argv preserves spaces, empty arguments, Unicode, quotes and literal newlines', async () => {
  const args = ['a b', '', 'العربية ☕', '"quoted"', "'single'", 'line1\nline2', '$(never-run)', '`literal`'];
  const r = await runBatch(plan('argv', [check('argv data', 'argv', ...args)]), tmp);
  assert.equal(r.status, 'successful');
  assert.deepEqual(JSON.parse(fs.readFileSync(r.checks[0].artifacts.stdout, 'utf8')), args);
});
test('empty executable is rejected before an attempt is created', () => {
  assert.throws(() => validatePlan(plan('empty', [{ name: 'empty launcher', argv: ['', 'x'], timeout_s: 1 }])), /executable must be nonempty/);
  assert.equal(fs.existsSync(path.join(tmp, 'checks/empty')), false);
  const f = path.join(tmp, 'empty-launch.json'); fs.writeFileSync(f, JSON.stringify(plan('empty', [{ name: 'empty launcher', argv: ['', ''], timeout_s: 1 }])));
  const result = cli(runner, ['run', '--plan', f]); assert.equal(result.status, 2); assert.match(result.stderr, /executable must be nonempty/);
});
test('later nonexistent executable rejects the whole plan before any side effect or attempt', async () => {
  const marker = path.join(tmp, 'preflight-marker.txt'), f = path.join(tmp, 'preflight-plan.json');
  const p = plan('preflight', [check('early side effect', 'once', marker, '1'), { name: 'later missing launcher', argv: ['missing-pr85-launcher'], timeout_s: 1 }]);
  assert.throws(() => validatePlan(p), /executable not found/);
  await assert.rejects(runBatch(p, tmp), /executable not found/);
  fs.writeFileSync(f, JSON.stringify(p), 'utf8');
  const result = cli(runner, ['run', '--plan', f]);
  assert.equal(result.status, 2); assert.match(result.stderr, /executable not found/);
  assert.equal(result.stdout, ''); assert.equal(fs.existsSync(marker), false);
  assert.equal(fs.existsSync(path.join(tmp, 'checks/preflight')), false);
});

test('preflight uses batch and check cwd/env for PATH and explicit relative launchers without executing them', () => {
  const base = path.join(tmp, 'resolution-base'), other = path.join(tmp, 'resolution-check');
  const name = 'preflight-only' + (process.platform === 'win32' ? '.exe' : '');
  for (const dir of [path.join(base, 'batch-bin'), path.join(other, 'check-bin'), other]) {
    fs.mkdirSync(dir, { recursive: true });
    // Invalid native contents still pass file resolution: validation must not
    // try to launch arbitrary programs to determine whether they are usable.
    fs.writeFileSync(path.join(dir, name), 'validation must only inspect this file', { encoding: 'utf8', mode: 0o700 });
  }
  const batchCheck = { name: 'batch PATH', argv: [name], timeout_s: 1 };
  const localCheck = { name: 'check PATH', argv: [name], timeout_s: 1, cwd: other, env: { [process.platform === 'win32' ? 'Path' : 'PATH']: 'check-bin' } };
  const p = plan('resolution', [batchCheck, localCheck, { name: 'relative launcher', argv: ['./' + name], timeout_s: 1, cwd: other }], { cwd: base, env: { PATH: 'batch-bin' } });
  assert.equal(validatePlan(p), p);
  assert.throws(() => validatePlan({ ...p, checks: [{ ...batchCheck, cwd: other }] }), /executable not found/);
  assert.throws(() => validatePlan({ ...p, checks: [{ ...localCheck, cwd: base }] }), /executable not found/);
  assert.throws(() => validatePlan({ ...p, checks: [{ ...batchCheck, env: { PATH: 'missing-bin' } }] }), /executable not found/);
  assert.throws(() => validatePlan({ ...p, checks: [{ ...batchCheck, env: { PATH: '' } }] }), /executable not found/);
  assert.equal(fs.existsSync(path.join(tmp, 'checks/resolution')), false);
});

test('validated per-check PATH/cwd and explicit environment overrides also govern execution', async () => {
  const cwd = path.join(tmp, 'execution-resolution'); fs.mkdirSync(cwd);
  const p = plan('execution-resolution', [{ name: 'effective command', argv: [path.basename(process.execPath), '-e', 'console.log(JSON.stringify({cwd:process.cwd(),value:process.env.CHECK_VALUE}))'], timeout_s: 10,
    cwd, env: { [process.platform === 'win32' ? 'Path' : 'PATH']: path.dirname(process.execPath), CHECK_VALUE: 'check' } }], { env: { PATH: 'missing-bin', CHECK_VALUE: 'batch' } });
  const r = await runBatch(p, tmp);
  assert.equal(r.status, 'successful');
  assert.deepEqual(JSON.parse(fs.readFileSync(r.checks[0].artifacts.stdout, 'utf8')), { cwd, value: 'check' });
});

test('POSIX preflight rejects files without execute permission and searches later PATH entries', { skip: process.platform === 'win32' }, async () => {
  const first = path.join(tmp, 'non-executable'), second = path.join(tmp, 'executable');
  for (const dir of [first, second]) fs.mkdirSync(dir);
  const file = path.join(first, 'launcher');
  fs.writeFileSync(file, 'not executable', { encoding: 'utf8', mode: 0o600 });
  fs.writeFileSync(path.join(second, 'launcher'), 'executable file', { encoding: 'utf8', mode: 0o700 });
  const c = { name: 'permission check', argv: [file], timeout_s: 1 };
  await assert.rejects(runBatch(plan('permissions', [c]), tmp), /executable not found/);
  assert.equal(fs.existsSync(path.join(tmp, 'checks/permissions')), false);
  assert.doesNotThrow(() => validatePlan(plan('permissions-path', [{ ...c, argv: ['launcher'] }], { env: { PATH: [first, second].join(path.delimiter) } })));
});

test('invalid argv, duplicate names, undefined env and missing timeouts fail validation', () => {
  for (const c of [{ name: 'x', argv: ['node', null], timeout_s: 1 }, { name: 'x', argv: ['node'] }, { ...check('x', 'argv'), env: { BAD: undefined } }]) assert.throws(() => validatePlan(plan('bad', [c])));
  assert.throws(() => validatePlan(plan('bad', [check('same', 'argv'), check('same', 'argv')])), /unique/);
});
test('explicit Python placeholder uses a real interpreter and preserves data', async t => {
  const probe = spawnSync(process.platform === 'win32' ? 'python.exe' : 'python3', ['-c', 'import sys; print(sys.executable)'], { encoding: 'utf8', windowsHide: true });
  if (probe.status !== 0) return t.skip('real Python unavailable');
  const py = probe.stdout.trim();
  const args = ['space here', '', 'عربي', 'line\nnext'];
  const r = await runBatch(plan('python', [{ name: 'Python argv', argv: ['{{python}}', path.join(here, 'fixtures/check-fixture.py'), ...args], timeout_s: 10 }], { interpreters: { python: py }, env: { PYTHONUTF8: '1' } }), tmp);
  assert.equal(r.status, 'successful');
  assert.deepEqual(JSON.parse(fs.readFileSync(r.checks[0].artifacts.stdout, 'utf8')), args);
  assert.throws(() => validatePlan(plan('missing-python', [{ name: 'Python missing', argv: ['{{python}}'], timeout_s: 1 }])), /explicit real Python/);
});
test('program failures retain meaningful names, codes and following checks', async () => {
  const r = await runBatch(plan('failures', [check('parser regression', 'fail'), check('later validation', 'argv')]), tmp);
  assert.equal(r.status, 'failed');
  assert.deepEqual(r.checks.map(c => [c.name, c.status, c.exit_code]), [['parser regression', 'failed', 17], ['later validation', 'passed', 0]]);
});
test('actual OS spawn failures are distinct from nonzero program exits', async () => {
  const f = path.join(tmp, 'invalid-native.exe'); fs.writeFileSync(f, 'this is not an executable', { encoding: 'utf8', mode: 0o700 });
  const r = await runBatch(plan('spawn-error', [{ name: 'OS launcher failure', argv: [f], timeout_s: 2 }]), tmp);
  assert.equal(r.checks[0].status, 'launch_failed'); assert.equal(r.checks[0].exit_code, null); assert.ok(r.checks[0].launch_error);
});
test('Windows shims are rejected before an attempt without a shell fallback', { skip: process.platform !== 'win32' }, async () => {
  const f = path.join(tmp, 'unsupported.cmd'); fs.writeFileSync(f, '@echo off\r\necho should-not-execute', 'utf8');
  const p = plan('shim', [{ name: 'unsupported shim', argv: [f], timeout_s: 1 }]);
  assert.throws(() => validatePlan(p), /unsupported Windows shim/);
  await assert.rejects(runBatch(p, tmp), /unsupported Windows shim/);
  assert.equal(fs.existsSync(path.join(tmp, 'checks/shim')), false);
});
test('repeated attempts append and collector exposes prior failures', async () => {
  const p = plan('repeat', [check('first failure', 'fail')]);
  const first = await runBatch(p, tmp);
  const raw = fs.readFileSync(path.join(tmp, 'checks/repeat', first.attempt_id, 'result.json'), 'utf8');
  await runBatch(p, tmp, { retryOf: first.attempt_id });
  const collected = collectBatch(tmp, 'repeat');
  assert.equal(collected.total_attempts, 2); assert.deepEqual(collected.attempts.map(a => a.status), ['failed', 'failed']);
  const bounded = collectBatch(tmp, 'repeat', null, 1); assert.equal(bounded.omitted_attempts, 1); assert.equal(bounded.truncated, true); assert.equal(bounded.omitted_status_counts.failed, 1);
  assert.equal(fs.readFileSync(path.join(tmp, 'checks/repeat', first.attempt_id, 'result.json'), 'utf8'), raw);
});
test('incomplete attempts expose completed checkpoints and pending checks', () => {
  const dir = path.join(tmp, 'checks/incomplete/attempt-123-aabbccddeeff'); fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'plan.json'), JSON.stringify(plan('incomplete', [check('done', 'argv'), check('pending', 'argv')])));
  fs.writeFileSync(path.join(dir, 'attempt.json'), JSON.stringify({ attempt_id: path.basename(dir), status: 'running', checks: [{ name: 'done', status: 'pending', exit_code: null }, { name: 'pending', status: 'pending', exit_code: null }] }));
  fs.writeFileSync(path.join(dir, '001.result.json'), JSON.stringify({ name: 'done', status: 'failed', exit_code: 17 }));
  const r = collectBatch(tmp, 'incomplete').attempts[0]; assert.equal(r.status, 'incomplete'); assert.deepEqual(r.checks.map(c => c.status), ['failed', 'pending']);
  const initial = JSON.parse(fs.readFileSync(path.join(dir, 'attempt.json'), 'utf8'));
  initial.owner_pid = process.pid;
  fs.writeFileSync(path.join(dir, 'attempt.json'), JSON.stringify(initial));
  fs.writeFileSync(path.join(dir, '002.started.json'), JSON.stringify({ pid: process.pid, started_at: new Date().toISOString() }));
  const live = collectBatch(tmp, 'incomplete');
  assert.deepEqual(live.check_status_counts, { failed: 1, running: 1 });
  assert.equal(live.attempts[0].checks[1].status, 'running');
});
