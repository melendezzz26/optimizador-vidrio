// T1 wire boundary. Decimal strings stay intact; conversion is restricted to rendering.
import { getGeometryBounds } from './visualizationGeometry.js';

const events = new Set(['optimization_started', 'group_started', 'piece_started', 'piece_placed',
  'group_completed', 'metrics_calculated', 'optimization_completed', 'optimization_failed']);
const states = new Set(['EN_EJECUCION', 'COMPLETADA', 'SIN_SOLUCION', 'FALLIDA']);
export class RunContractError extends Error {
  constructor() { super('No se pudo interpretar el avance del trabajo. Consulta el resultado antes de continuar.'); }
}
function require(value) { if (!value) throw new RunContractError(); }
const positiveId = n => Number.isSafeInteger(n) && n > 0;
const count = n => Number.isSafeInteger(n) && n >= 0;
const object = n => n !== null && typeof n === 'object' && !Array.isArray(n);

export function decimalKey(value) {
  const match = /^(\+|-)?(\d+)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/.exec(String(value));
  require(match);
  const exponent = Number(match[4] || 0) - (match[3]?.length || 0);
  require(Number.isSafeInteger(exponent) && Math.abs(exponent) <= 1000);
  let digits = (match[2] + (match[3] || '')).replace(/^0+/, '') || '0';
  if (digits === '0') return '0';
  let scale = exponent;
  while (digits.endsWith('0')) { digits = digits.slice(0, -1); scale++; }
  const position = digits.length + scale;
  const text = scale >= 0 ? digits + '0'.repeat(scale)
    : position > 0 ? `${digits.slice(0, position)}.${digits.slice(position)}` : `0.${'0'.repeat(-position)}${digits}`;
  return (match[1] === '-' ? '-' : '') + text;
}
function decimal(value, positive = false) {
  require(typeof value === 'string' && decimalKey(value)[0] !== '-');
  require(!positive || decimalKey(value) !== '0');
  return value;
}
export function renderNumber(value) {
  const number = Number(value);
  require((typeof value === 'string' || typeof value === 'number') && Number.isFinite(number));
  require(number !== 0 || decimalKey(value) === '0');
  return number;
}
export const groupKey = value => `${value.id_tipo_vidrio}:${decimalKey(value.espesor_mm)}`;
export const stockKey = value => `${value.material_source}:${value.material_id}:${value.stock_unit_index}`;
export const unitKey = value => `${value.id_pedido}:${value.id_pieza}:${value.unit_index}`;

export function buildRunRequest(orderIds) {
  require(Array.isArray(orderIds) && orderIds.length > 0 && orderIds.every(positiveId)
    && new Set(orderIds).size === orderIds.length);
  return { order_ids: [...orderIds] };
}
function materialKey(value) {
  require(object(value) && positiveId(value.id_tipo_vidrio)); decimal(value.espesor_mm, true);
}
function unit(value) {
  materialKey(value);
  require(positiveId(value.id_pedido) && positiveId(value.id_pieza) && positiveId(value.unit_index));
}
function geometry(value) { require(getGeometryBounds(value)); }
function material(value) {
  materialKey(value);
  require(['PLANCHA', 'RETAZO'].includes(value.material_source) && positiveId(value.material_id)
    && positiveId(value.stock_unit_index) && (value.material_source !== 'RETAZO' || value.stock_unit_index === 1));
  geometry(value.geometria); decimal(value.area_mm2, true);
  require(value.material_source !== 'PLANCHA' || value.geometria.type === 'RECTANGULO');
}
function placement(value) {
  unit(value);
  require(['PLANCHA', 'RETAZO'].includes(value.material_source) && positiveId(value.material_id)
    && positiveId(value.stock_unit_index) && (value.material_source !== 'RETAZO' || value.stock_unit_index === 1));
  for (const key of ['x_mm', 'y_mm', 'rotation_deg', 'resolution_mm']) decimal(value[key], key === 'resolution_mm');
  require(renderNumber(value.rotation_deg) < 360);
  geometry(value.geometria);
  if (value.geometria.type === 'POLIGONO_CONVEXO') {
    require([0, 1].every(axis => Math.min(...value.geometria.vertices_mm.map(p => p[axis])) === 0));
  }
}
function progress(data) {
  require(count(data.placed_units) && positiveId(data.total_units) && data.placed_units <= data.total_units);
  decimal(data.progress_pct);
  require(Math.abs(renderNumber(data.progress_pct) - data.placed_units / data.total_units * 100) < 1e-9);
}
function configuration(data) {
  require(object(data));
  for (const key of ['resolucion_raster_mm', 'margen_mm', 'separacion_mm', 'paso_angular_grados']) {
    decimal(data[key], key === 'resolucion_raster_mm' || key === 'paso_angular_grados');
  }
  require(renderNumber(data.paso_angular_grados) <= 360);
}
function metrics(data) {
  require(typeof data.metrics_available === 'boolean');
  if (!data.metrics_available) { require(data.metrics == null); return; }
  const value = data.metrics; require(object(value));
  for (const key of ['aprovechamiento_pct', 'merma_mm2', 'retazo_recuperable_mm2',
    'area_material_total_mm2', 'area_piezas_colocadas_mm2']) decimal(value[key], key === 'area_material_total_mm2');
  require(renderNumber(value.aprovechamiento_pct) <= 100 && count(value.planchas_nuevas_usadas)
    && count(value.tiempo_computacional_ms));
}

