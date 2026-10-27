import { placementMatchesGroup } from './materialGroups.js';
import { groupKey, parseEvent, parseRun, resultSnapshot, stockKey, unitKey, visualPlacement, visualStock } from './runContract.js';
export const STAGES = [
  ['preparing_orders', 'Preparando pedidos'], ['grouping_materials', 'Agrupando por material y espesor'],
  ['rasterizing', 'Preparando formas de corte'], ['sorting_pieces', 'Ordenando piezas'],
  ['first_fit', 'Calculando distribución'], ['evaluating_rotations', 'Evaluando rotaciones'], ['calculating_metrics', 'Calculando aprovechamiento'],
  ['completed', 'Distribución lista'],
];
export const initialOptimization = {
  status: 'loading_orders', orders: [], selected: [], connection: 'loading', orderError: '',
  snapshot: null, placements: [], completedGroups: [], metrics: null, error: '', runId: null, stage: null,
  optimizationId: null, sequence: 0, estado: null, placed_units: 0, total_units: 0, progress_pct: '0',
  completo: false, metrics_available: false, confirmable: false, confirmed: false, resultUrl: null,
  errorKind: null, retryAfter: null,
};
export const placementKey = unitKey;
export const containerKey = stockKey;
export const pieceCount = orders => orders.reduce((sum, order) => sum + (order.piezas ?? []).reduce((n, p) => n + p.cantidad, 0), 0);
const runStatus = state => ({ EN_EJECUCION: 'running', COMPLETADA: 'completed', SIN_SOLUCION: 'no_solution', FALLIDA: 'failed' })[state];

function loadedSnapshot(dto, previous) {
  const snapshot = resultSnapshot(dto);
  if (!previous) return snapshot;
  return { ...snapshot, fixture: previous.fixture, rasters: previous.rasters,
    orders: snapshot.orders.map(o => ({ ...previous.orders.find(old => old.id_pedido === o.id_pedido), ...o })),
    groups: snapshot.groups.map(g => {
      const old = previous.groups.find(old => old.id === g.id);
      return { ...g, name: old?.name ?? g.name, containers: [...g.containers,
        ...(old?.containers ?? []).filter(c => !g.containers.some(n => stockKey(n) === stockKey(c)))] };
    }) };
}
export function optimizationReducer(state, action) {
  try { return withErrorKind(state, reduce(state, action), action); }
  catch (error) { return { ...state, status: 'failed', error: error.message, confirmable: false, errorKind: null, retryAfter: null }; }
}

// TA-037: only these actions classify their error; any other new error is generic.
const CLASSIFIED = new Set(['connection_failed', 'event']);
function withErrorKind(previous, next, action) {
  if (next.error && (next.error === previous.error || CLASSIFIED.has(action.type))) return next;
  return next.errorKind || next.retryAfter ? { ...next, errorKind: null, retryAfter: null } : next;
}

const ERROR_KINDS = { LOAD_LIMIT_EXCEEDED: 'load_limit', OPTIMIZER_BUSY: 'busy', TIME_BUDGET_EXCEEDED: 'time_budget' };

