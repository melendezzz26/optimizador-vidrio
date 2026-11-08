// TA-043/B01: opt-in contracts only. No transport, UI or v1 defaults are changed.
import { RunContractError, parseRun, decimalKey } from './runContract.js';
import { parseMaskDescriptor, parseVisualEvent } from './visualContract.js';

export const CATALOG_V2 = Object.freeze([
  ['FF', 'FF', 'First Fit', 'PLACEMENT_FACTS', true, null],
  ['BF', 'BF', 'Best Fit', 'PLACEMENT_FACTS', true, null],
  ['WF', 'WF', 'Worst Fit', 'PLACEMENT_FACTS', true, null],
  ['HF', 'HF', 'Hole Filling', 'CHOSEN_SOLUTION_REPLAY', true, null],
  ['M5', 'BRF', 'Best Residual Fit', 'PLACEMENT_FACTS', true, null],
  ['M6-BS', 'BS-2', 'Beam Search acotada', 'SEARCH_PROGRESS', false, 2],
].map(([code, label, name, observation, native_visual, beam_width]) => Object.freeze({
  code, label, name, observation, native_visual, checkpoint: true, beam_width,
})));
export const METHODS_V2 = Object.freeze(CATALOG_V2.map(m => m.code));
const METHODS_V1 = Object.freeze(METHODS_V2.slice(0, 3));
const check = value => { if (!value) throw new RunContractError(); };
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const count = value => Number.isSafeInteger(value) && value >= 0;
const id = value => Number.isSafeInteger(value) && value > 0 && value <= 2147483647;
const bool = value => typeof value === 'boolean';
const keys = (data, allowed) => check(object(data) && Object.keys(data).every(k => allowed.includes(k)));
const profile = data => check(object(data) && data.profile === 'comparison-v2' && data.schema_version === 2);
const beamReasons = ['EXPANSION_LIMIT', 'GEOMETRY_PROBE_LIMIT', 'STATE_MEMORY_LIMIT', 'TIME_LIMIT'];
const engineReasons = ['COMPLETED', 'NO_FIT', ...beamReasons];
const supervisorReasons = ['GLOBAL_TIME_LIMIT', 'TIME_BUDGET_EXCEEDED', 'MEMORY_BUDGET_EXCEEDED',
  'EXECUTION_FAILED', 'RESULT_SAVE_FAILED', 'WORKER_STOPPED', 'PROCESS_START_FAILED', 'CANCELLED'];

export function validateMethods(methods, { profile: selectedProfile = 'comparison-v2', requireAll = false } = {}) {
  const allowed = { 'comparison-v1': METHODS_V1, 'comparison-v2': METHODS_V2 }[selectedProfile];
  check(allowed && Array.isArray(methods) && methods.length > 0
    && methods.every(m => typeof m === 'string' && allowed.includes(m)) && new Set(methods).size === methods.length);
  if (requireAll) check(methods.length === allowed.length && allowed.every(m => methods.includes(m)));
  return [...methods];
}

function diagnostic(data, method) {
  keys(data, ['origin', 'termination_reason', 'statistics']);
  check(({ ENGINE: engineReasons, SUPERVISOR: supervisorReasons }[data.origin] || []).includes(data.termination_reason)
    && object(data.statistics) && Object.entries(data.statistics).every(([k, v]) => k.length > 0 && count(v))
    && (!beamReasons.includes(data.termination_reason) || method === 'M6-BS'));
}

function sameMetrics(a, b) {
  if (a === null || b === null) return a === b;
  const names = ['aprovechamiento_pct', 'merma_mm2', 'planchas_nuevas_usadas', 'retazo_recuperable_mm2',
    'area_material_total_mm2', 'area_piezas_colocadas_mm2', 'tiempo_computacional_ms'];
  return object(a) && object(b) && names.every(k => decimalKey(a[k]) === decimalKey(b[k]));
}

