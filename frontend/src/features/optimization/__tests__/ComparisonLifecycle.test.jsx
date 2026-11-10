import { expect, test, vi } from 'vitest';
import fixture from '../../../../../docs/contracts/optimization/comparison-v1.json';
import { createComparisonController } from '../comparisonController';

function deferred() {
  let resolve, reject;
  const promise = new Promise((ok, fail) => { resolve = ok; reject = fail; });
  return { promise, resolve, reject };
}
function setup({ confirmed = false } = {}) {
  localStorage.clear();
  let listener;
  const current = { ...structuredClone(fixture.completed), selected_execution_id: 2,
    confirmable: !confirmed, confirmed, selection_allowed: !confirmed };
  const source = { subscribe(fn) { listener = fn; return () => {}; },
    load() { listener({ type: 'orders', orders: [{ id_pedido: 1 }, { id_pedido: 99 }] }); },
    refresh: vi.fn(), dispose() {}, emit(orders) { listener({ type: 'orders', orders }); } };
  const api = { load: vi.fn(async () => structuredClone(current)),
    result: vi.fn(async (_, e) => structuredClone(fixture.results[e.execution_id])),
    manifest: vi.fn(async (_, e) => structuredClone(fixture.manifests[e.execution_id])),
    confirm: vi.fn(async () => {}), choose: vi.fn(), release: vi.fn(), start: vi.fn(), observe: vi.fn(), lookup: vi.fn() };
  const flow = createComparisonController({ api, source, storageKey: 'lifecycle-test' });
  flow.mount();
  return { flow, api, source, current };
}

test('an ambiguous start keeps its key and order set across reload and retry', async () => {
  const { flow, api, source, current } = setup();
  flow.select([1]);
  api.start.mockRejectedValueOnce(Object.assign(new Error('Sin conexión'), { status: 0 }));
  await flow.start();
  const key = api.start.mock.calls[0][1];
  expect(flow.getSnapshot().pendingRequest).toBe(true);
  flow.select([99]);
  await flow.start();
  expect(api.start).toHaveBeenCalledTimes(1);
  expect(flow.getSnapshot().error).toContain('antes de cambiar los pedidos');
  flow.dispose();
  api.lookup.mockRejectedValue(Object.assign(new Error('No encontrada'), { status: 404 }));
  api.start.mockResolvedValue(current);
  const restored = createComparisonController({ api, source, storageKey: 'lifecycle-test' });
  restored.mount();
  try {
    await vi.waitFor(() => expect(api.lookup).toHaveBeenCalledWith(key));
    expect(restored.getSnapshot().selected).toEqual([1]);
    await restored.start();
    expect(api.start.mock.calls[1][0]).toEqual([1]);
    expect(api.start.mock.calls[1][1]).toBe(key);
  } finally { restored.dispose(); }
});

test.each(['OPTIMIZER_BUSY', 'RECOVERY_BLOCKED'])('a confirmed %s rejection allows selecting another order', async code => {
  const { flow, api, current } = setup();
  try {
    flow.select([1]);
    api.start.mockRejectedValueOnce(Object.assign(new Error('Inicio rechazado'), {
      status: 503, code, requestAccepted: false,
    }));
    await flow.start();
    expect(flow.getSnapshot()).toMatchObject({ pendingRequest: false, error: 'Inicio rechazado' });
    flow.select([99]);
    api.start.mockResolvedValue(current);
    await flow.start();
    expect(api.start.mock.calls[1][0]).toEqual([99]);
    expect(api.start.mock.calls[1][1]).not.toBe(api.start.mock.calls[0][1]);
  } finally { flow.dispose(); }
});

test('acknowledged confirmation clears transient state and storage once, preserving only success and pending orders', async () => {
  const { flow, api, source } = setup();
  try {
    await flow.load(1);
    const pending = deferred(); api.confirm.mockReturnValue(pending.promise);
    const first = flow.confirm(); await flow.confirm();
    expect(flow.getSnapshot().busy).toBe(true);
    expect(api.confirm).toHaveBeenCalledTimes(1);
    pending.resolve(); await first;
    expect(flow.getSnapshot()).toMatchObject({ comparison: null, selected: [], results: {}, visuals: {}, live: {},
      cursor: 0, partial: false, history: false, busy: false, error: '', orders: [{ id_pedido: 99 }] });
    expect(flow.getSnapshot().success).toContain('Trabajo #1 confirmado');
    expect(localStorage.getItem('lifecycle-test')).toBeNull();
    expect(source.refresh).toHaveBeenLastCalledWith({ force: true });
    source.emit([{ id_pedido: 1 }, { id_pedido: 99 }]);
    expect(flow.getSnapshot().orders).toEqual([{ id_pedido: 99 }]);
  } finally { flow.dispose(); }
});

