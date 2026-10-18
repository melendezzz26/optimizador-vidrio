import { listOrders } from '../orders/ordersApi';

// Complete snapshots only: a partial pagination response must never remove selection.
export function createPendingOrdersSource({ token, intervalMs = 15000, request = listOrders,
  schedule = setTimeout, cancel = clearTimeout } = {}) {
  const listeners = new Set();
  let controller, timer, busy = false, disposed = false, generation = 0;
  const publish = event => listeners.forEach(listener => listener(event));
  async function refresh() {
    if (disposed || busy) return;
    busy = true;
    const current = generation;
    cancel(timer);
    controller = new AbortController();
    const requestController = controller;
    try {
      let page = 1, totalPages = 1;
      const orders = [];
      do {
        const result = await request({ estado: 'PENDIENTE', page, limit: 100 }, { token, signal: requestController.signal });
        if (!Array.isArray(result.items) || !Number.isInteger(result.total_pages) || result.total_pages < 0) throw new Error('Respuesta de pedidos no válida.');
        orders.push(...result.items);
        totalPages = result.total_pages;
        page++;
      } while (page <= totalPages && !disposed && current === generation);
      if (!disposed && current === generation) publish({ type: 'orders', orders: [...new Map(orders.map(o => [o.id_pedido, o])).values()] });
    } catch (error) {
      if (!disposed && current === generation && error.name !== 'AbortError') publish({ type: 'error', error });
    } finally {
      if (current === generation) {
        busy = false;
        if (!disposed) timer = schedule(refresh, intervalMs);
      }
    }
  }
  return {
    load() { disposed = false; return refresh(); }, refresh,
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    dispose() { disposed = true; generation++; busy = false; cancel(timer); controller?.abort(); listeners.clear(); },
  };
}

export function createFixturePendingOrdersSource(initial, { schedule = setTimeout, cancel = clearTimeout, changes = [] } = {}) {
  let orders = structuredClone(initial), timers = [];
  const listeners = new Set();
  const publish = event => listeners.forEach(listener => listener(event));
  const refresh = () => publish({ type: 'orders', orders: structuredClone(orders) });
  function emit(change) {
    if (change.type === 'error') { publish({ type: 'error', error: new Error('Conexión interrumpida. Se intentará reconectar automáticamente.') }); return; }
    if (change.type === 'upsert') orders = [...orders.filter(o => o.id_pedido !== change.order.id_pedido), change.order];
    if (change.type === 'remove') orders = orders.filter(o => o.id_pedido !== change.id);
    refresh();
  }
  return { refresh, emit,
    load() { refresh(); timers = changes.map(change => schedule(() => emit(change), change.afterMs)); },
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    dispose() { timers.forEach(cancel); timers = []; listeners.clear(); },
  };
}