export function parseEvent(raw) {
  require(object(raw) && raw.schema_version === 1 && positiveId(raw.sequence) && positiveId(raw.id_optimizacion)
    && events.has(raw.event) && typeof raw.occurred_at === 'string'
    && /(Z|\+00:00)$/.test(raw.occurred_at) && Number.isFinite(Date.parse(raw.occurred_at)) && object(raw.data));
  const d = raw.data;
  switch (raw.event) {
    case 'optimization_started':
      require(d.metodo === 'FF' && positiveId(d.total_units) && Array.isArray(d.groups) && d.groups.length > 0);
      buildRunRequest(d.order_ids); d.groups.forEach(materialKey); configuration(d.configuracion); break;
    case 'group_started': materialKey(d); require(positiveId(d.total_units)); break;
    case 'piece_started': unit(d); progress(d); break;
    case 'piece_placed':
      placement(d); progress(d); material(d.material);
      require(d.placed_units > 0 && stockKey(d) === stockKey(d.material) && groupKey(d) === groupKey(d.material)); break;
    case 'group_completed': materialKey(d); progress(d); require(typeof d.result_url === 'string'); break;
    case 'metrics_calculated': metrics(d); break;
    case 'optimization_completed':
      progress(d); require(['COMPLETADA', 'SIN_SOLUCION'].includes(d.estado) && typeof d.result_url === 'string'
        && d.completo === (d.placed_units === d.total_units) && d.completo === (d.estado === 'COMPLETADA')); break;
    case 'optimization_failed':
      require(d.estado === 'FALLIDA' && ['CALCULATION_FAILED', 'EXECUTION_INTERRUPTED', 'RESULT_SAVE_FAILED', 'TIME_BUDGET_EXCEEDED'].includes(d.code)
        && typeof d.message === 'string' && typeof d.result_url === 'string'); break;
  }
  return structuredClone(raw);
}

export function parseRun(raw) {
  require(object(raw) && raw.schema_version === 1 && positiveId(raw.id_optimizacion) && raw.metodo === 'FF' && states.has(raw.estado));
  buildRunRequest(raw.order_ids); configuration(raw.configuracion); progress(raw); metrics(raw);
  require(raw.tiempo_computacional_ms == null || count(raw.tiempo_computacional_ms));
  if (raw.metrics_available) require(raw.metrics.tiempo_computacional_ms === raw.tiempo_computacional_ms);
  require(Array.isArray(raw.groups) && raw.groups.length > 0 && Array.isArray(raw.placements)
    && Array.isArray(raw.materials_used) && Array.isArray(raw.unplaced_units));
  const requested = new Map(); const groupKeys = new Set();
  raw.groups.forEach(g => {
    materialKey(g); require(!groupKeys.has(groupKey(g))); groupKeys.add(groupKey(g));
    require(Array.isArray(g.units) && g.units.length > 0);
    g.units.forEach(u => { unit(u); geometry(u.geometria); decimal(u.area_mm2, true);
      require(u.tipo_forma === u.geometria.type && groupKey(u) === groupKey(g) && raw.order_ids.includes(u.id_pedido)
        && !requested.has(unitKey(u))); requested.set(unitKey(u), u); });
  });
  require(requested.size === raw.total_units && new Set([...requested.values()].map(u => u.id_pedido)).size === raw.order_ids.length);
  const stocks = new Map(); raw.materials_used.forEach(s => { material(s); require(!stocks.has(stockKey(s))); stocks.set(stockKey(s), s); });
  const placed = new Set(), used = new Set();
  raw.placements.forEach(p => { placement(p); const u = requested.get(unitKey(p)), s = stocks.get(stockKey(p));
    require(u && s && !placed.has(unitKey(p)) && groupKey(p) === groupKey(u) && groupKey(p) === groupKey(s)
      && decimalKey(p.resolution_mm) === decimalKey(raw.configuracion.resolucion_raster_mm));
    placed.add(unitKey(p)); used.add(stockKey(p)); });
  const missing = new Set();
  raw.unplaced_units.forEach(u => { unit(u); require(requested.has(unitKey(u)) && !placed.has(unitKey(u)) && !missing.has(unitKey(u))
    && groupKey(u) === groupKey(requested.get(unitKey(u)))
    && u.reason === ({ EN_EJECUCION: 'PENDING', SIN_SOLUCION: 'NO_FIT', FALLIDA: 'INTERRUPTED', COMPLETADA: 'NO_FIT' })[raw.estado]); missing.add(unitKey(u)); });
  require(placed.size === raw.placed_units && missing.size + placed.size === requested.size && used.size === stocks.size
    && raw.completo === (raw.placed_units === raw.total_units) && typeof raw.confirmed === 'boolean' && typeof raw.confirmable === 'boolean'
    && (!raw.confirmed || raw.estado === 'COMPLETADA')
    && raw.confirmable === (raw.estado === 'COMPLETADA' && raw.completo && !raw.confirmed)
    && (raw.estado !== 'COMPLETADA' || raw.completo) && (raw.estado !== 'SIN_SOLUCION' || !raw.completo));
  require(!raw.metrics_available || stocks.size > 0);
  if (raw.residual_regions !== undefined) {
    require(Array.isArray(raw.residual_regions));
    raw.residual_regions.forEach(r => {
      const s = stocks.get(stockKey(r));
      require(s); decimal(r.x_mm); decimal(r.y_mm); decimal(r.width_mm, true); decimal(r.height_mm, true); decimal(r.area_mm2, true);
      const bounds = getGeometryBounds(s.geometria);
      require(bounds && renderNumber(r.x_mm) + renderNumber(r.width_mm) <= bounds.width + 1e-6
        && renderNumber(r.y_mm) + renderNumber(r.height_mm) <= bounds.height + 1e-6);
    });
  }
  return structuredClone(raw);
}

