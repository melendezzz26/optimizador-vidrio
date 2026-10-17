import { createFixturePendingOrdersSource } from './pendingOrdersSource';
import { pieceCount } from './optimizationModel';
import { detectMaterialGroups } from './materialGroups';
import { eventsForRun, fixtureProgress } from './runFixtures.js';
import { visualPlacement } from './runContract.js';

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
  return { material_source: 'PLANCHA', stock_unit_index: 1, material_id: sheet.id_plancha, material_width_mm: width,
    material_height_mm: height, geometry: rectangle(width, height), material_name: materialName, id_tipo_vidrio: sheet.id_tipo_vidrio, espesor_mm: Number(sheet.espesor_mm) };
}
const containers = {
  '1:6': sheetToContainer(fixtureSheet, 'Templado'),
  '2:5.5': { material_source: 'RETAZO', stock_unit_index: 1, material_id: 8, material_width_mm: 1600, material_height_mm: 1000,
    geometry: rectangle(1600, 1000), material_name: 'Bronce', espesor_mm: 5.5 },
};
// Decoupled, synthetic inventory source. No commercial defaults for real orders.
export function fixtureMaterialSource(id) {
  if (id === '1:6') return { name: 'Templado', containers: [containers[id]] };
  if (id === '2:5.5') return { name: 'Bronce', containers: [
    sheetToContainer({ id_plancha: 16, ancho_mm: 1600, alto_mm: 1000, id_tipo_vidrio: 2, espesor_mm: 5.5 }, 'Bronce'),
    { ...containers[id], id_tipo_vidrio: 2 },
  ] };
  return null;
}
const placements = {
  101: { x_mm: 80, y_mm: 80, rotation_deg: 0 },
  102: { x_mm: 1400, y_mm: 80, rotation_deg: 90 },
  103: { x_mm: 60, y_mm: 60, rotation_deg: 0 },
  104: { x_mm: 2000, y_mm: 150, rotation_deg: 30 },
  105: { x_mm: 700, y_mm: 80, rotation_deg: 0 },
};
export function prepareFixture(ids, available = [...fixtureOrders, newFixtureOrder]) {
  const orders = structuredClone(available.filter(o => ids.includes(o.id_pedido) && o.estado === 'PENDIENTE'));
  if (!orders.length || orders.length !== ids.length) throw new Error('Selecciona pedidos pendientes válidos.');
  const { groups, unresolved } = detectMaterialGroups(orders, fixtureMaterialSource);
  if (unresolved.length || groups.some(g => !g.containers.length)) throw new Error('Falta material, espesor o plancha base en la fuente de demostración.');
  // Explicit, illustrative HU-015 span masks. No rasterization algorithm in UI.
  const mask = (columns, runs) => ({ resolution_mm: 100, columns, row_count: runs.length,
    occupied_cells: runs.reduce((n, [start, end]) => n + end - start, 0),
    spans_by_row: runs.map((run, row) => ({ row, runs: [run] })) });
  const availableRasters = {
    101: mask(8, Array.from({ length: 6 }, () => [0, 8])),
    102: mask(6, Array.from({ length: 4 }, () => [0, 6])),
    103: mask(5, [[1, 4], [0, 5], [0, 5], [0, 5], [1, 4]]),
    104: mask(5, [[0, 5], [0, 5], [0, 5], [1, 4]]),
    105: mask(5, [[0, 5], [0, 5], [0, 5]]),
  };
  const rasters = Object.fromEntries(orders.flatMap(o => o.piezas.map(p => [p.id_pieza, availableRasters[p.id_pieza]])));
  return structuredClone({ orders, groups, rasters, total: pieceCount(orders), fixture: true });
}

