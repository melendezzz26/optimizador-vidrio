import { test } from 'node:test';
import assert from 'node:assert/strict';
import { initialOptimization, optimizationReducer as reduce } from '../../src/features/optimization/optimizationModel.js';
const orders = [{ id_pedido: 21, estado: 'PENDIENTE', piezas: [{ id_pieza: 101, cantidad: 2, id_tipo_vidrio: 1, espesor_mm: 6 }] }];
const snapshot = { orders, groups: [{ id: '1:6', containers: [{ material_source: 'plancha', material_id: 15, espesor_mm: 6, id_tipo_vidrio: 1 }], units: [0, 1].map(unit_index => ({ id_pedido: 21, id_pieza: 101, unit_index })) }] };
function running() {
  let s = reduce(initialOptimization, { type: 'orders_received', orders });
  s = reduce(s, { type: 'select', ids: [21] });
  s = reduce(s, { type: 'preparing' });
  s = reduce(s, { type: 'prepared', snapshot });
  return reduce(s, { type: 'run', runId: 'a' });
}
const event = (state, type, extra = {}) => reduce(state, { type: 'event', event: { type, run_id: 'a', ...extra } });
const placement = { id_pedido: 21, id_pieza: 101, unit_index: 0, group_id: '1:6', material_source: 'plancha', material_id: 15, x_mm: 10, y_mm: 20, rotation_deg: 37.5 };
test('placement deduplicates units and preserves arbitrary rotation', () => {
  let s = event(running(), 'piece_placed', placement);
  s = event(s, 'piece_placed', placement);
  assert.equal(s.placements.length, 1); assert.equal(s.placements[0].rotation_deg, 37.5);
  s = event(s, 'piece_placed', { ...placement, unit_index: 1 });
  assert.equal(s.placements.length, 2);
});
test('group, stage, metrics and completion events', () => {
  let s = event(running(), 'optimization_started');
  s = event(s, 'stage_changed', { stage: 'sorting_pieces' }); assert.equal(s.stage, 'sorting_pieces');
  s = event(s, 'group_started', { group_id: '1:6' }); assert.equal(s.activeGroup, '1:6');
  s = event(s, 'piece_started', { id_pieza: 101 }); assert.equal(s.activePiece, 101);
  s = event(s, 'group_completed', { group_id: '1:6' }); assert.deepEqual(s.completedGroups, ['1:6']);
  s = event(s, 'metrics_calculated', { metrics: { placed: 1, total: 2 } });
  s = event(s, 'optimization_completed'); assert.equal(s.status, 'completed'); assert.equal(s.metrics.placed, 1);
  assert.equal(event(s, 'optimization_failed').status, 'completed');
});
test('failed and retry reject stale events and clear old placements', () => {
  let s = event(running(), 'piece_placed', placement);
  s = event(s, 'optimization_failed', { message: 'Interrumpida' }); assert.equal(s.status, 'failed');
  s = reduce(s, { type: 'run', runId: 'b' }); assert.equal(s.placements.length, 0);
  assert.equal(event(s, 'piece_placed', placement).placements.length, 0);
});
test('live updates reconcile selection but preserve deep run snapshot', () => {
  const s = running();
  assert.notEqual(s.snapshot.orders, orders);
  const next = reduce(s, { type: 'orders_received', orders: [{ id_pedido: 24, estado: 'PENDIENTE' }] });
  assert.deepEqual(next.selected, []); assert.equal(next.snapshot.orders[0].id_pedido, 21);
  assert.equal(next.snapshot.orders[0].piezas[0].cantidad, 2);
});
test('non-pending excluded, new orders unselected and preparation invalidated', () => {
  let s = reduce(initialOptimization, { type: 'orders_received', orders: [...orders, { id_pedido: 22, estado: 'CANCELADO' }] });
  assert.equal(s.orders.length, 1);
  s = reduce(s, { type: 'select', ids: [21, 22] }); assert.deepEqual(s.selected, [21]);
  s = reduce(s, { type: 'preparing' });
  s = reduce(s, { type: 'orders_received', orders: [] });
  s = reduce(s, { type: 'prepared', snapshot }); assert.equal(s.snapshot, null);
});
test('invalid placement fails without polluting canvas', () => {
  for (const patch of [{ rotation_deg: NaN }, { unit_index: -1 }, { material_id: 999 }, { id_pieza: 999 }]) {
    const s = event(running(), 'piece_placed', { ...placement, ...patch });
    assert.equal(s.status, 'failed'); assert.equal(s.placements.length, 0);
  }
});
test('discard cancels run identity and missing metrics cannot complete', () => {
  const s = reduce(running(), { type: 'discard' }); assert.equal(s.snapshot, null); assert.equal(s.runId, null);
  assert.equal(event(s, 'piece_placed', placement).placements.length, 0);
  assert.equal(event(running(), 'optimization_completed').status, 'failed');
});

test('public events alone advance progress, metrics and completion without stage_changed', () => {
  let s = event(running(), 'optimization_started');
  assert.equal(s.stage, 'preparing_orders');
  s = event(s, 'group_started', { group_id: '1:6' });
  assert.equal(s.stage, 'first_fit');
  s = event(s, 'piece_started', { id_pieza: 101 });
  s = event(s, 'piece_placed', placement);
  s = event(s, 'piece_placed', { ...placement, unit_index: 1 });
  s = event(s, 'group_completed', { group_id: '1:6' });
  assert.equal(s.placements.length, 2);
  assert.deepEqual(s.completedGroups, ['1:6']);
  s = event(s, 'metrics_calculated', { metrics: { placed: 2, total: 2 } });
  assert.equal(s.stage, 'calculating_metrics');
  s = event(s, 'optimization_completed');
  assert.equal(s.status, 'completed');
  assert.equal(s.metrics.placed, 2);
});
