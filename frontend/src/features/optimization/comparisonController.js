// Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
import { emptyVisual } from './visualState';
import { visualPlacement, unitKey, stockKey } from './runContract';

const freshVisual = () => ({ ...emptyVisual(), enabled: true });
const newKey = () => globalThis.crypto?.randomUUID?.() ?? `cmp-${Date.now()}-${Math.random().toString(36).slice(2)}`;

export function createComparisonController({ api, apiV2, source, storageKey, initialId, initialProfile, onExpired, onLegacy }) {
  let state = { orders: [], selected: [], comparison: null, results: {}, visuals: {}, live: {}, cursor: 0,
    busy: false, loading: true, error: '', success: '', history: false, connection: 'connecting', partial: false,
    savedComparisons: [], historyNext: null, historyOpen: false, pendingRequest: false,
    profile: initialProfile === 'comparison-v2' ? 'comparison-v2' : 'comparison-v1' };
  let active = false, generation = 0, observer, request, retry, unsubscribe, requestKey, operation, syncTimer;
  let actionSequence = 0;
  let attemptOrders = null;
  const confirmedOrders = new Set();
  const listeners = new Set();
  const set = patch => { state = { ...state, ...patch }; listeners.forEach(fn => fn()); };
  const remember = (pending = false) => { try { localStorage.setItem(storageKey, JSON.stringify({ id: pending ? null : state.comparison?.comparison_id,
    requestKey, operation, attemptOrders, profile: state.profile })); } catch { /* Almacenamiento opcional. */ } };
  const client = profile => profile === 'comparison-v2' ? apiV2 : api;
  const valid = g => active && g === generation;
  const fail = error => { if (error.status === 401) onExpired?.(); set({ error: error.message, loading: false }); };
  function clearWork(success = '') {
    prepare(); actionSequence++; requestKey = null; operation = null; attemptOrders = null;
    try { localStorage.removeItem(storageKey); } catch { /* Almacenamiento opcional. */ }
    set({ comparison: null, results: {}, visuals: {}, live: {}, cursor: 0, selected: [], error: '',
      partial: false, history: false, busy: false, loading: true, success, connection: 'connecting',
      pendingRequest: false, orders: state.orders.filter(order => !confirmedOrders.has(order.id_pedido)) });
    source.refresh?.({ force: true });
  }
  function confirmed(current) {
    current.order_ids.forEach(id => confirmedOrders.add(id));
    clearWork(`Trabajo #${current.comparison_id} confirmado. Los pedidos y el inventario se actualizaron con la distribución elegida.`);
  }
  function released(current) {
    clearWork(`Trabajo #${current.comparison_id} liberado sin confirmar. Los pedidos vuelven a pendientes y el inventario se conserva.`);
  }
  function apply(current) {
    if (state.comparison?.comparison_id === current.comparison_id && state.comparison.version > current.version) return;
    const profile = current.profile === 'comparison-v2' ? 'comparison-v2' : 'comparison-v1';
    set({ comparison: current, profile, loading: false, pendingRequest: false }); remember();
  }
  async function sync(visual = false) {
    const g = generation, current = state.comparison;
    if (!current) return;
    const activeApi = client(current.profile);
    const next = await activeApi.load(current.comparison_id, request?.signal);
    if (!valid(g)) return;
    if (next.profile !== 'comparison-v2' && next.confirmed && !state.history) { confirmed(next); return; }
    if (next.profile !== 'comparison-v2' && next.released && !state.history) { released(next); return; }
    apply(next);
    await Promise.all(next.executions.map(async execution => {
      if (execution.result_available ?? execution.status === 'COMPLETADA') {
        const old = state.results[execution.execution_id];
        const signature = JSON.stringify([execution.metrics, execution.complete, execution.diagnostic]);
        if (!old || old.signature !== signature) {
          const value = await activeApi.result(next, execution, request?.signal);
          if (valid(g)) set({ results: { ...state.results, [execution.execution_id]: { result: value.result, signature } } });
        }
      }
      if (visual) {
        try {
          const manifest = await activeApi.manifest(next, execution, request?.signal);
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
    const g = generation;
    syncTimer = setTimeout(() => { if (valid(g)) sync(visual).catch(error => {
      if (valid(g) && error.name !== 'AbortError') fail(error);
    }); }, 40);
  }
  function event(value) {
    set({ cursor: value.sequence, connection: 'connected' });
    if (value.event === 'snapshot_required') { set({ partial: true }); delayedSync(true); return; }
    if (value.event === 'search_progress') {
      const key = value.execution_id, previous = state.visuals[key] ?? freshVisual();
      if (value.execution_sequence > previous.sequence) set({ visuals: { ...state.visuals, [key]: {
        ...previous, sequence: value.execution_sequence, searchProgress: value.data } } });
      return;
    }
    if (value.event === 'execution_state') { delayedSync(); return; }
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
      await client(state.comparison.profile).observe(state.comparison, state.cursor, value => { if (valid(g)) event(value); }, observer.signal);
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
  async function load(id, { automatic = false, profile = state.profile } = {}) {
    const selectedProfile = profile === 'comparison-v2' ? 'comparison-v2' : 'comparison-v1';
    const g = prepare(); set({ profile: selectedProfile, loading: true, error: '', success: '', history: false, cursor: 0, visuals: {}, results: {}, live: {}, partial: false });
    try {
      const current = await client(selectedProfile).load(id, request.signal);
      if (!valid(g)) return;
      if (automatic && current.profile !== 'comparison-v2' && current.confirmed) { confirmed(current); return; }
      if (automatic && current.profile !== 'comparison-v2' && current.released) { released(current); return; }
      set({ history: current.confirmed || current.released });
      apply(current); await sync(true);
      if (valid(g) && !state.comparison.terminal) follow(g);
    } catch (error) {
      if (!valid(g) || error.name === 'AbortError') return;
      if (selectedProfile === 'comparison-v1' && error.status === 404 && onLegacy) onLegacy(id);
      else fail(error);
    }
  }
  async function action(fn) {
    if (state.busy) return;
    const sequence = ++actionSequence;
    set({ busy: true, error: '' });
    try { await fn(); } catch (error) {
      if (active && sequence === actionSequence && error.name !== 'AbortError') {
        fail(error);
        if (error.status === 409) { try { await sync(); if (sequence === actionSequence) { operation = null; remember(); } } catch { /* Mantener el error original. */ } }
      }
    } finally { if (active && sequence === actionSequence) set({ busy: false }); }
  }
  return {
    subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    getSnapshot: () => state,
    mount() {
      active = true;
      unsubscribe = source.subscribe(e => {
        if (!active) return;
        if (e.type === 'orders') {
          const orders = e.orders.filter(order => !confirmedOrders.has(order.id_pedido));
          set({ orders, selected: state.selected.filter(id => orders.some(o => o.id_pedido === id)), loading: false });
        }
        else { set({ connection: 'reconnecting' }); fail(e.error); }
      });
      source.load();
      let saved = {};
      try { const value = JSON.parse(localStorage.getItem(storageKey) ?? '{}'); if (value && typeof value === 'object') saved = value; } catch { /* Sin estado local. */ }
      const restoredProfile = initialProfile ?? (initialId ? 'comparison-v1' : saved.profile);
      if (restoredProfile === 'comparison-v2' && apiV2) set({ profile: 'comparison-v2' });
      requestKey = saved.requestKey; operation = saved.operation;
      attemptOrders = Array.isArray(saved.attemptOrders) && saved.attemptOrders.every(id => Number.isSafeInteger(id) && id > 0)
        ? saved.attemptOrders : null;
      if (requestKey && !saved.id) set({ pendingRequest: true, selected: attemptOrders ?? [] });
      const g = generation;
      if (initialId ?? saved.id) load(initialId ?? saved.id, { automatic: !initialId, profile: restoredProfile });
      else if (requestKey) client(restoredProfile).lookup(requestKey).then(current => { if (valid(g)) load(current.comparison_id, { automatic: true, profile: restoredProfile }); })
        .catch(error => { if (valid(g) && error.status !== 404) fail(error); });
    },
    dispose() { active = false; prepare(); unsubscribe?.(); source.dispose(); },
    select: ids => set({ selected: ids }),
    setProfile(profile) {
      if (!['comparison-v1', 'comparison-v2'].includes(profile) || profile === 'comparison-v2' && !apiV2
        || state.pendingRequest || state.comparison && !state.comparison.released && !state.comparison.confirmed) return;
      if (profile !== state.profile) { requestKey = null; operation = null; }
      set({ profile, error: '' }); remember(true);
    },
    load,
    history: beforeId => action(async () => {
      if (!apiV2?.history) return;
      const g = generation;
      const value = await apiV2.history(beforeId, request?.signal);
      if (valid(g)) set({ savedComparisons: beforeId ? [...state.savedComparisons, ...value.items] : value.items,
        historyNext: value.next_before_id, historyOpen: true });
    }),
    loadByKey(key, profile = state.profile) {
      return action(async () => {
        if (typeof key !== 'string' || !key.trim()) return;
        const g = prepare(), selectedProfile = profile === 'comparison-v2' ? 'comparison-v2' : 'comparison-v1';
        set({ profile: selectedProfile, loading: true, error: '', success: '', history: false, cursor: 0, visuals: {}, results: {}, live: {}, partial: false });
        const current = await client(selectedProfile).lookup(key.trim(), request.signal);
        if (valid(g)) await load(current.comparison_id, { profile: selectedProfile });
      });
    },
    refresh: () => action(async () => {
      if (state.comparison) await sync(true);
      else if (requestKey) { const current = await client(state.profile).lookup(requestKey); await load(current.comparison_id, { profile: state.profile }); }
      else source.refresh?.();
    }),
    start: (profile = state.profile) => action(async () => {
      if (!state.selected.length || state.comparison && !state.comparison.released && !state.comparison.confirmed) return;
      if (state.comparison?.confirmed || state.comparison?.released) requestKey = null;
      if (!['comparison-v1', 'comparison-v2'].includes(profile) || profile === 'comparison-v2' && !apiV2) return;
      if (state.pendingRequest && profile !== state.profile) throw new Error('Actualiza el resultado antes de cambiar los métodos.');
      if (profile !== state.profile) { requestKey = null; operation = null; }
      const selectedOrders = [...state.selected].sort((a, b) => a - b);
      if (requestKey && attemptOrders && JSON.stringify(selectedOrders) !== JSON.stringify(attemptOrders)) {
        throw new Error('Hay una comparación por recuperar. Actualiza el resultado antes de cambiar los pedidos.');
      }
      set({ profile });
      const g = prepare(); requestKey ??= newKey(); attemptOrders = selectedOrders; operation = null;
      set({ pendingRequest: true }); remember(true);
      let current;
      try { current = await client(profile).start(attemptOrders, requestKey, request.signal); }
      catch (error) {
        // A rejected input never became an accepted work. Network errors and
        // conflicts remain recoverable with the original key and frozen orders.
        if ([400, 422].includes(error.status)) {
          requestKey = null; attemptOrders = null; set({ pendingRequest: false }); remember(true);
        }
        throw error;
      }
      if (!valid(g)) return;
      set({ visuals: {}, results: {}, live: {}, cursor: 0, partial: false, success: '', history: false }); apply(current); source.refresh?.(); follow(g);
    }),
    choose: id => action(async () => {
      const current = state.comparison, g = generation;
      if (!current?.selection_allowed) return;
      const next = await client(current.profile).choose(current, id);
      if (valid(g)) { apply(next); operation = null; remember(); }
    }),
    confirm: () => action(async () => {
      const current = state.comparison;
      if (!current?.confirmable || current.confirmed || current.released) return;
      const g = generation;
      if (!operation || operation.executionId !== current.selected_execution_id) operation = { executionId: current.selected_execution_id, version: current.version, key: newKey() };
      remember();
      try { await client(current.profile).confirm(current, operation); }
      catch (error) {
        if (current.profile !== 'comparison-v2' || !valid(g)) throw error;
        // A lost response can follow a successful commit. Read before retrying effects.
        try { await sync(); } catch { /* Keep the stable operation for a later retry. */ }
        const receipt = state.comparison?.confirmation;
        if (!valid(g) || !state.comparison?.confirmed || receipt?.key !== operation.key
          || receipt.execution_id !== operation.executionId || receipt.expected_version !== operation.version) throw error;
      }
      if (!valid(g)) return;
      if (current.profile === 'comparison-v2') {
        await sync();
        if (!valid(g)) return;
        operation = null;
        current.order_ids.forEach(id => confirmedOrders.add(id));
        set({ history: true, error: '', success: `Trabajo #${current.comparison_id} confirmado. Se conserva su resultado histórico.` });
        remember(); source.refresh?.({ force: true });
      } else confirmed(current);
    }),
    release: () => action(async () => {
      const current = state.comparison, g = generation;
      if (!current?.terminal || current.confirmed || current.released) return;
      const next = await client(current.profile).release(current);
      if (valid(g)) released(next);
    }),
    reset() {
      if (state.comparison && !state.comparison.released && !state.comparison.confirmed) return;
      clearWork();
    },
  };
}
