import { test } from 'node:test';
import {
  assert, check, cli, collectBatch, driver, encodeReceipt, env, excerptFile, fixture, fs, path, plan, projectResult, publicJson, redact, runBatch, runner, spawnSync, storedAttempt, tmp,
} from './execution-helpers.mjs';

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

test('JSON masking preserves usage lexemes, scalar types and nested token counters', () => {
  const source = `{
    "usage": {"input_tokens": 9007199254740993, "cache_creation_input_tokens": 1e3,
      "cache_read_input_tokens": 0, "cached_input_tokens": 42, "output_tokens": -0,
      "output_tokens_details": {"reasoning_tokens": 3, "thinking_tokens": null}},
    "tokens": {"input_total": 1042, "output_total": 3, "fidelity": "exact"},
    "complete": true, "cost": 0.125, "unknown": null, "items": [false, 2, "visible"]
  }`;
  assert.equal(redact(source), source);
  assert.deepEqual(JSON.parse(redact(source)), JSON.parse(source));
});

test('JSON credential values are masked as valid JSON regardless of their type or nesting', () => {
  const source = {
    api_key: 'opaque-credential-\"quoted\"-\\path', password: 872641, secret: false,
    credentials: { label: 'opaque-nested-canary', count: 764219, nested: [true, null] },
    authorization: ['opaque-array-canary', { value: 641927 }],
    token: null, tokens: { label: 'opaque-token-container-canary', count: 219764 },
    input_tokens: 'opaque-counter-canary', unrelated: 'Bearer opaque-bearer-canary',
  };
  const hidden = redact(JSON.stringify(source, null, 2)), parsed = JSON.parse(hidden);
  for (const key of Object.keys(source).filter(key => key !== 'unrelated')) assert.equal(parsed[key], '[redacted]');
  assert.equal(parsed.unrelated, 'Bearer [redacted]');
  for (const canary of ['opaque-', '872641', '764219', '641927', '219764']) assert.ok(!hidden.includes(canary));
});

test('JSON decoded strings and explicitly known numeric secrets cannot damage serialization or escape masking', () => {
  const escaped = 'opaque-\"quoted\"-\\path\nnext';
  const source = JSON.stringify({ visible: escaped, number: 872641, usage: { input_tokens: 872641 }, normal: 17 });
  const hidden = redact(source, [escaped, '872641']);
  assert.deepEqual(JSON.parse(hidden), { visible: '[redacted]', number: '[redacted]', usage: { input_tokens: '[redacted]' }, normal: 17 });
  assert.ok(!hidden.includes('opaque')); assert.ok(!hidden.includes('872641'));
  assert.equal(redact(hidden, [escaped, '872641']), hidden);
});

test('explicit known secrets retain precedence across serialized JSON syntax and quoted literals', () => {
  for (const source of ['{"private":"opaque-canary"}', '"opaque-canary"', '["opaque-canary",false,872641]']) {
    const hidden = redact(source, [source]);
    assert.equal(JSON.parse(hidden), '[redacted]');
    assert.ok(!hidden.includes('opaque-canary')); assert.ok(!hidden.includes('872641'));
    assert.equal(redact(hidden, [source]), hidden);
  }
  const nested = '{"normal":"opaque-canary","usage":{"input_tokens":1e3}}';
  assert.deepEqual(JSON.parse(redact(nested, ['"opaque-canary"'])), { normal: '[redacted]', usage: { input_tokens: 1000 } });
  assert.ok(redact(nested, ['"opaque-canary"']).includes('"input_tokens":1e3'));
});

test('crossing and overlapping known serialized spans hide their complete containing JSON record', () => {
  const source = '{"left":"opaque-one","right":"opaque-two","usage":{"input_tokens":9007199254740993}}';
  for (const secrets of [
    ['opaque-one","right":"opaque-two'],
    ['opaque-one","right"', 'right":"opaque-two'],
    ['right":"opaque-two', 'opaque-one","right"'],
  ]) {
    assert.equal(JSON.parse(redact(source, secrets)), '[redacted]');
  }
  assert.equal(redact(source), source);
});

test('known serialized JSONL spans mask affected records while retaining unrelated telemetry records', () => {
  const first = '{"left":"opaque-one","right":"opaque-two"}';
  const second = '{"private":"opaque-three"}';
  const telemetry = '{"usage":{"input_tokens":9007199254740993,"cache_creation_input_tokens":1e3}}';
  for (const secrets of [[first + '\r\n' + second], ['opaque-one","right":"opaque-two', second]]) {
    const hidden = redact(first + '\r\n' + second + '\n' + telemetry + '\n', secrets);
    const lines = hidden.trimEnd().split(/\r?\n/);
    assert.equal(JSON.parse(lines[0]), '[redacted]'); assert.equal(JSON.parse(lines[1]), '[redacted]');
    assert.equal(lines[2], telemetry);
    assert.ok(!hidden.includes('opaque-')); assert.ok(hidden.includes('\r\n'));
    assert.equal(redact(hidden, secrets), hidden);
  }
});