export function visualStock(dto) {
  const b = getGeometryBounds(dto.geometria);
  return { ...dto, geometry: dto.geometria, material_width_mm: b.width, material_height_mm: b.height };
}
export const visualPlacement = dto => ({ ...dto, group_id: groupKey(dto) });

export function resultSnapshot(dto) {
  const orders = dto.order_ids.map(id_pedido => ({ id_pedido, piezas: [] }));
  dto.groups.forEach(g => g.units.forEach(u => {
    const order = orders.find(o => o.id_pedido === u.id_pedido);
    const previous = order.piezas.find(p => p.id_pieza === u.id_pieza);
    if (previous) previous.cantidad = Math.max(previous.cantidad, u.unit_index);
    else order.piezas.push({ ...u, cantidad: u.unit_index });
  }));
  return { orders, total: dto.total_units, groups: dto.groups.map(g => ({
    id: groupKey(g), materialId: g.id_tipo_vidrio, name: `Material #${g.id_tipo_vidrio}`, thickness: g.espesor_mm,
    units: g.units, orders: [...new Set(g.units.map(u => u.id_pedido))],
    containers: dto.materials_used.filter(s => groupKey(s) === groupKey(g)).map(visualStock),
  })), rasters: {}, residuals: dto.residual_regions ?? [] };
}

export function parseConfirmation(raw, id) {
  require(object(raw) && raw.schema_version === 1 && raw.id_optimizacion === id && raw.confirmed === true
    && Array.isArray(raw.orders) && raw.orders.length > 0 && raw.orders.every(o => positiveId(o.id_pedido) && o.estado === 'CONFIRMADO')
    && Array.isArray(raw.materials_consumed) && raw.materials_consumed.length > 0 && Array.isArray(raw.remnants_created));
  const stockReference = value => require(object(value) && ['PLANCHA', 'RETAZO'].includes(value.material_source)
    && positiveId(value.material_id) && positiveId(value.stock_unit_index)
    && (value.material_source !== 'RETAZO' || value.stock_unit_index === 1));
  raw.materials_consumed.forEach(stockReference);
  require(new Set(raw.materials_consumed.map(stockKey)).size === raw.materials_consumed.length
    && new Set(raw.orders.map(o => o.id_pedido)).size === raw.orders.length);
  raw.remnants_created.forEach(r => {
    require(positiveId(r.id_retazo)); stockReference(r.source); decimal(r.x_mm); decimal(r.y_mm);
    geometry(r.geometria); require(r.geometria.type === 'RECTANGULO'); decimal(r.area_mm2, true);
  });
  return structuredClone(raw);
}

// No fetch or endpoint is selected here. Future transport is supplied by the caller.
export async function* readNdjson(chunks) {
  const decoder = new TextDecoder('utf-8', { fatal: true }); let buffer = '', terminal = false;
  const line = text => {
    const value = parseEvent(JSON.parse(text));
    require(!terminal); terminal = ['optimization_completed', 'optimization_failed'].includes(value.event);
    return value;
  };
  for await (const chunk of chunks) {
    buffer += decoder.decode(chunk, { stream: true }); require(buffer.length <= 1_048_576);
    let newline;
    while ((newline = buffer.indexOf('\n')) >= 0) {
      const text = buffer.slice(0, newline).trim(); buffer = buffer.slice(newline + 1);
      if (text) yield line(text);
    }
  }
  buffer += decoder.decode(); require(buffer.trim() === '' && terminal);
}
