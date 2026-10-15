import { createFixturePendingOrdersSource } from './pendingOrdersSource';
import { pieceCount } from './optimizationModel';

const rectangle = (width_mm, height_mm) => ({ type: 'RECTANGULO', width_mm, height_mm });
const piece = (id_pieza, id_tipo_vidrio, espesor_mm, geometria) => ({ id_pieza, id_tipo_vidrio, espesor_mm, geometria, cantidad: 1, tipo_forma: geometria.type });
export const fixtureOrders = [
  { id_pedido: 21, cliente: 'Vidrios Norte', estado: 'PENDIENTE', piezas: [
    piece(101, 1, 6, rectangle(800, 600)), piece(102, 1, 6, rectangle(600, 400)),
    piece(103, 2, 5.5, { type: 'CIRCUNFERENCIA', radius_mm: 240 }),
  ] },
  { id_pedido: 22, cliente: 'Constructora Sur', estado: 'PENDIENTE', piezas: [
    piece(104, 1, 6, { type: 'POLIGONO_CONVEXO', vertices_mm: [[0, 0], [500, 0], [400, 400], [0, 300]] }),
  ] },
];
export const newFixtureOrder = { id_pedido: 24, cliente: 'Cliente nuevo', estado: 'PENDIENTE', piezas: [piece(105, 2, 5.5, rectangle(500, 300))] };

// These records are synthetic inventory, never commercial defaults for real stock.
const fixtureSheet = { id_plancha: 15, ancho_mm: 3300, alto_mm: 2140, id_tipo_vidrio: 1, espesor_mm: 6 };
export function sheetToContainer(sheet, materialName) {
  const width = Number(sheet.ancho_mm), height = Number(sheet.alto_mm);
  if (![width, height].every(n => Number.isFinite(n) && n > 0)) throw new Error('La plancha no tiene dimensiones registradas válidas.');
  return { material_source: 'plancha', material_id: sheet.id_plancha, material_width_mm: width,
    material_height_mm: height, geometry: rectangle(width, height), material_name: materialName, espesor_mm: Number(sheet.espesor_mm) };
}
const containers = {
  '1:6': sheetToContainer(fixtureSheet, 'Templado'),
  '2:5.5': { material_source: 'retazo', material_id: 8, material_width_mm: 1600, material_height_mm: 1000,
    geometry: rectangle(1600, 1000), material_name: 'Bronce', espesor_mm: 5.5 },
};
const placements = {
  101: { x_mm: 80, y_mm: 80, rotation_deg: 0 },
  102: { x_mm: 1400, y_mm: 80, rotation_deg: 90 },
  103: { x_mm: 60, y_mm: 60, rotation_deg: 0 },
  104: { x_mm: 2000, y_mm: 150, rotation_deg: 30 },
  105: { x_mm: 700, y_mm: 80, rotation_deg: 0 },
};
const area = geometry => {
  if (geometry.type === 'RECTANGULO') return geometry.width_mm * geometry.height_mm;
  if (geometry.type === 'CIRCUNFERENCIA') return Math.PI * geometry.radius_mm ** 2;
  const vertices = geometry.vertices_mm;
  return Math.abs(vertices.reduce((sum, [x, y], i) => {
    const [nx, ny] = vertices[(i + 1) % vertices.length]; return sum + x * ny - nx * y;
  }, 0)) / 2;
};

