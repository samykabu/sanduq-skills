import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { runBatch, collectBatch, validatePlan } from '../check-runner.mjs';
import { acquireBatchLock, alive, containmentClosed } from '../process-tools.mjs';
import { excerptFile, projectResult, redact } from '../bounded.mjs';
import { executionProgress } from '../delegate.mjs';
import { encodeReceipt } from '../check-receipt.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const runner = path.join(here, '../check-runner.mjs'), driver = path.join(here, '../delegate.mjs');
const fixture = path.join(here, 'fixtures/check-fixture.mjs');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'delegate-execution-'));
const env = { ...process.env, DELEGATE_RUNS_DIR: tmp };
const plan = (id, checks, extra = {}) => ({ batch_id: id, cwd: tmp, checks, ...extra });
const check = (name, mode, ...args) => ({ name, argv: ['{{node}}', fixture, mode, ...args], timeout_s: 10 });
const cli = (file, args, over = {}) => spawnSync(process.execPath, [file, ...args], { env: { ...env, ...over }, encoding: 'utf8', windowsHide: true, shell: false, timeout: 30000, maxBuffer: 4 * 1024 * 1024 });
const delay = ms => new Promise(r => setTimeout(r, ms));
function processLive(pid) {
  if (!alive(pid)) return false;
  try { return !fs.readFileSync(`/proc/${pid}/stat`, 'utf8').includes(') Z '); } catch { return true; }
}
async function until(fn) {
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) { const v = fn(); if (v) return v; await delay(20); }
  throw new Error('fixture condition not reached within 10s');
}
function asyncCli(args) {
  const p = spawn(process.execPath, [runner, ...args], { env, windowsHide: true, shell: false, stdio: ['ignore', 'pipe', 'pipe'] });
  let stdout = '', stderr = '';
  p.stdout.on('data', c => stdout += c); p.stderr.on('data', c => stderr += c);
  return { child: p, done: new Promise((resolve, reject) => { p.on('error', reject); p.on('close', code => resolve({ code, stdout, stderr })); }) };
}
after(() => fs.rmSync(tmp, { recursive: true, force: true }));

test('overlapping and escaped secrets are replaced longest-first without rewriting replacement markers', () => {
  const values = ['alpha', 'alphaomega', 'alpha', 'redacted', '界\n"alphaomega"', 'a+b', 'a+b(c)'];
  const sample = 'alphaomega alpha a+b(c) a+b ' + '界\n"alphaomega"' + ' ' + JSON.stringify('界\n"alphaomega"') + ' [redacted]';
  const hidden = redact(sample, values);
  assert.ok(!hidden.includes('omega')); assert.ok(!hidden.includes('(c)')); assert.ok(!hidden.includes('界'));
  assert.ok(!hidden.includes('[[redacted]]')); assert.equal(redact(hidden, values), hidden);
  assert.equal(redact('password="private-value"'), 'password=[redacted]');
  assert.equal(redact('alphaomega alpha', ['alpha', 'alphaomega']), '[redacted] [redacted]');
});

test('crossing secret overlaps redact the complete union without suffix leakage', () => {
  assert.equal(redact('abcdef', ['abc', 'bcdef']), '[redacted]');
  assert.equal(redact('abcdef', ['bcdef', 'abc', 'abc']), '[redacted]');
});

test('chained secret overlaps redact every covered character once', () => {
  assert.equal(redact('abcdefghij', ['abc', 'cdef', 'efgh', 'hij']), '[redacted]');
  assert.equal(redact('abcdefghij', ['hij', 'efgh', 'cdef', 'abc']), '[redacted]');
});

test('Unicode secret overlaps preserve surrounding text without leaking suffixes', () => {
  assert.equal(redact('前😀界語文後', ['😀界', '界語', '語文']), '前[redacted]後');
  assert.equal(redact('a+b(c)\n界', ['a+b', '+b(c)\n界']), '[redacted]');
  assert.equal(redact('a+b(c)\\n界', ['a+b', '+b(c)\n界']), '[redacted]');
});

