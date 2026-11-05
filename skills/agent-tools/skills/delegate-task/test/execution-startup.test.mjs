import { test } from 'node:test';
import {
  assert, cli, delay, driver, env, executionProgress, fixture, fs, here, path, spawnSync, startHarness, stream, tmp, until,
} from './execution-helpers.mjs';

test('heartbeat-only and startup-stalled diagnostics have deterministic times and null events', () => {
  const meta = { started_at: '2026-10-16T00:00:00Z', no_output_after_ms: 1000 };
  const dir = path.join(tmp, 'progress-unit'); fs.mkdirSync(dir);
  assert.equal(executionProgress(meta, dir, Date.parse(meta.started_at) + 1100).progress_state, 'supervisor_preparing');
  fs.writeFileSync(path.join(dir, 'progress.json'), JSON.stringify({ child_started_at: meta.started_at }));
  assert.equal(executionProgress(meta, dir, Date.parse(meta.started_at) + 10).progress_state, 'heartbeat_only');
  const r = executionProgress(meta, dir, Date.parse(meta.started_at) + 1100);
  assert.equal(r.progress_state, 'startup_stalled'); assert.equal(r.last_structured_event_at, null); assert.match(r.diagnostic, /no harness output/);
});
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
test('a cancel marker present before launch starts nothing and proves closure', { skip: process.platform !== 'win32' }, async () => {
  const dir = fs.mkdtempSync(path.join(tmp, 'precancel-'));
  const marker = path.join(dir, 'ran'), cancel = path.join(dir, 'cancel'), proof = path.join(dir, 'proof.json');
  const [stdout, stderr] = ['stdout', 'stderr'].map(n => path.join(dir, n)); for (const f of [stdout, stderr]) fs.writeFileSync(f, '');
  fs.writeFileSync(cancel, '');
  const request = { nonce: 'n', owner_pid: process.pid, file: process.execPath, args: [fixture, 'once', marker, '100'], cwd: dir,
    env: { ...process.env }, timeout_s: 10, stdout, stderr, proof, cancel };
  const helper = spawnSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-File', path.join(here, '../containment-windows.ps1')],
    { input: JSON.stringify(request), encoding: 'utf8', windowsHide: true, timeout: 30000 });
  assert.equal(helper.status, 0, helper.stderr);
  const result = JSON.parse(fs.readFileSync(proof, 'utf8'));
  assert.equal(result.state, 'closed'); assert.equal(result.started, false); assert.equal(result.root_pid, null); assert.equal(result.launch_error, null);
  assert.equal(fs.existsSync(marker), false);
});
test('Linux containment enumerates children by /proc scan when the kernel children file is missing', { skip: process.platform !== 'linux' }, () => {
  const script = `
import builtins, importlib.util, subprocess, sys
spec = importlib.util.spec_from_file_location('containment_linux', sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
real = builtins.open
def no_children(path, *a, **k):
    if str(path).endswith('/children'): raise FileNotFoundError(path)
    return real(path, *a, **k)
builtins.open = no_children
child = subprocess.Popen(['sleep', '5'])
try:
    assert child.pid in m.list_children(), m.list_children()
    assert 0 not in m.list_children()
finally:
    child.kill(); child.wait()
`;
  const r = spawnSync('python3', ['-c', script, path.join(here, '../containment-linux.py')], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
});