export function prepareFixture(ids, available = [...fixtureOrders, newFixtureOrder]) {
  const orders = structuredClone(available.filter(o => ids.includes(o.id_pedido) && o.estado === 'PENDIENTE'));
  if (!orders.length || orders.length !== ids.length) throw new Error('Selecciona pedidos pendientes válidos.');
  const groups = [];
  for (const order of orders) for (const p of order.piezas) {
    const id = `${p.id_tipo_vidrio}:${Number(p.espesor_mm)}`;
    let group = groups.find(g => g.id === id);
    if (!group) { group = { id, name: containers[id].material_name, thickness: p.espesor_mm, orders: [], units: [], containers: [containers[id]] }; groups.push(group); }
    if (!group.orders.includes(order.id_pedido)) group.orders.push(order.id_pedido);
    for (let unit_index = 0; unit_index < p.cantidad; unit_index++) group.units.push({ id_pedido: order.id_pedido, id_pieza: p.id_pieza, unit_index });
  }
  // Small explicit HU-015-compatible rectangle mask; no raster algorithm in UI.
  const rasters = { 101: { resolution_mm: 200, columns: 4, row_count: 3, occupied_cells: 12,
    spans_by_row: [0, 1, 2].map(row => ({ row, runs: [[0, 4]] })) } };
  return structuredClone({ orders, groups, rasters, total: pieceCount(orders), fixture: true });
}

export function fixtureEvents(snapshot) {
  const events = [{ type: 'optimization_started' }];
  for (const stage of ['preparing_orders', 'grouping_materials', 'rasterizing', 'sorting_pieces']) events.push({ type: 'stage_changed', stage });
  for (const group of snapshot.groups) {
    events.push({ type: 'group_started', group_id: group.id });
    for (const unit of group.units) {
      events.push({ type: 'piece_started', ...unit });
      events.push({ type: 'piece_placed', ...unit, ...placements[unit.id_pieza], group_id: group.id,
        material_source: group.containers[0].material_source, material_id: group.containers[0].material_id });
    }
    events.push({ type: 'group_completed', group_id: group.id });
  }
  const materialArea = snapshot.groups.reduce((n, g) => n + area(g.containers[0].geometry), 0);
  const usedArea = snapshot.orders.reduce((n, o) => n + o.piezas.reduce((s, p) => s + area(p.geometria) * p.cantidad, 0), 0);
  const utilization = Number((usedArea / materialArea * 100).toFixed(1));
  events.push({ type: 'stage_changed', stage: 'calculating_metrics' }, { type: 'metrics_calculated', metrics: {
    placed: snapshot.total, total: snapshot.total, orders: snapshot.orders.length, groups: snapshot.groups.length,
    remnants: snapshot.groups.filter(g => g.containers[0].material_source === 'retazo').length,
    sheets: snapshot.groups.filter(g => g.containers[0].material_source === 'plancha').length,
    utilization, waste: Number((100 - utilization).toFixed(1)), duration_ms: 842,
  } }, { type: 'optimization_completed' });
  return events;
}

export function createFixtureEventSource(snapshot, { delayMs = 220, schedule = setTimeout, cancel = clearTimeout, includeInternalStages = true } = {}) {
  let timer, stopped = false;
  return {
    subscribe(listener, runId) {
      stopped = false;
      const events = fixtureEvents(snapshot).filter(event => includeInternalStages || event.type !== 'stage_changed');
      let index = 0;
      function next() {
        if (stopped || index >= events.length) return;
        listener({ ...events[index++], run_id: runId });
        if (!stopped) timer = schedule(next, delayMs);
      }
      timer = schedule(next, delayMs);
      return () => { stopped = true; cancel(timer); };
    },
    dispose() { stopped = true; cancel(timer); },
  };
}
export const unavailableOptimizationAdapter = {
  async prepare() { throw new Error('La preparación First Fit con pedidos reales está pendiente del contrato backend. Puedes explorar la demostración con datos de ejemplo.'); },
  async confirm() { throw new Error('No se guardó la solución: el endpoint de confirmación todavía no está disponible. No se modificó el inventario.'); },
};
export function createFixtureAdapter(options) {
  return { isFixture: true, prepare: async ids => prepareFixture(ids), createEventSource: snapshot => createFixtureEventSource(snapshot, options),
    confirm: unavailableOptimizationAdapter.confirm };
}
export function createDemoOrdersSource() {
  return createFixturePendingOrdersSource(fixtureOrders, { changes: [
    { afterMs: 7000, type: 'upsert', order: newFixtureOrder },
  ] });
}
