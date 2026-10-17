import { useEffect, useReducer, useRef } from 'react';
import { buildRunRequest } from './runContract.js';
import { initialOptimization, optimizationReducer } from './optimizationModel';

let runSequence = 0;
export function useFirstFit({ source, adapter, onSessionExpired, result }) {
  const [state, dispatch] = useReducer(optimizationReducer, initialOptimization);
  const lifecycle = useRef(0);
  const stream = useRef(null);
  const activeRun = useRef(null);
  const busy = useRef(false);
  useEffect(() => {
    const invalidate = () => { lifecycle.current++; };
    const unsubscribe = source.subscribe(event => {
      if (event.type === 'orders') dispatch({ type: 'orders_received', orders: event.orders });
      else {
        if (event.error.status === 401) onSessionExpired?.();
        dispatch({ type: 'orders_failed', message: event.error.message });
      }
    });
    source.load();
    return () => { invalidate(); unsubscribe(); source.dispose(); stream.current?.dispose(); activeRun.current = null; };
  }, [source, onSessionExpired]);
  useEffect(() => { if (result) dispatch({ type: 'result', result }); }, [result]);
  async function prepare() {
    if (busy.current || !state.selected.length || state.connection !== 'connected') return;
    busy.current = true;
    const version = lifecycle.current;
    dispatch({ type: 'preparing' });
    try {
      const snapshot = await adapter.prepare(buildRunRequest(state.selected));
      if (version === lifecycle.current) dispatch({ type: 'prepared', snapshot });
    } catch (error) {
      if (error.status === 401) onSessionExpired?.();
      if (version === lifecycle.current) dispatch({ type: 'prepare_failed', message: error.message });
    } finally { busy.current = false; }
  }
  function run() {
    if (!state.snapshot || state.status === 'running') return;
    stream.current?.dispose();
    const runId = `first-fit-${++runSequence}`;
    activeRun.current = runId;
    dispatch({ type: 'run', runId });
    try {
      stream.current = adapter.createEventSource(buildRunRequest(state.snapshot.orders.map(o => o.id_pedido)), { snapshot: state.snapshot });
      const accept = event => {
        if (runId !== activeRun.current) return;
        dispatch({ type: 'event', event, runId });
        if (['optimization_completed', 'optimization_failed'].includes(event.event) && adapter.loadResult) {
          Promise.resolve().then(() => adapter.loadResult(event.id_optimizacion, { resultUrl: event.data.result_url }))
            .then(result => { if (runId === activeRun.current) dispatch({ type: 'result', result, runId }); })
            .catch(error => {
              if (error.status === 401) onSessionExpired?.();
              if (runId === activeRun.current) dispatch({ type: 'result_error', message: 'No se pudo recuperar el resultado. La confirmación sigue deshabilitada.' });
            });
        }
      };
      stream.current.subscribe(accept, error => {
        if (error.status === 401) onSessionExpired?.();
        if (runId === activeRun.current) dispatch({ type: 'connection_failed', message: error.message, rejected: error.status >= 400 && error.status < 500 });
      }, optimizationId => {
        if (runId === activeRun.current) dispatch({ type: 'accepted', optimizationId, runId });
      });
    } catch (error) { dispatch({ type: 'connection_failed', message: error.message, rejected: error.status >= 400 && error.status < 500 }); }
  }
  function discard() { activeRun.current = null; stream.current?.dispose(); lifecycle.current++; busy.current = false; dispatch({ type: 'discard' }); }
  async function recover() {
    const version = lifecycle.current, run = activeRun.current;
    try {
      const result = await adapter.loadResult(state.optimizationId, { resultUrl: state.resultUrl });
      if (version === lifecycle.current && run === activeRun.current) dispatch({ type: 'result', result });
    } catch (error) {
      if (error.status === 401) onSessionExpired?.();
      if (version === lifecycle.current && run === activeRun.current) dispatch({ type: 'result_error', message: 'No se pudo recuperar el resultado.' });
    }
  }
  async function load(id) {
    if (busy.current || state.status === 'running') return;
    busy.current = true;
    stream.current?.dispose(); activeRun.current = null;
    const version = ++lifecycle.current;
    dispatch({ type: 'loading_result' });
    try {
      const result = await adapter.loadResult(id);
      if (version === lifecycle.current) dispatch({ type: 'result', result });
    } catch (error) {
      if (error.status === 401) onSessionExpired?.();
      if (version === lifecycle.current) dispatch({ type: 'result_error', message: error.message });
    } finally { busy.current = false; }
  }
  return { state, prepare, run, discard, recover, load, confirmed: () => dispatch({ type: 'confirmed' }), select: ids => dispatch({ type: 'select', ids }) };
}