export function parseExecutionSummaryV2(e) {
  keys(e, ['execution_id', 'method', 'status', 'dispatch_state', 'outcome', 'result_available', 'complete',
    'eligible', 'placed_units', 'total_units', 'metrics', 'computation_time_ms', 'diagnostic']);
  validateMethods([e.method]);
  check(id(e.execution_id) && ['EN_EJECUCION', 'COMPLETADA', 'FALLIDA'].includes(e.status)
    && ['QUEUED', 'STARTING', 'RUNNING', 'TERMINATED'].includes(e.dispatch_state)
    && [e.result_available, e.complete, e.eligible].every(bool) && count(e.placed_units)
    && id(e.total_units) && e.placed_units <= e.total_units
    && (e.computation_time_ms === null || count(e.computation_time_ms)));
  const terminal = e.dispatch_state === 'TERMINATED';
  check(terminal === (e.status !== 'EN_EJECUCION'));
  if (!terminal) check(e.outcome === null && e.diagnostic === null && !e.result_available
    && !e.complete && !e.eligible && e.metrics === null);
  else {
    diagnostic(e.diagnostic, e.method);
    if (e.status === 'FALLIDA') check(e.outcome === 'FAILED' && !e.result_available && !e.complete
      && !e.eligible && e.placed_units === 0 && e.metrics === null
      && !['COMPLETED', 'NO_FIT'].includes(e.diagnostic.termination_reason));
    else check(e.result_available && e.outcome === (e.complete ? 'COMPLETE' : 'PARTIAL')
      && e.complete === (e.placed_units === e.total_units) && (!e.eligible || e.complete)
      && e.diagnostic.origin === 'ENGINE' && (e.diagnostic.termination_reason === 'COMPLETED') === e.complete);
  }
  if (e.metrics !== null) {
    const m = e.metrics;
    keys(m, ['aprovechamiento_pct', 'merma_mm2', 'planchas_nuevas_usadas', 'retazo_recuperable_mm2',
      'area_material_total_mm2', 'area_piezas_colocadas_mm2', 'tiempo_computacional_ms']);
    check(e.placed_units > 0 && m.tiempo_computacional_ms === e.computation_time_ms
      && count(m.tiempo_computacional_ms) && count(m.planchas_nuevas_usadas));
    for (const k of ['aprovechamiento_pct', 'merma_mm2', 'retazo_recuperable_mm2', 'area_material_total_mm2', 'area_piezas_colocadas_mm2']) {
      check(typeof m[k] === 'string' && decimalKey(m[k])[0] !== '-');
    }
    check(Number(m.aprovechamiento_pct) <= 100 && Number(m.area_material_total_mm2) > 0
      && Number(m.area_piezas_colocadas_mm2) <= Number(m.area_material_total_mm2));
  }
  return structuredClone(e);
}

