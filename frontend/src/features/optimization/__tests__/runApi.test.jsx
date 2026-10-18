import { expect, test, vi } from 'vitest';
import { createBackendRunAdapter, RunApiError } from '../runApi';
import shared from '../contractV1Fixture.json';
import { fixtureOrders } from '../firstFitFixture';

function stream(events, width = 7) {
  const bytes = new TextEncoder().encode(events.map(e => JSON.stringify(e)).join('\n') + '\n');
  return new Response(new ReadableStream({ start(controller) {
    for (let i = 0; i < bytes.length; i += width) controller.enqueue(bytes.slice(i, i + width));
    controller.close();
  } }), { status: 201, headers: { 'Content-Type': 'application/x-ndjson' } });
}
const json = data => new Response(JSON.stringify(data), { headers: { 'Content-Type': 'application/json' } });

test('real adapter posts order_ids once, parses fragmented NDJSON and preserves Decimal/physical identities', async () => {
  const fetchImpl = vi.fn().mockResolvedValue(stream(shared.success_events));
  const adapter = createBackendRunAdapter({ token: 'synthetic-token', fetchImpl });
  const received = [];
  await new Promise((resolve, reject) => adapter.createEventSource({ order_ids: [10] }).subscribe(event => {
    received.push(event); if (event.event === 'optimization_completed') resolve();
  }, reject));
  expect(received).toEqual(shared.success_events);
  expect(fetchImpl).toHaveBeenCalledOnce();
  const [url, options] = fetchImpl.mock.calls[0];
  expect(url).toMatch(/\/api\/optimization\/runs$/);
  expect(options.method).toBe('POST'); expect(JSON.parse(options.body)).toEqual({ order_ids: [10] });
  expect(options.headers.Authorization).toBe('Bearer synthetic-token');
  expect(options.signal).toBeInstanceOf(AbortSignal);
});
test('canonical GET and confirmation use implemented URLs, without following external result_url or sending a body', async () => {
  const fetchImpl = vi.fn().mockResolvedValueOnce(json(shared.result)).mockResolvedValueOnce(json(shared.confirmation));
  const adapter = createBackendRunAdapter({ token: 'test', fetchImpl });
  expect(await adapter.loadResult(101, { resultUrl: 'https://untrusted.invalid/redirect' })).toEqual(shared.result);
  expect(await adapter.confirm(101)).toEqual(shared.confirmation);
  expect(fetchImpl.mock.calls[0][0]).toMatch(/\/api\/optimization\/runs\/101$/);
  expect(fetchImpl.mock.calls[1][0]).toMatch(/\/api\/optimization\/runs\/101\/confirm$/);
  expect(fetchImpl.mock.calls[1][1].method).toBe('POST');
  expect(fetchImpl.mock.calls[1][1]).not.toHaveProperty('body');
  expect(fetchImpl.mock.calls[1][1].headers).not.toHaveProperty('Content-Type');
});
test.each([401, 403, 404, 409, 422, 500])('HTTP %i keeps safe error status and code without automatic retry', async status => {
  const fetchImpl = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { code: 'SAFE_CODE', message: 'Mensaje seguro' } }), { status }));
  const adapter = createBackendRunAdapter({ fetchImpl });
  await expect(adapter.confirm(101)).rejects.toMatchObject({ status, code: 'SAFE_CODE', message: 'Mensaje seguro' });
  expect(fetchImpl).toHaveBeenCalledOnce();
});
test('stream HTTP 403 reaches the consumer without parser error or fake completion', async () => {
  const fetchImpl = vi.fn().mockResolvedValue(new Response('{}', { status: 403 }));
  const adapter = createBackendRunAdapter({ fetchImpl });
  const received = [];
  const failure = await new Promise(resolve => adapter.createEventSource({ order_ids: [10] }).subscribe(e => received.push(e), resolve));
  expect(failure).toBeInstanceOf(RunApiError); expect(failure.status).toBe(403); expect(received).toEqual([]);
});
test('preparation reads every persisted order without creating stock, masks, states or mutations', async () => {
  const fetchImpl = vi.fn();
  const readOrder = vi.fn(async id => structuredClone(fixtureOrders.find(o => o.id_pedido === id)));
  const adapter = createBackendRunAdapter({ token: 'test', fetchImpl, readOrder });
  const prepared = await adapter.prepare({ order_ids: [21, 22] });
  expect(prepared.total).toBe(4); expect(prepared.orders.map(o => o.id_pedido)).toEqual([21, 22]);
  expect(prepared.groups.every(g => g.containers.length === 0)).toBe(true);
  expect(prepared.rasters).toEqual({}); expect(prepared.fixture).toBeUndefined();
  expect(fetchImpl).not.toHaveBeenCalled(); expect(readOrder).toHaveBeenCalledTimes(2);
  readOrder.mockResolvedValue({ ...fixtureOrders[0], estado: 'OPTIMIZADO' });
  await expect(adapter.prepare({ order_ids: [21] })).rejects.toMatchObject({ status: 409 });
});
test('disposing the real stream aborts its request and suppresses late events', () => {
  let signal;
  const fetchImpl = vi.fn((url, options) => { signal = options.signal; return new Promise(() => {}); });
  const listener = vi.fn(); const failed = vi.fn();
  const source = createBackendRunAdapter({ fetchImpl }).createEventSource({ order_ids: [10] });
  source.subscribe(listener, failed); source.dispose();
  expect(signal.aborted).toBe(true); expect(listener).not.toHaveBeenCalled(); expect(failed).not.toHaveBeenCalled();
});

test('Location preserves the durable ID if streaming fails before the first valid envelope', async () => {
  const fetchImpl = vi.fn().mockResolvedValue(new Response('{broken}\n', {
    status: 201, headers: { 'Content-Type': 'application/x-ndjson', Location: '/api/optimization/runs/101' },
  }));
  const accepted = vi.fn(), listener = vi.fn();
  await new Promise(resolve => createBackendRunAdapter({ fetchImpl }).createEventSource({ order_ids: [10] })
    .subscribe(listener, resolve, accepted));
  expect(accepted).toHaveBeenCalledExactlyOnceWith(101);
  expect(listener).not.toHaveBeenCalled(); expect(fetchImpl).toHaveBeenCalledOnce();
});