test('mixed JSONL and plain diagnostics retain record boundaries and mask every credential form', () => {
  const first = JSON.stringify({ usage: { cache_creation_input_tokens: 120, output_tokens: 8 }, api_key: 'opaque-jsonl-canary' });
  const second = JSON.stringify({ credentials: [{ value: 'opaque-nested-jsonl-canary' }], complete: true });
  const hidden = redact(`${first}\r\npassword=872641\r\n${second}\n{"secret":"opaque-partial-canary`);
  const lines = hidden.split(/\r?\n/);
  assert.equal(JSON.parse(lines[0]).usage.cache_creation_input_tokens, 120);
  assert.equal(JSON.parse(lines[0]).api_key, '[redacted]');
  assert.equal(lines[1], 'password=[redacted]');
  assert.deepEqual(JSON.parse(lines[2]), { credentials: '[redacted]', complete: true });
  assert.ok(!hidden.includes('opaque-')); assert.ok(!hidden.includes('872641'));
  assert.equal((hidden.match(/\r\n/g) || []).length, 2);
});

test('JSONL excerpts keep masked complete records parseable and preserve numeric usage', () => {
  const file = path.join(tmp, 'json-redaction.log');
  const record = JSON.stringify({ usage: { input_tokens: 21, cache_creation_input_tokens: 34 }, secret: { value: 'opaque-excerpt-canary' } }) + '\n';
  fs.writeFileSync(file, record.repeat(20));
  const excerpt = excerptFile(file, { head: record.length * 2 + 10, tail: record.length * 2 + 10 });
  assert.equal(excerpt.truncated, true); assert.ok(excerpt.omitted_bytes > 0);
  for (const line of (excerpt.head + excerpt.tail).trim().split('\n')) {
    assert.deepEqual(JSON.parse(line), { usage: { input_tokens: 21, cache_creation_input_tokens: 34 }, secret: '[redacted]' });
  }
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
  assert.equal(launch.status, 2); assert.equal(launch.stdout, '');
  assert.ok(!launch.stderr.includes(secret)); assert.ok(!launch.stderr.includes(inherited));
  assert.equal(fs.existsSync(path.join(tmp, 'checks/secret-launch')), false);
  const invalidNative = path.join(tmp, secret + '.exe'); fs.writeFileSync(invalidNative, 'not an executable', { encoding: 'utf8', mode: 0o700 });
  fs.writeFileSync(f, JSON.stringify(plan('secret-native-launch', [{ name: secret + ' ' + inherited, argv: [invalidNative], timeout_s: 1 }], { env: { CUSTOM: secret } })), 'utf8');
  const native = cli(runner, ['run', '--plan', f], { CHECK_API_KEY: inherited });
  assert.equal(native.status, 1); assert.equal(JSON.parse(native.stdout).checks[0].status, 'launch_failed');
  assert.ok(!native.stdout.includes(secret)); assert.ok(!native.stdout.includes(inherited));
  assert.ok(!native.stderr.includes(secret)); assert.ok(!native.stderr.includes(inherited));
});
test('historical launch failures emit whole records and aggregate counts inside default and minimum byte budgets', () => {
  storedAttempt('many-checks', 1, Array.from({ length: 100 }, (_, i) => ({ name: `فشل ☕ ${i}`, status: 'launch_failed', exit_code: null,
    launch_error: 'executable not found; historical launcher resolution diagnostic. '.repeat(5) })));
  const receipt = collectBatch(tmp, 'many-checks').attempts[0];
  const r = publicJson({ status: 0, stdout: encodeReceipt(receipt, 16384) });
  assert.equal(r.total_checks, 100); assert.equal(r.check_status_counts.launch_failed, 100); assert.equal(r.status, 'failed');
  assert.ok(r.projection.truncated); assert.ok(r.projection.next_cursor || r.projection.narrow);
  for (const c of r.checks) { assert.equal(c.status, 'launch_failed'); assert.equal(c.exit_code, null); assert.ok(c.name.startsWith('فشل')); }
  const tiny = publicJson({ status: 0, stdout: encodeReceipt(receipt, 2048) }, 2048);
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
test('CLI rejects unsafe ids, oversized plans and projection limits', () => {
  assert.equal(cli(runner, ['collect', '--batch', '../bad']).status, 2);
  assert.equal(cli(runner, ['collect', '--batch', 'repeat', '--limit', '500']).status, 2);
  const f = path.join(tmp, 'oversized.json'); fs.writeFileSync(f, ' '.repeat(1024 * 1024 + 1));
  assert.equal(cli(runner, ['run', '--plan', f]).status, 2);
});
test('bounded delegate projection keeps failure, unknown actual model and normalised usage', () => {
  const r = projectResult({ schema: 'delegate-task.result.v2', status: 'failed', summary: 'token=private-value\n' + 'a'.repeat(30000), requested_model: 'gpt-6.1-sol', actual_model: null, model_observed: false, tokens: { total: 42, fidelity: 'exact' }, usage_raw: { input_tokens: 1000, output_tokens: 2000 }, status_provenance: { primary: 'exit_code', evidence: Array(200).fill('program failed') } });
  assert.equal(r.status, 'failed'); assert.equal(r.actual_model, null); assert.equal(r.tokens.total, 42);
  assert.equal(Object.hasOwn(r, 'usage_raw'), false);
  assert.equal(r.projection.truncated, true); assert.ok(!JSON.stringify(r).includes('private-value'));
});
test('public projection bounds oversized keys and redacts multiline and opaque known secrets', () => {
  const r = projectResult({ status: 'failed', summary: 'first-line\nsecond-line opaque-value', artifacts: { ['k'.repeat(100000)]: 'value' } }, { secrets: ['first-line\nsecond-line', 'opaque-value'] });
  const s = JSON.stringify(r); assert.ok(s.length < 20000); assert.ok(!s.includes('opaque-value')); assert.ok(!s.includes('first-line')); assert.equal(r.projection.truncated, true);
  assert.ok(!redact('Authorization: Bearer opaquecredential').includes('opaquecredential'));
  assert.ok(!redact('Authorization: Basic abc').includes('abc'));
});
test('stored raw usage is excluded from summary while normalised usage and full readback remain intact', () => {
  const id = 'codex-20261017000000-aabbcc', dir = path.join(tmp, id); fs.mkdirSync(dir);
  fs.writeFileSync(path.join(dir, 'meta.json'), JSON.stringify({ harness: 'codex' }), 'utf8');
  const tokens = { input: 10, output: 5, total: 15, fidelity: 'exact' };
  const usageRaw = { input_tokens: 1000, output_tokens: 2000, payload: 'raw-usage-sentinel' };
  const raw = JSON.stringify({ schema: 'delegate-task.result.v2', run_id: id, status: 'successful', tokens, usage_raw: usageRaw });
  fs.writeFileSync(path.join(dir, 'result.json'), raw, 'utf8');
  const full = cli(driver, ['collect', id, '--json']); assert.equal(full.status, 0, full.stderr);
  assert.deepEqual(JSON.parse(full.stdout).usage_raw, usageRaw);
  const summary = cli(driver, ['collect', id, '--summary']); assert.equal(summary.status, 0, summary.stderr);
  const projected = JSON.parse(summary.stdout);
  assert.deepEqual(projected.tokens, tokens); assert.equal(Object.hasOwn(projected, 'usage_raw'), false);
  assert.ok(!summary.stdout.includes('raw-usage-sentinel'));
  assert.equal(fs.readFileSync(path.join(dir, 'result.json'), 'utf8'), raw);
});

test('bounded collector refuses oversized historical metadata without rewriting it', () => {
  const id = 'codex-20261016000001-aabbcc', dir = path.join(tmp, id); fs.mkdirSync(dir);
  fs.writeFileSync(path.join(dir, 'meta.json'), JSON.stringify({ harness: 'codex' }));
  const f = path.join(dir, 'result.json'); const fd = fs.openSync(f, 'w'); fs.ftruncateSync(fd, 8 * 1024 * 1024 + 1); fs.closeSync(fd);
  const r = cli(driver, ['collect', id, '--summary']); assert.equal(r.status, 8); assert.match(r.stderr, /metadata over 8 MiB/); assert.equal(fs.statSync(f).size, 8 * 1024 * 1024 + 1);
});
test('summary recovery of a lost run with a 24 MB journal completes under a 32 MB heap and reports containment', () => {
  const id = 'codex-20261029000000-c0ffee', dir = path.join(tmp, id); fs.mkdirSync(dir);
  const t = new Date().toISOString(), dead = 2147483646; // a recent start: collect prunes runs older than 30 days
  fs.writeFileSync(path.join(dir, 'meta.json'), JSON.stringify({ run_id: id, harness: 'codex', harness_label: 'OpenAI Codex', tier: 'verified', task: 'lost', cwd: tmp, permission: 'bypass', started_at: t, supervisor_pid: dead }));
  fs.writeFileSync(path.join(dir, 'stdout.log'), '');
  const fd = fs.openSync(path.join(dir, 'journal.jsonl'), 'w');
  fs.writeSync(fd, [['supervisor_started', { pid: dead }], ['contained', { mechanism: 'windows_job' }], ['child_started', { pid: dead }]].map(([state, x]) => JSON.stringify({ t, state, ...x }) + '\n').join(''));
  const beats = `{"t":"${t}","state":"heartbeat","pad":"${'x'.repeat(200)}"}\n`.repeat(4096);
  for (let n = 0; n < 24 * 1024 * 1024; n += beats.length) fs.writeSync(fd, beats);
  fs.closeSync(fd);
  const r = spawnSync(process.execPath, ['--max-old-space-size=32', driver, 'collect', id, '--summary'], { env, encoding: 'utf8', windowsHide: true, timeout: 60000 });
  assert.equal(r.status, 0, r.stderr.slice(-2000));
  assert.equal(JSON.parse(r.stdout).status, 'abandoned');
  // The summary projection omits process_containment; the persisted terminal result carries it.
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(dir, 'result.json'), 'utf8')).process_containment, { mechanism: 'windows_job', closure: 'closed' });
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
