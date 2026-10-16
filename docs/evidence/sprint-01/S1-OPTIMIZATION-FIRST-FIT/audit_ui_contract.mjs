// Read-only compatibility audit of the published UI parser against real backend artifacts.
// Run from repo root. Sources go only to a temporary directory, never frontend.
import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
const directory = mkdtempSync(join(tmpdir(), 'newglass-contract-audit-'));
try {
  writeFileSync(join(directory, 'package.json'), '{"type":"module"}');
  const reference = 'origin/feature/S1-optimization-ui';
  const head = execFileSync('git', ['rev-parse', reference], { encoding: 'utf8' }).trim();
  for (const file of ['runContract.js', 'visualizationGeometry.js']) {
    writeFileSync(join(directory, file), execFileSync('git', ['show', `${reference}:frontend/src/features/optimization/${file}`]));
  }
  const { parseRun, readNdjson } = await import(pathToFileURL(join(directory, 'runContract.js')));
  const base = 'docs/evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/';
  const bytes = readFileSync(base + 'phase5-example-complete.ndjson');
  async function* chunks() { for (let i = 0; i < bytes.length; i += 7) yield bytes.subarray(i, i + 7); }
  const events = [];
  for await (const event of readNdjson(chunks())) events.push(event);
  const run = parseRun(JSON.parse(readFileSync(base + 'phase5-example-complete.json', 'utf8')));
  if (events.length !== 13 || !run.completo || run.placed_units !== 4
    || events.some((e, i) => e.sequence !== i + 1)) throw new Error('Unexpected captured run');
  console.log(JSON.stringify({ ui_head: head, events_accepted: events.length, chunk_bytes: 7,
    canonical_status: run.estado, placements: run.placed_units,
    physical_units: new Set(run.materials_used.map(s => `${s.material_source}:${s.material_id}:${s.stock_unit_index}`)).size,
    decimal_strings_preserved: run.placements.every(p => typeof p.x_mm === 'string'),
    frontend_modified: false }, null, 2));
} finally { rmSync(directory, { recursive: true, force: true }); }