export function parseComparisonV2(data) {
  profile(data);
  check(id(data.comparison_id) && id(data.version) && typeof data.input_sha256 === 'string'
    && /^[a-f0-9]{64}$/.test(data.input_sha256) && Array.isArray(data.methods)
    && data.methods.length === METHODS_V2.length && data.methods.every((m, i) => m === METHODS_V2[i])
    && Array.isArray(data.order_ids) && data.order_ids.length > 0 && data.order_ids.every(id)
    && new Set(data.order_ids).size === data.order_ids.length && Array.isArray(data.requested_pieces)
    && id(data.configuration_id) && id(data.configuration_version)
    && Array.isArray(data.executions) && data.executions.length === METHODS_V2.length);
  for (const [name, positive] of [['resolucion_raster_mm', true], ['margen_mm', false],
    ['separacion_mm', false], ['paso_angular_grados', true]]) {
    const value = data.configuration?.[name];
    check(typeof value === 'string' && decimalKey(value)[0] !== '-' && (!positive || decimalKey(value) !== '0'));
  }
  check(Number(data.configuration.paso_angular_grados) <= 360);
  data.executions.forEach(parseExecutionSummaryV2);
  validateMethods(data.executions.map(e => e.method), { requireAll: true });
  check(new Set(data.executions.map(e => e.execution_id)).size === data.executions.length
    && [data.terminal, data.incomplete, data.supervisor_stopped, data.released, data.confirmed,
      data.selection_allowed, data.confirmable].every(bool));
  const terminal = data.supervisor_stopped && data.executions.every(e => e.dispatch_state === 'TERMINATED');
  check(data.terminal === terminal);
  const status = !terminal ? 'EN_EJECUCION' : data.executions.some(e => e.complete) ? 'COMPLETADA'
    : data.executions.some(e => e.status === 'FALLIDA') ? 'FALLIDA' : 'SIN_SOLUCION';
  check(data.status === status);
  const editable = terminal && !data.released && !data.confirmed;
  for (const e of data.executions) check(e.eligible === (editable && e.complete && e.result_available));
  const selected = data.executions.find(e => e.execution_id === data.selected_execution_id);
  check(data.selected_execution_id === null || selected && terminal && !data.released && selected.complete && selected.result_available);
  check(data.selection_allowed === (editable && data.executions.some(e => e.eligible))
    && data.confirmable === (editable && Boolean(selected))
    && data.incomplete === data.executions.some(e => ['PARTIAL', 'FAILED'].includes(e.outcome))
    && data.confirmed === (data.confirmation !== null));
  if (data.confirmed) check(selected && data.confirmation.execution_id === selected.execution_id && data.confirmation.method === selected.method);
  return structuredClone(data);
}

export function parseExecutionV2(data, comparison, expected) {
  profile(data);
  const e = parseExecutionSummaryV2(data.execution);
  check(data.comparison_id === comparison.comparison_id
    && comparison.executions.some(v => v.execution_id === e.execution_id && v.method === e.method)
    && (!expected || expected.execution_id === e.execution_id && expected.method === e.method)
    && e.result_available === (data.result !== null));
  if (data.result !== null) {
    const r = data.result;
    check(r.schema_version === 2 && ['COMPLETADA', 'SIN_SOLUCION'].includes(r.estado)
      && r.metodo === e.method && r.id_optimizacion === data.comparison_id
      && r.termination_reason === e.diagnostic.termination_reason && r.completo === e.complete
      && r.placed_units === e.placed_units && r.total_units === e.total_units
      && r.tiempo_computacional_ms === e.computation_time_ms && sameMetrics(r.metrics, e.metrics)
      && ['COMPLETED', 'NO_FIT', ...(e.method === 'M6-BS' ? beamReasons : [])].includes(r.termination_reason));
    const reason = r.termination_reason === 'NO_FIT' ? 'NO_FIT' : 'RESOURCE_LIMIT';
    check(Array.isArray(r.unplaced_units) && r.unplaced_units.every(u => u.reason === reason));
    // Reuse legacy geometry/R4 validation on a view; preserve the actual V2 reasons.
    parseRun({ ...r, schema_version: 1, confirmed: false, confirmable: r.estado === 'COMPLETADA' && r.completo,
      unplaced_units: r.unplaced_units.map(u => ({ ...u, reason: 'NO_FIT' })) }, { methods: METHODS_V2 });
  }
  return structuredClone(data);
}

