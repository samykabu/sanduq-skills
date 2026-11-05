import { test } from 'node:test';
import {
  acquireBatchLock, alive, assert, asyncCli, check, cli, collectBatch, containmentClosed, fs, path, plan, processLive, runBatch, runner, spawn, tmp, until,
} from './execution-helpers.mjs';

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