// TA-037 T04: what the person can do after an operational limit (SPEC §7).
// "load_limit" and "time_budget" ask for a smaller batch; "busy" asks to retry later.
export function runErrorFeedback({ error, errorKind, retryAfter }) {
  if (!error) return null;
  if (errorKind === 'load_limit') return { kind: errorKind, variant: 'error', message: error,
    title: 'El trabajo es demasiado grande para un solo cálculo',
    hint: 'Los pedidos siguen pendientes y no se usó inventario. Ajusta la selección y vuelve a revisar vidrios y piezas.' };
  if (errorKind === 'busy') return { kind: errorKind, variant: 'warning', message: error,
    title: 'El optimizador está ocupado',
    hint: `Los pedidos siguen pendientes. Vuelve a presionar «Calcular distribución» en ${retryAfter ?? 15} segundos.` };
  if (errorKind === 'time_budget') return { kind: errorKind, variant: 'error', message: error,
    title: 'El cálculo superó el tiempo máximo',
    hint: 'No se consumió inventario. Consulta el resultado; los pedidos de este trabajo requieren revisión antes de volver a calcularse.' };
  return { kind: null, variant: 'error', message: error, title: undefined, hint: null };
}
function reduce(state, action) {
  switch (action.type) {
    case 'accepted': return state.status === 'running' && action.runId === state.runId
      ? { ...state, optimizationId: action.optimizationId } : state;
    case 'loading_result': return { ...initialOptimization, orders: state.orders, connection: state.connection, status: 'loading_result' };
    case 'orders_received': {
      const orders = action.orders.filter(o => o.estado === 'PENDIENTE');
      const selected = state.selected.filter(id => orders.some(o => o.id_pedido === id));
      const invalidated = state.status === 'prepared' && selected.length !== state.selected.length;
      return { ...state, orders, selected, connection: 'connected', orderError: '',
        status: state.status === 'loading_orders' || invalidated ? 'selection_ready' : state.status,
        snapshot: invalidated ? null : state.snapshot };
    }
    case 'orders_failed': return { ...state, connection: 'error', orderError: action.message,
      status: state.status === 'loading_orders' ? 'selection_ready' : state.status };
    case 'select':
      if (['running', 'preparing'].includes(state.status)) return state;
      return { ...initialOptimization, orders: state.orders, connection: state.connection,
        selected: action.ids.filter(id => state.orders.some(o => o.id_pedido === id)), status: 'selection_ready' };
    case 'preparing': return { ...state, status: 'preparing', error: '', snapshot: null, placements: [], metrics: null, runId: null, stage: null, completedGroups: [], confirmable: false, confirmed: false };
    case 'prepared': {
      if (state.status !== 'preparing') return state;
      if (!action.snapshot.orders.every(o => state.selected.includes(o.id_pedido))) {
        return { ...state, status: 'selection_ready', error: 'La selección cambió. Prepara nuevamente los pedidos pendientes.' };
      }
      return { ...state, status: 'prepared', snapshot: structuredClone(action.snapshot) };
    }
    case 'prepare_failed': return { ...state, status: 'selection_ready', error: action.message };
    case 'run':
      if (!state.snapshot) return state;
      return { ...state, status: 'running', runId: action.runId, placements: [], metrics: null, optimizationId: null, sequence: 0,
        estado: 'EN_EJECUCION', placed_units: 0, total_units: state.snapshot.total, progress_pct: '0', completo: false,
        metrics_available: false, confirmable: false, confirmed: false, resultUrl: null,
        completedGroups: [], stage: 'preparing_orders', error: '', availableAtStart: state.orders.map(o => o.id_pedido) };
    case 'discard': return { ...initialOptimization, orders: state.orders, selected: state.selected, connection: state.connection, status: 'selection_ready' };
    case 'connection_failed': {
      // A rejected POST has not created a run. Keep the reviewed work and allow
      // an explicit retry; do not report server execution or leave progress active.
      if (action.rejected && !state.optimizationId && state.sequence === 0) return {
        ...state, status: 'prepared', error: action.message, runId: null, estado: null,
        stage: null, placed_units: 0, progress_pct: '0', confirmable: false,
        errorKind: ERROR_KINDS[action.code] ?? null, retryAfter: action.retryAfter ?? null,
      };
      return { ...state, status: 'failed', stage: null, error: action.message, confirmable: false, errorKind: null, retryAfter: null };
    }
    case 'result_error': return { ...state, status: state.status === 'loading_result' ? 'failed' : state.status, error: action.message, confirmable: false };
    case 'confirmed': return { ...state, confirmed: true, confirmable: false };
    case 'result': {
      if (action.runId && action.runId !== state.runId) return state;
      const dto = parseRun(action.result);
      if (state.optimizationId && dto.id_optimizacion !== state.optimizationId) throw new Error('El resultado pertenece a otra ejecución.');
      return { ...state, status: runStatus(dto.estado), estado: dto.estado, optimizationId: dto.id_optimizacion,
        snapshot: loadedSnapshot(dto, state.snapshot), placements: dto.placements.map(visualPlacement),
        completedGroups: dto.estado === 'EN_EJECUCION' ? [] : dto.groups.map(groupKey),
        placed_units: dto.placed_units, total_units: dto.total_units, progress_pct: dto.progress_pct,
        completo: dto.completo, metrics_available: dto.metrics_available, metrics: dto.metrics ?? null,
        confirmable: dto.confirmable, confirmed: dto.confirmed,
        error: dto.estado === 'FALLIDA' ? state.error || 'No se pudo calcular el corte. Consulta el resultado antes de preparar otro trabajo.' : '',
        stage: dto.estado === 'COMPLETADA' ? 'completed' : state.stage };
    }
    case 'event': {
      if (state.status !== 'running' || action.runId !== state.runId) return state;
      const event = parseEvent(action.event), data = event.data;
      if (state.optimizationId && event.id_optimizacion !== state.optimizationId) throw new Error('Evento de otra ejecución.');
      if (event.sequence <= state.sequence) return state;
      if (event.sequence !== state.sequence + 1) throw new Error('Se interrumpió la secuencia. Recupera el resultado antes de continuar.');
      const next = { ...state, optimizationId: event.id_optimizacion, sequence: event.sequence };
      switch (event.event) {
        case 'optimization_started': {
          if (data.total_units !== state.snapshot.total || JSON.stringify([...data.order_ids].sort()) !== JSON.stringify(state.snapshot.orders.map(o => o.id_pedido).sort())) throw new Error('La selección cambió en el servidor. Recupera el resultado.');
          return { ...next, total_units: data.total_units };
        }
        case 'group_started': return { ...next, activeGroup: groupKey(data), stage: 'first_fit' };
        case 'piece_started': return { ...next, activePiece: data.id_pieza };
        case 'piece_placed': {
          const placement = visualPlacement(data);
          if (state.placements.some(p => placementKey(p) === placementKey(placement))) throw new Error('Unidad duplicada en la ejecución.');
          const snapshot = { ...state.snapshot, groups: state.snapshot.groups.map(g => g.id !== placement.group_id ? g : {
            ...g, containers: [...g.containers.filter(c => containerKey(c) !== containerKey(data.material)), visualStock(data.material)],
          }) };
          if (!placementMatchesGroup(snapshot, placement) || data.placed_units !== state.placements.length + 1 || data.total_units !== state.total_units) throw new Error('Se recibió una colocación incompatible con esta ejecución.');
          return { ...next, snapshot, placements: [...state.placements, placement],
            placed_units: data.placed_units, progress_pct: data.progress_pct };
        }
        case 'group_completed': return { ...next, completedGroups: [...new Set([...state.completedGroups, groupKey(data)])], resultUrl: data.result_url };
        case 'metrics_calculated': return { ...next, metrics: data.metrics ?? null, metrics_available: data.metrics_available, stage: 'calculating_metrics' };
        case 'optimization_completed':
          if (data.placed_units !== state.placements.length || data.total_units !== state.total_units) throw new Error('Los contadores no coinciden con las colocaciones recibidas. Recupera el resultado.');
          return { ...next, status: runStatus(data.estado), estado: data.estado, completo: data.completo,
            placed_units: data.placed_units, progress_pct: data.progress_pct, resultUrl: data.result_url,
            stage: data.completo ? 'completed' : state.stage, confirmable: false };
        case 'optimization_failed': return { ...next, status: 'failed', estado: 'FALLIDA', error: data.message, resultUrl: data.result_url, confirmable: false,
          errorKind: data.code === 'TIME_BUDGET_EXCEEDED' ? 'time_budget' : null, retryAfter: null };
        default: return next;
      }
    }
    default: return state;
  }
}
