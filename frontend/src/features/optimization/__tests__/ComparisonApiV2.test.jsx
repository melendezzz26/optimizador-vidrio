import { expect, test, vi } from 'vitest';
import fixture from '../../../../../docs/contracts/optimization/comparison-v2.json';
import { createComparisonV2Api } from '../comparisonApiV2';

const jsonResponse = value => ({ ok: true, headers: { get: () => 'application/json' }, body: null,
  json: async () => structuredClone(value) });
const descriptor = (executionId = 4301, method = 'FF') => ({ profile: 'comparison-v2', schema_version: 2,
  comparison_id: 43, id_optimizacion: 43, execution_id: executionId, method, available: true,
  mask_ref: 'a'.repeat(32), kind: 'PIECE', resolution_mm: '1', rotation_deg: '0', columns: 4,
  row_count: 2, occupied_cells: 4, piece: { id_pedido: 1, id_pieza: 1 }, source: null, reason: null });

test('history is a bounded GET with validated owner-scoped references', async () => {
  const value = { items: [{ comparison_id: 43, profile: 'comparison-v2', started_at: '2026-11-06T12:00:00Z',
    status: 'COMPLETADA', order_ids: [1], confirmed: false, released: false }], next_before_id: 43 };
  const fetchImpl = vi.fn().mockResolvedValueOnce(jsonResponse(value))
    .mockResolvedValueOnce(jsonResponse({ ...value, items: [{ ...value.items[0], comparison_id: -1 }] }));
  const api = createComparisonV2Api({ fetchImpl });
  expect(await api.history()).toEqual(value);
  expect(fetchImpl.mock.calls[0][0]).toMatch(/comparisons-v2\/history$/);
  expect(fetchImpl.mock.calls[0][1].method).toBe('GET');
  await expect(api.history(43)).rejects.toThrow();
});

test('v2 selection and confirmation use the approved bodies and validate receipt ownership', async () => {
  const selected = { ...structuredClone(fixture.completed), selected_execution_id: 4305,
    version: fixture.completed.version + 1, confirmable: true };
  const operation = { executionId: 4305, version: selected.version, key: 'stable-confirm-key' };
  const confirmed = { profile: 'comparison-v2', schema_version: 2, comparison_id: 43,
    execution_id: 4305, version: selected.version + 1, receipt: {
      schema_version: 1, id_optimizacion: 43, confirmed: true,
      orders: [{ id_pedido: 1, estado: 'CONFIRMADO' }],
      materials_consumed: [{ material_source: 'PLANCHA', material_id: 1, stock_unit_index: 1 }], remnants_created: [],
    } };
  const fetchImpl = vi.fn().mockResolvedValueOnce(jsonResponse(selected)).mockResolvedValueOnce(jsonResponse(confirmed))
    .mockResolvedValueOnce(jsonResponse({ ...confirmed, execution_id: 4306 }));
  const api = createComparisonV2Api({ fetchImpl });
  expect(await api.choose(fixture.completed, 4305)).toEqual(selected);
  expect(await api.confirm(selected, operation)).toEqual(confirmed);
  expect(fetchImpl.mock.calls[0][0]).toMatch(/comparisons-v2\/43\/selection$/);
  expect(JSON.parse(fetchImpl.mock.calls[0][1].body)).toEqual({ execution_id: 4305, expected_version: fixture.completed.version });
  expect(fetchImpl.mock.calls[1][0]).toMatch(/comparisons-v2\/43\/confirm$/);
  expect(fetchImpl.mock.calls[1][1].headers['Idempotency-Key']).toBe(operation.key);
  expect(JSON.parse(fetchImpl.mock.calls[1][1].body)).toEqual({ execution_id: 4305, expected_version: selected.version });
  await expect(api.confirm(selected, operation)).rejects.toThrow();
});

test('v2 start, ID/key recovery and execution reads stay on the explicit v2 paths', async () => {
  const fetchImpl = vi.fn().mockResolvedValueOnce(jsonResponse(fixture.accepted))
    .mockResolvedValueOnce(jsonResponse(fixture.completed)).mockResolvedValueOnce(jsonResponse(fixture.completed))
    .mockResolvedValueOnce(jsonResponse(fixture.results['4301']));
  const api = createComparisonV2Api({ token: 'secret', fetchImpl });
  expect((await api.start([1], 'stable-key-0001')).profile).toBe('comparison-v2');
  expect(fetchImpl.mock.calls[0][0]).toMatch(/\/api\/optimization\/comparisons-v2$/);
  expect(fetchImpl.mock.calls[0][1].headers['Idempotency-Key']).toBe('stable-key-0001');
  const current = await api.load(43);
  expect((await api.lookup('stable-key-0001')).comparison_id).toBe(current.comparison_id);
  expect((await api.result(current, current.executions[0])).result.metodo).toBe('FF');
  expect(fetchImpl.mock.calls.slice(1).map(call => call[0])).toEqual([
    expect.stringMatching(/comparisons-v2\/43$/), expect.stringMatching(/comparisons-v2\/requests\/stable-key-0001$/),
    expect.stringMatching(/comparisons-v2\/43\/executions\/4301$/),
  ]);
});

test('manifest pages and mask windows preserve comparison/execution/method ownership', async () => {
  const mask = descriptor();
  const manifest = { profile: 'comparison-v2', schema_version: 2, comparison_id: 43, execution_id: 4301,
    method: 'FF', revision: 1, execution_sequence: 2, preparation_completed: true, processed_units: 0,
    evaluations: 0, phase: 'PREPARATION', current: null, last_orientation: null, ordered_units: [], total: 1,
    next_offset: null, items: [mask] };
  const window = { ...mask, geometria: { type: 'RECTANGULO', width_mm: 4, height_mm: 2 },
    geometria_original: { type: 'RECTANGULO', width_mm: 4, height_mm: 2 },
    window: { row_start: 0, row_count: 2, column_start: 0, column_count: 4 },
    spans_by_row: [{ row: 0, runs: [[0, 2]] }, { row: 1, runs: [[0, 2]] }] };
  const fetchImpl = vi.fn().mockResolvedValueOnce(jsonResponse(manifest)).mockResolvedValueOnce(jsonResponse(window));
  const api = createComparisonV2Api({ token: 'secret', fetchImpl });
  const current = fixture.completed, execution = current.executions[0];
  expect((await api.manifest(current, execution)).items).toEqual([mask]);
  const adapter = api.forExecution(current.comparison_id, execution);
  expect((await adapter.loadVisualMask(current.comparison_id, mask, { row_start: 0, row_count: 2,
    column_start: 0, column_count: 4 })).window).toEqual(window.window);
  expect(fetchImpl.mock.calls[0][0]).toMatch(/\/executions\/4301\/visual\?offset=0$/);
  expect(fetchImpl.mock.calls[1][0]).toMatch(/\/executions\/4301\/visual\/masks\/a{32}\?/);
});

test('a mask descriptor from another engine is rejected before any HTTP request', async () => {
  const fetchImpl = vi.fn();
  const api = createComparisonV2Api({ fetchImpl });
  const current = fixture.completed, ff = current.executions[0], bfMask = descriptor(4302, 'BF');
  await expect(api.forExecution(43, ff).loadVisualMask(43, bfMask)).rejects.toThrow();
  expect(fetchImpl).not.toHaveBeenCalled();
});