export function fixtureRun(snapshot) {
  const areas = { 101: '480000', 102: '240000', 103: '180955.74', 104: '160000', 105: '150000' };
  const oriented = {
    102: rectangle(400, 600),
    104: { type: 'POLIGONO_CONVEXO', vertices_mm: [[150, 0], [583.012702, 250], [296.410162, 546.410162], [0, 259.807621]] },
  };
  const stock = c => ({ material_source: c.material_source, material_id: c.material_id, stock_unit_index: c.stock_unit_index,
    id_tipo_vidrio: c.id_tipo_vidrio, espesor_mm: String(c.espesor_mm), geometria: c.geometry,
    area_mm2: String(c.material_width_mm * c.material_height_mm) });
  const materials = snapshot.groups.map(g => stock(g.containers[0]));
  const groups = snapshot.groups.map(g => ({ id_tipo_vidrio: g.materialId, espesor_mm: String(g.thickness), units: g.units.map(u => {
    const piece = snapshot.orders.find(o => o.id_pedido === u.id_pedido).piezas.find(p => p.id_pieza === u.id_pieza);
    return { ...u, id_tipo_vidrio: piece.id_tipo_vidrio, espesor_mm: String(piece.espesor_mm),
      tipo_forma: piece.tipo_forma, geometria: piece.geometria, area_mm2: areas[piece.id_pieza] };
  }) }));
  const placed = groups.flatMap(g => g.units.map(u => {
    const c = materials.find(c => c.id_tipo_vidrio === g.id_tipo_vidrio && c.espesor_mm === g.espesor_mm);
    const position = placements[u.id_pieza];
    return { id_pedido: u.id_pedido, id_pieza: u.id_pieza, unit_index: u.unit_index,
      id_tipo_vidrio: u.id_tipo_vidrio, espesor_mm: u.espesor_mm,
      material_source: c.material_source, material_id: c.material_id, stock_unit_index: c.stock_unit_index,
      x_mm: String(position.x_mm), y_mm: String(position.y_mm), rotation_deg: String(position.rotation_deg),
      resolution_mm: '100', geometria: oriented[u.id_pieza] ?? u.geometria };
  }));
  const fullDemo = snapshot.total === 4 && snapshot.orders.some(o => o.id_pedido === 22);
  return { schema_version: 1, id_optimizacion: 301, metodo: 'FF', estado: 'COMPLETADA',
    order_ids: snapshot.orders.map(o => o.id_pedido), groups, placements: placed, materials_used: materials, unplaced_units: [],
    configuracion: { resolucion_raster_mm: '100', margen_mm: '0', separacion_mm: '0', paso_angular_grados: '5' },
    ...fixtureProgress(snapshot.total, snapshot.total), completo: true, metrics_available: fullDemo,
    metrics: fullDemo ? { aprovechamiento_pct: '12.248391366889864', merma_mm2: '7601044.26', planchas_nuevas_usadas: 2,
      retazo_recuperable_mm2: '0', area_material_total_mm2: '8662000', area_piezas_colocadas_mm2: '1060955.74', tiempo_computacional_ms: 842 } : null,
    tiempo_computacional_ms: fullDemo ? 842 : null, confirmed: false, confirmable: true };
}
export const fixtureEvents = snapshot => eventsForRun(fixtureRun(snapshot));
export const fixturePlacements = snapshot => fixtureEvents(snapshot).filter(e => e.event === 'piece_placed').map(e => visualPlacement(e.data));

export function createFixtureEventSource(snapshot, { delayMs = 220, schedule = setTimeout, cancel = clearTimeout } = {}) {
  let timer, stopped = false;
  return {
    subscribe(listener) {
      stopped = false;
      const events = fixtureEvents(snapshot);
      let index = 0;
      function next() {
        if (stopped || index >= events.length) return;
        listener(events[index++]);
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
  async loadResult() { throw new Error('La consulta del resultado está pendiente del backend.'); },
  async confirm() { throw new Error('No se guardó la solución: el endpoint de confirmación todavía no está disponible. No se modificó el inventario.'); },
};
export function createFixtureAdapter(options) {
  let result;
  return { isFixture: true, resolveMaterial: fixtureMaterialSource,
    prepare: async request => prepareFixture(request.order_ids),
    createEventSource: (request, { snapshot }) => {
      if (JSON.stringify(request.order_ids) !== JSON.stringify(snapshot.orders.map(o => o.id_pedido))) throw new Error('La selección cambió.');
      result = fixtureRun(snapshot); return createFixtureEventSource(snapshot, options);
    },
    loadResult: async () => structuredClone(result),
    confirm: unavailableOptimizationAdapter.confirm };
}
export function createDemoOrdersSource() {
  return createFixturePendingOrdersSource(fixtureOrders, { changes: [
    { afterMs: 7000, type: 'upsert', order: newFixtureOrder },
  ] });
}
