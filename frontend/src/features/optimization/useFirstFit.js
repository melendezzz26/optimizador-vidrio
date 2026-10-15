import { useEffect, useReducer, useRef } from 'react';
import { initialOptimization, optimizationReducer } from './optimizationModel';

let runSequence = 0;
export function useFirstFit({ source, adapter, onSessionExpired }) {
  const [state, dispatch] = useReducer(optimizationReducer, initialOptimization);
  const lifecycle = useRef(0);
  const stream = useRef(null);
  const busy = useRef(false);
  useEffect(() => {
    const version = lifecycle.current;
    const unsubscribe = source.subscribe(event => {
      if (event.type === 'orders') dispatch({ type: 'orders_received', orders: event.orders });
      else {
        if (event.error.status === 401) onSessionExpired?.();
        dispatch({ type: 'orders_failed', message: event.error.message });
      }
    });
    source.load();
    return () => { lifecycle.current = version + 1; unsubscribe(); source.dispose(); stream.current?.dispose(); };
  }, [source, onSessionExpired]);
  async function prepare() {
    if (busy.current || !state.selected.length || state.connection !== 'connected') return;
    busy.current = true;
    const version = lifecycle.current;
    dispatch({ type: 'preparing' });
    try {
      const snapshot = await adapter.prepare([...state.selected]);
      if (version === lifecycle.current) dispatch({ type: 'prepared', snapshot });
    } catch (error) {
      if (version === lifecycle.current) dispatch({ type: 'prepare_failed', message: error.message });
    } finally { busy.current = false; }
  }
  function run() {
    if (!state.snapshot || state.status === 'running') return;
    stream.current?.dispose();
    const runId = `first-fit-${++runSequence}`;
    dispatch({ type: 'run', runId });
    try {
      stream.current = adapter.createEventSource(state.snapshot);
      stream.current.subscribe(event => dispatch({ type: 'event', event }), runId);
    } catch (error) { dispatch({ type: 'event', event: { type: 'optimization_failed', run_id: runId, message: error.message } }); }
  }
  function discard() { stream.current?.dispose(); lifecycle.current++; busy.current = false; dispatch({ type: 'discard' }); }
  return { state, prepare, run, discard, select: ids => dispatch({ type: 'select', ids }) };
}