test.each([409, 500, 503, 0])('failed confirmation status %s retains the work and shows no success', async status => {
  const { flow, api } = setup();
  try {
    await flow.load(1);
    api.confirm.mockRejectedValue(Object.assign(new Error('No se confirmó el corte.'), { status }));
    await flow.confirm();
    expect(flow.getSnapshot().comparison.comparison_id).toBe(1);
    expect(flow.getSnapshot().results[2]).toBeDefined();
    expect(flow.getSnapshot().success).toBe('');
    expect(flow.getSnapshot().error).toBe('No se confirmó el corte.');
    expect(localStorage.getItem('lifecycle-test')).not.toBeNull();
  } finally { flow.dispose(); }
});

test('ambiguous confirmation recovers committed backend state by GET without posting another confirmation', async () => {
  const { flow, api, current } = setup();
  try {
    await flow.load(1);
    api.confirm.mockRejectedValue(Object.assign(new Error('Respuesta interrumpida'), { status: 0 }));
    await flow.confirm();
    current.confirmed = true; current.confirmable = false; current.selection_allowed = false;
    await flow.refresh();
    expect(api.confirm).toHaveBeenCalledTimes(1);
    expect(flow.getSnapshot().comparison).toBeNull();
    expect(flow.getSnapshot().success).toContain('Trabajo #1 confirmado');
  } finally { flow.dispose(); }
});

test('late visual replies cannot restore a work after confirmation', async () => {
  const { flow, api } = setup();
  try {
    const pending = deferred(); api.manifest.mockReturnValue(pending.promise);
    const loading = flow.load(1);
    await vi.waitFor(() => expect(api.manifest).toHaveBeenCalledTimes(3));
    await flow.confirm();
    pending.resolve(fixture.manifests[1]); await loading;
    expect(flow.getSnapshot().comparison).toBeNull();
    expect(flow.getSnapshot().visuals).toEqual({});
    expect(flow.getSnapshot().results).toEqual({});
  } finally { flow.dispose(); }
});

test('confirmed history is consultable explicitly and cannot be selected or confirmed again', async () => {
  const { flow, api } = setup({ confirmed: true });
  try {
    await flow.load(1);
    expect(flow.getSnapshot().history).toBe(true);
    expect(flow.getSnapshot().comparison.confirmed).toBe(true);
    expect(flow.getSnapshot().results[2]).toBeDefined();
    await flow.confirm(); await flow.choose(1); await flow.release();
    expect(api.confirm).not.toHaveBeenCalled();
    expect(api.choose).not.toHaveBeenCalled();
    expect(api.release).not.toHaveBeenCalled();
  } finally { flow.dispose(); }
});

test('release returns to pending without confirming and clearing the view does not delete history', async () => {
  const { flow, api, source, current } = setup();
  try {
    await flow.load(1);
    api.release.mockResolvedValue({ ...current, released: true, confirmable: false, selection_allowed: false });
    await flow.release();
    expect(api.confirm).not.toHaveBeenCalled();
    expect(flow.getSnapshot().comparison).toBeNull();
    expect(flow.getSnapshot().selected).toEqual([]);
    expect(flow.getSnapshot().success).toContain('liberado sin confirmar');
    expect(source.refresh).toHaveBeenLastCalledWith({ force: true });
    current.released = true; current.confirmable = false; current.selection_allowed = false;
    await flow.load(1);
    expect(flow.getSnapshot().comparison.released).toBe(true);
    expect(flow.getSnapshot().history).toBe(true);
    flow.reset();
    expect(flow.getSnapshot().comparison).toBeNull();
    expect(api.release).toHaveBeenCalledTimes(1);
  } finally { flow.dispose(); }
});

test('an automatically recovered confirmed work is cleared rather than restored as an active operation', async () => {
  const { flow, api, current } = setup({ confirmed: true });
  try {
    await flow.load(1, { automatic: true });
    expect(flow.getSnapshot().comparison).toBeNull();
    expect(flow.getSnapshot().success).toContain('Trabajo #1 confirmado');
    expect(api.confirm).not.toHaveBeenCalled();
    expect(current.confirmed).toBe(true);
  } finally { flow.dispose(); }
});
