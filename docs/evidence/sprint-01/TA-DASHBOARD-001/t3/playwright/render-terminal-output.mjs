// Render exact excerpts from captured command logs as clearly labeled terminal-output PNGs.
// These are rendered views, not native terminal screenshots.
import { chromium } from '../../../../../../frontend/node_modules/playwright/index.mjs';
import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const t3 = resolve(here, '..');
const logs = resolve(t3, 'logs');
const terminal = resolve(t3, 'terminal');

const captures = [
  ['01-git-precheck.png', 'git-precheck-summary.txt', { head: 10 }],
  ['02-backend-health.png', 'backend-agent-start-block-summary.txt', { head: 10 }],
  ['03-dashboard-tests.png', 'dashboard-targeted-summary.txt', { head: 8 }],
  ['04-unit-tests.png', 'unit-final-summary.txt', { head: 10 }],
  ['05-component-tests.png', 'component-final-summary.txt', { head: 10 }],
  ['06-lint.png', 'lint-final-summary.txt', { head: 8 }],
  ['07-build.png', 'build-final-summary.txt', { head: 8 }],
  ['08-e2e-real.png', 'dashboard-e2e-summary.txt', { head: 20 }],
  ['09-diff-check.png', 'diff-check-final.txt', { head: 14 }],
  ['10-git-status-before-commit.png', 'git-status-before-commit.txt', { head: 24 }],
  ['11-backend-health-recheck.png', 'backend-health-recheck-summary.txt', { head: 10 }],
  ['12-dashboard-e2e-skipped.png', 'e2e-initial-skips-summary.txt', { head: 10 }],
];

async function readLog(file) {
  const bytes = await readFile(file);
  if (bytes[0] === 0xff && bytes[1] === 0xfe) return bytes.subarray(2).toString('utf16le');
  if (bytes[0] === 0xfe && bytes[1] === 0xff) {
    const swapped = Buffer.from(bytes.subarray(2));
    for (let i = 0; i + 1 < swapped.length; i += 2) [swapped[i], swapped[i + 1]] = [swapped[i + 1], swapped[i]];
    return swapped.toString('utf16le');
  }
  return bytes.toString('utf8').replace(/^\uFEFF/, '');
}

const browser = await chromium.launch({ headless: true });
try {
  for (const [imageName, logName, excerpt] of captures) {
    const full = (await readLog(resolve(logs, logName))).replaceAll('\r\n', '\n').trimEnd();
    const allLines = full.split('\n');
    const lines = excerpt.head && excerpt.tail
      ? [...allLines.slice(0, excerpt.head), '…', ...allLines.slice(-excerpt.tail)]
      : excerpt.head ? allLines.slice(0, excerpt.head) : allLines.slice(-excerpt.tail);
    const escaped = lines.map(line => line.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')).join('\n');
    const page = await browser.newPage({ viewport: { width: 1720, height: 900 }, deviceScaleFactor: 1 });
    await page.setContent(`<!doctype html><meta charset="utf-8"><style>
      *{box-sizing:border-box}body{margin:0;padding:24px;background:#10151d;color:#dce7f5;font:16px/1.45 Consolas,'Cascadia Mono',monospace}
      header{margin:0 0 18px;padding:12px 16px;border:1px solid #235d49;border-radius:8px;color:#8cf0b5;background:#13251f;font-weight:700}
      pre{margin:0;padding:20px;background:#070a0f;border:1px solid #283240;border-radius:10px;white-space:pre-wrap;overflow-wrap:anywhere;min-height:140px}
    </style><header>RENDERED TERMINAL OUTPUT · source log: ${logName.replaceAll('&', '&amp;').replaceAll('<', '&lt;')} · excerpt, not a native screenshot</header><pre>${escaped}</pre>`);
    await page.screenshot({ path: resolve(terminal, imageName), fullPage: true });
    await page.close();
    process.stdout.write(`${imageName}: rendered from ${logName} (${lines.length} lines)\n`);
  }
} finally {
  await browser.close();
}
