// Opt-in visual contract. The frozen V1 parser/reducer continue on their own path.
import { decimalKey, parseEvent, RunContractError } from './runContract.js';
import { getGeometryBounds } from './visualizationGeometry.js';

const check = value => { if (!value) throw new RunContractError(); };
const object = value => value && typeof value === 'object' && !Array.isArray(value);
const count = value => Number.isSafeInteger(value) && value >= 0;
const id = value => Number.isSafeInteger(value) && value > 0;
const number = value => typeof value === 'string' && Number.isFinite(Number(value));
const maskRef = value => typeof value === 'string' && /^[a-f0-9]{32}$/.test(value);
const baseEvents = new Set(['optimization_started', 'group_started', 'piece_started', 'piece_placed',
  'group_completed', 'metrics_calculated', 'optimization_completed', 'optimization_failed']);
const newEvents = new Set(['preparation_started', 'piece_rasterizing', 'piece_ready',
  'preparation_completed', 'orientation_testing', 'source_selected', 'piece_unplaced']);
const unit = data => check(id(data.id_pedido) && id(data.id_pieza) && id(data.unit_index)
  && id(data.id_tipo_vidrio) && number(data.espesor_mm) && Number(data.espesor_mm) > 0);
const source = data => check(object(data) && ['PLANCHA', 'RETAZO'].includes(data.material_source)
  && id(data.material_id) && id(data.stock_unit_index) && (data.material_source !== 'RETAZO' || data.stock_unit_index === 1));
const progress = data => {
  check(count(data.placed_units) && id(data.total_units) && count(data.processed_units)
    && data.placed_units <= data.processed_units && data.processed_units <= data.total_units
    && number(data.progress_pct) && Math.abs(Number(data.progress_pct) - data.placed_units / data.total_units * 100) < 1e-9);
};

export function parseMaskDescriptor(data, runId) {
  check(object(data) && id(data.id_optimizacion) && data.id_optimizacion === runId
    && typeof data.available === 'boolean' && data.available === maskRef(data.mask_ref)
    && (data.available ? data.reason === null : data.mask_ref === null && data.reason === 'VISUAL_BUDGET_EXCEEDED')
    && ['PIECE', 'MATERIAL'].includes(data.kind) && number(data.resolution_mm) && Number(data.resolution_mm) > 0
    && number(data.rotation_deg) && Number(data.rotation_deg) >= 0 && Number(data.rotation_deg) < 360
    && id(data.columns) && data.columns <= 4000 && id(data.row_count) && data.row_count <= 4000
    && count(data.occupied_cells) && data.occupied_cells <= data.columns * data.row_count);
  if (data.kind === 'PIECE') check(object(data.piece) && id(data.piece.id_pedido) && id(data.piece.id_pieza) && data.source === null);
  else { source(data.source); check(data.piece === null); }
  return structuredClone(data);
}

export function parseVisualEvent(raw) {
  check(object(raw) && raw.schema_version === 2 && id(raw.id_optimizacion) && id(raw.sequence)
    && typeof raw.occurred_at === 'string' && /(Z|\+00:00)$/.test(raw.occurred_at)
    && Number.isFinite(Date.parse(raw.occurred_at)) && object(raw.data));
  const d = raw.data;
  if (baseEvents.has(raw.event)) {
    parseEvent({ ...raw, schema_version: 1 });
    if (['piece_started', 'piece_placed', 'optimization_completed'].includes(raw.event)) progress(d);
    if (raw.event === 'optimization_completed') check(d.processed_units === d.total_units);
    if (raw.event === 'optimization_started') {
      const v = d.visual;
      check(object(v) && v.profile === 'visual-v2' && v.representative_orientations === true
        && v.max_extra_samples === 128 && v.max_extra_samples_per_second === 10
        && v.retention_max_seconds === 300 && v.retention_may_end_earlier === true);
    }
  } else {
    check(newEvents.has(raw.event));
    if (raw.event.startsWith('preparation_')) {
      check(id(d.unique_pieces) && count(d.material_bases) && id(d.total_units));
      if (raw.event === 'preparation_started') {
        check(d.metodo === 'FF' && object(d.configuracion));
        for (const key of ['resolucion_raster_mm', 'margen_mm', 'separacion_mm', 'paso_angular_grados']) {
          check(number(d.configuracion[key]) && Number(d.configuracion[key]) >= 0);
        }
        check(Number(d.configuracion.resolucion_raster_mm) > 0 && Number(d.configuracion.paso_angular_grados) > 0 && Number(d.configuracion.paso_angular_grados) <= 360);
      }
    } else if (['piece_ready', 'piece_rasterizing'].includes(raw.event)) {
      check(id(d.id_pedido) && id(d.id_pieza) && id(d.id_tipo_vidrio) && number(d.espesor_mm)
        && Number(d.espesor_mm) > 0 && id(d.cantidad));
    } else { unit(d); progress(d); }
    if (d.mask !== undefined) {
      parseMaskDescriptor(d.mask, raw.id_optimizacion);
      check(d.mask.kind === 'PIECE' && d.mask.piece.id_pedido === d.id_pedido && d.mask.piece.id_pieza === d.id_pieza);
    }
    if (raw.event === 'piece_ready') check(d.mask !== undefined);
    if (raw.event === 'orientation_testing') {
      source(d.source); check(id(d.evaluation_index) && d.sampled === true && d.mask !== undefined);
    } else if (raw.event === 'source_selected') {
      source(d.source); check(d.mask !== undefined);
      parseMaskDescriptor(d.material_mask, raw.id_optimizacion);
      check(d.material_mask.kind === 'MATERIAL' && ['material_source', 'material_id', 'stock_unit_index'].every(key => d.source[key] === d.material_mask.source[key]));
      check(d.score === null ? d.score_name === null : count(d.score) && d.score_name === 'remaining_free_cells_after_placement');
    } else if (raw.event === 'piece_unplaced') check(d.reason === 'NO_FIT');
  }
  return structuredClone(raw);
}

