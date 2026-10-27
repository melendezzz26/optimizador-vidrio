import { test } from 'node:test';
import assert from 'node:assert/strict';
import shared from '../../src/features/optimization/contractV1Fixture.json' with { type: 'json' };
import { buildRunRequest, decimalKey, parseEvent, parseRun, parseConfirmation, readNdjson, renderNumber, stockKey } from '../../src/features/optimization/runContract.js';
import { scenarioFixture, eventsForRun } from '../../src/features/optimization/runFixtures.js';
import { createRunTransport } from '../../src/features/optimization/runTransport.js';

test('shared core T1 fixture validates without aliases or data loss', () => {
  assert.deepEqual(buildRunRequest([10]), shared.request);
  assert.deepEqual(parseRun(shared.result), shared.result);
  shared.success_events.forEach(e => assert.deepEqual(parseEvent(e), e));
  assert.deepEqual(parseEvent(shared.failed_event), shared.failed_event);
  assert.deepEqual(parseConfirmation(shared.confirmation, 101), shared.confirmation);
});
test('request has only order_ids; empty, duplicate, string and invalid IDs rejected', () => {
  assert.deepEqual(Object.keys(buildRunRequest([11, 10])), ['order_ids']);
  for (const ids of [[], [1, 1], ['1'], [0], [true]]) assert.throws(() => buildRunRequest(ids));
});
test('decimal strings are preserved; equivalence keys avoid Number precision loss', () => {
  const run = structuredClone(shared.result);
  run.placements[0].x_mm = '120.50000000000000000001';
  assert.equal(parseRun(run).placements[0].x_mm, '120.50000000000000000001');
  assert.equal(decimalKey('6.00'), '6'); assert.equal(decimalKey('6e0'), '6');
  assert.equal(decimalKey('0.00000000000000000001'), '0.00000000000000000001');
  assert.equal(renderNumber('120.50'), 120.5);
  assert.throws(() => renderNumber('1e-999'));
  run.placements[0].x_mm = 120.5; assert.throws(() => parseRun(run));
});
test('all authored scenarios are T1-shaped: quantity, orders, materials, physical units and nullable results', () => {
  for (const name of ['complete', 'incomplete', 'failed', 'running', 'not-confirmable', 'confirmed']) {
    const run = scenarioFixture(name); parseRun(run);
    eventsForRun(run).forEach(parseEvent);
    assert.equal(run.order_ids.length, 2); assert.equal(run.groups.length, 2);
    assert.deepEqual(run.groups[0].units.map(u => u.unit_index), [1, 2, 3]);
    assert.equal(run.metrics_available, false); assert.equal(run.metrics, null);
  }
  const stocks = scenarioFixture().materials_used;
  assert.deepEqual(stocks.map(stockKey), ['PLANCHA:5:1', 'PLANCHA:5:2', 'RETAZO:8:1']);
});
test('malformed identity, source, physical unit, oriented contour and counters are rejected', () => {
  for (const patch of [{ unit_index: 0 }, { stock_unit_index: 0 }, { material_source: 'plancha' },
    { x_mm: 'NaN' }, { rotation_deg: '360' }, { material_id: 999 }]) {
    const run = structuredClone(shared.result); Object.assign(run.placements[0], patch);
    assert.throws(() => parseRun(run));
  }
  const run = structuredClone(shared.result); run.placements[0].geometria = { type: 'POLIGONO_CONVEXO', vertices_mm: [[1, 1], [2, 1], [1, 2]] };
  assert.throws(() => parseRun(run));
});
test('incomplete or confirmed result cannot claim confirmation eligibility', () => {
  for (const name of ['incomplete', 'confirmed']) {
    const run = scenarioFixture(name); run.confirmable = true; assert.throws(() => parseRun(run));
  }
});
test('NDJSON handles UTF-8 split characters, split lines and multiple lines per chunk', async () => {
  const encoded = new TextEncoder().encode(shared.success_events.map(e => JSON.stringify(e)).join('\n') + '\n');
  async function* bytes() { for (let i = 0; i < encoded.length; i += 7) yield encoded.slice(i, i + 7); }
  const output = []; for await (const e of readNdjson(bytes())) output.push(e);
  assert.deepEqual(output, shared.success_events);
});
test('NDJSON truncated line, absent terminal and invalid JSON do not fabricate completion', async () => {
  for (const text of [JSON.stringify(shared.success_events[0]), JSON.stringify(shared.success_events[0]) + '\n', '{bad}\n']) {
    async function* bytes() { yield new TextEncoder().encode(text); }
    await assert.rejects(async () => { for await (const e of readNdjson(bytes())) assert.notEqual(e.event, 'optimization_completed'); });
  }
});
test('injected transport sends only selection and confirms by ID without functional body', async () => {
  let received, confirmed;
  const transport = createRunTransport({ load: async () => shared.result, confirm: async id => { confirmed = id; return shared.confirmation; },
    open: async request => { received = request; return (async function* () { yield new TextEncoder().encode(shared.success_events.map(e => JSON.stringify(e)).join('\n') + '\n'); })(); } });
  await new Promise((resolve, reject) => transport.createEventSource({ order_ids: [10], ignored: true }).subscribe(e => {
    if (e.event === 'optimization_completed') resolve();
  }, reject));
  assert.deepEqual(received, { order_ids: [10] });
  await transport.confirm(101); assert.equal(confirmed, 101);
  assert.deepEqual(await transport.loadResult(101), shared.result);
});
test('unconfigured transport performs no fabricated network operation', async () => {
  const transport = createRunTransport();
  await assert.rejects(transport.loadResult(101), /no está disponible/);
  await assert.rejects(transport.confirm(101), /no está disponible/);
});

test('TA-037: optimization_failed accepts TIME_BUDGET_EXCEEDED and still rejects unknown codes', () => {
  const failed = code => ({ schema_version: 1, sequence: 9, id_optimizacion: 7, occurred_at: '2026-10-26T20:00:00Z',
    event: 'optimization_failed', data: { estado: 'FALLIDA', code, message: 'El cálculo superó el tiempo máximo.',
      result_url: '/api/optimization/runs/7' } });
  assert.equal(parseEvent(failed('TIME_BUDGET_EXCEEDED')).data.code, 'TIME_BUDGET_EXCEEDED');
  assert.throws(() => parseEvent(failed('SOMETHING_ELSE')));
});
