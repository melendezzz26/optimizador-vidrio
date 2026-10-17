import { test } from 'node:test';
import assert from 'node:assert/strict';
import { initialOptimization, optimizationReducer as reduce } from '../../src/features/optimization/optimizationModel.js';
import { scenarioFixture, eventsForRun } from '../../src/features/optimization/runFixtures.js';
import { resultSnapshot } from '../../src/features/optimization/runContract.js';
const result = scenarioFixture();
const snapshot = resultSnapshot(result);
const orders = snapshot.orders.map(o => ({ ...o, estado: 'PENDIENTE' }));
function running() {
  let s = reduce(initialOptimization, { type: 'orders_received', orders });
  s = reduce(s, { type: 'select', ids: [10, 11] });
  s = reduce(s, { type: 'preparing' }); s = reduce(s, { type: 'prepared', snapshot });
  return reduce(s, { type: 'run', runId: 'a' });
}
const apply = (s, event, runId = 'a') => reduce(s, { type: 'event', event, runId });
const played = name => eventsForRun(scenarioFixture(name)).reduce((s, e) => apply(s, e), running());
test('canonical recovery preserves a safe failure message without inventing a PENDIENTE transition', () => {
  const failed = played('failed');
  const recovered = reduce(failed, { type: 'result', result: scenarioFixture('failed') });
  assert.equal(recovered.estado, 'FALLIDA'); assert.equal(recovered.confirmable, false);
  assert.equal(recovered.error, failed.error); assert.ok(recovered.error);
  const loaded = reduce(initialOptimization, { type: 'result', result: scenarioFixture('failed') });
  assert.equal(loaded.estado, 'FALLIDA'); assert.match(loaded.error, /No se pudo calcular el corte/);
});
test('wire events preserve 1-based units, physical stock and decimal strings; duplicate sequence ignored', () => {
  let s = running(); const events = eventsForRun(result);
  for (const event of events.slice(0, 6)) s = apply(s, event);
  assert.equal(s.placements.length, 2);
  assert.deepEqual(s.placements.map(p => p.unit_index), [1, 2]);
  assert.deepEqual(s.placements.map(p => p.stock_unit_index), [1, 2]);
  assert.equal(s.placements[1].rotation_deg, '90');
  assert.equal(apply(s, events[5]).placements.length, 2);
});
test('terminal with nullable metrics is not a failure; confirmation waits for canonical GET', () => {
  const s = played('complete'); assert.equal(s.estado, 'COMPLETADA'); assert.equal(s.status, 'completed');
  assert.equal(s.metrics, null); assert.equal(s.confirmable, false);
  const loaded = reduce(s, { type: 'result', result }); assert.equal(loaded.confirmable, true);
});
test('SIN_SOLUCION retains diagnostic placements and cannot confirm', () => {
  const s = played('incomplete'); assert.equal(s.estado, 'SIN_SOLUCION'); assert.equal(s.placements.length, 3);
  assert.equal(s.placed_units, 3); assert.equal(s.total_units, 4); assert.equal(s.confirmable, false);
});
test('failed event shows safe error, canonical confirmed snapshot disables confirmation', () => {
  const s = played('failed'); assert.equal(s.estado, 'FALLIDA'); assert.equal(s.status, 'failed');
  assert.match(s.error, /No se pudo completar/);
  const loaded = reduce(initialOptimization, { type: 'result', result: scenarioFixture('confirmed') });
  assert.equal(loaded.confirmed, true); assert.equal(loaded.confirmable, false);
});
test('sequence gaps, mismatched correlation and malformed placement fail without polluting canvas', () => {
  const events = eventsForRun(result);
  for (const mutation of [e => ({ ...e, sequence: 9 }), e => ({ ...e, id_optimizacion: 999 }),
    e => ({ ...e, data: { ...e.data, unit_index: 0 } }), e => ({ ...e, data: { ...e.data, material_source: 'plancha' } })]) {
    let s = events.slice(0, 3).reduce((s, e) => apply(s, e), running());
    s = apply(s, mutation(events[3])); assert.equal(s.status, 'failed'); assert.equal(s.placements.length, 0);
  }
});
test('retry and discard reject stale lifecycle events', () => {
  let s = played('failed'); s = reduce(s, { type: 'run', runId: 'b' });
  assert.equal(s.placements.length, 0);
  assert.equal(apply(s, eventsForRun(result)[0]).optimizationId, null);
  s = reduce(s, { type: 'discard' }); assert.equal(s.snapshot, null); assert.equal(s.runId, null);
});
test('live updates reconcile selection but preserve run snapshot', () => {
  const s = running();
  const next = reduce(s, { type: 'orders_received', orders: [] });
  assert.deepEqual(next.selected, []); assert.equal(next.snapshot.orders.length, 2);
  assert.equal(next.snapshot.groups[0].units.length, 3);
});
test('new orders are unselected, non-pending excluded and preparation invalidated', () => {
  let s = reduce(initialOptimization, { type: 'orders_received', orders: [...orders, { id_pedido: 99, estado: 'CANCELADO' }] });
  s = reduce(s, { type: 'select', ids: [10, 11, 99] }); assert.deepEqual(s.selected, [10, 11]);
  s = reduce(s, { type: 'preparing' }); s = reduce(s, { type: 'orders_received', orders: [] });
  assert.equal(reduce(s, { type: 'prepared', snapshot }).snapshot, null);
});
test('group-scoped completion does not replace global progress', () => {
  let s = running();
  for (const event of eventsForRun(result)) {
    s = apply(s, event);
    if (event.event === 'group_completed' && event.data.id_tipo_vidrio === 8) {
      assert.equal(event.data.placed_units, 1); assert.equal(s.placed_units, 4);
    }
  }
  assert.equal(s.progress_pct, '100');
});
