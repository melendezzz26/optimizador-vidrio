import { expect, test } from 'vitest';
import { initialOptimization, optimizationReducer } from '../optimizationModel';
import { resultSnapshot } from '../runContract';
import shared from '../contractV1Fixture.json';

const b = shared.success_events;
const unit = b[2].data;
const placed = b[3].data;
const source = { material_source: placed.material_source, material_id: placed.material_id, stock_unit_index: placed.stock_unit_index };
const mask = { id_optimizacion: 101, available: true, mask_ref: 'a'.repeat(32), kind: 'PIECE',
  resolution_mm: placed.resolution_mm, rotation_deg: placed.rotation_deg, columns: 10, row_count: 5, occupied_cells: 50,
  piece: { id_pedido: unit.id_pedido, id_pieza: unit.id_pieza }, source: null, reason: null };
const material = { ...mask, mask_ref: 'b'.repeat(32), kind: 'MATERIAL', columns: 100, row_count: 50, occupied_cells: 5000, piece: null, source };
const piece = { id_pedido: unit.id_pedido, id_pieza: unit.id_pieza, id_tipo_vidrio: unit.id_tipo_vidrio, espesor_mm: unit.espesor_mm, cantidad: 1 };
const prep = { unique_pieces: 1, material_bases: 1, total_units: 1 };
const policy = { profile: 'visual-v2', representative_orientations: true, max_extra_samples: 128,
  max_extra_samples_per_second: 10, retention_max_seconds: 300, retention_may_end_earlier: true };
const events = () => [
  { event: b[0].event, data: { ...b[0].data, visual: policy } },
  { event: 'preparation_started', data: { ...prep, metodo: 'FF', configuracion: shared.result.configuracion } },
  { event: 'piece_rasterizing', data: piece },
  { event: 'piece_ready', data: { ...piece, mask } },
  { event: 'preparation_completed', data: prep },
  b[1], { event: b[2].event, data: { ...unit, processed_units: 0 } },
  { event: 'orientation_testing', data: { ...unit, processed_units: 0, evaluation_index: 1, sampled: true, source, mask } },
  { event: 'source_selected', data: { ...unit, placed_units: 1, progress_pct: '100', processed_units: 1,
    source, mask, material_mask: material, score_name: null, score: null } },
  { event: b[3].event, data: { ...placed, processed_units: 1 } }, b[4], b[5],
  { event: b[6].event, data: { ...b[6].data, processed_units: 1 } },
].map((value, index) => ({ ...value, schema_version: 2, sequence: index + 1,
  id_optimizacion: 101, occurred_at: '2026-10-27T23:00:00Z' }));
const start = () => optimizationReducer({ ...initialOptimization, snapshot: resultSnapshot(shared.result), status: 'prepared' }, { type: 'run', runId: 'visual-test' });
const accept = (state, event) => optimizationReducer(state, { type: 'visual_event', event, runId: 'visual-test' });

test('interleaved V2 facts preserve the V1 state machine and confirm only after canonical GET', () => {
  let state = events().reduce(accept, start());
  expect(state.error).toBe('');
  expect(state.status).toBe('completed');
  expect(state.sequence).toBe(shared.success_events.length);
  expect(state.visual.sequence).toBe(events().length);
  expect(state.visual.preparation).toBe('complete');
  expect(state.visual.processed).toBe(1);
  expect(state.visual.order).toEqual([{ id_pedido: 10, id_pieza: 27, unit_index: 1 }]);
  expect(state.confirmable).toBe(false);
  state = optimizationReducer(state, { type: 'result', result: shared.result });
  expect(state.confirmable).toBe(true);
  expect(state.placements).toHaveLength(1);
});

test.each(['resolution', 'placement-angle', 'configuration', 'sequence'])('%s mismatch fails without fabricating confirmation', kind => {
  const values = structuredClone(events());
  if (kind === 'resolution') values[7].data.mask.resolution_mm = '2';
  if (kind === 'placement-angle') values[8].data.mask.rotation_deg = '90';
  if (kind === 'configuration') values[1].data.configuracion.margen_mm = '9';
  if (kind === 'sequence') values[2].sequence++;
  const state = values.reduce(accept, start());
  expect(state.status).toBe('failed');
  expect(state.confirmable).toBe(false);
});

test('discard suppresses delayed facts from the previous run', () => {
  let state = events().slice(0, 5).reduce(accept, start());
  state = optimizationReducer(state, { type: 'discard' });
  const after = accept(state, events()[5]);
  expect(after).toBe(state);
  expect(after.visual.enabled).toBe(false);
});

test('V2 keeps the time-budget feedback and never treats a technical failure as NO_FIT', () => {
  let state = events().slice(0, 8).reduce(accept, start());
  state = accept(state, { ...events()[8], event: 'optimization_failed', data: {
    code: 'TIME_BUDGET_EXCEEDED', message: 'Se agotó el tiempo de cálculo.',
    result_url: '/api/optimization/runs/101', estado: 'FALLIDA',
  } });
  expect(state.status).toBe('failed');
  expect(state.errorKind).toBe('time_budget');
  expect(state.unplaced_units).toEqual([]);
  expect(state.confirmable).toBe(false);
});
