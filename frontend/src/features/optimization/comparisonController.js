// Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
import { emptyVisual } from './visualState';
import { visualPlacement, unitKey, stockKey } from './runContract';

const freshVisual = () => ({ ...emptyVisual(), enabled: true });
const newKey = () => globalThis.crypto?.randomUUID?.() ?? `cmp-${Date.now()}-${Math.random().toString(36).slice(2)}`;

export function createComparisonController({ api, source, storageKey, initialId, onExpired, onLegacy }) {
  let state = { orders: [], selected: [], comparison: null, results: {}, visuals: {}, live: {}, cursor: 0,
    busy: false, loading: true, error: '', connection: 'connecting', partial: false };
  let active = false, generation = 0, observer, request, retry, unsubscribe, requestKey, operation, syncTimer;
  const listeners = new Set();
  const set = patch => { state = { ...state, ...patch }; listeners.forEach(fn => fn()); };
  const remember = (pending = false) => { try { localStorage.setItem(storageKey, JSON.stringify({ id: pending ? null : state.comparison?.comparison_id, requestKey, operation })); } catch { /* Almacenamiento opcional. */ } };
  const valid = g => active && g === generation;
  const fail = error => { if (error.status === 401) onExpired?.(); set({ error: error.message, loading: false }); };
  function apply(current) {
    if (state.comparison?.comparison_id === current.comparison_id && state.comparison.version > current.version) return;
    set({ comparison: current, loading: false }); remember();
  }
  async function sync(visual = false) {
    const g = generation, current = state.comparison;
    if (!current) return;
    const next = await api.load(current.comparison_id, request?.signal);
    if (!valid(g)) return;
    apply(next);
    await Promise.all(next.executions.map(async execution => {
      if (execution.status === 'COMPLETADA') {
        const old = state.results[execution.execution_id];
        const signature = JSON.stringify(execution.metrics);
        if (!old || old.signature !== signature) {
          const value = await api.result(next, execution, request?.signal);
          if (valid(g)) set({ results: { ...state.results, [execution.execution_id]: { result: value.result, signature } } });
        }
      }
      if (visual) {
        try {
          const manifest = await api.manifest(next, execution, request?.signal);
          if (!valid(g)) return;
          const previous = state.visuals[execution.execution_id] ?? freshVisual();
          set({ visuals: { ...state.visuals, [execution.execution_id]: { ...previous,
            sequence: manifest.execution_sequence ?? previous.sequence, preparation: manifest.preparation_completed ? 'complete' : previous.preparation,
            processed: manifest.processed_units, evaluations: manifest.evaluations, order: manifest.ordered_units,
            current: manifest.current, lastOrientation: manifest.last_orientation, descriptors: Object.fromEntries(manifest.items.map(m => [m.mask_ref, m])), error: '' } } });
        } catch (error) {
          if (error.name === 'AbortError' || !valid(g)) return;
          if (error.status === 401) onExpired?.();
          set({ visuals: { ...state.visuals, [execution.execution_id]: { ...(state.visuals[execution.execution_id] ?? freshVisual()), error: error.message } } });
        }
      }
    }));
  }
  function delayedSync(visual = false) {
    clearTimeout(syncTimer);
    syncTimer = setTimeout(() => { if (active) sync(visual).catch(fail); }, 40);
  }
  function event(value) {
    set({ cursor: value.sequence, connection: 'connected' });
    if (value.event === 'snapshot_required') { set({ partial: true }); delayedSync(true); return; }
    if (value.method) {
      const key = value.execution_id, previous = state.visuals[key] ?? freshVisual(), data = value.data;
      if (value.execution_sequence <= previous.sequence) return;
      const visual = { ...previous, sequence: value.execution_sequence, descriptors: { ...previous.descriptors } };
      if (value.event === 'preparation_started') visual.preparation = 'running';
      if (value.event === 'preparation_completed') visual.preparation = 'complete';
      if (value.event === 'ordering_ready') visual.order = data.units;
      if (data.processed_units !== undefined) visual.processed = data.processed_units;
      if (data.evaluation_index !== undefined) visual.evaluations = data.evaluation_index;
      if (['piece_rasterizing', 'piece_ready', 'orientation_testing', 'source_selected', 'piece_unplaced'].includes(value.event)) visual.current = { ...data, kind: value.event };
      if (['orientation_testing', 'source_selected'].includes(value.event)) visual.lastOrientation = { ...data, kind: value.event };
      for (const mask of [data.mask, data.material_mask]) if (mask?.available) visual.descriptors[mask.mask_ref] = mask;
      set({ visuals: { ...state.visuals, [key]: visual } });
      if (value.event === 'piece_placed') {
        const live = state.live[key] ?? { placements: [], materials: [] };
        if (!live.placements.some(p => unitKey(p) === unitKey(data))) set({ live: { ...state.live, [key]: {
          placements: [...live.placements, visualPlacement(data)],
          materials: [...live.materials.filter(m => stockKey(m) !== stockKey(data.material)), data.material] } } });
      }
      if (['result_persisted', 'execution_failed'].includes(value.event)) delayedSync();
    }
    if (value.event === 'comparison_finished') delayedSync();
  }
  async function follow(g) {
    observer?.abort(); observer = new AbortController();
    try {
      await api.observe(state.comparison, state.cursor, value => { if (valid(g)) event(value); }, observer.signal);
      if (valid(g)) await sync();
    } catch (error) {
      if (!valid(g) || error.name === 'AbortError') return;
      if (error.status === 401) { fail(error); return; }
      if (error.code === 'EVENT_CURSOR_EXPIRED' && Number.isSafeInteger(error.latestSequence)) set({ cursor: error.latestSequence, partial: true });
      set({ connection: 'reconnecting' });
      try { await sync(true); } catch (e) { if (valid(g)) fail(e); }
    }
    if (valid(g) && !state.comparison?.terminal) retry = setTimeout(() => follow(g), 1000);
  }
  function prepare() {
    generation++; observer?.abort(); request?.abort(); clearTimeout(retry); clearTimeout(syncTimer);
    request = new AbortController();
    return generation;
  }
  async function load(id) {
    const g = prepare(); set({ loading: true, error: '', cursor: 0, visuals: {}, results: {}, live: {}, partial: false });
    try {
      const current = await api.load(id, request.signal);
      if (!valid(g)) return;
      apply(current); await sync(true);
      if (valid(g) && !state.comparison.terminal) follow(g);
    } catch (error) {
      if (!valid(g) || error.name === 'AbortError') return;
      if (error.status === 404 && onLegacy) onLegacy(id);
      else fail(error);
    }
  }
  async function action(fn) {
    if (state.busy) return;
    set({ busy: true, error: '' });
    try { await fn(); } catch (error) {
      if (active && error.name !== 'AbortError') {
        fail(error);
        if (error.status === 409) { try { await sync(); operation = null; remember(); } catch { /* Mantener el error original. */ } }
      }
    } finally { if (active) set({ busy: false }); }
  }
  return {
    subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    getSnapshot: () => state,
    mount() {
      active = true;
      unsubscribe = source.subscribe(e => {
        if (!active) return;
        if (e.type === 'orders') set({ orders: e.orders, selected: state.selected.filter(id => e.orders.some(o => o.id_pedido === id)), loading: false });
        else { set({ connection: 'reconnecting' }); fail(e.error); }
      });
      source.load();
      let saved = {};
      try { saved = JSON.parse(localStorage.getItem(storageKey) ?? '{}'); } catch { /* Sin estado local. */ }
      requestKey = saved.requestKey; operation = saved.operation;
      if (initialId ?? saved.id) load(initialId ?? saved.id);
      else if (requestKey) api.lookup(requestKey).then(current => { if (active) load(current.comparison_id); }).catch(error => { if (active && error.status !== 404) fail(error); });
    },
    dispose() { active = false; prepare(); unsubscribe?.(); source.dispose(); },
    select: ids => set({ selected: ids }),
    load,
    refresh: () => action(async () => {
      if (state.comparison) await sync(true);
      else if (requestKey) { const current = await api.lookup(requestKey); await load(current.comparison_id); }
      else source.refresh?.();
    }),
    start: () => action(async () => {
      if (!state.selected.length || state.comparison && !state.comparison.released && !state.comparison.confirmed) return;
      const g = prepare(); requestKey ??= newKey(); operation = null; remember(true);
      const current = await api.start(state.selected, requestKey, request.signal);
      if (!valid(g)) return;
      set({ visuals: {}, results: {}, live: {}, cursor: 0, partial: false }); apply(current); source.refresh?.(); follow(g);
    }),
    choose: id => action(async () => { apply(await api.choose(state.comparison, id)); operation = null; remember(); }),
    confirm: () => action(async () => {
      const current = state.comparison;
      if (!current?.confirmable) return;
      if (!operation || operation.executionId !== current.selected_execution_id) operation = { executionId: current.selected_execution_id, version: current.version, key: newKey() };
      remember(); await api.confirm(current, operation); operation = null; remember(); await sync(); source.refresh?.();
    }),
    release: () => action(async () => { apply(await api.release(state.comparison)); requestKey = null; operation = null; remember(); source.refresh?.(); }),
    reset() {
      if (state.comparison && !state.comparison.released && !state.comparison.confirmed) return;
      prepare(); requestKey = null; operation = null;
      set({ comparison: null, results: {}, visuals: {}, live: {}, cursor: 0, selected: [], error: '' }); remember(); source.refresh?.();
    },
  };
}
