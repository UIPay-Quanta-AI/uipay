// Kills whatever process is already listening on the given port before the
// dev server starts. On Windows, Ctrl+C in a terminal running `npm run
// start:dev` often doesn't kill the underlying node.exe - it gets orphaned
// holding the port, so the next start silently fails or fights the old
// process for the port instead of replacing it.
import { execSync } from 'node:child_process';

const port = process.argv[2];
if (!port) {
  console.error('Usage: node free-port.mjs <port>');
  process.exit(1);
}

function killWindows(port) {
  let output;
  try {
    output = execSync(`netstat -ano -p tcp | findstr :${port}`, {
      encoding: 'utf8',
    });
  } catch {
    return;
  }

  const pids = new Set();
  for (const line of output.split('\n')) {
    const match = line.trim().match(/LISTENING\s+(\d+)\s*$/);
    if (match) pids.add(match[1]);
  }

  for (const pid of pids) {
    try {
      execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' });
      console.log(`freed port ${port} (killed pid ${pid})`);
    } catch {
      // already gone
    }
  }
}

function killPosix(port) {
  let pids;
  try {
    pids = execSync(`lsof -ti tcp:${port}`, { encoding: 'utf8' })
      .split('\n')
      .filter(Boolean);
  } catch {
    return;
  }

  for (const pid of pids) {
    try {
      execSync(`kill -9 ${pid}`, { stdio: 'ignore' });
      console.log(`freed port ${port} (killed pid ${pid})`);
    } catch {
      // already gone
    }
  }
}

if (process.platform === 'win32') {
  killWindows(port);
} else {
  killPosix(port);
}
