// Read only the published UI parser. No checkout/merge or frontend modification.
import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
const temp = mkdtempSync(join(tmpdir(), 'newglass-confirm-contract-'));
try {
  writeFileSync(join(temp, 'package.json'), '{"type":"module"}');
  const ref = 'origin/feature/S1-optimization-ui';
  const head = execFileSync('git', ['rev-parse', ref], { encoding:'utf8' }).trim();
  for (const file of ['runContract.js', 'visualizationGeometry.js']) {
    writeFileSync(join(temp, file), execFileSync('git', ['show', `${ref}:frontend/src/features/optimization/${file}`]));
  }
  const { parseRun, parseConfirmation, readNdjson } = await import(pathToFileURL(join(temp, 'runContract.js')));
  const base = 'docs/evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/confirmation-example-';
  const before = parseRun(JSON.parse(readFileSync(base + 'before.json', 'utf8')));
  const after = parseRun(JSON.parse(readFileSync(base + 'after.json', 'utf8')));
  const confirmation = parseConfirmation(JSON.parse(readFileSync(base + 'response.json', 'utf8')), after.id_optimizacion);
  const bytes = readFileSync(base + 'stream.ndjson');
  async function* chunks() { for (let i=0; i<bytes.length; i+=7) yield bytes.subarray(i,i+7); }
  const events = [];
  for await (const event of readNdjson(chunks())) events.push(event);
  if (!before.confirmable || before.confirmed || after.confirmable || !after.confirmed
    || events.some((e,i)=>e.sequence!==i+1) || after.placed_units!==6) throw new Error('Unexpected captured result');
  console.log(JSON.stringify({ ui_head:head, ndjson_events:events.length, chunk_bytes:7,
    orders_confirmed:confirmation.orders.length, physical_units_consumed:confirmation.materials_consumed.length,
    valid_remnants_created:confirmation.remnants_created.length, canonical_confirmed:after.confirmed,
    canonical_confirmable:after.confirmable, frontend_modified:false }, null, 2));
} finally { rmSync(temp, { recursive:true, force:true }); }
