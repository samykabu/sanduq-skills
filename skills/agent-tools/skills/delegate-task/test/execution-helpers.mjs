// Shared setup for the execution test files. Each file runs in its own process (node --test),
// so each gets its own runs directory and its own cleanup.
import { after } from 'node:test';
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

export const here = path.dirname(fileURLToPath(import.meta.url));
export const runner = path.join(here, '../check-runner.mjs'), driver = path.join(here, '../delegate.mjs');
export const fixture = path.join(here, 'fixtures/check-fixture.mjs');
export const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'delegate-execution-'));
export const env = { ...process.env, DELEGATE_RUNS_DIR: tmp };
export const plan = (id, checks, extra = {}) => ({ batch_id: id, cwd: tmp, checks, ...extra });
export const check = (name, mode, ...args) => ({ name, argv: ['{{node}}', fixture, mode, ...args], timeout_s: 10 });
export const cli = (file, args, over = {}) => spawnSync(process.execPath, [file, ...args], { env: { ...env, ...over }, encoding: 'utf8', windowsHide: true, shell: false, timeout: 30000, maxBuffer: 4 * 1024 * 1024 });
export const delay = ms => new Promise(r => setTimeout(r, ms));
export function processLive(pid) {
  if (!alive(pid)) return false;
  try { return !fs.readFileSync(`/proc/${pid}/stat`, 'utf8').includes(') Z '); } catch { return true; }
}
export async function until(fn) {
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) { const v = fn(); if (v) return v; await delay(20); }
  throw new Error('fixture condition not reached within 10s');
}
export function asyncCli(args) {
  const p = spawn(process.execPath, [runner, ...args], { env, windowsHide: true, shell: false, stdio: ['ignore', 'pipe', 'pipe'] });
  let stdout = '', stderr = '';
  p.stdout.on('data', c => stdout += c); p.stderr.on('data', c => stderr += c);
  return { child: p, done: new Promise((resolve, reject) => { p.on('error', reject); p.on('close', code => resolve({ code, stdout, stderr })); }) };
}
after(() => fs.rmSync(tmp, { recursive: true, force: true }));


export { assert, fs, os, path, spawn, spawnSync, fileURLToPath, runBatch, collectBatch, validatePlan, acquireBatchLock, alive, containmentClosed, excerptFile, projectResult, redact, executionProgress, encodeReceipt };

export function publicJson(result, budget = 16384, expectedExit = 0) {
  assert.equal(result.status, expectedExit, result.stderr);
  const bytes = Buffer.byteLength(result.stdout, 'utf8');
  assert.ok(bytes <= budget, `emitted ${bytes} bytes, budget ${budget}`);
  const parsed = JSON.parse(result.stdout);
  assert.equal(parsed.projection.emitted_bytes, bytes);
  return parsed;
}
export function storedAttempt(batchId, number, checks, extra = {}) {
  const id = `attempt-${1700000000000 + number}-${number.toString(16).padStart(12, '0')}`;
  const dir = path.join(tmp, 'checks', batchId, id); fs.mkdirSync(dir, { recursive: true });
  const p = plan(batchId, checks.map((c, i) => check(c.name || `check ${i}`, 'fail')));
  fs.writeFileSync(path.join(dir, 'plan.json'), JSON.stringify(p), 'utf8');
  fs.writeFileSync(path.join(dir, 'result.json'), JSON.stringify({ schema: 'delegate-task.check-batch.v1', batch_id: batchId, attempt_id: id, status: 'failed', status_provenance: null, checks, ...extra }), 'utf8');
  return { id, dir };
}

export const stream = JSON.stringify({ type: 'thread.started', thread_id: 'fake-startup' }) + '\n' + JSON.stringify({ type: 'turn.completed', usage: { input_tokens: 5, output_tokens: 2 } }) + '\n';
export function startHarness(extra, flags = []) {
  const result = cli(driver, ['start', '--harness', 'codex', '--cwd', tmp, '--task', 'fixture only', '--model', 'gpt-6.1-sol', '--timeout', '15', ...flags], { DELEGATE_BIN_CODEX: path.join(here, 'fixtures/fake-harness.mjs'), FAKE_STREAM: '', FAKE_SLEEP_MS: '5000', ...extra });
  assert.equal(result.status, 0, result.stderr); return JSON.parse(result.stdout).run_id;
}