test('disjoint secret unions preserve every nonsecret gap', () => {
  assert.equal(redact('abcdef / visible😀 / uvwxyz', ['abc', 'bcdef', 'uvw', 'wxyz']), '[redacted] / visible😀 / [redacted]');
  assert.equal(redact('abc - bcdef', ['abc', 'bcdef']), '[redacted] - [redacted]');
});
test('validation, malformed input and launch diagnostics cannot expose explicit or inherited credentials', () => {
  const secret = 'unlabelled-alphaomega', inherited = 'inherited-private-credential';
  const f = path.join(tmp, 'secret-validation.json');
  for (const p of [
    plan('invalid-secret-timeout', [{ ...check(secret, 'argv'), timeout_s: -1 }], { env: { CUSTOM: secret } }),
    plan('invalid-inherited-timeout', [{ ...check(inherited, 'argv'), timeout_s: 0 }]),
    plan('invalid-secret-cwd', [check('cwd input', 'argv')], { cwd: path.join(tmp, secret), env: { CUSTOM: secret } }),
    { env: { CUSTOM: secret }, checks: [null], batch_id: secret, cwd: tmp },
  ]) {
    fs.writeFileSync(f, JSON.stringify(p), 'utf8');
    const r = cli(runner, ['run', '--plan', f], { CHECK_API_KEY: inherited });
    assert.equal(r.status, 2);
    assert.ok(!r.stderr.includes(secret)); assert.ok(!r.stderr.includes(inherited));
  }
  fs.writeFileSync(f, '{"env":{"CUSTOM":"' + secret + '"},"broken":!}', 'utf8');
  const malformed = cli(runner, ['run', '--plan', f]); assert.equal(malformed.status, 2); assert.ok(!malformed.stderr.includes(secret));
  fs.writeFileSync(f, JSON.stringify(plan('secret-launch', [{ name: secret + ' ' + inherited, argv: [path.join(tmp, secret)], timeout_s: 1 }], { env: { CUSTOM: secret } })), 'utf8');
  const launch = cli(runner, ['run', '--plan', f], { CHECK_API_KEY: inherited });
  assert.equal(launch.status, 1); assert.ok(!launch.stdout.includes(secret)); assert.ok(!launch.stdout.includes(inherited));
  assert.ok(!launch.stderr.includes(secret)); assert.ok(!launch.stderr.includes(inherited));
  assert.equal(JSON.parse(launch.stdout).checks[0].status, 'launch_failed');
  const invalidNative = path.join(tmp, secret + '.exe'); fs.writeFileSync(invalidNative, 'not an executable');
  fs.writeFileSync(f, JSON.stringify(plan('secret-native-launch', [{ name: secret + ' ' + inherited, argv: [invalidNative], timeout_s: 1 }], { env: { CUSTOM: secret } })), 'utf8');
  const native = cli(runner, ['run', '--plan', f], { CHECK_API_KEY: inherited });
  assert.equal(native.status, 1); assert.equal(JSON.parse(native.stdout).checks[0].status, 'launch_failed');
  assert.ok(!native.stdout.includes(secret)); assert.ok(!native.stdout.includes(inherited));
  assert.ok(!native.stderr.includes(secret)); assert.ok(!native.stderr.includes(inherited));
});
test('prompt root failure retains detached-stdio descendant ownership until closure before next check or retry', async () => {
  const marker = path.join(tmp, 'background-marker.json'), release = path.join(tmp, 'background-release'), next = path.join(tmp, 'background-next');
  const p = plan('background', [check('background parent failure', 'background', marker, release, '17'), check('no overlap', 'assert-stopped', marker, next)]);
  const f = path.join(tmp, 'background-plan.json'); fs.writeFileSync(f, JSON.stringify(p));
  const run = asyncCli(['run', '--plan', f]);
  try {
    const data = await until(() => { try { return JSON.parse(fs.readFileSync(marker, 'utf8')); } catch { return null; } });
    await until(() => !processLive(data.root_pid));
    assert.equal(processLive(data.pid), true); assert.equal(fs.existsSync(next), false);
    const attempt = fs.readdirSync(path.join(tmp, 'checks/background')).find(n => n.startsWith('attempt-'));
    const blocked = cli(runner, ['run', '--plan', f, '--retry-of', attempt]); assert.equal(blocked.status, 3);
    fs.writeFileSync(release, 'release');
    const result = await run.done; assert.equal(result.code, 1, result.stderr);
    const receipt = JSON.parse(result.stdout); assert.equal(receipt.checks[0].exit_code, 17);
    assert.equal(receipt.checks[0].containment.state, 'closed'); assert.equal(receipt.checks[1].status, 'passed');
    assert.equal(processLive(data.pid), false);
    const again = cli(runner, ['run', '--plan', f, '--retry-of', receipt.attempt_id]);
    assert.equal(again.status, 1, again.stderr); assert.notEqual(JSON.parse(again.stdout).attempt_id, receipt.attempt_id);
  } finally { fs.writeFileSync(release, 'release'); await run.done; }
});
test('timeout after prompt root exit stops detached descendants before the next check', async () => {
  const marker = path.join(tmp, 'background-timeout.json'), release = path.join(tmp, 'background-timeout-release'), next = path.join(tmp, 'background-timeout-next');
  const r = await runBatch(plan('background-timeout', [{ ...check('background timeout', 'background', marker, release), timeout_s: 1.5 }, check('closed tree before next', 'assert-stopped', marker, next)]), tmp);
  assert.equal(r.checks[0].status, 'timeout'); assert.equal(r.checks[0].exit_code, 0);
  assert.equal(r.checks[0].containment.state, 'closed'); assert.equal(r.checks[1].status, 'passed');
  const data = JSON.parse(fs.readFileSync(marker, 'utf8')); assert.equal(processLive(data.pid), false);
});
test('supervisor loss permits only proof-backed recovery and otherwise retains an unresolved lease', async () => {
  const marker = path.join(tmp, 'owner-loss.json'), release = path.join(tmp, 'owner-loss-release'), next = path.join(tmp, 'owner-loss-next');
  const f = path.join(tmp, 'owner-loss-plan.json'); fs.writeFileSync(f, JSON.stringify(plan('owner-loss', [check('owner loss', 'background', marker, release), check('next after ownership proof', 'assert-stopped', marker, next)])));
  const run = asyncCli(['run', '--plan', f]);
  try {
    const data = await until(() => { try { return JSON.parse(fs.readFileSync(marker, 'utf8')); } catch { return null; } });
    const batch = path.join(tmp, 'checks/owner-loss'), attempt = fs.readdirSync(batch).find(n => n.startsWith('attempt-'));
    const started = JSON.parse(fs.readFileSync(path.join(batch, attempt, '001.started.json'), 'utf8'));
    run.child.kill('SIGKILL'); await run.done;
    await until(() => !processLive(started.pid));
    assert.equal(fs.existsSync(next), false);
    if (process.platform === 'win32') await until(() => !processLive(data.pid));
    fs.writeFileSync(release, 'release');
    const proven = containmentClosed(started.containment);
    const retry = cli(runner, ['run', '--plan', f, '--retry-of', attempt]);
    const collection = collectBatch(tmp, 'owner-loss'); assert.equal(collection.status_counts.incomplete, 1);
    if (proven) {
      assert.equal(processLive(data.pid), false); assert.equal(retry.status, 0, retry.stderr);
      assert.equal(collection.status_counts.successful, 1);
    } else {
      assert.equal(retry.status, 3, retry.stderr);
      assert.equal(fs.readdirSync(batch).filter(n => n.startsWith('attempt-')).length, 1);
      assert.equal(collection.attempts[0].checks[0].containment.state, 'unresolved');
      assert.equal(fs.existsSync(path.join(batch, 'execution.lock')), true);
      if (process.platform === 'win32') assert.equal(processLive(data.pid), false);
    }
  } finally { fs.writeFileSync(release, 'release'); }
});
test('helper hard loss leaves an unresolved lease and skips later checks and all retries', async () => {
  const marker = path.join(tmp, 'helper-loss.json'), release = path.join(tmp, 'helper-loss-release'), next = path.join(tmp, 'helper-loss-next');
  const f = path.join(tmp, 'helper-loss-plan.json'); fs.writeFileSync(f, JSON.stringify(plan('helper-loss', [check('helper hard loss', 'kill-helper', marker, release), check('must stay skipped', 'once', next, '1')])));
  try {
    const result = cli(runner, ['run', '--plan', f]); assert.equal(result.status, 1, result.stderr);
    const r = JSON.parse(result.stdout); assert.equal(r.status_provenance.primary, 'containment_unresolved');
    assert.equal(r.checks[0].status, 'containment_unresolved'); assert.equal(r.checks[1].status, 'skipped'); assert.equal(fs.existsSync(next), false);
    const retry = cli(runner, ['run', '--plan', f, '--retry-of', r.attempt_id]); assert.equal(retry.status, 3);
    const collected = collectBatch(tmp, 'helper-loss'); assert.equal(collected.attempts[0].checks[0].containment.state, 'unresolved');
  } finally { fs.writeFileSync(release, 'release'); }
});

