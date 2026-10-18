// Authored wire examples, never a packing algorithm or inventory calculation.
import shared from './contractV1Fixture.json' with { type: 'json' };

const ratio = (placed, total) => total === 3
  ? ['0', '33.33333333333333333333333333', '66.66666666666666666666666667', '100'][placed]
  : String(placed / total * 100);
export const fixtureProgress = (placed, total) => ({ placed_units: placed, total_units: total, progress_pct: ratio(placed, total) });

export function eventsForRun(result) {
  const result_url = shared.success_events.at(-1).data.result_url.replace('/101', `/${result.id_optimizacion}`);
  const rows = [];
  const push = (event, data) => rows.push({ schema_version: 1, sequence: rows.length + 1,
    event, id_optimizacion: result.id_optimizacion, occurred_at: '2026-10-16T15:00:00Z', data });
  push('optimization_started', { metodo: 'FF', order_ids: result.order_ids, total_units: result.total_units,
    groups: result.groups.map(({ id_tipo_vidrio, espesor_mm }) => ({ id_tipo_vidrio, espesor_mm })), configuracion: result.configuracion });
  let placed = 0;
  for (const group of result.groups) {
    const key = { id_tipo_vidrio: group.id_tipo_vidrio, espesor_mm: group.espesor_mm };
    push('group_started', { ...key, total_units: group.units.length });
    let groupPlaced = 0;
    for (const unit of group.units) {
      const { id_pedido, id_pieza, unit_index } = unit;
      push('piece_started', { ...key, id_pedido, id_pieza, unit_index, ...fixtureProgress(placed, result.total_units) });
      const p = result.placements.find(p => p.id_pedido === id_pedido && p.id_pieza === id_pieza && p.unit_index === unit_index);
      if (p) {
        placed++; groupPlaced++;
        const material = result.materials_used.find(s => s.material_source === p.material_source && s.material_id === p.material_id && s.stock_unit_index === p.stock_unit_index);
        push('piece_placed', { ...p, material, ...fixtureProgress(placed, result.total_units) });
      }
    }
    push('group_completed', { ...key, ...fixtureProgress(groupPlaced, group.units.length), result_url });
  }
  if (result.estado === 'EN_EJECUCION') return structuredClone(rows);
  if (result.estado === 'FALLIDA') {
    push('optimization_failed', { ...shared.failed_event.data, result_url });
  } else {
    push('metrics_calculated', { metrics_available: result.metrics_available, metrics: result.metrics });
    push('optimization_completed', { estado: result.estado, completo: result.completo,
      ...fixtureProgress(result.placed_units, result.total_units), result_url });
  }
  return structuredClone(rows);
}

export function scenarioFixture(scenario = 'complete') {
  const result = structuredClone(shared.result);
  // Four units, two orders/materials, two physical units of sheet 5 plus remnant 8.
  const original = result.groups[0].units[0];
  const a = { ...original, unit_index: 1 };
  const b = { ...original, unit_index: 2 };
  const c = { ...original, unit_index: 3 };
  const d = { ...original, id_pedido: 11, id_pieza: 28, unit_index: 1, id_tipo_vidrio: 8,
    espesor_mm: '4', geometria: { type: 'RECTANGULO', width_mm: 4, height_mm: 2 }, area_mm2: '8' };
  result.order_ids = [10, 11];
  result.groups = [{ id_tipo_vidrio: 7, espesor_mm: '6.00', units: [a, b, c] },
    { id_tipo_vidrio: 8, espesor_mm: '4', units: [d] }];
  const first = result.materials_used[0];
  const second = { ...first, stock_unit_index: 2 };
  const remnant = { ...first, material_source: 'RETAZO', material_id: 8, stock_unit_index: 1,
    id_tipo_vidrio: 8, espesor_mm: '4', geometria: { type: 'RECTANGULO', width_mm: 20, height_mm: 20 }, area_mm2: '400' };
  result.materials_used = [first, second, remnant];
  const make = (u, s, x, angle = '0', oriented = u.geometria) => ({
    id_pedido: u.id_pedido, id_pieza: u.id_pieza, unit_index: u.unit_index, id_tipo_vidrio: u.id_tipo_vidrio, espesor_mm: u.espesor_mm,
    material_source: s.material_source, material_id: s.material_id, stock_unit_index: s.stock_unit_index,
    x_mm: x, y_mm: '0', rotation_deg: angle, resolution_mm: '5', geometria: oriented,
  });
  result.placements = [make(a, first, '0'), make(b, second, '0', '90', { type: 'RECTANGULO', width_mm: 5, height_mm: 10 }),
    make(c, second, '10'), make(d, remnant, '0')];
  result.total_units = 4; result.placed_units = 4; result.progress_pct = '100';
  // No fabricated R4 metrics for these alternative illustrative scenarios.
  result.metrics_available = false; result.metrics = null; result.tiempo_computacional_ms = null;
  if (scenario === 'incomplete' || scenario === 'failed' || scenario === 'running') {
    const missing = result.placements.pop();
    result.materials_used.pop(); result.placed_units = 3; result.progress_pct = '75'; result.completo = false; result.confirmable = false;
    result.estado = ({ incomplete: 'SIN_SOLUCION', failed: 'FALLIDA', running: 'EN_EJECUCION' })[scenario];
    const { id_pedido, id_pieza, unit_index, id_tipo_vidrio, espesor_mm } = missing;
    result.unplaced_units = [{ id_pedido, id_pieza, unit_index, id_tipo_vidrio, espesor_mm,
      reason: ({ incomplete: 'NO_FIT', failed: 'INTERRUPTED', running: 'PENDING' })[scenario] }];
  }
  if (scenario === 'not-confirmable') result.estado = 'EN_EJECUCION', result.confirmable = false;
  if (scenario === 'confirmed') result.confirmed = true, result.confirmable = false;
  return result;
}
