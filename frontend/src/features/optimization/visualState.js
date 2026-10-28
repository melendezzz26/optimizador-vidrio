import { parseVisualEvent } from './visualContract.js';
import { unitKey, stockKey, decimalKey } from './runContract.js';

export const emptyVisual = () => ({ enabled: false, sequence: 0, preparation: null, current: null,
  descriptors: {}, processed: 0, evaluations: 0, manifestRevision: 0, error: '', config: null, order: [] });

export function applyVisualFact(state, raw) {
  const event = parseVisualEvent(raw), data = event.data;
  const current = state.visual ?? emptyVisual();
  if (event.id_optimizacion !== (state.optimizationId ?? event.id_optimizacion)
    || event.sequence !== current.sequence + 1) throw new Error('Se interrumpió el avance visual. Consulta el resultado.');
  const visual = { ...current, enabled: true, sequence: event.sequence };
  if (data.configuracion && state.config && Object.keys(state.config).some(key => decimalKey(state.config[key]) !== decimalKey(data.configuracion[key]))) throw new Error('La configuración cambió dentro de la corrida.');
  for (const mask of [data.mask, data.material_mask]) if (mask && state.config
    && decimalKey(mask.resolution_mm) !== decimalKey(state.config.resolucion_raster_mm)) throw new Error('La máscara utiliza otra resolución.');
  if (['orientation_testing', 'source_selected', 'piece_unplaced'].includes(event.event)
    && unitKey(current.order.at(-1) ?? {}) !== unitKey(data)) throw new Error('El detalle corresponde a otra unidad.');
  if (event.event === 'source_selected' && (data.placed_units !== state.placements.length + 1
    || data.processed_units !== current.processed + 1 || state.method === 'FF' && data.score !== null)) throw new Error('Selección visual incoherente.');
  if (event.event === 'piece_unplaced' && (data.placed_units !== state.placements.length
    || data.processed_units !== current.processed + 1)) throw new Error('Pieza faltante incoherente.');
  if (event.event === 'piece_placed') {
    const selected = current.current;
    if (selected?.kind !== 'source_selected' || unitKey(selected) !== unitKey(data)
      || stockKey(selected.source) !== stockKey(data) || decimalKey(selected.mask.rotation_deg) !== decimalKey(data.rotation_deg)
      || decimalKey(selected.mask.resolution_mm) !== decimalKey(data.resolution_mm)) throw new Error('La máscara y la colocación no corresponden.');
  }
  if (data.processed_units !== undefined) {
    if (data.processed_units < current.processed || data.total_units !== state.total_units) throw new Error('El progreso visual no corresponde al trabajo.');
    visual.processed = data.processed_units;
  }
  if (event.event === 'optimization_started' || event.event === 'preparation_started') visual.config = data.configuracion;
  if (event.event === 'preparation_started') visual.preparation = 'running';
  if (event.event === 'preparation_completed') visual.preparation = 'complete';
  if (event.event === 'piece_rasterizing') visual.current = { ...data, kind: event.event };
  if (event.event === 'piece_started') {
    if (current.order.some(unit => unitKey(unit) === unitKey(data)) || current.order.length >= 150) throw new Error('Orden de piezas duplicado o fuera del presupuesto.');
    visual.order = [...current.order, { id_pedido: data.id_pedido, id_pieza: data.id_pieza, unit_index: data.unit_index }];
    visual.current = { ...data, kind: event.event };
  }
  if (['piece_ready', 'orientation_testing', 'source_selected'].includes(event.event)) {
    visual.current = { ...data, kind: event.event };
    const descriptors = { ...current.descriptors };
    for (const value of [data.mask, data.material_mask]) if (value?.available && !descriptors[value.mask_ref]) descriptors[value.mask_ref] = value;
    if (Object.keys(descriptors).length > 1024) throw new Error('El detalle visual excedió su presupuesto.');
    visual.descriptors = descriptors;
  }
  if (event.event === 'orientation_testing') {
    if (data.evaluation_index <= current.evaluations) throw new Error('Evaluación visual fuera de orden.');
    visual.evaluations = data.evaluation_index;
  }
  if (event.event === 'piece_unplaced') {
    visual.current = { ...data, kind: event.event };
    if ((state.unplaced_units ?? []).some(unit => unitKey(unit) === unitKey(data))) throw new Error('Pieza faltante duplicada.');
  }
  return { event, visual };
}
