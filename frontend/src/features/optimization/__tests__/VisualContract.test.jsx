import { expect, test, vi } from 'vitest';
import { createBackendRunAdapter } from '../runApi';
import { parseVisualEvent, parseVisualMask, readVisualNdjson } from '../visualContract';
import shared from '../contractV1Fixture.json';

const policy = { profile: 'visual-v2', representative_orientations: true, max_extra_samples: 128,
  max_extra_samples_per_second: 10, retention_max_seconds: 300, retention_may_end_earlier: true };
const envelope = (event, data, sequence = 1) => ({ schema_version: 2, id_optimizacion: 101,
  sequence, occurred_at: '2026-10-27T22:00:00Z', event, data });
export const descriptor = { id_optimizacion: 101, available: true, mask_ref: 'a'.repeat(32), kind: 'PIECE',
  resolution_mm: '1', rotation_deg: '90', columns: 2, row_count: 3, occupied_cells: 6,
  piece: { id_pedido: 10, id_pieza: 27 }, source: null, reason: null };
export const windowData = { ...descriptor, schema_version: 2,
  geometria: { type: 'RECTANGULO', width_mm: 2, height_mm: 3 },
  geometria_original: { type: 'RECTANGULO', width_mm: 3, height_mm: 2 },
  window: { row_start: 1, row_count: 1, column_start: 0, column_count: 2 },
  spans_by_row: [{ row: 1, runs: [[0, 2]] }] };

test('V2 parser accepts real descriptor context and rejects another run or piece', () => {
  const event = envelope('piece_ready', { id_pedido: 10, id_pieza: 27, id_tipo_vidrio: 7, espesor_mm: '6', cantidad: 2, mask: descriptor });
  expect(parseVisualEvent(event)).toEqual(event);
  expect(() => parseVisualEvent({ ...event, schema_version: 1 })).toThrow();
  expect(() => parseVisualEvent({ ...event, id_optimizacion: 102 })).toThrow();
  expect(() => parseVisualEvent({ ...event, data: { ...event.data, id_pieza: 28 } })).toThrow();
});

test('mask windows preserve orientation and reject stale resolution or invalid ranges', () => {
  expect(parseVisualMask(windowData, 101, descriptor)).toEqual(windowData);
  for (const change of [{ resolution_mm: '2' }, { rotation_deg: '0' }, { mask_ref: 'b'.repeat(32) },
    { spans_by_row: [{ row: 0, runs: [[0, 2]] }] }, { spans_by_row: [{ row: 1, runs: [[0, 3]] }] }]) {
    expect(() => parseVisualMask({ ...windowData, ...change }, 101, descriptor)).toThrow();
  }
});

test('fragmented V2 reader checks sequence, versions, terminal and byte budget', async () => {
  const start = { ...shared.success_events[0], schema_version: 2, sequence: 1,
    data: { ...shared.success_events[0].data, visual: policy } };
  const terminal = { ...shared.success_events.at(-1), schema_version: 2, sequence: 2,
    data: { ...shared.success_events.at(-1).data, processed_units: shared.success_events.at(-1).data.total_units } };
  async function collect(events, width = 3) {
    const bytes = new TextEncoder().encode(events.map(event => JSON.stringify(event)).join('\n') + '\n');
    async function* chunks() { for (let i = 0; i < bytes.length; i += width) yield bytes.slice(i, i + width); }
    const result = [];
    for await (const event of readVisualNdjson(chunks())) result.push(event);
    return result;
  }
  expect(await collect([start, terminal])).toEqual([start, terminal]);
  for (const events of [[start], [start, { ...terminal, sequence: 3 }], [start, { ...terminal, id_optimizacion: 999 }],
    [start, { ...terminal, schema_version: 1 }], [start, terminal, terminal],
    [start, { ...terminal, padding: 'x'.repeat(65536) }]]) await expect(collect(events, 100000)).rejects.toThrow();
});

test('opt-in adapter requests V2 while canonical reads and reference URLs stay local', async () => {
  const start = { ...shared.success_events[0], schema_version: 2, sequence: 1,
    data: { ...shared.success_events[0].data, visual: policy } };
  const end = { ...shared.success_events.at(-1), schema_version: 2, sequence: 2,
    data: { ...shared.success_events.at(-1).data, processed_units: shared.success_events.at(-1).data.total_units } };
  const fetchImpl = vi.fn().mockResolvedValueOnce(new Response([start, end].map(value => JSON.stringify(value)).join('\n') + '\n',
    { status: 201, headers: { 'Content-Type': 'application/x-ndjson', Location: '/api/optimization/runs/101' } }))
    .mockResolvedValueOnce(new Response(JSON.stringify(windowData), { headers: { 'Content-Type': 'application/json' } }));
  const adapter = createBackendRunAdapter({ token: 'test-token', fetchImpl, streamProfile: 'visual-v2' });
  const events = [];
  await new Promise((resolve, reject) => adapter.createEventSource({ order_ids: [10] }).subscribe(value => {
    events.push(value); if (value.event === 'optimization_completed') resolve();
  }, reject));
  expect(events).toEqual([start, end]);
  expect(fetchImpl.mock.calls[0][0]).toMatch(/\/runs\?stream_profile=visual-v2$/);
  expect(await adapter.loadVisualMask(101, descriptor, { row_start: 1, row_count: 1 })).toEqual(windowData);
  expect(fetchImpl.mock.calls[1][0]).toMatch(/\/runs\/101\/visual\/masks\/a{32}\?/);
  expect(fetchImpl.mock.calls[1][1].headers.Authorization).toBe('Bearer test-token');
  await expect(adapter.loadVisualMask(102, descriptor)).rejects.toThrow();
  expect(fetchImpl).toHaveBeenCalledTimes(2);
});