export async function* readVisualNdjson(chunks) {
  const decoder = new TextDecoder('utf-8', { fatal: true });
  const encoder = new TextEncoder();
  let buffer = '', runId = null, sequence = 0, terminal = false;
  for await (const chunk of chunks) {
    // Bound retained text even if a transport delivers many events in one chunk.
    for (let offset = 0; offset < chunk.length; offset += 4096) {
      buffer += decoder.decode(chunk.subarray(offset, offset + 4096), { stream: true });
      let newline;
      while ((newline = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, newline); buffer = buffer.slice(newline + 1);
        check(!terminal && line.trim() !== '' && encoder.encode(line + '\n').length <= 65536);
        const value = parseVisualEvent(JSON.parse(line));
        if (runId === null) { check(value.event === 'optimization_started'); runId = value.id_optimizacion; }
        check(value.id_optimizacion === runId && value.sequence === ++sequence);
        terminal = ['optimization_completed', 'optimization_failed'].includes(value.event);
        yield value;
      }
      check(encoder.encode(buffer).length <= 65536);
    }
  }
  buffer += decoder.decode();
  check(buffer === '' && terminal);
}

export function parseVisualManifest(raw, runId) {
  check(object(raw) && raw.schema_version === 2 && raw.id_optimizacion === runId && count(raw.revision)
    && Array.isArray(raw.items) && raw.items.length <= 64 && raw.revision >= raw.items.length
    && (raw.next_offset === null || count(raw.next_offset) && raw.next_offset <= raw.revision));
  const refs = new Set();
  raw.items.forEach(item => {
    parseMaskDescriptor(item, runId); check(item.available && !refs.has(item.mask_ref)); refs.add(item.mask_ref);
  });
  return structuredClone(raw);
}

export function parseVisualMask(raw, runId, expected) {
  parseMaskDescriptor(raw, runId);
  check(raw.schema_version === 2 && raw.available && raw.mask_ref === expected.mask_ref
    && decimalKey(raw.resolution_mm) === decimalKey(expected.resolution_mm)
    && decimalKey(raw.rotation_deg) === decimalKey(expected.rotation_deg)
    && raw.kind === expected.kind && JSON.stringify(raw.piece) === JSON.stringify(expected.piece)
    && JSON.stringify(raw.source) === JSON.stringify(expected.source)
    && getGeometryBounds(raw.geometria) && getGeometryBounds(raw.geometria_original));
  const w = raw.window;
  check(object(w) && count(w.row_start) && count(w.column_start) && id(w.row_count) && w.row_count <= 256
    && id(w.column_count) && w.column_count <= 1024 && w.row_start + w.row_count <= raw.row_count
    && w.column_start + w.column_count <= raw.columns && Array.isArray(raw.spans_by_row) && raw.spans_by_row.length === w.row_count);
  raw.spans_by_row.forEach((row, index) => {
    check(row.row === w.row_start + index && Array.isArray(row.runs));
    let previous = w.column_start;
    row.runs.forEach(run => {
      check(Array.isArray(run) && run.length === 2 && run.every(count) && previous <= run[0]
        && run[0] < run[1] && run[1] <= w.column_start + w.column_count); previous = run[1];
    });
  });
  return structuredClone(raw);
}
