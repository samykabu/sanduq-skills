import fs from 'node:fs';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const [mode, ...args] = process.argv.slice(2);
if (mode === 'argv') process.stdout.write(JSON.stringify(args));
else if (mode === 'fail') { console.error('fixture program failure'); process.exitCode = 17; }
else if (mode === 'flood') {
  console.log('secret=' + process.env.CHECK_SECRET);
  process.stdout.write(JSON.stringify({ huge: 'ع'.repeat(1000000) }) + '\n');
  console.error('stderr complete');
  console.log('finished');
} else if (mode === 'once') {
  fs.appendFileSync(args[0], 'executed\n', 'utf8');
  setTimeout(() => {}, Number(args[1] || 500));
} else if (mode === 'tree') {
  const child = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { windowsHide: true, stdio: 'inherit' });
  fs.writeFileSync(args[0], String(child.pid), 'utf8');
  setInterval(() => {}, 1000);
} else if (mode === 'background' || mode === 'kill-helper') {
  const [marker, release, exit = '0'] = args;
  const child = spawn(process.execPath, [fileURLToPath(import.meta.url), 'background-worker', release], { windowsHide: true, detached: true, stdio: 'ignore' });
  child.on('spawn', () => {
    fs.writeFileSync(marker, JSON.stringify({ pid: child.pid, root_pid: process.pid, helper_pid: process.ppid }), 'utf8');
    child.unref();
    if (mode === 'kill-helper') process.kill(process.ppid, 'SIGKILL');
    process.exitCode = Number(exit);
  });
} else if (mode === 'background-worker') {
  const began = Date.now();
  const timer = setInterval(() => {
    if (fs.existsSync(args[0]) || Date.now() - began > 15000) clearInterval(timer);
  }, 20);
} else if (mode === 'assert-stopped') {
  const { pid } = JSON.parse(fs.readFileSync(args[0], 'utf8'));
  let alive = true;
  try { process.kill(pid, 0); } catch { alive = false; }
  if (alive) process.exitCode = 23;
  else fs.writeFileSync(args[1], 'next check started after closure', 'utf8');
}
