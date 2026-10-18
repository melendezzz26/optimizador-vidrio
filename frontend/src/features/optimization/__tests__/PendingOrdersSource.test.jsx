import { expect, test, vi } from 'vitest';
import { createPendingOrdersSource } from '../pendingOrdersSource';

test('pagination deduplicates repeated IDs while preserving distinct orders for the same client', async () => {
  const first = { id_pedido: 73, cliente: 'Vidrios Norte', estado: 'PENDIENTE' };
  const historical = { ...first, id_pedido: 74 };
  const request = vi.fn()
    .mockResolvedValueOnce({ items: [first], total_pages: 2 })
    .mockResolvedValueOnce({ items: [first, historical], total_pages: 2 });
  const source = createPendingOrdersSource({ request, schedule: vi.fn(), cancel: vi.fn() });
  const listener = vi.fn();
  source.subscribe(listener);
  await source.load();
  expect(request).toHaveBeenCalledTimes(2);
  expect(listener).toHaveBeenCalledWith({ type: 'orders', orders: [first, historical] });
  source.dispose();
});
