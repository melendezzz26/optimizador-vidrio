export const STAGES = [
  ['preparing_orders', 'Preparando pedidos'], ['grouping_materials', 'Agrupando materiales'],
  ['rasterizing', 'Rasterizando / preparando geometrías'], ['sorting_pieces', 'Ordenando piezas'],
  ['first_fit', 'Ejecutando First Fit'], ['calculating_metrics', 'Calculando métricas'],
];
export const initialOptimization = {
  status: 'loading_orders', orders: [], selected: [], connection: 'loading', orderError: '',
  snapshot: null, placements: [], completedGroups: [], metrics: null, error: '', runId: null, stage: null,
};
export const placementKey = p => `${p.id_pedido}:${p.id_pieza}:${p.unit_index}`;
export const containerKey = p => `${p.material_source}:${p.material_id}`;
export const pieceCount = orders => orders.reduce((sum, order) => sum + (order.piezas ?? []).reduce((n, p) => n + p.cantidad, 0), 0);

export function optimizationReducer(state, action) {
  switch (action.type) {
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
      return { ...state, selected: action.ids.filter(id => state.orders.some(o => o.id_pedido === id)),
        status: 'selection_ready', snapshot: null, placements: [], metrics: null, error: '', runId: null, stage: null, completedGroups: [] };
    case 'preparing': return { ...state, status: 'preparing', error: '', snapshot: null, placements: [], metrics: null, runId: null, stage: null, completedGroups: [] };
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
      return { ...state, status: 'running', runId: action.runId, placements: [], metrics: null,
        completedGroups: [], stage: 'preparing_orders', error: '', availableAtStart: state.orders.map(o => o.id_pedido) };
    case 'discard': return { ...state, status: 'selection_ready', snapshot: null, placements: [], metrics: null, runId: null, error: '', stage: null };
    case 'event': {
      const event = action.event;
      if (state.status !== 'running' || event.run_id !== state.runId) return state;
      switch (event.type) {
        case 'optimization_started': return state;
        // Optional UI/fixture telemetry, never required by the public backend contract.
        // Public group/metrics/completion events advance the UI without this event.
        case 'stage_changed': return STAGES.some(([id]) => id === event.stage) ? { ...state, stage: event.stage } : state;
        case 'group_started': return { ...state, activeGroup: event.group_id, stage: 'first_fit' };
        case 'piece_started': return { ...state, activePiece: event.id_pieza };
        case 'piece_placed': {
          if (state.placements.some(p => placementKey(p) === placementKey(event))) return state;
          const order = state.snapshot.orders.find(o => o.id_pedido === event.id_pedido);
          const piece = order?.piezas.find(p => p.id_pieza === event.id_pieza);
          const group = state.snapshot.groups.find(g => g.id === event.group_id);
          if (!piece || !Number.isInteger(event.unit_index) || event.unit_index < 0 || event.unit_index >= piece.cantidad
            || ![event.x_mm, event.y_mm, event.rotation_deg].every(Number.isFinite)
            || !group?.containers.some(c => containerKey(c) === containerKey(event))) {
            return { ...state, status: 'failed', error: 'Se recibió una colocación incompatible con esta ejecución.' };
          }
          return { ...state, placements: [...state.placements, event] };
        }
        case 'group_completed': return { ...state, completedGroups: [...new Set([...state.completedGroups, event.group_id])] };
        case 'metrics_calculated': return { ...state, metrics: event.metrics, stage: 'calculating_metrics' };
        case 'optimization_completed': return state.metrics
          ? { ...state, status: 'completed' }
          : { ...state, status: 'failed', error: 'La ejecución terminó sin métricas.' };
        case 'optimization_failed': return { ...state, status: 'failed', error: event.message || 'No se pudo completar First Fit.' };
        default: return state;
      }
    }
    default: return state;
  }
}
