import fs from 'node:fs';
import { spawn } from 'node:child_process';
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
}