function publicJson(result, budget = 16384, expectedExit = 0) {
  assert.equal(result.status, expectedExit, result.stderr);
  const bytes = Buffer.byteLength(result.stdout, 'utf8');
  assert.ok(bytes <= budget, `emitted ${bytes} bytes, budget ${budget}`);
  const parsed = JSON.parse(result.stdout);
  assert.equal(parsed.projection.emitted_bytes, bytes);
  return parsed;
}
function storedAttempt(batchId, number, checks, extra = {}) {
  const id = `attempt-${1700000000000 + number}-${number.toString(16).padStart(12, '0')}`;
  const dir = path.join(tmp, 'checks', batchId, id); fs.mkdirSync(dir, { recursive: true });
  const p = plan(batchId, checks.map((c, i) => check(c.name || `check ${i}`, 'fail')));
  fs.writeFileSync(path.join(dir, 'plan.json'), JSON.stringify(p), 'utf8');
  fs.writeFileSync(path.join(dir, 'result.json'), JSON.stringify({ schema: 'delegate-task.check-batch.v1', batch_id: batchId, attempt_id: id, status: 'failed', status_provenance: null, checks, ...extra }), 'utf8');
  return { id, dir };
}

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
test('many failed checks emit whole records and aggregate failure counts inside default and minimum byte budgets', () => {
  const f = path.join(tmp, 'many-checks.json');
  const p = plan('many-checks', Array.from({ length: 100 }, (_, i) => ({ name: `فشل ☕ ${i}`, argv: ['not-installed-batch-fixture'], timeout_s: 1 })));
  fs.writeFileSync(f, JSON.stringify(p), 'utf8');
  const r = publicJson(cli(runner, ['run', '--plan', f]), 16384, 1);
  assert.equal(r.total_checks, 100); assert.equal(r.check_status_counts.launch_failed, 100); assert.equal(r.status, 'failed');
  assert.ok(r.projection.truncated); assert.ok(r.projection.next_cursor || r.projection.narrow);
  for (const c of r.checks) { assert.equal(c.status, 'launch_failed'); assert.equal(c.exit_code, null); assert.ok(c.name.startsWith('فشل')); }
  const tiny = publicJson(cli(runner, ['run', '--plan', f, '--max-bytes', '2048']), 2048, 4);
  assert.equal(tiny.status, 'failed'); assert.equal(tiny.check_status_counts.launch_failed, 100);
  assert.ok(tiny.projection.omitted_checks > 0);
  const restored = publicJson(cli(runner, ['collect', '--batch', 'many-checks', '--attempt', r.attempt_id, '--max-bytes', '2048', '--output-bytes', '0'] ), 2048);
  assert.equal(restored.check_status_counts.launch_failed, 100);
});
test('many attempts, Unicode and oversized metadata remain valid within total emitted UTF-8 budgets', () => {
  const failed = Array.from({ length: 100 }, (_, i) => ({ name: `فشل 😀 ${i}`, status: 'failed', exit_code: 17, signal: null, launch_error: null, error: null,
    oversized_metadata: '界'.repeat(1500) }));
  for (let i = 1; i <= 24; i++) storedAttempt('many-attempts', i, failed, { ignored_extra: 'ع'.repeat(20000) });
  for (const budget of [2048, 4096, 16384, 32768]) {
    const r = publicJson(cli(runner, ['collect', '--batch', 'many-attempts', '--limit', '20', '--max-bytes', String(budget)]), budget);
    assert.equal(r.status, 'failed'); assert.equal(r.status_provenance.primary, 'attempt_history'); assert.equal(r.total_attempts, 24);
    assert.equal(r.status_counts.failed, 24); assert.equal(r.check_status_counts.failed, 2400); assert.equal(r.total_checks, 2400);
    assert.equal(r.omitted_status_counts.failed, 4); assert.ok(r.projection.truncated);
    for (const a of r.attempts) { assert.equal(a.status_provenance, null); for (const c of a.checks) assert.equal(c.oversized_metadata, failed[c.check_index].oversized_metadata); }
  }
});
test('collection cursor traverses records once and narrowing retrieves an oversized record without log loading', () => {
  const { id, dir } = storedAttempt('pages', 1, Array.from({ length: 8 }, (_, i) => ({ name: `record ${i} 😀`, status: 'failed', exit_code: 17, signal: null, launch_error: null, error: null })));
  const seen = [], base = ['collect', '--batch', 'pages', '--attempt', id, '--max-bytes', '2048', '--output-bytes', '0'];
  let cursor;
  do {
    const r = publicJson(cli(runner, [...base, ...(cursor ? ['--cursor', cursor] : [])]), 2048);
    for (const a of r.attempts) for (const c of a.checks) seen.push(c.check_index);
    cursor = r.projection.next_cursor;
  } while (cursor);
  assert.deepEqual(seen, [0, 1, 2, 3, 4, 5, 6, 7]);
  const log = path.join(dir, 'huge.log'); const fd = fs.openSync(log, 'w'); fs.ftruncateSync(fd, 20 * 1024 * 1024); fs.closeSync(fd);
  const raw = JSON.parse(fs.readFileSync(path.join(dir, 'result.json'), 'utf8'));
  raw.checks[0].artifacts = { stdout: log }; fs.writeFileSync(path.join(dir, 'result.json'), JSON.stringify(raw));
  const narrow = publicJson(cli(runner, [...base, '--check-index', '0']), 2048);
  assert.equal(narrow.attempts[0].checks[0].output.stdout.total_bytes, 20 * 1024 * 1024);
  assert.equal(narrow.attempts[0].checks[0].output.stdout.head, '');
  assert.equal(cli(runner, ['collect', '--batch', 'pages', '--attempt', id, '--check-index', '0', '--output-bytes', '3']).status, 0);
  const oldCursor = publicJson(cli(runner, base), 2048).projection.next_cursor;
  storedAttempt('pages', 2, raw.checks);
  const stale = cli(runner, [...base, '--cursor', oldCursor]); assert.equal(stale.status, 2); assert.match(stale.stderr, /cursor no longer matches/);
});
test('byte limits reject unsafe minima before executing a plan and count the exact final newline', () => {
  const marker = path.join(tmp, 'bad-budget.txt'), f = path.join(tmp, 'bad-budget.json');
  fs.writeFileSync(f, JSON.stringify(plan('bad-budget', [check('not launched', 'once', marker, '1')])));
  for (const budget of ['2047', 'NaN', '16384.5', '1048577']) assert.equal(cli(runner, ['run', '--plan', f, '--max-bytes', budget]).status, 2);
  assert.equal(fs.existsSync(marker), false);
  const text = encodeReceipt({ batch_id: 'busy', busy: true }, 2048);
  assert.ok(text.endsWith('\n')); assert.equal(JSON.parse(text).projection.emitted_bytes, Buffer.byteLength(text, 'utf8'));
  assert.equal(JSON.parse(text).status, null); assert.equal(JSON.parse(text).total_checks, null);
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
test('large single records produce bounded valid JSON, truncation metadata and redaction', async () => {
  const r = await runBatch(plan('flood', [check('oversized record', 'flood')], { env: { CHECK_SECRET: 'sensitive-fixture-value' } }), tmp);
  const s = JSON.stringify(r);
  assert.ok(s.length < 20000); assert.ok(!s.includes('sensitive-fixture-value'));
  assert.equal(r.checks[0].output.stdout.truncated, true);
  assert.ok(r.checks[0].output.stdout.omitted_bytes > 1000000);
  assert.ok(fs.statSync(r.checks[0].artifacts.stdout).size > 1000000);
  const c = cli(runner, ['collect', '--batch', 'flood', '--output-bytes', '512']);
  assert.equal(c.status, 0, c.stderr); assert.ok(JSON.parse(c.stdout).attempts[0].checks[0].output.stdout.truncated);
});
test('CLI batch exits 1 for a named failure while oversized output remains valid bounded JSON', () => {
  const f = path.join(tmp, 'cli-failure.json');
  fs.writeFileSync(f, JSON.stringify(plan('cli-failure', [check('named CLI failure', 'fail'), check('large CLI output', 'flood')], { env: { CHECK_SECRET: 'cli-private-value' } })), 'utf8');
  const result = cli(runner, ['run', '--plan', f]);
  assert.equal(result.status, 1, result.stderr);
  assert.ok(result.stdout.length < 20000); assert.ok(!result.stdout.includes('cli-private-value'));
  const r = JSON.parse(result.stdout); assert.equal(r.checks[0].exit_code, 17); assert.equal(r.checks[1].status, 'passed'); assert.ok(r.checks[1].output.stdout.truncated);
});
test('excerpts omit boundary fragments rather than leaking partial credentials', () => {
  const f = path.join(tmp, 'boundary.log');
  fs.writeFileSync(f, 'token=' + 'x'.repeat(5000), 'utf8');
  const r = excerptFile(f, { head: 30, tail: 30 });
  assert.equal(r.head, ''); assert.equal(r.tail, ''); assert.equal(r.omitted_bytes, 5006);
});
test('two concurrent owners execute the same batch exactly once', async () => {
  const marker = path.join(tmp, 'once.txt'), f = path.join(tmp, 'race.json');
  fs.writeFileSync(f, JSON.stringify(plan('race', [check('single execution', 'once', marker, '1200')])));
  const first = asyncCli(['run', '--plan', f]);
  await until(() => fs.existsSync(marker));
  const second = await asyncCli(['run', '--plan', f]).done;
  assert.equal(second.code, 3, second.stderr); assert.equal(JSON.parse(second.stdout).busy, true);
  assert.equal((await first.done).code, 0);
  assert.equal(fs.readFileSync(marker, 'utf8'), 'executed\n');
});
test('lock recovery proves death; live and incomplete owners remain protected', async () => {
  const lock = path.join(tmp, 'lock');
  const release = acquireBatchLock(lock); assert.ok(release);
  assert.equal(acquireBatchLock(lock), null); release();
  fs.mkdirSync(lock); assert.equal(acquireBatchLock(lock), null); fs.rmdirSync(lock);
  const child = spawn(process.execPath, ['-e', ''], { windowsHide: true });
  await new Promise(r => child.on('close', r));
  fs.mkdirSync(lock); fs.writeFileSync(path.join(lock, `${child.pid}-aabbcc`), JSON.stringify({ active_child: null }));
  const recovered = acquireBatchLock(lock); assert.ok(recovered); recovered();
});

test('native closure proof is nonce-bound and required before releasing or recovering descendant ownership', async () => {
  const lock = path.join(tmp, 'proof-lock'), proof = path.join(tmp, 'proof-closure.json');
  const binding = { proof, nonce: 'expected-native-nonce' };
  const owner = acquireBatchLock(lock); owner.child('launching', binding);
  assert.throws(() => owner.child(null), /unproven/); owner(); assert.equal(fs.existsSync(lock), true);
  fs.writeFileSync(proof, JSON.stringify({ nonce: 'wrong-nonce', state: 'closed', mechanism: 'windows_job' }));
  assert.throws(() => owner.child(null), /unproven/);
  fs.writeFileSync(proof, JSON.stringify({ nonce: binding.nonce, state: 'closed', mechanism: 'windows_job' }));
  owner.child(null); owner(); assert.equal(fs.existsSync(lock), false);
  const dead = spawn(process.execPath, ['-e', ''], { windowsHide: true });
  await new Promise(r => dead.on('close', r));
  fs.mkdirSync(lock);
  fs.writeFileSync(path.join(lock, `${dead.pid}-aabbcc`), JSON.stringify({ active_child: dead.pid, containment: binding }));
  const recovered = acquireBatchLock(lock); assert.ok(recovered); recovered();
});
test('dead owner recovery refuses a still-active child and never terminates it', async () => {
  const lock = path.join(tmp, 'orphan-lock');
  const dead = spawn(process.execPath, ['-e', ''], { windowsHide: true });
  await new Promise(r => dead.on('close', r));
  const live = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { windowsHide: true, stdio: 'ignore' });
  try {
    fs.mkdirSync(lock); fs.writeFileSync(path.join(lock, `${dead.pid}-aabbcc`), JSON.stringify({ active_child: live.pid }));
    assert.equal(acquireBatchLock(lock), null); assert.equal(alive(live.pid), true);
  } finally { live.kill('SIGKILL'); await new Promise(r => live.on('close', r)); }
});
test('timeout kills owned descendants and leaves an unrelated process alive', async () => {
  const marker = path.join(tmp, 'descendant.pid');
  const unrelated = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { windowsHide: true, stdio: 'ignore' });
  try {
    const r = await runBatch(plan('timeout', [{ ...check('owned tree timeout', 'tree', marker), timeout_s: 1.5 }]), tmp);
    assert.equal(r.checks[0].status, 'timeout'); assert.equal(r.status, 'failed');
    const pid = Number(fs.readFileSync(marker, 'utf8'));
    await until(() => {
      if (!alive(pid)) return true;
      // Linux may retain a dead orphan as a zombie until init reaps it.
      try { return fs.readFileSync(`/proc/${pid}/stat`, 'utf8').includes(') Z '); } catch { return false; }
    });
    assert.equal(alive(unrelated.pid), true);
  } finally { unrelated.kill('SIGKILL'); await new Promise(r => unrelated.on('close', r)); }
});
test('program and launch failures retain meaningful names, codes and following checks', async () => {
  const r = await runBatch(plan('failures', [check('parser regression', 'fail'), { name: 'missing launcher', argv: ['does-not-exist-retro625'], timeout_s: 1 }, check('later validation', 'argv')]), tmp);
  assert.equal(r.status, 'failed');
  assert.deepEqual(r.checks.map(c => [c.name, c.status, c.exit_code]), [['parser regression', 'failed', 17], ['missing launcher', 'launch_failed', null], ['later validation', 'passed', 0]]);
});
test('actual OS spawn failures are distinct from nonzero program exits', async () => {
  const f = path.join(tmp, 'invalid-native.exe'); fs.writeFileSync(f, 'this is not an executable', { mode: 0o600 });
  const r = await runBatch(plan('spawn-error', [{ name: 'OS launcher failure', argv: [f], timeout_s: 2 }]), tmp);
  assert.equal(r.checks[0].status, 'launch_failed'); assert.equal(r.checks[0].exit_code, null); assert.ok(r.checks[0].launch_error);
});
test('Windows shims are rejected explicitly without a shell fallback', { skip: process.platform !== 'win32' }, async () => {
  const f = path.join(tmp, 'unsupported.cmd'); fs.writeFileSync(f, '@echo off\r\necho should-not-execute');
  const r = await runBatch(plan('shim', [{ name: 'unsupported shim', argv: [f], timeout_s: 1 }]), tmp);
  assert.equal(r.checks[0].status, 'launch_failed'); assert.match(r.checks[0].launch_error, /unsupported Windows shim/);
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
test('CLI rejects unsafe ids, oversized plans and projection limits', () => {
  assert.equal(cli(runner, ['collect', '--batch', '../bad']).status, 2);
  assert.equal(cli(runner, ['collect', '--batch', 'repeat', '--limit', '500']).status, 2);
  const f = path.join(tmp, 'oversized.json'); fs.writeFileSync(f, ' '.repeat(1024 * 1024 + 1));
  assert.equal(cli(runner, ['run', '--plan', f]).status, 2);
});
test('bounded delegate projection keeps failure, unknown actual model and normalised usage', () => {
  const r = projectResult({ schema: 'delegate-task.result.v2', status: 'failed', summary: 'token=private-value\n' + 'a'.repeat(30000), requested_model: 'gpt-6.1-sol', actual_model: null, model_observed: false, tokens: { total: 42, fidelity: 'exact' }, status_provenance: { primary: 'exit_code', evidence: Array(200).fill('program failed') } });
  assert.equal(r.status, 'failed'); assert.equal(r.actual_model, null); assert.equal(r.tokens.total, 42);
  assert.equal(r.projection.truncated, true); assert.ok(!JSON.stringify(r).includes('private-value'));
});
test('public projection bounds oversized keys and redacts multiline and opaque known secrets', () => {
  const r = projectResult({ status: 'failed', summary: 'first-line\nsecond-line opaque-value', usage_raw: { ['k'.repeat(100000)]: 'value' } }, { secrets: ['first-line\nsecond-line', 'opaque-value'] });
  const s = JSON.stringify(r); assert.ok(s.length < 20000); assert.ok(!s.includes('opaque-value')); assert.ok(!s.includes('first-line')); assert.equal(r.projection.truncated, true);
  assert.ok(!redact('Authorization: Bearer opaquecredential').includes('opaquecredential'));
  assert.ok(!redact('Authorization: Basic abc').includes('abc'));
});
test('bounded collector refuses oversized historical metadata without rewriting it', () => {
  const id = 'codex-20261016000001-aabbcc', dir = path.join(tmp, id); fs.mkdirSync(dir);
  fs.writeFileSync(path.join(dir, 'meta.json'), JSON.stringify({ harness: 'codex' }));
  const f = path.join(dir, 'result.json'); const fd = fs.openSync(f, 'w'); fs.ftruncateSync(fd, 8 * 1024 * 1024 + 1); fs.closeSync(fd);
  const r = cli(driver, ['collect', id, '--summary']); assert.equal(r.status, 8); assert.match(r.stderr, /metadata over 8 MiB/); assert.equal(fs.statSync(f).size, 8 * 1024 * 1024 + 1);
});
test('legacy collect JSON readback remains intact while summary is bounded and read-only', () => {
  const id = 'codex-20261016000000-aabbcc', dir = path.join(tmp, id); fs.mkdirSync(dir);
  fs.writeFileSync(path.join(dir, 'meta.json'), JSON.stringify({ harness: 'codex', started_at: new Date().toISOString() }));
  const raw = JSON.stringify({ run_id: id, status: 'failed', summary: 'x'.repeat(20000), model: 'requested-only', tokens: { total: 7, fidelity: 'partial' }, exit_code: 2 });
  fs.writeFileSync(path.join(dir, 'result.json'), raw);
  const full = JSON.parse(cli(driver, ['collect', id, '--json']).stdout);
  assert.equal(full.schema, 'delegate-task.result.v1'); assert.equal(full.summary.length, 20000);
  const result = cli(driver, ['collect', id, '--summary', '--max-chars', '128']); assert.equal(result.status, 0, result.stderr);
  const small = JSON.parse(result.stdout); assert.equal(small.status_provenance.primary, 'legacy'); assert.equal(small.actual_model, null); assert.equal(small.tokens.total, 7); assert.equal(small.projection.truncated, true);
  assert.equal(fs.readFileSync(path.join(dir, 'result.json'), 'utf8'), raw);
});
test('heartbeat-only and startup-stalled diagnostics have deterministic times and null events', () => {
  const meta = { started_at: '2026-10-16T00:00:00Z', no_output_after_ms: 1000 };
  const dir = path.join(tmp, 'progress-unit'); fs.mkdirSync(dir);
  assert.equal(executionProgress(meta, dir, Date.parse(meta.started_at) + 1100).progress_state, 'supervisor_preparing');
  fs.writeFileSync(path.join(dir, 'progress.json'), JSON.stringify({ child_started_at: meta.started_at }));
  assert.equal(executionProgress(meta, dir, Date.parse(meta.started_at) + 10).progress_state, 'heartbeat_only');
  const r = executionProgress(meta, dir, Date.parse(meta.started_at) + 1100);
  assert.equal(r.progress_state, 'startup_stalled'); assert.equal(r.last_structured_event_at, null); assert.match(r.diagnostic, /no harness output/);
});
const stream = JSON.stringify({ type: 'thread.started', thread_id: 'fake-startup' }) + '\n' + JSON.stringify({ type: 'turn.completed', usage: { input_tokens: 5, output_tokens: 2 } }) + '\n';
function startHarness(extra, flags = []) {
  const result = cli(driver, ['start', '--harness', 'codex', '--cwd', tmp, '--task', 'fixture only', '--model', 'gpt-6.1-sol', '--timeout', '15', ...flags], { DELEGATE_BIN_CODEX: path.join(here, 'fixtures/fake-harness.mjs'), FAKE_STREAM: '', FAKE_SLEEP_MS: '5000', ...extra });
  assert.equal(result.status, 0, result.stderr); return JSON.parse(result.stdout).run_id;
}
test('silent fake harness hits only the explicit startup deadline and preserves model unknown', () => {
  const id = startHarness({}, ['--startup-timeout', '0.4', '--no-output-after', '0.1']);
  const c = cli(driver, ['collect', id, '--wait', '10', '--summary']); assert.equal(c.status, 0, c.stderr);
  const r = JSON.parse(c.stdout); assert.equal(r.status, 'abandoned'); assert.equal(r.status_provenance.primary, 'startup_timeout'); assert.equal(r.requested_model, 'gpt-6.1-sol'); assert.equal(r.actual_model, null); assert.equal(r.execution.last_structured_event_at, null); assert.equal(r.execution.stdout_bytes, 0);
  assert.equal(r.execution.progress_state, 'startup_stalled'); assert.match(r.execution.diagnostic, /deadline expired/);
});
test('stderr alone is not structured harness progress and cannot cancel startup deadline', () => {
  const id = startHarness({ FAKE_STDERR: 'initialising plugins\n' }, ['--startup-timeout', '0.4', '--no-output-after', '0.1']);
  const c = cli(driver, ['collect', id, '--wait', '10', '--json']); const r = JSON.parse(c.stdout);
  assert.equal(r.status_provenance.primary, 'startup_timeout'); assert.ok(r.execution.stderr_bytes > 0); assert.equal(r.execution.last_structured_event_at, null);
});
test('observed structured events cancel startup deadline without shortening valid tasks', async () => {
  const id = startHarness({ FAKE_STREAM: stream, FAKE_SLEEP_MS: '2000' }, ['--startup-timeout', '0.4']);
  await until(() => {
    try { return JSON.parse(fs.readFileSync(path.join(tmp, id, 'progress.json'), 'utf8')).last_structured_event_at; }
    catch { return null; }
  });
  const status = JSON.parse(cli(driver, ['status', id]).stdout);
  assert.equal(status.state, 'running'); assert.equal(status.execution.progress_state, 'harness_events');
  const c = cli(driver, ['collect', id, '--wait', '10', '--json']); const r = JSON.parse(c.stdout);
  assert.equal(r.status, 'successful'); assert.equal(r.execution.progress_state, 'harness_events'); assert.ok(r.execution.last_structured_event_at); assert.equal(r.actual_model, null);
});
test('startup deadline is opt-in; silent startup status does not declare completion', async () => {
  const id = startHarness({ FAKE_SLEEP_MS: '800' }, ['--no-output-after', '0.05']);
  await until(() => fs.existsSync(path.join(tmp, id, 'progress.json')));
  await delay(100);
  const s = JSON.parse(cli(driver, ['status', id]).stdout);
  assert.equal(s.state, 'running'); assert.equal(s.status, null); assert.equal(s.execution.progress_state, 'startup_stalled'); assert.equal(s.execution.startup_deadline_ms, null);
  const c = cli(driver, ['collect', id, '--wait', '10', '--json']); const r = JSON.parse(c.stdout);
  assert.equal(r.status_provenance.primary, 'telemetry_incomplete');
});