export function parseComparisonEventV2(data, comparison) {
  profile(data);
  const globals = ['comparison_accepted', 'comparison_finished', 'heartbeat', 'snapshot_required'];
  const facts = ['group_started', 'piece_started', 'piece_placed', 'group_completed', 'preparation_started',
    'piece_rasterizing', 'piece_ready', 'preparation_completed', 'orientation_testing', 'source_selected', 'piece_unplaced'];
  check(data.comparison_id === comparison.comparison_id && id(data.sequence) && object(data.data)
    && typeof data.timestamp === 'string' && /(Z|\+00:00)$/.test(data.timestamp) && Number.isFinite(Date.parse(data.timestamp))
    && [...globals, ...facts, 'engine_ready', 'engine_started', 'ordering_ready', 'execution_state',
      'result_persisted', 'execution_failed', 'search_progress'].includes(data.event));
  const d = data.data;
  if (globals.includes(data.event)) check([data.execution_id, data.method, data.execution_sequence, data.presentation].every(v => v === null));
  else {
    check(comparison.executions.some(e => e.execution_id === data.execution_id && e.method === data.method)
      && id(data.execution_sequence) && ['OBSERVED', 'PROVISIONAL', 'FINAL_REPLAY'].includes(data.presentation));
    if (data.event === 'search_progress') {
      check(data.method === 'M6-BS' && data.presentation === 'PROVISIONAL');
      keys(d, ['completed_levels', 'processed_units', 'total_units', 'expansions', 'geometry_probes', 'frontier_size']);
      check(['completed_levels', 'processed_units', 'expansions', 'geometry_probes'].every(k => count(d[k]))
        && id(d.total_units) && id(d.frontier_size) && d.processed_units <= d.total_units);
    } else check(data.presentation !== 'PROVISIONAL');
    if (data.method === 'M6-BS' && ['piece_started', 'piece_placed', 'piece_unplaced', 'source_selected', 'orientation_testing'].includes(data.event)) {
      check(data.presentation === 'FINAL_REPLAY');
    }
    for (const mask of [d.mask, d.material_mask]) if (mask !== undefined) {
      profile(mask); parseMaskDescriptor(mask, data.comparison_id);
      check(mask.comparison_id === data.comparison_id && mask.execution_id === data.execution_id && mask.method === data.method);
    }
    if (data.event === 'preparation_started') check(d.metodo === data.method);
    if (facts.includes(data.event)) parseVisualEvent({ schema_version: 2, id_optimizacion: data.comparison_id,
      sequence: data.sequence, occurred_at: data.timestamp, event: data.event, data: d }, { methods: METHODS_V2 });
    if (['execution_state', 'result_persisted', 'execution_failed'].includes(data.event)) {
      parseExecutionSummaryV2(d);
      check(d.execution_id === data.execution_id && d.method === data.method
        && (data.event !== 'result_persisted' || d.result_available)
        && (data.event !== 'execution_failed' || d.outcome === 'FAILED'));
    }
    if (data.event === 'ordering_ready') check(d.criterion === 'area_desc_max_side_desc_order_piece_unit_asc'
      && Array.isArray(d.units) && d.units.length > 0 && d.units.length <= 800
      && d.units.every(u => id(u.id_pedido) && id(u.id_pieza) && id(u.unit_index) && id(u.id_tipo_vidrio) && typeof u.espesor_mm === 'string'));
  }
  if (['engine_ready', 'engine_started', 'heartbeat'].includes(data.event)) keys(d, []);
  if (data.event === 'comparison_accepted') {
    check(id(d.version) && Array.isArray(d.methods) && d.methods.length === METHODS_V2.length && d.methods.every((m, i) => m === METHODS_V2[i])
      && Array.isArray(d.executions) && d.executions.length === METHODS_V2.length && d.executions.every(e => id(e.execution_id))
      && new Set(d.executions.map(e => e.execution_id)).size === METHODS_V2.length);
    validateMethods(d.executions.map(e => e.method), { requireAll: true });
    check(d.executions.every(e => comparison.executions.some(v => v.execution_id === e.execution_id && v.method === e.method)));
  }
  if (data.event === 'comparison_finished') check(id(d.version) && ['COMPLETADA', 'SIN_SOLUCION', 'FALLIDA'].includes(d.status)
    && bool(d.incomplete) && d.supervisor_stopped === true);
  if (data.event === 'snapshot_required') check(count(d.latest_sequence));
  return structuredClone(data);
}
